"""Build manuscript/taslp_submission.md and taslp_supplement.md from draft 2 (manuscript.md).

The submission is organised around three questions (Sections 4.2, 4.4 and 4.5): how much of the
8 kbit/s Opus penalty the validated linear control reproduces; whether the residual survives
alternative explanations (the inclusive best-linear attribution, level matching, the bitrate
sweep, the reference decoder, the encoder application mode and the error weighting); and what
changing the bandwidth allocation at the same bitrate does. Sections 1-3.8 and the primary results
are draft-2 text, restructured and re-referenced. The robustness methods and results, the
Discussion, Limitations, Conclusion, Reproducibility statement and the supplement are written here
from the sealed records of the later analyses (Additions A and B, R1-R4, A1, B1, C1). Gate
mechanics, rule thresholds and outcome labels are in the supplement; full hashes, manifests and
logs are in the repository. Every number is copied from draft 2 or from the output of
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


def prose(sec):
    """A section's paragraphs without its tables, captions and figures."""
    keep = []
    for para in sec.split("\n\n")[1:]:
        if para.startswith(("|", ": ", "![")) or not para.strip():
            continue
        keep.append(para.strip("\n"))
    return keep


# =============================================================== main paper: Sections 1-3.8 (draft 2)
TITLE = "Bandwidth Removal Reproduces Only Part of the ASR Penalty of 8-kbit/s Opus"   # authors' choice (packaging pass)
head = SRC[:find(SRC, "\n# 4. Results", "draft-2 section") + 1]
head = rep(head, 'title: "How much of the ASR penalty of low-rate Opus is bandwidth loss? A decomposition with a validated bandwidth control"',
           f'title: "{TITLE}"')
head = rep(head, 'date: "Draft 2, 2026-09-27"', 'date: "TASLP submission version, 2026-09-28"')
# final author block as supplied by the author (IEEE SPS review is single-blind): one author, who is the
# corresponding author; no funding. The affiliation is the institution of the supplied e-mail address.
AUTHORS = "Jinghang Mei"
AUTHOR_BLOCK = (AUTHORS + r"\thanks{This work received no funding. (Corresponding author: Jinghang Mei.)}"
                r"\thanks{J. Mei is with the School of Electrical and Computer Engineering, The University of Sydney, Sydney, NSW 2006, Australia "
                r"(e-mail: jmei0175@uni.sydney.edu.au).}")
head = rep(head, 'author: "[Authors withheld for review]"', "author: '" + AUTHOR_BLOCK + "'")
head = rep(head, "**Index Terms**: speech recognition, speech coding, Opus, bandwidth limitation, robustness,\nWhisper, wav2vec 2.0",
           "**Index Terms**: automatic speech recognition, speech coding, Opus, bandwidth limitation, robust\nspeech recognition")
comment = between(head, "<!--", "-->\n") + "-->\n"
head = rep(head, comment, """<!--
TASLP submission version (generated file; edit tools/build_submission.py and rebuild)

- Built from draft 2 (manuscript/manuscript.md, commit dbf8d5c) by tools/build_submission.py: draft-2 text for
  Sections 1-3.8 and the primary results, plus text and tables of the later sealed analyses (Additions A and B,
  R1-R4, A1, B1, C1) taken from sealed records. Supporting material is in taslp_supplement.md.
- Every table row and number of both files is checked against the frozen outputs by
  `python manuscript/tools/check_numbers.py --submission`; render with tools/render_ieee.sh taslp_submission.md.
-->
""")

# the abstract (SPS limit 150-250 words): problem, primary result, residual, one robustness summary
ABSTRACT = """Low-bitrate narrowband codecs remove bandwidth and introduce other distortions at the same time,
which makes their penalty on automatic speech recognition (ASR) hard to attribute. We quantify this
for Opus at 8 kbit/s (SILK narrowband in libopus 1.4) with a zero-phase low-pass control fitted to
SILK narrowband's measured high-rate linear transfer function and validated on unseen speakers. In
a paired design specified before any evaluation audio was decoded (a pilot,
then one confirmatory run on 2,174 LibriSpeech test utterances from 73 speakers), removing the
bandwidth with the control increased corpus WER by 0.14 percentage points (pp) for Whisper
large-v3 and 1.40 pp for wav2vec2-base-960h, whereas Opus added a further 0.69 and 2.07 pp
(95 % speaker-bootstrap intervals excluding zero): the control reproduced only a minority of the
penalty. A more inclusive best-linear sensitivity analysis, which assigns the gain, spectral tilt,
roll-off, phase and delay of the actual codec output to the linear component, still left residual
penalties of 0.74 and 2.32 pp. The residual also exceeded the bandwidth component under four error
weightings, although the exact share, particularly for Whisper, depends on the attribution path and
the metric. Level matching, a bitrate sweep, and decoder and application-mode sensitivities further
constrain, but do not identify, the mechanism."""
head = rep(head, between(head, "# Abstract\n\n", "\n\n**Index Terms**"), "# Abstract\n\n" + ABSTRACT)

# introduction: the three questions and four contributions
INTRO_AIM = """This paper measures it. A zero-phase linear low-pass filter reproduces the linear band
limitation of SILK narrowband; it is fitted to the codec's measured high-rate transfer function and
validated on held-out speakers before any recognition experiment. The control separates the
penalty of Opus at 8 kbit/s into a bandwidth component (control minus original) and a
codec-specific residual (Opus minus control); because the decomposition is sequential, the
bandwidth share it yields is path-dependent. Both components are estimated for Whisper
large-v3 [@radford2023whisper] and wav2vec2-base-960h [@baevski2020wav2vec], evaluated without
adaptation on identical, paired audio, in a design specified before any evaluation audio was decoded
(Section 3.1). The paper asks three questions: how much of the penalty the validated control
reproduces (Section 4.2), whether the residual survives reasonable alternative explanations
(Section 4.4), and what changing the bandwidth allocation at the same bitrate does (Section 4.5).
The contributions are:

1. **A measured, independently validated linear control** that isolates the high-rate linear response of SILK narrowband: a linear-phase low-pass filter fitted to the codec's measured transfer function and validated on held-out speakers against pre-specified tolerances.
2. **A paired, prospectively specified decomposition of the 8 kbit/s Opus penalty** into a bandwidth component and a codec-specific residual for two fixed pretrained recognisers, with speaker-cluster bootstrap intervals and negative controls.
3. **Targeted robustness tests:** the codec-specific residual survives a more inclusive best-linear attribution of the actual codec output, RMS level matching and alternative error weightings, and its dependence on the coding rate is quantified; separate sensitivity analyses quantify how the decoder implementation and the encoder application mode affect the total 8 kbit/s penalty.
4. **A low-rate bandwidth-allocation counterfactual** at the same nominal bitrate, which shows recogniser-dependent trade-offs between spectral coverage and coding fidelity.
"""
head = rep(head, between(head, "This paper measures it.", "\n# 2. Related work"), INTRO_AIM)
head = rep(head, "cost of the linear band limitation itself.",
           "cost of the linear band limitation itself. As a sensitivity to the attribution definition, we adapt\n"
           "their orthogonal-projection framework to the codec output (Section 3.9). The two analyses ask\n"
           "different questions: the control, how much of the penalty the independently validated high-rate\n"
           "SILK narrowband linear response reproduces; the adaptation, whether a residual remains when the\n"
           "gain, tilt, roll-off, phase and delay that best linearly explain the actual 8 kbit/s output are\n"
           "assigned to the linear component.")
head = rep(head, between(head, "**Position of this study.**", "\n\n# 3. Methods"),
           "**Position of this study.** The Opus–ASR studies we located report total penalties. The design\n"
           "here follows the bandwidth-versus-codec comparisons above, and cutoff-matched low-pass controls\n"
           "are prior art [@borsky2015mp3]. It differs from them in the codec (one whose audio bandwidth the\n"
           "encoder selects from the bitrate), in the control (fitted to the codec's measured linear transfer\n"
           "response rather than to a cutoff, and validated on held-out speakers), in the recognisers (fixed\n"
           "pretrained models of two architectures), in the evaluation (paired and prospectively specified,\n"
           "with speaker-level intervals), and in a separate best-linear attribution\n"
           "sensitivity (Section 3.9).")

