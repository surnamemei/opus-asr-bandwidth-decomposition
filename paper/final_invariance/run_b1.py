"""
B1 runner: 8-kbit/s application-mode sensitivity (written after the plan was sealed).

Commands, strictly in the order of the frozen plan (B1_PLAN.md):

    calibrate encode   calibration set only, no ASR: OPUS_AUDIO8 reproduction (K1), OPUS_VOIP8 encode and
                       decode (K2), readback (K3), packets (K4), environment (K5), determinism (K6), and the
                       descriptive signal and bitrate summaries.
    calibrate asr      calibration set only (GPU): K7 (the frozen Stage 3 pipeline reproduces the sealed
                       Stage 3 calibration outputs; OPUS_VOIP8 recognised, the first 2 utterances again);
                       no WER is compared.
    validate           confirmation set, no ASR: K1-K5, K8, K9 and the descriptive summaries.
    run                recognition of OPUS_VOIP8, once.
    analyse            A, V and D_app with intervals; outcome per recogniser.

calibrate needs the sealed plan; validate, run and analyse need the committed plan and code freeze.
"""

import argparse
import collections
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / "paper" / "reviewer_sensitivity"), str(ROOT / "paper" / "taslp_upgrade"),
                str(ROOT / "paper")]

import numpy as np                   # noqa: E402
import pandas as pd                  # noqa: E402
import torch                         # noqa: E402
from tqdm import tqdm                # noqa: E402

import b1_design as design           # noqa: E402
import common                        # noqa: E402
import opus_direct                   # noqa: E402
import reviewer_pipeline as rp       # noqa: E402
import run_lowpass_validation as s2b  # noqa: E402
import run_stage3 as s3              # noqa: E402
import stage3_audio as audio         # noqa: E402
import upgrade_design as upgrade     # noqa: E402
import upgrade_pipeline as upipe     # noqa: E402
import upgrade_stats as ustats       # noqa: E402

SAMPLE_RATE = audio.SAMPLE_RATE
VALIDATION_REPORT = design.VALIDATION / "validation_report.json"
VALIDATION_ROWS = design.VALIDATION / "validation_rows.csv"
PAIRS = [(design.REF, design.AUDIO8), (design.REF, design.VOIP8)]
SETTINGS = {design.AUDIO8: design.AUDIO8_SETTINGS, design.VOIP8: design.VOIP8_SETTINGS}
PREFIX = {design.AUDIO8: "audio8", design.VOIP8: "voip8"}
MIN_FREE_GPU_GIB = 12.0


# ==================================================
# One utterance: both encodes, checks and descriptive measures
# ==================================================

def coded(waveform: torch.Tensor, name: str) -> dict:
    """One frozen encode with the condition's settings, decoded by the frozen FFmpeg path at 16 kHz."""
    out = rp.encode_and_decode(waveform, SETTINGS[name], 1, False)
    infos = [opus_direct.packet_info(p) for p in out["result"].packets]
    out["packets"] = {
        "modes": ";".join(f"{k}:{v}" for k, v in sorted(collections.Counter(i["mode"] for i in infos).items())),
        "bandwidths": ";".join(sorted({i["bandwidth"] for i in infos})),
        "libopus_bandwidths": ";".join(sorted({i["libopus_bandwidth"] for i in infos})),
        "frame_ms": ";".join(str(v) for v in sorted({i["frame_ms"] for i in infos})),
        "any_stereo": any(i["stereo"] for i in infos),
        "share_silk": sum(i["mode"] == "SILK" for i in infos) / len(infos),
    }
    return out


