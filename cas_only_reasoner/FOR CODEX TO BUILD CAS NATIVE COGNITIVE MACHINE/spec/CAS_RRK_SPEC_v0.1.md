# CAS Reasoning Runtime Kernel v0.1

Status: normative contract for runtime `0.1.0`  
Claim: bounded deterministic Python reference demonstrator only

The words MUST, MUST NOT, REQUIRED, SHOULD, and MAY are normative. `AUTHORITY_MANIFEST.yaml` has highest precedence. The Draft 2020-12 schemas define wire shapes; Python validation and transaction checks define cross-object invariants that JSON Schema cannot express.

## 1. Scope

The kernel consumes one typed `cncm.problem/0.1` packet, executes a finite symbolic episode, and emits a `RunResult` containing a summary, final state, sealed trace, and `cncm.evidence/0.1` packet. It is not a complete CAS or CCDL implementation, an English reasoner, a neural system, AGI, or a production system.

The package also exposes a separate deterministic controlled-English facade. That facade can compile only its frozen sentence grammar into typed packets and must verify a matching execution of the same compiled packet on a second fresh machine before answering. This checks deterministic execution, not the correctness of the language interpretation. It does not change the kernel's scope or make raw English authoritative.

The canonical identifiers remain `^0`-`^9`, domains `P/C/E/O`, Drive rails `F1`-`F7`, and registers `T/A/f/E`. The v0.1 packet and runtime state do not store those coordinates. `^6`, `^8`, and `^9` have the bounded meanings in the manifest, but the implementation generates no `^8` associations: candidates, if any, are declared by the caller. `^0`-`^5` and `^7` remain `OPEN-SEMANTICS`.

TKS Foundations `TF1`-`TF7`, Sub-Foundations `TF1a`-`TF7d`, their Drive adapter, and D/W/P sufficiency remain `OPEN-SEMANTICS`. `foundation_ref` is an optional opaque identifier. There are no D/W/P fields or routing rules in v0.1.

## 2. Input contract

`ProblemPacket` requires:

- `schema_version` equal to `cncm.problem/0.1`;
- `problem_id`, `goal_id`, and a nonnegative integer `seed`;
- declared `entities` and typed `predicates`;
- asserted ground `facts`, typed `rules`, and a ground `query`.

It may contain caller-declared `candidates`, caller-declared `rpm_resolvers`, one opaque `foundation_ref`, and `budgets`.

Budget keys are exactly `max_ticks`, `max_branches`, `max_rpm_depth`, `max_inference_steps`, `max_memory_queries`, and `max_repeat_states`. Runtime parsing also enforces unique declarations, predicate arity and entity types, ground facts and queries, asserted candidate facts, hypothetical assumptions, range-restricted rules, and explicit transitive-predicate declarations. Candidate ID `root` is reserved. Candidate IDs, semantic fact keys, top-level rule IDs, resolver target keys, and each resolver's local semantic fact keys and rule IDs must be unique.

No raw English, model output, external observation, or unstated world knowledge is an authoritative input. A controlled-facade assertion becomes an ordinary caller-supplied packet premise; the facade does not certify that premise as externally true.

## 3. Machine state and boot

`MachineState` has exactly the fields in `machine_state.schema.json`: runtime/tick/run/seed identity, constitution revision, Foundation/Drive/domain-power tuples, global workspace, working and episodic memory, active goal, RPM stack, branch table, pending intent IDs, commitment state, learning queue, halt status, trace head, state hash, and remaining budget.

Boot is direct; no runtime phase field or boot-transition trace exists. It installs:

- constitution `cncm-constitution/0.1`;
- `TF1`-`TF7 = UNSPECIFIED`;
- `F1`-`F7 = AVAILABLE`;
- `P/C/E = GOOD` and `O = ENABLED` as structural constants, not substantive certifications;
- one `branch-root` when candidates exist, otherwise `branch-main`;
- an empty public episodic snapshot, or the privately supplied snapshot retained on a `RunResult` for same-process internal replay, sorted by `episode_id`;
- `RUNNING`, empty trace head, and finite budgets.

