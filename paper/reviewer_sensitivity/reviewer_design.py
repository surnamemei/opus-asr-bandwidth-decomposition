"""
Reviewer-concern sensitivity analyses R1-R3: the frozen plan (revision 2).

    R1  decoder sensitivity with a decoder-matched control: the identical Stage 3 OPUS and
        SILK packets decoded by FFmpeg 6.1.1's native decoder (the frozen path) and by the
        libopus 1.4 reference decoder. The control for the reference-decoder chain is the
        frozen LP only if it passes a pre-specified control-reuse gate against the
        libopus-decoded SILK40 linear response; otherwise LP_LIBOPUS, built by the unchanged
        Stage 2B procedure and validated independently.
    R2  the 8-kbit/s effective coherent-linear surrogate (SURR8): a zero-phase linear
        surrogate of the coherent linear response of Opus at 8 kbit/s: an alternative
        attribution under a more inclusive same-frequency linear-loss definition.
    R3  forced-wideband 8 kbit/s practical counterfactual on the 1,665 Addition-B sweep
        utterances: WER(WB8) - WER(NB8), outcome WB_BETTER / NO_CLEAR_DIFFERENCE / WB_WORSE.

All three are post-confirmation sensitivity analyses, specified after Stage 3 and after the
TASLP-upgrade additions A and B.

Commands (this file encodes, decodes, filters and recognises nothing):

    select        seal selection_signal_validation.json: a new signal-only validation subset
                  of train-clean-100 speakers outside the Stage 2B filter-validation set.
                  Reads SPEAKERS.TXT and file names only.
    diagnose-r2   seal r2_planning_diagnosis.json: the 1,625 Hz planning probe and its
                  diagnosis, computed from frozen Stage 2B transfer curves only.
    freeze-spec   seal reviewer_spec.json and render 00_REVIEWER_SENSITIVITY_PLAN.md.
    check         verify the seals, the rendering and every recorded input (files only).
    freeze-code   (step RS2, after the calibration step RS1) seal
                  results_paper/reviewer_sensitivity/code_freeze.json.

The runner (run_reviewer_sensitivity.py, written at step RS1) calls require_frozen_plan()
or require_code_freeze() before it does anything. rule(), combine() and r3_outcome()
implement the plan's interpretation rules exactly.
"""

import argparse
import hashlib
import json
import math
import os
import random
import sys
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "taslp_upgrade"), str(HERE.parent)]

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import opus_direct                      # noqa: E402
import run_lowpass_confirmation as s2c  # noqa: E402
import run_lowpass_validation as s2b    # noqa: E402
import run_stage3 as s3                 # noqa: E402
import stage3_asr as asr                # noqa: E402
import stage3_audio as audio            # noqa: E402
import stage3_stats as s3stats          # noqa: E402
import upgrade_amendments as amendments  # noqa: E402
import upgrade_design as upgrade        # noqa: E402
import upgrade_pipeline as pipe         # noqa: E402
import upgrade_stats as ustats          # noqa: E402


# ==================================================
# Paths (relative to the repository root)
# ==================================================

REPO_ROOT = HERE.parents[1]
REVIEW = Path("paper") / "reviewer_sensitivity"
SPEC_JSON = REVIEW / "reviewer_spec.json"
PLAN_MD = REVIEW / "00_REVIEWER_SENSITIVITY_PLAN.md"
LITERATURE_NOTE = REVIEW / "01_LITERATURE_NOTE.md"
SV_SELECTION = REVIEW / "selection_signal_validation.json"
R2_DIAGNOSIS = REVIEW / "r2_planning_diagnosis.json"
RESULTS = Path("results_paper") / "reviewer_sensitivity"
CODE_FREEZE = RESULTS / "code_freeze.json"
CALIBRATION_REPORT = RESULTS / "calibration" / "calibration_report.json"
LP_LIBOPUS_FILTER = RESULTS / "calibration" / "lp_libopus_filter.json"
SURR8_FILTER = RESULTS / "calibration" / "surr8_filter.json"
EVALUATION_OUTPUTS = [RESULTS / name for name in ["validation", "raw", "analysis"]]

STAGE2B_FILTER = s2b.FILTER_PATH
STAGE2B_CALIBRATION_CURVES = s2b.OUTPUT_DIR / "calibration_curves.csv"
STAGE2B_CURVES = s2b.OUTPUT_DIR / "transfer_curves.csv"
FV_SELECTION = s2c.SELECTION_PATH
FV_SPEC = s2c.SPEC_PATH
FV_CURVES = s2c.OUTPUT_DIR / "transfer_curves.csv"
A_DECISION = upgrade.RESULTS / "level" / "analysis" / "level_decision.json"
B_DECISION = upgrade.RESULTS / "sweep" / "analysis" / "sweep_decision.json"
B_VALIDATION_REPORT = upgrade.RESULTS / "sweep" / "validation" / "validation_report.json"
B_VALIDATION_ROWS = upgrade.RESULTS / "sweep" / "validation" / "validation_rows.csv"
B_POOLED = upgrade.RESULTS / "sweep" / "raw" / "pooled_transfer.csv"
S3_POOLED = upgrade.S3_CONFIRMATION / "pooled_transfer.csv"

# Code of R1-R3; the last three files are written at step RS1 and are absent at the design freeze
REVIEW_CODE_FILES = [REVIEW / name for name in [
    "reviewer_design.py", "reviewer_pipeline.py", "reviewer_stats.py", "run_reviewer_sensitivity.py",
]]
OTHER_CODE_USED = [upgrade.UPGRADE / name for name in [
    "upgrade_design.py", "upgrade_pipeline.py", "upgrade_stats.py", "upgrade_amendments.py",
]] + [Path("paper") / "run_lowpass_confirmation.py"]

# The uncommitted draft that this revision supersedes (sealed, never committed, nothing run)
SUPERSEDED_DRAFT = {
    "spec_sha256": "668202b9b900aef09ddaf20183f98de5bc2f2e1bb3705949e18b5226485fb57f",
    "created_utc": "2026-09-27T04:45:48.630399+00:00",
}

# ==================================================
# Frozen design constants
# ==================================================

MODELS = asr.MODELS
N_BOOT = s3stats.N_BOOT                 # 10,000, as Stage 3, A and B
CONFIRMATION_SEED = s3stats.BOOT_SEED   # 5305: Stage 3's seed on Stage 3's speakers (as A)
SWEEP_SEED = ustats.SWEEP_SEED          # 5306: B's seed on B's speakers
MATERIALITY_FRACTION = 0.25             # a quarter of the frozen Stage 3 residual T*: A's GO margin

GATE_RESULTS = ("PASS", "FAIL")
OUTCOMES = ("SUPPORT", "WEAKEN")                         # R1, R2
QUALIFIERS = ("reduction shown", "not established")      # qualifiers of WEAKEN
R3_OUTCOMES = ("WB_BETTER", "NO_CLEAR_DIFFERENCE", "WB_WORSE")
STOPPED = "STOPPED"
SUPPORT_BY_IDENTITY = {"outcome": "SUPPORT", "qualifier": "by identity (no ASR)"}

BASE_CONDITIONS = ["REF", "LP", "OPUS", "SILK"]
OPUS_REFDEC, SILK_REFDEC, LP_LIBOPUS = "OPUS_REFDEC", "SILK_REFDEC", "LP_LIBOPUS"
SURR8 = "SURR8"
NB8, WB8 = "NB8", "WB8"
CONFIRMATION_CONDITIONS = {"R1": [OPUS_REFDEC, SILK_REFDEC, LP_LIBOPUS], "R2": [SURR8]}
SWEEP_CONDITIONS = {"R3": [NB8, WB8]}

# (residual-like primary quantity, rule quantity, sign that turns the rule quantity into the
# reduction of the residual caused by the analysis's change)
RULE_QUANTITIES = {"R1": ("P1", "D1", -1.0), "R2": ("P2", "Delta2", 1.0)}

# R1: reference decoder and decoder-matched control
REFERENCE_DECODER_RATE = 48000
REFERENCE_DECODER_MAX_FRAME = 5760      # 120 ms at 48 kHz, the longest Opus packet
SAMPLES_PER_PACKET_48K = 960            # 20 ms frames
R1_EQ_BAND_HZ = tuple(s2b.TOLERANCES["g6_h1_rms_band_hz"])        # [3000, 4200]: the primary edge upwards
R1_EQ_ABS_BAND_HZ = tuple(s2b.TOLERANCES["g6_h1_abs_band_hz"])    # [3000, 4150]
R1_EQ_RMS_MARGIN_DB = s2b.PASSBAND_DEVIATION_DB                   # 0.5 dB

# R1 and R2: calibration reproduction of frozen Stage 2B curves
REPRODUCTION_TOLERANCE_DB = 0.01
REPRODUCTION_UP_TO_HZ = 4150.0          # the Stage 2B convergence ("measurable") range

# R2: SURR8 validation (every tolerance is the unchanged Stage 2B value)
R2_TOLERANCE_SOURCES = {
    "V1_max_abs_lag_samples": "g1_max_abs_lag_samples",
    "V2_min_coherence": "g3_min_coherence",
    "V2_up_to_hz": "g3_min_coherence_up_to_hz",
    "V3_rms_max_db": "g6_h1_rms_max_db",
    "V3_rms_band_upper_hz": ("g6_h1_rms_band_hz", 1),
    "V3_abs_max_db": "g6_h1_abs_max_db",
    "V3_abs_band_upper_hz": ("g6_h1_abs_band_hz", 1),
    "V4_threshold_db": "g4_coherent_bw_threshold_db",
    "V4_max_hz": "g4_coherent_bw_vs_reference_max_hz",
    "V5_max_db": "g5_coherent_hf_vs_reference_max_db",
    "V6_from_hz": "g6_stopband_from_hz",
    "V6_max_db": "g6_stopband_max_db",
}
R2_RESPONSE_REPORT_HZ = [1000.0, 2000.0, 3000.0, 3500.0, 4000.0]

# R2 planning diagnosis (frozen curves only)
DIAGNOSIS_SETS = ["dev-clean", "dev-other", "train-clean-100"]
DIAGNOSIS_CELLS = ["opus_8k_nb", "opus_12k_nb", "silk_nb_linear_ref", "lp"]
DIAGNOSIS_DEVIATIONS_DB = [0.25, 0.5, 1.0]
DIAGNOSIS_LEVEL_BANDS_HZ = [(500.0, 2000.0), (250.0, 1000.0), (500.0, 1000.0), (300.0, 3400.0)]
DIAGNOSIS_HZ = [250.0, 1000.0, 1500.0, 1625.0, 2000.0, 2500.0, 3000.0, 3500.0, 3812.5, 4000.0, 4125.0]
PLANNING_PROBE_EDGE_HZ = 1625.0

# New signal-only validation subset (R1-V and R2-V)
SV_SUBSET = "train-clean-100"
SV_SEED = 53055                         # selection seeds so far: 53051-53053 (Stage 3), 53054 (B)
SV_SPEAKERS_PER_SEX = 20

# R3: forced wideband at 8 kbit/s on the sweep utterances
NB8_SETTINGS = audio.CODEC_SETTINGS["OPUS"]
WB8_SETTINGS = opus_direct.EncoderSettings(bitrate_bps=8000, bandwidth="WB")
WB_CONFIGURATION = 9                    # RFC 6716 TOC: SILK-only, WB, 20 ms
BITRATE_TOLERANCE = upgrade.BITRATE_TOLERANCE   # 15 % of nominal, as B's V2
RATE_MATCH_TOLERANCE = 0.10             # WB8 median payload within 10 % of NB8's
HF_REALISED_MIN_DB = -10.0              # pooled total 4-8 kHz power against REF

SECONDS_PER_UTTERANCE_SIX_CONDITIONS = 1.59     # Stage 3 measurement (RTX 5090)


# ==================================================
# Interpretation rules (exact)
# ==================================================

def rule(analysis: str, intervals: dict, t_star: float) -> dict:
    """
    SUPPORT / WEAKEN for R1 or R2 and one recogniser. intervals maps the analysis's two rule
    quantities to their 95 % percentile intervals (lo, hi) in pp: R1 {P1, D1}, R2 {P2, Delta2}.
    The reduction of the residual is -D1 (R1) or Delta2 (R2). SUPPORT: the residual-like
    quantity's lower bound is above 0 and the reduction's upper bound is below
    MATERIALITY_FRACTION x T*. WEAKEN otherwise: 'reduction shown' if the reduction's lower
    bound is above that margin, 'not established' if not. A missing (NaN) bound never
    satisfies SUPPORT.
    """
    primary, change, sign = RULE_QUANTITIES[analysis]
    margin = MATERIALITY_FRACTION * float(t_star)
    p_lo = float(intervals[primary][0])
    c_lo, c_hi = (float(v) for v in intervals[change])
    r_lo, r_hi = (c_lo, c_hi) if sign > 0 else (-c_hi, -c_lo)
    record = {"analysis": analysis, "margin_pp": margin, "reduction_interval_pp": [r_lo, r_hi],
              "primary_lower_pp": p_lo}
    if all(math.isfinite(v) for v in (p_lo, r_lo, r_hi, margin)) and p_lo > 0 and r_hi < margin:
        return {**record, "outcome": "SUPPORT", "qualifier": None}
    shown = math.isfinite(r_lo) and math.isfinite(margin) and r_lo > margin
    return {**record, "outcome": "WEAKEN", "qualifier": QUALIFIERS[0] if shown else QUALIFIERS[1]}


