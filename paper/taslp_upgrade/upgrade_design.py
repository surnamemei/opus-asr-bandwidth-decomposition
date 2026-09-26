"""
TASLP-upgrade design: the frozen plan for two additions to the closed Stage 3 study.

    A  OPUS level-matched sensitivity: a post-confirmation sensitivity analysis on
       the Stage 3 confirmation set, not a second confirmatory test
    B  forced SILK-NB bitrate sweep: pre-registered, on fresh utterances (a
       fresh-utterance, not fresh-speaker, holdout)

Commands (this file encodes, decodes and recognises nothing):

    select        seal paper/taslp_upgrade/selection_sweep.json. Inputs: LibriSpeech
                  file names, FLAC header durations, reference transcripts (non-empty
                  rule only), provenance/used_test_utterances.json and this
                  repository's results_paper/ (exclusions only). No audio samples.
    freeze-spec   seal paper/taslp_upgrade/upgrade_spec.json and render
                  00_UPGRADE_PLAN.md from it. Reads only sealed Stage 3 files.
    freeze-code   (after the calibration step) seal results_paper/taslp_upgrade/
                  code_freeze.json; required by every evaluation command.

The runners (run_bitrate_sweep.py, run_level_sensitivity.py) call
require_frozen_plan() / require_code_freeze() before doing anything.
"""

import argparse
import csv
import json
import math
import os
import random
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import opus_direct          # noqa: E402
import run_stage3 as s3     # noqa: E402
import stage3_asr as asr    # noqa: E402
import stage3_audio as audio  # noqa: E402
import upgrade_pipeline as pipe  # noqa: E402
import upgrade_stats as ustats   # noqa: E402


# ==================================================
# Paths (relative to the repository root)
# ==================================================

REPO_ROOT = HERE.parents[1]
UPGRADE = Path("paper") / "taslp_upgrade"
SPEC_JSON = UPGRADE / "upgrade_spec.json"
PLAN_MD = UPGRADE / "00_UPGRADE_PLAN.md"
SELECTION = UPGRADE / "selection_sweep.json"
SELECTION_CSV = UPGRADE / "selection_sweep.csv"
USED = Path("provenance") / "used_test_utterances.json"
RESULTS = Path("results_paper") / "taslp_upgrade"
CODE_FREEZE = RESULTS / "code_freeze.json"
CALIBRATION_REPORT = RESULTS / "calibration" / "calibration_report.json"

S3 = Path("results_paper") / "stage3_asr"
S3_FREEZE = S3 / "confirmation_freeze.json"
S3_DECISION = S3 / "stage3_decision.json"
S3_BOOTSTRAP = S3 / "07_paired_bootstrap.csv"
S3_CONFIRMATION = S3 / "raw" / "confirmation"
S3_CALIBRATION = S3 / "calibration"

UPGRADE_CODE_FILES = [UPGRADE / name for name in [
    "upgrade_design.py", "upgrade_stats.py", "upgrade_pipeline.py",
    "run_bitrate_sweep.py", "run_level_sensitivity.py",
]]

# ==================================================
# Frozen design constants (data and gates; analysis constants: upgrade_stats.py)
# ==================================================

SWEEP_SUBSETS = ["test-clean", "test-other"]
SWEEP_SEED = 53054                 # Stage 3 used 53051-53053 for its selections
SWEEP_MAX_PER_SPEAKER = 30         # the Stage 3 confirmation rule
SCAN_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".txt"}
ID_PATTERN = re.compile(r"\b(\d{1,4})-(\d{1,6})-(\d{4})\b")

BITRATE_TOLERANCE = 0.15           # V2: |median payload / nominal - 1| <= 15 %
MIN_ADJACENT_RATIO = 1.2           # V2: medians strictly increasing, adjacent ratio >= 1.2
LEVEL_TOLERANCE_DB = 1e-3          # A2
GAIN_REPRODUCTION_TOLERANCE_DB = 1e-6  # A3


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


# ==================================================
# Integrity of the closed Stage 3 study
# ==================================================

def stage3_integrity() -> dict:
    """Stage 3 code, seals and output manifests unchanged; returns their identifiers."""
    freeze = s3.read_sealed(S3_FREEZE, "freeze_sha256")
    changed = [f for f, h in freeze["code_sha256"].items() if s3.file_sha256(Path(f)) != h]
    if changed:
        raise RuntimeError(f"Stage 3 code differs from its confirmation freeze: {changed}")
    spec = s3.read_sealed(s3.SPEC_JSON, "spec_sha256")
    decision = s3.read_sealed(S3_DECISION, "decision_sha256")
    if s3.file_sha256(S3_BOOTSTRAP) != decision["bootstrap_sha256"]:
        raise RuntimeError("07_paired_bootstrap.csv differs from the sealed Stage 3 decision")
    manifests = {}
    for name, directory in [("confirmation", S3_CONFIRMATION), ("calibration", S3_CALIBRATION)]:
        record = s3.read_sealed(directory / "outputs_sha256.json", "outputs_sha256")
        for filename, digest in record["files"].items():
            if s3.file_sha256(directory / filename) != digest:
                raise RuntimeError(f"{directory / filename} differs from its sealed manifest")
        manifests[name] = record["outputs_sha256"]
    selections = {s: s3.load_selection(s)["selection_sha256"] for s in ["calibration", "confirmation"]}
    if selections["confirmation"] != spec["data"]["selections"]["confirmation"]["sha256"]:
        raise RuntimeError("confirmation selection differs from the Stage 3 spec")
    return {
        "stage3_spec_sha256": spec["spec_sha256"],
        "stage3_confirmation_freeze_sha256": freeze["freeze_sha256"],
        "stage3_decision_sha256": decision["decision_sha256"],
        "stage3_decision": decision["decision"],
        "stage3_bootstrap_csv_sha256": decision["bootstrap_sha256"],
        "stage3_confirmation_outputs_sha256": manifests["confirmation"],
        "stage3_calibration_outputs_sha256": manifests["calibration"],
        "stage3_confirmation_selection_sha256": selections["confirmation"],
        "stage3_calibration_selection_sha256": selections["calibration"],
        "stage3_code_files_verified": len(freeze["code_sha256"]),
        "frozen_lp_taps_sha256": audio.FROZEN_LP_SHA256,
        "stage3_requirements_lock_sha256": spec["requirements_lock_sha256"],
    }


def used_record() -> dict:
    record = s3.read_sealed(USED, "record_sha256")
    if record["stage3_confirmation_selection_sha256"] != s3.load_selection("confirmation")["selection_sha256"]:
        raise RuntimeError("used-utterance record refers to a different Stage 3 confirmation selection")
    return record


# ==================================================
# Guards used by the runners
# ==================================================

def tracked_and_clean(path: Path) -> None:
    if git("ls-files", "--error-unmatch", str(path)).returncode != 0:
        raise RuntimeError(f"{path} is not committed; commit the frozen plan first")
    if git("diff", "--quiet", "HEAD", "--", str(path)).returncode != 0:
        raise RuntimeError(f"{path} differs from the committed version")


def require_frozen_plan() -> dict:
    """The sealed, committed plan, with selection and provenance record unchanged."""
    spec = s3.read_sealed(SPEC_JSON, "spec_sha256")
    for path in [SPEC_JSON, SELECTION, USED]:
        tracked_and_clean(path)
    if s3.read_sealed(SELECTION, "selection_sha256")["selection_sha256"] != spec["B"]["data"]["sha256"]:
        raise RuntimeError("sweep selection differs from the frozen plan")
    if used_record()["record_sha256"] != spec["provenance"]["used_test_utterances_sha256"]:
        raise RuntimeError("used-utterance record differs from the frozen plan")
    stage3_integrity()
    return spec


