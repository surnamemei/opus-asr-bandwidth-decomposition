"""
Unit tests for paper/opus_direct.py (Stage 2A). Synthetic signals only; no
LibriSpeech evaluation data is used.

Run from the repository root:
    /home/mei/elec5305-project/.venv/bin/python -m unittest discover -s paper/tests -v
"""

import math
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch
import torchaudio


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "paper"))
os.chdir(REPO_ROOT)

import common  # noqa: E402
import opus_direct  # noqa: E402
import run_opus_validation  # noqa: E402
import run_reproduce  # noqa: E402


SAMPLE_RATE = 16000


def synthetic_speech(seconds: float = 2.0, seed: int = 0) -> torch.Tensor:
    """Harmonic signal with 150 Hz pitch up to 8 kHz, syllable-rate envelope
    and noise, quantised to 16 bit."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    f0 = 150.0 * (1.0 + 0.05 * np.sin(2 * np.pi * 3.0 * t))
    phase = 2 * np.pi * np.cumsum(f0) / SAMPLE_RATE
    voiced = sum(np.sin(k * phase) / k for k in range(1, 53))
    envelope = 0.5 * (1.0 + np.sin(2 * np.pi * 4.0 * t))
    x = envelope * voiced + 0.05 * rng.standard_normal(len(t))
    x = 0.3 * x / np.max(np.abs(x))
    return torch.from_numpy(np.round(x * 32768.0) / 32768.0).float().unsqueeze(0)


def ogg_pages(data: bytes):
    """(offset, header+body bytes) for every Ogg page."""
    position = 0
    while position < len(data):
        assert data[position:position + 4] == b"OggS"
        segments = data[position + 26]
        body = sum(data[position + 27:position + 27 + segments])
        end = position + 27 + segments + body
        yield position, data[position:end]
        position = end


class TestLibrary(unittest.TestCase):

    def test_same_libopus_as_ffmpeg(self):
        self.assertEqual(opus_direct.libopus_version(), "libopus 1.4")
        self.assertEqual(
            opus_direct.libopus_path(),
            run_reproduce.libopus_version()["path"],
        )


class TestEncoder(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.waveform = synthetic_speech()
        cls.num_samples = cls.waveform.shape[-1]

    def encode(self, bitrate, bandwidth):
        return opus_direct.encode(
            self.waveform, SAMPLE_RATE,
            opus_direct.EncoderSettings(bitrate_bps=bitrate, bandwidth=bandwidth),
        )

    def test_every_control_reads_back_as_set(self):
        for bandwidth in ["WB", "NB"]:
            settings = opus_direct.EncoderSettings(bitrate_bps=8000, bandwidth=bandwidth)
            result = opus_direct.encode(self.waveform, SAMPLE_RATE, settings)
            with self.subTest(bandwidth=bandwidth):
                for name, value in settings.ctl_values().items():
                    self.assertEqual(result.queried[name], value, name)
                self.assertEqual(
                    result.queried["application"],
                    opus_direct.APPLICATIONS[settings.application],
                )
                self.assertEqual(result.queried["sample_rate"], SAMPLE_RATE)

    def test_lookahead_and_trimming(self):
        result = self.encode(12000, "WB")
        # libopus: Fs/400 + Fs/250 for the audio application
        self.assertEqual(result.lookahead_samples, SAMPLE_RATE // 400 + SAMPLE_RATE // 250)
        self.assertEqual(result.pre_skip_48k, 3 * result.lookahead_samples)
        self.assertEqual(
            len(result.packets),
            math.ceil((self.num_samples + result.lookahead_samples) / 320),
        )
        self.assertEqual(result.final_granule_48k,
                         result.pre_skip_48k + 3 * self.num_samples)
        self.assertTrue(0 <= result.end_trim_48k < 960)

    def test_forced_bandwidth_in_every_packet(self):
        for bitrate in [12000, 8000]:
            for bandwidth in ["WB", "NB"]:
                with self.subTest(bitrate=bitrate, bandwidth=bandwidth):
                    result = self.encode(bitrate, bandwidth)
                    self.assertEqual(
                        {opus_direct.packet_info(p)["bandwidth"] for p in result.packets},
                        {bandwidth},
                    )

    def test_toc_parsers_agree(self):
        for packet in self.encode(8000, "WB").packets:
            info = opus_direct.packet_info(packet)
            self.assertEqual(info["libopus_bandwidth"], info["bandwidth"])
            self.assertEqual(info["libopus_frames"], 1)
            self.assertEqual(info["libopus_samples_48k"], 960)

    def test_unpad_detects_cbr_padding_only(self):
        vbr = self.encode(8000, "WB")
        self.assertTrue(all(opus_direct.unpadded_length(p) == len(p) for p in vbr.packets))
        cbr = opus_direct.encode(
            self.waveform, SAMPLE_RATE,
            opus_direct.EncoderSettings(bitrate_bps=8000, bandwidth="WB", vbr=False),
        )
        self.assertTrue(any(opus_direct.unpadded_length(p) < len(p) for p in cbr.packets))

    def test_deterministic(self):
        self.assertEqual(self.encode(8000, "WB").ogg, self.encode(8000, "WB").ogg)

    def test_auto_bandwidth_matches_frozen_ffmpeg_packets(self):
        for bitrate in [12000, 8000]:
            with self.subTest(bitrate=bitrate):
                _, ffmpeg_packets = run_reproduce.encode_opus_file(
                    self.waveform, SAMPLE_RATE, f"{bitrate // 1000}k"
                )
                self.assertEqual(self.encode(bitrate, "AUTO").packets, ffmpeg_packets)

    def test_rejects_non_16_bit_input(self):
        waveform = self.waveform.clone()
        waveform[0, 10] = 0.123456789
        with self.assertRaises(ValueError):
            opus_direct.encode(waveform, SAMPLE_RATE,
                               opus_direct.EncoderSettings(bitrate_bps=8000))

    def test_rejects_implicit_resampling(self):
        with self.assertRaises(ValueError):
            opus_direct.encode(self.waveform, 48000,
                               opus_direct.EncoderSettings(bitrate_bps=8000))


class TestOgg(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.waveform = synthetic_speech(seconds=3.3, seed=1)
        cls.result = opus_direct.encode(
            cls.waveform, SAMPLE_RATE,
            opus_direct.EncoderSettings(bitrate_bps=12000, bandwidth="NB"),
        )

    def test_crc_matches_ffmpeg_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            wav_path = os.path.join(temp_dir, "input.wav")
            opus_path = os.path.join(temp_dir, "output.opus")
            torchaudio.save(wav_path, self.waveform, SAMPLE_RATE)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path,
                            "-codec:a", "libopus", "-b:a", "12k", opus_path], check=True)
            data = Path(opus_path).read_bytes()
        for _, page in ogg_pages(data):
            stored = struct.unpack("<I", page[22:26])[0]
            zeroed = page[:22] + b"\0\0\0\0" + page[26:]
            self.assertEqual(opus_direct.ogg_crc(zeroed), stored)

    def test_own_pages_have_valid_crc_and_flags(self):
        pages = list(ogg_pages(self.result.ogg))
        for number, (_, page) in enumerate(pages):
            stored = struct.unpack("<I", page[22:26])[0]
            self.assertEqual(opus_direct.ogg_crc(page[:22] + b"\0" * 4 + page[26:]), stored)
            self.assertEqual(struct.unpack("<I", page[18:22])[0], number)
        self.assertEqual(pages[0][1][5], 0x02)   # beginning of stream
        self.assertEqual(pages[-1][1][5], 0x04)  # end of stream

    def test_packets_round_trip_through_frozen_parser(self):
        parsed = run_opus_validation.parse_ogg_packets(self.result.ogg)
        self.assertEqual(parsed, self.result.packets)

    def test_opus_head(self):
        head = opus_direct.read_opus_head(self.result.ogg)
        self.assertEqual(head["pre_skip"], self.result.pre_skip_48k)
        self.assertEqual(head["channels"], 1)
        self.assertEqual(head["input_sample_rate"], SAMPLE_RATE)
        self.assertEqual(opus_direct.last_granule(self.result.ogg),
                         self.result.final_granule_48k)

    def test_frozen_decode_path_trims_to_input_length(self):
        decoded, rate = opus_direct.decode_frozen_path(self.result.ogg)
        self.assertEqual(rate, 48000)
        self.assertEqual(decoded.shape, (1, 3 * self.waveform.shape[-1]))


class TestBandLsd(unittest.TestCase):

    def test_full_band_equals_frozen_lsd(self):
        reference = synthetic_speech(seed=2)
        processed = synthetic_speech(seed=3)
        ref_mag = common.magnitude_spectrogram(reference)
        proc_mag = common.magnitude_spectrogram(processed)
        frequencies = np.linspace(0, SAMPLE_RATE / 2, common.N_FFT // 2 + 1)
        _, lsd_db, _ = common.spectral_distortion(ref_mag, proc_mag)
        full = run_opus_validation.band_lsd(ref_mag, proc_mag, frequencies,
                                            0.0, 8000.0, include_high=True)
        self.assertAlmostEqual(full, lsd_db, places=4)


if __name__ == "__main__":
    unittest.main()
