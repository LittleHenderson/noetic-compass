# CAS-CLOSED-LOOP-1 adapter contract

This specification describes the prospective 2026-09-25 correctness amendment.
The pinned native coordinator remains the only writer of native state. The
adapter is a trusted host boundary, not an isolation boundary against arbitrary
Python code that changes interpreter hooks or mutates native objects.

## Return location

With no live acquisition frame, `return_identity` is null and
`frame_identities` is empty. This applies at genesis, during ordinary root work
and after all checked returns. The location still records the current state
hash, logical tick, root goal and root call. These fields describe current
context and do not create a suspension or grant return authority.

Each live frame has the eleven fields listed in `RETURN_IDENTITY_FIELDS`.
Its source snapshot and Bias basis come from the unique authorized suspension
event's pre-state hash. The active return identity is the top frame's identity.
Coordinates and this read-only record cannot select or resume a caller.

## Grant and observed native entry

The grant permits zero or one native host call. `I_attempted` counts the host
dispatch attempt separately. Before work, the dispatcher requires the exact
pinned bound `CompoundMachine.advance` method, including its receiver, function
identity and code object. Substituted wrappers cannot enter the native code.
The pinned implementation does not recursively enter `advance`.

The CPython call hook meters native entry and refuses an unexpected second
entry. A hook exception disables profiling, so code that catches that exception
could execute unmetered work. Any such breach invalidates the entire observation
and produces no receipt or usable count. This remains an error even if the
exception was caught. An ordinary internal native fault with an intact meter
uses the existing invalid-native-error receipt and leaves complete work unknown.

Every usable receipt must have exact integer counters satisfying
`0 <= I_executed <= I_allocated <= 1`, as well as a valid content digest.
Disabled and zero grants execute no native call. Native policy budgets remain
independent of this host-call count. These counts are not total compute or a
calibrated attention measurement.

## State-bound work join

Before reading work records, `primitive_work_for_events` obtains the validated
native result. This verifies the state content hash and its binding to the
complete sealed event chain, including profile, problem and ingress. The
catalog and event lookup both come from that exact result. A changed state,
even with a newly computed self-consistent hash, is refused if it is not the
state reached by the native trace. Empty event selections still require this
validation.

The existing catalog join then requires run, tick, intent and sealed event
identity. The report retains `catalog_state_binding` with the validated run,
state hash, trace head and logical tick. When replay checks an earlier window
against the final validated state, its catalog may contain later records;
the selected event-work rows and measured totals must still match exactly.
Historical receipts remain unchanged. Content hashes provide integrity, not
external signatures or fresh semantic authority.

## Acceptance boundary

New focused regression cases cover the three rules above. They must run on
the freshly admitted AWS Lane-A source together with existing public cases,
the checked engineering witness and fresh-process replay. AST parsing alone
is not acceptance. No current AWS validation claim is made by this document.

`HISTORICAL_PRODUCER.json` identifies the preserved original source snapshots
checked against the historical `RUN_MANIFEST.json`. That historical evidence
proves the original producer's retained bytes; it does not accept this amended
source. The fresh prospective source/package freeze binds the current code.

## Amendment 2026-09-27 (Claude, lease `CAS-CORRECTION-20260927-01`): host-entry meter across threads

The rule "any unexpected re-entry invalidates the whole observation" is now enforced for threads too. Before the
native call the dispatcher requires both `sys.getprofile()` and `threading.getprofile()` to be free. During the
window the meter is installed on the window thread and, through `threading.setprofile`, on every thread started
inside the window. Any Python call event on a thread other than the window thread invalidates the window. An entry
into the pinned `advance` from a foreign thread is refused at its call event, before its body runs. After the call
the dispatcher checks that the window thread's hook is still the meter; a cleared or replaced hook invalidates the
window. An invalidated window raises `InvalidNativeObservation("HOST_ENTRY_METER_INVALIDATED")` and produces no
receipt and no usable count.

Claim boundary, stated exactly. The tested attacker class is same-process, in-memory patching of native internals
(for example `CompoundMachine._execute`) that installs, replaces or clears no interpreter hook, on the window thread
or on a thread it starts. That is the class the two re-entry regression cases exercise. This meter is not isolation
against arbitrary Python: code that changes interpreter hooks, or a thread that already existed before the window,
is outside the tested class and outside this specification's guarantee. A hook or a thread census is not an
isolation boundary and is not claimed as one.

Evidence for this amendment: the corrected probe `claude_lead_20260927/probe_threaded_reentry_v2.py`, which counts
real entries from the patched callee's caller frame without touching hooks, produced a verifying receipt with
`I_executed = 1` after two direct entries on two threads against the previous adapter
(`probe_threaded_reentry_v2_result_unmodified.txt`), and is refused by this adapter
(`probe_threaded_reentry_v2_result_hardened.txt`). The same-file regression case is
`test_foreign_thread_entry_inside_window_never_publishes_a_count`.

## Amendment 2026-09-27 (Claude, lease `CAS-CORRECTION-20260927-01`): snapshot-bound atlas addresses

