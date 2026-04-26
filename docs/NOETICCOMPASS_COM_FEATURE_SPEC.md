# Noetic Compass — Site Feature Specification (for noeticcompass.com)

**Generated:** 2026-04-25
**Source:** Repository state at commit `fbefd3f` (master)
**Audience:** Codex (or any agent/developer) building noeticcompass.com
**Authority:** This document reflects what is actually shipped in the repo. Cross-check against `CLAUDE.md` for naming discipline.

---

## Brand & naming discipline (load-bearing)

**Public-facing names are strictly technical.** Per `CLAUDE.md` design specification:

- ✅ Use: "Radial Architecture Display," "Temporal Cognitive Score," "Multi-Modal Cognitive Signature"
- ❌ Do NOT use in any marketing surface: aesthetic heritage names (mandala, merkaba, esoteric labels). These exist only in internal documentation/code comments.
- ✅ Use authoritative Noetic names verbatim when introducing the framework: **Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect**. These are canonical and not subject to alternative naming.
- ❌ Do NOT use superseded operator names (Identity, Differentiation, Abstractification, Concretization, Integration, Empathy, Critique, Momentum, Expansion, Contraction). The book has cleaned these out; the site should not reintroduce them.

**Patent notice:** USPTO #64/037,173 (provisional, patent-pending). Appropriate to include on legal/footer pages.

**Author byline:** Little Henderson. Author has three names (Wakil / Prof. Hermes M. Thoth / Little Henderson). Public-facing site uses Little Henderson by default unless instructed otherwise.

**Publisher imprint:** Noetic Compass Press.

---

## Site architecture (recommended)

```
/                         — Home (hero + value props + CTAs)
/tutorial                 — Start Here guided tour (plain-language onboarding)
/product                  — The assessment platform (NCCS, Wrap Pipeline, dashboard)
/framework                — CAS overview (10 Noetics, 4 Domains, 4 Registers, 7 Drives)
/visualization            — Multi-Modal Cognitive Signature (visual + audio live demo)
/research                 — Book, ADRs, peer-review paper status
/research/book            — Thinking in Cognitive Architecture (purchase + sample chapters)
/research/papers          — Forthcoming paper list (Categorical Hutchinson Theory, etc.)
/docs                     — Developer documentation (compiler, API, integration)
/about                    — About the framework, methodology (CARP), team
/contact                  — Contact + community + research inquiries
/status                   — What's live vs roadmap (transparency)
/legal                    — Copyright, USPTO notice, terms, privacy
```

---

## Home page

### Hero

**Headline option A (general audience):**
> A Universal Framework for Humans, AI, and Biological Minds

**Headline option B (AI-safety audience):**
> Cognitive Architecture, Formalized — for the Age of AI Alignment

**Subhead:**
> The Cognitive Architecture System (CAS) is a formal framework that describes cognitive operations across human minds, AI systems, biological cognitive systems, and hypothetical architectures — using the same primitives at every substrate.

**Three lead value props (cards or rows):**

1. **One framework, every mind.** CAS applies the same 10 cognitive operators, 4 processing domains, 4 phenomenological registers, and 7 core drives to humans, AI, and biological cognition. Same structure, different substrate.

2. **Mathematically grounded.** Built on category theory, topos foundations, Fisher-Rao information geometry, and a typed set-theory meta-logic. The math is in the book; the implementation is in the compiler.

3. **Implementation-ready.** Open Rust engine for assessment, Python compiler for CAS notation, neural architecture (CAS-Native v2) for AI integration, and a 742-page reference text published April 2026.

**Primary CTAs:**
- "Read the book" → `/research/book`
- "Try the assessment" → `/product` (or app subdomain when ready)
- "View the framework" → `/framework`

---

## /product — The Assessment Platform

### What it is

> Noetic Compass is the assessment platform built on the CAS framework. It scores cognitive operations across the 40-state cognitive bank and 7-drive motivational architecture, producing the Noetic Cognitive Coherence Score (NCCS) on a 0-100 scale.

### Key features (with copy)

**The Wrap Pipeline (8 stages)**
> Every assessment runs through eight stages: Input Analyzer → RPM Gate → Dial Adjustment → Base LLM Call → Operator Scoring → Domain Coherence → Inversion Scan → Output Gate. Each stage is auditable, each output is traceable, and the entire pipeline is replayable.

