# A1: Cross-validated best-linear decomposition of 8-kbit/s Opus - frozen plan

Sealed `A1_SPEC.json` SHA-256 `77da2190c2115548b654f6aeb2abd0dfa21b54fbabed7100f103aa91560d8edb`, created 2026-09-27T16:27:00.335148+00:00.

**Status: FROZEN PLAN: sealed before any A1 audio is read. Evaluation (confirmation-set LIN8 audio and ASR) needs the committed plan, calibration, code freeze and a passed signal validation.**

**Label: POST-CONFIRMATION SENSITIVITY ANALYSIS: AN INCLUSIVE SAME-FREQUENCY LINEAR ATTRIBUTION - NOT A REPLACEMENT FOR STAGE 3, NOT A BANDWIDTH CONTROL, NOT R2, NOT A CAUSAL DECOMPOSITION**

Rendered from `A1_SPEC.json`; the JSON record is authoritative. Method basis: `A1_METHOD_NOTE.md`.

## 1. Question

If every same-frequency linearly predictable change of the actual 8 kbit/s Opus chain is assigned to a linear component, does a substantial ASR residual remain?

A1 is not:

- a replacement for the Stage 3 decomposition, which stays the primary pre-specified result
- a redefinition of the published primary control
- a bandwidth control
- a resurrection of R2 (a global zero-phase surrogate)
- a causal coding-distortion decomposition

## 2. Method

- **choice**: option A of the pass instructions: the orthogonal projection-based decomposition (OPD) target component of Iwamoto et al. (Interspeech 2022) and Ochiai et al. (IEEE/ACM TASLP 2024), i.e. the BSS Eval projection; see A1_METHOD_NOTE.md
- **definition**: for each utterance u with REF x_u and the exact Stage 3 OPUS waveform y_u (FFmpeg decode, 16 kHz, length T), LIN8_u = P_x y_u restricted to the T samples of REF, where P_x projects onto the span of x_u delayed by tau = -256 ... +255 (L = 512 basis vectors); the residual is y_u - LIN8_u
- **copied**: L = 512 (BSS Eval default, Ochiai et al.); per-utterance, time-domain, unconstrained least-squares FIR projection; mir_eval._project algorithm (zero padding by L - 1, FFT autocorrelation Toeplitz Gram matrix, FFT cross-correlation, exact solve with least-squares fallback), reimplemented in numpy (a1_opd.py)
- **adapted**: the delay span is centred (tau = -256 ... +255) instead of causal (0 ... 511), because the decoded signal is aligned with REF to within 1-2 samples and the chain's linear response is two-sided (linear-phase resampler); implemented as in BSS Eval by delaying the estimate by 256 samples and advancing the projection. The centring is fixed a priori at L/2; the causal variant is computed on the calibration set only, as a descriptive check, and selects nothing
- **free_parameters**: none: no global filter is fitted, no support or ridge grid is used, no parameter is tuned on any data
- **allowed_in_the_linear_component**: gain, spectral tilt, band-edge roll-off, phase and delay within the 32 ms span; no unity gain, flat passband, zero phase or 4 kHz cutoff is imposed
- **not_in_the_linear_component**: anything not same-frequency linearly predictable from REF by one time-invariant 512-tap filter per utterance: nonlinear coding distortion, the 4-5 kHz mirror image, time-varying gains

## 3. Data isolation and selection

- The projection is utterance-level by construction (the prior method), so the confirmation utterances' own OPUS waveforms are projected; this is pre-specified here, uses no ASR output, and no parameter is fitted on any set.
- The new signal-only sets (selection_a1_signal.json) serve to run every piece of code before the freeze, to fix and check the signal gates, and to describe the linear response; no ASR is run on them.
- No Addition B sweep utterance is used.

- **path**: paper/final_invariance/selection_a1_signal.json
- **sha256**: 354439bd16ae73661c268b5557b7727845f6d81aba039d2e873966a427c8bcbe
- **seed**: 53056
- **calibration**: 40 utterances (20 F, 20 M speakers)
- **validation**: 40 utterances (20 F, 20 M speakers)
- **evaluation**: the 2,174 Stage 3 confirmation utterances (73 speakers), unchanged

## 4. Signal processing

- **OPUS8**: Stage 3 OPUS settings (libopus 1.4, 8 kbit/s, forced NB, signal=auto, application audio, unconstrained VBR, complexity 10, 20 ms frames), Ogg Opus, FFmpeg 6.1.1 native decode at 48 kHz, torchaudio resample to 16 kHz: stage3_audio.codec_round_trip, unchanged
- **LIN8**: a1_opd.project(REF, OPUS8): float64, cast to float32 for recognition; no gain matching, no realignment after the projection, no clipping, no post-filtering

## 5. Gates

