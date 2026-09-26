"""
Stage 3 ASR systems, transcript normalisation and scoring.

Model A  Whisper large-v3 (attention encoder-decoder), Hugging Face
         openai/whisper-large-v3 at a pinned revision, float16, greedy
         decoding (num_beams=1), temperature 0 without fallback, English
         transcription, no timestamps, no prompt, no VAD. Utterances are
         <= 30 s (selection rule), so every input is a single padded
         30 s window.
Model B  wav2vec2-base-960h (CTC), torchaudio WAV2VEC2_ASR_BASE_960H with the
         frozen ELEC5305 greedy CTC decoder (paper/common.py, verbatim).

Both systems are used as released: no fine-tuning, no adaptation per
condition. The same normaliser (Whisper EnglishTextNormalizer from the pinned
tokenizer) is applied to references and to every hypothesis of both models.
"""

import hashlib
from pathlib import Path

import jiwer
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from transformers import WhisperForConditionalGeneration, WhisperProcessor, WhisperTokenizer

import common


SAMPLE_RATE = 16000
MAX_DURATION_S = 30.0

WHISPER_REPO = "openai/whisper-large-v3"
WHISPER_REVISION = "06f233fe06e710322aca913c1bc4249a0d71fce1"
WHISPER_DTYPE = torch.float16
WHISPER_BATCH_SIZE = 16
WHISPER_GENERATE = {
    "language": "en",
    "task": "transcribe",
    "num_beams": 1,
    "do_sample": False,
    "return_timestamps": False,
}

WAV2VEC2_BUNDLE = "torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H"
WAV2VEC2_CHECKPOINT = "wav2vec2_fairseq_base_ls960_asr_ls960.pth"

MODELS = ["whisper", "wav2vec2"]
MODEL_LABELS = {"whisper": "Whisper large-v3", "wav2vec2": "wav2vec2-base-960h"}


def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class WhisperASR:

    def __init__(self, device: str = "cuda") -> None:
        self.device = device
        self.processor = WhisperProcessor.from_pretrained(WHISPER_REPO, revision=WHISPER_REVISION)
        self.model = WhisperForConditionalGeneration.from_pretrained(
            WHISPER_REPO, revision=WHISPER_REVISION, dtype=WHISPER_DTYPE,
        ).to(device).eval()

    def transcribe(self, waveforms: list[np.ndarray]) -> list[str]:
        for waveform in waveforms:
            if waveform.size > MAX_DURATION_S * SAMPLE_RATE:
                raise ValueError("input longer than Whisper's 30 s window")
        features = self.processor.feature_extractor(
            [np.asarray(w, dtype=np.float32) for w in waveforms],
            sampling_rate=SAMPLE_RATE, return_tensors="pt",
        ).input_features.to(self.device, WHISPER_DTYPE)
        with torch.inference_mode():
            ids = self.model.generate(features, **WHISPER_GENERATE)
        return self.processor.batch_decode(ids, skip_special_tokens=True)

    def settings(self) -> dict:
        generation = {k: v for k, v in self.model.generation_config.to_dict().items()
                      if not isinstance(v, (list, dict)) or k in ("suppress_tokens",
                                                                  "begin_suppress_tokens")}
        extractor = self.processor.feature_extractor.to_dict()
        return {
            "repository": WHISPER_REPO,
            "revision": WHISPER_REVISION,
            "dtype": str(WHISPER_DTYPE),
            "batch_size": WHISPER_BATCH_SIZE,
            "generate_kwargs": WHISPER_GENERATE,
            "temperature_fallback": "none (temperature 0 only; no compression-ratio, "
                                    "log-prob or no-speech thresholds)",
            "prompt": "none (forced decoder prefix: <|startoftranscript|><|en|>"
                      "<|transcribe|><|notimestamps|>)",
            "vad": "none",
            "attention_implementation": self.model.config._attn_implementation,
            "generation_config": generation,
            "feature_extractor": {k: extractor[k] for k in (
                "feature_size", "sampling_rate", "hop_length", "chunk_length", "n_fft",
                "n_samples", "padding_value") if k in extractor},
            "weights_sha256": file_sha256(hf_hub_download(
                WHISPER_REPO, "model.safetensors", revision=WHISPER_REVISION)),
            "max_duration_s": MAX_DURATION_S,
        }


class Wav2Vec2ASR:

    def __init__(self) -> None:
        common.load_model()

    def transcribe(self, waveform: torch.Tensor) -> str:
        return common.recognise(waveform, SAMPLE_RATE)

    def settings(self) -> dict:
        checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / WAV2VEC2_CHECKPOINT
        return {
            "bundle": WAV2VEC2_BUNDLE,
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": file_sha256(checkpoint),
            "decoder": "greedy CTC, blank id 0, repeated tokens collapsed "
                       "(paper/common.py decode(), verbatim from the frozen pipeline)",
            "language_model": "none",
            "device": str(common.device),
            "dtype": "float32",
            "input_normalisation": "none (bundle does not normalise the waveform)",
        }


class Normaliser:
    """Whisper EnglishTextNormalizer from the pinned tokenizer revision."""

    def __init__(self) -> None:
        self.tokenizer = WhisperTokenizer.from_pretrained(WHISPER_REPO, revision=WHISPER_REVISION)

    def __call__(self, text: str) -> str:
        return self.tokenizer.normalize(text)

    def settings(self) -> dict:
        import transformers
        return {
            "normaliser": "transformers WhisperTokenizer.normalize -> EnglishTextNormalizer",
            "transformers_version": transformers.__version__,
            "tokenizer": f"{WHISPER_REPO}@{WHISPER_REVISION}",
            "spelling_map_sha256": file_sha256(hf_hub_download(
                WHISPER_REPO, "normalizer.json", revision=WHISPER_REVISION)),
            "spelling_map_entries": len(self.tokenizer.english_spelling_normalizer or {}),
        }


def score(reference: str, hypothesis: str) -> dict:
    """Word and character edit counts of normalised strings (jiwer defaults)."""
    words = jiwer.process_words(reference, hypothesis)
    chars = jiwer.process_characters(reference, hypothesis)
    n_words = words.hits + words.substitutions + words.deletions
    n_chars = chars.hits + chars.substitutions + chars.deletions
    word_errors = words.substitutions + words.deletions + words.insertions
    char_errors = chars.substitutions + chars.deletions + chars.insertions
    return {
        "n_words": n_words,
        "hits": words.hits,
        "substitutions": words.substitutions,
        "deletions": words.deletions,
        "insertions": words.insertions,
        "word_errors": word_errors,
        "wer": word_errors / n_words,
        "n_chars": n_chars,
        "char_errors": char_errors,
        "cer": char_errors / n_chars,
    }
