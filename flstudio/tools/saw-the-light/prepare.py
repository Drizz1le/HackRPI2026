"""Sample prep for the flip: grid-locked chops + bassline, MBDTF-style.

  * source beats (beats.npy, librosa) -> bars start on beat phase 2 (where the chords change)
  * every chop spans whole source beats and is warped with Rubber Band (via ffmpeg) to exactly
    N beats at the new tempo and shifted -1 semitone (the "Gorgeous"/"Good Life" move); this also
    absorbs the live drummer's drift (117-123 BPM)
  * "nodrums" = vocals + other + bass stems, so the new drums own the low end and the groove
  * bassline = per-beat median pitch of the bass stem (pyin), transposed with the chops
Writes chops/flip/*.wav and chops/flip/manifest.json.
"""
import json, os, subprocess, sys
import numpy as np, librosa, soundfile as sf

BPM = 92.0  # v11: 82 -> 92 for energy (refs Flashing Lights 2 96, Eyes Closed 89, GAJ 107-112)
SEMITONES = -1
STEMS = 'stems/htdemucs/I Saw the Light - Todd Rundgren/'
OUT = 'chops/flip'
SR = 44100

# name: (stem, first source beat, beats)  - beat indices from beats.npy, bars start at phase 2
CHOPS = {
    'loopA':     ('nodrums', 2, 8),     # intro vamp  D | G Em          -> C# | F# D#m
    'hookA':     ('nodrums', 94, 16),   # "Cause I saw the light in your eyes"
    'hookB':     ('nodrums', 198, 16),  # "Till I saw the light in your eyes"
    'prehook':   ('nodrums', 74, 16),   # "then you gazed up at me..." C | C7 | F | E Am
    'last':      ('nodrums', 302, 16),  # "Can't you see the light in my eyes?"
    'vamp':      ('nodrums', 318, 8),   # outro vamp under "in my eyes"
    'vox_light': ('vocals', 101, 2),    # "light"
    'vox_head':  ('vocals', 142, 4),    # "in my head"
    'vox_eyes1': ('vocals', 320, 4),    # "in my eyes"
    'vox_eyes2': ('vocals', 328, 4),
    'vox_saw':   ('vocals', 96, 4),     # "I saw the"
}


def ffmpeg():
    import glob, shutil
    hits = glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe'))
    return hits[0] if hits else (shutil.which('ffmpeg') or 'ffmpeg')


# R2 engine: the R3 engine (rubberband-r3.exe) ignored the start of the time map (beat 1 landed at
# 0.49 s instead of 0.73 s); R2 lands every beat within ~7 ms.
RUBBERBAND = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rubberband',
                          'rubberband-4.0.0-gpl-executable-windows', 'rubberband.exe')


def refine_beats(beats):
    """librosa's beat times sit ~35 ms after the actual drum hits (measured: median -34.8 ms, sd 7.9);
    snap each beat to the nearest drum-stem onset within 60 ms, else shift by the median offset."""
    y, sr = librosa.load(STEMS + 'drums.wav', sr=SR)
    on = librosa.onset.onset_detect(y=y, sr=sr, hop_length=128, units='time', backtrack=False)
    d = np.array([on[np.argmin(abs(on - b))] - b for b in beats])
    near = np.abs(d) < 0.06
    med = np.median(d[near])
    return np.where(near, beats + d, beats + med)


def warp(src, beat_times, dst):
    """Per-beat time map: every source beat lands exactly on the BPM grid (the 1972 drummer drifts
    112-143 BPM beat to beat), pitch SEMITONES with formants preserved (Rubber Band R3 engine)."""
    import tempfile
    beat = 60.0 / BPM
    t0, t1 = beat_times[0], beat_times[-1]
    y, sr = sf.read(src, always_2d=True, start=int(t0 * SR), stop=int(t1 * SR))
    assert sr == SR
    tmp = tempfile.mkdtemp()
    seg, mapf = os.path.join(tmp, 'seg.wav'), os.path.join(tmp, 'map.txt')
    sf.write(seg, y, SR, subtype='FLOAT')
    with open(mapf, 'w') as f:
        for k, t in enumerate(beat_times):
            f.write('%d %d\n' % (int(round((t - t0) * SR)), int(round(k * beat * SR))))
    n = int(round((len(beat_times) - 1) * beat * SR))
    # two passes: Rubber Band's time map is only honoured without a pitch shift (with -p -1 just 2/16
    # beats landed); so 1) time-map onto the grid, 2) pitch -1 st (formants kept) at ratio 1.
    timed = os.path.join(tmp, 'timed.wav')
    subprocess.run([RUBBERBAND, '-q', '-D', '%.6f' % (n / SR), '-M', mapf, seg, timed], check=True, capture_output=True)
    subprocess.run([RUBBERBAND, '-q', '-p', str(SEMITONES), '--formant', timed, dst], check=True, capture_output=True)
    y, _ = sf.read(dst, always_2d=True)
    if len(y) != n:  # rubberband lands a few ms off: micro-resample to the exact grid length (no gap at loop points)
        y = librosa.resample(y.T, orig_sr=len(y), target_sr=n, axis=-1).T[:n]
    f = int(0.004 * SR)
    y[:f] *= np.linspace(0, 1, f)[:, None]
    y[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(dst, y, SR, subtype='PCM_24')


def bassline(beats):
    y, sr = librosa.load(STEMS + 'bass.wav', sr=22050)
    f0, voiced, _ = librosa.pyin(y, fmin=35, fmax=330, sr=sr, frame_length=4096)
    times = librosa.times_like(f0, sr=sr, hop_length=1024)
    notes = []
    for a, b in zip(beats[:-1], beats[1:]):
        m = (times >= a) & (times < b) & voiced & ~np.isnan(f0)
        notes.append(int(round(librosa.hz_to_midi(np.median(f0[m])))) + SEMITONES if m.sum() >= 2 else None)
    return notes


def main():
    beats = refine_beats(np.load('beats.npy'))
    os.makedirs(OUT, exist_ok=True)
    nod = os.path.join(OUT, '_nodrums.wav')
    if not os.path.exists(nod):
        mix = None
        for s in ('vocals', 'other', 'bass'):
            y, sr = sf.read(STEMS + s + '.wav', always_2d=True)
            mix = y if mix is None else mix + y
        sf.write(nod, mix, sr, subtype='PCM_24')
    srcs = {'nodrums': nod, 'vocals': STEMS + 'vocals.wav'}
    manifest = {'bpm': BPM, 'semitones': SEMITONES, 'chops': {}}
    for name, (stem, b0, n) in CHOPS.items():
        dst = os.path.abspath(os.path.join(OUT, name + '.wav'))
        warp(srcs[stem], beats[b0:b0 + n + 1], dst)
        manifest['chops'][name] = {'file': dst, 'beats': n, 'src_beat': b0}
        print('chop %-10s %5.2fs-%5.2fs -> %d beats' % (name, beats[b0], beats[b0 + n], n))
    bl = bassline(beats)
    manifest['bass'] = {name: bl[b0:b0 + n] for name, (stem, b0, n) in CHOPS.items() if stem == 'nodrums'}
    json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
    for k, v in manifest['bass'].items():
        print('bass %-8s %s' % (k, ' '.join(librosa.midi_to_note(x, unicode=False) if x else '-' for x in v)))


if __name__ == '__main__':
    main()
