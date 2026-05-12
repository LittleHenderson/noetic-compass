# Candidate E Stage 2 evaluation — `e2a`

- checkpoint: `/workspace/tksCAS/stage_e2a_warmup_20260512T150330Z/ckpt_final.pt`
- dev_path: `/workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl`
- source_swap_dev_path: `/workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl`
- max_cas_prefix_len: 192
- max_new_tokens: 192
- tf_mode: False (False = free-decode)

## Dev (canonical recovery)

- records:                       200
- applicable rpm records:        200
- total target identifiers:      612
- total recovered identifiers:   0
- aggregate recovery rate:       0.0
- full-recovery records:         0 / 200
- full-recovery rate:            0.0

## Source-swap pairs (swap fidelity)

- pairs:                              50
- pairs with full pass:               0
- pair pass rate:                     0.0
- pairs with cross-emission:          0
- total cross-emission count:         0
- pairs with partial recovery only:   50

## Gate semantics

**E2a is warmup.** Identifier recovery is expected near 0 because
copy is off (loss_weight `copy=0.0`). Metrics are informational —
they inform L_span / L_contrastive_margin / L_coverage design
for Stage 2b. The gate the warmup must clear is LM/slot-head
stability, NOT recovery; inspect `slot_type_trace`,
`longest_stage_var_run`, and `stage_var_token_count` per record
in the JSON report.

**E2b is NOT implemented in this evaluator.** When the Stage 2b
loss PR lands, this evaluator must be extended with TF recovery,
slot F1, non-rpm leakage scoring, and fail-exit thresholds
(≥80% / ≥85% / ≥90% / 0). Until then `--stage e2b` raises.
