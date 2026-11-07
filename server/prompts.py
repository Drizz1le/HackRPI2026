"""Assemble an agent's system prompt.

Every agent loads the universal SYSTEM_PROMPT.md, has its {{...}} template
variables filled from the environment, then gets exactly one differentiation
prompt appended:

  - "master"   -> MASTER_PROMPT.md    (the synthesizer / orchestrator)
  - "subagent" -> SUBAGENT_PROMPT.md  (the searcher that finds version diffs)

This matches the loading contract in SYSTEM_PROMPT.md section 9.
"""
import os
from pathlib import Path

# The prompt files live in qwen/ at the repo root. In the container they are
# copied next to this file at /app/qwen. Try the known locations in order, or
# use PROMPTS_DIR if the caller set it.
_CANDIDATE_DIRS = [
    os.environ.get("PROMPTS_DIR"),
    Path(__file__).resolve().parent.parent / "qwen",  # repo root/qwen (local)
    Path(__file__).resolve().parent / "qwen",          # /app/qwen (container)
]


def _qwen_dir():
    for d in _CANDIDATE_DIRS:
        if d and Path(d).is_dir():
            return Path(d)
    raise FileNotFoundError(
        "could not find the qwen/ prompt directory; set PROMPTS_DIR"
    )


_DIFFERENTIATION = {
    "master": "differentiation_prompts/MASTER_PROMPT.md",
    "subagent": "differentiation_prompts/SUBAGENT_PROMPT.md",
}

# Template variables from SYSTEM_PROMPT.md, filled from the environment with
# hackathon-friendly defaults so nothing is left unsubstituted.
_TEMPLATE_DEFAULTS = {
    "CLUSTER_NAME": "hackrpi-swarm",
    "WORKSPACE": "/workspace",
    "SCOPE_FILE": "/workspace/scope.md",
    "TARGET": "unset-target",
    "VERSION_A": "unset",
    "VERSION_B": "unset",
    "SANDBOX": "/sandbox",
    "MASTER_MODEL": os.environ.get("MASTER_MODEL", "qwen2.5:14b"),
    "WORKER_MODEL": os.environ.get("WORKER_MODEL", "qwen2.5:3b"),
}


def _values():
    return {k: os.environ.get(k, default) for k, default in _TEMPLATE_DEFAULTS.items()}


def _substitute(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def build_system_prompt(role):
    """Return the full system prompt for 'master' or 'subagent'."""
    role = role.lower()
    if role not in _DIFFERENTIATION:
        raise ValueError(
            f"unknown role {role!r}; expected one of {sorted(_DIFFERENTIATION)}"
        )
    qwen = _qwen_dir()
    system = (qwen / "system_prompts" / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")
    differentiation = (qwen / _DIFFERENTIATION[role]).read_text(encoding="utf-8")
    assembled = system.rstrip() + "\n\n---\n\n" + differentiation.lstrip()
    return _substitute(assembled, _values())
