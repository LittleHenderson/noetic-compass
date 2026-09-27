# Authored coverage, not executed acceptance

All test outcomes below are NOT_RUN; none closes an acceptance gate. The source
fixture is synthetic. File names reference tests/ unless otherwise stated.

| Requirement IDs | Current evidence and remaining boundary |
| --- | --- |
| HELM-Q1 T01-T05 | test_contracts.py covers fixture admission, schema, checkpoint, branch, stale/expired state; actual HELM admission absent |
| HELM-Q1 T06-T10 | test_classical.py and test_contracts.py cover order, all inputs, negative target, unsupported instructions and independent verifier |
| HELM-Q1 T11-T15 | Quantum predicate/coherence/cleanup/decoding absent; Claude lease issued, no ACK observed |
| HELM-Q1 T16-T17 | test_contracts.py covers disabled/shadow/research immutable fixture behavior; host baseline parity NOT_RUN |
| HELM-Q1 T18-T25 | Exact return fields bound, but actual RPM nested/shared/cycle/rollback/restart/RPA integration absent; evaluator separated in source |
| HELM-Q1 T26-T27 | test_backend.py and test_cli.py cover zero submission and refusal of fake grants/fallback; no provider client |
| HELM-Q1 T28-T30 | Atomic paid accounting, retry reconciliation and current provider quote handling not implemented |
| HELM-Q1 T31-T34 | No real jobs; unknown poll/cancel/decode explicitly refused; hardware receipt forgery probes authored; simulation/calibration absent |
| HELM-Q1 T35 | test_classical.py distinguishes finite no-sample from exhaustive/structured proof and budget exhaustion |
| HELM-Q1 T36 | Source-authored methods counted separately from collection/execution and old helper receipt |
| HELM-Q1 T37 | Q1-Codex attribution recorded; no native-learning claim |
| HELM-Q1 T38 | Finite fixture limits implemented; OS memory enforcement and simulator resource preflight still required |
| HELM-Q1 T39 | Isolated root/history and no incumbent writes/jobs by this session; live training health not revalidated |
| HELM-Q1 T40 | Independent acceptance NOT_RECEIVED |
