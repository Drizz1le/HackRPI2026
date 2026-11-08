"""Spazz edits, baked offline so every cut is sample-exact (FL's Sampler doesn't cut at note-off in CLI
renders, see LEARNINGS), plus the break loops stretched to 114 BPM.

  stut_need   1 bar: "I-I-I-I nee-nee need you to run" (Kanye stem, 16th retriggers into the phrase)
  stut_run    1 bar: "run right back" 8th/16th/32nd retriggers (the build's last bar)
  gate4       4 bars of cyc4 through a 16th trance gate (the build)
  rev_fm      1 beat: the Fm downbeat reversed (sucks into each drop)
  tape2       1 bar: the last bar of cyc2, tape-stopped
  cyc1_cut    cyc1 with its last 3 beats silent (hole for "when the beat drop...")
  cyc4_spz / cyc2_tape / gate4_run   the chop with its last bar replaced by stut_need / tape2 / stut_run
  break/break2  Jail / Egyptian Luvr breaks, 2 bars each at 114
Adds manifest['fx'] and manifest['loops'].
"""
import json, os, subprocess
import numpy as np, soundfile as sf, librosa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'chops', 'flip')
MAN = os.path.join(OUT, 'manifest.json')
KIT = os.path.expanduser('~') + r'\Documents\FLStudio\Dope Tec\~Drum Loops\Breaks'
LOOPS = {'break': (KIT + r'\[110] Jail.wav', 110, 2), 'break2': (KIT + r'\[105] Egyptian Luvr.wav', 105, 2)}
SR = 44100


def fade(y, a=0.002, b=0.006):
    y = y.copy()
    fa, fb = max(1, int(a * SR)), max(1, int(b * SR))
    y[:fa] *= np.linspace(0, 1, fa)[:, None]
    y[-fb:] *= np.linspace(1, 0, fb)[:, None]
    return y


def onset_near(y, t, win=0.15):
    """vocal onset closest to t (s): so a stutter starts on the consonant, not before it."""
    env = librosa.onset.onset_strength(y=y.mean(1), sr=SR, hop_length=128)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=128, units='time')
    near = on[np.abs(on - t) < win]
    return float(near[np.argmin(abs(near - t))]) if len(near) else t


def stutter(y, s16, hits, total16=16):
    """hits: (dst 16th, src time s, length in 16ths) - each hit replays the source from that time."""
    out = np.zeros((total16 * s16, y.shape[1]))
    for d, t, ln in hits:
        a = int(t * SR)
        seg = y[a:a + ln * s16 - int(0.008 * SR)]  # 8 ms gap before the next hit = the chop sound
        out[d * s16:d * s16 + len(seg)] += fade(seg)
    return out


