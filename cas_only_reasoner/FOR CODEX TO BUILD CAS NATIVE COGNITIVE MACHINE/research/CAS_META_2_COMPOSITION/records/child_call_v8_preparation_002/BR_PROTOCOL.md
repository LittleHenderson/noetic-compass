# B/R same-state construction protocol

Status: **PROTOCOL_ONLY. Native construction, snapshot restoration on CUDA, numerical discrimination, and whole-task discrimination are UNEXECUTED.**

This is preparation for a later child-input lesson. It adds no work to the independently runnable saved-model prefix diagnostic. No model, native runtime, database, provider, reservation, or paid job was executed for this document. No accepted runtime, verifier, repair guard, or model weights were changed.

## Exact question and controls

Can the same child containing C legitimately consume either the already committed B result or the already committed R result, from two copies of the same valid state, and produce a task-relevant distinction?

Fix the observation binding, child body (`C(arg)`), child return, parent return, C expectation (`L2`), goal context, route settings, permissions, model, and available policy budget. Change only the selected committed input reference: B versus R. Both choices must remain native-allowed even when one is wrong for a particular task. Do not change an expected symbol between arms to make both appear accepted.

This intervention changes the whole committed reference: payload, semantic content, producer, provenance, and publication age. It is not a claim that tensor values alone caused the difference. B will normally be older than R; retain and report that fact.

The pure scaffold catalog remains complete before prediction: `arg`, A, B, C, and R references are in scope. The prepared enumeration has 180 tuples, including topology and returned-result rejections. Its six B/R pairs hold binding, child, and return fixed. Choosing those pairs for a construction check must not become a private-target-based inference mask. This first C-only comparison does not establish child-selection skill.

## 1. Construct both inputs through legitimate execution

Start in a new disposable AWS development directory under a separately approved, bounded GPU scope. Use the unchanged fixed native fixture and GPU transport checks. For the currently prepared scaffold, execute the declared ordinary prelude:

```text
A(arg) -> B(A_result) -> C(B_result) -> R(C_result)
```

Require each intended step to finish with an accepted, durable PublishedEffect through the existing runtime. Record the real B and R effect IDs, immutable effect documents, commit receipts, trace identities, retained tensor-artifact hashes, decoder results, and actual compute charges. Stop on a rejection or a repair state that prevents the declared prelude from completing. Never create, reseal, rename into existence, or fabricate a repair result.

The existing `fixture.run_reference` is a different five-tick path: A, B, rejected C, genuine R repair, exact resumed C. It explicitly checks repair opening and closure. It is a source-backed alternative fixture for a separately declared component check, not proof that the four-step scaffold works and not permission to substitute a different curriculum silently. Its authored rejection expectation is part of that fixture, not a task-conditioned target to vary.

Before a comparison snapshot, require **no open repair IDs or suspended caller/repair state**. Do not snapshot the accepted restart test at its fourth tick and then switch inputs: that state reserves the next tick for one exact repair resumption. Keep `repair cannot open without a durable distinct ^6 round trip` and all other native checks intact.

## 2. Make one complete saved state, then two byte-identical copies

The supported restoration entry point is `cas_meta.fixture.open_native(path)`, which calls `NeuralCJTRuntime.open`. It reloads persisted weights, verifies configuration/topology/decoder/model identities, and calls `coordinator.restore_and_verify()`. There is no native snapshot or clone API in the inspected source.

Stop all work on the new construction database and close the runtime and every other database connection. The store uses SQLite WAL mode; `close()` closes the connection but does not explicitly request a checkpoint. Therefore, copying only a live main `.db` file is not a valid snapshot procedure.

For this small protocol, accept only a closed, self-contained database with no pending WAL content or required sidecar. If this cannot be established, stop at **SNAPSHOT_NOT_SELF_CONTAINED**. A separately implemented SQLite backup/checkpoint step would need its own checks; none is implemented here. Do not use `immutable=1` to ignore a live WAL.

Hash and retain that closed master. Copy it to two new, non-linked directories; require both initial database hashes to equal the master. Never open or mutate the retained master. Restore each copy separately using `open_native`. Opening a copy is not read-only: `SQLiteAtomicStore` configures WAL and creates/verifies schema.

Before either comparison tick, require equality of:

- Full persisted network state, including the complete C BiasState, memory/readiness/governance state, model version/digest and stored checkpoint artifact.
- Store head, ordered prior traces, next tick, and retained B/R effect documents and tensor bytes.
- Topology, operation contracts, decoder manifests, route settings, available compute ceilings, and any external allowance supplied to the comparison.

Record before-state digests and actual values needed to verify these equalities. Do not infer state equality from matching weights alone. Two sequential calls on one database are not equivalent to this design.

## 3. Restore on AWS CUDA and execute one input choice per copy

A small AWS-only restoration adapter is still missing. `NativeBackend.__init__` always calls `create_native(output / "native.db")`; that is an initialization path, not the required supported restoration path for the two copied databases.

The adapter must call `open_native` on each disposable copy, then reuse the existing CUDA bridge pattern: approved CUDA device check, eval/no-gradient mode, parameter freeze, `_CudaMaterializer`, `_gpu_forward_guards`, and model-byte identity checks before and after device movement and execution. All model creation/loading/forward work belongs on AWS. This document does not implement or execute that adapter.

