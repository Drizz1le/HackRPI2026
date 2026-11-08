"""'Send Me' - an original love-letter song, Graduation era with a Bound 2 vibe.

Samples: The Ponderosa Twins Plus One "You Send Me" (12/8 doo-wop, the group behind Bound 2's "Bound"),
coupled +4 st: its dotted-quarter pulse 58.7 -> 74 BPM (Bound 2 tempo), C -> E major, the triplet swing
kept. Smokey Robinson "Baby Come Close" vocal chops, chipmunk +5 (B -> E).
Changes: E - C#m | F#m - B7 (I vi | ii V). Rhodes in neo-soul voicings (White Dress), Juno-style synth
strings (Flashing Lights), supersaw stabs in the last hook (Good Life / Stronger), Graduation kit drums
on a triplet grid, Bound 2 hard stops with a chipmunk "baby come close" in the hole, Lost in the World
tribal drums under the love-letter bridge ("wanting you ... to marry you ... and take you home").

  Intro 0-3 | Hook 4-11 | Verse 12-27 | Hook 28-35 | Verse 36-51 | Bridge 52-59 | Final hook 60-67
  | Outro 68-75   (v3. v4: Yeezus break at 36-39, everything after +4 bars -> 80 bars, 4:20)
"""
import json, os, random
import numpy as np
from flpbuild import Project, preset, BAR

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.expanduser('~') + r'\Documents\FLStudio'
GR = KIT + r'\Graduation'
MB = KIT + r'\MBDTF Drum Kit'
MAN = json.load(open(os.path.join(ROOT, 'chops', 'flip', 'manifest.json')))
CH = {k: v['file'] for k, v in MAN['chops'].items()}
T = BAR // 12  # triplet 8th: 12 per bar (12/8 feel)
BPM = MAN['bpm']
random.seed(5)
PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
# voicings (Rhodes, around middle C) with smooth voice leading; roots stay in the 808
VOICE = {'E': [56, 59, 63, 66], 'C#m': [56, 59, 63, 64], 'F#m': [57, 61, 64, 68], 'B7': [57, 61, 63, 68]}
LOOP_H = [['E', 'C#m'], ['F#m', 'B7']] * 2  # per bar, half-bar chords
H = {'hookA': LOOP_H, 'loopA': LOOP_H, 'loopB': LOOP_H, 'miss': LOOP_H[:2],
     'intro': [['B7']] * 4, 'darling': [['B7']] * 4,
     'letter': [['F#m', 'B7'], ['E', 'C#m'], ['F#m'], ['B7']]}
root = lambda ch: ch.rstrip('m7')


def bass_key(pc):  # E1..D#2
    return 28 + (PC[pc] - 4) % 12


