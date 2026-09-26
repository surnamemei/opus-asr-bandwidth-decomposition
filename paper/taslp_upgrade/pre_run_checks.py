"""
TASLP upgrade, U1: supplementary pre-run checks on the Stage 3 calibration set.

Run after `run_bitrate_sweep.py calibrate` (gates E1, E2) and before
`upgrade_design.py freeze-code`. Only the 20 dev-clean utterances of the sealed
Stage 3 calibration selection are read, encoded, decoded or recognised; no sweep or
confirmation utterance is touched and no WER is computed. The checks add to E1/E2;
they change no gate, estimand or rule of the frozen plan.

    A  level matching. LP, OPUS and OPUS8_LEVEL_MATCHED come from the evaluation path
       (upgrade_pipeline.level_conditions) and are checked against the sealed Stage 3
       calibration manifest with the gate logic of run_level_sensitivity (A1-A3 on
       calibration data). The transform must be exactly float32(g * float64(OPUS)):
       no clipping, no length or alignment change, no re-encoding (every codec call
       is recorded). wav2vec2 scale invariance is checked numerically (front end with
       and without GroupNorm's epsilon, emissions, hypotheses); the Whisper log-mel
       offset G/40 is recorded (descriptive).
    B  bitrate sweep. Every rate goes through upgrade_pipeline.encode_decode and
       through the frozen stage3_audio.codec_round_trip: packets 100 % TOC config 1
       (SILK-only, NB, 20 ms), encoder read-back equal to the request and identical
       across rates except the bitrate, one decoder and resampler path for every rate
       (every call recorded). Payload and Ogg bitrates, packet modes, lag, RMS change,
       LSD 0-3 kHz and coherence are recorded (descriptive).
    P  environment and provenance: pip freeze equal to the Stage 3 lock, libopus,
       FFmpeg, GPU, checkpoint, torch flags; every sealed record and output manifest
       re-verified; the Stage 3 identifiers equal those the plan was frozen against;
       every hash in provenance/PROVENANCE.md section 3 recomputed.

The freeze gates are every check except those that a sealed amendment
(upgrade_amendments.py) reclassified as descriptive calibration findings; those are still
computed and reported. Run 1 wrote calibration/checks/ (verdict FAIL on
A_wav2vec2_scale_invariance alone, reclassified by amendment 01) and is kept unchanged; a
run after amendment NN writes calibration/checks_after_amendment_NN/.

Commands:

    check     the checks above; a sealed checks_report.json (verdict PASS if every freeze
              gate passes, else FAIL)
    manifest  after freeze-code: seal results_paper/taslp_upgrade/freeze_manifest.json,
              the SHA-256 of every code, specification, amendment, selection, statistics,
              test, provenance and calibration file, bound to the code freeze; requires
              every freeze gate of the latest run to pass
"""

import argparse
import collections
import contextlib
import copy
import hashlib
import importlib.metadata
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402
import torch                # noqa: E402
import torchaudio           # noqa: E402
from tqdm import tqdm       # noqa: E402

import common               # noqa: E402
import lowpass              # noqa: E402
import opus_direct          # noqa: E402
import run_bitrate_sweep as sweep      # noqa: E402
import run_level_sensitivity as level  # noqa: E402
import run_lowpass_validation as stage2b  # noqa: E402
import run_reproduce        # noqa: E402
import run_stage3 as s3     # noqa: E402
import stage3_asr as asr    # noqa: E402
import stage3_audio as audio  # noqa: E402
import upgrade_amendments as amendments  # noqa: E402
import upgrade_design as design  # noqa: E402
import upgrade_pipeline as pipe  # noqa: E402
import upgrade_stats as ustats   # noqa: E402


THIS_FILE = design.UPGRADE / "pre_run_checks.py"
SUPPLEMENTARY_CODE = [THIS_FILE, amendments.THIS_FILE]
CALIBRATION = design.CALIBRATION_REPORT.parent
CHECKS = CALIBRATION / "checks"                   # run 1: verdict FAIL, kept unchanged
REPORT = "checks_report.json"
FREEZE_MANIFEST = design.RESULTS / "freeze_manifest.json"
PROVENANCE_MD = Path("provenance") / "PROVENANCE.md"
LOCK = design.S3 / "requirements-lock.txt"

LM = ustats.LEVEL_MATCHED
CALIBRATION_SUBSETS = ["dev-clean"]
SEALED_ROOTS = ["paper", "provenance", "results_paper"]

# Audio-manifest values of a regenerated condition that must equal the sealed Stage 3 row
AUDIO_METRICS = ["num_samples", "input_rms_dbfs", "output_rms_dbfs", "rms_change_db", "peak", "clip_count",
                 "nonfinite_count", "lag_vs_ref_samples", "waveform_sha256"]
CODEC_METRICS = ["num_packets", "ogg_bytes", "ogg_sha256", "measured_bitrate_kbps"]

# Every sealed record of the repository outside results_paper/taslp_upgrade (path -> self-hash key)
SEALED = {
    "paper/taslp_upgrade/selection_sweep.json": "selection_sha256",
    "paper/taslp_upgrade/upgrade_spec.json": "spec_sha256",
    "provenance/prior_study_context.json": "record_sha256",
    "provenance/used_test_utterances.json": "record_sha256",
    "results_paper/lowpass_confirmation/revised_spec.json": "spec_sha256",
    "results_paper/lowpass_confirmation/selection.json": "selection_sha256",
    "results_paper/stage3_asr/calibration/outputs_sha256.json": "outputs_sha256",
    "results_paper/stage3_asr/confirmation_freeze.json": "freeze_sha256",
    "results_paper/stage3_asr/pilot/pilot_decision.json": "decision_sha256",
    "results_paper/stage3_asr/raw/confirmation/outputs_sha256.json": "outputs_sha256",
    "results_paper/stage3_asr/raw/pilot/outputs_sha256.json": "outputs_sha256",
    "results_paper/stage3_asr/selection_calibration.json": "selection_sha256",
    "results_paper/stage3_asr/selection_confirmation.json": "selection_sha256",
    "results_paper/stage3_asr/selection_pilot.json": "selection_sha256",
    "results_paper/stage3_asr/stage3_decision.json": "decision_sha256",
    "results_paper/stage3_asr/stage3_spec.json": "spec_sha256",
}


