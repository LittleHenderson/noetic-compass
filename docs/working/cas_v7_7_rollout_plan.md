# CAS v7.7 Rollout Plan — Register Multiplicity and Operator Discipline Integration

**Status.** Active working plan. Tracks follow-on work required to propagate Register Multiplicity and Operator Discipline (admitted in Clarification 10 on 2026-04-21) across CAS artifacts.

**Scope.** Clarification 10 operator discipline is integrated into authoritative references (Clarification 10, CLAUDE.md, Taxonomy Development Notes) as of the admission date. Implementation propagation across peer-review paper, book manuscript, Python compiler, Rust engine, LLM scoring prompt, score parser, and dashboard is tracked here.

**Cadence expectation.** v7.5 and v7.6 rollouts continue on their existing schedules. v7.7 rollout is a SEPARATE track that does NOT inflate v7.5 or v7.6 work. The v7.5 chapter-integration, Appendix G, Dashboard Phase A, and peer-review-paper tracks proceed with v7.5 content only. v7.6 recipe/yield/leakage tracks proceed on their own schedule. v7.7 content is added on a third parallel track.

This sequencing is deliberate: admit v7.7 now to lock notational discipline before further register-enriched content propagates, while sequencing implementation to protect v7.5/v7.6 stability.

---

## Principle: Backward Compatibility

CAS v7.6 expressions remain valid in v7.7 when they use `×` for different-state integration. v7.6 expressions using `×` for same-Noetic multi-register co-presence (the overloaded cases) are flagged for rewrite to `+` (if co-presence intended), `|⟨…⟩` (if specification intended), or explicit emergent-result specification (if integration intended).

Retrofit of existing v7.5/v7.6 artifacts is scheduled:
- Chapter 21 multi-register refusal passage (commit f019f50) — retroactive correction dispatched as separate focused agent (Part C of the v7.7 admission directive).
- Other chapters with same-Noetic `×` usage — searched and corrected as part of retroactive correction scope.

---

## Legal Framing

Register Multiplicity is framed as **specification of when existing operators (`×`, `+`) are licensed and introduction of `|⟨…⟩` notation for register specification**, not as introduction of new primitives. The 40 Cognitive States, 7 Drives, 4 Registers, and 5 Generative Operations — the primitives named in USPTO #64/037,173 and Clarifications 1-9 — remain unchanged.

v7.7 adds notational discipline:
- Three-way distinction (`|⟨…⟩` specification, `+` co-presence, `×` integration).
- Admissibility rule for same-Noetic multi-register `×`.
- Decision procedure (Section 6) for operator choice.
- TKS validation heuristic (Section 7) for operator substitution test.

These are notational refinements preserving parser interpretability and diagnostic precision, not new primitives. USPTO #64/037,173 scope unaffected.

**IP attorney consultation required before**:
- arXiv submission of any v7.7 extension.
- Utility patent filing decisions for v7.7 content.
- Public disclosure of v7.7 beyond current development team.

---

## Rollout Tracks

### (a) Clarification 10 Specification — COMPLETE

