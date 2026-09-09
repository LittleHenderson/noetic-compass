# Graph-first ^6 — ln(3) neural diagnostic AWS attempt 002: FINISHED — the collapse is MEASURED

Status: **AWS_GRAPH_TRAINING_LN3_DIAGNOSTIC_FINISHED.** The replacement ran the
full measurement: preflight, one new `$4.00` reservation, launch, CUDA,
encoder, candidate ^6 module, per-record scores, option geometry, and the
alternative-target gradient test on BOTH framing arms. No optimizer step
(`optimizer_steps_taken: 0`), checkpoint identities unchanged, cleanup with
zero leftovers.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-ln3-diagnostic-20260909085756-95693cd8` |
| request sha256 | `d7823d544d5a15f0cb9220bc19174d8376ccd6f8fc58e6c48e0f62c2607e89e3` |
| authority sha256 | `f3c36c947b24008c8a11f4a89c5898b5c7b00f01ef8b3dab5a18b91e179bd8d3` |
| owner record sha256 | `b856257b7625cbf71cd51014ae2d9ff63b716ce5fef5d3dc52f2e310f658efe4` |
| collected result sha256 | `f685506fcd8bdc6fc57407a8e5f0c5249461a9af7b576e30327620a4533fecb6` |
| instance | `i-00207f8412e451d90` (CONFIRMED_TERMINATED) |
| elapsed | 547.16 s |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-ln3-diagnostic-20260909085756-95693cd8/`
(deterministic analysis: `tools/graph_training_ln3_result_analysis.py`).

Ledger 34 → 35 (`$186.00 → $190.00` reserved, `$214.00 → $210.00`
unreserved).

## Measured (30 records per arm, 10 per op; both arms show the same pattern)

| Quantity | cas | generic |
|---|---|---|
| checkpoint before == after | true | true |
| score spread (within record) | median `0.0`; 21/30 exactly `0.0`; max `5.59e-9` | same (identical to 4 digits) |
| all 90 scores | within `0.02079586 ± 1e-8` | same |
| option pair cosines (3 pairs/record) | min `0.9999999675104585`, max `1.0000000294871674` | same |
| problem→option cosines | min `0.9999999079116348` | min `0.9999999681049316` |
| per-target loss (targets 0/1/2) | exactly `1.0986123085021973` (= float32 ln 3) for every target | same |
| gradient norms | `left.weight` 1.72e-8…3.52e-8; `merge.weight` 3.99e-8…8.04e-8; `right.weight` 2.06e-8…3.70e-8 | same |
| argmax accuracy | 12/30 | 10/30 |
| chance | 10/30 | 10/30 |

## The bound decision rules, applied to the measurement

1. **"Equal scores while option vectors are distinct → the readout loses the
   distinction"** — scores ARE equal (spread ≈ 0), but the option vectors are
   NOT distinct: all pairwise cosines are ≈ 1.0 to within 4e-8. Rule 1's
   condition fails; the loss of distinction happens EARLIER than the readout.
2. **"Option vectors near-parallel → projection/pooling erases distinctions
   before the readout"** — **MEASURED TRUE.** The frozen seeded projection +
   mean-pooling collapses every option representation onto one direction
   (and the problem vector too: problem→option cosines ≈ 1.0).
3. **"Losses differ per target but gradients ≈ 0 → the corrective signal does
   not reach the module"** — losses do NOT differ (all exactly ln 3, because
   the scores are equal). The gradient norms ARE at the noise floor
   (≤ 8.0e-8): the readout gradient is Σ(p_i − y_i)·opt_i ≈ (1 − 1)·opt ≈ 0,
   a direct consequence of rule 2's collapse.
4. **"Gradient norms differ usefully per target → the machinery can express a
   preference"** — NOT triggered: per-target gradient norms differ only at
   the float-noise scale, not usefully.

## The measured explanation of the flat ln(3) pilot

1. The frozen encoder stage (projection → mean-pooling) maps all three
   option vectors to near-parallel directions (pairwise cosine deviation
   < 4e-8) for every record in both arms.
2. Therefore all three scores are equal to float32 noise (within-record
   spread ≤ 5.6e-9; median 0.0), and all 90 scores per arm sit in a
   ~2e-8-wide band around `0.02079586` — the module output is effectively
   constant across records.
3. Therefore softmax is uniform, cross-entropy is exactly ln 3 for every
   target, and the parameter gradients are float32 noise (1.7e-8…8.0e-8).
4. Attempt 010's digest-level weight movement is consistent with this:
   AdamW (lr 0.003, decay 0.0) converts even noise-level gradients into
   O(lr) sign-driven updates, so weights moved while the uniform scores —
   and the exact ln 3 loss — stayed.
5. Argmax sits at chance (12/30 and 10/30 vs 10/30).

## What this does and does not say

- It DOES answer the investigation: the repeated ln(3) flat losses are a
  measured property of the frozen input stage — the option representations
  collapse to one direction before the ^6 module can act on them. This is a
  measurement, not an inference.
- It does NOT say the ^6 module cannot learn whole-part reasoning. The
  module's capacity is not what this pipeline tests: the distinction never
  reaches it, and its output is a near-constant operating point here.
- No learning or capability claim follows. Any follow-up (e.g., a
  non-collapsing option representation, a different pooling, or a readout
  inside the permitted plasticity group) is a new experiment and needs new
  owner authorization.
- Frozen negatives `0/72`, accepted models, sealed splits, and the
  attempt-010 record are untouched.
