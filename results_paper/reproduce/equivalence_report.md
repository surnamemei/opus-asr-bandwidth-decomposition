# Stage 1 equivalence report

**Verdict: PASS** — 250 of 250 checks passed; 28 informational rows.

Scope: first 50 utterances of the frozen 500-utterance selection of each subset; WAV, Opus 12k and Opus 8k through the frozen encoding path (ffmpeg libopus, default settings).

## Environment

- Python 3.12.3 (/home/mei/elec5305-project/.venv/bin/python)
- torch 2.13.0, torchaudio 2.11.0, torchcodec 0.16.0, numpy 2.5.2, pandas 3.0.5, jiwer 4.0.0, soundfile 0.14.0, tqdm 4.70.0, matplotlib 3.11.1, encodec 0.1.1
- ffmpeg version 6.1.1-3ubuntu5 Copyright (c) 2000-2023 the FFmpeg developers
- libopus linked by ffmpeg: libopus 1.4
- CUDA 13.0, cuDNN 92000, NVIDIA GeForce RTX 5090 (driver 596.49)
- Torch flags: {'cuda.matmul.allow_tf32': False, 'cudnn.allow_tf32': True, 'cudnn.benchmark': False, 'cudnn.deterministic': False, 'float32_matmul_precision': 'highest'}
- The environment that produced the frozen results was not recorded in the repository; equivalence is established by reproduction, not by version matching.

## Mismatches

None.

## All checks (representation drift summarised below)

