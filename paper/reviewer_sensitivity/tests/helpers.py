"""Shared test helpers: import paths (no audio, no ASR)."""

import os
import sys
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parents[1]
PAPER_DIR = REVIEW_DIR.parent
REPO_ROOT = PAPER_DIR.parent
for path in (str(REVIEW_DIR), str(PAPER_DIR / "taslp_upgrade"), str(PAPER_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)
os.chdir(REPO_ROOT)                     # plan paths are relative to the repository root


def synthetic_metrics(conditions, extra_errors, seed=0, speakers_per_subset=6, utterances_per_speaker=4,
                      models=("whisper", "wav2vec2")):
    """Paired per-utterance edit counts with known signs (as the upgrade tests' helper)."""
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed)
    rows = []
    for subset_index, subset in enumerate(["test-clean", "test-other"]):
        for s in range(speakers_per_subset):
            speaker = 1000 * (subset_index + 1) + s
            for u in range(utterances_per_speaker):
                utterance = f"{speaker}-1-{u:04d}"
                n_words = int(rng.integers(10, 40))
                for model in models:
                    base = int(rng.poisson(1.5))
                    for condition in conditions:
                        errors = base + int(rng.poisson(extra_errors.get(condition, 0.0)))
                        rows.append({"set": "synthetic", "utterance": utterance, "subset": subset,
                                     "speaker_id": speaker, "condition": condition, "model": model,
                                     "n_words": n_words, "n_chars": 5 * n_words, "hits": n_words - errors,
                                     "substitutions": errors, "deletions": 0, "insertions": 0,
                                     "word_errors": errors, "wer": errors / n_words, "char_errors": 2 * errors,
                                     "cer": 2 * errors / (5 * n_words), "hypothesis_normalised": ""})
    return pd.DataFrame(rows)
