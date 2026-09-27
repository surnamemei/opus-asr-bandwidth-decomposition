"""B1 tests: one encoder parameter, the frozen outcome rule, the plan, the guards and the statistics (no ASR)."""

import dataclasses
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FI = HERE.parent
ROOT = FI.parents[1]
for p in [str(FI), str(ROOT / "paper" / "reviewer_sensitivity"), str(ROOT / "paper" / "taslp_upgrade"),
          str(ROOT / "paper")]:
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(ROOT)

import numpy as np                     # noqa: E402
import pandas as pd                    # noqa: E402

import b1_design as design             # noqa: E402
import opus_direct                     # noqa: E402
import run_b1                          # noqa: E402
import run_stage3 as s3                # noqa: E402
import stage3_audio as audio           # noqa: E402


class TestContrast(unittest.TestCase):

    def test_exactly_one_encoder_parameter(self):
        self.assertEqual(design.settings_difference(), {"application": ["audio", "voip"]})
        self.assertIs(design.AUDIO8_SETTINGS, audio.CODEC_SETTINGS["OPUS"])
        v = dataclasses.asdict(design.VOIP8_SETTINGS)
        self.assertEqual((v["signal"], v["bandwidth"], v["bitrate_bps"], v["frame_ms"], v["vbr"], v["vbr_constraint"],
                          v["complexity"], v["inband_fec"], v["dtx"]), ("auto", "NB", 8000, 20.0, True, False, 10, False, False))

    def test_voip_encode_reads_back_voip(self):
        # int16-representable synthetic noise (the encoder accepts exactly representable 16-bit PCM only)
        x = (np.round(np.clip(0.1 * np.random.default_rng(0).standard_normal(16000), -1, 1) * 32768) / 32768).astype(np.float32)
        import torch
        c = run_b1.coded(torch.from_numpy(x).unsqueeze(0), design.VOIP8)
        self.assertEqual(c["result"].queried["application"], opus_direct.APPLICATIONS["voip"])
        self.assertEqual(c["readback_mismatches"], [])
        self.assertEqual(c["packets"]["bandwidths"], "NB")
        self.assertEqual(c["packets"]["frame_ms"], "20.0")


class TestOutcomeRule(unittest.TestCase):

    def test_classes(self):
        self.assertEqual(design.b1_outcome(-0.5, -0.1), "VOIP_LOWER_PENALTY")
        self.assertEqual(design.b1_outcome(0.1, 0.5), "VOIP_HIGHER_PENALTY")
        self.assertEqual(design.b1_outcome(-0.1, 0.2), "NO_CLEAR_APPLICATION_DIFFERENCE")
        self.assertEqual(design.b1_outcome(0.0, 0.2), "NO_CLEAR_APPLICATION_DIFFERENCE")
        self.assertEqual(design.b1_outcome(float("nan"), -0.1), "NO_CLEAR_APPLICATION_DIFFERENCE")


class TestPlanAndGuards(unittest.TestCase):

    def test_plan_rendering(self):
        if not design.SPEC_JSON.exists():
            self.skipTest("plan not frozen yet")
        spec = s3.read_sealed(design.SPEC_JSON, "spec_sha256")
        self.assertEqual(design.PLAN_MD.read_text(), design.render(spec))

    def test_evaluation_needs_the_commit(self):
        committed = design.upgrade.git("ls-files", "--error-unmatch", str(design.CODE_FREEZE)).returncode == 0
        if committed:
            self.skipTest("the B1 plan and code freeze are committed")
        with self.assertRaises(Exception):
            design.require_code_freeze(committed=True)


def synthetic_metrics(extra: dict, speakers: int = 6, per: int = 4, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for k, subset in enumerate(["test-clean", "test-other"]):
        for s in range(speakers):
            spk = 1000 * (k + 1) + s
            for u in range(per):
                n = int(rng.integers(10, 40))
                for model in design.MODELS:
                    base = int(rng.poisson(1.5))
                    for c in design.CONDITIONS:
                        e = base + int(rng.poisson(extra.get(c, 0.0)))
                        rows.append({"set": "synthetic", "utterance": f"{spk}-1-{u:04d}", "subset": subset,
                                     "speaker_id": spk, "condition": c, "model": model, "n_words": n, "n_chars": 5 * n,
                                     "hits": n - e, "substitutions": e, "deletions": 0, "insertions": 0,
                                     "word_errors": e, "wer": e / n, "char_errors": 2 * e, "cer": 2 * e / (5 * n),
                                     "hypothesis_normalised": ""})
    return pd.DataFrame(rows)


class TestStatistics(unittest.TestCase):

    def test_identities(self):
        table = run_b1.analyse_table(synthetic_metrics({design.AUDIO8: 1.0, design.VOIP8: 1.5}), design.CONDITIONS,
                                     n_boot=200)
        for m in design.MODELS:
            for scope in ["pooled", "test-clean", "test-other"]:
                get = lambda q: run_b1.ustats.lookup(table, m, q, "micro", scope)[0]
                self.assertAlmostEqual(get("V") - get("A"), get("D_app"), places=10)


if __name__ == "__main__":
    unittest.main()
