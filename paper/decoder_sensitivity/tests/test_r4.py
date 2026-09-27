"""R4 tests: the frozen rule, the sealed plan, the decoder convention and the statistics (no LibriSpeech, no ASR)."""

import math
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
R4_DIR = HERE.parent
for path in (str(R4_DIR), str(R4_DIR.parent / "reviewer_sensitivity"), str(R4_DIR.parent / "taslp_upgrade"),
             str(R4_DIR.parent)):
    if path not in sys.path:
        sys.path.insert(0, path)
os.chdir(R4_DIR.parents[1])             # plan paths are relative to the repository root

import numpy as np                      # noqa: E402
import pandas as pd                     # noqa: E402
import torch                            # noqa: E402

import r4_design as design              # noqa: E402
import run_r4                           # noqa: E402
import run_lowpass_validation as s2b    # noqa: E402
import run_stage3 as s3                 # noqa: E402


class TestOutcomeRule(unittest.TestCase):

    def test_three_outcomes(self):
        self.assertEqual(design.r4_outcome(-0.5, -0.1), "DECODER_LOWER_PENALTY")
        self.assertEqual(design.r4_outcome(0.1, 0.5), "DECODER_HIGHER_PENALTY")
        self.assertEqual(design.r4_outcome(-0.1, 0.1), "NO_CLEAR_DECODER_DIFFERENCE")

    def test_boundaries_and_missing_bounds(self):
        self.assertEqual(design.r4_outcome(-0.2, 0.0), "NO_CLEAR_DECODER_DIFFERENCE")   # touching zero
        self.assertEqual(design.r4_outcome(0.0, 0.2), "NO_CLEAR_DECODER_DIFFERENCE")
        self.assertEqual(design.r4_outcome(float("nan"), -0.1), "NO_CLEAR_DECODER_DIFFERENCE")
        self.assertEqual(design.r4_outcome(0.1, float("nan")), "NO_CLEAR_DECODER_DIFFERENCE")

    def test_no_threshold_parameter(self):
        self.assertEqual(design.r4_outcome(-1e-9, -1e-12), "DECODER_LOWER_PENALTY")   # no minimum effect


class TestPlan(unittest.TestCase):

    def test_seal_and_rendering(self):
        spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")
        self.assertEqual(design.PLAN_MD.read_text(), design.render(spec))
        self.assertEqual(spec["analysis"], "R4")
        self.assertEqual(set(spec["stage3_anchors"]), set(design.MODELS))

    def test_frozen_constants_match_plan(self):
        spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")
        self.assertIn(f"{design.N_BOOT:,} replicates, seed {design.SEED}", spec["bootstrap"])
        self.assertEqual(spec["provenance"]["stage3_opus_encoder_settings"]["bitrate_bps"], 8000)
        self.assertIn(f"frame_size={design.DECODER_MAX_FRAME}, decode_fec=0", spec["decoder"]["decode_call"])

    def test_freeze_spec_refuses_twice(self):
        with self.assertRaises(RuntimeError):
            design.freeze_spec()

    def test_evaluation_needs_the_committed_plan(self):
        committed = design.upgrade.git("ls-files", "--error-unmatch", str(design.SPEC_JSON)).returncode == 0
        if committed and design.CODE_FREEZE.exists():
            self.skipTest("the plan and code freeze are committed; evaluation may have been approved")
        with self.assertRaises(RuntimeError):
            design.require_code_freeze(committed=True)


def synthetic_speech(seconds: float = 1.3, seed: int = 0) -> torch.Tensor:
    """Band-limited noise on the 16-bit grid (the encoder checks that float input is exact 16-bit PCM)."""
    rng = np.random.default_rng(seed)
    x = np.convolve(rng.standard_normal(int(seconds * 16000)), np.hanning(9), mode="same") * 0.05
    return torch.from_numpy(np.round(np.clip(x, -1, 1) * 32767) / 32768).to(torch.float32).unsqueeze(0)


