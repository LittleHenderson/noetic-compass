# COST ESTIMATE

## Boundary rules

- No paid model API (no Bedrock, Anthropic, OpenAI, or any).
- No cloud GPU in Phase 0.
- No new model download when a suitable local snapshot exists.
- Every later GPU phase records an estimated runtime and a maximum
  resource budget BEFORE it runs.

## Phase 0 (this commit)

- GPU: none.
- Paid API: none.
- Cost: 0 USD. Local file writes and git only.

## Later phases (rough, pending — not authorized yet)

All figures OPEN until the model and hardware are fixed. Placeholders
below are order-of-magnitude only and are NOT a budget approval.

| Phase | Work | GPU | Rough cost note |
|---|---|---|---|
| 1 | Synthetic right-inverse maths + tests | none (CPU) | ~0 USD |
| 2 | Readout fit + controls, small local model | local GPU (RTX 4070) or CPU for a small model | electricity only if local |
| 3 | Activation-level bridge | local GPU | electricity only if local |
| 4 | LoRA weight-update realizer | local GPU | electricity only if local |
| 5 | CAS-Ohm dose calibration | local GPU | electricity only if local |
| 6 | Learning-benefit runs (7 conditions x example counts) | local GPU; escalate only if capacity-floor fails | OPEN |
| 7 | Selective consolidation, sequential tasks | local GPU | OPEN |
| 8 | Replication bundle | none | ~0 USD |

## Escalation cost rule

A larger model applies to EVERY condition, not just the CAS condition, so
its cost multiplies across all arms. Record the multiplied budget before
any escalation.

## Overhead accountability

Phase 6 must measure controller/measurement overhead. If overhead exceeds
compute saved, the wall-clock acceleration claim is withdrawn
(falsifier 6).
