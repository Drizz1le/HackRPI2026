"""Run the whole cluster on one machine and make one song.

    python server/run_local.py            # FL instrumental if FL Studio is installed
    python server/run_local.py --no-fl    # skip the instrumental role
    python server/run_local.py --brief "a rainy-night lo-fi track"

Starts the coordinator, an LLM worker (theory + lyrics) and, when FL Studio
is available, an instrumental worker. It then runs the master in the foreground
and stops everything when the song is done. Output lands in output/.

Needs: Ollama running with the worker model pulled (default qwen2.5:7b), and
the server/requirements.txt packages. FISH_API_KEY (from the environment or the
repo's .env) turns on real vocals; without it the master writes a placeholder.
FL Studio must be CLOSED while the instrumental renders.
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

SERVER_DIR = Path(__file__).resolve().parent
REPO = SERVER_DIR.parent
FL_EXE = Path(os.environ.get("FL_DIR", r"C:\Program Files\Image-Line\FL Studio 2025")) / "FL64.exe"


def load_dotenv(path):
    """KEY=VALUE lines from .env, without overriding the real environment."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def wait_for_coordinator(url, proc, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            sys.exit("coordinator exited during startup (is port 5000 already in use?)")
        try:
            requests.get(f"{url}/status", timeout=2)
            return
        except requests.RequestException:
            time.sleep(0.5)
    sys.exit(f"coordinator did not come up at {url}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    fl = ap.add_mutually_exclusive_group()
    fl.add_argument("--fl", dest="fl", action="store_true", default=None, help="require the FL instrumental")
    fl.add_argument("--no-fl", dest="fl", action="store_false", help="skip the FL instrumental")
    ap.add_argument("--brief", help="one-line brief for the theory agent")
    args = ap.parse_args()

    load_dotenv(REPO / ".env")
    use_fl = FL_EXE.is_file() if args.fl is None else args.fl
    if use_fl and not FL_EXE.is_file():
        sys.exit(f"--fl given but FL Studio not found at {FL_EXE} (set FL_DIR)")

    port = os.environ.get("PORT", "5000")
    server = f"http://localhost:{port}"
    env = dict(os.environ)
    env.setdefault("MODEL_MODE", "ollama")
    env.setdefault("OLLAMA_HOST", "http://localhost:11434")
    env.setdefault("LEASE_SECS", "900")  # an FL render can take a few minutes
    env["SERVER"] = server
    env["INSTRUMENTAL"] = "1" if use_fl else "0"
    env["OUTPUT_DIR"] = str(REPO / "output")
    env["INPUT_DIR"] = str(REPO / "input")
    env["PYTHONUNBUFFERED"] = "1"
    if args.brief:
        env["SONG_BRIEF"] = args.brief
    (REPO / "output").mkdir(exist_ok=True)

    py = sys.executable
    procs = []

    def start(name, script, **extra):
        e = dict(env, **extra)
        p = subprocess.Popen([py, str(SERVER_DIR / script)], cwd=str(SERVER_DIR), env=e)
        procs.append((name, p))
        return p

    print(f"[run] model mode {env['MODEL_MODE']}, FL instrumental {'on' if use_fl else 'off'}, "
          f"vocals {'Fish Audio' if env.get('FISH_API_KEY') else 'placeholder (no FISH_API_KEY)'}")
    try:
        coord = start("coordinator", "coord.py")
        wait_for_coordinator(server, coord)
        start("llm worker", "worker.py", ROLES="theory,lyrics")
        if use_fl:
            start("fl worker", "worker.py", ROLES="instrumental")
        code = subprocess.call([py, str(SERVER_DIR / "master.py")], cwd=str(SERVER_DIR), env=env)
        print(f"[run] master finished (exit {code}); output in {REPO / 'output'}")
        return code
    except KeyboardInterrupt:
        print("\n[run] interrupted")
        return 130
    finally:
        for name, p in reversed(procs):
            if p.poll() is None:
                p.terminate()
        for name, p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
