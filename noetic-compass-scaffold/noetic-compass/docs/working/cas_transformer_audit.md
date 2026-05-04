# CAS Transformer Turn Generator — Feature Audit

**Date:** 2026-05-04
**Auditor branch:** `audit-cas-transformer-feature`
**Trigger:** Phase 1 T1 hygiene commit discovered that `cas-synthetic/generator/__init__.py` imports
from a 559-line module that is local-only and not present in `origin/master`.

## Summary

The CAS Transformer turn generator is a deterministic, template-driven synthetic data feature
that emits Phase-1 conversational training records. Each record is built from a typed CAS
transition, a typed meta-logic context, and a renderer-v0 surface span — no LLM is called.
The feature spans three layers (schema -> generator -> recovery validator) plus a pytest
trio, and is fully self-contained with zero `TODO`/`FIXME` markers and 33 passing tests.
The generator drives 10 scenario buckets covering OPEN/ACK/CLARIFY/EMPATHIZE/ANSWER/PLAN/
REPAIR/REFUSE/REFUSE_CLAIM/production-recipe/meta-logic-nesting/authority-evidence patterns.
The recovery validator gates the round-trip `intended transition -> rendered text -> recovered
transition` path with a six-component weighted score (turn_type 0.25, cas_axis 0.25,
meta_logic 0.15, trace_span 0.15, ast_equivalence 0.10, authority_surface 0.10) plus three
critical-exact fields. The hygiene commit was scope-creep: this is a feature ship, not a
no-op import.

## Inventory

| File | Lines | Status (vs `origin/master`) | Role |
|------|-------|------------------------------|------|
| `cas-synthetic/generator/__init__.py` | 42 | **Modified** (M) — adds 8 lines of imports/exports | Entry point |
| `cas-synthetic/generator/cas_transformer.py` | 559 | **Untracked** (??) — new file | `CASTransformerTurnGenerator` + `CASSurfaceRendererV0` + `RenderedNode` + 10 scenario builders + `TURN_TEMPLATE_BANK` |
| `cas-synthetic/schemas/cas_transformer.py` | 935 | **Untracked** (??) — new file | All typed dataclasses: `CASTurnRecord`, `CASTraceNode`, `CASTrace`, `CASTransition`, `MetaLogicContext`/`Object`/`Relation`, `CASStateContext`, `RegisterBinding`, `ProductionTransition`/`Ingredient`/`Modifier`, `DomainTransition`, `CASTraceEdge`, `CASPerturbationExample`, `ValidationDiagnostic`, `TraceQueryEngine`, `validate_compound_transition` |
| `cas-synthetic/validation/cas_transformer_recovery.py` | 293 | **Untracked** (??) — new file | `CASSurfaceRecoveryParserV0`, `RecoveryFidelityScorer`, `RecoveryFidelityResult`, weighted-score gate |
| `cas-synthetic/tests/test_cas_transformer_schema.py` | 478 | **Untracked** (??) — new file | 20 schema validation tests |
| `cas-synthetic/tests/test_cas_transformer_generator.py` | 105 | **Untracked** (??) — new file | 7 generator/renderer tests |
| `cas-synthetic/tests/test_cas_transformer_recovery.py` | 91 | **Untracked** (??) — new file | 6 recovery-validator tests |
| **Audited core total** | **2,503** | | |

### Adjacent untracked files (NOT audited as ship surface — flagged for separate decision)

| File | Lines | Status | Why excluded |
|------|-------|--------|--------------|
| `cas-synthetic/schemas/shape2.py` | 334 | ?? | Imports `cas_synthetic.schemas.diagram_graph` which **does not exist** (only stale `.pyc` in `__pycache__/`). Cannot import. |
| `cas-synthetic/scripts/generate_cas_transformer_turns.py` | 116 | ?? | CLI driver; depends on the audited core; could ship in the same PR or follow-up |
| `cas-synthetic/scripts/write_shape2_records.py` | 94 | ?? | Depends on broken `shape2.py` |
| `cas-synthetic/tests/test_shape2_record_writer.py` | 98 | ?? | Errors on collection because of the broken `diagram_graph` import |
| `docs/working/cas_transformer_first_wedge_plan.md` | n/a | ?? | Planning doc |
| `docs/working/cas_transformer_round3_phase1_build_order.md` | n/a | ?? | Planning doc |

The `__init__.py` only re-exports the three audited core symbols (`CASSurfaceRendererV0`,
`CASTransformerTurnGenerator`, `RenderedNode`); shape2 / scripts / docs are NOT pulled in
by the import chain and can be sequenced independently.

## Test Results

Command:

