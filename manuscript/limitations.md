# Limitations (draft 2, 2026-09-27)

Ordered roughly by how much each one qualifies the primary claim (OPUS − LP > 0 in both
recognisers). Numbers are from `results_paper/stage3_asr/`; the follow-up analyses (TASLP
upgrade, draft 2) are from `results_paper/taslp_upgrade/` (level/ = addition A, sweep/ =
addition B).

## A. What the OPUS − LP contrast contains

1. **The residual is a bundle, not a single mechanism.** LP reproduces only SILK-NB's linear
   band-limiting. OPUS − LP therefore contains:
   - low-rate in-band coding distortion;
   - the 4–5 kHz mirror image (total 4–8 kHz power −16.7 dB vs −24.5 dB for LP);
   - a small level difference (median RMS −0.68 dB vs REF for OPUS and −0.08 dB for LP; no
     level normalisation, pre-declared);
   - a 1–2 sample lag (no re-alignment, the frozen convention);
   - the codec decode path (48 kHz FFmpeg decode, then resampling).

   High-rate SILK-NB shares the image, the lag and the decode path, and shows no pooled
   residual; NEG_CODEC ≈ REF. Both argue against those components explaining the residual,
   but neither isolates in-band coding distortion. **Level (draft 2):** addition A, a
   post-confirmation sensitivity analysis on the same utterances (not a second confirmatory
   test), matched the broadband RMS level of OPUS to LP; the residual remained (W +0.70 pp
   [+0.47, +0.95], V +2.09 pp [+1.71, +2.57]; effect of level matching W +0.012 [−0.007,
   +0.032], V +0.018 [−0.028, +0.062]; GO in both). It did not equalise level per frequency
   band.
2. **Mechanism not established.** The signal evidence (in-band LSD 6.1 vs 1.4 dB, coherence
   0.62 vs 0.99) is *consistent with* in-band coding distortion. No condition manipulated
   in-band distortion while holding everything else fixed. Utterance-level correlations were
   weak (|ρ| ≤ 0.09; 4 of 36 with CIs excluding 0; uncorrected). **Rate (draft 2):** in
   addition B the residual fell with bitrate (slope W −0.206 [−0.267, −0.146], V −0.854
   [−1.074, −0.657] pp per doubling; GO in both), but in-band distortion, level and image
   fidelity all changed with the rate, so the sweep supports but does not isolate the in-band
   interpretation.
3. **The LP reference is not fully converged.** The SILK-NB linear response was measured at
   40 kbps. Across 3.0–4.1 kHz it still rose by 0.24–0.83 dB (mean 0.46) between 32 and
   40 kbps (frozen calibration curves). The LP may therefore attenuate the band edge slightly
   more than the asymptotic linear chain, which would slightly inflate LP − REF and deflate
   OPUS − LP (conservative for the primary claim). An earlier "+0.27 dB at 48 kbps" figure came
   from an unsealed check and is withdrawn.
4. **The LP control was validated with a corrected gate.** Stage 2B v1 FAILED an internally
   inconsistent Gate 5. The corrected gate was frozen before the confirmation audio existed
   and passed on unseen speakers; the v1 result is retained. Reviewers should see both.

## B. The high-rate SILK reference

5. **Not a bitrate-only contrast.** SILK uses `signal=voice`, OPUS `signal=auto` (both
   produced 100 % SILK-NB packets). OPUS − SILK mixes bitrate with the signal-type hint and
   any encoder decisions it conditions. **Draft 2:** addition B fixes the hint and varies the
   rate (8, 12, 16, 24, 40 kbps), but on 1,665 other utterances of the same speakers: a
   fresh-utterance, not fresh-speaker, holdout, without REF recognition (no bandwidth component
   or share for its utterances). At 8 kbps its `signal=voice` files were byte-identical to the
   OPUS settings' files for all 1,665 utterances.
