---
title: "Supplementary material for: How much of the ASR penalty of 8 kbit/s Opus is bandwidth loss? A decomposition with a validated bandwidth control"
author: "[Authors withheld for review]"
date: "TASLP submission version, 2026-09-27"
---

<!--
SUPPLEMENTARY MATERIAL of the TASLP submission version (taslp_submission.md): material moved out of draft 2, and the
details of the later sealed analyses (Sections S7-S11); checked with `python manuscript/tools/check_numbers.py --submission`.
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

Tables S3–S6 support main-paper Sections 4.2 and 4.4–4.8.

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

# S4. Addition A: level-matched sensitivity analysis

*Post-confirmation sensitivity analysis on the confirmation utterances, decoded a second time;
not a second confirmatory test.*

All gates passed before recognition. LP and OPUS reproduced the confirmation audio bit for bit
for all 2,174 utterances, the largest level-matching error was $1.6 \times 10^{-8}$ dB, and the
gains equalled those implied by the confirmation audio within $1.4 \times 10^{-14}$ dB. The
gains had a median of +0.562 dB (5th–95th percentile +0.290 to +1.032 dB; range −0.076 to
+2.381 dB).

Before recognition, LP and OPUS had to reproduce the confirmation audio bit for bit, the
level-matched RMS had to equal that of LP within 0.001 dB, and the gains had to equal those
implied by the confirmation audio within $10^{-6}$ dB. Each follow-up rule has three outcomes,
GO, WEAKEN or FALSIFY, applied per recogniser; the combined outcome is GO or FALSIFY only if both
recognisers agree, and WEAKEN otherwise, and a missing interval bound never satisfies GO or
FALSIFY. With $T^\ast$ the confirmatory OPUS − LP estimate of each recogniser, Addition A returns
GO if the lower bound of $L$ = OPUS8_LEVEL_MATCHED − LP is above zero and the lower bound of
$K$ = OPUS8_LEVEL_MATCHED − OPUS is above $-0.25\,T^\ast$, and FALSIFY if the upper bound of $K$
is below $-0.5\,T^\ast$.

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

The sweep used test utterances that the project had never encoded, decoded or recognised,
selected from metadata only with the confirmation rule: up to 30 per speaker from every test
speaker with an eligible unused utterance. This gave 1,665 utterances from 70 speakers
(38 test-clean, 32 test-other; 777 and 888 utterances; 3.17 h; 31,601 reference words).

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
monotone. Before recognition, encoding and decoding alone had to show that every packet at every
rate was SILK-only narrowband with 20 ms frames, that every encoder setting read back as
requested, and that the median payload bitrate was within ±15 % of nominal, with each rate's
median at least 1.2 times the previous one. The rule compares the slope $S$ with
$S^\ast = (U^\ast - T^\ast)/\log_2 5$, the slope implied by the confirmatory residuals at
8 kbit/s ($T^\ast$, OPUS − LP) and 40 kbit/s ($U^\ast$, SILK − LP): GO if the lower bound of
$R_8$ is above zero, the upper bound of $S$ is below zero and its lower bound is at or below
$0.5\,S^\ast$; FALSIFY if the upper bound of $S$ is at or above zero and its lower bound is above
$0.5\,S^\ast$.

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
result in Addition A would be uninformative. A dated amendment, sealed before the freeze and
before any evaluation audio was decoded, corrected that expectation (the normalisation's nonzero
epsilon lets gain information persist in low-variance channels), reclassified the check as a
descriptive calibration finding and retained the failed calibration record; it changed no
estimand, gate, decision threshold, condition, selection or rule, and no code changed after the
freeze.

# S7. Forced-wideband counterfactual and stopped sensitivity analyses