def combine(per_model: dict) -> str:
    """Overall outcome of R1 or R2: SUPPORT only if SUPPORT for every recogniser."""
    if set(per_model) != set(MODELS):
        raise ValueError(f"need an outcome for each of {MODELS}")
    return "SUPPORT" if all(r["outcome"] == "SUPPORT" for r in per_model.values()) else "WEAKEN"


def r3_outcome(w_lo: float, w_hi: float) -> str:
    """R3 outcome for one recogniser from the 95 % interval of W = WER(WB8) - WER(NB8)."""
    if math.isfinite(w_hi) and w_hi < 0:
        return "WB_BETTER"
    if math.isfinite(w_lo) and w_lo > 0:
        return "WB_WORSE"
    return "NO_CLEAR_DIFFERENCE"


# ==================================================
# select: the new signal-only validation subset (metadata only)
# ==================================================

def draw_signal_validation() -> dict:
    """
    20 female and 20 male train-clean-100 speakers outside the Stage 2B filter-validation set,
    one utterance each, with the filter-validation rule and a new seed. Reads SPEAKERS.TXT and
    file names only.
    """
    fv_spec = s3.read_sealed(FV_SPEC, "spec_sha256")
    fv = fv_spec["confirmation_set"]
    excluded = set(fv["speakers_female"]) | set(fv["speakers_male"])
    speakers = s2c.read_speakers()
    rng = random.Random(SV_SEED)
    chosen = {}
    for sex in ["F", "M"]:
        pool = sorted(s["id"] for s in speakers
                      if s["subset"] == SV_SUBSET and s["sex"] == sex and s["id"] not in excluded)
        chosen[sex] = sorted(rng.sample(pool, SV_SPEAKERS_PER_SEX))
    selected = chosen["F"] + chosen["M"]
    dev = {int(p.name) for subset in s2c.DEV_SUBSETS for p in s2c.subset_dir(subset).iterdir() if p.is_dir()}
    if dev & set(selected) or excluded & set(selected):
        raise RuntimeError("signal-validation speakers overlap the dev sets or the filter-validation set")
    root = s2c.subset_dir(SV_SUBSET)
    rng = random.Random(SV_SEED)
    utterances = []
    for speaker in sorted(selected):
        files = sorted(p.relative_to(root).as_posix() for p in (root / str(speaker)).glob("*/*.flac"))
        if not files:
            raise RuntimeError(f"no audio files for speaker {speaker}")
        path = rng.choice(files)
        speaker_id, chapter_id, utterance_id = Path(path).stem.split("-")
        utterances.append({"speaker_id": int(speaker_id), "chapter_id": int(chapter_id),
                           "utterance_id": int(utterance_id), "path": path, "candidates": len(files)})
    return {
        "subset": SV_SUBSET,
        "role": "signal-only validation subset for R1-V and R2-V: no transcript is read and no ASR is run",
        "speaker_source": str(s2c.SPEAKERS_FILE),
        "speakers_file_sha256": s3.file_sha256(s2c.SPEAKERS_FILE),
        "seed": SV_SEED,
        "speaker_rule": f"random.Random({SV_SEED}).sample of {SV_SPEAKERS_PER_SEX} female then "
                        f"{SV_SPEAKERS_PER_SEX} male speakers from the sorted {SV_SUBSET} IDs in SPEAKERS.TXT, "
                        "excluding the 40 speakers of the Stage 2B filter-validation set",
        "utterance_rule": s2c.UTTERANCE_RULE.replace(f"random.Random({s2c.SEED})", f"random.Random({SV_SEED})"),
        "excluded_filter_validation_speakers": sorted(excluded),
        "filter_validation_spec_sha256": fv_spec["spec_sha256"],
        "speakers_female": chosen["F"],
        "speakers_male": chosen["M"],
        "disjoint_from_dev_and_filter_validation_speakers": True,
        "utterances": utterances,
    }


def select() -> None:
    if SV_SELECTION.exists():
        raise RuntimeError(f"{SV_SELECTION} is sealed and exists")
    digest = s3.write_sealed(SV_SELECTION, {"created_utc": s3.now(), **draw_signal_validation()},
                             "selection_sha256")
    print(f"signal-validation selection sha256 {digest}")


# ==================================================
# diagnose-r2: the planning probe, from frozen curves only
# ==================================================

def frozen_curves() -> dict:
    curves = {}
    for path in [STAGE2B_CURVES, FV_CURVES]:
        table = pd.read_csv(path)
        for (subset, cell), group in table.groupby(["subset", "cell"]):
            group = group.sort_values("frequency_hz")
            if not np.allclose(group["frequency_hz"].to_numpy(), s2b.FREQS):
                raise RuntimeError(f"{path}: unexpected frequency grid")
            curves[(subset, cell)] = group
    return curves


def edge_hz(h1_rel_db: np.ndarray, deviation_db: float) -> float:
    """build_target's passband edge for a given deviation (build_target uses 0.5 dB)."""
    stays_below = np.array([np.max(h1_rel_db[k:]) <= -deviation_db for k in range(len(s2b.FREQS))])
    return float(s2b.FREQS[int(np.argmax(stays_below))])


def renormalised(h1_rel_db: np.ndarray, band: tuple) -> np.ndarray:
    """h1_rel_db re-normalised to the mean linear gain over another level band."""
    inside = (s2b.FREQS >= band[0]) & (s2b.FREQS <= band[1])
    return h1_rel_db - 20.0 * np.log10(np.mean(10.0 ** (h1_rel_db[inside] / 20.0)))


def diagnosis_body() -> dict:
    curves = frozen_curves()
    freqs = s2b.FREQS
    edges = {s: {c: {f"{d:g}": edge_hz(curves[(s, c)]["h1_rel_db"].to_numpy(), d)
                     for d in DIAGNOSIS_DEVIATIONS_DB} for c in DIAGNOSIS_CELLS} for s in DIAGNOSIS_SETS}
    bands = {s: {f"{b[0]:g}-{b[1]:g}": edge_hz(renormalised(curves[(s, "opus_8k_nb")]["h1_rel_db"].to_numpy(), b),
                                               s2b.PASSBAND_DEVIATION_DB)
                 for b in DIAGNOSIS_LEVEL_BANDS_HZ} for s in DIAGNOSIS_SETS}
    shape, depth = {}, {}
    for s in DIAGNOSIS_SETS:
        h1 = curves[(s, "opus_8k_nb")]["h1_rel_db"].to_numpy()
        coherence = curves[(s, "opus_8k_nb")]["coherence"].to_numpy()
        lp = curves[(s, "lp")]["h1_rel_db"].to_numpy()
        target, edge = s2b.build_target(h1)
        rows = []
        for hz in DIAGNOSIS_HZ:
            i = int(np.argmin(np.abs(freqs - hz)))
            rows.append({"hz": float(freqs[i]), "opus8_h1_rel_db": float(h1[i]), "opus8_coherence": float(coherence[i]),
                         "target_db": float(target[i]), "lp_h1_rel_db": float(lp[i]),
                         "target_minus_lp_db": float(target[i] - lp[i])})
        shape[s] = rows
        above = (freqs >= edge) & (freqs <= REPRODUCTION_UP_TO_HZ)
        depth[s] = float(np.max(np.minimum(h1, 0.0)[above] - target[above]))
    e = {s: edges[s]["opus_8k_nb"]["0.5"] for s in DIAGNOSIS_SETS}
    silk = [edges[s]["silk_nb_linear_ref"]["0.5"] for s in DIAGNOSIS_SETS]
    b_all = [v for s in DIAGNOSIS_SETS for v in bands[s].values()]
    extra = [r["target_minus_lp_db"] for s in DIAGNOSIS_SETS for r in shape[s] if 2500.0 <= r["hz"] <= 4000.0]
    upper = [hz for hz in DIAGNOSIS_HZ if 2500.0 <= hz <= 4000.0]
    spread = max(max(r["target_db"] for s in DIAGNOSIS_SETS for r in shape[s] if r["hz"] == hz)
                 - min(r["target_db"] for s in DIAGNOSIS_SETS for r in shape[s] if r["hz"] == hz) for hz in upper)
    coh = {r["hz"]: r["opus8_coherence"] for r in shape["dev-clean"]}
    names = [f"{b[0] / 1000:g}-{b[1] / 1000:g}" for b in DIAGNOSIS_LEVEL_BANDS_HZ]
    level_bands = f"{names[0]} (frozen), " + ", ".join(names[1:-1]) + f" or {names[-1]}"
    return {
        "probe": {
            "date": "2026-09-27",
            "statement": "While the superseded draft (spec "
                         f"{SUPERSEDED_DRAFT['spec_sha256'][:12]}...) was being written, "
                         "run_lowpass_validation.build_target was applied once to the frozen opus_8k_nb h1_rel_db "
                         "curve of the Stage 2B filter-validation set (train-clean-100). It gave an edge of "
                         f"{PLANNING_PROBE_EDGE_HZ:g} Hz. No tolerance of that draft was changed (all were unchanged "
                         "Stage 2B values), but that draft validated R2 on the same set.",
            "result_edge_hz": PLANNING_PROBE_EDGE_HZ,
            "reproduced_here_hz": e["train-clean-100"],
        },
        "sources": {str(p): s3.file_sha256(p) for p in [STAGE2B_CURVES, FV_CURVES]},
        "edges_hz_by_deviation_db": edges,
        "opus8_edges_hz_by_level_band": bands,
        "opus8_shape": shape,
        "running_minimum_depth_db": depth,
        "findings": [
            "The planning probe reproduces: the unchanged Stage 2B target construction puts the edge of Opus "
            f"8 kbit/s's coherent response at {e['train-clean-100']:g} Hz on the filter-validation set.",
            f"It is not a property of Opus 8 kbit/s alone: the same construction gives {e['dev-clean']:g} Hz on "
            f"dev-clean (the calibration data of R2) and {e['dev-other']:g} Hz on dev-other, whereas the SILK-NB "
            f"reference at 40 kbit/s gives {min(silk):g}-{max(silk):g} Hz on all three sets.",
            f"It depends on the construction constants: with the level band set to {level_bands} kHz, the edge "
            f"ranges from {min(b_all):g} to {max(b_all):g} Hz across the three sets.",
            "Cause: relative to its 0.5-2 kHz level, the coherent response of Opus at 8 kbit/s declines smoothly "
            "across the band (dev-clean: "
            + ", ".join(f"{r['opus8_h1_rel_db']:+.1f} dB at {r['hz'] / 1000:g} kHz" for r in shape["dev-clean"]
                        if r["hz"] in (250.0, 1500.0, 2500.0, 3000.0, 3500.0))
            + "), and so does its coherence ("
            + ", ".join(f"{coh[hz]:.2f} at {hz / 1000:g} kHz" for hz in (250.0, 1500.0, 3000.0))
            + "). The 'edge' is where this decline first stays below -0.5 dB. It marks the start of a gradual "
            "loss of coherent (linearly predictable) content through low-rate coding, not a band limit.",
            f"Between 2.5 and 4 kHz the three sets' targets agree to within {spread:.1f} dB, and the surrogate "
            f"target lies {-max(extra):.1f} to {-min(extra):.1f} dB below LP there on every set.",
            f"The running minimum lies up to {max(depth.values()):.2f} dB below the capped curve (non-monotone "
            "ripples), so the target is an envelope, not the measured response itself.",
        ],
        "consequences": [
            "The filter-validation set, whose Opus 8 kbit/s curve was inspected, validates neither R1 nor R2. A new "
            "signal-only validation subset (selection_signal_validation.json) is drawn before this freeze, and none "
            "of its audio is read before RS3.",
            "The R2 condition is described as the 8-kbit/s effective coherent-linear surrogate (SURR8) for "
            "an alternative attribution under a more inclusive same-frequency linear-loss definition, not as a "
            "bandwidth control; its 'edge' is reported as a construction "
            "parameter, not as a bandwidth.",
            "The surrogate construction stays the unchanged Stage 2B procedure: no constant is tuned to these "
            f"results. On the frozen dev-clean curve its edge is {e['dev-clean']:g} Hz; RS1 must reproduce that "
            "curve (gate R2-C1), so this is the edge SURR8 will have.",
            "R2-V3 compares the whole surrogate response, from that calibration edge to 4.2 kHz, with the target "
            "built from the new subset; the between-set variation shown above is exactly what V3 tests.",
        ],
    }


def diagnose_r2() -> None:
    if R2_DIAGNOSIS.exists():
        raise RuntimeError(f"{R2_DIAGNOSIS} is sealed and exists")
    digest = s3.write_sealed(R2_DIAGNOSIS, {"created_utc": s3.now(), **diagnosis_body()}, "diagnosis_sha256")
    print(f"R2 planning diagnosis sha256 {digest}")


