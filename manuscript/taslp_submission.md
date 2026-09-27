---
title: "How much of the ASR penalty of 8 kbit/s Opus is bandwidth loss? A decomposition with a validated bandwidth control"
author: "[Authors withheld for review]"
date: "TASLP submission version, 2026-09-27"
bibliography: references.bib
link-citations: true
---

<!--
TASLP SUBMISSION VERSION (remove before submission)

- Derived from draft 2 (manuscript/manuscript.md, commit dbf8d5c) by editorial restructuring, plus the text and tables
  of the later sealed analyses (R3, R4 and the final invariance pass: A1, B1, C1), all taken from sealed records.
  Moved material is in taslp_supplement.md (supplementary material).
- Every table row and number of both files is checked against the frozen outputs by
  `python manuscript/tools/check_numbers.py --submission`; render with tools/render_ieee.sh taslp_submission.md.
-->

# Abstract

Low-bitrate speech codecs degrade automatic speech recognition (ASR); their narrowband modes
remove bandwidth and add coding distortion at once, and studies of GSM, AMR and MP3 disagree on
the share due to bandwidth. We measure it for Opus at 8 kbit/s (SILK narrowband in libopus) with
a zero-phase low-pass control fitted to SILK narrowband's measured high-rate linear transfer function and
validated on unseen speakers. In a paired design specified and version-sealed before any
evaluation audio was decoded (a pilot, then one confirmatory run: 2,174 LibriSpeech test
utterances, 73 speakers), bandwidth removal alone increased corpus WER by 0.14 percentage points
(pp) for Whisper large-v3 and 1.40 pp for wav2vec2-base-960h. Opus added a further 0.69 and
2.07 pp beyond the control (95 % speaker-bootstrap intervals excluding zero), so bandwidth removal
accounted for a minority of the total Opus penalty (sequential, path-dependent attribution).
High-rate SILK narrowband showed no detectable pooled residual. Sensitivity analyses sealed after
the confirmation did not remove the residual: 0.70 and 2.09 pp remained after RMS level matching,
and 0.74 and 2.32 pp beyond a per-utterance best-linear projection of the codec output; its
excess over the bandwidth component held under four error weightings. On 1,665 unused test utterances (a fresh-utterance,
not fresh-speaker, holdout), the residual of forced SILK narrowband decreased as the bitrate rose
from 8 to 40 kbit/s, by 0.21 and 0.85 pp per doubling. This supports, but does not isolate, the
interpretation of the residual as low-rate in-band coding distortion.

**Index Terms**: speech recognition, speech coding, Opus, bandwidth limitation, robustness,
Whisper, wav2vec 2.0

# 1. Introduction

Speech is often compressed by a lossy codec before a recogniser sees it. Opus [@rfc6716;
@rfc8251] is one of the two audio codecs that every WebRTC endpoint must implement [@rfc7874].
The effect of speech coding on ASR has been studied since low-rate coders entered telephone
networks. Error rates rise as the coding rate falls [@euler1994influence; @lilly1996effect;
@hirsch2002influence], codec effects differ between recognisers [@moller2002analytic], and
standards bodies considered them large enough to evaluate distributed front-ends as an
alternative to the voice codec [@3gpp2004tr26943].

At low bitrates many codecs change two things at once: they reduce the audio bandwidth, and
they add coding distortion within the band they keep. Opus illustrates this. Its
linear-prediction layer, SILK, runs at twice the coded audio bandwidth, and the reference
encoder chooses the bandwidth from the requested bitrate and other parameters [@rfc6716]. In
libopus 1.4 the narrowband/wideband switch lies at 9 kbit/s [@libopus14; @skoglund2020opus],
so at 8 kbit/s Opus codes only the band below 4 kHz. Because SILK's spectral-envelope bits
hardly vary with rate, the bits left for the excitation fall rapidly as the rate drops below
about 8 kbit/s [@skoglund2020opus]. A word-error-rate (WER) increase at 8 kbit/s can therefore
come from the missing band, from in-band coding distortion, or from both. Studies that ran
low-rate Opus through recognisers report the combined penalty [@khare2020opus;
@jassim2020vocoders; @jacobellis2024mpq; @bai2026semdac]; one attributes the collapse at
8 kbit/s to narrowband operation without a control for it [@khare2020opus]. Our preliminary
analysis raised the same question. It used wav2vec2-base-960h on other LibriSpeech test
utterances with a different scoring convention and is context only: WER on test-other rose by
1.33 pp at 12 kbit/s but by 6.63 pp at 8 kbit/s, where libopus switches from wideband to
narrowband SILK.

Separating band limitation from other degradations is not new. Moreno and Stern
[@moreno1994sources] showed that band-limiting TIMIT to the telephone band reproduced only part
of the recognition loss on its telephone-network version, NTIMIT [@jankowski1990ntimit].
Comparisons of coded speech with band-limited uncoded speech have reached different
conclusions for different codecs. For GSM full rate, most of the loss relative to wideband
speech was due to band limitation [@besacier2001effect; @heymans2022multistyle]. For AMR-NB at
12.2 kbit/s, the codec effect exceeded the bandwidth effect in phone recognition
[@bauer2010wtimit]. For MP3 at 12 kbit/s, a low-pass control at the codec's observed cutoff
explained less than one point of an 11–17-point WER increase [@borsky2015mp3]. Those studies
used recognisers of the HMM era, most of them trained or retrained for each bandwidth, and
nominal or cutoff-matched filters. Because the answer differs between codecs, and because
recognisers are now often used as fixed pretrained models, the share of the low-rate Opus
penalty due to bandwidth has to be measured rather than inferred.

This paper measures it. A zero-phase linear low-pass filter reproduces the linear band
limitation of SILK narrowband; it is fitted to the codec's measured high-rate transfer function and
validated on held-out speakers before any recognition experiment. The control separates the
penalty of Opus at 8 kbit/s into a bandwidth component (control minus original) and a
codec-specific residual (Opus minus control); because the decomposition is sequential, the
bandwidth share it yields is path-dependent. Both components are estimated for Whisper
large-v3 [@radford2023whisper] and wav2vec2-base-960h [@baevski2020wav2vec], evaluated without
adaptation on identical, paired audio. The conditions, data split, recognisers, metrics and
decision rules were fixed and sealed before a pilot was decoded, and a single confirmatory run
followed. Each later analysis was specified and sealed before any of its audio was encoded, and
each was run once. The contributions are:

1. **A bandwidth control for Opus SILK narrowband:** a linear-phase low-pass filter fitted to the codec's measured linear transfer function and validated on held-out speakers against pre-specified tolerances. The validation history, including a failed first criterion, is reported.
2. **A prospectively specified, paired estimate of the two components of the 8 kbit/s Opus penalty:** the bandwidth component and the codec-specific residual, estimated for two pretrained recognisers with speaker-cluster bootstrap intervals and negative controls.
3. **A same-mode high-rate reference and signal descriptors:** forced SILK narrowband at 40 kbit/s, which, together with the descriptors, constrains, but does not identify, the mechanism of the residual.
4. **Prospectively specified follow-up and sensitivity analyses:** a forced SILK narrowband bitrate sweep on fresh utterances that tests whether the residual depends on the coding rate; sensitivity analyses of the residual (RMS level matching, and an inclusive best-linear attribution of the actual codec output) and of the total penalty (decoder; encoder application mode); and a metric and weighting audit.

# 2. Related work