The run ID is content-derived from runtime version, problem hash, exact initial episode IDs, and seed. The private snapshot path is trusted host input, not a signature, ownership proof, durable-restore API, or security boundary.

## 4. Deterministic episode driver

The implemented high-level order is:

1. Fork each declared candidate from the root, then discard only that root with reason `candidate expansion complete`; with no candidates, use the mechanical main branch.
2. Attempt exact verified episodic recall for the query.
3. Record deterministic decomposition.
4. Apply admitted inference until stable or bounded.
5. Record actual contradictions.
6. If the query lacks authoritative support, try declared missing prerequisites sequentially in canonical target order, re-running inference and contradiction detection after each successful return.
7. Re-record decomposition, classify branches, and record one shared-frame comparison.
8. Select the deterministic winner, reconstruct all commitment gates, and request decision commit.
9. Request one trace-bound episodic write.
10. Request one typed halt.

Every mutation is an intent-mediated tick. The driver and coordinator enforce hard tick, inference, branch, memory-query, and RPM-depth budgets and reserve the final tick for halt. `max_repeat_states` bounds repeated inference fingerprints. No wall-clock value participates.

## 5. Transaction semantics

`StateStore` is the sole authoritative state owner. A component can only propose an `Intent`. `TransactionCoordinator.execute`:

1. verifies the current state hash and `RUNNING` status;
2. deep-normalizes proposals, collapses identical input ID occurrence groups, and sorts the resulting trace-safe intents by provenance-bound content-derived `intent_id`;
3. requires the issuer to be both enabled and scheduled, then checks capability authority, current tick, exact pre-state hash, target/branch/goal/envelope scope, recursively string-keyed payload shape, and semantic reconstruction;
4. rejects every occurrence of a duplicated input intent ID, rejects a mixed admissible/inadmissible batch atomically, rejects mixed intent types, coalesces byte-identical same-key writes, and rejects conflicting same-key writes as `INTENT_CONFLICT`;
5. applies authorized writes in stable intent-ID order;
6. decrements the tick budget and advances the logical tick even if all intents were rejected;
7. creates and seals exactly one trace event; and
8. atomically installs the next state and appends the event. If the reserved final-tick batch does not authorize exactly one valid `HALT`, the kernel seals a fail-safe `FAULT` event.

There is no priority field, phase precondition, last-writer-wins rule, or separate `SEAL_TRACE` intent.

## 6. Branches and proof reconstruction

Candidate branches are immutable frames replaced atomically. A fork must exactly reconstruct a declared candidate: inherited parent propositions plus declared facts and hypotheses, declared constraints, empty proof/decomposition/contradiction/unknown collections, and `OPEN` status. Branch-local data cannot directly write global output or episodic memory.

Derivation intents carry a complete `ProofStep`. Acceptance requires:

- the target branch is writable; asserted roots are never overwritten, exact duplicate steps are suppressed, and alternate proof paths for one conclusion are admitted only until an authoritative support path exists;
- the operation is `RECALL`, `INFER_MODUS_PONENS`, `INFER_TRANSITIVE`, or `RPM_CHILD_RESULT`;
- every premise key, rule ID, substitution pair, conclusion, branch ID, verification flag, and provenance record reconstructs exactly;
- recall binds a verified episode with the same conclusion key;
- modus ponens/transitivity recompute from the frozen rule set and current branch;
- an RPM child result equals the deterministic result of the declared resolver.

Authoritative support is reconstructed iteratively from asserted roots and verified recall/RPM/ordinary-proof chains whose premises are themselves authoritative. A hypothetical-only query, constraint, or proof chain cannot authorize decomposition resolution, branch admissibility, comparison, commitment, or final conclusion. Final decomposition selects one canonical authoritative path.

