# Paper extension: stage status

Frozen ELEC5305 pipeline: `src/` and `results/` unchanged throughout.

| Stage | Status | Evidence |
|---|---|---|
| 1 Reproduction of the frozen pipeline | PASS (250/250 checks) | `results_paper/reproduce/equivalence_report.md` |
| 2A Direct-libopus bandwidth control | PASS (7/7 gates) | `results_paper/opus_validation/validation_report.md` |
| 2B-v1 Matched low-pass control, original specification | **FAIL under the original internally inconsistent Gate 5** (kept unchanged as historical record) | `results_paper/lowpass_validation/validation_report.md` |
| 2B Matched low-pass control | **PASS under corrected specification, independently confirmed** | `results_paper/lowpass_confirmation/confirmation_report.md` |

## Stage 2B provenance

| Item | Value |
|---|---|
| Frozen filter taps SHA-256 (unchanged in every run) | `583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16` |
| Original tolerance set SHA-256 (2B-v1) | `bc91d298ac402bbed082dfd71de0ec4dc15d0c1419261a7fdac6ca6a88c49833` |
| Revised specification SHA-256 (Gate 5 corrected; frozen before the confirmation data were downloaded) | `166f5672263373ece22a955baf3b2e1f3c7ac7c9ce14098f9daa65938d9055ff` |
| Confirmation selection SHA-256 (train-clean-100, 20 F + 20 M speakers, seed 5305) | `0dfc09813d018c3f5026da7723cec3222fe14c957289f126e6aa3108e9932212` |

Timeline (UTC, 2026-09-26):

| Time | Event |
|---|---|
| 05:52:25 | Filter calibrated on dev-clean and frozen; tolerance hash stored |
| 05:53:29 | 2B-v1 validation (dev-clean, dev-other): FAIL on Gate 5 / Gate 7 |
| 06:02:50 | Revised specification frozen (train-clean-100 not on disk) |
| 06:16:04 | train-clean-100 download completed |
| 06:16:38 | Utterance selection resolved from file names only and sealed |
| 06:17:02 | Single confirmatory validation: PASS (gates 1-4, 5 revised, 6; gate 7 confirmatory) |

Correction: the original Gate 5 also required the LP's coherent 4-8 kHz power to lie
within 6 dB of Opus8-NB's. Under the linear-only definition this is inconsistent,
because Opus8-NB's coherent 4-8 kHz power contains bitrate-dependent SILK coding
droop across the 4 kHz edge (linear reference -25.3 dB, Opus12-NB -31.1 dB,
Opus8-NB -34.6 dB on dev-clean). Only that sub-criterion was removed; the 3.0 dB
tolerance against the linear SILK-NB reference and every other gate, tolerance,
filter tap and encoder setting are unchanged.

No ASR model, transcript or WER has been used in Stages 2A-2B. No ASR experiment
has been run on the controlled conditions.
