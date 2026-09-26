# Provenance

This repository is the permanent paper repository. It was initialised on 2026-09-26 from a
separate development repository and holds only the paper-relevant materials. The development
Git history, including every commit and tag named below, is **not** part of this repository.
The identifiers below let anyone with access to the development repository check the record.
The sealed files in `results_paper/` let anyone check the frozen outputs from this repository
alone.

## 1. What was migrated, and what was not

| Migrated | Notes |
|---|---|
| `manuscript/` | Manuscript, bibliography, figures, rendering and checking tools, planning and audit notes |
| `paper/` | Stage 1–3 code and tests, unchanged; the TASLP-upgrade plan in `paper/taslp_upgrade/` (new) |
| `results_paper/` | Sealed Stage 1–3 outputs, unchanged |
| `provenance/` | This record; the list of test utterances already used; a two-row extract of the prior study cited as context (new) |

- Every migrated file under `manuscript/`, `paper/` (Stage 1–3) and `results_paper/` is
  byte-identical to its committed version at development commit
  `051a96330c244804714c5e49faed997339ece987`. The one exception is
  `manuscript/tools/check_numbers.py`, adapted as described below.
- Two resumable Stage 3 checkpoints (`progress.jsonl` of the calibration and pilot runs) were
  not migrated. No seal covers them. The confirmation checkpoint had already been removed from
  version control in the development repository.
- `.gitignore` and `requirements.txt` were rewritten for this repository.
- Not migrated: the coursework code (`src/`), the coursework outputs (`results/`), coursework
  documents and reports, site files, build artefacts, and LibriSpeech.
- One tool was adapted: `manuscript/tools/check_numbers.py`. It reads the two prior-study rows
  it verifies from `provenance/prior_study_context.json` instead of the coursework `results/`
  (section 6). The tool is not a frozen output, and no checked value changed.

## 2. Development sequence

All development commits are on the development repository's paper branch.

| Step | What was done | Outcome | Evidence here | Development commit |
|---|---|---|---|---|
| Stage 1 | Reproduction of the frozen preliminary pipeline (wav2vec2-base-960h, Opus via FFmpeg) before any intervention | PASS: 250/250 checks | `results_paper/reproduce/` (`equivalence_report.md`, `frozen_hashes.json`) | `8a77f412ee8ac779e5230d1d5a8df3cb0e027286` |
| Stage 2A | Controlled Opus bandwidth manipulation: direct libopus 1.4 encoding with every control set and read back; forced NB versus WB at 8 and 12 kbit/s. No ASR | PASS: 7/7 gates | `results_paper/opus_validation/` | `d70c9938481415d4016336fb4ad4bb58a5b9ee74` |
| Stage 2B-v1 | Linear low-pass control fitted to SILK-NB's measured linear transfer function (calibrated on dev-clean), validated on dev-clean and dev-other. No ASR | **FAIL** on the original Gate 5, which was internally inconsistent with the linear-only definition. Kept unchanged as the historical record | `results_paper/lowpass_validation/` | `d70c9938481415d4016336fb4ad4bb58a5b9ee74` |
| Stage 2B | Corrected criterion: only the inconsistent sub-criterion was removed, and the 3 dB tolerance against the linear SILK-NB reference was kept. Frozen before the confirmation data were downloaded, then confirmed once on 40 unseen train-clean-100 speakers with the filter taps unchanged. No ASR | PASS under the corrected specification, independently confirmed | `results_paper/lowpass_confirmation/`, `results_paper/STAGE_STATUS.md` | tag `paper-stage2b-confirmed` (tag object `ebcf06bab238a09ea891215de36483ac1ed3dce8`) on `d70c9938481415d4016336fb4ad4bb58a5b9ee74` |
| Stage 3 freeze | Specification, data split (calibration / pilot / confirmation) and code sealed before any pilot or confirmation utterance was decoded | Sealed | `results_paper/stage3_asr/stage3_spec.json`, `00_FROZEN_STAGE3_SPEC.md`, `selection_*.json` | `ef072e5c188b91a4b96f03ad98a89d640ab349aa` |
| Stage 3 pilot | 138 utterances (69 dev speakers) decoded once; pre-declared kill test; analysis code sealed again (confirmation freeze) | PROCEED | `results_paper/stage3_asr/pilot/`, `confirmation_freeze.json` | `a51ea54503f951d39688837305d44f82077c4536` |
| Stage 3 confirmation | 2,174 test utterances (73 speakers) decoded once and analysed with the frozen code | GO (pre-declared rule) | `results_paper/stage3_asr/` (`stage3_decision.json`, `01_stage3_summary.md`, `07_paired_bootstrap.csv`, `raw/confirmation/`) | `d612bdb6fe1936c8b5029a7999bbe185275edb10` |
| Interpretation note | Dated correction of interpretation wording; no output changed | – | `results_paper/stage3_asr/01b_interpretation_note_2026-09-26.md` | `d612bdb6fe1936c8b5029a7999bbe185275edb10` |
| Literature audit | Positioning audit and frozen positioning | `NOVELTY_NARROW_BUT_DEFENSIBLE` | `manuscript/novelty_boundary.md`, `literature_matrix.md`, `related_work_notes.md` | `0644d480cf86b64ca9c81f583f2524417a047cf7` |
| Manuscript | Draft 1 from frozen evidence only; rendered assets; editorial pass (figures regenerated from frozen files only) | Complete draft | `manuscript/` | `7d76286d1e1646a85ff5e469d0246f20d068a8ed`, `04a13ad8c70d3b0710dbe594d30a5acc12f819f6`, `c49e1e90327fc210cbcfcd44ba6d9589df177ce4` |
| Last development commit | Removal of outdated project documents | – | – | `051a96330c244804714c5e49faed997339ece987` |
| TASLP upgrade (this repository) | Plan for two additions frozen; nothing decoded | Planned, not run | `paper/taslp_upgrade/` | this repository |
| TASLP upgrade U1–U2 (this repository) | Calibration on the 20-utterance Stage 3 calibration set only: E1, E2 and supplementary checks (run 1 FAIL on the wav2vec2 level-invariance expectation alone, kept unchanged); amendment 01 corrects that expectation (section 3.5); checks re-run; code freeze | E1, E2 PASS; every freeze gate PASS; code frozen; no evaluation utterance decoded | `results_paper/taslp_upgrade/`, `paper/taslp_upgrade/amendments/` | this repository |

