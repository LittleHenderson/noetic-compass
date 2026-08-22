# V25 — ROLE BINDING READ: survives position counterbalance AND a proof-level surface match

**Date:** 2026-08-21 · `pythia-160m`, **attested engine**, CPU, **$0**. sha256 `9225319e8f519f67…`

## Design — every cheat removed, verified before the model loaded
- **A:** `the {sensory} came before ; the {memory} came after ; done`
- **B:** `the {sensory} came after ; the {memory} came before ; done`

12 pairs / 24 items, leave-one-**PAIR**-out.

| guarantee | status |
|---|---|
| identical word multisets | **0/12 mismatches** → bag-of-words FORCED to `0.500` |
| identical char-ngram bags | **residual `0.000000`** (mean & max) → char-ngram FORCED to `0.500` |
| position counterbalanced | sensory phrase in slot 1 in **BOTH** members → position is uninformative |
| no token-length artifact | **0/12** token-length mismatches; identical positions; first differing token is exactly the `before`/`after` swap |

**A BLOCKING PRE-FLIGHT GATE enforced this before loading the model** and **rejected two earlier designs at `$0`** (v24 residual `0.02776`; v25a residual `0.004626`, leaking `e ; ` vs `r ; ` because the sentence-final `;` had no trailing character — fixed by appending `done`).

## Result
| | accuracy |
|---|---|
| bag-of-words | **`0.500`** (forced) |
| char-ngram (n=2,3,4) | **`0.500`** (forced) |
| **activation, best layer** | **`1.000`** (L0) |
| activation, mean over 12 layers | **`0.917`** |

**Verdict: `ROLE_BINDING_READ` — survives position counterbalance AND surface match.**

## What this establishes
The only information distinguishing A from B is **which phrase the temporal marker binds to**, across a long-range dependency. Words, character n-grams, position, and sentence length are all **provably uninformative**. The activations classify it **perfectly**.

**This is the first result in the record where the model demonstrably tracks *which thing goes with which* rather than *what is present*.** It cannot be defeated by a lexical rule, because the lexical rule is pinned at chance by arithmetic — not by argument, and not by a baseline that merely happened to score low.

Contrast with v23 (`1.000`, but positional by construction): v25 removes the positional route and the result **holds** (mean over layers `0.917` vs v23 `0.938`, delta `−0.021`). **The pre-registered "falls to chance if v23 was positional" outcome did NOT occur.**

## Honest limits
- **Best layer is `L0`.** If `L0` denotes the state after the first transformer block, one attention pass suffices to move marker information to the final position — real binding, but **shallow**, not deep multi-layer composition. This should be resolved by confirming the engine's layer indexing before any "deep structure" language is used.
- **NOT a CAS claim.** The discriminative task is *"which phrase came earlier in time,"* not *"which is the `^8` trigger."* **No CAS-specificity is licensed.** CAS-specificity remains `GREY`.
- n = 12 pairs / 24 items; one frame template; one model (160m); one seed.
- Scale untested (6.9b would cost ~$0.15).

## Claim state
- **Real:** all numbers, real `pythia-160m` via the **attested engine**, `$0`. **Accepted:** none.
- **LICENSED:** *"On pairs where bag-of-words and char-n-gram models are provably pinned at chance and position is counterbalanced, the model's activations recover the long-range binding at `1.000` best-layer / `0.917` mean-over-layers."*
- **NOT LICENSED:** CAS-specificity; deep (multi-layer) structural composition.