class TestDecoderConvention(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.waveform = synthetic_speech()
        cls.d = run_r4.decode(cls.waveform)

    def test_output_length_convention(self):
        d, n = self.d, self.waveform.shape[-1]
        info = d["info"]
        self.assertEqual(info["output_gain"], 0)
        self.assertEqual(info["pre_skip"], 3 * d["result"].lookahead_samples)
        self.assertEqual(d["pcm48"].size, info["final_granule"] - info["pre_skip"])
        self.assertEqual(d["pcm48"].size, 3 * n)
        self.assertEqual(d["ffmpeg_length_48k"], d["pcm48"].size)
        self.assertEqual(d["libopus"].shape[-1], n)
        self.assertEqual(info["samples_per_packet"], [design.SAMPLES_PER_PACKET_48K])
        self.assertTrue(info["packets"] == d["result"].packets)
        self.assertTrue(np.isfinite(d["pcm48"]).all() and torch.isfinite(d["libopus"]).all())

    def test_decoding_is_deterministic(self):
        again = run_r4.decode(self.waveform)
        self.assertTrue(np.array_equal(again["pcm48"], self.d["pcm48"]))
        self.assertTrue(torch.equal(again["libopus"], self.d["libopus"]))

    def test_libopus_only_is_the_same_audio(self):
        audio, info = run_r4.libopus_only(self.waveform)
        self.assertTrue(torch.equal(audio, self.d["libopus"]))
        self.assertEqual(len(info["ogg_sha256"]), 64)


class TestDiagnostics(unittest.TestCase):

    def test_one_sample_alignment(self):
        rng = np.random.default_rng(1)
        a = rng.standard_normal(1000)
        b = np.concatenate([[0.0], a[:-1]])                   # libopus one sample later than FFmpeg
        out = run_r4.decoder_difference(torch.from_numpy(a).unsqueeze(0), torch.from_numpy(b).unsqueeze(0))
        self.assertTrue(math.isinf(out["snr_one_sample_db"]))
        self.assertEqual(out["one_sample_shift"], 1)
        self.assertFalse(out["bit_identical"])
        same = run_r4.decoder_difference(torch.from_numpy(a).unsqueeze(0), torch.from_numpy(a).unsqueeze(0))
        self.assertTrue(same["bit_identical"] and math.isinf(same["snr_unaligned_db"]))

    def test_band_power_of_identical_signals_is_zero_db(self):
        acc = s2b.TransferAccumulator()
        x = synthetic_speech(seed=2)
        acc.add(x, x)
        self.assertAlmostEqual(run_r4.band_power_db(acc, design.POWER_BAND_HZ), 0.0, places=9)


def gate_rows(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame([{
        "utterance": f"u{i}", "g1_ogg_identical": True, "packets_identical": True, "samples_per_packet": "960",
        "output_gain": 0, "pre_skip_is_3x_lookahead": True, "length_48k": 3 * 100, "length_48k_convention": 3 * 100,
        "num_samples_ref": 100, "ffmpeg_length_48k": 3 * 100, "length_equals_ref": True,
        "nonfinite_48k": 0, "nonfinite_16k": 0} for i in range(n)])


class TestGates(unittest.TestCase):

    def test_all_pass(self):
        g = run_r4.gate_results(gate_rows(), 3, [])
        self.assertTrue(all(g[k]["pass"] for k in ["G1", "G2", "G3", "G4"]))

    def test_each_failure_is_caught(self):
        for field, value, gate in [("g1_ogg_identical", False, "G1"), ("packets_identical", False, "G2"),
                                   ("output_gain", 256, "G3"), ("samples_per_packet", "1920", "G3"),
                                   ("length_48k_convention", 299, "G3"), ("length_equals_ref", False, "G3"),
                                   ("nonfinite_48k", 1, "G4")]:
            rows = gate_rows()
            rows.loc[1, field] = value
            self.assertFalse(run_r4.gate_results(rows, 3, [])[gate]["pass"], field)
        self.assertFalse(run_r4.gate_results(gate_rows(), 3, [{"utterance": "u9", "error": "x"}])["G2"]["pass"])
        self.assertFalse(run_r4.gate_results(gate_rows(2), 3, [])["G1"]["pass"])        # a missing utterance


def synthetic_metrics(extra: dict, seed: int = 0, speakers: int = 6, per_speaker: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for k, subset in enumerate(["test-clean", "test-other"]):
        for s in range(speakers):
            speaker = 1000 * (k + 1) + s
            for u in range(per_speaker):
                n_words = int(rng.integers(10, 40))
                for model in design.MODELS:
                    base = int(rng.poisson(1.5))
                    for condition in design.CONDITIONS:
                        e = base + int(rng.poisson(extra.get(condition, 0.0)))
                        rows.append({"set": "synthetic", "utterance": f"{speaker}-1-{u:04d}", "subset": subset,
                                     "speaker_id": speaker, "condition": condition, "model": model,
                                     "n_words": n_words, "n_chars": 5 * n_words, "hits": n_words - e,
                                     "substitutions": e, "deletions": 0, "insertions": 0, "word_errors": e,
                                     "wer": e / n_words, "char_errors": 2 * e, "cer": 2 * e / (5 * n_words),
                                     "hypothesis_normalised": ""})
    return pd.DataFrame(rows)


class TestStatistics(unittest.TestCase):

    def test_d_is_the_difference_of_the_totals(self):
        table = run_r4.analyse_table(synthetic_metrics({design.OPUS_FFMPEG: 1.0, design.OPUS_LIBOPUS: 1.0}),
                                     design.CONDITIONS, n_boot=200)
        for model in design.MODELS:
            for scope in design.SCOPES:
                t_ff = run_r4.ustats.lookup(table, model, "T_ffmpeg", "micro", scope)[0]
                t_lib = run_r4.ustats.lookup(table, model, "T_libopus", "micro", scope)[0]
                d = run_r4.ustats.lookup(table, model, "D", "micro", scope)[0]
                self.assertAlmostEqual(d, t_lib - t_ff, places=10)

    def test_a_large_decoder_penalty_is_detected(self):
        table = run_r4.analyse_table(synthetic_metrics({design.OPUS_FFMPEG: 0.5, design.OPUS_LIBOPUS: 4.0}),
                                     design.CONDITIONS, n_boot=500)
        for model in design.MODELS:
            _, lo, hi = run_r4.ustats.lookup(table, model, "D", "micro", "pooled")
            self.assertEqual(design.r4_outcome(lo, hi), "DECODER_HIGHER_PENALTY")

    def test_anchor_check_on_stage3_reproduces(self):
        """G9's machinery on the sealed Stage 3 metrics, with the frozen seed and replicate count."""
        spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")
        table = run_r4.analyse_table(run_r4.stage3_metrics(), [design.REF, design.OPUS_FFMPEG])
        check = run_r4.anchor_check(table, spec["stage3_anchors"])
        self.assertTrue(check["pass"], check["max_abs_difference_pp"])


if __name__ == "__main__":
    unittest.main()