# ==================================================
# Inputs read to freeze the plan (sealed and frozen files only)
# ==================================================

def recorded_inputs() -> dict:
    """Identifiers of every sealed input; require_frozen_plan() re-checks each one."""
    fv = s3.read_sealed(FV_SELECTION, "selection_sha256")
    fv_spec = s3.read_sealed(FV_SPEC, "spec_sha256")
    if fv["spec_sha256"] != fv_spec["spec_sha256"]:
        raise RuntimeError("the filter-validation selection was not made under its sealed spec")
    frozen = json.loads(STAGE2B_FILTER.read_text())
    if frozen["metadata"]["tolerances_sha256"] != s2b.tolerances_sha256():
        raise RuntimeError("Stage 2B tolerances differ from those frozen with the primary control")
    if s2c.REVISED_TOLERANCES != fv_spec["revised_tolerances"]:
        raise RuntimeError("revised Stage 2B tolerances differ from their sealed spec")
    a = s3.read_sealed(A_DECISION, "decision_sha256")
    b = s3.read_sealed(B_DECISION, "decision_sha256")
    b_validation = s3.read_sealed(B_VALIDATION_REPORT, "report_sha256")
    if s3.file_sha256(B_VALIDATION_ROWS) != b_validation["rows_sha256"]:
        raise RuntimeError("B validation rows differ from their sealed report")
    return {
        **upgrade.stage3_integrity(),
        "upgrade_spec_sha256": s3.read_sealed(upgrade.SPEC_JSON, "spec_sha256")["spec_sha256"],
        "upgrade_code_freeze_sha256": s3.read_sealed(upgrade.CODE_FREEZE, "freeze_sha256")["freeze_sha256"],
        "upgrade_amendments_sha256": [r["amendment_sha256"] for r in amendments.load_all()],
        "addition_A_decision_sha256": a["decision_sha256"],
        "addition_A_outcome": a["outcome"],
        "addition_B_decision_sha256": b["decision_sha256"],
        "addition_B_outcome": b["outcome"],
        "sweep_selection_sha256": s3.read_sealed(upgrade.SELECTION, "selection_sha256")["selection_sha256"],
        "addition_B_validation_report_sha256": b_validation["report_sha256"],
        "addition_B_pooled_transfer_sha256": s3.file_sha256(B_POOLED),
        "stage2b_frozen_filter_file_sha256": s3.file_sha256(STAGE2B_FILTER),
        "stage2b_tolerances_sha256": frozen["metadata"]["tolerances_sha256"],
        "stage2b_calibration_curves_sha256": s3.file_sha256(STAGE2B_CALIBRATION_CURVES),
        "stage2b_transfer_curves_sha256": s3.file_sha256(STAGE2B_CURVES),
        "filter_validation_selection_sha256": fv["selection_sha256"],
        "filter_validation_spec_sha256": fv_spec["spec_sha256"],
        "filter_validation_transfer_curves_sha256": s3.file_sha256(FV_CURVES),
        "stage3_confirmation_pooled_transfer_sha256": s3.file_sha256(S3_POOLED),
        "signal_validation_selection_sha256": s3.read_sealed(SV_SELECTION, "selection_sha256")["selection_sha256"],
        "r2_planning_diagnosis_sha256": s3.read_sealed(R2_DIAGNOSIS, "diagnosis_sha256")["diagnosis_sha256"],
        "literature_note_sha256": s3.file_sha256(LITERATURE_NOTE),
    }


def stage3_anchors() -> dict:
    """Frozen Stage 3 pooled micro estimates (confirmation) and the rule margins."""
    boot = pd.read_csv(upgrade.S3_BOOTSTRAP)

    def cell(model, quantity, kind="micro"):
        row = boot[(boot["set"] == "confirmation") & (boot["model"] == model) & (boot["scope"] == "pooled")
                   & (boot["kind"] == kind) & (boot["quantity"] == quantity)]
        if len(row) != 1:
            raise RuntimeError(f"expected one Stage 3 row for {model} {quantity} {kind}")
        row = row.iloc[0]
        return {"estimate": float(row["estimate"]), "ci": [float(row["ci_lower"]), float(row["ci_upper"])]}

    anchors = {}
    for model in MODELS:
        t = cell(model, "delta_opus_residual")
        margin = MATERIALITY_FRACTION * t["estimate"]
        anchors[model] = {
            "T_star": t, "B_star": cell(model, "delta_bw"), "total_star": cell(model, "delta_opus_total"),
            "U_star": cell(model, "delta_silk_residual"),
            "share_star": cell(model, "bw_share_of_opus_total", "ratio"),
            "margin_pp": margin,
            "R1_D1_lower_must_exceed": -margin,
            "R2_Delta2_upper_must_be_below": margin,
        }
    return anchors


def pooled_rows(path: Path, processed: list[str]) -> dict:
    pooled = pd.read_csv(path)
    rows = pooled[(pooled["reference"] == "REF") & pooled["processed"].isin(processed)]
    fields = ["h1_level_db", "coherent_bandwidth_hz", "coherent_hf_power_db", "total_hf_power_db",
              "image_coherence_4100_4900", "mean_coherence_0_3500"]
    return {r["processed"]: {f: float(r[f]) for f in fields} for _, r in rows.iterrows()}


def sweep_anchors() -> dict:
    report = s3.read_sealed(B_VALIDATION_REPORT, "report_sha256")
    rows = pd.read_csv(B_VALIDATION_ROWS)
    return {
        "n_utterances": int((rows["condition"] == "SILK8").sum()),
        "silk8_median_payload_kbps": float(report["measured_median_payload_kbps"][0]),
        "bridge_share_silk8_identical_to_stage3_opus_settings":
            float(report["bridge_share_silk8_identical_to_stage3_opus_settings"]),
        "pooled_against_ref": pooled_rows(B_POOLED, ["LP", "SILK8"]),
    }


def r2_design() -> dict:
    frozen = json.loads(STAGE2B_FILTER.read_text())
    metadata = frozen["metadata"]
    indices = metadata["calibration_dataset_indices"]
    return {
        "procedure": "paper/run_lowpass_validation.py, unchanged: TransferAccumulator, build_target, "
                     "constrain, design",
        "num_taps": s2b.NUM_TAPS, "kaiser_beta": s2b.KAISER_BETA, "design_grid": s2b.DESIGN_GRID,
        "level_band_hz": list(s2b.LEVEL_BAND_HZ), "passband_deviation_db": s2b.PASSBAND_DEVIATION_DB,
        "stopband_floor_db": s2b.STOPBAND_FLOOR_DB, "correction_iterations": s2b.N_CORRECTION_ITERATIONS,
        "correction_floor_db": s2b.CORRECTION_FLOOR_DB,
        "analysis": {"n_fft": s2b.common.N_FFT, "win_length": s2b.common.WIN_LENGTH,
                     "hop_length": s2b.common.HOP_LENGTH, "window": "hann"},
        "primary_control_edge_hz": metadata["design"]["passband_edge_hz"],
        "primary_control_taps_sha256": frozen["taps_sha256"],
        "calibration_subset": metadata["calibration_subset"],
        "calibration_utterances": len(indices),
        "calibration_seconds": metadata["calibration_seconds"],
        "calibration_indices_sha256": hashlib.sha256(json.dumps(indices).encode()).hexdigest(),
    }


def r2_tolerances() -> dict:
    out = {}
    for name, source in R2_TOLERANCE_SOURCES.items():
        if isinstance(source, tuple):
            out[name] = {"value": s2b.TOLERANCES[source[0]][source[1]], "stage2b": f"{source[0]}[{source[1]}]"}
        else:
            out[name] = {"value": s2b.TOLERANCES[source], "stage2b": source}
    return out


def r1_reuse_criteria() -> dict:
    t = s2b.TOLERANCES
    return {
        "coherent_bandwidth_max_hz": t["g4_coherent_bw_vs_reference_max_hz"],
        "coherent_hf_power_max_db": t["g5_coherent_hf_vs_reference_max_db"],
        "rms_band_hz": list(R1_EQ_BAND_HZ), "rms_max_db": t["g6_h1_rms_max_db"],
        "abs_band_hz": list(R1_EQ_ABS_BAND_HZ), "abs_max_db": t["g6_h1_abs_max_db"],
        "rms_margin_over_ffmpeg_db": R1_EQ_RMS_MARGIN_DB,
    }


def settings_table() -> dict:
    nb, silk, wb = (asdict(s) for s in (NB8_SETTINGS, audio.CODEC_SETTINGS["SILK"], WB8_SETTINGS))
    if sorted(k for k in nb if nb[k] != wb[k]) != ["bandwidth"] or (nb["bandwidth"], wb["bandwidth"]) != ("NB", "WB"):
        raise RuntimeError("WB8 must differ from NB8 (the Stage 3 OPUS settings) only in bandwidth (NB -> WB)")
    if silk != asdict(pipe.SWEEP_SETTINGS["SILK40"]):
        raise RuntimeError("the Stage 3 SILK settings must equal B's SILK40")
    b8 = asdict(pipe.SWEEP_SETTINGS["SILK8"])
    if sorted(k for k in nb if nb[k] != b8[k]) != ["signal"]:
        raise RuntimeError("B's SILK8 must differ from the Stage 3 OPUS settings only in the signal hint")
    return {NB8: nb, WB8: wb, "SILK": silk}


def selections() -> dict:
    conf, cal = s3.load_selection("confirmation"), s3.load_selection("calibration")
    sweep = s3.read_sealed(upgrade.SELECTION, "selection_sha256")
    sv = s3.read_sealed(SV_SELECTION, "selection_sha256")
    design = r2_design()
    return {
        "confirmation": {
            "path": str(upgrade.S3 / "selection_confirmation.json"), "sha256": conf["selection_sha256"],
            "size": f"{conf['n_utterances']:,} utterances, {conf['n_speakers']} speakers, {conf['subsets']}",
            "used_by": "R1 and R2: pre-ASR gates R1-G1 to G3 and the ASR run RS4a",
            "note": "decoded a third time (Stage 3, Addition A, R1-R2), for these sensitivity analyses only",
        },
        "sweep": {
            "path": str(upgrade.SELECTION), "sha256": sweep["selection_sha256"],
            "size": f"{sweep['n_utterances']:,} utterances, {sweep['n_speakers']} speakers, {sweep['subsets']}",
            "used_by": "R3: pre-ASR gates R3-G0 to G5 and the ASR run RS4b",
            "note": "Addition B's fresh-utterance, not fresh-speaker, holdout; decoded a second time (B, R3)",
        },
        "technical_calibration": {
            "path": str(upgrade.S3 / "selection_calibration.json"), "sha256": cal["selection_sha256"],
            "size": f"{cal['n_utterances']} utterances, {cal['n_speakers']} speakers, {cal['subsets']}",
            "used_by": "gates E1 and E2 only; no WER is compared between conditions",
        },
        "stage2b_calibration": {
            "path": f"{STAGE2B_FILTER} (dataset indices)", "sha256": design["calibration_indices_sha256"],
            "size": f"{design['calibration_utterances']} {design['calibration_subset']} utterances, "
                    f"{design['calibration_seconds']:.1f} s",
            "used_by": "RS1 calibration only: R1-C1, R1-REUSE and (if needed) the fit of LP_LIBOPUS; R2-C1 and the "
                       "fit of SURR8. These are the utterances that fitted the primary control.",
        },
        "signal_validation": {
            "path": str(SV_SELECTION), "sha256": sv["selection_sha256"],
            "size": f"{len(sv['utterances'])} {sv['subset']} utterances ({len(sv['speakers_female'])} F, "
                    f"{len(sv['speakers_male'])} M speakers, one utterance each)",
            "used_by": "RS3 held-out validation only: R1-V (the decoder-matched control) and R2-V1 to V6 (SURR8); "
                       "signal measurements only, no transcript and no ASR",
            "note": "new; drawn from file names and SPEAKERS.TXT before this freeze, excluding the 40 "
                    "filter-validation speakers; none of its audio is read before RS3",
        },
        "rule": "The Stage 2B filter-validation set (40 train-clean-100 speakers) is not used by R1-R3: its Opus "
                "8 kbit/s curve was inspected while planning. No test utterance outside the confirmation and "
                "sweep selections is read; the sweep reserve stays unused.",
    }


# ==================================================
# The specification
# ==================================================

