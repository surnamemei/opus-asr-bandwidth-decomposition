"""
R4: reference-decoder total-penalty sensitivity (a post-confirmation sensitivity analysis).

Question: with the exact frozen 8 kbit/s Opus bitstreams of the Stage 3 confirmation set, does
replacing FFmpeg 6.1.1's native Opus decoder with the libopus 1.4 reference decoder materially
change the total ASR penalty (OPUS - REF)? Only one new condition is created, OPUS_LIBOPUS; REF
and OPUS_FFMPEG are the sealed Stage 3 results. R4 is not a successor to R1, not a decoder-matched
decomposition, not a bandwidth control, not an interaction analysis and not a confirmatory run.

This module holds the sealed plan (r4_spec.json, rendered as 00_R4_PLAN.md), the frozen outcome
rule and the guards that every later step calls.

    python paper/decoder_sensitivity/r4_design.py freeze-spec   # RS0: seal the plan
    python paper/decoder_sensitivity/r4_design.py check         # seal, rendering and inputs unchanged
    python paper/decoder_sensitivity/r4_design.py freeze-code   # RS2: after the RS1 dry run

Evaluation steps (run_r4.py validate, run, analyse) refuse to start unless the plan and the code
freeze are committed, which happens only after the author has approved the frozen plan.
"""

import argparse
import json
import math
import os
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "reviewer_sensitivity"), str(HERE.parent / "taslp_upgrade"),
                str(HERE.parent)]

import numpy as np                   # noqa: E402
import pandas as pd                  # noqa: E402
import torch                         # noqa: E402
import torchaudio                    # noqa: E402

import opus_direct                   # noqa: E402
import run_stage3 as s3              # noqa: E402
import stage3_asr as asr             # noqa: E402
import stage3_audio as audio         # noqa: E402
import stage3_stats as s3stats       # noqa: E402
import upgrade_design as upgrade     # noqa: E402

REPO_ROOT = HERE.parents[1]
R4 = Path("paper") / "decoder_sensitivity"
SPEC_JSON = R4 / "r4_spec.json"
PLAN_MD = R4 / "00_R4_PLAN.md"
RESULTS = Path("results_paper") / "decoder_sensitivity"
CALIBRATION = RESULTS / "calibration"
DRY_RUN_PARTS = {"decode": CALIBRATION / "dry_run_decode.json", "asr": CALIBRATION / "dry_run_asr.json"}
CODE_FREEZE = RESULTS / "code_freeze.json"
EVALUATION_OUTPUTS = [RESULTS / name for name in ["validation", "raw", "analysis"]]

REVIEW = Path("paper") / "reviewer_sensitivity"
R1_SPEC = REVIEW / "reviewer_spec.json"
R1_RESULTS = Path("results_paper") / "reviewer_sensitivity"
R1_DECISION = R1_RESULTS / "analysis" / "reviewer_decision.json"
R1_CALIBRATION_REPORT = R1_RESULTS / "calibration" / "calibration_report.json"
R1_E2_AUDIO = R1_RESULTS / "calibration" / "e2_audio_manifest.csv"
R1_CONFIRMATION_REPORT = R1_RESULTS / "validation" / "confirmation_report.json"
R1_CONFIRMATION_ROWS = R1_RESULTS / "validation" / "confirmation_rows.csv"
R1_DIAGNOSIS = R1_RESULTS / "exploratory" / "post_gate_diagnosis.json"

R4_CODE_FILES = [R4 / "r4_design.py", R4 / "run_r4.py", R4 / "tests" / "test_r4.py"]
OTHER_CODE_USED = [REVIEW / "reviewer_pipeline.py", REVIEW / "reviewer_design.py"] + \
    [upgrade.UPGRADE / name for name in ["upgrade_design.py", "upgrade_stats.py", "upgrade_pipeline.py"]]

# ---------------------------------------------------------------- conditions, statistics, rule
MODELS = asr.MODELS
REF, OPUS_FFMPEG, OPUS_LIBOPUS = "REF", "OPUS_FFMPEG", "OPUS_LIBOPUS"
STAGE3_LABEL = {REF: "REF", OPUS_FFMPEG: "OPUS"}      # condition names in the sealed Stage 3 files
CONDITIONS = [REF, OPUS_FFMPEG, OPUS_LIBOPUS]
QUANTITIES = {"T_ffmpeg": (OPUS_FFMPEG, REF), "T_libopus": (OPUS_LIBOPUS, REF), "D": (OPUS_LIBOPUS, OPUS_FFMPEG)}
SCOPES = ["pooled", "test-clean", "test-other"]
N_BOOT = s3stats.N_BOOT          # 10,000, as Stage 3
SEED = s3stats.BOOT_SEED         # 5305: Stage 3's seed on Stage 3's speakers (as Addition A)
OUTCOMES = ("DECODER_LOWER_PENALTY", "NO_CLEAR_DECODER_DIFFERENCE", "DECODER_HIGHER_PENALTY")
STOPPED = "STOPPED"
ANCHOR_TOLERANCE_PP = 1e-9       # G9: T_ffmpeg and the two WERs must reproduce Stage 3 to this

