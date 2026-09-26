# Related-work notes (draft 1, 2026-09-26)

Draft prose for §2 (Related work), plus citation checklists for §1, §3 and §5. Keys refer
to `literature_matrix.md`, which holds the full citations and verification sources. Claim
limits and wording rules are in `novelty_boundary.md`. Nothing here claims priority.

Keys already in the verified course bibliography (`FINAL_REPORT_REFERENCES.bib`):
`besacier2001effect`, `narayanan2018domain`, `drude2021opus`, `radford2023whisper`,
`baevski2020wav2vec`, `hsu2021robust`, `huang2022distortion`, `iwamoto2022artifacts`,
`wu2024codecsuperb`, `shi2024espnetcodec`, `wang2025audiocodecbench`, `rfc6716`,
`panayotov2015librispeech`, `graves2006ctc`, `bisani2004bootstrap`, `efron1993bootstrap`,
`hirsch2000aurora`. All other keys need new BibTeX entries built from the matrix records.

---

## 1. Suggested structure of §2 (about 0.9 page)

1. Speech codecs and ASR (from narrowband coders to Opus)
2. Band limitation and narrowband ASR
3. Separating band limitation from coding distortion (the closest work)
4. Controlled signal interventions that attribute ASR degradation
5. Positioning paragraph

Opus/SILK design facts belong in §3 (Methods), not §2. See §3 of these notes.

## 2. Draft prose

### 2.1 Speech codecs and ASR

The effect of speech coding on recognition has been studied since low-rate coders entered
telephone networks. For HMM recognisers, errors grew as the coding rate fell, and tandem
coding compounded the losses [euler1994influence; lilly1996effect; hirsch2002influence].
Codec effects were recogniser-specific and poorly predicted by perceptual-quality models
[moller2002analytic; moller2002diagnostic]. Standards bodies judged them large enough to
specify distributed front-ends as an alternative to the voice codec [etsi-dsr;
3gpp2004tr26943; kelleher2002dsr]. Perceptual audio codecs such as MP3 were harmless at
high rates and increasingly harmful at low rates, with large losses at or below
16–24 kbit/s in these studies [besacier2001effect; pollak2011mp3; borsky2015mp3]. With neural recognisers, codec-simulated training reduces the penalty
[narayanan2018domain; vu2019codec].

Opus has been evaluated mainly in multichannel far-field front-ends [khare2020opus;
drude2021opus; jones2022microphone] and as a baseline for neural vocoders and codecs
[jassim2020vocoders; jacobellis2024mpq; bai2026semdac]. At 6–8 kbit/s it raises word error
rates, including Whisper's [khare2020opus; jacobellis2024mpq; bai2026semdac]. Opus at
6 kb/s, evaluated where the enhancement set-up implies wideband SILK, raised the WER of a
Conformer recogniser on LibriSpeech test-clean by about one point [buethe2024nolace].
Current neural-codec benchmarks do not include traditional codecs
[wu2024codecsuperb; shi2024espnetcodec].

*(Optional, if space: codec degradation beyond the 8 kHz band limitation is the premise of
codec augmentation for telephony ASR [vu2019codec; fernandezgallego2022contact].)*

### 2.2 Band limitation and narrowband ASR

Recognisers trained on wideband speech lose accuracy on narrowband input. Early comparisons
of TIMIT with its telephone-network versions confounded band limitation with other channel
effects [chigier1992phonetic; jankowski1990ntimit]. Mixed-bandwidth training and bandwidth
extension reduce the mismatch [seltzer2007mixed; li2012mixedbw; yu2013featurelearning;
mantena2019bwemb; mac2019largescale; li2015dnnbwe; gao2019mixedbw; li2019ssrasr]. With
matched training, removing content above 4 kHz from LibriSpeech costs relatively little:
0.2–0.3 points on dev-other for one Transformer-CTC model [likhomanenko2021rethinking], and
0.7 / 2.0 points on test-clean / test-other for an SSL model with matched fine-tuning
[sukhadia2023channelaware].

The shape of the passband also matters at a fixed nominal band [hirsch2000aurora]. For
current pretrained models, Speech Robust Bench found wav2vec2-base-960h far less robust
than Whisper to audio-processing perturbations that include low-pass filtering
[shah2025srb]. Foundation models perform poorly on real narrowband telephony, but there
bandwidth is confounded with codec, channel and domain [godambe2026responsible;
khalid2025bridging].

### 2.3 Separating band limitation from coding distortion

Several studies have separated the band limitation of a transmission chain from its other
distortions using a band-limited, uncoded reference. Moreno and Stern showed that
downsampling and telephone-band filtering of TIMIT reproduced only 3.0 of the 10.2
accuracy points lost on NTIMIT [moreno1994sources]. For narrowband codecs, uncoded 8 kHz
speech was the usual reference [lilly1996effect; hirsch2002influence].

