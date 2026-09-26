# Stage 2B confirmation: revised Gate 5 on unseen train-clean-100 speakers

**Verdict under the revised specification: PASS**

## 1. Original Stage 2B result (unchanged, historical)

Original verdict: **FAIL** (results_paper/lowpass_validation/validation_report.md).

| subset | gate | status |
|---|---|---|
| dev-clean | 1 | PASS |
| dev-clean | 2 | PASS |
| dev-clean | 3 | PASS |
| dev-clean | 4 | PASS |
| dev-clean | 5 | FAIL |
| dev-clean | 6 | PASS |
| dev-other | 1 | PASS |
| dev-other | 2 | PASS |
| dev-other | 3 | PASS |
| dev-other | 4 | PASS |
| dev-other | 5 | FAIL |
| dev-other | 6 | PASS |
| dev-other | 7 | FAIL |

## 2. Why the original Gate 5 was inconsistent with the linear-only definition

The control is defined as SILK-NB's linear band-limiting component only. Opus8-NB's coherent 4-8 kHz power additionally contains bitrate-dependent in-band coding droop across the 4 kHz edge (dev-clean: linear reference -25.3 dB, Opus12-NB -31.1 dB, Opus8-NB -34.6 dB; |H1| at 3.5-4.25 kHz 5-11 dB below the linear chain at 8 kbps), which the definition excludes.

## 3. Revised criterion (frozen before the confirmation data were on disk)

- spec SHA-256 `166f5672263373ece22a955baf3b2e1f3c7ac7c9ce14098f9daa65938d9055ff`, created 2026-09-26T06:02:50.716156+00:00
- selection SHA-256 `0dfc09813d018c3f5026da7723cec3222fe14c957289f126e6aa3108e9932212`, created 2026-09-26T06:16:38.949193+00:00
- removed tolerance: ['g5_coherent_hf_vs_opus8nb_max_db'] (|coherent 4-8 kHz power (LP) - coherent 4-8 kHz power (Opus8-NB)| <= 6.0 dB; Opus8-NB coherent 4-8 kHz power is reported as information only)
- revised Gate 5 criterion: |coherent 4-8 kHz power (LP) - coherent 4-8 kHz power (SILK-NB linear reference, same utterances)| <= g5_coherent_hf_vs_reference_max_db (3.0 dB, unchanged)
- revised Gate 5 criterion: median total 4-8 kHz power change (LP) <= median total 4-8 kHz power change (Opus8-NB) (unchanged)
- unchanged: filter taps (frozen_filter.json), calibration procedure, encoder settings of every cell, gates 1, 2, 3, 4, 6 and their tolerances, Gate 5 reference tolerance (3.0 dB)

## 4. Confirmation set

