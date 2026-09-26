"""
Pre-registered GO / WEAKEN / FALSIFY rules of the TASLP upgrade (pure logic, no data).

    python -m unittest discover -s paper/taslp_upgrade/tests -v
"""

import itertools
import math
import unittest

import numpy as np
import pandas as pd

import helpers  # noqa: F401
import upgrade_stats as ustats


NAN = float("nan")
T = 0.686367          # Whisper T* (frozen Stage 3 OPUS - LP), used only as an example value
S = -0.287667         # Whisper S* example


class TestLevelRule(unittest.TestCase):

    def test_go(self):
        self.assertEqual(ustats.level_rule((0.3, 0.9), (-0.10, 0.05), T), "GO")

    def test_go_needs_positive_l_lower(self):
        self.assertEqual(ustats.level_rule((0.0, 0.9), (-0.10, 0.05), T), "WEAKEN")

    def test_go_boundary_is_strict(self):
        self.assertEqual(ustats.level_rule((0.3, 0.9), (-0.25 * T, 0.05), T), "WEAKEN")

    def test_falsify(self):
        self.assertEqual(ustats.level_rule((-0.1, 0.2), (-0.70, -0.40), T), "FALSIFY")
        self.assertEqual(ustats.level_rule((0.1, 0.2), (-0.70, -0.40), T), "FALSIFY")

    def test_falsify_boundary_is_strict(self):
        self.assertEqual(ustats.level_rule((-0.1, 0.2), (-0.70, -0.5 * T), T), "WEAKEN")

    def test_partial_reduction_weakens(self):
        self.assertEqual(ustats.level_rule((0.2, 0.6), (-0.35, -0.10), T), "WEAKEN")

    def test_nan_never_decides(self):
        self.assertEqual(ustats.level_rule((NAN, 0.9), (-0.1, 0.05), T), "WEAKEN")
        self.assertEqual(ustats.level_rule((0.3, 0.9), (NAN, NAN), T), "WEAKEN")

    def test_invalid_anchor(self):
        with self.assertRaises(ValueError):
            ustats.level_rule((0.3, 0.9), (-0.1, 0.05), 0.0)

    def test_go_and_falsify_exclusive(self):
        values = np.linspace(-1.5, 1.5, 13)
        for l_lo, k_lo, k_hi in itertools.product(values, values, values):
            if k_lo > k_hi:
                continue
            go = l_lo > 0 and k_lo > -0.25 * T
            falsify = k_hi < -0.5 * T
            self.assertFalse(go and falsify)
            expected = "GO" if go else "FALSIFY" if falsify else "WEAKEN"
            self.assertEqual(ustats.level_rule((l_lo, l_lo + 1), (k_lo, k_hi), T), expected)


