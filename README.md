# How much of the ASR penalty of low-rate Opus is bandwidth loss?

[![Zenodo DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23011460.svg)](https://doi.org/10.5281/zenodo.23011460)

This is the paper repository for a decomposition of the automatic speech recognition (ASR)
penalty of 8 kbit/s Opus into two parts: a bandwidth component and a codec-specific residual.
The bandwidth component is measured with a validated linear bandwidth control.

## Research question

How much of the ASR penalty of low-rate Opus is explained by bandwidth loss, and how much
remains as a codec-specific residual beyond a validated linear bandwidth control?

At 8 kbit/s, libopus 1.4 encodes speech in SILK narrowband mode. The control (LP) is a
zero-phase linear low-pass filter fitted to SILK narrowband's measured linear transfer
function. It was calibrated on LibriSpeech dev-clean and validated on held-out speakers before
any recognition experiment. Along the path REF → LP → OPUS:

- LP − REF is the bandwidth component;
- OPUS − LP is the codec-specific residual.

## Main result (Stage 3, frozen)

The design was pre-registered and paired: a pilot, then one confirmatory run on 2,174
LibriSpeech test utterances from 73 speakers. Two pretrained recognisers were used without
adaptation. Intervals are 95 % speaker-bootstrap intervals. The pre-declared decision rule
returned GO.

| Corpus WER contrast | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| Bandwidth component, LP − REF | +0.14 pp [0.04, 0.25] | +1.40 pp [0.99, 1.92] |
| Codec-specific residual, OPUS − LP | +0.69 pp [0.46, 0.94] | +2.07 pp [1.68, 2.57] |
| Bandwidth share of the total Opus penalty | 17 % [5, 29] | 40 % [35, 45] |
| High-rate SILK narrowband (40 kbit/s) − LP | +0.02 pp [−0.04, +0.08] | −0.09 pp [−0.20, +0.02] |

How to read these results:

- In this setting, bandwidth removal accounted for 17 % and 40 % of the total penalty.
- The decomposition is sequential, so any interaction between band limitation and coding
  falls into the residual.
- High-rate SILK narrowband showed no detectable pooled residual. No equivalence margin was
  pre-declared, so this is not a claim of equivalence.
- The residual consisted mainly of substitutions. It is consistent with low-rate in-band coding
  distortion; the mechanism was not isolated.
- All codec results are defined for libopus 1.4 decoded by FFmpeg 6.1.1.

## TASLP upgrade results (sealed)

Two additions were pre-registered after Stage 3 closed (`paper/taslp_upgrade/00_UPGRADE_PLAN.md`,
with amendment 01) and run once each. Both pre-declared rules returned GO in both recognisers.
The Stage 3 estimates and decision are unchanged.

| Addition | Result (pp, 95 % speaker-bootstrap intervals) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|---|
| A: level-matched OPUS | OPUS8_LEVEL_MATCHED − LP | +0.70 [+0.47, +0.95] | +2.09 [+1.71, +2.57] |
| A: level-matched OPUS | OPUS8_LEVEL_MATCHED − OPUS | +0.012 [−0.007, +0.032] | +0.018 [−0.028, +0.062] |
| B: SILK-NB bitrate sweep | Residual at 8 kbit/s, SILK8 − LP | +0.55 [+0.37, +0.74] | +2.07 [+1.65, +2.55] |
| B: SILK-NB bitrate sweep | Residual at 40 kbit/s, SILK40 − LP | +0.03 [−0.05, +0.11] | −0.06 [−0.21, +0.09] |
| B: SILK-NB bitrate sweep | Slope on log2 bitrate (pp per doubling) | −0.21 [−0.27, −0.15] | −0.85 [−1.07, −0.66] |

- **A is a post-confirmation sensitivity analysis, not a second confirmatory test.** It decoded
  the 2,174 Stage 3 confirmation utterances a second time. Matching the RMS level of the Opus
  signal to the control did not remove the residual in either recogniser.
- **B is a fresh-utterance, not fresh-speaker, holdout:** 1,665 test utterances never used
  before, from 70 of the Stage 3 test speakers. Within forced SILK narrowband, the residual
  decreased as the bitrate rose from 8 to 40 kbit/s. This supports, but does not isolate, the
  low-rate in-band coding distortion interpretation: in-band distortion, level and the 4–5 kHz
  image all change with the rate.

**Positioning** (`manuscript/novelty_boundary.md`). Earlier studies separated band limitation
from coding distortion for telephone channels, GSM, AMR and MP3. This work applies the same
logic to 8 kbit/s Opus, with a control fitted to the codec's measured linear response and
validated on held-out speakers, and with two current pretrained recognisers. It makes no
priority claim.

## Status

- **Stages 1–3:** complete. All outputs are sealed and unchanged.
- **Manuscript:** revised draft (`manuscript/manuscript.md`) with both upgrade additions. Every
  reported number is checked against the sealed outputs.
- **TASLP upgrade:** complete and sealed. The plan (`paper/taslp_upgrade/00_UPGRADE_PLAN.md`)
  and amendment 01 (`paper/taslp_upgrade/amendments/`, a correction of the plan's wav2vec2
  level-invariance expectation that changes no estimand, gate, threshold, condition, selection
  or rule) were fixed before any evaluation utterance was decoded. Every step ran once, in the
  frozen order:
  - U1–U2: calibration on the 20-utterance Stage 3 calibration set, then the code freeze
    (`results_paper/taslp_upgrade/code_freeze.json`, `freeze_manifest.json`);
  - U3–U5, addition B: validation gates V1–V5 passed, one ASR run, sealed decision GO
    (`results_paper/taslp_upgrade/sweep/`);
  - U6–U8, addition A: gates A1–A3 passed, one ASR run, sealed decision GO
    (`results_paper/taslp_upgrade/level/`).
- **No further experiment is planned or running.**

## Repository structure

```
manuscript/         manuscript.md, references.bib, figures/, tools/ (make_tables.py,
                    check_numbers.py, figure scripts, render.sh), planning and audit notes
paper/              Stage 1-3 code and tests (unchanged since the Stage 3 freeze)
paper/taslp_upgrade/  frozen upgrade plan (upgrade_spec.json, 00_UPGRADE_PLAN.md,
                    selection_sweep.json), amendments/, runners, statistics, pre-run checks
                    and tests (frozen; all steps run)
results_paper/      sealed Stage 1-3 outputs (reproduce/, opus_validation/,
                    lowpass_validation/, lowpass_confirmation/, stage3_asr/, STAGE_STATUS.md);
                    taslp_upgrade/ (calibration/, code freeze, sweep/ for addition B,
                    level/ for addition A; all sealed)
provenance/         PROVENANCE.md, used_test_utterances.json (test utterances already used),
                    prior_study_context.json (two cited prior-study rows), derivation scripts
```

## Reproducibility and provenance

- **Sealed records.** Each sealed JSON record carries the SHA-256 of its own body (for example
  `spec_sha256`, `selection_sha256`, `decision_sha256`). Output directories carry an
  `outputs_sha256.json` manifest. The Stage 3 code hashes are sealed in
  `results_paper/stage3_asr/confirmation_freeze.json`.
- **Nothing sealed is edited.** Corrections are new, dated files.
- **Decoded once.** Every evaluation set was decoded once. A new experiment needs a sealed,
  committed specification before any of its evaluation audio is decoded.
- **Development history.** It is not part of this repository.
  `provenance/PROVENANCE.md` summarises the development sequence and lists the development
  commits and frozen hashes. It also lists which Stage 1 checks need the development repository.
- **Data.** LibriSpeech is not included. The code expects it at `data/LibriSpeech`, which may
  be a symlink and is ignored by git.
- **Environment.** Python 3.12 with `requirements.txt`, libopus 1.4 and FFmpeg 6.1.1. The
  complete frozen environment is `results_paper/stage3_asr/requirements-lock.txt`.

### Checks

```
python manuscript/tools/check_numbers.py
python -m unittest discover -s paper/taslp_upgrade/tests -t paper/taslp_upgrade/tests
python -m unittest discover -s paper/tests -p "test_[los]*.py"
```

- The first command checks every table row and number in the manuscript against the frozen
  outputs, applies the wording rules, and resolves every citation key.
- The second runs the upgrade tests: statistics, rules, the integrity of the frozen plan and its
  amendments, and, since the code freeze, that no file hashed by the freeze manifest has changed.
- The third runs the Stage 2–3 unit tests, which use synthetic signals only.
- `test_stage3.py`'s prior-study exclusion test and `paper/tests/test_equivalence.py` (Stage 1)
  need the coursework `src/` and `results/` of the development repository. See
  `provenance/PROVENANCE.md`.
- The manuscript renders with `manuscript/tools/render.sh`, which needs pandoc and xelatex.
