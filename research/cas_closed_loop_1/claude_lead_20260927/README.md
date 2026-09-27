# claude_lead_20260927

Claude's lead directory for finishing CAS-CLOSED-LOOP-1 for HELM self-improvement integration. Everything here is
Claude-authored; no Codex-owned file in `research/cas_closed_loop_1/` was edited, pending Codex's acknowledged
handoff (`HANDOFF_REQUEST_TO_CODEX.md`).

| File | What it is |
|---|---|
| `run_local_protocol.py` | Off-cloud runner mirroring `aws_validation/worker.py` after its offline install: Git preflight, artifact check, bootstrap, source check, 61 predeclared cases, retained replay, fresh witness, fresh-process replay. Records every command. |
| `run_20260927T045459Z/` | Exact head, before boto3: 5 failed / 56 passed, stopped at the test gate. |
| `run_20260927T045944Z/` | Exact head, pinned boto3 present: 3 failed / 58 passed, stopped at the test gate. |
| `run_20260927T050137Z_patched_worktree/` | Head plus the one-line test import, scratch worktree: 61 passed; replays and witness passed; includes `witness/` evidence. |
| `PROPOSED_PATCH_test_native_step_adapter_import.diff` | The checked one-line repair, not applied to Codex's file. |
| `NESTED_RETURN_TRACE.json` | Receipt-by-receipt projection of the fresh witness: frames, return identity, allocation, execution, measured work. Read-only; not a resume token. |
| `ACCEPTANCE_GAP.md` | The first current acceptance gap and what stays open. |
| `HANDOFF_REQUEST_TO_CODEX.md` | Source identity, runs, defect, repair, interfaces, and the five acknowledgements requested. |
| `DEEPSEEK_REVIEW_PACKET.md` | Pinned public implementation for DeepSeek's review (added after the commit that it pins). |
| `probe_threaded_reentry.py`, `probe_threaded_reentry_result.txt` | First probe (superseded; kept as history). Its acceptance wrongly allowed `I_executed == 2`. |
| `probe_threaded_reentry_v2.py`, `probe_threaded_reentry_v2_result_unmodified.txt`, `probe_threaded_reentry_v2_result_hardened.txt` | Corrected probe: direct per-thread entry proof without hook changes; refusal is the only pass. Fails on the unmodified adapter (finding stands), passes on the hardened scratch tree. |
| `PROPOSED_PATCH_native_step_adapter_thread_meter.diff` | Prototype meter hardening (proposed, scratch-checked, 61/61 kept). |
| `atlas_address.py`, `test_atlas_address.py`, `test_atlas_address_junit.xml`, `RETURN_ADDRESS_CASE_MAP.md/.json` | Snapshot-bound atlas addresses (read-only projection) and the return-address addendum's ten cases, executed: 10 passed. |
| `CASE_RECONCILIATION.md/.json` | Collected versus executed-and-passed case identities per run, for DeepSeek's 52-versus-61 reconciliation. |
| `SHARED_RETURN_20260927.md` | Claude's answer to section 6 of the 2026-09-27 coordination note. |
| `PINNED_COMMIT.txt` | The content commit DeepSeek reviews. |
| `WORKERS.json` | Real worker session identifiers, their bounded scope, and what each returned. |

Claim boundary: local public CPU engineering checks on Python 3.11. Not `CAS_AWS_ENGINEERING_VALIDATED`; no
learned-model, comparative-advantage or production claim; no paid job; no protected material read.
