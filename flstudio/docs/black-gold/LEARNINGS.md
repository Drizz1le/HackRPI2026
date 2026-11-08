# Learnings specific to Black Gold (general: ../docs/LEARNINGS.md, ../cry-of-a-dreamer/docs/LEARNINGS.md)

- FL's pack instruments (Data\Patches\Packs\Instruments\...\*.wav) are in an Image-Line format that
  libsndfile and ffmpeg can't open ("Malformed fmt chunk", "no decoder"). Their .fst presets load in
  DirectWave. To get the audio: build a 1-channel project playing held notes and render it with the FL
  CLI (tools/render_notes.py). The FL CLI needs an absolute .flp path (relative path: no render, no error).
- Guitar cab impulses (Impulses\Guitar Cabinet\*.wv, WavPack) decode fine with ffmpeg.
- Expressive guitar can't come from the piano roll; offline pitch-curve playback of real notes works:
  variable-rate read (cumsum of 2^(dp/12)), sustain by Hann grains at a hop of whole periods (no
  phasing), then drive + cab. Self-check measures the bend target with yin (80/81 notes within 0.5 st).
- Rubato intros are great chop material: onset-split + chroma template per segment gives clean chord
  slices. A slice that is cut by the next chord's onset dies out when stretched (C#m at 35.9 s): check
  last-quarter RMS and pick another occurrence. Level-match slices (the source runs ppp..ff).
- librosa read 92 BPM as 184 here too (third time): always halve when the IBI is ~0.3 s.
- Lyrics + per-word pyin pitch (vocal stem) finds sung lines that fit a new progression without pitch
  shifting (Minnie's bridge = G#/F#: hook vocal over G#m | A).
