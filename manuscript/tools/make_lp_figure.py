"""Low-pass control validation figure (presentation only).

Reads the frozen Stage 2B confirmation curves (40 unseen train-clean-100 speakers) and plots
them; nothing is recomputed or re-measured. Output: manuscript/figures/fig_lp_validation.{png,pdf}.
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "results_paper" / "lowpass_confirmation" / "transfer_curves.csv"
OUT = ROOT / "manuscript" / "figures"

SURFACE, TEXT, TEXT2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
# (cell, label, colour, linestyle, width, z). Categorical slots 1-3 of the reference palette;
# the linear reference is a neutral dashed line so identity never depends on colour alone.
SERIES = [
    ("silk_nb_linear_ref", "SILK-NB linear reference (40 kbit/s)", TEXT2, (0, (4, 2)), 1.6, 4),
    ("lp", "LP control", "#2a78d6", "-", 2.0, 5),
    ("opus_8k_nb", "Opus 8 kbit/s (SILK-NB)", "#eb6834", "-", 1.6, 3),
    ("opus_12k_nb", "Opus 12 kbit/s, forced NB", "#1baf7a", (0, (1, 1.2)), 1.6, 2),
]

rows = list(csv.DictReader(open(SRC, newline="")))
assert {r["subset"] for r in rows} == {"train-clean-100"}


def curve(cell, col):
    pts = sorted((float(r["frequency_hz"]) / 1000, float(r[col])) for r in rows if r["cell"] == cell)
    return [p[0] for p in pts], [p[1] for p in pts]


plt.rcParams.update({"font.size": 8, "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.labelsize": 8.5, "axes.edgecolor": TEXT2, "axes.labelcolor": TEXT,
                     "xtick.color": TEXT2, "ytick.color": TEXT2, "axes.linewidth": 0.6,
                     "font.family": "DejaVu Sans",
                     "pdf.fonttype": 42, "ps.fonttype": 42})  # TrueType, not Type 3
fig, axes = plt.subplots(2, 2, figsize=(6.2, 4.7), facecolor=SURFACE)
panels = [
    (axes[0, 0], "h1_rel_db", (0, 8), (-80, 5), "|H1| re 0.5–2 kHz (dB)", "(a) Linear transfer, 0–8 kHz"),
    (axes[0, 1], "h1_rel_db", (3.0, 4.5), (-60, 2), "|H1| re 0.5–2 kHz (dB)", "(b) Band edge, 3.0–4.5 kHz"),
    (axes[1, 0], "coherence", (0, 8), (0, 1.02), "Coherence with input at f", "(c) Coherence"),
    (axes[1, 1], "mirror_coherence", (0, 8), (0, 1.02), "Coherence with input at 8 kHz − f",
     "(d) Mirror coherence (image)"),
]
for ax, col, xl, yl, ylab, title in panels:
    ax.set_facecolor(SURFACE)
    for cell, label, colour, ls, lw, z in SERIES:
        x, y = curve(cell, col)
        ax.plot(x, [max(v, yl[0] - 5) for v in y], color=colour, ls=ls, lw=lw, zorder=z, label=label)
    ax.set_xlim(*xl)
    ax.set_ylim(*yl)
    ax.set_xlabel("Frequency (kHz)")
    ax.set_ylabel(ylab)
    ax.set_title(title, loc="left", fontsize=8.5, color=TEXT)
    ax.grid(True, color=GRID, lw=0.5)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
handles, labels = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=8,
           bbox_to_anchor=(0.5, -0.005), labelcolor=TEXT)
fig.tight_layout(rect=(0, 0.08, 1, 1))
OUT.mkdir(parents=True, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(OUT / f"fig_lp_validation.{ext}", dpi=300, facecolor=SURFACE)
print("wrote", OUT / "fig_lp_validation.png")