- train-clean-100, 40 speakers (20 F, 20 M), one utterance each, seed 5305
- speaker rule: random.Random(5305).sample of 20 female then 20 male speakers from the sorted train-clean-100 IDs in SPEAKERS.TXT
- utterance rule: For each selected speaker in ascending numeric ID order, list every <speaker>/<chapter>/*.flac file of train-clean-100, sort the file names, and pick one with random.Random(5305).choice (one generator shared across speakers, in that order). File names only; no audio or transcript is read during selection.

## 5. Provenance checks before the run

| check | result |
|---|---|
| selection made under this spec | True |
| filter taps unchanged | True |
| original tolerances unchanged | True |
| revised tolerances in code = frozen spec | True |
| encoder settings unchanged | True |
| original Stage 2B outputs and code unchanged | True |

Filter taps SHA-256: `583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16` (frozen at Stage 2B calibration).

## 6. Gates on the confirmation set

| subset | gate | name | status | evidence |
|---|---|---|---|---|
| train-clean-100 | 1 | zero effective delay | PASS | odd, exactly symmetric taps with (L-1)/2 = 511 samples removed: True; alignment lag 0 in 40/40 |
| train-clean-100 | 2 | waveform length unchanged | PASS | 40/40 utterances; deterministic 40/40 |
| train-clean-100 | 3 | low-band distortion small (bandwidth removal only) | PASS | LSD 0-3 kHz median 0.031 dB, p95 0.037 dB; LSD 0-4 kHz median 1.37 dB = 21.7% of Opus8-NB (6.32 dB); min coherence 0-3800 Hz 0.9992 (Opus8-NB 0.168) |
| train-clean-100 | 4 | bandwidth matches SILK-NB (coherent definition) | PASS | coherent bandwidth LP 4093.8 Hz, reference 4125.0 (-31.2), Opus8-NB 4031.2 (+62.5); power-based retained bandwidth median LP 4093.8 Hz (range 3950-4200; Opus8-NB 4625.0 includes the image) |
| train-clean-100 | 5 (revised) | 4-8 kHz attenuation matches SILK-NB's linear (bitrate-independent) response | PASS | coherent 4-8 kHz power LP -24.7 dB, linear reference -24.9 dB (+0.2, tolerance +-3.0); total 4-8 kHz power change median LP -24.6 dB <= Opus8-NB -16.6 dB: True; information only: Opus8-NB coherent 4-8 kHz power -32.5 dB (+7.8) |
| train-clean-100 | 6 | transition shape matches SILK-NB linear response | PASS | \|H1\| LP - reference: RMS 0.57 dB over [3000.0, 4200.0] Hz, max 1.35 dB over [3000.0, 4150.0] Hz; LP \|H1\| above 4200 Hz <= -26.9 dB |
| train-clean-100 | 7 (confirmatory) | frozen filter passes gates 1-4, 5 (revised), 6 on unseen speakers | PASS | taps SHA-256 583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16; 6/6 passed |

Original Gate 5 evaluated on the same data (information only, not part of the revised verdict):

| gate | status | evidence |
|---|---|---|
| 5 (original, information only) | FAIL | coherent 4-8 kHz power LP -24.7 dB, reference -24.9 (+0.2), Opus8-NB -32.5 (+7.8); total 4-8 kHz power change median LP -24.6 dB <= Opus8-NB -16.6 dB (difference = image, mirror coherence 4.1-4.9 kHz Opus8-NB 0.23, LP 0.000) |

## 7. Per-cell summary

| subset | cell | utterances | lag_samples | length_equal | retained_bandwidth_hz_median | lsd_db_median | lsd_0_3k_db_median | lsd_0_4k_db_median | lsd_4_8k_db_median | hf_power_change_db_median | coherent_bandwidth_hz | coherent_hf_power_db | total_hf_power_db | image_coherence_4100_4900 | h1_level_db | packets |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| train-clean-100 | lp | 40 | {"0": 40} | 40/40 | 4.09e+03 | 8.37 | 0.0305 | 1.37 | 11.7 | -24.6 | 4.09e+03 | -24.7 | -24.5 | 0.000456 | 3.39e-07 |  |
| train-clean-100 | opus_8k_nb | 40 | {"2": 39, "1": 1} | 40/40 | 4.62e+03 | 9.52 | 6.05 | 6.32 | 10.9 | -16.6 | 4.03e+03 | -32.5 | -16 | 0.231 | -1.84 | {"SILK-NB": 27048} |
| train-clean-100 | opus_12k_nb | 40 | {"2": 40} | 40/40 | 4.59e+03 | 9.07 | 4.84 | 5.37 | 10.9 | -17.9 | 4.03e+03 | -31 | -17.4 | 0.534 | -0.875 | {"SILK-NB": 27048} |
| train-clean-100 | silk_nb_linear_ref | 40 | {"2": 40} | 40/40 | 4.69e+03 | 7.92 | 1.29 | 2.02 | 10.8 | -15.5 | 4.12e+03 | -24.9 | -15.1 | 0.972 | -0.0758 | {"SILK-NB": 27048} |

## 8. Linear transfer |H1| relative to the 0.5-2 kHz level (dB)

| frequency_hz | lp | opus_12k_nb | opus_8k_nb | silk_nb_linear_ref |
|---|---|---|---|---|
| 3e+03 | -0.526 | -3.69 | -5.49 | -0.606 |
| 3.5e+03 | -2.16 | -5.69 | -7.6 | -2.1 |
| 3.75e+03 | -3.82 | -8.67 | -11.3 | -3.91 |
| 3.88e+03 | -5.66 | -11.8 | -13.3 | -5.75 |
| 4e+03 | -10.6 | -16.1 | -17 | -11 |
| 4.06e+03 | -15.6 | -20.2 | -20 | -15.5 |
| 4.12e+03 | -20.8 | -27 | -31.4 | -19.4 |
| 4.19e+03 | -24.6 | -36 | -41.2 | -27.7 |
| 4.25e+03 | -30.3 | -44.1 | -39.3 | -34.7 |
| 4.5e+03 | -55.1 | -54 | -58 | -48.2 |
| 5e+03 | -76.7 | -90.2 | -85 | -79.3 |
