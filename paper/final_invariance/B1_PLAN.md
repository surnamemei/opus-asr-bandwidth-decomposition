# B1: 8-kbit/s application-mode sensitivity - frozen plan

Sealed `B1_SPEC.json` SHA-256 `42504ce4bb2675c26693d91d6cc4f0c4c3c1de5c9778e0e7c9530ca2a587b4aa`, created 2026-09-27T19:04:03.704195+00:00.

**Status: FROZEN PLAN: sealed before any OPUS_VOIP8 audio is generated. Evaluation recognition needs the committed plan, calibration, code freeze and a passed evaluation-bitstream validation.**

**Label: POST-CONFIRMATION CONFIGURATION SENSITIVITY OF THE TOTAL PENALTY - NOT A NEW DECOMPOSITION, NOT A BANDWIDTH CONTROL, NOT AN EQUIVALENCE TEST, NO VOIP BANDWIDTH SHARE**

Rendered from `B1_SPEC.json`; the JSON record is authoritative.

## 1. Question

Keeping bitrate, bandwidth, signal hint, frame duration, VBR, complexity, decoder and ASR fixed, does changing only OPUS_APPLICATION_AUDIO -> OPUS_APPLICATION_VOIP materially change the total ASR penalty of 8 kbit/s Opus?

## 2. Conditions and encoder settings

- **REF**: sealed Stage 3 REF outputs (reused)
- **OPUS_AUDIO8**: the Stage 3 OPUS condition: its sealed outputs are reused, and its bitstreams and waveforms are regenerated and must reproduce Stage 3 exactly before recognition
- **OPUS_VOIP8**: new: the Stage 3 OPUS settings with application = voip (OPUS_APPLICATION_VOIP, 2048); same encoder call, Ogg writer, FFmpeg 6.1.1 native decode at 48 kHz and torchaudio resample to 16 kHz; no realignment, no gain normalisation

