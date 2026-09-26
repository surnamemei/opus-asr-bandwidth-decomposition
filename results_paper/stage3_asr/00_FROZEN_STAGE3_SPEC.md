# 00 — Frozen Stage 3 specification

Sealed `stage3_spec.json` SHA-256 `ac5a36a01f50e7643cc73bbbc2f75ce44fe34b0730ec828082084ba1643b5219`, created 2026-09-26T07:17:48.839927+00:00. Written before any pilot or confirmation utterance was decoded.

**Question.** After bandwidth is independently controlled with the frozen, independently validated linear low-pass (LP), is there still a reproducible codec-specific ASR penalty?

## Provenance

- stage1_commit: `8a77f412ee8ac779e5230d1d5a8df3cb0e027286`
- stage2_commit: `d70c9938481415d4016336fb4ad4bb58a5b9ee74`
- stage2_tag: `paper-stage2b-confirmed`
- stage2_tag_object: `ebcf06bab238a09ea891215de36483ac1ed3dce8`
- frozen_lp_taps_sha256: `583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16`
- revised_gate5_spec_sha256: `166f5672263373ece22a955baf3b2e1f3c7ac7c9ce14098f9daa65938d9055ff`
- stage2b_confirmation_selection_sha256: `0dfc09813d018c3f5026da7723cec3222fe14c957289f126e6aa3108e9932212`
- head_at_freeze: `d70c9938481415d4016336fb4ad4bb58a5b9ee74`

## Conditions (paired: every utterance in every condition)

- **REF**: original LibriSpeech waveform
- **LP**: frozen Stage 2B zero-phase low-pass (linear SILK-NB band-limiting only)
- **OPUS**: Opus 8 kbps, frozen prior-study settings (SILK-NB; packets identical to the ELEC5305 Opus 8k condition)
- **SILK**: SILK-NB at 40 kbps with signal=voice (the Stage 2B SILK-NB reference condition: SILK narrowband coding with minimal coding distortion)
- **NEG_LP**: negative control: same FIR design routine, flat to 7.0 kHz
- **NEG_CODEC**: negative control: Opus 64 kbps, frozen settings (CELT-WB), the prior study's transparent condition

- Note: OPUS and SILK are both Opus's SILK layer in narrowband mode; they differ in coding rate (8 vs 40 kbps), not in bandwidth. The prior study had no separate SILK codec.
- Level policy: no normalisation of any condition; physical output level
- Sample-rate policy: all conditions 16 kHz mono float32, length equal to REF; codec outputs decoded at 48 kHz by the frozen torchaudio.load path and resampled with torchaudio.functional.resample
- Alignment policy: no re-alignment before recognition (frozen convention); lags recorded
- Filter hashes: {"LP": "583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16", "NEG_LP": "6740aac541103376fe83da19417fe8728c31114e525bdd07c280f9b5bf0ebc0a"}
- Encoder settings: `{"OPUS": {"bitrate_bps": 8000, "bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}, "SILK": {"bitrate_bps": 40000, "bandwidth": "NB", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "voice", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}, "NEG_CODEC": {"bitrate_bps": 64000, "bandwidth": "AUTO", "max_bandwidth": "FB", "sample_rate": 16000, "channels": 1, "application": "audio", "vbr": true, "vbr_constraint": false, "complexity": 10, "frame_ms": 20.0, "signal": "auto", "packet_loss_perc": 0, "inband_fec": false, "dtx": false, "lsb_depth": 24, "prediction_disabled": false, "expert_frame_duration": "arg", "force_channels": "auto"}}`
- Expected packet configuration: {"OPUS": "SILK-NB", "SILK": "SILK-NB", "NEG_CODEC": "CELT-WB"}

## Data (speaker-disjoint sets, selected before any ASR decoding)

