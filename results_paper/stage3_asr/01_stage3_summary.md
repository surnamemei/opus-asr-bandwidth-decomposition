# Stage 3 Decision

**GO** — OPUS: residual CI > 0 in both architectures, estimate >= 0.5 pp in both, same direction as the pilot.

Result types: TYPE 2 (OPUS): WER_REF <= WER_LP < WER_OPUS; TYPE 3: OPUS and SILK residuals differ (same direction in both models). Decision record `stage3_decision.json` SHA-256 `608c919c33e135bb7ca236e2e07e1c9b1b567285a5b1d9d8caabedeb08cb3a41`.

# Frozen Design

- Spec `00_FROZEN_STAGE3_SPEC.md` / `stage3_spec.json` SHA-256 `ac5a36a01f50e7643cc73bbbc2f75ce44fe34b0730ec828082084ba1643b5219` (created 2026-09-26T07:17:48.839927+00:00, before any pilot or confirmation decoding).
- Confirmation freeze SHA-256 `7beca2163329d259ccf169293f3173115ec8da474e5c372e46f15b93dfaaf39b` (created 2026-09-26T07:23:32.613281+00:00); code changed since spec: ['paper/stage3_report.py'].
- Conditions: REF, LP (frozen filter `583c66a169d31e27…`), OPUS (Opus 8 kbps, SILK-NB), SILK (SILK-NB 40 kbps); controls NEG_LP (flat to 7 kHz) and NEG_CODEC (Opus 64 kbps).
- Sets (speaker-disjoint): calibration 20 utt / 4 spk (dev-clean); pilot 138 / 69 (dev-clean + dev-other); confirmation 2174 / 73 (test-clean + test-other, never decoded before in this project).
- Provenance: Stage 2 tag `paper-stage2b-confirmed` (commit `d70c99384814`), revised-spec `166f5672263373ec…`, Stage 2B selection `0dfc09813d018c3f…`.

# ASR Systems

- Model A: Whisper large-v3 (`06f233fe06e7`), float16, greedy, temperature 0 without fallback, English, no prompt, no VAD.
- Model B: wav2vec2-base-960h (torchaudio), greedy CTC, frozen ELEC5305 decoder.
- Same Whisper EnglishTextNormalizer for references and all hypotheses.

# Pilot

Pilot decision: PROCEED_TO_CONFIRMATION (at least one codec residual has a 95% CI lower bound above 0; SHA-256 `fb63d2fa95e5998e…`). Pilot vs confirmation residuals (micro, 95% CI):

| model | codec | pilot residual | confirmation residual |
|---|---|---|---|
| Whisper large-v3 | OPUS | +0.35 pp [+0.07, +0.64] | +0.69 pp [+0.46, +0.94] |
| Whisper large-v3 | SILK | +0.07 pp [-0.21, +0.30] | +0.02 pp [-0.04, +0.08] |
| wav2vec2-base-960h | OPUS | +1.49 pp [+0.74, +2.25] | +2.07 pp [+1.68, +2.57] |
| wav2vec2-base-960h | SILK | -0.42 pp [-0.84, +0.03] | -0.09 pp [-0.20, +0.02] |

# Confirmation

Corpus WER (%) on the confirmation set, 95% speaker-bootstrap CI:

| condition | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| REF | 2.50 [2.19, 2.84] | 5.36 [4.73, 6.08] |
| LP | 2.64 [2.32, 2.98] | 6.76 [5.89, 7.74] |
| OPUS | 3.32 [2.86, 3.82] | 8.84 [7.72, 10.17] |
| SILK | 2.66 [2.34, 3.01] | 6.68 [5.85, 7.60] |
| NEG_LP | 2.42 [2.11, 2.76] | 5.46 [4.80, 6.22] |
| NEG_CODEC | 2.50 [2.19, 2.84] | 5.36 [4.71, 6.10] |

# Bandwidth Penalty

