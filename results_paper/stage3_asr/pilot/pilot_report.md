# Stage 3 pilot (kill test)

**Pilot decision: PROCEED_TO_CONFIRMATION** — at least one codec residual has a 95% CI lower bound above 0.

Rule (frozen): PROCEED if any (model, codec) micro residual CI lower bound > 0; else STOP.

## Residuals

| model | codec | estimate_pp | ci_lower_pp | ci_upper_pp | clearly_positive |
|---|---|---|---|---|---|
| whisper | OPUS | 0.346 | 0.0727 | 0.639 | True |
| whisper | SILK | 0.0693 | -0.207 | 0.304 | False |
| wav2vec2 | OPUS | 1.49 | 0.736 | 2.25 | True |
| wav2vec2 | SILK | -0.416 | -0.84 | 0.0348 | False |

## Corpus WER (%)

| condition | wav2vec2 | whisper |
|---|---|---|
| REF | 5.16 | 2.11 |
| LP | 7.2 | 2.32 |
| OPUS | 8.69 | 2.67 |
| SILK | 6.79 | 2.39 |
| NEG_LP | 5.16 | 2.08 |
| NEG_CODEC | 5.23 | 2.18 |

## All paired quantities (micro, 95% speaker-bootstrap CI)

| model | quantity | micro |
|---|---|---|
| whisper | Bandwidth: LP − REF | +0.21 pp [-0.23, +0.67] |
| whisper | Opus residual: OPUS − LP | +0.35 pp [+0.07, +0.64] |
| whisper | SILK residual: SILK − LP | +0.07 pp [-0.21, +0.30] |
| whisper | OPUS − SILK | +0.28 pp [-0.07, +0.64] |
| whisper | Opus total: OPUS − REF | +0.55 pp [+0.04, +1.10] |
| whisper | SILK total: SILK − REF | +0.28 pp [-0.14, +0.74] |
| whisper | Control: NEG_LP − REF | -0.03 pp [-0.32, +0.25] |
| whisper | Control: NEG_CODEC − REF | +0.07 pp [-0.07, +0.25] |
| wav2vec2 | Bandwidth: LP − REF | +2.04 pp [+1.12, +3.17] |
| wav2vec2 | Opus residual: OPUS − LP | +1.49 pp [+0.74, +2.25] |
| wav2vec2 | SILK residual: SILK − LP | -0.42 pp [-0.84, +0.03] |
| wav2vec2 | OPUS − SILK | +1.91 pp [+1.09, +2.71] |
| wav2vec2 | Opus total: OPUS − REF | +3.53 pp [+2.34, +4.95] |
| wav2vec2 | SILK total: SILK − REF | +1.63 pp [+0.76, +2.67] |
| wav2vec2 | Control: NEG_LP − REF | +0.00 pp [-0.26, +0.24] |
| wav2vec2 | Control: NEG_CODEC − REF | +0.07 pp [-0.19, +0.35] |
