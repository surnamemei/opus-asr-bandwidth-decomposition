"""
Stage 3 reporting: frozen-spec rendering, pilot report, final tables,
figures and the Stage 3 summary.

Figures follow the dataviz reference palette (light surface): models use
categorical slots 1-2 (validated default order), paired utterance changes
use the documented blue <-> red diverging pair with a neutral midpoint, and
every other category is encoded by position, not by additional hues.
"""

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import stage3_asr as asr
import stage3_audio as audio
import stage3_stats as stats


MODELS = asr.MODELS
CONDITIONS = audio.CONDITIONS

SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"
MODEL_COLOURS = {"whisper": "#2a78d6", "wav2vec2": "#eb6834"}
DIVERGING = {"lower": "#2a78d6", "same": "#f0efec", "higher": "#e34948"}
FIG_DPI = 200

QUANTITY_LABELS = {
    "delta_bw": "Bandwidth: LP − REF",
    "delta_opus_residual": "Opus residual: OPUS − LP",
    "delta_silk_residual": "SILK residual: SILK − LP",
    "opus_minus_silk": "OPUS − SILK",
    "delta_opus_total": "Opus total: OPUS − REF",
    "delta_silk_total": "SILK total: SILK − REF",
    "neg_lp_minus_ref": "Control: NEG_LP − REF",
    "neg_codec_minus_ref": "Control: NEG_CODEC − REF",
}
PRIMARY_QUANTITIES = ["delta_bw", "delta_opus_residual", "delta_silk_residual", "opus_minus_silk"]
PAIRED = [("delta_bw", "LP", "REF"), ("delta_opus_residual", "OPUS", "LP"),
          ("delta_silk_residual", "SILK", "LP")]
EXPLORATORY_FEATURES = [
    "ref_hf_energy_fraction_4_8k", "ref_fricative_frame_fraction", "ref_voiced_frame_fraction",
    "ref_spectral_flatness", "ref_spectral_flux_db", "vs_lp_lsd_0_3k_db", "vs_lp_lsd_0_4k_db",
    "vs_lp_coherence_0_3500", "vs_lp_envelope_decorrelation",
]


# ==================================================
# Formatting helpers
# ==================================================

def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": BASELINE, "axes.linewidth": 0.8, "axes.labelcolor": INK_2,
        "axes.titlecolor": INK, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "axes.axisbelow": True,
        "xtick.color": BASELINE, "ytick.color": BASELINE,
        "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2, "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5, "legend.frameon": False, "legend.fontsize": 8.5,
        "font.family": "DejaVu Sans", "font.size": 9, "lines.linewidth": 2.0,
        "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "figure.titlesize": 11, "figure.titleweight": "normal",
    })


def save(fig, path: Path) -> None:
    fig.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
    plt.close(fig)


def ci_text(row: dict, unit: str = "pp") -> str:
    return f"{row['estimate']:+.2f} {unit} [{row['ci_lower']:+.2f}, {row['ci_upper']:+.2f}]"


