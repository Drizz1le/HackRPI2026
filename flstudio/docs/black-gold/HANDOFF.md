# Black Gold (start here)

Third flip, own folder (tools copied from cry-of-a-dreamer/). MBDTF / Good Ass Job style.
Source: Rotary Connection, "I Am the Black Gold of the Sun" (1971, Charles Stepney arr., Minnie Riperton),
from a soul sample playlist. Goal: a standout sample chop + a Mike Dean
Devil in a New Dress guitar solo; layering other samples is allowed.

## The idea
- The chop (tools/chop.py): the record's rubato orchestral intro (0-44 s, no drums) sliced into chord
  swells by onset + chroma, each stretched to exactly 1 bar and level-matched, rebuilt on the grid:
  verse G#m | E | C#m | D#7 (i VI iv V) sustained; hook G#m | A | B7 | D#7 (i bII III V) MPC re-triggered
  (16th hits 0,3,6,8,10,12; hard cuts) + a reversed swell sucking into every phrase.
- Minnie's bridge lines (vocal stem), all G#-minor melodies: "I'm the black gold of the sun" (hook),
  "I am a man so free", "I'm the shining sea...", "smiling on everyone" (over E: chord tones).
- 88 BPM, G# minor = source key (no pitch change: no artifacts on Minnie).
- MBDTF kit drums (Devil kick/snare/hats, Power clap, Lost in the World big drums), Dope Tec
  "[88] Right Wing" break (native 88 BPM), "[90] Grown" perc, 808 on chord roots, low strings in fifths.
- Solo (tools/solo.py): real FL "Picked Humb" guitar notes (rendered by FL CLI, tools/render_notes.py)
  played along a continuous pitch curve: bends, releases, slides, hammer-ons, delayed vibrato; period-
  aligned grain sustain; asymmetric overdrive + FL guitar-cab IR. Original 16-bar line in Dean's vocabulary
  (repeated bends, pull-off runs, b2 over A, F#->G leading-tone bend over D#7, peak D#6 bend).
  Bars 52-59 no drums (Devil move), drums slam back at 60.

## Pipeline (from this folder)
```
python tools/chop.py             # chord slices + Minnie -> chops/flip (self-check included)
python tools/prepare_loops.py    # break/perc -> chops/loops
python tools/solo.py             # guitar solo -> chops/flip/solo.wav (self-check: bends hit pitch)
python gold.py                   # out/Black Gold.flp + .mix.json
python fl.py open "out\Black Gold.flp"; python mix.py "out\Black Gold.mix.json"
python tools/export.py N "notes"
```
Guitar notes only need re-rendering for a new instrument:
`python tools/render_notes.py "<...>\Packs\Instruments\Guitar\Picked Humb.fst" gtr/humb 52 55 ... 88`

## Arrangement (84 bars)
Intro 0-3 | Verse 4-19 | Hook 20-27 | Verse 28-43 | Hook 44-51 | Solo 52-67 | Final hook 68-75 | Outro 76-83
