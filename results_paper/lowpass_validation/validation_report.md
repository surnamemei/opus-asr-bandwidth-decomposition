# Stage 2B: matched bandwidth-removal control

**Verdict: FAIL** (10/13 gate evaluations passed; gate 7 = gates 1-6 on held-out dev-other with the frozen filter)

Definition: linear band-limiting component of Opus SILK-NB only (no spectral image, no coding distortion).

## Frozen filter

- taps SHA-256 `583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16`, 1023 taps
- design: {"sample_rate": 16000, "num_taps": 1023, "delay_removed_samples": 511, "kaiser_beta": 8.0, "design_grid": 16384, "level_band_hz": [500.0, 2000.0], "passband_deviation_db": 0.5, "passband_edge_hz": 3000.0, "stopband_floor_db": -80.0, "correction_iterations": 3, "correction_floor_db": -50.0, "analysis": {"n_fft": 512, "win_length": 400, "hop_length": 160, "window": "hann"}}
- calibration: dev-clean, 40 utterances, 348 s
- reference: {"bitrates": [24000, 32000, 40000], "bitrate_used": 40000, "signal": "voice", "other_settings": "Stage 2A EncoderSettings defaults, forced NB", "packet_configurations": {"24000": {"SILK-NB": 17442}, "32000": {"SILK-NB": 17442}, "40000": {"SILK-NB": 17442}}, "convergence": {"max_abs_h1_diff_24k_vs_40k_db_up_to_4150hz": 1.9622866478558763, "max_abs_h1_diff_32k_vs_40k_db_up_to_4150hz": 0.8252086608651226}, "libopus": "libopus 1.4"}

Correction iterations (LP measured vs target, dev-clean):

| iteration | rms_error_db_3000_4200 | max_abs_error_db_3000_4150 |
|---|---|---|
| 0 | 0.12 | 0.62 |
| 1 | 0.0508 | 0.275 |
| 2 | 0.0512 | 0.196 |
| 3 | 0.052 | 0.162 |

## Tolerances (declared before validation; SHA-256 `bc91d298ac402bbed082dfd71de0ec4dc15d0c1419261a7fdac6ca6a88c49833` stored at calibration)

```json
{
 "g1_max_abs_lag_samples": 0,
 "g3_lsd_0_3k_median_max_db": 0.5,
 "g3_lsd_0_3k_p95_max_db": 1.0,
 "g3_lsd_0_4k_ratio_to_opus8nb_max": 0.4,
 "g3_min_coherence_up_to_hz": 3800.0,
 "g3_min_coherence": 0.99,
 "g4_coherent_bw_threshold_db": -20.0,
 "g4_coherent_bw_vs_reference_max_hz": 62.5,
 "g4_coherent_bw_vs_opus8nb_max_hz": 125.0,
 "g4_retained_bw_median_range_hz": [
  3950.0,
  4200.0
 ],
 "g5_coherent_hf_vs_reference_max_db": 3.0,
 "g5_coherent_hf_vs_opus8nb_max_db": 6.0,
 "g6_h1_rms_band_hz": [
  3000.0,
  4200.0
 ],
 "g6_h1_rms_max_db": 1.5,
 "g6_h1_abs_band_hz": [
  3000.0,
  4150.0
 ],
 "g6_h1_abs_max_db": 4.0,
 "g6_stopband_from_hz": 4200.0,
 "g6_stopband_max_db": -25.0
}
```

## Gates

