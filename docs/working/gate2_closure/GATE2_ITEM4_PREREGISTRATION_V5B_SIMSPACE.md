# GATE 2 ITEM 4 — PRE-REGISTRATION v5b (`TKS-HELDOUT-COMPOSITION-SIMSPACE-v5b`)

**Committed BEFORE any v5b result exists.** Owner-authorized. v1–v5 remain NOT LICENSED / VOID and are
retained unedited.

---

## 1. What v5 got wrong

v5 composed `normalize(mean(row) ⊙ mean(col))` in **embedding space**, then made that vector compete
against 39 raw definition embeddings. The elementwise product of two averaged high-dimensional vectors
points toward the centre of the embedding distribution, so after normalisation it sits systematically
close to *everything*. It became a degenerate attractor: every item selected it, every arm scored
`1.0000`, and permutation `p = 1.0000` — the score was independent of anchor content.

**The multiplication was right. The space was wrong.**

## 2. The v5b fix — multiply in similarity space

For each test item `x` and held-out cell `c`:

```
sim_row      = cos(x, normalize(mean of row N without c))
sim_col      = cos(x, normalize(mean of col W without c))
sim_global   = cos(x, normalize(mean of all 39 remaining cells))
sim_composed = sim_row * sim_col / sim_global
```

Cell `c` is scored by `sim_composed`; the other 39 cells keep their raw cosine to `x`; argmax decides.
Every quantity is a cosine in `[-1, 1]`, so all 40 competitors are commensurable and no scale
degeneracy can arise. The multiplicative Noetic × World interaction — the thing addition discards — is
preserved.

**Numerical safeguard, declared in advance:** if `|sim_global| < 0.05` for an item, `sim_composed` is
undefined and that item is **excluded**, with the exclusion count reported. Dividing by a near-zero
denominator would manufacture arbitrarily large values, which is how v5 failed. If more than 10% of
items are excluded, the run is **VOID** and reported as such.

## 3. Everything else identical to v4/v5

Leave-one-out over all 40 cells; v4 masking retained; **frozen bars unchanged**. v5b differs from v4 in
the operator and its space, and in nothing else.

| # | Criterion | Bar |
|---|---|---|
| V1 | TKS above chance | `> 0.025`, permutation `p < 0.01` |
| V2 | TKS beats compact CAS | margin `>= 0.05` |
| V3 | Lexical control at chance | `<= 0.05` |
| V4 | Nulls at chance | `<= 0.05` |
| V5 | Not one cell | `>= 8` of 40 folds |
| **V6** | **Metric is content-dependent** *(new)* | permutation `p` strictly inside `(floor, 1.0)`, **and** not both arms at `1.0000`, **and** random-anchor null `< 0.10` |

**V6 is new and exists because of v5.** v5 returned a perfect score for a definition set with zero
compositional structure, and a permutation p of exactly `1.0000`. A metric whose output survives
randomising its own inputs measures nothing. V6 makes that an automatic VOID rather than something I
have to notice. It is a gate against *me*, not against the data.

## 4. Pre-committed consequences

- **All pass** → scoped positive: composition is detectable on `pythia-1b` under a multiplicative
  operator with direct vocabulary masked. The external A/B claim still waits on the independent bank.
- **V1 or V2 fails** → the operator family is genuinely exhausted. Additive and multiplicative, in both
  natural spaces, will have been tested. The bank becomes the sole path.
- **V3 or V6 fails** → VOID, and the same conclusion follows.
- **FINAL RUN IN THIS FAMILY.** No v5c, no third space, no further operator variants. Whatever this
  returns is the family's last word.

## 5. Declared ceiling (unchanged from v5)

Masking removes the held-out cell's own item vocabulary but not the sibling channel: **46.2%** of a
cell's vocabulary already sits in its row and column siblings. A PASS licenses *"composition is
detectable despite direct vocabulary control"* — never *"vocabulary plays no role."*

## 6. Status

`LOCKED / COMMITTED BEFORE RESULTS EXIST / NOTHING LICENSED`

`EleutherAI/pythia-1b`, layer 12, repaired 40-Element holdout (5,920 unique, zero leakage), chance
`0.025`. Independent bank track continues in parallel regardless of outcome.
