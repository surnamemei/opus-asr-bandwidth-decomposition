"""
Integrity of the frozen TASLP-upgrade plan: provenance record, sweep selection, sealed
specification, and the absence of any upgrade decoding before the code freeze.
Reads sealed JSON/CSV files and LibriSpeech file names only.

    python -m unittest discover -s paper/taslp_upgrade/tests -v
"""

import json
import math
import unittest
from dataclasses import asdict
from pathlib import Path

import pandas as pd

import helpers  # noqa: F401
import run_stage3 as s3
import stage3_audio as audio
import upgrade_design as design
import upgrade_pipeline as pipe
import upgrade_stats as ustats


class TestStage3Unchanged(unittest.TestCase):

    def test_stage3_integrity(self):
        integrity = design.stage3_integrity()
        self.assertEqual(integrity["stage3_decision"], "GO")
        self.assertEqual(integrity["frozen_lp_taps_sha256"],
                         "583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16")


@unittest.skipUnless(design.USED.exists(), "derive provenance/used_test_utterances.json first")
class TestUsedRecord(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.record = design.used_record()

    def test_counts(self):
        self.assertEqual(self.record["counts"], {"prior_study": 1000, "stage3_confirmation": 2174,
                                                 "other_development_outputs": 2, "all_used": 3176})

    def test_stage3_confirmation_excludes_prior_study(self):
        confirmation = {u["utterance"] for u in s3.load_selection("confirmation")["utterances"]}
        self.assertFalse(confirmation & set(self.record["prior_study"]))
        self.assertTrue(confirmation <= set(self.record["all_used_test_utterances"]))


@unittest.skipUnless(design.SELECTION.exists(), "run upgrade_design.py select first")
class TestSweepSelection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.selection = s3.read_sealed(design.SELECTION, "selection_sha256")
        cls.utterances = cls.selection["utterances"]
        cls.chosen = {u["utterance"] for u in cls.utterances}

    def test_fresh_utterances_only(self):
        used = set(design.used_record()["all_used_test_utterances"])
        confirmation = {u["utterance"] for u in s3.load_selection("confirmation")["utterances"]}
        self.assertFalse(self.chosen & used)
        self.assertFalse(self.chosen & confirmation)
        self.assertEqual(len(self.chosen), len(self.utterances))

    def test_fresh_utterance_not_fresh_speaker_is_declared(self):
        self.assertIn("FRESH-UTTERANCE, NOT FRESH-SPEAKER", self.selection["rules"]["holdout_type"])
        confirmation_speakers = {u["speaker_id"] for u in s3.load_selection("confirmation")["utterances"]}
        speakers = {u["speaker_id"] for u in self.utterances}
        self.assertTrue(speakers <= confirmation_speakers)
        self.assertEqual(self.selection["speakers_also_in_stage3_confirmation"], len(speakers))

    def test_eligibility_and_cap(self):
        per_speaker = pd.Series([u["speaker_id"] for u in self.utterances]).value_counts()
        self.assertLessEqual(int(per_speaker.max()), design.SWEEP_MAX_PER_SPEAKER)
        for u in self.utterances:
            self.assertIn(u["subset"], design.SWEEP_SUBSETS)
            self.assertLessEqual(u["duration_s"], 30.0)
            self.assertTrue(u["reference"].strip())
            self.assertTrue((s3.LIBRI / u["path"]).exists())

    def test_seed_and_rule(self):
        self.assertEqual(self.selection["seed"], design.SWEEP_SEED)
        self.assertIn(f"random.Random({design.SWEEP_SEED})", self.selection["rules"]["rule"])


@unittest.skipUnless(design.SPEC_JSON.exists(), "run upgrade_design.py freeze-spec first")
class TestFrozenSpec(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")

    def test_hashes_link_plan_selection_and_provenance(self):
        self.assertEqual(self.spec["B"]["data"]["sha256"],
                         s3.read_sealed(design.SELECTION, "selection_sha256")["selection_sha256"])
        self.assertEqual(self.spec["provenance"]["used_test_utterances_sha256"],
                         design.used_record()["record_sha256"])
        self.assertEqual(self.spec["A"]["data"]["sha256"],
                         s3.load_selection("confirmation")["selection_sha256"])

    def test_labels(self):
        self.assertIn("NOT A SECOND CONFIRMATORY TEST", self.spec["A"]["label"])
        self.assertIn("FRESH UTTERANCES, NOT FRESH SPEAKERS", self.spec["B"]["label"])
        self.assertTrue(self.spec["status"].startswith("PLANNED, NOT RUN"))

    def test_constants_agree_with_code(self):
        A, B = self.spec["A"], self.spec["B"]
        self.assertEqual(A["bootstrap"], {**A["bootstrap"], "seed": ustats.LEVEL_SEED, "replicates": ustats.N_BOOT})
        self.assertEqual(B["bootstrap"], {**B["bootstrap"], "seed": ustats.SWEEP_SEED, "replicates": ustats.N_BOOT})
        self.assertEqual([c["name"] for c in B["conditions"]], ustats.SWEEP_CONDITIONS)
        self.assertEqual(B["encoder_settings"], {k: asdict(v) for k, v in pipe.SWEEP_SETTINGS.items()})
        self.assertEqual(A["encoder_settings_opus"], asdict(audio.CODEC_SETTINGS["OPUS"]))

    def test_anchors_recomputed_from_frozen_stage3(self):
        anchors = design.stage3_anchors()
        for m in ustats.MODELS:
            t, u = anchors[m]["T_star"]["estimate"], anchors[m]["U_star"]["estimate"]
            self.assertAlmostEqual(self.spec["B"]["anchors"][m]["S_star"], (u - t) / math.log2(5), places=12)
            self.assertAlmostEqual(self.spec["A"]["anchors"][m]["T_star"]["estimate"], t, places=12)
            self.assertAlmostEqual(self.spec["A"]["anchors"][m]["GO_threshold_K_lower"], -0.25 * t, places=12)
            self.assertAlmostEqual(self.spec["A"]["anchors"][m]["FALSIFY_threshold_K_upper"], -0.5 * t, places=12)
        self.assertAlmostEqual(anchors["whisper"]["T_star"]["estimate"], 0.686367, places=6)
        self.assertAlmostEqual(anchors["wav2vec2"]["T_star"]["estimate"], 2.070618, places=6)

    def test_plan_markdown_is_rendered_from_spec(self):
        self.assertEqual(design.PLAN_MD.read_text(), design.render(self.spec))


@unittest.skipIf(design.CODE_FREEZE.exists(), "the code freeze exists; evaluation steps may have run")
class TestNothingDecoded(unittest.TestCase):
    """Before the code freeze no evaluation output may exist and no evaluation command may start."""

    def test_no_evaluation_outputs(self):
        for sub in ["sweep", "level"]:
            self.assertFalse((design.RESULTS / sub).exists(), sub)

    def test_evaluation_commands_refuse(self):
        import run_bitrate_sweep as sweep
        import run_level_sensitivity as level
        for command in [sweep.validate, sweep.run, sweep.analyse, level.regenerate, level.run, level.analyse]:
            with self.assertRaises((RuntimeError, FileNotFoundError)):
                command()
        for sub in ["sweep", "level"]:
            self.assertFalse((design.RESULTS / sub).exists(), sub)

    def test_code_freeze_required(self):
        with self.assertRaises((RuntimeError, FileNotFoundError)):
            design.require_code_freeze()


if __name__ == "__main__":
    unittest.main()