def md_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = ["| " + " | ".join(map(str, columns)) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for _, row in frame.iterrows():
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append("" if np.isnan(v) else f"{v:.3g}" if abs(v) < 1000 else f"{v:,.0f}")
            else:
                cells.append(str(v).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def point(ax, x, row, colour, horizontal=False, size=7):
    lo, hi, est = row["ci_lower"], row["ci_upper"], row["estimate"]
    if horizontal:
        ax.errorbar(est, x, xerr=[[est - lo], [hi - est]], fmt="o", color=colour, ecolor=colour,
                    elinewidth=1.6, capsize=0, markersize=size, markeredgecolor=SURFACE,
                    markeredgewidth=1.5, zorder=3)
    else:
        ax.errorbar(x, est, yerr=[[est - lo], [hi - est]], fmt="o", color=colour, ecolor=colour,
                    elinewidth=1.6, capsize=0, markersize=size, markeredgecolor=SURFACE,
                    markeredgewidth=1.5, zorder=3)


# ==================================================
# Figures
# ==================================================

def fig_wer_by_condition(boot: pd.DataFrame, set_name: str, path: Path) -> None:
    fig, axes = plt.subplots(1, len(MODELS), figsize=(9.2, 3.6))
    positions = [0, 1, 2, 3, 4.7, 5.7]
    for ax, model in zip(axes, MODELS):
        for x, condition in zip(positions, CONDITIONS):
            row = stats.lookup(boot, set_name, model, f"wer_{condition}")
            colour = MODEL_COLOURS[model] if condition in audio.PRIMARY_CONDITIONS else MUTED
            point(ax, x, row, colour)
        ax.axvline(4.05, color=GRID, linewidth=0.8)
        ax.set_xticks(positions, ["REF", "LP", "OPUS", "SILK", "NEG\nLP", "NEG\nCODEC"])
        ax.set_ylim(bottom=0)
        ax.set_title(asr.MODEL_LABELS[model], loc="left")
        ax.grid(axis="x", visible=False)
        ax.text(5.2, ax.get_ylim()[1] * 0.98, "negative controls", ha="center", va="top",
                color=MUTED, fontsize=8)
    axes[0].set_ylabel("Corpus WER (%)")
    fig.suptitle(f"Corpus WER by condition, {set_name} set (95% speaker-bootstrap CI)",
                 x=0.01, ha="left")
    fig.tight_layout()
    save(fig, path)


def fig_bandwidth_vs_residual(boot: pd.DataFrame, set_name: str, path: Path) -> None:
    quantities = ["delta_bw", "delta_opus_residual", "delta_silk_residual"]
    labels = ["Bandwidth\nLP − REF", "Opus residual\nOPUS − LP", "SILK residual\nSILK − LP"]
    fig, axes = plt.subplots(1, len(MODELS), figsize=(9.2, 3.6), sharey=True)
    for ax, model in zip(axes, MODELS):
        rows = [stats.lookup(boot, set_name, model, q) for q in quantities]
        x = np.arange(len(quantities))
        estimates = [r["estimate"] for r in rows]
        ax.bar(x, estimates, width=0.45, color=MODEL_COLOURS[model], zorder=2)
        ax.errorbar(x, estimates, yerr=[[r["estimate"] - r["ci_lower"] for r in rows],
                                        [r["ci_upper"] - r["estimate"] for r in rows]],
                    fmt="none", ecolor=INK_2, elinewidth=1.2, capsize=0, zorder=3)
        for xi, r in zip(x, rows):
            top = max(r["ci_upper"], 0)
            ax.text(xi, top, f"{r['estimate']:+.2f}", ha="center", va="bottom", color=INK,
                    fontsize=8.5)
        ax.axhline(0, color=BASELINE, linewidth=0.8)
        ax.set_xticks(x, labels)
        ax.grid(axis="x", visible=False)
        ax.set_title(asr.MODEL_LABELS[model], loc="left")
    axes[0].set_ylabel("Δ corpus WER (percentage points)")
    fig.suptitle(f"Bandwidth component vs codec-specific residual, {set_name} set",
                 x=0.01, ha="left")
    fig.tight_layout()
    save(fig, path)


def utterance_differences(metrics: pd.DataFrame, set_name: str, model: str, a: str, b: str):
    part = metrics[(metrics["set"] == set_name) & (metrics["model"] == model)]
    wer = part.pivot(index="utterance", columns="condition", values="wer")
    return (wer[a] - wer[b]).to_numpy() * 100.0


def fig_paired_differences(metrics: pd.DataFrame, set_name: str, path: Path) -> None:
    rows = []
    for model in MODELS:
        for name, a, b in PAIRED:
            d = utterance_differences(metrics, set_name, model, a, b)
            same = np.isclose(d, 0.0, atol=1e-9)
            rows.append({"label": f"{asr.MODEL_LABELS[model]} · {a} vs {b}",
                         "lower": 100 * np.mean((d < 0) & ~same),
                         "same": 100 * np.mean(same),
                         "higher": 100 * np.mean((d > 0) & ~same),
                         "mean": d.mean()})
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    y = np.arange(len(rows))[::-1]
    for yi, r in zip(y, rows):
        half = r["same"] / 2
        ax.barh(yi, r["lower"], left=-half - r["lower"], height=0.5, color=DIVERGING["lower"])
        ax.barh(yi, r["same"], left=-half, height=0.5, color=DIVERGING["same"])
        ax.barh(yi, r["higher"], left=half, height=0.5, color=DIVERGING["higher"])
        ax.text(-half - r["lower"] - 1, yi, f"{r['lower']:.0f}%", ha="right", va="center",
                color=INK_2, fontsize=8)
        ax.text(half + r["higher"] + 1, yi, f"{r['higher']:.0f}%", ha="left", va="center",
                color=INK_2, fontsize=8)
    ax.axvline(0, color=BASELINE, linewidth=0.8)
    ax.set_yticks(y, [r["label"] for r in rows])
    limit = max(r["same"] / 2 + max(r["lower"], r["higher"]) for r in rows) + 12
    ax.set_xlim(-limit, limit)
    ticks = ax.get_xticks()
    ax.set_xticks(ticks, [f"{abs(t):.0f}" for t in ticks])
    ax.set_xlabel("Share of utterances (%): left = lower WER in the first condition, "
                  "centre = unchanged, right = higher")
    ax.grid(axis="y", visible=False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=DIVERGING[k]) for k in ["lower", "same", "higher"]]
    ax.legend(handles, ["lower WER", "no change", "higher WER"], loc="upper left",
              bbox_to_anchor=(1.0, 1.0))
    fig.suptitle(f"Paired per-utterance WER changes, {set_name} set", x=0.01, ha="left")
    fig.tight_layout()
    save(fig, path)


def fig_bootstrap_ci(boot: pd.DataFrame, sets: list[str], path: Path) -> None:
    quantities = list(QUANTITY_LABELS)
    fig, axes = plt.subplots(1, len(sets), figsize=(5.0 * len(sets) + 2.2, 4.6), sharey=True,
                             squeeze=False)
    y = np.arange(len(quantities))[::-1]
    for ax, set_name in zip(axes[0], sets):
        for offset, model in zip([0.14, -0.14], MODELS):
            for yi, q in zip(y, quantities):
                point(ax, yi + offset, stats.lookup(boot, set_name, model, q),
                      MODEL_COLOURS[model], horizontal=True, size=6)
        ax.axvline(0, color=BASELINE, linewidth=0.9)
        ax.set_title(f"{set_name} set", loc="left")
        ax.set_xlabel("Δ corpus WER (percentage points), 95% CI")
        ax.grid(axis="y", visible=False)
    axes[0][0].set_yticks(y, [QUANTITY_LABELS[q] for q in quantities])
    handles = [plt.Line2D([], [], marker="o", linestyle="", color=MODEL_COLOURS[m], markersize=7)
               for m in MODELS]
    axes[0][-1].legend(handles, [asr.MODEL_LABELS[m] for m in MODELS], loc="upper left",
                       bbox_to_anchor=(1.0, 1.0))
    fig.suptitle("Paired decomposition with speaker-bootstrap intervals", x=0.01, ha="left")
    fig.tight_layout()
    save(fig, path)


def fig_model_comparison(boot: pd.DataFrame, set_name: str, path: Path) -> None:
    # Composite encoding (marker shape + legend) so identity never depends on label placement
    encodings = {
        "delta_bw": ("s", INK, "Bandwidth: LP − REF"),
        "delta_opus_residual": ("o", INK, "Opus residual: OPUS − LP"),
        "delta_silk_residual": ("^", INK, "SILK residual: SILK − LP"),
        "opus_minus_silk": ("D", INK, "OPUS − SILK"),
        "neg_lp_minus_ref": ("v", MUTED, "Control: NEG_LP − REF"),
        "neg_codec_minus_ref": ("P", MUTED, "Control: NEG_CODEC − REF"),
    }
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    values, handles = [], []
    for q, (marker, colour, label) in encodings.items():
        a = stats.lookup(boot, set_name, "whisper", q)
        b = stats.lookup(boot, set_name, "wav2vec2", q)
        ax.errorbar(a["estimate"], b["estimate"],
                    xerr=[[a["estimate"] - a["ci_lower"]], [a["ci_upper"] - a["estimate"]]],
                    yerr=[[b["estimate"] - b["ci_lower"]], [b["ci_upper"] - b["estimate"]]],
                    fmt=marker, color=colour, ecolor=colour, elinewidth=1.0, capsize=0,
                    markersize=7, markeredgecolor=SURFACE, markeredgewidth=1.2, alpha=0.95,
                    zorder=3)
        handles.append(plt.Line2D([], [], marker=marker, linestyle="", color=colour,
                                  markersize=7, label=label))
        values += [a["ci_lower"], a["ci_upper"], b["ci_lower"], b["ci_upper"]]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    low, high = min(values + [0]) - 0.3, max(values + [0]) + 0.3
    ax.plot([low, high], [low, high], color=BASELINE, linewidth=0.9, zorder=1)
    ax.axhline(0, color=BASELINE, linewidth=0.8)
    ax.axvline(0, color=BASELINE, linewidth=0.8)
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_xlabel(f"{asr.MODEL_LABELS['whisper']}: Δ WER (pp)")
    ax.set_ylabel(f"{asr.MODEL_LABELS['wav2vec2']}: Δ WER (pp)")
    ax.set_title(f"Cross-ASR consistency, {set_name} set (diagonal = equal effect)", loc="left")
    fig.tight_layout()
    save(fig, path)


def fig_error_types(boot: pd.DataFrame, set_name: str, path: Path) -> None:
    contrasts = ["delta_bw", "delta_opus_residual", "delta_silk_residual"]
    fig, axes = plt.subplots(len(contrasts), len(MODELS), figsize=(8.4, 7.2), sharey=True)
    for i, contrast in enumerate(contrasts):
        for j, model in enumerate(MODELS):
            ax = axes[i][j]
            rows = [stats.lookup(boot, set_name, model, f"{contrast}_{t}", kind="micro_error_type")
                    for t in ["S", "D", "I"]]
            x = np.arange(3)
            est = [r["estimate"] for r in rows]
            ax.bar(x, est, width=0.45, color=MODEL_COLOURS[model], zorder=2)
            ax.errorbar(x, est, yerr=[[r["estimate"] - r["ci_lower"] for r in rows],
                                      [r["ci_upper"] - r["estimate"] for r in rows]],
                        fmt="none", ecolor=INK_2, elinewidth=1.2, capsize=0, zorder=3)
            ax.axhline(0, color=BASELINE, linewidth=0.8)
            ax.set_xticks(x, ["substitutions", "deletions", "insertions"])
            ax.grid(axis="x", visible=False)
            ax.set_title(f"{asr.MODEL_LABELS[model]} · {QUANTITY_LABELS[contrast]}", loc="left",
                         fontsize=9)
        axes[i][0].set_ylabel("Δ errors per 100 ref. words")
    fig.suptitle(f"Error-type composition of each component, {set_name} set", x=0.01, ha="left")
    fig.tight_layout()
    save(fig, path)


def residual_frame(metrics: pd.DataFrame, signal: pd.DataFrame, set_name: str,
                   codec: str) -> pd.DataFrame:
    part = metrics[metrics["set"] == set_name]
    wer = part.pivot_table(index=["utterance", "model"], columns="condition", values="wer")
    residual = ((wer[codec] - wer["LP"]) * 100).rename("residual_pp").reset_index()
    features = signal[(signal["set"] == set_name) & (signal["condition"] == codec)]
    reference = signal[(signal["set"] == set_name) & (signal["condition"] == "REF")]
    merged = residual.merge(features[["utterance", "speaker_id", "subset"] + [
        f for f in EXPLORATORY_FEATURES if f.startswith("vs_lp")]], on="utterance")
    return merged.merge(reference[["utterance"] + [f for f in EXPLORATORY_FEATURES
                                                  if f.startswith("ref_")]], on="utterance")


def fig_residual_vs_distortion(metrics, signal, set_name: str, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8), sharey=True)
    for ax, codec in zip(axes, ["OPUS", "SILK"]):
        frame = residual_frame(metrics, signal, set_name, codec)
        edges = np.quantile(frame["vs_lp_lsd_0_3k_db"], np.linspace(0, 1, 11))
        frame["bin"] = np.clip(np.searchsorted(edges, frame["vs_lp_lsd_0_3k_db"], side="right") - 1, 0, 9)
        for model in MODELS:
            part = frame[frame["model"] == model]
            grouped = part.groupby("bin").agg(x=("vs_lp_lsd_0_3k_db", "median"),
                                              y=("residual_pp", "mean"),
                                              sd=("residual_pp", "std"), n=("residual_pp", "size"))
            half = 1.96 * grouped["sd"] / np.sqrt(grouped["n"])
            ax.fill_between(grouped["x"], grouped["y"] - half, grouped["y"] + half,
                            color=MODEL_COLOURS[model], alpha=0.10, linewidth=0)
            ax.plot(grouped["x"], grouped["y"], color=MODEL_COLOURS[model], marker="o",
                    markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.2,
                    label=asr.MODEL_LABELS[model])
        ax.axhline(0, color=BASELINE, linewidth=0.8)
        ax.set_title(f"{codec} − LP", loc="left")
        ax.set_xlabel(f"LSD {codec} vs LP, 0–3 kHz (dB)")
    axes[0].set_ylabel("Mean per-utterance Δ WER (pp) ± 1.96 SE")
    axes[1].legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.suptitle(f"Exploratory: codec residual vs in-band codec distortion (decile bins), "
                 f"{set_name} set", x=0.01, ha="left")
    fig.tight_layout()
    save(fig, path)


