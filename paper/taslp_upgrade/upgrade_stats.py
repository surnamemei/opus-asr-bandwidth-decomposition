"""
TASLP-upgrade statistics: estimands, paired speaker-cluster bootstrap and the
pre-registered GO / WEAKEN / FALSIFY rules of the two additions.

    A  OPUS level-matched sensitivity: a post-confirmation sensitivity analysis
       on the Stage 3 confirmation set, not a second confirmatory test
    B  forced SILK-NB bitrate sweep: pre-registered, on fresh utterances
       (a fresh-utterance, not fresh-speaker, holdout)

The frozen Stage 3 machinery is reused unchanged (paper/stage3_stats.py):
PairedSet (per-utterance edit counts, paired over conditions),
bootstrap_weights (speakers resampled with replacement within subset strata)
and percentile_interval (95 % percentile interval). Every derived quantity
(contrasts, trend slopes) is recomputed inside each bootstrap replicate from
that replicate's corpus WERs.

Units: WERs and contrasts in percentage points (pp); trend slopes in pp per
doubling of bitrate (log2 bitrate) or pp per rate step (rank scores).

Every constant below is part of the frozen upgrade specification
(paper/taslp_upgrade/upgrade_spec.json); tests check that they agree.
"""

import math

import numpy as np
import pandas as pd

import stage3_stats as s3stats


# ==================================================
# Frozen analysis constants
# ==================================================

N_BOOT = s3stats.N_BOOT                 # 10,000, as Stage 3
CI_LEVEL = s3stats.CI_LEVEL             # 95 % percentile intervals, as Stage 3
LEVEL_SEED = s3stats.BOOT_SEED          # 5305: Stage 3's seed on Stage 3's speakers
SWEEP_SEED = 5306

MODELS = ["whisper", "wav2vec2"]

# A: level-matched sensitivity
LEVEL_MATCHED = "OPUS8_LEVEL_MATCHED"
LEVEL_CONDITIONS = ["LP", "OPUS", LEVEL_MATCHED]
LEVEL_CONTRASTS = [
    ("L_level_matched_minus_lp", LEVEL_MATCHED, "LP"),      # primary
    ("K_level_matched_minus_opus", LEVEL_MATCHED, "OPUS"),  # effect of level matching
    ("T_opus_minus_lp", "OPUS", "LP"),                      # same-run Stage 3 residual
]
A_GO_FRACTION = 0.25        # GO needs K_lo > -0.25 T*
A_FALSIFY_FRACTION = 0.5    # FALSIFY needs K_hi < -0.50 T*

# B: forced SILK-NB bitrate sweep
SWEEP_RATES_KBPS = [8, 12, 16, 24, 40]
SWEEP_CODED = [f"SILK{b}" for b in SWEEP_RATES_KBPS]
SWEEP_CONDITIONS = ["LP"] + SWEEP_CODED
SWEEP_RESIDUALS = [(f"R_{b}", f"SILK{b}", "LP") for b in SWEEP_RATES_KBPS]
SWEEP_ADJACENT = [(f"D_{a}_{b}", f"SILK{a}", f"SILK{b}")
                  for a, b in zip(SWEEP_RATES_KBPS, SWEEP_RATES_KBPS[1:])]
SWEEP_ENDPOINT = ("E_8_40", "SILK8", "SILK40")
LOG2_RATES = [math.log2(b) for b in SWEEP_RATES_KBPS]
RANK_SCORES = [1.0, 2.0, 3.0, 4.0, 5.0]
B_SLOPE_FRACTION = 0.5      # a meaningful decline is at least 0.5 x the Stage-3-implied slope S*

OUTCOMES = ("GO", "WEAKEN", "FALSIFY")
ERROR_FIELDS = s3stats.ERROR_FIELDS


# ==================================================
# Bootstrap replicates
# ==================================================

def replicate_weights(paired: s3stats.PairedSet, seed: int, n_boot: int = N_BOOT) -> np.ndarray:
    """
    Speaker multiplicities: row 0 is the point estimate (every speaker once), rows
    1..n_boot are bootstrap replicates. Built exactly as paper/stage3_stats.decompose
    builds them, so the same seed on the same speakers gives the same replicates.
    """
    rng = np.random.default_rng(seed)
    return np.vstack([np.ones(len(paired.speakers)),
                      s3stats.bootstrap_weights(paired.speaker_stratum, n_boot, rng)])


