# Literature matrix (literature-positioning audit, 2026-09-26)

**Scope question.** "How much of the ASR penalty of low-rate Opus is explained by bandwidth
loss, and how much remains as a codec-specific residual beyond a validated linear bandwidth
control?"

**How this matrix was built.**
- Six searches were run in parallel on 2026-09-26, one per category group: 1+2, 3, 4, 5, 6, 7. Category 5 was searched by the lead author of this note, the others by delegated searchers under the same rules.
- Every record below was confirmed on a primary or authoritative page: publisher or DOI landing page, ISCA Archive, ACL Anthology, arXiv, RFC Editor or IETF Datatracker, ETSI deliver server, official source repository at a pinned tag, Crossref, or OpenAlex.
- No field was filled from memory. Where a field could not be read, it is marked U (unknown).
- The key claims that bound the novelty were re-checked against the full texts: Moreno 1994, Besacier 2001, Bauer 2010, Borský 2015, Heymans 2022, Basu 2026, Speech Robust Bench, NoLACE, Khare 2020, RFC 6716 and libopus/FFmpeg source.
- Companion files: `novelty_boundary.md` (verdict and claim limits) and `related_work_notes.md` (draft prose).

**Legend**

| Code | Meaning |
|---|---|
| Ev FT / AB / MD | Evidence level: full text read / abstract only / metadata only |
| S2 | Bandwidth and coding (or other) effects are quantified separately (explicit decomposition) |
| S1 | Partial or implicit separation. Either bandwidth is held fixed (codec vs uncoded speech at the same band), or the design permits separation but the authors do not compute it |
| S0 | No separation |
| M3 | Bandwidth control fitted to the codec's *measured* transfer function and validated on held-out data. **None found in this search; this is our design** |
| M2 | Control matched to the codec's observed cutoff (e.g., per-bitrate cutoff read from spectrograms) |
| M1 | Nominal band limitation: decimation to 8 kHz, a fixed 3.4 kHz low-pass, or a G.712/P.341 mask |
| M0 | No bandwidth control |
| NA | Not applicable |
| Multi | Whether more than one recogniser was run under identical conditions |
| THREATENS (generic) | Pre-empts a *generic* claim we might otherwise make ("first to separate bandwidth from coding", "first matched control", "first to show X"). Must be cited; the claim must not be made |
| NARROWS | Partial overlap. Cite and differentiate |
| SUPPORTS | Consistent evidence or a citable foundation |
| CONTEXT | Background |

Preprints are flagged "(preprint, not peer-reviewed)".

---

## 1. Summary matrix: works that bound the novelty

