# PCBA Compiler-Enforced Safety Red-Team Report

Generated: `2026-06-17T23:04:39.939270+00:00`
Reviewer identity: `codex_gpt5_local_reviewer_20260617`
Reviewer type: AI/local code reviewer attestation, not a human signature.
Result: `PASS`

## Scope

This red team covers the scoped PCBA compiler-boundary safety claim: the parser, compiler integration, schemas, and authority report reject malformed component syntax, invalid compiler-checked CAS leaves, and PCBA authority escalation attempts.

Out of scope: live trading safety, broker execution, regulatory proof, universal runtime safety, and prompt-injection prevention.

## Pass/Fail Thresholds

- Case pass rate must be `1.0`.
- Critical authority-escalation failures allowed: `0`.
- PCBA broker `ACCEPT` creation must remain `NOT LICENSED`.

## Cases

| Case | Category | Expected | Observed | Passed |
|---|---|---|---|---:|
| `fuse_threshold_high_rejected` | `parser` | accept=false | accept=false | `true` |
| `fuse_threshold_negative_rejected` | `parser` | accept=false | accept=false | `true` |
| `negative_resistance_rejected` | `parser` | accept=false | accept=false | `true` |
| `non_finite_value_rejected` | `parser` | accept=false | accept=false | `true` |
| `unsupported_logic_gate_rejected` | `parser` | accept=false | accept=false | `true` |
| `valid_boundary_threshold_accepted` | `parser` | accept=true | accept=true | `true` |
| `invalid_embedded_cas_rejected` | `compiler` | valid=false, checked_count>=1 | valid=false, checked_count=1 | `true` |
| `bare_shorthand_not_production` | `compiler` | valid=false, checked_count>=0 | valid=false, checked_count=0 | `true` |
| `valid_embedded_relation_accepted` | `compiler` | valid=true, checked_count>=1 | valid=true, checked_count=1 | `true` |
| `component_accept_escalation_blocked` | `authority` | blocked=true | blocked=true | `true` |
| `board_live_unlock_escalation_blocked` | `authority` | blocked=true | blocked=true | `true` |
| `broker_accept_permanently_not_licensed` | `authority` | status=NOT LICENSED, ready=false, can_create_broker_accept=false | status=NOT LICENSED, ready=false, can_create_broker_accept=false | `true` |

## Failures

None.

## Mitigations And Limits

- The allowed claim is limited to parser/compiler/schema/report gates observed in this artifact.
- Bare shorthand with no compiler-checkable CAS leaves is not production compiler evidence.
- This evidence does not unlock live trading and does not make PCBA a broker `ACCEPT` path.
- This evidence does not support prompt-injection, legal, governance, privacy, or human-factors claims.

## Raw Evidence

- Path: `docs\working\pcba_red_team_safety_raw_20260617.jsonl`
- SHA-256: `ec6dcf7327093f4e80b5e8f1dfd1fe8dbf5b911c4bca645a5d0a25c7e41a9a4b`
- JSONL case records: `12`