- **OPUS_AUDIO8**: {"bitrate_bps": 8000, "bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}
- **OPUS_VOIP8**: {"bitrate_bps": 8000, "bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "voip", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}
- **difference**: {"application": ["audio", "voip"]}
- **not_changed**: the signal hint stays auto (it is NOT set to voice); bitrate 8000 b/s, forced NB, unconstrained VBR, complexity 10, 20 ms frames, no FEC, no DTX, lsb_depth 24, mono

## 3. Checks before recognition

- **K1 AUDIO8 reproduction**: calibration (20) and confirmation (2,174): every regenerated OPUS_AUDIO8 Ogg file and 16 kHz waveform equals the sealed Stage 3 OPUS ogg_sha256 and waveform_sha256
- **K2 VOIP8 encode**: every utterance encodes and decodes without error; decoded length equals the REF length; no NaN or Inf
- **K3 readback**: for both conditions, every control read back from the encoder after encoding equals the requested value, including the application (audio 2049, voip 2048)
- **K4 packets**: for both conditions every packet is mono, narrowband and 20 ms (the forced settings); the packet mode (SILK, hybrid, CELT) is reported, not gated
- **K5 codec and environment**: libopus 1.4 at the sealed path and hash; environment equal to the plan's
- **K6 determinism (calibration)**: a second pass reproduces every OPUS_VOIP8 Ogg file and waveform bit for bit
- **K7 ASR path (calibration, GPU)**: the frozen Stage 3 pipeline reproduces the sealed Stage 3 calibration audio and hypotheses exactly, and OPUS_VOIP8 recognition runs and repeats deterministically on two utterances (no WER is compared)
- **K8 anchors**: B1's analysis code reproduces Stage 3's WER(REF), WER(OPUS) and OPUS - REF (estimate and bounds, pooled and per subset) within 1e-09 pp
- **K9 procedural**: no OPUS_VOIP8 evaluation WER exists before the plan, calibration, code freeze and validation are committed
- **descriptive only (never a gate)**: payload bitrate distribution; clipping counts; lag against REF; RMS change; LSD 0-3 kHz and coherence 0-3.5 kHz against REF (per utterance, frozen Stage 2B/3 metrics); pooled 4-8 kHz power and 4.1-4.9 kHz mirror coherence (frozen TransferAccumulator). OPUS_VOIP8 is not required to look like OPUS_AUDIO8: the difference is the treatment
- **on_failure**: B1 is STOPPED before evaluation recognition; the failed check is sealed and reported; no other setting is tried under the B1 label

Stage 3 anchors that K8 must reproduce (micro, pp):

| Recogniser | Scope | WER REF | WER OPUS (AUDIO8) | OPUS - REF |
|---|---|---|---|---|
| Whisper large-v3 | pooled | 2.496718 | 3.323583 | 0.826865 |
| Whisper large-v3 | test-clean | 1.617305 | 1.882174 | 0.264869 |
| Whisper large-v3 | test-other | 3.681280 | 5.265149 | 1.583869 |
| wav2vec2-base-960h | pooled | 5.359652 | 8.835249 | 3.475597 |
| wav2vec2-base-960h | test-clean | 3.302833 | 4.647243 | 1.344410 |
| wav2vec2-base-960h | test-other | 8.130169 | 14.476458 | 6.346289 |

## 4. Recognition

- OPUS_VOIP8 only, once, on the 2,174 Stage 3 confirmation utterances (f41dcc20bd6e...); REF and OPUS_AUDIO8 reuse the sealed Stage 3 outputs.
- Recognisers, checkpoints, decoding options, normalisation and scoring exactly as Stage 3; runner upgrade_pipeline.run_set (chunks of 8, resumable progress file); each OPUS_VOIP8 waveform must equal its validated SHA-256.
- Cross-run component: Whisper's batches differ from Stage 3's (one condition per chunk); greedy float16 Whisper is not exactly invariant to batch composition. It is part of V and D_app and is not separated; wav2vec2 decodes each utterance alone.
- GPU: at least 12 GiB free and no other major GPU job at the start; GPU state logged.

## 5. Estimands, bootstrap and outcome rule

- **A**: WER(OPUS_AUDIO8) - WER(REF) (= Stage 3 OPUS - REF)
- **V**: WER(OPUS_VOIP8) - WER(REF)
- **D_app**: WER(OPUS_VOIP8) - WER(OPUS_AUDIO8) (primary, per recogniser, pooled)
- **secondary**: the same per test subset (uncorrected); CER and S/D/I composition descriptively
- **not computed**: no VOIP bandwidth share and no VOIP decomposition: no application-matched linear control exists or is built

Stage 3's paired speaker-cluster bootstrap, unchanged: speakers resampled within test subsets, 10,000 replicates, seed 5305 on the Stage 3 speakers, 95 % percentile intervals, every quantity recomputed in each replicate (upgrade_stats)

per recogniser, pooled D_app: VOIP_LOWER_PENALTY if its 95 % interval lies below zero; VOIP_HIGHER_PENALTY if above zero; NO_CLEAR_APPLICATION_DIFFERENCE otherwise (no equivalence claim); no combined outcome

## 6. Manuscript consequences

- **application sensitivity (either recogniser VOIP_LOWER or VOIP_HIGHER)**: scope headline claims explicitly to libopus 1.4 / application=audio / forced SILK-NB; do not imply generic WebRTC deployment behaviour
- **NO_CLEAR_APPLICATION_DIFFERENCE in both**: state it only as a post-confirmation configuration sensitivity; no equivalence claim

## 7. Run order, outputs and policies

- freeze-spec: this plan (after A1 was sealed and committed)
- calibrate encode: run_b1.py calibrate encode (K1-K6 on the 20 Stage 3 calibration utterances, CPU)
- calibrate asr: run_b1.py calibrate asr (K7, GPU)
- freeze-code: B1_CODE_FREEZE.json
- commit the plan, calibration and code freeze
- validate: run_b1.py validate (K1-K5, K8, K9 on the 2,174 confirmation bitstreams, no ASR)
- run: run_b1.py run (OPUS_VOIP8 recognition, once)
- analyse: run_b1.py analyse (bootstrap, outcome, B1_DECISION.json)

Outputs: `{"calibration": "results_paper/final_invariance/b1_calibration", "validation": "results_paper/final_invariance/b1_validation", "raw": "results_paper/final_invariance/b1_raw", "decision": "results_paper/final_invariance/B1_DECISION.json", "bootstrap": "results_paper/final_invariance/b1_bootstrap.csv"}`

- No setting, check, data selection or rule is changed after evaluation ASR is seen.
- Sealed records are never edited; failures are sealed and reported.
- Every outcome, including STOPPED, is reported.

## 8. Provenance and environment

- stage3_spec_sha256: `ac5a36a01f50e7643cc73bbbc2f75ce44fe34b0730ec828082084ba1643b5219`
- stage3_decision_sha256: `608c919c33e135bb7ca236e2e07e1c9b1b567285a5b1d9d8caabedeb08cb3a41`
- stage3_confirmation_outputs_sha256: `de82f749b6a1446ff45cfed187c59fdd7da0feb8aa459f035d1108b0893b8d17`
- stage3_calibration_outputs_sha256: `3ae2f98149f483ee60bcf46516e2beec366d7a599738e53875fcc616f5a53100`
- stage3_bootstrap_csv_sha256: `aaa556b987e5c33b0f1c419561de78e81e1971c93e90c0cccc73db135b1a6644`
- confirmation_selection_sha256: `f41dcc20bd6e94a83444d632f19a186c564233906c7d252c24e79d4de6355da5`
- calibration_selection_sha256: `f966a4399ec2ea68db9a11a68ef6942524acd2e6c184f85220cc87cf0af8c79b`
- stage3_opus_encoder_settings: `{"bitrate_bps": 8000, "bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}`
- a1_decision_sha256: `7b60320cc6079c916e54c4548bb3b87140b4d5d74ba7f6d37f7b4853d3951d8c`
- git_head_at_freeze: `569c66a3e80c23d1d7f5fd3cb41938643c7c6300`
- libopus: `{"version": "libopus 1.4", "path": "/usr/lib/x86_64-linux-gnu/libopus.so.0.9.0", "sha256": "63ddaf057d71c53090607e0467eb308640c3b39b0f189e5b937e9c397be2f676"}`
- python: `3.12.3`
- torch: `2.13.0+cu130`
- torchaudio: `2.11.0+cu130`
- numpy: `2.5.2`
- pandas: `3.0.5`