def build_spec() -> dict:
    inputs = recorded_inputs()
    anchors = stage3_anchors()
    sweep_ref = sweep_anchors()
    transfer = pooled_rows(S3_POOLED, ["LP", "OPUS", "SILK"])
    diagnosis = s3.read_sealed(R2_DIAGNOSIS, "diagnosis_sha256")
    settings = settings_table()
    design = r2_design()
    tolerances = r2_tolerances()
    reuse = r1_reuse_criteria()
    sel = selections()
    tol = {k: v["value"] for k, v in tolerances.items()}
    run, des = ("python paper/reviewer_sensitivity/run_reviewer_sensitivity.py",
                "python paper/reviewer_sensitivity/reviewer_design.py")
    q = f"{MATERIALITY_FRACTION} x T*_m"
    per_condition = SECONDS_PER_UTTERANCE_SIX_CONDITIONS / 6
    conf_n = s3.load_selection("confirmation")["n_utterances"]
    n_conf = len(BASE_CONDITIONS) + sum(len(c) for c in CONFIRMATION_CONDITIONS.values())
    minutes_a = per_condition * n_conf * conf_n / 60
    minutes_b = per_condition * 2 * sweep_ref["n_utterances"] / 60
    w, v = anchors["whisper"], anchors["wav2vec2"]
    op, sk = transfer["OPUS"], transfer["SILK"]
    b_lp, b_s8 = sweep_ref["pooled_against_ref"]["LP"], sweep_ref["pooled_against_ref"]["SILK8"]
    dcal = diagnosis["edges_hz_by_deviation_db"]["dev-clean"]["opus_8k_nb"]["0.5"]
    dshape = {r["hz"]: r for r in diagnosis["opus8_shape"]["dev-clean"]}

    return {
        "stage": "Reviewer-concern sensitivity analyses R1-R3 - design freeze, revision 2",
        "created_utc": s3.now(),
        "status": "PLANNED, NOT RUN. Frozen before any R1-R3 audio was encoded, decoded or filtered, before any "
                  "R1-R3 control or surrogate was fitted and before any R1-R3 ASR run. Inputs read to freeze it: "
                  "sealed Stage 2B, Stage 3 and TASLP-upgrade records, the frozen Stage 2B filter record and "
                  "transfer curves, LibriSpeech SPEAKERS.TXT and file names (new validation subset), and the "
                  "literature note. Binding once committed.",
        "revision_history": [
            f"Supersedes the uncommitted draft sealed {SUPERSEDED_DRAFT['created_utc']} (spec "
            f"{SUPERSEDED_DRAFT['spec_sha256']}). That draft was revised at the author's request after a "
            "reviewer-style critique, before any commit and before any R1-R3 audio, fit or ASR run; it bound "
            "nothing.",
            "R1: the reference-decoder residual now uses a decoder-matched control. The frozen LP is reused only "
            "if it passes a pre-specified control-reuse gate (not a statistical equivalence test) against the "
            "libopus-decoded SILK40 linear response; "
            "otherwise LP_LIBOPUS is built by the unchanged Stage 2B procedure and validated on held-out "
            "speakers.",
            "R2: the planning probe (edge 1,625 Hz) is disclosed and diagnosed before this freeze "
            "(r2_planning_diagnosis.json). Validation moves to a new signal-only subset. The condition is "
            "renamed SURR8 and described as an 8-kbit/s effective coherent-linear surrogate: an alternative "
            "attribution under a more inclusive same-frequency linear-loss definition.",
            "R3: moved to the 1,665 Addition-B sweep utterances, primary estimand WER(WB8) - WER(NB8), outcomes "
            "WB_BETTER / NO_CLEAR_DIFFERENCE / WB_WORSE instead of SUPPORT / WEAKEN.",
            "Terminology only, before commit (no design change): R1's gate is named a control-reuse gate "
            "(R1-REUSE), not a statistical equivalence test; R2 is described as an alternative attribution under "
            "a more inclusive same-frequency linear-loss definition, with s1 and s2 a sensitivity range across two "
            "pre-specified linear definitions, not bounds on a true share.",
        ],
        "scope": [
            "Stage 3 and the TASLP-upgrade additions A and B are closed. Their sealed specifications, "
            "selections, outputs, estimates, intervals and decisions are final; R1-R3 never recompute, replace "
            "or re-decide them, and the manuscript is not changed until the R1-R3 results exist.",
            "R1, R2 and R3 are POST-CONFIRMATION SENSITIVITY ANALYSES, specified after Stage 3, A and B in answer "
            "to reviewer concerns. None is a second confirmatory test. Their outcomes can qualify the "
            "interpretation of the Stage 3 decomposition or leave it standing; they cannot strengthen the "
            "Stage 3 confirmatory claim.",
            "R1: the residual may depend on the decoder. Every Stage 3 codec output was decoded by FFmpeg's "
            "native decoder, RFC 6716 leaves the decoder's resampling to the implementation, and the control was "
            "fitted to the FFmpeg-decoded SILK chain.",
            "R2: the control reproduces the bitrate-independent linear chain (SILK narrowband at 40 kbit/s). How "
            "much more of the penalty could be attributed to linear spectral loss if the control reproduced the "
            "coherent linear response of Opus at 8 kbit/s itself?",
            "R3: at the same 8 kbit/s, does spending the bits on wideband change WER? A practical "
            "bandwidth-allocation counterfactual, not a factorial causal effect.",
            "R1 and R2 share one ASR run on the confirmation set (RS4a); R3 has its own run on the sweep set "
            "(RS4b). Each analysis has its own gates and outcome; a gate failure stops only that analysis.",
            "Stage 2B, Stage 3 and upgrade modules are imported unchanged; R1-R3 code adds only what the new "
            "conditions, gates and estimands require.",
        ],
        "interpretation_labels": [
            "PASS / FAIL: every pre-ASR gate. All gates of an analysis must PASS before its conditions are "
            "recognised; one FAIL stops that analysis (STOPPED), which is reported with the failed gate and its "
            "measured values. R1-REUSE is a decision gate: its FAIL selects LP_LIBOPUS and stops nothing.",
            "R1 and R2, per recogniser: SUPPORT if the lower 95 % bound of the residual-like quantity (P1, P2) is "
            "above zero and the interval of the change of the residual excludes a reduction of a quarter or "
            "more of the Stage 3 residual; otherwise WEAKEN, qualified as 'reduction shown' (the interval "
            "excludes a smaller reduction) or 'not established'. A missing (NaN) bound never satisfies SUPPORT. "
            "Overall per analysis: SUPPORT if SUPPORT for both recognisers, WEAKEN otherwise.",
            f"The margin, {q} with T*_m the frozen Stage 3 pooled micro OPUS - LP estimate of recogniser m, is "
            "Addition A's GO margin, so A, R1 and R2 judge materiality on one scale.",
            "R3, per recogniser, from the 95 % interval of W = WER(WB8) - WER(NB8): WB_BETTER if the interval "
            "lies below zero, WB_WORSE if it lies above zero, NO_CLEAR_DIFFERENCE otherwise (a NaN bound gives "
            "NO_CLEAR_DIFFERENCE). No combined R3 outcome is formed; both recognisers are reported, and no "
            "difference inside the interval is interpreted.",
            "Implementation: reviewer_design.rule, reviewer_design.combine, reviewer_design.r3_outcome (frozen "
            "with this plan).",
        ],
        "provenance": {
            **inputs,
            "superseded_draft_spec_sha256": SUPERSEDED_DRAFT["spec_sha256"],
            "head_at_freeze": s3.git("rev-parse", "HEAD"),
            "working_tree_status": s3.git("status", "--porcelain").splitlines(),
            "libopus": opus_direct.libopus_version(),
            "environment_rule": "the Stage 3 environment (results_paper/stage3_asr/requirements-lock.txt, "
                                "libopus 1.4, FFmpeg 6.1.1, same GPU type), verified end to end by gate E1 "
                                "before any R1-R3 audio is generated",
        },
        "inputs_read": [
            "Sealed Stage 3 records: specification, confirmation freeze, decision, bootstrap table (anchors), "
            "selections and the confirmation pooled transfer measures.",
            "Sealed upgrade records: specification, code freeze, amendment 01, the A and B decisions, the sweep "
            "selection, B's validation report and rows (SILK8 hashes and payload bitrates) and B's pooled "
            "transfer measures.",
            "Stage 2B: the frozen filter record (design parameters, calibration indices, tolerance hash), the "
            "calibration curves, the original and revised tolerances, the filter-validation selection and its "
            "sealed spec (to exclude its speakers).",
            "The frozen Stage 2B transfer curves of dev-clean, dev-other and the filter-validation set: the "
            "planning probe (1,625 Hz, disclosed) and its diagnosis (r2_planning_diagnosis.json). No tolerance "
            "was chosen from them; every R1 and R2 tolerance is an unchanged Stage 2B value.",
            "LibriSpeech SPEAKERS.TXT and train-clean-100 file names, to draw the signal-validation subset. No "
            "audio or transcript of it was read.",
            "The literature note 01_LITERATURE_NOTE.md; its SHA-256 is recorded.",
            "No audio, no transcript and no ASR output of any set was read to freeze this plan.",
        ],
        "code_sha256_at_design_freeze": code_hashes(),
        "selections": sel,
        "common_pipeline": [
            "Audio: 16 kHz mono float32, length equal to REF. REF, LP, OPUS and SILK exactly as Stage 3 "
            "(paper/stage3_audio.generate_conditions); LP = frozen Stage 2B zero-phase low-pass (taps SHA-256 "
            f"{audio.FROZEN_LP_SHA256[:12]}...), applied by paper/lowpass.apply_zero_phase.",
            "Codec path of OPUS, SILK, NB8 and WB8: direct libopus 1.4 C API (paper/opus_direct.encode; every "
            "control set explicitly and read back), Ogg Opus written by paper/opus_direct (fixed serial, "
            "lookahead as pre-skip, end trim by granule position), decoded by torchaudio.load (FFmpeg 6.1.1 "
            "native decoder) at 48 kHz, resampled to 16 kHz by torchaudio.functional.resample: the steps of "
            "paper/stage3_audio.codec_round_trip. Only R1's *_REFDEC conditions replace the decoder.",
            "No re-alignment, no level normalisation and no clipping of any condition: samples with |x| >= 1 "
            "are passed to the recognisers unchanged and counted, as in Stage 3.",
            "Recognisers exactly as Stage 3 (paper/stage3_asr.py): Whisper large-v3 at revision "
            f"{asr.WHISPER_REVISION[:12]}..., float16, batch {asr.WHISPER_BATCH_SIZE}, greedy, temperature 0 "
            "without fallback, English, transcribe, no timestamps, no prompt; wav2vec2-base-960h (torchaudio "
            "bundle), float32, greedy CTC, no language model. No adaptation.",
            "Scoring exactly as Stage 3: Whisper EnglishTextNormalizer (pinned tokenizer) on references and "
            "hypotheses; jiwer word and character edit counts; an empty or failed hypothesis counts as all "
            "deletions; no utterance is excluded after decoding.",
            "Bootstrap exactly as Stage 3 (paper/stage3_stats: PairedSet, bootstrap_weights, "
            f"percentile_interval), {N_BOOT:,} replicates, speakers resampled with replacement within subset "
            "strata, all conditions and both recognisers of an utterance kept together, 95 % percentile "
            f"intervals. Confirmation set: seed {CONFIRMATION_SEED} (Stage 3's and A's seed on the same speakers, "
            f"so replicate k resamples the same speakers). Sweep set: seed {SWEEP_SEED} (B's seed on the same "
            "speakers). Every derived quantity is recomputed within each replicate from that replicate's corpus "
            "WERs; a ratio is NaN in a replicate whose denominator is <= 0 and the valid replicates are counted "
            "(the Stage 3 convention).",
            "Primary scope: pooled (stratified); per-subset scopes are secondary. Primary estimator: corpus "
            "(micro) WER difference from total edit counts, in percentage points (pp). No multiplicity "
            "correction across R1-R3, recognisers or subsets; only the named rule quantities enter an outcome.",
        ],
        "asr_runs": [
            f"RS4a, confirmation set ({conf_n:,} utterances), both recognisers, once: REF, LP, OPUS and SILK, plus "
            "OPUS_REFDEC, SILK_REFDEC and (only if R1-REUSE failed) LP_LIBOPUS for R1, and SURR8 for R2, for each "
            "analysis whose gates PASSED (for R1, unless the identity check ended it).",
            f"RS4b, sweep set ({sweep_ref['n_utterances']:,} utterances), both recognisers, once: NB8 and WB8, if "
            "R3's gates PASSED.",
            "Determinism: every condition is regenerated in its run; its waveform_sha256 (and ogg_sha256 for "
            "coded conditions) must equal the sealed Stage 3 confirmation manifest (REF, LP, OPUS, SILK), B's "
            "sealed validation rows (NB8, as B's SILK8) or the sealed RS3 validation rows (every new condition). "
            "A mismatch stops the run before that condition is recognised, and is reported.",
            "Same-run anchors: every contrast uses conditions recognised in the same run.",
            "Reproduction checks (not gates): per recogniser, the number of utterances whose raw hypothesis "
            "differs from the frozen Stage 3 asr_outputs.csv (REF, LP, OPUS, SILK in RS4a) and from B's frozen "
            "SILK8 hypotheses (NB8 in RS4b). Differences are reported; analyses always use same-run conditions.",
        ],
        "environment_gates": {
            "E1": "gate: the Stage 3 six-condition pipeline is re-run on the Stage 3 calibration set; every "
                  "waveform_sha256 and ogg_sha256 and every raw hypothesis of both recognisers must equal the "
                  "sealed Stage 3 calibration outputs.",
            "E2": "sanity, no comparison: on the Stage 3 calibration set, OPUS_REFDEC, SILK_REFDEC, NB8, WB8 and "
                  "(after their fits) SURR8 and, if built, LP_LIBOPUS are generated and recognised. Checked: "
                  "decoding, lengths, packet configurations, determinism (the first two utterances regenerated "
                  "and re-recognised) and throughput. No WER is compared between conditions.",
            "on_failure": "E1 FAIL stops R1-R3 before any audio of the Stage 2B calibration, signal-validation, "
                          "confirmation or sweep set is generated. An E2 failure is reported and stops the "
                          "affected analysis.",
        },
        "anchors": anchors,
        "confirmation_transfer_frozen": transfer,
        "sweep_frozen": sweep_ref,
        "R1": {
            "title": "Decoder sensitivity with a decoder-matched control",
            "label": "POST-CONFIRMATION SENSITIVITY ANALYSIS - NOT A SECOND CONFIRMATORY TEST",
            "question": "Does the codec-specific residual persist when the identical Opus packets are decoded by "
                        "the libopus reference decoder and the control is matched to that decoder?",
            "data_and_conditions": {
                "OPUS, SILK": "the Stage 3 OPUS (8 kbit/s, forced NB, signal=auto) and SILK (40 kbit/s, forced NB, "
                              "signal=voice; B's SILK40) conditions, regenerated; Ogg bytes and FFmpeg-native "
                              "waveforms bit-identical to Stage 3 (R1-G1)",
                "OPUS_REFDEC, SILK_REFDEC": "the same OPUS and SILK Ogg bytes decoded by the libopus reference "
                                            "decoder",
                "LP_DEC": "the decoder-matched control: the frozen LP if R1-REUSE passes, otherwise LP_LIBOPUS "
                          "(below); decided once, at RS1",
                "LP": "the frozen control, recognised in the same run (the Stage 3 residual from this run)",
            },
            "reference_decoder": [
                "libopus 1.4 through its C API (ctypes), the shared object that encodes (opus_direct.libopus_path).",
                "Per utterance: OpusHead parsed (opus_direct.read_opus_head); one decoder "
                f"(opus_decoder_create({REFERENCE_DECODER_RATE}, 1)); the audio packets in stream order, each "
                f"decoded by opus_decode_float(..., frame_size={REFERENCE_DECODER_MAX_FRAME}, decode_fec=0).",
                "RFC 7845: the first pre-skip samples are discarded and the output is trimmed to (final granule "
                "position - pre-skip) samples; the OpusHead output gain is 0 in every file (checked).",
                "Float32 output at 48 kHz, then torchaudio.functional.resample(48 000 -> 16 000) with the "
                "parameters of stage3_audio.codec_round_trip.",
                "libopus 1.4 has no decoder-side neural processing (LACE, NoLACE and deep PLC arrived in libopus "
                "1.5 and are opt-in); nothing else is set on the decoder.",
                "Held identical: packets, container, pre-skip and end trimming, 48 kHz output, the 48 -> 16 kHz "
                "resampler, float32 samples without dither, no clipping, no re-alignment.",
            ],
            "decoder_matched_control": {
                "R1-C1 (RS1, gate)": "On the 40 Stage 2B calibration utterances, the regenerated FFmpeg-decoded "
                                     "SILK40 h1_rel_db equals the frozen Stage 2B reference curve "
                                     f"({STAGE2B_CALIBRATION_CURVES}, reference_h1_rel_db_40k), and the measured "
                                     "LP h1_rel_db equals the frozen lp_measured_h1_rel_db, each within "
                                     f"{REPRODUCTION_TOLERANCE_DB} dB at every frequency up to "
                                     f"{REPRODUCTION_UP_TO_HZ:g} Hz. FAIL: R1 STOPPED.",
                "Measurement": "On the same utterances, the libopus-decoded SILK40 h1_rel_db (SILK40_LIB) is "
                               "measured with the unchanged Stage 2B TransferAccumulator: the measurement that "
                               "defined LP, with only the decoder changed.",
                "R1-REUSE (RS1, control-reuse gate)": "Not a statistical equivalence test: a pre-specified rule that "
                                              "decides whether the frozen LP is reused as the control for the "
                                              "reference-decoder chain. LP is reused if all hold on the "
                                              "calibration set: (a) |coherent bandwidth(LP) - coherent "
                                              "bandwidth(SILK40_LIB)| <= "
                                              f"{reuse['coherent_bandwidth_max_hz']} Hz (g4); (b) |coherent "
                                              "4-8 kHz power(LP) - coherent 4-8 kHz power(SILK40_LIB)| <= "
                                              f"{reuse['coherent_hf_power_max_db']} dB (g5); (c) the RMS "
                                              "difference of h1_rel_db (LP - SILK40_LIB) over "
                                              f"[{R1_EQ_BAND_HZ[0]:g}, {R1_EQ_BAND_HZ[1]:g}] Hz, RMS_LIB, is <= "
                                              f"{reuse['rms_max_db']} dB and the maximum absolute difference "
                                              f"over [{R1_EQ_ABS_BAND_HZ[0]:g}, {R1_EQ_ABS_BAND_HZ[1]:g}] Hz is <= "
                                              f"{reuse['abs_max_db']} dB (g6); (d) RMS_LIB <= RMS_FF + "
                                              f"{reuse['rms_margin_over_ffmpeg_db']} dB, where RMS_FF is the "
                                              "same RMS against the FFmpeg-decoded SILK40 curve: the decoder "
                                              "change must not worsen LP's fit in the transition band by more "
                                              "than the Stage 2B passband-deviation tolerance ("
                                              f"{reuse['rms_margin_over_ffmpeg_db']} dB), inherited from "
                                              "Stage 2B and fixed before any libopus-decoder result is observed. "
                                              "PASS: LP_DEC = LP. "
                                              "FAIL: LP_DEC = LP_LIBOPUS. Decided once; never revisited after "
                                              "validation or ASR.",
                "LP_LIBOPUS (RS1, only if R1-REUSE fails)": "built by the unchanged Stage 2B procedure "
                                                         "(build_target, design, constrain; "
                                                         f"{design['num_taps']:,} taps, "
                                                         f"{design['correction_iterations']} measurement-domain "
                                                         "corrections) with SILK40_LIB as the reference, on the "
                                                         "same calibration utterances; taps and their SHA-256 "
                                                         f"frozen in {LP_LIBOPUS_FILTER} before the code freeze "
                                                         "and before any validation or confirmation audio is "
                                                         "filtered.",
                "R1-V (RS3, gate, signal-validation subset)": "LP_DEC is validated on the new signal-only subset "
                                                              "with the revised Stage 2B validation, unchanged in "
                                                              "code and tolerances (gates 1-4 and 6 of "
                                                              "run_lowpass_validation.evaluate_gates, gate 5 of "
                                                              "run_lowpass_confirmation.revised_gate5; revised "
                                                              f"tolerance set as sealed in {FV_SPEC}), with the "
                                                              "SILK-NB linear reference and Opus 8 kbit/s decoded "
                                                              "by the reference decoder. The same validation is "
                                                              "required whether LP_DEC is LP or LP_LIBOPUS. FAIL: "
                                                              "R1 STOPPED.",
            },
            "pre_asr_gates": {
                "R1-G1": "For all 2,174 confirmation utterances, the regenerated OPUS and SILK ogg_sha256 and "
                         "FFmpeg-native waveform_sha256 equal the sealed Stage 3 confirmation manifest "
                         "(raw/confirmation/audio_manifest.csv; outputs_sha256 "
                         f"{inputs['stage3_confirmation_outputs_sha256'][:12]}...).",
                "R1-G2": "The reference decoder reports 'libopus 1.4' (opus_get_version_string) and is the shared "
                         "object that encodes; every OpusHead has output gain 0 and a pre-skip of 3 x the encoder "
                         f"lookahead; every packet decodes without error to {SAMPLES_PER_PACKET_48K} samples.",
                "R1-G3": "After pre-skip removal and end trimming, every reference-decoder output has exactly the "
                         "48 kHz length of the FFmpeg-native output; after resampling, its length equals REF and "
                         "every sample is finite.",
                "Identity check (not a gate)": "if every OPUS_REFDEC and SILK_REFDEC waveform is bit-identical to "
                                               "OPUS and SILK, R1 ends at RS3 without ASR: SUPPORT by identity "
                                               "for both recognisers (the Stage 3 estimates hold for the "
                                               "reference decoder).",
                "on_failure": "R1 is STOPPED before recognition (stopping rules)",
                "descriptive, sealed before ASR": "per utterance, the lag of the reference-decoder output "
                                                  "against the FFmpeg-native output (frozen "
                                                  "common.align_waveforms), the decoder-difference SNR 10 "
                                                  "log10(sum y_ff^2 / sum (y_ref - y_ff)^2) at 16 kHz, the "
                                                  "maximum absolute difference and the share of bit-identical "
                                                  "outputs; RS1's SILK40_LIB and SILK40 curves and every R1-REUSE "
                                                  "quantity; the frozen Stage 3 descriptor set for OPUS, "
                                                  "OPUS_REFDEC, SILK and SILK_REFDEC. No descriptor enters a rule.",
            },
            "estimands": {
                "primary": "P1_m = WER_micro(OPUS_REFDEC) - WER_micro(LP_DEC), pooled, per recogniser m: the "
                           "codec-specific residual when both the codec output and the control are matched to "
                           "the reference decoder",
                "rule quantity": "D1_m = P1_m - (WER_micro(OPUS) - WER_micro(LP)), from the same run: the change "
                                 "of the residual when decoder and control are both changed to the reference "
                                 "decoder (D1_m = WER_micro(OPUS_REFDEC) - WER_micro(OPUS) when LP_DEC = LP). The "
                                 "reduction of the residual is -D1_m.",
                "secondary": [
                    "SILK_REFDEC - LP_DEC: the decoder-matched high-rate residual (the counterpart of Stage 3's "
                    "SILK - LP, near zero there)",
                    "OPUS_REFDEC - LP: the reference-decoder residual against the unmatched control",
                    "OPUS_REFDEC - OPUS and SILK_REFDEC - SILK: the decoder effects on the codec outputs alone",
                    "LP_DEC - LP (when LP_LIBOPUS is used) and OPUS_REFDEC - SILK_REFDEC",
                    "same-run OPUS - LP and SILK - LP (the Stage 3 residuals from this run)",
                    "macro WER, CER and substitution/deletion/insertion composition of P1 and D1",
                    "per-subset scopes (test-clean, test-other)",
                ],
                "descriptive": "per recogniser, the number of utterances whose raw hypothesis differs between "
                               "OPUS and OPUS_REFDEC, and between SILK and SILK_REFDEC",
            },
            "analytic_expectations": [
                "RFC 6716 section 4.2.9 leaves the resampler non-normative but fixes its delay (Table 54). FFmpeg "
                "6.1.1 upsamples SILK output with libswresample (filter_size 16); libopus uses its own SILK "
                "resampler. Expected: waveform differences near the 4 kHz band edge and in the 4-5 kHz image, the "
                "outputs aligned to within about a sample, and a SILK40 linear response that differs mainly "
                "near the band edge. Whether LP passes R1-REUSE is not predicted.",
                f"SILK carries image energy of comparable power (pooled total 4-8 kHz power {sk['total_hf_power_db']:+.1f} "
                f"dB against REF, OPUS {op['total_hf_power_db']:+.1f} dB) but had no pooled residual in Stage 3, so "
                "SILK_REFDEC - LP_DEC shows whether the decoder-matched control is also residual-free at 40 kbit/s.",
                "These expectations come from the specifications and the source code; they are not tests.",
            ],
            "rules": {
                "definitions": "For recogniser m: P1_m [P1_lo, P1_hi] and D1_m [D1_lo, D1_hi], pooled micro, 95 % "
                               "percentile speaker-bootstrap intervals, same run; T*_m is the frozen Stage 3 pooled "
                               "micro OPUS - LP estimate.",
                "SUPPORT_m": f"P1_lo > 0 AND D1_lo > -{q}: a residual remains with the reference decoder and a "
                             "decoder-matched control, and the interval excludes the change removing a quarter or "
                             "more of the Stage 3 residual.",
                "WEAKEN_m": f"neither; qualified 'reduction shown' if D1_hi < -{q}, 'not established' otherwise.",
                "overall": "SUPPORT if SUPPORT for both recognisers; WEAKEN otherwise. Per-recogniser outcomes are "
                           "always reported.",
                "not in the rules": "the SILK contrasts, the unmatched-control contrast, per-subset scopes, "
                                    "secondary estimators and every descriptor (all reported)",
                "implementation": "reviewer_design.rule('R1', {'P1': ..., 'D1': ...}, T*_m), reviewer_design.combine",
            },
            "manuscript_consequences": {
                "SUPPORT_m": "may state, as a post-confirmation sensitivity analysis, that with the libopus "
                             "reference decoder and a control matched to it a residual remained for recogniser m "
                             "(values given, and which control was used); the 'Implementations' limitation is "
                             "narrowed to the versions tested, and 'decoding with the reference decoder' leaves "
                             "the future-work list",
                "WEAKEN_m (reduction shown)": "must state that for recogniser m at least a quarter of the residual "
                                              "depended on the decoder chain (P1 and D1 given); the residual is "
                                              "described as defined for FFmpeg's native decoder, and the in-band "
                                              "coding-distortion interpretation is qualified for m; the Stage 3 "
                                              "estimates stand unchanged",
                "WEAKEN_m (not established)": "reports P1 and D1 and states that the residual was not shown to be "
                                              "independent of the decoder chain for recogniser m; the "
                                              "'Implementations' limitation stays, with the numbers added",
                "STOPPED": "reports the failed gate and its values; the 'Implementations' limitation and the "
                           "future-work item stay unchanged",
            },
        },
        "R2": {
            "title": "8-kbit/s effective coherent-linear surrogate",
            "label": "POST-CONFIRMATION SENSITIVITY ANALYSIS - AN ALTERNATIVE ATTRIBUTION UNDER A MORE INCLUSIVE "
                     "SAME-FREQUENCY LINEAR-LOSS DEFINITION, NOT A BANDWIDTH CONTROL; THE PRIMARY CONTROL, "
                     "COMPONENTS AND SHARE ARE UNCHANGED",
            "question": "If the control is replaced by a zero-phase surrogate of the coherent linear response of "
                        "Opus at 8 kbit/s itself (a more inclusive same-frequency linear-loss definition), how "
                        "much of the Opus penalty is attributed to linear loss, and does a residual remain "
                        "beyond the surrogate?",
            "planning_probe_and_diagnosis": [
                "Disclosure (" + diagnosis["probe"]["date"] + "): " + diagnosis["probe"]["statement"],
                *diagnosis["findings"],
                *diagnosis["consequences"],
                f"Record: {R2_DIAGNOSIS} (SHA-256 {diagnosis['diagnosis_sha256'][:12]}...), computed from frozen "
                "curves only by reviewer_design.py diagnose-r2.",
            ],
            "data_and_conditions": {
                "SURR8": "the confirmation REF waveform filtered by the frozen surrogate (lowpass.apply_zero_phase); "
                         "no codec",
                "REF, LP, OPUS": "as Stage 3, recognised in the same run (RS4a)",
            },
            "surrogate_design": [
                "Measured response: the pooled same-frequency coherent transfer function |H1(f)| = |Sxy| / Sxx of "
                "OPUS (the Stage 3 OPUS settings; direct libopus 1.4; frozen decode path) against REF on the 40 "
                "Stage 2B calibration utterances, after the frozen alignment (common.align_waveforms), normalised "
                f"to its mean over {design['level_band_hz'][0]:g}-{design['level_band_hz'][1]:g} Hz: "
                "TransferAccumulator.results()['h1_rel_db'] of paper/run_lowpass_validation.py, the measurement "
                "that defined the primary control with the SILK-NB reference at 40 kbit/s replaced by OPUS.",
                "Target: run_lowpass_validation.build_target, unchanged: 0 dB up to the first frequency above which "
                f"the response stays below -{design['passband_deviation_db']} dB (the 'edge', a construction "
                f"parameter: {dcal:g} Hz on the frozen calibration curve), then the running minimum of the response "
                f"capped at 0 dB, floored at {design['stopband_floor_db']:g} dB.",
                f"FIR: run_lowpass_validation.design and constrain, unchanged: {design['num_taps']:,} taps (type I), "
                f"Kaiser beta {design['kaiser_beta']:g}, frequency sampling on a {design['design_grid']:,}-point grid, "
                f"gain at DC equal to the target; {design['correction_iterations']} measurement-domain corrections "
                f"above the edge where the target is above {design['correction_floor_db']:g} dB.",
                f"Freeze: taps, SHA-256, target, calibration curve and correction iterations in {SURR8_FILTER} at "
                "RS1, before the code freeze and before any signal-validation or confirmation audio is filtered.",
                "Application: lowpass.apply_zero_phase: zero phase, length preserved, no level normalisation.",
                "Not reproduced: OPUS's phase, lag, 4-5 kHz image and uncorrelated (noise-like) output; its in-band "
                f"coherent level (h1_level_db {op['h1_level_db']:+.2f} dB on the confirmation set) and its emphasis "
                f"below the level band (h1_rel_db {dshape[250.0]['opus8_h1_rel_db']:+.1f} dB at 0.25 kHz on the "
                "calibration curve). The surrogate is normalised to 0 dB in the level band, as LP is; broadband "
                "level was examined in A.",
                "Definition: above the edge the target is the greatest non-increasing curve at or below OPUS's "
                "coherent response (capped at 0 dB), so SURR8 removes at every frequency above the edge at least "
                "what OPUS's coherent response removes on the calibration data, and no more than monotonicity "
                "requires. B2 is therefore the penalty attributed to linear loss under this more inclusive "
                "same-frequency definition. With the primary control, s1 and s2 form a sensitivity range across "
                "two pre-specified linear definitions; they are not mathematical bounds on a true share.",
                "The frozen LP is neither changed nor re-fitted and remains the primary control.",
            ],
            "pre_asr_gates": {
                "R2-C1 (RS1, gate)": "The regenerated OPUS h1_rel_db on the 40 Stage 2B calibration utterances "
                                     f"equals the frozen Stage 2B dev-clean opus_8k_nb curve ({STAGE2B_CURVES}) "
                                     f"within {REPRODUCTION_TOLERANCE_DB} dB at every frequency up to "
                                     f"{REPRODUCTION_UP_TO_HZ:g} Hz, so the fitted response and its {dcal:g} Hz edge "
                                     "are the ones diagnosed above.",
                "validation set (RS3)": "the new signal-only subset: OPUS encoded and decoded by the frozen path, "
                                        "SURR8 applied to REF; no ASR, no transcripts. Tolerances: the unchanged "
                                        "Stage 2B values (TOLERANCES, SHA-256 "
                                        f"{inputs['stage2b_tolerances_sha256'][:12]}...), with the SILK-NB "
                                        "reference replaced by OPUS.",
                "R2-V1": "zero effective delay: symmetric odd-length taps with (L - 1) / 2 samples removed, and an "
                         f"absolute alignment lag against REF of at most {tol['V1_max_abs_lag_samples']} samples (none) "
                         "for every utterance (g1).",
                "R2-V2": f"linearity: pooled coherence of SURR8 with REF >= {tol['V2_min_coherence']} at every "
                         f"frequency up to {tol['V2_up_to_hz']:g} Hz (g3).",
                "R2-V3": f"shape: over [edge, {tol['V3_rms_band_upper_hz']:g}] Hz, the RMS difference between SURR8's "
                         "measured h1_rel_db and the target that build_target makes from OPUS's h1_rel_db on the "
                         f"validation subset is <= {tol['V3_rms_max_db']} dB, and the maximum absolute difference over "
                         f"[edge, {tol['V3_abs_band_upper_hz']:g}] Hz is <= {tol['V3_abs_max_db']} dB; edge = the "
                         "calibration edge (g6, whose primary band [3000, 4200] Hz also started at its edge).",
                "R2-V4": f"coherent bandwidth (last frequency with h1_rel_db >= {tol['V4_threshold_db']:g} dB): "
                         f"|SURR8 - OPUS| <= {tol['V4_max_hz']} Hz (g4).",
                "R2-V5": f"coherent 4-8 kHz power: |SURR8 - OPUS| <= {tol['V5_max_db']} dB (g5): the droop across the "
                         "band edge, excluded from the primary definition, is part of the surrogate.",
                "R2-V6": f"stopband: SURR8 h1_rel_db <= {tol['V6_max_db']:g} dB at every frequency from "
                         f"{tol['V6_from_hz']:g} Hz (g6).",
                "on_failure": "R2 is STOPPED before recognition (C1 at RS1, or any of V1-V6 at RS3); no other "
                              "target, FIR length, correction count, level band, deviation or tolerance is tried "
                              "under the R2 label",
                "descriptive, sealed before ASR": "on the validation subset: the edge that build_target gives for "
                                                  "OPUS, LSD 0-3 kHz against REF (median, p95), power-based "
                                                  "retained bandwidth, total 4-8 kHz power, and the SURR8 - LP "
                                                  "response difference at "
                                                  + ", ".join(f"{x / 1000:g}" for x in R2_RESPONSE_REPORT_HZ)
                                                  + " kHz; the calibration edge and correction errors; the "
                                                  "frozen Stage 3 descriptor set for SURR8 on the confirmation "
                                                  "audio",
            },
            "tolerances": tolerances,
            "design_parameters": design,
            "estimands": {
                "primary": "P2_m = WER_micro(OPUS) - WER_micro(SURR8), pooled: the residual beyond the "
                           "coherent-linear surrogate",
                "rule quantity": "Delta2_m = WER_micro(SURR8) - WER_micro(LP): the part of the same-run residual "
                                 "OPUS - LP that the surrogate attributes to linear spectral loss "
                                 "(P2_m = (OPUS - LP)_m - Delta2_m)",
                "surrogate component": "B2_m = WER_micro(SURR8) - WER_micro(REF)",
                "attribution shares": "s2_m = B2_m / (WER_micro(OPUS) - WER_micro(REF)), the SURR8-control share, and, "
                                      "from the same run, the primary share s1_m = (WER_micro(LP) - WER_micro(REF)) "
                                      "/ (WER_micro(OPUS) - WER_micro(REF)); each with its 95 % percentile interval "
                                      "(Stage 3 ratio convention)",
                "sensitivity range": "per recogniser, [min(s1, s2), max(s1, s2)] for the point estimates, and from "
                                     "the lower 95 % limit of the smaller to the upper limit of the larger; a range "
                                     "across two definitions, not a confidence interval",
                "secondary": [
                    "same-run LP - REF, OPUS - LP and OPUS - REF (the Stage 3 decomposition from this run)",
                    "macro WER, CER and substitution/deletion/insertion composition of P2, B2 and Delta2",
                    "per-subset scopes (test-clean, test-other)",
                ],
                "descriptive": "per recogniser, the number of utterances whose raw hypothesis differs between LP "
                               "and SURR8",
            },
            "analytic_expectations": [
                "From the frozen calibration curve (diagnosis), the surrogate lies "
                f"{-dshape[3000.0]['target_minus_lp_db']:.1f} dB below LP at 3 kHz and "
                f"{-dshape[4000.0]['target_minus_lp_db']:.1f} dB at 4 kHz. Expected: Delta2 >= 0, B2 >= LP - REF and "
                "P2 <= OPUS - LP; the size of the shift is what R2 measures.",
                "The Stage 3 bandwidth component was larger for wav2vec2-base-960h than for Whisper large-v3 "
                f"(+{v['B_star']['estimate']:.2f} against +{w['B_star']['estimate']:.2f} pp), so a larger Delta2 is "
                "expected for wav2vec2.",
                "These expectations come from frozen, published curves; they are not tests.",
            ],
            "rules": {
                "definitions": "For recogniser m: P2_m [P2_lo, P2_hi] and Delta2_m [Delta2_lo, Delta2_hi], pooled "
                               "micro, 95 % percentile intervals, same run; T*_m as in R1.",
                "SUPPORT_m": f"P2_lo > 0 AND Delta2_hi < {q}: a residual remains beyond the surrogate, and the "
                             "interval excludes the surrogate absorbing a quarter or more of the Stage 3 residual.",
                "WEAKEN_m": f"neither; qualified 'reduction shown' if Delta2_lo > {q}, 'not established' otherwise.",
                "overall": "SUPPORT if SUPPORT for both recognisers; WEAKEN otherwise. Per-recogniser outcomes are "
                           "always reported.",
                "not in the rules": "B2, the shares and their range, per-subset scopes, secondary estimators and "
                                    "every descriptor (all reported in every outcome)",
                "implementation": "reviewer_design.rule('R2', {'P2': ..., 'Delta2': ...}, T*_m), "
                                  "reviewer_design.combine",
            },
            "manuscript_consequences": {
                "SUPPORT_m": "may state that for recogniser m a residual remained beyond a surrogate of the coherent "
                             "linear response of Opus at 8 kbit/s (values given); the bandwidth share is reported "
                             "beside the unchanged primary estimate as the sensitivity range s1-s2 across two "
                             "pre-specified linear definitions (primary control and SURR8 control), not as "
                             "bounds on a true share",
                "WEAKEN_m (reduction shown)": "must state that for recogniser m at least a quarter of the residual "
                                              "is reproduced by the coherent-linear surrogate; reports B2, P2 and "
                                              "s2 beside the primary values; qualifies the in-band "
                                              "coding-distortion interpretation (part of the residual is linear "
                                              "loss of coherent in-band content); and gives the share as a range "
                                              "wherever it is stated, the abstract included",
                "WEAKEN_m (not established)": "reports B2, P2, Delta2 and s2 and states that a residual beyond the "
                                              "surrogate was not established for recogniser m; the share is "
                                              "reported as a range in the results",
                "STOPPED": "reports the failed criterion and its values; the primary control and share are "
                           "reported alone, with the statement that the control reproduces only the "
                           "bitrate-independent chain",
            },
        },
        "R3": {
            "title": "Forced-wideband 8 kbit/s practical counterfactual",
            "label": "PRACTICAL BANDWIDTH-ALLOCATION COUNTERFACTUAL ON A FRESH-UTTERANCE, NOT FRESH-SPEAKER, "
                     "HOLDOUT - NOT A FACTORIAL CAUSAL EFFECT",
            "question": "On unused utterances of the test speakers, with every other encoder setting and the decode "
                        "path held fixed, does forcing wideband instead of narrowband at a nominal 8 kbit/s change "
                        "WER?",
            "data_and_conditions": {
                "set": f"the Addition-B sweep selection ({sel['sweep']['size']}); a fresh-utterance, not "
                       "fresh-speaker, holdout; decoded a second time (B, R3)",
                "NB8": "the Stage 3 OPUS settings (8 kbit/s, forced NB, signal=auto); on these utterances its Ogg "
                       "bytes equal B's SILK8 (B's bridge share: "
                       f"{sweep_ref['bridge_share_silk8_identical_to_stage3_opus_settings']:.3f}), checked by R3-G0",
                "WB8": "the same settings with the bandwidth forced to WB, through the same direct-libopus path and "
                       "the same decode path",
                "encoder settings": f"WB8 {json.dumps(settings[WB8])}; NB8 identical except bandwidth NB",
                "held fixed": "target bitrate 8000 bit/s, unconstrained VBR, complexity 10, 20 ms frames, "
                              "application audio, signal auto, maximum bandwidth FB, no FEC, no DTX, 0 % expected "
                              "loss, LSB depth 24, 16 kHz encoder input, the decoder and the resampler",
                "not factorial": "forcing WB also changes SILK's internal sampling rate (16 instead of 8 kHz), its "
                                 "LPC order (16 instead of 10; RFC 6716) and the allocation of about 7.6 kbit/s of "
                                 "payload over twice the band; R3 compares two practical configurations at one "
                                 "rate, estimates no interaction and does not enter the decomposition (REF and LP "
                                 "are not recognised in R3)",
            },
            "encoder_settings_record": {NB8: settings[NB8], WB8: settings[WB8]},
            "pre_asr_gates": {
                "set (RS3)": "the sweep selection; encode and decode only, no ASR",
                "R3-G0": "NB8 reproduces B's SILK8: for all 1,665 utterances its ogg_sha256 and waveform_sha256 "
                         f"equal B's sealed validation rows ({B_VALIDATION_ROWS}).",
                "R3-G1": "settings: WB8 differs from NB8 only in bandwidth (checked at this freeze and again at RS3); "
                         "for every encode, every queried control equals its requested value (read-back).",
                "R3-G2": f"packets: every packet of every WB8 utterance has TOC configuration {WB_CONFIGURATION} "
                         "(SILK-only, WB, 20 ms), is mono and has frame-count code 0, and libopus reports "
                         "bandwidth WB: 100 %.",
                "R3-G3": "rate: the median over utterances of the payload bitrate (8 x sum of unpadded packet bytes "
                         f"/ duration) of WB8 is within +/-{BITRATE_TOLERANCE:.0%} of 8 kbit/s (B's V2 tolerance) and "
                         f"within +/-{RATE_MATCH_TOLERANCE:.0%} of NB8's median on the same utterances (B, frozen: "
                         f"{sweep_ref['silk8_median_payload_kbps']:.2f} kbit/s).",
                "R3-G4": "decode path: decoded at 48 kHz by the frozen path; after resampling, length equals REF and "
                         "every sample is finite.",
                "R3-G5": f"band realised: pooled total 4-8 kHz power of WB8 against REF >= {HF_REALISED_MIN_DB:g} dB "
                         f"(B, frozen, same utterances: SILK8 {b_s8['total_hf_power_db']:+.1f} dB, LP "
                         f"{b_lp['total_hf_power_db']:+.1f} dB).",
                "on_failure": "R3 is STOPPED before recognition; no other bitrate, bandwidth, signal hint or setting "
                              "is tried under the R3 label",
                "descriptive, sealed before ASR": "packet-configuration counts, payload and container bitrates, "
                                                  "RMS change and lag against REF, samples with |x| >= 1, and the "
                                                  "frozen Stage 3 descriptor set for NB8 and WB8 (in-band "
                                                  "coherence 0-3.5 kHz and LSD 0-3 kHz against REF among them; "
                                                  f"B's frozen SILK8 mean coherence {b_s8['mean_coherence_0_3500']:.3f})",
            },
            "estimands": {
                "primary": "W_m = WER_micro(WB8) - WER_micro(NB8), pooled, per recogniser m, with its 95 % "
                           f"percentile speaker-bootstrap interval (seed {SWEEP_SEED}, B's speakers and strata)",
                "secondary": [
                    "macro WER, CER and substitution/deletion/insertion composition of W",
                    "per-subset W (test-clean, test-other)",
                ],
                "descriptive": "per recogniser, the number of utterances whose raw hypothesis differs between NB8 "
                               "and WB8, and between NB8 and B's frozen SILK8 hypotheses (reproduction check)",
            },
            "outcomes": {
                "WB_BETTER_m": "W_hi < 0: forcing wideband lowered WER",
                "WB_WORSE_m": "W_lo > 0: forcing wideband raised WER",
                "NO_CLEAR_DIFFERENCE_m": "otherwise, including a missing (NaN) bound",
                "reporting": "per recogniser; no combined outcome; no difference inside the interval is "
                             "interpreted",
                "implementation": "reviewer_design.r3_outcome(W_lo, W_hi)",
            },
            "analytic_expectations": [
                "libopus 1.4: OPUS_SET_BANDWIDTH overrides the automatic choice, and a 16 kHz input caps the band at "
                "WB (opus_encoder.c L1508-1529; audit record libopus-1.4), so SILK-only WB packets are expected. "
                "Skoglund and Valin (2020) coded wideband SILK at 6 kb/s, so 8 kbit/s wideband is within the "
                "encoder's range.",
                "Expected: restored 4-8 kHz power and more in-band distortion than NB8. The sign of W is not "
                "predicted; wav2vec2-base-960h was the more bandwidth-sensitive recogniser in Stage 3.",
                "These expectations come from the source code and the literature note; they are not tests.",
            ],
            "manuscript_consequences": {
                "WB_BETTER_m": "may state that on unused utterances of the test speakers, forcing wideband at the "
                               "same nominal 8 kbit/s lowered WER for recogniser m (W given), as a practical "
                               "allocation result; must say that coding changed with the band, so this is not an "
                               "interaction estimate and does not change the decomposition",
                "WB_WORSE_m": "may state that forcing wideband at the same nominal 8 kbit/s raised WER for "
                              "recogniser m (W given), as a practical allocation result, with the same "
                              "qualification",
                "NO_CLEAR_DIFFERENCE_m": "reports W and its interval and states that no difference was "
                                         "established for recogniser m; no practical recommendation is drawn",
                "in every outcome": "the 'Limitations' text changes from 'forced to wideband at 8 kbit/s, which was "
                                    "not run' to report R3 as a practical counterfactual; the statement that an "
                                    "interaction estimate needs a factorial design stays",
                "STOPPED": "reports the failed gate and its values; the limitation stays as written",
            },
        },
        "stopping_rules": [
            "No R1-R3 audio is encoded, decoded or filtered, no control or surrogate is fitted, and no audio of the "
            "signal-validation subset is read before this plan is committed (RS0).",
            "E1 FAIL: R1-R3 stop before any audio of the Stage 2B calibration, signal-validation, confirmation or "
            "sweep set is generated; nothing proceeds until an approved, sealed amendment exists.",
            "A gate FAIL of R1 (C1, V, G1-G3), R2 (C1, V1-V6) or R3 (G0-G5): that analysis is STOPPED before "
            "recognition; its conditions are not recognised; the failed gate and every measured value are sealed "
            "and reported. No redesign, re-fit, other target, FIR length, tolerance, decoder, bitrate or setting "
            "is tried under the same label; a successor analysis needs an approved, sealed amendment and is "
            "reported as post hoc. The other analyses continue.",
            "R1-REUSE is decided once, at RS1: its outcome selects LP or LP_LIBOPUS and is never revisited after R1-V, "
            "the identity check or ASR.",
            "R1 identity: if every OPUS_REFDEC and SILK_REFDEC waveform is bit-identical to OPUS and SILK, R1 ends at "
            "RS3 without ASR (SUPPORT by identity).",
            "RS4a is not performed if R1 ended by identity or was STOPPED and R2 was STOPPED; RS4b is not performed "
            "if R3 was STOPPED.",
            "Each ASR run is performed once. A resumable progress file is allowed as in Stage 3; every interruption "
            "and resume is logged; nothing is re-decoded selectively or rerun from scratch; no estimate is computed "
            "before both runs that will be performed are complete.",
            "The analysis (RS5) uses only the frozen code and rules; any further analysis is labelled exploratory "
            "and cannot change an outcome.",
            "Order independence: R1-R3 are frozen together; no result of one changes another's plan, and all are "
            "analysed together after RS4.",
            "Reporting: every outcome, STOPPED, WEAKEN and NO_CLEAR_DIFFERENCE included, is reported in the "
            "supplement, with a sentence in the main text wherever the affected claim is made.",
        ],
        "run_order": [
            "RS0  Design freeze (this plan): signal-validation selection, R2 planning diagnosis and reviewer_spec.json "
            "sealed, this file rendered; binding once committed.",
            "RS1  Implementation and technical calibration: runner code and tests; gate E1, then E2, on the Stage 3 "
            "calibration set; on the Stage 2B calibration set, R1-C1, the SILK40_LIB measurement, R1-REUSE and (if "
            "needed) LP_LIBOPUS, then R2-C1 and the SURR8 fit; every filter frozen with its SHA-256.",
            "RS2  Code freeze: every R1-R3, upgrade, Stage 2B and Stage 3 code file hashed and sealed with this "
            "plan's hash, the R1-REUSE decision and the filter hashes. Files present at the design freeze and changed "
            "since are listed and need an amendment note; files added at RS1 are listed as added.",
            "RS3  Pre-ASR validation, no ASR: R1-G1 to G3 and the identity check on the confirmation set; R1-V and "
            "R2-V1 to V6 on the signal-validation subset; R3-G0 to G5 on the sweep set. One sealed validation "
            "report holds every gate result and descriptive measure.",
            "RS4  ASR runs, once each: RS4a on the confirmation set (R1, R2) and RS4b on the sweep set (R3), with "
            "the conditions of every analysis whose gates passed; both recognisers.",
            "RS5  Analysis with the frozen code: estimates, intervals and outcomes; one sealed decision record per "
            "analysis and a combined record.",
            "RS6  The manuscript is revised only after RS5 and the author's review, and only as the consequences "
            "above allow.",
        ],
        "commands": [
            {"step": "RS0", "command": f"{des} select"},
            {"step": "RS0", "command": f"{des} diagnose-r2"},
            {"step": "RS0", "command": f"{des} freeze-spec"},
            {"step": "RS1", "command": f"{run} calibrate"},
            {"step": "RS2", "command": f"{des} freeze-code"},
            {"step": "RS3", "command": f"{run} validate"},
            {"step": "RS4", "command": f"{run} run"},
            {"step": "RS5", "command": f"{run} analyse"},
        ],
        "outputs": {
            "calibration": str(CALIBRATION_REPORT.parent),
            "code_freeze": str(CODE_FREEZE),
            "validation": str(RESULTS / "validation"),
            "raw": str(RESULTS / "raw") + "/{confirmation,sweep}",
            "analysis": str(RESULTS / "analysis"),
        },
        "policies": [
            "Amendments: a change to this plan before the step it affects needs explicit approval and a sealed "
            "amendment record (text, reason, time, new hashes). A change after that step is a deviation and is "
            "reported with the results.",
            "Sealed records are never edited; corrections go in new, dated records.",
        ],
        "compute_estimate": f"Stage 3 measured {SECONDS_PER_UTTERANCE_SIX_CONDITIONS} s per utterance for six conditions "
                            f"and both recognisers (RTX 5090), about {per_condition:.2f} s per utterance and condition. "
                            f"RS4a with all {n_conf} conditions: about {minutes_a:.0f} min; RS4b (2 conditions, "
                            f"{sweep_ref['n_utterances']:,} utterances): about {minutes_b:.0f} min. RS3 (encode, decode "
                            "and filter; no ASR): about 20-30 min. RS1: minutes.",
        "not_done": [
            "No decoder other than FFmpeg 6.1.1's native decoder and libopus 1.4; no other library version and no "
            "decoder-side enhancement.",
            "No re-fitting of the primary control: LP stays the primary control; LP_LIBOPUS (if built) serves R1 "
            "only, and SURR8 serves only the alternative attribution of R2.",
            "No mediumband, super-wideband or fullband, no other bitrate or signal hint in R3, and no REF or LP "
            "recognition in R3.",
            "No level matching of OPUS_REFDEC, LP_LIBOPUS, SURR8 or WB8 (broadband level was examined in A).",
            "No fresh speakers: R1 and R2 reuse the confirmation set, R3 reuses B's fresh-utterance, not "
            "fresh-speaker, holdout.",
            "No factorial interaction estimate, no multiplicity correction, and no other recogniser, beam search "
            "or language model.",
            "No change to Stage 1-3, A or B records, or to the manuscript, before RS5.",
        ],
        "literature_note": {"path": str(LITERATURE_NOTE), "sha256": inputs["literature_note_sha256"]},
    }


