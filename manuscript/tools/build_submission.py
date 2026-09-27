"""Build manuscript/taslp_submission.md and taslp_supplement.md from draft 2 (manuscript.md).

Presentation and submission selection: draft-2 text is moved to the supplement, shortened or
re-referenced (table, figure and section numbers), and "pre-registered" is reworded as a
prospective, version-sealed specification. The only text not taken from draft 2 reports the later
sealed analyses: R1-R3 (the forced-wideband counterfactual of Sections 3.10 and 4.11, and
Supplementary Section S7) and R4 (the reference-decoder sensitivity paragraph of Section 4.8 and
Supplementary Section S8), the final invariance pass (the inclusive best-linear attribution, the
encoder application mode and the metric audit of Sections 3.11 and 4.12, and Supplementary
Sections S9-S11), with the matching edits to the Discussion, Limitations, Conclusion and
Reproducibility statement. Gate mechanics, rule thresholds and outcome labels of the later
analyses are given in the supplement, not in the main paper. Every number is copied from draft 2 or from the output of
tools/make_tables.py, which derives it from the frozen outputs; nothing is computed here.

    python manuscript/tools/build_submission.py           # (re)write both files
    python manuscript/tools/build_submission.py --check   # compare with the files on disk; write nothing

Fails loudly (exit status 1) if draft 2 differs from its committed version, if an expected
section, table, caption or phrase of draft 2 is missing or ambiguous, or if the output contains a
decimal number that is in neither draft 2 nor the generated tables. The numbers and table rows of
the output are then verified against the frozen outputs by `check_numbers.py --submission`.
"""
import re
import subprocess
import sys
from pathlib import Path

MANUSCRIPT = Path(__file__).resolve().parents[1]
CHECK = "--check" in sys.argv[1:]


def fail(msg):
    sys.exit(f"build_submission: FAIL: {msg}")


# draft 2 as committed (an uncommitted edit would make the submission irreproducible)
if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "manuscript.md"], cwd=MANUSCRIPT).returncode != 0:
    fail("manuscript.md (draft 2) differs from its committed version")
SRC = (MANUSCRIPT / "manuscript.md").read_text(encoding="utf-8")
GEN = subprocess.run([sys.executable, str(MANUSCRIPT / "tools" / "make_tables.py")], capture_output=True, text=True,
                     check=True, cwd=MANUSCRIPT).stdout


def find(text, s, what):
    """Index of s in text; fails unless it occurs exactly once."""
    n = text.count(s)
    if n != 1:
        fail(f"{what}: expected exactly 1 occurrence, found {n}: {s[:90]!r}")
    return text.index(s)


def gen_table(title, keep=None):
    """Generated table (header, rule, rows); keep = first-cell labels to retain, in order."""
    block = [l for l in GEN[find("\n" + GEN, "\n" + title, "generated table"):].split("\n\n")[0].splitlines()[1:]
             if l.startswith("|")]
    if len(block) < 3:
        fail(f"generated table {title.strip()!r} has no data rows")
    head, rule, rows = block[0], block[1], block[2:]
    if keep is not None:
        by = {r.split("|")[1].strip(): r for r in rows}
        missing = [k for k in keep if k not in by]
        if missing:
            fail(f"generated table {title.strip()!r} lacks rows {missing}")
        rows = [by[k] for k in keep]
    return "\n".join([head, rule, *rows])


def section(title, level="# "):
    """Text of a draft-2 section from its heading up to the next heading of the same level."""
    start = find(SRC, "\n" + level + title, "draft-2 section") + 1
    ends = [i for i in (SRC.find("\n# ", start + 1), SRC.find("\n## ", start + 1) if level == "## " else -1) if i != -1]
    return SRC[start:min(ends) if ends else len(SRC)]


def rep(text, old, new, count=1):
    n = text.count(old)
    if n != count:
        fail(f"replacement source: expected {count} occurrence(s), found {n}: {old[:90]!r}")
    return text.replace(old, new)


def between(text, a, b):
    return text[find(text, a, "block start"):find(text, b, "block end")]


# =============================================================== main paper
head = SRC[:find(SRC, "\n# 4. Results", "draft-2 section") + 1]
head = rep(head, 'title: "How much of the ASR penalty of low-rate Opus is bandwidth loss? A decomposition with a validated bandwidth control"',
           'title: "How much of the ASR penalty of 8 kbit/s Opus is bandwidth loss? A decomposition with a validated bandwidth control"')
head = rep(head, 'date: "Draft 2, 2026-09-27"', 'date: "TASLP submission version, 2026-09-27"')
comment = between(head, "<!--", "-->\n") + "-->\n"
head = rep(head, comment, """<!--
TASLP SUBMISSION VERSION (remove before submission)

- Derived from draft 2 (manuscript/manuscript.md, commit dbf8d5c) by editorial restructuring, plus the text and tables
  of the later sealed analyses (R3, R4 and the final invariance pass: A1, B1, C1), all taken from sealed records.
  Moved material is in taslp_supplement.md (supplementary material).
- Every table row and number of both files is checked against the frozen outputs by
  `python manuscript/tools/check_numbers.py --submission`; render with tools/render_ieee.sh taslp_submission.md.
-->
""")
head = rep(head, "detectable pooled residual. The residual consisted mainly of substitutions. Two pre-registered\nfollow-up analyses were then run once each.",
           "detectable pooled residual. The residual consisted mainly of substitutions. Two follow-up\nanalyses, specified and version-sealed in the same way after the confirmation, were then run\nonce each.")
head = rep(head, "In a pre-registered\npaired design (a pilot, then one confirmatory run",
           "In a paired design\nspecified and version-sealed before any evaluation audio was decoded (a pilot, then one confirmatory run")
head = rep(head, "2. **A pre-registered, paired estimate of the two components",
           "2. **A prospectively specified, paired estimate of the two components")
head = rep(head, "4. **Two pre-registered follow-up analyses:** a post-confirmation sensitivity analysis that matches the RMS level of the Opus signal to the control, and a forced SILK narrowband bitrate sweep on fresh utterances that tests whether the residual depends on the coding rate.",
           "4. **Prospectively specified follow-up and sensitivity analyses:** a forced SILK narrowband bitrate sweep on fresh utterances that tests whether the residual depends on the coding rate; sensitivity analyses of the residual (RMS level matching, and an inclusive best-linear attribution of the actual codec output) and of the total penalty (decoder; encoder application mode); and a metric and weighting audit.")
head = rep(head, "(paired, pre-registered, with\nspeaker-level intervals)",
           "(paired, prospectively specified and\nversion-sealed, with speaker-level intervals)")
head = rep(head, "## 3.1 Overview and pre-registration", "## 3.1 Overview and prospective specification")
head = rep(head, "and committed to version control. It fixed the data selections,",
           "and committed to version control; the specification is internal and was not lodged in a public\nregistry. It fixed the data selections,")
validation = between(head, "| Measure | Control | Reference / other |", "![Validation of the low-pass")
head = rep(head, validation, "")
head = rep(head, "frozen before the confirmation data were downloaded. On the confirmation set, 40 unseen\ntrain-clean-100",
           "frozen before the confirmation data were downloaded. On an independent filter-validation set of\n40 unseen train-clean-100")
head = rep(head, "train-clean-100 speakers (20 female, 20 male) with the filter taps unchanged, all criteria\npassed (Fig. 1):\n",
           "train-clean-100 speakers (20 female, 20 male) with the filter taps unchanged, all criteria\npassed (Fig. 1; the measured values are in Supplementary Table S1).\n")
head = rep(head, "it changed no estimand, gate,\nthreshold, condition, selection or rule (Appendix B).",
           "it changed no estimand, gate,\nthreshold, condition, selection or rule (Supplementary Section S6).")
head = head.replace("(Table 1)", "(Table I)")
# final invariance pass: later plans, the prior-art projection, and the follow-up rules in words
head = rep(head, "limitation of SILK narrowband; it is fitted to the codec's measured transfer function and",
           "limitation of SILK narrowband; it is fitted to the codec's measured high-rate transfer function and")
head = rep(head, "OPUS\nreproduces the encoder configuration of the preliminary analysis. In an earlier validation on\n40 dev-clean utterances, its packets were byte-identical to those of that analysis's encoding\npath; this identity was not re-verified on the test utterances. At 8 kbit/s, libopus 1.4\nselects narrowband automatically [@libopus14], so forcing narrowband produced the same packets\nas automatic selection in that validation (40/40).",
           "OPUS\nreproduces the encoder configuration of the preliminary analysis (byte-identical packets on 40\ndev-clean utterances; not re-verified on the test utterances). At 8 kbit/s, libopus 1.4 selects\nnarrowband automatically [@libopus14]; forcing it gave the same packets (40/40).")
head = rep(head, "Beam search was measured\nat 2–7.5 s per utterance on the shared GPU before any evaluation decoding, and was replaced by\ngreedy decoding at that point; greedy output was deterministic across repeats and identical\nbetween batched and unbatched decoding on the calibration set. Section 4.9 reports three Whisper\nhypotheses that differed when the same audio was decoded again in batches of a different\ncomposition.",
           "Greedy decoding replaced\nbeam search before any evaluation decoding, for compute reasons; it was deterministic across\nrepeats and between batched and unbatched decoding on the calibration set, although batches of a\ndifferent composition changed three Whisper hypotheses (Section 4.9).")
