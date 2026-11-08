"""'Saw the Light' - an MBDTF / Good Ass Job era flip of Todd Rundgren's "I Saw the Light".

Everything is written in code and lands in a real FL Studio project (flpbuild), so it stays editable
in FL. Research behind the choices: docs/research.md.

  82 BPM, F# major (source G, warped and dropped 1 semitone). 92 bars, ~4:29.
  Intro 0-7 | Verse 8-23 | Hook 24-31 | Verse 32-47 | Hook 48-55 | Interlude 56-63 (no drums)
  | Return 64-71 (solo peak) | Final hook 72-79 | Coda 80-91 (distorted "in my eyes", lone piano)
"""
import json, os, random
import numpy as np, soundfile as sf
from flpbuild import Project, preset, BAR

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.expanduser('~') + r'\Documents\FLStudio'
MAN = json.load(open(os.path.join(ROOT, 'chops', 'flip', 'manifest.json')))
CH = {k: v['file'] for k, v in MAN['chops'].items()}
B = 96            # ticks per beat
S = B // 4        # 16th
BPM = MAN['bpm']
random.seed(7)

PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def bass_key(pc):          # E1..D#2 : 41-78 Hz fundamentals (MBDTF synth-bass range)
    return 28 + (PC[pc] - 4) % 12


def triad(pc, octave_base=60, minor=False):
    r = octave_base + (PC[pc] - octave_base) % 12
    return [r, r + (3 if minor else 4), r + 7]


