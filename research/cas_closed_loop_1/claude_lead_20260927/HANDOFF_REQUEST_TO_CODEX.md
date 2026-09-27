# CAS-CLOSED-LOOP-1: Claude lead handoff request to Codex (2026-09-27)

**Author:** Claude (lead for HELM self-improvement integration of CAS-CLOSED-LOOP-1, per the owner's
2026-09-26 assignment). **Status:** request for Codex's acknowledged source/file handoff. Nothing in this
file edits a Codex-owned file, launches a paid job, reads protected material, or touches an active HELM job.

## 1. Source identity under review

| Item | Value |
|---|---|
| Codex head reviewed | `aa6006683d9e798c85667dc0d389a604b0e99053` (`origin/codex/cas-closed-loop-1-aws-validation-20260925`) |
| Amended implementation commits | `f6253e1a` (adapter correctness amendment) and `3a4d23f0` (bootstrap transport correction) |
| Pinned native runtime commit | `8182ad52b4468f18f140837dffee0e7debcfe786` (108 manifest files, bootstrapped from local Git objects) |
| Predeclared case count | 61 (57 scientific + 4 launcher-transport), per `aws_validation/jobs/cas-cpu-v2-20260925-155020-59bae1/proposal_admission.json` |
| Claude branch | `claude/focused-mccarthy-uj45ul`, started at `aa600668`; all Claude files live under `research/cas_closed_loop_1/claude_lead_20260927/` |

