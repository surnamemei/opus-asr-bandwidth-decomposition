# Organising hypothesis (exploratory; no new experiment)

> **Candidate organising hypothesis.** Low-rate ASR behaviour reflects a bitrate-allocation
> trade-off between spectral coverage and fidelity within the retained representation.

This note is exploratory. It reorganises sealed results. It runs nothing new, computes no
p-values and fits nothing to evaluation ASR.

- Every number comes from sealed records: Stage 3, the Addition B bitrate sweep, R3, and the A1
  and B1 records of this pass.
- The hypothesis is a candidate way to organise these results. It is not a demonstrated mechanism.
- Where the evidence cannot separate candidate variables, this note says so.

## 1. Evidence at the condition level

Addition B / R3 set: 1,665 utterances, 70 speakers. The residual is measured against the frozen LP
control on the same set (pp, 95 % speaker-bootstrap intervals). The descriptors are medians
(Addition B sweep descriptors, R3 descriptives). In the SILK sweep the signal hint is fixed; NB8
produces the same hypotheses as SILK8.

| Condition | Payload kbit/s (median) | Retained bandwidth (Hz) | 4–8 kHz power vs REF (dB) | LSD 0–3 kHz vs LP (dB) | Coherence 0–3.5 kHz | Whisper: condition − LP | wav2vec2: condition − LP |
|---|---|---|---|---|---|---|---|
| SILK8 = NB8 | 7.36 | 4,625 | −17.2 | 6.19 | 0.623 | +0.55 [+0.37, +0.74] | +2.07 [+1.65, +2.55] |
| SILK12 | 11.35 | 4,594 | −18.6 | 4.96 | 0.810 | +0.21 [+0.09, +0.33] | +0.75 [+0.55, +0.97] |
| SILK16 | 15.43 | 4,594 | −18.5 | 3.98 | 0.896 | +0.13 [+0.04, +0.22] | +0.36 [+0.19, +0.54] |
| SILK24 | 23.46 | 4,625 | −17.7 | 2.66 | 0.963 | +0.05 [−0.04, +0.14] | +0.05 [−0.11, +0.20] |
| SILK40 | 38.96 | 4,656 | −16.4 | 1.37 | 0.993 | +0.03 [−0.05, +0.11] | −0.06 [−0.21, +0.09] |
| WB8 (forced wideband, 8 kbit/s) | 7.76 | 8,000 | +1.7 | 6.77† | 0.559† | WB8 − NB8: +0.14 [−0.07, +0.36] | WB8 − NB8: −0.98 [−1.57, −0.42] |

Notes on the table:

- † For WB8, the LSD and coherence are measured against REF, not LP. For SILK8 = NB8 the two
  references agree: LSD 6.19 dB and coherence 0.623 in both cases.
- The residual trend over log2 bitrate is −0.21 pp per doubling [−0.27, −0.15] for Whisper and
  −0.85 [−1.07, −0.66] for wav2vec2 (Addition B, GO).
- Stage 3 confirmation set (2,174 utterances), for context:
  - The bandwidth component is B = +0.14 pp (Whisper) and +1.40 pp (wav2vec2).
  - The Opus 8 kbit/s residual is R = +0.69 and +2.07.
  - Its in-band coherence against LP is 0.623 and its LSD 0–3 kHz is 6.14 dB, the same as SILK8
    in the sweep.

## 2. What the evidence is consistent with

1. **At fixed coverage, the residual tracks in-band fidelity.**
   - Across the SILK sweep, retained bandwidth stays at 4.6 kHz and 4–8 kHz power stays at
     −16 to −19 dB.
   - Over the same sweep, the residual falls monotonically as in-band fidelity rises. LSD 0–3 kHz
     falls from 6.2 to 1.4 dB and coherence rises from 0.62 to 0.99.
   - For both recognisers the residual is no longer detectable once in-band coherence exceeds
     about 0.96 (24 and 40 kbit/s).
   - This is consistent with the residual being a cost of in-band fidelity within the retained
     narrowband representation, rather than of coverage.
