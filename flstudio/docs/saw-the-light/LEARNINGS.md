# Everything learned (running log)

Driving FL Studio 2025 (25.1.4, scripting API v38) entirely from code, and producing a
Kanye 2010-era flip with it. Newest findings are appended at the bottom of each section.

## 1. FL Studio's Python sandbox
- Controller ("device") scripts run in a **sub-interpreter** of FL's bundled Python 3.12.1.
  - `open()` fails: `SystemError: <class '_io.FileIO'> returned NULL`. No file I/O.
  - `socket.socket()` fails the same way. No networking.
  - `import ctypes` fails: "module _ctypes does not support loading in subinterpreters".
  - `print()` goes to View > Script output (the only log).
- A script is attached to a MIDI **input** port in Options > MIDI settings ("Controller type").
  Without a port there is no script. Reloading a script needs the GUI button, so to stay
  code-only we restart FL (`fl.py open`).
- The script API has 440 functions (`python fl.py api`, saved in `api.txt`). Notably **missing**:
  load a sample, add a channel/plugin, write piano-roll notes, place playlist clips, open a project,
  export audio. Those are solved by generating the `.flp` instead (section 3).

## 2. The bridge (device_AIBridge.py <-> fl.py)
- Transport = **MIDI SysEx over loopMIDI**, because files/sockets/ctypes are blocked.
  - Manufacturer ID 0x7D (non-commercial), tag 0x41. Payload = base64(JSON), chunks of 200 bytes
    (loopMIDI's default SysEx buffer is 256).
  - Request chunk: `F0 7D 41 <0 more|1 last> <8-byte request id> <chunk idx> <data> F7`.
  - Reply chunk:   `F0 7D 41 <2 more|3 last> <8-byte request id> <idx lo> <idx hi> <data> F7`.
  - The request/reply flag ranges differ, so a script seeing its own reply echoed back ignores it.
- FL's MIDI output for the script = whichever output port has the **same port number** (200).
  Both loopMIDI ports ended up as outputs on 200, so the client listens on "loopMIDI Port", which
  also carries the requests.
- **Unhandled SysEx is echoed** by FL to the output: handle in `OnMidiIn` and set `event.handled`,
  otherwise you get an infinite loop through the loopback port.
- FL can deliver the **same SysEx twice** (OnMidiIn and OnSysEx), especially while playing, and
  **drops some messages while the transport runs** (~40% lost without retries).
  Fix: requests are idempotent by id. Chunks are assembled per id by index, a finished request's
  reply is cached, the client resends on silence, and the script re-sends the cached reply.
  Exactly-once execution, at-least-once delivery.
- Client side uses raw `winmm` via ctypes (python-rtmidi has no wheel for Python 3.14):
  midiInOpen + 1024 prepared 512-byte buffers polled for MHDR_DONE, and midiOutLongMsg.
  64 buffers was not enough: big replies are bursts and overflowed.
- Security: the code bridge runs arbitrary Python in FL. Only a 32-hex token embedded in the
  installed script (and saved in `~/.fl_ai_bridge_token`) is accepted.
- Multi-line code returns the value of a variable named `result`. One-liners return their value.
- `mixer.setTrackVolume` is applied asynchronously. Reading it back in the same call returns stale
  values (0.0). Do math client-side.

## 3. The .flp format (flp.py / flpbuild.py)
- Header `FLhd` (u32 6, i16 format, u16 channel count, u16 PPQ=96), then `FLdt` + u32 length + events.
  Event id <64: 1 byte, <128: 2 bytes, <192: 4 bytes, >=192: varint length + data.
- `.fst` presets are the same container (format 0x30 plugin state, 0x20 channel state) with 3 key
  events: 201 internal name (old presets ASCII, projects UTF-16), 212 wrapper (52 bytes),
  213 plugin state. Those can be spliced into a project to create a channel or a mixer effect.
- Channel block starts with event 64 (index). Event 21 type: 0 = Sampler, 2 = plugin generator.
  203 = display name, 196 = sample path (after event 20). The plugin state (213) goes right after
  event 41.
- Pattern = 65 (index, 1-based), 193 name, 224 notes, 24 bytes per note:
  `u32 pos, u16 flags=0x4000, u16 channel, u32 length, u16 key, u16 group, u8 fine(120),
  u8 0, u8 release(64), u8 midi ch, u8 pan(64), u8 velocity, u8 modX(128), u8 modY(128)`.
  Key 60 plays a Sampler at its own pitch. Patterns are placed before the controller events (226).
- Playlist = event 233, 80 bytes per item: `u32 pos, u16 0x5000, u16 0x5000+pattern, u32 length,
  u16 (499 - track), u16 group, 8 bytes 7800408040648080, u32 start 0, u32 end length,`
  then a 48-byte tail (copied from an FL-saved file; first u32 = clip id).
- Mixer: each insert = event 236 (flags) + ten 98 events (slot index). The **first 236 is the
  master**. A slot's plugin events (201, 212, 203, 155, 128, 41, 213) go **before** its 98 event.
- **Wrapper (212) of a mixer plugin: dword0 = insert, dword1 = slot.** FL places the plugin from
  this, not from the event position. Presets carry other values, and a mismatch **hangs FL while
  loading** ("Opening: Fruity soft clipper", not responding). Found by bisecting with
  `tools/fxprobe.py`.
- Wrapper flags (u32 at byte 16): 0x1 = editor window open, 0x200 = ? Cleared both, so projects
  open without plugin windows popping up.
- Base template: `Data\Templates\Minimal\Empty\Empty.flp` (FL 24.2 save, opens fine in 25).

## 4. FL command line and process control
- `FL64.exe "x.flp"` opens a project. Passing a .wav to a running instance does nothing.
- `FL64.exe /R /Ewav "x.flp"` renders next to the project, **only when no FL is running**
  (a running instance swallows it). The whole 4:44 song renders in ~24 s.
- It renders in the **mode the project was saved in**: saved in Pattern mode, it exported 18 s
  (one pattern). `mix.py` forces Song mode before saving.
- MIDI device settings live in `HKCU\Software\Image-Line\FL Studio 25\Devices\MIDI input|output\<port>`.
  **All values must be REG_SZ strings**: a DWORD crashed FL at startup
  ("Invalid data type for 'Type'"). FL rewrites these on exit, so edit only while FL is closed.
  A scripted controller is saved as `Type=-3`, `ScriptFolder=<folder name>`.
- Graceful close: `CloseMainWindow()`. If the project is unsaved FL shows a modal Save prompt, so
  save first through the bridge (`transport.globalTransport(midi.FPT_Save, 1)`).
- API calls that open dialogs block the script thread until the dialog closes
  (`patterns.findFirstNextEmptyPat(FFNEP_FindFirst)` opens a rename prompt; use DontPromptName).

## 5. Knobs by name and unit (mix.py `setv`)
- Plugin params are 0..1. `setv` binary-searches until FL's own display string
  (`getParamValueString`) reads the target ("120Hz", "-0.3dB", "Peaking").
- Bipolar knobs ("100% left" .. "100% right") break a numeric search; set the raw value (0.5 = centre).
- Mixer fader curve (value -> dB): 0.5 -9.18, 0.6 -5.95, 0.7 -2.91, 0.75 -1.44, **0.8 0.0**,
  0.85 1.42, 0.9 2.83, 1.0 +5.59. Channel volume 0.78 (default) = -5.2 dB, 1.0 = 0 dB.
- Factory presets are hot. Fruity Limiter "Max loudness" had **+13.1 dB gain and a +2.5 dB
  ceiling**, the drum limiter presets +12.8 and +14 dB, Compressor "Vintage" 8:1 with +8.6 dB,
  Blood Overdrive preamp 100%. Stacked, that is v1's brick wall. Always reset preset gains.
- Fruity Stereo Shaper "Stereoize" = 51% L/R dephasing: the sample went **out of phase**
  (correlation -0.24) and vanishes in mono. Don't widen samples with it.

## 6. Listening and measuring
- `fl.py listen` records the Windows default output (WASAPI loopback) while FL plays, then gives
  tempo, key, peak/RMS and a spectrogram PNG the AI can look at.
- `tools/export.py N` renders through the CLI and adds EBU R128 (ffmpeg ebur128: integrated LUFS,
  LRA, true peak).
- `tools/balance.py` = % energy per band per song section. This is what found v2's problem:
  **84% of verse energy below 60 Hz**.
- Kick samples, measured: Power layer kick 32 Hz with 97% sub energy over 0.39 s; Runaway kick
  47 Hz, 88% sub; Devil in a New Dress kick 74 Hz, 6% sub, 0.07 s. The sub layer, not the bass,
  swamped the verses.
- Soloing inserts and recording the loopback (`tools/autogain.py`) gave **inconsistent readings**
  between passes. Don't trust it: measure renders instead.
- `fl.py meters` polls FL's own peak meters per insert while playing.

## 7. Sample work
- Stems: Demucs htdemucs (vocals / drums / bass / other), 32 s for a 3-minute song on CPU.
- Lyrics with word timestamps: Whisper "small" (pass audio as an array; no ffmpeg was needed).
- Beat grid: librosa beat_track on the drum stem. The live 1972 drummer drifts 117-123 BPM.
  Downbeat = beat phase where chords change (chroma novelty), not just the loudest kick.
- Chops warped per chop with **Rubber Band through ffmpeg** (`rubberband=tempo:pitch:formant=preserved`):
  each chop spans whole source beats and is stretched to exactly N beats at 82 BPM, -1 semitone.
  This absorbs the drummer's drift. Rubber Band output lands a few ms short, so micro-resample
  to the exact length or the loop points get gaps.
- "nodrums" bed = vocals + other + bass stems, so the new drums own the groove.
- Bassline = per-beat median pyin pitch of the bass stem, transposed with the chops.
- Variants are baked offline, like resampling on an ASR-10: low-passed loop for the intro,
  band-passed + tanh-driven "in my eyes" for the Runaway-style coda.

## 7b. Timing: getting the sample exactly on the grid (the "it's off beat" fix, v6)
- librosa's beat times sat **~35 ms after the actual drum hits** (median -34.8 ms, sd 7.9 ms,
  338/344 beats had an onset within 60 ms). Every chop started late and cut into its attack.
