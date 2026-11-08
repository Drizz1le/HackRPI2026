"""Yeezus left-turns, baked offline so every edit is sample-exact (74 BPM, E):

  yz_demon     Smokey "so warm" pitched down an octave (formants down too), driven + bit-crushed (I Am a God)
  yz_stutter   "s-s-s-s-send me": the first 16th of vox_send re-triggered, accelerating, then the phrase
  yz_tapestop  the last beat of the verse loop slowing to a stop (one beat long)
  yz_acid      2 bars of a 303-style acid line (saw + resonant swept low-pass + drive), On Sight
  yz_808       a blown-out 808 on E, Black Skinhead / Blood on the Leaves weight
  yz_riser     1 bar white-noise riser (band-pass sweep up) into the drop
  yz_scream    Smokey's "ooh" +7 st and torn up: a short scream stab
Appends to chops/flip/manifest.json (key 'yz').
"""
import json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare import RUBBERBAND, BPM, OUT

SR = 44100
BEAT = 60.0 / BPM
KIT808 = os.path.expanduser('~') + r'\Documents\FLStudio\Dope Tec\-808s & Bass\[808] Clean.wav'


def load(name):
    y, sr = sf.read(os.path.join(OUT, name + '.wav'), always_2d=True)
    assert sr == SR
    return y


def rb(y, *args):
    tmp = tempfile.mkdtemp()
    a, b = os.path.join(tmp, 'a.wav'), os.path.join(tmp, 'b.wav')
    sf.write(a, y, SR, subtype='FLOAT')
    subprocess.run([RUBBERBAND, '-q', *args, a, b], check=True, capture_output=True)
    return sf.read(b, always_2d=True)[0]


def fit(y, beats):
    n = int(round(beats * BEAT * SR))
    return np.pad(y, ((0, max(0, n - len(y))), (0, 0)))[:n]


def fade(y, a=0.003, b=0.02):
    fa, fb = int(a * SR), int(b * SR)
    y[:fa] *= np.linspace(0, 1, fa)[:, None]
    y[-fb:] *= np.linspace(1, 0, fb)[:, None]
    return y


def norm(y, peak=0.8):
    return y * peak / (np.abs(y).max() + 1e-9)


def demon():
    y = rb(load('sm_warm'), '-p', '-12')  # no --formant: the voice drops with it
    y = np.tanh(y * 6)
    y = np.round(y * 24) / 24  # bit crush
    y = sosfilt(butter(2, [80, 5000], 'band', fs=SR, output='sos'), y, axis=0)
    return fade(norm(fit(y, 6)))


