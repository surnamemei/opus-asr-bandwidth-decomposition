# A1 method note: a best-linear decomposition of 8 kbit/s Opus, grounded in prior work

Written before any A1 code was run or any A1 audio was read (2026-09-27).

## 1. Closest prior method

Iwamoto et al. [Interspeech 2022, arXiv:2201.06685] and Ochiai et al. [IEEE TASLP 32,
3589–3602, 2024, arXiv:2404.14860] analyse how speech-enhancement errors affect ASR. Both use the
orthogonal projection-based decomposition (OPD) of BSS Eval [Vincent et al., IEEE TASLP 14(4), 2006].

The decomposition, quoted from Iwamoto et al., Sec. 2.1, Eqs. (1)–(6):

- ŝ = s_target + e_noise + e_artif.
- P_s := A_s (A_sᵀ A_s)⁻¹ A_sᵀ, with A_s := [s_{τ=0}, …, s_{τ=L−1}] ∈ R^{T×L}. Here s_τ is the
  reference source delayed by τ, and "L − 1 is the number of maximum delay allowed".
- s_target = P_s ŝ; e_noise = P_{s,n} ŝ − P_s ŝ; e_artif = ŝ − P_{s,n} ŝ.
- The artifact component is "the SE error signal that cannot be represented as a linear combination
  of speech and noise sources". The target component is the best least-squares approximation of ŝ
  by a length-L FIR filter applied to the reference.

Ochiai et al. (Sec. III, Eqs. (2)–(4), and Sec. V) use the same projections, adding interference.
They set "the number of basis vectors … L = 512 by following the de facto standard BSSEval's
implementation", and they analyse ASR by rescaling the decomposed components (their Eq. (16)).

## 2. Properties of the prior projection

| Property | Prior method (OPD / BSS Eval) |
|---|---|
| Scope | Per utterance (per T-length waveform); no parameters are shared across utterances |
| Domain | Time domain (waveform vectors in R^T) |
| Model | A time-invariant FIR filter of L = 512 taps (32 ms at 16 kHz) on the reference; least squares = orthogonal projection |
| Causality | Delays τ = 0 … L−1: the estimate may depend on the current and past reference samples only |
| Constraints | None on gain, phase, spectral shape or delay within the span; no regularisation |
| Computation (BSS Eval reference code, mir_eval `_project`) | Zero-pad both signals by L−1; Gram matrix from the FFT autocorrelation of the reference (Toeplitz); cross-correlations with the estimate; exact solve, with a least-squares fallback if singular; the projection has length T + L − 1 |

## 3. Adaptation to codec output

1. **Single reference, no noise or interference.** Here the "estimate" is the decoded 8 kbit/s
   Opus waveform (OPUS8, the exact Stage 3 FFmpeg-decoded signal) and the "source" is REF. There
   is no noise reference, so the decomposition reduces to y = P_s y + (y − P_s y). The linear
   component is LIN8 := P_s y and the rest is the residual. The residual contains what BSS Eval
   calls artifacts: nonlinear coding distortion, the 4–5 kHz mirror image, and anything else not
   same-frequency linearly predictable.
2. **Centred delay span (the only change to the projection itself).** BSS Eval assumes an estimate
   that is a delayed version of the reference, so its span is causal (0 … L−1). The decoded Opus
   signal is aligned with REF to within 1–2 samples, and the chain includes a linear-phase
   48 → 16 kHz resampler with a two-sided response. A causal span would therefore miss the part of
   the linear response before its peak and wrongly assign it to the residual. A1 keeps L = 512
   basis vectors but centres them: τ = −256 … +255. This is implemented exactly as BSS Eval, by
   delaying the estimate by 256 samples, projecting on the causal span and advancing the result.
   The number of basis vectors, the least-squares criterion, the per-utterance scope and the
   absence of constraints are unchanged. The causal variant is computed on the calibration set only,
   as a descriptive check; it does not select anything.
3. **Time support for recognition.** The projection has length T + L − 1. LIN8 is its restriction
   to the T samples of REF, so every condition has the REF length, as in Stage 3.

## 4. What is copied exactly and what is new

- **Copied:**
  - the OPD target projection (Iwamoto Eqs. (2) and (4));
  - L = 512 (Ochiai, following BSS Eval);
  - the per-utterance, time-domain, unconstrained least-squares filter;
  - the reference algorithm of `mir_eval.separation._project`, reimplemented in numpy with the same
    padding, FFT correlations, Toeplitz Gram matrix and solve-with-fallback.
- **New here:**
  - the centred span (section 3.2);
  - its use on codec output rather than enhancement output;
  - recognising the target component on its own (LIN8) to define the sensitivity decomposition
    L8 = LIN8 − REF, R8 = OPUS8 − LIN8;
  - the signal-only gates.
- **Not claimed:** A1 is not identical to the prior method, which scales the components of enhanced
  speech rather than recognising a target-only signal.

## 5. Why this method answers the reviewer objection

The objection is that the primary control (the high-rate 40 kbit/s SILK narrowband linear
response) assigns to the residual, by construction, any additional linear change that the
8 kbit/s chain makes: coherent gain, spectral tilt and band-edge droop.

The OPD target component is the most inclusive same-frequency linear account available:
- for each utterance, it assigns to the linear component every change of the actual 8 kbit/s
  output that a stable 512-tap LTI filter of REF can reproduce, including gain, tilt, band-edge
  roll-off, phase and delay;
- it forces no unity gain, flat passband, zero phase or 4 kHz cutoff;
- it has no free parameter to tune, because L comes from prior work and the span centring is fixed
  a priori at L/2.

So if a substantial ASR residual remains beyond LIN8, it cannot be attributed to same-frequency
linear loss under any LTI filter of this support. If it vanishes, the primary split depends on how
linear loss is defined.

Because the projection is fitted per utterance, it is fitted on the evaluation utterances'
own OPUS8 output. This is required by the prior method (option A of the pass instructions), is
pre-specified before any evaluation recognition, and uses no ASR output.

It is more inclusive than a global LTI surrogate (option B), which would capture only the average
linear response of the chain. A1 therefore does not fit a global filter and has no support or
ridge grid.

The new signal-only calibration and validation speakers serve three purposes: to run every piece
of code before the freeze, to check numerical stability, reproducibility and the absence of
held-out collapse, and to describe the linear response. No ASR is run on them.

## 6. Limits stated in advance

- **Not a replacement or redefinition.** LIN8 is not a bandwidth control. A1 does not replace the
  pre-specified Stage 3 decomposition and does not redefine the published primary control. A1 is
  not R2 (a global zero-phase surrogate).
- **Inclusiveness.** The per-utterance filter may absorb any coding distortion that is linearly
  correlated with the input over a whole utterance. A1 is therefore an inclusive, not a
  conservative, linear attribution, and its share S8 is a sensitivity quantity, not a "true" share.
- **Time-invariance.** The filter is time-invariant within an utterance. Time-varying linear
  behaviour, such as frame-wise SILK gains, remains in the residual.
