"""
Stage 3 audio conditions and signal-level controls.

Every condition is generated from the same LibriSpeech utterance (paired
design). All conditions are 16 kHz, mono, float32, and have exactly the
input length. No level normalisation is applied to any condition: every
signal is presented to the recognisers at its physical output level.

Primary conditions
    REF        original LibriSpeech waveform (16-bit FLAC, exact float)
    LP         frozen Stage 2B zero-phase low-pass (taps SHA-256 583c66a1...)
    OPUS       Opus 8 kbps, frozen prior-study encoder settings (SILK-NB;
               packets byte-identical to the ELEC5305 Opus 8k condition)
    SILK       SILK-NB at 40 kbps, signal=voice (the Stage 2B "SILK-NB
               linear reference" condition: SILK narrowband coding with
               minimal coding distortion)

Negative controls (secondary, pre-declared)
    NEG_LP     mild zero-phase low-pass designed with the same procedure,
               flat to 7.0 kHz; expected ASR-equivalent to REF
    NEG_CODEC  Opus 64 kbps, frozen settings (CELT-WB); the prior study's
               transparent condition; tests the codec decode path

Codec outputs are decoded by the frozen torchaudio.load path (48 kHz) and
resampled to 16 kHz with torchaudio.functional.resample, exactly as in the
frozen pipeline. Signals are not re-aligned before recognition (frozen
convention); alignment lags are recorded.
"""

import hashlib

import numpy as np
import torch
import torchaudio

import common
import lowpass
import opus_direct
import run_lowpass_validation as stage2b


SAMPLE_RATE = 16000
FREQS = stage2b.FREQS

FROZEN_LP_PATH = stage2b.FILTER_PATH
FROZEN_LP_SHA256 = "583c66a169d31e27cf2250c8dd475d5cc74f7d590a8364ee9ffde463d69b1a16"

PRIMARY_CONDITIONS = ["REF", "LP", "OPUS", "SILK"]
CONTROL_CONDITIONS = ["NEG_LP", "NEG_CODEC"]
CONDITIONS = PRIMARY_CONDITIONS + CONTROL_CONDITIONS

CODEC_SETTINGS = {
    "OPUS": opus_direct.EncoderSettings(bitrate_bps=8000, bandwidth="NB"),
    "SILK": opus_direct.EncoderSettings(bitrate_bps=40000, bandwidth="NB", signal="voice"),
    "NEG_CODEC": opus_direct.EncoderSettings(bitrate_bps=64000),
}
EXPECTED_CONFIGURATION = {"OPUS": "SILK-NB", "SILK": "SILK-NB", "NEG_CODEC": "CELT-WB"}

# Negative-control low-pass: same design routine and parameters as the
# frozen LP, target flat to 7.0 kHz with a linear-in-dB roll-off to the
# stopband floor at 7.6 kHz. Fixed before any ASR decoding.
NEG_LP_DESIGN = {
    "passband_edge_hz": 7000.0,
    "stopband_edge_hz": 7600.0,
    "stopband_db": -80.0,
    "num_taps": 1023,
    "kaiser_beta": 8.0,
    "design_grid": 16384,
}

# Pairs whose pooled cross-spectra are accumulated (reference -> processed)
TRANSFER_PAIRS = (
    [("REF", c) for c in CONDITIONS if c != "REF"] + [("LP", "OPUS"), ("LP", "SILK")]
)

ACTIVE_FRAME_RANGE_DB = 40.0     # frames within 40 dB of the utterance's loudest frame
ENVELOPE_BANDS_HZ = [(0.0, 500.0), (500.0, 1000.0), (1000.0, 2000.0), (2000.0, 4000.0)]


# ==================================================
# Filters
# ==================================================

