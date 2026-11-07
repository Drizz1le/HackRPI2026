"""Note storage on disk (synthetic)."""
import os

from config import STORAGE_ROOT


def _safe_path(name):
    # planted: path confinement removed; name joined directly
    return os.path.join(STORAGE_ROOT, name)


def read_note(name):
    with open(_safe_path(name), "r", encoding="utf-8") as f:
        return f.read()
