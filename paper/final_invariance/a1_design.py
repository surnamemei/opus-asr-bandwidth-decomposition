"""
A1: cross-validated best-linear decomposition of 8 kbit/s Opus (post-confirmation sensitivity).

Design module: the metadata-only signal-set draw, the sealed plan (A1_SPEC.json, rendered as
A1_PLAN.md), the frozen outcome rule and the guards that every later step calls.

    python paper/final_invariance/a1_design.py select        # signal-only sets, from metadata only
    python paper/final_invariance/a1_design.py freeze-spec   # seal the plan (before any A1 audio is read)
    python paper/final_invariance/a1_design.py check
    python paper/final_invariance/a1_design.py freeze-code   # after the calibration step

A1 is not a replacement for Stage 3, not a redefinition of the primary control, not a bandwidth
control, not a successor to R2 and not a causal coding-distortion decomposition.
"""

import argparse
import json
import math
import os
import platform
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / "paper" / "decoder_sensitivity"), str(ROOT / "paper" / "reviewer_sensitivity"),
                str(ROOT / "paper" / "taslp_upgrade"), str(ROOT / "paper")]

import numpy as np                   # noqa: E402
import pandas as pd                  # noqa: E402
import torch                         # noqa: E402
import torchaudio                    # noqa: E402

import a1_opd as opd                 # noqa: E402
import opus_direct                   # noqa: E402
import reviewer_design as rd         # noqa: E402
import run_lowpass_confirmation as s2c  # noqa: E402
import run_stage3 as s3              # noqa: E402
import stage3_asr as asr             # noqa: E402
import stage3_audio as audio         # noqa: E402
import stage3_stats as s3stats       # noqa: E402
import upgrade_design as upgrade     # noqa: E402

FI = Path("paper") / "final_invariance"
SELECTION = FI / "selection_a1_signal.json"
SPEC_JSON = FI / "A1_SPEC.json"
PLAN_MD = FI / "A1_PLAN.md"
METHOD_NOTE = FI / "A1_METHOD_NOTE.md"
CODE_FREEZE = FI / "A1_CODE_FREEZE.json"
RESULTS = Path("results_paper") / "final_invariance"
CALIBRATION = RESULTS / "a1_calibration"
VALIDATION = RESULTS / "a1_validation"
EVALUATION = RESULTS / "a1_evaluation"
RAW = RESULTS / "a1_raw"
DECISION = RESULTS / "A1_DECISION.json"
BOOTSTRAP = RESULTS / "a1_bootstrap.csv"

A1_CODE_FILES = [FI / name for name in ["a1_opd.py", "a1_design.py", "run_a1.py", "tests/test_a1.py"]]
OTHER_CODE_USED = [Path("paper/reviewer_sensitivity/reviewer_design.py"),
                   Path("paper/taslp_upgrade/upgrade_design.py"), Path("paper/taslp_upgrade/upgrade_stats.py"),
                   Path("paper/taslp_upgrade/upgrade_pipeline.py")]

SEED = 53056                         # selection seeds so far: 53051-53053 (Stage 3), 53054 (B), 53055 (R1/R2)
SUBSET = "train-clean-100"
PER_SEX = 20                         # per set and sex: 20 F + 20 M calibration, 20 F + 20 M validation
MODELS = asr.MODELS
LIN8 = "LIN8"
STAGE3_CONDITIONS = ["REF", "LP", "OPUS"]
CONDITIONS = STAGE3_CONDITIONS + [LIN8]
N_BOOT = s3stats.N_BOOT              # 10,000
BOOT_SEED = s3stats.BOOT_SEED        # 5305: Stage 3's seed on Stage 3's speakers
NORMAL_EQUATION_TOLERANCE = 1e-6
MIN_COLLAPSE_TOLERANCE_DB = 1.0
ANCHOR_TOLERANCE_PP = 1e-9
OUTCOMES = ("ROBUST_RESIDUAL", "RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS", "MIXED", "LINEAR_EXPLANATION_DOMINATES")
QUANTITIES = {"L8": (LIN8, "REF"), "R8": ("OPUS", LIN8), "T": ("OPUS", "REF"),
              "B_primary": ("LP", "REF"), "R_primary": ("OPUS", "LP"),
              "delta_L": (LIN8, "LP"), "delta_R": ("LP", LIN8)}


