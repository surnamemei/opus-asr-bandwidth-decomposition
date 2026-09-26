# TASLP upgrade - frozen plan

Sealed `upgrade_spec.json` SHA-256 `0d5d5c7105e794c92e56427d798339121b302afce7b361f3bbe1aaf38979ccd0`, created 2026-09-26T12:34:16.230372+00:00.

**Status: PLANNED, NOT RUN. Frozen before any upgrade audio was encoded or decoded and before any upgrade ASR run. Inputs read to freeze it: LibriSpeech file names, FLAC header durations and reference transcripts (sweep selection), exclusion records, and sealed Stage 3 result files (anchors, expected gains). Binding once committed.**

This file is rendered from `upgrade_spec.json`; the JSON record is authoritative.

## 0. Scope

- Stage 3 is closed. Its sealed specification, selections, outputs, estimates, intervals and decision (GO) are final. The upgrade never recomputes, replaces or re-decides them, and the manuscript is not changed until the upgrade results exist.
- Addition A is a POST-CONFIRMATION SENSITIVITY ANALYSIS on the Stage 3 confirmation set. It is not a second confirmatory test. Its outcome can only qualify the interpretation of the Stage 3 residual (the level confound); it cannot strengthen the Stage 3 confirmatory claim.
- Addition B is a PRE-REGISTERED PROSPECTIVE SWEEP on utterances the project has never encoded, decoded or recognised. It is a FRESH-UTTERANCE, NOT FRESH-SPEAKER, holdout.
- Stage 3 modules are imported unchanged (hashes checked against the Stage 3 confirmation freeze); upgrade code adds only what the new conditions and estimands require.

## 1. Provenance

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
- used_test_utterances_sha256: `2f7948753945353e582052120141d159ea9f7df390182e3083bf7d6e81cfcb11`
- used_test_utterances_development_commit: `051a96330c244804714c5e49faed997339ece987`
- head_at_freeze: `01c0ccba42c7c782e6089f428bd755d0e366a01a`
- libopus: `libopus 1.4`
- environment_rule: `the Stage 3 environment (results_paper/stage3_asr/requirements-lock.txt, libopus 1.4, FFmpeg 6.1.1, same GPU type); verified end to end by gate E1 before any evaluation decoding`
- working tree at freeze: ['M .gitignore', ' M requirements.txt', '?? paper/taslp_upgrade/', '?? provenance/']

## 2. Common pipeline (unchanged from Stage 3)

- Audio: 16 kHz mono float32, length equal to REF; LP = frozen Stage 2B zero-phase low-pass (taps SHA-256 583c66a169d3...), applied by paper/lowpass.apply_zero_phase.
- Codec path (every Opus condition): direct libopus 1.4 C API (paper/opus_direct.encode; every control set explicitly and read back), Ogg Opus written by paper/opus_direct (fixed serial, lookahead as pre-skip, end trim by granule position), decoded by torchaudio.load (FFmpeg 6.1.1 native decoder) at 48 kHz, resampled to 16 kHz by torchaudio.functional.resample: the steps of paper/stage3_audio.codec_round_trip.
- No re-alignment and no level normalisation of any condition, except the single scalar gain that defines OPUS8_LEVEL_MATCHED in A. No clipping: samples with |x| >= 1 are passed to the recognisers unchanged and counted, as in Stage 3.
- Recognisers exactly as Stage 3 (paper/stage3_asr.py): Whisper large-v3 at revision 06f233fe06e7..., float16, batch 16, greedy, temperature 0 without fallback, English, transcribe, no timestamps, no prompt; wav2vec2-base-960h (torchaudio bundle), float32, greedy CTC, no language model. No adaptation.
- Scoring exactly as Stage 3: Whisper EnglishTextNormalizer (pinned tokenizer) on references and hypotheses; jiwer word and character edit counts; an empty or failed hypothesis counts as all deletions; no utterance is excluded after decoding.
- Bootstrap exactly as Stage 3 (paper/stage3_stats: PairedSet, bootstrap_weights, percentile_interval): speakers resampled with replacement within subset strata, all conditions and both recognisers of an utterance kept together, 10,000 replicates, 95 % percentile intervals. Primary scope: pooled (stratified); per-subset scopes are secondary. Primary estimator: corpus (micro) WER difference from total edit counts, in percentage points (pp).