# ---- offline variants of chops (filtering/distortion baked in, like resampling on an ASR-10) ----
def variant(name, kind):
    src = CH[name]
    dst = src.replace('.wav', '_%s.wav' % kind)
    # rebuild whenever the chop is newer (v10 fix: a stale lpf intro from before the timing fix was off beat)
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        from scipy.signal import butter, sosfilt
        y, sr = sf.read(src, always_2d=True)
        if kind == 'lpf':      # intro: muffled "through the wall" sample
            y = sosfilt(butter(4, 700, 'low', fs=sr, output='sos'), y, axis=0) * 1.6
        elif kind == 'dist':   # coda: overdriven, band-limited vocal (Runaway outro feel)
            y = sosfilt(butter(2, [250, 4500], 'band', fs=sr, output='sos'), y, axis=0)
            y = np.tanh(y * 9.0) * 0.5
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

    # ---- channels ----
    c = {}
    # v4: punch from the Devil kick (74 Hz, 6% sub); Runaway kick tucked under for weight. The Power layer
    # kick (32 Hz, 97% sub, 0.39 s) was the rumble that put 81% of verse energy below 60 Hz.
    c['kick'] = smp('Kick (Devil)', KIT + r'\MBDTF Drum Kit\Kicks\Kick (Devil In A New Dress).wav')
    c['kick2'] = smp('Kick sub (Runaway)', KIT + r'\MBDTF Drum Kit\Kicks\Kick (Runaway).wav')
    c['snare'] = smp('Snare (Devil)', KIT + r'\MBDTF Drum Kit\Snares\Snare (Devil In A New Dress).wav')
    c['snare2'] = smp('Snare layer (Power)', KIT + r'\MBDTF Drum Kit\Snares\Layer Snare (Power).wav')
    c['clap'] = smp('Clap (Power)', KIT + r'\MBDTF Drum Kit\Claps\Clap (Power).wav')
    c['hat'] = smp('Hat (Devil)', KIT + r'\MBDTF Drum Kit\Hats\Closed Hat (Devil In A New Dress).wav')
    c['ohat'] = smp('Open hat (Devil)', KIT + r'\MBDTF Drum Kit\Hats\Open Hat (Devil In A New Dress).wav')
    c['crash'] = smp('Crash (Devil)', KIT + r'\MBDTF Drum Kit\Hats\Crash (Devil In A New Dress).wav')
    c['bigdrum'] = smp('Big drum (Lost)', KIT + r'\MBDTF Drum Kit\Percussion\Big Drum (Lost In The World).wav')
    c['tom'] = smp('Tom (Devil)', KIT + r'\MBDTF Drum Kit\Percussion\Tom (Devil In A New Dress).wav')
    p808 = KIT + r'\Dope Tec\-808s & Bass\[808] Clean.wav'
    c['808'] = smp('808', p808)
    for k in ('loopA', 'hookA', 'hookB', 'prehook', 'last', 'vamp'):
        c[k] = smp('chop ' + k, CH[k])
    c['loopA_lpf'] = smp('chop loopA lpf', variant('loopA', 'lpf'))
    for k in ('vox_light', 'vox_head', 'vox_saw', 'vox_eyes1', 'vox_eyes2'):
        c[k] = smp(k, CH[k])
    c['eyes1_dist'] = smp('eyes1 dist', variant('vox_eyes1', 'dist'))
    c['eyes2_dist'] = smp('eyes2 dist', variant('vox_eyes2', 'dist'))
    c['piano'] = pr.plugin('Piano', G(r'FL Keys\Concert Piano.fst'))
    c['lowstr'] = pr.plugin('Low strings', G(r'Kepler Exo\X Saif Sameer\Strings\LowStrings.fst'))
    c['cello'] = pr.plugin('Cello', G(r'Sakura\Sonic Haiku Bank\BW Deep Wide Cello.fst'))
    c['choir'] = pr.plugin('Choir', G(r'Kepler\Pads\Choir 1.fst'))
    c['brass'] = pr.plugin('Brass stab', G(r'Kepler Exo\X Saif Sameer\Brasses\Big Brass.fst'))
    c['moog'] = pr.plugin('Moog bass', G(r'PoiZone\Factory\BAS MoogaBass TC.fst'))
    c['lead'] = pr.plugin('Lead (Dean)', G(r'Sawer\Leads\FG Weeping Moog.fst'))
    c['gtr'] = pr.plugin('Guitar (Dean)', G(r'Sytrus\X Saif Sameer\Synths\TG33 Dist Guitar 1.fst'))
    # v10 groove layer: the Runaway move (live break under the programmed kick + reverbed clap) and the
    # Lost in the World tribal drums, plus motion/warmth layers MBDTF is full of
    LOOP = json.load(open(os.path.join(ROOT, 'chops', 'loops', 'manifest.json')))
    c['brk'] = smp('Break (Good Life)', LOOP['break_goodlife']['file'])
    c['perc'] = smp('Perc loop (Shining)', LOOP['perc_shining']['file'])
    c['tamb'] = smp('Tamb (Homecoming)', KIT + r'\Graduation\Perc\Tamb (Homecoming).wav')
    c['bigdrum2'] = smp('Big drum 2 (Lost)', KIT + r'\MBDTF Drum Kit\Percussion\Big Drum 2 (Lost In The World).wav')
    c['spic'] = pr.plugin('Spiccato strings', G(r'Kepler Exo\X Sako\Instrument\Strings\String Spiccato.fst'))
    c['organ'] = pr.plugin('Organ', G(r'Harmless\Keyboards\Hammond Organ NUC.fst'))
    c['bells'] = pr.plugin('Bells', G(r'Harmless\Percussion\Church Bells 1 FG.fst'))

    r808 = detect_root(p808)
    k808 = lambda pc: 60 + (bass_key(pc) - r808)  # sampler: key 60 plays the sample at its own pitch

    notes = []

    def n(ch, bar, step, length_steps, key=60, vel=100, pan=64):
        notes.append((c[ch], int(bar * BAR + step * S), int(length_steps * S), key, vel, pan))

    def chop(name, bar, beats=None):
        n(name, bar, 0, (beats or MAN['chops'].get(name, {'beats': 4})['beats']) * 4)

    # harmony per bar of each chop (root pitch classes, from the transposed source bassline)
    H = {'loopA': [['C#'], ['F#', 'D#']], 'hookA': [['C#'], ['C#'], ['F#'], ['B']],
         'hookB': [['C#'], ['C#'], ['F#'], ['B']], 'prehook': [['B'], ['B'], ['E'], ['D#', 'G#']],
         'last': [['C#'], ['C#'], ['F#'], ['B']], 'vamp': [['C#', 'F#'], ['B']]}
    MINOR = {'D#', 'G#'}
    harmony = {}  # bar -> list of roots

    def lay(name, bar, times):
        for t in range(times):
            ln = len(H[name])
            chop(name, bar + t * ln)
            for i, roots in enumerate(H[name]):
                harmony[bar + t * ln + i] = roots

    def drums(bar, style='verse', fill=False):
        kicks = {'verse': [0, 7, 10], 'verse2': [0, 7, 10, 14], 'hook': [0, 3, 7, 10]}[style]
        for s in kicks:  # v6: no sub-kick layer - the 808 owns the sub (element scan: Runaway kick 88% <60 Hz)
            n('kick', bar, s, 2, vel=118 if s == 0 else 104)
        for s in (4, 12):
            n('snare', bar, s, 2, vel=120)
            n('snare2', bar, s, 2, vel=90)
            if style == 'hook':
                n('clap', bar, s, 2, vel=115)
        if style == 'hook':  # v10: swung 16ths push the hooks forward; roll into every 4th bar
            for s in range(16):
                sw = 0.17 if s % 2 else 0.0  # ~17% swing on the off-16ths
                n('hat', bar, s + sw, 1, vel=(104 if s % 4 == 0 else 84 if s % 2 == 0 else 62) + random.randint(-6, 6), pan=74)
            if bar % 4 == 3:
                for k in range(8):  # 32nd-note roll on the last beat, rising
                    n('hat', bar, 12 + k * 0.5, 0.5, vel=60 + k * 6, pan=74)
        else:
            for s in range(0, 16, 2):
                n('hat', bar, s, 1, vel=(100 if s % 4 == 0 else 72) + random.randint(-6, 6), pan=74)
            for s in (7, 15):  # 16th pickups keep the verses rolling
                n('hat', bar, s + 0.17, 1, vel=58 + random.randint(-4, 4), pan=74)
            for s in (4, 12):
                n('clap', bar, s, 2, vel=78)  # soft clap under the snare (reverbed on the snare bus)
        if style == 'hook':
            n('ohat', bar, 14, 2, vel=80, pan=54)
            n('ohat', bar, 6, 2, vel=66, pan=54)
        if bar % 4 == 3:
            n('snare', bar, 15, 1, vel=58)  # ghost into the next phrase
        if fill:
            for i, s in enumerate((8, 10, 12, 14)):
                n('tom', bar, s, 2, key=62 - 3 * i, vel=105)

    def bassline(bar, groove=(0, 7, 10)):
        roots = harmony.get(bar)
        if not roots:
            return
        lens = {0: 6, 3: 3, 7: 3, 10: 5, 14: 2}
        for s in groove:
            pc = roots[0] if (len(roots) == 1 or s < 8) else roots[1]
            # v3: an octave up (82-156 Hz) - v2 measured 84% of verse energy below 60 Hz
            n('moog', bar, s, lens.get(s, 3), key=bass_key(pc) + 12, vel=100)

    def sub808(bar, groove=None):
        """Sustained 808 under hooks; with `groove`, short notes locked to the kick (verses)."""
        roots = harmony.get(bar)
        if roots and groove:
            lens = {0: 5, 3: 3, 7: 3, 10: 5, 14: 2}
            for s in groove:
                pc = roots[0] if (len(roots) == 1 or s < 8) else roots[1]
                n('808', bar, s, lens.get(s, 3), key=k808(pc), vel=104)
            return
        if roots:
            n('808', bar, 0, 8 if len(roots) > 1 else 15, key=k808(roots[0]), vel=110)
            if len(roots) > 1:
                n('808', bar, 8, 7, key=k808(roots[1]), vel=104)

    def pad(ch, bar, octave_base, vel, fifths_only=False):
        for i, pc in enumerate(harmony.get(bar, [])):
            span = 16 // len(harmony[bar])
            keys = [octave_base + (PC[pc] - octave_base) % 12]
            keys += [keys[0] + 7, keys[0] + 12] if fifths_only else triad(pc, octave_base, pc in MINOR)[1:]
            for k in keys:
                n(ch, bar, i * span, span, key=k, vel=vel)

    def groove(bar, level='verse'):
        """v10 forward motion: Good Life break under everything (every 2 bars); in hooks also the
        Shining perc loop, offbeat tambourine and Lost in the World tribal drums between the kicks."""
        if bar % 2 == 0:
            n('brk', bar, 0, 32, vel=100 if level == 'hook' else 88)
        if level == 'hook':
            if bar % 4 == 0:
                n('perc', bar, 0, 64, vel=80)
            for s in (2, 6, 10, 14):
                n('tamb', bar, s + 0.17, 1, vel=76 + random.randint(-6, 6), pan=46)
            for s, d, v in ((6, 'bigdrum2', 96), (11, 'bigdrum', 88), (14, 'bigdrum2', 92)):
                n(d, bar, s, 2, vel=v, pan=58 if d == 'bigdrum' else 70)
        else:
            for s in (4, 12):
                n('tamb', bar, s, 1, vel=64, pan=46)

    def motion(bar, vel=74):
        """Spiccato strings in 8ths through the chord (upper mids) - MBDTF's constant movement."""
        roots = harmony.get(bar)
        if not roots:
            return
        for i in range(8):
            pc = roots[0] if (len(roots) == 1 or i < 4) else roots[1]
            t = triad(pc, 60, pc in MINOR)
            seq = [t[0], t[1], t[2], t[0] + 12, t[2], t[1], t[0] + 12, t[2]]
            n('spic', bar, i * 2, 2, key=seq[i], vel=vel + (8 if i % 2 == 0 else 0))

    def warmth(bar, vel=70):
        """Organ triads in the low mids (the 120-250 Hz band measured thin vs Kanye records)."""
        pad('organ', bar, 48, vel)

    def bell(bar):
        roots = harmony.get(bar)
        if roots:
            r = 72 + (PC[roots[0]] - 72) % 12
            for k in (r, r + 7):
                n('bells', bar, 0, 8, key=k, vel=82)

    def stab(bar):  # Power-style section opener
        roots = harmony.get(bar, ['C#'])
        for k in triad(roots[0], 60, roots[0] in MINOR) + [triad(roots[0], 48)[0]]:
            n('brass', bar, 0, 3, key=k, vel=120)
        n('crash', bar, 0, 8, vel=110)

    # ---------------- arrangement ----------------
    # Intro 0-7: lone piano note (Runaway), muffled sample enters, strings swell, big drums, stab
    for bar in range(0, 8):
        for beat in range(4):
            if bar < 4 or beat in (0, 2):
                n('piano', bar, beat * 4, 3, key=78, vel=92 - (beat % 2) * 14)  # F#5, repeated
    for t in range(2):
        chop('loopA_lpf', 4 + 2 * t)
        harmony[4 + 2 * t], harmony[5 + 2 * t] = ['C#'], ['F#', 'D#']
    for bar in range(4, 8):
        pad('lowstr', bar, 42, 70, fifths_only=True)
    for bar in (6, 7):
        n('bigdrum', bar, 0, 4, vel=118)
        n('bigdrum', bar, 8, 4, vel=104)
    n('vox_eyes1', 2, 0, 16, vel=80)

    # Verse 1 8-23
    lay('loopA', 8, 8)
    for bar in range(8, 24):
        drums(bar, 'verse', fill=(bar == 23))
        groove(bar, 'verse')
        sub808(bar, (0, 7, 10))
        if bar % 4 == 3 and bar != 23:
            n('vox_light', bar, 6, 8, vel=105)  # So Appalled move: offbeat vocal stab every 4th bar
    stab(8)

    # Hook 1 24-31
    lay('hookA', 24, 2)
    for bar in range(24, 32):
        drums(bar, 'hook')
        groove(bar, 'hook')
        motion(bar)
        warmth(bar)
        sub808(bar)
        pad('choir', bar, 60, 64)
        pad('lowstr', bar, 42, 76, fifths_only=True)
    stab(24)
    stab(28)
    bell(24)
    bell(28)

    # Verse 2 32-47
    lay('prehook', 32, 4)
    cello = [(0, 54, 8), (8, 51, 8), (16, 47, 16), (32, 44, 8), (40, 47, 8), (48, 46, 8), (56, 44, 8)]
    for bar in range(32, 47):
        drums(bar, 'verse2', fill=(bar == 46))
        groove(bar, 'verse')
        warmth(bar, 56)
        if bar >= 40:  # strings start moving halfway through the verse: build into the hook
            motion(bar, 62)
        sub808(bar, (0, 7, 10, 14))
    for phrase in (32, 36, 40, 44):
        for st, key, ln in cello:
            n('cello', phrase, st, ln, key=key, vel=88)
        if phrase != 44:
            n('vox_head', phrase + 3, 8, 16, vel=100)
    stab(40)
    n('kick', 47, 0, 2, vel=118)
    chop('vox_saw', 47)  # "I saw the" a cappella pickup into the hook

    # Hook 2 48-55
    lay('hookB', 48, 1)
    lay('hookA', 52, 1)
    for bar in range(48, 55):
        drums(bar, 'hook')
        groove(bar, 'hook')
        motion(bar)
        warmth(bar)
        sub808(bar)
        pad('choir', bar, 60, 66)
        pad('lowstr', bar, 42, 80, fifths_only=True)
        pad('cello', bar, 48, 70, fifths_only=True)
    n('kick', 55, 0, 2, vel=118)
    sub808(55)
    pad('choir', 55, 60, 66)
    for bar in (48, 50, 52, 54):
        stab(bar)
    bell(48)
    bell(52)

    # Interlude 56-63: drums out, live band plays the hook changes (Devil in a New Dress move)
    prog = ['C#', 'C#', 'F#', 'B'] * 2
    for i, pc in enumerate(prog):
        bar = 56 + i
        harmony[bar] = [pc]
        for beat in range(4):
            for k in triad(pc, 60):
                n('piano', bar, beat * 4, 3 if beat < 3 else 4, key=k, vel=86 - beat * 4)
        n('piano', bar, 0, 16, key=bass_key(pc) + 24, vel=90)
        pad('lowstr', bar, 42, 84, fifths_only=True)
        pad('cello', bar, 48, 78, fifths_only=True)
        n('moog', bar, 0, 14, key=bass_key(pc) + 12, vel=96)
        warmth(bar, 66)  # gospel organ under the live-band interlude
    lead_in = [(60, 0, 16, 73), (61, 0, 8, 70), (61, 8, 8, 68), (62, 0, 16, 66), (63, 0, 8, 68), (63, 8, 8, 70)]
    for bar, st, ln, key in lead_in:
        n('lead', bar, st, ln, key=key, vel=96)
    n('vox_eyes2', 59, 0, 16, vel=86)

    # Return 64-71: drums slam back, the solo peaks over the *instrumental* intro bed (Devil in a New
    # Dress move) - v9: the vocal "Can't you see the light" chop clashed with the lead melody here
    lay('loopA', 64, 4)
    for bar in range(64, 72):
        drums(bar, 'hook', fill=(bar == 71))
        groove(bar, 'hook')
        motion(bar, 70)
        sub808(bar)
        pad('lowstr', bar, 42, 82, fifths_only=True)
    stab(64)
    n('bigdrum', 64, 0, 4, vel=120)
    solo = [  # (bar, step, len16, key) F# major pentatonic, climbing to the peak, guitar doubles the top
        (64, 0, 6, 78), (64, 6, 2, 80), (64, 8, 8, 82), (65, 0, 4, 85), (65, 4, 4, 82), (65, 8, 8, 80),
        (66, 0, 12, 85), (66, 12, 4, 87), (67, 0, 16, 90),
        (68, 0, 2, 85), (68, 2, 2, 87), (68, 4, 2, 90), (68, 6, 2, 92), (68, 8, 8, 94),
        (69, 0, 4, 92), (69, 4, 4, 90), (69, 8, 4, 87), (69, 12, 4, 85),
        (70, 0, 8, 87), (70, 8, 8, 90), (71, 0, 12, 85), (71, 12, 4, 82)]
    for bar, st, ln, key in solo:
        n('lead', bar, st, ln, key=key, vel=104)
        if bar >= 68:
            n('gtr', bar, st, ln, key=key - 12, vel=96)

    # Final hook 72-79: everything
    lay('hookA', 72, 1)
    lay('hookB', 76, 1)
    for bar in range(72, 80):
        drums(bar, 'hook')
        groove(bar, 'hook')
        motion(bar, 80)
        warmth(bar, 74)
        sub808(bar)
        pad('choir', bar, 60, 70)
        pad('choir', bar, 72, 56, fifths_only=True)  # extra harmony stack
        pad('lowstr', bar, 42, 86, fifths_only=True)
        pad('cello', bar, 48, 74, fifths_only=True)
    for bar in (72, 74, 76, 78):
        stab(bar)
        bell(bar)
    # v9: no held lead under the vocal hook (two melodies fighting); the last chop answers the hook instead
    chop('vox_eyes1', 75)
    chop('vox_eyes2', 79)

    # Coda 80-91: vamp + distorted "in my eyes", drums drop at 84, lone piano note ends it
    lay('vamp', 80, 5)
    for bar in range(80, 90):
        if bar < 84:
            drums(bar, 'hook')
            groove(bar, 'hook')
            sub808(bar)
        else:
            warmth(bar, 62)
            if bar < 88:
                n('bigdrum', bar, 0, 4, vel=112)
        if bar >= 84:  # Moog takes the bass once the drums and 808 drop out
            bassline(bar, (0, 10))
        pad('lowstr', bar, 42, 80, fifths_only=True)
        pad('cello', bar, 48, 72, fifths_only=True)
        if bar % 2 == 0:
            n('eyes1_dist' if bar % 4 == 0 else 'eyes2_dist', bar, 0, 16, vel=100)
    n('lead', 80, 0, 64, key=78, vel=90)
    for bar in range(88, 91):
        for beat in (0, 2):
            n('piano', bar, beat * 4, 6, key=78, vel=84 - (bar - 88) * 10)
    n('piano', 91, 0, 16, key=78, vel=70)
    for k in (54, 61, 66):
        n('lowstr', 90, 0, 32, key=k, vel=70)

    only = os.environ.get('ONLY')  # analysis aid: keep just these channel keys (element-by-element renders)
    if only:
        keep = {c[k] for k in only.split(',')}
        notes[:] = [x for x in notes if x[0] in keep]

    # one pattern per 4-bar block so the playlist shows the structure and stays editable
    by_block = {}
    for note in notes:
        blk = note[1] // (4 * BAR)
        by_block.setdefault(blk, []).append((note[0], note[1] - blk * 4 * BAR) + note[2:])
    sections = {0: 'Intro', 2: 'Verse 1', 6: 'Hook 1', 8: 'Verse 2', 12: 'Hook 2', 14: 'Interlude',
                16: 'Return', 18: 'Final Hook', 20: 'Coda'}
    name = 'Intro'
    for blk in range(23):
        name = sections.get(blk, name)
        pid = pr.pattern('%s %d' % (name, blk + 1), by_block.get(blk, []))
        pr.clip(pid, blk * 4, 0, 4)

    # mixer effects (factory presets; fine-tuned live through the bridge by mix.py)
    E = lambda rel: preset('Effects', rel)
    fx = {
        1: ['Fruity Parametric EQ 2\\Kick.fst', 'Fruity Limiter\\For drums (slight saturation).fst'],
        2: ['Fruity Parametric EQ 2\\Tight Drum Sizzle.fst', 'Fruity Limiter\\Drum compression.fst', 'LuxeVerb\\Live Drum Room.fst'],
        3: ['Fruity Parametric EQ 2\\40Hz cut.fst', 'LuxeVerb\\Damped Drum Room.fst'],
        # v5: no Stereo Shaper - its 'Stereoize' dephasing put the sample out of phase (L/R correlation -0.24)
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
    skip = os.environ.get('SKIP_FX', '')  # debugging aid: comma list of inserts to leave empty
    for ins, chain in fx.items():
        if str(ins) in skip.split(','):
            continue
        for slot, rel in enumerate(chain):
            pr.effect(ins, slot, E(rel))

    # channel -> insert routing, applied live by mix.py (FL's API) after the project opens
    route = {1: ['kick', 'kick2', '808'], 2: ['snare', 'snare2', 'clap'], 3: ['hat', 'ohat', 'crash', 'bigdrum', 'tom'],
             4: ['loopA', 'loopA_lpf', 'hookA', 'hookB', 'prehook', 'last', 'vamp'],
             5: ['vox_light', 'vox_head', 'vox_saw', 'vox_eyes1', 'vox_eyes2', 'eyes1_dist', 'eyes2_dist'],
             6: ['moog'], 7: ['lowstr', 'cello', 'choir'], 8: ['piano'], 9: ['brass'], 10: ['lead', 'gtr'],
             11: ['brk', 'perc', 'tamb', 'bigdrum2'], 12: ['spic', 'organ', 'bells']}
    json.dump({'route': {ins: [c[k] for k in ks] for ins, ks in route.items()},
               'names': {1: 'Kick+808', 2: 'Snare/Clap', 3: 'Hats/Perc', 4: 'Sample', 5: 'Vox chops', 6: 'Moog bass',
                         7: 'Strings/Choir', 8: 'Piano', 9: 'Brass', 10: 'Lead', 11: 'Groove', 12: 'Layers'},
               'channels': c, 'bars': 92, 'bpm': BPM},
              open(os.path.splitext(out)[0] + '.mix.json', 'w'), indent=1)
    pr.save(out)
    print('built', out, '-', len(pr.channels), 'channels,', len(notes), 'notes,', len(pr.patterns), 'patterns')


if __name__ == '__main__':
    import sys
    os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'out', 'Saw the Light.flp'))
