"""
TASLP-upgrade addition A: OPUS level-matched sensitivity.

POST-CONFIRMATION SENSITIVITY ANALYSIS - NOT A SECOND CONFIRMATORY TEST. It uses the
2,174 Stage 3 confirmation utterances, cannot change the sealed Stage 3 estimates or
decision, and can only qualify the interpretation of the Stage 3 residual.
NOT RUN AT DESIGN TIME.

    OPUS8_LEVEL_MATCHED = float32(g * OPUS), g = RMS(LP) / RMS(OPUS) per utterance,
    applied after decoding: no re-encoding, no AGC, no clipping, no re-alignment,
    no other normalisation. Primary contrast: OPUS8_LEVEL_MATCHED - LP.

Commands, strictly in this order (after run_bitrate_sweep.py calibrate and
upgrade_design.py freeze-code):

    regenerate  U6  LP and OPUS regenerated bit-identically to Stage 3, level matching
                    checked: gates A1-A3. No ASR.
    run         U7  ASR, once: LP, OPUS, OPUS8_LEVEL_MATCHED (resumable, never rerun).
    analyse     U8  frozen analysis, reproduction check and the pre-registered rule.
"""

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402
from tqdm import tqdm       # noqa: E402

import run_stage3 as s3     # noqa: E402
import stage3_audio as audio  # noqa: E402
import upgrade_design as design  # noqa: E402
import upgrade_pipeline as pipe  # noqa: E402
import upgrade_stats as ustats   # noqa: E402


OUT = design.RESULTS / "level"
REGENERATION = OUT / "regeneration"
REGENERATION_REPORT = REGENERATION / "regeneration_report.json"
REGENERATION_ROWS = REGENERATION / "regeneration_rows.csv"
RAW = OUT / "raw"
ANALYSIS = OUT / "analysis"
LM = ustats.LEVEL_MATCHED


def confirmation(spec: dict) -> dict:
    selection = s3.load_selection("confirmation")
    if selection["selection_sha256"] != spec["A"]["data"]["sha256"]:
        raise RuntimeError("confirmation selection differs from the frozen plan")
    return selection


def frozen_stage3_audio() -> dict:
    """(utterance, condition) -> row of the sealed Stage 3 confirmation audio manifest (LP, OPUS)."""
    manifest = pd.read_csv(design.S3_CONFIRMATION / "audio_manifest.csv")
    manifest = manifest[manifest["condition"].isin(["LP", "OPUS"])]
    return {(r["utterance"], r["condition"]): r for r in manifest.to_dict(orient="records")}


def gate_row(entry: dict, audio_rows: list[dict], frozen: dict) -> dict:
    by = {r["condition"]: r for r in audio_rows}
    lp_f, opus_f = frozen[(entry["utterance"], "LP")], frozen[(entry["utterance"], "OPUS")]
    lm = by[LM]
    frozen_gain_db = lp_f["output_rms_dbfs"] - opus_f["output_rms_dbfs"]
    return {
        "utterance": entry["utterance"], "subset": entry["subset"], "speaker_id": entry["speaker_id"],
        "lp_waveform_identical": by["LP"]["waveform_sha256"] == lp_f["waveform_sha256"],
        "opus_waveform_identical": by["OPUS"]["waveform_sha256"] == opus_f["waveform_sha256"],
        "opus_ogg_identical": by["OPUS"]["ogg_sha256"] == opus_f["ogg_sha256"],
        "gain": lm["gain"], "gain_db": lm["gain_db"], "frozen_gain_db": frozen_gain_db,
        "gain_reproduction_error_db": lm["gain_db"] - frozen_gain_db,
        "level_error_db": lm["output_rms_dbfs"] - by["LP"]["output_rms_dbfs"],
        "length_equals_ref": bool(lm["length_equals_ref"]), "nonfinite": int(lm["nonfinite_count"]),
        "samples_at_or_above_full_scale": int(lm["clip_count"]),
    }


def gates_pass(row: dict) -> bool:
    return bool(row["lp_waveform_identical"] and row["opus_waveform_identical"] and row["opus_ogg_identical"]
                and abs(row["level_error_db"]) <= design.LEVEL_TOLERANCE_DB
                and abs(row["gain_reproduction_error_db"]) <= design.GAIN_REPRODUCTION_TOLERANCE_DB
                and row["length_equals_ref"] and row["nonfinite"] == 0)


