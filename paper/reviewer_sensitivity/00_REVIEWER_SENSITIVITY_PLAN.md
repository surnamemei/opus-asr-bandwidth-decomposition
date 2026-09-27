# Reviewer-concern sensitivity analyses R1-R3 - frozen plan (revision 2)

Sealed `reviewer_spec.json` SHA-256 `2a6eae3511c07ac862c605c38eb4dd297a98c239248d5ec09b0eec9dc48345c0`, created 2026-09-27T05:15:09.231900+00:00.

**Status: PLANNED, NOT RUN. Frozen before any R1-R3 audio was encoded, decoded or filtered, before any R1-R3 control or surrogate was fitted and before any R1-R3 ASR run. Inputs read to freeze it: sealed Stage 2B, Stage 3 and TASLP-upgrade records, the frozen Stage 2B filter record and transfer curves, LibriSpeech SPEAKERS.TXT and file names (new validation subset), and the literature note. Binding once committed.**

This file is rendered from `reviewer_spec.json`; the JSON record is authoritative. The literature basis is `paper/reviewer_sensitivity/01_LITERATURE_NOTE.md` (SHA-256 `aea117c27e9cb05081fd7311004a986f3f1ed527f7f01c270a130eae4440078d`).

## 0. Revision history

- Supersedes the uncommitted draft sealed 2026-09-27T04:45:48.630399+00:00 (spec 668202b9b900aef09ddaf20183f98de5bc2f2e1bb3705949e18b5226485fb57f). That draft was revised at the author's request after a reviewer-style critique, before any commit and before any R1-R3 audio, fit or ASR run; it bound nothing.
- R1: the reference-decoder residual now uses a decoder-matched control. The frozen LP is reused only if it passes a pre-specified control-reuse gate (not a statistical equivalence test) against the libopus-decoded SILK40 linear response; otherwise LP_LIBOPUS is built by the unchanged Stage 2B procedure and validated on held-out speakers.
- R2: the planning probe (edge 1,625 Hz) is disclosed and diagnosed before this freeze (r2_planning_diagnosis.json). Validation moves to a new signal-only subset. The condition is renamed SURR8 and described as an 8-kbit/s effective coherent-linear surrogate: an alternative attribution under a more inclusive same-frequency linear-loss definition.
- R3: moved to the 1,665 Addition-B sweep utterances, primary estimand WER(WB8) - WER(NB8), outcomes WB_BETTER / NO_CLEAR_DIFFERENCE / WB_WORSE instead of SUPPORT / WEAKEN.
- Terminology only, before commit (no design change): R1's gate is named a control-reuse gate (R1-REUSE), not a statistical equivalence test; R2 is described as an alternative attribution under a more inclusive same-frequency linear-loss definition, with s1 and s2 a sensitivity range across two pre-specified linear definitions, not bounds on a true share.

## 1. Scope

- Stage 3 and the TASLP-upgrade additions A and B are closed. Their sealed specifications, selections, outputs, estimates, intervals and decisions are final; R1-R3 never recompute, replace or re-decide them, and the manuscript is not changed until the R1-R3 results exist.
- R1, R2 and R3 are POST-CONFIRMATION SENSITIVITY ANALYSES, specified after Stage 3, A and B in answer to reviewer concerns. None is a second confirmatory test. Their outcomes can qualify the interpretation of the Stage 3 decomposition or leave it standing; they cannot strengthen the Stage 3 confirmatory claim.
- R1: the residual may depend on the decoder. Every Stage 3 codec output was decoded by FFmpeg's native decoder, RFC 6716 leaves the decoder's resampling to the implementation, and the control was fitted to the FFmpeg-decoded SILK chain.
- R2: the control reproduces the bitrate-independent linear chain (SILK narrowband at 40 kbit/s). How much more of the penalty could be attributed to linear spectral loss if the control reproduced the coherent linear response of Opus at 8 kbit/s itself?
- R3: at the same 8 kbit/s, does spending the bits on wideband change WER? A practical bandwidth-allocation counterfactual, not a factorial causal effect.
- R1 and R2 share one ASR run on the confirmation set (RS4a); R3 has its own run on the sweep set (RS4b). Each analysis has its own gates and outcome; a gate failure stops only that analysis.
- Stage 2B, Stage 3 and upgrade modules are imported unchanged; R1-R3 code adds only what the new conditions, gates and estimands require.

## 2. Interpretation labels

- PASS / FAIL: every pre-ASR gate. All gates of an analysis must PASS before its conditions are recognised; one FAIL stops that analysis (STOPPED), which is reported with the failed gate and its measured values. R1-REUSE is a decision gate: its FAIL selects LP_LIBOPUS and stops nothing.
- R1 and R2, per recogniser: SUPPORT if the lower 95 % bound of the residual-like quantity (P1, P2) is above zero and the interval of the change of the residual excludes a reduction of a quarter or more of the Stage 3 residual; otherwise WEAKEN, qualified as 'reduction shown' (the interval excludes a smaller reduction) or 'not established'. A missing (NaN) bound never satisfies SUPPORT. Overall per analysis: SUPPORT if SUPPORT for both recognisers, WEAKEN otherwise.
- The margin, 0.25 x T*_m with T*_m the frozen Stage 3 pooled micro OPUS - LP estimate of recogniser m, is Addition A's GO margin, so A, R1 and R2 judge materiality on one scale.
- R3, per recogniser, from the 95 % interval of W = WER(WB8) - WER(NB8): WB_BETTER if the interval lies below zero, WB_WORSE if it lies above zero, NO_CLEAR_DIFFERENCE otherwise (a NaN bound gives NO_CLEAR_DIFFERENCE). No combined R3 outcome is formed; both recognisers are reported, and no difference inside the interval is interpreted.
- Implementation: reviewer_design.rule, reviewer_design.combine, reviewer_design.r3_outcome (frozen with this plan).

## 3. Provenance and inputs