# ==================================================
# Markdown rendering (from the sealed record only)
# ==================================================

HEADINGS = {
    "planning_probe_and_diagnosis": "Planning probe and its diagnosis (before this freeze)",
    "data_and_conditions": "Data and conditions",
    "reference_decoder": "Reference decoder",
    "decoder_matched_control": "Decoder-matched control",
    "surrogate_design": "Surrogate design (unchanged Stage 2B procedure, one change)",
    "pre_asr_gates": "Pre-ASR gates (PASS required)",
    "estimands": "Estimands",
    "outcomes": "Outcomes (exact)",
    "analytic_expectations": "Analytic expectations (not tests)",
    "rules": "Interpretation rules (exact)",
    "manuscript_consequences": "Consequences for the manuscript",
}
NOT_RENDERED_IN_SECTION = {"title", "label", "question", "tolerances", "design_parameters", "encoder_settings_record"}


def _block(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [f"- {s}" for s in value]
    lines = []
    for key, item in value.items():
        if isinstance(item, list):
            lines += [f"- **{key}**:", *[f"  - {s}" for s in item]]
        else:
            lines.append(f"- **{key}**: {item}")
    return lines


def _analysis(number: str, key: str, spec: dict) -> list[str]:
    r = spec[key]
    lines = [f"## {number}. {key} - {r['title']}", "", f"**{r['label']}**", "", f"**Question.** {r['question']}", ""]
    sub = 0
    for field, value in r.items():
        if field in NOT_RENDERED_IN_SECTION:
            continue
        sub += 1
        lines += [f"### {number}.{sub} {HEADINGS[field]}", "", *_block(value), ""]
    if "tolerances" in r:
        lines += ["R2 tolerances (unchanged Stage 2B values):", "", "| R2 criterion | Value | Stage 2B key |",
                  "|---|---|---|", *[f"| {k} | {t['value']} | `{t['stage2b']}` |" for k, t in r["tolerances"].items()], ""]
    return lines


def render(spec: dict) -> str:
    P, labels, sel = spec["provenance"], asr.MODEL_LABELS, spec["selections"]
    lines = [
        "# Reviewer-concern sensitivity analyses R1-R3 - frozen plan (revision 2)", "",
        f"Sealed `reviewer_spec.json` SHA-256 `{spec['spec_sha256']}`, created {spec['created_utc']}.", "",
        f"**Status: {spec['status']}**", "",
        "This file is rendered from `reviewer_spec.json`; the JSON record is authoritative. The literature basis "
        f"is `{spec['literature_note']['path']}` (SHA-256 `{spec['literature_note']['sha256']}`).", "",
        "## 0. Revision history", "", *_block(spec["revision_history"]), "",
        "## 1. Scope", "", *_block(spec["scope"]), "",
        "## 2. Interpretation labels", "", *_block(spec["interpretation_labels"]), "",
        "## 3. Provenance and inputs", "",
        *[f"- {k}: `{v}`" for k, v in P.items() if k != "working_tree_status"],
        f"- working tree at freeze: {P['working_tree_status'] or 'clean'}", "",
        "Inputs read to freeze this plan:", "", *_block(spec["inputs_read"]), "",
        "## 4. Selections (only the signal-validation subset is new)", "",
        "| Role | File | SHA-256 | Size | Used by |", "|---|---|---|---|---|",
        *[f"| {role.replace('_', ' ')} | `{s['path']}` | `{s['sha256'][:12]}...` | {s['size']} | {s['used_by']}"
          f"{'; ' + s['note'] if 'note' in s else ''} |" for role, s in sel.items() if role != "rule"],
        "", sel["rule"], "",
        "## 5. Common pipeline, ASR runs and statistics", "", *_block(spec["common_pipeline"]), "",
        "ASR runs:", "", *_block(spec["asr_runs"]), "",
        "Environment gates (RS1, Stage 3 calibration set):", "", *_block(spec["environment_gates"]), "",
        "## 6. Anchors from frozen Stage 3 (confirmation, pooled micro, pp)", "",
        f"Margin = {MATERIALITY_FRACTION} x T*_m (Addition A's GO margin); used by R1 and R2.", "",
        "| Recogniser | T* = OPUS - LP [95 % CI] | B* = LP - REF [95 % CI] | OPUS - REF | share s* [95 % CI] | "
        "margin | R1: D1_lo > | R2: Delta2_hi < |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {labels[m]} | {a['T_star']['estimate']:.6f} [{a['T_star']['ci'][0]:.3f}, {a['T_star']['ci'][1]:.3f}] | "
          f"{a['B_star']['estimate']:.6f} [{a['B_star']['ci'][0]:.3f}, {a['B_star']['ci'][1]:.3f}] | "
          f"{a['total_star']['estimate']:.6f} | {a['share_star']['estimate']:.3f} "
          f"[{a['share_star']['ci'][0]:.3f}, {a['share_star']['ci'][1]:.3f}] | {a['margin_pp']:.6f} | "
          f"{a['R1_D1_lower_must_exceed']:.6f} | {a['R2_Delta2_upper_must_be_below']:.6f} |"
          for m, a in spec["anchors"].items()],
        "",
        *_analysis("7", "R1", spec),
        *_analysis("8", "R2", spec),
        *_analysis("9", "R3", spec),
        "## 10. Stopping rules", "", *_block(spec["stopping_rules"]), "",
        "## 11. Run order and commands", "", *_block(spec["run_order"]), "",
        "Commands (the runner is written at RS1; its name and subcommands are part of this plan):", "",
        *[f"- {c['step']}: `{c['command']}`" for c in spec["commands"]],
        "", f"Outputs: {json.dumps(spec['outputs'])}", "",
        "## 12. Policies", "", *_block(spec["policies"]), "",
        "## 13. Compute", "", spec["compute_estimate"], "",
        "## 14. Not done in R1-R3", "", *_block(spec["not_done"]), "",
    ]
    return "\n".join(lines)