class Replicates:
    """Corpus-level quantities of one model / scope for the point estimate and every replicate."""

    def __init__(self, paired: s3stats.PairedSet, weights: np.ndarray):
        self.paired = paired
        self.weights = weights
        self.words = weights @ paired.speaker_sum(paired.n_words)
        self.chars = weights @ paired.speaker_sum(paired.n_chars)
        self.count = weights @ paired.speaker_sum(np.ones(len(paired.utterances)))

    def _sum(self, values: np.ndarray) -> np.ndarray:
        return self.weights @ self.paired.speaker_sum(values)

    def micro(self, condition: str) -> np.ndarray:
        return self._sum(self.paired.values[condition]["word_errors"]) / self.words

    def cer(self, condition: str) -> np.ndarray:
        return self._sum(self.paired.values[condition]["char_errors"]) / self.chars

    def macro_difference(self, a: str, b: str) -> np.ndarray:
        values = self.paired.values
        return self._sum(values[a]["wer"] - values[b]["wer"]) / self.count

    def error_type_difference(self, a: str, b: str, field: str) -> np.ndarray:
        values = self.paired.values
        return self._sum(values[a][field] - values[b][field]) / self.words


def interval_row(quantity: str, kind: str, series: np.ndarray, unit: str, scale: float) -> dict:
    """Point estimate (row 0) and percentile interval over the replicates (rows 1..)."""
    series = np.asarray(series, dtype=float) * scale
    lo, hi = s3stats.percentile_interval(series[1:])
    return {"quantity": quantity, "kind": kind, "unit": unit, "estimate": float(series[0]),
            "ci_lower": lo, "ci_upper": hi, "excludes_zero": bool(lo > 0 or hi < 0),
            "n_boot_valid": int(np.sum(np.isfinite(series[1:])))}


def descriptive_row(quantity: str, value: float, unit: str) -> dict:
    return {"quantity": quantity, "kind": "descriptive", "unit": unit, "estimate": float(value),
            "ci_lower": float("nan"), "ci_upper": float("nan"), "excludes_zero": False,
            "n_boot_valid": 0}


def contrast_rows(rep: Replicates, name: str, a: str, b: str, full: bool = True) -> list[dict]:
    rows = [interval_row(name, "micro", rep.micro(a) - rep.micro(b), "pp", 100.0)]
    if full:
        rows.append(interval_row(name, "micro_cer", rep.cer(a) - rep.cer(b), "pp", 100.0))
        rows.append(interval_row(name, "macro", rep.macro_difference(a, b), "pp", 100.0))
        for field, short in ERROR_FIELDS.items():
            rows.append(interval_row(f"{name}_{short}", "micro_error_type",
                                     rep.error_type_difference(a, b, field), "per_100_words", 100.0))
    return rows


def ols_slope(x, y: np.ndarray) -> np.ndarray:
    """Least-squares slope of every row of y (n_rows, k) on x (k,), equal weights."""
    x = np.asarray(x, dtype=float)
    xc = x - x.mean()
    y = np.asarray(y, dtype=float)
    return (y - y.mean(axis=1, keepdims=True)) @ xc / float(xc @ xc)


# ==================================================
# Estimands
# ==================================================

def level_quantities(paired: s3stats.PairedSet, seed: int = LEVEL_SEED, n_boot: int = N_BOOT) -> list[dict]:
    """A: WER per condition; L (primary), K and the same-run OPUS - LP with secondary estimators."""
    rep = Replicates(paired, replicate_weights(paired, seed, n_boot))
    rows = []
    for condition in LEVEL_CONDITIONS:
        rows.append(interval_row(f"wer_{condition}", "micro", rep.micro(condition), "pp", 100.0))
        rows.append(interval_row(f"cer_{condition}", "micro", rep.cer(condition), "pp", 100.0))
    for name, a, b in LEVEL_CONTRASTS:
        rows += contrast_rows(rep, name, a, b)
    return rows


