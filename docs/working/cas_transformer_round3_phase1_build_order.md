# CAS Transformer Round 3 Phase-1 Build Order

**Date:** 2026-04-29
**Purpose:** Convert Round 3 specialist synthesis into a concrete Phase-1 execution sequence.

---

## Resolved Commitments

### B11: Compound-Transition Validation

Use a three-phase validation walk:

```text
phase 1: structural trace walk
phase 2: meta-logic/register walk
phase 3: tight semantic walk
```

Each failure emits structured diagnostics:

```text
phase
code
message
severity
fixable
suggestion
```

Repair is not assumed. Phase 1 uses resampling with diagnostic-conditioned context. Measure whether the second proposal succeeds. If success is below 70%, diagnostics remain developer/eval artifacts, not product claims.

### B13: TIGHT vs SHELL Zones

Final assignment:

```text
TIGHT:
  ANSWER
  REFUSE
  REFUSE_CLAIM
  REPAIR
  CLARIFY

SHELL:
  OPEN
  ACK
  MIRROR
  EMPATHIZE
  PLAN
  CLOSE
```

TIGHT turns run full transition validation. SHELL turns always run structure, register, and meta-logic validation, but production/domain semantic failures can be diagnostic warnings unless the turn makes a typed claim.

CLARIFY is TIGHT because its precondition is structural:

```text
lacunarity_map non-empty at named slot
```

### B14: Trace-History Schema

Phase 1 uses an ordered trace DAG:

```text
nodes: ordered CASTraceNode list
edges: typed CASTraceEdge table
indices: turn_type, domain
```

Query API:

```text
nodes_for_turn_type(turn_type)
latest_by_domain(domain)
predecessors(node_id, relation?)
has_feedback_license(node_id, lookback=10)
```

No general-purpose graph engine in Phase 1.

### B15: Catalyst/Inhibitor Extension

Production modifiers:

```text
ProductionModifier {
  kind: catalyst | inhibitor
  primitive
  scale
}
```

Inference-time validation:

- Modifier primitive must be a CAS primitive.
- Modifier scale must be positive.
- Catalyst/inhibitor cannot also be an ingredient.
- Catalyst/inhibitor is not consumed.

Offline/eval validation:

- Compare actual yield `Y_A` to theoretical yield `Y_T`.
- If `Y_A < Y_T` despite catalyst, trigger leakage analysis.

### B5/B6: End-Of-Transition + Renderer

Phase 1 commits to end-of-transition validation before any surface text is released.

Renderer v0 is deterministic/template-constrained. Renderer v1 may be a small CAS-conditioned neural renderer only after v0 proves recovery fidelity.

No third-party general LLM renderer in the proof wedge.

---

## Current Code Landed In This Session

Implemented in `cas-synthetic/schemas/cas_transformer.py`:

- `ValidationDiagnostic`
- `TIGHT_TURN_TYPES`
- `SHELL_TURN_TYPES`
- zone-aware transition diagnostics
- `ProductionModifier`
- catalyst/inhibitor validation
- `CASTraceEdge`
- `CASTrace`
- `TraceQueryEngine`
- `validate_compound_transition`

Implemented in `cas-synthetic/generator/cas_transformer.py`:

- `CASSurfaceRendererV0`
- `TURN_TEMPLATE_BANK` with at least 3 templates per turn type
- `CASTransformerTurnGenerator`
- 10 deterministic Phase-1 buckets:
  - `open_ack_close`
  - `clarify_lacunarity`
  - `empathetic_acknowledgment`
  - `structured_answer`
  - `planning_response`
  - `repair_response`
  - `refusal_boundary`
  - `production_recipe_explanation`
  - `meta_logic_nesting`
  - `authority_evidence_boundary`

Implemented in `cas-synthetic/scripts/generate_cas_transformer_turns.py`:

- JSONL generator CLI for CAS Transformer turn records.
- Per-record validation before write.
- Per-record recovery-fidelity validation before write.
- Bucket-count report.

Implemented in `cas-synthetic/validation/cas_transformer_recovery.py`:

- `CASSurfaceRecoveryParserV0`
- `RecoveryFidelityScorer`
- weighted recovery-fidelity component scores
- critical-field exactness checks
- renderer-v0 round-trip tests

Focused tests:

```text
pytest cas-synthetic/tests/test_cas_transformer_schema.py -q
20 passed
```

---

## Phase-1 Build Order

1. Codify zone assignment in compiler/synthetic validator. DONE in schema layer.
2. Implement compound-transition validation pipeline. DONE in schema layer.
3. Add catalyst/inhibitor fields to production semantics. DONE in schema layer.
4. Build `CASTrace` container and `TraceQueryEngine`. DONE in schema layer.
5. Generate 1,000-record held-out recoverable Level 3 eval set, stratified by bucket.
6. Implement turn-type admissibility predicates for all turn types.
7. Build structured-prediction head over typed transition fields.
8. Build deterministic surface renderer v0. DONE for CAS-turn records.
9. Build recovery parser / recovery-fidelity scorer. DONE for renderer v0.
10. Define 7,000-record wedge training corpus.
11. Train wedge model plus ablations.
12. Run falsification protocol.
13. Run M1 conditionality evaluation.
14. Run M2 recovery-fidelity evaluation.
15. Run M3-internal use-case evaluation.
16. Write wedge report and decide: graduate, iterate, or pivot.

---

## Falsification Gates

### M1: CAS Conditionality

Gate:

```text
delta >= 0.5 nats on >=80% of small-talk critical tokens
```

If failed, the system is not CAS-causal enough to claim CAS Transformer.

### M2: Recovery Fidelity

Dependency: 1,000-record held-out Level 3 eval set.

Gate:

```text
wedge RF >= baseline RF + 5 percentage points
```

Report confidence intervals; the old 30-record eval is not enough.

### M3: Internal Use-Case Preference

Phase-1 substitute for customer migration:

```text
3 internal use cases prefer wedge over 41M reranker baseline
```

Suggested use cases:

- incident classification
- scenario CAS labeling
- taxonomy validation

---

## Remaining Implementation Questions

### B6.1: Meta-Logic Template Severity

Renderer templates should select the highest-severity violated relation, not merely the first relation in topological order.

### B14.1: Multi-Transition Node Recovery

Need test cases where one surface node contains more than one transition, such as `PLAN + ANSWER`.

### B6.2: Diagnostic Resampling Success

Measure second-proposal success after structured diagnostic feedback. Do not claim repair unless success is at least 70%.

### Catalyst Registry

Need typed registry distinguishing valid catalysts/inhibitors from consumed ingredients. Current Phase-1 validation only checks that modifiers are non-consumed CAS primitives.

### Generator Coverage

The deterministic CAS-turn generator now covers 10 Phase-1 buckets, but it does not yet generate the full 7,000-record wedge training corpus or the 1,000-record held-out recoverable eval set. Those remain data-production tasks.
