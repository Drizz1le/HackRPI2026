"""Master: render spoken vocals from the lyrics (Fish Audio TTS), then mix them
over the teammate's instrumental and save the final track.

Flow once both theory and lyrics results are in:
  1. TTS the lyrics -> output/vocals.mp3 (Fish Audio).
  2. If input/instrumental.(wav|mp3) exists, overlay the vocals on top of it
     (instrumental ducked a few dB) -> output/song.mp3. Otherwise the vocals
     alone become output/song.mp3.

Stub mode: if FISH_API_KEY is unset, no TTS call is made. A placeholder is
written so the pipeline still completes end to end without a key.
"""
import os
import shutil
import time
from pathlib import Path

import requests

SERVER = os.environ.get("SERVER", "http://localhost:5000")

# Shared secret sent to the coordinator; must match its SWARM_TOKEN.
TOKEN = os.environ.get("SWARM_TOKEN", "")
HEADERS = {"X-Swarm-Token": TOKEN} if TOKEN else {}

API_KEY = os.environ.get("FISH_API_KEY", "")
VOICE_ID = os.environ.get("FISH_VOICE", "")  # optional reference_id
INPUT_DIR = Path(os.environ.get("INPUT_DIR", "input"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))
DUCK_DB = int(os.environ.get("DUCK_DB", "6"))  # lower instrumental under vocals


def collect():
    r = requests.get(f"{SERVER}/status", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def _by_role(results):
    out = {}
    for v in results.values():
        if isinstance(v, dict) and v.get("role"):
            out[v["role"]] = v.get("result", "")
    return out


def tts_vocals(lyrics):
    """Render spoken vocals to output/vocals.mp3. Returns the path, or None in
    stub mode or on failure. The Fish Audio call is wrapped so a missing key,
    missing package, or signature mismatch fails gracefully."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not API_KEY:
        path = OUTPUT_DIR / "vocals.txt"
        path.write_text(
            "[STUB] FISH_API_KEY not set; no TTS performed.\n\n"
            "Lyrics that WOULD have been spoken:\n\n" + lyrics,
            encoding="utf-8",
        )
        print(f"[stub] no FISH_API_KEY; wrote {path}")
        return None

    # Signature verified against the fish-audio-sdk (legacy) docs:
    #   Session(api_key).tts(TTSRequest(text=..., reference_id=..., format=...))
    # returns an iterator of audio chunks. Wrapped per spec: on any error dump
    # the request and return None rather than crashing the run.
    path = OUTPUT_DIR / "vocals.mp3"
    try:
        from fish_audio_sdk import Session, TTSRequest

        session = Session(API_KEY)
        kwargs = {"text": lyrics, "format": "mp3"}
        if VOICE_ID:
            kwargs["reference_id"] = VOICE_ID
        request = TTSRequest(**kwargs)
        with open(path, "wb") as f:
            for chunk in session.tts(request):
                f.write(chunk)
        print(f"[tts] wrote vocals -> {path}")
        return path
    except Exception as e:
        err = OUTPUT_DIR / "vocals_error.txt"
        err.write_text(
            f"Fish Audio TTS failed: {e}\n\nreference_id={VOICE_ID!r}\n\n"
            "lyrics:\n" + lyrics,
            encoding="utf-8",
        )
        print(f"[error] Fish Audio TTS failed: {e}; request saved -> {err}")
        return None


def find_instrumental():
    for ext in ("wav", "mp3"):
        p = INPUT_DIR / f"instrumental.{ext}"
        if p.is_file():
            return p
    return None


def mix(vocals_path):
    """Overlay vocals on the instrumental if present, else vocals alone."""
    if vocals_path is None:
        print("[mix] no vocals audio (stub or TTS failure); nothing to mix")
        return None

    out = OUTPUT_DIR / "song.mp3"
    inst = find_instrumental()
    if inst is None:
        shutil.copyfile(vocals_path, out)
        print(f"[mix] no instrumental in {INPUT_DIR}/; vocals alone -> {out}")
        return out

    try:
        from pydub import AudioSegment

        vocals = AudioSegment.from_file(vocals_path)
        bed = AudioSegment.from_file(inst) - DUCK_DB  # duck the instrumental
        if len(bed) < len(vocals):  # pad so the vocals aren't clipped
            bed = bed + AudioSegment.silent(duration=len(vocals) - len(bed))
        mixed = bed.overlay(vocals)
        mixed.export(out, format="mp3")
        print(f"[mix] overlaid vocals on {inst.name} -> {out}")
        return out
    except Exception as e:
        shutil.copyfile(vocals_path, out)
        print(f"[mix] mix failed ({e}); fell back to vocals alone -> {out}")
        return out


def main():
    print(f"master online; watching {SERVER}")
    while True:
        try:
            status = collect()
        except requests.RequestException as e:
            print(f"coordinator unreachable ({e}); retrying...")
            time.sleep(3)
            continue

        roles = _by_role(status.get("results", {}))
        if "theory" in roles and "lyrics" in roles:
            print("theory + lyrics in; rendering vocals and mixing")
            vocals = tts_vocals(roles["lyrics"])
            if vocals is None:
                # stub mode or TTS failure: still emit a song.* so the pipeline
                # completes with a deliverable.
                placeholder = OUTPUT_DIR / "song.txt"
                placeholder.write_text(
                    "[PLACEHOLDER] no vocal audio produced (stub mode or TTS "
                    "failure). Lyrics:\n\n" + roles["lyrics"],
                    encoding="utf-8",
                )
                print(f"[placeholder] wrote {placeholder}")
            else:
                mix(vocals)
            print("done")
            return

        have = ", ".join(sorted(roles)) or "nothing yet"
        print(f"waiting: have {have}")
        time.sleep(3)


if __name__ == "__main__":
    main()
