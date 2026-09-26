"""
Stage 1 equivalence tests for the paper pipeline.

Run from the repository root with the project interpreter:
    /home/mei/elec5305-project/.venv/bin/python -m unittest discover -s paper/tests -v

1. Source: every function in paper/common.py is AST-identical to its frozen
   original in src/, so the copies cannot drift silently.
2. Settings: every frozen setting in paper/common.py has the frozen value.
3. Isolation: no frozen script that runs an experiment at import time is
   imported by the paper code.
4. Frozen trees: git reports no change under src/ or results/.
5. Reproduction: the comparison of run_reproduce.compare_all(), recomputed
   from the rows saved in results_paper/reproduce/, has no failed check and
   covers the full Stage 1 scope. Skipped if run_reproduce.py has not been
   run.
"""

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PAPER_DIR = REPO_ROOT / "paper"
SRC_DIR = REPO_ROOT / "src"
COMMON_PATH = PAPER_DIR / "common.py"
REPRODUCE_DIR = REPO_ROOT / "results_paper" / "reproduce"

sys.path.insert(0, str(PAPER_DIR))

# (function in paper/common.py, frozen file that holds the original)
COPIED_FUNCTIONS = [
    ("load_dataset", "representation_analysis.py"),
    ("select_indices", "representation_analysis.py"),
    ("decode", "run_all_experiments.py"),
    ("recognise", "run_all_experiments.py"),
    ("process_audio", "run_all_experiments.py"),
    ("compress_audio", "signal_distortion_analysis.py"),
    ("align_waveforms", "signal_distortion_analysis.py"),
    ("magnitude_spectrogram", "signal_distortion_analysis.py"),
    ("spectral_distortion", "signal_distortion_analysis.py"),
    ("bandwidth_measures", "signal_distortion_analysis.py"),
    ("extract_hidden_states", "representation_analysis.py"),
    ("representation_similarity", "representation_analysis.py"),
    ("standardise", "representation_analysis.py"),
    ("configuration_name", "opus_mode_check.py"),
    ("ogg_audio_packets", "opus_mode_check.py"),
]

# (setting in paper/common.py, frozen files that define it)
FROZEN_SETTINGS = {
    "DATA_ROOT": ["run_all_experiments.py", "signal_distortion_analysis.py",
                  "representation_analysis.py"],
    "NUM_SAMPLES": ["run_all_experiments.py", "signal_distortion_analysis.py",
                    "representation_analysis.py", "opus_mode_check.py"],
    "RANDOM_SEED": ["run_all_experiments.py", "signal_distortion_analysis.py",
                    "representation_analysis.py", "opus_mode_check.py"],
    "DATASET_NAMES": ["signal_distortion_analysis.py", "representation_analysis.py"],
    "N_FFT": ["signal_distortion_analysis.py"],
    "HOP_LENGTH": ["signal_distortion_analysis.py"],
    "WIN_LENGTH": ["signal_distortion_analysis.py"],
    "LOG_EPS": ["signal_distortion_analysis.py"],
    "DYNAMIC_RANGE_DB": ["signal_distortion_analysis.py"],
    "BANDWIDTH_DROP_DB": ["signal_distortion_analysis.py"],
    "HF_BAND_HZ": ["signal_distortion_analysis.py"],
    "MAX_SHIFT_SAMPLES": ["signal_distortion_analysis.py"],
    "NUM_TRANSFORMER_LAYERS": ["representation_analysis.py"],
    "LAYER_NAMES": ["representation_analysis.py"],
}

# Frozen scripts whose module body runs an experiment
RUNS_ON_IMPORT = [
    "analyse_results", "baseline_asr", "bootstrap_analysis",
    "comparison_analysis", "experiment_mp3", "representation_analysis",
    "run_all_experiments", "signal_distortion_analysis",
]


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text())