# methods 3.1-3.8: wording, references and procedural condensation
head = rep(head, "The effect of speech coding on ASR has been studied since low-rate coders entered telephone\n"
                 "networks. Error rates rise as the coding rate falls [@euler1994influence; @lilly1996effect;\n"
                 "@hirsch2002influence], codec effects differ between recognisers [@moller2002analytic], and\n"
                 "standards bodies considered them large enough to evaluate distributed front-ends as an\n"
                 "alternative to the voice codec [@3gpp2004tr26943].",
           "The effect of speech coding on ASR has been studied since low-rate coders entered telephone\n"
           "networks (Section 2), and standards bodies considered it large enough to evaluate distributed\n"
           "front-ends as an alternative to the voice codec [@3gpp2004tr26943].")
# the unpublished preliminary analysis is not part of the Introduction (its numbers stay in draft 2, checked
# there); Methods name it where its provenance and exclusions matter (Section 3.1 onwards)
head = rep(head, " Our preliminary\nanalysis raised the same question. It used wav2vec2-base-960h on other LibriSpeech test\n"
                 "utterances with a different scoring convention and is context only: WER on test-other rose by\n"
                 "1.33 pp at 12 kbit/s but by 6.63 pp at 8 kbit/s, where libopus switches from wideband to\nnarrowband SILK.",
           "")
head = rep(head, "## 3.1 Overview and pre-registration", "## 3.1 Overview and prospective specification")
head = rep(head, "A 20-utterance calibration set (4\ndev-clean speakers) was used only to check that decoding succeeded, was deterministic and had\n"
                 "adequate throughput; it computed no condition comparison.",
           "A 20-utterance calibration set (4\ndev-clean speakers) served only for decoding checks and computed no condition comparison.")
head = rep(head, "a hash-stamped specification was sealed\nand committed to version control. It fixed the data selections,",
           "a hash-stamped specification was committed\nto version control; it is internal and was not lodged in a public registry. It fixed the data\nselections,")
head = rep(head, "The pilot was decoded once; a pre-declared kill test was\napplied, and the analysis code was then sealed again. "
                 "The confirmation set was decoded once,\nwithout restarts, and analysed with the frozen code.",
           "The pilot was decoded once and assessed with a pre-declared stopping rule; the analysis code was\n"
           "then fixed and committed again, and the confirmation set was decoded once, without restarts, and\n"
           "analysed with that code.")
head = rep(head, "One amendment, recorded before the\nconfirmation, was presentation-only (marker shapes in one figure). The processing pipeline\n"
                 "reproduced an earlier analysis exactly (250/250 checks), and the codec and filter controls\n"
                 "described below were validated in two earlier stages that used no ASR output. After the\n"
                 "confirmatory analysis was closed, a second specification for two follow-up analyses (Section\n"
                 "3.9) was sealed and committed before any of their audio was encoded or decoded. Their code was\n"
                 "frozen after a check on the calibration set, and each was decoded once. Neither changes any\n"
                 "confirmatory estimate or decision.",
           "The processing pipeline\nreproduced an earlier, unpublished preliminary analysis exactly (250/250 checks), and the codec and filter controls\n"
           "described below were validated in two earlier stages that used no ASR output.")
head = rep(head, "Exclusions were fixed at selection time from metadata\nonly:\n\n- utterances longer than 30 s (Whisper's input window);\n"
                 "- utterances with an empty normalised reference;\n- the development utterances used for the controls;\n"
                 "- for the confirmation set, the 1,000 utterances of the preliminary analysis. The confirmation utterances had therefore never been decoded in this project, although their speakers are the same test speakers.\n\n"
                 "No utterance was excluded after decoding.",
           "Exclusions were fixed at selection time from metadata\nonly: utterances longer than 30 s (Whisper's input window), utterances with an empty normalised\n"
           "reference, the development utterances used for the controls and, for the confirmation set, the\n"
           "1,000 utterances of the preliminary analysis, so the confirmation utterances had never been\n"
           "decoded in this project, although their speakers are the same test speakers. No utterance was\n"
           "excluded after decoding.")
head = rep(head, "OPUS\nreproduces the encoder configuration of the preliminary analysis. In an earlier validation on\n"
                 "40 dev-clean utterances, its packets were byte-identical to those of that analysis's encoding\n"
                 "path; this identity was not re-verified on the test utterances. At 8 kbit/s, libopus 1.4\n"
                 "selects narrowband automatically [@libopus14], so forcing narrowband produced the same packets\n"
                 "as automatic selection in that validation (40/40).",
           "OPUS\nreproduces the encoder configuration of the preliminary analysis (byte-identical packets on 40\n"
           "dev-clean utterances; not re-verified on the test utterances). At 8 kbit/s, libopus 1.4 selects\n"
           "narrowband automatically [@libopus14]; forcing it gave the same packets (40/40).")
# journal wording for one cell of the conditions table (check_numbers.py maps it back to the draft-2 row)
head = rep(head, "| LP | Frozen zero-phase low-pass control (Section 3.4) | — | — |",
           "| LP | Fixed zero-phase low-pass control (Section 3.4) | — | — |")
validation = between(head, "| Measure | Control | Reference / other |", "![Validation of the low-pass")
head = rep(head, validation, "")
head = rep(head, "frozen before the confirmation data were downloaded. On the confirmation set, 40 unseen\ntrain-clean-100",
           "fixed before the confirmation data were downloaded. On an independent filter-validation set of\n40 unseen train-clean-100")
head = rep(head, "drawn from the frozen confirmation curves of the control's validation.",
           "drawn from the curves recorded in the control's held-out validation.")
head = rep(head, "train-clean-100 speakers (20 female, 20 male) with the filter taps unchanged, all criteria\npassed (Fig. 1):\n",
           "train-clean-100 speakers (20 female, 20 male) with the filter taps unchanged, all criteria\npassed (Fig. 1; the measured values are in Supplementary Table S1).\n")
head = rep(head, "The level-matched condition of Addition A (Section 3.9) is the only condition to\nwhich a gain was applied.",
           "The level-matched condition of Section 3.9 is the only condition to which a\ngain was applied.")
head = rep(head, "\n**Relation to earlier controls.** The nearest precedent in the ASR literature matched only the\n"
                 "cutoff of each codec bitrate [@borsky2015mp3]. The control here is fitted to the full measured\n"
                 "linear response and validated on held-out speakers.\n", "")
head = rep(head, "Beam search was measured\nat 2–7.5 s per utterance on the shared GPU before any evaluation decoding, and was replaced by\n"
                 "greedy decoding at that point; greedy output was deterministic across repeats and identical\n"
                 "between batched and unbatched decoding on the calibration set. Section 4.9 reports three Whisper\n"
                 "hypotheses that differed when the same audio was decoded again in batches of a different\ncomposition.",
           "Greedy decoding replaced\nbeam search before any evaluation decoding, for compute reasons.")
head = rep(head, "is therefore a share along this path.",
           "is therefore a path-dependent share along this path, not an interaction-free attribution.")
# the decision rules in words; the outcome labels of the specification are given in Supplementary Section S3
head = rep(head, between(head, "**Decision rules (sealed before decoding).**", "\n\n## 3.8 Signal descriptors"),
           "**Decision rules (specified before decoding).** The study was to proceed past the pilot only if a\n"
           "residual interval lay above zero for some recogniser and codec condition. The primary confirmatory\n"
           "criterion required, for some codec condition, a residual interval above zero and an estimate of at\n"
           "least 0.5 pp in both recognisers, and positive pilot estimates in both. Weaker, null and\n"
           "inconclusive outcomes were also defined, and a negative control whose interval excluded zero with\n"
           "an estimate above 0.5 pp in magnitude would have made a positive outcome inconclusive\n"
           "(Supplementary Section S3). Error types and exploratory correlations were to be analysed only if a\n"
           "residual survived.")