## 3. Addition A - OPUS level-matched sensitivity

**POST-CONFIRMATION SENSITIVITY ANALYSIS - NOT A SECOND CONFIRMATORY TEST**

**Question.** Is the Stage 3 codec-specific residual (OPUS - LP) explained by the lower RMS level of the decoded Opus signal (median -0.68 dB relative to REF, against -0.08 dB for LP)?

### 3.1 Data

- `results_paper/stage3_asr/selection_confirmation.json` (SHA-256 `f41dcc20bd6e94a83444d632f19a186c564233906c7d252c24e79d4de6355da5`): 2,174 utterances, 73 speakers, {'test-clean': 1190, 'test-other': 984}.
- the same 2,174 utterances; A decodes them a second time, for this sensitivity analysis only, and says so wherever A is reported.

### 3.2 Conditions and derivation

- **LP**: frozen LP, regenerated; must be bit-identical to Stage 3 (gate A1)
- **OPUS**: the Stage 3 OPUS condition (Opus 8 kbit/s, forced NB, signal=auto, Stage 3 encoder settings), regenerated through the unchanged stage3_audio.codec_round_trip; Ogg bytes and decoded waveform must be bit-identical to Stage 3 (gate A1)
- **OPUS8_LEVEL_MATCHED**: the decoded OPUS waveform times one scalar gain per utterance, so that its RMS equals that of LP
- OPUS encoder settings: `{"bitrate_bps": 8000, "bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}`
- g_u = RMS(LP_u) / RMS(OPUS_u), where RMS(x) = sqrt(mean(x^2)) over every sample of the 16 kHz float32 waveform exactly as passed to the recognisers, computed in float64 (upgrade_pipeline.level_match).
- OPUS8_LEVEL_MATCHED_u = float32(g_u * float64(OPUS_u)).
- Not applied: re-encoding, decoding of a gain-modified signal, clipping or limiting, re-alignment (the 1-2 sample OPUS lag is kept), AGC, per-frame or per-band gain, any other normalisation. LP and OPUS are unchanged.
- Expected gains (frozen Stage 3 manifest, descriptive): median +0.562 dB, 5th-95th percentile +0.290 to +1.032 dB, range -0.076 to +2.381 dB (1 utterances below 0 dB; 17 Stage 3 OPUS utterances already had samples at or above full scale).

### 3.3 Pre-ASR gates

- **A1**: For all 2,174 utterances, the regenerated LP waveform_sha256 and the regenerated OPUS ogg_sha256 and waveform_sha256 equal the sealed Stage 3 confirmation manifest (raw/confirmation/audio_manifest.csv; outputs_sha256 de82f749b6a1...).
- **A2**: For every utterance |20 log10(RMS(OPUS8_LEVEL_MATCHED) / RMS(LP))| <= 0.001 dB; every sample finite; length equal to REF.
- **A3**: Realised gains equal those implied by the frozen manifest (output_rms_dbfs LP - OPUS) within 1e-06 dB for every utterance.
- **on_failure**: stop before any ASR decoding and report; nothing is decoded until a sealed, approved amendment exists

### 3.4 Estimands and statistics

- ASR: conditions decoded, once: LP, OPUS, OPUS8_LEVEL_MATCHED; recognisers and settings as Stage 3.
- **Primary**: L_m = WER_micro(OPUS8_LEVEL_MATCHED) - WER_micro(LP), pooled, for each recogniser m, with LP and the level-matched condition decoded in the same run.
- Secondary: K_m = WER_micro(OPUS8_LEVEL_MATCHED) - WER_micro(OPUS): the effect of level matching.
- Secondary: OPUS - LP from the same run (reproduces the Stage 3 residual).
- Secondary: macro WER, CER and substitution/deletion/insertion composition of L_m and K_m.
- Secondary: per-subset scopes (test-clean, test-other).
- Descriptive: retained fraction L_m / T*_m (point estimate only).
- Descriptive: per recogniser, the number of utterances whose raw hypothesis differs between OPUS and OPUS8_LEVEL_MATCHED.
- Descriptive: gain distribution (dB) and the count of samples with |x| >= 1 in the level-matched condition.
- Bootstrap: seed 5305, 10,000 replicates; Stage 3's seed on Stage 3's speakers and strata, so bootstrap replicate k resamples exactly the speakers of Stage 3 replicate k.
- Reproduction check: Not a gate. Per recogniser and condition (LP, OPUS), the number of utterances whose raw hypothesis differs from the frozen Stage 3 asr_outputs.csv. If none differs, the same-run OPUS - LP estimate and interval equal the frozen Stage 3 values exactly. Any difference is reported; the primary analysis always uses same-run LP and OPUS.