# ==================================================
# Spec and normalisation documents
# ==================================================

def render_spec(spec: dict) -> str:
    c, d, a = spec["conditions"], spec["data"], spec["analysis"]
    w, v = spec["asr_models"]["whisper"], spec["asr_models"]["wav2vec2"]
    lines = [
        "# 00 — Frozen Stage 3 specification", "",
        f"Sealed `stage3_spec.json` SHA-256 `{spec['spec_sha256']}`, created {spec['created_utc']}. "
        "Written before any pilot or confirmation utterance was decoded.", "",
        f"**Question.** {spec['question']}", "",
        "## Provenance", "",
        *[f"- {k}: `{val}`" for k, val in spec["provenance"].items() if k != "working_tree_status"],
        "", "## Conditions (paired: every utterance in every condition)", "",
        *[f"- **{k}**: {val}" for k, val in c["definitions"].items()],
        "", f"- Note: {c['naming_note']}",
        f"- Level policy: {c['level_policy']}",
        f"- Sample-rate policy: {c['sample_rate_policy']}",
        f"- Alignment policy: {c['alignment_policy']}",
        f"- Filter hashes: {json.dumps(c['filter_sha256'])}",
        f"- Encoder settings: `{json.dumps(c['encoder_settings'])}`",
        f"- Expected packet configuration: {json.dumps(c['expected_packet_configuration'])}",
        "", "## Data (speaker-disjoint sets, selected before any ASR decoding)", "",
        md_table(pd.DataFrame([{"set": s, **{k: (json.dumps(val) if isinstance(val, dict) else val)
                                              for k, val in info.items()}}
                               for s, info in d["selections"].items()])),
        "", *[f"- {k}: {json.dumps(val) if isinstance(val, dict) else val}" for k, val in d["rules"].items()],
        f"- Post-decoding exclusions: {d['post_decoding_exclusions']}",
        "", "## ASR systems (public, fixed, no adaptation)", "",
        f"- **Model A** Whisper: `{w['repository']}` revision `{w['revision']}`, {w['dtype']}, "
        f"batch {w['batch_size']}, generate `{json.dumps(w['generate_kwargs'])}`; temperature "
        f"fallback: {w['temperature_fallback']}; prompt: {w['prompt']}; VAD: {w['vad']}; "
        f"attention {w['attention_implementation']}; weights SHA-256 `{w['weights_sha256']}`; "
        f"max duration {w['max_duration_s']} s.",
        f"- **Model B** wav2vec2: `{v['bundle']}`, checkpoint SHA-256 `{v['checkpoint_sha256']}`, "
        f"{v['decoder']}; language model: {v['language_model']}; {v['input_normalisation']}.",
        "", "## Transcript normalisation", "",
        f"- {json.dumps(spec['normalisation'])} (see transcript_normalization_spec.md)",
        "", "## Metrics", "", *[f"- {k}: {val}" for k, val in spec["metrics"].items()],
        "", "## Analysis (frozen)", "",
        f"- Bootstrap: {json.dumps(a['bootstrap'])}",
        f"- Contrasts: {json.dumps(a['contrasts'])}",
        f"- Pilot rule: {json.dumps(a['pilot_rule'])}",
        *[f"- Confirmation {k}: {val}" for k, val in a["confirmation_rule"].items()],
        f"- Conditional analyses: {a['conditional_analyses']}",
        f"- Not run: {a['not_run']}",
        "", "## Compute", "", f"- {json.dumps(spec['compute'])}",
        "", "## Environment", "",
        f"- Python {spec['environment']['python'].split()[0]}; "
        + ", ".join(f"{k} {val}" for k, val in spec['environment']['packages'].items()),
        f"- {spec['environment']['ffmpeg']['version']}; libopus "
        f"{spec['environment']['libopus_linked_by_ffmpeg']['version']}; CUDA "
        f"{spec['environment']['cuda']['torch_cuda_version']} on {spec['environment']['cuda'].get('gpu')}",
        f"- requirements-lock.txt SHA-256 `{spec['requirements_lock_sha256']}`",
        f"- Stage 1 regression check after installing transformers: all identical = "
        f"{spec['env_check']['all_identical']}",
        f"- Calibration sanity: determinism {json.dumps(spec['calibration']['determinism'])}, "
        f"{spec['calibration']['seconds_per_utterance']:.2f} s/utterance",
        "", "## Code SHA-256 at freeze", "",
        *[f"- `{k}` `{val}`" for k, val in spec["code_sha256"].items()], "",
    ]
    return "\n".join(lines)