head = head.replace("(Table 1)", "(Table I)")
# the rate-dependent part of the chain's linear-looking attenuation belongs to component (iii); the inclusive
# best-linear attribution of Section 3.9 assigns it to the linear side (Fig. 1 shows it)
head = rep(head, "and (iii) bitrate-dependent coding distortion\nwithin the retained band.",
           "and (iii) bitrate-dependent coding distortion\nwithin the retained band, including the additional attenuation within the band and at the band\n"
           "edge that appears at low rates (Fig. 1).")

# methods 3.9-3.10: the later analyses, organised by the question they answer (replaces draft-2 3.9)
METHODS_LATER = r"""## 3.9 Robustness analyses (specified after the confirmation)

Each analysis in this section and in Section 3.10 was specified in its own plan after the
confirmatory analysis was closed, committed to version control before any of its audio was encoded,
run once and analysed with the confirmation's speaker-cluster bootstrap (10,000 replicates). These post-confirmation
analyses can qualify the confirmatory result but not strengthen it; their pre-recognition checks,
rule thresholds and outcomes are in the supplement.

**Inclusive best-linear attribution.** The control reproduces SILK narrowband's high-rate linear
response, whereas the 8 kbit/s chain has its own, lossier linear response. To test whether the
residual is linear loss that the control leaves out, we adapted the orthogonal-projection
framework used for speech-enhancement output [@iwamoto2022artifacts; @ochiai2024rethinking] to the
codec output, with REF as the only source and the study's pre-specified centred delay span instead
of the causal span of the original. For each confirmation utterance, the decoded 8 kbit/s Opus waveform was projected
onto the span of REF delayed by −256 to +255 samples, that is, onto everything a 512-tap filter
applied to REF can produce. The projection, LIN8, is the part of the Opus output that one
time-invariant linear filter per utterance reproduces from REF, including gain, spectral tilt,
band-edge roll-off, phase and delay; the remainder, OPUS − LIN8, contains what no such filter
reproduces, such as time-varying coding error, the 4–5 kHz mirror image and nonlinear distortion.
LIN8 was itself recognised, so the linear component is LIN8 − REF and the residual beyond it is
OPUS − LIN8. Unlike the control, which is one fixed filter measured at 40 kbit/s, the projection is
fitted to each utterance's actual 8 kbit/s output; it is an attribution, not a codec model, and it
has no free parameter. The pre-declared criterion for a robust residual is that OPUS − LIN8 lies above
zero and exceeds LIN8 − REF in both recognisers. This is a sensitivity to the attribution
definition: it does not replace the sequential decomposition, and its linear share is not a
bandwidth share.

**Level matching.** The decoded Opus signal was about 0.6 dB quieter than LP (Section 3.3). The
confirmation utterances were decoded again with the Opus waveform multiplied by one scalar gain per
utterance, $g_u = \mathrm{RMS}(\mathrm{LP}_u)/\mathrm{RMS}(\mathrm{OPUS}_u)$, and nothing else. The
primary contrast is OPUS8_LEVEL_MATCHED − LP; the pre-declared criterion also required that level
matching remove less than a quarter of the confirmatory residual.

**Coding rate.** On 1,665 test utterances that the project had never decoded, narrowband was forced
with a fixed signal-type hint (`signal=voice`) at 8, 12, 16, 24 and 40 kbit/s (SILK8–SILK40), and
every other setting, the decoder and the resampler were held fixed. This is a fresh-utterance, not
fresh-speaker, holdout: the 70 speakers are confirmation speakers, and REF was not recognised. The
primary quantity is the ordinary least-squares slope of the residual $R_b$ = SILK$b$ − LP on
$\log_2 b$, in pp per doubling of bitrate; the pre-declared criterion is a residual at 8 kbit/s
that declines with rate, with a slope interval that reaches at least half the slope implied by the
confirmatory residuals at 8 and 40 kbit/s.

**Decoder and application mode.** Two analyses changed one element of the codec chain and measured
the total penalty only: the confirmation bitstreams were decoded again with the libopus 1.4
reference decoder instead of FFmpeg 6.1.1, and the encoder was run with `OPUS_APPLICATION_VOIP` instead of
`application=audio`, with every other setting, including the automatic signal-type hint,
unchanged. For each, the pre-declared outcome is whether the interval of the difference from the
primary chain lies below zero, above zero or includes zero. No equivalence margin was declared, and
no bandwidth component or share is computed under either change.

**Error weighting.** Without new recognition, the bandwidth component, the residual and their
difference were recomputed in every bootstrap replicate under four weightings: corpus WER
(primary), mean per-utterance WER, equal-speaker WER and CER. Criteria fixed before the audit
classified each statement as robust to the weighting or not, and each share as stable or unstable.

## 3.10 Bandwidth-allocation counterfactual (specified after the confirmation)

At the same nominal 8 kbit/s, does spending the bits on wideband instead of narrowband change WER?
On the 1,665 utterances of the bitrate sweep, NB8 has the confirmatory OPUS settings (forced
narrowband, `signal=auto`) and WB8 the same settings with wideband forced; the decoder and the
resampler are unchanged. The primary contrast is WB8 − NB8 per recogniser, and the pre-declared
outcome is whether its interval lies below zero, above zero or includes zero. Forcing wideband also
changes SILK's internal sampling rate, its LPC order and the allocation of the bit budget, so this
is a practical bandwidth-allocation counterfactual, not a factorial estimate of an interaction
between bandwidth loss and coding distortion, and it does not enter the decomposition.
"""
head = head[:find(head, "## 3.9 Follow-up analyses (sealed after the confirmation)", "draft-2 section 3.9")] + METHODS_LATER + "\n"

# =============================================================== main paper: results
T2, T3, T6, T10 = gen_table("TABLE 2 "), gen_table("TABLE 3 "), gen_table("TABLE 6 "), gen_table("TABLE 10 ")
# corner labels of the header rows named after the project's history ("addition B") are renamed for the reader;
# check_numbers.py verifies the other header cells and every data row
corner = lambda tab, old, new: rep(tab, "| " + old + " |", "| " + new + " |")
T6 = corner(T6, "Condition (addition B)", "Condition (bitrate sweep)")
cap = lambda s: SRC[find(SRC, s, "draft-2 caption or figure"):].split("\n")[0]
cap2 = cap(": Corpus WER (%) on the confirmation set")
cap3 = rep(cap(": Paired contrasts on the confirmation set"), "with 95 % speaker-bootstrap intervals.",
           "with 95 % speaker-bootstrap intervals. Bandwidth shares (LP − REF divided by OPUS − REF or SILK − REF) are sequential and path-dependent.")
cap6 = rep(cap(": Addition B, the forced SILK narrowband bitrate sweep"), ": Addition B, the forced SILK narrowband bitrate sweep",
           ": Bitrate sweep of forced SILK narrowband")
cap6 = rep(cap6, "(fresh-utterance, not fresh-speaker, holdout;", "(fresh-utterance holdout;")   # defined in Section 3.9
fig_components = cap("![Bandwidth component (LP − REF)")
fig_sweep = rep(cap("![Addition B: residual beyond the linear control"), "![Addition B: residual beyond the linear control",
                "![Bitrate sweep: residual beyond the linear control")
fig_sweep = rep(fig_sweep, " (a fresh-utterance, not fresh-speaker, holdout)", "")
CAP10 = (": Post-confirmation robustness analyses (pooled, pp, 95 % speaker-bootstrap intervals). Residual: beyond a linear "
         "component; total: the total 8 kbit/s penalty; change in total: the difference between two codec chains. The first "
         "six rows use the 2,174 confirmation utterances, the last row the 1,665 utterances of the bitrate sweep.")

p42 = rep(prose(section("4.2 Confirmation: word error rate by condition", "## "))[0], "(Table 2, Fig. 2)", "(Table II)")
p42 = rep(p42, " No condition produced an empty hypothesis.", "")
p43 = prose(section("4.3 Bandwidth component and codec-specific residual", "## "))
p43[0] = rep(p43[0], "(Table 3)", "(Table III)")
p43[0] = rep(p43[0], "Along the REF → LP → OPUS path, bandwidth\nremoval therefore accounted for 17 % [5, 29]",
             "Along the sequential REF → LP → OPUS path,\nbandwidth removal therefore accounted for a path-dependent share of 17 % [5, 29]")