def load_filters() -> dict[str, np.ndarray]:
    taps, record = lowpass.load_filter(FROZEN_LP_PATH)
    if record["taps_sha256"] != FROZEN_LP_SHA256:
        raise RuntimeError("frozen Stage 2B filter hash mismatch")
    d = NEG_LP_DESIGN
    neg_taps = lowpass.design_linear_phase_fir(
        np.array([0.0, d["passband_edge_hz"], d["stopband_edge_hz"], SAMPLE_RATE / 2]),
        np.array([0.0, 0.0, d["stopband_db"], d["stopband_db"]]),
        SAMPLE_RATE, d["num_taps"], d["kaiser_beta"], d["design_grid"],
    )
    return {"LP": taps, "NEG_LP": neg_taps}


def filter_hashes(filters: dict[str, np.ndarray]) -> dict[str, str]:
    return {name: lowpass.taps_sha256(taps) for name, taps in filters.items()}


# ==================================================
# Condition generation
# ==================================================

def tensor_sha256(waveform: torch.Tensor) -> str:
    return hashlib.sha256(
        waveform.detach().cpu().contiguous().numpy().astype("<f4").tobytes()
    ).hexdigest()


def codec_round_trip(waveform: torch.Tensor, settings: opus_direct.EncoderSettings):
    result = opus_direct.encode(waveform, SAMPLE_RATE, settings)
    decoded, decoded_rate = opus_direct.decode_frozen_path(result.ogg)
    if decoded_rate != SAMPLE_RATE:
        decoded = torchaudio.functional.resample(decoded, decoded_rate, SAMPLE_RATE)
    configurations: dict[str, int] = {}
    for packet in result.packets:
        name = opus_direct.packet_info(packet)["configuration"]
        configurations[name] = configurations.get(name, 0) + 1
    info = {
        "decoded_sample_rate": decoded_rate,
        "num_packets": len(result.packets),
        "ogg_bytes": len(result.ogg),
        "ogg_sha256": hashlib.sha256(result.ogg).hexdigest(),
        "configurations": configurations,
        "measured_bitrate_kbps": 8 * len(result.ogg) / (waveform.shape[-1] / SAMPLE_RATE) / 1000,
    }
    return decoded.to(torch.float32), info


def generate_conditions(waveform: torch.Tensor, filters: dict[str, np.ndarray]):
    """All conditions of one utterance: {name: (waveform (1, N) float32, info)}."""
    if waveform.dim() != 2 or waveform.shape[0] != 1:
        raise ValueError("expected a mono (1, N) waveform")
    out = {"REF": (waveform.to(torch.float32), {})}
    for name in ["LP", "NEG_LP"]:
        out[name] = (lowpass.apply_zero_phase(waveform, filters[name]).to(torch.float32), {})
    for name, settings in CODEC_SETTINGS.items():
        out[name] = codec_round_trip(waveform, settings)
    return {name: out[name] for name in CONDITIONS}


# ==================================================
# Audio statistics (03_audio_manifest)
# ==================================================

def audio_stats(name: str, processed: torch.Tensor, reference: torch.Tensor, info: dict) -> dict:
    x = processed.detach().cpu().double().numpy().reshape(-1)
    ref = reference.detach().cpu().double().numpy().reshape(-1)
    rms = float(np.sqrt(np.mean(x ** 2)))
    ref_rms = float(np.sqrt(np.mean(ref ** 2)))
    _, _, lag = common.align_waveforms(reference, processed)
    row = {
        "condition": name,
        "sample_rate": SAMPLE_RATE,
        "channels": processed.shape[0],
        "num_samples": x.size,
        "duration_s": x.size / SAMPLE_RATE,
        "length_equals_ref": x.size == ref.size,
        "input_rms_dbfs": 20 * np.log10(max(ref_rms, 1e-12)),
        "output_rms_dbfs": 20 * np.log10(max(rms, 1e-12)),
        "rms_change_db": 20 * np.log10(max(rms, 1e-12) / max(ref_rms, 1e-12)),
        "peak": float(np.max(np.abs(x))),
        "clip_count": int(np.sum(np.abs(x) >= 1.0)),
        "nonfinite_count": int(np.sum(~np.isfinite(x))),
        "lag_vs_ref_samples": int(lag),
        "waveform_sha256": tensor_sha256(processed),
    }
    if info:
        configurations = info["configurations"]
        expected = EXPECTED_CONFIGURATION[name]
        row.update({
            "num_packets": info["num_packets"],
            "ogg_bytes": info["ogg_bytes"],
            "ogg_sha256": info["ogg_sha256"],
            "measured_bitrate_kbps": info["measured_bitrate_kbps"],
            "expected_configuration": expected,
            "share_expected_configuration": configurations.get(expected, 0) / info["num_packets"],
            "configurations": ";".join(f"{k}:{v}" for k, v in sorted(configurations.items())),
        })
    return row


