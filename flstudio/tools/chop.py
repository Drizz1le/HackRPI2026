"""The chop: Rotary Connection's rubato orchestral intro (0-44 s, no drums) sliced into chord swells and
rebuilt on the grid as a new progression (MPC-style rechop, not a loop), plus Minnie Riperton's bridge
lines for the hook. Baked offline so every stutter is sample-exact:

  <chord>_sus.wav   the swell stretched to exactly 1 bar
  <chord>_chop.wav  1 bar, re-triggered 3-3-2 + 8ths (hook rhythm), last hit rings
  <chord>_rev.wav   1 beat: the swell reversed (sucks into the next bar)
  vox_*.wav         Minnie's lines (vocal stem), stretched to whole beats, formants kept

Writes chops/flip/*.wav + manifest.json.  BPM 88, key G# minor (source key, no pitch change).
"""
import json, os, subprocess, sys, tempfile
import numpy as np, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare import RUBBERBAND

BPM = 88.0
SR = 44100
SRC = 'sources/Black Gold - Rotary Connection.wav'
VOX = 'stems/htdemucs/Black Gold - Rotary Connection/vocals.wav'
OUT = 'chops/flip'
BEAT = 60.0 / BPM

# chord: (start s, end s) in the source intro - picked by onset + chroma (see docs/LEARNINGS.md)
SLICES = {
    'G#m': (6.20, 9.36), 'A': (11.61, 14.47), 'B7': (16.93, 19.23), 'E': (20.04, 22.05),
    'D#7': (28.70, 31.14), 'C#m': (1.65, 4.32)  # 35.9 s version died out mid-bar,
}
# name: (start s, end s, beats) - bridge vocals, all in G# minor
VOCALS = {
    'vox_gold': (174.45, 178.25, 6),    # "I'm the black gold of the sun"  G#4 F#4 .. G#3
    'vox_sea': (166.60, 170.10, 5),     # "I'm the shining sea, I'm the moving heart"
    'vox_smile': (162.45, 164.60, 3),   # "smiling on everyone"
    'vox_free': (170.05, 174.50, 6),    # "I am a man so free"
}


def stretch(y, secs, formant=False):
    tmp = tempfile.mkdtemp()
    a, b = os.path.join(tmp, 'a.wav'), os.path.join(tmp, 'b.wav')
    sf.write(a, y, SR, subtype='FLOAT')
    cmd = [RUBBERBAND, '-q', '-D', '%.6f' % secs] + (['--formant'] if formant else []) + [a, b]
    subprocess.run(cmd, check=True, capture_output=True)
    z, _ = sf.read(b, always_2d=True)
    n = int(round(secs * SR))
    return np.pad(z, ((0, max(0, n - len(z))), (0, 0)))[:n]


def fade(y, a=0.003, b=0.03):
    y = y.copy()
    fa, fb = int(a * SR), int(b * SR)
    y[:fa] *= np.linspace(0, 1, fa)[:, None]
    y[-fb:] *= np.linspace(1, 0, fb)[:, None]
    return y


def read(path, t0, t1):
    y, sr = sf.read(path, always_2d=True, start=int(t0 * SR), stop=int(t1 * SR))
    assert sr == SR
    return y


def stutter(bar):
    """MPC re-trigger: hits on 16th steps 0, 3, 6 (3-3-2), 8, 10, then 12 rings to the end. Each hit
    replays the slice's attack; the gaps are hard cuts with 5 ms declicks (that's the chop sound)."""
    s16 = int(BEAT / 4 * SR)
    out = np.zeros_like(bar)
    hits = [0, 3, 6, 8, 10, 12, 16]
    for a, b in zip(hits[:-1], hits[1:]):
        ln = (b - a) * s16 - (int(0.012 * SR) if b < 16 else 0)  # tiny gap before each retrigger
        seg = fade(bar[:ln], 0.002, 0.005) * (1.0 if a in (0, 6, 12) else 0.85)
        out[a * s16:a * s16 + ln] += seg
    return out


def check():
    """self-check: the stutter keeps the bar length and leaves silence right before each retrigger."""
    bar = np.ones((int(4 * BEAT * SR), 2))
    s = stutter(bar)
    s16 = int(BEAT / 4 * SR)
    assert len(s) == len(bar)
    assert abs(s[3 * s16 - 10]).max() == 0 and abs(s[3 * s16 + 200]).max() > 0


def main():
    check()
    os.makedirs(OUT, exist_ok=True)
    man = {'bpm': BPM, 'key': 'G#m', 'chords': {}, 'vox': {}}
    bar_s = 4 * BEAT
    for name, (t0, t1) in SLICES.items():
        y = read(SRC, t0, t1)
        sus = fade(stretch(y, bar_s))
        sus *= 0.06 / np.sqrt(np.mean(sus ** 2))  # level-match the swells (source dynamics run ppp..ff)
        safe = name.replace('#', 's')
        files = {'sus': sus, 'chop': stutter(sus), 'rev': fade(sus[:int(BEAT * SR)][::-1] * np.linspace(0.2, 1, int(BEAT * SR))[:, None], 0.01, 0.003)}
        man['chords'][name] = {}
        for kind, z in files.items():
            p = os.path.abspath(os.path.join(OUT, '%s_%s.wav' % (safe, kind)))
            sf.write(p, z, SR, subtype='PCM_24')
            man['chords'][name][kind] = p
        print('%-4s %.2fs -> 1 bar (x%.2f)' % (name, t1 - t0, bar_s / (t1 - t0)))
    for name, (t0, t1, beats) in VOCALS.items():
        y = read(VOX, t0, t1)
        z = fade(stretch(y, beats * BEAT, formant=True), 0.005, 0.08)
        p = os.path.abspath(os.path.join(OUT, name + '.wav'))
        sf.write(p, z, SR, subtype='PCM_24')
        man['vox'][name] = {'file': p, 'beats': beats}
        print('%-9s %.2fs -> %d beats (x%.2f)' % (name, t1 - t0, beats, beats * BEAT / (t1 - t0)))
    json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
