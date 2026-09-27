"""
A1 runner: best-linear (OPD target) decomposition of 8 kbit/s Opus. Commands, in the order of the
sealed plan (A1_PLAN.md):

    calibrate signal   A1 calibration speakers (signal only): C1, C2, collapse tolerance, descriptors
    calibrate asr      Stage 3 calibration set (GPU): C3 environment reproduction and LIN8 path check
    validate           A1 validation speakers (signal only): V1-V3 (needs the sealed code freeze)
    evaluate           confirmation set, no ASR: E1-E5 and the 2,174 LIN8 waveforms (needs the commit)
    run                LIN8 recognition, once (GPU)
    analyse            bootstrap, estimates, outcome: A1_DECISION.json

OPUS8 is the Stage 3 OPUS waveform (stage3_audio.codec_round_trip, unchanged); LIN8 = a1_opd.project.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "paper" / "taslp_upgrade"), str(HERE.parents[1] / "paper")]

import numpy as np                   # noqa: E402
import pandas as pd                  # noqa: E402
import torch                         # noqa: E402
import torchaudio                    # noqa: E402
from tqdm import tqdm                # noqa: E402

import a1_design as design           # noqa: E402
import a1_opd as opd                 # noqa: E402
import common                        # noqa: E402
import run_lowpass_validation as s2b  # noqa: E402
import run_stage3 as s3              # noqa: E402
import stage3_audio as audio         # noqa: E402
import upgrade_design as upgrade     # noqa: E402
import upgrade_pipeline as upipe     # noqa: E402
import upgrade_stats as ustats       # noqa: E402

OPUS_SETTINGS = audio.CODEC_SETTINGS["OPUS"]
LIBRI = upipe.LIBRI
MIN_FREE_GPU_GIB = 12.0


def lin8(reference: torch.Tensor, opus8: torch.Tensor) -> tuple[torch.Tensor, dict]:
    out = opd.project(reference.numpy(), opus8.numpy())
    return torch.from_numpy(out["component"].astype(np.float32)).unsqueeze(0), out


def process_signal(entry_path: str, second_pass: bool) -> tuple[dict, dict]:
    """One signal-only utterance: OPUS8 by the Stage 3 path, LIN8, checks and descriptors."""
    waveform, rate = torchaudio.load(LIBRI / entry_path)
    if rate != opd.SAMPLE_RATE or waveform.shape[0] != 1:
        raise RuntimeError(f"{entry_path}: {rate} Hz, {waveform.shape[0]} channels")
    opus8, info = audio.codec_round_trip(waveform, OPUS_SETTINGS)
    component, out = lin8(waveform[0], opus8[0])
    row = signal_row(waveform, opus8, component, out)
    row.update({"ogg_sha256": info["ogg_sha256"], "opus8_sha256": audio.tensor_sha256(opus8)})
    if second_pass:
        again, _ = lin8(waveform[0], audio.codec_round_trip(waveform, OPUS_SETTINGS)[0][0])
        row["second_pass_identical"] = audio.tensor_sha256(again) == row["lin8_sha256"]
    causal = opd.causal_projection(waveform[0].numpy(), opus8[0].numpy(), opd.L)["projection"][:waveform.shape[-1]]
    row["causal_span_nmse_db"] = opd.nmse_db(opus8[0].numpy(), causal)
    return row, {"reference": waveform, "opus8": opus8, "lin8": component}


def signal_row(reference: torch.Tensor, opus8: torch.Tensor, component: torch.Tensor, out: dict) -> dict:
    y = opus8.detach().double().numpy().reshape(-1)
    lin = component.detach().double().numpy().reshape(-1)
    nmse = opd.nmse_db(y, lin)
    return {
        "num_samples": int(y.size), "length_equals_ref": lin.size == reference.shape[-1] == y.size,
        "finite": bool(np.isfinite(lin).all() and np.isfinite(out["taps"]).all()),
        "normal_equation_residual": out["normal_equation_residual"], "lstsq_fallback": out["lstsq_fallback"],
        "nmse_db": nmse, "explained_energy_fraction": float(1 - 10 ** (nmse / 10)),
        "lin8_rms_change_db": float(10 * np.log10(np.sum(lin ** 2) / np.sum(reference.double().numpy() ** 2))),
        "opus8_rms_change_db": float(10 * np.log10(np.sum(y ** 2) / np.sum(reference.double().numpy() ** 2))),
        "lin8_sha256": audio.tensor_sha256(component), **opd.filter_descriptors(out["taps"]),
    }


def pooled(pairs: dict) -> tuple[dict, list[dict]]:
    """Frozen Stage 2B/3 pooled cross-spectral measures after the frozen alignment."""
    summary, curves = {}, []
    for name, acc in pairs.items():
        r = acc.results()
        summary[name] = {"h1_level_db": r["level_db"], "coherent_bandwidth_hz": r["coherent_bandwidth_hz"],
                         "mean_coherence_0_3500": float(np.mean(r["coherence"][s2b.FREQS <= 3500])),
                         "total_hf_power_db": r["total_hf_power_db"],
                         "image_coherence_4100_4900": r["image_coherence_4100_4900"]}
        curves += [{"pair": name, "frequency_hz": float(f), "h1_rel_db": float(r["h1_rel_db"][k]),
                    "coherence": float(r["coherence"][k])} for k, f in enumerate(s2b.FREQS)]
    return summary, curves


def summarise(rows: pd.DataFrame) -> dict:
    def q(col):
        v = rows[col].astype(float)
        return {"median": float(v.median()), "q25": float(v.quantile(0.25)), "q75": float(v.quantile(0.75)),
                "min": float(v.min()), "max": float(v.max())}
    cols = ["nmse_db", "explained_energy_fraction", "causal_span_nmse_db", "gain_0p5_2k_db", "rel_2000_db",
            "rel_2500_db", "rel_3000_db", "rel_3500_db", "rel_4000_db", "linear_delay_samples",
            "lin8_rms_change_db", "opus8_rms_change_db"]
    return {c: q(c) for c in cols if c in rows}


def signal_set(name: str, second_pass: bool) -> tuple[pd.DataFrame, dict, list[dict]]:
    sel = s3.read_sealed(design.SELECTION, "selection_sha256")[name]
    rows, pairs = [], {"REF->OPUS8": s2b.TransferAccumulator(), "REF->LIN8": s2b.TransferAccumulator()}
    for u in tqdm(sel["utterances"], desc=f"A1 {name}", unit="utt"):
        row, sig = process_signal(u["path"], second_pass)
        rows.append({"utterance": u["utterance"], "speaker_id": u["speaker_id"], "sex": u["sex"], **row})
        for key, other in [("REF->OPUS8", sig["opus8"]), ("REF->LIN8", sig["lin8"])]:
            ref_al, proc_al, _ = common.align_waveforms(sig["reference"], other)
            pairs[key].add(ref_al, proc_al)
    summary, curves = pooled(pairs)
    return pd.DataFrame(rows), summary, curves


def numeric_gate(rows: pd.DataFrame, n: int) -> dict:
    ok = (rows["finite"].astype(bool) & rows["length_equals_ref"].astype(bool)
          & (rows["normal_equation_residual"] <= design.NORMAL_EQUATION_TOLERANCE))
    return {"pass": bool(len(rows) == n and ok.all()), "passing": int(ok.sum()), "of": n,
            "max_normal_equation_residual": float(rows["normal_equation_residual"].max()),
            "lstsq_fallbacks": int(rows["lstsq_fallback"].astype(bool).sum())}


def calibrate_signal() -> int:
    spec = design.require_frozen_plan(committed=False)
    path = design.CALIBRATION / "signal_report.json"
    if path.exists():
        raise RuntimeError(f"{path} exists")
    design.CALIBRATION.mkdir(parents=True, exist_ok=True)
    rows, summary, curves = signal_set("calibration", second_pass=True)
    rows.to_csv(design.CALIBRATION / "signal_rows.csv", index=False)
    pd.DataFrame(curves).to_csv(design.CALIBRATION / "signal_curves.csv", index=False)
    iqr = float(rows["nmse_db"].quantile(0.75) - rows["nmse_db"].quantile(0.25))
    gates = {"C1": numeric_gate(rows, len(rows)),
             "C2": {"pass": bool(rows["second_pass_identical"].all()), "identical": int(rows["second_pass_identical"].sum()),
                    "of": len(rows)}}
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "part": "signal calibration",
              "n_utterances": len(rows), "gates": gates, "summary": summarise(rows), "pooled": summary,
              "collapse_tolerance_db": max(design.MIN_COLLAPSE_TOLERANCE_DB, iqr), "nmse_iqr_db": iqr,
              "descriptive_causal_span": "BSS Eval's causal span, computed for comparison only (selects nothing)",
              "files": {p.name: s3.file_sha256(p) for p in [design.CALIBRATION / "signal_rows.csv",
                                                             design.CALIBRATION / "signal_curves.csv"]}}
    report["pass"] = all(g["pass"] for g in gates.values())
    digest = s3.write_sealed(path, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], "gates": gates, "collapse_tolerance_db": report["collapse_tolerance_db"],
                      "nmse_db": report["summary"]["nmse_db"], "pooled": summary, "report_sha256": digest}, indent=1))
    return 0 if report["pass"] else 1


def gpu_state() -> dict:
    out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                          "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    free, total = torch.cuda.mem_get_info() if torch.cuda.is_available() else (0, 0)
    return {"nvidia_smi": out, "free_gib": free / 2 ** 30, "total_gib": total / 2 ** 30}


def require_gpu() -> dict:
    state = gpu_state()
    if state["free_gib"] < MIN_FREE_GPU_GIB:
        raise RuntimeError(f"GPU busy ({state}); nothing was run")
    return state


def lin8_generate(waveform: torch.Tensor) -> dict:
    opus8, _ = audio.codec_round_trip(waveform, OPUS_SETTINGS)
    component, _ = lin8(waveform[0], opus8[0])
    return {design.LIN8: (component, {})}


def calibrate_asr() -> int:
    spec = design.require_frozen_plan(committed=False)
    path = design.CALIBRATION / "asr_report.json"
    if path.exists():
        raise RuntimeError(f"{path} exists")
    signal = s3.read_sealed(design.CALIBRATION / "signal_report.json", "report_sha256")
    if not signal["pass"]:
        raise RuntimeError("signal calibration has not passed")
    gpu = require_gpu()
    selection = s3.load_selection("calibration")["utterances"]
    pipeline = s3.Pipeline()
    started = time.time()
    records = []
    for start in range(0, len(selection), upipe.CHUNK_UTTERANCES):
        records += pipeline.process_chunk("calibration", selection[start:start + upipe.CHUNK_UTTERANCES],
                                          audio.new_accumulators())
    new_audio = pd.DataFrame([r for rec in records for r in rec["audio"]])
    new_asr = pd.DataFrame([r for rec in records for r in rec["asr"]])
    frozen_audio = pd.read_csv(upgrade.S3_CALIBRATION / "audio_manifest.csv")
    frozen_asr = pd.read_csv(upgrade.S3_CALIBRATION / "asr_outputs.csv", keep_default_na=False)
    audio_cmp = frozen_audio.merge(new_audio, on=["utterance", "condition"], suffixes=("_frozen", "_new"))
    codec = audio_cmp["ogg_sha256_frozen"].notna()
    asr_cmp = frozen_asr.merge(new_asr, on=["utterance", "condition", "model"], suffixes=("_frozen", "_new"))
    env = {"audio_matched": len(audio_cmp), "audio_frozen": len(frozen_audio), "asr_matched": len(asr_cmp),
           "asr_frozen": len(frozen_asr),
           "waveform_mismatches": int((audio_cmp["waveform_sha256_frozen"] != audio_cmp["waveform_sha256_new"]).sum()),
           "ogg_mismatches": int((audio_cmp.loc[codec, "ogg_sha256_frozen"] != audio_cmp.loc[codec, "ogg_sha256_new"]).sum()),
           "hypothesis_mismatches": int((asr_cmp["hypothesis_frozen"] != asr_cmp["hypothesis_new"]).sum())}
    env["pass"] = bool(len(audio_cmp) == len(frozen_audio) == len(new_audio) and len(asr_cmp) == len(frozen_asr)
                       == len(new_asr) and env["waveform_mismatches"] == 0 and env["ogg_mismatches"] == 0
                       and env["hypothesis_mismatches"] == 0)
    rec = upipe.Recognisers.from_stage3_pipeline(pipeline)
    lin_records = []
    for start in range(0, len(selection), upipe.CHUNK_UTTERANCES):
        lin_records += upipe.process_chunk("calibration", selection[start:start + upipe.CHUNK_UTTERANCES],
                                           lin8_generate, [design.LIN8], rec)
    repeat = upipe.process_chunk("calibration", selection[:2], lin8_generate, [design.LIN8], rec)
    first = {(r["utterance"], r["model"]): r["hypothesis"] for record in lin_records[:2] for r in record["asr"]}
    lin_asr = pd.DataFrame([r for record in lin_records for r in record["asr"]])
    lin_audio = pd.DataFrame([r for record in lin_records for r in record["audio"]])
    path_check = {"repeat_hypotheses_identical": all(first[(r["utterance"], r["model"])] == r["hypothesis"]
                                                     for record in repeat for r in record["asr"]),
                  "repeat_audio_identical": all(
                      r["waveform_sha256"] == lin_audio.set_index("utterance").loc[r["utterance"], "waveform_sha256"]
                      for record in repeat for r in record["audio"]),
                  "empty_hypotheses": int((lin_asr["hypothesis"].astype(str).str.strip() == "").sum()),
                  "lengths_equal_ref": bool(lin_audio["length_equals_ref"].all()),
                  "nonfinite": int(lin_audio["nonfinite_count"].sum())}
    path_check["pass"] = bool(path_check["repeat_hypotheses_identical"] and path_check["repeat_audio_identical"]
                              and path_check["lengths_equal_ref"] and path_check["nonfinite"] == 0)
    new_audio.to_csv(design.CALIBRATION / "c3_env_audio_manifest.csv", index=False)
    new_asr.to_csv(design.CALIBRATION / "c3_env_asr_outputs.csv", index=False)
    lin_asr.to_csv(design.CALIBRATION / "c3_lin8_asr_outputs.csv", index=False)
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "part": "asr calibration (Stage 3 "
              "calibration set; no WER compared)", "gpu_at_start": gpu, "C3_environment": env, "C3_lin8_path": path_check,
              "seconds": time.time() - started,
              "files": {p.name: s3.file_sha256(p) for p in sorted(design.CALIBRATION.glob("c3_*.csv"))}}
    report["pass"] = bool(env["pass"] and path_check["pass"])
    digest = s3.write_sealed(path, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], "env": env, "lin8_path": path_check, "report_sha256": digest}, indent=1))
    return 0 if report["pass"] else 1


def validate() -> int:
    spec, freeze = design.require_code_freeze(committed=False)
    path = design.VALIDATION / "validation_report.json"
    if path.exists():
        raise RuntimeError(f"{path} exists")
    design.VALIDATION.mkdir(parents=True, exist_ok=True)
    rows, summary, curves = signal_set("validation", second_pass=True)
    rows.to_csv(design.VALIDATION / "validation_rows.csv", index=False)
    pd.DataFrame(curves).to_csv(design.VALIDATION / "validation_curves.csv", index=False)
    tol, cal_median = freeze["collapse_tolerance_db"], freeze["calibration_median_nmse_db"]
    val_median = float(rows["nmse_db"].median())
    gates = {"V1": numeric_gate(rows, len(rows)),
             "V2": {"pass": bool(val_median <= cal_median + tol), "validation_median_nmse_db": val_median,
                    "calibration_median_nmse_db": cal_median, "tolerance_db": tol,
                    "generalisation_gap_db": val_median - cal_median},
             "V3": {"pass": bool(rows["second_pass_identical"].all()), "identical": int(rows["second_pass_identical"].sum()),
                    "of": len(rows)}}
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
              "n_utterances": len(rows), "gates": gates, "summary": summarise(rows), "pooled": summary,
              "files": {p.name: s3.file_sha256(p) for p in [design.VALIDATION / "validation_rows.csv",
                                                             design.VALIDATION / "validation_curves.csv"]}}
    report["pass"] = all(g["pass"] for g in gates.values())
    report["status"] = "PASS: A1 may proceed to evaluation" if report["pass"] else "STOPPED before evaluation"
    digest = s3.write_sealed(path, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], "gates": gates, "summary_nmse": report["summary"]["nmse_db"],
                      "pooled": summary, "report_sha256": digest}, indent=1))
    return 0 if report["pass"] else 1


# ==================================================
# Evaluation (confirmation set)
# ==================================================

def a1_quantities(paired, seed: int = design.BOOT_SEED, n_boot: int = design.N_BOOT) -> list[dict]:
    rep = ustats.Replicates(paired, ustats.replicate_weights(paired, seed, n_boot))
    present = list(paired.values)
    rows = [ustats.interval_row(f"wer_{c}", "micro", rep.micro(c), "pp", 100.0) for c in present]
    for name, (a, b) in design.QUANTITIES.items():
        if a in present and b in present:
            rows.append(ustats.interval_row(name, "micro", rep.micro(a) - rep.micro(b), "pp", 100.0))
    if {"OPUS", "REF"} <= set(present):
        total = rep.micro("OPUS") - rep.micro("REF")
        safe = np.where(total > 0, total, 1.0)
        for name, a in [("S8", design.LIN8), ("S_primary", "LP")]:
            if a in present:
                row = ustats.interval_row(name, "ratio", np.where(total > 0, (rep.micro(a) - rep.micro("REF")) / safe,
                                                                  np.nan), "fraction", 1.0)
                row["replicates_denominator_le_0"] = int(np.sum(total[1:] <= 0))
                rows.append(row)
    return rows


def analyse_table(metrics: pd.DataFrame, conditions: list[str], **kwargs) -> pd.DataFrame:
    return ustats.analyse(metrics, conditions, a1_quantities, design.MODELS, **kwargs)


def stage3_metrics() -> pd.DataFrame:
    manifest = s3.read_sealed(upgrade.S3_CONFIRMATION / "outputs_sha256.json", "outputs_sha256")
    path = upgrade.S3_CONFIRMATION / "utterance_metrics.csv"
    if s3.file_sha256(path) != manifest["files"]["utterance_metrics.csv"]:
        raise RuntimeError("Stage 3 metrics differ from their sealed manifest")
    frame = pd.read_csv(path, keep_default_na=False)
    return frame[frame["condition"].isin(design.STAGE3_CONDITIONS)].copy()


def anchor_check(table: pd.DataFrame, anchors: dict) -> dict:
    worst = 0.0
    for model, scopes in anchors.items():
        for scope, quantities in scopes.items():
            for name, ref in quantities.items():
                got = ustats.lookup(table, model, name, "micro", scope)
                worst = max(worst, abs(got[0] - ref["estimate"]), abs(got[1] - ref["ci"][0]), abs(got[2] - ref["ci"][1]))
    return {"max_abs_difference_pp": worst, "tolerance_pp": design.ANCHOR_TOLERANCE_PP,
            "pass": bool(worst <= design.ANCHOR_TOLERANCE_PP)}


def evaluate() -> int:
    spec, freeze = design.require_code_freeze(committed=True)
    validation = s3.read_sealed(design.VALIDATION / "validation_report.json", "report_sha256")
    upgrade.tracked_and_clean(design.VALIDATION / "validation_report.json")
    if not validation["pass"]:
        raise RuntimeError("A1 validation did not pass: A1 is STOPPED")
    path = design.EVALUATION / "evaluation_report.json"
    if path.exists():
        raise RuntimeError(f"{path} exists")
    if design.RAW.exists() or design.DECISION.exists():
        raise RuntimeError("A1 recognition or decision outputs exist before evaluation (E5)")
    design.EVALUATION.mkdir(parents=True, exist_ok=True)
    manifest = pd.read_csv(upgrade.S3_CONFIRMATION / "audio_manifest.csv")
    frozen = manifest[manifest["condition"] == "OPUS"].set_index("utterance")
    selection = s3.load_selection("confirmation")["utterances"]
    rows = []
    started = time.time()
    for entry in tqdm(selection, desc="A1 evaluate", unit="utt"):
        waveform = upipe.load_reference(entry)
        opus8, info = audio.codec_round_trip(waveform, OPUS_SETTINGS)
        component, out = lin8(waveform[0], opus8[0])
        row = {"utterance": entry["utterance"], "subset": entry["subset"], "speaker_id": entry["speaker_id"],
               "ogg_identical": info["ogg_sha256"] == frozen.loc[entry["utterance"], "ogg_sha256"],
               "opus8_identical": audio.tensor_sha256(opus8) == frozen.loc[entry["utterance"], "waveform_sha256"],
               **signal_row(waveform, opus8, component, out)}
        rows.append(row)
    rows = pd.DataFrame(rows)
    rows.to_csv(design.EVALUATION / "evaluation_rows.csv", index=False)
    table = analyse_table(stage3_metrics(), design.STAGE3_CONDITIONS)
    gates = {"E1": {"pass": bool(rows["ogg_identical"].all() and rows["opus8_identical"].all() and len(rows) == len(selection)),
                    "ogg_identical": int(rows["ogg_identical"].sum()), "opus8_identical": int(rows["opus8_identical"].sum()),
                    "of": len(selection)},
             "E2": numeric_gate(rows, len(selection)),
             "E3": {"environment_differences": design.environment_differences(spec)},
             "E4": anchor_check(table, spec["stage3_anchors"]),
             "E5": {"no_a1_recognition_outputs": not design.RAW.exists(), "pass": not design.RAW.exists()}}
    gates["E3"]["pass"] = not gates["E3"]["environment_differences"]
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
              "validation_report_sha256": validation["report_sha256"], "n_utterances": len(rows), "gates": gates,
              "summary": summarise(rows), "seconds_per_utterance": (time.time() - started) / len(rows),
              "rows_sha256": s3.file_sha256(design.EVALUATION / "evaluation_rows.csv")}
    report["pass"] = all(g["pass"] for g in gates.values())
    report["status"] = "PASS: LIN8 recognition may run" if report["pass"] else "STOPPED before recognition"
    digest = s3.write_sealed(path, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], **{k: g["pass"] for k, g in gates.items()},
                      "nmse_db": report["summary"]["nmse_db"], "report_sha256": digest}, indent=1))
    return 0 if report["pass"] else 1


def run() -> str:
    spec, freeze = design.require_code_freeze(committed=True)
    report = s3.read_sealed(design.EVALUATION / "evaluation_report.json", "report_sha256")
    if not report["pass"] or report["code_freeze_sha256"] != freeze["freeze_sha256"]:
        raise RuntimeError("A1 evaluation checks have not passed under this code freeze")
    if s3.file_sha256(design.EVALUATION / "evaluation_rows.csv") != report["rows_sha256"]:
        raise RuntimeError("evaluation rows differ from the sealed report")
    gpu = require_gpu()
    rows = pd.read_csv(design.EVALUATION / "evaluation_rows.csv")
    expected = dict(zip(rows["utterance"], rows["lin8_sha256"]))
    selection = s3.load_selection("confirmation")

    def check(entry, audio_rows):
        for row in audio_rows:
            if row["waveform_sha256"] != expected[entry["utterance"]]:
                raise RuntimeError(f"{entry['utterance']}: LIN8 differs from the evaluated audio")

    design.RAW.mkdir(parents=True, exist_ok=True)
    (design.RAW / "gpu_at_start.json").write_text(json.dumps(gpu, indent=1))
    return upipe.run_set("confirmation", selection["utterances"], design.RAW, lin8_generate, [design.LIN8],
                         upipe.Recognisers(), freeze["code_sha256"], selection["selection_sha256"], check=check)


def analyse() -> dict:
    spec, freeze = design.require_code_freeze(committed=True)
    if design.DECISION.exists() or design.BOOTSTRAP.exists():
        raise RuntimeError("A1 has already been analysed (single analysis only)")
    manifest = s3.read_sealed(design.RAW / "outputs_sha256.json", "outputs_sha256")
    path = design.RAW / "utterance_metrics.csv"
    if s3.file_sha256(path) != manifest["files"]["utterance_metrics.csv"]:
        raise RuntimeError("A1 metrics differ from their sealed manifest")
    new = pd.read_csv(path, keep_default_na=False)
    metrics = pd.concat([stage3_metrics(), new[new["condition"] == design.LIN8]], ignore_index=True)
    table = analyse_table(metrics, design.CONDITIONS)
    table.to_csv(design.BOOTSTRAP, index=False)
    cells = {}
    for m in design.MODELS:
        cells[m] = {q: list(ustats.lookup(table, m, q, "micro", "pooled")) for q in design.QUANTITIES}
        cells[m]["S8"] = list(ustats.lookup(table, m, "S8", "ratio", "pooled"))
        cells[m]["S_primary"] = list(ustats.lookup(table, m, "S_primary", "ratio", "pooled"))
    outcome = design.a1_outcome(cells)
    decision = {"created_utc": s3.now(), "analysis": "A1: best-linear (OPD target) decomposition of 8 kbit/s Opus; "
                "post-confirmation sensitivity; S8 is an inclusive linear-loss sensitivity share, not a bandwidth share",
                "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
                "outputs_sha256": manifest["outputs_sha256"], "anchor_reproduction": anchor_check(table, spec["stage3_anchors"]),
                "cells": cells, "outcome": outcome, "bootstrap_sha256": s3.file_sha256(design.BOOTSTRAP)}
    s3.write_sealed(design.DECISION, s3.native(decision), "decision_sha256")
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["calibrate", "validate", "evaluate", "run", "analyse"])
    parser.add_argument("part", nargs="?", choices=["signal", "asr"])
    args = parser.parse_args()
    os.chdir(design.ROOT)
    if args.command == "calibrate":
        return calibrate_signal() if args.part == "signal" else calibrate_asr()
    if args.command == "validate":
        return validate()
    if args.command == "evaluate":
        return evaluate()
    if args.command == "run":
        print(f"A1 outputs manifest {run()}")
        return 0
    decision = analyse()
    print(json.dumps({"outcome": decision["outcome"], "cells": decision["cells"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