For each restored copy, call the actual cascade constructor:

```python
cause = restored.cause_from_effect(
    selected_effect_id,  # saved B ID in one copy; saved R ID in the other
    tick=restored.store.next_tick(),
    candidate_operation_ids=("^6",),
    goal_context=GOAL_CONTEXT,
)
```

The constructor checks the PublishedEffect digest, authoritative status, durable receipt/trace binding, and retained artifact. It has no latest-effect-only restriction, but that fact alone does not guarantee the subsequent inference tick is admissible.

Materialize and receipt the real plan, then execute C through the unchanged public native API with the same fixed expectations/settings. Preserve each refusal, first failing check, repair outcome, plan, accepted result, actual output artifact, and trace. Use equal available limits, not manually forced equal materialized plans: plans and measured charge may legitimately depend on the selected input.

Both arms must finish native execution legitimately. A wrong choice rejected before usable execution is an eliminated option, not evidence of context-sensitive input learning. An arm that unexpectedly requires repair does not pass this direct ordinary-C construction gate; report it without bypassing the guard or silently appending repair work. Rehash sources and model bytes afterward and record complete/partial status.

## 4. Separate three different claims

1. **Native availability:** both committed inputs can reach C from the equal saved state. The two arm results establish this only after actual AWS execution.
2. **Meaningful input contrast:** compare numerical tensors and decoded semantic content, not only hashes or producer IDs. If only provenance differs, label it a provenance-only contrast. Different hashes alone do not establish a task-relevant effect.
3. **Task-conditioned correctness:** public task information must determine when B is required and when R is required, under existing semantics. This varying public curriculum and its independently checked targets are **NOT BUILT**. An always-R rule or arbitrary private target alternation does not meet this gate.

The unchanged `native.verify_task` checks renaming-independent program structure, observation binding, dependency edges/return node, all stored result rows/output bytes, and trace validity against a private native reference. A B-versus-R edge difference can fail its dependency check even if tensors are numerically equal; report that narrower distinction honestly.

The same-state C-only fork is a **component construction check**, not automatically a full `verify_task` packet. The current full runner constructs a fresh complete run and the stored checker expects its complete records. Do not mislabel suffix traces as whole-task evidence, invent run counts, or feed fabricated records to the verifier. After the component check succeeds, the later curriculum must execute complete candidate and private-reference scaffold programs through the existing runner/verifier and demonstrate a public-task-relevant difference without changing the verifier.

## Required output before later training

Retain the master/copy identities, declared prelude, both actual input producer identities, before-state comparison, accepted/refused arm results, actual output comparisons, plans/charges, unchanged source/model identities, and exact failure status if any. Report B/R task-conditioned variation as unbuilt until it exists and is checked.

No training readiness, numerical discrimination, full-task success, or CAS-specific advantage follows from the pure enumeration or this protocol. The B/R construction has its own scope and approval; it must not delay or silently expand the saved-model prefix measurement.

## Inspected source identities

These are read-only source observations, not native execution receipts. Recheck them when implementing the adapter.

- [Native runner and whole-task verifier](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/native.py:66>) — NativeBackend; cause/plan transport; verify_task at 483.
  SHA-256: `16131d98dcbd76d274a1c083e9bc5f100cadfbbba7dfcdb38282c23946c20512`.

- [Pure scaffold enumeration](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/cas_meta2/child_scaffold_v8.py:135>) — 180 candidate tuples; controlled B/R pairs; no native execution.
  SHA-256: `4ca4f80dc173d3567cd7cb32a146299c4fc9b5b8e2db797a0d6612ac5aa1570b`.

- [Native fixture and restore entry point](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/fixture.py:45>) — create_native/open_native; run_reference at 85.
  SHA-256: `0038db2ed122e7d1ccb312771e0ea14388ee8564d3ffaa9a9f6c7316c6eb1735`.

- [Accepted restart test source](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CASFORMER_v0_3_META_LOGIC_WIP/tests/test_executor.py:146>) — Restores exact caller/repair state, then resumes; not run here.
  SHA-256: `887747e435256b7c2fe9006f07d44fb4ccdab659d177d939e7457a95823bf766`.

- [Native persistence restoration and repair gate](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py:421>) — open; cause_from_effect at 528; reserved repair stage at 591; inference_tick at 1231.
  SHA-256: `5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187`.

- [Committed-effect validation](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/state.py:303>) — cause_from_committed_effect: exact durable receipt, trace, artifact linkage.
  SHA-256: `5be617d5e3dc2f9590076ac07f1b0325ce9bf5465b7766315a3322f390b94240`.

- [SQLite custody and next tick](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/persistence.py:287>) — WAL initialization; close at 310; immutable_document at 1639; next_tick at 1663.
  SHA-256: `94eaf401078a248b9420f4b573b4fad02f0e30b7df9f0c84f74668b130570882`.

- [Existing CUDA transport checks](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_1_LEARNED_SELECTION/cas_meta1/execution.py:183>) — _CudaMaterializer; _gpu_forward_guards; _model_identity.
  SHA-256: `1acb999a77fd952ba12a5927461f8d99b97b4689aa3ab5696053dccb2c6d2376`.
