---
title: "Supplementary material for: How much of the ASR penalty of 8 kbit/s Opus is bandwidth loss? A decomposition with a validated bandwidth control"
author: "[Authors withheld for review]"
date: "TASLP submission version, 2026-09-27"
---

<!--
SUPPLEMENTARY MATERIAL of the TASLP submission version (taslp_submission.md). Material moved out of draft 2 without
changing any claim, number or caveat; checked with `python manuscript/tools/check_numbers.py --submission`.
-->

```{=latex}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\thesection}{S\arabic{section}}
\suppressfloats[t]
```

This supplement gives the tables, figures and diagnostics moved out of the main paper. Sections,
tables and figures of the main paper are referred to as such; S-numbers refer to this supplement.

# S1. Validation of the bandwidth control

The control was validated on 40 unseen train-clean-100 speakers with the filter taps unchanged
(main paper, Section 3.4 and Fig. 1). All criteria passed:

| Measure | Control | Reference / other |
|---|---|---|
| Log-spectral distance, 0–3 kHz (median) | 0.031 dB | — |
| Coherent bandwidth | 4,093.8 Hz | 4,125.0 Hz (SILK-NB reference) |
| Coherent 4–8 kHz power | −24.7 dB | −24.9 dB (linear reference) |
| $\lvert H_1\rvert$ difference from the reference, 3.0–4.2 kHz (RMS) | 0.57 dB | — |
| Minimum coherence, 0–3.8 kHz | 0.9992 | 0.168 (Opus at 8 kbit/s) |

: Validation of the low-pass control (LP) on 40 unseen train-clean-100 speakers, with the SILK narrowband linear reference and Opus at 8 kbit/s for comparison (no ASR).

# S2. Pilot

On the pilot (138 utterances, 69 speakers), the residual was OPUS − LP = +0.35 pp [+0.07, +0.64]
for Whisper large-v3 and +1.49 pp [+0.74, +2.25] for wav2vec2-base-960h (Table S2). Both
intervals excluded zero, so the pre-declared kill test returned PROCEED. The bandwidth
component was +0.21 pp [−0.23, +0.67] (Whisper) and +2.04 pp [+1.12, +3.17] (wav2vec2).

| | REF | LP | OPUS | SILK | NEG_LP | NEG_CODEC |
|---|---|---|---|---|---|---|
| Whisper large-v3 | 2.11 | 2.32 | 2.67 | 2.39 | 2.08 | 2.18 |
| wav2vec2-base-960h | 5.16 | 7.20 | 8.69 | 6.79 | 5.16 | 5.23 |

: Pilot (dev-clean + dev-other; 138 utterances, 69 speakers, 2,887 reference words): corpus WER (%) (upper part) and paired contrasts with 95 % speaker-bootstrap intervals (lower part).

| Contrast (micro, pp) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| LP − REF | +0.21 [−0.23, +0.67] | +2.04 [+1.12, +3.17] |
| OPUS − LP | +0.35 [+0.07, +0.64] | +1.49 [+0.74, +2.25] |
| SILK − LP | +0.07 [−0.21, +0.30] | −0.42 [−0.84, +0.03] |
| OPUS − SILK | +0.28 [−0.07, +0.64] | +1.91 [+1.09, +2.71] |
| NEG_LP − REF | −0.03 [−0.32, +0.25] | +0.00 [−0.26, +0.24] |
| NEG_CODEC − REF | +0.07 [−0.07, +0.25] | +0.07 [−0.19, +0.35] |

# S3. Confirmation: additional results

Fig. S1 and Tables S3–S6 support main-paper Sections 4.2 and 4.4–4.8; Figs. S2 and S3 compare
the contrasts between pilot and confirmation and between the two recognisers.

