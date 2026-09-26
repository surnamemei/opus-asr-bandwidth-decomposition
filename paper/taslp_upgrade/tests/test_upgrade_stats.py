"""
Estimands and bootstrap of the TASLP upgrade (synthetic data only; no audio, no ASR).

    python -m unittest discover -s paper/taslp_upgrade/tests -v
"""

import math
import unittest

import numpy as np

import helpers  # noqa: F401  (paths, working directory)
import stage3_stats as s3stats
import upgrade_stats as ustats


N_BOOT = 400


def paired(frame, model="whisper", conditions=None):
    return s3stats.PairedSet(frame[frame["model"] == model], conditions)


class TestConstants(unittest.TestCase):

    def test_frozen_values(self):
        self.assertEqual(ustats.N_BOOT, 10000)
        self.assertEqual(ustats.LEVEL_SEED, 5305)
        self.assertEqual(ustats.SWEEP_SEED, 5306)
        self.assertEqual(ustats.SWEEP_RATES_KBPS, [8, 12, 16, 24, 40])
        self.assertEqual(ustats.SWEEP_CONDITIONS, ["LP", "SILK8", "SILK12", "SILK16", "SILK24", "SILK40"])
        self.assertEqual(ustats.LEVEL_CONDITIONS, ["LP", "OPUS", "OPUS8_LEVEL_MATCHED"])
        self.assertEqual((ustats.A_GO_FRACTION, ustats.A_FALSIFY_FRACTION, ustats.B_SLOPE_FRACTION),
                         (0.25, 0.5, 0.5))
        self.assertEqual(ustats.LEVEL_CONTRASTS[0], ("L_level_matched_minus_lp", "OPUS8_LEVEL_MATCHED", "LP"))

    def test_log2_rates(self):
        self.assertEqual(ustats.LOG2_RATES, [math.log2(b) for b in (8, 12, 16, 24, 40)])


class TestSlope(unittest.TestCase):

    def test_ols_slope_matches_polyfit(self):
        rng = np.random.default_rng(1)
        y = rng.normal(size=(50, 5))
        expected = np.array([np.polyfit(ustats.LOG2_RATES, row, 1)[0] for row in y])
        np.testing.assert_allclose(ustats.ols_slope(ustats.LOG2_RATES, y), expected, atol=1e-12)

    def test_exact_line(self):
        x = np.array(ustats.LOG2_RATES)
        y = (2.0 - 0.3 * x)[None, :]
        self.assertAlmostEqual(float(ustats.ols_slope(x, y)[0]), -0.3, places=12)


class TestLevelQuantities(unittest.TestCase):

    def setUp(self):
        self.frame = synthetic = helpers.synthetic_metrics(
            ustats.LEVEL_CONDITIONS, {"LP": 0.2, "OPUS": 1.2, "OPUS8_LEVEL_MATCHED": 1.1}, seed=3)
        self.paired = paired(synthetic, conditions=ustats.LEVEL_CONDITIONS)

    def test_replicates_identical_to_stage3_decompose(self):
        """Seed 5305 on the same speakers resamples exactly as Stage 3 (A's reproduction property)."""
        ours = {r["quantity"]: r for r in ustats.level_quantities(self.paired, n_boot=N_BOOT)
                if r["kind"] == "micro"}
        stage3 = {r["quantity"]: r for r in s3stats.decompose(self.paired, ustats.LEVEL_CONDITIONS,
                                                              n_boot=N_BOOT) if r["kind"] == "micro"}
        for key in ["estimate", "ci_lower", "ci_upper"]:
            self.assertEqual(ours["T_opus_minus_lp"][key], stage3["delta_opus_residual"][key])
            self.assertEqual(ours["wer_LP"][key], stage3["wer_LP"][key])

    def test_micro_estimate_is_total_edit_counts(self):
        rows = {r["quantity"]: r for r in ustats.level_quantities(self.paired, n_boot=N_BOOT)
                if r["kind"] == "micro"}
        part = self.frame[self.frame["model"] == "whisper"]
        words = part[part["condition"] == "LP"]["n_words"].sum()
        errors = part.groupby("condition")["word_errors"].sum()
        self.assertAlmostEqual(rows["L_level_matched_minus_lp"]["estimate"],
                               100 * (errors["OPUS8_LEVEL_MATCHED"] - errors["LP"]) / words, places=10)
        self.assertAlmostEqual(rows["K_level_matched_minus_opus"]["estimate"],
                               100 * (errors["OPUS8_LEVEL_MATCHED"] - errors["OPUS"]) / words, places=10)

    def test_identical_conditions_give_zero(self):
        frame = helpers.synthetic_metrics(ustats.LEVEL_CONDITIONS, {}, seed=4)
        for c in ["OPUS", "OPUS8_LEVEL_MATCHED"]:
            frame.loc[frame["condition"] == c, ["word_errors", "wer", "substitutions", "char_errors"]] = \
                frame.loc[frame["condition"] == "LP", ["word_errors", "wer", "substitutions", "char_errors"]].values
        rows = ustats.level_quantities(paired(frame, conditions=ustats.LEVEL_CONDITIONS), n_boot=N_BOOT)
        for row in rows:
            if row["quantity"].startswith(("L_", "K_", "T_")):
                self.assertEqual((row["estimate"], row["ci_lower"], row["ci_upper"]), (0.0, 0.0, 0.0))

    def test_unpaired_design_rejected(self):
        frame = self.frame[~((self.frame["condition"] == "OPUS") & (self.frame["utterance"] == "1000-1-0000"))]
        with self.assertRaises(ValueError):
            paired(frame, conditions=ustats.LEVEL_CONDITIONS)


