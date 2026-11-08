"""Compare a render's spectral balance and crest factor with real Kanye records on disk.
usage: python tools/compare.py OURS.wav"""
import os, sys
import numpy as np, librosa

REFS = {'Runaway': os.path.expanduser('~') + r'\Downloads\ogs\6. MBDTF\Runaway.mp3',
        'Power (remix)': os.path.expanduser('~') + r'\Downloads\ogs\6. MBDTF\POWER (Remix).mp3',
        'Blame Game': os.path.expanduser('~') + r'\Downloads\ogs\6. MBDTF\Blame Game (No Chris Rock Skit).mp3',
        'Flashing Lights 2': os.path.expanduser('~') + r'\Downloads\ogs\4. Good Ass Job\Flashing Lights 2.mp3',
        'Homecoming': os.path.expanduser('~') + r'\Downloads\ogs\3. Graduation\Homecoming.wav'}
GAJ = os.path.expanduser('~') + r'\Downloads\PASTELLE COLLECTIVE - GOOD ASS JOB\PASTELLE TEAM - GOOD ASS JOB\INSTS'
for _n in ('01. Hard Horn Nightmare', '02. Sweat On My Face', '03. That\'s My Bitch', '08. Mamas Boyfriend', '15. Never See Me Again'):
    REFS['GAJ inst ' + _n[4:18]] = GAJ + '\\' + _n + '.mp3'  # instrumentals: best A/B for an instrumental
BANDS = [(20, 60), (60, 120), (120, 250), (250, 1000), (1000, 4000), (4000, 12000)]


def profile(path, offset=30, duration=90):
    y, sr = librosa.load(path, sr=44100, mono=True, offset=offset, duration=duration)
    P = (np.abs(librosa.stft(y, n_fft=8192)) ** 2).mean(1)
    f = librosa.fft_frequencies(sr=sr, n_fft=8192)
    bands = [100 * P[(f >= a) & (f < b)].sum() / P.sum() for a, b in BANDS]
    return bands + [20 * np.log10(np.abs(y).max() / np.sqrt((y ** 2).mean()))]


if __name__ == '__main__':
    rows = {k: profile(p) for k, p in REFS.items()}
    ref = np.array(list(rows.values()))
    rows['-> Kanye median'] = list(np.median(ref, 0))
    for p in sys.argv[1:]:
        rows['OURS ' + p.split('\\')[-1].split('/')[-1][:14]] = profile(p)
    print('%-22s' % '' + ''.join('%9s' % ('%d-%d' % b) for b in BANDS) + '   crest')
    for k, v in rows.items():
        print('%-22s' % k + ''.join('%8.1f%%' % x for x in v[:-1]) + '  %5.1f dB' % v[-1])