def condition_row(name: str, waveform: torch.Tensor, c: dict, stage3: dict | None) -> dict:
    p = PREFIX[name]
    a = upipe.audio_row(name, c["ffmpeg"], waveform, {})
    metrics, _, aligned = s2b.signal_metrics(waveform, c["ffmpeg"])
    ogg_sha256 = hashlib.sha256(c["result"].ogg).hexdigest()
    row = {
        f"{p}_ogg_sha256": ogg_sha256, f"{p}_waveform_sha256": a["waveform_sha256"],
        f"{p}_length_equals_ref": bool(a["length_equals_ref"]), f"{p}_nonfinite": int(a["nonfinite_count"]),
        f"{p}_readback_mismatches": ";".join(c["readback_mismatches"]),
        f"{p}_queried_application": int(c["result"].queried["application"]),
        f"{p}_packet_modes": c["packets"]["modes"], f"{p}_bandwidths": c["packets"]["bandwidths"],
        f"{p}_libopus_bandwidths": c["packets"]["libopus_bandwidths"], f"{p}_frame_ms": c["packets"]["frame_ms"],
        f"{p}_any_stereo": bool(c["packets"]["any_stereo"]), f"{p}_share_silk": c["packets"]["share_silk"],
        f"{p}_num_packets": int(c["summary"]["num_packets"]), f"{p}_payload_kbps": float(c["summary"]["payload_kbps"]),
        f"{p}_container_kbps": float(c["summary"]["container_kbps"]),
        f"{p}_clip_count": int(a["clip_count"]), f"{p}_peak": float(a["peak"]), f"{p}_rms_change_db": a["rms_change_db"],
        f"{p}_lag_vs_ref_samples": int(a["lag_vs_ref_samples"]),
        f"{p}_lsd_0_3k_db": float(metrics["lsd_0_3k_db"]), f"{p}_coherence_0_3500": audio.mean_coherence(*aligned),
    }
    if stage3 is not None:
        row[f"{p}_stage3_ogg_identical"] = ogg_sha256 == stage3["ogg_sha256"]
        row[f"{p}_stage3_waveform_identical"] = a["waveform_sha256"] == stage3["waveform_sha256"]
    return row


def process(selection: list[dict], stage3: dict, desc: str) -> tuple[pd.DataFrame, dict, list[dict]]:
    """Every utterance: both conditions; an encode or decode error is recorded (it fails K2)."""
    accumulators = upipe.new_accumulators(PAIRS)
    rows, errors = [], []
    for entry in tqdm(selection, desc=desc, unit="utt"):
        waveform = upipe.load_reference(entry)
        row = {"utterance": entry["utterance"], "subset": entry["subset"], "speaker_id": entry["speaker_id"],
               "num_samples_ref": int(waveform.shape[-1])}
        try:
            for name in [design.AUDIO8, design.VOIP8]:
                c = coded(waveform, name)
                row.update(condition_row(name, waveform, c, stage3[entry["utterance"]] if name == design.AUDIO8 else None))
                aligned_ref, aligned_proc, _ = common.align_waveforms(waveform, c["ffmpeg"])
                accumulators[(design.REF, name)].add(aligned_ref, aligned_proc)
        except RuntimeError as error:
            errors.append({"utterance": entry["utterance"], "error": str(error)})
            continue
        rows.append(row)
    return pd.DataFrame(rows), accumulators, errors