![Corpus WER by condition on the confirmation set, with 95 % speaker-bootstrap intervals. Negative controls are shown in grey.](figures/fig_wer.pdf){#fig:wer}

| Subset | Model | REF | LP | OPUS | SILK | LP − REF | OPUS − LP | SILK − LP |
|---|---|---|---|---|---|---|---|---|
| test-clean | Whisper large-v3 | 1.62 | 1.59 | 1.88 | 1.59 | −0.03 [−0.13, +0.07] | +0.29 [+0.15, +0.46] | −0.004 [−0.06, +0.05] |
| test-clean | wav2vec2-base-960h | 3.30 | 3.71 | 4.65 | 3.74 | +0.41 [+0.20, +0.64] | +0.94 [+0.72, +1.18] | +0.02 [−0.06, +0.10] |
| test-other | Whisper large-v3 | 3.68 | 4.05 | 5.27 | 4.10 | +0.37 [+0.16, +0.59] | +1.22 [+0.75, +1.77] | +0.05 [−0.08, +0.18] |
| test-other | wav2vec2-base-960h | 8.13 | 10.88 | 14.48 | 10.64 | +2.75 [+1.83, +3.92] | +3.60 [+2.78, +4.68] | −0.24 [−0.50, −0.005] |

: Per-subset WER (%) and contrasts (pp, micro, 95 % speaker-bootstrap intervals). Secondary scope; no multiplicity correction.

| Model | Contrast | Substitutions | Deletions | Insertions |
|---|---|---|---|---|
| Whisper large-v3 | LP − REF | +0.09 [+0.009, +0.18] | +0.03 [−0.009, +0.06] | +0.02 [−0.009, +0.05] |
| Whisper large-v3 | OPUS − LP | +0.51 [+0.34, +0.70] | +0.10 [+0.05, +0.16] | +0.08 [+0.03, +0.13] |
| Whisper large-v3 | SILK − LP | +0.03 [−0.02, +0.09] | −0.009 [−0.03, +0.007] | −0.002 [−0.02, +0.02] |
| wav2vec2-base-960h | LP − REF | +1.16 [+0.83, +1.58] | +0.23 [+0.14, +0.33] | +0.02 [−0.03, +0.07] |
| wav2vec2-base-960h | OPUS − LP | +1.79 [+1.46, +2.21] | +0.13 [+0.05, +0.22] | +0.15 [+0.09, +0.20] |
| wav2vec2-base-960h | SILK − LP | −0.08 [−0.18, +0.02] | −0.03 [−0.06, +0.009] | +0.02 [−0.01, +0.04] |

: Error-type composition of the contrasts (change in errors per 100 reference words, with 95 % speaker-bootstrap intervals).

| Contrast | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| NEG_LP − REF | −0.08 [−0.15, −0.004] | +0.10 [+0.02, +0.19] |
| NEG_CODEC − REF | +0.002 [−0.046, +0.049] | +0.002 [−0.057, +0.065] |

: Negative controls (pp, micro, with 95 % speaker-bootstrap intervals; pre-declared margin ±0.5 pp).

| Descriptor (median vs REF) | LP | OPUS | SILK | NEG_LP | NEG_CODEC |
|---|---|---|---|---|---|
| LSD, full band (dB) | 9.71 | 10.42 | 9.15 | 3.48 | 1.57 |
| LSD, 0–3 kHz (dB) | 0.03 | 6.14 | 1.37 | 0.00 | 1.29 |
| LSD, 0–4 kHz (dB) | 1.42 | 6.46 | 2.16 | 0.00 | 1.30 |
| LSD, 4–8 kHz (dB) | 13.60 | 12.60 | 12.52 | 4.92 | 1.64 |
| Retained bandwidth, power-based (Hz) | 4,094 | 4,625 | 4,656 | 7,156 | 8,000 |
| 4–8 kHz power change (dB) | −25.4 | −17.2 | −16.3 | −0.5 | −0.4 |
| Coherence, 0–3.5 kHz | 1.000 | 0.623 | 0.993 | 1.000 | 0.995 |

: Signal descriptors on the confirmation set, relative to REF: per-utterance medians (upper part) and pooled cross-spectral measures (lower part).

| Pooled cross-spectral descriptor (vs REF) | LP | OPUS | SILK |
|---|---|---|---|
| Coherent bandwidth (Hz) | 4,094 | 4,000 | 4,094 |
| Coherent 4–8 kHz power (dB) | −24.6 | −34.0 | −25.0 |
| Total 4–8 kHz power (dB) | −24.5 | −16.7 | −15.8 |
| Mirror coherence, 4.1–4.9 kHz | 0.000 | 0.227 | 0.970 |
| In-band gain $\lvert H_1\rvert$, 0.5–2 kHz (dB) | 0.00 | −1.83 | −0.08 |

![Paired contrasts on the pilot and the confirmation set, with 95 % speaker-bootstrap intervals.](figures/fig_forest.pdf){#fig:forest}

![Cross-recogniser comparison of the paired contrasts on the confirmation set, with 95 % speaker-bootstrap intervals. The diagonal marks equal effects in both recognisers; negative controls are shown in grey.](figures/fig_models.pdf){#fig:models}

# S4. Addition A: level-matched sensitivity analysis

*Post-confirmation sensitivity analysis on the confirmation utterances, decoded a second time;
not a second confirmatory test.*

All gates passed before recognition. LP and OPUS reproduced the confirmation audio bit for bit
for all 2,174 utterances, the largest level-matching error was $1.6 \times 10^{-8}$ dB, and the
gains equalled those implied by the confirmation audio within $1.4 \times 10^{-14}$ dB. The
gains had a median of +0.562 dB (5th–95th percentile +0.290 to +1.032 dB; range −0.076 to
+2.381 dB).

| Addition A (pooled) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| Corpus WER, LP, same run (%) | 2.63 [2.31, 2.98] | 6.76 [5.89, 7.74] |
| Corpus WER, OPUS, same run (%) | 3.32 [2.86, 3.82] | 8.84 [7.72, 10.17] |
| Corpus WER, OPUS8_LEVEL_MATCHED (%) | 3.33 [2.87, 3.83] | 8.85 [7.74, 10.18] |
| OPUS8_LEVEL_MATCHED − LP (pp; primary) | +0.70 [+0.47, +0.95] | +2.09 [+1.71, +2.57] |
| OPUS8_LEVEL_MATCHED − OPUS (pp) | +0.012 [−0.007, +0.032] | +0.018 [−0.028, +0.062] |
| OPUS − LP, same run (pp) | +0.69 [+0.46, +0.94] | +2.07 [+1.68, +2.57] |
| OPUS − LP, confirmatory run (pp) | +0.69 [+0.46, +0.94] | +2.07 [+1.68, +2.57] |
| Share of the confirmatory residual retained | 1.02 | 1.01 |
| GO: lower bound of OPUS8_LEVEL_MATCHED − OPUS above | −0.172 | −0.518 |
| FALSIFY: its upper bound below | −0.343 | −1.035 |
| Hypotheses changed by level matching | 42 of 2,174 | 188 of 2,174 |
| Outcome (frozen rule) | GO | GO |

: Addition A, the level-matched sensitivity analysis (post-confirmation; confirmation utterances decoded a second time; pooled, 95 % speaker-bootstrap intervals). The share retained is the level-matched residual divided by the confirmatory OPUS − LP estimate (point estimates). Thresholds are those of the pre-declared rule (Section 3.9).

| Subset | Model | OPUS8_LEVEL_MATCHED − LP | OPUS8_LEVEL_MATCHED − OPUS |
|---|---|---|---|
| test-clean | Whisper large-v3 | +0.32 [+0.17, +0.50] | +0.028 [+0.000, +0.059] |
| test-clean | wav2vec2-base-960h | +0.96 [+0.75, +1.20] | +0.028 [−0.013, +0.069] |
| test-other | Whisper large-v3 | +1.21 [+0.74, +1.76] | −0.011 [−0.037, +0.016] |
| test-other | wav2vec2-base-960h | +3.61 [+2.81, +4.64] | +0.005 [−0.084, +0.090] |

: Addition A per subset (secondary scope; no multiplicity correction; 95 % speaker-bootstrap intervals): level-matched residual and effect of level matching (pp).

Per 100 reference words, the level-matched residual comprised +0.52 substitutions [+0.35, +0.71]
for Whisper and +1.79 substitutions [+1.48, +2.19] for wav2vec2. The changed hypotheses and the corrected
expectation for wav2vec2-base-960h are reported in the main paper (Section 4.9) and in Section S6.

Level matching raised the number of samples at or above full scale from 113 in 17 utterances
(OPUS) to 349 in 33 utterances, out of about $2.6 \times 10^{8}$; as in the confirmatory
analysis, the recognisers received them unchanged. Decoded a second time, the LP and OPUS
hypotheses of wav2vec2-base-960h were identical to those of the confirmatory run, so its
same-run OPUS − LP equals the confirmatory estimate. For Whisper, 3 of 4,348 hypotheses
differed (two LP, one OPUS; all three involve proper names), which changed the same-run
OPUS − LP by 0.002 pp. As pre-declared, this reproduction check was reported, not a gate, and
the analysis uses the same-run LP and OPUS.

# S5. Addition B: bitrate sweep

*Fresh-utterance, not fresh-speaker, holdout: 1,665 unused test utterances of 70 of the
confirmation speakers.*

Validation passed before recognition. Each rate produced 571,809 packets, all SILK-only
narrowband with 20 ms frames, and every encoder setting read back as requested. Median payload
bitrates were 7.36, 11.35, 15.43, 23.46 and 38.96 kbit/s, 2.3–8.0 % below nominal (main paper, Table V);
over the Ogg files, including container overhead, they were 8.19–39.77 kbit/s. At 8 kbit/s the
sweep's `signal=voice` encoding produced Ogg files byte-identical to those of the OPUS settings
(`signal=auto`) for all 1,665 utterances, so SILK8 − LP repeats the confirmatory OPUS − LP
contrast on new utterances. Corpus WERs by condition are in Table S11. The slopes on the rate rank and on the measured payload bitrate agree with the primary slope
(Table S9). The decline was concentrated at low rates. The step from 8 to 12 kbit/s was the
largest (+0.34 and +1.32 pp), and the later steps were smaller. The point estimates fell at every
step in both recognisers, and 66 % (Whisper) and 98 % (wav2vec2) of bootstrap replicates were
monotone.

| Addition B (pooled) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| Slope on log2 bitrate (pp per doubling; primary) | −0.206 [−0.267, −0.146] | −0.854 [−1.074, −0.657] |
| Slope implied by the confirmation, S* | −0.288 | −0.929 |
| GO: lower bound of the slope at or below 0.5 S* | −0.144 | −0.465 |
| Slope on rate rank (pp per step) | −0.120 [−0.155, −0.085] | −0.497 [−0.624, −0.382] |
| Slope on log2 measured payload (pp per doubling) | −0.201 [−0.260, −0.142] | −0.831 [−1.045, −0.640] |
| SILK8 − SILK12 | +0.34 [+0.19, +0.51] | +1.32 [+0.99, +1.67] |
| SILK12 − SILK16 | +0.08 [−0.03, +0.19] | +0.39 [+0.21, +0.58] |
| SILK16 − SILK24 | +0.08 [+0.01, +0.15] | +0.32 [+0.14, +0.50] |
| SILK24 − SILK40 | +0.02 [−0.04, +0.07] | +0.10 [+0.007, +0.20] |
| SILK8 − SILK40 | +0.52 [+0.36, +0.68] | +2.13 [+1.65, +2.67] |
| Adjacent declines, point estimates | 4 of 4 | 4 of 4 |
| Replicates with a monotone decline | 0.66 | 0.98 |
| Outcome (frozen rule) | GO | GO |

: Addition B: trend over bitrate, adjacent-rate and endpoint contrasts (pp; secondary), and the pre-declared rule. S* is the slope implied by the confirmatory residuals at 8 and 40 kbit/s.

| Descriptor (addition B) | LP | SILK8 | SILK12 | SILK16 | SILK24 | SILK40 |
|---|---|---|---|---|---|---|
| LSD, 0–3 kHz, vs LP (dB) | — | 6.19 | 4.96 | 3.98 | 2.66 | 1.37 |
| Coherence, 0–3.5 kHz, vs LP | — | 0.623 | 0.810 | 0.896 | 0.963 | 0.993 |
| RMS level change vs REF (dB) | −0.09 | −0.68 | −0.40 | −0.29 | −0.19 | −0.12 |
| In-band gain $\lvert H_1\rvert$ vs REF, 0.5–2 kHz (dB) | 0.00 | −1.83 | −0.87 | −0.51 | −0.23 | −0.08 |
| Mirror coherence vs REF, 4.1–4.9 kHz | 0.000 | 0.245 | 0.548 | 0.730 | 0.892 | 0.970 |
| Total 4–8 kHz power vs REF (dB) | −24.4 | −16.5 | −17.6 | −17.5 | −16.7 | −15.6 |

: Addition B: signal descriptors by rate (per-utterance medians relative to LP or REF, upper part; pooled cross-spectral measures relative to REF, lower part). Descriptive only; no descriptor enters the rule.

| Condition (addition B, WER %) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| LP | 2.84 [2.49, 3.23] | 7.60 [6.66, 8.71] |
| SILK8 | 3.40 [2.97, 3.87] | 9.68 [8.44, 11.09] |
| SILK12 | 3.05 [2.68, 3.45] | 8.36 [7.36, 9.52] |
| SILK16 | 2.97 [2.60, 3.37] | 7.97 [6.99, 9.10] |
| SILK24 | 2.89 [2.52, 3.30] | 7.65 [6.74, 8.73] |
| SILK40 | 2.88 [2.50, 3.28] | 7.55 [6.64, 8.61] |

: Addition B: corpus WER (%) by condition on the 1,665 sweep utterances, with 95 % speaker-bootstrap intervals.

| Subset | Model | SILK8 − LP | Slope (pp per doubling) |
|---|---|---|---|
| test-clean | Whisper large-v3 | +0.11 [−0.04, +0.27] | −0.055 [−0.111, −0.001] |
| test-clean | wav2vec2-base-960h | +0.62 [+0.32, +0.97] | −0.243 [−0.388, −0.121] |
| test-other | Whisper large-v3 | +0.95 [+0.65, +1.28] | −0.344 [−0.450, −0.243] |
| test-other | wav2vec2-base-960h | +3.39 [+2.67, +4.27] | −1.410 [−1.816, −1.060] |

: Addition B per subset (secondary scope; no multiplicity correction; 95 % speaker-bootstrap intervals): residual at 8 kbit/s (pp) and slope on log2 bitrate (pp per doubling).

# S6. Amendments and deviations

Before any evaluation decoding, greedy decoding replaced beam search for Whisper, for compute
reasons on a shared GPU. After the pilot and before the confirmation, one figure changed from
text labels to marker shapes (presentation only; recorded in the confirmation freeze). After
the confirmation, a resumable decoding checkpoint, which no seal covers, was removed from
version control, and interpretation wording was corrected in a dated note; no frozen output,
statistic, specification, selection or figure was changed. During the controls stage, the
first validation of the low-pass control failed on an internally inconsistent criterion; the
corrected criterion was frozen before the confirmation data were downloaded, and the failed
result is retained (main paper, Section 3.4).

**Follow-up analyses.** Before their code was frozen, a calibration check on the 20 calibration
utterances found that level matching changed 1 of 20 wav2vec2-base-960h hypotheses. The sealed
plan had expected wav2vec2 to remove a scalar gain in its first-layer normalisation, so that its
result in Addition A would be uninformative and a GO expected by construction. A dated
amendment, sealed before the freeze and before any evaluation audio was decoded, corrected that
expectation. The normalisation's nonzero epsilon lets gain information persist in low-variance
channels, so invariance is approximate, not exact, and the wav2vec2 result is interpreted
normally. The check was reclassified from a freeze gate to a descriptive calibration finding,
and the failed calibration record is retained. The amendment changed no estimand, gate,
decision threshold, condition, selection or rule, and no code changed after the freeze. The
three Whisper hypotheses that differed when Addition A decoded the confirmation audio again are
reported in Section S4 (main paper, Section 4.9).

# S7. Forced-wideband counterfactual and stopped sensitivity analyses

A later plan, sealed after Additions A and B and before any of its audio was encoded, fixed the
selections, pre-recognition checks, estimands, bootstrap and outcome rules of three analyses; its
code was frozen after a calibration step.

**Forced-wideband counterfactual (main paper, Sections 3.10 and 4.11).** All pre-recognition
checks passed (bitrates and descriptors: Table S14). NB8's Ogg files and raw hypotheses were identical to those of Addition B's SILK8
for all 1,665 utterances in both recognisers. Per-subset contrasts are secondary and uncorrected
for multiplicity (Table S13); the interval for Whisper large-v3 on test-clean lay above zero
(+0.27 pp [+0.03, +0.54]), and that for wav2vec2-base-960h on test-other below zero
(−1.70 pp [−2.75, −0.65]).

| Scope | Recogniser | WER NB8 (%) | WER WB8 (%) | WB8 − NB8 (pp) | Outcome (frozen rule) |
|---|---|---|---|---|---|
| pooled | Whisper large-v3 | 3.40 [2.97, 3.87] | 3.54 [3.06, 4.06] | +0.14 [−0.07, +0.36] | NO_CLEAR_DIFFERENCE |
| pooled | wav2vec2-base-960h | 9.68 [8.44, 11.09] | 8.70 [7.62, 9.94] | −0.98 [−1.57, −0.42] | WB_BETTER |
| test-clean | Whisper large-v3 | 2.20 [1.77, 2.67] | 2.47 [2.02, 2.94] | +0.27 [+0.03, +0.54] | — (secondary) |
| test-clean | wav2vec2-base-960h | 4.49 [3.77, 5.29] | 4.31 [3.60, 5.06] | −0.19 [−0.43, +0.06] | — (secondary) |
| test-other | Whisper large-v3 | 4.48 [3.77, 5.27] | 4.51 [3.69, 5.42] | +0.03 [−0.30, +0.36] | — (secondary) |
| test-other | wav2vec2-base-960h | 14.39 [12.15, 16.88] | 12.69 [10.71, 15.02] | −1.70 [−2.75, −0.65] | — (secondary) |

: Forced-wideband counterfactual at 8 kbit/s (1,665 utterances of Addition B; fresh-utterance, not fresh-speaker, holdout): corpus WER (%) and WB8 − NB8 (pp), 95 % speaker-bootstrap intervals; frozen-rule outcome for pooled rows only. A practical bandwidth-allocation counterfactual, not a factorial interaction estimate.

| Descriptor | NB8 | WB8 |
|---|---|---|
| Median payload bitrate (kbit/s) | 7.36 | 7.76 |
| Coherence with REF, 0–3.5 kHz (median) | 0.623 | 0.559 |
| LSD vs REF, 0–3 kHz (dB, median) | 6.19 | 6.77 |
| 4–8 kHz power change vs REF (dB, median) | −17.19 | 1.72 |
| Coherent bandwidth vs REF (Hz, pooled) | 4000 | 8000 |
| Total 4–8 kHz power vs REF (dB, pooled) | −16.54 | 2.14 |
| Raw hypotheses differing from NB8 (Whisper; wav2vec2) | — | 782; 999 |

: Forced-wideband counterfactual: NB8 and WB8 payload bitrate and signal descriptors against REF (medians over utterances, or pooled cross-spectral measures) and raw hypotheses (of 1,665) differing from NB8. Descriptive only.

**Stopped attribution sensitivities.** Two additional attribution sensitivities were prospectively
gated but stopped before ASR because their signal-domain controls failed held-out validation.
The held-out subset was new and signal-only (no transcripts; 40 train-clean-100 speakers, 20 female
and 20 male, one utterance each, disjoint from the calibration and filter-validation speakers). Neither control
was redesigned or refitted; the main paper's primary control, decomposition and decoder
limitation are unchanged.

- *Decoding with the libopus reference decoder.* The frozen control failed a pre-specified
  control-reuse gate against the libopus-decoded SILK narrowband response, so a decoder-matched
  control was fitted by the unchanged procedure (main paper, Section 3.4). The decoder-matched
  control failed held-out transition-shape validation: RMS difference 2.07 dB over 3.0–4.2 kHz
  (limit 1.5 dB).
- *The 8-kbit/s effective coherent-linear surrogate* (fitted to the same-frequency coherent
  response of Opus at 8 kbit/s, for an alternative attribution under a more inclusive
  same-frequency linear-loss definition; not a bandwidth control) failed held-out
  transition-shape validation: RMS difference from its target 2.04 dB (limit 1.5 dB), maximum
  8.91 dB (limit 4.0 dB).

*Post hoc and exploratory, not part of any rule:* the libopus-decoded chain has a sub-sample,
content-dependent delay (median 0.44 and 0.47 samples at 16 kHz, calibration and validation sets);
under the frozen integer alignment its linear response depended on the speaker set (largest
calibration–validation difference over 3.0–4.15 kHz: 3.61 dB, against 0.92 dB with one fixed
alignment and 0.94 dB for the FFmpeg-decoded chain). This fractional-delay diagnosis is post hoc
and exploratory; no successor analysis has been run.

**Deviations** (none changed a gate, tolerance, rule, selection or outcome): the code freeze was
sealed before the held-out signal validation, keeping the plan's order; the validation report was
sealed in three parts plus a combined report, so the decoder analysis's pre-recognition checks were
completed after it had stopped; three pre-specified descriptive items of the counterfactual
(differing-hypothesis counts, reproduction check, in-band descriptors of Table S14) were computed
afterwards from sealed outputs by a separate script, and the in-band descriptors were sealed with
the recognition outputs rather than before recognition; a pre-freeze dry run on 3 calibration
utterances was discarded.

# S8. Reference-decoder sensitivity of the total penalty

A further plan, sealed after the analyses of Section S7 and before its own decoding and
recognition, tested whether the libopus 1.4 reference decoder, instead of FFmpeg 6.1.1, changes
the total penalty OPUS − REF on the same frozen confirmation bitstreams (main paper, Section 4.8).
It tests the total penalty only: no bandwidth component, share or residual was computed under
libopus, it is not a successor to the stopped decoder analysis of Section S7, and a result without
a clear difference is not an equivalence claim. The decoder applied RFC 7845 pre-skip and end
trimming at 48 kHz, followed by the Stage 3 resampler, with no gain, alignment or filtering; only
OPUS_LIBOPUS was recognised, once. The frozen rule classifies D = OPUS_LIBOPUS − OPUS_FFMPEG by
whether its 95 % interval lies below zero (DECODER_LOWER_PENALTY), above zero
(DECODER_HIGHER_PENALTY) or includes it (NO_CLEAR_DECODER_DIFFERENCE), with no minimum effect and
Stage 3's bootstrap and seed. All pre-recognition checks passed: bitstreams byte-identical to
Stage 3's (2,174 of 2,174), no decoding error, the pre-specified output lengths, no non-finite
sample, an unchanged environment, and exact reproduction of the sealed Stage 3 calibration outputs
and of Stage 3's OPUS − REF. The same bitstreams had been decoded with the same libopus path
before, signal only, when the stopped analysis of Section S7 was checked; the new decode reproduced
it exactly, and no libopus-decoded evaluation audio had been recognised before.

| Pooled (confirmation set) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| WER, REF (%) | 2.50 [2.19, 2.84] | 5.36 [4.73, 6.08] |
| WER, OPUS_FFMPEG (%) | 3.32 [2.86, 3.82] | 8.84 [7.72, 10.17] |
| WER, OPUS_LIBOPUS (%) | 3.22 [2.78, 3.70] | 8.92 [7.78, 10.26] |
| T_ffmpeg = OPUS_FFMPEG − REF (pp) | +0.83 [+0.57, +1.10] | +3.48 [+2.73, +4.45] |
| T_libopus = OPUS_LIBOPUS − REF (pp) | +0.72 [+0.49, +0.97] | +3.56 [+2.79, +4.54] |
| D = OPUS_LIBOPUS − OPUS_FFMPEG (pp) | −0.11 [−0.17, −0.04] | +0.09 [−0.04, +0.21] |
| Outcome (frozen rule) | DECODER_LOWER_PENALTY | NO_CLEAR_DECODER_DIFFERENCE |

: Reference-decoder sensitivity of the total 8 kbit/s penalty on the confirmation set (2,174 utterances, 73 speakers; pooled; 95 % speaker-bootstrap intervals with Stage 3's seed): corpus WER (%), the totals and their difference (pp), and the frozen outcome. Total penalty only: no bandwidth share or residual under libopus.

| Subset | Recogniser | WER, OPUS_LIBOPUS (%) | T_ffmpeg (pp) | T_libopus (pp) | D (pp) |
|---|---|---|---|---|---|
| test-clean | Whisper large-v3 | 1.87 [1.54, 2.22] | +0.26 [+0.12, +0.43] | +0.25 [+0.12, +0.40] | −0.01 [−0.07, +0.05] |
| test-clean | wav2vec2-base-960h | 4.62 [4.06, 5.21] | +1.34 [+0.97, +1.77] | +1.32 [+0.95, +1.71] | −0.02 [−0.14, +0.09] |
| test-other | Whisper large-v3 | 5.03 [4.12, 6.11] | +1.58 [+1.04, +2.20] | +1.35 [+0.85, +1.91] | −0.23 [−0.37, −0.10] |
| test-other | wav2vec2-base-960h | 14.71 [12.10, 17.85] | +6.35 [+4.76, +8.54] | +6.58 [+4.90, +8.82] | +0.23 [+0.00, +0.47] |

: Reference-decoder sensitivity per subset (secondary scope; no multiplicity correction; 95 % speaker-bootstrap intervals). The wav2vec2 test-other interval of D has a lower bound of exactly 0.00 and does not exclude zero.

| Descriptor (against REF; descriptive) | OPUS_FFMPEG | OPUS_LIBOPUS |
|---|---|---|
| Integer lag (samples: utterances) | 1: 12; 2: 2,162 | 0: 1,084; 1: 1,082; 2: 8 |
| RMS change, median [5th, 95th percentile] (dB) | −0.68 [−2.09, −0.34] | −0.67 [−1.98, −0.33] |
| 4–5 kHz power (dB, pooled) | −13.33 | −13.85 |
| Total 4–8 kHz power (dB, pooled) | −16.74 | −17.26 |
| Mirror coherence, 4.1–4.9 kHz (pooled) | 0.227 | 0.098 |
| Samples at or above full scale (utterances) | 113 (17) | 51 (14) |

: Reference-decoder sensitivity: descriptive decoder and signal diagnostics against REF (lag counts, per-utterance medians, pooled cross-spectral measures, and samples at or above full scale, which were passed on unchanged). No descriptor enters the rule.

The FFmpeg- and libopus-decoded signals of the same bitstream were never bit-identical; their SNR
had a median of 10.13 dB unaligned and 17.96 dB after the better one-sample shift (minimum
0.06 dB; the better shift was −1 in 2,173 utterances and +1 in one). *Transcript differences (a
post-analysis descriptive addition, not pre-specified).* Relative to OPUS_FFMPEG, 292 raw (103
normalised) Whisper transcripts and 801 raw (797 normalised) wav2vec2 transcripts of the 2,174
changed under OPUS_LIBOPUS. OPUS_LIBOPUS was recognised in a separate run whose Whisper batches
differed from Stage 3's, and greedy float16 Whisper decoding is not exactly invariant to batch
composition (Section S4: 3 of 4,348 hypotheses), so not every Whisper transcript difference can be
interpreted as a decoder effect; wav2vec2 decodes each utterance alone.

**Deviations** (none changed a gate, rule, selection or outcome): the transcript-difference counts
were computed after the analysis by a script outside the code freeze; the main paper reports this
analysis in a Results paragraph and a Discussion sentence and rewrites the Implementations
limitation, whose statement that one decoder was used no longer held, whereas the plan foresaw one
main-paper sentence and at most one added limitation sentence; and the Whisper batch-composition
component of the cross-run comparison is part of D and was not separated.
