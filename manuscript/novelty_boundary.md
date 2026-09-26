# Novelty boundary (literature-positioning audit, 2026-09-26)

**Scope question.** "How much of the ASR penalty of low-rate Opus is explained by bandwidth
loss, and how much remains as a codec-specific residual beyond a validated linear bandwidth
control?"

Evidence: `literature_matrix.md` (keys below refer to it). Our numbers come from
`results_paper/stage3_asr/` and `01b_interpretation_note_2026-09-26.md`.

## 1. Verdict: **NOVELTY_NARROW_BUT_DEFENSIBLE**

**Why not NOVELTY_CLEAR.**
- **The design idea is at least 32 years old.** Earlier work separated the band limitation of a transmission chain from its other distortions using an uncoded, band-limited reference:
  - telephone channels (moreno1994sources);
  - GSM (besacier2001effect, heymans2022multistyle);
  - AMR (bauer2010wtimit);
  - MP3 (borsky2015mp3);
  - GSM with current recognisers (basu2026factors, preprint).
- **A bandwidth-matched low-pass control for a codec already exists.** borsky2015mp3 matched the cutoff per bitrate from spectrograms.
- **The qualitative result has precedents.** "The codec residual exceeds the bandwidth component" was reported for AMR-NB 12.2 (bauer2010wtimit) and for low-rate MP3 (borsky2015mp3).
- **Two supporting facts are already published:**
  - wav2vec2-base-960h is far more sensitive to band limitation than Whisper (shah2025srb);
  - low-rate SILK coding raises WER even when bandwidth is (by implication) preserved (buethe2024nolace: Opus at 6 kb/s, with enhancement set-up implying WB SILK).

**Why not NOVELTY_THREATENED.** No located work answers the scope question for Opus. None of the following was found:
1. **A decomposition of a low-rate Opus/SILK-NB penalty.** The Opus–ASR studies located report only the total penalty (khare2020opus, jassim2020vocoders, jacobellis2024mpq, bai2026semdac, wang2025stcts, jones2022microphone, buethe2024nolace). One of them attributes the 8 kbit/s loss to narrowband operation without testing it (khare2020opus).
2. **A bandwidth control fitted to a codec's *measured* transfer function and validated on held-out speakers before ASR.** The nearest are a cutoff read from spectrograms (borsky2015mp3), neural-codec frequency responses measured but never used as a control (tseng2025probing), and measured channel responses used only to simulate training data (tarcisio1999simulated).
3. **A bandwidth/codec decomposition estimated for fixed, pretrained recognisers.** No study did this on identical paired audio, with speaker-level interval estimates, a pilot followed by a single pre-registered confirmation, and negative controls. Earlier decompositions used HMM-era systems, mostly retrained per condition. basu2026factors has two current recognisers but no decomposition and no statistics.
4. **A same-mode high-rate reference for Opus** (forced SILK-NB at 40 kbit/s). Analogues exist only for other codecs: G.711 64k and Speex-NB 24.6k.

**Why the increment matters.** Earlier decompositions reach codec-dependent answers:
- GSM FR at 13 kbit/s: mostly bandwidth (besacier2001effect, heymans2022multistyle).
- AMR-NB 12.2 and MP3 at 12 kbit/s: mostly residual (bauer2010wtimit, borsky2015mp3).

So the answer for low-rate Opus, and for current pretrained recognisers, could not be inferred from them. It had to be measured.

**Condition on the verdict.**
- The search had access limits (§8). ICASSP 2025–2026 papers were not systematically title-scanned, and several paywalled texts were read at abstract level only.
- The verdict holds as of 2026-09-26. Re-run the targeted queries in §8 before submission.

## 2. What prior work already establishes (do not claim any of these)

