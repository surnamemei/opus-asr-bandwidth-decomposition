# Final check report: pre-submission invariance pass (2026-09-28)

Branch `pre-submission-invariance-pass`. The pass started from parent commit `85ea991`. This
report is committed after branch head `4d2395f`. The user pushes manually; nothing was pushed.

## 1. Verifiers and checks

| Check | Result |
|---|---|
| `python paper/final_invariance/verify_frozen.py` (every self-sealed JSON, every output manifest, Stage 3 integrity, all code freezes; R1/R2 STOPPED asserted) | **PASS**: 69 self-sealed records (52 at baseline + 17 from this pass), 9 output manifests (7 + 2) |
| `python manuscript/tools/build_submission.py --check` (both submission files reproduce byte for byte from draft 2 and the generated tables) | **PASS** |
| `python manuscript/tools/check_numbers.py --submission` (every table row and number of the submission and supplement against the sealed outputs; wording rules; figure paths; citation keys) | **PASS**: 195 table rows |
| `python manuscript/tools/check_numbers.py` (draft 2) | **PASS**: 98 table rows |
| Draft 2 (`manuscript/manuscript.md`) unchanged since `dbf8d5c` | **yes** (empty diff) |
| LaTeX logs of both renders: undefined references or citations | **none** (only the usual Times font-substitution warnings) |

## 2. Tests

Run with `python -m unittest discover -s <dir> -t <dir> [-p <pattern>]`.

| Suite | Run | Result | Baseline |
|---|---|---|---|
| R4 (`paper/decoder_sensitivity/tests`) | 17 | OK (1 skipped) | same |
| R1–R3 (`paper/reviewer_sensitivity/tests`) | 33 | OK | same |
| TASLP upgrade (`paper/taslp_upgrade/tests`) | 80 | OK (3 skipped) | same |
| Stage 2–3 expected set (`paper/tests`, `-p "test_[los]*.py"`) | 62 | **1 error** (known, below) | same |
| Final invariance A1/B1/C1 (`paper/final_invariance/tests`) | 22 | OK (2 skipped) | new |

**Known failure (repository hygiene, not a scientific failure).**

- `test_stage3.TestSelections.test_confirmation_excludes_prior_study` reads
  `results/test-clean_experiment_details.csv` from the prior study's development repository. That
  file is deliberately not in this repository. The error is unchanged from the baseline.
- `paper/tests/test_equivalence.py` (Stage 1) needs the prior study's `src/` for the same reason,
  and is outside the expected set.
- Neither was "fixed" by changing any science.

**Skips.**

- The two new skips are by design: the "evaluation needs the commit" guards of A1 and B1 skip
  once their plans and code freezes are committed.
- The R4 and TASLP-upgrade skips are the same as at baseline.

## 3. Commits of the pass (oldest first)

| Commit | Content |
|---|---|
| `e65e3c6` | Checkpoint of the uncommitted R4 manuscript integration draft (editorial only; kept separate from science) |
| `a7bddc3` | Baseline state record and read-only verifier |
| `ec784a2` | C1 metric and weighting audit (sealed; no new ASR) |
| `6dd879d` | A1 plan, method note, signal selection, calibration, code freeze and held-out validation, sealed and committed before any confirmation-set LIN8 audio |
| `569c66a` | A1 evaluation, recognition, decision and report (ROBUST_RESIDUAL) |
| `25d81fa` | B1 plan, calibration and code freeze |
| `00ce368` | B1 pre-recognition validation (committed before recognition, as the plan requires) |
| `43ca46b` | Rounding correction in the A1 report (one table value; no sealed record touched) |
| `e6bab8a` | B1 recognition, decision and report (NO_CLEAR_APPLICATION_DIFFERENCE) |
| `37e8806` | D1 not run: record and reasons |
| `9ba14b4` | Final adversarial audit and organising-hypothesis note |
| `853bbee` | Rounding correction of Whisper's VoIP total in the B1 report and the audit (+0.70, not +0.71) |
| `4d2395f` | Manuscript integration (draft 2 unchanged; builder, tables, checks, claims register) |
| (this commit) | Final check report |

- **Deviation from the prescribed sequence.** C1 was committed before A1 because the shared GPU
  was occupied by other projects' jobs for about 1.5 h. C1 needs no GPU and is independent of A1
  and B1; committing it early also timestamps it before any A1 or B1 result existed.
- **Failed analyses.** None of the pass failed. No failed analysis was squashed or deleted in
  earlier history (R1/R2 STOPPED records are intact).

## 4. Sealed records of this pass (all verified)