def code_hashes() -> dict[str, str]:
    return {str(p): s3.file_sha256(p) for p in UPGRADE_CODE_FILES + list(s3.CODE_FILES)}


def require_code_freeze() -> tuple[dict, dict]:
    spec = require_frozen_plan()
    freeze = s3.read_sealed(CODE_FREEZE, "freeze_sha256")
    if freeze["spec_sha256"] != spec["spec_sha256"]:
        raise RuntimeError("plan changed since the code freeze")
    current = code_hashes()
    changed = sorted(f for f in freeze["code_sha256"] if freeze["code_sha256"][f] != current.get(f))
    if changed:
        raise RuntimeError(f"code changed since the code freeze: {changed}")
    return spec, freeze


# ==================================================
# select: fresh test utterances for the sweep (metadata only)
# ==================================================

def ids_in_csv(path: Path, walkers: dict[str, list[str]]) -> set[str]:
    ids = set()
    with path.open(newline="", errors="ignore") as file:
        reader = csv.DictReader(file)
        fields = set(reader.fieldnames or [])
        by_parts = {"speaker_id", "chapter_id", "utterance_id"} <= fields
        by_index = {"dataset", "dataset_index"} <= fields
        if not (by_parts or by_index):
            return ids
        for row in reader:
            try:
                if by_parts:
                    ids.add(f"{int(float(row['speaker_id']))}-{int(float(row['chapter_id']))}-"
                            f"{int(float(row['utterance_id'])):04d}")
                if by_index and row["dataset"] in walkers:
                    ids.add(walkers[row["dataset"]][int(float(row["dataset_index"]))])
            except (ValueError, KeyError, IndexError):
                continue
    return ids


