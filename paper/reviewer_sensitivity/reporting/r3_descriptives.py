"""
R3: the descriptive measures pre-specified in the plan (sections 9.2 and 9.3) that the frozen
analyse() does not compute. Written after RS5, outside the code freeze; reads sealed outputs only;
no measure enters an outcome.

    python paper/reviewer_sensitivity/reporting/r3_descriptives.py

Writes results_paper/reviewer_sensitivity/analysis/r3_descriptives.json (sealed).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parents[1] / "taslp_upgrade"), str(HERE.parents[1])]

import pandas as pd                  # noqa: E402

import reviewer_design as design     # noqa: E402
import run_stage3 as s3              # noqa: E402
import upgrade_design as udesign     # noqa: E402

RAW = design.RESULTS / "raw" / "sweep"
OUT = design.RESULTS / "analysis" / "r3_descriptives.json"


def main():
    if OUT.exists():
        raise RuntimeError(f"{OUT} exists")
    manifest = s3.read_sealed(RAW / "outputs_sha256.json", "outputs_sha256")
    for name, digest in manifest["files"].items():
        if s3.file_sha256(RAW / name) != digest:
            raise RuntimeError(f"{RAW / name} differs from its sealed manifest")
    decision = s3.read_sealed(design.RESULTS / "analysis" / "r3_decision.json", "decision_sha256")
    asr = pd.read_csv(RAW / "asr_outputs.csv", keep_default_na=False)
    b_asr = pd.read_csv(udesign.RESULTS / "sweep" / "raw" / "asr_outputs.csv", keep_default_na=False)
    b_manifest = s3.read_sealed(udesign.RESULTS / "sweep" / "raw" / "outputs_sha256.json", "outputs_sha256")
    if s3.file_sha256(udesign.RESULTS / "sweep" / "raw" / "asr_outputs.csv") != b_manifest["files"]["asr_outputs.csv"]:
        raise RuntimeError("B's asr_outputs.csv differs from its sealed manifest")

    hyp = asr.pivot_table(index=["utterance", "model"], columns="condition", values="hypothesis", aggfunc="first")
    b8 = b_asr[b_asr["condition"] == "SILK8"].set_index(["utterance", "model"])["hypothesis"]
    counts = {}
    for model in design.MODELS:
        part = hyp.xs(model, level="model")
        frozen = b8.xs(model, level="model").reindex(part.index)
        counts[model] = {"utterances": int(len(part)),
                         "nb8_vs_wb8_raw_hypothesis_differs": int((part[design.NB8] != part[design.WB8]).sum()),
                         "nb8_vs_b_silk8_raw_hypothesis_differs": int((part[design.NB8] != frozen).sum())}

    signal = pd.read_csv(RAW / "signal_metrics.csv")
    columns = {"vs_ref_coherence_0_3500": "coherence 0-3.5 kHz vs REF", "vs_ref_lsd_0_3k_db": "LSD 0-3 kHz vs REF (dB)",
               "vs_ref_lsd_0_4k_db": "LSD 0-4 kHz vs REF (dB)", "vs_ref_retained_bandwidth_hz": "retained bandwidth (Hz)",
               "vs_ref_hf_power_change_db": "4-8 kHz power change vs REF (dB)"}
    medians = signal.groupby("condition")[list(columns)].median().rename(columns=columns)
    pooled = pd.read_csv(RAW / "pooled_transfer.csv").set_index("processed")
    audio = pd.read_csv(design.RESULTS / "validation" / "sweep_rows.csv")
    rates = audio.groupby("condition").agg(payload_kbps_median=("payload_kbps", "median"),
                                           container_kbps_median=("container_kbps", "median"),
                                           rms_change_db_median=("rms_change_db", "median"),
                                           lag_min=("lag_vs_ref_samples", "min"), lag_max=("lag_vs_ref_samples", "max"),
                                           clipped_samples=("clip_count", "sum"))
    record = {
        "created_utc": s3.now(),
        "label": "descriptive measures pre-specified in the plan (R3, sections 9.2 and 9.3) and not computed by the frozen "
                 "analyse(); computed by this reporting script outside the code freeze after RS5; they enter no outcome",
        "r3_decision_sha256": decision["decision_sha256"], "outputs_sha256": manifest["outputs_sha256"],
        "hypothesis_differences": counts,
        "signal_descriptor_medians": {c: {k: float(v) for k, v in row.items()} for c, row in medians.iterrows()},
        "pooled_against_ref": {c: {k: float(pooled.loc[c, k]) for k in ["h1_level_db", "coherent_bandwidth_hz",
                                                                       "coherent_hf_power_db", "total_hf_power_db",
                                                                       "mean_coherence_0_3500"]}
                               for c in [design.NB8, design.WB8]},
        "packets_and_levels": {c: {k: float(v) for k, v in row.items()} for c, row in rates.iterrows()},
        "note_on_timing": "the plan lists the in-band descriptor set among the measures sealed before ASR; validate sweep "
                          "sealed the packet, bitrate, level and lag rows before ASR, but the in-band descriptors were "
                          "computed in the RS4b run (signal_metrics.csv) and are sealed with its outputs",
    }
    digest = s3.write_sealed(OUT, record, "descriptives_sha256")
    print(f"R3 descriptives sealed: {digest}")


if __name__ == "__main__":
    main()