def render_normalisation(spec: dict, normaliser) -> str:
    examples = [
        "HE'S TWENTY FIVE YEARS OLD AND WON'T GO TO MISTER SMITH'S",
        " He's 25 years old, and won't go to Mr. Smith's!",
        "COLOUR OF THE HONOUR", "Hmm, uh, I think so.",
        "THE ANTARCTIC OCEAN IS NINETEEN FORTY SEVEN FEET DEEP",
    ]
    rows = pd.DataFrame([{"input": e, "normalised": normaliser(e)} for e in examples])
    return "\n".join([
        "# Transcript normalisation specification", "",
        f"Frozen with the Stage 3 spec (SHA-256 `{spec['spec_sha256']}`).", "",
        "One policy, applied identically to LibriSpeech references and to every hypothesis of "
        "both ASR systems, before scoring: the Whisper `EnglishTextNormalizer` "
        f"({json.dumps(spec['normalisation'])}).", "",
        "It lower-cases; removes punctuation and bracketed/filler tokens (hmm, uh, um); "
        "standardises apostrophes and expands common contractions; converts spelled-out numbers "
        "and number words to digits; maps British to American spellings (1,740-entry map); and "
        "collapses whitespace.", "",
        "Scoring: jiwer word alignment on the normalised strings (default transforms); WER = "
        "(S + D + I) / reference words. CER from jiwer character alignment (secondary).", "",
        "Examples:", "", md_table(rows), "",
        "The policy was fixed before any pilot or confirmation decoding and is not changed after "
        "seeing codec results.", "",
    ])


