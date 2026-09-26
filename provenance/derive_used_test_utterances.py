"""
Derive the list of LibriSpeech test utterances already used by the project.

The TASLP-upgrade bitrate sweep may use only test utterances that the project
has never encoded, decoded or recognised. Some of the earlier uses are recorded
only in the development repository, whose coursework outputs (`results/`) are
not part of this repository. This script reads the development repository at
one fixed commit, through git objects only (committed content, not the working
tree), and writes a sealed record:

    provenance/used_test_utterances.json

Sources, all committed files at the given commit:

    results/**        coursework outputs of the prior study
    results_paper/**  Stage 1-3 outputs

An utterance counts as used if a committed file names it: by the LibriSpeech
utterance-ID pattern, by speaker/chapter/utterance columns, or by
(dataset, dataset_index) columns mapped through the sorted file listing, which is
the torchaudio LIBRISPEECH order used by the prior study. The prior-study
selection itself is rebuilt exactly as paper/run_stage3.prior_study_utterances
does it. Inputs: file names of the LibriSpeech test subsets (no audio is read).

    python provenance/derive_used_test_utterances.py \
        --development-repo /path/to/development/repository --commit <sha>
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "provenance" / "used_test_utterances.json"
TEST_SUBSETS = ["test-clean", "test-other"]
SCAN_ROOTS = ["results", "results_paper"]
SCAN_SUFFIXES = (".csv", ".json", ".jsonl", ".md", ".txt")
ID_PATTERN = re.compile(r"\b(\d{1,4})-(\d{1,6})-(\d{4})\b")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def body_sha256(record: dict, key: str) -> str:
    body = {k: v for k, v in record.items() if k != key}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def test_listing(librispeech: Path) -> dict[str, list[str]]:
    """Sorted utterance IDs per test subset (the torchaudio LIBRISPEECH order)."""
    listing = {}
    for subset in TEST_SUBSETS:
        listing[subset] = sorted(p.stem for p in (librispeech / subset).glob("*/*/*.flac"))
        if not listing[subset]:
            raise RuntimeError(f"no FLAC files under {librispeech / subset}")
    return listing


def ids_in_csv(text: str, walkers: dict[str, list[str]]) -> set[str]:
    ids = set()
    reader = csv.DictReader(io.StringIO(text))
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


def prior_study(repo: Path, commit: str, walkers: dict[str, list[str]]) -> set[str]:
    """As paper/run_stage3.prior_study_utterances: the 'wav' rows of the frozen selection."""
    chosen = set()
    for subset in TEST_SUBSETS:
        text = git(repo, "show", f"{commit}:results/{subset}_experiment_details.csv").decode()
        for row in csv.DictReader(io.StringIO(text)):
            if row["codec"] != "wav":
                continue
            fileid = walkers[subset][int(row["dataset_index"])]
            if fileid != f"{row['speaker_id']}-{row['chapter_id']}-{int(row['utterance_id']):04d}":
                raise RuntimeError(f"prior-study index mapping mismatch at {row['dataset_index']}")
            chosen.add(fileid)
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--development-repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--librispeech", type=Path, default=REPO_ROOT / "data" / "LibriSpeech")
    args = parser.parse_args()
    if OUT.exists():
        raise RuntimeError(f"{OUT} is sealed and exists")

    repo = args.development_repo.resolve()
    commit = git(repo, "rev-parse", "--verify", f"{args.commit}^{{commit}}").decode().strip()
    walkers = test_listing(args.librispeech)
    test_ids = set().union(*map(set, walkers.values()))

    files = [f for f in git(repo, "ls-tree", "-r", "--name-only", commit, "--", *SCAN_ROOTS)
             .decode().splitlines() if f.endswith(SCAN_SUFFIXES)]
    sources, scanned = [], set()
    for path in files:
        blob = git(repo, "rev-parse", f"{commit}:{path}").decode().strip()
        data = git(repo, "cat-file", "blob", blob)
        text = data.decode(errors="ignore")
        found = {"-".join(m) for m in ID_PATTERN.findall(text)}
        if path.endswith(".csv"):
            found |= ids_in_csv(text, walkers)
        found &= test_ids
        if found:
            sources.append({"path": path, "git_blob": blob, "sha256": hashlib.sha256(data).hexdigest(),
                            "n_test_utterances": len(found)})
            scanned |= found

    prior = prior_study(repo, commit, walkers)
    selection = json.loads(git(repo, "show", f"{commit}:results_paper/stage3_asr/selection_confirmation.json"))
    confirmation = {u["utterance"] for u in selection["utterances"]}
    if not (prior <= scanned and confirmation <= scanned):
        raise RuntimeError("scan missed a known selection")
    if prior & confirmation:
        raise RuntimeError("prior-study and Stage 3 confirmation selections overlap")
    other = scanned - prior - confirmation
    other_sources = sorted(s["path"] for s in sources
                           if other & ids_in_path(repo, commit, s["path"], walkers))

    record = {
        "description": "LibriSpeech test utterances already used by the project (named in committed "
                       "outputs of the development repository). The TASLP-upgrade bitrate sweep excludes "
                       "all of them.",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "development_repository_commit": commit,
        "method": "git objects at the commit; files under results/ and results_paper/ with suffix "
                  + ", ".join(SCAN_SUFFIXES) + "; utterance-ID pattern " + ID_PATTERN.pattern
                  + "; speaker/chapter/utterance columns; (dataset, dataset_index) columns mapped "
                    "through the sorted file listing; intersected with the LibriSpeech test file names",
        "librispeech_test_utterances": {s: len(v) for s, v in walkers.items()},
        "counts": {"prior_study": len(prior), "stage3_confirmation": len(confirmation),
                   "other_development_outputs": len(other), "all_used": len(scanned)},
        "prior_study_selection_rule": "rows with codec == 'wav' in results/<subset>_experiment_details.csv, "
                                      "mapped as paper/run_stage3.prior_study_utterances (500 per subset, "
                                      "seed 5305)",
        "stage3_confirmation_selection_sha256": selection["selection_sha256"],
        "other_development_outputs": {"utterances": sorted(other), "sources": other_sources},
        "sources": sources,
        "prior_study": sorted(prior),
        "all_used_test_utterances": sorted(scanned),
    }
    record["record_sha256"] = body_sha256(record, "record_sha256")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1))
    print(json.dumps(record["counts"]), "->", OUT.relative_to(REPO_ROOT), record["record_sha256"])
    return 0


def ids_in_path(repo: Path, commit: str, path: str, walkers: dict[str, list[str]]) -> set[str]:
    text = git(repo, "show", f"{commit}:{path}").decode(errors="ignore")
    found = {"-".join(m) for m in ID_PATTERN.findall(text)}
    if path.endswith(".csv"):
        found |= ids_in_csv(text, walkers)
    return found


if __name__ == "__main__":
    sys.exit(main())
