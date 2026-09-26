# Results notes (draft 1, 2026-09-26)

All numbers are copied from `results_paper/stage3_asr/` (`06_corpus_metrics.csv`,
`07_paired_bootstrap.csv`, `09_signal_*.csv`, `03_audio_manifest.csv`,
`11_exploratory_signal_correlations.csv`) and `pilot/pilot_bootstrap.csv`. WER in %,
differences in percentage points (pp), 95 % speaker-bootstrap CIs. W = Whisper large-v3,
V = wav2vec2-base-960h. Approved wording: `01b_interpretation_note_2026-09-26.md`.

## 0. Context (prior study and Stage 2, not Stage 3 evidence)

- **Prior study** (frozen ELEC5305, wav2vec2-base-960h, raw uppercase scoring, 500
  utterances per subset). ΔWER vs WAV:

  | | Opus 12 kbps (SILK-WB) | Opus 8 kbps (SILK-NB) |
  |---|---|---|
  | test-clean | +0.32 pp | +1.15 pp |
  | test-other | +1.33 pp | +6.63 pp |

  This onset motivated the question. The numbers are not comparable in absolute terms
  (different utterances and scoring).
- **Stage 2A.** Forced SILK-NB / SILK-WB at 8 and 12 kbps was reliable (100 % of packets in
  the requested bandwidth). Packets were byte-identical to the prior-study ffmpeg path
  (40/40 dev-clean utterances).
- **Stage 2B.** The LP control reproduces SILK-NB's linear band-limiting. On unseen speakers:
  LSD 0–3 kHz 0.031 dB, coherent bandwidth 4,094 Hz vs 4,125 Hz for the reference, |H1| RMS
  difference 0.57 dB.

## 1. Pilot (dev-clean + dev-other, 138 utterances, 69 speakers)

| | REF | LP | OPUS | SILK | NEG_LP | NEG_CODEC |
|---|---|---|---|---|---|---|
| W | 2.11 | 2.32 | 2.67 | 2.39 | 2.08 | 2.18 |
| V | 5.16 | 7.20 | 8.69 | 6.79 | 5.16 | 5.23 |

| micro | W | V |
|---|---|---|
| LP − REF | +0.21 [−0.23, +0.67] | +2.04 [+1.12, +3.17] |
| OPUS − LP | **+0.35 [+0.07, +0.64]** | **+1.49 [+0.74, +2.25]** |
| SILK − LP | +0.07 [−0.21, +0.30] | −0.42 [−0.84, +0.03] |
| OPUS − SILK | +0.28 [−0.07, +0.64] | +1.91 [+1.09, +2.71] |
| NEG_LP − REF | −0.03 [−0.32, +0.25] | +0.00 [−0.26, +0.24] |
| NEG_CODEC − REF | +0.07 [−0.07, +0.25] | +0.07 [−0.19, +0.35] |

Pre-declared kill test: **PROCEED** (the OPUS residual CI excludes 0 in both recognisers).

## 2. Confirmation: corpus WER (test-clean + test-other, 2,174 utterances, 73 speakers)

| | REF | LP | OPUS | SILK | NEG_LP | NEG_CODEC |
|---|---|---|---|---|---|---|
| W | 2.50 [2.19, 2.84] | 2.64 [2.32, 2.98] | 3.32 [2.86, 3.82] | 2.66 [2.34, 3.01] | 2.42 [2.11, 2.76] | 2.50 [2.19, 2.84] |
| V | 5.36 [4.73, 6.08] | 6.76 [5.89, 7.74] | 8.84 [7.72, 10.17] | 6.68 [5.85, 7.60] | 5.46 [4.80, 6.22] | 5.36 [4.71, 6.10] |

Word errors out of 43,417 reference words: W 1,084 / 1,145 / 1,443 / 1,153 (REF / LP / OPUS /
SILK); V 2,327 / 2,937 / 3,836 / 2,899. No empty hypotheses in any condition.

## 3. Decomposition (confirmation)

