# Stage 2A: direct-libopus validation (dev-clean)

**Verdict: PASS** (7/7 gates passed)

Data: 40 dev-clean utterances, one per speaker (seed 5305), 348 s.

## Gates

| gate | name | status | evidence |
|---|---|---|---|
| 1 | forced 8 kbps WB reliable on every utterance | PASS | 40/40 files 100% WB; 17442/17442 packets WB |
| 2 | every packet of every cell in the requested bandwidth | PASS | opus_12k_wb: 1.0000; opus_12k_nb: 1.0000; opus_8k_wb: 1.0000; opus_8k_nb: 1.0000 |
| 3 | WB and NB measured bitrate comparable at each nominal rate (aggregate and median gap <= 5%) | PASS | 12k measured: aggregate gap 1.05%, median \|gap\| 1.18%; 12k payload: aggregate gap 1.05%, median \|gap\| 1.18%; 8k measured: aggregate gap 4.14%, median \|gap\| 4.12%; 8k payload: aggregate gap 4.14%, median \|gap\| 4.12% |
| 4 | all cells decode through the frozen torchaudio.load path | PASS | decoded rate [np.int64(48000)]; Ogg packet round trip 160/160; TOC parsers agree 160/160 |
| 5 | decoded length, trimming, alignment understood and reproducible | PASS | decoded 48k length = 3N in 160/160; re-encode identical 160/160; pre-skip [np.int64(312)]; lags by cell opus_12k_wb {"0": 40}; opus_12k_nb {"2": 40}; opus_8k_wb {"0": 40}; opus_8k_nb {"2": 39, "1": 1} |
| 6 | WB vs NB spectral difference measurable | PASS | 12k: median WB-NB retained bandwidth 3438 Hz (40/40 utterances >= 2000), 4-8 kHz power 16.9 dB (40/40 >= 6); 8k: median WB-NB retained bandwidth 3438 Hz (40/40 utterances >= 2000), 4-8 kHz power 18.8 dB (40/40 >= 6) |
| 7 | no hidden encoder difference between cells except bitrate and bandwidth | PASS | differing settings/queries beyond bitrate and bandwidth: none; coding mode SILK in all packets of all cells: True; all packets single-frame without padding (payload = coded bits): True |

## Encoder settings (identical in all cells except bitrate and bandwidth)

```json
{
  "common_settings": {
    "max_bandwidth": "FB",
    "sample_rate": 16000,
    "channels": 1,
    "application": "audio",
    "vbr": true,
    "vbr_constraint": false,
    "complexity": 10,
    "frame_ms": 20.0,
    "signal": "auto",
    "packet_loss_perc": 0,
    "inband_fec": false,
    "dtx": false,
    "lsb_depth": 24,
    "prediction_disabled": false,
    "expert_frame_duration": "arg",
    "force_channels": "auto"
  },
  "frame_samples": 320,
  "ctl_order": [
    "complexity",
    "vbr",
    "vbr_constraint",
    "bitrate",
    "max_bandwidth",
    "bandwidth",
    "signal",
    "packet_loss_perc",
    "inband_fec",
    "dtx",
    "lsb_depth",
    "prediction_disabled",
    "expert_frame_duration",
    "force_channels"
  ],
  "input_format": "int16 PCM via opus_encode (exact; source is 16-bit FLAC)",
  "cells": [
    {
      "cell": "opus_12k_wb",
      "bitrate_bps": 12000,
      "bandwidth": "WB"
    },
    {
      "cell": "opus_12k_nb",
      "bitrate_bps": 12000,
      "bandwidth": "NB"
    },
    {
      "cell": "opus_8k_wb",
      "bitrate_bps": 8000,
      "bandwidth": "WB"
    },
    {
      "cell": "opus_8k_nb",
      "bitrate_bps": 8000,
      "bandwidth": "NB"
    }
  ],
  "ogg": {
    "serial": 1346457682,
    "packets_per_page": 50,
    "opus_tags_comments": [
      "ENCODER=paper/opus_direct.py"
    ]
  },
  "libopus": "libopus 1.4"
}
```

## Packet configurations

| cell | files | packets | packet_configurations | share_requested_bandwidth |
|---|---|---|---|---|
| opus_12k_wb | 40 | 17442 | {"SILK-WB": 17442} | 1 |
| opus_12k_nb | 40 | 17442 | {"SILK-NB": 17442} | 1 |
| opus_8k_wb | 40 | 17442 | {"SILK-WB": 17442} | 1 |
| opus_8k_nb | 40 | 17442 | {"SILK-NB": 17442} | 1 |

## Measured bitrate (kbps; measured = file size, frozen definition)

