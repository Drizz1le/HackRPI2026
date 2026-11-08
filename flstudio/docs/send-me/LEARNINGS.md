# Learnings specific to Send Me

- 12/8 sources: onset autocorrelation peaks at 1x/3x/6x/12x the 8th (0.34 s -> 1.02 -> 2.04 -> 4.09 s)
  and the chroma period (8.17 s = 2 bars) give the meter. Pick the beat phase (every 3rd 8th) with the
  strongest drum onsets, then the bar phase by chroma novelty.
- Coupled +4 st turns a 58.7 BPM dotted-quarter pulse into 74 BPM with the triplet swing intact: a hip-hop
  beat on a triplet grid (T = BAR/12) locks to it.
- Whisper mishears soul: "you send me" -> "you're me", "infatuation" -> "in graduation".
- FL Sampler did NOT stop at the end of a shortened note in a CLI render (beat 4 still full level). Bake
  stops/edits into the audio (chop "_stop" variants) instead of relying on note length.
- If mix.py fails midway it never saves, and export renders the unmixed build (factory preset gains:
  -4.9 LUFS, +0.6 dBTP). Check mix.py's last line before exporting.
- Bash heredoc + Python string replace of '\\' paths silently missed; use the Edit tool for such lines.
- Master (tools/master.py, run by export.py): reference-matched EQ (1/3-oct LTAS vs the mean of the Kanye
  refs, 70%, +-4 dB, anchored at 1 kHz THEN clamped: clamping first let the anchor shift push +6 dB at
  8 kHz), 1.5:1 glue, tanh soft clip above -3 dBFS, 4x-oversampled lookahead limiter at -1 dBTP, gain
  iterated on ffmpeg EBU R128 to -8 LUFS. Self-check asserts the true peak.
- Yeezus edits are easiest baked offline (tools/yeezus.py): octave-down Rubber Band without --formant
  (demon), re-triggered 16th stutter, variable-rate tape stop, a 303 line from a saw + per-sample SVF.
- Long bash heredocs with nested quotes can fail to parse ("unexpected EOF"): write patch scripts to the
  scratchpad and run them.
- Factory FX presets are wet-heavy as well as hot: LuxeVerb "Lush Pad Hall" = 12.65 s decay at 0 dB wet,
  Delay 3 "Tape" = 62.5% feedback at 100% wet. Stacked on 9 inserts this read as "too much reverb /
  can't hear the lyrics". Read every reverb/delay's decay/wet/feedback through the bridge and set them.
- With stems on disk, "make the sample's words clearer" = remix the chop source (vocals x1.5 vs
  other+bass) before chopping, instead of EQ on the finished chop.