def sweep_quantities(paired: s3stats.PairedSet, seed: int = SWEEP_SEED, n_boot: int = N_BOOT,
                     measured_kbps: list[float] | None = None) -> list[dict]:
    """
    B: WER per condition; R_b (primary) with secondary estimators; the primary
    log2-bitrate trend S; the ordered (rank) and measured-bitrate trend
    sensitivities; adjacent-rate and endpoint contrasts; monotonicity summary.
    """
    rep = Replicates(paired, replicate_weights(paired, seed, n_boot))
    rows = []
    for condition in SWEEP_CONDITIONS:
        rows.append(interval_row(f"wer_{condition}", "micro", rep.micro(condition), "pp", 100.0))
        rows.append(interval_row(f"cer_{condition}", "micro", rep.cer(condition), "pp", 100.0))
    residuals = []
    for name, a, b in SWEEP_RESIDUALS:
        rows += contrast_rows(rep, name, a, b)
        residuals.append(100.0 * (rep.micro(a) - rep.micro(b)))
    r = np.column_stack(residuals)                       # (1 + n_boot, 5), pp

    rows.append(interval_row("S_log2", "trend", ols_slope(LOG2_RATES, r), "pp_per_doubling", 1.0))
    rows.append(interval_row("S_rank", "trend", ols_slope(RANK_SCORES, r), "pp_per_step", 1.0))
    if measured_kbps is not None:
        if len(measured_kbps) != len(SWEEP_RATES_KBPS) or min(measured_kbps) <= 0:
            raise ValueError("measured_kbps needs one positive value per rate")
        rows.append(interval_row("S_log2_measured", "trend",
                                 ols_slope(np.log2(np.asarray(measured_kbps, dtype=float)), r),
                                 "pp_per_doubling", 1.0))

    for name, a, b in SWEEP_ADJACENT + [SWEEP_ENDPOINT]:
        rows += contrast_rows(rep, name, a, b, full=False)

    declines = r[:, :-1] - r[:, 1:]                      # R_b - R_b' for b < b'; > 0 means a decline
    rows.append(descriptive_row("n_adjacent_declines", float(np.sum(declines[0] > 0)), "count"))
    rows.append(descriptive_row("share_replicates_monotone_non_increasing",
                                float(np.mean(np.all(declines[1:] >= 0, axis=1))), "fraction"))
    return rows


def analyse(metrics: pd.DataFrame, conditions: list[str], quantities, models: list[str] = MODELS,
            **kwargs) -> pd.DataFrame:
    """Every (model, scope): pooled (stratified by subset) first, then each subset."""
    rows = []
    for model in models:
        group = metrics[metrics["model"] == model]
        if group.empty:
            raise ValueError(f"no metrics for {model}")
        scopes = [("pooled", group)] + [(s, group[group["subset"] == s])
                                        for s in sorted(group["subset"].unique())]
        for scope, part in scopes:
            paired = s3stats.PairedSet(part, conditions)
            for row in quantities(paired, **kwargs):
                rows.append({"model": model, "scope": scope, **row,
                             "n_speakers": len(paired.speakers),
                             "n_utterances": len(paired.utterances),
                             "n_words": int(paired.n_words.sum())})
    return pd.DataFrame(rows)


def lookup(table: pd.DataFrame, model: str, quantity: str, kind: str = "micro",
           scope: str = "pooled") -> tuple[float, float, float]:
    row = table[(table["model"] == model) & (table["quantity"] == quantity) &
                (table["kind"] == kind) & (table["scope"] == scope)]
    if len(row) != 1:
        raise KeyError(f"{model}/{quantity}/{kind}/{scope}: {len(row)} rows")
    row = row.iloc[0]
    return float(row["estimate"]), float(row["ci_lower"]), float(row["ci_upper"])


# ==================================================
# Pre-registered interpretation rules
# ==================================================

