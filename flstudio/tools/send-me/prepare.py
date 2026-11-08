"""Cry of a Dreamer (The Sylvers) prep - copy of prepare.py with a COUPLED resample (chipmunk soul):
time-map the 76 BPM source to a 96/2^(4/12) grid, then resample to the 96 BPM length = +4 st and faster at once.

Original notes: Sample prep for the flip: grid-locked chops + bassline, MBDTF-style.

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

BPM = 74.0  # Bound 2 tempo: the source's dotted quarter (12/8, 58.7) sped up x1.26
SEMITONES = 4  # C major -> E major (Through the Wire style +4)
RATIO = 2 ** (SEMITONES / 12)
STEMS = 'stems/htdemucs/You Send Me - Ponderosa Twins/'
OUT = 'chops/flip'
BEATS = 'beats.npy'  # 12/8: librosa's beats are the triplet 8ths; every 3rd (strongest phase) = 1 beat, bar phase by chord change
SR = 44100

# name: (stem, first source beat, beats)  - beat indices from beats.npy, bars start at phase 2
CHOPS = {  # beat 0 = 1.09 s, bar k = beat 4k. Changes: C Am | Dm G7 (-> E C#m | F#m B7)
    'intro':     ('nodrums', 0, 16),    # G7 vamp with oohs (-> B7 pedal)
    'hookA':     ('nodrums', 16, 16),   # "you send me, yeah you send me girl..."
    'loopA':     ('nodrums', 32, 16),   # the changes with background oohs (verse bed)
    'loopB':     ('inst', 32, 16),      # same, no vocals
    'miss':      ('nodrums', 56, 8),    # "I miss you, I miss you too"
    'letter':    ('nodrums', 112, 16),  # "now I find myself wanting you, yeah to marry you, and take you home"
    'darling':   ('nodrums', 128, 16),  # "yes you do ... darling you send me" (vamp)
    'vox_send':  ('vocals', 14, 2),     # "you send me"
    'vox_marry': ('vocals', 118, 4),    # "yeah, to marry you"
    'vox_home':  ('vocals', 122, 4),    # "and take you home"
    'vox_darl':  ('vocals', 134, 4),    # "darling you send me"
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
    drifts beat to beat), then a plain resample = coupled speed+pitch (chipmunk)."""
    import tempfile
    beat = 60.0 / BPM
    t0, t1 = beat_times[0], beat_times[-1]
    y, sr = sf.read(src, always_2d=True, start=int(t0 * SR), stop=int(t1 * SR))
    assert sr == SR
    tmp = tempfile.mkdtemp()
    seg, mapf = os.path.join(tmp, 'seg.wav'), os.path.join(tmp, 'map.txt')
    sf.write(seg, y, SR, subtype='FLOAT')
    n = int(round((len(beat_times) - 1) * beat * SR))
    timed = os.path.join(tmp, 'timed.wav')
    # coupled resample: map to the slower grid (n * RATIO), then the resample below speeds it up = +SEMITONES
    nslow = int(round(n * RATIO))
    with open(mapf, 'w') as f:
        for k, t in enumerate(beat_times):
            f.write('%d %d\n' % (int(round((t - t0) * SR)), int(round(k * beat * RATIO * SR))))
    subprocess.run([RUBBERBAND, '-q', '-D', '%.6f' % (nslow / SR), '-M', mapf, seg, timed], check=True, capture_output=True)
    y, _ = sf.read(timed, always_2d=True)
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
    beats = refine_beats(np.load(BEATS))
    os.makedirs(OUT, exist_ok=True)
    nod = os.path.join(OUT, '_nodrums.wav')
    if not os.path.exists(nod):
        mix = None
        for s in ('vocals', 'other', 'bass'):
            y, sr = sf.read(STEMS + s + '.wav', always_2d=True)
            y = y * (1.5 if s == 'vocals' else 1.0)  # v6: twins' words +3.5 dB over the band (lyrics were buried)
            mix = y if mix is None else mix + y
        sf.write(nod, mix, sr, subtype='PCM_24')
    inst = os.path.join(OUT, '_inst.wav')
    if not os.path.exists(inst):
        y = sum(sf.read(STEMS + s + '.wav', always_2d=True)[0] for s in ('other', 'bass'))
        sf.write(inst, y, SR, subtype='PCM_24')
    srcs = {'nodrums': nod, 'inst': inst, 'vocals': STEMS + 'vocals.wav'}
    manifest = {'bpm': BPM, 'semitones': SEMITONES, 'chops': {}}
    for name, (stem, b0, n) in CHOPS.items():
        dst = os.path.abspath(os.path.join(OUT, name + '.wav'))
        warp(srcs[stem], beats[b0:b0 + n + 1], dst)
        manifest['chops'][name] = {'file': dst, 'beats': n, 'src_beat': b0}
        print('chop %-10s %5.2fs-%5.2fs -> %d beats' % (name, beats[b0], beats[b0 + n], n))
    bl = bassline(beats)
    manifest['bass'] = {name: bl[b0:b0 + n] for name, (stem, b0, n) in CHOPS.items() if stem != 'vocals'}
    json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)
    for k, v in manifest['bass'].items():
        print('bass %-8s %s' % (k, ' '.join(librosa.midi_to_note(x, unicode=False) if x else '-' for x in v)))


if __name__ == '__main__':
    main()