# ==================================================
# Helpers
# ==================================================

def same(a, b) -> bool:
    """Exact equality of a recomputed value and a sealed one (numbers as float64; NaN equals NaN)."""
    numbers = (bool, int, float, np.number, np.bool_)
    if isinstance(a, numbers) and isinstance(b, numbers):
        a, b = float(a), float(b)
        return a == b or (math.isnan(a) and math.isnan(b))
    return str(a) == str(b)


def count_string(values) -> str:
    return ";".join(f"{k}:{v}" for k, v in sorted(collections.Counter(values).items()))


def transform_exact(opus: torch.Tensor, matched: torch.Tensor, gain: float) -> bool:
    """matched is bit for bit float32(gain * float64(opus)): one scalar, nothing clipped, shifted or trimmed."""
    expected = torch.from_numpy((gain * opus.detach().cpu().double().numpy()).astype(np.float32))
    return (tuple(matched.shape) == tuple(opus.shape) and matched.dtype == torch.float32
            and audio.tensor_sha256(matched) == audio.tensor_sha256(expected))


def readback_differences(queried: dict[str, dict]) -> list[str]:
    """Encoder controls whose read-back value is not the same in every condition (a missing control counts)."""
    keys = set().union(*queried.values())
    return sorted(k for k in keys if len({repr(q.get(k, "<missing>")) for q in queried.values()}) > 1)


@contextlib.contextmanager
def recorded(module, name: str, log: list, describe):
    """Replace module.name by a wrapper that appends describe(args, kwargs, result) to log; restored on exit."""
    original = getattr(module, name)

    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        log.append(describe(args, kwargs, result))
        return result

    setattr(module, name, wrapper)
    try:
        yield log
    finally:
        setattr(module, name, original)


@contextlib.contextmanager
def codec_calls():
    """Every libopus encode, frozen-path decode and resample call made inside the block."""
    calls = {"encode": [], "decode": [], "resample": []}
    with recorded(opus_direct, "encode", calls["encode"],
                  lambda a, k, r: asdict(a[2] if len(a) > 2 else k["settings"])), \
            recorded(opus_direct, "decode_frozen_path", calls["decode"],
                     lambda a, k, r: {"decoded_rate": int(r[1])}), \
            recorded(torchaudio.functional, "resample", calls["resample"],
                     lambda a, k, r: {"orig_freq": int(a[1]), "new_freq": int(a[2]),
                                      "keyword_arguments": sorted(k)}):
        yield calls


def expected_calls(settings: opus_direct.EncoderSettings) -> dict:
    """One encode with these settings, one frozen-path decode at 48 kHz, one 48 -> 16 kHz default resample."""
    return {"encode": [asdict(settings)], "decode": [{"decoded_rate": pipe.DECODED_SAMPLE_RATE}],
            "resample": [{"orig_freq": pipe.DECODED_SAMPLE_RATE, "new_freq": pipe.SAMPLE_RATE,
                          "keyword_arguments": []}]}


def metric_mismatches(new: dict, frozen: dict, columns: list[str]) -> str:
    return ";".join(c for c in columns if not same(new.get(c), frozen.get(c)))


def code_sha256() -> dict[str, str]:
    """The design-frozen code files and the supplementary U1 code."""
    return {**design.code_hashes(), **{str(p): s3.file_sha256(p) for p in SUPPLEMENTARY_CODE}}


def checks_dirs() -> list[Path]:
    """Output directory of every U1 checks run, oldest first: run 1, then one run after each sealed amendment."""
    return [CHECKS] + [CALIBRATION / f"checks_after_amendment_{r['amendment']}" for r in amendments.load_all()]


def report_intact(directory: Path) -> bool:
    """A sealed U1 checks report (read_sealed raises if it changed) whose CSV files keep their sealed hashes."""
    record = s3.read_sealed(directory / REPORT, "report_sha256")
    return all(s3.file_sha256(directory / name) == digest for name, digest in record["files"].items())


def freeze_gates(checks: dict[str, bool], reclassified: dict[str, dict]) -> dict:
    """
    The freeze gates are every check not reclassified as a descriptive finding by a sealed
    amendment. Descriptive findings are reported with their value and never gate the freeze.
    """
    return {"gates": [k for k in checks if k not in reclassified],
            "failed_gates": [k for k in checks if k not in reclassified and not checks[k]],
            "descriptive": {k: {"value": checks[k], **reclassified[k]} for k in checks if k in reclassified},
            "reclassified_but_missing": sorted(set(reclassified) - set(checks))}


# ==================================================
# Data: the Stage 3 calibration set only
# ==================================================

def calibration_set(spec: dict) -> tuple[list[dict], dict]:
    """The sealed Stage 3 calibration utterances, checked to share nothing with any evaluation set."""
    selection = s3.load_selection("calibration")
    if selection["selection_sha256"] != spec["provenance"]["stage3_calibration_selection_sha256"]:
        raise RuntimeError("calibration selection differs from the frozen plan")
    utterances = selection["utterances"]
    ids = {u["utterance"] for u in utterances}
    sweep_ids = {u["utterance"] for u in s3.read_sealed(design.SELECTION, "selection_sha256")["utterances"]}
    confirmation_ids = {u["utterance"] for u in s3.load_selection("confirmation")["utterances"]}
    used_ids = set(design.used_record()["all_used_test_utterances"])
    isolation = {
        "set": "Stage 3 calibration selection", "selection_sha256": selection["selection_sha256"],
        "n_utterances": len(utterances), "n_speakers": len({u["speaker_id"] for u in utterances}),
        "subsets": sorted({u["subset"] for u in utterances}),
        "overlap_sweep_selection": len(ids & sweep_ids),
        "overlap_confirmation_selection": len(ids & confirmation_ids),
        "overlap_used_test_utterances": len(ids & used_ids),
    }
    if (isolation["subsets"] != CALIBRATION_SUBSETS or isolation["overlap_sweep_selection"]
            or isolation["overlap_confirmation_selection"] or isolation["overlap_used_test_utterances"]):
        raise RuntimeError(f"calibration set is not isolated from the evaluation sets: {isolation}")
    return utterances, isolation