def a1_outcome(cells: dict) -> str:
    """
    Frozen A1 outcome from the pooled micro estimates of both recognisers (cells[m] holds R8 = (est,
    lo, hi) and L8 = (est, lo, hi)). Precedence, in this order:

    1. LINEAR_EXPLANATION_DOMINATES: R8_lo <= 0 (or missing) in both recognisers, or L8 > R8 (the
       best-linear surrogate absorbs most of the total penalty) in both.
    2. MIXED: R8_lo > 0 in exactly one recogniser.
    3. ROBUST_RESIDUAL: R8_lo > 0 in both, and R8 > L8 in both.
    4. RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS: R8_lo > 0 in both, but L8 >= R8 in at least one.
    """
    def persists(m):
        lo = cells[m]["R8"][1]
        return lo is not None and not (isinstance(lo, float) and math.isnan(lo)) and lo > 0

    linear_most = {m: cells[m]["L8"][0] > cells[m]["R8"][0] for m in MODELS}
    if not any(persists(m) for m in MODELS) or all(linear_most.values()):
        return "LINEAR_EXPLANATION_DOMINATES"
    if persists(MODELS[0]) != persists(MODELS[1]):
        return "MIXED"
    if all(cells[m]["R8"][0] > cells[m]["L8"][0] for m in MODELS):
        return "ROBUST_RESIDUAL"
    return "RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS"


# ==================================================
# Signal-only sets (metadata only)
# ==================================================

def excluded_speakers() -> dict:
    fv = s3.read_sealed(s2c.SPEC_PATH, "spec_sha256")["confirmation_set"]
    sv = s3.read_sealed(rd.SV_SELECTION, "selection_sha256")
    return {"stage2b_filter_validation": sorted(set(fv["speakers_female"]) | set(fv["speakers_male"])),
            "r1_r2_signal_validation": sorted(set(sv["speakers_female"]) | set(sv["speakers_male"]))}


def draw_signal_sets() -> dict:
    """20 F + 20 M calibration and 20 F + 20 M validation train-clean-100 speakers, one utterance each."""
    excluded = excluded_speakers()
    used = set(excluded["stage2b_filter_validation"]) | set(excluded["r1_r2_signal_validation"])
    speakers = s2c.read_speakers()
    rng = random.Random(SEED)
    sets = {"calibration": {}, "validation": {}}
    for sex in ["F", "M"]:
        pool = sorted(s["id"] for s in speakers if s["subset"] == SUBSET and s["sex"] == sex and s["id"] not in used)
        drawn = rng.sample(pool, 2 * PER_SEX)
        sets["calibration"][sex] = sorted(drawn[:PER_SEX])
        sets["validation"][sex] = sorted(drawn[PER_SEX:])
    dev = {int(p.name) for subset in s2c.DEV_SUBSETS for p in s2c.subset_dir(subset).iterdir() if p.is_dir()}
    all_drawn = [s for part in sets.values() for group in part.values() for s in group]
    if len(set(all_drawn)) != 4 * PER_SEX or (set(all_drawn) & (used | dev)):
        raise RuntimeError("A1 signal sets overlap each other, earlier signal sets or the dev sets")
    root = s2c.subset_dir(SUBSET)
    rng = random.Random(SEED)
    out = {}
    for name in ["calibration", "validation"]:
        utterances = []
        for speaker in sorted(sets[name]["F"] + sets[name]["M"]):
            files = sorted(p.relative_to(root).as_posix() for p in (root / str(speaker)).glob("*/*.flac"))
            if not files:
                raise RuntimeError(f"no audio files for speaker {speaker}")
            path = rng.choice(files)
            speaker_id, chapter_id, utterance_id = Path(path).stem.split("-")
            utterances.append({"speaker_id": int(speaker_id), "chapter_id": int(chapter_id),
                               "utterance_id": int(utterance_id), "utterance": Path(path).stem,
                               "path": f"{SUBSET}/{path}", "sex": "F" if speaker in sets[name]["F"] else "M",
                               "candidates": len(files)})
        out[name] = {"speakers_female": sets[name]["F"], "speakers_male": sets[name]["M"], "utterances": utterances}
    return {
        "role": "A1 signal-only sets: no transcript is read and no ASR is run on them",
        "subset": SUBSET, "speaker_source": str(s2c.SPEAKERS_FILE),
        "speakers_file_sha256": s3.file_sha256(s2c.SPEAKERS_FILE), "seed": SEED,
        "speaker_rule": f"for each sex, random.Random({SEED}).sample of {2 * PER_SEX} speakers from the sorted "
                        f"{SUBSET} IDs in SPEAKERS.TXT, excluding every speaker of earlier signal-control fits and "
                        f"validations (Stage 2B filter validation, R1/R2 signal validation); the first {PER_SEX} of "
                        f"each sex drawn are the calibration set, the next {PER_SEX} the validation set",
        "utterance_rule": f"for each selected speaker in ascending ID order, one file drawn by random.Random({SEED})"
                          ".choice from the sorted <speaker>/<chapter>/*.flac names (one generator, calibration "
                          "then validation); file names only",
        "excluded": excluded, **out,
        "note": "Stage 2B calibration and the Stage 3 sets are dev/test speakers, disjoint from train-clean-100",
    }


