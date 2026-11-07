"""The single place the local model is called. Wire Ollama in here.

MODEL_MODE controls what call_model does:
  - "stub"   (default) returns a canned TaskResult-shaped reply so the whole
             cluster runs end to end without any model installed.
  - "ollama" sends the prompt to a local Ollama server over its HTTP API.

To go live: set MODEL_MODE=ollama and OLLAMA_HOST to the Ollama server. No
other code changes are needed; this function is the only wiring point.
"""
import json
import os

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_MODE = os.environ.get("MODEL_MODE", "stub").lower()


def call_model(system_prompt, user_prompt, model):
    """Send one prompt to the local model and return its text response."""
    if MODEL_MODE == "ollama":
        return _call_ollama(system_prompt, user_prompt, model)
    return _call_stub(system_prompt, user_prompt, model)


def _call_ollama(system_prompt, user_prompt, model):
    r = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        },
        timeout=600,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def _call_stub(system_prompt, user_prompt, model):
    """Deterministic placeholder so the pipeline runs without a model."""
    return json.dumps(
        {
            "status": "ok",
            "summary": f"[stub:{model}] model not wired; echoing task unprocessed",
            "findings": [],
            "evidence": [],
            "confidence": 0.0,
        }
    )