head = rep(head, "Exclusions were fixed at selection time from metadata\nonly:\n\n- utterances longer than 30 s (Whisper's input window);\n- utterances with an empty normalised reference;\n- the development utterances used for the controls;\n- for the confirmation set, the 1,000 utterances of the preliminary analysis. The confirmation utterances had therefore never been decoded in this project, although their speakers are the same test speakers.\n\nNo utterance was excluded after decoding.",
           "Exclusions were fixed at selection time from metadata\nonly: utterances longer than 30 s (Whisper's input window), utterances with an empty normalised\nreference, the development utterances used for the controls and, for the confirmation set, the\n1,000 utterances of the preliminary analysis, so the confirmation utterances had never been\ndecoded in this project, although their speakers are the same test speakers. No utterance was\nexcluded after decoding.")
head = rep(head, "\n**Relation to earlier controls.** The nearest precedent in the ASR literature matched only the\ncutoff of each codec bitrate [@borsky2015mp3]. The control here is fitted to the full measured\nlinear response and validated on held-out speakers.\n", "")
head = rep(head, "One amendment, recorded before the\nconfirmation, was presentation-only (marker shapes in one figure). The processing pipeline\nreproduced an earlier analysis exactly (250/250 checks), and the codec and filter controls\ndescribed below were validated in two earlier stages that used no ASR output. After the\nconfirmatory analysis was closed, a second specification for two follow-up analyses (Section\n3.9) was sealed and committed before any of their audio was encoded or decoded. Their code was\nfrozen after a check on the calibration set, and each was decoded once. Neither changes any\nconfirmatory estimate or decision.",
           "The codec and filter controls\ndescribed below were validated in two earlier stages that used no ASR output. Every later\nanalysis (Sections 3.9, 3.10 and 3.11) was specified and sealed after the confirmatory analysis\nwas closed and before any of its audio was encoded; none changes any confirmatory estimate or\ndecision.")
head = rep(head, "The\nsweep used test utterances that the project had never encoded, decoded or recognised, selected\nfrom metadata only with the confirmation rule: up to 30 per speaker from every test speaker\nwith an eligible unused utterance. This gave 1,665 utterances from 70 speakers (38 test-clean,\n32 test-other; 777 and 888 utterances; 3.17 h; 31,601 reference words). Every one of these\nspeakers also appears in the confirmation set: no test speaker was left unused, the development\nsubsets had supplied the pilot, calibration and control data, and wav2vec2-base-960h was\nfine-tuned on the training subsets. The results therefore generalise to new utterances of the\ntest speakers, not to new speakers.",
           "The\nsweep used 1,665 test utterances of 70 speakers that the project had never encoded, decoded or\nrecognised, selected from metadata only with the confirmation rule (Supplementary Section S5).\nAll 70 speakers also appear in the confirmation set, because no other test speakers were left\nand the other subsets had been used for development or training, so the results generalise to\nnew utterances of the test speakers, not to new speakers.")
# (thresholds and outcome labels in Supplementary Sections S4 and S5)
head = rep(head, "followed. Two follow-up analyses were then specified and sealed before any of their audio was\nencoded, and each was run once.",
           "followed. Each later analysis was specified and sealed before any of its audio was encoded, and\neach was run once.")
head = rep(head, "cost of the linear band limitation itself.",
           "cost of the linear band limitation itself. As a sensitivity analysis, we also apply their\nprojection to the codec output (Section 3.11).")
head = rep(head, "Each has its own\npre-declared rule with three outcomes, GO, WEAKEN or FALSIFY, applied per recogniser; the\ncombined outcome is GO or FALSIFY only if both recognisers agree, and WEAKEN otherwise. A\nmissing interval bound never satisfies GO or FALSIFY.",
           "Each has its own\npre-declared three-way rule, applied per recogniser; the rules and thresholds are given in\nSupplementary Sections S4 and S5.")
head = rep(head, " Before recognition, LP and OPUS had to reproduce the confirmation\naudio bit for bit, the level-matched RMS had to equal that of LP within 0.001 dB, and the gains\nhad to equal those implied by the confirmation audio within $10^{-6}$ dB.",
           " Before recognition, LP and OPUS had to reproduce the confirmation\naudio bit for bit and the level matching had to be exact (Supplementary Section S4).")
head = rep(head, "With $T^\\ast$ the confirmatory OPUS − LP estimate of each recogniser, the rule is GO if\nthe lower bound of $L$ is above zero and the lower bound of $K$ is above $-0.25\\,T^\\ast$ (a\nresidual remains, and the interval excludes level matching removing a quarter or more of it),\nand FALSIFY if the upper bound of $K$ is below $-0.5\\,T^\\ast$ (level matching removed more than\nhalf of it).",
           "The pre-declared criterion for a residual that persists under level\nmatching is that the interval of $L$ lies above zero and that of $K$ excludes level matching\nremoving a quarter or more of the confirmatory residual.")
head = rep(head, " Before recognition, encoding and\ndecoding alone had to show that every packet at every rate was SILK-only narrowband with 20 ms\nframes, that every encoder setting read back as requested, and that the median payload bitrate\nwas within ±15 % of nominal, with each rate's median at least 1.2 times the previous one.",
           " Before recognition, encoding and\ndecoding alone had to confirm the packet mode, the encoder settings and the bitrates\n(Supplementary Section S5).")
head = rep(head, "replicate. The rule compares $S$ with $S^\\ast = (U^\\ast - T^\\ast)/\\log_2 5$, the slope implied by\nthe confirmatory residuals at 8 kbit/s ($T^\\ast$, OPUS − LP) and 40 kbit/s ($U^\\ast$, SILK − LP).\nIt returns GO if the lower bound of $R_8$ is above zero, the upper bound of $S$ is below zero and\nthe lower bound of $S$ is at or below $0.5\\,S^\\ast$ (a residual at 8 kbit/s that declines with\nrate, with an interval that does not exclude a decline half as steep as the confirmation\nimplies), and FALSIFY if the upper bound of $S$ is at or above zero and its lower bound is above\n$0.5\\,S^\\ast$.",
           "replicate. The pre-declared criterion is a residual at 8 kbit/s that declines with rate: the\ninterval of $R_8$ lies above zero, and that of $S$ lies below zero and does not exclude a decline\nhalf as steep as the confirmatory residuals at 8 and 40 kbit/s imply.")

# final editorial pass: the SPS abstract limit (150-250 words), path-dependent wording of the
# sequential bandwidth share ("a small share" for Whisper in high-level prose; exact values stay in
# the results), and wording that does not identify the residual with in-band coding distortion.
# No number is added or changed.
ABSTRACT = """Low-bitrate speech codecs degrade automatic speech recognition (ASR); their narrowband modes
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
interpretation of the residual as low-rate in-band coding distortion."""
head = rep(head, between(head, "# Abstract\n\n", "\n\n**Index Terms**"), "# Abstract\n\n" + ABSTRACT)
head = rep(head, "codec-specific residual (Opus minus control). Both components",
           "codec-specific residual (Opus minus control); because the decomposition is sequential, the\n"
           "bandwidth share it yields is path-dependent. Both components")
head = rep(head, "is therefore a share along this path.",
           "is therefore a path-dependent share along this path, not an interaction-free attribution.")

T2, T3 = gen_table("TABLE 2 "), gen_table("TABLE 3 ")
cap = lambda s: SRC[find(SRC, s, "draft-2 caption or figure"):].split("\n")[0]
cap2 = cap(": Corpus WER (%) on the confirmation set")
cap3 = cap(": Paired contrasts on the confirmation set")
cap3 = rep(cap3, "with 95 % speaker-bootstrap intervals.",
           "with 95 % speaker-bootstrap intervals. Bandwidth shares (LP − REF divided by OPUS − REF or SILK − REF) are sequential and path-dependent.")
fig_components = cap("![Bandwidth component (LP − REF)")
fig_sweep = cap("![Addition B: residual beyond the linear control")
T5 = gen_table("TABLE 5 ", ["OPUS8_LEVEL_MATCHED − LP (pp; primary)", "OPUS8_LEVEL_MATCHED − OPUS (pp)"])
T6 = gen_table("TABLE 6 ")
T7 = gen_table("TABLE 7 ", ["Slope on log2 bitrate (pp per doubling; primary)", "SILK8 − SILK40"])
cap6 = cap(": Addition B, the forced SILK narrowband bitrate sweep")

r = section("4.9 Level-matched sensitivity analysis (Addition A)", "## ")
r10 = section("4.10 Bitrate sweep (Addition B)", "## ")
s42 = section("4.2 Confirmation: word error rate by condition", "## ")
s43 = section("4.3 Bandwidth component and codec-specific residual", "## ")
s44 = section("4.4 Replication across subsets, recognisers and the pilot", "## ")
s45 = section("4.5 High-rate SILK narrowband reference", "## ")
s46 = section("4.6 Error types", "## ")
s47 = section("4.7 Signal descriptors", "## ")
s48 = section("4.8 Negative controls", "## ")


def prose(sec):
    """A section's paragraphs without its tables, captions and figures."""
    keep = []
    for para in sec.split("\n\n")[1:]:
        if para.startswith(("|", ": ", "![")) or not para.strip():
            continue
        keep.append(para.strip("\n"))
    return keep


p43 = prose(s43)
p43[0] = rep(p43[0], "(Table 3)", "(Table III)")
p43[0] = rep(p43[0], "total Opus penalty (Fig. 3)", "total Opus penalty (Fig. 2)")
p43[0] = rep(p43[0], "Along the REF → LP → OPUS path, bandwidth\nremoval therefore accounted for 17 % [5, 29]",
             "Along the sequential REF → LP → OPUS path,\nbandwidth removal therefore accounted for a path-dependent share of 17 % [5, 29]")
