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

## Worker A2 acceptance map (bounded, read-only; full table in `A2_acceptance_audit.md` / `.json`)

Classification of the 36 acceptance ids at `aa600668`: 12 `COVERED_BY_TEST`, 15 `PARTIAL`, 1 `EVIDENCE_ONLY` (AT08,
no residual is ever computed), 8 `NOT_APPLICABLE_YET` (AT28–AT35, tasks T08–T12 not started; `pilot` refused).
Static case count matches the freeze: 30 + 22 + 5 + 4 = 61.

- **Strict first gap in dependency order: AT03** (task T02). T01's ids have a tracked execution against source
  byte-identical to the head (`a227f8/partial_git_probe.json`: `check_artifacts.py --git-ref f6253e1a` =
  `EXACT_BYTES_VERIFIED`). Every id from AT03 onward depends on the 57-case suite, which had no tracked execution
  against `f6253e1a`/`aa600668` before this directory's runs. Those runs are now tracked here; they are local, not AWS.
- **First demonstrable defect: AT05 (also AT15, AT27)**: the `NameError` above. The worker reached it independently.
- **Next gap after the repair (M3 atlas parity, T07; addendum RPA-RETURN-1):** the `RETURN_ADDRESS_TEST_MAP.json`
  on `codex/cas-closed-loop-1` names ten adapter-level cases (`new_adapter_case_needed`). Zero are present in the
  61-case suite; three have partial analogs; seven are absent. Root cause: `runtime_location` emits
  `atlas_binding: None` (`native_step_adapter.py` line 253), so no snapshot-bound atlas address exists to test. The
  exact nested return delivered here is at the runtime-identity level (eleven fields per live frame), not yet at the
  atlas-address level the addendum asks for. The five upstream native tests the map cites exist at the runtime commit
  but are not part of the frozen suite.
- **Documentary discrepancy (AT01):** `missing_from_live_repository` is contradicted in this clone; both objects
  resolve, and `2636bbb6` is the base commit of `codex/cas-closed-loop-1`.
- **Historical evidence note:** `evidence/events.jsonl` row 0 (producer `8f55cc3a`) carries a non-null
  `return_identity` with null fields while `frames == []`, which the amended `HARNESS_SPEC.md` now forbids. The
  historical bytes are intentionally unchanged; the amended rule applies to new receipts only.
- Smaller items: AT07 tests assert a bare `ValueError` without the refusal name and have no overflow or
  scale-mismatch case; AT12 has no large-drive cap case; AT17 asserts the terminal reason only as set membership.

## Round 2 status (2026-09-27, after the ChatGPT coordination note)

- **F1 import defect:** still open in Codex's file (no acknowledged handoff yet); repair checked twice (61/61).
- **F2 threaded meter:** corrected probe `probe_threaded_reentry_v2.py` proves two direct host entries on two threads
  with no hook change and gets a verifying receipt saying one (`probe_threaded_reentry_v2_result_unmodified.txt`).
  Prototype hardening `PROPOSED_PATCH_native_step_adapter_thread_meter.diff` refuses the window
  (`HOST_ENTRY_METER_INVALIDATED`) and keeps 61/61 (`probe_threaded_reentry_v2_result_hardened.txt`). Decision on
  adopting it or narrowing the specification stays with Codex.
- **F3 atlas addresses:** implemented as a Claude-owned read-only module with the addendum's ten cases executed and
  passing locally (`RETURN_ADDRESS_CASE_MAP.md`). Remaining gap: Codex wiring `runtime_location.atlas_binding` to it
  under a new adapter version, and inclusion of the cases in a re-cut freeze.
- **Next acceptance gap after these:** AWS execution of the re-cut freeze at the repaired commit (Lane A v2), owner
  decision on one corrected attempt. No new gap was found in this round.
