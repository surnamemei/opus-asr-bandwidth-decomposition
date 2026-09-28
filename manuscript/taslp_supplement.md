---
title: "Supplementary material for: How much of the ASR penalty of 8 kbit/s Opus is bandwidth loss? A decomposition with a validated bandwidth control"
author: "[Authors withheld for review]"
date: "TASLP submission version, 2026-09-28"
---

<!--
SUPPLEMENTARY MATERIAL of the TASLP submission version (taslp_submission.md): the evidence behind the main paper's
tables and robustness analyses; full sealed records, manifests and logs are in the repository. Checked with
`python manuscript/tools/check_numbers.py --submission`.
-->

```{=latex}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\thesection}{S\arabic{section}}
\suppressfloats[t]
```

This supplement gives the evidence behind the main paper's tables and robustness analyses; the
project repository holds the full sealed records, manifests and logs. Sections, tables and figures
of the main paper are referred to as such; S-numbers refer to this supplement.

# S1. Validation of the bandwidth control

The control was validated on 40 unseen train-clean-100 speakers with the filter taps unchanged
(main paper, Section 3.4 and Fig. 1). All criteria passed; the first validation had failed an
internally inconsistent criterion, which was corrected before the confirmation data were
downloaded (Section S10).

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

Tables S3–S6 support main-paper Sections 4.2 and 4.3.

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

# S4. Level matching

The confirmation utterances were decoded a second time under LP, OPUS and OPUS8_LEVEL_MATCHED (main
paper, Section 3.9). Before recognition, LP and OPUS had to reproduce the confirmation audio bit for
bit, the level-matched RMS had to equal that of LP within 0.001 dB, and the gains had to equal those
implied by the confirmation audio within $10^{-6}$ dB; all checks passed. The per-utterance gains had
a median of +0.562 dB (5th–95th percentile +0.290 to +1.032 dB; range −0.076 to
+2.381 dB). With $T^\ast$ the confirmatory OPUS − LP estimate of each recogniser, the rule returns GO
if the lower bound of $L$ = OPUS8_LEVEL_MATCHED − LP is above zero and the lower bound of
$K$ = OPUS8_LEVEL_MATCHED − OPUS is above $-0.25\,T^\ast$, FALSIFY if the upper bound of $K$ is below
$-0.5\,T^\ast$, and WEAKEN otherwise; a combined GO or FALSIFY needs both recognisers, and a missing
interval bound never satisfies either. Both recognisers returned GO (Table S7). The level-matched
residual was 1.02 and 1.01 times the confirmatory residual, and per 100 reference words it comprised
+0.52 substitutions [+0.35, +0.71] for Whisper and +1.79 substitutions [+1.48, +2.19] for wav2vec2.
Level matching changed 42 of the 2,174 Whisper hypotheses and 188 of the 2,174 wav2vec2 hypotheses,
without reducing either error count; the plan's expectation that wav2vec2-base-960h would be
insensitive to a scalar gain was corrected before the code freeze (Section S10). Decoded a second
time, 3 of Whisper's 4,348 LP and OPUS hypotheses differed from the confirmatory run (wav2vec2's
were identical), so the analysis uses the same-run LP and OPUS.

| Level matching (pooled) | Whisper large-v3 | wav2vec2-base-960h |
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

: Level matching (post-confirmation; confirmation utterances decoded a second time; pooled, 95 % speaker-bootstrap intervals). The share retained is the level-matched residual divided by the confirmatory OPUS − LP estimate (point estimates). Thresholds are those of the pre-declared rule (Section S4).

# S5. Coding-rate sweep

