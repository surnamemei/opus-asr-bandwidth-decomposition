# B1 — 8-kbit/s application-mode sensitivity: report

**Frozen outcome: NO_CLEAR_APPLICATION_DIFFERENCE for both recognisers.** With
`OPUS_APPLICATION_VOIP` in place of `OPUS_APPLICATION_AUDIO`, and every other setting unchanged,
the total 8 kbit/s penalty remained positive and of similar size:

- **Whisper large-v3.** V = +0.70 pp [+0.48, +0.95] against A = +0.83 [+0.57, +1.10]. The
  difference D_app = −0.12 pp [−0.25, 0.00] has an upper bound of exactly zero, so it does not
  exclude zero.
- **wav2vec2-base-960h.** V = +3.44 pp [+2.71, +4.37] against +3.48 [+2.73, +4.45], with
  D_app = −0.03 pp [−0.23, +0.15].

B1 is a post-confirmation configuration sensitivity of the total penalty. It is not a new
decomposition and not an equivalence test, and it computes no VoIP bandwidth share.

**Sealed records.**

- Plan `B1_SPEC.json` (`42504ce4…`, rendered as `B1_PLAN.md`; sealed after A1 was committed).
- Calibration `b1_calibration/encode_report.json` (`f2617b4f…`) and `asr_report.json`
  (`7a62b116…`).
- Code freeze `B1_CODE_FREEZE.json` (`b811a4a3…`); the plan package was committed in `25d81fa`.
- Validation `b1_validation/validation_report.json` (`211bb0a1…`), committed in `00ce368` before
  recognition.
- Recognition outputs `b1_raw/outputs_sha256.json` (`cf0a5030…`).
- Decision `B1_DECISION.json` (`863e9c91…`) and bootstrap `b1_bootstrap.csv` (`bce9f577…`).

## 1. Question

Keeping bitrate, bandwidth, signal hint, frame duration, VBR, complexity, decoder and ASR fixed,
does changing only `OPUS_APPLICATION_AUDIO` → `OPUS_APPLICATION_VOIP` materially change the
total ASR penalty of 8 kbit/s Opus? Stage 3 used `application=audio` to reproduce the frozen
codec baseline of the preliminary analysis. Real-time VoIP deployments typically use the VOIP
application.

## 2. Design (as frozen)

- **Conditions.**
  - REF and OPUS_AUDIO8 are the sealed Stage 3 REF and OPUS outputs, reused.
  - OPUS_AUDIO8's bitstreams and waveforms were regenerated and reproduced exactly before
    recognition.
  - OPUS_VOIP8 is the only new condition.
- **The single change.** OPUS_VOIP8 uses the Stage 3 OPUS encoder settings with one parameter
  changed: application audio → voip (`OPUS_APPLICATION_VOIP`, 2048). Everything else is identical:
  - libopus 1.4, 8 kbit/s, forced narrowband, `signal=auto` (not set to voice);
  - unconstrained VBR, complexity 10, 20 ms frames;
  - no FEC or DTX, lsb_depth 24, mono;
  - the same Ogg writer, FFmpeg 6.1.1 native decode at 48 kHz and torchaudio resample to 16 kHz;
  - no realignment and no gain normalisation.
- **Estimands** (pooled, per recogniser; Stage 3's paired speaker-cluster bootstrap, 10,000
  replicates, seed 5305, 95 % percentile intervals):
  - A = WER(OPUS_AUDIO8) − WER(REF);
  - V = WER(OPUS_VOIP8) − WER(REF);
  - D_app = WER(OPUS_VOIP8) − WER(OPUS_AUDIO8).
- **Frozen outcome rule.**
  - VOIP_LOWER_PENALTY if D_app's upper bound is < 0;
  - VOIP_HIGHER_PENALTY if its lower bound is > 0;
  - NO_CLEAR_APPLICATION_DIFFERENCE otherwise.
  - There is no minimum effect, no equivalence claim and no combined outcome. No VoIP bandwidth
    share is computed, because no application-matched linear control exists or was built.
- **Order of steps.**
  - Plan sealed after A1 was committed.
  - Calibration on the 20 Stage 3 calibration utterances (K1–K7).
  - Code freeze, and the plan package committed (`25d81fa`).
  - Validation of the 2,174 confirmation bitstreams, committed before recognition (`00ce368`).
  - OPUS_VOIP8 recognised once, in one session, on an otherwise idle GPU (30.2 GiB free at the
    start).
  - Analysis run once.