| subset | gate | name | status | evidence |
|---|---|---|---|---|
| dev-clean | 1 | zero effective delay | PASS | odd, exactly symmetric taps with (L-1)/2 = 511 samples removed: True; alignment lag 0 in 40/40 |
| dev-clean | 2 | waveform length unchanged | PASS | 40/40 utterances; deterministic 40/40 |
| dev-clean | 3 | low-band distortion small (bandwidth removal only) | PASS | LSD 0-3 kHz median 0.029 dB, p95 0.039 dB; LSD 0-4 kHz median 1.44 dB = 22.5% of Opus8-NB (6.39 dB); min coherence 0-3800 Hz 0.9991 (Opus8-NB 0.186) |
| dev-clean | 4 | bandwidth matches SILK-NB (coherent definition) | PASS | coherent bandwidth LP 4093.8 Hz, reference 4093.8 (+0.0), Opus8-NB 4031.2 (+62.5); power-based retained bandwidth median LP 4093.8 Hz (range 3950-4200; Opus8-NB 4562.5 includes the image) |
| dev-clean | 5 | 4-8 kHz attenuation matches SILK-NB (coherent definition) | FAIL | coherent 4-8 kHz power LP -25.2 dB, reference -25.3 (+0.1), Opus8-NB -34.6 (+9.4); total 4-8 kHz power change median LP -24.9 dB <= Opus8-NB -17.1 dB (difference = image, mirror coherence 4.1-4.9 kHz Opus8-NB 0.23, LP 0.001) |
| dev-clean | 6 | transition shape matches SILK-NB linear response | PASS | \|H1\| LP - reference: RMS 0.05 dB over [3000.0, 4200.0] Hz, max 0.16 dB over [3000.0, 4150.0] Hz; LP \|H1\| above 4200 Hz <= -26.8 dB |
| dev-other | 1 | zero effective delay | PASS | odd, exactly symmetric taps with (L-1)/2 = 511 samples removed: True; alignment lag 0 in 33/33 |
| dev-other | 2 | waveform length unchanged | PASS | 33/33 utterances; deterministic 33/33 |
| dev-other | 3 | low-band distortion small (bandwidth removal only) | PASS | LSD 0-3 kHz median 0.029 dB, p95 0.037 dB; LSD 0-4 kHz median 1.40 dB = 22.2% of Opus8-NB (6.28 dB); min coherence 0-3800 Hz 0.9991 (Opus8-NB 0.161) |
| dev-other | 4 | bandwidth matches SILK-NB (coherent definition) | PASS | coherent bandwidth LP 4093.8 Hz, reference 4093.8 (+0.0), Opus8-NB 4031.2 (+62.5); power-based retained bandwidth median LP 4093.8 Hz (range 3950-4200; Opus8-NB 4656.2 includes the image) |
| dev-other | 5 | 4-8 kHz attenuation matches SILK-NB (coherent definition) | FAIL | coherent 4-8 kHz power LP -25.2 dB, reference -25.7 (+0.5), Opus8-NB -33.9 (+8.7); total 4-8 kHz power change median LP -24.3 dB <= Opus8-NB -16.8 dB (difference = image, mirror coherence 4.1-4.9 kHz Opus8-NB 0.21, LP 0.001) |
| dev-other | 6 | transition shape matches SILK-NB linear response | PASS | \|H1\| LP - reference: RMS 0.60 dB over [3000.0, 4200.0] Hz, max 1.04 dB over [3000.0, 4150.0] Hz; LP \|H1\| above 4200 Hz <= -26.5 dB |
| dev-other | 7 | same frozen filter passes gates 1-6 on held-out dev-other | FAIL | taps SHA-256 583c66a169d31e27..., no retuning; 5/6 passed |

## Per-cell summary

| subset | cell | utterances | lag_samples | length_equal | retained_bandwidth_hz_median | lsd_db_median | lsd_0_3k_db_median | lsd_0_4k_db_median | lsd_4_8k_db_median | hf_power_change_db_median | coherent_bandwidth_hz | coherent_hf_power_db | total_hf_power_db | image_coherence_4100_4900 | h1_level_db | packets |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dev-clean | lp | 40 | {"0": 40} | 40/40 | 4.09e+03 | 8.96 | 0.0294 | 1.44 | 12.5 | -24.9 | 4.09e+03 | -25.2 | -25.1 | 0.00062 | 2.61e-07 |  |
| dev-clean | opus_8k_nb | 40 | {"2": 39, "1": 1} | 40/40 | 4.56e+03 | 9.87 | 6.04 | 6.39 | 11.8 | -17.1 | 4.03e+03 | -34.6 | -16.7 | 0.226 | -1.71 | {"SILK-NB": 17442} |
| dev-clean | opus_12k_nb | 40 | {"2": 40} | 40/40 | 4.56e+03 | 9.54 | 4.87 | 5.47 | 11.9 | -18.4 | 4.03e+03 | -31.1 | -18.2 | 0.541 | -0.826 | {"SILK-NB": 17442} |
| dev-clean | silk_nb_linear_ref | 40 | {"2": 40} | 40/40 | 4.67e+03 | 8.61 | 1.29 | 2.04 | 11.8 | -15.5 | 4.09e+03 | -25.3 | -16 | 0.971 | -0.0668 | {"SILK-NB": 17442} |
| dev-other | lp | 33 | {"0": 33} | 33/33 | 4.09e+03 | 8.91 | 0.029 | 1.4 | 12.5 | -24.3 | 4.09e+03 | -25.2 | -25 | 0.000609 | 3.13e-07 |  |
| dev-other | opus_8k_nb | 33 | {"2": 33} | 33/33 | 4.66e+03 | 9.82 | 6.05 | 6.28 | 11.6 | -16.8 | 4.03e+03 | -33.9 | -16.4 | 0.215 | -1.97 | {"SILK-NB": 11821} |
| dev-other | opus_12k_nb | 33 | {"2": 33} | 33/33 | 4.56e+03 | 9.57 | 4.83 | 5.44 | 11.7 | -18.1 | 4.03e+03 | -31.7 | -17.8 | 0.507 | -0.955 | {"SILK-NB": 11821} |
| dev-other | silk_nb_linear_ref | 33 | {"2": 33} | 33/33 | 4.66e+03 | 8.42 | 1.3 | 2.15 | 11.6 | -15.8 | 4.09e+03 | -25.7 | -15.7 | 0.969 | -0.076 | {"SILK-NB": 11821} |

