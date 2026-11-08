"""Render sustained single notes of an FL instrument preset through the FL command line -> one WAV per
note. Used to get real guitar notes (FL's encrypted DirectWave packs can't be decoded outside FL) for
the offline Mike Dean solo engine (tools/solo.py).

usage: python tools/render_notes.py "<preset.fst>" outdir key1 key2 ...   (MIDI keys)
"""
import os, subprocess, sys, time
import numpy as np, soundfile as sf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flpbuild import Project, BAR
from fl import FL_EXE
from export import close_fl

NOTE_BARS = 2  # each note: 1.5 bars held, 0.5 bar gap, at 120 BPM = 3 s + 1 s


def render(fst, outdir, keys):
    outdir = os.path.abspath(outdir)
    os.makedirs(outdir, exist_ok=True)
    pr = Project(tempo=120.0)
    ch = pr.plugin('inst', fst)
    notes = [(ch, i * NOTE_BARS * BAR, int(1.5 * BAR), k, 110, 64) for i, k in enumerate(keys)]
    pid = pr.pattern('notes', notes)
    pr.clip(pid, 0, 0, NOTE_BARS * len(keys))
    flp = os.path.join(outdir, '_notes.flp')
    pr.save(flp)
    wav = flp[:-4] + '.wav'
    if os.path.exists(wav):
        os.remove(wav)
    close_fl()
    subprocess.run([FL_EXE, '/R', '/Ewav', flp], timeout=600)
    for _ in range(60):
        if os.path.exists(wav):
            break
        time.sleep(2)
    y, sr = sf.read(wav, always_2d=True)
    seg = int(NOTE_BARS * 2.0 * sr)  # 2 s per bar at 120 BPM
    for i, k in enumerate(keys):
        s = y[i * seg:(i + 1) * seg].mean(axis=1)
        sf.write(os.path.join(outdir, 'note_%d.wav' % k), s, sr, subtype='FLOAT')
        print('key %d  peak %.3f  len %.2fs' % (k, np.abs(s).max(), len(s) / sr))


if __name__ == '__main__':
    render(sys.argv[1], sys.argv[2], [int(k) for k in sys.argv[3:]])
