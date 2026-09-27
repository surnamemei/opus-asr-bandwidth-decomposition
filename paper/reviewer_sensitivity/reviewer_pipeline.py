"""
Runtime of the R1-R3 runner (run_reviewer_sensitivity.py), written at step RS1.

Built from frozen functions, imported unchanged:
opus_direct (encode, decode_frozen_path, packet_info, read_opus_head, last_granule and the
libopus shared object), common (ogg_audio_packets, align_waveforms), lowpass,
run_lowpass_validation (TransferAccumulator, signal_metrics, build_target, constrain,
design, load_subset, opus_round_trip, evaluate_gates), run_lowpass_confirmation
(revised_gate5, subset_dir), stage3_audio (codec_round_trip, load_filters, tensor_sha256,
mean_coherence, pooled_transfer_rows), upgrade_pipeline (audio_row, packet_summary,
readback_mismatches, process_chunk, run_set, Recognisers, load_reference).

Conditions
    REF, LP, OPUS, SILK   as Stage 3 (OPUS and SILK decoded by the frozen FFmpeg path)
    OPUS_REFDEC           the OPUS Ogg bytes decoded by the libopus 1.4 reference decoder (R1)
    SILK_REFDEC           the SILK Ogg bytes decoded by the libopus 1.4 reference decoder (R1)
    LP_LIBOPUS            the decoder-matched control, only if R1-REUSE failed (R1)
    SURR8                 the 8-kbit/s effective coherent-linear surrogate (R2)
    NB8, WB8              Stage 3 OPUS settings, bandwidth NB or WB, frozen decode path (R3)
"""

import collections
import ctypes
import json
import os
import tempfile

import numpy as np
import pandas as pd
import torch
import torchaudio

import common
import lowpass
import opus_direct
import reviewer_design as design
import run_lowpass_confirmation as s2c
import run_lowpass_validation as s2b
import stage3_audio as audio
import upgrade_pipeline as upipe


SAMPLE_RATE = audio.SAMPLE_RATE
FREQS = s2b.FREQS
OPUS_SETTINGS = audio.CODEC_SETTINGS["OPUS"]
SILK_SETTINGS = audio.CODEC_SETTINGS["SILK"]
EXPECTED_CONFIG = {"OPUS": 1, "SILK": 1, design.NB8: 1, design.WB8: design.WB_CONFIGURATION}
if s2b.CELLS["opus_8k_nb"] != OPUS_SETTINGS or s2b.CELLS["silk_nb_linear_ref"] != SILK_SETTINGS:
    raise RuntimeError("Stage 2B cell settings differ from the Stage 3 OPUS and SILK settings")


# ==================================================
# The libopus reference decoder (R1): the shared object that encodes
# ==================================================

_lib = opus_direct.libopus
_lib.opus_decoder_create.restype = ctypes.c_void_p
_lib.opus_decoder_create.argtypes = [ctypes.c_int32, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
_lib.opus_decoder_destroy.restype = None
_lib.opus_decoder_destroy.argtypes = [ctypes.c_void_p]
_lib.opus_decode_float.restype = ctypes.c_int
_lib.opus_decode_float.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int32,
                                   ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.c_int]


def ogg_packets(ogg: bytes) -> list[bytes]:
    """Audio packets of an Ogg Opus stream, by the frozen parser common.ogg_audio_packets."""
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "stream.opus")
        with open(path, "wb") as file:
            file.write(ogg)
        return common.ogg_audio_packets(path)


