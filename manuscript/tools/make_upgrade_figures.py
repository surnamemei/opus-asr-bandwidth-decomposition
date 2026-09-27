"""Vector manuscript figure for the TASLP-upgrade bitrate sweep (addition B; presentation only).

Reads only the sealed sweep bootstrap table and the frozen Stage 3 anchors, through
make_tables.py's loaders (which check the seals), and draws the residual beyond LP at each
rate with its 95 % interval, the fitted log2-bitrate slope, and the Stage 3 residuals at
8 and 40 kbit/s for reference. Nothing is recomputed except the line drawn for the slope,
which passes through the mean of the five point estimates, as the least-squares fit does.
Output: manuscript/figures/fig_sweep.pdf (+ .png preview).
"""
import contextlib
import io
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
with contextlib.redirect_stdout(io.StringIO()):
    import make_tables as T  # noqa: E402


class F:
    """House style of make_stage3_figures.py (copied: importing it would redraw the Stage 3 figures)."""
    OUT = HERE.parent / "figures"
    SURFACE, TEXT, TEXT2, GRID, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
    MODELS = [("whisper", "Whisper large-v3", "#2a78d6", "o"), ("wav2vec2", "wav2vec2-base-960h", "#eb6834", "s")]
    W = 6.2

    @staticmethod
    def style(ax):
        ax.grid(True, axis="y", color=F.GRID, lw=0.5)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    @staticmethod
    def signed(v):
        return ("−" if v < 0 else "+") + f"{abs(v):.2f}"

    @staticmethod
    def save(fig, name):
        F.OUT.mkdir(parents=True, exist_ok=True)
        fig.savefig(F.OUT / f"{name}.pdf")
        fig.savefig(F.OUT / f"{name}.png", dpi=200)
        plt.close(fig)


plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.labelsize": 8.5, "axes.titlesize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.edgecolor": F.TEXT2, "axes.labelcolor": F.TEXT, "xtick.color": F.TEXT2, "ytick.color": F.TEXT2,
    "axes.linewidth": 0.6, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.unicode_minus": True,
    "savefig.facecolor": F.SURFACE, "figure.facecolor": F.SURFACE, "axes.facecolor": F.SURFACE,
})

x = [math.log2(r) for r in T.RATES]
fig, axes = plt.subplots(1, 2, figsize=(F.W, 2.5))
for ax, (m, name, colour, marker) in zip(axes, F.MODELS):
    est = [T.sw(m, f"R_{r}") for r in T.RATES]
    for xi, (e, lo, hi) in zip(x, est):
        ax.plot([xi, xi], [lo, hi], color=colour, lw=1.2, solid_capstyle="round", zorder=2)
    ax.plot(x, [e for e, _, _ in est], ls="none", marker=marker, ms=5, color=colour, mec=F.SURFACE,
            mew=1.0, zorder=3)
    s, s_lo, s_hi = T.sw(m, "S_log2", kind="trend")
    xm, ym = sum(x) / len(x), sum(e for e, _, _ in est) / len(est)
    ax.plot([x[0], x[-1]], [ym + s * (x[0] - xm), ym + s * (x[-1] - xm)], color=colour, lw=0.8, ls=(0, (4, 2)),
            zorder=1)
    anchors = T.SPEC["B"]["anchors"][m]
    for xi, key in [(x[0], "T_star"), (x[-1], "U_star")]:
        a = anchors[key]
        ax.plot([xi + 0.09] * 2, a["ci"], color=F.NEUTRAL, lw=1.0, zorder=2)
        ax.plot(xi + 0.09, a["estimate"], ls="none", marker=marker, ms=5, mfc=F.SURFACE, mec=F.NEUTRAL,
                mew=1.0, zorder=3)
    ax.axhline(0, color=F.TEXT2, lw=0.6, zorder=0)
    ax.set_xticks(x, [str(r) for r in T.RATES])
    ax.set_xlabel("SILK narrowband bitrate (kbit/s, log scale)")
    ax.set_ylabel("WER difference from LP (pp)")
    ax.set_title(name, loc="left", color=F.TEXT, fontsize=8.5)
    ax.text(0.97, 0.97, f"slope {F.signed(s)} [{F.signed(s_lo)}, {F.signed(s_hi)}]\npp per doubling",
            transform=ax.transAxes, ha="right", va="top", color=F.TEXT2, fontsize=8)
    F.style(ax)
from matplotlib.lines import Line2D  # noqa: E402
handles = [Line2D([], [], ls="none", marker="o", ms=5, color=F.TEXT2, label="Sweep, fresh utterances (95 % CI)"),
           Line2D([], [], color=F.TEXT2, lw=0.8, ls=(0, (4, 2)), label="Fitted log2-bitrate slope"),
           Line2D([], [], ls="none", marker="o", ms=5, mfc=F.SURFACE, mec=F.NEUTRAL, label="Confirmatory run")]
fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False)
fig.subplots_adjust(left=0.09, right=0.985, top=0.9, bottom=0.3, wspace=0.28)
F.save(fig, "fig_sweep")
print("wrote figures/fig_sweep.pdf")
