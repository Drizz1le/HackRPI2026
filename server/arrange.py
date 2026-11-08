"""Turn the theory agent's composition plan into a full arrangement.

Pure Python, no FL Studio needed: this is the musical half of the instrumental
role. flstudio/tools/cluster_render.py takes the plan this module returns and
turns it into an FL Studio project and a rendered WAV.

    plan = plan_from_theory(theory_json_string)

The theory agent is a small model, so the input is treated as untrusted:
missing or garbled fields fall back to sensible defaults and everything is
clamped to a playable range. Every fallback is listed in plan["warnings"].

Output (all positions are relative to the start of their section):
    {
      "bpm": 90.0, "key": "A minor", "tonic": 9, "mode": "minor",
      "bar_seconds": 2.667, "bars": 64, "seconds": 170.7,
      "vocal_start_seconds": 21.3,      # end of the intro, where the voice comes in
      "sections": [
        {"name": "Intro", "style": "intro", "start_bar": 0, "bars": 8,
         "chords": ["Am", "F", ...],   # one per bar
         "notes": [[instrument, bar, step16, len16, midi_key, velocity], ...]},
        ...
      ],
      "warnings": [...]
    }

Instruments: keys, pad, bass, kick, snare, clap, hat, ohat, crash.
Drum notes use key 60 (the Sampler plays its sample unpitched); "bass" uses the
real MIDI key, and the renderer transposes it for the 808 sample's own pitch.
"""
import json
import re

STEPS = 16  # 16th-note grid, 4/4 only

NOTE_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PC_NAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "harmonic minor": [0, 2, 3, 5, 7, 8, 11],
}
MODE_ALIASES = {"ionian": "major", "maj": "major", "aeolian": "minor", "min": "minor",
                "m": "minor", "natural minor": "minor"}
MINOR_LIKE = {"minor", "dorian", "phrygian", "locrian", "harmonic minor"}

DEFAULT_PROGRESSION = {True: "i - VI - III - VII", False: "I - V - vi - IV"}  # keyed by minor?
DEFAULT_STRUCTURE = [("Intro", 8), ("Verse", 16), ("Hook", 8), ("Verse", 16), ("Hook", 8), ("Outro", 8)]

BPM_RANGE = (60.0, 180.0)
MAX_SECTION_BARS = 32
MAX_TOTAL_BARS = 128

