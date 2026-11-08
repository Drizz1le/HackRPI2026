"""Time the lyrics against the song: where the sampled vocals sing (per beat, from the vocal stems),
where the rap is, how many syllables per bar and how many seconds are left empty.

usage: python tools/lyric_timing.py [lyrics.md]
Song: 74 BPM, 12/8 -> 4 beats/bar, 3.243 s/bar, 80 bars = 4:19.
"""
import os, re, sys
import numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BPM, BARS = 74.0, 80
BEAT = 60 / BPM
TWINS = os.path.join(ROOT, 'stems/htdemucs/You Send Me - Ponderosa Twins/vocals.wav')
# song bar -> (chop source beat, number of bars before it loops), from send.py's arrangement
CHOP_AT = {0: ('intro', 0, 4), 4: ('hookA', 16, 4), 8: ('hookA', 16, 4), 12: ('loopA', 32, 4), 16: ('loopA', 32, 4),
           20: ('loopA', 32, 4), 24: ('loopA', 32, 4), 28: ('hookA', 16, 4), 32: ('hookA', 16, 4),
           40: ('loopA', 32, 4), 44: ('loopA', 32, 4), 48: ('miss', 56, 2), 50: ('miss', 56, 2), 52: ('loopA', 32, 4),
           56: ('darling', 128, 4), 60: ('letter', 112, 4), 64: ('hookA', 16, 4), 68: ('hookA', 16, 4)}
SECTIONS = [('Intro', 0, 4), ('Hook 1', 4, 12), ('Verse 1', 12, 28), ('Hook 2', 28, 36), ('Yeezus', 36, 40),
            ('Verse 2', 40, 56), ('Bridge', 56, 64), ('Final hook', 64, 72), ('Outro', 72, 80)]


def twins_beats():
    """{song bar: 4 flags} - True where the twins sing in that beat (vocal-stem RMS over a gate)."""
    y, sr = sf.read(TWINS, always_2d=True)
    y = y.mean(1)
    src = np.load(os.path.join(ROOT, 'beats.npy'))
    rms = np.array([np.sqrt(np.mean(y[int(a * sr):int(b * sr)] ** 2)) for a, b in zip(src[:-1], src[1:])])
    gate = 0.25 * np.percentile(rms, 95)
    out = {}
    for bar in range(BARS):
        start = max((b for b in CHOP_AT if b <= bar), default=None)
        if start is None or bar >= start + CHOP_AT[start][2]:
            out[bar] = [False] * 4
            continue
        b0 = CHOP_AT[start][1] + 4 * (bar - start)
        out[bar] = [bool(rms[b0 + k] > gate) for k in range(4)]
    return out


def syllables(cell):
    cell = re.sub(r'\(.*?\)|[^\w\s\'-]', ' ', cell)
    return sum(1 + w.strip('-').count('-') for w in cell.split() if w.strip('-'))


def rap_bars(path):
    """{bar: [syllables per beat]} from the [ beat ][ beat ][ beat ][ beat ] notation."""
    bars = {}
    for line in open(path, encoding='utf-8'):
        m = re.match(r'\s*(\d+)(?:-(\d+))?\s*▌?\s*(.*)', line)
        if not m or '[' not in m.group(3):
            continue
        cells = re.findall(r'\[([^\]]*)\]', m.group(3))
        bars[int(m.group(1))] = [syllables(c) for c in cells]
    return bars


def main(path):
    tw, rap = twins_beats(), rap_bars(path)
    total_empty = 0
    print('bar  twins  rap/beat        syl   (T = twins sing that beat)')
    for name, a, b in SECTIONS:
        sec_syl = sec_rap = sec_empty = 0
        for bar in range(a, b):
            t = ''.join('T' if f else '.' for f in tw[bar])
            r = rap.get(bar, [])
            busy = [tw[bar][k] or (k < len(r) and r[k] > 0) for k in range(4)]
            sec_empty += busy.count(False)
            sec_syl += sum(r)
            sec_rap += bool(sum(r))
            print('%3d  %s   %-14s %3s' % (bar, t, ' '.join(map(str, r)) or '-', sum(r) or ''))
        secs = (b - a) * 4 * BEAT
        total_empty += sec_empty
        print('== %-10s bars %2d-%2d  %5.1fs  rap in %2d/%d bars, %4.1f syl/bar rapped, %4.1fs with no voice at all\n'
              % (name, a, b - 1, secs, sec_rap, b - a, sec_syl / max(sec_rap, 1), sec_empty * BEAT))
    full = [sum(v) for v in rap.values() if sum(v) > 4]  # ad-lib bars (<=4 syllables) don't count as rap
    print('song %.0fs, rap in %d/%d bars at %.1f syl/bar (%.1f syl/s), no voice for %.0fs (%.0f%%)' % (BARS * 4 * BEAT,
          len(full), BARS, np.mean(full), np.mean(full) / (4 * BEAT), total_empty * BEAT, 100 * total_empty / (BARS * 4)))


if __name__ == '__main__':
    assert syllables('MA-ma said "turn') == 4 and syllables('(baby come close)') == 0
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'lyrics.md'))
