# CJT-OHM-0R — `NON_VACUOUS_EXPERIMENT_REMAINS`. `$0`, CPU, no training, no GPU.

**Answers the owner's ruling: *"Return whether a non-vacuous neural experiment remains."***

**Yes — but not the one the document proposed, and much narrower than the ladder it describes.**

Sixteen checks, all passing. `python ohm0r.py` · receipt `CJT_OHM_0R_RESULT.json`.

---

## 1. The answer in one paragraph

The claim *"CAS-Ohm generates the effective weight matrix"* is **retired** — it is its own output
mixture, to `8.882e-16`. What survives is three things a mixing coefficient cannot express:
**absolute flow** governing compute, **typed diagnosis** selecting a repair, and a **hard mask**
certifying a closed path. All three live at a **recurrent or pre-nonlinear socket**, and none of
them is the weight-generation claim.

**And one thing does not survive:** on routing alone, a controller handed only the ratio `g = V/R`
reproduces both `α` and `I_total` **exactly**. The Drive/resistance split earns nothing in
allocation. If it earns anything, it earns it in diagnosis.

## 2. What is retired

| check | measured | consequence |
|---|---|---|
| `C1` original linear `W_eff` vs its output mixture | **`8.882e-16`** over 400 inputs | `ORIGINAL_WEIGHT_FORMULATION_REPARAMETERIZATION_ONLY` |
| `C12` ratio-only controller vs full `V`,`R` controller | **`0.000e+00`** on both `α` and `I_total` | the `V/R` split adds **nothing to routing** |

`C1` retires the owner's own `O4 − O2 ≥ 0.01` criterion: those were never two mechanisms.

## 3. Where composition genuinely differs from mixing

`C2`, with the **exact** twin — same `α`, same bases, same nonlinearity placement:

```
linear socket          8.882e-16   TWIN -- vacuous
pre-nonlinear socket   0.4528      DISTINCT
recurrent socket       0.1112      DISTINCT
```

`C3` asks the follow-up that matters — is the recurrent difference real or a rounding artefact?
Divergence per step over 10 steps:

```
0.0000, 0.0382, 0.0498, 0.0522, 0.0525, 0.0526, 0.0526, 0.0526, 0.0526, 0.0526
```

It **grows and then saturates at a fixed point**. Real, bounded, and a property of the socket —
**not** of CAS. A generic hypernetwork modulating the same socket would show the same thing. This
establishes *where a non-vacuous experiment could live*, not that CAS wins there.

## 4. The owner's Q4 amendment — confirmed, and corrected in one place

**Confirmed.** Common-mode factors cancel from `α`; per-junction factors do not:

| | measured |
|---|---|
| `C4` common multiplier (`ψ×4`, and `V,R×9`) → change in `α` | `1.241e-07` |
| `C5` one junction's `R` raised → change in `α` | **`0.0448`** |
| `C5` one junction unready → change in `α` | **`0.5000`** |
| `C6` `ψ×4` → `α` unchanged, `I_total` | **`×4.0000`** |

Keeping both outputs is the right fix: a multiplicative common factor is **invisible in `α` and
visible in `I_total`**. Discarding `I` is exactly what makes a global region or readiness
multiplier decorative.

### The correction — to the amendment, and to my own first draft

**`I_total` does NOT rescue `V/R` identifiability.** `C7` measures three `(V,R)` pairs with equal
ratios and finds **`α` identical AND `I_total` identical (`[2.0, 2.0, 2.0]`)**. A *joint*
rescaling `V→cV, R→cR` cancels inside the ratio itself, so it is invisible in both outputs.

**These are two different invariances**, and the amendment fixes only the first:

| invariance | cancels in `α` | cancels in `I_total` | fixed by keeping `I`? |
|---|---|---|---|
| multiplicative common factor (`ψ`, `ρ`, global scale) | yes | **no** | **yes** |
| joint rescaling of `V` and `R` | yes | **yes** | **no** |