def reference_decode(ogg: bytes) -> tuple[np.ndarray, dict]:
    """
    Decode an Ogg Opus stream with libopus: one decoder at 48 kHz, opus_decode_float per packet
    in stream order (decode_fec 0), the first pre-skip samples discarded and the output trimmed to
    (final granule position - pre-skip) samples (RFC 7845). Returns float32 samples at 48 kHz.
    """
    head = opus_direct.read_opus_head(ogg)
    if head["channels"] != 1:
        raise RuntimeError("only mono streams are decoded")
    final = opus_direct.last_granule(ogg)
    packets = ogg_packets(ogg)
    error = ctypes.c_int()
    decoder = ctypes.c_void_p(_lib.opus_decoder_create(design.REFERENCE_DECODER_RATE, 1, ctypes.byref(error)))
    if error.value != opus_direct.OPUS_OK:
        raise RuntimeError(f"opus_decoder_create: {_lib.opus_strerror(error.value).decode()}")
    buffer = (ctypes.c_float * design.REFERENCE_DECODER_MAX_FRAME)()
    chunks, counts = [], []
    try:
        for packet in packets:
            n = _lib.opus_decode_float(decoder, packet, len(packet), buffer, design.REFERENCE_DECODER_MAX_FRAME, 0)
            if n < 0:
                raise RuntimeError(f"opus_decode_float: {_lib.opus_strerror(n).decode()}")
            counts.append(int(n))
            chunks.append(np.ctypeslib.as_array(buffer)[:n].copy())
    finally:
        _lib.opus_decoder_destroy(decoder)
    pcm = np.concatenate(chunks).astype(np.float32)
    skip, total = head["pre_skip"], final - head["pre_skip"]
    if total <= 0 or skip + total > pcm.size:
        raise RuntimeError("final granule position lies beyond the decoded samples")
    return pcm[skip:skip + total], {"pre_skip": skip, "output_gain": head["output_gain"], "final_granule": final,
                                    "packets": packets, "samples_per_packet": sorted(set(counts)),
                                    "length_48k": int(total)}


def to_16k(waveform_48k: torch.Tensor) -> torch.Tensor:
    """The resampling step of stage3_audio.codec_round_trip (float32 input, default parameters)."""
    return torchaudio.functional.resample(waveform_48k, design.REFERENCE_DECODER_RATE, SAMPLE_RATE).to(torch.float32)


def packet_summary(result: opus_direct.EncodeResult, num_samples: int, decoded_rate: int, expected_config: int) -> dict:
    """upgrade_pipeline.packet_summary with the share of an arbitrary expected TOC configuration."""
    summary = upipe.packet_summary(result, num_samples, decoded_rate)
    configs = collections.Counter(opus_direct.packet_info(p)["config"] for p in result.packets)
    summary["expected_config"] = expected_config
    summary["share_expected_config"] = configs.get(expected_config, 0) / len(result.packets)
    return summary


def encode_and_decode(waveform: torch.Tensor, settings: opus_direct.EncoderSettings, expected_config: int,
                      reference_decoder: bool) -> dict:
    """
    One encode; the Ogg bytes decoded by the frozen FFmpeg path (the steps of
    stage3_audio.codec_round_trip) and, if asked, by the libopus reference decoder.
    """
    result = opus_direct.encode(waveform, SAMPLE_RATE, settings)
    decoded, rate = opus_direct.decode_frozen_path(result.ogg)
    ffmpeg_48k_length = int(decoded.shape[-1])
    if rate != SAMPLE_RATE:
        decoded = torchaudio.functional.resample(decoded, rate, SAMPLE_RATE)
    summary = packet_summary(result, waveform.shape[-1], rate, expected_config)
    out = {"result": result, "ffmpeg": decoded.to(torch.float32), "summary": summary,
           "readback_mismatches": upipe.readback_mismatches(result)}
    if reference_decoder:
        pcm, info = reference_decode(result.ogg)
        out["refdec"] = to_16k(torch.from_numpy(pcm).unsqueeze(0))
        out["refdec_info"] = {
            "packets_identical": info["packets"] == result.packets,
            "samples_per_packet": ";".join(str(n) for n in info["samples_per_packet"]),
            "output_gain": info["output_gain"],
            "pre_skip_is_3x_lookahead": info["pre_skip"] == 3 * result.lookahead_samples,
            "length_48k": info["length_48k"], "ffmpeg_length_48k": ffmpeg_48k_length,
            "decoder": opus_direct.libopus_version(), "decoder_path": opus_direct.libopus_path(),
        }
    return out


def refdec_round_trip(waveform: torch.Tensor, settings: opus_direct.EncoderSettings) -> torch.Tensor:
    return encode_and_decode(waveform, settings, 1, True)["refdec"]


# ==================================================
# Stage 2B measurements and the unchanged Stage 2B fit
# ==================================================

def stage2b_calibration_waveforms() -> list[torch.Tensor]:
    """The 40 dev-clean utterances that fitted the primary control, in the frozen order."""
    metadata = json.loads(design.STAGE2B_FILTER.read_text())["metadata"]
    dataset, indices = s2b.load_subset(metadata["calibration_subset"])
    if list(indices) != metadata["calibration_dataset_indices"]:
        raise RuntimeError("Stage 2B calibration indices differ from the frozen filter record")
    waveforms = []
    for index in indices:
        waveform, rate, *_ = dataset[index]
        if rate != SAMPLE_RATE:
            raise RuntimeError(f"calibration utterance {index}: {rate} Hz")
        waveforms.append(waveform)
    return waveforms