# Chord qualities as intervals above the root.
QUALITIES = {
    "maj": [0, 4, 7], "min": [0, 3, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
    "sus2": [0, 2, 7], "sus4": [0, 5, 7],
    "7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10],
    "m7b5": [0, 3, 6, 10], "dim7": [0, 3, 6, 9],
}
QUALITY_SUFFIX = {"maj": "", "min": "m", "dim": "dim", "aug": "aug", "sus2": "sus2",
                  "sus4": "sus4", "7": "7", "maj7": "maj7", "m7": "m7", "m7b5": "m7b5",
                  "dim7": "dim7"}

ROMAN = ["vii", "iii", "vi", "iv", "ii", "v", "i"]  # longest first for matching
ROMAN_DEGREE = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _load_theory(theory):
    """Accept a dict or the agent's raw text (possibly with ```json fences)."""
    if isinstance(theory, dict):
        return theory
    text = str(theory or "")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _accidental(s):
    return {"#": 1, "♯": 1, "b": -1, "♭": -1}.get(s, 0)


def parse_key(text):
    """'A minor', 'F#m', 'Bb Dorian', 'C' -> (tonic pitch class, mode name)."""
    m = re.match(r"\s*([A-Ga-g])\s*([#b♯♭]?)\s*(.*)$", str(text or ""))
    if not m:
        return None
    tonic = (NOTE_PC[m.group(1).upper()] + _accidental(m.group(2))) % 12
    rest = m.group(3).strip().lower()
    rest = re.sub(r"\b(key|scale|mode)\b", "", rest).strip()
    if not rest:
        return tonic, "major"
    rest = MODE_ALIASES.get(rest, rest)
    if rest in MODES:
        return tonic, rest
    for name in sorted(MODES, key=len, reverse=True):  # "minor pentatonic" -> minor
        if name in rest:
            return tonic, name
    if rest.startswith("m") and not rest.startswith("maj"):
        return tonic, "minor"
    return tonic, "major"


def _quality_from_suffix(suffix, minor):
    """Chord suffix ('m7', 'maj7', 'dim', 'sus4', ...) -> quality name.
    `minor` is the default when the suffix says nothing (lowercase numerals)."""
    raw = suffix.strip()
    if raw.startswith(("M7", "Maj7", "maj7", "ma7", "Δ", "M9", "maj9")):
        return "maj7"
    s = raw.lower().replace("°", "dim").replace("ø", "m7b5").replace("+", "aug").replace("min", "m")
    if "m7b5" in s or "half" in s:
        return "m7b5"
    if s.startswith(("dim7", "o7")):
        return "dim7"
    if s.startswith("dim") or s == "o":
        return "dim"
    if s.startswith("aug"):
        return "aug"
    if s.startswith("sus2"):
        return "sus2"
    if s.startswith("sus"):
        return "sus4"
    if s.startswith("m") and not s.startswith("maj"):
        minor = True
    elif s.startswith("maj"):
        minor = False
    if any(d in s for d in ("7", "9", "11", "13")):
        return "m7" if minor else "7"
    return "min" if minor else "maj"


def parse_chord(token, tonic, mode):
    """One chord symbol or roman numeral -> (root pitch class, quality), or None."""
    tok = token.strip().split("/")[0]  # slash chords: ignore the bass note
    if not tok:
        return None
    m = re.match(r"^([A-G])([#b♯♭]?)(.*)$", tok)
    if m:
        root = (NOTE_PC[m.group(1)] + _accidental(m.group(2))) % 12
        return root, _quality_from_suffix(m.group(3), minor=False)
    m = re.match(r"^([#b♯♭]?)(" + "|".join(ROMAN) + r")(.*)$", tok, re.I)
    if m:
        numeral = m.group(2)
        degree = ROMAN_DEGREE[numeral.lower()]
        if m.group(1):  # explicit accidental: relative to the major scale (bVII, #iv)
            offset = MODES["major"][degree] + _accidental(m.group(1))
        else:  # plain numeral: a degree of the key's own mode (VI in minor = b6)
            offset = MODES[mode][degree]
        quality = _quality_from_suffix(m.group(3), minor=numeral.islower())
        return (tonic + offset) % 12, quality
    return None


def parse_progression(text, tonic, mode):
    tokens = re.split(r"[\s,|\-–—→>]+", str(text or ""))
    chords = []
    for t in tokens:
        if t.lower() in ("e.g.", "eg", "e.g"):
            continue
        c = parse_chord(t, tonic, mode)
        if c:
            chords.append(c)
    return chords


def chord_name(root, quality):
    return PC_NAME[root] + QUALITY_SUFFIX[quality]


def section_style(name):
    n = name.lower()
    for style, words in (
        ("intro", ("intro",)),
        ("outro", ("outro", "end", "fade")),
        ("hook", ("hook", "chorus", "drop", "refrain")),
        ("bridge", ("bridge", "break", "interlude", "breakdown")),
        ("build", ("pre", "build", "lift")),
    ):
        if any(w in n for w in words):
            return style
    return "verse"


# ---------------------------------------------------------------------------
# Writing parts
# ---------------------------------------------------------------------------

def voice(root, quality, prev):
    """Close voicing near middle C with the smallest move from the previous chord."""
    pcs = [(root + i) % 12 for i in QUALITIES[quality]]
    best, best_cost = None, None
    for inv in range(len(pcs)):
        order = pcs[inv:] + pcs[:inv]
        for base in range(48, 66):  # lowest note between C3 and F4
            if base % 12 != order[0]:
                continue
            notes, last = [], None
            for pc in order:
                n = base if last is None else last + ((pc - last) % 12 or 12)
                notes.append(n)
                last = n
            if notes[-1] > 79:
                continue
            if prev:
                cost = sum(min(abs(n - p) for p in prev) for n in notes)
            else:
                cost = abs(sum(notes) / len(notes) - 62)  # first chord: centre on D4
            if best_cost is None or cost < best_cost:
                best, best_cost = notes, cost
    return best


def bass_key(root):
    """Root in E1..D#2 (MIDI 28-39), the 808's sweet spot."""
    return 28 + (root - 4) % 12


def _drums(style, bar, last_bar, notes):
    add = lambda inst, step, vel, ln=1: notes.append([inst, bar, step, ln, 60, vel])
    if style in ("intro", "bridge"):
        if style == "intro" and not last_bar:
            for s in range(0, STEPS, 4):
                add("hat", s, 58)
        return
    if style == "outro":
        if bar == 0:
            add("crash", 0, 90)
        if not last_bar:
            add("kick", 0, 100)
            add("snare", 8, 92)
        return
    hook = style == "hook"
    kicks = [0, 7, 10] if hook else [0, 10]
    for s in kicks:
        add("kick", s, 118 if s == 0 else 100)
    for s in (4, 12):
        add("snare", s, 112)
        add("clap", s, 100 if hook else 76)
    step = 1 if hook else 2
    for s in range(0, STEPS, step):
        vel = 92 if s % 4 == 0 else (70 if s % 2 == 0 else 54)
        add("hat", s, vel)
    if hook and bar % 2 == 1:
        add("ohat", 14, 72)
    if hook and bar == 0:
        add("crash", 0, 96)
    if style == "build" and last_bar:  # snare roll into the next section
        for s in range(8, STEPS):
            add("snare", s, 60 + (s - 8) * 6)


def _section_notes(style, voicings, roots, bars):
    notes = []
    for b in range(bars):
        last_bar = b == bars - 1
        keys_vel = {"intro": 72, "verse": 80, "build": 84, "hook": 90, "bridge": 76, "outro": 70}[style]
        for k in voicings[b]:
            notes.append(["keys", b, 0, STEPS, k, keys_vel])
        if style in ("hook", "bridge", "outro"):
            for k in voicings[b][:3]:
                notes.append(["pad", b, 0, STEPS, k + 12, 64 if style == "hook" else 56])
        bk = bass_key(roots[b])
        if style in ("verse", "build", "hook"):
            notes.append(["bass", b, 0, 6, bk, 100])
            notes.append(["bass", b, 10, 6 if style == "hook" else 4, bk, 92])
        elif style in ("bridge", "outro") and not last_bar:
            notes.append(["bass", b, 0, STEPS, bk, 84])
        _drums(style, b, last_bar, notes)
    return notes


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def plan_from_theory(theory):
    data = _load_theory(theory)
    warnings = []
    if not data:
        warnings.append("theory result was not valid JSON; using defaults")

    try:
        bpm = float(data.get("bpm", 90))
    except (TypeError, ValueError):
        warnings.append(f"bad bpm {data.get('bpm')!r}; using 90")
        bpm = 90.0
    if not BPM_RANGE[0] <= bpm <= BPM_RANGE[1]:
        clamped = min(max(bpm, BPM_RANGE[0]), BPM_RANGE[1])
        warnings.append(f"bpm {bpm:g} out of range; using {clamped:g}")
        bpm = clamped

    key = parse_key(data.get("key"))
    if key is None:
        warnings.append(f"could not read key {data.get('key')!r}; using C major")
        key = (0, "major")
    tonic, mode = key
    minor = mode in MINOR_LIKE

    ts = str(data.get("time_signature", "4/4")).replace(" ", "")
    if ts not in ("4/4", ""):
        warnings.append(f"time signature {ts} not supported; rendering in 4/4")

    chords = parse_progression(data.get("chord_progression"), tonic, mode)
    if not chords:
        warnings.append(f"could not read chord progression {data.get('chord_progression')!r}; "
                        f"using {DEFAULT_PROGRESSION[minor]}")
        chords = parse_progression(DEFAULT_PROGRESSION[minor], tonic, mode)

    structure = []
    for s in data.get("structure") or []:
        if not isinstance(s, dict):
            continue
        name = str(s.get("section") or s.get("name") or "Verse").strip() or "Verse"
        try:
            bars = int(s.get("bars", 8))
        except (TypeError, ValueError):
            bars = 8
        bars = min(max(bars, 1), MAX_SECTION_BARS)
        structure.append((name, bars))
    if not structure:
        warnings.append("no usable structure; using the default layout")
        structure = list(DEFAULT_STRUCTURE)
    total, trimmed = 0, []
    for name, bars in structure:
        if total + bars > MAX_TOTAL_BARS:
            warnings.append(f"song longer than {MAX_TOTAL_BARS} bars; dropped from {name!r} on")
            break
        trimmed.append((name, bars))
        total += bars
    structure = trimmed

    bar_seconds = 240.0 / bpm
    sections, start, prev_voicing, chord_i = [], 0, None, 0
    vocal_start = None
    for name, bars in structure:
        style = section_style(name)
        bar_chords, voicings, roots = [], [], []
        for _ in range(bars):
            root, quality = chords[chord_i % len(chords)]
            chord_i += 1
            v = voice(root, quality, prev_voicing)
            prev_voicing = v
            bar_chords.append(chord_name(root, quality))
            voicings.append(v)
            roots.append(root)
        if vocal_start is None and style != "intro":
            vocal_start = start * bar_seconds
        sections.append({
            "name": name, "style": style, "start_bar": start, "bars": bars,
            "chords": bar_chords,
            "notes": _section_notes(style, voicings, roots, bars),
        })
        start += bars

    return {
        "bpm": bpm,
        "key": f"{PC_NAME[tonic]} {mode}",
        "tonic": tonic,
        "mode": mode,
        "bar_seconds": round(bar_seconds, 4),
        "bars": start,
        "seconds": round(start * bar_seconds, 2),
        "vocal_start_seconds": round(vocal_start or 0.0, 2),
        "sections": sections,
        "warnings": warnings,
    }