The recovery branch's `SOURCE_BINDINGS.json` and `DECISIONS.md` record objects `348638c9` and `2636bbb6` as
`MISSING_FROM_LIVE_REPOSITORY`. Both objects are present on `origin` (branch `codex/cas-closed-loop-1`) and were
readable in this clone (`git cat-file -e` exit 0, recorded in every run's `record.json`). The note describes Codex's
local partial clone, not the remote.

## 2. What Claude executed (local, public, CPU, no cloud, no model)

Runner: `run_local_protocol.py` in this directory. It mirrors `aws_validation/worker.py` after the offline package
install: Git preflight, `check_artifacts.py --git-ref`, `bootstrap_runtime.py`, `run_closed_loop.py check`,
`check_artifacts.py`, the four predeclared test files with a junit report, the retained-evidence replay, a fresh
witness, and a fresh-process replay. Every command, exit code, duration and stdout hash is in `run_*/record.json`.

| Run | Tree | Result |
|---|---|---|
| `run_20260927T045459Z` | exact `aa600668`, before boto3 was installed | 61 collected; **5 failed** (3 `NameError`, 2 `ModuleNotFoundError: boto3`), 56 passed, 73.5 s; stopped at the test gate |
| `run_20260927T045944Z` | exact `aa600668`, pinned boto3/botocore 1.43.87 installed | 61 collected; **3 failed** (`NameError`), 58 passed, 70.2 s; stopped at the test gate |
| `run_20260927T050137Z_patched_worktree` | `aa600668` plus the one-line test import below, in a detached scratch worktree | **61 passed**, 0 failed, 0 errors, 0 skipped, 103.5 s; retained replay, witness and fresh-process replay all passed |

Environment: Python 3.11.15 on Linux, pytest 9.0.2, pydantic 2.12.5, pydantic_core 2.41.5, boto3/botocore 1.43.87.
The AWS worker pins Python 3.12; that venue remains the acceptance venue. These runs are local engineering
checks only. They do not establish `CAS_AWS_ENGINEERING_VALIDATED`.

## 3. The defect found (first current acceptance gap)

`research/cas_closed_loop_1/test_native_step_adapter.py` lines 138 and 285 use `TerminalStatus` at module scope.
The only import of that name is local to an earlier test function (line 102). Both uses were added by `f6253e1a`.
The three affected cases are exactly the new regression cases for two of the three DeepSeek CHANGES_REQUIRED items:

- `test_no_frame_has_no_return_identity_before_during_and_after_root_call` (item 1, no-frame return identity)
- `test_work_join_refuses_records_removed_from_trace_bound_state[False]` and `[True]` (item 3, state-bound work join)

Consequence for the AWS lane: `worker.py` requires `{"tests": 61, "failures": 0, "errors": 0, "skipped": 0}` and
raises `PREDECLARED_TEST_COUNTS_REQUIRED_WITHOUT_SKIPS` otherwise. The frozen proposal `cas-cpu-v2-20260925-155020-59bae1`
(freeze `fab6734e…`, source `3a4d23f0`) would therefore fail at the test gate even with the transport fix working,
and even after a successful bootstrap. The freeze cannot pass as cut.

## 4. The checked repair (proposed, not applied to Codex's file)

`PROPOSED_PATCH_test_native_step_adapter_import.diff` (sha256 `d88c14c9381ff86260023426ce7b1f4bcd1896a401eb1f5e2f125882ce411aeb`)
adds one module-level line after `from cncm.compound_model import create_problem`:

```python
from cncm.model import TerminalStatus
```

Patched file sha256: `2a913d56f8d968f47b6b41bdd8b5176e9e6eebac5bbf265064aa80510b4b7bcb`. With it, the three cases pass
(29.1 s) and the full predeclared 61 pass (103.5 s). No adapter, control, runner, evidence or manifest byte changes.

## 5. Interfaces delivered for Codex's use

**Exact nested return.** `native_step_adapter.runtime_location(machine)` is the read-only location record. In the
fresh witness (`run_20260927T050137Z_patched_worktree/witness/events.jsonl`, summarized in `NESTED_RETURN_TRACE.json`)
the frame stack goes 0 → 1 (`COMPOUND_APPLY`) → 2 (`COMPOUND_CONSTRUCT`) → 1 → 0 across receipts 2–9; every live
frame carries the eleven `RETURN_IDENTITY_FIELDS`; `return_identity` is `null` and `frame_identities` is `[]` in all
five receipts with no frame (before, during ordinary root work, and after all checked returns). Each identity's
`source_snapshot` and `bias_version_at_suspension` are the unique authorized suspension event's pre-state hash.

**Measurement.** Each `execute_grant` receipt separates `I_predicted` (exact compiler design flow, value 1),
`I_allocated` (0 or 1), `I_executed` (CPython call-event count for the pinned `CompoundMachine.advance` code),
`I_attempted`, `charged_native_policy_units` (reservations) and `actual_primitive_work` (event-bound executor
reports with `catalog_state_binding`). Witness totals: 12 host entries, 18 native events, 19,030 primitive
instructions, 1,693 original checks, 32 linear checks, one record without counters (`JOINED_PARTIAL` on receipt 0).

**Replay.** `run_closed_loop.py replay --directory <dir> --expected-bundle-digest <caller-retained>`:
- retained evidence: `EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT`, 18 events, journal digest `6e6ecaf1e7c4…`;
- fresh witness bundle digest `8048bba869c47c00a8f9e306f727accfb146533f654eb02210eb8e7d038971ee`, fresh-process
  replay `EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT`, final state hash `ccb3e99a3323…`, journal digest identical to the
  historical evidence (the native journal is deterministic; receipts differ only in wall-clock fields).

Commands, from the repository root, after `python research/cas_closed_loop_1/bootstrap_runtime.py`:

```text
python research/cas_closed_loop_1/claude_lead_20260927/run_local_protocol.py
python research/cas_closed_loop_1/run_closed_loop.py replay --directory research/cas_closed_loop_1/claude_lead_20260927/run_20260927T050137Z_patched_worktree/witness --expected-bundle-digest 8048bba869c47c00a8f9e306f727accfb146533f654eb02210eb8e7d038971ee
```

## 6. What Claude asks Codex to acknowledge (no Codex file is edited until this lands)

- **R1.** Acknowledge handoff of `research/cas_closed_loop_1/test_native_step_adapter.py` for the one-line import
  repair in section 4, or apply the identical line yourself on your branch. Either way, the resulting commit is the
  new source to freeze.
- **R2.** Re-cut the Lane A v2 freeze at that new commit (`package.py --freeze --source NEW_SHA --expected-tests 61 …`).
  The existing freeze `fab6734e…` binds the bytes of `3a4d23f0`, which cannot pass the worker's test gate.
- **R3.** Amend `SOURCE_BINDINGS.json` / `DECISIONS.md` so `missing_from_live_repository` says the objects were absent
  from Codex's local partial clone and are present on `origin`, or keep the wording and add that note.
- **R4.** Confirm the witness expectations in `worker.py` stay `output 3`, `host_entries 12`, `native_events 18`; the
  patched run reproduced all three.
- **R5.** Keep the Lane A launch decision with the owner as recorded in `proposal_admission.json`
  (`execute_authorized: false`). Claude did not launch, reserve, or price any cloud work.

## 7. Boundaries

No AWS operation, no model call, no `pilot`, no protected file read, no edit to any file outside
`research/cas_closed_loop_1/claude_lead_20260927/` and the lineage `CHANGELOG.md`, no change to HELM sources, jobs,
receipts or custody. The scratch worktree used for the patched run is outside the repository tree and is removed
after the run; its `record.json` shows the modified test file as the only tracked change.

## 8. Worker A3 review of the three DeepSeek items (bounded, read-only; report in `A3_adapter_review.md`)

Verdict from the worker: `CHANGES_REQUIRED`. All three items are implemented at `aa600668` and match
`HARNESS_SPEC.md` and `CONTRACTS.json` on inspection against the pinned runtime. Two findings need Codex:

**F1 (MAJOR, confirmed).** The `NameError` of section 3: the amendment's own regression cases for items 1 and 3 cannot
execute, so the state-bound work-join rule (`test_work_join_refuses_records_removed_from_trace_bound_state`) has no
executable coverage at the head. Repair: section 4.

**F2 (MAJOR, confirmed against the real adapter; trust-model dependent).** The host-entry meter uses `sys.setprofile`,
which hooks only the calling thread. The in-scope test
`test_internal_reentry_that_clears_meter_never_publishes_a_count` already treats an in-memory monkeypatch of
`CompoundMachine._execute` as a fair attacker and expects invalidation. The same attacker, running its second
`advance` on a new thread, is neither counted nor refused. Claude's probe `probe_threaded_reentry.py`, run in the
scratch worktree against the unmodified adapter (`probe_threaded_reentry_result.txt`), returned a receipt with
`I_executed = 1` while `native_event_count = 2` and the native trace grew by two events; `verify_receipt` passed.
Under the `HARNESS_SPEC.md` sentence "the adapter is a trusted host boundary, not an isolation boundary against
arbitrary Python code that changes interpreter hooks or mutates native objects", this could be ruled out of scope;
but the existing re-entry test contradicts that exclusion for exactly this attacker class, so the specification and
the tests disagree. Options for Codex, in preference order:
1. Harden: install the meter with `threading.setprofile(entry_meter)` for the window as well as `sys.setprofile`,
   and refuse the observation if `threading.active_count()` differs before and after the native call; add a
   regression test shaped like the probe.
2. Narrow: state in `HARNESS_SPEC.md` and `CONTRACTS.json` that the count covers same-thread entries only, and keep
   the existing test as the documented boundary.

**MINOR.** `native_step_adapter.py` line 169 rebinds `observed` (the validated native result from line 142) to a
list of report bodies inside the loop. Harmless today; fragile.

**NOTES.** A `sys.getprofile() is not entry_meter` check in the `finally` would also catch hook-clearing re-entry.
`I_attempted` is not constrained by `verify_receipt`. `catalog_state_binding` has no consumer yet. The branch at line
320 is unreachable. No Python 3.11 versus 3.12 divergence was found for the relied-upon interpreter semantics
(hook exception clears the profile and propagates; `f_locals['self']` at `call`; bound-method identity).

- **R6.** Decide F2 (harden or narrow) on your branch; Claude will re-run the probe and the 61 cases on the result.

## 9. Worker A2 acceptance map (bounded, read-only; report in `A2_acceptance_audit.md`)

Strict first gap AT03; first demonstrable defect AT05/AT15/AT27 (the `NameError`); case count 61 confirmed
statically; details in `ACCEPTANCE_GAP.md`. Two items need Codex beyond F1 and F2:

**F3 (gap, not a defect).** The return-address addendum's ten adapter-level cases (`RETURN_ADDRESS_TEST_MAP.json`,
`new_adapter_case_needed`) are absent from the 61-case suite because `runtime_location` still emits
`atlas_binding: None`. The nested return is exact at the runtime-identity level and is not yet bound to a
snapshot-bound atlas address. This is the next acceptance gap after the repair, under task T07 / milestone M3.

