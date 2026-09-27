"""Generate manuscript tables from the frozen Stage 3 outputs and the later sealed analyses (read-only).

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

# ================================================================ Reviewer-concern sensitivity analyses R1-R3 (sealed outputs)
RV = ROOT / "results_paper" / "reviewer_sensitivity"
R_DEC = sealed(RV / "analysis" / "reviewer_decision.json", "decision_sha256")
R3_DEC = sealed(RV / "analysis" / "r3_decision.json", "decision_sha256")
R3_DESC = sealed(RV / "analysis" / "r3_descriptives.json", "descriptives_sha256")
R_VAL = sealed(RV / "validation" / "validation_report.json", "report_sha256")
R_SWEEP = sealed(RV / "validation" / "sweep_report.json", "report_sha256")
R_SIGNAL = sealed(RV / "validation" / "signal_report.json", "report_sha256")
R_EXPL = sealed(RV / "exploratory" / "post_gate_diagnosis.json", "diagnosis_sha256")
assert R_DEC["decisions"]["R3"] == R3_DEC["decision_sha256"] and R3_DESC["r3_decision_sha256"] == R3_DEC["decision_sha256"]
assert file_sha256(RV / "analysis" / "sweep_bootstrap.csv") == R_DEC["bootstrap_sha256"]["sweep_bootstrap.csv"]
assert R_VAL["parts"]["sweep"] == R_SWEEP["report_sha256"] and R_VAL["parts"]["signal"] == R_SIGNAL["report_sha256"]
assert R_DEC["outcomes"]["R1"] == R_DEC["outcomes"]["R2"] == "STOPPED" and not R_VAL["R1"]["pass"] and not R_VAL["R2"]["pass"]
assert R_VAL["R3"]["pass"] and R_EXPL["inputs"]["signal_report_sha256"] == R_SIGNAL["report_sha256"]
R3_BOOT = load(RV / "analysis" / "sweep_bootstrap.csv")
R3_OUT = {m: R3_DEC["cells"][m]["outcome"] for m, _ in MODELS}


def r3(model, quantity, scope="pooled", kind="micro"):
    return ub(R3_BOOT, model, quantity, scope, kind)


# ---------------------------------------------------------------- Table S13: R3 WER and W
out.append("TABLE S13 (R3: forced wideband vs forced narrowband at 8 kbit/s, practical counterfactual) [submission]")
out.append("| Scope | Recogniser | WER NB8 (%) | WER WB8 (%) | WB8 − NB8 (pp) | Outcome (frozen rule) |")
out.append("|---|---|---|---|---|---|")
for scope in ["pooled", "test-clean", "test-other"]:
    for m, name in MODELS:
        out.append(row(scope, [name, ci(*r3(m, "wer_NB8", scope), signed=False), ci(*r3(m, "wer_WB8", scope), signed=False),
                               ci(*r3(m, "W", scope)), R3_OUT[m] if scope == "pooled" else "— (secondary)"]))
out.append("")

# ---------------------------------------------------------------- Table S14: R3 packets and descriptors
R3_MED = R3_DESC["signal_descriptor_medians"]
R3_POOL = R3_DESC["pooled_against_ref"]
R3_HYP = R3_DESC["hypothesis_differences"]
R3_PAY = R_SWEEP["median_payload_kbps"]
out.append("TABLE S14 (R3: packets and signal descriptors; medians over utterances or pooled against REF) [submission]")
out.append("| Descriptor | NB8 | WB8 |")
out.append("|---|---|---|")
out.append(row("Median payload bitrate (kbit/s)", [f"{R3_PAY['NB8']:.2f}", f"{R3_PAY['WB8']:.2f}"]))
for label, key, dec in [("Coherence with REF, 0–3.5 kHz (median)", "coherence 0-3.5 kHz vs REF", 3),
                        ("LSD vs REF, 0–3 kHz (dB, median)", "LSD 0-3 kHz vs REF (dB)", 2),
                        ("4–8 kHz power change vs REF (dB, median)", "4-8 kHz power change vs REF (dB)", 2)]:
    out.append(row(label, [cell(R3_MED["NB8"][key], dec), cell(R3_MED["WB8"][key], dec)]))
for label, key, dec in [("Coherent bandwidth vs REF (Hz, pooled)", "coherent_bandwidth_hz", 0),
                        ("Total 4–8 kHz power vs REF (dB, pooled)", "total_hf_power_db", 2)]:
    out.append(row(label, [cell(R3_POOL["NB8"][key], dec), cell(R3_POOL["WB8"][key], dec)]))
out.append(row("Raw hypotheses differing from NB8 (Whisper; wav2vec2)",
               ["—", f"{R3_HYP['whisper']['nb8_vs_wb8_raw_hypothesis_differs']}; "
                     f"{R3_HYP['wav2vec2']['nb8_vs_wb8_raw_hypothesis_differs']}"]))
out.append("")

# ---------------------------------------------------------------- R1 and R2: failed held-out criteria; exploratory diagnosis
import re as _re
R1_G6 = next(g for g in R_SIGNAL["R1-V"]["gates"] if g["gate"] == 6)
assert R1_G6["status"] == "FAIL" and R_SIGNAL["R1-V"]["control"] == "LP_LIBOPUS"
R1_RMS = float(_re.search(r"RMS ([\d.]+) dB over \[3000\.0, 4200\.0\] Hz", R1_G6["evidence"]).group(1))
R1_TOL = sealed(ROOT / "results_paper" / "lowpass_confirmation" / "revised_spec.json", "spec_sha256")["revised_tolerances"]
assert R1_TOL["g6_h1_rms_band_hz"] == [3000.0, 4200.0]     # R1-V: the revised Stage 2B tolerances, unchanged
R2_V3 = R_SIGNAL["R2-V"]["gates"]["R2-V3"]
assert not R2_V3["pass"]
R2_TOL = {k: v["value"] for k, v in
          sealed(ROOT / "paper" / "reviewer_sensitivity" / "reviewer_spec.json", "spec_sha256")["R2"]["tolerances"].items()}
R_DELAY = R_EXPL["silk40_alignment_dependence"]["libopus_delay_samples_16k"]
R_STAB = R_EXPL["silk40_alignment_dependence"]["max_abs_calibration_minus_validation_db_3000_4150"]
out.append("R1 AND R2: STOPPED BEFORE ASR, FAILED HELD-OUT TRANSITION-SHAPE CRITERIA [submission]")
out.append(f"R1-V gate 6 (LP_LIBOPUS vs libopus SILK40): RMS {R1_RMS:.2f} dB over "
           f"{R1_TOL['g6_h1_rms_band_hz'][0] / 1000:.1f}–{R1_TOL['g6_h1_rms_band_hz'][1] / 1000:.1f} kHz, "
           f"limit {R1_TOL['g6_h1_rms_max_db']:.1f} dB")
out.append(f"R2-V3 (SURR8): RMS {R2_V3['rms_db']:.2f} dB, limit {R2_TOL['V3_rms_max_db']:.1f} dB; "
           f"maximum {R2_V3['max_abs_db']:.2f} dB, limit {R2_TOL['V3_abs_max_db']:.1f} dB")
out.append("EXPLORATORY POST-GATE DIAGNOSIS (post hoc; not part of any rule) [submission]")
out.append(f"libopus delay, median samples at 16 kHz: calibration {R_DELAY['calibration']['median']:.2f}, "
           f"validation {R_DELAY['validation']['median']:.2f}; largest calibration-validation |H1| difference "
           f"(3.0-4.15 kHz): libopus, fixed alignment {R_STAB['libopus_fixed0']:.2f} dB; FFmpeg "
           f"{R_STAB['ffmpeg_fixed2']:.2f} dB; libopus, frozen alignment {R_STAB['libopus_frozen']:.2f} dB")
out.append("")

# ================================================================ R4: reference-decoder total-penalty sensitivity (sealed outputs)
R4R = ROOT / "results_paper" / "decoder_sensitivity"
R4_DEC = sealed(R4R / "analysis" / "r4_decision.json", "decision_sha256")
R4_VAL = sealed(R4R / "validation" / "validation_report.json", "report_sha256")
R4_DESC = sealed(R4R / "analysis" / "r4_descriptives.json", "descriptives_sha256")
R4_RAW = sealed(R4R / "raw" / "outputs_sha256.json", "outputs_sha256")
assert file_sha256(R4R / "analysis" / "r4_bootstrap.csv") == R4_DEC["bootstrap_sha256"]
assert file_sha256(R4R / "validation" / "validation_rows.csv") == R4_VAL["rows_sha256"]
assert R4_DESC["r4_decision_sha256"] == R4_DEC["decision_sha256"] and R4_DEC["outputs_sha256"] == R4_RAW["outputs_sha256"]
assert R4_VAL["pass"] and R4_DEC["anchor_reproduction"]["pass"] and R4_VAL["gates"]["G9"]["pass"]
R4_BOOT = load(R4R / "analysis" / "r4_bootstrap.csv")
R4_OUT = {m: R4_DEC["cells"][m]["outcome"] for m, _ in MODELS}
R4_DIAG = R4_VAL["diagnostics"]
R4_ROWS = load(R4R / "validation" / "validation_rows.csv")


def r4(model, quantity, scope="pooled"):
    return ub(R4_BOOT, model, quantity, scope, "micro")


out.append("TABLE S15 (R4: reference-decoder sensitivity of the total penalty, pooled) [submission]")
out.append("| Pooled (confirmation set) | Whisper large-v3 | wav2vec2-base-960h |")
out.append("|---|---|---|")
for label, q, signed in [("WER, REF (%)", "wer_REF", False), ("WER, OPUS_FFMPEG (%)", "wer_OPUS_FFMPEG", False),
                         ("WER, OPUS_LIBOPUS (%)", "wer_OPUS_LIBOPUS", False),
                         ("T_ffmpeg = OPUS_FFMPEG − REF (pp)", "T_ffmpeg", True),
                         ("T_libopus = OPUS_LIBOPUS − REF (pp)", "T_libopus", True),
                         ("D = OPUS_LIBOPUS − OPUS_FFMPEG (pp)", "D", True)]:
    out.append(row(label, [ci(*r4(m, q), signed=signed) for m, _ in MODELS]))
out.append(row("Outcome (frozen rule)", [R4_OUT[m] for m, _ in MODELS]))
out.append("")
out.append("TABLE S16 (R4 per subset, secondary) [submission]")
out.append("| Subset | Recogniser | WER, OPUS_LIBOPUS (%) | T_ffmpeg (pp) | T_libopus (pp) | D (pp) |")
out.append("|---|---|---|---|---|---|")
for scope in ["test-clean", "test-other"]:
    for m, name in MODELS:
        out.append(row(scope, [name, ci(*r4(m, "wer_OPUS_LIBOPUS", scope), signed=False),
                               ci(*r4(m, "T_ffmpeg", scope)), ci(*r4(m, "T_libopus", scope)), ci(*r4(m, "D", scope))]))
out.append("")


def lag_cell(counts):
    return "; ".join(f"{k}: {int(v):,}" for k, v in counts.items())


S3_OPUS_MAN = [r for r in load(ROOT / "results_paper" / "stage3_asr" / "raw" / "confirmation" / "audio_manifest.csv")
               if r["condition"] == "OPUS"]
R4_CLIPS = {"OPUS_FFMPEG": (sum(int(r["clip_count"]) for r in S3_OPUS_MAN), sum(int(r["clip_count"]) > 0 for r in S3_OPUS_MAN)),
            "OPUS_LIBOPUS": (sum(int(r["libopus_clip_count"]) for r in R4_ROWS),
                             sum(int(r["libopus_clip_count"]) > 0 for r in R4_ROWS))}
out.append("TABLE S17 (R4 descriptive decoder and signal diagnostics; no descriptor enters the rule) [submission]")
out.append("| Descriptor (against REF; descriptive) | OPUS_FFMPEG | OPUS_LIBOPUS |")
out.append("|---|---|---|")
dF, dL = R4_DIAG["OPUS_FFMPEG"], R4_DIAG["OPUS_LIBOPUS"]
out.append(row("Integer lag (samples: utterances)", [lag_cell(dF["lag_vs_ref_counts"]), lag_cell(dL["lag_vs_ref_counts"])]))
out.append(row("RMS change, median [5th, 95th percentile] (dB)",
               [f"{fmt(d['rms_change_db']['median'])} [{fmt(d['rms_change_db']['p05'])}, {fmt(d['rms_change_db']['p95'])}]"
                for d in (dF, dL)]))
out.append(row("4–5 kHz power (dB, pooled)", [fmt(d["pooled_power_4000_5000_db"]) for d in (dF, dL)]))
out.append(row("Total 4–8 kHz power (dB, pooled)", [fmt(d["pooled_total_hf_power_4000_8000_db"]) for d in (dF, dL)]))
out.append(row("Mirror coherence, 4.1–4.9 kHz (pooled)", [f"{d['pooled_mirror_coherence_4100_4900']:.3f}" for d in (dF, dL)]))
out.append(row("Samples at or above full scale (utterances)",
               [f"{R4_CLIPS[c][0]} ({R4_CLIPS[c][1]})" for c in ["OPUS_FFMPEG", "OPUS_LIBOPUS"]]))
out.append("")
dd, rep = R4_DIAG["decoder_difference"], R4_DIAG["reproduction"]
n4 = rep["of"]
out.append("R4 DECODER DIFFERENCE, REPRODUCTION AND TRANSCRIPTS [submission]")
out.append(f"FFmpeg vs libopus, same bitstream: bit-identical {dd['bit_identical']} of {n4:,}; SNR median "
           f"{dd['snr_unaligned_db']['median']:.2f} dB unaligned (minimum {dd['snr_unaligned_db']['min']:.2f}), "
           f"{dd['snr_one_sample_db']['median']:.2f} dB after the better one-sample shift (minimum "
           f"{dd['snr_one_sample_db']['min']:.2f}); shift −1 in {dd['one_sample_shift_counts']['-1']:,}, "
           f"+1 in {dd['one_sample_shift_counts']['1']}")
out.append(f"reproduction: FFmpeg re-decode = Stage 3 {rep['ffmpeg_identical_to_stage3']:,} of {n4:,}; libopus = earlier "
           f"libopus decode {rep['libopus_identical_to_r1_refdec']:,} of {n4:,}")
H = R4_DESC["hypothesis_differences"]
out.append("transcripts differing from OPUS_FFMPEG (raw; normalised): " + "; ".join(
    f"{m} {H[m]['raw_hypothesis_differs']}; {H[m]['normalised_hypothesis_differs']} of {H[m]['utterances']:,} ("
    + ", ".join(f"{s} {v['raw_hypothesis_differs']}; {v['normalised_hypothesis_differs']}" for s, v in H[m]["by_subset"].items())
    + ")" for m, _ in MODELS))
out.append(f"R4 gates: G1 {R4_VAL['gates']['G1']['identical']:,} of {n4:,}; G2 decoded {R4_VAL['gates']['G2']['decoded']:,}, "
           f"errors {len(R4_VAL['gates']['G2']['decode_errors'])}; G3 {R4_VAL['gates']['G3']['pass']}; "
           f"G4 non-finite {R4_VAL['gates']['G4']['nonfinite_48k'] + R4_VAL['gates']['G4']['nonfinite_16k']}; "
           f"G5 {R4_VAL['gates']['G5']['pass']}; G7 {R4_VAL['gates']['G7']['pass']}; G9 {R4_VAL['gates']['G9']['pass']}")
out.append("")

# ================================================================ Final invariance pass (sealed outputs): A1, C1
FIR = ROOT / "results_paper" / "final_invariance"
A1_DEC = sealed(FIR / "A1_DECISION.json", "decision_sha256")
A1_EVAL = sealed(FIR / "a1_evaluation" / "evaluation_report.json", "report_sha256")
A1_CAL = sealed(FIR / "a1_calibration" / "signal_report.json", "report_sha256")
A1_VAL = sealed(FIR / "a1_validation" / "validation_report.json", "report_sha256")
A1_RAW = sealed(FIR / "a1_raw" / "outputs_sha256.json", "outputs_sha256")
assert file_sha256(FIR / "a1_bootstrap.csv") == A1_DEC["bootstrap_sha256"]
assert file_sha256(FIR / "a1_evaluation" / "evaluation_rows.csv") == A1_EVAL["rows_sha256"]
assert A1_DEC["outputs_sha256"] == A1_RAW["outputs_sha256"] and A1_DEC["anchor_reproduction"]["pass"]
assert A1_EVAL["pass"] and A1_VAL["pass"] and A1_CAL["pass"]
A1_BOOT = load(FIR / "a1_bootstrap.csv")
A1_ROWS = load(FIR / "a1_evaluation" / "evaluation_rows.csv")


def a1(model, quantity, scope="pooled", kind="micro"):
    return ub(A1_BOOT, model, quantity, scope, kind)


out.append("TABLE A1 (inclusive best-linear attribution of the 8 kbit/s output, pooled) [submission]")
out.append("| Pooled (confirmation set) | Whisper large-v3 | wav2vec2-base-960h |")
out.append("|---|---|---|")
for label, q, signed in [("WER, LIN8 (%)", "wer_LIN8", False),
                         ("LIN8 − REF (inclusive linear component, pp)", "L8", True),
                         ("OPUS − LIN8 (residual beyond the best-linear surrogate, pp)", "R8", True),
                         ("LIN8 − LP (pp)", "delta_L", True)]:
    out.append(row(label, [ci(*a1(m, q), signed=signed) for m, _ in MODELS]))
out.append(row("Linear share, (LIN8 − REF)/(OPUS − REF)", [ci(*a1(m, "S8", kind="ratio"), signed=False) for m, _ in MODELS]))
out.append(row("Sequential share along REF → LP → OPUS", [ci(*a1(m, "S_primary", kind="ratio"), signed=False) for m, _ in MODELS]))
out.append(row("Outcome (frozen rule)", [A1_DEC["outcome"]] * 2))
out.append("")
out.append("TABLE A1S (inclusive best-linear attribution per subset, secondary) [submission]")
out.append("| Subset | Recogniser | LIN8 − REF | OPUS − LIN8 | LIN8 − LP |")
out.append("|---|---|---|---|---|")
for scope in ["test-clean", "test-other"]:
    for m, name in MODELS:
        out.append(row(scope, [name] + [ci(*a1(m, q, scope)) for q in ["L8", "R8", "delta_L"]]))
out.append("")


def lp_response():
    """Frozen LP control response at fixed frequencies relative to its 0.5-2 kHz gain (dB)."""
    import numpy as np
    taps = np.asarray(json.loads((ROOT / "results_paper" / "lowpass_validation" / "frozen_filter.json").read_text())["taps"])
    freqs = np.fft.rfftfreq(8192, 1 / 16000)
    db = 20 * np.log10(np.maximum(np.abs(np.fft.rfft(taps, 8192)), 1e-12))
    gain = float(db[(freqs >= 500) & (freqs <= 2000)].mean())
    return gain, {hz: float(db[int(np.argmin(abs(freqs - hz)))] - gain) for hz in [2000, 2500, 3000, 3500, 4000]}


LP_GAIN, LP_REL = lp_response()
A1_SUM = {"calibration": A1_CAL["summary"], "validation": A1_VAL["summary"], "confirmation": A1_EVAL["summary"]}
out.append("TABLE A1D (linear response of the 8 kbit/s chain: per-utterance medians; LP control for comparison) [submission]")
out.append("| Descriptor | LIN8, calibration | LIN8, validation | LIN8, confirmation | LP control |")
out.append("|---|---|---|---|---|")
out.append(row("Projection NMSE (dB)", [fmt(A1_SUM[s]["nmse_db"]["median"]) for s in A1_SUM] + ["—"]))
out.append(row("Energy explained", [fmt(A1_SUM[s]["explained_energy_fraction"]["median"], dec=3) for s in A1_SUM] + ["—"]))
out.append(row("Gain, 0.5–2 kHz (dB)", [fmt(A1_SUM[s]["gain_0p5_2k_db"]["median"]) for s in A1_SUM] + [fmt(round(LP_GAIN, 2) + 0.0)]))
for hz in [2000, 2500, 3000, 3500, 4000]:
    out.append(row(f"Response at {hz / 1000:.1f} kHz, relative (dB)",
                   [fmt(A1_SUM[s][f"rel_{hz}_db"]["median"]) for s in A1_SUM] + [fmt(round(LP_REL[hz], 2) + 0.0)]))
out.append(row("Delay (samples)", [fmt(A1_SUM[s]["linear_delay_samples"]["median"]) for s in A1_SUM] + ["0"]))
pc, pv = A1_CAL["pooled"], A1_VAL["pooled"]
out.append(row("Pooled coherence 0–3.5 kHz, OPUS / LIN8", [f"{fmt(p['REF->OPUS8']['mean_coherence_0_3500'], dec=3)} / "
                                                              f"{fmt(p['REF->LIN8']['mean_coherence_0_3500'], dec=3)}" for p in (pc, pv)] + ["—", "—"]))
out.append(row("Pooled 4–8 kHz power vs REF, OPUS / LIN8 (dB)", [f"{fmt(p['REF->OPUS8']['total_hf_power_db'], dec=1)} / "
                                                                   f"{fmt(p['REF->LIN8']['total_hf_power_db'], dec=1)}" for p in (pc, pv)] + ["—", "—"]))
out.append("")
g = A1_VAL["gates"]
out.append(f"A1 gates: calibration NMSE median {fmt(A1_CAL['summary']['nmse_db']['median'])} dB, tolerance "
           f"{fmt(A1_CAL['collapse_tolerance_db'])} dB; validation median {fmt(g['V2']['validation_median_nmse_db'])} dB "
           f"(gap {fmt(g['V2']['generalisation_gap_db'], signed=True)} dB); OPUS8 reproduced {A1_EVAL['gates']['E1']['opus8_identical']:,} "
           f"of {A1_EVAL['gates']['E1']['of']:,}; anchors {A1_DEC['anchor_reproduction']['max_abs_difference_pp']:.1e} pp")
out.append("")

# ---------------------------------------------------------------- C1: metric and weighting robustness (no new ASR)
C1_REC = sealed(FIR / "C1_RECORD.json", "record_sha256")
assert file_sha256(FIR / "c1_metric_table.csv") == C1_REC["table_sha256"]
C1_TAB = load(FIR / "c1_metric_table.csv")
C1_W = [("micro", "Corpus WER"), ("macro", "Mean utterance WER"), ("speaker", "Equal-speaker WER"), ("cer", "CER")]


def c1(model, metric, quantity, scope="pooled"):
    rows = [r for r in C1_TAB if r["model"] == model and r["metric"] == metric and r["quantity"] == quantity
            and r["scope"] == scope]
    assert len(rows) == 1, (model, metric, quantity, scope)
    return float(rows[0]["estimate"]), float(rows[0]["ci_lower"]), float(rows[0]["ci_upper"])


out.append("TABLE C1 (metric and weighting robustness of the primary contrasts, pooled; no new ASR) [submission]")
out.append("| Weighting | Recogniser | LP − REF | OPUS − LP | (OPUS − LP) − (LP − REF) | Sequential share |")
out.append("|---|---|---|---|---|---|")
for metric, wname in C1_W:
    for m, name in MODELS:
        out.append(row(wname, [name, ci(*c1(m, metric, "B")), ci(*c1(m, metric, "R")), ci(*c1(m, metric, "R_minus_B")),
                               ci(*c1(m, metric, "share_B_over_T"), signed=False)]))
out.append("")
CL = C1_REC["classifications"]
out.append("C1 classes: " + "; ".join(f"{k}: {'/'.join(v['classes'])}" for k, v in CL.items()))
for m, name in MODELS:
    est = CL[f"{m}: sequential share B/T"]["estimates"]
    out.append(f"C1 share range {m}: {fmt(min(est.values()))}–{fmt(max(est.values()))}")
out.append("C1 disagreeing secondary cells: whisper test-clean CER R−B " + ci(*c1("whisper", "cer", "R_minus_B", "test-clean"))
           + "; wav2vec2 test-other macro R−B " + ci(*c1("wav2vec2", "macro", "R_minus_B", "test-other"))
           + "; wav2vec2 deletions R−B " + ci(*c1("wav2vec2", "D", "R_minus_B")))
out.append("")


def c1_rel_residual(model, metric):
    """Residual relative to the LP level (%), from the sealed C1 cells (REF level = T / (T / REF))."""
    ref = c1(model, metric, "T")[0] / c1(model, metric, "rel_T")[0]
    return 100 * c1(model, metric, "R")[0] / (ref + c1(model, metric, "B")[0])


out.append("C1 residual relative to the LP level (%, Whisper and wav2vec2): " + "; ".join(
    f"{wname} {c1_rel_residual('whisper', m):.1f} and {c1_rel_residual('wav2vec2', m):.1f}" for m, wname in C1_W))
out.append("C1 ratio of the bandwidth components (wav2vec2 / Whisper): " + "; ".join(
    f"{wname} {c1('wav2vec2', m, 'B')[0] / c1('whisper', m, 'B')[0]:.1f}" for m, wname in C1_W))
out.append("C1 criteria: interval ratio above 2; point estimates differing by a factor above 1.5; replicates with "
           "a non-positive denominator: " + ", ".join(
               str(sum(int(float(r["replicates_denominator_le_0"] or 0)) for r in C1_TAB
                       if r["model"] == m and r["scope"] == "pooled" and r["quantity"] == "share_B_over_T")) for m, _ in MODELS))
out.append("")

# ---------------------------------------------------------------- B1: encoder application mode (sealed outputs)
B1_DEC = sealed(FIR / "B1_DECISION.json", "decision_sha256")
B1_VAL = sealed(FIR / "b1_validation" / "validation_report.json", "report_sha256")
B1_RAW = sealed(FIR / "b1_raw" / "outputs_sha256.json", "outputs_sha256")
B1_CAL = sealed(FIR / "b1_calibration" / "encode_report.json", "report_sha256")
assert file_sha256(FIR / "b1_bootstrap.csv") == B1_DEC["bootstrap_sha256"]
assert file_sha256(FIR / "b1_validation" / "validation_rows.csv") == B1_VAL["rows_sha256"]
assert B1_DEC["outputs_sha256"] == B1_RAW["outputs_sha256"] and B1_DEC["anchor_reproduction"]["pass"] and B1_VAL["pass"]
B1_BOOT = load(FIR / "b1_bootstrap.csv")
B1_OUT = {m: B1_DEC["cells"][m]["outcome"] for m, _ in MODELS}


def b1(model, quantity, scope="pooled", kind="micro"):
    return ub(B1_BOOT, model, quantity, scope, kind)


out.append("TABLE B1 (encoder application mode: total penalty under OPUS_APPLICATION_VOIP, pooled) [submission]")
out.append("| Pooled (confirmation set) | Whisper large-v3 | wav2vec2-base-960h |")
out.append("|---|---|---|")
for label, q, signed in [("WER, OPUS_AUDIO8 (= OPUS) (%)", "wer_OPUS_AUDIO8", False), ("WER, OPUS_VOIP8 (%)", "wer_OPUS_VOIP8", False),
                         ("A = OPUS_AUDIO8 − REF (pp)", "A", True), ("V = OPUS_VOIP8 − REF (pp)", "V", True),
                         ("D_app = OPUS_VOIP8 − OPUS_AUDIO8 (pp)", "D_app", True)]:
    out.append(row(label, [ci(*b1(m, q), signed=signed) for m, _ in MODELS]))
out.append(row("D_app, CER (pp)", [ci(*b1(m, "D_app", kind="micro_cer")) for m, _ in MODELS]))
out.append(row("Outcome (frozen rule)", [B1_OUT[m] for m, _ in MODELS]))
out.append("")
out.append("TABLE B1S (encoder application mode per subset, secondary) [submission]")
out.append("| Subset | Recogniser | V = OPUS_VOIP8 − REF | D_app = OPUS_VOIP8 − OPUS_AUDIO8 |")
out.append("|---|---|---|---|")
for scope in ["test-clean", "test-other"]:
    for m, name in MODELS:
        out.append(row(scope, [name, ci(*b1(m, "V", scope)), ci(*b1(m, "D_app", scope))]))
out.append("")
BD = B1_VAL["descriptive"]
out.append("TABLE B1D (encoder application mode: packets and signal descriptors against REF, 2,174 utterances; descriptive) [submission]")
out.append("| Descriptor | OPUS_AUDIO8 | OPUS_VOIP8 |")
out.append("|---|---|---|")
C_ = ["OPUS_AUDIO8", "OPUS_VOIP8"]
out.append(row("Payload bitrate, median [5th, 95th percentile] (kbit/s)",
               [f"{fmt(BD[c]['payload_kbps']['median'])} [{fmt(BD[c]['payload_kbps']['p05'])}, {fmt(BD[c]['payload_kbps']['p95'])}]" for c in C_]))
out.append(row("Coherence with REF, 0–3.5 kHz (median)", [fmt(BD[c]["coherence_0_3500_vs_ref"]["median"], dec=3) for c in C_]))
out.append(row("LSD vs REF, 0–3 kHz (dB, median)", [fmt(BD[c]["lsd_0_3k_db_vs_ref"]["median"]) for c in C_]))
out.append(row("RMS change vs REF (dB, median)", [fmt(BD[c]["rms_change_db"]["median"]) for c in C_]))
out.append(row("In-band gain, 0.5–2 kHz (dB, pooled)", [fmt(BD[c]["pooled_h1_level_db"]) for c in C_]))
out.append(row("Total 4–8 kHz power vs REF (dB, pooled)", [fmt(BD[c]["pooled_total_hf_power_db"], dec=1) for c in C_]))
out.append(row("Mirror coherence, 4.1–4.9 kHz (pooled)", [fmt(BD[c]["pooled_mirror_coherence_4100_4900"], dec=3) for c in C_]))
out.append(row("Integer lag vs REF (samples: utterances)", [lag_cell(BD[c]["lag_vs_ref_counts"]).replace("-", MINUS) for c in C_]))
out.append(row("Samples at or above full scale (utterances)",
               [f"{BD[c]['clipped_samples_total']} ({BD[c]['utterances_with_clipping']})" for c in C_]))
out.append("")
K = B1_VAL["checks"]
out.append(f"B1 checks: AUDIO8 reproduced {K['K1']['ogg_identical']:,} and {K['K1']['waveform_identical']:,} of {K['K1']['of']:,}; "
           f"VOIP8 encoded {K['K2']['encoded']:,} of {K['K2']['of']:,}; readback application "
           f"{K['K3']['OPUS_VOIP8']['queried_application']} for VOIP8; all-SILK utterances {K['K4']['OPUS_VOIP8']['utterances_all_silk']:,}; "
           f"anchors {B1_DEC['anchor_reproduction']['max_abs_difference_pp']:.1e} pp")
out.append("")
# ---------------------------------------------------------------- main-paper Table VII (Section 4.12)
B1_ROWS_ENABLED = True
out.append("TABLE 9 (post-confirmation sensitivity of the residual and of the total, pooled) [submission]")
out.append("| Pooled (confirmation set, pp) | Whisper large-v3 | wav2vec2-base-960h |")
out.append("|---|---|---|")
out.append(row("LIN8 − REF (inclusive linear component)", [ci(*a1(m, "L8")) for m, _ in MODELS]))
out.append(row("OPUS − LIN8 (residual beyond the best-linear surrogate)", [ci(*a1(m, "R8")) for m, _ in MODELS]))
out.append(row("LIN8 − LP", [ci(*a1(m, "delta_L")) for m, _ in MODELS]))
out.append(row("Linear share, (LIN8 − REF)/(OPUS − REF)", [ci(*a1(m, "S8", kind="ratio"), signed=False) for m, _ in MODELS]))
if B1_ROWS_ENABLED:
    out.append(row("OPUS_VOIP8 − REF (total, VoIP application mode)", [ci(*b1(m, "V")) for m, _ in MODELS]))
    out.append(row("OPUS_VOIP8 − OPUS (application mode)", [ci(*b1(m, "D_app")) for m, _ in MODELS]))
out.append("")

print("\n".join(out))