**Speech codecs and ASR.** For HMM-era recognisers, errors grew as the coding rate fell, and
tandem coding compounded the losses [@euler1994influence; @lilly1996effect;
@hirsch2002influence]; codec effects were recogniser-specific and poorly predicted by
perceptual-quality models [@moller2002analytic]. Audio codecs such as MP3 were harmless at
high rates and increasingly harmful as the rate fell, with severe losses at the lowest rates
tested (8–12 kbit/s) [@besacier2001effect; @pollak2011mp3; @borsky2015mp3]. For neural
recognisers, codec-simulated training reduces the penalty [@narayanan2018domain; @vu2019codec].
Opus has been evaluated mainly in multichannel far-field front-ends [@khare2020opus;
@drude2021opus] and as a baseline for neural vocoders and codecs [@jassim2020vocoders;
@jacobellis2024mpq; @bai2026semdac]. At 6–8 kbit/s it raises word error rates, including
Whisper's [@khare2020opus; @jacobellis2024mpq; @bai2026semdac]. At 6 kb/s, in an evaluation
whose set-up implies wideband SILK, Opus raised the WER of a Conformer recogniser on
LibriSpeech test-clean by about one point [@buethe2024nolace]. Current neural-codec benchmarks
evaluate neural codecs only [@wu2024codecsuperb; @shi2024espnetcodec].

**Band limitation and narrowband ASR.** Recognisers trained on wideband speech lose accuracy on
narrowband input; mixed-bandwidth training and bandwidth extension reduce the mismatch
[@seltzer2007mixed; @li2019ssrasr]. With matched training, removing content above 4 kHz from
LibriSpeech costs relatively little: 0.2–0.3 points on dev-other for one Transformer-CTC model
[@likhomanenko2021rethinking]. Passband shape matters as well as cutoff [@hirsch2000aurora].
Among current pretrained models, Speech Robust Bench found wav2vec2-base-960h far less robust
than Whisper to audio-processing perturbations that include low-pass filtering [@shah2025srb].
Foundation models perform poorly on real narrowband telephony, but there bandwidth is
confounded with codec, channel and domain [@godambe2026responsible].

**Separating band limitation from coding distortion.** Section 1 summarises the studies closest
to ours [@moreno1994sources; @besacier2001effect; @bauer2010wtimit; @borsky2015mp3;
@heymans2022multistyle]. For narrowband codecs, uncoded 8 kHz speech was the usual reference
[@lilly1996effect; @hirsch2002influence], and uncoded references at each sampling rate have
also been placed next to narrowband and wideband codecs [@fernandezgallardo2017predicting].
Bandwidth and coding have been separated in speaker verification
[@fernandezgallardo2014advantages] and emotion recognition [@lech2020ser]. A recent preprint
added a 3.4 kHz low-pass condition next to GSM and Opus for two current recognisers, but did
not compute a decomposition and did not state the Opus bitrate [@basu2026factors]. The nearest
precedent for a codec-matched control filtered uncoded speech with a low-pass at the cutoff
estimated from spectrograms for each MP3 bitrate [@borsky2015mp3]. Neural-codec frequency
responses have been measured with sine sweeps, but not used as a control [@tseng2025probing].

**Controlled signal interventions.** Keeping the early part of a measured impulse response and
attenuating the tail isolates late reverberation [@sehr2010reverberation]. In speech
enhancement, orthogonal projection splits the enhanced signal into a linear "natural" part and
an artifact residual, and scaling each part shows that artifacts dominate the ASR loss
[@iwamoto2022artifacts; @ochiai2024rethinking]. In that framework linear filtering of the
target is not counted as error. Our bandwidth control does the reverse and measures the ASR
cost of the linear band limitation itself. As a sensitivity analysis, we also apply their
projection to the codec output (Section 3.11).

**Position of this study.** The Opus–ASR studies we located report total penalties. The design
here follows the bandwidth-versus-codec comparisons above. It differs from them in the codec
(one whose audio bandwidth the encoder selects from the bitrate), in the control (fitted to the
measured linear response and validated on held-out speakers), in the recognisers (fixed
pretrained models of two architectures), and in the statistics (paired, prospectively specified and
version-sealed, with speaker-level intervals).

# 3. Methods

## 3.1 Overview and prospective specification

Every utterance was processed under six conditions and decoded by both recognisers (Table I).
Before any pilot or confirmation utterance was decoded, a hash-stamped specification was sealed
and committed to version control; the specification is internal and was not lodged in a public
registry. It fixed the data selections, the conditions and exact
encoder settings, the recognisers and decoding options, the text normalisation, and the
metrics, bootstrap and decision rules. The pilot was decoded once; a pre-declared kill test was
applied, and the analysis code was then sealed again. The confirmation set was decoded once,
without restarts, and analysed with the frozen code. A 20-utterance calibration set (4
dev-clean speakers) was used only to check that decoding succeeded, was deterministic and had
adequate throughput; it computed no condition comparison. The codec and filter controls
described below were validated in two earlier stages that used no ASR output. Every later
analysis (Sections 3.9, 3.10 and 3.11) was specified and sealed after the confirmatory analysis
was closed and before any of its audio was encoded; none changes any confirmatory estimate or
decision.

## 3.2 Data

