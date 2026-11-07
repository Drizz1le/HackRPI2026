"""Maintenance commands (synthetic)."""
import subprocess


def export_note(name, dest):
    # argument list, no shell interpretation
    subprocess.run(["cp", "--", name, dest], check=True)
