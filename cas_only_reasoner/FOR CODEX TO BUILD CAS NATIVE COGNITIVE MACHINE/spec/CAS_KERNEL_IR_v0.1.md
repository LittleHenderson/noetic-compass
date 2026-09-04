# CAS Kernel IR v0.1

Status: normative description of the implemented intent and trace IR

This IR is the typed boundary between deterministic components and the single-writer kernel. It is not CCDL syntax and has no raw-English compiler.

## 1. Intent envelope

Every `Intent.to_dict()` has exactly:

`intent_id`, `intent_type`, `issuer_subsystem`, `required_capability`, `target_scope`, nullable `branch_id`, nullable `goal_id`, `precondition`, `proposed_mutation`, `created_at_tick`, and `provenance`.

`precondition` contains only the current plain 64-hex `state_hash`. `intent_id` is `intent-` plus the first 16 hex characters of the SHA-256 digest of every normalized content field, including canonically sorted provenance. The kernel rejects the wrong tick, stale hash, recursively non-string mapping keys, floating-point values, malformed or provenance-mismatched content IDs, unauthorized issuer/capability pairs, wrong target/branch/goal/envelope scope, and irreconstructible mutations. Intent payloads are deep immutable snapshots.

An intent is a request, never an authority token. There is no priority, coordinate, phase, status, mutation digest, or `authority_claim` field.

## 2. Closed intent set and typed mutation

| Intent type | Exact mutation keys | Exact target scope |
|---|---|---|
| `FORK_BRANCH` | `branch` | `branch_table` |
| `DERIVE_PROPOSITION` | `proof` | `branch:<branch_id>` |
| `RECORD_DECOMPOSITION` | `decomposition` | `branch:<branch_id>` |
| `RECORD_CONTRADICTION` | `atom_key` | `branch:<branch_id>` |
| `SET_BRANCH_STATUS` | `status` | `branch:<branch_id>` |
| `DISCARD_BRANCH` | `reason` | `branch:<branch_id>` |
| `RECORD_COMPARISON` | `report` | `global_workspace` |
| `PUSH_RPM` | `frame` | `rpm_stack` |
| `RETURN_RPM` success | `frame_id`, `success: true`, `proof` | `rpm_stack` |
| `RETURN_RPM` failure | `frame_id`, `success: false`, `failure_status`, `detail` | `rpm_stack` |
| `DECISION_COMMIT` | `conclusion`, `gate_results` | `commitment_state` |
| `WRITE_EPISODE` | `episode` | `episodic_memory` |
| `HALT` | `status`, `lacunae`, `diagnostics` | `halt_status` |
| `EXTERNAL_ACTION` | none | `prohibited` |
| `PROTECTED_PATCH` | none | `prohibited` |

`EXTERNAL_ACTION` and `PROTECTED_PATCH` exist only so attempts are typed and rejected. They have no apply semantics. No `POWER_DOMAIN`, `ADVANCE_PHASE`, `SEAL_TRACE`, tool, network, or generic mutation instruction exists. The root intent JSON Schema describes the trace-safe envelope and may retain arbitrary JSON members inside a rejected mutation object. `intent.schema.json#/$defs/accepted_intent` adds the strict typed-mutation shape; kernel semantic reconstruction remains stronger than either schema.

## 3. Reasoning realization

The inference enum contains `RECALL`, `ASSOCIATE`, `DECOMPOSE`, `INFER_MODUS_PONENS`, `INFER_TRANSITIVE`, and `RPM_CHILD_RESULT`. Only `RECALL`, the two rule operators, and `RPM_CHILD_RESULT` may occur in an accepted `DERIVE_PROPOSITION` proof.

`^6` is represented by `RECORD_DECOMPOSITION`, not a `DECOMPOSE` proof. `^8` candidate association is not executed; candidates are declared in the problem packet. `^9` conclusion is represented by the conclusion inside an exactly reconstructed proof step.

## 4. Branch IR

`BranchFrame` contains identity/parent/goal/candidate fields, assumptions, propositions, recalled episode IDs, proof steps, decompositions, hard constraints, contradictions, unknowns, status, and creation tick.

Runtime status values are `OPEN`, `BLOCKED`, `CONTRADICTED`, `DOMINATED`, `ADMISSIBLE`, `SELECTED`, `COMMITTED`, `DISCARDED`, and `FAULTED`. The comparison issuer can request only `BLOCKED`, `CONTRADICTED`, `DOMINATED`, `ADMISSIBLE`, or `SELECTED`. `DISCARD_BRANCH` sets `DISCARDED`. Decision commit sets the winner `COMMITTED` and other non-contradicted/non-faulted branches `DISCARDED`.

Discard retains the immutable branch and trace evidence; it changes status rather than deleting the frame. A direct `DISCARD_BRANCH` request is admitted only for the exact `branch-root` candidate-expansion transition with canonical reason, before comparison or commitment. No discarded branch can be an episodic-write source.

