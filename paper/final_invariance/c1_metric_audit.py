"""
C1: metric and weighting robustness audit of the primary Stage 3 contrasts (no new ASR).

Uses only the sealed Stage 3 per-utterance outputs (REF, LP, OPUS) and Stage 3's paired
speaker-cluster bootstrap (10,000 replicates, seed 5305, speakers resampled within test subsets).
For every metric: B = LP - REF, R = OPUS - LP, T = OPUS - REF, R - B, and the sequential share B / T.

Metrics (each recomputed in every bootstrap replicate from that replicate's speaker weights):
    micro      corpus WER (total errors / total words; the primary Stage 3 estimator)
    macro      mean per-utterance WER
    speaker    equal-speaker-weighted WER (mean of per-speaker corpus WERs)
    cer        corpus CER
    S, D, I    substitutions, deletions, insertions per 100 reference words
    rel_*      relative change from REF: (condition - REF) / REF for micro, macro, speaker and CER
Scopes: pooled (stratified by subset), test-clean, test-other.

Classification rules, fixed before the audit was computed:

- Sign and ordering statements ("B > 0", "R > 0", "R > B"), per recogniser. A statement holds in a
  (metric, scope) cell if the 95 % interval of B, R or R - B lies above zero.
  - METRIC_ROBUST: it holds for all four pooled weightings (micro, macro, speaker, CER) and in both
    test subsets (micro).
  - WEIGHTING_SENSITIVE: it holds for pooled micro but not for at least one other pooled weighting.
  - SUBSET_DEPENDENT: it holds for pooled micro but not in at least one test subset (micro).
  - A statement can be both WEIGHTING_SENSITIVE and SUBSET_DEPENDENT. NOT_SUPPORTED means it does
    not hold even for pooled micro.
- Ratio statements (the sequential share B / T), per recogniser. RATIO_UNSTABLE applies if any of:
  - a pooled replicate has T <= 0 (denominator not bounded away from zero);
  - the pooled micro interval has lower bound <= 0 or upper/lower > 2;
  - the pooled point estimates across the four weightings differ by more than a factor of 1.5.
  Otherwise the statement is METRIC_ROBUST.

    python paper/final_invariance/c1_metric_audit.py
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "paper" / "taslp_upgrade"), str(ROOT / "paper")]
os.chdir(ROOT)

import numpy as np                   # noqa: E402
import pandas as pd                  # noqa: E402

import run_stage3 as s3              # noqa: E402
import stage3_stats as s3stats       # noqa: E402
import upgrade_design as upgrade     # noqa: E402
import upgrade_stats as ustats       # noqa: E402

OUT_CSV = Path("results_paper/final_invariance/c1_metric_table.csv")
OUT_JSON = Path("results_paper/final_invariance/C1_RECORD.json")
MODELS = ["whisper", "wav2vec2"]
CONDITIONS = ["REF", "LP", "OPUS"]
WEIGHTINGS = ["micro", "macro", "speaker", "cer"]
SEED, N_BOOT = s3stats.BOOT_SEED, s3stats.N_BOOT


def levels(paired: s3stats.PairedSet, w: np.ndarray) -> dict:
    """Metric level of each condition in every replicate (row 0 = point estimate)."""
    ss = paired.speaker_sum
    words, chars = w @ ss(paired.n_words), w @ ss(paired.n_chars)
    count = w @ ss(np.ones(len(paired.utterances)))
    out = {}
    for c in CONDITIONS:
        v = paired.values[c]
        spk_wer = ss(v["word_errors"]) / ss(paired.n_words)
        out[c] = {"micro": w @ ss(v["word_errors"]) / words, "macro": w @ ss(v["wer"]) / count,
                  "speaker": (w @ spk_wer) / w.sum(axis=1), "cer": w @ ss(v["char_errors"]) / chars,
                  "S": w @ ss(v["substitutions"]) / words, "D": w @ ss(v["deletions"]) / words,
                  "I": w @ ss(v["insertions"]) / words}
    return out


def interval(series: np.ndarray, scale: float = 100.0) -> dict:
    s = np.asarray(series, dtype=float) * scale
    lo, hi = s3stats.percentile_interval(s[1:])
    return {"estimate": float(s[0]), "ci_lower": lo, "ci_upper": hi, "excludes_zero": bool(lo > 0 or hi < 0),
            "n_boot_valid": int(np.sum(np.isfinite(s[1:])))}


def audit_cell(paired: s3stats.PairedSet, w: np.ndarray) -> list[dict]:
    lev = levels(paired, w)
    rows = []
    for metric in WEIGHTINGS + ["S", "D", "I"]:
        ref, lp, opus = (lev[c][metric] for c in CONDITIONS)
        b, r, t = lp - ref, opus - lp, opus - ref
        for name, series in [("B", b), ("R", r), ("T", t), ("R_minus_B", r - b)]:
            row = {"metric": metric, "quantity": name, "unit": "pp" if metric in WEIGHTINGS else "per_100_words",
                   **interval(series)}
            if name == "R_minus_B":
                row["prob_R_gt_B"] = float(np.mean(series[1:] > 0))
            rows.append(row)
        if metric in WEIGHTINGS:
            share = np.where(t > 0, b / np.where(t > 0, t, 1.0), np.nan)
            rows.append({"metric": metric, "quantity": "share_B_over_T", "unit": "fraction", **interval(share, 1.0),
                         "replicates_denominator_le_0": int(np.sum(t[1:] <= 0))})
            for name, num in [("rel_B", b), ("rel_R", r), ("rel_T", t)]:
                rows.append({"metric": metric, "quantity": name, "unit": "fraction of REF", **interval(num / ref, 1.0)})
    return rows


def classify(table: pd.DataFrame) -> dict:
    def get(model, scope, metric, quantity):
        r = table[(table["model"] == model) & (table["scope"] == scope) & (table["metric"] == metric)
                  & (table["quantity"] == quantity)].iloc[0]
        return r
    out = {}
    for model in MODELS:
        for label, q in [("bandwidth component B > 0", "B"), ("residual R > 0", "R"), ("ordering R > B", "R_minus_B")]:
            holds = lambda scope, metric: bool(get(model, scope, metric, q)["ci_lower"] > 0)
            pooled = {m: holds("pooled", m) for m in WEIGHTINGS}
            subsets = {s: holds(s, "micro") for s in ["test-clean", "test-other"]}
            if not pooled["micro"]:
                classes = ["NOT_SUPPORTED"]
            else:
                classes = []
                if not all(pooled.values()):
                    classes.append("WEIGHTING_SENSITIVE")
                if not all(subsets.values()):
                    classes.append("SUBSET_DEPENDENT")
                classes = classes or ["METRIC_ROBUST"]
            out[f"{model}: {label}"] = {"classes": classes, "pooled": pooled, "subsets_micro": subsets}
        shares = {m: get(model, "pooled", m, "share_B_over_T") for m in WEIGHTINGS}
        est = {m: float(shares[m]["estimate"]) for m in WEIGHTINGS}
        micro = shares["micro"]
        reasons = []
        if any(int(shares[m]["replicates_denominator_le_0"]) > 0 for m in WEIGHTINGS):
            reasons.append("some replicates have T <= 0")
        if micro["ci_lower"] <= 0 or micro["ci_upper"] / micro["ci_lower"] > 2:
            reasons.append(f"wide micro interval [{micro['ci_lower']:.3f}, {micro['ci_upper']:.3f}]")
        if max(est.values()) / max(min(est.values()), 1e-12) > 1.5:
            reasons.append(f"point estimates across weightings {json.dumps({k: round(v, 3) for k, v in est.items()})}")
        out[f"{model}: sequential share B/T"] = {"classes": ["RATIO_UNSTABLE"] if reasons else ["METRIC_ROBUST"],
                                                 "reasons": reasons, "estimates": est,
                                                 "micro_interval": [float(micro["ci_lower"]), float(micro["ci_upper"])]}
    return out


def main() -> int:
    if OUT_JSON.exists():
        raise RuntimeError(f"{OUT_JSON} is sealed and exists")
    manifest = s3.read_sealed(upgrade.S3_CONFIRMATION / "outputs_sha256.json", "outputs_sha256")
    path = upgrade.S3_CONFIRMATION / "utterance_metrics.csv"
    if s3.file_sha256(path) != manifest["files"]["utterance_metrics.csv"]:
        raise RuntimeError("Stage 3 metrics differ from their sealed manifest")
    metrics = pd.read_csv(path, keep_default_na=False)
    metrics = metrics[metrics["condition"].isin(CONDITIONS)]
    rows = []
    for model in MODELS:
        group = metrics[metrics["model"] == model]
        for scope, part in [("pooled", group)] + [(s, group[group["subset"] == s]) for s in ["test-clean", "test-other"]]:
            paired = s3stats.PairedSet(part, CONDITIONS)
            w = ustats.replicate_weights(paired, SEED, N_BOOT)
            rows += [{"model": model, "scope": scope, **r} for r in audit_cell(paired, w)]
    table = pd.DataFrame(rows)
    # the primary estimator must reproduce the sealed Stage 3 bootstrap exactly
    boot = pd.read_csv(upgrade.S3_BOOTSTRAP)
    boot = boot[(boot["set"] == "confirmation") & (boot["kind"] == "micro")]
    worst = 0.0
    for model in MODELS:
        for scope in ["pooled", "test-clean", "test-other"]:
            for q, s3q in [("B", "delta_bw"), ("R", "delta_opus_residual"), ("T", "delta_opus_total")]:
                a = table[(table["model"] == model) & (table["scope"] == scope) & (table["metric"] == "micro")
                          & (table["quantity"] == q)].iloc[0]
                b = boot[(boot["model"] == model) & (boot["scope"] == scope) & (boot["quantity"] == s3q)].iloc[0]
                worst = max(worst, abs(a["estimate"] - b["estimate"]), abs(a["ci_lower"] - b["ci_lower"]),
                            abs(a["ci_upper"] - b["ci_upper"]))
    if worst > 1e-9:
        raise RuntimeError(f"the audit does not reproduce the sealed Stage 3 micro contrasts ({worst})")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT_CSV, index=False)
    record = {"created_utc": s3.now(), "analysis": "C1 metric and weighting robustness audit (no new ASR)",
              "inputs": {"stage3_confirmation_outputs_sha256": manifest["outputs_sha256"],
                         "stage3_bootstrap_csv_sha256": s3.file_sha256(upgrade.S3_BOOTSTRAP)},
              "bootstrap": f"Stage 3 paired speaker-cluster bootstrap, {N_BOOT:,} replicates, seed {SEED}",
              "stage3_reproduction_max_abs_difference_pp": worst,
              "classification_rules": __doc__.split("Classification rules, fixed before the audit was computed:")[1]
              .split("    python")[0].strip(),
              "classifications": classify(table), "table_sha256": s3.file_sha256(OUT_CSV)}
    digest = s3.write_sealed(OUT_JSON, s3.native(record), "record_sha256")
    print(json.dumps(record["classifications"], indent=1))
    print("record_sha256", digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
