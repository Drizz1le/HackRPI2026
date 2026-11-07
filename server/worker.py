import requests, time

# ---- point this at the coordinator computer's LAN IP ----
SERVER = "http://192.168.1.50:5000"  # CHANGE to the coordinator's actual IP


def run_task(task):
    time.sleep(1)  # pretend the work takes a moment
    return task["payload"] ** 2


def main():
    node_id = requests.post(f"{SERVER}/register").json()["node_id"]
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
