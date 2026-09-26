"""
Provenance tests for the Stage 2B revised Gate 5 confirmation.

Run from the repository root:
    /home/mei/elec5305-project/.venv/bin/python -m unittest discover -s paper/tests -v
"""

import datetime
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "paper"))
os.chdir(REPO_ROOT)

import lowpass  # noqa: E402
import run_lowpass_confirmation as confirmation  # noqa: E402
import run_lowpass_validation as stage2b  # noqa: E402


class TestRevisedTolerances(unittest.TestCase):

    def test_exactly_one_tolerance_removed(self):
        original = stage2b.TOLERANCES
        revised = confirmation.REVISED_TOLERANCES
        self.assertEqual(set(original) - set(revised), {"g5_coherent_hf_vs_opus8nb_max_db"})
        self.assertEqual(set(revised) - set(original), set())
        for key, value in revised.items():
            self.assertEqual(value, original[key], key)

    def test_reference_tolerance_unchanged(self):
        self.assertEqual(confirmation.REVISED_TOLERANCES["g5_coherent_hf_vs_reference_max_db"], 3.0)

    def test_original_specification_untouched(self):
        _, record = lowpass.load_filter(stage2b.FILTER_PATH)
        self.assertEqual(record["metadata"]["tolerances_sha256"], stage2b.tolerances_sha256())
        self.assertIn("g5_coherent_hf_vs_opus8nb_max_db", stage2b.TOLERANCES)


@unittest.skipUnless(confirmation.SPEC_PATH.exists(), "run freeze first")
class TestFrozenSpec(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.spec = confirmation.read_sealed(confirmation.SPEC_PATH, "spec_sha256")

    def test_filter_hash_matches(self):
        _, record = lowpass.load_filter(stage2b.FILTER_PATH)
        self.assertEqual(record["taps_sha256"], self.spec["frozen_filter"]["taps_sha256"])

    def test_revised_tolerances_match_code(self):
        self.assertEqual(self.spec["revised_tolerances"], confirmation.REVISED_TOLERANCES)

    def test_original_outputs_unchanged(self):
        self.assertEqual(confirmation.original_snapshot(),
                         self.spec["original_specification"]["files_sha256"])

    def test_speakers_are_train_clean_100_and_disjoint_from_dev(self):
        chosen = self.spec["confirmation_set"]
        speakers = {s["id"]: s for s in confirmation.read_speakers()}
        self.assertEqual(len(chosen["speakers_female"]), 20)
        self.assertEqual(len(chosen["speakers_male"]), 20)
        for sex in ["F", "M"]:
            for speaker in chosen["speakers_female" if sex == "F" else "speakers_male"]:
                self.assertEqual(speakers[speaker]["subset"], "train-clean-100")
                self.assertEqual(speakers[speaker]["sex"], sex)
        self.assertEqual(confirmation.select_speakers(),
                         {"F": chosen["speakers_female"], "M": chosen["speakers_male"]})

    def test_spec_frozen_before_confirmation_data_downloaded(self):
        archive = Path(stage2b.common.DATA_ROOT) / "train-clean-100.tar.gz"
        if not archive.exists():
            self.skipTest("confirmation data not downloaded yet")
        created = datetime.datetime.fromisoformat(self.spec["created_utc"])
        downloaded = datetime.datetime.fromtimestamp(archive.stat().st_mtime,
                                                     datetime.timezone.utc)
        self.assertLess(created, downloaded)


@unittest.skipUnless(confirmation.SELECTION_PATH.exists(), "run select first")
class TestSelection(unittest.TestCase):

    def test_selection_sealed_under_spec(self):
        spec = confirmation.read_sealed(confirmation.SPEC_PATH, "spec_sha256")
        selection = confirmation.read_sealed(confirmation.SELECTION_PATH, "selection_sha256")
        self.assertEqual(selection["spec_sha256"], spec["spec_sha256"])
        self.assertLess(spec["created_utc"], selection["created_utc"])
        speakers = sorted(spec["confirmation_set"]["speakers_female"]
                          + spec["confirmation_set"]["speakers_male"])
        self.assertEqual([u["speaker_id"] for u in selection["utterances"]], speakers)
        for entry in selection["utterances"]:
            self.assertTrue(entry["path"].startswith(f"{entry['speaker_id']}/"))


if __name__ == "__main__":
    unittest.main()