p43[0] = rep(p43[0], "total Opus penalty (Fig. 3).",
             "total Opus penalty (Fig. 2). These shares are sequential attributions, not causal fractions, and\n"
             "both depend on the definition of linear loss (Section 4.4). The Whisper ratio is imprecise and is\n"
             "not invariant to the attribution definition or error weighting.")
p43[0] = rep(p43[0], "The macro estimates and CER point the same way;", "For both components, the macro estimates and CER point the same way;")
p43[0] = rep(p43[0], "The pre-declared\nrule returned GO for the Opus residual.",
             "The Opus residual\nmet the pre-declared primary criterion (Section 3.7).")
p43[1] = rep(p43[1], "about three times, and its\nbandwidth component about ten times, those of Whisper large-v3. Relative to each recogniser's\n"
                     "own baseline, the residual was similar: +26.0 % and +30.6 % of the LP WER.",
             "about three times, and its\nbandwidth component five to ten times (depending on the error weighting; Section 4.4), those of\n"
             "Whisper large-v3. Relative to each recogniser's own baseline, the residual was similar under WER,\n"
             "+26.0 % and +30.6 % of the LP WER, but not under CER (+30.3 % and +45.6 %).")
p44 = rep(prose(section("4.4 Replication across subsets, recognisers and the pilot", "## "))[0], "(Table S1, Figs. 4 and 5)",
          "(Supplementary Table S3)")
p45 = rep(prose(section("4.5 High-rate SILK narrowband reference", "## "))[0],
          " Across the two\nrecognisers, the intervals lie between −0.20 and +0.08 pp.", "")
p46 = rep(prose(section("4.6 Error types", "## "))[0], "(Table S2)", "(Supplementary Table S4)")
p47 = prose(section("4.7 Signal descriptors", "## "))
# the prose values are relative to LP (09_signal_summary.csv, vs_lp_* fields); Table S6 gives the
# independently computed values relative to REF (vs_ref_* fields), which round to the same figures
p47[0] = rep(p47[0], "Compared with LP, the Opus 8 kbit/s signal differed mainly within the retained band (Table 4).\n"
                     "Median LSD over 0–3 kHz was 6.14 dB, and median coherence over 0–3.5 kHz was 0.623; SILK at\n"
                     "40 kbit/s showed 1.37 dB and 0.993.",
             "Compared with LP, the Opus 8 kbit/s signal differed mainly within the retained band: relative to\n"
             "LP, median LSD over 0–3 kHz was 6.14 dB and median coherence over 0–3.5 kHz 0.623, against\n"
             "1.37 dB and 0.993 for SILK at 40 kbit/s (relative to REF, the medians are the same to the\n"
             "precision shown; Supplementary Table S6).")
p48 = rep(prose(section("4.8 Negative controls", "## "))[0], "(Table S3)", "(Supplementary Table S5)")

ROBUSTNESS = r"""**Inclusive best-linear attribution.** The best-linear component of the actual 8 kbit/s output kept
the chain's lower gain and steeper in-band roll-off: its median gain over 0.5–2 kHz was −2.22 dB,
and its response at 3.5 kHz relative to that gain was −7.30 dB, against 0.00 and −2.16 dB for the
control (Supplementary Table S10). Yet it was no more harmful than the control: LIN8 − LP was
−0.06 pp [−0.13, +0.01] for Whisper large-v3 and −0.25 pp [−0.47, −0.04] for wav2vec2-base-960h.
The residual beyond the best-linear component was +0.74 pp [+0.51, +1.00] and +2.32 pp
[+1.85, +2.97] (Table IV); it exceeded the linear component in both recognisers, which met the
pre-declared criterion, and in both test subsets. Under this attribution the linear share of the total
was 0.10 (Whisper) and 0.33 (wav2vec2), against 0.17 and 0.40 along the sequential, path-dependent
REF → LP → OPUS path: the exact attribution changed, but the residual did not disappear.

**Level matching.** Matching the RMS level of the Opus signal to the control did not remove the
residual: +0.70 pp [+0.47, +0.95] (Whisper large-v3) and +2.09 pp [+1.71, +2.57]
(wav2vec2-base-960h) remained, and level matching itself changed WER by +0.012 pp [−0.007, +0.032]
and +0.018 pp [−0.028, +0.062]. The pre-declared criterion was met in both recognisers
(Supplementary Section S4).

**Coding rate.** Within forced SILK narrowband, the residual beyond the control decreased as the
bitrate rose, in both recognisers (Table V, Fig. 3). At 8 kbit/s it was +0.55 pp [+0.37, +0.74]
(Whisper large-v3) and +2.07 pp [+1.65, +2.55] (wav2vec2-base-960h), close to the confirmatory
+0.69 and +2.07 pp on different utterances. Neither 24 nor 40 kbit/s showed a detectable residual
relative to LP individually, although for wav2vec2 their paired 24–40 kbit/s contrast resolved a
smaller difference (+0.10 pp [+0.007, +0.20]; Supplementary Table S8). The slope on log2 bitrate was −0.206 pp per doubling [−0.267, −0.146] for Whisper and −0.854
[−1.074, −0.657] for wav2vec2, which met the pre-declared criterion in both recognisers; with the
signal-type hint fixed, SILK8 − SILK40 was +0.52 pp [+0.36, +0.68] and +2.13 pp [+1.65, +2.67].
For Whisper, the 8 kbit/s residual was concentrated in test-other (+0.95 pp [+0.65, +1.28]; on
test-clean +0.11 pp [−0.04, +0.27]). In-band fidelity relative to LP improved with the rate (median
LSD over 0–3 kHz from 6.19 to 1.37 dB; coherence from 0.623 to 0.993), but the level deficit and
the image fidelity changed as well (Supplementary Section S5), so the sweep shows that the residual
depends on the coding rate, not which rate-dependent property produces it.

__T6__

__CAP6__

__FIG_SWEEP__

**Decoder.** When the confirmation bitstreams were decoded with the libopus 1.4 reference decoder
instead of FFmpeg 6.1.1, the total penalty remained positive for both recognisers:
+0.72 pp [+0.49, +0.97] for Whisper large-v3 and +3.56 pp [+2.79, +4.54] for wav2vec2-base-960h;
with FFmpeg decoding the totals were +0.83 and +3.48 pp. Relative to FFmpeg decoding, the libopus
decoder reduced Whisper WER by 0.11 pp [0.04, 0.17], whereas no clear decoder difference was
established for wav2vec2 (+0.09 pp [−0.04, +0.21]). The decoder implementation thus affects the
magnitude for Whisper, and the total penalty is not an artefact of FFmpeg decoding alone. The
bandwidth decomposition remains defined for the FFmpeg chain, and no decoder-invariant residual or
share is claimed.

**Application mode.** With `OPUS_APPLICATION_VOIP` instead of `application=audio`, the total penalty
remained positive: +0.70 pp [+0.48, +0.95] (Whisper large-v3) and +3.44 pp [+2.71, +4.37]
(wav2vec2-base-960h). No clear application-mode difference was established: VoIP minus audio was
−0.12 pp [−0.25, +0.00] and −0.03 pp [−0.23, +0.15]. For Whisper the interval reaches zero and two
secondary cells (CER; test-other) excluded it, so a small reduction under the VoIP mode is not
ruled out; no equivalence is claimed.

**Error weighting.** The residual remained positive and larger than the primary bandwidth component
under all four tested error weightings; the exact share, especially for Whisper, was not invariant.
The ordering held for both recognisers and, under corpus WER, in both test subsets; the Whisper
share ranged from 0.17 (corpus WER) to 0.28 (CER), and the wav2vec2 share from 0.35 to 0.42
(Supplementary Section S8).

**Stopped analyses.** Two additional attribution sensitivities were prospectively gated but stopped
before ASR because their signal-domain controls failed held-out validation. A bandwidth control
matched to the libopus decoder and a surrogate of the coherent linear response at 8 kbit/s both
failed the pre-specified transition-shape criterion (Supplementary Section S9); neither was refitted."""
ROBUSTNESS = ROBUSTNESS.replace("__T6__", T6).replace("__CAP6__", cap6).replace("__FIG_SWEEP__", fig_sweep)