# ==================================================
# U6 regenerate (A1-A3) - no ASR
# ==================================================

def regenerate() -> int:
    spec, freeze = design.require_code_freeze()
    if REGENERATION_REPORT.exists():
        raise RuntimeError(f"{REGENERATION_REPORT} exists")
    selection = confirmation(spec)["utterances"]
    frozen = frozen_stage3_audio()
    filters = audio.load_filters()
    rows = []
    for entry in tqdm(selection, desc="regenerate", unit="utt"):
        waveform = pipe.load_reference(entry)
        generated = pipe.level_conditions(waveform, filters)
        audio_rows = [pipe.audio_row(name, generated[name][0], waveform, generated[name][1])
                      for name in ustats.LEVEL_CONDITIONS]
        rows.append(gate_row(entry, audio_rows, frozen))
    REGENERATION.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(REGENERATION_ROWS, index=False)
    gates = {
        "A1": bool(frame["lp_waveform_identical"].all() and frame["opus_waveform_identical"].all()
                   and frame["opus_ogg_identical"].all()),
        "A2": bool((frame["level_error_db"].abs() <= design.LEVEL_TOLERANCE_DB).all()
                   and frame["length_equals_ref"].all() and (frame["nonfinite"] == 0).all()),
        "A3": bool((frame["gain_reproduction_error_db"].abs() <= design.GAIN_REPRODUCTION_TOLERANCE_DB).all()),
    }
    gain = frame["gain_db"].to_numpy()
    report = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
        "n_utterances": len(frame), "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL",
        "mismatches": {"lp_waveform": int((~frame["lp_waveform_identical"]).sum()),
                       "opus_waveform": int((~frame["opus_waveform_identical"]).sum()),
                       "opus_ogg": int((~frame["opus_ogg_identical"]).sum())},
        "gain_db": {"median": float(np.median(gain)), "p05": float(np.quantile(gain, 0.05)),
                    "p95": float(np.quantile(gain, 0.95)), "min": float(gain.min()), "max": float(gain.max())},
        "max_abs_level_error_db": float(frame["level_error_db"].abs().max()),
        "max_abs_gain_reproduction_error_db": float(frame["gain_reproduction_error_db"].abs().max()),
        "level_matched_samples_at_or_above_full_scale": int(frame["samples_at_or_above_full_scale"].sum()),
        "rows_sha256": s3.file_sha256(REGENERATION_ROWS),
    }
    digest = s3.write_sealed(REGENERATION_REPORT, report, "report_sha256")
    print(json.dumps({"verdict": report["verdict"], "gates": gates, "report_sha256": digest}, indent=1))
    return 0 if report["verdict"] == "PASS" else 1


# ==================================================
# U7 run - ASR, once
# ==================================================

def run() -> None:
    spec, freeze = design.require_code_freeze()
    regeneration = s3.read_sealed(REGENERATION_REPORT, "report_sha256")
    if regeneration["verdict"] != "PASS":
        raise RuntimeError("regeneration gates did not pass; no ASR run")
    frozen = frozen_stage3_audio()

    def check(entry, audio_rows):
        if not gates_pass(gate_row(entry, audio_rows, frozen)):
            raise RuntimeError(f"{entry['utterance']}: regenerated audio fails gates A1-A3")

    selection = confirmation(spec)
    filters = audio.load_filters()
    digest = pipe.run_set("level", selection["utterances"], RAW,
                          lambda waveform: pipe.level_conditions(waveform, filters),
                          ustats.LEVEL_CONDITIONS, pipe.Recognisers(), freeze["code_sha256"],
                          selection["selection_sha256"], check=check)
    print(f"level-matched sensitivity decoded once; outputs_sha256 {digest}")


# ==================================================
# U8 analyse
# ==================================================

def reproduction_check(asr_rows: pd.DataFrame) -> pd.DataFrame:
    frozen = pd.read_csv(design.S3_CONFIRMATION / "asr_outputs.csv", keep_default_na=False)
    frozen = frozen[frozen["condition"].isin(["LP", "OPUS"])]
    merged = frozen.merge(asr_rows, on=["utterance", "condition", "model"], suffixes=("_stage3", "_new"))
    if len(merged) != len(frozen):
        raise RuntimeError("reproduction check: unmatched rows")
    merged["identical"] = merged["hypothesis_stage3"] == merged["hypothesis_new"]
    return (merged.groupby(["model", "condition"])["identical"]
            .agg(n="size", identical="sum").reset_index()
            .assign(differing=lambda f: f["n"] - f["identical"]))


