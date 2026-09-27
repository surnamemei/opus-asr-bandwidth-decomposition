"""
B1: 8-kbit/s application-mode sensitivity (a post-confirmation configuration sensitivity).

Question: keeping bitrate, bandwidth, signal hint, frame duration, VBR, complexity, decoder and ASR
fixed, does changing only OPUS_APPLICATION_AUDIO -> OPUS_APPLICATION_VOIP materially change the total
ASR penalty of 8 kbit/s Opus? OPUS_AUDIO8 is the sealed Stage 3 OPUS condition (reproduced exactly
before recognition); OPUS_VOIP8 is the only new condition. B1 is not a new decomposition, not a
bandwidth control and not an equivalence test, and it computes no VOIP bandwidth share.

This module holds the sealed plan (B1_SPEC.json, rendered as B1_PLAN.md), the frozen outcome rule
and the guards that every later step calls.

    python paper/final_invariance/b1_design.py freeze-spec
    python paper/final_invariance/b1_design.py check
    python paper/final_invariance/b1_design.py freeze-code   # after the calibration step
"""

import argparse
import dataclasses
import json
import math
import os
import platform
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

import opus_direct                   # noqa: E402
import run_stage3 as s3              # noqa: E402
import stage3_asr as asr             # noqa: E402
import stage3_audio as audio         # noqa: E402
import stage3_stats as s3stats       # noqa: E402
import upgrade_design as upgrade     # noqa: E402

FI = Path("paper") / "final_invariance"
SPEC_JSON = FI / "B1_SPEC.json"
PLAN_MD = FI / "B1_PLAN.md"
CODE_FREEZE = FI / "B1_CODE_FREEZE.json"
A1_DECISION = Path("results_paper") / "final_invariance" / "A1_DECISION.json"
RESULTS = Path("results_paper") / "final_invariance"
CALIBRATION = RESULTS / "b1_calibration"
CALIBRATION_PARTS = {"encode": CALIBRATION / "encode_report.json", "asr": CALIBRATION / "asr_report.json"}
VALIDATION = RESULTS / "b1_validation"
RAW = RESULTS / "b1_raw"
DECISION = RESULTS / "B1_DECISION.json"
BOOTSTRAP = RESULTS / "b1_bootstrap.csv"

B1_CODE_FILES = [FI / name for name in ["b1_design.py", "run_b1.py", "tests/test_b1.py"]]
OTHER_CODE_USED = [Path("paper/reviewer_sensitivity/reviewer_pipeline.py"),
                   Path("paper/taslp_upgrade/upgrade_design.py"), Path("paper/taslp_upgrade/upgrade_stats.py"),
                   Path("paper/taslp_upgrade/upgrade_pipeline.py")]

# ---------------------------------------------------------------- conditions, statistics, rule
MODELS = asr.MODELS
REF, AUDIO8, VOIP8 = "REF", "OPUS_AUDIO8", "OPUS_VOIP8"
STAGE3_LABEL = {REF: "REF", AUDIO8: "OPUS"}          # condition names in the sealed Stage 3 files
CONDITIONS = [REF, AUDIO8, VOIP8]
QUANTITIES = {"A": (AUDIO8, REF), "V": (VOIP8, REF), "D_app": (VOIP8, AUDIO8)}
SCOPES = ["pooled", "test-clean", "test-other"]
N_BOOT = s3stats.N_BOOT          # 10,000, as Stage 3
SEED = s3stats.BOOT_SEED         # 5305: Stage 3's seed on Stage 3's speakers
OUTCOMES = ("VOIP_LOWER_PENALTY", "NO_CLEAR_APPLICATION_DIFFERENCE", "VOIP_HIGHER_PENALTY")
STOPPED = "STOPPED"
ANCHOR_TOLERANCE_PP = 1e-9

AUDIO8_SETTINGS = audio.CODEC_SETTINGS["OPUS"]
VOIP8_SETTINGS = dataclasses.replace(AUDIO8_SETTINGS, application="voip")
EXPECTED = {"bandwidth": "NB", "frame_ms": 20.0, "channels": "mono"}   # forced by the settings in both conditions
POWER_BAND_HZ = (4000.0, 8000.0)


def settings_difference() -> dict:
    """Every EncoderSettings field that differs between the two conditions (must be application only)."""
    a, v = dataclasses.asdict(AUDIO8_SETTINGS), dataclasses.asdict(VOIP8_SETTINGS)
    return {k: [a[k], v[k]] for k in a if a[k] != v[k]}


