# Central Claim

**Setting.**

- Opus at 8 kbit/s: libopus 1.4, forced SILK narrowband, `application=audio`, FFmpeg 6.1.1
  decoding.
- Two pretrained recognisers used without adaptation: Whisper large-v3 and wav2vec2-base-960h.
- 2,174 LibriSpeech test utterances from 73 speakers.

**Claim.**

- A validated linear control that reproduces SILK narrowband's (high-rate) linear band
  limitation accounts for a minority of the total WER penalty: bandwidth component +0.14 and
  +1.40 pp.
- A codec-specific residual of +0.69 and +2.07 pp remains beyond the control. It is larger than
  the bandwidth component in both recognisers.
- Within SILK narrowband, the residual falls with coding rate and is not detectable at
  24–40 kbit/s.
- The decomposition is sequential (REF → LP → OPUS) and prospectively specified. Stage 3 remains
  its primary, frozen record.

# What Survived

Everything below holds for both recognisers.

- **Positive residual, larger than the bandwidth component:**
  - under corpus, per-utterance, equal-speaker and character weighting (C1: METRIC_ROBUST);
  - in both test subsets;
  - in the pilot.
- **An inclusive best-linear definition of linear loss** (A1: ROBUST_RESIDUAL).
  - The linear component is a per-utterance OPD/BSS Eval projection of the actual 8 kbit/s
    output. It includes the chain's own lower gain (−2.2 dB), in-band tilt, roll-off, phase and
    delay.
  - Beyond it, +0.74 [+0.51, +1.00] and +2.32 [+1.85, +2.97] pp remain.
- **RMS level matching** (Addition A): +0.70 and +2.09 pp remain.
- **Bitrate** (Addition B, fresh utterances): the residual declines with rate.
- **The total penalty** persists:
  - under the libopus reference decoder (R4): +0.72 and +3.56 pp;
  - under the VoIP application mode (B1): +0.70 and +3.44 pp.
- **Frozen records.** Every sealed record verifies (`verify_frozen.py`: 69 self-sealed records
  and 9 output manifests, PASS). That is the 52 records and 7 manifests of the baseline plus the
  new A1/B1/C1 records. No sealed file was edited.

# What Changed

- **Linear loss.**
  - The 8 kbit/s chain's own linear response is lossier than the control: about 2 dB lower gain,
    and a further −7 dB at 3.5 kHz against −2 dB for the control.
  - Reproducing it per utterance did not raise WER above the control: Whisper −0.06 pp
    [−0.13, +0.01]; wav2vec2 −0.25 pp [−0.47, −0.04].
  - The residual therefore grows slightly under the inclusive definition.
- **Shares depend on the definition of linear loss.** Linear share 0.10 (Whisper) and 0.33
  (wav2vec2) under A1, against the sequential 0.17 and 0.40.
- **The Whisper share is RATIO_UNSTABLE** (C1). It is 0.17 under corpus WER and 0.28 under CER,
  with a corpus-WER interval of [0.05, 0.29].
- **Two post hoc cross-recogniser statements are not metric-robust.**
  - "About ten times" the bandwidth component: 4.9–10.0 across weightings.
  - "Similar relative residual": holds under WER, not under CER (30.3 % vs 45.6 %).
- **Whisper's total penalty moves by about 0.1 pp with implementation or configuration details.**
  - Libopus decoding: −0.11 [−0.17, −0.04].
  - VOIP application: −0.12 [−0.25, 0.00], upper bound exactly zero; not established.
  - wav2vec2's total does not move detectably under either.
- **Error types (C1).** For wav2vec2, deletions are larger in the bandwidth component than in the
  residual. The ordering is a property of the substitution-dominated totals.

# Hidden Assumptions Remaining

- **What "bandwidth component" means.** It means the effect of SILK narrowband's high-rate
  (40 kbit/s) linear band-limiting response. It does not mean all linear loss of the 8 kbit/s
  chain; A1 bounds the consequence.
- **Sequential path.** The decomposition follows REF → LP → OPUS, so any bandwidth × coding
  interaction is inside the residual. No factorial design was run; R3 is not factorial.