p43[0] = rep(p43[0], "total Opus penalty (Fig. 2).", "total Opus penalty (Fig. 2); the Whisper share is imprecisely estimated.")
p43[1] = rep(p43[1], "about three times, and its\nbandwidth component about ten times, those of Whisper large-v3. Relative to each recogniser's\nown baseline, the residual was similar: +26.0 % and +30.6 % of the LP WER.",
             "about three times, and its\nbandwidth component five to ten times (depending on the error weighting; Section 4.12), those of\nWhisper large-v3. Relative to each recogniser's own baseline, the residual was similar under WER,\n+26.0 % and +30.6 % of the LP WER, but not under CER (+30.3 % and +45.6 %).")
p44 = rep(prose(s44)[0], "(Table S1, Figs. 4 and 5)", "(Supplementary Table S3)")
p45 = prose(s45)[0]
p46 = rep(prose(s46)[0], "(Table S2)", "(Supplementary Table S4)")
p47 = prose(s47)
p47[0] = rep(p47[0], "(Table 4)", "(Supplementary Table S6)")
p48 = rep(prose(s48)[0], "(Table S3)", "(Supplementary Table S5)")
p42 = rep(prose(s42)[0], "(Table 2, Fig. 2)", "(Table II)")

a_para = prose(r)                     # 0 label, 1 gates, 2 result, 3 wav2vec2, 4 clipping+reproduction
b_para = prose(r10)                   # 0 label, 1 validation, 2 result, 3 descriptors
a_result = rep(a_para[2], "recogniser (Table 5).", "recogniser (Supplementary Table S7).")
a_result = rep(a_result, "recognisers. The same held in both test subsets (Table S5), and the residual was still mostly\nsubstitutions: per 100 reference words, +0.52 substitutions [+0.35, +0.71] for Whisper and\n+1.79 substitutions [+1.48, +2.19] for wav2vec2.",
               "recognisers. The same held in both test subsets, and the residual was still mostly\nsubstitutions (Supplementary Section S4, Tables S7 and S8).")
a_w2v = rep(a_para[3], "per-channel normalisation. That expectation was corrected before the code freeze: the\nnormalisation's epsilon lets gain information persist in low-variance channels (Appendix B).",
            "per-channel normalisation. That expectation was corrected before the code freeze: the\nnormalisation's epsilon lets gain information persist in low-variance channels\n(Supplementary Section S6).")
a_w2v = ("Level matching changed 42 of the 2,174 Whisper hypotheses and 188 of the 2,174 wav2vec2\n"
         "hypotheses, without reducing either error count. The plan's expectation that wav2vec2-base-960h\n"
         "would be insensitive to a scalar gain was corrected before the code freeze, so its result is\n"
         "informative about level (Supplementary Section S6).")
a_result = rep(a_result, "Both intervals lie above the GO thresholds of −0.172 and −0.518 pp\nand exclude the reductions required for FALSIFY, so the pre-declared rule returned GO for both\nrecognisers.",
               "Both intervals exclude level matching removing a quarter of the\nconfirmatory residual, so the pre-declared criterion was met for both recognisers.")
b_valid = """Every packet at every rate was SILK-only narrowband with 20 ms frames, and the median payload
bitrates were 2.3–8.0 % below nominal (Table IV). At 8 kbit/s the sweep's `signal=voice`
encoding produced Ogg files byte-identical to those of the OPUS settings (`signal=auto`) for
all 1,665 utterances, so SILK8 − LP repeats the confirmatory OPUS − LP contrast on new
utterances (validation details: Supplementary Section S5)."""
b_result = b_para[2]
b_result = rep(b_result, "in both recognisers (Tables 6 and 7, Fig. 6).", "in both recognisers (Table IV, Fig. 3; trend and\nthresholds in Supplementary Table S9).")
b_result = rep(b_result, " The slopes on the rate rank and on the measured payload bitrate agree. The\ndecline was concentrated at low rates. The step from 8 to 12 kbit/s was the largest (+0.34 and\n+1.32 pp), and the later steps were smaller. The point estimates fell at every step in both\nrecognisers, and 66 % (Whisper) and 98 % (wav2vec2) of bootstrap replicates were monotone.\n", "\n")
b_result = rep(b_result, "[+1.65, +2.67]. In the per-subset analysis (Table S5),",
               "[+1.65, +2.67]. The decline was concentrated at low rates, with the largest step between 8 and\n12 kbit/s; the secondary slopes, the adjacent-rate contrasts and the corpus WERs are in\nSupplementary Section S5 (Tables S9 and S11). In the per-subset analysis (Supplementary Table S12),")
b_desc = rep(b_para[3], "changed with the rate as well (Table 8).", "changed with the rate as well (Supplementary Table S10).")
b_result = rep(b_result, "Both intervals lie below zero and reach below half the slope\nimplied by the confirmatory residuals (−0.144 and −0.465), so the pre-declared rule returned GO\nin both recognisers.",
               "Both intervals lie below zero and reach below half the slope\nimplied by the confirmatory residuals, so the pre-declared criterion was met in both recognisers.")

# the forced-wideband counterfactual of the later sensitivity plan (sealed R3 outputs): a practical
# bandwidth-allocation counterfactual, not a factorial interaction estimate; the two stopped
# attribution sensitivities (R1, R2) are reported in the Reproducibility statement and in S7 only
R3_METHODS = """## 3.10 Forced-wideband counterfactual (sealed after the follow-up analyses)

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
Section S7)."""
R3_RESULTS = """## 4.11 Forced-wideband counterfactual

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
descriptors: Supplementary Section S7, Tables S13 and S14)."""
# Section 4.12 (sealed A1, B1 and C1 records); numbers from the generated tables A1, A1D, C1 and 9
T9 = gen_table("TABLE 9 ")
LAST_SUPP_TABLE = 24 if ('With the VoIP application mode the total penalty remained positive: OPUS_VOIP8 − REF was\n+0.70 pp [+0.48, +0.95] for Whisper large-v3 and +3.44 pp [+2.71, +4.37] for wav2vec2-base-960h.\nNo clear application difference was established: OPUS_VOIP8 − OPUS was −0.12 pp [−0.25, +0.00]\nand −0.03 pp [−0.23, +0.15]. For Whisper the interval reaches zero and two secondary cells (CER;\ntest-other) excluded it, so a small reduction under the VoIP mode cannot be ruled out; no\nequivalence is claimed.\n\n') else 21
FINAL_RESULTS = "## 4.12 Sensitivity of the residual, the total and the metric\n\n" + T9 + "\n\n" + \
    ": Post-confirmation sensitivity analyses on the confirmation set (pooled, pp, 95 % speaker-bootstrap intervals): " \
    "inclusive best-linear attribution of the 8 kbit/s Opus output (LIN8; Section 3.11)" + (' and a change of the encoder application mode alone (OPUS_VOIP8)') + \
    ". The linear share is descriptive and is not a bandwidth share; details in Supplementary Sections S9–S11.\n\n" + \
    """The best-linear surrogate kept the chain's lower gain and steeper in-band roll-off (median gain
−2.22 dB over 0.5–2 kHz and a further −7.30 dB at 3.5 kHz, against 0.00 and −2.16 dB for the
control; Supplementary Table S20), yet it was no more harmful than the control (Table V):
LIN8 − LP was −0.06 pp [−0.13, +0.01] for Whisper large-v3 and −0.25 pp [−0.47, −0.04] for
wav2vec2-base-960h. The residual beyond it was +0.74 pp [+0.51, +1.00] and +2.32 pp [+1.85, +2.97]
and exceeded the linear component in both recognisers and both test subsets, meeting the
pre-declared criterion. The linear share was 0.10 (Whisper) and 0.33 (wav2vec2), against 0.17 and
0.40 along the sequential, path-dependent REF → LP → OPUS path: the exact split depends on how
linear loss is defined, but the residual did not shrink.

""" + ('With the VoIP application mode the total penalty remained positive: OPUS_VOIP8 − REF was\n+0.70 pp [+0.48, +0.95] for Whisper large-v3 and +3.44 pp [+2.71, +4.37] for wav2vec2-base-960h.\nNo clear application difference was established: OPUS_VOIP8 − OPUS was −0.12 pp [−0.25, +0.00]\nand −0.03 pp [−0.23, +0.15]. For Whisper the interval reaches zero and two secondary cells (CER;\ntest-other) excluded it, so a small reduction under the VoIP mode cannot be ruled out; no\nequivalence is claimed.\n\n') + """Recomputed without new recognition, the residual and its excess over the bandwidth component
were positive for both recognisers under corpus, mean per-utterance, equal-speaker and character
weighting, and under corpus WER in both test subsets. The shares were less stable than the contrasts: the
Whisper share ranged from 0.17 (corpus WER) to 0.28 (CER), with an interval of [0.05, 0.29] under
corpus WER, and the wav2vec2 share from 0.35 to 0.42. Two secondary cells left the ordering
unresolved (Supplementary Section S11)."""