# ==================================================
# Pilot
# ==================================================

def pilot_figures(metrics: pd.DataFrame, boot: pd.DataFrame, out: Path) -> None:
    style()
    fig_wer_by_condition(boot, "pilot", out / "pilot_fig01_wer_by_condition.png")
    fig_bandwidth_vs_residual(boot, "pilot", out / "pilot_fig02_bandwidth_vs_codec_residual.png")
    fig_paired_differences(metrics, "pilot", out / "pilot_fig03_paired_utterance_differences.png")
    fig_bootstrap_ci(boot, ["pilot"], out / "pilot_fig04_bootstrap_ci.png")
    fig_model_comparison(boot, "pilot", out / "pilot_fig05_asr_model_comparison.png")


def render_pilot(decision: dict, boot: pd.DataFrame, corpus: pd.DataFrame) -> str:
    cells = pd.DataFrame(decision["cells"])
    wer = corpus[(corpus["scope"] == "pooled")].pivot(index="condition", columns="model",
                                                      values="wer_pct").loc[CONDITIONS].reset_index()
    rows = []
    for model in MODELS:
        for q in list(QUANTITY_LABELS):
            r = stats.lookup(boot, "pilot", model, q)
            rows.append({"model": model, "quantity": QUANTITY_LABELS[q], "micro": ci_text(r)})
    return "\n".join([
        "# Stage 3 pilot (kill test)", "",
        f"**Pilot decision: {decision['decision']}** — {decision['reason']}.", "",
        f"Rule (frozen): {decision['rule']}.", "",
        "## Residuals", "", md_table(cells), "",
        "## Corpus WER (%)", "", md_table(wer), "",
        "## All paired quantities (micro, 95% speaker-bootstrap CI)", "", md_table(pd.DataFrame(rows)), "",
    ])


# ==================================================
# Final analysis
# ==================================================

def final_analysis(spec, freeze, out: Path, raw: Path, metrics: pd.DataFrame, seal) -> None:
    style()
    sets = ["pilot", "confirmation"]

    def concat(name, **kwargs):
        return pd.concat([pd.read_csv(raw / s / name, **kwargs) for s in sets], ignore_index=True)

    audio_rows = concat("audio_manifest.csv")
    asr_rows = concat("asr_outputs.csv", keep_default_na=False)
    signal = concat("signal_metrics.csv")
    pooled = concat("pooled_transfer.csv")
    audio_rows.to_csv(out / "03_audio_manifest.csv", index=False)
    asr_rows.to_csv(out / "04_asr_outputs.csv", index=False)
    metrics.to_csv(out / "05_utterance_metrics.csv", index=False)
    corpus = stats.corpus_table(metrics)
    corpus.to_csv(out / "06_corpus_metrics.csv", index=False)
    boot = stats.decompose_all(metrics, CONDITIONS, MODELS)
    boot.to_csv(out / "07_paired_bootstrap.csv", index=False)
    signal.to_csv(out / "09_signal_metrics.csv", index=False)
    pooled.to_csv(out / "09_signal_metrics_pooled.csv", index=False)
    signal_summary = signal_summary_table(signal)
    signal_summary.to_csv(out / "09_signal_summary.csv", index=False)

    decision = stats.confirmation_decision(boot, MODELS)
    survives = any(c["robust_positive"] for c in decision["cells"])
    if survives:
        error_types = boot[(boot["kind"] == "micro_error_type")
                           & boot["quantity"].str.match(r"(delta_bw|delta_opus_residual|delta_silk_residual)_[SDI]$")]
        error_types.to_csv(out / "08_error_type_analysis.csv", index=False)
        correlations = []
        for codec in ["OPUS", "SILK"]:
            frame = residual_frame(metrics, signal, "confirmation", codec)
            for model in MODELS:
                for row in stats.exploratory_correlations(frame[frame["model"] == model],
                                                          "residual_pp", EXPLORATORY_FEATURES):
                    correlations.append({"set": "confirmation", "codec": codec, "model": model, **row})
        pd.DataFrame(correlations).to_csv(out / "11_exploratory_signal_correlations.csv", index=False)
    else:
        pd.DataFrame([{"note": "not run: no codec residual CI lower bound > 0 on confirmation"}]).to_csv(
            out / "08_error_type_analysis.csv", index=False)

    fig_wer_by_condition(boot, "confirmation", out / "fig01_wer_by_condition.png")
    fig_bandwidth_vs_residual(boot, "confirmation", out / "fig02_bandwidth_vs_codec_residual.png")
    fig_paired_differences(metrics, "confirmation", out / "fig03_paired_utterance_differences.png")
    fig_bootstrap_ci(boot, sets, out / "fig04_bootstrap_ci.png")
    fig_model_comparison(boot, "confirmation", out / "fig05_asr_model_comparison.png")
    if survives:
        fig_error_types(boot, "confirmation", out / "fig06_error_type_breakdown.png")
        fig_residual_vs_distortion(metrics, signal, "confirmation",
                                   out / "fig07_residual_vs_signal_distortion.png")

    digest = seal(out / "stage3_decision.json", {
        "spec_sha256": spec["spec_sha256"], "confirmation_freeze_sha256": freeze["freeze_sha256"],
        "bootstrap_sha256": hashlib.sha256((out / "07_paired_bootstrap.csv").read_bytes()).hexdigest(),
        **decision, "residual_survives": survives,
    }, "decision_sha256")
    (out / "10_reproduce_commands.txt").write_text(reproduce_commands(spec, freeze))
    (out / "01_stage3_summary.md").write_text(render_summary(
        spec, freeze, decision, digest, boot, corpus, pooled, signal_summary, survives,
        out / "11_exploratory_signal_correlations.csv", read_pilot_decision(out)))
    print(json.dumps({k: decision[k] for k in ("decision", "reason", "result_types")}, indent=1))


