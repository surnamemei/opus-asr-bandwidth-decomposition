"""
Reviewer-concern sensitivity analyses R1-R3: the runner (written at step RS1).

Commands, strictly in the order of the frozen plan (00_REVIEWER_SENSITIVITY_PLAN.md):

    calibrate            RS1  gate E1 on the Stage 3 calibration set; on the Stage 2B calibration
                              set R1-C1, the SILK40_LIB measurement, R1-REUSE (control-reuse gate)
                              and, only if it fails, LP_LIBOPUS; R2-C1 and the SURR8 fit; then E2 on
                              the Stage 3 calibration set. Sealed calibration report and filters.
    validate signal      RS3  R1-V and R2-V1..V6 on the signal-only validation subset (no ASR).
    validate confirmation RS3 R1-G1..G3 and the identity check on the confirmation set (no ASR).
    validate sweep       RS3  R3-G0..G5 on the sweep set (no ASR).
                              Each part seals its own report; when all three exist, the one
                              validation report that holds every gate result is sealed.
    run                  RS4  RS4a (confirmation set, R1 and R2) and RS4b (sweep set, R3): ASR, once.
    analyse              RS5  estimates, intervals and outcomes; sealed decision records.

calibrate needs the committed plan; every later command also needs the sealed code freeze
(reviewer_design.py freeze-code), which follows calibrate.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "taslp_upgrade"), str(HERE.parent)]

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402
import torch                # noqa: E402
from tqdm import tqdm       # noqa: E402

import lowpass              # noqa: E402
import opus_direct          # noqa: E402
import reviewer_design as design     # noqa: E402
import reviewer_pipeline as rp       # noqa: E402
import reviewer_stats as rstats      # noqa: E402
import run_stage3 as s3              # noqa: E402
import stage3_audio as audio         # noqa: E402
import upgrade_design as udesign     # noqa: E402
import upgrade_pipeline as upipe     # noqa: E402


CALIBRATION = design.CALIBRATION_REPORT.parent
VALIDATION = design.RESULTS / "validation"
PART_REPORTS = {part: VALIDATION / f"{part}_report.json" for part in ["signal", "confirmation", "sweep"]}
VALIDATION_REPORT = VALIDATION / "validation_report.json"
RAW = design.RESULTS / "raw"
ANALYSIS = design.RESULTS / "analysis"
KEY_HZ = [1000.0, 2000.0, 2500.0, 3000.0, 3500.0, 3812.5, 4000.0, 4062.5, 4125.0]


def at(curve, hz: float) -> float:
    return float(np.asarray(curve)[int(np.argmin(np.abs(rp.FREQS - hz)))])


def fir_response(taps: np.ndarray) -> dict:
    return {f"{hz:g}": float(lowpass.frequency_response_db(taps, np.array([hz]), rp.SAMPLE_RATE)[0]) for hz in KEY_HZ}


# ==================================================
# RS1 calibrate
# ==================================================

def environment_e1(pipeline: s3.Pipeline, selection: list[dict]) -> dict:
    """E1: the frozen Stage 3 pipeline, six conditions, against the sealed Stage 3 calibration outputs."""
    started = time.time()
    records = []
    for start in range(0, len(selection), upipe.CHUNK_UTTERANCES):
        records += pipeline.process_chunk("calibration", selection[start:start + upipe.CHUNK_UTTERANCES],
                                          audio.new_accumulators())
    new_audio = pd.DataFrame([r for rec in records for r in rec["audio"]])
    new_asr = pd.DataFrame([r for rec in records for r in rec["asr"]])
    frozen_audio = pd.read_csv(udesign.S3_CALIBRATION / "audio_manifest.csv")
    frozen_asr = pd.read_csv(udesign.S3_CALIBRATION / "asr_outputs.csv", keep_default_na=False)
    audio_cmp = frozen_audio.merge(new_audio, on=["utterance", "condition"], suffixes=("_frozen", "_new"))
    codec = audio_cmp["ogg_sha256_frozen"].notna()
    asr_cmp = frozen_asr.merge(new_asr, on=["utterance", "condition", "model"], suffixes=("_frozen", "_new"))
    e1 = {
        "rows": {"audio_frozen": len(frozen_audio), "audio_new": len(new_audio), "audio_matched": len(audio_cmp),
                 "asr_frozen": len(frozen_asr), "asr_new": len(new_asr), "asr_matched": len(asr_cmp)},
        "waveform_mismatches": int((audio_cmp["waveform_sha256_frozen"] != audio_cmp["waveform_sha256_new"]).sum()),
        "ogg_mismatches": int((audio_cmp.loc[codec, "ogg_sha256_frozen"] != audio_cmp.loc[codec, "ogg_sha256_new"]).sum()),
        "hypothesis_mismatches": int((asr_cmp["hypothesis_frozen"] != asr_cmp["hypothesis_new"]).sum()),
        "seconds_per_utterance": (time.time() - started) / len(selection),
    }
    e1["pass"] = bool(len(audio_cmp) == len(frozen_audio) == len(new_audio)
                      and len(asr_cmp) == len(frozen_asr) == len(new_asr)
                      and e1["waveform_mismatches"] == 0 and e1["ogg_mismatches"] == 0
                      and e1["hypothesis_mismatches"] == 0)
    new_audio.to_csv(CALIBRATION / "e1_audio_manifest.csv", index=False)
    new_asr.to_csv(CALIBRATION / "e1_asr_outputs.csv", index=False)
    return e1


def calibrate_r1(waveforms: list, lp_taps: np.ndarray, curves: pd.DataFrame) -> tuple[dict, np.ndarray | None]:
    tol = design.REPRODUCTION_TOLERANCE_DB
    silk_ff = rp.measure(waveforms, rp.ffmpeg_codec(rp.SILK_SETTINGS))
    lp = rp.measure(waveforms, rp.zero_phase(lp_taps), align=False)
    c1 = {
        "silk40_ffmpeg_max_abs_difference_db": rp.max_abs_difference(
            silk_ff["h1_rel_db"], curves["reference_h1_rel_db_40k"], design.REPRODUCTION_UP_TO_HZ),
        "lp_max_abs_difference_db": rp.max_abs_difference(
            lp["h1_rel_db"], curves["lp_measured_h1_rel_db"], design.REPRODUCTION_UP_TO_HZ),
        "tolerance_db": tol, "up_to_hz": design.REPRODUCTION_UP_TO_HZ,
    }
    c1["pass"] = bool(c1["silk40_ffmpeg_max_abs_difference_db"] <= tol and c1["lp_max_abs_difference_db"] <= tol)
    record = {"C1_pass": c1["pass"], "C1": c1, "REUSE_pass": None, "control": None, "lp_libopus_taps_sha256": None}
    if not c1["pass"]:
        return record, None
    silk_lib = rp.measure(waveforms, rp.libopus_codec(rp.SILK_SETTINGS))
    reuse = rp.reuse_gate(lp, silk_lib, silk_ff)
    replica, _ = rp.fit_stage2b_filter(silk_ff["h1_rel_db"], waveforms)       # procedure check, descriptive
    record.update({
        "REUSE_pass": reuse["pass"], "REUSE": reuse,
        "silk40_ffmpeg": rp.transfer_summary(silk_ff), "silk40_libopus": rp.transfer_summary(silk_lib),
        "lp": rp.transfer_summary(lp),
        "h1_rel_db_at": {f"{hz:g}": {"silk40_ffmpeg": at(silk_ff["h1_rel_db"], hz),
                                     "silk40_libopus": at(silk_lib["h1_rel_db"], hz), "lp": at(lp["h1_rel_db"], hz)}
                         for hz in KEY_HZ},
        "max_abs_difference_libopus_vs_ffmpeg_db_up_to_4150": rp.max_abs_difference(
            silk_lib["h1_rel_db"], silk_ff["h1_rel_db"], design.REPRODUCTION_UP_TO_HZ),
        "procedure_reproduction": {
            "note": "descriptive: fit_stage2b_filter on the regenerated FFmpeg SILK40 curve must give the frozen LP",
            "taps_sha256": lowpass.taps_sha256(replica), "equals_frozen_lp": lowpass.taps_sha256(replica) == audio.FROZEN_LP_SHA256,
            "max_abs_tap_difference": float(np.max(np.abs(replica - lp_taps)))},
    })
    pd.DataFrame({"frequency_hz": rp.FREQS, "silk40_ffmpeg_h1_rel_db": silk_ff["h1_rel_db"],
                  "silk40_libopus_h1_rel_db": silk_lib["h1_rel_db"], "lp_h1_rel_db": lp["h1_rel_db"],
                  "silk40_ffmpeg_coherence": silk_ff["coherence"], "silk40_libopus_coherence": silk_lib["coherence"],
                  "silk40_ffmpeg_mirror_coherence": silk_ff["mirror_coherence"],
                  "silk40_libopus_mirror_coherence": silk_lib["mirror_coherence"],
                  "silk40_ffmpeg_power_ratio_db": silk_ff["power_ratio_db"],
                  "silk40_libopus_power_ratio_db": silk_lib["power_ratio_db"]}
                 ).to_csv(CALIBRATION / "r1_curves.csv", index=False)
    if reuse["pass"]:
        record["control"] = "LP"
        return record, None
    taps, fit = rp.fit_stage2b_filter(silk_lib["h1_rel_db"], waveforms)
    digest = rp.save_filter(design.LP_LIBOPUS_FILTER, taps, fit, "LP_LIBOPUS: the Stage 2B linear-chain control "
                            "fitted to the libopus-decoded SILK40 response", silk_lib["h1_rel_db"])
    record.update({"control": design.LP_LIBOPUS, "lp_libopus_taps_sha256": digest,
                   "lp_libopus": {"edge_hz": fit["edge_hz"], "iterations": fit["iterations"],
                                  "fir_response_db": fir_response(taps)}})
    return record, taps


def calibrate_r2(waveforms: list, lp_taps: np.ndarray) -> tuple[dict, np.ndarray | None]:
    frozen = pd.read_csv(design.STAGE2B_CURVES)
    frozen = frozen[(frozen["subset"] == "dev-clean") & (frozen["cell"] == "opus_8k_nb")].sort_values("frequency_hz")
    opus = rp.measure(waveforms, rp.ffmpeg_codec(rp.OPUS_SETTINGS))
    difference = rp.max_abs_difference(opus["h1_rel_db"], frozen["h1_rel_db"].to_numpy(), design.REPRODUCTION_UP_TO_HZ)
    c1 = {"opus_max_abs_difference_db": difference, "tolerance_db": design.REPRODUCTION_TOLERANCE_DB,
          "up_to_hz": design.REPRODUCTION_UP_TO_HZ, "pass": bool(difference <= design.REPRODUCTION_TOLERANCE_DB)}
    record = {"C1_pass": c1["pass"], "C1": c1, "surr8_taps_sha256": None}
    if not c1["pass"]:
        return record, None
    taps, fit = rp.fit_stage2b_filter(opus["h1_rel_db"], waveforms)
    digest = rp.save_filter(design.SURR8_FILTER, taps, fit, "SURR8: the 8-kbit/s effective coherent-linear surrogate "
                            "(an alternative attribution under a more inclusive same-frequency linear-loss definition)",
                            opus["h1_rel_db"])
    diagnosis = s3.read_sealed(design.R2_DIAGNOSIS, "diagnosis_sha256")
    expected_edge = diagnosis["edges_hz_by_deviation_db"]["dev-clean"]["opus_8k_nb"]["0.5"]
    lp_response, surr_response = fir_response(lp_taps), fir_response(taps)
    record.update({
        "surr8_taps_sha256": digest, "edge_hz": fit["edge_hz"], "diagnosed_edge_hz": expected_edge,
        "edge_reproduces": fit["edge_hz"] == expected_edge, "iterations": fit["iterations"],
        "properties": {"num_taps": int(len(taps)), "symmetric_odd": bool(len(taps) % 2 == 1 and np.array_equal(taps, taps[::-1])),
                       "dc_gain": float(np.sum(taps)), "fir_response_db": surr_response,
                       "surr8_minus_lp_fir_db": {k: surr_response[k] - lp_response[k] for k in surr_response},
                       "measured_h1_rel_db": {f"{hz:g}": at(fit["measured_h1_rel_db"], hz) for hz in KEY_HZ},
                       "target_db": {f"{hz:g}": at(fit["target_db"], hz) for hz in KEY_HZ}},
        "opus8": rp.transfer_summary(opus),
    })
    return record, taps


def environment_e2(rec, selection: list[dict], lp_taps, lp_libopus_taps, surr8_taps) -> dict:
    """E2: new conditions on the Stage 3 calibration set; pipeline sanity only, no WER compared."""
    conditions = [design.OPUS_REFDEC, design.SILK_REFDEC]
    conditions += [design.LP_LIBOPUS] if lp_libopus_taps is not None else []
    conditions += [design.SURR8] if surr8_taps is not None else []
    conditions += [design.NB8, design.WB8]

    def generate(waveform):
        out = rp.confirmation_conditions(waveform, lp_taps, True, lp_libopus_taps, surr8_taps)
        out.update(rp.sweep_conditions(waveform))
        return out

    started = time.time()
    records = []
    for start in range(0, len(selection), upipe.CHUNK_UTTERANCES):
        records += upipe.process_chunk("calibration", selection[start:start + upipe.CHUNK_UTTERANCES],
                                       generate, conditions, rec)
    seconds = time.time() - started
    frame = pd.DataFrame([r for record in records for r in record["audio"]])
    asr_rows = pd.DataFrame([r for record in records for r in record["asr"]])

    identity, differences = [], []
    for entry in selection[:2]:
        waveform = upipe.load_reference(entry)
        generated = generate(waveform)
        for name, settings in [("OPUS", rp.OPUS_SETTINGS), ("SILK", rp.SILK_SETTINGS), (design.NB8, design.NB8_SETTINGS)]:
            frozen, _ = audio.codec_round_trip(waveform, settings)
            identity.append(audio.tensor_sha256(generated[name][0]) == audio.tensor_sha256(frozen))
    for entry in selection:
        waveform = upipe.load_reference(entry)
        generated = rp.confirmation_conditions(waveform, lp_taps, True, None, None)
        for name in ["OPUS", "SILK"]:
            differences.append({"utterance": entry["utterance"], "condition": name,
                                **rp.decoder_difference(generated[name][0], generated[f"{name}_REFDEC"][0])})
    repeat = upipe.process_chunk("calibration", selection[:2], generate, conditions, rec)
    first = {(r["utterance"], r["condition"]): r["waveform_sha256"] for record in records[:2] for r in record["audio"]}
    first_asr = {(r["utterance"], r["condition"], r["model"]): r["hypothesis"] for record in records[:2] for r in record["asr"]}
    refdec = frame[frame["condition"].isin([design.OPUS_REFDEC, design.SILK_REFDEC])]
    coded = frame[frame["condition"].isin([design.NB8, design.WB8])]
    e2 = {
        "conditions": conditions,
        "refdec_packets_identical": bool(refdec["packets_identical"].astype(str).eq("True").all()),
        "refdec_samples_per_packet": sorted(refdec["samples_per_packet"].astype(str).unique().tolist()),
        "refdec_output_gain_zero": bool((refdec["output_gain"] == 0).all()),
        "refdec_pre_skip_is_3x_lookahead": bool(refdec["pre_skip_is_3x_lookahead"].astype(str).eq("True").all()),
        "refdec_48k_length_equals_ffmpeg": bool((refdec["length_48k"] == refdec["ffmpeg_length_48k"]).all()),
        "refdec_decoder": sorted(refdec["decoder"].unique().tolist()),
        "ffmpeg_path_identity_with_codec_round_trip": {"checked": len(identity), "identical": int(sum(identity))},
        "packets_expected_config": {n: float(coded.loc[coded["condition"] == n, "share_expected_config"].min())
                                    for n in [design.NB8, design.WB8]},
        "readback_mismatches": sorted(set(";".join(coded["readback_mismatches"].fillna("").astype(str)).split(";")) - {""}),
        "median_payload_kbps": {n: float(coded.loc[coded["condition"] == n, "payload_kbps"].median())
                                for n in [design.NB8, design.WB8]},
        "lengths_equal_ref": bool(frame["length_equals_ref"].all()),
        "nonfinite_samples": int(frame["nonfinite_count"].sum()),
        "empty_hypotheses": int((asr_rows["hypothesis"].astype(str).str.strip() == "").sum()),
        "determinism": {
            "waveforms_identical": all(first[(r["utterance"], r["condition"])] == r["waveform_sha256"]
                                       for record in repeat for r in record["audio"]),
            "hypotheses_identical": all(first_asr[(r["utterance"], r["condition"], r["model"])] == r["hypothesis"]
                                        for record in repeat for r in record["asr"])},
        "decoder_difference_calibration_set": pd.DataFrame(differences).groupby("condition").agg(
            bit_identical=("bit_identical", "sum"), snr_db_median=("snr_db", "median"), snr_db_min=("snr_db", "min"),
            max_abs_difference=("max_abs_difference", "max"), lag_min=("lag_samples", "min"),
            lag_max=("lag_samples", "max")).reset_index().to_dict(orient="records"),
        "seconds_per_utterance": seconds / len(selection),
    }
    e2["pass"] = bool(e2["refdec_packets_identical"] and e2["refdec_samples_per_packet"] == [str(design.SAMPLES_PER_PACKET_48K)]
                      and e2["refdec_output_gain_zero"] and e2["refdec_pre_skip_is_3x_lookahead"]
                      and e2["refdec_48k_length_equals_ffmpeg"]
                      and e2["ffmpeg_path_identity_with_codec_round_trip"]["identical"] == len(identity)
                      and all(v == 1.0 for v in e2["packets_expected_config"].values())
                      and not e2["readback_mismatches"] and e2["lengths_equal_ref"] and e2["nonfinite_samples"] == 0
                      and e2["determinism"]["waveforms_identical"] and e2["determinism"]["hypotheses_identical"])
    frame.to_csv(CALIBRATION / "e2_audio_manifest.csv", index=False)
    asr_rows.to_csv(CALIBRATION / "e2_asr_outputs.csv", index=False)
    pd.DataFrame(differences).to_csv(CALIBRATION / "e2_decoder_difference.csv", index=False)
    return e2


def calibrate() -> int:
    spec = design.require_frozen_plan()
    if design.CALIBRATION_REPORT.exists():
        raise RuntimeError(f"{design.CALIBRATION_REPORT} exists")
    for path in [design.LP_LIBOPUS_FILTER, design.SURR8_FILTER]:
        if path.exists():
            raise RuntimeError(f"{path} exists")
    CALIBRATION.mkdir(parents=True, exist_ok=True)
    report = {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
              "purpose": "RS1: environment reproduction (E1), R1 and R2 calibration on the Stage 2B calibration set, "
                         "and pipeline sanity of every new condition (E2); no condition comparison is computed"}
    pipeline = s3.Pipeline()
    selection = s3.load_selection("calibration")["utterances"]
    report["E1"] = environment_e1(pipeline, selection)
    if report["E1"]["pass"]:
        waveforms = rp.stage2b_calibration_waveforms()
        lp_taps = audio.load_filters()["LP"]
        curves = pd.read_csv(design.STAGE2B_CALIBRATION_CURVES)
        report["R1"], lp_libopus_taps = calibrate_r1(waveforms, lp_taps, curves)
        report["R2"], surr8_taps = calibrate_r2(waveforms, lp_taps)
        report["E2"] = environment_e2(upipe.Recognisers.from_stage3_pipeline(pipeline), selection, lp_taps,
                                      lp_libopus_taps, surr8_taps)
    else:
        report.update({"R1": {"C1_pass": False, "note": "not run: E1 failed"},
                       "R2": {"C1_pass": False, "note": "not run: E1 failed"}, "E2": {"pass": False}})
    report["files"] = {p.name: s3.file_sha256(p) for p in sorted(CALIBRATION.glob("*")) if p.suffix in {".csv", ".json"}
                       and p != design.CALIBRATION_REPORT}
    digest = s3.write_sealed(design.CALIBRATION_REPORT, report, "report_sha256")
    print(json.dumps({"E1": report["E1"]["pass"], "E2": report["E2"]["pass"],
                      "R1": {k: report["R1"].get(k) for k in ["C1_pass", "REUSE_pass", "control"]},
                      "R2": {k: report["R2"].get(k) for k in ["C1_pass", "edge_hz", "surr8_taps_sha256"]},
                      "report_sha256": digest}, indent=1))
    return 0 if report["E1"]["pass"] and report["E2"]["pass"] else 1


# ==================================================
# RS3 validate (no ASR)
# ==================================================

def frozen_controls(freeze: dict) -> dict:
    """The filters recorded in the code freeze (taps hashes checked)."""
    out = {"LP": audio.load_filters()["LP"], "control": freeze["r1_control"], "lp_libopus": None, "surr8": None,
           "surr8_edge_hz": None}
    if freeze["r1_control"] == design.LP_LIBOPUS:
        out["lp_libopus"], _ = rp.load_frozen_filter(design.LP_LIBOPUS_FILTER, freeze["lp_libopus_taps_sha256"])
    if freeze["r2_status"] == "calibrated":
        out["surr8"], record = rp.load_frozen_filter(design.SURR8_FILTER, freeze["surr8_taps_sha256"])
        out["surr8_edge_hz"] = record["metadata"]["edge_hz"]
    out["lp_dec"] = out["lp_libopus"] if out["control"] == design.LP_LIBOPUS else out["LP"]
    return out


def validate_signal(spec: dict, freeze: dict) -> dict:
    selection = s3.read_sealed(design.SV_SELECTION, "selection_sha256")
    if selection["selection_sha256"] != spec["selections"]["signal_validation"]["sha256"]:
        raise RuntimeError("signal-validation selection differs from the frozen plan")
    controls = frozen_controls(freeze)
    r1_on = freeze["r1_status"] == "calibrated"
    rows, transfer = rp.signal_validation(selection, controls["lp_dec"], controls["surr8"])
    rows.to_csv(VALIDATION / "signal_rows.csv", index=False)
    pd.concat([pd.DataFrame({"cell": cell, "frequency_hz": rp.FREQS, "h1_rel_db": tr["h1_rel_db"],
                             "coherence": tr["coherence"], "mirror_coherence": tr["mirror_coherence"],
                             "power_ratio_db": tr["power_ratio_db"]}) for cell, tr in transfer.items()]
              ).to_csv(VALIDATION / "signal_transfer_curves.csv", index=False)
    report = {"part": "signal", "n_utterances": len(selection["utterances"]),
              "transfer": {cell: rp.transfer_summary(tr) for cell, tr in transfer.items()}}
    if r1_on:
        report["R1-V"] = {"control": controls["control"], **rp.r1_validation(rows, transfer, controls["lp_dec"])}
    else:
        report["R1-V"] = {"pass": False, "note": "R1 STOPPED at RS1"}
    if controls["surr8"] is not None:
        surr_rows = rows[rows["cell"] == "surr8"]
        gates = rp.surr8_gates(transfer["surr8"], transfer["opus_8k_nb_ffmpeg"], surr_rows["alignment_lag_samples"],
                               controls["surr8"], controls["surr8_edge_hz"])
        lp_response, surr_response = fir_response(controls["LP"]), fir_response(controls["surr8"])
        report["R2-V"] = {**gates, "descriptive": {
            "surr8_lsd_0_3k_vs_ref_db": {"median": float(surr_rows["lsd_0_3k_db"].median()),
                                         "p95": float(surr_rows["lsd_0_3k_db"].quantile(0.95))},
            "surr8_retained_bandwidth_hz_median": float(surr_rows["retained_bandwidth_hz"].median()),
            "surr8_total_hf_power_db": transfer["surr8"]["total_hf_power_db"],
            "surr8_minus_lp_fir_db": {f"{hz:g}": surr_response[f"{hz:g}"] - lp_response[f"{hz:g}"]
                                      for hz in design.R2_RESPONSE_REPORT_HZ},
            "surr8_packets_irrelevant": "no codec"}}
    else:
        report["R2-V"] = {"pass": False, "note": "R2 STOPPED at RS1"}
    report["reference_decoder_checks"] = {
        "packets_identical": bool(rows.loc[rows["cell"].isin(["silk_nb_linear_ref", "opus_8k_nb"]), "packets_identical"]
                                  .astype(str).eq("True").all()),
        "samples_per_packet": sorted(rows.loc[rows["cell"].isin(["silk_nb_linear_ref", "opus_8k_nb"]), "samples_per_packet"]
                                     .astype(str).unique().tolist())}
    report["rows_sha256"] = s3.file_sha256(VALIDATION / "signal_rows.csv")
    report["curves_sha256"] = s3.file_sha256(VALIDATION / "signal_transfer_curves.csv")
    return report


def validate_confirmation(spec: dict, freeze: dict) -> dict:
    selection = s3.load_selection("confirmation")
    if selection["selection_sha256"] != spec["selections"]["confirmation"]["sha256"]:
        raise RuntimeError("confirmation selection differs from the frozen plan")
    controls = frozen_controls(freeze)
    manifest = pd.read_csv(udesign.S3_CONFIRMATION / "audio_manifest.csv")
    frozen = {(r.utterance, r.condition): (r.waveform_sha256, r.ogg_sha256) for r in manifest.itertuples()}
    rows, differences = [], []
    for entry in tqdm(selection["utterances"], desc="validate confirmation", unit="utt"):
        waveform = upipe.load_reference(entry)
        generated = rp.confirmation_conditions(waveform, controls["LP"], True, controls["lp_libopus"], controls["surr8"])
        ids = {"utterance": entry["utterance"], "subset": entry["subset"], "speaker_id": entry["speaker_id"]}
        for name, (processed, info) in generated.items():
            if name in ("REF", "LP"):
                continue
            rows.append({**ids, **upipe.audio_row(name, processed, waveform, info)})
        for name in ["OPUS", "SILK"]:
            differences.append({**ids, "condition": name,
                                **rp.decoder_difference(generated[name][0], generated[f"{name}_REFDEC"][0])})
    frame = pd.DataFrame(rows)
    frame.to_csv(VALIDATION / "confirmation_rows.csv", index=False)
    pd.DataFrame(differences).to_csv(VALIDATION / "confirmation_decoder_difference.csv", index=False)
    codec = frame[frame["condition"].isin(["OPUS", "SILK"])]
    refdec = frame[frame["condition"].isin([design.OPUS_REFDEC, design.SILK_REFDEC])]
    g1 = all(frozen[(r.utterance, r.condition)] == (r.waveform_sha256, r.ogg_sha256) for r in codec.itertuples())
    g2 = bool(refdec["decoder"].eq(opus_direct.libopus_version()).all()
              and refdec["decoder_path"].eq(opus_direct.libopus_path()).all()
              and (refdec["output_gain"] == 0).all()
              and refdec["pre_skip_is_3x_lookahead"].astype(str).eq("True").all()
              and refdec["packets_identical"].astype(str).eq("True").all()
              and refdec["samples_per_packet"].astype(str).eq(str(design.SAMPLES_PER_PACKET_48K)).all())
    g3 = bool((refdec["length_48k"] == refdec["ffmpeg_length_48k"]).all() and refdec["length_equals_ref"].all()
              and (refdec["nonfinite_count"] == 0).all())
    diff = pd.DataFrame(differences)
    return {"part": "confirmation", "n_utterances": len(selection["utterances"]),
            "R1-G1": bool(g1 and len(codec) == 2 * len(selection["utterances"])), "R1-G2": g2, "R1-G3": g3,
            "identity_all_bit_identical": bool(diff["bit_identical"].all()),
            "decoder_difference": diff.groupby("condition").agg(
                bit_identical=("bit_identical", "sum"), snr_db_median=("snr_db", "median"), snr_db_min=("snr_db", "min"),
                max_abs_difference=("max_abs_difference", "max"), lag_min=("lag_samples", "min"),
                lag_max=("lag_samples", "max")).reset_index().to_dict(orient="records"),
            "rows_sha256": s3.file_sha256(VALIDATION / "confirmation_rows.csv")}


def validate_sweep(spec: dict, freeze: dict) -> dict:
    selection = s3.read_sealed(udesign.SELECTION, "selection_sha256")
    if selection["selection_sha256"] != spec["selections"]["sweep"]["sha256"]:
        raise RuntimeError("sweep selection differs from the frozen plan")
    b_rows = pd.read_csv(design.B_VALIDATION_ROWS)
    b8 = {r.utterance: (r.waveform_sha256, r.ogg_sha256) for r in b_rows[b_rows["condition"] == "SILK8"].itertuples()}
    rows = []
    accumulator = rp.s2b.TransferAccumulator()
    for entry in tqdm(selection["utterances"], desc="validate sweep", unit="utt"):
        waveform = upipe.load_reference(entry)
        generated = rp.sweep_conditions(waveform)
        ids = {"utterance": entry["utterance"], "subset": entry["subset"], "speaker_id": entry["speaker_id"]}
        for name, (processed, info) in generated.items():
            rows.append({**ids, **upipe.audio_row(name, processed, waveform, info)})
        _, _, aligned = rp.s2b.signal_metrics(waveform, generated[design.WB8][0])
        accumulator.add(*aligned)
    frame = pd.DataFrame(rows)
    frame.to_csv(VALIDATION / "sweep_rows.csv", index=False)
    nb, wb = frame[frame["condition"] == design.NB8], frame[frame["condition"] == design.WB8]
    wb_median, nb_median = float(wb["payload_kbps"].median()), float(nb["payload_kbps"].median())
    hf = accumulator.results()["total_hf_power_db"]
    gates = {
        "R3-G0": bool(all(b8[r.utterance] == (r.waveform_sha256, r.ogg_sha256) for r in nb.itertuples())
                      and len(nb) == len(b8)),
        "R3-G1": bool(design.settings_table()[design.WB8] == spec["R3"]["encoder_settings_record"][design.WB8]
                      and wb["readback_mismatches"].fillna("").astype(str).eq("").all()),
        "R3-G2": bool((wb["share_expected_config"] == 1).all() and not wb["any_stereo"].astype(str).eq("True").any()
                      and wb["frame_count_codes"].astype(str).eq("0").all() and wb["libopus_bandwidths"].eq("WB").all()),
        "R3-G3": bool(abs(wb_median / 8.0 - 1) <= design.BITRATE_TOLERANCE
                      and abs(wb_median / nb_median - 1) <= design.RATE_MATCH_TOLERANCE),
        "R3-G4": bool((wb["decoded_sample_rate"] == design.REFERENCE_DECODER_RATE).all() and wb["length_equals_ref"].all()
                      and (wb["nonfinite_count"] == 0).all()),
        "R3-G5": bool(hf >= design.HF_REALISED_MIN_DB),
    }
    return {"part": "sweep", "n_utterances": len(selection["utterances"]), "gates": gates,
            "median_payload_kbps": {design.NB8: nb_median, design.WB8: wb_median}, "wb8_total_hf_power_db": hf,
            "rows_sha256": s3.file_sha256(VALIDATION / "sweep_rows.csv")}


def combine_validation(spec: dict, freeze: dict) -> None:
    parts = {part: s3.read_sealed(path, "report_sha256") for part, path in PART_REPORTS.items()}
    signal, confirmation, sweep = parts["signal"], parts["confirmation"], parts["sweep"]
    r1_pass = bool(freeze["r1_status"] == "calibrated" and signal["R1-V"]["pass"] and confirmation["R1-G1"]
                   and confirmation["R1-G2"] and confirmation["R1-G3"])
    record = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
        "parts": {part: report["report_sha256"] for part, report in parts.items()},
        "R1": {"pass": r1_pass, "identity": bool(r1_pass and confirmation["identity_all_bit_identical"]),
               "control": freeze["r1_control"]},
        "R2": {"pass": bool(freeze["r2_status"] == "calibrated" and signal["R2-V"]["pass"])},
        "R3": {"pass": bool(all(sweep["gates"].values())), "gates": sweep["gates"]},
    }
    s3.write_sealed(VALIDATION_REPORT, record, "report_sha256")
    print(json.dumps({k: record[k] for k in ["R1", "R2", "R3"]}, indent=1))


def validate(part: str) -> int:
    spec, freeze = design.require_code_freeze()
    VALIDATION.mkdir(parents=True, exist_ok=True)
    path = PART_REPORTS[part]
    if path.exists():
        raise RuntimeError(f"{path} exists")
    body = {"signal": validate_signal, "confirmation": validate_confirmation, "sweep": validate_sweep}[part](spec, freeze)
    digest = s3.write_sealed(path, {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
                                    "code_freeze_sha256": freeze["freeze_sha256"], **body}, "report_sha256")
    print(f"validation part {part}: report_sha256 {digest}")
    if all(p.exists() for p in PART_REPORTS.values()) and not VALIDATION_REPORT.exists():
        combine_validation(spec, freeze)
    return 0


# ==================================================
# RS4 run (ASR, once) and RS5 analyse
# ==================================================

def run() -> None:
    spec, freeze = design.require_code_freeze()
    validation = s3.read_sealed(VALIDATION_REPORT, "report_sha256")
    for part, digest in validation["parts"].items():
        if s3.read_sealed(PART_REPORTS[part], "report_sha256")["report_sha256"] != digest:
            raise RuntimeError(f"validation part {part} differs from the combined report")
    controls = frozen_controls(freeze)
    rec = None
    r1 = validation["R1"]["pass"] and not validation["R1"]["identity"]
    r2 = validation["R2"]["pass"]
    if r1 or r2:
        rec = upipe.Recognisers()
        manifest = pd.read_csv(udesign.S3_CONFIRMATION / "audio_manifest.csv")
        rows = pd.read_csv(VALIDATION / "confirmation_rows.csv")
        expected = {(r.utterance, r.condition): (r.waveform_sha256, r.ogg_sha256 if isinstance(r.ogg_sha256, str) else None)
                    for r in pd.concat([manifest, rows]).itertuples()}
        conditions = ["REF", "LP", "OPUS", "SILK"]
        conditions += [design.OPUS_REFDEC, design.SILK_REFDEC] if r1 else []
        conditions += [design.LP_LIBOPUS] if r1 and controls["control"] == design.LP_LIBOPUS else []
        conditions += [design.SURR8] if r2 else []

        def check(entry, audio_rows):
            for row in audio_rows:
                waveform_sha, ogg_sha = expected[(entry["utterance"], row["condition"])]
                if row["waveform_sha256"] != waveform_sha or (ogg_sha and row.get("ogg_sha256") != ogg_sha):
                    raise RuntimeError(f"{entry['utterance']} {row['condition']} differs from the sealed rows")

        selection = s3.load_selection("confirmation")
        vs_lp = [c for c in ["OPUS", "SILK", design.OPUS_REFDEC, design.SILK_REFDEC] if c in conditions]
        pairs = [("REF", c) for c in conditions if c != "REF"] + [("LP", c) for c in vs_lp]
        digest = upipe.run_set(
            "confirmation", selection["utterances"], RAW / "confirmation",
            lambda w: rp.confirmation_conditions(w, controls["LP"], r1,
                                                 controls["lp_libopus"] if r1 else None, controls["surr8"] if r2 else None),
            conditions, rec, freeze["code_sha256"], selection["selection_sha256"],
            signal_fn=lambda ref, gen: rp.signal_rows(ref, gen, [c for c in conditions if c != "REF"], vs_lp),
            transfer_pairs=pairs, check=check)
        print(f"RS4a decoded once; outputs_sha256 {digest}")
    if validation["R3"]["pass"]:
        rec = rec or upipe.Recognisers()
        rows = pd.read_csv(VALIDATION / "sweep_rows.csv")
        expected = {(r.utterance, r.condition): (r.waveform_sha256, r.ogg_sha256) for r in rows.itertuples()}

        def check_sweep(entry, audio_rows):
            for row in audio_rows:
                if (row["waveform_sha256"], row["ogg_sha256"]) != expected[(entry["utterance"], row["condition"])]:
                    raise RuntimeError(f"{entry['utterance']} {row['condition']} differs from the sealed rows")

        selection = s3.read_sealed(udesign.SELECTION, "selection_sha256")
        conditions = [design.NB8, design.WB8]
        digest = upipe.run_set(
            "sweep", selection["utterances"], RAW / "sweep", rp.sweep_conditions, conditions, rec,
            freeze["code_sha256"], selection["selection_sha256"],
            signal_fn=lambda ref, gen: rp.signal_rows(ref, gen, conditions, []),
            transfer_pairs=[("REF", c) for c in conditions], check=check_sweep)
        print(f"RS4b decoded once; outputs_sha256 {digest}")


def verified_outputs(directory: Path) -> dict:
    manifest = s3.read_sealed(directory / "outputs_sha256.json", "outputs_sha256")
    for name, digest in manifest["files"].items():
        if s3.file_sha256(directory / name) != digest:
            raise RuntimeError(f"{directory / name} differs from its sealed manifest")
    return manifest


def analyse() -> None:
    spec, freeze = design.require_code_freeze()
    validation = s3.read_sealed(VALIDATION_REPORT, "report_sha256")
    combined_path = ANALYSIS / "reviewer_decision.json"
    if combined_path.exists():
        raise RuntimeError(f"{combined_path} exists")
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    anchors = spec["anchors"]
    decisions = {}
    r1 = validation["R1"]["pass"] and not validation["R1"]["identity"]
    if (r1 or validation["R2"]["pass"]):
        manifest = verified_outputs(RAW / "confirmation")
        metrics = pd.read_csv(RAW / "confirmation" / "utterance_metrics.csv", keep_default_na=False)
        conditions = [c for c in metrics["condition"].unique()]
        lp_dec = validation["R1"]["control"]
        table = rstats.analyse(metrics, conditions, rstats.confirmation_quantities, lp_dec=lp_dec, r1=r1,
                               r2=validation["R2"]["pass"])
        table.to_csv(ANALYSIS / "confirmation_bootstrap.csv", index=False)
        if r1:
            decisions["R1"] = {**rstats.r1_decision(table, anchors, lp_dec), "outputs_sha256": manifest["outputs_sha256"]}
        if validation["R2"]["pass"]:
            decisions["R2"] = {**rstats.r2_decision(table, anchors), "outputs_sha256": manifest["outputs_sha256"]}
    if validation["R1"]["pass"] and validation["R1"]["identity"]:
        decisions["R1"] = {"analysis": "R1", "cells": {m: dict(design.SUPPORT_BY_IDENTITY) for m in design.MODELS},
                           "outcome": "SUPPORT"}
    if not validation["R1"]["pass"]:
        decisions["R1"] = {"analysis": "R1", "outcome": design.STOPPED}
    if not validation["R2"]["pass"]:
        decisions["R2"] = {"analysis": "R2", "outcome": design.STOPPED}
    if validation["R3"]["pass"]:
        manifest = verified_outputs(RAW / "sweep")
        metrics = pd.read_csv(RAW / "sweep" / "utterance_metrics.csv", keep_default_na=False)
        table = rstats.analyse(metrics, [design.NB8, design.WB8], rstats.sweep_quantities)
        table.to_csv(ANALYSIS / "sweep_bootstrap.csv", index=False)
        decisions["R3"] = {**rstats.r3_decision(table), "outputs_sha256": manifest["outputs_sha256"]}
    else:
        decisions["R3"] = {"analysis": "R3", "outcome": design.STOPPED}
    hashes = {}
    for name, decision in decisions.items():
        hashes[name] = s3.write_sealed(ANALYSIS / f"{name.lower()}_decision.json",
                                       {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
                                        "code_freeze_sha256": freeze["freeze_sha256"],
                                        "validation_report_sha256": validation["report_sha256"], **decision},
                                       "decision_sha256")
    bootstraps = {p.name: s3.file_sha256(p) for p in sorted(ANALYSIS.glob("*_bootstrap.csv"))}
    s3.write_sealed(combined_path, {"created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
                                    "decisions": hashes, "bootstrap_sha256": bootstraps,
                                    "outcomes": {k: v.get("outcome") if k != "R3" or v.get("outcome") == design.STOPPED
                                                 else {m: c["outcome"] for m, c in v["cells"].items()}
                                                 for k, v in decisions.items()}}, "decision_sha256")
    print(json.dumps({k: v.get("outcome") for k, v in decisions.items()}, indent=1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["calibrate", "validate", "run", "analyse"])
    parser.add_argument("part", nargs="?", choices=list(PART_REPORTS))
    args = parser.parse_args()
    os.chdir(design.REPO_ROOT)
    if args.command == "validate" and not args.part:
        parser.error("validate needs a part: signal, confirmation or sweep")
    if args.command == "validate":
        return validate(args.part)
    result = {"calibrate": calibrate, "run": run, "analyse": analyse}[args.command]()
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
