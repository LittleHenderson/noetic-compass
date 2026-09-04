# Codex Gap Analysis

> Historical v0.1 analysis. For the current 14,616-line authority source,
> 31-system status, CAS-Math implementation, and complete-machine append, use
> `docs/CNCM_COMPLETE_REQUIREMENT_LEDGER.md`. This file remains useful for the
> original RRK-kernel details but is not the current exhaustive gap ledger.

## Executive finding

The strongest honest v0.1 claim is a bounded, deterministic, authority-mediated symbolic reasoning demonstrator. It can prove small typed Horn queries, distinguish authoritative support from hypothetical paths, preserve branch isolation, resolve declared missing prerequisites through identity-bound RPM transactions, compare declared candidates under one frozen frame, commit only through reconstructed gates, write one trace-bound episode per run, and emit replayable local artifacts with hash-chain tamper evidence.

It is not a production cognitive system, a complete CNCM, a brain model, or an AGI system. The larger ontology, native candidate generation, D/W/P semantics, compiler, authenticated persistent-memory admission, external embodiment, and general-learning claims remain open or out of scope.

## Capability-to-module/test map

| Bounded capability | Deterministic implementation | Evidence |
|---|---|---|
| Typed world declaration | `model.py` declarations plus `ProblemPacket` cross-validation, uniqueness checks, and reserved `root` candidate rejection | Eight fixtures, packet-boundary negatives, and CLI validation tests. |
| Bounded open-world deduction | Iterative unification and canonical Horn matching in `semantics.py`; at most one proof returned per call and at most 4,096 match expansions | Deduction, missing-information, large-rule, and combinatorial-search regressions. |
| Authoritative support | Iterative support graph rooted in asserted evidence or verified recall/RPM results; ordinary proof support propagates only through authoritative premises | Hypothetical-path, alternate-proof, asserted-root, and deep-chain regressions. |
| Explicit transitivity | Structural packet validation plus exact proof reconstruction | `transitive_reasoning`. |
| `^6`-like decomposition | `decompose_query` plus exact kernel reconstruction of the current branch state and canonical authoritative path | Decomposition and stale-classification/comparison regressions. |
| Contradiction without explosion | Opposite-polarity detector and commitment block | `contradiction` and contradiction-commit negatives. |
| Candidate branch isolation | Exact declared forks, reserved structural root, one exact root discard, and immutable branch replacement | `branch_rollback`, fork-binding, discard, and resurrection regressions. |
| Shared-frame comparison | Complete branch set, frozen frame hash, six metrics, lexical tie-break, and exact report reconstruction | Comparison coverage/classification/forgery regressions. |
| Bounded RPM return | Declared resolver, exact stack/frame/branch/result identity, suspended parent, sequential prerequisites, and target-prefix inference cost | RPM success/failure, sequential-prerequisite, closure-budget, and cross-branch regressions. |
| Decision latch | One-shot comparison, selection, commit, and seven independently recomputed gates | Concluding fixtures and one-shot/forgery regressions. |
| Episodic learning/recall | Exact-query verified recall; one state/trace/proof-bound write per run; same-instance persistence | Warm-memory, exact-recall, duplicate-write, and public-import regressions. |
| Sole-writer authority | Enabled-and-scheduled issuer checks, operation-bound capabilities, exact scope/goal binding, atomic batch rejection, and final-tick fail-safe | Authority-contract and hardening suites. |
| Deterministic evidence | String-key canonical JSON, sealed event chain, exact evidence projection, digest bindings, and replay | Replay, tamper, malformed-proposal, bundle-shape, and golden tests. |
| Host usability | API plus explicit CLI adapter | CLI test suite and `demo`. |

## Implemented but narrower than the charter

### Noetics

- `^6` is a deterministic query decomposition record.
- `^9` is represented by reconstructed proof conclusions.
- `^8` has a frozen non-deductive meaning but no runtime generator; all candidates are supplied by the packet.
- `^0`-`^5` and `^7` are not executable and remain `OPEN-SEMANTICS`.
- No noetic/domain/drive/register coordinates are carried on runtime instructions.

### Authoritative proof semantics

Hypothetical propositions may participate in an attempted proof path, but they are not authoritative roots and cannot authorize commitment. An ordinary derived conclusion becomes authoritative only when every premise in its verified support path is authoritative. Asserted roots are preserved. If the first proof of a conclusion is hypothetical, canonical alternate proofs remain eligible until an authoritative path exists; final decomposition then selects a canonical authoritative path. Support traversal and antecedent matching are iterative, so deep proof chains do not depend on Python recursion.

This is still a small Horn fragment. It does not supply defeasible logic, probability, quantified theorem proving, paraconsistent consequence beyond the explicit commit block, or externally validated truth.

### RPM

