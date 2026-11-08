# Run Right Back (start here)
Hopecore flip of Kanye's extended Runaway outro, live at LA Memorial Coliseum (Dec 2021): "someday you're gonna run away ...
I need you to run right back to me, baby ... more specifically, Kimberly". The sample is the song.

- Source: sources/Runaway @ LAMC.mp3. Outro 219-327 s: no drums, piano + Kanye sung free (86-92 BPM), chords B C#m A E, 2 bars each.
- tools/prepare.py: chord changes = anchors of 8 beats (hand list, snapped to piano onsets); inside a span, tracked beats
  (-30 ms, snapped) when exactly 7 fit, else linear. Coupled +4 st -> 114 BPM, G#: Fm C# G# D#. Chops pre/cyc1-4/tail (+ _i piano, _v vocal), hype shout.
- tools/check_grid.py: chords per 2-bar block (all Fm C# G# D#), piano onsets vs 8th grid (cyc1/3 ok; cyc4 looser).
- tools/edits.py: stutters (word times from Whisper on the warped stem), 16th gate, reverse, tape stop, baked last-bar variants, breaks (Jail, Egyptian Luvr).
- runaway.py: Pre 0-1 | Intro 2-9 | Drop A 10-25 | Break 26-33 | Build 34-37 | Drop B 38-53 | Drop C 54-61 | Outro 62-67 (68 bars, 2:23).
Pipeline: python tools/prepare.py; python tools/edits.py; python tools/check_grid.py; python runaway.py;
python fl.py open "out/Run Right Back.flp"; python mix.py "out/Run Right Back.mix.json"; python tools/export.py N "notes"