## 5. Comparison IR

`ComparisonReport` contains a content-derived ID, exact evaluation-frame hash, ordered branch IDs, branch/six-integer metric pairs, shared features, differences, nullable winner, and nullable single-candidate reason.

Kernel acceptance requires exactly one comparison, covering every declared reasoning branch. Each branch must have current decomposition/inference closure and an exactly reconstructed classification. The kernel recomputes the frame hash, lexical branch order, every metric, and the winner. Winner reporting is one-shot: the winner becomes `SELECTED` and other admissible branches become `DOMINATED`. Comparison cannot apply decision commitment.

## 6. RPM IR

`RPMFrame` contains exactly `frame_id`, child and parent goal IDs, branch ID, nullable opaque Foundation reference, blocked prerequisite key, return address, resume stage, expected result key, and positive depth.

Push acceptance binds every identity to the current state, current decomposition, declared resolver, intent envelope, exact child/parent goal, return address/stage, next depth, and cycle/depth checks. It suspends parent transitions and cannot preempt an available parent proof or exact recall or address a closed branch. Return acceptance binds the top frame ID, branch, expected result, child proof or exact `NEEDS_INFORMATION` failure, parent goal, and stack pop. Successful child cost is the exact target-producing prefix; a truncated closure is `BUDGET_EXHAUSTED`. Missing prerequisites are attempted sequentially, and failure diagnostics name the branch and target. There is no generic continuation, suspended phase object, D/W/P status, or independently scheduled child machine.

## 7. Atomic tick IR

For one `execute` call the coordinator deep-normalizes intents, collapses occurrence groups by provenance-bound intent ID, sorts by ID, validates each against the same pre-state, resolves write-key conflicts, enforces aggregate budgets, and applies the accepted set atomically. Every occurrence in a duplicate input-ID group is rejected `DUPLICATE_ID`. A mixture of valid and invalid proposals poisons the whole batch; mixed intent types reject atomically. Identical same-key mutations with distinct IDs coalesce: the first is authorized and later writes are rejected `DUPLICATE_ID`. Different same-key mutations are all rejected `INTENT_CONFLICT`.

The tick always advances once and decrements `ticks_remaining`, including a rejection-only tick. `pending_intents` becomes the ordered unique IDs proposed during that tick. Recall decrements the aggregate memory-query budget; ordinary derivations and the exact RPM target-producing prefix decrement aggregate inference budget; fork decrements aggregate branch budget. On the final tick, exactly one valid `HALT` must authorize; otherwise the kernel seals fail-safe `FAULT`.

## 8. Trace event IR

Every tick emits one `TraceEvent` with exactly:

- event/parent/tick/run/runtime identity;
- pre-state hash;
- enabled and scheduled component IDs;
- full trace-safe proposed intents, including rejected malformed typed payloads or schema-safe surrogates for raw inputs that could not be normalized as an `Intent`;
- authorized intent IDs and typed rejected intents;
- committed write keys;
- post-state hash and terminal status;
- previous event hash, event hash, and `sealed: true`.

The event ID is `event-<run_id>-<six-digit logical_tick>`. First-event parent is null and previous hash is empty. Each later event binds both the preceding ID and hash. Trace recording validates the chain but grants no authority.

## 9. Rejection IR

The closed rejection set is:

`UNAUTHORIZED_ISSUER`, `INTENT_TYPE_PROHIBITED`, `INVALID_TARGET_SCOPE`, `STALE_SNAPSHOT`, `INTENT_CONFLICT`, `BRANCH_NOT_FOUND`, `BRANCH_NOT_WRITABLE`, `INVALID_PROOF`, `DUPLICATE_ID`, `BRANCH_BUDGET_EXHAUSTED`, `INFERENCE_BUDGET_EXHAUSTED`, `MEMORY_BUDGET_EXHAUSTED`, `STACK_FAULT`, `RPM_DEPTH_EXHAUSTED`, `RPM_CYCLE`, `COMMITMENT_GATES_FAILED`, `UNRESOLVED_CONTRADICTION`, `UNSEALED_TRACE`, `UNCOMMITTED_LEARNING_SOURCE`, `DISCARDED_BRANCH_REFERENCE`, `INVALID_TERMINAL_STATUS`, and `MALFORMED_MUTATION`.

Parser-level `ContractError` values are not trace rejection codes. Earlier draft names such as `WRITE_CONFLICT`, `ISSUER_UNAUTHORIZED`, `UNSUPPORTED_CONCLUSION`, and `HASH_MISMATCH` are not v0.1 enum values.

## 10. Compiler boundary

The runtime accepts already typed `ProblemPacket` objects or mappings. A future compiler may emit these packets, but compiler acceptance cannot authorize an intent, authenticate a rule, or add semantics. Full CCDL, English, coordinate lowering, and ontology compilation are out of scope.
