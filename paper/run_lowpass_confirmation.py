"""
Stage 2B, revised Gate 5: confirmatory validation of the frozen low-pass
control on an unseen train-clean-100 speaker subset.

Provenance
----------
The original Stage 2B specification, code (run_lowpass_validation.py),
frozen filter and FAIL report (results_paper/lowpass_validation/) are kept
unchanged. This script imports the original machinery read-only and changes
exactly one thing: Gate 5 no longer requires the LP's coherent 4-8 kHz power
to be within 6 dB of Opus8-NB's (tolerance g5_coherent_hf_vs_opus8nb_max_db
removed). All other gates, all other tolerances (including the +-3 dB
reference tolerance of Gate 5), the filter taps, the calibration procedure
and the encoder settings are unchanged.

Reason: under the linear-only definition the LP reproduces SILK-NB's
bitrate-independent linear band-limiting response. Opus8-NB's coherent
4-8 kHz power also contains SILK's bitrate-dependent in-band coding droop
across the 4 kHz edge (coherent 4-8 kHz power: linear reference -25.3 dB,
Opus12-NB -31.1 dB, Opus8-NB -34.6 dB on dev-clean), which the definition
explicitly excludes. Matching it would require copying coding distortion.

Commands (strictly in this order)
---------------------------------
freeze    Before train-clean-100 is on disk. Writes revised_spec.json: the
          revised Gate 5, the revised tolerance set, the frozen filter hash,
          hashes of the original Stage 2B outputs and code, the encoder
          settings, and the confirmation speakers (chosen from
          SPEAKERS.TXT metadata with a fixed seed) plus the utterance rule.
select    After download. Resolves one utterance per speaker from file
          names only (no audio, no transcripts) and writes selection.json.
confirm   Verifies every hash, then runs the one confirmatory validation.

No ASR model, transcript or WER is used. test-clean / test-other are not
read.

Run:
    /home/mei/elec5305-project/.venv/bin/python paper/run_lowpass_confirmation.py freeze
    /home/mei/elec5305-project/.venv/bin/python paper/run_lowpass_confirmation.py select
    /home/mei/elec5305-project/.venv/bin/python paper/run_lowpass_confirmation.py confirm
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import random
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torchaudio
from tqdm import tqdm

import common
import lowpass
import run_lowpass_validation as stage2b
import run_reproduce


# ==================================================
# Settings
# ==================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path("results_paper") / "lowpass_confirmation"
SPEC_PATH = OUTPUT_DIR / "revised_spec.json"
SELECTION_PATH = OUTPUT_DIR / "selection.json"
ORIGINAL_DIR = stage2b.OUTPUT_DIR
ORIGINAL_CODE = [Path("paper/run_lowpass_validation.py"), Path("paper/lowpass.py")]

CONFIRMATION_SUBSET = "train-clean-100"
SPEAKERS_FILE = Path(common.DATA_ROOT) / "LibriSpeech" / "SPEAKERS.TXT"
SEED = 5305
SPEAKERS_PER_SEX = 20          # 40 speakers, as in the dev-clean calibration set
DEV_SUBSETS = ["dev-clean", "dev-other"]

REMOVED_TOLERANCES = ["g5_coherent_hf_vs_opus8nb_max_db"]
REVISED_TOLERANCES = {
    k: v for k, v in stage2b.TOLERANCES.items() if k not in REMOVED_TOLERANCES
}

UTTERANCE_RULE = (
    "For each selected speaker in ascending numeric ID order, list every "
    "<speaker>/<chapter>/*.flac file of train-clean-100, sort the file names, "
    f"and pick one with random.Random({SEED}).choice (one generator shared "
    "across speakers, in that order). File names only; no audio or "
    "transcript is read during selection."
)

REVISED_GATE5 = {
    "name": "4-8 kHz attenuation matches SILK-NB's linear (bitrate-independent) response",
    "criteria": [
        "|coherent 4-8 kHz power (LP) - coherent 4-8 kHz power (SILK-NB linear "
        "reference, same utterances)| <= g5_coherent_hf_vs_reference_max_db (3.0 dB, "
        "unchanged)",
        "median total 4-8 kHz power change (LP) <= median total 4-8 kHz power "
        "change (Opus8-NB) (unchanged)",
    ],
    "removed": "|coherent 4-8 kHz power (LP) - coherent 4-8 kHz power (Opus8-NB)| "
               "<= 6.0 dB; Opus8-NB coherent 4-8 kHz power is reported as information only",
    "reason": (
        "The control is defined as SILK-NB's linear band-limiting component only. "
        "Opus8-NB's coherent 4-8 kHz power additionally contains bitrate-dependent "
        "in-band coding droop across the 4 kHz edge (dev-clean: linear reference "
        "-25.3 dB, Opus12-NB -31.1 dB, Opus8-NB -34.6 dB; |H1| at 3.5-4.25 kHz 5-11 dB "
        "below the linear chain at 8 kbps), which the definition excludes."
    ),
}


# ==================================================
# Hash helpers
# ==================================================

def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def body_sha256(record: dict, hash_key: str) -> str:
    body = {k: v for k, v in record.items() if k != hash_key}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def write_sealed(path: Path, record: dict, hash_key: str) -> str:
    if path.exists():
        raise RuntimeError(f"{path} already exists and is frozen")
    record[hash_key] = body_sha256(record, hash_key)
    path.write_text(json.dumps(record, indent=1))
    return record[hash_key]


def read_sealed(path: Path, hash_key: str) -> dict:
    record = json.loads(path.read_text())
    if body_sha256(record, hash_key) != record[hash_key]:
        raise RuntimeError(f"{path} was modified after it was frozen")
    return record


def original_snapshot() -> dict[str, str]:
    files = sorted(p for p in ORIGINAL_DIR.iterdir() if p.is_file()) + ORIGINAL_CODE
    return {str(p): file_sha256(p) for p in files}


def encoder_settings() -> dict[str, dict]:
    return {cell: asdict(s) for cell, s in stage2b.CELLS.items() if s is not None}


# ==================================================
# Speaker and utterance selection
# ==================================================

def read_speakers() -> list[dict]:
    speakers = []
    for line in SPEAKERS_FILE.read_text().splitlines():
        if line.startswith(";") or not line.strip():
            continue
        speaker_id, sex, subset, minutes, name = [f.strip() for f in line.split("|", 4)]
        speakers.append({"id": int(speaker_id), "sex": sex, "subset": subset,
                         "minutes": float(minutes)})
    return speakers


def select_speakers() -> dict[str, list[int]]:
    speakers = read_speakers()
    ids = [s["id"] for s in speakers]
    if len(ids) != len(set(ids)):
        raise RuntimeError("a speaker is listed in more than one subset")
    rng = random.Random(SEED)
    chosen = {}
    for sex in ["F", "M"]:
        pool = sorted(s["id"] for s in speakers
                      if s["subset"] == CONFIRMATION_SUBSET and s["sex"] == sex)
        chosen[sex] = sorted(rng.sample(pool, SPEAKERS_PER_SEX))
    return chosen


def subset_dir(subset: str) -> Path:
    return Path(common.DATA_ROOT) / "LibriSpeech" / subset


# ==================================================
# Commands
# ==================================================

def freeze() -> None:

    taps, record = lowpass.load_filter(stage2b.FILTER_PATH)
    if record["metadata"]["tolerances_sha256"] != stage2b.tolerances_sha256():
        raise RuntimeError("original Stage 2B tolerances differ from the frozen filter record")
    if subset_dir(CONFIRMATION_SUBSET).exists():
        raise RuntimeError(
            f"{CONFIRMATION_SUBSET} is already on disk; the specification must be "
            "frozen before the confirmation data are available")

    speakers = select_speakers()
    selected = speakers["F"] + speakers["M"]
    dev_speakers = {int(p.name) for s in DEV_SUBSETS for p in subset_dir(s).iterdir()
                    if p.is_dir()}
    if dev_speakers & set(selected):
        raise RuntimeError("confirmation speakers overlap the dev calibration/validation sets")

    spec = {
        "stage": "2B revised Gate 5, confirmatory validation",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "frozen_filter": {"path": str(stage2b.FILTER_PATH),
                          "taps_sha256": record["taps_sha256"],
                          "num_taps": record["num_taps"]},
        "original_specification": {
            "tolerances": stage2b.TOLERANCES,
            "tolerances_sha256": stage2b.tolerances_sha256(),
            "verdict": "FAIL (Gate 5 and Gate 7, results_paper/lowpass_validation)",
            "files_sha256": original_snapshot(),
        },
        "revised_gate5": REVISED_GATE5,
        "removed_tolerance_keys": REMOVED_TOLERANCES,
        "revised_tolerances": REVISED_TOLERANCES,
        "unchanged": [
            "filter taps (frozen_filter.json)", "calibration procedure",
            "encoder settings of every cell", "gates 1, 2, 3, 4, 6 and their tolerances",
            "Gate 5 reference tolerance (3.0 dB)",
        ],
        "encoder_settings": encoder_settings(),
        "confirmation_set": {
            "subset": CONFIRMATION_SUBSET,
            "speaker_source": str(SPEAKERS_FILE),
            "speakers_file_sha256": file_sha256(SPEAKERS_FILE),
            "seed": SEED,
            "speaker_rule": f"random.Random({SEED}).sample of {SPEAKERS_PER_SEX} female "
                            f"then {SPEAKERS_PER_SEX} male speakers from the sorted "
                            f"{CONFIRMATION_SUBSET} IDs in SPEAKERS.TXT",
            "speakers_female": speakers["F"],
            "speakers_male": speakers["M"],
            "disjoint_from_dev_speakers": True,
            "utterance_rule": UTTERANCE_RULE,
        },
        "confirmation_gates": "Gates 1-4 and 6 (original), Gate 5 (revised) on the "
                              "confirmation set; PASS only if all pass with the frozen filter",
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    digest = write_sealed(SPEC_PATH, spec, "spec_sha256")
    print(json.dumps({"spec_sha256": digest, "taps_sha256": record["taps_sha256"],
                      "speakers": speakers}, indent=1))


def select() -> None:

    spec = read_sealed(SPEC_PATH, "spec_sha256")
    root = subset_dir(CONFIRMATION_SUBSET)
    rng = random.Random(SEED)
    utterances = []
    speakers = sorted(spec["confirmation_set"]["speakers_female"]
                      + spec["confirmation_set"]["speakers_male"])
    for speaker in speakers:
        files = sorted(p.relative_to(root).as_posix()
                       for p in (root / str(speaker)).glob("*/*.flac"))
        if not files:
            raise RuntimeError(f"no audio files for speaker {speaker}")
        chosen = rng.choice(files)
        speaker_id, chapter_id, utterance_id = Path(chosen).stem.split("-")
        utterances.append({"speaker_id": int(speaker_id), "chapter_id": int(chapter_id),
                           "utterance_id": int(utterance_id), "path": chosen,
                           "candidates": len(files)})

    selection = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "spec_sha256": spec["spec_sha256"],
        "subset": CONFIRMATION_SUBSET,
        "rule": UTTERANCE_RULE,
        "utterances": utterances,
    }
    digest = write_sealed(SELECTION_PATH, selection, "selection_sha256")
    print(json.dumps({"selection_sha256": digest, "utterances": len(utterances)}, indent=1))


def run_selection(utterances: list[dict], taps: np.ndarray):
    """The per-utterance body of stage2b.run_subset, reading audio by path."""
    root = subset_dir(CONFIRMATION_SUBSET)
    rows, curves = [], collections.defaultdict(list)
    accumulators = {cell: stage2b.TransferAccumulator() for cell in stage2b.CELLS}
    packets = {cell: collections.Counter() for cell in stage2b.CELLS if cell != "lp"}

    for number, entry in enumerate(tqdm(utterances, desc=CONFIRMATION_SUBSET, unit="utt")):
        waveform, sample_rate = torchaudio.load(root / entry["path"])
        if sample_rate != stage2b.SAMPLE_RATE:
            raise RuntimeError(f"{entry['path']}: {sample_rate} Hz")
        ids = {"dataset": CONFIRMATION_SUBSET, "dataset_index": number,
               "speaker_id": entry["speaker_id"], "chapter_id": entry["chapter_id"],
               "utterance_id": entry["utterance_id"]}
        for cell, settings in stage2b.CELLS.items():
            if cell == "lp":
                processed = lowpass.apply_zero_phase(waveform, taps)
                repeat = lowpass.apply_zero_phase(waveform, taps)
                extra = {"deterministic": torch.equal(processed, repeat),
                         "output_dtype": str(processed.dtype)}
            else:
                processed, configurations = stage2b.opus_round_trip(
                    waveform, sample_rate, settings)
                packets[cell].update(configurations)
                extra = {"share_silk_nb": configurations.get("SILK-NB", 0)
                         / sum(configurations.values())}
            row, dfrequency, aligned = stage2b.signal_metrics(waveform, processed)
            rows.append({**ids, "cell": cell, **row, **extra})
            curves[cell].append(dfrequency)
            accumulators[cell].add(*aligned)

    transfer = {cell: acc.results() for cell, acc in accumulators.items()}
    return pd.DataFrame(rows), curves, transfer, packets


def revised_gate5(subset: str, rows: pd.DataFrame, transfer: dict) -> dict:
    t = REVISED_TOLERANCES
    lp = rows[rows["cell"] == "lp"]
    opus8 = rows[rows["cell"] == "opus_8k_nb"]
    lp_t, ref_t, o8_t = transfer["lp"], transfer["silk_nb_linear_ref"], transfer["opus_8k_nb"]
    hf_ref = lp_t["coherent_hf_power_db"] - ref_t["coherent_hf_power_db"]
    lp_hf, o8_hf = float(lp["hf_power_change_db"].median()), float(opus8["hf_power_change_db"].median())
    passed = abs(hf_ref) <= t["g5_coherent_hf_vs_reference_max_db"] and lp_hf <= o8_hf
    return {
        "subset": subset, "gate": "5 (revised)", "name": REVISED_GATE5["name"],
        "status": "PASS" if passed else "FAIL",
        "evidence": (
            f"coherent 4-8 kHz power LP {lp_t['coherent_hf_power_db']:.1f} dB, linear "
            f"reference {ref_t['coherent_hf_power_db']:.1f} dB ({hf_ref:+.1f}, tolerance "
            f"+-{t['g5_coherent_hf_vs_reference_max_db']:.1f}); total 4-8 kHz power change "
            f"median LP {lp_hf:.1f} dB <= Opus8-NB {o8_hf:.1f} dB: {lp_hf <= o8_hf}; "
            f"information only: Opus8-NB coherent 4-8 kHz power "
            f"{o8_t['coherent_hf_power_db']:.1f} dB ({lp_t['coherent_hf_power_db'] - o8_t['coherent_hf_power_db']:+.1f})"
        ),
    }


def confirm() -> int:

    spec = read_sealed(SPEC_PATH, "spec_sha256")
    selection = read_sealed(SELECTION_PATH, "selection_sha256")
    taps, record = lowpass.load_filter(stage2b.FILTER_PATH)

    checks = {
        "selection made under this spec": selection["spec_sha256"] == spec["spec_sha256"],
        "filter taps unchanged": record["taps_sha256"] == spec["frozen_filter"]["taps_sha256"],
        "original tolerances unchanged": stage2b.tolerances_sha256()
        == spec["original_specification"]["tolerances_sha256"],
        "revised tolerances in code = frozen spec": REVISED_TOLERANCES == spec["revised_tolerances"],
        "encoder settings unchanged": json.loads(json.dumps(encoder_settings()))
        == spec["encoder_settings"],
        "original Stage 2B outputs and code unchanged": original_snapshot()
        == spec["original_specification"]["files_sha256"],
    }
    if not all(checks.values()):
        raise RuntimeError(f"provenance check failed: {checks}")

    rows, curves, transfer, packets = run_selection(selection["utterances"], taps)
    rows.to_csv(OUTPUT_DIR / "utterance_rows.csv", index=False)

    original = stage2b.evaluate_gates(CONFIRMATION_SUBSET, rows, transfer, taps)
    gates = [g for g in original if g["gate"] != 5]
    gates.insert(4, revised_gate5(CONFIRMATION_SUBSET, rows, transfer))
    passed = all(g["status"] == "PASS" for g in gates)
    gates.append({
        "subset": CONFIRMATION_SUBSET, "gate": "7 (confirmatory)",
        "name": "frozen filter passes gates 1-4, 5 (revised), 6 on unseen speakers",
        "status": "PASS" if passed else "FAIL",
        "evidence": f"taps SHA-256 {record['taps_sha256']}; "
                    f"{sum(g['status'] == 'PASS' for g in gates)}/{len(gates)} passed",
    })
    gates_df = pd.DataFrame(gates)
    original_gate5 = pd.DataFrame([dict(g, gate="5 (original, information only)")
                                   for g in original if g["gate"] == 5])

    summary = stage2b.cell_summary(CONFIRMATION_SUBSET, rows, transfer, packets)
    transfer_df = stage2b.transfer_table(CONFIRMATION_SUBSET, transfer, curves)
    gates_df.to_csv(OUTPUT_DIR / "gates.csv", index=False)
    original_gate5.to_csv(OUTPUT_DIR / "original_gate5_on_confirmation_set.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "cell_summary.csv", index=False)
    transfer_df.to_csv(OUTPUT_DIR / "transfer_curves.csv", index=False)

    environment = run_reproduce.collect_environment()
    environment["confirmation_subset"] = os.path.realpath(subset_dir(CONFIRMATION_SUBSET))
    (OUTPUT_DIR / "environment.json").write_text(json.dumps(environment, indent=2))

    write_report(spec, selection, record, checks, gates_df, original_gate5, summary,
                 transfer_df, passed)
    print(gates_df[["gate", "status", "evidence"]].to_string(index=False))
    print(f"Report: {OUTPUT_DIR / 'confirmation_report.md'}")
    return 0 if passed else 1


def write_report(spec, selection, record, checks, gates, original_gate5, summary,
                 transfer_df, passed) -> None:

    table = run_reproduce.markdown_table
    original_gates = pd.read_csv(ORIGINAL_DIR / "gates.csv")
    key_freqs = [3000, 3500, 3750, 3875, 4000, 4062.5, 4125, 4187.5, 4250, 4500, 5000]
    h1 = (transfer_df[transfer_df["frequency_hz"].isin(key_freqs)]
          .pivot_table(index="frequency_hz", columns="cell", values="h1_rel_db").reset_index())

    lines = [
        "# Stage 2B confirmation: revised Gate 5 on unseen train-clean-100 speakers",
        "",
        f"**Verdict under the revised specification: {'PASS' if passed else 'FAIL'}**",
        "",
        "## 1. Original Stage 2B result (unchanged, historical)",
        "",
        "Original verdict: **FAIL** (results_paper/lowpass_validation/validation_report.md).",
        "",
        table(original_gates[["subset", "gate", "status"]]),
        "",
        "## 2. Why the original Gate 5 was inconsistent with the linear-only definition",
        "",
        REVISED_GATE5["reason"],
        "",
        "## 3. Revised criterion (frozen before the confirmation data were on disk)",
        "",
        f"- spec SHA-256 `{spec['spec_sha256']}`, created {spec['created_utc']}",
        f"- selection SHA-256 `{selection['selection_sha256']}`, created {selection['created_utc']}",
        f"- removed tolerance: {spec['removed_tolerance_keys']} ({REVISED_GATE5['removed']})",
        *[f"- revised Gate 5 criterion: {c}" for c in REVISED_GATE5["criteria"]],
        f"- unchanged: {', '.join(spec['unchanged'])}",
        "",
        "## 4. Confirmation set",
        "",
        f"- {CONFIRMATION_SUBSET}, {len(selection['utterances'])} speakers "
        f"({len(spec['confirmation_set']['speakers_female'])} F, "
        f"{len(spec['confirmation_set']['speakers_male'])} M), one utterance each, seed {SEED}",
        f"- speaker rule: {spec['confirmation_set']['speaker_rule']}",
        f"- utterance rule: {spec['confirmation_set']['utterance_rule']}",
        "",
        "## 5. Provenance checks before the run",
        "",
        table(pd.DataFrame([{"check": k, "result": v} for k, v in checks.items()])),
        "",
        f"Filter taps SHA-256: `{record['taps_sha256']}` (frozen at Stage 2B calibration).",
        "",
        "## 6. Gates on the confirmation set",
        "",
        table(gates),
        "",
        "Original Gate 5 evaluated on the same data (information only, not part of the "
        "revised verdict):",
        "",
        table(original_gate5[["gate", "status", "evidence"]]),
        "",
        "## 7. Per-cell summary",
        "",
        table(summary),
        "",
        "## 8. Linear transfer |H1| relative to the 0.5-2 kHz level (dB)",
        "",
        table(h1),
        "",
    ]
    (OUTPUT_DIR / "confirmation_report.md").write_text("\n".join(lines))


# ==================================================
# Main
# ==================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 2B revised Gate 5 confirmation")
    parser.add_argument("command", choices=["freeze", "select", "confirm"])
    args = parser.parse_args()
    os.chdir(REPO_ROOT)
    if args.command == "freeze":
        freeze()
        return 0
    if args.command == "select":
        select()
        return 0
    return confirm()


if __name__ == "__main__":
    sys.exit(main())
