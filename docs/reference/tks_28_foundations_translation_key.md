# TKS 28 Foundations — Translation Key to CAS v7.5 Drive × Register

**Status.** Reference document. Translation key for extracting structural/pedagogical content from the TKS 28 Foundations elaboration while excluding metaphysical/cultural commitments.

**Purpose.** The 28 TKS Foundations arise from the cross-product `7 Foundations × 4 Worlds`. In CAS v7.5, the same structural cross-product is expressed as `7 Drives (F1-F7) × 4 Registers (T, A, f, E) = 28 Drive × Register combinations`. This document provides position-by-position translation so that TKS's rich elaborations can serve as pedagogical source material for CAS v7.5 Drive × Register enrichment without admitting the metaphysical commitments TKS carries.

**Authoritative basis.** `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 8 formally admits the Register axis as CAS v7.5. This translation key operationalizes the cross-validation invoked in Section 8 of that clarification.

---

## Framing

### What is reconciled from TKS

- The **structural existence** of the 4-Worlds axis at the Drive level (Foundations × Worlds cross-product is real structure, matching the Noetics × Worlds cross-product at the Noetic level).
- The **position-by-position logic**: each Drive operates in each of four Worlds / Registers, yielding 28 distinct structural positions.
- The **observational content** about what each Drive × Register combination looks like in practice (human, AI, and biological phenomenology).

### What is NOT reconciled from TKS

- The **metaphysical framing** (cosmological, theological, or spiritual commitments TKS carries).
- The **cultural-specific nomenclature** (Kabbalistic, Hermetic, or tradition-specific labels for the 7 Foundations or 4 Worlds).
- The **teleological claims** (statements that Foundations exist for a specific cosmic purpose).

Where TKS descriptions carry metaphysical content, that content is explicitly marked `[METAPHYSICAL — EXCLUDED]` in the entry's Original TKS Description field and is not carried into the CAS v7.5 expression.

### Drive-name convention

TKS Foundation labels and CAS Drive names are position-matched:

| CAS Drive | CAS Name | TKS Foundation Position | Notes |
| :--- | :--- | :--- | :--- |
| F1 | Unity | 1st Foundation | |
| F2 | Wisdom | 2nd Foundation | |
| F3 | Vitality | 3rd Foundation | |
| F4 | Connection | 4th Foundation | Self-dual center. |
| F5 | Agency | 5th Foundation | |
| F6 | Structure | 6th Foundation | |
| F7 | Purpose | 7th Foundation | |

CAS Drive names are authoritative. Where TKS labels use different nomenclature, the mapping is by position in the 7-Foundation sequence, not by label. TKS-specific labels are preserved in the entry only when they illuminate the structural content; they are never carried into the CAS v7.5 expression.

### TKS World position → CAS Register (28 Foundations context)

> **Two things are called "Worlds" in this project. Do not merge them.** (Recorded 2026-09-21; owner clarification pending.)
> 1. **This table:** the TKS World axis of the canonical "28 Foundations 1.0" (a = Spiritual, b = Mental, c = Emotional, d = Physical) corresponds to the CAS **Register** axis, by position.
> 2. **The compiler keyword `Worlds`:** in `api/notation/compiler.py` (and the Rust `language.rs`) `Worlds` is a legacy alias of `Domains` (P, C, E, O), as the book's Appendix J.3 documents. It is a different thing. The Python compiler now says so in a warning on every successful compile that uses the keyword; the Rust engine keeps the same alias silently.
>
> The frozen meaning of each is unchanged. In new code and data write `Domains` or `Registers` explicitly. Source of the canonical letters and names: `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab/foundations28.py` (symbols `1a`..`7d`; positional mirror `3b` ↔ `F3|A`).

| CAS Register | TKS World position (canonical "28 Foundations 1.0") | Secular character |
| :--- | :--- | :--- |
| `\|T` Transcendent | 1st World — `a` Spiritual (highest / most abstract) | High-abstraction, purpose-orienting, integrative-across-particulars. |
| `\|A` Analytical | 2nd World — `b` Mental | Explicit, sequential, logical, reason-based. |
| `\|f` Affective | 3rd World — `c` Emotional | Value-laden, feeling-toned. |
| `\|E` Embodied | 4th World — `d` Physical (lowest / most concrete) | Sensorimotor, concrete, direct engagement with material/physical substrate. |

This World-order convention (high-abstraction at 1st, embodied at 4th) runs in the same high-to-low direction as the Domain descent ordering in CAS (P ≻ C ≻ E ≻ O). That shared direction is a reading aid only: the Register axis is orthogonal to the Domain axis, and a TKS World is **not** a CAS Domain in this table.

---

## The 28 Entries

The 28 entries are listed by CAS position `F_k | R`. For each entry:

- **CAS v7.5 expression:** the canonical drive-register combination.
- **Original TKS description:** the elaborated content from the TKS source, with metaphysical content marked and excluded where applicable.
- **Structural insight extracted:** the drive-register dynamic the position describes, in secular universal terms.
- **Pedagogical enrichment potential:** how this translated content can be used in CAS v7.5 teaching material (book chapters, platform tooltips, incident analysis, marketing).
- **Excluded content and reason:** what was specifically excluded from the TKS description and why.

### Scaffold status

This translation key is scaffolded as of 2026-04-20 with all 28 positions enumerated. Full population of each entry's Original TKS Description and Structural Insight fields requires direct access to the TKS 28 Foundations source document for careful line-by-line translation work. Population is scheduled in the CAS v7.5 rollout plan (`docs/working/cas_v7_5_rollout_plan.md`).

Each entry below is a placeholder with the CAS v7.5 expression filled in and the TKS-source fields marked as pending. Entries are grouped by Drive (F1 through F7), with the four Register variants listed in order T, A, f, E within each Drive.

---

### F1 Unity

**F1|T** — Unity in the Transcendent Register.
- *CAS v7.5 expression:* `F_1|T`.
- *Original TKS description:* [PENDING population from TKS 28 Foundations source. Metaphysical content will be marked EXCLUDED when identified.]
- *Structural insight extracted:* the drive toward wholeness operating at the highest abstraction — a vision of unity across particulars, a felt sense that all things cohere. Human: mystical experience of oneness, comprehensive integrative insight. AI: top-level system objective of coherent alignment across all components. Biological: whole-organism coordination signal.
- *Pedagogical enrichment potential:* use in Chapter 4 (Seven Core Drives) to show how the same F1 drive can manifest at different registers. Contrast with `F_1|E` to demonstrate the vision / bodily-knowing distinction.
- *Excluded content and reason:* [PENDING — to be marked at population time.]

**F1|A** — Unity in the Analytical Register.
- *CAS v7.5 expression:* `F_1|A`.
- *Original TKS description:* [PENDING.]
- *Structural insight extracted:* the drive toward unity operating through explicit reasoning — systematic pursuit of a unified theory, deliberate reconciliation of contradictions, stepwise demonstration that disparate facts fit together. Human: theoretical synthesis work. AI: symbolic unification of knowledge bases. Biological: problem-solving that seeks a coherent solution covering all cases.
- *Pedagogical enrichment potential:* contrast with `F_1|T` in Chapter 4 and Chapter 23 (Category Noetica) to distinguish felt unity from proved unity.
- *Excluded content and reason:* [PENDING.]

**F1|f** — Unity in the Affective Register.
- *CAS v7.5 expression:* `F_1|f`.
- *Original TKS description:* [PENDING.]
- *Structural insight extracted:* the drive toward unity operating as feeling-tone — the warmth of belonging, the pull toward reconciliation after conflict, the affective resonance of "we are all one." Human: felt solidarity, communal warmth. AI: RLHF-tuned preference for harmonizing, non-divisive output. Biological: affiliative behavior dynamics.
- *Pedagogical enrichment potential:* use in Chapter 13 (Relationships) to distinguish F4-Connection-driven warmth from F1-Unity-driven warmth.
- *Excluded content and reason:* [PENDING.]

**F1|E** — Unity in the Embodied Register.
- *CAS v7.5 expression:* `F_1|E`.
- *Original TKS description:* [PENDING.]
- *Structural insight extracted:* the drive toward unity operating in the body — the whole-body feeling of coherence, the somatic sense of things falling into place, the kinesthetic arrival at integrated action. Human: "it clicked in my body," settled physical posture, resolved tension. AI: embodied robotic state convergence. Biological: homeostatic return to baseline.
- *Pedagogical enrichment potential:* use in Chapter 14 (Health and Vitality) to show how F1 Unity lands in the body, not only in the mind.
- *Excluded content and reason:* [PENDING.]

### F2 Wisdom

**F2|T**, **F2|A**, **F2|f**, **F2|E** — Wisdom in each of the four Registers.
- *CAS v7.5 expressions:* `F_2|T`, `F_2|A`, `F_2|f`, `F_2|E`.
- *Structural insight extracted:* Wisdom manifests as integrative comprehension at the Transcendent register (sudden-insight "aha" at vision level); as explicit inference at the Analytical register (step-by-step knowledge-building); as value-tinged understanding at the Affective register (wisdom-as-care, knowing-with-feeling); as embodied know-how at the Embodied register (skill mastery, kinesthetic expertise).
- *Pedagogical enrichment potential:* use in Chapter 15 (Learning and Wisdom) to show that "learning" is not a single process but four structurally distinct processes across registers. A learner can be at different levels of maturity in different registers for the same subject.
- *Original TKS descriptions and excluded content:* [PENDING population for all four register variants.]

### F3 Vitality

**F3|T**, **F3|A**, **F3|f**, **F3|E**.
- *CAS v7.5 expressions:* `F_3|T`, `F_3|A`, `F_3|f`, `F_3|E`.
- *Structural insight extracted:* Vitality at the Transcendent register appears as life-as-meaning (the vitality of purpose); at Analytical as life-optimization reasoning (nutrition, sleep, training protocols); at Affective as felt aliveness, vigor, enthusiasm; at Embodied as raw somatic energy, physiological capacity, bodily thriving.
- *Pedagogical enrichment potential:* Chapter 14 (Health and Vitality) benefits substantially. The chapter already invokes F3 heavily; adding the register distinction shows why "health" is a multi-register phenomenon that a single-register intervention (e.g., purely analytical diet planning, `F_3|A`-only) fails to support.
- *Original TKS descriptions and excluded content:* [PENDING.]

### F4 Connection

**F4|T**, **F4|A**, **F4|f**, **F4|E**.
- *CAS v7.5 expressions:* `F_4|T`, `F_4|A`, `F_4|f`, `F_4|E`.
- *Structural insight extracted:* Connection at the Transcendent register is the principled commitment to the Other (relational ideal); at Analytical is explicit understanding of a person's Ideas (knowing how they think); at Affective is felt warmth, emotional attunement, empathic resonance; at Embodied is physical co-presence, touch, side-by-side activity.
- *Pedagogical enrichment potential:* Chapter 13 (Relationships) gains substantially. A relationship in which partners connect only at `F_4|A` (intellectual rapport) lacks the `F_4|f` (affective attunement) and `F_4|E` (physical co-presence) that long-term partnership requires. Register specification lets the chapter diagnose mismatches precisely.
- *Original TKS descriptions and excluded content:* [PENDING.]

### F5 Agency

**F5|T**, **F5|A**, **F5|f**, **F5|E**.
- *CAS v7.5 expressions:* `F_5|T`, `F_5|A`, `F_5|f`, `F_5|E`.
- *Structural insight extracted:* Agency at the Transcendent register is the principled commitment to act (will-as-vision); at Analytical is deliberate decision-making and plan construction; at Affective is the felt drive to do something, the push of ambition; at Embodied is physical exertion, muscular execution, hands-on work.
- *Pedagogical enrichment potential:* Chapter 12 (Career and Purpose) benefits. David's transition from analyst to director involved a register shift, not just a role shift: his former role exercised `F_5|A` (analytical execution), his new role demands `F_5|E` (operational execution of management rituals). Register-specification clarifies why his `^5^C` analyst substrate doesn't support the new role's `F_5|E` demands.
- *Original TKS descriptions and excluded content:* [PENDING.]

### F6 Structure

**F6|T**, **F6|A**, **F6|f**, **F6|E**.
- *CAS v7.5 expressions:* `F_6|T`, `F_6|A`, `F_6|f`, `F_6|E`.
- *Structural insight extracted:* Structure at the Transcendent register is the principled commitment to order (integrity-as-vision); at Analytical is rule-construction and system-design; at Affective is the satisfaction of order, the discomfort of chaos (felt structure); at Embodied is physical arrangement, material organization, spatial order.
- *Pedagogical enrichment potential:* Chapter 16 (Wealth and Structure) will gain substantially. Different wealth-building styles correspond to different register manifestations of F6: analytical planners (`F_6|A`), rule-following system-builders (`F_6|A × F_7|A`), felt-safety hoarders (`F_6|f`), physical-possession organizers (`F_6|E`).
- *Original TKS descriptions and excluded content:* [PENDING.]

### F7 Purpose

**F7|T**, **F7|A**, **F7|f**, **F7|E**.
- *CAS v7.5 expressions:* `F_7|T`, `F_7|A`, `F_7|f`, `F_7|E`.
- *Structural insight extracted:* Purpose at the Transcendent register is the highest form — the felt calling, the integrative vision of what a life is for; at Analytical is reasoned articulation of goals and their justifications; at Affective is felt meaning, passion, the warmth of doing something that matters; at Embodied is the body's commitment, the hands-on living-out of purpose in daily acts.
- *Pedagogical enrichment potential:* Chapter 12 (Career and Purpose) and Chapter 17 (Leadership) both gain. A leader who has only `F_7|A` (articulated mission statement) without `F_7|f` (felt commitment) or `F_7|E` (embodied living-out) is structurally unstable. Register specification makes this visible.
- *Original TKS descriptions and excluded content:* [PENDING.]

---

## Population Plan

Full population of each entry's TKS-source fields is scheduled as a named deliverable in the CAS v7.5 rollout plan. Population requires:

1. Direct access to the TKS 28 Foundations source document.
2. Line-by-line translation work, carefully separating structural content (reconciled) from metaphysical content (excluded).
3. Review by Wakil to confirm each excluded-content marking is correct (i.e., the excluded content genuinely carries metaphysical commitment and is not merely culturally flavored structural observation).

Until population is complete, the Structural Insight Extracted fields (populated above) serve as the minimum viable translation — they express the secular structural content that CAS v7.5 reconciles, without relying on the TKS source's specific language.

The Pedagogical Enrichment Potential fields (populated above) indicate which book chapters, platform features, or analytical uses stand to benefit most from each entry's translated content. This guides prioritization when the full population is undertaken.

---

## Notation Note

This document uses `F_k|R` for Drive × Register positions (e.g., `F_1|T`, `F_7|E`). The `F_k` notation (underscore-subscript) matches the CAS notation standard for Drives. The `|R` suffix is the Register modifier per Clarification 8 notation specification.

When a position needs to be referenced in running prose, either `F_1|T` (formal) or "F1 Unity in the Transcendent register" (prose) is acceptable. The latter form is preferred in pedagogical contexts; the former in formal analysis.
