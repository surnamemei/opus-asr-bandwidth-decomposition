# Paper outline (draft 2, 2026-09-26; positioning frozen)

Every number comes from `results_paper/stage3_asr/` (frozen outputs) and
`results_paper/stage3_asr/01b_interpretation_note_2026-09-26.md` (approved wording).
Positioning and literature: `novelty_boundary.md`, `literature_matrix.md` and
`related_work_notes.md` (audit completed 2026-09-26).
Companion files: `claims_and_evidence.md`, `methods_notes.md`, `results_notes.md`,
`limitations.md`.

## Working title (no priority or causal claims)

- A. *How much of the ASR penalty of low-rate Opus is bandwidth loss? A decomposition with a
  validated bandwidth control*
- B. *Bandwidth removal explains only part of the ASR degradation of 8 kbps Opus*

## Research question (frozen scope)

How much of the ASR penalty of low-rate Opus is explained by bandwidth loss, and how much
remains as a codec-specific residual beyond a validated linear bandwidth control?

In operational terms: SILK-NB's linear band limitation is reproduced by an independently
validated low-pass (LP) control. We then test whether 8 kbps Opus still carries an ASR
penalty beyond the control, and whether that residual appears in two structurally different
pretrained recognisers.

**Scope (decided).** The paper covers the decomposition only.
- The *interaction* of bandwidth and coding distortion is future work: the Stage 2A bandwidth-by-bitrate cells were validated but never decoded by ASR.
- So is *propagation through the ASR encoder*: no representation analysis was run on the Stage 3 conditions.

## Positioning (frozen 2026-09-26): **NOVELTY_NARROW_BUT_DEFENSIBLE**

Source: `novelty_boundary.md` §1–3. The contribution is a controlled measurement for a
specific, widely deployed codec operating point. It is not a new concept, and no priority is
claimed.

| Component | Status after the audit | Nearest prior work (keys in `literature_matrix.md`) | How the paper treats it |
|---|---|---|---|
| General bandwidth-vs-codec (or vs-channel) decomposition | **Not novel** | moreno1994sources, besacier2001effect, bauer2010wtimit, borsky2015mp3, heymans2022multistyle; partial: moller2002analytic, fernandezgallardo2017predicting, basu2026factors (preprint) | Cited in the Introduction as the origin of the design. The paper says it *follows* this logic |
| Cutoff-matched bandwidth control | **Already exists** | borsky2015mp3 (per-bitrate cutoff read from spectrograms); nominal controls elsewhere | Cited as the nearest precedent. No priority claimed for having a matched control |
| Low-rate Opus/SILK-NB decomposition with a control fitted to the measured response and validated on held-out speakers | **Not found in the audited literature** (as of 2026-09-26; search limits in `novelty_boundary.md` §9) | Located Opus–ASR studies report total penalties only (khare2020opus, jassim2020vocoders, jacobellis2024mpq, bai2026semdac, buethe2024nolace). Nearest controls: borsky2015mp3 (cutoff only), tseng2025probing (responses measured, no control) | Described factually ("the Opus–ASR studies we located report the total penalty"), never as "first" |
| Paired confirmation in two pretrained recognisers with speaker-bootstrap intervals (pilot + one pre-registered confirmatory run, negative controls) | **Part of the current contribution; no priority claimed** | Earlier decompositions used HMM-era, mostly retrained systems without intervals. basu2026factors has two current models but no decomposition or statistics | Reported as design properties of this study |

**Contribution statement (use verbatim or shorten; from `novelty_boundary.md` §6):**

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

## Evidence hierarchy

| Tier | Content | Main evidence |
|---|---|---|
| Primary | REF → LP (bandwidth) and LP → OPUS 8 kbps (codec-specific residual) | Confirmation set, micro WER, speaker bootstrap |
| Replication | Same residual direction in Whisper large-v3 and wav2vec2-base-960h, in both test subsets, and in the pilot | Confirmation and pilot |
| Supporting | High-rate SILK-NB shows no detectable pooled residual relative to LP. It is a supporting reference, not a bitrate-only contrast | Confirmation, pooled |
| Interpretation | Signal evidence is consistent with low-rate in-band coding distortion; the mechanism is not established | Signal descriptors (descriptive) |

## Abstract (draft, ~190 words)