Studies that also retained the wideband original reached codec-dependent conclusions:
- **GSM full rate:** most of the loss relative to wideband came from band limitation [besacier2001effect; heymans2022multistyle].
- **AMR-NB at 12.2 kbit/s:** the codec effect exceeded the bandwidth effect in phone recognition [bauer2010wtimit].
- **MP3 at 12 kbit/s:** a low-pass control at the cutoff observed for each bitrate explained less than one point of an 11–17-point increase. The authors described the combined effect as non-linear [borsky2015mp3].

Related designs include uncoded references at each sampling rate next to narrowband and
wideband codecs [fernandezgallardo2017predicting], and separations of bandwidth from coding
in speaker verification [fernandezgallardo2014advantages] and emotion recognition
[lech2020ser]. A recent preprint added a 3.4 kHz low-pass condition next to GSM and Opus
for two current recognisers, but did not compute a decomposition [basu2026factors].

These studies used nominal or cutoff-matched filters and recognisers retrained per
condition or from the HMM era, and none reports interval estimates for the components. None
of them decomposes an Opus penalty.

### 2.4 Controlled signal interventions that attribute ASR degradation

Outside coding, ASR penalties have been attributed to components of a processing chain by
re-synthesising partial versions of the signal:
- **Reverberation:** keeping the early part of a measured impulse response and attenuating the tail isolates the effect of late reverberation [sehr2010reverberation].
- **Speech enhancement:** orthogonal projection splits the enhanced signal into a linear "natural" part and an artifact residual; scaling each part shows that artifacts dominate the ASR loss [iwamoto2022artifacts; ochiai2024rethinking; araki2023residual]. In that framework, linear filtering of the target is not counted as error. Our bandwidth control does the opposite: it measures the ASR cost of the linear band limitation itself.
- **Ageing voices:** inserting one candidate component at a time tested whether voice-source changes reproduce the WER gap [vipperla2010ageing].

### 2.5 Positioning paragraph (for the end of §2)

> We apply the bandwidth-versus-residual logic to Opus at 8 kbit/s, where libopus 1.4 selects
> SILK narrowband automatically because the rate is below its 9 kbit/s wideband threshold
> [libopus-1.4; skoglund2020opus]. The design differs from earlier decompositions in three
> respects. First, the bandwidth control is fitted to the codec's measured linear transfer
> function and validated on held-out speakers. Second, the recognisers are fixed pretrained
> models of two architectures, evaluated on identical paired audio. Third, the components are
> estimated in a pre-registered paired design with speaker-bootstrap intervals, a same-mode
> high-rate reference and negative controls. The Opus–ASR studies cited above report total
> penalties; one attributes the 8 kbit/s loss to narrowband operation without a control
> [khare2020opus].

---

## 3. Citation checklist for §3 (Methods): Opus facts and their sources

| Statement in the paper | Source (verified) |
|---|---|
| Opus modes (SILK, Hybrid, CELT) and the five audio bandwidths | rfc6716 §2 Table 1, §3.1 Table 2 |
| SILK runs at twice the audio bandwidth (8/12/16 kHz); CELT at 48 kHz | rfc6716 §2; valin2013music §2 |
| 8–12 kbit/s is the NB-speech "sweet spot" for 20 ms frames | rfc6716 §2.1.1; rfc7587 §3.1.1; vos2013voice Table 2 |
| libopus 1.4 switches NB↔WB at 9 kbit/s (±700 bit/s hysteresis), so 8 kbit/s is SILK-NB | libopus-1.4 src/opus_encoder.c L123–137, L1462–1506; skoglund2020opus footnote 2 |
| OPUS_SET_BANDWIDTH overrides automatic selection (our forced-NB SILK condition) | libopus-1.4 include/opus_defines.h; opus_encoder.c L1508–1512 |
| Low-rate SILK: residual bits collapse below about 8 kb/s; quality degrades quickly below 10 kb/s | skoglund2020opus §2 and abstract |
| Ogg Opus pre-skip, 48 kHz granule positions, end trimming | rfc7845 §4.2–4.4, §5.1 |
| Decoder resampling is non-normative (delay normative; conformance per output rate) | rfc6716 §4.2.9, §6 |
| FFmpeg's native decoder outputs 48 kHz and upsamples SILK with libswresample (filter_size 16) | ffmpeg-6.1.1-opusdec (opusdec.c L685, L721–732) |
| NEG_CODEC is CELT (MDCT) | valin2010celt; rfc6716 |
| Opus is mandatory for WebRTC (motivation) | rfc7874 §3 |
| Statistics | bisani2004bootstrap; efron1993bootstrap |
| Data and models | panayotov2015librispeech; radford2023whisper; baevski2020wav2vec; graves2006ctc |

Wording cautions from the primary sources:
- **12 kbit/s.** Do not write that 12 kbit/s is in the RFC's wideband region: RFC 6716 lists 8–12 kbit/s as the NB sweet spot. Wideband at 12 kbit/s is libopus behaviour from v1.2 onward.
- **Version.** Name the library version: libopus 1.4.
- **Resampling.** Write "non-normative (implementation-defined within conformance limits)", not "arbitrary".
- **Design sources.** Cite vos2013voice and RFC 6716 §5 for design rationale only. libopus removed the SILK prefilter in 2016, so the encoder prose is not an exact description of v1.4.
- **Opus ≥ 1.5 enhancement.** It does not apply to our NB condition: OSCE is opt-in and wideband-only (libopus-1.5.2/1.6.1 dnn/osce.c; osce-draft-04 §3).