def select() -> None:
    if SELECTION.exists():
        raise RuntimeError(f"{SELECTION} is sealed and exists")
    digest = s3.write_sealed(SELECTION, s3.native(draw_signal_sets()), "selection_sha256")
    print(f"A1 signal-set selection sealed: {digest}")


# ==================================================
# Recorded inputs and environment
# ==================================================

def environment() -> dict:
    lib = opus_direct.libopus_path()
    return {"libopus": {"version": opus_direct.libopus_version(), "path": lib, "sha256": s3.file_sha256(Path(lib))},
            "python": platform.python_version(), "torch": torch.__version__, "torchaudio": torchaudio.__version__,
            "numpy": np.__version__, "pandas": pd.__version__}


def recorded_inputs() -> dict:
    return {
        "stage3_spec_sha256": s3.read_sealed(s3.SPEC_JSON, "spec_sha256")["spec_sha256"],
        "stage3_decision_sha256": s3.read_sealed(upgrade.S3_DECISION, "decision_sha256")["decision_sha256"],
        "stage3_confirmation_outputs_sha256":
            s3.read_sealed(upgrade.S3_CONFIRMATION / "outputs_sha256.json", "outputs_sha256")["outputs_sha256"],
        "stage3_calibration_outputs_sha256":
            s3.read_sealed(upgrade.S3_CALIBRATION / "outputs_sha256.json", "outputs_sha256")["outputs_sha256"],
        "stage3_bootstrap_csv_sha256": s3.file_sha256(upgrade.S3_BOOTSTRAP),
        "confirmation_selection_sha256": s3.load_selection("confirmation")["selection_sha256"],
        "calibration_selection_sha256": s3.load_selection("calibration")["selection_sha256"],
        "a1_signal_selection_sha256": s3.read_sealed(SELECTION, "selection_sha256")["selection_sha256"],
        "method_note_sha256": s3.file_sha256(METHOD_NOTE),
        "stage3_opus_encoder_settings": s3.read_sealed(s3.SPEC_JSON, "spec_sha256")["conditions"]["encoder_settings"]["OPUS"],
    }


def stage3_anchors() -> dict:
    """Stage 3's sealed confirmation values that A1's code must reproduce before recognition (gate E4)."""
    boot = pd.read_csv(upgrade.S3_BOOTSTRAP)
    boot = boot[(boot["set"] == "confirmation") & (boot["kind"] == "micro")]
    names = {"wer_REF": "wer_REF", "wer_LP": "wer_LP", "wer_OPUS": "wer_OPUS", "B_primary": "delta_bw",
             "R_primary": "delta_opus_residual", "T": "delta_opus_total"}
    out = {}
    for model in MODELS:
        out[model] = {}
        for scope in ["pooled", "test-clean", "test-other"]:
            out[model][scope] = {}
            for a1_name, s3_name in names.items():
                row = boot[(boot["model"] == model) & (boot["scope"] == scope) & (boot["quantity"] == s3_name)]
                if len(row) != 1:
                    raise RuntimeError(f"Stage 3 bootstrap: {model}/{scope}/{s3_name}")
                r = row.iloc[0]
                out[model][scope][a1_name] = {"stage3_quantity": s3_name, "estimate": float(r["estimate"]),
                                              "ci": [float(r["ci_lower"]), float(r["ci_upper"])]}
    return out


