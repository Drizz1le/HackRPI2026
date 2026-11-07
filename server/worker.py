import json, os, requests, time

from model import call_model
from prompts import build_system_prompt

# ---- point this at the coordinator computer's LAN IP (set via env var) ----
SERVER = os.environ.get("SERVER", "http://192.168.1.50:5000")
WORKER_MODEL = os.environ.get("WORKER_MODEL", "qwen2.5:3b")

# This node is a subagent: a searcher that finds version differences. Assemble
# its system prompt once (universal prompt + subagent differentiation prompt).
SYSTEM_PROMPT = build_system_prompt("subagent")


def register():
    """Keep trying until the coordinator is reachable (it may start after us)."""
    while True:
        try:
            return requests.post(f"{SERVER}/register", timeout=10).json()["node_id"]
        except requests.RequestException as e:
            print(f"can't reach coordinator at {SERVER} ({e}); retrying...")
            time.sleep(3)


def run_task(task):
    """Run one bounded task through the local model as a searcher.

    The task envelope is handed to the model as the user message; the model
    replies with a TaskResult (version-diff findings) following the subagent
    prompt. The model call itself lives in model.py.
    """
    user_prompt = json.dumps(task, indent=2)
    return call_model(SYSTEM_PROMPT, user_prompt, WORKER_MODEL)


def main():
    node_id = register()
    print(f"registered as {node_id}, pulling tasks from {SERVER}")
    while True:
        try:
            r = requests.get(
                f"{SERVER}/task", params={"node_id": node_id}, timeout=10
            ).json()
        except requests.RequestException as e:
            print(f"server unreachable ({e}); retrying...")
            time.sleep(3)
            continue

        if r["status"] == "none":
            time.sleep(2)
            continue  # queue empty, wait and ask again

        task = r["task"]
        result = run_task(task)
        requests.post(
            f"{SERVER}/result",
            json={
                "task_id": task["task_id"],
                "node_id": node_id,
                "result": result,
            },
        )
        print(f"did {task['task_id'][:8]} -> {str(result)[:80]}")


if __name__ == "__main__":
    main()