# ==================================================
# Freeze, check and guards
# ==================================================

def code_hashes() -> dict:
    """SHA-256 of every R1-R3, upgrade, Stage 2B and Stage 3 code file; None for a file not yet written."""
    files = REVIEW_CODE_FILES + OTHER_CODE_USED + list(s3.CODE_FILES)
    return {str(p): (s3.file_sha256(p) if p.exists() else None) for p in files}


def inputs_unchanged(spec: dict) -> None:
    current = recorded_inputs()
    changed = sorted(k for k, value in current.items() if spec["provenance"].get(k) != value)
    if changed:
        raise RuntimeError(f"inputs changed since the design freeze: {changed}")
    table = settings_table()
    if {NB8: table[NB8], WB8: table[WB8]} != spec["R3"]["encoder_settings_record"]:
        raise RuntimeError("NB8 or WB8 settings differ from the frozen plan")
    if stage3_anchors() != spec["anchors"]:
        raise RuntimeError("Stage 3 anchors differ from the frozen plan")
    if r2_tolerances() != spec["R2"]["tolerances"]:
        raise RuntimeError("R2 tolerances differ from the frozen plan")
    selection = s3.read_sealed(SV_SELECTION, "selection_sha256")
    drawn = draw_signal_validation()
    if {k: selection[k] for k in drawn} != drawn:
        raise RuntimeError("the signal-validation selection does not reproduce from its rule")