| # | Established finding | Evidence (keys) |
|---|---|---|
| E1 | Low-rate speech and audio codecs degrade ASR, roughly monotonically with bitrate | euler1994influence, lilly1996effect, besacier2001effect, hirsch2002influence, moller2002analytic, pollak2011mp3, borsky2015mp3, 3gpp2004tr26943 |
| E2 | Low-rate Opus degrades ASR, including Whisper | khare2020opus (8 kbit/s: +202 % relative), jassim2020vocoders, jacobellis2024mpq, bai2026semdac, wang2025stcts; buethe2024nolace (Opus 6 kb/s: 2.01 → 3.08 % WER; WB SILK inferred from the enhancement set-up, since the ASR encoder settings are not stated) |
| E3 | Codec effects measured against uncoded speech at the *same* bandwidth | lilly1996effect, hirsch2002influence, moller2002diagnostic, pelaezmoreno2001voip, vu2019codec |
| E4 | Explicit bandwidth-vs-codec (or bandwidth-vs-channel) decomposition in ASR | moreno1994sources, besacier2001effect, bauer2010wtimit, borsky2015mp3, heymans2022multistyle. Partial: moller2002analytic, fernandezgallardo2017predicting, morales2007nodalida, basu2026factors |
| E5 | The same idea in adjacent tasks | speaker verification: fernandezgallardo2014advantages; emotion recognition: lech2020ser; perceptual quality: waltermann2010dimensions, codec-results-03 (Opus NB tied with a 3.5 kHz low-pass anchor) |
| E6 | A codec-matched (by cutoff) low-pass control in ASR | borsky2015mp3 |
| E7 | The residual can exceed the bandwidth part (AMR-NB, MP3), or be smaller (GSM FR) | bauer2010wtimit, borsky2015mp3 / besacier2001effect, heymans2022multistyle |
| E8 | wav2vec2-base-960h is far more band-limit-sensitive than Whisper; with matched training, LibriSpeech holds little ASR information above 4 kHz | shah2025srb; likhomanenko2021rethinking, li2019ssrasr, sukhadia2023channelaware |
| E9 | Low-rate SILK coding alone (bandwidth preserved, by implication of the set-up) raises WER; SILK's low-rate behaviour is documented | buethe2024nolace; skoglund2020opus, vos2013voice |
| E10 | Component-isolating re-synthesis to attribute an ASR penalty is established. A preprint already pairs Whisper-large-v3 with wav2vec2 and a paired bootstrap for such an analysis in speech enhancement | iwamoto2022artifacts, ochiai2024rethinking, sehr2010reverberation, vipperla2010ageing; huo2026polar (preprint) |
| E11 | Opus decoder resampling is implementation-defined within conformance limits | rfc6716 §4.2.9 and §6; ffmpeg-6.1.1-opusdec |

## 3. What this paper adds (defensible if stated descriptively)

| # | Increment | Nearest prior work and the difference |
|---|---|---|
| A1 | A bandwidth vs residual decomposition of the **8 kbit/s Opus** penalty, where libopus 1.4 selects SILK-NB because the rate is below its 9 kbit/s wideband threshold | Located Opus–ASR work reports total penalties only. khare2020opus assumes the loss is a narrowband effect; basu2026factors includes Opus at an unstated rate with no matched control |
| A2 | A control fitted to SILK-NB's **measured linear transfer function** and **validated on held-out speakers** before any ASR run. The validation history is reported, including the failed first Gate 5 | borsky2015mp3 matched the cutoff only, with no validation. tseng2025probing measured responses but built no control. tarcisio1999simulated used measured channel responses for training data |
| A3 | **Fixed pretrained** recognisers of two architectures (Whisper large-v3, wav2vec2-base-960h) on identical paired audio. Speaker-cluster bootstrap CIs, a pilot plus a single pre-registered confirmation, and negative controls | Earlier decompositions used HMM-era, mostly retrained systems without uncertainty estimates. basu2026factors has two current models but no decomposition or statistics. moller2002analytic had two HMM-era recognisers |
| A4 | A **same-mode high-rate reference** (forced SILK-NB, 40 kbit/s) that shares the decode path | G.711 or Speex-NB served as high-rate same-band codecs for other codecs (besacier2001effect, moller2002analytic, fernandezgallardo2017predicting). No Opus version found |
| A5 | An explicit definition of the residual relative to the actual decode chain (libopus 1.4 encoder + FFmpeg 6.1.1 native decoder), including its implementation-specific 4–5 kHz image | RFC 6716 §4.2.9 leaves resampling to the implementation. FFmpeg's interpolator differs from the reference decoder's. [The link between that interpolator and our image is an inference from source code, not a measurement] |

