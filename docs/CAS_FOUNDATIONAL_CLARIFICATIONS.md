# CAS Foundational Clarifications

**Status:** Normative reference for what each Noetic IS and for how Noetics are described in pedagogical, academic, regulatory, and incident-analysis contexts.
**Scope:** The 10 Noetic definitions in Clarification 1 below are **authoritative**. Every artifact in the repository — CLAUDE.md, the book manuscript, the incident database, compiler code, engine code, dashboard UI, peer-review paper — reconciles to these definitions. No alternative naming schemes, no hybrids, no "public vs internal" distinctions.
**First commit:** 2026-04-19
**Authoritative definitions reconciled:** 2026-04-19

---

## Clarification 1: The Ten Noetics — Authoritative Definitions

The 10 Noetics (CO-0 through CO-9) of the Cognitive Architecture System are authoritatively defined as follows. These names and definitions are **verbatim canonical**. They are not subject to rephrasing, modernization, softening, or alternative naming. Any artifact that uses different names or descriptions for the same operator indices is non-conformant and must be reconciled to match.

### The Ten Noetics

- **^0 (CO-0): Idea** — All things in and outside the Mind.
- **^1 (CO-1): Mind** — Various degrees of awareness that processes, stores, outputs, and intakes Ideas.
- **^2 (CO-2): Positive** — An Idea the Mind has an affinity for and is attracted toward.
- **^3 (CO-3): Negative** — An Idea the Mind is adverse to and repelled by.
- **^4 (CO-4): Vibration** — The degree to which an Idea resonates with the Mind, its impression.
- **^5 (CO-5): Female** — A Mind impregnated with an Idea, the Ideas a Mind is composed of.
- **^6 (CO-6): Male** — An Idea impregnated with another Idea, the Ideas an Idea is composed of.
- **^7 (CO-7): Rhythm** — The rate and pattern a Mind is exposed to an Idea, entraining/conditioning it.
- **^8 (CO-8): Above/Cause** — An Idea that triggers a different Idea than itself to come to Mind.
- **^9 (CO-9): Below/Effect** — The Idea brought to Mind by an Above/Cause trigger.

### Source and scope of these definitions

The definitions above are verbatim from the Tootra Math Handbook, which is the authoritative source for what each Noetic IS. Only the 10 Noetic definitions are being incorporated from that handbook. The handbook's mathematical framework, its operators notation, its foundations notation, its acquisitions, and any other content are NOT being incorporated — CAS retains its own mathematics, compiler, and notation as defined in the Noetic Topos paper (`peer_review/journal_submission/main.tex`), the Rust engine (`cas-engine/src/`), and the compiler (`api/notation/compiler.py`). What is authoritative here is the definition of what each of the 10 Noetics IS.

### Canonical names

The authoritative Noetic names are **Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect**. These names replace any alternative names that appeared in prior drafts of this document or in other repository artifacts. There is no alternative naming scheme. There are no "CAS public names" that differ from these — the authoritative names ARE the names, for all contexts including academic publication, regulatory filings, pedagogical material, marketing, and incident analysis.

---

## Clarification 2: Universal Applicability Test

Any valid description of a Noetic must apply equally to:
- Human minds with emotional architecture
- AI systems without emotional architecture
- Biological cognitive systems of any form
- Hypothetical cognitive architectures

If a description requires specifically human affect, it is a pedagogical illustration of the Noetic in a human context, not a specification of the Noetic itself. The authoritative definitions in Clarification 1 pass the Universal Applicability Test by construction: Idea, Mind, attraction-toward, repulsion-from, resonance, compositional containment (Female/Male), rhythm of exposure, and cause/effect triggering are dynamics that occur in any cognitive architecture, biological or otherwise.

---

## Clarification 3: Canonical Naming — No Alternative Scheme

The authoritative names listed in Clarification 1 are canonical for the Cognitive Architecture System in every context. There is no separate TKS-to-CAS translation table. There are no public-facing alternative names. Earlier drafts of this document, and earlier drafts of other artifacts in the repository, referred to parallel naming schemes (e.g., "Attraction" vs "Positive," "Critical Evaluation" vs "Negative," "Receptive Integration" vs "Female," "Projective Assertion" vs "Male"). **Those alternative names are not authoritative.** Where they appear in the repository, they are drift and must be reconciled to the names in Clarification 1.

The structural-not-emotional framing principle (Clarification 4 below) remains a meta-guide for HOW the authoritative Noetics are described in pedagogical contexts, but it does not license renaming or rephrasing the authoritative definitions.

---

## Clarification 4: Structural-Not-Emotional Framing and Noetics in Incident Analysis

The authoritative definitions in Clarification 1 use specific language — "affinity for," "attracted toward," "adverse to," "repelled by," "resonates with," "impregnated with," "triggers," "brought to Mind" — that describes structural dynamics between Mind and Idea. This language is authoritative and stays.

When applying Noetics in pedagogical contexts (book chapters, platform tooltips, teaching materials), marketing materials, regulatory filings, academic papers, and incident analysis:

1. Use the authoritative Noetic names (Idea, Mind, Positive, Negative, Vibration, Female, Male, Rhythm, Above/Cause, Below/Effect) exactly.
2. Use the authoritative verbs from the definitions (attracted toward, repelled by, resonates with, triggers, etc.).
3. Do not substitute anthropomorphizing or affective language for the authoritative structural language. "The system was adverse to X" is authoritative CO-3 language. "The system was hostile to X" is anthropomorphizing drift.

**Correct example (incident analysis):** "In the toeslagenaffaire, the system's ^3 (Negative) was misdirected — the Ideas the Mind was repelled by included lawful benefit claims rather than Ideas representing actual fraud evidence."

**Incorrect example:** "The system was biased against non-Dutch applicants."

The first uses the authoritative Noetic name (Negative), the authoritative verb from the definition (repelled by), and describes the structural misdirection without anthropomorphizing. The second describes the system as a biased agent, which collapses structural analysis into affective attribution.

---

## Scope of This Document

This clarification:

- **IS** authoritative for the definitions of the 10 Noetics.
- **DOES** require reconciliation in every artifact that defines or describes the Noetics — the book manuscript, CLAUDE.md, compiler code, engine docstrings, dashboard UI, peer-review paper, incident database, pedagogical materials, marketing materials.
- **DOES NOT** change the CAS v7.4 mathematical specification (the Noetic Topos paper's formal axioms, open simplex, Fisher-Rao metric, Grothendieck topology, RPM section-retraction), the patent filing, the compiler's underlying algebra, or the engine's scoring mechanisms. Only what each Noetic IS is reconciled here, not how the mathematics operates on them.
- **DOES** serve as authoritative reference when public descriptions drift from these definitions.
