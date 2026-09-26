"""
TASLP-upgrade addition B: forced SILK-NB bitrate sweep.

PRE-REGISTERED PROSPECTIVE SWEEP on fresh utterances: a fresh-utterance, not
fresh-speaker, holdout (see 00_UPGRADE_PLAN.md). NOT RUN AT DESIGN TIME.

    LP, SILK8, SILK12, SILK16, SILK24, SILK40: every coded condition uses the same
    direct-libopus path, forced NB, signal=voice and identical application, VBR,
    complexity, frame duration, FEC/DTX settings, decoder and resampler.

Commands, strictly in this order:

    calibrate   U1  Stage 3 calibration set only (20 dev-clean utterances): gate E1
                    (the environment reproduces the sealed Stage 3 calibration outputs
                    exactly) and E2 (sweep-condition sanity; no condition comparison).
    validate    U3  sweep selection, encode/decode only, no ASR: gates V1-V5.
    run         U4  sweep selection: ASR, once (resumable, never rerun).
    analyse     U5  frozen analysis and the pre-registered GO / WEAKEN / FALSIFY rule.

calibrate needs the committed, sealed plan; validate, run and analyse also need the
sealed code freeze (upgrade_design.py freeze-code), which follows calibrate.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402
import torch                # noqa: E402
from tqdm import tqdm       # noqa: E402

import lowpass              # noqa: E402
import opus_direct          # noqa: E402
import run_stage3 as s3     # noqa: E402
import stage3_audio as audio  # noqa: E402
import upgrade_design as design  # noqa: E402
import upgrade_pipeline as pipe  # noqa: E402
import upgrade_stats as ustats   # noqa: E402


OUT = design.RESULTS / "sweep"
VALIDATION = OUT / "validation"
VALIDATION_REPORT = VALIDATION / "validation_report.json"
VALIDATION_ROWS = VALIDATION / "validation_rows.csv"
RAW = OUT / "raw"
ANALYSIS = OUT / "analysis"
CALIBRATION = design.CALIBRATION_REPORT.parent

DESCRIPTORS = {   # column in signal_metrics.csv / audio_manifest.csv -> label (medians over utterances)
    "vs_lp_lsd_0_3k_db": "LSD 0-3 kHz vs LP (dB)",
    "vs_lp_lsd_0_4k_db": "LSD 0-4 kHz vs LP (dB)",
    "vs_lp_coherence_0_3500": "coherence 0-3.5 kHz vs LP",
    "vs_ref_coherence_0_3500": "coherence 0-3.5 kHz vs REF",
    "vs_ref_retained_bandwidth_hz": "retained bandwidth, power-based (Hz)",
    "vs_ref_hf_power_change_db": "4-8 kHz power change vs REF (dB)",
}


def load_selection(spec: dict) -> dict:
    selection = s3.read_sealed(design.SELECTION, "selection_sha256")
    if selection["selection_sha256"] != spec["B"]["data"]["sha256"]:
        raise RuntimeError("sweep selection differs from the frozen plan")
    return selection


def ids(entry: dict) -> dict:
    return {"utterance": entry["utterance"], "subset": entry["subset"], "speaker_id": entry["speaker_id"]}


# ==================================================
# U1 calibrate (E1, E2) - Stage 3 calibration set only
# ==================================================

def calibrate() -> int:
    spec = design.require_frozen_plan()
    if design.CALIBRATION_REPORT.exists():
        raise RuntimeError(f"{design.CALIBRATION_REPORT} exists")
    CALIBRATION.mkdir(parents=True, exist_ok=True)
    pipeline = s3.Pipeline()
    selection = s3.load_selection("calibration")["utterances"]

    # E1: the frozen Stage 3 pipeline, all six conditions, against the sealed calibration outputs
    started = time.time()
    records = []
    for start in range(0, len(selection), pipe.CHUNK_UTTERANCES):
        records += pipeline.process_chunk("calibration", selection[start:start + pipe.CHUNK_UTTERANCES],
                                          audio.new_accumulators())
    e1_seconds = time.time() - started
    new_audio = pd.DataFrame([r for rec in records for r in rec["audio"]])
    new_asr = pd.DataFrame([r for rec in records for r in rec["asr"]])
    frozen_audio = pd.read_csv(design.S3_CALIBRATION / "audio_manifest.csv")
    frozen_asr = pd.read_csv(design.S3_CALIBRATION / "asr_outputs.csv", keep_default_na=False)
    audio_cmp = frozen_audio.merge(new_audio, on=["utterance", "condition"], suffixes=("_frozen", "_new"))
    codec = audio_cmp["ogg_sha256_frozen"].notna()
    asr_cmp = frozen_asr.merge(new_asr, on=["utterance", "condition", "model"], suffixes=("_frozen", "_new"))
    e1 = {
        "rows": {"audio_frozen": len(frozen_audio), "audio_new": len(new_audio), "audio_matched": len(audio_cmp),
                 "asr_frozen": len(frozen_asr), "asr_new": len(new_asr), "asr_matched": len(asr_cmp)},
        "waveform_mismatches": int((audio_cmp["waveform_sha256_frozen"] != audio_cmp["waveform_sha256_new"]).sum()),
        "ogg_mismatches": int((audio_cmp.loc[codec, "ogg_sha256_frozen"]
                               != audio_cmp.loc[codec, "ogg_sha256_new"]).sum()),
        "hypothesis_mismatches": int((asr_cmp["hypothesis_frozen"] != asr_cmp["hypothesis_new"]).sum()),
    }
    e1["pass"] = bool(len(audio_cmp) == len(frozen_audio) == len(new_audio)
                      and len(asr_cmp) == len(frozen_asr) == len(new_asr)
                      and e1["waveform_mismatches"] == 0 and e1["ogg_mismatches"] == 0
                      and e1["hypothesis_mismatches"] == 0)
    new_audio.to_csv(CALIBRATION / "e1_audio_manifest.csv", index=False)
    new_asr.to_csv(CALIBRATION / "e1_asr_outputs.csv", index=False)

    # E2: sweep conditions, pipeline sanity only (no WER is compared between conditions)
    rec = pipe.Recognisers.from_stage3_pipeline(pipeline)

    def generate(waveform):
        return pipe.sweep_conditions(waveform, pipeline.filters)

    started = time.time()
    e2_records = []
    for start in range(0, len(selection), pipe.CHUNK_UTTERANCES):
        e2_records += pipe.process_chunk("calibration", selection[start:start + pipe.CHUNK_UTTERANCES],
                                         generate, ustats.SWEEP_CONDITIONS, rec)
    e2_seconds = time.time() - started
    e2_audio = pd.DataFrame([r for rec_ in e2_records for r in rec_["audio"]])
    e2_asr = pd.DataFrame([r for rec_ in e2_records for r in rec_["asr"]])
    identity = []
    for entry in selection[:2]:
        waveform = pipe.load_reference(entry)
        for name, settings in pipe.SWEEP_SETTINGS.items():
            ours, _, _ = pipe.encode_decode(waveform, settings)
            frozen, _ = audio.codec_round_trip(waveform, settings)
            identity.append(audio.tensor_sha256(ours) == audio.tensor_sha256(frozen))
    repeat = pipe.process_chunk("calibration", selection[:2], generate, ustats.SWEEP_CONDITIONS, rec)
    first = {(r["utterance"], r["condition"]): r["waveform_sha256"] for rec_ in e2_records[:2] for r in rec_["audio"]}
    first_asr = {(r["utterance"], r["condition"], r["model"]): r["hypothesis"]
                 for rec_ in e2_records[:2] for r in rec_["asr"]}
    coded = e2_audio[e2_audio["condition"] != "LP"]
    e2 = {
        "codec_round_trip_identity": {"checked": len(identity), "identical": int(sum(identity))},
        "determinism": {
            "waveforms_identical": all(first[(r["utterance"], r["condition"])] == r["waveform_sha256"]
                                       for rec_ in repeat for r in rec_["audio"]),
            "hypotheses_identical": all(first_asr[(r["utterance"], r["condition"], r["model"])] == r["hypothesis"]
                                        for rec_ in repeat for r in rec_["asr"])},
        "packets_all_expected_config": bool((coded["share_expected_config"] == 1).all()),
        "lengths_equal_ref": bool(e2_audio["length_equals_ref"].all()),
        "nonfinite_samples": int(e2_audio["nonfinite_count"].sum()),
        "empty_hypotheses": int((e2_asr["hypothesis"].astype(str).str.strip() == "").sum()),
        "median_payload_kbps": {n: float(coded.loc[coded["condition"] == n, "payload_kbps"].median())
                                for n in ustats.SWEEP_CODED},
    }
    e2["pass"] = bool(e2["codec_round_trip_identity"]["identical"] == len(identity)
                      and e2["determinism"]["waveforms_identical"] and e2["determinism"]["hypotheses_identical"]
                      and e2["packets_all_expected_config"] and e2["lengths_equal_ref"]
                      and e2["nonfinite_samples"] == 0)
    e2_audio.to_csv(CALIBRATION / "e2_audio_manifest.csv", index=False)
    e2_asr.to_csv(CALIBRATION / "e2_asr_outputs.csv", index=False)

    report = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
        "purpose": "environment reproduction (E1) and sweep pipeline sanity (E2) on the Stage 3 calibration "
                   "set; no condition comparison is computed",
        "utterances": len(selection), "E1": e1, "E2": e2,
        "seconds_per_utterance": {"E1_six_stage3_conditions": e1_seconds / len(selection),
                                  "E2_six_sweep_conditions": e2_seconds / len(selection)},
        "files": {p.name: s3.file_sha256(p) for p in sorted(CALIBRATION.glob("*.csv"))},
    }
    digest = s3.write_sealed(design.CALIBRATION_REPORT, report, "report_sha256")
    print(json.dumps({"E1": e1["pass"], "E2": e2["pass"], "report_sha256": digest}, indent=1))
    return 0 if e1["pass"] and e2["pass"] else 1


# ==================================================
# U3 validate (V1-V5) - encode/decode only, no ASR
# ==================================================

def validate() -> int:
    spec, freeze = design.require_code_freeze()
    if VALIDATION_REPORT.exists():
        raise RuntimeError(f"{VALIDATION_REPORT} exists")
    selection = load_selection(spec)["utterances"]
    filters = audio.load_filters()                 # V5: raises unless the LP taps hash is the frozen one
    rows, bridge = [], []
    for entry in tqdm(selection, desc="validate", unit="utt"):
        waveform = pipe.load_reference(entry)
        lp = lowpass.apply_zero_phase(waveform, filters["LP"]).to(torch.float32)
        rows.append({**ids(entry), **pipe.audio_row("LP", lp, waveform, {})})
        silk8 = None
        for name, settings in pipe.SWEEP_SETTINGS.items():
            decoded, summary, result = pipe.encode_decode(waveform, settings)
            rows.append({**ids(entry), **pipe.audio_row(name, decoded, waveform, summary),
                         "readback_mismatches": ";".join(pipe.readback_mismatches(result))})
            if name == "SILK8":
                silk8 = result.ogg
        stage3_opus = opus_direct.encode(waveform, pipe.SAMPLE_RATE, pipe.OPUS_SETTINGS).ogg
        bridge.append(stage3_opus == silk8)
    VALIDATION.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(VALIDATION_ROWS, index=False)

    coded = frame[frame["condition"] != "LP"]
    medians = [float(coded.loc[coded["condition"] == n, "payload_kbps"].median()) for n in ustats.SWEEP_CODED]
    container = [float(coded.loc[coded["condition"] == n, "container_kbps"].median()) for n in ustats.SWEEP_CODED]
    within = [abs(m / r - 1.0) <= design.BITRATE_TOLERANCE for m, r in zip(medians, ustats.SWEEP_RATES_KBPS)]
    ratios = [b / a for a, b in zip(medians, medians[1:])]
    gates = {
        "V1": bool((coded["share_expected_config"] == 1).all() and not coded["any_stereo"].any()
                   and (coded["frame_count_codes"].astype(str) == "0").all()
                   and (coded["libopus_bandwidths"] == "NB").all()),
        "V2": bool(all(within) and all(r >= design.MIN_ADJACENT_RATIO for r in ratios)),
        "V3": bool((coded["readback_mismatches"].fillna("").astype(str) == "").all()),
        "V4": bool((coded["decoded_sample_rate"] == pipe.DECODED_SAMPLE_RATE).all()
                   and frame["length_equals_ref"].all() and (frame["nonfinite_count"] == 0).all()),
        "V5": True,
    }
    report = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
        "n_utterances": len(selection), "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL",
        "measured_median_payload_kbps": medians, "median_container_kbps": container,
        "payload_within_tolerance": within, "adjacent_ratios": ratios,
        "share_packets_expected_config_min": float(coded["share_expected_config"].min()),
        "bridge_share_silk8_identical_to_stage3_opus_settings": float(np.mean(bridge)),
        "lp_taps_sha256": audio.FROZEN_LP_SHA256,
        "descriptive_by_condition": frame.groupby("condition").agg(
            lag_min=("lag_vs_ref_samples", "min"), lag_max=("lag_vs_ref_samples", "max"),
            rms_change_db_median=("rms_change_db", "median"), clipped_samples=("clip_count", "sum"),
        ).reset_index().to_dict(orient="records"),
        "rows_sha256": s3.file_sha256(VALIDATION_ROWS),
    }
    digest = s3.write_sealed(VALIDATION_REPORT, report, "report_sha256")
    print(json.dumps({"verdict": report["verdict"], "gates": gates, "report_sha256": digest}, indent=1))
    return 0 if report["verdict"] == "PASS" else 1


# ==================================================
# U4 run - ASR, once
# ==================================================

def run() -> None:
    spec, freeze = design.require_code_freeze()
    validation = s3.read_sealed(VALIDATION_REPORT, "report_sha256")
    if validation["verdict"] != "PASS":
        raise RuntimeError("validation did not pass; no ASR run")
    if s3.file_sha256(VALIDATION_ROWS) != validation["rows_sha256"]:
        raise RuntimeError("validation rows differ from the sealed report")
    frozen = pd.read_csv(VALIDATION_ROWS)
    expected = {(r.utterance, r.condition): (r.waveform_sha256, r.ogg_sha256 if isinstance(r.ogg_sha256, str) else None)
                for r in frozen.itertuples()}

    def check(entry, audio_rows):
        for row in audio_rows:
            waveform_sha, ogg_sha = expected[(entry["utterance"], row["condition"])]
            if row["waveform_sha256"] != waveform_sha or (ogg_sha and row.get("ogg_sha256") != ogg_sha):
                raise RuntimeError(f"{entry['utterance']} {row['condition']} differs from validation")

    selection = load_selection(spec)
    filters = audio.load_filters()
    digest = pipe.run_set("sweep", selection["utterances"], RAW,
                          lambda waveform: pipe.sweep_conditions(waveform, filters),
                          ustats.SWEEP_CONDITIONS, pipe.Recognisers(), freeze["code_sha256"],
                          selection["selection_sha256"], signal_fn=pipe.sweep_signal_rows,
                          transfer_pairs=pipe.SWEEP_TRANSFER_PAIRS, check=check)
    print(f"sweep decoded once; outputs_sha256 {digest}")


# ==================================================
# U5 analyse
# ==================================================

def analyse() -> None:
    spec, freeze = design.require_code_freeze()
    validation = s3.read_sealed(VALIDATION_REPORT, "report_sha256")
    manifest = s3.read_sealed(RAW / "outputs_sha256.json", "outputs_sha256")
    for name, digest in manifest["files"].items():
        if s3.file_sha256(RAW / name) != digest:
            raise RuntimeError(f"{RAW / name} differs from its sealed manifest")
    decision_path = ANALYSIS / "sweep_decision.json"
    if decision_path.exists():
        raise RuntimeError(f"{decision_path} exists")
    metrics = pd.read_csv(RAW / "utterance_metrics.csv", keep_default_na=False)
    table = ustats.analyse(metrics, ustats.SWEEP_CONDITIONS, ustats.sweep_quantities,
                           measured_kbps=validation["measured_median_payload_kbps"])
    anchors = spec["B"]["anchors"]
    decision = ustats.sweep_decision(table, {m: anchors[m]["S_star"] for m in ustats.MODELS})

    signal = pd.read_csv(RAW / "signal_metrics.csv")
    audio_rows = pd.read_csv(RAW / "audio_manifest.csv")
    descriptors = signal.groupby("condition")[[c for c in DESCRIPTORS if c in signal]].median()
    descriptors["rms_change_db vs REF"] = audio_rows.groupby("condition")["rms_change_db"].median()
    descriptors = descriptors.reindex(ustats.SWEEP_CONDITIONS).rename(columns=DESCRIPTORS)
    pooled = pd.read_csv(RAW / "pooled_transfer.csv")

    replication = {}
    for model in ustats.MODELS:
        replication[model] = {
            "R_8": list(ustats.lookup(table, model, "R_8")), "T_star": anchors[model]["T_star"],
            "R_40": list(ustats.lookup(table, model, "R_40")), "U_star": anchors[model]["U_star"],
            "E_8_40": list(ustats.lookup(table, model, "E_8_40")), "V_star": anchors[model]["V_star"],
        }
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    table.to_csv(ANALYSIS / "sweep_bootstrap.csv", index=False)
    descriptors.to_csv(ANALYSIS / "sweep_descriptors.csv")
    pooled.to_csv(ANALYSIS / "sweep_pooled_transfer.csv", index=False)
    record = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
        "validation_report_sha256": validation["report_sha256"], "outputs_sha256": manifest["outputs_sha256"],
        "bootstrap_sha256": s3.file_sha256(ANALYSIS / "sweep_bootstrap.csv"),
        **decision, "replication_anchors_descriptive": replication,
        "note": "descriptors are mechanism evidence only and do not enter the rule",
    }
    digest = s3.write_sealed(decision_path, record, "decision_sha256")
    (ANALYSIS / "sweep_report.md").write_text(render_report(record, table, descriptors))
    print(json.dumps({"outcome": decision["outcome"],
                      "per_model": {m: c["outcome"] for m, c in decision["cells"].items()},
                      "decision_sha256": digest}, indent=1))


def render_report(record: dict, table: pd.DataFrame, descriptors: pd.DataFrame) -> str:
    def fmt(model, quantity, kind="micro"):
        est, lo, hi = ustats.lookup(table, model, quantity, kind)
        return f"{est:+.2f} [{lo:+.2f}, {hi:+.2f}]"

    lines = ["# Forced SILK-NB bitrate sweep: result", "",
             "Pre-registered prospective sweep on fresh utterances (a fresh-utterance, not fresh-speaker, "
             "holdout).", "", f"**Outcome: {record['outcome']}**", "",
             "| Quantity | " + " | ".join(ustats.MODELS) + " |", "|---|" + "---|" * len(ustats.MODELS)]
    for quantity, kind in ([(f"R_{b}", "micro") for b in ustats.SWEEP_RATES_KBPS]
                           + [("S_log2", "trend"), ("S_rank", "trend"), ("S_log2_measured", "trend")]
                           + [(name, "micro") for name, _, _ in ustats.SWEEP_ADJACENT] + [("E_8_40", "micro")]):
        lines.append(f"| {quantity} | " + " | ".join(fmt(m, quantity, kind) for m in ustats.MODELS) + " |")
    lines += ["", "Per-recogniser outcomes: "
              + ", ".join(f"{m}: {c['outcome']}" for m, c in record["cells"].items()), "",
              "Descriptors (medians; mechanism evidence only):", "", markdown_table(descriptors), ""]
    return "\n".join(lines)


def markdown_table(frame: pd.DataFrame) -> str:
    """Plain Markdown table (the frozen environment has no tabulate, so no DataFrame.to_markdown)."""
    header = ["condition"] + [str(c) for c in frame.columns]
    rows = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for index, values in frame.iterrows():
        rows.append("| " + " | ".join([str(index)] + [f"{v:.3f}" if isinstance(v, (int, float, np.floating))
                                                        else str(v) for v in values]) + " |")
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["calibrate", "validate", "run", "analyse"])
    args = parser.parse_args()
    os.chdir(design.REPO_ROOT)
    result = {"calibrate": calibrate, "validate": validate, "run": run, "analyse": analyse}[args.command]()
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
