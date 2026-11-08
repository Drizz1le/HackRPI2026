"""Timing proof for the outro chops (no drums in the source, so measure the piano): onsets of each
piano-only chop vs the 114 BPM 8th grid, and the chord per 2-bar block.
usage: python tools/check_grid.py"""
import json, os
import numpy as np, librosa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
man = json.load(open(os.path.join(ROOT, 'chops', 'flip', 'manifest.json')))
beat = 60.0 / man['bpm']
T = {'Fm': [5, 8, 0], 'C#': [1, 5, 8], 'G#': [8, 0, 3], 'D#': [3, 7, 10]}
for ch in ('cyc1_i', 'cyc3_i', 'cyc4_i'):
    y, sr = librosa.load(man['chops'][ch]['file'], sr=44100)
    on = librosa.onset.onset_detect(y=y, sr=sr, units='time', hop_length=128)
    e = np.abs(((on / (beat / 2)) + .5) % 1 - .5) * beat / 2 * 1000  # ms to the nearest 8th
    blocks = []
    for k in range(0, int(len(y) / sr / beat) // 8):
        c = librosa.feature.chroma_cqt(y=y[int(k * 8 * beat * sr):int((k + 1) * 8 * beat * sr)], sr=sr).mean(1)
        blocks.append(max(T, key=lambda t: sum(c[i] for i in T[t])))
    print('%-7s piano onsets %3d  median %4.0f ms from the 8th grid, %3d%% within 30 ms (random ~ 66 ms / 23%%)   chords %s'
          % (ch, len(on), np.median(e), 100 * np.mean(e < 30), ' '.join(blocks)))