def checks(rows: pd.DataFrame, n_expected: int, errors: list[dict], spec: dict) -> dict:
    """K1-K5 over a set of utterance rows (a check passes only if every utterance passes)."""
    complete = bool(not errors and len(rows) == n_expected)
    k = {"K1": {"ogg_identical": int(rows["audio8_stage3_ogg_identical"].sum()),
                "waveform_identical": int(rows["audio8_stage3_waveform_identical"].sum()), "of": n_expected}}
    k["K1"]["pass"] = bool(complete and k["K1"]["ogg_identical"] == n_expected
                           and k["K1"]["waveform_identical"] == n_expected)
    k["K2"] = {"errors": errors, "encoded": int(len(rows)), "of": n_expected,
               "length_equals_ref": int(rows["voip8_length_equals_ref"].sum()),
               "nonfinite": int(rows["voip8_nonfinite"].sum())}
    k["K2"]["pass"] = bool(complete and k["K2"]["length_equals_ref"] == n_expected and k["K2"]["nonfinite"] == 0)
    k["K3"] = {}
    for name, p, code in [(design.AUDIO8, "audio8", 2049), (design.VOIP8, "voip8", 2048)]:
        mismatched = rows[rows[f"{p}_readback_mismatches"].fillna("").astype(str) != ""]
        k["K3"][name] = {"utterances_with_mismatches": int(len(mismatched)),
                         "queried_application": sorted(int(v) for v in rows[f"{p}_queried_application"].unique()),
                         "expected_application": code}
    k["K3"]["pass"] = bool(complete and all(v["utterances_with_mismatches"] == 0 and v["queried_application"] ==
                                            [v["expected_application"]] for v in k["K3"].values()))
    k["K4"] = {}
    for name, p in PREFIX.items():
        k["K4"][name] = {"bandwidths": sorted(rows[f"{p}_bandwidths"].astype(str).unique().tolist()),
                         "frame_ms": sorted(rows[f"{p}_frame_ms"].astype(str).unique().tolist()),
                         "any_stereo": bool(rows[f"{p}_any_stereo"].any()),
                         "packet_modes_reported": collections.Counter(
                             m.split(":")[0] for v in rows[f"{p}_packet_modes"] for m in str(v).split(";")),
                         "utterances_all_silk": int((rows[f"{p}_share_silk"] == 1.0).sum())}
    k["K4"]["pass"] = bool(complete and all(v["bandwidths"] == ["NB"] and v["frame_ms"] == ["20.0"] and not v["any_stereo"]
                                            for v in k["K4"].values()))
    k["K5"] = {"environment_differences": design.environment_differences(spec),
               "libopus": opus_direct.libopus_version(), "libopus_path": opus_direct.libopus_path()}
    k["K5"]["pass"] = not k["K5"]["environment_differences"]
    return k


def band_power_db(acc: s2b.TransferAccumulator, band: tuple[float, float]) -> float:
    mask = (s2b.FREQS >= band[0]) & (s2b.FREQS <= band[1])
    return float(10 * np.log10(acc.syy[mask].sum() / acc.sxx[mask].sum()))


def descriptives(rows: pd.DataFrame, accumulators: dict) -> dict:
    """Descriptive only (never a gate): bitrate, clipping, lag, level, in-band fidelity, high band, mirror image."""
    out = {}
    for name, p in PREFIX.items():
        pooled = accumulators[(design.REF, name)].results()
        q = lambda col: {"median": float(rows[col].median()), "p05": float(rows[col].quantile(0.05)),
                         "p95": float(rows[col].quantile(0.95))}
        out[name] = {
            "payload_kbps": q(f"{p}_payload_kbps"), "container_kbps": q(f"{p}_container_kbps"),
            "clipped_samples_total": int(rows[f"{p}_clip_count"].sum()),
            "utterances_with_clipping": int((rows[f"{p}_clip_count"] > 0).sum()),
            "lag_vs_ref_counts": {str(k): int(v) for k, v in
                                  rows[f"{p}_lag_vs_ref_samples"].value_counts().sort_index().items()},
            "rms_change_db": q(f"{p}_rms_change_db"), "lsd_0_3k_db_vs_ref": q(f"{p}_lsd_0_3k_db"),
            "coherence_0_3500_vs_ref": q(f"{p}_coherence_0_3500"),
            "pooled_power_4000_8000_db": band_power_db(accumulators[(design.REF, name)], design.POWER_BAND_HZ),
            "pooled_total_hf_power_db": pooled["total_hf_power_db"],
            "pooled_mirror_coherence_4100_4900": pooled["image_coherence_4100_4900"],
            "pooled_mean_coherence_0_3500": float(np.mean(pooled["coherence"][s2b.FREQS <= 3500])),
            "pooled_h1_level_db": pooled["level_db"],
            "pooled_coherent_bandwidth_hz": pooled["coherent_bandwidth_hz"],
        }
    out["paired_payload_kbps_difference_voip_minus_audio"] = {
        "median": float((rows["voip8_payload_kbps"] - rows["audio8_payload_kbps"]).median())}
    out["voip8_waveform_identical_to_audio8"] = int((rows["voip8_waveform_sha256"] == rows["audio8_waveform_sha256"]).sum())
    return out


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
    frame = frame[frame["condition"] == design.STAGE3_LABEL[design.AUDIO8]]
    return {r["utterance"]: {"ogg_sha256": r["ogg_sha256"], "waveform_sha256": r["waveform_sha256"]}
            for r in frame.to_dict(orient="records")}