- **C1 (calibration set)**: for every utterance the projection is finite and its normal-equation residual is <= 1e-06; LIN8 has the REF length and is finite
- **C2 (calibration set)**: a second pass reproduces every LIN8 waveform bit for bit
- **C3 (Stage 3 calibration set, GPU)**: the frozen Stage 3 pipeline reproduces the sealed Stage 3 calibration audio and hypotheses exactly (environment reproduction), and the LIN8 recognition path runs and repeats deterministically (no WER is compared)
- **collapse tolerance (fixed at calibration, before validation audio is read)**: tol = max(1.0 dB, interquartile range of the calibration per-utterance projection NMSE in dB)
- **V1 (validation set)**: as C1 for every validation utterance
- **V2 (validation set)**: no held-out collapse: median validation NMSE (dB) <= median calibration NMSE (dB) + tol
- **V3 (validation set)**: a second pass reproduces every LIN8 waveform bit for bit
- **E1 (confirmation set, before recognition)**: the regenerated OPUS Ogg files and waveforms equal the sealed Stage 3 OPUS ogg_sha256 and waveform_sha256 for all 2,174 utterances
- **E2 (confirmation set)**: as C1 for all 2,174 LIN8 waveforms
- **E3 (confirmation set)**: the environment equals the one sealed in this plan
- **E4 (confirmation set)**: A1's analysis code reproduces Stage 3's WER(REF), WER(LP), WER(OPUS), LP - REF, OPUS - LP and OPUS - REF (estimate and bounds, pooled and per subset) within 1e-09 pp
- **E5 (procedural)**: no A1 evaluation WER exists before the plan, calibration, code freeze and validation are committed
- **on_failure**: A1 is STOPPED before evaluation recognition; the failed gate is sealed and reported; no other span, filter length, projection, alignment or tolerance is tried under the A1 label

Stage 3 anchors that E4 must reproduce (micro, pp):

| Recogniser | Scope | WER REF | WER LP | WER OPUS | LP - REF | OPUS - LP | OPUS - REF |
|---|---|---|---|---|---|---|---|
| Whisper large-v3 | pooled | 2.496718 | 2.637216 | 3.323583 | 0.140498 | 0.686367 | 0.826865 |
| Whisper large-v3 | test-clean | 1.617305 | 1.589213 | 1.882174 | -0.028092 | 0.292961 | 0.264869 |
| Whisper large-v3 | test-other | 3.681280 | 4.048868 | 5.265149 | 0.367587 | 1.216282 | 1.583869 |
| wav2vec2-base-960h | pooled | 5.359652 | 6.764631 | 8.835249 | 1.404980 | 2.070618 | 3.475597 |
| wav2vec2-base-960h | test-clean | 3.302833 | 3.712176 | 4.647243 | 0.409343 | 0.935067 | 1.344410 |
| wav2vec2-base-960h | test-other | 8.130169 | 10.876264 | 14.476458 | 2.746094 | 3.600195 | 6.346289 |

## 6. Recognition

- LIN8 only, once, on the 2,174 confirmation utterances; REF, LP and OPUS reuse the sealed Stage 3 outputs (exact paired reuse: the same utterances, and OPUS is the same waveform, checked by E1).
- Recognisers, checkpoints, decoding options and scoring exactly as Stage 3; runner upgrade_pipeline.run_set (chunks of 8, resumable progress file); each LIN8 waveform must equal its E-validated SHA-256.
- Cross-run component: Whisper's batches differ from Stage 3's (one condition per chunk); greedy float16 Whisper is not exactly invariant to batch composition (Addition A: 3 of 4,348 hypotheses). This is part of L8, R8 and delta_L and is not separated; wav2vec2 decodes each utterance alone.
- GPU: at least 12 GiB free and no other major GPU job at the start; GPU state logged.

## 7. Estimands, bootstrap and outcome rule

- **primary (pooled, per recogniser)**: L8 = WER(LIN8) - WER(REF); R8 = WER(OPUS8) - WER(LIN8); T = WER(OPUS8) - WER(REF); corpus (micro) WER, pp
- **descriptive share**: S8 = L8 / T (NaN in a replicate with T <= 0; such replicates are counted); an inclusive linear-loss sensitivity share, not a bandwidth share and not a true share
- **change from the primary decomposition**: delta_L = L8 - (LP - REF) = WER(LIN8) - WER(LP); delta_R = R8 - (OPUS - LP) = -delta_L
- **secondary**: the same quantities per test subset, uncorrected for multiplicity

Stage 3's paired speaker-cluster bootstrap, unchanged: speakers resampled within test subsets, 10,000 replicates, seed 5305 on the Stage 3 speakers, 95 % percentile intervals, every quantity recomputed in each replicate (upgrade_stats.replicate_weights, Replicates, interval_row, analyse)

