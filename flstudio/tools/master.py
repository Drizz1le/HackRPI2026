"""Offline master, matched to the Kanye references on disk (tools/compare.py REFS).

  1. tonal match: 1/3-octave long-term spectrum of the mix vs the mean of the refs; 70% of the
     difference, clamped to +-4 dB, smoothed, applied as a linear-phase FIR
  2. glue: stereo-linked RMS compressor, 1.5:1 above -14 dB RMS, 30 ms / 250 ms (about 1-2 dB of gain reduction)
  3. soft clip of the few peaks above -3 dBFS (tanh knee)
  4. true-peak limiter: 4x oversampled detection, 5 ms lookahead, 80 ms release, ceiling -1 dBTP
  5. loudness: gain iterated until ffmpeg's EBU R128 reads the target (default -8 LUFS)

usage: python tools/master.py in.wav out.wav [target_lufs]
"""
import os, subprocess, sys
import numpy as np, soundfile as sf, librosa
from scipy.signal import welch, firwin2, fftconvolve, resample_poly
from scipy.ndimage import minimum_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compare import REFS
from export import FFMPEG, loudness

SR = 44100
CEIL_DB = -1.0
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out', '_ref_ltas.npy')
F3 = 1000 * 2 ** (np.arange(-17, 15) / 3)  # 1/3-octave centres 20 Hz .. 20 kHz


def ltas(y):
    f, p = welch(y, SR, nperseg=8192)
    out = []
    for fc in F3:
        m = (f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6))
        out.append(p[m].mean() if m.any() else 1e-20)
    out = np.array(out)
    return 10 * np.log10(out / out.sum() + 1e-20)


def ref_curve():
    if os.path.exists(CACHE):
        return np.load(CACHE)
    curves = []
    for name, p in REFS.items():
        if os.path.exists(p):
            y, _ = librosa.load(p, sr=SR, mono=True, offset=30, duration=90)
            curves.append(ltas(y))
    c = np.mean(curves, 0)
    np.save(CACHE, c)
    return c


def match_eq(x):
    diff = ref_curve() - ltas(x.mean(1))
    diff = np.convolve(np.pad(diff, 1, mode='edge'), np.ones(3) / 3, 'valid')  # smooth across bands
    lim = np.where((F3 < 30) | (F3 > 14000), 2.0, 4.0)
    g = 0.7 * diff
    g = np.clip(g - np.interp(1000, F3, g), -lim, lim)  # anchor at 1 kHz (tone, not level), then clamp
    freqs = np.concatenate([[0], F3[F3 < SR / 2], [SR / 2]])
    gains = 10 ** (np.concatenate([[g[0]], g[F3 < SR / 2], [g[-1]]]) / 20)
    fir = firwin2(4097, freqs / (SR / 2), gains)
    y = np.stack([fftconvolve(x[:, ch], fir)[2048:2048 + len(x)] for ch in range(x.shape[1])], 1)
    return y, {int(f): float(v) for f, v in zip(np.round(F3), np.round(g, 1))}


def glue(x, ratio=1.5, thresh_db=-14.0, att=0.03, rel=0.25):
    blk = int(0.005 * SR)
    n = len(x) // blk
    lvl = 10 * np.log10(np.mean(x[:n * blk].reshape(n, blk, -1) ** 2, axis=(1, 2)) + 1e-12)
    a, r = np.exp(-0.005 / att), np.exp(-0.005 / rel)
    env, gr = -100.0, np.zeros(n)
    for i, l in enumerate(lvl):
        env = a * env + (1 - a) * l if l > env else r * env + (1 - r) * l
        gr[i] = min(0.0, (thresh_db - env) * (1 - 1 / ratio)) if env > thresh_db else 0.0
    g = np.repeat(10 ** (gr / 20), blk)
    g = np.concatenate([g, np.full(len(x) - len(g), g[-1])])
    return x * g[:, None], float(np.median(gr[lvl > lvl.max() - 20]))


def soft_clip(x, knee_db=-3.0):
    k = 10 ** (knee_db / 20)
    a = np.abs(x)
    over = a > k
    y = x.copy()
    y[over] = np.sign(x[over]) * (k + (1 - k) * np.tanh((a[over] - k) / (1 - k)))
    return y


def limit(x, ceil_db=CEIL_DB, look=0.005, rel=0.08):
    ceil = 10 ** (ceil_db / 20)
    up = resample_poly(x, 4, 1, axis=0)
    pk = np.abs(up).max(1).reshape(-1, 4).max(1)[:len(x)]  # true-peak per output sample
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    need = minimum_filter1d(need, int(look * SR) * 2 + 1)  # lookahead window
    blk = 32
    n = len(need) // blk + 1
    nb = np.pad(need, (0, n * blk - len(need)), constant_values=1.0).reshape(n, blk).min(1)
    r = np.exp(-blk / SR / rel)
    g, out = 1.0, np.empty(n)
    for i, v in enumerate(nb):
        g = v if v < g else r * g + (1 - r) * v
        out[i] = g
    gain = np.interp(np.arange(len(x)), np.arange(n) * blk + blk / 2, out)
    gain = np.minimum(gain, need)  # never above what the lookahead allows
    y = x * gain[:, None]
    return np.clip(y, -ceil, ceil), float(20 * np.log10(gain.min()))


def master(src, dst, target=-8.0):
    x, sr = sf.read(src, always_2d=True)
    assert sr == SR
    before = loudness(src)
    x, eq = match_eq(x)
    x, gr = glue(x)
    gain_db = target - before['integrated_lufs']
    tmp = dst[:-4] + '_tmp.wav'
    for _ in range(4):
        y, lim_gr = limit(soft_clip(x * 10 ** (gain_db / 20)))
        sf.write(tmp, y, SR, subtype='PCM_24')
        got = loudness(tmp)
        if abs(got['integrated_lufs'] - target) < 0.15:
            break
        gain_db += target - got['integrated_lufs']
    os.replace(tmp, dst)
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', dst, '-b:a', '320k', dst[:-4] + '.mp3'], check=True)
    after = loudness(dst)
    assert after['true_peak_dbfs'] <= CEIL_DB + 0.3, after  # self-check: the limiter holds the ceiling
    return {'before': before, 'after': after, 'eq_db': eq, 'glue_gr_db': gr, 'limiter_max_gr_db': lim_gr}


if __name__ == '__main__':
    import json
    r = master(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else -8.0)
    print(json.dumps({k: v for k, v in r.items()}, indent=1, default=str))
