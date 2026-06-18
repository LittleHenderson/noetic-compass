# CJT Production-Authority Readiness Report

Date: 2026-06-17
Scope: CAS Forex CJT/PCBA production-authority gates
Status: Local engineering gates partially advanced; not production-authority enabled

## Result

The requested high-authority CJT features are now explicit, testable readiness gates in CAS Forex. A local ungating evidence run has advanced the parser/IR/no-`ACCEPT` proof items, but the features are not enabled as production authority.

Current statuses:

| Feature | Status | Ready | Authority Boundary |
|---|---:|---:|---|
| Production `CJT<>` compiler syntax | `OPEN` | false | Research parser present; approval/semantics/production compiler integration still missing |
| Live-trading permission path | `NOT LICENSED` | false | Local no-bypass proof present; 12-month/30-day/legal/broker/human proof still missing |
| Claim of compiler-enforced safety | `NOT LICENSED` | false | Cannot be used as a product claim |
| Prompt-injection prevention | `NOT LICENSED` | false | Shadow diagnostics only |
| Governance-standard/regulatory proof | `NOT LICENSED` | false | Requires external legal/regulatory review |
| Anything that can create broker `ACCEPT` | `NOT LICENSED` | false | Blocked by schema and tests |

## Local Evidence Run

Evidence artifact:

- `docs/working/cjt_ungating_local_evidence_20260617.json`

Local evidence now present:

- `cjt_grammar_spec_present`
- `cjt_parser_implementation_present`
- `cjt_parser_tests_pass`
- `cjt_invalid_form_tests_pass`
- `cjt_ir_roundtrip_tests_pass`
- `cjt_compiler_branch_disconnected_from_live_trading`
- `cjt_no_accept_bypass_tests_pass`
- `no_cjt_to_accept_route`
- `auditor_accept_requires_gate_passes`
- `broker_accept_negative_tests_pass`

## Implemented

- Added CJT diagnostic schemas:
  - `CjtRegion`
  - `CjtDiagnosticKind`
  - `CjtClaimCeiling`
  - `CjtObservation`
  - `CjtCircuitDiagnostic`
  - `CjtProductionFeature`
  - `CjtProductionReadinessCheck`
  - `CjtProductionReadinessReport`
- Added optional `cjt_diagnostics` sidecar fields to:
  - `ForexEvidencePacket`
  - `ForecastHarnessReport`
- Added `cas_forex.cjt_readiness` with:
  - `build_cjt_production_readiness_report()`
  - `assert_cjt_high_authority_features_blocked()`
  - `is_production_cjt_syntax_enabled()`
- Added `scripts/report_cjt_readiness.py`.
- Added `tests/test_cjt_readiness.py`.

## Tests Run

From `cas-forex/`:

- `python -m pytest tests/test_cjt_readiness.py -q` -> `5 passed`
- `python -m pytest tests/test_cjt_compiler_syntax.py -q` -> `14 passed`
- `python scripts\run_cjt_ungating_checks.py --out ..\docs\working\cjt_ungating_local_evidence_20260617.json` -> local evidence collected
- `python -m pytest tests/test_plan_completion.py -q` -> `10 passed`
- `python -m pytest -q` -> `108 passed`
- `python scripts\smoke_backtest.py` -> `14 trades | 5 won | 9 lost | PnL $-15.60 | Sharpe 0.63`
- `python scripts\smoke_mtfa.py` -> completed across scalping/day/swing/position styles

Warnings: known `datetime.utcnow()` deprecation warnings remain.

## Boundary

CJT diagnostics can explain, `SUPPRESS`, `FLAG_FOR_HUMAN_REVIEW`, or contribute to `LIVE_LOCKED`. They cannot create `ACCEPT`, unlock live trading, license compiler-enforced safety claims, license prompt-injection prevention claims, or license governance/regulatory proof.

CAS Forex live money remains `NOT LICENSED`.
