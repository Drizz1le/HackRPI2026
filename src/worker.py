"""Worker: pull one diff task, analyze it with the local model, post the result.

Runs on every machine. SERVER points at the master; start.bat sets it to
http://<master-ip>:5000 on remote machines, and the master runs one of these
against localhost itself.
"""
import json
import os
import time
from pathlib import Path

import requests

from model import ask

SERVER = os.environ.get("SERVER", "http://localhost:5000")
PROMPT = (Path(__file__).resolve().parent.parent / "prompts" / "worker.md").read_text("utf-8")


def analyze(task):
    return ask(PROMPT, json.dumps(task, indent=2))


def run(server):
    print(f"worker -> {server}")
    while True:
        try:
            task = requests.get(f"{server}/task", timeout=10).json().get("task")
        except requests.RequestException as e:
            print(f"waiting for coordinator ({e})")
            time.sleep(3)
            continue
        if not task:
            time.sleep(2)
            continue
        try:
            result = analyze(task)
        except Exception as e:  # model/network error: report it, keep going
            result = json.dumps({"summary": f"worker error: {e}", "findings": []})
        try:
            requests.post(f"{server}/result",
                          json={"id": task["id"], "result": result}, timeout=30)
            print(f"done {task['id']} {task['path']}")
        except requests.RequestException as e:
            print(f"could not post result for {task['id']} ({e})")


if __name__ == "__main__":
    run(SERVER)
