# R4: Reference-decoder total-penalty sensitivity - frozen plan

Sealed `r4_spec.json` SHA-256 `1e3f95ecf87719d1f014a72aa82eb15f7718ccd3b7946a9953601dc81224aabc`, created 2026-09-27T14:13:42.515455+00:00.

**Status: FROZEN PLAN (RS0): sealed before any R4 audio is decoded. Evaluation steps (RS3-RS5) need the committed plan and code freeze, i.e. the author's approval.**

**Label: POST-CONFIRMATION SENSITIVITY ANALYSIS OF THE TOTAL 8 kbit/s OPUS PENALTY TO THE DECODER - NOT A SUCCESSOR TO R1, NOT A DECOMPOSITION, NOT A CONFIRMATORY TEST**

This file is rendered from `r4_spec.json`; the JSON record is authoritative.

## 1. Question and scope

Using the exact same frozen 8 kbit/s Opus bitstreams from the Stage 3 confirmation set, does replacing FFmpeg 6.1.1's native Opus decoder with the libopus reference decoder materially change the total ASR penalty?

R4 is not:

- a successor to R1 (R1 remains STOPPED)
- a decoder-matched decomposition
- a new bandwidth control
- an interaction analysis
- a new confirmation run

Claim boundaries:

- R4 tests the decoder sensitivity of the total 8 kbit/s Opus ASR penalty (OPUS - REF) only.
- It does not estimate a bandwidth component or bandwidth share under libopus.
- It does not establish decoder independence of the codec-specific residual (OPUS - LP); LP is not used.
- NO_CLEAR_DECODER_DIFFERENCE is not an equivalence claim: no equivalence margin is specified.
- R1 remains STOPPED. No R1b, R2 successor, image-removal condition, extra recogniser, extra codec, extra decoder setting or version, or VOIP experiment may be started under or alongside R4.

## 2. Provenance and environment

- stage3_spec_sha256: `ac5a36a01f50e7643cc73bbbc2f75ce44fe34b0730ec828082084ba1643b5219`
- stage3_confirmation_freeze_sha256: `7beca2163329d259ccf169293f3173115ec8da474e5c372e46f15b93dfaaf39b`
- stage3_decision_sha256: `608c919c33e135bb7ca236e2e07e1c9b1b567285a5b1d9d8caabedeb08cb3a41`
- stage3_bootstrap_csv_sha256: `aaa556b987e5c33b0f1c419561de78e81e1971c93e90c0cccc73db135b1a6644`
- stage3_confirmation_outputs_sha256: `de82f749b6a1446ff45cfed187c59fdd7da0feb8aa459f035d1108b0893b8d17`
- stage3_calibration_outputs_sha256: `3ae2f98149f483ee60bcf46516e2beec366d7a599738e53875fcc616f5a53100`
- confirmation_selection_sha256: `f41dcc20bd6e94a83444d632f19a186c564233906c7d252c24e79d4de6355da5`
- calibration_selection_sha256: `f966a4399ec2ea68db9a11a68ef6942524acd2e6c184f85220cc87cf0af8c79b`
- r1_r3_spec_sha256: `2a6eae3511c07ac862c605c38eb4dd297a98c239248d5ec09b0eec9dc48345c0`
- r1_r3_decision_sha256: `10adb06228f5e8d25d4d4033b45a0a0360ebdb32ddc47624c28b9e3513936a04`
- r1_calibration_report_sha256: `6391750a297d73635c7009180d3cdcdc97f31258c5f946fc84e82862f6585fa1`
- r1_confirmation_report_sha256: `5c4519ca1e53daf7d8e6cad9b2076ae790dfe7772bdb8c376b9e4d1d1796c32d`
- r1_post_gate_diagnosis_sha256: `7882bd8944f9654fb418fb0e339a33fc63e7676aaaeecd299140ad0894e86505`
- stage3_opus_encoder_settings: `{"bitrate_bps": 8000, "bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}`
- git_head_at_freeze: `06ee339504f4384fed3486cf6e879d9f3db6b71b`
- working tree at freeze: ?? paper/decoder_sensitivity/

- libopus: `{"version": "libopus 1.4", "path": "/usr/lib/x86_64-linux-gnu/libopus.so.0.9.0", "sha256": "63ddaf057d71c53090607e0467eb308640c3b39b0f189e5b937e9c397be2f676"}`
- python: `3.12.3`
- torch: `2.13.0+cu130`
- torchaudio: `2.11.0+cu130`
- numpy: `2.5.2`
- pandas: `3.0.5`
- resampler: `torchaudio.functional.resample(waveform_48k, 48000, 16000) with default parameters (resampling_method sinc_interp_hann, lowpass_filter_width 6, rolloff 0.99), float32`