def stutter():
    v = load('vox_send')
    s16 = int(BEAT / 4 * SR)
    out = []
    for ln in (s16, s16, s16 // 2, s16 // 2, s16 // 4, s16 // 4, s16 // 4, s16 // 4):  # accelerating
        out.append(fade(v[:ln].copy(), 0.002, 0.004))
    head = np.concatenate(out)
    y = np.concatenate([head, v])
    return fade(fit(y, 4))


def tapestop():
    y = load('loopA')
    seg = y[int(15 * BEAT * SR):int(16 * BEAT * SR)]
    n = len(seg)
    rate = np.linspace(1.0, 0.0, n) ** 1.5  # slows to a halt over one beat
    pos = np.cumsum(rate)
    out = np.stack([np.interp(pos, np.arange(n), seg[:, ch]) for ch in range(seg.shape[1])], 1)
    return fade(out, 0.002, 0.03)


def acid():
    """303-ish: saw, resonant low-pass whose cutoff sweeps per note, accent, slide, then drive."""
    steps = [(0, 40, 1, 1), (1, 40, 0, 0), (2, 52, 1, 0), (3, 43, 0, 1), (4, 40, 0, 0), (5, 47, 1, 0),
             (6, 50, 0, 1), (7, 52, 1, 0), (8, 40, 1, 0), (9, 55, 0, 1), (10, 52, 1, 0), (11, 47, 0, 0)]
    t16 = BEAT / 3  # triplet 8ths (12 per bar), the song's grid
    n = int(2 * 12 * t16 * SR)
    f = np.zeros(n)
    acc = np.zeros(n)
    cut = np.zeros(n)
    for bar in range(2):
        for st, key, accent, slide in steps:
            a = int((bar * 12 + st) * t16 * SR)
            b = a + int(t16 * SR)
            hz = 440 * 2 ** ((key - 69) / 12)
            f[a:b] = hz
            if slide and a > 0:
                k = int(0.04 * SR)
                f[a:a + k] = np.linspace(f[a - 1], hz, k)
            env = np.exp(-np.arange(b - a) / SR / (0.09 if accent else 0.05))
            cut[a:b] = 300 + (3200 if accent else 1600) * env * (1 + 0.6 * bar)  # opens up in bar 2
            acc[a:b] = (1.0 if accent else 0.6) * np.minimum(1, np.arange(b - a) / (0.003 * SR))
    phase = np.cumsum(f / SR)
    saw = 2 * (phase % 1) - 1
    # resonant state-variable low-pass, cutoff per sample (block-wise for speed)
    y = np.zeros(n)
    low = band = 0.0
    q = 0.12
    blk = 64
    for i in range(0, n, blk):
        fc = 2 * np.sin(np.pi * min(cut[i], 8000) / SR)
        for j in range(i, min(i + blk, n)):
            low += fc * band
            high = saw[j] - low - q * band
            band += fc * high
            y[j] = low
    y = np.tanh(y * acc * 3.5)
    y = sosfilt(butter(2, 60, 'high', fs=SR, output='sos'), y)
    return fade(norm(np.stack([y, y], 1), 0.7))


def blown_808():
    y, sr = sf.read(KIT808, always_2d=True)
    y = rb(y, '-p', '4')  # roughly onto E
    y = np.tanh(y * 10) * 0.8
    y = sosfilt(butter(2, 4000, 'low', fs=SR, output='sos'), y, axis=0)
    return fade(norm(fit(y, 3), 0.9), 0.001, 0.08)


def riser():
    n = int(4 * BEAT * SR)
    rng = np.random.default_rng(1)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = int(0.02 * SR)
    for i in range(0, n, blk):
        k = i / n
        fc = 300 * (40 ** k)
        sos = butter(2, [fc * 0.7, min(fc * 1.4, 18000)], 'band', fs=SR, output='sos')
        out[i:i + blk] = sosfilt(sos, x[max(0, i - 2048):i + blk])[-len(out[i:i + blk]):] * (0.2 + 0.8 * k ** 2)
    return fade(norm(np.stack([out, out[::-1] * 0 + out], 1), 0.6), 0.01, 0.005)


def scream():
    y = load('sm_warm')[:int(1.5 * BEAT * SR)]
    y = rb(y, '-p', '7')
    y = np.tanh(y * 12)
    y = sosfilt(butter(2, [400, 7000], 'band', fs=SR, output='sos'), y, axis=0)
    return fade(norm(fit(y, 2), 0.7), 0.002, 0.15)


def main():
    mp = os.path.join(OUT, 'manifest.json')
    man = json.load(open(mp))
    man['yz'] = {}
    for name, fn in (('yz_demon', demon), ('yz_stutter', stutter), ('yz_tapestop', tapestop), ('yz_acid', acid),
                     ('yz_808', blown_808), ('yz_riser', riser), ('yz_scream', scream)):
        y = fn()
        assert np.isfinite(y).all() and np.abs(y).max() > 0.05, name  # self-check: audible, no NaNs
        p = os.path.abspath(os.path.join(OUT, name + '.wav'))
        sf.write(p, y, SR, subtype='PCM_24')
        man['yz'][name] = p
        print('%-12s %.2fs  peak %.2f' % (name, len(y) / SR, np.abs(y).max()))
    json.dump(man, open(mp, 'w'), indent=1)


if __name__ == '__main__':
    main()