# ---------------------------------------------------------------- the reference decoder (frozen R1 code)
DECODER_RATE = 48000
DECODER_MAX_FRAME = 5760         # 120 ms at 48 kHz, the longest Opus packet
SAMPLES_PER_PACKET_48K = 960     # 20 ms frames (Stage 3 OPUS settings)
OPUS_SETTINGS = audio.CODEC_SETTINGS["OPUS"]
POWER_BAND_HZ = (4000.0, 5000.0)             # descriptive 4-5 kHz power
ONE_SAMPLE_SHIFTS = (-1, 1)                  # descriptive SNR after one-sample alignment


def r4_outcome(d_lo: float, d_hi: float) -> str:
    """
    Frozen descriptive outcome for D = WER(OPUS_LIBOPUS) - WER(OPUS_FFMPEG), one recogniser, pooled,
    from its 95 % speaker-bootstrap interval; no minimum-effect threshold, no combined outcome.

        DECODER_LOWER_PENALTY        D_hi < 0
        DECODER_HIGHER_PENALTY       D_lo > 0
        NO_CLEAR_DECODER_DIFFERENCE  otherwise, including a missing (NaN) bound
    """
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (d_lo, d_hi)):
        return "NO_CLEAR_DECODER_DIFFERENCE"
    if d_hi < 0:
        return "DECODER_LOWER_PENALTY"
    if d_lo > 0:
        return "DECODER_HIGHER_PENALTY"
    return "NO_CLEAR_DECODER_DIFFERENCE"


# ==================================================
# Recorded inputs, environment, anchors and prior exposure
# ==================================================

def sha(path: Path) -> str:
    return s3.file_sha256(path)


def libopus_record() -> dict:
    path = opus_direct.libopus_path()
    return {"version": opus_direct.libopus_version(), "path": path, "sha256": sha(Path(path))}


def environment() -> dict:
    """Recorded at the design freeze and compared at every later step (gate G5)."""
    return {
        "libopus": libopus_record(),
        "python": platform.python_version(),
        "torch": torch.__version__, "torchaudio": torchaudio.__version__, "numpy": np.__version__,
        "pandas": pd.__version__,
        "resampler": "torchaudio.functional.resample(waveform_48k, 48000, 16000) with default parameters "
                     "(resampling_method sinc_interp_hann, lowpass_filter_width 6, rolloff 0.99), float32",
    }


def recorded_inputs() -> dict:
    s3spec = s3.read_sealed(s3.SPEC_JSON, "spec_sha256")
    return {
        "stage3_spec_sha256": s3spec["spec_sha256"],
        "stage3_confirmation_freeze_sha256": s3.read_sealed(upgrade.S3_FREEZE, "freeze_sha256")["freeze_sha256"],
        "stage3_decision_sha256": s3.read_sealed(upgrade.S3_DECISION, "decision_sha256")["decision_sha256"],
        "stage3_bootstrap_csv_sha256": sha(upgrade.S3_BOOTSTRAP),
        "stage3_confirmation_outputs_sha256":
            s3.read_sealed(upgrade.S3_CONFIRMATION / "outputs_sha256.json", "outputs_sha256")["outputs_sha256"],
        "stage3_calibration_outputs_sha256":
            s3.read_sealed(upgrade.S3_CALIBRATION / "outputs_sha256.json", "outputs_sha256")["outputs_sha256"],
        "confirmation_selection_sha256": s3.load_selection("confirmation")["selection_sha256"],
        "calibration_selection_sha256": s3.load_selection("calibration")["selection_sha256"],
        "r1_r3_spec_sha256": s3.read_sealed(R1_SPEC, "spec_sha256")["spec_sha256"],
        "r1_r3_decision_sha256": s3.read_sealed(R1_DECISION, "decision_sha256")["decision_sha256"],
        "r1_calibration_report_sha256": s3.read_sealed(R1_CALIBRATION_REPORT, "report_sha256")["report_sha256"],
        "r1_confirmation_report_sha256": s3.read_sealed(R1_CONFIRMATION_REPORT, "report_sha256")["report_sha256"],
        "r1_post_gate_diagnosis_sha256": s3.read_sealed(R1_DIAGNOSIS, "diagnosis_sha256")["diagnosis_sha256"],
        "stage3_opus_encoder_settings": s3spec["conditions"]["encoder_settings"]["OPUS"],
    }


def stage3_anchors() -> dict:
    """Stage 3's sealed confirmation values that R4 must reproduce (gate G9): per model and scope."""
    boot = pd.read_csv(upgrade.S3_BOOTSTRAP)
    boot = boot[(boot["set"] == "confirmation") & (boot["kind"] == "micro")]
    names = {"wer_REF": "wer_REF", "wer_OPUS_FFMPEG": "wer_OPUS", "T_ffmpeg": "delta_opus_total"}
    out = {}
    for model in MODELS:
        out[model] = {}
        for scope in SCOPES:
            out[model][scope] = {}
            for r4_name, s3_name in names.items():
                row = boot[(boot["model"] == model) & (boot["scope"] == scope) & (boot["quantity"] == s3_name)]
                if len(row) != 1:
                    raise RuntimeError(f"Stage 3 bootstrap: {model}/{scope}/{s3_name}: {len(row)} rows")
                r = row.iloc[0]
                out[model][scope][r4_name] = {"stage3_quantity": s3_name, "estimate": float(r["estimate"]),
                                              "ci": [float(r["ci_lower"]), float(r["ci_upper"])]}
    return out


