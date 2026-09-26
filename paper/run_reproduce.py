"""
Stage 1: reproduce the frozen ELEC5305 pipeline before any intervention.

For the first NUM_UTTERANCES utterances of the frozen 500-utterance selection
of each LibriSpeech subset, this script re-runs

    WAV, Opus 12 kbps and Opus 8 kbps

through the copied frozen logic in paper/common.py, repeating the per-
utterance loop bodies of

    src/run_all_experiments.py        (ASR, WER, bitrate)
    src/signal_distortion_analysis.py (alignment, LSD, retained bandwidth)
    src/representation_analysis.py    (raw and standardised drift)
    src/opus_mode_check.py            (Opus TOC configuration)

and compares every new row with the corresponding frozen row. Each frozen
script encoded the audio independently, so each path here encodes
independently too.

Nothing under src/ or results/ is written. SHA-256 hashes of both trees are
taken before and after the run and compared.

Outputs (results_paper/reproduce/):
    environment.json           versions of Python, PyTorch, FFmpeg, libopus, CUDA, ...
    requirements-lock.txt      pip freeze of the interpreter used
    new_asr_rows.csv           one row per utterance and condition
    new_signal_rows.csv        one row per utterance and Opus condition
    new_representation_rows.csv
    new_packet_modes.csv       TOC configuration counts per utterance
    new_determinism_rows.csv   decoded-waveform hashes of the independent encodes
    frozen_hashes.json         src/ and results/ hashes before and after
    equivalence_report.csv     one row per compared field
    equivalence_report.md

Run from anywhere (the script changes to the repository root):
    /home/mei/elec5305-project/.venv/bin/python paper/run_reproduce.py
"""

import argparse
import ctypes
import datetime
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import jiwer
import numpy as np
import pandas as pd
import torch
import torchaudio
from jiwer import wer
from tqdm import tqdm

import common


# ==================================================
# Settings
# ==================================================

REPO_ROOT = Path(__file__).resolve().parent.parent

FROZEN_DIR = Path("results")
OUTPUT_DIR = Path("results_paper") / "reproduce"

# First NUM_UTTERANCES of the frozen selection, per subset. 50 also matches
# the utterances used by the frozen table_opus_modes.csv (test-clean).
NUM_UTTERANCES = 50

CONDITIONS = [
    {"codec": "wav", "bitrate": "uncompressed"},
    {"codec": "opus", "bitrate": "12k"},
    {"codec": "opus", "bitrate": "8k"},
]
CODEC_CONDITIONS = [c for c in CONDITIONS if c["codec"] != "wav"]

# Hidden states are recomputed twice for the first few WAV utterances to
# measure run-to-run GPU variation
REPEAT_UTTERANCES = 5

# torchaudio.save writes 16-bit PCM WAV with a 78-byte header, so the frozen
# original_size_bytes gives the exact number of samples
WAV_HEADER_BYTES = 78
WAV_BYTES_PER_SAMPLE = 2

# --------------------------------------------------
# Tolerances, fixed before the first comparison run
# --------------------------------------------------
# Frozen ASR and signal CSVs store full float64 precision, so their fields
# are expected to reproduce exactly (signal analysis runs on the CPU).
TOL_WER = 0.0
TOL_RELATIVE_BITRATE = 1e-12
TOL_SIGNAL_ABS = 1e-9
# Frozen representation CSV is written with float_format="%.6g". A drift
# value passes if it is within the 6-significant-digit rounding of the
# frozen value plus TOL_DRIFT_EXCESS.
TOL_DRIFT_EXCESS = 1e-5

SIGNAL_FLOAT_FIELDS = [
    "spectral_distortion",
    "lsd_db",
    "hf_power_change_db",
    "estimated_delay_ms",
]
DRIFT_FIELDS = (
    [f"drift_{layer}" for layer in common.LAYER_NAMES]
    + [f"sdrift_{layer}" for layer in common.LAYER_NAMES]
)


# ==================================================
# Helpers
# ==================================================

def condition_label(codec: str, bitrate: str) -> str:
    return "WAV" if codec == "wav" else f"Opus {bitrate}"


def tensor_hash(tensor: torch.Tensor) -> str:
    array = tensor.detach().cpu().contiguous().numpy()
    return hashlib.sha256(array.tobytes()).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_tree(roots=("src", "results")) -> dict[str, str]:
    hashes = {}
    for root in roots:
        for path in sorted(Path(root).rglob("*")):
            if path.is_file():
                hashes[str(path)] = file_hash(path)
    return hashes


