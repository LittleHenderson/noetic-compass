# Causal steering test — ^2−^3 direction does NOT pass its controls (clean negative)

**Date:** 2026-06-11  ·  **Status: EXPLORATORY, NEGATIVE.** The pre-registered PASS required a signed, monotone comply↔refuse flip that beats the norm-matched random direction AND survives refusal-token-unembedding orthogonalization AND holds a fluency floor. It did not.

## Setup
Qwen2.5-1.5B, steer at the prompt-final residual (block 13, BEFORE any token generated). Direction d = probe CO-2 minus CO-3 (polarity calibration, NOT comply/refuse labels). Controls: norm-matched **random** direction; **orth_polarity** = d projected off the refusal-token unembedding (cos(d,d_orth)=0.996, so d is already ~orthogonal to "I cannot"). 44 borderline prompts × 3 directions × 9 α-levels (−4..+4 × residual norm). Convention: −α pushes CO-3/refuse, +α pushes CO-2/comply. Data archived `D:\tksCAS-archive\steering_causal_20260611\`.

## Result — refuse-rate vs α
```
alpha:        -4.0  -2.0  -1.0  -0.5  +0.0  +0.5  +1.0  +2.0  +4.0
polarity      0.02  0.68  0.68  0.59  0.68  0.52  0.39  0.05  0.14
random        0.07  0.41  0.82  0.77  0.68  0.30  0.32  0.39  0.36
orth_polarity 0.02  0.61  0.68  0.57  0.68  0.66  0.55  0.07  0.25
mean gen_len (polarity): 55 47 57 56 59 53 58 61 51   (random −4 collapses to 32)
```
Baseline refuse-rate (α=0) = 0.68.

## Verdict: FAIL the pre-registered bar
1. **Not signed-monotone.** Pushing toward CO-2 (+α) *does* lower refusal (0.68→0.05 at +2, fluent gen_len 61) — a hint. But pushing toward CO-3 (−α) does **nothing** (flat 0.68 at −0.5/−1/−2); the effect is one-sided, not the symmetric dose-response a causal axis predicts.
2. **Does not beat the random control.** The norm-matched random direction shifts refuse-rate as much or more (swing −4↔+4: random 0.30 vs polarity 0.11; at −1 random 0.82 vs polarity 0.68). With n=44 (SE ≈ 0.075) the polarity-vs-random differences are within noise. So the shift is a **generic residual-perturbation effect, not specific to the ^2−^3 direction.**
3. **Extremes are fluency-confounded.** At |α|=4 gen_len drops (random −4 → 32); the near-zero refuse-rates there are likely broken/gibberish output counted as "not refused," not steered compliance.
4. orth_polarity ≈ polarity (expected, cos 0.996) — moot, since polarity itself didn't pass.

## Honest conclusion
**No causal proof that the ^2−^3 direction controls Qwen's comply/refuse branch.** The control rig did its job — it caught the non-specificity (random moves comparably) and the fluency confound, so we did **not** false-positive. Combined with the detection half (leakage + within-class chance + underpowered), the marketable pre-speech/causal claim is **NOT achieved on Qwen-1.5B via the ^2−^3 direction.** The output-side audit remains the only working capability.

## What this does NOT rule out (the live follow-ups)
- **The DRIVE axis** (the team's actual best bet, orthogonal to the falsified ^2−^3) was NOT tested — it needs a drive-contrast readout direction (the Gate-A probe only gives the 10 Noetics). A drive probe + steering is the next causal attempt.
- **A more-refusing model** — both the weak +α hint and the detection flicker (typed-profile 0.806/p=0.005, n=10) would be settled with matched within-class data a more-refusing model supplies.
- The weak asymmetric +α→less-refusal hint is worth a powered re-test (more prompts, mid-α fluent range only), but does NOT meet the bar today.
