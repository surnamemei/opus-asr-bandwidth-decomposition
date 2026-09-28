# Final claim audit (TASLP submission, 2026-09-28)

## Method

**Files.** Both files as built by `tools/build_submission.py` in the final editorial pass:

- `manuscript/taslp_submission.md` (main paper);
- `manuscript/taslp_supplement.md` (supplement).

HTML comments, which are not rendered, were excluded.

**Terms.** Searched case-insensitively, as whole words with their inflections: mechanism, cause,
caused, causal, independent, robust, general, generalise, generalize, equivalent, equivalence,
"bandwidth share", "coding distortion", "wideband better", superior, first, novel, proof, prove,
demonstrate.

**Result.**

- There are **69 occurrences**: 55 in the main paper and 14 in the supplement. Each was read in
  context.
- **No hits** for cause, caused, equivalent, generalize, superior, novel, proof, prove, demonstrate
  or "wideband better".
- All 69 remaining occurrences are **kept**, each justified below.
- The risky phrasings of the previous submission version (commit `4d2395f`) were **changed** in
  this pass. They are listed in Part B.

**Automatic check.** `tools/check_numbers.py --submission` (FORBIDDEN list) independently rejects
the following:

- priority claims ("first to/study/…", "novel", "for the first time");
- "equivalent";
- "caused by (in-band) coding";
- "prove(s)";
- "wideband is/was (generally) better/superior";
- "decoder-independent/-invariant" unless negated ("no decoder-invariant …").

It passes on the final files.

## A. Occurrences in the final files

Status is **K** (kept). Section names follow the final numbering.

