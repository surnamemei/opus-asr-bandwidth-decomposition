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