def gate(y, s16, pattern):
    """16th gate: pattern of 1/0 per 16th, repeating; 3 ms edges."""
    g = np.zeros(len(y))
    e = int(0.003 * SR)
    for k in range(len(y) // s16):
        if pattern[k % len(pattern)]:
            g[k * s16:(k + 1) * s16] = 1
    g = np.convolve(g, np.ones(e) / e, mode='same')
    return y * g[:, None]


def tapestop(y):
    """playback rate 1 -> 0 over the segment (quadratic), read by interpolating the source."""
    n = len(y)
    rate = (1 - np.linspace(0, 1, n)) ** 1.5
    pos = np.cumsum(rate)
    pos = np.clip(pos, 0, n - 1)
    return np.stack([np.interp(pos, np.arange(n), y[:, c]) for c in range(y.shape[1])], 1) * np.linspace(1, 0.3, n)[:, None]


def check():
    y = np.ones((SR * 2, 2))
    s = stutter(y, 1000, [(0, 0.0, 1), (2, 0.0, 2)], total16=4)
    assert len(s) == 4000 and abs(s[990:1000]).max() == 0 and abs(s[2100]).max() > 0
    assert abs(tapestop(y)[-1]).max() < 0.5


def main():
    check()
    man = json.load(open(MAN))
    bpm = man['bpm']
    beat = 60 / bpm
    s16 = int(round(beat / 4 * SR))
    rd = lambda k: sf.read(man['chops'][k]['file'], always_2d=True)[0]
    fx = {}
    v4, c4, c3, c2, c1 = rd('cyc4_v'), rd('cyc4'), rd('cyc3'), rd('cyc2'), rd('cyc1')
    # cyc4_v words (whisper on the warped stem, in beats): I 11.8, need 13.0, you 13.6, run 14.7, right 15.2
    w = {k: onset_near(v4, b * beat) for k, b in (('I', 11.8), ('need', 13.0), ('run', 14.7), ('right', 15.2))}
    fx['stut_need'] = stutter(v4, s16, [(0, w['need'], 1), (1, w['need'], 1), (2, w['need'], 1), (3, w['need'], 1),  # 'I' is too soft to retrigger
                                        (4, w['need'], 1), (5, w['need'], 1), (6, w['need'], 2), (8, w['need'], 8)])
    fx['stut_run'] = stutter(v4, s16, [(0, w['run'], 2), (2, w['run'], 2), (4, w['run'], 2), (6, w['run'], 1),
                                       (7, w['run'], 1)] + [(k, w['run'], 1) for k in range(8, 12)] +
                             [(12, w['right'], 4)])
    bar = 16 * s16
    fx['gate4'] = gate(c4[:4 * bar], s16, [1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1])
    b1 = c3[:4 * s16]
    fx['rev_fm'] = fade(b1[::-1] * np.linspace(0.15, 1, len(b1))[:, None], 0.01, 0.004)
    fx['tape2'] = tapestop(c2[-bar:])
    cut = c1.copy()
    cut[len(c1) - 12 * s16 - int(0.01 * SR):] *= 0
    cut[len(c1) - 12 * s16 - int(0.02 * SR):len(c1) - 12 * s16 - int(0.01 * SR)] *= np.linspace(1, 0, int(0.01 * SR))[:, None]
    fx['cyc1_cut'] = cut
    # whole-chop variants: the edit replaces the chop's last bar (two Kanyes on top of each other = mud)
    c4i = rd('cyc4_i')
    spz = c4.copy(); spz[-bar:] = c4i[-bar:] * 0.8 + fx['stut_need'][:bar]
    fx['cyc4_spz'] = spz
    tp = c2.copy(); tp[-bar:] = fx['tape2']
    fx['cyc2_tape'] = tp
    g = fx['gate4'].copy(); g[-bar:] = fx['stut_run'][:bar]
    fx['gate4_run'] = g
    man['fx'] = {}
    for k, y in fx.items():
        p = os.path.join(OUT, k + '.wav')
        sf.write(p, y, SR, subtype='PCM_24')
        man['fx'][k] = p
        print('fx %-9s %.2fs' % (k, len(y) / SR))
    rb = os.path.join(ROOT, 'tools', 'rubberband', 'rubberband-4.0.0-gpl-executable-windows', 'rubberband.exe')
    man['loops'] = {}
    for k, (src, tag, bars) in LOOPS.items():
        y, sr = sf.read(src, always_2d=True)
        y = y[:int(round(bars * 4 * 60 / tag * sr))]
        tmp, dst = os.path.join(OUT, '_' + k + '_src.wav'), os.path.join(OUT, k + '.wav')
        sf.write(tmp, y, sr)
        subprocess.run([rb, '-q', '-D', '%.6f' % (bars * 4 * beat), tmp, dst], check=True, capture_output=True)
        man['loops'][k] = {'file': dst, 'bars': bars}
        print('loop %-7s %.0f -> %.0f BPM, %d bars' % (k, tag, bpm, bars))
    json.dump(man, open(MAN, 'w'), indent=1)


if __name__ == '__main__':
    main()
