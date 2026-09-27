"""
The frozen R1-R3 plan (revision 2): the interpretation rules (synthetic intervals only) and,
once sealed, the signal-validation selection, the R2 planning diagnosis and the specification
against the files on disk. Reads sealed JSON/CSV files, SPEAKERS.TXT and file names only;
no audio, no ASR.

    python -m unittest discover -s paper/reviewer_sensitivity/tests -t paper/reviewer_sensitivity/tests -v
"""

import math
import unittest

import helpers  # noqa: F401
import reviewer_design as design
import run_lowpass_confirmation as s2c
import run_lowpass_validation as s2b
import run_stage3 as s3
import upgrade_stats

NAN = float("nan")
T_STAR = 1.0                            # margin 0.25


def outcome(analysis, primary, change):
    p, c, _ = design.RULE_QUANTITIES[analysis]
    record = design.rule(analysis, {p: primary, c: change}, T_STAR)
    return record["outcome"], record["qualifier"]


class TestRules(unittest.TestCase):

    def test_r1(self):
        self.assertEqual(outcome("R1", (0.3, 0.9), (-0.2, 0.1)), ("SUPPORT", None))
        self.assertEqual(outcome("R1", (0.1, 0.5), (-0.6, -0.3)), ("WEAKEN", "reduction shown"))
        self.assertEqual(outcome("R1", (-0.1, 0.5), (-0.1, 0.1)), ("WEAKEN", "not established"))
        self.assertEqual(outcome("R1", (0.3, 0.9), (0.1, 0.4)), ("SUPPORT", None))   # the change adds errors

    def test_r2(self):
        self.assertEqual(outcome("R2", (0.2, 0.8), (0.0, 0.2)), ("SUPPORT", None))
        self.assertEqual(outcome("R2", (0.2, 0.8), (0.3, 0.6)), ("WEAKEN", "reduction shown"))
        self.assertEqual(outcome("R2", (0.2, 0.8), (0.1, 0.4)), ("WEAKEN", "not established"))
        self.assertEqual(outcome("R2", (-0.1, 0.8), (0.0, 0.1)), ("WEAKEN", "not established"))

    def test_margin_is_strict(self):
        self.assertEqual(outcome("R1", (0.3, 0.9), (-0.25, 0.1))[0], "WEAKEN")
        self.assertEqual(outcome("R2", (0.3, 0.9), (0.0, 0.25))[0], "WEAKEN")
        self.assertEqual(outcome("R1", (0.0, 0.9), (-0.1, 0.1))[0], "WEAKEN")      # P_lo must exceed 0

    def test_nan_never_supports(self):
        for analysis in design.RULE_QUANTITIES:
            self.assertEqual(outcome(analysis, (NAN, 1.0), (0.0, 0.0))[0], "WEAKEN")
            self.assertEqual(outcome(analysis, (0.5, 1.0), (NAN, 0.0)), ("WEAKEN", "not established"))
            self.assertEqual(outcome(analysis, (0.5, 1.0), (0.0, NAN)), ("WEAKEN", "not established"))

    def test_margin_scales_with_t_star(self):
        record = design.rule("R2", {"P2": (0.5, 1.0), "Delta2": (0.3, 0.45)}, 2.0)
        self.assertEqual(record["outcome"], "SUPPORT")
        self.assertTrue(math.isclose(record["margin_pp"], 0.5))

    def test_combine(self):
        support, weaken = {"outcome": "SUPPORT"}, {"outcome": "WEAKEN"}
        self.assertEqual(design.combine({"whisper": support, "wav2vec2": support}), "SUPPORT")
        self.assertEqual(design.combine({"whisper": support, "wav2vec2": weaken}), "WEAKEN")
        with self.assertRaises(ValueError):
            design.combine({"whisper": support})

    def test_r3_outcome(self):
        self.assertEqual(design.r3_outcome(-0.8, -0.1), "WB_BETTER")
        self.assertEqual(design.r3_outcome(0.1, 0.8), "WB_WORSE")
        self.assertEqual(design.r3_outcome(-0.2, 0.3), "NO_CLEAR_DIFFERENCE")
        self.assertEqual(design.r3_outcome(-0.5, 0.0), "NO_CLEAR_DIFFERENCE")     # a bound at 0 is not clear
        self.assertEqual(design.r3_outcome(NAN, NAN), "NO_CLEAR_DIFFERENCE")
        self.assertEqual(set(design.R3_OUTCOMES), {"WB_BETTER", "NO_CLEAR_DIFFERENCE", "WB_WORSE"})
        self.assertNotIn("R3", design.RULE_QUANTITIES)                              # R3 has no SUPPORT/WEAKEN