```
python -m pytest cas-synthetic/tests/test_cas_transformer_schema.py \
                 cas-synthetic/tests/test_cas_transformer_generator.py \
                 cas-synthetic/tests/test_cas_transformer_recovery.py
```

**Result: 33 passed, 0 failed, 0 skipped, 0.23s.**

- 20/20 schema tests pass — covers carrier compatibility, authority license blocking,
  production limiting-reagent computation, register integration/co-presence rules,
  domain feedback license, TIGHT vs SHELL zone severity, three-phase compound validation,
  trace cycle detection, query-engine indexing, feedback-license window lookup.
- 7/7 generator tests pass — template coverage across all 11 turn types, all 10 scenario
  buckets emit valid records, deterministic-for-same-seed, trace-edge serialization,
  production recipe with catalyst modifier, CLARIFY zone + lacunarity precondition,
  perturbation set on every record.
- 6/6 recovery tests pass — full-fidelity score = 1.0 on all 20 generated records,
  detects turn-type mismatch, detects ast-expression drift, detects
  `compiler.valid=False` as critical failure, serializes structured payload.

The `test_shape2_record_writer.py` file (NOT in the audit surface) errors on
collection due to the missing `diagram_graph` module — that is an independent
issue and does not affect the audited core.

## Coherence Assessment

The audited surface is **ship-ready**:

- No `TODO`, `FIXME`, `XXX`, `HACK`, or `NotImplementedError` markers in any of
  the six files.
- All imports inside the audited core resolve (`cas_synthetic.schemas.cas_transformer`
  is the only cross-module dependency, and it is part of the audited surface).
- The `__init__.py` modification is minimal, additive, and the three exports it
  surfaces all exist.
- 100% of recovery scoring on 20 deterministic records is exact (score == 1.0,
  critical_exact == True).
- The renderer is bounded (template bank with 3+ templates per turn type), and
  the scenario builders enumerate all Phase-1 buckets.
- v7.6 production semantics, v7.7 register multiplicity (`integration` /
  `co_presence` / `set_spec` / `single`), and domain-descent / feedback-license
  rules are all enforced at the schema layer with negative-path tests.

## Recommendation

**Ship as a single PR.** This is a coherent vertical slice (schema +
generator + recovery validator + tests) with green tests and no ragged edges.
Splitting it would create artificial boundaries — the schema is dead code without
the generator, the generator can't validate without the schema, the recovery
validator gates the generator's output, and the tests cross-cut all three.

- **Branch name (for the ship PR — not this audit PR):**
  `feat-cas-transformer-turn-generator-v0`
- **PR title (for the ship PR):**
  `feat(cas-synthetic): CAS Transformer turn generator v0 + schema + recovery validator`

Recommended ship boundary:

- IN: the six files in the "audited core" inventory plus the `__init__.py`
  modification.
- OUT: `shape2.py`, `write_shape2_records.py`, `test_shape2_record_writer.py`
  (broken `diagram_graph` dep — fix in a follow-up).
- DECIDE: `scripts/generate_cas_transformer_turns.py` (116 lines) — small, clean,
  depends only on audited core. Reasonable to include if the user wants a runnable
  CLI shipped with the feature; defer if the user prefers a strictly typed-API ship.
- DEFER: planning docs (`docs/working/cas_transformer_*.md`) — separate doc PR.

## Open Questions for the User

1. **Include the CLI driver?** `cas-synthetic/scripts/generate_cas_transformer_turns.py`
   (116 lines) imports only the audited core and looks clean. Ship it in the same
   PR or sequence as a follow-up?
2. **Scope of the planning docs.** `docs/working/cas_transformer_first_wedge_plan.md`
   and `cas_transformer_round3_phase1_build_order.md` are untracked. Bundle into
   the ship PR for context, or land separately?
3. **Shape2 status.** `cas-synthetic/schemas/shape2.py` references a deleted
   `diagram_graph.py` module (only stale `.pyc` exists). Is that module being
   resurrected, or is shape2 being abandoned/rescoped? This blocks the
   `test_shape2_record_writer.py` test independent of this audit.
4. **Phase 1 T1 hygiene.** Was the T1 commit intended as pure no-op hygiene, or
   was the user expecting to bundle this feature ship into T1? The audit
   confirms T1 cannot be a clean hygiene commit while `generator/__init__.py`
   imports from an unshipped module — either the imports are reverted (defer
   feature) or the feature is shipped first (this PR's recommendation).
5. **Renderer-v0 ceiling.** Recovery hits 1.0 on the deterministic generator
   today. Is there a planned non-template renderer (renderer-v1) that the
   recovery scorer is expected to handle? If so, the 0.92-pass threshold and
   six-component weighting are the levers to revisit.