def measure(waveforms: list[torch.Tensor], process, align: bool = True) -> dict:
    """Pooled TransferAccumulator results of process(waveform) against the waveform (Stage 2B)."""
    accumulator = s2b.TransferAccumulator()
    for waveform in waveforms:
        processed = process(waveform)
        if align:
            reference, processed, _ = common.align_waveforms(waveform, processed)
            accumulator.add(reference, processed)
        else:
            accumulator.add(waveform, processed)
    return accumulator.results()


def ffmpeg_codec(settings):
    return lambda waveform: s2b.opus_round_trip(waveform, SAMPLE_RATE, settings)[0]


def libopus_codec(settings):
    return lambda waveform: refdec_round_trip(waveform, settings)


def zero_phase(taps):
    return lambda waveform: lowpass.apply_zero_phase(waveform, taps)


def fit_stage2b_filter(reference_h1_rel_db: np.ndarray, waveforms: list[torch.Tensor]) -> tuple[np.ndarray, dict]:
    """
    The design part of run_lowpass_validation.calibrate, unchanged: build_target, design with
    N_CORRECTION_ITERATIONS measurement-domain corrections where the target is measurable,
    constrain. Only the reference curve differs.
    """
    target_db, edge_hz = s2b.build_target(reference_h1_rel_db)
    design_db = target_db.copy()
    correctable = (FREQS >= edge_hz) & (target_db > s2b.CORRECTION_FLOOR_DB)
    t = s2b.TOLERANCES
    rms_band = (FREQS >= t["g6_h1_rms_band_hz"][0]) & (FREQS <= t["g6_h1_rms_band_hz"][1])
    edge_band = (FREQS >= edge_hz) & (FREQS <= t["g6_h1_rms_band_hz"][1])
    iterations, taps, measured = [], None, None
    for iteration in range(s2b.N_CORRECTION_ITERATIONS + 1):
        taps = s2b.design(design_db)
        measured = measure(waveforms, zero_phase(taps), align=False)["h1_rel_db"]
        error = measured - target_db
        iterations.append({
            "iteration": iteration,
            "rms_error_db_3000_4200": float(np.sqrt(np.mean(error[rms_band] ** 2))),
            "max_abs_error_db_3000_4150": float(np.max(np.abs(error[(FREQS >= 3000) & (FREQS <= 4150)]))),
            "rms_error_db_edge_4200": float(np.sqrt(np.mean(error[edge_band] ** 2))),
        })
        if iteration == s2b.N_CORRECTION_ITERATIONS:
            break
        design_db[correctable] -= error[correctable]
        design_db = s2b.constrain(design_db, edge_hz)
    return taps, {"edge_hz": float(edge_hz), "target_db": target_db, "design_db": design_db,
                  "measured_h1_rel_db": measured, "iterations": iterations}


def max_abs_difference(a: np.ndarray, b: np.ndarray, up_to_hz: float) -> float:
    band = FREQS <= up_to_hz
    return float(np.max(np.abs(np.asarray(a)[band] - np.asarray(b)[band])))


def transfer_summary(result: dict) -> dict:
    return {"coherent_bandwidth_hz": result["coherent_bandwidth_hz"],
            "coherent_hf_power_db": result["coherent_hf_power_db"],
            "total_hf_power_db": result["total_hf_power_db"],
            "image_coherence_4100_4900": result["image_coherence_4100_4900"],
            "level_db": result["level_db"]}


def band(low: float, high: float) -> np.ndarray:
    return (FREQS >= low) & (FREQS <= high)


