"""
Shared runtime of the TASLP-upgrade runners. Nothing here is run at design time.

Built only from frozen Stage 2B/3 functions, which are imported unchanged:
lowpass.apply_zero_phase, opus_direct.encode / decode_frozen_path / packet_info,
stage3_audio.codec_round_trip / load_filters / tensor_sha256 / mean_coherence /
pooled_transfer_rows, run_lowpass_validation.signal_metrics / TransferAccumulator,
stage3_asr.WhisperASR / Wav2Vec2ASR / Normaliser / score, common.align_waveforms.

Conditions
    LP                   frozen Stage 2B zero-phase low-pass (as Stage 3)
    SILK8 ... SILK40     Opus, forced NB, signal=voice, 8/12/16/24/40 kbit/s; every
                         other setting identical (B)
    OPUS                 the Stage 3 OPUS condition, through the unchanged Stage 3
                         codec_round_trip (A)
    OPUS8_LEVEL_MATCHED  OPUS times one scalar gain per utterance so that its RMS
                         equals LP's (A); nothing else is changed
"""

import collections
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torchaudio
from tqdm import tqdm

import common
import lowpass
import opus_direct
import run_lowpass_validation as stage2b
import run_stage3 as s3
import stage3_asr as asr
import stage3_audio as audio
import upgrade_stats as ustats


SAMPLE_RATE = audio.SAMPLE_RATE
LIBRI = Path(common.DATA_ROOT) / "LibriSpeech"
CHUNK_UTTERANCES = 8                       # as Stage 3
DECODED_SAMPLE_RATE = 48000                # torchaudio.load of Ogg Opus (FFmpeg)
EXPECTED_SWEEP_CONFIG = 1                  # RFC 6716 TOC config 1: SILK-only, NB, 20 ms
LEVEL_MATCHED = ustats.LEVEL_MATCHED

SWEEP_SETTINGS = {
    name: opus_direct.EncoderSettings(bitrate_bps=1000 * rate, bandwidth="NB", signal="voice")
    for name, rate in zip(ustats.SWEEP_CODED, ustats.SWEEP_RATES_KBPS)
}
OPUS_SETTINGS = audio.CODEC_SETTINGS["OPUS"]             # Stage 3 OPUS: 8 kbit/s, NB, signal=auto
SWEEP_TRANSFER_PAIRS = ([("REF", c) for c in ustats.SWEEP_CONDITIONS]
                        + [("LP", c) for c in ustats.SWEEP_CODED])


# ==================================================
# Codec round trip with packet details (B)
# ==================================================

def encode_decode(waveform: torch.Tensor, settings: opus_direct.EncoderSettings):
    """
    The steps of stage3_audio.codec_round_trip (encode, frozen decode path, resample
    to 16 kHz, float32), keeping the encoder result for packet validation.
    Identity with codec_round_trip is checked at calibration (E2).
    """
    result = opus_direct.encode(waveform, SAMPLE_RATE, settings)
    decoded, decoded_rate = opus_direct.decode_frozen_path(result.ogg)
    if decoded_rate != SAMPLE_RATE:
        decoded = torchaudio.functional.resample(decoded, decoded_rate, SAMPLE_RATE)
    return decoded.to(torch.float32), packet_summary(result, waveform.shape[-1], decoded_rate), result


def packet_summary(result: opus_direct.EncodeResult, num_samples: int, decoded_rate: int) -> dict:
    infos = [opus_direct.packet_info(p) for p in result.packets]
    duration = num_samples / SAMPLE_RATE
    configs = collections.Counter(i["config"] for i in infos)
    payload = sum(i["unpadded_bytes"] for i in infos)
    return {
        "decoded_sample_rate": int(decoded_rate),
        "num_packets": len(infos),
        "packet_configs": ";".join(f"{k}:{v}" for k, v in sorted(configs.items())),
        "share_expected_config": configs.get(EXPECTED_SWEEP_CONFIG, 0) / len(infos),
        "any_stereo": any(i["stereo"] for i in infos),
        "frame_count_codes": ";".join(str(c) for c in sorted({i["frame_count_code"] for i in infos})),
        "libopus_bandwidths": ";".join(sorted({i["libopus_bandwidth"] for i in infos})),
        "payload_bytes": payload,
        "payload_kbps": 8 * payload / duration / 1000,
        "ogg_bytes": len(result.ogg),
        "container_kbps": 8 * len(result.ogg) / duration / 1000,
        "ogg_sha256": hashlib.sha256(result.ogg).hexdigest(),
    }


