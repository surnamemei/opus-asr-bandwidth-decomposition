"""Generate manuscript tables from the frozen Stage 3 outputs (read-only).

Every table cell in manuscript/manuscript.md is copied from this script's output, and
check_numbers.py re-derives the same strings to verify the manuscript.
"""
import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S3 = ROOT / "results_paper" / "stage3_asr"
MINUS = "−"


def fmt(x, signed=False, dec=2):
    """Format with Unicode minus; keep 3 decimals for small non-zero values."""
    if x is None:
        return "—"
    d = dec
    if x != 0 and abs(x) < 0.01 and dec == 2:
        d = 3
    s = f"{abs(x):.{d}f}"
    if float(s) == 0 and x < 0:
        # a value that rounds to zero keeps its sign, e.g. -0.00
        return MINUS + s
    if x < 0:
        return MINUS + s
    return ("+" + s) if signed else s


def ci(est, lo, hi, signed=True, dec=2):
    return f"{fmt(est, signed, dec)} [{fmt(lo, signed, dec)}, {fmt(hi, signed, dec)}]"


def load(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


BOOT = load(S3 / "07_paired_bootstrap.csv")
CORPUS = load(S3 / "06_corpus_metrics.csv")

# The pilot rows of 07 must equal the sealed pilot bootstrap file.
_KEY = ("set", "model", "scope", "quantity", "kind")
_pilot_07 = {tuple(r[k] for k in _KEY): r["estimate"] for r in BOOT if r["set"] == "pilot"}
_pilot_file = {tuple(r[k] for k in _KEY): r["estimate"] for r in load(S3 / "pilot" / "pilot_bootstrap.csv")}
assert _pilot_07 and all(_pilot_file.get(k) == v for k, v in _pilot_07.items()), "pilot rows differ"


def b(set_, model, quantity, scope="pooled", kind="micro"):
    rows = [r for r in BOOT if r["set"] == set_ and r["model"] == model
            and r["quantity"] == quantity and r["scope"] == scope and r["kind"] == kind]
    if len(rows) != 1:
        raise KeyError((set_, model, quantity, scope, kind, len(rows)))
    r = rows[0]
    return float(r["estimate"]), float(r["ci_lower"]), float(r["ci_upper"])


def corpus(set_, model, condition, scope="pooled"):
    rows = [r for r in CORPUS if r["set"] == set_ and r["model"] == model
            and r["condition"] == condition and r["scope"] == scope]
    if len(rows) != 1:
        raise KeyError((set_, model, condition, scope, len(rows)))
    return rows[0]


MODELS = [("whisper", "Whisper large-v3"), ("wav2vec2", "wav2vec2-base-960h")]
CONDS = ["REF", "LP", "OPUS", "SILK", "NEG_LP", "NEG_CODEC"]
out = []

# ---------------------------------------------------------------- Table 2
out.append("TABLE 2 (confirmation corpus WER, %, 95% CI)")
out.append("| Condition | Whisper large-v3 | wav2vec2-base-960h |")
out.append("|---|---|---|")
for c in CONDS:
    cells = [ci(*b("confirmation", m, f"wer_{c}"), signed=False) for m, _ in MODELS]
    out.append(f"| {c} | " + " | ".join(cells) + " |")
out.append("")
for m, name in MODELS:
    errs = [corpus("confirmation", m, c)["word_errors"] for c in CONDS]
    words = corpus("confirmation", m, "REF")["n_words"]
    empty = sum(int(corpus("confirmation", m, c)["empty_hypotheses"]) for c in CONDS)
    out.append(f"{name}: word errors {dict(zip(CONDS, errs))} / {words} words; empty hyps {empty}")
out.append("")

# ---------------------------------------------------------------- Table 3
CONTRASTS = [
    ("delta_bw", "LP − REF (bandwidth component)"),
    ("delta_opus_residual", "OPUS − LP (codec-specific residual)"),
    ("delta_opus_total", "OPUS − REF (total)"),
    ("delta_silk_residual", "SILK − LP"),
    ("delta_silk_total", "SILK − REF"),
    ("opus_minus_silk", "OPUS − SILK"),
]
out.append("TABLE 3 (confirmation, pooled; pp; micro primary, macro secondary)")
out.append("| Contrast | Whisper micro | Whisper macro | wav2vec2 micro | wav2vec2 macro |")
out.append("|---|---|---|---|---|")
for q, label in CONTRASTS:
    cells = []
    for m, _ in MODELS:
        cells.append(ci(*b("confirmation", m, q)))
        cells.append(ci(*b("confirmation", m, q, kind="macro")))
    out.append(f"| {label} | " + " | ".join(cells) + " |")
for q, label in [("bw_share_of_opus_total", "Bandwidth share of OPUS − REF"),
                 ("bw_share_of_silk_total", "Bandwidth share of SILK − REF")]:
    cells = []
    for m, _ in MODELS:
        cells.append(ci(*b("confirmation", m, q, kind="ratio"), signed=False))
        cells.append("—")
    out.append(f"| {label} | " + " | ".join(cells) + " |")
out.append("")
out.append("CER micro:")
for m, name in MODELS:
    for q in ["delta_bw", "delta_opus_residual", "delta_silk_residual"]:
        out.append(f"  {name} {q}: {ci(*b('confirmation', m, q, kind='micro_cer'))}")
out.append("")
out.append("Relative effects (post hoc):")
for m, name in MODELS:
    ref = b("confirmation", m, "wer_REF")[0]
    lp = b("confirmation", m, "wer_LP")[0]
    bw = b("confirmation", m, "delta_bw")[0]
    res = b("confirmation", m, "delta_opus_residual")[0]
    tot = b("confirmation", m, "delta_opus_total")[0]
    sres = b("confirmation", m, "delta_silk_residual")[0]
    out.append(f"  {name}: bw/REF {100*bw/ref:+.1f}%, res/LP {100*res/lp:+.1f}%, "
               f"total/REF {100*tot/ref:+.1f}%, silkres/LP {100*sres/lp:+.1f}%")
out.append("")

# ---------------------------------------------------------------- Table S1 per subset
out.append("TABLE S1 (per subset; WER % and contrasts pp)")
out.append("| Subset | Model | REF | LP | OPUS | SILK | LP − REF | OPUS − LP | SILK − LP |")
out.append("|---|---|---|---|---|---|---|---|---|")
for sub in ["test-clean", "test-other"]:
    for m, name in MODELS:
        w = [fmt(b("confirmation", m, f"wer_{c}", scope=sub)[0]) for c in ["REF", "LP", "OPUS", "SILK"]]
        d = [ci(*b("confirmation", m, q, scope=sub)) for q in ["delta_bw", "delta_opus_residual", "delta_silk_residual"]]
        out.append(f"| {sub} | {name} | " + " | ".join(w + d) + " |")
out.append("")

# ---------------------------------------------------------------- Table S2 error types
out.append("TABLE S2 (error-type composition; Δ errors per 100 reference words)")
out.append("| Model | Contrast | Substitutions | Deletions | Insertions |")
out.append("|---|---|---|---|---|")
for m, name in MODELS:
    for q, label in [("delta_bw", "LP − REF"), ("delta_opus_residual", "OPUS − LP"),
                     ("delta_silk_residual", "SILK − LP")]:
        cells = [ci(*b("confirmation", m, f"{q}_{t}", kind="micro_error_type")) for t in "SDI"]
        out.append(f"| {name} | {label} | " + " | ".join(cells) + " |")
for m, name in MODELS:
    s = b("confirmation", m, "delta_opus_residual_S", kind="micro_error_type")[0]
    tot = b("confirmation", m, "delta_opus_residual")[0]
    out.append(f"  substitution share of OPUS − LP, {name}: {100*s/tot:.0f}%")
out.append("")

# ---------------------------------------------------------------- Table S3 negative controls
out.append("TABLE S3 (negative controls, pp)")
out.append("| Contrast | Whisper large-v3 | wav2vec2-base-960h |")
out.append("|---|---|---|")
for q, label in [("neg_lp_minus_ref", "NEG_LP − REF"), ("neg_codec_minus_ref", "NEG_CODEC − REF")]:
    cells = []
    for m, _ in MODELS:
        e, lo, hi = b("confirmation", m, q)
        dec = 3 if abs(e) < 0.01 else 2
        cells.append(ci(e, lo, hi, dec=dec) if dec == 3 else ci(e, lo, hi))
    out.append(f"| {label} | " + " | ".join(cells) + " |")
out.append("")

# ---------------------------------------------------------------- Table S4 pilot
out.append("TABLE S4 (pilot: dev-clean + dev-other)")
out.append("| | " + " | ".join(CONDS) + " |")
out.append("|---|" + "---|" * len(CONDS))
for m, name in MODELS:
    out.append(f"| {name} | " + " | ".join(fmt(b("pilot", m, f"wer_{c}")[0]) for c in CONDS) + " |")
out.append("")
out.append("| Contrast (micro, pp) | Whisper large-v3 | wav2vec2-base-960h |")
out.append("|---|---|---|")
for q, label in [("delta_bw", "LP − REF"), ("delta_opus_residual", "OPUS − LP"),
                 ("delta_silk_residual", "SILK − LP"), ("opus_minus_silk", "OPUS − SILK"),
                 ("neg_lp_minus_ref", "NEG_LP − REF"), ("neg_codec_minus_ref", "NEG_CODEC − REF")]:
    out.append(f"| {label} | " + " | ".join(ci(*b("pilot", m, q)) for m, _ in MODELS) + " |")
pilot_n = corpus("pilot", "whisper", "REF")
out.append(f"pilot n_utterances {pilot_n['n_utterances']}, speakers {pilot_n['n_speakers']}, words {pilot_n['n_words']}")
out.append("")

# ---------------------------------------------------------------- Table 4 signal
SUM = {r["condition"]: r for r in load(S3 / "09_signal_summary.csv") if r["set"] == "confirmation"}
POOL = [r for r in load(S3 / "09_signal_metrics_pooled.csv") if r["set"] == "confirmation"]
MAN = [r for r in load(S3 / "03_audio_manifest.csv") if r["set"] == "confirmation"]


def med(cond, col):
    vals = [float(r[col]) for r in MAN if r["condition"] == cond and r[col] not in ("", None)]
    return statistics.median(vals)


def pct(cond, col, q):
    vals = sorted(float(r[col]) for r in MAN if r["condition"] == cond and r[col] not in ("", None))
    k = (len(vals) - 1) * q
    lo = int(k)
    hi = min(lo + 1, len(vals) - 1)
    return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)


