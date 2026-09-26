"""
Direct libopus encoding with explicit, recorded encoder settings.

The frozen pipeline encodes with `ffmpeg -codec:a libopus -b:a <rate>`,
which cannot force the coded audio bandwidth (ffmpeg only exposes
OPUS_SET_MAX_BANDWIDTH through -cutoff). This module calls the system
libopus through ctypes so that OPUS_SET_BANDWIDTH can be set, and writes a
standard Ogg Opus file (RFC 7845) so that the output is decoded by exactly
the same torchaudio.load path as the frozen pipeline.

Design rules:

- Every encoder control is set explicitly, in a fixed order, and every value
  is read back from the encoder after encoding (EncodeResult.queried).
- The defaults of EncoderSettings are the settings that the frozen ffmpeg
  command passes to libopus (application audio, unconstrained VBR,
  complexity 10, 20 ms frames, no FEC, no DTX, 0% expected loss, maximum
  bandwidth FB, automatic signal type); only `bandwidth` and `bitrate_bps`
  are varied by the paper conditions.
- Input is 16-bit PCM passed to opus_encode(); LibriSpeech is 16-bit FLAC,
  so the conversion from float is exact (and is checked).
- Encoder lookahead is compensated exactly as ffmpeg does: the Ogg pre-skip
  is the lookahead (in 48 kHz samples), the input is zero-padded by the
  lookahead, and the final granule position trims the decoded output to the
  original length.
"""

import ctypes
import math
import os
import struct
import tempfile
from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np
import torch
import torchaudio

import common


# ==================================================
# libopus constants (opus_defines.h, libopus 1.4)
# ==================================================

OPUS_OK = 0
OPUS_AUTO = -1000

APPLICATIONS = {"voip": 2048, "audio": 2049, "restricted_lowdelay": 2051}
SIGNALS = {"auto": OPUS_AUTO, "voice": 3001, "music": 3002}
BANDWIDTHS = {"AUTO": OPUS_AUTO, "NB": 1101, "MB": 1102, "WB": 1103,
              "SWB": 1104, "FB": 1105}
FRAME_DURATIONS = {"arg": 5000, 2.5: 5001, 5.0: 5002, 10.0: 5003, 20.0: 5004,
                   40.0: 5005, 60.0: 5006}

# Encoder CTL request numbers: (set, get)
CTL = {
    "application": (4000, 4001),
    "bitrate": (4002, 4003),
    "max_bandwidth": (4004, 4005),
    "vbr": (4006, 4007),
    "bandwidth": (4008, 4009),
    "complexity": (4010, 4011),
    "inband_fec": (4012, 4013),
    "packet_loss_perc": (4014, 4015),
    "dtx": (4016, 4017),
    "vbr_constraint": (4020, 4021),
    "force_channels": (4022, 4023),
    "signal": (4024, 4025),
    "lsb_depth": (4036, 4037),
    "expert_frame_duration": (4040, 4041),
    "prediction_disabled": (4042, 4043),
}
GET_LOOKAHEAD = 4027
GET_SAMPLE_RATE = 4029

OGG_SAMPLE_RATE = 48000
MAX_PACKET_BYTES = 4000


# ==================================================
# Library
# ==================================================

