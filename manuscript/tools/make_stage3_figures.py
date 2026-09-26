"""Vector manuscript figures for Stage 3 (presentation only).

Reads only the frozen Stage 3 bootstrap table (results_paper/stage3_asr/07_paired_bootstrap.csv,
through make_tables.py's loader) and redraws the four Stage 3 result figures at print width
(6.2 in) with >= 8 pt text and no in-image titles. Nothing is recomputed.
Output: manuscript/figures/fig_{wer,components,forest,models}.pdf (+ .png previews).
"""
import contextlib
import io
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
with contextlib.redirect_stdout(io.StringIO()):
    import make_tables as T  # noqa: E402

OUT = HERE.parent / "figures"
SURFACE, TEXT, TEXT2, GRID, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
MODELS = [("whisper", "Whisper large-v3", "#2a78d6", "o"), ("wav2vec2", "wav2vec2-base-960h", "#eb6834", "s")]
M = "−"
W = 6.2

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.labelsize": 8.5, "axes.titlesize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.edgecolor": TEXT2, "axes.labelcolor": TEXT, "xtick.color": TEXT2, "ytick.color": TEXT2,
    "axes.linewidth": 0.6, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.unicode_minus": True,
    "savefig.facecolor": SURFACE, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
})


def style(ax):
    ax.grid(True, axis="y", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def signed(v):
    return (M if v < 0 else "+") + f"{abs(v):.2f}"


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 2: WER by condition
CONDS = ["REF", "LP", "OPUS", "SILK", "NEG_LP", "NEG_CODEC"]
fig, axes = plt.subplots(1, 2, figsize=(W, 2.4))
for ax, (m, name, colour, marker) in zip(axes, MODELS):
    for i, c in enumerate(CONDS):
        e, lo, hi = T.b("confirmation", m, f"wer_{c}")
        col = NEUTRAL if c.startswith("NEG") else colour
        ax.errorbar(i, e, yerr=[[e - lo], [hi - e]], fmt=marker, color=col, ms=5, capsize=3, lw=1.2)
    ax.set_xticks(range(len(CONDS)), ["REF", "LP", "OPUS", "SILK", "NEG_LP", "NEG_\nCODEC"])
    ax.set_title(name, loc="left", color=TEXT)
    ax.set_ylim(bottom=0)
    style(ax)
axes[0].set_ylabel("Corpus WER (%)")
fig.tight_layout()
save(fig, "fig_wer")

# ---------------------------------------------------------------- Fig. 3: components
COMP = [("delta_bw", "Bandwidth\nLP " + M + " REF"), ("delta_opus_residual", "Opus residual\nOPUS " + M + " LP"),
        ("delta_silk_residual", "SILK residual\nSILK " + M + " LP")]
fig, axes = plt.subplots(1, 2, figsize=(W, 2.5), sharey=True)
for ax, (m, name, colour, _) in zip(axes, MODELS):
    for i, (q, _lab) in enumerate(COMP):
        e, lo, hi = T.b("confirmation", m, q)
        ax.bar(i, e, width=0.6, color=colour, zorder=2)
        ax.errorbar(i, e, yerr=[[e - lo], [hi - e]], fmt="none", ecolor=TEXT, capsize=3, lw=1, zorder=3)
        ax.annotate(signed(e), (i, max(hi, 0)), xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8, color=TEXT)
    ax.axhline(0, color=TEXT2, lw=0.6)
    ax.set_xticks(range(len(COMP)), [lab for _, lab in COMP])
    ax.set_title(name, loc="left", color=TEXT)
    style(ax)
axes[0].set_ylabel("Δ corpus WER (pp), 95 % CI")
axes[0].set_ylim(-0.4, 2.9)
fig.tight_layout()
save(fig, "fig_components")

# ---------------------------------------------------------------- Fig. 4: forest, pilot vs confirmation
FOREST = [("delta_bw", "Bandwidth: LP " + M + " REF"), ("delta_opus_residual", "Opus residual: OPUS " + M + " LP"),
          ("delta_silk_residual", "SILK residual: SILK " + M + " LP"), ("opus_minus_silk", "OPUS " + M + " SILK"),
          ("delta_opus_total", "Opus total: OPUS " + M + " REF"), ("delta_silk_total", "SILK total: SILK " + M + " REF"),
          ("neg_lp_minus_ref", "Control: NEG_LP " + M + " REF"),
          ("neg_codec_minus_ref", "Control: NEG_CODEC " + M + " REF")]
fig, axes = plt.subplots(1, 2, figsize=(W, 3.3), sharey=True)
for ax, (set_, title) in zip(axes, [("pilot", "Pilot (138 utterances)"), ("confirmation", "Confirmation (2,174 utterances)")]):
    for j, (m, name, colour, marker) in enumerate(MODELS):
        for i, (q, _lab) in enumerate(FOREST):
            e, lo, hi = T.b(set_, m, q)
            y = i + (-0.17 if j == 0 else 0.17)
            ax.errorbar(e, y, xerr=[[e - lo], [hi - e]], fmt=marker, color=colour, ms=4, capsize=2, lw=1.1,
                        label=name if i == 0 else None)
    ax.axvline(0, color=TEXT2, lw=0.7)
    ax.set_title(title, loc="left", color=TEXT)
    ax.set_xlabel("Δ corpus WER (pp), 95 % CI")
    ax.grid(True, axis="x", color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
axes[0].set_yticks(range(len(FOREST)), [lab for _, lab in FOREST])
axes[0].invert_yaxis()
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.58, -0.01))
fig.tight_layout(rect=(0, 0.06, 1, 1))
save(fig, "fig_forest")

# ---------------------------------------------------------------- Fig. 5: cross-recogniser comparison
PAIRS = [("delta_bw", "Bandwidth: LP " + M + " REF", "s"), ("delta_opus_residual", "Opus residual: OPUS " + M + " LP", "o"),
         ("delta_silk_residual", "SILK residual: SILK " + M + " LP", "^"), ("opus_minus_silk", "OPUS " + M + " SILK", "D"),
         ("neg_lp_minus_ref", "Control: NEG_LP " + M + " REF", "v"),
         ("neg_codec_minus_ref", "Control: NEG_CODEC " + M + " REF", "P")]
fig, ax = plt.subplots(figsize=(W, 3.2))
for q, lab, mk in PAIRS:
    x, xlo, xhi = T.b("confirmation", "whisper", q)
    y, ylo, yhi = T.b("confirmation", "wav2vec2", q)
    col = NEUTRAL if lab.startswith("Control") else TEXT
    ax.errorbar(x, y, xerr=[[x - xlo], [xhi - x]], yerr=[[y - ylo], [yhi - y]], fmt=mk, color=col,
                ms=5.5, capsize=2, lw=0.9, label=lab, mfc=col)
lim = (-0.5, 3.0)
ax.plot(lim, lim, color=GRID, lw=1, zorder=0)
ax.axhline(0, color=TEXT2, lw=0.5)
ax.axvline(0, color=TEXT2, lw=0.5)
ax.set_xlim(*lim)
ax.set_ylim(*lim)
ax.set_aspect("equal")
ax.set_xlabel("Whisper large-v3: Δ corpus WER (pp)")
ax.set_ylabel("wav2vec2-base-960h: Δ corpus WER (pp)")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.legend(loc="center left", bbox_to_anchor=(1.03, 0.5), frameon=False)
fig.tight_layout()
save(fig, "fig_models")
print("wrote", sorted(p.name for p in OUT.glob("fig_*.pdf")))
