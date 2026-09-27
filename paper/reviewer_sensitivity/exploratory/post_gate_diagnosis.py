"""
EXPLORATORY - POST HOC. Diagnosis of the R1-V and R2-V failures (RS3, signal-validation subset).

Run after the frozen gates had failed and R1 and R2 were STOPPED. It is not part of any rule,
cannot change any outcome, and is not in the code freeze. Signal measurements only (Stage 2B
calibration utterances and the signal-validation subset); no transcript, no ASR.

    python paper/reviewer_sensitivity/exploratory/post_gate_diagnosis.py

Writes results_paper/reviewer_sensitivity/exploratory/post_gate_diagnosis.json (sealed, so that
the recorded numbers cannot drift) and POST_GATE_DIAGNOSIS.md.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parents[1] / "taslp_upgrade"), str(HERE.parents[1])]

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402
import torch                # noqa: E402
import torchaudio           # noqa: E402

import common               # noqa: E402
import reviewer_design as design     # noqa: E402
import reviewer_pipeline as rp       # noqa: E402
import run_lowpass_confirmation as s2c  # noqa: E402
import run_lowpass_validation as s2b    # noqa: E402
import run_stage3 as s3              # noqa: E402
import upgrade_pipeline as upipe     # noqa: E402

F = s2b.FREQS
OUT = design.RESULTS / "exploratory"
LABEL = ("EXPLORATORY - POST HOC: computed after the frozen R1-V and R2-V gates failed and R1 and R2 were STOPPED; "
         "not part of any rule; cannot change any outcome; code outside the code freeze")


def at(curve, hz):
    return float(np.asarray(curve)[int(np.argmin(np.abs(F - hz)))])


def rms(x, mask):
    return float(np.sqrt(np.mean(np.asarray(x)[mask] ** 2)))


def band(lo, hi, closed_low=True):
    return ((F >= lo) if closed_low else (F > lo)) & (F <= hi)


def fractional_delay(ref, proc):
    """Sub-sample delay of proc against ref: parabolic interpolation of the cross-correlation peak."""
    r, p = ref.double().numpy().reshape(-1), proc.double().numpy().reshape(-1)
    n = 1 << int(np.ceil(np.log2(len(r) + len(p))))
    c = np.fft.irfft(np.fft.rfft(p, n) * np.conj(np.fft.rfft(r, n)), n)
    k = int(np.argmax(np.concatenate([c[-8:], c[:9]]))) - 8
    y0, y1, y2 = c[(k - 1) % n], c[k % n], c[(k + 1) % n]
    return float(k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2))


def shifted(proc, delay):
    p = proc.double().numpy().reshape(-1)
    n = 2 * len(p)
    spectrum = np.fft.rfft(p, n) * np.exp(2j * np.pi * np.fft.rfftfreq(n) * delay)
    return torch.from_numpy(np.fft.irfft(spectrum, n)[:len(p)]).unsqueeze(0).float()


def silk40_curves(waveforms):
    """libopus SILK40 |H1| under three alignments, and FFmpeg SILK40 under two."""
    acc = {k: s2b.TransferAccumulator() for k in ["libopus_frozen", "libopus_subsample", "libopus_fixed0",
                                                   "ffmpeg_frozen", "ffmpeg_fixed2"]}
    delays = []
    for w in waveforms:
        coded = rp.encode_and_decode(w, rp.SILK_SETTINGS, 1, True)
        lib, ff = coded["refdec"], coded["ffmpeg"]
        acc["libopus_frozen"].add(*common.align_waveforms(w, lib)[:2])
        d = fractional_delay(w, lib)
        delays.append(d)
        acc["libopus_subsample"].add(w, shifted(lib, d))
        acc["libopus_fixed0"].add(w, lib)
        acc["ffmpeg_frozen"].add(*common.align_waveforms(w, ff)[:2])
        n = w.shape[-1] - 2
        acc["ffmpeg_fixed2"].add(w[:, :n], ff[:, 2:2 + n])
    return {k: v.results()["h1_rel_db"] for k, v in acc.items()}, np.array(delays)


def main():
    if (OUT / "post_gate_diagnosis.json").exists():
        raise RuntimeError("the exploratory record exists")
    calibration = s3.read_sealed(design.CALIBRATION_REPORT, "report_sha256")
    signal = s3.read_sealed(design.RESULTS / "validation" / "signal_report.json", "report_sha256")
    rows = pd.read_csv(design.RESULTS / "validation" / "signal_rows.csv")
    e2 = pd.read_csv(design.RESULTS / "calibration" / "e2_audio_manifest.csv")
    curves = pd.read_csv(design.RESULTS / "validation" / "signal_transfer_curves.csv")
    h = {c: g.sort_values("frequency_hz")["h1_rel_db"].to_numpy() for c, g in curves.groupby("cell")}
    r1_cal = pd.read_csv(design.RESULTS / "calibration" / "r1_curves.csv")
    surr = json.loads(design.SURR8_FILTER.read_text())["metadata"]
    target_val, edge_val = s2b.build_target(h["opus_8k_nb_ffmpeg"])

    # 1. alignment lags
    lags = {"signal_validation_subset": {c: {int(k): int(v) for k, v in g.value_counts().sort_index().items()}
                                         for c, g in rows.groupby("cell")["alignment_lag_samples"]},
            "stage3_calibration_set_e2": {c: {int(k): int(v) for k, v in g.value_counts().sort_index().items()}
                                          for c, g in e2.groupby("condition")["lag_vs_ref_samples"]}}

    # 2. R1: where LP_LIBOPUS misses the libopus SILK40 curve on the validation subset
    d1 = h["lp"] - h["silk_nb_linear_ref"]
    r1 = {"rms_db_3000_3900": rms(d1, band(3000, 3900)), "rms_db_3900_4200": rms(d1, band(3900, 4200, False)),
          "rows": [{"hz": hz, "silk40_libopus_calibration": at(r1_cal["silk40_libopus_h1_rel_db"], hz),
                    "silk40_libopus_validation": at(h["silk_nb_linear_ref"], hz), "lp_libopus_validation": at(h["lp"], hz)}
                   for hz in [2000, 2500, 3000, 3500, 3750, 3812.5, 4000, 4062.5, 4125]]}

    # 3. R2: where SURR8 misses the validation target
    d2 = h["surr8"] - target_val
    mask = band(surr["edge_hz"], 4150)
    worst = int(np.where(mask)[0][np.argmax(np.abs(d2[mask]))])
    r2 = {"validation_edge_hz": float(edge_val), "rms_db_edge_4000": rms(d2, band(surr["edge_hz"], 4000)),
          "rms_db_4000_4200": rms(d2, band(4000, 4200, False)), "largest_error": {"hz": float(F[worst]), "db": float(d2[worst])},
          "rows": [{"hz": hz, "opus_calibration": at(surr["reference_h1_rel_db"], hz), "opus_validation": at(h["opus_8k_nb_ffmpeg"], hz),
                    "target_calibration": at(surr["target_db"], hz), "target_validation": at(target_val, hz),
                    "surr8_validation": at(h["surr8"], hz)} for hz in [2000, 2500, 3000, 3500, 3812.5, 4000, 4062.5, 4093.75, 4125]],
          "calibration_fit_rms_db_edge_4000": rms(np.array(surr["measured_h1_rel_db"]) - np.array(surr["target_db"]),
                                                  band(surr["edge_hz"], 4000)),
          "calibration_fit_rms_db_4000_4200": rms(np.array(surr["measured_h1_rel_db"]) - np.array(surr["target_db"]),
                                                  band(4000, 4200, False))}

    # 4. SILK40 under different alignments, both sets
    cal_w = rp.stage2b_calibration_waveforms()
    sel = s3.read_sealed(design.SV_SELECTION, "selection_sha256")
    root = s2c.subset_dir(design.SV_SUBSET)
    val_w = [torchaudio.load(root / u["path"])[0] for u in sel["utterances"]]
    cal, d_cal = silk40_curves(cal_w)
    val, d_val = silk40_curves(val_w)
    edge_band = band(3000, 4150)
    alignment = {
        "libopus_delay_samples_16k": {"calibration": {"median": float(np.median(d_cal)), "min": float(d_cal.min()), "max": float(d_cal.max())},
                                      "validation": {"median": float(np.median(d_val)), "min": float(d_val.min()), "max": float(d_val.max())}},
        "max_abs_calibration_minus_validation_db_3000_4150": {k: float(np.max(np.abs(cal[k][edge_band] - val[k][edge_band]))) for k in cal},
        "libopus_minus_ffmpeg_fixed_alignment_calibration_db_3000_4150": {
            "max_abs": float(np.max(np.abs((cal["libopus_fixed0"] - cal["ffmpeg_fixed2"])[edge_band]))),
            "rms": rms(cal["libopus_fixed0"] - cal["ffmpeg_fixed2"], edge_band)},
        "rows": [{"hz": hz, **{f"{k}_calibration": at(cal[k], hz) for k in cal}, **{f"{k}_validation": at(val[k], hz) for k in val}}
                 for hz in [2000, 3000, 3500, 3750, 3812.5, 4000, 4062.5, 4125]],
    }

    # 5. waveform-level decoder difference on the Stage 3 calibration set, unaligned and aligned
    snr = []
    for u in s3.load_selection("calibration")["utterances"]:
        w = upipe.load_reference(u)
        for name, settings in [("OPUS", rp.OPUS_SETTINGS), ("SILK", rp.SILK_SETTINGS)]:
            coded = rp.encode_and_decode(w, settings, 1, True)
            a, b = coded["ffmpeg"].double().numpy().reshape(-1), coded["refdec"].double().numpy().reshape(-1)
            ra, pa, lag = common.align_waveforms(coded["ffmpeg"], coded["refdec"])
            ra, pa = ra.double().numpy().reshape(-1), pa.double().numpy().reshape(-1)
            snr.append({"condition": name, "lag": int(lag),
                        "snr_unaligned_db": float(10 * np.log10(np.sum(a ** 2) / np.sum((b - a) ** 2))),
                        "snr_aligned_db": float(10 * np.log10(np.sum(ra ** 2) / np.sum((pa - ra) ** 2)))})
    snr = pd.DataFrame(snr).groupby("condition").agg(lag=("lag", "median"), snr_unaligned_db_median=("snr_unaligned_db", "median"),
                                                     snr_aligned_db_median=("snr_aligned_db", "median"),
                                                     snr_aligned_db_min=("snr_aligned_db", "min")).reset_index()

    record = {
        "label": LABEL, "created_utc": s3.now(),
        "inputs": {"calibration_report_sha256": calibration["report_sha256"], "signal_report_sha256": signal["report_sha256"]},
        "alignment_lags": lags, "r1_validation_misfit": r1, "r2_validation_misfit": r2,
        "silk40_alignment_dependence": alignment, "decoder_waveform_difference_calibration_set": snr.to_dict(orient="records"),
        "reading": [
            "The libopus chain has a sub-sample, content-dependent delay (about 0.45 samples at 16 kHz); the frozen per-utterance "
            "integer alignment puts its utterances at lag 0 or 1, whereas every FFmpeg-decoded utterance is at lag 2.",
            "Under that alignment the pooled |H1| of the libopus chain depends on each set's lag mix, so the libopus SILK40 curve "
            "moved between the calibration set and the signal-validation subset; with one fixed alignment for every utterance it is "
            "as stable across sets as FFmpeg's. This most likely drove the R1-REUSE failure and the R1-V gate 6 failure.",
            "Measured with one fixed alignment, libopus's band edge is genuinely flatter to about 3.8 kHz than FFmpeg's and then "
            "steeper.",
            "The R2-V3 misfit is concentrated at 4.0-4.2 kHz, more than 20 dB down, where the held-out Opus 8 kbit/s curve is less "
            "steep than on dev-clean and SURR8 (whose corrections did not converge there) over-attenuates.",
            "These readings are exploratory. Any successor analysis needs an approved, sealed amendment and is reported as post hoc.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    digest = s3.write_sealed(OUT / "post_gate_diagnosis.json", record, "diagnosis_sha256")
    (OUT / "POST_GATE_DIAGNOSIS.md").write_text(render(record, digest))
    print(f"exploratory post-gate diagnosis sealed: {digest}")


def render(r: dict, digest: str) -> str:
    a = r["silk40_alignment_dependence"]
    lines = [
        "# R1-V and R2-V failures: post-gate diagnosis", "",
        f"**{r['label']}.**", "",
        f"Record: `post_gate_diagnosis.json` (SHA-256 `{digest}`), from "
        f"`paper/reviewer_sensitivity/exploratory/post_gate_diagnosis.py`.", "",
        "## Readings (exploratory)", "", *[f"- {s}" for s in r["reading"]], "",
        "## Numbers", "",
        f"- Alignment lags against REF on the signal-validation subset: {json.dumps(r['alignment_lags']['signal_validation_subset'])}.",
        f"- libopus delay (samples at 16 kHz): {json.dumps(a['libopus_delay_samples_16k'])}.",
        "- Largest calibration-minus-validation difference of the SILK40 |H1| over 3.0-4.15 kHz (dB): "
        f"{json.dumps({k: round(v, 2) for k, v in a['max_abs_calibration_minus_validation_db_3000_4150'].items()})}.",
        "- libopus minus FFmpeg SILK40 |H1|, one fixed alignment, calibration set, 3.0-4.15 kHz: "
        f"max {a['libopus_minus_ffmpeg_fixed_alignment_calibration_db_3000_4150']['max_abs']:.2f} dB, "
        f"RMS {a['libopus_minus_ffmpeg_fixed_alignment_calibration_db_3000_4150']['rms']:.2f} dB.",
        f"- R1-V gate 6 misfit (LP_LIBOPUS minus libopus SILK40): RMS {r['r1_validation_misfit']['rms_db_3000_3900']:.2f} dB over "
        f"3.0-3.9 kHz, {r['r1_validation_misfit']['rms_db_3900_4200']:.2f} dB over 3.9-4.2 kHz.",
        f"- R2-V3 misfit (SURR8 minus validation target): RMS {r['r2_validation_misfit']['rms_db_edge_4000']:.2f} dB from the edge "
        f"to 4 kHz, {r['r2_validation_misfit']['rms_db_4000_4200']:.2f} dB over 4.0-4.2 kHz; largest "
        f"{r['r2_validation_misfit']['largest_error']['db']:.2f} dB at {r['r2_validation_misfit']['largest_error']['hz']:g} Hz; "
        f"validation-subset edge {r['r2_validation_misfit']['validation_edge_hz']:g} Hz.",
        f"- Decoder waveform difference, Stage 3 calibration set: {json.dumps(r['decoder_waveform_difference_calibration_set'])}.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