def reuse_gate(lp: dict, silk_lib: dict, silk_ff: dict) -> dict:
    """R1-REUSE (control-reuse gate, not a statistical equivalence test), exactly as frozen."""
    c = design.r1_reuse_criteria()
    rms_band, abs_band = band(*c["rms_band_hz"]), band(*c["abs_band_hz"])
    d_lib = lp["h1_rel_db"] - silk_lib["h1_rel_db"]
    d_ff = lp["h1_rel_db"] - silk_ff["h1_rel_db"]
    rms_lib = float(np.sqrt(np.mean(d_lib[rms_band] ** 2)))
    rms_ff = float(np.sqrt(np.mean(d_ff[rms_band] ** 2)))
    max_lib = float(np.max(np.abs(d_lib[abs_band])))
    bw = lp["coherent_bandwidth_hz"] - silk_lib["coherent_bandwidth_hz"]
    hf = lp["coherent_hf_power_db"] - silk_lib["coherent_hf_power_db"]
    criteria = {
        "a_coherent_bandwidth": {"value_hz": bw, "limit_hz": c["coherent_bandwidth_max_hz"],
                                 "pass": abs(bw) <= c["coherent_bandwidth_max_hz"]},
        "b_coherent_hf_power": {"value_db": hf, "limit_db": c["coherent_hf_power_max_db"],
                                "pass": abs(hf) <= c["coherent_hf_power_max_db"]},
        "c_shape": {"rms_lib_db": rms_lib, "rms_limit_db": c["rms_max_db"], "max_abs_lib_db": max_lib,
                    "abs_limit_db": c["abs_max_db"], "pass": rms_lib <= c["rms_max_db"] and max_lib <= c["abs_max_db"]},
        "d_no_worse_than_ffmpeg_fit": {"rms_lib_db": rms_lib, "rms_ff_db": rms_ff,
                                       "margin_db": c["rms_margin_over_ffmpeg_db"],
                                       "pass": rms_lib <= rms_ff + c["rms_margin_over_ffmpeg_db"]},
    }
    return {"criteria": criteria, "pass": all(v["pass"] for v in criteria.values())}


def surr8_gates(surr: dict, opus: dict, lags: pd.Series, taps: np.ndarray, edge_hz: float) -> dict:
    """R2-V1 to V6 on the signal-validation subset, with the unchanged Stage 2B tolerances."""
    tol = {k: v["value"] for k, v in design.r2_tolerances().items()}
    target, validation_edge = s2b.build_target(opus["h1_rel_db"])
    difference = surr["h1_rel_db"] - target
    rms = float(np.sqrt(np.mean(difference[band(edge_hz, tol["V3_rms_band_upper_hz"])] ** 2)))
    worst = float(np.max(np.abs(difference[band(edge_hz, tol["V3_abs_band_upper_hz"])])))
    symmetric = len(taps) % 2 == 1 and np.array_equal(taps, taps[::-1])
    min_coherence = float(np.min(surr["coherence"][FREQS <= tol["V2_up_to_hz"]]))
    bw = surr["coherent_bandwidth_hz"] - opus["coherent_bandwidth_hz"]
    hf = surr["coherent_hf_power_db"] - opus["coherent_hf_power_db"]
    stop = float(np.max(surr["h1_rel_db"][FREQS > tol["V6_from_hz"]]))
    gates = {
        "R2-V1": {"pass": bool(symmetric and (lags.abs() <= tol["V1_max_abs_lag_samples"]).all()),
                  "symmetric_odd_taps": bool(symmetric), "max_abs_lag_samples": int(lags.abs().max())},
        "R2-V2": {"pass": min_coherence >= tol["V2_min_coherence"], "min_coherence": min_coherence},
        "R2-V3": {"pass": rms <= tol["V3_rms_max_db"] and worst <= tol["V3_abs_max_db"], "rms_db": rms,
                  "max_abs_db": worst, "edge_hz": edge_hz, "validation_subset_opus_edge_hz": float(validation_edge)},
        "R2-V4": {"pass": abs(bw) <= tol["V4_max_hz"], "difference_hz": bw,
                  "surr8_hz": surr["coherent_bandwidth_hz"], "opus_hz": opus["coherent_bandwidth_hz"]},
        "R2-V5": {"pass": abs(hf) <= tol["V5_max_db"], "difference_db": hf,
                  "surr8_db": surr["coherent_hf_power_db"], "opus_db": opus["coherent_hf_power_db"]},
        "R2-V6": {"pass": stop <= tol["V6_max_db"], "max_h1_rel_db_above_4200_hz": stop},
    }
    return {"gates": gates, "pass": all(g["pass"] for g in gates.values())}


