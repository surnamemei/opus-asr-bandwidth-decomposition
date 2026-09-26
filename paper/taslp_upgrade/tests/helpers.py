"""Shared test helpers: import paths and synthetic per-utterance metrics (no audio, no ASR)."""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

UPGRADE_DIR = Path(__file__).resolve().parents[1]
PAPER_DIR = UPGRADE_DIR.parent
REPO_ROOT = PAPER_DIR.parent
for path in (str(UPGRADE_DIR), str(PAPER_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)
os.chdir(REPO_ROOT)                     # Stage 3 and upgrade paths are relative to the repository root


def synthetic_metrics(conditions: list[str], extra_errors: dict[str, float], seed: int = 0,
                      speakers_per_subset: int = 6, utterances_per_speaker: int = 4,
                      models=("whisper", "wav2vec2")) -> pd.DataFrame:
    """
    Paired per-utterance edit counts. Each condition adds a Poisson number of word errors
    with mean extra_errors[condition] to a shared baseline, so contrasts have known signs.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for subset_index, subset in enumerate(["test-clean", "test-other"]):
        for s in range(speakers_per_subset):
            speaker = 1000 * (subset_index + 1) + s
            for u in range(utterances_per_speaker):
                utterance = f"{speaker}-1-{u:04d}"
                n_words = int(rng.integers(10, 40))
                n_chars = 5 * n_words
                for model in models:
                    base = int(rng.poisson(1.5))
                    for condition in conditions:
                        errors = base + int(rng.poisson(extra_errors.get(condition, 0.0)))
                        subs = errors
                        rows.append({
                            "set": "synthetic", "utterance": utterance, "subset": subset,
                            "speaker_id": speaker, "condition": condition, "model": model,
                            "n_words": n_words, "n_chars": n_chars, "hits": n_words - subs,
                            "substitutions": subs, "deletions": 0, "insertions": 0,
                            "word_errors": errors, "wer": errors / n_words,
                            "char_errors": 2 * errors, "cer": 2 * errors / n_chars,
                            "hypothesis_normalised": "",
                        })
    return pd.DataFrame(rows)
