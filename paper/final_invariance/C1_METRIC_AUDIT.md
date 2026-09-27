# C1 — Metric and weighting robustness audit

Status: complete, no new ASR. Sealed record `results_paper/final_invariance/C1_RECORD.json`
(`record_sha256` 0981f5af737194932118d3145fda7509b39494a20cc80301179227953a850b7b); table
`results_paper/final_invariance/c1_metric_table.csv` (sha256 043260f409e805abb014d22f856d5c8c3e6759b593857e31fc04bf2cf0cb891e);
code `paper/final_invariance/c1_metric_audit.py`; tests `paper/final_invariance/tests/test_c1.py`.

## 1. What was done

The only inputs were the sealed Stage 3 confirmation per-utterance outputs for REF, LP and OPUS
(`utterance_metrics.csv`, verified against its sealed manifest `de82f749…`). No audio was decoded
and no recogniser was run. Every metric was recomputed inside each replicate of the frozen Stage 3
paired speaker-cluster bootstrap. The bootstrap used 10,000 replicates, seed 5305, speakers
resampled within test subsets, and 95 % percentile intervals, so the primary micro contrasts
reproduce the sealed Stage 3 bootstrap to 4 × 10⁻¹⁶ pp.

Metrics:

- micro WER, the corpus WER and the primary Stage 3 estimator;
- macro WER, the mean per-utterance WER;
- equal-speaker WER, the mean of per-speaker corpus WERs, which gives each speaker equal weight;
- CER;
- S, D and I per 100 reference words;
- relative change from REF (B/REF, R/REF, T/REF);
- the sequential share B/T under each weighting.

For each metric we report B = LP − REF, R = OPUS − LP, T = OPUS − REF and R − B.

The classification rules were written into the script's docstring before it was first run, and
they are copied into the sealed record.

- **Sign and ordering statements** (B > 0, R > 0, R > B), per recogniser. A statement holds in a
  cell if its interval lies above zero.
  - METRIC_ROBUST: it holds for all four pooled weightings and, under micro, in both subsets.
  - WEIGHTING_SENSITIVE: it holds for pooled micro but fails for another pooled weighting.
  - SUBSET_DEPENDENT: it fails in a subset.
- **The share B/T** is RATIO_UNSTABLE if any of the following holds:
  - some pooled replicate has T ≤ 0;
  - the micro interval has a lower bound ≤ 0 or an upper/lower ratio > 2;
  - the point estimates across weightings differ by more than a factor of 1.5.

## 2. Classification of the pre-declared statements

| Statement | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| Bandwidth component B > 0 | **SUBSET_DEPENDENT** (holds for all four pooled weightings; not detectable on test-clean) | **METRIC_ROBUST** |
| Codec-specific residual R > 0 | **METRIC_ROBUST** | **METRIC_ROBUST** |
| Ordering R > B | **METRIC_ROBUST** (two secondary cells disagree, §4) | **METRIC_ROBUST** (one secondary cell disagrees, §4) |
| Sequential share B/T | **RATIO_UNSTABLE** (wide interval; 0.17–0.28 across weightings) | **METRIC_ROBUST** (0.35–0.42 across weightings) |

## 3. Pooled contrasts under each weighting (pp; 95 % speaker-bootstrap intervals)

| Recogniser | Metric | B = LP − REF | R = OPUS − LP | T = OPUS − REF | R − B | P(R > B) |
|---|---|---|---|---|---|---|
| Whisper | micro WER (primary) | +0.14 [+0.04, +0.25] | +0.69 [+0.46, +0.94] | +0.83 [+0.57, +1.10] | +0.55 [+0.30, +0.82] | 1.000 |
| Whisper | macro WER | +0.35 [+0.17, +0.54] | +1.00 [+0.64, +1.39] | +1.35 [+0.93, +1.78] | +0.65 [+0.25, +1.08] | 1.000 |
| Whisper | equal-speaker WER | +0.18 [+0.05, +0.31] | +0.77 [+0.53, +1.01] | +0.94 [+0.68, +1.22] | +0.59 [+0.32, +0.88] | 1.000 |
| Whisper | CER | +0.12 [+0.07, +0.18] | +0.31 [+0.20, +0.44] | +0.43 [+0.30, +0.59] | +0.19 [+0.08, +0.32] | 1.000 |
| wav2vec2 | micro WER (primary) | +1.40 [+0.99, +1.92] | +2.07 [+1.68, +2.57] | +3.48 [+2.73, +4.45] | +0.67 [+0.37, +0.95] | 1.000 |
| wav2vec2 | macro WER | +1.90 [+1.39, +2.44] | +2.61 [+2.12, +3.13] | +4.50 [+3.65, +5.47] | +0.71 [+0.21, +1.20] | 0.998 |
| wav2vec2 | equal-speaker WER | +1.52 [+1.13, +1.95] | +2.16 [+1.79, +2.57] | +3.68 [+3.00, +4.46] | +0.63 [+0.32, +0.95] | 1.000 |
| wav2vec2 | CER | +0.59 [+0.42, +0.81] | +1.09 [+0.87, +1.40] | +1.69 [+1.30, +2.20] | +0.50 [+0.36, +0.65] | 1.000 |

