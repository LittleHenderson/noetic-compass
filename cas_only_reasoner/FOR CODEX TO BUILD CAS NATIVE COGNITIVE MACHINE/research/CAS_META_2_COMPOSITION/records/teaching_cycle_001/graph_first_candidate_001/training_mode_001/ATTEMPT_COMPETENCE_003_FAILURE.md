# Graph-first ^6 — competence run 003: STAGES 1 AND 2 COMPLETED; report serialization crashed (one-line fix prepared)

Status: **AWS_COMPETENCE_FAILED / REMOTE_WORKER_FAILED — after training
completed.** The normalized encoder PASSED the stage-1 gate
(relationship input check + forward/backward sanity), and stage 2 TRAINED
the module to completion (64 steps) — then the result crashed in MY
`fit_criterion` helper on the per-op loss shape (`{"total": float}` dicts
vs ints), so the training numbers were not serialized. Ledger 42 → 43
(`$218.00 → $222.00` reserved, `$178.00` unreserved); the reservation
stands — no refund, no automatic retry. Cleanup complete (instance
`i-0b429fccf06ab4f84` confirmed terminated; collected result sha
`8c42c9dd…` verified; elapsed 553.5 s).

## What this run establishes

1. **The normalized relationship encoder PASSED the stage-1 gate on the
   GPU** — the same-token rewiring now produces a distinguishable module
   input beyond the reorder baseline, and the forward/backward sanity
   passed. The gate defects from runs 001/002 are resolved in a real run.
2. **Stage 2 training ran to completion** (64 optimizer steps, learning
   curve recorded, containment computed) before the serialization crash.

## The one-line defect (fixed, test-locked)

`competence.fit_criterion` summed per-op losses directly; the real trainer
returns `{"total": float}` dicts (the same shape the trainer's own
history-mean already handles). Fixed with the shared `_loss_total`
extraction; the pure test now covers the dict shape explicitly. 130 graph
tests pass.

## What this does NOT change

- The training numbers from this run were lost in the crash; the replacement
  re-runs the whole fixed sequence.
- No capability claim; the two-arm comparison stays postponed; module,
  option path, learning scope, and allowance unchanged.
- The replacement needs a NEW owner GO and one new `$4.00` reservation
  (ledger 43 → 44: `$226.00` / `$174.00`).