6. **"No residual" is pooled and is not an equivalence result.** No equivalence margin was
   pre-declared. The pooled CIs lie between −0.20 and +0.08 pp. Secondary: for wav2vec2 on
   test-other, SILK − LP = −0.24 pp [−0.50, −0.005]. If real, the image could slightly help
   that recogniser, in which case OPUS's image might partly offset its coding damage.

## C. Recognisers and decoding

7. **Two recognisers.** Whisper large-v3 (attention encoder-decoder) and wav2vec2-base-960h
   (CTC, no language model). No transducer, Conformer-CTC or language-model-rescored system
   was tested; results may not generalise.
8. **Decoding choices.**
   - Whisper used greedy decoding in float16 (beam 5 was too slow on a shared GPU; decided
     before any evaluation decoding), not the common beam-5 configuration.
   - wav2vec2 used greedy CTC without a language model, the prior study's configuration.
   - Absolute WERs, and possibly effect sizes, could change with beam search or a language
     model.
9. **Training-data exposure.**
   - wav2vec2-base-960h was fine-tuned on LibriSpeech's 960 h training subsets. The
     evaluation is in-domain, but the dev and test sets were not used for training.
   - Whisper's training data are undisclosed, and exposure to LibriSpeech test audio or text
     cannot be ruled out.
10. **Recogniser comparisons depend on the scale.** In absolute points, wav2vec2's residual is
    ≈3× Whisper's; relative to each recogniser's baseline the residuals are similar (+26 % vs
    +31 %). Relative effects are post hoc, with no CIs.

## D. Data and generalisation

11. **One corpus, one condition class.** LibriSpeech read English audiobooks at 16 kHz,
    utterances ≤ 30 s. Conversational, telephone, noisy, far-field, multilingual and
    real-network (packet loss, jitter) conditions were not tested.
12. **One codec implementation.** libopus 1.4 encoder, decoded by FFmpeg 6.1.1's native
    Opus decoder and resampled by torchaudio. The image level depends on the decoder's
    resampler; other decoders (e.g. libopus's own) could differ.
13. **Speakers.** The confirmation set has 73 speakers, which limits bootstrap resolution.
    The confirmation *utterances* are new, but the *speakers* are the same test speakers
    whose other utterances formed the prior study, where the Opus 8 kbps degradation was
    first observed.
14. **Scoring differs from the prior study.** The Whisper English normaliser is applied to
    all references and hypotheses, so absolute WERs are not comparable with the prior study's
    raw uppercase scoring.

## E. Statistics and reporting

15. **Scopes.** Per-subset results are secondary and uncorrected for multiplicity.
    Bandwidth shares are pre-declared secondary ratios. Relative percentages are post hoc.
16. **Resolution limit.** The NEG_LP control's CIs exclude 0 in opposite directions
    (−0.08 / +0.10 pp) while staying within the ±0.5 pp margin, so effects of order 0.1 pp
    should not be interpreted.
17. **Pre-registration is internal.** It rests on sealed files, hashes and local commits
    (spec committed at 07:18:04 UTC before the pilot started at 07:18:13), not on a public
    registry. The analyst had seen the prior-study and Stage 2 results, but no Stage 3 ASR
    output, when writing the specification. One presentation-only amendment (fig05) was made
    after the pilot.
18. **Descriptive signal measures only.** STOI and PESQ were not computed. The column
    `clip_count` counts samples at or above full scale (at most 136 out of ≈2.6 × 10⁸ per
    condition), not clipping events; the recognisers received unclipped float input.

## F. Out of scope for this paper

19. **The interaction of bandwidth and coding distortion** (the Stage 2A 12k/8k × WB/NB cells
    were validated but not decoded by ASR), **and propagation through the ASR encoder** (no
    representation analysis on the Stage 3 conditions). Both belonged to the project's
    original question and are not evidenced here.
20. **Perceptual claims.** Human intelligibility and quality were not measured.