- **Linear attribution.** One time-invariant filter per utterance, over ±16 ms. Frame-level,
  time-varying linear changes (SILK's adaptive spectral shaping) count as residual by
  construction.
- **Reference audio.** REF is LibriVox-derived and MP3-sourced, not pristine speech.
- **Decoding.** Greedy decoding without a language model.
- **Cross-run batch effects.** Whisper's float16 batch-composition effect (3/4,348 hypotheses) is
  contained, not separated, in the cross-run comparisons (A1, B1, R4).
- **Inference unit.** Paired speaker-cluster bootstrap on 73 test speakers. The Addition B and R3
  holdouts reuse those speakers.

# Fair-Matching Risks

- **Control fitted to an unconverged reference.** LP was fitted to a 40 kbit/s reference that
  still rose by 0.24–0.83 dB near the band edge between 32 and 40 kbit/s. This biases the
  bandwidth component slightly up and the residual slightly down, which is conservative for the
  residual claim.
- **What LP lacks.** LP has no mirror image, no level drop and no 1–2 sample lag.
  - Addition A covers the level: level matching changed WER by +0.01 and +0.02 pp.
  - A1 covers gain, tilt, roll-off, phase and delay.
  - The image stays on the residual side under both definitions. It is argued against, but not
    excluded, by SILK40, which has image power without a residual.
- **LIN8 is not a pure loss model.** It is an utterance-level attribution, not a deployable
  control. A least-squares projection can act as a mild long-term spectral weighting, so LIN8's
  slightly lower WER than LP (wav2vec2) is not interpreted.
- **The decoder-matched control failed.** It failed held-out validation (R1 STOPPED), so no
  decoder-matched decomposition exists.

# Configuration Dependence

| Configuration | Effect | Source |
|---|---|---|
| Decoder (total penalty only) | Persists. Whisper −0.11 pp under libopus; wav2vec2 no clear difference. The decomposition is defined for the FFmpeg chain. | R4 |
| Application mode (total penalty only) | Persists. No clear difference in either recogniser (Whisper −0.12 [−0.25, 0.00]; wav2vec2 −0.03 [−0.23, +0.15]). No equivalence claim. | B1 |
| Coded bandwidth at a fixed 8 kbit/s | Forced wideband better for wav2vec2 (−0.98 pp); no clear difference for Whisper. A practical counterfactual, not factorial. | R3 |
| Signal hint at 8 kbit/s | voice and auto give byte-identical files. | Addition B |
| Bitrate | The residual vanishes at 24–40 kbit/s. | Addition B |

Untested: other libopus versions (the NB/WB threshold has moved), FEC, DTX, packet loss, other
codecs.

# Metric Dependence

C1 recomputes every contrast inside the frozen bootstrap under four weightings, with no new ASR.

| Statement | Class |
|---|---|
| R > 0, both recognisers | METRIC_ROBUST |
| R > B, both recognisers | METRIC_ROBUST |
| Whisper B > 0 | SUBSET_DEPENDENT (not detectable on test-clean) |
| wav2vec2 B > 0 | METRIC_ROBUST |
| Whisper share | RATIO_UNSTABLE (0.17–0.28) |
| wav2vec2 share | METRIC_ROBUST (0.35–0.42) |

- No pooled replicate had a non-positive denominator.
- Disclosed secondary disagreements: R − B is unresolved for Whisper on test-clean under CER and
  for wav2vec2 on test-other under mean per-utterance WER.
- Conclusion: the raw pp contrasts and their ordering carry the claim; the ratios do not.

# Evaluation-Pipeline Dependence

- One normaliser: the Whisper EnglishTextNormalizer, scored with jiwer.
- Greedy decoding.
- The FFmpeg decoder and the torchaudio resampler for the decomposition. The decoder affects
  Whisper's total (R4).
- A1 execution note: single-threaded BLAS changed rare LIN8 samples in the last bit only. The
  recognised audio equals the audio that passed the checks.
- Cross-run Whisper batch effects are included in A1, B1 and R4.

# Mechanism / Organizing Variable

- Exploratory only (`ORGANISING_HYPOTHESIS.md`). The candidate is an allocation between spectral
  coverage and *coherent* in-band fidelity.
- **Within SILK narrowband.** The residual tracks in-band coherence and LSD across bitrate at
  constant coverage.
- **At a fixed 8 kbit/s.** Forced wideband trades in-band coherence (0.623 → 0.559) for coverage.
  The net effect depends on the recogniser's coverage sensitivity: it helps wav2vec2 but not
  Whisper.
- **A1** weakens purely spectral-magnitude fidelity measures: a large linear spectral change had no
  WER cost. It keeps coherence, the incoherent fraction, as the candidate.
- **B1** is below the descriptor's resolution: coherence fell by 0.01 and WER did not rise. For
  Whisper the direction is opposite to a coherence-only prediction.
- **Status.** The mechanism is not established. The hypothesis organises conditions, not
  utterances (per-utterance |ρ| ≤ 0.09).

# Generalization Limits

- One read-speech corpus (LibriSpeech, MP3-sourced) and 73 test speakers. The fresh-utterance
  holdouts reuse those speakers.
- Two recognisers: one encoder–decoder transformer and one CTC SSL model.
- One encoder implementation, and one decoder for the decomposition.
- **D1 was not run.**
  - No different-family recogniser or non-LibriSpeech corpus was reproducibly available.
  - The cheap pair was Parakeet RNN-T on FLEURS. It needs `librosa`, which would change the frozen
    environment, and FLEURS has no speaker IDs.
  - See `D1_NOT_RUN.md`.
- Conversational, telephone-sourced, noisy, far-field, multilingual and packet-loss conditions are
  untested.

# Top 3 Reviewer Attacks After This Pass

1. **"LibriSpeech and two recognisers only."** The residual-over-bandwidth ordering is shown for
   read audiobooks and two pretrained models. It may not hold for Conformer or transducer
   recognisers trained on telephone-band data, or for conversational speech. D1 was not run.
2. **"What does the 'bandwidth component' measure, and is the decomposition meaningful?"**
   - It is the high-rate narrowband linear response, removed sequentially.
   - The shares are path-, definition- and weighting-dependent.
   - Whisper's bandwidth component is tiny and appears only on test-other.
   - There is no factorial interaction estimate.
   - A1 answers the "missed linear loss" version of this attack. A reviewer may still ask for a
     time-varying linear attribution or a factorial design.
3. **"The residual is an unexplained bundle, tied to one implementation."**
   - No condition isolates in-band coding distortion.
   - The decomposition exists only for the FFmpeg decoder chain, because the decoder-matched
     control failed validation.
   - Whisper's total moves by about 0.1 pp with the decoder or the application mode.
   - Deployment conditions (packet loss, FEC, other codec versions) are untested.

# Claims That Must Be Weakened

- **Exact shares.** 17 % (Whisper) and 40 % (wav2vec2) go to "a minority of the penalty". The
  exact shares are path-, definition- (A1) and weighting-dependent (C1). The Whisper share is not
  a stable quantity.
- **"About ten times" the bandwidth component** becomes "five to ten times, depending on the error
  weighting".
- **"The residual is similar relative to each baseline"** becomes "under WER; not under CER".
- **Scope.** No statement may imply that the decomposition holds for other decoders, other
  application settings or generic WebRTC deployments. The total penalty was checked under the
  libopus decoder and the VOIP application; the decomposition was not.
- **Error types.** "The residual exceeds the bandwidth component" holds for the error totals and
  substitutions, not for wav2vec2 deletions.

# Claims That Became Stronger

- The residual is not linear loss that the control leaves out (A1, pre-specified,
  literature-grounded). It is at least as large under the inclusive best-linear attribution.
- The ordering of the residual over the bandwidth component does not depend on the error
  weighting (C1).
- The total 8 kbit/s penalty is not an artefact of the decoder implementation (R4) or of the
  `audio` application mode (B1). It persists in both recognisers, with sign and approximate size
  unchanged.

# Strongest Surviving Contribution

A prospectively specified, validated-control decomposition of the 8 kbit/s Opus (SILK narrowband)
ASR penalty for two pretrained recognisers. It shows that the degradation beyond linear band
limitation is the larger component, and that it is:

- robust to an inclusive best-linear attribution of the actual codec output, to level matching
  and to error weighting;
- declining with coding rate;
- set in a total penalty that persists across decoder and application mode.

The contribution is the measured, bounded answer to "how much is bandwidth?", delivered with a
transparent record of failed controls (R1 and R2 STOPPED).

# Submission Recommendation

**SUBMIT TASLP WITH NARROWER CLAIMS**

- **The central story got stronger.** Every test of this pass that could have overturned it (A1,
  B1, C1) left it standing.
- **Several secondary claims must be narrowed.** The share values, the cross-recogniser ratios
  and the scope of configuration statements; the manuscript patch of this pass implements these.
- **Why not "one more specific test".** No single remaining test could overturn the central story
  *as scoped* (libopus 1.4 / FFmpeg / LibriSpeech / two recognisers). A different-family
  recogniser on another corpus (D1) could narrow the generalisation, but not falsify the measured
  result. The generalisation limit is stated as future work.
