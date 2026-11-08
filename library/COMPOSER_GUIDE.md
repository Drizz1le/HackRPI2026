# COMPOSER_GUIDE.md

## Master Guide for Downstream Music Generation Agents

This document acts as the central orchestrator and blueprint for the **FL Studio Composer Agent** and the **ElevenLabs Singer Agent**. It synthesizes the research library files into clear, operational rules for multi-agent music generation.

---

## 🗂 Library Architecture Reference

The research library is organized into three primary domain modules:

```text
library/
├── arrangement/
│   ├── global_composition.md      <-- Macro composition rules, energy flow, & arrangement strategies
│   └── structure_blueprints.md    <-- Song section blueprints, measure counts, & structural transitions
├── harmony/
│   ├── core_harmony.md            <-- Functional harmony, chord progressions, cadences, & voicings
│   └── global_scales.md           <-- Modes, scale selections, emotional mappings, & key signatures
└── vocals/
    ├── global_vocal_techniques.md <-- Vocal styles, performance dynamics, & timbre directions
    └── prosody_stress.md          <-- Syllable alignment, metric accenting, & text-to-speech cues
```

---

## 🎼 Phase 1: Harmonic & Modal Initialization (Composer Agent)

1. **Scale & Mode Selection** (`library/harmony/global_scales.md`):
   * Select a foundational mode or scale based on the targeted emotional arc of the piece (e.g., *Dorian* for nostalgia/melancholy with uplifting elements, *Aeolian* for deep sadness, *Lydian* for dreamy/bright landscapes).
   * Maintain key consistency across MIDI channels unless executing an intentional modal interchange or modulation.

2. **Progression Building** (`library/harmony/core_harmony.md`):
   * Construct main chord progressions following functional harmony rules (e.g., tonic establishment, subdominant departure, dominant tension, cadential resolution).
   * Apply smooth voice leading—avoid parallel fifths/octaves unless producing genre-specific effects (e.g., power chords or synth stacks).
   * Use extended and altered chords (7ths, 9ths, suspended tones) during dynamic build-ups to increase harmonic color.

---

## 📐 Phase 2: Structural Planning & Arrangement (Composer Agent)

1. **Song Macro-Structure** (`library/arrangement/structure_blueprints.md`):
   * Define the overall layout before placing patterns into the FL Studio Playlist (e.g., `Intro` $\rightarrow$ `Verse 1` $\rightarrow$ `Pre-Chorus` $\rightarrow$ `Chorus` $\rightarrow$ `Verse 2` $\rightarrow$ `Chorus` $\rightarrow$ `Bridge` $\rightarrow$ `Outro`).
   * Adhere to strict measure counts (e.g., 8-bar or 16-bar section blocks) locked to the session BPM and time signature.

2. **Arrangement & Layering** (`library/arrangement/global_composition.md`):
   * **Frequency Management:** Reserve specific frequency bands for core elements (sub-bass below 80 Hz, kick punch at 90–120 Hz, vocals/lead melody at 1–4 kHz).
   * **Stem Distribution:** Introduce or remove instrument stems every 4 to 8 bars to maintain energy progression and prevent static arrangements.
   * **Dynamic Arc:** Scale velocity and channel volumes across the arrangement so that the primary `Chorus` or climax reaches peak loudness and density.

---

## 🎤 Phase 3: Vocal & Prosody Alignment (Singer Agent)

1. **Prosody & Metric Accent** (`library/vocals/prosody_stress.md`):
   * Align lyric stress patterns with the downbeats and metric accents established by the Composer Agent's drum/bass rhythm.
   * Insert pause markers, commas, or breath spaces at natural syntactic boundaries to maintain human prosody.

2. **Vocal Direction & Styling** (`library/vocals/global_vocal_techniques.md`):
   * Apply emotion tags (`[whispers]`, `[softly]`, `[belt]`, `[sighs]`) to lyrics, matching the dynamic level of the underlying arrangement.
   * Ensure vocal pitch range and register align with the chord voicings generated in `core_harmony.md`.

---

## 🔄 Execution Workflow Summary

```text
  [Read COMPOSER_GUIDE.md]
             │
             ├──► Composer Agent ──► Parse harmony/ & arrangement/ ──► Generate MIDI & FL Studio Layout
             │
             └──► Singer Agent   ──► Parse vocals/ ─────────────────► Generate ElevenLabs Audio & Timing Cues
```