## 4. Closest designs compared with ours

| Feature | moreno1994sources | besacier2001effect | bauer2010wtimit | borsky2015mp3 | heymans2022multistyle | basu2026factors (preprint) | **This paper** |
|---|---|---|---|---|---|---|---|
| Degradation | Telephone channel (no codec) | GSM FR 13 kbit/s | AMR-NB 12.2 (+AMR-WB, real 3G) | MP3 12–128 kbit/s | GSM FR (WAV49) | GSM; Opus (rate unstated) | **Opus 8 kbit/s (SILK-NB)** |
| Bandwidth control | Downsampling + typical-channel filter | Downsampling (8 kHz model) | Decimation | FIR low-pass at cutoff read from spectrograms | Downsampling | 3.4 kHz low-pass + resampling | **Zero-phase FIR fitted to measured SILK-NB \|H1\|, validated on held-out speakers** |
| Control matched to codec | No | No | No | Cutoff only | No | No | **Transfer function** |
| Recogniser(s) | SPHINX-I / SPHINX-II | RAPHAEL (HMM) | HTK HMM | Kaldi GMM-HMM | DNN-HMM | Conformer; Whisper-large-v3 (Hindi fine-tune) | **Whisper large-v3; wav2vec2-base-960h** |
| Models retrained per condition | Yes | Yes (per bandwidth) | Yes | No | Yes | No | **No** |
| Task / metric | Phone error (TIMIT) | Word accuracy (French) | Phone accuracy (TIMIT) | WER (Czech LVCSR) | WER (LibriSpeech dev) | WER (Hindi) | **WER (LibriSpeech test-clean/other)** |
| Decomposition reported | Yes | Yes | Yes | Yes (+ non-additivity noted) | Yes (training framing) | No | **Yes, paired contrasts with 95 % CIs** |
| Uncertainty | None | None | None | None | SE over 3 seeds | None | **Speaker-cluster bootstrap; pre-registered** |
| High-rate same-codec reference | — | G.711 | — | — | — | — | **SILK-NB 40 kbit/s (forced)** |
| Direction | Band limitation ≈ 3 of 10.2 points | Bandwidth dominates | Codec > bandwidth | Residual ≫ low-pass | Bandwidth dominates | (figure) GSM residual > low-pass | **Residual > bandwidth in both recognisers** |

## 5. How our results sit relative to prior results (for the Discussion)

These comparisons are directional only. Recognisers, languages, training regimes and metrics differ across studies, so magnitudes are not comparable.

- **Residual vs bandwidth, by codec and rate.**
  - Our result (8 kbit/s Opus: residual > bandwidth) matches bauer2010wtimit (AMR-NB 12.2) and borsky2015mp3 (MP3 at 12 kbit/s).
  - It differs from besacier2001effect and heymans2022multistyle (GSM FR at 13 kbit/s: mostly bandwidth).
  - Our high-rate SILK-NB reference (no detectable pooled residual) sits on the GSM-FR side of that pattern.
  - Wording: across these studies, the size of the residual is **consistent with** a dependence on codec and coding rate rather than on narrowband operation as such. No study, including ours, tests that dependence directly.
- **Bandwidth component by recogniser.**
  - Our result: +1.40 pp (wav2vec2) vs +0.14 pp (Whisper).
  - This agrees in direction with shah2025srb (audio-processing NWERD: 30.6 for wav2vec2-base-960h vs 6.9 for whisper-large-v2).
  - It is also consistent with the small bandwidth-only costs under matched training (likhomanenko2021rethinking; li2019ssrasr; sukhadia2023channelaware).
