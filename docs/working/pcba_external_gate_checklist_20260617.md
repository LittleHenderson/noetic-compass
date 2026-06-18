# PCBA External Gate Checklist

Date: 2026-06-17
Scope: Gates that cannot be honestly closed by local code alone
Status: External/time/legal/security proof still required

## Local Gates Moved Forward

Local evidence artifact:

- `docs/working/pcba_model_local_evidence_20260617.json`

Locally provable evidence verified:

- `pcba_grammar_spec_present`
- `pcba_parser_implementation_present`
- `pcba_component_catalog_complete`
- `pcba_parser_tests_pass`
- `pcba_invalid_form_tests_pass`
- `pcba_ir_roundtrip_tests_pass`
- `pcba_production_compiler_integration_tests_pass`
- `pcba_no_accept_bypass_tests_pass`
- `no_pcba_to_accept_route`
- `auditor_accept_requires_gate_passes`
- `broker_accept_negative_tests_pass`
- `csb_shadow_mode_tests_pass`
- `cpmb_brownout_lock_tests_pass`

Verification:

- `python scripts\run_pcba_model_checks.py --out "..\docs\working\pcba_model_local_evidence_20260617.json"` passed
- `python -m pytest -q` from `cas-forex` passed `152 passed`
- `python scripts\smoke_backtest.py` and `python scripts\smoke_mtfa.py` both ran

Additional rectification status:

- `docs/working/pcba_rectification_status_20260617.md`

## Still Missing Before Production PCBA Component Syntax

- `pcba_semantics_review_signed`

## Still Missing Before Live-Trading Permission

- `twelve_month_backtest_pass`
- `thirty_trading_day_paper_proof_pass`
- `legal_account_gates_pass`
- `broker_proof_pass`
- `human_unlock_next_session_receipt`

## Still Missing Before Safety, Prompt-Injection, Memory, Burnout, or Governance Claims

- Formal semantics.
- Negative/security evaluation.
- External red-team report.
- Evidence anchoring.
- Legal/regulatory review where applicable.
- Claim review signed by the owner.

## Permanent Boundary: Broker `ACCEPT`

PCBA component or board diagnostics must not directly create broker `ACCEPT`. `ACCEPT` remains controlled by the existing CAS Forex auditor/gate path.