class TestSweepQuantities(unittest.TestCase):

    def setUp(self):
        # residual declines with bitrate: mean extra errors 2.0, 1.4, 1.0, 0.6, 0.2 above LP
        extra = {"LP": 0.0, "SILK8": 2.0, "SILK12": 1.4, "SILK16": 1.0, "SILK24": 0.6, "SILK40": 0.2}
        self.frame = helpers.synthetic_metrics(ustats.SWEEP_CONDITIONS, extra, seed=5,
                                               speakers_per_subset=10)
        self.paired = paired(self.frame, conditions=ustats.SWEEP_CONDITIONS)
        self.rows = ustats.sweep_quantities(self.paired, n_boot=N_BOOT, measured_kbps=[7.4, 11.4, 15.5, 23.4, 39.2])
        self.by = {(r["quantity"], r["kind"]): r for r in self.rows}

    def test_all_estimands_present(self):
        for b in ustats.SWEEP_RATES_KBPS:
            for kind in ["micro", "micro_cer", "macro"]:
                self.assertIn((f"R_{b}", kind), self.by)
            for short in ["S", "D", "I"]:
                self.assertIn((f"R_{b}_{short}", "micro_error_type"), self.by)
        for name in ["S_log2", "S_rank", "S_log2_measured"]:
            self.assertIn((name, "trend"), self.by)
        for name, _, _ in ustats.SWEEP_ADJACENT + [ustats.SWEEP_ENDPOINT]:
            self.assertIn((name, "micro"), self.by)
        self.assertIn(("share_replicates_monotone_non_increasing", "descriptive"), self.by)

    def test_slope_point_estimate_is_ols_of_point_residuals(self):
        residuals = [self.by[(f"R_{b}", "micro")]["estimate"] for b in ustats.SWEEP_RATES_KBPS]
        expected = np.polyfit(ustats.LOG2_RATES, residuals, 1)[0]
        self.assertAlmostEqual(self.by[("S_log2", "trend")]["estimate"], expected, places=10)
        self.assertLess(expected, 0)

    def test_adjacent_and_endpoint_are_residual_differences(self):
        r = {b: self.by[(f"R_{b}", "micro")]["estimate"] for b in ustats.SWEEP_RATES_KBPS}
        for name, a, b in ustats.SWEEP_ADJACENT:
            self.assertAlmostEqual(self.by[(name, "micro")]["estimate"],
                                   r[int(a[4:])] - r[int(b[4:])], places=10)
        self.assertAlmostEqual(self.by[("E_8_40", "micro")]["estimate"], r[8] - r[40], places=10)

    def test_measured_kbps_validated(self):
        with self.assertRaises(ValueError):
            ustats.sweep_quantities(self.paired, n_boot=10, measured_kbps=[8, 12, 16])
        with self.assertRaises(ValueError):
            ustats.sweep_quantities(self.paired, n_boot=10, measured_kbps=[0, 12, 16, 24, 40])

    def test_monotone_summary_bounds(self):
        share = self.by[("share_replicates_monotone_non_increasing", "descriptive")]["estimate"]
        self.assertTrue(0.0 <= share <= 1.0)
        self.assertIn(self.by[("n_adjacent_declines", "descriptive")]["estimate"], [0, 1, 2, 3, 4])

    def test_analyse_scopes_and_decision_lookup(self):
        table = ustats.analyse(self.frame, ustats.SWEEP_CONDITIONS, ustats.sweep_quantities, n_boot=50)
        self.assertEqual(set(table["scope"]), {"pooled", "test-clean", "test-other"})
        est, lo, hi = ustats.lookup(table, "wav2vec2", "S_log2", kind="trend")
        self.assertTrue(lo <= est <= hi)


if __name__ == "__main__":
    unittest.main()
