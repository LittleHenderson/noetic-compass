# V22 — Matched minimal pairs: the first PROVABLY beyond-lexical result — but it does not beat character-order

**Date:** 2026-08-21 · **Model:** `pythia-160m` (reserialized `d5861d32…`), **attested engine**, CPU, **$0**.
**Results file (co-located):** `detector_v22_minimal_pairs_results.json`, sha256 `3f3de94bec8bbc4e…`
**Why:** every reading result this session died because the stimuli were solvable from words alone (v19–v21). This builds the test the spec sheet has flagged as missing since **L3 (`INCONCLUSIVE BY DESIGN`)** — the sharpest available discriminator.

## Design — the guarantee is enforced in code
**Role-swap pairs with an IDENTICAL word multiset:**
- **A** (sensory cue is the trigger): *"The scent of pine tar pulled his whole childhood back up"*
- **B** (memory is the trigger): *"His whole childhood pulled the scent of pine tar back up"*

Same words, different structure. **A bag-of-words model is mathematically forced to tie at chance; a hand lexicon is forced to tie.** Only a reader sensitive to order/role can split them. 12 pairs (24 items); the multiset identity is **verified in code with an abort** (`all 12 pairs have IDENTICAL word multisets`). Protocol: **leave-one-PAIR-out** nearest centroid (the held-out pair's two sentences are never in training).

## Results (exact)
| model | accuracy | note |
|---|---|---|
| **bag-of-words baseline** | **`0.500`** | **exactly chance — the construction guarantee HELD** |
| char-ngram (n=2,3,4) baseline | **`0.875`** | char n-grams capture local word ORDER, so they detect the swap |
| **activation (best layer)** | **`0.917`** (L2) | mean over all 12 layers `0.813` |

**Verdict: `ABOVE_CHANCE_BUT_UNDER_GATE`** — clears the `0.70` bar but beats char-ngram by only `+0.042`, under the `+0.15` margin required.

## What this establishes — and what it does not

**ESTABLISHED (a genuine first for this session): the model's activations carry information that words alone provably cannot supply.** Bag-of-words is pinned at `0.500` **by construction**, and the activation detector reaches `0.917`. Every prior result died to a lexical rule; **this one cannot, as a matter of arithmetic.** The lexicon attack that killed v19/v20/v21 is structurally defeated here.

**NOT ESTABLISHED: that this is *structural/role* reading rather than surface word-order statistics.** Char n-grams — still a surface model, just an order-sensitive one — reach `0.875`, only `0.042` below the activations. So the honest statement is **"beyond bag-of-words (proven), NOT beyond character-order n-grams."**

**A further honest mark against the deep-structure reading: the best layer is `L2` of 12 — a very early layer.** The spec sheet already flags early-layer peaks as consistent with near-surface feature reading (the 20B 40E headline peaked at layer 2 of 44 and was caveated for exactly this). An early-layer peak is what you would expect from local order statistics, not from deep role representation.

## Where this leaves the reading track
- Bag-of-words / hand-lexicon attacks: **defeated** (first time all session).
- Character-order surface model: **not defeated** (`+0.042`).
- So the reading track moves from *"explicable by word lists"* (v21, a clean negative) to *"requires at least word-order sensitivity — but not yet shown to require anything more."* **That is real progress and an honest, narrow claim.**

## Next tests that would separate role-structure from word-order
1. **Order-matched controls:** pairs where the *same* local bigrams/trigrams appear in both members (e.g. swap roles via case/preposition marking rather than by moving the noun phrases), so char n-grams are forced toward tie as well.
2. **Longer-range swaps:** put the swapped constituents far apart so local n-grams cannot span the dependency.
3. **Scale it:** re-run at 6.9b — if the activation margin over char-ngram grows with scale while char-ngram stays flat, that is evidence for genuine structural reading. (~$0.15, one A40.)
4. Larger n than 12 pairs.

## Claim state
- **Real:** all numbers, real `pythia-160m` weights through the **attested engine**, `$0`. **Accepted:** none.
- **LICENSED (narrow):** *"On matched minimal pairs where a bag-of-words model is provably at chance, the model's activations classify the role-swap at `0.917`."*
- **NOT LICENSED:** that this is CAS-specific, or that it is role/structure reading rather than word-order statistics.
- CAS-specificity remains `GREY`.
