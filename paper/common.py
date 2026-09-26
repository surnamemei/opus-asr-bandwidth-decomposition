"""
Frozen ELEC5305 numerical logic, copied for the paper extension.

Every function below is a verbatim copy of a function in src/. The frozen
scripts cannot be imported because most of them run the full experiment at
import time, so the functions are copied instead. The source of each copy is
given in the comment above it; paper/tests/test_equivalence.py checks that
every copy is still AST-identical to its frozen original and that every
setting has the frozen value.

The copied functions read module-level names (model, labels, device,
standardisation, ...), exactly as they did in their original scripts. Call
load_model() and load_frozen_standardisation() before using them.

Nothing in this module writes to disk except temporary files.
"""

import os
import random
import subprocess
import tempfile
from typing import cast

import numpy as np
import torch
import torch.nn.functional as F
import torchaudio
from torchaudio.models import Wav2Vec2Model


# ==================================================
# Frozen settings (values from src/)
# ==================================================

DATA_ROOT = "data"
DATASET_NAMES = ["test-clean", "test-other"]

# Utterance selection: run_all_experiments.py and every analysis script
NUM_SAMPLES = 500
RANDOM_SEED = 5305

# Signal analysis: signal_distortion_analysis.py
N_FFT = 512
HOP_LENGTH = 160
WIN_LENGTH = 400
LOG_EPS = 1e-12
DYNAMIC_RANGE_DB = 80.0
BANDWIDTH_DROP_DB = 20.0
HF_BAND_HZ = (4000.0, 8000.0)
MAX_SHIFT_SAMPLES = 4000

# Representation analysis: representation_analysis.py
NUM_TRANSFORMER_LAYERS = 12
LAYER_NAMES = ["conv"] + [
    f"layer_{i}" for i in range(1, NUM_TRANSFORMER_LAYERS + 1)
]

# Written by representation_analysis.py; loaded, never re-estimated
FROZEN_STANDARDISATION_PATH = os.path.join(
    "results", "representation_standardisation.pt"
)


# ==================================================
# Model state read by the copied functions
# ==================================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = None                 # Wav2Vec2 (run_all_experiments / representation_analysis)
labels = None                # CTC labels (run_all_experiments)
target_sample_rate = None    # run_all_experiments spelling
TARGET_SAMPLE_RATE = None    # representation_analysis spelling
standardisation = None       # per-layer (mean, std) from the frozen .pt file


def load_model() -> None:
    """Load the fixed Wav2Vec2 model exactly as the frozen scripts do."""
    global model, labels, target_sample_rate, TARGET_SAMPLE_RATE

    bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
    model = cast(Wav2Vec2Model, bundle.get_model()).to(device)
    model.eval()

    labels = bundle.get_labels()
    target_sample_rate = int(bundle.sample_rate)
    TARGET_SAMPLE_RATE = target_sample_rate


def load_frozen_standardisation(path: str = FROZEN_STANDARDISATION_PATH) -> None:
    """Load the frozen per-layer standardisation statistics."""
    global standardisation
    standardisation = torch.load(path)


# ==================================================
# Utterance selection
# ==================================================

# Copied verbatim from src/representation_analysis.py: load_dataset()
def load_dataset(dataset_name: str):
    return torchaudio.datasets.LIBRISPEECH(
        root=DATA_ROOT,
        url=dataset_name,
        download=False,
    )

# Copied verbatim from src/representation_analysis.py: select_indices()
def select_indices(dataset) -> list[int]:
    random.seed(RANDOM_SEED)
    return random.sample(
        range(len(dataset)),
        k=min(NUM_SAMPLES, len(dataset)),
    )


# ==================================================
# Wav2Vec2 inference and greedy CTC decoding
# ==================================================

# Copied verbatim from src/run_all_experiments.py: decode()
def decode(emissions):
    token_ids = torch.argmax(emissions, dim=-1)[0]

    blank_id = 0
    collapsed_ids = []
    previous_id = None

    for token_id in token_ids.tolist():
        if token_id != previous_id:
            if token_id != blank_id:
                collapsed_ids.append(token_id)

        previous_id = token_id

    transcript = "".join(labels[i] for i in collapsed_ids)

    return transcript.replace("|", " ").strip()

# Copied verbatim from src/run_all_experiments.py: recognise()
def recognise(waveform, sample_rate):
    if sample_rate != target_sample_rate:
        waveform = torchaudio.functional.resample(
            waveform,
            sample_rate,
            target_sample_rate
        )

    waveform = waveform.to(device)

    with torch.inference_mode():
        emissions, _ = model(waveform)

    return decode(emissions)


# ==================================================
# Codec invocation
# ==================================================

