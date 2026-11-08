# Versions (exports/vN)  bands: sub/60-120/120-250/250-1k/1-4k/4-12k %, crest. Kanye median 32/17/12/18/7/2, 11.1 dB

## v1 - first
-7.5 LUFS, LRA 1.7. 22/7/5/56/10/0.6, 8.6 dB: mud (Rhodes+strings+doo-wop sample). Bound 2 stops not audible
(beat 4 as loud as beat 3): FL Sampler kept playing past shortened notes; hooks weren't cut at all.
## v2 - stops baked into the chops, de-mud
First render invalid (mix.py failed on a missing insert-8 EQ, project unsaved -> factory presets, -4.9 LUFS);
re-rendered: -8.1 LUFS. 54/19/4/17/5/0.5, 7.1 dB: mids fixed, sub way over. Stops now -3..-5 dB.
## v3 - balance
808 bus -3.5 dB, Rhodes HPF 150, master limiter gain 2 dB. -8.7 LUFS, LRA 2.8, TP +0.2.
41/16/5/29/8/0.7, 8.9 dB. 73.8 BPM, 3.15 hits/s. Still: 120-250 thin, sub a bit high, TP > 0.
## v4 - Kanye/Yeezus pass + master
Yeezus break inserted at bars 36-39 (blown 808, acid line, pitched-down demon "so warm", claps, scream);
"s-s-s-send me" stutter ends hook 1; tape stop ends verse 1; scream stab end of verse 2; 808 slams on
hook 2 / final hook; noise riser into the final hook. New: pluck arp (verse 2 + final hook), music box
(hooks), Homecoming piano stabs (intro, bridge), whistle-lead melody (outro). 80 bars, 4:31.
First offline master (tools/master.py): raw -8.4 LUFS/-0.3 TP -> master -8.1 LUFS, -0.9 dBTP, LRA 3.1,
glue -2.2 dB, limiter max -2.1 dB. Master bands 44.7/19.0/7.9/20.4/6.7/1.1, crest 9.2.
## v5 - hook lift attempt
Verse chops vel 88, 808 vel 92/98. Master 41.3/19.5/8.2/22.1/7.4/1.3, crest 9.6, -8.1 LUFS, -0.9 dBTP.
Section RMS still flat (hooks -10.9 vs verses -10.6 after the master): hook lift has to come from
density/brightness (saws, arp, music box), or quieter verse drums, not chop level.
## v6 - clarity (less reverb, less mud, clearer sample vocals)
Measured the reverbs through the bridge: vox chops ran Delay 3 at 62.5% feedback/100% wet + a plate;
strings and arp/music box halls had 12.65 s decay at 0 dB wet. Now: vox delay 18% wet / 30% fb, plate
-10 dB; halls 3.0 / 2.5 s, -8/-9 dB; rooms -8..-12 dB; Reeverb 30%; -3.5 dB at 2.5 kHz in strings,
Rhodes, arp/music box. Chops rebuilt with the twins' vocal stem +3.5 dB over the band (prepare.py).
Master -8.1 LUFS, -0.9 dBTP; 40.5/18.9/8.0/24.1/7.0/1.4, crest 9.4; side/mid -6.8 -> -7.4 dB.
Not applied: insert 10 (whistle lead) delay still 100% wet / 62.5% fb (setv didn't move it).