# ==================================================
# A: level matching
# ==================================================

def group_norm_difference(block, conv_x: torch.Tensor, conv_y: torch.Tensor, eps: float) -> float:
    norm = block.layer_norm
    x = torch.nn.functional.group_norm(conv_x, norm.num_groups, norm.weight, norm.bias, eps)
    y = torch.nn.functional.group_norm(conv_y, norm.num_groups, norm.weight, norm.bias, eps)
    return float((y - x).abs().max())


def wav2vec2_invariance(w2v: asr.Wav2Vec2ASR, opus: torch.Tensor, matched: torch.Tensor, gain: float) -> dict:
    """
    Plan section 3.5: the first convolution has no bias and is followed by GroupNorm with
    one channel per group, so a scalar gain is removed up to GroupNorm's epsilon and float
    rounding. Front end in float64 on the CPU, with epsilon 1e-5 and with epsilon 0; full
    model emissions and hypotheses through the Stage 3 path (GPU, float32).
    """
    block = copy.deepcopy(common.model.feature_extractor.conv_layers[0]).to("cpu", torch.float64)
    with torch.inference_mode():
        conv_x = block.conv(opus.to(torch.float64).reshape(1, 1, -1))
        conv_y = block.conv(matched.to(torch.float64).reshape(1, 1, -1))
        row = {
            "w2v_conv_has_bias": block.conv.bias is not None,
            "w2v_groupnorm_groups_equal_channels": block.layer_norm.num_groups == block.layer_norm.num_channels,
            "w2v_conv_linearity_rel_error": float((conv_y - gain * conv_x).abs().max()
                                                  / (gain * conv_x).abs().max()),
            "w2v_conv_min_channel_variance": float(conv_x.var(dim=-1, correction=0).min()),
            "w2v_groupnorm_max_abs_diff": group_norm_difference(block, conv_x, conv_y, block.layer_norm.eps),
            "w2v_groupnorm_max_abs_diff_eps0": group_norm_difference(block, conv_x, conv_y, 0.0),
        }
        del conv_x, conv_y
        emissions_x, _ = common.model(opus.to(common.device))
        emissions_y, _ = common.model(matched.to(common.device))
        row.update({
            "w2v_emissions_max_abs": float(emissions_x.abs().max()),
            "w2v_emissions_max_abs_diff": float((emissions_y - emissions_x).abs().max()),
            "w2v_frames": int(emissions_x.shape[1]),
            "w2v_frames_argmax_changed": int((emissions_y.argmax(-1) != emissions_x.argmax(-1)).sum()),
        })
    row["w2v_hypothesis_opus"] = w2v.transcribe(opus)
    row["w2v_hypothesis_level_matched"] = w2v.transcribe(matched)
    row["w2v_hypotheses_identical"] = row["w2v_hypothesis_opus"] == row["w2v_hypothesis_level_matched"]
    return row


def whisper_offset(extractor, opus: torch.Tensor, matched: torch.Tensor, gain_db: float) -> dict:
    """Plan section 3.5 (descriptive): Whisper log-mel features of the level-matched signal minus OPUS vs G/40."""
    features = extractor([np.asarray(w[0].numpy(), dtype=np.float32) for w in (opus, matched)],
                         sampling_rate=asr.SAMPLE_RATE, return_tensors="pt").input_features.double().numpy()
    delta = features[1] - features[0]
    deviation = np.abs(delta - gain_db / 40.0)
    speech = opus.shape[-1] // extractor.hop_length          # frames inside the utterance; padding after +2
    padding = deviation[:, speech + 2:]
    return {"whisper_expected_offset": gain_db / 40.0, "whisper_median_offset": float(np.median(delta)),
            "whisper_max_abs_deviation_speech": float(deviation[:, :speech].max()),
            "whisper_max_abs_deviation_padding": float(padding.max()) if padding.size else float("nan"),
            "whisper_share_bins_within_1e-4": float(np.mean(deviation <= 1e-4))}


def level_checks(entries, filters, stage3_audio, stage3_asr, w2v, extractor) -> list[dict]:
    frozen = {(r["utterance"], r["condition"]): r for r in stage3_audio.to_dict(orient="records")}
    frozen_hypotheses = {(r["utterance"], r["condition"], r["model"]): r["hypothesis"]
                         for r in stage3_asr.to_dict(orient="records")}
    rows = []
    for entry in tqdm(entries, desc="A: level matching", unit="utt"):
        utterance = entry["utterance"]
        waveform = pipe.load_reference(entry)
        with codec_calls() as calls:
            generated = pipe.level_conditions(waveform, filters)
        audio_rows = [pipe.audio_row(name, generated[name][0], waveform, generated[name][1])
                      for name in ustats.LEVEL_CONDITIONS]
        by = {r["condition"]: r for r in audio_rows}
        lp, opus, matched = (generated[name][0] for name in ustats.LEVEL_CONDITIONS)
        gain = generated[LM][1]["gain"]
        row = level.gate_row(entry, audio_rows, frozen)          # U6's A1-A3 logic, on calibration data
        row.update({
            "gates_pass": level.gates_pass(row),
            "lp_metrics_mismatched": metric_mismatches(by["LP"], frozen[(utterance, "LP")], AUDIO_METRICS),
            "opus_metrics_mismatched": metric_mismatches(by["OPUS"], frozen[(utterance, "OPUS")],
                                                         AUDIO_METRICS + CODEC_METRICS),
            "transform_exact": transform_exact(opus, matched, gain),
            "gain_equals_rms_ratio": gain == pipe.rms(lp.numpy()) / pipe.rms(opus.numpy()),
            "opus_peak": by["OPUS"]["peak"], "level_matched_peak": by[LM]["peak"],
            "peak_scaled_not_limited": by[LM]["peak"] == float(np.float32(gain * by["OPUS"]["peak"])),
            "opus_samples_at_or_above_full_scale": by["OPUS"]["clip_count"],
            "lengths_equal_ref": (tuple(lp.shape) == tuple(opus.shape) == tuple(matched.shape)
                                  == tuple(waveform.shape)),
            "lag_opus": by["OPUS"]["lag_vs_ref_samples"], "lag_level_matched": by[LM]["lag_vs_ref_samples"],
            "lag_opus_to_level_matched": int(common.align_waveforms(opus, matched)[2]),
            "codec_calls": json.dumps(calls, sort_keys=True),
            "codec_calls_expected": calls == expected_calls(pipe.OPUS_SETTINGS),
        })
        row.update(wav2vec2_invariance(w2v, opus, matched, gain))
        row["w2v_opus_hypothesis_equals_stage3"] = (row["w2v_hypothesis_opus"]
                                                    == frozen_hypotheses[(utterance, "OPUS", "wav2vec2")])
        row.update(whisper_offset(extractor, opus, matched, row["gain_db"]))
        rows.append(row)
    return rows