### 3.5 Analytic expectations (not tests)

- wav2vec2-base-960h: the torchaudio bundle does not normalise the waveform, but its first convolution has no bias and is followed by GroupNorm with one channel per group. A per-utterance scalar gain is therefore removed by that normalisation, up to GroupNorm's epsilon (1e-5) and float32 rounding. Expected: K near 0 and nearly all wav2vec2 hypotheses unchanged. For wav2vec2, A is expected to be uninformative about level, and a GO for wav2vec2 is reported as expected by construction.
- Whisper large-v3: the feature extractor does not normalise the waveform; features are log10 mel power, floored at (maximum - 8), then (x + 4) / 4. A gain of G dB adds the constant G/40 to every normalised log-mel value of the 30 s window, padding included (the floor moves with the maximum), up to float rounding and the 1e-10 power floor. Expected offset: median 0.0141, maximum 0.0595. Whisper is not level-invariant, so A is informative for Whisper.
- These expectations come from reading the model code. They are not tests and do not enter the rules.

### 3.6 Interpretation rules (exact)

- **definitions**: For recogniser m: L_m [L_lo, L_hi] and K_m [K_lo, K_hi] are pooled micro estimates with 95 % percentile speaker-bootstrap intervals; T*_m is the frozen Stage 3 pooled micro OPUS - LP estimate.
- **GO_m**: L_lo > 0 AND K_lo > -0.25 x T*_m: a residual remains after level matching, and the interval excludes level matching removing a quarter or more of the Stage 3 residual.
- **FALSIFY_m**: K_hi < -0.5 x T*_m: level matching removed more than half of the Stage 3 residual, and the interval excludes smaller reductions.
- **WEAKEN_m**: neither GO_m nor FALSIFY_m (a partial reduction, or too imprecise to decide). A missing (NaN) bound never satisfies GO or FALSIFY.
- **exclusive**: GO_m requires K_lo > -0.25 T*_m and FALSIFY_m requires K_hi < -0.5 T*_m; since K_lo <= K_hi and T*_m > 0, both cannot hold.
- **overall**: GO if GO for both recognisers; FALSIFY if FALSIFY for both; WEAKEN otherwise. The per-recogniser outcome is always reported and governs the wording for that recogniser.
- **implementation**: upgrade_stats.level_rule, upgrade_stats.combine

| Recogniser | T*_m = Stage 3 OPUS - LP (pp) [95 % CI] | GO needs K_lo > | FALSIFY needs K_hi < |
|---|---|---|---|
| Whisper large-v3 | 0.686367 [0.460, 0.938] | -0.171592 | -0.343184 |
| wav2vec2-base-960h | 2.070618 [1.679, 2.567] | -0.517654 | -1.035309 |

### 3.7 Consequences for the manuscript

- **GO_m**: may state, as a post-confirmation sensitivity analysis, that matching the RMS level of the Opus signal to the control did not remove the residual for recogniser m (values given); the 'level not tested' limitation is replaced by this result.
- **WEAKEN_m**: reports L_m and K_m and states that level matching reduced the residual partly, or that the result is inconclusive, for recogniser m; the limitation stays, with the numbers added.
- **FALSIFY_m**: must state that for recogniser m more than half of the Stage 3 residual was attributable to the RMS level difference, and must revise the interpretation of the residual for m; the Stage 3 estimates stand unchanged.

### 3.8 Commands (in order, after U2)

- `python paper/taslp_upgrade/run_level_sensitivity.py regenerate`
- `python paper/taslp_upgrade/run_level_sensitivity.py run`
- `python paper/taslp_upgrade/run_level_sensitivity.py analyse`

## 4. Addition B - Forced SILK-NB bitrate sweep

