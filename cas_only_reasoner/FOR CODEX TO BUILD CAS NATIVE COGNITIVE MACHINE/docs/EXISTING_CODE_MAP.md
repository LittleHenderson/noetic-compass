# Existing Code Map

This map describes the frozen v0.1 reference implementation as it exists. It is not a proposed architecture and does not claim a production CNCM, brain, or AGI system.

## Runtime modules

| File | Current responsibility | Does not do |
|---|---|---|
| `cncm/canonical.py` | Recursive primitive conversion, rejection of non-string mapping keys, compact sorted canonical JSON, SHA-256 digest, and content-derived 16-hex IDs. | Signatures, remote anchoring, alternate canonicalization profiles. |
| `cncm/model.py` | Immutable declarations, packets, proofs, branches, RPM frames, state, intents, trace, and enums; packet uniqueness/type checks; reserved `root` candidate rejection; provenance-bound intent IDs; deep-frozen intent payloads. | Authenticated rule trust, general-English parsing, ontology meaning. |
| `cncm/semantics.py` | Semantic-key maps, iterative authoritative-support traversal, iterative bounded unification, canonical Horn proof selection, decomposition, contradiction detection, target-prefix RPM closure, and loop fingerprints. | Candidate generation, D/W/P, probabilities, externally grounded truth, causal semantics. |
| `cncm/kernel.py` | Frozen issuer/capability matrix, structural boot state, sole-writer store, append-only trace fabric, trace-safe proposal normalization, exact intent/state reconstruction, atomic conflict and batch-budget handling, one-shot guards, final-tick fail-safe, and immutable state replacement. | High-level problem strategy, external actions, durable database. |
| `cncm/engine.py` | Ordered episode driver: exact recall, declared candidate expansion and root discard, decomposition, bounded inference, sequential RPM prerequisites, branch classification, comparison/selection, commit, one episodic write, typed halt, evidence, and exact `RunResult` replay. | General planning, native association, unbounded recursion, self-modification. |
| `cncm/verification.py` | Fail-total verification of exact bundle shape, state/event hashes, event chain, intent partition, terminal sequence, summary projection, evidence projection, and cross-artifact bindings. | Re-executes proof semantics, authenticates external storage, recovers omitted initial memory. |
| `cncm/api.py` | Host calls for `boot`, `run`, `replay`, `verify_evidence`, and a step-capable `KernelSession`. | Expands authority or persists data. |
| `cncm/conversation.py` | Deterministic controlled-English dialogue facade for explicit facts, rules, questions, bounded referent clarification, response plans, evidence verification, and same-packet fresh-machine execution parity. | Independent language-semantic validation, general-English understanding, probabilistic language inference, external models or tools, durable memory, action authority, or chatbot qualification. |
| `cncm/math_model.py` | Exact rational and expression IR; content-bound claims, proposals, and receipts; fixed math theory/branch/checker identities. | General symbolic algebra, approximation, theorem discovery, RRK state authority. |
| `cncm/math_parser.py` | Bounded frozen ASCII expression and statement grammar. | Implicit multiplication, decimals, exponents, functions, free-form mathematical language. |
| `cncm/math_normalize.py` | Exact evaluation, substitution, and canonical Q-linear normalization. | Nonlinear normalization or approximation. |
| `cncm/math_kernel.py` | Pure proof-step reconstruction, fail-closed guards, receipt-chain re-execution, and checked-claim issuance. | State writes, theory mutation, learning, or candidate authority. |
| `cncm/math_engine.py` | Deterministic one-variable linear proof generation and whole-result semantic re-execution. | General equation solving or strategy learning. |
| `cncm/math_counterexample.py` | Deterministic bounded integer search and independent retained-search re-execution. | Proof by finite-search absence or unbounded search. |
| `cncm/math_api.py` | Stable host-facing solve, validate, counterexample, and verification surface. | Authority expansion or persistence. |
| `cncm/cli.py` | Explicit file-host adapter for `check`, `run`, `replay`, `verify`, and `demo`. | Kernel-initiated I/O or action execution. |
| `cncm/__init__.py` | Public symbol exports. | Runtime logic. |
| `cncm/__main__.py` | `python -m cncm` entry point. | Runtime logic. |

