"""
A1: the orthogonal projection-based decomposition (OPD) target component of BSS Eval, as used by
Iwamoto et al. (Interspeech 2022) and Ochiai et al. (IEEE TASLP 2024), adapted to codec output.

    project(reference, estimate)        -> the linear component (length T), filter taps and checks

The algorithm is that of the BSS Eval reference code (mir_eval.separation._project), reimplemented
in numpy: both signals zero-padded by L - 1, the Gram matrix of the delayed reference from its FFT
autocorrelation (Toeplitz), the inner products with the estimate from the FFT cross-correlation, an
exact solve with a least-squares fallback, and the filtered reference as the projection. L = 512
basis vectors, as in BSS Eval and Ochiai et al.

The one adaptation (A1_METHOD_NOTE.md, section 3.2): the delay span is centred, tau = -256 ... +255,
instead of 0 ... 511. This is implemented as in BSS Eval: delay the estimate by CENTRE samples,
project on the causal span 0 ... L - 1, and advance the result. The projection is restricted to the
T samples of the reference.
"""

import numpy as np

L = 512                      # number of basis vectors (BSS Eval default; Ochiai et al. 2024)
CENTRE = L // 2              # centred span: tau = -256 ... +255
SAMPLE_RATE = 16000


def _correlations(reference: np.ndarray, estimate: np.ndarray, flen: int):
    """mir_eval._project, steps 1-2: Gram matrix G (flen x flen) and inner products D (flen)."""
    n = reference.size
    ref = np.concatenate([reference, np.zeros(flen - 1)])
    est = np.concatenate([estimate, np.zeros(flen - 1)])
    n_fft = int(2 ** np.ceil(np.log2(n + flen - 1.0)))
    sf = np.fft.rfft(ref, n=n_fft)
    sef = np.fft.rfft(est, n=n_fft)
    ssf = np.fft.irfft(sf * np.conj(sf), n=n_fft)            # autocorrelation of the reference
    ssef = np.fft.irfft(sf * np.conj(sef), n=n_fft)          # correlation of the reference with the estimate
    column = np.concatenate([[ssf[0]], ssf[-1:-flen:-1]])    # mir_eval: toeplitz(c=[r0, r-1, ...], r=r[:flen])
    row = ssf[:flen]
    index = np.subtract.outer(np.arange(flen), np.arange(flen))
    gram = np.where(index >= 0, column[np.abs(index)], row[np.abs(index)])
    inner = np.concatenate([[ssef[0]], ssef[-1:-flen:-1]])   # D[tau] = <reference delayed by tau, estimate>
    return gram, inner, ref


def _solve(gram: np.ndarray, inner: np.ndarray) -> tuple[np.ndarray, bool]:
    """mir_eval._project, step 3: exact solve, least-squares fallback if the Gram matrix is singular."""
    try:
        return np.linalg.solve(gram, inner), False
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(gram, inner, rcond=None)[0], True


def causal_projection(reference: np.ndarray, estimate: np.ndarray, flen: int = L) -> dict:
    """BSS Eval's projection on the span of the reference delayed by 0 ... flen - 1 (length T + flen - 1)."""
    reference = np.asarray(reference, dtype=np.float64).reshape(-1)
    estimate = np.asarray(estimate, dtype=np.float64).reshape(-1)
    if reference.size != estimate.size:
        raise ValueError("reference and estimate must have the same length")
    gram, inner, ref = _correlations(reference, estimate, flen)
    taps, fallback = _solve(gram, inner)
    n = reference.size + flen - 1
    n_fft = int(2 ** np.ceil(np.log2(n + flen - 1.0)))
    projection = np.fft.irfft(np.fft.rfft(taps, n=n_fft) * np.fft.rfft(ref, n=n_fft), n=n_fft)[:n]
    residual = float(np.linalg.norm(gram @ taps - inner) / max(np.linalg.norm(inner), 1e-300))
    return {"projection": projection, "taps": taps, "lstsq_fallback": fallback,
            "normal_equation_residual": residual}


def project(reference: np.ndarray, estimate: np.ndarray, centre: int = CENTRE, flen: int = L) -> dict:
    """
    The A1 linear component of `estimate` given `reference` (both 16 kHz, same length T): the OPD
    target component on the centred span tau = -centre ... flen - 1 - centre, restricted to the T
    samples of the reference. Returns the component, the taps (index k <-> delay k - centre) and
    the numerical checks.
    """
    reference = np.asarray(reference, dtype=np.float64).reshape(-1)
    estimate = np.asarray(estimate, dtype=np.float64).reshape(-1)
    t = reference.size
    delayed_estimate = np.concatenate([np.zeros(centre), estimate])
    padded_reference = np.concatenate([reference, np.zeros(centre)])
    out = causal_projection(padded_reference, delayed_estimate, flen)
    component = out["projection"][centre:centre + t]
    return {"component": component, "taps": out["taps"], "lstsq_fallback": out["lstsq_fallback"],
            "normal_equation_residual": out["normal_equation_residual"]}


# ==================================================
# Descriptors of a linear component (signal-only)
# ==================================================

def nmse_db(target: np.ndarray, approximation: np.ndarray) -> float:
    """Energy of (target - approximation) relative to the energy of target, in dB."""
    target = np.asarray(target, dtype=np.float64).reshape(-1)
    approximation = np.asarray(approximation, dtype=np.float64).reshape(-1)
    return float(10 * np.log10(np.sum((target - approximation) ** 2) / max(np.sum(target ** 2), 1e-300)))


def response(taps: np.ndarray, centre: int = CENTRE, n_fft: int = 4096) -> tuple[np.ndarray, np.ndarray]:
    """Frequency response of the centred filter: H(f) = sum_k taps[k] exp(-j 2 pi f (k - centre) / fs)."""
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / SAMPLE_RATE)
    spectrum = np.fft.rfft(np.asarray(taps, dtype=np.float64), n=n_fft) * np.exp(2j * np.pi * freqs * centre / SAMPLE_RATE)
    return freqs, spectrum


def filter_descriptors(taps: np.ndarray, centre: int = CENTRE) -> dict:
    """Gain over 0.5-2 kHz, magnitude at fixed frequencies (absolute and relative), and linear delay."""
    freqs, h = response(taps, centre)
    mag_db = 20 * np.log10(np.maximum(np.abs(h), 1e-12))
    band = (freqs >= 500.0) & (freqs <= 2000.0)
    gain = float(np.mean(mag_db[band]))
    out = {"gain_0p5_2k_db": gain}
    for hz in [2000.0, 2500.0, 3000.0, 3500.0, 4000.0]:
        k = int(np.argmin(np.abs(freqs - hz)))
        out[f"mag_{int(hz)}_db"] = float(mag_db[k])
        out[f"rel_{int(hz)}_db"] = float(mag_db[k] - gain)
    fit = (freqs >= 500.0) & (freqs <= 3000.0)
    phase = np.unwrap(np.angle(h))
    slope = np.polyfit(2 * np.pi * freqs[fit] / SAMPLE_RATE, phase[fit], 1)[0]
    out["linear_delay_samples"] = float(-slope)
    out["peak_delay_samples"] = int(np.argmax(np.abs(taps)) - centre)
    return out