def prior_exposure() -> dict:
    """What the author has already seen of libopus-decoded audio (all from sealed R1 records)."""
    e2 = s3.read_sealed(R1_CALIBRATION_REPORT, "report_sha256")["E2"]
    conf = s3.read_sealed(R1_CONFIRMATION_REPORT, "report_sha256")
    diag = s3.read_sealed(R1_DIAGNOSIS, "diagnosis_sha256")
    rows = pd.read_csv(R1_CONFIRMATION_ROWS)
    if sha(R1_CONFIRMATION_ROWS) != conf["rows_sha256"]:
        raise RuntimeError("R1 confirmation rows differ from the sealed report")
    refdec = rows[rows["condition"] == "OPUS_REFDEC"]
    opus_e2 = [d for d in e2["decoder_difference_calibration_set"] if d["condition"] == "OPUS"][0]
    opus_conf = [d for d in conf["decoder_difference"] if d["condition"] == "OPUS"][0]
    return {
        "summary": (
            "The Stage 3 OPUS bitstreams have already been decoded with this reference decoder path in two R1 "
            "steps: the 20 calibration utterances in R1's RS1 gate E2 (with a pipeline-sanity ASR pass on those 20 "
            "dev-clean utterances; no condition comparison), and all 2,174 confirmation utterances in R1's RS3 "
            "confirmation part (deviation 3 of the R1-R3 record; encode and decode only, no ASR). No "
            "recognition of libopus-decoded confirmation audio has ever been run, and no evaluation WER under "
            "the reference decoder exists. The signal-level summaries below were seen by the author before "
            "this plan was written; R4's signal diagnostics therefore partly repeat known values and enter no "
            "rule."),
        "r1_e2_calibration": {"report_sha256": s3.read_sealed(R1_CALIBRATION_REPORT, "report_sha256")["report_sha256"],
                              "pass": bool(e2["pass"]), "opus_decoder_difference": opus_e2,
                              "refdec_output_gain_zero": e2["refdec_output_gain_zero"],
                              "refdec_48k_length_equals_ffmpeg": e2["refdec_48k_length_equals_ffmpeg"],
                              "refdec_samples_per_packet": e2["refdec_samples_per_packet"]},
        "r1_confirmation_part": {
            "report_sha256": conf["report_sha256"], "rows_sha256": conf["rows_sha256"],
            "gates_R1_G1_G3": [bool(conf["R1-G1"]), bool(conf["R1-G2"]), bool(conf["R1-G3"])],
            "opus_decoder_difference": opus_conf,
            "opus_refdec_rows": int(len(refdec)),
            "opus_refdec_lag_vs_ref_counts": {str(k): int(v) for k, v in
                                              refdec["lag_vs_ref_samples"].value_counts().sort_index().items()},
            "opus_refdec_rms_change_db_median": float(refdec["rms_change_db"].median()),
            "opus_refdec_length_equals_ref_all": bool(refdec["length_equals_ref"].astype(str).eq("True").all()),
        },
        "r1_post_gate_diagnosis": {"diagnosis_sha256": diag["diagnosis_sha256"],
                                   "label": "exploratory, post hoc (R1); includes the calibration-set decoder "
                                            "difference after alignment"},
        "not_seen": "no WER, CER or hypothesis of OPUS_LIBOPUS on any evaluation utterance",
    }


# ==================================================
# The plan
# ==================================================

def selections() -> dict:
    conf, cal = s3.load_selection("confirmation"), s3.load_selection("calibration")
    subsets = pd.Series([u["subset"] for u in conf["utterances"]]).value_counts().to_dict()
    return {
        "confirmation": {
            "path": str(s3.OUT / "selection_confirmation.json"), "sha256": conf["selection_sha256"],
            "size": f"{len(conf['utterances']):,} utterances, {len({u['speaker_id'] for u in conf['utterances']})} "
                    f"speakers, {subsets}",
            "used_by": "RS3 (decode and gates, no ASR), RS4 (ASR of OPUS_LIBOPUS, once), RS5 (analysis)",
            "note": "the exact Stage 3 confirmation set; no utterance is added, dropped or reselected"},
        "calibration": {
            "path": str(s3.OUT / "selection_calibration.json"), "sha256": cal["selection_sha256"],
            "size": f"{len(cal['utterances'])} utterances, {len({u['speaker_id'] for u in cal['utterances']})} "
                    f"dev-clean speakers",
            "used_by": "RS1 dry run only (before the code freeze); no condition comparison is computed",
            "note": "the Stage 3 calibration set, already used by Stage 3, Additions A/B and R1-R3 for "
                    "environment and pipeline checks"},
        "rule": "No new selection is drawn. R4 reads no utterance outside these two sealed selections.",
    }


