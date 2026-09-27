# Claims and evidence (draft 3, 2026-09-27; positioning frozen; TASLP-upgrade claims C17–C20 added)

All values are from the confirmation set (2,174 utterances, 73 speakers) unless marked.
WER differences are micro (corpus) values in percentage points (pp). Intervals are 95 %
speaker-bootstrap CIs (10,000 replicates, stratified by subset). W = Whisper large-v3;
V = wav2vec2-base-960h. Source directory: `results_paper/stage3_asr/`. The literature
positioning comes from the completed audit (`novelty_boundary.md`, `literature_matrix.md`).

## Positioning (frozen 2026-09-26): **NOVELTY_NARROW_BUT_DEFENSIBLE**

| # | Component | Status | Evidence from the audit (keys in `literature_matrix.md`) | Permitted wording in the paper |
|---|---|---|---|---|
| P1 | General bandwidth-vs-codec (or vs-channel) decomposition | **Not novel** | moreno1994sources (telephone channel); besacier2001effect (GSM FR); bauer2010wtimit (AMR-NB/WB); borsky2015mp3 (MP3); heymans2022multistyle (GSM FR). Partial: moller2002analytic, fernandezgallardo2017predicting, basu2026factors (preprint) | "Earlier studies separated band limitation from coding distortion for telephone channels, GSM, AMR and MP3 [..]; we apply the same logic to 8 kbps Opus." |
| P2 | Cutoff-matched bandwidth control | **Already exists** | borsky2015mp3 (FIR low-pass at a per-bitrate cutoff read from spectrograms). Nominal controls (decimation, a 3.4 kHz low-pass, G.712) are common | "The nearest precedent matched the cutoff of each MP3 bitrate [borsky2015mp3]; our control is fitted to the full measured linear response and validated on held-out speakers." No priority claim |
| P3 | Low-rate Opus/SILK-NB decomposition with a control fitted to the measured response and validated on held-out speakers | **Not found in the audited literature** (as of 2026-09-26; search limits in `novelty_boundary.md` §9) | Located Opus–ASR studies report total penalties only: khare2020opus, jassim2020vocoders, jacobellis2024mpq, bai2026semdac, wang2025stcts, jones2022microphone, buethe2024nolace. Nearest controls: borsky2015mp3 (cutoff only); tseng2025probing (neural-codec responses measured, no control) | "The Opus–ASR studies we located report the total penalty and do not include a bandwidth control." Never "first" or "novel" |
| P4 | Paired confirmation in two pretrained recognisers, with speaker-bootstrap intervals, a pilot plus one pre-registered confirmatory run, and negative controls | **Part of the current contribution; no priority claimed** | Earlier decompositions used HMM-era, mostly retrained systems and reported no intervals. basu2026factors ran two current models under identical degradations, without a decomposition or statistics. moller2002analytic had two HMM-era recognisers | Described as properties of this study's design (Methods), not as an advance over prior work |

**Contribution statement (conservative; `novelty_boundary.md` §6).** We measure how much of
the WER increase caused by 8 kbit/s Opus, which libopus 1.4 encodes in SILK narrowband mode,
is reproduced by removing bandwidth alone.
- **Control.** A zero-phase linear low-pass fitted to SILK-NB's measured linear transfer function, calibrated on one set of speakers and validated on held-out speakers before any recognition experiment.
- **Design and result.** In a pre-registered paired design (a pilot, then one confirmatory run with 2,174 utterances from 73 speakers):
  - the control increased WER by 0.14 pp (Whisper large-v3) and 1.40 pp (wav2vec2-base-960h);
  - Opus increased it by a further 0.69 and 2.07 pp, with 95 % speaker-bootstrap intervals excluding zero;
  - bandwidth removal therefore accounted for about 17 % and 40 % of the total Opus penalty;
  - high-rate SILK-NB showed no detectable pooled residual.
- **Relation to prior work.** The design follows earlier coded-vs-band-limited comparisons for telephone channels, GSM, AMR and MP3. We apply it to a codec whose audio bandwidth the encoder selects from the bitrate, with a codec-matched control and two current pretrained recognisers.

## Claims made