def readback_mismatches(result: opus_direct.EncodeResult) -> list[str]:
    """Controls whose queried value differs from the requested one (gate V3)."""
    settings = result.settings
    requested = {**settings.ctl_values(), "application": opus_direct.APPLICATIONS[settings.application]}
    return sorted(name for name, value in requested.items() if result.queried.get(name) != value)


def sweep_conditions(waveform: torch.Tensor, filters: dict) -> dict:
    out = {"LP": (lowpass.apply_zero_phase(waveform, filters["LP"]).to(torch.float32), {})}
    for name, settings in SWEEP_SETTINGS.items():
        decoded, summary, _ = encode_decode(waveform, settings)
        out[name] = (decoded, summary)
    return out


# ==================================================
# Level matching (A)
# ==================================================

def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(x, dtype=np.float64) ** 2)))


def level_match(opus: torch.Tensor, lp: torch.Tensor) -> tuple[torch.Tensor, float]:
    """
    OPUS8_LEVEL_MATCHED = float32(g * float64(OPUS)), g = RMS(LP) / RMS(OPUS), RMS over
    every sample of the 16 kHz float32 waveforms given to the recognisers, in float64.
    No clipping, limiting, re-alignment or other normalisation.
    """
    x = opus.detach().cpu().double().numpy().reshape(-1)
    y = lp.detach().cpu().double().numpy().reshape(-1)
    if x.size != y.size:
        raise ValueError("OPUS and LP lengths differ")
    rms_x, rms_y = rms(x), rms(y)
    if not (np.isfinite(rms_x) and np.isfinite(rms_y) and rms_x > 0):
        raise ValueError("RMS must be finite and positive")
    gain = rms_y / rms_x
    matched = torch.from_numpy((gain * x).astype(np.float32)).reshape(opus.shape)
    return matched, gain


def level_conditions(waveform: torch.Tensor, filters: dict) -> dict:
    lp = lowpass.apply_zero_phase(waveform, filters["LP"]).to(torch.float32)
    opus, info = audio.codec_round_trip(waveform, OPUS_SETTINGS)       # unchanged Stage 3 path
    matched, gain = level_match(opus, lp)
    return {"LP": (lp, {}), "OPUS": (opus, info),
            LEVEL_MATCHED: (matched, {"gain": gain, "gain_db": 20 * np.log10(gain)})}


# ==================================================
# Audio statistics and signal descriptors
# ==================================================

def audio_row(name: str, processed: torch.Tensor, reference: torch.Tensor, info: dict) -> dict:
    x = processed.detach().cpu().double().numpy().reshape(-1)
    ref = reference.detach().cpu().double().numpy().reshape(-1)
    out_rms, ref_rms = rms(x), rms(ref)
    _, _, lag = common.align_waveforms(reference, processed)
    row = {
        "condition": name, "sample_rate": SAMPLE_RATE, "num_samples": x.size,
        "length_equals_ref": x.size == ref.size,
        "input_rms_dbfs": 20 * np.log10(max(ref_rms, 1e-12)),
        "output_rms_dbfs": 20 * np.log10(max(out_rms, 1e-12)),
        "rms_change_db": 20 * np.log10(max(out_rms, 1e-12) / max(ref_rms, 1e-12)),
        "peak": float(np.max(np.abs(x))),
        "clip_count": int(np.sum(np.abs(x) >= 1.0)),
        "nonfinite_count": int(np.sum(~np.isfinite(x))),
        "lag_vs_ref_samples": int(lag),
        "waveform_sha256": audio.tensor_sha256(processed),
    }
    for key, value in (info or {}).items():
        row[key] = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
    return row


METRIC_SKIP = ("reference_num_samples", "processed_num_samples", "aligned_num_samples")


