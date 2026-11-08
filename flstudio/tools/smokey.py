"""Smokey Robinson "Baby Come Close" vocal chops, Graduation chipmunk style: coupled resample +5 st
(B major -> E major, the song key; speed and pitch together like an ASR-10), then a small time-only
stretch (Rubber Band R2) to whole beats at 74 BPM. Vocal stem. Appends to chops/flip/manifest.json.
"""
import json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare import RUBBERBAND, BPM, OUT

SR = 44100
SEMI = 5
VOX = 'stems/htdemucs/Baby Come Close - Smokey Robinson/vocals.wav'
CHOPS = {  # name: (start s, end s, beats)
    'sm_lights': (115.60, 122.40, 6),   # "turn the lights down low, baby come close"
    'sm_close': (119.90, 122.40, 2),    # "baby come close"
    'sm_warm': (145.95, 152.90, 6),     # "so warm, so warm"
    'sm_dreams': (183.50, 188.80, 5),   # "let dreams come true, let dreams come true"
}


def chop(t0, t1, beats):
    y, sr = sf.read(VOX, always_2d=True, start=int(t0 * SR), stop=int(t1 * SR))
    r = 2 ** (SEMI / 12)
    y = librosa.resample(y.T, orig_sr=SR * r, target_sr=SR, axis=-1).T  # play faster = higher (coupled)
    tmp = tempfile.mkdtemp()
    a, b = os.path.join(tmp, 'a.wav'), os.path.join(tmp, 'b.wav')
    sf.write(a, y, SR, subtype='FLOAT')
    secs = beats * 60.0 / BPM
    subprocess.run([RUBBERBAND, '-q', '-D', '%.6f' % secs, a, b], check=True, capture_output=True)
    z, _ = sf.read(b, always_2d=True)
    n = int(round(secs * SR))
    z = np.pad(z, ((0, max(0, n - len(z))), (0, 0)))[:n]
    f, g = int(0.005 * SR), int(0.06 * SR)
    z[:f] *= np.linspace(0, 1, f)[:, None]
    z[-g:] *= np.linspace(1, 0, g)[:, None]
    return z, len(y) / SR


def main():
    mp = os.path.join(OUT, 'manifest.json')
    man = json.load(open(mp))
    for name, (t0, t1, beats) in CHOPS.items():
        z, natural = chop(t0, t1, beats)
        p = os.path.abspath(os.path.join(OUT, name + '.wav'))
        sf.write(p, z, SR, subtype='PCM_24')
        man['chops'][name] = {'file': p, 'beats': beats, 'src_beat': None}
        print('%-10s %.2fs -> chipmunk %.2fs -> %d beats (%.2fs)' % (name, t1 - t0, natural, beats, beats * 60 / BPM))
    json.dump(man, open(mp, 'w'), indent=1)


if __name__ == '__main__':
    main()
