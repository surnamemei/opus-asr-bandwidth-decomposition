"""
Stage 3 paired decomposition, speaker bootstrap and decision rules.

All thresholds below are part of the frozen Stage 3 specification.

Quantities (per ASR model, per evaluation set)
----------------------------------------------
micro (primary): differences of corpus WER computed from total edit counts,
    e.g. delta_opus_residual = (sum E_OPUS - sum E_LP) / sum N
macro (secondary): mean over utterances of per-utterance WER differences

Uncertainty: paired percentile bootstrap resampling LibriSpeech speakers with
replacement, stratified by subset (clean / other), all conditions and both
models of an utterance kept together. 95% intervals.
"""

import numpy as np
import pandas as pd


# ==================================================
# Frozen analysis constants
# ==================================================

N_BOOT = 10000
BOOT_SEED = 5305
CI_LEVEL = 0.95
N_BOOT_EXPLORATORY = 2000

CONTRASTS = [
    ("delta_bw", "LP", "REF"),
    ("delta_opus_residual", "OPUS", "LP"),
    ("delta_silk_residual", "SILK", "LP"),
    ("opus_minus_silk", "OPUS", "SILK"),
    ("delta_opus_total", "OPUS", "REF"),
    ("delta_silk_total", "SILK", "REF"),
    ("neg_lp_minus_ref", "NEG_LP", "REF"),
    ("neg_codec_minus_ref", "NEG_CODEC", "REF"),
]
RESIDUALS = {"OPUS": "delta_opus_residual", "SILK": "delta_silk_residual"}
SHARES = [
    ("bw_share_of_opus_total", "delta_bw", "delta_opus_total"),
    ("bw_share_of_silk_total", "delta_bw", "delta_silk_total"),
]
NEGATIVE_CONTROLS = ["neg_lp_minus_ref", "neg_codec_minus_ref"]

# Pilot kill test
PILOT_BOUNDED_SMALL_PP = 1.0        # all residual CI upper bounds below this -> "bounded small"
# Confirmation decision
MIN_RESIDUAL_PP = 0.5               # GO requires the residual estimate >= this in both models
NEGATIVE_CONTROL_MARGIN_PP = 0.5    # control flagged if CI excludes 0 and |estimate| > this

ERROR_FIELDS = {"substitutions": "S", "deletions": "D", "insertions": "I"}


# ==================================================
# Paired arrays
# ==================================================

class PairedSet:
    """Per-utterance edit counts of one model on one evaluation set, all conditions."""

    def __init__(self, metrics: pd.DataFrame, conditions: list[str]):
        table = metrics.set_index(["utterance", "condition"]).sort_index()
        utterances = sorted(metrics["utterance"].unique())
        missing = [(u, c) for u in utterances for c in conditions if (u, c) not in table.index]
        if missing:
            raise ValueError(f"unpaired design: {len(missing)} (utterance, condition) rows missing")

        first = table.xs(conditions[0], level="condition").loc[utterances]
        self.utterances = utterances
        self.speaker = first["speaker_id"].to_numpy()
        self.subset = first["subset"].to_numpy()
        self.n_words = first["n_words"].to_numpy(dtype=float)
        self.n_chars = first["n_chars"].to_numpy(dtype=float)
        self.values = {}
        for condition in conditions:
            rows = table.xs(condition, level="condition").loc[utterances]
            if not np.array_equal(rows["n_words"].to_numpy(dtype=float), self.n_words):
                raise ValueError("reference word counts differ between conditions")
            self.values[condition] = {
                field: rows[field].to_numpy(dtype=float)
                for field in ["word_errors", "substitutions", "deletions", "insertions",
                              "wer", "char_errors"]
            }

        speakers, self.speaker_index = np.unique(self.speaker, return_inverse=True)
        self.speakers = speakers
        self.speaker_stratum = np.array([
            self.subset[self.speaker_index == k][0] for k in range(len(speakers))
        ])

    def speaker_sum(self, values: np.ndarray) -> np.ndarray:
        return np.bincount(self.speaker_index, weights=values, minlength=len(self.speakers))