## 3. Frozen identifiers

Each value can be checked from the sealed files in this repository. Sealed JSON records carry
the SHA-256 of their own body under the key shown: the hash of
`json.dumps(record without that key, sort_keys=True)`. Output manifests
(`outputs_sha256.json`) list the SHA-256 of every output file.

| Item | SHA-256 | Where |
|---|---|---|
| Stage 2B frozen filter taps | `583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16` | `lowpass_validation/frozen_filter.json` (`taps_sha256`) |
| Stage 2B original tolerance set (2B-v1) | `bc91d298ac402bbed082dfd71de0ec4dc15d0c1419261a7fdac6ca6a88c49833` | `STAGE_STATUS.md` |
| Stage 2B revised specification | `166f5672263373ece22a955baf3b2e1f3c7ac7c9ce14098f9daa65938d9055ff` | `lowpass_confirmation/revised_spec.json` (`spec_sha256`) |
| Stage 2B confirmation selection | `0dfc09813d018c3f5026da7723cec3222fe14c957289f126e6aa3108e9932212` | `lowpass_confirmation/selection.json` (`selection_sha256`) |
| Stage 3 specification | `ac5a36a01f50e7643cc73bbbc2f75ce44fe34b0730ec828082084ba1643b5219` | `stage3_asr/stage3_spec.json` (`spec_sha256`) |
| Stage 3 selections: calibration / pilot / confirmation | `f966a4399ec2ea68db9a11a68ef6942524acd2e6c184f85220cc87cf0af8c79b` / `94fee5a6bde157bc818ca50dbb933442eb5dfc64506a033f48763df387ea0aea` / `f41dcc20bd6e94a83444d632f19a186c564233906c7d252c24e79d4de6355da5` | `stage3_asr/selection_*.json` (`selection_sha256`) |
| Stage 3 pilot decision | `fb63d2fa95e5998e67b66475a511af4461416b587475972cbf7b95168e16ea61` | `stage3_asr/pilot/pilot_decision.json` (`decision_sha256`) |
| Stage 3 confirmation freeze | `7beca2163329d259ccf169293f3173115ec8da474e5c372e46f15b93dfaaf39b` | `stage3_asr/confirmation_freeze.json` (`freeze_sha256`); it also holds the SHA-256 of the 11 Stage 3 code files |
| Stage 3 decision (GO) | `608c919c33e135bb7ca236e2e07e1c9b1b567285a5b1d9d8caabedeb08cb3a41` | `stage3_asr/stage3_decision.json` (`decision_sha256`) |
| Stage 3 paired bootstrap table | `aaa556b987e5c33b0f1c419561de78e81e1971c93e90c0cccc73db135b1a6644` | file hash of `stage3_asr/07_paired_bootstrap.csv`, recorded in the decision |
| Stage 3 output manifests: calibration / pilot / confirmation | `3ae2f98149f483ee60bcf46516e2beec366d7a599738e53875fcc616f5a53100` / `df65e8cbe2fa8be245b1e0520b930487923fd3f9996705973ba9330bcd0d6a3b` / `de82f749b6a1446ff45cfed187c59fdd7da0feb8aa459f035d1108b0893b8d17` | `stage3_asr/{calibration,raw/pilot,raw/confirmation}/outputs_sha256.json` |
| Stage 3 environment lock | `745b91dd04708e7226ac691191c33f4118b316248335f778ee0af0d87357d45f` | file hash of `stage3_asr/requirements-lock.txt` |

