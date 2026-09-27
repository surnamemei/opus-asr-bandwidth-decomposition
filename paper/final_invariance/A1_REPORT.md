# A1 — Cross-validated best-linear decomposition of 8-kbit/s Opus: report

**Frozen outcome: ROBUST_RESIDUAL.** A substantial residual remains when every same-frequency,
linearly predictable change made by the actual 8 kbit/s Opus chain is assigned to a linear
component. The inclusive linear component is no larger than the Stage 3 bandwidth component:
Whisper shows no clear difference, and wav2vec2's is smaller.

This is a post-confirmation sensitivity analysis. The Stage 3 decomposition (REF → LP → OPUS)
remains the primary, pre-specified result. A1 is not:

- a replacement for Stage 3;
- a new bandwidth control or a redefinition of the primary control;
- a successor to R2;
- a causal decomposition.

**Sealed records.**

- Plan and specification: `A1_SPEC.json` (`77da2190…`, rendered as `A1_PLAN.md`) and
  `A1_METHOD_NOTE.md`.
- Signal-set selection: `selection_a1_signal.json` (`354439bd…`).
- Calibration: `a1_calibration/signal_report.json` (`9aec2d21…`) and `asr_report.json`
  (`7aa61124…`).
- Code freeze: `A1_CODE_FREEZE.json` (`819eec0b…`).
- Validation: `a1_validation/validation_report.json` (`ae976ec8…`).
- These were all committed in `6dd879d` before any confirmation-set LIN8 audio existed.
- After that commit:
  - evaluation `a1_evaluation/evaluation_report.json` (`863e6012…`);
  - recognition outputs `a1_raw/outputs_sha256.json` (`ef160ab0…`);
  - decision `A1_DECISION.json` (`7b60320c…`);
  - bootstrap `a1_bootstrap.csv` (sha256 `f7fd453d…`).
- Execution notes and deviations: `A1_DEVIATIONS_2026-09-28.md`.

## 1. Question

If every same-frequency, linearly predictable change made by the actual 8 kbit/s Opus chain
is assigned to a linear component, does a substantial ASR residual remain? The Stage 3
control reproduces the high-rate (40 kbit/s) SILK narrowband linear response. A reviewer can
object that the 8 kbit/s chain's own linear response is lossier than that: lower gain, more
in-band tilt, a different roll-off, phase and delay. The objection is that the Stage 3 residual
may be linear loss that the control leaves out.

## 2. Method (as frozen)

- **Linear component.**
  - For every confirmation utterance, LIN8 is the orthogonal projection of the exact Stage 3
    8 kbit/s Opus waveform (OPUS8) onto the span of REF delayed by −256 … +255 samples (L = 512).
    This is the OPD / BSS Eval target component of Iwamoto et al. (2022) and Ochiai et al. (2024),
    with a centred span.
  - One time-invariant 512-tap least-squares filter is fitted per utterance, so gain, tilt,
    band-edge roll-off, phase and delay within 32 ms are all counted as linear.
  - There are no free parameters and nothing is tuned (`A1_METHOD_NOTE.md`, `A1_PLAN.md`).
- **What stays outside the linear component.** Everything one such filter cannot predict from
  REF at the same frequency: time-varying coding error, the 4–5 kHz mirror image and nonlinear
  distortion. That is the residual R8 = OPUS8 − LIN8.
- **Estimands.** Corpus WER, pp, with Stage 3's paired speaker-cluster bootstrap (10,000
  replicates, seed 5305, 95 % percentile intervals):
  - L8 = WER(LIN8) − WER(REF);
  - R8 = WER(OPUS) − WER(LIN8);
  - T = WER(OPUS) − WER(REF);
  - δ_L = L8 − (LP − REF) = WER(LIN8) − WER(LP), and δ_R = −δ_L;
  - S8 = L8 / T, a descriptive inclusive-linear sensitivity share. It is not a bandwidth share
    and not a true share.
- **Frozen outcome rule** (precedence as in the plan):
  - LINEAR_EXPLANATION_DOMINATES if R8's interval is not above zero in either recogniser, or
    L8 > R8 in both;
  - MIXED if R8's interval is above zero in exactly one recogniser;
  - ROBUST_RESIDUAL if it is above zero in both and R8 > L8 in both;
  - otherwise RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS.
