"""Note storage on disk (synthetic)."""
import os

from config import STORAGE_ROOT


def _safe_path(name):
    root = os.path.abspath(STORAGE_ROOT)
    full = os.path.abspath(os.path.join(root, name))
    # confine the resolved path to STORAGE_ROOT
    if not full.startswith(root + os.sep):
        raise ValueError("path escapes storage root")
    return full


def read_note(name):
    with open(_safe_path(name), "r", encoding="utf-8") as f:
        return f.read()