| Record | Key | SHA-256 |
|---|---|---|
| `paper/final_invariance/selection_a1_signal.json` | selection_sha256 | `354439bd16ae73661c268b5557b7727845f6d81aba039d2e873966a427c8bcbe` |
| `paper/final_invariance/A1_SPEC.json` | spec_sha256 | `77da2190c2115548b654f6aeb2abd0dfa21b54fbabed7100f103aa91560d8edb` |
| `paper/final_invariance/A1_CODE_FREEZE.json` | freeze_sha256 | `819eec0b543419841bb43045a958e1d86a656f51731972a5e5969036c090e3b1` |
| `results_paper/final_invariance/a1_calibration/signal_report.json` | report_sha256 | `9aec2d21681be71d2f681eaf77c48eccbff120b2a9d943eb16695cc8d96f07b7` |
| `results_paper/final_invariance/a1_calibration/asr_report.json` | report_sha256 | `7aa6112489ecaa1f1dfb5eb872886c8918878621f1df5c9d9a1fc9f70d5521be` |
| `results_paper/final_invariance/a1_validation/validation_report.json` | report_sha256 | `ae976ec889eb4545b0cc665b5fb64391b1e4f56ce8de424b3585f0a3f925ace7` |
| `results_paper/final_invariance/a1_evaluation/evaluation_report.json` | report_sha256 | `863e60122d84df38fbdd50c8ef9140db243a430acc3c518ff37c70163701ee61` |
| `results_paper/final_invariance/a1_raw/outputs_sha256.json` | outputs_sha256 | `ef160ab04f0f10195b13dc30527ea1f4c28ae2b6d1cf58f0b0dd58082b2342b2` |
| `results_paper/final_invariance/A1_DECISION.json` | decision_sha256 | `7b60320cc6079c916e54c4548bb3b87140b4d5d74ba7f6d37f7b4853d3951d8c` |
| `paper/final_invariance/B1_SPEC.json` | spec_sha256 | `42504ce4bb2675c26693d91d6cc4f0c4c3c1de5c9778e0e7c9530ca2a587b4aa` |
| `paper/final_invariance/B1_CODE_FREEZE.json` | freeze_sha256 | `b811a4a380feb6e841e0523e7c1d3bbb172c0d06dad806ed34d46fec6c00bb93` |
| `results_paper/final_invariance/b1_calibration/encode_report.json` | report_sha256 | `f2617b4f592bf0a0b9919b796a04930a90fb2384530be417ffa61376656242a9` |
| `results_paper/final_invariance/b1_calibration/asr_report.json` | report_sha256 | `7a62b1167c87d4a56d264046805a67e8c4fb03994917023256bd6ea0ed8c5a18` |
| `results_paper/final_invariance/b1_validation/validation_report.json` | report_sha256 | `211bb0a1a1807ea5fd80b0fb4ad22be8ae5652932c3741d711618f1ba447ab92` |
| `results_paper/final_invariance/b1_raw/outputs_sha256.json` | outputs_sha256 | `cf0a5030223b844e7b2b05adcaeeb9aa2eae92bcb2b156cc1142476a908c5f95` |
| `results_paper/final_invariance/B1_DECISION.json` | decision_sha256 | `863e9c9108a26f752532ea9b6e9606d447b57db3869ffbec5eecdc922eb966c2` |
| `results_paper/final_invariance/C1_RECORD.json` | record_sha256 | `0981f5af737194932118d3145fda7509b39494a20cc80301179227953a850b7b` |

Sealed CSVs, each tied to its record by hash:

- `c1_metric_table.csv`: `043260f4…`
- `a1_bootstrap.csv`: `f7fd453d…`
- `b1_bootstrap.csv`: `bce9f577…`

## 5. Page counts (IEEE journal, 10 pt; body text not reduced; figure and table text at 8 pt)

- **Main paper** (`taslp_submission.md`, two columns): **13 pages** including references
  (limit 13). The abstract has 242 words (SPS limit 150–250).
- **Supplement** (`taslp_supplement.md`, two columns): **9 pages**. **The target of ≤ 6 was not
  met.**
  - The supplement now carries the gate mechanics, rule thresholds and outcome labels moved out of
    the main paper, plus three new analyses (Sections S9–S11, Tables S18–S24).
  - To save space, the redundant Figs. S1–S3 (re-plots of tabulated numbers) were dropped and
    procedural prose (S6, and the S7 and S8 deviation lists) was condensed.
  - Reaching 6 pages would require removing secondary evidence tables. Reviewers cannot see the
    repository ("link withheld for review"), so they were kept.
  - One-column rendering is not shorter (8–9 pages).
- **Render commands:**
  - `OUT=build/ieee_taslp_submission tools/render_ieee.sh taslp_submission.md`
  - `OUT=build/ieee_taslp_supplement EXTRA_HEADER=tools/ieee-supplement.tex tools/render_ieee.sh taslp_supplement.md`
  - Both run from `manuscript/`. The 85 % supplement figure scaling was removed from
    `tools/ieee-supplement.tex`.

## 6. Frozen records

- **No historical frozen record was modified.**
  - `git diff --name-status 85ea991..HEAD -- results_paper paper` lists only additions under
    `final_invariance/`.
  - `verify_frozen.py` passes for every sealed record and manifest of every stage.
  - Draft 2 is unchanged.
- **R1 and R2 remain STOPPED**, and are asserted by the verifier.
- **Stage 3 remains the primary pre-specified decomposition.**
- **Corrections of this pass were made in unsealed report files only**, and are recorded in
  commits `43ca46b` and `853bbee`.
- **Execution deviations are recorded in `A1_DEVIATIONS_2026-09-28.md`.**
  - A1 ran with single-threaded BLAS, with last-bit effects only.
  - Two A1 validation attempts were stopped before any output was written.
  - B1's changes between plan seal and code freeze are listed in `B1_CODE_FREEZE.json`.
