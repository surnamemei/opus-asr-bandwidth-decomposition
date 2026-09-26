"""
Extract the two prior-study rows that the manuscript cites as context.

The manuscript's Introduction reports the preliminary analysis (context only): WER on
test-other rose by 1.33 pp at 12 kbit/s and by 6.63 pp at 8 kbit/s. Those values come from
the prior study's bootstrap table in the development repository's coursework outputs, which
are not part of this repository. This script copies exactly the two rows that
manuscript/tools/check_numbers.py verifies, from the git objects of one development commit,
into a sealed record with the source file's git blob and SHA-256:

    provenance/prior_study_context.json

    python provenance/derive_prior_study_context.py \
        --development-repo /path/to/development/repository --commit <sha>
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "provenance" / "prior_study_context.json"
SOURCE = "results/bootstrap_results.csv"
ROWS = [("opus", "12k", "test-other"), ("opus", "8k", "test-other")]


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--development-repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    if OUT.exists():
        raise RuntimeError(f"{OUT} is sealed and exists")
    repo = args.development_repo.resolve()
    commit = git(repo, "rev-parse", "--verify", f"{args.commit}^{{commit}}").decode().strip()
    blob = git(repo, "rev-parse", f"{commit}:{SOURCE}").decode().strip()
    data = git(repo, "cat-file", "blob", blob)
    table = list(csv.DictReader(io.StringIO(data.decode())))
    rows = []
    for codec, bitrate, dataset in ROWS:
        match = [r for r in table if (r["codec"], r["bitrate"], r["dataset"]) == (codec, bitrate, dataset)]
        if len(match) != 1:
            raise RuntimeError(f"expected one row for {codec} {bitrate} {dataset}, found {len(match)}")
        rows.append(match[0])
    record = {
        "description": "Prior-study rows cited as context in the manuscript Introduction (preliminary "
                       "analysis: wav2vec2-base-960h, raw-text scoring, different utterances; context only)",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "development_repository_commit": commit,
        "source": {"path": SOURCE, "git_blob": blob, "sha256": hashlib.sha256(data).hexdigest(),
                   "n_rows": len(table)},
        "selection": [dict(zip(("codec", "bitrate", "dataset"), r)) for r in ROWS],
        "rows": rows,
    }
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    record["record_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    OUT.write_text(json.dumps(record, indent=1))
    print(OUT.relative_to(REPO_ROOT), record["record_sha256"],
          [(r["bitrate"], r["delta_wer_pp"]) for r in rows])
    return 0


if __name__ == "__main__":
    sys.exit(main())
