# Reviewer-concern sensitivity analyses R1–R3: deviations and disclosures (2026-09-27)

Plan: `paper/reviewer_sensitivity/reviewer_spec.json` (SHA-256 `2a6eae35…`, commit `17bc8e2`).
Code freeze: `code_freeze.json` (SHA-256 `dc271f29…`). The plan states that a change made
after the step it affects is a deviation and is reported with the results. This note lists
every such change and every disclosure. None of them changed a gate, a tolerance, a rule, a
selection or an outcome.

1. **RS2 before the signal-validation step.** The author asked for RS1 together with the
   R1-V and R2-V validations. The plan places those validations in RS3, after the RS2 code
   freeze, and allows no reading of the signal-validation subset before RS3. The code freeze
   was therefore sealed between RS1 and the validations. The plan's order was kept.

2. **RS3 in three sealed parts.** RS3 was sealed as three part reports (`signal`,
   `confirmation`, `sweep`) and one combined report, `validation/validation_report.json`, which
   holds every gate result and the hash of each part. The plan asks for one sealed validation
   report; the combined report is that report.

3. **Confirmation part run although R1 was already STOPPED.** R1-G1 to G3 (encode and decode
   only, no ASR) were run after R1-V had failed, because the frozen runner forms the combined
   report only from all three parts. They passed. R1 stays STOPPED at R1-V.

4. **R3 descriptive items missing from the frozen analysis.** The frozen `analyse` step did not
   compute three R3 descriptive items that the plan pre-specifies:
   - the number of raw hypotheses that differ between NB8 and WB8;
   - the reproduction check of NB8 against Addition B's SILK8 hypotheses;
   - the in-band signal descriptors.

   They were computed after RS5 by `paper/reviewer_sensitivity/reporting/r3_descriptives.py`,
   which is outside the code freeze and reads sealed outputs only. They are sealed separately in
   `analysis/r3_descriptives.json` (SHA-256 `847f300e…`) and enter no outcome.

5. **Timing of the R3 in-band descriptors.** The plan lists the in-band descriptor set for NB8
   and WB8 among the measures sealed before ASR. `validate sweep` sealed the packet, bitrate,
   level and lag rows before ASR. The in-band descriptors were computed in the RS4b run
   (`raw/sweep/signal_metrics.csv`) and are sealed with its outputs.

6. **Throwaway dry run before the code freeze.** Before RS2, the RS3–RS5 code paths were run
   once on 3 utterances of the Stage 3 calibration set (dev-clean), to catch bugs that would
   otherwise have needed an amendment after the freeze. The outputs were written to a scratch
   directory and discarded. No evaluation or signal-validation audio was read, and no WER was
   compared.

7. **Exploratory post-gate diagnosis.** After R1-V and R2-V failed and R1 and R2 were STOPPED, an
   exploratory, post-hoc diagnosis was run (`exploratory/post_gate_diagnosis.json`, SHA-256
   `7882bd89…`, commit `c229a97`). Its code is outside the freeze and it is not part of any rule.
   It indicates that the libopus chain has a sub-sample, content-dependent delay, which makes the
   frozen integer-aligned |H1| measurement set-dependent. Any successor analysis needs an
   approved, sealed amendment and would be reported as post hoc. None has been started.

8. **Decoder-difference SNR.** The descriptive decoder-difference SNR follows the plan's
   definition, which uses no re-alignment. The ~1-sample offset between the two decoders
   dominates it. The SNR after removing that offset is reported only in the exploratory record
   (item 7).