# ==================================================
# The plan
# ==================================================

def build_spec() -> dict:
    sel = s3.read_sealed(SELECTION, "selection_sha256")
    return {
        "analysis": "A1",
        "title": "Cross-validated best-linear decomposition of 8-kbit/s Opus",
        "created_utc": s3.now(),
        "status": "FROZEN PLAN: sealed before any A1 audio is read. Evaluation (confirmation-set LIN8 audio and ASR) "
                  "needs the committed plan, calibration, code freeze and a passed signal validation.",
        "label": "POST-CONFIRMATION SENSITIVITY ANALYSIS: AN INCLUSIVE SAME-FREQUENCY LINEAR ATTRIBUTION - NOT A "
                 "REPLACEMENT FOR STAGE 3, NOT A BANDWIDTH CONTROL, NOT R2, NOT A CAUSAL DECOMPOSITION",
        "question": "If every same-frequency linearly predictable change of the actual 8 kbit/s Opus chain is assigned "
                    "to a linear component, does a substantial ASR residual remain?",
        "is_not": ["a replacement for the Stage 3 decomposition, which stays the primary pre-specified result",
                   "a redefinition of the published primary control", "a bandwidth control",
                   "a resurrection of R2 (a global zero-phase surrogate)", "a causal coding-distortion decomposition"],
        "method": {
            "choice": "option A of the pass instructions: the orthogonal projection-based decomposition (OPD) target "
                      "component of Iwamoto et al. (Interspeech 2022) and Ochiai et al. (IEEE TASLP 2024), i.e. "
                      "the BSS Eval projection; see A1_METHOD_NOTE.md",
            "definition": "for each utterance u with REF x_u and the exact Stage 3 OPUS waveform y_u (FFmpeg decode, "
                          "16 kHz, length T), LIN8_u = P_x y_u restricted to the T samples of REF, where P_x projects "
                          "onto the span of x_u delayed by tau = -256 ... +255 (L = 512 basis vectors); the residual is "
                          "y_u - LIN8_u",
            "copied": "L = 512 (BSS Eval default, Ochiai et al.); per-utterance, time-domain, unconstrained "
                      "least-squares FIR projection; mir_eval._project algorithm (zero padding by L - 1, FFT "
                      "autocorrelation Toeplitz Gram matrix, FFT cross-correlation, exact solve with least-squares "
                      "fallback), reimplemented in numpy (a1_opd.py)",
            "adapted": "the delay span is centred (tau = -256 ... +255) instead of causal (0 ... 511), because the "
                       "decoded signal is aligned with REF to within 1-2 samples and the chain's linear response is "
                       "two-sided (linear-phase resampler); implemented as in BSS Eval by delaying the estimate by 256 "
                       "samples and advancing the projection. The centring is fixed a priori at L/2; the causal "
                       "variant is computed on the calibration set only, as a descriptive check, and selects nothing",
            "free_parameters": "none: no global filter is fitted, no support or ridge grid is used, no parameter is "
                               "tuned on any data",
            "allowed_in_the_linear_component": "gain, spectral tilt, band-edge roll-off, phase and delay within the "
                                               "32 ms span; no unity gain, flat passband, zero phase or 4 kHz cutoff is "
                                               "imposed",
            "not_in_the_linear_component": "anything not same-frequency linearly predictable from REF by one "
                                           "time-invariant 512-tap filter per utterance: nonlinear coding distortion, "
                                           "the 4-5 kHz mirror image, time-varying gains",
        },
        "data_isolation": [
            "The projection is utterance-level by construction (the prior method), so the confirmation utterances' own "
            "OPUS waveforms are projected; this is pre-specified here, uses no ASR output, and no parameter is fitted "
            "on any set.",
            "The new signal-only sets (selection_a1_signal.json) serve to run every piece of code before the freeze, "
            "to fix and check the signal gates, and to describe the linear response; no ASR is run on them.",
            "No Addition B sweep utterance is used.",
        ],
        "selection": {"path": str(SELECTION), "sha256": sel["selection_sha256"], "seed": SEED,
                      "calibration": f"{len(sel['calibration']['utterances'])} utterances (20 F, 20 M speakers)",
                      "validation": f"{len(sel['validation']['utterances'])} utterances (20 F, 20 M speakers)",
                      "evaluation": "the 2,174 Stage 3 confirmation utterances (73 speakers), unchanged"},
        "signal_processing": {
            "OPUS8": "Stage 3 OPUS settings (libopus 1.4, 8 kbit/s, forced NB, signal=auto, application audio, "
                     "unconstrained VBR, complexity 10, 20 ms frames), Ogg Opus, FFmpeg 6.1.1 native decode at 48 kHz, "
                     "torchaudio resample to 16 kHz: stage3_audio.codec_round_trip, unchanged",
            "LIN8": "a1_opd.project(REF, OPUS8): float64, cast to float32 for recognition; no gain matching, no "
                    "realignment after the projection, no clipping, no post-filtering",
        },
        "gates": {
            "C1 (calibration set)": f"for every utterance the projection is finite and its normal-equation residual is "
                                    f"<= {NORMAL_EQUATION_TOLERANCE}; LIN8 has the REF length and is finite",
            "C2 (calibration set)": "a second pass reproduces every LIN8 waveform bit for bit",
            "C3 (Stage 3 calibration set, GPU)": "the frozen Stage 3 pipeline reproduces the sealed Stage 3 calibration "
                                                 "audio and hypotheses exactly (environment reproduction), and the LIN8 "
                                                 "recognition path runs and repeats deterministically (no WER is "
                                                 "compared)",
            "collapse tolerance (fixed at calibration, before validation audio is read)":
                f"tol = max({MIN_COLLAPSE_TOLERANCE_DB} dB, interquartile range of the calibration per-utterance "
                f"projection NMSE in dB)",
            "V1 (validation set)": f"as C1 for every validation utterance",
            "V2 (validation set)": "no held-out collapse: median validation NMSE (dB) <= median calibration NMSE "
                                   "(dB) + tol",
            "V3 (validation set)": "a second pass reproduces every LIN8 waveform bit for bit",
            "E1 (confirmation set, before recognition)": "the regenerated OPUS Ogg files and waveforms equal the sealed "
                                                         "Stage 3 OPUS ogg_sha256 and waveform_sha256 for all 2,174 "
                                                         "utterances",
            "E2 (confirmation set)": "as C1 for all 2,174 LIN8 waveforms",
            "E3 (confirmation set)": "the environment equals the one sealed in this plan",
            "E4 (confirmation set)": f"A1's analysis code reproduces Stage 3's WER(REF), WER(LP), WER(OPUS), LP - REF, "
                                     f"OPUS - LP and OPUS - REF (estimate and bounds, pooled and per subset) within "
                                     f"{ANCHOR_TOLERANCE_PP} pp",
            "E5 (procedural)": "no A1 evaluation WER exists before the plan, calibration, code freeze and validation "
                               "are committed",
            "on_failure": "A1 is STOPPED before evaluation recognition; the failed gate is sealed and reported; no "
                          "other span, filter length, projection, alignment or tolerance is tried under the A1 label",
        },
        "stage3_anchors": stage3_anchors(),
        "recognition": [
            "LIN8 only, once, on the 2,174 confirmation utterances; REF, LP and OPUS reuse the sealed Stage 3 outputs "
            "(exact paired reuse: the same utterances, and OPUS is the same waveform, checked by E1).",
            "Recognisers, checkpoints, decoding options and scoring exactly as Stage 3; runner upgrade_pipeline.run_set "
            "(chunks of 8, resumable progress file); each LIN8 waveform must equal its E-validated SHA-256.",
            "Cross-run component: Whisper's batches differ from Stage 3's (one condition per chunk); greedy float16 "
            "Whisper is not exactly invariant to batch composition (Addition A: 3 of 4,348 hypotheses). This is part "
            "of L8, R8 and delta_L and is not separated; wav2vec2 decodes each utterance alone.",
            "GPU: at least 12 GiB free and no other major GPU job at the start; GPU state logged.",
        ],
        "estimands": {
            "primary (pooled, per recogniser)": "L8 = WER(LIN8) - WER(REF); R8 = WER(OPUS8) - WER(LIN8); "
                                                "T = WER(OPUS8) - WER(REF); corpus (micro) WER, pp",
            "descriptive share": "S8 = L8 / T (NaN in a replicate with T <= 0; such replicates are counted); an "
                                 "inclusive linear-loss sensitivity share, not a bandwidth share and not a true share",
            "change from the primary decomposition": "delta_L = L8 - (LP - REF) = WER(LIN8) - WER(LP); "
                                                     "delta_R = R8 - (OPUS - LP) = -delta_L",
            "secondary": "the same quantities per test subset, uncorrected for multiplicity",
        },
        "bootstrap": f"Stage 3's paired speaker-cluster bootstrap, unchanged: speakers resampled within test subsets, "
                     f"{N_BOOT:,} replicates, seed {BOOT_SEED} on the Stage 3 speakers, 95 % percentile intervals, every "
                     f"quantity recomputed in each replicate (upgrade_stats.replicate_weights, Replicates, interval_row, "
                     f"analyse)",
        "outcome_rule": {
            "classes": list(OUTCOMES),
            "precedence": [
                "1 LINEAR_EXPLANATION_DOMINATES: R8's 95 % interval does not lie above zero in either recogniser, or "
                "L8 > R8 (the best-linear surrogate absorbs most of the total penalty) in both recognisers",
                "2 MIXED: R8's interval lies above zero in exactly one recogniser",
                "3 ROBUST_RESIDUAL: R8's interval lies above zero in both recognisers and R8 > L8 in both",
                "4 RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS: R8's interval lies above zero in both, but L8 >= R8 in at "
                "least one",
            ],
            "note": "the pass instructions' four classes, with this precedence fixed where their definitions overlap; "
                    "pooled micro estimates; implemented by a1_design.a1_outcome",
            "regardless of outcome": "the Stage 3 decomposition remains the primary pre-specified result",
        },
        "manuscript_consequences": {
            "ROBUST_RESIDUAL": "keep the Stage 3 decomposition; add a short sensitivity statement that a residual also "
                               "remains under a more inclusive best-linear attribution; never call S8 a true share",
            "RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS": "retain the Stage 3 result; state that the exact component split "
                                                        "depends on how linear loss is defined; high-level prose says a "
                                                        "substantial residual remains rather than exact shares",
            "MIXED": "make recogniser dependence central; remove any cross-recogniser statement that the residual "
                     "dominates",
            "LINEAR_EXPLANATION_DOMINATES": "do not hide it; rescope: the high-rate narrowband control underestimates "
                                            "the linear component of low-rate codec degradation, and a more inclusive "
                                            "linear attribution materially changes the split; Stage 3 stays the "
                                            "original pre-specified analysis",
            "STOPPED": "report the failed gate; the manuscript's decomposition is unchanged",
        },
        "run_order": [
            "select (done before this plan): selection_a1_signal.json",
            "freeze-spec: this plan",
            "calibrate: run_a1.py calibrate signal (C1, C2, collapse tolerance) and run_a1.py calibrate asr (C3, GPU)",
            "freeze-code: A1_CODE_FREEZE.json",
            "validate: run_a1.py validate (V1-V3)",
            "commit plan, selection, calibration, code freeze and validation",
            "evaluate: run_a1.py evaluate (E1-E5, 2,174 LIN8 waveforms, no ASR)",
            "run: run_a1.py run (LIN8 recognition, once)",
            "analyse: run_a1.py analyse (bootstrap, outcome, A1_DECISION.json)",
        ],
        "outputs": {"calibration": str(CALIBRATION), "validation": str(VALIDATION), "evaluation": str(EVALUATION),
                    "raw": str(RAW), "decision": str(DECISION), "bootstrap": str(BOOTSTRAP)},
        "policies": [
            "No threshold, span, filter length, alignment or data selection is changed after evaluation ASR is seen.",
            "Sealed records are never edited; corrections go in new, dated records; failures are sealed and reported.",
            "Every outcome, including STOPPED and LINEAR_EXPLANATION_DOMINATES, is reported.",
        ],
        "provenance": {**recorded_inputs(), "git_head_at_freeze": upgrade.git("rev-parse", "HEAD").stdout.strip()},
        "environment": environment(),
        "code_sha256_at_design_freeze": code_hashes(),
    }


