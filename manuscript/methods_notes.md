# Methods notes (draft 1, 2026-09-26)

Working notes for the Methods section. Every item is taken from a frozen record; the record
is named in brackets.

## 1. Provenance and pre-registration timeline (UTC, 2026-09-26)

| Time | Event | Record |
|---|---|---|
| — | Stage 1 (reproduction of the frozen prior-study pipeline, 250/250 checks) | commit `8a77f41` |
| — | Stage 2A (direct-libopus control) and Stage 2B (LP control, v1 FAIL retained, corrected Gate 5 confirmed) | commit `d70c993`, tag `paper-stage2b-confirmed` |
| 07:14:59 | Stage 3 selections sealed (calibration `f966a439…`, pilot `94fee5a6…`, confirmation `f41dcc20…`) | `selection_*.json` |
| 07:17:48 | Stage 3 specification sealed (`ac5a36a0…`) | `stage3_spec.json`, `00_FROZEN_STAGE3_SPEC.md` |
| 07:18:04 | Specification committed, before any evaluation decoding | commit `ef072e5` |
| 07:18:13–07:22:02 | Pilot decoded once (220 s) | `raw/pilot/run_log.json` |
| 07:22:16 | Pilot decision sealed: PROCEED (`fb63d2fa…`) | `pilot/pilot_decision.json` |
| 07:23:32 | Confirmation freeze sealed (`7beca216…`), with one presentation-only amendment | `confirmation_freeze.json` |
| 07:23:58 | Freeze committed | commit `a51ea54` |
| 07:24:01–08:21:40 | Confirmation decoded once (3,447 s, never resumed) | `raw/confirmation/run_log.json` |
| — | Frozen analysis and decision GO (`608c919c…`) | `stage3_decision.json`, commit `d612bdb` |

Before sealing, the calibration set (20 utterances) was used only for pipeline sanity
(decoding succeeds, determinism, throughput; REF WER only). No condition comparison was
computed on it [`calibration/calibration_report.json`]. After installing `transformers`, a
regression check re-ran the Stage 1 pipeline on 3 prior-study utterances per test subset and
reproduced predictions, WER, file sizes, LSD, retained bandwidth, delay and all 13
standardised drift layers exactly [`env_check.json`].

## 2. Data

- **Corpus.** LibriSpeech, 16 kHz read English. Evaluation uses dev-clean, dev-other,
  test-clean and test-other only: wav2vec2-base-960h was fine-tuned on all 960 h of the
  training subsets.
- **Splits.** No speaker appears in more than one split [`selection_*.json`].

  | Split | Source | Utterances | Speakers | Rule |
  |---|---|---|---|---|
  | Calibration | dev-clean | 20 | 4 | 4 speakers (seed 53051) × 5 utterances |
  | Pilot | dev-clean (36 speakers) + dev-other (33) | 138 | 69 | 2 utterances per speaker (seed 53052) |
  | Confirmation | test-clean (40 speakers, 1,190 utterances) + test-other (33, 984) | 2,174 | 73 | up to 30 per speaker (seed 53053); 16,083 s; 43,417 normalised reference words |

