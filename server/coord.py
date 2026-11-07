from flask import Flask, request, jsonify
import threading, uuid, time

import job

app = Flask(__name__)
lock = threading.Lock()

queue = []  # tasks waiting to be handed out
assigned = {}  # task_id -> {task, node, at}   (in progress)
results = {}  # task_id -> result             (done)
nodes = {}  # node_id -> last_seen time

LEASE_SECS = 30  # if a worker goes quiet this long, its task is requeued


def load_job():
    """Split the target's two versions into searcher tasks and seed the queue.
    See job.build_tasks (reads VERSION_A_DIR / VERSION_B_DIR from the env)."""
    tasks = job.build_tasks()
    with lock:
        queue.extend(tasks)
    print(f"loaded {len(queue)} tasks")


def requeue_dead():
    """Any task whose worker went silent past the lease goes back in the queue."""
    while True:
        time.sleep(5)
        now = time.time()
        with lock:
            for tid, a in list(assigned.items()):
                if now - a["at"] > LEASE_SECS:
                    print(f"[requeue] {tid[:8]} (worker {a['node']} went quiet)")
                    queue.append(a["task"])
                    assigned.pop(tid, None)


@app.post("/register")
def register():
    node_id = str(uuid.uuid4())[:8]
    with lock:
        nodes[node_id] = time.time()
    print(f"[join] {node_id}")
    return jsonify({"node_id": node_id})


@app.get("/task")
def get_task():
    node_id = request.args.get("node_id", "?")
    with lock:
        nodes[node_id] = time.time()  # counts as a heartbeat
        if not queue:
            return jsonify({"status": "none"})
        task = queue.pop(0)
        assigned[task["task_id"]] = {"task": task, "node": node_id, "at": time.time()}
        return jsonify({"status": "ok", "task": task})


@app.post("/result")
def post_result():
    data = request.get_json()
    tid = data["task_id"]
    with lock:
        results[tid] = data["result"]
        assigned.pop(tid, None)
        nodes[data["node_id"]] = time.time()
    print(f"[done] {tid[:8]} from {data['node_id']} -> {data['result']}")
    return jsonify({"ok": True})


@app.get("/status")
def status():
    """Open this in a browser to watch progress / build the dashboard on."""
    with lock:
        return jsonify(
            {
                "nodes": list(nodes),
                "queued": len(queue),
                "in_progress": len(assigned),
                "done": len(results),
                "results": results,
            }
        )


if __name__ == "__main__":
    load_job()
    threading.Thread(target=requeue_dead, daemon=True).start()
    # host=0.0.0.0 => reachable by the other computers on the same LAN
    app.run(host="0.0.0.0", port=5000)
