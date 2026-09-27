# Literature note: reviewer-concern sensitivity analyses R1–R3

Written 2026-09-27, before the R1–R3 plan was sealed, and revised the same day with plan
revision 2: R1 now uses a decoder-matched control, and R2 is described as a coherent-linear
surrogate. Nothing was committed in between. Its SHA-256 is recorded in `reviewer_spec.json`,
so later changes need a new, dated note. The note extends the
literature-positioning audit of 2026-09-26 (`manuscript/literature_matrix.md`), in which every
record was verified on a primary or authoritative page. It cites audit records by their keys.
Statements marked *[inference]* are our reading of the cited statements; everything else is
stated by the source. The note reports what the searches found and did not find. It makes no
claim that a study does not exist.

## 1. Decoder-dependent Opus output is established technically

- RFC 6716 §4.2.9 (audit record `rfc6716`, errata checked): "The resampler itself is
  non-normative, and a decoder can use any method it wants to perform the resampling." The
  resampler *delay* is normative (Table 54).
- RFC 8251 updated the reference decoder and replaced the conformance test vectors. The Opus
  test-vector page (https://opus-codec.org/testvectors/, read 2026-09-27) says the RFC 8251
  vectors "allow some decoder improvements while maintaining full compatibility". It also says
  conformance is tested separately at each output sampling rate (8, 12, 16, 24 and 48 kHz),
  using `opus_demo` and `opus_compare`.
- FFmpeg n6.1.1 (audit record `ffmpeg-6.1.1-opusdec`, source read):
  - The native Opus decoder, FFmpeg's default, always outputs 48 kHz.
  - It upsamples SILK output with libswresample (`filter_size` 16, Kaiser β 9).
  - FFmpeg's own tests accept a non-zero deviation from the RFC 8251 reference outputs for
    SILK vectors.
- libopus resamples SILK output with its own resampler (`silk/resampler.c`; audit record
  `libopus-1.4`).
- *[inference]* Two conforming decoders can therefore return different waveforms for the same
  SILK packets. The differences are most likely near the 4 kHz band edge and in the 4–5 kHz
  image. That such differences can occur is established. The literature we found does not
  establish whether they change ASR results. The manuscript already defines its results for
  "libopus 1.4 encoder + FFmpeg 6.1.1 native decoder" and lists decoding with the reference
  decoder as future work. **→ R1.**

## 2. Forced bandwidth is part of the Opus API and has precedent in codec-quality studies

- **API.** In libopus 1.4 `include/opus_defines.h`
  (https://raw.githubusercontent.com/xiph/opus/v1.4/include/opus_defines.h, read 2026-09-27),
  `OPUS_SET_BANDWIDTH` "Sets the encoder's bandpass to a specific value. This prevents the
  encoder from automatically selecting the bandpass based on the available bitrate."
  - Its values include `OPUS_BANDWIDTH_NARROWBAND` (4 kHz passband) and
    `OPUS_BANDWIDTH_WIDEBAND` (8 kHz passband).
  - The header recommends `OPUS_SET_MAX_BANDWIDTH` for normal use, because it "still gives the
    encoder the freedom to reduce the bandpass when the bitrate becomes too low".
- **Source** (audit record `libopus-1.4`):
  - `OPUS_SET_BANDWIDTH` overrides the automatic selection (`src/opus_encoder.c` L1508–1512).
  - An input sampling rate of 16 kHz or less caps the band at WB (L1520–1529).
  - In libopus 1.3–1.6.1 the automatic switch from narrowband to wideband is at 9 kbit/s, so
    8 kbit/s selects narrowband in every version checked.
  - Every packet signals its coded bandwidth in the TOC byte (RFC 6716 §3.1), so a forced
    bandwidth can be checked packet by packet.
- **Precedent in codec-quality studies:**
  - IETF listening-test summary (draft-ietf-codec-results-03, §2.4, Universität Tübingen
    tests; https://www.ietf.org/archive/id/draft-ietf-codec-results-03.txt, read 2026-09-27).
    Opus conditions were encoded with the reference tool and an explicit bandwidth option:
    `test_opus 0 48000 2 12000 -cbr -framesize 60 -bandwidth NB` and
    `test_opus 0 48000 2 16000 -cbr -framesize 20 -bandwidth WB`.
  - Skoglund & Valin, Interspeech 2020 (audit record `skoglund2020opus`; full text read
    2026-09-27). A MUSHRA test of Opus "coded at 6 kb/s (average rate, since SILK is variable
    rate) in wideband mode". A footnote gives 9 kb/s as "the lowest bit rate for which the
    encoder defaults to wideband if signal bandwidth is not specifically set".
    *[inference]* The bandwidth of the 6 kb/s wideband condition was therefore set
    explicitly.
  - Büthe et al., NoLACE, ICASSP 2024 (audit record `buethe2024nolace`). Its training data
    came from "a patched version of libopus that restricts Opus to linear-predictive mode and
    wideband encoding". LACE (WASPAA 2023) enhances wideband SILK only, at 6–12 kb/s.
  - Opus 1.3 release notes (J.-M. Valin, 2018; https://jmvalin.ca/opus/opus-1.3/, read
    2026-09-27). libopus moved its narrowband-to-wideband switch to 9 kb/s because "an
    (unpublished) experiment by folks at Google" showed that "most people actually prefer
    wideband to narrowband even at 9 kb/s". This is a perceptual comparison of bandwidth
    allocation at one low rate, and it is unpublished, so it is context only.
- None of these is an ASR study. **→ R3** compares forced NB with forced WB at 8 kbit/s and
  checks the realised bandwidth packet by packet.

## 3. Opus-ASR studies in the audit report total effects at given bitrates

The audit found these ASR studies with Opus conditions. Full records are in
`manuscript/literature_matrix.md`.

| Audit key | Opus manipulation | What is reported |
|---|---|---|
| khare2020opus (preprint) | CBR 8, 16, 32 and 128 kbit/s per channel | WER per rate. The 8 kbit/s loss (202.1 % relative) is attributed to narrowband operation, without a control. |
| drude2021opus (Interspeech 2021) | 16–128 kbit/s per channel; mode forced to SILK or CELT (not bandwidth) | WER per rate and mode. Bandwidth is neither controlled nor reported. |
| buethe2024nolace (ICASSP 2024) | 6, 9, 12 and 20 kb/s; wideband SILK by implication; with and without enhancement | WER per rate. |
| jassim2020vocoders (QoMEX 2020) | 6 kb/s (NB SILK) against 9 kb/s (WB SILK), default settings | WER per rate. Bandwidth and rate are confounded. |
| narayanan2018domain (SLT 2018) | Opus 24 kbit/s test condition | WER with and without codec training. |
| basu2026factors (preprint) | GSM, and Opus at an unstated rate; a generic 3.4 kHz low-pass | WER per condition. The band limitation is generic, not matched to the codec. |
| vu2019codec (APSIPA 2019) | Opus/SILK at 4.5–32 kbit/s at 8 kHz, among 27 codecs | Pooled effects of codec augmentation. |
| jacobellis2024mpq, bai2026semdac, wang2025stcts, jones2022microphone, prescott2026attack, zaporowski2026medical | Opus at one low rate (4.5–6 kbit/s) or at an unstated rate, used as a condition, baseline or purification step | WER or accuracy at that rate. prescott2026attack reports no Opus penalty on clean speech. |

None of these studies does any of the following:

- vary the decoder for identical packets;
- build a linear surrogate or bandwidth control from the codec's own coherent response at the
  operating rate;
- compare forced NB with forced WB at one nominal rate.

The nearest methods are partial:

- `tseng2025probing` measured the frequency responses of neural codecs with sine sweeps and
  related them qualitatively to Whisper WER. It built no control.
- `borsky2015mp3` matched a low-pass to the cutoff of each MP3 bitrate, not to a measured
  response.

The audit's category M3 is "a control fitted to the codec's measured transfer function and
validated on held-out data". The only entry in it is this project's own design.

## 4. No exact prior ASR study matching R1–R3 was located in the current search

- **Searches:** the audit's six category searches (2026-09-26) and ten targeted web searches
  on 2026-09-27 (listed below). The 2026-09-27 searches also re-found the audit's closest
  records.
- **Not located:**
  - an ASR study that decodes identical Opus packets with more than one decoder implementation
    (R1);
  - an ASR study that builds a linear surrogate, or a bandwidth control, from a codec's
    effective coherent response at the operating bitrate (R2);
  - an ASR study that compares forced-narrowband with forced-wideband Opus at the same nominal
    bitrate (R3).
- **Closest found:**
  - jassim2020vocoders: NB at 6 kb/s against WB at 9 kb/s, so rate and bandwidth are
    confounded;
  - drude2021opus: forced mode, not bandwidth;
  - buethe2024nolace: wideband only.
- **New hits:** one new hit (arXiv:2608.07378) was checked and set aside. It is not an
  Opus-ASR study.
- **Limits:** general web search plus the audit's sources; no search of paywalled full text;
  English only. The paper may say that we did not find such a study. It may not say that none
  exists.

Queries of 2026-09-27:

1. `RFC 6716 section 6 conformance opus_compare decoder output "sampling rate" test vectors not bit-exact`
2. `FFmpeg native Opus decoder versus libopus decoder speech recognition word error rate`
3. `Opus forced wideband versus narrowband same bitrate 8 kbps speech recognition WER`
4. `speech recognition codec "transfer function" matched low-pass control effective bandwidth Opus SILK residual coding distortion`
5. `"Opus" "decoder" implementation differences ASR robustness libopus reference decoder evaluation Whisper wav2vec2`
6. `Opus bandwidth setting OPUS_SET_BANDWIDTH wideband narrowband low bitrate speech recognition experiment`
7. `SILK wideband versus narrowband at the same bit rate automatic speech recognition Opus 2025 2026`
8. `non-bit-exact Opus decoders FFmpeg opus decoder SILK resampler deviation test vectors`
9. `site:arxiv.org Opus codec narrowband wideband speech recognition word error rate low bitrate`
10. `site:isca-archive.org Opus codec speech recognition bandwidth narrowband SILK`