2. **At fixed bitrate, more coverage costs in-band fidelity.**
   - Forcing wideband at 8 kbit/s (WB8) uses almost the same payload as NB8 (7.76 vs 7.36 kbit/s).
   - WB8 restores coverage to 8 kHz, with 4–8 kHz power near REF.
   - WB8 lowers in-band fidelity: coherence falls from 0.623 to 0.559 and LSD 0–3 kHz rises from
     6.19 to 6.77 dB.
   - This is the allocation trade-off in its plainest form: the same bits are spread over a wider
     band.
3. **Which side of the trade-off wins depends on the recogniser's sensitivity to coverage.**
   - wav2vec2-base-960h has a large bandwidth component (B = +1.40 pp), and WB8 lowered its WER
     (−0.98 pp).
   - Whisper large-v3 has a small bandwidth component (B = +0.14 pp), and it showed no clear
     difference (+0.14 [−0.07, +0.36]).
   - This pattern is consistent with a recogniser gaining from coverage in proportion to its
     bandwidth sensitivity while paying for the lost in-band fidelity.
   - With two recognisers it can only be called suggestive.

## 3. Candidate organising variables

| Candidate | Orders the SILK sweep? | Separates NB8 from WB8? | Explains the recogniser-dependent WB8 result? |
|---|---|---|---|
| Payload bitrate / log2 bitrate | yes (monotone) | no (7.36 vs 7.76 kbit/s) | no |
| Coded / retained bandwidth | no (constant at ~4.6 kHz) | yes | only jointly with a fidelity variable |
| LSD 0–3 kHz | yes (monotone) | yes (6.19 vs 6.77 dB, predicts WB8 worse) | no by itself (wav2vec2 improved) |
| Coherence 0–3.5 kHz | yes (monotone) | yes (0.623 vs 0.559, predicts WB8 worse) | no by itself |
| High-band (4–8 kHz) power | no (constant) | yes (−17.2 vs +1.7 dB) | only jointly with a fidelity variable |

- **Bitrate, LSD and coherence cannot be separated.** They are collinear across the SILK sweep,
  and five conditions from one codec cannot tell them apart.
- **No single scalar orders all six conditions for both recognisers.**
  - A fidelity variable alone predicts WB8 worse than NB8. That holds for neither recogniser: the
    difference is unclear for Whisper, and WB8 is better for wav2vec2.
  - A coverage variable alone predicts WB8 better than NB8. That holds for wav2vec2 but not
    clearly for Whisper.
- **The smallest description consistent with every condition has two parts:** in-band fidelity
  plus coverage, weighted by the recogniser's coverage sensitivity. This is why the hypothesis
  is phrased as an allocation trade-off rather than as a rate–distortion curve in one variable.
- **The two-part description is itself a candidate.** It is fitted to nothing and tested against
  nothing held out.

## 4. Limits of this reading

- **It organises conditions, not utterances.** In the frozen Stage 3 exploratory analysis,
  per-utterance in-band descriptors barely rank the per-utterance Opus residual. Spearman
  ρ(coherence) is −0.06 [−0.12, +0.004] for Whisper and −0.09 [−0.16, −0.02] for wav2vec2, and
  the LSD correlations are ≤ 0.04 (`11_exploratory_signal_correlations.csv`). The hypothesis is
  about where a codec configuration sits on the trade-off, not about which utterances suffer.
- **Narrow evidence base.**
  - One codec family (SILK in libopus 1.4) and one decoder path, although R4 shows that the total
    penalty persists under the reference decoder.
  - One corpus of read speech and two recognisers.
  - Six conditions, five of them on a single axis.
- **Coherence and LSD are signal descriptors, not recogniser features.** Neither tells us what the
  recogniser uses.