| set | file | sha256 | n_utterances | n_speakers | subsets |
|---|---|---|---|---|---|
| calibration | selection_calibration.json | f966a4399ec2ea68db9a11a68ef6942524acd2e6c184f85220cc87cf0af8c79b | 20 | 4 | {"dev-clean": 20} |
| pilot | selection_pilot.json | 94fee5a6bde157bc818ca50dbb933442eb5dfc64506a033f48763df387ea0aea | 138 | 69 | {"dev-clean": 72, "dev-other": 66} |
| confirmation | selection_confirmation.json | f41dcc20bd6e94a83444d632f19a186c564233906c7d252c24e79d4de6355da5 | 2174 | 73 | {"test-clean": 1190, "test-other": 984} |

- calibration: dev-clean: 4 speakers (random.Random(53051).sample of sorted speaker IDs), 5 utterances each
- pilot: dev-clean speakers not used for calibration + all dev-other speakers, 2 utterances each (random.Random(53052))
- confirmation: test-clean + test-other, all speakers, up to 30 utterances each (random.Random(53053))
- eligibility: duration <= 30.0 s (Whisper window); non-empty normalised reference; not in the excluded set of the subset
- exclusions: {"dev-clean": "Stage 2A/2B signal-level development utterances (one per speaker)", "dev-other": "Stage 2A/2B signal-level development utterances (one per speaker)", "test-clean": "frozen ELEC5305 prior-study selection (500 utterances, seed 5305)", "test-other": "frozen ELEC5305 prior-study selection (500 utterances, seed 5305)"}
- selection_inputs: file names, FLAC header durations, reference transcripts (for the non-empty rule only); no ASR output of any kind
- Post-decoding exclusions: none: every selected utterance is scored in every condition and model; an empty or failed hypothesis counts as all deletions

## ASR systems (public, fixed, no adaptation)

- **Model A** Whisper: `openai/whisper-large-v3` revision `06f233fe06e710322aca913c1bc4249a0d71fce1`, torch.float16, batch 16, generate `{"language": "en", "task": "transcribe", "num_beams": 1, "do_sample": false, "return_timestamps": false}`; temperature fallback: none (temperature 0 only; no compression-ratio, log-prob or no-speech thresholds); prompt: none (forced decoder prefix: <|startoftranscript|><|en|><|transcribe|><|notimestamps|>); VAD: none; attention sdpa; weights SHA-256 `a8e94b85976e5864ba3e9525c7e6c83b2a1eca42d4b797a0c7c24d778e40fd95`; max duration 30.0 s.
- **Model B** wav2vec2: `torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H`, checkpoint SHA-256 `488fd4f16de84438ffc945334278c1b9fb9b7159a806c1080b16111a958c945d`, greedy CTC, blank id 0, repeated tokens collapsed (paper/common.py decode(), verbatim from the frozen pipeline); language model: none; none (bundle does not normalise the waveform).

## Transcript normalisation

- {"normaliser": "transformers WhisperTokenizer.normalize -> EnglishTextNormalizer", "transformers_version": "5.17.0", "tokenizer": "openai/whisper-large-v3@06f233fe06e710322aca913c1bc4249a0d71fce1", "spelling_map_sha256": "bf1c507dc8724ca9cf9903640dacfb69dae2f00edee4f21ceba106a7392f26dd", "spelling_map_entries": 1740} (see transcript_normalization_spec.md)

## Metrics

- primary: WER (word errors S+D+I over reference words, normalised text, jiwer)
- recorded: ['substitutions', 'deletions', 'insertions', 'n_words', 'CER (secondary)']
- micro: corpus WER from total edit counts (primary)
- macro: mean of per-utterance WER differences (secondary)

## Analysis (frozen)