def signal_summary_table(signal: pd.DataFrame) -> pd.DataFrame:
    columns = [c for c in signal.columns if c.startswith(("vs_ref_", "vs_lp_"))
               and pd.api.types.is_numeric_dtype(signal[c])
               and not pd.api.types.is_bool_dtype(signal[c])]
    return (signal[signal["condition"] != "REF"].groupby(["set", "condition"], sort=False)[columns]
            .median().reset_index())


def reproduce_commands(spec: dict, freeze: dict) -> str:
    python = "/home/mei/elec5305-project/.venv/bin/python"
    return "\n".join([
        "# Stage 3 reproduction (run from the repository root, in this order)",
        f"# spec SHA-256 {spec['spec_sha256']}", f"# confirmation freeze SHA-256 {freeze['freeze_sha256']}",
        f"# environment: stage3_spec.json + requirements-lock.txt (transformers "
        f"{spec['environment']['packages'].get('transformers')}); the Stage 3 commit contains the "
        f"frozen Stage 1/2 state (tag {spec['provenance']['stage2_tag']} is its ancestor)",
        "# Re-running 'select' / 'freeze-spec' refuses to overwrite sealed files: use a clean output",
        "# directory to reproduce, then compare the sealed hashes.",
        f"{python} -m pip install transformers==5.17.0",
        f"{python} paper/run_stage3.py select",
        f"{python} paper/run_stage3.py env-check",
        f"{python} paper/run_stage3.py calibrate",
        f"{python} paper/run_stage3.py freeze-spec",
        f"{python} paper/run_stage3.py run --set pilot",
        f"{python} paper/run_stage3.py pilot-decision",
        f"{python} paper/run_stage3.py freeze-confirmation",
        f"{python} paper/run_stage3.py run --set confirmation",
        f"{python} paper/run_stage3.py analyze",
        f"{python} -m unittest discover -s paper/tests -v", "",
    ])