## 3. Checks before recognition (all passed)

| Check | Calibration (20) | Confirmation (2,174) |
|---|---|---|
| K1: OPUS_AUDIO8 reproduces the sealed Stage 3 OPUS Ogg files and waveforms | 20/20 | 2,174/2,174 |
| K2: OPUS_VOIP8 encodes and decodes; REF length; finite | 20/20 | 2,174/2,174 |
| K3: every control reads back as requested (application 2049 / 2048) | pass | pass |
| K4: every packet mono, narrowband, 20 ms (mode reported: all SILK) | pass | pass |
| K5: libopus 1.4 at the sealed path and hash; environment unchanged | pass | pass |
| K6: second pass bit-identical | 20/20 | — |
| K7: Stage 3 pipeline reproduces the sealed calibration outputs; VOIP8 recognition path deterministic | pass | — |
| K8: B1 code reproduces Stage 3 WER(REF), WER(OPUS), OPUS − REF | — | 1.8 × 10⁻¹⁵ pp |
| K9: plan and code freeze committed; validation committed before any B1 WER | — | pass |

## 4. Results (confirmation set, 2,174 utterances, 73 speakers)

| Pooled | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| WER REF / OPUS_AUDIO8 / OPUS_VOIP8 (%) | 2.50 / 3.32 / 3.20 | 5.36 / 8.84 / 8.80 |
| A = OPUS_AUDIO8 − REF (= Stage 3 OPUS − REF) | +0.827 [+0.574, +1.102] | +3.476 [+2.732, +4.453] |
| **V = OPUS_VOIP8 − REF** | **+0.705 [+0.484, +0.951]** | **+3.441 [+2.708, +4.370]** |
| **D_app = OPUS_VOIP8 − OPUS_AUDIO8** | **−0.122 [−0.253, 0.000]** | **−0.035 [−0.227, +0.154]** |
| D_app, CER (secondary) | −0.067 [−0.131, −0.007] | −0.046 [−0.132, +0.038] |
| D_app per 100 words: S / D / I (secondary) | −0.097 / +0.009 / −0.035 | −0.067 / +0.035 / −0.002 |
| Frozen outcome | NO_CLEAR_APPLICATION_DIFFERENCE | NO_CLEAR_APPLICATION_DIFFERENCE |

Per subset (secondary, uncorrected):

| | V | D_app |
|---|---|---|
| Whisper test-clean | +0.261 [+0.128, +0.413] | −0.004 [−0.103, +0.087] |
| Whisper test-other | +1.303 [+0.839, +1.836] | −0.281 [−0.561, −0.020] |
| wav2vec2 test-clean | +1.272 [+0.925, +1.647] | −0.072 [−0.278, +0.131] |
| wav2vec2 test-other | +6.363 [+4.793, +8.483] | +0.016 [−0.330, +0.375] |

**The Whisper boundary case.**

- The pooled Whisper interval of D_app is [−0.253, 0.000]. Its upper bound is exactly zero,
  because one percentile replicate has equal error totals in the two conditions.
- The frozen rule requires an upper bound *below* zero for VOIP_LOWER_PENALTY, so the outcome is
  NO_CLEAR_APPLICATION_DIFFERENCE. The rule was applied as written.
- Two secondary Whisper cells do exclude zero: CER (−0.067 [−0.131, −0.007]) and test-other
  (−0.281 [−0.561, −0.020]). Both are uncorrected secondary scopes.
- The honest reading is a borderline tendency toward a *lower* Whisper penalty under the VOIP
  application. It is of the same size and direction as the libopus-decoder effect of R4
  (−0.11 pp [−0.17, −0.04]), and it is not established.

**Cross-run component.** OPUS_VOIP8 was recognised in its own run, whereas REF and OPUS_AUDIO8
are the sealed Stage 3 outputs, so Whisper's float16 batches differed from Stage 3's. Addition A
measured this batch-composition effect at 3 of 4,348 hypotheses. It is part of V and D_app and is
not separated. wav2vec2 decodes each utterance alone.

## 5. Descriptors (confirmation set; descriptive only, never a gate)

