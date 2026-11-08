"""Solo each mixer insert in turn while a section plays, record FL's output, report level + sub share.
The 'which track is muddying the low end' question, answered by listening instead of guessing.
usage: python tools/solo_scan.py START_BAR SECONDS [inserts...]"""
import os, sys, time
import numpy as np, soundcard as sc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fl import fl

bar, secs = int(sys.argv[1]), float(sys.argv[2])
inserts = [int(x) for x in sys.argv[3:]] or list(range(1, 11))
mic = sc.get_microphone(sc.default_speaker().id, include_loopback=True)
sr = 44100
names = fl('[mixer.getTrackName(t) for t in range(11)]')
for t in inserts:
    fl('import midi\ntransport.stop()\nif transport.getLoopMode() == 0: transport.setLoopMode()\n'
       'mixer.soloTrack(%d, 1)\ntransport.setSongPos(%d * 4 * general.getRecPPQ(), midi.SONGLENGTH_ABSTICKS)' % (t, bar))
    with mic.recorder(samplerate=sr, channels=2) as rec:
        fl('transport.start()')
        y = rec.record(numframes=int(secs * sr)).mean(1)
    fl('transport.stop()\nmixer.soloTrack(%d, 0)' % t)
    S = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / sr)
    tot = S.sum() + 1e-12
    print('%2d %-14s rms %6.1f dB   <60Hz %5.1f%%   60-250 %5.1f%%   >250 %5.1f%%' % (
        t, names[t], 10 * np.log10((y ** 2).mean() + 1e-12), 100 * S[f < 60].sum() / tot,
        100 * S[(f >= 60) & (f < 250)].sum() / tot, 100 * S[f >= 250].sum() / tot))
fl('for t in range(11): mixer.soloTrack(t, 0)')