The residual and the ordering R > B hold under every weighting for both recognisers. Macro WER
gives the largest pp values because short utterances, whose per-utterance WER moves in large
steps, weigh as much as long ones. Equal-speaker weighting lies close to micro.

## 4. Subsets (pp)

| Recogniser | Subset | Metric | B | R | R − B | P(R > B) |
|---|---|---|---|---|---|---|
| Whisper | test-clean | micro WER | −0.03 [−0.13, +0.07] | +0.29 [+0.15, +0.46] | +0.32 [+0.12, +0.54] | 0.999 |
| Whisper | test-clean | macro WER | +0.05 [−0.09, +0.19] | +0.37 [+0.15, +0.61] | +0.32 [+0.02, +0.63] | 0.981 |
| Whisper | test-clean | equal-speaker WER | −0.03 [−0.13, +0.08] | +0.34 [+0.16, +0.53] | +0.36 [+0.13, +0.60] | 0.999 |
| Whisper | test-clean | CER | +0.01 [−0.03, +0.06] | +0.10 [+0.03, +0.17] | +0.09 [−0.01, +0.19] | 0.965 |
| Whisper | test-other | micro WER | +0.37 [+0.16, +0.59] | +1.22 [+0.75, +1.77] | +0.85 [+0.37, +1.40] | 1.000 |
| Whisper | test-other | macro WER | +0.71 [+0.34, +1.10] | +1.76 [+1.02, +2.58] | +1.05 [+0.26, +1.93] | 0.996 |
| Whisper | test-other | equal-speaker WER | +0.42 [+0.19, +0.69] | +1.28 [+0.83, +1.79] | +0.87 [+0.35, +1.42] | 1.000 |
| Whisper | test-other | CER | +0.28 [+0.16, +0.40] | +0.61 [+0.36, +0.90] | +0.33 [+0.10, +0.60] | 0.998 |
| wav2vec2 | test-clean | micro WER | +0.41 [+0.20, +0.64] | +0.94 [+0.72, +1.18] | +0.53 [+0.31, +0.73] | 1.000 |
| wav2vec2 | test-clean | macro WER | +0.59 [+0.31, +0.90] | +1.24 [+0.92, +1.60] | +0.65 [+0.30, +1.00] | 1.000 |
| wav2vec2 | test-clean | equal-speaker WER | +0.48 [+0.26, +0.70] | +0.97 [+0.74, +1.23] | +0.50 [+0.26, +0.73] | 1.000 |
| wav2vec2 | test-clean | CER | +0.14 [+0.08, +0.21] | +0.41 [+0.30, +0.54] | +0.27 [+0.18, +0.38] | 1.000 |
| wav2vec2 | test-other | micro WER | +2.75 [+1.83, +3.92] | +3.60 [+2.78, +4.68] | +0.85 [+0.18, +1.46] | 0.994 |
| wav2vec2 | test-other | macro WER | +3.48 [+2.43, +4.68] | +4.26 [+3.27, +5.34] | +0.78 [−0.25, +1.78] | 0.932 |
| wav2vec2 | test-other | equal-speaker WER | +2.79 [+1.99, +3.75] | +3.60 [+2.86, +4.46] | +0.80 [+0.13, +1.42] | 0.992 |
| wav2vec2 | test-other | CER | +1.23 [+0.82, +1.75] | +2.05 [+1.55, +2.72] | +0.82 [+0.53, +1.11] | 1.000 |

**Disagreeing cells, reported and not hidden.** The declared rule checks subsets under micro only;
these cells fall outside it.

- **Whisper, B on test-clean.** B is not detectable under any weighting. It was already disclosed
  in the manuscript (Section 4.4). Whisper's pooled bandwidth component comes from test-other.
- **Whisper, test-clean CER.** R − B = +0.09 [−0.01, +0.19], P(R > B) = 0.965, so the ordering is
  not resolved in this cell. The residual itself, +0.10 [+0.03, +0.17], is positive.
- **wav2vec2, test-other macro WER.** R − B = +0.78 [−0.25, +1.78], P(R > B) = 0.932, so the
  ordering is not resolved in this cell. Under micro, equal-speaker and CER weighting it is
  resolved.