# Copied verbatim from src/run_all_experiments.py: process_audio()
def process_audio(waveform, sample_rate, codec, bitrate):
    """
    Returns:
        processed_waveform
        processed_sample_rate
        original_size
        compressed_size
        compression_ratio
    """

    with tempfile.TemporaryDirectory() as temp_dir:

        wav_path = os.path.join(temp_dir, "input.wav")

        torchaudio.save(
            wav_path,
            waveform,
            sample_rate
        )

        original_size = os.path.getsize(wav_path)

        # ------------------------------
        # WAV baseline
        # ------------------------------
        if codec == "wav":
            processed_waveform = waveform
            processed_sample_rate = sample_rate
            compressed_size = original_size
            compression_ratio = 1.0

            return (
                processed_waveform,
                processed_sample_rate,
                original_size,
                compressed_size,
                compression_ratio,
            )

        # ------------------------------
        # MP3
        # ------------------------------
        if codec == "mp3":
            output_path = os.path.join(temp_dir, "compressed.mp3")

            command = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                wav_path,
                "-codec:a",
                "libmp3lame",
                "-b:a",
                bitrate,
                output_path,
            ]

        # ------------------------------
        # Opus
        # ------------------------------
        elif codec == "opus":
            output_path = os.path.join(temp_dir, "compressed.opus")

            command = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                wav_path,
                "-codec:a",
                "libopus",
                "-b:a",
                bitrate,
                output_path,
            ]

        else:
            raise ValueError(f"Unsupported codec: {codec}")

        subprocess.run(
            command,
            check=True
        )

        compressed_size = os.path.getsize(output_path)

        processed_waveform, processed_sample_rate = torchaudio.load(
            output_path
        )

        compression_ratio = original_size / compressed_size

        return (
            processed_waveform,
            processed_sample_rate,
            original_size,
            compressed_size,
            compression_ratio,
        )

# Copied verbatim from src/signal_distortion_analysis.py: compress_audio()
def compress_audio(waveform, sample_rate, codec, bitrate):
    """Encode with FFmpeg and decode back to a waveform."""

    encoders = {"mp3": "libmp3lame", "opus": "libopus"}

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.wav")
        output_path = os.path.join(temp_dir, f"compressed.{codec}")

        torchaudio.save(input_path, waveform, sample_rate)

        command = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", input_path,
            "-codec:a", encoders[codec],
            "-b:a", bitrate,
            output_path,
        ]
        subprocess.run(command, check=True)

        compressed_waveform, compressed_sr = torchaudio.load(output_path)

    return compressed_waveform, int(compressed_sr)


# ==================================================
# Alignment and signal metrics
# ==================================================

# Copied verbatim from src/signal_distortion_analysis.py: align_waveforms()
def align_waveforms(reference, processed, max_shift_samples=MAX_SHIFT_SAMPLES):
    """
    Align processed audio to reference using normalised cross-correlation
    over a limited lag range. The correlation for every lag is computed at
    once with an FFT; the normalisation uses the energy of the overlapping
    segments, so the score is identical to the direct sliding computation.

    Positive delay means the processed signal is delayed relative to the
    reference.
    """

    ref = reference.mean(dim=0).cpu().double().numpy()
    proc = processed.mean(dim=0).cpu().double().numpy()

    n_ref = len(ref)
    n_proc = len(proc)
    max_shift = min(max_shift_samples, n_ref - 1, n_proc - 1)

    n_fft = 1 << int(np.ceil(np.log2(n_ref + n_proc - 1)))
    correlation = np.fft.irfft(
        np.fft.rfft(proc, n_fft) * np.conj(np.fft.rfft(ref, n_fft)),
        n_fft,
    )

    ref_energy = np.concatenate([[0.0], np.cumsum(ref ** 2)])
    proc_energy = np.concatenate([[0.0], np.cumsum(proc ** 2)])

    best_lag = 0
    best_score = -np.inf

    for lag in range(-max_shift, max_shift + 1):
        if lag >= 0:
            length = min(n_ref, n_proc - lag)
            dot = correlation[lag]
            energy = ref_energy[length] * (
                proc_energy[lag + length] - proc_energy[lag]
            )
        else:
            shift = -lag
            length = min(n_proc, n_ref - shift)
            dot = correlation[n_fft + lag]
            energy = proc_energy[length] * (
                ref_energy[shift + length] - ref_energy[shift]
            )

        if length < 100 or energy <= 0.0:
            continue

        score = dot / np.sqrt(energy)
        if score > best_score:
            best_score = score
            best_lag = lag

    ref_t = reference.mean(dim=0)
    proc_t = processed.mean(dim=0)

    if best_lag >= 0:
        aligned_processed = proc_t[best_lag:]
        aligned_reference = ref_t
    else:
        aligned_reference = ref_t[-best_lag:]
        aligned_processed = proc_t

    length = min(len(aligned_reference), len(aligned_processed))

    return (
        aligned_reference[:length].unsqueeze(0),
        aligned_processed[:length].unsqueeze(0),
        best_lag,
    )

# Copied verbatim from src/signal_distortion_analysis.py: magnitude_spectrogram()
def magnitude_spectrogram(waveform):
    window = torch.hann_window(WIN_LENGTH)
    stft = torch.stft(
        waveform.squeeze(0),
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        win_length=WIN_LENGTH,
        window=window,
        return_complex=True,
    )
    return torch.abs(stft)