`results_paper/reproduce/frozen_hashes.json` records the hashes of the development
repository's coursework `src/` and `results/` trees before and after Stage 1. It shows that
Stage 1 changed neither tree.

## 4. What still depends on the development repository

- `paper/run_reproduce.py` (Stage 1) and `paper/tests/test_equivalence.py` compare
  `paper/common.py` with the coursework `src/` and read the coursework `results/`. They cannot
  be re-run here. Their sealed outputs (`results_paper/reproduce/`) are included.
- `paper/run_stage3.py select` read the prior-study selection from the coursework `results/`.
  Its sealed selections are included and are never recomputed. The same dependency makes
  `paper/tests/test_stage3.py` (`TestSelections.test_confirmation_excludes_prior_study`)
  unrunnable here. The equivalent check in this repository is
  `paper/taslp_upgrade/tests/test_plan.py` (`TestUsedRecord`), which reads the list below.
- The `environment.json` files of Stages 1–2 record absolute paths of the development
  environment. They are historical records.
- Sealed Stage 1–3 files and the Stage 1–3 code refer to the prior study by its original
  coursework label. They cannot be edited without breaking their seals and code hashes, so they
  are kept verbatim.

## 5. Test utterances already used

`provenance/used_test_utterances.json` (sealed, `record_sha256`) lists every LibriSpeech test
utterance that the project has encoded, decoded or recognised. It was derived by
`provenance/derive_used_test_utterances.py` from the git objects of development commit
`051a96330c244804714c5e49faed997339ece987`. The derivation read every committed file under the
coursework `results/` and under `results_paper/`, using three sources: the utterance-ID
pattern, speaker/chapter/utterance columns, and (dataset, dataset_index) columns mapped through
the sorted file listing. Each source file is listed with its git blob and SHA-256.

| Category | Utterances |
|---|---|
| Prior-study selection (500 per test subset) | 1,000 |
| Stage 3 confirmation selection | 2,174 |
| Other development outputs (two early exploratory runs on the first test-clean utterances) | 2 |
| All used test utterances | 3,176 |

The TASLP-upgrade bitrate sweep excludes all of them (see `paper/taslp_upgrade/00_UPGRADE_PLAN.md`).

## 6. Prior-study context numbers

The Introduction cites the preliminary analysis as context only: WER on test-other rose by
1.33 pp at 12 kbit/s and by 6.63 pp at 8 kbit/s. `provenance/prior_study_context.json` (sealed,
`record_sha256`) holds exactly the two rows of the prior study's bootstrap table that
`manuscript/tools/check_numbers.py` verifies. It records the development commit, the source
path, the git blob and the SHA-256 of the full source file. It was written by
`provenance/derive_prior_study_context.py` from the git objects of development commit
`051a96330c244804714c5e49faed997339ece987`.

## 7. Policy

- Sealed files, output manifests and the Stage 1–3 code are never edited. Any correction is a
  new, dated file.
- Every evaluation set was decoded once. Resumable checkpoints are allowed, are logged, and are
  not tracked.
- A new experiment needs a sealed specification committed before any of its evaluation audio is
  decoded. The TASLP-upgrade plan follows this rule.
