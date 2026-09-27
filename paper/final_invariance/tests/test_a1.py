"""A1 tests: the OPD projection, the frozen outcome rule, the selection, the plan and the statistics (no ASR)."""

import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FI = HERE.parent
ROOT = FI.parents[1]
for p in [str(FI), str(ROOT / "paper" / "taslp_upgrade"), str(ROOT / "paper")]:
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(ROOT)

import numpy as np                     # noqa: E402
import pandas as pd                    # noqa: E402

import a1_design as design             # noqa: E402
import a1_opd as opd                   # noqa: E402
import run_a1                          # noqa: E402
import run_stage3 as s3                # noqa: E402


class TestProjection(unittest.TestCase):

    def test_equals_brute_force_least_squares(self):
        rng = np.random.default_rng(0)
        t, flen, centre = 2000, 48, 24
        s = rng.standard_normal(t)
        y = np.convolve(s, rng.standard_normal(7), mode="same") + 0.1 * rng.standard_normal(t)
        out = opd.project(s, y, centre=centre, flen=flen)
        ref, est = np.concatenate([s, np.zeros(centre)]), np.concatenate([np.zeros(centre), y])
        n = ref.size + flen - 1
        a = np.zeros((n, flen))
        for tau in range(flen):
            a[tau:tau + ref.size, tau] = ref
        coef = np.linalg.lstsq(a, np.concatenate([est, np.zeros(flen - 1)]), rcond=None)[0]
        self.assertLess(np.max(np.abs(out["component"] - (a @ coef)[centre:centre + t])), 1e-10)
        self.assertLess(out["normal_equation_residual"], 1e-10)

    def test_centred_span_recovers_a_two_sided_filter(self):
        rng = np.random.default_rng(1)
        h = np.zeros(11)
        h[[2, 5, 8]] = [0.3, 1.0, -0.4]
        x = rng.standard_normal(30000)
        out = opd.project(x, np.convolve(x, h, mode="same"))
        np.testing.assert_allclose(out["taps"][[opd.CENTRE - 3, opd.CENTRE, opd.CENTRE + 3]], [0.3, 1.0, -0.4], atol=1e-4)

    def test_residual_orthogonal_to_the_reference_span(self):
        rng = np.random.default_rng(2)
        x = rng.standard_normal(8000)
        y = np.tanh(3 * np.convolve(x, [0.5, 1.0, 0.2], mode="same"))       # nonlinear: a residual must remain
        out = opd.project(x, y)
        self.assertGreater(opd.nmse_db(y, out["component"]), -40.0)

    def test_output_length_and_dtype(self):
        x = np.random.default_rng(3).standard_normal(5000)
        out = opd.project(x, 0.5 * x)
        self.assertEqual(out["component"].shape, (5000,))
        self.assertLess(opd.nmse_db(0.5 * x, out["component"]), -100)


class TestOutcomeRule(unittest.TestCase):

    @staticmethod
    def cells(r8w, l8w, r8v, l8v):
        return {"whisper": {"R8": r8w, "L8": (l8w, 0, 0)}, "wav2vec2": {"R8": r8v, "L8": (l8v, 0, 0)}}

    def test_classes(self):
        self.assertEqual(design.a1_outcome(self.cells((0.6, 0.3, 0.9), 0.2, (2.0, 1.5, 2.5), 1.4)), "ROBUST_RESIDUAL")
        self.assertEqual(design.a1_outcome(self.cells((0.6, 0.3, 0.9), 0.2, (1.5, 1.0, 2.0), 2.0)),
                         "RESIDUAL_PERSISTS_BUT_ATTRIBUTION_SHIFTS")
        self.assertEqual(design.a1_outcome(self.cells((0.6, 0.3, 0.9), 0.2, (0.2, -0.1, 0.5), 3.0)), "MIXED")
        self.assertEqual(design.a1_outcome(self.cells((0.1, -0.1, 0.3), 0.7, (0.2, -0.1, 0.5), 3.0)),
                         "LINEAR_EXPLANATION_DOMINATES")

    def test_precedence_linear_most_in_both(self):
        # residual detectable in both, but the linear surrogate absorbs most of the penalty in both
        self.assertEqual(design.a1_outcome(self.cells((0.3, 0.1, 0.5), 0.5, (1.0, 0.5, 1.5), 2.5)),
                         "LINEAR_EXPLANATION_DOMINATES")

    def test_missing_bound_is_not_persistence(self):
        self.assertEqual(design.a1_outcome(self.cells((0.6, float("nan"), 0.9), 0.2, (2.0, 1.5, 2.5), 1.4)), "MIXED")