A later plan, sealed after Additions A and B and before any of its audio was encoded, fixed the
selections, pre-recognition checks, estimands, bootstrap and outcome rules of three analyses; its
code was frozen after a calibration step. For the forced-wideband counterfactual, NB8 had to
reproduce Addition B's SILK8 files byte for byte, every WB8 packet had to be SILK-only wideband
with 20 ms frames, every encoder setting had to read back as requested, WB8's median payload
bitrate had to lie within ±15 % of nominal and within ±10 % of NB8's, and WB8's pooled 4–8 kHz
power relative to REF had to be at least −10 dB; the outcome is WB_BETTER if the interval of
WB8 − NB8 lies below zero, WB_WORSE if it lies above zero and NO_CLEAR_DIFFERENCE otherwise.

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

**Deviations** (none changed a gate, tolerance, rule, selection or outcome; full list in the
sealed record): the plan's order of code freeze and held-out signal validation, a validation
report sealed in parts, three descriptive items computed afterwards from sealed outputs, and a
discarded pre-freeze dry run.

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

**Deviations** (none changed a gate, rule, selection or outcome; full list in the sealed
record): the transcript-difference counts were computed after the analysis, outside the code
freeze; the main paper reports the analysis in more text than the one sentence the plan foresaw;
and the cross-run Whisper batch component is part of D.

# S9. Inclusive best-linear attribution

A plan sealed after the analysis of Section S8 specified the attribution of main-paper
Section 3.11. It was committed, with its method note, signal-only calibration, code freeze and
held-out validation, before any confirmation-set projection was computed. For each confirmation
utterance, LIN8 is the orthogonal projection of the confirmation's exact Opus waveform onto the
span of REF delayed by −256 to +255 samples (512 basis vectors), computed as in the BSS Eval
reference code with a centred delay span; no parameter was fitted or tuned. Calibration and
held-out validation each used one utterance from 40 new train-clean-100 speakers (20 female and
20 male per set; no transcripts or ASR): the projection was numerically exact, a second pass
reproduced every waveform, and the held-out projection error showed no collapse
(calibration median projection error −12.39 dB, tolerance 3.08 dB; validation median −11.61 dB). Before recognition, the regenerated Opus files and waveforms equalled those of
the confirmation for all 2,174 utterances, and the analysis code reproduced the confirmation's
contrasts. LIN8 was recognised in its own run, so Whisper's batches differed from the
confirmation's (Section S4); wav2vec2 decodes each utterance alone. The frozen outcome was
ROBUST_RESIDUAL: the residual beyond LIN8 lay above zero and exceeded the linear component in
both recognisers (Table S18) and in both subsets (Table S19). The confirmation projections used
single-threaded linear algebra because of CPU contention on the shared machine; this changes
rare samples in the last bit only, and the recognised audio is the audio that passed the checks.

| Pooled (confirmation set) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| WER, LIN8 (%) | 2.58 [2.28, 2.92] | 6.52 [5.69, 7.41] |
| LIN8 − REF (inclusive linear component, pp) | +0.09 [−0.02, +0.19] | +1.16 [+0.81, +1.55] |
| OPUS − LIN8 (residual beyond the best-linear surrogate, pp) | +0.74 [+0.51, +1.00] | +2.32 [+1.85, +2.97] |
| LIN8 − LP (pp) | −0.06 [−0.13, +0.01] | −0.25 [−0.47, −0.04] |
| Linear share, (LIN8 − REF)/(OPUS − REF) | 0.10 [−0.02, 0.22] | 0.33 [0.28, 0.39] |
| Sequential share along REF → LP → OPUS | 0.17 [0.05, 0.29] | 0.40 [0.35, 0.45] |
| Outcome (frozen rule) | ROBUST_RESIDUAL | ROBUST_RESIDUAL |