ALLOCATION = """On the 1,665 utterances of the bitrate sweep, NB8 reproduced SILK8's files and hypotheses, and the
median payload bitrates were 7.36 (NB8) and 7.76 kbit/s (WB8). At approximately 8 kbit/s, forced
wideband reduced the WER of wav2vec2-base-960h relative to forced narrowband by
0.98 pp [0.42, 1.57], whereas Whisper large-v3 showed no clear difference: +0.14 pp [−0.07, +0.36]
(Table IV). Wideband coding restored the energy above 4 kHz (pooled 4–8 kHz power relative to
REF: +2.14 dB, against −16.54 dB for NB8) but worsened in-band fidelity relative to REF: median
coherence over 0–3.5 kHz fell from 0.623 to 0.559, and median LSD over 0–3 kHz rose from 6.19 to 6.77 dB.
Coding therefore changed with the band, so the comparison does not isolate a bandwidth × coding
interaction and does not change the decomposition. The result was recogniser-dependent and does
not show a general advantage of wideband coding at this rate (Supplementary Section S7)."""

results = f"""# 4. Results

## 4.1 Pilot

On the pilot (138 utterances, 69 speakers), the residual interval excluded zero in both recognisers,
so the study proceeded to the confirmation as specified (Supplementary Section S2, Table S2).

## 4.2 How much of the penalty does the validated control reproduce?

{T2}

{cap2}

{p42}

{T3}

{cap3}

{p43[0]}

{p43[1]}

{fig_components}

{p44}

{p46}

## 4.3 High-rate reference, signal descriptors and negative controls

{p45}

{p47[0]}

{p47[1]}

{p48}

## 4.4 Does the residual survive alternative explanations?

Table IV summarises the robustness analyses.

{T10}

{CAP10}

{ROBUSTNESS}

## 4.5 What does changing the low-rate bandwidth allocation do?

{ALLOCATION}

"""

# =============================================================== main paper: discussion, limitations, conclusion
BACK = """# 5. Discussion

**What is robust.** In both recognisers, removing SILK narrowband's bandwidth with the validated
linear control reproduced only a minority of the WER increase under Opus at 8 kbit/s, and a
substantial residual beyond the linear component remained: 0.69 and 2.07 pp beyond the control in
the primary analysis, and 0.74 and 2.32 pp beyond the best-linear component of the actual codec
output, which absorbs the chain's gain, spectral tilt, roll-off, phase and delay. The residual had
the same direction in both recognisers, both test subsets and an independent pilot, and neither
level matching nor the choice among four error weightings removed it. The attribution of the
8 kbit/s penalty to narrowband operation [@khare2020opus] is therefore incomplete for these
recognisers and data. The direction is not new: coding also cost more than band limitation for
AMR-NB and MP3, but not for GSM full rate (Section 1), and our high-rate SILK reference, without a
detectable pooled residual, falls on the GSM side; comparisons between studies are directional only.

**What depends on definitions.** The share assigned to bandwidth is not an invariant quantity. It
is sequential and path-dependent; it depends on how linear loss is defined (for Whisper 0.17 along
the primary path against 0.10 under the best-linear attribution, for wav2vec2 0.40 against 0.33);
and for Whisper it also depends on the error weighting (0.17 to 0.28). The shares describe an
attribution; they are not causal fractions of the penalty. For wav2vec2, the best-linear component
was slightly less harmful than the primary control despite its lower gain and steeper high-frequency
roll-off, showing that ASR sensitivity is not ordered monotonically by these simple spectral
descriptors and reinforcing that neither linear share should be interpreted as a unique physical
fraction.

**What depends on configuration.** The total 8 kbit/s Opus penalty persisted under the libopus
reference decoder for both recognisers; its magnitude was lower for Whisper, while no clear decoder
difference was established for wav2vec2, and the bandwidth decomposition itself remains defined for
the FFmpeg decoder chain. No clear application-mode difference was established for either
recogniser, and within forced SILK narrowband the residual depended on the coding rate. The evidence
comes from one encoder version, one corpus and two recognisers.

**A candidate organising hypothesis.** Low-rate ASR behaviour in these data is consistent with a
bitrate-allocation trade-off between spectral coverage and fidelity. Within narrowband, raising the
rate improved in-band fidelity and removed the detectable residual. At a fixed 8 kbit/s, forcing
wideband restored the high band but lowered in-band fidelity; this lowered the WER of
wav2vec2-base-960h, whose bandwidth component was large, and did not clearly change that of
Whisper large-v3, whose bandwidth component was small. That ordering of the bandwidth components
agrees with the robustness ranking of Speech Robust Bench [@shah2025srb], and with matched training,
removing content above 4 kHz from LibriSpeech costs little [@likhomanenko2021rethinking]. The
hypothesis is an exploratory reading of a few conditions, not a fitted law or an identified
mechanism.

**What is still unknown.** The residual is a codec-specific residual beyond the specified linear
control, and the evidence is consistent with low-rate coding degradation beyond linear effects.
The Opus signal differed from the control mainly within the retained 0–3 kHz band, where the SILK
reference did not; SILK's excitation bits fall rapidly as the rate drops below about 8 kbit/s
[@skoglund2020opus]; and low-rate SILK coding increased WER even when bandwidth was, by implication
of the evaluation set-up, preserved [@buethe2024nolace]. The residual also contains the 4–5 kHz
image, a small level difference and a 1–2 sample lag. SILK carries image energy of comparable
power and the same lag and decode path yet shows no pooled residual, and NEG_CODEC shows that the
container, decoder and resampling chain alone leave WER unchanged (being CELT-coded, it does not
exercise the SILK upsampling step [@ffmpeg611]); an image of low-rate *coded* content may
nevertheless affect recognition differently. No condition manipulated in-band coding degradation
while holding everything else fixed, so the mechanism is not established.

**Practical reading.** For pipelines that transcribe low-rate Opus with pretrained recognisers,
restoring the missing band alone would not target the residual, the larger component in both
recognisers. Higher coding rates removed it on these data, and decoder-side enhancement of low-rate
SILK [@buethe2024nolace] is a candidate to the extent that the residual is coding degradation;
neither bandwidth extension nor decoder-side enhancement was tested.

# 6. Limitations

1. **Path dependence.** The primary decomposition is sequential (REF → LP → OPUS); its bandwidth share is path-dependent, not an interaction-free attribution.
2. **Definition and metric.** The exact share depends on the definition of linear loss and on the error weighting (Section 4.4), and the control's high-rate reference had not fully converged (up to 0.83 dB near the band edge; Section 3.4).
3. **No factorial interaction.** Estimating the interaction would need a factorial design. A forced-wideband 8 kbit/s counterfactual was tested, but changing bandwidth allocation also changes the coding-distortion budget, so the comparison does not identify a factorial interaction between bandwidth loss and coding distortion.
4. **Mechanism.** The residual is a bundle, not a uniquely identified mechanism: it contains in-band coding degradation, the mirror image, a small level difference, a 1–2 sample lag and the decode path. Level matching was broadband only, and the bitrate sweep changed in-band distortion, level and image fidelity together.
5. **Decoder.** The primary decomposition is defined for FFmpeg 6.1.1 decoding. A post-confirmation sensitivity using the libopus 1.4 reference decoder showed that the total 8 kbit/s penalty persisted for both recognisers, although its magnitude was lower for Whisper. Because the decoder-matched bandwidth control failed held-out validation before ASR, decoder invariance of the bandwidth share or codec-specific residual was not established.
6. **Encoder version.** One encoder version (libopus 1.4) was used. The automatic choice of bandwidth depends on the version: 8 kbit/s selects narrowband in every version we inspected, but the wideband threshold has moved over time. Later libopus releases introduced optional or experimental decoder enhancements that act only on wideband SILK (neural enhancement in 1.5, bandwidth extension in 1.6) [@opus15; @opus16]; these do not apply to the narrowband conditions studied here but may affect the forced-wideband 8 kbit/s counterfactual.
7. **Application mode.** The encoder used `application=audio`, retained to reproduce the codec configuration of the preliminary analysis; `OPUS_APPLICATION_VOIP` was tested only as a post-confirmation sensitivity of the total penalty.
8. **Recognisers and corpus.** Two recognisers were tested, both without a language model or beam search, on one corpus of read English audiobooks with one text normalisation policy. wav2vec2-base-960h was fine-tuned on LibriSpeech training data (evaluation used only held-out subsets), Whisper's training data are undisclosed, and the confirmation speakers are those of the preliminary analysis.
9. **Source audio.** LibriSpeech derives from LibriVox recordings, which are MP3-compressed [@panayotov2015librispeech, Sec. 5], so REF is lossless relative to this study's manipulations but is not guaranteed to represent never-lossy-coded source speech; the paired within-utterance contrasts remain valid, but generalisation to pristine-source recordings is limited.
10. **Decoding configuration.** Whisper was decoded greedily without temperature fallback; the study therefore evaluates that fixed decoding configuration rather than the full default Whisper fallback heuristic, and the conclusions need not transfer unchanged to other decoding settings.
11. **Recogniser nondeterminism.** Greedy float16 decoding of Whisper was not exactly reproducible when batch composition changed (3 of 4,348 hypotheses differed when the confirmation audio was decoded again); this component is contained, not separated, in the cross-run comparisons.
12. **Transmission and acoustic conditions.** Packet loss, jitter, FEC, DTX and other network conditions were not tested, nor were noisy, far-field, conversational or multilingual speech.
13. **External replication.** No external corpus and no new speakers were tested, so the findings have not been replicated beyond the LibriSpeech test speakers.

# 7. Conclusion

We decomposed the ASR penalty of Opus at 8 kbit/s into a bandwidth component and a codec-specific
residual, using a linear low-pass control fitted to SILK narrowband's measured high-rate transfer
function and validated on held-out speakers. In a paired design, the validated control reproduced only a minority of the penalty, and a substantial
residual (0.69 and 2.07 pp) remained in both recognisers, both test subsets and the pilot. The
residual survived an inclusive best-linear attribution of the actual codec output, level matching
and alternative error weightings, and the total penalty persisted under the reference decoder and
the VoIP application mode; the exact fractions, by contrast, depend on the attribution path, the
definition of linear loss and the metric. Within SILK narrowband the residual declined with the
coding rate and was not detectable at 24 kbit/s and above, and at a fixed 8 kbit/s a wideband
allocation lowered WER for one recogniser only. Together these results are consistent with a
low-rate trade-off between spectral coverage and fidelity, but the mechanism is not established.
Generalisation beyond the tested codec version, corpus and recognisers remains future work, as do
a manipulation that changes in-band coding degradation with level and image held fixed, a
decoder-matched decomposition and a factorial design that estimates the interaction between
bandwidth and coding.

# Reproducibility statement

The primary design was specified and version-sealed before any evaluation audio was decoded; each
later analysis was specified separately before any of its audio was encoded (Sections 3.1 and 3.9).
Stopped analyses and failed validation criteria are retained and reported. Code, analysis records,
data selections, per-utterance outputs and intermediate reports are archived at
<https://doi.org/10.5281/zenodo.23011460> and maintained at
<https://github.com/surnamemei/opus-asr-bandwidth-decomposition>. LibriSpeech, the recogniser
checkpoints (pinned revisions), libopus 1.4 and FFmpeg 6.1.1 are public.

# Acknowledgments

OpenAI ChatGPT and Codex, and Anthropic Claude through Claude Code, were used for research ideation,
code-development assistance, adversarial review of the experimental design, and drafting and editorial
assistance throughout the manuscript and supplementary material. AI-assisted text and code were
reviewed, revised, and independently verified by the author, who takes full responsibility for the
experimental design, analyses, results, interpretations, and final manuscript.

# References

::: {#refs}
:::
"""
if SRC.count("\n# References\n\n::: {#refs}\n:::") != 1:
    fail("draft-2 reference block changed")
