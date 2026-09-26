"""
Stage 2B: matched signal-domain bandwidth-removal control.

Definition (chosen with the user after the Stage 2B diagnostics)
-----------------------------------------------------------------
Opus SILK-NB output decomposes into three parts:

1. a linear band-limiting response that does not depend on bitrate
   (encoder/decoder resampling chain): flat to ~2.5 kHz, a roll-off from
   ~3 kHz, a steep edge at 4 kHz and no coherent content above ~4.2 kHz;
2. a spectral image of the 3-4 kHz band folded into 4-5 kHz (coherent with
   the input at the mirror frequency 8000 - f, not at f), also independent
   of bitrate;
3. in-band coding distortion, which depends on bitrate.

The low-pass control ("LP") reproduces part 1 only. Its target is SILK-NB's
linear transfer function |H1(f)| = |Sxy| / Sxx, measured at a high bitrate
(40 kbps, signal=voice, 100% SILK-NB packets) where coding distortion is
negligible. Because Opus-NB's 4-5 kHz image is deliberately not reproduced,
the power-based frozen metrics (retained bandwidth, 4-8 kHz power change)
of LP are expected to be lower than Opus-NB's; bandwidth and attenuation
criteria are therefore declared against SILK-NB's coherent response.

Commands (run in this order)
----------------------------
calibrate   dev-clean only. Measures the SILK-NB linear reference, builds the
            target, designs the FIR with N_CORRECTION_ITERATIONS measurement-
            domain corrections, and freezes it (taps, hash, parameters,
            calibration log, hash of TOLERANCES). Refuses to overwrite a
            frozen filter.
validate    Loads the frozen filter (taps hash and tolerance hash checked) and
            evaluates dev-clean (in-sample) and dev-other (held out) for LP,
            Opus8-NB, Opus12-NB and the linear reference.

No ASR model, transcript or WER is used anywhere in this stage. test-clean
and test-other are refused.

Outputs: results_paper/lowpass_validation/

Run:
    /home/mei/elec5305-project/.venv/bin/python paper/run_lowpass_validation.py calibrate
    /home/mei/elec5305-project/.venv/bin/python paper/run_lowpass_validation.py validate
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torchaudio
from tqdm import tqdm

import common
import lowpass
import opus_direct
import run_opus_validation
import run_reproduce


# ==================================================
# Settings
# ==================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path("results_paper") / "lowpass_validation"
FILTER_PATH = OUTPUT_DIR / "frozen_filter.json"

CALIBRATION_SUBSET = "dev-clean"
VALIDATION_SUBSETS = ["dev-clean", "dev-other"]   # dev-other is held out
ALLOWED_SUBSETS = {"dev-clean", "dev-other"}

SAMPLE_RATE = 16000
FREQS = np.linspace(0.0, SAMPLE_RATE / 2.0, common.N_FFT // 2 + 1)
MIRROR = np.arange(len(FREQS))[::-1]               # bin of 8000 - f

# --------------------------------------------------
# SILK-NB linear reference (measurement only, never an experimental cell)
# --------------------------------------------------
REFERENCE_BITRATES = [24000, 32000, 40000]
REFERENCE_BITRATE = 40000
REFERENCE_SIGNAL = "voice"   # keeps high-rate forced NB 100% SILK (auto gives ~2.5% CELT-NB)

# Opus cells compared with LP: Stage 2A settings (frozen ffmpeg defaults)
CELLS = {
    "lp": None,
    "opus_8k_nb": opus_direct.EncoderSettings(bitrate_bps=8000, bandwidth="NB"),
    "opus_12k_nb": opus_direct.EncoderSettings(bitrate_bps=12000, bandwidth="NB"),
    "silk_nb_linear_ref": opus_direct.EncoderSettings(
        bitrate_bps=REFERENCE_BITRATE, bandwidth="NB", signal=REFERENCE_SIGNAL),
}

# --------------------------------------------------
# Filter design parameters
# --------------------------------------------------
NUM_TAPS = 1023                  # 64 ms; odd, type I linear phase
KAISER_BETA = 8.0                # ~80 dB sidelobes
DESIGN_GRID = 16384
LEVEL_BAND_HZ = (500.0, 2000.0)  # |H1| is normalised to its mean level here
PASSBAND_DEVIATION_DB = 0.5      # passband edge: last point before the reference stays below -0.5 dB
STOPBAND_FLOOR_DB = -80.0
N_CORRECTION_ITERATIONS = 3
CORRECTION_FLOOR_DB = -50.0      # only correct where the target is measurable

# --------------------------------------------------
# Tolerances, declared before the first validation run. Their SHA-256 is
# stored in the frozen filter at calibration time and checked by validate.
# --------------------------------------------------
TOLERANCES = {
    "g1_max_abs_lag_samples": 0,
    "g3_lsd_0_3k_median_max_db": 0.5,
    "g3_lsd_0_3k_p95_max_db": 1.0,
    "g3_lsd_0_4k_ratio_to_opus8nb_max": 0.40,
    "g3_min_coherence_up_to_hz": 3800.0,
    "g3_min_coherence": 0.99,
    "g4_coherent_bw_threshold_db": -20.0,
    "g4_coherent_bw_vs_reference_max_hz": 62.5,
    "g4_coherent_bw_vs_opus8nb_max_hz": 125.0,
    "g4_retained_bw_median_range_hz": [3950.0, 4200.0],
    "g5_coherent_hf_vs_reference_max_db": 3.0,
    "g5_coherent_hf_vs_opus8nb_max_db": 6.0,
    "g6_h1_rms_band_hz": [3000.0, 4200.0],
    "g6_h1_rms_max_db": 1.5,
    "g6_h1_abs_band_hz": [3000.0, 4150.0],
    "g6_h1_abs_max_db": 4.0,
    "g6_stopband_from_hz": 4200.0,
    "g6_stopband_max_db": -25.0,
}


def tolerances_sha256() -> str:
    return hashlib.sha256(json.dumps(TOLERANCES, sort_keys=True).encode()).hexdigest()


# ==================================================
# Measurement
# ==================================================

WINDOW = torch.hann_window(common.WIN_LENGTH, dtype=torch.float64)


def stft(waveform: torch.Tensor) -> np.ndarray:
    """Complex STFT with the frozen analysis parameters, in float64."""
    return torch.stft(
        waveform.squeeze(0).double(), n_fft=common.N_FFT,
        hop_length=common.HOP_LENGTH, win_length=common.WIN_LENGTH,
        window=WINDOW, return_complex=True,
    ).numpy()


class TransferAccumulator:
    """Pooled cross-spectra between reference and processed signals."""

    def __init__(self) -> None:
        self.sxx = np.zeros(len(FREQS))
        self.syy = np.zeros(len(FREQS))
        self.sxy = np.zeros(len(FREQS), dtype=complex)
        self.sxy_mirror = np.zeros(len(FREQS), dtype=complex)

    def add(self, reference: torch.Tensor, processed: torch.Tensor) -> None:
        x, y = stft(reference), stft(processed)
        self.sxx += (np.abs(x) ** 2).sum(axis=1)
        self.syy += (np.abs(y) ** 2).sum(axis=1)
        self.sxy += (y * np.conj(x)).sum(axis=1)
        # An image of the component at 8000 - f appears at f as its conjugate
        self.sxy_mirror += (y * x[MIRROR]).sum(axis=1)

    def results(self) -> dict[str, object]:
        tiny = 1e-300
        h1 = np.abs(self.sxy) / np.maximum(self.sxx, tiny)
        level_band = (FREQS >= LEVEL_BAND_HZ[0]) & (FREQS <= LEVEL_BAND_HZ[1])
        level = np.mean(h1[level_band])
        h1_rel_db = 20.0 * np.log10(np.maximum(h1 / level, 1e-15))

        coherent_power = np.abs(self.sxy) ** 2 / np.maximum(self.sxx, tiny)
        hf = FREQS >= 4000.0
        above = np.flatnonzero(h1_rel_db >= TOLERANCES["g4_coherent_bw_threshold_db"])
        image_band = (FREQS >= 4100.0) & (FREQS <= 4900.0)
        mirror_coherence = np.abs(self.sxy_mirror) ** 2 / np.maximum(
            self.sxx[MIRROR] * self.syy, tiny)

        return {
            "h1_rel_db": h1_rel_db,
            "level_db": 20.0 * np.log10(level),
            "coherence": np.abs(self.sxy) ** 2 / np.maximum(self.sxx * self.syy, tiny),
            "mirror_coherence": mirror_coherence,
            "power_ratio_db": 10.0 * np.log10(np.maximum(self.syy, tiny)
                                              / np.maximum(self.sxx, tiny)),
            "coherent_bandwidth_hz": float(FREQS[above[-1]]) if len(above) else 0.0,
            "coherent_hf_power_db": float(10.0 * np.log10(
                coherent_power[hf].sum() / self.sxx[hf].sum())),
            "total_hf_power_db": float(10.0 * np.log10(
                self.syy[hf].sum() / self.sxx[hf].sum())),
            "image_coherence_4100_4900": float(np.mean(mirror_coherence[image_band])),
        }


def signal_metrics(reference: torch.Tensor, processed: torch.Tensor):
    """Frozen signal metrics plus band-limited LSD. Returns row, D(f), aligned pair."""
    aligned_ref, aligned_proc, lag = common.align_waveforms(reference, processed)
    ref_mag = common.magnitude_spectrogram(aligned_ref)
    proc_mag = common.magnitude_spectrogram(aligned_proc)
    dspec, lsd_db, dfrequency = common.spectral_distortion(ref_mag, proc_mag)
    retained, hf_change = common.bandwidth_measures(ref_mag, proc_mag, FREQS)
    band_lsd = run_opus_validation.band_lsd
    row = {
        "alignment_lag_samples": lag,
        "alignment_lag_ms": lag / SAMPLE_RATE * 1000.0,
        "reference_num_samples": reference.shape[-1],
        "processed_num_samples": processed.shape[-1],
        "length_equal": processed.shape[-1] == reference.shape[-1],
        "aligned_num_samples": aligned_ref.shape[-1],
        "spectral_distortion": dspec,
        "lsd_db": lsd_db,
        "lsd_0_3k_db": band_lsd(ref_mag, proc_mag, FREQS, 0.0, 3000.0),
        "lsd_0_4k_db": band_lsd(ref_mag, proc_mag, FREQS, 0.0, 4000.0),
        "lsd_4_8k_db": band_lsd(ref_mag, proc_mag, FREQS, 4000.0, 8000.0, include_high=True),
        "retained_bandwidth_hz": retained,
        "hf_power_change_db": hf_change,
    }
    return row, dfrequency, (aligned_ref, aligned_proc)


def opus_round_trip(waveform, sample_rate, settings):
    """Direct libopus encode, frozen decode path, resample to 16 kHz."""
    result = opus_direct.encode(waveform, sample_rate, settings)
    decoded, decoded_sr = opus_direct.decode_frozen_path(result.ogg)
    if decoded_sr != sample_rate:
        decoded = torchaudio.functional.resample(decoded, decoded_sr, sample_rate)
    configurations = collections.Counter(
        opus_direct.packet_info(p)["configuration"] for p in result.packets)
    return decoded, configurations


def load_subset(subset: str):
    if subset not in ALLOWED_SUBSETS:
        raise ValueError(f"Stage 2B may only use {sorted(ALLOWED_SUBSETS)}, not {subset}")
    dataset = torchaudio.datasets.LIBRISPEECH(common.DATA_ROOT, url=subset, download=False)
    return dataset, run_opus_validation.select_dev_utterances(dataset)


# ==================================================
# Calibration (dev-clean)
# ==================================================

def build_target(reference_h1_rel_db: np.ndarray) -> tuple[np.ndarray, float]:
    """0 dB passband, measured SILK-NB linear response above the passband
    edge (never above 0 dB, monotone non-increasing), floored."""
    stays_below = np.array([
        np.max(reference_h1_rel_db[k:]) <= -PASSBAND_DEVIATION_DB
        for k in range(len(FREQS))
    ])
    edge = int(np.argmax(stays_below))
    target = np.minimum(reference_h1_rel_db, 0.0)
    target[:edge] = 0.0
    target[edge:] = np.minimum.accumulate(target[edge:])
    return np.maximum(target, STOPBAND_FLOOR_DB), float(FREQS[edge])


def constrain(design_db: np.ndarray, edge_hz: float) -> np.ndarray:
    design_db = np.minimum(design_db, 0.0)
    above = FREQS >= edge_hz
    design_db[~above] = 0.0
    design_db[above] = np.minimum.accumulate(design_db[above])
    return np.maximum(design_db, STOPBAND_FLOOR_DB)


def design(design_db: np.ndarray) -> np.ndarray:
    return lowpass.design_linear_phase_fir(
        FREQS, design_db, SAMPLE_RATE, NUM_TAPS, KAISER_BETA, DESIGN_GRID)


def calibrate(force: bool) -> None:

    if FILTER_PATH.exists() and not force:
        raise RuntimeError(f"{FILTER_PATH} exists: the filter is frozen (use --force to redesign)")

    dataset, indices = load_subset(CALIBRATION_SUBSET)
    waveforms = []
    references = {rate: TransferAccumulator() for rate in REFERENCE_BITRATES}
    reference_packets = {rate: collections.Counter() for rate in REFERENCE_BITRATES}

    for index in tqdm(indices, desc=f"reference ({CALIBRATION_SUBSET})", unit="utt"):
        waveform, sample_rate, *_ = dataset[index]
        waveforms.append(waveform)
        for rate in REFERENCE_BITRATES:
            settings = opus_direct.EncoderSettings(
                bitrate_bps=rate, bandwidth="NB", signal=REFERENCE_SIGNAL)
            decoded, configurations = opus_round_trip(waveform, sample_rate, settings)
            reference_packets[rate].update(configurations)
            aligned_ref, aligned_dec, _ = common.align_waveforms(waveform, decoded)
            references[rate].add(aligned_ref, aligned_dec)

    reference = {rate: acc.results() for rate, acc in references.items()}
    reference_h1 = reference[REFERENCE_BITRATE]["h1_rel_db"]
    measurable = FREQS <= 4150.0
    convergence = {
        f"max_abs_h1_diff_{rate // 1000}k_vs_{REFERENCE_BITRATE // 1000}k_db_up_to_4150hz":
        float(np.max(np.abs(reference[rate]["h1_rel_db"] - reference_h1)[measurable]))
        for rate in REFERENCE_BITRATES if rate != REFERENCE_BITRATE
    }

    target_db, edge_hz = build_target(reference_h1)
    design_db = target_db.copy()
    correctable = (FREQS >= edge_hz) & (target_db > CORRECTION_FLOOR_DB)
    rms_band = (FREQS >= TOLERANCES["g6_h1_rms_band_hz"][0]) & (
        FREQS <= TOLERANCES["g6_h1_rms_band_hz"][1])

    iterations = []
    for iteration in range(N_CORRECTION_ITERATIONS + 1):
        taps = design(design_db)
        accumulator = TransferAccumulator()
        for waveform in tqdm(waveforms, desc=f"design iteration {iteration}", unit="utt"):
            accumulator.add(waveform, lowpass.apply_zero_phase(waveform, taps))
        measured = accumulator.results()["h1_rel_db"]
        error = measured - target_db
        iterations.append({
            "iteration": iteration,
            "rms_error_db_3000_4200": float(np.sqrt(np.mean(error[rms_band] ** 2))),
            "max_abs_error_db_3000_4150": float(np.max(np.abs(error[
                (FREQS >= 3000) & (FREQS <= 4150)]))),
        })
        if iteration == N_CORRECTION_ITERATIONS:
            break
        design_db[correctable] -= error[correctable]
        design_db = constrain(design_db, edge_hz)

    metadata = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "definition": "linear band-limiting component of Opus SILK-NB only "
                      "(no spectral image, no coding distortion)",
        "calibration_subset": CALIBRATION_SUBSET,
        "calibration_dataset_indices": indices,
        "calibration_seconds": float(sum(w.shape[-1] for w in waveforms) / SAMPLE_RATE),
        "reference": {
            "bitrates": REFERENCE_BITRATES,
            "bitrate_used": REFERENCE_BITRATE,
            "signal": REFERENCE_SIGNAL,
            "other_settings": "Stage 2A EncoderSettings defaults, forced NB",
            "packet_configurations": {str(r): dict(c) for r, c in reference_packets.items()},
            "convergence": convergence,
            "libopus": opus_direct.libopus_version(),
        },
        "design": {
            "sample_rate": SAMPLE_RATE,
            "num_taps": NUM_TAPS,
            "delay_removed_samples": (NUM_TAPS - 1) // 2,
            "kaiser_beta": KAISER_BETA,
            "design_grid": DESIGN_GRID,
            "level_band_hz": list(LEVEL_BAND_HZ),
            "passband_deviation_db": PASSBAND_DEVIATION_DB,
            "passband_edge_hz": edge_hz,
            "stopband_floor_db": STOPBAND_FLOOR_DB,
            "correction_iterations": N_CORRECTION_ITERATIONS,
            "correction_floor_db": CORRECTION_FLOOR_DB,
            "iterations": iterations,
            "analysis": {"n_fft": common.N_FFT, "win_length": common.WIN_LENGTH,
                         "hop_length": common.HOP_LENGTH, "window": "hann"},
        },
        "tolerances": TOLERANCES,
        "tolerances_sha256": tolerances_sha256(),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    digest = lowpass.save_filter(FILTER_PATH, taps, metadata)

    pd.DataFrame({
        "frequency_hz": FREQS,
        **{f"reference_h1_rel_db_{r // 1000}k": reference[r]["h1_rel_db"]
           for r in REFERENCE_BITRATES},
        "reference_power_ratio_db": reference[REFERENCE_BITRATE]["power_ratio_db"],
        "reference_mirror_coherence": reference[REFERENCE_BITRATE]["mirror_coherence"],
        "target_db": target_db,
        "design_db": design_db,
        "lp_measured_h1_rel_db": measured,
        "fir_response_db": lowpass.frequency_response_db(taps, FREQS, SAMPLE_RATE),
    }).to_csv(OUTPUT_DIR / "calibration_curves.csv", index=False)

    print(json.dumps({"taps_sha256": digest, "passband_edge_hz": edge_hz,
                      "convergence": convergence, "iterations": iterations}, indent=2))


# ==================================================
# Validation (dev-clean in-sample, dev-other held out)
# ==================================================

def run_subset(subset: str, taps: np.ndarray):

    dataset, indices = load_subset(subset)
    rows, curves = [], collections.defaultdict(list)
    accumulators = {cell: TransferAccumulator() for cell in CELLS}
    packets = {cell: collections.Counter() for cell in CELLS if cell != "lp"}

    for index in tqdm(indices, desc=subset, unit="utt"):
        waveform, sample_rate, _, speaker_id, chapter_id, utterance_id = dataset[index]
        ids = {"dataset": subset, "dataset_index": index, "speaker_id": speaker_id,
               "chapter_id": chapter_id, "utterance_id": utterance_id}
        for cell, settings in CELLS.items():
            if cell == "lp":
                processed = lowpass.apply_zero_phase(waveform, taps)
                repeat = lowpass.apply_zero_phase(waveform, taps)
                extra = {"deterministic": torch.equal(processed, repeat),
                         "output_dtype": str(processed.dtype)}
            else:
                processed, configurations = opus_round_trip(waveform, sample_rate, settings)
                packets[cell].update(configurations)
                extra = {"share_silk_nb": configurations.get("SILK-NB", 0)
                         / sum(configurations.values())}
            row, dfrequency, aligned = signal_metrics(waveform, processed)
            rows.append({**ids, "cell": cell, **row, **extra})
            curves[cell].append(dfrequency)
            accumulators[cell].add(*aligned)

    transfer = {cell: acc.results() for cell, acc in accumulators.items()}
    return pd.DataFrame(rows), curves, transfer, packets


def evaluate_gates(subset: str, rows: pd.DataFrame, transfer: dict,
                   taps: np.ndarray) -> list[dict]:

    t = TOLERANCES
    lp = rows[rows["cell"] == "lp"]
    opus8 = rows[rows["cell"] == "opus_8k_nb"].set_index("dataset_index").loc[lp["dataset_index"]]
    lp_t, ref_t, o8_t = transfer["lp"], transfer["silk_nb_linear_ref"], transfer["opus_8k_nb"]
    gates = []

    def gate(number, name, passed, evidence):
        gates.append({"subset": subset, "gate": number, "name": name,
                      "status": "PASS" if passed else "FAIL", "evidence": evidence})

    symmetric = len(taps) % 2 == 1 and np.array_equal(taps, taps[::-1])
    lags = lp["alignment_lag_samples"].abs()
    gate(1, "zero effective delay",
         symmetric and bool((lags <= t["g1_max_abs_lag_samples"]).all()),
         f"odd, exactly symmetric taps with (L-1)/2 = {(len(taps) - 1) // 2} samples "
         f"removed: {symmetric}; alignment lag 0 in {int((lags == 0).sum())}/{len(lp)}")

    gate(2, "waveform length unchanged", bool(lp["length_equal"].all()),
         f"{int(lp['length_equal'].sum())}/{len(lp)} utterances; deterministic "
         f"{int(lp['deterministic'].sum())}/{len(lp)}")

    band = FREQS <= t["g3_min_coherence_up_to_hz"]
    lsd03_median = float(lp["lsd_0_3k_db"].median())
    lsd03_p95 = float(lp["lsd_0_3k_db"].quantile(0.95))
    ratio = float(lp["lsd_0_4k_db"].median() / opus8["lsd_0_4k_db"].median())
    min_coherence = float(lp_t["coherence"][band].min())
    gate(3, "low-band distortion small (bandwidth removal only)",
         lsd03_median <= t["g3_lsd_0_3k_median_max_db"]
         and lsd03_p95 <= t["g3_lsd_0_3k_p95_max_db"]
         and ratio <= t["g3_lsd_0_4k_ratio_to_opus8nb_max"]
         and min_coherence >= t["g3_min_coherence"],
         f"LSD 0-3 kHz median {lsd03_median:.3f} dB, p95 {lsd03_p95:.3f} dB; "
         f"LSD 0-4 kHz median {lp['lsd_0_4k_db'].median():.2f} dB = {ratio:.1%} of "
         f"Opus8-NB ({opus8['lsd_0_4k_db'].median():.2f} dB); min coherence 0-"
         f"{t['g3_min_coherence_up_to_hz']:.0f} Hz {min_coherence:.4f} "
         f"(Opus8-NB {o8_t['coherence'][band].min():.3f})")

    retained = float(lp["retained_bandwidth_hz"].median())
    low, high = t["g4_retained_bw_median_range_hz"]
    bw_ref = lp_t["coherent_bandwidth_hz"] - ref_t["coherent_bandwidth_hz"]
    bw_o8 = lp_t["coherent_bandwidth_hz"] - o8_t["coherent_bandwidth_hz"]
    gate(4, "bandwidth matches SILK-NB (coherent definition)",
         abs(bw_ref) <= t["g4_coherent_bw_vs_reference_max_hz"]
         and abs(bw_o8) <= t["g4_coherent_bw_vs_opus8nb_max_hz"]
         and low <= retained <= high,
         f"coherent bandwidth LP {lp_t['coherent_bandwidth_hz']:.1f} Hz, reference "
         f"{ref_t['coherent_bandwidth_hz']:.1f} ({bw_ref:+.1f}), Opus8-NB "
         f"{o8_t['coherent_bandwidth_hz']:.1f} ({bw_o8:+.1f}); power-based retained "
         f"bandwidth median LP {retained:.1f} Hz (range {low:.0f}-{high:.0f}; Opus8-NB "
         f"{opus8['retained_bandwidth_hz'].median():.1f} includes the image)")

    hf_ref = lp_t["coherent_hf_power_db"] - ref_t["coherent_hf_power_db"]
    hf_o8 = lp_t["coherent_hf_power_db"] - o8_t["coherent_hf_power_db"]
    lp_hf, o8_hf = float(lp["hf_power_change_db"].median()), float(opus8["hf_power_change_db"].median())
    gate(5, "4-8 kHz attenuation matches SILK-NB (coherent definition)",
         abs(hf_ref) <= t["g5_coherent_hf_vs_reference_max_db"]
         and abs(hf_o8) <= t["g5_coherent_hf_vs_opus8nb_max_db"]
         and lp_hf <= o8_hf,
         f"coherent 4-8 kHz power LP {lp_t['coherent_hf_power_db']:.1f} dB, reference "
         f"{ref_t['coherent_hf_power_db']:.1f} ({hf_ref:+.1f}), Opus8-NB "
         f"{o8_t['coherent_hf_power_db']:.1f} ({hf_o8:+.1f}); total 4-8 kHz power "
         f"change median LP {lp_hf:.1f} dB <= Opus8-NB {o8_hf:.1f} dB (difference = "
         f"image, mirror coherence 4.1-4.9 kHz Opus8-NB "
         f"{o8_t['image_coherence_4100_4900']:.2f}, LP {lp_t['image_coherence_4100_4900']:.3f})")

    rms_band = (FREQS >= t["g6_h1_rms_band_hz"][0]) & (FREQS <= t["g6_h1_rms_band_hz"][1])
    abs_band = (FREQS >= t["g6_h1_abs_band_hz"][0]) & (FREQS <= t["g6_h1_abs_band_hz"][1])
    stop = FREQS > t["g6_stopband_from_hz"]
    difference = lp_t["h1_rel_db"] - ref_t["h1_rel_db"]
    rms = float(np.sqrt(np.mean(difference[rms_band] ** 2)))
    worst = float(np.max(np.abs(difference[abs_band])))
    stop_max = float(np.max(lp_t["h1_rel_db"][stop]))
    gate(6, "transition shape matches SILK-NB linear response",
         rms <= t["g6_h1_rms_max_db"] and worst <= t["g6_h1_abs_max_db"]
         and stop_max <= t["g6_stopband_max_db"],
         f"|H1| LP - reference: RMS {rms:.2f} dB over {t['g6_h1_rms_band_hz']} Hz, max "
         f"{worst:.2f} dB over {t['g6_h1_abs_band_hz']} Hz; LP |H1| above "
         f"{t['g6_stopband_from_hz']:.0f} Hz <= {stop_max:.1f} dB")

    return gates


def cell_summary(subset: str, rows: pd.DataFrame, transfer: dict, packets: dict) -> pd.DataFrame:
    out = []
    for cell, group in rows.groupby("cell", sort=False):
        tr = transfer[cell]
        out.append({
            "subset": subset, "cell": cell, "utterances": len(group),
            "lag_samples": json.dumps(dict(collections.Counter(
                int(v) for v in group["alignment_lag_samples"]))),
            "length_equal": f"{int(group['length_equal'].sum())}/{len(group)}",
            **{f"{m}_median": float(group[m].median()) for m in [
                "retained_bandwidth_hz", "lsd_db", "lsd_0_3k_db", "lsd_0_4k_db",
                "lsd_4_8k_db", "hf_power_change_db"]},
            "coherent_bandwidth_hz": tr["coherent_bandwidth_hz"],
            "coherent_hf_power_db": tr["coherent_hf_power_db"],
            "total_hf_power_db": tr["total_hf_power_db"],
            "image_coherence_4100_4900": tr["image_coherence_4100_4900"],
            "h1_level_db": tr["level_db"],
            "packets": json.dumps(dict(packets.get(cell, {}))) if cell != "lp" else "",
        })
    return pd.DataFrame(out)


def transfer_table(subset: str, transfer: dict, curves: dict) -> pd.DataFrame:
    frames = []
    for cell, tr in transfer.items():
        frames.append(pd.DataFrame({
            "subset": subset, "cell": cell, "frequency_hz": FREQS,
            "h1_rel_db": tr["h1_rel_db"], "coherence": tr["coherence"],
            "mirror_coherence": tr["mirror_coherence"],
            "power_ratio_db": tr["power_ratio_db"],
            "mean_dfreq_db": np.mean(np.stack(curves[cell]), axis=0),
            "median_dfreq_db": np.median(np.stack(curves[cell]), axis=0),
        }))
    return pd.concat(frames)


def write_report(record, gates, summary, transfer_df, path):

    table = run_reproduce.markdown_table
    meta = record["metadata"]
    verdict = "PASS" if (gates["status"] == "PASS").all() else "FAIL"

    key_freqs = [1000, 2000, 3000, 3500, 3750, 3875, 4000, 4062.5, 4125, 4250, 4500,
                 5000, 6000, 7000]
    def curve_table(column):
        sub = transfer_df[transfer_df["frequency_hz"].isin(key_freqs)]
        return sub.pivot_table(index=["subset", "frequency_hz"], columns="cell",
                               values=column).reset_index()

    lines = [
        "# Stage 2B: matched bandwidth-removal control",
        "",
        f"**Verdict: {verdict}** ({int((gates['status'] == 'PASS').sum())}/{len(gates)} "
        "gate evaluations passed; gate 7 = gates 1-6 on held-out dev-other with the "
        "frozen filter)",
        "",
        f"Definition: {meta['definition']}.",
        "",
        "## Frozen filter",
        "",
        f"- taps SHA-256 `{record['taps_sha256']}`, {record['num_taps']} taps",
        f"- design: {json.dumps({k: v for k, v in meta['design'].items() if k != 'iterations'})}",
        f"- calibration: {meta['calibration_subset']}, "
        f"{len(meta['calibration_dataset_indices'])} utterances, "
        f"{meta['calibration_seconds']:.0f} s",
        f"- reference: {json.dumps(meta['reference'])}",
        "",
        "Correction iterations (LP measured vs target, dev-clean):",
        "",
        table(pd.DataFrame(meta["design"]["iterations"])),
        "",
        "## Tolerances (declared before validation; SHA-256 "
        f"`{meta['tolerances_sha256']}` stored at calibration)",
        "",
        "```json",
        json.dumps(meta["tolerances"], indent=1),
        "```",
        "",
        "## Gates",
        "",
        table(gates),
        "",
        "## Per-cell summary",
        "",
        table(summary),
        "",
        "## Linear transfer |H1| relative to the 0.5-2 kHz level (dB)",
        "",
        table(curve_table("h1_rel_db")),
        "",
        "## Long-term power ratio (dB)",
        "",
        table(curve_table("power_ratio_db")),
        "",
        "## Mean D(f) (dB, frozen definition)",
        "",
        table(curve_table("mean_dfreq_db")),
        "",
        "## Mirror coherence (output at f vs input at 8000 - f)",
        "",
        table(curve_table("mirror_coherence")),
        "",
    ]
    path.write_text("\n".join(lines))


def validate() -> int:

    taps, record = lowpass.load_filter(FILTER_PATH)
    if record["metadata"]["tolerances_sha256"] != tolerances_sha256():
        raise RuntimeError("TOLERANCES changed after the filter was frozen")

    environment = run_reproduce.collect_environment()
    environment["libopus_loaded_by_opus_direct"] = opus_direct.libopus_version()
    environment["subsets"] = {
        s: os.path.realpath(os.path.join(common.DATA_ROOT, "LibriSpeech", s))
        for s in VALIDATION_SUBSETS}
    (OUTPUT_DIR / "environment.json").write_text(json.dumps(environment, indent=2))

    all_gates, summaries, transfers = [], [], []
    for subset in VALIDATION_SUBSETS:
        rows, curves, transfer, packets = run_subset(subset, taps)
        rows.to_csv(OUTPUT_DIR / f"{subset}_utterance_rows.csv", index=False)
        all_gates.extend(evaluate_gates(subset, rows, transfer, taps))
        summaries.append(cell_summary(subset, rows, transfer, packets))
        transfers.append(transfer_table(subset, transfer, curves))

    gates = pd.DataFrame(all_gates)
    held_out = gates[gates["subset"] == "dev-other"]
    gates = pd.concat([gates, pd.DataFrame([{
        "subset": "dev-other", "gate": 7,
        "name": "same frozen filter passes gates 1-6 on held-out dev-other",
        "status": "PASS" if (held_out["status"] == "PASS").all() else "FAIL",
        "evidence": f"taps SHA-256 {record['taps_sha256'][:16]}..., no retuning; "
                    f"{int((held_out['status'] == 'PASS').sum())}/{len(held_out)} passed",
    }])], ignore_index=True)

    summary = pd.concat(summaries, ignore_index=True)
    transfer_df = pd.concat(transfers, ignore_index=True)
    gates.to_csv(OUTPUT_DIR / "gates.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "cell_summary.csv", index=False)
    transfer_df.to_csv(OUTPUT_DIR / "transfer_curves.csv", index=False)
    write_report(record, gates, summary, transfer_df, OUTPUT_DIR / "validation_report.md")

    print(gates[["subset", "gate", "status", "evidence"]].to_string(index=False))
    print(f"Report: {OUTPUT_DIR / 'validation_report.md'}")
    return 0 if (gates["status"] == "PASS").all() else 1


# ==================================================
# Main
# ==================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 2B low-pass control")
    parser.add_argument("command", choices=["calibrate", "validate"])
    parser.add_argument("--force", action="store_true",
                        help="calibrate: overwrite an existing frozen filter")
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if args.command == "calibrate":
        calibrate(args.force)
        return 0
    return validate()


if __name__ == "__main__":
    sys.exit(main())
