"""
Sealed amendments to the TASLP-upgrade plan: integrity, the superseded text, the plan
sections left unchanged and the reclassified U1 check (sealed JSON and Markdown only).

    python -m unittest discover -s paper/taslp_upgrade/tests -v
"""

import unittest
from pathlib import Path

import helpers  # noqa: F401
import run_stage3 as s3
import upgrade_amendments as amendments
import upgrade_design as design


@unittest.skipUnless(amendments.paths(), "no amendment is sealed")
class TestAmendments(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")
        cls.records = amendments.load_all()       # seals, amended plan and unchanged sections verified
        cls.first = cls.records[0]

    def test_markdown_rendered_from_record(self):
        for path, record in zip(amendments.paths(), self.records):
            self.assertEqual(path.with_suffix(".md").read_text(), amendments.render(record))

    def test_plan_files_not_edited(self):
        self.assertEqual(self.first["amends"]["spec_sha256"], self.spec["spec_sha256"])
        self.assertEqual(self.first["amends"]["plan_markdown_sha256"], s3.file_sha256(design.PLAN_MD))
        for path in [design.SPEC_JSON, design.PLAN_MD]:
            design.tracked_and_clean(path)

    def test_01_supersedes_only_the_wav2vec2_expectation(self):
        amends = self.first["amends"]
        self.assertEqual(amends["item"], "A.analytic_expectations[0]")
        self.assertEqual(amends["original_text"], self.spec["A"]["analytic_expectations"][0])
        self.assertTrue(amends["original_text"].startswith("wav2vec2-base-960h"))
        self.assertIn("by construction", amends["original_text"])
        sections = amendments.plan_sections(self.spec)
        self.assertEqual(set(self.first["unchanged"]["plan_sections_sha256"]), set(sections) - {amends["item"]})

    def test_01_no_estimand_gate_threshold_condition_selection_or_rule_changed(self):
        sections = amendments.plan_sections(self.spec)
        unchanged = self.first["unchanged"]["plan_sections_sha256"]
        for key in ["common_pipeline", "policies", "run_order",
                    "A.data", "A.conditions", "A.encoder_settings_opus", "A.derivation", "A.pre_asr_gates",
                    "A.estimands", "A.bootstrap", "A.anchors", "A.rules", "A.manuscript_consequences",
                    "B.data", "B.conditions", "B.encoder_settings", "B.technical_calibration",
                    "B.pre_asr_validation", "B.estimands", "B.bootstrap", "B.anchors", "B.rules",
                    "B.manuscript_consequences"]:
            self.assertEqual(unchanged[key], amendments.section_sha256(sections[key]), key)
        self.assertTrue(self.first["unchanged"]["code_unchanged_since_design_freeze"])

    def test_01_statement(self):
        text = " ".join(self.first["statement"])
        for phrase in ["by construction, was incorrect", "approximate, not exact, level invariance",
                       "nonzero epsilon", "persists in sufficiently low-variance channels",
                       "scientifically informative", "interpreted normally", "predetermined sanity-null",
                       "changes no estimand, gate, decision threshold, condition, dataset selection or "
                       "analysis rule",
                       "reclassified from a freeze gate to a descriptive calibration finding"]:
            self.assertIn(phrase, text)

    def test_01_reclassifies_one_check(self):
        self.assertEqual(set(amendments.reclassified_checks()), {"A_wav2vec2_scale_invariance"})
        item = self.first["reclassified_checks"][0]
        self.assertEqual((item["from"], item["to"], item["run1_value"]),
                         ("freeze gate", "descriptive calibration finding", False))

    def test_01_run1_fail_report_preserved(self):
        evidence = self.first["evidence"]["u1_checks_run1"]
        path = Path(evidence["path"])
        run1 = s3.read_sealed(path, "report_sha256")
        self.assertEqual(run1["report_sha256"], evidence["report_sha256"])
        self.assertEqual((run1["verdict"], run1["failed"]), ("FAIL", ["A_wav2vec2_scale_invariance"]))
        for name, digest in run1["files"].items():
            self.assertEqual(s3.file_sha256(path.parent / name), digest, name)


if __name__ == "__main__":
    unittest.main()
