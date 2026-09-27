"""Build manuscript/taslp_submission.md and taslp_supplement.md from draft 2 (manuscript.md).

Presentation and submission selection: draft-2 text is moved to the supplement, shortened or
re-referenced (table, figure and section numbers), and "pre-registered" is reworded as a
prospective, version-sealed specification. The only text not taken from draft 2 reports the later
sensitivity plan (sealed R1-R3 outputs): the forced-wideband counterfactual (Sections 3.10 and
4.11, and edits to the Discussion, Limitations, Conclusion and Reproducibility statement) and
Supplementary Section S7. Every number is copied from draft 2 or from the output of
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

- Derived from draft 2 (manuscript/manuscript.md, commit dbf8d5c) by editorial restructuring only: no scientific claim,
  number or caveat was changed. Moved material is in taslp_supplement.md (supplementary material).
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
head = rep(head, "4. **Two pre-registered follow-up analyses:**", "4. **Two prospectively specified follow-up analyses:**")
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

T2, T3 = gen_table("TABLE 2 "), gen_table("TABLE 3 ")
cap = lambda s: SRC[find(SRC, s, "draft-2 caption or figure"):].split("\n")[0]
cap2 = cap(": Corpus WER (%) on the confirmation set")
cap3 = cap(": Paired contrasts on the confirmation set")
fig_components = cap("![Bandwidth component (LP − REF)")
fig_sweep = cap("![Addition B: residual beyond the linear control")
T5 = gen_table("TABLE 5 ", ["OPUS8_LEVEL_MATCHED − LP (pp; primary)", "OPUS8_LEVEL_MATCHED − OPUS (pp)", "Outcome (frozen rule)"])
T6 = gen_table("TABLE 6 ")
T7 = gen_table("TABLE 7 ", ["Slope on log2 bitrate (pp per doubling; primary)", "SILK8 − SILK40", "Outcome (frozen rule)"])
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
p44 = rep(prose(s44)[0], "(Table S1, Figs. 4 and 5)", "(Supplementary Table S3 and Figs. S2–S3)")
p45 = prose(s45)[0]
p46 = rep(prose(s46)[0], "(Table S2)", "(Supplementary Table S4)")
p47 = prose(s47)
p47[0] = rep(p47[0], "(Table 4)", "(Supplementary Table S6)")
p48 = rep(prose(s48)[0], "(Table S3)", "(Supplementary Table S5)")
p42 = rep(prose(s42)[0], "(Table 2, Fig. 2)", "(Table II; Supplementary Fig. S1)")

a_para = prose(r)                     # 0 label, 1 gates, 2 result, 3 wav2vec2, 4 clipping+reproduction
b_para = prose(r10)                   # 0 label, 1 validation, 2 result, 3 descriptors
a_result = rep(a_para[2], "recogniser (Table 5).", "recogniser (Table IV).")
a_result = rep(a_result, "recognisers. The same held in both test subsets (Table S5), and the residual was still mostly\nsubstitutions: per 100 reference words, +0.52 substitutions [+0.35, +0.71] for Whisper and\n+1.79 substitutions [+1.48, +2.19] for wav2vec2.",
               "recognisers. The same held in both test subsets, and the residual was still mostly\nsubstitutions (Supplementary Section S4, Tables S7 and S8).")
a_w2v = rep(a_para[3], "per-channel normalisation. That expectation was corrected before the code freeze: the\nnormalisation's epsilon lets gain information persist in low-variance channels (Appendix B).",
            "per-channel normalisation. That expectation was corrected before the code freeze: the\nnormalisation's epsilon lets gain information persist in low-variance channels\n(Supplementary Section S6).")
b_valid = """Validation passed before recognition: every packet at every rate was SILK-only narrowband
with 20 ms frames, every encoder setting read back as requested, and the median payload
bitrates were 2.3–8.0 % below nominal (Table V). At 8 kbit/s the sweep's `signal=voice`
encoding produced Ogg files byte-identical to those of the OPUS settings (`signal=auto`) for
all 1,665 utterances, so SILK8 − LP repeats the confirmatory OPUS − LP contrast on new
utterances (validation details: Supplementary Section S5)."""
b_result = b_para[2]
b_result = rep(b_result, "in both recognisers (Tables 6 and 7, Fig. 6).", "in both recognisers (Tables V and VI, Fig. 3).")
b_result = rep(b_result, " The slopes on the rate rank and on the measured payload bitrate agree. The\ndecline was concentrated at low rates. The step from 8 to 12 kbit/s was the largest (+0.34 and\n+1.32 pp), and the later steps were smaller. The point estimates fell at every step in both\nrecognisers, and 66 % (Whisper) and 98 % (wav2vec2) of bootstrap replicates were monotone.\n", "\n")
b_result = rep(b_result, "[+1.65, +2.67]. In the per-subset analysis (Table S5),",
               "[+1.65, +2.67]. The decline was concentrated at low rates, with the largest step between 8 and\n12 kbit/s; the secondary slopes, the adjacent-rate contrasts and the corpus WERs are in\nSupplementary Section S5 (Tables S9 and S11). In the per-subset analysis (Supplementary Table S12),")
b_desc = rep(b_para[3], "changed with the rate as well (Table 8).", "changed with the rate as well (Supplementary Table S10).")

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
SILK8 files byte for byte, every WB8 packet had to be SILK-only wideband with 20 ms frames,
every encoder setting had to read back as requested, WB8's median payload bitrate had to lie
within ±15 % of nominal and within ±10 % of NB8's, and WB8's pooled 4–8 kHz power relative to
REF had to be at least −10 dB. The primary contrast is $W$ = WB8 − NB8 per recogniser, with 95 %
speaker-bootstrap intervals (Addition B's seed on the same speakers). The outcome is WB_BETTER
if the interval lies below zero, WB_WORSE if it lies above zero and NO_CLEAR_DIFFERENCE
otherwise; no combined outcome is formed. Forcing wideband also changes SILK's internal sampling
rate, its LPC order and the allocation of the bit budget, so this is a practical
bandwidth-allocation counterfactual, not a factorial estimate of an interaction between
bandwidth loss and coding distortion, and it does not enter the decomposition. The same plan
included two attribution sensitivities that were stopped before recognition (Supplementary
Section S7)."""
R3_RESULTS = """## 4.11 Forced-wideband counterfactual

*Practical bandwidth-allocation counterfactual on the 1,665 utterances of Addition B (a
fresh-utterance, not fresh-speaker, holdout); not a factorial interaction estimate.*

All gates passed before recognition. NB8 reproduced Addition B's SILK8 files byte for byte and,
after recognition, all of its hypotheses; every WB8 packet was SILK-only wideband with 20 ms
frames; and the median payload bitrates were 7.36 (NB8) and 7.76 kbit/s (WB8). At approximately
8 kbit/s, forced wideband reduced the WER of wav2vec2-base-960h relative to forced narrowband by
0.98 pp [0.42, 1.57] (WB_BETTER).
Whisper large-v3 showed no clear difference: +0.14 pp [−0.07, +0.36] (NO_CLEAR_DIFFERENCE).
Wideband coding restored the energy above 4 kHz (pooled 4–8 kHz power relative to REF: +2.14 dB,
against −16.54 dB for NB8) but worsened in-band fidelity: median coherence with REF over
0–3.5 kHz fell from 0.623 to 0.559, and median LSD over 0–3 kHz rose from 6.19 to 6.77 dB.
Coding therefore changed with the band, so the comparison does not isolate a bandwidth × coding
interaction and does not change the decomposition. The result was recogniser-dependent and does
not show a general advantage of wideband coding at this rate (per-subset results and
descriptors: Supplementary Section S7, Tables S13 and S14)."""
head = head.rstrip("\n") + "\n\n" + R3_METHODS + "\n\n"

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

