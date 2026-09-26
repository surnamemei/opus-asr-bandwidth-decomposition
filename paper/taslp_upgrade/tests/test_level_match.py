"""
Level matching for OPUS8_LEVEL_MATCHED (synthetic arrays only; no codec, no ASR).

    python -m unittest discover -s paper/taslp_upgrade/tests -v
"""

import unittest

import numpy as np
import torch

import helpers  # noqa: F401
import upgrade_pipeline as pipe


def tone(n=16000, amplitude=0.1, seed=0):
    rng = np.random.default_rng(seed)
    x = amplitude * np.sin(2 * np.pi * 440 * np.arange(n) / 16000) + 0.01 * rng.normal(size=n)
    return torch.from_numpy(x.astype(np.float32)).reshape(1, -1)


class TestLevelMatch(unittest.TestCase):

    def test_rms_matches_lp_and_gain_is_ratio(self):
        opus, lp = tone(amplitude=0.08, seed=1), tone(amplitude=0.1, seed=2)
        matched, gain = pipe.level_match(opus, lp)
        self.assertAlmostEqual(gain, pipe.rms(lp.numpy()) / pipe.rms(opus.numpy()), places=12)
        error_db = 20 * np.log10(pipe.rms(matched.numpy()) / pipe.rms(lp.numpy()))
        self.assertLess(abs(error_db), 1e-5)

    def test_single_scalar_float32_same_shape(self):
        opus, lp = tone(seed=3), tone(amplitude=0.2, seed=4)
        matched, gain = pipe.level_match(opus, lp)
        self.assertEqual(matched.dtype, torch.float32)
        self.assertEqual(tuple(matched.shape), tuple(opus.shape))
        expected = (gain * opus.double().numpy()).astype(np.float32)
        np.testing.assert_array_equal(matched.numpy(), expected)

    def test_no_clipping(self):
        opus = torch.full((1, 1000), 0.9, dtype=torch.float32)
        lp = torch.full((1, 1000), 1.8, dtype=torch.float32)
        matched, gain = pipe.level_match(opus, lp)
        self.assertAlmostEqual(gain, 2.0, places=6)
        self.assertGreater(float(matched.max()), 1.0)       # passed unchanged, as in Stage 3

    def test_no_realignment_or_other_change(self):
        opus = torch.zeros((1, 100), dtype=torch.float32)
        opus[0, 7] = 0.5
        matched, _ = pipe.level_match(opus, 2 * opus)
        self.assertEqual(int(torch.argmax(matched.abs())), 7)

    def test_rejects_length_mismatch_and_silence(self):
        with self.assertRaises(ValueError):
            pipe.level_match(tone(n=100), tone(n=101))
        with self.assertRaises(ValueError):
            pipe.level_match(torch.zeros((1, 100)), tone(n=100))


class TestSweepSettings(unittest.TestCase):

    def test_only_bitrate_varies(self):
        from dataclasses import asdict
        settings = {name: asdict(s) for name, s in pipe.SWEEP_SETTINGS.items()}
        self.assertEqual(list(settings), ["SILK8", "SILK12", "SILK16", "SILK24", "SILK40"])
        self.assertEqual([s["bitrate_bps"] for s in settings.values()], [8000, 12000, 16000, 24000, 40000])
        for s in settings.values():
            self.assertEqual((s["bandwidth"], s["signal"], s["application"], s["vbr"], s["vbr_constraint"],
                              s["complexity"], s["frame_ms"], s["inband_fec"], s["dtx"], s["packet_loss_perc"]),
                             ("NB", "voice", "audio", True, False, 10, 20.0, False, False, 0))

    def test_relation_to_stage3_settings(self):
        from dataclasses import asdict
        import stage3_audio as audio
        self.assertEqual(asdict(pipe.SWEEP_SETTINGS["SILK40"]), asdict(audio.CODEC_SETTINGS["SILK"]))
        opus, silk8 = asdict(audio.CODEC_SETTINGS["OPUS"]), asdict(pipe.SWEEP_SETTINGS["SILK8"])
        self.assertEqual(sorted(k for k in opus if opus[k] != silk8[k]), ["signal"])
        self.assertIs(pipe.OPUS_SETTINGS, audio.CODEC_SETTINGS["OPUS"])


if __name__ == "__main__":
    unittest.main()