| | W micro | W macro | V micro | V macro |
|---|---|---|---|---|
| LP − REF (bandwidth) | +0.14 [+0.04, +0.25] | +0.35 [+0.17, +0.54] | +1.40 [+0.99, +1.92] | +1.90 [+1.39, +2.44] |
| **OPUS − LP (residual)** | **+0.69 [+0.46, +0.94]** | +1.00 [+0.64, +1.39] | **+2.07 [+1.68, +2.57]** | +2.61 [+2.12, +3.13] |
| SILK − LP | +0.02 [−0.04, +0.08] | −0.02 [−0.15, +0.11] | −0.09 [−0.20, +0.02] | −0.13 [−0.30, +0.05] |
| OPUS − SILK | +0.67 [+0.46, +0.89] | +1.02 [+0.65, +1.40] | +2.16 [+1.73, +2.71] | +2.73 [+2.18, +3.33] |
| OPUS − REF (total) | +0.83 [+0.57, +1.10] | +1.35 [+0.93, +1.78] | +3.48 [+2.73, +4.45] | +4.50 [+3.65, +5.47] |
| SILK − REF | +0.16 [+0.07, +0.26] | +0.33 [+0.19, +0.50] | +1.32 [+0.94, +1.78] | +1.77 [+1.29, +2.29] |

- **Bandwidth share of the total penalty (pre-declared secondary):**
  - of OPUS − REF: W 0.17 [0.05, 0.29]; V 0.40 [0.35, 0.45];
  - of SILK − REF: W 0.88 [0.39, 1.36]; V 1.07 [0.98, 1.15].
- **Baseline-relative effects** (post hoc, descriptive, no CIs):

  | | W | V |
  |---|---|---|
  | bandwidth, as % of REF WER | +5.6 % | +26.2 % |
  | OPUS residual, as % of LP WER | +26.0 % | +30.6 % |
  | OPUS total, as % of REF WER | +33.1 % | +64.8 % |
  | SILK residual, as % of LP WER | +0.7 % | −1.3 % |

- **CER (micro):** OPUS − LP W +0.31 [+0.20, +0.44], V +1.09 [+0.87, +1.40]; LP − REF
  W +0.12 [+0.07, +0.18], V +0.59 [+0.42, +0.81].
- **Decision:** GO (OPUS). Result types 2 (REF < LP < OPUS) and 3 (OPUS and SILK residuals
  differ).

## 4. Per subset (secondary; no multiplicity correction)

| subset | | REF | LP | OPUS | SILK | LP − REF | OPUS − LP | SILK − LP |
|---|---|---|---|---|---|---|---|---|
| test-clean | W | 1.62 | 1.59 | 1.88 | 1.59 | −0.03 [−0.13, +0.07] | +0.29 [+0.15, +0.46] | −0.00 [−0.06, +0.05] |
| test-clean | V | 3.30 | 3.71 | 4.65 | 3.74 | +0.41 [+0.20, +0.64] | +0.94 [+0.72, +1.18] | +0.02 [−0.06, +0.10] |
| test-other | W | 3.68 | 4.05 | 5.27 | 4.10 | +0.37 [+0.16, +0.59] | +1.22 [+0.75, +1.77] | +0.05 [−0.08, +0.18] |
| test-other | V | 8.13 | 10.88 | 14.48 | 10.64 | +2.75 [+1.83, +3.92] | +3.60 [+2.78, +4.68] | −0.24 [−0.50, −0.005] |

## 5. Error types (confirmation, Δ errors per 100 reference words)

| | S | D | I |
|---|---|---|---|
| W LP − REF | +0.09 [+0.01, +0.18] | +0.03 [−0.01, +0.06] | +0.02 [−0.01, +0.05] |
| W OPUS − LP | +0.51 [+0.34, +0.70] | +0.10 [+0.05, +0.16] | +0.08 [+0.03, +0.13] |
| W SILK − LP | +0.03 [−0.02, +0.09] | −0.01 [−0.03, +0.01] | −0.00 [−0.02, +0.02] |
| V LP − REF | +1.16 [+0.83, +1.58] | +0.23 [+0.14, +0.33] | +0.02 [−0.03, +0.07] |
| V OPUS − LP | +1.79 [+1.46, +2.21] | +0.13 [+0.05, +0.22] | +0.15 [+0.09, +0.20] |
| V SILK − LP | −0.08 [−0.18, +0.02] | −0.03 [−0.06, +0.01] | +0.02 [−0.01, +0.04] |

Substitutions make up 74 % (W) and 86 % (V) of the OPUS − LP residual.

## 6. Negative controls (confirmation)