- **Residual.**
  - Consistent with buethe2024nolace (Opus 6 kb/s: +1.07 pp for a Conformer; bandwidth preserved if, as the enhancement set-up implies, the test encoder was wideband SILK).
  - Consistent with skoglund2020opus ("as the rate drops below 10 kb/s, quality degrades quickly"; residual bits starve below 8 kb/s).
- **The narrowband-attribution assumption.**
  - khare2020opus attributed the 8 kbit/s collapse to narrowband operation. In our setting bandwidth removal explains 17 % (Whisper) and 40 % (wav2vec2) of the total penalty.
  - State this as a finding for our recognisers and data, not as a refutation (different system and data).
- **Perception vs recognition.**
  - Perceptually, Opus NB at 11 kb/s was tied with a 3.5 kHz low-pass anchor (codec-results-03).
  - For recognition at 8 kb/s, we find a residual beyond a matched low-pass.
  - The rates differ (11 vs 8 kb/s), so present this as an observation, not a contrast.

## 6. Proposed contribution statement (descriptive; no priority claim)

> We measure how much of the word-error-rate increase caused by 8 kbit/s Opus, which
> libopus 1.4 encodes in SILK narrowband mode, is reproduced by removing bandwidth alone. The
> bandwidth control is a zero-phase linear low-pass filter fitted to the measured linear
> transfer function of SILK narrowband, calibrated on one set of speakers and validated on
> held-out speakers before any recognition experiment. In a pre-registered paired design on
> LibriSpeech (a pilot, then one confirmatory run with 2,174 utterances from 73 speakers),
> the control increased WER by 0.14 percentage points for Whisper large-v3 and 1.40 points
> for wav2vec2-base-960h. Opus increased WER by a further 0.69 and 2.07 points beyond the
> control, with 95 % speaker-bootstrap intervals excluding zero. Bandwidth removal therefore
> accounted for about 17 % and 40 % of the total Opus penalty. High-rate SILK narrowband
> showed no detectable pooled residual. The design follows earlier comparisons of coded and
> band-limited uncoded speech for telephone channels, GSM, AMR and MP3 [moreno1994sources;
> besacier2001effect; bauer2010wtimit; borsky2015mp3]. We apply it to a codec whose audio
> bandwidth the encoder selects from the bitrate, with a codec-matched control and two
> current pretrained recognisers.

Bullet form for the Introduction:
1. **A bandwidth control for Opus SILK narrowband.** A linear-phase low-pass fitted to the codec's measured linear transfer function and validated on held-out speakers against pre-specified tolerances. The validation history, including a failed first criterion, is reported.
2. **A pre-registered, paired estimate of the two components of the 8 kbit/s Opus penalty.** The bandwidth component and the codec-specific residual are estimated for Whisper large-v3 and wav2vec2-base-960h, with speaker-cluster bootstrap intervals and negative controls.
3. **A same-mode high-rate reference and signal descriptors.** Forced SILK narrowband at 40 kbit/s, plus descriptors that constrain the mechanism of the residual but do not identify it.

## 7. Reviewer risks and prepared responses