if set(settings_difference()) != {"application"} or AUDIO8_SETTINGS.application != "audio":
    raise RuntimeError("B1 must change exactly one encoder parameter: application audio -> voip")


def b1_outcome(d_lo: float, d_hi: float) -> str:
    """
    Frozen outcome for D_app = WER(OPUS_VOIP8) - WER(OPUS_AUDIO8), one recogniser, pooled, from its 95 %
    speaker-bootstrap interval; no minimum-effect threshold, no equivalence claim, no combined outcome.

        VOIP_LOWER_PENALTY               D_hi < 0
        VOIP_HIGHER_PENALTY              D_lo > 0
        NO_CLEAR_APPLICATION_DIFFERENCE  otherwise, including a missing (NaN) bound
    """
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in (d_lo, d_hi)):
        return "NO_CLEAR_APPLICATION_DIFFERENCE"
    if d_hi < 0:
        return "VOIP_LOWER_PENALTY"
    if d_lo > 0:
        return "VOIP_HIGHER_PENALTY"
    return "NO_CLEAR_APPLICATION_DIFFERENCE"


# ==================================================
# Recorded inputs, environment and anchors
# ==================================================

def environment() -> dict:
    lib = opus_direct.libopus_path()
    return {"libopus": {"version": opus_direct.libopus_version(), "path": lib, "sha256": s3.file_sha256(Path(lib))},
            "python": platform.python_version(), "torch": torch.__version__, "torchaudio": torchaudio.__version__,
            "numpy": np.__version__, "pandas": pd.__version__}


def recorded_inputs() -> dict:
    s3spec = s3.read_sealed(s3.SPEC_JSON, "spec_sha256")
    return {
        "stage3_spec_sha256": s3spec["spec_sha256"],
        "stage3_decision_sha256": s3.read_sealed(upgrade.S3_DECISION, "decision_sha256")["decision_sha256"],
        "stage3_confirmation_outputs_sha256":
            s3.read_sealed(upgrade.S3_CONFIRMATION / "outputs_sha256.json", "outputs_sha256")["outputs_sha256"],
        "stage3_calibration_outputs_sha256":
            s3.read_sealed(upgrade.S3_CALIBRATION / "outputs_sha256.json", "outputs_sha256")["outputs_sha256"],
        "stage3_bootstrap_csv_sha256": s3.file_sha256(upgrade.S3_BOOTSTRAP),
        "confirmation_selection_sha256": s3.load_selection("confirmation")["selection_sha256"],
        "calibration_selection_sha256": s3.load_selection("calibration")["selection_sha256"],
        "stage3_opus_encoder_settings": s3spec["conditions"]["encoder_settings"]["OPUS"],
        "a1_decision_sha256": s3.read_sealed(A1_DECISION, "decision_sha256")["decision_sha256"]
        if A1_DECISION.exists() else None,
    }


def stage3_anchors() -> dict:
    """Stage 3's sealed confirmation values that B1's code must reproduce before recognition."""
    boot = pd.read_csv(upgrade.S3_BOOTSTRAP)
    boot = boot[(boot["set"] == "confirmation") & (boot["kind"] == "micro")]
    names = {"wer_REF": "wer_REF", "wer_OPUS_AUDIO8": "wer_OPUS", "A": "delta_opus_total"}
    out = {}
    for model in MODELS:
        out[model] = {}
        for scope in SCOPES:
            out[model][scope] = {}
            for b1_name, s3_name in names.items():
                row = boot[(boot["model"] == model) & (boot["scope"] == scope) & (boot["quantity"] == s3_name)]
                if len(row) != 1:
                    raise RuntimeError(f"Stage 3 bootstrap: {model}/{scope}/{s3_name}")
                r = row.iloc[0]
                out[model][scope][b1_name] = {"stage3_quantity": s3_name, "estimate": float(r["estimate"]),
                                              "ci": [float(r["ci_lower"]), float(r["ci_upper"])]}
    return out


# ==================================================
# The plan
# ==================================================