# ==================================================
# Signal controls and exploratory features (09_signal_metrics)
# ==================================================

def mean_coherence(reference: torch.Tensor, processed: torch.Tensor, up_to_hz: float = 3500.0) -> float:
    accumulator = stage2b.TransferAccumulator()
    accumulator.add(reference, processed)
    coherence = accumulator.results()["coherence"]
    return float(np.mean(coherence[FREQS <= up_to_hz]))


def reference_features(reference: torch.Tensor) -> dict:
    """Descriptive properties of the clean utterance (exploratory, Step 12)."""
    spectrum = stage2b.stft(reference)
    power = np.abs(spectrum) ** 2
    frame_energy = power.sum(axis=0)
    frame_db = 10 * np.log10(frame_energy + 1e-20)
    active = frame_db >= frame_db.max() - ACTIVE_FRAME_RANGE_DB

    centroid = (FREQS[:, None] * power).sum(axis=0) / (frame_energy + 1e-20)
    band = (FREQS >= 100) & (FREQS <= 7000)
    flatness = np.exp(np.mean(np.log(power[band] + 1e-20), axis=0)) / (
        np.mean(power[band], axis=0) + 1e-20)
    log_power = 10 * np.log10(power + 1e-20)
    flux = np.concatenate([[0.0], np.mean(np.maximum(np.diff(log_power, axis=1), 0.0), axis=0)])

    # Voicing: normalised autocorrelation peak for lags of 2.5-16 ms (62.5-400 Hz)
    x = reference.detach().cpu().double().numpy().reshape(-1)
    frames = np.lib.stride_tricks.sliding_window_view(x, common.WIN_LENGTH)[::common.HOP_LENGTH]
    frames = frames - frames.mean(axis=1, keepdims=True)
    spectrum_ac = np.fft.rfft(frames, 2 * common.WIN_LENGTH, axis=1)
    autocorr = np.fft.irfft(np.abs(spectrum_ac) ** 2, axis=1)[:, :common.WIN_LENGTH]
    peak = autocorr[:, 40:257].max(axis=1) / (autocorr[:, 0] + 1e-20)
    time_frame_db = 10 * np.log10(autocorr[:, 0] + 1e-20)
    time_active = time_frame_db >= time_frame_db.max() - ACTIVE_FRAME_RANGE_DB

    return {
        "ref_hf_energy_fraction_4_8k": float(power[FREQS >= 4000].sum() / power.sum()),
        "ref_fricative_frame_fraction": float(np.mean(centroid[active] > 3000.0)),
        "ref_voiced_frame_fraction": float(np.mean(peak[time_active] > 0.5)),
        "ref_spectral_flatness": float(np.median(flatness[active])),
        "ref_spectral_flux_db": float(np.mean(flux[active])),
    }


