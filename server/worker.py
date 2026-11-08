import json, os, requests, sys, time
from pathlib import Path

from model import call_model, check_models
from prompts import THEORY_PROMPT, build_lyrics_prompt

# ---- point this at the coordinator's address (LAN IP, or the Vultr public IP) ----
SERVER = os.environ.get("SERVER", "http://192.168.1.50:5000")
WORKER_MODEL = os.environ.get("WORKER_MODEL", "qwen2.5:7b")
# Optional per-role overrides, e.g. keep theory on a small model on a low-VRAM
# machine: THEORY_MODEL=qwen2.5:3b. Both default to WORKER_MODEL.
THEORY_MODEL = os.environ.get("THEORY_MODEL") or WORKER_MODEL
LYRICS_MODEL = os.environ.get("LYRICS_MODEL") or WORKER_MODEL
# Optional one-line brief seeding the theory agent.
SONG_BRIEF = os.environ.get("SONG_BRIEF", "Create an original song of your choice.")

# Shared secret sent to the coordinator; must match its SWARM_TOKEN.
TOKEN = os.environ.get("SWARM_TOKEN", "")
# Lyrics system prompt = LYRICS_PROMPT + composer guide + vocals library files.
LYRICS_SYSTEM = build_lyrics_prompt()
HEADERS = {"X-Swarm-Token": TOKEN} if TOKEN else {}

# Roles this worker will take. Default: the LLM roles any machine can run.
# Only a Windows machine with FL Studio should add "instrumental".
ROLES = [r.strip() for r in os.environ.get("ROLES", "theory,lyrics").split(",") if r.strip()]
REPO = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", REPO / "output"))


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
        return call_model(THEORY_PROMPT, SONG_BRIEF, THEORY_MODEL)
    if role == "lyrics":
        user = "Composition plan to write lyrics for:\n" + str(task.get("theory", ""))
        return call_model(LYRICS_SYSTEM, user, LYRICS_MODEL)
    if role == "instrumental":
        return render_instrumental(task.get("theory", ""))
    return json.dumps({"error": f"unknown role {role!r}"})


def render_instrumental(theory):
    """theory plan -> arrangement -> FL Studio project -> rendered WAV.

    Returns JSON with the WAV path. The master reads that file directly, so the
    instrumental worker and the master must share a disk (same machine)."""
    from arrange import plan_from_theory

    sys.path.insert(0, str(REPO / "flstudio" / "tools"))
    from cluster_render import render

    plan = plan_from_theory(theory)
    try:
        instrumentation = json.loads(theory).get("instrumentation", ())
    except (ValueError, AttributeError):
        instrumentation = ()
    info = render(plan, str(OUTPUT_DIR), instrumentation=instrumentation)
    return json.dumps(info)


def main():
    print(f"models: theory={THEORY_MODEL} lyrics={LYRICS_MODEL}")
    llm_roles = {"theory": THEORY_MODEL, "lyrics": LYRICS_MODEL}
    check_models({m for r, m in llm_roles.items() if r in ROLES})
    node_id = register()
    print(f"registered as {node_id}, roles {','.join(ROLES)}, pulling tasks from {SERVER}")
    while True:
        try:
            r = requests.get(
                f"{SERVER}/task", params={"node_id": node_id, "roles": ",".join(ROLES)},
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