| check | subset | condition | field | comparison | n | n_exact | max_abs_error | tolerance | status | note |
|---|---|---|---|---|---|---|---|---|---|---|
| selection | test-clean | all | dataset_index (selection order) | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | sample | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | reference | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | prediction | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | original_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | compressed_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | WAV | wer (per utterance) | tolerance | 50 | 50 | 0 | abs <= 0 | PASS |  |
| asr | test-clean | WAV | corpus WER over reproduced utterances | tolerance | 1 | 1 | 0 | abs <= 0 | PASS |  |
| bitrate | test-clean | WAV | actual_bitrate_kbps | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| bitrate | test-clean | WAV | compression_ratio | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| waveform | test-clean | WAV | num_samples = (frozen original_size_bytes - 78) / 2 | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-clean | WAV | decoded sample rate seen by ASR | info |  |  |  |  | INFO | [16000]. not stored in frozen outputs |
| errors | test-clean | WAV | edit errors S+D+I (vs error_analysis.py) | exact | 50 | 50 |  | exact | PASS |  |
| errors | test-clean | WAV | S/D/I split differences | info |  |  |  |  | INFO | 0 utterance(s). JiWER vs error_analysis.py back-trace tie-breaking; totals are the check |
| asr | test-clean | Opus 12k | sample | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 12k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 12k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 12k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 12k | reference | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 12k | prediction | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 12k | original_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 12k | compressed_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 12k | wer (per utterance) | tolerance | 50 | 50 | 0 | abs <= 0 | PASS |  |
| asr | test-clean | Opus 12k | corpus WER over reproduced utterances | tolerance | 1 | 1 | 0 | abs <= 0 | PASS |  |
| bitrate | test-clean | Opus 12k | actual_bitrate_kbps | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| bitrate | test-clean | Opus 12k | compression_ratio | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| waveform | test-clean | Opus 12k | num_samples = (frozen original_size_bytes - 78) / 2 | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-clean | Opus 12k | decoded sample rate seen by ASR | info |  |  |  |  | INFO | [48000]. not stored in frozen outputs |
| errors | test-clean | Opus 12k | edit errors S+D+I (vs error_analysis.py) | exact | 50 | 50 |  | exact | PASS |  |
| errors | test-clean | Opus 12k | S/D/I split differences | info |  |  |  |  | INFO | 0 utterance(s). JiWER vs error_analysis.py back-trace tie-breaking; totals are the check |
| asr | test-clean | Opus 8k | sample | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 8k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 8k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 8k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 8k | reference | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 8k | prediction | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 8k | original_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 8k | compressed_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-clean | Opus 8k | wer (per utterance) | tolerance | 50 | 50 | 0 | abs <= 0 | PASS |  |
| asr | test-clean | Opus 8k | corpus WER over reproduced utterances | tolerance | 1 | 1 | 0 | abs <= 0 | PASS |  |
| bitrate | test-clean | Opus 8k | actual_bitrate_kbps | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| bitrate | test-clean | Opus 8k | compression_ratio | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| waveform | test-clean | Opus 8k | num_samples = (frozen original_size_bytes - 78) / 2 | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-clean | Opus 8k | decoded sample rate seen by ASR | info |  |  |  |  | INFO | [48000]. not stored in frozen outputs |
| errors | test-clean | Opus 8k | edit errors S+D+I (vs error_analysis.py) | exact | 50 | 50 |  | exact | PASS |  |
| errors | test-clean | Opus 8k | S/D/I split differences | info |  |  |  |  | INFO | 0 utterance(s). JiWER vs error_analysis.py back-trace tie-breaking; totals are the check |
| signal | test-clean | Opus 12k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 12k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 12k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 12k | estimated_delay_samples | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 12k | retained_bandwidth_hz | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 12k | spectral_distortion | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-clean | Opus 12k | lsd_db | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-clean | Opus 12k | hf_power_change_db | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-clean | Opus 12k | estimated_delay_ms | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| waveform | test-clean | Opus 12k | decoded length - reference length (16 kHz samples, min/max) | info |  |  |  |  | INFO | 0/0. not stored in frozen outputs |
| waveform | test-clean | Opus 12k | aligned length - reference length (min/max) | info |  |  |  |  | INFO | 0/0. not stored in frozen outputs |
| signal | test-clean | Opus 8k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 8k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 8k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 8k | estimated_delay_samples | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 8k | retained_bandwidth_hz | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-clean | Opus 8k | spectral_distortion | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-clean | Opus 8k | lsd_db | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-clean | Opus 8k | hf_power_change_db | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-clean | Opus 8k | estimated_delay_ms | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| waveform | test-clean | Opus 8k | decoded length - reference length (16 kHz samples, min/max) | info |  |  |  |  | INFO | 0/0. not stored in frozen outputs |
| waveform | test-clean | Opus 8k | aligned length - reference length (min/max) | info |  |  |  |  | INFO | -2/-2. not stored in frozen outputs |
| representation | test-clean | Opus 12k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| representation | test-clean | Opus 12k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| representation | test-clean | Opus 12k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-clean | Opus 12k | Wav2Vec2 frames: compressed - WAV (min/max) | info |  |  |  |  | INFO | 0/0. frozen code truncates to the shorter sequence |
| representation | test-clean | Opus 8k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| representation | test-clean | Opus 8k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| representation | test-clean | Opus 8k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-clean | Opus 8k | Wav2Vec2 frames: compressed - WAV (min/max) | info |  |  |  |  | INFO | 0/0. frozen code truncates to the shorter sequence |
| packets | test-clean | Opus 12k | TOC configuration packet counts (SILK-WB) | exact | 1 | 1 |  | exact | PASS | frozen table_opus_modes.csv covers the same 50 utterances |
| packets | test-clean | Opus 8k | TOC configuration packet counts (SILK-NB) | exact | 1 | 1 |  | exact | PASS | frozen table_opus_modes.csv covers the same 50 utterances |
| determinism | test-clean | WAV | wav_hidden_state_repeat_max_abs_diff | info |  |  |  |  | INFO | max 0 over 5 utterances. GPU run-to-run variation |
| determinism | test-clean | all | opus_12k_decoded_identical_across_encodes | exact | 50 | 50 |  | exact | PASS | independent encodes of the same utterance |
| determinism | test-clean | all | opus_12k_file_size_identical_across_encodes | exact | 50 | 50 |  | exact | PASS | independent encodes of the same utterance |
| determinism | test-clean | all | opus_8k_decoded_identical_across_encodes | exact | 50 | 50 |  | exact | PASS | independent encodes of the same utterance |
| determinism | test-clean | all | opus_8k_file_size_identical_across_encodes | exact | 50 | 50 |  | exact | PASS | independent encodes of the same utterance |
| selection | test-other | all | dataset_index (selection order) | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | sample | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | reference | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | prediction | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | original_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | compressed_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | WAV | wer (per utterance) | tolerance | 50 | 50 | 0 | abs <= 0 | PASS |  |
| asr | test-other | WAV | corpus WER over reproduced utterances | tolerance | 1 | 1 | 0 | abs <= 0 | PASS |  |
| bitrate | test-other | WAV | actual_bitrate_kbps | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| bitrate | test-other | WAV | compression_ratio | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| waveform | test-other | WAV | num_samples = (frozen original_size_bytes - 78) / 2 | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-other | WAV | decoded sample rate seen by ASR | info |  |  |  |  | INFO | [16000]. not stored in frozen outputs |
| errors | test-other | WAV | edit errors S+D+I (vs error_analysis.py) | exact | 50 | 50 |  | exact | PASS |  |
| errors | test-other | WAV | S/D/I split differences | info |  |  |  |  | INFO | 0 utterance(s). JiWER vs error_analysis.py back-trace tie-breaking; totals are the check |
| asr | test-other | Opus 12k | sample | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 12k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 12k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 12k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 12k | reference | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 12k | prediction | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 12k | original_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 12k | compressed_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 12k | wer (per utterance) | tolerance | 50 | 50 | 0 | abs <= 0 | PASS |  |
| asr | test-other | Opus 12k | corpus WER over reproduced utterances | tolerance | 1 | 1 | 0 | abs <= 0 | PASS |  |
| bitrate | test-other | Opus 12k | actual_bitrate_kbps | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| bitrate | test-other | Opus 12k | compression_ratio | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| waveform | test-other | Opus 12k | num_samples = (frozen original_size_bytes - 78) / 2 | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-other | Opus 12k | decoded sample rate seen by ASR | info |  |  |  |  | INFO | [48000]. not stored in frozen outputs |
| errors | test-other | Opus 12k | edit errors S+D+I (vs error_analysis.py) | exact | 50 | 50 |  | exact | PASS |  |
| errors | test-other | Opus 12k | S/D/I split differences | info |  |  |  |  | INFO | 0 utterance(s). JiWER vs error_analysis.py back-trace tie-breaking; totals are the check |
| asr | test-other | Opus 8k | sample | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 8k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 8k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 8k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 8k | reference | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 8k | prediction | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 8k | original_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 8k | compressed_size_bytes | exact | 50 | 50 |  | exact | PASS |  |
| asr | test-other | Opus 8k | wer (per utterance) | tolerance | 50 | 50 | 0 | abs <= 0 | PASS |  |
| asr | test-other | Opus 8k | corpus WER over reproduced utterances | tolerance | 1 | 1 | 0 | abs <= 0 | PASS |  |
| bitrate | test-other | Opus 8k | actual_bitrate_kbps | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| bitrate | test-other | Opus 8k | compression_ratio | tolerance | 50 | 50 | 0 | rel <= 1e-12 | PASS |  |
| waveform | test-other | Opus 8k | num_samples = (frozen original_size_bytes - 78) / 2 | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-other | Opus 8k | decoded sample rate seen by ASR | info |  |  |  |  | INFO | [48000]. not stored in frozen outputs |
| errors | test-other | Opus 8k | edit errors S+D+I (vs error_analysis.py) | exact | 50 | 50 |  | exact | PASS |  |
| errors | test-other | Opus 8k | S/D/I split differences | info |  |  |  |  | INFO | 0 utterance(s). JiWER vs error_analysis.py back-trace tie-breaking; totals are the check |
| signal | test-other | Opus 12k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 12k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 12k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 12k | estimated_delay_samples | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 12k | retained_bandwidth_hz | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 12k | spectral_distortion | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-other | Opus 12k | lsd_db | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-other | Opus 12k | hf_power_change_db | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-other | Opus 12k | estimated_delay_ms | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| waveform | test-other | Opus 12k | decoded length - reference length (16 kHz samples, min/max) | info |  |  |  |  | INFO | 0/0. not stored in frozen outputs |
| waveform | test-other | Opus 12k | aligned length - reference length (min/max) | info |  |  |  |  | INFO | 0/0. not stored in frozen outputs |
| signal | test-other | Opus 8k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 8k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 8k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 8k | estimated_delay_samples | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 8k | retained_bandwidth_hz | exact | 50 | 50 |  | exact | PASS |  |
| signal | test-other | Opus 8k | spectral_distortion | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-other | Opus 8k | lsd_db | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-other | Opus 8k | hf_power_change_db | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| signal | test-other | Opus 8k | estimated_delay_ms | tolerance | 50 | 50 | 0 | abs <= 1e-09 | PASS |  |
| waveform | test-other | Opus 8k | decoded length - reference length (16 kHz samples, min/max) | info |  |  |  |  | INFO | 0/0. not stored in frozen outputs |
| waveform | test-other | Opus 8k | aligned length - reference length (min/max) | info |  |  |  |  | INFO | -2/-2. not stored in frozen outputs |
| representation | test-other | Opus 12k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| representation | test-other | Opus 12k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| representation | test-other | Opus 12k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-other | Opus 12k | Wav2Vec2 frames: compressed - WAV (min/max) | info |  |  |  |  | INFO | 0/0. frozen code truncates to the shorter sequence |
| representation | test-other | Opus 8k | speaker_id | exact | 50 | 50 |  | exact | PASS |  |
| representation | test-other | Opus 8k | chapter_id | exact | 50 | 50 |  | exact | PASS |  |
| representation | test-other | Opus 8k | utterance_id | exact | 50 | 50 |  | exact | PASS |  |
| waveform | test-other | Opus 8k | Wav2Vec2 frames: compressed - WAV (min/max) | info |  |  |  |  | INFO | 0/0. frozen code truncates to the shorter sequence |
| packets | test-other | Opus 12k | TOC configuration packet counts | info |  |  |  |  | INFO | {'SILK-WB': 15924}. no frozen packet table for this subset/size |
| packets | test-other | Opus 8k | TOC configuration packet counts | info |  |  |  |  | INFO | {'SILK-NB': 15924}. no frozen packet table for this subset/size |
| determinism | test-other | WAV | wav_hidden_state_repeat_max_abs_diff | info |  |  |  |  | INFO | max 0 over 5 utterances. GPU run-to-run variation |
| determinism | test-other | all | opus_12k_decoded_identical_across_encodes | exact | 50 | 50 |  | exact | PASS | independent encodes of the same utterance |
| determinism | test-other | all | opus_12k_file_size_identical_across_encodes | exact | 50 | 50 |  | exact | PASS | independent encodes of the same utterance |
| determinism | test-other | all | opus_8k_decoded_identical_across_encodes | exact | 50 | 50 |  | exact | PASS | independent encodes of the same utterance |
| determinism | test-other | all | opus_8k_file_size_identical_across_encodes | exact | 50 | 50 |  | exact | PASS | independent encodes of the same utterance |
| frozen | all | all | src/ and results/ SHA-256 after run vs before | exact | 1 | 1 |  | exact | PASS | 111 files hashed |
| frozen | all | all | src/ and results/ SHA-256 at comparison time vs before | exact | 1 | 1 |  | exact | PASS | 111 files hashed |

