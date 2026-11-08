"""Tests for lyrics_clean. Run from server/: python3 -m unittest test_lyrics_clean"""
import unittest

from lyrics_clean import clean_lyrics, speech_text

# Real qwen2.5:3b output (with guide) from the first live test.
REAL_OUTPUT = """[Intro]
Wham, wham! The bass thumps in my chest.
Drum roll—boom. It's time to reflect and step.

[Verse]
In the mirror, I see shadows hide.

[Outro]
Fade out—drum roll. The bass lingers long.
This melody will keep me grounded and strong.

Beat drops like thunder in the sky."""


class CleanLyricsTest(unittest.TestCase):
    def test_real_output(self):
        self.assertEqual(
            clean_lyrics(REAL_OUTPUT),
            "[Intro]\n"
            "Wham, wham! The bass thumps in my chest.\n"
            "It's time to reflect and step.\n\n"
            "[Verse]\n"
            "In the mirror, I see shadows hide.\n\n"
            "[Outro]\n"
            "The bass lingers long.\n"
            "This melody will keep me grounded and strong.\n\n"
            # Long enough to read as a (weak) lyric, so the filter keeps it.
            "Beat drops like thunder in the sky.",
        )

    def test_drops_preamble_before_first_section(self):
        text = "Sure! Here are your lyrics:\n\n[Verse]\nWalking the line."
        self.assertEqual(clean_lyrics(text), "[Verse]\nWalking the line.")

    def test_keeps_lyrics_that_mention_music_in_passing(self):
        lines = [
            "The bass thumps in my chest.",
            "I ride this beat until the sun comes up.",
            "When the music fades, I'm still standing here, still breathing slow.",
            "Pause for nobody, I keep moving forward through the noise.",
            "Silence cradles dreams, where we belong,",
            "Fade out like a story ending too soon,",
        ]
        text = "[Verse]\n" + "\n".join(lines)
        self.assertEqual(clean_lyrics(text), text)

    def test_removes_standalone_cue_lines(self):
        for cue in ["Fade out.", "Drum roll...", "(Beat drops)", "Instrumental break",
                    "Bass enters.", "The music fades away", "Silence.",
                    "Fade out softly—"]:
            with self.subTest(cue=cue):
                text = f"[Hook]\nHold the line.\n{cue}\nNever let go."
                self.assertEqual(clean_lyrics(text), "[Hook]\nHold the line.\nNever let go.")

    def test_splits_cue_off_a_lyric(self):
        self.assertEqual(
            clean_lyrics("[Outro]\nFade out softly—let these chords sing so low,"),
            "[Outro]\nlet these chords sing so low,",
        )

    def test_no_markers_keeps_text(self):
        self.assertEqual(clean_lyrics("Just a line.\nFade out."), "Just a line.")

    def test_empty(self):
        self.assertEqual(clean_lyrics(""), "")
        self.assertEqual(clean_lyrics(None), "")


class SpeechTextTest(unittest.TestCase):
    def test_strips_section_markers(self):
        self.assertEqual(
            speech_text("[Intro]\nLine one.\n\n[Verse]\nLine two."),
            "Line one.\n\nLine two.",
        )

    def test_keeps_inline_brackets(self):
        self.assertEqual(speech_text("[Verse]\nI said [softly] no."), "I said [softly] no.")


if __name__ == "__main__":
    unittest.main()
