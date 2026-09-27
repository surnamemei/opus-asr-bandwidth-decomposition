# A1 — deviations and execution notes (2026-09-28)

Dated record. The sealed A1 files (`A1_SPEC.json`, `A1_CODE_FREEZE.json` and the calibration and
validation reports) are not edited.

## 1. Single-threaded BLAS for validate, evaluate and run (execution setting)

- **What.** `run_a1.py validate`, `evaluate` and `run` are executed with the environment variable
  `OPENBLAS_NUM_THREADS=1`. This caps numpy's bundled OpenBLAS at one thread.
- **What is unchanged.**
  - No code changed: the code freeze `819eec0b…` still verifies.
  - torch threads are unchanged, so the Opus decode and resampling path is unchanged.
  - The recorded environment (library versions, libopus path and hash) is unchanged.
- **Why.** The machine was shared with other projects' CPU jobs (load average about 38 on 32
  logical cores). numpy's default 32-thread OpenBLAS then spent about 10–24 s on each 512 × 512
  `np.linalg.solve`, an operation that takes milliseconds. A Python stack dump showed the main
  thread inside `solve`. At that rate the 2,174-utterance evaluation would have taken hours.
- **Effect on the numbers, measured on calibration utterances only** (signal-only set, no ASR):
  - OPUS8 is bit-identical to Stage 3 under both settings (3/3).
  - LIN8 under one thread equals the sealed default-thread calibration hash for 1 of 3
    utterances.
  - On a differing utterance (39-121915-0030), exactly 1 of 196,080 float32 samples differs, by
    2.3 × 10⁻¹³: a last-bit rounding flip, with difference energy −273 dB relative to the signal.
  - The default-thread projection reproduced the sealed hash exactly, in 10.1 s.
  - The calibration gates C1–C3, the collapse tolerance and the calibration median NMSE were
    computed with default threads. Differences of this size do not affect them.
- **Consequence for the evaluation.**
  - `evaluate` computes and seals every LIN8 SHA-256 under the one-thread setting.
  - `run` regenerates LIN8 under the same setting and refuses any waveform whose hash differs
    (the frozen check).
  - The LIN8 audio that is recognised is therefore exactly the audio that passed E1–E5.
- **Reproducibility.** Reproducing the A1 LIN8 waveforms bit for bit requires the same OpenBLAS
  thread setting. With another thread count, rare samples can differ in the last bit.

## 2. Validation attempts stopped before any output (no result produced or seen)

Two `validate` attempts were stopped before any validation output existed. Neither wrote a row,
curve or report, and no validation quantity was seen. The only trace was the empty
`a1_validation/` directory created at the start.

1. The first attempt (default threads, 04:20–04:31 local) was stalled in the thread contention
   described above and was stopped after about 11 minutes.
2. The second attempt (default threads, under `faulthandler` stack dumps, about 50 s) was stopped
   after one utterance, once the dump had located the stall in `np.linalg.solve`.

The third attempt, with `OPENBLAS_NUM_THREADS=1`, is the sealed validation (`ae976ec8…`), and it
passed V1–V3. The diagnostic runs used only calibration utterances.

## 3. Code change between the design freeze and the code freeze

After the plan was sealed and before the code freeze, `run_a1.analyse` gained a guard that
refuses a second analysis (the decision or bootstrap file already exists). It is listed among
the changed files in the code freeze (`code_changed_since_design_freeze`). It changes no
estimand, gate, rule or number.
