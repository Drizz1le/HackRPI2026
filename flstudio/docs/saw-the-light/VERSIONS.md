# Versions of "Saw the Light"

Each exports/vN/ has the FL project (.flp), .wav, .mp3, spectrogram (.png) and stats (.json).

| version | LUFS | LRA | true peak | what changed |
|---|---|---|---|---|
| v1 | - | - | - | first full render: over-limited brick wall, sample very forward |
| v2 | -10.0 | 7.1 | -1.3 | mix pass: tamed preset gains (master limiter +13 dB -> +3 dB, ceiling -0.3), sample HPF 120 / LPF 11k / -2.5 dB @3k, gentler drum + sample compression, lighter overdrive |
| v3 | -9.6 | 5.6 | -1.3 | Moog bass up an octave (verse sub energy was 84%), sample/vox louder, kick+808 and Moog lower, master +1.5 dB toward -8 LUFS |
| v4 | -9.4 | 5.7 | -1.3 | kick rebuilt: Devil kick (punch) + Runaway kick tucked at low velocity; dropped Power 32 Hz sub layer that swamped the verses |
| v5 | -8.9 | 6.6 | -0.7 | sample-forward mix (v1 feel, v4 cleanliness): sample bus +2.8 dB, chop channels to 0 dB, sample comp 4:1 +6 dB, drums/bass/pads stepped back, Stereo Shaper removed (was phase-cancelling the sample) |
| v6 | -9.4 | 9.3 | -1.0 | TIMING FIX: chops re-warped with per-beat time map (beats snapped to drum onsets; were 35 ms late + drummer drift) - median 8 ms on grid. LOW END: one owner per band - 808 owns sub (verses locked to kick), no sub-kick layer, Moog only in interlude/coda, strings/choir HPF 100, sample HPF 90 (body back), +1.5 dB @3k presence, choir lower, less limiting |
| v7 | -9.7 | 9.0 | -1.2 | balance toward Kanye reference curve: kick+808 bus -4 dB, hats/snare up for presence, brass up, master +1 dB |
| v8 | -9.1 | 9.4 | -1.0 | master tilt EQ toward the measured Kanye curve: -3 dB @90, +1.5 @220, +2.5 @2.5k; sample +2.5 @200 body, +3 @3k presence |
| v9 | -9.1 | 9.3 | -0.8 | arrangement de-clash: solo now rides the instrumental intro loop (was over a vocal chop), no held lead under the final vocal hook, 'in my eyes' answers instead |
| v10 | -7.8 | 5.6 | 0.2 | GROOVE: Good Life break under the drums (Runaway move), swung 16th hats + rolls in hooks, 16th pickups + soft clap in verses, tambourine, Shining perc loop, Lost in the World tribal drums between kicks. LAYERS: spiccato strings in 8ths, Hammond organ warmth, church bells on hook downbeats. FIX: intro lpf loop rebuilt from the re-timed chop (was stale -> off beat) |
| v11 | -8.3 | 5.0 | -0.4 | ENERGY: tempo 82 -> 92 BPM (refs: Flashing Lights 2 96, Eyes Closed 89, GAJ 107-112); all chops/loops re-warped to the new grid (median 5-12 ms); master ceiling -1.0 dB (v10 hit +0.2 dBTP) |