> **`CONDUCTANCE_ONLY` stands.** Only an *independent readout* of `V` or `R` — a place where one
> is consumed without the other — can identify the decomposition. `I_total` is not that place.

**My first draft of this package asserted the opposite** — that `I_total` "DOES separate them" —
while the run it shipped with printed `[2.0, 2.0, 2.0]`. The measurement was right and the
sentence was wrong. Corrected, and recorded rather than quietly fixed, because a conclusion
contradicting its own output is the exact defect this program keeps catching in other people's work.

**Also corrected:** the invariances are approximate, not exact. The `ε` in `V/(R+ε)` and
`i/(I+ε)` breaks exact scale invariance at `O(ε)` — measured `1.241e-07`. Behaviourally
irrelevant, but "exact invariance" would have been a false claim.

## 5. What is genuinely non-vacuous — three capabilities, none of them weight generation

### `C8` typed diagnosis — the strongest surviving result

Five scenarios were constructed with **different causes and different correct repairs**. Measured:
**2 distinct allocation values each map to more than one correct repair, covering 4 repairs.**

A controller that emits only `α` sees the same number in cases needing *"raise goal relevance"*
and *"remove a resource constraint"*. It **cannot** choose between them — not because it is
under-trained, but because the information is not in its output. The typed controller sees `V`,
`R`, `ρ` and `m` separately and can.

**This is an information argument, not an empirical one.** It proves a scalar gate *cannot*
express the distinction. It does **not** prove the typed repair *helps* — that needs a bench.

### `C9` the hard mask is a guarantee no soft gate gives

```
hard mask   -> alpha[0] = 0.0e+00     EXACTLY zero
softmax     -> alpha[0] = 6.388e-24   with a logit of -50, still strictly positive
```

A softmax gate on finite logits is positive everywhere. It can make a path negligible; it can
never **certify** a path closed. For a policy prohibition — *refuse regardless of Drive* — that
distinction is the whole point.

### `C6` absolute flow can govern compute

`I_total` responds to a common multiplier that `α` discards, so total flow can drive processing
depth, activation threshold and plasticity magnitude. Whether it *should* is untested.

## 6. Governance checks

`C10` controller inputs are answer-free — 7 declared, 0 forbidden. `C11` a verdict at `t` alters
`t+1` only: same-tick leak `False`, next-tick routing moved `True`.

## 7. What this package cannot answer, stated plainly

**Everything that requires learning.** Sample efficiency, out-of-distribution extrapolation, and
the central question — *does the CAS form beat a matched generic controller given the same
inputs, parameters and data* — are **not settled here and cannot be**. `Q5` stands: a generic MLP
can represent `normalize(m·ρ·ψ·V/R)`, so CAS can only ever win as an **inductive bias**, never on
expressiveness. That is a GPU question and it is not authorized.

This package also does not show that any of the three surviving capabilities is **useful**. It
shows they are **expressible by the typed law and not by a coefficient**, which is the
precondition for asking whether they help — not the answer.

## 8. The honest shape of what is left

```
RETIRED     CAS-Ohm generates the weights            C1: 8.882e-16
RETIRED     V/R earns its keep in routing            C12: 0.000e+00
UNRESOLVED  does the CAS form beat a generic one     requires learning; GPU; not authorized
LIVE        typed diagnosis picks the right repair   C8: a coefficient provably cannot
LIVE        hard mask certifies a closed path        C9: a softmax provably cannot
LIVE        absolute flow governs compute            C6: I_total x4 where alpha is flat
```

**The smallest experiment that would change anyone's mind** is not the document's nine-arm
ladder. It is: *same conductance, different cause — does a typed controller select the correct
repair and improve the next tick, where a coefficient-only controller cannot?* That is one task
family, it needs no weight generation, and the `C8` construction is already the seed of it.