A proposition's desirability, Foundation, Drive, comparison rank, or CAS-Ohm value cannot make a proof valid.

## 7. Comparison

The immutable evaluation frame is `cncm-shared-lexicographic/0.1`. Its hash binds criteria in this order: admissibility, hard-constraint violations, contradictions, unresolved unknowns, assumptions, proof length, then branch ID as the deterministic tie-break.

Before comparison, every declared reasoning branch must have a current decomposition, no remaining applicable parent proof, and a status exactly reconstructed as `CONTRADICTED`, `ADMISSIBLE`, or `BLOCKED`. The one allowed `ComparisonReport` must exactly reconstruct:

- the frozen evaluation-frame hash;
- lexically ordered branch IDs;
- each branch's six-integer metric;
- the metric/branch-ID winner among admissible branches.

The report must cover the complete declared branch set. It may identify a winner but does not commit it. Winner selection is a one-shot report-bound transition; every other admissible branch becomes `DOMINATED`. For one branch the report records `mechanically_deterministic_declared_path`. The frozen frame explicitly prohibits Foundation truth authority and makes no fairness claim.

## 8. RPM

RPM is a bounded resolver stack, not D/W/P reasoning. The engine considers a decomposition unknown only when a caller declared an `rpm_resolver` with that exact target key.

`PUSH_RPM` must bind the current parent goal, exact child goal, existing open/blockable branch, next stack depth, current decomposition unknown, expected result key, resolver presence, return address `branch:<id>:inference`, and resume stage `INFERENCE`. The envelope branch and embedded frame branch must match. Goal and frame IDs are content-derived; `target_foundation` merely carries the packet's opaque reference. A pushed child suspends the parent, and RPM cannot preempt an applicable parent proof or exact recall or touch a closed branch.

`RETURN_RPM` must address the exact top frame, branch, and parent goal. Success carries an exactly reconstructed `RPM_CHILD_RESULT` proof for the expected target. Resolver closure is canonical and stops at the first target-producing prefix; only that prefix is charged to inference budget. If a truncated closure cannot establish whether the target is absent, the result is budget exhaustion, not resolver failure. A genuine failure is only `NEEDS_INFORMATION` with exact detail `resolver did not establish its declared target`. Diagnostics identify the branch and target. Depth overflow, repeated goal/prerequisite identity, parent mismatch, wrong result, or invalid continuation fails closed.

## 9. Commitment and episodic write

Decision commit requires all seven exact Boolean gates:

- `principled_gate`: every hard constraint has authoritative support;
- `derivation_complete`: the query has authoritative support;
- `comparison_stable`: the latest report names this branch;
- `rpm_sufficient`: the RPM stack is empty;
- `contradiction_free`: no branch contradiction remains;
- `provenance_present`: the conclusion has provenance;
- `operational_ready`: structural `P/C/E = GOOD`, `O = ENABLED`.

The kernel recomputes every gate and rejects a supplied mismatch. Commitment is one-shot. On commit it records the selected branch/conclusion, marks that branch `COMMITTED`, and limits later mutations to one episode write and halt.

The only learning write is one verified `EpisodicRecord` from that committed branch. Its content-derived ID, problem/goal/branch binding, full conclusion, proof digest, current trace head, and current state hash must all match exactly. Success places the episode ID in the per-run `learning_queue`; any later write in that run rejects `DUPLICATE_ID`. A new boot clears this disposition while retaining trusted same-machine episodes. Online semantic, procedural, architectural, kernel, and constitutional learning are prohibited.

## 10. Halting