SIGCONDS = ["LP", "OPUS", "SILK", "NEG_LP", "NEG_CODEC"]
out.append("TABLE 4a (per-utterance medians vs REF, confirmation)")
out.append("| Descriptor | " + " | ".join(SIGCONDS) + " |")
out.append("|---|" + "---|" * len(SIGCONDS))
rows = [("LSD, full band (dB)", "vs_ref_lsd_db", 2),
        ("LSD, 0–3 kHz (dB)", "vs_ref_lsd_0_3k_db", 2),
        ("LSD, 0–4 kHz (dB)", "vs_ref_lsd_0_4k_db", 2),
        ("LSD, 4–8 kHz (dB)", "vs_ref_lsd_4_8k_db", 2),
        ("Retained bandwidth, power-based (Hz)", "vs_ref_retained_bandwidth_hz", 0),
        ("4–8 kHz power change (dB)", "vs_ref_hf_power_change_db", 1),
        ("Coherence, 0–3.5 kHz", "vs_ref_coherence_0_3500", 3)]
for label, col, dec in rows:
    cells = []
    for c in SIGCONDS:
        v = float(SUM[c][col])
        cells.append(f"{v:,.0f}" if dec == 0 else fmt(v, dec=dec) if dec != 1 else (MINUS if v < 0 else "") + f"{abs(v):.1f}")
    out.append(f"| {label} | " + " | ".join(cells) + " |")