def _load_libopus() -> ctypes.CDLL:
    library = ctypes.CDLL("libopus.so.0")

    library.opus_get_version_string.restype = ctypes.c_char_p
    library.opus_strerror.restype = ctypes.c_char_p
    library.opus_strerror.argtypes = [ctypes.c_int]

    library.opus_encoder_create.restype = ctypes.c_void_p
    library.opus_encoder_create.argtypes = [
        ctypes.c_int32, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int),
    ]
    library.opus_encoder_destroy.restype = None
    library.opus_encoder_destroy.argtypes = [ctypes.c_void_p]
    library.opus_encode.restype = ctypes.c_int32
    library.opus_encode.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_int,
        ctypes.c_char_p, ctypes.c_int32,
    ]
    # opus_encoder_ctl is variadic: no argtypes, arguments are passed as
    # explicit ctypes values

    library.opus_packet_get_bandwidth.restype = ctypes.c_int
    library.opus_packet_get_bandwidth.argtypes = [ctypes.c_char_p]
    library.opus_packet_get_nb_frames.restype = ctypes.c_int
    library.opus_packet_get_nb_frames.argtypes = [ctypes.c_char_p, ctypes.c_int32]
    library.opus_packet_get_samples_per_frame.restype = ctypes.c_int
    library.opus_packet_get_samples_per_frame.argtypes = [ctypes.c_char_p, ctypes.c_int32]
    library.opus_packet_unpad.restype = ctypes.c_int32
    library.opus_packet_unpad.argtypes = [ctypes.c_char_p, ctypes.c_int32]

    return library


libopus = _load_libopus()


def libopus_version() -> str:
    return libopus.opus_get_version_string().decode()


def libopus_path() -> str:
    """Real path of the libopus shared object loaded into this process."""
    with open("/proc/self/maps") as maps:
        for line in maps:
            if "libopus.so" in line:
                return os.path.realpath(line.split()[-1])
    return "unknown"


def _check(code: int, what: str) -> None:
    if code != OPUS_OK:
        raise RuntimeError(f"{what}: {libopus.opus_strerror(code).decode()} ({code})")


# ==================================================
# Settings
# ==================================================

@dataclass(frozen=True)
class EncoderSettings:
    """Every libopus encoder control that is set. Defaults = frozen ffmpeg."""

    bitrate_bps: int
    bandwidth: str = "AUTO"            # OPUS_SET_BANDWIDTH (forced bandwidth)
    max_bandwidth: str = "FB"          # OPUS_SET_MAX_BANDWIDTH (libopus/ffmpeg default)
    sample_rate: int = 16000           # encoder input rate
    channels: int = 1
    application: str = "audio"         # ffmpeg default
    vbr: bool = True                   # ffmpeg default "-vbr on"
    vbr_constraint: bool = False       # ffmpeg "-vbr on" = unconstrained
    complexity: int = 10               # ffmpeg default
    frame_ms: float = 20.0             # ffmpeg default "-frame_duration 20"
    signal: str = "auto"
    packet_loss_perc: int = 0          # ffmpeg default
    inband_fec: bool = False           # ffmpeg default
    dtx: bool = False                  # ffmpeg default
    lsb_depth: int = 24                # libopus default (ffmpeg does not set it)
    prediction_disabled: bool = False  # libopus default
    expert_frame_duration: str = "arg"  # frame size given by each encode call
    force_channels: str = "auto"

    def ctl_values(self) -> dict[str, int]:
        """Values passed to the SET controls, in the order they are applied."""
        return {
            "complexity": self.complexity,
            "vbr": int(self.vbr),
            "vbr_constraint": int(self.vbr_constraint),
            "bitrate": self.bitrate_bps,
            "max_bandwidth": BANDWIDTHS[self.max_bandwidth],
            "bandwidth": BANDWIDTHS[self.bandwidth],
            "signal": SIGNALS[self.signal],
            "packet_loss_perc": self.packet_loss_perc,
            "inband_fec": int(self.inband_fec),
            "dtx": int(self.dtx),
            "lsb_depth": self.lsb_depth,
            "prediction_disabled": int(self.prediction_disabled),
            "expert_frame_duration": FRAME_DURATIONS[self.expert_frame_duration],
            "force_channels": OPUS_AUTO if self.force_channels == "auto"
            else int(self.force_channels),
        }

    @property
    def frame_samples(self) -> int:
        samples = self.sample_rate * self.frame_ms / 1000.0
        if samples != int(samples):
            raise ValueError("frame_ms does not give a whole number of samples")
        return int(samples)


# ==================================================
# Packets
# ==================================================

BANDWIDTH_NAMES = {v: k for k, v in BANDWIDTHS.items() if k != "AUTO"}