## Core control flow

```text
typed ProblemPacket
  -> strict parsing, normalization, uniqueness, and type validation
  -> boot_state(exact same-instance episodic snapshot)
  -> StateStore + TraceFabric + TransactionCoordinator
  -> scheduled components propose deep-immutable intents
  -> trace-safe normalization or schema-safe malformed surrogate
  -> enabled + scheduled issuer/capability + exact goal/scope/payload checks
  -> duplicate/mixed/admissibility conflict and aggregate budget checks
  -> one atomic MachineState replacement
  -> one sealed TraceEvent
  -> typed halt or reserved-final-tick FAULT fail-safe
  -> RunResult(summary, final_state, trace, evidence)
```

The optional conversational path is a separate facade over that typed boundary:

```text
controlled sentence
  -> exact grammar match or typed rejection/clarification
  -> explicit dialogue/referent state
  -> exact ProblemPacket compilation
  -> two fresh-machine runs of the same compiled packet
  -> evidence verification + deterministic execution-parity comparison
  -> response plan and bounded natural-language rendering
```

It does not grant raw text authority inside the kernel. A resolved question is answered only when both same-packet fresh-machine executions verify and match; otherwise the facade fails closed. This parity check does not independently prove that the language interpretation was correct.

`RunResult` also retains `problem`, `initial_episodic_memory`, and `initial_state_hash` in memory. Its serialized dictionary omits the problem and initial episodic snapshot, relying on hashes and projections in summary/evidence. Public nonempty episodic-memory injection is rejected. Engine replay passes the retained snapshot to private `_from_trusted_snapshot`; that method trusts its same-process caller and does not enforce snapshot origin. It is implementation plumbing, not a security or cryptographic ownership mechanism.

## State and authority ownership

- `StateStore.snapshot()` returns the current immutable state.
- Only `TransactionCoordinator` calls the private commit path.
- Every accepted mutation produces a new dataclass graph.
- Intent preconditions and mutation payloads are recursively frozen; later caller mutation cannot alter a sealed trace.
- Intent IDs bind type, issuer, capability, target, branch, goal, precondition, mutation, tick, and normalized provenance.
- An issuer must be both enabled and scheduled and must hold the capability for that exact operation.
- Mixed intent types, duplicate-ID occurrence groups, and batches mixing admissible with inadmissible proposals cannot partially write.
- Branch, inference, and memory budgets are checked across the complete accepted batch.
- `MachineState.state_hash` excludes itself and `trace_head`; sealed events bind pre-state, post-state, and the prior event hash.
- `TraceFabric` validates append order and hashes but cannot authorize mutation.
- `EXTERNAL_ACTION` and `PROTECTED_PATCH` have no transition authority.

## Implemented semantic path

1. Normalize and validate entities, predicates, facts, rules, candidates, resolvers, budgets, local uniqueness, and the reserved candidate identifier.
2. Fork each declared candidate exactly once, then discard only the open structural root with reason `candidate expansion complete`; otherwise use `branch-main`.
3. Attempt exact-query verified episodic recall before RPM.
4. Record a decomposition reconstructed from the current branch.
5. Ask `applicable_proofs` for at most one canonical proof. Antecedent matching is iterative and capped at 4,096 match expansions per call.
6. Propagate authoritative support iteratively from asserted evidence and verified recall/RPM roots. Hypothetical-only paths do not authorize commitment; asserted roots are not overwritten, and alternate paths remain eligible until support is authoritative.
7. Record explicit polarity contradictions without explosive inference.
8. Resolve each sequential missing prerequisite through a declared RPM frame. The parent is suspended, the branch identity is fixed, and successful inference cost stops at the target-producing proof prefix. A truncated closure is budget exhaustion, not a false failure.
9. Record a fresh decomposition, reconstruct each branch's status, and seal one full-coverage shared-frame comparison.
10. Select at most one admissible winner, recompute seven gates, and commit exactly the authoritative query proposition.
11. Write at most one exact trace/state/proof-bound episode. The run-local `learning_queue` prevents a second write; a later run clears the queue while same-instance memory persists.
12. Accept only a reconstructed terminal disposition. If the reserved final HALT tick contains a missing, malformed, invalid, or rejected HALT batch, the coordinator seals `FAULT` through its fail-safe.

