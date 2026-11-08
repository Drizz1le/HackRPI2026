"""'Cry of a Dreamer' - College Dropout era chipmunk-soul flip of The Sylvers' "Cry of a Dreamer" (1972).

Source D major ~76 BPM -> coupled resample +4 st = F# major, 96 BPM (tools/prepare.py).
College Dropout drums (Through the Wire / Slow Jamz / Get Em High), sample up front.
Layers play roots + fifths only: the sample carries the thirds (no major/minor clashes).

  Intro 0-3 | Verse 4-19 | Prehook 20-23 | Hook 24-31 | Verse 32-47 | Prehook 48-51 | Hook 52-59
  | Breakdown 60-63 (no drums) | Final hook 64-71 | Coda 72-79   (80 bars, 3:20)
"""
import json, os, random
import numpy as np, soundfile as sf
from flpbuild import Project, preset, BAR

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.expanduser('~') + r'\Documents\FLStudio'
CD = KIT + r'\Kanye West - The College Dropout (Drum Kit)'
MAN = json.load(open(os.path.join(ROOT, 'chops', 'flip', 'manifest.json')))
LOOP = json.load(open(os.path.join(ROOT, 'chops', 'loops', 'manifest.json')))
CH = {k: v['file'] for k, v in MAN['chops'].items()}
S = 24  # 16th in ticks (PPQ 96)
BPM = MAN['bpm']
random.seed(11)
PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
NAMES = list(PC)


def bass_key(pc):  # E1..D#2: 41-78 Hz fundamentals
    return 28 + (PC[pc] - 4) % 12


def chop_harmony(name):
    """Per bar [root on beat 1, root on beat 3] from the source bass stem (pyin, transposed): the 808
    follows what the record's bassist actually played."""
    notes, last, out = MAN['bass'][name], 'F#', []
    for b in range(0, len(notes), 4):
        roots = []
        for k in (b, b + 2):
            if notes[k] is not None:
                last = NAMES[notes[k] % 12]
            roots.append(last)
        out.append(roots if roots[0] != roots[1] else roots[:1])
    return out


def variant(name, kind):
    src = CH[name]
    dst = src.replace('.wav', '_%s.wav' % kind)
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        from scipy.signal import butter, sosfilt
        y, sr = sf.read(src, always_2d=True)
        if kind == 'lpf':    # intro / breakdown: "through the wall"
            y = sosfilt(butter(4, 700, 'low', fs=sr, output='sos'), y, axis=0) * 1.6
        elif kind == 'tel':  # coda vocal: band-limited and driven
            y = sosfilt(butter(2, [300, 4000], 'band', fs=sr, output='sos'), y, axis=0)
            y = np.tanh(y * 6.0) * 0.5
        sf.write(dst, y, sr, subtype='PCM_24')
    return dst


def detect_root(path):
    import librosa
    y, sr = librosa.load(path, sr=22050, duration=1.0)
    f0, v, _ = librosa.pyin(y, fmin=30, fmax=200, sr=sr)
    f = np.nanmedian(f0[v]) if np.any(v) else 55.0
    return int(round(librosa.hz_to_midi(f)))