## Linear transfer |H1| relative to the 0.5-2 kHz level (dB)

| subset | frequency_hz | lp | opus_12k_nb | opus_8k_nb | silk_nb_linear_ref |
|---|---|---|---|---|---|
| dev-clean | 1e+03 | -1.97e-09 | 0.193 | 0.272 | -0.0164 |
| dev-clean | 2e+03 | -8.29e-07 | -0.115 | -0.289 | -0.0218 |
| dev-clean | 3e+03 | -0.529 | -3.42 | -4.81 | -0.534 |
| dev-clean | 3.5e+03 | -2.17 | -6.55 | -8.85 | -2.17 |
| dev-clean | 3.75e+03 | -3.82 | -8.03 | -10.5 | -3.82 |
| dev-clean | 3.88e+03 | -5.62 | -10.5 | -11.6 | -5.61 |
| dev-clean | 4e+03 | -10.6 | -15.7 | -17.5 | -10.7 |
| dev-clean | 4.06e+03 | -15.6 | -20.5 | -25.7 | -15.5 |
| dev-clean | 4.12e+03 | -20.9 | -26 | -29.5 | -20.8 |
| dev-clean | 4.25e+03 | -30.3 | -37.8 | -41.9 | -30.4 |
| dev-clean | 4.5e+03 | -55.1 | -44.2 | -50.9 | -45.6 |
| dev-clean | 5e+03 | -76.7 | -73.8 | -80.8 | -76.7 |
| dev-clean | 6e+03 | -80 | -134 | -137 | -146 |
| dev-clean | 7e+03 | -80 | -132 | -132 | -131 |
| dev-other | 1e+03 | -6.4e-09 | 0.285 | 0.298 | -0.0164 |
| dev-other | 2e+03 | -2.48e-07 | -1.12 | -1.55 | -0.134 |
| dev-other | 3e+03 | -0.513 | -3.64 | -5.3 | -0.642 |
| dev-other | 3.5e+03 | -2.16 | -6.03 | -8.06 | -2.16 |
| dev-other | 3.75e+03 | -3.8 | -8.79 | -11.5 | -3.95 |
| dev-other | 3.88e+03 | -5.61 | -11.2 | -13.3 | -5.77 |
| dev-other | 4e+03 | -10.7 | -15.7 | -16.7 | -11 |
| dev-other | 4.06e+03 | -15.5 | -21.8 | -23.5 | -15.9 |
| dev-other | 4.12e+03 | -20.9 | -26 | -30.2 | -21.7 |
| dev-other | 4.25e+03 | -29.8 | -35.5 | -40.3 | -30.8 |
| dev-other | 4.5e+03 | -55 | -45.5 | -48.3 | -50 |
| dev-other | 5e+03 | -76.7 | -83.6 | -77.2 | -85.9 |
| dev-other | 6e+03 | -80 | -134 | -125 | -137 |
| dev-other | 7e+03 | -80 | -132 | -128 | -131 |

## Long-term power ratio (dB)