def function_node(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise KeyError(name)


def assignment_value(module: ast.Module, name: str) -> ast.expr:
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return node.value
    raise KeyError(name)


def normalised_signature(node: ast.FunctionDef, renames: dict[str, str]) -> str:
    """AST dump without docstring and type annotations, with names renamed."""
    node = ast.parse(ast.unparse(node)).body[0]
    if ast.get_docstring(node) is not None:
        node.body = node.body[1:]
    node.returns = None
    for child in ast.walk(node):
        if isinstance(child, ast.arg):
            child.annotation = None
            child.arg = renames.get(child.arg, child.arg)
        elif isinstance(child, ast.Name):
            child.id = renames.get(child.id, child.id)
    return ast.dump(node)


class TestSourceEquivalence(unittest.TestCase):

    def test_copied_functions_are_identical(self):
        common = parse(COMMON_PATH)
        for name, frozen_file in COPIED_FUNCTIONS:
            with self.subTest(function=name, frozen=frozen_file):
                frozen = parse(SRC_DIR / frozen_file)
                self.assertEqual(
                    ast.dump(function_node(common, name)),
                    ast.dump(function_node(frozen, name)),
                )

    def test_representation_codec_path_is_the_signal_codec_path(self):
        """
        representation_analysis.py has its own compress_audio(); it differs
        from the copied signal version only by docstring, type annotations
        and parameter names (input_waveform, input_sample_rate), so one copy
        serves both frozen paths.
        """
        renames = {"input_waveform": "waveform", "input_sample_rate": "sample_rate"}
        self.assertEqual(
            normalised_signature(function_node(
                parse(SRC_DIR / "representation_analysis.py"), "compress_audio"),
                renames),
            normalised_signature(function_node(
                parse(SRC_DIR / "signal_distortion_analysis.py"), "compress_audio"),
                {}),
        )

    def test_settings_have_frozen_values(self):
        common = parse(COMMON_PATH)
        for name, frozen_files in FROZEN_SETTINGS.items():
            for frozen_file in frozen_files:
                with self.subTest(setting=name, frozen=frozen_file):
                    self.assertEqual(
                        ast.dump(assignment_value(common, name)),
                        ast.dump(assignment_value(parse(SRC_DIR / frozen_file), name)),
                    )

    def test_frozen_standardisation_path(self):
        import common
        self.assertEqual(
            Path(common.FROZEN_STANDARDISATION_PATH),
            Path("results") / "representation_standardisation.pt",
        )


class TestIsolation(unittest.TestCase):

    def test_no_frozen_experiment_script_is_imported(self):
        import run_reproduce  # noqa: F401  (imports common as well)
        imported = [name for name in RUNS_ON_IMPORT if name in sys.modules]
        self.assertEqual(imported, [])

    def test_frozen_trees_unchanged_in_git(self):
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "src", "results"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        ).stdout
        self.assertEqual(status, "")


@unittest.skipUnless(
    (REPRODUCE_DIR / "new_asr_rows.csv").exists(),
    "run paper/run_reproduce.py first",
)
class TestReproduction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.chdir(REPO_ROOT)
        import run_reproduce
        cls.run_reproduce = run_reproduce
        cls.report = run_reproduce.compare_all(REPRODUCE_DIR)

    def test_no_failed_check(self):
        failures = self.report[self.report["status"] == "FAIL"]
        self.assertTrue(
            failures.empty,
            "\n" + failures[["check", "subset", "condition", "field", "note"]].to_string(),
        )

    def test_scope(self):
        asr = self.run_reproduce.read_csv(REPRODUCE_DIR / "new_asr_rows.csv")
        self.assertEqual(sorted(asr["dataset"].unique()), ["test-clean", "test-other"])
        for subset, group in asr.groupby("dataset"):
            with self.subTest(subset=subset):
                self.assertEqual(group["dataset_index"].nunique(), 50)
                self.assertEqual(
                    sorted(set(zip(group["codec"], group["bitrate"]))),
                    [("opus", "12k"), ("opus", "8k"), ("wav", "uncompressed")],
                )

    def test_every_stored_layer_compared(self):
        compared = set(
            self.report.loc[self.report["check"] == "representation", "field"]
        )
        self.assertTrue(set(self.run_reproduce.DRIFT_FIELDS) <= compared)

    def test_packet_modes_compared_against_frozen_table(self):
        rows = self.report[
            (self.report["check"] == "packets")
            & (self.report["subset"] == "test-clean")
        ]
        self.assertEqual(len(rows), 2)
        self.assertTrue((rows["comparison"] == "exact").all())

    def test_saved_report_matches_recomputed(self):
        saved = self.run_reproduce.read_csv(REPRODUCE_DIR / "equivalence_report.csv")
        self.assertEqual(saved["status"].tolist(), self.report["status"].tolist())


if __name__ == "__main__":
    unittest.main()