: Inclusive best-linear attribution on the confirmation set (2,174 utterances, 73 speakers; pooled; 95 % speaker-bootstrap intervals with the confirmation's seed): corpus WER of LIN8 (%), the linear component, the residual beyond it and its difference from the control (pp), the descriptive linear share beside the sequential share, and the frozen outcome. The linear share is not a bandwidth share.

| Subset | Recogniser | LIN8 − REF | OPUS − LIN8 | LIN8 − LP |
|---|---|---|---|---|
| test-clean | Whisper large-v3 | −0.02 [−0.10, +0.06] | +0.28 [+0.14, +0.46] | +0.008 [−0.05, +0.06] |
| test-clean | wav2vec2-base-960h | +0.27 [+0.07, +0.48] | +1.08 [+0.82, +1.37] | −0.14 [−0.27, −0.01] |
| test-other | Whisper large-v3 | +0.23 [+0.02, +0.45] | +1.36 [+0.87, +1.93] | −0.14 [−0.29, +0.00] |
| test-other | wav2vec2-base-960h | +2.35 [+1.62, +3.24] | +3.99 [+2.99, +5.44] | −0.39 [−0.90, +0.06] |

: Inclusive best-linear attribution per subset (secondary scope; no multiplicity correction; pp, 95 % speaker-bootstrap intervals).

| Descriptor | LIN8, calibration | LIN8, validation | LIN8, confirmation | LP control |
|---|---|---|---|---|
| Projection NMSE (dB) | −12.39 | −11.61 | −12.08 | — |
| Energy explained | 0.942 | 0.931 | 0.938 | — |
| Gain, 0.5–2 kHz (dB) | −2.05 | −2.10 | −2.22 | 0.00 |
| Response at 2.0 kHz, relative (dB) | −1.15 | −0.93 | −1.34 | 0.00 |
| Response at 2.5 kHz, relative (dB) | −2.54 | −2.74 | −2.59 | 0.00 |
| Response at 3.0 kHz, relative (dB) | −4.57 | −4.54 | −4.54 | −0.62 |
| Response at 3.5 kHz, relative (dB) | −6.94 | −6.79 | −7.30 | −2.16 |
| Response at 4.0 kHz, relative (dB) | −16.68 | −16.87 | −15.66 | −10.76 |
| Delay (samples) | 1.69 | 1.64 | 1.67 | 0 |
| Pooled coherence 0–3.5 kHz, OPUS / LIN8 | 0.650 / 0.945 | 0.658 / 0.939 | — | — |
| Pooled 4–8 kHz power vs REF, OPUS / LIN8 (dB) | −17.5 / −28.8 | −18.4 / −30.7 | — | — |

: Linear response of the 8 kbit/s chain: medians of the per-utterance best-linear filters on the calibration, validation and confirmation sets (projection error, gain over 0.5–2 kHz, response at fixed frequencies relative to that gain, and phase-slope delay), with the frozen LP control for comparison, and pooled cross-spectral measures against REF (no ASR). Descriptive only.

# S10. Encoder application mode

A plan sealed after the attribution of Section S9, and committed with its calibration and code
freeze before any confirmation bitstream was encoded, tested whether changing only the encoder
application (`OPUS_APPLICATION_AUDIO` → `OPUS_APPLICATION_VOIP`) changes the total 8 kbit/s penalty
(main paper, Sections 3.11 and 4.12). Every other setting, the Ogg writer, the FFmpeg decoder and
the resampler were unchanged, and the signal-type hint stayed `signal=auto`. In checks committed
before recognition, the regenerated OPUS_AUDIO8 bitstreams and waveforms equalled those of the
confirmation for all 2,174 utterances; every OPUS_VOIP8 utterance was encoded and decoded to the
REF length without non-finite samples; every encoder control read back as requested (application
2048); every packet was mono, narrowband and 20 ms (all SILK); and the analysis code reproduced
the confirmation's contrasts. OPUS_VOIP8 was recognised once, in its own run (Whisper batch
composition as in Section S4). The frozen rule classifies D_app = OPUS_VOIP8 − OPUS_AUDIO8 by
whether its 95 % interval lies below zero (VOIP_LOWER_PENALTY), above zero (VOIP_HIGHER_PENALTY)
or includes it (NO_CLEAR_APPLICATION_DIFFERENCE), with no minimum effect and no equivalence
margin; both recognisers returned NO_CLEAR_APPLICATION_DIFFERENCE (Table S21). For Whisper
large-v3 the upper bound is exactly zero, and the CER contrast and the test-other contrast
excluded zero (Tables S21 and S22; secondary, uncorrected). The VoIP mode changed every waveform
at an almost unchanged bitrate, with slightly lower in-band fidelity and a weaker image copy
(Table S23); these descriptors enter no rule, and no mechanism is inferred.