- **Selection-time exclusions only** (based on metadata, never on ASR output):
  - duration > 30 s (Whisper's window);
  - an empty normalised reference;
  - the Stage 2A/2B dev utterances (one per speaker);
  - for confirmation, the 1,000 utterances of the prior ELEC5305 study (500 per test subset,
    seed 5305). The confirmation *utterances* had never been decoded in this project, but
    their *speakers* are the same as the prior study's.
- **Post-decoding exclusions:** none. Every selected utterance is scored in every condition
  and model.

## 3. Conditions (paired: every utterance in every condition) [`stage3_spec.json`]

| Condition | Processing | Encoder settings (libopus 1.4, direct ctypes) |
|---|---|---|
| REF | original waveform (16-bit FLAC, exact float) | — |
| LP | frozen zero-phase low-pass (taps SHA-256 `583c66a1…`) | — |
| OPUS | Opus 8 kbps | bitrate 8000, bandwidth NB (forced), `signal=auto`, application audio, VBR unconstrained, complexity 10, 20 ms frames, no FEC/DTX, 0 % loss, lsb_depth 24, max bandwidth FB |
| SILK | SILK-NB 40 kbps | as OPUS but bitrate 40000 and **`signal=voice`** |
| NEG_LP | negative control: zero-phase low-pass flat to 7.0 kHz (taps `6740aac5…`) | — |
| NEG_CODEC | negative control: Opus 64 kbps, frozen settings (automatic bandwidth, CELT-WB) | bitrate 64000, bandwidth AUTO, `signal=auto` |

- **Packets.** 100 % of packets had the expected configuration in every confirmation
  utterance: SILK-NB for OPUS and SILK, CELT-WB for NEG_CODEC [`03_audio_manifest.csv`].
  Median measured bitrates, including Ogg overhead: 8.17, 39.79 and 70.59 kbps.
- **Relation to the prior study.** OPUS uses the prior study's encoder configuration. Its
  packets were verified byte-identical to the prior-study ffmpeg path on 40 dev-clean
  utterances in Stage 2A: automatic-bandwidth packets were identical to ffmpeg's (40/40), and
  forced-NB packets were identical to automatic-bandwidth packets (40/40). The Ogg files
  differ by 3 bytes (OpusTags). This was not re-verified on the test utterances.
- **Why SILK uses `signal=voice`.** With `signal=auto`, high-rate forced NB produced ≈2.5 %
  CELT-NB packets during Stage 2B development. This is recorded only as a comment in the
  committed Stage 2B code (`paper/run_lowpass_validation.py`, `REFERENCE_SIGNAL`); no rate range
  is recorded. OPUS − SILK therefore differs in bitrate **and** the signal-type hint, so SILK is
  a supporting reference, not a bitrate-only contrast.
- **Codec path.** The encoder output is written to Ogg Opus (RFC 7845, pre-skip = lookahead of
  312 samples at 48 kHz, end trimming by granule position). It is decoded by
  `torchaudio.load`, which uses torchcodec with FFmpeg 6.1.1's native Opus decoder, at
  48 kHz, then resampled to 16 kHz with `torchaudio.functional.resample` (defaults), exactly
  as in the prior study. Decoded length equals REF length.
- **Alignment.** There is no re-alignment before recognition (the frozen convention). Lags vs
  REF are 1–2 samples for OPUS and SILK and 0 for the others.
- **Level.** No normalisation (pre-declared). Median RMS change vs REF is −0.68 dB for OPUS
  (5th–95th percentile −2.09 to −0.34), −0.11 for SILK, −0.08 for LP, and −0.005 / −0.003 for
  NEG_LP / NEG_CODEC.
- **Full scale.** Processing is in float and nothing is clipped. Samples with |x| ≥ 1.0
  (manifest column `clip_count`): LP 136, OPUS 113, NEG_CODEC 80, SILK 75, NEG_LP 66, out of
  ≈2.57 × 10⁸ per condition. The recognisers received them unclipped.

## 4. Bandwidth control (Stage 2B) [`results_paper/lowpass_validation/`, `results_paper/lowpass_confirmation/`]

- **Imaging finding.** Opus SILK-NB output decomposes into:
  1. a bitrate-independent linear band-limiting response;
  2. a mirror image of the 3–4 kHz band folded into 4–5 kHz (coherent with the input at
     8000 − *f*, not at *f*);
  3. bitrate-dependent in-band coding distortion.

  The frozen power-based metrics count the image as "retained bandwidth" (≈4.6 kHz).
- **Definition (linear only, chosen before building the filter).** The LP reproduces
  component 1 only. The target is SILK-NB's linear transfer |H1| = |S_xy| / S_xx, pooled over
  the 40 dev-clean calibration utterances (348 s) at 40 kbps with `signal=voice` (100 %
  SILK-NB), normalised to its 0.5–2 kHz level:
  - 0 dB below the passband edge (3.0 kHz: the last point before the reference stays below
    −0.5 dB);
  - the measured response above that, made monotone;
  - a floor at −80 dB.
- **Design.** Frequency sampling (16,384-point grid), 1,023-tap type-I FIR, Kaiser β = 8,
  exact symmetry, DC gain 1. It is applied by float64 FFT convolution with the 511-sample
  delay removed, so it is zero-phase and preserves length. Three corrections in the
  measurement domain reduced the |H1| error over 3.0–4.2 kHz from 0.12 to 0.05 dB RMS
  (maximum from 0.62 to 0.16 dB).
- **Reference convergence** [`lowpass_validation/calibration_curves.csv`,
  `frozen_filter.json` metadata]. Across 3.0–4.1 kHz the reference |H1| rose by 0.24–0.83 dB
  (mean 0.46) from 32 to 40 kbps and by 0.76–1.96 dB (mean 1.22) from 24 to 40 kbps, so it had
  not converged at 40 kbps. The LP may therefore attenuate the band edge slightly more than the
  asymptotic linear chain. This would bias LP − REF slightly up and OPUS − LP slightly down,
  which is conservative for the residual.
  - *Correction (2026-09-26, manuscript drafting):* an earlier note gave "+0.27 dB from 40 to
    48 kbps; 64 kbps entirely CELT" and a "≈0.3–0.7 dB" bound. Those came from an unsealed check
    that is not in any frozen output, so they are withdrawn and not used in the manuscript.
- **Validation history.**
  - v1: FAIL on the original Gate 5, which required coherent 4–8 kHz power within 6 dB of
    Opus 8 kbps. That quantity contains bitrate-dependent coding droop, so the gate was
    inconsistent with the linear-only definition. The v1 result is retained unchanged.
  - The corrected Gate 5 (±3 dB against the linear reference, unchanged tolerance) was frozen
    (`166f5672…`) before the confirmation data existed.
  - Confirmation on 40 unseen train-clean-100 speakers (selection `0dfc0981…`): all gates
    PASS. LSD 0–3 kHz 0.031 dB; coherent bandwidth 4093.8 Hz (reference 4125.0); coherent
    4–8 kHz power −24.7 dB (reference −24.9); |H1| RMS difference 0.57 dB; filter hash
    unchanged.

## 5. Recognisers [`stage3_spec.json`]

- **Model A: Whisper large-v3.** Hugging Face `openai/whisper-large-v3`, revision
  `06f233fe06e710322aca913c1bc4249a0d71fce1`, weights SHA-256 `a8e94b85…`, transformers
  5.17.0, float16, SDPA attention, batch 16.
  - Greedy decoding (`num_beams=1`), temperature 0 with no fallback (no compression-ratio,
    log-prob or no-speech thresholds), `language="en"`, `task="transcribe"`, no timestamps,
    no prompt, no VAD. Default token suppression (88 tokens; begin-suppress 220, 50257);
    max_length 448.
  - Input: a 128-bin log-mel of each utterance, padded to 30 s.
  - Why greedy: beam 5 was measured at 2–7.5 s per utterance on the shared GPU *before* any
    evaluation decoding. Greedy output was deterministic across repeats and identical
    between batch size 1 and batched decoding.
- **Model B: wav2vec2-base-960h.** torchaudio `WAV2VEC2_ASR_BASE_960H` (checkpoint
  `488fd4f1…`), float32, greedy CTC (blank 0, repeats collapsed), no language model. This is
  the prior study's recogniser and decoder, used verbatim; no waveform normalisation.
- **Fixed for both.** No fine-tuning, no adaptation per condition. Environment: Python 3.12.3,
  torch 2.13.0 (CUDA 13.0, cuDNN 9.2), torchaudio 2.11.0, torchcodec 0.16.0, jiwer 4.0.0,
  RTX 5090 (shared with an unrelated job), default torch flags (cuDNN TF32 allowed, matmul
  TF32 off, non-deterministic cuDNN mode). Determinism was verified on the calibration set.

## 6. Normalisation and scoring [`transcript_normalization_spec.md`]

- One policy for references and all hypotheses of both models: Whisper `EnglishTextNormalizer`
  (via `WhisperTokenizer.normalize`, pinned revision; 1,740-entry spelling map, SHA-256
  `bf1c507d…`). It lower-cases, removes punctuation and fillers, expands contractions, maps
  numbers to digits and British to American spelling, and collapses whitespace.
- WER = (S + D + I) / reference words from jiwer 4.0.0 word alignment; CER from character
  alignment (secondary).
- Absolute WERs are not comparable to the prior study, which scored raw uppercase text on
  different utterances.

## 7. Statistics [`stage3_stats.py`, frozen]

- **Contrasts.** LP − REF, OPUS − LP, SILK − LP, OPUS − SILK, OPUS − REF, SILK − REF,
  NEG_LP − REF, NEG_CODEC − REF.
- **Micro (primary):** the difference of corpus WERs from total edit counts.
  **Macro (secondary):** the mean of per-utterance WER differences.
  Also recorded: CER and the S/D/I composition (per 100 reference words).
- **Bandwidth share:** (LP − REF) / (codec − REF), over replicates with a positive denominator.
- **Bootstrap.** Paired percentile bootstrap resampling speakers with replacement,
  stratified by subset. All conditions and both models of an utterance are kept together.
  10,000 replicates, seed 5305, 95 % intervals. Scopes: pooled (primary) and per subset
  (secondary, no multiplicity correction).
- **Pilot rule:** PROCEED if any (model, codec) residual CI lower bound > 0.
- **Confirmation rule:**
  - KILL if all four residual CIs include 0;
  - GO if, for some codec, the CI lower bound > 0 in both models, the estimate ≥ 0.5 pp in
    both, and the pilot estimate > 0 in both;
  - CONDITIONAL GO if robust in both but short of GO;
  - HOLD otherwise;
  - GO / CONDITIONAL GO are capped at HOLD if a negative control's CI excludes 0 **and**
    |estimate| > 0.5 pp.
- **Conditional analyses**, run only if a residual survives: error types, and exploratory
  Spearman correlations (36; speaker bootstrap B = 2,000; no multiplicity correction).

## 8. Signal descriptors (descriptive only)

- **Frozen definitions:**
  - STFT with a 512-point FFT, 400-sample Hann window and 160-sample hop;
  - log spectra clipped 80 dB below the reference peak;
  - LSD = RMS over frequency, then mean over frames;
  - band-limited LSD over 0–3, 0–4 and 4–8 kHz;
  - retained bandwidth: the highest frequency with long-term power within 20 dB of the
    reference;
  - 4–8 kHz power change;
  - alignment by FFT normalised cross-correlation (±4,000 samples).
- **Pooled cross-spectral measures:** |H1| relative to its 0.5–2 kHz level, coherence,
  mirror coherence (output at *f* vs input at 8000 − *f*), coherent bandwidth (−20 dB
  point), and coherent / total 4–8 kHz power.
- **Codec vs LP:** band LSD, coherence over 0–3.5 kHz, and log-envelope decorrelation over
  4 bands in 0–4 kHz.
- **Clean-speech features** (exploratory): 4–8 kHz energy fraction, fricative-frame fraction,
  voiced-frame fraction, spectral flatness, spectral flux.
- **Not computed:** STOI and PESQ.

## 9. Amendments and deviations (all recorded)

- **After the pilot:** fig05 changed from offset text labels to marker shape plus legend.
  Presentation only; recorded in the confirmation freeze.
- **After the analysis:**
  - `raw/confirmation/progress.jsonl`, a resumable checkpoint not covered by any seal, was
    removed from Git tracking; only the latest commit was amended.
  - Interpretation wording was corrected in `01b_interpretation_note_2026-09-26.md`; frozen
    outputs are unchanged.
- **Before any evaluation decoding:** greedy rather than beam decoding for Whisper (compute
  on a shared GPU).