def sweep_signal_rows(reference: torch.Tensor, conditions: dict) -> tuple[list[dict], dict]:
    """Descriptive only: frozen Stage 2B/3 metrics against REF and, for coded conditions, against LP."""
    rows, aligned_pairs = [], {}
    lp = conditions["LP"][0]
    for name in ustats.SWEEP_CONDITIONS:
        processed = conditions[name][0]
        metrics, _, aligned = stage2b.signal_metrics(reference, processed)
        row = {"condition": name, **{f"vs_ref_{k}": v for k, v in metrics.items() if k not in METRIC_SKIP}}
        row["vs_ref_coherence_0_3500"] = audio.mean_coherence(*aligned)
        aligned_pairs[("REF", name)] = aligned
        if name != "LP":
            metrics, _, aligned = stage2b.signal_metrics(lp, processed)
            row.update({f"vs_lp_{k}": v for k, v in metrics.items()
                        if k not in METRIC_SKIP + ("length_equal",)})
            row["vs_lp_coherence_0_3500"] = audio.mean_coherence(*aligned)
            aligned_pairs[("LP", name)] = aligned
        rows.append(row)
    return rows, aligned_pairs


def new_accumulators(pairs) -> dict:
    return {pair: stage2b.TransferAccumulator() for pair in pairs}


def accumulators_to_arrays(accumulators: dict) -> dict:
    return {f"{a}->{b}:{field}": getattr(acc, field)
            for (a, b), acc in accumulators.items() for field in ["sxx", "syy", "sxy", "sxy_mirror"]}


def accumulators_from_arrays(arrays, pairs) -> dict:
    accumulators = new_accumulators(pairs)
    for (a, b), acc in accumulators.items():
        for field in ["sxx", "syy", "sxy", "sxy_mirror"]:
            setattr(acc, field, np.array(arrays[f"{a}->{b}:{field}"]))
    return accumulators


# ==================================================
# Recognition (Stage 3 recognisers, settings and scoring, unchanged)
# ==================================================

class Recognisers:

    def __init__(self, whisper=None, wav2vec2=None, normaliser=None):
        self.whisper = whisper or asr.WhisperASR()
        self.wav2vec2 = wav2vec2 or asr.Wav2Vec2ASR()
        self.normaliser = normaliser or asr.Normaliser()

    @classmethod
    def from_stage3_pipeline(cls, pipeline: s3.Pipeline) -> "Recognisers":
        return cls(pipeline.whisper, pipeline.wav2vec2, pipeline.normaliser)


def load_reference(entry: dict) -> torch.Tensor:
    waveform, rate = torchaudio.load(LIBRI / entry["path"])
    if rate != SAMPLE_RATE or waveform.shape[0] != 1:
        raise RuntimeError(f"{entry['path']}: {rate} Hz, {waveform.shape[0]} channels")
    return waveform


def process_chunk(set_name: str, entries: list[dict], generate, conditions: list[str],
                  rec: Recognisers, signal_fn=None, accumulators=None, check=None) -> list[dict]:
    """Stage 3's per-chunk order: audio rows, signal rows, wav2vec2 per condition, batched Whisper."""
    records, queue = [], []
    for entry in entries:
        waveform = load_reference(entry)
        generated = generate(waveform)
        ids = {"set": set_name, "utterance": entry["utterance"], "subset": entry["subset"],
               "speaker_id": entry["speaker_id"]}
        reference_norm = rec.normaliser(entry["reference"])
        record = {"utterance": entry["utterance"], "audio": [], "signal": [], "asr": [], "metrics": []}
        for name in conditions:
            processed, info = generated[name]
            record["audio"].append({**ids, **audio_row(name, processed, waveform, info)})
        if check is not None:
            check(entry, record["audio"])
        if signal_fn is not None:
            rows, aligned_pairs = signal_fn(waveform, generated)
            record["signal"] = [{**ids, **row} for row in rows]
            for pair, aligned in aligned_pairs.items():
                accumulators[pair].add(*aligned)
        for name in conditions:
            processed = generated[name][0]
            add_asr(record, ids, name, "wav2vec2", entry["reference"], reference_norm,
                    rec.wav2vec2.transcribe(processed), rec)
            queue.append((record, ids, name, entry["reference"], reference_norm, processed[0].numpy()))
        records.append(record)
    for start in range(0, len(queue), asr.WHISPER_BATCH_SIZE):
        batch = queue[start:start + asr.WHISPER_BATCH_SIZE]
        texts = rec.whisper.transcribe([item[5] for item in batch])
        for (record, ids, name, reference, reference_norm, _), text in zip(batch, texts):
            add_asr(record, ids, name, "whisper", reference, reference_norm, text, rec)
    return records


