# CAS v7.6 Rollout Plan — Stoichiometric Production Semantics Integration

**Status.** Active working plan. Tracks follow-on work required to propagate Stoichiometric Production Semantics (admitted in Clarification 9 on 2026-04-20) across CAS artifacts.

**Scope.** Production semantics is integrated into authoritative references (Clarification 9, CLAUDE.md, Taxonomy Development Notes) as of the admission date. Implementation propagation across peer-review paper, book manuscript, compiler, Rust engine, dashboard, LLM scoring prompt, scenario catalog, and related artifacts is a multi-week effort tracked here.

**Cadence expectation.** v7.5 rollout continues on its existing schedule. v7.6 rollout is a SEPARATE track that does NOT inflate v7.5 work. v7.5 Chapter 9 integrated expansion, v7.5 Appendix G, v7.5 Dashboard Phase A, and v7.5 peer-review-paper track all proceed with v7.5 content only. v7.6 content is added as v7.5 rollout stabilizes.

This sequencing is deliberate: admit v7.6 now to lock framework formalization, while sequencing implementation to protect v7.5 stability.

---

## Principle: Backward Compatibility

CAS v7.5 expressions remain valid in v7.6. Production semantics is an ADDITIVE higher-order analytical layer over the v7.5 state space; it does not modify the state space itself. No existing artifact is "broken" by the v7.6 admission.

Propagation is staged: new work in each artifact may use v7.6 recipe/yield/leakage vocabulary where analytically useful; retrofit of existing v7.5 artifacts is opportunistic (not forced) unless a specific artifact has a blocking requirement.

---

## Legal Framing

Production semantics is framed as **specification of how existing CAS primitives (Noetics, Domains, Drives, Registers) participate in outcome production**, not as introduction of new ontological primitives. The 40 Cognitive States, 7 Drives, and 4 Registers — the primitives named in USPTO #64/037,173 and Clarifications 1-8 — remain unchanged.

v7.6 adds analytical capacities, not primitives:
- Recipe notation (proportional weightings over existing primitives).
- Yield measurement (theoretical vs actual, ratio metric).
- Leakage detection (side-reaction products — distinct from lacunarity and inversion).
- Catalyst/inhibitor formalism (conversion modifiers).
- Limiting reagent analysis (bottleneck identification).

**IP attorney consultation required** before:

1. arXiv submission of v7.6 paper content.
2. Utility patent filing that references v7.6.

Specific questions to cover in the v7.6 consultation (in addition to the v7.5 questions already flagged in the v7.5 rollout plan):

- Does v7.6 production semantics extend the provisional patent scope, or fit within existing claims as analytical application of the disclosed primitives?
- Continuation-in-part considerations for a utility patent that includes production semantics.
- arXiv submission gate for v7.6 paper content (priority-date implications for the production-semantics material).
- Are there any recipe/yield/leakage-specific claims that should be drafted for independent protection?

This consultation is **blocking** for any public disclosure of v7.6 that might affect patent priority.

---

## Track (a): Clarification 9 Specification

**Status.** COMPLETE as of 2026-04-20 admission commit.

Authoritative specification lives in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9 (ten sections: Principle Statement, Definitions, Notation, Integration with CAS v7.5, Distinctions from Existing CAS Concepts, Five Generative Operations Under v7.6, Universal Applicability, Diagnostic Applications, Source and Triple-Gate Validation, Formal Verification Status).

No further specification work required for the admission itself. Clarification 9 is the authoritative reference.

---

## Track (b): CLAUDE.md Ontology Update

**Status.** COMPLETE as of 2026-04-20 admission commit.

CLAUDE.md Project Identity line updated to v7.6. New "Production Semantics — CAS v7.6 extension" subsection added after the "Phenomenological Register axis — CAS v7.5 extension" subsection, referencing Clarification 9 as the authoritative specification and summarizing the core concepts for session-start context.

---

## Track (c): Peer-Review Paper v7.6 Extension

**Location.** `peer_review/journal_submission/main.tex`.

**Priority.** BLOCKED on IP attorney consultation.

**Required updates:**

1. Add production semantics section to axiomatization. Specify the recipe/yield/leakage formalism and its relationship to the v7.5 state space. Production semantics operates as higher-order structure over the monoid (Δ°₃₉, ×, CO-0); it does not modify the monoid.
2. Add worked examples demonstrating recipe analysis. At minimum, include the "complete AI safety research paper" example from Clarification 9 Section 4 and the "reliable refusal of harmful requests" example from Section 7.
3. Update abstract and introduction to reflect v7.6 designation. Acknowledge v7.5 as the prior specification and v7.4 before that.
4. Address the proof obligations flagged in Clarification 9 Section 10 (recipe arithmetic, yield calculation properties, leakage conservation) as open research questions, or provide partial proofs where available.
5. Bibliography updates for production-semantics references if any are added.