main = head + results + BACK

# =============================================================== supplement
appA = section("Appendix A. Supplementary tables")
capS = lambda s: appA[find(appA, s, "Appendix A caption"):].split("\n")[0]
pilot_text = rep(prose(section("4.1 Pilot", "## "))[0], "(Table S4)", "(Table S2)")
pilot_tab = between(appA, "| | REF | LP | OPUS |", ": Pilot").strip("\n")
pilot_contr = appA[find(appA, "| Contrast (micro, pp) |", "Appendix A pilot table"):].split("\n\n")[0].strip("\n")
s47 = section("4.7 Signal descriptors", "## ")
T4a = between(s47, "| Descriptor (median vs REF) |", ": Signal descriptors").strip("\n")
T4b = s47[find(s47, "| Pooled cross-spectral descriptor (vs REF) |", "Section 4.7 table"):].split("\n\n")[0].strip("\n")
cap4 = cap(": Signal descriptors on the confirmation set")
cap5 = rep(cap(": Addition A, the level-matched sensitivity analysis"), ": Addition A, the level-matched sensitivity analysis",
           ": Level matching")
cap5 = rep(cap5, "Thresholds are those of the pre-declared rule (Section 3.9).", "Thresholds are those of the pre-declared rule (Section S4).")
cap7 = rep(cap(": Addition B: trend over bitrate"), ": Addition B: trend over bitrate", ": Bitrate sweep: trend over bitrate")
# supplementary tables, in order: S1 validation, S2 pilot, S3 per subset, S4 error types, S5 negative controls,
# S6 descriptors, S7 level matching, S8 sweep trend, S9 best-linear attribution, S10 its linear response,
# S11 decoder / application / allocation, S12 robustness per subset, S13 error weighting, S14 stopped analyses
TABLES = {name: gen_table(title) for name, title in [
    ("SUBSET", "TABLE S1 "), ("ERRTYPE", "TABLE S2 "), ("NEG", "TABLE S3 "), ("LEVEL", "TABLE 5 "), ("TREND", "TABLE 7 "),
    ("A1", "TABLE A1 "), ("A1D", "TABLE A1DS "), ("SC", "TABLE SC "), ("SP", "TABLE SP "), ("C1", "TABLE C1 "),
    ("SR", "TABLE SR ")]}
TABLES["LEVEL"] = corner(TABLES["LEVEL"], "Addition A (pooled)", "Level matching (pooled)")
TABLES["TREND"] = corner(TABLES["TREND"], "Addition B (pooled)", "Bitrate sweep (pooled)")