The sweep is a fresh-utterance, not fresh-speaker, holdout. It used test utterances that the project
had never encoded, decoded or recognised, selected from metadata only with the confirmation rule: up
to 30 per speaker from every test speaker with an eligible unused utterance. This gave 1,665
utterances from 70 speakers (38 test-clean,
32 test-other; 777 and 888 utterances; 3.17 h; 31,601 reference words). Before recognition, encoding
and decoding alone had to show that every packet at every rate was SILK-only narrowband with 20 ms
frames, that every encoder setting read back as requested, and that the median payload bitrate was
within ±15 % of nominal, with each rate's median at least 1.2 times the previous one. All checks
passed, with median payload bitrates of 7.36, 11.35, 15.43, 23.46 and 38.96 kbit/s, 2.3–8.0 % below
nominal, and at 8 kbit/s the sweep's `signal=voice` encoding produced Ogg files byte-identical to
those of the OPUS settings (`signal=auto`) for all 1,665 utterances. The rule compares the slope $S$
with $S^\ast = (U^\ast - T^\ast)/\log_2 5$, the slope implied by the confirmatory residuals at
8 kbit/s ($T^\ast$, OPUS − LP) and 40 kbit/s ($U^\ast$, SILK − LP): GO if the lower bound of $R_8$ is
above zero, the upper bound of $S$ is below zero and its lower bound is at or below $0.5\,S^\ast$;
FALSIFY if the upper bound of $S$ is at or above zero and its lower bound is above $0.5\,S^\ast$.
Both recognisers returned GO (Table S8). The decline was concentrated at low rates: the step from 8
to 12 kbit/s was the largest (+0.34 and
+1.32 pp), the point estimates fell at every step in both recognisers, and 66 % (Whisper) and
98 % (wav2vec2) of bootstrap replicates were monotone. On test-clean the Whisper slope interval only
just excluded zero (−0.055 [−0.111, −0.001]); per-subset values are in Table S12. The descriptors
changed with the rate: median LSD over 0–3 kHz relative to LP fell from 6.19 to 1.37 dB
and coherence rose from 0.623 to 0.993, the median RMS change relative to REF went from −0.68 to
−0.12 dB, the in-band gain from −1.83 to −0.08 dB, and the mirror coherence from 0.245 to 0.970.

| Bitrate sweep (pooled) | Whisper large-v3 | wav2vec2-base-960h |
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

: Bitrate sweep: trend over bitrate, adjacent-rate and endpoint contrasts (pp; secondary), and the pre-declared rule. S* is the slope implied by the confirmatory residuals at 8 and 40 kbit/s.

# S6. Inclusive best-linear attribution

The plan, a method note, a signal-only selection, the calibration, the code freeze and a held-out
validation were committed before any confirmation-set projection was computed (main paper,
Section 3.9). LIN8 is the orthogonal projection of the confirmation's exact Opus waveform onto the
span of REF delayed by −256 to +255 samples (512 basis vectors), computed as in the BSS Eval
reference code with a centred delay span. Calibration and held-out validation each used one
utterance from 40 new train-clean-100 speakers (20 female and 20 male per set; no transcripts or
ASR): the projection was numerically exact, a second pass reproduced every waveform, and the
held-out median projection error (−11.61 dB) stayed within the frozen tolerance of 3.08 dB above
the calibration median (−12.39 dB). Before recognition, the regenerated Opus files and
waveforms equalled those of the confirmation for all 2,174 utterances, and the analysis code
reproduced the confirmation's contrasts. The frozen outcome was ROBUST_RESIDUAL: the residual
beyond LIN8 lay above zero and exceeded the linear component in both recognisers (Table S9) and in
both subsets (Table S12). Table S10 shows what the linear component absorbs: a gain about 2 dB below
the control and a steeper in-band roll-off. LIN8 was recognised in its own run, so Whisper's batches
differed from the confirmation's; wav2vec2 decodes each utterance alone. The confirmation projections
used single-threaded linear algebra because of CPU contention on the shared machine, which changes
rare samples in the last bit only.

| Pooled | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| WER, LIN8 (%) | 2.58 [2.28, 2.92] | 6.52 [5.69, 7.41] |
| LIN8 − REF (pp) | +0.09 [−0.02, +0.19] | +1.16 [+0.81, +1.55] |
| OPUS − LIN8 (pp) | +0.74 [+0.51, +1.00] | +2.32 [+1.85, +2.97] |
| LIN8 − LP (pp) | −0.06 [−0.13, +0.01] | −0.25 [−0.47, −0.04] |
| Linear share | 0.10 [−0.02, 0.22] | 0.33 [0.28, 0.39] |
| Sequential share | 0.17 [0.05, 0.29] | 0.40 [0.35, 0.45] |
| Outcome (frozen rule) | ROBUST_RESIDUAL | ROBUST_RESIDUAL |

