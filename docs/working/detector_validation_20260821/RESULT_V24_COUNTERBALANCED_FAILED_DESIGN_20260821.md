# V24 — Counterbalanced pairs: FAILED DESIGN (junction leak). No model advantage. Null.

**Date:** 2026-08-21 · `pythia-160m`, attested engine, **$0**. Results sha256 `439be848ba21147a…`

## What was attempted
The pre-registered decisive follow-up to v23: take **position out of the label** so only role reading can pass. Sensory phrase in slot 1 in **both** members; only the temporal binding flips:
- A: *"the scent of tar came **before** and the memory of childhood came **after**"*
- B: *"the scent of tar came **after** and the memory of childhood came **before**"*

## Result — the design LEAKED
| | score |
|---|---|
| bag-of-words | `0.500` (forced) |
| **char-ngram** | **`1.000`** ← **the leak** |
| activation best | `1.000` (L0); mean over layers `0.993` |

**char-ngram bag residual `0.02776`** (v23 was `0.00000`). The junction n-grams differ — `"before and"` vs `"after and"` — and that alone identifies the class. The char-counter scores **perfectly**, so the activations have **zero** advantage.

## Honest verdict: NULL — the experiment cannot answer its question
This says **nothing** about whether the model reads roles. The stimulus set is surface-solvable, so v23's open question — *positional or role?* — **remains open**. The pre-registered expectation (accuracy falls toward chance if v23 was positional) was **not tested**, because the design failed its own surface check.

**This is the v19 lesson recurring in a new form:** I matched the *word* multiset and forgot that moving a function word changes *junction* n-grams. The matched-n-gram-bag check (which v23 passed at `0.00000`) is the binding gate — **v24 should not have been run at residual `0.02776`.**

## Fix for the next attempt
Make the temporal markers occupy **identical junction contexts** in both members (e.g. place `before`/`after` where the neighbouring characters are the same), and **gate the run on char-ngram residual `≤0.001`** before spending any compute.

## Claim state
- **Real:** all numbers. **Accepted:** none. **Verdict:** `FAILED_DESIGN / NULL`.
- v23's positional-vs-role question is **STILL OPEN**. No claim licensed from v24.