The state enum contains `CONCLUDED`, `NEEDS_INFORMATION`, `NEEDS_CAPABILITY`, `CONFLICT_UNRESOLVED`, `INADMISSIBLE`, `BUDGET_EXHAUSTED`, `LOOP_LIMIT_REACHED`, `DEADLOCK`, and `FAULT`; `RUNNING` is state-only. Component halt requests are limited to the exactly reconstructed statuses `CONCLUDED`, `NEEDS_INFORMATION`, `CONFLICT_UNRESOLVED`, `INADMISSIBLE`, and `BUDGET_EXHAUSTED`, with canonical lacunae/diagnostics. Components cannot request `NEEDS_CAPABILITY`, `LOOP_LIMIT_REACHED`, `DEADLOCK`, or `FAULT`. `FAULT` is emitted only by the coordinator's sealed final-tick fail-safe. `CONCLUDED` requires a coherent committed authoritative winner. Every halt requires a prior sealed trace head and itself produces the final sealed event.

## 11. Canonicalization, hashes, and trace

Canonical JSON recursively requires string mapping keys, uses sorted keys, compact separators, and ASCII escaping, and rejects NaN/Infinity. Authoritative intent payloads also reject every float. SHA-256 values are plain 64-character lowercase hexadecimal strings without a prefix.

- A problem hash covers `ProblemPacket.to_dict()`.
- A state hash covers `MachineState.to_dict()` with `state_hash` and `trace_head` omitted.
- An event hash covers the full `TraceEvent.to_dict()` with `event_hash` omitted.
- `previous_event_hash` and `parent_event_id` bind the event chain.
- A trace digest covers the canonical ordered array of complete trace-event objects, not merely their hashes.
- An evidence digest covers the evidence object before `evidence_digest` is added.

All trace events are sealed. The final state's `trace_head` equals the final event hash. Malformed raw proposals are normalized into schema-safe trace surrogates and rejected; typed but malformed mutation objects remain visible in the trace. Therefore the root intent schema is the trace envelope, while `#/$defs/accepted_intent` is the stricter typed-mutation profile. This is local tamper evidence, not remote anchoring or tamper-proof storage.

## 12. RunResult, evidence, and replay

`RunResult` retains the exact sorted `initial_episodic_memory` snapshot in memory, plus problem, initial state hash, final state, trace, and evidence. `RunResult.to_dict()` intentionally emits only `summary`, `final_state`, `trace`, and `evidence`; the initial episodic snapshot is not embedded in that bundle.

Engine-level `replay(problem, expected_run_result)` constructs a new machine through a private trusted-snapshot path from `expected_run_result.initial_episodic_memory` and requires exact equality of final state, complete trace, and evidence. Replaying from a different or absent initial episode snapshot is not the same run. The public trace-replay host API starts with empty memory and rejects nonempty injection. The private underscore path trusts its same-process caller; it does not cryptographically enforce `RunResult` ownership.

Records learned and recalled within one persistent machine follow the kernel's write checks. Public nonempty episodic injection is rejected. v0.1 has no durable-memory restore/import signature or verifier; only internal exact-`RunResult` replay can reinstall a snapshot.

`verify_bundle` fails closed and reconstructs exact bundle keys, state/event/evidence hashes, event/parent/state chains, run/runtime/tick/terminal identity, intent partition, summary projection, and the evidence projection from final state and trace. It does not re-authenticate packet facts/rules, prove ontology truth, recover an omitted initial memory snapshot, authenticate external storage, or formally verify the implementation.

## 13. Claim boundary

Passing tests demonstrates only the fixtures and invariants exercised. It does not establish complete CAS semantics, English understanding, general intelligence, consciousness, empirical validity, security, safety, scalability, or production readiness. The CAS Foundry/Cognitive Board Studio/CADA web-workbench proposal appended to the source charter is follow-on scope only; the separate owner-only playground is a runtime interaction surface, not a Foundry, canvas, editor, collaboration, registry, or publishing service. The subsequent CRQS v0.1 qualification-bench proposal is likewise `PROPOSED-NOT-IMPLEMENTED` / `OPEN-SPECIFICATION`; current tests and goldens are not CRQS qualification, earn no `D0`-`D10`, `CAS-G`, `CV`, `E-Tier`, `A-Level`, or `RMB` result, and implement no qualification or repair engine.
