<!--
Reviewer risk map for the TASLP submission (internal; not for submission). It covers the six most
likely reviewer concerns, numbered 1-6 identically under each of the four headings:

1. definition of bandwidth / linear loss
2. decoder dependence
3. application mode
4. generalisation
5. mechanism not identified
6. exact share / metric dependence

Numbers are those of the built manuscript (taslp_submission.md, taslp_supplement.md), which
check_numbers.py verifies against the sealed records. "Main" means the main paper and "S" the
supplement. No new experiment is proposed beyond what a reviewer would have to request.
-->

# Reviewer Concern

1. **Definition of bandwidth / linear loss.** The control reproduces only SILK narrowband's
   high-rate linear response. The 8 kbit/s chain has additional linear attenuation (lower gain,
   steeper in-band roll-off), so the "codec-specific residual" might be linear loss that a too
   narrow definition of bandwidth leaves out.
2. **Decoder dependence.** FFmpeg upsamples SILK output with its own interpolator, not the libopus
   reference decoder's. The penalty, or its decomposition, might be an artefact of one decoder
   implementation.
3. **Application mode.** The encoder used `application=audio`, whereas real-time voice deployments
   typically use `OPUS_APPLICATION_VOIP`. The measured penalty might not transfer to the mode that
   matters in practice.
4. **Generalisation.** The study covers one corpus of read English audiobooks (MP3-derived source
   audio), two recognisers, one encoder version and no network impairments. Its holdouts are
   fresh-utterance, not fresh-speaker.
5. **Mechanism not identified.** The paper does not show what the residual is. Candidates are
   in-band coding degradation, the 4–5 kHz image, level, lag, or the decode path.
6. **Exact share / metric dependence.** The bandwidth shares (17 % and 40 % along the sequential
   path) look fragile: they depend on the attribution path, the definition of linear loss, the
   error weighting and, for Whisper, a wide interval.

# Evidence Already in Paper

1. **Definition of bandwidth / linear loss.**
   - *Inclusive best-linear attribution* (Main 3.9 and 4.4, Table IV; S6, Tables S9–S10). A
     per-utterance 512-tap orthogonal projection of the actual 8 kbit/s output onto delayed copies
     of REF absorbs gain, spectral tilt, roll-off, phase and delay (median gain −2.22 dB; response
     at 3.5 kHz −7.30 dB against −2.16 dB for the control).
   - LIN8 was recognised. The residual beyond it was +0.74 pp [+0.51, +1.00] for Whisper and
     +2.32 pp [+1.85, +2.97] for wav2vec2, with the frozen outcome ROBUST_RESIDUAL. LIN8 was no more
     harmful than the control (LIN8 − LP −0.06 and −0.25 pp).
   - Level matching left +0.70 and +2.09 pp.
   - The control was validated on held-out speakers (Main 3.4, S1), and SILK at 40 kbit/s shows no
     detectable pooled residual (Main 4.3).
2. **Decoder dependence.**
   - The same frozen bitstreams decoded with libopus 1.4 kept a positive total penalty: +0.72 pp
     [+0.49, +0.97] for Whisper and +3.56 pp [+2.79, +4.54] for wav2vec2.
   - Relative to FFmpeg, the change was −0.11 pp [−0.17, −0.04] for Whisper (a lower penalty) and
     +0.09 pp [−0.04, +0.21] for wav2vec2 (no clear difference) (Main 4.4, Table IV; S7, Table S11).
   - NEG_CODEC, CELT at 64 kbit/s through the same container, decoder and resampler, leaves WER
     unchanged (Main 4.3). The claim boundary is explicit: the decomposition is defined for FFmpeg,
     and no decoder-invariant residual or share is claimed.
3. **Application mode.**
   - With `OPUS_APPLICATION_VOIP` the total penalty stayed positive: +0.70 pp [+0.48, +0.95] and
     +3.44 pp [+2.71, +4.37].
   - VoIP minus audio was −0.12 pp [−0.25, +0.00] and −0.03 pp [−0.23, +0.15]. The frozen outcome
     is NO_CLEAR_APPLICATION_DIFFERENCE for both recognisers (Main 4.4; S7).
   - The Whisper boundary case is reported: the upper bound is exactly zero, and the CER and
     test-other cells exclude zero. The paper states that no equivalence is claimed.
4. **Generalisation.**
   - The direction of the result replicates across two recognisers of different architectures and
     training regimes, both test subsets, and a pilot on the development subsets.
   - The coding-rate sweep uses 1,665 utterances never decoded before (a fresh-utterance holdout).
   - The limitations state every boundary: one encoder version, two recognisers on one corpus,
     MP3-derived source audio, no transmission, acoustic or network conditions, and no external
     replication (Main 6, items 6, 8, 9, 11 and 12).
   - The conclusion leaves generalisation to future work.