| # | Phrase (verbatim excerpt) | File / section | Status | Reason |
|---|---|---|---|---|
| 1 | "further constrain, but do not identify, the mechanism" | main / Abstract | K | States explicitly that the mechanism is not identified. |
| 2 | "No mechanism is inferred from them" (exploratory correlations) | main / 4.3 | K | Negation; draft-2 wording for exploratory, uncorrected correlations. |
| 3 | "not a fitted law or an identified mechanism" | main / 5 (organising hypothesis) | K | Labels the coverage/fidelity reading as exploratory, as required. |
| 4 | "so the mechanism is not established" | main / 5 (What is still unknown) | K | Negation; no condition isolates in-band degradation. |
| 5–6 | "**Mechanism.** The residual is a bundle, not a uniquely identified mechanism" | main / 6, item 4 | K | Limitation heading and negation (2 occurrences). |
| 7 | "but the mechanism is not established" | main / 7 | K | Negation in the conclusion. |
| 8 | "These shares are sequential attributions, not causal fractions" | main / 4.2 | K | Negation; frames the 17 % / 40 % shares as required. |
| 9 | "they are not causal fractions of the penalty" | main / 5 | K | Negation. |
| 10 | "A measured, independently validated linear control" | main / 1, contribution 1 | K | Validation used 40 held-out speakers disjoint from calibration (Section 3.4, S1); "independently" describes the data split, not a claim of generality. |
| 11 | "(i) a bitrate-independent linear band-limiting response" | main / 3.4 | K | Draft-2 description of the preparatory component model. Clarified in this pass: component (iii) now states that it includes the additional low-rate attenuation seen in Fig. 1, which the best-linear attribution assigns to the linear side. |
| 12 | "On an independent filter-validation set of 40 unseen train-clean-100 speakers" | main / 3.4 | K | Describes a disjoint data set. |
| 13 | "both test subsets and an independent pilot" | main / 5 (What is robust) | K | The pilot used the development subsets, disjoint from the confirmation set. |
| 14 | "robustness" (index term) | main / Index Terms | K | Keyword. |
| 15 | "**Targeted robustness tests of the residual:** it survives a more inclusive best-linear attribution …, RMS level matching and alternative error weightings" | main / 1, contribution 3 | K | Each item is backed by its frozen outcome: best-linear ROBUST_RESIDUAL, level matching GO, and the metric audit (ordering classed robust). Decoder and application mode are described as quantified dependence, not survival of the residual. |
| 16–17 | "Speech Robust Bench found wav2vec2-base-960h far less robust than Whisper" | main / 2 | K | Literature report [shah2025srb] (2 occurrences). |
| 18 | "CONDITIONAL GO if the residual is robust in both recognisers" | main / 3.7 | K | Verbatim frozen decision rule. |
| 19 | "3.9 Robustness analyses (specified after the confirmation)" | main / 3.9 heading | K | Section label; status defined in its first paragraph. |
| 20 | "The pre-declared criterion for a robust residual" | main / 3.9 | K | Names the frozen outcome ROBUST_RESIDUAL and states its criterion. |
| 21 | "classified each statement as robust to the weighting or not" | main / 3.9 | K | Frozen metric-audit class, defined in S8. |
| 22–23 | "summarises the robustness analyses"; "Post-confirmation robustness analyses" | main / 4.4 text and Table IV caption | K | Labels (2 occurrences); the caption states that the contrasts differ between rows. |
| 24 | "**What is robust.**" | main / 5 | K | Discussion heading requested (§15 A); the paragraph lists the evidence and boundaries. |
| 25–26 | "the robustness ranking of Speech Robust Bench" | main / 5 | K | Literature (2 occurrences). |
| 27 | "does not show a general advantage of wideband coding at this rate" | main / 4.5 | K | Negation; frozen allocation claim boundary. |
| 28 | "generalisation to pristine-source recordings is limited" | main / 6, item 9 | K | Limitation. |
| 29 | "Generalisation beyond the tested codec version, corpus and recognisers remains future work" | main / 7 | K | Limitation, as requested (§17). |
| 30 | "No equivalence margin was declared" | main / 3.9 | K | Negation. |
| 31–32 | "No equivalence margin was pre-declared, so this is not a claim of equivalence" (SILK reference) | main / 4.3 | K | Negation (2 occurrences). |
| 33 | "No clear difference; not equivalence" (application-mode row) | main / Table IV | K | Negation; required application-mode boundary. |
| 34 | "no equivalence is claimed" | main / 4.4 (Application mode) | K | Negation. |
| 35 | "the bandwidth share it yields is path-dependent" | main / 1 | K | Required framing. |
| 36 | "The pre-declared secondary *bandwidth share* … is therefore a path-dependent share along this path, not an interaction-free attribution" | main / 3.7 | K | Definition plus framing. |
| 37 | "its linear share is not a bandwidth share" | main / 3.9 | K | Negation; the best-linear component is not called "bandwidth". |
| 38–39 | "Bandwidth share of OPUS − REF / of SILK − REF" | main / Table III rows | K | Frozen table labels; the caption states "sequential and path-dependent". |
| 40 | "Bandwidth shares (…) are sequential and path-dependent" | main / Table III caption | K | Framing. |
| 41 | "its linear share is not a bandwidth share" | main / Table IV | K | Negation. |
| 42 | "its bandwidth share is path-dependent, not an interaction-free attribution" | main / 6, item 1 | K | Limitation. |
| 43 | "decoder invariance of the bandwidth share or codec-specific residual was not established" | main / 6, item 5 | K | Verbatim frozen decoder limitation. |
| 44 | "they add coding distortion within the band they keep" | main / 1 | K | General description of low-rate codecs (problem statement), not a claim about the residual. |
| 45 | "can therefore come from the missing band, from in-band coding distortion, or from both" | main / 1 | K | Poses the question; no attribution. |
| 46 | "**Separating band limitation from coding distortion.**" | main / 2 | K | Literature topic heading. |
| 47 | "(iii) bitrate-dependent coding distortion within the retained band, including the additional attenuation …" | main / 3.4 | K | Signal component of the preparatory model (no ASR); clarified in this pass. |
| 48 | "It therefore contains in-band coding distortion and every other difference between the decoded Opus signal and the LP signal" | main / 3.7 | K | Definitional: the residual contains every difference and is not identified with any one of them. |
| 49 | "not a factorial estimate of an interaction between bandwidth loss and coding distortion" | main / 3.10 | K | Negation; frozen allocation boundary. |
| 50–51 | "changes the coding-distortion budget, so the comparison does not identify a factorial interaction between bandwidth loss and coding distortion" | main / 6, item 3 | K | Verbatim frozen limitation (2 occurrences). |
| 52 | "including a failed first criterion" | main / 1, contribution 1 | K | Ordinal. |
| 53 | "The first validation (dev-clean and dev-other) failed one criterion" | main / 3.4 | K | Ordinal. |
| 54–55 | "The first six rows …"; "(first two rows)" | main / Table IV caption | K | Ordinal (2 occurrences). |
| 56 | "the main paper's tables and robustness analyses" | suppl. / preamble | K | Label. |
| 57–59 | "ROBUST_RESIDUAL" (frozen outcome) | suppl. / S6 text and Table S9 (2 cells) | K | Frozen outcome labels (3 occurrences). |
| 60 | "Robustness analyses per subset (secondary scope; no multiplicity correction …)" | suppl. / Table S12 caption | K | Label with scope caveat. |
| 61–63 | "robust to the weighting if …"; "were robust for both recognisers"; "the wav2vec2 share robust" | suppl. / S8 | K | Frozen metric-audit classes with their criteria stated in the same paragraph (3 occurrences). |
| 64 | "a result without a clear difference is not an equivalence claim" | suppl. / S7 (Decoder) | K | Negation. |
| 65 | "no bandwidth share, residual or equivalence is claimed" | suppl. / Table S11 caption | K | Negation. |
| 66 | "The linear share is not a bandwidth share" | suppl. / Table S9 caption | K | Negation. |
| 67 | "no bandwidth share, residual or equivalence is claimed" | suppl. / Table S11 caption | K | Same sentence as #65; the two search terms, "equivalence" and "bandwidth share", were counted separately. |
| 68 | "the first validation had failed an internally inconsistent criterion" | suppl. / S1 | K | Ordinal. |
| 69 | "the first validation of the low-pass control failed" | suppl. / S10 | K | Ordinal. |

## B. Phrases changed in this pass

Each change is relative to the committed submission version of `4d2395f`.