- The 1972 drummer's beat-to-beat intervals run 418-534 ms (112-143 BPM locally), so one stretch
  ratio per 4-bar chop drifted inside the chop.
- Fix (tools/prepare.py): snap each beat to its drum-stem onset, then warp each chop with a
  **per-beat time map**. Every source beat maps to k x 60/82 s.
- Rubber Band CLI 4.0 (official Windows build, tools/rubberband/):
  - The **R3 engine (`rubberband-r3.exe`) ignored the start of the time map**: beat 1 landed at
    0.49 s instead of 0.73 s. The R2 engine (`rubberband.exe`) honours it.
  - **Time map + `-p` pitch shift together breaks the map** (2/16 beats on time). Two passes:
    time map first (no pitch), then `-p -1 --formant` (ratio 1).
- Proof: warp the *drum stem* through the same map (the sample is too soft-edged to measure) and
  measure hits vs the grid (tools/check_grid.py). Result: median error 7-14 ms per chop; the
  remaining big misses are beats where the drummer didn't play.
- The backbeat lines up: the source snare falls on beats 2 and 4 of the chosen bars.

## 7c. Mixing by measurement against real records (v6-v9)
- tools/compare.py measures the band balance and crest factor of reference tracks on disk
  (Runaway, Power remix, Blame Game, Flashing Lights 2, Homecoming). Kanye median:
  20-60 Hz 26.7% | 60-120 13.5% | 120-250 11.8% | 250-1k 23.2% | 1-4k 11.0% | 4-12k 2.0% | crest 11.5 dB.
