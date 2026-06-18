# CAS PCBA Engineer — Changelog

## 2026-06-18 — v0.5 (two more worked recipes: COB + CDAB)

Extended the recipe/limiting-reagent tooling (Ch 14) onto two more boards:
- **Ch 19 (COB)** — new "Recipe View: What Produces Entrainment": the PLL
  outcome `Ω_entrainment` as `Θ = 1·^1^C + 1·^4^E + 2·^3^O`. Worked case shows a
  high-insight, high-Q compulsion where behavioral plasticity (`^3^O`, the VCO)
  is the limiting reagent (`Y_T=0.30`) — the structural form of "I understand it
  and still can't stop." Therapy = feeding the bottleneck (lower L widens the
  lock range = raises effective `^3^O`); lock-range = the η-preserving operating
  condition; steady reference = catalyst, chaos = inhibitor.
- **Ch 20 (CDAB)** — new "Recipe View: What Produces a Synthesis": `Ω_synthesis`
  (a `×` fusion) as `Θ = 1·^1^C + 2·^4^P + 1·^6^C`. Worked stalemate case where
  the integrative drive (`^4^P|T`, will-to-unify) is the limiting reagent
  (`Y_T=0.25`) — the well-characterized disagreement that never resolves. Names
  the **leakage** path too: poor CMRR contaminates the difference signal (present
  but wrong = `Λ`), so good CMRR is a precondition for sound synthesis.

Rebuilt PDF (6×9). Canonical Noetic names preserved; CCDL listings unchanged.

## 2026-06-18 — v0.4 (recipes / production semantics developed)

Paid off the Chapter 2 recipe forward-promise and made recipes a first-class
circuit-design tool:
- **Ch 14** — new section *"Recipes and the Limiting Reagent: What Caps the
  Outcome"* developing the full v7.6 production semantics as circuit analysis:
  recipe `Θ`, state vector `S`, **theoretical yield** `Y_T = minᵢ(xᵢ/aᵢ)`,
  **limiting reagent** `L`, **actual yield** `Y_A`, **efficiency** `η`, **excess
  capacity** `ε`, **leakage/side-reaction** `Λ` (vs lacunarity vs inversion), and
  **catalyst/inhibitor** `κ/ι` — tied to the chapter's power-budget/efficiency
  material. Includes a worked **CSB refusal recipe** showing that the Chapter 18
  starvation attack is exactly a limiting-reagent failure (principled aversion
  starved below the saturation-lock threshold), with the redundant-register fix
  reframed as raising the floor on the limiting reagent.
- **Ch 2** — the recipe forward-reference now points concretely to Chapter 14
  and names the limiting reagent.
- **Ch 14 exercises** — added the long-promised power-dissipation exercise (14.4,
  which Appendix E already answered but the chapter had never listed — a
  pre-existing phantom-answer gap, now closed) and a new limiting-reagent
  exercise (14.5); Appendix E gains the 14.5 worked answer.
- **Appendix G** — the Recipe (Θ) glossary entry expanded to define the whole
  production-semantics family.

Rebuilt PDF (6×9). CCDL code listings unchanged; canonical Noetic names preserved.

## 2026-06-18 — v0.3 (vector charts + multilayer-board diagram)

Added five more vector figures, replacing ASCII sketches / filling gaps where
the text described a chart but had none. Charts use `pgfplots` (added to
`build/figures_preamble.tex`); all are grayscale-legible (color + line style):
- **Ch 9** — CJT characteristic-curve family: effect-vs-cause traces at bias
  {0.2, 0.4, 0.6, 0.8}, with the load line (`R=30`) and the labelled Q-point
  (0.43, 0.45), cutoff/active-region/saturation-knee annotations.
- **Ch 16** — two-panel Bode plot: magnitude roll-off to the 0 dB crossover and
  phase to −180°, with gain margin (~20 dB) and phase margin (~30°) marked.
- **Ch 12** — four filter frequency responses (low-pass / high-pass / band-pass
  / notch) on one log-frequency axis, with the −3 dB line and fc/f0 markers.
- **Ch 6** — forgetting curve: stored charge vs time under the chapter's
  `(1−leakage)^t` model, a deep memory (leakage 0.001) vs a leaky one (0.05),
  half-life marked.
- **Ch 17** — multilayer cognitive-board illustration (TikZ): the four Domain
  layers (P/C/E/O) with descent vias v1–v3 and the distinct upward feedback
  via v4 (`^9^O→^0^P`). The CCDL `board { … }` listing was left as code.

Book now carries **12 vector figures**. Rebuilt PDF: 699-page 6×9, zero TeX
errors, zero missing glyphs.

## 2026-06-18 — v0.2 polish (consistency, answer key, vector schematics)

Three review/upgrade passes over the v0.1 draft:

**1. Cross-chapter consistency audit + fixes.** A full audit confirmed the CSB,
the five boards, the Drive rails, the Dials, and the running amplifier are
consistent across chapters and Appendix D. Five surgical fixes applied:
- Ch 21: address-decoder block no longer glosses `^1^C` as "differentiation"
  (now canonical "Mind") — the lone Noetic-naming drift in the book.
- Ch 5: voltage-divider worked build — corrected `V_expand` to 0.40 so the
  formula matches the "expansion is the minority partner" prose.
- Ch 14: reconciled the brownout thresholds with Ch 22/App D (normalized 0–1
  here vs +12V / 2.5V trip on the CPMB, with an explicit note); rewrote the
  thermal response from two stages to the canonical three tiers (Warning −25% β
  / Critical force `^0^P` rest ~5min / Emergency all-CJT cutoff); pinned the
  brownout β-derate to 0.5; updated the datasheet and Key Takeaways to match.

**2. Appendix E answer-key verification + fixes.** Every chapter's exercises
were checked against the answer key (104 answers, 4/chapter — no gaps, no
phantoms). Three corrections: Ch 22 Ex 22.1 named the wrong +12V rails (F3/F7,
not F3/F5) and carried a self-contradicting note; Ch 2 Ex 2.4 mis-described a
forward E→P move as the sanctioned O→P feedback path.

**3. Vector schematics.** Replaced the main ASCII block diagrams with
professional TikZ figures (true vector, native to the LaTeX pipeline), domain-
colored (P gold / C blue / E red / O green): the CJT terminal diagram (Ch 3),
the five board signal-flow diagrams (CSB Ch 18, COB Ch 19, CDAB Ch 20, CMB
Ch 21, CPMB Ch 22), and the deployment ladder (Ch 25). Styles live in
`build/figures_preamble.tex`; CCDL code listings were left as code.

Rebuilt PDF: 695-page 6×9 paperback, zero TeX errors, zero missing glyphs.

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