def decoder_spec() -> dict:
    lib = libopus_record()
    return {
        "implementation": (
            "reviewer_pipeline.reference_decode and reviewer_pipeline.to_16k, imported unchanged from the "
            "R1-R3 code frozen at dc271f29 (the code that produced R1's sealed OPUS_REFDEC audio). Reusing "
            "frozen code does not make R4 a successor to R1: R4 uses no R1 control, estimand, gate or rule."),
        "library": f"{lib['version']} ({lib['path']}, SHA-256 {lib['sha256']}), the shared object that "
                   f"also encodes (opus_direct.libopus), called through ctypes",
        "decoder": f"opus_decoder_create(Fs={DECODER_RATE}, channels=1); one decoder per stream",
        "packets": "the audio packets of the Ogg stream in stream order, parsed by the frozen common.ogg_audio_packets "
                   "(the parser of the Stage 3 packet checks)",
        "decode_call": f"opus_decode_float(decoder, packet, len, pcm, frame_size={DECODER_MAX_FRAME}, decode_fec=0) "
                       f"per packet; float32 output; every packet present, so packet-loss concealment is never "
                       f"invoked; no CTL is set on the decoder (decoder gain 0 dB, the libopus default)",
        "pre_skip_and_end_trimming": (
            "RFC 7845: the first pre-skip samples (OpusHead, 48 kHz units) are discarded and the output is "
            "truncated to (final granule position - pre-skip) samples; the OpusHead output gain must be 0, so the "
            "RFC 7845 output-gain step is the identity"),
        "resampling": "torchaudio.functional.resample(pcm_48k, 48000, 16000), default parameters, float32: the "
                      "resampling step of the Stage 3 pipeline (stage3_audio.codec_round_trip)",
        "no_correction": "no gain or level matching, no integer or fractional realignment, no filtering, no "
                         "clipping or limiting; samples beyond full scale are passed unchanged, as in Stage 3",
        "output_length_convention": (
            f"at 48 kHz the decoded length equals final granule position - pre-skip = 3 x N_REF samples and equals "
            f"FFmpeg's decoded length for the same file; pre-skip = 3 x the encoder lookahead; every packet yields "
            f"{SAMPLES_PER_PACKET_48K} samples (20 ms); after resampling the length equals N_REF (the REF length), "
            f"as for Stage 3's OPUS"),
        "bitstreams": (
            "Stage 3 kept no Ogg files, only their SHA-256. The Ogg bytes are regenerated from the REF FLAC by the "
            "frozen Stage 3 encoder call (opus_direct.encode with the Stage 3 OPUS settings), exactly as Addition A "
            "(gate A1) and R1 (R1-G1) did, and every file must reproduce the sealed Stage 3 ogg_sha256 byte for "
            "byte (G1); the decoder therefore reads the exact frozen bitstreams"),
        "ffmpeg_path_for_diagnostics_only": (
            "opus_direct.decode_frozen_path (torchaudio.load, FFmpeg 6.1.1 native decoder, 48 kHz) and the same "
            "resampler; the result is expected to equal Stage 3's sealed OPUS waveform_sha256 (reported) and is "
            "used only for the descriptive decoder-difference SNR, never for recognition"),
    }


