# CAS Transformer Round 2 Decisions

**Date:** 2026-04-29
**Purpose:** Convert the Round 2 specialist critique into build commitments.

---

## Decision 1: CAS-Decoded, Not Merely CAS-Conditioned

CAS-conditioned:

```text
token is primary
CAS embedding is a feature
L = L_token(y_t | h_t, CAS_embedding)
```

CAS-decoded:

```text
transition is primary
surface token renders accepted transition
L = L_transition(a_t | S_t, G_t) + L_surface(y_t | accepted a_t)
```

The CAS Transformer target is CAS-decoded. The first wedge may use a bridge architecture, but it must not call itself true CAS Transformer until CAS perturbation changes token likelihoods and transitions remain valid without candidate-bank masking.

---

## Decision 2: End-Of-Transition Validation

Commit to B5:

```text
input
-> CAS encoder initializes S_t, G_t, R_t, P_t, Omega_t, Trace_t, U_t
-> transition head proposes completed a_t
-> compiler/meta/RPM/production validators accept or reject completed a_t
-> accepted a_t updates state
-> renderer emits surface text
-> recovery parser reconstructs a'_t
-> recovery-fidelity gate accepts, repairs, or asks clarify
```

Per-token masks may prune invalid candidates, but they are not the proof gate.

---

## Decision 3: Renderer V0 Is Deterministic

Renderer v0 is template-constrained. It receives only:

```text
a_t, S_t, S_t+1, G_t, Trace_t, surface_constraints
```

It may not call a third-party general LLM. A third-party renderer would reintroduce an independent language route and collapse the proof wedge into a wrapper.

Renderer v1 may be a small CAS-conditioned neural renderer after v0 proves recovery fidelity.

---

## Decision 4: Turn-Type Admissibility Predicates

Turn types require prior-state preconditions.

| Turn type | Required condition | Invalid when |
|---|---|---|
| `OPEN` | `channel_idle` | already active without need to reopen |
| `ACK` | `input_received` | no new input exists |
| `MIRROR` | `user_intent_present` | no interpretable user intent |
| `CLARIFY` | `lacunarity_detected` | required slots are already filled |
| `EMPATHIZE` | `affect_detected` | no affective signal |
| `ANSWER` | `task_active` and `claim_supported` | no support/evidence for answer |
| `PLAN` | `task_active` | no task has been established |
| `REFUSE` | `boundary_violation` | no boundary violation |
| `REFUSE_CLAIM` | `evidence_gap` | claim is supported |
| `REPAIR` | `prior_error_detected` | no prior error/mismatch |
| `CLOSE` | `response_delivered` | response has not landed |

These are validator obligations, not style guidelines.

---

## Decision 5: B4 Typed Fields Are Authoritative

Rendered notation is derived. Typed transition fields are authoritative.

Required typed frames:

```text
ProductionTransition
RegisterBinding
DomainTransition
MetaLogicContext
CASStateContext
```

String fields may exist for rendering/round-trip checks, but the validator must inspect typed frames.

---

## Decision 6: Production Semantics Validation

`ProductionTransition` validates:

```text
coefficient_i > 0
available_i >= 0
Y_T = min_i(available_i / coefficient_i)
limiting_reagent = argmin_i(available_i / coefficient_i)
leakage >= 0
```

Wrong coefficient binding, wrong limiting reagent, or wrong yield is invalid even if the expression string compiles.

---

## Decision 7: Register Multiplicity Validation

`RegisterBinding` validates:

```text
single:       exactly one register
set_spec:     at least two registers, no interaction claim
co_presence: at least two registers, no emergent omega target
integration: at least two registers and required omega target
```

This preserves the v7.7 distinction:

```text
|<A,f,T>  specification
+         co-presence
x         integration with named emergent
```

---

## Decision 8: Domain Descent / Feedback Validation

Domain descent:

```text
P -> C -> E -> O
```

`O -> P` is not descent. It is feedback and requires a license. Same-domain changes are state updates.

---

## Decision 9: Recovery-Fidelity Metric

Round-trip fidelity is:

```text
intended transition -> render -> recovered transition
```

Gate:

```text
formal CAS expression: AST equivalence required
per-transition RF:     >= 0.92
response mean RF:      >= 0.95
minimum transition RF: >= 0.90
critical fields:       exact
```

Critical fields:

```text
transition kind
compiler validity
source/target state hash
authority path
trace-node membership
```

---

## Decision 10: Shape 2 Is The Data Engine

Shape 2 is the bridge product and data engine:

```text
prompt
S_t
G_t
candidate_bank_id
proposed_transition_candidates
accepted_transition
validation_artifact
S_t+1
rendered_response
recovered_trace
recovery_fidelity
failure_repair_path
```

Every production call should generate supervised evidence for CAS Transformer training.

---

## Immediate Build Order

1. Finish typed schema tests.
2. Build deterministic CAS-turn generator with typed transitions.
3. Build meta-logic/turn-type validator.
4. Build deterministic renderer v0.
5. Build recovery parser / recovery-fidelity scorer.
6. Build Shape 2 record writer.
7. Add ConditionalityProbe after model-side CAS conditioning exists.

