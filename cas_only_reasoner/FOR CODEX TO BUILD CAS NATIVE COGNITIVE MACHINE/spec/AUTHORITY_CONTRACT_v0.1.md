# CNCM-RRK Authority Contract v0.1

Status: normative for runtime `0.1.0`

Component names are software roles, not persons, agents, or claims of consciousness.

## 1. Sole-writer rule

No reasoning component directly owns authoritative state. Components emit immutable typed intents. `TransactionCoordinator` validates authority, state binding, typed payloads, semantic reconstruction, conflicts, and invariants. `StateStore._commit_from_coordinator` is the sole state-installation path and accepts only a correctly rehashed state.

`TraceFabric` is append-only and validates event sealing, chain identity, and event hash. It cannot authorize an intent or mutate machine state.

## 2. Exact issuer/capability matrix

Only the following triples are authorized:

| Issuer | Intent | Required capability |
|---|---|---|
| `reasoning_engine` | `DERIVE_PROPOSITION` | `derive_branch_local` |
| `reasoning_engine` | `RECORD_DECOMPOSITION` | `decompose` |
| `reasoning_engine` | `RECORD_CONTRADICTION` | `detect_contradiction` |
| `memory_controller` | `DERIVE_PROPOSITION` | `recall_verified_episode` |
| `branch_manager` | `FORK_BRANCH` | `fork_branch` |
| `branch_manager` | `DISCARD_BRANCH` | `discard_branch` |
| `comparison_system` | `SET_BRANCH_STATUS` | `classify_candidate` or `report_selected_candidate` |
| `comparison_system` | `RECORD_COMPARISON` | `compare_under_shared_frame` |
| `rpm_controller` | `PUSH_RPM` | `push_prerequisite_goal` |
| `rpm_controller` | `RETURN_RPM` | `return_prerequisite_result` or `return_prerequisite_failure` |
| `commitment_latch` | `DECISION_COMMIT` | `request_decision_commit` |
| `write_back_controller` | `WRITE_EPISODE` | `write_committed_episode` |
| `halting_controller` | `HALT` | `request_typed_halt` |

`scheduler` and `trace_fabric` have empty intent sets. Any unknown issuer, wrong issuer/intent pair, or wrong capability is `UNAUTHORIZED_ISSUER`. Capability strings do not transfer authority between issuers.

## 3. Absolute prohibitions

`EXTERNAL_ACTION` and `PROTECTED_PATCH` are rejected as `INTENT_TYPE_PROHIBITED` before issuer checks. No issuer can enable them through configuration. The kernel has no authority for tools, network calls, subprocesses, messages, payments, devices, source modification, protected-contract modification, or other external effects.

Raw English, a neural model, an LLM, CAS-Ohm, Foundation identity, Drive availability, candidate preference, and comparison rank have no proof or mutation authority.

The optional controlled-English facade is a host-side deterministic adapter only. Its exact grammar may translate explicit user assertions into caller-supplied packet premises, but it does not attest their truth, issue kernel intents, or gain proof, commitment, action, or memory-write authority.

The explicit CLI host adapter may read a named problem file and write requested artifacts. Those file operations are user-invoked host I/O, not a kernel intent or cognitive authority.

## 4. Snapshot binding

An intent must bind:

- the current logical tick in `created_at_tick`;
- exactly one `precondition.state_hash` equal to the current state;
- a recomputable content-derived `intent_id`;
- its exact typed target scope;
- branch, goal, stack, or report identities required by that intent.

The issuer must be both enabled and scheduled. The intent ID binds normalized provenance as well as every other content field. Stale tick/hash is `STALE_SNAPSHOT`. Wrong scope is `INVALID_TARGET_SCOPE`. Invalid raw types, recursively non-string mapping keys, floats, wrong mutation keys, or malformed content IDs are `MALFORMED_MUTATION`.

## 5. Proof authority

`reasoning_engine` cannot self-assert a proof. Ordinary derivations must byte-for-byte equal the next canonical proof reconstructed from the current branch and frozen packet rules; the issuer is bound to the ordinary rule operation. `memory_controller` may issue only exact-query `RECALL` proofs bound to an installed verified episode. RPM success must equal a new deterministic execution of the declared resolver.

Authoritative output support is an iterative dependency graph rooted in asserted propositions or verified source-specific recall/RPM results. Ordinary conclusions are authoritative only when every premise is authoritative. Hypothetical-only queries, constraints, and proof chains cannot authorize classification, comparison, commitment, or conclusion.

The input packet is the rule-authority boundary in v0.1: rules require structural validity and provenance, but the model has no cryptographic signer or separate verified-rule registry. That limitation must remain visible in claims.