: Inclusive best-linear attribution on the confirmation set (2,174 utterances, 73 speakers; pooled; 95 % speaker-bootstrap intervals with the confirmation's seed): corpus WER of LIN8 (%), the linear component LIN8 − REF, the residual beyond it OPUS − LIN8 and the difference from the control LIN8 − LP (pp), the descriptive linear share (LIN8 − REF)/(OPUS − REF) beside the sequential share (LP − REF)/(OPUS − REF), and the frozen outcome. The linear share is not a bandwidth share.

| Descriptor | LIN8, calibration | LIN8, validation | LIN8, confirmation | LP control |
|---|---|---|---|---|
| Projection NMSE (dB) | −12.39 | −11.61 | −12.08 | — |
| Gain, 0.5–2 kHz (dB) | −2.05 | −2.10 | −2.22 | 0.00 |
| Response at 3.0 kHz, relative (dB) | −4.57 | −4.54 | −4.54 | −0.62 |
| Response at 3.5 kHz, relative (dB) | −6.94 | −6.79 | −7.30 | −2.16 |
| Response at 4.0 kHz, relative (dB) | −16.68 | −16.87 | −15.66 | −10.76 |
| Delay (samples) | 1.69 | 1.64 | 1.67 | 0 |
| Pooled coherence 0–3.5 kHz, OPUS / LIN8 | 0.650 / 0.945 | 0.658 / 0.939 | — | — |
| Pooled 4–8 kHz power vs REF, OPUS / LIN8 (dB) | −17.5 / −28.8 | −18.4 / −30.7 | — | — |

: Linear response of the 8 kbit/s chain: medians of the per-utterance best-linear filters on the calibration, validation and confirmation sets (projection error, gain over 0.5–2 kHz, response at fixed frequencies relative to that gain, and phase-slope delay), with the frozen LP control for comparison, and pooled cross-spectral measures against REF (no ASR). Descriptive only; further rows are in the repository.

# S7. Decoder, application mode and bandwidth allocation

Each of these analyses changes one element of the codec chain (Table S11; per subset, Table S12).

**Decoder.** The same frozen confirmation bitstreams were decoded with the libopus 1.4 reference
decoder, which applied RFC 7845 pre-skip and end trimming at 48 kHz, followed by the resampler of
the primary chain, with no gain, alignment or filtering; only OPUS_LIBOPUS was recognised, once.
All pre-recognition checks passed: bitstreams byte-identical to the confirmation's (2,174 of
2,174), no decoding error, the pre-specified output lengths, no non-finite sample, an unchanged
environment and exact reproduction of the confirmatory OPUS − REF. The analysis tests the total penalty only: no bandwidth
component, share or residual was computed under libopus, and a result without a clear difference is
not an equivalence claim.

**Application mode.** The encoder was run again with `OPUS_APPLICATION_VOIP`; every other setting,
the Ogg writer, the decoder and the resampler were unchanged, and the signal-type hint stayed
`signal=auto`. In checks committed before recognition, the regenerated OPUS_AUDIO8 bitstreams and
waveforms equalled those of the confirmation for all 2,174 utterances, every OPUS_VOIP8 utterance
was encoded and decoded to the REF length without non-finite samples, every encoder control read
back as requested, and every packet was mono, narrowband and 20 ms (all SILK).
Under the frozen rule, both recognisers returned NO_CLEAR_APPLICATION_DIFFERENCE. For Whisper
large-v3 the upper bound is exactly zero, and the CER contrast and the test-other contrast excluded zero (secondary,
uncorrected). The VoIP mode changed every waveform at an almost unchanged payload bitrate (median
7.29 against 7.34 kbit/s), with slightly lower in-band coherence (median 0.614 against 0.623); these
descriptors enter no rule.

**Bandwidth allocation.** On the 1,665 sweep utterances, NB8 had to reproduce the sweep's SILK8 files
byte for byte, every WB8 packet had to be SILK-only wideband with 20 ms frames, every encoder setting
had to read back as requested, WB8's median payload bitrate had to lie within ±15 % of nominal and
within ±10 % of NB8's, and WB8's pooled 4–8 kHz power relative to REF had to be at least −10 dB; all
checks passed. NB8's Ogg files and raw hypotheses were identical to those of the sweep's SILK8 for
all 1,665 utterances in both recognisers. In the secondary per-subset analysis, the interval for
Whisper large-v3 on test-clean lay above zero (+0.27 pp [+0.03, +0.54]), and that for
wav2vec2-base-960h on test-other below zero (−1.70 pp [−2.75, −0.65]).