class TestDesignConstants(unittest.TestCase):

    def test_wb8_differs_from_nb8_only_in_bandwidth(self):
        table = design.settings_table()
        diff = sorted(k for k in table[design.NB8] if table[design.NB8][k] != table[design.WB8][k])
        self.assertEqual(diff, ["bandwidth"])
        self.assertEqual((table[design.NB8]["bandwidth"], table[design.WB8]["bandwidth"]), ("NB", "WB"))

    def test_r2_tolerances_are_stage2b_values(self):
        for name, t in design.r2_tolerances().items():
            key = design.R2_TOLERANCE_SOURCES[name]
            value = s2b.TOLERANCES[key[0]][key[1]] if isinstance(key, tuple) else s2b.TOLERANCES[key]
            self.assertEqual(t["value"], value, name)

    def test_r1_reuse_gate_uses_stage2b_constants(self):
        eq = design.r1_reuse_criteria()
        self.assertEqual(eq["coherent_bandwidth_max_hz"], s2b.TOLERANCES["g4_coherent_bw_vs_reference_max_hz"])
        self.assertEqual(eq["coherent_hf_power_max_db"], s2b.TOLERANCES["g5_coherent_hf_vs_reference_max_db"])
        self.assertEqual(eq["rms_max_db"], s2b.TOLERANCES["g6_h1_rms_max_db"])
        self.assertEqual(eq["rms_margin_over_ffmpeg_db"], s2b.PASSBAND_DEVIATION_DB)

    def test_margin_and_seeds_match_earlier_stages(self):
        self.assertEqual(design.MATERIALITY_FRACTION, upgrade_stats.A_GO_FRACTION)
        self.assertEqual(design.CONFIRMATION_SEED, upgrade_stats.LEVEL_SEED)
        self.assertEqual(design.SWEEP_SEED, upgrade_stats.SWEEP_SEED)
        self.assertNotIn(design.SV_SEED, (53051, 53052, 53053, 53054, s2c.SEED))


@unittest.skipUnless(design.SV_SELECTION.exists(), "run reviewer_design.py select first")
class TestSignalValidationSelection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.selection = s3.read_sealed(design.SV_SELECTION, "selection_sha256")

    def test_reproduces_from_its_rule(self):
        drawn = design.draw_signal_validation()
        self.assertEqual({k: self.selection[k] for k in drawn}, drawn)

    def test_speakers(self):
        female, male = self.selection["speakers_female"], self.selection["speakers_male"]
        self.assertEqual((len(female), len(male)), (design.SV_SPEAKERS_PER_SEX, design.SV_SPEAKERS_PER_SEX))
        fv = s3.read_sealed(design.FV_SPEC, "spec_sha256")["confirmation_set"]
        self.assertFalse(set(female + male) & set(fv["speakers_female"] + fv["speakers_male"]))
        self.assertEqual(sorted(u["speaker_id"] for u in self.selection["utterances"]), sorted(female + male))

    def test_files_exist(self):
        root = s2c.subset_dir(design.SV_SUBSET)
        for u in self.selection["utterances"]:
            self.assertTrue((root / u["path"]).exists(), u["path"])


@unittest.skipUnless(design.R2_DIAGNOSIS.exists(), "run reviewer_design.py diagnose-r2 first")
class TestPlanningDiagnosis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.diagnosis = s3.read_sealed(design.R2_DIAGNOSIS, "diagnosis_sha256")

    def test_reproduces_from_frozen_curves(self):
        body = s3.native(design.diagnosis_body())
        self.assertEqual({k: self.diagnosis[k] for k in body}, body)

    def test_probe_is_reproduced(self):
        probe = self.diagnosis["probe"]
        self.assertEqual(probe["reproduced_here_hz"], design.PLANNING_PROBE_EDGE_HZ)
        self.assertEqual(self.diagnosis["edges_hz_by_deviation_db"]["train-clean-100"]["opus_8k_nb"]["0.5"],
                         design.PLANNING_PROBE_EDGE_HZ)


@unittest.skipUnless(design.SPEC_JSON.exists(), "run reviewer_design.py freeze-spec first")
class TestFrozenPlan(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")

    def test_plan_is_the_rendering_of_the_sealed_spec(self):
        self.assertEqual(design.PLAN_MD.read_text(), design.render(self.spec))

    def test_inputs_unchanged(self):
        design.inputs_unchanged(self.spec)

    def test_literature_note_is_bound(self):
        self.assertEqual(s3.file_sha256(design.LITERATURE_NOTE), self.spec["literature_note"]["sha256"])

    def test_supersedes_the_draft(self):
        self.assertEqual(self.spec["provenance"]["superseded_draft_spec_sha256"],
                         design.SUPERSEDED_DRAFT["spec_sha256"])
        self.assertNotEqual(self.spec["spec_sha256"], design.SUPERSEDED_DRAFT["spec_sha256"])

    def test_margins(self):
        for a in self.spec["anchors"].values():
            margin = design.MATERIALITY_FRACTION * a["T_star"]["estimate"]
            self.assertTrue(math.isclose(a["margin_pp"], margin))
            self.assertTrue(math.isclose(a["R1_D1_lower_must_exceed"], -margin))
            self.assertTrue(math.isclose(a["R2_Delta2_upper_must_be_below"], margin))

    def test_design_file_unchanged_since_freeze(self):
        path = str(design.REVIEW / "reviewer_design.py")
        self.assertEqual(s3.file_sha256(design.REVIEW / "reviewer_design.py"),
                         self.spec["code_sha256_at_design_freeze"][path])

    def test_no_evaluation_output_before_code_freeze(self):
        if not design.CODE_FREEZE.exists():
            for path in design.EVALUATION_OUTPUTS:
                self.assertFalse(path.exists(), str(path))


if __name__ == "__main__":
    unittest.main()