## Bounded proof and RPM details

- `has_authoritative_support` is an iterative dependency traversal, not recursive proof walking.
- Asserted propositions are authoritative roots. Verified exact recall and verified RPM child results are also trusted runtime roots.
- Ordinary proof conclusions require every recorded premise key to be authoritative.
- `decompose_query` resolves the query only through authoritative support and selects a canonical authoritative proof path.
- `applicable_proofs` returns at most one canonical proof per call and stops after the fixed match-expansion budget.
- RPM frames bind child goal, parent goal, branch, target, return address, depth, and optional opaque Foundation reference.
- `RETURN_RPM` failure can only reconstruct branch-qualified `NEEDS_INFORMATION` with the exact declared-target failure detail.
- `target_foundation` is opaque `OPEN-SEMANTICS`; it does not implement Desire/Wisdom/Power.

## One-shot and closed-state rules

- Comparison, winner selection, decision commitment, and episodic write are one-shot transitions.
- The only permitted discard before comparison is the exact structural-root candidate-expansion transition.
- A selected or committed branch cannot be discarded or reopened.
- RPM cannot mutate a closed branch and cannot allow parent inference while a child frame is active.
- Components cannot self-certify `FAULT`, `LOOP_LIMIT_REACHED`, `DEADLOCK`, or `NEEDS_CAPABILITY`; `FAULT` is coordinator fail-safe output only.

## Contracts and schemas

`AUTHORITY_MANIFEST.yaml` freezes core identifiers and claim limits and binds the exact in-homebase `cas_reasoner.txt` snapshot. The seven required Phase 0 artifact names now exist; their ontology and adapter contracts keep unresolved semantics explicitly open, so artifact presence does not close the phase. `spec/` describes the current bounded runtime. Twenty-eight `schemas/*.schema.json` files describe packet, retained-artifact, conversation, and CAS-Math JSON shapes, including a trace-safe proposed-intent envelope distinct from accepted typed-mutation conditions. The broader `cas.*` conversation contracts remain provisional and are separated from the compact `cncm.*` runtime transport by an explicit adapter boundary.

Python code additionally enforces relational invariants that portable JSON Schema cannot express directly: semantic-key uniqueness, arity/type agreement, content-derived identities, issuer scheduling, exact goal and branch binding, proof reconstruction, authoritative support, comparison coverage/frame identity, RPM parent/result identity, one-shot transitions, atomic intent partitions, and hash chains.

## Fixture and test assets

- `fixtures/*/problem.json`: eight cold-run typed inputs.
- `fixtures/conversation/*/case.json`: eight controlled-dialogue contract families covering single turns, multi-turn context, pronouns, ambiguity, clarification, correction, topic switching, and memory recall.
- `fixtures/math/*/case.json`: six CAS-Math categories; five execute exactly and one recursive-learning case is explicitly contract-only.
- `golden/expected_final_states/`: exact final-state artifacts.
- `golden/expected_traces/`: exact complete trace artifacts.
- `golden/evidence/`: exact evidence artifacts.
- `golden/expected_failures/`: summaries for non-concluding fixtures.
- `golden/math/`: deterministic retained outputs for the five executable math fixtures plus a no-output contract receipt for recursive learning.
- `golden/manifest.json`: v0.2 retained hashes and source binding for eight RRK plus six math fixtures.
- `tests/test_reasoning_behavior.py`: positive reasoning, branch, RPM, memory, budget, and normalization behavior.
- `tests/test_authority_contract.py`: negative authority, identity, proof, conflict, learning, seal, and state-hash behavior.
- `tests/test_hardening_regressions.py`: final-tick fail-safe, atomic batch, malformed trace, bounded iterative search, authoritative support, exact binding, sequential RPM, one-shot, and verifier regressions.
- `tests/test_integrity_and_schemas.py`: replay, exact bundle/evidence checks, tamper detection, packet validation, schema/ref integrity, and protected-boundary source checks.
- `tests/test_cli.py`: host-adapter exit codes and artifact verification.
- `tests/test_conversation_runtime.py`: controlled grammar, dialogue state, clarification, rejection, compiled packet execution, evidence verification, and deterministic fresh-machine re-execution parity.
- `tests/test_conversation_contracts.py`: schema-backed conversation contract and fixture invariants.
- `tests/test_math_runtime.py`: exact arithmetic, parser budgets, proof rules, receipt-chain authority, identity/alias attacks, nonlinear fail-closed behavior, counterexamples, and semantic re-execution.
- `tests/test_math_fixtures.py`: executable math fixture families and explicit contract-only learning fixture handling.
- `tests/test_browser_bridge_math.py`: browser-bridge proof/search execution, fresh same-runtime semantic re-verification, tamper rejection, and request-shape checks.

