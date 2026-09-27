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