def scan_repository_outputs(test_ids: set[str], walkers: dict[str, list[str]]) -> dict[str, list[str]]:
    """Test utterances named in this repository's results_paper/ (upgrade outputs excluded)."""
    sources = {}
    for path in sorted(Path("results_paper").rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES or RESULTS in path.parents:
            continue
        found = {"-".join(m) for m in ID_PATTERN.findall(path.read_text(errors="ignore"))}
        if path.suffix == ".csv":
            found |= ids_in_csv(path, walkers)
        found &= test_ids
        if found:
            sources[str(path)] = sorted(found)
    return sources


def select() -> None:
    if SELECTION.exists():
        raise RuntimeError(f"{SELECTION} is sealed and exists")
    integrity = stage3_integrity()
    used = used_record()
    normaliser = asr.Normaliser()
    sex = s3.speaker_sex()
    listings = {s: s3.list_subset(s) for s in SWEEP_SUBSETS}
    walkers = {s: sorted(listings[s]["utterance"]) for s in SWEEP_SUBSETS}
    test_ids = set().union(*walkers.values())
    if {s: len(v) for s, v in walkers.items()} != used["librispeech_test_utterances"]:
        raise RuntimeError("LibriSpeech test listing differs from the provenance record")

    recorded = set(used["all_used_test_utterances"])
    local = scan_repository_outputs(test_ids, walkers)
    local_ids = set().union(*map(set, local.values()))
    excluded = recorded | local_ids
    confirmation_utterances = s3.load_selection("confirmation")["utterances"]
    confirmation = {u["utterance"] for u in confirmation_utterances}
    if not confirmation <= excluded or not set(used["prior_study"]) <= excluded:
        raise RuntimeError("exclusions miss a known selection")

    def eligible(frame):
        ok = (frame["duration_s"] <= asr.MAX_DURATION_S) & ~frame["utterance"].isin(excluded)
        ok &= frame["reference"].map(lambda t: normaliser(t).strip() != "")
        return frame[ok]

    rng = random.Random(SWEEP_SEED)
    parts, reserve, exhausted, too_long = [], {}, {}, {}
    for s in SWEEP_SUBSETS:
        unused = listings[s][~listings[s]["utterance"].isin(excluded)]
        too_long[s] = int((unused["duration_s"] > asr.MAX_DURATION_S).sum())
        frame = eligible(listings[s])
        chosen_here = 0
        for speaker in sorted(frame["speaker_id"].unique()):
            pool = sorted(frame[frame["speaker_id"] == speaker]["utterance"])
            k = min(SWEEP_MAX_PER_SPEAKER, len(pool))
            parts.append(frame[frame["utterance"].isin(sorted(rng.sample(pool, k)))])
            chosen_here += k
        reserve[s] = int(len(frame) - chosen_here)
        exhausted[s] = sorted(int(x) for x in set(listings[s]["speaker_id"]) - set(frame["speaker_id"]))
    chosen = pd.concat(parts).sort_values(["subset", "speaker_id", "utterance"])
    if set(chosen["utterance"]) & excluded:
        raise RuntimeError("selection overlaps an excluded utterance")
    n_words = chosen["reference"].map(lambda t: len(normaliser(t).split()))

    rules = {
        "set": "sweep (TASLP-upgrade addition B)",
        "holdout_type": "FRESH-UTTERANCE, NOT FRESH-SPEAKER: every selected utterance is new to the "
                        "project, but every selected speaker also appears in the Stage 3 confirmation "
                        "set (and in the prior study)",
        "rule": f"test-clean + test-other, every speaker with an eligible utterance, up to "
                f"{SWEEP_MAX_PER_SPEAKER} utterances each (random.Random({SWEEP_SEED}), speakers in sorted "
                "order, subsets in the order test-clean, test-other; the Stage 3 confirmation rule)",
        "eligibility": f"duration <= {asr.MAX_DURATION_S} s (Whisper window); non-empty normalised "
                       "reference; not excluded",
        "exclusions": "every test utterance in provenance/used_test_utterances.json (prior study, Stage 3 "
                      "confirmation, other development outputs) and every test utterance named in this "
                      "repository's results_paper/",
        "selection_inputs": "file names, FLAC header durations, reference transcripts (non-empty rule only), "
                            "exclusion records; no audio samples, no codec, no ASR output",
    }
    utterances = json.loads(chosen[["subset", "utterance", "speaker_id", "chapter_id", "path",
                                    "duration_s", "sample_rate", "reference"]].to_json(orient="records"))
    digest = s3.write_sealed(SELECTION, {
        "set": "sweep", "created_utc": s3.now(), "seed": SWEEP_SEED, "rules": rules,
        "stage3_integrity": integrity,
        "used_test_utterances_sha256": used["record_sha256"],
        "n_utterances": len(utterances), "n_speakers": int(chosen["speaker_id"].nunique()),
        "subsets": chosen["subset"].value_counts().to_dict(),
        "speakers_by_subset": chosen.groupby("subset")["speaker_id"].nunique().to_dict(),
        "sex_by_speaker": pd.Series({sp: sex[sp] for sp in chosen["speaker_id"].unique()})
                            .value_counts().to_dict(),
        "duration_hours": float(chosen["duration_s"].sum() / 3600),
        "normalised_reference_words": int(n_words.sum()),
        "speakers_also_in_stage3_confirmation":
            int(len(set(chosen["speaker_id"]) & {u["speaker_id"] for u in confirmation_utterances})),
        "chapters": int(chosen["chapter_id"].nunique()),
        "chapters_also_in_stage3_confirmation":
            int(len(set(chosen["chapter_id"]) & {u["chapter_id"] for u in confirmation_utterances})),
        "exclusion_counts": {**used["counts"], "local_results_paper": len(local_ids),
                             "local_not_in_record": len(local_ids - recorded), "union": len(excluded)},
        "unused_but_longer_than_30_s": too_long,
        "eligible_not_selected_reserve": reserve,
        "speakers_without_eligible_utterances": exhausted,
        "design_code_sha256": {str(p): s3.file_sha256(p) for p in UPGRADE_CODE_FILES if p.exists()},
        "utterances": utterances,
    }, "selection_sha256")
    chosen.assign(sex=chosen["speaker_id"].map(sex))[
        ["subset", "speaker_id", "sex", "chapter_id", "utterance", "duration_s", "path", "reference"]
    ].to_csv(SELECTION_CSV, index=False)
    print(f"sweep: {len(utterances)} utterances, {chosen['speaker_id'].nunique()} speakers, "
          f"{chosen['duration_s'].sum() / 3600:.2f} h, sha256 {digest}")


# ==================================================
# Anchors from the frozen Stage 3 files (read-only)
# ==================================================

def stage3_anchors() -> dict:
    boot = pd.read_csv(S3_BOOTSTRAP)

    def cell(model, quantity):
        row = boot[(boot["set"] == "confirmation") & (boot["model"] == model) &
                   (boot["scope"] == "pooled") & (boot["kind"] == "micro") &
                   (boot["quantity"] == quantity)].iloc[0]
        return {"estimate": float(row["estimate"]), "ci": [float(row["ci_lower"]), float(row["ci_upper"])]}

    span = math.log2(ustats.SWEEP_RATES_KBPS[-1] / ustats.SWEEP_RATES_KBPS[0])
    anchors = {}
    for model in ustats.MODELS:
        t, u, v = (cell(model, q) for q in ["delta_opus_residual", "delta_silk_residual", "opus_minus_silk"])
        s_star = (u["estimate"] - t["estimate"]) / span
        anchors[model] = {
            "T_star": t, "U_star": u, "V_star": v, "S_star": s_star,
            "B_meaningful_decline_threshold": ustats.B_SLOPE_FRACTION * s_star,
            "A_go_threshold_K_lower": -ustats.A_GO_FRACTION * t["estimate"],
            "A_falsify_threshold_K_upper": -ustats.A_FALSIFY_FRACTION * t["estimate"],
        }
    return anchors


def expected_gains() -> dict:
    manifest = pd.read_csv(S3_CONFIRMATION / "audio_manifest.csv")
    level = manifest.pivot(index="utterance", columns="condition", values="output_rms_dbfs")
    gain = (level["LP"] - level["OPUS"]).to_numpy()
    opus = manifest[manifest["condition"] == "OPUS"]
    return {
        "source": "Stage 3 confirmation audio_manifest.csv (sealed): output_rms_dbfs(LP) - output_rms_dbfs(OPUS)",
        "n": int(gain.size), "median_db": float(np.median(gain)),
        "p05_db": float(np.quantile(gain, 0.05)), "p95_db": float(np.quantile(gain, 0.95)),
        "min_db": float(gain.min()), "max_db": float(gain.max()),
        "utterances_with_gain_below_0_db": int(np.sum(gain < 0)),
        "stage3_opus_utterances_with_samples_at_or_above_full_scale": int(np.sum(opus["clip_count"] > 0)),
        "whisper_log_mel_offset_median": float(np.median(gain) / 40.0),
        "whisper_log_mel_offset_max": float(gain.max() / 40.0),
    }


def settings_table() -> dict:
    table = {name: asdict(s) for name, s in pipe.SWEEP_SETTINGS.items()}
    stage3_opus, stage3_silk = asdict(audio.CODEC_SETTINGS["OPUS"]), asdict(audio.CODEC_SETTINGS["SILK"])
    if table["SILK40"] != stage3_silk:
        raise RuntimeError("SILK40 must equal the Stage 3 SILK settings")
    if sorted(k for k in stage3_opus if stage3_opus[k] != table["SILK8"][k]) != ["signal"]:
        raise RuntimeError("SILK8 must differ from the Stage 3 OPUS settings only in signal")
    if sorted({k for s in table.values() for k in s if s[k] != table["SILK8"][k]}) != ["bitrate_bps"]:
        raise RuntimeError("sweep settings must differ only in bitrate")
    return table


# ==================================================
# The specification
# ==================================================

def build_spec() -> dict:
    integrity = stage3_integrity()
    used = used_record()
    selection = s3.read_sealed(SELECTION, "selection_sha256")
    confirmation = s3.load_selection("confirmation")
    anchors = stage3_anchors()
    gains = expected_gains()
    settings = settings_table()
    run = "python paper/taslp_upgrade/"
    return {
        "stage": "TASLP upgrade - design freeze",
        "created_utc": s3.now(),
        "status": "PLANNED, NOT RUN. Frozen before any upgrade audio was encoded or decoded and before any "
                  "upgrade ASR run. Inputs read to freeze it: LibriSpeech file names, FLAC header durations "
                  "and reference transcripts (sweep selection), exclusion records, and sealed Stage 3 result "
                  "files (anchors, expected gains). Binding once committed.",
        "scope": [
            "Stage 3 is closed. Its sealed specification, selections, outputs, estimates, intervals and "
            "decision (GO) are final. The upgrade never recomputes, replaces or re-decides them, and the "
            "manuscript is not changed until the upgrade results exist.",
            "Addition A is a POST-CONFIRMATION SENSITIVITY ANALYSIS on the Stage 3 confirmation set. It is "
            "not a second confirmatory test. Its outcome can only qualify the interpretation of the Stage 3 "
            "residual (the level confound); it cannot strengthen the Stage 3 confirmatory claim.",
            "Addition B is a PRE-REGISTERED PROSPECTIVE SWEEP on utterances the project has never encoded, "
            "decoded or recognised. It is a FRESH-UTTERANCE, NOT FRESH-SPEAKER, holdout.",
            "Stage 3 modules are imported unchanged (hashes checked against the Stage 3 confirmation "
            "freeze); upgrade code adds only what the new conditions and estimands require.",
        ],
        "provenance": {**integrity, "used_test_utterances_sha256": used["record_sha256"],
                       "used_test_utterances_development_commit": used["development_repository_commit"],
                       "head_at_freeze": s3.git("rev-parse", "HEAD"),
                       "working_tree_status": s3.git("status", "--porcelain").splitlines(),
                       "libopus": opus_direct.libopus_version(),
                       "environment_rule": "the Stage 3 environment (results_paper/stage3_asr/"
                                           "requirements-lock.txt, libopus 1.4, FFmpeg 6.1.1, same GPU type); "
                                           "verified end to end by gate E1 before any evaluation decoding"},
        "code_sha256_at_design_freeze": code_hashes(),
        "common_pipeline": [
            "Audio: 16 kHz mono float32, length equal to REF; LP = frozen Stage 2B zero-phase low-pass "
            f"(taps SHA-256 {audio.FROZEN_LP_SHA256[:12]}...), applied by paper/lowpass.apply_zero_phase.",
            "Codec path (every Opus condition): direct libopus 1.4 C API (paper/opus_direct.encode; every "
            "control set explicitly and read back), Ogg Opus written by paper/opus_direct (fixed serial, "
            "lookahead as pre-skip, end trim by granule position), decoded by torchaudio.load (FFmpeg 6.1.1 "
            "native decoder) at 48 kHz, resampled to 16 kHz by torchaudio.functional.resample: the steps "
            "of paper/stage3_audio.codec_round_trip.",
            "No re-alignment and no level normalisation of any condition, except the single scalar gain that "
            "defines OPUS8_LEVEL_MATCHED in A. No clipping: samples with |x| >= 1 are passed to the "
            "recognisers unchanged and counted, as in Stage 3.",
            "Recognisers exactly as Stage 3 (paper/stage3_asr.py): Whisper large-v3 at revision "
            f"{asr.WHISPER_REVISION[:12]}..., float16, batch {asr.WHISPER_BATCH_SIZE}, greedy, temperature 0 "
            "without fallback, English, transcribe, no timestamps, no prompt; wav2vec2-base-960h (torchaudio "
            "bundle), float32, greedy CTC, no language model. No adaptation.",
            "Scoring exactly as Stage 3: Whisper EnglishTextNormalizer (pinned tokenizer) on references and "
            "hypotheses; jiwer word and character edit counts; an empty or failed hypothesis counts as all "
            "deletions; no utterance is excluded after decoding.",
            f"Bootstrap exactly as Stage 3 (paper/stage3_stats: PairedSet, bootstrap_weights, "
            f"percentile_interval): speakers resampled with replacement within subset strata, all conditions "
            f"and both recognisers of an utterance kept together, {ustats.N_BOOT:,} replicates, 95 % "
            "percentile intervals. Primary scope: pooled (stratified); per-subset scopes are secondary. "
            "Primary estimator: corpus (micro) WER difference from total edit counts, in percentage points "
            "(pp).",
        ],
        "A": {
            "title": "OPUS level-matched sensitivity",
            "label": "POST-CONFIRMATION SENSITIVITY ANALYSIS - NOT A SECOND CONFIRMATORY TEST",
            "question": "Is the Stage 3 codec-specific residual (OPUS - LP) explained by the lower RMS level of "
                        "the decoded Opus signal (median -0.68 dB relative to REF, against -0.08 dB for LP)?",
            "data": {"selection": "results_paper/stage3_asr/selection_confirmation.json",
                     "sha256": confirmation["selection_sha256"], "n_utterances": confirmation["n_utterances"],
                     "n_speakers": confirmation["n_speakers"], "subsets": confirmation["subsets"],
                     "note": "the same 2,174 utterances; A decodes them a second time, for this sensitivity "
                             "analysis only, and says so wherever A is reported"},
            "conditions": {
                "LP": "frozen LP, regenerated; must be bit-identical to Stage 3 (gate A1)",
                "OPUS": "the Stage 3 OPUS condition (Opus 8 kbit/s, forced NB, signal=auto, Stage 3 encoder "
                        "settings), regenerated through the unchanged stage3_audio.codec_round_trip; Ogg bytes "
                        "and decoded waveform must be bit-identical to Stage 3 (gate A1)",
                ustats.LEVEL_MATCHED: "the decoded OPUS waveform times one scalar gain per utterance, so that "
                                      "its RMS equals that of LP",
            },
            "encoder_settings_opus": asdict(audio.CODEC_SETTINGS["OPUS"]),
            "derivation": [
                "g_u = RMS(LP_u) / RMS(OPUS_u), where RMS(x) = sqrt(mean(x^2)) over every sample of the 16 kHz "
                "float32 waveform exactly as passed to the recognisers, computed in float64 "
                "(upgrade_pipeline.level_match).",
                f"{ustats.LEVEL_MATCHED}_u = float32(g_u * float64(OPUS_u)).",
                "Not applied: re-encoding, decoding of a gain-modified signal, clipping or limiting, "
                "re-alignment (the 1-2 sample OPUS lag is kept), AGC, per-frame or per-band gain, any other "
                "normalisation. LP and OPUS are unchanged.",
            ],
            "expected_gains_from_frozen_stage3": gains,
            "pre_asr_gates": {
                "A1": "For all 2,174 utterances, the regenerated LP waveform_sha256 and the regenerated OPUS "
                      "ogg_sha256 and waveform_sha256 equal the sealed Stage 3 confirmation manifest "
                      "(raw/confirmation/audio_manifest.csv; outputs_sha256 "
                      f"{integrity['stage3_confirmation_outputs_sha256'][:12]}...).",
                "A2": f"For every utterance |20 log10(RMS({ustats.LEVEL_MATCHED}) / RMS(LP))| <= "
                      f"{LEVEL_TOLERANCE_DB} dB; every sample finite; length equal to REF.",
                "A3": "Realised gains equal those implied by the frozen manifest (output_rms_dbfs LP - OPUS) "
                      f"within {GAIN_REPRODUCTION_TOLERANCE_DB} dB for every utterance.",
                "on_failure": "stop before any ASR decoding and report; nothing is decoded until a sealed, "
                              "approved amendment exists",
            },
            "asr": f"conditions decoded, once: LP, OPUS, {ustats.LEVEL_MATCHED}; recognisers and settings as Stage 3",
            "estimands": {
                "primary": f"L_m = WER_micro({ustats.LEVEL_MATCHED}) - WER_micro(LP), pooled, for each "
                           "recogniser m, with LP and the level-matched condition decoded in the same run",
                "secondary": [
                    f"K_m = WER_micro({ustats.LEVEL_MATCHED}) - WER_micro(OPUS): the effect of level matching",
                    "OPUS - LP from the same run (reproduces the Stage 3 residual)",
                    "macro WER, CER and substitution/deletion/insertion composition of L_m and K_m",
                    "per-subset scopes (test-clean, test-other)",
                ],
                "descriptive": [
                    "retained fraction L_m / T*_m (point estimate only)",
                    "per recogniser, the number of utterances whose raw hypothesis differs between OPUS and "
                    f"{ustats.LEVEL_MATCHED}",
                    "gain distribution (dB) and the count of samples with |x| >= 1 in the level-matched condition",
                ],
            },
            "bootstrap": {"seed": ustats.LEVEL_SEED, "replicates": ustats.N_BOOT,
                          "note": "Stage 3's seed on Stage 3's speakers and strata, so bootstrap replicate k "
                                  "resamples exactly the speakers of Stage 3 replicate k"},
            "reproduction_check": "Not a gate. Per recogniser and condition (LP, OPUS), the number of "
                                  "utterances whose raw hypothesis differs from the frozen Stage 3 "
                                  "asr_outputs.csv. If none differs, the same-run OPUS - LP estimate and "
                                  "interval equal the frozen Stage 3 values exactly. Any difference is "
                                  "reported; the primary analysis always uses same-run LP and OPUS.",
            "analytic_expectations": [
                "wav2vec2-base-960h: the torchaudio bundle does not normalise the waveform, but its first "
                "convolution has no bias and is followed by GroupNorm with one channel per group. A "
                "per-utterance scalar gain is therefore removed by that normalisation, up to GroupNorm's "
                "epsilon (1e-5) and float32 rounding. Expected: K near 0 and nearly all wav2vec2 hypotheses "
                "unchanged. For wav2vec2, A is expected to be uninformative about level, and a GO for wav2vec2 "
                "is reported as expected by construction.",
                "Whisper large-v3: the feature extractor does not normalise the waveform; features are log10 "
                "mel power, floored at (maximum - 8), then (x + 4) / 4. A gain of G dB adds the constant G/40 "
                "to every normalised log-mel value of the 30 s window, padding included (the floor moves with "
                "the maximum), up to float rounding and the 1e-10 power floor. Expected offset: median "
                f"{gains['whisper_log_mel_offset_median']:.4f}, maximum {gains['whisper_log_mel_offset_max']:.4f}. "
                "Whisper is not level-invariant, so A is informative for Whisper.",
                "These expectations come from reading the model code. They are not tests and do not enter "
                "the rules.",
            ],
            "anchors": {m: {"T_star": anchors[m]["T_star"],
                            "GO_threshold_K_lower": anchors[m]["A_go_threshold_K_lower"],
                            "FALSIFY_threshold_K_upper": anchors[m]["A_falsify_threshold_K_upper"]}
                        for m in ustats.MODELS},
            "rules": {
                "definitions": "For recogniser m: L_m [L_lo, L_hi] and K_m [K_lo, K_hi] are pooled micro "
                               "estimates with 95 % percentile speaker-bootstrap intervals; T*_m is the frozen "
                               "Stage 3 pooled micro OPUS - LP estimate.",
                "GO_m": f"L_lo > 0 AND K_lo > -{ustats.A_GO_FRACTION} x T*_m: a residual remains after level "
                        "matching, and the interval excludes level matching removing a quarter or more of the "
                        "Stage 3 residual.",
                "FALSIFY_m": f"K_hi < -{ustats.A_FALSIFY_FRACTION} x T*_m: level matching removed more than "
                             "half of the Stage 3 residual, and the interval excludes smaller reductions.",
                "WEAKEN_m": "neither GO_m nor FALSIFY_m (a partial reduction, or too imprecise to decide). A "
                            "missing (NaN) bound never satisfies GO or FALSIFY.",
                "exclusive": "GO_m requires K_lo > -0.25 T*_m and FALSIFY_m requires K_hi < -0.5 T*_m; since "
                             "K_lo <= K_hi and T*_m > 0, both cannot hold.",
                "overall": "GO if GO for both recognisers; FALSIFY if FALSIFY for both; WEAKEN otherwise. The "
                           "per-recogniser outcome is always reported and governs the wording for that "
                           "recogniser.",
                "implementation": "upgrade_stats.level_rule, upgrade_stats.combine",
            },
            "manuscript_consequences": {
                "GO_m": "may state, as a post-confirmation sensitivity analysis, that matching the RMS level of "
                        "the Opus signal to the control did not remove the residual for recogniser m (values "
                        "given); the 'level not tested' limitation is replaced by this result",
                "WEAKEN_m": "reports L_m and K_m and states that level matching reduced the residual partly, or "
                            "that the result is inconclusive, for recogniser m; the limitation stays, with the "
                            "numbers added",
                "FALSIFY_m": "must state that for recogniser m more than half of the Stage 3 residual was "
                             "attributable to the RMS level difference, and must revise the interpretation of "
                             "the residual for m; the Stage 3 estimates stand unchanged",
            },
            "commands": [f"{run}run_level_sensitivity.py regenerate", f"{run}run_level_sensitivity.py run",
                         f"{run}run_level_sensitivity.py analyse"],
        },
        "B": {
            "title": "Forced SILK-NB bitrate sweep",
            "label": "PRE-REGISTERED PROSPECTIVE SWEEP - FRESH UTTERANCES, NOT FRESH SPEAKERS",
            "question": "Within forced SILK narrowband, with the signal-type hint, every other encoder setting "
                        "and the decode path held fixed, does the WER residual beyond the linear bandwidth "
                        "control decrease as the coding bitrate increases?",
            "motivation": "In Stage 3, OPUS (8 kbit/s, signal=auto) and SILK (40 kbit/s, signal=voice) differed in "
                          "bitrate and in the signal-type hint. B varies the bitrate alone, at five rates.",
            "claim_tested": "Within forced SILK-NB, with every other encoder setting, the signal hint and the "
                            "decode path fixed, the WER residual beyond the linear bandwidth control decreases as "
                            "the coding bitrate increases.",
            "data": {
                "selection": str(SELECTION), "sha256": selection["selection_sha256"],
                **{k: selection[k] for k in [
                    "n_utterances", "n_speakers", "subsets", "speakers_by_subset", "sex_by_speaker",
                    "duration_hours", "normalised_reference_words", "rules", "exclusion_counts",
                    "unused_but_longer_than_30_s", "eligible_not_selected_reserve",
                    "speakers_without_eligible_utterances", "speakers_also_in_stage3_confirmation",
                    "chapters", "chapters_also_in_stage3_confirmation"]},
                "other_development_outputs": used["other_development_outputs"],
            },
            "holdout_statement": [
                "FRESH-UTTERANCE, NOT FRESH-SPEAKER HOLDOUT. No selected utterance has been encoded, decoded or "
                "recognised by this project, but every selected speaker also appears in the Stage 3 "
                f"confirmation set (and in the prior study), and {selection['chapters_also_in_stage3_confirmation']} "
                f"of its {selection['chapters']} chapters also supplied Stage 3 confirmation utterances.",
                "No fresh-speaker holdout exists for this design within LibriSpeech: test-clean and test-other "
                "have 40 + 33 speakers, all used in Stage 3; the dev subsets supplied the Stage 2 development "
                "utterances, the calibration set and the pilot; the training subsets are excluded because "
                "wav2vec2-base-960h was fine-tuned on all 960 h of them.",
                "Results from B therefore generalise to new utterances of the Stage 3 test speakers, not to "
                "new speakers.",
            ],
            "conditions": [{"name": "LP", "processing": "frozen LP (as Stage 3)", "bitrate": "-",
                            "expected_packets": "-"}] + [
                {"name": name, "processing": f"Opus, forced NB, signal=voice, {rate} kbit/s",
                 "bitrate": f"{rate} kbit/s", "expected_packets": "100 % TOC config 1 (SILK-only, NB, 20 ms)"}
                for name, rate in zip(ustats.SWEEP_CODED, ustats.SWEEP_RATES_KBPS)],
            "encoder_settings": settings,
            "settings_identity": [
                "The five coded conditions differ only in bitrate_bps (checked when the plan was frozen): same "
                "direct-libopus path, forced NB, signal=voice, application audio, unconstrained VBR, complexity "
                "10, 20 ms frames, no FEC, no DTX, 0 % expected loss, same decoder and resampler.",
                "SILK40 has exactly the Stage 3 SILK settings.",
                "SILK8 differs from the Stage 3 OPUS settings only in signal (voice instead of auto).",
                "REF is not recognised in B (R_b needs only LP); the signal descriptors read the REF waveform.",
            ],
            "technical_calibration": [
                "Set: the Stage 3 calibration set (20 dev-clean utterances, 4 speakers; selection_calibration.json, "
                f"sha256 {integrity['stage3_calibration_selection_sha256'][:12]}...). No test utterance.",
                "E1 (gate, environment): the Stage 3 six-condition pipeline is re-run on this set; every "
                "waveform_sha256 and ogg_sha256 and every raw hypothesis of both recognisers must equal the sealed "
                "Stage 3 calibration outputs. Failure: stop and report before any evaluation decoding.",
                "E2 (sanity, no comparison): the sweep conditions are generated and recognised on this set. "
                "Checked: encode_decode equals stage3_audio.codec_round_trip for every rate (waveform hash, first "
                "two utterances); packet configuration; decoded length and finiteness; determinism (first two "
                "utterances regenerated and re-recognised); throughput. No WER is compared between conditions.",
            ],
            "pre_asr_validation": {
                "set": "the frozen sweep selection itself; encode and decode only, no ASR",
                "V1": "Every packet of every utterance in every coded condition has TOC configuration 1 (SILK-only, "
                      "NB, 20 ms), is mono, has frame-count code 0 (one frame per packet), and libopus reports "
                      "bandwidth NB. Required share: 100 %.",
                "V2": f"For each rate b, the median over utterances of the payload bitrate (8 x sum of unpadded "
                      f"packet bytes / utterance duration) is within +/-{BITRATE_TOLERANCE:.0%} of nominal, and the "
                      f"five medians are strictly increasing with every adjacent ratio >= {MIN_ADJACENT_RATIO}. "
                      "(Frozen Stage 2A data, dev-clean, signal=auto: SILK-NB VBR payload bitrates of about 7.4 "
                      "kbit/s at 8 and 11.4 kbit/s at 12, 5-7 % below nominal.)",
                "V3": "Encoder read-back: for every encode, every queried control equals the requested value.",
                "V4": "Decode path: decoded at 48 kHz; after resampling, length equals REF and every sample is "
                      "finite.",
                "V5": "LP taps SHA-256 equals the frozen value.",
                "descriptive": [
                    "container bitrate (Ogg bytes, as Stage 3), lag against REF, RMS change against REF, samples "
                    "with |x| >= 1",
                    "bridge check: per utterance, whether the SILK8 Ogg bytes equal those produced by the Stage 3 "
                    "OPUS settings (signal=auto) for the same utterance; the share of identical files tells whether "
                    "R_8 is exactly a fresh-utterance replication of the Stage 3 OPUS residual (not a gate)",
                ],
                "freeze": "the measured median payload bitrates are sealed in the validation report and fix the x "
                          "values of the measured-bitrate sensitivity before any ASR",
                "determinism": "the ASR run regenerates every condition and requires its ogg_sha256 and "
                               "waveform_sha256 to equal the validation rows",
                "on_failure": "stop before any ASR decoding and report; any change (for example dropping a rate) "
                              "needs explicit approval and a sealed amendment before ASR",
            },
            "estimands": {
                "primary_residuals": "R_b,m = WER_micro(SILK_b) - WER_micro(LP), pooled, for b in {8, 12, 16, 24, "
                                     "40} and each recogniser m: ten primary estimates, each with a 95 % interval, "
                                     "no multiplicity correction; the decision uses only the quantities named in "
                                     "the rules",
                "primary_trend": "S_m = ordinary least-squares slope of R_b,m on x_b = log2(b) (b in kbit/s, "
                                 "nominal), equal weights over the five rates, in pp per doubling of bitrate, "
                                 "recomputed within every bootstrap replicate from that replicate's five residuals; "
                                 "x = " + ", ".join(f"{v:.4f}" for v in ustats.LOG2_RATES),
                "ordered_trend_sensitivity": [
                    "slope of R_b,m on the rank scores 1-5 (pp per rate step): the ordered trend without the log "
                    "spacing",
                    "monotonicity (descriptive): the number of the four adjacent differences R_b - R_b' (b < b') "
                    "with a positive point estimate, and the share of bootstrap replicates with "
                    "R_8 >= R_12 >= R_16 >= R_24 >= R_40",
                    "slope on log2 of the measured median payload bitrates (frozen at validation)",
                ],
                "secondary": [
                    "adjacent-rate contrasts D_b,b' = WER_micro(SILK_b) - WER_micro(SILK_b') for (8,12), (12,16), "
                    "(16,24), (24,40); positive means WER falls as the rate rises",
                    "endpoint contrast E = WER_micro(SILK8) - WER_micro(SILK40): a pure bitrate contrast at a "
                    "fixed signal hint",
                    "macro WER, CER and substitution/deletion/insertion composition of every R_b",
                    "per-subset scopes (test-clean, test-other) of every estimand",
                ],
                "descriptive_mechanism_evidence_only": [
                    "per condition, medians over utterances (frozen Stage 2B/3 metric code): LSD 0-3 and 0-4 kHz "
                    "against LP; coherence 0-3.5 kHz against LP and against REF; RMS change against REF; "
                    "power-based retained bandwidth; 4-8 kHz power change",
                    "pooled cross-spectral measures against REF: in-band gain |H1| (0.5-2 kHz), coherent bandwidth, "
                    "coherent and total 4-8 kHz power, mirror coherence 4.1-4.9 kHz",
                    "no inferential test on any descriptor, no per-utterance correlation analysis, and no "
                    "descriptor enters a rule",
                ],
                "replication_anchors_descriptive": "R_8 beside the Stage 3 OPUS - LP residual (T*), R_40 beside "
                                                   "the Stage 3 SILK - LP residual (U*), E beside the Stage 3 "
                                                   "OPUS - SILK contrast (V*). Different utterances and, for R_8, a "
                                                   "different signal hint: agreement is not a criterion.",
            },
            "bootstrap": {"seed": ustats.SWEEP_SEED, "replicates": ustats.N_BOOT,
                          "note": "speaker clusters stratified by subset; all six conditions and both recognisers "
                                  "of an utterance together; every derived quantity recomputed within each "
                                  "replicate"},
            "anchor_definition": "S*_m = (U*_m - T*_m) / log2(40/8): the slope implied by the frozen Stage 3 "
                                 "residuals at 8 kbit/s (OPUS - LP) and 40 kbit/s (SILK - LP). A meaningful decline "
                                 f"is at least {ustats.B_SLOPE_FRACTION} x S*_m.",
            "anchors": {m: {k: anchors[m][k] for k in ["T_star", "U_star", "V_star", "S_star",
                                                       "B_meaningful_decline_threshold"]}
                        for m in ustats.MODELS},
            "rules": {
                "definitions": "For recogniser m: R_8,m [R8_lo, R8_hi] and S_m [S_lo, S_hi], pooled micro, 95 % "
                               "percentile speaker-bootstrap intervals.",
                "GO_m": f"R8_lo > 0 AND S_hi < 0 AND S_lo <= {ustats.B_SLOPE_FRACTION} x S*_m: a residual is "
                        "present at 8 kbit/s, it declines with bitrate, and the interval does not exclude a decline "
                        "half as steep as Stage 3 implies.",
                "FALSIFY_m": f"S_hi >= 0 AND S_lo > {ustats.B_SLOPE_FRACTION} x S*_m: no decline is detected and "
                             "the interval excludes a decline half as steep as Stage 3 implies.",
                "WEAKEN_m": "neither: for example a decline smaller than half the implied one (S_hi < 0 but "
                            "S_lo > 0.5 S*), a decline without a positive 8 kbit/s residual (R8_lo <= 0), or an "
                            "interval too wide to decide. A missing (NaN) bound never satisfies GO or FALSIFY.",
                "exclusive": "GO_m requires S_hi < 0 and FALSIFY_m requires S_hi >= 0.",
                "overall": "GO if GO for both recognisers; FALSIFY if FALSIFY for both; WEAKEN otherwise. "
                           "Per-recogniser outcomes are always reported.",
                "not_in_the_rules": "adjacent contrasts, E, per-subset scopes, secondary estimators, the ordered "
                                    "and measured-bitrate sensitivities, and every descriptor",
                "implementation": "upgrade_stats.sweep_rule, upgrade_stats.combine",
            },
            "manuscript_consequences": {
                "GO": "may state that within SILK narrowband the residual decreased with bitrate in both "
                      "recognisers (slopes and intervals given), which supports, but does not isolate, the "
                      "low-rate in-band coding distortion interpretation: in-band distortion, level and image "
                      "properties all vary with the rate, and the descriptors are reported beside the result",
                "WEAKEN": "states that the sweep did not establish, or only partly established, a bitrate "
                          "dependence (per-recogniser outcomes given); 'consistent with low-rate in-band coding "
                          "distortion' may stay only with that qualification beside it",
                "FALSIFY": "must state that within SILK narrowband the residual did not decrease with bitrate over "
                           "8-40 kbit/s in either recogniser, report which pattern occurred (a residual at every "
                           "rate, or at none), and remove the low-rate in-band coding distortion interpretation; the "
                           "Stage 3 decomposition estimates stand unchanged",
            },
            "commands": [f"{run}run_bitrate_sweep.py calibrate", f"{run}upgrade_design.py freeze-code",
                         f"{run}run_bitrate_sweep.py validate", f"{run}run_bitrate_sweep.py run",
                         f"{run}run_bitrate_sweep.py analyse"],
        },
        "outputs": {
            "code_freeze": str(CODE_FREEZE),
            "calibration": str(CALIBRATION_REPORT.parent),
            "sweep": str(RESULTS / "sweep") + "/{validation,raw,analysis}",
            "level": str(RESULTS / "level") + "/{regeneration,raw,analysis}",
        },
        "run_order": [
            "U0  Design freeze (this plan): selection_sweep.json and upgrade_spec.json sealed; binding once "
            "committed. No upgrade audio is encoded or decoded before the commit.",
            "U1  run_bitrate_sweep.py calibrate on the Stage 3 calibration set: gate E1 (the environment "
            "reproduces Stage 3 exactly), then E2 (sweep-condition sanity).",
            "U2  upgrade_design.py freeze-code: every upgrade and Stage 3 code file hashed and sealed with this "
            "plan's hash; files changed since the design freeze are listed and need an amendment note.",
            "U3  run_bitrate_sweep.py validate on the sweep selection (encode/decode only): gates V1-V5; sealed "
            "report with the measured median payload bitrates.",
            "U4  run_bitrate_sweep.py run: ASR, once (LP and SILK8-SILK40, both recognisers).",
            "U5  run_bitrate_sweep.py analyse: estimates, intervals and rule outcome with the frozen code; sealed "
            "decision record.",
            "U6  run_level_sensitivity.py regenerate on the confirmation set (no ASR): gates A1-A3.",
            "U7  run_level_sensitivity.py run: ASR, once (LP, OPUS, OPUS8_LEVEL_MATCHED, both recognisers).",
            "U8  run_level_sensitivity.py analyse: estimates, intervals, reproduction check and rule outcome; "
            "sealed sensitivity record.",
            "The manuscript is revised only after U8, and only as the consequences above allow.",
        ],
        "policies": [
            "Single run: each evaluation ASR run (U4, U7) is performed once. A resumable progress file is allowed "
            "as in Stage 3; every interruption and resume is logged; nothing is re-decoded selectively or rerun "
            "from scratch.",
            "Amendments: a change to this plan before the step it affects needs explicit approval and a sealed "
            "amendment record (text, reason, time, new hashes). A change after that step is a deviation and is "
            "reported with the results.",
            "Stop points: a failed gate (E1, V1-V5, A1-A3) stops the upgrade before any evaluation ASR; nothing is "
            "decoded until an approved, sealed amendment exists.",
            "Order independence: A and B are frozen together here; neither result can change the other's plan.",
        ],
        "compute_estimate": "Stage 3 measured 1.59 s per utterance for six conditions and both recognisers "
                            f"(RTX 5090). B: about 45 min for {selection['n_utterances']:,} utterances; A: about "
                            "30 min for 2,174 utterances and three conditions; calibration and validation: minutes.",
        "not_done": [
            "No REF recognition in B, so B gives no fresh-utterance bandwidth component or bandwidth share.",
            "No level matching in B; per-rate level differences are reported descriptively.",
            "No pilot or kill test for B: every rule outcome is reported, and the technical calibration covers "
            "pipeline sanity.",
            "No other decoder, resampler, recogniser, beam search, language model, corpus or bandwidth.",
            "No multiplicity correction across the ten R_b intervals; the decision uses only the rules.",
            "No change to Stage 1-3 files, estimates or decision, or to the manuscript.",
        ],
    }


# ==================================================
# Markdown rendering (from the sealed record only)
# ==================================================

def render(spec: dict) -> str:
    A, B, P = spec["A"], spec["B"], spec["provenance"]
    g = A["expected_gains_from_frozen_stage3"]
    d = B["data"]
    labels = asr.MODEL_LABELS
    lines = [
        "# TASLP upgrade - frozen plan", "",
        f"Sealed `upgrade_spec.json` SHA-256 `{spec['spec_sha256']}`, created {spec['created_utc']}.", "",
        f"**Status: {spec['status']}**", "",
        "This file is rendered from `upgrade_spec.json`; the JSON record is authoritative.", "",
        "## 0. Scope", "", *[f"- {s}" for s in spec["scope"]], "",
        "## 1. Provenance", "",
        *[f"- {k}: `{v}`" for k, v in P.items() if k != "working_tree_status"],
        f"- working tree at freeze: {P['working_tree_status'] or 'clean'}", "",
        "## 2. Common pipeline (unchanged from Stage 3)", "", *[f"- {s}" for s in spec["common_pipeline"]], "",
        f"## 3. Addition A - {A['title']}", "", f"**{A['label']}**", "", f"**Question.** {A['question']}", "",
        "### 3.1 Data", "",
        f"- `{A['data']['selection']}` (SHA-256 `{A['data']['sha256']}`): {A['data']['n_utterances']:,} "
        f"utterances, {A['data']['n_speakers']} speakers, {A['data']['subsets']}.",
        f"- {A['data']['note']}.", "",
        "### 3.2 Conditions and derivation", "",
        *[f"- **{k}**: {v}" for k, v in A["conditions"].items()],
        f"- OPUS encoder settings: `{json.dumps(A['encoder_settings_opus'])}`",
        *[f"- {s}" for s in A["derivation"]],
        f"- Expected gains (frozen Stage 3 manifest, descriptive): median {g['median_db']:+.3f} dB, 5th-95th "
        f"percentile {g['p05_db']:+.3f} to {g['p95_db']:+.3f} dB, range {g['min_db']:+.3f} to {g['max_db']:+.3f} dB "
        f"({g['utterances_with_gain_below_0_db']} utterances below 0 dB; "
        f"{g['stage3_opus_utterances_with_samples_at_or_above_full_scale']} Stage 3 OPUS utterances already had "
        "samples at or above full scale).", "",
        "### 3.3 Pre-ASR gates", "", *[f"- **{k}**: {v}" for k, v in A["pre_asr_gates"].items()], "",
        "### 3.4 Estimands and statistics", "",
        f"- ASR: {A['asr']}.", f"- **Primary**: {A['estimands']['primary']}.",
        *[f"- Secondary: {s}." for s in A["estimands"]["secondary"]],
        *[f"- Descriptive: {s}." for s in A["estimands"]["descriptive"]],
        f"- Bootstrap: seed {A['bootstrap']['seed']}, {A['bootstrap']['replicates']:,} replicates; "
        f"{A['bootstrap']['note']}.",
        f"- Reproduction check: {A['reproduction_check']}", "",
        "### 3.5 Analytic expectations (not tests)", "", *[f"- {s}" for s in A["analytic_expectations"]], "",
        "### 3.6 Interpretation rules (exact)", "",
        *[f"- **{k}**: {v}" for k, v in A["rules"].items()], "",
        "| Recogniser | T*_m = Stage 3 OPUS - LP (pp) [95 % CI] | GO needs K_lo > | FALSIFY needs K_hi < |",
        "|---|---|---|---|",
        *[f"| {labels[m]} | {a['T_star']['estimate']:.6f} [{a['T_star']['ci'][0]:.3f}, {a['T_star']['ci'][1]:.3f}] | "
          f"{a['GO_threshold_K_lower']:.6f} | {a['FALSIFY_threshold_K_upper']:.6f} |" for m, a in A["anchors"].items()],
        "",
        "### 3.7 Consequences for the manuscript", "",
        *[f"- **{k}**: {v}." for k, v in A["manuscript_consequences"].items()], "",
        "### 3.8 Commands (in order, after U2)", "", *[f"- `{c}`" for c in A["commands"]], "",
        f"## 4. Addition B - {B['title']}", "", f"**{B['label']}**", "", f"**Question.** {B['question']}", "",
        B["motivation"], "", f"**Claim tested.** {B['claim_tested']}", "",
        "### 4.1 Data: a fresh-utterance, not fresh-speaker, holdout", "",
        *[f"- {s}" for s in B["holdout_statement"]],
        f"- `{d['selection']}` (SHA-256 `{d['sha256']}`): {d['n_utterances']:,} utterances, {d['n_speakers']} "
        f"speakers ({d['speakers_by_subset']}; speaker sex {d['sex_by_speaker']}), {d['subsets']}, "
        f"{d['duration_hours']:.2f} h, {d['normalised_reference_words']:,} normalised reference words; "
        f"{d['speakers_also_in_stage3_confirmation']} of the {d['n_speakers']} speakers are in the Stage 3 "
        "confirmation set.",
        f"- Rule: {d['rules']['rule']}.",
        f"- Eligibility: {d['rules']['eligibility']}.",
        f"- Exclusions: {d['rules']['exclusions']}. Counts: {d['exclusion_counts']}. Other development outputs: "
        f"{', '.join(d['other_development_outputs']['utterances'])} "
        f"(from {', '.join(d['other_development_outputs']['sources'])}).",
        f"- Unused test utterances longer than 30 s: {d['unused_but_longer_than_30_s']}.",
        f"- Speakers without an eligible utterance (not in B): {d['speakers_without_eligible_utterances']}.",
        f"- Eligible but not selected (reserve, never decoded): {d['eligible_not_selected_reserve']}.",
        f"- Selection inputs: {d['rules']['selection_inputs']}.", "",
        "### 4.2 Conditions", "",
        "| Condition | Processing | Bitrate | Expected packets |", "|---|---|---|---|",
        *[f"| {c['name']} | {c['processing']} | {c['bitrate']} | {c['expected_packets']} |" for c in B["conditions"]],
        "", *[f"- {s}" for s in B["settings_identity"]],
        "- Encoder settings, identical except `bitrate_bps`: "
        f"`{json.dumps({k: v for k, v in B['encoder_settings']['SILK8'].items() if k != 'bitrate_bps'})}`", "",
        "### 4.3 Technical calibration and pre-ASR validation", "",
        *[f"- {s}" for s in B["technical_calibration"]],
        f"- Validation set: {B['pre_asr_validation']['set']}.",
        *[f"- **{k}**: {B['pre_asr_validation'][k]}" for k in ["V1", "V2", "V3", "V4", "V5"]],
        *[f"- Descriptive: {s}." for s in B["pre_asr_validation"]["descriptive"]],
        f"- Freeze: {B['pre_asr_validation']['freeze']}.",
        f"- Determinism: {B['pre_asr_validation']['determinism']}.",
        f"- On failure: {B['pre_asr_validation']['on_failure']}.", "",
        "### 4.4 Estimands", "",
        f"- **Primary residuals**: {B['estimands']['primary_residuals']}.",
        f"- **Primary trend**: {B['estimands']['primary_trend']}.",
        *[f"- Ordered/log-bitrate sensitivity: {s}." for s in B["estimands"]["ordered_trend_sensitivity"]],
        *[f"- Secondary: {s}." for s in B["estimands"]["secondary"]],
        *[f"- Descriptive mechanism evidence only: {s}." for s in B["estimands"]["descriptive_mechanism_evidence_only"]],
        f"- Replication anchors (descriptive): {B['estimands']['replication_anchors_descriptive']}",
        f"- Bootstrap: seed {B['bootstrap']['seed']}, {B['bootstrap']['replicates']:,} replicates; "
        f"{B['bootstrap']['note']}.", "",
        "### 4.5 Anchors from frozen Stage 3 (pooled micro, pp)", "", B["anchor_definition"], "",
        "| Recogniser | T* = OPUS - LP | U* = SILK - LP | V* = OPUS - SILK | S* (pp/doubling) | 0.5 S* |",
        "|---|---|---|---|---|---|",
        *[f"| {labels[m]} | {a['T_star']['estimate']:.6f} | {a['U_star']['estimate']:.6f} | "
          f"{a['V_star']['estimate']:.6f} | {a['S_star']:.6f} | {a['B_meaningful_decline_threshold']:.6f} |"
          for m, a in B["anchors"].items()], "",
        "### 4.6 Interpretation rules (exact)", "", *[f"- **{k}**: {v}" for k, v in B["rules"].items()], "",
        "### 4.7 Consequences for the manuscript", "",
        *[f"- **{k}**: {v}." for k, v in B["manuscript_consequences"].items()], "",
        "### 4.8 Commands (in order)", "", *[f"- `{c}`" for c in B["commands"]], "",
        "## 5. Run order and stop points", "", *[f"- {s}" for s in spec["run_order"]], "",
        f"Outputs: {json.dumps(spec['outputs'])}", "",
        "## 6. Policies", "", *[f"- {s}" for s in spec["policies"]], "",
        "## 7. Compute", "", spec["compute_estimate"], "",
        "## 8. Not done in the upgrade", "", *[f"- {s}" for s in spec["not_done"]], "",
    ]
    return "\n".join(lines)


def freeze_spec() -> None:
    if SPEC_JSON.exists() or PLAN_MD.exists():
        raise RuntimeError("the upgrade plan is already frozen")
    if RESULTS.exists():
        raise RuntimeError(f"{RESULTS} exists: the plan must precede every upgrade run")
    digest = s3.write_sealed(SPEC_JSON, build_spec(), "spec_sha256")
    PLAN_MD.write_text(render(s3.read_sealed(SPEC_JSON, "spec_sha256")))
    print(f"upgrade spec sha256 {digest}")


def freeze_code(amendment: str | None) -> None:
    spec = require_frozen_plan()
    if CODE_FREEZE.exists():
        raise RuntimeError(f"{CODE_FREEZE} is sealed and exists")
    calibration = s3.read_sealed(CALIBRATION_REPORT, "report_sha256")
    if not calibration["E1"]["pass"]:
        raise RuntimeError("gate E1 failed; the code cannot be frozen for evaluation")
    current = code_hashes()
    changed = sorted(f for f in current if spec["code_sha256_at_design_freeze"].get(f) != current[f])
    if changed and not amendment:
        raise RuntimeError(f"code changed since the design freeze ({changed}); an amendment note is required")
    s3.write_sealed(CODE_FREEZE, {
        "created_utc": s3.now(), "spec_sha256": spec["spec_sha256"],
        "calibration_report_sha256": calibration["report_sha256"],
        "code_sha256": current, "code_changed_since_design_freeze": changed, "amendment": amendment,
    }, "freeze_sha256")
    print("code freeze sealed; changed since the design freeze:", changed or "none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["select", "freeze-spec", "freeze-code"])
    parser.add_argument("--amendment", default=None)
    args = parser.parse_args()
    os.chdir(REPO_ROOT)
    {"select": select, "freeze-spec": freeze_spec,
     "freeze-code": lambda: freeze_code(args.amendment)}[args.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