Whether it needs a GPU at all is an open question I would want answered before asking for one.

---

## 9. Four results from the adversarial lanes that are STRONGER than mine

An independent five-lane assessment attacked this analysis. I re-verified each consequential
claim myself before accepting it. **Four of them improve on what I had**, and one reframes the
whole proposal.

### `C14` — the equivalence is worse than I stated, and provable for EVERY `α`

I measured `C1` for one `α` over 400 inputs. The correct argument is algebraic and universal.
Because `Σ αⱼ = 1`:

```
W_eff = W0 + s·Σⱼ αⱼ dWⱼ  =  Σⱼ αⱼ (W0 + s·dWⱼ)
```

**A convex combination of `J` FIXED matrices.** Worst relative identity error over 200 random
`α`: **`2.807e-16`**. So the composed output lies in the span of the `J` fixed expert outputs
**always**, and `O4 − O2` is **identically zero by algebra** — not merely small for the case I
happened to test. The owner's registered gate was not just unlikely to fire; it was
**mathematically impossible** to fire.

### `C13` — a gate that actually discriminates, replacing the Jacobian one

The registered Jacobian scalar-fit gate is worse than "too weak": it scored the **vacuous** case
`0.3384` and a **genuine** case `0.3194` — the vacuous case slightly *higher*. It has **no
discriminating power at all**.

The replacement needs no `α` and no scalar fit — just ask whether a **free least-squares mix of
the fixed expert outputs** can reproduce the composed output:

```
ADDITIVE law (as written)   span residual  1.8e-15    nothing beyond the span -- VACUOUS
SERIES law                  span residual  0.0233     genuinely outside it
```

### `C15` — the law restricts nothing at all

I said a generic MLP could *approximate* `normalize(m·ρ·ψ·V/R)`. Stronger: set `V` to any target
and `R` to one, and the law reproduces that target **exactly** — worst relative error
**`3.069e-16`** hitting random simplex points. **The CAS-Ohm law is onto the whole open simplex;
it imposes no constraint whatsoever on reachable coefficients.**

So value cannot live in the weight law under any formulation. It can only live in the **map from
raw signals to `α`** — which is precisely the thing a generic controller also learns.

### `C16` — the breaks belong to the socket, not to CAS

Four formulations *do* break the equivalence: repeated linear application, nonlinear recurrence,
attention through a softmax, and series composition. But a **generic Dirichlet `α` breaks it by
the same amount**:

```
series socket   GENERIC dirichlet   mean 0.0170   p5-p95 0.0055-0.0353
series socket   CAS-Ohm V/R         mean 0.0150   p5-p95 0.0031-0.0310
```

Overlapping. **Non-equivalence is a property of where the coefficients enter the network, not of
the law that produced them.** So none of the four breaks converts into an advantage for CAS over
the matched generic hypernetwork — which is the proposal's actual primary comparison, `O4` vs
`O3`, and it remains untouched by all of this.

## 10. The one genuinely new idea — and it is a good one

**In Ohm's law, conductances ADD when elements are in PARALLEL. Parallel *is* mixture.**

> **The proposal wrote the parallel law and then claimed the series benefit.**

The series formulation `W_eff = Πⱼ (I + s·αⱼ dWⱼ) W0` is the one single-step arrangement that is
genuinely outside the additive family. The best **free, unconstrained** additive fit
`W0 + Σⱼ βⱼ dWⱼ` to a series matrix leaves a relative residual of **`0.966`–`0.972`** — the
series matrix is essentially not representable additively at all.

That is a different hypothesis class, not the same law re-parameterised, and it has the correct
physical reading rather than a borrowed one. **If any part of this program is worth building, it
is this** — and it is not what the document proposed.

**The honest qualifier, from `C16`:** series composition being a richer class does **not** make it
a CAS result. A generic controller at the same series socket gets the same richness. What series
buys is a **compute and parameter saving** — every broken formulation is exactly a mixture over a
combinatorially larger *implicit* set of composed operators, with coefficients that are monomials
in `α`. That is what depth and multiplicative parameterisation buy in any network.