cells = []
for c in SIGCONDS:
    v = med(c, "rms_change_db")
    cells.append((MINUS if v < 0 else "") + (f"{abs(v):.3f}" if abs(v) < 0.01 else f"{abs(v):.2f}"))
out.append("| RMS level change (dB) | " + " | ".join(cells) + " |")
out.append("")
out.append("vs LP (medians): " + ", ".join(
    f"{c}: LSD0-3 {float(SUM[c]['vs_lp_lsd_0_3k_db']):.2f}, coh {float(SUM[c]['vs_lp_coherence_0_3500']):.3f}, "
    f"env {float(SUM[c]['vs_lp_envelope_decorrelation']):.3f}" for c in ["OPUS", "SILK"]))
out.append(f"OPUS rms change p5 {pct('OPUS','rms_change_db',0.05):.2f}, p95 {pct('OPUS','rms_change_db',0.95):.2f}")
for c in ["OPUS", "SILK", "NEG_CODEC"]:
    out.append(f"{c}: median bitrate {med(c,'measured_bitrate_kbps'):.2f} kbps; "
               f"min share expected config {min(float(r['share_expected_configuration']) for r in MAN if r['condition']==c):.3f}")
for c in ["LP", "OPUS", "SILK", "NEG_LP", "NEG_CODEC"]:
    lags = sorted(set(int(float(r["lag_vs_ref_samples"])) for r in MAN if r["condition"] == c))
    clips = sum(int(r["clip_count"]) for r in MAN if r["condition"] == c)
    peak = max(float(r["peak"]) for r in MAN if r["condition"] == c)
    out.append(f"{c}: lags {lags}; clip_count total {clips}; max peak {peak:.2f}")