| # | Tier | Claim (approved wording) | Evidence | Source | Qualification |
|---|---|---|---|---|---|
| C1 | Primary | Removing SILK-NB's bandwidth with the linear low-pass control alone increases WER | LP − REF: W +0.14 [+0.04, +0.25]; V +1.40 [+0.99, +1.92] | `07` (delta_bw, micro) | W test-clean alone −0.03 [−0.13, +0.07] (secondary) |
| C2 | Primary | After bandwidth is controlled, 8 kbps Opus leaves a codec-specific residual in both recognisers | OPUS − LP: W +0.69 [+0.46, +0.94]; V +2.07 [+1.68, +2.57]. Macro: W +1.00 [+0.64, +1.39]; V +2.61 [+2.12, +3.13] | `07` (delta_opus_residual) | The contrast also contains the 4–5 kHz image, a median level difference of about −0.6 dB and a 1–2 sample lag (see C9, L2). It is defined for the libopus 1.4 encoder + FFmpeg 6.1.1 native decoder (decoder resampling is non-normative, RFC 6716 §4.2.9). The decomposition is sequential (REF → LP → OPUS), so the residual includes any bandwidth × coding interaction |
| C3 | Primary | Bandwidth removal accounts for only part of the total Opus penalty | Share of OPUS − REF: W 0.17 [0.05, 0.29]; V 0.40 [0.35, 0.45] | `07` (bw_share_of_opus_total) | Pre-declared secondary ratio. It is a share along the REF → LP → OPUS path, not an interaction-free attribution |
| C4 | Replication | The residual has the same direction in both recognisers | C2; both CIs exclude 0 | `07`, `fig05` | Two recognisers only |
| C5 | Replication | The residual is present in both test subsets | test-clean: W +0.29 [+0.15, +0.46], V +0.94 [+0.72, +1.18]; test-other: W +1.22 [+0.75, +1.77], V +3.60 [+2.78, +4.68] | `07` (per-subset scopes) | Secondary scope |
| C6 | Replication | The pilot showed the same direction | Pilot OPUS − LP: W +0.35 [+0.07, +0.64]; V +1.49 [+0.74, +2.25] (138 utterances, 69 speakers) | `pilot/pilot_bootstrap.csv` | Different split (dev sets) |
| C7 | Supporting | High-rate SILK-NB (40 kbps) showed no detectable pooled residual relative to LP | SILK − LP: W +0.02 [−0.04, +0.08]; V −0.09 [−0.20, +0.02] | `07` (delta_silk_residual) | Pooled only (V test-other −0.24 [−0.50, −0.005]); no equivalence margin; SILK uses `signal=voice` |
| C8 | Supporting | Low-rate OPUS has higher WER than high-rate SILK-NB | OPUS − SILK: W +0.67 [+0.46, +0.89]; V +2.16 [+1.73, +2.71] | `07` (opus_minus_silk) | **Not a pure bitrate effect** (bitrate and signal hint both differ) |
| C9 | Supporting | 4–8 kHz image energy of comparable power is present in both codec conditions | Total 4–8 kHz power vs REF: LP −24.5, OPUS −16.7, SILK −15.8 dB. Mirror coherence: 0.000 / 0.227 / 0.970 | `09_signal_metrics_pooled.csv` | Coherence measures copy fidelity, not strength. The image level depends on the decoder's resampler: FFmpeg's interpolator differs from the reference decoder's (inferred from source, not measured) |
| C10 | Descriptive | The residual is mostly substitutions | OPUS − LP, per 100 reference words: W S +0.51 [+0.34, +0.70], D +0.10, I +0.08; V S +1.79 [+1.46, +2.21], D +0.13, I +0.15 | `07` (micro_error_type) | The error-type split depends on the alignment |
| C11 | Descriptive | Relative to each baseline, the Opus residual is similar across recognisers; the bandwidth penalty is not | Residual / LP WER: W +26.0 %, V +30.6 %. Bandwidth / REF WER: W +5.6 %, V +26.2 % | Derived from `07` | Post hoc; no CIs |
| C12 | Interpretation | The residual is consistent with (the signal evidence implicates) low-rate in-band coding distortion | In-band LSD 0–3 kHz vs LP: OPUS 6.14 dB, SILK 1.37 dB. Coherence with LP over 0–3.5 kHz: 0.623 vs 0.993 (medians). SILK carries comparable image power with no pooled residual | `09_signal_summary.csv`, C7, C9 | **Not causal:** no manipulation isolates in-band distortion |
| C13 | Control | The codec decode path does not by itself change WER | NEG_CODEC − REF: W +0.002 [−0.046, +0.049]; V +0.002 [−0.057, +0.065] | `07` | Controls the Ogg container, the FFmpeg decoder and the 48 → 16 kHz resampling. NEG_CODEC is CELT-only, so by FFmpeg's source it does not pass through the SILK upsampling (swresample) step; that step is shared only by OPUS and SILK (inferred from source, not measured) |
| C14 | Control | The filtering path produces at most ~0.1 pp effects | NEG_LP − REF: W −0.08 [−0.15, −0.004]; V +0.10 [+0.02, +0.19] | `07` | CIs exclude 0, but stay within the pre-declared ±0.5 pp margin; do not interpret effects of order 0.1 pp |
| C15 | Validation | The LP control reproduces SILK-NB's linear band limitation on unseen speakers | Stage 2B confirmation (train-clean-100, 40 speakers): LSD 0–3 kHz 0.031 dB; coherent bandwidth 4093.8 vs reference 4125.0 Hz; coherent 4–8 kHz power −24.7 vs −24.9 dB; \|H1\| RMS difference 0.57 dB (3.0–4.2 kHz) | `results_paper/lowpass_confirmation/` | Corrected Gate 5 (the v1 FAIL is retained). The LP reference was measured at 40 kbps and is not fully converged: near the band edge it still rose by 0.24–0.83 dB between 32 and 40 kbps (`lowpass_validation/calibration_curves.csv`) |
| C17 | Sensitivity (post-confirmation; not confirmatory) | Matching the RMS level of the Opus signal to the control did not remove the residual in either recogniser | Addition A, confirmation utterances decoded a second time: OPUS8_LEVEL_MATCHED − LP W +0.70 [+0.47, +0.95], V +2.09 [+1.71, +2.57]; OPUS8_LEVEL_MATCHED − OPUS W +0.012 [−0.007, +0.032], V +0.018 [−0.028, +0.062]; retained 1.02 / 1.01 of T*; rule GO in both | `results_paper/taslp_upgrade/level/analysis/level_decision.json` (`1e7e8424…`) | Broadband RMS only, not per band. Can qualify but not strengthen C2. The wav2vec2 result is informative (amendment 01: invariance only approximate; 188 of 2,174 wav2vec2 hypotheses changed) |
| C18 | Supporting (fresh-utterance, not fresh-speaker, holdout) | Within forced SILK-NB, the residual beyond LP decreased with bitrate in both recognisers | Addition B, 1,665 unused test utterances, 70 speakers: slope on log2 bitrate W −0.206 [−0.267, −0.146], V −0.854 [−1.074, −0.657] pp per doubling; R_8 W +0.55 [+0.37, +0.74], V +2.07 [+1.65, +2.55]; R_24, R_40 CIs include 0; rule GO in both | `results_paper/taslp_upgrade/sweep/analysis/sweep_decision.json` (`eb0ec2a2…`) | Speakers are the confirmation speakers; no REF recognition. Supports, but does not isolate, C12: in-band distortion, level and image fidelity all vary with the rate (descriptors reported beside it) |
| C19 | Supporting | At a fixed signal hint, 8 kbps SILK-NB has higher WER than 40 kbps SILK-NB | SILK8 − SILK40: W +0.52 [+0.36, +0.68]; V +2.13 [+1.65, +2.67] | addition B, `sweep_bootstrap.csv` (E_8_40) | Fresh utterances; a bitrate contrast at a fixed hint, which C8 is not |
| C20 | Replication (descriptive) | The 8 kbps residual reappears on fresh utterances | R_8 (sweep) W +0.55, V +2.07 vs confirmatory T* W +0.69, V +2.07; SILK8 files byte-identical to the OPUS settings' files for all 1,665 sweep utterances | addition B | Agreement was not a pre-declared criterion; W subset pattern: test-clean R_8 +0.11 [−0.04, +0.27], test-other +0.95 [+0.65, +1.28] |
| C16 | Provenance | The design and decision rules were fixed before any evaluation decoding | Spec `ac5a36a0…` sealed 07:17:48 UTC, commit `ef072e5`; pilot decoded from 07:18:13; confirmation freeze `7beca216…`, commit `a51ea54`; confirmation decoded 07:24:01–08:21:40 | `stage3_spec.json`, `confirmation_freeze.json`, `raw/*/run_log.json` | Internal pre-registration (sealed files and commits), not a public registry |

