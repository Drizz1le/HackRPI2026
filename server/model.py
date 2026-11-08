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
# Context window for Ollama. The lyrics prompt carries the composer guide
# (~2.5k tokens), which can overflow Ollama's small default and get truncated.
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))


def call_model(system_prompt, user_prompt, model):
    """Send one prompt to the local model and return its text response."""
    if MODEL_MODE == "ollama":
        return _call_ollama(system_prompt, user_prompt, model)
    return _call_stub(system_prompt, user_prompt, model)


def check_models(models):
    """Warn at startup if Ollama is unreachable or a model is not pulled.

    Only warns: the worker keeps running, so pulling the model afterwards
    (ollama pull <model>) fixes it without a restart. No-op in stub mode.
    """
    if MODEL_MODE != "ollama":
        return
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        r.raise_for_status()
        have = {m["name"] for m in r.json().get("models", [])}
    except requests.RequestException as e:
        print(f"warning: can't reach Ollama at {OLLAMA_HOST} ({e})")
        return
    for model in sorted(models):
        # Ollama lists untagged pulls as "<name>:latest".
        if model not in have and f"{model}:latest" not in have:
            print(f"warning: model {model!r} not found on {OLLAMA_HOST}; "
                  f"run: ollama pull {model}")


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
            "options": {"num_ctx": OLLAMA_NUM_CTX},
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
