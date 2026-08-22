# V17 — SCALE CAUSAL OPS: do Domain/Operator directions steer? (PAID A40) — a CAUTION, not a win

**Date:** 2026-08-21 · **Model:** `EleutherAI/pythia-6.9b`, direct transformers, fp16 CUDA. Paid A40 (`$0.44/hr`, pod `g0za4pqxzhlcks` verified `EXITED`). **NOT** the attested engine (canary still `NOT RUN`).
**Results file (co-located):** `detector_validation_v17_scale_causal_ops_pythia69b_results.json`, sha256 `5a7bdcae358722ef…`
**Verified by a 2-lens adversarial pass (numbers CLEAN; circularity ISSUES_FOUND, 3 BLOCKERs). The draft "Domain and Operator directions are causal levers — Claim B broadened to 3 axes" is WITHDRAWN. This is the corrected, bounded record.**

## What was run
For two contrasts, build `d = mean(A resid) − mean(B resid)` at a layer, inject ±d at natural magnitude ×1→×8, measure the A-vs-B **output-token margin** swing on 4 neutral prompts vs a K=8 **norm-matched random** null. Domain: P `{must,should,ought,shall}` vs O `{first,then,next,step}`. Operator: `^2` `{good,great,love,wonderful}` vs `^3` `{bad,awful,hate,terrible}`.

## Raw numbers (exact, all confirmed)
- **Domain P vs O, L16:** swing ×1 `+2.226` (z `5.41`, beats null max `0.773`), ×2 `+4.679` (z `3.62`), ×4 `+5.100` (z `2.49`), ×8 `+5.991` (z `2.09`) — directional on all 4 prompts, roughly dose-monotone. **L6: no clean effect** (z<1.2).
- **Operator ^2 vs ^3, L16:** swing ×1 `+1.840` (z `4.44`), ×2 `+2.068` (z `4.03`, not all-positive), ×4 `+1.240` (z `0.71`), ×8 `+1.062` (z `0.33`) — **washes out by ×4, non-monotone. L6: no clean effect.**

## What this DOES and does NOT show (the load-bearing part)

**DOES:** a diff-in-means direction between deontic (must/should) and procedural (first/then) sentences, injected at **layer 16 of 32**, **direction-specifically (vs norm-matched random)** raises deontic-modal output vocabulary over sequential vocabulary, roughly dose-monotone. Real, and it beats a random direction cleanly.

**DOES NOT** — three BLOCKER reasons the CAS-construct claim is unlicensed:
1. **Circular/lexical readout.** The measured output tokens ARE the defining vocabulary of the input classes. Injecting a direction that encodes "these words vs those words" and watching those words rise is near-tautological — the construct labels "Domain"/"Operator" do no work beyond the word lists. This is generic token promotion, not evidence of a CAS construct.
2. **Random is the wrong null for a construct claim.** Beating a norm-matched random direction shows specificity-vs-random (random gaussians are near-orthogonal to any feature — an easy bar). It does NOT show specificity-vs-arbitrary-topical-steering. **No structured non-CAS null was run** (a diff-in-means between two other arbitrary topically-distinct sentence sets, read on their own tokens).
3. **`^2`/`^3` is valence relabeled.** good/great/love vs bad/awful/hate = sentiment; this reproduces the v16 valence lever, it is **not** an independent second axis.

**Also bounded:** effects are **mid-layer only** (L16, absent at L6); Operator **washes out by ×4 and is non-monotone** — a fragile point effect at natural magnitude, not a controllable "lever." And `z` (K=8 null, n=4 prompts) is a **screening heuristic**, not calibrated significance — read it as "exceeds all 8 random controls," not "5σ."

## Verdict — DIRECTION-SPECIFIC (vs random), NOT CONSTRUCT-LICENSED

This does **not** broaden Claim B. It is a **caution**: the causal-steering method, applied with definitional-token readouts and a random-only null, yields "positive" numbers that do **not** establish CAS-specificity. **CAS-specificity stays `GREY`.** It even slightly bounds v16 retroactively — v16's valence readout tokens (good/great/wonderful/amazing) partly overlap the input vocabulary, so v16 is best stated as "the valence direction steers valence output, direction-specific vs random" (standard steering-vector claim), not "CAS-valence-construct-specific."

## The honest follow-up (what would actually license a construct claim)
- A **structured non-CAS null**: diff-in-means between two arbitrary topically-distinct sentence sets, read on their own characteristic tokens. CAS contrasts must beat *that*, not just random.
- A **non-definitional readout**: does the Domain direction raise obligation-*framed continuations* that avoid the four modal words?
- Larger K (≥100) and more neutral prompts to calibrate the null and characterize prompt variance.

## Claim state
- **Real:** all numbers, real pythia-6.9b weights, direct transformers. **Accepted:** none.
- **Not a positive for CAS-specificity:** direction-specific-vs-random only; construct claim unlicensed.
- **Not the attested engine / not the canary.**