def build_spec() -> dict:
    anchors = stage3_anchors()
    return {
        "analysis": "R4",
        "title": "Reference-decoder total-penalty sensitivity",
        "created_utc": s3.now(),
        "status": "FROZEN PLAN (RS0): sealed before any R4 audio is decoded. Evaluation steps (RS3-RS5) need the "
                  "committed plan and code freeze, i.e. the author's approval.",
        "label": "POST-CONFIRMATION SENSITIVITY ANALYSIS OF THE TOTAL 8 kbit/s OPUS PENALTY TO THE DECODER - NOT A "
                 "SUCCESSOR TO R1, NOT A DECOMPOSITION, NOT A CONFIRMATORY TEST",
        "question": "Using the exact same frozen 8 kbit/s Opus bitstreams from the Stage 3 confirmation set, does "
                    "replacing FFmpeg 6.1.1's native Opus decoder with the libopus reference decoder materially "
                    "change the total ASR penalty?",
        "is_not": ["a successor to R1 (R1 remains STOPPED)", "a decoder-matched decomposition",
                   "a new bandwidth control", "an interaction analysis", "a new confirmation run"],
        "claim_boundaries": [
            "R4 tests the decoder sensitivity of the total 8 kbit/s Opus ASR penalty (OPUS - REF) only.",
            "It does not estimate a bandwidth component or bandwidth share under libopus.",
            "It does not establish decoder independence of the codec-specific residual (OPUS - LP); LP is not "
            "used.",
            "NO_CLEAR_DECODER_DIFFERENCE is not an equivalence claim: no equivalence margin is specified.",
            "R1 remains STOPPED. No R1b, R2 successor, image-removal condition, extra recogniser, extra codec, "
            "extra decoder setting or version, or VOIP experiment may be started under or alongside R4.",
        ],
        "provenance": {**recorded_inputs(), "git_head_at_freeze": upgrade.git("rev-parse", "HEAD").stdout.strip(),
                       "working_tree_status": upgrade.git("status", "--porcelain").stdout.strip()},
        "environment": environment(),
        "prior_exposure": prior_exposure(),
        "selections": selections(),
        "conditions": {
            REF: "the original LibriSpeech waveform; its recognition outputs are the sealed Stage 3 confirmation "
                 "outputs (not recognised again)",
            OPUS_FFMPEG: "Stage 3's OPUS condition (label OPUS in the sealed files): the frozen bitstreams decoded by "
                         "FFmpeg 6.1.1's native decoder; its recognition outputs are the sealed Stage 3 outputs (not "
                         "recognised again)",
            OPUS_LIBOPUS: "new: the same frozen bitstreams decoded by the libopus 1.4 reference decoder (below), then "
                          "the Stage 3 resampler; the only condition recognised in R4",
        },
        "decoder": decoder_spec(),
        "gates": {
            "G1 (RS3)": "every regenerated OPUS Ogg file's SHA-256 equals the sealed Stage 3 OPUS ogg_sha256 "
                        "(results_paper/stage3_asr/raw/confirmation/audio_manifest.csv), for all 2,174 utterances",
            "G2 (RS3)": "libopus decoding succeeds for all 2,174 utterances: opus_decoder_create returns OPUS_OK, every "
                        "packet decodes without error, and the packets parsed from each file equal the encoder's "
                        "packets (none missing, so concealment is never used)",
            "G3 (RS3)": "decoded lengths follow the pre-specified output-length convention (decoder section) for "
                        "every utterance: output gain 0, pre-skip = 3 x lookahead, "
                        f"{SAMPLES_PER_PACKET_48K} samples per packet, 48 kHz length = final granule - pre-skip = "
                        "3 x REF length = FFmpeg's 48 kHz length, and 16 kHz length = REF length",
            "G4 (RS3)": "no NaN or Inf sample at 48 kHz or 16 kHz, in any utterance",
            "G5 (RS1 and RS3)": "the decoder, library and software versions and every decoder setting are recorded, "
                                "and equal the values sealed in this plan (environment, decoder)",
            "G6 (RS1, calibration set)": "the 20 calibration utterances reproduce deterministically under the new "
                                         "decoder path: (a) two decodes of each regenerated file give identical 16 kHz "
                                         "waveforms (SHA-256), and (b) recognising the first 2 utterances again gives "
                                         "identical hypotheses in both recognisers",
            "G7 (procedural)": "no evaluation WER is inspected before the plan and the code freeze are sealed: RS3-RS5 "
                               "refuse to run unless both are committed; no OPUS_LIBOPUS recognition output exists "
                               "before RS4",
            "G8 (RS1, proposed addition)": "environment reproduction: the frozen Stage 3 pipeline, rerun on the 20 "
                                           "calibration utterances, reproduces the sealed Stage 3 calibration audio "
                                           "(waveform and Ogg SHA-256) and hypotheses exactly (as E1 of Additions A/B "
                                           "and R1-R3). Needed because REF and OPUS_FFMPEG come from the Stage 3 run "
                                           "and OPUS_LIBOPUS from a new one",
            "G9 (RS3, proposed addition)": "analysis-code reproduction: before any OPUS_LIBOPUS recognition, the R4 "
                                           "analysis code, applied to the sealed Stage 3 metrics, reproduces Stage 3's "
                                           f"WER(REF), WER(OPUS) and OPUS - REF (estimate and both bounds, pooled and "
                                           f"per subset, both recognisers) within {ANCHOR_TOLERANCE_PP} pp",
            "on_failure": "R4 is STOPPED before recognition; the failed gate and its values are sealed and reported; "
                          "no other decoder, decoder setting, library version, resampler, trimming or alignment is "
                          "tried under the R4 label",
        },
        "stage3_anchors": anchors,
        "asr_run": [
            "RS4: OPUS_LIBOPUS only, 2,174 utterances, once (resumable progress file as in Stage 3; every "
            "interruption logged; nothing re-decoded selectively).",
            "Recognisers, checkpoints, decoding options and scoring exactly as Stage 3 (stage3_asr, unchanged): "
            "Whisper large-v3 float16 greedy (batch 16) and wav2vec2-base-960h float32 greedy CTC; Whisper's text "
            "normaliser; WER = (S + D + I) / N.",
            "Runner: the frozen upgrade_pipeline.run_set/process_chunk (chunks of 8 utterances). Each utterance's "
            "audio is regenerated and must equal its RS3-validated SHA-256 before it is recognised.",
            "Known cross-run component: Stage 3 queued six conditions per chunk into mixed Whisper batches; R4 has "
            "one condition, so its Whisper batches differ in composition (8 items per chunk). Greedy float16 Whisper "
            "decoding is not exactly invariant to batch composition (Addition A: 3 of 4,348 hypotheses differed, "
            "changing OPUS - LP by 0.002 pp). This run-to-run component is part of D and T_libopus and is not "
            "separated; wav2vec2 decodes each utterance alone and is unaffected.",
        ],
        "estimands": {
            "primary": "per recogniser, pooled over test-clean and test-other: T_ffmpeg = WER(OPUS_FFMPEG) - WER(REF), "
                       "T_libopus = WER(OPUS_LIBOPUS) - WER(REF) and D = WER(OPUS_LIBOPUS) - WER(OPUS_FFMPEG); WER is "
                       "the corpus (micro) WER from total edit counts, in pp",
            "secondary": "the same three quantities per test subset (test-clean, test-other), uncorrected for "
                         "multiplicity",
            "descriptive": "corpus WER of each condition with its interval",
            "note": "D = T_libopus - T_ffmpeg exactly (REF cancels); T_ffmpeg is Stage 3's sealed OPUS - REF",
        },
        "bootstrap": (f"the Stage 3 paired speaker-cluster bootstrap, unchanged: speakers resampled with replacement "
                      f"within each test subset (stratified), all conditions and both recognisers of an utterance kept "
                      f"together, {N_BOOT:,} replicates, seed {SEED} on the Stage 3 speakers (Stage 3's seed, as "
                      f"Addition A), 95 % percentile intervals; every quantity recomputed in each replicate "
                      f"(upgrade_stats.replicate_weights, Replicates, interval_row and analyse, unchanged)"),
        "outcome_rule": {
            "DECODER_LOWER_PENALTY_m": "D_hi < 0: the 95 % interval of D lies entirely below zero",
            "NO_CLEAR_DECODER_DIFFERENCE_m": "the interval includes zero (or a bound is missing)",
            "DECODER_HIGHER_PENALTY_m": "D_lo > 0: the interval lies entirely above zero",
            "scope": "pooled only, per recogniser; per-subset intervals are secondary and enter no rule; no combined "
                     "outcome; no minimum-effect threshold",
            "implementation": "r4_design.r4_outcome(D_lo, D_hi)",
        },
        "descriptive_diagnostics": [
            "None enters a gate or the rule. Computed at RS3 for OPUS_LIBOPUS and, for comparison, for the "
            "regenerated OPUS_FFMPEG audio (expected to equal Stage 3's sealed OPUS waveform; reported):",
            "integer lag relative to REF (distribution; common.align_waveforms, as in the Stage 3 audio manifest)",
            "RMS level change relative to REF (dB; median and 5th-95th percentiles)",
            "SNR between the FFmpeg- and libopus-decoded OPUS at 16 kHz: unaligned, and after one-sample alignment "
            "(the better of the shifts -1 and +1 samples, overlap only; the chosen shift recorded)",
            f"pooled power in {POWER_BAND_HZ[0]:.0f}-{POWER_BAND_HZ[1]:.0f} Hz and total 4-8 kHz power relative to "
            "REF (dB), and pooled mirror coherence over 4.1-4.9 kHz (the frozen Stage 2B/3 TransferAccumulator, "
            "after the frozen alignment)",
            "reproduction check (reported, not a gate): each OPUS_LIBOPUS waveform is expected to equal R1's sealed "
            "OPUS_REFDEC waveform (results_paper/reviewer_sensitivity/validation/confirmation_rows.csv), since the "
            "decoder code, bitstreams and resampler are the same",
        ],
        "manuscript_consequences": {
            "in every outcome": "reported as a post-confirmation sensitivity analysis of the total penalty only, in a "
                                "supplementary section, with one sentence in the main paper; the Implementations "
                                "limitation keeps its existing sentences (R1's frozen STOPPED consequence) and gains "
                                "at most one sentence reporting R4; the abstract, the decomposition and the shares are "
                                "unchanged; no statement of decoder independence of the residual",
            "NO_CLEAR_DECODER_DIFFERENCE_m": "reports T_libopus and D with intervals and states that no difference in "
                                             "the total penalty between the two decoders was established for m; not an "
                                             "equivalence claim",
            "DECODER_LOWER_PENALTY_m / DECODER_HIGHER_PENALTY_m": "states that for m the total 8 kbit/s penalty was "
                                                                  "lower / higher with the libopus reference decoder "
                                                                  "(D given), and that the Stage 3 results are defined "
                                                                  "for FFmpeg's decoder",
            "STOPPED": "reports the failed gate and its values; the manuscript is otherwise unchanged",
        },
        "stopping_rules": [
            "A failed gate (G1-G6, G8, G9) stops R4 before recognition; its values are sealed and reported.",
            "The RS1 dry run touches only the 20 calibration utterances; no confirmation audio is regenerated, "
            "decoded or recognised before the plan and the code freeze are committed (author approval).",
            "RS4 runs once; no estimate is computed before it is complete; no utterance is re-recognised selectively.",
            "RS5 uses only the frozen code and rule; any further analysis is labelled exploratory and cannot change "
            "the outcome.",
        ],
        "run_order": [
            "RS0 (now): seal this plan (r4_design.py freeze-spec).",
            "RS1 (now, calibration set only): dry run - run_r4.py calibrate decode (G1-G5 analogues, G6a, "
            "diagnostics, reproduction of R1's E2 audio) and run_r4.py calibrate asr (G8 environment reproduction, "
            "G6b, OPUS_LIBOPUS pipeline sanity; no condition comparison).",
            "RS2 (after RS1): seal the code freeze (r4_design.py freeze-code).",
            "Author approval, then commit of the plan and the code freeze.",
            "RS3: run_r4.py validate - regenerate and decode the 2,174 confirmation files, gates G1-G5 and G9, "
            "descriptive diagnostics; no ASR.",
            "RS4: run_r4.py run - recognition of OPUS_LIBOPUS, once.",
            "RS5: run_r4.py analyse - estimates, intervals, outcomes; sealed decision record.",
        ],
        "commands": [
            {"step": "RS0", "command": "python paper/decoder_sensitivity/r4_design.py freeze-spec"},
            {"step": "RS1", "command": "python paper/decoder_sensitivity/run_r4.py calibrate decode"},
            {"step": "RS1", "command": "python paper/decoder_sensitivity/run_r4.py calibrate asr"},
            {"step": "RS2", "command": "python paper/decoder_sensitivity/r4_design.py freeze-code"},
            {"step": "RS3", "command": "python paper/decoder_sensitivity/run_r4.py validate"},
            {"step": "RS4", "command": "python paper/decoder_sensitivity/run_r4.py run"},
            {"step": "RS5", "command": "python paper/decoder_sensitivity/run_r4.py analyse"},
        ],
        "outputs": {"calibration": str(CALIBRATION), "code_freeze": str(CODE_FREEZE),
                    "validation": str(RESULTS / "validation"), "raw": str(RESULTS / "raw"),
                    "analysis": str(RESULTS / "analysis")},
        "policies": [
            "A change to this plan before the step it affects needs the author's approval and a sealed amendment; a "
            "change after that step is a deviation and is reported with the results.",
            "Sealed records are never edited; corrections go in new, dated records. R4 writes only under "
            "paper/decoder_sensitivity/ and results_paper/decoder_sensitivity/; the Stage 3, Addition A/B and R1-R3 "
            "records are read, after their seals and output manifests are verified, and never modified.",
            "Every outcome, STOPPED and NO_CLEAR_DECODER_DIFFERENCE included, is reported.",
        ],
        "compute_estimate": "RS1 a few minutes; RS3 about 0.3-0.5 s per utterance on the CPU (about 10-20 min); RS4 "
                            "about 0.3 s per utterance for one condition on the RTX 5090 (about 10-15 min with model "
                            "loading); RS5 about 1-2 min.",
        "code_sha256_at_design_freeze": code_hashes(),
    }