- **Order of steps.** The plan, method note, signal-only selection, calibration, code freeze and
  validation were sealed and committed (`6dd879d`) before any confirmation-set LIN8 audio was
  made. LIN8 was recognised once, in a single session, and the analysis was run once.
- **Execution note.** validate, evaluate and run used single-threaded BLAS. LIN8 then differs
  from multi-threaded BLAS only by last-bit float32 rounding; the recognised LIN8 audio is
  hash-identical to the validated audio (`A1_DEVIATIONS_2026-09-28.md`).

## 3. Signal-level results (no ASR)

| | Calibration (40 utt.) | Validation (40 utt.) | Confirmation (2,174 utt.) |
|---|---|---|---|
| Projection NMSE, median [q25, q75] (dB) | −12.39 [−13.88, −10.80] | −11.61 [−13.22, −10.41] | −12.08 [−13.80, −10.18] |
| Energy of OPUS8 explained by LIN8, median | 0.942 | 0.931 | 0.938 |
| Generalisation gap vs calibration median | — | +0.78 dB (tolerance 3.08 dB) | +0.30 dB |
| Normal-equation residual, max | 6.5 × 10⁻¹⁶ | 7.7 × 10⁻¹⁶ | 2.9 × 10⁻¹⁵ |
| Least-squares fallbacks | 0 | 0 | 0 |
| Second pass bit-identical | 40/40 | 40/40 | (hash-checked at recognition) |
| Pooled coherence 0–3.5 kHz with REF: OPUS8 / LIN8 | 0.650 / 0.945 | 0.658 / 0.939 | — |
| Pooled in-band gain H1 (0.5–2 kHz): OPUS8 / LIN8 | −1.89 / −1.89 dB | −1.90 / −1.90 dB | — |
| Pooled 4–8 kHz power vs REF: OPUS8 / LIN8 | −17.5 / −28.8 dB | −18.4 / −30.7 dB | — |
| Mirror-image coherence 4.1–4.9 kHz: OPUS8 / LIN8 | 0.201 / 0.003 | 0.227 / 0.005 | — |

Gates:

- **C1–C3** (calibration) passed. C3 is the frozen Stage 3 pipeline reproducing the sealed
  Stage 3 calibration outputs: 120/120 waveforms and 240/240 hypotheses identical. The LIN8
  recognition path was deterministic.
- **V1–V3** (held-out signal validation, 40 new speakers) passed: no numerical failure and no
  held-out collapse.
- **E1–E5** (confirmation set, before recognition) passed:
  - the regenerated OPUS8 Ogg files and waveforms equal Stage 3's for 2,174/2,174 utterances;
  - all 2,174 LIN8 waveforms are finite and REF-length;
  - the environment is unchanged;
  - the Stage 3 anchors reproduce to 1.8 × 10⁻¹⁵ pp;
  - no A1 WER existed before the commit.

**Linear response of the 8 kbit/s chain.** Medians of the per-utterance filters. Relative
values are measured against each filter's own 0.5–2 kHz gain.

| | LIN8 filter, calibration [q25, q75] | validation | confirmation | LP control (frozen) |
|---|---|---|---|---|
| Gain 0.5–2 kHz (dB) | −2.05 [−2.44, −1.77] | −2.10 | −2.22 | 0.00 |
| 2.0 kHz (dB, relative) | −1.15 [−1.91, −0.37] | −0.93 | −1.34 | −0.00 |
| 2.5 kHz | −2.55 [−3.74, −1.86] | −2.74 | −2.59 | −0.00 |
| 3.0 kHz | −4.57 [−7.37, −3.83] | −4.54 | −4.54 | −0.62 |
| 3.5 kHz | −6.94 [−9.99, −6.08] | −6.79 | −7.30 | −2.16 |
| 4.0 kHz | −16.68 [−19.69, −13.25] | −16.87 | −15.66 | −10.76 |
| Linear delay (phase slope, 0.5–3 kHz; samples) | 1.69 [1.64, 1.74] | 1.64 | 1.67 | 0 (zero phase) |
| RMS change vs REF, median (dB) | −0.94 | −0.93 | −0.95 | −0.08 |

Observations:

- **Gain and tilt.** The best-linear response of the 8 kbit/s chain is about 2 dB below the
  control over 0.5–2 kHz. It has an additional in-band tilt of about −1 dB at 2 kHz, growing to
  about −4 to −6 dB at 3–4 kHz. This is the bitrate-dependent in-band attenuation that the
  control, fitted to the 40 kbit/s response, deliberately excludes.