- tools/element_scan.py renders every element alone through the FL CLI (filtered builds via
  `ONLY=` in song.py). It found the mud sources by number: Runaway kick 88% <60 Hz,
  low strings 30% <60 Hz, Moog 20%/30% in sub/low-bass, choir 84% in 250-1k.
- Rule applied: **one owner per band**. The 808 owns the sub (short notes locked to the kick in
  verses, sustained in hooks). The Devil kick owns 60-120 Hz. The Moog plays only where there is
  no 808 (interlude, coda). Strings/choir high-passed at 100 Hz. The sample high-pass moved from
  120 to 90 Hz to give its body back.
- **Generated projects must store Song mode: header event 9 = 1** (PyFLP calls it "LoopActive").
  Without it the CLI renders only pattern 1 (3-12 s files).
- FL's CLI render normalizes each element render to about -0.5 dBFS peak, so solo renders only
  show balance shape, not level.
- Progress v5 -> v9 (sub / 60-120 / 120-250 / 250-1k / 1-4k / crest):
  69/8/2.5/15/3.7/8.9 -> 30.8/19.7/5.2/34.5/8.3/11.1 (Kanye median 26.7/13.5/11.8/23.2/11.0/11.5).
- Arrangement de-clash: no lead melody over a vocal chop. The solo rides the instrumental loop;
  the final hook has no held lead.

