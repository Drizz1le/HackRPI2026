"""Master: collect the theory style prompt + the lyrics, then render the song.

Waits until both the theory and lyrics results are in, builds a text-to-music
request from the theory style_prompt plus the lyrics, calls the ElevenLabs Music
API, and saves the audio to the output directory.

Stub mode: if ELEVENLABS_API_KEY is not set, no API call is made. A placeholder
text file is written instead so the whole pipeline runs end to end without
spending credits.
"""
import json
import os
import time
from pathlib import Path

import requests

SERVER = os.environ.get("SERVER", "http://localhost:5000")

# Shared secret sent to the coordinator; must match its SWARM_TOKEN.
TOKEN = os.environ.get("SWARM_TOKEN", "")
HEADERS = {"X-Swarm-Token": TOKEN} if TOKEN else {}

MODEL_ID = os.environ.get("MUSIC_MODEL_ID", "music_v2_5")
SONG_LENGTH_MS = int(os.environ.get("SONG_LENGTH_MS", "75000"))  # ~75s MVP
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "output"))
API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")


def collect():
    r = requests.get(f"{SERVER}/status", headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


def _by_role(results):
    """results is {task_id: {role, result}}. Return {role: result_text}."""
    out = {}
    for v in results.values():
        if isinstance(v, dict) and v.get("role"):
            out[v["role"]] = v.get("result", "")
    return out


def _strip_fences(text):
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    return t.strip()


def style_prompt_from_theory(theory_text):
    """Pull the style_prompt out of the theory JSON; fall back to raw text."""
    try:
        plan = json.loads(_strip_fences(theory_text))
        if isinstance(plan, dict) and plan.get("style_prompt"):
            return str(plan["style_prompt"])
    except (ValueError, TypeError):
        pass
    return (theory_text or "").strip()


def build_prompt(theory_text, lyrics_text):
    style = style_prompt_from_theory(theory_text)
    return f"{style}\n\nUse these lyrics, following the section markers:\n\n{lyrics_text}"


def render(prompt):
    """Produce the song. Real API when a key is set, else a stub placeholder.
    Returns the path written."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not API_KEY:
        path = OUTPUT_DIR / "song.txt"
        path.write_text(
            "[STUB] ELEVENLABS_API_KEY not set; no audio generated.\n\n"
            "The request that WOULD have been sent to ElevenLabs Music:\n"
            f"  model_id: {MODEL_ID}\n"
            f"  music_length_ms: {SONG_LENGTH_MS}\n\n"
            f"prompt:\n{prompt}\n",
            encoding="utf-8",
        )
        print(f"[stub] wrote placeholder (no API key) -> {path}")
        return path

    # Real call. Imported here so stub mode needs no SDK installed.
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=API_KEY)
    try:
        track = client.music.compose(
            prompt=prompt,
            music_length_ms=SONG_LENGTH_MS,
            model_id=MODEL_ID,
        )
    except Exception as e:
        # Fail loudly but don't crash the run: dump the request for debugging.
        path = OUTPUT_DIR / "song_error.txt"
        path.write_text(f"ElevenLabs request failed: {e}\n\nprompt:\n{prompt}\n",
                        encoding="utf-8")
        print(f"[error] ElevenLabs call failed: {e}; request saved -> {path}")
        return path

    path = OUTPUT_DIR / "song.mp3"
    with open(path, "wb") as f:
        for chunk in track:  # compose() returns an iterator of audio chunks
            f.write(chunk)
    print(f"[done] wrote song -> {path}")
    return path


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
            print("theory + lyrics in; rendering song")
            prompt = build_prompt(roles["theory"], roles["lyrics"])
            render(prompt)
            return

        have = ", ".join(sorted(roles)) or "nothing yet"
        print(f"waiting: have {have}")
        time.sleep(3)


if __name__ == "__main__":
    main()
