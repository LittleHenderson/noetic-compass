# V16 — SCALE CAUSAL: is the valence direction a causal LEVER at 6.9b? (PAID A40) — YES

**Date:** 2026-08-21 · **Model:** `EleutherAI/pythia-6.9b` (32 layers, 4096 hidden), `transformers 5.15.1`, `torch 2.8.0+cu128`, fp16 CUDA.
**Hardware:** owner-authorized paid RunPod **A40** (`$0.44/hr`, hard 22-min watchdog, pod `j9h3dor7g90hcc` verified `EXITED`). Direct transformers forward hooks — **NOT** the attested engine (canary still `NOT RUN`).
**Results file (co-located):** `detector_validation_v16_scale_causal_pythia69b_results.json`, sha256 `fdf2f1103f599f1c…`

## The question (and why v10/v14 came out null)
v8 (160m) showed the valence direction is **causally load-bearing** — injecting it steers output valence. v10/v14 tried the same at 6.9b and got a **null** — but at a **fixed injection norm α=6.0**. At 6.9b the natural valence direction has norm ~23–40 and the typical residual norm is ~97–250, so **α=6.0 was a negligible nudge.** The fix: inject the **natural-magnitude** direction `w_raw = mean(explicit-pos) − mean(explicit-neg)` and **sweep a multiplier ×1→×8**, at two layers, against a **norm-matched random-direction null** (K=8).

## Result — CAUSALLY LOAD-BEARING AT SCALE

**L16 (mid layer) — strong, clean, monotonic:**

| inject | swing (valence margin) | per-prompt | null mean±std (max\|·\|) | z over null | beats null max |
|---|---|---|---|---|---|
| ×1 (‖·‖ 40.3) | **3.692** | 4.74 / 3.14 / 2.35 / 4.55 | −0.19 ± 0.35 (0.73) | **11.18** | yes |
| ×2 (‖·‖ 80.6) | 5.556 | all positive | 0.41 ± 0.58 (1.59) | 8.86 | yes |
| ×4 (‖·‖ 161) | 7.259 | all positive | 0.55 ± 1.32 (2.04) | 5.07 | yes |
| ×8 (‖·‖ 322) | 10.851 | all positive | −0.32 ± 2.81 (4.99) | 3.98 | yes |

**At every multiplier**, L16 injection raises output valence on **every one of the 4 neutral prompts**, the swing rises monotonically with strength (3.69 → 10.85), and it beats the norm-matched random null's max at every step. At the **natural magnitude (×1)** the effect is **z=11.18** over the null.

**L6 (the valence-readable layer) — weaker lever:** null at ×1 (z=0.6), reaches z=3.05 at ×4 (swing 1.383, directional, beats null max), washes out at ×8 (z=0.7 as random directions also perturb at large norm). So the direction *reads* at L6 but *steers* far more effectively at L16.

## What it means

**The valence direction is not just correlational — injecting it causally steers the model's output at scale.** The v10/v14 null is fully explained: it was an under-scaled-injection artifact, not evidence against causal sufficiency. At natural magnitude the direction is a **strong, directional, monotonic lever** (z=11.18 at L16 ×1), robust across the entire ×1→×8 sweep.

**Both halves of Claim B now have real evidence at 6.9b scale:**
- **Measurement (reading):** valence, Operator-10, Domain-4 all beat the char-ngram surface control at 6.9b (v10/v14/v15); `^8`/`^9` marginal.
- **Correction (steering):** the valence direction causally moves output valence, z=11.18 over a matched-random null (this run).

So CAS-as-a-measurement-**and-correction**-language (Claim B) is supported on real weights at scale for the valence axis on *both* halves.

## Claim state
- **Real:** all numbers, real pythia-6.9b weights via direct transformers on a paid A40. **Accepted:** none — research-grade.
- **Not the attested engine / not the canary:** direct transformers; frozen canary still `NOT RUN`.
- **Strong positive:** valence steering at L16, z=11.18 at natural magnitude, robust across the sweep.
- **Honest scope:** this is **sufficiency** (inject → steer), NOT **necessity** (ablate → remove; the direct-hook path adds, it doesn't project-out). n=4 neutral prompts; K=8 null (z is the honest measure, not a K-limited p-value); swept 2 layers × 4 multipliers and report the whole grid — L16 is robust across all four multipliers, so the result is not best-of selection luck. Valence only; other axes' causal steering not tested.