## Isolated CASformer research package

`research/CASFORMER_v0_1/` is a separate, untrained PyTorch reference package.
It implements CAS-Ohm-shaped conductance routing, local relation-ID-selected
operators, a CJT-inspired Cause/Bias/Effect gate, a causal language-model shell,
a bounded differential-conductance signed reparameterization, a passive graph
solve, contract-checked zero-authority traces, source bindings, and its own test
and completion receipts. It is not imported by `cncm`, its relation IDs are not
canonical CAS-Sem types, and its proxy quantities have no registered neural
calibration bridge. It supplies engineering mechanism evidence only—not a
trained model, language or reasoning capability, CAS-specific advantage,
replay/provenance evidence, authority, or production readiness.

## Trust boundaries

- Packet structure is verified, but packet rule truth remains an input-authority assumption.
- Local hashes provide deterministic identity and tamper evidence, not signatures, WORM anchoring, or external attestation.
- Public nonempty episodic import is forbidden; same-process replay is trusted implementation plumbing only.
- The CLI owns explicit filesystem I/O. The kernel cannot perform external actions.
- The no-touch sibling workstream is not imported and has no runtime authority in this repository.

## Appended Foundry/Board proposal

The appended CAS Foundry / Cognitive Board Studio / CADA workbench material is not represented by runtime modules here. The separate owner-only playground is a runtime interaction and inspection surface; it is not the proposed Foundry, board canvas, studio editor, collaboration service, registry, or visual ontology-authoring system. That broader material remains a follow-on proposal only.

## Appended CRQS qualification-bench proposal

The CRQS v0.1 material at source lines 10031-11171 is also not represented by runtime modules. There is no task-difficulty grader, `CAS-G` evaluator, Capability Vector scorer, evidence-tier evaluator, deployment-authority evaluator, reference-model benchmark, protected qualification suite, anti-gaming harness, failure-localization evaluator, repair engine, or qualification-bench UI. The proposal is `PROPOSED-NOT-IMPLEMENTED` / `OPEN-SPECIFICATION`; current engineering tests and goldens confer no CRQS result.

Any future implementation must first freeze its Board Ontology and Capability Specification, then connect through an explicit reviewed compiler/packet boundary. It must not be described as an existing runtime capability or silently expand the authority of this kernel.

## Appended conversational-system proposal

The narrow controlled-English facade, frozen conversation schemas/fixtures, and owner-only “Chat With This Mind” interface implement a deterministic reference slice of the appended conversational proposal. The isolated CASformer package does not connect to or augment that path. The CNCM conversation path therefore does not implement general-English understanding, Transformer augmentation, external-model fallback, tools, durable autobiographical memory, voice, multimodal input, or autonomous action. No `CONV`, CCB-L1, CCB-D1, CRQS, or chatbot qualification has been earned.

## Intentional no-touch boundary

The separately owned sibling workstream remains outside this implementation. This repository neither imports it nor grants it executable authority. Future integration must use an explicit reviewed boundary, not source copying or shared mutation authority.