## Representation drift, every stored layer

Aggregated over subsets and Opus conditions. Frozen values are stored with 6 significant digits; tolerance is that rounding plus 1e-05. Per-condition rows are in equivalence_report.csv.

| layer | kind | n | n_exact | max_abs_error | status |
|---|---|---|---|---|---|
| conv | raw | 200 | 0 | 4.99e-07 | PASS |
| layer_1 | raw | 200 | 0 | 4.98e-07 | PASS |
| layer_2 | raw | 200 | 0 | 4.97e-07 | PASS |
| layer_3 | raw | 200 | 0 | 4.95e-07 | PASS |
| layer_4 | raw | 200 | 0 | 4.98e-07 | PASS |
| layer_5 | raw | 200 | 0 | 4.91e-07 | PASS |
| layer_6 | raw | 200 | 0 | 4.96e-07 | PASS |
| layer_7 | raw | 200 | 0 | 4.88e-07 | PASS |
| layer_8 | raw | 200 | 0 | 4.95e-07 | PASS |
| layer_9 | raw | 200 | 0 | 4.9e-07 | PASS |
| layer_10 | raw | 200 | 0 | 4.97e-07 | PASS |
| layer_11 | raw | 200 | 0 | 4.82e-08 | PASS |
| layer_12 | raw | 200 | 0 | 3.5e-07 | PASS |
| conv | standardised | 200 | 0 | 4.99e-07 | PASS |
| layer_1 | standardised | 200 | 0 | 4.99e-07 | PASS |
| layer_2 | standardised | 200 | 0 | 4.99e-07 | PASS |
| layer_3 | standardised | 200 | 0 | 5e-07 | PASS |
| layer_4 | standardised | 200 | 0 | 4.98e-07 | PASS |
| layer_5 | standardised | 200 | 0 | 4.97e-07 | PASS |
| layer_6 | standardised | 200 | 0 | 4.88e-07 | PASS |
| layer_7 | standardised | 200 | 0 | 4.9e-07 | PASS |
| layer_8 | standardised | 200 | 0 | 5e-07 | PASS |
| layer_9 | standardised | 200 | 0 | 4.91e-07 | PASS |
| layer_10 | standardised | 200 | 0 | 4.95e-07 | PASS |
| layer_11 | standardised | 200 | 0 | 4.81e-07 | PASS |
| layer_12 | standardised | 200 | 0 | 4.99e-07 | PASS |
