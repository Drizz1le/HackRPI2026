"""Tests for arrange. Run from server/: python3 -m unittest test_arrange"""
import json
import unittest

from arrange import parse_chord, parse_key, parse_progression, plan_from_theory, voice

# Real qwen2.5:7b theory output from the live test.
REAL_THEORY = {
    "genre": "Spoken Word", "mood": "Inspiring and Motivational", "key": "C", "bpm": 90,
    "time_signature": "4/4", "instrumentation": ["Acoustic Guitar", "Electric Bass"],
    "structure": [
        {"section": "Intro", "bars": 8}, {"section": "Verse", "bars": 16},
        {"section": "Hook", "bars": 8}, {"section": "Verse", "bars": 16},
        {"section": "Hook", "bars": 8}, {"section": "Outro", "bars": 8},
    ],
    "chord_progression": "C - G - Am - F",
}


def names(text, key="C"):
    from arrange import chord_name
    tonic, mode = parse_key(key)
    return [chord_name(r, q) for r, q in parse_progression(text, tonic, mode)]


class KeyTest(unittest.TestCase):
    def test_keys(self):
        self.assertEqual(parse_key("C"), (0, "major"))
        self.assertEqual(parse_key("A minor"), (9, "minor"))
        self.assertEqual(parse_key("F#m"), (6, "minor"))
        self.assertEqual(parse_key("Bb Dorian"), (10, "dorian"))
        self.assertEqual(parse_key("Eb major"), (3, "major"))
        self.assertEqual(parse_key("D minor pentatonic"), (2, "minor"))
        self.assertIsNone(parse_key("unknown"))
        self.assertIsNone(parse_key(None))


class ProgressionTest(unittest.TestCase):
    def test_chord_names(self):
        self.assertEqual(names("C - G - Am - F"), ["C", "G", "Am", "F"])
        self.assertEqual(names("F#m7, Bb, Cmaj7 | Gsus4"), ["F#m7", "Bb", "Cmaj7", "Gsus4"])
        self.assertEqual(names("C/E Bdim G7"), ["C", "Bdim", "G7"])

    def test_roman_in_minor_uses_the_minor_scale(self):
        # i - VI - III - VII in A minor = Am F C G
        self.assertEqual(names("i - VI - III - VII", "A minor"), ["Am", "F", "C", "G"])

    def test_roman_in_major(self):
        self.assertEqual(names("ii-V-I", "C"), ["Dm", "G", "C"])
        self.assertEqual(names("I - V - vi - IV", "G major"), ["G", "D", "Em", "C"])
        self.assertEqual(names("I bVII IV", "D"), ["D", "C", "G"])
        self.assertEqual(names("ii7 V7 Imaj7", "C"), ["Dm7", "G7", "Cmaj7"])

    def test_prompt_example_text(self):
        # The theory prompt's own placeholder: "e.g. i - VI - III - VII"
        self.assertEqual(names("e.g. i - VI - III - VII", "A minor"), ["Am", "F", "C", "G"])

    def test_garbage(self):
        self.assertEqual(names("something dreamy"), [])
        self.assertIsNone(parse_chord("", 0, "major"))


class VoicingTest(unittest.TestCase):
    def test_chord_tones_and_range(self):
        v = voice(9, "min", None)  # A minor
        self.assertEqual(sorted(n % 12 for n in v), sorted([9, 0, 4]))
        self.assertTrue(all(48 <= n <= 79 for n in v))

    def test_smooth_voice_leading(self):
        prev = voice(0, "maj", None)
        nxt = voice(5, "maj", prev)  # C -> F: should move at most a few semitones per voice
        self.assertLessEqual(sum(min(abs(n - p) for p in prev) for n in nxt), 6)


class PlanTest(unittest.TestCase):
    def test_real_theory(self):
        plan = plan_from_theory(json.dumps(REAL_THEORY))
        self.assertEqual(plan["warnings"], [])
        self.assertEqual(plan["bpm"], 90)
        self.assertEqual(plan["bars"], 64)
        self.assertAlmostEqual(plan["seconds"], 64 * 240 / 90, places=1)
        self.assertAlmostEqual(plan["vocal_start_seconds"], 8 * 240 / 90, places=1)
        self.assertEqual([s["style"] for s in plan["sections"]],
                         ["intro", "verse", "hook", "verse", "hook", "outro"])
        self.assertEqual([s["start_bar"] for s in plan["sections"]], [0, 8, 24, 32, 48, 56])
        self.assertEqual(plan["sections"][0]["chords"][:5], ["C", "G", "Am", "F", "C"])

    def test_section_contents(self):
        plan = plan_from_theory(REAL_THEORY)
        insts = lambda i: {n[0] for n in plan["sections"][i]["notes"]}
        self.assertNotIn("kick", insts(0))          # intro: no kick
        self.assertNotIn("bass", insts(0))
        self.assertTrue({"kick", "snare", "hat", "bass", "keys"} <= insts(1))  # verse
        self.assertIn("pad", insts(2))              # hook adds the pad
        for s in plan["sections"]:
            for inst, bar, step, ln, key, vel in s["notes"]:
                self.assertTrue(0 <= bar < s["bars"])
                self.assertTrue(0 <= step < 16 and ln >= 1)
                self.assertTrue(0 <= key <= 127 and 1 <= vel <= 127)

    def test_bass_follows_chord_roots(self):
        plan = plan_from_theory(REAL_THEORY)
        verse = plan["sections"][1]
        for bar, chord in enumerate(verse["chords"]):
            bass = [n[4] for n in verse["notes"] if n[0] == "bass" and n[1] == bar]
            root = {"C": 0, "G": 7, "Am": 9, "F": 5}[chord]
            self.assertTrue(bass and all(k % 12 == root for k in bass), (bar, chord, bass))

    def test_fenced_json_from_model(self):
        text = "Here you go:\n```json\n" + json.dumps(REAL_THEORY) + "\n```"
        self.assertEqual(plan_from_theory(text)["bars"], 64)

    def test_garbage_falls_back(self):
        plan = plan_from_theory("not json at all")
        self.assertEqual(plan["bars"], 64)
        self.assertEqual(plan["key"], "C major")
        self.assertTrue(plan["warnings"])

    def test_clamps(self):
        plan = plan_from_theory({"bpm": 400, "key": "A minor", "time_signature": "6/8",
                                 "structure": [{"section": "Verse", "bars": 999}] * 10,
                                 "chord_progression": "???"})
        self.assertEqual(plan["bpm"], 180)
        self.assertLessEqual(plan["bars"], 128)
        self.assertTrue(all(s["bars"] <= 32 for s in plan["sections"]))
        w = " ".join(plan["warnings"])
        for word in ("bpm", "6/8", "progression", "longer"):
            self.assertIn(word, w)
        self.assertEqual(plan["sections"][0]["chords"][:4], ["Am", "F", "C", "G"])


if __name__ == "__main__":
    unittest.main()
