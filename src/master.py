"""Master: build tasks from the diff, serve them to workers over the LAN,
collect the results, then synthesize the final vulnerability report.

Run on the coordinator machine via `start.bat -master`. It also runs one local
worker thread, so the master machine analyzes too.

Target (env, defaults to the bundled synthetic fixture):
  VERSION_A_DIR / VERSION_B_DIR   the two versions (directories or files)
  VERSION_A / VERSION_B           human labels for them
"""
import json
import logging
import os
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request

import diff
import worker
from model import ask

PORT = int(os.environ.get("COORD_PORT", "8765"))
LEASE = int(os.environ.get("LEASE_SECS", "120"))  # requeue a task idle this long
ROOT = Path(__file__).resolve().parent.parent
PROMPT = (ROOT / "prompts" / "master.md").read_text("utf-8")

VERSION_A = os.environ.get("VERSION_A", "sample_vA")
VERSION_B = os.environ.get("VERSION_B", "sample_vB")
DIR_A = os.environ.get("VERSION_A_DIR", str(ROOT / "fixtures" / "sample_vA"))
DIR_B = os.environ.get("VERSION_B_DIR", str(ROOT / "fixtures" / "sample_vB"))

app = Flask(__name__)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
lock = threading.Lock()
queue = []        # tasks not yet handed out
inflight = {}     # id -> (task, assigned_at)
results = {}      # id -> result text
total = 0


@app.get("/task")
def get_task():
    with lock:
        if not queue:
            return jsonify({"task": None})
        task = queue.pop(0)
        inflight[task["id"]] = (task, time.time())
        return jsonify({"task": task})


@app.post("/result")
def post_result():
    d = request.get_json()
    with lock:
        if d["id"] not in results:
            results[d["id"]] = d["result"]
        inflight.pop(d["id"], None)
    print(f"[{len(results)}/{total}] result in: {d['id']}")
    return jsonify({"ok": True})


@app.get("/status")
def status():
    with lock:
        return jsonify({"total": total, "queued": len(queue),
                        "inflight": len(inflight), "done": len(results)})


def _requeue_loop():
    while True:
        time.sleep(5)
        now = time.time()
        with lock:
            for tid, (task, at) in list(inflight.items()):
                if now - at > LEASE:
                    print(f"requeue {tid} (worker went quiet)")
                    queue.append(task)
                    inflight.pop(tid, None)


def main():
    global total
    tasks = diff.build_tasks(DIR_A, DIR_B, VERSION_A, VERSION_B)
    with lock:
        queue.extend(tasks)
        total = len(tasks)
    print(f"{VERSION_A} -> {VERSION_B}: {total} changed files to analyze")
    if not total:
        print("no changes between the two versions; nothing to do")
        return

    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=PORT),
                     daemon=True).start()
    threading.Thread(target=_requeue_loop, daemon=True).start()
    threading.Thread(target=lambda: worker.run(f"http://localhost:{PORT}"),
                     daemon=True).start()

    while True:
        with lock:
            done, q, inf = len(results), len(queue), len(inflight)
        if done >= total:
            break
        print(f"waiting: done={done} queued={q} inflight={inf}")
        time.sleep(3)

    print("\nall tasks in; synthesizing report\n")
    report = ask(PROMPT, json.dumps(
        {"versions": [VERSION_A, VERSION_B], "results": results}, indent=2))
    (ROOT / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"\n--- report.md written to {ROOT / 'report.md'} ---")


if __name__ == "__main__":
    main()
