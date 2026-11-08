"""Stereo vs mono level of one soloed insert (catches phase-cancelling 'wideners' that vanish in mono).
usage: python tools/stereo_check.py INSERT START_BAR [SECONDS]"""
import os, sys
import numpy as np, soundcard as sc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fl import fl

t, bar = int(sys.argv[1]), int(sys.argv[2])
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 5
mic = sc.get_microphone(sc.default_speaker().id, include_loopback=True)
fl('import midi\ntransport.stop()\nmixer.soloTrack(%d, 1)\ntransport.setSongPos(%d * 4 * general.getRecPPQ(), midi.SONGLENGTH_ABSTICKS)' % (t, bar))
with mic.recorder(samplerate=44100, channels=2) as rec:
    fl('transport.start()')
    y = rec.record(numframes=int(44100 * secs))
fl('transport.stop()\nmixer.soloTrack(%d, 0)' % t)
db = lambda x: 10 * np.log10((x ** 2).mean() + 1e-12)
print('insert %d: L %.1f  R %.1f  mid %.1f  side %.1f dB  L/R correlation %.2f' % (
    t, db(y[:, 0]), db(y[:, 1]), db(y.mean(1)), db((y[:, 0] - y[:, 1]) / 2), np.corrcoef(y[:, 0], y[:, 1])[0, 1]))
