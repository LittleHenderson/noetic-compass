# CAS Taxonomy Development Notes

**Purpose.** This document tracks the evolution of CAS taxonomy extensions — proposed refinements, candidate subcategories, and framework additions that have been surfaced during research work. Entries migrate between states: **Proposed** (under consideration), **Admitted** (formally integrated into the framework with a version bump), and **Deferred/Rejected** (examined and set aside, with reasoning preserved).

**Related documents.**
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` — authoritative clarifications on current framework semantics (Clarifications 1-9).
- `docs/INCIDENT_CATEGORIES.md` — contains an in-line "Taxonomy Development Notes" section focused on incident-classification candidate extensions (Boundary Failures subcategory, Institutional Posture Observation, etc.). Those incident-specific notes remain where they are; this document tracks **framework-level** taxonomy evolution distinct from the incident taxonomy.

---

## Status Update — 2026-04-20 (second admission same day)

**Stoichiometric Production Semantics: Proposed → Admitted (CAS v7.6).**

Stoichiometric Production Semantics has been formally admitted into CAS as of v7.6. This moves the proposal (Refinement 7 in the taxonomy tracking) from "candidate future extension" to "integrated framework structure." Authoritative specification lives in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9.

### Summary of the admitted extension

- **Layer:** Production semantics as higher-order analytical layer over v7.5 state space.
- **Core concepts:** Production Target (Ω), Recipe (Θ), State Vector (S), Theoretical Yield (Y_T), Actual Yield (Y_A), Production Efficiency (η), Limiting Reagent (L), Excess Capacity (ε), Leakage (Λ), Catalyst (κ), Inhibitor (ι).
- **Scope:** Recipes are drawn from v7.5 primitives (Noetics, Domains, Drives, Registers). Production semantics operates ON v7.5 primitives; it does not add new primitives.
- **Notation:** `Θ(Ω) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ → Ω`. Leakage notation extends the right-hand side with `+ Λ₁·Ω_side₁`. Catalyst/inhibitor specified as conditions on the arrow: `Θ(Ω) | κ₁, ι₁ → Ω`.
- **Backward compatibility:** v7.4 and v7.5 expressions remain valid in v7.6. Recipes are a new analytical layer, not a modification of the state space.

### Triple-gate validation

Production semantics passed all three admission gates (detail in Clarification 9 Section 9):

- **Gate 1 (Universal Applicability): PASSED.** Production concepts apply to human, AI, and biological cognitive architectures with architecture-specific manifestations.
- **Gate 2 (Secular Translatability): PASSED.** All concepts are definable without metaphysical commitment. Recipes are proportional weightings; yields are measurable ratios; leakage is diversion to unintended products.
- **Gate 3 (Framework Coherence): PASSED with required distinctions.** Explicit boundary-setting between production semantics and existing CAS vocabulary (Lacunarity, Inversion, RPM, Drive values, Limiting Reagent) preserved.

### Source of the extension

External analytical collaboration (ChatGPT analysis of TKS-to-production-grammar mapping), refined through triple-gate analysis in the 2026-04-20 CAS session. Cross-validated by the framework's own production-side diagnostic gaps (5 previously-unaddressed cases that production semantics now resolves — see Clarification 9 Section 8).

### What the admission does NOT change

The following remain unchanged from CAS v7.5:

- The 10 authoritative Noetic definitions (Clarification 1).
- The 40 Cognitive States (10 Noetics × 4 Domains).
- The 7 Core Drives (F1-F7).
- The 4 Registers (T, A, f, E) — admitted in v7.5 per Clarification 8.
- Axioms A1-A7 of the Noetic Topos.
- The RPM section-retraction structure.
- The Fisher-Rao metric on the open probability simplex.
- Prior Clarifications 1 through 8.

### Follow-on rollout

Integration of production semantics across CAS artifacts is scheduled in `docs/working/cas_v7_6_rollout_plan.md`. v7.5 rollout continues on its existing schedule; v7.6 implementation rolls out as a SEPARATE track. v7.5 chapter integration, Appendix G, Dashboard Phase A, and peer-review-paper tracks all proceed with v7.5 content only. v7.6 content is added as v7.5 rollout stabilizes.

### Legal framing

Production semantics is specification of how existing CAS primitives participate in outcome production, not introduction of new ontological primitives. This preserves the integrity of the provisional patent filing USPTO #64/037,173. IP attorney consultation regarding v7.6 scope, continuation-in-part considerations, and arXiv-submission gating for v7.6 paper content is flagged in the v7.6 rollout plan.

### Pace note (two admissions in one session)

Both the Phenomenological Register axis (v7.5, admitted 2026-04-20 earlier today) and Stoichiometric Production Semantics (v7.6, admitted 2026-04-20 later today) passed independent triple-gate analysis and both were admitted in the same research session. This is unusual development pace. It is justifiable because: the underlying primitives (10 Noetics, 4 Domains, 7 Drives) are stable; both extensions are additive, not modificational; each has formal structural rationale; legal framing (specification, not new primitives) is preserved across both. Management of implementation lag, reviewer comprehension, and audience version-tracking is flagged in the v7.6 rollout plan under "Strategic pace considerations."

---

## Status Update — 2026-04-20

**Phenomenological Register axis: Proposed → Admitted (CAS v7.5).**

The Phenomenological Register axis has been formally admitted into CAS as of v7.5. This moves the proposal from "candidate future extension" to "integrated framework structure." Authoritative specification lives in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 8.

### Summary of the admitted extension

- **Axis:** Phenomenological Register, a second orthogonal axis to the Noetic Topos.
- **Values:** R ∈ {T Transcendent, A Analytical, f Affective, E Embodied}.
- **Scope:** Applies to Noetics, Drives, and compound Cognitive States. Orthogonal to the existing Noetic, Domain, and Drive axes.
- **Notation:** `^n|R`, `F_k|R`, `^n^D_{F_k}|R`, and `^n|R_n^D_{F_k|R_d}` for independent specification.
- **Backward compatibility:** CAS v7.4 expressions (no register) remain valid in v7.5 and indicate register-neutral / unspecified register.

### Cross-validation via TKS structural confirmation

The Register axis was not a post-hoc invention. It was independently confirmed by two TKS structural elaborations:

1. **10 Noetics × 4 Worlds = 40 Elements** (Noetic-level cross-product).
2. **7 Foundations × 4 Worlds = 28 Foundations** (Drive-level cross-product).

The same 4-Worlds axis appears at both cross-products. Reframed in secular universal terms as 4 Registers (T, A, f, E), the axis applies consistently across all CAS primitives. CAS v7.4 lost this axis in translation; v7.5 restores it on secular basis.

The structural logic (axis existence, cross-product appearance at both Noetic and Drive levels) is reconciled from TKS. The metaphysical/cultural content of TKS elaborations is not. The translation with excluded-content clearly marked is preserved in `docs/reference/tks_28_foundations_translation_key.md` as pedagogical enrichment material.

### What the admission does NOT change

The following remain unchanged from CAS v7.4:

- The 10 authoritative Noetic definitions (Clarification 1).
- The 40 Cognitive States (10 Noetics × 4 Domains).
- The 7 Core Drives (F1-F7).
- Axioms A1-A7 of the Noetic Topos.
- The RPM section-retraction structure.
- The Fisher-Rao metric on the open probability simplex.
- Prior Clarifications 1 through 6 (and — when it is numbered — 7).

### Follow-on rollout

Integration of the Register axis across all CAS artifacts (peer-review paper, book manuscript, compiler, Rust engine, dashboard, LLM scoring prompt, incident database, scenario catalog, NL signal analyzer) is scheduled in `docs/working/cas_v7_5_rollout_plan.md`. This is a multi-week effort; the immediate admission via Clarification 8 provides the authoritative reference point. Follow-on propagation proceeds per the rollout plan cadence.

### Legal framing

Register is specification of operational character of existing primitives, not introduction of new ontological primitives. This preserves the integrity of the provisional patent filing USPTO #64/037,173. IP attorney consultation regarding continuation-in-part considerations is flagged in the rollout plan.

---

## Proposed Extensions — Current Candidates

This section lists proposals under active consideration. Entries migrate to the Admitted section (with a version bump) when the evidence base supports formalization, or to the Deferred/Rejected section (with reasoning preserved) when the proposal is set aside.

*(No active Proposed entries at this time. The Register axis — previously the principal Proposed entry — was admitted in v7.5 on 2026-04-20.)*

---

## Admitted Extensions — Version History

### CAS v7.6 (2026-04-20)

- **Stoichiometric Production Semantics** — admitted per Clarification 9. Higher-order analytical layer over v7.5 state space. Core concepts: Production Target, Recipe, State Vector, Theoretical/Actual Yield, Production Efficiency, Limiting Reagent, Excess Capacity, Leakage, Catalyst, Inhibitor. Backward compatible with v7.4 and v7.5.

### CAS v7.5 (2026-04-20)

- **Phenomenological Register axis** — admitted per Clarification 8 above. Cross-validated by TKS 40 Elements and 28 Foundations. Backward compatible with v7.4.

### CAS v7.4 (Corrected Edition, prior)

- 10 authoritative Noetic definitions (Clarification 1).
- 40 Cognitive States (10 × 4 Domains).
- 7 Core Drives (F1-F7).
- Axioms A1-A7 of the Noetic Topos.
- Four mathematical corrections (admissibility relations, RPM section-retraction, counit-direction coverage, open-simplex state space).
- Clarifications 1 through 6 (Authoritative definitions, Universal Applicability Test, Canonical Naming, Structural-Not-Emotional Framing, ^5 Female Expanded Scope, Colloquialism Test).

---

## Deferred / Rejected Proposals

*(No entries at this time.)*

---

## Entry Lifecycle Convention

New entries begin in Proposed with:

- **Surfaced:** date and context (session, research thread, incident analysis).
- **Working definition:** operational statement of what the proposal is.
- **Structural rationale:** why the proposal is a candidate framework extension.
- **Admission criteria:** what evidence, validation, or structural argument is required before promoting to Admitted.
- **Current evidence state:** what has accumulated so far.

When an entry is admitted, it moves to Admitted with a version bump and a reference to the authoritative specification document (a new Clarification, a new section in an existing reference, or similar). The admission note preserves the structural rationale for future auditability.

When an entry is deferred or rejected, it moves to Deferred/Rejected with explicit reasoning preserved.

This convention ensures that framework evolution has a traceable development record: what was considered, what was admitted, what was set aside, and why.
