"""
TASLP upgrade: sealed amendments to the frozen plan.

upgrade_spec.json and 00_UPGRADE_PLAN.md are never edited. An amendment is a new, dated,
sealed record, paper/taslp_upgrade/amendments/amendment_NN_<date>.json (key
amendment_sha256), rendered to a Markdown file of the same name. It quotes the plan text it
supersedes and gives the replacement, the approval, the reason, the sealed evidence and the
SHA-256 of every plan section it leaves unchanged. Plan section 6: a change made before the
step it affects needs explicit approval and a sealed amendment record.

    python paper/taslp_upgrade/upgrade_amendments.py seal 01

    01  2026-09-26, after U1 and before the code freeze (U2): corrects the
        wav2vec2-base-960h expectation of section 3.5 and reclassifies the U1
        supplementary check A_wav2vec2_scale_invariance from a freeze gate to a
        descriptive calibration finding.
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import pandas as pd         # noqa: E402

import run_stage3 as s3     # noqa: E402
import upgrade_design as design  # noqa: E402


THIS_FILE = design.UPGRADE / "upgrade_amendments.py"
AMENDMENTS = design.UPGRADE / "amendments"
U1_RUN1_REPORT = design.CALIBRATION_REPORT.parent / "checks" / "checks_report.json"


# ==================================================
# Plan sections
# ==================================================

def section_sha256(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def plan_sections(spec: dict) -> dict:
    """Every section of the sealed plan: top-level keys, the keys of A and B, each analytic expectation."""
    sections = {}
    for key, value in spec.items():
        if key == "spec_sha256":
            continue
        if key not in ("A", "B"):
            sections[key] = value
            continue
        for sub, item in value.items():
            if sub == "analytic_expectations":
                sections.update({f"{key}.{sub}[{i}]": text for i, text in enumerate(item)})
            else:
                sections[f"{key}.{sub}"] = item
    return sections


# ==================================================
# Amendment 01: the wav2vec2 expectation of section 3.5
# ==================================================

CHECK_01 = "A_wav2vec2_scale_invariance"
GROUPNORM_EPS = 1e-5        # wav2vec2-base-960h feature_extractor.conv_layers[0].layer_norm, as section 3.5


def amendment_01(spec: dict) -> dict:
    if design.CODE_FREEZE.exists() or any((design.RESULTS / s).exists() for s in ["sweep", "level"]):
        raise RuntimeError("amendment 01 precedes the code freeze and every evaluation step")
    if design.code_hashes() != spec["code_sha256_at_design_freeze"]:
        raise RuntimeError("code changed since the design freeze")
    calibration = s3.read_sealed(design.CALIBRATION_REPORT, "report_sha256")
    run1 = s3.read_sealed(U1_RUN1_REPORT, "report_sha256")
    for name, digest in run1["files"].items():
        if s3.file_sha256(U1_RUN1_REPORT.parent / name) != digest:
            raise RuntimeError(f"{name} differs from the sealed U1 run-1 report")
    if run1["verdict"] != "FAIL" or run1["failed"] != [CHECK_01]:
        raise RuntimeError(f"amendment 01 answers a U1 run-1 FAIL on {CHECK_01} alone")
    item = "A.analytic_expectations[0]"
    original = plan_sections(spec)[item]
    if not original.startswith("wav2vec2-base-960h") or "by construction" not in original:
        raise RuntimeError(f"{item} is not the wav2vec2 expectation")

    created = s3.now()
    w, gain = run1["level"]["wav2vec2"], run1["level"]["gain_db"]
    unchanged_hypotheses, utterances = map(int, w["hypotheses_identical"].split("/"))
    changed_frames, frames = map(int, w["frames_argmax_changed"].split("/"))
    variance = pd.read_csv(U1_RUN1_REPORT.parent / "level_rows.csv")["w2v_conv_min_channel_variance"]
    replacement = (
        f"wav2vec2-base-960h (amendment 01, {created[:10]}): the torchaudio bundle does not normalise the "
        "waveform; its first convolution has no bias and is followed by GroupNorm with one channel per group "
        "and epsilon 1e-5. Because epsilon is nonzero, a per-utterance scalar gain is removed only "
        "approximately: where a channel's variance is small relative to epsilon, the normalisation divides by "
        "about the square root of epsilon instead of by the channel's standard deviation, and gain information "
        f"persists. On the Stage 3 calibration set, level matching left {unchanged_hypotheses} of {utterances} "
        f"wav2vec2 hypotheses unchanged and changed the most probable label in {changed_frames} of {frames:,} "
        "frames. wav2vec2-base-960h is therefore approximately, not exactly, level-invariant: for wav2vec2, A is "
        "informative about level, its result is interpreted normally, and no outcome is expected by construction."
    )
    statement = [
        "The original expectation in plan section 3.5, that wav2vec2-base-960h removes a per-utterance scalar "
        "gain in its first-layer normalisation, so that for wav2vec2 addition A would be uninformative about "
        "level and a GO would be reported as expected by construction, was incorrect.",
        f"Calibration showed approximate, not exact, level invariance. On the {utterances} utterances of the "
        "Stage 3 calibration set (dev-clean; U1, before any evaluation utterance was encoded, decoded or "
        f"recognised), matching the RMS level of OPUS to that of LP (gains {gain['min']:+.2f} to "
        f"{gain['max']:+.2f} dB) left {unchanged_hypotheses} of {utterances} wav2vec2-base-960h hypotheses "
        f"unchanged, changed the most probable CTC label in {changed_frames} of {frames:,} frames and changed "
        f"the output logits by up to {w['max_emissions_abs_diff']:.1f}.",
        "The deviation arises from the nonzero epsilon (1e-5) of the model's first-layer normalisation, a "
        "GroupNorm with one channel per group that follows a convolution without bias. Where a channel's "
        "variance is small relative to epsilon, the normalisation divides by about the square root of epsilon "
        "instead of by the channel's standard deviation, so gain information persists in sufficiently "
        "low-variance channels. In every calibration utterance the lowest first-layer channel variance "
        f"({variance.min():.1e} to {variance.max():.1e}) was far below epsilon; the normalised first-layer "
        f"output changed by up to {w['max_groupnorm_abs_diff']:.2f} with epsilon 1e-5, and by at most "
        f"{w['max_groupnorm_abs_diff_eps0']:.1e} (float32 rounding of the level-matched input) with epsilon "
        "set to 0.",
        "Therefore the wav2vec2 level-matched result (L and K for wav2vec2-base-960h) is scientifically "
        "informative and is interpreted normally, as the Whisper result is, under the unchanged rules and "
        "manuscript consequences of sections 3.6 and 3.7; it is not treated as a predetermined sanity-null.",
        "This correction changes no estimand, gate, decision threshold, condition, dataset selection or "
        "analysis rule. upgrade_spec.json and 00_UPGRADE_PLAN.md are not edited: only the first analytic "
        "expectation of section 3.5 is superseded, by the replacement text of this amendment, and the SHA-256 "
        "of every other section of the plan is recorded here.",
        f"The U1 supplementary check {CHECK_01} (paper/taslp_upgrade/pre_run_checks.py; pass criterion: every "
        "calibration hypothesis of wav2vec2-base-960h identical with and without level matching, first "
        "convolution without bias, GroupNorm with one channel per group), which tested the superseded "
        "expectation, is reclassified from a freeze gate to a descriptive calibration finding. It is still "
        "computed and reported in every later U1 run, and it gates neither the code freeze nor any later step. "
        "The U1 run-1 report (verdict FAIL) is preserved unchanged as historical provenance.",
    ]
    return {
        "amendment": "01", "date": created[:10], "created_utc": created,
        "title": "Correction of the wav2vec2-base-960h level-invariance expectation (plan section 3.5)",
        "approval": f"Explicitly approved by the study owner on {created[:10]}, choosing option 1 after the U1 "
                    "run-1 FAIL report, before the code freeze (U2) and before any evaluation step.",
        "amends": {"record": str(design.SPEC_JSON), "spec_sha256": spec["spec_sha256"],
                   "plan_markdown": str(design.PLAN_MD), "plan_markdown_sha256": s3.file_sha256(design.PLAN_MD),
                   "section": "3.5 Analytic expectations (not tests)", "item": item,
                   "original_text": original, "replacement_text": replacement},
        "statement": statement,
        "reclassified_checks": [{
            "check": CHECK_01, "defined_in": "paper/taslp_upgrade/pre_run_checks.py (U1 supplementary checks)",
            "criterion": "every calibration hypothesis of wav2vec2-base-960h identical with and without level "
                         "matching; first convolution without bias; GroupNorm with one channel per group",
            "from": "freeze gate", "to": "descriptive calibration finding",
            "run1_value": run1["checks"][CHECK_01]}],
        "reason": f"The U1 supplementary checks (run 1) failed only {CHECK_01}. That check tested an analytic "
                  "expectation of section 3.5, which the plan states is not a test and does not enter the "
                  "rules; it did not test the pipeline: every pipeline gate passed and the level-matching "
                  "transform behaved exactly as specified. Left uncorrected, section 3.5 would present the "
                  "wav2vec2 outcome of addition A as predetermined. The amendment is made after U1, before the "
                  "code freeze (U2) and before any evaluation utterance was encoded, decoded or recognised; "
                  "under plan section 6 it therefore applies to every later step.",
        "applies_to": "U2 onwards. The evaluation steps U3-U8 run under the unchanged plan; the interpretation "
                      "of the wav2vec2 result of addition A (U8) and the manuscript revision after U8 follow "
                      "the replacement text.",
        "evidence": {
            "set": f"Stage 3 calibration selection, {run1['isolation']['n_utterances']} "
                   f"{'/'.join(run1['isolation']['subsets'])} utterances, {run1['isolation']['n_speakers']} "
                   f"speakers (selection_sha256 {run1['isolation']['selection_sha256']}); no evaluation utterance",
            "u1_calibration_report": {"path": str(design.CALIBRATION_REPORT),
                                      "report_sha256": calibration["report_sha256"],
                                      "E1_pass": calibration["E1"]["pass"], "E2_pass": calibration["E2"]["pass"]},
            "u1_checks_run1": {"path": str(U1_RUN1_REPORT), "report_sha256": run1["report_sha256"],
                               "verdict": run1["verdict"], "failed": run1["failed"],
                               "level_rows_sha256": run1["files"]["level_rows.csv"]},
            "level_matching_gain_db": gain,
            "wav2vec2_hypotheses_unchanged": w["hypotheses_identical"],
            "wav2vec2_frames_most_probable_label_changed": w["frames_argmax_changed"],
            "wav2vec2_max_abs_logit_difference": w["max_emissions_abs_diff"],
            "first_convolution_max_relative_linearity_error": w["max_conv_linearity_rel_error"],
            "first_layer_normalised_output_max_abs_difference": {
                "epsilon_1e-5": w["max_groupnorm_abs_diff"], "epsilon_0": w["max_groupnorm_abs_diff_eps0"]},
            "lowest_first_layer_channel_variance_per_utterance": {"min": float(variance.min()),
                                                                  "max": float(variance.max())},
            "groupnorm_epsilon": GROUPNORM_EPS,
        },
        "unchanged": {
            "statement": "Every section of upgrade_spec.json except the superseded item, by the SHA-256 of its "
                         "JSON (json.dumps, sort_keys=True); no code file changed since the design freeze.",
            "plan_sections_sha256": {k: section_sha256(v) for k, v in plan_sections(spec).items() if k != item},
            "code_unchanged_since_design_freeze": True,
        },
    }


BUILDERS = {"01": amendment_01}


# ==================================================
# Sealed records
# ==================================================

def paths() -> list[Path]:
    return sorted(AMENDMENTS.glob("amendment_*.json"))


def load_all() -> list[dict]:
    """Every sealed amendment, oldest first, checked against the sealed plan it amends."""
    if not paths():
        return []
    spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")
    sections = plan_sections(spec)
    records = []
    for path in paths():
        record = s3.read_sealed(path, "amendment_sha256")
        amends, unchanged = record["amends"], record["unchanged"]["plan_sections_sha256"]
        if amends["spec_sha256"] != spec["spec_sha256"] or sections[amends["item"]] != amends["original_text"]:
            raise RuntimeError(f"{path} amends a different plan")
        if {k: section_sha256(sections[k]) for k in unchanged} != unchanged or \
                set(unchanged) | {amends["item"]} != set(sections):
            raise RuntimeError(f"{path}: the plan differs from the sections recorded as unchanged")
        records.append(record)
    return records


def sealed_paths() -> dict[str, str]:
    return {str(p): "amendment_sha256" for p in paths()}


def reclassified_checks() -> dict[str, dict]:
    """U1 check -> the sealed amendment that reclassified it from a freeze gate to a descriptive finding."""
    return {item["check"]: {"amendment": record["amendment"], "amendment_sha256": record["amendment_sha256"],
                            "classification": item["to"]}
            for record in load_all() for item in record.get("reclassified_checks", [])}


def render(record: dict) -> str:
    a, e = record["amends"], record["evidence"]
    lines = [
        f"# Amendment {record['amendment']} to the TASLP upgrade plan ({record['date']})", "",
        f"Sealed `amendment_{record['amendment']}_{record['date']}.json` SHA-256 `{record['amendment_sha256']}`, "
        f"created {record['created_utc']}. This file is rendered from that record; the JSON record is "
        "authoritative.", "",
        f"**{record['title']}.** Amends `{a['record']}` (spec SHA-256 `{a['spec_sha256']}`), section "
        f"{a['section']}, item `{a['item']}`. The plan files are not edited.", "",
        f"**Approval.** {record['approval']}", "",
        "## Amendment", "", *[f"{i}. {s}" for i, s in enumerate(record["statement"], 1)], "",
        "## Superseded text", "", f"> {a['original_text']}", "",
        "## Replacement text", "", f"> {a['replacement_text']}", "",
        "## Reclassified U1 check", "",
        *[f"- `{c['check']}` ({c['defined_in']}): {c['from']} -> {c['to']}. Criterion: {c['criterion']}. "
          f"Run-1 value: {c['run1_value']}." for c in record["reclassified_checks"]], "",
        "## Reason", "", record["reason"], "",
        "## Applies to", "", record["applies_to"], "",
        "## Evidence (sealed U1 records; Stage 3 calibration set only)", "",
        *[f"- {k}: `{json.dumps(v)}`" for k, v in e.items()], "",
        "## Unchanged", "", record["unchanged"]["statement"], "",
        "| Plan section | SHA-256 |", "|---|---|",
        *[f"| `{k}` | `{v}` |" for k, v in record["unchanged"]["plan_sections_sha256"].items()], "",
    ]
    return "\n".join(lines)


def seal(number: str) -> None:
    spec = design.require_frozen_plan()
    if any(p.name.startswith(f"amendment_{number}_") for p in paths()):
        raise RuntimeError(f"amendment {number} is sealed and exists")
    record = BUILDERS[number](spec)
    path = AMENDMENTS / f"amendment_{number}_{record['date']}.json"
    digest = s3.write_sealed(path, record, "amendment_sha256")
    path.with_suffix(".md").write_text(render(s3.read_sealed(path, "amendment_sha256")))
    print(f"amendment {number} sealed: {path}, amendment_sha256 {digest}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["seal"])
    parser.add_argument("number", choices=sorted(BUILDERS))
    args = parser.parse_args()
    os.chdir(design.REPO_ROOT)
    seal(args.number)
    return 0


if __name__ == "__main__":
    sys.exit(main())