## 7d. Groove and energy (v10-v11)
- v9 felt more Donda than MBDTF and lacked drive.
  tools/energy.py on reference instrumentals (Flashing Lights 2, Hard Horn Nightmare, Mama's
  Boyfriend, That's My Bitch, Eyes Closed: Good Ass Job INSTS): 89-112 BPM, 3.7-5.5 hits/s,
  3.4-6.0 high-band hits/s. v9 had 2.5 hits/s at 82 BPM.
- v10 added the Runaway move: a real break (Dope Tec "[87] Good Life", 2 bars, stretched to exact
  bars) under the programmed kick, high-passed at 150 Hz so its kick doesn't fight. Plus swung 16th
  hats (~17%), 32nd rolls into every 4th hook bar, verse 16th pickups, offbeat tambourine, a perc loop,
  and Lost in the World tribal drums (both big drums) on the off-16ths between the kicks.
  Hits/s went 2.5 -> 4.2.
- Layers for MBDTF fullness, each in its own range: spiccato strings in 8ths (motion, upper mids),
  Hammond organ triads (low-mid warmth; 120-250 Hz went 5% -> 15%), church bells on hook downbeats
  (top end). All on a "Layers" bus with a 140 Hz high-pass.
- v11: tempo 82 -> 92 BPM. Only BPM in prepare.py changes; every chop/loop re-warps to the new grid
  (still 5-12 ms median). The source needs less stretch at 92 (123 -> 92), so it sounds cleaner.
- Bug found: offline chop variants (lpf intro, distorted coda vox) were cached and not rebuilt after
  the re-time, so the intro was off beat. Variants now rebuild when the chop is newer.
- Bug found: `fl.py open` used to save the current project first. With an old copy of the same file
  open, that overwrote the fresh build ("v10" rendered as v9). It no longer saves by default.
- Reference set grew: Good Ass Job instrumentals (Pastelle Collective) at
  `~\Downloads\PASTELLE COLLECTIVE - GOOD ASS JOB\PASTELLE TEAM - GOOD ASS JOB\INSTS`.
  Median of all refs: sub 32 / 60-120 17 / 120-250 12 / 250-1k 18 / 1-4k 7 / 4-12k 2 %, crest 11 dB.

## 8. Production research (summary; sources in docs/research.md)
- Kanye's main sampler was the Ensoniq ASR-10 (61 keys = chop per key). Drums on an MPC2000XL.
- Default pitch move = coupled resample (chipmunk, about +3 to +5 st, e.g. Through the Wire +4).
  Big tempo changes = time-stretch + small pitch move (Good Life 127 -> 85 BPM, -1 st).
- MBDTF moves: lone piano motif (Runaway), drums out / live band interlude + guitar solo
  (Devil in a New Dress), section-opening stabs (Power's King Crimson), offbeat vocal stab every 4th
  count (So Appalled), long processed-vocal coda, "no high strings, only low strings" (Kilhoffer).
- Mix: MBDTF CD is DR 5, RMS about -6 to -7, clipped peaks (Vlado Meller master). Drums dry and
  close; the ambience comes from the samples and the choirs.
