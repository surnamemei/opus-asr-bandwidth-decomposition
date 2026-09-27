"""
R1-R3 statistics: estimands, paired speaker-cluster bootstrap and outcomes, as frozen in
reviewer_spec.json. Written at step RS1.

Reuses the frozen machinery unchanged: stage3_stats (PairedSet, bootstrap_weights,
percentile_interval) through upgrade_stats (replicate_weights, Replicates, interval_row,
contrast_rows, analyse, lookup). Every derived quantity is recomputed within each bootstrap
replicate from that replicate's corpus WERs; a ratio is NaN in a replicate whose denominator
is <= 0 (the Stage 3 convention). Outcomes: reviewer_design.rule / combine / r3_outcome.
"""

import numpy as np
import pandas as pd

import reviewer_design as design
import stage3_stats as s3stats
import upgrade_stats as ustats

MODELS = design.MODELS
ERROR_FIELDS = ustats.ERROR_FIELDS


def ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    return np.where(denominator > 0, numerator / np.where(denominator > 0, denominator, 1.0), np.nan)


def difference_of_contrasts(rep: ustats.Replicates, name: str, first: tuple[str, str],
                            second: tuple[str, str]) -> list[dict]:
    """(a - b) - (c - d) with the estimators of ustats.contrast_rows."""
    (a, b), (c, d) = first, second
    rows = [
        ustats.interval_row(name, "micro", (rep.micro(a) - rep.micro(b)) - (rep.micro(c) - rep.micro(d)), "pp", 100.0),
        ustats.interval_row(name, "micro_cer", (rep.cer(a) - rep.cer(b)) - (rep.cer(c) - rep.cer(d)), "pp", 100.0),
        ustats.interval_row(name, "macro", rep.macro_difference(a, b) - rep.macro_difference(c, d), "pp", 100.0),
    ]
    for field, short in ERROR_FIELDS.items():
        rows.append(ustats.interval_row(
            f"{name}_{short}", "micro_error_type",
            rep.error_type_difference(a, b, field) - rep.error_type_difference(c, d, field), "per_100_words", 100.0))
    return rows


def confirmation_quantities(paired: s3stats.PairedSet, lp_dec: str | None = None, r1: bool = True,
                            r2: bool = True, seed: int = design.CONFIRMATION_SEED,
                            n_boot: int = design.N_BOOT) -> list[dict]:
    """RS4a: the same-run Stage 3 decomposition, R1 (P1, D1 and secondaries) and R2 (P2, Delta2, B2, shares)."""
    rep = ustats.Replicates(paired, ustats.replicate_weights(paired, seed, n_boot))
    rows = []
    for condition in paired.values:
        rows.append(ustats.interval_row(f"wer_{condition}", "micro", rep.micro(condition), "pp", 100.0))
        rows.append(ustats.interval_row(f"cer_{condition}", "micro", rep.cer(condition), "pp", 100.0))
    for name, a, b in [("T_opus_minus_lp", "OPUS", "LP"), ("U_silk_minus_lp", "SILK", "LP"),
                       ("B_lp_minus_ref", "LP", "REF"), ("total_opus_minus_ref", "OPUS", "REF")]:
        rows += ustats.contrast_rows(rep, name, a, b)
    if r1:
        rows += ustats.contrast_rows(rep, "P1", design.OPUS_REFDEC, lp_dec)
        rows += difference_of_contrasts(rep, "D1", (design.OPUS_REFDEC, lp_dec), ("OPUS", "LP"))
        secondary = [("silk_refdec_minus_lp_dec", design.SILK_REFDEC, lp_dec),
                     ("opus_refdec_minus_lp", design.OPUS_REFDEC, "LP"),
                     ("opus_refdec_minus_opus", design.OPUS_REFDEC, "OPUS"),
                     ("silk_refdec_minus_silk", design.SILK_REFDEC, "SILK"),
                     ("opus_refdec_minus_silk_refdec", design.OPUS_REFDEC, design.SILK_REFDEC)]
        if lp_dec != "LP":
            secondary.append(("lp_dec_minus_lp", lp_dec, "LP"))
        for name, a, b in secondary:
            rows += ustats.contrast_rows(rep, name, a, b, full=False)
        rows += difference_of_contrasts(rep, "decoder_effect_difference",
                                        (design.OPUS_REFDEC, "OPUS"), (design.SILK_REFDEC, "SILK"))[:1]
    if r2:
        surr8 = design.SURR8
        rows += ustats.contrast_rows(rep, "P2", "OPUS", surr8)
        rows += ustats.contrast_rows(rep, "Delta2", surr8, "LP")
        rows += ustats.contrast_rows(rep, "B2", surr8, "REF")
        total = rep.micro("OPUS") - rep.micro("REF")
        rows.append(ustats.interval_row("s1_primary_share", "ratio",
                                        ratio(rep.micro("LP") - rep.micro("REF"), total), "fraction", 1.0))
        rows.append(ustats.interval_row("s2_surr8_share", "ratio",
                                        ratio(rep.micro(surr8) - rep.micro("REF"), total), "fraction", 1.0))
    return rows