def build_spec() -> dict:
    conf = s3.load_selection("confirmation")
    return {
        "analysis": "B1",
        "title": "8-kbit/s application-mode sensitivity",
        "created_utc": s3.now(),
        "status": "FROZEN PLAN: sealed before any OPUS_VOIP8 audio is generated. Evaluation recognition needs the "
                  "committed plan, calibration, code freeze and a passed evaluation-bitstream validation.",
        "label": "POST-CONFIRMATION CONFIGURATION SENSITIVITY OF THE TOTAL PENALTY - NOT A NEW DECOMPOSITION, NOT A "
                 "BANDWIDTH CONTROL, NOT AN EQUIVALENCE TEST, NO VOIP BANDWIDTH SHARE",
        "question": "Keeping bitrate, bandwidth, signal hint, frame duration, VBR, complexity, decoder and ASR fixed, "
                    "does changing only OPUS_APPLICATION_AUDIO -> OPUS_APPLICATION_VOIP materially change the total "
                    "ASR penalty of 8 kbit/s Opus?",
        "conditions": {
            REF: "sealed Stage 3 REF outputs (reused)",
            AUDIO8: "the Stage 3 OPUS condition: its sealed outputs are reused, and its bitstreams and waveforms are "
                    "regenerated and must reproduce Stage 3 exactly before recognition",
            VOIP8: "new: the Stage 3 OPUS settings with application = voip (OPUS_APPLICATION_VOIP, 2048); same "
                   "encoder call, Ogg writer, FFmpeg 6.1.1 native decode at 48 kHz and torchaudio resample to 16 kHz; "
                   "no realignment, no gain normalisation",
        },
        "encoder_settings": {AUDIO8: dataclasses.asdict(AUDIO8_SETTINGS), VOIP8: dataclasses.asdict(VOIP8_SETTINGS),
                             "difference": settings_difference(),
                             "not_changed": "the signal hint stays auto (it is NOT set to voice); bitrate 8000 b/s, "
                                            "forced NB, unconstrained VBR, complexity 10, 20 ms frames, no FEC, no DTX, "
                                            "lsb_depth 24, mono"},
        "checks_before_recognition": {
            "K1 AUDIO8 reproduction": "calibration (20) and confirmation (2,174): every regenerated OPUS_AUDIO8 Ogg file "
                                      "and 16 kHz waveform equals the sealed Stage 3 OPUS ogg_sha256 and waveform_sha256",
            "K2 VOIP8 encode": "every utterance encodes and decodes without error; decoded length equals the REF length; "
                               "no NaN or Inf",
            "K3 readback": "for both conditions, every control read back from the encoder after encoding equals the "
                           "requested value, including the application (audio 2049, voip 2048)",
            "K4 packets": "for both conditions every packet is mono, narrowband and 20 ms (the forced settings); the "
                          "packet mode (SILK, hybrid, CELT) is reported, not gated",
            "K5 codec and environment": "libopus 1.4 at the sealed path and hash; environment equal to the plan's",
            "K6 determinism (calibration)": "a second pass reproduces every OPUS_VOIP8 Ogg file and waveform bit for bit",
            "K7 ASR path (calibration, GPU)": "the frozen Stage 3 pipeline reproduces the sealed Stage 3 calibration "
                                              "audio and hypotheses exactly, and OPUS_VOIP8 recognition runs and repeats "
                                              "deterministically on two utterances (no WER is compared)",
            "K8 anchors": f"B1's analysis code reproduces Stage 3's WER(REF), WER(OPUS) and OPUS - REF (estimate and "
                          f"bounds, pooled and per subset) within {ANCHOR_TOLERANCE_PP} pp",
            "K9 procedural": "no OPUS_VOIP8 evaluation WER exists before the plan, calibration, code freeze and "
                             "validation are committed",
            "descriptive only (never a gate)": "payload bitrate distribution; clipping counts; lag against REF; RMS "
                                               "change; LSD 0-3 kHz and coherence 0-3.5 kHz against REF (per utterance, "
                                               "frozen Stage 2B/3 metrics); pooled 4-8 kHz power and 4.1-4.9 kHz mirror "
                                               "coherence (frozen TransferAccumulator). OPUS_VOIP8 is not required to "
                                               "look like OPUS_AUDIO8: the difference is the treatment",
            "on_failure": "B1 is STOPPED before evaluation recognition; the failed check is sealed and reported; no "
                          "other setting is tried under the B1 label",
        },
        "stage3_anchors": stage3_anchors(),
        "recognition": [
            f"{VOIP8} only, once, on the 2,174 Stage 3 confirmation utterances "
            f"({conf['selection_sha256'][:12]}...); REF and OPUS_AUDIO8 reuse the sealed Stage 3 outputs.",
            "Recognisers, checkpoints, decoding options, normalisation and scoring exactly as Stage 3; runner "
            "upgrade_pipeline.run_set (chunks of 8, resumable progress file); each OPUS_VOIP8 waveform must equal its "
            "validated SHA-256.",
            "Cross-run component: Whisper's batches differ from Stage 3's (one condition per chunk); greedy float16 "
            "Whisper is not exactly invariant to batch composition. It is part of V and D_app and is not separated; "
            "wav2vec2 decodes each utterance alone.",
            "GPU: at least 12 GiB free and no other major GPU job at the start; GPU state logged.",
        ],
        "estimands": {
            "A": "WER(OPUS_AUDIO8) - WER(REF) (= Stage 3 OPUS - REF)",
            "V": "WER(OPUS_VOIP8) - WER(REF)",
            "D_app": "WER(OPUS_VOIP8) - WER(OPUS_AUDIO8) (primary, per recogniser, pooled)",
            "secondary": "the same per test subset (uncorrected); CER and S/D/I composition descriptively",
            "not computed": "no VOIP bandwidth share and no VOIP decomposition: no application-matched linear control "
                            "exists or is built",
        },
        "bootstrap": f"Stage 3's paired speaker-cluster bootstrap, unchanged: speakers resampled within test subsets, "
                     f"{N_BOOT:,} replicates, seed {SEED} on the Stage 3 speakers, 95 % percentile intervals, every "
                     f"quantity recomputed in each replicate (upgrade_stats)",
        "outcome_rule": {"classes": list(OUTCOMES),
                         "rule": "per recogniser, pooled D_app: VOIP_LOWER_PENALTY if its 95 % interval lies below "
                                 "zero; VOIP_HIGHER_PENALTY if above zero; NO_CLEAR_APPLICATION_DIFFERENCE otherwise "
                                 "(no equivalence claim); no combined outcome",
                         "implementation": "b1_design.b1_outcome"},
        "manuscript_consequences": {
            "application sensitivity (either recogniser VOIP_LOWER or VOIP_HIGHER)":
                "scope headline claims explicitly to libopus 1.4 / application=audio / forced SILK-NB; do not imply "
                "generic WebRTC deployment behaviour",
            "NO_CLEAR_APPLICATION_DIFFERENCE in both": "state it only as a post-confirmation configuration "
                                                       "sensitivity; no equivalence claim",
        },
        "run_order": [
            "freeze-spec: this plan (after A1 was sealed and committed)",
            "calibrate encode: run_b1.py calibrate encode (K1-K6 on the 20 Stage 3 calibration utterances, CPU)",
            "calibrate asr: run_b1.py calibrate asr (K7, GPU)",
            "freeze-code: B1_CODE_FREEZE.json",
            "commit the plan, calibration and code freeze",
            "validate: run_b1.py validate (K1-K5, K8, K9 on the 2,174 confirmation bitstreams, no ASR)",
            "run: run_b1.py run (OPUS_VOIP8 recognition, once)",
            "analyse: run_b1.py analyse (bootstrap, outcome, B1_DECISION.json)",
        ],
        "outputs": {"calibration": str(CALIBRATION), "validation": str(VALIDATION), "raw": str(RAW),
                    "decision": str(DECISION), "bootstrap": str(BOOTSTRAP)},
        "policies": [
            "No setting, check, data selection or rule is changed after evaluation ASR is seen.",
            "Sealed records are never edited; failures are sealed and reported.",
            "Every outcome, including STOPPED, is reported.",
        ],
        "provenance": {**recorded_inputs(), "git_head_at_freeze": upgrade.git("rev-parse", "HEAD").stdout.strip()},
        "environment": environment(),
        "code_sha256_at_design_freeze": code_hashes(),
    }