def add_asr(record, ids, condition, model, reference, reference_norm, hypothesis, rec) -> None:
    hypothesis_norm = rec.normaliser(hypothesis)
    record["asr"].append({**ids, "condition": condition, "model": model, "reference": reference,
                          "reference_normalised": reference_norm, "hypothesis": hypothesis,
                          "hypothesis_normalised": hypothesis_norm})
    record["metrics"].append({**ids, "condition": condition, "model": model,
                              **asr.score(reference_norm, hypothesis_norm),
                              "hypothesis_normalised": hypothesis_norm})


def run_set(set_name: str, utterances: list[dict], out_dir: Path, generate, conditions: list[str],
            rec: Recognisers, code_hashes: dict, selection_sha256: str, signal_fn=None,
            transfer_pairs=None, check=None) -> str:
    """
    Resumable single run, as paper/run_stage3.run_set: one progress line per utterance,
    no rerun once the sealed outputs manifest exists. Returns the manifest hash.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / "outputs_sha256.json"
    if final.exists():
        raise RuntimeError(f"{set_name} has already been decoded ({final}); single run only")
    progress = out_dir / "progress.jsonl"
    state = out_dir / "transfer_accumulators.npz"
    done = [json.loads(line)["utterance"] for line in progress.read_text().splitlines()] \
        if progress.exists() else []
    accumulators = new_accumulators(transfer_pairs) if transfer_pairs else None
    if done and accumulators is not None:
        arrays = np.load(state)
        if int(arrays["n_done"]) != len(done):
            raise RuntimeError("accumulator checkpoint does not match progress; not resumable")
        accumulators = accumulators_from_arrays(arrays, transfer_pairs)

    log_path = out_dir / "run_log.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {
        "set": set_name, "selection_sha256": selection_sha256, "sessions": []}
    session = {"started_utc": s3.now(), "resumed_after": len(done), "chunks": 0, "code_sha256": code_hashes}
    log["sessions"].append(session)
    pending = [u for u in utterances if u["utterance"] not in set(done)]
    started = time.time()
    with tqdm(total=len(utterances), initial=len(done), desc=set_name, unit="utt") as bar:
        for start in range(0, len(pending), CHUNK_UTTERANCES):
            chunk = pending[start:start + CHUNK_UTTERANCES]
            records = process_chunk(set_name, chunk, generate, conditions, rec, signal_fn,
                                    accumulators, check)
            if accumulators is not None:
                np.savez(out_dir / "transfer_accumulators.tmp.npz", n_done=len(done) + start + len(chunk),
                         **accumulators_to_arrays(accumulators))
            with progress.open("a") as file:
                for record in records:
                    file.write(json.dumps(s3.native(record)) + "\n")
            if accumulators is not None:
                os.replace(out_dir / "transfer_accumulators.tmp.npz", state)
            session["chunks"] += 1
            session["seconds"] = time.time() - started
            log_path.write_text(json.dumps(log, indent=1))
            bar.update(len(chunk))

    records = {}
    for line in progress.read_text().splitlines():
        record = json.loads(line)
        records[record["utterance"]] = record
    ordered = [records[u["utterance"]] for u in utterances]
    kinds = [("audio", "audio_manifest.csv"), ("asr", "asr_outputs.csv"), ("metrics", "utterance_metrics.csv")]
    if signal_fn is not None:
        kinds.append(("signal", "signal_metrics.csv"))
    for kind, filename in kinds:
        pd.DataFrame([row for record in ordered for row in record[kind]]).to_csv(out_dir / filename, index=False)
    if accumulators is not None:
        summary, curves = audio.pooled_transfer_rows(accumulators)
        pd.DataFrame(summary).assign(set=set_name).to_csv(out_dir / "pooled_transfer.csv", index=False)
        pd.DataFrame(curves).assign(set=set_name).to_csv(out_dir / "pooled_transfer_curves.csv", index=False)
    session["finished_utc"] = s3.now()
    session["seconds"] = time.time() - started
    session["seconds_per_utterance"] = session["seconds"] / max(len(pending), 1)
    log_path.write_text(json.dumps(log, indent=1))
    hashes = {f.name: s3.file_sha256(f) for f in sorted(out_dir.glob("*.csv"))}
    return s3.write_sealed(final, {"set": set_name, "created_utc": s3.now(), "n_utterances": len(ordered),
                                   "selection_sha256": selection_sha256, "files": hashes}, "outputs_sha256")