# ==================================================
# B: bitrate sweep
# ==================================================

def sweep_checks(entries, filters, stage3_audio, stage3_signal) -> tuple[list[dict], list[dict]]:
    frozen = {(r["utterance"], r["condition"]): r for r in stage3_audio.to_dict(orient="records")}
    frozen_signal = {(r["utterance"], r["condition"]): r for r in stage3_signal.to_dict(orient="records")}
    counterparts = {"LP": "LP", "SILK8": "OPUS", "SILK40": "SILK"}   # SILK8 vs OPUS: descriptive bridge only
    audio_rows, signal_rows = [], []
    for entry in tqdm(entries, desc="B: bitrate sweep", unit="utt"):
        utterance = entry["utterance"]
        waveform = pipe.load_reference(entry)
        lp = lowpass.apply_zero_phase(waveform, filters["LP"]).to(torch.float32)
        generated, queried, rows = {"LP": (lp, {})}, {}, [{**sweep.ids(entry), **pipe.audio_row("LP", lp, waveform, {})}]
        for name, settings in pipe.SWEEP_SETTINGS.items():
            with codec_calls() as calls:
                decoded, summary, result = pipe.encode_decode(waveform, settings)
            with codec_calls() as frozen_calls:
                frozen_decoded, frozen_info = audio.codec_round_trip(waveform, settings)
            generated[name], queried[name] = (decoded, summary), result.queried
            infos = [opus_direct.packet_info(p) for p in result.packets]
            rows.append({
                **sweep.ids(entry), **pipe.audio_row(name, decoded, waveform, summary),
                "nominal_kbps": settings.bitrate_bps / 1000,
                "packet_modes": count_string(i["configuration"] for i in infos),
                "packet_frame_ms": count_string(i["frame_ms"] for i in infos),
                "lookahead_samples": result.lookahead_samples,
                "readback_mismatches": ";".join(pipe.readback_mismatches(result)),
                "codec_calls": json.dumps(calls, sort_keys=True),
                "codec_calls_expected": calls == expected_calls(settings),
                "frozen_path_calls_identical": calls == frozen_calls,
                "frozen_path_ogg_identical": summary["ogg_sha256"] == frozen_info["ogg_sha256"],
                "frozen_path_waveform_identical": audio.tensor_sha256(decoded) == audio.tensor_sha256(frozen_decoded),
            })
        differs = ";".join(readback_differences(queried))
        for row in rows:
            counterpart = counterparts.get(row["condition"])
            f = frozen.get((utterance, counterpart), {})
            row["stage3_counterpart"] = counterpart or ""
            row["equals_stage3_counterpart"] = bool(counterpart) and row["waveform_sha256"] == f["waveform_sha256"] \
                and (row["condition"] == "LP" or row["ogg_sha256"] == f["ogg_sha256"])
            if row["condition"] != "LP":
                row["readback_differs_across_rates"] = differs
        audio_rows += rows

        metrics, _ = pipe.sweep_signal_rows(waveform, generated)
        for row in metrics:
            counterpart = {"LP": "LP", "SILK40": "SILK"}.get(row["condition"])   # same waveform in Stage 3
            mismatched = ""
            if counterpart:
                f = frozen_signal[(utterance, counterpart)]
                mismatched = ";".join(k for k in row if k != "condition" and (k not in f or not same(row[k], f[k])))
            signal_rows.append({**sweep.ids(entry), **row, "stage3_counterpart": counterpart or "",
                                "stage3_mismatched_metrics": mismatched})
    return audio_rows, signal_rows