SUPP = r"""---
title: "Supplementary material for: __TITLE__"
author: "__AUTHORS__"
date: "TASLP submission version, 2026-09-28"
---

<!--
SUPPLEMENTARY MATERIAL of the TASLP submission version (taslp_submission.md): the evidence behind the main paper's
tables and robustness analyses; full sealed records, manifests and logs are in the repository. Checked with
`python manuscript/tools/check_numbers.py --submission`.
-->

```{=latex}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\thesection}{S\arabic{section}}
\suppressfloats[t]
```

This supplement gives the evidence behind the main paper's tables and robustness analyses; the
project repository holds the full sealed records, manifests and logs. Sections, tables and figures
of the main paper are referred to as such; S-numbers refer to this supplement.

# S1. Validation of the bandwidth control

The control was validated on 40 unseen train-clean-100 speakers with the filter taps unchanged
(main paper, Section 3.4 and Fig. 1). All criteria passed; the first validation had failed an
internally inconsistent criterion, which was corrected before the confirmation data were
downloaded (Section S10).

__S1_ROWS__

: Validation of the low-pass control (LP) on 40 unseen train-clean-100 speakers, with the SILK narrowband linear reference and Opus at 8 kbit/s for comparison (no ASR).

# S2. Pilot

__PILOT_TEXT__

__PILOT_TAB__

__CAP_PILOT__

__PILOT_CONTR__

# S3. Confirmation: additional results

Tables S3–S6 support main-paper Sections 4.2 and 4.3. Under the decision rule of main-paper
Section 3.7, the confirmation could return GO (primary criterion met), CONDITIONAL GO (residual
intervals above zero in both recognisers without the size or pilot condition), KILL (all four
residual intervals including zero) or HOLD (any other pattern, or a positive outcome capped by a
negative control). It returned GO for the Opus residual, and no negative control capped it.

__T_SUBSET__

__CAP_S3__

__T_ERRTYPE__

__CAP_S4__

__T_NEG__

__CAP_S5__

__T4A__

__CAP4__

__T4B__

# S4. Level matching

The confirmation utterances were decoded a second time under LP, OPUS and OPUS8_LEVEL_MATCHED (main
paper, Section 3.9). Before recognition, LP and OPUS had to reproduce the confirmation audio bit for
bit, the level-matched RMS had to equal that of LP within 0.001 dB, and the gains had to equal those
implied by the confirmation audio within $10^{-6}$ dB; all checks passed. The per-utterance gains had
a median of +0.562 dB (5th–95th percentile +0.290 to +1.032 dB; range −0.076 to
+2.381 dB). With $T^\ast$ the confirmatory OPUS − LP estimate of each recogniser, the rule returns GO
if the lower bound of $L$ = OPUS8_LEVEL_MATCHED − LP is above zero and the lower bound of
$K$ = OPUS8_LEVEL_MATCHED − OPUS is above $-0.25\,T^\ast$, FALSIFY if the upper bound of $K$ is below
$-0.5\,T^\ast$, and WEAKEN otherwise; a combined GO or FALSIFY needs both recognisers, and a missing
interval bound never satisfies either. Both recognisers returned GO (Table S7). The level-matched
residual was 1.02 and 1.01 times the confirmatory residual, and per 100 reference words it comprised
+0.52 substitutions [+0.35, +0.71] for Whisper and +1.79 substitutions [+1.48, +2.19] for wav2vec2.
Level matching changed 42 of the 2,174 Whisper hypotheses and 188 of the 2,174 wav2vec2 hypotheses,
without reducing either error count; the plan's expectation that wav2vec2-base-960h would be
insensitive to a scalar gain was corrected before the code freeze (Section S10). Decoded a second
time, 3 of Whisper's 4,348 LP and OPUS hypotheses differed from the confirmatory run (wav2vec2's
were identical), so the analysis uses the same-run LP and OPUS.

__T_LEVEL__

__CAP5__

# S5. Coding-rate sweep

The sweep is a fresh-utterance, not fresh-speaker, holdout. It used test utterances that the project
had never encoded, decoded or recognised, selected from metadata only with the confirmation rule: up
to 30 per speaker from every test speaker with an eligible unused utterance. This gave 1,665
utterances from 70 speakers (38 test-clean,
32 test-other; 777 and 888 utterances; 3.17 h; 31,601 reference words). Before recognition, encoding
and decoding alone had to show that every packet at every rate was SILK-only narrowband with 20 ms
frames, that every encoder setting read back as requested, and that the median payload bitrate was
within ±15 % of nominal, with each rate's median at least 1.2 times the previous one. All checks
passed, with median payload bitrates of 7.36, 11.35, 15.43, 23.46 and 38.96 kbit/s, 2.3–8.0 % below
nominal, and at 8 kbit/s the sweep's `signal=voice` encoding produced Ogg files byte-identical to
those of the OPUS settings (`signal=auto`) for all 1,665 utterances. The rule compares the slope $S$
with $S^\ast = (U^\ast - T^\ast)/\log_2 5$, the slope implied by the confirmatory residuals at
8 kbit/s ($T^\ast$, OPUS − LP) and 40 kbit/s ($U^\ast$, SILK − LP): GO if the lower bound of $R_8$ is
above zero, the upper bound of $S$ is below zero and its lower bound is at or below $0.5\,S^\ast$;
FALSIFY if the upper bound of $S$ is at or above zero and its lower bound is above $0.5\,S^\ast$.
Both recognisers returned GO (Table S8). The decline was concentrated at low rates: the step from 8
to 12 kbit/s was the largest (+0.34 and
+1.32 pp), the point estimates fell at every step in both recognisers, and 66 % (Whisper) and
98 % (wav2vec2) of bootstrap replicates were monotone. On test-clean the Whisper slope interval only
just excluded zero (−0.055 [−0.111, −0.001]); per-subset values are in Table S12. The descriptors
changed with the rate: median LSD over 0–3 kHz relative to LP fell from 6.19 to 1.37 dB
and coherence rose from 0.623 to 0.993, the median RMS change relative to REF went from −0.68 to
−0.12 dB, the in-band gain from −1.83 to −0.08 dB, and the mirror coherence from 0.245 to 0.970.

__T_TREND__

__CAP7__

# S6. Inclusive best-linear attribution

The plan, a method note, a signal-only selection, the calibration, the code freeze and a held-out
validation were committed before any confirmation-set projection was computed (main paper,
Section 3.9). LIN8 is the orthogonal projection of the confirmation's exact Opus waveform onto the
span of REF delayed by −256 to +255 samples (512 basis vectors), computed as in the BSS Eval
reference code with a centred delay span. Calibration and held-out validation each used one
utterance from 40 new train-clean-100 speakers (20 female and 20 male per set; no transcripts or
ASR): the projection was numerically exact, a second pass reproduced every waveform, and the
held-out median projection error (−11.61 dB) stayed within the frozen tolerance of 3.08 dB above
the calibration median (−12.39 dB). Before recognition, the regenerated Opus files and
waveforms equalled those of the confirmation for all 2,174 utterances, and the analysis code
reproduced the confirmation's contrasts. The frozen outcome was ROBUST_RESIDUAL: the residual
beyond LIN8 lay above zero and exceeded the linear component in both recognisers (Table S9) and in
both subsets (Table S12). Table S10 shows what the linear component absorbs: a gain about 2 dB below
the control and a steeper in-band roll-off. LIN8 was recognised in its own run, so Whisper's batches
differed from the confirmation's; wav2vec2 decodes each utterance alone. The confirmation projections
used single-threaded linear algebra because of CPU contention on the shared machine, which changes
rare samples in the last bit only.

__T_A1__

: Inclusive best-linear attribution on the confirmation set (2,174 utterances, 73 speakers; pooled; 95 % speaker-bootstrap intervals with the confirmation's seed): corpus WER of LIN8 (%), the linear component LIN8 − REF, the residual beyond it OPUS − LIN8 and the difference from the control LIN8 − LP (pp), the descriptive linear share (LIN8 − REF)/(OPUS − REF) beside the sequential share (LP − REF)/(OPUS − REF), and the frozen outcome. The linear share is not a bandwidth share.

__T_A1D__

: Linear response of the 8 kbit/s chain: medians of the per-utterance best-linear filters on the calibration, validation and confirmation sets (projection error, gain over 0.5–2 kHz, response at fixed frequencies relative to that gain, and phase-slope delay), with the frozen LP control for comparison, and pooled cross-spectral measures against REF (no ASR). Descriptive only; further rows are in the repository.

# S7. Decoder, application mode and bandwidth allocation

Each of these analyses changes one element of the codec chain (Table S11; per subset, Table S12).

**Decoder.** The same frozen confirmation bitstreams were decoded with the libopus 1.4 reference
decoder, which applied RFC 7845 pre-skip and end trimming at 48 kHz, followed by the resampler of
the primary chain, with no gain, alignment or filtering; only OPUS_LIBOPUS was recognised, once.
All pre-recognition checks passed: bitstreams byte-identical to the confirmation's (2,174 of
2,174), no decoding error, the pre-specified output lengths, no non-finite sample, an unchanged
environment and exact reproduction of the confirmatory OPUS − REF. The analysis tests the total penalty only: no bandwidth
component, share or residual was computed under libopus, and a result without a clear difference is
not an equivalence claim.

**Application mode.** The encoder was run again with `OPUS_APPLICATION_VOIP`; every other setting,
the Ogg writer, the decoder and the resampler were unchanged, and the signal-type hint stayed
`signal=auto`. In checks committed before recognition, the regenerated OPUS_AUDIO8 bitstreams and
waveforms equalled those of the confirmation for all 2,174 utterances, every OPUS_VOIP8 utterance
was encoded and decoded to the REF length without non-finite samples, every encoder control read
back as requested, and every packet was mono, narrowband and 20 ms (all SILK).
Under the frozen rule, both recognisers returned NO_CLEAR_APPLICATION_DIFFERENCE. For Whisper
large-v3 the upper bound is exactly zero, and the CER contrast and the test-other contrast excluded zero (secondary,
uncorrected). The VoIP mode changed every waveform at an almost unchanged payload bitrate (median
7.29 against 7.34 kbit/s), with slightly lower in-band coherence (median 0.614 against 0.623); these
descriptors enter no rule.

**Bandwidth allocation.** On the 1,665 sweep utterances, NB8 had to reproduce the sweep's SILK8 files
byte for byte, every WB8 packet had to be SILK-only wideband with 20 ms frames, every encoder setting
had to read back as requested, WB8's median payload bitrate had to lie within ±15 % of nominal and
within ±10 % of NB8's, and WB8's pooled 4–8 kHz power relative to REF had to be at least −10 dB; all
checks passed. NB8's Ogg files and raw hypotheses were identical to those of the sweep's SILK8 for
all 1,665 utterances in both recognisers. In the secondary per-subset analysis, the interval for
Whisper large-v3 on test-clean lay above zero (+0.27 pp [+0.03, +0.54]), and that for
wav2vec2-base-960h on test-other below zero (−1.70 pp [−2.75, −0.65]).

__T_SC__

: Decoder, application mode and bandwidth allocation (pooled; 95 % speaker-bootstrap intervals): corpus WER (%), the difference from the primary chain (pp) and the frozen outcome of each analysis. The decoder and application-mode rows use the 2,174 confirmation utterances, the allocation rows the 1,665 sweep utterances. Total penalties and practical contrasts only: no bandwidth share, residual or equivalence is claimed.

__T_SP__

: Robustness analyses per subset (secondary scope; no multiplicity correction; pp, 95 % speaker-bootstrap intervals). The sweep and allocation rows use the 1,665 sweep utterances, all other rows the confirmation utterances. A bound printed as zero is exactly zero, and its interval includes zero.

# S8. Error weighting

Without new recognition, the primary contrasts were recomputed from the confirmation outputs in every
bootstrap replicate (the confirmation's seed on the same speakers) under four weightings: corpus WER,
mean per-utterance WER, equal-speaker WER (the mean of per-speaker corpus WERs) and CER. The
classification criteria were fixed in the audit code before it was run. A sign or ordering statement
is robust to the weighting if its interval lies above zero under all four pooled weightings and,
under corpus WER, in both subsets; a share is unstable if any pooled replicate has a non-positive
denominator, if its corpus-WER interval has an upper-to-lower ratio above 2, or if its point
estimates differ by more than a factor of 1.5 across weightings. The residual and its excess over
the bandwidth component were robust for both recognisers, Whisper's bandwidth component was
subset-dependent (not detectable on test-clean), the Whisper share was unstable and the wav2vec2
share robust; no pooled replicate had a non-positive denominator (Table S13). In secondary cells,
the ordering was unresolved for Whisper on test-clean under CER and for wav2vec2 on test-other under
mean per-utterance WER, and for wav2vec2 the deletions rose more with band limitation than beyond it
(residual minus bandwidth component −0.09 [−0.22, +0.02] per 100 reference words).

__T_C1__

: Error weighting of the primary contrasts on the confirmation set (pooled; pp; 95 % speaker-bootstrap intervals with the confirmation's seed): bandwidth component, residual, their difference and the sequential share under four weightings. No new recognition.

# S9. Attribution analyses stopped before ASR

Two additional attribution sensitivities were prospectively gated but stopped before ASR because
their signal-domain controls failed held-out validation. Table S14 gives the failed criteria. The
decoder-matched control (LP_LIBOPUS) was to test the decomposition under the libopus decoder; it had
been fitted by the unchanged procedure of main-paper Section 3.4 because the frozen control failed a
pre-specified control-reuse gate against the libopus-decoded SILK narrowband response. The 8 kbit/s
surrogate (SURR8), fitted to the same-frequency coherent response of Opus at 8 kbit/s, was to give
an attribution under a more inclusive linear-loss definition; it is not a bandwidth control. The
held-out subset was new and signal-only (no transcripts; 40 train-clean-100 speakers, 20 female and
20 male, one utterance each, disjoint from the calibration and filter-validation speakers). Neither
control was redesigned or refitted: a repaired control would be a new design that needs its own
held-out validation. A post hoc and exploratory diagnosis points to a sub-sample, content-dependent
delay of the libopus-decoded chain; no successor analysis has been run.

__T_SR__

: Attribution analyses stopped before ASR: the intended question, the failed held-out criterion of each signal-domain control, its value and pre-specified threshold, and the consequence (STOPPED: no recognition was run). The primary control and decomposition are unchanged.

# S10. Amendments and deviations

Before any evaluation decoding, greedy decoding replaced beam search for Whisper, for compute reasons
on a shared GPU. After the pilot and before the confirmation, one figure changed from text labels to
marker shapes (presentation only). During the controls stage, the first validation of the low-pass
control failed on an internally inconsistent criterion; the corrected criterion was frozen before
the confirmation data were downloaded, and the failed result is retained (main paper, Section 3.4).
Before the code freeze of the level-matching analysis, a calibration check found that level matching
changed 1 of 20 wav2vec2-base-960h hypotheses, whereas the plan had expected invariance to a scalar
gain; a dated amendment, sealed before the freeze and before any evaluation audio was decoded,
corrected that expectation and changed no estimand, gate, threshold, condition, selection or rule.
The other later analyses had deviations that changed no gate, tolerance, rule, selection or outcome
(for example descriptive items computed from sealed outputs after the analysis, a validation report
sealed in parts, single-threaded linear algebra for the best-linear attribution, and a manuscript
description of the decoder analysis longer than its plan foresaw); the full lists are in the sealed
records.
"""
SUBS = {"__TITLE__": TITLE, "__AUTHORS__": AUTHORS, "__S1_ROWS__": validation.strip("\n"), "__PILOT_TEXT__": pilot_text, "__PILOT_TAB__": pilot_tab,
        "__CAP_PILOT__": capS(": Pilot"), "__PILOT_CONTR__": pilot_contr,
        "__CAP_S3__": capS(": Per-subset WER"), "__CAP_S4__": capS(": Error-type composition"),
        "__CAP_S5__": capS(": Negative controls"), "__T4A__": T4a, "__CAP4__": cap4, "__T4B__": T4b, "__CAP5__": cap5,
        "__CAP7__": cap7, **{f"__T_{k}__": v for k, v in TABLES.items()}}
