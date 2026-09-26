"""
Zero-phase FIR low-pass for the matched bandwidth-removal control.

The filter is a linear-phase FIR of odd length L with exactly symmetric taps,
designed by frequency sampling of a target gain curve and a Kaiser window.
It is applied by linear convolution (float64 FFT) and the (L - 1) / 2 sample
delay of the symmetric FIR is removed exactly, so the applied operation is
zero-phase, preserves the waveform length and is deterministic.

The target curve and every design parameter are chosen by
paper/run_lowpass_validation.py (calibration on dev-clean) and frozen in a
JSON file together with the SHA-256 of the taps; load_filter() refuses a file
whose taps do not match the recorded hash.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import torch


def design_linear_phase_fir(
    freqs_hz: np.ndarray,
    gain_db: np.ndarray,
    sample_rate: int,
    num_taps: int,
    kaiser_beta: float,
    grid_size: int,
) -> np.ndarray:
    """
    Frequency-sampling design: the target amplitude (interpolated in dB onto
    a grid of grid_size // 2 + 1 points) is inverse-transformed as a real,
    zero-phase response, truncated to num_taps around lag 0 with a Kaiser
    window, made exactly symmetric and normalised to the target DC gain.
    """
    if num_taps % 2 == 0:
        raise ValueError("num_taps must be odd for a zero-phase (type I) FIR")
    if grid_size < 4 * num_taps:
        raise ValueError("grid_size should be at least 4 x num_taps")

    grid = np.linspace(0.0, sample_rate / 2.0, grid_size // 2 + 1)
    amplitude = 10.0 ** (np.interp(grid, freqs_hz, gain_db) / 20.0)
    impulse = np.fft.irfft(amplitude, grid_size)

    half = (num_taps - 1) // 2
    taps = np.concatenate([impulse[-half:], impulse[:half + 1]])
    taps = taps * np.kaiser(num_taps, kaiser_beta)
    taps = 0.5 * (taps + taps[::-1])          # exactly symmetric
    taps = taps * (amplitude[0] / taps.sum())  # DC gain equals the target
    return taps


def apply_zero_phase(waveform: torch.Tensor, taps: np.ndarray) -> torch.Tensor:
    """
    Filter every channel of a (channels, samples) waveform with the symmetric
    FIR and remove its (L - 1) / 2 delay exactly. Output has the input's
    shape and dtype. Samples beyond the ends are treated as zero.
    """
    if len(taps) % 2 == 0 or not np.array_equal(taps, taps[::-1]):
        raise ValueError("taps must be odd-length and exactly symmetric")

    signal = waveform.detach().cpu().double().numpy()
    num_samples = signal.shape[-1]
    half = (len(taps) - 1) // 2
    size = 1 << (num_samples + len(taps) - 2).bit_length()

    filtered = np.fft.irfft(
        np.fft.rfft(signal, size, axis=-1) * np.fft.rfft(taps, size), size, axis=-1
    )[..., half:half + num_samples]

    return torch.from_numpy(np.ascontiguousarray(filtered)).to(waveform.dtype)


def frequency_response_db(taps: np.ndarray, freqs_hz: np.ndarray,
                          sample_rate: int) -> np.ndarray:
    """Zero-phase amplitude response of a symmetric FIR, in dB."""
    half = (len(taps) - 1) // 2
    k = np.arange(1, half + 1)
    amplitude = taps[half] + 2.0 * np.cos(
        2.0 * np.pi * np.outer(freqs_hz, k) / sample_rate
    ) @ taps[half + 1:]
    return 20.0 * np.log10(np.maximum(np.abs(amplitude), 1e-300))


def taps_sha256(taps: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(taps, dtype="<f8").tobytes()).hexdigest()


def save_filter(path: Path, taps: np.ndarray, metadata: dict) -> str:
    """Write taps (exact float repr), their SHA-256 and metadata as JSON."""
    digest = taps_sha256(taps)
    path.write_text(json.dumps(
        {"taps_sha256": digest, "num_taps": len(taps), "taps": taps.tolist(),
         "metadata": metadata},
        indent=1,
    ))
    return digest


def load_filter(path: Path) -> tuple[np.ndarray, dict]:
    """Load a frozen filter; fails if the taps do not match their hash."""
    record = json.loads(Path(path).read_text())
    taps = np.asarray(record["taps"], dtype=np.float64)
    if taps_sha256(taps) != record["taps_sha256"]:
        raise ValueError(f"{path}: taps do not match the recorded SHA-256")
    return taps, record