| subset | frequency_hz | lp | opus_12k_nb | opus_8k_nb | silk_nb_linear_ref |
|---|---|---|---|---|---|
| dev-clean | 1e+03 | 2.62e-07 | -0.452 | -0.738 | -0.0801 |
| dev-clean | 2e+03 | -5.56e-07 | -0.295 | -0.101 | -0.0753 |
| dev-clean | 3e+03 | -0.526 | -2.2 | -1.45 | -0.551 |
| dev-clean | 3.5e+03 | -2.17 | -4.43 | -3.74 | -2.17 |
| dev-clean | 3.75e+03 | -3.82 | -6.06 | -5.36 | -3.77 |
| dev-clean | 3.88e+03 | -5.6 | -7.51 | -5.86 | -5.29 |
| dev-clean | 4e+03 | -10.5 | -9.35 | -7.01 | -7.62 |
| dev-clean | 4.06e+03 | -15.4 | -10.3 | -8.76 | -7.94 |
| dev-clean | 4.12e+03 | -20.8 | -10.7 | -9.06 | -8.53 |
| dev-clean | 4.25e+03 | -29.7 | -13.3 | -12.5 | -10.9 |
| dev-clean | 4.5e+03 | -54.9 | -18.4 | -17.7 | -16.1 |
| dev-clean | 5e+03 | -70.1 | -37 | -36.2 | -35.3 |
| dev-clean | 6e+03 | -71.3 | -75.8 | -77.6 | -75.1 |
| dev-clean | 7e+03 | -72.5 | -78.6 | -80.3 | -77.3 |
| dev-other | 1e+03 | 3.11e-07 | -0.405 | -0.836 | -0.0882 |
| dev-other | 2e+03 | 9.22e-08 | -1.07 | -0.831 | -0.188 |
| dev-other | 3e+03 | -0.51 | -2.54 | -2.23 | -0.662 |
| dev-other | 3.5e+03 | -2.16 | -4.22 | -3.26 | -2.15 |
| dev-other | 3.75e+03 | -3.8 | -6.52 | -5.57 | -3.91 |
| dev-other | 3.88e+03 | -5.59 | -7.77 | -6.55 | -5.47 |
| dev-other | 4e+03 | -10.6 | -9.17 | -7.14 | -7.89 |
| dev-other | 4.06e+03 | -15.2 | -10.2 | -8.26 | -8.27 |
| dev-other | 4.12e+03 | -20.8 | -10.3 | -9.04 | -8.07 |
| dev-other | 4.25e+03 | -29.2 | -12 | -11 | -9.38 |
| dev-other | 4.5e+03 | -54.7 | -18.3 | -17.3 | -16.2 |
| dev-other | 5e+03 | -66.9 | -37.3 | -37 | -35.5 |
| dev-other | 6e+03 | -67.1 | -72.3 | -74.2 | -70 |
| dev-other | 7e+03 | -66.2 | -71.6 | -73.3 | -69.3 |

## Mean D(f) (dB, frozen definition)

| subset | frequency_hz | lp | opus_12k_nb | opus_8k_nb | silk_nb_linear_ref |
|---|---|---|---|---|---|
| dev-clean | 1e+03 | 0.000984 | 3.08 | 4.36 | 0.557 |
| dev-clean | 2e+03 | 0.000612 | 4.02 | 4.86 | 0.875 |
| dev-clean | 3e+03 | 0.484 | 4.44 | 5.04 | 1.22 |
| dev-clean | 3.5e+03 | 1.78 | 4.94 | 5.24 | 2.1 |
| dev-clean | 3.75e+03 | 3.04 | 5.79 | 5.78 | 3.34 |
| dev-clean | 3.88e+03 | 4.35 | 6.46 | 6.23 | 4.46 |
| dev-clean | 4e+03 | 7.65 | 8.7 | 8.21 | 7.44 |
| dev-clean | 4.06e+03 | 10.1 | 8 | 7.52 | 7 |
| dev-clean | 4.12e+03 | 12.5 | 8.5 | 8.08 | 7.54 |
| dev-clean | 4.25e+03 | 14.6 | 9.34 | 8.94 | 8.67 |
| dev-clean | 4.5e+03 | 15.1 | 10.5 | 10.2 | 10 |
| dev-clean | 5e+03 | 13.3 | 12.7 | 12.7 | 12.5 |
| dev-clean | 6e+03 | 11 | 11 | 11 | 11 |
| dev-clean | 7e+03 | 10.1 | 10.1 | 10.1 | 10.1 |
| dev-other | 1e+03 | 0.000457 | 3.22 | 4.5 | 0.57 |
| dev-other | 2e+03 | 0.00122 | 4.1 | 4.98 | 0.889 |
| dev-other | 3e+03 | 0.465 | 4.47 | 4.93 | 1.24 |
| dev-other | 3.5e+03 | 1.71 | 4.85 | 5.05 | 2.09 |
| dev-other | 3.75e+03 | 2.93 | 5.68 | 5.69 | 3.25 |
| dev-other | 3.88e+03 | 4.18 | 6.31 | 6 | 4.38 |
| dev-other | 4e+03 | 7.32 | 8.37 | 7.81 | 7.14 |
| dev-other | 4.06e+03 | 9.85 | 7.87 | 7.4 | 6.9 |
| dev-other | 4.12e+03 | 12.1 | 8.18 | 7.72 | 7.28 |
| dev-other | 4.25e+03 | 14.1 | 8.89 | 8.49 | 8.27 |
| dev-other | 4.5e+03 | 15.1 | 10.4 | 9.98 | 9.89 |
| dev-other | 5e+03 | 13.2 | 12.8 | 12.7 | 12.6 |
| dev-other | 6e+03 | 10.7 | 10.7 | 10.7 | 10.7 |
| dev-other | 7e+03 | 8.96 | 8.97 | 8.97 | 8.97 |