supp = SUPP
for key, value in SUBS.items():
    supp = rep(supp, key, value)
if re.search(r"__[A-Z0-9_]+__", supp):
    fail("unfilled supplement placeholder")

OUTPUTS = {"taslp_submission.md": main.rstrip("\n") + "\n", "taslp_supplement.md": supp}

# =============================================================== guards
# every decimal number of the output (e.g. +0.35, 2.3, 1,665) must already be in draft 2 or in
# the generated tables: this script moves numbers, it never makes them. The number of the section
# it adds (3.10) is exempt, but only as a heading or a "Section(s)" reference, and so are web
# addresses (the archive DOI and the repository URL are identifiers, not results)
NEW_SECTION = r"(?:3\.10)"
SECTION_REF = re.compile(rf"(?:^## |Sections?\s+)(?:\d\.\d+,?\s+(?:and\s+)?)*{NEW_SECTION}(?:\s+and\s+{NEW_SECTION})?", re.M)
WEB_ADDRESS = re.compile(r"https?://[^\s>)]+")
known = SRC + "\n" + GEN
for name, text in OUTPUTS.items():
    new = sorted({n for n in re.findall(r"\d[\d,]*\.\d+|\d{1,3}(?:,\d{3})+", SECTION_REF.sub("", WEB_ADDRESS.sub("", text)))
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
