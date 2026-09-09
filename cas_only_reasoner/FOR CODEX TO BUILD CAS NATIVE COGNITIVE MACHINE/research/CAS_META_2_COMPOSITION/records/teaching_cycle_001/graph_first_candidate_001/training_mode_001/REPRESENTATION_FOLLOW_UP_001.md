# Graph-first ^6 — representation follow-up 001 (owner-authorized "implement it")

## Basis of authorization

The owner instructed: *"IF THE FOLLOWING IS TRUE IMPLEMENT IT IF NOT IT'S YOUR
CALL"*, pasting the attempt-002 result record. The record is **TRUE** — every
identity in it was re-verified before acting: collected result sha
`f685506f…` matches the byte file, the launcher `result.json` status is
`AWS_GRAPH_TRAINING_LN3_DIAGNOSTIC_FINISHED`, cleanup complete, and the ledger
transition 34 → 35 is recorded. The follow-up the record names is therefore
implemented here.

## The change (exactly ONE variable)

| Piece | Attempt 010 (frozen record) | Follow-up 001 |
|---|---|---|
| option-slot aggregation (frozen readout side) | MEAN pooling | **SUM pooling** |
| problem aggregation (module input) | MEAN pooling | MEAN pooling — UNCHANGED |
| public-record contract, lessons, scoring, seeds (`20260909`) | frozen | UNCHANGED |
| module (registered ^6 decompose candidate, config, plasticity `operation:^6`) | frozen | UNCHANGED |
| budget (64 steps / 600 s per arm; totals 128 / 1200), one job, `$4.00`, no retries | frozen | UNCHANGED |
| sealed splits + evaluation boundaries | frozen | UNCHANGED |

Code: `real_framework.GraphLearner._sum` for options (training AND sealed
predict paths), `adapter.option_vector` sum mirror; tests lock both and the
problem-side mean. Why sum: the measured collapse came from averaging heavily
overlapping token sequences; sum keeps each option's distinct tokens and
their count, and any common additive component is softmax-shift-invariant
(harmless to the decision).

## Ruled out (recorded, not silent)

"Readout inside the permitted plasticity group" is NOT implemented: a learned
readout head would add parameters outside the registered
`operation:^6`/`bias_update_head` contract and would be new architecture
mid-correction. The module input scale is also deliberately unchanged so the
module's operating point is exactly attempt 010's — one variable at a time.

## Preregistered expectations (both recorded honestly)

- **A — the representation was the blocker:** losses move below ln 3 and
  sealed accuracy moves above chance → the distinction now reaches the
  readout and the module can act on it within the allowance.
- **B — flat losses persist:** the distinction reaches the readout but the
  module still cannot use it within the allowance; the next measured suspect
  is the module's operating point (tanh saturation at
  `initial_saturation=100.0`), a separate, separately authorizable step.

No learning or capability claim is precommitted; the run's containment
report and sealed evaluation decide the record.

## Measured outcome (attempt 011, `cas-meta2-teaching-graph-20260909095712-4ca46fce`)

See `ATTEMPT_GRAPH_011_RESULT.md` (result sha `e4a0d61d…`, ledger 35 → 36).

- **A (first half) CONFIRMED for 2 of 3 ops:** LIST_PARTS and REACHED_VIA
  before-losses are no longer exactly ln 3 and move under the same 64-step
  allowance — the sum-pooled readout now delivers distinct options.
- **A (second half) NOT confirmed:** sealed accuracy 3/12, chance-level.
- **Residual:** FIND_SHARED_PART stays exactly at float32 ln 3 before and
  after in both arms — its options still score identically.
- Next measured suspects (each separately authorizable): the
  FIND_SHARED_PART residual collapse, the 64-step allowance, and the module's
  operating point.