## 11. Revised bottom line

```
POSSIBLE      only in a narrower form -- the weight-generation claim is dead by algebra
BENEFICIAL    unproven, and the burden is now clearly on data efficiency and OOD transfer,
              never on accuracy or expressiveness
LIVE          typed diagnosis (C8), hard-mask certification (C9), absolute flow (C6)
NEW           series composition -- physically correct, genuinely outside the additive
              family, and NOT what was proposed
```

**Cheapest decisive next step, and it is still `$0`:** the span gate (`C13`) plus the positional
control (`C16`) settle the entire weight lane before a GPU is booked. Both are already in this
package and both already ran.

---

## 12. OWNER RULING 2026-09-02 — three corrections to THIS package

`cbffa4a0` is **provisionally accepted pending independent audit**. Three corrections apply to
my own framing, and all three narrow claims I made.

### 12.1 "Series Ohm's law" is the wrong name — it is a CASCADE

My §10 said *"in Ohm's law conductances ADD in PARALLEL"* — correct — and then called the matrix
product **series**, which conflates two different things. In circuits, **conductances add in
parallel; resistances add in series.** Multiplying transformation matrices is neither: it is a
**cascade of active stages**, where one stage's Effect becomes the next stage's Cause, and stage
gains multiply.

> **Renamed: `CJT CASCADE COMPOSITION`, not `SERIES CONDUCTANCE WEIGHT LAW`.**

The mathematics is unchanged — the cross term `s²·α₁α₂·ΔW₂ΔW₁` still does not exist in the
additive mixture, and `ΔW₂ΔW₁ ≠ ΔW₁ΔW₂` still makes order matter. Only my electrical analogy was
sloppy, and a sloppy analogy in this program is how a metaphor becomes a claim.

### 12.2 `C9` — the hard mask is GOVERNANCE, not unique CAS arithmetic

`C9` measures something true: a hard `0/1` mask gives exactly `0.0` where a softmax floors at
`6.388e-24`, so only the former can **certify** a path closed. But I presented it under "what
survives for CAS," which implies CAS uniquely provides it.

**It does not.** Any architecture can carry a hard permission mask. It is a **governance
mechanism CAS includes**, not a CAS result. Reclassified.

### 12.3 `C8` — my strongest result was measured against the wrong competitor

`C8` proves a controller **emitting only `α`** cannot select the correct repair. True, and
useless: that is not the competitor that matters.

> **The fair generic competitor is a `GENERIC_FULL_STATE_MLP` receiving all the same nongold
> fields — `V`, the resistance components, readiness, mask, verifier history — as a flat
> vector.** Such a controller can distinguish the cases perfectly well.

So `C8` proves **a coefficient is insufficient**. It does **not** prove **CAS typing is
necessary**. Those are different claims and I stated the weaker measurement in the stronger
frame. The real contest is CAS factorization versus generic full-state, both seeing identical
inputs, and it is decided by sample efficiency, unseen combinations, repair-error rate and
next-tick recovery — **none of which this package measured or could measure.**

### 12.4 What the ruling preserves and closes

```
CLOSED     additive weight generation          mathematical reparameterization
DELETED    O4 vs O2 as a scientific contrast   never two mechanisms
PRESERVED  allocation alpha
PRESERVED  absolute flow I_total
PRESERVED  hard mask -- as GOVERNANCE, not CAS arithmetic
PERMITTED  separate V/R interpretation ONLY with independent sources
PRIMARY    typed diagnosis and next-tick repair
SEPARATE   CJT cascade composition -- its own design, NOT a continuation of the retired claim
NO GPU     until audit and preregistration
```

---

## 13. GLM INDEPENDENT AUDIT of `cbffa4a0` — `PASS`, one finding, `$0`