**Dependencies.** Blocked on IP attorney consultation (priority-date considerations for v7.6 material).

---

## Track (d): Python Compiler Production-Semantics Support

**Location.** `api/notation/compiler.py`.

**Priority.** MEDIUM-HIGH.

**Required updates:**

1. Extend the grammar/lexer to parse recipe notation:
   - `Θ(Ω_name) = a₁·X₁ + a₂·X₂ + ... + aₙ·Xₙ → Ω_name` where Xᵢ are v7.5 primitives (already supported by the compiler) and aᵢ are numeric coefficients.
   - State vector notation: `S = {X₁: x₁, X₂: x₂, ...}`.
   - Leakage extensions on the right-hand side: `... → Ω + Λ₁·Ω_side₁ + Λ₂·Ω_side₂`.
   - Catalyst/inhibitor modifiers on the arrow: `Θ(Ω) | κ₁, ι₁ → Ω`.
2. Extend the AST with Recipe, StateVector, and ProductionTarget node types.
3. Implement yield calculation: given a Recipe and a StateVector, compute theoretical yield `Y_T = min_i(xᵢ / aᵢ)` and identify the Limiting Reagent.
4. Validate that recipe prerequisites Xᵢ are all valid v7.5 primitives (leveraging existing v7.5 parser infrastructure).
5. Backward compatibility mandate: v7.5 expressions continue to parse unchanged. Recipe notation is a new top-level expression form, not a modification of state-expression syntax.
6. Tests: recipe parsing (simple and complex), yield calculation on representative state vectors, limiting-reagent identification, leakage-notation parsing, catalyst/inhibitor-modifier parsing, backward-compat verification.

**Dependencies.** None blocking; v7.5 compiler infrastructure is in place.

---

## Track (e): Rust Engine Recipe Type + Yield Calculation

**Location.** `cas-engine/src/`.

**Priority.** MEDIUM-HIGH.

**Required updates:**

1. Add Recipe, StateVector, and ProductionTarget types to the ontology module. Derive standard traits and serde.
2. Add a yield-calculation function: given a Recipe and a StateVector, return `(Y_T, Limiting Reagent)`.
3. Add an efficiency-calculation function: given `Y_T` and an observed `Y_A`, return `η = Y_A / Y_T`.
4. Add leakage-tracking data structures for Recipes whose right-hand side includes side-reaction products.
5. Expose all new types via the public API and PyO3 bindings where applicable.
6. Tests: Recipe construction, yield calculation for representative cases (clearly limiting reagent, tie cases, edge cases), efficiency calculation, leakage accumulation.

**Dependencies.** Track (d) compiler support is helpful but not blocking; engine types can ship independently.

---

## Track (f): LLM Scoring Prompt Production-Semantics Section

**Location.** `api/llm_connectors/base.py` (`CAS_BASE_SYSTEM_PROMPT`).

**Priority.** MEDIUM.

**Required updates:**

1. Add a new Production Semantics section to the prompt after the Phenomenological Register section. Introduce recipe/yield/leakage vocabulary and the Limiting Reagent concept.
2. Instruct the scoring LLM that when a scoring query is framed as a production question (e.g., "Why is this person struggling to complete their book?"), the LLM may identify the production target Ω, propose a recipe Θ from v7.5 primitives, and identify the Limiting Reagent in the subject's current state.
3. Backward compatibility: if the user query is not production-framed, the LLM defaults to v7.5 state-space scoring without invoking production semantics.
4. Worked example in the prompt: use the "reliable refusal of harmful requests" recipe from Clarification 9 Section 7 to illustrate the AI-safety application of production semantics.
5. Preserve existing v7.5 content (10 Noetic definitions, Phenomenological Register section, anti-drift annotations, CAS_SELF_SCORING_APPENDIX).

**Dependencies.** None blocking. Standalone string update like the v7.5 prompt update was.

---

## Track (g): Book Manuscript v7.6 Chapter

**Location.** `book/manuscript/FULL_MANUSCRIPT.md`.

**Priority.** MEDIUM.

**Required updates:**

