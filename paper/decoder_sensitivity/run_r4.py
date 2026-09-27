"""
R4 runner: reference-decoder total-penalty sensitivity (written at RS1, after the plan was sealed).

Commands, strictly in the order of the frozen plan (00_R4_PLAN.md):

    calibrate decode   RS1  calibration set only, no ASR: regenerate the OPUS Ogg files and decode
                            them with the libopus reference decoder, twice (G1-G5 analogues, G6a),
                            the descriptive diagnostics, and the reproduction of R1's E2 audio.
    calibrate asr      RS1  calibration set only: G8 (the frozen Stage 3 pipeline reproduces the
                            sealed Stage 3 calibration outputs) and G6b (OPUS_LIBOPUS recognised,
                            the first 2 utterances again); no WER is compared.
    validate           RS3  confirmation set, no ASR: G1-G5, G7 and G9, descriptive diagnostics.
    run                RS4  recognition of OPUS_LIBOPUS, once.
    analyse            RS5  T_ffmpeg, T_libopus and D with intervals; outcome per recogniser.

calibrate needs the sealed plan; validate, run and analyse need the committed plan and the committed
code freeze (r4_design.py freeze-code), i.e. the author's approval of the frozen plan.

OPUS_LIBOPUS is built only from frozen functions: the Stage 3 encoder call (opus_direct.encode with
the Stage 3 OPUS settings), R1's reference decoder (reviewer_pipeline.reference_decode) and the
Stage 3 resampler (reviewer_pipeline.to_16k). The FFmpeg path (opus_direct.decode_frozen_path) is
run only for the descriptive decoder-difference SNR.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "reviewer_sensitivity"), str(HERE.parent / "taslp_upgrade"),
                str(HERE.parent)]

import numpy as np                   # noqa: E402
import pandas as pd                  # noqa: E402
import torch                         # noqa: E402
import torchaudio                    # noqa: E402
from tqdm import tqdm                # noqa: E402

import common                        # noqa: E402
import opus_direct                   # noqa: E402
import r4_design as design           # noqa: E402
import reviewer_pipeline as rp       # noqa: E402
import run_lowpass_validation as s2b  # noqa: E402
import run_stage3 as s3              # noqa: E402
import stage3_audio as audio         # noqa: E402
import upgrade_design as upgrade     # noqa: E402
import upgrade_pipeline as upipe     # noqa: E402
import upgrade_stats as ustats       # noqa: E402

SAMPLE_RATE = audio.SAMPLE_RATE
VALIDATION = design.RESULTS / "validation"
VALIDATION_REPORT = VALIDATION / "validation_report.json"
VALIDATION_ROWS = VALIDATION / "validation_rows.csv"
RAW = design.RESULTS / "raw"
ANALYSIS = design.RESULTS / "analysis"
PAIRS = [(design.REF, design.OPUS_FFMPEG), (design.REF, design.OPUS_LIBOPUS)]
MIN_FREE_GPU_GIB = 12.0              # the GPU is shared: recognition waits for a free device


# ==================================================
# One utterance: the frozen bitstream, both decoders, checks and diagnostics
# ==================================================

def decode(waveform: torch.Tensor) -> dict:
    """One frozen encode; its Ogg bytes decoded by the libopus reference decoder and by FFmpeg."""
    result = opus_direct.encode(waveform, SAMPLE_RATE, design.OPUS_SETTINGS)
    pcm48, info = rp.reference_decode(result.ogg)            # raises on any decoder error (G2)
    libopus = rp.to_16k(torch.from_numpy(pcm48).unsqueeze(0))
    ffmpeg48, rate = opus_direct.decode_frozen_path(result.ogg)
    ffmpeg = ffmpeg48 if rate == SAMPLE_RATE else torchaudio.functional.resample(ffmpeg48, rate, SAMPLE_RATE)
    return {"result": result, "pcm48": pcm48, "info": info, "libopus": libopus.to(torch.float32),
            "ffmpeg": ffmpeg.to(torch.float32), "ffmpeg_length_48k": int(ffmpeg48.shape[-1])}


def libopus_only(waveform: torch.Tensor) -> tuple[torch.Tensor, dict]:
    """OPUS_LIBOPUS for recognition (RS1 asr, RS4): the same frozen steps, without the FFmpeg path."""
    result = opus_direct.encode(waveform, SAMPLE_RATE, design.OPUS_SETTINGS)
    pcm48, _ = rp.reference_decode(result.ogg)
    return rp.to_16k(torch.from_numpy(pcm48).unsqueeze(0)).to(torch.float32), {
        "ogg_sha256": hashlib.sha256(result.ogg).hexdigest()}


def snr_db(a: np.ndarray, b: np.ndarray) -> float:
    noise = float(np.sum((b - a) ** 2))
    return float("inf") if noise == 0 else float(10 * np.log10(np.sum(a ** 2) / noise))


def decoder_difference(ffmpeg: torch.Tensor, libopus: torch.Tensor) -> dict:
    """Descriptive: SNR of libopus against FFmpeg, unaligned and after the better one-sample shift.
    Shift +1: libopus sample n+1 against FFmpeg sample n; shift -1: libopus n against FFmpeg n+1."""
    a = ffmpeg.detach().cpu().double().numpy().reshape(-1)
    b = libopus.detach().cpu().double().numpy().reshape(-1)
    if a.size != b.size:
        return {"same_length": False}
    shifted = {1: snr_db(a[:-1], b[1:]), -1: snr_db(a[1:], b[:-1])}
    best = max(shifted, key=shifted.get)
    return {"same_length": True, "bit_identical": bool(np.array_equal(a, b)),
            "snr_unaligned_db": snr_db(a, b), "snr_one_sample_db": shifted[best], "one_sample_shift": int(best),
            "max_abs_difference": float(np.max(np.abs(b - a)))}


def utterance_row(entry: dict, waveform: torch.Tensor, d: dict, stage3: dict, r1_hash: str | None) -> dict:
    """Every gate quantity and descriptive diagnostic of one utterance (no ASR)."""
    result, info, n_ref = d["result"], d["info"], waveform.shape[-1]
    lib = upipe.audio_row(design.OPUS_LIBOPUS, d["libopus"], waveform, {})
    ffm = upipe.audio_row(design.OPUS_FFMPEG, d["ffmpeg"], waveform, {})
    ogg_sha256 = hashlib.sha256(result.ogg).hexdigest()
    return {
        "utterance": entry["utterance"], "subset": entry["subset"], "speaker_id": entry["speaker_id"],
        "num_samples_ref": n_ref,
        # G1
        "ogg_sha256": ogg_sha256, "stage3_ogg_sha256": stage3["ogg_sha256"],
        "g1_ogg_identical": ogg_sha256 == stage3["ogg_sha256"],
        # G2
        "num_packets": len(result.packets), "packets_identical": info["packets"] == result.packets,
        "samples_per_packet": ";".join(str(n) for n in info["samples_per_packet"]),
        # G3
        "output_gain": int(info["output_gain"]), "pre_skip": int(info["pre_skip"]),
        "lookahead_samples": int(result.lookahead_samples),
        "pre_skip_is_3x_lookahead": int(info["pre_skip"]) == 3 * int(result.lookahead_samples),
        "final_granule": int(info["final_granule"]), "length_48k": int(d["pcm48"].size),
        "length_48k_convention": int(info["final_granule"]) - int(info["pre_skip"]),
        "ffmpeg_length_48k": d["ffmpeg_length_48k"], "length_16k": lib["num_samples"],
        "length_equals_ref": bool(lib["length_equals_ref"]),
        # G4
        "nonfinite_48k": int(np.sum(~np.isfinite(d["pcm48"]))), "nonfinite_16k": int(lib["nonfinite_count"]),
        # outputs and reproduction checks (reported, not gates)
        "waveform_sha256": lib["waveform_sha256"], "r1_refdec_waveform_sha256": r1_hash,
        "r1_refdec_identical": None if r1_hash is None else lib["waveform_sha256"] == r1_hash,
        "ffmpeg_waveform_sha256": ffm["waveform_sha256"], "stage3_opus_waveform_sha256": stage3["waveform_sha256"],
        "ffmpeg_identical_to_stage3": ffm["waveform_sha256"] == stage3["waveform_sha256"],
        # descriptive diagnostics
        "libopus_lag_vs_ref_samples": lib["lag_vs_ref_samples"], "ffmpeg_lag_vs_ref_samples": ffm["lag_vs_ref_samples"],
        "libopus_rms_change_db": lib["rms_change_db"], "ffmpeg_rms_change_db": ffm["rms_change_db"],
        "libopus_peak": lib["peak"], "libopus_clip_count": lib["clip_count"],
        **{f"decoder_{k}": v for k, v in decoder_difference(d["ffmpeg"], d["libopus"]).items()},
        "decoder": opus_direct.libopus_version(),
    }


def gate_results(rows: pd.DataFrame, n_expected: int, errors: list[dict]) -> dict:
    """G1-G4 over a set of utterance rows (a gate passes only if every utterance passes)."""
    spp = sorted(rows["samples_per_packet"].astype(str).unique().tolist())
    g = {
        "G1": {"pass": bool(len(rows) == n_expected and rows["g1_ogg_identical"].all()),
               "identical": int(rows["g1_ogg_identical"].sum()), "of": n_expected},
        "G2": {"pass": bool(not errors and len(rows) == n_expected and rows["packets_identical"].all()),
               "decoded": int(len(rows)), "decode_errors": errors,
               "packets_identical": int(rows["packets_identical"].sum()), "of": n_expected},
        "G3": {"output_gain_zero": bool((rows["output_gain"] == 0).all()),
               "pre_skip_is_3x_lookahead": bool(rows["pre_skip_is_3x_lookahead"].all()),
               "samples_per_packet": spp,
               "length_48k_follows_convention": bool((rows["length_48k"] == rows["length_48k_convention"]).all()),
               "length_48k_is_3x_ref": bool((rows["length_48k"] == 3 * rows["num_samples_ref"]).all()),
               "length_48k_equals_ffmpeg": bool((rows["length_48k"] == rows["ffmpeg_length_48k"]).all()),
               "length_16k_equals_ref": bool(rows["length_equals_ref"].all())},
        "G4": {"nonfinite_48k": int(rows["nonfinite_48k"].sum()), "nonfinite_16k": int(rows["nonfinite_16k"].sum())},
    }
    g["G3"]["pass"] = bool(all(v for k, v in g["G3"].items() if k != "samples_per_packet")
                           and spp == [str(design.SAMPLES_PER_PACKET_48K)])
    g["G4"]["pass"] = bool(g["G4"]["nonfinite_48k"] == 0 and g["G4"]["nonfinite_16k"] == 0)
    return g


def band_power_db(acc: s2b.TransferAccumulator, band: tuple[float, float]) -> float:
    mask = (s2b.FREQS >= band[0]) & (s2b.FREQS <= band[1])
    return float(10 * np.log10(acc.syy[mask].sum() / acc.sxx[mask].sum()))


def diagnostics(rows: pd.DataFrame, accumulators: dict) -> dict:
    """Descriptive only: lags, RMS change, decoder-difference SNR, pooled 4-5 kHz / 4-8 kHz power, mirror coherence."""
    out = {}
    for name, prefix in [(design.OPUS_LIBOPUS, "libopus"), (design.OPUS_FFMPEG, "ffmpeg")]:
        rms = rows[f"{prefix}_rms_change_db"]
        pooled = accumulators[(design.REF, name)].results()
        out[name] = {
            "lag_vs_ref_counts": {str(k): int(v) for k, v in
                                  rows[f"{prefix}_lag_vs_ref_samples"].value_counts().sort_index().items()},
            "rms_change_db": {"median": float(rms.median()), "p05": float(rms.quantile(0.05)),
                              "p95": float(rms.quantile(0.95))},
            "pooled_power_4000_5000_db": band_power_db(accumulators[(design.REF, name)], design.POWER_BAND_HZ),
            "pooled_total_hf_power_4000_8000_db": pooled["total_hf_power_db"],
            "pooled_mirror_coherence_4100_4900": pooled["image_coherence_4100_4900"],
        }
    shifts = rows["decoder_one_sample_shift"].value_counts().sort_index()
    out["decoder_difference"] = {
        "bit_identical": int(rows["decoder_bit_identical"].sum()),
        "snr_unaligned_db": {"median": float(rows["decoder_snr_unaligned_db"].median()),
                             "min": float(rows["decoder_snr_unaligned_db"].min())},
        "snr_one_sample_db": {"median": float(rows["decoder_snr_one_sample_db"].median()),
                              "min": float(rows["decoder_snr_one_sample_db"].min())},
        "one_sample_shift_counts": {str(k): int(v) for k, v in shifts.items()},
        "max_abs_difference": float(rows["decoder_max_abs_difference"].max()),
    }
    out["reproduction"] = {
        "ffmpeg_identical_to_stage3": int(rows["ffmpeg_identical_to_stage3"].sum()),
        "libopus_identical_to_r1_refdec": int(rows["r1_refdec_identical"].fillna(False).astype(bool).sum()),
        "r1_refdec_available": int(rows["r1_refdec_waveform_sha256"].notna().sum()),
        "of": int(len(rows)),
    }
    return out


def process(selection: list[dict], stage3: dict, r1: dict, desc: str) -> tuple[pd.DataFrame, dict, list[dict]]:
    """Every utterance of a selection; a decoder error is recorded (it fails G2) instead of aborting."""
    accumulators = upipe.new_accumulators(PAIRS)
    rows, errors = [], []
    for entry in tqdm(selection, desc=desc, unit="utt"):
        waveform = upipe.load_reference(entry)
        try:
            d = decode(waveform)
        except RuntimeError as error:
            errors.append({"utterance": entry["utterance"], "error": str(error)})
            continue
        rows.append(utterance_row(entry, waveform, d, stage3[entry["utterance"]], r1.get(entry["utterance"])))
        for name, key in [(design.OPUS_FFMPEG, "ffmpeg"), (design.OPUS_LIBOPUS, "libopus")]:
            aligned_ref, aligned_proc, _ = common.align_waveforms(waveform, d[key])
            accumulators[(design.REF, name)].add(aligned_ref, aligned_proc)
    return pd.DataFrame(rows), accumulators, errors


# ==================================================
# Sealed inputs
# ==================================================

def verified_csv(directory: Path, name: str, **kwargs) -> pd.DataFrame:
    manifest = s3.read_sealed(directory / "outputs_sha256.json", "outputs_sha256")
    if s3.file_sha256(directory / name) != manifest["files"][name]:
        raise RuntimeError(f"{directory / name} differs from its sealed manifest")
    return pd.read_csv(directory / name, **kwargs)


def stage3_opus(directory: Path) -> dict:
    frame = verified_csv(directory, "audio_manifest.csv")
    frame = frame[frame["condition"] == design.STAGE3_LABEL[design.OPUS_FFMPEG]]
    return {r["utterance"]: {"ogg_sha256": r["ogg_sha256"], "waveform_sha256": r["waveform_sha256"]}
            for r in frame.to_dict(orient="records")}


def r1_refdec(path: Path, sealed_sha256: str) -> dict:
    if s3.file_sha256(path) != sealed_sha256:
        raise RuntimeError(f"{path} differs from its sealed record")
    frame = pd.read_csv(path)
    frame = frame[frame["condition"] == "OPUS_REFDEC"]
    return dict(zip(frame["utterance"], frame["waveform_sha256"]))


def r1_calibration_file(name: str) -> Path:
    path = design.R1_E2_AUDIO.parent / name
    if s3.file_sha256(path) != s3.read_sealed(design.R1_CALIBRATION_REPORT, "report_sha256")["files"][name]:
        raise RuntimeError(f"{path} differs from the sealed R1 calibration report")
    return path


def r1_e2_sha256() -> str:
    return s3.read_sealed(design.R1_CALIBRATION_REPORT, "report_sha256")["files"][design.R1_E2_AUDIO.name]


def r1_confirmation_rows_sha256() -> str:
    return s3.read_sealed(design.R1_CONFIRMATION_REPORT, "report_sha256")["rows_sha256"]


def stage3_metrics() -> pd.DataFrame:
    """Sealed Stage 3 confirmation metrics of REF and OPUS (renamed OPUS_FFMPEG)."""
    frame = verified_csv(upgrade.S3_CONFIRMATION, "utterance_metrics.csv", keep_default_na=False)
    labels = {v: k for k, v in design.STAGE3_LABEL.items()}
    frame = frame[frame["condition"].isin(labels)].copy()
    frame["condition"] = frame["condition"].map(labels)
    return frame


# ==================================================
# Statistics (frozen upgrade_stats machinery, Stage 3's seed on Stage 3's speakers)
# ==================================================

def r4_quantities(paired, seed: int = design.SEED, n_boot: int = design.N_BOOT) -> list[dict]:
    rep = ustats.Replicates(paired, ustats.replicate_weights(paired, seed, n_boot))
    present = list(paired.values)
    rows = [ustats.interval_row(f"wer_{c}", "micro", rep.micro(c), "pp", 100.0) for c in present]
    for name, (a, b) in design.QUANTITIES.items():
        if a in present and b in present:
            rows.append(ustats.interval_row(name, "micro", rep.micro(a) - rep.micro(b), "pp", 100.0))
    return rows


def analyse_table(metrics: pd.DataFrame, conditions: list[str], **kwargs) -> pd.DataFrame:
    return ustats.analyse(metrics, conditions, r4_quantities, design.MODELS, **kwargs)


def anchor_check(table: pd.DataFrame, anchors: dict) -> dict:
    """G9: R4's code reproduces Stage 3's WER(REF), WER(OPUS) and OPUS - REF (estimate and bounds)."""
    worst, cells = 0.0, {}
    for model, scopes in anchors.items():
        for scope, quantities in scopes.items():
            for name, ref in quantities.items():
                got = ustats.lookup(table, model, name, "micro", scope)
                diff = max(abs(got[0] - ref["estimate"]), abs(got[1] - ref["ci"][0]), abs(got[2] - ref["ci"][1]))
                worst = max(worst, diff)
                cells[f"{model}/{scope}/{name}"] = diff
    return {"max_abs_difference_pp": worst, "tolerance_pp": design.ANCHOR_TOLERANCE_PP,
            "pass": bool(worst <= design.ANCHOR_TOLERANCE_PP), "cells": cells}


# ==================================================
# RS1 calibrate (calibration set only)
# ==================================================

def calibrate_decode() -> int:
    spec = design.require_frozen_plan(committed=False)
    path = design.DRY_RUN_PARTS["decode"]
    if path.exists():
        raise RuntimeError(f"{path} exists")
    design.CALIBRATION.mkdir(parents=True, exist_ok=True)
    selection = s3.load_selection("calibration")["utterances"]
    stage3 = stage3_opus(upgrade.S3_CALIBRATION)
    r1 = r1_refdec(design.R1_E2_AUDIO, r1_e2_sha256())
    started = time.time()
    first, accumulators, errors = process(selection, stage3, r1, "RS1 decode, pass 1")
    second, _, errors_second = process(selection, stage3, r1, "RS1 decode, pass 2")
    seconds = time.time() - started
    gates = gate_results(first, len(selection), errors + errors_second)
    gates["G5"] = {"environment_differences": design.environment_unchanged(spec),
                   "decoder": opus_direct.libopus_version(), "decoder_path": opus_direct.libopus_path()}
    gates["G5"]["pass"] = not gates["G5"]["environment_differences"]
    determinism = {"ogg_identical": bool((first["ogg_sha256"] == second["ogg_sha256"]).all()),
                   "waveforms_identical": bool((first["waveform_sha256"] == second["waveform_sha256"]).all()),
                   "of": len(selection)}
    gates["G6a"] = {**determinism, "pass": determinism["ogg_identical"] and determinism["waveforms_identical"]}
    first.to_csv(design.CALIBRATION / "dry_run_decode_rows.csv", index=False)
    report = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "part": "decode",
        "purpose": "RS1 dry run, calibration set only, no ASR: G1-G5 analogues and G6a on the 20 calibration "
                   "utterances, descriptive diagnostics, reproduction of R1's E2 audio",
        "n_utterances": len(selection), "gates": gates, "diagnostics": diagnostics(first, accumulators),
        "seconds_per_utterance_per_pass": seconds / (2 * len(selection)),
        "rows_sha256": s3.file_sha256(design.CALIBRATION / "dry_run_decode_rows.csv"),
    }
    report["pass"] = all(g["pass"] for g in gates.values())
    digest = s3.write_sealed(path, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], **{k: g["pass"] for k, g in gates.items()},
                      "diagnostics": report["diagnostics"], "report_sha256": digest}, indent=1))
    return 0 if report["pass"] else 1


def free_gpu_gib() -> float:
    free, _ = torch.cuda.mem_get_info()
    return free / 2 ** 30


def environment_g8(pipeline: s3.Pipeline, selection: list[dict]) -> dict:
    """G8: the frozen Stage 3 pipeline, six conditions, against the sealed Stage 3 calibration outputs."""
    started = time.time()
    records = []
    for start in range(0, len(selection), upipe.CHUNK_UTTERANCES):
        records += pipeline.process_chunk("calibration", selection[start:start + upipe.CHUNK_UTTERANCES],
                                          audio.new_accumulators())
    new_audio = pd.DataFrame([r for rec in records for r in rec["audio"]])
    new_asr = pd.DataFrame([r for rec in records for r in rec["asr"]])
    frozen_audio = verified_csv(upgrade.S3_CALIBRATION, "audio_manifest.csv")
    frozen_asr = verified_csv(upgrade.S3_CALIBRATION, "asr_outputs.csv", keep_default_na=False)
    audio_cmp = frozen_audio.merge(new_audio, on=["utterance", "condition"], suffixes=("_frozen", "_new"))
    codec = audio_cmp["ogg_sha256_frozen"].notna()
    asr_cmp = frozen_asr.merge(new_asr, on=["utterance", "condition", "model"], suffixes=("_frozen", "_new"))
    g8 = {
        "rows": {"audio_frozen": len(frozen_audio), "audio_new": len(new_audio), "audio_matched": len(audio_cmp),
                 "asr_frozen": len(frozen_asr), "asr_new": len(new_asr), "asr_matched": len(asr_cmp)},
        "waveform_mismatches": int((audio_cmp["waveform_sha256_frozen"] != audio_cmp["waveform_sha256_new"]).sum()),
        "ogg_mismatches": int((audio_cmp.loc[codec, "ogg_sha256_frozen"] != audio_cmp.loc[codec, "ogg_sha256_new"]).sum()),
        "hypothesis_mismatches": int((asr_cmp["hypothesis_frozen"] != asr_cmp["hypothesis_new"]).sum()),
        "seconds_per_utterance": (time.time() - started) / len(selection),
    }
    g8["pass"] = bool(len(audio_cmp) == len(frozen_audio) == len(new_audio)
                      and len(asr_cmp) == len(frozen_asr) == len(new_asr)
                      and g8["waveform_mismatches"] == 0 and g8["ogg_mismatches"] == 0
                      and g8["hypothesis_mismatches"] == 0)
    new_audio.to_csv(design.CALIBRATION / "g8_audio_manifest.csv", index=False)
    new_asr.to_csv(design.CALIBRATION / "g8_asr_outputs.csv", index=False)
    return g8


def calibrate_asr() -> int:
    spec = design.require_frozen_plan(committed=False)
    path = design.DRY_RUN_PARTS["asr"]
    if path.exists():
        raise RuntimeError(f"{path} exists")
    decode_part = s3.read_sealed(design.DRY_RUN_PARTS["decode"], "report_sha256")
    if not decode_part["pass"] or decode_part["spec_sha256"] != spec["spec_sha256"]:
        raise RuntimeError("the RS1 decode part has not passed under this plan")
    if not torch.cuda.is_available() or free_gpu_gib() < MIN_FREE_GPU_GIB:
        raise RuntimeError(f"the GPU is busy (free {free_gpu_gib() if torch.cuda.is_available() else 0:.1f} GiB, "
                           f"need {MIN_FREE_GPU_GIB}); nothing was run")
    selection = s3.load_selection("calibration")["utterances"]
    pipeline = s3.Pipeline()
    g8 = environment_g8(pipeline, selection)
    rec = upipe.Recognisers.from_stage3_pipeline(pipeline)

    def generate(waveform):
        return {design.OPUS_LIBOPUS: libopus_only(waveform)}

    records = []
    for start in range(0, len(selection), upipe.CHUNK_UTTERANCES):
        records += upipe.process_chunk("calibration", selection[start:start + upipe.CHUNK_UTTERANCES],
                                       generate, [design.OPUS_LIBOPUS], rec)
    repeat = upipe.process_chunk("calibration", selection[:2], generate, [design.OPUS_LIBOPUS], rec)
    audio_rows = pd.DataFrame([r for record in records for r in record["audio"]])
    asr_rows = pd.DataFrame([r for record in records for r in record["asr"]])
    decoded = pd.read_csv(design.CALIBRATION / "dry_run_decode_rows.csv")
    same_audio = audio_rows.merge(decoded[["utterance", "waveform_sha256"]], on="utterance", suffixes=("", "_decode"))
    first = {(r["utterance"], r["model"]): r["hypothesis"] for record in records[:2] for r in record["asr"]}
    r1_asr = pd.read_csv(r1_calibration_file("e2_asr_outputs.csv"), keep_default_na=False)
    r1_asr = r1_asr[r1_asr["condition"] == "OPUS_REFDEC"]
    cmp = asr_rows.merge(r1_asr, on=["utterance", "model"], suffixes=("", "_r1"))
    g6b = {
        "audio_identical_to_decode_part": int((same_audio["waveform_sha256"] == same_audio["waveform_sha256_decode"]).sum()),
        "of": len(selection),
        "repeat_hypotheses_identical": all(first[(r["utterance"], r["model"])] == r["hypothesis"]
                                           for record in repeat for r in record["asr"]),
        "empty_hypotheses": int((asr_rows["hypothesis"].astype(str).str.strip() == "").sum()),
    }
    g6b["pass"] = bool(g6b["audio_identical_to_decode_part"] == len(selection) and g6b["repeat_hypotheses_identical"])
    asr_rows.to_csv(design.CALIBRATION / "dry_run_asr_outputs.csv", index=False)
    report = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "part": "asr",
        "purpose": "RS1 dry run, calibration set only: G8 environment reproduction and G6b; no WER is compared",
        "G8": g8, "G6b": g6b,
        "descriptive": {"hypotheses_identical_to_r1_e2_refdec": {
            m: int((cmp.loc[cmp["model"] == m, "hypothesis"] == cmp.loc[cmp["model"] == m, "hypothesis_r1"]).sum())
            for m in design.MODELS}, "of": len(selection),
            "note": "R1's E2 recognised OPUS_REFDEC in chunks with other conditions, so Whisper batches differed"},
        "files": {p.name: s3.file_sha256(p) for p in sorted(design.CALIBRATION.glob("*.csv"))},
    }
    report["pass"] = bool(g8["pass"] and g6b["pass"])
    digest = s3.write_sealed(path, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], "G8": g8["pass"], "G6b": g6b, "descriptive": report["descriptive"],
                      "report_sha256": digest}, indent=1))
    return 0 if report["pass"] else 1


# ==================================================
# RS3 validate, RS4 run, RS5 analyse (confirmation set; need the committed plan and code freeze)
# ==================================================

def committed_state() -> dict:
    return {str(p): upgrade.git("log", "-1", "--format=%H %cI", "--", str(p)).stdout.strip()
            for p in [design.SPEC_JSON, design.PLAN_MD, design.CODE_FREEZE]}


def validate() -> int:
    spec, freeze = design.require_code_freeze(committed=True)
    if VALIDATION_REPORT.exists():
        raise RuntimeError(f"{VALIDATION_REPORT} exists")
    if RAW.exists() or ANALYSIS.exists():
        raise RuntimeError("R4 recognition or analysis outputs exist before validation (G7)")
    VALIDATION.mkdir(parents=True, exist_ok=True)
    selection = s3.load_selection("confirmation")["utterances"]
    stage3 = stage3_opus(upgrade.S3_CONFIRMATION)
    r1 = r1_refdec(design.R1_CONFIRMATION_ROWS, r1_confirmation_rows_sha256())
    started = time.time()
    rows, accumulators, errors = process(selection, stage3, r1, "RS3 validate")
    gates = gate_results(rows, len(selection), errors)
    gates["G5"] = {"environment_differences": design.environment_unchanged(spec),
                   "decoder": opus_direct.libopus_version(), "decoder_path": opus_direct.libopus_path()}
    gates["G5"]["pass"] = not gates["G5"]["environment_differences"]
    gates["G7"] = {"committed": committed_state(), "no_r4_recognition_outputs": not RAW.exists(), "pass": not RAW.exists()}
    gates["G9"] = anchor_check(analyse_table(stage3_metrics(), [design.REF, design.OPUS_FFMPEG]), spec["stage3_anchors"])
    rows.to_csv(VALIDATION_ROWS, index=False)
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
              "n_utterances": len(selection), "gates": gates, "diagnostics": diagnostics(rows, accumulators),
              "seconds_per_utterance": (time.time() - started) / len(selection),
              "rows_sha256": s3.file_sha256(VALIDATION_ROWS)}
    report["pass"] = all(g["pass"] for g in gates.values())
    report["status"] = "PASS: RS4 may run" if report["pass"] else f"{design.STOPPED} before recognition"
    digest = s3.write_sealed(VALIDATION_REPORT, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], **{k: g["pass"] for k, g in gates.items()},
                      "report_sha256": digest}, indent=1))
    return 0 if report["pass"] else 1


def run() -> str:
    spec, freeze = design.require_code_freeze(committed=True)
    report = s3.read_sealed(VALIDATION_REPORT, "report_sha256")
    if not report["pass"] or report["code_freeze_sha256"] != freeze["freeze_sha256"]:
        raise RuntimeError("R4 validation has not passed under this code freeze; R4 is STOPPED")
    if s3.file_sha256(VALIDATION_ROWS) != report["rows_sha256"]:
        raise RuntimeError("validation rows differ from the sealed report")
    if not torch.cuda.is_available() or free_gpu_gib() < MIN_FREE_GPU_GIB:
        raise RuntimeError(f"the GPU is busy (need {MIN_FREE_GPU_GIB} GiB free); nothing was run")
    rows = pd.read_csv(VALIDATION_ROWS)
    validated = dict(zip(rows["utterance"], rows["waveform_sha256"]))
    selection = s3.load_selection("confirmation")

    def generate(waveform):
        return {design.OPUS_LIBOPUS: libopus_only(waveform)}

    def check(entry, audio_rows):
        for row in audio_rows:
            if row["waveform_sha256"] != validated[entry["utterance"]]:
                raise RuntimeError(f"{entry['utterance']}: audio differs from the validated audio")

    return upipe.run_set("confirmation", selection["utterances"], RAW, generate, [design.OPUS_LIBOPUS],
                         upipe.Recognisers(), freeze["code_sha256"], selection["selection_sha256"], check=check)


def analyse() -> dict:
    spec, freeze = design.require_code_freeze(committed=True)
    manifest = s3.read_sealed(RAW / "outputs_sha256.json", "outputs_sha256")
    new = verified_csv(RAW, "utterance_metrics.csv", keep_default_na=False)
    new = new[new["condition"] == design.OPUS_LIBOPUS]
    metrics = pd.concat([stage3_metrics(), new], ignore_index=True)
    table = analyse_table(metrics, design.CONDITIONS)
    anchors = anchor_check(table, spec["stage3_anchors"])
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    table.to_csv(ANALYSIS / "r4_bootstrap.csv", index=False)
    cells = {}
    for model in design.MODELS:
        d = ustats.lookup(table, model, "D", "micro", "pooled")
        cells[model] = {q: list(ustats.lookup(table, model, q, "micro", "pooled")) for q in design.QUANTITIES}
        cells[model]["outcome"] = design.r4_outcome(d[1], d[2])
    decision = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
                "outputs_sha256": manifest["outputs_sha256"], "anchor_reproduction": anchors,
                "analysis": "R4: reference-decoder total-penalty sensitivity (post-confirmation sensitivity analysis; "
                            "total penalty only; not a decomposition)",
                "cells": cells, "outcome": None, "note": "per recogniser only; no combined outcome",
                "bootstrap_sha256": s3.file_sha256(ANALYSIS / "r4_bootstrap.csv")}
    s3.write_sealed(ANALYSIS / "r4_decision.json", s3.native(decision), "decision_sha256")
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["calibrate", "validate", "run", "analyse"])
    parser.add_argument("part", nargs="?", choices=["decode", "asr"])
    args = parser.parse_args()
    os.chdir(design.REPO_ROOT)
    if args.command == "calibrate":
        if args.part is None:
            parser.error("calibrate needs a part: decode or asr")
        return calibrate_decode() if args.part == "decode" else calibrate_asr()
    if args.part is not None:
        parser.error(f"{args.command} takes no part")
    if args.command == "validate":
        return validate()
    if args.command == "run":
        print(f"R4 outputs manifest {run()}")
        return 0
    decision = analyse()
    print(json.dumps({m: c["outcome"] for m, c in decision["cells"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