## 4.8 Negative controls

{p48}

## 4.9 Level-matched sensitivity analysis (Addition A)

{a_para[0]}

All pre-recognition gates passed: LP and OPUS reproduced the confirmation audio bit for bit for
all 2,174 utterances, and the level-matched RMS equalled that of LP within
$1.6 \\times 10^{{-8}}$ dB (diagnostics in Supplementary Section S4).

{T5}

: Addition A, the level-matched sensitivity analysis (post-confirmation; confirmation utterances decoded a second time; pooled, pp, 95 % speaker-bootstrap intervals): primary contrasts and the outcome of the pre-declared rule (Section 3.9). Full results: Supplementary Table S7.

{a_result}

{a_w2v}

The level-matched signals had more samples at or above full scale than OPUS, and the
recognisers received them unchanged. Decoded a second time, 3 of 4,348 Whisper hypotheses of the
LP and OPUS audio differed from the confirmatory run; as pre-declared, this was reported, not a
gate, and the analysis uses the same-run LP and OPUS (Supplementary Section S4).

## 4.10 Bitrate sweep (Addition B)

{b_para[0]}

{b_valid}

{T6}

{cap6}

{T7}

: Addition B: primary trend over bitrate, endpoint contrast at a fixed signal-type hint, and the outcome of the pre-declared rule (pooled, 95 % speaker-bootstrap intervals). Secondary slopes and adjacent-rate contrasts: Supplementary Table S9.

