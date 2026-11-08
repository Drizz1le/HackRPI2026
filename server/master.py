"""Master: render spoken vocals from the lyrics (Fish Audio TTS), then mix them
over the teammate's instrumental and save the final track.

Flow once every role the coordinator expects is in (theory + lyrics, plus
instrumental when the coordinator runs with INSTRUMENTAL=1):
  1. TTS the lyrics -> output/vocals.mp3 (Fish Audio).
  2. Pick the instrumental: the WAV the instrumental worker rendered in FL
     Studio, else input/instrumental.(wav|mp3) if present.
  3. Overlay the vocals on it (instrumental ducked a few dB), starting where
     the arrangement's intro ends -> output/song.mp3. With no instrumental the
     vocals alone become output/song.mp3.

Stub mode: if FISH_API_KEY is unset, no TTS call is made. A placeholder is
written so the pipeline still completes end to end without a key.
"""
import json
import os
import shutil
import time
from pathlib import Path

import requests

from lyrics_clean import clean_lyrics, speech_text

SERVER = os.environ.get("SERVER", "http://localhost:5000")

# Shared secret sent to the coordinator; must match its SWARM_TOKEN.
TOKEN = os.environ.get("SWARM_TOKEN", "")
HEADERS = {"X-Swarm-Token": TOKEN} if TOKEN else {}

API_KEY = os.environ.get("FISH_API_KEY", "")
VOICE_ID = os.environ.get("FISH_VOICE", "")  # optional reference_id
# Fish Audio TTS model, passed as the `backend` kwarg of session.tts().
FISH_MODEL = os.environ.get("FISH_MODEL", "s2.1-pro-free")
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

    # Verified live against fish-audio-sdk: Session(api_key).tts(TTSRequest(...),
    # backend=<model>) returns an iterator of audio chunks. The model is the
    # `backend` kwarg (TTSRequest has no model field). Wrapped per spec: on any
    # error dump the request and return None rather than crashing the run.
    path = OUTPUT_DIR / "vocals.mp3"
    try:
        from fish_audio_sdk import Session, TTSRequest

        session = Session(API_KEY)
        # [Section] markers are layout, not speech; strip them for TTS.
        kwargs = {"text": speech_text(lyrics), "format": "mp3"}
        if VOICE_ID:
            kwargs["reference_id"] = VOICE_ID
        request = TTSRequest(**kwargs)
        with open(path, "wb") as f:
            for chunk in session.tts(request, backend=FISH_MODEL):
                f.write(chunk)
        print(f"[tts] wrote vocals ({FISH_MODEL}) -> {path}")
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


def rendered_instrumental(result):
    """Parse the instrumental worker's result -> (wav path, vocal start ms), or None."""
    if not result:
        return None
    try:
        info = json.loads(result)
    except (TypeError, ValueError):
        print("[instrumental] result is not JSON; ignoring it")
        return None
    if info.get("error"):
        print(f"[instrumental] worker failed: {info['error']}")
        return None
    for w in info.get("warnings", []):
        print(f"[instrumental] warning: {w}")
    wav = Path(info.get("wav", ""))
    if not wav.is_file():
        print(f"[instrumental] rendered WAV not found at {wav} (the master must "
              "run on the same machine as the instrumental worker)")
        return None
    return wav, int(float(info.get("vocal_start_seconds", 0)) * 1000)


def find_instrumental(rendered=None):
    """-> (path, vocal start ms) or None. The FL render wins over input/."""
    if rendered:
        return rendered
    for ext in ("wav", "mp3"):
        p = INPUT_DIR / f"instrumental.{ext}"
        if p.is_file():
            return p, 0
    return None


def mix(vocals_path, instrumental=None):
    """Overlay vocals on the instrumental if present, else vocals alone."""
    if vocals_path is None:
        print("[mix] no vocals audio (stub or TTS failure); nothing to mix")
        return None

    out = OUTPUT_DIR / "song.mp3"
    if instrumental is None:
        shutil.copyfile(vocals_path, out)
        print(f"[mix] no instrumental (none rendered, none in {INPUT_DIR}/); vocals alone -> {out}")
        return out
    inst, start_ms = instrumental

    try:
        from pydub import AudioSegment

        vocals = AudioSegment.from_file(vocals_path)
        bed = AudioSegment.from_file(inst) - DUCK_DB  # duck the instrumental
        need = start_ms + len(vocals)
        if len(bed) < need:  # pad so the vocals aren't clipped
            bed = bed + AudioSegment.silent(duration=need - len(bed))
        mixed = bed.overlay(vocals, position=start_ms)
        mixed.export(out, format="mp3")
        print(f"[mix] overlaid vocals on {inst.name} at {start_ms / 1000:.1f}s -> {out}")
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
        expected = status.get("expected") or ["theory", "lyrics"]
        if all(r in roles for r in expected):
            print(f"{' + '.join(expected)} in; rendering vocals and mixing")
            instrumental = find_instrumental(rendered_instrumental(roles.get("instrumental")))
            # Drop preamble and production cues so TTS only speaks lyrics.
            lyrics = clean_lyrics(roles["lyrics"])
            vocals = tts_vocals(lyrics)
            if vocals is None:
                # stub mode or TTS failure: still emit a song.* so the pipeline
                # completes with a deliverable.
                placeholder = OUTPUT_DIR / "song.txt"
                inst_note = (f"Instrumental: {instrumental[0]}\n\n" if instrumental
                             else "No instrumental.\n\n")
                placeholder.write_text(
                    "[PLACEHOLDER] no vocal audio produced (stub mode or TTS "
                    "failure).\n" + inst_note + "Lyrics:\n\n" + lyrics,
                    encoding="utf-8",
                )
                print(f"[placeholder] wrote {placeholder}")
            else:
                mix(vocals, instrumental)
            print("done")
            return

        have = ", ".join(sorted(roles)) or "nothing yet"
        print(f"waiting: have {have}; need {', '.join(expected)}")
        time.sleep(3)


if __name__ == "__main__":
    main()