def stage3_metrics() -> pd.DataFrame:
    """Sealed Stage 3 confirmation metrics of REF and OPUS (renamed OPUS_AUDIO8)."""
    frame = verified_csv(upgrade.S3_CONFIRMATION, "utterance_metrics.csv", keep_default_na=False)
    labels = {v: k for k, v in design.STAGE3_LABEL.items()}
    frame = frame[frame["condition"].isin(labels)].copy()
    frame["condition"] = frame["condition"].map(labels)
    return frame


# ==================================================
# Statistics (frozen upgrade_stats machinery, Stage 3's seed on Stage 3's speakers)
# ==================================================

def b1_quantities(paired, seed: int = design.SEED, n_boot: int = design.N_BOOT) -> list[dict]:
    rep = ustats.Replicates(paired, ustats.replicate_weights(paired, seed, n_boot))
    present = list(paired.values)
    rows = [ustats.interval_row(f"wer_{c}", "micro", rep.micro(c), "pp", 100.0) for c in present]
    for name, (a, b) in design.QUANTITIES.items():
        if a in present and b in present:
            rows.append(ustats.interval_row(name, "micro", rep.micro(a) - rep.micro(b), "pp", 100.0))
            rows.append(ustats.interval_row(name, "micro_cer", rep.cer(a) - rep.cer(b), "pp", 100.0))
            for field in ["substitutions", "deletions", "insertions"]:
                rows.append(ustats.interval_row(f"{name}_{field[0].upper()}", "micro_error_type",
                                                rep.error_type_difference(a, b, field), "per 100 words", 100.0))
    return rows


def analyse_table(metrics: pd.DataFrame, conditions: list[str], **kwargs) -> pd.DataFrame:
    return ustats.analyse(metrics, conditions, b1_quantities, design.MODELS, **kwargs)


def anchor_check(table: pd.DataFrame, anchors: dict) -> dict:
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
# Calibration (calibration set only)
# ==================================================

def calibrate_encode() -> int:
    spec = design.require_frozen_plan(committed=False)
    path = design.CALIBRATION_PARTS["encode"]
    if path.exists():
        raise RuntimeError(f"{path} exists")
    design.CALIBRATION.mkdir(parents=True, exist_ok=True)
    selection = s3.load_selection("calibration")["utterances"]
    stage3 = stage3_opus(upgrade.S3_CALIBRATION)
    started = time.time()
    first, accumulators, errors = process(selection, stage3, "B1 calibrate, pass 1")
    second, _, errors_second = process(selection, stage3, "B1 calibrate, pass 2")
    seconds = time.time() - started
    k = checks(first, len(selection), errors + errors_second, spec)
    same = {p: bool((first[f"{p}_ogg_sha256"] == second[f"{p}_ogg_sha256"]).all()
                    and (first[f"{p}_waveform_sha256"] == second[f"{p}_waveform_sha256"]).all()) for p in PREFIX.values()}
    k["K6"] = {"identical_second_pass": same, "of": len(selection), "pass": bool(all(same.values()))}
    first.to_csv(design.CALIBRATION / "encode_rows.csv", index=False)
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "part": "encode",
              "purpose": "calibration set only, no ASR: K1-K6 on the 20 Stage 3 calibration utterances and the "
                         "descriptive summaries",
              "n_utterances": len(selection), "checks": s3.native(k), "descriptive": descriptives(first, accumulators),
              "seconds_per_utterance_per_pass": seconds / (2 * len(selection)),
              "rows_sha256": s3.file_sha256(design.CALIBRATION / "encode_rows.csv")}
    report["pass"] = all(v["pass"] for v in k.values())
    digest = s3.write_sealed(path, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], **{n: v["pass"] for n, v in k.items()},
                      "descriptive": report["descriptive"], "report_sha256": digest}, indent=1, default=str))
    return 0 if report["pass"] else 1