def require_frozen_plan() -> dict:
    """The sealed, committed plan, its rendering, and every recorded input unchanged."""
    spec = s3.read_sealed(SPEC_JSON, "spec_sha256")
    for path in [SPEC_JSON, PLAN_MD, LITERATURE_NOTE, SV_SELECTION, R2_DIAGNOSIS]:
        upgrade.tracked_and_clean(path)
    if PLAN_MD.read_text() != render(spec):
        raise RuntimeError(f"{PLAN_MD} is not the rendering of the sealed plan")
    inputs_unchanged(spec)
    return spec


def require_code_freeze() -> tuple[dict, dict]:
    spec = require_frozen_plan()
    freeze = s3.read_sealed(CODE_FREEZE, "freeze_sha256")
    if freeze["spec_sha256"] != spec["spec_sha256"]:
        raise RuntimeError("plan changed since the code freeze")
    current = code_hashes()
    changed = sorted(f for f, digest in freeze["code_sha256"].items() if current.get(f) != digest)
    if changed:
        raise RuntimeError(f"code changed since the code freeze: {changed}")
    return spec, freeze


def freeze_spec() -> None:
    if SPEC_JSON.exists() or PLAN_MD.exists():
        raise RuntimeError("the R1-R3 plan is already frozen")
    if RESULTS.exists():
        raise RuntimeError(f"{RESULTS} exists: the plan must precede every R1-R3 run")
    for path in [LITERATURE_NOTE, SV_SELECTION, R2_DIAGNOSIS]:
        if not path.exists():
            raise RuntimeError(f"{path} must exist before the freeze (select, diagnose-r2)")
    digest = s3.write_sealed(SPEC_JSON, build_spec(), "spec_sha256")
    PLAN_MD.write_text(render(s3.read_sealed(SPEC_JSON, "spec_sha256")))
    print(f"R1-R3 spec sha256 {digest}")


