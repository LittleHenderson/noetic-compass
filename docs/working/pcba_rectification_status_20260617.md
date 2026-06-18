# PCBA Rectification Status

Date: 2026-06-17
Scope: User-requested cleanup for `datetime.utcnow()` and PCBA production/readiness gates

## Rectified Locally

| Item | Result | Evidence |
|---|---|---|
| `datetime.utcnow()` | Replaced in `cas-forex` runtime, schemas, and proof scripts with central timezone-aware UTC helpers. | `cas-forex/cas_forex/time_utils.py`; `rg "datetime\.utcnow|utcnow\(" cas_forex scripts tests` returns no matches. |
| Python deprecation warnings | Cleared in the full local test run. | `python -m pytest -q` -> `152 passed` with no warning summary. |
| PCBA compiler integration | Added real CAS compiler checking for embedded CAS leaves/relations in PCBA components. | `cas-forex/cas_forex/pcba_compiler.py`; `tests/test_pcba_compiler_integration.py`; `pcba_production_compiler_integration_tests_pass=true`. |
| PCBA no-`ACCEPT` route | Re-verified. | `no_pcba_to_accept_route`, `auditor_accept_requires_gate_passes`, and `broker_accept_negative_tests_pass` are `true` in `docs/working/pcba_model_local_evidence_20260617.json`. |

## Still Open Or NOT LICENSED

| Gate | Status | What Still Has To Happen |
|---|---|---|
| Production PCBA component syntax | `OPEN` | Only `pcba_semantics_review_signed` remains. A human/owner semantics review must approve the grammar and meaning boundary before this can be marked production syntax. |
| Live-trading permission | `NOT LICENSED` | Needs real `twelve_month_backtest_pass`, real `thirty_trading_day_paper_proof_pass`, `legal_account_gates_pass`, `broker_proof_pass`, and `human_unlock_next_session_receipt`. Synthetic smoke runners do not satisfy this. |
| Compiler-enforced safety claim | `NOT LICENSED` | Needs formal PCBA safety semantics, negative safety evaluation, red-team report, evidence anchoring, and signed claim review. |
| Prompt-injection prevention claim | `NOT LICENSED` | Needs matched prompt-injection evaluation, hidden/text controls, false-positive floor, red-team pass, and repeatable evidence chain. |
| Governance/regulatory proof claim | `NOT LICENSED` | Needs regulatory mapping, legal review, audit-retention proof, customer disclosure review, and signed governance claim review. |
| Broker `ACCEPT` creation from PCBA | `NOT LICENSED` | This remains intentionally blocked. PCBA can explain, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`, or contribute to `LIVE_LOCKED`; it must not directly create broker `ACCEPT`. |

## Verification Commands

- `python -m pytest tests/test_pcba_compiler_integration.py tests/test_pcba_models.py -q` -> `44 passed`
- `python -m pytest -q` -> `152 passed`
- `python scripts\run_pcba_model_checks.py --out "..\docs\working\pcba_model_local_evidence_20260617.json"` -> passed
- `python scripts\smoke_backtest.py` -> ran
- `python scripts\smoke_mtfa.py` -> ran
- `python scripts\run_comparative_backtest.py --bars 120 --output-dir evidence_runs\rectify_comparative_smoke` -> runner/evidence chain verified, report intentionally `passed=false`
- `python scripts\run_paper_trading_session.py --days 2 --output-dir evidence_runs\rectify_paper_smoke` -> runner/evidence chain verified, report intentionally `passed=false`
