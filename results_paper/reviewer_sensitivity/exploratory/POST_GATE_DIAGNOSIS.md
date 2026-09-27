# R1-V and R2-V failures: post-gate diagnosis

**EXPLORATORY - POST HOC: computed after the frozen R1-V and R2-V gates failed and R1 and R2 were STOPPED; not part of any rule; cannot change any outcome; code outside the code freeze.**

Record: `post_gate_diagnosis.json` (SHA-256 `7882bd8944f9654fb418fb0e339a33fc63e7676aaaeecd299140ad0894e86505`), from `paper/reviewer_sensitivity/exploratory/post_gate_diagnosis.py`.

## Readings (exploratory)

- The libopus chain has a sub-sample, content-dependent delay (about 0.45 samples at 16 kHz); the frozen per-utterance integer alignment puts its utterances at lag 0 or 1, whereas every FFmpeg-decoded utterance is at lag 2.
- Under that alignment the pooled |H1| of the libopus chain depends on each set's lag mix, so the libopus SILK40 curve moved between the calibration set and the signal-validation subset; with one fixed alignment for every utterance it is as stable across sets as FFmpeg's. This most likely drove the R1-REUSE failure and the R1-V gate 6 failure.
- Measured with one fixed alignment, libopus's band edge is genuinely flatter to about 3.8 kHz than FFmpeg's and then steeper.
- The R2-V3 misfit is concentrated at 4.0-4.2 kHz, more than 20 dB down, where the held-out Opus 8 kbit/s curve is less steep than on dev-clean and SURR8 (whose corrections did not converge there) over-attenuates.
- These readings are exploratory. Any successor analysis needs an approved, sealed amendment and is reported as post hoc.

## Numbers

- Alignment lags against REF on the signal-validation subset: {"lp": {"0": 40}, "opus_8k_nb": {"0": 21, "1": 18, "2": 1}, "opus_8k_nb_ffmpeg": {"2": 40}, "silk_nb_linear_ref": {"0": 22, "1": 17, "2": 1}, "surr8": {"0": 40}}.
- libopus delay (samples at 16 kHz): {"calibration": {"median": 0.4350653869044945, "min": 0.15816573685762583, "max": 0.9072613703493306}, "validation": {"median": 0.47497523327798785, "min": 0.24613676415329988, "max": 1.8116923897685062}}.
- Largest calibration-minus-validation difference of the SILK40 |H1| over 3.0-4.15 kHz (dB): {"libopus_frozen": 3.61, "libopus_subsample": 2.9, "libopus_fixed0": 0.92, "ffmpeg_frozen": 0.94, "ffmpeg_fixed2": 0.94}.
- libopus minus FFmpeg SILK40 |H1|, one fixed alignment, calibration set, 3.0-4.15 kHz: max 3.53 dB, RMS 1.95 dB.
- R1-V gate 6 misfit (LP_LIBOPUS minus libopus SILK40): RMS 1.60 dB over 3.0-3.9 kHz, 3.04 dB over 3.9-4.2 kHz.
- R2-V3 misfit (SURR8 minus validation target): RMS 0.87 dB from the edge to 4 kHz, 6.26 dB over 4.0-4.2 kHz; largest -8.91 dB at 4125 Hz; validation-subset edge 1812.5 Hz.
- Decoder waveform difference, Stage 3 calibration set: [{"condition": "OPUS", "lag": -1.0, "snr_unaligned_db_median": 10.7200017396427, "snr_aligned_db_median": 17.74302856613103, "snr_aligned_db_min": 11.876271990342266}, {"condition": "SILK", "lag": -1.0, "snr_unaligned_db_median": 10.510870378497962, "snr_aligned_db_median": 17.323407175654005, "snr_aligned_db_min": 10.678931651300203}].