tot_samples = sum(int(r["num_samples"]) for r in MAN if r["condition"] == "REF")
tot_dur = sum(float(r["duration_s"]) for r in MAN if r["condition"] == "REF")
out.append(f"REF samples {tot_samples:.3e}; duration {tot_dur:.1f} s")
out.append("")
out.append("TABLE 4b (pooled cross-spectral, confirmation)")
out.append("| Descriptor | LP | OPUS | SILK |")
out.append("|---|---|---|---|")
P = {(r["reference"], r["processed"]): r for r in POOL}
prow = [("Coherent bandwidth (Hz)", "coherent_bandwidth_hz", "hz"),
        ("Coherent 4–8 kHz power (dB)", "coherent_hf_power_db", 1),
        ("Total 4–8 kHz power (dB)", "total_hf_power_db", 1),
        ("Mirror coherence, 4.1–4.9 kHz", "image_coherence_4100_4900", 3),
        ("In-band gain $\\lvert H_1\\rvert$, 0.5–2 kHz (dB)", "h1_level_db", 2),
        ("Mean coherence, 0–3.5 kHz", "mean_coherence_0_3500", 3)]
for label, col, dec in prow:
    cells = []
    for c in ["LP", "OPUS", "SILK"]:
        v = float(P[("REF", c)][col])
        if dec == "hz":
            cells.append(f"{v:,.0f}")
        else:
            s = f"{abs(v):.{dec}f}"
            cells.append((MINUS if v < 0 and float(s) != 0 else "") + s)
    out.append(f"| {label} | " + " | ".join(cells) + " |")
out.append("")

# ---------------------------------------------------------------- exploratory
EX = [r for r in load(S3 / "11_exploratory_signal_correlations.csv") if r["set"] == "confirmation"]
sig = [r for r in EX if r["excludes_zero"] == "True"]
out.append(f"Exploratory correlations: {len(EX)} total, {len(sig)} exclude 0; max |rho| of those "
           f"{max(abs(float(r['spearman'])) for r in sig):.3f}")