# the reference-decoder sensitivity of the total penalty (sealed R4 outputs): total penalty only; no
# bandwidth component, share or residual under libopus; R1 remains STOPPED
R4_RESULTS = """**Decoder sensitivity.** As a post-confirmation decoder sensitivity, the same frozen 8 kbit/s Opus
bitstreams were decoded with libopus 1.4 instead of FFmpeg 6.1.1. The total Opus penalty remained
positive for both recognisers: +0.72 pp [+0.49, +0.97] for Whisper large-v3 and +3.56 pp
[+2.79, +4.54] for wav2vec2-base-960h. Relative to FFmpeg decoding, the libopus decoder reduced
Whisper WER by 0.11 pp [0.04, 0.17], whereas no clear decoder difference was established for
wav2vec2 (+0.09 pp [−0.04, +0.21]). This sensitivity tests the total penalty only; the bandwidth
decomposition remains defined for the FFmpeg chain. With FFmpeg decoding the totals were +0.83 and
+3.48 pp (Table III); checks and decoder diagnostics are in Supplementary Section S8."""
# the final invariance pass (sealed A1, B1 and C1 records): an inclusive best-linear attribution of the
# actual 8 kbit/s output (prior-art projection), the encoder application mode, and a metric audit;
# gates, thresholds and outcome labels are in Supplementary Sections S9-S11
FINAL_METHODS = """## 3.11 Sensitivity of the residual, the total and the metric (sealed after all of the above)

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

""" + ('**Encoder application mode.** The confirmatory settings used `application=audio`, as in the\npreliminary analysis, whereas real-time VoIP deployments typically use `OPUS_APPLICATION_VOIP`. A\nfurther plan changed only that encoder parameter (OPUS_VOIP8), checked the new bitstreams before\nrecognition and recognised them once; the pre-declared outcome is whether the interval of\nOPUS_VOIP8 − OPUS lies below zero, above zero or includes zero, with no equivalence margin and no\nbandwidth share.\n\n') + """**Metric and weighting robustness.** Without new recognition, the bandwidth component, the
residual, the total, their difference and the sequential share were recomputed in every
bootstrap replicate of the confirmation under four weightings (corpus WER, mean per-utterance
WER, equal-speaker WER and CER), per error type and per subset. Criteria fixed before the audit
classified each statement as robust to the weighting, weighting-sensitive, subset-dependent or,
for ratios, unstable."""

head = head.rstrip("\n") + "\n\n" + R3_METHODS + "\n\n" + FINAL_METHODS + "\n\n"

results = f"""# 4. Results

## 4.1 Pilot

The pilot (138 utterances, 69 speakers) was decoded once and analysed with the sealed code. Its
pre-declared kill test returned PROCEED: the residual interval excluded zero in both
recognisers (Supplementary Section S2, Table S2).

## 4.2 Confirmation: word error rate by condition

{T2}

{cap2}

{p42}

## 4.3 Bandwidth component and codec-specific residual

{T3}

{cap3}

{p43[0]}

{p43[1]}

{fig_components}

## 4.4 Replication across subsets, recognisers and the pilot

{p44}

## 4.5 High-rate SILK narrowband reference

{p45}

## 4.6 Error types

{p46}

## 4.7 Signal descriptors

{p47[0]}

{p47[1]}

## 4.8 Negative controls and decoder sensitivity

{p48}

{R4_RESULTS}

## 4.9 Level-matched sensitivity analysis (Addition A)

{a_para[0]}

All pre-recognition checks passed (Supplementary Section S4).

{a_result}

{a_w2v}

Decoded a second time, 3 of 4,348 Whisper hypotheses of the LP and OPUS audio differed from the
confirmatory run; the analysis uses the same-run LP and OPUS (Supplementary Section S4).

## 4.10 Bitrate sweep (Addition B)

{b_para[0]}

{b_valid}

{T6}

{cap6}

{b_result}

{fig_sweep}

{b_desc}

{R3_RESULTS}

{FINAL_RESULTS}

"""
back = SRC[find(SRC, "\n# 5. Discussion", "draft-2 section") + 1:find(SRC, "\n# Appendix A. Supplementary tables", "draft-2 section") + 1]
back = rep(back, "fidelity all changed with the rate (Table 8).", "fidelity all changed with the rate (Supplementary Table S10).")
back = rep(back, "The pre-registration is internal (sealed files and version-control commits), not in a public\nregistry.",
           "The prospective specification is internal (sealed files and version-control commits); it was\nnot lodged in a public registry.")
back = rep(back, "transfer function and validated on held-out speakers. In a pre-registered paired design,",
           "transfer function and validated on held-out speakers. In a prospectively specified,\nversion-sealed paired design,")
back = rep(back, "the Opus signal to the control did not remove it. In a pre-registered bitrate sweep on fresh\nutterances of the same speakers,",
           "the Opus signal to the control did not remove it. In a bitrate sweep on fresh utterances of the\nsame speakers, specified and sealed before decoding,")
back = rep(back, "and each decision record was sealed. Code, sealed selections,",
           "and each decision record was sealed. A later plan, sealed before any of its audio was encoded,\n"
           "added the forced-wideband counterfactual (Section 4.11); its code was frozen after a\n"
           "calibration step, the counterfactual was decoded once, and its decision record was sealed. Two\n"
           "additional attribution sensitivities were prospectively gated but stopped before ASR because\n"
           "their signal-domain controls failed held-out validation. A further sealed plan tested the\n"
           "decoder sensitivity of the total penalty; its code was frozen after a calibration dry run, the\n"
           "libopus-decoded audio was recognised once, and its decision record was sealed. Supplementary\n"
           "material gives the tables and figures moved out of this paper and the details of the later\n"
           "analyses (Tables S1–S17, Figs. S1–S3), the level-matching, bitrate-sweep and sensitivity-analysis\n"
           "diagnostics (Sections S4, S5, S7 and S8), and the amendments and deviations.\nCode, sealed selections,")
back = rep(back, "on these data. Restoring the band and\ndecoder-side enhancement were not tested.",
           "on these data. At the same nominal\n"
           "8 kbit/s, forcing wideband instead of narrowband lowered the WER of wav2vec2-base-960h but not\n"
           "detectably that of Whisper large-v3 (Section 4.11): on these data, a wideband allocation\n"
           "lowered WER for one recogniser only. The total 8 kbit/s Opus penalty persisted under the\n"
           "libopus reference decoder for both recognisers; its magnitude was lower for Whisper, while no\n"
           "clear decoder difference was established for wav2vec2, and the bandwidth decomposition itself\n"
           "remains defined for the FFmpeg decoder chain (Section 4.8). Restoring the band without changing\n"
           "the coding, as bandwidth extension would, and decoder-side enhancement were not tested.")
back = rep(back, "Estimating the interaction would need a\nfactorial design, for example Opus forced to wideband at 8 kbit/s, which was not run. The\ncontrol was fitted",
           "Estimating the interaction would need a\nfactorial design. A forced-wideband 8 kbit/s counterfactual was tested, but changing bandwidth\n"
           "allocation also changes the coding-distortion budget, so the comparison does not identify a\n"
           "factorial interaction between bandwidth loss and coding distortion. The\ncontrol was fitted")
back = rep(back, "limitation alone. Future work includes:",
           "limitation alone. At the same nominal 8 kbit/s, forcing wideband lowered WER for\n"
           "wav2vec2-base-960h but not detectably for Whisper large-v3; this practical, recogniser-dependent\n"
           "result does not estimate a bandwidth × coding interaction. Future work includes:")
back = rep(back, "**Bandwidth explains a minority of the low-rate Opus penalty.**",
           "**Bandwidth removal reproduces a minority of the low-rate Opus penalty.**")
back = rep(back, "increase caused by Opus at 8 kbit/s: 17 % for Whisper large-v3 and 40 % for\nwav2vec2-base-960h, along the REF → LP → OPUS path.",
           "increase caused by Opus at 8 kbit/s: a small share for Whisper large-v3 and 40 % for\n"
           "wav2vec2-base-960h, both path-dependent shares along the sequential REF → LP → OPUS path.")
back = rep(back, "NEG_CODEC shows that the\ncontainer, decoder", "NEG_CODEC shows that this\ncontainer, decoder")
back = rep(back, "than in how they respond to in-band coding\ndistortion.",
           "than in how they respond to the codec-specific\ndegradation beyond the control.")
back = rep(back, "or higher coding rates, target the\nlarger component.",
           "and higher coding rates are\ncandidates for the larger component, to the extent that it is coding distortion, which the\n"
           "evidence supports but does not establish.")
# limitations: path dependence, and the encoder application mode and source-audio limitations
back = rep(back, "**The decomposition.** The decomposition is sequential, so the residual includes any\n"
                 "interaction between band limitation and coding.",
           "**The decomposition.** The decomposition is sequential, so the residual includes any\n"
           "interaction between band limitation and coding, and the bandwidth share is path-dependent, not\n"
           "an interaction-free attribution.")
back = rep(back, "**Implementations.** One encoder (libopus 1.4) and one decoder (FFmpeg 6.1.1) were used. Opus\n"
                 "leaves decoder resampling to the implementation [@rfc6716], so the image and possibly the\n"
                 "residual could differ with another decoder, such as libopus's own.",
           "**Implementations.** One encoder (libopus 1.4) was used, and Opus leaves decoder resampling to the\n"
           "implementation [@rfc6716]. The primary decomposition is defined for FFmpeg 6.1.1 decoding. A\n"
           "post-confirmation sensitivity using the libopus 1.4 reference decoder showed that the total\n"
           "8 kbit/s penalty persisted for both recognisers, although its magnitude was lower for Whisper.\n"
           "Because the decoder-matched bandwidth control failed held-out validation before ASR, decoder\n"
           "invariance of the bandwidth share or codec-specific residual was not established.")
back = rep(back, "inspected, but the wideband threshold has moved over time.",
           "inspected, but the wideband threshold has moved over time. The encoder used\n"
           "`application=audio`, retained to reproduce the frozen codec baseline of the preliminary\n"
           "analysis; deployment-specific behaviour under `OPUS_APPLICATION_VOIP` was not evaluated.")
