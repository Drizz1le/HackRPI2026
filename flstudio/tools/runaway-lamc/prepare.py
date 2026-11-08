"""Runaway @ LAMC (Larry Hoover benefit, LA Memorial Coliseum, Dec 2021) - the extended outro
("someday you're gonna run away ... I need you to run right back to me, baby ... more specifically,
Kimberly"). No drums there: piano + Kanye, sung free (86-92 BPM drifting), chords B | C#m | A | E,
2 bars each.

Grid: every chord change is an anchor = 8 beats (chord-change times from bass-register chroma +
full chroma, snapped to piano onsets; see docs/LEARNINGS.md). Beats in between are interpolated, then
the usual coupled resample (prepare.py from send-me): time map onto a 114/2^(4/12) grid with Rubber
Band R2, resample to the 114 BPM length -> +4 st and faster at once (hopecore chipmunk Kanye).
Key E -> G#: the cycle C#m A E B becomes Fm C# G# D# (vi IV I V).
Writes chops/flip/*.wav + manifest.json.
"""
import json, os, subprocess, sys, tempfile, glob, shutil
import numpy as np, librosa, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BPM = 114.0
SEMITONES = 4
RATIO = 2 ** (SEMITONES / 12)
SR = 44100
STEMS = os.path.join(ROOT, 'stems/htdemucs/Runaway @ LAMC/')
OUT = os.path.join(ROOT, 'chops/flip')
RUBBERBAND = os.path.join(ROOT, 'tools', 'rubberband', 'rubberband-4.0.0-gpl-executable-windows', 'rubberband.exe')

# chord changes in the outro (source seconds, before snapping); each lasts 8 beats
ANCHORS = [(219.01, 'B'), (226.01, 'C#m'), (230.92, 'A'), (237.38, 'E'), (243.00, 'B'), (248.41, 'C#m'),
           (253.75, 'A'), (258.39, 'E'), (264.00, 'B'), (269.04, 'C#m'), (274.58, 'A'), (280.01, 'E'),
           (285.30, 'B'), (290.64, 'C#m'), (295.93, 'A'), (300.65, 'E'), (305.37, 'B'), (312.06, 'C#m'),
           (316.84, 'A'), (322.20, 'E'), (327.50, None)]
# name: (source, first anchor index, beats)  -  anchor k starts beat 8k
CHOPS = {
    'pre':    ('full', 0, 8),     # B: "run away as fast as you can"
    'cyc1':   ('full', 1, 32),    # "someday I'm gonna make you run away ... that's what some say"
    'cyc2':   ('full', 5, 32),    # "someday he's gonna make you run away ... that's what, that's what"
    'cyc3':   ('full', 9, 32),    # "someday you're gonna run away ... and when you run away baby, I need you to run back, back to me"
    'cyc4':   ('full', 13, 32),   # "I need you to run right back to me, baby" x2
    'tail':   ('full', 17, 24),   # "...run right back, baby / more specifically, Kimberly" + last E
    'cyc1_i': ('inst', 1, 32), 'cyc3_i': ('inst', 9, 32), 'cyc4_i': ('inst', 13, 32),  # piano only
    'cyc3_v': ('vocals', 9, 32), 'cyc4_v': ('vocals', 13, 32),                          # Kanye only
}
FREE = {'hype': (34.10, 36.40)}  # "when the beat drop, I need y'all to make some noise" (speech: plain +4 resample)


def ffmpeg():
    hits = glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe'))
    return hits[0] if hits else (shutil.which('ffmpeg') or 'ffmpeg')


def snapped_anchors():
    y, sr = librosa.load(STEMS + 'other.wav', sr=22050, offset=210)
    on = librosa.onset.onset_detect(y=y, sr=sr, units='time', hop_length=256) + 210
    out = []
    for t, ch in ANCHORS:
        near = on[np.abs(on - t) < 0.35]
        out.append(float(near[np.argmin(abs(near - t))]) if ch and len(near) else t)
    return np.array(out)


def beat_times(anchors, tracked=None, onsets=None):
    """8 beats per anchor span. Inside a span: the tracked beats (librosa, -30 ms lag, snapped to piano
    onsets within 60 ms) when there are exactly 7 of them, else linear (rubato spans)."""
    b = []
    for a, c in zip(anchors[:-1], anchors[1:]):
        lin = [a + (c - a) * k / 8 for k in range(8)]
        if tracked is not None:
            tb = tracked - 0.03
            if onsets is not None:
                tb = np.array([o if abs(o - t) < 0.06 else t for t, o in ((t, onsets[np.argmin(abs(onsets - t))]) for t in tb)])
            inner = tb[(tb > a + 0.25 * (c - a) / 8) & (tb < c - 0.25 * (c - a) / 8)]
            if len(inner) == 7:
                lin = [a] + list(inner)
        b += lin
    return np.array(b + [anchors[-1]])