for r in sig:
    out.append(f"  {r['codec']}/{r['model']} {r['feature']}: {float(r['spearman']):+.3f} "
               f"[{float(r['ci_lower']):+.3f}, {float(r['ci_upper']):+.3f}]")

# ---------------------------------------------------------------- selection
SEL = load(S3 / "02_dataset_selection.csv")
for s in ["calibration", "pilot", "confirmation"]:
    rs = [r for r in SEL if r["set"] == s]
    spk = len(set(r["speaker_id"] for r in rs))
    dur = sum(float(r["duration_s"]) for r in rs)
    subs = {}
    for r in rs:
        subs.setdefault(r["subset"], set()).add(r["speaker_id"])
    out.append(f"selection {s}: {len(rs)} utts, {spk} speakers, {dur:.1f} s, "
               + ", ".join(f"{k}: {len(v)} spk / {sum(1 for r in rs if r['subset']==k)} utts" for k, v in subs.items()))

# ================================================================ TASLP upgrade (sealed outputs)
UP = ROOT / "results_paper" / "taslp_upgrade"


def sealed(path, key):
    """A sealed JSON record, refused if its body no longer matches its own hash."""
    import hashlib
    record = json.loads(Path(path).read_text())
    body = json.dumps({k: v for k, v in record.items() if k != key}, sort_keys=True).encode()
    assert hashlib.sha256(body).hexdigest() == record[key], f"{path} changed after sealing"
    return record


def file_sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


SPEC = sealed(ROOT / "paper" / "taslp_upgrade" / "upgrade_spec.json", "spec_sha256")
A_DEC = sealed(UP / "level" / "analysis" / "level_decision.json", "decision_sha256")
B_DEC = sealed(UP / "sweep" / "analysis" / "sweep_decision.json", "decision_sha256")
A_REG = sealed(UP / "level" / "regeneration" / "regeneration_report.json", "report_sha256")
B_VAL = sealed(UP / "sweep" / "validation" / "validation_report.json", "report_sha256")
assert file_sha256(UP / "level" / "analysis" / "level_bootstrap.csv") == A_DEC["bootstrap_sha256"]
assert file_sha256(UP / "sweep" / "analysis" / "sweep_bootstrap.csv") == B_DEC["bootstrap_sha256"]
A_BOOT = load(UP / "level" / "analysis" / "level_bootstrap.csv")
B_BOOT = load(UP / "sweep" / "analysis" / "sweep_bootstrap.csv")
LM = "OPUS8_LEVEL_MATCHED"
RATES = [8, 12, 16, 24, 40]


def ub(boot, model, quantity, scope="pooled", kind="micro"):
    rows = [r for r in boot if r["model"] == model and r["quantity"] == quantity
            and r["scope"] == scope and r["kind"] == kind]
    if len(rows) != 1:
        raise KeyError((model, quantity, scope, kind, len(rows)))
    num = lambda v: float(v) if v != "" else float("nan")    # descriptive rows have no interval
    return num(rows[0]["estimate"]), num(rows[0]["ci_lower"]), num(rows[0]["ci_upper"])


def a(model, quantity, scope="pooled", kind="micro"):
    return ub(A_BOOT, model, quantity, scope, kind)


def sw(model, quantity, scope="pooled", kind="micro"):
    return ub(B_BOOT, model, quantity, scope, kind)


def row(label, cells):
    return f"| {label} | " + " | ".join(cells) + " |"


# ---------------------------------------------------------------- Table 5: addition A
LV_MAN = load(UP / "level" / "raw" / "audio_manifest.csv")
REPRO = load(UP / "level" / "analysis" / "reproduction_check.csv")
N_A = int(A_REG["n_utterances"])
out.append("TABLE 5 (addition A: level-matched sensitivity, pooled, 95% CI)")
out.append(row("Addition A (pooled)", [n for _, n in MODELS]))
out.append("|---|---|---|")
for c, label in [("LP", "Corpus WER, LP, same run (%)"), ("OPUS", "Corpus WER, OPUS, same run (%)"),
                 (LM, "Corpus WER, OPUS8_LEVEL_MATCHED (%)")]:
    out.append(row(label, [ci(*a(m, f"wer_{c}"), signed=False) for m, _ in MODELS]))