def sweep_summary(frame: pd.DataFrame, signal: pd.DataFrame) -> dict:
    """Per-rate descriptive record: bitrates, packet modes, lag, RMS change, descriptors, stability flags."""
    per_condition, flagged = [], {}
    coded = frame[frame["condition"] != "LP"]
    for name in ustats.SWEEP_CONDITIONS:
        part, sig = frame[frame["condition"] == name], signal[signal["condition"] == name]
        row = {"condition": name, "utterances": int(len(part)),
               "lag_vs_ref_samples": count_string(part["lag_vs_ref_samples"]),
               "rms_change_db_median": float(part["rms_change_db"].median()),
               "samples_at_or_above_full_scale": int(part["clip_count"].sum()),
               **{f"{column}_median": float(sig[column].median()) for column in sweep.DESCRIPTORS if column in sig}}
        if name != "LP":
            nominal = float(part["nominal_kbps"].iloc[0])
            modes = sorted({m.split(":")[0] for s in part["packet_modes"] for m in s.split(";")})
            frame_ms = sorted({m.split(":")[0] for s in part["packet_frame_ms"] for m in s.split(";")})
            row.update({
                "nominal_kbps": nominal, "packets": int(part["num_packets"].sum()), "packet_modes": modes,
                "packet_frame_ms": frame_ms,
                "packet_configs": sorted({int(c.split(":")[0]) for s in part["packet_configs"] for c in s.split(";")}),
                "min_share_config_1": float(part["share_expected_config"].min()),
                "payload_kbps_median": float(part["payload_kbps"].median()),
                "payload_kbps_min": float(part["payload_kbps"].min()),
                "payload_kbps_max": float(part["payload_kbps"].max()),
                "payload_median_vs_nominal": float(part["payload_kbps"].median() / nominal - 1.0),
                "container_kbps_median": float(part["container_kbps"].median()),
                "readback_mismatch_encodes": int((part["readback_mismatches"] != "").sum()),
                "lookahead_samples": sorted(set(part["lookahead_samples"].astype(int))),
            })
            reasons = [reason for reason, bad in [
                ("not 100 % TOC config 1", row["min_share_config_1"] < 1),
                ("packet mode other than SILK-NB", modes != ["SILK-NB"]),
                ("frame duration other than 20 ms", frame_ms != ["20.0"]),
                ("encoder read-back mismatch", row["readback_mismatch_encodes"] > 0),
                ("median payload outside +/-15 % of nominal (V2 forecast)",
                 abs(row["payload_median_vs_nominal"]) > design.BITRATE_TOLERANCE),
            ] if bad]
            if reasons:
                flagged[name] = reasons
        per_condition.append(row)
    medians = [float(coded.loc[coded["condition"] == n, "payload_kbps"].median()) for n in ustats.SWEEP_CODED]
    ratios = [b / a for a, b in zip(medians, medians[1:])]
    for (a, b), ratio in zip(zip(ustats.SWEEP_CODED, ustats.SWEEP_CODED[1:]), ratios):
        if ratio < design.MIN_ADJACENT_RATIO:
            flagged.setdefault(b, []).append(f"adjacent payload ratio {a}->{b} below {design.MIN_ADJACENT_RATIO}")
    silk8 = frame[frame["condition"] == "SILK8"]
    return {
        "per_condition": per_condition,
        "v2_forecast_on_calibration": {
            "note": "descriptive: V2 is a gate of the validation step on the sweep selection, not of U1",
            "median_payload_kbps": medians, "adjacent_ratios": ratios,
            "would_pass": bool(all(abs(m / r - 1) <= design.BITRATE_TOLERANCE
                                   for m, r in zip(medians, ustats.SWEEP_RATES_KBPS))
                               and all(r >= design.MIN_ADJACENT_RATIO for r in ratios))},
        "rates_flagged": flagged,
        "bridge_share_silk8_ogg_equals_stage3_opus": float(silk8["equals_stage3_counterpart"].mean()),
    }


# ==================================================
# P: environment and provenance
# ==================================================

def environment(spec: dict) -> tuple[dict, dict]:
    stage3 = s3.read_sealed(s3.SPEC_JSON, "spec_sha256")["environment"]
    freeze_text = run_reproduce.command_output([sys.executable, "-m", "pip", "freeze"])
    checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / asr.WAV2VEC2_CHECKPOINT
    record = {
        "python": sys.version, "python_executable": sys.executable,
        "packages": {name: importlib.metadata.version(name) for name in [
            "torch", "torchaudio", "torchcodec", "transformers", "huggingface_hub", "numpy", "pandas",
            "jiwer", "soundfile"]},
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none",
        "driver": run_reproduce.command_output(["nvidia-smi", "--query-gpu=driver_version",
                                                "--format=csv,noheader"]),
        "torch_flags": {
            "cuda.matmul.allow_tf32": torch.backends.cuda.matmul.allow_tf32,
            "cudnn.allow_tf32": torch.backends.cudnn.allow_tf32,
            "cudnn.benchmark": torch.backends.cudnn.benchmark,
            "cudnn.deterministic": torch.backends.cudnn.deterministic,
            "float32_matmul_precision": torch.get_float32_matmul_precision(),
        },
        "libopus": opus_direct.libopus_version(), "libopus_path": opus_direct.libopus_path(),
        "ffmpeg": run_reproduce.command_output(["ffmpeg", "-hide_banner", "-version"]).splitlines()[0],
        "wav2vec2_checkpoint_sha256": s3.file_sha256(checkpoint),
        "pip_freeze_sha256": hashlib.sha256((freeze_text + "\n").encode()).hexdigest(),
    }
    matches = {
        "pip_freeze_equals_stage3_lock": freeze_text + "\n" == LOCK.read_text(),
        "lock_sha256_equals_plan": s3.file_sha256(LOCK) == spec["provenance"]["stage3_requirements_lock_sha256"],
        "libopus_equals_plan": record["libopus"] == spec["provenance"]["libopus"],
        "ffmpeg_equals_stage3": record["ffmpeg"] == stage3["ffmpeg"]["version"],
        "gpu_equals_stage3": record["gpu"] == stage3["cuda"]["gpu"],
        "wav2vec2_checkpoint_equals_stage3": record["wav2vec2_checkpoint_sha256"] == stage3["wav2vec2_checkpoint"]["sha256"],
        "torch_flags_equal_stage3": record["torch_flags"] == stage3["torch_flags"],
    }
    return record, matches


def discover_sealed() -> list[str]:
    """Every JSON record outside results_paper/taslp_upgrade that carries its own body hash."""
    found = []
    for root in SEALED_ROOTS:
        for path in sorted(Path(root).rglob("*.json")):
            if design.RESULTS in path.parents:
                continue
            record = json.loads(path.read_text())
            if isinstance(record, dict) and any(
                    k.endswith("_sha256") and v == s3.body_sha256(record, k) for k, v in record.items()):
                found.append(str(path))
    return sorted(found)


def provenance_table_hashes() -> set[str]:
    text = PROVENANCE_MD.read_text()
    return set(re.findall(r"\b[0-9a-f]{64}\b", text[text.index("## 3."):text.index("## 4.")]))


