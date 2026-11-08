# Send Me (start here)

Original love-letter song: Graduation era with a Bound 2 vibe (refs: Bound 2, White Dress, Lost in the World).
Own folder; tools copied from black-gold/. Lyric-writing research: docs/lyrics-research.md (background agent).

## Samples
- The Ponderosa Twins Plus One, "You Send Me" (the "Bound" group). 12/8 doo-wop: librosa's beats are the
  triplet 8ths; every 3rd (strongest phase) = 1 beat; bar phase by chord change. Coupled +4 st:
  dotted quarter 58.7 -> 74 BPM (Bound 2 tempo), C -> E major, triplet swing kept.
  Changes: E - C#m | F#m - B7. Intro/"darling" = B7 pedal.
- Smokey Robinson, "Baby Come Close" (B major) -> vocal chops chipmunk +5 = E (tools/smokey.py).

## Chops (tools/prepare.py CHOPS, beat 0 = 1.09 s, bar k = beat 4k)
intro (oohs, B7), hookA ("you send me, yeah you send me girl"), loopA/loopB (changes w/ and w/o oohs),
miss ("I miss you, I miss you too"), letter ("now I find myself wanting you, yeah to marry you, and take
you home"), darling ("yes you do ... darling you send me"), vox_send/marry/home/darl; Smokey: sm_lights
("turn the lights down low, baby come close"), sm_close, sm_warm ("so warm"), sm_dreams.

## Arrangement (send.py, 76 bars, triplet grid T = BAR/12)
Intro 0-3 | Hook 4-11 | Verse 12-27 | Hook 28-35 | Verse 36-51 | Bridge 52-59 (love letter, Lost in the
World tribal drums) | Final hook 60-67 (+ supersaw, ride) | Outro 68-75 (twins' last words, Smokey a cappella)
Bound 2 hard stops every 4th bar: chop "_stop" variants (last beat silent) + drums/808/Rhodes stop,
chipmunk "baby come close" fills the hole. Rhodes neo-soul voicings (Emaj9 C#m9 F#m9 B13), Juno strings.
Graduation kit: Homecoming kick (15% sub: the 808 owns the sub), Good Morning snare, Flashing Lights clap,
Stronger hats, Homecoming tamb, Big Brother ride.

## v4+ additions
Yeezus break 36-39 and edits (tools/yeezus.py -> manifest 'yz'), arp/music box/piano/whistle lead,
offline master: export.py writes "<name> vN (master).wav/.mp3" next to the raw render.
Arrangement now: Intro 0-3 | Hook 4-11 | Verse 12-27 | Hook 28-35 | Yeezus 36-39 | Verse 40-55 |
Bridge 56-63 | Final hook 64-71 | Outro 72-79.

## Pipeline (from this folder)
python tools/prepare.py; python tools/smokey.py; python tools/yeezus.py; python tools/check_grid.py; python send.py
python fl.py open "out\Send Me.flp"; python mix.py "out\Send Me.mix.json"; python tools/export.py N "notes"