def bootstrap_weights(strata: np.ndarray, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    """Speaker multiplicities (n_boot, n_speakers), resampled within each stratum."""
    weights = np.zeros((n_boot, len(strata)))
    rows = np.arange(n_boot)[:, None]
    for stratum in np.unique(strata):
        members = np.flatnonzero(strata == stratum)
        draws = rng.integers(0, len(members), size=(n_boot, len(members)))
        np.add.at(weights, (rows, members[draws]), 1.0)
    return weights


def percentile_interval(samples: np.ndarray) -> tuple[float, float]:
    alpha = (1.0 - CI_LEVEL) / 2.0
    samples = samples[np.isfinite(samples)]
    if samples.size == 0:
        return float("nan"), float("nan")
    return float(np.quantile(samples, alpha)), float(np.quantile(samples, 1 - alpha))


# ==================================================
# Decomposition with bootstrap
# ==================================================

def decompose(paired: PairedSet, conditions: list[str], seed: int = BOOT_SEED,
              n_boot: int = N_BOOT) -> list[dict]:
    """Point estimates and bootstrap CIs for every quantity of one model / set / scope."""
    rng = np.random.default_rng(seed)
    weights = np.vstack([np.ones(len(paired.speakers)),
                         bootstrap_weights(paired.speaker_stratum, n_boot, rng)])
    words = weights @ paired.speaker_sum(paired.n_words)
    chars = weights @ paired.speaker_sum(paired.n_chars)
    counts = weights @ paired.speaker_sum(np.ones(len(paired.utterances)))

    micro = {c: weights @ paired.speaker_sum(paired.values[c]["word_errors"]) / words
             for c in conditions}
    cer = {c: weights @ paired.speaker_sum(paired.values[c]["char_errors"]) / chars
           for c in conditions}

    rows = []

    def add(quantity, kind, series, unit="pp"):
        scale = 100.0 if unit == "pp" else 1.0
        lo, hi = percentile_interval(series[1:] * scale)
        rows.append({
            "quantity": quantity, "kind": kind, "unit": unit,
            "estimate": float(series[0] * scale), "ci_lower": lo, "ci_upper": hi,
            "excludes_zero": bool(lo > 0 or hi < 0),
            "n_boot_valid": int(np.sum(np.isfinite(series[1:]))),
        })

    for c in conditions:
        add(f"wer_{c}", "micro", micro[c])
        add(f"cer_{c}", "micro", cer[c])

    contrast_series = {}
    for name, a, b in CONTRASTS:
        if a not in conditions or b not in conditions:
            continue
        contrast_series[name] = micro[a] - micro[b]
        add(name, "micro", contrast_series[name])
        add(name, "micro_cer", cer[a] - cer[b])
        per_utterance = paired.values[a]["wer"] - paired.values[b]["wer"]
        add(name, "macro", weights @ paired.speaker_sum(per_utterance) / counts)
        for field, short in ERROR_FIELDS.items():
            delta = paired.values[a][field] - paired.values[b][field]
            add(f"{name}_{short}", "micro_error_type", weights @ paired.speaker_sum(delta) / words)

    for name, numerator, denominator in SHARES:
        if numerator in contrast_series and denominator in contrast_series:
            num, den = contrast_series[numerator], contrast_series[denominator]
            ratio = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
            add(name, "ratio", ratio, unit="fraction")

    for row in rows:
        row.update({"n_speakers": len(paired.speakers), "n_utterances": len(paired.utterances),
                    "n_words": int(paired.n_words.sum())})
    return rows


def decompose_all(metrics: pd.DataFrame, conditions: list[str], models: list[str]) -> pd.DataFrame:
    """Every (set, model, scope) with scope = pooled (stratified) and each subset."""
    rows = []
    for (set_name, model), group in metrics.groupby(["set", "model"], sort=False):
        scopes = [("pooled", group)] + [
            (subset, group[group["subset"] == subset]) for subset in sorted(group["subset"].unique())
        ]
        for scope, part in scopes:
            paired = PairedSet(part, conditions)
            for row in decompose(paired, conditions):
                rows.append({"set": set_name, "model": model, "scope": scope, **row})
    table = pd.DataFrame(rows)
    table["model_order"] = table["model"].map({m: i for i, m in enumerate(models)})
    return (table.sort_values(["set", "model_order"], kind="stable")
            .drop(columns="model_order").reset_index(drop=True))


def corpus_table(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in metrics.groupby(["set", "model", "condition"], sort=False):
        for scope, part in [("pooled", group)] + [
                (s, group[group["subset"] == s]) for s in sorted(group["subset"].unique())]:
            n = part["n_words"].sum()
            rows.append({
                "set": keys[0], "model": keys[1], "condition": keys[2], "scope": scope,
                "n_utterances": len(part), "n_speakers": part["speaker_id"].nunique(),
                "n_words": int(n),
                "substitutions": int(part["substitutions"].sum()),
                "deletions": int(part["deletions"].sum()),
                "insertions": int(part["insertions"].sum()),
                "word_errors": int(part["word_errors"].sum()),
                "wer_pct": 100.0 * part["word_errors"].sum() / n,
                "cer_pct": 100.0 * part["char_errors"].sum() / part["n_chars"].sum(),
                "mean_utterance_wer_pct": 100.0 * part["wer"].mean(),
                "empty_hypotheses": int((part["hypothesis_normalised"].fillna("").str.strip() == "").sum()),
            })
    return pd.DataFrame(rows)


# ==================================================
# Decisions
# ==================================================

def lookup(boot: pd.DataFrame, set_name: str, model: str, quantity: str,
           kind: str = "micro", scope: str = "pooled") -> dict:
    row = boot[(boot["set"] == set_name) & (boot["model"] == model) & (boot["scope"] == scope)
               & (boot["quantity"] == quantity) & (boot["kind"] == kind)]
    if len(row) != 1:
        raise KeyError((set_name, model, quantity, kind, scope))
    return row.iloc[0].to_dict()


def pilot_decision(boot: pd.DataFrame, models: list[str]) -> dict:
    cells = []
    for model in models:
        for codec, quantity in RESIDUALS.items():
            r = lookup(boot, "pilot", model, quantity)
            cells.append({"model": model, "codec": codec, "estimate_pp": r["estimate"],
                          "ci_lower_pp": r["ci_lower"], "ci_upper_pp": r["ci_upper"],
                          "clearly_positive": r["ci_lower"] > 0})
    proceed = any(c["clearly_positive"] for c in cells)
    bounded = all(c["ci_upper_pp"] < PILOT_BOUNDED_SMALL_PP for c in cells)
    if proceed:
        decision = "PROCEED_TO_CONFIRMATION"
        reason = "at least one codec residual has a 95% CI lower bound above 0"
    elif bounded:
        decision = "STOP_KILL"
        reason = (f"no residual CI excludes 0 and every upper bound is below "
                  f"{PILOT_BOUNDED_SMALL_PP} pp: bandwidth explains nearly all degradation")
    else:
        decision = "STOP_KILL"
        reason = ("no residual CI excludes 0 (pilot rule); upper bounds are not all small, "
                  "so the pilot is inconclusive rather than evidence of no residual")
    return {"decision": decision, "reason": reason, "cells": cells,
            "rule": "PROCEED if any (model, codec) micro residual CI lower bound > 0; else STOP"}


def confirmation_decision(boot: pd.DataFrame, models: list[str]) -> dict:
    cells = {}
    for model in models:
        for codec, quantity in RESIDUALS.items():
            conf = lookup(boot, "confirmation", model, quantity)
            pilot = lookup(boot, "pilot", model, quantity)
            cells[(model, codec)] = {
                "model": model, "codec": codec,
                "estimate_pp": conf["estimate"], "ci_lower_pp": conf["ci_lower"],
                "ci_upper_pp": conf["ci_upper"],
                "robust_positive": conf["ci_lower"] > 0,
                "robust_negative": conf["ci_upper"] < 0,
                "large": conf["estimate"] >= MIN_RESIDUAL_PP,
                "pilot_estimate_pp": pilot["estimate"],
                "pilot_positive": pilot["estimate"] > 0,
            }

    codecs = list(RESIDUALS)
    both = [c for c in codecs if all(cells[(m, c)]["robust_positive"] for m in models)]
    one = [c for c in codecs if sum(cells[(m, c)]["robust_positive"] for m in models) == 1]
    negative = [c for c in codecs if any(cells[(m, c)]["robust_negative"] for m in models)]
    go = [c for c in both if all(cells[(m, c)]["pilot_positive"] and cells[(m, c)]["large"]
                                 for m in models)]
    all_null = all(not cells[k]["robust_positive"] and not cells[k]["robust_negative"]
                   for k in cells)

    if all_null:
        decision, reason = "KILL", "all codec residual CIs include 0 in both ASR architectures"
    elif go:
        decision = "GO"
        reason = (f"{', '.join(go)}: residual CI > 0 in both architectures, estimate >= "
                  f"{MIN_RESIDUAL_PP} pp in both, same direction as the pilot")
    elif both:
        decision = "CONDITIONAL GO"
        reason = (f"{', '.join(both)}: residual CI > 0 in both architectures, but the pilot "
                  f"direction or the {MIN_RESIDUAL_PP} pp size criterion is not met in both")
    elif one or negative:
        decision = "HOLD"
        reason = ("residual robust in only one architecture"
                  + (" / robustly negative residual" if negative else ""))
    else:
        decision, reason = "HOLD", "no consistent residual pattern"

    controls = []
    for model in models:
        for quantity in NEGATIVE_CONTROLS:
            r = lookup(boot, "confirmation", model, quantity)
            flagged = r["excludes_zero"] and abs(r["estimate"]) > NEGATIVE_CONTROL_MARGIN_PP
            controls.append({"model": model, "control": quantity, "estimate_pp": r["estimate"],
                             "ci_lower_pp": r["ci_lower"], "ci_upper_pp": r["ci_upper"],
                             "flagged": flagged})
    capped = False
    if any(c["flagged"] for c in controls) and decision in ("GO", "CONDITIONAL GO"):
        decision, capped = "HOLD", True
        reason += "; capped at HOLD because a negative control failed"

    return {"decision": decision, "reason": reason, "cells": list(cells.values()),
            "negative_controls": controls, "capped_by_negative_control": capped,
            "result_types": result_types(boot, models)}


def result_types(boot: pd.DataFrame, models: list[str]) -> list[str]:
    types = []
    residual = {(m, c): lookup(boot, "confirmation", m, q) for m in models
                for c, q in RESIDUALS.items()}
    bandwidth = {m: lookup(boot, "confirmation", m, "delta_bw") for m in models}
    opus_silk = {m: lookup(boot, "confirmation", m, "opus_minus_silk") for m in models}

    if all(not r["excludes_zero"] for r in residual.values()) and all(
            b["ci_lower"] > 0 for b in bandwidth.values()):
        types.append("TYPE 1: WER_REF < WER_LP ~ WER_CODEC")
    for codec in RESIDUALS:
        if all(residual[(m, codec)]["ci_lower"] > 0 for m in models) and all(
                bandwidth[m]["estimate"] >= 0 for m in models):
            types.append(f"TYPE 2 ({codec}): WER_REF <= WER_LP < WER_{codec}")
    signs = {np.sign(opus_silk[m]["estimate"]) for m in models}
    if all(opus_silk[m]["excludes_zero"] for m in models) and len(signs) == 1:
        types.append("TYPE 3: OPUS and SILK residuals differ (same direction in both models)")
    for codec in RESIDUALS:
        states = [residual[(m, codec)]["ci_lower"] > 0 for m in models]
        if any(states) and not all(states):
            types.append(f"TYPE 4 ({codec}): residual depends on the recogniser")
    return types


# ==================================================
# Exploratory: residual vs signal features (Step 12)
# ==================================================

def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = pd.Series(x).rank(method="average").to_numpy()
    ry = pd.Series(y).rank(method="average").to_numpy()
    rx, ry = rx - rx.mean(), ry - ry.mean()
    denominator = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
    return float((rx * ry).sum() / denominator) if denominator > 0 else float("nan")


def exploratory_correlations(frame: pd.DataFrame, outcome: str, features: list[str],
                             seed: int = BOOT_SEED) -> list[dict]:
    """Spearman correlation of a per-utterance outcome with each feature, speaker bootstrap."""
    rng = np.random.default_rng(seed)
    speakers, index = np.unique(frame["speaker_id"].to_numpy(), return_inverse=True)
    strata = np.array([frame["subset"].to_numpy()[index == k][0] for k in range(len(speakers))])
    members = [np.flatnonzero(index == k) for k in range(len(speakers))]
    weights = bootstrap_weights(strata, N_BOOT_EXPLORATORY, rng).astype(int)
    y = frame[outcome].to_numpy(dtype=float)
    rows = []
    for feature in features:
        x = frame[feature].to_numpy(dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
        estimate = spearman(x[ok], y[ok])
        samples = []
        for w in weights:
            rows_b = np.concatenate([np.repeat(members[k], w[k]) for k in np.flatnonzero(w)])
            rows_b = rows_b[ok[rows_b]]
            samples.append(spearman(x[rows_b], y[rows_b]))
        lo, hi = percentile_interval(np.array(samples))
        rows.append({"feature": feature, "spearman": estimate, "ci_lower": lo, "ci_upper": hi,
                     "excludes_zero": bool(lo > 0 or hi < 0), "n": int(ok.sum())})
    return rows
