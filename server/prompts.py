"""Assemble an agent's system prompt.

Every agent loads the universal SYSTEM_PROMPT.md, then gets exactly one
differentiation prompt appended:

  - "master"   -> MASTER_PROMPT.md    (the synthesizer / orchestrator)
  - "subagent" -> SUBAGENT_PROMPT.md  (the searcher that finds version diffs)

Deployment values (cluster name, paths, target, versions, models) are
hardcoded in the prompt files, so no environment substitution happens here.
This matches the loading contract in SYSTEM_PROMPT.md section 9.
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Music pipeline role prompts. The theory and lyrics agents are plain LLM calls
# (Qwen via Ollama, or the stub); these are their system prompts.
# ---------------------------------------------------------------------------

THEORY_PROMPT = """You are a music theory and composition agent in a track-making
pipeline. Given a short brief, design one coherent track and return ONLY a JSON
object (no prose, no markdown fences) with exactly these fields:

{
  "genre": "...",
  "mood": "...",
  "key": "...",
  "bpm": 90,
  "time_signature": "4/4",
  "instrumentation": ["...", "..."],
  "structure": [
    {"section": "Intro",  "bars": 8},
    {"section": "Verse",  "bars": 16},
    {"section": "Hook",   "bars": 8},
    {"section": "Verse",  "bars": 16},
    {"section": "Hook",   "bars": 8},
    {"section": "Outro",  "bars": 8}
  ],
  "chord_progression": "e.g. i - VI - III - VII"
}

The vocals on this track are SPOKEN (spoken-word / rap), not sung, so favor a
groove and tempo that suit speech over the beat. Keep the track modest in length
(~60-90s). The "structure" list is what the lyrics agent must follow. Return
valid JSON only."""

LYRICS_PROMPT = """You are a spoken-word lyricist in a track-making pipeline. You
receive a composition plan (JSON) with a "structure" layout, "mood", and
"bpm". Write words to be SPOKEN OUT LOUD over the track - spoken-word / rap
style, NOT sung. Do not write melody or notes; write lines a narrator performs.

Rules:
- Follow the "structure" sections exactly, in order, one block per section. Put
  the section name on its own line in brackets before its lines: [Intro],
  [Verse], [Hook], [Outro], etc. If a section repeats, write different words.
- Match the plan's mood. Write for read-aloud rhythm: use line breaks to set the
  cadence and punctuation (commas, periods, dashes, ellipses) to control pacing
  and pauses. Shorter lines land harder; longer lines ride the beat.
- Keep each section's length roughly proportional to its bar count and the bpm.
- Return ONLY the spoken lines with their [Section] markers. No explanations,
  no JSON, no stage directions."""

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

def build_system_prompt(role):
    """Return the full system prompt for 'master', 'subagent', or 'verify'."""
    role = role.lower()
    if role not in _DIFFERENTIATION:
        raise ValueError(
            f"unknown role {role!r}; expected one of {sorted(_DIFFERENTIATION)}"
        )
    qwen = _qwen_dir()
    system = (qwen / "system_prompts" / "SYSTEM_PROMPT.md").read_text(encoding="utf-8")
    differentiation = (qwen / _DIFFERENTIATION[role]).read_text(encoding="utf-8")
    return system.rstrip() + "\n\n---\n\n" + differentiation.lstrip()