**PRE-REGISTERED PROSPECTIVE SWEEP - FRESH UTTERANCES, NOT FRESH SPEAKERS**

**Question.** Within forced SILK narrowband, with the signal-type hint, every other encoder setting and the decode path held fixed, does the WER residual beyond the linear bandwidth control decrease as the coding bitrate increases?

In Stage 3, OPUS (8 kbit/s, signal=auto) and SILK (40 kbit/s, signal=voice) differed in bitrate and in the signal-type hint. B varies the bitrate alone, at five rates.

**Claim tested.** Within forced SILK-NB, with every other encoder setting, the signal hint and the decode path fixed, the WER residual beyond the linear bandwidth control decreases as the coding bitrate increases.

### 4.1 Data: a fresh-utterance, not fresh-speaker, holdout

- FRESH-UTTERANCE, NOT FRESH-SPEAKER HOLDOUT. No selected utterance has been encoded, decoded or recognised by this project, but every selected speaker also appears in the Stage 3 confirmation set (and in the prior study), and 170 of its 170 chapters also supplied Stage 3 confirmation utterances.
- No fresh-speaker holdout exists for this design within LibriSpeech: test-clean and test-other have 40 + 33 speakers, all used in Stage 3; the dev subsets supplied the Stage 2 development utterances, the calibration set and the pilot; the training subsets are excluded because wav2vec2-base-960h was fine-tuned on all 960 h of them.
- Results from B therefore generalise to new utterances of the Stage 3 test speakers, not to new speakers.
- `paper/taslp_upgrade/selection_sweep.json` (SHA-256 `d3fb1487594ed35fde1ad6419ff694b9c2200656fa4aa11f4c6db48966b3f680`): 1,665 utterances, 70 speakers ({'test-clean': 38, 'test-other': 32}; speaker sex {'F': 36, 'M': 34}), {'test-other': 888, 'test-clean': 777}, 3.17 h, 31,601 normalised reference words; 70 of the 70 speakers are in the Stage 3 confirmation set.
- Rule: test-clean + test-other, every speaker with an eligible utterance, up to 30 utterances each (random.Random(53054), speakers in sorted order, subsets in the order test-clean, test-other; the Stage 3 confirmation rule).
- Eligibility: duration <= 30.0 s (Whisper window); non-empty normalised reference; not excluded.
- Exclusions: every test utterance in provenance/used_test_utterances.json (prior study, Stage 3 confirmation, other development outputs) and every test utterance named in this repository's results_paper/. Counts: {'prior_study': 1000, 'stage3_confirmation': 2174, 'other_development_outputs': 2, 'all_used': 3176, 'local_results_paper': 2274, 'local_not_in_record': 0, 'union': 3176}. Other development outputs: 1089-134686-0005, 1089-134686-0009 (from results/baseline_results.csv, results/mp3_32k_results.csv).
- Unused test utterances longer than 30 s: {'test-clean': 7, 'test-other': 6}.
- Speakers without an eligible utterance (not in B): {'test-clean': [4077, 8224], 'test-other': [6938]}.
- Eligible but not selected (reserve, never decoded): {'test-clean': 144, 'test-other': 561}.
- Selection inputs: file names, FLAC header durations, reference transcripts (non-empty rule only), exclusion records; no audio samples, no codec, no ASR output.

### 4.2 Conditions

| Condition | Processing | Bitrate | Expected packets |
|---|---|---|---|
| LP | frozen LP (as Stage 3) | - | - |
| SILK8 | Opus, forced NB, signal=voice, 8 kbit/s | 8 kbit/s | 100 % TOC config 1 (SILK-only, NB, 20 ms) |
| SILK12 | Opus, forced NB, signal=voice, 12 kbit/s | 12 kbit/s | 100 % TOC config 1 (SILK-only, NB, 20 ms) |
| SILK16 | Opus, forced NB, signal=voice, 16 kbit/s | 16 kbit/s | 100 % TOC config 1 (SILK-only, NB, 20 ms) |
| SILK24 | Opus, forced NB, signal=voice, 24 kbit/s | 24 kbit/s | 100 % TOC config 1 (SILK-only, NB, 20 ms) |
| SILK40 | Opus, forced NB, signal=voice, 40 kbit/s | 40 kbit/s | 100 % TOC config 1 (SILK-only, NB, 20 ms) |