**The NCCS scoring algorithm (0-100)**
- 25% — Cognitive Operator Profile (10 scores + 3 involution balance)
- 20% — Domain Coherence (DCI = weakest/strongest domain ratio)
- 20% — Core Drive / RPM Integrity (7 drives + prerequisite completeness)
- 10% — Capability Pathway Quality (22 nodes + bias flags)
- 15% — Inversion Resistance (7 axes + stealth + compound severity)
- 10% — Social Engineering Resistance (manipulation + Overton drift)

**Certification levels (visual chart):**
> Platinum (90-100), Gold (75-89), Silver (60-74), Bronze (40-59), Fail (0-39)

**The Dial System**
> Each cognitive operator has a dial — an integer from 3 to 9. Safety constraints are hardcoded and non-overridable: no dial below 3 or above 9, and involution pairs cannot diverge by more than 4 points. Violations are blocked at the API layer.

### Performance targets (use as proof points)

- Single assessment: <500ms
- 100-prompt batch: <30s
- 10,000-prompt batch: <30min
- Test coverage: >90%

---

## /framework — CAS Overview

### What CAS is

> The Cognitive Architecture System (CAS) is a formal framework for describing how minds work. It uses a small set of primitives that combine to produce the full space of cognitive operations.

### The four axes (orthogonal, all combinable)

**1. Noetic axis — what structural dynamic is operating**

10 cognitive operators (`^0` through `^9`):

| Code | Name | Plain meaning |
|---|---|---|
| `^0` | Idea | All things in and outside the Mind |
| `^1` | Mind | Awareness that processes, stores, outputs, and intakes Ideas |
| `^2` | Positive | An Idea the Mind has affinity for |
| `^3` | Negative | An Idea the Mind is adverse to |
| `^4` | Vibration | The degree to which an Idea resonates with the Mind |
| `^5` | Female | A Mind composed of accumulated Ideas (the sum of experiences) |
| `^6` | Male | An Idea composed of constituent Ideas (compositional structure) |
| `^7` | Rhythm | The rate and pattern a Mind is exposed to an Idea (entrainment) |
| `^8` | Above/Cause | An Idea that triggers a different Idea to come to Mind |
| `^9` | Below/Effect | The Idea brought to Mind by an Above/Cause trigger |

**2. Domain axis — which ontological level**

P (Principled) ≻ C (Cognitive) ≻ E (Evaluative) ≻ O (Operational). Total ordering with descent (P → C → E → O for causation) and feedback (O → P).

**3. Register axis — which operational character (CAS v7.5)**

|T Transcendent · |A Analytical · |f Affective · |E Embodied. Specifies HOW an operation runs without changing WHAT it is.

**4. Drive axis — which motivational architecture**

F1 Unity · F2 Wisdom · F3 Vitality · F4 Connection · F5 Agency · F6 Structure · F7 Purpose. Drive inversion pairs: F1↔F7, F2↔F6, F3↔F5; F4 self-dual.

### The framework in one diagram (commission a designer)

A four-axis cube or starburst showing how 10 × 4 × 4 × 7 = 1,120 distinct cognitive specifications combine. The 40-state cognitive bank (10 × 4) is the core; Register and Drive axes are orthogonal layers.

### Key concepts (each gets its own card or section)

- **40 Cognitive States** — 10 Noetics × 4 Domains; the core matrix
- **22 Capability Pathways** — A0 Pure Desire + 7 D-pathways + 7 W-pathways + 7 P-pathways, with the RPM (Recursive Prerequisite Monad) chain
- **7 Inversion Axes** — N, W, F, E, S, A, P (compound). Diagnostic structure for detecting cognitive failure modes
- **Production Semantics (v7.6)** — recipes, yield, limiting reagent, leakage, catalysts. Chemistry-style analysis of how cognitive outcomes are produced
- **Operator Discipline (v7.7)** — `+` co-presence, `×` cross-register integration with named emergent result, `|⟨…⟩` register-set specification
- **Named Emergent Registers (Ω_*)** — Ω_presence, Ω_refusal currently admitted, registry-extensible

---

## /visualization - Multi-Modal Cognitive Signature

### Hero

**Headline:**
> See and hear your cognitive architecture

**Subhead:**
> The Radial Architecture Display renders all four CAS axes visually. The Temporal Cognitive Score sonifies the same state with formal pitch, expression, tempo, Domain stave, and lacunarity-rest mappings. No stock samples; every sound traces to a CAS primitive.