{b_result}

{fig_sweep}

{b_desc}

{R3_RESULTS}

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
           "their signal-domain controls failed held-out validation. Supplementary material gives the\n"
           "tables and figures moved out of this paper and the counterfactual's details (Tables S1–S14,\n"
           "Figs. S1–S3), the level-matching, bitrate-sweep and sensitivity-analysis diagnostics (Sections\n"
           "S4, S5 and S7), and the amendments and deviations.\nCode, sealed selections,")
back = rep(back, "on these data. Restoring the band and\ndecoder-side enhancement were not tested.",
           "on these data. At the same nominal\n"
           "8 kbit/s, forcing wideband instead of narrowband lowered the WER of wav2vec2-base-960h but not\n"
           "detectably that of Whisper large-v3 (Section 4.11), so whether a wideband allocation helps\n"
           "depends on the recogniser. Restoring the band without changing the coding, as bandwidth\n"
           "extension would, and decoder-side enhancement were not tested.")
back = rep(back, "Estimating the interaction would need a\nfactorial design, for example Opus forced to wideband at 8 kbit/s, which was not run. The\ncontrol was fitted",
           "Estimating the interaction would need a\nfactorial design. A forced-wideband 8 kbit/s counterfactual was tested, but changing bandwidth\n"
           "allocation also changes the coding-distortion budget, so the comparison does not identify a\n"
           "factorial interaction between bandwidth loss and coding distortion. The\ncontrol was fitted")
back = rep(back, "limitation alone. Future work includes:",
           "limitation alone. At the same nominal 8 kbit/s, forcing wideband lowered WER for\n"
           "wav2vec2-base-960h but not detectably for Whisper large-v3; this practical, recogniser-dependent\n"
           "result does not estimate a bandwidth × coding interaction. Future work includes:")
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
SUPPLEMENTARY MATERIAL of the TASLP submission version (taslp_submission.md). Material moved out of draft 2 without
changing any claim, number or caveat; checked with `python manuscript/tools/check_numbers.py --submission`.
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

Fig. S1 and Tables S3–S6 give the confirmation results referred to in the main paper,
Sections 4.2 and 4.4–4.8; Figs. S2 and S3 compare the contrasts across the pilot and the
confirmation, and across the two recognisers.

{fig_wer}

{s1}

{capS(": Per-subset WER")}

{s2}

{capS(": Error-type composition")}

{s3}

{capS(": Negative controls")}

{T4a}

{cap4}

{T4b}

{fig_forest}

{fig_models}

# S4. Addition A: level-matched sensitivity analysis

{a_para[0]}

{a_gates}

{T5full}

{cap5}

{S5A}

: Addition A per subset (secondary scope; no multiplicity correction; 95 % speaker-bootstrap intervals): level-matched residual and effect of level matching (pp).

Per 100 reference words, the level-matched residual comprised +0.52 substitutions [+0.35, +0.71]
for Whisper and +1.79 substitutions [+1.48, +2.19] for wav2vec2.

{a_para[3].replace("(Appendix B)", "(Section S6)")}

{a_para[4]}

# S5. Addition B: bitrate sweep

{b_para[0]}

{b_valid_full}

{T7full}

{cap7}

{b_second}

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

A later plan was specified after Additions A and B and sealed before any of its audio was
encoded. For each of its three analyses it fixed the selection, the checks to be passed before
recognition, the estimands, the bootstrap and the outcome rule; its code was frozen after a
calibration step.

