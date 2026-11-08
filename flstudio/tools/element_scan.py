"""Render each element of the song alone (FL command-line render of a filtered build) and report its
level and band balance - finds what muddies the mix by measurement, not guesswork.
FL must be closed (the CLI renderer will not run next to an open instance).
usage: python tools/element_scan.py"""
import os, subprocess, sys, time
import numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from fl import FL_EXE

GROUPS = {'kick': 'kick', 'kick2': 'kick2', '808': '808', 'snare+clap': 'snare,snare2,clap', 'hats+perc': 'hat,ohat,crash,bigdrum,tom',
          'sample': 'loopA,loopA_lpf,hookA,hookB,prehook,last,vamp', 'vox': 'vox_light,vox_head,vox_saw,vox_eyes1,vox_eyes2,eyes1_dist,eyes2_dist',
          'moog': 'moog', 'lowstr': 'lowstr', 'cello': 'cello', 'choir': 'choir', 'piano': 'piano', 'brass': 'brass', 'lead+gtr': 'lead,gtr'}
BANDS = [(20, 60), (60, 120), (120, 250), (250, 1000), (1000, 4000), (4000, 16000)]
out = os.path.join(ROOT, 'out', 'elements')
os.makedirs(out, exist_ok=True)
subprocess.run(['taskkill', '/F', '/IM', 'FL64.exe'], capture_output=True)
print('%-11s %7s %7s ' % ('element', 'rms', 'peak') + ''.join('%8s' % ('%d-%d' % b) for b in BANDS))
for name, keys in GROUPS.items():
    flp = os.path.join(out, name + '.flp')
    subprocess.run([sys.executable, os.path.join(ROOT, 'song.py'), flp], env=dict(os.environ, ONLY=keys), check=True, capture_output=True)
    subprocess.run([FL_EXE, '/R', '/Ewav', flp], timeout=600)
    wav = flp[:-4] + '.wav'
    for _ in range(60):
        if os.path.exists(wav):
            break
        time.sleep(1)
    y, sr = sf.read(wav, always_2d=True)
    y = y.mean(1)
    act = y[np.abs(y) > 1e-4]
    S = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / sr)
    tot = S.sum() + 1e-12
    print('%-11s %6.1f %6.1f ' % (name, 10 * np.log10((act ** 2).mean() + 1e-12), 20 * np.log10(np.abs(y).max() + 1e-12))
          + ''.join('%7.1f%%' % (100 * S[(f >= a) & (f < b)].sum() / tot) for a, b in BANDS))