def stop_variant(path, beats):
    """Bound 2 hard stop baked into the audio: last beat silent (FL's Sampler kept playing past a
    shortened note in v1, so the stop has to live in the file)."""
    import soundfile as sf
    dst = path.replace('.wav', '_stop.wav')
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(path):
        y, sr = sf.read(path, always_2d=True)
        cut = int(round((beats - 1) * 60.0 / BPM * sr))
        f = int(0.008 * sr)
        y[cut - f:cut] *= np.linspace(1, 0, f)[:, None]
        y[cut:] = 0
        sf.write(dst, y, sr, subtype='PCM_24')
    return dst


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
    c['kick'] = smp('Kick (Homecoming)', GR + r'\Kicks\Kick (Homecoming).wav')
    c['snare'] = smp('Snare (Good Morning)', GR + r'\Snares\Snare (Good Morning).wav')
    c['clap'] = smp('Clap (Flashing Lights)', GR + r'\Claps\Clap (Flashing Lights).wav')
    c['hat'] = smp('Hat (Stronger)', GR + r'\Hats\Hi Hat (Stronger).wav')
    c['ohat'] = smp('Open hat (Barry Bonds)', GR + r'\Hats\Open Hat (Barry Bonds).wav')
    c['ride'] = smp('Ride (Big Brother)', GR + r'\Perc\Ride (Big Brother).wav')
    c['tamb'] = smp('Tamb (Homecoming)', GR + r'\Perc\Tamb (Homecoming).wav')
    c['crash'] = smp('Crash (Devil)', MB + r'\Hats\Crash (Devil In A New Dress).wav')
    c['bigdrum'] = smp('Big drum (Lost)', MB + r'\Percussion\Big Drum (Lost In The World).wav')
    c['bigdrum2'] = smp('Big drum 2 (Lost)', MB + r'\Percussion\Big Drum 2 (Lost In The World).wav')
    p808 = KIT + r'\Dope Tec\-808s & Bass\[808] Clean.wav'
    c['808'] = smp('808', p808)
    for k in CH:
        c[k] = smp(k, CH[k])
        if MAN['chops'][k].get('src_beat') is not None and MAN['chops'][k]['beats'] == 16:
            c[k + '_stop'] = smp(k + ' stop', stop_variant(CH[k], 16))
    c['rhodes'] = pr.plugin('Rhodes', G(r'Harmor\Keyboard\Rhodes.fst'))
    c['strings'] = pr.plugin('Synth strings', G(r'Kepler\Synths\J106 Brass & Strings softer.fst'))
    c['saw'] = pr.plugin('Supersaw', G(r'Harmless\X Nucleon\Lead\90 Supersaw.fst'))
    c['arp'] = pr.plugin('Pluck arp', G(r'Harmless\Keyboards\Dancer Pluck FG.fst'))
    c['mbox'] = pr.plugin('Music box', G(r'Fruity DX10\Music Box.fst'))
    c['piano'] = pr.plugin('Piano', G(r'FL Keys\Concert Piano.fst'))
    c['lead'] = pr.plugin('Whistle lead', G(r'Harmless\X Olbaid\Lead\Lead Whistle.fst'))
    for k, f in MAN['yz'].items():
        c[k] = smp(k, f)

    r808 = detect_root(p808)
    k808 = lambda ch: 60 + (bass_key(root(ch)) - r808)
    notes = []
    harm = {}  # bar -> [chord, chord]

    def nt(ch, bar, t, tlen, key=60, vel=100, pan=64):  # triplet-grid note
        notes.append((c[ch], int(bar * BAR + t * T), int(tlen * T), key, vel, pan))

    def chop(name, bar, times=1, cut_last=False, vel=100):
        beats = MAN['chops'][name]['beats']
        bars = max(1, beats // 4)
        for i in range(times):
            b = bar + i * bars
            stop = (cut_last or name == 'hookA') and name + '_stop' in c
            nt(name + '_stop' if stop else name, b, 0, beats * 3, vel=vel)  # Bound 2 stop: last beat silent
            for k, chs in enumerate(H.get(name, [])[:bars]):
                harm[b + k] = chs

    def drums(bar, style='verse', stop=False):
        kicks = {'verse': [0, 5, 7], 'hook': [0, 5, 6, 8], 'half': [0, 7]}[style]
        end = 9 if stop else 12
        for t in kicks:
            if t < end:
                nt('kick', bar, t, 1, vel=120 if t == 0 else 104)
        for t in ((3, 9) if style != 'half' else (6,)):
            if t < end:
                nt('snare', bar, t, 1, vel=118)
                nt('clap', bar, t, 1, vel=108 if style == 'hook' else 84)
        for t in range(end):
            on_beat = t % 3 == 0
            if style == 'hook' or on_beat or t % 3 == 2:  # shuffle: beat + the triplet "a"
                nt('hat', bar, t, 1, vel=(100 if on_beat else 62 if t % 3 == 1 else 76) + random.randint(-5, 5), pan=74)
        if style == 'hook' and not stop:
            nt('ohat', bar, 11, 1, vel=72, pan=54)
            for t in (3, 9):
                nt('tamb', bar, t + 1, 1, vel=74, pan=44)

    def sub808(bar, verse=False, stop=False):
        chs = harm.get(bar)
        if not chs:
            return
        if verse:  # short notes locked to the kick
            for t in (0, 5, 7):
                ch = chs[0] if t < 6 or len(chs) == 1 else chs[1]
                nt('808', bar, t, 2 if t else 4, key=k808(ch), vel=92)  # v5: sub was 45% (median 32)
            return
        for i, ch in enumerate(chs):
            span = 12 // len(chs)
            ln = span - (3 if stop and i == len(chs) - 1 else 0)
            nt('808', bar, i * span, ln, key=k808(ch), vel=98)

    def rhodes(bar, vel=78, stop=False):
        for i, ch in enumerate(harm.get(bar, [])):
            span = 12 // len(harm[bar])
            for t, ln, v in ((0, 3, 0), (4, 2, -12)):  # comp: on the beat, then the triplet push
                if stop and i * span + t >= 9:
                    continue
                for k in VOICE[ch]:
                    nt('rhodes', bar, i * span + t, ln, key=k, vel=vel + v)

    def strings(bar, vel=70):
        for i, ch in enumerate(harm.get(bar, [])):
            span = 12 // len(harm[bar])
            for k in VOICE[ch][1:]:
                nt('strings', bar, i * span, span, key=k + 12, vel=vel)

    def saws(bar):
        for i, ch in enumerate(harm.get(bar, [])):
            span = 12 // len(harm[bar])
            for t in (0, 2):
                for k in VOICE[ch]:
                    nt('saw', bar, i * span + t, 1, key=k + 12, vel=96 if t == 0 else 78)

    def bound_stop(bar):  # Bound 2: everything drops on beat 4, a chipmunk "baby come close" fills it
        nt('sm_close', bar, 9, 6, vel=112)

    def hook(bar, big=False):
        chop('hookA', bar, 2)
        for x in range(bar, bar + 8):
            stop = x % 4 == 3
            drums(x, 'hook', stop=stop)
            sub808(x, stop=stop)
            rhodes(x, 74, stop=stop)
            strings(x, 76 if big else 64)
            if big:
                saws(x)
                if x % 2 == 0:
                    nt('ride', x, 0, 3, vel=80, pan=80)
            if stop:
                bound_stop(x)
        nt('crash', bar, 0, 6, vel=104)
        if big:
            for x in (bar, bar + 4):
                nt('bigdrum', x, 0, 3, vel=116)

    def verse(bar, plan):
        b = bar
        for name, times in plan:
            chop(name, b, times, cut_last=(name != 'miss'), vel=88)  # v5: verses under the hooks
            b += times * MAN['chops'][name]['beats'] // 4
        for x in range(bar, b):
            stop = x % 4 == 3
            drums(x, 'verse', stop=stop)
            sub808(x, verse=True)
            rhodes(x, 64, stop=stop)
            if stop:
                bound_stop(x)
        return b

    # ---------------- arrangement (v4: Yeezus break + more instruments, 80 bars) ----------------
    def arp(bar, vel=70):  # Graduation triplet arpeggio (Flashing Lights motion), an octave over the Rhodes
        for i, ch in enumerate(harm.get(bar, [])):
            span = 12 // len(harm[bar])
            v = VOICE[ch]
            seq = [v[0] + 12, v[1] + 12, v[2] + 12, v[3] + 12, v[2] + 12, v[1] + 12]
            for t in range(span):
                nt('arp', bar, i * span + t, 1, key=seq[t % 6], vel=vel + (10 if t % 3 == 0 else 0), pan=50 + 28 * (t % 2))

    def musicbox(bar, vel=72):
        for i, ch in enumerate(harm.get(bar, [])):
            span = 12 // len(harm[bar])
            top = VOICE[ch][-1] + 24
            nt('mbox', bar, i * span, 3, key=top, vel=vel)
            nt('mbox', bar, i * span + 4, 2, key=top - 5, vel=vel - 14)

    def piano_stab(bar, vel=92):  # Homecoming: octave chords on the beat
        for i, ch in enumerate(harm.get(bar, [])):
            span = 12 // len(harm[bar])
            r = 40 + (PC[root(ch)] - 40) % 12
            for t in range(0, span, 3):
                for k in [r, r + 12] + [x + 12 for x in VOICE[ch]]:
                    nt('piano', bar, i * span + t, 2, key=k, vel=vel - (8 if t else 0))

    def drop_fill(bar):  # remove the stop's "baby come close" so a Yeezus edit can take the hole
        notes[:] = [z for z in notes if not (z[0] == c['sm_close'] and z[1] == int(bar * BAR + 9 * T))]

    chop('intro', 0)  # B7 pedal, the twins' oohs, Rhodes + piano swells, Smokey enters
    for x in range(4):
        for k in VOICE['B7']:
            nt('rhodes', x, 0, 12, key=k, vel=70)
        if x >= 2:
            piano_stab(x, 76)
    nt('sm_lights', 2, 0, 18, vel=108)
    nt('bigdrum', 3, 9, 3, vel=110)
    hook(4)
    for x in range(4, 12):
        musicbox(x)
    drop_fill(11)
    nt('yz_stutter', 11, 6, 12, vel=110)  # "s-s-s-send me" into verse 1
    verse(12, [('loopA', 4)])
    nt('sm_warm', 17, 0, 18, vel=100)
    nt('vox_send', 21, 6, 6, vel=104)
    drop_fill(27)
    nt('yz_tapestop', 27, 9, 3, vel=110)  # verse 1 grinds to a halt into hook 2
    hook(28)
    for x in range(28, 36):
        musicbox(x)
    nt('yz_808', 28, 0, 9, vel=110)
    # Yeezus break 36-39: no drums. Blown 808, acid line, the demon "so warm", a scream, silence
    nt('yz_808', 36, 0, 9, vel=120)
    nt('yz_acid', 36, 0, 24, vel=105)
    for t in (0, 6):
        nt('yz_808', 38, t, 6, vel=112)
    nt('yz_demon', 38, 0, 18, vel=110)
    for t in (3, 9):
        nt('clap', 38, t, 1, vel=110)
        nt('clap', 39, t, 1, vel=110)
    nt('yz_scream', 39, 6, 6, vel=100)
    verse(40, [('loopA', 2), ('miss', 2), ('loopA', 1)])
    for x in range(40, 56):
        arp(x, 60 if x < 48 else 68)
        if x >= 44:
            strings(x, 58)
    nt('sm_dreams', 50, 0, 15, vel=104)
    drop_fill(47)
    nt('yz_scream', 47, 9, 6, vel=84)
    # bridge 56-63: the love letter. "darling you send me" (B7 pedal) -> "wanting you, marry you, take you home"
    chop('darling', 56)
    chop('letter', 60)
    for x in range(56, 64):
        sub808(x)
        strings(x, 60 + 2 * (x - 56))
        rhodes(x, 66)
        if x >= 60:
            piano_stab(x, 84)
        for t, d, v in ((0, 'bigdrum', 112), (5, 'bigdrum2', 90), (7, 'bigdrum2', 96), (10, 'bigdrum', 100)):
            nt(d, x, t, 2, vel=v + (x - 56), pan=58 if d == 'bigdrum' else 70)  # Lost in the World
        if x >= 60:
            for t in (3, 9):
                nt('clap', x, t, 1, vel=96)
        if x >= 62:
            for t in range(12):
                nt('hat', x, t, 1, vel=60 + t * 3, pan=74)
    nt('yz_riser', 63, 0, 12, vel=100)
    hook(64, big=True)
    for x in range(64, 72):
        arp(x, 66)
        musicbox(x, 78)
    nt('yz_808', 64, 0, 9, vel=118)
    chop('loopB', 72, 2)  # outro: the band alone, the twins' last words, a whistle melody, Smokey a cappella
    for x in range(72, 80):
        if x < 76:
            drums(x, 'half')
            sub808(x)
        rhodes(x, 66 - 2 * (x - 72))
    melody = [(72, 0, 6, 71), (72, 6, 3, 68), (72, 9, 3, 64), (73, 0, 6, 66), (73, 6, 6, 63),
              (74, 0, 6, 71), (74, 6, 3, 73), (74, 9, 3, 71), (75, 0, 9, 68), (75, 9, 3, 66),
              (76, 0, 12, 64), (77, 0, 6, 63), (77, 6, 6, 66)]
    for bar, t, ln, k in melody:  # 808s-era whistle lead, answers the twins (E major: B G# E F# D#)
        nt('lead', bar, t, ln, key=k, vel=88)
    nt('vox_marry', 72, 6, 12, vel=104)
    nt('vox_home', 74, 6, 12, vel=104)
    nt('vox_darl', 76, 0, 12, vel=100)
    nt('sm_lights', 78, 0, 18, vel=104)
    for k in VOICE['E']:
        nt('rhodes', 79, 6, 18, key=k, vel=62)

    only = os.environ.get('ONLY')
    if only:
        keep = {c[k] for k in only.split(',')}
        notes[:] = [x for x in notes if x[0] in keep]

    by_block = {}
    for note in notes:
        blk = note[1] // (4 * BAR)
        by_block.setdefault(blk, []).append((note[0], note[1] - blk * 4 * BAR) + note[2:])
    sections = {0: 'Intro', 1: 'Hook 1', 3: 'Verse 1', 7: 'Hook 2', 9: 'Yeezus', 10: 'Verse 2', 14: 'Bridge', 16: 'Final Hook', 18: 'Outro'}
    name = 'Intro'
    for blk in range(20):  # 80 bars
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

    route = {1: ['kick', '808'], 2: ['snare', 'clap'], 3: ['hat', 'ohat', 'ride', 'crash'],
             4: [k for k in c if k.split('_')[0] in ('intro', 'hookA', 'loopA', 'loopB', 'miss', 'letter', 'darling')],
             5: ['vox_send', 'vox_marry', 'vox_home', 'vox_darl', 'sm_lights', 'sm_close', 'sm_warm', 'sm_dreams',
                 'yz_demon', 'yz_stutter', 'yz_scream'],
             6: ['yz_acid', 'yz_808', 'yz_riser'], 7: ['strings'], 8: ['rhodes', 'piano'], 9: ['saw'], 10: ['lead'],
             11: ['tamb', 'bigdrum', 'bigdrum2'], 12: ['arp', 'mbox']}
    json.dump({'route': {ins: [c[k] for k in ks] for ins, ks in route.items()},
               'names': {1: 'Kick+808', 2: 'Snare/Clap', 3: 'Hats', 4: 'Ponderosa', 5: 'Vox chops', 6: 'Yeezus FX',
                         7: 'Synth strings', 8: 'Rhodes/Piano', 9: 'Supersaw', 10: 'Lead', 11: 'Perc/Tribal', 12: 'Arp/Music box'},
               'channels': c, 'bars': 80, 'bpm': BPM},
              open(os.path.splitext(out)[0] + '.mix.json', 'w'), indent=1)
    pr.save(out)
    print('built', out, '-', len(pr.channels), 'channels,', len(notes), 'notes,', len(pr.patterns), 'patterns')


if __name__ == '__main__':
    import sys
    os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'out', 'Send Me.flp'))
