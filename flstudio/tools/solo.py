"""Mike Dean style guitar solo (Devil in a New Dress move), rendered offline from real guitar notes.

FL's piano roll can't do expressive bends on a sampled guitar, so: real "Picked Humb" notes rendered
by FL (tools/render_notes.py -> gtr/humb/note_<key>.wav) are played along a continuous pitch curve
(bends, releases, slides, hammer-ons, delayed vibrato), sustained by period-aligned grains, then
overdriven and put through a guitar cab impulse. Delay/reverb are on mixer insert 10 in FL.

Phrase language: (bar, beat, beats, midi, art)
  art: ''  pluck              'h' hammer-on / pull-off (legato, no pick)
       'b' pick 2 st below, bend up      'b1' pick 1 st below, bend up
       'r' release: start 2 st above (held bend), let down   '/' slide in from 3 st below
  notes >= 1 beat get vibrato after 180 ms (Dean: slow and wide, ~5.5 Hz, +-0.3 st)
"""
import glob, os, re, sys
import numpy as np, soundfile as sf, librosa
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = {int(re.search(r'note_(\d+)', f).group(1)): f for f in glob.glob(os.path.join(ROOT, 'gtr', 'humb', 'note_*.wav'))}

# 16 bars over G#m | A | B7 | D#7, G# minor pentatonic + b2 (A) and the leading tone G over D#7.
# Original line in Dean's vocabulary (not his Devil melody).
SOLO = [
    # call: low, lyrical, space
    (0, 0.5, 1.5, 63, '/'), (0, 2.5, 0.5, 66, ''), (0, 3, 1, 68, 'b'),
    (1, 0, 1.5, 69, 'h'), (1, 2, 0.5, 68, 'h'), (1, 2.5, 0.5, 64, ''), (1, 3, 1, 61, ''),
    (2, 0.5, 0.5, 59, ''), (2, 1, 0.5, 63, ''), (2, 1.5, 0.5, 66, 'h'), (2, 2, 2, 69, 'b1'),
    (3, 0, 0.5, 68, 'r'), (3, 0.5, 0.5, 66, ''), (3, 1, 0.5, 67, 'h'), (3, 2, 2, 63, ''),
    # response: up an octave-ish
    (4, 0, 1, 71, '/'), (4, 1.5, 0.5, 73, ''), (4, 2, 1.5, 75, 'b'), (4, 3.5, 0.5, 73, ''),
    (5, 0, 1.5, 73, ''), (5, 1.5, 0.5, 71, 'h'), (5, 2, 0.5, 69, ''), (5, 2.5, 0.5, 68, 'h'), (5, 3, 1, 64, ''),
    (6, 0, 0.5, 66, '/'), (6, 0.5, 0.5, 71, ''), (6, 1, 0.5, 75, ''), (6, 1.5, 1.5, 78, 'b'), (6, 3, 1, 75, ''),
    (7, 0, 1.5, 79, 'b1'), (7, 1.5, 0.5, 78, 'r'), (7, 2, 0.5, 75, ''), (7, 2.5, 0.5, 73, 'h'), (7, 3, 1, 70, ''),
    # drums back: busier, 16th runs
    (8, 0, 2, 80, 'b'), (8, 2, 0.5, 78, 'r'), (8, 2.5, 0.25, 75, ''), (8, 2.75, 0.25, 73, 'h'),
    (8, 3, 0.25, 75, 'h'), (8, 3.25, 0.25, 73, 'h'), (8, 3.5, 0.5, 71, ''),
    (9, 0, 0.5, 73, ''), (9, 0.5, 0.5, 76, ''), (9, 1, 1.5, 81, '/'), (9, 2.5, 0.5, 80, 'h'), (9, 3, 1, 76, ''),
    (10, 0, 0.25, 71, ''), (10, 0.25, 0.25, 73, 'h'), (10, 0.5, 0.25, 75, ''), (10, 0.75, 0.25, 78, 'h'),
    (10, 1, 0.25, 80, ''), (10, 1.25, 0.25, 81, 'h'), (10, 1.5, 1.5, 83, 'b'), (10, 3, 1, 81, 'r'),
    (11, 0, 0.5, 78, ''), (11, 0.5, 1, 79, 'b1'), (11, 1.5, 0.5, 75, ''), (11, 2, 0.5, 70, ''),
    (11, 2.5, 0.5, 67, 'h'), (11, 3, 1, 75, '/'),
    # peak: the same bend twice, then the top
    (12, 0, 1, 85, 'b'), (12, 1, 0.5, 83, 'r'), (12, 1.5, 0.5, 80, ''), (12, 2, 2, 85, 'b'),
    (13, 0, 3, 87, 'b'), (13, 3, 1, 85, 'r'),
    (14, 0, 0.25, 83, ''), (14, 0.25, 0.25, 81, 'h'), (14, 0.5, 0.25, 78, ''), (14, 0.75, 0.25, 75, 'h'),
    (14, 1, 0.25, 78, ''), (14, 1.25, 0.25, 75, 'h'), (14, 1.5, 0.25, 71, ''), (14, 1.75, 0.25, 69, 'h'),
    (14, 2, 2, 78, 'b'),
    (15, 0, 1, 79, 'b1'), (15, 1, 0.5, 78, 'r'), (15, 1.5, 0.5, 75, ''), (15, 2, 0.5, 70, ''),
    (15, 2.5, 0.5, 67, 'h'), (15, 3, 6, 68, '/'),
]


