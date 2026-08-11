# Audit Findings Received and Current Disposition — 2026-07-21

This file preserves the audit concerns supplied by the project owner and records their status at this handoff. It is a triage record, not proof that an open engineering item was fixed.

The supplied report says “17 findings,” but its numbered sections enumerate 20 findings: five claims findings, five code-foundation findings, four evidence-integrity findings, and six operations findings. Future summaries should use the numbered list or explicitly explain that count discrepancy.

| Finding | Current disposition |
|---|---|
| 1.1 Scope explosion between versions | Partially addressed in current specifications and the Amazon claim/evidence manifest. Cross-architecture raw-evidence reconciliation remains `OPEN`; no universal claim is licensed by the 2026-07-21 run. |
| 1.2 Withdrawn first `ACCEPT` | Correction preserved prominently. Root cause is tied to a pre-fix candidate-only `control_proof` being treated as verified. No `ACCEPT` stands. Prospective verdict-reliability testing remains required. |
| 1.3 Universal claim not licensed | Adaptive open-weight universality remains an explicit engineering objective. Empirical cross-architecture universality remains `OPEN`. |
| 1.4 Numbers without error bars | The new primary result includes a paired clustered-bootstrap 95% CI. Historical headline numbers still require claim-by-claim uncertainty and split/provenance review. |
| 1.5 Silent “not proven” list | Current successor, Amazon draft, claim-status file, and this handoff place limitations near the front. |
| 2.1 Planner magic numbers | `OPEN`. Replace unlabeled precision with named, versioned coefficients and measured calibration receipts by hardware/runtime class. |
| 2.2 Planner can return a non-fitting plan | `OPEN`. Execution dispatch must reject or require explicit research override when the final plan does not fit. Add boundary tests. |
| 2.3 MoE blind spot | `OPEN`. Add architecture metadata for total versus active parameters, expert topology, routing, and activation workspace. |
| 2.4 Estimated layer count proceeds | `OPEN`. Claim-bearing execution must require authoritative model config; an estimate may remain planning-only. |
| 2.5 Precision/quantization string handling | `OPEN` low-risk hardening item. Normalize allowed aliases and reject unknown combinations with direct tests. |
| 3.1 Governance-mode WORM is operator-overridable | `OPEN` critical durability/integrity gate. Use true compliance retention where appropriate or independently controlled escrow/Merkle-root publication. |
| 3.2 Approximately 30-day evidence window | `OPEN`. Define contractual retention classes and prove export/retention/reconstruction beyond the incident-review horizon. |
| 3.3 Explainer IP leakage | `OPEN` design risk. Use a typed allow-list projection, schema tests, provider data controls, adversarial tests, and strict discard-on-mismatch. Prompt instructions alone are insufficient. |
| 3.4 SHA-256 and quantum framing | Do not describe SHA-256 as presently broken or as having “zero” quantum resistance. Preserve crypto agility and obtain formal long-horizon cryptographic review; adding SHA-512 or SHA-3 alone is not automatically a post-quantum evidence design. |
| 5.1 Single Postgres architecture | `OPEN` critical resilience gate. Add checkpoint/restart semantics, tested backup restore, and replica/failover evidence. |
| 5.2 No cryptographic worker identity | `OPEN` critical worker-trust gate. Require cryptographic identity plus signed lease/job/result binding; identity still does not prove honest computation. |
| 5.3 512-worker cap | Retain as a current bounded operational limit, not a law of the architecture. Add a reviewed future-scale escalation path rather than silently bypassing it. |
| 5.4 Hosted customer-weight exfiltration risk | `OPEN`. Requires isolation, least privilege, access logging, deletion receipts, process controls, agreements, and—where feasible—customer-controlled execution. |
| 5.5 Pythia-only validation concern | The completed diagnostic is one pinned Pythia-160M run. Historical OLMo/Qwen/Pythia-scale evidence must be classified by exact tier and raw artifact availability. Cross-family replication remains `OPEN`. |
| 5.6 Heartbeat blind spot | `OPEN`. Heartbeats prove liveness, not honesty. Add signed results, spot-check/redundant execution, invariants, and reconstruction checks in proportion to cost. |

No production code remediation is claimed merely because these findings are organized here. The protected implementation snapshot is included so the next engineering pass can implement and test the code-level items against exact audited bytes.

