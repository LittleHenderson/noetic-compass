# Candidate E Stage 2 evaluation — `e2b`

- checkpoint: `/workspace/tksCAS/stage_e2b_full_20260512T172129Z/ckpt_final.pt`
- dev_path: `/workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl`
- source_swap_dev_path: `/workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl`
- max_cas_prefix_len: 192
- max_new_tokens: 192
- tf_mode legacy flag: False (TF eval is always run for the e2b gate)

## TF dev (teacher-forced identifier-level recovery — PRIMARY E2b GATE)

- records:                              200
- applicable rpm records:               200
- total target identifiers:             648
- total recovered identifiers (TF):     4
- identifier_recovery_rate (TF):        **0.006172839506172839** ← GATE METRIC
- full_recovery_rate (TF, strict):      0.0
- per_token_accuracy (TF, granular):    0.38387465317447367

Identifier-level (gate metric) credits a record-IDs as recovered iff
EVERY token in its STAGE_VAR span has correct argmax(p_copy) under TF.
Full-record (strict) requires ALL canonical identifiers in a record
recovered. Per-token is the most granular: fraction of in-span tokens
with correct argmax src.

## Dev free-decode (informational — slot-trace + drift evidence)

- records:                       200
- applicable rpm records:        200
- total target identifiers:      612
- total recovered identifiers:   192
- aggregate recovery rate:       0.3137254901960784
- full-recovery records:         31 / 200
- full-recovery rate:            0.155

Free-decode metrics measure what happens when the model generates its
own prefix — drift failure modes show here. TF/free-decode divergence is
the exposure-bias signature from the A/B/C/D postmortems.

## Source-swap pairs (swap fidelity)

- pairs:                              50
- pairs with full pass:               2
- pair pass rate:                     0.04
- pairs with cross-emission:          0
- total cross-emission count:         0
- pairs with partial recovery only:   48

## Gate semantics

**E2b enforces fail-exit gates** per design doc §Stage 2b.
Evaluator exits non-zero if any gate misses.

| gate | value | threshold | pass |
|---|---|---|---|
| **TF identifier_recovery_rate** (primary, design doc §Stage 2b) | 0.0062 | 0.8000 | ✗ |
| swap pair_pass_rate (free-decode, swap conditionality) | 0.0400 | 0.8500 | ✗ |

**Context (not gated):**
- TF full_recovery_rate (strict whole-record): 0.0
- TF per_token_accuracy (granular): 0.38387465317447367

**Not yet implemented in this evaluator** (deferred per user
2026-05-12 evaluator-upgrade scope decision): slot F1 against
gold target slot tags, non-rpm leakage scoring against a non-rpm
dev subset. These extensions land in a follow-on PR; they are
NOT prerequisites for E2b launch, because exact-ID recovery and
wrong-pair leakage are the load-bearing E2b signals.
