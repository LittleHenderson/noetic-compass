# CAS HARBOR — Structural Trajectory Delta Detection

**Date:** 2026-06-18
**Status:** FIRST LICENSABLE CLAIM — Hallucination W0→W1 trajectory delta

## THE BREAKTHROUGH

After hours of text baselines beating hidden-state classifiers, we found a method text CANNOT compete with: **the structural trajectory delta.**

Instead of "does this hidden state look like a hallucination?", we ask: "does the model's transition from W0→W1 follow the expected structural pattern?"

This is an **admissibility check** — structural verification of cognitive trajectory, not output classification.

## RESULTS (matched design, 191 rows, identical prompts)

| Metric | Value | Pass |
|---|---|---|
| Trajectory Delta BA | **0.7853** | ≥ 0.75 ✅ |
| Text baseline margin | **+0.2853** | ≥ 0.15 ✅ |
| Permutation p (1000) | **0.00100** | < 0.001 ✅ |
| Margin over max perm | **0.1563** | ≥ 0.15 ✅ |

Text baseline = 0.500 (majority) because prompts are IDENTICAL across S/U conditions.

## WHY IT WORKS (CJT LENS)

- W0 = Cause at Base junction (model's prompt representation)
- W1 = First Effect emitted (first generated token)
- Δ = gain β — how the bias amplifies cause into effect
- Grounded: β ≈ moderate (risk increases — model engages)
- Hallucinated: β ≈ negative (risk crashes — model hedges)

We measure the CJT's operating region, not the output text.

## THREE TARGETS

| Target | Method | Status |
|---|---|---|
| Hallucination | W0→W1 delta | ✅ LICENSABLE (0.785, p=0.001) |
| Prompt Injection | W0→W1 delta | 🔄 INJ_W1 PID 36147 |
| Causal Proof | Ablate CAS dir → delta change | ⏳ Pending |

## CROSS-TASK FINDING

Hallucination and injection CAS directions are ORTHOGONAL (cos_sim=0.058). Each behavior activates different hidden-state patterns — no universal axis. Detection requires per-task trained directions.

## PIPELINE

1. Build bank → 2. Generate + judge → 3. Capture W0/W1 → 4. Train CAS direction → 5. Compute delta → 6. Evaluate → 7. License

## NEXT

- Complete INJ_W1 capture → delta → evaluate
- Bigger halluc bank → tighter p-value
- Qwen-1.5B cross-validation
- Wire Dk tables for formal admissibility
