"""'Black Gold' - MBDTF / Good Ass Job style rechop of Rotary Connection's "I Am the Black Gold of the Sun"
(1971, Charles Stepney / Minnie Riperton) with a Mike Dean style guitar solo (Devil in a New Dress move).

88 BPM, G# minor (source key). The chop (tools/chop.py): the record's rubato orchestral intro sliced into
chord swells and rebuilt on the grid:
  verse  G#m | E | C#m | D#7   (i VI iv V)  sustained swells
  hook   G#m | A | B7  | D#7   (i bII III V) MPC re-triggered 3-3-2, reversed swells into each phrase
Minnie's bridge lines on top ("I'm the black gold of the sun"). Solo: tools/solo.py.

  Intro 0-3 | Verse 4-19 | Hook 20-27 | Verse 28-43 | Hook 44-51 | Solo 52-67 (drums out until 60)
  | Final hook 68-75 | Outro 76-83      (84 bars, 3:49)
"""
import json, os, random
import numpy as np
from flpbuild import Project, preset, BAR

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.expanduser('~') + r'\Documents\FLStudio'
MB = KIT + r'\MBDTF Drum Kit'
MAN = json.load(open(os.path.join(ROOT, 'chops', 'flip', 'manifest.json')))
LOOP = json.load(open(os.path.join(ROOT, 'chops', 'loops', 'manifest.json')))
S = 24  # 16th in ticks
BPM = MAN['bpm']
random.seed(23)
PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
VERSE = ['G#m', 'E', 'C#m', 'D#7']
HOOK = ['G#m', 'A', 'B7', 'D#7']
root = lambda chord: chord.rstrip('m7')


def bass_key(pc):  # E1..D#2
    return 28 + (PC[pc] - 4) % 12


def detect_root(path):
    import librosa
    y, sr = librosa.load(path, sr=22050, duration=1.0)
    f0, v, _ = librosa.pyin(y, fmin=30, fmax=200, sr=sr)
    return int(round(librosa.hz_to_midi(np.nanmedian(f0[v]) if np.any(v) else 55.0)))


