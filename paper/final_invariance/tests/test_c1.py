"""C1 tests: the sealed audit record, its table, the identities and the pre-declared classification."""

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

import pandas as pd                    # noqa: E402

import c1_metric_audit as c1           # noqa: E402
import run_stage3 as s3                # noqa: E402


@unittest.skipUnless(c1.OUT_JSON.exists(), "C1 has not been run")
class TestC1Record(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.record = s3.read_sealed(c1.OUT_JSON, "record_sha256")
        cls.table = pd.read_csv(c1.OUT_CSV)

    def test_table_matches_the_sealed_record(self):
        self.assertEqual(s3.file_sha256(c1.OUT_CSV), self.record["table_sha256"])

    def test_primary_estimator_reproduces_stage3(self):
        self.assertLess(self.record["stage3_reproduction_max_abs_difference_pp"], 1e-9)

    def test_point_identities(self):
        t = self.table.set_index(["model", "scope", "metric", "quantity"])["estimate"]
        for (model, scope, metric), _ in self.table.groupby(["model", "scope", "metric"]):
            b, r, tot = (t[(model, scope, metric, q)] for q in ["B", "R", "T"])
            self.assertAlmostEqual(b + r, tot, places=9)
            self.assertAlmostEqual(t[(model, scope, metric, "R_minus_B")], r - b, places=9)
            if metric in c1.WEIGHTINGS:
                self.assertAlmostEqual(t[(model, scope, metric, "share_B_over_T")], b / tot, places=9)

    def test_classification_follows_the_declared_rule(self):
        # recomputed from the CSV (last-digit float round trip), so compare the classes, not the floats
        again = s3.native(c1.classify(self.table))
        self.assertEqual({k: v["classes"] for k, v in again.items()},
                         {k: v["classes"] for k, v in self.record["classifications"].items()})

    def test_full_bootstrap_everywhere(self):
        self.assertEqual(int(self.table["n_boot_valid"].min() >= c1.N_BOOT - 2), 1)


if __name__ == "__main__":
    unittest.main()
