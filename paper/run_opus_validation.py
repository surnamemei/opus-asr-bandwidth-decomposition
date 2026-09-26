"""
Stage 2A: validate the direct-libopus encoding path on dev-clean.

Controlled cells (all encoded by paper/opus_direct.py with identical
settings except bitrate and forced bandwidth):

    opus_12k_wb, opus_12k_nb, opus_8k_wb, opus_8k_nb

Diagnostic cells (not part of the design; they tie the direct path to the
frozen pipeline):

    direct_12k_auto, direct_8k_auto   direct path, automatic bandwidth
    ffmpeg_12k, ffmpeg_8k             the frozen ffmpeg command

Every controlled file is decoded through the frozen torchaudio.load path and
measured with the frozen signal functions in paper/common.py (alignment,
LSD, D(f), retained bandwidth, 4-8 kHz power change), plus band-limited LSD
(0-4 kHz and 4-8 kHz), which is new.

Development data only: one utterance per dev-clean speaker. test-clean and
test-other are not touched.

Outputs (results_paper/opus_validation/):
    environment.json, encoder_settings.json
    file_rows.csv            one row per encoded file (controlled cells)
    diagnostic_rows.csv      packet identity of the diagnostic comparisons
    cell_summary.csv         per-cell distributions
    paired_bitrate.csv       per-utterance WB vs NB bitrate at each nominal rate
    frequency_distortion.csv mean and median D(f) per cell
    gates.csv                pass/fail gates (thresholds fixed below)
    bitrate_mode_rows.csv    diagnostic: the four cells under constrained VBR and CBR
    bitrate_mode_summary.csv diagnostic: WB vs NB bitrate gap per bitrate mode
    validation_report.md

Run:
    /home/mei/elec5305-project/.venv/bin/python paper/run_opus_validation.py
"""

import collections
import hashlib
import json
import os
import random
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torchaudio
from tqdm import tqdm

import common
import opus_direct
import run_reproduce


# ==================================================
# Settings
# ==================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path("results_paper") / "opus_validation"

DEV_SUBSET = "dev-clean"
DEV_SEED = 5305            # one utterance per speaker, chosen with this seed

CONTROLLED_CELLS = [
    {"cell": "opus_12k_wb", "bitrate_bps": 12000, "bandwidth": "WB"},
    {"cell": "opus_12k_nb", "bitrate_bps": 12000, "bandwidth": "NB"},
    {"cell": "opus_8k_wb", "bitrate_bps": 8000, "bandwidth": "WB"},
    {"cell": "opus_8k_nb", "bitrate_bps": 8000, "bandwidth": "NB"},
]

# The design uses "vbr" (the frozen ffmpeg setting). The other modes are a
# diagnostic only: do they change the WB vs NB bitrate gap?
BITRATE_MODES = {
    "vbr": {"vbr": True, "vbr_constraint": False},
    "cvbr": {"vbr": True, "vbr_constraint": True},
    "cbr": {"vbr": False, "vbr_constraint": False},
}
DIAGNOSTIC_BITRATE_MODES = ["cvbr", "cbr"]

# Fields of EncoderSettings that the design is allowed to vary
VARIED_SETTINGS = {"bitrate_bps", "bandwidth"}
VARIED_QUERIES = {"bitrate", "bandwidth"}

# Band limits for band-limited LSD. 4 kHz is the nominal Opus NB bandwidth.
IN_BAND_HZ = (0.0, 4000.0)       # [0, 4000)
OUT_BAND_HZ = (4000.0, 8000.0)   # [4000, 8000]

# --------------------------------------------------
# Gate thresholds, fixed before the first validation run
# --------------------------------------------------
GATE_BITRATE_AGGREGATE_GAP = 0.05   # |WB - NB| / nominal, aggregate over files
GATE_BITRATE_MEDIAN_GAP = 0.05      # median per-utterance |WB - NB| / nominal
GATE_MAX_ABS_LAG_SAMPLES = 3        # 16 kHz samples (0.19 ms)
GATE_RETAINED_BW_DIFF_HZ = 2000.0   # median paired WB - NB retained bandwidth
GATE_HF_POWER_DIFF_DB = 6.0         # median paired WB - NB 4-8 kHz power change


# ==================================================
# Helpers
# ==================================================