- stage3_spec_sha256: `ac5a36a01f50e7643cc73bbbc2f75ce44fe34b0730ec828082084ba1643b5219`
- stage3_confirmation_freeze_sha256: `7beca2163329d259ccf169293f3173115ec8da474e5c372e46f15b93dfaaf39b`
- stage3_decision_sha256: `608c919c33e135bb7ca236e2e07e1c9b1b567285a5b1d9d8caabedeb08cb3a41`
- stage3_decision: `GO`
- stage3_bootstrap_csv_sha256: `aaa556b987e5c33b0f1c419561de78e81e1971c93e90c0cccc73db135b1a6644`
- stage3_confirmation_outputs_sha256: `de82f749b6a1446ff45cfed187c59fdd7da0feb8aa459f035d1108b0893b8d17`
- stage3_calibration_outputs_sha256: `3ae2f98149f483ee60bcf46516e2beec366d7a599738e53875fcc616f5a53100`
- stage3_confirmation_selection_sha256: `f41dcc20bd6e94a83444d632f19a186c564233906c7d252c24e79d4de6355da5`
- stage3_calibration_selection_sha256: `f966a4399ec2ea68db9a11a68ef6942524acd2e6c184f85220cc87cf0af8c79b`
- stage3_code_files_verified: `11`
- frozen_lp_taps_sha256: `583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16`
- stage3_requirements_lock_sha256: `745b91dd04708e7226ac691191c33f4118b316248335f778ee0af0d87357d45f`
- upgrade_spec_sha256: `0d5d5c7105e794c92e56427d798339121b302afce7b361f3bbe1aaf38979ccd0`
- upgrade_code_freeze_sha256: `af54518c0aa92b4ee6135d8d6e6fdc17fb2526602490fc026fc9972160a7624f`
- upgrade_amendments_sha256: `['1fcf7bc1c3d4058e08005377927ac1944f195417d9c075f2f45f2805770be393']`
- addition_A_decision_sha256: `1e7e8424a59b647f14ebb4a2328c7e60647b2ff4ec9766831cc456f1cc5451ba`
- addition_A_outcome: `GO`
- addition_B_decision_sha256: `eb0ec2a2d9db98952c2dd14d39a8a0e6205d7110f615f5d1c1f0ee5dbdc2968d`
- addition_B_outcome: `GO`
- sweep_selection_sha256: `d3fb1487594ed35fde1ad6419ff694b9c2200656fa4aa11f4c6db48966b3f680`
- addition_B_validation_report_sha256: `1ca6b91ba901cddea83298a3840eb52eb123fcaa2e1906c4aab4cdda0691c977`
- addition_B_pooled_transfer_sha256: `43011bba619111ddfded6549c838ab8d247816fdd2e09d9f9b28a731b66a992b`
- stage2b_frozen_filter_file_sha256: `c3b23b6e798f6bd7afb9e1d41985290d5c4d8867bff71eb5eb2dc4e9dcf88e10`
- stage2b_tolerances_sha256: `bc91d298ac402bbed082dfd71de0ec4dc15d0c1419261a7fdac6ca6a88c49833`
- stage2b_calibration_curves_sha256: `5899391a91bfd84780e57cce2af616ae51913e6b842eb7470a9b6985d0839388`
- stage2b_transfer_curves_sha256: `ba952d4e348c70b77519ddb6dc67669ffc44d913db0c74f965eabbd8fcf33711`
- filter_validation_selection_sha256: `0dfc09813d018c3f5026da7723cec3222fe14c957289f126e6aa3108e9932212`
- filter_validation_spec_sha256: `166f5672263373ece22a955baf3b2e1f3c7ac7c9ce14098f9daa65938d9055ff`
- filter_validation_transfer_curves_sha256: `0f6c67920ac4d5c99d8c41ebc5b433d3b3b2a85d8f72a0fe6ed47c555733df4b`
- stage3_confirmation_pooled_transfer_sha256: `2db74093a695fc86d867c977ec13a35ff3e6d0e5d3ef5076feeea7088dd30c82`
- signal_validation_selection_sha256: `51d8feb8e34ba0ca2a89b806c0086b1f87529b9587c75e2ffa07c28a762ded3d`
- r2_planning_diagnosis_sha256: `dac556a9d4b2d7d48443257e7553b922d5359ca773e3caeb76217e975c370445`
- literature_note_sha256: `aea117c27e9cb05081fd7311004a986f3f1ed527f7f01c270a130eae4440078d`
- superseded_draft_spec_sha256: `668202b9b900aef09ddaf20183f98de5bc2f2e1bb3705949e18b5226485fb57f`
- head_at_freeze: `dedb6d6207c2d14c4bac17eda4012961007c83eb`
- libopus: `libopus 1.4`
- environment_rule: `the Stage 3 environment (results_paper/stage3_asr/requirements-lock.txt, libopus 1.4, FFmpeg 6.1.1, same GPU type), verified end to end by gate E1 before any R1-R3 audio is generated`
- working tree at freeze: ['?? paper/reviewer_sensitivity/']

Inputs read to freeze this plan:

- Sealed Stage 3 records: specification, confirmation freeze, decision, bootstrap table (anchors), selections and the confirmation pooled transfer measures.
- Sealed upgrade records: specification, code freeze, amendment 01, the A and B decisions, the sweep selection, B's validation report and rows (SILK8 hashes and payload bitrates) and B's pooled transfer measures.
- Stage 2B: the frozen filter record (design parameters, calibration indices, tolerance hash), the calibration curves, the original and revised tolerances, the filter-validation selection and its sealed spec (to exclude its speakers).
- The frozen Stage 2B transfer curves of dev-clean, dev-other and the filter-validation set: the planning probe (1,625 Hz, disclosed) and its diagnosis (r2_planning_diagnosis.json). No tolerance was chosen from them; every R1 and R2 tolerance is an unchanged Stage 2B value.
- LibriSpeech SPEAKERS.TXT and train-clean-100 file names, to draw the signal-validation subset. No audio or transcript of it was read.
- The literature note 01_LITERATURE_NOTE.md; its SHA-256 is recorded.
- No audio, no transcript and no ASR output of any set was read to freeze this plan.

## 4. Selections (only the signal-validation subset is new)

| Role | File | SHA-256 | Size | Used by |
|---|---|---|---|---|
| confirmation | `results_paper/stage3_asr/selection_confirmation.json` | `f41dcc20bd6e...` | 2,174 utterances, 73 speakers, {'test-clean': 1190, 'test-other': 984} | R1 and R2: pre-ASR gates R1-G1 to G3 and the ASR run RS4a; decoded a third time (Stage 3, Addition A, R1-R2), for these sensitivity analyses only |
| sweep | `paper/taslp_upgrade/selection_sweep.json` | `d3fb1487594e...` | 1,665 utterances, 70 speakers, {'test-other': 888, 'test-clean': 777} | R3: pre-ASR gates R3-G0 to G5 and the ASR run RS4b; Addition B's fresh-utterance, not fresh-speaker, holdout; decoded a second time (B, R3) |
| technical calibration | `results_paper/stage3_asr/selection_calibration.json` | `f966a4399ec2...` | 20 utterances, 4 speakers, {'dev-clean': 20} | gates E1 and E2 only; no WER is compared between conditions |
| stage2b calibration | `results_paper/lowpass_validation/frozen_filter.json (dataset indices)` | `019f4de6162a...` | 40 dev-clean utterances, 348.1 s | RS1 calibration only: R1-C1, R1-REUSE and (if needed) the fit of LP_LIBOPUS; R2-C1 and the fit of SURR8. These are the utterances that fitted the primary control. |
| signal validation | `paper/reviewer_sensitivity/selection_signal_validation.json` | `51d8feb8e34b...` | 40 train-clean-100 utterances (20 F, 20 M speakers, one utterance each) | RS3 held-out validation only: R1-V (the decoder-matched control) and R2-V1 to V6 (SURR8); signal measurements only, no transcript and no ASR; new; drawn from file names and SPEAKERS.TXT before this freeze, excluding the 40 filter-validation speakers; none of its audio is read before RS3 |

The Stage 2B filter-validation set (40 train-clean-100 speakers) is not used by R1-R3: its Opus 8 kbit/s curve was inspected while planning. No test utterance outside the confirmation and sweep selections is read; the sweep reserve stays unused.

