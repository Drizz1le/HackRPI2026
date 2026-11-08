"""Render a cluster arrangement to audio with FL Studio (Windows + FL Studio 2025 only).

The instrumental role of the agent cluster calls render(plan, out_dir). `plan`
comes from server/arrange.py: tempo, key, and per-section notes for keys, pad,
bass and drums. This builds a .flp with flpbuild (one pattern per section, laid
out on the playlist in order) and renders it with FL's command line:

    FL64.exe /R /Ewav <project>.flp

No mouse, no MIDI bridge: the CLI renderer only needs FL to be CLOSED. If FL
is open, render() refuses instead of killing it (that would lose unsaved work).

Sounds are the ones Ben's songs already load successfully:
  keys  Harmor Rhodes (FL Keys Concert Piano if the plan's instrumentation says piano)
  pad   Kepler "J106 Brass & Strings softer"
  bass  Dope Tec [808] Clean (Sampler, transposed by its detected root)
  drums Graduation / MBDTF kits from Documents\\FLStudio
A missing preset or sample is skipped with a warning rather than failing the
song. Override locations with FL_DIR and FL_KIT_DIR.

Standalone test on the FL machine:
    python cluster_render.py theory.json [out_dir]
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flpbuild  # noqa: E402
from flpbuild import BAR, Project, preset  # noqa: E402

FL_DIR = os.environ.get("FL_DIR", r"C:\Program Files\Image-Line\FL Studio 2025")
FL_EXE = os.path.join(FL_DIR, "FL64.exe")
KIT = os.environ.get("FL_KIT_DIR", os.path.join(os.path.expanduser("~"), "Documents", "FLStudio"))
STEP = BAR // 16  # ticks per 16th note
RENDER_TIMEOUT = int(os.environ.get("FL_RENDER_TIMEOUT", "900"))

# flpbuild reads FL's template and presets from its own constants; point them at FL_DIR.
flpbuild.FL = FL_DIR
flpbuild.TEMPLATE = os.path.join(FL_DIR, r"Data\Templates\Minimal\Empty\Empty.flp")
flpbuild.PRESETS = os.path.join(FL_DIR, r"Data\Patches\Plugin presets")

PLUGINS = {
    "keys": r"Harmor\Keyboard\Rhodes.fst",
    "piano": r"FL Keys\Concert Piano.fst",
    "pad": r"Kepler\Synths\J106 Brass & Strings softer.fst",
}
SAMPLES = {
    "kick": r"Graduation\Kicks\Kick (Homecoming).wav",
    "snare": r"Graduation\Snares\Snare (Good Morning).wav",
    "clap": r"Graduation\Claps\Clap (Flashing Lights).wav",
    "hat": r"Graduation\Hats\Hi Hat (Stronger).wav",
    "ohat": r"Graduation\Hats\Open Hat (Barry Bonds).wav",
    "crash": r"MBDTF Drum Kit\Hats\Crash (Devil In A New Dress).wav",
    "bass": r"Dope Tec\-808s & Bass\[808] Clean.wav",
}
DEFAULT_808_ROOT = 33  # A1 (55 Hz), same fallback as send.py


def _fl_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FL64.exe", "/NH"],
                         capture_output=True, text=True).stdout
    return "FL64.exe" in out


def _detect_root(path):
    """Pitch of the 808 sample, so bass notes can be transposed onto the chord roots."""
    try:
        import librosa
        import numpy as np
        y, sr = librosa.load(path, sr=22050, duration=1.0)
        f0, voiced, _ = librosa.pyin(y, fmin=30, fmax=200, sr=sr)
        if np.any(voiced):
            return int(round(librosa.hz_to_midi(np.nanmedian(f0[voiced]))))
    except Exception as e:  # librosa missing or analysis failed
        print(f"[render] 808 root detection failed ({e}); assuming A1")
    return DEFAULT_808_ROOT


def _normalize(wav, peak_db=-1.0):
    """Peak-normalize the render so it sits at a known level under the vocals."""
    try:
        import numpy as np
        import soundfile as sf
        y, sr = sf.read(wav, always_2d=True)
        peak = float(np.max(np.abs(y))) if y.size else 0.0
        if peak > 0:
            sf.write(wav, y * (10 ** (peak_db / 20) / peak), sr, subtype="PCM_16")
        return peak
    except Exception as e:
        print(f"[render] normalize skipped ({e})")
        return None


def build(plan, flp_path, instrumentation=()):
    """Write the .flp for `plan`. Returns (path, warnings)."""
    warnings = []
    pr = Project(tempo=float(plan["bpm"]))
    ch = {}

    keys_preset = PLUGINS["keys"]
    if any("piano" in str(i).lower() for i in instrumentation):
        keys_preset = PLUGINS["piano"]
    for name, rel in (("keys", keys_preset), ("pad", PLUGINS["pad"])):
        try:
            ch[name] = pr.plugin(name.capitalize(), preset("Generators", rel))
        except (FileNotFoundError, AssertionError) as e:
            warnings.append(f"{name}: preset {rel} not usable ({e}); part skipped")

    bass_root = DEFAULT_808_ROOT
    for name, rel in SAMPLES.items():
        path = os.path.join(KIT, rel)
        if not os.path.isfile(path):
            warnings.append(f"{name}: sample not found at {path}; part skipped")
            continue
        ch[name] = pr.sampler(name.capitalize(), path)
        if name == "bass":
            bass_root = _detect_root(path)

    if "keys" not in ch:
        raise RuntimeError("no keys instrument available; can't render a song with no chords. "
                           + "; ".join(warnings))

    for sec in plan["sections"]:
        notes = []
        for inst, bar, step, ln, key, vel in sec["notes"]:
            if inst not in ch:
                continue
            if inst == "bass":
                key = 60 + (key - bass_root)  # Sampler plays its root at key 60
            notes.append((ch[inst], bar * BAR + step * STEP, ln * STEP, key, vel))
        if not notes:
            continue
        pat = pr.pattern(sec["name"], notes)
        pr.clip(pat, sec["start_bar"], 0, sec["bars"])

    pr.save(flp_path)
    return flp_path, warnings


def render(plan, out_dir, name="Cluster Song", instrumentation=()):
    """Build and render. Returns a JSON-able dict with the WAV path and timing."""
    os.makedirs(out_dir, exist_ok=True)
    flp_path = os.path.join(os.path.abspath(out_dir), name + ".flp")
    wav = flp_path[:-4] + ".wav"

    if not os.path.isfile(FL_EXE):
        raise RuntimeError(f"FL Studio not found at {FL_EXE}; set FL_DIR")
    if _fl_running():
        raise RuntimeError("FL Studio is open; close it so the command-line renderer can run")

    _, warnings = build(plan, flp_path, instrumentation)
    if os.path.exists(wav):
        os.remove(wav)

    t = time.time()
    subprocess.run([FL_EXE, "/R", "/Ewav", flp_path], timeout=RENDER_TIMEOUT)
    # The renderer can hand off to a child process: wait for the WAV and for FL to exit.
    deadline = time.time() + RENDER_TIMEOUT
    while time.time() < deadline:
        if os.path.exists(wav) and not _fl_running():
            break
        time.sleep(2)
    if not os.path.exists(wav):
        raise RuntimeError("FL render produced no WAV")

    peak = _normalize(wav)
    return {
        "wav": wav,
        "flp": flp_path,
        "bpm": plan["bpm"],
        "key": plan["key"],
        "bars": plan["bars"],
        "seconds": plan["seconds"],
        "vocal_start_seconds": plan["vocal_start_seconds"],
        "render_seconds": round(time.time() - t, 1),
        "raw_peak": peak,
        "warnings": plan.get("warnings", []) + warnings,
    }


if __name__ == "__main__":
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(repo, "server"))
    from arrange import plan_from_theory

    theory = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(repo, "output")
    info = render(plan_from_theory(theory), out, instrumentation=theory.get("instrumentation", ()))
    print(json.dumps(info, indent=1))