def _block(value) -> list[str]:
    if isinstance(value, list):
        return [f"- {v}" for v in value]
    if isinstance(value, dict):
        return [f"- **{k}**: {v}" for k, v in value.items()]
    return [str(value)]


def render(spec: dict) -> str:
    rows = [f"| {asr.MODEL_LABELS[m]} | {s} | " + " | ".join(f"{a[q]['estimate']:.6f}" for q in
                                                              ["wer_REF", "wer_LP", "wer_OPUS", "B_primary", "R_primary", "T"]) + " |"
            for m, scopes in spec["stage3_anchors"].items() for s, a in scopes.items()]
    return "\n".join([
        f"# A1: {spec['title']} - frozen plan", "",
        f"Sealed `A1_SPEC.json` SHA-256 `{spec['spec_sha256']}`, created {spec['created_utc']}.", "",
        f"**Status: {spec['status']}**", "", f"**Label: {spec['label']}**", "",
        "Rendered from `A1_SPEC.json`; the JSON record is authoritative. Method basis: `A1_METHOD_NOTE.md`.", "",
        "## 1. Question", "", spec["question"], "", "A1 is not:", "", *_block(spec["is_not"]), "",
        "## 2. Method", "", *_block(spec["method"]), "",
        "## 3. Data isolation and selection", "", *_block(spec["data_isolation"]), "", *_block(spec["selection"]), "",
        "## 4. Signal processing", "", *_block(spec["signal_processing"]), "",
        "## 5. Gates", "", *_block(spec["gates"]), "",
        "Stage 3 anchors that E4 must reproduce (micro, pp):", "",
        "| Recogniser | Scope | WER REF | WER LP | WER OPUS | LP - REF | OPUS - LP | OPUS - REF |",
        "|---|---|---|---|---|---|---|---|", *rows, "",
        "## 6. Recognition", "", *_block(spec["recognition"]), "",
        "## 7. Estimands, bootstrap and outcome rule", "", *_block(spec["estimands"]), "", spec["bootstrap"], "",
        *_block(spec["outcome_rule"]["precedence"]), "", spec["outcome_rule"]["note"], "",
        f"Regardless of outcome: {spec['outcome_rule']['regardless of outcome']}.", "",
        "## 8. Manuscript consequences", "", *_block(spec["manuscript_consequences"]), "",
        "## 9. Run order, outputs and policies", "", *_block(spec["run_order"]), "",
        f"Outputs: `{json.dumps(spec['outputs'])}`", "", *_block(spec["policies"]), "",
        "## 10. Provenance and environment", "",
        *[f"- {k}: `{json.dumps(v) if isinstance(v, dict) else v}`" for k, v in spec["provenance"].items()],
        *[f"- {k}: `{json.dumps(v) if isinstance(v, dict) else v}`" for k, v in spec["environment"].items()], "",
    ])