5. **Mechanism not identified.**
   - The paper claims no mechanism (abstract, Main 5 "What is still unknown", Limitations item 4,
     Conclusion).
   - The evidence is consistent with low-rate coding degradation beyond linear effects:
     - Opus differs from the control mainly within the retained band, and SILK at 40 kbit/s does
       not (Main 4.3).
     - The image power, lag and decode path are shared with SILK at 40 kbit/s, which shows no
       pooled residual.
     - NEG_CODEC is null, level matching does not remove the residual, and the residual remains
       beyond the best-linear component.
     - The residual falls with the coding rate and is not detectable at 24 and 40 kbit/s.
   - The coverage/fidelity reading is labelled an exploratory organising hypothesis (Main 5).
6. **Exact share / metric dependence.**
   - The shares are reported only as sequential, path-dependent attributions, "not causal
     fractions" (Main 4.2 and 5).
   - Under four error weightings the residual stayed positive and larger than the bandwidth
     component, and the ordering was classed as robust to the weighting. The Whisper share ranges
     from 0.17 to 0.28 (classed unstable) and the wav2vec2 share from 0.35 to 0.42 (Main 4.4; S8,
     Table S13).
   - Under the best-linear attribution the linear shares are 0.10 and 0.33 (Main 4.4).
   - The abstract and conclusion state no share value.

# Remaining Limitation

1. **Definition of bandwidth / linear loss.**
   - The best-linear projection is time-invariant within an utterance, so any time-varying linear
     effect, such as frame-wise gain changes of the coder, stays in its residual.
   - It is one inclusive definition, not the only possible one.
   - The alternative "same-frequency coherent-linear" definition (SURR8) failed held-out
     validation and was stopped before ASR (S9, Table S14).
   - The control's high-rate reference had not fully converged (up to 0.83 dB near the band edge).
2. **Decoder dependence.**
   - The decomposition exists for FFmpeg decoding only. The decoder-matched control (LP_LIBOPUS)
     failed held-out transition-shape validation (2.07 dB against 1.5 dB) and was not refitted.
   - Decoder invariance of the bandwidth share or residual is therefore not established.
   - NEG_CODEC, being CELT-coded, does not exercise the SILK upsampling step.
3. **Application mode.**
   - No equivalence margin was declared, so a small reduction under the VoIP mode, for Whisper,
     is not ruled out.
   - No bandwidth decomposition was computed under the VoIP mode.
   - FEC, DTX, packet loss and other deployment settings were not tested.
4. **Generalisation.**
   - No external corpus or new speakers were tested.
   - A planned external check was not run. Per the repository note `D1_NOT_RUN.md`, the candidate
     corpus lacks speaker identifiers for the speaker bootstrap, and the candidate recogniser's
     dependencies risked altering the frozen analysis environment.
   - Conversational, noisy, far-field and multilingual speech are untested.
5. **Mechanism not identified.**
   - No condition manipulated in-band coding degradation while holding level, image and lag
     fixed.
   - Level matching was broadband only.
   - The sweep and the allocation counterfactual change several signal properties together.
6. **Exact share / metric dependence.**
   - There is no interaction-free attribution, because no factorial bandwidth × coding design was
     run. The forced-wideband counterfactual is practical, not factorial.
   - Whisper's bandwidth component is small and detectable only on test-other, so its share
     remains imprecise under any weighting.

# What We Would Do in Revision

1. **Definition of bandwidth / linear loss.**
   - Clarify the attribution language further if a reviewer finds it ambiguous.
   - Add the full best-linear response and per-subset tables from the repository, which were
     trimmed from the supplement for length.
   - A frame-wise (time-varying) linear attribution would be a new analysis. It would be specified
     and sealed before any audio is generated, and run only if a reviewer asks for it.
2. **Decoder dependence.**
   - Add the repository's decoder diagnostics (decoder SNR, transcript differences) to the
     supplement if requested.
   - Keep the claim limited to the total penalty.
   - A decoder-matched decomposition would need a newly designed control that passes its own
     held-out validation. It would be offered only as a separately specified analysis.
3. **Application mode.**
   - No change to the claim.
   - If requested, add the VoIP-mode signal descriptors and per-subset table from the repository,
     and state the minimum difference that the interval can exclude.
4. **Generalisation.**
   - Keep the scope statements.
   - If a reviewer requires external evidence, one pre-specified replication would be proposed on
     a corpus with speaker labels. It would reuse the frozen control, conditions and analysis code,
     and be reported whatever its outcome.
5. **Mechanism not identified.**
   - No stronger claim. If needed, tighten the Discussion wording further.
   - A controlled manipulation of in-band coding degradation remains future work, not part of a
     revision.
6. **Exact share / metric dependence.**
   - Keep the shares in the results and tables only.
   - If requested, move the Whisper share into a table footnote and report the metric range beside
     it.
   - No factorial design is planned within a revision.