RPM is a stack-safe missing-premise resolver over declared child facts and rules. A push binds the exact child goal, parent goal, branch, expected target, return address, depth, and Foundation reference. The parent is suspended while the frame is active, and a closed branch cannot be mutated through RPM. The engine attempts sequential missing prerequisites. A successful child charges only the proof prefix needed to first establish the declared target; truncated closure is budget exhaustion, not a false resolver failure. The only accepted failure return is branch-qualified `NEEDS_INFORMATION` with the exact reconstructed failure detail.

This is not arbitrary recursive cognition and contains no D/W/P sufficiency semantics.

### Global workspace and memory

The global workspace is a typed shared record for problem/query, recalled episode IDs, comparisons, conclusion, lacunae, and diagnostics. It is not a broadcast attention model. Working memory contains supplied facts; branch propositions carry most episode-local reasoning.

Recall is exact-query-only. A successful `WRITE_EPISODE` stores its episode ID in the run-local `learning_queue`; any later write in the same run is rejected as `DUPLICATE_ID`. A new run clears that queue while retaining verified episodes held by the same `CognitiveMachine` instance.

Public nonempty episodic import is prohibited. Engine replay supplies the exact snapshot retained by its `RunResult` to `_from_trusted_snapshot`; the private method itself trusts arbitrary same-process caller input and does not verify origin. It is an implementation boundary, not authentication, cryptographic ownership, or a security control.

### Atomic authority and terminal behavior

Intent identity includes normalized provenance, and intent payloads are deep immutable snapshots. The issuer must be both enabled and scheduled and must hold the capability for the exact operation. The kernel binds goal, branch, scope, frame, and embedded payload identities before mutation.

Duplicate intent-ID occurrence groups reject as a unit. Mixed intent types conflict, and a batch containing both admissible and inadmissible proposals is rejected atomically. Branch, inference, and memory budgets are enforced across the whole accepted batch. Malformed raw proposals are replaced with schema-safe trace surrogates and rejected without escaping the trace contract.

Components cannot request `FAULT`, `LOOP_LIMIT_REACHED`, `DEADLOCK`, or `NEEDS_CAPABILITY` as an accepted terminal disposition. `FAULT` is reserved for the coordinator's final-tick fail-safe when the required single HALT proposal is missing, malformed, invalid, or rejected.

### P/C/E/O and Drives

Boot installs `P/C/E = GOOD`, `O = ENABLED`, and all Drive rails `AVAILABLE` as structural constants. There is no substantive evaluation, power-sequence state machine, Drive arbitration, or empirical validation. These fields cannot establish proof truth.

## Correctness and product gaps that block a stronger claim

### G-001 — Authenticated durable episodic restore is absent (high)

Public machine, boot, and host API paths reject nonempty external memory. This closes direct injection but leaves no durable restart/restore path. A later version needs authenticated records or store receipts, policy binding, validation, and explicit admission semantics; `verified=True` alone must never become a credential.

### G-002 — Rule authority is packet-local (high)

Rules require strict structure and provenance strings, and proof intents reconstruct exactly, but there is no signed rule registry or independent verified-rule status. A trusted packet author can supply a structurally valid false rule. Evidence proves execution relative to that packet, not real-world truth.

### G-003 — Warm replay receipt is not self-contained (medium)

`RunResult` retains exact initial episodic memory in process, and private replay uses it correctly. `RunResult.to_dict()` omits that snapshot. A retained warm bundle can be integrity-verified, but it cannot independently recreate the same run without the external initial snapshot.

### G-004 — Recall policy is semantic-key-only (medium)

Exact recall matches the query proposition's semantic key. It does not require the same problem ID, goal ID, ontology version, or source policy. This permits intended cross-problem reuse but is too permissive for an untrusted durable memory system.

### G-005 — JSON Schema is not the runtime gate (medium)

The dependency-free parser and kernel enforce strict keys and substantial relational invariants. They do not load the Draft 2020-12 documents during execution. Schema/Python drift therefore requires conformance tests, and third-party metaschema validation is not pinned in project dependencies.

### G-006 — Bundle verification does not re-execute semantics (medium)

`verify_bundle` is fail-total and exact about bundle keys, state/event hashes, event chains, intent partitions, summary projection, evidence projection, and cross-artifact bindings. It does not rerun proof, comparison, RPM, or commitment semantics because the serialized bundle omits the full problem packet. Replay with the original packet and exact initial snapshot is the stronger semantic check.

### G-007 — No durable runtime or crash model (medium)

Episodic state is in memory. The CLI writes artifacts but does not provide atomic databases, locks, migrations, WORM storage, restart recovery, access control, or key management. Local SHA-256 bindings are tamper evidence, not signatures or independent anchoring.

### G-008 — Coverage is broad but not exhaustive (medium)