# ==================================================
# Freeze, check and guards
# ==================================================

def code_hashes() -> dict:
    files = A1_CODE_FILES + OTHER_CODE_USED + list(s3.CODE_FILES)
    return {str(p): (s3.file_sha256(p) if p.exists() else None) for p in files}


def inputs_unchanged(spec: dict) -> None:
    current = recorded_inputs()
    changed = sorted(k for k, v in current.items() if spec["provenance"].get(k) != v)
    if changed:
        raise RuntimeError(f"A1 inputs changed since the plan: {changed}")
    if s3.native(stage3_anchors()) != spec["stage3_anchors"]:
        raise RuntimeError("Stage 3 anchors differ from the A1 plan")
    upgrade.stage3_integrity()


def environment_differences(spec: dict) -> list[str]:
    now = s3.native(environment())
    return sorted(k for k in spec["environment"] if spec["environment"][k] != now.get(k))


def require_frozen_plan(committed: bool) -> dict:
    spec = s3.read_sealed(SPEC_JSON, "spec_sha256")
    if PLAN_MD.read_text() != render(spec):
        raise RuntimeError(f"{PLAN_MD} is not the rendering of the sealed plan")
    if committed:
        for path in [SPEC_JSON, PLAN_MD, SELECTION, METHOD_NOTE]:
            upgrade.tracked_and_clean(path)
    inputs_unchanged(spec)
    return spec