back = rep(back, "real-network conditions were not tested. The confirmation speakers",
           "real-network conditions were not tested. LibriSpeech derives from LibriVox recordings, which\n"
           "are MP3-compressed [@panayotov2015librispeech, Sec. 5], so REF is lossless relative to this\n"
           "study's manipulations but is not guaranteed to represent never-lossy-coded source speech; the\n"
           "paired within-utterance contrasts remain valid, but generalisation to pristine-source\n"
           "recordings is limited. The confirmation speakers")
back = rep(back, "**Statistics and reporting.** Per-subset results and bandwidth shares are secondary",
           "**Statistics and reporting.** Per-subset results and the path-dependent bandwidth shares are\nsecondary")
back = rep(back, "bandwidth removal accounted for 17 % (Whisper large-v3) and 40 % (wav2vec2-base-960h) of the\n"
                 "total penalty.",
           "bandwidth removal accounted for a minority of the total penalty: a small share for Whisper\n"
           "large-v3 and 40 % for wav2vec2-base-960h, both path-dependent shares along the sequential\n"
           "REF → LP → OPUS path.")
# final invariance pass: Discussion, Limitations, Conclusion and Reproducibility statement (sealed A1, B1, C1)
back = rep(back, "using a linear low-pass control fitted to SILK narrowband's measured\ntransfer function",
           "using a linear low-pass control fitted to SILK narrowband's measured\nhigh-rate transfer function")
_X_PRACTICAL, _X_IMPL, _X_CONCL = 'The total penalty also persisted when the encoder used the VoIP application mode, without a clear difference from the audio mode (Section 4.12).', 'The encoder used\n`application=audio`, retained to reproduce the frozen codec baseline of the preliminary\nanalysis, and the decomposition is defined for it. A post-confirmation sensitivity with\n`OPUS_APPLICATION_VOIP` alone showed that the total penalty persisted, without a clear\ndifference from the audio mode (not an equivalence result); FEC, DTX, packet loss and other\ndeployment settings were not tested.', 'The total penalty persisted with the libopus reference decoder and with the VoIP application mode.'
back = rep(back, "Within SILK narrowband, the bitrate sweep tested the rate dependence on fresh utterances: with\nthe signal-type hint and the decode path fixed, the residual fell from +0.55 and +2.07 pp at\n8 kbit/s to no detectable residual at 24 and 40 kbit/s (Section 4.10).",
           "Within SILK narrowband, with the signal-type hint and the decode path fixed, the residual fell\n"
           "with the coding rate on fresh utterances and was not detectable at 24 and 40 kbit/s (Section 4.10).")
back = rep(back, "At the same nominal\n8 kbit/s, forcing wideband instead of narrowband lowered the WER of wav2vec2-base-960h but not\ndetectably that of Whisper large-v3 (Section 4.11): on these data, a wideband allocation\nlowered WER for one recogniser only.",
           "Forcing wideband at\nthe same nominal 8 kbit/s lowered WER for wav2vec2-base-960h only (Section 4.11).")
back = rep(back, "**What the residual contains.** The residual is a bundle, not a mechanism: it contains in-band\ncoding distortion, the mirror image, a small level difference, a 1–2 sample lag and the codec\ndecode path. SILK and NEG_CODEC argue against some of these explaining it, but no condition\nisolates in-band distortion. Matching the broadband RMS level did not remove the residual\n(Section 4.9), but that was a post-confirmation sensitivity analysis on the same utterances, not\na second confirmatory test, and it did not equalise the level within frequency bands. The\nbitrate sweep changed in-band distortion, level and image fidelity together, so it supports but\ndoes not isolate the in-band interpretation.",
           "**What the residual contains.** The residual is a bundle, not a mechanism: it contains in-band\n"
           "coding distortion, the mirror image, a small level difference, a 1–2 sample lag and the codec\n"
           "decode path, and no condition isolates in-band distortion. Level matching was broadband and\n"
           "post-confirmation, and the bitrate sweep changed in-band distortion, level and image fidelity\n"
           "together, so both support but do not isolate the in-band interpretation.")
back = rep(back, "At the same nominal 8 kbit/s, forcing wideband lowered WER for\nwav2vec2-base-960h but not detectably for Whisper large-v3; this practical, recogniser-dependent\nresult does not estimate a bandwidth × coding interaction.",
           "Forcing wideband at the same nominal 8 kbit/s lowered WER for\n"
           "wav2vec2-base-960h only; this practical result does not estimate a bandwidth × coding interaction.")
back = rep(back, "same direction in both recognisers, in both test subsets and in an independent pilot. The\nattribution of the 8 kbit/s penalty",
           "same direction in both recognisers, in both test subsets and in an independent pilot. It did\n"
           "not depend on how linear loss is defined or on how errors are weighted: beyond a per-utterance\n"
           "best-linear projection of the actual 8 kbit/s output it was at least as large, and its excess\n"
           "over the bandwidth component held under four error weightings (Section 4.12). The\n"
           "attribution of the 8 kbit/s penalty")
back = rep(back, "residual in either recogniser (Section 4.9), so the broadband level difference does not account\nfor it.",
           "residual in either recogniser (Section 4.9), so the broadband level difference does not account\n"
           "for it. Nor does the 8 kbit/s chain's own linear response: reproduced per utterance, its lower\n"
           "gain and steeper in-band roll-off left WER no higher than the control (Section 4.12).")
back = rep(back, "residual was similar (+26 % and +31 % of the LP WER), whereas the bandwidth component still\ndiffered markedly",
           "residual was similar under WER (+26 % and +31 % of the LP WER), though not under CER, whereas the\n"
           "bandwidth component still differed markedly")
if _X_PRACTICAL:
    back = rep(back, "remains defined for the FFmpeg decoder chain (Section 4.8). Restoring the band without changing",
               "remains defined for the FFmpeg decoder chain (Section 4.8). " + _X_PRACTICAL + " Restoring the band without changing")
back = rep(back, "an interaction-free attribution. Estimating the interaction would need a\nfactorial design.",
           "an interaction-free attribution. The split also depends on how linear loss is defined: under a\n"
           "per-utterance best-linear attribution of the actual codec output, the linear share was 0.10\n"
           "(Whisper) and 0.33 (wav2vec2) instead of 0.17 and 0.40 (Section 4.12). Estimating the\n"
           "interaction would need a factorial design.")
if _X_IMPL:
    back = rep(back, "The encoder used\n`application=audio`, retained to reproduce the frozen codec baseline of the preliminary\n"
                     "analysis; deployment-specific behaviour under `OPUS_APPLICATION_VOIP` was not evaluated.",
               _X_IMPL)
back = rep(back, "relative percentages are post hoc. The negative controls imply a resolution of about 0.1 pp.",
           "relative percentages are post hoc. The shares also depend on the error weighting (the Whisper\n"
           "share ranged from 0.17 to 0.28), whereas the ordering of the two components did not\n"
           "(Section 4.12). The negative controls imply a resolution of about 0.1 pp.")
back = rep(back, "subsets and the pilot. In a post-confirmation sensitivity analysis, matching the RMS level of\nthe Opus signal to the control did not remove it.",
           "subsets and the pilot. Post-confirmation sensitivity analyses did not remove it: it remained\n"
           "after matching the RMS level of the Opus signal to the control and, at 0.74 and 2.32 pp, beyond a\n"
           "per-utterance best-linear projection of the actual 8 kbit/s output, and its excess over the\n"
           "bandwidth component held under four error weightings.")
if _X_CONCL:
    back = rep(back, "result does not estimate a bandwidth × coding interaction. Future work includes:",
               "result does not estimate a bandwidth × coding interaction. " + _X_CONCL + " Future work includes:")
back = rep(back, "- a fresh-speaker holdout on another corpus;\n- decoding with the reference decoder;",
           "- a fresh-speaker holdout on another corpus, with a recogniser of another family such as a\n  transducer;\n"
           "- a decoder-matched decomposition, which needs a bandwidth control validated for that decoder;")
back = rep(back, "Future work includes:\n\n- a manipulation that changes in-band coding distortion with level and image held fixed;\n"
                 "- a fresh-speaker holdout on another corpus, with a recogniser of another family such as a\n  transducer;\n"
                 "- a decoder-matched decomposition, which needs a bandwidth control validated for that decoder;\n"
                 "- a factorial design that estimates the interaction between bandwidth and coding.",
           "Future work includes a manipulation that changes in-band coding distortion with level\n"
           "and image held fixed; a fresh-speaker holdout on another corpus, with a recogniser of another\n"
           "family such as a transducer; a decoder-matched decomposition, which needs a bandwidth control\n"
           "validated for that decoder; and a factorial design that estimates the interaction between\n"
           "bandwidth and coding.")
back = rep(back, "the specification (conditions, encoder\nsettings, data selections, recognisers and decoding options, normalisation, metrics, bootstrap\nand decision rules) was sealed with SHA-256 hashes",
           "the specification of Section 3.1 was sealed with SHA-256 hashes")
_start = back.index("The two follow-up analyses were specified after the")
_end_marker = "and the amendments and deviations.\nCode, sealed selections,"
assert back.count("The two follow-up analyses were specified after the") == 1 and back.count(_end_marker) == 1
_end = back.index(_end_marker) + len("and the amendments and deviations.\n")
back = back[:_start] + (
    "Every later analysis (Sections 3.9, 3.10 and 3.11, and the decoder\n"
    "sensitivity of Section 4.8) was specified in its own sealed plan before any of its audio was\n"
    "encoded, had its code frozen after a calibration step, was decoded once and has a sealed decision\n"
    "record; one amendment was sealed before a freeze. Two additional attribution sensitivities were\n"
    "prospectively gated but stopped before ASR because their signal-domain controls failed held-out\n"
    "validation. Supplementary material gives the tables and figures moved out of this paper\n"
    f"(Tables S1–S{LAST_SUPP_TABLE}) and the checks, rule thresholds, outcomes, amendments and\n"
    "deviations of the later analyses.\n") + back[_end:]