out.append(row("OPUS8_LEVEL_MATCHED − LP (pp; primary)", [ci(*a(m, "L_level_matched_minus_lp")) for m, _ in MODELS]))
out.append(row("OPUS8_LEVEL_MATCHED − OPUS (pp)", [ci(*a(m, "K_level_matched_minus_opus"), dec=3) for m, _ in MODELS]))
out.append(row("OPUS − LP, same run (pp)", [ci(*a(m, "T_opus_minus_lp")) for m, _ in MODELS]))
out.append(row("OPUS − LP, confirmatory run (pp)", [ci(SPEC["A"]["anchors"][m]["T_star"]["estimate"],
                                               *SPEC["A"]["anchors"][m]["T_star"]["ci"]) for m, _ in MODELS]))
out.append(row("Share of the confirmatory residual retained", [f"{A_DEC['cells'][m]['retained_fraction_L_over_T_star']:.2f}"
                                                          for m, _ in MODELS]))
out.append(row("GO: lower bound of OPUS8_LEVEL_MATCHED − OPUS above",
               [fmt(A_DEC["cells"][m]["go_threshold_K_lower"], True, 3) for m, _ in MODELS]))
out.append(row("FALSIFY: its upper bound below",
               [fmt(A_DEC["cells"][m]["falsify_threshold_K_upper"], True, 3) for m, _ in MODELS]))
out.append(row("Hypotheses changed by level matching",
               [f"{A_DEC['hypotheses_changed_by_level_matching'][m]} of {N_A:,}" for m, _ in MODELS]))
out.append(row("Outcome (frozen rule)", [A_DEC["cells"][m]["outcome"] for m, _ in MODELS]))
out.append("")
g = A_REG["gain_db"]
out.append(f"A gates {A_REG['gates']} verdict {A_REG['verdict']}; gain median {g['median']:+.3f} dB, "
           f"p05 {g['p05']:+.3f}, p95 {g['p95']:+.3f}, range {g['min']:+.3f} to {g['max']:+.3f} dB; "
           f"max level error {A_REG['max_abs_level_error_db']:.1e} dB; max gain error "
           f"{A_REG['max_abs_gain_reproduction_error_db']:.1e} dB; overall outcome {A_DEC['outcome']}")
for c in ["LP", "OPUS", LM]:
    rs = [r for r in LV_MAN if r["condition"] == c]
    out.append(f"A {c}: full-scale samples {sum(int(r['clip_count']) for r in rs)} in "
               f"{sum(int(r['clip_count']) > 0 for r in rs)} utterances; max peak {max(float(r['peak']) for r in rs):.3f}")
out.append("A reproduction check: " + "; ".join(f"{r['model']} {r['condition']} {r['differing']} of {r['n']} differ"
                                                for r in REPRO))
for m, _ in MODELS:
    for q, word in [("S", "substitutions"), ("D", "deletions"), ("I", "insertions")]:
        e = a(m, f"L_level_matched_minus_lp_{q}", kind="micro_error_type")
        out.append(f"A {m} L {word}: {ci(*e)}")
out.append("")

# ---------------------------------------------------------------- Tables 6-8: addition B
# (manuscript order: Table 6 residuals, Table 7 trend and decision, Table 8 descriptors)
SW_SIG = {r["condition"]: r for r in load(UP / "sweep" / "analysis" / "sweep_descriptors.csv")}
SW_POOL = {(r["reference"], r["processed"]): r for r in load(UP / "sweep" / "analysis" / "sweep_pooled_transfer.csv")}
SW_ROWS = load(UP / "sweep" / "validation" / "validation_rows.csv")
SW_SEL = sealed(ROOT / "paper" / "taslp_upgrade" / "selection_sweep.json", "selection_sha256")
payload = B_VAL["measured_median_payload_kbps"]
out.append("TABLE 6 (addition B: residual beyond LP by rate, pooled, 95% CI)")
out.append(row("Condition (addition B)", ["Median payload (kbit/s)"] + [n for _, n in MODELS]))
out.append("|---|---|---|---|")
out.append(row("LP, corpus WER (%)", ["—"] + [ci(*sw(m, "wer_LP"), signed=False) for m, _ in MODELS]))
for rate, p in zip(RATES, payload):
    out.append(row(f"SILK{rate} − LP", [f"{p:.2f}"] + [ci(*sw(m, f"R_{rate}")) for m, _ in MODELS]))