def render_summary(spec, freeze, decision, digest, boot, corpus, pooled, signal_summary,
                   survives, correlations_path: Path, pilot_text: str) -> str:
    L = lambda s, m, q, k="micro", scope="pooled": stats.lookup(boot, s, m, q, kind=k, scope=scope)
    cells = {(c["model"], c["codec"]): c for c in decision["cells"]}
    sel = spec["data"]["selections"]

    wer_rows = []
    for model in MODELS:
        for condition in CONDITIONS:
            r = L("confirmation", model, f"wer_{condition}")
            wer_rows.append({"model": asr.MODEL_LABELS[model], "condition": condition,
                             "corpus WER %": f"{r['estimate']:.2f} [{r['ci_lower']:.2f}, {r['ci_upper']:.2f}]"})
    wer_table = pd.DataFrame(wer_rows).pivot(index="condition", columns="model",
                                             values="corpus WER %").loc[CONDITIONS].reset_index()

    def component_table(quantities, set_name="confirmation"):
        rows = []
        for q in quantities:
            row = {"quantity": QUANTITY_LABELS.get(q, q)}
            for model in MODELS:
                row[f"{asr.MODEL_LABELS[model]} micro"] = ci_text(L(set_name, model, q))
                row[f"{asr.MODEL_LABELS[model]} macro"] = ci_text(L(set_name, model, q, "macro"))
            rows.append(row)
        return md_table(pd.DataFrame(rows))

    subset_rows = []
    scopes = sorted(s for s in boot.loc[boot["set"] == "confirmation", "scope"].unique() if s != "pooled")
    for scope in scopes:
        for q in ["delta_bw", "delta_opus_residual", "delta_silk_residual"]:
            row = {"subset": scope, "quantity": QUANTITY_LABELS[q]}
            for model in MODELS:
                row[asr.MODEL_LABELS[model]] = ci_text(L("confirmation", model, q, scope=scope))
            subset_rows.append(row)

    shares = []
    for model in MODELS:
        for q in ["bw_share_of_opus_total", "bw_share_of_silk_total"]:
            r = L("confirmation", model, q, k="ratio")
            shares.append(f"{asr.MODEL_LABELS[model]} {q.replace('_', ' ')}: "
                          f"{r['estimate']:.2f} [{r['ci_lower']:.2f}, {r['ci_upper']:.2f}] "
                          f"({r['n_boot_valid']} valid replicates)")

    pilot_cells = pd.DataFrame([{
        "model": asr.MODEL_LABELS[m], "codec": c,
        "pilot residual": ci_text(L("pilot", m, stats.RESIDUALS[c])),
        "confirmation residual": ci_text(L("confirmation", m, stats.RESIDUALS[c])),
    } for m in MODELS for c in stats.RESIDUALS])

    consistency = []
    for q in PRIMARY_QUANTITIES:
        a, b = L("confirmation", "whisper", q), L("confirmation", "wav2vec2", q)
        same_sign = np.sign(a["estimate"]) == np.sign(b["estimate"])
        consistency.append({"quantity": QUANTITY_LABELS[q], "Whisper": ci_text(a),
                            "wav2vec2": ci_text(b), "same sign": bool(same_sign),
                            "both CIs exclude 0": bool(a["excludes_zero"] and b["excludes_zero"])})
    ranking = {m: sorted(stats.RESIDUALS, key=lambda c: -cells[(m, c)]["estimate_pp"]) for m in MODELS}

    error_text = "Not run: no codec residual survived confirmation (frozen rule)."
    if survives:
        error_lines = []
        for model in MODELS:
            for q in ["delta_opus_residual", "delta_silk_residual"]:
                parts = [f"{t} {ci_text(L('confirmation', model, f'{q}_{t}', 'micro_error_type'))}"
                         for t in ["S", "D", "I"]]
                error_lines.append(f"- {asr.MODEL_LABELS[model]}, {QUANTITY_LABELS[q]}: "
                                   + "; ".join(parts) + " (per 100 reference words)")
        error_text = "\n".join(error_lines)

    p = pooled[pooled["set"] == "confirmation"].set_index(["reference", "processed"])
    s = signal_summary[signal_summary["set"] == "confirmation"].set_index("condition")
    signal_lines = [
        f"- In-band LSD 0–3 kHz vs REF (median): LP {s.loc['LP', 'vs_ref_lsd_0_3k_db']:.2f} dB, "
        f"OPUS {s.loc['OPUS', 'vs_ref_lsd_0_3k_db']:.2f} dB, SILK {s.loc['SILK', 'vs_ref_lsd_0_3k_db']:.2f} dB, "
        f"NEG_LP {s.loc['NEG_LP', 'vs_ref_lsd_0_3k_db']:.2f} dB, NEG_CODEC {s.loc['NEG_CODEC', 'vs_ref_lsd_0_3k_db']:.2f} dB.",
        f"- Codec vs LP (median): OPUS in-band LSD 0–3 kHz {s.loc['OPUS', 'vs_lp_lsd_0_3k_db']:.2f} dB, "
        f"SILK {s.loc['SILK', 'vs_lp_lsd_0_3k_db']:.2f} dB; mean coherence with LP 0–3.5 kHz "
        f"OPUS {s.loc['OPUS', 'vs_lp_coherence_0_3500']:.3f}, SILK {s.loc['SILK', 'vs_lp_coherence_0_3500']:.3f}; "
        f"envelope decorrelation OPUS {s.loc['OPUS', 'vs_lp_envelope_decorrelation']:.3f}, "
        f"SILK {s.loc['SILK', 'vs_lp_envelope_decorrelation']:.3f}.",
        f"- Pooled coherent bandwidth vs REF: LP {p.loc[('REF', 'LP'), 'coherent_bandwidth_hz']:.0f} Hz, "
        f"OPUS {p.loc[('REF', 'OPUS'), 'coherent_bandwidth_hz']:.0f} Hz, SILK "
        f"{p.loc[('REF', 'SILK'), 'coherent_bandwidth_hz']:.0f} Hz; 4–5 kHz image (mirror coherence) "
        f"LP {p.loc[('REF', 'LP'), 'image_coherence_4100_4900']:.3f}, OPUS "
        f"{p.loc[('REF', 'OPUS'), 'image_coherence_4100_4900']:.3f}, SILK "
        f"{p.loc[('REF', 'SILK'), 'image_coherence_4100_4900']:.3f}.",
        f"- Total 4–8 kHz power vs REF (pooled): LP {p.loc[('REF', 'LP'), 'total_hf_power_db']:.1f} dB, "
        f"OPUS {p.loc[('REF', 'OPUS'), 'total_hf_power_db']:.1f} dB, SILK "
        f"{p.loc[('REF', 'SILK'), 'total_hf_power_db']:.1f} dB.",
        "- STOI/PESQ: not computed (packages not installed; descriptive only per the brief).",
    ]
    if survives and correlations_path.exists():
        corr = pd.read_csv(correlations_path)
        top = corr[corr["excludes_zero"]].sort_values("spearman", key=np.abs, ascending=False).head(6)
        signal_lines.append("- Exploratory (Step 12, not confirmatory) residual correlations whose "
                            "bootstrap CI excludes 0: " + ("; ".join(
                                f"{r.codec}/{r.model} {r.feature} rho={r.spearman:+.2f} "
                                f"[{r.ci_lower:+.2f}, {r.ci_upper:+.2f}]" for r in top.itertuples())
                                if len(top) else "none"))

    supported, unsupported = supported_statements(boot, decision, L)
    negative = pd.DataFrame(decision["negative_controls"])
    return "\n".join([
        "# Stage 3 Decision", "",
        f"**{decision['decision']}** — {decision['reason']}.", "",
        f"Result types: {'; '.join(decision['result_types']) or 'none of the pre-declared types'}. "
        f"Decision record `stage3_decision.json` SHA-256 `{digest}`.", "",
        "# Frozen Design", "",
        f"- Spec `00_FROZEN_STAGE3_SPEC.md` / `stage3_spec.json` SHA-256 `{spec['spec_sha256']}` "
        f"(created {spec['created_utc']}, before any pilot or confirmation decoding).",
        f"- Confirmation freeze SHA-256 `{freeze['freeze_sha256']}` (created {freeze['created_utc']}); "
        f"code changed since spec: {freeze['code_changed_since_spec'] or 'none'}.",
        f"- Conditions: REF, LP (frozen filter `{audio.FROZEN_LP_SHA256[:16]}…`), OPUS (Opus 8 kbps, "
        "SILK-NB), SILK (SILK-NB 40 kbps); controls NEG_LP (flat to 7 kHz) and NEG_CODEC (Opus 64 kbps).",
        f"- Sets (speaker-disjoint): calibration {sel['calibration']['n_utterances']} utt / "
        f"{sel['calibration']['n_speakers']} spk (dev-clean); pilot {sel['pilot']['n_utterances']} / "
        f"{sel['pilot']['n_speakers']} (dev-clean + dev-other); confirmation "
        f"{sel['confirmation']['n_utterances']} / {sel['confirmation']['n_speakers']} (test-clean + "
        "test-other, never decoded before in this project).",
        f"- Provenance: Stage 2 tag `{spec['provenance']['stage2_tag']}` "
        f"(commit `{spec['provenance']['stage2_commit'][:12]}`), revised-spec "
        f"`{spec['provenance']['revised_gate5_spec_sha256'][:16]}…`, Stage 2B selection "
        f"`{spec['provenance']['stage2b_confirmation_selection_sha256'][:16]}…`.", "",
        "# ASR Systems", "",
        f"- Model A: Whisper large-v3 (`{spec['asr_models']['whisper']['revision'][:12]}`), "
        "float16, greedy, temperature 0 without fallback, English, no prompt, no VAD.",
        "- Model B: wav2vec2-base-960h (torchaudio), greedy CTC, frozen ELEC5305 decoder.",
        "- Same Whisper EnglishTextNormalizer for references and all hypotheses.", "",
        "# Pilot", "",
        f"Pilot decision: {pilot_text}. Pilot vs confirmation residuals (micro, 95% CI):", "",
        md_table(pilot_cells), "",
        "# Confirmation", "",
        "Corpus WER (%) on the confirmation set, 95% speaker-bootstrap CI:", "",
        md_table(wer_table), "",
        "# Bandwidth Penalty", "",
        component_table(["delta_bw", "delta_opus_total", "delta_silk_total"]), "",
        *[f"- {line}" for line in shares], "",
        "# Codec-Specific Residual", "",
        component_table(["delta_opus_residual", "delta_silk_residual", "opus_minus_silk"]), "",
        "Per subset (secondary):", "", md_table(pd.DataFrame(subset_rows)), "",
        "# Cross-ASR Consistency", "",
        md_table(pd.DataFrame(consistency)), "",
        f"Residual ranking by estimate: Whisper {' > '.join(ranking['whisper'])}; "
        f"wav2vec2 {' > '.join(ranking['wav2vec2'])}.", "",
        "# Uncertainty", "",
        f"Paired percentile bootstrap over speakers (stratified by subset), {stats.N_BOOT} "
        f"replicates, seed {stats.BOOT_SEED}; confirmation has "
        f"{sel['confirmation']['n_speakers']} speakers. Micro = corpus WER from total edit counts "
        "(primary); macro = mean per-utterance difference (secondary). Negative controls:", "",
        md_table(negative), "",
        "# Error Types", "", error_text, "",
        "# Signal-Level Interpretation", "", *signal_lines, "",
        "# What Is Supported", "", *[f"- {s}" for s in supported], "",
        "# What Is NOT Supported", "", *[f"- {s}" for s in unsupported], "",
        "# Next Step", "", next_step(decision, survives), "",
    ])