| Key | Year · venue | Cat | Recogniser(s) | Codec / bandwidth manipulation | Sep | LP | Multi | Relation |
|---|---|---|---|---|---|---|---|---|
| moreno1994sources | 1994 · ICASSP | 1,5,6 | SPHINX-I; SPHINX-II | TIMIT full band vs 8 kHz vs telephone-filtered vs NTIMIT; channel simulator, one impairment at a time; no codec | S2 | M1 | 2 (different experiments) | THREATENS (generic) |
| besacier2001effect | 2001 · IEEE MMSP | 4,5 | RAPHAEL (Janus-III) HMM; 16 and 8 kHz models | GSM FR, G.711, G.723.1 vs uncoded 8 kHz; MPEG-1 L1–3 at 8–64 kbit/s | S2 | M1 | N | THREATENS (generic) |
| bauer2010wtimit | 2010 · LREC | 1,4,5 | HTK HMM phone recogniser, retrained per condition | TIMIT vs decimated 8 kHz vs AMR-NB 12.2 / AMR-WB 12.65 (simulated and real 3G) | S2 | M1 | N | THREATENS (generic) |
| borsky2015mp3 | 2015 · EURASIP JASMP | 4,5,6 | Kaldi GMM-HMM (PLP, MFCC) | MP3 12–128 kbit/s; uncoded low-passed at per-bitrate cutoffs (7.2/5.8/5.6 kHz); "spectral valleys" condition | S2 | M2 | N | THREATENS (generic) |
| heymans2022multistyle | 2022 · SACAIR (CCIS) | 4,5 | DNN-HMM, retrained | GSM FR (WAV49) at 8 kHz; 16 kHz vs 8 kHz uncoded vs encoded training | S2 (training-mismatch framing) | M1 | N | NARROWS |
| moller2002analytic | 2002 · Speech Commun. | 1,4,5 | Swiss-French HMM/ANN; German HMM | G.712 channel ± G.711, G.726, G.728, G.729, IS-54, tandems | S1 | M1 | 2 | NARROWS |
| moller2002diagnostic | 2002 · LREC | 4,5 | Three (HMM/ANN; HMM keyword; AURORA HTK) | Same simulator; codecs vs the G.711 default connection | S1 | M1 | 3 | NARROWS |
| fernandezgallardo2017predicting | 2017 · Interspeech | 1,4,5 | CMU Sphinx-4 (matched training) | NB/WB/SWB codecs plus uncoded 8/16/32 kHz references | S1 | M1 | N | NARROWS |
| morales2007nodalida | 2007 · NODALIDA | 1,5 | HMM phone recogniser | TIMIT low-pass 6/4 kHz and 300–3400 Hz vs a real telephone channel | S1 | M1 | N | NARROWS |
| basu2026factors | 2026 · arXiv (preprint) | 1,4,5,7 | Indic-Conformer-hi; Whisper-large-v3 Hindi fine-tune | GSM; 3.4 kHz low-pass + 8 kHz resampling "to isolate bandwidth"; Opus (rate unstated) | S1 | M1 | 2 | NARROWS (closest modern) |
| shah2025srb | 2025 · ICLR | 7 | About 20, **including wav2vec2-base-960h and Whisper tiny–large-v2** | Low-pass 4 kHz → 0.5 kHz, resampling and others; **no codecs** | NA | M0 | Y | THREATENS (generic: our models' band-limit sensitivity is already measured) |
| buethe2024nolace | 2024 · ICASSP | 3,4 | SpeechBrain Conformer + LM | Opus at 6/9/12/20 kb/s ± LACE/NoLACE (WB SILK implied by the set-up; ASR encoder settings not stated) | S1 (WB, inferred) | M0 | N | THREATENS (generic: low-rate SILK coding alone raises WER) |
| tseng2025probing | 2025 · Interspeech | 4,5 | Whisper-large (evaluator) | Neural codecs; codec frequency responses measured with sine sweeps | S1 | M0 | N | NARROWS (measuring a codec's linear response is not new) |
| iwamoto2022artifacts | 2022 · Interspeech | 6 | Kaldi DNN-HMM | SE output split by projection into target/noise/artifact; components re-scaled and decoded | NA | Partial (oracle) | N | NARROWS (method) |
| ochiai2024rethinking | 2024 · IEEE TASLP | 6 | Kaldi DNN-HMMs | As above, extended (interference/noise/artifact) | NA | Partial (oracle) | Partly | NARROWS (method) |
| sehr2010reverberation | 2010 · IWAENC | 6 | HTK HMM | Measured RIR: early part kept, tail attenuated | NA | Yes (exact partial channel) | N | NARROWS (method) |
| khare2020opus | 2020 · arXiv | 4 | LSTM hybrid + beamforming | Opus CBR 8/16/32/128 kbit/s per channel | S0 | M0 | N | SUPPORTS (motivation: 8 kbit/s loss attributed to narrowband, untested) |
| jassim2020vocoders | 2020 · QoMEX | 3,4 | Google STT | Opus 6 kb/s (NB SILK) vs 9 kb/s (WB SILK); vocoders | S0 | M0 | N | SUPPORTS / CONTEXT |
| drude2021opus | 2021 · Interspeech | 4 | RNN-T + MVDR | Opus 16–128 kbit/s per channel; SILK/CELT forced | S0 | M0 | N | CONTEXT |
| narayanan2018domain | 2018 · SLT | 4,7 | LSTM (low frame rate) | MP3/AAC training simulation; Opus 24k test | S0 | M0 | N | CONTEXT |
| likhomanenko2021rethinking | 2021 · Interspeech | 1,7 | Transformer-CTC | All data at 8 kHz vs 16 kHz (matched training) | NA | M1 | N | SUPPORTS (magnitude) |
| li2019ssrasr | 2019 · Interspeech | 2 | Hybrid LSTM/HMM | LibriSpeech test-clean downsampled to 8 kHz; BWE | NA | M1 | N | SUPPORTS (magnitude) |
| hirsch2000aurora | 2000 · ASR2000 | 1,6 | HTK digits | G.712 vs MIRS filter shapes at fixed bandwidth | NA | NA | N | SUPPORTS (filter shape matters, so fit it) |
| rfc6716 / libopus-1.4 / ffmpeg-6.1.1 | 2012–2023 · RFC, source | 3 | — | Modes, sweet spots, bandwidth thresholds, non-normative resampling | NA | NA | NA | SUPPORTS (Methods facts); NARROWS ("residual" includes a decoder-implementation component) |

No work in any category was found at level **M3**, and no work decomposes a low-rate
**Opus/SILK** penalty. See `novelty_boundary.md` for the resulting verdict.

---

## 2. Closest prior work: full records

### moreno1994sources
**Moreno, P. J., & Stern, R. M. (1994). Sources of degradation of speech recognition in the telephone network. *Proc. IEEE ICASSP 1994*, vol. 1, pp. I/109–I/112. doi:10.1109/ICASSP.1994.389343**
- **Verified:** CMU Robust Speech Group copy (https://www.cs.cmu.edu/~robust/Papers/ica94p.ps); Crossref · **Ev:** FT · **Categories:** 1, 5, 6
- **Recogniser:** CMU SPHINX-I (TIMIT/NTIMIT phone recognition); SPHINX-II (simulator experiments).
- **Corpus:** TIMIT, NTIMIT; CMU AN4.
- **Manipulation:**
  - TIMIT at 0–8 kHz; downsampled to 8 kHz (0–4 kHz); downsampled and filtered to approximate a typical telephone channel (250–3400 Hz); NTIMIT.
  - A commercial telephone-channel simulator (TAS 1010) applied one impairment at a time: C-message noise, impulse noise, a 180 Hz tone, jitter, intermodulation, and channel frequency responses.
  - No codec.
- **Separated:** S2, for band limitation vs other telephone-channel factors. Phone error: 47.3 % (0–8 kHz), 48.2 (0–4 kHz), 50.3 (250–3400 Hz), 57.5 (NTIMIT).
- **Matched LP:** M1 (nominal filter; not fitted to the NTIMIT channels) · **Multi:** two SPHINX versions, but in different experiments.
- **Establishes:** Band limitation plus linear filtering accounted for 3.0 of the 10.2-point gap. Quote: "bandwidth limitations and other linear filtering effects are not the sole source of the observed degradation". In simulation, additive noise, impulse noise and low-frequency tones dominated.
- **Relation: THREATENS (generic).** The logic "reproduce the band limitation of a transmission chain with an uncoded control and attribute the remainder to other factors" is 32 years old. Our differences: a codec rather than a channel; a transfer-function-matched, validated control; current pretrained recognisers; paired inference.

### besacier2001effect
**Besacier, L., Bergamini, C., Vaufreydaz, D., & Castelli, E. (2001). The effect of speech and audio compression on speech recognition performance. *Proc. IEEE Fourth Workshop on Multimedia Signal Processing (MMSP)*, Cannes, pp. 301–306. doi:10.1109/MMSP.2001.962750**
- **Verified:** HAL author copy (https://inria.hal.science/inria-00326165); Crossref · **Ev:** FT · **Categories:** 4, 5
- **Recogniser:** RAPHAEL (Janus-III) French continuous recogniser. Acoustic models were trained on BREF80 at 16 kHz or downsampled to 8 kHz; 5k and 28k trigram LMs.
- **Corpus:** CSTAR120 (tourism, 5k vocabulary); AUPELF (newspaper, 28k).
- **Manipulation:** GSM FR (13 kbit/s), G.711 and G.723.1 (5.3 kbit/s), tested against uncoded 8 kHz speech with the 8 kHz model. MPEG-1 Layers 1–3 at 8–64 kbit/s, tested against uncoded 16 kHz speech.
- **Separated:** S2 (16 kHz uncoded → 8 kHz uncoded → GSM FR). AUPELF word accuracy: 61.2 % → 49.7 % → 46.3 %. CSTAR120: 92.3 → 91.6 → 91.6 %.
- **Matched LP:** M1 (downsampling defines the band; a separate 8 kHz-trained model is used) · **Multi:** N
- **Establishes:** For GSM FR the loss relative to wideband is "mainly due to the bandlimiting and not to the GSM transcoding". MPEG coding below 32 kbit/s is severe.
- **Relation: THREATENS (generic).** This is an explicit 2001 separation of band limitation from a narrowband codec against a bandwidth-matched uncoded reference.
  - Its result has the **opposite emphasis** to ours: the bandwidth component dominated for a 13 kbit/s codec. This is consistent with our high-rate SILK reference (no pooled residual).
  - The bandwidth contrast also changes the acoustic model (retrained per band), unlike our fixed models.

### bauer2010wtimit
**Bauer, P., Scheler, D., & Fingscheidt, T. (2010). WTIMIT: The TIMIT speech corpus transmitted over the 3G AMR wideband mobile network. *Proc. LREC 2010*, Valletta, ELRA, pp. 1566–1570 (pages printed on the ACL Anthology PDF). ACL Anthology L10-1198; Crossref doi:10.63317/4gfner9csunj**
- **Verified:** https://aclanthology.org/L10-1198/ and the LDC-hosted PDF · **Ev:** FT · **Categories:** 1, 4, 5
- **Recogniser:** HTK HMM phone recogniser: 48 models, 3 states, 16 Gaussians, 39-dim MFCC. It has a wideband (26 filters, 0–8 kHz) and a narrowband (23 filters, 0–4 kHz) front-end, and is retrained per condition.
- **Corpus:** TIMIT and derivatives.
- **Manipulation:** TIMIT; TIMIT decimated to 8 kHz "using a high-quality lowpass filter"; AMR-NB 12.2 and AMR-WB 12.65 fixed-point simulations; real 3G AMR-NB and AMR-WB transmission (WTIMIT).
- **Separated:** S2. Section 4.2.1 is titled "Effects of Bandwidth, Codec, and Channel".
  - Bandwidth (TIMIT vs TIMIT↓2): −1.45 % phone accuracy.
  - Narrowband codec (TIMIT↓2 vs + AMR-NB sim): −2.28 %.
  - Wideband codec: −1.55 %.
  - Codec plus real channel: −6.05 / −6.29 %.
- **Matched LP:** M1 (generic decimation; not matched to AMR-NB's response and not validated) · **Multi:** N
- **Establishes:** With matched training, the AMR-NB 12.2 codec effect exceeded the bandwidth effect. Simulating codecs alone understates real-network losses.
- **Relation: THREATENS (generic).** This is the closest classic precedent for our decomposition logic, **and it found the same direction** (codec > bandwidth). It did not cover:
  - Opus/SILK;
  - fixed pretrained recognisers (each condition was retrained);
  - word error rate on read English (it measured phone accuracy);
  - a matched or validated control, a second recogniser, a high-rate same-codec reference, or statistics.

### borsky2015mp3
**Borský, M., Pollák, P., & Mizera, P. (2015). Advanced acoustic modelling techniques in MP3 speech recognition. *EURASIP Journal on Audio, Speech, and Music Processing*, 2015:20. doi:10.1186/s13636-015-0064-7**
- **Verified:** SpringerOpen full text and Table 6 (HTML); Crossref · **Ev:** FT · **Categories:** 4, 5, 6
- **Recogniser:** Kaldi GMM-HMM (triphones; LDA, SAT/fMLLR, SGMM, MMI), with PLP and MFCC features, trained on uncompressed speech.
- **Corpus:** Czech SPEECON and TEMIC, 16 kHz; phoneme task and 1 h LVCSR test.
- **Manipulation:**
  - MP3 (LAME/SoX) at 128–12 kbit/s.
  - **Low-pass condition:** "The uncompressed signals were filtered by a FIR low-pass filter at corresponding cutoff frequencies, which were estimated for each bit-rate from their spectrograms" (7.2, 5.8 and 5.6 kHz).
  - **Spectral-valley condition:** suppressed bins above the cutoff are replaced by uncoded bins.
- **Separated:** S2. LVCSR WER (MMI models):
  - Raw: 14.25 (PLP) / 14.22 (MFCC).
  - Low-pass at 5.6 kHz: 14.54 / 14.86.
  - MP3 at 12 kbit/s: 25.23 / 31.54.
  - Spectral valleys at 12 kbit/s: 16.68 / 19.70.
- **Matched LP:** **M2** (cutoff matched per bitrate; not a measured transfer function; no held-out validation) · **Multi:** N (one system, two feature types)
- **Establishes:** A cutoff-matched low-pass explains a tiny part of the MP3 penalty. Quote: the increase "was the result of the non-linear combination of both distortions".
- **Relation: THREATENS (generic).** This is the only prior codec-ASR study found with a bandwidth-matched low-pass control on uncoded speech, so we cannot claim a "first matched low-pass control". Its direction (residual ≫ low-pass) agrees with ours. Its non-additivity statement is a caveat for our sequential REF→LP→OPUS decomposition (see `novelty_boundary.md` §7).

### heymans2022multistyle
**Heymans, W., Davel, M. H., & van Heerden, C. (2022). Multi-style training for South African call centre audio. In *Artificial Intelligence Research (SACAIR 2021)*, Communications in Computer and Information Science, Springer, pp. 111–124. doi:10.1007/978-3-030-95070-5_8 (arXiv:2202.07219)**
- **Verified:** arXiv full text; Crossref · **Ev:** FT · **Categories:** 4, 5
- **Recogniser:** PyTorch-Kaldi MLP DNN-HMM (fMLLR), retrained per condition.
- **Corpus:** LibriSpeech train-clean-100 / dev-clean; proprietary South African call-centre data.
- **Manipulation:** WAV49 (GSM 06.10 full rate) at 8 kHz; models trained at 16 or 8 kHz, on encoded or unencoded audio.
- **Separated:** S2, in a training-mismatch framing. A clean 16 kHz model gives 8.88 % on dev-clean and 19.32 % on encoded dev. An 8 kHz clean-trained model gives 11.44 % on encoded dev; encoding the training data adds a further 2.0 % relative.
- **Matched LP:** M1 (downsampling) · **Multi:** N
- **Establishes:** "most of the mismatch is a result of the difference in sampling rate and not due to encoding."
- **Relation: NARROWS.** Another bandwidth-vs-codec separation for GSM FR, again with bandwidth dominating. Its question is training mismatch, not a fixed model's decomposition.

### moller2002analytic
**Möller, S., & Bourlard, H. (2002). Analytic assessment of telephone transmission impact on ASR performance using a simulation model. *Speech Communication*, 38(3–4), 441–459. doi:10.1016/S0167-6393(02)00013-4**
- **Verified:** Crossref; IDIAP-RR 01-17 full text (https://publications.idiap.ch/attachments/reports/2001/rr01-17.pdf) · **Ev:** FT (report version) · **Categories:** 1, 4, 5
- **Recognisers:** Swiss-French hybrid HMM/ANN (trained on PolyPhone telephone calls); German commercial HMM keyword spotter.
- **Corpus:** 150 Swiss-French utterances (10 speakers); 395 German keywords × 10 speakers.
- **Manipulation:** An E-model-parameterised network simulator. The default channel is a G.712 band-pass; codecs G.711, G.726 (32), G.728 (16), G.729 (8), IS-54 (7.95) and tandems; noise; MNRU.
- **Separated:** S1. Codec effects are measured on top of an uncoded G.712 channel, and the drop on that default channel is attributed to band limitation. There is no formal decomposition.
- **Matched LP:** M1 (nominal G.712 mask) · **Multi:** Y (2)
- **Establishes:** Codec effects on ASR are recogniser-specific and not predicted by E-model quality. Quote: "The strict bandwidth limitation applied in the current simulation model (G.712 filter) seems to be responsible for the decrease".
- **Relation: NARROWS** (codec vs band-limited uncoded channel, with two recognisers).

### fernandezgallardo2017predicting
**Fernández Gallardo, L., Möller, S., & Beerends, J. (2017). Predicting automatic speech recognition performance over communication channels from instrumental speech quality and intelligibility scores. *Proc. Interspeech 2017*, pp. 2939–2943. doi:10.21437/Interspeech.2017-36**
- **Verified:** ISCA Archive PDF · **Ev:** FT · **Categories:** 1, 4, 5
- **Recogniser:** CMU Sphinx-4 (training and test matched per channel).
- **Corpus:** AusTalk subset (37 speakers, 322 words).
- **Manipulation:**
  - NB (G.712 filter): G.711, G.723.1, GSM-EFR, AMR-NB 4.75/12.2, Speex-NB 2.15/11/24.6.
  - WB (P.341 filter): G.722, AMR-WB, Speex-WB.
  - SWB: G.722.1C.
  - Plus "direct speech sampled as 8, 16, or 32 kHz" with "no bandwidth filter or codec applied".
- **Separated:** S1. The references allow separation, but no decomposition is reported. Example WERs: NB uncoded 19.6 %, WB uncoded 15.3 %, AMR-NB 4.75 27.3 %.
- **Matched LP:** M1 (the reference matches the sampling rate, not the channel filter) · **Multi:** N
- **Establishes:** ASR improves from NB to WB but not from WB to SWB; WER is predictable from instrumental quality/intelligibility scores.
- **Relation: NARROWS.** Uncoded bandwidth-matched references sit next to NB and WB codecs in ASR work.

### morales2007nodalida
**Morales, N., Toledano, D. T., Hansen, J. H. L., & Garrido, J. (2007). Multivariate cepstral feature compensation on band-limited data for robust speech recognition. *Proc. NODALIDA 2007*, Tartu, pp. 144–151. ACL Anthology W07-2421**
- **Verified:** ACL Anthology PDF · **Ev:** FT · **Categories:** 1, 5
- **Recogniser:** HMM phonetic recogniser (51 HMMs, MFCC over 0–8 kHz), trained on TIMIT.
- **Corpus:** TIMIT; STC-TIMIT (TIMIT sent through one real telephone line).
- **Manipulation:** Low-pass at 6 and 4 kHz, a 300–3400 Hz band-pass, and a real telephone channel.
- **Separated:** S1. Matched-training accuracy: band-pass 65.73 % vs real telephone channel 61.80 %. The residual lumps converters, network and noise; no codec is isolated.
- **Matched LP:** M1 · **Multi:** N
- **Establishes:** A real channel leaves a residual beyond a nominal telephone-band filter, even with matched training.
- **Relation: NARROWS** (a "residual beyond band limitation" for a channel, not a codec).

### basu2026factors
**Basu, A., Kumar J, P., Bhat, P., Pulikodan, S., Sanka, V., Desai, N., & Ghosh, P. K. (2026). Factors affecting ASR performance: A study using state of the art ASR models in Indic languages. arXiv:2606.09335v1 (8 Jun 2026). Preprint, not peer-reviewed; no venue stated.**
- **Verified:** https://arxiv.org/abs/2606.09335 and PDF (read twice independently) · **Ev:** FT · **Categories:** 1, 4, 5, 7
- **Recognisers (audio-factor experiments):** Indic-Conformer-hi; Vaani-Whisper-L-hi (Whisper-large-v3 fine-tuned for Hindi).
- **Corpus:** Hindi FLEURS and Kathbath test sets.
- **Manipulation:**
  - "GSM (2G)": 8 kHz + GSM + resample.
  - "Narrowband (3G) speech is simulated via 3.4 kHz low-pass filtering and 8 kHz resampling to isolate bandwidth limitation without codec artifacts".
  - "Wideband (4G)": 8 kHz low-pass.
  - "Opus (5G)": bitrate and mode not stated.
  - Also neural BWE, bit depth and noise.
- **Separated:** S1. The control exists, but no decomposition or statistics are reported; results appear only in figures. Approximate values read from Fig. 2b show GSM exceeding the narrowband control by about 1.5–3 WER points while the control costs about 0.2–1.2 points. The authors nevertheless conclude that "bandwidth limitation is the most critical".
- **Matched LP:** M1 (a generic 3.4 kHz filter, not matched to GSM or Opus) · **Multi:** Y (2)
- **Establishes:** Uncoded band-limited controls have now been run alongside codecs with a Whisper-class model.
- **Relation: NARROWS (closest modern overlap).** It differs from ours in:
  - codec: GSM plus an unspecified Opus configuration (its "marginal" Opus penalty suggests a wideband setting);
  - no SILK-NB condition;
  - a generic, unvalidated filter;
  - no decomposition;
  - Hindi rather than LibriSpeech;
  - no wav2vec2 CTC model, no statistics, and no negative controls.
  
  It also illustrates the misattribution that an explicit decomposition prevents.

### shah2025srb
**Shah, M. A., Solans Noguero, D., Heikkilä, M. A., Raj, B., & Kourtellis, N. (2025). Speech Robust Bench: A robustness benchmark for speech recognition. *Proc. ICLR 2025*, pp. 38625–38651. arXiv:2403.07937**
- **Verified:** ICLR proceedings page and BibTeX; arXiv v3 PDF (perturbation table and model list re-checked) · **Ev:** FT · **Categories:** 7 (also 1)
- **Recognisers:** About 20 English models, **including wav2vec2-base-960h** and Whisper tiny/base/small/medium/large-v2, plus HuBERT, Canary and Parakeet models.
- **Corpus:** LibriSpeech test-clean, TED-LIUM 3 and MLS-Spanish (synthetic perturbations); CHiME-6, AMI and others.
- **Manipulation:** 114 perturbations, including a low-pass filter at severities 4 kHz, 2833, 1666 and 500 (the table prints "kHz"; presumably Hz) and resampling at 0.75× to 0.125×. **No codec or compression perturbation.**
- **Separated:** NA (no codecs) · **Matched LP:** M0 (low-pass is a perturbation, not a control) · **Multi:** Y
- **Establishes:** Whisper-large is the most robust on average. The "audio processing" robustness score (NWERD, including low-pass) is 30.6 for wav2vec2-base-960h vs 6.9 for whisper-large-v2.
- **Relation: THREATENS (generic)** any claim to be the first to measure band-limitation sensitivity of our two model families. **SUPPORTS** our direction: wav2vec2 is far more bandwidth-sensitive than Whisper (our LP − REF: +1.40 vs +0.14 pp).

### buethe2024nolace
**Büthe, J., Mustafa, A., Valin, J.-M., Helwani, K., & Goodwin, M. M. (2024). NoLACE: Improving low-complexity speech codec enhancement through adaptive temporal shaping. *Proc. IEEE ICASSP 2024*, pp. 476–480. doi:10.1109/ICASSP48485.2024.10448332 (arXiv:2309.14521)**
- **Verified:** Crossref; arXiv full text (ASR table re-read) · **Ev:** FT · **Categories:** 3, 4
- **Recogniser:** SpeechBrain Conformer with Transformer LM (asr-conformer-transformerlm-librispeech).
- **Corpus:** LibriSpeech test-clean (ASR); NTT database (P.808).
- **Manipulation:** Opus at 6, 9, 12 and 20 kb/s, with LACE, NoLACE or LPCNet resynthesis.
  - Training used "a patched version of libopus that restricts Opus to linear-predictive mode and wideband encoding".
  - The ASR encoder configuration is not stated, but the enhancers act only on WB SILK frames.
- **Separated:** S1 (bandwidth effectively held at WB) · **Matched LP:** M0 · **Multi:** N
- **Establishes:** WER is 2.01 % clean, 3.08 % at 6 kb/s, 2.15 % at 9, 2.07 % at 12 and 2.03 % at 20 kb/s. "Opus coding has a significant impact on ASR performance at very low bitrates". LACE and NoLACE recover about half of the 6 kb/s loss.
- **Relation: THREATENS (generic)** "low-rate SILK coding distortion raises WER" as a new finding. **SUPPORTS** our residual interpretation. It is the wideband counterpart to our narrowband study.

### khare2020opus
**Khare, A., Sundaram, S., & Wu, M. (2020). Multi-channel acoustic modeling using mixed bitrate OPUS compression. arXiv:2002.00122. Preprint; no peer-reviewed venue found.**
- **Verified:** arXiv PDF · **Ev:** FT · **Categories:** 4
- **Recogniser:** Two-channel learned beamformer plus 5-layer LSTM hybrid (CE then sMBR); in-house far-field data.
- **Corpus:** In-house test set of 33,000 utterances.
- **Manipulation:** Opus CBR at 8, 16, 32 and 128 kbit/s per channel; mixed-bitrate training.
- **Separated:** S0 · **Matched LP:** M0 · **Multi:** N
- **Establishes:** Relative WER degradation of 202.1 % at 8 kbit/s, falling to 12.6 % at 16. Quote: "the performance with the 8kbps encoding degrades drastically since OPUS encodes the audio as narrowband at 8kbps."
- **Relation: SUPPORTS (motivation).** Prior Opus-ASR work attributed the 8 kbit/s loss to narrowband operation without a control. Our LP condition tests that attribution directly.

---

## 3. Category records

Each work appears once, under its primary category; cross-references are given as "→".
Compact records give every required field. Where a field is omitted, it is NA or U.

### Category 1: ASR robustness to narrowband / telephone-band speech

→ moreno1994sources, bauer2010wtimit, morales2007nodalida, moller2002analytic, fernandezgallardo2017predicting, basu2026factors (§2).

#### likhomanenko2021rethinking
**Likhomanenko, T., Xu, Q., Pratap, V., Tomasello, P., Kahn, J., Avidov, G., Collobert, R., & Synnaeve, G. (2021). Rethinking evaluation in ASR: Are our models robust enough? *Proc. Interspeech 2021*, pp. 311–315. doi:10.21437/Interspeech.2021-1758**
- **Ev:** FT (ISCA) · **Categories:** 1, 7
- **Recogniser:** 270M Transformer-CTC. **Corpus:** WSJ, TED-LIUM 3, Common Voice, LibriSpeech, SWB+Fisher, Robust Video.
- **Manipulation:** All training and evaluation at 8 kHz vs 16 kHz (matched training). **Sep** NA · **LP** M1 · **Multi** N.
- **Establishes:** Training and testing LibriSpeech at 8 kHz costs little: "absolute 0.3% and 0.2% worse on dev-other".
- **Relation: SUPPORTS.** With matched training, LibriSpeech carries little ASR-relevant information above 4 kHz, which is consistent in size with our small Whisper bandwidth component.

#### hirsch2000aurora
**Hirsch, H.-G., & Pearce, D. (2000). The AURORA experimental framework for the performance evaluation of speech recognition systems under noisy conditions. *Proc. ASR2000 (ISCA ITRW)*, pp. 181–188. https://www.isca-archive.org/asr_2000/hirsch00_asr.html**
- **Ev:** FT · **Categories:** 1, 6
- **Recogniser:** HTK whole-word digit HMMs. **Corpus:** TIDigits at 8 kHz (Aurora 2).
- **Manipulation:** G.712 vs MIRS filter characteristics at fixed bandwidth, plus noise. **Sep** NA · **LP** NA · **Multi** N.
- **Establishes:** Filter *shape* at a fixed nominal band changes accuracy in noise (e.g., street noise 61.51 % G.712 vs 66.11 % MIRS).
- **Relation: SUPPORTS.** Passband shape matters, which justifies fitting our control to the codec's measured response rather than using a nominal mask.

#### tarcisio1999simulated
**Tarcisio, C., Daniele, F., Roberto, G., & Marco, O. (1999). Use of simulated data for robust telephone speech recognition. *Proc. Eurospeech 1999*, pp. 2825–2828. doi:10.21437/Eurospeech.1999-707** (names as in the ISCA/Crossref record, which appears to invert given names and surnames: likely Coianiz T., Falavigna D., Gretter R., Orlandi M.)
- **Ev:** FT · **Categories:** 1, 6
- **Recogniser:** IRST HMM (Italian). **Corpus:** APASCI, APASCI-SIM, telephone test sets.
- **Manipulation:** Wideband speech filtered with **measured** telephone impulse responses plus noise, to create training data. **Sep** S0 · **LP** partly (measured channel, but used for training data, not as a control) · **Multi** N.
- **Relation: NARROWS (method).** Filtering speech with a measured channel response predates us. Using it as a validated *control* in a codec decomposition does not.

#### Compact records (category 1; all CONTEXT unless noted)
- **chigier1992phonetic** — Chigier, B. (1992). Phonetic classification on wide-band and telephone quality speech. *Speech and Natural Language Workshop* (Harriman, NY), pp. 291–295. ACL H92-1058.
  - Ev FT. Gaussian phonetic classifier; TIMIT vs N-TIMIT (real network).
  - Sep S0 (combined effects) · LP M0 · Multi N.
  - The telephone network raises error "by a factor of 1.3". Canonical confounded comparison.
- **jankowski1990ntimit** — Jankowski, C., Kalyanswamy, A., Basson, S., & Spitz, J. (1990). NTIMIT: A phonetically balanced, continuous speech, telephone bandwidth speech database. *Proc. ICASSP-90*, pp. 109–112. doi:10.1109/ICASSP.1990.115550.
  - Ev AB. Corpus paper; no ASR results in the abstract.
- **brown1995ctimit** — Brown, K. L., & George, E. B. (1995). CTIMIT: A speech corpus for the cellular environment with applications to automatic speech recognition. *Proc. ICASSP 1995*, vol. 1, pp. 105–108. doi:10.1109/ICASSP.1995.479284.
  - Ev AB. TIMIT-trained HMM phoneme accuracy dropped 58 % on CTIMIT.
  - Cellular codec and channel not separated. Sep S0.
- **morales2008stctimit** — Morales, N., Tejedor, J., Garrido, J., Colás, J., & Toledano, D. T. (2008). STC-TIMIT: Generation of a single-channel telephone corpus. *Proc. LREC 2008*, pp. 391–395. ACL L08-1497.
  - Ev FT. HMM phone recogniser; matched accuracy TIMIT 71.18, STC-TIMIT 61.80, NTIMIT 53.76 %.
  - The loss is attributed "mostly" to band limitation without a control. Sep S0.
- **morales2009featcomp** — Morales, N., Toledano, D. T., Hansen, J. H. L., & Garrido, J. (2009). Feature compensation techniques for ASR on band-limited speech. *IEEE TASLP* 17(4):758–774. doi:10.1109/TASL.2008.2012321.
  - Ev AB. Real telephone channels plus artificial low/band-pass filters on TIMIT.
- **seltzer2007mixed** — Seltzer, M. L., & Acero, A. (2007). Training wideband acoustic models using mixed-bandwidth training data for speech recognition. *IEEE TASLP* 15(1):235–245. doi:10.1109/TASL.2006.876774.
  - Ev FT. HTK GMM-HMM; WSJ0 passed through a G.712-spec filter. No codec.
- **seltzer2005fbe** — Seltzer, M. L., & Acero, A. (2005). Training wideband acoustic models using mixed-bandwidth training data via feature bandwidth extension. *Proc. ICASSP 2005*, vol. 1, pp. I-921–924. doi:10.1109/ICASSP.2005.1415265.
  - Ev MD.
- **li2012mixedbw** — Li, J., Yu, D., Huang, J.-T., & Gong, Y. (2012). Improving wideband speech recognition using mixed-bandwidth training data in CD-DNN-HMM. *Proc. IEEE SLT 2012*, pp. 131–136. doi:10.1109/SLT.2012.6424210.
  - Ev FT. Voice search; matched wideband 27.47 % vs downsampled 28.98 %. No codec.
- **yu2013featurelearning** — Yu, D., Seltzer, M. L., Li, J., Huang, J.-T., & Seide, F. (2013). Feature learning in deep neural networks – studies on speech recognition tasks. ICLR 2013 (arXiv:1301.3605).
  - Ev FT. A wideband-only DNN gives 27.5 % on WB and 53.5 % on NB test data: "DNNs cannot extrapolate to test samples that are substantially different".
- **mantena2019bwemb** — Mantena, G., Kalinli, O., Abdel-Hamid, O., & McAllaster, D. (2019). Bandwidth embeddings for mixed-bandwidth speech recognition. *Proc. Interspeech 2019*, pp. 3203–3207. doi:10.21437/Interspeech.2019-2589.
  - Ev FT. CNN-DNN hybrid; sox resampling; no codec.
- **mac2019largescale** — Mac, K.-N. C., Cui, X., Zhang, W., & Picheny, M. (2019). Large-scale mixed-bandwidth deep neural network acoustic modeling for automatic speech recognition. *Proc. Interspeech 2019*, pp. 251–255. doi:10.21437/Interspeech.2019-2641.
  - Ev FT. Hybrid CNNs; downsampled training costs +2.9 points on average. Real narrowband data confound bandwidth with channel/codec.
- **sukhadia2023channelaware** — Sukhadia, V. N., & Umesh, S. (2023). Channel-aware pretraining of joint encoder-decoder self-supervised model for telephonic-speech ASR. *Proc. ICASSP 2023 Workshops*, pp. 1–5. doi:10.1109/ICASSPW59220.2023.10193218 (arXiv:2211.01669).
  - The arXiv version adds A. Arunkumar as an author. Ev FT.
  - HuBERT-style SSL; LibriSpeech downsampled to 8 kHz for fine-tuning and test: 8.2/22.3 → 8.9/24.3 (pooled baseline). No codec.
  - **SUPPORTS** (bandwidth-only magnitude in the SSL era).
- **parihar2003aurora4** — Parihar, N., & Picone, J. (2003). Analysis of the Aurora large vocabulary evaluations. *Proc. Eurospeech 2003*, pp. 337–340. doi:10.21437/Eurospeech.2003-139.
  - Ev FT. Aurora-4 at 8 kHz (G.712) vs 16 kHz (P.341); the bandwidth effect can vanish in noise.
- **Other mixed-bandwidth and wideband-benefit papers** (Ev AB; all CONTEXT):
  - macho2003wideband — Macho, D. A., & Cheng, Y. M. (2003). On the use of wideband signal for noise robust ASR. *ICASSP 2003*, II-109–112. doi:10.1109/ICASSP.2003.1202306.
  - nadeu2001speechdatcar — Nadeu, C., & Tolos, M. (2001). Recognition experiments with the SpeechDat-Car Aurora Spanish database using 8 kHz- and 16 kHz-sampled signals. *ASRU 2001*, pp. 135–138. doi:10.1109/ASRU.2001.1034606.
  - karafiat2007cmllr — Karafiát, M., Burget, L., Černocký, J., & Hain, T. (2007). Application of CMLLR in narrow band wide band adapted systems. *Interspeech 2007*, pp. 282–285. doi:10.21437/Interspeech.2007-122.
  - you2014dnnadapt — You, Z., & Xu, B. (2014). Improving wideband acoustic models using mixed-bandwidth training data via DNN adaptation. *Interspeech 2014*, pp. 2204–2208. doi:10.21437/Interspeech.2014-493.
  - fukuda2019kd — Fukuda, T., & Thomas, S. (2019). Mixed bandwidth acoustic modeling leveraging knowledge distillation. *ASRU 2019*, pp. 509–515. doi:10.1109/ASRU46091.2019.9003760.
  - liao2003bmc — Liao, Y.-F., Lin, J.-S., & Tsai, W.-H. (2003). Bandwidth mismatch compensation for robust speech recognition. *Eurospeech 2003*, pp. 3093–3096. doi:10.21437/Eurospeech.2003-548.
  - hirsch2001multiple — Hirsch, H.-G., Hellwig, K., & Dobler, S. (2001). Speech recognition at multiple sampling rates. *Eurospeech 2001*, pp. 1837–1840 (ISCA hirsch01_eurospeech; Ev MD).
- **godambe2026responsible** — Godambe, T., Choudhary, N., Shah, S., Adiga, N., & Adavanne, S. (2026). Responsible ASR: Overcoming challenges of foundational models in narrow-band and low-resource settings. arXiv:2606.18659 (preprint).
  - Ev FT. Zero-shot Whisper-large-v3 on real 8 kHz call-centre audio: 28.7 % WER (English), 49.2 % (Hindi).
  - The authors attribute this "mainly" to wideband read-speech training, without a control. Sep S0 · Multi Y.
  - **SUPPORTS (motivation).**
- **khalid2025bridging** — Khalid, A., Adeeba, F., Sehar, N. U., & Hussain, S. (2025). Bridging the bandwidth gap: A mixed band telephonic Urdu ASR approach with domain adaptation for banking applications. *Proc. CHiPSAL 2025*, pp. 172–184. ACL 2025.chipsal-1.17.
  - Ev FT. Zero-shot Whisper-large 50 % WER vs mixed-band TDNN 27.56 % on Urdu telephony. Sep S0.

### Category 2: Bandwidth extension / restoration evaluated with ASR

→ basu2026factors (§2: neural BWE worsened WER).

#### bauer2014eusipco
**Bauer, P., Abel, J., Fischer, V., & Fingscheidt, T. (2014). Automatic recognition of wideband telephone speech with limited amount of matched training data. *Proc. EUSIPCO 2014*, Lisbon, pp. 1232–1236 (per OpenAlex). Zenodo doi:10.5281/zenodo.43771** (author order as given by the Zenodo PDF read in full; the Zenodo metadata lists Abel first)
- **Ev:** FT · **Categories:** 1, 2, 4
- **Recogniser:** RWTH GMM-HMM (triphones, trigram LM). **Corpus:** German Verbmobil (about 70 h).
- **Manipulation:** NB = telephone band-pass + decimation + **AMR-NB 12.2**; WB = P.341 + **AMR-WB 12.65**; statistical ABE applied to AMR-NB-coded training data.
- **Separated:** S1, lumped. A "cheat" ABE restoring the true upper band still exceeds the WB WER by 3.3 % relative, attributed to lower-band degradation "by means of a telephone bandpass filter and an AMR-NB speech codec". Filter and codec are not separated.
- **LP:** M0 (no uncoded band-limited condition) · **Multi:** N
- **Relation: NARROWS.** The only BWE-for-ASR study found whose narrowband input is codec-coded. It notes a lower-band residual but does not isolate the codec.

#### li2019ssrasr
**Li, X., Chebiyyam, V., & Kirchhoff, K. (2019). Speech audio super-resolution for speech recognition. *Proc. Interspeech 2019*, pp. 3416–3420. doi:10.21437/Interspeech.2019-3043**
- **Ev:** FT · **Categories:** 2
- **Recogniser:** Hybrid LSTM/HMM with 4-gram LM (LibriSpeech); BiLSTM (Speech Commands).
- **Corpus:** LibriSpeech test-clean downsampled to 8 kHz.
- **Manipulation:** Downsampling; BWE by interpolation, DNN, GAN and cGAN with ASR losses. No codec. **Sep** NA · **LP** M1 · **Multi** N.
- **Establishes:** Test-clean WER is 10.81 % at 16 kHz vs 12.66 % for interpolated 8 kHz; the cGAN gives 12.17 %.
- **Relation: SUPPORTS.** A prior bandwidth-only magnitude on the same test set, for a wideband-trained hybrid system.

#### Compact records (category 2; all CONTEXT; none involves Opus)
- **gao2019mixedbw** — Gao, J., Du, J., & Chen, E. (2019). Mixed-bandwidth cross-channel speech recognition via joint optimization of DNN-based bandwidth expansion and acoustic modeling. *IEEE TASLP* 27(3):559–571. doi:10.1109/TASLP.2018.2886739.
  - Ev FT. Mandarin DNN-HMM; 6 kHz VOX-compressed call-centre data confounded with channel. Sep S0.
- **gao2016ijcnn** — Gao, J., Du, J., Kong, C., Lu, H., Chen, E., & Lee, C.-H. (2016). An experimental study on joint modeling of mixed-bandwidth data via deep neural networks for robust speech recognition. *IJCNN 2016*, pp. 588–594. doi:10.1109/IJCNN.2016.7727253.
  - Ev FT. Real telephony narrowband; no codec named.
- **li2015dnnbwe** — Li, K., Huang, Z., Xu, Y., & Lee, C.-H. (2015). DNN-based speech bandwidth expansion and its application to adding high-frequency missing features for automatic speech recognition of narrowband speech. *Interspeech 2015*, pp. 2578–2582. doi:10.21437/Interspeech.2015-555.
  - Ev FT. WSJ0: matched WB 8.12 %, NB 8.67 %, BWE 8.26 %. No codec.
- **bachhav2020cvae** — Bachhav, P., Todisco, M., & Evans, N. (2020). Artificial bandwidth extension using conditional variational auto-encoders and adversarial learning. *ICASSP 2020*, pp. 6924–6928. doi:10.1109/ICASSP40776.2020.9053737.
  - Ev FT. Kaldi GMM-HMMs (4 variants); TIMIT tri3: 21.3 (WB), 27.2 (up-NB), 24.1 % (CVAE-GAN). No codec.
- **haws2019cyclegan** — Haws, D., & Cui, X. (2019). CycleGAN bandwidth extension acoustic modeling for automatic speech recognition. *ICASSP 2019*, pp. 6780–6784. doi:10.1109/ICASSP.2019.8682760.
  - Ev AB.
- **hao2020mfnet** — Hao, X., Xu, C., Hou, N., Xie, L., Chng, E. S., & Li, H. (2020). Time-domain neural network approach for speech bandwidth extension. *ICASSP 2020*. doi:10.1109/ICASSP40776.2020.9054551.
  - Ev AB (reports WER; recogniser unknown).
- **shi2023ccris** — Shi, L. (2023). A unified mixed-bandwidth ASR framework with generative adversarial network. *Proc. CCRIS 2023* (ACM), pp. 160–165. doi:10.1145/3622896.3622923.
  - Ev AB.
- **yuan2025cogsr** — Yuan, J., Wang, X., Xiao, Y., Wu, Y., Hu, C., & Lv, X. (2025). CogSR: Semantic-aware speech super-resolution via chain-of-thought guided flow matching. arXiv:2512.16304 (preprint).
  - Ev FT. Whisper-large-v3 used as the BWE evaluator on downsampled VCTK; no codec.
- **liu2024lowfrequency** — Liu, A., Vunderink, P., Vargas Quiros, J., Raman, C., & Hung, H. (2024). How private is low-frequency speech audio in the wild? *Interspeech 2024*, pp. 2725–2729. doi:10.21437/Interspeech.2024-1258.
  - Ev FT. Whisper at 0.3–20 kHz sampling rates plus BWE; extreme bandwidths; no codec.
- **chae2026pebe** — Chae et al. (2026). Parallel enhancement and bandwidth extension of coded speech. *Applied Sciences* 16(3):1439. doi:10.3390/app16031439.
  - Ev AB (Crossref). **Opus-coded** NB/WB input; lower-band coding artefacts treated separately from BWE; MUSHRA only, no ASR.
- **Null result:** no BWE-for-ASR study with Opus-coded input was found.

### Category 3: Opus/SILK design, bitrate–bandwidth operating regions, speech-coding behaviour

For these records the recogniser, corpus, Multi and LP fields are NA (design documents) unless stated.

#### rfc6716
**Valin, J.-M., Vos, K., & Terriberry, T. B. (2012). Definition of the Opus audio codec. RFC 6716, IETF. doi:10.17487/RFC6716** (cite as updated by RFC 8251)
- **Ev:** FT (https://www.rfc-editor.org/rfc/rfc6716.txt; errata checked: none on §2.1.1 or §4.2.9) · **Categories:** 3
- **Facts:**
  - Table 1 (§2): NB 4 kHz / 8 kHz … FB 20/48.
  - §3.1: three modes (SILK-only NB/MB/WB; Hybrid SWB/FB; CELT-only).
  - §2: "the LP layer always operates at a sample rate of twice the audio bandwidth, up to a maximum of 16 kHz".
  - §2.1.1: bitrate "sweet spots": "8-12 kbit/s for NB speech, 16-20 kbit/s for WB speech".
  - §4.2.9: "The resampler itself is non-normative, and a decoder can use any method it wants to perform the resampling". The resampler *delay* is normative (Table 54).
  - §6: conformance is judged per output sampling rate.
- **Relation: SUPPORTS** (Methods facts). **NARROWS** our wording: resampling is implementation-defined within conformance limits, not arbitrary.

#### libopus-1.4
**Xiph.Org Foundation (2023). libopus 1.4 source code, tag v1.4 (commit 82ac57d9f1aaf575800cf17373348e45b7ce6c0d): src/opus_encoder.c; silk/control_SNR.c; silk/resampler.c. https://github.com/xiph/opus/tree/v1.4**
- **Ev:** FT (source read; thresholds re-checked) · **Categories:** 3
- **Facts:**
  - `mono_voice_bandwidth_thresholds` and `mono_music_bandwidth_thresholds` both set NB↔MB = 9000 ±700 and MB↔WB = 9000 ±700 (L123–137); mediumband is skipped.
  - Automatic selection (L1462–1506); `OPUS_SET_BANDWIDTH` overrides it (L1508–1512); an input Fs ≤ 16 kHz caps the band at WB (L1520–1529).
  - SILK gets about 7.6 kbit/s of payload at 8 kbit/s with 20 ms frames.
  - SILK residual SNR targets are tabulated against rate (about 14 dB NB at 7.6 kbit/s; about 38 dB at 40 kbit/s).
  - Version history: the thresholds were 11000/14000 (plus ×1.1 rate scaling) in v1.0.3–1.1.x, 10000/11000 in v1.2.x, and 9000/9000 in v1.3–1.6.1.
  - **8 kbit/s → NB in every version checked; 12 kbit/s → WB only from v1.2.**
- **Relation: SUPPORTS** (the automatic narrowband selection at 8 kbit/s; the forced-NB SILK condition). **NARROWS:** the paper must name the library version.

#### ffmpeg-6.1.1-opusdec
**FFmpeg developers (2023). FFmpeg n6.1.1 source (commit e38092ef9395d7049f871ef4d5411eb410e283e0): libavcodec/opusdec.c, opus_silk.c; libswresample/resample.c, options.c; libavcodec/allcodecs.c. https://github.com/FFmpeg/FFmpeg/tree/n6.1.1**
- **Ev:** FT (source; `filter_size 16` and 48 kHz output re-checked) · **Categories:** 3
- **Facts:**
  - The native Opus decoder (FFmpeg's default) always outputs 48 kHz (L685).
  - SILK output is upsampled with libswresample, `filter_size = 16` (L732), Kaiser window β = 9, with the upsampling cutoff at the SILK Nyquist. The swr cutoff is the "6dB point".
  - FFmpeg's own tests accept non-zero deviation from the RFC 8251 reference outputs for SILK vectors.
- **Relation: NARROWS** the interpretation of OPUS − LP. [Inference, not measured] The 4–5 kHz image we observed is plausibly produced by this short interpolator. That image is an implementation-specific, time-varying component, so the residual is defined for "libopus 1.4 encoder + FFmpeg 6.1.1 native decoder". SILK-40k shares this path.

#### vos2013voice
**Vos, K., Sørensen, K. V., Jensen, S. S., & Valin, J.-M. (2013). Voice coding with Opus. *135th AES Convention*, New York (convention paper; paper number not verified; AES E-Library blocked).**
- **Verified:** Author preprint (https://jmvalin.ca/papers/aes135_opus_silk.pdf) · **Ev:** FT · **Categories:** 3
- **Facts:** Recommended mono ranges are NB 8–12, MB 12–16, WB 16–20, SWB 20–28 and FB 28–40 kbps. Noise-shaping analysis "makes the decoded signal more harmonic, and thus easier to encode, at low bitrates".
- **Relation: SUPPORTS** (design rationale for a codec-specific, non-bandwidth modification at low rate). Caveat: libopus removed the SILK prefilter in 2016, so cite as design rationale, not as exact libopus 1.4 behaviour.

#### skoglund2020opus
**Skoglund, J., & Valin, J.-M. (2020). Improving Opus low bit rate quality with neural speech synthesis. *Proc. Interspeech 2020*, pp. 2847–2851. doi:10.21437/Interspeech.2020-2939 (arXiv:1905.04628)**
- **Ev:** FT · **Categories:** 3, 5
- **Test:** MUSHRA listening test, no ASR. **Corpus:** NTT database.
- **Manipulation:** Opus WB SILK at 6 and 9 kb/s. **Sep** S1 (WB fixed; the low-pass anchor was omitted) · **LP** M0.
- **Establishes:**
  - "as the rate drops below 10 kb/s, quality degrades quickly".
  - LSF bits hardly vary with rate, so residual bits collapse below 8 kb/s.
  - 9 kb/s is "the lowest bit rate for which the encoder defaults to wideband".
- **Relation: SUPPORTS** (why 8 kbit/s is NB, and why a large in-band coding distortion is expected there).

#### Compact records (category 3)
- **rfc8251** — Valin, J.-M., & Vos, K. (2017). Updates to the Opus audio codec. RFC 8251. doi:10.17487/RFC8251.
  - Ev FT. Decoder-code fixes including the reference SILK resampler; new test vectors. CONTEXT.
- **rfc7845** — Terriberry, T., Lee, R., & Giles, R. (2016). Ogg encapsulation for the Opus audio codec. RFC 7845. doi:10.17487/RFC7845.
  - Ev FT. Pre-skip, 48 kHz granule positions, end trimming (§4.2–4.4, §5.1). SUPPORTS (alignment method).
- **rfc7587** — Spittka, J., Vos, K., & Valin, J.-M. (2015). RTP payload format for the Opus speech and audio codec. RFC 7587. doi:10.17487/RFC7587.
  - Ev FT. §3.1.1 repeats the recommended rates. SUPPORTS.
- **rfc7874** — Valin, J.-M., & Bran, C. (2016). WebRTC audio codec and processing requirements. RFC 7874. doi:10.17487/RFC7874.
  - Ev FT. Opus and G.711 are mandatory for WebRTC. CONTEXT (deployment motivation).
- **valin2013music** — Valin, J.-M., Maxwell, G., Terriberry, T. B., & Vos, K. (2013). High-quality, low-delay music coding in the Opus codec. *135th AES Convention* (arXiv:1602.04845).
  - Ev FT. "CELT always operates at a sampling rate of 48 kHz, while SILK can operate at 8 kHz, 12 kHz, or 16 kHz." SUPPORTS.
- **valin2010celt** — Valin, J.-M., Terriberry, T. B., Montgomery, C., & Maxwell, G. (2010). A high-quality speech and audio codec with less than 10-ms delay. *IEEE TASLP* 18(1):58–67. doi:10.1109/TASL.2009.2023186.
  - Ev AB. CONTEXT (NEG_CODEC is CELT).
- **buethe2023lace** — Büthe, J., Valin, J.-M., & Mustafa, A. (2023). LACE: A light-weight, causal model for enhancing coded speech through adaptive convolutions. *IEEE WASPAA 2023*, pp. 1–5. doi:10.1109/WASPAA58266.2023.10248150.
  - Ev FT. WB-only SILK enhancement at 6–12 kb/s; P.808/PESQ, no ASR. SUPPORTS (low-rate SILK distortion is recognised).
- **osce-draft-04** — Buethe, J. (Ed.), & Valin, J.-M. (2026). Integration of speech codec enhancement algorithms into the Opus codec. draft-ietf-mlcodec-opus-speech-coding-enhancement-04 (work in progress, 2026-07-21).
  - Ev FT. "narrowband and mediumband content MUST NOT be extended". Conforming decoders may differ slightly.
  - CONTEXT: Opus ≥ 1.5 enhancement does not touch our NB condition. libopus 1.5.2/1.6.1 source confirms OSCE is opt-in and WB-only (dnn/osce.c).
- **ramo2011opus** — Rämö, A., & Toukomaa, H. (2011). Voice quality characterization of IETF Opus codec. *Interspeech 2011*, pp. 2541–2544. doi:10.21437/Interspeech.2011-650.
  - Ev FT. ACR tests with band-limited uncoded "direct" references; early Opus NB 5–9 kbit/s.
  - CONTEXT (a perceptual analogue of a bandwidth-matched reference; version drift).
- **codec-results-03** — Hoene, C. (Ed.), Valin, J.-M., Vos, K., & Skoglund, J. (2013). Summary of Opus listening test results. draft-ietf-codec-results-03 (expired).
  - Ev FT. "Opus at 11 kb/s was tied with the 3.5 low-pass of the original." CONTEXT (perceptual analogue of our LP control).
- **draft-vos-silk-02** — Vos, K., Jensen, S. S., & Sørensen, K. V. (2010). SILK speech codec. draft-vos-silk-02 (expired, individual).
  - Ev FT. Rationale for lowering the sampling rate at low bitrates ("Good quality is achieved at around 1 bit/sample").
  - Opus-SILK is not compatible with stand-alone SILK (RFC 6716 §2). SUPPORTS (rationale only).
- **valin2023dred** — Valin, J.-M., Büthe, J., & Mustafa, A. (2023). Low-bitrate redundancy coding of speech using a rate-distortion-optimized variational autoencoder. *ICASSP 2023*. doi:10.1109/ICASSP49357.2023.10096528.
  - Ev AB. Packet-loss redundancy. CONTEXT (low relevance).
- **spanias1994** — Spanias, A. S. (1994). Speech coding: A tutorial review. *Proc. IEEE* 82(10):1541–1582. doi:10.1109/5.326413.
  - Ev AB. CONTEXT.
- **Standards, metadata only** (titles/dates safe to cite; content not read):
  - ITU-T G.711 (1988), G.712 (2001), G.722 (2012), G.729 (2012), G.722.2 (2003).
  - 3GPP TS 26.090 (AMR), TS 26.190 (AMR-WB), TS 26.445 (EVS).

### Category 4: ASR robustness to Opus and other lossy codecs

→ besacier2001effect, bauer2010wtimit, borsky2015mp3, heymans2022multistyle, moller2002analytic, fernandezgallardo2017predicting, basu2026factors, buethe2024nolace, khare2020opus (§2).

#### 4a. Classic narrowband coders: codec vs bandwidth-matched uncoded speech (S1, bandwidth held fixed)

##### lilly1996effect
**Lilly, B. T., & Paliwal, K. K. (1996). Effect of speech coders on speech recognition performance. *Proc. ICSLP 1996*, pp. 2344–2347. doi:10.21437/ICSLP.1996-593**
- **Ev:** FT · **Categories:** 4
- **Recogniser:** HTK HMM (whole-word ISOLET; phoneme TIMIT); LPCEP/MFCC features. **Corpus:** ISOLET, TIMIT.
- **Manipulation:** ADPCM G.723 (40/24), G.721 (32), LD-CELP G.728 (16), GSM (13), CELP-1016 (4.8); tandeming.
  - Quote: "every utterance … is decimated to 8 kHz using a low pass filter with a half power cutoff of 3.5 kHz … The 128 kbits/s uncoded PCM data is used as a reference".
- **Sep** S1 · **LP** M1 · **Multi:** two HMM task systems from one toolkit.
- **Establishes:** Accuracy declines with bitrate; GSM and CELP-1016 hurt; ADPCM barely matters; tandeming compounds low-rate losses.
- **Relation: NARROWS (implicit).** The codec effect beyond a bandwidth-matched uncoded reference is standard in this era; the step from wideband to narrowband was not measured.

##### hirsch2002influence
**Hirsch, H.-G. (2002). The influence of speech coding on recognition performance in telecommunication networks. *Proc. ICSLP 2002*, pp. 1877–1880. doi:10.21437/ICSLP.2002-539**
- **Ev:** FT · **Categories:** 4
- **Recogniser:** HTK digits with the ETSI basic (ES 201 108) and advanced (ES 202 050) front-ends. **Corpus:** Aurora-2 (8 kHz).
- **Manipulation:** G.711, GSM FR/HR/EFR, AMR 4.75–12.2 (8 modes); PCM reference at 8 kHz. Quote: "Only the 8 kHz mode is applied … because of the limitation to 4 kHz bandwidth due to the coding schemes."
- **Sep** S1 · **LP** M1 · **Multi:** two front-ends, one back-end.
- **Establishes:** Every codec lowers accuracy (worst GSM-HR, about −7 points); accuracy correlates with MOS across AMR modes.
- **Relation: NARROWS (implicit).**

##### moller2002diagnostic
**Möller, S., & Kavallieratou, E. (2002). Diagnostic assessment of telephone transmission impact on ASR performance and human-to-human speech quality. *Proc. LREC 2002*, Las Palmas, pp. 1177–1184. doi:10.63317/58nn3dbk8kjf**
- **Ev:** FT (http://www.lrec-conf.org/proceedings/lrec2002/pdf/41.pdf) · **Categories:** 4, 5
- **Recognisers:** Swiss-French hybrid HMM/ANN; German commercial keyword HMM; AURORA HTK digits.
- **Manipulation:** A 40-condition channel simulation (300–3400 Hz band fixed); G.711, G.726, G.728, G.729, IS-54 and tandems; MNRU; noise.
- **Sep** S1 · **LP** M1 · **Multi:** Y (3)
- **Establishes:** "Degradations originating from low bit-rate speech codecs are – with few exceptions – better 'tolerated' by the recognizers than by humans".
- **Relation: NARROWS (implicit;** multi-recogniser codec comparison at fixed bandwidth).

##### Compact records (4a)
- **euler1994influence** — Euler, S., & Zinke, J. (1994). The influence of speech coding algorithms on automatic speech recognition. *Proc. ICASSP 1994*, vol. 1, pp. I/621–I/624. doi:10.1109/ICASSP.1994.389217.
  - Ev AB. Coders from 64 to 4.8 kbit/s; isolated-word recogniser plus speaker verification; systems trained at 64 kbit/s (narrowband PCM).
  - 4.8 kbit/s "increases the error rate of the word recognizer by a factor of three". Sep S1 · LP M1 · Multi N (two tasks). NARROWS (implicit).
- **huerta1998gsm** — Huerta, J. M., & Stern, R. M. (1998). Speech recognition from GSM codec parameters. *Proc. ICSLP 1998*, paper 0626. doi:10.21437/ICSLP.1998-329.
  - Ev FT. RM1 low-passed to 3.5 kHz at 8 kHz; senonic HMM; GSM FR.
  - Distortion attributed to LAR (LPC) quantisation vs RPE-LTP residual coding: a **within-codec** decomposition at fixed bandwidth.
  - NARROWS (attribution of codec distortion to codec stages).
- **huerta2001distortion** — Huerta, J. M., & Stern, R. M. (2001). Distortion-class modeling for robust speech recognition under GSM RPE-LTP coding. *Speech Communication* 34(1–2):213–225. doi:10.1016/S0167-6393(00)00055-8.
  - Ev MD (the Tampere 1999 workshop version, read in full, states "distortion introduced in the residual signal affects recognition to a larger extent than the quantization that the LAR coefficients undergo").
  - PhD thesis: Huerta, J. M. (2000), *Speech Recognition in Mobile Environments*, CMU (FT); corpora "band-limited and downsampled" to match the codec input.
- **kelleher2002dsr** — Kelleher, H., Pearce, D., Ealey, D., & Mauuary, L. (2002). Speech recognition performance comparison between DSR and AMR transcoded speech. *Proc. ICSLP 2002*, pp. 1873–1876. doi:10.21437/ICSLP.2002-538.
  - Ev FT. Aurora 2/3 at 8 kHz; AMR 4.75/12.2 vs DSR advanced front-end: "When the speech is clean the distortion due to the codec is the main source of performance degradation." Sep S0 (all NB). CONTEXT.
- **3gpp2004tr26943** — 3GPP (2004). Recognition performance evaluations of codecs for Speech Enabled Services (SES). 3GPP TR 26.943 V6.0.0 (Release 6) = ETSI TR 126 943 V6.0.0 (2004-12); current V19.0.0 (2025-11).
  - Ev FT (ETSI). DSR X-AFE vs AMR 4.75/12.2 (8 kHz) and AMR-WB 12.65 (16 kHz); comparisons "made separately at 8 kHz and 16 kHz"; IBM and ScanSoft evaluations; recommends DSR.
  - Sep S0 · Multi Y (vendor systems). CONTEXT (standards body found codec losses large enough to justify DSR).
- **etsi-dsr** — ETSI ES 201 108 V1.1.3 (2003-09) and ES 202 050 V1.1.5 (2007-01), Distributed speech recognition front-end standards.
  - Ev FT (introductions). "The degradations are as a result of both the low bit rate speech coding and channel transmission errors." CONTEXT.
- **pelaezmoreno2001voip** — Peláez-Moreno, C., Gallardo-Antolín, A., & Díaz-de-María, F. (2001). Recognizing voice over IP: A robust front-end for speech recognition on the World Wide Web. *IEEE Trans. Multimedia* 3(2):209–218. doi:10.1109/6046.923820.
  - Ev FT. HTK; G.723.1 at 5.3 kb/s vs original 8 kHz speech: a significant drop. Sep S1 (implicit). NARROWS (implicit).
- **gallardoantolin2005gsm** — Gallardo-Antolín, A., Peláez-Moreno, C., & Díaz-de-María, F. (2005). Recognizing GSM digital speech. *IEEE TSAP* 13(6):1186–1205. doi:10.1109/TSA.2005.853210.
  - Ev AB. Bitstream features: "the recognition system is only affected by the quantization distortion of the spectral envelope". CONTEXT (within-codec attribution).
- **kimcox2001bitstream** — Kim, H. K., & Cox, R. V. (2001). A bitstream-based front-end for wireless speech recognition on IS-136 communications system. *IEEE TSAP* 9(5):558–568. doi:10.1109/89.928920.
  - Ev AB. CONTEXT.

#### 4b. Audio codecs (MP3 etc.) and codec augmentation

- **barras2001compressed** — Barras, C., Lamel, L., & Gauvain, J.-L. (2001). Automatic transcription of compressed broadcast audio. *Proc. ICASSP 2001*, vol. 1, pp. 265–268. doi:10.1109/ICASSP.2001.940818.
  - Ev AB (full text unobtainable). LIMSI French broadcast news; MP3, RealAudio, GSM; WER stays below 40 % at 6.5 kbit/s. Sep U. CONTEXT.
- **pollak2011mp3** — Pollák, P., & Behúnek, M. (2011). Accuracy of MP3 speech recognition under real-word conditions: Experimental study ("Real-Word" is the official title). *Proc. SIGMAP 2011*, pp. 5–10. doi:10.5220/0003512600050010.
  - Ev FT. HTK Czech digits; 95.22 % (WAV) → 21.02 % (MP3 at 8 kbps, MFCC). Sep S0. CONTEXT (predecessor of borsky2015mp3).
- **nouza2013noise** — Nouza, J., Červa, P., & Silovský, J. (2013). Adding controlled amount of noise to improve recognition of compressed and spectrally distorted speech. *ICASSP 2013*, pp. 8046–8050. doi:10.1109/ICASSP.2013.6639232.
  - Ev AB. MP3 degradation attributed to spectral gaps, not band limitation. SUPPORTS (a codec-specific non-bandwidth mechanism).
- **vu2019codec** — Vu, T.-L., Zeng, Z., Xu, H., & Chng, E.-S. (2019). Audio codec simulation based data augmentation for telephony speech recognition. *APSIPA ASC 2019*, pp. 198–203. doi:10.1109/APSIPAASC47483.2019.9023257.
  - Ev FT. Kaldi TDNN-F at 8 kHz; 27 codecs via FFmpeg, **including Opus/SILK at 4.5–32 kbps at 8 kHz**.
  - Codec effects measured on top of 8 kHz band limitation: 26.79 % clean vs 40.50 % codec-simulated dev.
  - Sep S1 (codecs pooled) · LP M1 · Multi N. NARROWS (implicit).
- **fernandezgallego2022contact** — Fernández-Gallego, M. P., & Toledano, D. T. (2022). A study of data augmentation for ASR robustness in low bit rate contact center recordings including packet losses. *Applied Sciences* 12(3):1580. doi:10.3390/app12031580.
  - Ev FT. Kaldi TDNN; MP3 at 8/16 kbit/s, GSM-FR, packet loss on telephone-band audio. Sep S1 (implicit). CONTEXT.
- **Abstract-only items** (all CONTEXT):
  - ng2004mp3 — Ng, P., & Sanches, I. (2004). The influence of audio compression on speech recognition systems. SPECOM 2004.
  - malek2018telephone — Málek, J., Žďánský, J., & Červa, P. (2018). Robust recognition of conversational telephone speech via multi-condition training and data augmentation. *TSD 2018*, LNCS, pp. 324–333. doi:10.1007/978-3-030-00794-2_35. It applies "speech compression and narrow-band spectrum" separately as augmentations; how they are separated is not in the abstract.
  - hailu2020codecaug — Hailu, N., Siegert, I., & Nürnberger, A. (2020). Improving automatic speech recognition utilizing audio-codecs for data augmentation. *IEEE MMSP 2020*. doi:10.1109/MMSP48831.2020.9287127.
  - ramana2012codecs — Ramana, A. V., Parayitam, L., & Pala, M. S. (2012). Investigation of automatic speech recognition performance and mean opinion scores for different standard speech and audio codecs. *IETE J. Research* 58(2):121–129. doi:10.4103/0377-2063.96179.
  - andronic2020mp3 — Andronic et al. (2020). MP3 compression to diminish adversarial noise in end-to-end speech recognition. arXiv:2007.12892 (SPECOM 2020). Ev FT.
  - putra2025mp3whisper — Putra, S. J., Wijaya, A., & Alam, R. G. G. (2025). Analysis of MP3 bitrate on the accuracy of academic audio transcription using Whisper large-v3. *Jurnal Sistem Cerdas* 8(2):160–168. doi:10.37396/jsc.v8i2.528. Five files only.

#### 4c. Opus and neural-era ASR (S0 unless stated: no bandwidth control anywhere)

##### drude2021opus
**Drude, L., Heymann, J., Schwarz, A., & Valin, J.-M. (2021). Multi-channel Opus compression for far-field automatic speech recognition with a fixed bitrate budget. *Proc. Interspeech 2021*, pp. 1669–1673. doi:10.21437/Interspeech.2021-1214**
- **Ev:** FT · **Categories:** 4
- **Recogniser:** RNN-T behind a neural-mask MVDR beamformer; 60k h of production training data. **Corpus:** 126 h of Echo-style far-field data.
- **Manipulation:** Opus at 16–128 kbit/s per channel, complexity 3/6/10, mode auto or forced SILK/CELT; a modified encoder with DFT across channels.
- **Sep** S0 (bandwidth neither controlled nor reported) · **LP** M0 · **Multi** N.
- **Establishes:** Single-channel ASR saturates at about 32 kbit/s; beamforming suffers below 128 kbit/s from spatial and phase distortion.
- **Relation: CONTEXT.** No narrowband regime. It shows mode forcing, not bandwidth forcing, in ASR work.

##### Compact records (4c)
- **narayanan2018domain** — Narayanan, A., Misra, A., Sim, K. C., Pundak, G., Tripathi, A., Elfeky, M., Haghani, P., Strohman, T., & Bacchiani, M. (2018). Toward domain-invariant speech recognition via large scale training. *IEEE SLT 2018*, pp. 441–447. doi:10.1109/SLT.2018.8639610.
  - Ev FT. LSTM; codec-simulated training (MP3/AAC).
  - Opus 24k: 10.8 → 10.2 % with codec training; MP3 23k: 13.6 → 10.6 %; no codec 10.5 → 10.0 %.
  - Its 8 kHz condition is a separate test set. Sep S0. CONTEXT.
- **jassim2020vocoders** — Jassim, W. A., Skoglund, J., Chinen, M., & Hines, A. (2020). Speech quality factors for traditional and neural-based low bit rate vocoders. *QoMEX 2020*, pp. 1–6. doi:10.1109/QoMEX48832.2020.9123109.
  - Ev FT. Google STT; Opus 6 kb/s (NB SILK) about 0.50 WER vs Opus 9 kb/s (WB SILK) about 0.26 (read from a figure).
  - Bandwidth and rate confounded. SUPPORTS / CONTEXT.
- **jacobellis2024mpq** — Jacobellis, D., Cummings, D., & Yadwadkar, N. J. (2024). Machine perceptual quality: Evaluating the impact of severe lossy compression on audio and image models. arXiv:2401.07957 (abridged in *DCC 2024*, p. 562, doi:10.1109/DCC58796.2024.00079).
  - Ev FT. Whisper word accuracy 0.849 (uncompressed) → 0.754 at Opus 6 kbps (Common Voice). CONTEXT.
- **bai2026semdac** — Bai, L., Lu, W., & Guo, L. (2026). Decoder-side semantic conditioning for low-bitrate neural speech compression. arXiv:2512.21653 (accepted to APSIPA ASC 2026).
  - Ev FT. Whisper medium.en on LibriSpeech: 4.25 % raw vs 5.31 % at Opus 6 kbps. CONTEXT (magnitude check).
- **wang2025stcts** — Wang, S., Li, H., & Zhu, D. (2025). STCTS: Generative semantic compression for ultra-low bitrate speech via explicit text-prosody-timbre decomposition. arXiv:2512.00451 (preprint).
  - Ev FT. FasterWhisper small; Opus 6 kbps about 3.2 % WER against original-audio transcripts. CONTEXT.
- **jones2022microphone** — Jones, D. T., Sharma, D., Kruchinin, S. Yu., & Naylor, P. A. (2022). Microphone array coding preserving spatial information for cloud-based multichannel speech recognition. *EUSIPCO 2022*, pp. 324–328. doi:10.23919/EUSIPCO55093.2022.9909679.
  - Ev FT. Multichannel SILK at 6 kbps per channel; ContextNet. CONTEXT.
- **prescott2026attack** — Prescott, J., Lertpetchpun, T., & Narayanan, S. (2026). Attack-dependent robustness of neural audio codecs for adversarial ASR. arXiv:2603.09034v2 (preprint).
  - Ev FT. Whisper-base and wav2vec2-base; Opus at a nominal 4.5 kbps as an adversarial-purification baseline; no clean-speech Opus penalty reported.
  - CONTEXT (the only prior work with both model families on low-rate Opus).
- **zaporowski2026medical** — Zaporowski, S., & Kurowski, A. (2026). Analysis of the efficiency of Polish medical terminology recognition by Whisper ASR system depending on the selected audio codecs. *ISD 2026*. doi:10.62036/ISD.2026.46.
  - Ev AB. Whisper large-v3; Opus caused no significant ΔWER at an unknown bitrate. CONTEXT.
- **tseng2025probing** — Tseng, W.-C., & Harwath, D. (2025). Probing the robustness properties of neural speech codecs. *Interspeech 2025*, pp. 5013–5017. doi:10.21437/Interspeech.2025-355.
  - Ev FT. Neural codecs; **frequency responses measured with sine sweeps** and related qualitatively to Whisper-large WER; no matched low-pass ASR control.
  - NARROWS (measuring a codec's linear response is not new; using it to build a validated control is).
- **Neural-codec benchmarks** (null for traditional codecs; all Ev FT; CONTEXT):
  - wu2024codecsuperb — Wu, H., et al. (2024). Codec-SUPERB: An in-depth analysis of sound codec models. *Findings of ACL 2024*, pp. 10330–10348. doi:10.18653/v1/2024.findings-acl.616.
  - Codec-SUPERB @ SLT 2024 (arXiv:2409.14085).
  - shi2024espnetcodec — Shi, J., et al. (2024). ESPnet-Codec. *IEEE SLT 2024*, pp. 562–569. doi:10.1109/SLT61566.2024.10832289.
  - DASB (arXiv:2406.14294); wang2025audiocodecbench (arXiv:2509.02349); CodecBench (arXiv:2508.20660).
  - None includes Opus, MP3, AAC, AMR, EVS, Speex or Lyra.
- **Transmission, packet loss and other** (all CONTEXT):
  - kumalija2022network — Kumalija, E. J., & Nakamoto, Y. (2022). Performance evaluation of automatic speech recognition systems on integrated noise-network distorted speech. *Frontiers in Signal Processing* 2:999457. doi:10.3389/frsip.2022.999457. Ev FT. G.722 plus jitter and loss; DeepSpeech.
  - mayorga2003packet — Mayorga, P., Besacier, L., Lamy, R., & Sérignat, J.-F. (2003). Audio packet loss over IP and speech recognition. *ASRU 2003*, pp. 607–612. doi:10.1109/ASRU.2003.1318509. Ev AB.
  - milner2000ip — Milner, B. P., & Semnani, S. (2000). Robust speech recognition over IP networks. *ICASSP 2000*, vol. 3, pp. 1791–1794. doi:10.1109/ICASSP.2000.862101. Ev AB.
  - neukirch2026intent — Neukirch, E., & Nussbaum, G. (2026). *Int. J. Communication and Information Technology* 7(3):51–56. doi:10.33545/2707661x.2026.v7.i3a.218. Ev AB; low-visibility venue.

### Category 5: Work that explicitly separates bandwidth limitation from codec distortion

→ In ASR: besacier2001effect, bauer2010wtimit, borsky2015mp3, heymans2022multistyle, moller2002analytic, fernandezgallardo2017predicting, basu2026factors, morales2007nodalida, moreno1994sources (channel) (§2). Bandwidth held fixed: buethe2024nolace, skoglund2020opus (WB SILK). Within-codec attribution: huerta1998gsm, gallardoantolin2005gsm.

#### Adjacent fields (not ASR): explicit separations
- **fernandezgallardo2014advantages** — Fernández Gallardo, L., Wagner, M., & Möller, S. (2014). Advantages of wideband over narrowband channels for speaker verification employing MFCCs and LFCCs. *Interspeech 2014*, pp. 1115–1119. doi:10.21437/Interspeech.2014-286.
  - Ev FT. i-vector speaker verification; clean 0–4, 4–8 and 0–8 kHz bands, plus channels (G.712 + G.711 or AMR-NB 12.2; P.341 + G.722 or AMR-WB 12.65).
  - Quote: "permit us the study of only the selected channel impairments, namely bandwidth limitation and codec".
  - Sep S2 · LP M1 · Multi N. NARROWS (the design idea exists in speaker verification).
- **jarina2017asv** — Jarina, R., Polacký, J., Počta, P., & Chmulík, M. (2017). Automatic speaker verification on narrowband and wideband lossy coded clean speech. *IET Biometrics* 6(4):276–281. doi:10.1049/iet-bmt.2016.0119.
  - Ev AB. GMM-UBM; NB and WB codecs incl. EVS; coded WB beats coded NB by 1–3 % EER "even at the lowest investigated bitrates". Sep U. CONTEXT.
- **lech2020ser** — Lech, M., Stolar, M. N., Best, C. J., & Bolia, R. S. (2020). Real-time speech emotion recognition using a pre-trained image classification network: Effects of bandwidth reduction and companding. *Frontiers in Computer Science* 2:14. doi:10.3389/fcomp.2020.00014.
  - Ev AB. 16 → 8 kHz costs −3.3 %; μ-law companding −3.8 %; combined about −7 %. Sep S2 (factorial). NARROWS (adjacent task).
- **fruhholz2016narrowband** — Frühholz, S., Marchi, E., & Schuller, B. (2016). The effect of narrow-band transmission on recognition of paralinguistic information from human vocalizations. *IEEE Access* 4:6059–6072. doi:10.1109/ACCESS.2016.2604038.
  - Ev AB. Narrow-band speech coders *and* static/formant-based low-pass cutoffs, tested separately; degradation only under severe low-pass. Sep S1. CONTEXT.
- **wang2022antispoof** — Wang, Y., Wang, X., Nishizaki, H., & Li, M. (2022). Low pass filtering and bandwidth extension for robust anti-spoofing countermeasure against codec variabilities. *ISCSLP 2022*, pp. 438–442. doi:10.1109/ISCSLP57327.2022.10038240.
  - Ev AB. Low-pass used as a *mitigation* against codec variability, not as a decomposition control. CONTEXT.
- **Metadata only** (content not read; do not cite for specific claims):
  - Ferro Filho, A., et al. (2025). Evaluating deep speaker embedding robustness to domain, sampling rate, and codec variations. *Interspeech 2025*, pp. 1113–1117. doi:10.21437/Interspeech.2025-2167.
  - Albahri, A., & Lech, M. (2016). Effects of band reduction and coding on speech emotion recognition. *ICSPCS 2016*. doi:10.1109/ICSPCS.2016.7843353.
  - Siegert, I., et al. (2016). Emotion intelligibility within codec-compressed and reduced bandwidth speech. ITG Speech Communication 2016.

#### Speech quality: bandwidth and coding impairments in one framework
- **moller2006impairment** — Möller, S., Raake, A., Kitawaki, N., Takahashi, A., & Wältermann, M. (2006). Impairment factor framework for wide-band speech codecs. *IEEE TASLP* 14(6):1969–1976. doi:10.1109/TASL.2006.883262.
  - Ev AB. Codec impairment factors derived to fit the E-model framework extended to wideband.
  - How narrowband bandwidth loss is represented was **not read**; do not cite it for a decomposition. CONTEXT.
- **moller2010instrumental** — Möller, S., Côté, N., Gautier-Turbin, V., Kitawaki, N., & Takahashi, A. (2010). Instrumental estimation of E-model parameters for wideband speech codecs. *EURASIP JASMP* 2010:782731. doi:10.1155/2010/782731.
  - Ev AB. NB → WB migration gives "roughly 30%" quality improvement. CONTEXT.
- **waltermann2010dimensions** — Wältermann, M., Raake, A., & Möller, S. (2010). Quality dimensions of narrowband and wideband speech transmission. *Acta Acustica united with Acustica* 96(6):1090–1103. doi:10.3813/AAA.918370.
  - Ev AB. Perceptual dimensions Discontinuity, Noisiness and Coloration, plus a wideband-specific dimension. CONTEXT (a perceptual counterpart of separating band-related from coding-related degradation).
- **moller2014dimensions** — Möller, S., Köster, F., Fernández Gallardo, L., & Wagner, M. (2014). Comparison of transmission quality dimensions of narrowband, wideband, and super-wideband speech channels. *ICSPCS 2014*, pp. 1–6. doi:10.1109/ICSPCS.2014.7021110.
  - Ev AB. Review that includes automatic speech/speaker recognition vs bandwidth. CONTEXT.

### Category 6: Controlled signal-domain interventions that explain ASR degradation

→ moreno1994sources, borsky2015mp3 (§2).

#### iwamoto2022artifacts
**Iwamoto, K., Ochiai, T., Delcroix, M., Ikeshita, R., Sato, H., Araki, S., & Katagiri, S. (2022). How bad are artifacts?: Analyzing the impact of speech enhancement errors on ASR. *Proc. Interspeech 2022*, pp. 5418–5422. doi:10.21437/Interspeech.2022-318**
- **Ev:** FT · **Categories:** 6
- **Recogniser:** Kaldi DNN-HMM (LF-MMI), multi-condition. **Corpus:** WSJ0 + CHiME-3 noise (simulated), CHiME-3 real.
- **Intervention:** The SE output is split by orthogonal projection into target, noise-error and artifact-error parts. "Direct scaling analysis" re-synthesises with each error term scaled, holding the target fixed, then decodes.
- **Sep** NA · **LP:** partial (an oracle per-utterance split, not a calibrated surrogate) · **Multi** N.
- **Establishes:** "the artifact errors have a larger impact on the degradation of ASR performance".
- **Relation: NARROWS (method).** "Split a processing penalty into a linear/natural part and a nonlinear residual by re-synthesis" is not new.
  - In this framework, linear filtering of the target is absorbed into the target and **not charged**. Our LP − REF term charges band limitation as its own ASR cost.
  - Speech enhancement, not codecs; one recogniser.

#### ochiai2024rethinking
**Ochiai, T., Iwamoto, K., Delcroix, M., Ikeshita, R., Sato, H., Araki, S., & Katagiri, S. (2024). Rethinking processing distortions: Disentangling the impact of speech enhancement errors on speech recognition performance. *IEEE TASLP* 32:3589–3602. doi:10.1109/TASLP.2024.3426924 (arXiv:2404.14860)**
- **Ev:** FT (arXiv) · **Categories:** 6
- **Recognisers:** Kaldi DNN-HMM back-ends (different training data; a CSJ system).
- **Intervention:** Target/interference/noise/artifact projection; scaling analysis; observation adding (OA).
- **Relation: NARROWS (method)**, as above. This is the fullest statement of the method.

#### sehr2010reverberation
**Sehr, A., Habets, E. A. P., Maas, R., & Kellermann, W. (2010). Towards a better understanding of the effect of reverberation on speech recognition performance. *Proc. IWAENC 2010* (pages U). https://iwaenc.org/proceedings/2010/HTML/Uploads/968.pdf**
- **Ev:** FT · **Categories:** 6
- **Recogniser:** HTK word HMMs. **Corpus:** TI digits with measured RIRs.
- **Intervention:** Keep the measured RIR up to delay T and attenuate the tail by A dB.
- **LP:** exact partial reproduction of a known LTI channel · **Multi** N.
- **Establishes:** Early reflections up to about 40–50 ms are benign; the tail matters.
- **Relation: NARROWS (method).** "Reproduce part of a channel, omit the rest, attribute the difference". There the channel is exactly known and LTI, so no surrogate needs to be fitted or validated.

#### Compact records (category 6; CONTEXT unless noted)
- **araki2023residual** — Araki, S., Yamamoto, A., Ochiai, T., Arai, K., Ogawa, A., Nakatani, T., & Irino, T. (2023). Impact of residual noise and artifacts in speech enhancement errors on intelligibility of human and machine. *Interspeech 2023*, pp. 2503–2507. doi:10.21437/Interspeech.2023-1116.
  - Ev FT. ESPnet plus human listeners; artifact scaling hurts both far more than noise scaling.
  - Caveat: artifact energy exceeded noise energy (relevant when comparing component sizes). SUPPORTS.
- **iwamoto2024e2e** — Iwamoto, K., et al. (2024). How does end-to-end speech recognition training impact speech enhancement artifacts? *ICASSP 2024*, pp. 11031–11035. doi:10.1109/ICASSP48485.2024.10447750.
  - Ev FT. WavLM front-end; SE degrades even SSL back-ends. CONTEXT.
- **maas2012reverb** — Maas, R., Habets, E. A. P., Sehr, A., & Kellermann, W. (2012). On the application of reverberation suppression to robust speech recognition. *ICASSP 2012*, pp. 297–300. doi:10.1109/ICASSP.2012.6287875.
  - Ev AB. CONTEXT.
- **vipperla2010ageing** — Vipperla, R., Renals, S., & Frankel, J. (2010). Ageing voices: The effect of changes in voice parameters on ASR performance. *EURASIP JASMP* 2010:525783. doi:10.1186/1687-4722-2010-525783 (Crossref also lists 10.1155/2010/525783).
  - Ev AB. Candidate components (jitter, shimmer, F0) were inserted to test whether they reproduce the WER gap; they largely did not.
  - SUPPORTS (the same sufficiency logic as our LP-alone condition).
- **vincent2017mismatch** — Vincent, E., Watanabe, S., Nugraha, A. A., Barker, J., & Marxer, R. (2017). An analysis of environment, microphone and data simulation mismatches in robust speech recognition. *Computer Speech & Language* 46:535–557. doi:10.1016/j.csl.2016.11.005.
  - Ev FT. Simulated "twins" of real utterances use different recordings, which confounds the gap. CONTEXT (a foil for our same-waveform design).
- **pohlhausen2025lowfreq** — Pohlhausen, J., & Bitzer, J. (2025). Revisiting the privacy of low-frequency speech signals. *SPSC 2025*, pp. 85–89. doi:10.21437/SPSC.2025-13.
  - Ev FT. LibriSpeech; anti-aliased vs non-anti-aliased resampling isolates aliasing. CONTEXT (folded/imaged components carry recognisable information).
- **alsteris2004phase** — Alsteris, L. D., & Paliwal, K. K. (2004). ASR on speech reconstructed from short-time Fourier phase spectra. *Interspeech 2004*, pp. 565–568. doi:10.21437/Interspeech.2004-219.
  - Ev FT.
- **lippmann1997missing** — Lippmann, R. P., & Carlson, B. A. (1997). Using missing feature theory to actively select features for robust speech recognition with interruptions, filtering and noise. *Eurospeech 1997*, pp. KN37–KN40. doi:10.21437/Eurospeech.1997-6.
  - Ev FT. Clean-trained HMMs: accuracy "drops well below 90% correct with a low pass cutoff below roughly 6 kHz" (filtering simulated in the filter-bank domain). CONTEXT.
- **lippmann1997review** — Lippmann, R. P. (1997). Speech recognition by machines and humans. *Speech Communication* 22(1):1–15. doi:10.1016/S0167-6393(97)00021-6.
  - Ev FT (review).
- **kanedera1997modulation** — Kanedera, N., Arai, T., Hermansky, H., & Pavel, M. (1997). On the importance of various modulation frequencies for speech recognition. *Eurospeech 1997*, pp. 1079–1082. doi:10.21437/Eurospeech.1997-104.
  - Ev FT.
- **trinh2021listening** — Trinh, V. A., & Mandel, M. I. (2021). Directly comparing the listening strategies of humans and machines. *IEEE TASLP* 29:312–323. doi:10.1109/TASLP.2020.3040545.
  - Ev AB. Bubble-noise importance maps.
- **mandel2016listening** — Mandel, M. I. (2016). Directly comparing the listening strategies of humans and machines. *Interspeech 2016*, pp. 660–664. doi:10.21437/Interspeech.2016-932.
  - Ev FT.
- **narayanan2013binarymask** — Narayanan, A., & Wang, D. (2013). The role of binary mask patterns in automatic speech recognition in background noise. *JASA* 133(5):3083–3093. doi:10.1121/1.4798661.
  - Ev AB.
- **adolfi2023successes** — Adolfi, F., Bowers, J. S., & Poeppel, D. (2023). Successes and critical failures of neural networks in capturing human-like speech recognition. *Neural Networks* 162:199–211. doi:10.1016/j.neunet.2023.02.032.
  - Ev FT. Four models incl. wav2vec 2.0; synthetic perturbation families.
- **huang2025audiochannels** — Huang, K.-T., Chen, L.-W., Lee, H.-S., Chen, B., & Wang, H.-M. (2025). Revealing the role of audio channels in ASR performance degradation. *IEEE ASRU 2025*, pp. 1–7. doi:10.1109/ASRU65441.2025.11434673.
  - Ev FT. Whisper-small on simultaneously recorded channels; linear vs nonlinear channel parts not separated.
- **spille2017dips** — Spille, C., & Meyer, B. T. (2017). Listening in the dips. *Interspeech 2017*, pp. 2968–2972. doi:10.21437/Interspeech.2017-1168.
  - Ev FT.
- **wu2023xasr** — Wu, X., Bell, P., & Rajan, A. (2023). Explanations for automatic speech recognition. *ICASSP 2023*. doi:10.1109/ICASSP49357.2023.10094635.
  - Ev AB.
- **vincent2006bsseval** — Vincent, E., Gribonval, R., & Févotte, C. (2006). Performance measurement in blind audio source separation. *IEEE TASLP* 14(4):1462–1469. doi:10.1109/TSA.2005.858005.
  - Ev AB. "Allowed distortions" (linear filters) are not counted as error. CONTEXT (conceptual contrast with our LP − REF).
- **Human-listener analogues** (CONTEXT):
  - loizou2011reasons — Loizou, P. C., & Kim, G. (2011). *IEEE TASLP* 19(1):47–56. doi:10.1109/TASL.2010.2045180. Ev FT.
  - kollmeier2016fade — Kollmeier, B., et al. (2016). *Trends in Hearing* 20. doi:10.1177/2331216516655795. Ev FT.
  - vanhuis2026bif — van Huis, N. D., Versfeld, N. J., & Smits, C. (2026). *Hearing Research* 481:109785. doi:10.1016/j.heares.2026.109785. Ev AB; Whisper used in a band-importance derivation.
- **Preprints** (not peer-reviewed):
  - huo2026polar — Huo, M., Zhang, Y., & Zhang, H. (2026). Where speech enhancement hurts recognition: An inference time polar projection diagnosis. arXiv:2607.11157.
    - Ev FT. **Whisper-large-v3 and wav2vec2-large**; component-isolating conditions (mask magnitude vs phase); paired bootstrap over utterances (B = 10⁴).
    - NARROWS (closest in evaluation practice). It is not a codec study and has no linear surrogate.
  - weerts2021psychometrics — Weerts, L., Rosen, S., Clopath, C., & Goodman, D. F. M. (2021/2022). The psychometrics of automatic speech recognition. bioRxiv doi:10.1101/2021.04.19.440438.
    - Ev FT. Band-pass filtering of wav2vec 2.0, Kaldi and DeepSpeech; wav2vec 2.0 was the most robust of the three.

### Category 7: Robustness of wav2vec2 and Whisper

→ shah2025srb, basu2026factors (§2); likhomanenko2021rethinking, sukhadia2023channelaware, godambe2026responsible, khalid2025bridging (cat. 1); liu2024lowfrequency, yuan2025cogsr (cat. 2); prescott2026attack, jacobellis2024mpq, bai2026semdac (cat. 4); huang2025audiochannels, huo2026polar, weerts2021psychometrics, adolfi2023successes (cat. 6).

- **radford2023whisper** — Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2023). Robust speech recognition via large-scale weak supervision. *ICML 2023*, PMLR 202:28492–28518. https://proceedings.mlr.press/v202/radford23a.html.
  - Ev FT. Effective robustness across 12 out-of-distribution sets (including CallHome and Switchboard) and white/pub noise; **no codec, bandwidth or sampling-rate tests**; all audio resampled to 16 kHz.
  - Switchboard WER: 28.3 (wav2vec2-large) vs 13.8 (Whisper large-v2). CONTEXT.
- **baevski2020wav2vec** — Baevski, A., Zhou, Y., Mohamed, A., & Auli, M. (2020). wav2vec 2.0: A framework for self-supervised learning of speech representations. *NeurIPS 33*, pp. 12449–12460.
  - Model reference (verified for the course report). CONTEXT.
- **hsu2021robust** — Hsu, W.-N., et al. (2021). Robust wav2vec 2.0: Analyzing domain shift in self-supervised pre-training. *Interspeech 2021*, pp. 721–725. doi:10.21437/Interspeech.2021-236.
  - Ev FT. "We re-sample all datasets to 16kHz"; telephone band folded into "domain". Sep S0. CONTEXT.
- **huang2022distortion** — Huang, K. P., Fu, Y.-K., Zhang, Y., & Lee, H.-y. (2022). Improving distortion robustness of self-supervised speech processing tasks with domain adaptation. *Interspeech 2022*, pp. 2193–2197. doi:10.21437/Interspeech.2022-519.
  - Ev FT. Noise and reverberation only; no band limiting, no codec. CONTEXT.
- **gong2023whisperat** — Gong, Y., Khurana, S., Karlinsky, L., & Glass, J. (2023). Whisper-AT: Noise-robust automatic speech recognizers are also strong general audio event taggers. *Interspeech 2023*, pp. 2798–2802. doi:10.21437/Interspeech.2023-2193.
  - Ev FT. Whisper's representations encode background type; noise only. CONTEXT.
- **zhang2024mmcbench** — Zhang, J., Pang, T., Du, C., Ren, Y., Li, B., & Lin, M. (2024). Benchmarking large multimodal models against common corruptions. arXiv:2401.11943 (preprint).
  - Ev FT. Low-pass, band-pass and **MP3** among 16 corruptions for about 40 speech-to-text models, including Whisper and wav2vec2. Results are aggregated and the metric is not WER. Sep S0. NARROWS (weakly).
- **chang2021exploration** — Chang, X., et al. (2021). An exploration of self-supervised pretrained representations for end-to-end speech recognition. *ASRU 2021*, pp. 228–235. doi:10.1109/ASRU51503.2021.9688137.
  - Ev FT. Switchboard upsampled to 16 kHz. CONTEXT.
- **vyas2021comparing** — Vyas, A., Madikeri, S., & Bourlard, H. (2021). Comparing CTC and LFMMI for out-of-domain adaptation of wav2vec 2.0 acoustic model. *Interspeech 2021*, pp. 2861–2865. doi:10.21437/Interspeech.2021-1683.
  - Ev FT. CONTEXT.
- **zuluagagomez2023atc** — Zuluaga-Gomez, J., et al. (2023). How does pre-trained wav2vec 2.0 perform on domain-shifted ASR? *IEEE SLT 2022* (published 2023), pp. 205–212. doi:10.1109/SLT54892.2023.10022724.
  - Ev FT. Air-traffic-control recordings upsampled to 16 kHz. CONTEXT.
- **gandhi2022esb** — Gandhi, S., von Platen, P., & Rush, A. M. (2022). ESB: A benchmark for multi-domain end-to-end speech recognition. arXiv:2210.13352 (preprint).
  - Ev FT. Includes SwitchBoard/CallHome as-is; no manipulation. CONTEXT.
- **gandhi2023distilwhisper** — Gandhi, S., von Platen, P., & Rush, A. M. (2023). Distil-Whisper: Robust knowledge distillation via large-scale pseudo labelling. arXiv:2311.00430 (preprint).
  - Ev FT. Noise only. CONTEXT.
- **atwany2025lost** — Atwany, H., Waheed, A., Singh, R., Choudhury, M., & Raj, B. (2025). Lost in transcription, found in distribution shift: Demystifying hallucination in speech foundation models. *Findings of ACL 2025*, pp. 23181–23203. doi:10.18653/v1/2025.findings-acl.1190.
  - Ev FT. More than 20 models; many perturbations but no band limiting and no codec. CONTEXT.

---

## 4. Search coverage and null results

**Sources queried.**
- Web search, about 250 queries across the six searches.
- Crossref and OpenAlex APIs.
- Semantic Scholar API (often rate-limited).
- ISCA Archive indexes, with systematic title scans of Interspeech 2021–2026 for bandwidth, narrowband, telephone, low-pass, sampling-rate and codec terms.
- ACL Anthology (LREC, NODALIDA, CHiPSAL, Findings).
- arXiv abstract pages and search UI (the export API was refused).
- RFC Editor and IETF Datatracker; ETSI deliver server; 3GPP DynaReport; ITU-T title pages.
- GitHub source at pinned tags (libopus v1.0.3–v1.6.1; FFmpeg n6.1.1).
- Author and institutional repositories: CMU, IDIAP, HAL, jmvalin.ca, UAM, UC3M, Zenodo, EURASIP proceedings, LREC proceedings.

**Explicit null results (as of 2026-09-26).**
1. No study decomposes a low-rate Opus/SILK ASR penalty into a bandwidth part and a residual.
2. No study uses a bandwidth control fitted to a codec's *measured* transfer function, or validates any bandwidth control on held-out speakers before ASR. The nearest are Borský 2015 (cutoff read from spectrograms) and Tseng & Harwath 2025 (neural-codec frequency responses, no control).
3. No study forces Opus SILK narrowband at a high rate as a same-mode reference. Drude 2021 forced mode, not bandwidth.
4. No 2022–2026 study evaluates wav2vec 2.0 on clean Opus at 12 kbit/s or below. The only one with both our model families on low-rate Opus is adversarial (Prescott 2026).
5. No BWE-for-ASR study with Opus-coded input was found.
6. No peer-reviewed study of Whisper or wav2vec2 WER as a function of low-pass cutoff with per-cutoff results was found. Speech Robust Bench reports aggregated scores.
7. The major neural-codec benchmarks contain no traditional-codec baselines.

**Access limits (the null results are conditional on these).**
- IEEE Xplore pages are not machine-readable, and ICASSP 2025/2026 were not systematically title-scanned. IEEE papers were checked through Crossref and OpenAlex metadata and abstracts only.
- ScienceDirect, ACM DL, MDPI, the AES E-Library and ITU-T recommendation texts returned 403 or bot challenges. Their content was read only when an author or repository copy existed.
- DBLP was blocked.

## 5. Unverified leads and grey literature (not used as evidence)

**Unverified leads:**
- Borský et al. 2017, *Speech Communication* 86:75–84 (MP3 dithering; may extend the bandwidth-vs-valley analysis).
- Cauchi et al. 2025, *Speech Communication* 173:103270 (reportedly Whisper with low-pass filtering at 1–6 kHz).
- Barras 2001 full text.
- Málek 2018 full text.
- Pollák & Borský 2012.
- Jones et al., WASPAA 2021 (Opus about 8 kbps per channel, about 26 % WER, second-hand).
- Triyason & Kanthamanon 2013.
- Chazan et al., EUSIPCO 2000.
- Teng & Kubichek 2006.
- Sroka & Braida 2005 (content).
- Lippmann & Carlson, ASRU 1997.
- Parihar et al., EUSIPCO 2004.
- Bauer, Jung & Fingscheidt, ITG 2010.
- Chigier "ICASSP 1991" attribution (conflicts with the verified 1992 workshop record).
- Nidadavolu et al. 2018.
- Hermansky et al., ICSLP 1996.
- AES convention paper numbers for the two Opus AES papers.
- The content of ITU-T G.107.1 / G.712.

**Grey literature, seen but not used:**
- Opus 1.5 release notes and demo page (consistent with the source code).
- Vendor and blog posts on Whisper input bitrates and telephony WER.
- A Hugging Face call-centre benchmark blog.
- An AI-generated Zenodo "podcast" note.
- A Gnani.ai web page on 2G audio.
