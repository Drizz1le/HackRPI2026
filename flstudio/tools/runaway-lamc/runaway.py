"""'Run Right Back' - a hopecore flip of Kanye's extended Runaway outro (LA Memorial Coliseum, Dec 2021):
"someday you're gonna run away ... I need you to run right back to me, baby ... more specifically,
Kimberly". The sample is the song: whole 8-bar cycles of the outro, coupled +4 st (E -> G#, 90 -> 114 BPM),
Fm C# G# D# (vi IV I V). Everything else runs under it: driving Runaway-kit drums + breaks, 32nd hat
rolls, 808, choir, 16th pluck arp, Runaway piano one-shot, supersaw/bells in the last drops, baked
spazz edits (stutters, gate, tape stop).

  Pre 0-1 | Intro 2-9 (beat-drop shout) | Drop A 10-25 | Break 26-33 | Build 34-37 | Drop B 38-53
  | Drop C 54-61 | Outro 62-67 ("more specifically, Kimberly")     68 bars at 114 = 2:23
"""
import json, os, random
import numpy as np
from flpbuild import Project, preset, BAR

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.expanduser('~') + r'\Documents\FLStudio'
MB = KIT + r'\MBDTF Drum Kit'
UZ = KIT + r'\Lil Uzi Vert Sample Pack 001'
MAN = json.load(open(os.path.join(ROOT, 'chops', 'flip', 'manifest.json')))
BPM = MAN['bpm']
S = BAR // 16  # 16th
random.seed(7)
PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
VOICE = {'Fm': [56, 60, 63, 65], 'C#': [56, 60, 61, 65], 'G#': [56, 60, 63, 68], 'D#': [55, 58, 63, 65]}
ROOTK = {'Fm': 29, 'C#': 37, 'G#': 32, 'D#': 39}  # 808 roots F1 C#2 G#1 D#2
CYCLE = ['Fm', 'Fm', 'C#', 'C#', 'G#', 'G#', 'D#', 'D#']


def detect_root(path):
    import librosa
    y, sr = librosa.load(path, sr=22050, duration=1.0)
    f0, v, _ = librosa.pyin(y, fmin=30, fmax=1200, sr=sr)
    return int(round(librosa.hz_to_midi(np.nanmedian(f0[v]) if np.any(v) else 60.0)))


def trimmed(path, db, name):
    """kit one-shot at a fixed gain (the Runaway kick is a full-scale sub thump: RMS 0.62, 88% < 60 Hz;
    in v1/v2 it was 13 dB over the whole sample and 72% of the drops' energy)."""
    import soundfile as sf
    dst = os.path.join(ROOT, 'chops', 'kit', name)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    y, sr = sf.read(path, always_2d=True)
    sf.write(dst, y * 10 ** (db / 20), sr, subtype='PCM_24')
    return dst