| quantity | Whisper large-v3 micro | Whisper large-v3 macro | wav2vec2-base-960h micro | wav2vec2-base-960h macro |
|---|---|---|---|---|
| Bandwidth: LP − REF | +0.14 pp [+0.04, +0.25] | +0.35 pp [+0.17, +0.54] | +1.40 pp [+0.99, +1.92] | +1.90 pp [+1.39, +2.44] |
| Opus total: OPUS − REF | +0.83 pp [+0.57, +1.10] | +1.35 pp [+0.93, +1.78] | +3.48 pp [+2.73, +4.45] | +4.50 pp [+3.65, +5.47] |
| SILK total: SILK − REF | +0.16 pp [+0.07, +0.26] | +0.33 pp [+0.19, +0.50] | +1.32 pp [+0.94, +1.78] | +1.77 pp [+1.29, +2.29] |

- Whisper large-v3 bw share of opus total: 0.17 [0.05, 0.29] (10000 valid replicates)
- Whisper large-v3 bw share of silk total: 0.88 [0.39, 1.36] (9995 valid replicates)
- wav2vec2-base-960h bw share of opus total: 0.40 [0.35, 0.45] (10000 valid replicates)
- wav2vec2-base-960h bw share of silk total: 1.07 [0.98, 1.15] (10000 valid replicates)

# Codec-Specific Residual

| quantity | Whisper large-v3 micro | Whisper large-v3 macro | wav2vec2-base-960h micro | wav2vec2-base-960h macro |
|---|---|---|---|---|
| Opus residual: OPUS − LP | +0.69 pp [+0.46, +0.94] | +1.00 pp [+0.64, +1.39] | +2.07 pp [+1.68, +2.57] | +2.61 pp [+2.12, +3.13] |
| SILK residual: SILK − LP | +0.02 pp [-0.04, +0.08] | -0.02 pp [-0.15, +0.11] | -0.09 pp [-0.20, +0.02] | -0.13 pp [-0.30, +0.05] |
| OPUS − SILK | +0.67 pp [+0.46, +0.89] | +1.02 pp [+0.65, +1.40] | +2.16 pp [+1.73, +2.71] | +2.73 pp [+2.18, +3.33] |

Per subset (secondary):

| subset | quantity | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|---|
| test-clean | Bandwidth: LP − REF | -0.03 pp [-0.13, +0.07] | +0.41 pp [+0.20, +0.64] |
| test-clean | Opus residual: OPUS − LP | +0.29 pp [+0.15, +0.46] | +0.94 pp [+0.72, +1.18] |
| test-clean | SILK residual: SILK − LP | -0.00 pp [-0.06, +0.05] | +0.02 pp [-0.06, +0.10] |
| test-other | Bandwidth: LP − REF | +0.37 pp [+0.16, +0.59] | +2.75 pp [+1.83, +3.92] |
| test-other | Opus residual: OPUS − LP | +1.22 pp [+0.75, +1.77] | +3.60 pp [+2.78, +4.68] |
| test-other | SILK residual: SILK − LP | +0.05 pp [-0.08, +0.18] | -0.24 pp [-0.50, -0.01] |

# Cross-ASR Consistency

| quantity | Whisper | wav2vec2 | same sign | both CIs exclude 0 |
|---|---|---|---|---|
| Bandwidth: LP − REF | +0.14 pp [+0.04, +0.25] | +1.40 pp [+0.99, +1.92] | True | True |
| Opus residual: OPUS − LP | +0.69 pp [+0.46, +0.94] | +2.07 pp [+1.68, +2.57] | True | True |
| SILK residual: SILK − LP | +0.02 pp [-0.04, +0.08] | -0.09 pp [-0.20, +0.02] | False | False |
| OPUS − SILK | +0.67 pp [+0.46, +0.89] | +2.16 pp [+1.73, +2.71] | True | True |

Residual ranking by estimate: Whisper OPUS > SILK; wav2vec2 OPUS > SILK.

# Uncertainty

Paired percentile bootstrap over speakers (stratified by subset), 10000 replicates, seed 5305; confirmation has 73 speakers. Micro = corpus WER from total edit counts (primary); macro = mean per-utterance difference (secondary). Negative controls:

| model | control | estimate_pp | ci_lower_pp | ci_upper_pp | flagged |
|---|---|---|---|---|---|
| whisper | neg_lp_minus_ref | -0.076 | -0.151 | -0.0042 | False |
| whisper | neg_codec_minus_ref | 0.0023 | -0.0457 | 0.0491 | False |
| wav2vec2 | neg_lp_minus_ref | 0.101 | 0.0204 | 0.19 | False |
| wav2vec2 | neg_codec_minus_ref | 0.0023 | -0.057 | 0.0651 | False |

# Error Types

- Whisper large-v3, Opus residual: OPUS − LP: S +0.51 pp [+0.34, +0.70]; D +0.10 pp [+0.05, +0.16]; I +0.08 pp [+0.03, +0.13] (per 100 reference words)
- Whisper large-v3, SILK residual: SILK − LP: S +0.03 pp [-0.02, +0.09]; D -0.01 pp [-0.03, +0.01]; I -0.00 pp [-0.02, +0.02] (per 100 reference words)
- wav2vec2-base-960h, Opus residual: OPUS − LP: S +1.79 pp [+1.46, +2.21]; D +0.13 pp [+0.05, +0.22]; I +0.15 pp [+0.09, +0.20] (per 100 reference words)
- wav2vec2-base-960h, SILK residual: SILK − LP: S -0.08 pp [-0.18, +0.02]; D -0.03 pp [-0.06, +0.01]; I +0.02 pp [-0.01, +0.04] (per 100 reference words)

# Signal-Level Interpretation

- In-band LSD 0–3 kHz vs REF (median): LP 0.03 dB, OPUS 6.14 dB, SILK 1.37 dB, NEG_LP 0.00 dB, NEG_CODEC 1.29 dB.
- Codec vs LP (median): OPUS in-band LSD 0–3 kHz 6.14 dB, SILK 1.37 dB; mean coherence with LP 0–3.5 kHz OPUS 0.623, SILK 0.993; envelope decorrelation OPUS 0.009, SILK 0.000.
- Pooled coherent bandwidth vs REF: LP 4094 Hz, OPUS 4000 Hz, SILK 4094 Hz; 4–5 kHz image (mirror coherence) LP 0.000, OPUS 0.227, SILK 0.970.
- Total 4–8 kHz power vs REF (pooled): LP -24.5 dB, OPUS -16.7 dB, SILK -15.8 dB.
- STOI/PESQ: not computed (packages not installed; descriptive only per the brief).
- Exploratory (Step 12, not confirmatory) residual correlations whose bootstrap CI excludes 0: OPUS/wav2vec2 vs_lp_coherence_0_3500 rho=-0.09 [-0.16, -0.02]; SILK/whisper vs_lp_lsd_0_4k_db rho=+0.06 [+0.01, +0.11]; SILK/whisper vs_lp_lsd_0_3k_db rho=+0.06 [+0.01, +0.10]; SILK/whisper vs_lp_coherence_0_3500 rho=-0.05 [-0.09, -0.00]

# What Is Supported

- Bandwidth removal alone (frozen LP) increases WER in both recognisers: Whisper large-v3 +0.14 pp [+0.04, +0.25]; wav2vec2-base-960h +1.40 pp [+0.99, +1.92].
- After bandwidth control, OPUS shows a codec-specific residual ASR penalty in both recognisers (Whisper large-v3 +0.69 pp [+0.46, +0.94]; wav2vec2-base-960h +2.07 pp [+1.68, +2.57]).

# What Is NOT Supported

- A SILK-specific residual beyond bandwidth (Whisper large-v3 +0.02 pp [-0.04, +0.08]; wav2vec2-base-960h -0.09 pp [-0.20, +0.02]; CIs include 0 or are negative).
- Any causal mechanism for the residual (Step 12 correlations are exploratory).
- Universality across ASR systems (two recognisers were tested).
- Human intelligibility or perceived quality equivalence of any condition.
- Codec quality rankings, or novelty claims about codec effects on ASR.
- Generalisation beyond LibriSpeech read English at 16 kHz.

# Next Step

Mechanism analysis (Step 12 follow-up, pre-registered): separate the codec residual into the deterministic 4–5 kHz image (present in OPUS and SILK, absent from LP) and in-band coding distortion, e.g. with an LP + synthetic-image control; test phonetic-class error concentration on a fresh held-out set.
