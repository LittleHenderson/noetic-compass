# COST ESTIMATE (Phase 0A)

## Boundary rules

- No paid model API (no Bedrock, Anthropic, OpenAI, or any).
- No cloud GPU in Phase 0.
- No new model download: the `Qwen/Qwen2.5-0.5B-Instruct` snapshot is
  already local (confirmed, hashed — see MODEL_IDENTITY.json). Nothing to
  download.
- Every later GPU phase records an estimated runtime and a maximum
  resource budget BEFORE it runs.

## Hardware

- Model: 0.5B parameters. Fits the local RTX 4070 (8GB, fp16) per the
  project compute ladder (local handles up to ~3B fp16). No AWS needed
  for the 0.5B arm.
- Fallback 1.5B also fits local fp16. A 3B escalation would be near the
  local ceiling; only then consider AWS, and only if a capacity-floor
  failure forces escalation across ALL arms.

## Phase 0 / 0A (this commit)

- GPU: none. Paid API: none. Model download: none.
- Cost: 0 USD. Local file writes, file hashing, PDF reads, git only.

## Later phases (rough, pending — not authorized)

| Phase | Work | GPU | Cost note |
|---|---|---|---|
| 1 | Synthetic right-inverse maths + tests | none (CPU) | ~0 USD |
| 2 | Readout fit + controls (0.5B) | local RTX 4070 | electricity only |
| 3 | Activation-level bridge | local RTX 4070 | electricity only |
| 4 | LoRA weight-update realizer | local RTX 4070 | electricity only |
| 5 | CAS-Ohm dose calibration | local RTX 4070 | electricity only |
| 6 | Learning benefit (7 conditions x example counts x 10 seeds) | local RTX 4070 | electricity; largest local run |
| 7 | Selective consolidation, 3 sequential tasks | local RTX 4070 | electricity |
| 8 | Replication bundle | none | ~0 USD |

## Escalation cost rule

A larger model applies to EVERY arm, multiplying cost across conditions.
Record the multiplied budget before any escalation. A 3B-or-larger
escalation moves off local to AWS and must be separately authorized.

## Overhead accountability

Phase 6 measures controller/measurement overhead. If overhead exceeds
compute saved, claim 4D (wall-clock) is withdrawn (falsifier 6).