def level_rule(l_interval: tuple[float, float], k_interval: tuple[float, float], t_star: float) -> str:
    """
    A, one recogniser. l_interval = (L_lo, L_hi), k_interval = (K_lo, K_hi) in pp;
    t_star = frozen Stage 3 pooled micro OPUS - LP (pp, > 0).

        GO       L_lo > 0 and K_lo > -0.25 T*
        FALSIFY  K_hi < -0.50 T*
        WEAKEN   otherwise (a NaN bound never satisfies GO or FALSIFY)
    """
    if not t_star > 0:
        raise ValueError("T* must be positive")
    l_lo, _ = l_interval
    k_lo, k_hi = k_interval
    if l_lo > 0 and k_lo > -A_GO_FRACTION * t_star:
        return "GO"
    if k_hi < -A_FALSIFY_FRACTION * t_star:
        return "FALSIFY"
    return "WEAKEN"


def sweep_rule(r8_interval: tuple[float, float], s_interval: tuple[float, float], s_star: float) -> str:
    """
    B, one recogniser. r8_interval = (R8_lo, R8_hi) in pp; s_interval = (S_lo, S_hi)
    in pp per doubling; s_star = Stage-3-implied slope (U* - T*) / log2(40/8) (< 0).

        GO       R8_lo > 0 and S_hi < 0 and S_lo <= 0.5 S*
        FALSIFY  S_hi >= 0 and S_lo > 0.5 S*
        WEAKEN   otherwise (a NaN bound never satisfies GO or FALSIFY)
    """
    if not s_star < 0:
        raise ValueError("S* must be negative")
    r8_lo, _ = r8_interval
    s_lo, s_hi = s_interval
    threshold = B_SLOPE_FRACTION * s_star
    if r8_lo > 0 and s_hi < 0 and s_lo <= threshold:
        return "GO"
    if s_hi >= 0 and s_lo > threshold:
        return "FALSIFY"
    return "WEAKEN"


def combine(per_model: dict[str, str]) -> str:
    """GO if GO for every recogniser, FALSIFY if FALSIFY for every recogniser, else WEAKEN."""
    outcomes = set(per_model.values())
    if not outcomes or not outcomes <= set(OUTCOMES):
        raise ValueError(f"unexpected outcomes {per_model}")
    if outcomes == {"GO"}:
        return "GO"
    if outcomes == {"FALSIFY"}:
        return "FALSIFY"
    return "WEAKEN"


def level_decision(table: pd.DataFrame, t_star: dict[str, float]) -> dict:
    cells = {}
    for model in MODELS:
        l_est, l_lo, l_hi = lookup(table, model, "L_level_matched_minus_lp")
        k_est, k_lo, k_hi = lookup(table, model, "K_level_matched_minus_opus")
        cells[model] = {
            "L": [l_est, l_lo, l_hi], "K": [k_est, k_lo, k_hi], "T_star": t_star[model],
            "go_threshold_K_lower": -A_GO_FRACTION * t_star[model],
            "falsify_threshold_K_upper": -A_FALSIFY_FRACTION * t_star[model],
            "retained_fraction_L_over_T_star": l_est / t_star[model],
            "outcome": level_rule((l_lo, l_hi), (k_lo, k_hi), t_star[model]),
        }
    return {"analysis": "A: post-confirmation sensitivity analysis (not a confirmatory test)",
            "cells": cells,
            "outcome": combine({m: c["outcome"] for m, c in cells.items()})}


def sweep_decision(table: pd.DataFrame, s_star: dict[str, float]) -> dict:
    cells = {}
    for model in MODELS:
        r_est, r_lo, r_hi = lookup(table, model, "R_8")
        s_est, s_lo, s_hi = lookup(table, model, "S_log2", kind="trend")
        cells[model] = {
            "R_8": [r_est, r_lo, r_hi], "S_log2": [s_est, s_lo, s_hi], "S_star": s_star[model],
            "meaningful_decline_threshold": B_SLOPE_FRACTION * s_star[model],
            "outcome": sweep_rule((r_lo, r_hi), (s_lo, s_hi), s_star[model]),
        }
    return {"analysis": "B: pre-registered forced SILK-NB bitrate sweep (fresh-utterance holdout)",
            "cells": cells,
            "outcome": combine({m: c["outcome"] for m, c in cells.items()})}