| Pooled | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| WER, OPUS: FFmpeg, application audio (%) | 3.32 [2.86, 3.82] | 8.84 [7.72, 10.17] |
| WER, OPUS_LIBOPUS (%) | 3.22 [2.78, 3.70] | 8.92 [7.78, 10.26] |
| WER, OPUS_VOIP8 (%) | 3.20 [2.79, 3.64] | 8.80 [7.70, 10.07] |
| OPUS_LIBOPUS − OPUS (pp) | −0.11 [−0.17, −0.04] | +0.09 [−0.04, +0.21] |
| Outcome, decoder (frozen rule) | DECODER_LOWER_PENALTY | NO_CLEAR_DECODER_DIFFERENCE |
| OPUS_VOIP8 − OPUS (pp) | −0.12 [−0.25, +0.00] | −0.03 [−0.23, +0.15] |
| OPUS_VOIP8 − OPUS, CER (pp) | −0.07 [−0.13, −0.007] | −0.05 [−0.13, +0.04] |
| Outcome, application (frozen rule) | NO_CLEAR_APPLICATION_DIFFERENCE | NO_CLEAR_APPLICATION_DIFFERENCE |
| WER, NB8, sweep utterances (%) | 3.40 [2.97, 3.87] | 9.68 [8.44, 11.09] |
| WER, WB8, sweep utterances (%) | 3.54 [3.06, 4.06] | 8.70 [7.62, 9.94] |
| WB8 − NB8 (pp) | +0.14 [−0.07, +0.36] | −0.98 [−1.57, −0.42] |
| Outcome, allocation (frozen rule) | NO_CLEAR_DIFFERENCE | WB_BETTER |

: Decoder, application mode and bandwidth allocation (pooled; 95 % speaker-bootstrap intervals): corpus WER (%), the difference from the primary chain (pp) and the frozen outcome of each analysis. The decoder and application-mode rows use the 2,174 confirmation utterances, the allocation rows the 1,665 sweep utterances. Total penalties and practical contrasts only: no bandwidth share, residual or equivalence is claimed.

| Analysis (pp) | Subset | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|---|
| Level matching: OPUS8_LEVEL_MATCHED − LP | test-clean | +0.32 [+0.17, +0.50] | +0.96 [+0.75, +1.20] |
| Level matching: OPUS8_LEVEL_MATCHED − LP | test-other | +1.21 [+0.74, +1.76] | +3.61 [+2.81, +4.64] |
| Level matching: OPUS8_LEVEL_MATCHED − OPUS | test-clean | +0.028 [+0.000, +0.059] | +0.028 [−0.013, +0.069] |
| Level matching: OPUS8_LEVEL_MATCHED − OPUS | test-other | −0.011 [−0.037, +0.016] | +0.005 [−0.084, +0.090] |
| Sweep: SILK8 − LP | test-clean | +0.11 [−0.04, +0.27] | +0.62 [+0.32, +0.97] |
| Sweep: SILK8 − LP | test-other | +0.95 [+0.65, +1.28] | +3.39 [+2.67, +4.27] |
| Sweep: slope (pp per doubling) | test-clean | −0.055 [−0.111, −0.001] | −0.243 [−0.388, −0.121] |
| Sweep: slope (pp per doubling) | test-other | −0.344 [−0.450, −0.243] | −1.410 [−1.816, −1.060] |
| Best-linear: OPUS − LIN8 | test-clean | +0.28 [+0.14, +0.46] | +1.08 [+0.82, +1.37] |
| Best-linear: OPUS − LIN8 | test-other | +1.36 [+0.87, +1.93] | +3.99 [+2.99, +5.44] |
| Decoder: OPUS_LIBOPUS − OPUS | test-clean | −0.01 [−0.07, +0.05] | −0.02 [−0.14, +0.09] |
| Decoder: OPUS_LIBOPUS − OPUS | test-other | −0.23 [−0.37, −0.10] | +0.23 [+0.00, +0.47] |
| Application: OPUS_VOIP8 − OPUS | test-clean | −0.004 [−0.10, +0.09] | −0.07 [−0.28, +0.13] |
| Application: OPUS_VOIP8 − OPUS | test-other | −0.28 [−0.56, −0.02] | +0.02 [−0.33, +0.38] |
| Allocation: WB8 − NB8 | test-clean | +0.27 [+0.03, +0.54] | −0.19 [−0.43, +0.06] |
| Allocation: WB8 − NB8 | test-other | +0.03 [−0.30, +0.36] | −1.70 [−2.75, −0.65] |

: Robustness analyses per subset (secondary scope; no multiplicity correction; pp, 95 % speaker-bootstrap intervals). The sweep and allocation rows use the 1,665 sweep utterances, all other rows the confirmation utterances. A bound printed as zero is exactly zero, and its interval includes zero.

