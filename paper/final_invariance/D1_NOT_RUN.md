# D1 — External generalisation check: not run

Status: **NOT RUN.** No D1 audio was generated and no D1 recognition was run. Nothing was
downloaded except one 368 kB metadata file (the FLEURS en_us test TSV), which was read to check
for speaker labels. It sits in the session scratch space and is not in the repository.

## 1. What was checked (2026-09-28, before any D1 decision)

The instructions allow D1 only if two things are locally available or cheap to obtain,
reproducibly and without licensing ambiguity:

- a modern recogniser from a meaningfully different family (Conformer, RNN-T or transducer);
- a speech corpus that is not LibriSpeech.

**Recognisers available locally.**

- Hugging Face cache: `openai/whisper-large-v3` only.
- torch hub: the torchaudio wav2vec2-base-960h checkpoint, EnCodec 24 kHz and ResNet-18.
- Toolkits: NeMo, SpeechBrain, ESPnet, k2, sherpa-onnx and onnxruntime are not installed.
- **No different-family recogniser is available locally.**

**Corpora available locally.**

- The data root holds LibriSpeech only.
- A search of the Linux file system and of the mounted Windows drives found no Common Voice,
  TED-LIUM, VCTK, TIMIT, AMI, VoxPopuli, FLEURS, GigaSpeech, Earnings, CHiME, LJSpeech or
  VOiCES corpus. The torchaudio tutorial cache holds one VOiCES file, which is not a corpus.
- **No non-LibriSpeech corpus is available locally.**

**Candidates that could be obtained.** Checked through Hugging Face metadata only.

| Candidate | Role | Licence (HF metadata) | Size | Usable here? |
|---|---|---|---|---|
| `nvidia/parakeet-rnnt-0.6b` (rev `1b6b548f70b9`) | FastConformer + RNN-T | CC-BY-4.0, not gated | ~2.4 GB, transformers format | Weights yes. Feature extractor needs `librosa` (see §2). |
| `nvidia/parakeet-ctc-0.6b` | FastConformer + CTC | CC-BY-4.0, not gated | 2.4 GB | Same `librosa` requirement. |
| `nvidia/parakeet-tdt-0.6b-v3` | FastConformer + TDT (multilingual) | CC-BY-4.0, not gated | transformers format | Same `librosa` requirement. |
| `google/fleurs` en_us test | read Wikipedia sentences | CC-BY-4.0, not gated | 290 MB audio + 368 kB TSV | Yes. 647 recordings of 350 sentences, gender labels, **no speaker IDs**. |
| `facebook/voxpopuli` | parliamentary speech | licence tags `cc0-1.0` **and** `other` | — | Excluded: licensing ambiguity. |
| Common Voice, GigaSpeech, SPGISpeech | — | gated or with terms of use | — | Excluded: terms would have to be accepted on the user's behalf. |
| TED-LIUM 3 | — | CC BY-NC-ND | — | Excluded: the no-derivatives clause is ambiguous for codec-processed copies. |
| VCTK | — | CC-BY-4.0 | ~11 GB | Excluded: large, and part of the NeMo English training data for Parakeet. |

## 2. Why D1 was not run

1. **The recogniser cannot be run reproducibly in the frozen environment.**
   - transformers 5.17's `ParakeetFeatureExtractor` is declared to require `librosa`. It uses
     `librosa.filters.mel` for the mel filterbank, and `librosa` is absent from both Python
     environments on this machine.
   - Installing `librosa` pulls in `numba`, `scipy`, `scikit-learn` and `soxr`. That risks
     changing numpy 2.5.2 and other packages in the single analysis environment, whose versions
     every sealed analysis (Stage 3, R4, A1, B1) records and re-checks before it runs.
   - The alternatives are a second, separately built CUDA environment or a runtime patch of the
     feature extractor. Either would add an unfrozen toolchain. Its preprocessing could not be
     checked against NeMo's reference implementation offline.
   - That is not "cheap and reproducible". A wrong mel front end would produce a generalisation
     result that says nothing about the codec.
2. **The only clearly licensed cheap corpus lacks the paper's inference unit.** FLEURS releases
   no speaker IDs. The paired speaker-cluster bootstrap of every other analysis would have to be
   replaced by a sentence-cluster bootstrap. That unit ignores within-speaker dependence, so its
   intervals are anti-conservative to an unknown degree, and there was no calibration basis for
   choosing it. Under the pass rules ("DO NOT GUESS"), it was not chosen overnight.
3. **Resources.** The shared GPU was occupied by other projects' jobs for most of the night, and
   the authorised analyses A1 and B1 took precedence. The instructions forbid downloading models
   "merely because time is available".

## 3. Best future pair

- **Recogniser:** `nvidia/parakeet-rnnt-0.6b` (FastConformer encoder, RNN-T decoder, English,
  CC-BY-4.0). Pin the Hugging Face revision; greedy transducer decoding. Run it in a dedicated,
  separately frozen environment (NeMo, or transformers with `librosa`). First validate the
  pipeline against the model's published LibriSpeech test-clean WER on a small calibration
  sample.
- **Corpus:** FLEURS en_us test (CC-BY-4.0, 647 recordings), all recordings, selected from
  metadata. Declare the sentence-cluster bootstrap unit in advance and state the missing speaker
  labels as a limitation. A CC-BY corpus with speaker labels that is held out from the
  recogniser's training data would be preferable if one is available.
- **Design (as the pass specifies):**
  - REF, the frozen Stage 2B LP control unchanged, and OPUS8 with the Stage 3 settings.
  - Freeze the model revision, decoding, normalisation (the Stage 3 Whisper English normaliser),
    selection and bootstrap unit before recognition.
  - The single question: does OPUS8 − LP > LP − REF hold in direction? A reversal would be
    reported prominently.

## 4. Consequence for the manuscript (rule H)

D1 was not run, so generalisation beyond LibriSpeech and the two recognisers stays future work.
No claim changes.
