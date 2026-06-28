# CAS Transformer First Wedge Plan

**Date:** 2026-04-29
**Depends on:** `docs/architecture/CAS_TRANSFORMER_ARCHITECTURE.md`
**Goal:** Prove whether CAS state causally controls language generation, including ordinary conversation.

---

## Core Question

Can a model be trained so that every response token is conditioned on a typed CAS transition, rather than CAS being added as a label or post-hoc trace?

The first wedge should answer this with a small, testable system.

---

## Phase 1: Schemas

Add schemas/dataclasses for:

```text
CASTurn
CASTraceNode
MetaLogicContext
AuthorityRelation
EvidenceRelation
CASPerturbationExample
```

Minimum fields:

```text
turn_type
source_state
target_state
noetic
domain
drive
register
omega_target
production_recipe
meta_logic_context
trace_node_id
surface_span
surface_role
compiler_status
```

Acceptance gate:

- Schemas serialize to JSONL.
- Schemas can represent small talk, technical answers, refusal, repair, clarification, and meta-logic claims.
- No record can omit `turn_type`, `trace_node_id`, or `meta_logic_context`.

---

## Phase 2: CAS-Turn Synthetic Generator

Generate compiler-first records:

```text
valid CAS trace -> meta-logic graph -> natural language response -> recovered CAS trace
```

Buckets:

```text
open_ack_close
clarify_lacunarity
empathetic_acknowledgment
structured_answer
planning_response
repair_response
refusal_boundary
production_recipe_explanation
meta_logic_nesting
authority_evidence_boundary
```

Acceptance gate:

- 1,000 records.
- 100% JSON schema-valid.
- 100% compiler-valid where a CAS expression is present.
- 100% meta-logic typecheck-valid for membership/subset/cluster/product relations.
- At least 100 records where the visible response is ordinary conversation rather than math notation.

---

## Phase 3: Meta-Logic Validator

Implement deterministic checks for:

```text
x ∈ X
A ⊆ B
NoeticCluster{...} ⊆ Noetics
StateCluster{...} ⊆ States
TraceNode ∈ TraceSet
UserUtterance ∈ UserRequestSet
UserRequestSet ⊄ SystemInstructionSet
ToolObservationSet -> EvidenceSet
EvidenceSet -> ValidatedClaimSet
ValidatedClaimSet -> RenderedResponseSet
```

Acceptance gate:

- Valid examples pass.
- Single-relation corruptions fail.
- Authority promotion errors are caught.
- Meta-logic failures produce repairable diagnostics.

---

## Phase 4: Turn-Type Admissibility Hooks

Implement the compiler-side hook that validates whether a proposed conversational transition is admissible in the prior CAS state.

Current implementation:

```text
noetic-compass-scaffold/noetic-compass/api/notation/turn_admissibility.py
noetic-compass-scaffold/noetic-compass/tests/test_turn_admissibility.py
```

Turn types currently covered:

```text
OPEN
ACK
MIRROR
CLARIFY
EMPATHIZE
ANSWER
PLAN
REFUSE
REFUSE_CLAIM
REPAIR
CLOSE
```

Acceptance gate:

- All 11 rules are exposed through `list_turn_admissibility_rules`.
- `validate_turn_admissibility(turn_type, context)` returns a JSON-ready result.
- `CLARIFY` requires lacunarity plus a named unfilled slot.
- `REFUSE` can be licensed by blocked authority-promotion relations.
- `REFUSE_CLAIM` requires an evidence gap or unsupported claim attempt.
- `ANSWER` requires active task plus supported claim.
- `REPAIR` requires detected prior error.

Status: implemented and covered by focused tests.

---

## Phase 5: Shape 2 Record Writer

Before model training, write accepted transitions into Shape 2 records:

```text
prompt
pre_state
candidates
accepted_transition
validation_artifact
rendered_response
recovered_trace
rf_score
perturbations
provenance
```

Current implementation:

```text
cas-synthetic/schemas/shape2.py
cas-synthetic/scripts/write_shape2_records.py
```

Acceptance gate:

- Every accepted `CASTurnRecord` can be converted into a valid Shape 2 JSONL record.
- Exactly one candidate is marked accepted.
- Recovery-fidelity score is persisted.
- Compound transition diagnostics are persisted.
- Perturbations survive into the Shape 2 record.
- The writer can append many records deterministically.

---

## Phase 6: Conditionality Probe

Add a probe that measures whether token logits depend on CAS state.

For same prompt and same prefix:

```text
correct CAS state
corrupted Noetic
corrupted Domain
corrupted Register
corrupted Drive
corrupted turn type
corrupted meta-logic authority relation
corrupted evidence membership
```

Metric:

```text
delta = log P(correct token | correct CAS) - log P(correct token | corrupted CAS)
```

Acceptance gate:

- `delta > margin` for CAS-critical tokens.
- Meta-logic corruption changes allowed claim/rendering behavior.
- Small-talk responses also show CAS dependency.

---

## Phase 7: Minimal Model Patch

Do not rebuild the whole model first.

Patch current CAS-Native with:

```text
CASStateEmbedding
MetaLogicEmbedding
TurnTypeEmbedding
TraceNodeEmbedding
CAS-conditioned LM head or adapter
ConditionalityProbe
```

Near-term architecture:

```text
hidden_state + CAS_state + meta_logic_state + turn_type -> token logits
```

This is not the final CAS Transformer, but it is the smallest test of whether CAS conditioning can causally steer generation.

Acceptance gate:

- Ablating CAS state degrades token loss on CAS-turn dataset.
- Permuting CAS state degrades token likelihood more than random noise.
- Correct CAS state beats corrupted CAS state under conditionality probe.
- Generated responses recover to intended CAS trace above threshold.

---

## Phase 8: Report

Produce:

```text
CAS_TRANSFORMER_WEDGE_REPORT.md
```

Required sections:

- Dataset composition.
- Compiler-validity result.
- Meta-logic validity result.
- Conditionality probe result.
- Small-talk grounding result.
- Perturbation result.
- Failure cases.
- Whether the system is still a wrapper or has evidence of CAS-causal generation.

---

## Non-Negotiable Framing

Do not call the wedge a true CAS Transformer unless CAS state perturbations causally alter token probabilities.

Do not call ordinary conversation outside CAS.

Do not let meta-logic remain notation-only. The meta-logic layer must govern nesting, evidence, authority, containment, trace membership, and claim licensing.
