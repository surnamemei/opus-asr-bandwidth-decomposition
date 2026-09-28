"""Verify manuscript/manuscript.md against the frozen outputs (read-only).

1. Every data row of every generated table must appear in the manuscript (same cells).
2. Every prose number listed below is re-derived from the frozen CSVs and must appear.
3. Forbidden priority / causal / equivalence phrasing must be absent.
4. Figure paths must exist; citation keys must exist in references.bib.
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Default: the full manuscript. --submission: the TASLP submission version and its supplement,
# checked together (every number may sit in either file); see section 5 for the extra rules.
SUBMISSION = "--submission" in sys.argv[1:]
FILES = (["taslp_submission.md", "taslp_supplement.md"] if SUBMISSION else ["manuscript.md"])
TEXTS = {f: (ROOT / "manuscript" / f).read_text(encoding="utf-8") for f in FILES}
MS = "\n\n".join(TEXTS.values())
MSN = " ".join(MS.split())          # prose checks ignore line breaks
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import contextlib  # noqa: E402
import io  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import make_tables as T  # noqa: E402  (re-uses the frozen-CSV loaders and formatters)

fails = []


def need(token, why):
    if " ".join(token.split()) not in MSN:
        fails.append(f"MISSING [{why}]: {token}")


def need_full_only(token, why):
    """A detail that draft 2 states and the submission leaves to the repository (sealed records)."""
    if not SUBMISSION:
        need(token, why)


# ------------------------------------------------------------------ 1. tables
generated = subprocess.run([sys.executable, str(HERE / "make_tables.py")], capture_output=True,
                           text=True, check=True).stdout
def is_rule(line):
    return line.startswith("|") and set(line.replace("|", "").strip()) <= set("-: ")


def cells_of(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


ms_rows = {}
ms_headers = []                     # header rows (the row above a rule), for the corner-free comparison
_ms_lines = MS.splitlines()
for i, line in enumerate(_ms_lines):
    if line.startswith("|") and not is_rule(line):
        cells = cells_of(line)
        ms_rows.setdefault(cells[0], []).append(cells)
        if i + 1 < len(_ms_lines) and is_rule(_ms_lines[i + 1]):
            ms_headers.append(cells)

SKIP_FIRST = {"Condition", "Contrast", "Subset", "Model", "Descriptor", "", "Measure",
              "Contrast (micro, pp)", "Descriptor (median vs REF)",
              "Pooled cross-spectral descriptor (vs REF)", "Mean coherence, 0–3.5 kHz",
              "RMS level change (dB)"}  # RMS levels are stated in Methods prose and checked below
NORMALISE = {"0.000": "0.00"}  # manuscript prints LSD of NEG_LP as 0.00 (value 3e-5 dB)
checked = 0
skip_tag = "[full manuscript]" if SUBMISSION else "[submission]"   # tables that belong to the other document
# tables tagged [repository] are superseded in both documents by compact tables; they are still generated
# from the sealed records for traceability
skipping = False
header_next = False
for line in generated.splitlines():
    if line.startswith("TABLE"):
        skipping = line.rstrip().endswith(skip_tag) or line.rstrip().endswith("[repository]")
        header_next = True
    if skipping or not line.startswith("|") or is_rule(line):
        continue
    cells = cells_of(line)
    if header_next:             # header row: compared without its corner cell
        header_next = False
        if cells[0] in SKIP_FIRST:
            continue
        checked += 1
        if not any(len(h) == len(cells) and h[1:] == cells[1:] for h in ms_headers):
            fails.append(f"TABLE HEADER MISMATCH (corner cell ignored): {line}")
        continue
    if cells[0] in SKIP_FIRST:
        continue
    candidates = ms_rows.get(cells[0], [])
    want = [NORMALISE.get(c, c) for c in cells]
    ok = any([NORMALISE.get(c, c) for c in cand] == want for cand in candidates)
    # rows whose first cell repeats (subset / model tables): match on the first two cells
    if not ok:
        ok = any(cand[:2] == cells[:2] and [NORMALISE.get(c, c) for c in cand] == want
                 for rows in ms_rows.values() for cand in rows)
    checked += 1
    if not ok:
        fails.append(f"TABLE ROW MISMATCH: {line}")

# ------------------------------------------------------------------ 2. prose numbers
b, fmt, ci = T.b, T.fmt, T.ci
M = "−"


def pp(q, m, scope="pooled", kind="micro", unsigned=False):
    e, lo, hi = b("confirmation", m, q, scope=scope, kind=kind)
    if unsigned:
        return f"{fmt(e)} pp [{fmt(lo)}, {fmt(hi)}]"
    return f"{fmt(e, True)} pp [{fmt(lo, True)}, {fmt(hi, True)}]"


for m in ("whisper", "wav2vec2"):
    need(pp("delta_bw", m, unsigned=True), "bandwidth component (prose)")
    need(pp("delta_opus_residual", m, unsigned=True), "residual (prose)")
    for q in ("delta_silk_residual", "opus_minus_silk",
              "neg_lp_minus_ref"):
        need(pp(q, m), f"{q} {m}")
    for sub in ("test-clean", "test-other"):
        need(pp("delta_opus_residual", m, scope=sub), f"residual {sub} {m}")
    e, lo, hi = b("confirmation", m, "bw_share_of_opus_total", kind="ratio")
    need(f"{round(100*e):.0f} % [{round(100*lo):.0f}, {round(100*hi):.0f}]", f"share {m}")
    need(pp("delta_opus_residual", m, kind="micro_cer"), f"CER residual {m}")
    ref = b("confirmation", m, "wer_REF")[0]
    lp = b("confirmation", m, "wer_LP")[0]
    for num, den in (("delta_bw", ref), ("delta_opus_residual", lp), ("delta_opus_total", ref)):
        need(f"+{100*b('confirmation', m, num)[0]/den:.1f} %", f"relative {num} {m}")
    e, lo, hi = b("pilot", m, "delta_opus_residual")
    need(f"{fmt(e, True)} pp [{fmt(lo, True)}, {fmt(hi, True)}]", f"pilot residual {m}")
    e, lo, hi = b("pilot", m, "delta_bw")
    need(f"{fmt(e, True)} pp [{fmt(lo, True)}, {fmt(hi, True)}]", f"pilot bandwidth {m}")
    s = b("confirmation", m, "delta_opus_residual_S", kind="micro_error_type")
    need(f"{fmt(s[0], True)} substitutions [{fmt(s[1], True)}, {fmt(s[2], True)}]", f"S {m}")
    for t, word in (("D", "deletions"), ("I", "insertions")):
        v = b("confirmation", m, f"delta_opus_residual_{t}", kind="micro_error_type")[0]
        need(f"{fmt(v, True)} {word}", f"{t} {m}")
    tot = b("confirmation", m, "delta_opus_residual")[0]
    need(f"{100*s[0]/tot:.0f} %", f"substitution share {m}")
    e, lo, hi = b("confirmation", m, "neg_codec_minus_ref")
    need(f"{fmt(e, True, 3)} pp [{fmt(lo, True, 3)}, {fmt(hi, True, 3)}]", f"NEG_CODEC {m}")

need(pp("delta_bw", "whisper", scope="test-clean"), "W test-clean bandwidth")
need(pp("delta_bw", "whisper", scope="test-other"), "W test-other bandwidth")
need(pp("delta_silk_residual", "wav2vec2", scope="test-other"), "V test-other SILK")

errs = {m: [int(T.corpus("confirmation", m, c)["word_errors"]) for c in ("REF", "LP", "OPUS")]
        for m in ("whisper", "wav2vec2")}
for m, (a, c2, d) in errs.items():
    need(f"{a:,}, {c2:,} and {d:,}", f"word errors {m}")
ref_row = T.corpus("confirmation", "whisper", "REF")
need(f"{int(ref_row['n_words']):,}", "reference words")
need(f"{int(ref_row['n_utterances']):,} ", "utterances")
need(f"{int(ref_row['n_speakers'])} speakers", "speakers")

# ------------------------------------------------------------------ 2b. TASLP-upgrade prose (sealed outputs)
# Addition A: level-matched sensitivity (post-confirmation); addition B: bitrate sweep (fresh utterances)
W, V = "whisper", "wav2vec2"


def up(est, lo, hi, dec=2, unit=" pp"):
    return f"{fmt(est, True, dec)}{unit} [{fmt(lo, True, dec)}, {fmt(hi, True, dec)}]"


L = {m: T.a(m, "L_level_matched_minus_lp") for m in (W, V)}
K = {m: T.a(m, "K_level_matched_minus_opus") for m in (W, V)}
for m in (W, V):
    need(up(*L[m]), f"A level-matched residual {m}")
    need(up(*K[m], dec=3), f"A effect of level matching {m}")
    subs = T.a(m, "L_level_matched_minus_lp_S", kind="micro_error_type")
    need(f"{fmt(subs[0], True)} substitutions [{fmt(subs[1], True)}, {fmt(subs[2], True)}]", f"A substitutions {m}")
need_full_only(f"{L[W][0]:.2f} and {L[V][0]:.2f} pp remained", "A abstract")
cells = T.A_DEC["cells"]
need(f"{cells[W]['retained_fraction_L_over_T_star']:.2f} and {cells[V]['retained_fraction_L_over_T_star']:.2f} times",
     "A retained share")
need(f"{fmt(cells[W]['go_threshold_K_lower'], True, 3)} | {fmt(cells[V]['go_threshold_K_lower'], True, 3)}",
     "A GO thresholds (Table S7)")
assert T.A_DEC["outcome"] == "GO" and all(c["outcome"] == "GO" for c in cells.values())
changed = T.A_DEC["hypotheses_changed_by_level_matching"]
need(f"changed {changed[W]} of the {T.N_A:,} Whisper hypotheses and {changed[V]} of the {T.N_A:,} wav2vec2", "A changed")
g = T.A_REG["gain_db"]
need(f"median of {fmt(g['median'], True, 3)} dB (5th–95th percentile {fmt(g['p05'], True, 3)} to "
     f"{fmt(g['p95'], True, 3)} dB; range {fmt(g['min'], True, 3)} to\n{fmt(g['max'], True, 3)} dB)", "A gains")
for key, tok in (("max_abs_level_error_db", "$1.6 \\times 10^{-8}$ dB"),
                 ("max_abs_gain_reproduction_error_db", "$1.4 \\times 10^{-14}$ dB")):
    need_full_only(tok, f"A {key}")
assert f"{T.A_REG['max_abs_level_error_db']:.1e}" == "1.6e-08"
assert f"{T.A_REG['max_abs_gain_reproduction_error_db']:.1e}" == "1.4e-14"
clip = {c: [r for r in T.LV_MAN if r["condition"] == c] for c in ("OPUS", T.LM)}
n = {c: (sum(int(r["clip_count"]) for r in rs), sum(int(r["clip_count"]) > 0 for r in rs)) for c, rs in clip.items()}
need_full_only(f"from {n['OPUS'][0]} in {n['OPUS'][1]} utterances\n(OPUS) to {n[T.LM][0]} in {n[T.LM][1]} utterances", "A clipping")
diff = {(r["model"], r["condition"]): int(r["differing"]) for r in T.REPRO}
assert diff[(V, "LP")] == diff[(V, "OPUS")] == 0 and (diff[(W, "LP")], diff[(W, "OPUS")]) == (2, 1)
need(f"{diff[(W, 'LP')] + diff[(W, 'OPUS')]} of {2 * T.N_A:,} hypotheses", "A reproduction")
same_run = T.a(W, "T_opus_minus_lp")[0] - T.SPEC["A"]["anchors"][W]["T_star"]["estimate"]
need_full_only(f"OPUS − LP by {same_run:.3f} pp", "A same-run shift")

R8 = {m: T.sw(m, "R_8") for m in (W, V)}
S_ = {m: T.sw(m, "S_log2", kind="trend") for m in (W, V)}
for m in (W, V):
    need(up(*R8[m]), f"B R_8 {m}")
need(f"{fmt(S_[W][0], True, 3)} pp per doubling [{fmt(S_[W][1], True, 3)}, {fmt(S_[W][2], True, 3)}]", "B slope whisper")
need(f"{fmt(S_[V][0], True, 3)}\n[{fmt(S_[V][1], True, 3)}, {fmt(S_[V][2], True, 3)}]", "B slope wav2vec2")
need_full_only(f"by {abs(S_[W][0]):.2f} and {abs(S_[V][0]):.2f} pp per doubling", "B abstract")
thr = T.B_DEC["cells"]
need(f"{fmt(thr[W]['meaningful_decline_threshold'], True, 3)} | {fmt(thr[V]['meaningful_decline_threshold'], True, 3)}",
     "B thresholds (Table S9)")
assert T.B_DEC["outcome"] == "GO" and all(c["outcome"] == "GO" for c in thr.values())
for m in (W, V):   # no residual detectable at 24 and 40 kbit/s; detectable at 8
    assert all(T.sw(m, f"R_{r}")[1] <= 0 <= T.sw(m, f"R_{r}")[2] for r in (24, 40)) and R8[m][1] > 0
# the paired 24-40 kbit/s contrast resolves a smaller difference for wav2vec2 only (Whisper's includes zero)
D2440 = {m: T.sw(m, "D_24_40") for m in (W, V)}
assert D2440[V][1] > 0 and D2440[W][1] <= 0 <= D2440[W][2]
need(", ".join(f"{p:.2f}" for p in T.payload[:-1]) + f" and {T.payload[-1]:.2f} kbit/s", "B payload")
dev = sorted(100 * (1 - p / r) for p, r in zip(T.payload, T.RATES))
need(f"{dev[0]:.1f}–{dev[-1]:.1f} % below nominal", "B payload deviation")
cont = T.B_VAL["median_container_kbps"]
need_full_only(f"{cont[0]:.2f}–{cont[-1]:.2f} kbit/s", "B Ogg bitrates")
need_full_only(f"{sum(int(float(r['num_packets'])) for r in T.SW_ROWS if r['condition'] == 'SILK8'):,} packets", "B packets")
assert T.B_VAL["bridge_share_silk8_identical_to_stage3_opus_settings"] == 1.0
need(f"for all {T.SW_SEL['n_utterances']:,} utterances", "B bridge")
d812 = {m: T.sw(m, "D_8_12")[0] for m in (W, V)}
need(f"({fmt(d812[W], True)} and\n{fmt(d812[V], True)} pp)", "B 8-12 step")
mono = {m: T.sw(m, "share_replicates_monotone_non_increasing", kind="descriptive")[0] for m in (W, V)}
need(f"{100 * mono[W]:.0f} % (Whisper) and {100 * mono[V]:.0f} % (wav2vec2)", "B monotone share")
E = {m: T.sw(m, "E_8_40") for m in (W, V)}
need(f"{up(*E[W])} and {fmt(E[V][0], True)} pp\n[{fmt(E[V][1], True)}, {fmt(E[V][2], True)}]", "B endpoint")
need(up(*T.sw(W, "R_8", scope="test-other")), "B whisper test-other R_8")
need(up(*T.sw(W, "R_8", scope="test-clean")), "B whisper test-clean R_8")
sc = T.sw(W, "S_log2", scope="test-clean", kind="trend")
need(f"({fmt(sc[0], True, 3)} [{fmt(sc[1], True, 3)}, {fmt(sc[2], True, 3)}])", "B whisper test-clean slope")
sig = T.SW_SIG
need(f"from {float(sig['SILK8']['LSD 0-3 kHz vs LP (dB)']):.2f} to {float(sig['SILK40']['LSD 0-3 kHz vs LP (dB)']):.2f} dB", "B LSD")
need(f"from {float(sig['SILK8']['coherence 0-3.5 kHz vs LP']):.3f} to {float(sig['SILK40']['coherence 0-3.5 kHz vs LP']):.3f}", "B coherence")
need(f"from {M}{abs(float(sig['SILK8']['rms_change_db vs REF'])):.2f} to {M}{abs(float(sig['SILK40']['rms_change_db vs REF'])):.2f} dB", "B RMS")
pool = T.SW_POOL
need(f"from {M}{abs(float(pool[('REF', 'SILK8')]['h1_level_db'])):.2f} to {M}{abs(float(pool[('REF', 'SILK40')]['h1_level_db'])):.2f} dB", "B in-band gain")
need(f"from {float(pool[('REF', 'SILK8')]['image_coherence_4100_4900']):.3f} to {float(pool[('REF', 'SILK40')]['image_coherence_4100_4900']):.3f}", "B mirror coherence")
sel = T.SW_SEL
need(f"{sel['n_utterances']:,} utterances from {sel['n_speakers']} speakers ({sel['speakers_by_subset']['test-clean']} test-clean,\n"
     f"{sel['speakers_by_subset']['test-other']} test-other; {sel['subsets']['test-clean']} and {sel['subsets']['test-other']} utterances; "
     f"{sel['duration_hours']:.2f} h; {sel['normalised_reference_words']:,} reference words)", "B selection")

# signal prose
S = T.SUM
# the prose states the values relative to LP (vs_lp_*); the descriptor table gives the separately computed
# values relative to REF (vs_ref_*); the submission says that they agree to the precision shown
for c in ("OPUS", "SILK"):
    assert f"{float(S[c]['vs_lp_lsd_0_3k_db']):.2f}" == f"{float(S[c]['vs_ref_lsd_0_3k_db']):.2f}"
    assert f"{float(S[c]['vs_lp_coherence_0_3500']):.3f}" == f"{float(S[c]['vs_ref_coherence_0_3500']):.3f}"
need(f"{float(S['OPUS']['vs_lp_lsd_0_3k_db']):.2f} dB", "OPUS in-band LSD vs LP")
need(f"{float(S['SILK']['vs_lp_lsd_0_3k_db']):.2f} dB", "SILK in-band LSD vs LP")
need(f"{float(S['OPUS']['vs_lp_coherence_0_3500']):.3f}", "OPUS coherence vs LP")
need(f"{float(S['SILK']['vs_lp_coherence_0_3500']):.3f}", "SILK coherence vs LP")
P = T.P
tot = {c: float(P[("REF", c)]["total_hf_power_db"]) for c in ("LP", "OPUS", "SILK")}
need(f"OPUS {M}{abs(tot['OPUS']):.1f} dB, SILK {M}{abs(tot['SILK']):.1f} dB", "image power")
need(f"{tot['OPUS']-tot['LP']:.1f} and {tot['SILK']-tot['LP']:.1f} dB", "image power above LP")
cb = [float(P[("REF", c)]["coherent_bandwidth_hz"]) for c in ("LP", "OPUS", "SILK")]
need(f"{cb[0]:,.0f}, {cb[1]:,.0f} and {cb[2]:,.0f} Hz", "coherent bandwidths")
opus_rms = T.med("OPUS", "rms_change_db")
need(f"{M}{abs(opus_rms):.2f} dB", "OPUS level")
need(f"{M}{abs(T.pct('OPUS','rms_change_db',0.05)):.2f} to {M}{abs(T.pct('OPUS','rms_change_db',0.95)):.2f} dB", "OPUS level p5-p95")
for c in ("OPUS", "SILK", "NEG_CODEC"):
    need(f"{T.med(c, 'measured_bitrate_kbps'):.2f} kbit/s", f"bitrate {c}")
clips = {c: sum(int(r["clip_count"]) for r in T.MAN if r["condition"] == c) for c in
         ("LP", "OPUS", "SILK", "NEG_LP", "NEG_CODEC")}
need(f"{min(clips.values())} (NEG_LP)", "min clip count")
need(f"{max(clips.values())} (LP)", "max clip count")
assert min(clips, key=clips.get) == "NEG_LP" and max(clips, key=clips.get) == "LP"

# Stage 2B confirmation (gate evidence strings) and preliminary study
gates = (ROOT / "results_paper" / "lowpass_confirmation" / "gates.csv").read_text()
for tok in ("0.031 dB", "4093.8 Hz", "4125.0", "-24.7 dB", "-24.9 dB", "0.57 dB", "0.9992", "0.168"):
    if tok not in gates:
        fails.append(f"STAGE2B token not in gates.csv: {tok}")
for tok in ("0.031 dB", "4,093.8 Hz", "4,125.0 Hz", f"{M}24.7 dB", f"{M}24.9 dB", "0.57 dB", "0.9992", "0.168"):
    need(tok, "Stage 2B confirmation")
# The prior study's outputs are not part of this repository; its two cited rows are kept as a
# sealed extract with the source file's hash (provenance/derive_prior_study_context.py).
extract = json.loads((ROOT / "provenance" / "prior_study_context.json").read_text())
if hashlib.sha256(json.dumps({k: v for k, v in extract.items() if k != "record_sha256"},
                             sort_keys=True).encode()).hexdigest() != extract["record_sha256"]:
    fails.append("PRIOR extract seal mismatch")
prior = extract["rows"]
for br, token in (("12k", "1.33 pp at 12 kbit/s"), ("8k", "6.63 pp at 8 kbit/s")):
    row = [r for r in prior if r["codec"] == "opus" and r["bitrate"] == br and r["dataset"] == "test-other"][0]
    if f"{float(row['delta_wer_pp']):.2f}" not in token:
        fails.append(f"PRIOR mismatch {br}: {row['delta_wer_pp']}")
    need_full_only(token, "preliminary study (the submission names the unpublished analysis without its numbers)")


# LP reference convergence (frozen calibration curves)
cal = [r for r in csv.DictReader(open(ROOT / "results_paper" / "lowpass_validation" / "calibration_curves.csv"))
       if 3000 <= float(r["frequency_hz"]) <= 4150]
d32 = [float(r["reference_h1_rel_db_40k"]) - float(r["reference_h1_rel_db_32k"]) for r in cal]
need(f"{min(d32):.2f}–{max(d32):.2f} dB (mean {sum(d32)/len(d32):.2f} dB)", "convergence 32->40k (Methods)")
need(f"up to {max(d32):.2f} dB", "convergence 32->40k (Limitations)")
for tok in ("+0.27 dB", "0.3–0.7 dB", "48 kbit/s"):
    if tok in MS:
        fails.append(f"UNSEALED number still present: {tok}")

# ------------------------------------------------------------------ 5. submission version
if SUBMISSION:
    # every table row of the submission files is a checked row: a generated row or a row of the
    # checked full manuscript (its hand-made tables: conditions, control validation)
    full = (ROOT / "manuscript" / "manuscript.md").read_text(encoding="utf-8")
    known = {" ".join(l.split()) for l in (generated + "\n" + full).splitlines() if l.startswith("|")}
    _src = (generated + "\n" + full).splitlines()
    known_headers = {tuple(cells_of(l)[1:]) for i, l in enumerate(_src)
                     if l.startswith("|") and not is_rule(l) and i + 1 < len(_src) and is_rule(_src[i + 1])}
    # a table cell that build_submission.py rewords for the journal; the row is otherwise the checked draft-2 row
    REWORDED = {"| LP | Fixed zero-phase low-pass control (Section 3.4) | — | — |":
                "| LP | Frozen zero-phase low-pass control (Section 3.4) | — | — |"}
    for f, text in TEXTS.items():
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("|") or " ".join(REWORDED.get(line, line).split()) in known:
                continue
            header = i + 1 < len(lines) and is_rule(lines[i + 1])
            if header and tuple(cells_of(line)[1:]) in known_headers:
                continue
            fails.append(f"UNCHECKED TABLE ROW in {f}: {line}")
    main = " ".join(TEXTS["taslp_submission.md"].split())
    primary = [pp("delta_bw", m, unsigned=True) for m in (W, V)] + \
              [pp("delta_opus_residual", m, unsigned=True) for m in (W, V)] + \
              [up(*L[m]) for m in (W, V)] + [up(*K[m], dec=3) for m in (W, V)] + \
              [up(*R8[m]) for m in (W, V)] + [up(*E[m]) for m in (W,)] + \
              [f"{fmt(S_[W][0], True, 3)} pp per doubling [{fmt(S_[W][1], True, 3)}, {fmt(S_[W][2], True, 3)}]"]
    for m in (W, V):
        e, lo, hi = b("confirmation", m, "bw_share_of_opus_total", kind="ratio")
        primary.append(f"{round(100*e):.0f} % [{round(100*lo):.0f}, {round(100*hi):.0f}]")
    # forced-wideband counterfactual (sealed R3 outputs), in the main paper as a practical
    # bandwidth-allocation counterfactual; the two attribution sensitivities that stopped before
    # ASR (R1, R2) get one sentence in the main paper and their failed criteria in the supplement
    assert T.R3_OUT == {W: "NO_CLEAR_DIFFERENCE", V: "WB_BETTER"}
    assert all(T.R3_HYP[m]["nb8_vs_b_silk8_raw_hypothesis_differs"] == 0 for m in (W, V))
    R3W = {m: T.r3(m, "W") for m in (W, V)}
    r3med = {c: T.R3_MED[c] for c in ("NB8", "WB8")}
    stopped = ("Two additional attribution sensitivities were prospectively gated but stopped before ASR "
               "because their signal-domain controls failed held-out validation.")
    primary += [
        f"At approximately 8 kbit/s, forced wideband reduced the WER of wav2vec2-base-960h relative to forced "
        f"narrowband by {abs(R3W[V][0]):.2f} pp [{abs(R3W[V][2]):.2f}, {abs(R3W[V][1]):.2f}]",
        f"Whisper large-v3 showed no clear difference: {up(*R3W[W])}",
        f"{T.R3_PAY['NB8']:.2f} (NB8) and {T.R3_PAY['WB8']:.2f} kbit/s (WB8)",
        f"REF: {fmt(T.R3_POOL['WB8']['total_hf_power_db'], True)} dB, against "
        f"{fmt(T.R3_POOL['NB8']['total_hf_power_db'], True)} dB for NB8",
        f"fell from {T.cell(r3med['NB8']['coherence 0-3.5 kHz vs REF'], 3)} to "
        f"{T.cell(r3med['WB8']['coherence 0-3.5 kHz vs REF'], 3)}",
        f"rose from {T.cell(r3med['NB8']['LSD 0-3 kHz vs REF (dB)'], 2)} to "
        f"{T.cell(r3med['WB8']['LSD 0-3 kHz vs REF (dB)'], 2)} dB",
        "does not isolate a bandwidth × coding interaction and does not change the decomposition",
        "recogniser-dependent and does not show a general advantage of wideband coding at this rate",
        "Estimating the interaction would need a factorial design.",     # kept (frozen plan, R3 in every outcome)
        "A forced-wideband 8 kbit/s counterfactual was tested, but changing bandwidth allocation also changes the "
        "coding-distortion budget, so the comparison does not identify a factorial interaction between bandwidth "
        "loss and coding distortion.",
        stopped,
    ]
    if " ".join(stopped.split()) not in " ".join(TEXTS["taslp_supplement.md"].split()):
        fails.append(f"MISSING in the supplement: {stopped}")
    need(f"NB8's Ogg files and raw hypotheses were identical to those of the sweep's SILK8 for all "
         f"{T.R3_HYP[W]['utterances']:,} utterances in both recognisers", "R3 reproduction (S7)")
    # R1 and R2 stay STOPPED: their failed held-out criteria are the rows of the generated Table S15 (checked
    # above as table rows, from the sealed validation records); the fractional-delay diagnosis is post hoc and
    # exploratory, and only its label is in the supplement (the numbers are in the repository)
    sr = [l for l in generated.split("TABLE SR ", 1)[1].split("\n\n", 1)[0].splitlines() if l.startswith("| ")][1:]
    assert len(sr) == 3 and all(l.rstrip().endswith("| STOPPED |") for l in sr)
    assert f"| {T.R1_RMS:.2f} | {T.R1_TOL['g6_h1_rms_max_db']:.1f} |" in sr[0]
    assert f"| {T.R2_V3['rms_db']:.2f} | {T.R2_TOL['V3_rms_max_db']:.1f} |" in sr[1]
    assert f"| {T.R2_V3['max_abs_db']:.2f} | {T.R2_TOL['V3_abs_max_db']:.1f} |" in sr[2]
    assert T.R1_RMS > T.R1_TOL['g6_h1_rms_max_db'] and T.R2_V3['rms_db'] > T.R2_TOL['V3_rms_max_db'] \
        and T.R2_V3['max_abs_db'] > T.R2_TOL['V3_abs_max_db']
    need("A post hoc and exploratory diagnosis points to a sub-sample, content-dependent delay", "exploratory label (S9)")
    need(f"Whisper large-v3 on test-clean lay above zero ({up(*T.r3(W, 'W', 'test-clean'))})", "R3 secondary (S7)")
    need(f"wav2vec2-base-960h on test-other below zero ({up(*T.r3(V, 'W', 'test-other'))})", "R3 secondary (S7)")
    for tok in primary:
        if " ".join(tok.split()) not in main:
            fails.append(f"PRIMARY RESULT not in the main paper: {tok}")
    # reference-decoder sensitivity of the total penalty (sealed R4 outputs): a Results paragraph, one
    # Discussion sentence and the decoder limitation in the main paper; tables in the supplement (Section S7),
    # diagnostics and transcript differences in the repository
    assert T.R4_OUT == {W: "DECODER_LOWER_PENALTY", V: "NO_CLEAR_DECODER_DIFFERENCE"}
    r4 = {(m, q): T.r4(m, q) for m in (W, V) for q in ("T_ffmpeg", "T_libopus", "D")}
    d_w = r4[(W, "D")]
    r4_tokens = [
        f"the total penalty remained positive for both recognisers: {up(*r4[(W, 'T_libopus')])} for Whisper "
        f"large-v3 and {up(*r4[(V, 'T_libopus')])} for wav2vec2-base-960h",
        f"Relative to FFmpeg decoding, the libopus decoder reduced Whisper WER by {abs(d_w[0]):.2f} pp "
        f"[{abs(d_w[2]):.2f}, {abs(d_w[1]):.2f}], whereas no clear decoder difference was established for wav2vec2 "
        f"({up(*r4[(V, 'D')])}).",
        "The bandwidth decomposition remains defined for the FFmpeg chain, and no decoder-invariant residual or share "
        "is claimed.",
        f"FFmpeg decoding the totals were {fmt(r4[(W, 'T_ffmpeg')][0], True)} and {fmt(r4[(V, 'T_ffmpeg')][0], True)} pp",
        "The primary decomposition is defined for FFmpeg 6.1.1 decoding. A post-confirmation sensitivity using the "
        "libopus 1.4 reference decoder showed that the total 8 kbit/s penalty persisted for both recognisers, although "
        "its magnitude was lower for Whisper. Because the decoder-matched bandwidth control failed held-out validation "
        "before ASR, decoder invariance of the bandwidth share or codec-specific residual was not established.",
        "The total 8 kbit/s Opus penalty persisted under the libopus reference decoder for both recognisers; its "
        "magnitude was lower for Whisper, while no clear decoder difference was established for wav2vec2, and the "
        "bandwidth decomposition itself remains defined for the FFmpeg decoder chain",
    ]
    # (until the author-packaging pass these tokens were appended to `primary` after its check loop and so
    # were never checked)
    for tok in r4_tokens:
        if " ".join(tok.split()) not in main:
            fails.append(f"PRIMARY RESULT not in the main paper: {tok}")
    # decoder SNR, transcript-difference counts and signal diagnostics are in the repository (sealed R4 records)
    need("no bandwidth component, share or residual was computed under libopus", "R4 claim boundary (S7)")
    need("a result without a clear difference is not an equivalence claim", "R4 claim boundary (S7)")
    need("this component is contained, not separated, in the cross-run comparisons", "Whisper batch component (Limitations)")
    # SPS Information for Authors: "The abstract must be between 150-250 words."
    abstract = TEXTS["taslp_submission.md"].split("# Abstract", 1)[1].split("**Index Terms**", 1)[0]
    if not 150 <= len(abstract.split()) <= 250:
        fails.append(f"ABSTRACT has {len(abstract.split())} words (SPS limit 150-250)")
    # the sequential bandwidth share is path-dependent wherever a share value is stated, and
    # Whisper's exact share appears in the results only (high-level prose says "a small share")
    paragraphs = TEXTS["taslp_submission.md"].split("\n\n")
    for para in paragraphs:
        if re.search(r"\b40 %", para) and "path-dependent" not in para:
            fails.append(f"SHARE without 'path-dependent': {' '.join(para.split())[:90]}")
    sections = re.split(r"\n(?=#{1,2} )", TEXTS["taslp_submission.md"])
    w_share = f"{round(100 * b('confirmation', W, 'bw_share_of_opus_total', kind='ratio')[0]):.0f} %"
    where = [sec.split("\n", 1)[0] for sec in sections if w_share in sec]
    if where != ["## 4.2 How much of the penalty does the validated control reproduce?"]:
        fails.append(f"WHISPER SHARE '{w_share}' outside Section 4.2: {where}")
    # limitations added in the final pass (encoder application mode; lossy-coded source audio)
    # final invariance pass (sealed A1 and C1 records): the inclusive best-linear attribution and the metric
    # audit in the main paper (Sections 3.11 and 4.12) and their details in Supplementary Sections S9 and S11
    assert T.A1_DEC["outcome"] == "ROBUST_RESIDUAL"
    a1r = {m: T.a1(m, "R8") for m in (W, V)}
    a1d = {m: T.a1(m, "delta_L") for m in (W, V)}
    for tok in [f"The residual beyond the best-linear component was {up(*a1r[W])} and {up(*a1r[V])}",
                f"LIN8 − LP was {up(*a1d[W])} for Whisper large-v3 and {up(*a1d[V])} for wav2vec2-base-960h",
                "the exact attribution changed, but the residual did not disappear",
                "This is a sensitivity to the attribution definition: it does not replace the sequential decomposition, "
                "and its linear share is not a bandwidth share.",
                "The residual remained positive and larger than the primary bandwidth component under all four tested "
                "error weightings; the exact share, especially for Whisper, was not invariant.",
                "residual beyond the linear component"]:
        if " ".join(tok.split()) not in main:
            fails.append(f"PRIMARY RESULT not in the main paper: {tok}")
    need("The frozen outcome was ROBUST_RESIDUAL", "A1 outcome (S6)")
    need("the Whisper share was unstable and the wav2vec2 share robust", "C1 classes (S8)")
    cl = T.C1_REC["classifications"]
    assert cl["whisper: sequential share B/T"]["classes"] == ["RATIO_UNSTABLE"]
    assert all(cl[f"{m}: {s}"]["classes"] == ["METRIC_ROBUST"] for m in (W, V) for s in ("residual R > 0", "ordering R > B"))

    # final invariance pass, B1 (sealed record): the encoder application mode (total penalty only)
    assert T.B1_OUT == {W: "NO_CLEAR_APPLICATION_DIFFERENCE", V: "NO_CLEAR_APPLICATION_DIFFERENCE"}
    b1v = {m: T.b1(m, "V") for m in (W, V)}
    b1d = {m: T.b1(m, "D_app") for m in (W, V)}
    for tok in [f"the total penalty remained positive: {up(*b1v[W])} (Whisper large-v3) and {up(*b1v[V])} "
                f"(wav2vec2-base-960h)",
                "No clear application-mode difference was established",
                f"VoIP minus audio was {up(*b1d[W])} and {up(*b1d[V])}",
                "no equivalence is claimed",
                "`application=audio`, retained to reproduce the codec configuration of the preliminary analysis",
                "`OPUS_APPLICATION_VOIP` was tested only as a post-confirmation sensitivity of the total penalty"]:
        if " ".join(tok.split()) not in main:
            fails.append(f"PRIMARY RESULT not in the main paper: {tok}")
    need("both recognisers returned NO_CLEAR_APPLICATION_DIFFERENCE", "B1 outcome (S7)")
    need("For Whisper large-v3 the upper bound is exactly zero", "B1 boundary case (S7)")
    need("MP3-compressed [@panayotov2015librispeech, Sec. 5]", "limitation: LibriVox MP3 source")
    need("generalisation to pristine-source recordings is limited", "limitation: LibriVox MP3 source")
    for f, text in TEXTS.items():
        for mt in re.finditer(r"pre-?regist\w*", re.sub(r"<!--.*?-->", "", text, flags=re.S), flags=re.I):
            fails.append(f"WORDING in {f}: '{mt.group(0)}' (use prospective specification / version sealing)")

    # final pre-submission cleanup: clarifications that must stay in the main paper, and the journal register
    # of its prose (outcome labels of the specifications live in the supplement and its tables)
    lp = {c: (float(S[c]["vs_lp_lsd_0_3k_db"]), float(S[c]["vs_lp_coherence_0_3500"])) for c in ("OPUS", "SILK")}
    for tok in [f"relative to LP, median LSD over 0–3 kHz was {lp['OPUS'][0]:.2f} dB and median coherence over "
                f"0–3.5 kHz {lp['OPUS'][1]:.3f}, against {lp['SILK'][0]:.2f} dB and {lp['SILK'][1]:.3f} for SILK at "
                f"40 kbit/s (relative to REF, the medians are the same to the precision shown",
                "Neither 24 nor 40 kbit/s showed a detectable residual relative to LP individually, although for "
                f"wav2vec2 their paired 24–40 kbit/s contrast resolved a smaller difference ({up(*D2440[V])};",
                "worsened in-band fidelity relative to REF",
                "The Whisper ratio is imprecise and is not invariant to the attribution definition or error weighting.",
                "For wav2vec2, the best-linear component was slightly less harmful than the primary control despite its "
                "lower gain and steeper high-frequency roll-off",
                "Whisper was decoded greedily without temperature fallback; the study therefore evaluates that fixed "
                "decoding configuration rather than the full default Whisper fallback heuristic, and the conclusions "
                "need not transfer unchanged to other decoding settings.",
                "The primary design was specified and version-sealed before any evaluation audio was decoded"]:
        if " ".join(tok.split()) not in main:
            fails.append(f"REQUIRED WORDING not in the main paper: {tok}")
    assert up(*a1d[V]).startswith(M) and a1d[V][2] < 0    # LIN8 - LP below zero for wav2vec2 (the sentence above)
    prose_main = re.sub(r"<!--.*?-->", "", TEXTS["taslp_submission.md"], flags=re.S)
    prose_main = "\n".join(l for l in prose_main.splitlines() if not l.startswith("|"))
    for mt in re.finditer(r"\b(?:CONDITIONAL GO|GO|KILL|HOLD|PROCEEDS?|FALSIFY|WEAKEN|SUPPORT|WB_BETTER|NB_BETTER|"
                          r"NO_CLEAR_\w+|STOPPED|ROBUST_RESIDUAL|DECODER_\w+|VOIP_\w+|kill test)\b", prose_main):
        fails.append(f"OUTCOME LABEL in the main paper (belongs in the supplement): {mt.group(0)}")
    for word, most in (("sealed", 1), ("frozen", 0), ("fresh-speaker", 1)):
        n_word = len(re.findall(rf"\b{word}\b", prose_main, flags=re.I))
        if n_word > most:
            fails.append(f"WORDING in the main paper: '{word}' {n_word} times (at most {most})")
    if "deterministic" in prose_main:
        fails.append("WORDING in the main paper: Whisper decoding is not to be called deterministic")

# ------------------------------------------------------------------ 6. table structure
# A caption paragraph (": ...") must follow its table after one blank line; anything else would
# let pandoc attach it to the next table instead.
for f, text in TEXTS.items():
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(": "):
            prev = next((l for l in reversed(lines[:i]) if l.strip()), "")
            if not prev.startswith("|"):
                fails.append(f"CAPTION NOT AFTER A TABLE in {f}: {line[:70]}")
        if line.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].startswith("|"):
            fails.append(f"TEXT DIRECTLY AFTER A TABLE in {f}: {lines[i + 1][:70]}")

# ------------------------------------------------------------------ 3. wording
FORBIDDEN = [r"\b(the |be )?first (to|study|studies|work|paper|time|demonstrat\w*|decomposition|systematic|attempt)\b",
             r"\bwe are the first\b", r"\bnovel\b", r"for the first time", r"unprecedented", r"no prior work",
             r"statistically indistinguishable", r"\bequivalent\b", r"caused by (in-band )?coding",
             r"byte-identical to the prior study\b", r"\bproves?\b",
             r"\bwideband (coding )?(is|was) (generally |universally |always )?(better|superior)\b",
             r"(?<!no )\bdecoder[-\s]+(independent|invariant)\b", r"\b(independent|invariant)\s+(of|to)\s+the\s+decoder\b",
             r"\buniversally superior\b"]
body = re.sub(r"<!--.*?-->", "", MS, flags=re.S)
for pat in FORBIDDEN:
    for mt in re.finditer(pat, body, flags=re.I):
        ctx = body[max(0, mt.start()-60): mt.end()+60].replace("\n", " ")
        fails.append(f"WORDING '{pat}': ...{ctx}...")

# ------------------------------------------------------------------ 4. figures, citations
for p in re.findall(r"\]\(([^)]+\.(?:png|pdf))\)", MS):
    if not (ROOT / "manuscript" / p).resolve().exists():
        fails.append(f"FIGURE missing: {p}")
bib = set(re.findall(r"^@\w+\{([^,]+),", (ROOT / "manuscript" / "references.bib").read_text(), re.M))
# a citation key follows an @ that is not inside a word (pandoc's rule), so e-mail addresses are not keys
for key in sorted(set(re.findall(r"(?<![\w.])@([A-Za-z0-9_]+)", body)) - bib):
    fails.append(f"CITATION missing in bib: {key}")

print(f"files: {', '.join(FILES)}")
print(f"table rows checked: {checked}")
print("RESULT:", "PASS" if not fails else f"{len(fails)} problem(s)")
for f in fails:
    print(" -", f)
sys.exit(1 if fails else 0)