`runtime_location` now carries `atlas_binding`: one exact address per live acquisition frame, in stack order, or
`null` when no frame exists. An address is built only from identities that already exist in the pinned runtime and
the pinned atlas projection: the run, `branch-main`, the root goal and root call occurrence, the unique authorized
`PUSH_*_ACQUISITION` event that created the frame (sealed event id and hash, tick, pre- and post-state hashes), the
frame itself with its content digest, and the atlas node identities `state-<pre_state_hash>` (the snapshot the caller
waits in, with the tick-bound `AtlasContext` the projection assigns), `state-<post_state_hash>` (the first state in
which the frame exists) and `frame-<frame_id>`. `resolve_atlas_address(view, address)` checks an address against a
rendered view by exact key match and returns `RESOLVED_LIVE_FRAME` or `RESOLVED_HISTORICAL_FRAME_NOT_LIVE`, or refuses
with a named reason. There is no nearest-node fallback.

Authority, stated exactly. An address is a lookup key and a display binding. It is not a resume token: nothing in the
adapter resumes, dispatches, commits or advances from an address, and the existing coordinator remains the only
writer of native state. Profile coordinates are never an input and are refused if supplied. The view's focus,
hypothesis handle and presentation are ignored by resolution. Two callers with equal or absent profiles never merge:
distinctness comes from run, event and frame identity. A machine started from byte-identical inputs reaches the
identical run id and frame identities; that is one episode identity, not two callers. Historical receipts are
unchanged; the field is populated in new receipts only.

Executable mapping of the return-address addendum: `RETURN_ADDRESS_TEST_MAP.json` (0.2) and
`test_return_addresses.py`. Local execution by Claude is an engineering check, not AWS acceptance.

### Explicit statement of the hook-changing bypass (Claude, 2026-09-27, source-only amendment)

The existing hook-clearing regression case `test_internal_reentry_that_clears_meter_never_publishes_a_count` is
retained unchanged, and its actual outcome is unchanged: the second same-thread entry raises inside the meter, CPython
clears the window thread's profile hook, the third entry runs unmetered, and the window is invalidated with
`HOST_ENTRY_METER_INVALIDATED` because the refusal flag was already set. The post-call check that the hook is still the
meter adds a second, independent reason to invalidate that same case.

What the meter does not cover, stated as a bypass and not as coverage: code running inside the window that calls
`sys.setprofile`, `threading.setprofile` or, on Python 3.12, `threading.setprofile_all_threads` can replace or remove
the meter. If it leaves the hook removed or replaced, the post-call check invalidates the window. If it restores the
meter before the call returns, every native entry made while the meter was absent is uncounted and undetected, and a
receipt would be issued for a window in which more entries occurred than the grant allowed. A thread that already
existed before the window is likewise unmetered because `threading.setprofile` applies only to threads started
afterwards. The adapter therefore guarantees the count only for the tested attacker class named above; a caller
that changes interpreter hooks is outside the guarantee, and no isolation claim is made for it.

## Amendment 2026-09-27 (Claude, packet B1-SEED18-IMPLEMENT-02): seed-18 frozen-model interface

Interface-specific section only; no runtime, adapter, control or SI change. Exclusive scope:
`claude_lead_20260927/seed18_interfaces/*` and `test_seed18_interfaces.py`.

- A frozen learned model is exactly one checkpoint named by size and SHA-256. A digest alone never authorizes it:
  `admit_frozen_model` requires an `AdmissionBinding` naming the identity digest and an admitting authority under a
  structured reference; the interface verifies no signature and says so. It takes no host: the SI TrustedHost at
  `d7808d59` (`checkpoint=None`) is a separate contract and does not admit neural parents.
- Admission order: identity, admission, regular file and no symlink, size before any byte is read, SHA-256 before
  any load, CUDA-only device, then the CPU-dry boundary `RESTORE_DEPENDENCIES_NOT_SUPPLIED`. The restore
  (`PointerCourseLearner.restore_checkpoint(torch, framework, encoder, *, path, expected_sha256,
  expected_run_identity_digest, device, expected_learnable_names=None)`, fresh framework, frozen typed encoder) and
  `predict(packet, 8)` are GPU-dependent and unaccepted until the admitted venue runs them. The handle exposes
  `predict` only; `stage_batch`, `train_sealed_batch`, `export_checkpoint` are refusals; prediction runs on a
  separate restored clone under the venue's RNG guard.
- The original neural prediction is a separate public record (digest, size, private reference) written before
  any repair; the body never enters a public record. Public records carry exactly their permitted fields in typed
  formats with a closed provenance set; there is no free-text field, so a short body cannot hide in one.
- Repair path `NONE` preserves the prediction digest with zero native work. Repair path `CAS_CLOSED_LOOP` is not
  implemented: no operation in `control.OPERATIONS` consumes a learned prediction, and the equation witness is not
  reported as a neural repair. Parity across paths requires the same items, order, frozen model, raw digests,
  budget and evaluator, and returns totals only.
- Status: slice 1 executed locally (43 passed, commit `2022be45`, engineering check); slice 2 written, not run;
  nothing here is acceptance. Refusal codes are the closed set in `frozen_model_interface.REFUSALS`.