| Before (previous submission version) | After (final) | File / section | Reason |
|---|---|---|---|
| "This supports, but does not isolate, the interpretation of the residual as low-rate in-band coding distortion." | "Level matching, a bitrate sweep, and decoder and application-mode sensitivities further constrain, but do not identify, the mechanism." | main / Abstract | No mechanism interpretation in the abstract (§3, §5). |
| "their narrowband modes remove bandwidth and add coding distortion at once, and studies … disagree on the share due to bandwidth" | "Low-bitrate narrowband codecs remove bandwidth and introduce other distortions at the same time, which makes their penalty … hard to attribute" | main / Abstract | Problem statement without presupposing what the residual contains. |
| "reproduced only part of the WER increase caused by Opus at 8 kbit/s: a small share for Whisper large-v3 and 40 % for wav2vec2-base-960h" | "reproduced only a minority of the WER increase under Opus at 8 kbit/s, and a substantial residual beyond the linear component remained: 0.69 and 2.07 pp … and 0.74 and 2.32 pp beyond the best-linear component" | main / 5 (What is robust) | "Caused" removed; the robust claim is the residual, not a share (§1, §15 A). |
| "It did not depend on how linear loss is defined or on how errors are weighted" | "neither level matching nor the choice among four error weightings removed it"; plus a new paragraph: "The share assigned to bandwidth is not an invariant quantity …" | main / 5 | The old sentence implied independence of the definitions. The residual's presence survives; the share does not (§15 B). |
| "The signal evidence is consistent with low-rate in-band coding distortion." | "the evidence is consistent with low-rate coding degradation beyond linear effects" | main / 5 (What is still unknown) | Allowed wording (§3). |
| "This supports, but does not isolate, the low-rate in-band coding distortion interpretation" | removed; "No condition manipulated in-band coding degradation while holding everything else fixed, so the mechanism is not established." | main / 5 | Mechanism language (§3). |
| "to the extent that it is coding distortion, which the evidence supports but does not establish" | "to the extent that the residual is coding degradation" | main / 5 (Practical reading) | Shorter and hedged. |
| "The two recognisers may therefore differ more in how they use content above 4 kHz than in how they respond to the codec-specific degradation beyond the control" | removed | main / 5 | The metric audit shows that the baseline-relative residual is similar under WER but not under CER (+30.3 % against +45.6 %); Section 4.2 now reports both. |
| "The residual is a bundle, not a mechanism: it contains in-band coding distortion, …" | "The residual is a bundle, not a uniquely identified mechanism: it contains in-band coding degradation, …" | main / 6, item 4 | Wording of limitation 4 (§16). |
| "These results support, but do not isolate, the interpretation of the residual as low-rate in-band coding distortion rather than band limitation alone." | "Together these results are consistent with a low-rate trade-off between spectral coverage and fidelity, but the mechanism is not established." | main / 7 | Conclusion as requested (§17). |
| "bandwidth removal accounted for a minority of the total penalty: a small share for Whisper large-v3 and 40 % for wav2vec2-base-960h" | "the validated control reproduced only a minority of the penalty" (no share values) | main / 7 | The conclusion does not end with the shares (§17). |
| "the exact split depends on how linear loss is defined, but the residual did not shrink" | "the exact attribution changed, but the residual did not disappear" | main / 4.4 | Wording required in §7. |
| "The best-linear surrogate …"; table row "residual beyond the best-linear surrogate" | "The best-linear component …"; row "OPUS − LIN8 (pp)" | main / 4.4; suppl. / Table S9 | "Surrogate" suggested a codec model. The best-linear attribution is a sensitivity to the attribution definition (§2 A, §14). |
| "This sensitivity tests the total penalty only; the bandwidth decomposition remains defined for the FFmpeg chain." | "The decoder implementation thus affects the magnitude for Whisper, and the total penalty is not an artefact of FFmpeg decoding alone. The bandwidth decomposition remains defined for the FFmpeg chain, and no decoder-invariant residual or share is claimed." | main / 4.4 (Decoder) | Decoder claim boundary as listed in §2 D. |
| "so the results generalise to new utterances of the test speakers, not to new speakers" | "This is a fresh-utterance, not fresh-speaker, holdout: the 70 speakers are confirmation speakers" | main / 3.9 | Same scope, without a generalisation claim. |
| "(iii) bitrate-dependent coding distortion within the retained band." | "… within the retained band, including the additional attenuation within the band and at the band edge that appears at low rates (Fig. 1)." | main / 3.4 | Makes the component model consistent with the best-linear result (the 8 kbit/s chain's own linear response differs from the control's). |
| Limitation "Its absence of a residual is a pooled, non-equivalence result" (SILK reference) | removed from Limitations | main / 6 | Not repeated: Section 4.3 keeps "this is not a claim of equivalence". |
| "…showed that the total penalty persisted, without a clear difference from the audio mode (not an equivalence result)" | "`OPUS_APPLICATION_VOIP` was tested only as a post-confirmation sensitivity of the total penalty" (limitation); "no equivalence is claimed" (Results) | main / 6, item 7; 4.4 | Not repeated; the application-mode wording follows §2 E. |