def _block(value) -> list[str]:
    if isinstance(value, list):
        return [f"- {v}" for v in value]
    if isinstance(value, dict):
        return [f"- **{k}**: {json.dumps(v) if isinstance(v, (dict, list)) else v}" for k, v in value.items()]
    return [str(value)]


def render(spec: dict) -> str:
    rows = [f"| {asr.MODEL_LABELS[m]} | {s} | " + " | ".join(f"{a[q]['estimate']:.6f}" for q in
                                                              ["wer_REF", "wer_OPUS_AUDIO8", "A"]) + " |"
            for m, scopes in spec["stage3_anchors"].items() for s, a in scopes.items()]
    return "\n".join([
        f"# B1: {spec['title']} - frozen plan", "",
        f"Sealed `B1_SPEC.json` SHA-256 `{spec['spec_sha256']}`, created {spec['created_utc']}.", "",
        f"**Status: {spec['status']}**", "", f"**Label: {spec['label']}**", "",
        "Rendered from `B1_SPEC.json`; the JSON record is authoritative.", "",
        "## 1. Question", "", spec["question"], "",
        "## 2. Conditions and encoder settings", "", *_block(spec["conditions"]), "", *_block(spec["encoder_settings"]), "",
        "## 3. Checks before recognition", "", *_block(spec["checks_before_recognition"]), "",
        "Stage 3 anchors that K8 must reproduce (micro, pp):", "",
        "| Recogniser | Scope | WER REF | WER OPUS (AUDIO8) | OPUS - REF |", "|---|---|---|---|---|", *rows, "",
        "## 4. Recognition", "", *_block(spec["recognition"]), "",
        "## 5. Estimands, bootstrap and outcome rule", "", *_block(spec["estimands"]), "", spec["bootstrap"], "",
        spec["outcome_rule"]["rule"], "",
        "## 6. Manuscript consequences", "", *_block(spec["manuscript_consequences"]), "",
        "## 7. Run order, outputs and policies", "", *_block(spec["run_order"]), "",
        f"Outputs: `{json.dumps(spec['outputs'])}`", "", *_block(spec["policies"]), "",
        "## 8. Provenance and environment", "",
        *[f"- {k}: `{json.dumps(v) if isinstance(v, dict) else v}`" for k, v in spec["provenance"].items()],
        *[f"- {k}: `{json.dumps(v) if isinstance(v, dict) else v}`" for k, v in spec["environment"].items()], "",
    ])