def provenance_checks(spec: dict, filters: dict, earlier: list[Path]) -> tuple[dict, dict]:
    sealed_paths = {**SEALED, **amendments.sealed_paths()}
    sealed = {path: s3.read_sealed(Path(path), key)[key] for path, key in sealed_paths.items()}   # raises if changed
    manifests = {}
    for path in [p for p in SEALED if p.endswith("outputs_sha256.json")]:
        record = s3.read_sealed(Path(path), "outputs_sha256")
        manifests[path] = all(s3.file_sha256(Path(path).parent / f) == h for f, h in record["files"].items())
    calibration = s3.read_sealed(design.CALIBRATION_REPORT, "report_sha256")
    integrity = design.stage3_integrity()
    recomputed = set(sealed.values()) | {s3.file_sha256(design.S3_BOOTSTRAP), s3.file_sha256(LOCK),
                                         lowpass.taps_sha256(filters["LP"]), stage2b.tolerances_sha256()}
    table = provenance_table_hashes()
    record = {
        "sealed_records": sealed, "output_manifests_verified": manifests,
        "stage3_identifiers": integrity,
        "provenance_md_section3_hashes": len(table),
        "provenance_md_hashes_not_recomputed": sorted(table - recomputed),
        "earlier_u1_reports": {str(d / REPORT): s3.read_sealed(d / REPORT, "report_sha256")["report_sha256"]
                               for d in earlier},
        "head": s3.git("rev-parse", "HEAD"), "working_tree_status": s3.git("status", "--porcelain").splitlines(),
    }
    checks = {
        "P_every_sealed_record_verified": discover_sealed() == sorted(sealed_paths),
        "P_earlier_u1_reports_preserved": all(report_intact(d) for d in earlier),
        "P_output_manifests_verified": all(manifests.values()),
        "P_calibration_report_files_verified": all(
            s3.file_sha256(design.CALIBRATION_REPORT.parent / f) == h for f, h in calibration["files"].items()),
        "P_stage3_identifiers_equal_plan": all(spec["provenance"][k] == v for k, v in integrity.items()),
        "P_provenance_md_hashes_recomputed": not record["provenance_md_hashes_not_recomputed"],
        "P_design_code_unchanged": design.code_hashes() == spec["code_sha256_at_design_freeze"],
        "P_plan_markdown_rendered_from_spec": design.PLAN_MD.read_text() == design.render(spec),
        "P_lp_taps_equal_plan": lowpass.taps_sha256(filters["LP"]) == spec["provenance"]["frozen_lp_taps_sha256"],
        "P_no_evaluation_outputs": not any((design.RESULTS / sub).exists() for sub in ["sweep", "level"]),
    }
    return record, checks


# ==================================================
# check
# ==================================================