## 5. Common pipeline, ASR runs and statistics

- Audio: 16 kHz mono float32, length equal to REF. REF, LP, OPUS and SILK exactly as Stage 3 (paper/stage3_audio.generate_conditions); LP = frozen Stage 2B zero-phase low-pass (taps SHA-256 583c66a169d3...), applied by paper/lowpass.apply_zero_phase.
- Codec path of OPUS, SILK, NB8 and WB8: direct libopus 1.4 C API (paper/opus_direct.encode; every control set explicitly and read back), Ogg Opus written by paper/opus_direct (fixed serial, lookahead as pre-skip, end trim by granule position), decoded by torchaudio.load (FFmpeg 6.1.1 native decoder) at 48 kHz, resampled to 16 kHz by torchaudio.functional.resample: the steps of paper/stage3_audio.codec_round_trip. Only R1's *_REFDEC conditions replace the decoder.
- No re-alignment, no level normalisation and no clipping of any condition: samples with |x| >= 1 are passed to the recognisers unchanged and counted, as in Stage 3.
- Recognisers exactly as Stage 3 (paper/stage3_asr.py): Whisper large-v3 at revision 06f233fe06e7..., float16, batch 16, greedy, temperature 0 without fallback, English, transcribe, no timestamps, no prompt; wav2vec2-base-960h (torchaudio bundle), float32, greedy CTC, no language model. No adaptation.
- Scoring exactly as Stage 3: Whisper EnglishTextNormalizer (pinned tokenizer) on references and hypotheses; jiwer word and character edit counts; an empty or failed hypothesis counts as all deletions; no utterance is excluded after decoding.
- Bootstrap exactly as Stage 3 (paper/stage3_stats: PairedSet, bootstrap_weights, percentile_interval), 10,000 replicates, speakers resampled with replacement within subset strata, all conditions and both recognisers of an utterance kept together, 95 % percentile intervals. Confirmation set: seed 5305 (Stage 3's and A's seed on the same speakers, so replicate k resamples the same speakers). Sweep set: seed 5306 (B's seed on the same speakers). Every derived quantity is recomputed within each replicate from that replicate's corpus WERs; a ratio is NaN in a replicate whose denominator is <= 0 and the valid replicates are counted (the Stage 3 convention).
- Primary scope: pooled (stratified); per-subset scopes are secondary. Primary estimator: corpus (micro) WER difference from total edit counts, in percentage points (pp). No multiplicity correction across R1-R3, recognisers or subsets; only the named rule quantities enter an outcome.

ASR runs:

- RS4a, confirmation set (2,174 utterances), both recognisers, once: REF, LP, OPUS and SILK, plus OPUS_REFDEC, SILK_REFDEC and (only if R1-REUSE failed) LP_LIBOPUS for R1, and SURR8 for R2, for each analysis whose gates PASSED (for R1, unless the identity check ended it).
- RS4b, sweep set (1,665 utterances), both recognisers, once: NB8 and WB8, if R3's gates PASSED.
- Determinism: every condition is regenerated in its run; its waveform_sha256 (and ogg_sha256 for coded conditions) must equal the sealed Stage 3 confirmation manifest (REF, LP, OPUS, SILK), B's sealed validation rows (NB8, as B's SILK8) or the sealed RS3 validation rows (every new condition). A mismatch stops the run before that condition is recognised, and is reported.
- Same-run anchors: every contrast uses conditions recognised in the same run.
- Reproduction checks (not gates): per recogniser, the number of utterances whose raw hypothesis differs from the frozen Stage 3 asr_outputs.csv (REF, LP, OPUS, SILK in RS4a) and from B's frozen SILK8 hypotheses (NB8 in RS4b). Differences are reported; analyses always use same-run conditions.

Environment gates (RS1, Stage 3 calibration set):

- **E1**: gate: the Stage 3 six-condition pipeline is re-run on the Stage 3 calibration set; every waveform_sha256 and ogg_sha256 and every raw hypothesis of both recognisers must equal the sealed Stage 3 calibration outputs.
- **E2**: sanity, no comparison: on the Stage 3 calibration set, OPUS_REFDEC, SILK_REFDEC, NB8, WB8 and (after their fits) SURR8 and, if built, LP_LIBOPUS are generated and recognised. Checked: decoding, lengths, packet configurations, determinism (the first two utterances regenerated and re-recognised) and throughput. No WER is compared between conditions.
- **on_failure**: E1 FAIL stops R1-R3 before any audio of the Stage 2B calibration, signal-validation, confirmation or sweep set is generated. An E2 failure is reported and stops the affected analysis.

## 6. Anchors from frozen Stage 3 (confirmation, pooled micro, pp)

