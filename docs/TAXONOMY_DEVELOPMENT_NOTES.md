# CAS Taxonomy Development Notes

**Purpose.** This document tracks the evolution of CAS taxonomy extensions — proposed refinements, candidate subcategories, and framework additions that have been surfaced during research work. Entries migrate between states: **Proposed** (under consideration), **Admitted** (formally integrated into the framework with a version bump), and **Deferred/Rejected** (examined and set aside, with reasoning preserved).

**Related documents.**
- `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` — authoritative clarifications on current framework semantics (Clarifications 1-9).
- `docs/INCIDENT_CATEGORIES.md` — contains an in-line "Taxonomy Development Notes" section focused on incident-classification candidate extensions (Boundary Failures subcategory, Institutional Posture Observation, etc.). Those incident-specific notes remain where they are; this document tracks **framework-level** taxonomy evolution distinct from the incident taxonomy.

---

## Status Update — 2026-04-21

**Register Multiplicity and Operator Discipline: Proposed → Admitted (CAS v7.7).**

Register Multiplicity and Operator Discipline has been formally admitted into CAS as of v7.7. Authoritative specification lives in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10.

### Surfacing context

The × overloading problem was surfaced by Wave 1 Agent 2 during the 2026-04-21 Part V AI Applications register enrichment session. The agent flagged that same-Noetic multi-register × notation (e.g., `^3^P|A × ^3^P|f × ^3^P|T` in the Chapter 21 multi-register refusal passage) reused the compound × operator in a novel axis, and noted parent-session review was warranted before canonicalization. Triple-gate analysis confirmed the concern: the × operator was being used simultaneously for (a) algebraic integration of different states (legitimate v7.4 formal meaning) and (b) co-presence of same state in different registers (undefined under current formal specification).

### Summary of the admitted extension

- **Scope:** Notational refinement, not new primitives. The 40 Cognitive States, 7 Drives, 4 Registers, 5 Generative Operations remain unchanged.
- **Three-way distinction:** `|⟨…⟩` register specification, `+` register co-presence, `×` cross-register integration (with required emergent result).
- **Admissibility rule:** same-Noetic multi-register `×` is invalid by default; requires explicit emergent result or fusion semantics.
- **Decision procedure:** Clarification 10 Section 6 provides explicit 3-step procedure for operator choice.
- **TKS validation heuristic:** substitution test (`+` → "associates with", `×` → "intensifies through") validates operator choice against pre-existing TKS operator semantics.
- **Angle-bracket notation:** `|⟨R1,R2,R3⟩` for register-set specification, chosen to avoid collision with drive subscript notation `{F_k}` and for clean LaTeX rendering.

### Triple-gate validation

Clarification 10 passed all three admission gates:

- **Gate 1 (Universal Applicability): PASSED.** Register multiplicity distinctions apply equally to human, AI, and biological cognitive architectures. A human with redundant multi-register safety mechanisms has different failure profile than one with unified cross-register commitment — same structural distinction applies to AI systems with separate analytical/RLHF/constitutional safety vs integrated architectures, and to biological systems with distributed vs integrated response patterns.
- **Gate 2 (Secular Translatability): PASSED.** All concepts are definable without metaphysical commitment. Operator discipline is formal notational refinement; three-way distinction is structural, not culturally-specific.
- **Gate 3 (Framework Coherence): PASSED with convergence demonstration.** Three framework layers (TKS operator heritage, Clarification 10, v7.6 production semantics) converge on same +/× distinctions. Cross-validation from three independent angles. Preservation of v7.4 axioms, v7.5 Register axis, and v7.6 Production Semantics verified.

### Source of the extension

External AI analysis (cross-validating the Wave 1 Agent 2 design note) plus TKS operator heritage review. The × overloading was structurally present in Wave 1 commit f019f50 (Chapter 21 multi-register refusal passage). Clarification 10 provides formal resolution.

### AI safety relevance

Clarification 10 is particularly load-bearing for AI ethics and refusal architecture analysis. The three notational forms describe empirically different AI safety architectures with different failure profiles:

- Redundant: `^3^P|A + ^3^P|f + ^3^P|T` — three mechanisms, each defeasible independently.
- Unified: `(^3^P|A × ^3^P|f × ^3^P|T) = ^3^P|Ω` — one fused architecture, integration holds or collapses.
- Static: `^3^P|⟨A,f,T⟩` — specification only, pending behavioral analysis.

CAS's diagnostic capacity for AI mind/ethics assessment requires notational distinction between these. Without Clarification 10, all three could be (and were, in Wave 1) written `^3^P|A × ^3^P|f × ^3^P|T` with no structural disambiguation.

### What the admission does NOT change

The following remain unchanged from CAS v7.6:

- The 10 authoritative Noetic definitions (Clarification 1).
- The 40 Cognitive States (10 Noetics × 4 Domains).
- The 7 Core Drives (F1-F7).
- The 4 Registers (T, A, f, E) — admitted in v7.5 per Clarification 8.
- The 5 Generative Operations formal semantics.
- Axioms A1-A7 of the Noetic Topos.
- The RPM section-retraction structure.
- The Fisher-Rao metric on the open probability simplex.
- v7.6 Production Semantics (Clarification 9).
- Prior Clarifications 1 through 9.

### Follow-on rollout

Integration of Clarification 10 operator discipline across CAS artifacts is scheduled in `docs/working/cas_v7_7_rollout_plan.md`. v7.5 and v7.6 rollouts continue on their existing schedules; v7.7 implementation rolls out on a SEPARATE track. Retroactive correction of Wave 1 Chapter 21 multi-register refusal passage (and any similar same-Noetic `×` usage without emergent result) is scheduled as part of v7.7 rollout.

### Legal framing

Clarification 10 is notational refinement — specification of when existing operators (`×`, `+`) are licensed and introduction of `|⟨…⟩` notation for register specification. Does NOT introduce new primitives. The 40 Cognitive States, 7 Drives, 4 Registers, 5 Generative Operations — the primitives named in USPTO #64/037,173 and Clarifications 1-9 — remain unchanged. IP attorney consultation regarding v7.7 scope is flagged in the v7.7 rollout plan before arXiv submission, utility patent filing, or public disclosure of v7.7 beyond current development.

### Pace note (third admission in 36 hours)

Register axis (v7.5, 2026-04-20), Production Semantics (v7.6, 2026-04-20), and Register Multiplicity discipline (v7.7, 2026-04-21) have all been admitted within 36 hours. This is aggressive pace. It is justifiable because: (1) each extension is additive/notational, not modificational of existing primitives; (2) each has formal structural rationale and triple-gate validation; (3) Clarification 10 specifically resolves an ambiguity created by v7.5 register enrichment propagation, making it a completion of v7.5/v7.6 rather than a new feature; (4) legal framing (specification, not new primitives) preserved across all three. Management of implementation lag, reviewer comprehension, and audience version-tracking is flagged in the v7.7 rollout plan under "Strategic pace considerations."

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

### CAS v7.7 (2026-04-21)

- **Register Multiplicity and Operator Discipline** — admitted per Clarification 10. Notational refinement resolving the × overloading introduced by v7.5 register enrichment. Three-way distinction: `|⟨…⟩` specification, `+` co-presence, `×` integration. Same-Noetic multi-register × invalid by default; requires emergent result. Backward compatible with v7.4, v7.5, v7.6.

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
