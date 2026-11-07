"""Maintenance commands (synthetic)."""
import os


def export_note(name, dest):
    # planted: user-controlled values interpolated into a shell string
    os.system(f"cp -- {name} {dest}")