1. Decide between (i) a new chapter dedicated to production semantics (candidate placement: between current Chapter 10 and Chapter 11, as the production layer that uses equations built in Chapters 7-11) or (ii) integrated treatment distributed across Chapters 12-17 (human applications) and 18-22 (AI applications). Decision for Wakil based on pedagogical flow.
2. If (i): the new chapter covers Clarification 9 Sections 1-8 with worked examples, explicit distinctions from existing CAS concepts, and diagnostic applications.
3. If (ii): recipe/yield/leakage analysis distributed into relevant application chapters (Chapter 12 career production, Chapter 13 relationship production, Chapter 14 health production, Chapter 21 AI safety production).
4. Either way: Appendix D glossary gains entries for Production Target, Recipe, State Vector, Yield (Theoretical/Actual), Production Efficiency, Limiting Reagent, Excess Capacity, Leakage, Catalyst, Inhibitor.
5. Cross-references to Clarification 9 for formal definitions.

**Dependencies.** Proceeds after v7.5 book rollout stabilizes.

---

## Track (h): Appendix H — Recipe Library for Common Outcomes

**Location.** `book/manuscript/FULL_MANUSCRIPT.md` (new appendix).

**Priority.** MEDIUM.

**Required updates:**

A curated library of recipes for commonly-analyzed outcomes, each drawn from v7.5 primitives per Clarification 9 Section 4. Candidate categories:

- Career / professional: Ω_book_completion, Ω_promotion, Ω_career_pivot, Ω_burnout_prevention.
- Relationship: Ω_conflict_resolution, Ω_intimacy_deepening, Ω_trust_repair.
- Health: Ω_habit_formation, Ω_recovery_trajectory, Ω_chronic_illness_management.
- Learning: Ω_skill_mastery, Ω_knowledge_integration, Ω_expertise_development.
- AI safety: Ω_reliable_refusal, Ω_calibrated_uncertainty, Ω_defense_in_depth, Ω_helpfulness_without_deception.
- Leadership: Ω_team_cohesion, Ω_strategic_vision, Ω_accountability_culture.

Each recipe cites its source (common empirical observation, specific case study, or theoretical derivation). Limiting-reagent discussion included where illustrative.

**Dependencies.** Proceeds alongside Track (g).

---

## Track (i): Multi-Modal Display v7.6 Extension

**Location.** `docs/design/cas_v7_5_multimodal_display_specification.md` (v7.6 addendum), and eventually `dashboard/src/`.

**Priority.** LOW-MEDIUM.

**Required updates:**

1. Specify visual encodings for v7.6 concepts in the Radial Architecture Display:
   - Yield indicators (annular ring segments showing Y_T vs Y_A for a selected Ω).
   - Leakage flows (directional arcs from prerequisite cells to side-product indicators outside the main display).
   - Catalyst/inhibitor markers (environmental-factor glyphs around the mandala perimeter).
   - Limiting-reagent highlight (distinct visual treatment of the bottleneck cell).
2. Specify auditory encodings for v7.6 concepts in the Temporal Cognitive Score:
   - Production dynamics: recipe execution as a temporal sequence, with yield progress rendered as motif development toward resolution.
   - Leakage: audible detuning or mismatched-interval motif branching off the main line.
   - Catalyst/inhibitor: tempo or dynamic modulation on the Ω-target motif.
3. Phase plan: v7.6 visualization is an incremental extension of the five-phase v7.5 plan, not a separate phase stack. Phase A shows only v7.5 elements (no v7.6 yield rings). v7.6 elements enter in a new Phase F or as enhancements to Phases B/C after Phase A ships.

**Dependencies.** v7.5 Phase A completion useful but not blocking; v7.6 design spec can be drafted independently.

---

## Track (j): Scenario Catalog v7.6 Coverage

**Location.** `scenarios/` directory.

**Priority.** LOW.

**Required updates:**

1. Audit existing scenarios for production-framing candidates: scenarios that describe an outcome to achieve (not just a state to score) should be re-examined under production-semantics lens.
2. Add new scenarios specifically exercising recipe/yield/leakage analysis:
   - Scenarios with an obvious Limiting Reagent that the scoring LLM should identify.
   - Scenarios with leakage where prerequisites are present but outcomes are wrong.
   - Scenarios with catalyst/inhibitor environmental factors.
3. Update scenario expected-outputs to optionally specify v7.6 analytical artifacts (identified recipe, limiting reagent, leakage pattern).

**Dependencies.** Requires Track (d) compiler support for recipe parsing in scenario files, and Track (f) LLM prompt support for production-framing scoring.

---

## Track (k): Dashboard v7.6 Display Elements