**F4 (documentation).** Historical `evidence/events.jsonl` row 0 has a non-null `return_identity` with null fields at
`frames == []`; the amended `HARNESS_SPEC.md` forbids that shape for new receipts. Bytes stay unchanged by design.

- **R7.** State on your branch whether the ten addendum cases close inside this lane (add `atlas_binding` and the
  cases under a new adapter version) or are explicitly deferred with the reason recorded in `DECISIONS.md`.
- **R8.** Add one sentence to `HARNESS_SPEC.md` or `README.md` saying the historical row-0 shape predates the
  amendment and is preserved, not accepted.

## 10. Round 2 (2026-09-27, after the ChatGPT "first CAS + SI correction round" note): what changed and what is asked

Codex had not yet acknowledged sections 6 and 8 when this round started (no new Codex commits, branches or PR
comments). Nothing below edits a Codex-owned file; every change is a new file in this directory or a diff.

**F2 corrected probe.** `probe_threaded_reentry_v2.py` replaces the first probe's flawed acceptance. It installs,
replaces or clears no interpreter hook. The patched `_execute` reads its caller frame and counts a real entry only
when that frame runs the pinned `advance` code on this machine, per (thread, frame). Two native events are not used
as proof. The only pass is a refused window with no receipt. Against the unmodified adapter it recorded two direct
entries on two threads, the foreign call returned normally, and a verifying receipt with `I_executed = 1` came back
(`probe_threaded_reentry_v2_result_unmodified.txt`). Resolution against the supported threat model: `HARNESS_SPEC.md`
excludes hook changes; the probe makes none, and the attacker class equals the adapter's own in-scope test. The
finding stands as MAJOR.

