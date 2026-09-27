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
| `WORKERS.json` | Real worker session identifiers, their bounded scope, and what each returned. |

Claim boundary: local public CPU engineering checks on Python 3.11. Not `CAS_AWS_ENGINEERING_VALIDATED`; no
learned-model, comparative-advantage or production claim; no paid job; no protected material read.