**Forced-wideband counterfactual (main paper, Sections 3.10 and 4.11).** NB8's Ogg files and raw
hypotheses were identical to those of Addition B's SILK8 for all 1,665 utterances in both
recognisers. Every WB8 packet was SILK-only wideband with 20 ms frames, every encoder setting
read back as requested, and WB8 restored the 4–8 kHz band (Table S14). The per-subset contrasts
are secondary and not corrected for multiplicity (Table S13); among them, the interval for Whisper
large-v3 on test-clean lay above zero (+0.27 pp [+0.03, +0.54]), and that for wav2vec2-base-960h on
test-other below zero (−1.70 pp [−2.75, −0.65]).

{S13t}

: Forced-wideband counterfactual at 8 kbit/s on the 1,665 utterances of Addition B (a fresh-utterance, not fresh-speaker, holdout): corpus WER (%) and WB8 − NB8 (pp) with 95 % speaker-bootstrap intervals, and the outcome of the frozen rule (pooled only; per-subset rows are secondary). A practical bandwidth-allocation counterfactual, not a factorial interaction estimate.

{S14t}

: Forced-wideband counterfactual: payload bitrate and signal descriptors of NB8 and WB8 (medians over utterances, or pooled cross-spectral measures, against REF), and the number of raw hypotheses (of 1,665) that differ from NB8. Descriptive only.

**Stopped attribution sensitivities.** Two additional attribution sensitivities were prospectively
gated but stopped before ASR because their signal-domain controls failed held-out validation.
Both controls were validated on a new signal-only subset of 40 train-clean-100 speakers (20
female, 20 male, one utterance each), disjoint from the calibration and filter-validation
speakers; no transcript was read and no recognition was run.

- *Decoding with the libopus reference decoder.* The frozen control failed a pre-specified
  control-reuse gate against the libopus-decoded SILK narrowband response, so a decoder-matched
  control was fitted by the control's unchanged procedure (main paper, Section 3.4). The
  decoder-matched control failed held-out transition-shape validation: RMS difference 2.07 dB
  over 3.0–4.2 kHz (limit 1.5 dB).
- *An 8-kbit/s effective coherent-linear surrogate*: a filter fitted to the same-frequency
  coherent response of Opus at 8 kbit/s, for an alternative attribution under a more inclusive
  definition of linear loss (not a bandwidth control). The 8-kbit/s effective coherent-linear
  surrogate failed held-out transition-shape validation: RMS difference from its target 2.04 dB
  (limit 1.5 dB), maximum 8.91 dB (limit 4.0 dB).

Neither control was redesigned or refitted, and neither analysis reached recognition. The primary
control, the decomposition and the decoder limitation of the main paper are unchanged.

*Post hoc and exploratory, not part of any rule.* After both analyses had stopped, a diagnosis
indicated that the libopus-decoded chain has a sub-sample, content-dependent delay (median 0.44
and 0.47 samples at 16 kHz on the calibration and validation sets). The frozen per-utterance
integer alignment then makes the measured linear response depend on the speaker set: the largest
calibration–validation difference over 3.0–4.15 kHz was 3.61 dB with the frozen alignment,
against 0.92 dB with one fixed alignment for every utterance and 0.94 dB for the FFmpeg-decoded
chain. This fractional-delay diagnosis is post hoc and exploratory; no successor analysis has
been run.

**Deviations.** None changed a gate, tolerance, rule, selection or outcome. The code freeze was
sealed before the held-out signal validation, to keep the plan's order. The validation report was
sealed in three parts with a combined report, and the pre-recognition checks of the decoder
analysis were completed after it had stopped, because the frozen runner needs every part. Three
pre-specified descriptive items of the counterfactual (the differing-hypothesis counts, the
reproduction check and the in-band descriptors of Table S14) were not computed by the frozen
analysis; a separate script computed them afterwards from sealed outputs, and the in-band
descriptors were sealed with the recognition outputs rather than before recognition. Before the
code freeze, the pipeline was dry-run on 3 calibration utterances and the outputs were discarded.
"""
OUTPUTS = {"taslp_submission.md": main.rstrip("\n") + "\n", "taslp_supplement.md": supp}

# =============================================================== guards
# every decimal number of the output (e.g. +0.35, 2.3, 1,665) must already be in draft 2 or in
# the generated tables: this script moves numbers, it never makes them. The numbers of the two
# sections it adds (3.10, 4.11) are exempt, but only as headings or "Section(s)" references
NEW_SECTION = r"(?:3\.10|4\.11)"
SECTION_REF = re.compile(rf"(?:^## |Sections?\s+){NEW_SECTION}(?:\s+and\s+{NEW_SECTION})?", re.M)
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