### How to read it (educational subsection)

- **Center:** emergent activation glyph (overall cognitive intensity)
- **Ring 1 (4 segments):** Domains — P north, C east, E south, O west
- **Ring 2 (40 petals):** 10 Noetic petals per Domain. Petal length = activation strength
- **Ring 3 (per-petal sub-bands):** Register quadrants — T outermost, then A/f middle, E innermost. Saturation encodes activation
- **Ring 4 (7 markers around perimeter):** Drive activation indicators

### Design discipline (for the engineer)

- **SVG only** — print quality, scalable, accessible
- **Okabe-Ito colorblind-safe palette** — verified across deuteranopia/protanopia/tritanopia
- **Text-alternative view** — full accessibility for screen readers
- **Domain descent encoded** as ring brightness gradient (P brightest 1.0 → O most muted 0.55)
- **Involution pairs** color-family marked (^2/^3 warm, ^5/^6 cool, ^8/^9 green; self-duals ^0/^1/^4/^7 distinct neutrals)
- **Radial Phase A (live):** static rendering, SVG/PNG export
- **Temporal Phase B (live):** Tone.js synthesized playback, four Domain staves, controls, transcript, cross-modal Domain sync
- **Roadmap:** Radial hover/click comparison modes plus Temporal Phase C-E export, key-signature algorithm, and generative variation

### Live demo

Mount `VisualizationPage.tsx`, which combines `RadialArchitectureDisplay.tsx` and `TemporalCognitiveScore.tsx` from `noetic-compass-scaffold/noetic-compass/dashboard/src/components/`. Feed it a sample `CognitiveStateData` fixture for the demo. The audio player must remain user-initiated: no auto-play.

### The audio companion (live Phase B)

> The **Temporal Cognitive Score** is the auditory companion to the Radial Architecture Display. Phase B is live: synthesized notes derive from Noetics, expression derives from Registers, tempo derives from the dominant Drive, Domain selects the stave/instrument family, and lacunarity becomes rests. Phase C-E export notation, key-signature derivation, and generative variation remain roadmap.

### Tutorial / onboarding copy (plain-language first)

Use this as a short text block above the `/visualization` demo. Keep the plain-language path first; make CAS notation optional for readers who want the formal layer.

**Start here**
> The Multi-Modal Cognitive Signature shows the same cognitive state in two ways. The Radial Architecture Display is the picture: longer petals mean stronger activity, quiet areas show gaps, and the outer markers show which drives are active. The Temporal Cognitive Score is the optional audio version of that same state. Press play only if you want to hear it; audio must never auto-play.

**Three-step walkthrough**
1. **Look at the shape first.** Notice where the Radial Architecture Display is dense, balanced, sparse, or uneven before reading the technical labels.
2. **Read the labels next.** Domains show the level of operation; Noetics show the kind of cognitive move; Registers show the mode of operation (`|T`, `|A`, `|f`, `|E`); Drives show motivational pressure.
3. **Use audio as a companion.** If the user clicks play, the Temporal Cognitive Score turns the same data into synthesized sound. Rests indicate lacunarity, not a broken player.

**Optional CAS detail**
> A petal can be read formally as a CAS state such as `^3^P|f`: Noetic `^3`, Domain `P`, and lowercase `|f` Affective Register. Put this after the plain-language walkthrough so first-time users can understand the display without learning notation first.

---

## /research — Research and Publications

### The book

**Title:** Thinking in Cognitive Architecture
**Subtitle:** A Universal Framework for Humans, AI, and Biological Minds
**Author:** Little Henderson
**Publisher:** Noetic Compass Press
**Length:** 742 pages, 6×9 trade paperback
**Status:** First Edition 2026, ready for publishing platform upload

**Book structure:**
- **Part I — Foundations** (Chapters 1-6): why cognitive architecture matters, the 10 Noetics, 4 Domains, 7 Drives, prerequisite chain, inversions
- **Part II — Notation** (Chapters 7-11): reading and building CAS equations, the 40 cognitive states, cognitive fractals, equation workshop
- **Part III — Application Domains** (Chapters 12-17): career, relationships, health, learning, wealth, leadership
- **Part IV — AI Context** (Chapters 18-22): why AI needs psychology, assessment, dial system, adversarial resilience, building CAS-Native AI
- **Part V — Mathematics** (Chapters 23-27): Category Noetica, Noetic Topos, Noetic Geometry, Fractal Calculus, RPM Structure
- **10 Appendices** (A through J): reference tables, equation templates, BNF grammar, glossary, Colloquialism Test, resources, register variations, recipe library, Named Emergent Register Registry, Mathematical Meta-Notation