def check() -> int:
    spec = design.require_frozen_plan()
    *earlier, out = checks_dirs()           # earlier runs are never overwritten
    if (out / REPORT).exists():
        raise RuntimeError(f"{out / REPORT} exists")
    if design.CODE_FREEZE.exists():
        raise RuntimeError("the code freeze exists; the U1 checks precede it")
    earlier = [d for d in earlier if (d / REPORT).exists()]
    reclassified = amendments.reclassified_checks()
    calibration = s3.read_sealed(design.CALIBRATION_REPORT, "report_sha256")   # run_bitrate_sweep.py calibrate
    entries, isolation = calibration_set(spec)
    filters = audio.load_filters()          # raises unless the LP taps hash is the frozen one
    stage3_audio = pd.read_csv(design.S3_CALIBRATION / "audio_manifest.csv", float_precision="round_trip")
    stage3_signal = pd.read_csv(design.S3_CALIBRATION / "signal_metrics.csv", float_precision="round_trip")
    stage3_asr = pd.read_csv(design.S3_CALIBRATION / "asr_outputs.csv", keep_default_na=False)
    env, env_checks = environment(spec)
    provenance, provenance_checks_ = provenance_checks(spec, filters, earlier)

    from transformers import WhisperProcessor
    w2v = asr.Wav2Vec2ASR()
    extractor = WhisperProcessor.from_pretrained(asr.WHISPER_REPO, revision=asr.WHISPER_REVISION).feature_extractor
    started = time.time()
    lf = pd.DataFrame(level_checks(entries, filters, stage3_audio, stage3_asr, w2v, extractor))
    level_seconds = time.time() - started
    started = time.time()
    audio_rows, signal_rows = sweep_checks(entries, filters, stage3_audio, stage3_signal)
    sweep_seconds = time.time() - started
    sf, sig = pd.DataFrame(audio_rows), pd.DataFrame(signal_rows)
    coded = sf[sf["condition"] != "LP"]

    out.mkdir(parents=True, exist_ok=True)
    lf.to_csv(out / "level_rows.csv", index=False)
    sf.to_csv(out / "sweep_audio_rows.csv", index=False)
    sig.to_csv(out / "sweep_signal_rows.csv", index=False)

    requested = {name: asdict(s) for name, s in pipe.SWEEP_SETTINGS.items()}
    checks = {
        "calibration_E1_pass": bool(calibration["E1"]["pass"]),
        "calibration_E2_pass": bool(calibration["E2"]["pass"]),
        **{f"env_{k}": bool(v) for k, v in env_checks.items()},
        **{k: bool(v) for k, v in provenance_checks_.items()},
        # A
        "A_opus_settings_equal_plan": asdict(pipe.OPUS_SETTINGS) == spec["A"]["encoder_settings_opus"],
        "A1_calibration": bool(lf[["lp_waveform_identical", "opus_waveform_identical", "opus_ogg_identical"]]
                               .all().all()),
        "A2_calibration": bool((lf["level_error_db"].abs() <= design.LEVEL_TOLERANCE_DB).all()
                               and lf["length_equals_ref"].all() and (lf["nonfinite"] == 0).all()),
        "A3_calibration": bool((lf["gain_reproduction_error_db"].abs()
                                <= design.GAIN_REPRODUCTION_TOLERANCE_DB).all()),
        "A_metrics_equal_stage3": bool((lf["lp_metrics_mismatched"] == "").all()
                                       and (lf["opus_metrics_mismatched"] == "").all()),
        "A_transform_exact": bool(lf["transform_exact"].all() and lf["gain_equals_rms_ratio"].all()),
        "A_no_clipping_or_limiting": bool(lf["transform_exact"].all() and lf["peak_scaled_not_limited"].all()),
        "A_no_length_change": bool(lf["lengths_equal_ref"].all()),
        "A_no_alignment_change": bool((lf["lag_opus"] == lf["lag_level_matched"]).all()
                                      and (lf["lag_opus_to_level_matched"] == 0).all()),
        "A_no_reencoding": bool(lf["codec_calls_expected"].all()),
        "A_opus_wav2vec2_hypothesis_equals_stage3": bool(lf["w2v_opus_hypothesis_equals_stage3"].all()),
        "A_wav2vec2_scale_invariance": bool(lf["w2v_hypotheses_identical"].all()
                                            and not lf["w2v_conv_has_bias"].any()
                                            and lf["w2v_groupnorm_groups_equal_channels"].all()),
        # B
        "B_V1_calibration": bool((coded["share_expected_config"] == 1).all() and not coded["any_stereo"].any()
                                 and (coded["frame_count_codes"].astype(str) == "0").all()
                                 and (coded["libopus_bandwidths"] == "NB").all()
                                 and (coded["packet_frame_ms"].str.fullmatch(r"20\.0:\d+")).all()),
        "B_V3_readback": bool((coded["readback_mismatches"] == "").all()),
        "B_settings_equal_plan": requested == spec["B"]["encoder_settings"],
        "B_settings_differ_only_in_bitrate": bool(
            sorted({k for s in requested.values() for k in s if s[k] != requested["SILK8"][k]}) == ["bitrate_bps"]
            and (coded["readback_differs_across_rates"] == "bitrate").all()),
        "B_V4_calibration": bool((coded["decoded_sample_rate"] == pipe.DECODED_SAMPLE_RATE).all()
                                 and sf["length_equals_ref"].all() and (sf["nonfinite_count"] == 0).all()),
        "B_one_decoder_resampler_path": bool(coded["codec_calls_expected"].all()
                                             and coded["frozen_path_calls_identical"].all()),
        "B_decode_path_equals_stage3_codec_round_trip": bool(coded["frozen_path_ogg_identical"].all()
                                                             and coded["frozen_path_waveform_identical"].all()),
        "B_lp_equals_stage3": bool(sf.loc[sf["condition"] == "LP", "equals_stage3_counterpart"].all()),
        "B_silk40_equals_stage3_silk": bool(sf.loc[sf["condition"] == "SILK40", "equals_stage3_counterpart"].all()),
        "B_signal_metrics_equal_stage3": bool((sig.loc[sig["stage3_counterpart"] != "",
                                                       "stage3_mismatched_metrics"] == "").all()),
    }
    gain = lf["gain_db"].to_numpy()
    status = freeze_gates(checks, reclassified)
    report = {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
        "calibration_report_sha256": calibration["report_sha256"],
        "purpose": "U1 supplementary pre-run checks, run after run_bitrate_sweep.py calibrate (E1, E2) and before "
                   "the code freeze, on the Stage 3 calibration set only; no evaluation utterance is read, encoded, "
                   "decoded or recognised; no WER is computed; not a gate of the sealed plan and no change to it",
        "run": {"number": len(earlier) + 1, "directory": str(out),
                "amendments": {r["amendment"]: r["amendment_sha256"] for r in amendments.load_all()}},
        "isolation": isolation,
        "verdict": "PASS" if not status["failed_gates"] and not status["reclassified_but_missing"] else "FAIL",
        "verdict_rule": "PASS if every freeze gate passes: every check except those reclassified as descriptive "
                        "calibration findings by a sealed amendment",
        "failed": [k for k, v in checks.items() if not v],
        "failed_gates": status["failed_gates"],
        "classification": {"gates": status["gates"], "descriptive": status["descriptive"]},
        "checks": checks,
        "level": {
            "gain_db": {"median": float(np.median(gain)), "min": float(gain.min()), "max": float(gain.max())},
            "max_abs_level_error_db": float(lf["level_error_db"].abs().max()),
            "max_abs_gain_reproduction_error_db": float(lf["gain_reproduction_error_db"].abs().max()),
            "level_matched_samples_at_or_above_full_scale": int(lf["samples_at_or_above_full_scale"].sum()),
            "opus_samples_at_or_above_full_scale": int(lf["opus_samples_at_or_above_full_scale"].sum()),
            "lags_opus": count_string(lf["lag_opus"]), "lags_level_matched": count_string(lf["lag_level_matched"]),
            "wav2vec2": {
                "hypotheses_identical": f"{int(lf['w2v_hypotheses_identical'].sum())}/{len(lf)}",
                "frames_argmax_changed": f"{int(lf['w2v_frames_argmax_changed'].sum())}/{int(lf['w2v_frames'].sum())}",
                "max_conv_linearity_rel_error": float(lf["w2v_conv_linearity_rel_error"].max()),
                "max_groupnorm_abs_diff": float(lf["w2v_groupnorm_max_abs_diff"].max()),
                "max_groupnorm_abs_diff_eps0": float(lf["w2v_groupnorm_max_abs_diff_eps0"].max()),
                "max_emissions_abs_diff": float(lf["w2v_emissions_max_abs_diff"].max()),
                "min_emissions_max_abs": float(lf["w2v_emissions_max_abs"].min()),
            },
            "whisper_descriptive": {
                "expected_offset_median": float(lf["whisper_expected_offset"].median()),
                "observed_offset_median": float(lf["whisper_median_offset"].median()),
                "max_abs_deviation_speech": float(lf["whisper_max_abs_deviation_speech"].max()),
                "max_abs_deviation_padding": float(lf["whisper_max_abs_deviation_padding"].max()),
                "min_share_bins_within_1e-4": float(lf["whisper_share_bins_within_1e-4"].min()),
            },
        },
        "sweep": sweep_summary(sf, sig),
        "environment": env, "provenance": provenance,
        "seconds": {"level": level_seconds, "sweep": sweep_seconds},
        "code_sha256": code_sha256(),
        "files": {p.name: s3.file_sha256(p) for p in sorted(out.glob("*.csv"))},
    }
    digest = s3.write_sealed(out / REPORT, report, "report_sha256")
    print(json.dumps({"verdict": report["verdict"], "failed_gates": report["failed_gates"],
                      "descriptive": {k: v["value"] for k, v in status["descriptive"].items()},
                      "rates_flagged": report["sweep"]["rates_flagged"], "report": str(out / REPORT),
                      "report_sha256": digest}, indent=1))
    return 0 if report["verdict"] == "PASS" else 1


