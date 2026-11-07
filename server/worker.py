import os, requests, time

# ---- point this at the coordinator computer's LAN IP (set via env var) ----
SERVER = os.environ.get("SERVER", "http://192.168.1.50:5000")


def register():
    """Keep trying until the coordinator is reachable (it may start after us)."""
    while True:
        try:
            return requests.post(f"{SERVER}/register", timeout=10).json()["node_id"]
        except requests.RequestException as e:
            print(f"can't reach coordinator at {SERVER} ({e}); retrying...")
            time.sleep(3)


def run_task(task):
    time.sleep(1)  # pretend the work takes a moment
    return task["payload"] ** 2


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
        print(f"did {task['task_id'][:8]} -> {result}")


if __name__ == "__main__":
    main()