| | W | V |
|---|---|---|
| NEG_LP − REF | −0.08 [−0.15, −0.004] | +0.10 [+0.02, +0.19] |
| NEG_CODEC − REF | +0.002 [−0.046, +0.049] | +0.002 [−0.057, +0.065] |

Neither control is flagged (margin ±0.5 pp). NEG_LP's CIs exclude 0 in opposite directions,
so effects of order 0.1 pp are at the resolution limit of this pipeline.

## 7. Signal descriptors (confirmation)

Per-utterance medians vs REF:

| | LP | OPUS | SILK | NEG_LP | NEG_CODEC |
|---|---|---|---|---|---|
| LSD full band (dB) | 9.71 | 10.42 | 9.15 | 3.48 | 1.57 |
| LSD 0–3 kHz | 0.03 | 6.14 | 1.37 | 0.00 | 1.29 |
| LSD 0–4 kHz | 1.42 | 6.46 | 2.16 | 0.00 | 1.30 |
| LSD 4–8 kHz | 13.60 | 12.60 | 12.52 | 4.92 | 1.64 |
| retained bandwidth, power-based (Hz) | 4,094 | 4,625 | 4,656 | 7,156 | 8,000 |
| 4–8 kHz power change (dB) | −25.4 | −17.2 | −16.3 | −0.5 | −0.4 |
| coherence 0–3.5 kHz | 1.000 | 0.623 | 0.993 | 1.000 | 0.995 |
| RMS change (dB) | −0.08 | −0.68 | −0.11 | −0.005 | −0.003 |
| lag (samples, min–max) | 0 | 1–2 | 1–2 | 0 | 0 |

Codec vs LP (medians): LSD 0–3 kHz OPUS 6.14 dB, SILK 1.37 dB; coherence 0–3.5 kHz 0.623 /
0.993; envelope decorrelation 0.009 / 0.000.

Pooled cross-spectra vs REF:

| | LP | OPUS | SILK |
|---|---|---|---|
| coherent bandwidth (Hz) | 4,094 | 4,000 | 4,094 |
| coherent 4–8 kHz power (dB) | −24.6 | −34.0 | −25.0 |
| total 4–8 kHz power (dB) | −24.5 | −16.7 | −15.8 |
| mirror coherence 4.1–4.9 kHz | 0.000 | 0.227 | 0.970 |
| \|H1\| level (0.5–2 kHz, dB) | 0.00 | −1.83 | −0.08 |

- The power-based "retained bandwidth" of the codec conditions (≈4.6 kHz) includes the image;
  their coherent bandwidth is ≈4.0–4.1 kHz, the same as LP.
- SILK's coherent response matches LP. OPUS's coherent 4–8 kHz power is lower (edge coding
  droop) and its in-band coherent gain is −1.8 dB.

## 8. Exploratory (Step 12; not confirmatory)

- 36 Spearman correlations between the per-utterance residual and signal features.
- 4 have CIs excluding 0, all with |ρ| ≤ 0.09:
  - OPUS/V, coherence(LP, OPUS): −0.09 [−0.16, −0.02];
  - SILK/W, LSD 0–3 kHz vs LP: +0.06 [+0.01, +0.10];
  - SILK/W, LSD 0–4 kHz vs LP: +0.07 [+0.01, +0.11];
  - SILK/W, coherence vs LP: −0.05 [−0.09, −0.003].
- Utterance-level signal features explain little of which utterances are affected. No
  mechanism inference.

## Key sentences for the Results section (approved wording)

- "Bandwidth removal alone increased corpus WER by 0.14 pp [0.04, 0.25] (Whisper large-v3)
  and 1.40 pp [0.99, 1.92] (wav2vec2-base-960h)."
- "Relative to the low-pass control, Opus at 8 kbps increased WER by a further 0.69 pp
  [0.46, 0.94] and 2.07 pp [1.68, 2.57]; bandwidth removal accounted for 17 % [5, 29] and
  40 % [35, 45] of the total Opus penalty."
- "Relative to each recogniser's own baseline, the residual was similar (+26 % and +31 % of
  the low-pass WER), whereas the bandwidth penalty differed (+6 % vs +26 % of REF WER)."
- "High-rate SILK narrowband showed no detectable pooled residual (+0.02 pp [−0.04, 0.08];
  −0.09 pp [−0.20, 0.02]); for wav2vec2 on test-other it was slightly below the low-pass
  control (−0.24 pp [−0.50, −0.005], secondary analysis)."