# ==================================================
# manifest (after freeze-code)
# ==================================================

def manifest_groups() -> dict[str, list[Path]]:
    upgrade = design.UPGRADE
    return {
        "upgrade_code": sorted(upgrade.glob("*.py")),
        "stage3_code": list(s3.CODE_FILES),
        "statistics": [upgrade / "upgrade_stats.py", Path("paper") / "stage3_stats.py"],
        "tests": sorted((upgrade / "tests").glob("*.py")),
        "specification": [design.SPEC_JSON, design.PLAN_MD] + sorted(amendments.AMENDMENTS.glob("amendment_*")),
        "selections": [design.SELECTION, design.SELECTION_CSV, design.S3 / "selection_calibration.json",
                       design.S3 / "selection_confirmation.json", design.USED],
        "stage3_references": [s3.SPEC_JSON, design.S3_FREEZE, design.S3_DECISION, design.S3_BOOTSTRAP, LOCK,
                              design.S3_CONFIRMATION / "outputs_sha256.json",
                              design.S3_CONFIRMATION / "audio_manifest.csv",
                              design.S3_CONFIRMATION / "asr_outputs.csv",
                              design.S3_CALIBRATION / "outputs_sha256.json"],
        "calibration": sorted(p for p in design.CALIBRATION_REPORT.parent.rglob("*") if p.is_file()),
        "code_freeze": [design.CODE_FREEZE],
    }


def manifest() -> None:
    spec, freeze = design.require_code_freeze()
    if FREEZE_MANIFEST.exists():
        raise RuntimeError(f"{FREEZE_MANIFEST} is sealed and exists")
    calibration = s3.read_sealed(design.CALIBRATION_REPORT, "report_sha256")
    runs = {d: s3.read_sealed(d / REPORT, "report_sha256") for d in checks_dirs() if (d / REPORT).exists()}
    if checks_dirs()[-1] not in runs:
        raise RuntimeError(f"no U1 checks run after the latest amendment ({checks_dirs()[-1]})")
    checks = runs[checks_dirs()[-1]]        # the latest run gates the freeze; earlier runs stay as provenance
    reclassified = amendments.reclassified_checks()
    status = freeze_gates(checks["checks"], reclassified)
    classified = {k: v["amendment_sha256"] for k, v in checks["classification"]["descriptive"].items()}
    if not (calibration["E1"]["pass"] and calibration["E2"]["pass"]) or checks["verdict"] != "PASS" \
            or status["failed_gates"] or status["reclassified_but_missing"] \
            or classified != {k: v["amendment_sha256"] for k, v in reclassified.items()}:
        raise RuntimeError("a U1 freeze gate did not pass; nothing is sealed")
    if freeze["calibration_report_sha256"] != calibration["report_sha256"]:
        raise RuntimeError("the code freeze refers to a different calibration report")
    if checks["code_sha256"] != code_sha256():
        raise RuntimeError("code changed after the U1 checks")
    for directory, record in [(CALIBRATION, calibration), *runs.items()]:
        for name, digest in record["files"].items():
            if s3.file_sha256(directory / name) != digest:
                raise RuntimeError(f"{directory / name} differs from its sealed report")
    present = {sub: (design.RESULTS / sub).exists() for sub in ["sweep", "level"]}
    if any(present.values()):
        raise RuntimeError(f"evaluation outputs exist: {present}")
    digest = s3.write_sealed(FREEZE_MANIFEST, {
        "created_utc": s3.now(),
        "purpose": "SHA-256 of every code, specification, amendment, selection, statistics, test, provenance and "
                   "calibration file at the code freeze (U2), before any evaluation utterance is encoded, decoded "
                   "or recognised",
        "spec_sha256": spec["spec_sha256"], "code_freeze_sha256": freeze["freeze_sha256"],
        "amendments": {r["amendment"]: r["amendment_sha256"] for r in amendments.load_all()},
        "calibration_report_sha256": calibration["report_sha256"], "checks_report_sha256": checks["report_sha256"],
        "u1_checks_runs": {str(d / REPORT): {"report_sha256": r["report_sha256"], "verdict": r["verdict"],
                                             "failed": r["failed"]} for d, r in runs.items()},
        "freeze_gates": {"passed": len(status["gates"]), "failed": status["failed_gates"],
                         "descriptive_findings": status["descriptive"]},
        "sweep_selection_sha256": spec["B"]["data"]["sha256"],
        "confirmation_selection_sha256": spec["A"]["data"]["sha256"],
        "used_test_utterances_sha256": spec["provenance"]["used_test_utterances_sha256"],
        "evaluation_outputs_present": present,
        "head": s3.git("rev-parse", "HEAD"), "working_tree_status": s3.git("status", "--porcelain").splitlines(),
        "files": {group: {str(p): s3.file_sha256(p) for p in paths} for group, paths in manifest_groups().items()},
    }, "manifest_sha256")
    print(f"freeze manifest sealed; manifest_sha256 {digest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["check", "manifest"])
    args = parser.parse_args()
    os.chdir(design.REPO_ROOT)
    result = {"check": check, "manifest": manifest}[args.command]()
    return int(result or 0)


if __name__ == "__main__":
    sys.exit(main())