# ==================================================
# Rendering
# ==================================================

def _block(value) -> list[str]:
    if isinstance(value, list):
        return [f"- {v}" for v in value]
    if isinstance(value, dict):
        return [f"- **{k}**: {v}" for k, v in value.items()]
    return [str(value)]


def render(spec: dict) -> str:
    labels = asr.MODEL_LABELS
    P, X = spec["provenance"], spec["prior_exposure"]
    anchor_rows = [
        f"| {labels[m]} | {scope} | {a['wer_REF']['estimate']:.6f} | {a['wer_OPUS_FFMPEG']['estimate']:.6f} | "
        f"{a['T_ffmpeg']['estimate']:.6f} [{a['T_ffmpeg']['ci'][0]:.6f}, {a['T_ffmpeg']['ci'][1]:.6f}] |"
        for m, scopes in spec["stage3_anchors"].items() for scope, a in scopes.items()]
    lines = [
        f"# R4: {spec['title']} - frozen plan", "",
        f"Sealed `r4_spec.json` SHA-256 `{spec['spec_sha256']}`, created {spec['created_utc']}.", "",
        f"**Status: {spec['status']}**", "",
        f"**Label: {spec['label']}**", "",
        "This file is rendered from `r4_spec.json`; the JSON record is authoritative.", "",
        "## 1. Question and scope", "", spec["question"], "", "R4 is not:", "", *_block(spec["is_not"]), "",
        "Claim boundaries:", "", *_block(spec["claim_boundaries"]), "",
        "## 2. Provenance and environment", "",
        *[f"- {k}: `{json.dumps(v) if isinstance(v, dict) else v}`" for k, v in P.items()
          if k != "working_tree_status"],
        f"- working tree at freeze: {P['working_tree_status'] or 'clean'}", "",
        *[f"- {k}: `{json.dumps(v) if isinstance(v, dict) else v}`" for k, v in spec["environment"].items()], "",
        "## 3. Prior exposure (disclosure)", "", X["summary"], "",
        f"- R1 RS1 gate E2, calibration set (report `{X['r1_e2_calibration']['report_sha256'][:12]}...`): "
        f"`{json.dumps(X['r1_e2_calibration']['opus_decoder_difference'])}`",
        f"- R1 RS3 confirmation part (report `{X['r1_confirmation_part']['report_sha256'][:12]}...`, rows "
        f"`{X['r1_confirmation_part']['rows_sha256'][:12]}...`): R1-G1..G3 "
        f"{X['r1_confirmation_part']['gates_R1_G1_G3']}; OPUS decoder difference "
        f"`{json.dumps(X['r1_confirmation_part']['opus_decoder_difference'])}`; OPUS_REFDEC lag vs REF "
        f"`{json.dumps(X['r1_confirmation_part']['opus_refdec_lag_vs_ref_counts'])}`, median RMS change "
        f"{X['r1_confirmation_part']['opus_refdec_rms_change_db_median']:.3f} dB, all lengths equal REF: "
        f"{X['r1_confirmation_part']['opus_refdec_length_equals_ref_all']}",
        f"- R1 exploratory post-gate diagnosis `{X['r1_post_gate_diagnosis']['diagnosis_sha256'][:12]}...` "
        f"({X['r1_post_gate_diagnosis']['label']})",
        f"- Not seen: {X['not_seen']}", "",
        "## 4. Selections (no new selection)", "",
        "| Role | File | SHA-256 | Size | Used by |", "|---|---|---|---|---|",
        *[f"| {role} | `{s['path']}` | `{s['sha256'][:12]}...` | {s['size']} | {s['used_by']}; {s['note']} |"
          for role, s in spec["selections"].items() if role != "rule"],
        "", spec["selections"]["rule"], "",
        "## 5. Conditions", "", *_block(spec["conditions"]), "",
        "## 6. Decoder implementation", "", *_block(spec["decoder"]), "",
        "## 7. Gates", "", *_block(spec["gates"]), "",
        "Stage 3 anchors that G9 must reproduce (confirmation, micro, pp):", "",
        "| Recogniser | Scope | WER(REF) | WER(OPUS_FFMPEG) | T_ffmpeg [95 % CI] |", "|---|---|---|---|---|",
        *anchor_rows, "",
        "## 8. Recognition run", "", *_block(spec["asr_run"]), "",
        "## 9. Estimands, bootstrap and outcome rule", "", *_block(spec["estimands"]), "",
        spec["bootstrap"], "", *_block(spec["outcome_rule"]), "",
        "## 10. Descriptive diagnostics", "", *_block(spec["descriptive_diagnostics"]), "",
        "## 11. Manuscript consequences", "", *_block(spec["manuscript_consequences"]), "",
        "## 12. Stopping rules", "", *_block(spec["stopping_rules"]), "",
        "## 13. Run order and commands", "", *_block(spec["run_order"]), "",
        *[f"- {c['step']}: `{c['command']}`" for c in spec["commands"]], "",
        f"Outputs: `{json.dumps(spec['outputs'])}`", "",
        "## 14. Policies and compute", "", *_block(spec["policies"]), "", spec["compute_estimate"], "",
    ]
    return "\n".join(lines)


