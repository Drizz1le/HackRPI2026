"""Drum/percussion loops for the groove layer (the Runaway move: a live break under the programmed kick
and reverbed clap). Each loop is exactly N bars at its tagged tempo, so it is stretched (no pitch
change, Rubber Band R2) to exactly N bars at the song tempo -> grid-locked."""
import json, os, subprocess, sys
import soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prepare import RUBBERBAND, BPM

KIT = os.path.expanduser('~') + r'\Documents\FLStudio\Dope Tec'
LOOPS = {  # name: (file, bars) - Cry of a Dreamer: closer to 96 BPM, less stretch
    'break': (KIT + r'\~Drum Loops\Breaks\[100] Bad Kick.wav', 2),
    'perc': (KIT + r'\~Perc Loops\[92] Night Stay.wav', 4),
}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'chops', 'loops')


def main():
    os.makedirs(OUT, exist_ok=True)
    man = {}
    for name, (src, bars) in LOOPS.items():
        dst = os.path.join(OUT, name + '.wav')
        secs = bars * 4 * 60.0 / BPM
        subprocess.run([RUBBERBAND, '-q', '-D', '%.6f' % secs, src, dst], check=True, capture_output=True)
        y, sr = sf.read(dst, always_2d=True)
        man[name] = {'file': dst, 'bars': bars}
        print('%-15s %d bars -> %.3fs (got %.3fs)' % (name, bars, secs, len(y) / sr))
    json.dump(man, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
