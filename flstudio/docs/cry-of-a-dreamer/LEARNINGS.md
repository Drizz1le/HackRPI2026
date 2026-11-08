# Learnings specific to this flip (general ones: ../docs/LEARNINGS.md)

- Getting audio: `python -m yt_dlp -x "ytsearch1:<artist> <title>"` gives webm; yt-dlp can't find
  ffmpeg (winget's is not on PATH), so convert with the Gyan.FFmpeg exe found by glob
  (`tools/export.py` FFMPEG). Check duration against Spotify (279.2 s = 279213 ms).
- Spotify playlist pages render no tracks for WebFetch; the embed page
  (`open.spotify.com/embed/playlist/<id>`) has the full list in `__NEXT_DATA__` JSON (trackList).
- librosa beat_track read this 76 BPM soul record as 152. Halve (every other beat) and pick the
  phase where the hook's first stressed word lands (Whisper word times in beat units).
- Coupled resample (chipmunk) with a per-beat time map: map source beats onto a grid RATIO = 2^(st/12)
  slower, then resample to the exact grid length. One Rubber Band pass (no pitch pass), formants move
  with the pitch like an ASR-10. Grid error median 2-3 ms (better than the two-pass -1 st method).
- 808/bass harmony from the bass stem per half-bar (cry.py chop_harmony) instead of hand-typed chords;
  layers use root+fifth+octave so major/minor guesses can't clash with the sample.
- Python raw strings: r'...Don\'t...' keeps the backslash -> FL "missing sample". Use r"...Don't...".
- FL wouldn't close (CloseMainWindow) with a modified project open even after a bridge save: it
  had to be closed by hand. Ask rather than kill.
