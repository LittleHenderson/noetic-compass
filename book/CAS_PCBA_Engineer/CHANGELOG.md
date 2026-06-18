# CAS PCBA Engineer — Changelog

## 2026-06-18 — v0.1 full draft + designed PDF

Wrote the complete first draft of *CAS PCBA Engineer: Designing Cognitive
Circuits with the Cognitive Architecture System*, following `CAS_PCBA_Engineer_BOOK_PLAN.md`
and the `docs/working/CJT_PCBA_IMPLEMENTATION_BLUEPRINT.md` reference designs.

**Content (~169k words across 36 Markdown files):**
- Front matter (`00_Front_Matter.md`): title, copyright, preface, how-to-use.
- 26 chapters in 5 parts:
  - Part I — Foundations (Ch 1–4): why circuits, CAS notation in one chapter,
    the transistor → CJT, first cognitive circuit.
  - Part II — The Component Library (Ch 5–10): resistors, capacitors, inductors,
    diodes, the CJT deep dive, special-purpose components.
  - Part III — Circuit Design (Ch 11–16): amplifiers, filters, oscillators,
    power management, mixed-signal, feedback systems.
  - Part IV — Cognitive Circuit Boards (Ch 17–22): the CCB design process and
    the five reference boards — CSB, COB, CDAB, CMB, CPMB.
  - Part V — Deployment & Governance (Ch 23–26): testing, debugging, production
    deployment, certification/governance.
- 8 appendices (A–H): notation quick-reference, component datasheets, CCDL
  language reference, consolidated CCB reference designs, exercise answers, lab
  setup guide, glossary, further reading.
- `STYLE_GUIDE.md`: internal authoring contract (canonical Noetic notation,
  voice, chapter template, anti-drift rules) — not part of the shipped book.

**Design conventions held throughout:**
- Canonical Noetic names only (Idea, Mind, Positive, Negative, Vibration,
  Female, Male, Rhythm, Above/Cause, Below/Effect) — no Scheme-A/B/C drift.
- v7.7 operator discipline (`+` / `×`-with-named-Ω / `|⟨…⟩`).
- Honesty: CCDL/compiler presented as a specified design (per the implementation
  blueprint roadmap); all parameters are design choices, no fabricated run or
  benchmark results; USPTO Provisional #64/037,173 stated as real.
- Running spine: the Cognitive Safety Board (CSB) is built across the book.

**Designed PDF:** `CAS_PCBA_Engineer.pdf` — 695-page 6×9 trade paperback,
memoir/XeLaTeX, Palatino body, DejaVu Sans Mono code, clean TOC, numbered
chapters/sections, part dividers. Reproducible via `build/` (see
`build/BUILD_README.md`). Compiles with zero TeX errors and zero missing glyphs.

**Status:** v0.1 complete draft. Suggested next passes — technical review of
worked CCDL builds for cross-chapter parameter consistency; verify all
Appendix E answers against final exercise text; integrate any figures/diagrams
beyond the ASCII schematics; copyedit pass.