Low-bitrate speech codecs degrade automatic speech recognition (ASR). Narrowband codec modes
remove bandwidth and add coding distortion at the same time, and earlier studies of GSM, AMR
and MP3 reached different conclusions about the share due to bandwidth. We measure it for Opus at
8 kbps, which libopus encodes in SILK narrowband mode. The bandwidth control is a zero-phase
linear low-pass filter fitted to SILK narrowband's measured linear transfer function; it was
calibrated on LibriSpeech dev-clean and validated on unseen speakers. The design was
pre-registered and paired: a pilot, then a single confirmatory run on 2,174 LibriSpeech test
utterances from 73 speakers. Bandwidth removal alone increased corpus WER by 0.14 pp
(Whisper large-v3) and 1.40 pp (wav2vec2-base-960h). Opus at 8 kbps increased WER by a
further 0.69 pp and 2.07 pp relative to the control, with 95 % speaker-bootstrap intervals
excluding zero. Bandwidth removal therefore accounted for 17 % and 40 % of the total Opus
penalty. High-rate SILK narrowband showed no detectable pooled residual. The residual
consisted mainly of substitutions. It is consistent with low-rate in-band coding distortion,
where the Opus signal differed most from the control; the causal mechanism was not tested.

## Sections

1. **Introduction.**
   - Codec degradation of ASR is well documented (cite).
   - Earlier work separated band limitation from coding for telephone channels, GSM, AMR and MP3, with codec-dependent answers (moreno1994sources; besacier2001effect; bauer2010wtimit; borsky2015mp3; heymans2022multistyle). The answer for low-rate Opus therefore has to be measured.
   - Motivation:
     - the prior study's wav2vec2 onset at the 12 → 8 kbps switch from SILK-WB to SILK-NB (do not cite the unpublished course report in a double-blind submission);
     - khare2020opus attributes the 8 kbps collapse to narrowband operation without a control;
     - Opus is mandatory in WebRTC (rfc7874).
   - Contributions: the three conservative bullets in `novelty_boundary.md` §6.
2. **Related work** (draft prose in `related_work_notes.md` §2):
   - 2.1 Speech codecs and ASR, from narrowband coders to Opus.
   - 2.2 Band limitation and narrowband ASR, including shah2025srb for our two model families.
   - 2.3 Separating band limitation from coding distortion: the closest work, with the four-way positioning table above in prose.
   - 2.4 Controlled signal interventions (sehr2010reverberation; NTT projection analyses, which do not charge linear filtering).
   - 2.5 Positioning paragraph.
   - Verified keys are listed in `related_work_notes.md` §8. Full citations are in `literature_matrix.md`.
3. **Methods.** See `methods_notes.md`.
   - 3.1 Data and speaker-disjoint splits.
   - 3.2 Conditions and codec pipeline (Table 1). Name **libopus 1.4** and **FFmpeg 6.1.1**. 8 kbps is SILK-NB because it is below libopus's 9 kbps wideband threshold. RFC 6716 lists 8–12 kbps as the NB "sweet spot", so do not describe 12 kbps as the RFC's wideband region.
   - 3.3 Bandwidth control: design, the imaging finding, and the validation history (including the retained v1 FAIL and the corrected Gate 5). Cite borsky2015mp3 as the nearest precedent for a matched control.
   - 3.4 Recognisers, decoding and normalisation.
   - 3.5 Paired decomposition, speaker bootstrap and pre-declared decision rules. **Add:** the decomposition is sequential (REF → LP → OPUS). The residual includes any bandwidth × coding interaction, and the bandwidth share is a share along this path (borsky2015mp3 reports non-linear combination).
   - 3.6 Signal descriptors (descriptive only).
   - **Residual definition:** relative to the libopus 1.4 encoder plus FFmpeg 6.1.1's native decoder. Decoder resampling is non-normative (RFC 6716 §4.2.9).
4. **Results.** See `results_notes.md`.
   - 4.1 Pilot (kill test: PROCEED).
   - 4.2 Confirmation: WER by condition (Fig. 1, Table 2).
   - 4.3 Bandwidth component vs codec-specific residual, absolute and relative (Fig. 2, Table 3).
   - 4.4 Replication across recognisers, subsets and the pilot (Figs. 3–4).
   - 4.5 Supporting reference: high-rate SILK-NB, with its caveats.
   - 4.6 Error types (supplementary figure).
   - 4.7 Signal descriptors (Table 4).
   - 4.8 Negative controls.