## 3. Prior exposure (disclosure)

The Stage 3 OPUS bitstreams have already been decoded with this reference decoder path in two R1 steps: the 20 calibration utterances in R1's RS1 gate E2 (with a pipeline-sanity ASR pass on those 20 dev-clean utterances; no condition comparison), and all 2,174 confirmation utterances in R1's RS3 confirmation part (deviation 3 of the R1-R3 record; encode and decode only, no ASR). No recognition of libopus-decoded confirmation audio has ever been run, and no evaluation WER under the reference decoder exists. The signal-level summaries below were seen by the author before this plan was written; R4's signal diagnostics therefore partly repeat known values and enter no rule.

- R1 RS1 gate E2, calibration set (report `6391750a297d...`): `{"condition": "OPUS", "bit_identical": 0, "snr_db_median": 10.7200017396427, "snr_db_min": 6.085450140040869, "max_abs_difference": 0.4382057897746563, "lag_min": -1, "lag_max": -1}`
- R1 RS3 confirmation part (report `5c4519ca1e53...`, rows `b3d7b77880ea...`): R1-G1..G3 [True, True, True]; OPUS decoder difference `{"condition": "OPUS", "bit_identical": 0, "snr_db_median": 10.130099723235546, "snr_db_min": 1.767654011229027, "max_abs_difference": 0.8253550231456757, "lag_min": -1, "lag_max": 1}`; OPUS_REFDEC lag vs REF `{"0": 1084, "1": 1082, "2": 8}`, median RMS change -0.667 dB, all lengths equal REF: True
- R1 exploratory post-gate diagnosis `7882bd8944f9...` (exploratory, post hoc (R1); includes the calibration-set decoder difference after alignment)
- Not seen: no WER, CER or hypothesis of OPUS_LIBOPUS on any evaluation utterance

## 4. Selections (no new selection)

| Role | File | SHA-256 | Size | Used by |
|---|---|---|---|---|
| confirmation | `results_paper/stage3_asr/selection_confirmation.json` | `f41dcc20bd6e...` | 2,174 utterances, 73 speakers, {'test-clean': 1190, 'test-other': 984} | RS3 (decode and gates, no ASR), RS4 (ASR of OPUS_LIBOPUS, once), RS5 (analysis); the exact Stage 3 confirmation set; no utterance is added, dropped or reselected |
| calibration | `results_paper/stage3_asr/selection_calibration.json` | `f966a4399ec2...` | 20 utterances, 4 dev-clean speakers | RS1 dry run only (before the code freeze); no condition comparison is computed; the Stage 3 calibration set, already used by Stage 3, Additions A/B and R1-R3 for environment and pipeline checks |

No new selection is drawn. R4 reads no utterance outside these two sealed selections.

## 5. Conditions

- **REF**: the original LibriSpeech waveform; its recognition outputs are the sealed Stage 3 confirmation outputs (not recognised again)
- **OPUS_FFMPEG**: Stage 3's OPUS condition (label OPUS in the sealed files): the frozen bitstreams decoded by FFmpeg 6.1.1's native decoder; its recognition outputs are the sealed Stage 3 outputs (not recognised again)
- **OPUS_LIBOPUS**: new: the same frozen bitstreams decoded by the libopus 1.4 reference decoder (below), then the Stage 3 resampler; the only condition recognised in R4

## 6. Decoder implementation

