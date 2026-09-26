"""
U1 supplementary pre-run checks: the helpers (synthetic data only; no codec, no ASR)
and, once sealed, the freeze manifest against the files on disk.

    python -m unittest discover -s paper/taslp_upgrade/tests -v
"""

import types
import unittest
from pathlib import Path

import numpy as np
import torch

import helpers  # noqa: F401
import pre_run_checks as checks
import run_stage3 as s3
import upgrade_design as design
import upgrade_pipeline as pipe


def signal(n=4000, seed=0):
    x = np.random.default_rng(seed).normal(0.0, 0.1, size=(1, n))
    return torch.from_numpy(x.astype(np.float32))


class TestTransformExact(unittest.TestCase):

    def setUp(self):
        self.opus = signal(seed=1)
        self.matched, self.gain = pipe.level_match(self.opus, 1.07 * signal(seed=1))

    def test_level_match_output_is_exact(self):
        self.assertTrue(checks.transform_exact(self.opus, self.matched, self.gain))

    def test_detects_clipping_shift_trim_and_other_gain(self):
        self.assertFalse(checks.transform_exact(self.opus, self.matched.clamp(-0.1, 0.1), self.gain))
        self.assertFalse(checks.transform_exact(self.opus, torch.roll(self.matched, 1, dims=-1), self.gain))
        self.assertFalse(checks.transform_exact(self.opus, self.matched[:, :-1], self.gain))
        self.assertFalse(checks.transform_exact(self.opus, self.matched, self.gain * (1 + 1e-6)))


class TestReadback(unittest.TestCase):

    BASE = {"bitrate": 8000, "bandwidth": 1101, "signal": 3001, "lookahead": 104}

    def test_only_bitrate(self):
        queried = {f"SILK{b}": {**self.BASE, "bitrate": 1000 * b} for b in (8, 12, 16)}
        self.assertEqual(checks.readback_differences(queried), ["bitrate"])

    def test_other_difference_or_missing_control(self):
        queried = {"SILK8": self.BASE, "SILK12": {**self.BASE, "bitrate": 12000, "signal": -1000}}
        self.assertEqual(checks.readback_differences(queried), ["bitrate", "signal"])
        missing = {k: v for k, v in self.BASE.items() if k != "lookahead"}
        self.assertEqual(checks.readback_differences({"SILK8": self.BASE, "SILK12": missing}), ["lookahead"])


class TestRecorded(unittest.TestCase):

    def test_records_and_restores(self):
        module = types.SimpleNamespace(f=lambda x, y=1: x + y)
        original, log = module.f, []
        with checks.recorded(module, "f", log, lambda a, k, r: {"args": list(a), "kwargs": sorted(k), "result": r}):
            self.assertEqual(module.f(2, y=3), 5)
        self.assertIs(module.f, original)
        self.assertEqual(log, [{"args": [2], "kwargs": ["y"], "result": 5}])

    def test_restores_after_error(self):
        module = types.SimpleNamespace(f=lambda: 0)
        original = module.f
        with self.assertRaises(ValueError):
            with checks.recorded(module, "f", [], lambda a, k, r: None):
                raise ValueError
        self.assertIs(module.f, original)

    def test_expected_calls_follow_the_settings(self):
        for settings in pipe.SWEEP_SETTINGS.values():
            calls = checks.expected_calls(settings)
            self.assertEqual(calls["encode"][0]["bitrate_bps"], settings.bitrate_bps)
            self.assertEqual(calls["decode"], [{"decoded_rate": 48000}])
            self.assertEqual(calls["resample"], [{"orig_freq": 48000, "new_freq": 16000, "keyword_arguments": []}])


class TestFreezeGates(unittest.TestCase):

    CHECKS = {"A1_calibration": True, "B_V1_calibration": True, "A_wav2vec2_scale_invariance": False}
    AMENDED = {"A_wav2vec2_scale_invariance": {"amendment": "01", "amendment_sha256": "0" * 64,
                                               "classification": "descriptive calibration finding"}}

    def test_without_amendment_every_check_gates(self):
        status = checks.freeze_gates(self.CHECKS, {})
        self.assertEqual(status["gates"], list(self.CHECKS))
        self.assertEqual(status["failed_gates"], ["A_wav2vec2_scale_invariance"])
        self.assertEqual(status["descriptive"], {})

    def test_reclassified_failure_does_not_gate_but_is_reported(self):
        status = checks.freeze_gates(self.CHECKS, self.AMENDED)
        self.assertEqual(status["failed_gates"], [])
        self.assertNotIn("A_wav2vec2_scale_invariance", status["gates"])
        self.assertIs(status["descriptive"]["A_wav2vec2_scale_invariance"]["value"], False)

    def test_any_other_failure_still_gates(self):
        status = checks.freeze_gates({**self.CHECKS, "B_V1_calibration": False}, self.AMENDED)
        self.assertEqual(status["failed_gates"], ["B_V1_calibration"])

    def test_reclassified_check_must_exist(self):
        status = checks.freeze_gates({"A1_calibration": True}, self.AMENDED)
        self.assertEqual(status["reclassified_but_missing"], ["A_wav2vec2_scale_invariance"])


class TestSame(unittest.TestCase):

    def test_numbers_and_strings(self):
        self.assertTrue(checks.same(309, 309.0))
        self.assertTrue(checks.same(np.float64(0.1), 0.1))
        self.assertTrue(checks.same(float("nan"), np.nan))
        self.assertTrue(checks.same(True, 1.0))
        self.assertFalse(checks.same(0.1, 0.1 + 1e-16))
        self.assertTrue(checks.same("abc", "abc"))
        self.assertFalse(checks.same("abc", None))


@unittest.skipUnless(checks.FREEZE_MANIFEST.exists(), "the freeze manifest is sealed after freeze-code")
class TestFreezeManifest(unittest.TestCase):
    """After the code freeze, every hashed file must be unchanged until the evaluation runs."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = s3.read_sealed(checks.FREEZE_MANIFEST, "manifest_sha256")

    def test_files_unchanged(self):
        changed = [path for group in self.manifest["files"].values() for path, digest in group.items()
                   if s3.file_sha256(Path(path)) != digest]
        self.assertEqual(changed, [])

    def test_bound_to_code_freeze_and_plan(self):
        spec, freeze = design.require_code_freeze()
        self.assertEqual(self.manifest["code_freeze_sha256"], freeze["freeze_sha256"])
        self.assertEqual(self.manifest["spec_sha256"], spec["spec_sha256"])
        self.assertEqual(self.manifest["evaluation_outputs_present"], {"sweep": False, "level": False})


if __name__ == "__main__":
    unittest.main()
