"""The one place the local Qwen model is called.

Each machine runs its own server (llama-server, started by start.bat, exposing
the OpenAI-compatible API on :8080). Point elsewhere with MODEL_HOST.

MODEL_MODE=stub returns a canned reply so the LAN can be wired up and tested
with no model loaded.
"""
import json
import os

import requests

HOST = os.environ.get("MODEL_HOST", "http://localhost:8080")
MODE = os.environ.get("MODEL_MODE", "live").lower()
MODEL = os.environ.get("MODEL", "qwen")


def ask(system, user):
    """Send one system+user prompt to the local model, return the text reply."""
    if MODE == "stub":
        return json.dumps({"summary": "[stub] no model loaded", "findings": []})
    r = requests.post(
        f"{HOST}/v1/chat/completions",
        json={"model": MODEL, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]},
        timeout=600,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