def require_code_freeze(committed: bool) -> tuple[dict, dict]:
    spec = require_frozen_plan(committed)
    freeze = s3.read_sealed(CODE_FREEZE, "freeze_sha256")
    if freeze["spec_sha256"] != spec["spec_sha256"]:
        raise RuntimeError("A1 plan changed since the code freeze")
    current = code_hashes()
    changed = sorted(f for f, digest in freeze["code_sha256"].items() if current.get(f) != digest)
    if changed:
        raise RuntimeError(f"A1 code changed since the code freeze: {changed}")
    if committed:
        upgrade.tracked_and_clean(CODE_FREEZE)
    return spec, freeze


def freeze_spec() -> None:
    if SPEC_JSON.exists() or PLAN_MD.exists():
        raise RuntimeError("the A1 plan is already frozen")
    if any(p.exists() for p in [CALIBRATION, VALIDATION, EVALUATION, RAW]):
        raise RuntimeError("A1 outputs exist: the plan must precede every A1 step")
    digest = s3.write_sealed(SPEC_JSON, s3.native(build_spec()), "spec_sha256")
    PLAN_MD.write_text(render(s3.read_sealed(SPEC_JSON, "spec_sha256")))
    print(f"A1 spec sha256 {digest}")


def check() -> None:
    spec = s3.read_sealed(SPEC_JSON, "spec_sha256")
    print(f"seal: OK ({spec['spec_sha256']})")
    if PLAN_MD.read_text() != render(spec):
        raise RuntimeError("plan rendering differs")
    inputs_unchanged(spec)
    print("inputs, anchors and Stage 3 integrity unchanged; environment differences:",
          environment_differences(spec) or "none")
    print("code freeze:", "sealed" if CODE_FREEZE.exists() else "not yet")


