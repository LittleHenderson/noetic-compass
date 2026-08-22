# V26 — CAS-PINNED: the `^8`/`^9` role assignment IS read under proof-level surface control

**Date:** 2026-08-21 · `pythia-160m`, **attested engine**, CPU, **$0**. sha256 `2cf748b98343a761…`

## Design
The v25 instrument pointed at an actual CAS contrast. Canonical (Clarification 1): **`^8` Above/Cause = the Idea that TRIGGERS**; **`^9` Below/Effect = the Idea BROUGHT TO MIND**.

- **A:** `the {sensory} : triggered ; the {memory} : arrived ; done`  → sensory = `^8`
- **B:** `the {sensory} : arrived ; the {memory} : triggered ; done`  → memory = `^8`

The ` : ` and ` ; ` separators give both verbs identical local context. 12 pairs / 24 items, leave-one-PAIR-out.

| guarantee | status |
|---|---|
| word multisets identical | **0/12 mismatches** → bag-of-words FORCED `0.500` |
| char-ngram bags identical | **residual `0.000000`** → char-ngram FORCED `0.500` |
| position counterbalanced | sensory phrase in slot 1 in **BOTH** members |
| token-length artifact | **0/12** mismatches |

## Result
| | accuracy |
|---|---|
| bag-of-words | **`0.500`** (forced) |
| char-ngram | **`0.500`** (forced) |
| **activation, best layer** | **`1.000`** (L0) |
| activation, mean over 12 layers | **`0.962`** |

**Verdict: `CAS_8_9_ROLE_READ_UNDER_PROOF_LEVEL_CONTROL`.**

## What it establishes
The trigger-vs-arrival role assignment — the relation CAS names `^8`/`^9` — **is present in the model's activations and readable at `1.000`** under conditions where words, character n-grams, position and length are **provably uninformative**. The `0.962` mean across all 12 layers shows it is a broad signal, not one layer.

This is the strongest CAS-adjacent reading result in the record, and the **first** produced under proof-level control.

## The pre-registered skeptic objection (recorded BEFORE the result, and it stands)
A pass may be read as **ordinary syntactic/semantic role assignment that CAS has merely NAMED**. This test **cannot settle** that. What it settles is that the relation is present, readable, and measurable where cheating is impossible.

**Therefore: still NOT a CAS-specificity proof.** CAS-specificity remains `GREY`. What has changed is that the `^8`/`^9` relation is no longer *unmeasurable* — it is now measured, cleanly, with an unfakeable floor.

## Limits
- Best layer `L0` — if that is post-block-0, one attention pass suffices; real binding but **shallow**. Confirm engine layer indexing before any "deep structure" language.
- n = 12 pairs; one frame; `pythia-160m`; one seed. 6.9b untested (~$0.15).

## Claim state
- **Real:** all numbers, attested engine, `$0`. **Accepted:** none.
- **LICENSED:** *"Under proof-level surface control with position counterbalanced, the model's activations recover the `^8`/`^9` trigger-vs-arrival role assignment at `1.000` best-layer / `0.962` mean-over-layers."*
- **NOT LICENSED:** CAS-specificity; deep multi-layer composition.
