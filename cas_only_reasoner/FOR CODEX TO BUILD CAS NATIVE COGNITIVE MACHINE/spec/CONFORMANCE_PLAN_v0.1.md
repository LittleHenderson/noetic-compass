# CNCM-RRK v0.1 Conformance Plan

Status: normative bounded test plan for runtime `0.1.0`

Conformance means agreement with the frozen v0.1 packet, state, intent, authority, trace, evidence, and deterministic-replay contracts. It does not mean complete CAS semantics, AGI, consciousness, formal verification, empirical validity, security certification, production readiness, or qualification under the proposed CAS Reasoning Qualification Standard (CRQS).

## 1. Required commands

From the build directory with Python 3.11 or newer:

```powershell
python -m pytest -q
python tools/verify_goldens.py
python -m cncm demo --fixtures fixtures
```

`pytest` is the behavioral and negative-contract suite. `verify_goldens.py` regenerates each fixture in memory, compares final state/trace/evidence to retained goldens, verifies every bundle, and verifies `golden/manifest.json`. `demo` proves all fixture packets can be executed by the host adapter; it is not a golden comparison.

For the browser playground:

```powershell
cd playground
npm run lint
npm run typecheck
npm run runtime:check
npm run build
```

The `prebuild` lifecycle regenerates the browser runtime and then runs the
fail-closed drift checker before the web compiler. The checker binds the 18-file
Python package, embedded bridge, eight RRK fixtures, six math fixtures, pinned
Pyodide assets, authoritative source hash, and golden-manifest hash.

Do not treat a copied count as a receipt. The exact current command output and current `golden/manifest.json` digest are authoritative for that checkout.

## 2. Schema and packet gate

Exactly these 28 Draft 2020-12 schemas must exist and parse. The first group
freezes the RRK and conversation contracts:

- `proposition.schema.json`
- `rule.schema.json`
- `problem_packet.schema.json`
- `branch_frame.schema.json`
- `rpm_frame.schema.json`
- `machine_state.schema.json`
- `intent.schema.json`
- `trace_event.schema.json`
- `evidence_packet.schema.json`
- `dialogue_act.schema.json`
- `dialogue_state.schema.json`
- `dialogue_turn.schema.json`
- `referent.schema.json`
- `response_plan.schema.json`
- `semantic_packet.schema.json`

The second group freezes the CAS-Math MVP and forward-compatible math
interfaces:

- `math_object.schema.json`
- `math_expression.schema.json`
- `math_statement.schema.json`
- `math_claim.schema.json`
- `math_rule.schema.json`
- `proof_step.schema.json`
- `theorem.schema.json`
- `conjecture.schema.json`
- `math_strategy.schema.json`
- `math_problem_packet.schema.json`
- `math_evidence_packet.schema.json`
- `math_result.schema.json`
- `math_counterexample.schema.json`

Every local `$ref` must resolve inside `schemas/`; `$id` values must be unique; every structured contract object is closed with `additionalProperties: false`. The one deliberate exception is the recursive contents of `Intent.proposed_mutation` in the trace-safe root envelope: rejected malformed typed payloads must remain representable. `intent.schema.json#/$defs/accepted_intent` supplies the closed typed-mutation profile. All fixture inputs must also pass `ProblemPacket.from_dict`, which enforces cross-object arity, typing, groundness, uniqueness-by-semantic-ID, provenance, evidence-status, range-restriction, transitivity, reserved candidate ID, and Foundation-reference rules.

The project has no runtime dependencies. Draft metaschema validation using the third-party `jsonschema` package is required when that package is available in the verification environment, but it is not evidence supplied by the dependency-free runtime itself.

## 3. Retained fixture matrix

| Fixture | Required cold-run result | Core behavior |
|---|---|---|
| `deduction` | `CONCLUDED` | Exact modus ponens proof and committed episode. |
| `transitive_reasoning` | `CONCLUDED` | Typed transitivity and exact substitution. |
| `branch_rollback` | `CONCLUDED` | Isolated candidate state; one committed winner; loser retained as discarded. |
| `contradiction` | `CONFLICT_UNRESOLVED` | Opposite polarities recorded; no commitment. |
| `missing_information` | `NEEDS_INFORMATION` | Missing premise recorded; no fabrication. |
| `rpm_recursion` | `CONCLUDED` | Exact RPM push/success return/parent resume. |
| `rpm_failure` | `NEEDS_INFORMATION` | Typed RPM failure, stack pop, blocked parent. |
| `memory_recall` | `NEEDS_INFORMATION` | Cold run has no matching initial episode. |