def piano_onsets():
    y, sr = librosa.load(STEMS + 'other.wav', sr=44100, offset=205)
    return librosa.onset.onset_detect(y=y, sr=sr, units='time', hop_length=128) + 205


def warp(src, bt, dst):
    """coupled resample (send-me/tools/prepare.py): bt[k] -> k beats on the slow grid, then resample."""
    beat = 60.0 / BPM
    t0 = bt[0]
    y, sr = sf.read(src, always_2d=True, start=int(t0 * SR), stop=int(bt[-1] * SR))
    tmp = tempfile.mkdtemp()
    seg, mapf, timed = (os.path.join(tmp, f) for f in ('seg.wav', 'map.txt', 'timed.wav'))
    sf.write(seg, y, SR, subtype='FLOAT')
    n = int(round((len(bt) - 1) * beat * SR))
    nslow = int(round(n * RATIO))
    with open(mapf, 'w') as f:
        for k, t in enumerate(bt):
            f.write('%d %d\n' % (int(round((t - t0) * SR)), int(round(k * beat * RATIO * SR))))
    subprocess.run([RUBBERBAND, '-q', '-D', '%.6f' % (nslow / SR), '-M', mapf, seg, timed], check=True, capture_output=True)
    y, _ = sf.read(timed, always_2d=True)
    y = librosa.resample(y.T, orig_sr=len(y), target_sr=n, axis=-1).T[:n]  # = the +4 st resample, exact length
    f = int(0.004 * SR)
    y[:f] *= np.linspace(0, 1, f)[:, None]
    y[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(dst, y, SR, subtype='PCM_24')


def main():
    os.makedirs(OUT, exist_ok=True)
    full, inst = os.path.join(OUT, '_full.wav'), os.path.join(OUT, '_inst.wav')
    st = {s: sf.read(STEMS + s + '.wav', always_2d=True)[0] for s in ('vocals', 'other', 'bass')}
    sf.write(full, 1.3 * st['vocals'] + st['other'] + st['bass'], SR, subtype='PCM_24')  # Kanye +2.3 dB (Send Me v6 lesson)
    sf.write(inst, st['other'] + st['bass'], SR, subtype='PCM_24')
    srcs = {'full': full, 'inst': inst, 'vocals': STEMS + 'vocals.wav'}
    an = snapped_anchors()
    bt = beat_times(an, np.load(os.path.join(ROOT, 'beats_outro_raw.npy')), piano_onsets())
    np.save(os.path.join(ROOT, 'beats.npy'), bt)
    spb = np.diff(an[:-1])
    print('anchors (snapped):', ' '.join('%.2f' % a for a in an))
    print('source beat per chord: %.3f..%.3f s (median %.3f = %.1f BPM)' % (spb.min() / 8, spb.max() / 8, np.median(spb) / 8, 480 / np.median(spb)))
    man = {'bpm': BPM, 'semitones': SEMITONES, 'key': 'G#', 'chops': {}, 'anchors': an.tolist()}
    for name, (s, a0, n) in CHOPS.items():
        dst = os.path.join(OUT, name + '.wav')
        warp(srcs[s], bt[8 * a0:8 * a0 + n + 1], dst)
        man['chops'][name] = {'file': dst, 'beats': n, 'anchor': a0}
        print('chop %-7s %6.2f-%6.2fs -> %d beats' % (name, bt[8 * a0], bt[8 * a0 + n], n))
    for name, (t0, t1) in FREE.items():
        y, _ = sf.read(STEMS + 'vocals.wav', always_2d=True, start=int(t0 * SR), stop=int(t1 * SR))
        y = librosa.resample(y.T, orig_sr=SR * RATIO, target_sr=SR, axis=-1).T
        dst = os.path.join(OUT, name + '.wav')
        sf.write(dst, y, SR, subtype='PCM_24')
        man['chops'][name] = {'file': dst, 'beats': len(y) / SR * BPM / 60}
    json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)


if __name__ == '__main__':
    assert len(beat_times(np.array([0.0, 8.0, 16.0]))) == 17
    main()
