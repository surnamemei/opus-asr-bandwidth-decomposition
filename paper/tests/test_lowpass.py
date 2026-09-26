"""
Unit tests for paper/lowpass.py and the frozen Stage 2B filter. Synthetic
signals only; no LibriSpeech data is used.

Run from the repository root:
    /home/mei/elec5305-project/.venv/bin/python -m unittest discover -s paper/tests -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "paper"))
os.chdir(REPO_ROOT)

import lowpass  # noqa: E402
import run_lowpass_validation as stage2b  # noqa: E402


FS = 16000
FREQS = np.linspace(0, FS / 2, 257)


def brick_target(cutoff_hz: float = 4000.0) -> np.ndarray:
    """Test target: 0 dB below the cutoff, -80 dB from 200 Hz above it."""
    return np.interp(FREQS, [0, cutoff_hz - 200, cutoff_hz + 200, FS / 2],
                     [0.0, 0.0, -80.0, -80.0])


def tone(freq_hz: float, seconds: float = 2.0) -> torch.Tensor:
    t = np.arange(int(seconds * FS)) / FS
    return torch.from_numpy(0.5 * np.sin(2 * np.pi * freq_hz * t)).float().unsqueeze(0)


class TestDesign(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.taps = lowpass.design_linear_phase_fir(FREQS, brick_target(), FS, 1023, 8.0, 16384)

    def test_odd_symmetric_unit_dc(self):
        self.assertEqual(len(self.taps) % 2, 1)
        self.assertTrue(np.array_equal(self.taps, self.taps[::-1]))
        self.assertAlmostEqual(float(self.taps.sum()), 1.0, places=12)

    def test_even_length_rejected(self):
        with self.assertRaises(ValueError):
            lowpass.design_linear_phase_fir(FREQS, brick_target(), FS, 1022, 8.0, 16384)

    def test_response_matches_fft_of_taps(self):
        size = 8192
        spectrum = np.fft.rfft(self.taps, size)
        grid = np.linspace(0, FS / 2, size // 2 + 1)
        expected = 20 * np.log10(np.maximum(np.abs(spectrum), 1e-300))
        measured = lowpass.frequency_response_db(self.taps, grid[::64], FS)
        passband = grid[::64] < 3500
        np.testing.assert_allclose(measured[passband], expected[::64][passband], atol=1e-9)

    def test_passband_and_stopband(self):
        response = lowpass.frequency_response_db(self.taps, np.array([1000.0, 3000.0, 5000.0, 7000.0]), FS)
        self.assertLess(np.max(np.abs(response[:2])), 0.01)
        self.assertLess(np.max(response[2:]), -60.0)


class TestApply(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.taps = lowpass.design_linear_phase_fir(FREQS, brick_target(), FS, 1023, 8.0, 16384)

    def test_length_dtype_and_determinism(self):
        x = tone(1000.0, 1.337)
        y = lowpass.apply_zero_phase(x, self.taps)
        self.assertEqual(y.shape, x.shape)
        self.assertEqual(y.dtype, x.dtype)
        self.assertTrue(torch.equal(y, lowpass.apply_zero_phase(x, self.taps)))

    def test_impulse_is_not_shifted(self):
        x = torch.zeros(1, 8001)
        x[0, 4000] = 1.0
        y = lowpass.apply_zero_phase(x.double(), self.taps)[0].numpy()
        self.assertEqual(int(np.argmax(y)), 4000)
        # zero phase: response is symmetric about the impulse
        np.testing.assert_allclose(y[4000 - 511:4000], y[4001:4000 + 512][::-1], atol=1e-15)

    def test_passband_tone_unchanged_and_in_phase(self):
        x = tone(1000.0)
        y = lowpass.apply_zero_phase(x, self.taps)
        middle = slice(2000, x.shape[-1] - 2000)
        np.testing.assert_allclose(y[0, middle].numpy(), x[0, middle].numpy(), atol=1e-4)

    def test_stopband_tone_removed(self):
        y = lowpass.apply_zero_phase(tone(6000.0), self.taps)
        middle = slice(2000, 30000)
        self.assertLess(float(y[0, middle].abs().max()), 0.5 * 10 ** (-60 / 20))

    def test_asymmetric_taps_rejected(self):
        taps = self.taps.copy()
        taps[0] += 1e-9
        with self.assertRaises(ValueError):
            lowpass.apply_zero_phase(tone(1000.0), taps)


class TestFilterFile(unittest.TestCase):

    def test_round_trip_and_tamper_detection(self):
        taps = lowpass.design_linear_phase_fir(FREQS, brick_target(), FS, 511, 8.0, 8192)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "filter.json"
            digest = lowpass.save_filter(path, taps, {"note": "test"})
            loaded, record = lowpass.load_filter(path)
            self.assertTrue(np.array_equal(loaded, taps))
            self.assertEqual(record["taps_sha256"], digest)

            record["taps"][10] += 1e-12
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):
                lowpass.load_filter(path)


@unittest.skipUnless(stage2b.FILTER_PATH.exists(), "run run_lowpass_validation.py calibrate first")
class TestFrozenFilter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.taps, cls.record = lowpass.load_filter(stage2b.FILTER_PATH)

    def test_tolerances_unchanged_since_calibration(self):
        self.assertEqual(self.record["metadata"]["tolerances_sha256"],
                         stage2b.tolerances_sha256())

    def test_design_parameters_match_code(self):
        design = self.record["metadata"]["design"]
        self.assertEqual(design["num_taps"], stage2b.NUM_TAPS)
        self.assertEqual(design["kaiser_beta"], stage2b.KAISER_BETA)
        self.assertEqual(self.record["metadata"]["calibration_subset"], "dev-clean")

    def test_zero_phase_and_band_limits(self):
        self.assertTrue(np.array_equal(self.taps, self.taps[::-1]))
        response = lowpass.frequency_response_db(
            self.taps, np.array([500.0, 1000.0, 2000.0, 4500.0, 6000.0]), FS)
        self.assertLess(np.max(np.abs(response[:3])), 0.1)
        self.assertLess(np.max(response[3:]), -40.0)


if __name__ == "__main__":
    unittest.main()
