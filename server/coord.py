from flask import Flask, request, jsonify
import threading, uuid, time, os

app = Flask(__name__)

# Shared secret. Required when the coordinator is on a public host (Vultr) so
# the open internet cannot pull tasks, poison results, or read /status. Workers
# and the master send it as the X-Swarm-Token header. Empty = no auth (local
# LAN only).
TOKEN = os.environ.get("SWARM_TOKEN", "")


@app.before_request
def _check_token():
    if TOKEN and request.headers.get("X-Swarm-Token") != TOKEN:
        return jsonify({"error": "unauthorized"}), 401


lock = threading.Lock()

queue = []  # tasks waiting to be handed out
assigned = {}  # task_id -> {task, node, at}   (in progress)
results = {}  # task_id -> result             (done)
nodes = {}  # node_id -> last_seen time

# If a worker goes quiet this long, its task is requeued. Must comfortably
# exceed a real model call (which can take minutes), or slow-but-alive workers
# get their tasks double-dispatched. Override with LEASE_SECS.
LEASE_SECS = int(os.environ.get("LEASE_SECS", "300"))

# INSTRUMENTAL=1 adds an "instrumental" role: once theory is in, a worker on a
# machine with FL Studio builds and renders the backing track (in parallel with
# lyrics). Off by default so a cluster without an FL machine still finishes.
INSTRUMENTAL = os.environ.get("INSTRUMENTAL", "0").lower() in ("1", "true", "yes")
AFTER_THEORY = ["lyrics"] + (["instrumental"] if INSTRUMENTAL else [])
EXPECTED = ["theory"] + AFTER_THEORY  # the master waits for all of these


def load_job():
    """Seed the queue with the theory task. The lyrics task is enqueued once
    the theory result arrives (it depends on the theory section layout), so it
    is not loaded up front. See post_result."""
    with lock:
        queue.append({"task_id": str(uuid.uuid4()), "role": "theory"})
    print(f"loaded {len(queue)} task(s); {' + '.join(AFTER_THEORY)} follow theory")


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
    # Workers may say which roles they can run (?roles=theory,lyrics); only
    # matching tasks are handed out. No roles param = any task.
    roles = [r for r in request.args.get("roles", "").split(",") if r]
    with lock:
        nodes[node_id] = time.time()  # counts as a heartbeat
        idx = next((i for i, t in enumerate(queue) if not roles or t["role"] in roles), None)
        if idx is None:
            return jsonify({"status": "none"})
        task = queue.pop(idx)
        assigned[task["task_id"]] = {"task": task, "node": node_id, "at": time.time()}
        return jsonify({"status": "ok", "task": task})


@app.post("/result")
def post_result():
    data = request.get_json()
    tid = data["task_id"]
    role = data.get("role")
    with lock:
        newly = tid not in results
        if newly:  # first result wins; ignore late duplicates
            results[tid] = {"role": role, "result": data["result"]}
        assigned.pop(tid, None)
        nodes[data["node_id"]] = time.time()
        # Dependency: once theory is in, build the next tasks from its output.
        if newly and role == "theory":
            for next_role in AFTER_THEORY:
                queue.append({
                    "task_id": str(uuid.uuid4()),
                    "role": next_role,
                    "theory": data["result"],
                })
                print(f"[enqueue] {next_role} task (theory ready)")
    print(f"[done] {role} {tid[:8]} from {data['node_id']}")
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
                "expected": EXPECTED,
                "results": results,
            }
        )


if __name__ == "__main__":
    load_job()
    threading.Thread(target=requeue_dead, daemon=True).start()
    # host=0.0.0.0 => reachable by the other computers on the same LAN
    app.run(host="0.0.0.0", port=5000)