| cell | files | aggregate_measured_kbps | aggregate_payload_kbps | measured_bitrate_kbps_mean | measured_bitrate_kbps_sd | measured_bitrate_kbps_min | measured_bitrate_kbps_median | measured_bitrate_kbps_max |
|---|---|---|---|---|---|---|---|---|
| opus_12k_wb | 40 | 12.3 | 11.6 | 12.3 | 0.322 | 11 | 12.4 | 12.9 |
| opus_12k_nb | 40 | 12.2 | 11.4 | 12.2 | 0.341 | 10.8 | 12.3 | 12.8 |
| opus_8k_wb | 40 | 8.52 | 7.77 | 8.57 | 0.224 | 7.8 | 8.58 | 9.07 |
| opus_8k_nb | 40 | 8.19 | 7.44 | 8.22 | 0.286 | 7.12 | 8.24 | 8.77 |

Paired WB - NB gap, % of nominal:

| nominal_kbps | bitrate | gap_pct_mean | gap_pct_sd | gap_pct_min | gap_pct_p05 | gap_pct_median | gap_pct_p95 | gap_pct_max |
|---|---|---|---|---|---|---|---|---|
| 12 | measured | 1.15 | 1.12 | -1.26 | -0.832 | 1.16 | 3.29 | 4.2 |
| 12 | payload | 1.15 | 1.12 | -1.26 | -0.832 | 1.16 | 3.29 | 4.2 |
| 8 | measured | 4.47 | 1.89 | 1.83 | 2.46 | 4.12 | 8.51 | 10.6 |
| 8 | payload | 4.47 | 1.89 | 1.83 | 2.46 | 4.12 | 8.51 | 10.6 |

## Signal level (medians over utterances)

| cell | lsd_db_median | lsd_0_4k_db_median | lsd_4_8k_db_median | retained_bandwidth_hz_median | hf_power_change_db_median |
|---|---|---|---|---|---|
| opus_12k_wb | 5.69 | 5.39 | 5.68 | 8e+03 | -1.51 |
| opus_12k_nb | 9.54 | 5.47 | 11.9 | 4.56e+03 | -18.4 |
| opus_8k_wb | 6.6 | 6.82 | 6.2 | 8e+03 | 1.98 |
| opus_8k_nb | 9.87 | 6.39 | 11.8 | 4.56e+03 | -17.1 |

## Alignment and trimming

| cell | lags |
|---|---|
| opus_12k_wb | {"0": 40} |
| opus_12k_nb | {"2": 40} |
| opus_8k_wb | {"0": 40} |
| opus_8k_nb | {"2": 39, "1": 1} |

Lookahead [np.int64(104)] samples at 16 kHz, pre-skip [np.int64(312)] at 48 kHz, end trim 168-888 samples at 48 kHz; decoded length equals 3 x input length for 160/160 files.

## Diagnostics: link to the frozen ffmpeg encoder

| nominal_bitrate_kbps | utterances | auto_equals_ffmpeg | forced_equals_auto | forced_cell |
|---|---|---|---|---|
| 8 | 40 | 40 | 40 | opus_8k_nb |
| 12 | 40 | 40 | 40 | opus_12k_wb |

## Diagnostic: bitrate mode and the WB vs NB bitrate gap

The design uses unconstrained VBR (the frozen setting). Constrained VBR and CBR are shown only to judge whether a controlled bitrate mode is needed; payload bitrate excludes Ogg overhead.

| bitrate_mode | nominal_kbps | wb_payload_kbps | nb_payload_kbps | aggregate_gap_pct | median_gap_pct | max_abs_gap_pct | wb_unpadded_kbps | nb_unpadded_kbps | unpadded_median_gap_pct | share_padded_packets | min_share_requested_bandwidth | all_packets_silk | wb_lsd_0_4k_median | nb_lsd_0_4k_median | wb_lsd_median | nb_lsd_median |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| vbr | 12 | 11.6 | 11.4 | 1.05 | 1.16 | 4.2 | 11.6 | 11.4 | 1.16 | 0 | 1 | True | 5.39 | 5.47 | 5.69 | 9.54 |
| vbr | 8 | 7.77 | 7.44 | 4.14 | 4.12 | 10.6 | 7.77 | 7.44 | 4.12 | 0 | 1 | True | 6.82 | 6.39 | 6.6 | 9.87 |
| cvbr | 12 | 11.6 | 11.4 | 1.05 | 1.16 | 4.2 | 11.6 | 11.4 | 1.16 | 0 | 1 | True | 5.39 | 5.47 | 5.69 | 9.54 |
| cvbr | 8 | 7.77 | 7.44 | 4.14 | 4.12 | 10.6 | 7.77 | 7.44 | 4.12 | 0 | 1 | True | 6.82 | 6.39 | 6.6 | 9.87 |
| cbr | 12 | 12 | 12 | 0 | 0 | 0 | 11.5 | 11.6 | -1.26 | 0.579 | 1 | True | 5.47 | 5.48 | 5.72 | 9.55 |
| cbr | 8 | 8.02 | 8.02 | 0 | 0 | 0 | 7.61 | 7.7 | -1.05 | 0.511 | 1 | True | 7.06 | 6.37 | 6.86 | 9.89 |