## Mirror coherence (output at f vs input at 8000 - f)

| subset | frequency_hz | lp | opus_12k_nb | opus_8k_nb | silk_nb_linear_ref |
|---|---|---|---|---|---|
| dev-clean | 1e+03 | 1.46e-05 | 1.23e-05 | 1.1e-05 | 1.49e-05 |
| dev-clean | 2e+03 | 5.17e-06 | 1.54e-05 | 2.42e-06 | 5.57e-06 |
| dev-clean | 3e+03 | 9.11e-05 | 0.000258 | 5.04e-05 | 8.68e-05 |
| dev-clean | 3.5e+03 | 0.00112 | 0.00211 | 0.000247 | 0.00107 |
| dev-clean | 3.75e+03 | 0.00123 | 0.0027 | 0.000731 | 0.0105 |
| dev-clean | 3.88e+03 | 0.000136 | 0.0237 | 0.00629 | 0.0558 |
| dev-clean | 4e+03 | 0.00305 | 0.189 | 0.0587 | 0.471 |
| dev-clean | 4.06e+03 | 0.000961 | 0.357 | 0.151 | 0.785 |
| dev-clean | 4.12e+03 | 0.000197 | 0.413 | 0.179 | 0.912 |
| dev-clean | 4.25e+03 | 0.00212 | 0.529 | 0.207 | 0.97 |
| dev-clean | 4.5e+03 | 0.00103 | 0.506 | 0.207 | 0.979 |
| dev-clean | 5e+03 | 1.38e-05 | 0.612 | 0.302 | 0.964 |
| dev-clean | 6e+03 | 7.21e-08 | 0.135 | 0.158 | 0.139 |
| dev-clean | 7e+03 | 2.31e-06 | 0.252 | 0.296 | 0.213 |
| dev-other | 1e+03 | 8.08e-06 | 4.31e-06 | 1.35e-05 | 7.15e-06 |
| dev-other | 2e+03 | 3.87e-07 | 1.46e-06 | 3.49e-05 | 1.28e-06 |
| dev-other | 3e+03 | 1.09e-06 | 1.2e-05 | 6.12e-05 | 5.89e-06 |
| dev-other | 3.5e+03 | 0.000561 | 0.00148 | 0.000512 | 0.000381 |
| dev-other | 3.75e+03 | 0.00167 | 0.00356 | 0.000781 | 0.00699 |
| dev-other | 3.88e+03 | 8.62e-05 | 0.0215 | 0.00495 | 0.0416 |
| dev-other | 4e+03 | 0.000971 | 0.171 | 0.069 | 0.473 |
| dev-other | 4.06e+03 | 1e-05 | 0.294 | 0.108 | 0.774 |
| dev-other | 4.12e+03 | 0.000226 | 0.359 | 0.134 | 0.919 |
| dev-other | 4.25e+03 | 0.00119 | 0.473 | 0.159 | 0.97 |
| dev-other | 4.5e+03 | 0.000465 | 0.524 | 0.208 | 0.974 |
| dev-other | 5e+03 | 3.09e-06 | 0.597 | 0.3 | 0.962 |
| dev-other | 6e+03 | 1.12e-08 | 0.0352 | 0.039 | 0.0324 |
| dev-other | 7e+03 | 2.42e-07 | 0.0946 | 0.11 | 0.0635 |