def freeze_code() -> None:
    spec = require_frozen_plan(committed=False)
    if CODE_FREEZE.exists():
        raise RuntimeError(f"{CODE_FREEZE} is sealed and exists")
    reports = {name: s3.read_sealed(CALIBRATION / f"{name}_report.json", "report_sha256") for name in ["signal", "asr"]}
    failed = [n for n, r in reports.items() if not r["pass"] or r["spec_sha256"] != spec["spec_sha256"]]
    if failed:
        raise RuntimeError(f"A1 calibration did not pass ({failed}); the code cannot be frozen")
    current = code_hashes()
    missing = sorted(f for f, d in current.items() if d is None)
    if missing:
        raise RuntimeError(f"code files missing: {missing}")
    at_design = spec["code_sha256_at_design_freeze"]
    digest = s3.write_sealed(CODE_FREEZE, {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
        "calibration_report_sha256": {n: r["report_sha256"] for n, r in reports.items()},
        "collapse_tolerance_db": reports["signal"]["collapse_tolerance_db"],
        "calibration_median_nmse_db": reports["signal"]["summary"]["nmse_db"]["median"],
        "code_sha256": current,
        "code_added_since_design_freeze": sorted(f for f in current if at_design.get(f) is None),
        "code_changed_since_design_freeze": sorted(f for f in current if at_design.get(f) not in (None, current[f])),
    }, "freeze_sha256")
    print(f"A1 code freeze sealed: {digest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["select", "freeze-spec", "check", "freeze-code"])
    args = parser.parse_args()
    os.chdir(ROOT)
    {"select": select, "freeze-spec": freeze_spec, "check": check, "freeze-code": freeze_code}[args.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