5. **Discussion.** Hedges are in `novelty_boundary.md` §5.
   - The residual is consistent with in-band coding distortion. The 4–5 kHz image of comparable power in SILK is not accompanied by a pooled residual.
   - Prior evidence, directional only:
     - residual > bandwidth for AMR-NB and MP3 (bauer2010wtimit, borsky2015mp3);
     - bandwidth-dominated for GSM FR (besacier2001effect, heymans2022multistyle);
     - our SILK-40k reference sits on the GSM-FR side, consistent with a rate dependence that no study tests directly.
   - Recogniser ordering of the bandwidth component matches shah2025srb. The residual is consistent with buethe2024nolace and skoglund2020opus.
   - Absolute vs relative sensitivity of the two recognisers.
   - The small level difference.
   - Decoder dependence of the image (FFmpeg interpolator; SILK-40k shares the path).
   - What the design cannot separate.
6. **Limitations.** See `limitations.md`. Add from the audit:
   - path-dependence of the decomposition (see 3.5);
   - decoder-implementation dependence (RFC 6716 §4.2.9);
   - libopus version dependence of bandwidth selection.
7. **Conclusion.** Bandwidth removal explains only part of the 8 kbps Opus penalty in both recognisers. Future work:
   - a pre-registered SILK-NB bitrate sweep holding the signal hint fixed;
   - a level-matched check;
   - a reference-decoder (libopus) re-decode;
   - a factorial design with forced-WB Opus at 8 kbps to estimate the interaction.

## Figures and tables

| Item | Content | Source |
|---|---|---|
| Fig. 1 | Corpus WER by condition, both recognisers | `fig01_wer_by_condition.png` |
| Fig. 2 | Bandwidth component vs codec residual | `fig02_bandwidth_vs_codec_residual.png` |
| Fig. 3 | Decomposition forest plot, pilot vs confirmation | `fig04_bootstrap_ci.png` |
| Fig. 4 | Cross-recogniser consistency | `fig05_asr_model_comparison.png` |
| Fig. 5 (or supp.) | Paired per-utterance changes | `fig03_paired_utterance_differences.png` |
| Supp. | Error-type composition | `fig06_error_type_breakdown.png` |
| Supp. | Exploratory residual vs distortion (labelled exploratory) | `fig07_residual_vs_signal_distortion.png` |
| Fig. (to make) | LP \|H1\| vs SILK-NB reference vs Opus 8 kbps (Stage 2B validation) | from `lowpass_validation/transfer_curves.csv` and `lowpass_confirmation/transfer_curves.csv`; presentation only |
| Table 1 | Conditions and exact encoder settings, including `signal` | `stage3_spec.json` |
| Table 2 | Corpus WER with 95 % CIs | `07_paired_bootstrap.csv` |
| Table 3 | Components, absolute and relative, and bandwidth shares | `07_paired_bootstrap.csv`, note §1 |
| Table 4 | Signal descriptors vs REF and vs LP | `09_signal_summary.csv`, `09_signal_metrics_pooled.csv` |
| Supp. tables | Per-subset, macro, CER, error types, negative controls, pilot | `07_paired_bootstrap.csv` |

## Reproducibility statement (draft)

- Before any pilot or confirmation utterance was decoded, the conditions, data split, recognisers, normalisation, metrics, bootstrap and decision rules were sealed (`stage3_spec.json`, SHA-256 `ac5a36a0…`) and committed (`ef072e5`).
- The analysis code was sealed again before the confirmatory run (`7beca216…`, commit `a51ea54`); one presentation-only amendment is recorded.
- The decision record is `stage3_decision.json` (`608c919c…`, commit `d612bdb`).
- Stage 1/2 provenance is tag `paper-stage2b-confirmed`.
- Code, sealed selections and all per-utterance outputs are in the repository; LibriSpeech is public.
- The literature audit and positioning were frozen in the commit that adds `novelty_boundary.md`.

## Open decisions

- Venue and page budget. This sets how much of Stage 2 goes in the main text, and whether the anonymity policy affects links to the public repository.
- Whether the imaging finding and the v1 FAIL history go in the main text or the supplement.
- Final title (A or B).
- Before submission: re-run the targeted literature queries in `novelty_boundary.md` §9.