def tree_digest(hashes: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def read_csv(path: Path) -> pd.DataFrame:
    """Read a result CSV without float rounding or NaN conversion of text."""
    return pd.read_csv(
        path,
        dtype={"bitrate": str},
        keep_default_na=False,
        float_precision="round_trip",
    )


def encode_opus_file(waveform, sample_rate, bitrate):
    """
    Encode exactly as src/opus_mode_check.py main() does and return the
    Ogg file size and the audio packets.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        wav_path = os.path.join(temp_dir, "input.wav")
        opus_path = os.path.join(temp_dir, "output.opus")
        torchaudio.save(wav_path, waveform, sample_rate)
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-i", wav_path,
                "-codec:a", "libopus", "-b:a", bitrate, opus_path,
            ],
            check=True,
        )
        return os.path.getsize(opus_path), common.ogg_audio_packets(opus_path)


# ==================================================
# Environment record
# ==================================================

def command_output(command: list[str]) -> str:
    try:
        return subprocess.run(
            command, capture_output=True, text=True, check=False
        ).stdout.strip()
    except OSError as error:
        return f"unavailable ({error})"


def libopus_version() -> dict[str, str]:
    """Version of the libopus that the ffmpeg binary actually links."""
    ldd = command_output(["ldd", command_output(["which", "ffmpeg"])])
    paths = [
        line.split("=>")[1].split("(")[0].strip()
        for line in ldd.splitlines()
        if "libopus" in line and "=>" in line
    ]
    if not paths:
        return {"path": "not found in ldd output", "version": "unknown"}
    library = ctypes.CDLL(paths[0])
    library.opus_get_version_string.restype = ctypes.c_char_p
    return {
        "path": os.path.realpath(paths[0]),
        "version": library.opus_get_version_string().decode(),
    }


def collect_environment() -> dict[str, object]:

    packages = {}
    for name in [
        "torch", "torchaudio", "torchcodec", "numpy", "pandas", "jiwer",
        "soundfile", "tqdm", "matplotlib", "encodec",
    ]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not installed"

    cuda = {
        "available": torch.cuda.is_available(),
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "device_used": str(common.device),
    }
    if torch.cuda.is_available():
        cuda["gpu"] = torch.cuda.get_device_name(0)
        cuda["compute_capability"] = ".".join(
            map(str, torch.cuda.get_device_capability(0))
        )
        cuda["driver"] = command_output([
            "nvidia-smi", "--query-gpu=driver_version",
            "--format=csv,noheader",
        ])

    torch_flags = {
        "cuda.matmul.allow_tf32": torch.backends.cuda.matmul.allow_tf32,
        "cudnn.allow_tf32": torch.backends.cudnn.allow_tf32,
        "cudnn.benchmark": torch.backends.cudnn.benchmark,
        "cudnn.deterministic": torch.backends.cudnn.deterministic,
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
    }

    try:
        from torchcodec._core import get_ffmpeg_library_versions
        torchcodec_ffmpeg = {
            k: str(v) for k, v in get_ffmpeg_library_versions().items()
        }
    except Exception as error:  # private API; record why it is missing
        torchcodec_ffmpeg = f"unavailable ({type(error).__name__})"

    checkpoint = (
        Path(torch.hub.get_dir()) / "checkpoints"
        / "wav2vec2_fairseq_base_ls960_asr_ls960.pth"
    )

    ffmpeg_version = command_output(["ffmpeg", "-hide_banner", "-version"])

    return {
        "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "packages": packages,
        "cuda": cuda,
        "torch_flags": torch_flags,
        "ffmpeg": {
            "binary": command_output(["which", "ffmpeg"]),
            "version": ffmpeg_version.splitlines()[0],
            "libraries": [
                line for line in ffmpeg_version.splitlines()
                if line.startswith("lib")
            ],
            "dpkg": command_output([
                "dpkg-query", "-W", "-f", "${Package} ${Version}\\n",
                "ffmpeg", "libopus0",
            ]).splitlines(),
        },
        "libopus_linked_by_ffmpeg": libopus_version(),
        "torchcodec_ffmpeg_libraries": torchcodec_ffmpeg,
        "wav2vec2_checkpoint": {
            "path": str(checkpoint),
            "sha256": file_hash(checkpoint) if checkpoint.exists() else "missing",
        },
        "frozen_standardisation_sha256": file_hash(
            Path(common.FROZEN_STANDARDISATION_PATH)
        ),
        "librispeech_root": os.path.realpath(common.DATA_ROOT),
        "git": {
            "head": command_output(["git", "rev-parse", "HEAD"]),
            "branch": command_output(["git", "branch", "--show-current"]),
            "status": command_output(["git", "status", "--porcelain"]).splitlines(),
        },
        "frozen_environment_note": (
            "The environment that produced the frozen results was not "
            "recorded in the repository; equivalence is established by "
            "reproduction, not by version matching."
        ),
    }


# ==================================================
# Reproduction
# ==================================================

def run_subset(dataset_name: str, num_utterances: int) -> dict[str, list[dict]]:

    dataset = common.load_dataset(dataset_name)
    sample_indices = common.select_indices(dataset)[:num_utterances]

    rows = {
        "asr": [], "signal": [], "representation": [],
        "packets": [], "determinism": [],
    }

    for sample_number, index in enumerate(
        tqdm(sample_indices, desc=dataset_name, unit="sample"), start=1
    ):
        (
            waveform,
            sample_rate,
            reference,
            speaker_id,
            chapter_id,
            utterance_id,
        ) = dataset[index]

        ids = {
            "dataset": dataset_name,
            "dataset_index": index,
            "speaker_id": speaker_id,
            "chapter_id": chapter_id,
            "utterance_id": utterance_id,
        }
        decoded_hashes = {}

        # ---- ASR: loop body of run_all_experiments.py -------------------
        duration_seconds = waveform.shape[-1] / sample_rate

        for condition in CONDITIONS:
            codec, bitrate = condition["codec"], condition["bitrate"]

            (
                processed_waveform,
                processed_sample_rate,
                original_size,
                compressed_size,
                compression_ratio,
            ) = common.process_audio(waveform, sample_rate, codec, bitrate)

            actual_bitrate_kbps = 8 * compressed_size / duration_seconds / 1000

            prediction = common.recognise(processed_waveform, processed_sample_rate)

            rows["asr"].append({
                **ids,
                "codec": codec,
                "bitrate": bitrate,
                "sample": sample_number,
                "reference": reference,
                "prediction": prediction,
                "wer": wer(reference, prediction),
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "actual_bitrate_kbps": actual_bitrate_kbps,
                "compression_ratio": compression_ratio,
                "num_samples": waveform.shape[-1],
                "processed_sample_rate": processed_sample_rate,
                "processed_num_samples": processed_waveform.shape[-1],
            })
            decoded_hashes[(codec, bitrate, "asr")] = tensor_hash(processed_waveform)

        # ---- Signal: loop body of signal_distortion_analysis.py ----------
        frequencies = np.linspace(0, sample_rate / 2, common.N_FFT // 2 + 1)

        for condition in CODEC_CONDITIONS:
            codec, bitrate = condition["codec"], condition["bitrate"]

            compressed_waveform, compressed_sr = common.compress_audio(
                waveform, sample_rate, codec, bitrate
            )
            decoded_hashes[(codec, bitrate, "signal")] = tensor_hash(compressed_waveform)
            decoded_num_samples = compressed_waveform.shape[-1]

            if compressed_sr != sample_rate:
                compressed_waveform = torchaudio.functional.resample(
                    compressed_waveform, compressed_sr, sample_rate
                )

            aligned_ref, aligned_comp, delay_samples = common.align_waveforms(
                waveform, compressed_waveform
            )

            reference_mag = common.magnitude_spectrogram(aligned_ref)
            processed_mag = common.magnitude_spectrogram(aligned_comp)

            dspec, lsd_db, _ = common.spectral_distortion(reference_mag, processed_mag)
            retained_bandwidth_hz, hf_power_change_db = common.bandwidth_measures(
                reference_mag, processed_mag, frequencies
            )

            rows["signal"].append({
                **ids,
                "codec": codec,
                "bitrate": bitrate,
                "spectral_distortion": dspec,
                "lsd_db": lsd_db,
                "retained_bandwidth_hz": retained_bandwidth_hz,
                "hf_power_change_db": hf_power_change_db,
                "estimated_delay_samples": delay_samples,
                "estimated_delay_ms": delay_samples / sample_rate * 1000.0,
                "reference_num_samples": waveform.shape[-1],
                "decoded_sample_rate": compressed_sr,
                "decoded_num_samples": decoded_num_samples,
                "resampled_num_samples": compressed_waveform.shape[-1],
                "aligned_num_samples": aligned_ref.shape[-1],
            })

        # ---- Representation: loop body of representation_analysis.py -----
        wav_features = common.extract_hidden_states(waveform, sample_rate)

        if sample_number <= REPEAT_UTTERANCES:
            repeat_features = common.extract_hidden_states(waveform, sample_rate)
            rows["determinism"].append({
                **ids,
                "check": "wav_hidden_state_repeat_max_abs_diff",
                "value": max(
                    float((wav_features[k] - repeat_features[k]).abs().max())
                    for k in common.LAYER_NAMES
                ),
            })

        for condition in CODEC_CONDITIONS:
            codec, bitrate = condition["codec"], condition["bitrate"]

            compressed_waveform, compressed_sr = common.compress_audio(
                waveform, sample_rate, codec, bitrate
            )
            decoded_hashes[(codec, bitrate, "representation")] = tensor_hash(
                compressed_waveform
            )

            compressed_features = common.extract_hidden_states(
                compressed_waveform, compressed_sr
            )

            row = {**ids, "codec": codec, "bitrate": bitrate}
            for layer_name in common.LAYER_NAMES:
                row[f"drift_{layer_name}"] = 1.0 - common.representation_similarity(
                    wav_features[layer_name],
                    compressed_features[layer_name],
                )
                row[f"sdrift_{layer_name}"] = 1.0 - common.representation_similarity(
                    common.standardise(wav_features[layer_name], layer_name),
                    common.standardise(compressed_features[layer_name], layer_name),
                )
            row["wav_frames"] = wav_features["layer_12"].shape[1]
            row["compressed_frames"] = compressed_features["layer_12"].shape[1]
            rows["representation"].append(row)

        # ---- Packets: encoding of opus_mode_check.py ---------------------
        for condition in CODEC_CONDITIONS:
            codec, bitrate = condition["codec"], condition["bitrate"]

            file_size, packets = encode_opus_file(waveform, sample_rate, bitrate)

            counts: dict[str, int] = {}
            for packet in packets:
                name = common.configuration_name(packet[0] >> 3)
                counts[name] = counts.get(name, 0) + 1
            for name, count in counts.items():
                rows["packets"].append({
                    **ids, "codec": codec, "bitrate": bitrate,
                    "configuration": name, "packets": count,
                })

            asr_size = next(
                r["compressed_size_bytes"] for r in rows["asr"]
                if r["dataset_index"] == index
                and r["codec"] == codec and r["bitrate"] == bitrate
            )
            rows["determinism"].append({
                **ids,
                "check": f"{codec}_{bitrate}_decoded_identical_across_encodes",
                "value": float(len({
                    decoded_hashes[(codec, bitrate, path)]
                    for path in ["asr", "signal", "representation"]
                }) == 1),
            })
            rows["determinism"].append({
                **ids,
                "check": f"{codec}_{bitrate}_file_size_identical_across_encodes",
                "value": float(file_size == asr_size),
            })

    return rows


# ==================================================
# Comparison
# ==================================================

def storage_rounding_bound(values: np.ndarray, significant_digits: int = 6) -> np.ndarray:
    """Largest error introduced by writing a value with %.<digits>g."""
    values = np.abs(values)
    bound = np.zeros_like(values)
    nonzero = values > 0
    exponent = np.floor(np.log10(values[nonzero]))
    bound[nonzero] = 0.5 * 10.0 ** (exponent - (significant_digits - 1))
    return bound


class Report:

    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def _add(self, **row) -> None:
        self.rows.append(row)

    def exact(self, check, subset, condition, field, new, frozen, note=""):
        new, frozen = list(new), list(frozen)
        mismatches = [
            i for i, (a, b) in enumerate(zip(new, frozen)) if a != b
        ]
        passed = len(new) == len(frozen) and len(new) > 0 and not mismatches
        if mismatches:
            i = mismatches[0]
            note = (
                f"{len(mismatches)} mismatch(es); first: new={new[i]!r} "
                f"frozen={frozen[i]!r}. {note}"
            ).strip()
        elif len(new) != len(frozen):
            note = f"length differs: new {len(new)}, frozen {len(frozen)}. {note}".strip()
        self._add(
            check=check, subset=subset, condition=condition, field=field,
            comparison="exact", n=len(new), n_exact=len(new) - len(mismatches),
            max_abs_error="", tolerance="exact",
            status="PASS" if passed else "FAIL", note=note,
        )

    def numeric(self, check, subset, condition, field, new, frozen,
                tolerance, relative=False, storage_bound=None, note=""):
        new = np.asarray(new, dtype=float)
        frozen = np.asarray(frozen, dtype=float)
        error = np.abs(new - frozen)
        if relative:
            measured = error / np.abs(frozen)
            tolerance_text = f"rel <= {tolerance:g}"
        elif storage_bound is not None:
            measured = error - storage_bound
            tolerance_text = f"<= %.6g rounding + {tolerance:g}"
        else:
            measured = error
            tolerance_text = f"abs <= {tolerance:g}"
        passed = (
            new.size > 0 and new.size == frozen.size
            and bool(np.all(np.isfinite(error)))
            and float(np.max(measured)) <= tolerance
        )
        self._add(
            check=check, subset=subset, condition=condition, field=field,
            comparison="tolerance", n=int(new.size),
            n_exact=int(np.sum(error == 0)),
            max_abs_error=float(np.max(error)) if error.size else float("nan"),
            tolerance=tolerance_text,
            status="PASS" if passed else "FAIL", note=note,
        )

    def info(self, check, subset, condition, field, value, note=""):
        self._add(
            check=check, subset=subset, condition=condition, field=field,
            comparison="info", n="", n_exact="", max_abs_error="",
            tolerance="", status="INFO", note=f"{value}. {note}".strip(" ."),
        )

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def aligned_frozen(new: pd.DataFrame, frozen: pd.DataFrame) -> pd.DataFrame:
    """Frozen rows in the order of the new rows (missing rows become NaN)."""
    return frozen.set_index("dataset_index").reindex(new["dataset_index"]).reset_index()


def compare_all(output_dir: Path = OUTPUT_DIR) -> pd.DataFrame:

    report = Report()

    new_asr = read_csv(output_dir / "new_asr_rows.csv")
    new_signal = read_csv(output_dir / "new_signal_rows.csv")
    new_rep = read_csv(output_dir / "new_representation_rows.csv")
    new_packets = read_csv(output_dir / "new_packet_modes.csv")
    new_determinism = read_csv(output_dir / "new_determinism_rows.csv")

    frozen_signal = read_csv(FROZEN_DIR / "signal_distortion_results.csv")
    frozen_rep = read_csv(FROZEN_DIR / "representation_similarity_results.csv")
    frozen_errors = read_csv(FROZEN_DIR / "error_analysis" / "per_utterance_errors.csv")
    frozen_modes = read_csv(FROZEN_DIR / "final_report" / "table_opus_modes.csv")

    for subset in list(dict.fromkeys(new_asr["dataset"])):

        frozen_asr = read_csv(FROZEN_DIR / f"{subset}_experiment_details.csv")
        subset_asr = new_asr[new_asr["dataset"] == subset]

        # ---- Selection ----------------------------------------------------
        new_order = (
            subset_asr[subset_asr["codec"] == "wav"]
            .sort_values("sample")["dataset_index"].tolist()
        )
        frozen_order = (
            frozen_asr[frozen_asr["codec"] == "wav"]
            .sort_values("sample")["dataset_index"].tolist()[:len(new_order)]
        )
        report.exact(
            "selection", subset, "all", "dataset_index (selection order)",
            new_order, frozen_order,
        )

        # ---- ASR ------------------------------------------------------------
        for condition in CONDITIONS:
            codec, bitrate = condition["codec"], condition["bitrate"]
            label = condition_label(codec, bitrate)

            new = subset_asr[
                (subset_asr["codec"] == codec) & (subset_asr["bitrate"] == bitrate)
            ].reset_index(drop=True)
            frozen = aligned_frozen(new, frozen_asr[
                (frozen_asr["codec"] == codec) & (frozen_asr["bitrate"] == bitrate)
            ])

            for field in [
                "sample", "speaker_id", "chapter_id", "utterance_id",
                "reference", "prediction",
                "original_size_bytes", "compressed_size_bytes",
            ]:
                report.exact("asr", subset, label, field, new[field], frozen[field])

            report.numeric("asr", subset, label, "wer (per utterance)",
                           new["wer"], frozen["wer"], TOL_WER)
            report.numeric(
                "asr", subset, label, "corpus WER over reproduced utterances",
                [jiwer.wer(new["reference"].tolist(), new["prediction"].tolist())],
                [jiwer.wer(frozen["reference"].tolist(), frozen["prediction"].tolist())],
                TOL_WER,
            )
            report.numeric("bitrate", subset, label, "actual_bitrate_kbps",
                           new["actual_bitrate_kbps"], frozen["actual_bitrate_kbps"],
                           TOL_RELATIVE_BITRATE, relative=True)
            report.numeric("bitrate", subset, label, "compression_ratio",
                           new["compression_ratio"], frozen["compression_ratio"],
                           TOL_RELATIVE_BITRATE, relative=True)

            # Waveform length: frozen WAV file size encodes the sample count
            report.exact(
                "waveform", subset, label,
                "num_samples = (frozen original_size_bytes - 78) / 2",
                new["num_samples"],
                (frozen["original_size_bytes"] - WAV_HEADER_BYTES) // WAV_BYTES_PER_SAMPLE,
            )
            report.info(
                "waveform", subset, label, "decoded sample rate seen by ASR",
                sorted(set(new["processed_sample_rate"])),
                "not stored in frozen outputs",
            )

            # Error counts: JiWER on the new transcripts vs the frozen
            # error_analysis.py counts (totals must match; S/D/I split can
            # differ by alignment tie-breaking, see final_report_tables.py)
            measures = [
                jiwer.process_words(r, p)
                for r, p in zip(new["reference"], new["prediction"])
            ]
            new_totals = [m.substitutions + m.deletions + m.insertions for m in measures]
            new_split = [(m.substitutions, m.deletions, m.insertions) for m in measures]

            if codec == "wav":
                errors = frozen_errors[
                    (frozen_errors["dataset"] == subset)
                    & (frozen_errors["codec"] == "opus")
                    & (frozen_errors["bitrate"] == "12k")
                ]
                prefix = "wav"
            else:
                errors = frozen_errors[
                    (frozen_errors["dataset"] == subset)
                    & (frozen_errors["codec"] == codec)
                    & (frozen_errors["bitrate"] == bitrate)
                ]
                prefix = "compressed"
            errors = aligned_frozen(new, errors)
            frozen_s = errors[f"{prefix}_substitutions"]
            frozen_d = errors[f"{prefix}_deletions"]
            frozen_i = errors[f"{prefix}_insertions"]
            report.exact(
                "errors", subset, label, "edit errors S+D+I (vs error_analysis.py)",
                new_totals, (frozen_s + frozen_d + frozen_i).tolist(),
            )
            split_differs = sum(
                a != b for a, b in zip(new_split, zip(frozen_s, frozen_d, frozen_i))
            )
            report.info(
                "errors", subset, label, "S/D/I split differences",
                f"{split_differs} utterance(s)",
                "JiWER vs error_analysis.py back-trace tie-breaking; totals are the check",
            )

        # ---- Signal ---------------------------------------------------------
        subset_signal = new_signal[new_signal["dataset"] == subset]
        frozen_subset_signal = frozen_signal[frozen_signal["dataset"] == subset]

        for condition in CODEC_CONDITIONS:
            codec, bitrate = condition["codec"], condition["bitrate"]
            label = condition_label(codec, bitrate)

            new = subset_signal[
                (subset_signal["codec"] == codec) & (subset_signal["bitrate"] == bitrate)
            ].reset_index(drop=True)
            frozen = aligned_frozen(new, frozen_subset_signal[
                (frozen_subset_signal["codec"] == codec)
                & (frozen_subset_signal["bitrate"] == bitrate)
            ])

            for field in [
                "speaker_id", "chapter_id", "utterance_id",
                "estimated_delay_samples", "retained_bandwidth_hz",
            ]:
                report.exact("signal", subset, label, field, new[field], frozen[field])
            for field in SIGNAL_FLOAT_FIELDS:
                report.numeric("signal", subset, label, field,
                               new[field], frozen[field], TOL_SIGNAL_ABS)

            report.info(
                "waveform", subset, label,
                "decoded length - reference length (16 kHz samples, min/max)",
                f"{int((new['resampled_num_samples'] - new['reference_num_samples']).min())}"
                f"/{int((new['resampled_num_samples'] - new['reference_num_samples']).max())}",
                "not stored in frozen outputs",
            )
            report.info(
                "waveform", subset, label,
                "aligned length - reference length (min/max)",
                f"{int((new['aligned_num_samples'] - new['reference_num_samples']).min())}"
                f"/{int((new['aligned_num_samples'] - new['reference_num_samples']).max())}",
                "not stored in frozen outputs",
            )

        # ---- Representation -------------------------------------------------
        subset_rep = new_rep[new_rep["dataset"] == subset]
        frozen_subset_rep = frozen_rep[frozen_rep["dataset"] == subset]

        for condition in CODEC_CONDITIONS:
            codec, bitrate = condition["codec"], condition["bitrate"]
            label = condition_label(codec, bitrate)

            new = subset_rep[
                (subset_rep["codec"] == codec) & (subset_rep["bitrate"] == bitrate)
            ].reset_index(drop=True)
            frozen = aligned_frozen(new, frozen_subset_rep[
                (frozen_subset_rep["codec"] == codec)
                & (frozen_subset_rep["bitrate"] == bitrate)
            ])

            for field in ["speaker_id", "chapter_id", "utterance_id"]:
                report.exact("representation", subset, label, field,
                             new[field], frozen[field])
            for field in DRIFT_FIELDS:
                frozen_values = frozen[field].to_numpy(dtype=float)
                report.numeric(
                    "representation", subset, label, field,
                    new[field], frozen_values, TOL_DRIFT_EXCESS,
                    storage_bound=storage_rounding_bound(frozen_values),
                )
            report.info(
                "waveform", subset, label, "Wav2Vec2 frames: compressed - WAV (min/max)",
                f"{int((new['compressed_frames'] - new['wav_frames']).min())}"
                f"/{int((new['compressed_frames'] - new['wav_frames']).max())}",
                "frozen code truncates to the shorter sequence",
            )

        # ---- Opus packet configuration --------------------------------------
        subset_packets = new_packets[new_packets["dataset"] == subset]
        num_utterances = subset_asr["dataset_index"].nunique()

        for condition in CODEC_CONDITIONS:
            bitrate = condition["bitrate"]
            label = condition_label("opus", bitrate)
            counts = (
                subset_packets[subset_packets["bitrate"] == bitrate]
                .groupby("configuration")["packets"].sum().to_dict()
            )
            if subset == "test-clean" and num_utterances == 50:
                frozen_counts = (
                    frozen_modes[frozen_modes["bitrate"] == bitrate]
                    .set_index("configuration")["packets"].to_dict()
                )
                names = sorted(set(counts) | set(frozen_counts))
                report.exact(
                    "packets", subset, label,
                    "TOC configuration packet counts (" + ", ".join(names) + ")",
                    [counts.get(n, 0) for n in names],
                    [frozen_counts.get(n, 0) for n in names],
                    "frozen table_opus_modes.csv covers the same 50 utterances",
                )
            else:
                report.info(
                    "packets", subset, label, "TOC configuration packet counts",
                    counts, "no frozen packet table for this subset/size",
                )

        # ---- Internal determinism ---------------------------------------------
        subset_det = new_determinism[new_determinism["dataset"] == subset]
        for check_name, group in subset_det.groupby("check", sort=False):
            if check_name.startswith("wav_hidden_state_repeat"):
                report.info(
                    "determinism", subset, "WAV", check_name,
                    f"max {group['value'].max():.3g} over {len(group)} utterances",
                    "GPU run-to-run variation",
                )
            else:
                report.exact(
                    "determinism", subset, "all", check_name,
                    group["value"].tolist(), [1.0] * len(group),
                    "independent encodes of the same utterance",
                )

    # ---- Frozen trees untouched -------------------------------------------
    hashes = json.loads((output_dir / "frozen_hashes.json").read_text())
    before = hashes["before"]
    for field, other in [
        ("src/ and results/ SHA-256 after run vs before", hashes["after"]),
        ("src/ and results/ SHA-256 at comparison time vs before", hash_tree()),
    ]:
        changed = sorted(
            path for path in set(before) | set(other)
            if before.get(path) != other.get(path)
        )
        report.exact(
            "frozen", "all", "all", field,
            [tree_digest(other)], [tree_digest(before)],
            f"{len(before)} files; changed: {changed[:5]}" if changed
            else f"{len(before)} files hashed",
        )

    return report.frame()


# ==================================================
# Markdown report
# ==================================================

def markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for _, row in frame.iterrows():
        cells = []
        for value in row:
            if isinstance(value, float):
                value = "" if np.isnan(value) else f"{value:.3g}"
            cells.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_markdown(report: pd.DataFrame, environment: dict, num_utterances: int,
                   path: Path) -> None:

    checks = report[report["status"] != "INFO"]
    failures = report[report["status"] == "FAIL"]
    verdict = "PASS" if failures.empty else "FAIL"

    main_rows = report[
        (report["check"] != "representation")
        | ~report["field"].isin(DRIFT_FIELDS)
    ]

    drift = report[report["field"].isin(DRIFT_FIELDS)].copy()
    drift["max_abs_error"] = drift["max_abs_error"].astype(float)
    drift_summary = (
        drift.assign(
            layer=drift["field"].str.replace("^s?drift_", "", regex=True),
            kind=np.where(drift["field"].str.startswith("sdrift"),
                          "standardised", "raw"),
        )
        .groupby(["layer", "kind"], sort=False)
        .agg(
            n=("n", "sum"),
            n_exact=("n_exact", "sum"),
            max_abs_error=("max_abs_error", "max"),
            status=("status", lambda s: "PASS" if (s == "PASS").all() else "FAIL"),
        )
        .reset_index()
    )

    cuda = environment["cuda"]
    lines = [
        "# Stage 1 equivalence report",
        "",
        f"**Verdict: {verdict}** — {len(checks) - len(failures)} of "
        f"{len(checks)} checks passed; {len(report) - len(checks)} "
        "informational rows.",
        "",
        f"Scope: first {num_utterances} utterances of the frozen 500-utterance "
        "selection of each subset; WAV, Opus 12k and Opus 8k through the "
        "frozen encoding path (ffmpeg libopus, default settings).",
        "",
        "## Environment",
        "",
        f"- Python {environment['python'].split()[0]} "
        f"({environment['python_executable']})",
        "- " + ", ".join(f"{k} {v}" for k, v in environment["packages"].items()),
        f"- {environment['ffmpeg']['version']}",
        f"- libopus linked by ffmpeg: {environment['libopus_linked_by_ffmpeg']['version']}",
        f"- CUDA {cuda['torch_cuda_version']}, cuDNN {cuda['cudnn_version']}, "
        f"{cuda.get('gpu', 'no GPU')} (driver {cuda.get('driver', '-')})",
        f"- Torch flags: {environment['torch_flags']}",
        f"- {environment['frozen_environment_note']}",
        "",
        "## Mismatches",
        "",
        markdown_table(failures) if not failures.empty else "None.",
        "",
        "## All checks (representation drift summarised below)",
        "",
        markdown_table(main_rows),
        "",
        "## Representation drift, every stored layer",
        "",
        "Aggregated over subsets and Opus conditions. Frozen values are "
        "stored with 6 significant digits; tolerance is that rounding plus "
        f"{TOL_DRIFT_EXCESS:g}. Per-condition rows are in equivalence_report.csv.",
        "",
        markdown_table(drift_summary),
        "",
    ]
    path.write_text("\n".join(lines))


# ==================================================
# Main
# ==================================================

def main() -> int:

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--num-utterances", type=int, default=NUM_UTTERANCES)
    parser.add_argument("--subsets", nargs="+", default=common.DATASET_NAMES)
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if Path("results").resolve() in OUTPUT_DIR.resolve().parents:
        raise RuntimeError("Refusing to write inside the frozen results/ directory")

    before = hash_tree()

    common.load_model()
    common.load_frozen_standardisation()

    environment = collect_environment()
    (OUTPUT_DIR / "environment.json").write_text(json.dumps(environment, indent=2))
    (OUTPUT_DIR / "requirements-lock.txt").write_text(
        command_output([sys.executable, "-m", "pip", "freeze"]) + "\n"
    )

    all_rows: dict[str, list[dict]] = {}
    for subset in args.subsets:
        for key, rows in run_subset(subset, args.num_utterances).items():
            all_rows.setdefault(key, []).extend(rows)

    for key, filename in [
        ("asr", "new_asr_rows.csv"),
        ("signal", "new_signal_rows.csv"),
        ("representation", "new_representation_rows.csv"),
        ("packets", "new_packet_modes.csv"),
        ("determinism", "new_determinism_rows.csv"),
    ]:
        pd.DataFrame(all_rows[key]).to_csv(OUTPUT_DIR / filename, index=False)

    after = hash_tree()
    (OUTPUT_DIR / "frozen_hashes.json").write_text(
        json.dumps({"before": before, "after": after}, indent=2)
    )

    report = compare_all(OUTPUT_DIR)
    report.to_csv(OUTPUT_DIR / "equivalence_report.csv", index=False)
    write_markdown(report, environment, args.num_utterances,
                   OUTPUT_DIR / "equivalence_report.md")

    failures = report[report["status"] == "FAIL"]
    checks = report[report["status"] != "INFO"]
    print(f"\n{len(checks) - len(failures)} / {len(checks)} checks passed")
    if not failures.empty:
        print(failures[["check", "subset", "condition", "field", "note"]].to_string())
    print(f"Report: {OUTPUT_DIR / 'equivalence_report.md'}")

    return 0 if failures.empty else 1


if __name__ == "__main__":
    sys.exit(main())