def build(out):
    pr = Project(tempo=BPM)
    smp = lambda name, path: pr.sampler(name, path)
    G = lambda rel: preset('Generators', rel)

    c = {}
    c['kick'] = smp('Kick (Through The Wire)', CD + r'\Kick\Kick - Through The Wire.wav')
    c['kick2'] = smp('Kick layer (Jesus Walks)', CD + r'\Kick\Kick - Jesus Walks.wav')
    c['snare'] = smp('Snare (Through The Wire)', CD + r'\Snare\Snare - Through The Wire.wav')
    c['snare2'] = smp('Snare layer (Jesus Walks)', CD + r'\Snare\Snare - Jesus Walks.wav')
    c['clap'] = smp('Clap (Slow Jamz)', CD + r'\Clap\Clap - Slow Jamz.wav')
    c['hat'] = smp('Hat (Through The Wire)', CD + r'\Hi Hat\Hi Hat - Through The Wire.wav')
    c['ohat'] = smp('Open hat (We Dont Care)', CD + r"\Perc\OH - We Don't Care.wav")
    c['crash'] = smp('Crash (Devil)', KIT + r'\MBDTF Drum Kit\Hats\Crash (Devil In A New Dress).wav')
    c['shaker'] = smp('Shaker (Get Em High)', CD + r'\Perc\Shaker - Get Em High.wav')
    c['bongo'] = smp('Bongos (Slow Jamz)', CD + r'\Perc\Bongos - Slow Jamz.wav')
    c['brk'] = smp('Break (Bad Kick)', LOOP['break']['file'])
    c['perc'] = smp('Perc loop (Night Stay)', LOOP['perc']['file'])
    p808 = KIT + r'\Dope Tec\-808s & Bass\[808] Clean.wav'
    c['808'] = smp('808', p808)
    for k in ('loopA', 'hookA', 'hookB', 'prehook', 'vamp'):
        c[k] = smp('chop ' + k, CH[k])
    c['loopA_lpf'] = smp('chop loopA lpf', variant('loopA', 'lpf'))
    for k in ('vox_dream', 'vox_ever', 'vox_lives', 'vox_aside'):
        c[k] = smp(k, CH[k])
    c['ever_tel'] = smp('forever tel', variant('vox_ever', 'tel'))
    c['piano'] = pr.plugin('Piano', G(r'FL Keys\Concert Piano.fst'))
    c['lowstr'] = pr.plugin('Low strings', G(r'Kepler Exo\X Saif Sameer\Strings\LowStrings.fst'))
    c['choir'] = pr.plugin('Choir', G(r'Kepler\Pads\Choir 1.fst'))
    c['brass'] = pr.plugin('Brass stab', G(r'Kepler Exo\X Saif Sameer\Brasses\Big Brass.fst'))
    c['spic'] = pr.plugin('Spiccato strings', G(r'Kepler Exo\X Sako\Instrument\Strings\String Spiccato.fst'))
    c['bells'] = pr.plugin('Bells', G(r'Harmless\Percussion\Church Bells 1 FG.fst'))

    r808 = detect_root(p808)
    k808 = lambda pc: 60 + (bass_key(pc) - r808)

    notes = []

    def n(ch, bar, step, len16, key=60, vel=100, pan=64):
        notes.append((c[ch], int(bar * BAR + step * S), int(len16 * S), key, vel, pan))

    H = {k: chop_harmony(k) for k in ('loopA', 'hookA', 'hookB', 'prehook', 'vamp')}
    H['loopA_lpf'] = H['loopA']
    harmony = {}

    def lay(name, bar, times):
        ln = len(H[name])
        for t in range(times):
            n(name, bar + t * ln, 0, MAN['chops'].get(name, MAN['chops']['loopA'])['beats'] * 4)
            for i, roots in enumerate(H[name]):
                harmony[bar + t * ln + i] = roots

    def drums(bar, style='verse'):
        # College Dropout bounce: kick on 1, the "and" of 2, 3-e; snare+clap 2 and 4
        kicks = {'verse': [0, 6, 10], 'verse2': [0, 6, 10, 15], 'hook': [0, 3, 6, 10, 11], 'pre': [0, 8]}[style]
        for s in kicks:
            n('kick', bar, s, 2, vel=120 if s == 0 else 106)
            if s in (0, 10):
                n('kick2', bar, s, 2, vel=84)
        for s in (4, 12):
            n('snare', bar, s, 2, vel=122)
            n('snare2', bar, s, 2, vel=84)
            n('clap', bar, s, 2, vel=110 if style == 'hook' else 86)
        hats = range(16) if style == 'hook' else range(0, 16, 2)
        for s in hats:
            sw = 0.2 if s % 2 else 0.0  # MPC-ish swing on the off-16ths
            n('hat', bar, s + sw, 1, vel=(106 if s % 4 == 0 else 86 if s % 2 == 0 else 64) + random.randint(-6, 6), pan=74)
        if style == 'hook':
            n('ohat', bar, 14, 2, vel=78, pan=54)
            if bar % 4 == 3:
                for k in range(8):
                    n('hat', bar, 12 + k * 0.5, 0.5, vel=58 + k * 7, pan=74)
        if style != 'pre':
            for s in (7, 15):
                n('hat', bar, s + 0.2, 1, vel=56 + random.randint(-4, 4), pan=74)
        if bar % 4 == 3:
            n('snare', bar, 15, 1, vel=60)

    def groove(bar, level='verse'):
        if bar % 2 == 0:
            n('brk', bar, 0, 32, vel=100 if level == 'hook' else 86)
        for s in range(0, 16, 2):
            n('shaker', bar, s + 1.2, 1, vel=70 + random.randint(-6, 6), pan=40)
        if level == 'hook':
            if bar % 4 == 0:
                n('perc', bar, 0, 64, vel=82)
            for s, v in ((3, 88), (6, 80), (11, 92), (14, 84)):
                n('bongo', bar, s, 2, vel=v, pan=86)

    def sub808(bar, groove=None):
        roots = harmony.get(bar)
        if not roots:
            return
        if groove:
            lens = {0: 5, 3: 3, 6: 3, 10: 5, 11: 2, 15: 1}
            for s in groove:
                pc = roots[0] if (len(roots) == 1 or s < 8) else roots[1]
                n('808', bar, s, lens.get(s, 3), key=k808(pc), vel=106)
            return
        n('808', bar, 0, 8 if len(roots) > 1 else 15, key=k808(roots[0]), vel=110)
        if len(roots) > 1:
            n('808', bar, 8, 7, key=k808(roots[1]), vel=104)

    def fifths(ch, bar, base, vel):
        roots = harmony.get(bar, [])
        for i, pc in enumerate(roots):
            span = 16 // len(roots)
            r = base + (PC[pc] - base) % 12
            for k in (r, r + 7, r + 12):
                n(ch, bar, i * span, span, key=k, vel=vel)

    def motion(bar, vel=72):  # spiccato 8ths on root/fifth/octave: movement without thirds
        roots = harmony.get(bar)
        if not roots:
            return
        for i in range(8):
            pc = roots[0] if (len(roots) == 1 or i < 4) else roots[1]
            r = 60 + (PC[pc] - 60) % 12
            n('spic', bar, i * 2, 2, key=[r, r + 7, r + 12, r + 7][i % 4], vel=vel + (8 if i % 2 == 0 else 0))

    def stab(bar):
        pc = harmony.get(bar, ['F#'])[0]
        r = 48 + (PC[pc] - 48) % 12
        for k in (r, r + 7, r + 12, r + 19):
            n('brass', bar, 0, 3, key=k, vel=118)
        n('crash', bar, 0, 8, vel=108)

    def bell(bar):
        pc = harmony.get(bar, ['F#'])[0]
        r = 72 + (PC[pc] - 72) % 12
        for k in (r, r + 7):
            n('bells', bar, 0, 8, key=k, vel=80)

    def hook(bar, a, b, big=False):
        lay(a, bar, 1)
        lay(b, bar + 4, 1)
        for x in range(bar, bar + 8):
            drums(x, 'hook')
            groove(x, 'hook')
            sub808(x)
            motion(x, 80 if big else 72)
            fifths('choir', x, 60, 70 if big else 62)
            fifths('lowstr', x, 42, 84 if big else 76)
        for x in (bar, bar + 4) if not big else (bar, bar + 2, bar + 4, bar + 6):
            stab(x)
            bell(x)

    def prehook(bar):
        lay('prehook', bar, 1)
        for x in range(bar, bar + 4):
            drums(x, 'pre')
            groove(x)
            sub808(x)
            fifths('lowstr', x, 42, 70 + 4 * (x - bar))  # strings swell into the hook
        for k in range(16):  # snare build on the last bar
            n('snare', bar + 3, k, 1, vel=50 + k * 4)

    # ---------------- arrangement ----------------
    lay('loopA_lpf', 0, 1)  # intro: muffled sample, piano roots, "forever" a cappella tail
    for bar in range(4):
        r = 66 + (PC[harmony[bar][0]] - 66) % 12
        n('piano', bar, 0, 8, key=r, vel=88)
        n('piano', bar, 8, 8, key=r + 7, vel=76)
    n('vox_ever', 3, 0, 16, vel=96)

    lay('loopA', 4, 4)  # verse 1
    for bar in range(4, 20):
        drums(bar, 'verse')
        groove(bar)
        sub808(bar, (0, 6, 10))
        if bar % 4 == 3:
            n('vox_dream', bar, 8, 8, vel=104)  # offbeat "dreamer" stab every 4th bar
    stab(4)

    prehook(20)
    hook(24, 'hookA', 'hookB')

    lay('loopA', 32, 4)  # verse 2
    for bar in range(32, 48):
        drums(bar, 'verse2')
        groove(bar)
        sub808(bar, (0, 6, 10, 15))
        if bar >= 40:
            motion(bar, 62)
        if bar % 4 == 3:
            n('vox_lives' if bar % 8 == 3 else 'vox_aside', bar, 0 if bar % 8 == 3 else 8, 16 if bar % 8 == 3 else 8, vel=100)
    stab(32)

    prehook(48)
    hook(52, 'hookB', 'hookA')

    lay('loopA_lpf', 60, 1)  # breakdown: drums out, piano chords on the roots, strings
    for bar in range(60, 64):
        for beat in range(4):
            for pc in harmony[bar][:1] if beat < 2 else harmony[bar][-1:]:
                r = 60 + (PC[pc] - 60) % 12
                for k in (r, r + 7, r + 12):
                    n('piano', bar, beat * 4, 3, key=k, vel=84 - beat * 4)
        fifths('lowstr', bar, 42, 82)
    n('vox_ever', 63, 0, 16, vel=100)

    hook(64, 'hookA', 'hookB', big=True)

    lay('vamp', 72, 4)  # coda: outro vamp, drums out at 76, telephone "forever"
    for bar in range(72, 80):
        if bar < 76:
            drums(bar, 'hook')
            groove(bar, 'hook')
            sub808(bar)
        fifths('lowstr', bar, 42, 80 - 2 * (bar - 72))
        if bar % 2 == 1:
            n('ever_tel', bar, 0, 16, vel=94)
    n('piano', 79, 0, 16, key=66, vel=70)

    only = os.environ.get('ONLY')
    if only:
        keep = {c[k] for k in only.split(',')}
        notes[:] = [x for x in notes if x[0] in keep]

    by_block = {}
    for note in notes:
        blk = note[1] // (4 * BAR)
        by_block.setdefault(blk, []).append((note[0], note[1] - blk * 4 * BAR) + note[2:])
    sections = {0: 'Intro', 1: 'Verse 1', 5: 'Prehook', 6: 'Hook 1', 8: 'Verse 2', 12: 'Prehook', 13: 'Hook 2',
                15: 'Breakdown', 16: 'Final Hook', 18: 'Coda'}
    name = 'Intro'
    for blk in range(20):
        name = sections.get(blk, name)
        pid = pr.pattern('%s %d' % (name, blk + 1), by_block.get(blk, []))
        pr.clip(pid, blk * 4, 0, 4)

    # same insert layout as Saw the Light, so mix.py's knob map applies unchanged
    E = lambda rel: preset('Effects', rel)
    fx = {
        1: ['Fruity Parametric EQ 2\\Kick.fst', 'Fruity Limiter\\For drums (slight saturation).fst'],
        2: ['Fruity Parametric EQ 2\\Tight Drum Sizzle.fst', 'Fruity Limiter\\Drum compression.fst', 'LuxeVerb\\Live Drum Room.fst'],
        3: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Damped Drum Room.fst'],
        4: ['Fruity Parametric EQ 2\\40Hz + 18kHz cut.fst', 'Fruity Blood Overdrive\\Drive.fst', 'Fruity Compressor\\Vintage.fst'],
        5: ['Fruity Parametric EQ 2\\Vocal Presence.fst', 'Fruity Delay 3\\Tape.fst', 'LuxeVerb\\Vocal Plate 1.fst'],
        6: ['Fruity Soft Clipper\\Default.fst', 'Fruity Compressor\\Leveler 1.fst'],
        7: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Lush Pad Hall.fst'],
        8: ['LuxeVerb\\Large Wood Room.fst'],
        9: ['Fruity Blood Overdrive\\Drive.fst', 'Fruity Reeverb 2\\Large Hall.fst'],
        10: ['Fruity Blood Overdrive\\Drive.fst', 'Fruity Delay 3\\Ping pong.fst', 'LuxeVerb\\Bright Hall.fst'],
        11: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'Fruity Compressor\\Drums.fst', 'LuxeVerb\\Damped Drum Room.fst'],
        12: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Lush Pad Hall.fst'],
        0: ['Fruity Parametric EQ 2\\Default.fst', 'Maximus\\Slight warmness.fst', 'Fruity Soft Clipper\\Default.fst', 'Fruity Limiter\\Max loudness (slight saturation).fst'],
    }
    for ins, chain in fx.items():
        for slot, rel in enumerate(chain):
            pr.effect(ins, slot, E(rel))

    route = {1: ['kick', 'kick2', '808'], 2: ['snare', 'snare2', 'clap'], 3: ['hat', 'ohat', 'crash'],
             4: ['loopA', 'loopA_lpf', 'hookA', 'hookB', 'prehook', 'vamp'],
             5: ['vox_dream', 'vox_ever', 'vox_lives', 'vox_aside', 'ever_tel'],
             6: [], 7: ['lowstr', 'choir'], 8: ['piano'], 9: ['brass'], 10: [],
             11: ['brk', 'perc', 'shaker', 'bongo'], 12: ['spic', 'bells']}
    json.dump({'route': {ins: [c[k] for k in ks] for ins, ks in route.items()},
               'names': {1: 'Kick+808', 2: 'Snare/Clap', 3: 'Hats', 4: 'Sample', 5: 'Vox chops', 6: '-',
                         7: 'Strings/Choir', 8: 'Piano', 9: 'Brass', 10: '-', 11: 'Groove', 12: 'Layers'},
               'channels': c, 'bars': 80, 'bpm': BPM},
              open(os.path.splitext(out)[0] + '.mix.json', 'w'), indent=1)
    pr.save(out)
    print('built', out, '-', len(pr.channels), 'channels,', len(notes), 'notes,', len(pr.patterns), 'patterns')
    print('harmony:', {k: v for k, v in H.items()})


if __name__ == '__main__':
    import sys
    os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'out', 'Cry of a Dreamer.flp'))
