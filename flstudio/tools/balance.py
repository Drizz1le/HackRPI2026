"""Per-section spectral balance of a render: % energy per band + RMS, so mix moves are measurable.
usage: python tools/balance.py file.wav [bpm]"""
import sys
import numpy as np, soundfile as sf

SECTIONS = {'intro': (0, 8), 'verse1': (8, 24), 'hook1': (24, 32), 'verse2': (32, 47), 'hook2': (48, 56),
            'interlude': (56, 64), 'return': (64, 72), 'final': (72, 80), 'coda': (80, 92)}
BANDS = [(20, 60), (60, 120), (120, 250), (250, 1000), (1000, 4000), (4000, 12000)]


def balance(path, bpm=82.0):
    y, sr = sf.read(path, always_2d=True)
    y = y.mean(1)
    bar = 4 * 60 / bpm
    out = {}
    for k, (a, b) in SECTIONS.items():
        seg = y[int(a * bar * sr):int(b * bar * sr)]
        S = np.abs(np.fft.rfft(seg)) ** 2
        f = np.fft.rfftfreq(len(seg), 1 / sr)
        tot = S.sum() + 1e-12
        out[k] = [100 * S[(f >= lo) & (f < hi)].sum() / tot for lo, hi in BANDS] + [10 * np.log10((seg ** 2).mean() + 1e-12)]
    return out


if __name__ == '__main__':
    r = balance(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 82.0)
    print('%-11s' % 'section' + ''.join('%9s' % ('%d-%d' % b) for b in BANDS) + '      rms')
    for k, v in r.items():
        print('%-11s' % k + ''.join('%8.1f%%' % x for x in v[:-1]) + '  %6.1f dB' % v[-1])