def configuration_duration_ms(config: int) -> float:
    """Frame duration of a TOC configuration (RFC 6716, Table 2)."""
    if config < 12:
        return [10.0, 20.0, 40.0, 60.0][config % 4]
    if config < 16:
        return [10.0, 20.0][config % 2]
    return [2.5, 5.0, 10.0, 20.0][config % 4]


def unpadded_length(packet: bytes) -> int:
    """Packet length after removing Opus padding (CBR fills packets with it)."""
    buffer = ctypes.create_string_buffer(packet, len(packet))
    length = libopus.opus_packet_unpad(buffer, len(packet))
    if length < 0:
        _check(length, "opus_packet_unpad")
    return length


def packet_info(packet: bytes) -> dict[str, object]:
    """
    TOC fields of one Opus packet, decoded twice: with the frozen parser
    (common.configuration_name) and with libopus's own packet functions.
    """
    config = packet[0] >> 3
    name = common.configuration_name(config)
    mode, bandwidth = name.split("-")
    return {
        "config": config,
        "configuration": name,
        "mode": mode,
        "bandwidth": bandwidth,
        "stereo": bool(packet[0] & 0x04),
        "frame_count_code": packet[0] & 0x03,
        "frame_ms": configuration_duration_ms(config),
        "libopus_bandwidth": BANDWIDTH_NAMES.get(
            libopus.opus_packet_get_bandwidth(packet), "invalid"),
        "libopus_frames": libopus.opus_packet_get_nb_frames(packet, len(packet)),
        "libopus_samples_48k": libopus.opus_packet_get_samples_per_frame(
            packet, OGG_SAMPLE_RATE),
        "bytes": len(packet),
        "unpadded_bytes": unpadded_length(packet),
    }


# ==================================================
# Ogg Opus writer (RFC 3533 pages, RFC 7845 mapping)
# ==================================================

def _crc_table() -> list[int]:
    table = []
    for i in range(256):
        r = i << 24
        for _ in range(8):
            r = ((r << 1) ^ 0x04C11DB7) if r & 0x80000000 else (r << 1)
        table.append(r & 0xFFFFFFFF)
    return table


_CRC_TABLE = _crc_table()


def ogg_crc(data: bytes) -> int:
    """Ogg page checksum: CRC-32, polynomial 0x04C11DB7, no reflection."""
    crc = 0
    for byte in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC_TABLE[((crc >> 24) & 0xFF) ^ byte]
    return crc


