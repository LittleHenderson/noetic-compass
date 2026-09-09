# Graph-first ^6 — competence run 005: **LEARNED_AND_TRANSFERRED**

Status: **AWS_COMPETENCE_FINISHED — outcome `LEARNED_AND_TRANSFERRED`.** One
targeted ^6 learner (cas framing) ran the whole fixed sequence in ONE job:
relationship gate, forward/backward sanity, 64 bounded updates on the
familiar examples, and the sealed fresh-example evaluation. Ledger 44 → 45
(`$226.00 → $230.00` reserved, `$170.00` unreserved). Cleanup complete
(instance `i-0b557bef60b48067b` confirmed terminated); collected result sha
`ab085d68…` verified; elapsed 554.8 s.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-competence-20260909210625-0a10f14d` |
| request sha256 | `98ead74e60057575a1e740c358cbb25b66961d547643d43f8fca0c41921c9553` |
| authority sha256 | `7c8a37ec4a68d97c2347c5723885cfaa68d0d72048c15666ddbe2d5c88777566` |
| owner record sha256 | `a169078d02acb7d3aee2b4d41c5422c9240203576fb9192fc7056ebb59bf5af7` |
| collected result sha256 | `ab085d682fbba7fef8b71a7a6f31cd38c822d77ca59bcce7ec0461024956ea80` |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-competence-20260909210625-0a10f14d/`

## STAGE 1 — the relationship gate, passed on real numbers

| Check | Measured |
|---|---|
| same-token rewiring → module INPUT difference | `1.7631` and `1.7631` (two records) |
| connection-list reorder → module INPUT difference | `0.0` and `0.0` |
| rewiring → module OUTPUT difference | `0.5772` / `0.5772` (the module RESPONDS) |
| forward/backward sanity | losses 1.011–1.153 finite; gradients 1.26–2.16 on all three matrices |

The relationship distinction survives encoding at O(1) scale, is exactly
invariant to harmless reordering, and moves the module output.

## STAGE 2 — bounded training on the familiar examples (64 updates, 600 s cap)

| Op | before loss | after loss |
|---|---|---|
| LIST_PARTS | `1.0817894220352173` | `0.6742571633309126` |
| FIND_SHARED_PART | `1.059303057193756` | `0.23778395615518094` |
| REACHED_VIA | `1.1539838492870331` | `0.7811747074127198` |

Learning curve (mean loss): `1.09836 → 0.86284 → 0.78657 → 0.72501 →
0.65592 → 0.63004 → 0.61819 → 0.55023 → 0.56441` (steps 0…64).

**Registered fit criterion: MET — margin `0.5339535005390644` (threshold
`0.02`).** Containment: only `left.weight`, `merge.weight`, `right.weight`
changed; zero forbidden. Lesson exposure: 22 / 22 / 20 updates across the
three ops. Familiar-example accuracy: **24 / 30**.

## STAGE 3 — fresh examples (sealed, predictions recorded before answers)

| Split:op | correct / attempted |
|---|---|
| validation:LIST_PARTS | 1 / 2 |
| validation:FIND_SHARED_PART | 2 / 2 |
| validation:REACHED_VIA | 1 / 3 |
| test:LIST_PARTS | 1 / 2 |
| test:FIND_SHARED_PART | 1 / 1 |
| test:REACHED_VIA | 1 / 2 |

**Sealed total: 7 / 12** (chance expectation ≈ 4 / 12).

## The registered outcome

> **LEARNED_AND_TRANSFERRED** — it learned the practice examples and
> transferred to these fresh examples.

## Honest scope

- One seed, one arm, one bounded allowance (64 updates / 600 s), small
  counts (30 familiar, 12 sealed). The two-framing comparison was
  deliberately postponed and is NOT claimed.
- The result is the registered deterministic outcome and its numbers; no
  broader capability claim is made. Frozen negatives `0/72`, accepted
  models, and prior records are untouched.
- What changed in the pipeline that made this possible, in order: the token
  lookup repair (attempt 005 diagnostic), the relationship-preserving
  problem encoder with per-line joint binding, unit normalization of bound
  lines (competence run 002's measurement), and the serialization/edge-case
  fixes from competence runs 001/003/004.