out.append("")

SWC = ["LP"] + [f"SILK{r}" for r in RATES]
out.append("TABLE 8 (addition B: descriptors; per-utterance medians and pooled vs REF)")
out.append(row("Descriptor (addition B)", SWC))
out.append("|---|" + "---|" * len(SWC))


def cell(v, dec):
    if v in ("", None):
        return "—"
    v = float(v)
    return (MINUS if v < 0 and float(f"{abs(v):.{dec}f}") != 0 else "") + f"{abs(v):.{dec}f}"


for label, col, dec in [("LSD, 0–3 kHz, vs LP (dB)", "LSD 0-3 kHz vs LP (dB)", 2),
                        ("Coherence, 0–3.5 kHz, vs LP", "coherence 0-3.5 kHz vs LP", 3),
                        ("RMS level change vs REF (dB)", "rms_change_db vs REF", 2)]:
    out.append(row(label, [cell(SW_SIG[c][col], dec) for c in SWC]))
for label, col, dec in [("In-band gain $\\lvert H_1\\rvert$ vs REF, 0.5–2 kHz (dB)", "h1_level_db", 2),
                        ("Mirror coherence vs REF, 4.1–4.9 kHz", "image_coherence_4100_4900", 3),
                        ("Total 4–8 kHz power vs REF (dB)", "total_hf_power_db", 1)]:
    out.append(row(label, [cell(SW_POOL[("REF", c)][col], dec) for c in SWC]))
out.append("")

out.append("TABLE 7 (addition B: trend, contrasts and decision, pooled, 95% CI)")
out.append(row("Addition B (pooled)", [n for _, n in MODELS]))
out.append("|---|---|---|")
out.append(row("Slope on log2 bitrate (pp per doubling; primary)", [ci(*sw(m, "S_log2", kind="trend"), dec=3) for m, _ in MODELS]))
out.append(row("Slope implied by the confirmation, S*", [fmt(B_DEC["cells"][m]["S_star"], True, 3) for m, _ in MODELS]))
out.append(row("GO: lower bound of the slope at or below 0.5 S*",
               [fmt(B_DEC["cells"][m]["meaningful_decline_threshold"], True, 3) for m, _ in MODELS]))
out.append(row("Slope on rate rank (pp per step)", [ci(*sw(m, "S_rank", kind="trend"), dec=3) for m, _ in MODELS]))
out.append(row("Slope on log2 measured payload (pp per doubling)",
               [ci(*sw(m, "S_log2_measured", kind="trend"), dec=3) for m, _ in MODELS]))
for x, y in zip(RATES, RATES[1:]):
    out.append(row(f"SILK{x} − SILK{y}", [ci(*sw(m, f"D_{x}_{y}")) for m, _ in MODELS]))
out.append(row("SILK8 − SILK40", [ci(*sw(m, "E_8_40")) for m, _ in MODELS]))
out.append(row("Adjacent declines, point estimates", [f"{sw(m, 'n_adjacent_declines', kind='descriptive')[0]:.0f} of 4"
                                                      for m, _ in MODELS]))
out.append(row("Replicates with a monotone decline", [f"{sw(m, 'share_replicates_monotone_non_increasing', kind='descriptive')[0]:.2f}"
                                                     for m, _ in MODELS]))