def sweep_quantities(paired: s3stats.PairedSet, seed: int = design.SWEEP_SEED,
                     n_boot: int = design.N_BOOT) -> list[dict]:
    """RS4b: W = WER(WB8) - WER(NB8) with its secondary estimators."""
    rep = ustats.Replicates(paired, ustats.replicate_weights(paired, seed, n_boot))
    rows = []
    for condition in [design.NB8, design.WB8]:
        rows.append(ustats.interval_row(f"wer_{condition}", "micro", rep.micro(condition), "pp", 100.0))
        rows.append(ustats.interval_row(f"cer_{condition}", "micro", rep.cer(condition), "pp", 100.0))
    rows += ustats.contrast_rows(rep, "W", design.WB8, design.NB8)
    return rows


def analyse(metrics: pd.DataFrame, conditions: list[str], quantities, **kwargs) -> pd.DataFrame:
    return ustats.analyse(metrics, conditions, quantities, MODELS, **kwargs)


def lookup(table: pd.DataFrame, model: str, quantity: str, kind: str = "micro") -> tuple[float, float, float]:
    return ustats.lookup(table, model, quantity, kind)


# ==================================================
# Outcomes (reviewer_design rules, frozen with the plan)
# ==================================================

def r1_decision(table: pd.DataFrame, anchors: dict, control: str) -> dict:
    cells = {}
    for model in MODELS:
        p1, d1 = lookup(table, model, "P1"), lookup(table, model, "D1")
        record = design.rule("R1", {"P1": p1[1:], "D1": d1[1:]}, anchors[model]["T_star"]["estimate"])
        cells[model] = {"P1": list(p1), "D1": list(d1), "T_star": anchors[model]["T_star"]["estimate"], **record}
    return {"analysis": "R1: decoder sensitivity with a decoder-matched control (post-confirmation sensitivity "
                        "analysis)", "control": control, "cells": cells, "outcome": design.combine(cells)}


def r2_decision(table: pd.DataFrame, anchors: dict) -> dict:
    cells = {}
    for model in MODELS:
        p2, delta2 = lookup(table, model, "P2"), lookup(table, model, "Delta2")
        record = design.rule("R2", {"P2": p2[1:], "Delta2": delta2[1:]}, anchors[model]["T_star"]["estimate"])
        s1, s2 = lookup(table, model, "s1_primary_share", "ratio"), lookup(table, model, "s2_surr8_share", "ratio")
        low, high = (s1, s2) if s1[0] <= s2[0] else (s2, s1)
        cells[model] = {
            "P2": list(p2), "Delta2": list(delta2), "B2": list(lookup(table, model, "B2")),
            "s1_primary_share": list(s1), "s2_surr8_share": list(s2),
            "sensitivity_range_point": [low[0], high[0]],
            "sensitivity_range_interval": [low[1], high[2]],
            "T_star": anchors[model]["T_star"]["estimate"], **record,
        }
    return {"analysis": "R2: 8-kbit/s effective coherent-linear surrogate, an alternative attribution under a more "
                        "inclusive same-frequency linear-loss definition (post-confirmation sensitivity analysis); "
                        "s1 and s2 form a sensitivity range across two pre-specified linear definitions, not bounds "
                        "on a true share", "cells": cells, "outcome": design.combine(cells)}


def r3_decision(table: pd.DataFrame) -> dict:
    cells = {}
    for model in MODELS:
        w = lookup(table, model, "W")
        cells[model] = {"W": list(w), "outcome": design.r3_outcome(w[1], w[2])}
    return {"analysis": "R3: forced-wideband 8 kbit/s practical counterfactual (not a factorial causal effect)",
            "cells": cells, "outcome": None,
            "note": "per recogniser only; no combined R3 outcome is formed"}
