"""Balance the mix by listening: solo each insert where it plays, measure gated RMS, move the fader
(in real dB through FL's API) toward a target balance, repeat. Saves the project (Song mode) after.

Targets = soloed, pre-master gated RMS in dBFS. MBDTF balance (docs/research.md): drums loud and
forward, the sample right under them, bass solid but not swamping, pads/strings as a bed.
usage: python tools/autogain.py [passes]
"""
import os, sys
import numpy as np, soundcard as sc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fl import fl

# insert: (target dB, bar to measure from, seconds)
PLAN = {1: (-13.0, 9, 4), 2: (-15.0, 9, 4), 3: (-24.0, 9, 4), 4: (-14.0, 9, 4), 5: (-18.0, 35, 4),
        6: (-18.0, 9, 4), 7: (-21.0, 25, 4), 8: (-17.0, 57, 4), 9: (-20.0, 24, 3), 10: (-17.0, 66, 4)}

# FL mixer fader curve, measured through the API (value -> dB). FL applies setTrackVolume
# asynchronously (a read-back in the same script call is stale), so the dB->value mapping is done here.
CURVE = [(0.05, -35.83), (0.1, -29.13), (0.15, -24.92), (0.2, -21.71), (0.25, -19.05), (0.3, -16.73),
         (0.35, -14.63), (0.4, -12.7), (0.45, -10.89), (0.5, -9.18), (0.55, -7.54), (0.6, -5.95),
         (0.65, -4.41), (0.7, -2.91), (0.75, -1.44), (0.8, 0.0), (0.85, 1.42), (0.9, 2.83), (0.95, 4.21), (1.0, 5.59)]


def db_to_fader(db):
    return float(np.interp(db, [d for _, d in CURVE], [v for v, _ in CURVE]))


def gated_rms(y, sr, gate_db=-45.0):
    win = int(0.05 * sr)
    frames = y[:len(y) // win * win].reshape(-1, win)
    db = 10 * np.log10((frames ** 2).mean(1) + 1e-12)
    keep = frames[db > gate_db]
    return 10 * np.log10((keep ** 2).mean() + 1e-12) if len(keep) else -99.0


def measure(mic, t, bar, secs, sr=44100):
    fl('import midi\ntransport.stop()\nif transport.getLoopMode() == 0: transport.setLoopMode()\n'
       'mixer.soloTrack(%d, 1)\ntransport.setSongPos(%d * 4 * general.getRecPPQ(), midi.SONGLENGTH_ABSTICKS)' % (t, bar))
    with mic.recorder(samplerate=sr, channels=2) as rec:
        fl('transport.start()')
        y = rec.record(numframes=int(secs * sr)).mean(1)
    fl('transport.stop()\nmixer.soloTrack(%d, 0)' % t)
    return gated_rms(y, sr)


HEADROOM = 4.0  # highest fader allowed; if a track needs more, every fader moves down together


def main(passes=2, chop_channels=()):
    mic = sc.get_microphone(sc.default_speaker().id, include_loopback=True)
    names = fl('[mixer.getTrackName(t) for t in range(11)]')
    for ch in chop_channels:  # Sampler default is -5.2 dB; chops play at 0 dB
        fl('channels.setChannelVolume(%d, 1.0)' % ch)
    for p in range(passes):
        need = {}
        for t, (target, bar, secs) in PLAN.items():
            got = measure(mic, t, bar, secs)
            cur = fl('mixer.getTrackVolume(%d, 1)' % t)
            cur = -40.0 if cur is None or cur < -40 else cur
            need[t] = (cur + (target - got), got, cur)
        shift = max(0.0, max(v[0] for v in need.values()) - HEADROOM)
        for t, (want, got, cur) in need.items():
            db = max(-40.0, want - shift)
            fl('mixer.setTrackVolume(%d, %r)' % (t, db_to_fader(db)))
            print('pass %d  %2d %-14s measured %6.1f  target %6.1f  fader %6.1f -> %6.1f dB' % (
                p + 1, t, names[t], got, PLAN[t][0], cur, db))
        if shift:
            print('pass %d  all faders -%.1f dB (master limiter makes the loudness back)' % (p + 1, shift))
    fl('import midi\nif transport.getLoopMode() == 0: transport.setLoopMode()\ntransport.globalTransport(midi.FPT_Save, 1)')


if __name__ == '__main__':
    import json
    mixfile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out', 'Send Me.mix.json')
    chops = json.load(open(mixfile))['route'].get('4', []) + json.load(open(mixfile))['route'].get('5', [])
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2, chops)
