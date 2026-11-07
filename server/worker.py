import json, os, requests, time

from model import call_model
from prompts import THEORY_PROMPT, LYRICS_PROMPT

# ---- point this at the coordinator's address (LAN IP, or the Vultr public IP) ----
SERVER = os.environ.get("SERVER", "http://192.168.1.50:5000")
WORKER_MODEL = os.environ.get("WORKER_MODEL", "qwen2.5:3b")
# Optional one-line brief seeding the theory agent.
SONG_BRIEF = os.environ.get("SONG_BRIEF", "Create an original song of your choice.")

# Shared secret sent to the coordinator; must match its SWARM_TOKEN.
TOKEN = os.environ.get("SWARM_TOKEN", "")
HEADERS = {"X-Swarm-Token": TOKEN} if TOKEN else {}


def register():
    """Keep trying until the coordinator is reachable (it may start after us)."""
    while True:
        try:
            return requests.post(
                f"{SERVER}/register", headers=HEADERS, timeout=10
            ).json()["node_id"]
        except requests.RequestException as e:
            print(f"can't reach coordinator at {SERVER} ({e}); retrying...")
            time.sleep(3)


def run_task(task):
    """Run one role task through the local model.

    theory -> composition plan JSON (+ a style_prompt string)
    lyrics -> section-marked lyrics that follow the theory's section layout
    """
    role = task.get("role")
    if role == "theory":
        return call_model(THEORY_PROMPT, SONG_BRIEF, WORKER_MODEL)
    if role == "lyrics":
        user = "Composition plan to write lyrics for:\n" + str(task.get("theory", ""))
        return call_model(LYRICS_PROMPT, user, WORKER_MODEL)
    return json.dumps({"error": f"unknown role {role!r}"})


def main():
    node_id = register()
    print(f"registered as {node_id}, pulling tasks from {SERVER}")
    while True:
        try:
            r = requests.get(
                f"{SERVER}/task", params={"node_id": node_id},
                headers=HEADERS, timeout=10,
            ).json()
        except requests.RequestException as e:
            print(f"server unreachable ({e}); retrying...")
            time.sleep(3)
            continue

        if r["status"] == "none":
            time.sleep(2)
            continue  # queue empty, wait and ask again

        task = r["task"]
        try:
            result = run_task(task)
        except Exception as e:  # model/network error: report it, keep going
            result = json.dumps({"error": f"worker error: {e}"})
        try:
            requests.post(
                f"{SERVER}/result",
                json={
                    "task_id": task["task_id"],
                    "node_id": node_id,
                    "role": task.get("role"),
                    "result": result,
                },
                headers=HEADERS, timeout=30,
            )
            print(f"did {task.get('role')} {task['task_id'][:8]} -> {str(result)[:60]}")
        except requests.RequestException as e:
            print(f"could not post result for {task['task_id'][:8]} ({e})")


if __name__ == "__main__":
    main()