# Copied verbatim from src/signal_distortion_analysis.py: spectral_distortion()
def spectral_distortion(reference_mag, processed_mag):
    """
    Returns:
        dspec:  mean squared log-spectral difference (dB^2), feedback point 15
        lsd_db: log-spectral distance, RMS over frequency then mean over
                frames (dB)
        dfrequency: mean absolute log-spectral difference per frequency
                bin (dB), feedback point 16
    """

    ref_log = 20.0 * torch.log10(reference_mag + LOG_EPS)
    proc_log = 20.0 * torch.log10(processed_mag + LOG_EPS)

    floor = ref_log.max() - DYNAMIC_RANGE_DB
    ref_log = torch.clamp(ref_log, min=floor)
    proc_log = torch.clamp(proc_log, min=floor)

    difference = proc_log - ref_log

    dspec = torch.mean(difference ** 2)
    lsd_db = torch.mean(torch.sqrt(torch.mean(difference ** 2, dim=0)))
    dfrequency = torch.mean(torch.abs(difference), dim=1)

    return float(dspec), float(lsd_db), dfrequency.numpy()

# Copied verbatim from src/signal_distortion_analysis.py: bandwidth_measures()
def bandwidth_measures(reference_mag, processed_mag, frequencies):
    """
    Returns:
        retained_bandwidth_hz: highest frequency where the codec keeps
            long-term power within BANDWIDTH_DROP_DB of the reference
            (feedback point 17)
        hf_power_change_db: codec / reference power in HF_BAND_HZ (dB)
    """

    ref_power = torch.mean(reference_mag ** 2, dim=1).double()
    proc_power = torch.mean(processed_mag ** 2, dim=1).double()

    ratio_db = 10.0 * torch.log10(
        (proc_power + LOG_EPS) / (ref_power + LOG_EPS)
    )

    retained = torch.where(ratio_db > -BANDWIDTH_DROP_DB)[0]
    if len(retained) == 0:
        retained_bandwidth_hz = 0.0
    else:
        retained_bandwidth_hz = float(frequencies[int(retained[-1])])

    band = (frequencies >= HF_BAND_HZ[0]) & (frequencies <= HF_BAND_HZ[1])
    band = torch.from_numpy(band)
    hf_power_change_db = 10.0 * torch.log10(
        (proc_power[band].sum() + LOG_EPS) / (ref_power[band].sum() + LOG_EPS)
    )

    return retained_bandwidth_hz, float(hf_power_change_db)


# ==================================================
# Hidden states and representation drift
# ==================================================

# Copied verbatim from src/representation_analysis.py: extract_hidden_states()
def extract_hidden_states(
    input_waveform: torch.Tensor,
    input_sample_rate: int,
) -> dict[str, torch.Tensor]:

    if input_sample_rate != TARGET_SAMPLE_RATE:
        input_waveform = torchaudio.functional.resample(
            input_waveform, input_sample_rate, TARGET_SAMPLE_RATE
        )

    prepared = input_waveform.to(device)

    with torch.inference_mode():
        conv_features, _ = model.feature_extractor(prepared, None)
        layer_features, _ = model.extract_features(prepared)

    selected = {"conv": conv_features.detach().cpu()}

    for layer_number in range(1, NUM_TRANSFORMER_LAYERS + 1):
        selected[f"layer_{layer_number}"] = (
            layer_features[layer_number - 1].detach().cpu()
        )

    return selected

# Copied verbatim from src/representation_analysis.py: representation_similarity()
def representation_similarity(
    reference_representation: torch.Tensor,
    compressed_representation: torch.Tensor,
) -> float:

    min_frames = min(
        reference_representation.shape[1],
        compressed_representation.shape[1],
    )

    frame_similarity = F.cosine_similarity(
        reference_representation[:, :min_frames, :],
        compressed_representation[:, :min_frames, :],
        dim=-1,
    )

    return float(frame_similarity.mean().item())

# Copied verbatim from src/representation_analysis.py: standardise()
def standardise(
    representation: torch.Tensor,
    layer_name: str,
) -> torch.Tensor:
    mean, std = standardisation[layer_name]
    return (representation - mean) / std


# ==================================================
# Opus packet configuration
# ==================================================

# Copied verbatim from src/opus_mode_check.py: configuration_name()
def configuration_name(config: int) -> str:
    """RFC 6716 Table 2."""
    if config < 12:
        return "SILK-" + ["NB", "MB", "WB"][config // 4]
    if config < 16:
        return "Hybrid-" + ["SWB", "FB"][(config - 12) // 2]
    return "CELT-" + ["NB", "WB", "SWB", "FB"][(config - 16) // 4]

# Copied verbatim from src/opus_mode_check.py: ogg_audio_packets()
def ogg_audio_packets(path: str) -> list[bytes]:
    """Split an Ogg Opus file into packets; drop OpusHead and OpusTags."""
    data = open(path, "rb").read()
    packets, buffer, position = [], b"", 0
    while position < len(data):
        assert data[position:position + 4] == b"OggS"
        num_segments = data[position + 26]
        lacing = data[position + 27:position + 27 + num_segments]
        body = position + 27 + num_segments
        for size in lacing:
            buffer += data[body:body + size]
            body += size
            if size < 255:
                packets.append(buffer)
                buffer = b""
        position = body
    return packets[2:]