- **Stability across speakers.** The response is stable. Interquartile ranges are about 1–3 dB
  in-band. Female and male medians differ by ≤ 0.3 dB in gain and ≤ 1.4 dB at 3.5 kHz.
- **Peak tap and alignment.** The largest tap lies at +2 samples for 79 of the 80 signal-set
  utterances; one validation utterance has its largest tap at +239 samples (descriptive, no gate
  uses it). The recognised LIN8 audio kept the chain's 1–2 sample lag against REF: 2 samples for
  2,162 utterances and 1 sample for 12. Fifteen samples in total were at or above full scale.
- **Causal span.** BSS Eval's causal span, computed on calibration for comparison only, gives
  nearly the same NMSE (median −12.20 dB against −12.39 dB).

## 4. ASR results (confirmation set, 2,174 utterances, 73 speakers)

Pooled; pp; 95 % speaker-bootstrap intervals; primary scope.

| | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| WER REF / LP / LIN8 / OPUS (%) | 2.50 / 2.64 / 2.58 / 3.32 | 5.36 / 6.76 / 6.52 / 8.84 |
| L8 = LIN8 − REF (inclusive linear component) | +0.085 [−0.018, +0.188] | +1.156 [+0.807, +1.547] |
| **R8 = OPUS − LIN8 (residual beyond the best-linear surrogate)** | **+0.742 [+0.512, +1.000]** | **+2.319 [+1.850, +2.968]** |
| T = OPUS − REF | +0.827 [+0.574, +1.102] | +3.476 [+2.732, +4.453] |
| Stage 3 bandwidth component LP − REF | +0.140 [+0.036, +0.249] | +1.405 [+0.990, +1.923] |
| Stage 3 residual OPUS − LP | +0.686 [+0.460, +0.938] | +2.071 [+1.679, +2.567] |
| δ_L = LIN8 − LP (= L8 − Stage 3 component) | −0.055 [−0.127, +0.013] | −0.249 [−0.472, −0.040] |
| δ_R = R8 − Stage 3 residual (= −δ_L) | +0.055 [−0.013, +0.127] | +0.249 [+0.040, +0.472] |
| S8 = L8 / T (descriptive; no replicate with T ≤ 0) | 0.10 [−0.02, 0.22] | 0.33 [0.28, 0.39] |
| Stage 3 sequential share (LP − REF) / T | 0.17 [0.05, 0.29] | 0.40 [0.35, 0.45] |
| Frozen outcome | ROBUST_RESIDUAL | (joint rule) |

Per subset (secondary, uncorrected):

| | Whisper test-clean | Whisper test-other | wav2vec2 test-clean | wav2vec2 test-other |
|---|---|---|---|---|
| L8 | −0.020 [−0.104, +0.061] | +0.227 [+0.017, +0.451] | +0.269 [+0.072, +0.476] | +2.351 [+1.620, +3.239] |
| R8 | +0.285 [+0.138, +0.456] | +1.357 [+0.869, +1.931] | +1.076 [+0.817, +1.367] | +3.995 [+2.986, +5.436] |
| δ_L = LIN8 − LP | +0.008 [−0.054, +0.064] | −0.141 [−0.293, +0.000] | −0.140 [−0.271, −0.012] | −0.395 [−0.895, +0.058] |

In every recogniser × scope cell, R8's interval lies above zero and R8 > L8.

**Cross-run component.** LIN8 was recognised in its own run, whereas REF, LP and OPUS are the
sealed Stage 3 outputs. Whisper's float16 batches therefore differed from Stage 3's. Addition A
measured this effect at 3 of 4,348 hypotheses, and it is contained in L8, R8 and δ_L without
being separated. wav2vec2 decodes each utterance alone and is not affected.

## 5. Answers to the required questions

1. **Does a substantial residual remain under the inclusive best-linear definition?** Yes.
   - R8 = +0.74 pp [+0.51, +1.00] for Whisper and +2.32 pp [+1.85, +2.97] for wav2vec2, which is
     90 % and 67 % of the total penalty.
   - The residual is positive and larger than the linear component in both recognisers, in both
     test subsets.
   - The residual is what one time-invariant filter per utterance cannot predict: the
     time-varying coding error, the mirror image and nonlinear effects. It does not include the
     chain's gain, tilt, roll-off, phase or delay.
