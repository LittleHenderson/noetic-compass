# GATE 2 ITEM 4 — PRE-REGISTRATION v5 (`TKS-HELDOUT-COMPOSITION-MULT-v5`)

**Committed BEFORE any v5 result exists.** Owner-authorized after external review.
v1–v4 remain permanently NOT LICENSED and are retained unedited.

---

## 1. Why v5 exists — a problem the bank critique did not cover

An external review made an argument I had missed, and I think it is correct:

> If additive reconstruction could detect compositional structure at all, **compact CAS should have
> scored below TKS** — it is built by concatenation and has zero compositional structure by
> construction. Instead both sat at chance. The additive operator is blind to the very thing being
> tested.

That is an **instrument** critique, independent of the shared-authorship **bank** critique. v5 tests it.

Verified numbers behind it: in v4, TKS `0.0071` and compact `0.0220` are statistically
indistinguishable — paired permutation `p = 0.4955`, 2/40 vs 3/40 cells nonzero. Neither arm registered.

## 2. The single change

`u_c = normalize( mean(row N without c) ⊙ mean(col W without c) )` — **elementwise product**, where v3
and v4 used `row + col − global`. Multiplication carries interaction terms that addition discards; it
is still parameter-free and still identical for every arm.

**Everything else is held exactly as v4**, including v4's masking (delete every word of the held-out
cell's test items from every definition in every arm before encoding) and — deliberately — **v4's exact
acceptance bars, unchanged**. v5 differs from v4 in the operator and nothing else, so a difference in
outcome is attributable to the operator. Re-tuning the bars here would destroy that comparison.

## 3. Frozen criteria — identical to v4, not relaxed

| # | Criterion | Bar |
|---|---|---|
| V1 | TKS above chance | `> 0.025`, permutation `p < 0.01` |
| V2 | TKS beats compact CAS | margin `>= 0.05` |
| V3 | Lexical control at chance | `<= 0.05` |
| V4 | Nulls at chance | `<= 0.05` |
| V5 | Not one cell | `>= 8` of 40 folds |

## 4. Declared ceiling — what a PASS would and would not mean

Masking removes the held-out cell's **own** item vocabulary. It does **not** remove the sibling channel:
measured on the real definitions, **46.2% of a cell's own vocabulary is already present in its row and
column siblings** (median 44.7%, max 77.8%; 38 of 40 cells above 25%). Composing siblings can therefore
reassemble some vocabulary about the held-out cell no matter what the operator is.

So a PASS licenses: *composition is detectable on this model despite direct vocabulary control.*
It does **not** license: *vocabulary plays no role.* That distinction is fixed here, before the result,
so it cannot be blurred afterwards.

## 5. Pre-committed consequences

- **All pass** → scoped positive: on `pythia-1b` and this fixture, TKS definitions support
  compositional reconstruction of unseen cells under a multiplicative operator with direct vocabulary
  masked, and compact CAS does not. The **full A/B comparison still waits on the independent bank.**
- **V1 or V2 fails** → the instrument family is exhausted. Additive and multiplicative are the two
  natural parameter-free operators; if neither registers, the problem is not the operator.
- **V3 fails** → void, as before.
- **This is the final operator attempt.** No v6 on a third operator.

## 6. Running in parallel

The independently-authored bank is being specified simultaneously, **not** sequenced behind this run.
It is the rate-limiting step and is required whether v5 passes or fails, because only it can support
the external A/B claim.

## 7. Status

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`

Model `EleutherAI/pythia-1b`, layer 12. Bank: repaired 40-Element holdout (5,920 unique, zero leakage).
Chance `0.025`.
