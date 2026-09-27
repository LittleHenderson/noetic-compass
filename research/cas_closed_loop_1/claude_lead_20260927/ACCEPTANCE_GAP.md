# First current acceptance gap (2026-09-27, Claude lead)

**Head examined:** `aa6006683d9e798c85667dc0d389a604b0e99053` (Codex, `codex/cas-closed-loop-1-aws-validation-20260925`).
**Recorded status before this check:** `CONTRACTS.json` = `CORRECTNESS_AMENDMENT_PENDING_AWS_VALIDATION`;
`CHANGELOG.md` = "runtime tests remain unexecuted"; Lane A v2 job `a227f8` failed in cloud-init before any test
ran; proposal `59bae1` = `PREPARED_NOT_AUTHORIZED_FOR_RETRY`.

## The gap

The amended source's own regression cases for two of the three DeepSeek CHANGES_REQUIRED items cannot execute.
`test_native_step_adapter.py` references `TerminalStatus` at module scope on lines 138 and 285 without a
module-level import (the only import is local to the function at line 102). Introduced by `f6253e1a`. Observed
locally as 3 failures out of 61 at the exact head (`run_20260927T045944Z/pytest.xml`).

| Failing case | DeepSeek item it was written to close | Acceptance ids it serves |
|---|---|---|
| `test_no_frame_has_no_return_identity_before_during_and_after_root_call` | (1) no-frame `return_identity` null | AT03 (separate state meanings), AT15 (exact parent resume), AT25/AT26 (no fabricated address or profile) |
| `test_work_join_refuses_records_removed_from_trace_bound_state[False]` / `[True]` | (3) state-bound work join | AT04 (typed measured provenance), AT08 (residual identity), AT09 (predicted vs executed work), AT27 (tamper handling) |

Because `aws_validation/worker.py` refuses any count other than 61/0/0/0, the frozen proposal for Lane A v2 would
fail at its test gate even if the bootstrap transport correction works. The earliest executable link in the
acceptance chain (T03/T05 regression coverage → T06 AWS witness) is therefore this test file, not the launcher.

## Evidence that the gap is the only local blocker

With the one-line module-level import (`PROPOSED_PATCH_test_native_step_adapter_import.diff`) and nothing else:
61/61 pass; `check_artifacts.py --git-ref aa600668…` = `EXACT_BYTES_VERIFIED` (13 files); retained replay =
`EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT`; fresh witness = `x=3`, 12 host entries, 18 native events; fresh-process
replay = `EXACT_NATIVE_REPLAY_AND_CHECKED_EFFECT`. Run record: `run_20260927T050137Z_patched_worktree/record.json`.

## What remains open after the repair (not closable by Claude here)

- AWS Lane A v2 execution on the pinned Python 3.12 wheelhouse, with instance Git preflight, under a fresh
  Codex-owned freeze at the repaired source commit; owner decision on one corrected attempt (`execute_authorized: false`).
- Root cause of the `a227f8` cloud-init `scripts_user` failure is still unconfirmed; the regional-endpoint change is a
  prospective fix supported by an out-of-instance reproduction only (`transport_followup.json`).
- Everything M4/M5 (learned adapter, matched pilot) stays `NOT_STARTED` / refused under the current no-model scope.

## Worker A2 acceptance map

See `A2_acceptance_audit.md` / `.json` in this directory once the worker's report is attached.