- The five coded conditions differ only in bitrate_bps (checked when the plan was frozen): same direct-libopus path, forced NB, signal=voice, application audio, unconstrained VBR, complexity 10, 20 ms frames, no FEC, no DTX, 0 % expected loss, same decoder and resampler.
- SILK40 has exactly the Stage 3 SILK settings.
- SILK8 differs from the Stage 3 OPUS settings only in signal (voice instead of auto).
- REF is not recognised in B (R_b needs only LP); the signal descriptors read the REF waveform.
- Encoder settings, identical except `bitrate_bps`: `{"bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "voice", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}`

### 4.3 Technical calibration and pre-ASR validation

- Set: the Stage 3 calibration set (20 dev-clean utterances, 4 speakers; selection_calibration.json, sha256 f966a4399ec2...). No test utterance.
- E1 (gate, environment): the Stage 3 six-condition pipeline is re-run on this set; every waveform_sha256 and ogg_sha256 and every raw hypothesis of both recognisers must equal the sealed Stage 3 calibration outputs. Failure: stop and report before any evaluation decoding.
- E2 (sanity, no comparison): the sweep conditions are generated and recognised on this set. Checked: encode_decode equals stage3_audio.codec_round_trip for every rate (waveform hash, first two utterances); packet configuration; decoded length and finiteness; determinism (first two utterances regenerated and re-recognised); throughput. No WER is compared between conditions.
- Validation set: the frozen sweep selection itself; encode and decode only, no ASR.
- **V1**: Every packet of every utterance in every coded condition has TOC configuration 1 (SILK-only, NB, 20 ms), is mono, has frame-count code 0 (one frame per packet), and libopus reports bandwidth NB. Required share: 100 %.
- **V2**: For each rate b, the median over utterances of the payload bitrate (8 x sum of unpadded packet bytes / utterance duration) is within +/-15% of nominal, and the five medians are strictly increasing with every adjacent ratio >= 1.2. (Frozen Stage 2A data, dev-clean, signal=auto: SILK-NB VBR payload bitrates of about 7.4 kbit/s at 8 and 11.4 kbit/s at 12, 5-7 % below nominal.)
- **V3**: Encoder read-back: for every encode, every queried control equals the requested value.
- **V4**: Decode path: decoded at 48 kHz; after resampling, length equals REF and every sample is finite.
- **V5**: LP taps SHA-256 equals the frozen value.
- Descriptive: container bitrate (Ogg bytes, as Stage 3), lag against REF, RMS change against REF, samples with |x| >= 1.
- Descriptive: bridge check: per utterance, whether the SILK8 Ogg bytes equal those produced by the Stage 3 OPUS settings (signal=auto) for the same utterance; the share of identical files tells whether R_8 is exactly a fresh-utterance replication of the Stage 3 OPUS residual (not a gate).
- Freeze: the measured median payload bitrates are sealed in the validation report and fix the x values of the measured-bitrate sensitivity before any ASR.
- Determinism: the ASR run regenerates every condition and requires its ogg_sha256 and waveform_sha256 to equal the validation rows.
- On failure: stop before any ASR decoding and report; any change (for example dropping a rate) needs explicit approval and a sealed amendment before ASR.

### 4.4 Estimands

