"""Per-beat chord estimate (triad template matching on the bass+other stems) for the beat grid in beats.npy."""
import json, sys
import numpy as np, librosa

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def templates():
    t = {}
    for r in range(12):
        for q, iv in (('', (0, 4, 7)), ('m', (0, 3, 7)), ('7', (0, 4, 7, 10))):
            v = np.zeros(12)
            v[[(r + i) % 12 for i in iv]] = 1
            v[r] += 0.5  # root weight
            t[NAMES[r] + q] = v / np.linalg.norm(v)
    return t


def beat_chords(stem_dir, beats, sr=22050):
    y = sum(librosa.load(stem_dir + s, sr=sr)[0] for s in ('other.wav', 'bass.wav'))
    ch = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=36)
    sync = librosa.util.sync(ch, librosa.time_to_frames(beats, sr=sr), aggregate=np.median)[:, 1:]  # col k = beat k
    T = templates()
    names, mat = list(T), np.array(list(T.values()))
    out = []
    for k in range(sync.shape[1]):
        v = sync[:, k] / (np.linalg.norm(sync[:, k]) + 1e-9)
        out.append(names[int(np.argmax(mat @ v))])
    return out


if __name__ == '__main__':
    stems = sys.argv[1]
    beats = np.load('beats.npy')
    c = beat_chords(stems, beats)
    json.dump(c, open('beat_chords.json', 'w'))
    for bar in range(0, len(c) // 4):
        print('bar %3d  %6.2fs  %s' % (bar, beats[bar * 4], ' '.join('%-4s' % x for x in c[bar * 4:bar * 4 + 4])))
