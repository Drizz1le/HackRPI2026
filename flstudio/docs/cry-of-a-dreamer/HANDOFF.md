# Cry of a Dreamer (start here)

Second flip, separate project. Source: The Sylvers, "Cry of a Dreamer" (1972), picked from a
soul sample playlist.
Everything here is self-contained: tools are copies from the Saw the Light project (repo root), which
stays untouched. General FL/bridge/.flp knowledge: `../docs/LEARNINGS.md`. New findings: `docs/LEARNINGS.md`.

## The idea
College Dropout chipmunk soul. Coupled resample +4 st (Through the Wire move): D major ~76 BPM ->
F# major 96 BPM. College Dropout kit drums (Through the Wire kick/snare, Slow Jamz clap/bongos,
Get Em High shaker), Dope Tec "[100] Bad Kick" break + "[92] Night Stay" perc loop.
Layers (strings, choir, brass, spiccato, bells) play roots + fifths only: the sample owns the thirds.

## Pipeline (run from this folder)
```
python tools/prepare.py          # chops -> chops/flip (only when chops/tempo change)
python tools/prepare_loops.py    # break/perc -> chops/loops
python tools/check_grid.py       # timing proof (v1: median 2-3 ms)
python cry.py                    # out/Cry of a Dreamer.flp + .mix.json
python fl.py open "out\Cry of a Dreamer.flp"
python mix.py "out\Cry of a Dreamer.mix.json"
python tools/export.py N "notes" # exports/vN
python tools/compare.py "exports\vN\Cry of a Dreamer vN.wav"; python tools/energy.py ...
```

## Files
| file | what |
|---|---|
| `sources/` | downloaded audio (yt-dlp, webm -> wav 44.1k) |
| `stems/htdemucs/...` | Demucs stems |
| `beats.npy` | 76 BPM grid (librosa said 152; every other beat). `beats152.npy` = raw |
| `lyrics.json`, `beat_chords.json` | Whisper words, per-beat chord guesses (noisy) |
| `tools/prepare.py` | CHOPS table (beat 0 = 10.08 s, hook "cry" on beat 60), coupled resample |
| `cry.py` | arrangement, 80 bars: Intro 0 / Verse 4 / Prehook 20 / Hook 24 / Verse 32 / Prehook 48 / Hook 52 / Breakdown 60 / Final hook 64 / Coda 72 |
| `mix.py` | same insert layout as Saw the Light (1 kick+808 ... 12 layers); knobs unchanged from v11 |

## State
v1 exported. See docs/VERSIONS.md. Next: tame 250-1k / 1-4k (sample is bright after +4 st), more crest.