main = head + results + back

# =============================================================== supplement
appA = section("Appendix A. Supplementary tables")
appB = section("Appendix B. Amendments and deviations")
pilot_text = prose(section("4.1 Pilot", "## "))[0]
pilot_text = rep(pilot_text, "(Table S4)", "(Table S2)")
S1_rows = validation.strip("\n")
capS = lambda s: appA[find(appA, s, "Appendix A caption"):].split("\n")[0]
s1 = gen_table("TABLE S1 ")
s2 = gen_table("TABLE S2 ")
s3 = gen_table("TABLE S3 ")
pilot_tab = between(appA, "| | REF | LP | OPUS |", ": Pilot") .strip("\n")
pilot_contr = appA[find(appA, "| Contrast (micro, pp) |", "Appendix A pilot table"):].split("\n\n")[0].strip("\n")
cap_pilot = capS(": Pilot")
T4a = between(s47, "| Descriptor (median vs REF) |", ": Signal descriptors").strip("\n")
cap4 = cap(": Signal descriptors on the confirmation set")
T4b = s47[find(s47, "| Pooled cross-spectral descriptor (vs REF) |", "Section 4.7 table"):].split("\n\n")[0].strip("\n")
T5full = gen_table("TABLE 5 ")
cap5 = cap(": Addition A, the level-matched sensitivity analysis")
T7full = gen_table("TABLE 7 ")
cap7 = cap(": Addition B: trend over bitrate")
T8 = gen_table("TABLE 8 ")
cap8 = cap(": Addition B: signal descriptors by rate")
S5A, S5B, S6t = gen_table("TABLE S5A "), gen_table("TABLE S5B "), gen_table("TABLE S6 ")
S13t, S14t = gen_table("TABLE S13 "), gen_table("TABLE S14 ")
S15t, S16t, S17t = gen_table("TABLE S15 "), gen_table("TABLE S16 "), gen_table("TABLE S17 ")
capS6 = capS(": Addition B: corpus WER")
fig_wer = cap("![Corpus WER by condition on the confirmation set")
fig_forest = cap("![Paired contrasts on the pilot and the confirmation set")
fig_models = cap("![Cross-recogniser comparison of the paired contrasts")
a_gates = a_para[1]
b_valid_full = rep(b_para[1], "2.3–8.0 % below nominal (Table 6);", "2.3–8.0 % below nominal (main paper, Table V);")
b_valid_full = rep(b_valid_full, " Corpus WERs by condition are in Table S6.", " Corpus WERs by condition are in Table S11.")
b_second = """The slopes on the rate rank and on the measured payload bitrate agree with the primary slope
(Table S9). The decline was concentrated at low rates. The step from 8 to 12 kbit/s was the
largest (+0.34 and +1.32 pp), and the later steps were smaller. The point estimates fell at every
step in both recognisers, and 66 % (Whisper) and 98 % (wav2vec2) of bootstrap replicates were
monotone."""
amend = prose(appB)
amend = [rep(amend[0], "result is retained (Section 3.4).", "result is retained (main paper, Section 3.4).")] + \
    [rep(amend[1], "reported in Section 4.9.", "reported in Section S4 (main paper, Section 4.9).")]

supp = f"""---
title: "Supplementary material for: How much of the ASR penalty of 8 kbit/s Opus is bandwidth loss? A decomposition with a validated bandwidth control"
author: "[Authors withheld for review]"
date: "TASLP submission version, 2026-09-27"
---

<!--
SUPPLEMENTARY MATERIAL of the TASLP submission version (taslp_submission.md): material moved out of draft 2, and the
details of the later sealed analyses (Sections S7-S11); checked with `python manuscript/tools/check_numbers.py --submission`.
-->

```{{=latex}}
\\renewcommand{{\\thetable}}{{S\\arabic{{table}}}}
\\renewcommand{{\\thefigure}}{{S\\arabic{{figure}}}}
\\renewcommand{{\\thesection}}{{S\\arabic{{section}}}}
\\suppressfloats[t]
```

This supplement gives the tables, figures and diagnostics moved out of the main paper. Sections,
tables and figures of the main paper are referred to as such; S-numbers refer to this supplement.

# S1. Validation of the bandwidth control

The control was validated on 40 unseen train-clean-100 speakers with the filter taps unchanged
(main paper, Section 3.4 and Fig. 1). All criteria passed:

{S1_rows}

: Validation of the low-pass control (LP) on 40 unseen train-clean-100 speakers, with the SILK narrowband linear reference and Opus at 8 kbit/s for comparison (no ASR).

# S2. Pilot

{pilot_text}

{pilot_tab}

{cap_pilot}

{pilot_contr}

# S3. Confirmation: additional results

Tables S3–S6 support main-paper Sections 4.2 and 4.4–4.8.

{s1}

{capS(": Per-subset WER")}

{s2}

{capS(": Error-type composition")}

{s3}

{capS(": Negative controls")}

{T4a}

{cap4}

{T4b}

# S4. Addition A: level-matched sensitivity analysis

{a_para[0]}

{a_gates}

{T5full}

{cap5}

{S5A}

: Addition A per subset (secondary scope; no multiplicity correction; 95 % speaker-bootstrap intervals): level-matched residual and effect of level matching (pp).

Per 100 reference words, the level-matched residual comprised +0.52 substitutions [+0.35, +0.71]
for Whisper and +1.79 substitutions [+1.48, +2.19] for wav2vec2. The changed hypotheses and the corrected
expectation for wav2vec2-base-960h are reported in the main paper (Section 4.9) and in Section S6.

{a_para[4]}

# S5. Addition B: bitrate sweep

{b_para[0]}

{b_valid_full} {b_second}

{T7full}

{cap7}

{T8}

{cap8}

{S6t}

{capS6}

{S5B}

: Addition B per subset (secondary scope; no multiplicity correction; 95 % speaker-bootstrap intervals): residual at 8 kbit/s (pp) and slope on log2 bitrate (pp per doubling).

# S6. Amendments and deviations

{amend[0]}

{amend[1]}

# S7. Forced-wideband counterfactual and stopped sensitivity analyses

A later plan, sealed after Additions A and B and before any of its audio was encoded, fixed the
selections, pre-recognition checks, estimands, bootstrap and outcome rules of three analyses; its
code was frozen after a calibration step.

**Forced-wideband counterfactual (main paper, Sections 3.10 and 4.11).** All pre-recognition
checks passed (bitrates and descriptors: Table S14). NB8's Ogg files and raw hypotheses were identical to those of Addition B's SILK8
for all 1,665 utterances in both recognisers. Per-subset contrasts are secondary and uncorrected
for multiplicity (Table S13); the interval for Whisper large-v3 on test-clean lay above zero
(+0.27 pp [+0.03, +0.54]), and that for wav2vec2-base-960h on test-other below zero
(−1.70 pp [−2.75, −0.65]).

{S13t}

: Forced-wideband counterfactual at 8 kbit/s (1,665 utterances of Addition B; fresh-utterance, not fresh-speaker, holdout): corpus WER (%) and WB8 − NB8 (pp), 95 % speaker-bootstrap intervals; frozen-rule outcome for pooled rows only. A practical bandwidth-allocation counterfactual, not a factorial interaction estimate.

{S14t}

: Forced-wideband counterfactual: NB8 and WB8 payload bitrate and signal descriptors against REF (medians over utterances, or pooled cross-spectral measures) and raw hypotheses (of 1,665) differing from NB8. Descriptive only.

**Stopped attribution sensitivities.** Two additional attribution sensitivities were prospectively
gated but stopped before ASR because their signal-domain controls failed held-out validation.
The held-out subset was new and signal-only (no transcripts; 40 train-clean-100 speakers, 20 female
and 20 male, one utterance each, disjoint from the calibration and filter-validation speakers). Neither control
was redesigned or refitted; the main paper's primary control, decomposition and decoder
limitation are unchanged.

- *Decoding with the libopus reference decoder.* The frozen control failed a pre-specified
  control-reuse gate against the libopus-decoded SILK narrowband response, so a decoder-matched
  control was fitted by the unchanged procedure (main paper, Section 3.4). The decoder-matched
  control failed held-out transition-shape validation: RMS difference 2.07 dB over 3.0–4.2 kHz
  (limit 1.5 dB).
- *The 8-kbit/s effective coherent-linear surrogate* (fitted to the same-frequency coherent
  response of Opus at 8 kbit/s, for an alternative attribution under a more inclusive
  same-frequency linear-loss definition; not a bandwidth control) failed held-out
  transition-shape validation: RMS difference from its target 2.04 dB (limit 1.5 dB), maximum
  8.91 dB (limit 4.0 dB).

*Post hoc and exploratory, not part of any rule:* the libopus-decoded chain has a sub-sample,
content-dependent delay (median 0.44 and 0.47 samples at 16 kHz, calibration and validation sets);
under the frozen integer alignment its linear response depended on the speaker set (largest
calibration–validation difference over 3.0–4.15 kHz: 3.61 dB, against 0.92 dB with one fixed
alignment and 0.94 dB for the FFmpeg-decoded chain). This fractional-delay diagnosis is post hoc
and exploratory; no successor analysis has been run.

**Deviations** (none changed a gate, tolerance, rule, selection or outcome): the code freeze was
sealed before the held-out signal validation, keeping the plan's order; the validation report was
sealed in three parts plus a combined report, so the decoder analysis's pre-recognition checks were
completed after it had stopped; three pre-specified descriptive items of the counterfactual
(differing-hypothesis counts, reproduction check, in-band descriptors of Table S14) were computed
afterwards from sealed outputs by a separate script, and the in-band descriptors were sealed with
the recognition outputs rather than before recognition; a pre-freeze dry run on 3 calibration
utterances was discarded.

# S8. Reference-decoder sensitivity of the total penalty

A further plan, sealed after the analyses of Section S7 and before its own decoding and
recognition, tested whether the libopus 1.4 reference decoder, instead of FFmpeg 6.1.1, changes
the total penalty OPUS − REF on the same frozen confirmation bitstreams (main paper, Section 4.8).
It tests the total penalty only: no bandwidth component, share or residual was computed under
libopus, it is not a successor to the stopped decoder analysis of Section S7, and a result without
a clear difference is not an equivalence claim. The decoder applied RFC 7845 pre-skip and end
trimming at 48 kHz, followed by the Stage 3 resampler, with no gain, alignment or filtering; only
OPUS_LIBOPUS was recognised, once. The frozen rule classifies D = OPUS_LIBOPUS − OPUS_FFMPEG by
whether its 95 % interval lies below zero (DECODER_LOWER_PENALTY), above zero
(DECODER_HIGHER_PENALTY) or includes it (NO_CLEAR_DECODER_DIFFERENCE), with no minimum effect and
Stage 3's bootstrap and seed. All pre-recognition checks passed: bitstreams byte-identical to
Stage 3's (2,174 of 2,174), no decoding error, the pre-specified output lengths, no non-finite
sample, an unchanged environment, and exact reproduction of the sealed Stage 3 calibration outputs
and of Stage 3's OPUS − REF. The same bitstreams had been decoded with the same libopus path
before, signal only, when the stopped analysis of Section S7 was checked; the new decode reproduced
it exactly, and no libopus-decoded evaluation audio had been recognised before.

{S15t}

: Reference-decoder sensitivity of the total 8 kbit/s penalty on the confirmation set (2,174 utterances, 73 speakers; pooled; 95 % speaker-bootstrap intervals with Stage 3's seed): corpus WER (%), the totals and their difference (pp), and the frozen outcome. Total penalty only: no bandwidth share or residual under libopus.

{S16t}

: Reference-decoder sensitivity per subset (secondary scope; no multiplicity correction; 95 % speaker-bootstrap intervals). The wav2vec2 test-other interval of D has a lower bound of exactly 0.00 and does not exclude zero.

{S17t}

: Reference-decoder sensitivity: descriptive decoder and signal diagnostics against REF (lag counts, per-utterance medians, pooled cross-spectral measures, and samples at or above full scale, which were passed on unchanged). No descriptor enters the rule.

The FFmpeg- and libopus-decoded signals of the same bitstream were never bit-identical; their SNR
had a median of 10.13 dB unaligned and 17.96 dB after the better one-sample shift (minimum
0.06 dB; the better shift was −1 in 2,173 utterances and +1 in one). *Transcript differences (a
post-analysis descriptive addition, not pre-specified).* Relative to OPUS_FFMPEG, 292 raw (103
normalised) Whisper transcripts and 801 raw (797 normalised) wav2vec2 transcripts of the 2,174
changed under OPUS_LIBOPUS. OPUS_LIBOPUS was recognised in a separate run whose Whisper batches
differed from Stage 3's, and greedy float16 Whisper decoding is not exactly invariant to batch
composition (Section S4: 3 of 4,348 hypotheses), so not every Whisper transcript difference can be
interpreted as a decoder effect; wav2vec2 decodes each utterance alone.

**Deviations** (none changed a gate, rule, selection or outcome): the transcript-difference counts
were computed after the analysis by a script outside the code freeze; the main paper reports this
analysis in a Results paragraph and a Discussion sentence and rewrites the Implementations
limitation, whose statement that one decoder was used no longer held, whereas the plan foresaw one
main-paper sentence and at most one added limitation sentence; and the Whisper batch-composition
component of the cross-run comparison is part of D and was not separated.
"""
# final invariance pass, supplement: the gates and rules moved out of main-paper Sections 3.9-3.10 (S4, S5, S7),
# condensed deviation lists (full records in the repository), and Sections S9-S11 (sealed A1, B1, C1 records)
supp = rep(supp, "+2.381 dB).", "+2.381 dB).\n\n"
           "Before recognition, LP and OPUS had to reproduce the confirmation audio bit for bit, the\n"
           "level-matched RMS had to equal that of LP within 0.001 dB, and the gains had to equal those\n"
           "implied by the confirmation audio within $10^{-6}$ dB. Each follow-up rule has three outcomes,\n"
           "GO, WEAKEN or FALSIFY, applied per recogniser; the combined outcome is GO or FALSIFY only if both\n"
           "recognisers agree, and WEAKEN otherwise, and a missing interval bound never satisfies GO or\n"
           "FALSIFY. With $T^\\ast$ the confirmatory OPUS − LP estimate of each recogniser, Addition A returns\n"
           "GO if the lower bound of $L$ = OPUS8_LEVEL_MATCHED − LP is above zero and the lower bound of\n"
           "$K$ = OPUS8_LEVEL_MATCHED − OPUS is above $-0.25\\,T^\\ast$, and FALSIFY if the upper bound of $K$\n"
           "is below $-0.5\\,T^\\ast$.")
