"""Split two versions of a target into one analysis task per changed file.

The two versions can be directories (unpacked trees) or single files. Version
trees are untrusted input: we only read them as bytes/text, never import them or
run anything inside them. Binary files are flagged, not decoded.
"""
import uuid
from difflib import unified_diff
from pathlib import Path

MAX_DIFF_LINES = 400  # keep each task small enough for one model call


def _is_text(path):
    try:
        with open(path, "rb") as f:
            return b"\0" not in f.read(8192)
    except OSError:
        return False


def _diff_pair(name, a, b):
    """A change record for two files that both exist, or None if identical."""
    if a.read_bytes() == b.read_bytes():
        return None
    if not (_is_text(a) and _is_text(b)):
        return {"path": name, "change_kind": "binary", "diff": ""}
    lines = list(unified_diff(
        a.read_text("utf-8", "replace").splitlines(keepends=True),
        b.read_text("utf-8", "replace").splitlines(keepends=True),
        fromfile=f"a/{name}", tofile=f"b/{name}"))
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES] + [f"... (truncated at {MAX_DIFF_LINES} lines)\n"]
    return {"path": name, "change_kind": "modified", "diff": "".join(lines)}


def _rel_files(root):
    root = Path(root)
    return {str(p.relative_to(root)): p for p in root.rglob("*") if p.is_file()}


def _records(path_a, path_b):
    a, b = Path(path_a), Path(path_b)
    if a.is_file() and b.is_file():
        rec = _diff_pair(b.name, a, b)
        return [rec] if rec else []

    fa, fb = _rel_files(a), _rel_files(b)
    out = []
    for rel in sorted(set(fa) | set(fb)):
        if rel in fa and rel in fb:
            rec = _diff_pair(rel, fa[rel], fb[rel])
        elif rel in fa:
            rec = {"path": rel, "change_kind": "removed", "diff": ""}
        else:
            rec = {"path": rel, "change_kind": "added", "diff": ""}
        if rec:
            out.append(rec)
    return out


def build_tasks(path_a, path_b, version_a, version_b):
    """Return one task dict per changed file between the two versions."""
    tasks = []
    for rec in _records(path_a, path_b):
        rec.update(id=uuid.uuid4().hex[:8],
                   version_from=version_a, version_to=version_b)
        tasks.append(rec)
    return tasks