| Pooled (confirmation set) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| WER, OPUS_AUDIO8 (= OPUS) (%) | 3.32 [2.86, 3.82] | 8.84 [7.72, 10.17] |
| WER, OPUS_VOIP8 (%) | 3.20 [2.79, 3.64] | 8.80 [7.70, 10.07] |
| A = OPUS_AUDIO8 − REF (pp) | +0.83 [+0.57, +1.10] | +3.48 [+2.73, +4.45] |
| V = OPUS_VOIP8 − REF (pp) | +0.70 [+0.48, +0.95] | +3.44 [+2.71, +4.37] |
| D_app = OPUS_VOIP8 − OPUS_AUDIO8 (pp) | −0.12 [−0.25, +0.00] | −0.03 [−0.23, +0.15] |
| D_app, CER (pp) | −0.07 [−0.13, −0.007] | −0.05 [−0.13, +0.04] |
| Outcome (frozen rule) | NO_CLEAR_APPLICATION_DIFFERENCE | NO_CLEAR_APPLICATION_DIFFERENCE |

: Encoder application mode on the confirmation set (2,174 utterances, 73 speakers; pooled; 95 % speaker-bootstrap intervals with the confirmation's seed): corpus WER (%), the totals under the audio and VoIP application modes and their difference (pp), and the frozen outcome. Total penalty only: no bandwidth share or residual under the VoIP mode; not an equivalence test.

| Subset | Recogniser | V = OPUS_VOIP8 − REF | D_app = OPUS_VOIP8 − OPUS_AUDIO8 |
|---|---|---|---|
| test-clean | Whisper large-v3 | +0.26 [+0.13, +0.41] | −0.004 [−0.10, +0.09] |
| test-clean | wav2vec2-base-960h | +1.27 [+0.92, +1.65] | −0.07 [−0.28, +0.13] |
| test-other | Whisper large-v3 | +1.30 [+0.84, +1.84] | −0.28 [−0.56, −0.02] |
| test-other | wav2vec2-base-960h | +6.36 [+4.79, +8.48] | +0.02 [−0.33, +0.38] |

: Encoder application mode per subset (secondary scope; no multiplicity correction; pp, 95 % speaker-bootstrap intervals).

| Descriptor | OPUS_AUDIO8 | OPUS_VOIP8 |
|---|---|---|
| Payload bitrate, median [5th, 95th percentile] (kbit/s) | 7.34 [6.73, 7.71] | 7.29 [6.71, 7.68] |
| Coherence with REF, 0–3.5 kHz (median) | 0.623 | 0.614 |
| LSD vs REF, 0–3 kHz (dB, median) | 6.14 | 6.41 |
| RMS change vs REF (dB, median) | −0.68 | −0.72 |
| In-band gain, 0.5–2 kHz (dB, pooled) | −1.83 | −2.02 |
| Total 4–8 kHz power vs REF (dB, pooled) | −16.7 | −16.8 |
| Mirror coherence, 4.1–4.9 kHz (pooled) | 0.227 | 0.093 |
| Integer lag vs REF (samples: utterances) | 1: 12; 2: 2,162 | −4: 1; −3: 1; −2: 20; −1: 28; 0: 213; 1: 1,625; 2: 286 |
| Samples at or above full scale (utterances) | 113 (17) | 78 (19) |

: Encoder application mode: payload bitrate and signal descriptors against REF (per-utterance medians or pooled cross-spectral measures), integer lags and samples at or above full scale (passed on unchanged). Descriptive only; no descriptor enters the rule.

# S11. Metric and weighting robustness

Without new recognition, the primary contrasts of main-paper Section 4.12 were recomputed from
the confirmation outputs in every bootstrap replicate (the confirmation's seed on the same
speakers) under four weightings: corpus WER, mean per-utterance WER, equal-speaker WER (the mean
of per-speaker corpus WERs) and CER. The classification criteria were fixed in the audit code
before it was run. A sign or ordering statement is robust to the weighting if its interval lies
above zero under all four pooled weightings and, under corpus WER, in both subsets; a share is
unstable if any pooled replicate has a non-positive denominator, if its corpus-WER interval has an
upper-to-lower ratio above 2, or if its point estimates differ by more than a factor of 1.5 across
weightings. The residual and its excess over the bandwidth component were robust for both
recognisers, Whisper's bandwidth component was subset-dependent (not detectable on test-clean),
the Whisper share was unstable and the wav2vec2 share robust; no pooled replicate had a
non-positive denominator. Relative to the LP WER, the residual was 26.0 % (Whisper) and 30.6 %
(wav2vec2) under corpus WER but 30.3 % and 45.6 % under CER, and the ratio of the two recognisers'
bandwidth components ranged from 4.9 (CER) to 10.0 (corpus WER). In secondary cells, the ordering
was unresolved for Whisper on test-clean under CER and for wav2vec2 on test-other under mean
per-utterance WER, and for wav2vec2 the deletions rose more with band limitation than beyond it
(residual minus bandwidth component −0.09 [−0.22, +0.02] per 100 reference words).

| Weighting | Recogniser | LP − REF | OPUS − LP | (OPUS − LP) − (LP − REF) | Sequential share |
|---|---|---|---|---|---|
| Corpus WER | Whisper large-v3 | +0.14 [+0.04, +0.25] | +0.69 [+0.46, +0.94] | +0.55 [+0.30, +0.82] | 0.17 [0.05, 0.29] |
| Corpus WER | wav2vec2-base-960h | +1.40 [+0.99, +1.92] | +2.07 [+1.68, +2.57] | +0.67 [+0.37, +0.95] | 0.40 [0.35, 0.45] |
| Mean utterance WER | Whisper large-v3 | +0.35 [+0.17, +0.54] | +1.00 [+0.64, +1.39] | +0.65 [+0.25, +1.08] | 0.26 [0.14, 0.39] |
| Mean utterance WER | wav2vec2-base-960h | +1.90 [+1.39, +2.44] | +2.61 [+2.12, +3.13] | +0.71 [+0.21, +1.20] | 0.42 [0.36, 0.48] |
| Equal-speaker WER | Whisper large-v3 | +0.18 [+0.05, +0.31] | +0.77 [+0.53, +1.01] | +0.59 [+0.32, +0.88] | 0.19 [0.06, 0.31] |
| Equal-speaker WER | wav2vec2-base-960h | +1.52 [+1.13, +1.95] | +2.16 [+1.79, +2.57] | +0.63 [+0.32, +0.95] | 0.41 [0.36, 0.46] |
| CER | Whisper large-v3 | +0.12 [+0.07, +0.18] | +0.31 [+0.20, +0.44] | +0.19 [+0.08, +0.32] | 0.28 [0.17, 0.40] |
| CER | wav2vec2-base-960h | +0.59 [+0.42, +0.81] | +1.09 [+0.87, +1.40] | +0.50 [+0.36, +0.65] | 0.35 [0.30, 0.39] |

: Metric and weighting robustness of the primary contrasts on the confirmation set (pooled; pp; 95 % speaker-bootstrap intervals with the confirmation's seed): bandwidth component, residual, their difference and the sequential share under four weightings. No new recognition.
