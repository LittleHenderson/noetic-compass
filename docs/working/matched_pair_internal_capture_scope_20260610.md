# Matched-pair internal capture (the live detector) — scope + feasibility verdict

**Date:** 2026-06-10  ·  **Status: SCOPE + FEASIBILITY.** This is the only path to a "catch the hijack in the activations before it speaks" claim. Honest verdict up front: **the clean version is NOT feasible on Qwen2.5-1.5B; the tractable approximations carry confounds. Do not spend on a naive capture — it will repeat v4.**

## What a clean live detector requires (and why)
To read internal comply/refuse from activations *without* the two confounds that have sunk every prior run, you need ALL of:
1. **Matched on prompt** — COMPLIED and REFUSED on the **same** prompt (else the probe reads *which payload*, the v1/v3 confound).
2. **Read pre-generation (W0)** — at the prompt-final position, *before* any token is generated (else the probe reads the surface refusal tokens — the **Path B leakage**: layer-0 AUC ≈ 1.0).
3. **n ≥ 40 matched prompts** (each contributing ≥1 comply and ≥1 refuse), per the frozen v4 group floor.

## Why the naive run is infeasible on Qwen (already proven)
- **v4** sampled K=16 completions on 44 borderline prompts → under consensus labeling only **17 REFUSED / 704**, and only **G_matched = 2** prompts produced both labels. Qwen2.5-1.5B simply does not flip on the *same* prompt often enough; its refusals on borderline extraction prompts are rare and disputed.
- So requirement (1)∧(3) cannot be met by sampling this model. A bigger sweep buys a near-linear trickle of matched pairs at large GPU cost — not worth it.

## The tractable options, and their costs
| Option | Gets matched pairs? | Confound | Verdict |
|---|---|---|---|
| A. More sampling on Qwen (K↑, more prompts) | barely (≈linear trickle) | none new | expensive, ~doomed (v4 showed the rate) |
| B. **Condition-nudge** — same payload ± a system nudge that flips refusal; read at **W0** | yes, reliably | the **nudge text** is in the prompt, so W0 encodes it → reads "which condition," not pure stance | runnable but confounded ("diagnostic only", per roundtable) |
| C. **A more-refusing model** (safety-tuned ≥7B) that flips on the same borderline prompts | yes | cross-family (new probe / Gate-A needed) | most promising, but a new model + new Gate-A probe build |
| D. Within-payload-class slice of existing data (e.g. v1 `overt_5`: 7 comply / 5 refuse, same class) | partial (same class, not same prompt) | residual within-class payload variation; n≈12 | too small to conclude, but a free sanity check |

## Recommendation
1. **Do NOT run a naive Qwen matched-pair capture.** It is the v4 trap.
2. **Cheapest informative step (free, now):** run option **D** — internal-P at W0 on the v1 `overt_5` (and other overlap-class) subsets where the SAME payload class has both labels. n is tiny (~12–20), so it can only *suggest*, not confirm — but it is the one payload-controlled internal read available from data we already have, and costs nothing.
3. **The real build, only if the live claim is worth it:** option **C** — pick a safety-tuned model that genuinely flips on borderline extraction prompts, train its Gate-A probe, then run the v4 matched-sampling design (W0 control + group CV) on it. This is a multi-week build (new model, new probe, new capture), justified only if "live interception" is a required product claim.

## Option D executed (the free within-class check) — result: CHANCE
Ran it: 3 v1 payload classes have both labels (overt_5 7c/5r, overt_4 1c/9r, overt_11 8c/1r) = 31 traces with payload controlled. Class-centered internal-P (probe ^2−^3): **comply-vs-refuse AUC = 0.562 (prompt-state), 0.508 (window)** — chance. So once payload is controlled, the probe's internal polarity carries **no** comply/refuse signal (the earlier uncontrolled prompt-state 0.615 was the payload confound). n is small (inconclusive in the strict sense), but it points the same way as every other clean test: **no internal signal survives payload control.**

## Bottom line
The **live internal detector is gated on data Qwen-1.5B cannot supply** — and every clean read (window 0.486, within-class-controlled 0.56, Path B = leakage) says the comply/refuse signal is simply **not linearly present in this model's activations** via the current probe. The honest near-term capability is the **output-side recipe audit** (working, shippable). The live detector is *future work conditional on a more-refusing model* — not a quick win, and not worth burning GPU on the Qwen matched-pair capture that v4 already showed yields ~2 pairs.
