"""
R1-R3 runtime (RS1 code): reference decoder, Stage 2B fit, gates, estimands and outcomes on
synthetic signals and synthetic edit counts only. No LibriSpeech audio, no ASR.

    python -m unittest discover -s paper/reviewer_sensitivity/tests -t paper/reviewer_sensitivity/tests -v
"""

import math
import unittest

import numpy as np
import pandas as pd
import torch

import helpers
import lowpass
import opus_direct
import reviewer_design as design
import reviewer_pipeline as rp
import reviewer_stats as rstats
import run_lowpass_validation as s2b


def pcm_signal(seconds=1.5, seed=0):
    """A speech-like 16-bit signal (exactly representable, as LibriSpeech FLAC)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rp.SAMPLE_RATE)
    t = np.arange(n) / rp.SAMPLE_RATE
    x = 0.2 * np.sin(2 * np.pi * 180 * t) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t)) + 0.02 * rng.normal(size=n)
    pcm = np.clip(np.round(x * 32768), -32768, 32767) / 32768
    return torch.from_numpy(pcm.astype(np.float32)).unsqueeze(0)


class TestReferenceDecoder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.waveform = pcm_signal()
        cls.coded = rp.encode_and_decode(cls.waveform, rp.OPUS_SETTINGS, 1, True)

    def test_packets_and_lengths(self):
        info = self.coded["refdec_info"]
        self.assertTrue(info["packets_identical"])
        self.assertEqual(info["samples_per_packet"], str(design.SAMPLES_PER_PACKET_48K))
        self.assertEqual(info["output_gain"], 0)
        self.assertTrue(info["pre_skip_is_3x_lookahead"])
        self.assertEqual(info["length_48k"], 3 * self.waveform.shape[-1])
        self.assertEqual(info["length_48k"], info["ffmpeg_length_48k"])
        self.assertEqual(self.coded["refdec"].shape, self.waveform.shape)
        self.assertEqual(self.coded["ffmpeg"].shape, self.waveform.shape)
        self.assertTrue(torch.isfinite(self.coded["refdec"]).all())
        self.assertEqual(self.coded["refdec"].dtype, torch.float32)

    def test_ffmpeg_path_is_codec_round_trip(self):
        frozen, _ = rp.audio.codec_round_trip(self.waveform, rp.OPUS_SETTINGS)
        self.assertTrue(torch.equal(frozen, self.coded["ffmpeg"]))

    def test_decoders_agree_closely(self):
        difference = rp.decoder_difference(self.coded["ffmpeg"], self.coded["refdec"])
        self.assertTrue(difference["same_length"])
        self.assertLessEqual(abs(difference["lag_samples"]), 2)

    def test_forced_wideband_packets(self):
        coded = rp.encode_and_decode(self.waveform, design.WB8_SETTINGS, design.WB_CONFIGURATION, False)
        self.assertEqual(coded["readback_mismatches"], [])
        self.assertEqual(coded["summary"]["expected_config"], design.WB_CONFIGURATION)
        self.assertGreaterEqual(coded["summary"]["share_expected_config"], 0.0)


class TestFit(unittest.TestCase):

    def test_fit_follows_the_stage2b_procedure(self):
        waveforms = [pcm_signal(1.0, seed) for seed in range(2)]
        reference = np.minimum(0.0, -np.maximum(0.0, s2b.FREQS - 2500.0) / 60.0)
        taps, fit = rp.fit_stage2b_filter(reference, waveforms)
        self.assertEqual(len(taps), s2b.NUM_TAPS)
        self.assertTrue(np.array_equal(taps, taps[::-1]))
        target, edge = s2b.build_target(reference)
        self.assertEqual(fit["edge_hz"], edge)
        self.assertTrue(np.array_equal(fit["target_db"], target))
        self.assertEqual(len(fit["iterations"]), s2b.N_CORRECTION_ITERATIONS + 1)


def transfer(h1, cbw=4000.0, hf=-25.0, coherence=1.0):
    return {"h1_rel_db": np.asarray(h1, dtype=float), "coherent_bandwidth_hz": cbw, "coherent_hf_power_db": hf,
            "coherence": np.full(len(s2b.FREQS), coherence)}


class TestGates(unittest.TestCase):

    def test_reuse_gate(self):
        curve = np.minimum(0.0, -np.maximum(0.0, s2b.FREQS - 3000.0) / 40.0)
        same = rp.reuse_gate(transfer(curve), transfer(curve), transfer(curve))
        self.assertTrue(same["pass"])
        shifted = rp.reuse_gate(transfer(curve), transfer(curve - 2.0), transfer(curve))
        self.assertFalse(shifted["pass"])                       # RMS 2 dB > 1.5 dB and worse than FFmpeg + 0.5
        self.assertFalse(shifted["criteria"]["d_no_worse_than_ffmpeg_fit"]["pass"])
        wide = rp.reuse_gate(transfer(curve, cbw=4000.0), transfer(curve, cbw=4100.0), transfer(curve))
        self.assertFalse(wide["criteria"]["a_coherent_bandwidth"]["pass"])

    def test_surr8_gates(self):
        opus = np.minimum(0.0, -np.maximum(0.0, s2b.FREQS - 2000.0) / 50.0)
        target, _ = s2b.build_target(opus)
        taps = np.ones(11)
        good = rp.surr8_gates(transfer(target), transfer(opus), pd.Series([0, 0]), taps, 2000.0)
        self.assertTrue(good["gates"]["R2-V6"]["pass"])
        self.assertTrue(good["gates"]["R2-V3"]["pass"])
        self.assertTrue(good["gates"]["R2-V1"]["pass"])
        lagged = rp.surr8_gates(transfer(target), transfer(opus), pd.Series([0, 1]), taps, 2000.0)
        self.assertFalse(lagged["gates"]["R2-V1"]["pass"])
        low_coherence = rp.surr8_gates(transfer(target, coherence=0.98), transfer(opus), pd.Series([0]), taps, 2000.0)
        self.assertFalse(low_coherence["gates"]["R2-V2"]["pass"])


class TestStats(unittest.TestCase):

    def test_confirmation_quantities_and_decisions(self):
        conditions = ["REF", "LP", "OPUS", "SILK", design.OPUS_REFDEC, design.SILK_REFDEC, design.SURR8]
        extra = {"LP": 0.3, "OPUS": 2.0, "SILK": 0.3, design.OPUS_REFDEC: 2.0, design.SILK_REFDEC: 0.3,
                 design.SURR8: 0.5}
        metrics = helpers.synthetic_metrics(conditions, extra, seed=1)
        table = rstats.analyse(metrics, conditions, rstats.confirmation_quantities, lp_dec="LP", r1=True, r2=True,
                               n_boot=200)
        p1 = rstats.lookup(table, "whisper", "P1")
        t = rstats.lookup(table, "whisper", "T_opus_minus_lp")
        d1 = rstats.lookup(table, "whisper", "D1")
        o = rstats.lookup(table, "whisper", "opus_refdec_minus_opus")
        self.assertAlmostEqual(d1[0], p1[0] - t[0], places=10)
        self.assertAlmostEqual(d1[0], o[0], places=10)          # LP_DEC = LP
        anchors = {m: {"T_star": {"estimate": 1.0}} for m in design.MODELS}
        r1 = rstats.r1_decision(table, anchors, "LP")
        self.assertIn(r1["outcome"], design.OUTCOMES)
        r2 = rstats.r2_decision(table, anchors)
        cell = r2["cells"]["whisper"]
        self.assertLessEqual(cell["sensitivity_range_point"][0], cell["sensitivity_range_point"][1])
        s1 = rstats.lookup(table, "whisper", "s1_primary_share", "ratio")
        b = rstats.lookup(table, "whisper", "B_lp_minus_ref")
        total = rstats.lookup(table, "whisper", "total_opus_minus_ref")
        self.assertAlmostEqual(s1[0], b[0] / total[0], places=10)

    def test_sweep_quantities_and_outcomes(self):
        metrics = helpers.synthetic_metrics([design.NB8, design.WB8], {design.NB8: 0.2, design.WB8: 2.0}, seed=2)
        table = rstats.analyse(metrics, [design.NB8, design.WB8], rstats.sweep_quantities, n_boot=200)
        decision = rstats.r3_decision(table)
        self.assertIsNone(decision["outcome"])
        for model, cell in decision["cells"].items():
            self.assertEqual(cell["outcome"], design.r3_outcome(cell["W"][1], cell["W"][2]))
        self.assertEqual(decision["cells"]["wav2vec2"]["outcome"], "WB_WORSE")

    def test_ratio_convention(self):
        values = rstats.ratio(np.array([1.0, 1.0, 1.0]), np.array([2.0, 0.0, -1.0]))
        self.assertEqual(values[0], 0.5)
        self.assertTrue(math.isnan(values[1]) and math.isnan(values[2]))


if __name__ == "__main__":
    unittest.main()
