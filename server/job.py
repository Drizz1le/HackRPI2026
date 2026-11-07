"""Turn two versions of a target into searcher tasks.

Given two local directories (one per version), diff them file by file and emit
one TaskEnvelope per changed file. The envelope shape follows SYSTEM_PROMPT.md
section 8. This module does no model work; it only decomposes the job.

Config (environment):
  VERSION_A_DIR / VERSION_B_DIR  absolute paths to the two unpacked versions
  VERSION_A / VERSION_B          human labels for the versions (default: dir names)
  TARGET                         name of the target (default: "unset-target")

Safety: the version trees are untrusted downloaded material. We only read them
as bytes/text with the standard library. We never import from them or run any
interpreter or build tool inside them. Binary files are skipped.
"""
import hashlib
import json
import os
import uuid
from difflib import unified_diff
from pathlib import Path

# Keep each task small (MASTER_PROMPT: a task over ~1500 output tokens is too
# big). Cap the diff carried in the envelope; the searcher can re-read the file
# from its path if it needs the rest.
MAX_DIFF_LINES = 400


def _is_text(path):
    """Cheap binary check: a null byte in the first chunk means binary."""
    try:
        with open(path, "rb") as f:
            return b"\0" not in f.read(8192)
    except OSError:
        return False


def _read_lines(path):
    return path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)


def _rel_files(root):
    """Relative paths of every file under root."""
    root = Path(root)
    return {
        str(p.relative_to(root)): p
        for p in root.rglob("*")
        if p.is_file()
    }


def diff_trees(dir_a, dir_b):
    """Compare two version directories. Returns a list of change records:
    {path, kind, diff}. kind is added | removed | modified | binary."""
    a = _rel_files(dir_a)
    b = _rel_files(dir_b)
    changes = []

    for rel in sorted(set(a) | set(b)):
        in_a, in_b = rel in a, rel in b

        if in_a and not in_b:
            changes.append({"path": rel, "kind": "removed", "diff": None})
            continue
        if in_b and not in_a:
            changes.append({"path": rel, "kind": "added", "diff": None})
            continue

        pa, pb = a[rel], b[rel]
        if pa.read_bytes() == pb.read_bytes():
            continue  # unchanged

        if not (_is_text(pa) and _is_text(pb)):
            changes.append({"path": rel, "kind": "binary", "diff": None})
            continue

        diff = list(
            unified_diff(
                _read_lines(pa),
                _read_lines(pb),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            )
        )
        if len(diff) > MAX_DIFF_LINES:
            diff = diff[:MAX_DIFF_LINES] + [f"... (diff truncated at {MAX_DIFF_LINES} lines)\n"]
        changes.append({"path": rel, "kind": "modified", "diff": "".join(diff)})

    return changes


def _envelope(change, version_a, version_b):
    diff = change["diff"] or ""
    key = hashlib.sha256(
        f"version-diff|{change['path']}|{diff}".encode("utf-8")
    ).hexdigest()
    return {
        "task_id": str(uuid.uuid4()),
        "parent_id": None,
        "role": "version-diff",
        "objective": (
            f"Analyze the {change['kind']} file {change['path']} between "
            f"{version_a} and {version_b} for security-relevant change."
        ),
        "context_refs": [],
        "inputs": {
            "path": change["path"],
            "change_kind": change["kind"],
            "version_from": version_a,
            "version_to": version_b,
            "diff": change["diff"],
        },
        "constraints": {
            "read_only": True,
            "sandbox_only": False,
            "allowed_tools": ["read", "grep", "glob"],
            "max_output_tokens": 1200,
            "deadline_seconds": 900,
        },
        "deliverable": {"schema": "TaskResult", "finding_kinds": ["version-diff"]},
        "lease_seconds": 900,
        "attempt": 1,
        "idempotency_key": f"sha256:{key}",
    }


def build_tasks():
    """Read the configured version dirs and return a list of TaskEnvelopes.
    Returns [] (and prints why) if the dirs are not usable."""
    dir_a = os.environ.get("VERSION_A_DIR")
    dir_b = os.environ.get("VERSION_B_DIR")
    if not dir_a or not dir_b:
        print("[job] VERSION_A_DIR / VERSION_B_DIR not set; no tasks loaded")
        return []
    if not Path(dir_a).is_dir() or not Path(dir_b).is_dir():
        print(f"[job] version dir missing: {dir_a!r} or {dir_b!r}; no tasks loaded")
        return []

    version_a = os.environ.get("VERSION_A", Path(dir_a).name)
    version_b = os.environ.get("VERSION_B", Path(dir_b).name)
    target = os.environ.get("TARGET", "unset-target")

    changes = diff_trees(dir_a, dir_b)
    tasks = [_envelope(c, version_a, version_b) for c in changes]
    print(
        f"[job] target={target} {version_a}..{version_b}: "
        f"{len(tasks)} changed files -> {len(tasks)} tasks"
    )
    return tasks


if __name__ == "__main__":
    # Quick manual check: print the envelopes as JSON.
    print(json.dumps(build_tasks(), indent=2))