- **WB8 changes more than coverage.** Forcing wideband also changes SILK's internal sampling rate
  and the allocation between bands. R3 is labelled a practical counterfactual, not a factorial
  effect of bandwidth.

## 5. What A1 and B1 add

*(Written after A1 and B1 were sealed and committed.)*

### 5.1 A1 (best-linear decomposition; sealed `A1_DECISION.json`, ROBUST_RESIDUAL)

- **The 8 kbit/s chain's own linear response loses some in-band fidelity.** Its median gain is
  −2.2 dB, and it has an extra in-band tilt of about −1 dB at 2 kHz, growing to −6 dB at
  3.5–4 kHz relative to the control. That loss is *linear*, and it did not cost WER.
  - The utterance-level best-linear surrogate LIN8 keeps this loss. Its WER was no higher than
    LP's: −0.06 pp [−0.13, +0.01] for Whisper and −0.25 [−0.47, −0.04] for wav2vec2.
  - The residual beyond it is +0.74 and +2.32 pp.
- **What organises the residual is the incoherent, non-linearly-predictable part.** Median
  in-band coherence with REF is 0.94 for LIN8 and 0.65 for OPUS8. Between REF, LP and LIN8, WER
  hardly changes; between LIN8 and OPUS8 it changes a lot.
- **Consequence for the candidate variables.**
  - Coherence over 0–3.5 kHz, which measures exactly this incoherent fraction, stays a candidate
    organising variable for fidelity.
  - A purely spectral-magnitude fidelity measure, such as band-limited LSD or in-band gain and
    tilt, is weakened as an organiser. LIN8 has a large spectral-shape change (a −2 dB gain and a
    −5 dB tilt at 3.5 kHz) and almost no WER cost.
  - The hypothesis becomes: *allocation between coverage and coherent in-band fidelity*.
  - This is consistent with A1, not established by it.

### 5.2 B1 (application mode; sealed `B1_DECISION.json`, NO_CLEAR_APPLICATION_DIFFERENCE in both)

- **What changed at the signal level.** Switching the encoder to the VOIP application changed
  every waveform. The bit budget stayed almost the same (median payload 7.29 vs 7.34 kbit/s) and
  the coded band did not change (all SILK narrowband). In-band fidelity descriptors were slightly
  worse under VOIP:
  - per-utterance coherence 0–3.5 kHz 0.614 vs 0.623 (pooled 0.583 vs 0.652);
  - LSD 0–3 kHz 6.41 vs 6.14 dB.
- **WER was not higher.** Whisper: −0.12 pp [−0.25, 0.00]. wav2vec2: −0.03 pp [−0.23, +0.15].
- **Prediction from the SILK sweep.** Interpolating the sweep's residual-versus-coherence relation,
  a coherence-only organiser predicts an *increase* of a few hundredths of a pp. That is far inside
  these intervals, so B1 cannot discriminate.
- **The Whisper direction is a caution.** The point estimate goes the other way, and so does the
  secondary test-other cell (−0.28 [−0.56, −0.02]).
- **What B1 changes in the reading.**
  - At fixed bitrate and coded band, differences in coherence this small (about 0.01) are below
    what the candidate variable can resolve.
  - The application mode changes other properties at the same time: the pre-processing, the delay
    distribution, and the image copy fidelity (0.093 vs 0.227).
  - B1 neither supports nor refutes the organising hypothesis. It marks the resolution limit of
    the descriptor.

## 6. What would weaken the hypothesis

These are stated for completeness. They were not run, and none is proposed for this submission.

- The hypothesis predicts a crossover bitrate at which a wider coded band starts to pay, and it
  predicts that the crossover is earlier for coverage-sensitive recognisers. It would be weakened
  if, at a fixed bitrate, the WER effect of widening the coded band did not order recognisers by
  their bandwidth component.
- It would also be weakened if a condition with high in-band coherence (≥ 0.96) at narrowband
  coverage still showed a residual clearly above zero.