def save_filter(path, taps: np.ndarray, fit: dict, definition: str, reference_curve: np.ndarray) -> str:
    return lowpass.save_filter(path, taps, {
        "created_utc": design.s3.now(), "definition": definition,
        "procedure": "run_lowpass_validation build_target / design / constrain, unchanged (reviewer_pipeline."
                     "fit_stage2b_filter)",
        "edge_hz": fit["edge_hz"], "iterations": fit["iterations"],
        "reference_h1_rel_db": [float(v) for v in reference_curve],
        "target_db": [float(v) for v in fit["target_db"]], "design_db": [float(v) for v in fit["design_db"]],
        "measured_h1_rel_db": [float(v) for v in fit["measured_h1_rel_db"]],
    })


def load_frozen_filter(path, expected_sha256: str) -> tuple[np.ndarray, dict]:
    taps, record = lowpass.load_filter(path)
    if record["taps_sha256"] != expected_sha256:
        raise RuntimeError(f"{path}: taps differ from the code freeze")
    return taps, record


# ==================================================
# Signal-validation subset (R1-V, R2-V): signal measurements only
# ==================================================

SV_CELLS = ["lp", "silk_nb_linear_ref", "opus_8k_nb", "surr8", "opus_8k_nb_ffmpeg"]


def signal_validation(selection: dict, lp_dec_taps: np.ndarray, surr8_taps: np.ndarray | None):
    """
    Per utterance of the signal-validation subset: LP_DEC, SILK40 and OPUS decoded by the reference
    decoder (R1-V), SURR8 and OPUS decoded by the frozen FFmpeg path (R2-V). The per-utterance body
    of run_lowpass_confirmation.run_selection, with these cells. No transcript, no ASR.
    """
    root = s2c.subset_dir(design.SV_SUBSET)
    rows = []
    accumulators = {cell: s2b.TransferAccumulator() for cell in SV_CELLS if surr8_taps is not None or cell[:4] != "surr"}
    for number, entry in enumerate(selection["utterances"]):
        waveform, rate = torchaudio.load(root / entry["path"])
        if rate != SAMPLE_RATE or waveform.shape[0] != 1:
            raise RuntimeError(f"{entry['path']}: {rate} Hz, {waveform.shape[0]} channels")
        ids = {"dataset": design.SV_SUBSET, "dataset_index": number, "speaker_id": entry["speaker_id"],
               "chapter_id": entry["chapter_id"], "utterance_id": entry["utterance_id"]}
        cells = {}
        processed = lowpass.apply_zero_phase(waveform, lp_dec_taps)
        cells["lp"] = (processed, {"deterministic": torch.equal(processed, lowpass.apply_zero_phase(waveform, lp_dec_taps)),
                                   "output_dtype": str(processed.dtype)})
        for cell, settings in [("silk_nb_linear_ref", SILK_SETTINGS), ("opus_8k_nb", OPUS_SETTINGS)]:
            coded = encode_and_decode(waveform, settings, 1, True)
            configs = collections.Counter(opus_direct.packet_info(p)["configuration"] for p in coded["result"].packets)
            cells[cell] = (coded["refdec"], {"share_silk_nb": configs.get("SILK-NB", 0) / sum(configs.values()),
                                             "packets_identical": coded["refdec_info"]["packets_identical"],
                                             "samples_per_packet": coded["refdec_info"]["samples_per_packet"]})
            if cell == "opus_8k_nb":
                cells["opus_8k_nb_ffmpeg"] = (coded["ffmpeg"], {"share_silk_nb": configs.get("SILK-NB", 0)
                                                                / sum(configs.values())})
        if surr8_taps is not None:
            processed = lowpass.apply_zero_phase(waveform, surr8_taps)
            cells["surr8"] = (processed, {"deterministic": torch.equal(processed, lowpass.apply_zero_phase(waveform, surr8_taps))})
        for cell, (processed, extra) in cells.items():
            row, _, aligned = s2b.signal_metrics(waveform, processed)
            rows.append({**ids, "cell": cell, **row, **extra})
            accumulators[cell].add(*aligned)
    return pd.DataFrame(rows), {cell: acc.results() for cell, acc in accumulators.items()}


