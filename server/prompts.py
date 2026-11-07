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

THEORY_PROMPT = """You are a music theory and composition agent in a song-making
pipeline. Given a short brief, design one coherent song and return ONLY a JSON
object (no prose, no markdown fences) with exactly these fields:

{
  "genre": "...",
  "mood": "...",
  "key": "...",
  "tempo_bpm": 120,
  "instrumentation": ["...", "..."],
  "sections": [
    {"name": "Intro",  "bars": 8},
    {"name": "Verse",  "bars": 16},
    {"name": "Chorus", "bars": 16},
    {"name": "Verse",  "bars": 16},
    {"name": "Chorus", "bars": 16},
    {"name": "Outro",  "bars": 8}
  ],
  "style_prompt": "One natural-language sentence summarizing genre, mood, key, tempo, and instrumentation, suitable as a text-to-music style prompt."
}

Keep the total length modest (a ~60-90 second song). The "sections" list is the
structure the lyrics agent must follow. Return valid JSON only."""

LYRICS_PROMPT = """You are a lyricist agent in a song-making pipeline. You are
given a composition plan (JSON) that includes a "sections" layout and a
"style_prompt". Write original lyrics that follow that section structure exactly,
in order, one block per section.

Rules:
- Put a section marker on its own line before each section's lines, using the
  section name in brackets: [Intro], [Verse], [Chorus], [Outro], etc. If a name
  repeats (two [Verse] sections), write different lyrics for each.
- Match the mood and theme implied by the style_prompt.
- Keep each section's length roughly proportional to its bar count.
- Return ONLY the lyrics with their markers. No explanations, no JSON."""

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
