# Causal Attention-Knockout Hallucination Detector — Findings

**Date:** 2026-06-19
**Verdict:** Mechanism WORKS (clean existence-check GO); as a detector it does **NOT clear the license gate** (+0.15 margin / residual proof). Best result of the effort; honest short of license.

## What was run (real, on the pod)
The #1 panel detector: sever attention from the answer-value position to the trusted-evidence
span at a mid-layer band, measure the answer-value token's probability drop = **GME**
(Grounding Mediation Effect). Run teacher-forced on the **existing balanced generations**
(`gen_hard_v2`, Qwen2.5-0.5B, stale_majority_vote, **95 SUPPORTED / 96 UNSUPPORTED**) — the
*exact set where the correlational W0→W1 probe failed* (negative margin). bf16 + eager attention.
Scripts: `knockout_from_generations.py`, `knockout_existence_check.py` (hook). Report:
`docs/working/knockout_gen_mv_full.json`.

Two real bugs fixed en route: **float16 → bfloat16** (Qwen2.5 emits `!!!!` garbage in fp16),
and an **off-by-one in the knockout query** (teacher-forcing reads logits at `answer_pos−1`, so
that is the query whose attention must be severed).

## Results
Existence check — a clean **GO**:
- mean GME(SUPPORTED) = **0.279** vs mean GME(UNSUPPORTED) = **−0.002**, Cohen's d = **1.36**.
- evidence-span GME = **0.138** vs random-span placebo = **−0.002** → effect is evidence-specific.
- GME-only balanced accuracy = **0.958**.

License gate — **falls short**:

| Test | GME BA | answer-text baseline | margin (need +0.15) |
|---|---|---|---|
| in-sample | 0.958 | 0.926 | +0.03 |
| held-out-topic | 0.919 | 0.852 | +0.067 |
| value-disjoint (GroupKFold by value) | 0.936 | 0.885 | +0.051 |
| **residual** (GME after regressing out answer-text) | **0.446 (chance)** | — | fails |

## Honest reading
- The **causal mechanism is real**: you can verify grounding by knocking out the evidence edge;
  grounded answers collapse, fabricated ones don't. This is the first thing in the whole effort
  that produces a clean, evidence-specific causal separation — and it does it on the set where
  correlational probes went negative.
- **But it does not license as a deployed detector.** It beats text only by +0.03 to +0.07 (never
  +0.15), and the residual proof is chance — because once the model has emitted the value, the
  value-text carries most of the grounded/fabricated label, so "read the answer" is a strong
  baseline that the causal signal only modestly exceeds. The wall is deeper than "the prompt
  predicts it": the *emitted value* predicts it.

## What this is good for / where it could still license
- **As an interpretability / grounding-verification tool**, GME is genuinely useful (does this
  specific answer causally depend on the cited evidence? — d=1.36, 0.94–0.96 BA).
- A license under the strict gate would require a setting where the detector does **not** get to
  read the answer value — i.e., a **pre-emission** causal signal (steer/clamp before the value
  token, measure abstention/flip), or a **value-blinded** evaluation. Those are new experiments;
  this result says the *post-hoc* causal detector, while real, is bounded by the value-text baseline.

Gate status unchanged: hallucination detection remains `OPEN / NOT LICENSED`. No fabrication.