# ==================================================
# Freeze, check and guards
# ==================================================

def code_hashes() -> dict:
    files = B1_CODE_FILES + OTHER_CODE_USED + list(s3.CODE_FILES)
    return {str(p): (s3.file_sha256(p) if p.exists() else None) for p in files}


def inputs_unchanged(spec: dict) -> None:
    current = recorded_inputs()
    changed = sorted(k for k, v in current.items() if spec["provenance"].get(k) != v)
    if changed:
        raise RuntimeError(f"B1 inputs changed since the plan: {changed}")
    if s3.native(stage3_anchors()) != spec["stage3_anchors"]:
        raise RuntimeError("Stage 3 anchors differ from the B1 plan")
    upgrade.stage3_integrity()


def environment_differences(spec: dict) -> list[str]:
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
        raise RuntimeError("B1 plan changed since the code freeze")
    current = code_hashes()
    changed = sorted(f for f, digest in freeze["code_sha256"].items() if current.get(f) != digest)
    if changed:
        raise RuntimeError(f"B1 code changed since the code freeze: {changed}")
    if committed:
        upgrade.tracked_and_clean(CODE_FREEZE)
    return spec, freeze


def freeze_spec() -> None:
    if SPEC_JSON.exists() or PLAN_MD.exists():
        raise RuntimeError("the B1 plan is already frozen")
    if any(p.exists() for p in [CALIBRATION, VALIDATION, RAW]):
        raise RuntimeError("B1 outputs exist: the plan must precede every B1 step")
    upgrade.tracked_and_clean(A1_DECISION)       # the pass order: A1 is sealed and committed first
    digest = s3.write_sealed(SPEC_JSON, s3.native(build_spec()), "spec_sha256")
    PLAN_MD.write_text(render(s3.read_sealed(SPEC_JSON, "spec_sha256")))
    print(f"B1 spec sha256 {digest}")


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
    reports = {name: s3.read_sealed(path, "report_sha256") for name, path in CALIBRATION_PARTS.items()}
    failed = [n for n, r in reports.items() if not r["pass"] or r["spec_sha256"] != spec["spec_sha256"]]
    if failed:
        raise RuntimeError(f"B1 calibration did not pass ({failed}); the code cannot be frozen")
    current = code_hashes()
    missing = sorted(f for f, d in current.items() if d is None)
    if missing:
        raise RuntimeError(f"code files missing: {missing}")
    at_design = spec["code_sha256_at_design_freeze"]
    digest = s3.write_sealed(CODE_FREEZE, {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
        "calibration_report_sha256": {n: r["report_sha256"] for n, r in reports.items()},
        "code_sha256": current,
        "code_added_since_design_freeze": sorted(f for f in current if at_design.get(f) is None),
        "code_changed_since_design_freeze": sorted(f for f in current if at_design.get(f) not in (None, current[f])),
    }, "freeze_sha256")
    print(f"B1 code freeze sealed: {digest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["freeze-spec", "check", "freeze-code"])
    args = parser.parse_args()
    os.chdir(ROOT)
    {"freeze-spec": freeze_spec, "check": check, "freeze-code": freeze_code}[args.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