In every subset × weighting cell, R is positive for both recognisers.

## 5. The sequential share B/T under each weighting

| Recogniser | Scope | micro | macro | equal-speaker | CER | replicates with T ≤ 0 (micro/macro/speaker/CER) |
|---|---|---|---|---|---|---|
| Whisper | pooled | 0.17 [0.05, 0.29] | 0.26 [0.14, 0.39] | 0.19 [0.06, 0.31] | 0.28 [0.17, 0.40] | 0/0/0/0 |
| Whisper | test-clean | −0.11 [−0.73, 0.25] | 0.12 [−0.27, 0.47] | −0.08 [−0.63, 0.25] | 0.09 [−0.38, 0.54] | 1/0/1/2 |
| Whisper | test-other | 0.23 [0.12, 0.36] | 0.29 [0.16, 0.44] | 0.25 [0.12, 0.38] | 0.31 [0.21, 0.43] | 0/0/0/0 |
| wav2vec2 | pooled | 0.40 [0.35, 0.45] | 0.42 [0.36, 0.48] | 0.41 [0.36, 0.46] | 0.35 [0.30, 0.39] | 0/0/0/0 |
| wav2vec2 | test-clean | 0.30 [0.19, 0.39] | 0.32 [0.21, 0.42] | 0.33 [0.23, 0.41] | 0.25 [0.17, 0.33] | 0/0/0/0 |
| wav2vec2 | test-other | 0.43 [0.37, 0.49] | 0.45 [0.38, 0.52] | 0.44 [0.38, 0.49] | 0.38 [0.33, 0.42] | 0/0/0/0 |

- **Denominator.** Pooled T > 0 in every replicate under every weighting for both recognisers.
  On Whisper test-clean, T ≤ 0 in 1–2 of 10,000 replicates, and the share there is not
  interpretable: its interval spans negative values.
- **The Whisper "17 %" (RATIO_UNSTABLE).** 17 % is the corpus-WER (micro) value, and it is the
  lowest of the four weightings.
  - Across weightings the point estimate ranges from 0.17 to 0.28, a factor of 1.65, beyond the
    declared 1.5.
  - The micro interval [0.05, 0.29] has an upper/lower ratio near 6.
  - The one property that survives every weighting: B is a minority of T. Every pooled upper
    bound is below 0.40, since the four upper bounds are 0.29, 0.39, 0.31 and 0.40 (0.396).
  - The precise value is not robust. The manuscript should keep "a small share" in the abstract
    and conclusion, and should not treat 17 % as a stable quantity. Where the number is given, it
    should be labelled as the corpus-WER value with its interval, and the 0.17–0.28 range across
    weightings should be stated.
- **The wav2vec2 "40 %" (METRIC_ROBUST).**
  - The pooled share is 0.35–0.42 across weightings.
  - Its intervals are narrow, and every upper bound is below 0.48.
  - CER gives the lowest value, 0.35 [0.30, 0.39].

## 6. Error types (pooled, per 100 reference words)

| Recogniser | Type | B | R | T | R − B |
|---|---|---|---|---|---|
| Whisper | S | +0.09 [+0.01, +0.18] | +0.51 [+0.34, +0.70] | +0.60 [+0.41, +0.82] | +0.41 [+0.22, +0.62] |
| Whisper | D | +0.03 [−0.01, +0.06] | +0.10 [+0.05, +0.16] | +0.12 [+0.07, +0.19] | +0.07 [+0.00, +0.15] |
| Whisper | I | +0.02 [−0.01, +0.05] | +0.08 [+0.03, +0.13] | +0.10 [+0.05, +0.16] | +0.06 [+0.00, +0.12] |
| wav2vec2 | S | +1.16 [+0.83, +1.58] | +1.79 [+1.46, +2.21] | +2.95 [+2.34, +3.75] | +0.63 [+0.41, +0.84] |
| wav2vec2 | D | +0.23 [+0.14, +0.33] | +0.13 [+0.05, +0.22] | +0.36 [+0.23, +0.51] | −0.09 [−0.22, +0.02] |
| wav2vec2 | I | +0.02 [−0.03, +0.07] | +0.15 [+0.09, +0.20] | +0.17 [+0.09, +0.24] | +0.13 [+0.05, +0.20] |

- **Substitutions.** They dominate both components for both recognisers. The manuscript's
  residual composition (74 % and 86 % substitutions) is reproduced exactly.
- **Deletions.** R > B does not hold for wav2vec2 deletions: the point estimate is B > R
  (−0.09 [−0.22, +0.02]).