### Literature consistency (for the Discussion; directional only, not evidence for the claims above)

| Our claim | Consistent prior evidence | Differing prior evidence |
|---|---|---|
| C2/C3: residual > bandwidth at 8 kbps | bauer2010wtimit (AMR-NB 12.2, codec > bandwidth); borsky2015mp3 (MP3 12 kbps, residual ≫ low-pass); basu2026factors Fig. 2b (GSM, read from figure) | besacier2001effect, heymans2022multistyle (GSM FR 13 kbps: mostly bandwidth; retrained models) |
| C1: V bandwidth-sensitive, W barely | shah2025srb (audio-processing NWERD: wav2vec2-base-960h 30.6 vs whisper-large-v2 6.9); likhomanenko2021rethinking, li2019ssrasr (small bandwidth-only costs) | — |
| C12: low-rate in-band coding distortion | buethe2024nolace (Opus 6 kb/s: +1.07 pp WER; WB SILK implied); skoglund2020opus (SILK quality "degrades quickly" below 10 kb/s) | — |
| C7: high-rate SILK-NB ≈ LP (pooled) | besacier2001effect, heymans2022multistyle (small codec share for 13 kbps GSM FR); codec-results-03 (Opus NB at 11 kb/s perceptually tied with a 3.5 kHz low-pass, a perceptual measure) | — |