def free_gpu_gib() -> float:
    free, _ = torch.cuda.mem_get_info()
    return free / 2 ** 30


def gpu_state() -> dict:
    import subprocess
    query = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
                            "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.strip()
    return {"utc": s3.now(), "nvidia_smi": query, "compute_apps": apps,
            "free_gib": free_gpu_gib() if torch.cuda.is_available() else None}


def require_gpu() -> dict:
    if not torch.cuda.is_available() or free_gpu_gib() < MIN_FREE_GPU_GIB:
        raise RuntimeError(f"the GPU is busy (need {MIN_FREE_GPU_GIB} GiB free); nothing was run")
    return gpu_state()


def environment_k7(pipeline: s3.Pipeline, selection: list[dict]) -> dict:
    """K7 (first part): the frozen Stage 3 pipeline against the sealed Stage 3 calibration outputs."""
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
    out = {"rows": {"audio_frozen": len(frozen_audio), "audio_new": len(new_audio), "audio_matched": len(audio_cmp),
                    "asr_frozen": len(frozen_asr), "asr_new": len(new_asr), "asr_matched": len(asr_cmp)},
           "waveform_mismatches": int((audio_cmp["waveform_sha256_frozen"] != audio_cmp["waveform_sha256_new"]).sum()),
           "ogg_mismatches": int((audio_cmp.loc[codec, "ogg_sha256_frozen"] != audio_cmp.loc[codec, "ogg_sha256_new"]).sum()),
           "hypothesis_mismatches": int((asr_cmp["hypothesis_frozen"] != asr_cmp["hypothesis_new"]).sum())}
    out["pass"] = bool(len(audio_cmp) == len(frozen_audio) == len(new_audio)
                       and len(asr_cmp) == len(frozen_asr) == len(new_asr)
                       and out["waveform_mismatches"] == 0 and out["ogg_mismatches"] == 0
                       and out["hypothesis_mismatches"] == 0)
    return out


def voip8_generate(waveform: torch.Tensor) -> dict:
    c = rp.encode_and_decode(waveform, design.VOIP8_SETTINGS, 1, False)
    return {design.VOIP8: (c["ffmpeg"], {"ogg_sha256": hashlib.sha256(c["result"].ogg).hexdigest(),
                                         "payload_kbps": c["summary"]["payload_kbps"]})}