class TestSweepRule(unittest.TestCase):

    def test_go(self):
        self.assertEqual(ustats.sweep_rule((0.3, 1.0), (-0.40, -0.18), S), "GO")

    def test_go_needs_positive_r8(self):
        self.assertEqual(ustats.sweep_rule((-0.05, 1.0), (-0.40, -0.18), S), "WEAKEN")

    def test_small_decline_weakens(self):
        self.assertEqual(ustats.sweep_rule((0.3, 1.0), (-0.10, -0.02), S), "WEAKEN")

    def test_falsify(self):
        self.assertEqual(ustats.sweep_rule((0.3, 1.0), (-0.10, 0.08), S), "FALSIFY")
        self.assertEqual(ustats.sweep_rule((-0.1, 0.1), (-0.05, 0.05), S), "FALSIFY")

    def test_wide_interval_weakens(self):
        self.assertEqual(ustats.sweep_rule((0.3, 1.0), (-0.60, 0.20), S), "WEAKEN")

    def test_boundaries(self):
        self.assertEqual(ustats.sweep_rule((0.3, 1.0), (0.5 * S, -0.01), S), "GO")      # S_lo <= 0.5 S*
        self.assertEqual(ustats.sweep_rule((0.3, 1.0), (0.5 * S, 0.0), S), "WEAKEN")    # S_hi >= 0, S_lo not > 0.5 S*
        self.assertEqual(ustats.sweep_rule((0.3, 1.0), (0.5 * S + 1e-9, 0.0), S), "FALSIFY")

    def test_nan_never_decides(self):
        self.assertEqual(ustats.sweep_rule((NAN, 1.0), (-0.4, -0.2), S), "WEAKEN")
        self.assertEqual(ustats.sweep_rule((0.3, 1.0), (NAN, NAN), S), "WEAKEN")

    def test_invalid_anchor(self):
        with self.assertRaises(ValueError):
            ustats.sweep_rule((0.3, 1.0), (-0.4, -0.2), 0.1)

    def test_go_and_falsify_exclusive(self):
        values = np.linspace(-1.0, 1.0, 21)
        for r8_lo, s_lo, s_hi in itertools.product(values, values, values):
            if s_lo > s_hi:
                continue
            go = r8_lo > 0 and s_hi < 0 and s_lo <= 0.5 * S
            falsify = s_hi >= 0 and s_lo > 0.5 * S
            self.assertFalse(go and falsify)
            expected = "GO" if go else "FALSIFY" if falsify else "WEAKEN"
            self.assertEqual(ustats.sweep_rule((r8_lo, r8_lo + 1), (s_lo, s_hi), S), expected)


class TestCombine(unittest.TestCase):

    def test_table(self):
        for a, b in itertools.product(ustats.OUTCOMES, repeat=2):
            expected = a if a == b and a in ("GO", "FALSIFY") else "WEAKEN"
            self.assertEqual(ustats.combine({"whisper": a, "wav2vec2": b}), expected)

    def test_rejects_unknown(self):
        with self.assertRaises(ValueError):
            ustats.combine({"whisper": "HOLD", "wav2vec2": "GO"})
        with self.assertRaises(ValueError):
            ustats.combine({})


def table(rows):
    return pd.DataFrame([{"model": m, "scope": "pooled", "quantity": q, "kind": k, "estimate": e,
                          "ci_lower": lo, "ci_upper": hi} for m, q, k, e, lo, hi in rows])


class TestDecisions(unittest.TestCase):

    def test_level_decision(self):
        rows = []
        for m in ustats.MODELS:
            rows += [(m, "L_level_matched_minus_lp", "micro", 0.6, 0.35, 0.85),
                     (m, "K_level_matched_minus_opus", "micro", -0.02, -0.08, 0.04)]
        decision = ustats.level_decision(table(rows), {"whisper": T, "wav2vec2": 2.070618})
        self.assertEqual(decision["outcome"], "GO")
        self.assertAlmostEqual(decision["cells"]["whisper"]["retained_fraction_L_over_T_star"], 0.6 / T)

    def test_sweep_decision_mixed(self):
        rows = [("whisper", "R_8", "micro", 0.7, 0.4, 1.0), ("whisper", "S_log2", "trend", -0.3, -0.4, -0.2),
                ("wav2vec2", "R_8", "micro", 2.0, 1.5, 2.5), ("wav2vec2", "S_log2", "trend", 0.0, -0.2, 0.2)]
        decision = ustats.sweep_decision(table(rows), {"whisper": S, "wav2vec2": -0.929461})
        self.assertEqual({m: c["outcome"] for m, c in decision["cells"].items()},
                         {"whisper": "GO", "wav2vec2": "FALSIFY"})
        self.assertEqual(decision["outcome"], "WEAKEN")

    def test_lookup_requires_one_row(self):
        with self.assertRaises(KeyError):
            ustats.lookup(table([]).reindex(columns=["model", "scope", "quantity", "kind"]), "whisper", "R_8")


if __name__ == "__main__":
    unittest.main()