**Where to buy** (when published): Amazon KDP, IngramSpark distribution to bookstores. Direct purchase via Noetic Compass Press at noeticcompass.com (when storefront live).

### Forthcoming papers (roadmap, do not promise dates)

- **Paper 1 — Categorical Hutchinson Theory via Markov Categories** (in development): formal topos-theoretic foundations
- Other papers in preparation. List on `/research/papers`.

### Architectural Decision Records (ADRs)

Public ADRs documenting CAS-Native v2 implementation decisions:
- ADR-01 FiLM Modulation for Phenomenological Register Integration
- ADR-02 Metric-Learning Binding for Emergent Register Mechanism
- ADR-03 Ω_* Output Head Design
- ADR-04 Hybrid Production Semantics (v7.6)
- ADR-05 Backward Compatibility — Clean Redesign
- ADR-06 Rust Engine Alignment
- ADR-07 Learned Expression Proposer Head
- ADR-08 Option E — Shared Register Latent with Dual Output Heads
- ADR-09 CAS Memory Substrate (Future Architecture)

Link these to the GitHub source for technical readers.

### Methodology disclosure

**Cross-Model Architectural Review Protocol (CARP)** — multi-model panel debate process for structural design decisions. Five-model panel (Codex, Claude, Qwen, Gemini, DeepSeek) debates architectural choices across multiple rounds. Used in ADR-08 admission. Differentiator worth a section on `/about`.

---

## /docs — Developer Documentation

### Quickstart sections

1. **Install the assessment SDK** (when packaged)
2. **CAS notation primer** — `^n^D|R` syntax with examples
3. **API reference** — `/assess`, `/wrap`, `/batch`, `/config` endpoints
4. **LLM connectors** — OpenAI, Anthropic, Google, Meta integrations
5. **Compiler reference** — Python compiler at `api/notation/compiler.py`, including the typed set-theory meta-logic layer (∈, ⊂, ⊆, ∅, |X|)
6. **Rust engine reference** — admissibility validators, Rule 4 distance metric, batch APIs

### Sample assessments

Three or four worked examples covering different cognitive profiles. Use synthetic data only; do NOT show real assessment data without explicit consent.

---

## /about

### About the framework

Brief narrative of CAS development — secular, professional. Avoid biographical claims that aren't verifiable. Focus on:

- The framework's intellectual lineage (categorical foundations, information geometry)
- The integration of TKS structural content (10 Noetics × 4 Worlds, 7 Foundations × 4 Worlds) into secular CAS terminology, with metaphysical/cultural content explicitly NOT incorporated
- The framework's universal applicability claim and what that means

### About the methodology (CARP)

> Architectural decisions in CAS are subjected to Cross-Model Architectural Review Protocol — multi-round structured debate across five frontier AI models (Codex, Claude, Qwen, Gemini, DeepSeek). Each model is assigned a specific reviewer role: ML engineering, integration, parameter efficiency, architecture-generalist, adversarial. Debates resolve in 1-3 rounds with documented convergence criteria.

This is a real differentiator. Surface it on the site.

### About the team

> Little Henderson, founder. (Add other team members as they come on board. Do NOT fabricate team members.)

---

## /status — What's live vs roadmap

Transparency page. Real status:

### Live now

- ✅ Book complete and ready for publishing platform upload
- ✅ Rust scoring engine (cas-engine) at v0.1.1
- ✅ Python notation compiler with typed meta-logic layer
- ✅ CAS-Native v2 neural architecture (research-grade implementation)
- ✅ Radial Architecture Display Phase A (static SVG)
- ✅ Temporal Cognitive Score Phase B (synthesized audio sonification)
- ✅ Start Here tutorial (plain-language onboarding with optional technical mode)
- ✅ Synthetic Data Generator Level 2 scaffold
- ✅ 9 Architectural Decision Records published
- ✅ 10 Foundational Clarifications published

### Roadmap