**F2 prototype hardening (proposed, scratch only).** `PROPOSED_PATCH_native_step_adapter_thread_meter.diff` adds
`threading.setprofile(entry_meter)` for threads started inside the window, refuses a busy thread-level hook, treats any
Python activity on a foreign thread inside the window as invalidating, refuses an `advance` entry from a foreign
thread before it executes, and verifies after the call that the hook is still the meter (a cleared or replaced hook
invalidates the window). With it, the corrected probe is refused with `HOST_ENTRY_METER_INVALIDATED` and the full 61
still pass (`probe_threaded_reentry_v2_result_hardened.txt`, 118.6 s). Residual, stated: a thread that already existed
before the window is not hooked by `threading.setprofile`; Python 3.12's `threading.setprofile_all_threads` could
cover it and was left out to keep 3.11 and 3.12 behavior identical. If Codex adopts the probe as a regression case,
the predeclared count changes and the freeze must be re-cut.

**F3 snapshot-bound atlas addresses.** `atlas_address.py` builds an exact address for a live frame from existing
identities only (run, `branch-main`, root goal and call occurrence, the unique authorized push event, the frame with
its content digest, and the atlas's `state-<hash>` and `frame-<frame_id>` nodes with their tick-bound contexts), and
resolves it against a rendered view with exact matching and named refusals. It has no resume, dispatch or commit
path and never reads profile coordinates or focus. The addendum's ten cases are executable in `test_atlas_address.py`:
10 passed locally (`RETURN_ADDRESS_CASE_MAP.md`). Recorded fact from row 6: the runtime is deterministic, so a machine
started from byte-identical inputs has the identical run id and frame identities; that is one episode identity, not
two callers.

**DeepSeek reconciliation input.** `CASE_RECONCILIATION.md` / `.json` list all 61 collected case identities per run
with outcomes, commands, environment and source hashes. Claude never observed a 52-passed result.

- **R1 (unchanged, first).** Acknowledge handoff of `test_native_step_adapter.py` for the one-line import, or apply it.
- **R6 (updated).** Adopt the thread-meter diff, or narrow `HARNESS_SPEC.md` and `CONTRACTS.json` to same-thread
  entries and keep the corrected probe as the documented boundary case.
- **R7 (updated).** Wire `runtime_location`'s `atlas_binding` to `atlas_address.address_for_frame` (or import the
  module) under a new adapter version, and carry the ten cases into the re-cut freeze; or record a deferral in
  `DECISIONS.md`.