def r1_validation(rows: pd.DataFrame, transfer: dict, lp_dec_taps: np.ndarray) -> dict:
    """R1-V: the revised Stage 2B validation, unchanged, with reference-decoder cells."""
    cells = ["lp", "silk_nb_linear_ref", "opus_8k_nb"]
    part = rows[rows["cell"].isin(cells)].reset_index(drop=True)
    tr = {cell: transfer[cell] for cell in cells}
    original = s2b.evaluate_gates(design.SV_SUBSET, part, tr, lp_dec_taps)
    gates = [g for g in original if g["gate"] != 5]
    gates.insert(4, s2c.revised_gate5(design.SV_SUBSET, part, tr))
    return {"gates": gates, "original_gate5_information_only": [g for g in original if g["gate"] == 5],
            "pass": all(g["status"] == "PASS" for g in gates)}


# ==================================================
# Conditions of the ASR runs (and of E2)
# ==================================================

def confirmation_conditions(waveform: torch.Tensor, lp_taps: np.ndarray, r1: bool,
                            lp_libopus_taps: np.ndarray | None, surr8_taps: np.ndarray | None) -> dict:
    """REF, LP, OPUS, SILK; with r1, OPUS_REFDEC and SILK_REFDEC from the same Ogg bytes; LP_LIBOPUS, SURR8."""
    out = {"REF": (waveform.to(torch.float32), {}),
           "LP": (lowpass.apply_zero_phase(waveform, lp_taps).to(torch.float32), {})}
    for name, settings in [("OPUS", OPUS_SETTINGS), ("SILK", SILK_SETTINGS)]:
        coded = encode_and_decode(waveform, settings, EXPECTED_CONFIG[name], r1)
        out[name] = (coded["ffmpeg"], coded["summary"])
        if r1:
            out[f"{name}_REFDEC"] = (coded["refdec"], {**coded["summary"], **coded["refdec_info"]})
    if lp_libopus_taps is not None:
        out[design.LP_LIBOPUS] = (lowpass.apply_zero_phase(waveform, lp_libopus_taps).to(torch.float32), {})
    if surr8_taps is not None:
        out[design.SURR8] = (lowpass.apply_zero_phase(waveform, surr8_taps).to(torch.float32), {})
    return out


def sweep_conditions(waveform: torch.Tensor) -> dict:
    out = {}
    for name, settings in [(design.NB8, design.NB8_SETTINGS), (design.WB8, design.WB8_SETTINGS)]:
        coded = encode_and_decode(waveform, settings, EXPECTED_CONFIG[name], False)
        out[name] = (coded["ffmpeg"], {**coded["summary"],
                                       "readback_mismatches": ";".join(coded["readback_mismatches"])})
    return out


METRIC_SKIP = upipe.METRIC_SKIP


def signal_rows(reference: torch.Tensor, conditions: dict, names: list[str], vs_lp: list[str]) -> tuple[list[dict], dict]:
    """Descriptive only: frozen Stage 2B/3 metrics against REF and, for the codec conditions, against LP."""
    rows, aligned_pairs = [], {}
    for name in names:
        processed = conditions[name][0]
        metrics, _, aligned = s2b.signal_metrics(reference, processed)
        row = {"condition": name, **{f"vs_ref_{k}": v for k, v in metrics.items() if k not in METRIC_SKIP}}
        row["vs_ref_coherence_0_3500"] = audio.mean_coherence(*aligned)
        aligned_pairs[("REF", name)] = aligned
        if name in vs_lp:
            metrics, _, aligned = s2b.signal_metrics(conditions["LP"][0], processed)
            row.update({f"vs_lp_{k}": v for k, v in metrics.items() if k not in METRIC_SKIP + ("length_equal",)})
            row["vs_lp_coherence_0_3500"] = audio.mean_coherence(*aligned)
            aligned_pairs[("LP", name)] = aligned
        rows.append(row)
    return rows, aligned_pairs


def decoder_difference(ffmpeg: torch.Tensor, refdec: torch.Tensor) -> dict:
    """Descriptive decoder-difference measures at 16 kHz (R1)."""
    a = ffmpeg.detach().cpu().double().numpy().reshape(-1)
    b = refdec.detach().cpu().double().numpy().reshape(-1)
    if a.size != b.size:
        return {"same_length": False}
    diff = b - a
    energy = float(np.sum(diff ** 2))
    _, _, lag = common.align_waveforms(ffmpeg, refdec)
    return {"same_length": True, "bit_identical": bool(np.array_equal(a, b)),
            "snr_db": float("inf") if energy == 0 else float(10 * np.log10(np.sum(a ** 2) / energy)),
            "max_abs_difference": float(np.max(np.abs(diff))), "lag_samples": int(lag)}
