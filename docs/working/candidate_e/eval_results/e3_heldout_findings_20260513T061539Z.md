# Candidate E Stage 2 evaluation — `e3`

- checkpoint: `/workspace/tksCAS/stage_e3_20260513T043823Z/ckpt_final.pt`
- dev_path: `/workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_test.jsonl`
- source_swap_dev_path: `/workspace/tksCAS/cas-synthetic/data/eval/rpm_copy_grounding_v2_source_swap_eval.jsonl`
- max_cas_prefix_len: 192
- max_new_tokens: 192
- tf_mode legacy flag: False (TF eval is always run for the e2b gate)

## TF dev (teacher-forced identifier-level recovery — PRIMARY E2b GATE)

- records:                              200
- applicable rpm records:               200
- total target identifiers:             647
- total recovered identifiers (TF):     467
- identifier_recovery_rate (TF):        **0.7217928902627512** ← GATE METRIC
- full_recovery_rate (TF, strict):      0.49
- per_token_accuracy (TF, granular):    0.8937449228269699

Identifier-level (gate metric) credits a record-IDs as recovered iff
EVERY token in its STAGE_VAR span has correct argmax(p_copy) under TF.
Full-record (strict) requires ALL canonical identifiers in a record
recovered. Per-token is the most granular: fraction of in-span tokens
with correct argmax src.

## Dev free-decode (informational — slot-trace + drift evidence)

- records:                       200
- applicable rpm records:        200
- total target identifiers:      601
- total recovered identifiers:   387
- aggregate recovery rate:       0.6439267886855241
- full-recovery records:         80 / 200
- full-recovery rate:            0.4

Free-decode metrics measure what happens when the model generates its
own prefix — drift failure modes show here. TF/free-decode divergence is
the exposure-bias signature from the A/B/C/D postmortems.

## Source-swap pairs (swap fidelity)

- pairs:                              50
- pairs with full pass:               8
- pair pass rate:                     0.16
- pairs with cross-emission:          0
- total cross-emission count:         0
- pairs with partial recovery only:   42

## Gate semantics

**E3 enforces the Stage 3 post-training gate.** Per Codex audit
2026-05-13:

- PRIMARY (LOAD-BEARING): free-decode `identifier_recovery_rate >= 0.50`
- HARD SAFETY (LOAD-BEARING): swap `cross_emission_count == 0`
- Strong-pass annotation: `identifier_recovery_rate >= 0.70`
- Kill / redesign floor (informational): `< 0.30` means scheduled
  sampling did not solve exposure; move to DAgger or other design.

Evaluator exits non-zero if PRIMARY OR HARD SAFETY misses.

| gate | value | threshold | pass | load-bearing |
|---|---|---|---|---|
| **free-decode identifier_recovery_rate** | 0.6439 | 0.5000 | ✓ | **YES (E3 PRIMARY)** |
| **swap cross_emission_count** (HARD safety) | 0 | 0 (exact) | ✓ | **YES (E3 HARD SAFETY)** |
| free-decode identifier_recovery_rate (strong-pass annotation) | 0.6439 | 0.7000 | ✗ | annotation only |
| TF per_token_accuracy | 0.8937 | — | — | informational at e3 |
| swap pair_pass_rate | 0.1600 | — | — | informational at e3 |

**Context (not gated):**
- TF full_recovery_rate (strict whole-record): 0.49
- TF span failure modes: exact=467 (0.7217928902627512), wrong_start=30 (0.04636785162287481), right_start_drift=150 (0.23183925811437403)
- TF per-token off-by-one (of incorrect tokens): 285 (0.43577981651376146)

**Not yet implemented in this evaluator** (deferred per user
2026-05-12 evaluator-upgrade scope decision): slot F1 against
gold target slot tags, non-rpm leakage scoring against a non-rpm
dev subset. These extensions land in a follow-on PR; they are
NOT prerequisites for E2b launch, because exact-ID recovery and
wrong-pair leakage are the load-bearing E2b signals.
