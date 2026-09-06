# B/R comparison: required state outside the database

This is source-backed preparation, not a native restoration result. It supplements
the retained `BR_PROTOCOL.md` without changing the frozen prefix diagnostic or
its existing $4 approval request. No GPU or training job is included here.

## New finding: the database is not the complete caller

The native SQLite database holds the network state, model/tensor artifacts,
published Effects, receipts and native traces. It does not hold the outer
program's live caller stack or its remaining allowance.

META-0's `Executor` holds frames and events in memory and saves them to a separate
`cas-meta-checkpoint/0.1` JSON file. `checkpoint()` validates evidence and binds
that file to the native head. `restore()` requires the expected file digest,
program, chain identity, permissions and limits. A native database copy alone
does not restore that executor.

META-2's `CompositionExecutor` also holds its frames and spent allowance in
memory. This inspected version has no checkpoint/restore API. Pausing a full
scaffold immediately before CALL, then copying `native.db`, would lose that
parent frame and its remaining allowance. It must not be described as a resumed
full scaffold.

This does not reopen the accepted META-0 restart audit. It identifies a
construction boundary for this new B/R component comparison.

## Construction rule for the later AWS check

The narrow component construction can finish the declared ordinary prelude
through direct native calls, retain its real receipts, close the runtime, and
then restore each copied database into a fresh equal-budget arm adapter. Record
that no outer executor owns a suspended call. This is a component intervention,
not whole-program continuation or a completed training task.

If META-0 was used instead, require its actual `done` property to be true,
`frames` to be empty and `result_effect_id` to be present; save its separately
validated checkpoint and evidence before closure. Preserve its exact controls
and charged allowance. Do not infer completion from an empty native repair set.

If META-2 was used, finish a standalone prelude and retain the completed executor
evidence. Do not pause it at the CALL and invent a restoration capability.
Adding general caller persistence is outside this component preparation.

The four-step ordinary prelude and both input arms remain unexecuted. If either
requires an unexpected repair, retain the refusal and stop this direct
construction; do not replace it with the five-tick repair fixture silently.

## Required witness from each restored copy

After the supported `open_native(copy)` on AWS, use the existing public checks:

| Required equality or condition | Existing evidence |
|---|---|
| Complete native starting state | `coordinator.restore_and_verify()` returns head, state and ordered traces; compare their complete contents |
| No pending repair anywhere | For every CJT: empty `rpm.open_repair_ids`, null `suspended_parent_cause_id`, empty `return_addresses` |
| Same next logical tick | `store.next_tick()` |
| Same B/R inputs already available | `immutable_document("published_effects", id)`, its committed receipt, retained artifact and trace |
| Same C recurrent state and model | Full network state plus `load_artifact` for the model checkpoint and C recurrent-state reference |
| Same external controls | Source/config/topology/decoder identities, goal, route settings, C expectation `L2`, permissions and available arm limits |
| No lost caller state | Direct-native ownership record, or the completed outer-executor evidence described above |

The declared native artifact digest binds its kind, media type, encoding,
metadata, byte length and payload. It is not merely SHA-256 of payload bytes.
Record a raw-payload SHA-256 separately if needed for numerical comparison.

The model and tensor bytes are stored in SQLite's `artifacts` rows.
`load_artifact()` verifies their bound identities. Native `open()` loads the
checkpoint from that store and verifies configuration, network, decoder labels,
model identity and durable history. It still depends on the external installed
software and supplied configuration; those must be pinned too.

Both B and R input tensor shapes must fit C's unchanged saved recurrent-state
shape. The control layer rejects a mismatch. Do not reset or reshape C's state
between arms to force acceptance.

Only the chosen committed input reference changes. Compare numerical output and
decoded semantic content separately from producer/provenance differences. Both
arms need legitimate native execution; a pruned or refused choice is not a
successful context-dependent binding lesson.

## What the new copy utility can and cannot prove

`cas_meta2/br_snapshot_v8.py` is a standalone byte-copy preparation helper. Its
tests use synthetic SQLite files, not a CAS runtime. A future AWS caller must
establish valid, closed, quiescent state before invoking it.

Matching copies and absent WAL/SHM/journal files do not prove that every process
closed the source or that its native state is valid. The caller assertion stays
labelled as an assertion. The required supported restoration and full before-state
witness remain separate. No accepted runtime, repair rule or verifier is changed.

## Inspected source identities

Paths below are relative to:

`C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/..`

- `CAS_META_2_COMPOSITION/cas_meta2/executor.py`, properties at 85-98 and completed evidence at 229:
  `edeb83fd3468aaccacb871bc4561c97a78ae087bb47b9d8ad38f1a58fd7efb2a`.
- `CASFORMER_v0_3_META_LOGIC_WIP/cas_meta/executor.py`, properties at 123-135, checkpoint at 408, restore at 438:
  `4570dec76d8f204c7fccb3d54a71b917b160da072322acb609fc8730ce4fa9df`.
- `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/network_coordinator.py`, restore at 4159:
  `4820106b4499d19fd6eb1932f3efa13725c3d13e733403a3ec386d1f0399a1c2`.
- `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/persistence.py`, head at 522, model manifest at 750, state/artifact access at 1604/1609:
  `94eaf401078a248b9420f4b573b4fad02f0e30b7df9f0c84f74668b130570882`.
- `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/artifacts.py`, bound digest at 54:
  `32ec61a5aa69f6949e71450f221a6ca9fc4f460e38ca32511e5ab7b80be2f67d`.
- `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/runtime.py`, native open at 421:
  `5eda27339d0d216d5359116617c6dc8c9f99c376d6cfa6be386845b59ec00187`.
- `CAS_CJT_TRANSFORMER_v0_2/cas_cjt/control.py`, persistent-shape check at 229:
  `fee2b8386feb5ad8b27f95c916a7632d4e6d6fa5365091ec2d2ef3eeb9e46804`.