def read_pilot_decision(out: Path) -> str:
    path = out / "pilot" / "pilot_decision.json"
    if not path.exists():
        return "pilot decision record not found"
    record = json.loads(path.read_text())
    return f"{record['decision']} ({record['reason']}; SHA-256 `{record['decision_sha256'][:16]}…`)"


def supported_statements(boot, decision, L) -> tuple[list[str], list[str]]:
    supported, unsupported = [], []
    bw = {m: L("confirmation", m, "delta_bw") for m in MODELS}
    if all(r["ci_lower"] > 0 for r in bw.values()):
        supported.append("Bandwidth removal alone (frozen LP) increases WER in both recognisers: "
                         + "; ".join(f"{asr.MODEL_LABELS[m]} {ci_text(bw[m])}" for m in MODELS) + ".")
    elif all(not r["excludes_zero"] for r in bw.values()):
        supported.append("Bandwidth removal alone (frozen LP) produces no measurable WER change "
                         "in either recogniser (both CIs include 0).")
    else:
        supported.append("The bandwidth penalty is recogniser-dependent: "
                         + "; ".join(f"{asr.MODEL_LABELS[m]} {ci_text(bw[m])}" for m in MODELS) + ".")
    for codec, quantity in stats.RESIDUALS.items():
        rows = {m: L("confirmation", m, quantity) for m in MODELS}
        text = "; ".join(f"{asr.MODEL_LABELS[m]} {ci_text(rows[m])}" for m in MODELS)
        if all(r["ci_lower"] > 0 for r in rows.values()):
            supported.append(f"After bandwidth control, {codec} shows a codec-specific residual "
                             f"ASR penalty in both recognisers ({text}).")
        elif any(r["ci_lower"] > 0 for r in rows.values()):
            supported.append(f"A {codec} residual is present in only one recogniser ({text}); "
                             "the effect is recogniser-dependent.")
        else:
            unsupported.append(f"A {codec}-specific residual beyond bandwidth ({text}; CIs include 0 "
                               "or are negative).")
    unsupported += [
        "Any causal mechanism for the residual (Step 12 correlations are exploratory).",
        "Universality across ASR systems (two recognisers were tested).",
        "Human intelligibility or perceived quality equivalence of any condition.",
        "Codec quality rankings, or novelty claims about codec effects on ASR.",
        "Generalisation beyond LibriSpeech read English at 16 kHz.",
    ]
    return supported, unsupported


def next_step(decision: dict, survives: bool) -> str:
    d = decision["decision"]
    if d == "KILL":
        return ("Report that bandwidth-matched linear filtering explains the narrowband ASR penalty "
                "within the measured uncertainty; no mechanism analysis is warranted.")
    if d in ("GO", "CONDITIONAL GO"):
        return ("Mechanism analysis (Step 12 follow-up, pre-registered): separate the codec residual "
                "into the deterministic 4–5 kHz image (present in OPUS and SILK, absent from LP) and "
                "in-band coding distortion, e.g. with an LP + synthetic-image control; test "
                "phonetic-class error concentration on a fresh held-out set.")
    return ("Resolve the recogniser dependence or negative-control flag before any mechanism "
            "claim; consider a third, structurally different recogniser on a fresh set.")
