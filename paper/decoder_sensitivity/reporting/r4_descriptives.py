"""
R4: hypothesis differences between FFmpeg- and libopus-decoded OPUS, requested by the author at the
approval of R4 and not pre-specified in the frozen plan. Written outside the code freeze; run once
after RS5; reads sealed outputs only; no measure enters an outcome.

    python paper/decoder_sensitivity/reporting/r4_descriptives.py

Writes results_paper/decoder_sensitivity/analysis/r4_descriptives.json (sealed).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parents[1] / "reviewer_sensitivity"),
                str(HERE.parents[1] / "taslp_upgrade"), str(HERE.parents[1])]

import pandas as pd                  # noqa: E402

import r4_design as design           # noqa: E402
import run_r4                        # noqa: E402
import run_stage3 as s3              # noqa: E402
import upgrade_design as upgrade     # noqa: E402

OUT = run_r4.ANALYSIS / "r4_descriptives.json"


def main() -> None:
    if OUT.exists():
        raise RuntimeError(f"{OUT} exists")
    decision = s3.read_sealed(run_r4.ANALYSIS / "r4_decision.json", "decision_sha256")
    new = run_r4.verified_csv(run_r4.RAW, "asr_outputs.csv", keep_default_na=False)
    old = run_r4.verified_csv(upgrade.S3_CONFIRMATION, "asr_outputs.csv", keep_default_na=False)
    new = new[new["condition"] == design.OPUS_LIBOPUS].set_index(["utterance", "model"])
    old = old[old["condition"] == design.STAGE3_LABEL[design.OPUS_FFMPEG]].set_index(["utterance", "model"])
    if set(new.index) != set(old.index):
        raise RuntimeError("OPUS_LIBOPUS and Stage 3 OPUS cover different utterances")
    old = old.reindex(new.index)
    counts = {}
    for model in design.MODELS:
        part = new.xs(model, level="model")
        ref = old.xs(model, level="model").reindex(part.index)
        raw = part["hypothesis"] != ref["hypothesis"]
        norm = part["hypothesis_normalised"] != ref["hypothesis_normalised"]
        counts[model] = {
            "utterances": int(len(part)),
            "raw_hypothesis_differs": int(raw.sum()),
            "normalised_hypothesis_differs": int(norm.sum()),
            "by_subset": {s: {"raw_hypothesis_differs": int(raw[part["subset"] == s].sum()),
                              "normalised_hypothesis_differs": int(norm[part["subset"] == s].sum()),
                              "utterances": int((part["subset"] == s).sum())}
                          for s in sorted(part["subset"].unique())},
        }
    s3.write_sealed(OUT, s3.native({
        "created_utc": s3.now(),
        "label": "descriptive; requested by the author at the approval of R4; not pre-specified in the frozen plan; "
                 "computed by this reporting script outside the code freeze after RS5, from sealed outputs only; "
                 "enters no gate and no outcome",
        "r4_decision_sha256": decision["decision_sha256"],
        "r4_outputs_sha256": decision["outputs_sha256"],
        "stage3_confirmation_outputs_sha256":
            s3.read_sealed(upgrade.S3_CONFIRMATION / "outputs_sha256.json", "outputs_sha256")["outputs_sha256"],
        "comparison": "OPUS_LIBOPUS (R4 run) against OPUS_FFMPEG (Stage 3 confirmation run, label OPUS), per utterance "
                      "and recogniser; raw and Whisper-normalised hypotheses",
        "hypothesis_differences": counts,
    }), "descriptives_sha256")
    print(OUT.read_text())


if __name__ == "__main__":
    import os
    os.chdir(design.REPO_ROOT)
    main()