- **implementation**: reviewer_pipeline.reference_decode and reviewer_pipeline.to_16k, imported unchanged from the R1-R3 code frozen at dc271f29 (the code that produced R1's sealed OPUS_REFDEC audio). Reusing frozen code does not make R4 a successor to R1: R4 uses no R1 control, estimand, gate or rule.
- **library**: libopus 1.4 (/usr/lib/x86_64-linux-gnu/libopus.so.0.9.0, SHA-256 63ddaf057d71c53090607e0467eb308640c3b39b0f189e5b937e9c397be2f676), the shared object that also encodes (opus_direct.libopus), called through ctypes
- **decoder**: opus_decoder_create(Fs=48000, channels=1); one decoder per stream
- **packets**: the audio packets of the Ogg stream in stream order, parsed by the frozen common.ogg_audio_packets (the parser of the Stage 3 packet checks)
- **decode_call**: opus_decode_float(decoder, packet, len, pcm, frame_size=5760, decode_fec=0) per packet; float32 output; every packet present, so packet-loss concealment is never invoked; no CTL is set on the decoder (decoder gain 0 dB, the libopus default)
- **pre_skip_and_end_trimming**: RFC 7845: the first pre-skip samples (OpusHead, 48 kHz units) are discarded and the output is truncated to (final granule position - pre-skip) samples; the OpusHead output gain must be 0, so the RFC 7845 output-gain step is the identity
- **resampling**: torchaudio.functional.resample(pcm_48k, 48000, 16000), default parameters, float32: the resampling step of the Stage 3 pipeline (stage3_audio.codec_round_trip)
- **no_correction**: no gain or level matching, no integer or fractional realignment, no filtering, no clipping or limiting; samples beyond full scale are passed unchanged, as in Stage 3
- **output_length_convention**: at 48 kHz the decoded length equals final granule position - pre-skip = 3 x N_REF samples and equals FFmpeg's decoded length for the same file; pre-skip = 3 x the encoder lookahead; every packet yields 960 samples (20 ms); after resampling the length equals N_REF (the REF length), as for Stage 3's OPUS
- **bitstreams**: Stage 3 kept no Ogg files, only their SHA-256. The Ogg bytes are regenerated from the REF FLAC by the frozen Stage 3 encoder call (opus_direct.encode with the Stage 3 OPUS settings), exactly as Addition A (gate A1) and R1 (R1-G1) did, and every file must reproduce the sealed Stage 3 ogg_sha256 byte for byte (G1); the decoder therefore reads the exact frozen bitstreams
- **ffmpeg_path_for_diagnostics_only**: opus_direct.decode_frozen_path (torchaudio.load, FFmpeg 6.1.1 native decoder, 48 kHz) and the same resampler; the result is expected to equal Stage 3's sealed OPUS waveform_sha256 (reported) and is used only for the descriptive decoder-difference SNR, never for recognition

## 7. Gates

- **G1 (RS3)**: every regenerated OPUS Ogg file's SHA-256 equals the sealed Stage 3 OPUS ogg_sha256 (results_paper/stage3_asr/raw/confirmation/audio_manifest.csv), for all 2,174 utterances
- **G2 (RS3)**: libopus decoding succeeds for all 2,174 utterances: opus_decoder_create returns OPUS_OK, every packet decodes without error, and the packets parsed from each file equal the encoder's packets (none missing, so concealment is never used)
- **G3 (RS3)**: decoded lengths follow the pre-specified output-length convention (decoder section) for every utterance: output gain 0, pre-skip = 3 x lookahead, 960 samples per packet, 48 kHz length = final granule - pre-skip = 3 x REF length = FFmpeg's 48 kHz length, and 16 kHz length = REF length
- **G4 (RS3)**: no NaN or Inf sample at 48 kHz or 16 kHz, in any utterance
- **G5 (RS1 and RS3)**: the decoder, library and software versions and every decoder setting are recorded, and equal the values sealed in this plan (environment, decoder)
- **G6 (RS1, calibration set)**: the 20 calibration utterances reproduce deterministically under the new decoder path: (a) two decodes of each regenerated file give identical 16 kHz waveforms (SHA-256), and (b) recognising the first 2 utterances again gives identical hypotheses in both recognisers
- **G7 (procedural)**: no evaluation WER is inspected before the plan and the code freeze are sealed: RS3-RS5 refuse to run unless both are committed; no OPUS_LIBOPUS recognition output exists before RS4
- **G8 (RS1, proposed addition)**: environment reproduction: the frozen Stage 3 pipeline, rerun on the 20 calibration utterances, reproduces the sealed Stage 3 calibration audio (waveform and Ogg SHA-256) and hypotheses exactly (as E1 of Additions A/B and R1-R3). Needed because REF and OPUS_FFMPEG come from the Stage 3 run and OPUS_LIBOPUS from a new one
- **G9 (RS3, proposed addition)**: analysis-code reproduction: before any OPUS_LIBOPUS recognition, the R4 analysis code, applied to the sealed Stage 3 metrics, reproduces Stage 3's WER(REF), WER(OPUS) and OPUS - REF (estimate and both bounds, pooled and per subset, both recognisers) within 1e-09 pp
- **on_failure**: R4 is STOPPED before recognition; the failed gate and its values are sealed and reported; no other decoder, decoder setting, library version, resampler, trimming or alignment is tried under the R4 label

Stage 3 anchors that G9 must reproduce (confirmation, micro, pp):

| Recogniser | Scope | WER(REF) | WER(OPUS_FFMPEG) | T_ffmpeg [95 % CI] |
|---|---|---|---|---|
| Whisper large-v3 | pooled | 2.496718 | 3.323583 | 0.826865 [0.574118, 1.102322] |
| Whisper large-v3 | test-clean | 1.617305 | 1.882174 | 0.264869 [0.117670, 0.433241] |
| Whisper large-v3 | test-other | 3.681280 | 5.265149 | 1.583869 [1.035950, 2.197523] |
| wav2vec2-base-960h | pooled | 5.359652 | 8.835249 | 3.475597 [2.732038, 4.452609] |
| wav2vec2-base-960h | test-clean | 3.302833 | 4.647243 | 1.344410 [0.966196, 1.770054] |
| wav2vec2-base-960h | test-other | 8.130169 | 14.476458 | 6.346289 [4.761893, 8.541681] |

## 8. Recognition run

- RS4: OPUS_LIBOPUS only, 2,174 utterances, once (resumable progress file as in Stage 3; every interruption logged; nothing re-decoded selectively).
- Recognisers, checkpoints, decoding options and scoring exactly as Stage 3 (stage3_asr, unchanged): Whisper large-v3 float16 greedy (batch 16) and wav2vec2-base-960h float32 greedy CTC; Whisper's text normaliser; WER = (S + D + I) / N.
- Runner: the frozen upgrade_pipeline.run_set/process_chunk (chunks of 8 utterances). Each utterance's audio is regenerated and must equal its RS3-validated SHA-256 before it is recognised.
- Known cross-run component: Stage 3 queued six conditions per chunk into mixed Whisper batches; R4 has one condition, so its Whisper batches differ in composition (8 items per chunk). Greedy float16 Whisper decoding is not exactly invariant to batch composition (Addition A: 3 of 4,348 hypotheses differed, changing OPUS - LP by 0.002 pp). This run-to-run component is part of D and T_libopus and is not separated; wav2vec2 decodes each utterance alone and is unaffected.

## 9. Estimands, bootstrap and outcome rule

- **primary**: per recogniser, pooled over test-clean and test-other: T_ffmpeg = WER(OPUS_FFMPEG) - WER(REF), T_libopus = WER(OPUS_LIBOPUS) - WER(REF) and D = WER(OPUS_LIBOPUS) - WER(OPUS_FFMPEG); WER is the corpus (micro) WER from total edit counts, in pp
- **secondary**: the same three quantities per test subset (test-clean, test-other), uncorrected for multiplicity
- **descriptive**: corpus WER of each condition with its interval
- **note**: D = T_libopus - T_ffmpeg exactly (REF cancels); T_ffmpeg is Stage 3's sealed OPUS - REF

the Stage 3 paired speaker-cluster bootstrap, unchanged: speakers resampled with replacement within each test subset (stratified), all conditions and both recognisers of an utterance kept together, 10,000 replicates, seed 5305 on the Stage 3 speakers (Stage 3's seed, as Addition A), 95 % percentile intervals; every quantity recomputed in each replicate (upgrade_stats.replicate_weights, Replicates, interval_row and analyse, unchanged)

- **DECODER_LOWER_PENALTY_m**: D_hi < 0: the 95 % interval of D lies entirely below zero
- **NO_CLEAR_DECODER_DIFFERENCE_m**: the interval includes zero (or a bound is missing)
- **DECODER_HIGHER_PENALTY_m**: D_lo > 0: the interval lies entirely above zero
- **scope**: pooled only, per recogniser; per-subset intervals are secondary and enter no rule; no combined outcome; no minimum-effect threshold
- **implementation**: r4_design.r4_outcome(D_lo, D_hi)

## 10. Descriptive diagnostics

- None enters a gate or the rule. Computed at RS3 for OPUS_LIBOPUS and, for comparison, for the regenerated OPUS_FFMPEG audio (expected to equal Stage 3's sealed OPUS waveform; reported):
- integer lag relative to REF (distribution; common.align_waveforms, as in the Stage 3 audio manifest)
- RMS level change relative to REF (dB; median and 5th-95th percentiles)
- SNR between the FFmpeg- and libopus-decoded OPUS at 16 kHz: unaligned, and after one-sample alignment (the better of the shifts -1 and +1 samples, overlap only; the chosen shift recorded)
- pooled power in 4000-5000 Hz and total 4-8 kHz power relative to REF (dB), and pooled mirror coherence over 4.1-4.9 kHz (the frozen Stage 2B/3 TransferAccumulator, after the frozen alignment)
- reproduction check (reported, not a gate): each OPUS_LIBOPUS waveform is expected to equal R1's sealed OPUS_REFDEC waveform (results_paper/reviewer_sensitivity/validation/confirmation_rows.csv), since the decoder code, bitstreams and resampler are the same

## 11. Manuscript consequences

- **in every outcome**: reported as a post-confirmation sensitivity analysis of the total penalty only, in a supplementary section, with one sentence in the main paper; the Implementations limitation keeps its existing sentences (R1's frozen STOPPED consequence) and gains at most one sentence reporting R4; the abstract, the decomposition and the shares are unchanged; no statement of decoder independence of the residual
- **NO_CLEAR_DECODER_DIFFERENCE_m**: reports T_libopus and D with intervals and states that no difference in the total penalty between the two decoders was established for m; not an equivalence claim
- **DECODER_LOWER_PENALTY_m / DECODER_HIGHER_PENALTY_m**: states that for m the total 8 kbit/s penalty was lower / higher with the libopus reference decoder (D given), and that the Stage 3 results are defined for FFmpeg's decoder
- **STOPPED**: reports the failed gate and its values; the manuscript is otherwise unchanged

## 12. Stopping rules

- A failed gate (G1-G6, G8, G9) stops R4 before recognition; its values are sealed and reported.
- The RS1 dry run touches only the 20 calibration utterances; no confirmation audio is regenerated, decoded or recognised before the plan and the code freeze are committed (author approval).
- RS4 runs once; no estimate is computed before it is complete; no utterance is re-recognised selectively.
- RS5 uses only the frozen code and rule; any further analysis is labelled exploratory and cannot change the outcome.

## 13. Run order and commands

- RS0 (now): seal this plan (r4_design.py freeze-spec).
- RS1 (now, calibration set only): dry run - run_r4.py calibrate decode (G1-G5 analogues, G6a, diagnostics, reproduction of R1's E2 audio) and run_r4.py calibrate asr (G8 environment reproduction, G6b, OPUS_LIBOPUS pipeline sanity; no condition comparison).
- RS2 (after RS1): seal the code freeze (r4_design.py freeze-code).
- Author approval, then commit of the plan and the code freeze.
- RS3: run_r4.py validate - regenerate and decode the 2,174 confirmation files, gates G1-G5 and G9, descriptive diagnostics; no ASR.
- RS4: run_r4.py run - recognition of OPUS_LIBOPUS, once.
- RS5: run_r4.py analyse - estimates, intervals, outcomes; sealed decision record.

- RS0: `python paper/decoder_sensitivity/r4_design.py freeze-spec`
- RS1: `python paper/decoder_sensitivity/run_r4.py calibrate decode`
- RS1: `python paper/decoder_sensitivity/run_r4.py calibrate asr`
- RS2: `python paper/decoder_sensitivity/r4_design.py freeze-code`
- RS3: `python paper/decoder_sensitivity/run_r4.py validate`
- RS4: `python paper/decoder_sensitivity/run_r4.py run`
- RS5: `python paper/decoder_sensitivity/run_r4.py analyse`

Outputs: `{"calibration": "results_paper/decoder_sensitivity/calibration", "code_freeze": "results_paper/decoder_sensitivity/code_freeze.json", "validation": "results_paper/decoder_sensitivity/validation", "raw": "results_paper/decoder_sensitivity/raw", "analysis": "results_paper/decoder_sensitivity/analysis"}`

## 14. Policies and compute

- A change to this plan before the step it affects needs the author's approval and a sealed amendment; a change after that step is a deviation and is reported with the results.
- Sealed records are never edited; corrections go in new, dated records. R4 writes only under paper/decoder_sensitivity/ and results_paper/decoder_sensitivity/; the Stage 3, Addition A/B and R1-R3 records are read, after their seals and output manifests are verified, and never modified.
- Every outcome, STOPPED and NO_CLEAR_DECODER_DIFFERENCE included, is reported.

RS1 a few minutes; RS3 about 0.3-0.5 s per utterance on the CPU (about 10-20 min); RS4 about 0.3 s per utterance for one condition on the RTX 5090 (about 10-15 min with model loading); RS5 about 1-2 min.