class TestSelection(unittest.TestCase):

    def test_sealed_disjoint_balanced(self):
        sel = s3.read_sealed(design.SELECTION, "selection_sha256")
        self.assertEqual(sel, {**sel, **s3.native(design.draw_signal_sets())})
        cal = set(sel["calibration"]["speakers_female"] + sel["calibration"]["speakers_male"])
        val = set(sel["validation"]["speakers_female"] + sel["validation"]["speakers_male"])
        used = set(sel["excluded"]["stage2b_filter_validation"]) | set(sel["excluded"]["r1_r2_signal_validation"])
        self.assertEqual((len(cal), len(val)), (40, 40))
        self.assertFalse(cal & val or cal & used or val & used)


class TestPlanAndGuards(unittest.TestCase):

    def test_plan_rendering(self):
        if not design.SPEC_JSON.exists():
            self.skipTest("plan not frozen yet")
        spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")
        self.assertEqual(design.PLAN_MD.read_text(), design.render(spec))

    def test_evaluation_needs_the_commit(self):
        committed = design.upgrade.git("ls-files", "--error-unmatch", str(design.CODE_FREEZE)).returncode == 0
        if committed:
            self.skipTest("the A1 plan and code freeze are committed")
        with self.assertRaises(Exception):
            design.require_code_freeze(committed=True)


def synthetic_metrics(extra: dict, speakers: int = 6, per: int = 4, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for k, subset in enumerate(["test-clean", "test-other"]):
        for s in range(speakers):
            spk = 1000 * (k + 1) + s
            for u in range(per):
                n = int(rng.integers(10, 40))
                for model in design.MODELS:
                    base = int(rng.poisson(1.5))
                    for c in design.CONDITIONS:
                        e = base + int(rng.poisson(extra.get(c, 0.0)))
                        rows.append({"set": "synthetic", "utterance": f"{spk}-1-{u:04d}", "subset": subset,
                                     "speaker_id": spk, "condition": c, "model": model, "n_words": n, "n_chars": 5 * n,
                                     "hits": n - e, "substitutions": e, "deletions": 0, "insertions": 0,
                                     "word_errors": e, "wer": e / n, "char_errors": 2 * e, "cer": 2 * e / (5 * n),
                                     "hypothesis_normalised": ""})
    return pd.DataFrame(rows)


class TestStatistics(unittest.TestCase):

    def test_identities(self):
        table = run_a1.analyse_table(synthetic_metrics({"LP": 0.3, "OPUS": 1.5, "LIN8": 0.8}), design.CONDITIONS, n_boot=200)
        for m in design.MODELS:
            for scope in ["pooled", "test-clean", "test-other"]:
                get = lambda q, kind="micro": run_a1.ustats.lookup(table, m, q, kind, scope)[0]
                self.assertAlmostEqual(get("L8") + get("R8"), get("T"), places=10)
                self.assertAlmostEqual(get("delta_L"), -get("delta_R"), places=10)
                self.assertAlmostEqual(get("delta_L"), get("L8") - get("B_primary"), places=10)
                self.assertAlmostEqual(get("S8", "ratio"), get("L8") / get("T"), places=10)


if __name__ == "__main__":
    unittest.main()