- **Insertions.** R > B holds for wav2vec2 insertions.
- **Whisper.** The ordering holds for every error type, with interval lower bounds at or just
  above zero for D and I.
- **Scope of this finding.** The ordering is a property of substitution-dominated error totals,
  not of every error type. This is descriptive. We give no mechanism for it and do not pursue one
  (word-class and phone-class analyses are out of scope).

## 7. Relative change from REF (pooled; fractions of the REF level)

| Recogniser | Metric | REF level | B / REF | R / REF | T / REF |
|---|---|---|---|---|---|
| Whisper | micro WER | 2.50 % | 0.06 [0.01, 0.10] | 0.27 [0.19, 0.37] | 0.33 [0.24, 0.44] |
| Whisper | macro WER | 3.30 % | 0.11 [0.05, 0.17] | 0.30 [0.20, 0.41] | 0.41 [0.29, 0.53] |
| Whisper | equal-speaker WER | 2.69 % | 0.07 [0.02, 0.12] | 0.28 [0.21, 0.36] | 0.35 [0.26, 0.44] |
| Whisper | CER | 0.91 % | 0.13 [0.07, 0.20] | 0.34 [0.23, 0.47] | 0.48 [0.34, 0.64] |
| wav2vec2 | micro WER | 5.36 % | 0.26 [0.19, 0.36] | 0.39 [0.31, 0.48] | 0.65 [0.51, 0.83] |
| wav2vec2 | macro WER | 6.50 % | 0.29 [0.22, 0.38] | 0.40 [0.32, 0.50] | 0.69 [0.56, 0.86] |
| wav2vec2 | equal-speaker WER | 5.70 % | 0.27 [0.20, 0.35] | 0.38 [0.31, 0.46] | 0.65 [0.53, 0.80] |
| wav2vec2 | CER | 1.81 % | 0.33 [0.24, 0.44] | 0.61 [0.49, 0.77] | 0.93 [0.74, 1.20] |

## 8. Manuscript statements that are not in the scripted classifier

These post hoc descriptive statements in Section 4.3 were checked against the sealed table by
arithmetic only: point estimates, with no new bootstrap. They are classified by the same criteria.

- **"wav2vec2's residual was about three times … those of Whisper" — METRIC_ROBUST.**
  R(wav2vec2)/R(Whisper) is 3.0 under micro, 2.6 under macro, 2.8 under equal-speaker and 3.5
  under CER.
- **"… and its bandwidth component about ten times" — RATIO_UNSTABLE.**
  - B(wav2vec2)/B(Whisper) is 10.0 under micro, 5.5 under macro, 8.7 under equal-speaker and
    4.9 under CER.
  - The denominator, Whisper B, has interval [0.04, 0.25].
  - "Several times larger" survives; "about ten times" does not.
- **"Relative to each recogniser's own baseline, the residual was similar (+26.0 % and +30.6 % of
  the LP WER)" — WEIGHTING_SENSITIVE.** R/LP by weighting (Whisper vs wav2vec2):

  | Weighting | Whisper | wav2vec2 |
  |---|---|---|
  | micro | 26.0 % | 30.6 % |
  | macro | 27.4 % | 31.1 % |
  | equal-speaker | 26.7 % | 29.8 % |
  | CER | 30.3 % | 45.6 % |

  The two recognisers are similar under the three WER weightings but not under CER. Measured
  from REF, the CER intervals R/REF do not overlap: 0.34 [0.23, 0.47] vs 0.61 [0.49, 0.77]. The
  sentence should say "under WER".
- **"The bandwidth component still differed (+5.6 % and +26.2 % of the REF WER)" —
  METRIC_ROBUST.** B/REF is higher for wav2vec2 under every weighting, and the intervals do not
  overlap under any weighting.

## 9. What this means for the paper

- **What survives every weighting.** A positive codec-specific residual that exceeds the bandwidth
  component, for both recognisers. Every weighting is corpus-, utterance-, speaker- or
  character-level, and each is recomputed inside the frozen bootstrap.
- **The primary estimator is unchanged.** Micro WER remains primary; nothing in the frozen
  Stage 3 record changes.
- **Wording to weaken.**
  - The Whisper share is RATIO_UNSTABLE. Report it as "a small share (17 % under corpus WER;
    0.17–0.28 across weightings)". Never present it as a stable property.
  - The cross-recogniser "about ten times" should become "several times".
  - "Similar relative residual" should be qualified as "under WER".
- **Already disclosed.** The Whisper bandwidth component is subset-dependent (Section 4.4).
- **To disclose.** Two secondary cells leave the ordering unresolved (Whisper test-clean CER;
  wav2vec2 test-other macro). A short supplement note can state this.