- 1 LINEAR_EXPLANATION_DOMINATES: R8's 95 % interval does not lie above zero in either recogniser, or L8 > R8 (the best-linear surrogate absorbs most of the total penalty) in both recognisers
- 2 MIXED: R8's interval lies above zero in exactly one recogniser
- 3 ROBUST_RESIDUAL: R8's interval lies above zero in both recognisers and R8 > L8 in both
- 4 RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS: R8's interval lies above zero in both, but L8 >= R8 in at least one

the pass instructions' four classes, with this precedence fixed where their definitions overlap; pooled micro estimates; implemented by a1_design.a1_outcome

Regardless of outcome: the Stage 3 decomposition remains the primary pre-specified result.

## 8. Manuscript consequences

- **ROBUST_RESIDUAL**: keep the Stage 3 decomposition; add a short sensitivity statement that a residual also remains under a more inclusive best-linear attribution; never call S8 a true share
- **RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS**: retain the Stage 3 result; state that the exact component split depends on how linear loss is defined; high-level prose says a substantial residual remains rather than exact shares
- **MIXED**: make recogniser dependence central; remove any cross-recogniser statement that the residual dominates
- **LINEAR_EXPLANATION_DOMINATES**: do not hide it; rescope: the high-rate narrowband control underestimates the linear component of low-rate codec degradation, and a more inclusive linear attribution materially changes the split; Stage 3 stays the original pre-specified analysis
- **STOPPED**: report the failed gate; the manuscript's decomposition is unchanged

## 9. Run order, outputs and policies

- select (done before this plan): selection_a1_signal.json
- freeze-spec: this plan
- calibrate: run_a1.py calibrate signal (C1, C2, collapse tolerance) and run_a1.py calibrate asr (C3, GPU)
- freeze-code: A1_CODE_FREEZE.json
- validate: run_a1.py validate (V1-V3)
- commit plan, selection, calibration, code freeze and validation
- evaluate: run_a1.py evaluate (E1-E5, 2,174 LIN8 waveforms, no ASR)
- run: run_a1.py run (LIN8 recognition, once)
- analyse: run_a1.py analyse (bootstrap, outcome, A1_DECISION.json)

Outputs: `{"calibration": "results_paper/final_invariance/a1_calibration", "validation": "results_paper/final_invariance/a1_validation", "evaluation": "results_paper/final_invariance/a1_evaluation", "raw": "results_paper/final_invariance/a1_raw", "decision": "results_paper/final_invariance/A1_DECISION.json", "bootstrap": "results_paper/final_invariance/a1_bootstrap.csv"}`

- No threshold, span, filter length, alignment or data selection is changed after evaluation ASR is seen.
- Sealed records are never edited; corrections go in new, dated records; failures are sealed and reported.
- Every outcome, including STOPPED and LINEAR_EXPLANATION_DOMINATES, is reported.

## 10. Provenance and environment

- stage3_spec_sha256: `ac5a36a01f50e7643cc73bbbc2f75ce44fe34b0730ec828082084ba1643b5219`
- stage3_decision_sha256: `608c919c33e135bb7ca236e2e07e1c9b1b567285a5b1d9d8caabedeb08cb3a41`
- stage3_confirmation_outputs_sha256: `de82f749b6a1446ff45cfed187c59fdd7da0feb8aa459f035d1108b0893b8d17`
- stage3_calibration_outputs_sha256: `3ae2f98149f483ee60bcf46516e2beec366d7a599738e53875fcc616f5a53100`
- stage3_bootstrap_csv_sha256: `aaa556b987e5c33b0f1c419561de78e81e1971c93e90c0cccc73db135b1a6644`
- confirmation_selection_sha256: `f41dcc20bd6e94a83444d632f19a186c564233906c7d252c24e79d4de6355da5`
- calibration_selection_sha256: `f966a4399ec2ea68db9a11a68ef6942524acd2e6c184f85220cc87cf0af8c79b`
- a1_signal_selection_sha256: `354439bd16ae73661c268b5557b7727845f6d81aba039d2e873966a427c8bcbe`
- method_note_sha256: `3008352f54417512bdbb94ed37a67305fbf905fe2f3a2bccd36ebeb2940db709`
- stage3_opus_encoder_settings: `{"bitrate_bps": 8000, "bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}`
- git_head_at_freeze: `a7bddc33291355c63d8a29c241e26d947ed82106`
- libopus: `{"version": "libopus 1.4", "path": "/usr/lib/x86_64-linux-gnu/libopus.so.0.9.0", "sha256": "63ddaf057d71c53090607e0467eb308640c3b39b0f189e5b937e9c397be2f676"}`
- python: `3.12.3`
- torch: `2.13.0+cu130`
- torchaudio: `2.11.0+cu130`
- numpy: `2.5.2`
- pandas: `3.0.5`
