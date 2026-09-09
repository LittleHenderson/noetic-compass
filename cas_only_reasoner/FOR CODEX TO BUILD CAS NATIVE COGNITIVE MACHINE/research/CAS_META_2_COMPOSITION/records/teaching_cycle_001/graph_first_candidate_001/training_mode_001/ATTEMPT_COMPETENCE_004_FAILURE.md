# Graph-first ^6 — competence run 004: FIT CRITERION MET; stage 3 crashed on a sealed empty-content option (fixed)

Status: **AWS_COMPETENCE_FAILED / REMOTE_WORKER_FAILED — after the fit
criterion was MET and stage 3 had begun.** This run went the farthest yet:
stage 1 passed, stage 2 trained, and the registered fit criterion was
satisfied (mean after-loss < mean before-loss − 0.02), so the sealed
fresh-example evaluation started — then crashed on a sealed record with an
all-shared option, because the SEALED predict path lacked the zero-vector
fallback that training already has. Ledger 43 → 44 (`$222.00 → $226.00`
reserved, `$174.00` unreserved); the reservation stands — no refund, no
automatic retry. Cleanup complete (instance `i-00608f7cfbca928dd` confirmed
terminated; collected result sha `f06da038…`; elapsed 552.2 s; receipt
`receipt_cas-meta2-competence-20260909202533-7cb622f8/`).

## What this run establishes

1. **The stage-1 relationship gate PASSES on the GPU** (second consecutive
   run).
2. **Training improves the familiar-example loss beyond the registered
   margin** — the fit criterion fired, which is the first positive learning
   signal on the practice examples in this whole investigation.
3. **The sealed evaluation is the only remaining broken step**, and its
   defect is a one-line asymmetry, not a learning question.

## The defect (fixed, test-locked)

`GraphLearner.predict`'s sealed path called `self._sum(item)` for every
option; a sealed record whose option is a strict subset (all tokens shared
by the other two) yields empty content, and `_sum([])` raised
`OPTION_EMBEDDING_REQUIRED`. The training path already handles this with the
ZERO vector; the sealed path now does too (`zeros_like(value)`), with a
behavioral regression test. 130 graph tests pass.

## What this does NOT change

- The training and criterion numbers from this run were lost in the crash;
  the replacement re-runs the whole fixed sequence.
- No capability claim; the two-arm comparison stays postponed; module,
  option path, learning scope, and allowance unchanged.
- The replacement needs a NEW owner GO and one new `$4.00` reservation
  (ledger 44 → 45: `$230.00` / `$170.00`).