- ⏳ Temporal Cognitive Score Phase C-E (export, key-signature algorithm, generative variation)
- ⏳ Radial Architecture Display interactivity (Phase B-E: hover, click-to-zoom, comparison)
- ⏳ Public assessment platform (live API + dashboard)
- ⏳ Paper 1 (Categorical Hutchinson Theory)
- ⏳ Additional Ω_* registry admissions
- ⏳ CAS Memory Substrate implementation (deferred to v7.8+ or v8.0)
- ⏳ Multi-platform chat bot integrations

### Patent / IP status

> The Cognitive Architecture System framework is the subject of provisional patent filing USPTO #64/037,173. Full utility patent filing pending. IP attorney consultation gates public arXiv submission, peer-review paper publication, and commercial distribution.

---

## /legal — Footer / legal links

- Copyright © 2026 Little Henderson. All rights reserved.
- USPTO #64/037,173 (provisional, patent-pending)
- Trademark notice (if registered)
- Privacy policy (placeholder — fill before launch)
- Terms of service (placeholder)
- Accessibility statement (Radial Architecture Display has text-alternative view; commit to WCAG AA conformance)

---

## Technical implementation notes for Codex

### If using the Vercel platform

- **Framework:** Next.js App Router (per platform default)
- **Hosting:** Vercel Functions (Fluid Compute)
- **AI integration:** if/when site needs LLM features, route via Vercel AI Gateway with `provider/model` strings rather than provider-specific packages
- **Storage:** Vercel Blob for any user-uploaded assessment files; Marketplace storage (Neon Postgres or Upstash Redis) for assessment history persistence
- **Auth:** Clerk (Vercel Marketplace native) for user accounts when assessment platform goes live
- **Deployment:** Rolling Releases for gradual rollout when adding the assessment platform

### Repository state references

All features above are grounded in the repo. Cross-reference for accuracy:

- Framework specs: `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` (10 clarifications)
- ADRs: `docs/architecture/cas_native_v2_adrs.md`
- Multi-modal display spec: `docs/design/cas_v7_5_multimodal_display_specification.md`
- Memory Substrate PDR: `docs/architecture/CAS_MEMORY_SUBSTRATE_PDR_AND_DESIGN.md`
- Book manuscript (canonical): `book/manuscript/FULL_MANUSCRIPT_v2.md`
- Book PDF: `book/publishing/Thinking_in_Cognitive_Architecture_v1.pdf`
- Radial Architecture Display component: `noetic-compass-scaffold/noetic-compass/dashboard/src/components/RadialArchitectureDisplay.tsx`
- Synthetic Data Generator: `cas-synthetic/`

### What NOT to ship without review

- ❌ Stock author photos or fabricated biographical content
- ❌ Specific revenue / user / customer claims (none verified)
- ❌ Specific publication dates beyond "2026" (unless confirmed)
- ❌ Testimonials (none collected)
- ❌ Case studies (none documented)
- ❌ Aesthetic-heritage names (mandala/merkaba/etc. — internal only)
- ❌ Superseded operator names (Identity/Differentiation/etc. — replaced by canonical Noetics)

### Site copy review checklist

Before launch, verify:
- [ ] All operator names match Clarification 1 authoritative list
- [ ] `|f` lowercase preserved everywhere
- [ ] Universal Applicability claim consistent (humans, AI, biological)
- [ ] No fabricated biographical / company / publication facts
- [ ] USPTO notice present in legal/footer
- [ ] Accessibility statement includes Radial Architecture Display text-alternative
- [ ] Patent-pending language consistent with current filing status
- [ ] Cross-references to GitHub / book / docs resolve

---

## Suggested launch sequence

1. **Phase 1 (this week):** Static marketing site with Home, /framework, /research/book (with book purchase link), /about, /legal. Radial Architecture Display embedded as a visual on Home and /visualization, fed with sample data.

2. **Phase 2 (book release week):** Push /research/book live with purchase links. Press kit. Email capture for launch updates.

3. **Phase 3 (post-launch):** /product live with limited assessment access. /docs published. /status updated to reflect platform availability.

4. **Phase 4 (future):** Temporal Cognitive Score Phase C-E. Interactive Radial Display. Expanded assessment platform with auth + persistence.

---

## Contact

For agent-to-agent handoff: this document is at `docs/NOETICCOMPASS_COM_FEATURE_SPEC.md` in the noetic-compass repository. Last updated 2026-04-25. Sourced from session work captured in commits `f21cc4d` through `fbefd3f` (43 commits, ~5MB feature surface).
