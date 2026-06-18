# W0 Prompt-Injection Causal Proof — Design + Gates

Date: 2026-06-18
Status: **DESIGN ONLY — `causal_proof` OPEN / NOT LICENSED.**

## Goal

Show that a hidden direction associated with prompt-injection *compliance*
is **causal**: intervene on it (add / ablate) before generation and observe a
behavior change, against matched controls.

## Existing infrastructure (reusable)

The live worker already has a real single-target causal harness:

- `live-trace-worker/app/runtime/ablation_probe.py`
  - `run_real_ablation_effect(...)` — hooks a target layer's MLP, ablates a unit
    at the last token, measures the logit/behavior effect on loaded weights.
  - `run_real_ablation_control(...)` — measures selectivity vs **random
    same-layer controls** (the matched-control requirement).

This is the right shape. What is missing is (a) a *direction* to intervene on and
(b) a dataset where the effect is not a surface artifact.

## Hard prerequisite created by the 2026-06-18 downgrade

The obvious candidate direction — the layer-18 logistic-probe weight vector — is
**disqualified as-is**, because that readout did not beat a character-level
surface control. Intervening on a surface-confounded direction would prove only
that we perturbed surface-token processing, not injection-compliance.

Therefore causal proof requires, IN ORDER:

1. A **surface-indistinguishable dataset** (PRESENT/ABSENT matched in both
   word- and char-level text controls; both at chance, hidden still separates).
2. A **re-licensed** internal W0 readout on that dataset (passes the 15-gate
   battery incl. `char_text_margin_pass`).
3. The probe direction from (2) used as the intervention vector.

## Causal protocol (once 1–3 hold)

1. Add `+α·d` / `−α·d` (d = unit-norm licensed direction) at the target layer,
   pre-generation, across α sweep.
2. Measure compliance/refusal behavior change with CI.
3. Matched controls (must NOT reproduce the effect):
   - random same-layer direction (`run_real_ablation_control` style),
   - orthogonal-to-`d` direction of matched norm,
   - shuffled-label direction.
4. Pass = behavior changes monotonically with α on the true direction and the
   matched controls do not, with a pre-registered effect size + CI.
5. WORM/verifier receipt records the result.

## Status

`causal_proof` is `OPEN` / `NOT LICENSED`. It is now **blocked on the W0
re-license** (which is itself blocked on a surface-indistinguishable dataset).
The intervention/control machinery exists; the validated direction and dataset
do not.