def select_dev_utterances(dataset) -> list[int]:
    """One utterance per speaker, chosen with a fixed seed."""
    by_speaker = collections.defaultdict(list)
    for n in range(len(dataset)):
        speaker_id = dataset.get_metadata(n)[3]
        by_speaker[speaker_id].append(n)
    rng = random.Random(DEV_SEED)
    return [rng.choice(by_speaker[s]) for s in sorted(by_speaker)]


def band_lsd(reference_mag, processed_mag, frequencies, low_hz, high_hz,
             include_high=False) -> float:
    """
    LSD over the bins in [low_hz, high_hz) (or [low_hz, high_hz]).
    Same log floor as common.spectral_distortion: both spectra are clipped at
    DYNAMIC_RANGE_DB below the full-band reference peak. RMS over the band's
    bins, then mean over frames.
    """
    ref_log = 20.0 * torch.log10(reference_mag + common.LOG_EPS)
    proc_log = 20.0 * torch.log10(processed_mag + common.LOG_EPS)
    floor = ref_log.max() - common.DYNAMIC_RANGE_DB
    difference = torch.clamp(proc_log, min=floor) - torch.clamp(ref_log, min=floor)

    upper = frequencies <= high_hz if include_high else frequencies < high_hz
    band = torch.from_numpy((frequencies >= low_hz) & upper)
    return float(torch.mean(torch.sqrt(torch.mean(difference[band] ** 2, dim=0))))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_ogg_packets(ogg: bytes) -> list[bytes]:
    """Packets as read back by the frozen Ogg parser (common.ogg_audio_packets)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        path = os.path.join(temp_dir, "file.opus")
        Path(path).write_bytes(ogg)
        return common.ogg_audio_packets(path)


def distribution(values) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    return {
        "mean": values.mean(), "sd": values.std(ddof=1) if len(values) > 1 else 0.0,
        "min": values.min(), "p05": np.quantile(values, 0.05),
        "median": np.median(values), "p95": np.quantile(values, 0.95),
        "max": values.max(),
    }


# ==================================================
# Validation of one controlled file
# ==================================================

def validate_file(waveform, sample_rate, ids, cell, bitrate_mode="vbr"
                  ) -> tuple[dict, np.ndarray, list[bytes]]:

    settings = opus_direct.EncoderSettings(
        bitrate_bps=cell["bitrate_bps"], bandwidth=cell["bandwidth"],
        **BITRATE_MODES[bitrate_mode],
    )
    result = opus_direct.encode(waveform, sample_rate, settings)
    repeat = opus_direct.encode(waveform, sample_rate, settings)

    num_samples = waveform.shape[-1]
    duration_seconds = num_samples / sample_rate

    # ---- packets --------------------------------------------------------
    infos = [opus_direct.packet_info(p) for p in result.packets]
    configurations = collections.Counter(i["configuration"] for i in infos)
    bandwidths = collections.Counter(i["bandwidth"] for i in infos)
    modes = collections.Counter(i["mode"] for i in infos)

    # ---- container ------------------------------------------------------
    head = opus_direct.read_opus_head(result.ogg)
    parsed = parse_ogg_packets(result.ogg)

    # ---- decode through the frozen path ----------------------------------
    decoded, decoded_sr = opus_direct.decode_frozen_path(result.ogg)
    decoded_again, _ = opus_direct.decode_frozen_path(result.ogg)
    upsample = decoded_sr // sample_rate

    # ---- frozen signal analysis ------------------------------------------
    resampled = decoded
    if decoded_sr != sample_rate:
        resampled = torchaudio.functional.resample(decoded, decoded_sr, sample_rate)
    aligned_ref, aligned_proc, lag = common.align_waveforms(waveform, resampled)
    reference_mag = common.magnitude_spectrogram(aligned_ref)
    processed_mag = common.magnitude_spectrogram(aligned_proc)
    frequencies = np.linspace(0, sample_rate / 2, common.N_FFT // 2 + 1)

    dspec, lsd_db, dfrequency = common.spectral_distortion(reference_mag, processed_mag)
    retained_bandwidth_hz, hf_power_change_db = common.bandwidth_measures(
        reference_mag, processed_mag, frequencies
    )

    row = {
        **ids,
        "cell": cell["cell"],
        "bitrate_mode": bitrate_mode,
        "nominal_bitrate_kbps": cell["bitrate_bps"] / 1000.0,
        "requested_bandwidth": cell["bandwidth"],
        **result.summary(),
        # packets
        "packet_configurations": json.dumps(dict(configurations)),
        "packet_modes": json.dumps(dict(modes)),
        "packets_in_requested_bandwidth": bandwidths.get(cell["bandwidth"], 0),
        "share_requested_bandwidth": bandwidths.get(cell["bandwidth"], 0) / len(infos),
        "all_packets_silk": modes.get("SILK", 0) == len(infos),
        "frame_ms_values": json.dumps(sorted({i["frame_ms"] for i in infos})),
        "all_single_frame": all(i["frame_count_code"] == 0 for i in infos),
        "all_mono": not any(i["stereo"] for i in infos),
        "libopus_parser_agrees": all(
            i["libopus_bandwidth"] == i["bandwidth"] and i["libopus_frames"] == 1
            and i["libopus_samples_48k"] == settings.frame_samples * upsample
            for i in infos
        ),
        # bitrate
        "duration_seconds": duration_seconds,
        "measured_bitrate_kbps": 8 * len(result.ogg) / duration_seconds / 1000,
        "payload_bitrate_kbps": 8 * result.summary()["payload_bytes"]
        / duration_seconds / 1000,
        "unpadded_payload_bytes": sum(i["unpadded_bytes"] for i in infos),
        "unpadded_bitrate_kbps": 8 * sum(i["unpadded_bytes"] for i in infos)
        / duration_seconds / 1000,
        "packets_code_nonzero": sum(i["frame_count_code"] != 0 for i in infos),
        "packet_bytes_min": min(i["bytes"] for i in infos),
        "packet_bytes_max": max(i["bytes"] for i in infos),
        # container and reproducibility
        "ogg_sha256": sha256(result.ogg),
        "reencode_identical": result.ogg == repeat.ogg,
        "ogg_packets_roundtrip": parsed == result.packets,
        "opus_head_pre_skip": head["pre_skip"],
        "opus_head_input_rate": head["input_sample_rate"],
        "ogg_last_granule": opus_direct.last_granule(result.ogg),
        # decode
        "decoded_sample_rate": decoded_sr,
        "decoded_num_samples": decoded.shape[-1],
        "decoded_duration_seconds": decoded.shape[-1] / decoded_sr,
        "decoded_length_matches_input": decoded.shape[-1] == num_samples * upsample,
        "decode_repeat_identical": torch.equal(decoded, decoded_again),
        "resampled_num_samples": resampled.shape[-1],
        # alignment
        "alignment_lag_samples": lag,
        "alignment_lag_ms": lag / sample_rate * 1000.0,
        "aligned_num_samples": aligned_ref.shape[-1],
        # signal
        "spectral_distortion": dspec,
        "lsd_db": lsd_db,
        "lsd_0_4k_db": band_lsd(reference_mag, processed_mag, frequencies,
                                *IN_BAND_HZ),
        "lsd_4_8k_db": band_lsd(reference_mag, processed_mag, frequencies,
                                *OUT_BAND_HZ, include_high=True),
        "retained_bandwidth_hz": retained_bandwidth_hz,
        "hf_power_change_db": hf_power_change_db,
        "dfreq_0_4k_db": float(np.mean(dfrequency[frequencies < 4000])),
        "dfreq_4_8k_db": float(np.mean(dfrequency[frequencies >= 4000])),
    }
    return row, dfrequency, result.packets


# ==================================================
# Diagnostics: link to the frozen encoder
# ==================================================

def diagnostic_rows(waveform, sample_rate, ids, controlled_packets) -> list[dict]:
    rows = []
    for bitrate_bps, forced_cell in [(12000, "opus_12k_wb"), (8000, "opus_8k_nb")]:
        auto = opus_direct.encode(
            waveform, sample_rate,
            opus_direct.EncoderSettings(bitrate_bps=bitrate_bps, bandwidth="AUTO"),
        )
        ffmpeg_size, ffmpeg_packets = run_reproduce.encode_opus_file(
            waveform, sample_rate, f"{bitrate_bps // 1000}k"
        )
        forced = controlled_packets[forced_cell]
        rows.append({
            **ids,
            "nominal_bitrate_kbps": bitrate_bps / 1000.0,
            "auto_configurations": json.dumps(dict(collections.Counter(
                opus_direct.packet_info(p)["configuration"] for p in auto.packets))),
            "ffmpeg_configurations": json.dumps(dict(collections.Counter(
                opus_direct.packet_info(p)["configuration"] for p in ffmpeg_packets))),
            "direct_auto_packets": len(auto.packets),
            "ffmpeg_packets": len(ffmpeg_packets),
            "direct_auto_equals_ffmpeg": auto.packets == ffmpeg_packets,
            "identical_packets_auto_vs_ffmpeg": sum(
                a == b for a, b in zip(auto.packets, ffmpeg_packets)),
            "direct_auto_file_bytes": len(auto.ogg),
            "ffmpeg_file_bytes": ffmpeg_size,
            "forced_cell": forced_cell,
            "forced_equals_auto": forced == auto.packets,
            "identical_packets_forced_vs_auto": sum(
                a == b for a, b in zip(forced, auto.packets)),
        })
    return rows


# ==================================================
# Summaries and gates
# ==================================================

def summarise(files: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:

    summary_rows = []
    for cell, group in files.groupby("cell", sort=False):
        row = {
            "cell": cell,
            "files": len(group),
            "packets": int(group["num_packets"].sum()),
            "packet_configurations": json.dumps(dict(sum(
                (collections.Counter(json.loads(c)) for c in group["packet_configurations"]),
                collections.Counter(),
            ))),
            "share_requested_bandwidth": group["packets_in_requested_bandwidth"].sum()
            / group["num_packets"].sum(),
            "aggregate_measured_kbps": 8 * group["file_size_bytes"].sum()
            / group["duration_seconds"].sum() / 1000,
            "aggregate_payload_kbps": 8 * group["payload_bytes"].sum()
            / group["duration_seconds"].sum() / 1000,
            "lags": json.dumps(dict(collections.Counter(
                int(v) for v in group["alignment_lag_samples"]))),
        }
        for field in [
            "measured_bitrate_kbps", "payload_bitrate_kbps", "lsd_db",
            "lsd_0_4k_db", "lsd_4_8k_db", "retained_bandwidth_hz",
            "hf_power_change_db", "spectral_distortion",
        ]:
            for stat, value in distribution(group[field]).items():
                row[f"{field}_{stat}"] = value
        summary_rows.append(row)

    paired_rows = []
    for nominal, group in files.groupby("nominal_bitrate_kbps", sort=False):
        wb = group[group["requested_bandwidth"] == "WB"].set_index("dataset_index")
        nb = group[group["requested_bandwidth"] == "NB"].set_index("dataset_index")
        nb = nb.loc[wb.index]
        for index in wb.index:
            paired_rows.append({
                "dataset_index": index,
                "speaker_id": wb.loc[index, "speaker_id"],
                "nominal_bitrate_kbps": nominal,
                "wb_measured_kbps": wb.loc[index, "measured_bitrate_kbps"],
                "nb_measured_kbps": nb.loc[index, "measured_bitrate_kbps"],
                "wb_payload_kbps": wb.loc[index, "payload_bitrate_kbps"],
                "nb_payload_kbps": nb.loc[index, "payload_bitrate_kbps"],
                "measured_gap_rel": (wb.loc[index, "measured_bitrate_kbps"]
                                     - nb.loc[index, "measured_bitrate_kbps"]) / nominal,
                "payload_gap_rel": (wb.loc[index, "payload_bitrate_kbps"]
                                    - nb.loc[index, "payload_bitrate_kbps"]) / nominal,
                "retained_bw_diff_hz": wb.loc[index, "retained_bandwidth_hz"]
                - nb.loc[index, "retained_bandwidth_hz"],
                "hf_power_diff_db": wb.loc[index, "hf_power_change_db"]
                - nb.loc[index, "hf_power_change_db"],
                "lsd_0_4k_diff_db": wb.loc[index, "lsd_0_4k_db"]
                - nb.loc[index, "lsd_0_4k_db"],
            })

    return pd.DataFrame(summary_rows), pd.DataFrame(paired_rows)


def settings_differences(files: pd.DataFrame) -> list[str]:
    """Settings or queried values that differ between cells of one utterance."""
    setting_columns = [c for c in files.columns if c.startswith("setting_")]
    query_columns = [c for c in files.columns if c.startswith("queried_")]
    allowed = (
        {f"setting_{k}" for k in VARIED_SETTINGS}
        | {f"queried_{k}" for k in VARIED_QUERIES}
    )
    differing = set()
    for _, group in files.groupby("dataset_index"):
        for column in setting_columns + query_columns + [
            "lookahead_samples", "pre_skip_48k", "padding_samples",
            "end_trim_48k", "num_packets",
        ]:
            if group[column].nunique() > 1 and column not in allowed:
                differing.add(column)
    return sorted(differing)


def evaluate_gates(files: pd.DataFrame, summary: pd.DataFrame,
                   paired: pd.DataFrame) -> pd.DataFrame:

    gates = []

    def gate(number, name, passed, evidence):
        gates.append({"gate": number, "name": name,
                      "status": "PASS" if passed else "FAIL", "evidence": evidence})

    wb8 = files[files["cell"] == "opus_8k_wb"]
    gate(1, "forced 8 kbps WB reliable on every utterance",
         bool((wb8["share_requested_bandwidth"] == 1.0).all()),
         f"{int((wb8['share_requested_bandwidth'] == 1.0).sum())}/{len(wb8)} files "
         f"100% WB; {int(wb8['packets_in_requested_bandwidth'].sum())}/"
         f"{int(wb8['num_packets'].sum())} packets WB")

    all_in_band = bool((files["share_requested_bandwidth"] == 1.0).all())
    gate(2, "every packet of every cell in the requested bandwidth", all_in_band,
         "; ".join(
             f"{r.cell}: {r.share_requested_bandwidth:.4f}"
             for r in summary.itertuples()
         ))

    bitrate_evidence = []
    bitrate_pass = True
    for nominal, group in paired.groupby("nominal_bitrate_kbps", sort=False):
        for kind in ["measured", "payload"]:
            wb_cell = summary[summary["cell"] == f"opus_{int(nominal)}k_wb"].iloc[0]
            nb_cell = summary[summary["cell"] == f"opus_{int(nominal)}k_nb"].iloc[0]
            aggregate_gap = abs(
                wb_cell[f"aggregate_{kind}_kbps"] - nb_cell[f"aggregate_{kind}_kbps"]
            ) / nominal
            median_gap = float(np.median(np.abs(group[f"{kind}_gap_rel"])))
            bitrate_pass &= (aggregate_gap <= GATE_BITRATE_AGGREGATE_GAP
                             and median_gap <= GATE_BITRATE_MEDIAN_GAP)
            bitrate_evidence.append(
                f"{int(nominal)}k {kind}: aggregate gap {aggregate_gap:.2%}, "
                f"median |gap| {median_gap:.2%}"
            )
    gate(3, "WB and NB measured bitrate comparable at each nominal rate "
         f"(aggregate and median gap <= {GATE_BITRATE_AGGREGATE_GAP:.0%})",
         bitrate_pass, "; ".join(bitrate_evidence))

    decode_ok = bool(
        (files["decoded_sample_rate"] == 48000).all()
        and files["ogg_packets_roundtrip"].all()
        and files["libopus_parser_agrees"].all()
        and files["decode_repeat_identical"].all()
    )
    gate(4, "all cells decode through the frozen torchaudio.load path", decode_ok,
         f"decoded rate {sorted(files['decoded_sample_rate'].unique())}; Ogg packet "
         f"round trip {int(files['ogg_packets_roundtrip'].sum())}/{len(files)}; "
         f"TOC parsers agree {int(files['libopus_parser_agrees'].sum())}/{len(files)}")

    lengths_ok = bool(
        files["decoded_length_matches_input"].all()
        and (files["resampled_num_samples"] == files["num_input_samples"]).all()
        and files["reencode_identical"].all()
        and (files["opus_head_pre_skip"] == files["pre_skip_48k"]).all()
        and (files["ogg_last_granule"] == files["final_granule_48k"]).all()
        and (files["alignment_lag_samples"].abs() <= GATE_MAX_ABS_LAG_SAMPLES).all()
    )
    gate(5, "decoded length, trimming, alignment understood and reproducible",
         lengths_ok,
         f"decoded 48k length = 3N in {int(files['decoded_length_matches_input'].sum())}"
         f"/{len(files)}; re-encode identical {int(files['reencode_identical'].sum())}"
         f"/{len(files)}; pre-skip {sorted(files['pre_skip_48k'].unique())}; lags by "
         "cell " + "; ".join(f"{r.cell} {r.lags}" for r in summary.itertuples()))

    spectral_evidence = []
    spectral_pass = True
    for nominal, group in paired.groupby("nominal_bitrate_kbps", sort=False):
        bw_diff = float(group["retained_bw_diff_hz"].median())
        hf_diff = float(group["hf_power_diff_db"].median())
        spectral_pass &= (bw_diff >= GATE_RETAINED_BW_DIFF_HZ
                          and hf_diff >= GATE_HF_POWER_DIFF_DB)
        spectral_evidence.append(
            f"{int(nominal)}k: median WB-NB retained bandwidth {bw_diff:.0f} Hz "
            f"({int((group['retained_bw_diff_hz'] >= GATE_RETAINED_BW_DIFF_HZ).sum())}"
            f"/{len(group)} utterances >= {GATE_RETAINED_BW_DIFF_HZ:.0f}), "
            f"4-8 kHz power {hf_diff:.1f} dB "
            f"({int((group['hf_power_diff_db'] >= GATE_HF_POWER_DIFF_DB).sum())}"
            f"/{len(group)} >= {GATE_HF_POWER_DIFF_DB:.0f})"
        )
    gate(6, "WB vs NB spectral difference measurable", spectral_pass,
         "; ".join(spectral_evidence))

    differing = settings_differences(files)
    silk = bool(files["all_packets_silk"].all())
    unpadded = bool(files["all_single_frame"].all()
                    and (files["unpadded_payload_bytes"] == files["payload_bytes"]).all())
    gate(7, "no hidden encoder difference between cells except bitrate and bandwidth",
         not differing and silk and unpadded,
         f"differing settings/queries beyond bitrate and bandwidth: {differing or 'none'}; "
         f"coding mode SILK in all packets of all cells: {silk}; "
         f"all packets single-frame without padding (payload = coded bits): {unpadded}")

    return pd.DataFrame(gates)


# ==================================================
# Report
# ==================================================

def bitrate_mode_summary(rows: pd.DataFrame) -> pd.DataFrame:
    """WB vs NB bitrate gap and distortion under each bitrate mode (diagnostic)."""
    out = []
    for (mode, nominal), group in rows.groupby(["bitrate_mode", "nominal_bitrate_kbps"],
                                              sort=False):
        wb = group[group["requested_bandwidth"] == "WB"].set_index("dataset_index")
        nb = group[group["requested_bandwidth"] == "NB"].set_index("dataset_index")
        nb = nb.loc[wb.index]

        def aggregate(frame, column="payload_bytes"):
            return 8 * frame[column].sum() / frame["duration_seconds"].sum() / 1000

        gaps = (wb["payload_bitrate_kbps"] - nb["payload_bitrate_kbps"]) / nominal
        unpadded_gaps = (wb["unpadded_bitrate_kbps"] - nb["unpadded_bitrate_kbps"]) / nominal
        out.append({
            "bitrate_mode": mode,
            "nominal_kbps": nominal,
            "wb_payload_kbps": aggregate(wb),
            "nb_payload_kbps": aggregate(nb),
            "aggregate_gap_pct": (aggregate(wb) - aggregate(nb)) / nominal * 100,
            "median_gap_pct": float(np.median(gaps)) * 100,
            "max_abs_gap_pct": float(np.max(np.abs(gaps))) * 100,
            "wb_unpadded_kbps": aggregate(wb, "unpadded_payload_bytes"),
            "nb_unpadded_kbps": aggregate(nb, "unpadded_payload_bytes"),
            "unpadded_median_gap_pct": float(np.median(unpadded_gaps)) * 100,
            "share_padded_packets": float(
                group["packets_code_nonzero"].sum() / group["num_packets"].sum()),
            "min_share_requested_bandwidth": float(group["share_requested_bandwidth"].min()),
            "all_packets_silk": bool(group["all_packets_silk"].all()),
            "wb_lsd_0_4k_median": float(wb["lsd_0_4k_db"].median()),
            "nb_lsd_0_4k_median": float(nb["lsd_0_4k_db"].median()),
            "wb_lsd_median": float(wb["lsd_db"].median()),
            "nb_lsd_median": float(nb["lsd_db"].median()),
        })
    return pd.DataFrame(out)


def write_report(path, files, summary, paired, diagnostics, gates, settings_record,
                 modes):

    verdict = "PASS" if (gates["status"] == "PASS").all() else "FAIL"
    table = run_reproduce.markdown_table

    bitrate_columns = ["cell", "files", "aggregate_measured_kbps", "aggregate_payload_kbps"] + [
        f"measured_bitrate_kbps_{s}" for s in ["mean", "sd", "min", "median", "max"]
    ]
    signal_columns = ["cell"] + [
        f"{field}_median" for field in [
            "lsd_db", "lsd_0_4k_db", "lsd_4_8k_db", "retained_bandwidth_hz",
            "hf_power_change_db",
        ]
    ]
    gap_rows = []
    for nominal, group in paired.groupby("nominal_bitrate_kbps", sort=False):
        for kind in ["measured", "payload"]:
            gaps = group[f"{kind}_gap_rel"] * 100
            gap_rows.append({
                "nominal_kbps": nominal, "bitrate": kind,
                **{f"gap_pct_{k}": v for k, v in distribution(gaps).items()},
            })

    diag_summary = (
        diagnostics.groupby("nominal_bitrate_kbps")
        .agg(
            utterances=("dataset_index", "count"),
            auto_equals_ffmpeg=("direct_auto_equals_ffmpeg", "sum"),
            forced_equals_auto=("forced_equals_auto", "sum"),
            forced_cell=("forced_cell", "first"),
        )
        .reset_index()
    )

    lines = [
        "# Stage 2A: direct-libopus validation (dev-clean)",
        "",
        f"**Verdict: {verdict}** ({int((gates['status'] == 'PASS').sum())}/"
        f"{len(gates)} gates passed)",
        "",
        f"Data: {files['dataset_index'].nunique()} dev-clean utterances, one per "
        f"speaker (seed {DEV_SEED}), {files['duration_seconds'].groupby(files['dataset_index']).first().sum():.0f} s.",
        "",
        "## Gates",
        "",
        table(gates),
        "",
        "## Encoder settings (identical in all cells except bitrate and bandwidth)",
        "",
        "```json",
        json.dumps(settings_record, indent=2),
        "```",
        "",
        "## Packet configurations",
        "",
        table(summary[["cell", "files", "packets", "packet_configurations",
                       "share_requested_bandwidth"]]),
        "",
        "## Measured bitrate (kbps; measured = file size, frozen definition)",
        "",
        table(summary[bitrate_columns]),
        "",
        "Paired WB - NB gap, % of nominal:",
        "",
        table(pd.DataFrame(gap_rows)),
        "",
        "## Signal level (medians over utterances)",
        "",
        table(summary[signal_columns]),
        "",
        "## Alignment and trimming",
        "",
        table(summary[["cell", "lags"]]),
        "",
        f"Lookahead {sorted(files['lookahead_samples'].unique())} samples at 16 kHz, "
        f"pre-skip {sorted(files['pre_skip_48k'].unique())} at 48 kHz, end trim "
        f"{files['end_trim_48k'].min()}-{files['end_trim_48k'].max()} samples at 48 kHz; "
        "decoded length equals 3 x input length for "
        f"{int(files['decoded_length_matches_input'].sum())}/{len(files)} files.",
        "",
        "## Diagnostics: link to the frozen ffmpeg encoder",
        "",
        table(diag_summary),
        "",
        "## Diagnostic: bitrate mode and the WB vs NB bitrate gap",
        "",
        "The design uses unconstrained VBR (the frozen setting). Constrained "
        "VBR and CBR are shown only to judge whether a controlled bitrate mode "
        "is needed; payload bitrate excludes Ogg overhead.",
        "",
        table(modes),
        "",
    ]
    path.write_text("\n".join(lines))


# ==================================================
# Main
# ==================================================

def main() -> int:

    os.chdir(REPO_ROOT)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    environment = run_reproduce.collect_environment()
    environment["libopus_loaded_by_opus_direct"] = {
        "path": opus_direct.libopus_path(), "version": opus_direct.libopus_version(),
    }
    environment["dev_data"] = {
        "subset": DEV_SUBSET,
        "root": os.path.realpath(os.path.join(common.DATA_ROOT, "LibriSpeech", DEV_SUBSET)),
    }
    (OUTPUT_DIR / "environment.json").write_text(json.dumps(environment, indent=2))

    base = opus_direct.EncoderSettings(bitrate_bps=0)
    settings_record = {
        "common_settings": {
            k: v for k, v in asdict(base).items() if k not in VARIED_SETTINGS
        },
        "frame_samples": base.frame_samples,
        "ctl_order": list(base.ctl_values()),
        "input_format": "int16 PCM via opus_encode (exact; source is 16-bit FLAC)",
        "cells": CONTROLLED_CELLS,
        "ogg": {
            "serial": opus_direct.OGG_SERIAL,
            "packets_per_page": opus_direct.OGG_PACKETS_PER_PAGE,
            "opus_tags_comments": opus_direct.OPUS_TAGS_COMMENTS,
        },
        "libopus": opus_direct.libopus_version(),
    }
    (OUTPUT_DIR / "encoder_settings.json").write_text(json.dumps(settings_record, indent=2))

    dataset = torchaudio.datasets.LIBRISPEECH(common.DATA_ROOT, url=DEV_SUBSET,
                                              download=False)
    indices = select_dev_utterances(dataset)

    file_rows, diag, mode_rows = [], [], []
    curves = collections.defaultdict(list)

    for index in tqdm(indices, desc=DEV_SUBSET, unit="utt"):
        waveform, sample_rate, transcript, speaker_id, chapter_id, utterance_id = (
            dataset[index]
        )
        ids = {"dataset": DEV_SUBSET, "dataset_index": index, "speaker_id": speaker_id,
               "chapter_id": chapter_id, "utterance_id": utterance_id}

        controlled_packets = {}
        for cell in CONTROLLED_CELLS:
            row, dfrequency, packets = validate_file(waveform, sample_rate, ids, cell)
            file_rows.append(row)
            curves[cell["cell"]].append(dfrequency)
            controlled_packets[cell["cell"]] = packets

        diag.extend(diagnostic_rows(waveform, sample_rate, ids, controlled_packets))

        for mode in DIAGNOSTIC_BITRATE_MODES:
            for cell in CONTROLLED_CELLS:
                mode_rows.append(
                    validate_file(waveform, sample_rate, ids, cell, bitrate_mode=mode)[0]
                )

    files = pd.DataFrame(file_rows)
    modes = bitrate_mode_summary(pd.concat([files, pd.DataFrame(mode_rows)]))
    diagnostics = pd.DataFrame(diag)
    summary, paired = summarise(files)
    gates = evaluate_gates(files, summary, paired)

    frequencies = np.linspace(0, 8000, common.N_FFT // 2 + 1)
    frequency_df = pd.concat([
        pd.DataFrame({
            "cell": cell, "frequency_hz": frequencies,
            "mean_distortion_db": np.mean(np.stack(values), axis=0),
            "median_distortion_db": np.median(np.stack(values), axis=0),
        })
        for cell, values in curves.items()
    ])

    files.to_csv(OUTPUT_DIR / "file_rows.csv", index=False)
    diagnostics.to_csv(OUTPUT_DIR / "diagnostic_rows.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "cell_summary.csv", index=False)
    paired.to_csv(OUTPUT_DIR / "paired_bitrate.csv", index=False)
    frequency_df.to_csv(OUTPUT_DIR / "frequency_distortion.csv", index=False)
    gates.to_csv(OUTPUT_DIR / "gates.csv", index=False)
    pd.DataFrame(mode_rows).to_csv(OUTPUT_DIR / "bitrate_mode_rows.csv", index=False)
    modes.to_csv(OUTPUT_DIR / "bitrate_mode_summary.csv", index=False)
    write_report(OUTPUT_DIR / "validation_report.md", files, summary, paired,
                 diagnostics, gates, settings_record, modes)

    print(gates.to_string(index=False))
    print(f"Report: {OUTPUT_DIR / 'validation_report.md'}")
    return 0 if (gates["status"] == "PASS").all() else 1


if __name__ == "__main__":
    sys.exit(main())
