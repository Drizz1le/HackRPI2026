"""Timing proof for the chops: warp the *drum stem* through exactly the same per-beat time map as each
chop (the sample itself is mostly sustained piano/vocal, too soft-edged to measure) and report how far
its kicks/snares land from the 82 BPM beat grid. If the drums land, the sample played with them lands.
usage: python tools/check_grid.py"""
import json, os, sys
import numpy as np, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prepare

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
beats = prepare.refine_beats(np.load(os.path.join(ROOT, 'beats.npy')))
beat = 60.0 / prepare.BPM
tmp = os.path.join(ROOT, 'out', '_gridcheck.wav')
for name, (stem, b0, n) in prepare.CHOPS.items():
    if stem != 'nodrums':
        continue
    prepare.warp(prepare.STEMS + 'drums.wav', beats[b0:b0 + n + 1], tmp)
    y, sr = librosa.load(tmp, sr=44100)
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=64)
    on = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=64, units='time')
    grid = np.arange(n) * beat
    err = np.array([np.min(np.abs(on - g)) for g in grid])  # nearest drum hit to each beat
    print('%-8s beats %2d  drum hit within 15 ms of the beat: %2d/%2d   median error %4.1f ms  worst %5.1f ms'
          % (name, n, (err < 0.015).sum(), n, 1000 * np.median(err), 1000 * err.max()))