def analyse() -> None:
    spec, freeze = design.require_code_freeze()
    manifest = s3.read_sealed(RAW / "outputs_sha256.json", "outputs_sha256")
    for name, digest in manifest["files"].items():
        if s3.file_sha256(RAW / name) != digest:
            raise RuntimeError(f"{RAW / name} differs from its sealed manifest")
    decision_path = ANALYSIS / "level_decision.json"
    if decision_path.exists():
        raise RuntimeError(f"{decision_path} exists")
    metrics = pd.read_csv(RAW / "utterance_metrics.csv", keep_default_na=False)
    asr_rows = pd.read_csv(RAW / "asr_outputs.csv", keep_default_na=False)
    table = ustats.analyse(metrics, ustats.LEVEL_CONDITIONS, ustats.level_quantities)
    t_star = {m: spec["A"]["anchors"][m]["T_star"]["estimate"] for m in ustats.MODELS}
    decision = ustats.level_decision(table, t_star)
    reproduction = reproduction_check(asr_rows)
    changed = {}
    for model in ustats.MODELS:
        part = asr_rows[asr_rows["model"] == model].pivot(index="utterance", columns="condition",
                                                         values="hypothesis")
        changed[model] = int((part["OPUS"] != part[LM]).sum())
    stage3 = {m: {"estimate": spec["A"]["anchors"][m]["T_star"]["estimate"],
                  "ci": spec["A"]["anchors"][m]["T_star"]["ci"],
                  "same_run": list(ustats.lookup(table, m, "T_opus_minus_lp"))} for m in ustats.MODELS}

    ANALYSIS.mkdir(parents=True, exist_ok=True)
    table.to_csv(ANALYSIS / "level_bootstrap.csv", index=False)
    reproduction.to_csv(ANALYSIS / "reproduction_check.csv", index=False)
    record = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
        "outputs_sha256": manifest["outputs_sha256"],
        "bootstrap_sha256": s3.file_sha256(ANALYSIS / "level_bootstrap.csv"),
        "label": "POST-CONFIRMATION SENSITIVITY ANALYSIS - NOT A SECOND CONFIRMATORY TEST",
        **decision,
        "hypotheses_changed_by_level_matching": changed,
        "reproduction_check": reproduction.to_dict(orient="records"),
        "stage3_residual_vs_same_run": stage3,
    }
    digest = s3.write_sealed(decision_path, record, "decision_sha256")
    (ANALYSIS / "level_report.md").write_text(render_report(record, table))
    print(json.dumps({"outcome": decision["outcome"],
                      "per_model": {m: c["outcome"] for m, c in decision["cells"].items()},
                      "decision_sha256": digest}, indent=1))


def render_report(record: dict, table: pd.DataFrame) -> str:
    def fmt(model, quantity, kind="micro"):
        est, lo, hi = ustats.lookup(table, model, quantity, kind)
        return f"{est:+.2f} [{lo:+.2f}, {hi:+.2f}]"

    lines = ["# OPUS level-matched sensitivity: result", "",
             "Post-confirmation sensitivity analysis on the Stage 3 confirmation set. Not a second "
             "confirmatory test; the Stage 3 estimates and decision are unchanged.", "",
             f"**Outcome: {record['outcome']}**", "",
             "| Quantity (pp) | " + " | ".join(ustats.MODELS) + " |", "|---|" + "---|" * len(ustats.MODELS)]
    for quantity in ["L_level_matched_minus_lp", "K_level_matched_minus_opus", "T_opus_minus_lp"]:
        lines.append(f"| {quantity} | " + " | ".join(fmt(m, quantity) for m in ustats.MODELS) + " |")
    lines += ["", "Per-recogniser outcomes: "
              + ", ".join(f"{m}: {c['outcome']}" for m, c in record["cells"].items()),
              f"Hypotheses changed by level matching: {record['hypotheses_changed_by_level_matching']}",
              f"Reproduction of Stage 3 hypotheses: {record['reproduction_check']}", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["regenerate", "run", "analyse"])
    args = parser.parse_args()
    os.chdir(design.REPO_ROOT)
    result = {"regenerate": regenerate, "run": run, "analyse": analyse}[args.command]()
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