We used LibriSpeech [@panayotov2015librispeech]: 16 kHz read English speech. wav2vec2-base-960h
was fine-tuned on all 960 hours of the LibriSpeech training subsets, so evaluation data were
drawn from the dev and test subsets only. The three splits share no speakers. The calibration
set has 20 utterances from 4 dev-clean speakers, and the pilot has 138 utterances from 69
speakers (36 dev-clean, 33 dev-other; two per speaker). The confirmation set has 2,174
utterances from 73 speakers (test-clean: 40 speakers, 1,190 utterances; test-other: 33
speakers, 984 utterances), with 16,083 s of audio and 43,417 normalised reference words. Each
split was drawn with its own random seed. Exclusions were fixed at selection time from metadata
only: utterances longer than 30 s (Whisper's input window), utterances with an empty normalised
reference, the development utterances used for the controls and, for the confirmation set, the
1,000 utterances of the preliminary analysis, so the confirmation utterances had never been
decoded in this project, although their speakers are the same test speakers. No utterance was
excluded after decoding.

## 3.3 Conditions and codec pipeline

| Condition | Processing | Encoder settings (libopus 1.4) | Packets (confirmation) |
|---|---|---|---|
| REF | Original waveform | — | — |
| LP | Frozen zero-phase low-pass control (Section 3.4) | — | — |
| OPUS | Opus, 8 kbit/s | Bandwidth NB, `signal=auto`, application audio, unconstrained VBR, complexity 10, 20 ms frames, no FEC/DTX | 100 % SILK-NB; median 8.17 kbit/s |
| SILK | Opus, 40 kbit/s | As OPUS, but `signal=voice` | 100 % SILK-NB; median 39.79 kbit/s |
| NEG_LP | Negative control: zero-phase low-pass, flat to 7.0 kHz | — | — |
| NEG_CODEC | Negative control: Opus, 64 kbit/s, automatic bandwidth | `signal=auto` | 100 % CELT-WB; median 70.59 kbit/s |

: Conditions. Bitrates are measured over the Ogg files, including container overhead.

**Encoding.** Opus conditions were encoded with libopus 1.4 through its C API, and bandwidth,
mode and bitrate were read from every packet's table-of-contents byte [@rfc6716]. OPUS
reproduces the encoder configuration of the preliminary analysis (byte-identical packets on 40
dev-clean utterances; not re-verified on the test utterances). At 8 kbit/s, libopus 1.4 selects
narrowband automatically [@libopus14]; forcing it gave the same packets (40/40). SILK is a high-rate narrowband reference:
narrowband is forced at 40 kbit/s, and the signal-type hint is set to *voice*, because with
`signal=auto` high-rate forced-narrowband encoding produced about 2.5 % CELT packets when the
control was developed. OPUS − SILK therefore differs in bitrate *and* in the signal-type hint,
and we treat SILK as a supporting reference, not as a bitrate-only contrast.

**Decoding.** The encoded packets were written to Ogg Opus [@rfc7845], with the encoder
lookahead as pre-skip and end trimming by granule position. They were decoded by FFmpeg
6.1.1's native Opus decoder [@ffmpeg611] at 48 kHz and resampled to 16 kHz with torchaudio's
default resampler, as in the preliminary analysis; decoded signals have the same length as REF.
Opus leaves resampling of the SILK output to the implementation [@rfc6716, Sec. 4.2.9], and
FFmpeg upsamples SILK output with its own interpolator, which differs from the reference
decoder's [@ffmpeg611; @libopus14]. All codec results below are therefore defined for this
encoder–decoder chain.

**No realignment or level normalisation (both pre-declared).** Lags relative to REF were 1–2
samples for OPUS and SILK and 0 for the other conditions. Median RMS level changes relative to
REF were −0.68 dB for OPUS (5th–95th percentile −2.09 to −0.34 dB), −0.11 dB for SILK and
−0.08 dB for LP; for NEG_LP and NEG_CODEC they were below 0.01 dB in magnitude. All processing
was in floating point and no sample was clipped. Between 66 (NEG_LP) and 136 (LP) samples per
condition, out of about $2.6 \times 10^{8}$, exceeded full scale; the recognisers received them
unchanged. The level-matched condition of Addition A (Section 3.9) is the only condition to
which a gain was applied.

## 3.4 Bandwidth control

**What the control reproduces.** A preparatory analysis on dev-clean (no ASR) showed that SILK
narrowband output, as decoded here, consists of three components: (i) a bitrate-independent
linear band-limiting response; (ii) a mirror image of the 3–4 kHz band in 4–5 kHz, coherent
with the input at $8000 - f$ rather than at $f$; and (iii) bitrate-dependent coding distortion
within the retained band. The control was defined, before it was built, to reproduce
component (i) only.

**Target.** The target was SILK narrowband's linear transfer function
$$\lvert H_1(f)\rvert = \frac{\lvert S_{xy}(f)\rvert}{S_{xx}(f)},$$
pooled over 40 dev-clean calibration utterances encoded at 40 kbit/s with `signal=voice`
(100 % SILK narrowband) and normalised to its 0.5–2 kHz level. The target response was 0 dB up
to 3.0 kHz, the measured response above that (made monotone), and a floor of −80 dB.

**Filter design and application.** The filter is a 1,023-tap type-I FIR designed by frequency
sampling with a Kaiser window ($\beta = 8$), with exact symmetry and unit DC gain. It is
applied by FFT convolution with the 511-sample delay removed, so it is zero-phase and preserves
length. The reference had not fully converged at 40 kbit/s: between 32 and 40 kbit/s it still
rose by 0.24–0.83 dB (mean 0.46 dB) over 3.0–4.1 kHz. The control may therefore attenuate the
band edge slightly more than the asymptotic linear chain, which would bias the bandwidth
component slightly up and the residual slightly down.

**Validation.** The first validation (dev-clean and dev-other) failed one criterion: that the
control's coherent 4–8 kHz power lie within 6 dB of Opus at 8 kbit/s. That quantity includes
bitrate-dependent coding droop across the 4 kHz edge, so the criterion contradicted the
linear-only definition; the failed result is retained in the record. The corrected criterion
compares the control with the linear reference at the unchanged 3 dB tolerance, and it was
frozen before the confirmation data were downloaded. On an independent filter-validation set of
40 unseen train-clean-100 speakers (20 female, 20 male) with the filter taps unchanged, all criteria
passed (Fig. 1; the measured values are in Supplementary Table S1).

![Validation of the low-pass (LP) control on 40 unseen train-clean-100 speakers, drawn from the frozen confirmation curves of the control's validation. (a, b) Linear transfer $\lvert H_1\rvert$ relative to its 0.5–2 kHz level: LP follows the SILK narrowband linear reference (40 kbit/s, `signal=voice`); Opus at 8 and 12 kbit/s (narrowband) shows additional bitrate-dependent attenuation within the band and at the band edge. (c) Coherence with the input at the same frequency. (d) Coherence of the output at $f$ with the input at $8\,\mathrm{kHz} - f$: the 4–5 kHz content of the SILK narrowband conditions is a mirror image of the 3–4 kHz band, and LP contains none.](figures/fig_lp_validation.pdf){#fig:lpvalidation}

## 3.5 Recognisers

Neither recogniser was fine-tuned or adapted to any condition. Whisper large-v3
[@radford2023whisper] was run from the checkpoint `openai/whisper-large-v3` (pinned revision)
in float16, with greedy decoding at temperature 0 and no temperature fallback (no
compression-ratio, log-probability or no-speech thresholds), the language fixed to English,
task *transcribe*, no timestamps, no prompt and a 30 s input window. Greedy decoding replaced
beam search before any evaluation decoding, for compute reasons; it was deterministic across
repeats and between batched and unbatched decoding on the calibration set, although batches of a
different composition changed three Whisper hypotheses (Section 4.9). wav2vec2-base-960h [@baevski2020wav2vec] was run from
the torchaudio checkpoint in float32 with greedy CTC decoding [@graves2006ctc] and no language
model; this is the recogniser and decoder of the preliminary analysis.

## 3.6 Scoring

References and all hypotheses of both recognisers were normalised with Whisper's English text
normaliser [@radford2023whisper], which lower-cases, removes punctuation and fillers, expands
contractions, and standardises numbers and spelling. With $S$, $D$ and $I$ the substitutions,
deletions and insertions of the word alignment and $N$ the number of reference words,
$\mathrm{WER} = (S + D + I)/N$; the character error rate (CER) is secondary. Absolute WERs are
not comparable with the preliminary analysis, which scored raw text on different utterances.

## 3.7 Statistical analysis and decision rules

**Contrasts and decomposition.** The primary contrasts are LP − REF (the *bandwidth component*)
and OPUS − LP (the *codec-specific residual*); OPUS − REF is the total. The residual is the part
of the Opus penalty that the linear band limitation does not reproduce. It therefore contains
in-band coding distortion and every other difference between the decoded Opus signal and the LP
signal, including the 4–5 kHz image, the small level change and the 1–2 sample lag. The
decomposition is sequential (REF → LP → OPUS): its two parts add up to the total by
construction, but any interaction between band limitation and coding falls into the residual
[cf. @borsky2015mp3]. The pre-declared secondary *bandwidth share*
$$s_{\mathrm{bw}} = \frac{\mathrm{WER}_{\mathrm{LP}} - \mathrm{WER}_{\mathrm{REF}}}{\mathrm{WER}_{\mathrm{OPUS}} - \mathrm{WER}_{\mathrm{REF}}}$$
is therefore a path-dependent share along this path, not an interaction-free attribution. Secondary contrasts are SILK − LP, OPUS − SILK,
SILK − REF, and the two negative controls minus REF.

**Estimators and bootstrap.** The primary estimator is the difference in corpus (micro) WER,
computed from total edit counts. Secondary estimators are the mean per-utterance WER difference
(macro), CER, and the substitution / deletion / insertion composition per 100 reference words.
Intervals are 95 % paired percentile bootstrap intervals from resampling speakers with
replacement, stratified by subset [@bisani2004bootstrap; @efron1993bootstrap]; all conditions
and both recognisers of an utterance stay together in each replicate (10,000 replicates, fixed
seed). The pooled confirmation set is the primary scope; per-subset results are secondary and
uncorrected for multiplicity. Baseline-relative effects (component divided by a baseline WER)
are post hoc descriptive ratios without intervals.

**Decision rules (sealed before decoding).** The pilot PROCEEDS if the lower bound of the
residual interval is above zero for any recogniser and codec. The confirmation returns:

- **GO** if, for some codec, the residual interval lies above zero in both recognisers, the estimate is at least 0.5 pp in both, and the pilot estimate was positive in both;
- **CONDITIONAL GO** if the residual is robust in both recognisers but short of GO;
- **KILL** if all residual intervals include zero;
- **HOLD** otherwise.

GO and CONDITIONAL GO are capped at HOLD if a negative control's interval excludes zero *and*
its estimate exceeds 0.5 pp in magnitude. Error types and exploratory correlations were
pre-declared to run only if a residual survived.

## 3.8 Signal descriptors (descriptive only)

Per-utterance descriptors were computed from short-time spectra (512-point FFT, 400-sample
Hann window, 160-sample hop, log spectra floored 80 dB below the reference peak): the
log-spectral distance (LSD) over the full band and over 0–3, 0–4 and 4–8 kHz
[@gray1980distortion]; the power-based retained bandwidth, i.e. the highest frequency whose
long-term power is within 20 dB of the reference; the change in 4–8 kHz power; and the
coherence over 0–3.5 kHz. They were also computed between each codec condition and LP. Pooled
cross-spectral descriptors per condition were the in-band gain $\lvert H_1\rvert$ and the
coherent bandwidth (the −20 dB point of $\lvert H_1\rvert$); the coherent and total 4–8 kHz
power; and the *mirror coherence*, i.e. the coherence between the output at $f$ and the input
at $8000 - f$ over 4.1–4.9 kHz, which measures how faithfully an image copies the input, not
how strong it is. STOI and PESQ were not computed. 36 Spearman correlations between
per-utterance residuals and signal features were pre-declared as exploratory.

## 3.9 Follow-up analyses (sealed after the confirmation)

Both analyses reuse the codec path, control, recognisers, scoring and bootstrap of Sections
3.3–3.7 unchanged, with 95 % speaker-cluster intervals from 10,000 replicates. Each has its own
pre-declared three-way rule, applied per recogniser; the rules and thresholds are given in
Supplementary Sections S4 and S5. Before the code was frozen, one dated
amendment corrected an analytic expectation of the plan; it changed no estimand, gate,
threshold, condition, selection or rule (Supplementary Section S6).

**Addition A: level-matched sensitivity analysis.** This is a post-confirmation sensitivity
analysis, not a second confirmatory test. The decoded Opus signal was about 0.6 dB quieter than
LP (Section 3.3), so the residual contains a level difference. Addition A decodes the 2,174
confirmation utterances a second time under LP, OPUS and OPUS8_LEVEL_MATCHED. The last is the
decoded OPUS waveform multiplied by one scalar gain per utterance,
$g_u = \mathrm{RMS}(\mathrm{LP}_u)/\mathrm{RMS}(\mathrm{OPUS}_u)$, computed in float64 over every
sample. Nothing else is applied: no re-encoding, automatic gain control, realignment, per-band
gain, clipping or limiting. Before recognition, LP and OPUS had to reproduce the confirmation
audio bit for bit and the level matching had to be exact (Supplementary Section S4). The primary contrast
is $L$ = OPUS8_LEVEL_MATCHED − LP; the effect of level matching is $K$ = OPUS8_LEVEL_MATCHED −
OPUS. The pre-declared criterion for a residual that persists under level
matching is that the interval of $L$ lies above zero and that of $K$ excludes level matching
removing a quarter or more of the confirmatory residual. The bootstrap reuses the confirmation's seed on the same speakers. Because the
confirmation had already been analysed, the outcome can qualify the interpretation of the
confirmatory residual but cannot strengthen it.

**Addition B: forced SILK narrowband bitrate sweep.** This is a fresh-utterance, not
fresh-speaker, holdout. In the confirmatory design, OPUS and SILK differed in bitrate and in the
signal-type hint (Section 3.3). Addition B varies the bitrate alone: narrowband is forced with
`signal=voice` at 8, 12, 16, 24 and 40 kbit/s (SILK8–SILK40), and every other encoder setting,
the decoder and the resampler are held fixed; SILK40 has exactly the settings of SILK. The
sweep used 1,665 test utterances of 70 speakers that the project had never encoded, decoded or
recognised, selected from metadata only with the confirmation rule (Supplementary Section S5).
All 70 speakers also appear in the confirmation set, because no other test speakers were left
and the other subsets had been used for development or training, so the results generalise to
new utterances of the test speakers, not to new speakers. REF was not recognised. Before recognition, encoding and
decoding alone had to confirm the packet mode, the encoder settings and the bitrates
(Supplementary Section S5). The
primary quantities are the residuals $R_b$ = SILK$b$ − LP and the ordinary least-squares slope
$S$ of $R_b$ on $\log_2 b$, in pp per doubling of bitrate, recomputed in every bootstrap
replicate. The pre-declared criterion is a residual at 8 kbit/s that declines with rate: the
interval of $R_8$ lies above zero, and that of $S$ lies below zero and does not exclude a decline
half as steep as the confirmatory residuals at 8 and 40 kbit/s imply. Slopes on the rate rank and on the measured payload bitrate, adjacent-rate
contrasts, per-subset scopes and the descriptors of Section 3.8 are secondary or descriptive and
do not enter the rule; the five residuals are not corrected for multiplicity.

## 3.10 Forced-wideband counterfactual (sealed after the follow-up analyses)

A later plan, specified after Additions A and B and sealed before any of its audio was encoded,
added a practical counterfactual: at the same nominal 8 kbit/s, does spending the bits on
wideband instead of narrowband change WER? It reuses the 1,665 utterances of Addition B, so it
is again a fresh-utterance, not fresh-speaker, holdout. NB8 has the confirmatory OPUS settings
(8 kbit/s, forced narrowband, `signal=auto`) and WB8 the same settings with wideband forced; the
decoder and the resampler are unchanged. Before recognition, NB8 had to reproduce Addition B's
SILK8 files, and WB8's packet mode, settings, bitrate and restored high-band power were checked
(Supplementary Section S7). The primary contrast is $W$ = WB8 − NB8 per recogniser, with 95 %
speaker-bootstrap intervals (Addition B's seed on the same speakers); the pre-declared outcome is
whether its interval lies below zero, above zero or includes zero, and no combined outcome is
formed. Forcing wideband also changes SILK's internal sampling
rate, its LPC order and the allocation of the bit budget, so this is a practical
bandwidth-allocation counterfactual, not a factorial estimate of an interaction between
bandwidth loss and coding distortion, and it does not enter the decomposition. The same plan
included two attribution sensitivities that were stopped before recognition (Supplementary
Section S7).

## 3.11 Sensitivity of the residual, the total and the metric (sealed after all of the above)

Three final plans, each sealed before any of its audio was generated, tested the definition of
linear loss, the encoder application mode and the error weighting.

**Inclusive best-linear attribution.** The control reproduces SILK narrowband's high-rate linear
response; the 8 kbit/s chain has its own, lossier one. To test whether the residual is linear
loss that the control leaves out, the decoded 8 kbit/s Opus signal of each confirmation
utterance was orthogonally projected onto REF delayed by −256 to +255 samples, as in the
projection-based decomposition of enhancement artefacts [@iwamoto2022artifacts;
@ochiai2024rethinking]. The projection, LIN8, contains every change that one time-invariant
512-tap filter per utterance reproduces from REF (gain, tilt, roll-off, phase and delay);
OPUS − LIN8 contains the rest, such as time-varying coding error, the mirror image and nonlinear
distortion. The method has no free parameter; it was calibrated and validated, signal only, on
80 new speakers before the plan was committed, and LIN8 was recognised once. The pre-declared
criterion for a robust residual is that OPUS − LIN8 lies above zero and exceeds LIN8 − REF in
both recognisers. The attribution does not replace the sequential decomposition, and its linear
share is not a bandwidth share.

**Encoder application mode.** The confirmatory settings used `application=audio`, as in the
preliminary analysis, whereas real-time VoIP deployments typically use `OPUS_APPLICATION_VOIP`. A
further plan changed only that encoder parameter (OPUS_VOIP8), checked the new bitstreams before
recognition and recognised them once; the pre-declared outcome is whether the interval of
OPUS_VOIP8 − OPUS lies below zero, above zero or includes zero, with no equivalence margin and no
bandwidth share.

**Metric and weighting robustness.** Without new recognition, the bandwidth component, the
residual, the total, their difference and the sequential share were recomputed in every
bootstrap replicate of the confirmation under four weightings (corpus WER, mean per-utterance
WER, equal-speaker WER and CER), per error type and per subset. Criteria fixed before the audit
classified each statement as robust to the weighting, weighting-sensitive, subset-dependent or,
for ratios, unstable.

# 4. Results

## 4.1 Pilot

The pilot (138 utterances, 69 speakers) was decoded once and analysed with the sealed code. Its
pre-declared kill test returned PROCEED: the residual interval excluded zero in both
recognisers (Supplementary Section S2, Table S2).

## 4.2 Confirmation: word error rate by condition

| Condition | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| REF | 2.50 [2.19, 2.84] | 5.36 [4.73, 6.08] |
| LP | 2.64 [2.32, 2.98] | 6.76 [5.89, 7.74] |
| OPUS | 3.32 [2.86, 3.82] | 8.84 [7.72, 10.17] |
| SILK | 2.66 [2.34, 3.01] | 6.68 [5.85, 7.60] |
| NEG_LP | 2.42 [2.11, 2.76] | 5.46 [4.80, 6.22] |
| NEG_CODEC | 2.50 [2.19, 2.84] | 5.36 [4.71, 6.10] |

: Corpus WER (%) on the confirmation set (2,174 utterances, 73 speakers, 43,417 reference words), with 95 % speaker-bootstrap intervals.

In both recognisers the ordering was REF < LP < OPUS (Table II). The word errors for
REF, LP and OPUS were 1,084, 1,145 and 1,443 for Whisper large-v3 and 2,327, 2,937 and 3,836
for wav2vec2-base-960h. No condition produced an empty hypothesis.

## 4.3 Bandwidth component and codec-specific residual

| Contrast | Whisper micro | Whisper macro | wav2vec2 micro | wav2vec2 macro |
|---|---|---|---|---|
| LP − REF (bandwidth component) | +0.14 [+0.04, +0.25] | +0.35 [+0.17, +0.54] | +1.40 [+0.99, +1.92] | +1.90 [+1.39, +2.44] |
| OPUS − LP (codec-specific residual) | +0.69 [+0.46, +0.94] | +1.00 [+0.64, +1.39] | +2.07 [+1.68, +2.57] | +2.61 [+2.12, +3.13] |
| OPUS − REF (total) | +0.83 [+0.57, +1.10] | +1.35 [+0.93, +1.78] | +3.48 [+2.73, +4.45] | +4.50 [+3.65, +5.47] |
| SILK − LP | +0.02 [−0.04, +0.08] | −0.02 [−0.15, +0.11] | −0.09 [−0.20, +0.02] | −0.13 [−0.30, +0.05] |
| SILK − REF | +0.16 [+0.07, +0.26] | +0.33 [+0.19, +0.50] | +1.32 [+0.94, +1.78] | +1.77 [+1.29, +2.29] |
| OPUS − SILK | +0.67 [+0.46, +0.89] | +1.02 [+0.65, +1.40] | +2.16 [+1.73, +2.71] | +2.73 [+2.18, +3.33] |
| Bandwidth share of OPUS − REF | 0.17 [0.05, 0.29] | — | 0.40 [0.35, 0.45] | — |
| Bandwidth share of SILK − REF | 0.88 [0.39, 1.36] | — | 1.07 [0.98, 1.15] | — |

: Paired contrasts on the confirmation set (pp; micro = corpus WER difference, primary; macro = mean per-utterance difference, secondary), with 95 % speaker-bootstrap intervals. Bandwidth shares (LP − REF divided by OPUS − REF or SILK − REF) are sequential and path-dependent.

Removing SILK narrowband's bandwidth with the linear control increased corpus WER by
0.14 pp [0.04, 0.25] for Whisper large-v3 and 1.40 pp [0.99, 1.92] for wav2vec2-base-960h
(Table III). Relative to the control, Opus at 8 kbit/s increased WER by a further
0.69 pp [0.46, 0.94] and 2.07 pp [1.68, 2.57]. Along the sequential REF → LP → OPUS path,
bandwidth removal therefore accounted for a path-dependent share of 17 % [5, 29] (Whisper) and 40 % [35, 45] (wav2vec2) of the
total Opus penalty (Fig. 2); the Whisper share is imprecisely estimated. The macro estimates and CER point the same way; the CER residual
was +0.31 pp [+0.20, +0.44] (Whisper) and +1.09 pp [+0.87, +1.40] (wav2vec2). The pre-declared
rule returned GO for the Opus residual.

In absolute percentage points, wav2vec2-base-960h's residual was about three times, and its
bandwidth component five to ten times (depending on the error weighting; Section 4.12), those of
Whisper large-v3. Relative to each recogniser's own baseline, the residual was similar under WER,
+26.0 % and +30.6 % of the LP WER, but not under CER (+30.3 % and +45.6 %). The bandwidth
component still differed (+5.6 % and +26.2 % of the REF WER), and the total Opus penalty was
+33.1 % and +64.8 % of the REF WER. These ratios are post hoc and descriptive.

![Bandwidth component (LP − REF), codec-specific residual (OPUS − LP) and SILK residual (SILK − LP) on the confirmation set, with 95 % speaker-bootstrap intervals.](figures/fig_components.pdf){#fig:components}

## 4.4 Replication across subsets, recognisers and the pilot

The residual had the same sign in every scope examined (Supplementary Table S3). It was
+0.29 pp [+0.15, +0.46] (Whisper) and +0.94 pp [+0.72, +1.18] (wav2vec2) on test-clean and
+1.22 pp [+0.75, +1.77] and +3.60 pp [+2.78, +4.68] on test-other, and it was positive in both
recognisers on the pilot (Section 4.1). The bandwidth component was not detectable for Whisper
on test-clean alone (−0.03 pp [−0.13, +0.07]). It was positive on test-other
(+0.37 pp [+0.16, +0.59]), and in both subsets for wav2vec2.

## 4.5 High-rate SILK narrowband reference

SILK at 40 kbit/s showed no detectable pooled residual relative to the control:
+0.02 pp [−0.04, +0.08] (Whisper) and −0.09 pp [−0.20, +0.02] (wav2vec2). Across the two
recognisers, the intervals lie between −0.20 and +0.08 pp. No equivalence margin was
pre-declared, so this is not a claim of equivalence. In a secondary per-subset analysis, SILK
was slightly *below* the control for wav2vec2 on test-other: −0.24 pp [−0.50, −0.005].
OPUS − SILK was +0.67 pp [+0.46, +0.89] and +2.16 pp [+1.73, +2.71]. Because the two conditions
differ in bitrate and in the signal-type hint, this contrast is not a bitrate effect.

## 4.6 Error types

Substitutions made up most of the residual: 74 % for Whisper and 86 % for wav2vec2 (Supplementary Table S4).
Per 100 reference words, OPUS − LP added +0.51 substitutions [+0.34, +0.70], +0.10 deletions
and +0.08 insertions for Whisper, and +1.79 substitutions [+1.46, +2.21], +0.13 deletions and
+0.15 insertions for wav2vec2.

## 4.7 Signal descriptors

Compared with LP, the Opus 8 kbit/s signal differed mainly within the retained band (Supplementary Table S6).
Median LSD over 0–3 kHz was 6.14 dB, and median coherence over 0–3.5 kHz was 0.623; SILK at
40 kbit/s showed 1.37 dB and 0.993. The coherent bandwidths of LP, OPUS and SILK were
4,094, 4,000 and 4,094 Hz. The codec conditions and the control therefore share the same linear band
limitation to within about 100 Hz; OPUS's slightly lower edge reflects the bitrate-dependent
coding droop at the band edge described in Section 3.4. Both codec conditions carried 4–8 kHz
energy of comparable total power (OPUS −16.7 dB, SILK −15.8 dB relative to REF; 7.7 and 8.7 dB
above LP). This energy is the mirror image identified in Section 3.4. Its mirror coherence was
0.970 for SILK, a close copy of the original 3–4 kHz band, and 0.227 for OPUS, a copy of coded
content. The power-based retained bandwidth of the codec conditions (about 4.6 kHz) counts the
image; coherent bandwidth does not.

Per-utterance signal features explained little of which utterances were affected. Four of the
36 exploratory correlations had intervals excluding zero, all with $\lvert\rho\rvert \le 0.09$,
uncorrected for multiplicity. No mechanism is inferred from them.

## 4.8 Negative controls and decoder sensitivity

Opus at 64 kbit/s (NEG_CODEC), coded by CELT, left WER unchanged in both recognisers:
+0.002 pp [−0.046, +0.049] and +0.002 pp [−0.057, +0.065] (Supplementary Table S5). The 7 kHz low-pass
(NEG_LP) had intervals that excluded zero in opposite directions: −0.08 pp [−0.15, −0.004]
(Whisper) and +0.10 pp [+0.02, +0.19] (wav2vec2). Both were within the pre-declared ±0.5 pp
margin, so neither control capped the decision. We read the NEG_LP result as the resolution
limit of the pipeline, and do not interpret effects of order 0.1 pp.

**Decoder sensitivity.** As a post-confirmation decoder sensitivity, the same frozen 8 kbit/s Opus
bitstreams were decoded with libopus 1.4 instead of FFmpeg 6.1.1. The total Opus penalty remained
positive for both recognisers: +0.72 pp [+0.49, +0.97] for Whisper large-v3 and +3.56 pp
[+2.79, +4.54] for wav2vec2-base-960h. Relative to FFmpeg decoding, the libopus decoder reduced
Whisper WER by 0.11 pp [0.04, 0.17], whereas no clear decoder difference was established for
wav2vec2 (+0.09 pp [−0.04, +0.21]). This sensitivity tests the total penalty only; the bandwidth
decomposition remains defined for the FFmpeg chain. With FFmpeg decoding the totals were +0.83 and
+3.48 pp (Table III); checks and decoder diagnostics are in Supplementary Section S8.

## 4.9 Level-matched sensitivity analysis (Addition A)

*Post-confirmation sensitivity analysis on the confirmation utterances, decoded a second time;
not a second confirmatory test.*

All pre-recognition checks passed (Supplementary Section S4).

Matching the RMS level of the Opus signal to the control did not remove the residual in either
recogniser (Supplementary Table S7). The level-matched signal remained worse than LP by +0.70 pp [+0.47, +0.95]
(Whisper large-v3) and +2.09 pp [+1.71, +2.57] (wav2vec2-base-960h), 1.02 and 1.01 times the
confirmatory residual. Level matching itself changed WER by +0.012 pp [−0.007, +0.032] and
+0.018 pp [−0.028, +0.062]. Both intervals exclude level matching removing a quarter of the
confirmatory residual, so the pre-declared criterion was met for both recognisers. The same held in both test subsets, and the residual was still mostly
substitutions (Supplementary Section S4, Tables S7 and S8).

Level matching changed 42 of the 2,174 Whisper hypotheses and 188 of the 2,174 wav2vec2
hypotheses, without reducing either error count. The plan's expectation that wav2vec2-base-960h
would be insensitive to a scalar gain was corrected before the code freeze, so its result is
informative about level (Supplementary Section S6).

Decoded a second time, 3 of 4,348 Whisper hypotheses of the LP and OPUS audio differed from the
confirmatory run; the analysis uses the same-run LP and OPUS (Supplementary Section S4).

## 4.10 Bitrate sweep (Addition B)

*Fresh-utterance, not fresh-speaker, holdout: 1,665 unused test utterances of 70 of the
confirmation speakers.*

Every packet at every rate was SILK-only narrowband with 20 ms frames, and the median payload
bitrates were 2.3–8.0 % below nominal (Table IV). At 8 kbit/s the sweep's `signal=voice`
encoding produced Ogg files byte-identical to those of the OPUS settings (`signal=auto`) for
all 1,665 utterances, so SILK8 − LP repeats the confirmatory OPUS − LP contrast on new
utterances (validation details: Supplementary Section S5).

| Condition (addition B) | Median payload (kbit/s) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|---|
| LP, corpus WER (%) | — | 2.84 [2.49, 3.23] | 7.60 [6.66, 8.71] |
| SILK8 − LP | 7.36 | +0.55 [+0.37, +0.74] | +2.07 [+1.65, +2.55] |
| SILK12 − LP | 11.35 | +0.21 [+0.09, +0.33] | +0.75 [+0.55, +0.97] |
| SILK16 − LP | 15.43 | +0.13 [+0.04, +0.22] | +0.36 [+0.19, +0.54] |
| SILK24 − LP | 23.46 | +0.05 [−0.04, +0.14] | +0.05 [−0.11, +0.20] |
| SILK40 − LP | 38.96 | +0.03 [−0.05, +0.11] | −0.06 [−0.21, +0.09] |

: Addition B, the forced SILK narrowband bitrate sweep (fresh-utterance, not fresh-speaker, holdout; 1,665 utterances, 70 speakers, 31,601 reference words): residual beyond the control at each rate (pp, pooled, 95 % speaker-bootstrap intervals) and median payload bitrate.

Within forced SILK narrowband, the residual beyond the control decreased as the bitrate rose,
in both recognisers (Table IV, Fig. 3; trend and
thresholds in Supplementary Table S9). At 8 kbit/s it was +0.55 pp [+0.37, +0.74]
(Whisper large-v3) and +2.07 pp [+1.65, +2.55] (wav2vec2-base-960h), close to the confirmatory
+0.69 and +2.07 pp on different utterances; at 24 and 40 kbit/s no residual was detectable. The
slope on log2 bitrate was −0.206 pp per doubling [−0.267, −0.146] for Whisper and −0.854
[−1.074, −0.657] for wav2vec2. Both intervals lie below zero and reach below half the slope
implied by the confirmatory residuals, so the pre-declared criterion was met in both recognisers.
With the signal-type hint fixed, SILK8 − SILK40 was +0.52 pp [+0.36, +0.68] and +2.13 pp
[+1.65, +2.67]. The decline was concentrated at low rates, with the largest step between 8 and
12 kbit/s; the secondary slopes, the adjacent-rate contrasts and the corpus WERs are in
Supplementary Section S5 (Tables S9 and S11). In the per-subset analysis (Supplementary Table S12), the 8 kbit/s residual for Whisper was
concentrated in test-other (+0.95 pp [+0.65, +1.28]); on test-clean it was +0.11 pp [−0.04, +0.27],
and the test-clean slope interval only just excluded zero (−0.055 [−0.111, −0.001]). For
wav2vec2 both subsets showed a residual and a decline.

![Addition B: residual beyond the linear control (SILK $b$ − LP) of forced SILK narrowband at five bitrates on 1,665 fresh test utterances (a fresh-utterance, not fresh-speaker, holdout), with 95 % speaker-bootstrap intervals and the fitted log2-bitrate slope (dashed; drawn through the mean of the five estimates). Hollow grey markers: the confirmatory OPUS − LP (8 kbit/s, `signal=auto`) and SILK − LP (40 kbit/s) residuals on the confirmation utterances.](figures/fig_sweep.pdf){#fig:sweep}

The signal descriptors changed with the rate as well (Supplementary Table S10). In-band distortion relative to
LP fell: median LSD over 0–3 kHz went from 6.19 to 1.37 dB and coherence from 0.623 to 0.993.
The level deficit shrank: median RMS change relative to REF went from −0.68 to −0.12 dB and the
in-band gain from −1.83 to −0.08 dB. The 4–5 kHz image became a closer copy of the input, with
mirror coherence rising from 0.245 to 0.970 at similar total power. The sweep therefore shows
that the residual depends on the coding rate, but not which of these rate-dependent properties
produces it.

## 4.11 Forced-wideband counterfactual

*Practical bandwidth-allocation counterfactual on the 1,665 utterances of Addition B (a
fresh-utterance, not fresh-speaker, holdout); not a factorial interaction estimate.*

All pre-recognition checks passed, and NB8 reproduced Addition B's SILK8 files and hypotheses; the
median payload bitrates were 7.36 (NB8) and 7.76 kbit/s (WB8). At approximately 8 kbit/s, forced
wideband reduced the WER of wav2vec2-base-960h relative to forced narrowband by
0.98 pp [0.42, 1.57]. Whisper large-v3 showed no clear difference: +0.14 pp [−0.07, +0.36].
Wideband coding restored the energy above 4 kHz (pooled 4–8 kHz power relative to REF: +2.14 dB,
against −16.54 dB for NB8) but worsened in-band fidelity: median coherence with REF over
0–3.5 kHz fell from 0.623 to 0.559, and median LSD over 0–3 kHz rose from 6.19 to 6.77 dB.
Coding therefore changed with the band, so the comparison does not isolate a bandwidth × coding
interaction and does not change the decomposition. The result was recogniser-dependent and does
not show a general advantage of wideband coding at this rate (per-subset results and
descriptors: Supplementary Section S7, Tables S13 and S14).

## 4.12 Sensitivity of the residual, the total and the metric

| Pooled (confirmation set, pp) | Whisper large-v3 | wav2vec2-base-960h |
|---|---|---|
| LIN8 − REF (inclusive linear component) | +0.09 [−0.02, +0.19] | +1.16 [+0.81, +1.55] |
| OPUS − LIN8 (residual beyond the best-linear surrogate) | +0.74 [+0.51, +1.00] | +2.32 [+1.85, +2.97] |
| LIN8 − LP | −0.06 [−0.13, +0.01] | −0.25 [−0.47, −0.04] |
| Linear share, (LIN8 − REF)/(OPUS − REF) | 0.10 [−0.02, 0.22] | 0.33 [0.28, 0.39] |
| OPUS_VOIP8 − REF (total, VoIP application mode) | +0.70 [+0.48, +0.95] | +3.44 [+2.71, +4.37] |
| OPUS_VOIP8 − OPUS (application mode) | −0.12 [−0.25, +0.00] | −0.03 [−0.23, +0.15] |

: Post-confirmation sensitivity analyses on the confirmation set (pooled, pp, 95 % speaker-bootstrap intervals): inclusive best-linear attribution of the 8 kbit/s Opus output (LIN8; Section 3.11) and a change of the encoder application mode alone (OPUS_VOIP8). The linear share is descriptive and is not a bandwidth share; details in Supplementary Sections S9–S11.

The best-linear surrogate kept the chain's lower gain and steeper in-band roll-off (median gain
−2.22 dB over 0.5–2 kHz and a further −7.30 dB at 3.5 kHz, against 0.00 and −2.16 dB for the
control; Supplementary Table S20), yet it was no more harmful than the control (Table V):
LIN8 − LP was −0.06 pp [−0.13, +0.01] for Whisper large-v3 and −0.25 pp [−0.47, −0.04] for
wav2vec2-base-960h. The residual beyond it was +0.74 pp [+0.51, +1.00] and +2.32 pp [+1.85, +2.97]
and exceeded the linear component in both recognisers and both test subsets, meeting the
pre-declared criterion. The linear share was 0.10 (Whisper) and 0.33 (wav2vec2), against 0.17 and
0.40 along the sequential, path-dependent REF → LP → OPUS path: the exact split depends on how
linear loss is defined, but the residual did not shrink.

With the VoIP application mode the total penalty remained positive: OPUS_VOIP8 − REF was
+0.70 pp [+0.48, +0.95] for Whisper large-v3 and +3.44 pp [+2.71, +4.37] for wav2vec2-base-960h.
No clear application difference was established: OPUS_VOIP8 − OPUS was −0.12 pp [−0.25, +0.00]
and −0.03 pp [−0.23, +0.15]. For Whisper the interval reaches zero and two secondary cells (CER;
test-other) excluded it, so a small reduction under the VoIP mode cannot be ruled out; no
equivalence is claimed.

Recomputed without new recognition, the residual and its excess over the bandwidth component
were positive for both recognisers under corpus, mean per-utterance, equal-speaker and character
weighting, and under corpus WER in both test subsets. The shares were less stable than the contrasts: the
Whisper share ranged from 0.17 (corpus WER) to 0.28 (CER), with an interval of [0.05, 0.29] under
corpus WER, and the wav2vec2 share from 0.35 to 0.42. Two secondary cells left the ordering
unresolved (Supplementary Section S11).

# 5. Discussion

**Bandwidth removal reproduces a minority of the low-rate Opus penalty.** In both recognisers, removing
SILK narrowband's bandwidth with a validated linear control reproduced only part of the WER
increase caused by Opus at 8 kbit/s: a small share for Whisper large-v3 and 40 % for
wav2vec2-base-960h, both path-dependent shares along the sequential REF → LP → OPUS path. The residual beyond the control had the
same direction in both recognisers, in both test subsets and in an independent pilot. It did
not depend on how linear loss is defined or on how errors are weighted: beyond a per-utterance
best-linear projection of the actual 8 kbit/s output it was at least as large, and its excess
over the bandwidth component held under four error weightings (Section 4.12). The
attribution of the 8 kbit/s penalty to narrowband operation [@khare2020opus] is therefore
incomplete for these recognisers and data.

**Relation to earlier decompositions.** Comparisons across studies are directional only,
because recognisers, languages, training regimes and metrics differ. Our result has the same
direction as that for AMR-NB at 12.2 kbit/s [@bauer2010wtimit] and for MP3 at 12 kbit/s
[@borsky2015mp3], where the codec effect exceeded the bandwidth effect. It differs from the
result for GSM full rate at 13 kbit/s, where band limitation dominated [@besacier2001effect;
@heymans2022multistyle]. Our high-rate reference, SILK narrowband at 40 kbit/s, showed no
detectable pooled residual, which places it on the GSM side of that contrast. Together these
results are consistent with the residual depending on the codec and its coding rate rather
than on narrowband operation as such. Across codecs this remains a comparison between studies.
Within SILK narrowband, with the signal-type hint and the decode path fixed, the residual fell
with the coding rate on fresh utterances and was not detectable at 24 and 40 kbit/s (Section 4.10). The ordering of the bandwidth component, large for wav2vec2 and small for Whisper,
agrees with the robustness ranking of Speech Robust Bench [@shah2025srb]. With matched
training, removing content above 4 kHz from LibriSpeech costs little
[@likhomanenko2021rethinking].

**What the residual contains.** The signal evidence is consistent with low-rate in-band coding
distortion. The Opus signal differed from the control mainly within the retained 0–3 kHz band,
where the SILK reference did not. SILK's excitation bits fall rapidly as the rate drops below
about 8 kbit/s [@skoglund2020opus], and low-rate SILK coding increased WER even when bandwidth
was, by implication of the evaluation set-up, preserved [@buethe2024nolace]. The residual also
contains the 4–5 kHz image, a median level difference of about −0.6 dB relative to LP, and a
1–2 sample lag. Matching the RMS level of the Opus signal to the control did not remove the
residual in either recogniser (Section 4.9), so the broadband level difference does not account
for it. Nor does the 8 kbit/s chain's own linear response: reproduced per utterance, its lower
gain and steeper in-band roll-off left WER no higher than the control (Section 4.12). SILK carries image energy of comparable power and the same lag and decode path,
yet shows no pooled residual. This argues against the image and the decode path explaining the
pooled residual. It does not exclude that an image of low-rate *coded* content affects
recognition differently from an image of nearly intact speech. NEG_CODEC shows that this
container, decoder and resampling chain alone leave WER unchanged; being CELT-coded, it does
not exercise the SILK upsampling step [@ffmpeg611]. Within SILK narrowband, the residual
decreased with bitrate in both recognisers (Section 4.10). This supports, but does not isolate,
the low-rate in-band coding distortion interpretation: in-band distortion, level and image
fidelity all changed with the rate (Supplementary Table S10). No condition manipulated in-band distortion while
holding everything else fixed, so the mechanism is not established.

**Absolute and relative sensitivity.** In absolute terms, wav2vec2-base-960h lost more accuracy
than Whisper large-v3 to both components. Relative to each recogniser's own baseline, the
residual was similar under WER (+26 % and +31 % of the LP WER), though not under CER, whereas the
bandwidth component still differed markedly (+6 % and +26 % of the REF WER). The two recognisers may therefore differ
more in how they use content above 4 kHz than in how they respond to the codec-specific
degradation beyond the control. This interpretation rests on post hoc ratios.

**Practical reading.** For pipelines that transcribe low-rate Opus with pretrained recognisers,
restoring the missing band alone would not target the residual beyond the control, which was
the larger component in both recognisers. Decoder-side enhancement of low-rate SILK, which
currently targets wideband operation [@buethe2024nolace], and higher coding rates are
candidates for the larger component, to the extent that it is coding distortion, which the
evidence supports but does not establish. The bitrate sweep bears on the second: at 24 kbit/s and above, forced SILK
narrowband left no detectable residual beyond the control on these data. Forcing wideband at
the same nominal 8 kbit/s lowered WER for wav2vec2-base-960h only (Section 4.11). The total 8 kbit/s Opus penalty persisted under the
libopus reference decoder for both recognisers; its magnitude was lower for Whisper, while no
clear decoder difference was established for wav2vec2, and the bandwidth decomposition itself
remains defined for the FFmpeg decoder chain (Section 4.8). The total penalty also persisted when the encoder used the VoIP application mode, without a clear difference from the audio mode (Section 4.12). Restoring the band without changing
the coding, as bandwidth extension would, and decoder-side enhancement were not tested.

# 6. Limitations

**What the residual contains.** The residual is a bundle, not a mechanism: it contains in-band
coding distortion, the mirror image, a small level difference, a 1–2 sample lag and the codec
decode path, and no condition isolates in-band distortion. Level matching was broadband and
post-confirmation, and the bitrate sweep changed in-band distortion, level and image fidelity
together, so both support but do not isolate the in-band interpretation.

**The decomposition.** The decomposition is sequential, so the residual includes any
interaction between band limitation and coding, and the bandwidth share is path-dependent, not
an interaction-free attribution. The split also depends on how linear loss is defined: under a
per-utterance best-linear attribution of the actual codec output, the linear share was 0.10
(Whisper) and 0.33 (wav2vec2) instead of 0.17 and 0.40 (Section 4.12). Estimating the
interaction would need a factorial design. A forced-wideband 8 kbit/s counterfactual was tested, but changing bandwidth
allocation also changes the coding-distortion budget, so the comparison does not identify a
factorial interaction between bandwidth loss and coding distortion. The
control was fitted to a reference measured at 40 kbit/s that had not fully converged: near the
band edge the reference still rose by up to 0.83 dB between 32 and 40 kbit/s. The control was
validated under a corrected criterion after the first criterion failed; the failed validation
is retained and reported.

**Implementations.** One encoder (libopus 1.4) was used, and Opus leaves decoder resampling to the
implementation [@rfc6716]. The primary decomposition is defined for FFmpeg 6.1.1 decoding. A
post-confirmation sensitivity using the libopus 1.4 reference decoder showed that the total
8 kbit/s penalty persisted for both recognisers, although its magnitude was lower for Whisper.
Because the decoder-matched bandwidth control failed held-out validation before ASR, decoder
invariance of the bandwidth share or codec-specific residual was not established. The automatic choice of
bandwidth depends on the libopus version: 8 kbit/s selects narrowband in every version we
inspected, but the wideband threshold has moved over time. The encoder used
`application=audio`, retained to reproduce the frozen codec baseline of the preliminary
analysis, and the decomposition is defined for it. A post-confirmation sensitivity with
`OPUS_APPLICATION_VOIP` alone showed that the total penalty persisted, without a clear
difference from the audio mode (not an equivalence result); FEC, DTX, packet loss and other
deployment settings were not tested.

**The SILK reference.** SILK differs from OPUS in the signal-type hint as well as the bitrate.
Its absence of a residual is a pooled, non-equivalence result, with a secondary exception for
wav2vec2 on test-other. The bitrate sweep adds five rates with the hint fixed, but on other
utterances. It is a fresh-utterance, not fresh-speaker, holdout: its speakers are the
confirmation speakers. REF was not recognised in it, so it gives no bandwidth component or
bandwidth share for its utterances.

**Recognisers, data and scoring.** Two recognisers were tested, both without a language model
or beam search; Whisper used greedy decoding for computational reasons decided before
evaluation. wav2vec2-base-960h was fine-tuned on LibriSpeech training data (evaluation used
only held-out subsets), and Whisper's training data are undisclosed. The data come from one
corpus of read English audiobooks; conversational, noisy, far-field, multilingual and
real-network conditions were not tested. LibriSpeech derives from LibriVox recordings, which
are MP3-compressed [@panayotov2015librispeech, Sec. 5], so REF is lossless relative to this
study's manipulations but is not guaranteed to represent never-lossy-coded source speech; the
paired within-utterance contrasts remain valid, but generalisation to pristine-source
recordings is limited. The confirmation speakers are those of the
preliminary analysis, although the utterances are new. One text normalisation policy was used.
Greedy float16 decoding of Whisper was not exactly reproducible when batch composition changed:
3 of 4,348 hypotheses differed when the confirmation audio was decoded again (Section 4.9).

**Statistics and reporting.** Per-subset results and the path-dependent bandwidth shares are
secondary, and
relative percentages are post hoc. The shares also depend on the error weighting (the Whisper
share ranged from 0.17 to 0.28), whereas the ordering of the two components did not
(Section 4.12). The negative controls imply a resolution of about 0.1 pp.
The prospective specification is internal (sealed files and version-control commits); it was
not lodged in a public registry. STOI, PESQ and human intelligibility were not measured.

# 7. Conclusion

We decomposed the ASR penalty of Opus at 8 kbit/s into a bandwidth component and a
codec-specific residual, using a linear low-pass control fitted to SILK narrowband's measured
high-rate transfer function and validated on held-out speakers. In a prospectively specified,
version-sealed paired design,
bandwidth removal accounted for a minority of the total penalty: a small share for Whisper
large-v3 and 40 % for wav2vec2-base-960h, both path-dependent shares along the sequential
REF → LP → OPUS path. The residual, 0.69 and 2.07 pp, was present in both recognisers, both test
subsets and the pilot. Post-confirmation sensitivity analyses did not remove it: it remained
after matching the RMS level of the Opus signal to the control and, at 0.74 and 2.32 pp, beyond a
per-utterance best-linear projection of the actual 8 kbit/s output, and its excess over the
bandwidth component held under four error weightings. In a bitrate sweep on fresh utterances of the
same speakers, specified and sealed before decoding, the residual of forced SILK narrowband decreased with bitrate
and was not detectable at 24 kbit/s and above. These results support, but do not isolate, the
interpretation of the residual as low-rate in-band coding distortion rather than band
limitation alone. Forcing wideband at the same nominal 8 kbit/s lowered WER for
wav2vec2-base-960h only; this practical result does not estimate a bandwidth × coding interaction. The total penalty persisted with the libopus reference decoder and with the VoIP application mode. Future work includes a manipulation that changes in-band coding distortion with level
and image held fixed; a fresh-speaker holdout on another corpus, with a recogniser of another
family such as a transducer; a decoder-matched decomposition, which needs a bandwidth control
validated for that decoder; and a factorial design that estimates the interaction between
bandwidth and coding.

# Reproducibility statement

Before any pilot or confirmation audio was decoded, the specification of Section 3.1 was sealed with SHA-256 hashes and committed to version control. The
analysis code was sealed again after the pilot kill test and before the confirmation run. The
confirmation audio was decoded once, and the decision record was sealed. In earlier stages, a
reproduction of the preliminary pipeline passed 250/250 checks and the codec control passed 7/7
validation gates; the low-pass control's original failure, the corrected criterion and its
independent confirmation are all retained. Every later analysis (Sections 3.9, 3.10 and 3.11, and the decoder
sensitivity of Section 4.8) was specified in its own sealed plan before any of its audio was
encoded, had its code frozen after a calibration step, was decoded once and has a sealed decision
record; one amendment was sealed before a freeze. Two additional attribution sensitivities were
prospectively gated but stopped before ASR because their signal-domain controls failed held-out
validation. Supplementary material gives the tables and figures moved out of this paper
(Tables S1–S24) and the checks, rule thresholds, outcomes, amendments and
deviations of the later analyses.
Code, sealed selections, per-utterance outputs and all
intermediate reports are in the project repository (link withheld for review).
LibriSpeech, the recogniser checkpoints (pinned revisions), libopus 1.4 and FFmpeg 6.1.1 are
public.

# References

::: {#refs}
:::
