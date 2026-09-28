# Submission metadata (IEEE/ACM TASLP)

<!-- Prepared for the TASLP submission of manuscript/taslp_submission.md and taslp_supplement.md.
Placeholders in [brackets] must be completed by the authors; no author detail is invented here.
The abstract and index terms below are copied from the built manuscript (tools/build_submission.py). -->

## Title

How much of the ASR penalty of 8 kbit/s Opus is bandwidth loss? A decomposition with a validated bandwidth control

The manuscript title is unchanged in this pass. Two alternatives are offered for decision below; the
manuscript has **not** been retitled.

**Alternative titles (for decision):**

1. *Bandwidth Removal Reproduces Only Part of the ASR Penalty of 8-kbit/s Opus.* This is
   statement-style. It uses "reproduces" rather than "explains" because the paper attributes rather
   than identifies causes.
2. *Separating Bandwidth Loss from Other Coding Effects in the ASR Penalty of 8-kbit/s Opus.* This
   is descriptive and scope-accurate, and it names the method rather than the result.

**Recommendation:** alternative 1 if a statement-style title is wanted. It matches the primary
claim and avoids putting a share in the title. Otherwise keep the current title, whose question
form is answered with qualifications in the paper.

## Short title (running head)

Bandwidth Loss and the ASR Penalty of 8-kbit/s Opus

## Article type

Regular paper. The main text is 12 pages in the IEEE two-column journal format, including
references (TASLP limit 13), with a separate 6-page supplementary document.

## Abstract (208 words; SPS limit 150–250)

Low-bitrate narrowband codecs remove bandwidth and introduce other distortions at the same time, which makes their penalty on automatic speech recognition (ASR) hard to attribute. We quantify this for Opus at 8 kbit/s (SILK narrowband in libopus 1.4) with a zero-phase low-pass control fitted to SILK narrowband's measured high-rate linear transfer function and validated on unseen speakers. In a paired design specified and version-sealed before any evaluation audio was decoded (a pilot, then one confirmatory run on 2,174 LibriSpeech test utterances from 73 speakers), removing the bandwidth with the control increased corpus WER by 0.14 percentage points (pp) for Whisper large-v3 and 1.40 pp for wav2vec2-base-960h, whereas Opus added a further 0.69 and 2.07 pp (95 % speaker-bootstrap intervals excluding zero): the control reproduced only a minority of the penalty. A more inclusive best-linear sensitivity analysis, which assigns the gain, spectral tilt, roll-off, phase and delay of the actual codec output to the linear component, still left residual penalties of 0.74 and 2.32 pp. The residual also exceeded the bandwidth component under four error weightings, although the exact share, particularly for Whisper, depends on the attribution path and the metric. Level matching, a bitrate sweep, and decoder and application-mode sensitivities further constrain, but do not identify, the mechanism.

## Index terms / keywords

speech recognition, speech coding, Opus, bandwidth limitation, robustness, Whisper, wav2vec 2.0

## Candidate EDICS categories

These are candidates only. Verify the codes and names against the EDICS list currently shown in
the TASLP submission system before selecting.

1. **SPE-ROBU**: robust speech recognition. This is the primary candidate: recognition under codec
   degradation.
2. **SPE-CODI**: speech coding. Opus/SILK narrowband, bitrate and bandwidth allocation.
3. **SPE-GASR**: general topics in speech recognition. Evaluation methodology for pretrained
   recognisers.

## Authors and declarations (placeholders)

- **Authors:** [Author 1], [Author 2], … (order to be confirmed)
- **Affiliations:** [Affiliation of each author]
- **Corresponding author:** [Name, postal address, e-mail]
- **ORCID:** [ORCID iD of each author]
- **Funding statement:** [Funding sources and grant numbers, or "This work received no specific
  funding."]
- **Conflict-of-interest statement:** [The authors declare that they have no competing interests.
  Confirm or replace.]
- **Disclosure of AI-assisted content:** [IEEE policy requires any use of AI-generated content
  (text, figures, code) to be disclosed in the Acknowledgments. The review version of the
  manuscript currently has no Acknowledgments section. The authors should add one with an
  accurate disclosure before submission.]

## Data and code availability

**Review (double-blind) version.** This wording is used in the manuscript's Reproducibility
statement:

> Code and sealed analysis records are available in an anonymised review repository at
> [ANONYMOUS_REPOSITORY].

**Post-acceptance (non-blind) version.** This wording replaces the sentence above after
acceptance:

> Code, sealed analysis records and per-utterance outputs are available at [PUBLIC_REPOSITORY].

No URL has been created or assumed. LibriSpeech, the recogniser checkpoints (pinned revisions),
libopus 1.4 and FFmpeg 6.1.1 are public.

## Supplementary material

A single PDF of 6 pages, built from `taslp_supplement.md`. It contains Sections S1–S10 and
Tables S1–S14:

- validation of the bandwidth control (S1);
- the pilot (S2);
- additional confirmation results: per-subset WER, error types, negative controls and signal
  descriptors (S3);
- level matching (S4);
- the coding-rate sweep (S5);
- the inclusive best-linear attribution (S6);
- the decoder, application-mode and bandwidth-allocation analyses (S7);
- error weighting (S8);
- the two attribution analyses stopped before ASR (S9);
- amendments and deviations (S10).

Gate-by-gate records, hashes, manifests and logs are in the repository, not in the supplement.
