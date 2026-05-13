# Candidate E Stage 2 evaluation — `e3-baseline`

- checkpoint: `/workspace/tksCAS/stage_e2c_cont_20260513T002539Z/ckpt_final.pt`
- dev_path: `/workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_dev.jsonl`
- source_swap_dev_path: `/workspace/tksCAS/cas-synthetic/data/path_d/rpm_copy_grounding_v2_source_swap_dev.jsonl`
- max_cas_prefix_len: 192
- max_new_tokens: 192
- tf_mode legacy flag: False (TF eval is always run for the e2b gate)

## TF dev (teacher-forced identifier-level recovery — PRIMARY E2b GATE)

- records:                              200
- applicable rpm records:               200
- total target identifiers:             648
- total recovered identifiers (TF):     428
- identifier_recovery_rate (TF):        **0.6604938271604939** ← GATE METRIC
- full_recovery_rate (TF, strict):      0.335
- per_token_accuracy (TF, granular):    0.923453566182471

Identifier-level (gate metric) credits a record-IDs as recovered iff
EVERY token in its STAGE_VAR span has correct argmax(p_copy) under TF.
Full-record (strict) requires ALL canonical identifiers in a record
recovered. Per-token is the most granular: fraction of in-span tokens
with correct argmax src.

## Dev free-decode (informational — slot-trace + drift evidence)

- records:                       200
- applicable rpm records:        200
- total target identifiers:      612
- total recovered identifiers:   270
- aggregate recovery rate:       0.4411764705882353
- full-recovery records:         39 / 200
- full-recovery rate:            0.195

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

**E3-baseline is the Stage 3 DECISION POINT.** It measures
free-decode behavior of the E2c-continuation checkpoint BEFORE
any Stage 3 training. Per Codex audit 2026-05-13:

- If `free-decode identifier_recovery_rate >= 0.50`: the model
  already clears the first free-decode bar. Do NOT train Stage 3 yet.
  Move to broader free-decode confirmation (test pack + swap_eval).
- If `< 0.50`: scheduled-sampling Stage 3 training is the next step.

Gates below are REPORTED but NOT enforced at e3-baseline; the
0.50 threshold is shown as the DECISION threshold, not a fail-exit.

| gate | value | threshold | pass | load-bearing |
|---|---|---|---|---|
| free-decode identifier_recovery_rate | 0.4412 | 0.5000 (decision threshold) | < | **DECISION POINT** (no fail-exit) |
| swap cross_emission_count | 0 | 0 (target) | ✓ | informational at baseline |
| TF per_token_accuracy | 0.9235 | — | — | informational |
| swap pair_pass_rate | 0.0400 | — | — | informational |

**Context (not gated):**
- TF full_recovery_rate (strict whole-record): 0.335
- TF span failure modes: exact=428 (0.6604938271604939), wrong_start=25 (0.038580246913580245), right_start_drift=195 (0.30092592592592593)
- TF per-token off-by-one (of incorrect tokens): 221 (0.47121535181236673)

**Not yet implemented in this evaluator** (deferred per user
2026-05-12 evaluator-upgrade scope decision): slot F1 against
gold target slot tags, non-rpm leakage scoring against a non-rpm
dev subset. These extensions land in a follow-on PR; they are
NOT prerequisites for E2b launch, because exact-ID recovery and
wrong-pair leakage are the load-bearing E2b signals.