- **Primary residuals**: R_b,m = WER_micro(SILK_b) - WER_micro(LP), pooled, for b in {8, 12, 16, 24, 40} and each recogniser m: ten primary estimates, each with a 95 % interval, no multiplicity correction; the decision uses only the quantities named in the rules.
- **Primary trend**: S_m = ordinary least-squares slope of R_b,m on x_b = log2(b) (b in kbit/s, nominal), equal weights over the five rates, in pp per doubling of bitrate, recomputed within every bootstrap replicate from that replicate's five residuals; x = 3.0000, 3.5850, 4.0000, 4.5850, 5.3219.
- Ordered/log-bitrate sensitivity: slope of R_b,m on the rank scores 1-5 (pp per rate step): the ordered trend without the log spacing.
- Ordered/log-bitrate sensitivity: monotonicity (descriptive): the number of the four adjacent differences R_b - R_b' (b < b') with a positive point estimate, and the share of bootstrap replicates with R_8 >= R_12 >= R_16 >= R_24 >= R_40.
- Ordered/log-bitrate sensitivity: slope on log2 of the measured median payload bitrates (frozen at validation).
- Secondary: adjacent-rate contrasts D_b,b' = WER_micro(SILK_b) - WER_micro(SILK_b') for (8,12), (12,16), (16,24), (24,40); positive means WER falls as the rate rises.
- Secondary: endpoint contrast E = WER_micro(SILK8) - WER_micro(SILK40): a pure bitrate contrast at a fixed signal hint.
- Secondary: macro WER, CER and substitution/deletion/insertion composition of every R_b.
- Secondary: per-subset scopes (test-clean, test-other) of every estimand.
- Descriptive mechanism evidence only: per condition, medians over utterances (frozen Stage 2B/3 metric code): LSD 0-3 and 0-4 kHz against LP; coherence 0-3.5 kHz against LP and against REF; RMS change against REF; power-based retained bandwidth; 4-8 kHz power change.
- Descriptive mechanism evidence only: pooled cross-spectral measures against REF: in-band gain |H1| (0.5-2 kHz), coherent bandwidth, coherent and total 4-8 kHz power, mirror coherence 4.1-4.9 kHz.
- Descriptive mechanism evidence only: no inferential test on any descriptor, no per-utterance correlation analysis, and no descriptor enters a rule.
- Replication anchors (descriptive): R_8 beside the Stage 3 OPUS - LP residual (T*), R_40 beside the Stage 3 SILK - LP residual (U*), E beside the Stage 3 OPUS - SILK contrast (V*). Different utterances and, for R_8, a different signal hint: agreement is not a criterion.
- Bootstrap: seed 5306, 10,000 replicates; speaker clusters stratified by subset; all six conditions and both recognisers of an utterance together; every derived quantity recomputed within each replicate.

### 4.5 Anchors from frozen Stage 3 (pooled micro, pp)

S*_m = (U*_m - T*_m) / log2(40/8): the slope implied by the frozen Stage 3 residuals at 8 kbit/s (OPUS - LP) and 40 kbit/s (SILK - LP). A meaningful decline is at least 0.5 x S*_m.

| Recogniser | T* = OPUS - LP | U* = SILK - LP | V* = OPUS - SILK | S* (pp/doubling) | 0.5 S* |
|---|---|---|---|---|---|
| Whisper large-v3 | 0.686367 | 0.018426 | 0.667941 | -0.287667 | -0.143833 |
| wav2vec2-base-960h | 2.070618 | -0.087523 | 2.158141 | -0.929461 | -0.464730 |

### 4.6 Interpretation rules (exact)

- **definitions**: For recogniser m: R_8,m [R8_lo, R8_hi] and S_m [S_lo, S_hi], pooled micro, 95 % percentile speaker-bootstrap intervals.
- **GO_m**: R8_lo > 0 AND S_hi < 0 AND S_lo <= 0.5 x S*_m: a residual is present at 8 kbit/s, it declines with bitrate, and the interval does not exclude a decline half as steep as Stage 3 implies.
- **FALSIFY_m**: S_hi >= 0 AND S_lo > 0.5 x S*_m: no decline is detected and the interval excludes a decline half as steep as Stage 3 implies.
- **WEAKEN_m**: neither: for example a decline smaller than half the implied one (S_hi < 0 but S_lo > 0.5 S*), a decline without a positive 8 kbit/s residual (R8_lo <= 0), or an interval too wide to decide. A missing (NaN) bound never satisfies GO or FALSIFY.
- **exclusive**: GO_m requires S_hi < 0 and FALSIFY_m requires S_hi >= 0.
- **overall**: GO if GO for both recognisers; FALSIFY if FALSIFY for both; WEAKEN otherwise. Per-recogniser outcomes are always reported.
- **not_in_the_rules**: adjacent contrasts, E, per-subset scopes, secondary estimators, the ordered and measured-bitrate sensitivities, and every descriptor
- **implementation**: upgrade_stats.sweep_rule, upgrade_stats.combine

### 4.7 Consequences for the manuscript

