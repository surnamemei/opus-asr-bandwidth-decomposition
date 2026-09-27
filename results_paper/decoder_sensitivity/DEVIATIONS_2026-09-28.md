# R4 reference-decoder total-penalty sensitivity: deviations and disclosures (2026-09-28)

Plan: `paper/decoder_sensitivity/r4_spec.json` (SHA-256 `1e3f95ec…`, commit `ec8deee`). Code
freeze: `code_freeze.json` (SHA-256 `ae16b7e4…`). None of the items below changed a gate, a
tolerance, the outcome rule, a selection or an outcome.

1. **Prior exposure (disclosed in the plan, section 3).** R1's confirmation part had already decoded
   all 2,174 Stage 3 OPUS bitstreams with the same reference-decoder path, signal only (deviation 3
   of the R1-R3 record). R4's decode reproduced R1's sealed OPUS_REFDEC waveforms for 2,174 of
   2,174 utterances. No recognition of libopus-decoded evaluation audio existed before RS4.

2. **Hypothesis-difference counts were not pre-specified.** The author requested them when
   approving R4. They were computed after RS5 by
   `paper/decoder_sensitivity/reporting/r4_descriptives.py`, which is outside the code freeze and
   reads sealed outputs only. They are sealed separately in `analysis/r4_descriptives.json`
   (SHA-256 `f66108ac…`) and enter no gate and no outcome.

3. **Execution notes (not deviations).**
   - RS3 ran with the GPU hidden from the process, so it was CPU only, as planned.
   - The RS1 ASR half and RS4 ran after the author allowed GPU use. At both starts the shared GPU
     was idle: 30.2 GiB free and no other GPU job running.
   - RS4 completed in one session: 272 chunks, no interruption or resume.

4. **Pre-disclosed limitation (plan, section 8).** REF and OPUS_FFMPEG come from the Stage 3 run and
   OPUS_LIBOPUS from the R4 run. The Whisper batch-composition component of this cross-run
   comparison is part of D and T_libopus and was not separated.

5. **Unexpected or noteworthy behaviour (descriptive only).**
   - The FFmpeg and libopus outputs of the same bitstream were never bit-identical. Their SNR had
     a median of 10.13 dB unaligned and 17.96 dB after the better one-sample shift.
   - After alignment, the tail was low: the minimum SNR was 0.06 dB and the 1st percentile 2.96 dB.
     The lowest values occurred in utterances where both decoders showed large level drops relative
     to REF (about -2.4 to -4.3 dB).
   - In 2,173 utterances the better shift was -1; in one it was +1.
   - The libopus output had 51 samples at or above full scale, in 14 utterances. As specified, they
     were passed to the recognisers unchanged.
   - Secondary scope only: the interval of D for wav2vec2-base-960h on test-other has a lower bound
     of exactly 0.0, a percentile of discrete edit counts. The interval does not exclude zero, and
     per-subset scopes enter no rule.