# ==================================================
# Freeze, check and guards
# ==================================================

def code_hashes() -> dict:
    files = R4_CODE_FILES + OTHER_CODE_USED + list(s3.CODE_FILES)
    return {str(p): (s3.file_sha256(p) if p.exists() else None) for p in files}


def inputs_unchanged(spec: dict) -> None:
    current = recorded_inputs()
    changed = sorted(k for k, v in current.items() if spec["provenance"].get(k) != v)
    if changed:
        raise RuntimeError(f"inputs changed since the design freeze: {changed}")
    if s3.native(stage3_anchors()) != spec["stage3_anchors"]:
        raise RuntimeError("Stage 3 anchors differ from the frozen plan")
    upgrade.stage3_integrity()


def environment_unchanged(spec: dict) -> list[str]:
    """G5: the recorded environment and decoder settings equal the sealed ones; returns the differences."""
    now = s3.native(environment())
    return sorted(k for k in spec["environment"] if spec["environment"][k] != now.get(k))


def require_frozen_plan(committed: bool) -> dict:
    spec = s3.read_sealed(SPEC_JSON, "spec_sha256")
    if PLAN_MD.read_text() != render(spec):
        raise RuntimeError(f"{PLAN_MD} is not the rendering of the sealed plan")
    if committed:
        for path in [SPEC_JSON, PLAN_MD]:
            upgrade.tracked_and_clean(path)
    inputs_unchanged(spec)
    return spec