- **GO**: may state that within SILK narrowband the residual decreased with bitrate in both recognisers (slopes and intervals given), which supports, but does not isolate, the low-rate in-band coding distortion interpretation: in-band distortion, level and image properties all vary with the rate, and the descriptors are reported beside the result.
- **WEAKEN**: states that the sweep did not establish, or only partly established, a bitrate dependence (per-recogniser outcomes given); 'consistent with low-rate in-band coding distortion' may stay only with that qualification beside it.
- **FALSIFY**: must state that within SILK narrowband the residual did not decrease with bitrate over 8-40 kbit/s in either recogniser, report which pattern occurred (a residual at every rate, or at none), and remove the low-rate in-band coding distortion interpretation; the Stage 3 decomposition estimates stand unchanged.

### 4.8 Commands (in order)

- `python paper/taslp_upgrade/run_bitrate_sweep.py calibrate`
- `python paper/taslp_upgrade/upgrade_design.py freeze-code`
- `python paper/taslp_upgrade/run_bitrate_sweep.py validate`
- `python paper/taslp_upgrade/run_bitrate_sweep.py run`
- `python paper/taslp_upgrade/run_bitrate_sweep.py analyse`

## 5. Run order and stop points

- U0  Design freeze (this plan): selection_sweep.json and upgrade_spec.json sealed; binding once committed. No upgrade audio is encoded or decoded before the commit.
- U1  run_bitrate_sweep.py calibrate on the Stage 3 calibration set: gate E1 (the environment reproduces Stage 3 exactly), then E2 (sweep-condition sanity).
- U2  upgrade_design.py freeze-code: every upgrade and Stage 3 code file hashed and sealed with this plan's hash; files changed since the design freeze are listed and need an amendment note.
- U3  run_bitrate_sweep.py validate on the sweep selection (encode/decode only): gates V1-V5; sealed report with the measured median payload bitrates.
- U4  run_bitrate_sweep.py run: ASR, once (LP and SILK8-SILK40, both recognisers).
- U5  run_bitrate_sweep.py analyse: estimates, intervals and rule outcome with the frozen code; sealed decision record.
- U6  run_level_sensitivity.py regenerate on the confirmation set (no ASR): gates A1-A3.
- U7  run_level_sensitivity.py run: ASR, once (LP, OPUS, OPUS8_LEVEL_MATCHED, both recognisers).
- U8  run_level_sensitivity.py analyse: estimates, intervals, reproduction check and rule outcome; sealed sensitivity record.
- The manuscript is revised only after U8, and only as the consequences above allow.

Outputs: {"code_freeze": "results_paper/taslp_upgrade/code_freeze.json", "calibration": "results_paper/taslp_upgrade/calibration", "sweep": "results_paper/taslp_upgrade/sweep/{validation,raw,analysis}", "level": "results_paper/taslp_upgrade/level/{regeneration,raw,analysis}"}

## 6. Policies

- Single run: each evaluation ASR run (U4, U7) is performed once. A resumable progress file is allowed as in Stage 3; every interruption and resume is logged; nothing is re-decoded selectively or rerun from scratch.
- Amendments: a change to this plan before the step it affects needs explicit approval and a sealed amendment record (text, reason, time, new hashes). A change after that step is a deviation and is reported with the results.
- Stop points: a failed gate (E1, V1-V5, A1-A3) stops the upgrade before any evaluation ASR; nothing is decoded until an approved, sealed amendment exists.
- Order independence: A and B are frozen together here; neither result can change the other's plan.

## 7. Compute

Stage 3 measured 1.59 s per utterance for six conditions and both recognisers (RTX 5090). B: about 45 min for 1,665 utterances; A: about 30 min for 2,174 utterances and three conditions; calibration and validation: minutes.

## 8. Not done in the upgrade

- No REF recognition in B, so B gives no fresh-utterance bandwidth component or bandwidth share.
- No level matching in B; per-rate level differences are reported descriptively.
- No pilot or kill test for B: every rule outcome is reported, and the technical calibration covers pipeline sanity.
- No other decoder, resampler, recogniser, beam search, language model, corpus or bandwidth.
- No multiplicity correction across the ten R_b intervals; the decision uses only the rules.
- No change to Stage 1-3 files, estimates or decision, or to the manuscript.