**Location.** `dashboard/src/`.

**Priority.** LOW.

**Required updates:**

1. Recipe display component (shows Ω target, prerequisite list with coefficients, Y_T/Y_A/η metrics, Limiting Reagent highlight).
2. Integration with the Radial Architecture Display per Track (i) visual spec.
3. Leakage-flow rendering.
4. Catalyst/inhibitor indicators.
5. Research-data export including recipe/yield/leakage data alongside v7.5 axis values.

**Dependencies.** Requires Track (e) Rust engine types, Track (d) compiler for scenario inputs, and Track (i) visual design specification.

---

## Sequencing Recommendation

The v7.6 rollout runs as a SEPARATE track from the v7.5 rollout. v7.5 rollout completion does not block v7.6 work, but v7.6 artifacts that depend on v7.5 infrastructure (e.g., Dashboard v7.6 elements building on v7.5 Phase A) follow their v7.5 dependencies naturally.

Suggested order:

1. **Tracks (a) and (b)** — COMPLETE via the v7.6 admission commit.
2. **Track (c) Peer-review paper** — BLOCKED on IP attorney consultation.
3. **Track (d) Compiler** and **Track (e) Rust Engine** — can proceed in parallel; both are backend infrastructure.
4. **Track (f) LLM prompt** — can proceed in parallel with (d)/(e); standalone string update.
5. **Track (g) Book manuscript** and **Track (h) Recipe library appendix** — proceed after v7.5 book rollout stabilizes.
6. **Track (i) Multi-modal display v7.6 extension** — can proceed in design-specification form anytime; implementation sequences after v7.5 Phase A ships.
7. **Track (j) Scenario catalog** — sequences after (d) and (f).
8. **Track (k) Dashboard display elements** — sequences after (e), (d), (i), and v7.5 Phase A.

The v7.6 rollout dependencies (items that must complete before v7.6 is considered fully rolled out):

- Track (c) peer-review paper update (or deferred per IP attorney guidance).
- Track (d) compiler production-semantics support.
- Track (e) Rust engine recipe types + yield calculation.
- Track (f) LLM scoring prompt production-semantics section.

Tracks (g)-(k) are progressive enhancement.

---

## Strategic Pace Considerations

Two framework extensions (v7.5 Phenomenological Register, v7.6 Stoichiometric Production Semantics) were admitted in a single session (2026-04-20). Both passed triple-gate analysis. Both are additive and backward-compatible with v7.4.

Items to manage at this pace:

1. **Implementation propagation lag.** Specification is racing ahead of implementation. Practical CAS (what the compiler/engine/dashboard actually do) trails formal CAS (what the papers describe). The v7.5 rollout dependencies still have three items outstanding (peer-review paper, Dashboard Phase A, register data-flow extension per track (j) of the v7.5 plan). v7.6 adds its own implementation tracks on top. This is manageable but real.

2. **Reviewer comprehension.** Peer reviewers need to absorb v7.5 AND v7.6 simultaneously if the paper includes both, which slows acceptance. Consider staged submissions: v7.5 paper submitted first, v7.6 paper submitted later as a follow-on specification.

3. **Audience version-tracking.** Enterprise buyers and regulators tracking CAS versions may find frequent version bumps destabilizing. Communication strategy: emphasize that v7.5 and v7.6 are both ADDITIVE over v7.4; v7.4 expressions remain valid throughout. The version number reflects specification lineage, not behavioral churn.

4. **Framework creator bandwidth.** Accelerating specification while implementation lags creates debt. Not a reason to slow down, but a reason to be intentional about pace in subsequent sessions.

None of these is a blocker. All are surfaced here so future sessions can reference them as explicit considerations rather than rediscovering them as problems.

---

## Open Decisions

1. **Book manuscript v7.6 placement** — new chapter between 10 and 11, vs. integrated treatment across Chapters 12-22. Pedagogical-flow decision for Wakil.
2. **v7.6 peer-review submission strategy** — single combined v7.5+v7.6 paper, vs. staged submissions. Depends on IP attorney guidance and journal preferences.
3. **Appendix H recipe-library scope** — full library of 20+ recipes, vs. curated core set of 8-10 canonical recipes. Decision for Wakil based on book pacing.
4. **v7.6 visualization phase placement** — new Phase F in the multi-modal display plan, vs. enhancements to Phases B/C after Phase A ships. Design-level decision.
5. **IP attorney scope** — combined v7.5+v7.6 consultation, vs. separate consultations. Depends on attorney availability and filing timeline.