def require_code_freeze(committed: bool) -> tuple[dict, dict]:
    spec = require_frozen_plan(committed)
    freeze = s3.read_sealed(CODE_FREEZE, "freeze_sha256")
    if freeze["spec_sha256"] != spec["spec_sha256"]:
        raise RuntimeError("plan changed since the code freeze")
    current = code_hashes()
    changed = sorted(f for f, digest in freeze["code_sha256"].items() if current.get(f) != digest)
    if changed:
        raise RuntimeError(f"code changed since the code freeze: {changed}")
    if committed:
        upgrade.tracked_and_clean(CODE_FREEZE)
    return spec, freeze


def freeze_spec() -> None:
    if SPEC_JSON.exists() or PLAN_MD.exists():
        raise RuntimeError("the R4 plan is already frozen")
    if RESULTS.exists():
        raise RuntimeError(f"{RESULTS} exists: the plan must precede every R4 step")
    digest = s3.write_sealed(SPEC_JSON, s3.native(build_spec()), "spec_sha256")
    PLAN_MD.write_text(render(s3.read_sealed(SPEC_JSON, "spec_sha256")))
    print(f"R4 spec sha256 {digest}")


def check() -> None:
    spec = s3.read_sealed(SPEC_JSON, "spec_sha256")
    print(f"seal: OK ({spec['spec_sha256']})")
    if PLAN_MD.read_text() != render(spec):
        raise RuntimeError(f"{PLAN_MD} is not the rendering of the sealed plan")
    print("plan rendering: OK")
    inputs_unchanged(spec)
    print("recorded inputs, Stage 3 anchors and Stage 3 integrity: unchanged")
    print("environment differences (G5):", environment_unchanged(spec) or "none")
    committed = all(upgrade.git("ls-files", "--error-unmatch", str(p)).returncode == 0 for p in [SPEC_JSON, PLAN_MD])
    print("plan committed:", "yes" if committed else "no (not yet approved)")
    print("code freeze:", "sealed" if CODE_FREEZE.exists() else "not yet")
    outputs = [str(p) for p in EVALUATION_OUTPUTS if p.exists()]
    print("R4 evaluation outputs:", outputs or "none")


def freeze_code() -> None:
    spec = require_frozen_plan(committed=False)
    if CODE_FREEZE.exists():
        raise RuntimeError(f"{CODE_FREEZE} is sealed and exists")
    parts = {name: s3.read_sealed(path, "report_sha256") for name, path in DRY_RUN_PARTS.items()}
    failed = [name for name, part in parts.items() if not part["pass"] or part["spec_sha256"] != spec["spec_sha256"]]
    if failed:
        raise RuntimeError(f"the RS1 dry run did not pass ({failed}); the code cannot be frozen")
    current = code_hashes()
    missing = sorted(f for f, digest in current.items() if digest is None)
    if missing:
        raise RuntimeError(f"code files missing at the code freeze: {missing}")
    at_design = spec["code_sha256_at_design_freeze"]
    s3.write_sealed(CODE_FREEZE, {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
        "dry_run_report_sha256": {name: part["report_sha256"] for name, part in parts.items()},
        "code_sha256": current,
        "code_added_since_design_freeze": sorted(f for f in current if at_design.get(f) is None),
        "code_changed_since_design_freeze": sorted(f for f in current if at_design.get(f) not in (None, current[f])),
    }, "freeze_sha256")
    print(f"R4 code freeze sealed: {s3.read_sealed(CODE_FREEZE, 'freeze_sha256')['freeze_sha256']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["freeze-spec", "check", "freeze-code"])
    args = parser.parse_args()
    os.chdir(REPO_ROOT)
    {"freeze-spec": freeze_spec, "check": check, "freeze-code": freeze_code}[args.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
