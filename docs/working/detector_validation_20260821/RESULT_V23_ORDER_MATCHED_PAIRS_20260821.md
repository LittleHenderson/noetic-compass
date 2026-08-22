# V23 — Order-matched pairs: BOTH surface baselines provably pinned at chance, model scores 1.000

**Date:** 2026-08-21 · **Model:** `pythia-160m`, **attested engine**, CPU, **$0**.
**Results file (co-located):** `detector_v23_order_matched_results.json`, sha256 `e3941d3e953f0767…`

## Design — two guarantees, both verified in code
Role-swap inside a **symmetric frame**, so the difference sits at a range longer than the n-gram window:
- **A:** *"the scent of tar came first and the memory of childhood came second"*
- **B:** *"the memory of childhood came first and the scent of tar came second"*

A bag of n-grams records *which* n-grams occur, not which were adjacent to which. Both sentences contain one `came first`, one `came second`, and both noun phrases — so the bags are identical.

**Verified:** word multisets identical in all 12 pairs; **char-ngram bag residual = `0.00000` (mean and max)** — the bags are *exactly* identical. Both baselines are **forced** to chance by construction, not merely observed at chance.

## Results (exact) — 12 pairs / 24 items, leave-one-PAIR-out
| model | accuracy |
|---|---|
| bag-of-words baseline | **`0.500`** (forced) |
| char-ngram (n=2,3,4) baseline | **`0.500`** (forced, residual `0.00000`) |
| **activation, best layer** | **`1.000`** (L3) |
| activation, mean over all 12 layers | `0.938` |

**Verdict: `ORDER_STRUCTURE_READ_BEYOND_SURFACE`** — clears the gate (≥`0.70`, and beats *both* surface baselines by `+0.500`).

## What this establishes
**The model definitively uses information that NO bag-of-features model can access.** This is the first stimulus set in the session where *both* surface baselines are pinned at chance **as a matter of arithmetic** — and the activations classify **perfectly (24/24)**. Every earlier result died to a lexical or n-gram rule; **this one cannot**, by construction. The `0.938` mean across *all* layers (not just the best) shows the signal is broad, not a single-layer artifact.

**This also validates the METHOD.** The harness now has a stimulus-design pattern — matched multiset + matched n-gram bag — under which surface confounds are *provably* eliminated rather than argued about. That pattern is reusable for every axis, and it is the answer to the v19–v21 collapse.

## The honest bound — what it does NOT establish
**The discriminating information is POSITIONAL, and positional reading is shallow.** By construction, class A = *sensory noun in slot 1*, class B = *memory noun in slot 1*. To solve this the model only needs "which type of noun phrase appears first" — position plus noun identity. **Any transformer has positional encoding; this is not evidence of deep role or semantic-structure representation.** The early best layer (`L3` of 12) is consistent with that shallow reading, matching the sheet's standing caution about early-layer peaks.

**It is also not clearly a CAS construct.** The task as built is "which entity is in position 1," not "which entity is the `^8` trigger." The `^8`/`^9` framing motivated the sentences, but the *discriminative* signal is positional. **No CAS-specificity claim is licensed.**

**Other limits:** n=12 pairs / 24 items; one frame template reused across all pairs; one model; 160m only.

## Where this leaves the reading track
| stage | status |
|---|---|
| v21 | every reading result explicable by word lists — **clean negative** |
| v22 | beyond bag-of-words (proven), **not** beyond char-order (`+0.042`) |
| **v23** | **beyond BOTH bag-of-words and char-n-grams (both provably pinned), `1.000`** — but the signal is **positional**, not shown to be role/semantic |

## The next test that would separate positional from role reading
**Counterbalance position out of the label.** Build pairs where the sensory noun appears in slot 1 in *both* members, and the role flips by some other means (voice, marking, or an explicit trigger verb), so that position is uninformative and only genuine role semantics can solve it. If activations still separate, that is role reading; if they drop to chance, v23 was positional — which is the honest expectation to hold until tested.

## Claim state
- **Real:** all numbers, real `pythia-160m` through the **attested engine**, `$0`. **Accepted:** none.
- **LICENSED (narrow but solid):** *"On pairs where bag-of-words and char-n-gram models are provably pinned at chance, the model's activations classify the ordering at `1.000` (best layer) / `0.938` (mean over layers)."*
- **NOT LICENSED:** deep role/semantic-structure reading; any CAS-specific claim. CAS-specificity remains `GREY`.