def build(out):
    pr = Project(tempo=BPM)
    smp = lambda name, path: pr.sampler(name, path)
    G = lambda rel: preset('Generators', rel)
    c = {}
    c['kick'] = smp('Kick (Devil)', MB + r'\Kicks\Kick (Devil In A New Dress).wav')
    c['snare'] = smp('Snare (Devil)', MB + r'\Snares\Snare (Devil In A New Dress).wav')
    c['snare2'] = smp('Snare layer (Power)', MB + r'\Snares\Layer Snare (Power).wav')
    c['clap'] = smp('Clap (Power)', MB + r'\Claps\Clap (Power).wav')
    c['hat'] = smp('Hat (Devil)', MB + r'\Hats\Closed Hat (Devil In A New Dress).wav')
    c['ohat'] = smp('Open hat (Devil)', MB + r'\Hats\Open Hat (Devil In A New Dress).wav')
    c['crash'] = smp('Crash (Devil)', MB + r'\Hats\Crash (Devil In A New Dress).wav')
    c['bigdrum'] = smp('Big drum (Lost)', MB + r'\Percussion\Big Drum (Lost In The World).wav')
    c['bigdrum2'] = smp('Big drum 2 (Lost)', MB + r'\Percussion\Big Drum 2 (Lost In The World).wav')
    c['tom'] = smp('Tom (Devil)', MB + r'\Percussion\Tom (Devil In A New Dress).wav')
    c['brk'] = smp('Break (Right Wing)', LOOP['break']['file'])
    c['perc'] = smp('Perc loop (Grown)', LOOP['perc']['file'])
    p808 = KIT + r'\Dope Tec\-808s & Bass\[808] Clean.wav'
    c['808'] = smp('808', p808)
    for ch, files in MAN['chords'].items():
        for kind, f in files.items():
            c['%s_%s' % (ch, kind)] = smp('%s %s' % (ch, kind), f)
    for k, v in MAN['vox'].items():
        c[k] = smp(k, v['file'])
    c['solo'] = smp('Guitar solo (Dean)', os.path.join(ROOT, 'chops', 'flip', 'solo.wav'))
    c['lowstr'] = pr.plugin('Low strings', G(r'Kepler Exo\X Saif Sameer\Strings\LowStrings.fst'))
    c['choir'] = pr.plugin('Choir', G(r'Kepler\Pads\Choir 1.fst'))
    c['brass'] = pr.plugin('Brass stab', G(r'Kepler Exo\X Saif Sameer\Brasses\Big Brass.fst'))

    r808 = detect_root(p808)
    k808 = lambda pc: 60 + (bass_key(pc) - r808)
    notes = []
    chord_at = {}

    def n(ch, bar, step, len16, key=60, vel=100, pan=64):
        notes.append((c[ch], int(bar * BAR + step * S), int(len16 * S), key, vel, pan))

    def chords(bar, prog, kind='sus', times=1, vel=100):
        for t in range(times):
            for i, ch in enumerate(prog):
                b = bar + 4 * t + i
                n('%s_%s' % (ch, kind), b, 0, 16, vel=vel)
                chord_at[b] = ch
            # reversed swell of the phrase's first chord sucks into the next phrase
            n('%s_rev' % prog[0], bar + 4 * t + 3, 12, 4, vel=vel - 10)

    def drums(bar, style='verse', fill=False):
        kicks = {'verse': [0, 7, 10], 'verse2': [0, 7, 10, 14], 'hook': [0, 3, 7, 10]}[style]
        for s in kicks:
            n('kick', bar, s, 2, vel=118 if s == 0 else 104)
        for s in (4, 12):
            n('snare', bar, s, 2, vel=120)
            n('snare2', bar, s, 2, vel=88)
            n('clap', bar, s, 2, vel=112 if style == 'hook' else 80)
        for s in (range(16) if style == 'hook' else range(0, 16, 2)):
            sw = 0.17 if s % 2 else 0.0
            n('hat', bar, s + sw, 1, vel=(104 if s % 4 == 0 else 84 if s % 2 == 0 else 60) + random.randint(-6, 6), pan=74)
        if style == 'hook':
            n('ohat', bar, 14, 2, vel=78, pan=54)
            for s, d, v in ((6, 'bigdrum2', 94), (11, 'bigdrum', 86), (14, 'bigdrum2', 90)):  # Lost in the World
                n(d, bar, s, 2, vel=v, pan=58 if d == 'bigdrum' else 70)
        else:
            for s in (7, 15):
                n('hat', bar, s + 0.17, 1, vel=56 + random.randint(-4, 4), pan=74)
        if bar % 4 == 3:
            n('snare', bar, 15, 1, vel=58)
        if fill:
            for i, s in enumerate((8, 10, 12, 14)):
                n('tom', bar, s, 2, key=62 - 3 * i, vel=104)

    def groove(bar, hook=False):
        if bar % 2 == 0:
            n('brk', bar, 0, 32, vel=100 if hook else 86)
            if hook:
                n('perc', bar, 0, 32, vel=80)

    def sub808(bar, groove=None):
        ch = chord_at.get(bar)
        if not ch:
            return
        k = k808(root(ch))
        if groove:
            for s in groove:
                n('808', bar, s, {0: 5, 7: 3, 10: 5, 14: 2}.get(s, 3), key=k, vel=106)
        else:
            n('808', bar, 0, 15, key=k, vel=110)

    def fifths(ch, bar, base, vel):
        if bar in chord_at:
            r = base + (PC[root(chord_at[bar])] - base) % 12
            for k in (r, r + 7, r + 12):
                n(ch, bar, 0, 16, key=k, vel=vel)

    def stab(bar):
        r = 48 + (PC[root(chord_at.get(bar, 'G#m'))] - 48) % 12
        for k in (r, r + 7, r + 12, r + 19):
            n('brass', bar, 0, 3, key=k, vel=118)
        n('crash', bar, 0, 8, vel=108)

    def hook(bar, big=False):
        chords(bar, HOOK, 'chop', 2)
        for x in range(bar, bar + 8):
            drums(x, 'hook')
            groove(x, True)
            sub808(x)
            fifths('lowstr', x, 42, 84 if big else 76)
            if big:
                fifths('choir', x, 60, 66)
        n('vox_gold', bar, 0, 24, vel=110)       # "I'm the black gold of the sun" over G#m -> A
        n('vox_free', bar + 2, 0, 24, vel=100)   # "I am a man so free" over B7 -> D#7
        n('vox_gold', bar + 4, 0, 24, vel=110)
        n('vox_free' if not big else 'vox_sea', bar + 6, 0, 24, vel=100)
        for x in ((bar, bar + 4) if not big else (bar, bar + 2, bar + 4, bar + 6)):
            stab(x)

    def verse(bar, style):
        chords(bar, VERSE, 'sus', 4)
        for x in range(bar, bar + 16):
            drums(x, style, fill=(x == bar + 15))
            groove(x)
            sub808(x, (0, 7, 10) if style == 'verse' else (0, 7, 10, 14))
            if x % 4 == 1 and x % 8 == 5:
                n('vox_smile', x, 4, 12, vel=96)   # "smiling on everyone" over E (B G# F# = 5, 3, 9)

    # ---------------- arrangement ----------------
    chords(0, HOOK, 'sus')                      # intro: the orchestra alone, then Minnie
    n('vox_gold', 2, 0, 24, vel=104)
    for bar in (2, 3):
        n('bigdrum', bar, 0, 4, vel=116)
        n('bigdrum', bar, 8, 4, vel=104)
    verse(4, 'verse')
    stab(4)
    hook(20)
    verse(28, 'verse2')
    stab(28)
    hook(44)
    # solo: Devil in a New Dress - drums drop, the swells and the guitar; drums slam back at 60
    chords(52, HOOK, 'sus', 2)
    chords(60, HOOK, 'chop', 2)
    n('solo', 52, 0, 17 * 16, vel=100)
    for x in range(52, 68):
        fifths('lowstr', x, 42, 82)
        sub808(x)
        if x >= 60:
            drums(x, 'hook', fill=(x == 67))
            groove(x, True)
        elif x >= 56:
            for s in (4, 12):
                n('snare2', x, s, 2, vel=70)  # rim-ish pulse creeping back in
    stab(60)
    n('bigdrum', 60, 0, 4, vel=120)
    hook(68, big=True)
    chords(76, ['G#m', 'E', 'G#m', 'E'], 'sus', 2)  # outro: i - VI, Minnie, drums out at 80
    for x in range(76, 84):
        if x < 80:
            drums(x, 'verse')
            groove(x)
            sub808(x)
        fifths('lowstr', x, 42, 80 - 2 * (x - 76))
    n('vox_sea', 76, 0, 20, vel=100)
    n('vox_smile', 81, 4, 12, vel=96)
    n('vox_gold', 82, 0, 24, vel=92)

    only = os.environ.get('ONLY')
    if only:
        keep = {c[k] for k in only.split(',')}
        notes[:] = [x for x in notes if x[0] in keep]

    by_block = {}
    for note in notes:
        blk = note[1] // (4 * BAR)
        by_block.setdefault(blk, []).append((note[0], note[1] - blk * 4 * BAR) + note[2:])
    sections = {0: 'Intro', 1: 'Verse 1', 5: 'Hook 1', 7: 'Verse 2', 11: 'Hook 2', 13: 'Solo', 17: 'Final Hook', 19: 'Outro'}
    name = 'Intro'
    for blk in range(21):
        name = sections.get(blk, name)
        pid = pr.pattern('%s %d' % (name, blk + 1), by_block.get(blk, []))
        pr.clip(pid, blk * 4, 0, 4)

    E = lambda rel: preset('Effects', rel)
    fx = {
        1: ['Fruity Parametric EQ 2\\Kick.fst', 'Fruity Limiter\\For drums (slight saturation).fst'],
        2: ['Fruity Parametric EQ 2\\Tight Drum Sizzle.fst', 'Fruity Limiter\\Drum compression.fst', 'LuxeVerb\\Live Drum Room.fst'],
        3: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Damped Drum Room.fst'],
        4: ['Fruity Parametric EQ 2\\40Hz + 18kHz cut.fst', 'Fruity Blood Overdrive\\Drive.fst', 'Fruity Compressor\\Vintage.fst'],
        5: ['Fruity Parametric EQ 2\\Vocal Presence.fst', 'Fruity Delay 3\\Tape.fst', 'LuxeVerb\\Vocal Plate 1.fst'],
        6: ['Fruity Soft Clipper\\Default.fst', 'Fruity Compressor\\Leveler 1.fst'],
        7: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Lush Pad Hall.fst'],
        9: ['Fruity Blood Overdrive\\Drive.fst', 'Fruity Reeverb 2\\Large Hall.fst'],
        # guitar is already driven + cabbed offline (tools/solo.py): only space here
        10: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'Fruity Delay 3\\Ping pong.fst', 'LuxeVerb\\Bright Hall.fst'],
        11: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'Fruity Compressor\\Drums.fst', 'LuxeVerb\\Damped Drum Room.fst'],
        0: ['Fruity Parametric EQ 2\\Default.fst', 'Maximus\\Slight warmness.fst', 'Fruity Soft Clipper\\Default.fst', 'Fruity Limiter\\Max loudness (slight saturation).fst'],
    }
    for ins, chain in fx.items():
        for slot, rel in enumerate(chain):
            pr.effect(ins, slot, E(rel))

    chord_ch = [k for k in c if k.split('_')[-1] in ('sus', 'chop', 'rev')]
    route = {1: ['kick', '808'], 2: ['snare', 'snare2', 'clap'], 3: ['hat', 'ohat', 'crash', 'bigdrum', 'tom'],
             4: chord_ch, 5: list(MAN['vox']), 6: [], 7: ['lowstr', 'choir'], 8: [], 9: ['brass'], 10: ['solo'],
             11: ['brk', 'perc', 'bigdrum2'], 12: []}
    json.dump({'route': {ins: [c[k] for k in ks] for ins, ks in route.items()},
               'names': {1: 'Kick+808', 2: 'Snare/Clap', 3: 'Hats/Perc', 4: 'Sample chop', 5: 'Minnie', 6: '-',
                         7: 'Strings/Choir', 8: '-', 9: 'Brass', 10: 'Guitar (Dean)', 11: 'Groove', 12: '-'},
               'channels': c, 'bars': 84, 'bpm': BPM},
              open(os.path.splitext(out)[0] + '.mix.json', 'w'), indent=1)
    pr.save(out)
    print('built', out, '-', len(pr.channels), 'channels,', len(notes), 'notes,', len(pr.patterns), 'patterns')


if __name__ == '__main__':
    import sys
    os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'out', 'Black Gold.flp'))