The warm-memory test first runs `deduction` on a persistent `CognitiveMachine`, then runs `memory_recall` on that same host. Only that exact verified episodic snapshot changes the second result to `CONCLUDED` by `RECALL`.

Public nonempty episodic injection must fail closed. The suite must distinguish the admitted same-instance learning path and private exact-`RunResult` replay path from unsupported durable import.

## 4. Reasoning assertions

Tests must show:

- modus ponens records exact premise, rule, binding, conclusion, status, branch, and provenance;
- transitivity works only for the validated structural transitive rule;
- proof identity or provenance forgery is rejected;
- the iterative matcher returns at most one canonical proof per call and fails closed at 4,096 match expansions;
- asserted roots are preserved, duplicate steps are suppressed, and alternate paths stop once authoritative support exists;
- hypothetical-only query/constraint/proof chains are excluded from authoritative support and commitment;
- missing support remains missing under the open-world rule;
- explicit contradiction blocks decision commitment;
- input collection order is normalized before hash and execution;
- hard tick/branch/inference/memory budgets and RPM prefix cost return typed, traced rejections or `BUDGET_EXHAUSTED` dispositions as specified.

## 5. Authority and identity assertions

Negative tests must prove no unauthorized state write for at least:

- scheduler decision-commit attempts;
- branch-manager episodic writes;
- external-action attempts from every issuer;
- protected-patch attempts;
- trace-fabric mutation attempts;
- stale snapshots;
- conflicting same-key intents;
- duplicate input intent-ID occurrence groups, mixed intent types, and valid/invalid atomic batch poisoning;
- recursively non-string canonical mapping keys and provenance-mismatched intent IDs;
- issuer enabled-but-not-scheduled and scheduled-but-not-enabled cases;
- wrong active goal or branch/frame envelope identity;
- missing RPM parent;
- forged RPM frame identity;
- forged comparison frame/metrics/winner;
- incomplete branch comparison, stale decomposition/classification, repeated comparison/selection/commit/write, and illegal non-root discard;
- Boolean smuggling into integer comparison metrics;
- forged rule proof identity/provenance;
- commit with unresolved contradiction;
- learning from a discarded branch;
- halt before any prior sealed event;
- component requests for `NEEDS_CAPABILITY`, `LOOP_LIMIT_REACHED`, `DEADLOCK`, or `FAULT`;
- rejected/invalid final-tick batches, which must seal fail-safe `FAULT`;
- malformed raw proposals and malformed typed mutation objects, which must remain schema-safe and trace-visible;
- public nonempty episodic imports and second per-run episode writes;
- installation of a bad state hash.

Every rejection must be trace-visible and leave the protected write unapplied. Passing this set does not prove every enum value or adversarial encoding has been exercised.

## 6. Trace, evidence, and replay assertions

For every retained run:

- event parent IDs and previous hashes form one chain;
- every event is sealed and its hash recomputes;
- every event pre/post state hash is consistent with its neighbors;
- final `trace_head` equals the last event hash;
- `trace_digest` covers the complete ordered event objects;
- evidence digest recomputes after omitting only `evidence_digest`;
- the evidence semantic projection exactly agrees with run/state identity, query/conclusion, proofs, branches, RPM events, comparison, gates, learning disposition, diagnostics, and trace;
- state, trace, and evidence tampering is detected.

Engine replay must start from `RunResult.initial_episodic_memory` and require exact final-state, trace, and evidence equality. The private underscore path is trusted same-process plumbing, not a security or ownership proof. A serialized bundle does not carry that initial snapshot, so bundle verification is structural/integrity verification, not self-contained replay of warm-memory history or external authenticity.

## 7. Golden acceptance

`python tools/verify_goldens.py` must report `valid: true` for 14 retained
fixtures: eight RRK fixtures and six CAS-Math fixtures. Five math fixtures are
exactly executable; `recursive_learning` is explicitly `CONTRACT_ONLY` and MUST
retain no fabricated runtime output or output hash. The v0.2 golden files are:

- RRK expected final state, trace, evidence, and failure summary where applicable;
- exact retained output for each executable math fixture;
- a source-bound contract-only receipt for the non-executable learning fixture;
- `golden/manifest.json` binding all 14 fixture definitions and retained artifacts.

Regeneration is acceptable only after an intentional contract/runtime change and review. A digest change is evidence of changed artifacts, not proof the change is correct.

## 8. CLI acceptance

CLI tests cover:

- `check` accepts a valid packet and returns 2 for invalid input;
- `run` writes requested trace, final-state, evidence, and bundle outputs;
- `replay` returns 0 for an exact trace and 4 for mismatch;
- `verify` returns 0 for a valid bundle and 4 for tampering;
- typed parsing/I/O errors return 2.

The CLI is a host adapter. Its explicit file writes do not expand kernel action authority.

## 9. Open conformance work

The current suite is intentionally not a completeness claim. Still open:

- third-party Draft 2020-12 metaschema validation in a pinned development environment;
- explicit tests for every terminal status, rejection enum, intent shape, and budget field;
- authenticated rule-source authority;
- general conditional-conclusion semantics beyond v0.1's authoritative-support filter;
- deeper nested RPM scheduling policy beyond the sequential declared-prerequisite driver;
- self-contained serialized warm-memory replay receipts;
- fuzz/property testing, performance bounds, concurrency (out of scope), security, persistence, and crash recovery;
- every `OPEN-SEMANTICS` ontology item.
- the proposed CAS Foundry/Cognitive Board Studio/CADA Board Ontology and Capability Specification; no web workbench is part of this conformance target.
- the proposed CRQS v0.1 task/report schemas, `D0`-`D10` grader, `CAS-G` evaluator, Capability Vector (`CV`), `E-Tier`, `A-Level`, Reference Model Benchmark (`RMB`), protected/held-out qualification suites, causal ablations, anti-gaming controls, failure localization, repair engine, and qualification-bench UI.
- executable CAS-Ohm semantic/hash validator, observer, pre-schedule `AttentionAllocationPlan`, scheduler, CJT/test-point, neural-profile, and CAS-GEM integration. The adopted protocol and stage-record schema are contract-only.

## 10. CAS-Ohm contract-only conformance

Current tests require the CAS-Ohm protocol and schema to parse, remain declared
`NOT-RUNTIME-INTEGRATED`, and hard-code `false` for truth, meaning, proof,
validity, commitment, permission, memory-occurrence/write, state-mutation,
halt, causal-identification, external-action, self-modification, and CNCM-intent
authority. The schema separates native-computational and neural-model
substrates, binds non-`UNASSESSED` semantic outcomes to CAS-Sem/verifier
evidence, and encodes CAS-GEM anchor/policy/verifier hard-gate combinations.

Before any observer implementation is admitted, positive and negative vectors
MUST pass the shape, kind/unit, exact-arithmetic, mode/profile, semantic-source,
CAS-GEM gate, and hash-chain validators. Tests MUST then prove that removing,
corrupting, or replaying the observer changes no CNCM state,
`TraceEvent`, proof, conclusion, commitment, RPM transition, halt, or episodic
write. Before any later allocator is admitted, a distinct pre-schedule plan
schema and tests MUST additionally prove exact budget conservation,
deterministic rounding and tie-breaking, fairness floors, branch ceilings,
starvation controls, neutral-profile equivalence, and hard-gate non-bypass.
Neural claims require disjoint calibration and held-out
splits, uncertainty, matched controls, retained failures, and explicit
anti-circularity checks. None of those implementation or empirical gates is
currently satisfied.

## 11. CRQS non-qualification boundary

The CRQS appendix at source lines 10031-11171 is `PROPOSED-NOT-IMPLEMENTED` and `OPEN-SPECIFICATION`. This plan contains public engineering fixtures selected to exercise the v0.1 implementation and regressions. It does not define CRQS task manifests, calibrated difficulty axes or hard floors, cumulative generation gates, Capability Vector metrics, protected fixture custody, unseen held-out splits, contamination checks, causal ablations, benchmark equivalence, evidence-tier prerequisites, deployment-authority policy, or evaluator independence.

Therefore, current conformance results and goldens are not CRQS qualification. They earn no `D0`-`D10`, `CAS-G`, `CV`, `E-Tier`, `A-Level`, or `RMB` result. Trace completeness, deterministic replay, or zero violations within this bounded suite must not be translated into those proposed grades.

A later CRQS evaluation may use a v0.1 trace or evidence packet as one input only if a separately frozen standard explicitly admits its schema and verifies its semantic and provenance requirements. Capability, evidence maturity, and deployment authority must remain separate outputs. A qualification or repair report cannot create kernel truth, mutation permission, patch authority, promotion authority, or external-action authority.

## 12. Permitted claim

When all current checks pass, the honest claim is: “the CNCM-RRK v0.1 deterministic reference demonstrator passed its retained unit, authority, integrity, CLI, fixture, and golden checks in this environment.” No stronger intelligence, qualification, evidence-maturity, deployment-authority, model-equivalence, completeness, safety, or production claim follows.
