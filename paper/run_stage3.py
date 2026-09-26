"""
Stage 3: ASR decomposition of narrowband codec degradation.

After bandwidth is independently controlled (frozen Stage 2B low-pass, LP),
is there still a reproducible codec-specific ASR penalty?

    Delta_BW            = WER_LP   - WER_REF
    Delta_OPUS_residual = WER_OPUS - WER_LP
    Delta_SILK_residual = WER_SILK - WER_LP

Commands, strictly in this order (each checks the seals of the previous):

    select               freeze calibration / pilot / confirmation selections
    env-check            re-verify the Stage 1 pipeline after installing transformers
    calibrate            pipeline sanity on the calibration set only
    freeze-spec          write and seal 00_FROZEN_STAGE3_SPEC.md (before any
                         pilot or confirmation audio is decoded)
    run --set pilot      decode the pilot set
    pilot-decision       pilot analysis and pre-declared kill test
    freeze-confirmation  seal analysis code and pilot decision
    run --set confirmation   decode the untouched confirmation set (once)
    analyze              final tables, figures, decision and summary

Outputs: results_paper/stage3_asr/
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile
import torch
import torchaudio
from tqdm import tqdm

import common
import run_opus_validation
import run_reproduce
import stage3_asr as asr
import stage3_audio as audio
import stage3_stats as stats


# ==================================================
# Paths and frozen design constants
# ==================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = Path("results_paper") / "stage3_asr"
RAW = OUT / "raw"
CALIBRATION_DIR = OUT / "calibration"
PILOT_DIR = OUT / "pilot"
SPEC_JSON = OUT / "stage3_spec.json"
SPEC_MD = OUT / "00_FROZEN_STAGE3_SPEC.md"
NORMALISATION_MD = OUT / "transcript_normalization_spec.md"
ENV_CHECK = OUT / "env_check.json"
PILOT_DECISION = PILOT_DIR / "pilot_decision.json"
CONFIRMATION_FREEZE = OUT / "confirmation_freeze.json"
LIBRI = Path(common.DATA_ROOT) / "LibriSpeech"

SETS = ["calibration", "pilot", "confirmation"]
SEEDS = {"calibration": 53051, "pilot": 53052, "confirmation": 53053}
CALIBRATION_SPEAKERS = 4
CALIBRATION_PER_SPEAKER = 5
PILOT_PER_SPEAKER = 2
CONFIRMATION_MAX_PER_SPEAKER = 30
SET_SUBSETS = {
    "calibration": ["dev-clean"],
    "pilot": ["dev-clean", "dev-other"],
    "confirmation": ["test-clean", "test-other"],
}

CHUNK_UTTERANCES = 8
MODELS = asr.MODELS
CONDITIONS = audio.CONDITIONS

CODE_FILES = [Path("paper") / name for name in [
    "run_stage3.py", "stage3_audio.py", "stage3_asr.py", "stage3_stats.py", "stage3_report.py",
    "common.py", "lowpass.py", "opus_direct.py", "run_lowpass_validation.py",
    "run_opus_validation.py", "run_reproduce.py",
]]

PROVENANCE = {
    "stage1_commit": "8a77f412ee8ac779e5230d1d5a8df3cb0e027286",
    "stage2_commit": "d70c9938481415d4016336fb4ad4bb58a5b9ee74",
    "stage2_tag": "paper-stage2b-confirmed",
    "stage2_tag_object": "ebcf06bab238a09ea891215de36483ac1ed3dce8",
    "frozen_lp_taps_sha256": audio.FROZEN_LP_SHA256,
    "revised_gate5_spec_sha256": "166f5672263373ece22a955baf3b2e1f3c7ac7c9ce14098f9daa65938d9055ff",
    "stage2b_confirmation_selection_sha256":
        "0dfc09813d018c3f5026da7723cec3222fe14c957289f126e6aa3108e9932212",
}


# ==================================================
# Hash and seal helpers
# ==================================================

def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_hashes() -> dict[str, str]:
    return {str(p): file_sha256(p) for p in CODE_FILES}


def native(value):
    """Recursively convert numpy scalars / arrays and tuples to JSON-native values."""
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    if isinstance(value, np.ndarray):
        return native(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def body_sha256(record: dict, key: str) -> str:
    body = {k: v for k, v in record.items() if k != key}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def write_sealed(path: Path, record: dict, key: str) -> str:
    if path.exists():
        raise RuntimeError(f"{path} is sealed and exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = native(record)
    record[key] = body_sha256(record, key)
    path.write_text(json.dumps(record, indent=1))
    return record[key]


def read_sealed(path: Path, key: str) -> dict:
    record = json.loads(Path(path).read_text())
    if body_sha256(record, key) != record[key]:
        raise RuntimeError(f"{path} changed after sealing")
    return record


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


# ==================================================
# STEP 1: data selection
# ==================================================

def speaker_sex() -> dict[int, str]:
    sex = {}
    for line in (LIBRI / "SPEAKERS.TXT").read_text().splitlines():
        if line.startswith(";") or not line.strip():
            continue
        speaker, gender, *_ = [f.strip() for f in line.split("|", 4)]
        sex[int(speaker)] = gender
    return sex


def list_subset(subset: str) -> pd.DataFrame:
    root = LIBRI / subset
    transcripts = {}
    for path in root.glob("*/*/*.trans.txt"):
        for line in path.read_text().splitlines():
            key, text = line.split(" ", 1)
            transcripts[key] = text
    rows = []
    for path in root.glob("*/*/*.flac"):
        speaker, chapter, _ = path.stem.split("-")
        info = soundfile.info(str(path))
        rows.append({"subset": subset, "utterance": path.stem, "speaker_id": int(speaker),
                     "chapter_id": int(chapter), "path": str(path.relative_to(LIBRI)),
                     "duration_s": info.frames / info.samplerate,
                     "sample_rate": info.samplerate, "reference": transcripts[path.stem]})
    return pd.DataFrame(rows).sort_values("utterance").reset_index(drop=True)


def prior_study_utterances(subset: str, listing: pd.DataFrame) -> set[str]:
    """Utterances of the frozen ELEC5305 selection (results/<subset>_experiment_details.csv)."""
    details = pd.read_csv(Path("results") / f"{subset}_experiment_details.csv")
    wav = details[details["codec"] == "wav"]
    walker = sorted(listing["utterance"])       # torchaudio LIBRISPEECH order
    chosen = set()
    for row in wav.itertuples():
        fileid = walker[row.dataset_index]
        if fileid != f"{row.speaker_id}-{row.chapter_id}-{row.utterance_id:04d}":
            raise RuntimeError(f"prior-study index mapping mismatch at {row.dataset_index}")
        chosen.add(fileid)
    return chosen


def stage2_dev_utterances(subset: str) -> set[str]:
    dataset = torchaudio.datasets.LIBRISPEECH(common.DATA_ROOT, url=subset, download=False)
    return {dataset._walker[i] for i in run_opus_validation.select_dev_utterances(dataset)}


def select() -> None:
    normaliser = asr.Normaliser()
    sex = speaker_sex()
    listings = {s: list_subset(s) for s in ["dev-clean", "dev-other", "test-clean", "test-other"]}

    excluded = {s: set() for s in listings}
    exclusion_reason = {}
    for s in ["dev-clean", "dev-other"]:
        excluded[s] |= stage2_dev_utterances(s)
        exclusion_reason[s] = "Stage 2A/2B signal-level development utterances (one per speaker)"
    for s in ["test-clean", "test-other"]:
        excluded[s] |= prior_study_utterances(s, listings[s])
        exclusion_reason[s] = "frozen ELEC5305 prior-study selection (500 utterances, seed 5305)"

    def eligible(frame):
        ok = (frame["duration_s"] <= asr.MAX_DURATION_S) & ~frame["utterance"].isin(
            excluded[frame["subset"].iloc[0]])
        ok &= frame["reference"].map(lambda t: normaliser(t).strip() != "")
        return frame[ok]

    chosen = {}
    rng = random.Random(SEEDS["calibration"])
    dev_clean = eligible(listings["dev-clean"])
    calibration_speakers = sorted(rng.sample(sorted(dev_clean["speaker_id"].unique()),
                                             CALIBRATION_SPEAKERS))
    parts = []
    for speaker in calibration_speakers:
        pool = sorted(dev_clean[dev_clean["speaker_id"] == speaker]["utterance"])
        parts += sorted(rng.sample(pool, CALIBRATION_PER_SPEAKER))
    chosen["calibration"] = dev_clean[dev_clean["utterance"].isin(parts)]

    rng = random.Random(SEEDS["pilot"])
    parts = []
    for s in ["dev-clean", "dev-other"]:
        frame = eligible(listings[s])
        for speaker in sorted(frame["speaker_id"].unique()):
            if speaker in calibration_speakers:
                continue
            pool = sorted(frame[frame["speaker_id"] == speaker]["utterance"])
            parts.append(frame[frame["utterance"].isin(sorted(rng.sample(pool, PILOT_PER_SPEAKER)))])
    chosen["pilot"] = pd.concat(parts)

    rng = random.Random(SEEDS["confirmation"])
    parts = []
    for s in ["test-clean", "test-other"]:
        frame = eligible(listings[s])
        for speaker in sorted(frame["speaker_id"].unique()):
            pool = sorted(frame[frame["speaker_id"] == speaker]["utterance"])
            k = min(CONFIRMATION_MAX_PER_SPEAKER, len(pool))
            parts.append(frame[frame["utterance"].isin(sorted(rng.sample(pool, k)))])
    chosen["confirmation"] = pd.concat(parts)

    speakers = {k: set(v["speaker_id"]) for k, v in chosen.items()}
    if speakers["calibration"] & speakers["pilot"] or speakers["pilot"] & speakers["confirmation"] \
            or speakers["calibration"] & speakers["confirmation"]:
        raise RuntimeError("selection sets are not speaker-disjoint")

    OUT.mkdir(parents=True, exist_ok=True)
    rules = {
        "calibration": f"dev-clean: {CALIBRATION_SPEAKERS} speakers (random.Random({SEEDS['calibration']}).sample "
                       f"of sorted speaker IDs), {CALIBRATION_PER_SPEAKER} utterances each",
        "pilot": f"dev-clean speakers not used for calibration + all dev-other speakers, "
                 f"{PILOT_PER_SPEAKER} utterances each (random.Random({SEEDS['pilot']}))",
        "confirmation": f"test-clean + test-other, all speakers, up to {CONFIRMATION_MAX_PER_SPEAKER} "
                        f"utterances each (random.Random({SEEDS['confirmation']}))",
        "eligibility": f"duration <= {asr.MAX_DURATION_S} s (Whisper window); non-empty normalised "
                       "reference; not in the excluded set of the subset",
        "exclusions": exclusion_reason,
        "selection_inputs": "file names, FLAC header durations, reference transcripts (for the "
                            "non-empty rule only); no ASR output of any kind",
    }
    table = []
    for set_name in SETS:
        frame = chosen[set_name].sort_values(["subset", "speaker_id", "utterance"])
        utterances = json.loads(frame.to_json(orient="records"))
        digest = write_sealed(OUT / f"selection_{set_name}.json", {
            "set": set_name, "created_utc": now(), "seed": SEEDS[set_name], "rules": rules,
            "n_utterances": len(utterances), "n_speakers": frame["speaker_id"].nunique(),
            "subsets": frame["subset"].value_counts().to_dict(), "utterances": utterances,
        }, "selection_sha256")
        print(f"{set_name}: {len(utterances)} utterances, {frame['speaker_id'].nunique()} speakers, "
              f"{frame['duration_s'].sum() / 3600:.2f} h, sha256 {digest}")
        table.append(frame.assign(set=set_name, sex=frame["speaker_id"].map(sex)))
    pd.concat(table)[["set", "subset", "speaker_id", "sex", "chapter_id", "utterance",
                      "duration_s", "sample_rate", "path", "reference"]].to_csv(
        OUT / "02_dataset_selection.csv", index=False)


def load_selection(set_name: str) -> dict:
    return read_sealed(OUT / f"selection_{set_name}.json", "selection_sha256")


# ==================================================
# Environment regression check (Stage 1 after installing transformers)
# ==================================================

def env_check() -> None:
    common.load_model()
    common.load_frozen_standardisation()
    committed = {name: run_reproduce.read_csv(Path("results_paper/reproduce") / f"new_{name}_rows.csv")
                 for name in ["asr", "signal", "representation"]}
    checks = {}
    for subset in ["test-clean", "test-other"]:
        rows = run_reproduce.run_subset(subset, 3)
        for kind, fields in [("asr", ["prediction", "wer", "compressed_size_bytes"]),
                             ("signal", ["lsd_db", "retained_bandwidth_hz", "estimated_delay_samples"]),
                             ("representation", [f"sdrift_{l}" for l in common.LAYER_NAMES])]:
            new = pd.DataFrame(rows[kind])
            old = committed[kind][committed[kind]["dataset"] == subset]
            merged = new.merge(old, on=["dataset_index", "codec", "bitrate"], suffixes=("_new", "_old"))
            for field in fields:
                a, b = merged[f"{field}_new"], merged[f"{field}_old"]
                if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
                    identical = bool(np.allclose(a.astype(float), b.astype(float), rtol=0, atol=1e-9))
                else:
                    identical = bool((a.astype(str) == b.astype(str)).all())
                checks[f"{subset}/{kind}/{field}"] = {"rows": len(merged), "identical": identical}
    result = {"created_utc": now(), "utterances_per_subset": 3,
              "all_identical": all(c["identical"] for c in checks.values()), "checks": checks,
              "note": "first 3 Stage 1 utterances per subset (prior-study utterances, excluded "
                      "from every Stage 3 set) re-run through the frozen pipeline after installing "
                      "transformers; compared with the committed Stage 1 rows"}
    ENV_CHECK.write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v["identical"] for k, v in checks.items()}, indent=1))
    print("ALL IDENTICAL:", result["all_identical"])


# ==================================================
# STEP 2-5: generate conditions, decode, score (resumable)
# ==================================================

class Pipeline:

    def __init__(self) -> None:
        self.filters = audio.load_filters()
        self.normaliser = asr.Normaliser()
        self.whisper = asr.WhisperASR()
        self.wav2vec2 = asr.Wav2Vec2ASR()

    def process_chunk(self, set_name: str, entries: list[dict], accumulators: dict) -> list[dict]:
        records, queue = [], []
        for entry in entries:
            waveform, rate = torchaudio.load(LIBRI / entry["path"])
            if rate != audio.SAMPLE_RATE or waveform.shape[0] != 1:
                raise RuntimeError(f"{entry['path']}: {rate} Hz, {waveform.shape[0]} channels")
            conditions = audio.generate_conditions(waveform, self.filters)
            ids = {"set": set_name, "utterance": entry["utterance"], "subset": entry["subset"],
                   "speaker_id": entry["speaker_id"]}
            reference_norm = self.normaliser(entry["reference"])
            record = {"utterance": entry["utterance"], "audio": [], "signal": [], "asr": [],
                      "metrics": []}
            for name in CONDITIONS:
                processed, info = conditions[name]
                record["audio"].append({**ids, **audio.audio_stats(name, processed, waveform, info)})
            signal_rows, aligned_pairs = audio.signal_controls(conditions)
            record["signal"] = [{**ids, **row} for row in signal_rows]
            for pair, aligned in aligned_pairs.items():
                accumulators[pair].add(*aligned)
            for name in CONDITIONS:
                processed = conditions[name][0]
                hypothesis = self.wav2vec2.transcribe(processed)
                self._add_asr(record, ids, name, "wav2vec2", entry["reference"], reference_norm,
                              hypothesis)
                queue.append((record, ids, name, entry["reference"], reference_norm,
                              processed[0].numpy()))
            records.append(record)

        for start in range(0, len(queue), asr.WHISPER_BATCH_SIZE):
            batch = queue[start:start + asr.WHISPER_BATCH_SIZE]
            texts = self.whisper.transcribe([item[5] for item in batch])
            for (record, ids, name, reference, reference_norm, _), text in zip(batch, texts):
                self._add_asr(record, ids, name, "whisper", reference, reference_norm, text)
        return records

    def _add_asr(self, record, ids, condition, model, reference, reference_norm, hypothesis):
        hypothesis_norm = self.normaliser(hypothesis)
        record["asr"].append({**ids, "condition": condition, "model": model,
                              "reference": reference, "reference_normalised": reference_norm,
                              "hypothesis": hypothesis, "hypothesis_normalised": hypothesis_norm})
        record["metrics"].append({**ids, "condition": condition, "model": model,
                                  **asr.score(reference_norm, hypothesis_norm),
                                  "hypothesis_normalised": hypothesis_norm})


def run_set(set_name: str, out_dir: Path, pipeline: Pipeline | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / "outputs_sha256.json"
    if final.exists():
        raise RuntimeError(f"{set_name} has already been decoded ({final}); single run only")
    selection = load_selection(set_name)
    progress = out_dir / "progress.jsonl"
    state = out_dir / "transfer_accumulators.npz"
    done = []
    if progress.exists():
        done = [json.loads(line)["utterance"] for line in progress.read_text().splitlines()]
    accumulators = audio.new_accumulators()
    if done:
        arrays = np.load(state)
        if int(arrays["n_done"]) != len(done):
            raise RuntimeError("accumulator checkpoint does not match progress; not resumable")
        accumulators = audio.accumulators_from_arrays(arrays)
    log_path = out_dir / "run_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {
        "set": set_name, "selection_sha256": selection["selection_sha256"], "sessions": []}
    session = {"started_utc": now(), "resumed_after": len(done), "chunks": 0,
               "code_sha256": code_hashes()}
    log["sessions"].append(session)

    pending = [u for u in selection["utterances"] if u["utterance"] not in set(done)]
    pipeline = pipeline or Pipeline()
    started = time.time()
    with tqdm(total=len(selection["utterances"]), initial=len(done), desc=set_name,
              unit="utt") as bar:
        for start in range(0, len(pending), CHUNK_UTTERANCES):
            chunk = pending[start:start + CHUNK_UTTERANCES]
            records = pipeline.process_chunk(set_name, chunk, accumulators)
            completed = len(done) + start + len(chunk)
            np.savez(out_dir / "transfer_accumulators.tmp.npz", n_done=completed,
                     **audio.accumulators_to_arrays(accumulators))
            with progress.open("a") as file:
                for record in records:
                    file.write(json.dumps(native(record)) + "\n")
            os.replace(out_dir / "transfer_accumulators.tmp.npz", state)
            session["chunks"] += 1
            session["seconds"] = time.time() - started
            log_path.write_text(json.dumps(log, indent=1))
            bar.update(len(chunk))

    records = {}
    for line in progress.read_text().splitlines():
        record = json.loads(line)
        records[record["utterance"]] = record
    ordered = [records[u["utterance"]] for u in selection["utterances"]]
    for kind, filename in [("audio", "audio_manifest.csv"), ("signal", "signal_metrics.csv"),
                           ("asr", "asr_outputs.csv"), ("metrics", "utterance_metrics.csv")]:
        pd.DataFrame([row for record in ordered for row in record[kind]]).to_csv(
            out_dir / filename, index=False)
    summary, curves = audio.pooled_transfer_rows(accumulators)
    pd.DataFrame(summary).assign(set=set_name).to_csv(out_dir / "pooled_transfer.csv", index=False)
    pd.DataFrame(curves).assign(set=set_name).to_csv(out_dir / "pooled_transfer_curves.csv", index=False)
    session["finished_utc"] = now()
    session["seconds"] = time.time() - started
    session["seconds_per_utterance"] = session["seconds"] / max(len(pending), 1)
    log_path.write_text(json.dumps(log, indent=1))
    hashes = {f.name: file_sha256(f) for f in sorted(out_dir.glob("*.csv"))}
    write_sealed(final, {"set": set_name, "created_utc": now(),
                         "n_utterances": len(ordered), "files": hashes}, "outputs_sha256")


# ==================================================
# Calibration (pipeline sanity only)
# ==================================================

def calibrate() -> None:
    pipeline = Pipeline()
    run_set("calibration", CALIBRATION_DIR, pipeline)
    audio_rows = pd.read_csv(CALIBRATION_DIR / "audio_manifest.csv")
    metrics = pd.read_csv(CALIBRATION_DIR / "utterance_metrics.csv", keep_default_na=False)
    asr_rows = pd.read_csv(CALIBRATION_DIR / "asr_outputs.csv", keep_default_na=False)
    log = json.loads((CALIBRATION_DIR / "run_log.json").read_text())

    # Determinism: regenerate and re-decode the first two utterances
    selection = load_selection("calibration")["utterances"][:2]
    repeat = pipeline.process_chunk("calibration", selection, audio.new_accumulators())
    repeat_audio = {(r["utterance"], r["condition"]): r["waveform_sha256"]
                    for rec in repeat for r in rec["audio"]}
    repeat_asr = {(r["utterance"], r["condition"], r["model"]): r["hypothesis"]
                  for rec in repeat for r in rec["asr"]}
    first = audio_rows[audio_rows["utterance"].isin([u["utterance"] for u in selection])]
    first_asr = asr_rows[asr_rows["utterance"].isin([u["utterance"] for u in selection])]
    audio_identical = all(repeat_audio[(r.utterance, r.condition)] == r.waveform_sha256
                          for r in first.itertuples())
    asr_identical = all(repeat_asr[(r.utterance, r.condition, r.model)] == r.hypothesis
                        for r in first_asr.itertuples())

    per_condition = audio_rows.groupby("condition", sort=False).agg(
        length_equals_ref=("length_equals_ref", "all"),
        nonfinite=("nonfinite_count", "sum"),
        clipped_samples=("clip_count", "sum"),
        lag_min=("lag_vs_ref_samples", "min"), lag_max=("lag_vs_ref_samples", "max"),
        rms_change_db_median=("rms_change_db", "median"),
    ).reset_index()
    if "share_expected_configuration" in audio_rows:
        share = audio_rows.groupby("condition")["share_expected_configuration"].min()
        per_condition["min_share_expected_packets"] = per_condition["condition"].map(share)
    empties = metrics.assign(empty=metrics["hypothesis_normalised"].str.strip() == "").groupby(
        ["model", "condition"])["empty"].sum().unstack()
    ref = metrics[metrics["condition"] == "REF"].groupby("model").apply(
        lambda g: 100 * g["word_errors"].sum() / g["n_words"].sum())

    report = {
        "created_utc": now(), "utterances": len(metrics["utterance"].unique()),
        "purpose": "pipeline debugging / decoding sanity only; no condition comparison is computed",
        "audio_by_condition": per_condition.to_dict(orient="records"),
        "empty_hypotheses_by_model_condition": empties.to_dict(),
        "ref_wer_pct_by_model": ref.to_dict(),
        "determinism_first_two_utterances": {"waveforms_identical": audio_identical,
                                             "hypotheses_identical": asr_identical},
        "seconds_per_utterance": log["sessions"][-1].get("seconds_per_utterance"),
    }
    (CALIBRATION_DIR / "calibration_report.json").write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps(report, indent=1, default=str))


# ==================================================
# Freeze the Stage 3 specification
# ==================================================

def freeze_spec() -> None:
    if SPEC_JSON.exists() or SPEC_MD.exists():
        raise RuntimeError("Stage 3 specification is already frozen")
    for set_name in ["pilot", "confirmation"]:
        if (RAW / set_name).exists():
            raise RuntimeError(f"{set_name} decoding has started; the spec must precede it")
    env = json.loads(ENV_CHECK.read_text())
    if not env["all_identical"]:
        raise RuntimeError("environment regression check failed")
    calibration = json.loads((CALIBRATION_DIR / "calibration_report.json").read_text())

    whisper = asr.WhisperASR()
    wav2vec2 = asr.Wav2Vec2ASR()
    normaliser = asr.Normaliser()
    filters = audio.load_filters()
    selections = {s: load_selection(s) for s in SETS}
    environment = run_reproduce.collect_environment()
    import transformers
    environment["packages"]["transformers"] = transformers.__version__
    freeze_text = run_reproduce.command_output([sys.executable, "-m", "pip", "freeze"])
    (OUT / "requirements-lock.txt").write_text(freeze_text + "\n")

    spec = {
        "stage": "Stage 3 - ASR decomposition", "created_utc": now(),
        "question": "After bandwidth is independently controlled with the frozen, "
                    "independently validated linear low-pass (LP), is there still a "
                    "reproducible codec-specific ASR penalty?",
        "provenance": {**PROVENANCE, "head_at_freeze": git("rev-parse", "HEAD"),
                       "working_tree_status": git("status", "--porcelain").splitlines()},
        "conditions": {
            "primary": audio.PRIMARY_CONDITIONS, "controls": audio.CONTROL_CONDITIONS,
            "definitions": {
                "REF": "original LibriSpeech waveform",
                "LP": "frozen Stage 2B zero-phase low-pass (linear SILK-NB band-limiting only)",
                "OPUS": "Opus 8 kbps, frozen prior-study settings (SILK-NB; packets identical "
                        "to the ELEC5305 Opus 8k condition)",
                "SILK": "SILK-NB at 40 kbps with signal=voice (the Stage 2B SILK-NB reference "
                        "condition: SILK narrowband coding with minimal coding distortion)",
                "NEG_LP": "negative control: same FIR design routine, flat to 7.0 kHz",
                "NEG_CODEC": "negative control: Opus 64 kbps, frozen settings (CELT-WB), the "
                             "prior study's transparent condition",
            },
            "encoder_settings": {k: asdict(v) for k, v in audio.CODEC_SETTINGS.items()},
            "expected_packet_configuration": audio.EXPECTED_CONFIGURATION,
            "filter_sha256": audio.filter_hashes(filters),
            "neg_lp_design": audio.NEG_LP_DESIGN,
            "naming_note": "OPUS and SILK are both Opus's SILK layer in narrowband mode; they "
                           "differ in coding rate (8 vs 40 kbps), not in bandwidth. The prior "
                           "study had no separate SILK codec.",
            "level_policy": "no normalisation of any condition; physical output level",
            "sample_rate_policy": "all conditions 16 kHz mono float32, length equal to REF; codec "
                                  "outputs decoded at 48 kHz by the frozen torchaudio.load path "
                                  "and resampled with torchaudio.functional.resample",
            "alignment_policy": "no re-alignment before recognition (frozen convention); lags recorded",
        },
        "data": {
            "selections": {s: {"file": f"selection_{s}.json",
                               "sha256": selections[s]["selection_sha256"],
                               "n_utterances": selections[s]["n_utterances"],
                               "n_speakers": selections[s]["n_speakers"],
                               "subsets": selections[s]["subsets"]} for s in SETS},
            "rules": selections["pilot"]["rules"],
            "speaker_disjoint": True,
            "post_decoding_exclusions": "none: every selected utterance is scored in every "
                                        "condition and model; an empty or failed hypothesis "
                                        "counts as all deletions",
        },
        "asr_models": {"whisper": whisper.settings(), "wav2vec2": wav2vec2.settings()},
        "normalisation": normaliser.settings(),
        "metrics": {
            "primary": "WER (word errors S+D+I over reference words, normalised text, jiwer)",
            "recorded": ["substitutions", "deletions", "insertions", "n_words", "CER (secondary)"],
            "micro": "corpus WER from total edit counts (primary)",
            "macro": "mean of per-utterance WER differences (secondary)",
        },
        "analysis": {
            "contrasts": stats.CONTRASTS, "residuals": stats.RESIDUALS, "shares": stats.SHARES,
            "bootstrap": {"unit": "speaker", "stratified_by": "LibriSpeech subset",
                          "replicates": stats.N_BOOT, "seed": stats.BOOT_SEED,
                          "interval": f"percentile {stats.CI_LEVEL:.0%}",
                          "paired": "all conditions and both models of an utterance together"},
            "pilot_rule": {"proceed": "any (model, codec) micro residual 95% CI lower bound > 0",
                           "stop": "otherwise STOP/KILL; 'bounded small' if every residual CI "
                                   f"upper bound < {stats.PILOT_BOUNDED_SMALL_PP} pp"},
            "confirmation_rule": {
                "KILL": "all four residual CIs (2 codecs x 2 models) include 0",
                "GO": f"for >= 1 codec: residual CI lower bound > 0 in both models, estimate "
                      f">= {stats.MIN_RESIDUAL_PP} pp in both, pilot estimate > 0 in both",
                "CONDITIONAL GO": "for >= 1 codec: residual CI lower bound > 0 in both models, "
                                  "GO size/pilot criteria not met",
                "HOLD": "residual robust in only one model, or robustly negative, or other",
                "negative_control_cap": f"if NEG_LP-REF or NEG_CODEC-REF has a CI excluding 0 "
                                        f"and |estimate| > {stats.NEGATIVE_CONTROL_MARGIN_PP} pp in "
                                        "either model, GO/CONDITIONAL GO is capped at HOLD",
                "primary_scope": "pooled (clean + other, stratified); per-subset results secondary",
            },
            "conditional_analyses": "error-type breakdown (Step 11) and exploratory signal "
                                    "correlations (Step 12, Spearman, speaker bootstrap "
                                    f"B={stats.N_BOOT_EXPLORATORY}) only if a residual CI lower "
                                    "bound > 0 in at least one model on confirmation",
            "not_run": "Step 14 (second bandwidth control): the LP shape is SILK-NB's measured "
                       "linear response, not an arbitrary choice; deferred unless challenged",
        },
        "compute": {"whisper_dtype": "float16", "whisper_batch_size": asr.WHISPER_BATCH_SIZE,
                    "chunk_utterances": CHUNK_UTTERANCES,
                    "decoding_rationale": "greedy decoding chosen before any evaluation decode: "
                                          "beam 5 measured at 2-7.5 s/utterance on the shared GPU"},
        "environment": environment,
        "requirements_lock_sha256": file_sha256(OUT / "requirements-lock.txt"),
        "env_check": {"all_identical": env["all_identical"], "file_sha256": file_sha256(ENV_CHECK)},
        "calibration": {"report_sha256": file_sha256(CALIBRATION_DIR / "calibration_report.json"),
                        "determinism": calibration["determinism_first_two_utterances"],
                        "seconds_per_utterance": calibration["seconds_per_utterance"]},
        "code_sha256": code_hashes(),
    }
    digest = write_sealed(SPEC_JSON, spec, "spec_sha256")
    spec = read_sealed(SPEC_JSON, "spec_sha256")

    import stage3_report
    SPEC_MD.write_text(stage3_report.render_spec(spec))
    NORMALISATION_MD.write_text(stage3_report.render_normalisation(spec, normaliser))
    print(f"spec sha256 {digest}")


def verify_code(expected: dict[str, str]) -> None:
    current = code_hashes()
    changed = [f for f in expected if expected[f] != current.get(f)]
    if changed:
        raise RuntimeError(f"code changed since freeze: {changed}")


# ==================================================
# Pilot, confirmation freeze, confirmation, analysis
# ==================================================

def run_command(set_name: str) -> None:
    spec = read_sealed(SPEC_JSON, "spec_sha256")
    if set_name == "pilot":
        verify_code(spec["code_sha256"])
    elif set_name == "confirmation":
        freeze = read_sealed(CONFIRMATION_FREEZE, "freeze_sha256")
        if freeze["spec_sha256"] != spec["spec_sha256"]:
            raise RuntimeError("spec changed since the confirmation freeze")
        verify_code(freeze["code_sha256"])
    else:
        raise ValueError(set_name)
    if load_selection(set_name)["selection_sha256"] != spec["data"]["selections"][set_name]["sha256"]:
        raise RuntimeError("selection differs from the frozen spec")
    run_set(set_name, RAW / set_name)


def load_metrics(set_names: list[str]) -> pd.DataFrame:
    frames = []
    for set_name in set_names:
        read_sealed(RAW / set_name / "outputs_sha256.json", "outputs_sha256")
        frames.append(pd.read_csv(RAW / set_name / "utterance_metrics.csv", keep_default_na=False))
    return pd.concat(frames, ignore_index=True)


def pilot_decision_command() -> None:
    import stage3_report
    spec = read_sealed(SPEC_JSON, "spec_sha256")
    verify_code(spec["code_sha256"])
    metrics = load_metrics(["pilot"])
    boot = stats.decompose_all(metrics, CONDITIONS, MODELS)
    corpus = stats.corpus_table(metrics)
    decision = stats.pilot_decision(boot, MODELS)
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    boot.to_csv(PILOT_DIR / "pilot_bootstrap.csv", index=False)
    corpus.to_csv(PILOT_DIR / "pilot_corpus_metrics.csv", index=False)
    write_sealed(PILOT_DECISION, {"created_utc": now(), "spec_sha256": spec["spec_sha256"],
                                  "bootstrap_sha256": file_sha256(PILOT_DIR / "pilot_bootstrap.csv"),
                                  **decision}, "decision_sha256")
    stage3_report.pilot_figures(metrics, boot, PILOT_DIR)
    (PILOT_DIR / "pilot_report.md").write_text(stage3_report.render_pilot(decision, boot, corpus))
    print(json.dumps(decision, indent=1))


def freeze_confirmation(amendment: str | None) -> None:
    spec = read_sealed(SPEC_JSON, "spec_sha256")
    decision = read_sealed(PILOT_DECISION, "decision_sha256")
    if decision["decision"] != "PROCEED_TO_CONFIRMATION":
        raise RuntimeError(f"pilot decision is {decision['decision']}; confirmation not permitted")
    if (RAW / "confirmation").exists():
        raise RuntimeError("confirmation decoding has already started")
    current = code_hashes()
    changed = sorted(f for f in current if spec["code_sha256"].get(f) != current[f])
    if changed and not amendment:
        raise RuntimeError(f"code changed since the spec freeze ({changed}); an amendment note is required")
    write_sealed(CONFIRMATION_FREEZE, {
        "created_utc": now(), "spec_sha256": spec["spec_sha256"],
        "pilot_decision_sha256": decision["decision_sha256"], "pilot_decision": decision["decision"],
        "code_sha256": current, "code_changed_since_spec": changed, "amendment": amendment,
        "frozen": ["metrics", "exclusion rules", "bootstrap procedure", "ASR decoding settings",
                   "analysis scripts (code_sha256)"],
    }, "freeze_sha256")
    print("confirmation freeze sealed; changed since spec:", changed or "none")


def analyze() -> None:
    import stage3_report
    spec = read_sealed(SPEC_JSON, "spec_sha256")
    freeze = read_sealed(CONFIRMATION_FREEZE, "freeze_sha256")
    verify_code(freeze["code_sha256"])
    stage3_report.final_analysis(spec, freeze, OUT, RAW, load_metrics(["pilot", "confirmation"]),
                                 write_sealed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["select", "env-check", "calibrate", "freeze-spec", "run",
                                            "pilot-decision", "freeze-confirmation", "analyze"])
    parser.add_argument("--set", choices=["pilot", "confirmation"])
    parser.add_argument("--amendment", default=None)
    args = parser.parse_args()
    os.chdir(REPO_ROOT)
    {
        "select": select, "env-check": env_check, "calibrate": calibrate,
        "freeze-spec": freeze_spec, "pilot-decision": pilot_decision_command,
        "analyze": analyze,
        "run": lambda: run_command(args.set),
        "freeze-confirmation": lambda: freeze_confirmation(args.amendment),
    }[args.command]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