def envelope_decorrelation(reference: torch.Tensor, processed: torch.Tensor) -> float:
    """1 - mean Pearson correlation of log band envelopes (0-4 kHz, 4 bands)."""
    ref_power = np.abs(stage2b.stft(reference)) ** 2
    proc_power = np.abs(stage2b.stft(processed)) ** 2
    correlations = []
    for low, high in ENVELOPE_BANDS_HZ:
        band = (FREQS >= low) & (FREQS < high)
        a = 10 * np.log10(ref_power[band].sum(axis=0) + 1e-20)
        b = 10 * np.log10(proc_power[band].sum(axis=0) + 1e-20)
        floor = a.max() - 60.0
        a, b = np.maximum(a, floor), np.maximum(b, floor)
        if a.std() > 0 and b.std() > 0:
            correlations.append(float(np.corrcoef(a, b)[0, 1]))
    return 1.0 - float(np.mean(correlations)) if correlations else float("nan")


def signal_controls(conditions: dict) -> tuple[list[dict], dict]:
    """
    Per-condition signal metrics of one utterance, plus the aligned pairs
    for the pooled transfer accumulators.
    """
    reference = conditions["REF"][0]
    rows, aligned_pairs = [], {}
    for name in CONDITIONS:
        processed = conditions[name][0]
        row = {"condition": name}
        if name == "REF":
            row.update(reference_features(reference))
        else:
            metrics, _, aligned = stage2b.signal_metrics(reference, processed)
            row.update({f"vs_ref_{k}": v for k, v in metrics.items()
                        if k not in ("reference_num_samples", "processed_num_samples",
                                     "aligned_num_samples")})
            row["vs_ref_coherence_0_3500"] = mean_coherence(*aligned)
            aligned_pairs[("REF", name)] = aligned
        if name in ("OPUS", "SILK"):
            lp = conditions["LP"][0]
            metrics, _, aligned = stage2b.signal_metrics(lp, processed)
            row.update({f"vs_lp_{k}": v for k, v in metrics.items()
                        if k not in ("reference_num_samples", "processed_num_samples",
                                     "aligned_num_samples", "length_equal")})
            row["vs_lp_coherence_0_3500"] = mean_coherence(*aligned)
            row["vs_lp_envelope_decorrelation"] = envelope_decorrelation(*aligned)
            aligned_pairs[("LP", name)] = aligned
        rows.append(row)
    return rows, aligned_pairs


# ==================================================
# Pooled transfer accumulators (resumable)
# ==================================================

def new_accumulators() -> dict:
    return {pair: stage2b.TransferAccumulator() for pair in TRANSFER_PAIRS}


def accumulators_to_arrays(accumulators: dict) -> dict[str, np.ndarray]:
    arrays = {}
    for (a, b), acc in accumulators.items():
        for field in ["sxx", "syy", "sxy", "sxy_mirror"]:
            arrays[f"{a}->{b}:{field}"] = getattr(acc, field)
    return arrays


def accumulators_from_arrays(arrays) -> dict:
    accumulators = new_accumulators()
    for (a, b), acc in accumulators.items():
        for field in ["sxx", "syy", "sxy", "sxy_mirror"]:
            setattr(acc, field, np.array(arrays[f"{a}->{b}:{field}"]))
    return accumulators


def pooled_transfer_rows(accumulators: dict) -> tuple[list[dict], list[dict]]:
    summary, curves = [], []
    for (a, b), acc in accumulators.items():
        result = acc.results()
        summary.append({
            "reference": a, "processed": b,
            "h1_level_db": result["level_db"],
            "coherent_bandwidth_hz": result["coherent_bandwidth_hz"],
            "coherent_hf_power_db": result["coherent_hf_power_db"],
            "total_hf_power_db": result["total_hf_power_db"],
            "image_coherence_4100_4900": result["image_coherence_4100_4900"],
            "mean_coherence_0_3500": float(np.mean(result["coherence"][FREQS <= 3500])),
        })
        for k, f in enumerate(FREQS):
            curves.append({"reference": a, "processed": b, "frequency_hz": f,
                           "h1_rel_db": result["h1_rel_db"][k],
                           "coherence": result["coherence"][k],
                           "mirror_coherence": result["mirror_coherence"][k],
                           "power_ratio_db": result["power_ratio_db"][k]})
    return summary, curves