def sustained(key, secs):
    """attack of the real note + grains of its steady part, hop = whole periods (phase-aligned)."""
    y, sr = sf.read(NOTES[key])
    assert sr == SR
    f0 = librosa.midi_to_hz(key)
    per = SR / f0
    a = int(0.22 * SR)
    g_len = int(round(4 * per))
    hop = int(round(2 * per))
    grain = y[a:a + g_len] * np.hanning(g_len)
    lvl = np.sqrt(np.mean(y[int(0.15 * SR):a] ** 2)) / (np.sqrt(np.mean(grain ** 2)) + 1e-9)
    n = int(secs * SR) + SR
    out = np.zeros(n + g_len)
    out[:a] = y[:a]
    k = a - g_len // 2
    while k < n:
        if k >= 0:
            out[k:k + g_len] += grain * lvl
        k += hop
    xf = int(0.03 * SR)  # crossfade the real decay into the grains
    out[a - xf:a] = y[a - xf:a] * np.linspace(1, 0, xf) + out[a - xf:a] * np.linspace(0, 1, xf)
    env = np.ones(len(out))
    env[a:] = np.exp(-(np.arange(len(out) - a) / SR) / 6.0)  # slow decay; the drive flattens it
    return out[:n] * env[:n]


def render(solo, bpm, bars_total):
    beat = 60.0 / bpm
    n = int((bars_total * 4 * beat + 4) * SR)
    pitch = np.full(n, np.nan)
    plucks = []  # (sample index, midi at pick)
    t_of = lambda bar, b: int((bar * 4 + b) * beat * SR)
    for i, (bar, b, ln, key, art) in enumerate(solo):
        s, e = t_of(bar, b), t_of(bar, b + ln)
        start = key - (2 if art == 'b' else 1 if art == 'b1' else -2 if art == 'r' else 3 if art == '/' else 0)
        glide = {'b': 0.11, 'b1': 0.08, 'r': 0.09, '/': 0.06, 'h': 0.012}.get(art, 0.0)
        tt = np.arange(e - s) / SR
        p = np.where(tt < glide, start + (key - start) * np.sin(np.pi / 2 * np.clip(tt / max(glide, 1e-6), 0, 1)), key) \
            if glide else np.full(e - s, float(key))
        if ln * beat >= 0.5:  # delayed, widening vibrato on held notes
            d = np.clip((tt - 0.18) / 0.4, 0, 1)
            p = p + 0.3 * d * np.sin(2 * np.pi * 5.5 * tt)
        pitch[s:e] = p
        if art != 'h':
            plucks.append((s, start))
    out = np.zeros(n)
    plucks.append((n, 0))
    for (s, k), (s2, _) in zip(plucks[:-1], plucks[1:]):
        seg_p = pitch[s:s2]
        valid = ~np.isnan(seg_p)
        end = s + (np.argmin(valid) if not valid.all() else len(seg_p))  # note ends where the pitch curve ends
        base = min(NOTES, key=lambda x: abs(x - k))
        ratio = 2 ** ((pitch[s:end] - base) / 12)
        pos = np.concatenate([[0], np.cumsum(ratio)[:-1]])
        src = sustained(base, (end - s) / SR * ratio.max() + 0.1)
        seg = np.interp(pos, np.arange(len(src)), src)
        r = min(int(0.03 * SR), len(seg))
        seg[-r:] *= np.linspace(1, 0, r)
        out[s:end] += seg
    return out


def amp(x):
    """Dean tone: tight low end, mid push, asymmetric overdrive, cab IR, a touch of compression."""
    x = sosfilt(butter(2, 110, 'high', fs=SR, output='sos'), x)
    x = x / (np.abs(x).max() + 1e-9)
    x = x + 0.6 * sosfilt(butter(2, [600, 1400], 'band', fs=SR, output='sos'), x)
    y = np.tanh(9 * x + 0.15) - np.tanh(0.15)
    y = sosfilt(butter(2, 40, 'high', fs=SR, output='sos'), y)
    ir, _ = sf.read(os.path.join(ROOT, 'gtr', 'cab_A.wav'))
    ir = ir[:int(0.1 * SR)]
    y = fftconvolve(y, ir / np.abs(ir).sum() * 8)[:len(y)]
    y = sosfilt(butter(2, 6500, 'low', fs=SR, output='sos'), y)
    return 0.5 * y / (np.abs(y).max() + 1e-9)


def check():
    p = render([(0, 0, 1, 64, ''), (0, 1, 1, 66, 'h'), (0, 2, 1, 68, 'b')], 120.0, 1)
    assert np.isfinite(p).all() and np.abs(p).max() > 0.01
    # the bend must actually reach the target pitch
    seg = p[int(2.3 * 0.5 * SR):int(2.45 * 0.5 * SR) + 4096]
    f = librosa.yin(seg, fmin=200, fmax=500, sr=SR).mean()
    assert abs(librosa.hz_to_midi(f) - 68) < 0.6, librosa.hz_to_midi(f)


if __name__ == '__main__':
    check()
    bpm = float(sys.argv[1]) if len(sys.argv) > 1 else 88.0
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'chops', 'flip', 'solo.wav')
    y = amp(render(SOLO, bpm, 17))
    sf.write(out, np.stack([y, y], 1), SR, subtype='PCM_24')
    print('solo ->', out, '%.1fs' % (len(y) / SR))
