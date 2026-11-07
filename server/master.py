"""Master agent: the synthesizer.

The searchers (workers) post version-diff findings to the coordinator. The
master pulls those collected results, hands them to the local model with the
master differentiation prompt, and emits the vulnerability report.

The model call itself lives in model.py (stub until Ollama is wired).
"""
import json
import os
import time

import requests

from model import call_model
from prompts import build_system_prompt

SERVER = os.environ.get("SERVER", "http://localhost:5000")
MASTER_MODEL = os.environ.get("MASTER_MODEL", "qwen2.5:14b")

# This node is the master. Assemble its system prompt once (universal prompt +
# master differentiation prompt).
SYSTEM_PROMPT = build_system_prompt("master")


def collect(server):
    """Pull everything the searchers have reported so far."""
    r = requests.get(f"{server}/status", timeout=10)
    r.raise_for_status()
    return r.json()


def synthesize(status):
    """Hand the collected searcher findings to the model as the master."""
    user_prompt = json.dumps(
        {
            "instruction": (
                "Merge the subagent version-diff findings below and produce the "
                "verified vulnerability report per your master prompt."
            ),
            "results": status.get("results", {}),
        },
        indent=2,
    )
    return call_model(SYSTEM_PROMPT, user_prompt, MASTER_MODEL)


def main():
    print(f"master online; watching {SERVER}")
    while True:
        try:
            status = collect(SERVER)
        except requests.RequestException as e:
            print(f"coordinator unreachable ({e}); retrying...")
            time.sleep(3)
            continue

        done, queued, running = status["done"], status["queued"], status["in_progress"]
        if done > 0 and queued == 0 and running == 0:
            print(f"all {done} searcher tasks in; synthesizing report")
            print(synthesize(status))
            return

        print(f"waiting: queued={queued} in_progress={running} done={done}")
        time.sleep(3)


if __name__ == "__main__":
    main()