def calibrate_asr() -> int:
    spec = design.require_frozen_plan(committed=False)
    path = design.CALIBRATION_PARTS["asr"]
    if path.exists():
        raise RuntimeError(f"{path} exists")
    encode_part = s3.read_sealed(design.CALIBRATION_PARTS["encode"], "report_sha256")
    if not encode_part["pass"] or encode_part["spec_sha256"] != spec["spec_sha256"]:
        raise RuntimeError("the B1 encode calibration has not passed under this plan")
    gpu = require_gpu()
    selection = s3.load_selection("calibration")["utterances"]
    pipeline = s3.Pipeline()
    k7_env = environment_k7(pipeline, selection)
    rec = upipe.Recognisers.from_stage3_pipeline(pipeline)
    records = []
    for start in range(0, len(selection), upipe.CHUNK_UTTERANCES):
        records += upipe.process_chunk("calibration", selection[start:start + upipe.CHUNK_UTTERANCES],
                                       voip8_generate, [design.VOIP8], rec)
    repeat = upipe.process_chunk("calibration", selection[:2], voip8_generate, [design.VOIP8], rec)
    audio_rows = pd.DataFrame([r for record in records for r in record["audio"]])
    asr_rows = pd.DataFrame([r for record in records for r in record["asr"]])
    encoded = pd.read_csv(design.CALIBRATION / "encode_rows.csv")
    same = audio_rows.merge(encoded[["utterance", "voip8_waveform_sha256"]], on="utterance")
    first = {(r["utterance"], r["model"]): r["hypothesis"] for record in records[:2] for r in record["asr"]}
    k7 = {"environment": k7_env,
          "audio_identical_to_encode_part": int((same["waveform_sha256"] == same["voip8_waveform_sha256"]).sum()),
          "of": len(selection),
          "repeat_hypotheses_identical": all(first[(r["utterance"], r["model"])] == r["hypothesis"]
                                             for record in repeat for r in record["asr"]),
          "empty_hypotheses": int((asr_rows["hypothesis"].astype(str).str.strip() == "").sum())}
    k7["pass"] = bool(k7_env["pass"] and k7["audio_identical_to_encode_part"] == len(selection)
                      and k7["repeat_hypotheses_identical"])
    asr_rows.to_csv(design.CALIBRATION / "k7_asr_outputs.csv", index=False)
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "part": "asr", "gpu_at_start": gpu,
              "purpose": "calibration set only: K7 (environment reproduction and the OPUS_VOIP8 recognition path); "
                         "no WER is compared",
              "K7": k7, "files": {"k7_asr_outputs.csv": s3.file_sha256(design.CALIBRATION / "k7_asr_outputs.csv")}}
    report["pass"] = k7["pass"]
    digest = s3.write_sealed(path, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], "K7": {k: v for k, v in k7.items() if k != "environment"},
                      "environment": k7_env["pass"], "report_sha256": digest}, indent=1))
    return 0 if report["pass"] else 1


# ==================================================
# validate, run, analyse (confirmation set; need the committed plan and code freeze)
# ==================================================

def committed_state() -> dict:
    return {str(p): upgrade.git("log", "-1", "--format=%H %cI", "--", str(p)).stdout.strip()
            for p in [design.SPEC_JSON, design.PLAN_MD, design.CODE_FREEZE]}


def validate() -> int:
    spec, freeze = design.require_code_freeze(committed=True)
    if VALIDATION_REPORT.exists():
        raise RuntimeError(f"{VALIDATION_REPORT} exists")
    if design.RAW.exists() or design.DECISION.exists():
        raise RuntimeError("B1 recognition or analysis outputs exist before validation (K9)")
    design.VALIDATION.mkdir(parents=True, exist_ok=True)
    selection = s3.load_selection("confirmation")["utterances"]
    stage3 = stage3_opus(upgrade.S3_CONFIRMATION)
    started = time.time()
    rows, accumulators, errors = process(selection, stage3, "B1 validate")
    k = checks(rows, len(selection), errors, spec)
    k["K8"] = anchor_check(analyse_table(stage3_metrics(), [design.REF, design.AUDIO8]), spec["stage3_anchors"])
    k["K9"] = {"committed": committed_state(), "no_b1_recognition_outputs": not design.RAW.exists(),
               "pass": not design.RAW.exists()}
    rows.to_csv(VALIDATION_ROWS, index=False)
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
              "n_utterances": len(selection), "checks": s3.native(k), "descriptive": descriptives(rows, accumulators),
              "seconds_per_utterance": (time.time() - started) / len(selection),
              "rows_sha256": s3.file_sha256(VALIDATION_ROWS)}
    report["pass"] = all(v["pass"] for v in k.values())
    report["status"] = "PASS: recognition may run" if report["pass"] else f"{design.STOPPED} before recognition"
    digest = s3.write_sealed(VALIDATION_REPORT, s3.native(report), "report_sha256")
    print(json.dumps({"pass": report["pass"], **{n: v["pass"] for n, v in k.items()},
                      "descriptive": report["descriptive"], "report_sha256": digest}, indent=1, default=str))
    return 0 if report["pass"] else 1


