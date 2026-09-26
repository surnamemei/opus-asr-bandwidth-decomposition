"""
Tests for the Stage 3 ASR decomposition code.

Synthetic tests exercise the statistics, decision rules, audio generation and
the complete report path without any LibriSpeech decoding. Provenance tests
check the sealed selections, spec and code hashes once they exist.

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
import pandas as pd
import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "paper"))
os.chdir(REPO_ROOT)

import lowpass  # noqa: E402
import run_stage3  # noqa: E402
import stage3_audio as audio  # noqa: E402
import stage3_report as report  # noqa: E402
import stage3_stats as stats  # noqa: E402


CONDITIONS = audio.CONDITIONS
MODELS = ["whisper", "wav2vec2"]


# ==================================================
# Synthetic data
# ==================================================

def synthetic_metrics(set_name: str, residual: float, seed: int, n_speakers=(12, 10),
                      per_speaker=4) -> pd.DataFrame:
    """Edit counts with a bandwidth effect and an OPUS residual of `residual` errors/word."""
    rng = np.random.default_rng(seed)
    effects = {"REF": 0.04, "LP": 0.05, "OPUS": 0.05 + residual, "SILK": 0.05,
               "NEG_LP": 0.04, "NEG_CODEC": 0.04}
    rows = []
    speaker = 1000
    for subset, count in zip(["clean", "other"], n_speakers):
        for _ in range(count):
            speaker += 1
            for u in range(per_speaker):
                utterance = f"{speaker}-1-{u:04d}"
                n = int(rng.integers(12, 40))
                chars = 5 * n
                for model in MODELS:
                    base = rng.binomial(n, 0.03)
                    for condition in CONDITIONS:
                        extra = rng.binomial(n, effects[condition] - 0.04 + 0.001)
                        s = min(n, base + extra)
                        rows.append({
                            "set": set_name, "utterance": utterance, "subset": subset,
                            "speaker_id": speaker, "condition": condition, "model": model,
                            "n_words": n, "hits": n - s, "substitutions": s, "deletions": 0,
                            "insertions": 0, "word_errors": s, "wer": s / n, "n_chars": chars,
                            "char_errors": 2 * s, "cer": 2 * s / chars,
                            "hypothesis_normalised": "x" * (condition != "OPUS" or u > 0),
                        })
    return pd.DataFrame(rows)


def synthetic_side_tables(metrics: pd.DataFrame):
    signal, audio_rows, asr_rows, pooled = [], [], [], []
    rng = np.random.default_rng(0)
    for (set_name, utterance), group in metrics.groupby(["set", "utterance"]):
        first = group.iloc[0]
        ids = {"set": set_name, "utterance": utterance, "subset": first["subset"],
               "speaker_id": first["speaker_id"]}
        for condition in CONDITIONS:
            row = {**ids, "condition": condition}
            if condition == "REF":
                row.update({f: rng.random() for f in report.EXPLORATORY_FEATURES if f.startswith("ref_")})
            else:
                row.update({"vs_ref_lsd_0_3k_db": rng.random(), "vs_ref_length_equal": True,
                            "vs_ref_retained_bandwidth_hz": 4000.0})
            if condition in ("OPUS", "SILK"):
                row.update({f: rng.random() for f in report.EXPLORATORY_FEATURES if f.startswith("vs_lp")})
            signal.append(row)
            audio_rows.append({**ids, "condition": condition, "num_samples": 16000})
            for model in MODELS:
                asr_rows.append({**ids, "condition": condition, "model": model,
                                 "reference": "a b", "hypothesis": "a b"})
    for set_name in metrics["set"].unique():
        for a, b in audio.TRANSFER_PAIRS:
            pooled.append({"set": set_name, "reference": a, "processed": b,
                           "coherent_bandwidth_hz": 4000.0, "image_coherence_4100_4900": 0.2,
                           "total_hf_power_db": -20.0, "coherent_hf_power_db": -25.0,
                           "h1_level_db": 0.0, "mean_coherence_0_3500": 0.9})
    return (pd.DataFrame(signal), pd.DataFrame(audio_rows), pd.DataFrame(asr_rows),
            pd.DataFrame(pooled))


def synthetic_boot(residuals: dict, controls: float = 0.0, pilot_sign: float = 1.0) -> pd.DataFrame:
    """Bootstrap table with given (model, codec) -> (estimate, lo, hi) on confirmation."""
    rows = []
    for set_name in ["pilot", "confirmation"]:
        for model in MODELS:
            def add(quantity, est, lo, hi):
                rows.append({"set": set_name, "model": model, "scope": "pooled",
                             "quantity": quantity, "kind": "micro", "estimate": est,
                             "ci_lower": lo, "ci_upper": hi, "excludes_zero": lo > 0 or hi < 0})
            for codec, quantity in stats.RESIDUALS.items():
                est, lo, hi = residuals[(model, codec)]
                if set_name == "pilot":
                    est, lo, hi = pilot_sign * est, pilot_sign * est - 1, pilot_sign * est + 1
                add(quantity, est, lo, hi)
            add("delta_bw", 1.0, 0.5, 1.5)
            add("opus_minus_silk", 0.0, -0.5, 0.5)
            for control in stats.NEGATIVE_CONTROLS:
                add(control, controls, controls - 0.1, controls + 0.1)
    return pd.DataFrame(rows)


# ==================================================
# Statistics
# ==================================================

class TestStatistics(unittest.TestCase):

    def test_bootstrap_weights_resample_within_strata(self):
        strata = np.array(["a"] * 5 + ["b"] * 3)
        weights = stats.bootstrap_weights(strata, 200, np.random.default_rng(1))
        np.testing.assert_array_equal(weights[:, :5].sum(axis=1), 5)
        np.testing.assert_array_equal(weights[:, 5:].sum(axis=1), 3)

    def test_identical_conditions_give_zero_contrasts(self):
        metrics = synthetic_metrics("pilot", 0.0, seed=3)
        whisper = metrics[metrics["model"] == "whisper"]
        ref = whisper[whisper["condition"] == "REF"]
        same = pd.concat([ref.assign(condition=c) for c in CONDITIONS])
        rows = pd.DataFrame(stats.decompose(stats.PairedSet(same, CONDITIONS), CONDITIONS, n_boot=200))
        contrasts = rows[rows["kind"] == "micro"]
        contrasts = contrasts[contrasts["quantity"].isin([c[0] for c in stats.CONTRASTS])]
        self.assertTrue(np.allclose(contrasts[["estimate", "ci_lower", "ci_upper"]], 0.0))

    def test_micro_estimate_matches_total_edit_counts(self):
        metrics = synthetic_metrics("pilot", 0.05, seed=4)
        part = metrics[metrics["model"] == "wav2vec2"]
        rows = pd.DataFrame(stats.decompose(stats.PairedSet(part, CONDITIONS), CONDITIONS, n_boot=100))
        totals = part.groupby("condition")["word_errors"].sum()
        words = part[part["condition"] == "REF"]["n_words"].sum()
        expected = 100 * (totals["OPUS"] - totals["LP"]) / words
        got = rows[(rows["quantity"] == "delta_opus_residual") & (rows["kind"] == "micro")]
        self.assertAlmostEqual(float(got["estimate"].iloc[0]), expected, places=10)

    def test_unpaired_design_rejected(self):
        metrics = synthetic_metrics("pilot", 0.0, seed=5)
        part = metrics[metrics["model"] == "whisper"].iloc[1:]
        with self.assertRaises(ValueError):
            stats.PairedSet(part, CONDITIONS)


class TestDecisions(unittest.TestCase):

    def cells(self, whisper_opus, wav2vec2_opus, silk=(0.0, -0.5, 0.5)):
        return {("whisper", "OPUS"): whisper_opus, ("wav2vec2", "OPUS"): wav2vec2_opus,
                ("whisper", "SILK"): silk, ("wav2vec2", "SILK"): silk}

    def test_go(self):
        boot = synthetic_boot(self.cells((2.0, 1.0, 3.0), (1.5, 0.8, 2.2)))
        self.assertEqual(stats.confirmation_decision(boot, MODELS)["decision"], "GO")

    def test_kill(self):
        boot = synthetic_boot(self.cells((0.2, -0.3, 0.7), (0.1, -0.4, 0.6)))
        self.assertEqual(stats.confirmation_decision(boot, MODELS)["decision"], "KILL")

    def test_hold_when_recogniser_specific(self):
        boot = synthetic_boot(self.cells((2.0, 1.0, 3.0), (0.3, -0.2, 0.8)))
        self.assertEqual(stats.confirmation_decision(boot, MODELS)["decision"], "HOLD")

    def test_conditional_go_when_small(self):
        boot = synthetic_boot(self.cells((0.3, 0.1, 0.5), (0.4, 0.2, 0.6)))
        self.assertEqual(stats.confirmation_decision(boot, MODELS)["decision"], "CONDITIONAL GO")

    def test_conditional_go_when_pilot_direction_differs(self):
        boot = synthetic_boot(self.cells((2.0, 1.0, 3.0), (1.5, 0.8, 2.2)), pilot_sign=-1.0)
        self.assertEqual(stats.confirmation_decision(boot, MODELS)["decision"], "CONDITIONAL GO")

    def test_negative_control_caps_at_hold(self):
        boot = synthetic_boot(self.cells((2.0, 1.0, 3.0), (1.5, 0.8, 2.2)), controls=1.0)
        decision = stats.confirmation_decision(boot, MODELS)
        self.assertEqual(decision["decision"], "HOLD")
        self.assertTrue(decision["capped_by_negative_control"])

    def test_pilot_rule(self):
        boot = synthetic_boot(self.cells((2.0, 1.0, 3.0), (0.0, -1.0, 1.0)))
        pilot = boot.replace({"confirmation": "unused"})
        self.assertEqual(stats.pilot_decision(pilot, MODELS)["decision"], "PROCEED_TO_CONFIRMATION")
        boot = synthetic_boot(self.cells((0.0, -0.5, 0.5), (0.0, -0.5, 0.5)))
        self.assertEqual(stats.pilot_decision(boot, MODELS)["decision"], "STOP_KILL")


# ==================================================
# Audio conditions
# ==================================================

class TestAudio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(0)
        t = np.arange(32000) / 16000
        x = sum(np.sin(2 * np.pi * 150 * k * t) / k for k in range(1, 50))
        x = 0.25 * (x + 0.05 * rng.standard_normal(t.size)) / np.max(np.abs(x))
        cls.waveform = torch.from_numpy(np.round(x * 32768) / 32768).float().unsqueeze(0)
        cls.filters = audio.load_filters()
        cls.conditions = audio.generate_conditions(cls.waveform, cls.filters)

    def test_frozen_filter_hash(self):
        self.assertEqual(lowpass.taps_sha256(self.filters["LP"]), audio.FROZEN_LP_SHA256)

    def test_negative_control_filter(self):
        response = lowpass.frequency_response_db(
            self.filters["NEG_LP"], np.array([500.0, 3000.0, 6500.0, 7800.0]), 16000)
        self.assertLess(np.max(np.abs(response[:3])), 0.05)
        self.assertLess(response[3], -60.0)

    def test_paired_lengths_rate_dtype(self):
        for name in CONDITIONS:
            processed = self.conditions[name][0]
            self.assertEqual(processed.shape, self.waveform.shape, name)
            self.assertEqual(processed.dtype, torch.float32, name)

    def test_lp_is_frozen_filter_applied(self):
        expected = lowpass.apply_zero_phase(self.waveform, self.filters["LP"])
        self.assertTrue(torch.equal(self.conditions["LP"][0], expected))

    def test_codec_bandwidths(self):
        for name, bandwidth in [("OPUS", "NB"), ("SILK", "NB"), ("NEG_CODEC", "WB")]:
            configurations = self.conditions[name][1]["configurations"]
            self.assertEqual({c.split("-")[1] for c in configurations}, {bandwidth}, name)

    def test_audio_stats(self):
        processed, info = self.conditions["LP"]
        row = audio.audio_stats("LP", processed, self.waveform, info)
        self.assertEqual(row["lag_vs_ref_samples"], 0)
        self.assertTrue(row["length_equals_ref"])
        self.assertEqual(row["nonfinite_count"], 0)

    def test_signal_controls_cover_all_conditions(self):
        rows, pairs = audio.signal_controls(self.conditions)
        self.assertEqual([r["condition"] for r in rows], CONDITIONS)
        self.assertEqual(set(pairs), set(audio.TRANSFER_PAIRS))


# ==================================================
# Report path end to end (synthetic)
# ==================================================

class TestReportEndToEnd(unittest.TestCase):

    def test_final_analysis_runs_and_writes_all_outputs(self):
        metrics = pd.concat([synthetic_metrics("pilot", 0.06, seed=10),
                             synthetic_metrics("confirmation", 0.06, seed=11)], ignore_index=True)
        signal, audio_rows, asr_rows, pooled = synthetic_side_tables(metrics)
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            for set_name in ["pilot", "confirmation"]:
                raw = out / "raw" / set_name
                raw.mkdir(parents=True)
                audio_rows[audio_rows["set"] == set_name].to_csv(raw / "audio_manifest.csv", index=False)
                asr_rows[asr_rows["set"] == set_name].to_csv(raw / "asr_outputs.csv", index=False)
                signal[signal["set"] == set_name].to_csv(raw / "signal_metrics.csv", index=False)
                pooled[pooled["set"] == set_name].to_csv(raw / "pooled_transfer.csv", index=False)
            boot = stats.decompose_all(metrics[metrics["set"] == "pilot"], CONDITIONS, MODELS)
            (out / "pilot").mkdir()
            report.pilot_figures(metrics[metrics["set"] == "pilot"], boot, out / "pilot")
            report.render_pilot(stats.pilot_decision(boot, MODELS), boot,
                                stats.corpus_table(metrics[metrics["set"] == "pilot"]))
            spec = {"spec_sha256": "s" * 64, "created_utc": "t",
                    "data": {"selections": {s: {"n_utterances": 1, "n_speakers": 1}
                                            for s in ["calibration", "pilot", "confirmation"]}},
                    "provenance": {"stage2_tag": "tag", "stage2_commit": "c" * 40,
                                   "revised_gate5_spec_sha256": "r" * 64,
                                   "stage2b_confirmation_selection_sha256": "q" * 64},
                    "asr_models": {"whisper": {"revision": "w" * 40}},
                    "environment": {"packages": {"transformers": "x"}}}
            freeze = {"freeze_sha256": "f" * 64, "created_utc": "t", "code_changed_since_spec": []}
            report.final_analysis(spec, freeze, out, out / "raw", metrics, run_stage3.write_sealed)
            expected = ["01_stage3_summary.md", "03_audio_manifest.csv", "04_asr_outputs.csv",
                        "05_utterance_metrics.csv", "06_corpus_metrics.csv",
                        "07_paired_bootstrap.csv", "08_error_type_analysis.csv",
                        "09_signal_metrics.csv", "10_reproduce_commands.txt",
                        "stage3_decision.json"] + [
                f"fig0{i}_{name}.png" for i, name in [
                    (1, "wer_by_condition"), (2, "bandwidth_vs_codec_residual"),
                    (3, "paired_utterance_differences"), (4, "bootstrap_ci"),
                    (5, "asr_model_comparison"), (6, "error_type_breakdown"),
                    (7, "residual_vs_signal_distortion")]]
            for name in expected:
                self.assertTrue((out / name).exists(), name)
            summary = (out / "01_stage3_summary.md").read_text()
            for heading in ["# Stage 3 Decision", "# Frozen Design", "# ASR Systems", "# Pilot",
                            "# Confirmation", "# Bandwidth Penalty", "# Codec-Specific Residual",
                            "# Cross-ASR Consistency", "# Uncertainty", "# Error Types",
                            "# Signal-Level Interpretation", "# What Is Supported",
                            "# What Is NOT Supported", "# Next Step"]:
                self.assertIn(heading, summary)


# ==================================================
# Provenance (after the real seals exist)
# ==================================================

@unittest.skipUnless((run_stage3.OUT / "selection_confirmation.json").exists(), "run select first")
class TestSelections(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sets = {s: run_stage3.load_selection(s) for s in run_stage3.SETS}

    def test_speaker_disjoint(self):
        speakers = {s: {u["speaker_id"] for u in v["utterances"]} for s, v in self.sets.items()}
        self.assertFalse(speakers["calibration"] & speakers["pilot"])
        self.assertFalse(speakers["pilot"] & speakers["confirmation"])
        self.assertFalse(speakers["calibration"] & speakers["confirmation"])

    def test_durations_and_subsets(self):
        for set_name, selection in self.sets.items():
            for u in selection["utterances"]:
                self.assertLessEqual(u["duration_s"], 30.0)
                self.assertIn(u["subset"], run_stage3.SET_SUBSETS[set_name])

    def test_confirmation_excludes_prior_study(self):
        chosen = {u["utterance"] for u in self.sets["confirmation"]["utterances"]}
        for subset in ["test-clean", "test-other"]:
            prior = run_stage3.prior_study_utterances(subset, run_stage3.list_subset(subset))
            self.assertFalse(chosen & prior)


@unittest.skipUnless(run_stage3.SPEC_JSON.exists(), "run freeze-spec first")
class TestFrozenSpec(unittest.TestCase):

    def test_spec_sealed_and_selections_match(self):
        spec = run_stage3.read_sealed(run_stage3.SPEC_JSON, "spec_sha256")
        for s in run_stage3.SETS:
            self.assertEqual(run_stage3.load_selection(s)["selection_sha256"],
                             spec["data"]["selections"][s]["sha256"])

    def test_code_unchanged_since_last_freeze(self):
        spec = run_stage3.read_sealed(run_stage3.SPEC_JSON, "spec_sha256")
        expected = spec["code_sha256"]
        if run_stage3.CONFIRMATION_FREEZE.exists():
            expected = run_stage3.read_sealed(run_stage3.CONFIRMATION_FREEZE, "freeze_sha256")["code_sha256"]
        self.assertEqual(run_stage3.code_hashes(), expected)


if __name__ == "__main__":
    unittest.main()