def check() -> None:
    spec = s3.read_sealed(SPEC_JSON, "spec_sha256")
    print(f"seal: OK ({spec['spec_sha256']})")
    if PLAN_MD.read_text() != render(spec):
        raise RuntimeError(f"{PLAN_MD} is not the rendering of the sealed plan")
    print("plan rendering: OK")
    diagnosis = s3.read_sealed(R2_DIAGNOSIS, "diagnosis_sha256")
    body = s3.native(diagnosis_body())
    if {k: diagnosis[k] for k in body} != body:
        raise RuntimeError("the R2 planning diagnosis does not reproduce from the frozen curves")
    print("R2 planning diagnosis: reproduces from the frozen curves")
    inputs_unchanged(spec)
    print("inputs, NB8/WB8 settings, Stage 3 anchors, R2 tolerances and the signal-validation draw: unchanged")
    committed = all(upgrade.git("ls-files", "--error-unmatch", str(p)).returncode == 0
                    for p in [SPEC_JSON, PLAN_MD, LITERATURE_NOTE, SV_SELECTION, R2_DIAGNOSIS])
    print("committed:", "yes (binding)" if committed else "no (not yet binding)")
    outputs = [str(p) for p in EVALUATION_OUTPUTS if p.exists()]
    print("R1-R3 evaluation outputs:", outputs or "none")


def freeze_code(amendment: str | None) -> None:
    spec = require_frozen_plan()
    if CODE_FREEZE.exists():
        raise RuntimeError(f"{CODE_FREEZE} is sealed and exists")
    calibration = s3.read_sealed(CALIBRATION_REPORT, "report_sha256")
    if not calibration["E1"]["pass"]:
        raise RuntimeError("gate E1 failed; the code cannot be frozen for evaluation")
    current = code_hashes()
    at_design = spec["code_sha256_at_design_freeze"]
    added = sorted(f for f in current if at_design.get(f) is None and current[f] is not None)
    changed = sorted(f for f in current if at_design.get(f) is not None and at_design[f] != current[f])
    if changed and not amendment:
        raise RuntimeError(f"code changed since the design freeze ({changed}); an amendment note is required")
    missing = sorted(f for f in current if current[f] is None)
    if missing:
        raise RuntimeError(f"code files missing at the code freeze: {missing}")
    r1, r2 = calibration.get("R1", {}), calibration.get("R2", {})
    s3.write_sealed(CODE_FREEZE, {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
        "calibration_report_sha256": calibration["report_sha256"],
        "r1_status": "calibrated" if r1.get("C1_pass") else STOPPED,
        "r1_reuse_pass": r1.get("REUSE_pass"), "r1_control": r1.get("control"),
        "lp_libopus_taps_sha256": r1.get("lp_libopus_taps_sha256"),
        "r2_status": "calibrated" if r2.get("C1_pass") else STOPPED,
        "surr8_taps_sha256": r2.get("surr8_taps_sha256"),
        "code_sha256": current, "code_added_since_design_freeze": added,
        "code_changed_since_design_freeze": changed, "amendment": amendment,
    }, "freeze_sha256")
    print("code freeze sealed; added:", added or "none", "; changed:", changed or "none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["select", "diagnose-r2", "freeze-spec", "check", "freeze-code"])
    parser.add_argument("--amendment", default=None)
    args = parser.parse_args()
    os.chdir(REPO_ROOT)
    {"select": select, "diagnose-r2": diagnose_r2, "freeze-spec": freeze_spec, "check": check,
     "freeze-code": lambda: freeze_code(args.amendment)}[args.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