| Risk | Response in the paper |
|---|---|
| R1 "Incremental over bauer2010wtimit, borsky2015mp3 and besacier2001effect" | Cite them in the Introduction as the origin of the design. Present the paper as a controlled measurement for Opus with current pretrained recognisers and a validated codec-matched control, not as a new concept. Stress that the earlier answers depend on the codec. |
| R2 "The additive split ignores interaction" (borsky2015mp3: "non-linear combination") | The decomposition is sequential (REF → LP → OPUS) and exact by construction, but path-dependent. The residual includes any interaction between band limitation and coding, and the "bandwidth share" is a share along this path. A factorial design (for example, forced-wideband Opus at 8 kbit/s, a Stage 2A cell never run through ASR) would be needed to estimate the interaction. This matches limitation F.19. **Add one sentence on path-dependence to Methods.** |
| R3 "The residual contains decoder artefacts" | Define the residual for libopus 1.4 + FFmpeg 6.1.1. Cite RFC 6716 §4.2.9 for non-normative resampling and the FFmpeg source for its interpolator. Point to SILK-40k, which shares the decode path and shows no pooled residual. List re-decoding with the libopus reference decoder as an untested sensitivity check (a new experiment; not run). |
| R4 "Version dependence" | Name libopus 1.4. 8 kbit/s → NB holds in every version checked (v1.0.3–v1.6.1). 12 kbit/s → WB holds only from v1.2 onward. |
| R5 "Retrained systems would give a different split" | The question concerns deployed pretrained recognisers used without retraining. Retrained-system decompositions (besacier2001effect, bauer2010wtimit, heymans2022multistyle) answer a different question; say so. |
| R6 "Whisper's low band-limit sensitivity is known" | Do not present it as a finding. Cite shah2025srb as external consistency. |
| R7 "basu2026factors already paired a low-pass control with codecs for Whisper" | Cite it. It uses GSM (not SILK-NB), a generic filter, no decomposition, no statistics, Hindi rather than LibriSpeech, and an unstated Opus rate. |
| R8 "Pre-registration is internal" | Already disclosed (limitation E.17). |
| R9 Anonymity | A searcher found the public course repository (github.com/surnamemei/elec5305-project-…) indexed by search engines. For a double-blind venue, check the policy, avoid self-identifying links, and do not cite the unpublished course report. |

## 8. Wording rules

**Use:**
- "Earlier studies separated band limitation from coding distortion for telephone channels, GSM, AMR and MP3 [..]; we apply the same logic to 8 kbit/s Opus."
- "The Opus–ASR studies we located report the total penalty and do not include a bandwidth control."
- "fitted to the codec's measured linear response and validated on held-out speakers"
- "in our setting, bandwidth removal accounted for 17 % and 40 % of the total penalty"
- "consistent with low-rate in-band coding distortion; the mechanism was not tested"

**Do not use:**
- "first", "novel", "for the first time", "unprecedented", "no prior work has …", "to our knowledge, the first …"
- "caused by coding distortion" (causal)
- "Whisper is robust to bandwidth loss" as a new result
- "the components are independent / additive" without the path-dependence caveat
- "12 kbit/s lies in the RFC's wideband operating region". RFC 6716 §2.1.1 puts 8–12 kbit/s in the *NB* sweet spot; wideband at 12 kbit/s is libopus ≥ 1.2 behaviour.
- "the decoder may resample arbitrarily". It is non-normative but conformance-bounded.
- Priority claims about the matched control. Say what it is and cite borsky2015mp3 as the nearest precedent.

## 9. Search limits and re-check list (before submission)

- **Not systematically covered:**
  - ICASSP 2025–2026 (IEEE Xplore not machine-readable);
  - content of *Speech Communication* and ScienceDirect items (403);
  - the AES E-Library;
  - ITU-T recommendation texts.
- **Covered:** Interspeech 2021–2026 titles were scanned; arXiv, ACL Anthology, Crossref and OpenAlex were queried.
- **Re-run before submission:**
  1. arXiv, ICASSP 2026 and Interspeech 2026 for "Opus" with "Whisper" or "wav2vec" plus "bandwidth", "low-pass" or "narrowband".
  2. A published version of basu2026factors (it may add Opus settings).
  3. Borský et al. 2017 (*Speech Communication* 86) and Cauchi et al. 2025 (*Speech Communication* 173), not yet readable.
  4. Málek 2018 (TSD) full text.
- **Priority leads to read:** Borský 2017 (it may extend the bandwidth-vs-spectral-valley analysis for MP3) and any 2026 codec-ASR study using Whisper with a band-limited control.
