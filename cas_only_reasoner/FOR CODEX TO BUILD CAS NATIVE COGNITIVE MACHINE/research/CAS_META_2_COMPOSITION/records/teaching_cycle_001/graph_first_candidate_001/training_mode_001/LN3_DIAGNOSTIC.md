# Graph-first ^6 — ln(3) flat-loss investigation (owner-directed)

Attempt 010 is preserved as a completed execution with **no measured learning
improvement**. This record separates what has been MEASURED from what is
PREPARED and still requires an authorized neural measurement. No larger
training allowance is proposed here.

## Measured now (non-neural, from the exported package_010)

Evidence: `training_mode_001/ln3_diagnostic_001/ln3_diagnostic.json`, sha256
`c7311c8dee220851cef18f91099122831979656363b467fe2201933d887d595f`.

1. **The answers do NOT collapse at the input level.** All 60 training+practice
   arm-records have three distinct option TAG STRINGS and three distinct
   option TOKEN-ID SEQUENCES (from the real tokenizer's `encode_public`).
   Option id-sequence lengths range 2–21 tokens. The illustrative
   "identical encodings" mechanism is therefore EXCLUDED at the id level.
2. **Loss recomputation is fresh.** `eval_loss` calls the live module's
   `forward` (source-verified), and the before/after measurements share that
   path.
3. **Weight decay is 0.0.** The learner's AdamW is constructed with
   `weight_decay=0.0` (source-verified), so the recorded parameter movement
   (`left.weight`, `merge.weight`, `right.weight`) came from task gradients —
   the flat loss is not a weight-decay artifact.

What remains unexplained is the stage between token ids and the decision:
the FIXED seeded projection, mean-pooling, the ^6 module output, and the
fixed dot-product readout. Those are neural quantities.

## Prepared neural diagnostic (requires separate authorization)

`cas_meta2/graph_teaching/diagnostic.py` is the fail-closed measurement spec
for the next separately authorized AWS job. It performs NO optimizer step:

- **Per-record three scores and spread** (after projection → pooling →
  module → readout), including the correct slot's score.
- **Option geometry**: pairwise cosines among the three option vectors and
  problem-to-option cosines.
- **Same-example, alternative-target gradient test**: for one example, loss
  values and per-matrix gradient norms (`left.weight`, `merge.weight`,
  `right.weight`) for each of the three targets, without any update.

Decision rules for the authorized run (to be bound in the signed record):

- If scores are all equal (spread ≈ 0) while option vectors are distinct →
  the fixed readout/projection is where the distinction is lost.
- If option vectors are near-parallel (cosine ≈ 1) → the projection/pooling
  erases distinctions before the readout.
- If losses differ per target but gradient norms are ≈ 0 → the corrective
  signal does not reach the module.
- If gradient norms differ usefully per target → the machinery can express a
  preference and the flat ln(3) pilot result points to the small allowance or
  optimization dynamics — a measured answer, not an inference.

## Attempt status (2026-09-09) — MEASURED VERDICT

- Attempt 001 (`cas-meta2-ln3-diagnostic-20260909084139-f6f49be5`) FAILED with
  a preserved spec bug (second backward through a freed graph); fix committed
  at `51f12c61` with regression tests. See `ATTEMPT_LN3_001_FAILURE.md`.
- Attempt 002 (`cas-meta2-ln3-diagnostic-20260909085756-95693cd8`) FINISHED.
  See `ATTEMPT_LN3_002_RESULT.md` (result sha `f685506f…`; ledger 34 → 35).
- **Measured verdict: decision rule 2 is TRUE.** The frozen projection +
  mean-pooling collapses all option vectors to near-parallel directions
  (pairwise cosines ≈ 1.0 to within 4e-8) for every record in both arms;
  scores are equal to float32 noise (spread ≤ 5.6e-9), losses are exactly
  ln 3 for every target, parameter gradients sit at the noise floor
  (≤ 8.0e-8), and argmax is at chance (12/30, 10/30). The flat pilot losses
  are a measured property of the input stage, not of the ^6 module's
  capacity — but whether a non-collapsing representation would let the
  module learn remains an OPEN question and needs a new owner-authorized
  experiment.

## Constraints preserved

- Accepted models unchanged; the completed attempt-010 evaluation result is
  kept intact and its test answers are NOT used to tune anything.
- Any later improvement claim needs a fresh evaluation.
- The repeated-teaching requirement remains; it is not being replaced by this
  diagnostic, only sequenced after the machinery question is answered.