## 4. Hooks for §1 (Introduction)

- **Deployment.** Opus is mandatory for WebRTC [rfc7874]. At low rates libopus switches to narrowband SILK [libopus-1.4].
- **The attribution gap.** khare2020opus attributes the 8 kbit/s collapse to narrowband operation ("OPUS encodes the audio as narrowband at 8kbps") without testing it. Studies of real narrowband telephony with foundation models attribute failures to "wide-band" training, with bandwidth confounded [godambe2026responsible].
- **Codec-dependent answers.** Prior decompositions disagree across codecs (GSM: bandwidth-dominated; AMR-NB 12.2 and MP3: residual-dominated) [besacier2001effect; bauer2010wtimit; borsky2015mp3]. The Opus answer therefore has to be measured.
- **Standards view.** "The degradations are as a result of both the low bit rate speech coding and channel transmission errors" [etsi-dsr].

## 5. Hooks for §5 (Discussion)

Details and hedges are in `novelty_boundary.md` §5.
- **Direction agrees** with bauer2010wtimit (AMR-NB 12.2) and borsky2015mp3 (MP3).
- **Direction differs** from besacier2001effect and heymans2022multistyle (GSM FR). Our 40 kbit/s SILK-NB reference sits on the GSM-FR side. This is consistent with the residual depending on coding rate, but not tested.
- **Recogniser ordering** of the bandwidth component matches shah2025srb.
- **Residual** is consistent with buethe2024nolace and skoglund2020opus.
- **Additivity.** borsky2015mp3 reports a non-linear combination of band limitation and coding. State that our shares are path-dependent (REF → LP → OPUS) and that the residual includes any interaction.
- **Imaging.** Folded or imaged components can carry recognisable information and shift WER [pohlhausen2025lowfreq]. This is relevant if the 4–5 kHz image is discussed, but it is a different regime (anti-aliasing at very low rates).
- **Speech enhancement analogy.** The NTT projection framework never charges linear filtering as error [iwamoto2022artifacts; ochiai2024rethinking]. Our LP − REF term is exactly that charge.

## 6. Corrections to the course report's descriptions (if reused)

- **besacier2001effect.** The course report says telephony codecs "(GSM, G.711) did not" degrade recognition.
  - The full text shows no GSM effect on the constrained CSTAR120 task (91.6 vs 91.6 %).
  - On AUPELF (28k vocabulary), GSM had "a slight negative influence" (49.7 → 46.3 %), and the loss relative to 16 kHz was "mainly due to the bandlimiting".
  - Use this more precise description; it is now a key precedent.
- **narayanan2018domain.** Quote the verified numbers: Opus 24k 10.8 → 10.2 % with codec training; MP3 23k 13.6 → 10.6 %; no codec 10.5 → 10.0 %. The 8 kHz condition is a separate test set.
- **drude2021opus.** Correct as summarised. Add that it forced SILK vs CELT *mode*, not bandwidth, and covered no narrowband regime (16–128 kbit/s per channel).
- **Other keys.** Unchanged.

## 7. Reading list before submission (not yet verified in full)

Priority:
1. Borský et al. 2017, *Speech Communication* 86:75–84 (MP3; may extend the bandwidth vs spectral-valley analysis).
2. Cauchi et al. 2025, *Speech Communication* 173:103270 (reportedly Whisper under low-pass filtering at 1–6 kHz).
3. Málek et al. 2018 (TSD; compression and narrowband applied as separate augmentations).
4. Any published version of basu2026factors.
5. Barras et al. 2001 full text.
6. Siegert et al. 2016 and Albahri & Lech 2016 (emotion recognition; codec vs reduced bandwidth).

Also re-run the queries in `novelty_boundary.md` §9 (ICASSP 2026, Interspeech 2026, arXiv).

## 8. Suggested core reference set (about 30)

- **Codecs × ASR:** euler1994influence, lilly1996effect, besacier2001effect, hirsch2002influence, moller2002analytic, 3gpp2004tr26943, borsky2015mp3, narayanan2018domain, khare2020opus, drude2021opus, jacobellis2024mpq, buethe2024nolace, wu2024codecsuperb.
- **Bandwidth:** moreno1994sources, bauer2010wtimit, seltzer2007mixed, likhomanenko2021rethinking, li2019ssrasr, hirsch2000aurora, shah2025srb.
- **Separation:** heymans2022multistyle, fernandezgallardo2017predicting, basu2026factors (preprint; cite as such).
- **Interventions:** sehr2010reverberation, iwamoto2022artifacts, ochiai2024rethinking.
- **Opus:** rfc6716, rfc7845, skoglund2020opus, vos2013voice, libopus-1.4 and ffmpeg-6.1.1 (as software citations).
- **Models and statistics:** radford2023whisper, baevski2020wav2vec, panayotov2015librispeech, bisani2004bootstrap.