def run() -> str:
    spec, freeze = design.require_code_freeze(committed=True)
    report = s3.read_sealed(VALIDATION_REPORT, "report_sha256")
    if not report["pass"] or report["code_freeze_sha256"] != freeze["freeze_sha256"]:
        raise RuntimeError("B1 validation has not passed under this code freeze; B1 is STOPPED")
    if s3.file_sha256(VALIDATION_ROWS) != report["rows_sha256"]:
        raise RuntimeError("validation rows differ from the sealed report")
    upgrade.tracked_and_clean(VALIDATION_REPORT)     # K9: the validation is committed before any B1 WER
    gpu = require_gpu()
    design.RAW.mkdir(parents=True, exist_ok=True)
    (design.RAW / "gpu_at_start.json").write_text(json.dumps(gpu, indent=1))
    rows = pd.read_csv(VALIDATION_ROWS)
    validated = dict(zip(rows["utterance"], rows["voip8_waveform_sha256"]))
    selection = s3.load_selection("confirmation")

    def check(entry, audio_rows):
        for row in audio_rows:
            if row["waveform_sha256"] != validated[entry["utterance"]]:
                raise RuntimeError(f"{entry['utterance']}: audio differs from the validated audio")

    return upipe.run_set("confirmation", selection["utterances"], design.RAW, voip8_generate, [design.VOIP8],
                         upipe.Recognisers(), freeze["code_sha256"], selection["selection_sha256"], check=check)


def analyse() -> dict:
    spec, freeze = design.require_code_freeze(committed=True)
    if design.DECISION.exists():
        raise RuntimeError(f"{design.DECISION} is sealed and exists")
    manifest = s3.read_sealed(design.RAW / "outputs_sha256.json", "outputs_sha256")
    new = verified_csv(design.RAW, "utterance_metrics.csv", keep_default_na=False)
    new = new[new["condition"] == design.VOIP8]
    metrics = pd.concat([stage3_metrics(), new], ignore_index=True)
    table = analyse_table(metrics, design.CONDITIONS)
    anchors = anchor_check(table, spec["stage3_anchors"])
    table.to_csv(design.BOOTSTRAP, index=False)
    cells = {}
    for model in design.MODELS:
        d = ustats.lookup(table, model, "D_app", "micro", "pooled")
        cells[model] = {q: list(ustats.lookup(table, model, q, "micro", "pooled")) for q in design.QUANTITIES}
        cells[model]["per_subset"] = {s: {q: list(ustats.lookup(table, model, q, "micro", s)) for q in design.QUANTITIES}
                                      for s in ["test-clean", "test-other"]}
        cells[model]["outcome"] = design.b1_outcome(d[1], d[2])
    decision = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
                "validation_report_sha256": s3.read_sealed(VALIDATION_REPORT, "report_sha256")["report_sha256"],
                "outputs_sha256": manifest["outputs_sha256"], "anchor_reproduction": anchors,
                "analysis": "B1: 8-kbit/s application-mode sensitivity of the total penalty (post-confirmation "
                            "configuration sensitivity; not a decomposition; no equivalence claim; no VOIP share)",
                "cells": cells, "outcome": None, "note": "per recogniser only; no combined outcome",
                "bootstrap_sha256": s3.file_sha256(design.BOOTSTRAP)}
    s3.write_sealed(design.DECISION, s3.native(decision), "decision_sha256")
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["calibrate", "validate", "run", "analyse"])
    parser.add_argument("part", nargs="?", choices=["encode", "asr"])
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.command == "calibrate":
        if args.part is None:
            parser.error("calibrate needs a part: encode or asr")
        return calibrate_encode() if args.part == "encode" else calibrate_asr()
    if args.part is not None:
        parser.error(f"{args.command} takes no part")
    if args.command == "validate":
        return validate()
    if args.command == "run":
        print(f"B1 outputs manifest {run()}")
        return 0
    decision = analyse()
    print(json.dumps({m: c["outcome"] for m, c in decision["cells"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