def ogg_page(packets: list[bytes], granule: int, serial: int, sequence: int,
             flags: int) -> bytes:
    lacing = bytearray()
    for packet in packets:
        lacing += bytes([255]) * (len(packet) // 255) + bytes([len(packet) % 255])
    if len(lacing) > 255:
        raise ValueError("too many segments for one Ogg page")
    page = bytearray(
        struct.pack("<4sBBqIIIB", b"OggS", 0, flags, granule, serial,
                    sequence, 0, len(lacing))
        + lacing + b"".join(packets)
    )
    struct.pack_into("<I", page, 22, ogg_crc(bytes(page)))
    return bytes(page)


OGG_SERIAL = 0x50415052            # fixed, so files are byte-reproducible
OGG_PACKETS_PER_PAGE = 50          # 1 s of 20 ms packets (ffmpeg default page duration)
OPUS_TAGS_COMMENTS = ["ENCODER=paper/opus_direct.py"]


def write_ogg_opus(packets: list[bytes], pre_skip: int, input_sample_rate: int,
                   final_granule: int, samples_per_packet_48k: int,
                   channels: int = 1) -> bytes:
    """
    Ogg Opus stream: OpusHead page, OpusTags page, audio pages.

    Granule positions count 48 kHz samples including the pre-skip; the
    final page carries the end-trimmed granule position.
    """
    if not (samples_per_packet_48k * (len(packets) - 1) < final_granule
            <= samples_per_packet_48k * len(packets)):
        raise ValueError("end trimming must fall inside the last packet")

    head = b"OpusHead" + struct.pack(
        "<BBHIhB", 1, channels, pre_skip, input_sample_rate, 0, 0
    )
    vendor = libopus_version().encode()
    tags = b"OpusTags" + struct.pack("<I", len(vendor)) + vendor
    tags += struct.pack("<I", len(OPUS_TAGS_COMMENTS))
    for comment in OPUS_TAGS_COMMENTS:
        tags += struct.pack("<I", len(comment)) + comment.encode()

    pages = [
        ogg_page([head], 0, OGG_SERIAL, 0, 0x02),
        ogg_page([tags], 0, OGG_SERIAL, 1, 0x00),
    ]

    sequence = 2
    start = 0
    while start < len(packets):
        end = start
        segments = 0
        while (end < len(packets) and end - start < OGG_PACKETS_PER_PAGE
               and segments + len(packets[end]) // 255 + 1 <= 255):
            segments += len(packets[end]) // 255 + 1
            end += 1
        last = end == len(packets)
        granule = final_granule if last else samples_per_packet_48k * end
        pages.append(ogg_page(packets[start:end], granule, OGG_SERIAL, sequence,
                              0x04 if last else 0x00))
        sequence += 1
        start = end

    return b"".join(pages)


def read_opus_head(ogg: bytes) -> dict[str, int]:
    """Pre-skip, channel count and input rate from the OpusHead packet."""
    start = 27 + ogg[26]
    _, channels, pre_skip, input_rate, gain, family = struct.unpack(
        "<BBHIhB", ogg[start + 8:start + 19]
    )
    return {"channels": channels, "pre_skip": pre_skip,
            "input_sample_rate": input_rate, "output_gain": gain,
            "mapping_family": family}


def last_granule(ogg: bytes) -> int:
    position = ogg.rfind(b"OggS")
    return struct.unpack("<q", ogg[position + 6:position + 14])[0]


# ==================================================
# Encoding
# ==================================================

@dataclass
class EncodeResult:
    ogg: bytes
    packets: list[bytes]
    settings: EncoderSettings
    queried: dict[str, int]          # every control read back after encoding
    num_input_samples: int           # at settings.sample_rate
    lookahead_samples: int           # at settings.sample_rate
    padding_samples: int             # zeros appended (lookahead + frame fill)
    pre_skip_48k: int
    final_granule_48k: int
    end_trim_48k: int                # decoded samples discarded after the end

    def summary(self) -> dict[str, object]:
        return {
            **{f"setting_{k}": v for k, v in asdict(self.settings).items()},
            **{f"queried_{k}": v for k, v in self.queried.items()},
            "num_input_samples": self.num_input_samples,
            "lookahead_samples": self.lookahead_samples,
            "padding_samples": self.padding_samples,
            "pre_skip_48k": self.pre_skip_48k,
            "final_granule_48k": self.final_granule_48k,
            "end_trim_48k": self.end_trim_48k,
            "num_packets": len(self.packets),
            "payload_bytes": sum(len(p) for p in self.packets),
            "file_size_bytes": len(self.ogg),
        }


def to_int16(waveform: torch.Tensor) -> np.ndarray:
    """Exact float -> int16 conversion; fails if the input is not 16-bit PCM."""
    samples = waveform.detach().cpu().double().numpy().reshape(-1) * 32768.0
    pcm = np.round(samples)
    if not np.array_equal(pcm, samples):
        raise ValueError("waveform is not exactly representable as 16-bit PCM")
    if pcm.min() < -32768 or pcm.max() > 32767:
        raise ValueError("waveform outside the 16-bit range")
    return pcm.astype(np.int16)


def encode(waveform: torch.Tensor, sample_rate: int,
           settings: EncoderSettings) -> EncodeResult:
    """Encode a mono 16-bit waveform to an Ogg Opus byte string."""

    if sample_rate != settings.sample_rate:
        raise ValueError(
            f"input is {sample_rate} Hz, encoder is set to {settings.sample_rate} Hz; "
            "resampling is not done implicitly"
        )
    if waveform.dim() != 2 or waveform.shape[0] != 1 or settings.channels != 1:
        raise ValueError("only mono input of shape (1, N) is supported")
    if OGG_SAMPLE_RATE % sample_rate:
        raise ValueError("sample rate must divide 48 kHz")

    pcm = to_int16(waveform)
    num_input = len(pcm)

    error = ctypes.c_int()
    encoder = ctypes.c_void_p(libopus.opus_encoder_create(
        settings.sample_rate, settings.channels,
        APPLICATIONS[settings.application], ctypes.byref(error),
    ))
    _check(error.value, "opus_encoder_create")

    try:
        for name, value in settings.ctl_values().items():
            _check(
                libopus.opus_encoder_ctl(encoder, ctypes.c_int(CTL[name][0]),
                                         ctypes.c_int32(value)),
                f"set {name}={value}",
            )

        lookahead = ctypes.c_int32()
        _check(libopus.opus_encoder_ctl(encoder, ctypes.c_int(GET_LOOKAHEAD),
                                        ctypes.byref(lookahead)), "get lookahead")

        frame = settings.frame_samples
        num_frames = math.ceil((num_input + lookahead.value) / frame)
        padded = np.zeros(num_frames * frame, dtype=np.int16)
        padded[:num_input] = pcm

        buffer = ctypes.create_string_buffer(MAX_PACKET_BYTES)
        packets = []
        for f in range(num_frames):
            chunk = np.ascontiguousarray(padded[f * frame:(f + 1) * frame])
            length = libopus.opus_encode(
                encoder, chunk.ctypes.data_as(ctypes.POINTER(ctypes.c_int16)),
                frame, buffer, MAX_PACKET_BYTES,
            )
            if length < 0:
                _check(length, f"opus_encode frame {f}")
            packets.append(buffer.raw[:length])

        queried = {}
        for name, (_, get_request) in CTL.items():
            value = ctypes.c_int32()
            _check(libopus.opus_encoder_ctl(encoder, ctypes.c_int(get_request),
                                            ctypes.byref(value)), f"get {name}")
            queried[name] = value.value
        rate = ctypes.c_int32()
        _check(libopus.opus_encoder_ctl(encoder, ctypes.c_int(GET_SAMPLE_RATE),
                                        ctypes.byref(rate)), "get sample rate")
        queried["sample_rate"] = rate.value
        queried["lookahead"] = lookahead.value
    finally:
        libopus.opus_encoder_destroy(encoder)

    upsample = OGG_SAMPLE_RATE // sample_rate
    pre_skip = lookahead.value * upsample
    final_granule = pre_skip + num_input * upsample
    samples_per_packet = frame * upsample

    ogg = write_ogg_opus(packets, pre_skip, sample_rate, final_granule,
                         samples_per_packet, settings.channels)

    return EncodeResult(
        ogg=ogg,
        packets=packets,
        settings=settings,
        queried=queried,
        num_input_samples=num_input,
        lookahead_samples=lookahead.value,
        padding_samples=num_frames * frame - num_input,
        pre_skip_48k=pre_skip,
        final_granule_48k=final_granule,
        end_trim_48k=num_frames * samples_per_packet - final_granule,
    )


# ==================================================
# Decoding: the frozen pipeline's path
# ==================================================

def decode_frozen_path(ogg: bytes, directory: Optional[str] = None
                       ) -> tuple[torch.Tensor, int]:
    """
    Decode with torchaudio.load from a .opus file, exactly as the frozen
    process_audio() / compress_audio() decode ffmpeg's output.
    """
    with tempfile.TemporaryDirectory(dir=directory) as temp_dir:
        path = os.path.join(temp_dir, "compressed.opus")
        with open(path, "wb") as file:
            file.write(ogg)
        waveform, sample_rate = torchaudio.load(path)
    return waveform, int(sample_rate)