supp = rep(supp, "*Fresh-utterance, not fresh-speaker, holdout: 1,665 unused test utterances of 70 of the\nconfirmation speakers.*",
           "*Fresh-utterance, not fresh-speaker, holdout: 1,665 unused test utterances of 70 of the\nconfirmation speakers.*\n\n"
           "The sweep used test utterances that the project had never encoded, decoded or recognised,\n"
           "selected from metadata only with the confirmation rule: up to 30 per speaker from every test\n"
           "speaker with an eligible unused utterance. This gave 1,665 utterances from 70 speakers\n"
           "(38 test-clean, 32 test-other; 777 and 888 utterances; 3.17 h; 31,601 reference words).")
supp = rep(supp, "of bootstrap replicates were\nmonotone.",
           "of bootstrap replicates were\nmonotone. Before recognition, encoding and decoding alone had to show that every packet at every\n"
           "rate was SILK-only narrowband with 20 ms frames, that every encoder setting read back as\n"
           "requested, and that the median payload bitrate was within ±15 % of nominal, with each rate's\n"
           "median at least 1.2 times the previous one. The rule compares the slope $S$ with\n"
           "$S^\\ast = (U^\\ast - T^\\ast)/\\log_2 5$, the slope implied by the confirmatory residuals at\n"
           "8 kbit/s ($T^\\ast$, OPUS − LP) and 40 kbit/s ($U^\\ast$, SILK − LP): GO if the lower bound of\n"
           "$R_8$ is above zero, the upper bound of $S$ is below zero and its lower bound is at or below\n"
           "$0.5\\,S^\\ast$; FALSIFY if the upper bound of $S$ is at or above zero and its lower bound is above\n"
           "$0.5\\,S^\\ast$.")
supp = rep(supp, "outcome rules of three analyses; its\ncode was frozen after a calibration step.",
           "outcome rules of three analyses; its\ncode was frozen after a calibration step. For the forced-wideband "
           "counterfactual, NB8 had to\nreproduce Addition B's SILK8 files byte for byte, every WB8 packet had to be SILK-only wideband\n"
           "with 20 ms frames, every encoder setting had to read back as requested, WB8's median payload\n"
           "bitrate had to lie within ±15 % of nominal and within ±10 % of NB8's, and WB8's pooled 4–8 kHz\n"
           "power relative to REF had to be at least −10 dB; the outcome is WB_BETTER if the interval of\n"
           "WB8 − NB8 lies below zero, WB_WORSE if it lies above zero and NO_CLEAR_DIFFERENCE otherwise.")
supp = rep(supp, "result in Addition A would be uninformative and a GO expected by construction. A dated\namendment, sealed before the freeze and before any evaluation audio was decoded, corrected that\nexpectation. The normalisation's nonzero epsilon lets gain information persist in low-variance\nchannels, so invariance is approximate, not exact, and the wav2vec2 result is interpreted\nnormally. The check was reclassified from a freeze gate to a descriptive calibration finding,\nand the failed calibration record is retained. The amendment changed no estimand, gate,\ndecision threshold, condition, selection or rule, and no code changed after the freeze. The\nthree Whisper hypotheses that differed when Addition A decoded the confirmation audio again are\nreported in Section S4 (main paper, Section 4.9).",
           "result in Addition A would be uninformative. A dated amendment, sealed before the freeze and\n"
           "before any evaluation audio was decoded, corrected that expectation (the normalisation's nonzero\n"
           "epsilon lets gain information persist in low-variance channels), reclassified the check as a\n"
           "descriptive calibration finding and retained the failed calibration record; it changed no\n"
           "estimand, gate, decision threshold, condition, selection or rule, and no code changed after the\n"
           "freeze.")
_dev7 = supp[find(supp, "**Deviations** (none changed a gate, tolerance, rule, selection or outcome): the code freeze was",
                  "S7 deviations"):].split("\n\n")[0]
supp = rep(supp, _dev7, "**Deviations** (none changed a gate, tolerance, rule, selection or outcome; full list in the\n"
                        "sealed record): the plan's order of code freeze and held-out signal validation, a validation\n"
                        "report sealed in parts, three descriptive items computed afterwards from sealed outputs, and a\n"
                        "discarded pre-freeze dry run.")