# S8. Error weighting

Without new recognition, the primary contrasts were recomputed from the confirmation outputs in every
bootstrap replicate (the confirmation's seed on the same speakers) under four weightings: corpus WER,
mean per-utterance WER, equal-speaker WER (the mean of per-speaker corpus WERs) and CER. The
classification criteria were fixed in the audit code before it was run. A sign or ordering statement
is robust to the weighting if its interval lies above zero under all four pooled weightings and,
under corpus WER, in both subsets; a share is unstable if any pooled replicate has a non-positive
denominator, if its corpus-WER interval has an upper-to-lower ratio above 2, or if its point
estimates differ by more than a factor of 1.5 across weightings. The residual and its excess over
the bandwidth component were robust for both recognisers, Whisper's bandwidth component was
subset-dependent (not detectable on test-clean), the Whisper share was unstable and the wav2vec2
share robust; no pooled replicate had a non-positive denominator (Table S13). In secondary cells,
the ordering was unresolved for Whisper on test-clean under CER and for wav2vec2 on test-other under
mean per-utterance WER, and for wav2vec2 the deletions rose more with band limitation than beyond it
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

: Error weighting of the primary contrasts on the confirmation set (pooled; pp; 95 % speaker-bootstrap intervals with the confirmation's seed): bandwidth component, residual, their difference and the sequential share under four weightings. No new recognition.

# S9. Attribution analyses stopped before ASR

Two additional attribution sensitivities were prospectively gated but stopped before ASR because
their signal-domain controls failed held-out validation. Table S14 gives the failed criteria. The
decoder-matched control (LP_LIBOPUS) was to test the decomposition under the libopus decoder; it had
been fitted by the unchanged procedure of main-paper Section 3.4 because the frozen control failed a
pre-specified control-reuse gate against the libopus-decoded SILK narrowband response. The 8 kbit/s
surrogate (SURR8), fitted to the same-frequency coherent response of Opus at 8 kbit/s, was to give
an attribution under a more inclusive linear-loss definition; it is not a bandwidth control. The
held-out subset was new and signal-only (no transcripts; 40 train-clean-100 speakers, 20 female and
20 male, one utterance each, disjoint from the calibration and filter-validation speakers). Neither
control was redesigned or refitted: a repaired control would be a new design that needs its own
held-out validation. A post hoc and exploratory diagnosis points to a sub-sample, content-dependent
delay of the libopus-decoded chain; no successor analysis has been run.

| Analysis | Intended question | Failed held-out criterion | Value (dB) | Threshold (dB) | Consequence |
|---|---|---|---|---|---|
| LP_LIBOPUS | Decomposition under the libopus decoder | Transition shape: RMS $\lvert H_1\rvert$ difference, 3.0–4.2 kHz | 2.07 | 1.5 | STOPPED |
| SURR8 | Share under a more inclusive linear-loss definition | Transition shape: RMS difference from its target | 2.04 | 1.5 | STOPPED |
| SURR8 | (as above) | Transition shape: maximum difference from its target | 8.91 | 4.0 | STOPPED |

: Attribution analyses stopped before ASR: the intended question, the failed held-out criterion of each signal-domain control, its value and pre-specified threshold, and the consequence (STOPPED: no recognition was run). The primary control and decomposition are unchanged.

# S10. Amendments and deviations

Before any evaluation decoding, greedy decoding replaced beam search for Whisper, for compute reasons
on a shared GPU. After the pilot and before the confirmation, one figure changed from text labels to
marker shapes (presentation only). During the controls stage, the first validation of the low-pass
control failed on an internally inconsistent criterion; the corrected criterion was frozen before
the confirmation data were downloaded, and the failed result is retained (main paper, Section 3.4).
Before the code freeze of the level-matching analysis, a calibration check found that level matching
changed 1 of 20 wav2vec2-base-960h hypotheses, whereas the plan had expected invariance to a scalar
gain; a dated amendment, sealed before the freeze and before any evaluation audio was decoded,
corrected that expectation and changed no estimand, gate, threshold, condition, selection or rule.
The other later analyses had deviations that changed no gate, tolerance, rule, selection or outcome
(for example descriptive items computed from sealed outputs after the analysis, a validation report
sealed in parts, single-threaded linear algebra for the best-linear attribution, and a manuscript
description of the decoder analysis longer than its plan foresaw); the full lists are in the sealed
records.
