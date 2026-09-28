# Cover letter (draft)

<!-- Draft for the TASLP submission of taslp_submission.md. Replace every [bracketed placeholder] before
sending; nothing here states author details that are not yet known. -->

[Date]

The Editor-in-Chief
IEEE Transactions on Audio, Speech, and Language Processing

Dear Editor,

We submit the manuscript "Bandwidth Removal Reproduces Only Part of the ASR Penalty of 8-kbit/s
Opus" for consideration as a regular paper in the IEEE Transactions on Audio, Speech, and
Language Processing.

At low bitrates, speech codecs such as Opus switch to narrowband operation, so the loss of audio
bandwidth and other coding effects arrive together. The resulting penalty on automatic speech
recognition (ASR) is therefore hard to attribute. Earlier bandwidth-versus-codec comparisons for
other codecs have reached different conclusions. For Opus at 8 kbit/s (SILK narrowband in libopus
1.4), the paper contributes a controlled isolation and quantification of the bandwidth part of the
penalty, together with targeted robustness and sensitivity tests. The isolation uses a linear
low-pass control, fitted to the codec's measured high-rate linear transfer function and validated
on held-out speakers. The quantification is a paired decomposition of the penalty into a bandwidth
component and a codec-specific residual, estimated for two fixed pretrained recognisers, Whisper
large-v3 and wav2vec2-base-960h.

The main finding is that the validated control reproduces only a minority of the 8 kbit/s penalty.
A substantial residual remains in both recognisers, both LibriSpeech test subsets and an independent
pilot.

The strongest robustness result is an inclusive best-linear attribution, adapted from the
projection-based decomposition of speech-enhancement artefacts. It assigns the gain, spectral tilt,
roll-off, phase and delay of the actual codec output to the linear component, and even then
residual penalties of 0.74 and 2.32 percentage points remain. The residual also persists under RMS
level matching and alternative error weightings, and its dependence on the coding rate is
quantified. Separate sensitivity analyses of the total penalty quantify the effect of the decoder
implementation and the encoder application mode; they do not decompose the penalty, so no
decoder- or application-invariant residual is claimed.

We report the bandwidth shares, but treat them as sequential, path-dependent and metric-dependent
attributions rather than causal fractions; the Whisper share in particular is imprecise. We do not
claim to have identified the mechanism of the residual.

The scope is deliberately narrow: one encoder version, two pretrained recognisers, read English
speech from LibriSpeech, and no transmission impairments. Within that scope, we believe the paper
fits the Transactions' interests in speech coding, robust ASR, and controlled signal-processing
evaluation of recognition systems.

On transparency:

- The primary design was specified and version-sealed before any evaluation audio was decoded.
- Each later analysis was specified separately before any of its audio was encoded, and was run
  once.
- Two analyses that stopped at a failed validation criterion, before any recognition, are retained
  and reported.
- The supplementary material gives the validation, robustness and decision details.
- Code, analysis records and per-utterance outputs are archived at [REPOSITORY_URL].

[Confirm or edit: This manuscript is original, has not been published, and is not under
consideration for publication elsewhere. All authors have approved the submission.]

Sincerely,

[Corresponding author name]
[Affiliation]
[Email address]
