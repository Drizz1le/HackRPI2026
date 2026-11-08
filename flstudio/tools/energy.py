"""What makes a beat 'move'? Measure tempo, hit density, percussive share and loudness of reference
instrumentals vs ours.
usage: python tools/energy.py OURS.wav ..."""
import os, sys
import numpy as np, librosa

GAJ = os.path.expanduser('~') + r'\Downloads\PASTELLE COLLECTIVE - GOOD ASS JOB\PASTELLE TEAM - GOOD ASS JOB\INSTS' + '\\'
REFS = {'Flashing Lights 2': GAJ + '06. Flashing Lights 2.mp3', 'Hard Horn Nightmare': GAJ + '01. Hard Horn Nightmare.mp3',
        'Mamas Boyfriend': GAJ + '08. Mamas Boyfriend.mp3', "That's My Bitch": GAJ + "03. That's My Bitch.mp3",
        'Eyes Closed': GAJ + '11. Eyes Closed.mp3'}


def energy(path, offset=40, duration=60):
    y, sr = librosa.load(path, sr=22050, offset=offset, duration=duration)
    tempo = float(np.atleast_1d(librosa.beat.beat_track(y=y, sr=sr)[0])[0])
    h, p = librosa.effects.hpss(y)
    on_all = librosa.onset.onset_detect(y=y, sr=sr, units='time')
    hi = librosa.onset.onset_strength(y=y, sr=sr, fmin=4000) if False else None
    S = np.abs(librosa.stft(p))
    f = librosa.fft_frequencies(sr=sr)
    hi_env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[f > 5000]), sr=sr)
    hi_on = librosa.onset.onset_detect(onset_envelope=hi_env, sr=sr, units='time')
    lo_env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[f < 150]), sr=sr)
    lo_on = librosa.onset.onset_detect(onset_envelope=lo_env, sr=sr, units='time')
    perc_share = 100 * (p ** 2).sum() / ((p ** 2).sum() + (h ** 2).sum())
    rms = 10 * np.log10((y ** 2).mean())
    return tempo, len(on_all) / duration, len(hi_on) / duration, len(lo_on) / duration, perc_share, rms


if __name__ == '__main__':
    rows = {k: energy(p) for k, p in REFS.items()}
    for p in sys.argv[1:]:
        rows['OURS ' + p.replace('\\', '/').split('/')[-1][:16]] = energy(p, offset=25)
    print('%-22s %6s %10s %12s %12s %8s %7s' % ('', 'bpm', 'hits/s', 'hi hits/s', 'low hits/s', 'perc %', 'rms'))
    for k, (t, a, h, l, pc, r) in rows.items():
        print('%-22s %6.1f %10.2f %12.2f %12.2f %7.1f%% %6.1f' % (k, t, a, h, l, pc, r))