def build(out):
    pr = Project(tempo=BPM)
    smp = lambda name, path: pr.sampler(name, path)
    G = lambda rel: preset('Generators', rel)
    c = {}
    c['kick'] = smp('Kick (Runaway)', trimmed(MB + r'\Kicks\Kick (Runaway).wav', -14.0, 'kick_runaway_-14dB.wav'))
    c['kick2'] = smp('Kick (Uzi)', UZ + r'\One Shot\Kick 01.wav')
    c['snare'] = smp('Snare (Runaway)', MB + r'\Snares\Snare (Runaway).wav')
    c['clap'] = smp('Clap (Uzi)', UZ + r'\One Shot\Clap.wav')
    c['hat'] = smp('Hat (Uzi)', UZ + r'\One Shot\Hi Hat 01.wav')
    c['ohat'] = smp('Open hat (Uzi)', UZ + r'\One Shot\Open Hi Hat.wav')
    c['crash'] = smp('Crash (Devil)', MB + r'\Hats\Crash (Devil In A New Dress).wav')
    c['tom'] = smp('Tom (Devil)', MB + r'\Percussion\Tom (Devil In A New Dress).wav')
    c['bigdrum'] = smp('Big drum (Lost)', MB + r'\Percussion\Big Drum (Lost In The World).wav')
    c['riser'] = smp('Riser (BURN)', KIT + r'\BURN - Ye x Ty$\burn riser.wav')
    p808 = UZ + r'\Synth Sounds\808 C.wav'
    c['808'] = smp('808', p808)
    ppiano = MB + r'\Other\Piano (Runaway).wav'
    c['rpiano'] = smp('Runaway piano', ppiano)
    for k, v in MAN['chops'].items():
        c[k] = smp(k, v['file'])
    for k, f in MAN['fx'].items():
        c[k] = smp(k, f)
    for k, v in MAN['loops'].items():
        c[k] = smp(k, v['file'])
    c['choir'] = pr.plugin('Choir', G(r'Kepler\Pads\Choir 1.fst'))
    c['saw'] = pr.plugin('Supersaw', G(r'Harmless\X Nucleon\Lead\90 Supersaw.fst'))
    c['arp'] = pr.plugin('Pluck arp', G(r'Harmless\Keyboards\Dancer Pluck FG.fst'))
    c['bell'] = pr.plugin('Music box', G(r'Fruity DX10\Music Box.fst'))

    r808, rpn = detect_root(p808), detect_root(ppiano)
    notes = []
    harm = {}

    def n(ch, bar, step, ln=1, key=60, vel=100, pan=64, tick=0):  # 16th grid (+ tick offset for 32nds)
        notes.append((c[ch], int(bar * BAR + step * S + tick), max(1, int(ln * S)), key, vel, pan))

    def sample(name, bar, bars=None):
        n(name, bar, 0, 16 * (bars or MAN['chops'].get(name, {'beats': 32})['beats'] / 4))
        for k in range(bars or 8):
            harm[bar + k] = CYCLE[k % 8]

    def kick(bar, steps, vel=118):
        for s in steps:
            n('kick', bar, s, 1, vel=vel if s == 0 else vel - 10)
            n('kick2', bar, s, 1, vel=vel - 24)
            ch = harm.get(bar)
            if ch:  # 808 locked to the kick, rings to the next kick
                nxt = [t for t in steps if t > s]
                n('808', bar, s, (nxt[0] if nxt else 16) - s, key=60 + ROOTK[ch] - r808, vel=72)  # v2: v1 sub was 71% of the drops' energy

    def snare(bar, steps=(4, 12), vel=116):
        for s in steps:
            n('snare', bar, s, 1, vel=vel)
            n('clap', bar, s, 1, vel=vel - 14, pan=58)

    def hats(bar, roll=None, vel=88):
        for s in range(16):
            if roll is not None and s >= roll:
                continue
            n('hat', bar, s, 1, vel=(vel if s % 2 == 0 else vel - 22) + random.randint(-4, 4), pan=76)
        if roll is not None:  # spazz: 32nds from `roll`, last beat 6-tuplets
            for k in range((16 - roll) * 2):
                tk = roll * S + k * S // 2
                if tk >= 12 * S:
                    break
                notes.append((c['hat'], bar * BAR + tk, S // 2, 60 + (k % 4 == 3) * 2, 70 + k * 2, 76))
            for k in range(6):
                notes.append((c['hat'], bar * BAR + 12 * S + k * (4 * S) // 6, S // 2, 62 + k, 78 + 4 * k, 76))

    def pad(bar, vel=58):
        ch = harm.get(bar)
        if ch and (bar == 0 or harm.get(bar - 1) != ch):
            for k in VOICE[ch]:
                n('choir', bar, 0, 32, key=k, vel=vel)

    def arp(bar, vel=60, octave=12):
        ch = harm.get(bar)
        if not ch:
            return
        v = VOICE[ch] + [x + 12 for x in VOICE[ch]]
        seq = [0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1, 2, 3]
        for s in range(16):
            n('arp', bar, s, 1, key=v[seq[s]] + octave - 12, vel=vel + (12 if s % 4 == 0 else 0), pan=40 + 48 * (s % 2))

    def saws(bar, vel=70):
        ch = harm.get(bar)
        if ch:
            for s in (2, 6, 10, 14):  # offbeat 8ths: the run
                for k in VOICE[ch]:
                    n('saw', bar, s, 1.5, key=k + 12, vel=vel)

    def bells(bar, vel=76):  # hopecore top line: chord tones, 2 octaves up, dotted rhythm
        ch = harm.get(bar)
        if ch:
            v = VOICE[ch]
            for s_, k in ((0, v[3]), (6, v[2]), (10, v[1]), (14, v[2])):
                n('bell', bar, s_, 2, key=k + 24, vel=vel - (8 if s_ else 0))

    def rpiano(bar, steps=(0, 4, 8, 12), key=68, vel=100):  # the Runaway note (E -> G#)
        for s in steps:
            n('rpiano', bar, s, 4, key=60 + key - rpn, vel=vel)

    def drop(bar, length, big=False, spz_last=False, src=('cyc3', 'cyc4')):
        for i, name in enumerate(src):
            sample(name, bar + 8 * i)
        if spz_last:
            notes[:] = [x for x in notes if not (x[0] == c[src[-1]] and x[1] == (bar + 8 * (len(src) - 1)) * BAR)]
            sample('cyc4_spz', bar + 8 * (len(src) - 1))
        for x in range(bar, bar + length):
            i = x - bar
            kick(x, [0, 6, 10] if i % 2 == 0 else [0, 3, 6, 10, 13])
            snare(x)
            if i % 4 == 3:
                n('snare', x, 15, 1, vel=70)
            hats(x, roll=(12 if i % 2 == 1 else None) if not big else (12 if i % 2 == 1 else 14))
            if i % 2 == 0:
                n('break2' if big and i % 4 == 2 else 'break', x, 0, 32, vel=92)
            pad(x, 62 if big else 56)
            arp(x, 66 if big else 58)
            if big:
                saws(x)
                bells(x)
                if i % 8 == 7:
                    for k, s in enumerate((12, 13, 14, 15)):
                        n('tom', x, s, 1, key=72 - 4 * k, vel=104)
            if i % 8 == 0:
                n('crash', x, 0, 16, vel=108)
                n('bigdrum', x, 0, 4, vel=112)
        n('ohat', bar, 0, 4, vel=90)

    # ---------------- arrangement ----------------
    sample('pre', 0, 2)
    harm[0] = harm[1] = 'D#'
    rpiano(0, vel=96)
    rpiano(1, vel=100)
    pad(0, 52)
    sample('cyc1_cut', 2)
    for x in range(2, 10):
        pad(x, 54)
        rpiano(x, steps=(0, 8), vel=78)
        if x >= 4:
            arp(x, 44 + 2 * (x - 4))
        if x >= 6:
            for s in range(0, 16, 2):
                n('hat', x, s, 1, vel=60 + 3 * (x - 6), pan=76)
    for s in range(0, 16, 4):
        n('snare', 8, s, 1, vel=72 + s)
    for s in range(0, 4, 1):  # bar 9 beat 1 roll, then the hole for the shout
        n('snare', 9, s, 1, vel=96 + 4 * s)
    n('riser', 8, 0, 32, vel=100)
    n('hype', 9, 4, 12, vel=118)  # "when the beat drop, I need y'all to make some noise"
    n('rev_fm', 9, 12, 4, vel=110)

    drop(10, 16, spz_last=True)                 # Drop A: "they say one ... I need you to run back, back to me"

    sample('cyc2_tape', 26)                      # Break: "someday he's gonna make you run away"
    for x in range(26, 34):
        i = x - 26
        if i < 7:
            kick(x, [0, 10] if x >= 30 else [0])
            if x < 30:
                notes[:] = [z for z in notes if not (z[0] == c['808'] and z[1] // BAR == x)]
            snare(x, (8,), vel=110)
            for s in range(0, 16, 2):
                n('hat', x, s, 1, vel=70, pan=76)
            n('bigdrum', x, 0, 4, vel=100)
            n('bigdrum', x, 11, 4, vel=88)
        pad(x, 64)
        rpiano(x, steps=(0, 4, 8, 12), vel=84)
        if i >= 4:
            bells(x, 66)

    sample('gate4_run', 34, 4)                   # Build
    harm.update({34: 'Fm', 35: 'Fm', 36: 'C#', 37: 'C#'})
    for x, step in ((34, 4), (35, 2), (36, 1)):
        for s in range(0, 16, step):
            n('snare', x, s, 1, vel=80 + (x - 34) * 12 + s)
        pad(x, 60)
    for k in range(24):  # bar 37: 32nds for 3 beats, then the hole
        notes.append((c['snare'], 37 * BAR + k * S // 2, S // 2, 60 + k // 4, 90 + k, 64))
    n('riser', 36, 0, 32, vel=110)
    n('rev_fm', 37, 12, 4, vel=118)

    drop(38, 16, big=True)                       # Drop B
    drop(54, 8, big=True, src=('cyc4_spz',))     # Drop C: the plea one more time, everything on
    n('crash', 54, 0, 16, vel=118)

    sample('tail', 62, 6)                        # Outro: "... more specifically, Kimberly"
    harm.update({62: 'Fm', 63: 'Fm', 64: 'C#', 65: 'C#', 66: 'G#', 67: 'G#'})
    for x in range(62, 68):
        pad(x, 58 - 2 * (x - 62))
        if x < 64:
            kick(x, [0, 10])
            snare(x, (8,))
            hats(x)
        rpiano(x, steps=(0, 8), vel=80 - 3 * (x - 62))
    n('crash', 62, 0, 16, vel=100)

    only = os.environ.get('ONLY')
    if only:
        keep = {c[k] for k in only.split(',')}
        notes[:] = [x for x in notes if x[0] in keep]

    by_block = {}
    for note in notes:
        blk = note[1] // (4 * BAR)
        by_block.setdefault(blk, []).append((note[0], note[1] - blk * 4 * BAR) + note[2:])
    sections = {0: 'Intro', 2: 'Drop A', 6: 'Break', 8: 'Build', 9: 'Drop B', 13: 'Drop C', 15: 'Outro'}
    name = 'Intro'
    for blk in range(17):  # 68 bars
        name = sections.get(blk, name)
        pid = pr.pattern('%s %d' % (name, blk + 1), by_block.get(blk, []))
        pr.clip(pid, blk * 4, 0, 4)

    E = lambda rel: preset('Effects', rel)
    fx = {  # same chains/slots as Send Me so mix.py's knob list applies
        1: ['Fruity Parametric EQ 2\\Kick.fst', 'Fruity Limiter\\For drums (slight saturation).fst'],
        2: ['Fruity Parametric EQ 2\\Tight Drum Sizzle.fst', 'Fruity Limiter\\Drum compression.fst', 'LuxeVerb\\Live Drum Room.fst'],
        3: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Damped Drum Room.fst'],
        4: ['Fruity Parametric EQ 2\\40Hz + 18kHz cut.fst', 'Fruity Blood Overdrive\\Drive.fst', 'Fruity Compressor\\Vintage.fst'],
        5: ['Fruity Parametric EQ 2\\Vocal Presence.fst', 'Fruity Delay 3\\Tape.fst', 'LuxeVerb\\Vocal Plate 1.fst'],
        6: ['Fruity Soft Clipper\\Default.fst', 'Fruity Compressor\\Leveler 1.fst'],
        7: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Lush Pad Hall.fst'],
        8: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Large Wood Room.fst'],
        9: ['Fruity Blood Overdrive\\Drive.fst', 'Fruity Reeverb 2\\Large Hall.fst'],
        10: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'Fruity Delay 3\\Ping pong.fst', 'LuxeVerb\\Bright Hall.fst'],
        11: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'Fruity Compressor\\Drums.fst', 'LuxeVerb\\Damped Drum Room.fst'],
        12: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Lush Pad Hall.fst'],
        0: ['Fruity Parametric EQ 2\\Default.fst', 'Maximus\\Slight warmness.fst', 'Fruity Soft Clipper\\Default.fst', 'Fruity Limiter\\Max loudness (slight saturation).fst'],
    }
    for ins, chain in fx.items():
        for slot, rel in enumerate(chain):
            pr.effect(ins, slot, E(rel))

    sample_ch = [k for k in MAN['chops'] if k != 'hype'] + ['cyc1_cut', 'cyc4_spz', 'cyc2_tape', 'gate4', 'gate4_run']
    route = {1: ['kick', 'kick2', '808'], 2: ['snare', 'clap'], 3: ['hat', 'ohat', 'crash'], 4: sample_ch,
             5: ['hype', 'stut_need', 'stut_run'], 6: ['riser', 'rev_fm', 'tape2'], 7: ['choir'], 8: ['rpiano'],
             9: ['saw'], 10: ['bell'], 11: ['break', 'break2', 'tom', 'bigdrum'], 12: ['arp']}
    json.dump({'route': {ins: [c[k] for k in ks] for ins, ks in route.items()},
               'names': {1: 'Kick+808', 2: 'Snare/Clap', 3: 'Hats', 4: 'Runaway LAMC', 5: 'Vox edits', 6: 'FX',
                         7: 'Choir', 8: 'Runaway piano', 9: 'Supersaw', 10: 'Bells', 11: 'Breaks/Toms', 12: 'Arp'},
               'channels': c, 'bars': 68, 'bpm': BPM},
              open(os.path.splitext(out)[0] + '.mix.json', 'w'), indent=1)
    pr.save(out)
    print('built', out, '-', len(pr.channels), 'channels,', len(notes), 'notes,', len(pr.patterns), 'patterns')


if __name__ == '__main__':
    import sys
    os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'out', 'Run Right Back.flp'))