Margin = 0.25 x T*_m (Addition A's GO margin); used by R1 and R2.

| Recogniser | T* = OPUS - LP [95 % CI] | B* = LP - REF [95 % CI] | OPUS - REF | share s* [95 % CI] | margin | R1: D1_lo > | R2: Delta2_hi < |
|---|---|---|---|---|---|---|---|
| Whisper large-v3 | 0.686367 [0.460, 0.938] | 0.140498 [0.036, 0.249] | 0.826865 | 0.170 [0.049, 0.287] | 0.171592 | -0.171592 | 0.171592 |
| wav2vec2-base-960h | 2.070618 [1.679, 2.567] | 1.404980 [0.990, 1.923] | 3.475597 | 0.404 [0.348, 0.450] | 0.517654 | -0.517654 | 0.517654 |

## 7. R1 - Decoder sensitivity with a decoder-matched control

**POST-CONFIRMATION SENSITIVITY ANALYSIS - NOT A SECOND CONFIRMATORY TEST**

**Question.** Does the codec-specific residual persist when the identical Opus packets are decoded by the libopus reference decoder and the control is matched to that decoder?

### 7.1 Data and conditions

- **OPUS, SILK**: the Stage 3 OPUS (8 kbit/s, forced NB, signal=auto) and SILK (40 kbit/s, forced NB, signal=voice; B's SILK40) conditions, regenerated; Ogg bytes and FFmpeg-native waveforms bit-identical to Stage 3 (R1-G1)
- **OPUS_REFDEC, SILK_REFDEC**: the same OPUS and SILK Ogg bytes decoded by the libopus reference decoder
- **LP_DEC**: the decoder-matched control: the frozen LP if R1-REUSE passes, otherwise LP_LIBOPUS (below); decided once, at RS1
- **LP**: the frozen control, recognised in the same run (the Stage 3 residual from this run)

### 7.2 Reference decoder

- libopus 1.4 through its C API (ctypes), the shared object that encodes (opus_direct.libopus_path).
- Per utterance: OpusHead parsed (opus_direct.read_opus_head); one decoder (opus_decoder_create(48000, 1)); the audio packets in stream order, each decoded by opus_decode_float(..., frame_size=5760, decode_fec=0).
- RFC 7845: the first pre-skip samples are discarded and the output is trimmed to (final granule position - pre-skip) samples; the OpusHead output gain is 0 in every file (checked).
- Float32 output at 48 kHz, then torchaudio.functional.resample(48 000 -> 16 000) with the parameters of stage3_audio.codec_round_trip.
- libopus 1.4 has no decoder-side neural processing (LACE, NoLACE and deep PLC arrived in libopus 1.5 and are opt-in); nothing else is set on the decoder.
- Held identical: packets, container, pre-skip and end trimming, 48 kHz output, the 48 -> 16 kHz resampler, float32 samples without dither, no clipping, no re-alignment.

### 7.3 Decoder-matched control

- **R1-C1 (RS1, gate)**: On the 40 Stage 2B calibration utterances, the regenerated FFmpeg-decoded SILK40 h1_rel_db equals the frozen Stage 2B reference curve (results_paper/lowpass_validation/calibration_curves.csv, reference_h1_rel_db_40k), and the measured LP h1_rel_db equals the frozen lp_measured_h1_rel_db, each within 0.01 dB at every frequency up to 4150 Hz. FAIL: R1 STOPPED.
- **Measurement**: On the same utterances, the libopus-decoded SILK40 h1_rel_db (SILK40_LIB) is measured with the unchanged Stage 2B TransferAccumulator: the measurement that defined LP, with only the decoder changed.
- **R1-REUSE (RS1, control-reuse gate)**: Not a statistical equivalence test: a pre-specified rule that decides whether the frozen LP is reused as the control for the reference-decoder chain. LP is reused if all hold on the calibration set: (a) |coherent bandwidth(LP) - coherent bandwidth(SILK40_LIB)| <= 62.5 Hz (g4); (b) |coherent 4-8 kHz power(LP) - coherent 4-8 kHz power(SILK40_LIB)| <= 3.0 dB (g5); (c) the RMS difference of h1_rel_db (LP - SILK40_LIB) over [3000, 4200] Hz, RMS_LIB, is <= 1.5 dB and the maximum absolute difference over [3000, 4150] Hz is <= 4.0 dB (g6); (d) RMS_LIB <= RMS_FF + 0.5 dB, where RMS_FF is the same RMS against the FFmpeg-decoded SILK40 curve: the decoder change must not worsen LP's fit in the transition band by more than the Stage 2B passband-deviation tolerance (0.5 dB), inherited from Stage 2B and fixed before any libopus-decoder result is observed. PASS: LP_DEC = LP. FAIL: LP_DEC = LP_LIBOPUS. Decided once; never revisited after validation or ASR.
- **LP_LIBOPUS (RS1, only if R1-REUSE fails)**: built by the unchanged Stage 2B procedure (build_target, design, constrain; 1,023 taps, 3 measurement-domain corrections) with SILK40_LIB as the reference, on the same calibration utterances; taps and their SHA-256 frozen in results_paper/reviewer_sensitivity/calibration/lp_libopus_filter.json before the code freeze and before any validation or confirmation audio is filtered.
- **R1-V (RS3, gate, signal-validation subset)**: LP_DEC is validated on the new signal-only subset with the revised Stage 2B validation, unchanged in code and tolerances (gates 1-4 and 6 of run_lowpass_validation.evaluate_gates, gate 5 of run_lowpass_confirmation.revised_gate5; revised tolerance set as sealed in results_paper/lowpass_confirmation/revised_spec.json), with the SILK-NB linear reference and Opus 8 kbit/s decoded by the reference decoder. The same validation is required whether LP_DEC is LP or LP_LIBOPUS. FAIL: R1 STOPPED.

### 7.4 Pre-ASR gates (PASS required)

- **R1-G1**: For all 2,174 confirmation utterances, the regenerated OPUS and SILK ogg_sha256 and FFmpeg-native waveform_sha256 equal the sealed Stage 3 confirmation manifest (raw/confirmation/audio_manifest.csv; outputs_sha256 de82f749b6a1...).
- **R1-G2**: The reference decoder reports 'libopus 1.4' (opus_get_version_string) and is the shared object that encodes; every OpusHead has output gain 0 and a pre-skip of 3 x the encoder lookahead; every packet decodes without error to 960 samples.
- **R1-G3**: After pre-skip removal and end trimming, every reference-decoder output has exactly the 48 kHz length of the FFmpeg-native output; after resampling, its length equals REF and every sample is finite.
- **Identity check (not a gate)**: if every OPUS_REFDEC and SILK_REFDEC waveform is bit-identical to OPUS and SILK, R1 ends at RS3 without ASR: SUPPORT by identity for both recognisers (the Stage 3 estimates hold for the reference decoder).
- **on_failure**: R1 is STOPPED before recognition (stopping rules)
- **descriptive, sealed before ASR**: per utterance, the lag of the reference-decoder output against the FFmpeg-native output (frozen common.align_waveforms), the decoder-difference SNR 10 log10(sum y_ff^2 / sum (y_ref - y_ff)^2) at 16 kHz, the maximum absolute difference and the share of bit-identical outputs; RS1's SILK40_LIB and SILK40 curves and every R1-REUSE quantity; the frozen Stage 3 descriptor set for OPUS, OPUS_REFDEC, SILK and SILK_REFDEC. No descriptor enters a rule.

### 7.5 Estimands

- **primary**: P1_m = WER_micro(OPUS_REFDEC) - WER_micro(LP_DEC), pooled, per recogniser m: the codec-specific residual when both the codec output and the control are matched to the reference decoder
- **rule quantity**: D1_m = P1_m - (WER_micro(OPUS) - WER_micro(LP)), from the same run: the change of the residual when decoder and control are both changed to the reference decoder (D1_m = WER_micro(OPUS_REFDEC) - WER_micro(OPUS) when LP_DEC = LP). The reduction of the residual is -D1_m.
- **secondary**:
  - SILK_REFDEC - LP_DEC: the decoder-matched high-rate residual (the counterpart of Stage 3's SILK - LP, near zero there)
  - OPUS_REFDEC - LP: the reference-decoder residual against the unmatched control
  - OPUS_REFDEC - OPUS and SILK_REFDEC - SILK: the decoder effects on the codec outputs alone
  - LP_DEC - LP (when LP_LIBOPUS is used) and OPUS_REFDEC - SILK_REFDEC
  - same-run OPUS - LP and SILK - LP (the Stage 3 residuals from this run)
  - macro WER, CER and substitution/deletion/insertion composition of P1 and D1
  - per-subset scopes (test-clean, test-other)
- **descriptive**: per recogniser, the number of utterances whose raw hypothesis differs between OPUS and OPUS_REFDEC, and between SILK and SILK_REFDEC

### 7.6 Analytic expectations (not tests)

- RFC 6716 section 4.2.9 leaves the resampler non-normative but fixes its delay (Table 54). FFmpeg 6.1.1 upsamples SILK output with libswresample (filter_size 16); libopus uses its own SILK resampler. Expected: waveform differences near the 4 kHz band edge and in the 4-5 kHz image, the outputs aligned to within about a sample, and a SILK40 linear response that differs mainly near the band edge. Whether LP passes R1-REUSE is not predicted.
- SILK carries image energy of comparable power (pooled total 4-8 kHz power -15.8 dB against REF, OPUS -16.7 dB) but had no pooled residual in Stage 3, so SILK_REFDEC - LP_DEC shows whether the decoder-matched control is also residual-free at 40 kbit/s.
- These expectations come from the specifications and the source code; they are not tests.

### 7.7 Interpretation rules (exact)

- **definitions**: For recogniser m: P1_m [P1_lo, P1_hi] and D1_m [D1_lo, D1_hi], pooled micro, 95 % percentile speaker-bootstrap intervals, same run; T*_m is the frozen Stage 3 pooled micro OPUS - LP estimate.
- **SUPPORT_m**: P1_lo > 0 AND D1_lo > -0.25 x T*_m: a residual remains with the reference decoder and a decoder-matched control, and the interval excludes the change removing a quarter or more of the Stage 3 residual.
- **WEAKEN_m**: neither; qualified 'reduction shown' if D1_hi < -0.25 x T*_m, 'not established' otherwise.
- **overall**: SUPPORT if SUPPORT for both recognisers; WEAKEN otherwise. Per-recogniser outcomes are always reported.
- **not in the rules**: the SILK contrasts, the unmatched-control contrast, per-subset scopes, secondary estimators and every descriptor (all reported)
- **implementation**: reviewer_design.rule('R1', {'P1': ..., 'D1': ...}, T*_m), reviewer_design.combine

### 7.8 Consequences for the manuscript

- **SUPPORT_m**: may state, as a post-confirmation sensitivity analysis, that with the libopus reference decoder and a control matched to it a residual remained for recogniser m (values given, and which control was used); the 'Implementations' limitation is narrowed to the versions tested, and 'decoding with the reference decoder' leaves the future-work list
- **WEAKEN_m (reduction shown)**: must state that for recogniser m at least a quarter of the residual depended on the decoder chain (P1 and D1 given); the residual is described as defined for FFmpeg's native decoder, and the in-band coding-distortion interpretation is qualified for m; the Stage 3 estimates stand unchanged
- **WEAKEN_m (not established)**: reports P1 and D1 and states that the residual was not shown to be independent of the decoder chain for recogniser m; the 'Implementations' limitation stays, with the numbers added
- **STOPPED**: reports the failed gate and its values; the 'Implementations' limitation and the future-work item stay unchanged

## 8. R2 - 8-kbit/s effective coherent-linear surrogate

**POST-CONFIRMATION SENSITIVITY ANALYSIS - AN ALTERNATIVE ATTRIBUTION UNDER A MORE INCLUSIVE SAME-FREQUENCY LINEAR-LOSS DEFINITION, NOT A BANDWIDTH CONTROL; THE PRIMARY CONTROL, COMPONENTS AND SHARE ARE UNCHANGED**

**Question.** If the control is replaced by a zero-phase surrogate of the coherent linear response of Opus at 8 kbit/s itself (a more inclusive same-frequency linear-loss definition), how much of the Opus penalty is attributed to linear loss, and does a residual remain beyond the surrogate?

### 8.1 Planning probe and its diagnosis (before this freeze)

- Disclosure (2026-09-27): While the superseded draft (spec 668202b9b900...) was being written, run_lowpass_validation.build_target was applied once to the frozen opus_8k_nb h1_rel_db curve of the Stage 2B filter-validation set (train-clean-100). It gave an edge of 1625 Hz. No tolerance of that draft was changed (all were unchanged Stage 2B values), but that draft validated R2 on the same set.
- The planning probe reproduces: the unchanged Stage 2B target construction puts the edge of Opus 8 kbit/s's coherent response at 1625 Hz on the filter-validation set.
- It is not a property of Opus 8 kbit/s alone: the same construction gives 2093.75 Hz on dev-clean (the calibration data of R2) and 1656.25 Hz on dev-other, whereas the SILK-NB reference at 40 kbit/s gives 2906.25-3000 Hz on all three sets.
- It depends on the construction constants: with the level band set to 0.5-2 (frozen), 0.25-1, 0.5-1 or 0.3-3.4 kHz, the edge ranges from 906.25 to 2281.25 Hz across the three sets.
- Cause: relative to its 0.5-2 kHz level, the coherent response of Opus at 8 kbit/s declines smoothly across the band (dev-clean: +1.2 dB at 0.25 kHz, -0.8 dB at 1.5 kHz, -3.0 dB at 2.5 kHz, -4.8 dB at 3 kHz, -8.9 dB at 3.5 kHz), and so does its coherence (0.98 at 0.25 kHz, 0.72 at 1.5 kHz, 0.31 at 3 kHz). The 'edge' is where this decline first stays below -0.5 dB. It marks the start of a gradual loss of coherent (linearly predictable) content through low-rate coding, not a band limit.
- Between 2.5 and 4 kHz the three sets' targets agree to within 1.4 dB, and the surrogate target lies 2.5 to 7.6 dB below LP there on every set.
- The running minimum lies up to 2.35 dB below the capped curve (non-monotone ripples), so the target is an envelope, not the measured response itself.
- The filter-validation set, whose Opus 8 kbit/s curve was inspected, validates neither R1 nor R2. A new signal-only validation subset (selection_signal_validation.json) is drawn before this freeze, and none of its audio is read before RS3.
- The R2 condition is described as the 8-kbit/s effective coherent-linear surrogate (SURR8) for an alternative attribution under a more inclusive same-frequency linear-loss definition, not as a bandwidth control; its 'edge' is reported as a construction parameter, not as a bandwidth.
- The surrogate construction stays the unchanged Stage 2B procedure: no constant is tuned to these results. On the frozen dev-clean curve its edge is 2093.75 Hz; RS1 must reproduce that curve (gate R2-C1), so this is the edge SURR8 will have.
- R2-V3 compares the whole surrogate response, from that calibration edge to 4.2 kHz, with the target built from the new subset; the between-set variation shown above is exactly what V3 tests.
- Record: paper/reviewer_sensitivity/r2_planning_diagnosis.json (SHA-256 dac556a9d4b2...), computed from frozen curves only by reviewer_design.py diagnose-r2.

### 8.2 Data and conditions

- **SURR8**: the confirmation REF waveform filtered by the frozen surrogate (lowpass.apply_zero_phase); no codec
- **REF, LP, OPUS**: as Stage 3, recognised in the same run (RS4a)

### 8.3 Surrogate design (unchanged Stage 2B procedure, one change)

- Measured response: the pooled same-frequency coherent transfer function |H1(f)| = |Sxy| / Sxx of OPUS (the Stage 3 OPUS settings; direct libopus 1.4; frozen decode path) against REF on the 40 Stage 2B calibration utterances, after the frozen alignment (common.align_waveforms), normalised to its mean over 500-2000 Hz: TransferAccumulator.results()['h1_rel_db'] of paper/run_lowpass_validation.py, the measurement that defined the primary control with the SILK-NB reference at 40 kbit/s replaced by OPUS.
- Target: run_lowpass_validation.build_target, unchanged: 0 dB up to the first frequency above which the response stays below -0.5 dB (the 'edge', a construction parameter: 2093.75 Hz on the frozen calibration curve), then the running minimum of the response capped at 0 dB, floored at -80 dB.
- FIR: run_lowpass_validation.design and constrain, unchanged: 1,023 taps (type I), Kaiser beta 8, frequency sampling on a 16,384-point grid, gain at DC equal to the target; 3 measurement-domain corrections above the edge where the target is above -50 dB.
- Freeze: taps, SHA-256, target, calibration curve and correction iterations in results_paper/reviewer_sensitivity/calibration/surr8_filter.json at RS1, before the code freeze and before any signal-validation or confirmation audio is filtered.
- Application: lowpass.apply_zero_phase: zero phase, length preserved, no level normalisation.
- Not reproduced: OPUS's phase, lag, 4-5 kHz image and uncorrelated (noise-like) output; its in-band coherent level (h1_level_db -1.83 dB on the confirmation set) and its emphasis below the level band (h1_rel_db +1.2 dB at 0.25 kHz on the calibration curve). The surrogate is normalised to 0 dB in the level band, as LP is; broadband level was examined in A.
- Definition: above the edge the target is the greatest non-increasing curve at or below OPUS's coherent response (capped at 0 dB), so SURR8 removes at every frequency above the edge at least what OPUS's coherent response removes on the calibration data, and no more than monotonicity requires. B2 is therefore the penalty attributed to linear loss under this more inclusive same-frequency definition. With the primary control, s1 and s2 form a sensitivity range across two pre-specified linear definitions; they are not mathematical bounds on a true share.
- The frozen LP is neither changed nor re-fitted and remains the primary control.

### 8.4 Pre-ASR gates (PASS required)

- **R2-C1 (RS1, gate)**: The regenerated OPUS h1_rel_db on the 40 Stage 2B calibration utterances equals the frozen Stage 2B dev-clean opus_8k_nb curve (results_paper/lowpass_validation/transfer_curves.csv) within 0.01 dB at every frequency up to 4150 Hz, so the fitted response and its 2093.75 Hz edge are the ones diagnosed above.
- **validation set (RS3)**: the new signal-only subset: OPUS encoded and decoded by the frozen path, SURR8 applied to REF; no ASR, no transcripts. Tolerances: the unchanged Stage 2B values (TOLERANCES, SHA-256 bc91d298ac40...), with the SILK-NB reference replaced by OPUS.
- **R2-V1**: zero effective delay: symmetric odd-length taps with (L - 1) / 2 samples removed, and an absolute alignment lag against REF of at most 0 samples (none) for every utterance (g1).
- **R2-V2**: linearity: pooled coherence of SURR8 with REF >= 0.99 at every frequency up to 3800 Hz (g3).
- **R2-V3**: shape: over [edge, 4200] Hz, the RMS difference between SURR8's measured h1_rel_db and the target that build_target makes from OPUS's h1_rel_db on the validation subset is <= 1.5 dB, and the maximum absolute difference over [edge, 4150] Hz is <= 4.0 dB; edge = the calibration edge (g6, whose primary band [3000, 4200] Hz also started at its edge).
- **R2-V4**: coherent bandwidth (last frequency with h1_rel_db >= -20 dB): |SURR8 - OPUS| <= 62.5 Hz (g4).
- **R2-V5**: coherent 4-8 kHz power: |SURR8 - OPUS| <= 3.0 dB (g5): the droop across the band edge, excluded from the primary definition, is part of the surrogate.
- **R2-V6**: stopband: SURR8 h1_rel_db <= -25 dB at every frequency from 4200 Hz (g6).
- **on_failure**: R2 is STOPPED before recognition (C1 at RS1, or any of V1-V6 at RS3); no other target, FIR length, correction count, level band, deviation or tolerance is tried under the R2 label
- **descriptive, sealed before ASR**: on the validation subset: the edge that build_target gives for OPUS, LSD 0-3 kHz against REF (median, p95), power-based retained bandwidth, total 4-8 kHz power, and the SURR8 - LP response difference at 1, 2, 3, 3.5, 4 kHz; the calibration edge and correction errors; the frozen Stage 3 descriptor set for SURR8 on the confirmation audio

### 8.5 Estimands

- **primary**: P2_m = WER_micro(OPUS) - WER_micro(SURR8), pooled: the residual beyond the coherent-linear surrogate
- **rule quantity**: Delta2_m = WER_micro(SURR8) - WER_micro(LP): the part of the same-run residual OPUS - LP that the surrogate attributes to linear spectral loss (P2_m = (OPUS - LP)_m - Delta2_m)
- **surrogate component**: B2_m = WER_micro(SURR8) - WER_micro(REF)
- **attribution shares**: s2_m = B2_m / (WER_micro(OPUS) - WER_micro(REF)), the SURR8-control share, and, from the same run, the primary share s1_m = (WER_micro(LP) - WER_micro(REF)) / (WER_micro(OPUS) - WER_micro(REF)); each with its 95 % percentile interval (Stage 3 ratio convention)
- **sensitivity range**: per recogniser, [min(s1, s2), max(s1, s2)] for the point estimates, and from the lower 95 % limit of the smaller to the upper limit of the larger; a range across two definitions, not a confidence interval
- **secondary**:
  - same-run LP - REF, OPUS - LP and OPUS - REF (the Stage 3 decomposition from this run)
  - macro WER, CER and substitution/deletion/insertion composition of P2, B2 and Delta2
  - per-subset scopes (test-clean, test-other)
- **descriptive**: per recogniser, the number of utterances whose raw hypothesis differs between LP and SURR8

### 8.6 Analytic expectations (not tests)

- From the frozen calibration curve (diagnosis), the surrogate lies 4.3 dB below LP at 3 kHz and 6.9 dB at 4 kHz. Expected: Delta2 >= 0, B2 >= LP - REF and P2 <= OPUS - LP; the size of the shift is what R2 measures.
- The Stage 3 bandwidth component was larger for wav2vec2-base-960h than for Whisper large-v3 (+1.40 against +0.14 pp), so a larger Delta2 is expected for wav2vec2.
- These expectations come from frozen, published curves; they are not tests.

### 8.7 Interpretation rules (exact)

- **definitions**: For recogniser m: P2_m [P2_lo, P2_hi] and Delta2_m [Delta2_lo, Delta2_hi], pooled micro, 95 % percentile intervals, same run; T*_m as in R1.
- **SUPPORT_m**: P2_lo > 0 AND Delta2_hi < 0.25 x T*_m: a residual remains beyond the surrogate, and the interval excludes the surrogate absorbing a quarter or more of the Stage 3 residual.
- **WEAKEN_m**: neither; qualified 'reduction shown' if Delta2_lo > 0.25 x T*_m, 'not established' otherwise.
- **overall**: SUPPORT if SUPPORT for both recognisers; WEAKEN otherwise. Per-recogniser outcomes are always reported.
- **not in the rules**: B2, the shares and their range, per-subset scopes, secondary estimators and every descriptor (all reported in every outcome)
- **implementation**: reviewer_design.rule('R2', {'P2': ..., 'Delta2': ...}, T*_m), reviewer_design.combine

### 8.8 Consequences for the manuscript

- **SUPPORT_m**: may state that for recogniser m a residual remained beyond a surrogate of the coherent linear response of Opus at 8 kbit/s (values given); the bandwidth share is reported beside the unchanged primary estimate as the sensitivity range s1-s2 across two pre-specified linear definitions (primary control and SURR8 control), not as bounds on a true share
- **WEAKEN_m (reduction shown)**: must state that for recogniser m at least a quarter of the residual is reproduced by the coherent-linear surrogate; reports B2, P2 and s2 beside the primary values; qualifies the in-band coding-distortion interpretation (part of the residual is linear loss of coherent in-band content); and gives the share as a range wherever it is stated, the abstract included
- **WEAKEN_m (not established)**: reports B2, P2, Delta2 and s2 and states that a residual beyond the surrogate was not established for recogniser m; the share is reported as a range in the results
- **STOPPED**: reports the failed criterion and its values; the primary control and share are reported alone, with the statement that the control reproduces only the bitrate-independent chain

R2 tolerances (unchanged Stage 2B values):

| R2 criterion | Value | Stage 2B key |
|---|---|---|
| V1_max_abs_lag_samples | 0 | `g1_max_abs_lag_samples` |
| V2_min_coherence | 0.99 | `g3_min_coherence` |
| V2_up_to_hz | 3800.0 | `g3_min_coherence_up_to_hz` |
| V3_rms_max_db | 1.5 | `g6_h1_rms_max_db` |
| V3_rms_band_upper_hz | 4200.0 | `g6_h1_rms_band_hz[1]` |
| V3_abs_max_db | 4.0 | `g6_h1_abs_max_db` |
| V3_abs_band_upper_hz | 4150.0 | `g6_h1_abs_band_hz[1]` |
| V4_threshold_db | -20.0 | `g4_coherent_bw_threshold_db` |
| V4_max_hz | 62.5 | `g4_coherent_bw_vs_reference_max_hz` |
| V5_max_db | 3.0 | `g5_coherent_hf_vs_reference_max_db` |
| V6_from_hz | 4200.0 | `g6_stopband_from_hz` |
| V6_max_db | -25.0 | `g6_stopband_max_db` |

## 9. R3 - Forced-wideband 8 kbit/s practical counterfactual

**PRACTICAL BANDWIDTH-ALLOCATION COUNTERFACTUAL ON A FRESH-UTTERANCE, NOT FRESH-SPEAKER, HOLDOUT - NOT A FACTORIAL CAUSAL EFFECT**

**Question.** On unused utterances of the test speakers, with every other encoder setting and the decode path held fixed, does forcing wideband instead of narrowband at a nominal 8 kbit/s change WER?

### 9.1 Data and conditions

- **set**: the Addition-B sweep selection (1,665 utterances, 70 speakers, {'test-other': 888, 'test-clean': 777}); a fresh-utterance, not fresh-speaker, holdout; decoded a second time (B, R3)
- **NB8**: the Stage 3 OPUS settings (8 kbit/s, forced NB, signal=auto); on these utterances its Ogg bytes equal B's SILK8 (B's bridge share: 1.000), checked by R3-G0
- **WB8**: the same settings with the bandwidth forced to WB, through the same direct-libopus path and the same decode path
- **encoder settings**: WB8 {"bitrate_bps": 8000, "bandwidth": "WB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}; NB8 identical except bandwidth NB
- **held fixed**: target bitrate 8000 bit/s, unconstrained VBR, complexity 10, 20 ms frames, application audio, signal auto, maximum bandwidth FB, no FEC, no DTX, 0 % expected loss, LSB depth 24, 16 kHz encoder input, the decoder and the resampler
- **not factorial**: forcing WB also changes SILK's internal sampling rate (16 instead of 8 kHz), its LPC order (16 instead of 10; RFC 6716) and the allocation of about 7.6 kbit/s of payload over twice the band; R3 compares two practical configurations at one rate, estimates no interaction and does not enter the decomposition (REF and LP are not recognised in R3)

### 9.2 Pre-ASR gates (PASS required)

- **set (RS3)**: the sweep selection; encode and decode only, no ASR
- **R3-G0**: NB8 reproduces B's SILK8: for all 1,665 utterances its ogg_sha256 and waveform_sha256 equal B's sealed validation rows (results_paper/taslp_upgrade/sweep/validation/validation_rows.csv).
- **R3-G1**: settings: WB8 differs from NB8 only in bandwidth (checked at this freeze and again at RS3); for every encode, every queried control equals its requested value (read-back).
- **R3-G2**: packets: every packet of every WB8 utterance has TOC configuration 9 (SILK-only, WB, 20 ms), is mono and has frame-count code 0, and libopus reports bandwidth WB: 100 %.
- **R3-G3**: rate: the median over utterances of the payload bitrate (8 x sum of unpadded packet bytes / duration) of WB8 is within +/-15% of 8 kbit/s (B's V2 tolerance) and within +/-10% of NB8's median on the same utterances (B, frozen: 7.36 kbit/s).
- **R3-G4**: decode path: decoded at 48 kHz by the frozen path; after resampling, length equals REF and every sample is finite.
- **R3-G5**: band realised: pooled total 4-8 kHz power of WB8 against REF >= -10 dB (B, frozen, same utterances: SILK8 -16.5 dB, LP -24.4 dB).
- **on_failure**: R3 is STOPPED before recognition; no other bitrate, bandwidth, signal hint or setting is tried under the R3 label
- **descriptive, sealed before ASR**: packet-configuration counts, payload and container bitrates, RMS change and lag against REF, samples with |x| >= 1, and the frozen Stage 3 descriptor set for NB8 and WB8 (in-band coherence 0-3.5 kHz and LSD 0-3 kHz against REF among them; B's frozen SILK8 mean coherence 0.657)

### 9.3 Estimands

- **primary**: W_m = WER_micro(WB8) - WER_micro(NB8), pooled, per recogniser m, with its 95 % percentile speaker-bootstrap interval (seed 5306, B's speakers and strata)
- **secondary**:
  - macro WER, CER and substitution/deletion/insertion composition of W
  - per-subset W (test-clean, test-other)
- **descriptive**: per recogniser, the number of utterances whose raw hypothesis differs between NB8 and WB8, and between NB8 and B's frozen SILK8 hypotheses (reproduction check)

### 9.4 Outcomes (exact)

- **WB_BETTER_m**: W_hi < 0: forcing wideband lowered WER
- **WB_WORSE_m**: W_lo > 0: forcing wideband raised WER
- **NO_CLEAR_DIFFERENCE_m**: otherwise, including a missing (NaN) bound
- **reporting**: per recogniser; no combined outcome; no difference inside the interval is interpreted
- **implementation**: reviewer_design.r3_outcome(W_lo, W_hi)

### 9.5 Analytic expectations (not tests)

- libopus 1.4: OPUS_SET_BANDWIDTH overrides the automatic choice, and a 16 kHz input caps the band at WB (opus_encoder.c L1508-1529; audit record libopus-1.4), so SILK-only WB packets are expected. Skoglund and Valin (2020) coded wideband SILK at 6 kb/s, so 8 kbit/s wideband is within the encoder's range.
- Expected: restored 4-8 kHz power and more in-band distortion than NB8. The sign of W is not predicted; wav2vec2-base-960h was the more bandwidth-sensitive recogniser in Stage 3.
- These expectations come from the source code and the literature note; they are not tests.

### 9.6 Consequences for the manuscript

- **WB_BETTER_m**: may state that on unused utterances of the test speakers, forcing wideband at the same nominal 8 kbit/s lowered WER for recogniser m (W given), as a practical allocation result; must say that coding changed with the band, so this is not an interaction estimate and does not change the decomposition
- **WB_WORSE_m**: may state that forcing wideband at the same nominal 8 kbit/s raised WER for recogniser m (W given), as a practical allocation result, with the same qualification
- **NO_CLEAR_DIFFERENCE_m**: reports W and its interval and states that no difference was established for recogniser m; no practical recommendation is drawn
- **in every outcome**: the 'Limitations' text changes from 'forced to wideband at 8 kbit/s, which was not run' to report R3 as a practical counterfactual; the statement that an interaction estimate needs a factorial design stays
- **STOPPED**: reports the failed gate and its values; the limitation stays as written

## 10. Stopping rules

- No R1-R3 audio is encoded, decoded or filtered, no control or surrogate is fitted, and no audio of the signal-validation subset is read before this plan is committed (RS0).
- E1 FAIL: R1-R3 stop before any audio of the Stage 2B calibration, signal-validation, confirmation or sweep set is generated; nothing proceeds until an approved, sealed amendment exists.
- A gate FAIL of R1 (C1, V, G1-G3), R2 (C1, V1-V6) or R3 (G0-G5): that analysis is STOPPED before recognition; its conditions are not recognised; the failed gate and every measured value are sealed and reported. No redesign, re-fit, other target, FIR length, tolerance, decoder, bitrate or setting is tried under the same label; a successor analysis needs an approved, sealed amendment and is reported as post hoc. The other analyses continue.
- R1-REUSE is decided once, at RS1: its outcome selects LP or LP_LIBOPUS and is never revisited after R1-V, the identity check or ASR.
- R1 identity: if every OPUS_REFDEC and SILK_REFDEC waveform is bit-identical to OPUS and SILK, R1 ends at RS3 without ASR (SUPPORT by identity).
- RS4a is not performed if R1 ended by identity or was STOPPED and R2 was STOPPED; RS4b is not performed if R3 was STOPPED.
- Each ASR run is performed once. A resumable progress file is allowed as in Stage 3; every interruption and resume is logged; nothing is re-decoded selectively or rerun from scratch; no estimate is computed before both runs that will be performed are complete.
- The analysis (RS5) uses only the frozen code and rules; any further analysis is labelled exploratory and cannot change an outcome.
- Order independence: R1-R3 are frozen together; no result of one changes another's plan, and all are analysed together after RS4.
- Reporting: every outcome, STOPPED, WEAKEN and NO_CLEAR_DIFFERENCE included, is reported in the supplement, with a sentence in the main text wherever the affected claim is made.

## 11. Run order and commands

- RS0  Design freeze (this plan): signal-validation selection, R2 planning diagnosis and reviewer_spec.json sealed, this file rendered; binding once committed.
- RS1  Implementation and technical calibration: runner code and tests; gate E1, then E2, on the Stage 3 calibration set; on the Stage 2B calibration set, R1-C1, the SILK40_LIB measurement, R1-REUSE and (if needed) LP_LIBOPUS, then R2-C1 and the SURR8 fit; every filter frozen with its SHA-256.
- RS2  Code freeze: every R1-R3, upgrade, Stage 2B and Stage 3 code file hashed and sealed with this plan's hash, the R1-REUSE decision and the filter hashes. Files present at the design freeze and changed since are listed and need an amendment note; files added at RS1 are listed as added.
- RS3  Pre-ASR validation, no ASR: R1-G1 to G3 and the identity check on the confirmation set; R1-V and R2-V1 to V6 on the signal-validation subset; R3-G0 to G5 on the sweep set. One sealed validation report holds every gate result and descriptive measure.
- RS4  ASR runs, once each: RS4a on the confirmation set (R1, R2) and RS4b on the sweep set (R3), with the conditions of every analysis whose gates passed; both recognisers.
- RS5  Analysis with the frozen code: estimates, intervals and outcomes; one sealed decision record per analysis and a combined record.
- RS6  The manuscript is revised only after RS5 and the author's review, and only as the consequences above allow.

Commands (the runner is written at RS1; its name and subcommands are part of this plan):

- RS0: `python paper/reviewer_sensitivity/reviewer_design.py select`
- RS0: `python paper/reviewer_sensitivity/reviewer_design.py diagnose-r2`
- RS0: `python paper/reviewer_sensitivity/reviewer_design.py freeze-spec`
- RS1: `python paper/reviewer_sensitivity/run_reviewer_sensitivity.py calibrate`
- RS2: `python paper/reviewer_sensitivity/reviewer_design.py freeze-code`
- RS3: `python paper/reviewer_sensitivity/run_reviewer_sensitivity.py validate`
- RS4: `python paper/reviewer_sensitivity/run_reviewer_sensitivity.py run`
- RS5: `python paper/reviewer_sensitivity/run_reviewer_sensitivity.py analyse`

Outputs: {"calibration": "results_paper/reviewer_sensitivity/calibration", "code_freeze": "results_paper/reviewer_sensitivity/code_freeze.json", "validation": "results_paper/reviewer_sensitivity/validation", "raw": "results_paper/reviewer_sensitivity/raw/{confirmation,sweep}", "analysis": "results_paper/reviewer_sensitivity/analysis"}

## 12. Policies

- Amendments: a change to this plan before the step it affects needs explicit approval and a sealed amendment record (text, reason, time, new hashes). A change after that step is a deviation and is reported with the results.
- Sealed records are never edited; corrections go in new, dated records.

## 13. Compute

Stage 3 measured 1.59 s per utterance for six conditions and both recognisers (RTX 5090), about 0.27 s per utterance and condition. RS4a with all 8 conditions: about 77 min; RS4b (2 conditions, 1,665 utterances): about 15 min. RS3 (encode, decode and filter; no ASR): about 20-30 min. RS1: minutes.

## 14. Not done in R1-R3

- No decoder other than FFmpeg 6.1.1's native decoder and libopus 1.4; no other library version and no decoder-side enhancement.
- No re-fitting of the primary control: LP stays the primary control; LP_LIBOPUS (if built) serves R1 only, and SURR8 serves only the alternative attribution of R2.
- No mediumband, super-wideband or fullband, no other bitrate or signal hint in R3, and no REF or LP recognition in R3.
- No level matching of OPUS_REFDEC, LP_LIBOPUS, SURR8 or WB8 (broadband level was examined in A).
- No fresh speakers: R1 and R2 reuse the confirmation set, R3 reuses B's fresh-utterance, not fresh-speaker, holdout.
- No factorial interaction estimate, no multiplicity correction, and no other recogniser, beam search or language model.
- No change to Stage 1-3, A or B records, or to the manuscript, before RS5.