- Bootstrap: {"unit": "speaker", "stratified_by": "LibriSpeech subset", "replicates": 10000, "seed": 5305, "interval": "percentile 95%", "paired": "all conditions and both models of an utterance together"}
- Contrasts: [["delta_bw", "LP", "REF"], ["delta_opus_residual", "OPUS", "LP"], ["delta_silk_residual", "SILK", "LP"], ["opus_minus_silk", "OPUS", "SILK"], ["delta_opus_total", "OPUS", "REF"], ["delta_silk_total", "SILK", "REF"], ["neg_lp_minus_ref", "NEG_LP", "REF"], ["neg_codec_minus_ref", "NEG_CODEC", "REF"]]
- Pilot rule: {"proceed": "any (model, codec) micro residual 95% CI lower bound > 0", "stop": "otherwise STOP/KILL; 'bounded small' if every residual CI upper bound < 1.0 pp"}
- Confirmation KILL: all four residual CIs (2 codecs x 2 models) include 0
- Confirmation GO: for >= 1 codec: residual CI lower bound > 0 in both models, estimate >= 0.5 pp in both, pilot estimate > 0 in both
- Confirmation CONDITIONAL GO: for >= 1 codec: residual CI lower bound > 0 in both models, GO size/pilot criteria not met
- Confirmation HOLD: residual robust in only one model, or robustly negative, or other
- Confirmation negative_control_cap: if NEG_LP-REF or NEG_CODEC-REF has a CI excluding 0 and |estimate| > 0.5 pp in either model, GO/CONDITIONAL GO is capped at HOLD
- Confirmation primary_scope: pooled (clean + other, stratified); per-subset results secondary
- Conditional analyses: error-type breakdown (Step 11) and exploratory signal correlations (Step 12, Spearman, speaker bootstrap B=2000) only if a residual CI lower bound > 0 in at least one model on confirmation
- Not run: Step 14 (second bandwidth control): the LP shape is SILK-NB's measured linear response, not an arbitrary choice; deferred unless challenged

## Compute

- {"whisper_dtype": "float16", "whisper_batch_size": 16, "chunk_utterances": 8, "decoding_rationale": "greedy decoding chosen before any evaluation decode: beam 5 measured at 2-7.5 s/utterance on the shared GPU"}

## Environment

- Python 3.12.3; torch 2.13.0, torchaudio 2.11.0, torchcodec 0.16.0, numpy 2.5.2, pandas 3.0.5, jiwer 4.0.0, soundfile 0.14.0, tqdm 4.70.0, matplotlib 3.11.1, encodec 0.1.1, transformers 5.17.0
- ffmpeg version 6.1.1-3ubuntu5 Copyright (c) 2000-2023 the FFmpeg developers; libopus libopus 1.4; CUDA 13.0 on NVIDIA GeForce RTX 5090
- requirements-lock.txt SHA-256 `745b91dd04708e7226ac691191c33f4118b316248335f778ee0af0d87357d45f`
- Stage 1 regression check after installing transformers: all identical = True
- Calibration sanity: determinism {"waveforms_identical": true, "hypotheses_identical": true}, 1.32 s/utterance

## Code SHA-256 at freeze

- `paper/run_stage3.py` `5e59f8f0ec2df72c16dfa87b4b7f6adb08d4e44fa395c45c18e6cb8851422a6c`
- `paper/stage3_audio.py` `d63aada553a9e8d522958249fe4edb639123ef10c2036307308728bba18a09e5`
- `paper/stage3_asr.py` `e85089058dd97c64d55b57bba69d8a54102c1ea6676a4bcfe29c69b2ddef7075`
- `paper/stage3_stats.py` `7d655fdf0154b67e132583e214d05f694ca5d1bf2a7edde102ca694965a3078d`
- `paper/stage3_report.py` `46caf880d75ca892c0dceb8345ac975de6842e0be001a715fe0fa87f13274ca0`
- `paper/common.py` `804e77dcd689ba2b296955d3adb168c223755b7f3c998d09c0ff0ada5d3d7c0a`
- `paper/lowpass.py` `2db57c8ba3c1197fb40eeb78319f80f962c62e1f22b0589477ca4b15437431eb`
- `paper/opus_direct.py` `08a1927131d436a37953b0c2cabcf15daf3586ac44647c8fe8d2dd2bbd711f3e`
- `paper/run_lowpass_validation.py` `e312079ec8df5773ac0355e549675aa3c963719c44b63d38875c31e9f9af3b1d`
- `paper/run_opus_validation.py` `8cccd0e7ce28b1afaa0b8f52592cddd97f11dfa694eb63567ab9c92c5521d742`
- `paper/run_reproduce.py` `0b8f559197b35ace4a035387b337a9f31247042d981134ad05e6d50dd7fb8e54`
