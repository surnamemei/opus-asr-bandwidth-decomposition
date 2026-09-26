# Transcript normalisation specification

Frozen with the Stage 3 spec (SHA-256 `ac5a36a01f50e7643cc73bbbc2f75ce44fe34b0730ec828082084ba1643b5219`).

One policy, applied identically to LibriSpeech references and to every hypothesis of both ASR systems, before scoring: the Whisper `EnglishTextNormalizer` ({"normaliser": "transformers WhisperTokenizer.normalize -> EnglishTextNormalizer", "transformers_version": "5.17.0", "tokenizer": "openai/whisper-large-v3@06f233fe06e710322aca913c1bc4249a0d71fce1", "spelling_map_sha256": "bf1c507dc8724ca9cf9903640dacfb69dae2f00edee4f21ceba106a7392f26dd", "spelling_map_entries": 1740}).

It lower-cases; removes punctuation and bracketed/filler tokens (hmm, uh, um); standardises apostrophes and expands common contractions; converts spelled-out numbers and number words to digits; maps British to American spellings (1,740-entry map); and collapses whitespace.

Scoring: jiwer word alignment on the normalised strings (default transforms); WER = (S + D + I) / reference words. CER from jiwer character alignment (secondary).

Examples:

| input | normalised |
|---|---|
| HE'S TWENTY FIVE YEARS OLD AND WON'T GO TO MISTER SMITH'S | he is 25 years old and will not go to mister smith is |
|  He's 25 years old, and won't go to Mr. Smith's! | he is 25 years old and will not go to mister smith is |
| COLOUR OF THE HONOUR | color of the honor |
| Hmm, uh, I think so. | i think so |
| THE ANTARCTIC OCEAN IS NINETEEN FORTY SEVEN FEET DEEP | the antarctic ocean is 1947 feet deep |

The policy was fixed before any pilot or confirmation decoding and is not changed after seeing codec results.
