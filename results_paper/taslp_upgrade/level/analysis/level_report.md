# OPUS level-matched sensitivity: result

Post-confirmation sensitivity analysis on the Stage 3 confirmation set. Not a second confirmatory test; the Stage 3 estimates and decision are unchanged.

**Outcome: GO**

| Quantity (pp) | whisper | wav2vec2 |
|---|---|---|
| L_level_matched_minus_lp | +0.70 [+0.47, +0.95] | +2.09 [+1.71, +2.57] |
| K_level_matched_minus_opus | +0.01 [-0.01, +0.03] | +0.02 [-0.03, +0.06] |
| T_opus_minus_lp | +0.69 [+0.46, +0.94] | +2.07 [+1.68, +2.57] |

Per-recogniser outcomes: whisper: GO, wav2vec2: GO
Hypotheses changed by level matching: {'whisper': 42, 'wav2vec2': 188}
Reproduction of Stage 3 hypotheses: [{'model': 'wav2vec2', 'condition': 'LP', 'n': 2174, 'identical': 2174, 'differing': 0}, {'model': 'wav2vec2', 'condition': 'OPUS', 'n': 2174, 'identical': 2174, 'differing': 0}, {'model': 'whisper', 'condition': 'LP', 'n': 2174, 'identical': 2172, 'differing': 2}, {'model': 'whisper', 'condition': 'OPUS', 'n': 2174, 'identical': 2173, 'differing': 1}]