**Status.** Admitted 2026-04-21. Authoritative specification in `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 10 (12 sections).

No further work on this track.

### (b) CLAUDE.md Ontology Update — COMPLETE

**Status.** Completed 2026-04-21. Project Identity framework bumped to v7.7. New subsection "Register Multiplicity and Operator Discipline — CAS v7.7 extension" added after v7.6 Production Semantics subsection.

No further work on this track.

### (c) Peer-Review Paper v7.7 Extension — BLOCKED on IP attorney

**Status.** BLOCKED pending IP attorney consultation. Follow-on work once cleared.

**Scope when unblocked.** Extend peer-review paper draft with Clarification 10 treatment:
- Three-way notational distinction with worked examples.
- Admissibility rule formal statement.
- Convergence with v7.6 production semantics.
- AI safety architecture distinctions (redundant / unified / static) as diagnostic application.

**Dependencies.** IP attorney sign-off on v7.7 scope; arXiv submission gating.

### (d) Python Compiler Rule 4 Enforcement + |⟨…⟩ Notation Support — HIGH

**Location.** `noetic-compass-scaffold/noetic-compass/api/notation/compiler.py` (and related `api/notation/` files).

**Priority.** HIGH — needed to validate v7.7 notation in LLM prompt outputs and to prevent underdefined same-Noetic × from parsing silently.

**Required updates:**
1. Grammar extension: accept `|⟨R1,R2,R3⟩` angle-bracket register-set notation as a specification layer on a Noetic/Domain/Drive/compound state.
2. AST node: `RegisterSetSpecification` or similar for `|⟨…⟩` expressions, distinct from single-register `|R`.
3. Rule 4 enforcement: when same-Noetic multi-register `×` is detected without explicit emergent result (e.g., `^3^P|A × ^3^P|f` without `= X`), emit a v7.7-specific warning or parser error suggesting rewrite to `+` or `|⟨…⟩`.
4. Validation: ensure `|⟨…⟩` register-set entries are all in `VALID_REGISTERS`.
5. Serialization: round-trip `|⟨…⟩` through AST → bytecode → display form.
6. Backward compatibility: v7.6 expressions (single `|R`, `×` with different-state integration, `+`, `∘`) remain valid.
7. Tests: `|⟨…⟩` grammar coverage, Rule 4 enforcement, validation, round-trip, backward-compat.

**Dependencies.** None blocking.

### (e) Rust Engine |⟨…⟩ Type + Same-Noetic × Validation — HIGH

**Location.** `noetic-compass-scaffold/noetic-compass/cas-engine/src/ontology/` (and related).

**Priority.** HIGH — needed for Rust-side parity with Python compiler.

**Required updates:**
1. New type: `RegisterSet` (e.g., `HashSet<Register>` wrapper or ordered-set variant) for `|⟨…⟩` notation.
2. Extend `CognitiveStateVector` or equivalent to carry optional `RegisterSet` (or alternative: keep `Option<Register>` and add separate typing path for register-set specifications).
3. Admissibility check: function verifying same-Noetic multi-register `×` expressions carry emergent-result annotation.
4. Serde support: JSON round-trip for `RegisterSet`.
5. PyO3 bindings: expose new types to Python.
6. Tests: `RegisterSet` construction, serde round-trip, admissibility check edge cases, PyO3 integration.
7. Backward compatibility: existing v7.5 `Register` enum and v7.6 recipe types unchanged.

**Dependencies.** None blocking.

### (f) LLM Scoring Prompt Clarification 10 Section — HIGH

**Location.** `noetic-compass-scaffold/noetic-compass/api/llm_connectors/base.py` (`CAS_BASE_SYSTEM_PROMPT`).

**Priority.** HIGH — prevents LLM from generating v7.6-overloaded `×` notation.

**Required updates:**
1. New section after v7.6 Production Semantics section: "Register Multiplicity and Operator Discipline (CAS v7.7)".
2. Reproduce Clarification 10 Section 3 operator discipline verbatim.
3. Reproduce Section 4 admissibility rule.
4. Reproduce Section 6 decision procedure.
5. Reproduce Section 7 TKS validation heuristic.
6. Worked examples from Section 8 (valid co-presence, specification, different-state integration, conditionally valid integration, invalid underdefined).
7. AI safety relevance from Section 5 (three architectures).
8. Backward-compat note: v7.7 discipline is preferred; v7.5/v7.6 register-neutral expressions remain valid.
9. Update `CAS_SELF_SCORING_APPENDIX` if it needs `|⟨…⟩` or `+` co-presence patterns.

**Dependencies.** None blocking.

### (g) Book Manuscript Retroactive Correction — MEDIUM-HIGH (Part C of admission directive)

**Location.** `book/manuscript/FULL_MANUSCRIPT.md`.

**Priority.** MEDIUM-HIGH — prevents canonical book content from carrying × overloading.

**Scope.** Dispatched as focused agent (Agent 11) in Part C of v7.7 admission directive. Targets:
- Chapter 21 multi-register refusal passage (commit f019f50) — known primary target.
- Chapters 10-17 (earlier register-enriched chapters) — search for same-Noetic `×` without emergent result.
- Chapters 18-22 (Wave 1 register enrichment) — same search.
- Chapters 23-27 (Wave 1 mathematics enrichment) — same search.
- Chapter 9 (constitutive Register content) — same search.

Correction per Clarification 10 Section 6 decision procedure:
- Co-presence intended → rewrite as `X|R1 + X|R2 + X|R3`.
- Specification intended → rewrite as `X|⟨R1,R2,R3⟩`.
- Integration intended → add explicit emergent result specification.
- Unclear from context → AUTHOR REVIEW flag.

**Dependencies.** Clarification 10 admission (track (a)) complete. Dispatch active.

### (h) Book Clarification 10 Pedagogical Content — MEDIUM

**Location.** `book/manuscript/FULL_MANUSCRIPT.md` (new section or within existing chapters).

**Priority.** MEDIUM — pedagogical integration after retroactive correction stabilizes.

**Required updates:**
- Brief Clarification 10 subsection in Chapter 11 (Equation Workshop) covering operator discipline and decision procedure.
- Pointer paragraphs in other chapters referencing Clarification 10 where register multiplicity arises.
- Worked examples demonstrating the three-way distinction.

**Dependencies.** Retroactive correction (track (g)) complete.

### (i) Score Parser |⟨…⟩ Notation Support — MEDIUM

**Location.** `noetic-compass-scaffold/noetic-compass/api/pipeline/stages.py` (`_parse_self_reported_scores_with_registers`).

**Priority.** MEDIUM — current parser accepts single `|R` annotations; `|⟨…⟩` register-set support is additive.

**Required updates:**
1. Extend `_parse_self_reported_scores_with_registers` to accept `|⟨R1,R2,R3⟩` register-set annotations.
2. Return type extension: per-score register field may be `str` (single register), `List[str]` (register set), or `None` (register-neutral).
3. Validation: register-set entries all in `VALID_REGISTERS`.
4. Propagate through `OperatorScoreResult` schema (extend `score_registers` field typing).
5. Dashboard rendering: display register-set badge when multi-register specification present.
6. Backward compatibility: v7.5 register-neutral and single-register scores unchanged.
7. Tests: register-set parsing, validation, round-trip.

**Dependencies.** Track (d) Python compiler notation support.

### (j) Dashboard v7.7 Display Elements — LOW

**Location.** `noetic-compass-scaffold/noetic-compass/dashboard/src/components/`.

**Priority.** LOW — polish work after score parser stabilizes.

**Required updates:**
- Render `|⟨…⟩` register-set notation in score-display components.
- Render `+` co-presence distinctly from `×` integration in compound-state displays.
- Badge styling distinguishing specification (`|⟨…⟩`), co-presence (`+`), integration (`×`).

**Dependencies.** Track (i) score parser `|⟨…⟩` support.

---

## Strategic Pace Considerations

Three framework extensions admitted within 36 hours (v7.5 Register 2026-04-20, v7.6 Production Semantics 2026-04-20, v7.7 Register Multiplicity 2026-04-21) represents aggressive specification pace. Implementation capacity will lag specification capacity — this is acknowledged as framework debt, not technical debt.

Framework debt is well-specified content awaiting implementation. Technical debt is poorly-implemented content awaiting cleanup. The former is manageable through staged rollout; the latter requires refactoring. Current state is the former.

Sequencing discipline:
- v7.5 tracks proceed as scheduled.
- v7.6 tracks proceed on independent schedule.
- v7.7 tracks proceed on third independent schedule.
- Retroactive correction (track (g)) prioritized to prevent v7.7 overloading propagating further.

Reviewer-facing and audience-facing version-tracking: the three version bumps within 36 hours are visible; each commit message and each Clarification explicitly notes legal framing (specification, not new primitives) to preserve USPTO #64/037,173 scope.

---

## Normative Summary for CAS v7.7

For all future CAS work (until v7.8 or higher):

1. `×` is reserved for true generative integration yielding emergent state.
2. `+` is the default notation for same-state multi-register co-presence.
3. `|⟨…⟩` is the preferred notation for register-set specification without operational claim.
4. Same-Noetic multi-register `×` is not licensed by default; requires explicit emergent result.
5. TKS validation heuristic (`+` → "associates with", `×` → "intensifies through") available for operator disambiguation.
6. Decision procedure (Clarification 10 Section 6): specification → `|⟨…⟩`, co-presence → `+`, integration → `×` with result.

These rules govern all CAS expression-writing in v7.7 and onward.