_dev8 = supp[find(supp, "**Deviations** (none changed a gate, rule, selection or outcome): the transcript-difference counts",
                  "S8 deviations"):].split("\n\n")[0]
supp = rep(supp, _dev8, "**Deviations** (none changed a gate, rule, selection or outcome; full list in the sealed\n"
                        "record): the transcript-difference counts were computed after the analysis, outside the code\n"
                        "freeze; the main paper reports the analysis in more text than the one sentence the plan foresaw;\n"
                        "and the cross-run Whisper batch component is part of D.")
A1_GATE_TEXT = "calibration median projection error −12.39 dB, tolerance 3.08 dB; validation median −11.61 dB"
_B1_SUPP = ("# S10. Encoder application mode\n\nA plan sealed after the attribution of Section S9, and committed with its calibration and code\nfreeze before any confirmation bitstream was encoded, tested whether changing only the encoder\napplication (`OPUS_APPLICATION_AUDIO` → `OPUS_APPLICATION_VOIP`) changes the total 8 kbit/s penalty\n(main paper, Sections 3.11 and 4.12). Every other setting, the Ogg writer, the FFmpeg decoder and\nthe resampler were unchanged, and the signal-type hint stayed `signal=auto`. In checks committed\nbefore recognition, the regenerated OPUS_AUDIO8 bitstreams and waveforms equalled those of the\nconfirmation for all 2,174 utterances; every OPUS_VOIP8 utterance was encoded and decoded to the\nREF length without non-finite samples; every encoder control read back as requested (application\n2048); every packet was mono, narrowband and 20 ms (all SILK); and the analysis code reproduced\nthe confirmation's contrasts. OPUS_VOIP8 was recognised once, in its own run (Whisper batch\ncomposition as in Section S4). The frozen rule classifies D_app = OPUS_VOIP8 − OPUS_AUDIO8 by\nwhether its 95 % interval lies below zero (VOIP_LOWER_PENALTY), above zero (VOIP_HIGHER_PENALTY)\nor includes it (NO_CLEAR_APPLICATION_DIFFERENCE), with no minimum effect and no equivalence\nmargin; both recognisers returned NO_CLEAR_APPLICATION_DIFFERENCE (Table S21). For Whisper\nlarge-v3 the upper bound is exactly zero, and the CER contrast and the test-other contrast\nexcluded zero (Tables S21 and S22; secondary, uncorrected). The VoIP mode changed every waveform\nat an almost unchanged bitrate, with slightly lower in-band fidelity and a weaker image copy\n(Table S23); these descriptors enter no rule, and no mechanism is inferred.\n\n{B1_S21}\n\n: Encoder application mode on the confirmation set (2,174 utterances, 73 speakers; pooled; 95 % speaker-bootstrap intervals with the confirmation's seed): corpus WER (%), the totals under the audio and VoIP application modes and their difference (pp), and the frozen outcome. Total penalty only: no bandwidth share or residual under the VoIP mode; not an equivalence test.\n\n{B1_S22}\n\n: Encoder application mode per subset (secondary scope; no multiplicity correction; pp, 95 % speaker-bootstrap intervals).\n\n{B1_S23}\n\n: Encoder application mode: payload bitrate and signal descriptors against REF (per-utterance medians or pooled cross-spectral measures), integer lags and samples at or above full scale (passed on unchanged). Descriptive only; no descriptor enters the rule.\n\n")
if _B1_SUPP:
    _B1_SUPP = _B1_SUPP.format(B1_S21=gen_table("TABLE B1 "), B1_S22=gen_table("TABLE B1S "), B1_S23=gen_table("TABLE B1D "))
S18t, S19t, S20t, S23t = gen_table("TABLE A1 "), gen_table("TABLE A1S "), gen_table("TABLE A1D "), gen_table("TABLE C1 ")
supp = supp.rstrip("\n") + "\n\n" + f"""# S9. Inclusive best-linear attribution

A plan sealed after the analysis of Section S8 specified the attribution of main-paper
Section 3.11. It was committed, with its method note, signal-only calibration, code freeze and
held-out validation, before any confirmation-set projection was computed. For each confirmation
utterance, LIN8 is the orthogonal projection of the confirmation's exact Opus waveform onto the
span of REF delayed by −256 to +255 samples (512 basis vectors), computed as in the BSS Eval
reference code with a centred delay span; no parameter was fitted or tuned. Calibration and
held-out validation each used one utterance from 40 new train-clean-100 speakers (20 female and
20 male per set; no transcripts or ASR): the projection was numerically exact, a second pass
reproduced every waveform, and the held-out projection error showed no collapse
({A1_GATE_TEXT}). Before recognition, the regenerated Opus files and waveforms equalled those of
the confirmation for all 2,174 utterances, and the analysis code reproduced the confirmation's
contrasts. LIN8 was recognised in its own run, so Whisper's batches differed from the
confirmation's (Section S4); wav2vec2 decodes each utterance alone. The frozen outcome was
ROBUST_RESIDUAL: the residual beyond LIN8 lay above zero and exceeded the linear component in
both recognisers (Table S18) and in both subsets (Table S19). The confirmation projections used
single-threaded linear algebra because of CPU contention on the shared machine; this changes
rare samples in the last bit only, and the recognised audio is the audio that passed the checks.

{S18t}

: Inclusive best-linear attribution on the confirmation set (2,174 utterances, 73 speakers; pooled; 95 % speaker-bootstrap intervals with the confirmation's seed): corpus WER of LIN8 (%), the linear component, the residual beyond it and its difference from the control (pp), the descriptive linear share beside the sequential share, and the frozen outcome. The linear share is not a bandwidth share.

{S19t}

: Inclusive best-linear attribution per subset (secondary scope; no multiplicity correction; pp, 95 % speaker-bootstrap intervals).

{S20t}

: Linear response of the 8 kbit/s chain: medians of the per-utterance best-linear filters on the calibration, validation and confirmation sets (projection error, gain over 0.5–2 kHz, response at fixed frequencies relative to that gain, and phase-slope delay), with the frozen LP control for comparison, and pooled cross-spectral measures against REF (no ASR). Descriptive only.

""" + _B1_SUPP + f"""# S11. Metric and weighting robustness

Without new recognition, the primary contrasts of main-paper Section 4.12 were recomputed from
the confirmation outputs in every bootstrap replicate (the confirmation's seed on the same
speakers) under four weightings: corpus WER, mean per-utterance WER, equal-speaker WER (the mean
of per-speaker corpus WERs) and CER. The classification criteria were fixed in the audit code
before it was run. A sign or ordering statement is robust to the weighting if its interval lies
above zero under all four pooled weightings and, under corpus WER, in both subsets; a share is
unstable if any pooled replicate has a non-positive denominator, if its corpus-WER interval has an
upper-to-lower ratio above 2, or if its point estimates differ by more than a factor of 1.5 across
weightings. The residual and its excess over the bandwidth component were robust for both
recognisers, Whisper's bandwidth component was subset-dependent (not detectable on test-clean),
the Whisper share was unstable and the wav2vec2 share robust; no pooled replicate had a
non-positive denominator. Relative to the LP WER, the residual was 26.0 % (Whisper) and 30.6 %
(wav2vec2) under corpus WER but 30.3 % and 45.6 % under CER, and the ratio of the two recognisers'
bandwidth components ranged from 4.9 (CER) to 10.0 (corpus WER). In secondary cells, the ordering
was unresolved for Whisper on test-clean under CER and for wav2vec2 on test-other under mean
per-utterance WER, and for wav2vec2 the deletions rose more with band limitation than beyond it
(residual minus bandwidth component −0.09 [−0.22, +0.02] per 100 reference words).

{S23t}

: Metric and weighting robustness of the primary contrasts on the confirmation set (pooled; pp; 95 % speaker-bootstrap intervals with the confirmation's seed): bandwidth component, residual, their difference and the sequential share under four weightings. No new recognition.
"""

OUTPUTS = {"taslp_submission.md": main.rstrip("\n") + "\n", "taslp_supplement.md": supp}

# =============================================================== guards
# every decimal number of the output (e.g. +0.35, 2.3, 1,665) must already be in draft 2 or in
# the generated tables: this script moves numbers, it never makes them. The numbers of the four
# sections it adds (3.10, 3.11, 4.11, 4.12) are exempt, but only as headings or "Section(s)" references
NEW_SECTION = r"(?:3\.10|3\.11|4\.11|4\.12)"
SECTION_REF = re.compile(rf"(?:^## |Sections?\s+)(?:\d\.\d+,\s+)*{NEW_SECTION}(?:\s+and\s+{NEW_SECTION})?", re.M)
known = SRC + "\n" + GEN
for name, text in OUTPUTS.items():
    new = sorted({n for n in re.findall(r"\d[\d,]*\.\d+|\d{1,3}(?:,\d{3})+", SECTION_REF.sub("", text))
                  if n not in known})
    if new:
        fail(f"{name}: numbers found in neither draft 2 nor the generated tables: {new}")
    for label in ("TABLE ", "pre-regist"):
        if label in text:
            fail(f"{name}: contains {label!r}")

if CHECK:
    differ = [n for n, t in OUTPUTS.items() if (MANUSCRIPT / n).read_text(encoding="utf-8") != t]
    if differ:
        fail(f"generated text differs from the file(s) on disk: {differ}")
    print("build_submission: --check PASS (both files reproduce byte for byte)")
else:
    for n, t in OUTPUTS.items():
        (MANUSCRIPT / n).write_text(t, encoding="utf-8")
    print("wrote taslp_submission.md and taslp_supplement.md")