The suites cover the main positive paths and many authority, budget, identity, batch, replay, and malformed-input attacks. They do not exhaust every enum combination, nested RPM history, property-based input family, platform, resource limit, or adversarial encoding.

### G-009 — CRQS qualification semantics and evaluator are absent (high)

The CRQS v0.1 appendix proposes `D0`-`D10`, `CAS-G`, Capability Vector (`CV`), `E-Tier`, `A-Level`, Reference Model Benchmark (`RMB`), cumulative hard gates, protected tests, causal ablations, a qualification bench, and repair recommendations. None has a runtime or evaluator implementation here. The proposal does not yet supply frozen machine-readable task/report schemas, calibrated operational definitions, protected-suite custody, evaluator independence, benchmark equivalence rules, or statistical acceptance criteria.

Current tests and goldens establish only engineering conformance to the bounded v0.1 runtime contract. They are not CRQS qualification inputs and confer no difficulty grade, native-generation level, vector score, evidence tier, deployment-authority level, or model-equivalence result. A topology or passing trace cannot award itself a grade.

## Explicit OPEN-SEMANTICS

The runtime must not invent behavior for:

- meanings of the seven TKS Foundations `TF1`-`TF7`;
- meanings of the 28 Sub-Foundations `TF1a`-`TF7d`;
- the Foundation-to-Drive adapter;
- Desire/Wisdom/Power definitions or sufficiency;
- Noetics `^0`-`^5` and `^7`;
- register-transfer semantics for `T/A/f/E`;
- substantive `P/C/E/O` goodness criteria;
- CAS-Ohm authority or causal meaning.

`target_foundation` is only an opaque Foundation reference. It does not encode D/W/P or authorize a semantic interpretation.

## Appended Foundry/Board proposal

The appended CAS Foundry / Cognitive Board Studio / CADA workbench material is a follow-on product proposal. This repository does implement a bounded browser playground for controlled chat, the Problem Lab, Exact Math, and live runtime/status inspection. That playground is not the proposed Foundry: there is no board canvas, studio editor, collaboration service, registry, visual ontology authoring environment, or related product workflow. The playground grants those proposed concepts no runtime authority and is not evidence that the Foundry has been delivered.

Before that follow-on is built, its Board Ontology and Capability Specification must be frozen separately and mapped through a reviewed compiler/packet boundary. It must not silently change the v0.1 kernel contract.

## Appended CRQS qualification-bench proposal

The subsequent CRQS v0.1 material at source lines 10031-11171 is `PROPOSED-NOT-IMPLEMENTED` and `OPEN-SPECIFICATION`. It describes a valuable qualification framework, but it does not change the implemented runtime and is not evidence that any proposed qualification feature exists.

Its result dimensions must remain orthogonal:

- **Capability** describes behavior demonstrated under a frozen task contract.
- **Evidence maturity** describes how strongly and independently that capability claim is supported.
- **Deployment authority** describes what action a separately governed policy permits.

A high result on one dimension cannot create another. `CAS-G` cannot grant `A-Level`; an `E-Tier` cannot prove broader capability than the evaluated task set; and an authority grant cannot validate a reasoning claim. `RMB` must remain separate from native CAS qualification and requires matched inputs, tools, budgets, memory, randomness, and scoring. A future repair engine may identify the first failing stage and suggest the smallest change, but that advice cannot authorize `PROTECTED_PATCH`, promotion, or external action.

Before any CRQS implementation or grade claim, freeze the proposed standard as a separate versioned contract with task/report schemas, difficulty-band and hard-floor precedence, Capability Vector measurement definitions, cumulative gate rules, evidence-tier prerequisites, held-out/protected evaluation, contamination controls, causal-ablation rules, evaluator immutability, authority-policy bindings, repair ontology, and negative conformance cases.

## Other out-of-scope work

General/raw-English and CCDL compilation, native association/candidate generation, neural models, embeddings, perception, external tools/actions, autonomous goals, online semantic/procedural/constitutional learning, self-modification, distributed execution, concurrency, probabilistic reasoning, general causality, production persistence, security certification, and AGI/consciousness claims remain out of scope for the v0.1 CNCM kernel. The isolated, untrained `research/CASFORMER_v0_1/` package is a research reference only; it is not integrated into that kernel and does not change these exclusions. The implemented controlled-English facade is a bounded deterministic adapter, not an exception to those broader exclusions.

## Honest acceptance statement

If the complete test suite and golden verification pass, v0.1 demonstrates a deterministic reference path from a strict typed packet to a trace-bound symbolic disposition. It does not demonstrate that packet rules are externally true, that open ontology meanings have been solved, that the proposed Foundry/Board product or CRQS qualification bench exists, that any CRQS grade has been earned, or that the machine has general cognition.