out.append(row("Outcome (frozen rule)", [B_DEC["cells"][m]["outcome"] for m, _ in MODELS]))
out.append("")
out.append(f"B gates {B_VAL['gates']} verdict {B_VAL['verdict']}; container kbps "
           + ", ".join(f"{v:.2f}" for v in B_VAL["median_container_kbps"])
           + "; payload vs nominal " + ", ".join(f"{100*(p/r-1):+.1f} %" for p, r in zip(payload, RATES))
           + "; adjacent ratios " + ", ".join(f"{v:.2f}" for v in B_VAL["adjacent_ratios"])
           + f"; bridge share {B_VAL['bridge_share_silk8_identical_to_stage3_opus_settings']:.2f}; overall {B_DEC['outcome']}")
coded = [r for r in SW_ROWS if r["condition"] != "LP"]
out.append(f"B packets per rate {sum(int(float(r['num_packets'])) for r in coded if r['condition'] == 'SILK8'):,}; "
           f"min share config 1 {min(float(r['share_expected_config']) for r in coded):.3f}")
for m, _ in MODELS:
    for q, word in [("S", "substitutions"), ("D", "deletions"), ("I", "insertions")]:
        out.append(f"B {m} R_8 {word}: {ci(*sw(m, f'R_8_{q}', kind='micro_error_type'))}")
out.append(f"B selection: {SW_SEL['n_utterances']:,} utts, {SW_SEL['n_speakers']} speakers "
           f"{SW_SEL['speakers_by_subset']}, {SW_SEL['subsets']}, {SW_SEL['duration_hours']:.2f} h, "
           f"{SW_SEL['normalised_reference_words']:,} words")
out.append("")

# ---------------------------------------------------------------- Table S5: upgrade per subset
out.append("TABLE S5 (upgrade, per subset, secondary) [full manuscript]")
out.append("| Subset | Model | SILK8 − LP | Slope (pp per doubling) | OPUS8_LEVEL_MATCHED − LP | OPUS8_LEVEL_MATCHED − OPUS |")
out.append("|---|---|---|---|---|---|")
for s in ["test-clean", "test-other"]:
    for m, name in MODELS:
        out.append(row(s, [name, ci(*sw(m, "R_8", scope=s)), ci(*sw(m, "S_log2", scope=s, kind="trend"), dec=3),
                           ci(*a(m, "L_level_matched_minus_lp", scope=s)),
                           ci(*a(m, "K_level_matched_minus_opus", scope=s), dec=3)]))
out.append("")

# ---------------------------------------------------------------- Table S5 split (submission supplement)
# the same cells as Table S5, one table per addition, so that neither needs shrinking
out.append("TABLE S5A (addition A, per subset, secondary) [submission]")
out.append("| Subset | Model | OPUS8_LEVEL_MATCHED − LP | OPUS8_LEVEL_MATCHED − OPUS |")
out.append("|---|---|---|---|")
for s in ["test-clean", "test-other"]:
    for m, name in MODELS:
        out.append(row(s, [name, ci(*a(m, "L_level_matched_minus_lp", scope=s)),
                           ci(*a(m, "K_level_matched_minus_opus", scope=s), dec=3)]))
out.append("")
out.append("TABLE S5B (addition B, per subset, secondary) [submission]")
out.append("| Subset | Model | SILK8 − LP | Slope (pp per doubling) |")
out.append("|---|---|---|---|")
for s in ["test-clean", "test-other"]:
    for m, name in MODELS:
        out.append(row(s, [name, ci(*sw(m, "R_8", scope=s)), ci(*sw(m, "S_log2", scope=s, kind="trend"), dec=3)]))
out.append("")

# ---------------------------------------------------------------- Table S6: sweep WER by condition
out.append("TABLE S6 (addition B: corpus WER by condition, %, 95% CI)")
out.append(row("Condition (addition B, WER %)", [n for _, n in MODELS]))
out.append("|---|---|---|")
for c in SWC:
    out.append(row(c, [ci(*sw(m, f"wer_{c}"), signed=False) for m, _ in MODELS]))
out.append("")

print("\n".join(out))