## 6. Branch authority

`branch_manager` can fork only a declared candidate with an exact reconstructed initial frame, matching envelope identity, unique branch ID, and remaining branch budget. Candidate ID `root` is reserved. Direct discard is limited to exact `branch-root` after all declared candidate forks, with reason `candidate expansion complete`, before comparison or commitment. It cannot derive, compare, commit, write an episode, or halt.

Reasoning and memory writes are branch-local. A branch that is absent, not writable, committed, or discarded fails with the applicable typed rejection. Branch contents remain in the evidence record after discard but cannot become authoritative output or learning source.

## 7. Comparison and decision authority

`comparison_system` may classify a branch only from current decomposition and inference closure. Status must reconstruct exactly. It may record exactly one report only when it covers every declared reasoning branch and the frozen evaluation frame, branch identities, metrics, and winner reconstruct exactly. It may report selection once, setting the winner `SELECTED` and other admissible branches `DOMINATED`; it cannot decision-commit.

`commitment_latch` can request commit only for an admissible/selected branch. The coordinator independently recomputes all seven gate values, query support, contradiction absence, latest comparison winner, empty RPM stack, provenance, and structural domain power. The apply path marks exactly one winner committed and discards remaining eligible branches.

Routine state commits on earlier ticks confer no decision authority.

## 8. RPM authority

`rpm_controller` may push only an exact next-depth frame for a declared missing prerequisite and resolver on an open/blockable branch. The intent envelope, child/parent goal, frame, branch, target, return address, and resume stage must all agree. Push suspends the parent and cannot preempt available parent inference or exact recall. Return is allowed only through the exact top frame, branch, parent goal, and expected result. Success requires full child-proof reconstruction and charges the target-producing proof prefix; truncated closure is budget exhaustion. Genuine failure is only `NEEDS_INFORMATION` with canonical detail. Closed branches cannot be touched.

RPM cannot invent Foundation or D/W/P semantics. `target_foundation` is carried opaquely.

## 9. Episodic-write authority

`write_back_controller` may append one episodic record only when:

- its branch is `COMMITTED` and selected;
- its conclusion equals the committed conclusion;
- its proof digest reconstructs from that branch;
- its episode ID reconstructs from problem, goal, full conclusion, branch, proof digest, current trace head, and current state hash;
- it is `verified: true`;
- it binds the current nonempty trace head and current state hash.

A discarded branch, uncommitted outcome, mismatched proof/state/trace identity, duplicate episode ID, second write in one run, or unverified record fails closed. A successful write stores its episode ID in `learning_queue`; the queue resets at boot while same-machine episodes persist. v0.1 writes no abstention episode and performs no semantic/procedural/constitutional promotion.

Public constructors, boot helpers, sessions, run helpers, and trace replay reject nonempty externally supplied episodic memory. Private engine replay passes the snapshot retained inside the supplied `RunResult` through `_from_trusted_snapshot`. This is a trusted same-process implementation boundary, not a security control, signature, or cryptographic ownership check. A future restore API requires a new authenticated admission contract.

## 10. Halt authority

`halting_controller` can request only `CONCLUDED`, `NEEDS_INFORMATION`, `CONFLICT_UNRESOLVED`, `INADMISSIBLE`, or `BUDGET_EXHAUSTED`, with canonical sorted unique lacunae and diagnostics that exactly reconstruct current state. It cannot request `NEEDS_CAPABILITY`, `LOOP_LIMIT_REACHED`, `DEADLOCK`, or `FAULT`. A prior sealed trace head is mandatory. `CONCLUDED` additionally requires a coherent committed authoritative winner. The halt transition itself becomes the final sealed trace event. If the reserved final tick does not authorize exactly one valid halt, the coordinator seals `FAULT` as a fail-safe.

An exception, process exit, or exhausted host work list is not a typed authoritative halt.

## 11. Conflict and atomicity

All normalized intents in one tick are validated against the same pre-state. A duplicated input intent-ID occurrence group is rejected in full. Mixing valid and invalid proposals or different intent types poisons the batch atomically. Same-key identical mutations with distinct IDs coalesce deterministically; later writes are trace-rejected. Same-key different mutations are all rejected. Aggregate branch, inference, and memory budgets are enforced before apply. Authorized mutations are applied in intent-ID order, then one state and one trace event are committed. No partial mutation is exposed.

## 12. Change control

Expanding any issuer, capability, intent, target, learning path, proof source, or external-effect authority requires a versioned manifest/spec/schema change and new negative tests. Runtime configuration alone cannot expand this graph.
