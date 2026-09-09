# Graph-first ^6 — competence run 001: ONE complete learning experiment (PREREGISTERED, AWAITING OWNER GO)

Owner-directed, 2026-09-09, after the review of the fragmented process. This
replaces the sequence of separate micro-diagnostics with ONE owner-approved,
bounded development job containing a fixed sequence. No separate launches
between stages; no silent mid-run patches; no unlimited retries.

## The question

Can ONE targeted ^6 learner learn the whole-part relationship at all — first
on the familiar examples, then measured on fresh examples? The two-framing
comparison is POSTPONED (first show one learner can learn; then compare
teaching styles).

## The fixed in-job sequence (single arm: cas framing)

- **STAGE 1 — checks, zero optimizer steps.** (a) Relationship preservation:
  same-token rewiring must produce a distinguishable module INPUT beyond the
  connection-list-reorder baseline (declared tolerance: rewire input
  difference > 10× reorder input difference). Module OUTPUT differences are
  REPORTED, not gated. (b) Forward/backward sanity: finite losses, nonzero
  gradients on all three matrices. Failure stops the job and RETURNS the
  preserved measurements with `outcome: "STAGE1_CHECK_FAILED"` — never a
  bare exception (attempt 001's defect, fixed and test-locked).
- **STAGE 2 — training.** The candidate ^6 module (registered decompose
  transform, `operation:^6` only) trains on the familiar train+practice
  whole-part examples: 64 optimizer steps / 600 s, learning rate 0.003,
  digest containment report, and a learning curve recorded every 8 steps.
- **STAGE 3 — fresh examples, only if the registered fit criterion is met:**
  mean after-loss < mean before-loss − 0.02. Then the sealed validation/test
  splits are evaluated with predictions recorded before answers, alongside
  the familiar-example accuracy — reported separately.

## The registered deliverable — exactly one of

1. **"It learned the practice examples and transferred to these fresh
   examples."** (criterion met AND sealed combined correct ≥ 6/12; chance
   expectation ≈ 4/12.)
2. **"It learned the practice examples but did not transfer."** (criterion
   met, sealed < 6/12.)
3. **"It did not fit the practice examples within the declared allowance;
   here are the actual losses, predictions, and remaining measured
   limitation."** (criterion not met — actual numbers reported regardless.)

The outcome label is computed by a deterministic rule from the recorded
numbers, never by prose judgement. No learning or capability claim beyond
the outcome sentence and its supporting numbers.

## Frozen budget and constraints

One job, ONE new `$4.00` reservation (ledger 40 → 41: `$214.00` reserved /
`$186.00` unreserved), no automatic retry. Relationship-preserving problem
encoder (option 2, prepared and test-locked); repaired token lookup; option
path and learning scope unchanged; sealed splits only ever read in stage 3;
128 graph tests pass.
