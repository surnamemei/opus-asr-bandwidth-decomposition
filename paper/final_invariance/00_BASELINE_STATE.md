# Pre-submission invariance pass: baseline state (2026-09-27 16:10 UTC)

## Repository

- Branch of this pass: `pre-submission-invariance-pass`.
- Exact parent commit: `85ea991` ("Record sealed reference-decoder R4 sensitivity results"), the
  head of `taslp-upgrade-freeze` when the pass started. The sealed R4 outputs were already
  committed.
- First commit of the branch: `e65e3c6`, a manuscript-only checkpoint. It holds the uncommitted R4
  integration draft of the TASLP submission (8 manuscript and tooling files) and is kept separate
  from every scientific commit.
- Untracked files at the start: none.

## Frozen records (verified before any new analysis: `python paper/final_invariance/verify_frozen.py`)

- 52 self-sealed JSON records verify; 7 sealed output manifests match their files.
- Stage 3: spec `ac5a36a0…`, decision `608c919c…`, outcome GO. Code, seals, manifests and
  selections are intact.
- TASLP upgrade:
  - plan `0d5d5c71…`, code freeze `af54518c…`;
  - freeze manifest: 0 mismatches; amendment 01 intact;
  - Addition A GO, Addition B GO.
- R1–R3:
  - plan `2a6eae35…`, code freeze `dc271f29…`;
  - R1 STOPPED, R2 STOPPED;
  - R3: Whisper NO_CLEAR_DIFFERENCE, wav2vec2 WB_BETTER.
- R4:
  - plan `1e3f95ec…` and code freeze `ae16b7e4…`, both committed;
  - Whisper DECODER_LOWER_PENALTY, wav2vec2 NO_CLEAR_DECODER_DIFFERENCE.

## Checks and tests at the start

- `build_submission.py --check`: PASS (both submission files reproduce byte for byte).
- `check_numbers.py --submission` and `check_numbers.py` (draft 2): PASS.
- Tests:
  - R4: 17 run, OK, 1 skipped.
  - R1–R3: 33 OK.
  - TASLP upgrade: 80 OK, 3 skipped.
  - Stage 2–3 expected set (`-p "test_[los]*.py"`): 62 run, 1 error.

The Stage 2–3 error (`test_confirmation_excludes_prior_study`) is the known repository-hygiene
issue: it reads the prior study's `results/` files, which are deliberately not in this repository.
`test_equivalence.py` is excluded for the same reason, because it needs the prior study's `src/`.
Neither is a scientific failure.

## GPU at the start

RTX 5090: 4.0 GiB used of 31.8 GiB, 4 % utilisation, and no other major GPU job running.
