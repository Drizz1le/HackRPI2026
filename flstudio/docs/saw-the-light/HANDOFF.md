# Handoff: AI-driven FL Studio production (start here)

Goal: an AI writes, arranges, mixes and "listens" to music in FL Studio 2025 entirely in code,
with no mouse or GUI clicking. The first song is "Saw the Light", an MBDTF / Good Ass Job-era flip of
Todd Rundgren's "I Saw the Light". Latest: **v11** (92 BPM, F# major, 4:14, -8.3 LUFS).

Read next: `docs/LEARNINGS.md` (every hard-won fact: sandbox, bridge protocol, .flp format,
timing, mixing by measurement) and `docs/research.md` (Kanye production research with sources).
Version history: `docs/VERSIONS.md`.

## Machine setup (already done on this PC)
- FL Studio 2025 (25.1.4, Producer Edition with all plugins) at `C:\Program Files\Image-Line\FL Studio 2025`.
- loopMIDI running with a port named **"loopMIDI Port"**. FL MIDI settings: input "loopMIDI Port" =
  controller type **AI Bridge**, port 200; outputs on port 200. (Registry values are REG_SZ; see LEARNINGS 4.)
- `python fl.py install` copies `device_AIBridge.py` (with the token) to
  `Documents\Image-Line\FL Studio\Settings\Hardware\AI Bridge\`. FL picks it up on start.
- Python 3.14 packages: numpy, scipy, soundfile, librosa, soundcard, matplotlib, pywin32, mido,
  demucs (+torch), openai-whisper. ffmpeg via winget (Gyan.FFmpeg). Rubber Band CLI 4.0 in
  `tools/rubberband/` (use the **R2** `rubberband.exe`).

## Files
| file | what |
|---|---|
| `fl.py` | CLI + Python API to FL: `fl("code")`, `api`, `params`, `set`, `open`, `listen`, `meters`, `analyze`, `chop` |
| `device_AIBridge.py` | FL controller script (SysEx bridge, exactly-once, token) |
| `flp.py` | low-level .flp/.fst reader/writer (`python flp.py file` dumps events) |
| `flpbuild.py` | build projects in code: sampler/plugin channels from .fst presets, patterns, playlist, mixer FX |
| `song.py` | "Saw the Light": the whole arrangement in code -> `out/Saw the Light.flp` (+ `.mix.json`) |
| `mix.py` | live mix through the bridge: routing, faders, plugin knobs by name and unit (`setv`), saves in Song mode |
| `tools/prepare.py` | sample prep: beat grid snap, per-beat Rubber Band time map, -1 st, bassline -> `chops/flip/` |
| `tools/prepare_loops.py` | break/perc loops stretched to exact bars -> `chops/loops/` |
| `tools/export.py N "notes"` | close FL, CLI-render `exports/vN/`, mp3, LUFS, spectrogram, reopen FL |
| `tools/compare.py wav` | band balance + crest vs Kanye refs (MBDTF + Good Ass Job instrumentals) |
| `tools/energy.py wav` | tempo, hits/s, percussive share vs the energy reference tracks |
| `tools/element_scan.py` | render each element alone (find mud sources) |
| `tools/balance.py wav` | band balance per song section |
| `tools/check_grid.py` | timing proof: drum stem through the chop time maps vs grid |
| `tools/transcribe.py`, `tools/chords.py` | Whisper word timestamps; per-beat chords |
| `tools/fxprobe.py` | open a 1-effect project to test a mixer preset loads (hang detector) |

## The pipeline (one version)
```
python tools/prepare.py            # only when chops/tempo change
python tools/prepare_loops.py      # only when loops/tempo change
python song.py                     # build out/Saw the Light.flp
python fl.py open "out\Saw the Light.flp"   # (never --save here: would overwrite the build)
python mix.py "out\Saw the Light.mix.json"  # routing + mix, saved by FL in Song mode
python tools/export.py 12 "what changed"    # render + stats into exports/v12
python tools/compare.py "exports\v12\Saw the Light v12.wav"
python tools/energy.py  "exports\v12\Saw the Light v12.wav"
```

## Production goals
- Keep the **sample up front** (like v1); v4's cleanliness was better.
- **Energy and forward motion** like Runaway, Lost in the World, Flashing Lights 2, Hard Horn
  Nightmare, Mama's Boyfriend, That's My Bitch, Eyes Closed. Keep the current drum sounds; add, don't replace.
- No timing slop: everything must sit on the grid (verify with `check_grid.py`).
- Not muddy, not overlapping: one owner per frequency band; no two melodies at once.
- **Never control FL with the mouse/GUI.** Export every version with its .flp. Write everything down.

## State / next ideas
- **v11 is the final version.** It is the baseline: keep its sound and
  export any change as a new version.
- v11 vs references: sub 25% (median 32), mids 31% (median 18, a bit rich), presence 10.7%, crest 9.9 dB.
- Could do: hand-written sample level rides ("Stronger" style), a second break for the hooks,
  vocal-chop rhythmic stabs denser in the final hook, sidechain the layers to the kick, master loudness
  toward -7 LUFS, real automation clips (playlist automation is not built in flpbuild yet).
- A new flip from another sample: follow the `fl-flip` skill (`.claude/skills/fl-flip/SKILL.md`).
