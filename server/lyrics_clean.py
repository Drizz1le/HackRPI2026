"""Clean the lyrics agent's output before it is spoken by TTS.

Everything handed to Fish Audio is read aloud, so anything that is not a line
for the narrator has to go. Two passes:

  clean_lyrics(text)  - keeps the [Section] layout, drops text before the first
                        section marker, and removes production cues the model
                        writes as plain text ("Fade out", "Drum roll", "Beat
                        drops ..."). Lines left empty are removed.
  speech_text(text)   - strips the [Section] markers themselves, leaving only
                        the words to speak.

The cue filter is deliberately conservative: it only removes a sentence
fragment that is essentially just a cue phrase ("Fade out softly", "Drum
roll"), so a real lyric that mentions the bass or the beat is kept, even one
that starts with a cue word ("Silence cradles dreams", "Beat drops like
thunder in the sky"). The prompt is the main defense; this is a backstop.
"""
import re

SECTION_RE = re.compile(r"^\s*\[([^\]\n]+)\]\s*$")

# Phrases that, at the start of a short fragment, mark it as a production cue
# rather than a spoken line.
_CUE_START = re.compile(
    r"^(?:the\s+)?(?:"
    r"fade(?:s|d)?\s*(?:out|in|away)?"
    r"|drum\s*roll"
    r"|(?:beat|bass|drums?|music|synths?|keys)\s+"
    r"(?:drops?|fades?|enters?|kicks?\s+in|comes?\s+in|stops?|builds?|cuts?(?:\s+out)?)"
    r"|(?:instrumental|interlude|silence|pause|break|outro|intro|riser|sfx)"
    r")\b",
    re.IGNORECASE,
)
# A cue fragment may carry at most this many words after the cue phrase
# ("Fade out softly"); anything longer is treated as a real lyric
# ("Silence cradles dreams, where we belong").
_MAX_EXTRA_WORDS = 2

# Split a line into fragments on sentence ends and dashes, keeping delimiters.
_FRAGMENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\s*[—–]\s*|\s+-\s+")


def _is_cue(fragment):
    words = re.sub(r"[^\w\s']", " ", fragment).split()
    if not words:
        return False
    joined = " ".join(words)
    m = _CUE_START.match(joined)
    return bool(m) and len(joined[m.end():].split()) <= _MAX_EXTRA_WORDS


def _strip_cues(line):
    """Remove cue fragments from one line; return what is left (may be '')."""
    fragments = [f for f in _FRAGMENT_SPLIT.split(line.strip()) if f.strip()]
    kept, prev_cue, removed = [], False, False
    for f in fragments:
        # A lone sound word right after a cue ("Drum roll—boom.") goes with it.
        lone_word = re.fullmatch(r"\W*\w+\W*", f.strip()) is not None
        if _is_cue(f) or (prev_cue and lone_word):
            prev_cue = removed = True
            continue
        prev_cue = False
        kept.append(f.strip())
    if not removed:
        return line.rstrip()
    return " ".join(kept).lstrip(" ,;:").rstrip()


def clean_lyrics(text):
    """Return the lyrics with preamble and production cues removed."""
    out = []
    seen_section = False
    for line in (text or "").splitlines():
        if SECTION_RE.match(line):
            seen_section = True
            out.append(line.strip())
            continue
        if not seen_section:
            continue  # model chatter before the first [Section]
        if not line.strip():
            out.append("")
            continue
        cleaned = _strip_cues(line)
        if cleaned:
            out.append(cleaned)
    # Collapse runs of blank lines and trim the ends.
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
    if not seen_section:
        # No markers at all: keep the text rather than speak nothing.
        return "\n".join(_strip_cues(l) for l in (text or "").splitlines()).strip()
    return result


def speech_text(text):
    """Drop [Section] markers so only the words to speak remain."""
    lines = [l for l in (text or "").splitlines() if not SECTION_RE.match(l)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