2. **How much do the component estimates move relative to Stage 3?** Little, and toward the
   residual.
   - The inclusive linear surrogate was not more harmful than the Stage 3 control. For Whisper,
     δ_L = −0.055 pp [−0.127, +0.013], with no clear difference. For wav2vec2, δ_L = −0.25 pp
     [−0.47, −0.04]: LIN8 was slightly *less* harmful than LP.
   - The residual therefore grows by the same amount: +0.055 and +0.25 pp.
   - The descriptive linear share falls from 0.17 to 0.10 (Whisper) and from 0.40 to 0.33
     (wav2vec2).
   - This happens although LIN8 is about 2 dB quieter than LP, has a steeper top-band roll-off
     and keeps the 1–2 sample delay.
   - A1 does not identify which property of LIN8 makes it no worse than LP. LIN8 has less 4–8 kHz
     power than LP, is fitted per utterance and is not zero-phase. No mechanism is inferred, and
     none was searched for.
3. **Which claims survive?**
   - A positive codec-specific residual, for both recognisers.
   - The ordering residual > linear component, for both recognisers. It now holds under two
     definitions of linear loss: the validated high-rate narrowband control, and the utterance-level
     best-linear projection of the actual 8 kbit/s chain.
   - The reading that the 8 kbit/s penalty is not explained by linear band limitation alone,
     including the chain's own lower gain and in-band tilt.
4. **Which claims must be weakened?**
   - No core claim.
   - The exact shares depend on how linear loss is defined: 0.17 vs 0.10 (Whisper) and 0.40 vs
     0.33 (wav2vec2). With C1's finding that the Whisper share is RATIO_UNSTABLE, this supports
     writing "a minority of the penalty" in high-level prose and giving shares only as
     path- and definition-dependent quantities.
   - The inclusive linear component is itself not detectable for Whisper in the pooled scope:
     L8 = +0.085 [−0.018, +0.188].
5. **Is "bandwidth" still the correct word for the primary control?** Yes, as an operational label
   that is defined once.
   - The control reproduces SILK narrowband's *high-rate* linear band-limiting response, fitted at
     40 kbit/s and validated on held-out speakers.
   - A1 shows that the 8 kbit/s chain's own linear response also contains a gain loss and an
     in-band tilt. So "bandwidth component" means the effect of the high-rate narrowband linear
     response, not the whole linear part of the 8 kbit/s chain.
   - Recommendation: keep "bandwidth component" in the text. The first mention (abstract, Section
     1, Section 3.4) should say that the control reproduces SILK narrowband's high-rate linear
     band-limiting response.
   - Because the more inclusive linear attribution does not reduce the residual, the choice of
     label does not change any conclusion.
6. **Does the alternative attribution strengthen or weaken the TASLP case?** It strengthens it.
   - It answers the main reviewer attack, that the residual is linear loss the high-rate control
     leaves out, with a literature-grounded, pre-specified test.
   - The answer is in the direction that supports the paper: including the actual chain's gain,
     tilt, roll-off, phase and delay in the linear component leaves a residual at least as large.

## 6. Limits

- **Utterance-level projection.** One filter is fitted per utterance, as in the prior method. So
  LIN8 is an *attribution* of each utterance's coded output, not a fixed, deployable control.
- **Not a pure loss model.** A least-squares projection can act as a mild long-term spectral
  weighting. L8 is therefore a sensitivity quantity, not an estimate of the harm from linear band
  limitation alone.
- **Time-invariant within an utterance.** The filter cannot follow SILK's frame-by-frame spectral
  shaping. Frame-level linear changes are therefore on the residual side by construction; this
  is the OPD definition. A time-varying linear attribution was not part of A1 and was not tried.
- **Span.** Delays beyond ±256 samples, and effects longer than 32 ms, are outside the linear
  span. The measured delay is 1–2 samples.
- **Pipeline scope.** One corpus, two recognisers, one encoder and decoder chain (libopus 1.4,
  FFmpeg 6.1.1), the Stage 3 settings (application=audio).

## 7. Manuscript consequence (rule A, ROBUST_RESIDUAL)

- Keep the Stage 3 primary decomposition.
- Add a short sensitivity statement: under a more inclusive, utterance-level best-linear
  attribution of the actual 8 kbit/s chain (Iwamoto et al.; Ochiai et al.), a residual of
  +0.74 and +2.32 pp remains.
- Never call S8 a true share.
- Note in the Methods that the control reproduces the high-rate narrowband linear response.
