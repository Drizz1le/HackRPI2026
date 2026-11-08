---
name: fl-flip
description: Produce, mix and export music in FL Studio 2025 entirely from code (no mouse) in this repo - Kanye-era sample flips, chopping, arranging, mixing by measurement, exporting versions. Use for any request to make a beat/flip/song, change the current song ("Saw the Light"), chop a sample, control FL Studio, mix, listen or export.
---

# FL flip (code-only FL Studio production)

Read `docs/HANDOFF.md` first (setup, files, pipeline, production goals), then `docs/LEARNINGS.md` when
something behaves oddly: most traps are already documented there with the fix.

## Hard rules
- **Never drive FL with the mouse, keyboard or GUI automation.** Everything goes through code:
  the SysEx bridge (`fl.py`), generated `.flp` files (`flpbuild.py`), and the FL command line.
- **Export every version** with `tools/export.py N "notes"` (keeps .flp, .wav, .mp3, .png, .json).
- **Write down everything learned** in `docs/LEARNINGS.md`. Keep `docs/VERSIONS.md` and
  `docs/HANDOFF.md` current.
- Timing must be exact (`tools/check_grid.py`), mixes not muddy (one owner per band), no two
  melodies on top of each other, sample up front, drums that push forward.

## Workflow for a NEW flip
1. Pick the source. Stems: `python -m demucs -n htdemucs -o stems "<song>"`.
   Lyrics/word times: `python tools/transcribe.py stems/.../vocals.wav lyrics.json`.
2. Beat grid: librosa beat_track on the drum stem -> `beats.npy`. `tools/prepare.py` snaps beats to
   drum onsets (librosa is ~35 ms late) and finds bars by the phase where chords change
   (`tools/chords.py`).
3. Decide tempo/pitch like Kanye: coupled resample about +3..+5 st (chipmunk soul), or time-stretch
   with a small pitch move (Good Life: 127 -> 85, -1 st). For energy, 89-112 BPM (reference tracks).
4. Edit `CHOPS`, `BPM`, `SEMITONES`, `STEMS` in a copy of `tools/prepare.py`. Chops are warped with a
   per-beat time map (Rubber Band **R2**, time map pass first, pitch pass second). Never pitch and
   time-map in one pass; never use R3 for time maps.
5. Write the arrangement as code (copy `song.py`): channels from your kits
   (`~\Documents\FLStudio\...`) and factory `.fst` presets via `preset('Generators', ...)`.
   Notes: `n(channel, bar, step16, len16, key, vel)`. Sections as 4-bar patterns on playlist track 1.
6. Mix: `mix.py` (routing, faders 0.8 = 0 dB, knobs by name/unit with `setv`). Reset factory preset
   gains: they are hot (limiter presets +13 dB).
7. Export, then measure: `tools/compare.py`, `tools/energy.py`, `tools/balance.py`, `tools/element_scan.py`.
   Iterate toward the reference numbers. Look at the spectrogram PNG.

## Gotchas that cost hours (details in LEARNINGS)
- Generated projects need Song mode (header event 9 = 1) or CLI renders only pattern 1.
- Mixer effect wrapper bytes: dword0 = insert, dword1 = slot, else FL hangs on load.
- `fl.py open` must not save (it would overwrite a fresh build with the old open copy).
- The FL CLI render only works with FL closed; it renders the saved mode.
- FL script sandbox: no files, sockets or ctypes. API calls that open dialogs block the bridge.
- Bridge replies can be lost or duplicated during playback: the protocol is already exactly-once with retries.
- Soloing + loopback recording is unreliable for levels: measure CLI renders instead.