## Claims not made (and why)

| Not claimed | Reason |
|---|---|
| In-band coding distortion *causes* the residual | The mechanism was not manipulated; the signal evidence is correlational/descriptive. The bitrate sweep (C18) shows rate dependence, but in-band distortion, level and image fidelity co-vary with rate |
| The level difference has no effect on recognition | Addition A (C17) matched broadband RMS only, and is a post-confirmation sensitivity analysis, not a confirmatory test |
| The sweep generalises to new speakers | Addition B is a fresh-utterance, not fresh-speaker, holdout |
| SILK is equivalent to, or statistically indistinguishable from, LP | No equivalence margin was pre-declared; the result is pooled only; V test-other differs |
| OPUS − SILK is a bitrate effect | `signal=auto` vs `signal=voice` also differs (the fixed-hint bitrate contrast is C19, on other utterances) |
| The 4–5 kHz image is stronger in SILK | Mirror coherence measures copy fidelity; the power is comparable |
| OPUS is byte-identical to the prior study (unqualified) | Verified on 40 dev-clean utterances in Stage 2A only |
| wav2vec2 is "3× / 10× more sensitive" (unqualified) | True only in absolute points; the relative residuals are similar |
| Universality across recognisers, languages, codecs, bitrates or decoders | Two recognisers, one corpus, one low-rate operating point, one decoder (FFmpeg 6.1.1) |
| Human intelligibility or perceived quality | Not measured (no listening tests, no STOI/PESQ) |
| First, or novel, separation of bandwidth from coding distortion | P1: moreno1994sources, besacier2001effect, bauer2010wtimit, borsky2015mp3, heymans2022multistyle |
| First, or novel, bandwidth-matched low-pass control | P2: borsky2015mp3 (cutoff-matched) |
| Priority for the Opus/SILK-NB decomposition or the measured-response control | P3: "not found in the audited literature" is a search outcome with stated limits, not a priority claim |
| Priority for the two-recogniser paired design | P4: presented as a design property only |
| "Codec residual can exceed the bandwidth effect" as a new finding | Already shown for AMR-NB (bauer2010wtimit) and MP3 (borsky2015mp3) |
| Whisper's low band-limit sensitivity relative to wav2vec2 as a new finding | Already measured (shah2025srb) |
| Low-rate SILK coding degrades ASR as a new finding | buethe2024nolace |
| The bandwidth shares are interaction-free | The decomposition is sequential; borsky2015mp3 reports a non-linear combination for MP3 |
| Interaction effects, or propagation through the ASR encoder | Not tested in Stage 3 |