Seventh audit this session, all `PASS`, cumulative audit spend `$0`. Fixes prohibited during the
audit and none were made. **GLM wrote its checks fresh from the ruling's spec and ran them
outside the repo** — it did not execute this package's code.

Reproduced independently at the `1e-16` class: `C1`/`C14` (worst `3.1e-16`; the convex-hull
identity at `1.7e-16`), `C12` (`2.2e-16`), `C9` (float-exact `0.0`), `C8`, and the cascade span
residual — **`0.2096` outside** ⚠ **[WRONG NUMBER — see §14. This is GLM's own reimplementation's figure, not this package's; the committed code gives `0.054458` standalone / `0.0746` full-run. And the quantity is VACUOUS regardless: it is a 60th-percentile draw from purely random matrices.]** the additive family against a matched additive control at
`3.0e-16` inside.

The auditor confirmed the package **correctly defers** the five-way matched cascade comparison to
a GPU stage, so **no unfair-depth claim is baked into Stage A** — and restated the owner's rule
that if generic and CAS cascades tie, the finding is `SEQUENTIAL_CASCADE_COMPOSITION_VALUE`, not
`CAS_OHM_VALUE`.

### Finding F1 — the ε class. Fixed here; **blocking for `D0`**

`split_flow` computed `α = i/(I + ε)` *inside* the `I > 0` branch, where the ε is **redundant** —
the branch already handles `I = 0` — and it broke exact common-mode invariance at `O(ε/I)`.

**Fixed.** `ψ` common-mode drift: `1.241e-07 → 0.000e+00`, exact.

The `R + ε` guard in `conductance` is **load-bearing** (`R` may be zero) and stays. Its
consequence is now documented as the **ε equality class**: same-conductance pairs are equal only
to `O(ε/R)`, measured up to **`2.496e-04`** at small `R`.

**That consequence is a side channel in `CJT-OHM-D0`'s collision groups**, where states must be
indistinguishable but would differ by the residue. Registered there as
`GATE_EPS_NOT_A_SIDE_CHANNEL` with a floor of `R, I ≥ 10⁴·ε`, and a classifier trained on the
residue alone added to the trivial-rule gate. See `CJT_OHM_D0` amendment A2.

### Auditor eligibility, recorded

GLM is **no longer eligible** as the third auditor for a claim-bearing neural result on this
line, having audited the design such a result would test. A third distinct auditor is required.

---

## 14. CORRECTION 2026-09-02 — THE HEADLINE CASCADE NUMBER IN THIS FILE IS WRONG, AND THE QUANTITY IT NAMES IS NOT CAS-SPECIFIC

Found by me while doing the pre-design check for `CJT-CASCADE-S0`, before any design work.
Artifact: `CJT_CASCADE_S0/verify_span_gate.py` — runnable, `$0`, local CPU.

### 14.1 The number is wrong

Section 13 records the cascade span residual as **`0.2096`** against a matched additive control
at **`3.0e-16`**. **The committed package does not produce those numbers.**

```
committed c13, standalone      cascade 0.054458   additive 1.785643e-15
committed c13, full-run        cascade 0.0746     additive 1.473e-15
RECORDED IN THIS FILE          cascade 0.2096     additive 3.0e-16
```

**Owner ruling on the framing: the problem is PROVENANCE, not arithmetic.** Each figure is
labelled, and none is called wrong:

```
0.2096      EXTERNAL REIMPLEMENTATION RESULT      (GLM's own rebuild)
0.054458    STANDALONE COMMITTED-CODE RESULT
0.0746      FULL-PACKAGE COMMITTED-CODE RESULT
```

**This does not necessarily mean GLM's calculation was false.** The numbers came from different
implementations and different random states. **The defect was mine: I improperly blended them
into one evidentiary trail**, transcribing the external rebuild's figure into §13 — and from
there into the spec-sheet Change Log and into memory — as though this package had emitted it.

The two committed values differ from each other too (`0.054458` vs `0.0746`), because the figure
depends on how much of the shared RNG stream was consumed before the check ran. **It is not a
stable quantity.**

**Rule violated:** *"Keep every number exact — never round, never paraphrase a metric."* This was
worse than rounding: it was attributing an outside reimplementation's figure to the committed
code.

### 14.2 The quantity is not CAS-specific — and could not be

**The committed `Basis` contains no CAS content whatsoever.** `W0`, `A`, `B` and `U` are all
`RNG.normal` draws. So `C13_SPAN_GATE` was never measuring anything about CAS; the right reading
of its output is *"what does a random system score?"*

Measured, 15 independent random systems under the exact `c13` protocol (`trials=200`):

```
min 0.026937   mean 0.047810   max 0.071911   sd 0.013662
```

**Every purely random system is "outside the additive span."** And the committed value
`0.054458` sits at the **60th percentile, `0.49` sd from the random mean** — a wholly typical
draw.

> **The gate has no discriminating power for CAS. It distinguishes a PRODUCT of matrices from a
> SUM of matrices, which is a fact of linear algebra, not a finding.**

### 14.3 It is also a free dial — the NINTH in this program

`s = 0.7` is hard-coded in `Basis.__init__`. No registered gate constrains it. A fresh `Basis`
and a fresh trial stream per row:

| `s` | additive | cascade | mean `‖s·ΔW_j‖₂` | `c13` gate |
|---|---|---|---|---|
| 1.000 | `1.4046e-15` | `9.508132e-02` | `1.2403` | **PASS** |
| 0.700 | `3.1552e-15` | `7.815411e-02` | `0.9994` | **PASS** ← committed default |
| 0.500 | `1.8583e-15` | `1.502731e-02` | `0.6489` | **PASS** |
| 0.300 | `7.8447e-15` | `6.064390e-03` | `0.3897` | **PASS** |
| 0.100 | `6.2334e-15` | `1.046009e-03` | `0.1593` | **PASS** |
| 0.050 | `4.9564e-15` | `2.257632e-04` | `0.0742` | **FAIL** |
| 0.030 | `6.6746e-15` | `7.082362e-05` | `0.0422` | **FAIL** |
| 0.010 | `5.7141e-15` | `5.990553e-06` | `0.0130` | **FAIL** |

Range **`15872×`**; exponent **`2.24`** — second order in `s`, exactly as the algebra predicts,
because the cross term `s²·aᵢ·aⱼ·ΔWⱼΔWᵢ` is the only part the additive mixture cannot express and
it vanishes quadratically while the arms' own effect vanishes linearly.

> **ONE HARD-CODED FLOAT SELECTS WHETHER THE GATE PASSES.** It flips to `FAIL` at `s ≤ 0.05`.

### 14.4 And the effect only exists where the comparison is unmatched

At the committed default `s = 0.7` the stages have mean operator norm **`1.2385`** — greater than
one. `(I + s·α·ΔW)` is nowhere near the identity. **These are not small updates composed
sequentially; the cascade is a genuinely deeper, different model.** The residual is large only
in the regime where the additive control is not a matched competitor at all — which is the
unfair-depth problem the owner flagged and the audit believed had been deferred to a GPU stage.

### 14.5 Consequence

**`C13_SPAN_GATE` is downgraded to `VACUOUS`.** It does not support a CAS claim, and it never
could have, because the object it measures has no CAS content in it.

The surviving mathematical fact is narrower and should be stated only in this form:

> **A sequential composition of matrix stages is not a member of the additive family. This is a
> property of matrix multiplication. It is true of random matrices, its magnitude is set by a
> free scale parameter, and it carries no information about CAS.**

**No negative is deleted and no other status changes.** `C1`, `C9`, `C12` and `C14` are
unaffected; the ε repair stands.