| Descriptor (against REF) | OPUS_AUDIO8 | OPUS_VOIP8 |
|---|---|---|
| Payload bitrate, median [5th, 95th percentile] (kbit/s) | 7.34 [6.73, 7.71] | 7.29 [6.71, 7.68] |
| Coherence 0–3.5 kHz, per-utterance median | 0.623 | 0.614 |
| Coherence 0–3.5 kHz, pooled | 0.652 | 0.583 |
| LSD 0–3 kHz, median (dB) | 6.14 | 6.41 |
| RMS change, median (dB) | −0.68 | −0.72 |
| In-band gain 0.5–2 kHz, pooled (dB) | −1.83 | −2.02 |
| Total 4–8 kHz power, pooled (dB) | −16.7 | −16.8 |
| Mirror-image coherence 4.1–4.9 kHz, pooled | 0.227 | 0.093 |
| Integer lag (samples: utterances) | 1: 12; 2: 2,162 | −4 to −1: 50; 0: 213; 1: 1,625; 2: 286 |
| Samples at or above full scale (utterances) | 113 (17) | 78 (19) |

Observations:

- **Every waveform changes.** No VOIP8 waveform is identical to its AUDIO8 counterpart.
- **Bit budget and band are almost unchanged.** The median paired payload difference is
  −0.03 kbit/s, and both conditions are all-SILK narrowband.
- **Fidelity descriptors are slightly worse under VOIP.** Per-utterance coherence is 0.614 vs
  0.623; LSD is 6.41 vs 6.14 dB; the image is a weaker copy of the input (0.093 vs 0.227).
- **The alignment spreads.** Most VOIP8 utterances have a 1-sample lag instead of 2.
- **No mechanism is inferred.** The slightly lower in-band fidelity did not raise WER for either
  recogniser. The mechanism behind Whisper's borderline tendency (for example the VOIP pre-filter
  or delay) is not examined, and is not examinable without mechanism fishing.

## 6. Answers to the required questions

1. **Is the total 8-kbit/s penalty application-mode sensitive?**
   - No clear application difference was established for either recogniser under the frozen rule.
   - The total penalty persisted under the VOIP application: +0.70 and +3.44 pp.
   - For Whisper the point estimate is 0.12 pp lower under VOIP, with an interval that just
     reaches zero. Two secondary cells exclude zero. A small Whisper sensitivity cannot be excluded.
   - This is not an equivalence result: no margin was pre-declared.
2. **Does the sign or magnitude materially change?**
   - The sign does not change: the penalty is positive in both recognisers and both subsets.
   - The magnitude changes by about 15 % of Whisper's total (−0.12 of +0.83 pp; not established)
     and by about 1 % of wav2vec2's.
   - The claim that 8 kbit/s Opus raises WER substantially, more for wav2vec2 than for Whisper,
     is unchanged.
3. **Must the manuscript be scoped explicitly to application=audio?**
   - Rule F applies: state the VOIP result only as a post-confirmation configuration sensitivity
     of the total penalty, without an equivalence claim.
   - The decomposition (bandwidth component, residual, shares) remains defined for the tested
     configuration (libopus 1.4, application=audio, forced SILK narrowband, FFmpeg decoding).
   - The Methods and Limitations should keep naming that configuration.
   - The manuscript need not restrict its *total-penalty* statements to application=audio. It
     should not imply generic WebRTC behaviour, because other deployment settings (FEC, DTX,
     packet loss, other versions) were not tested.
4. **Does VOIP alter the reviewer verdict?**
   - It removes a specific configuration objection: the total penalty is not an artefact of the
     `audio` application mode.
   - With R4, it also shows that Whisper's total penalty can move by about 0.1 pp with
     implementation or configuration details. This supports reporting pp contrasts with intervals
     and de-emphasising exact ratios (C1).
   - It does not change the recommendation.

## 7. Manuscript consequence (rule F)

- Replace the limitation "deployment-specific behaviour under `OPUS_APPLICATION_VOIP` was not
  evaluated" with the post-confirmation result:
  - the total penalty persisted under the VOIP application for both recognisers;
  - no clear difference from the audio application was established (Whisper −0.12 pp, upper
    bound 0.00; wav2vec2 −0.03 pp);
  - no equivalence is claimed;
  - the decomposition remains defined for application=audio.
- Add one sentence to the Results (Section 4.12) and one to the Discussion.