- **R9 (new).** Name the channel Claude can reach: this PR's review threads, a file under
  `research/cas_closed_loop_1/`, or a branch. Claude cannot read the agent bus.

## Round 4 additions (2026-09-27, owner's two-track follow-through)

- **R10 — joint run route.** Please cut the freeze (or joint freeze schema) for the seven-file joint command at CAS
  `7bbf1e0f…` + SI `d7808d59…` and declare the collected count in the admitted venue. `worker.py` line 123 hardcodes
  the four CAS files; the joint command needs your worker/freeze variant. Claude's package:
  `A5_ACCEPTANCE_PACKAGE_20260927.{md,json}`.
- **R11 — stale frozen concurrency identity (would block).** `launch.py` lines 103-108 and `package.py` lines
  213-216 permit only `i-0adf52b7fa801e08b` / job `cas-meta2-tpntr-20260925151836-b981625f-m-20260918`. With the
  seed-19 continuation on another instance, the all-regions check (`launch.py` 217-221) raises
  `UNDECLARED_ACTIVE_INSTANCE_CONCURRENCY_BLOCK`. Please re-declare the currently permitted instance in the new freeze.
  Read from the code, not executed.
- **R12 — seed-18 experimental file scope.** Please name the path under your records tree for the two continuation
  arms and their admissions (proposal: `records/typed_pointer_001/seed18_continuation_20260927/{armA_unchanged,armB_lr0.001}/`).
  Claude writes nothing there. Preregistration: `A4_SEED18_COMPARISON_PREREG_20260927.md`, `A4_SEED18_CONDITIONS.json`.
- **R13 — pass-20 main-course state identity.** Which receipt file holds cursor `2940` before the 16 interference and
  2 replay steps: `final.pt` (`5a8a3069…`), `prelast.pt` (`8e16f36c…`) or another? Both arms copy that one file.
- **R14 — continuation seam.** On the exact `c45f775f` bytes, please confirm that `restore_checkpoint` takes
  `optimizer_config` and `limits` from checkpoint metadata (archived-copy lines 2140-2141) and that
  `TYPED_CHECKPOINT_CURSOR` bounds the cursor by `limits["max_updates"]` (`2956` in the pass-10 metadata). If so, both
  seed-18 arms reuse your seed-19 continuation seam unchanged for arm A; please share its identity once cut.
- **R15 — growth.** CAS-side requirements for C3 are in `A4_GROWTH_CAS_REQUIREMENTS_20260927.md`; Claude writes the
  matching lane test identities only under a new packet request naming the growth file scope and boundary schema.
