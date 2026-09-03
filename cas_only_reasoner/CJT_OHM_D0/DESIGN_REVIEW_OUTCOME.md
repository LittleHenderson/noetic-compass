# CJT-OHM-D0 — `D0_DESIGN_INVALID`

```
D0_DESIGN_INVALID: D5_VACUOUS_AND_UNREPLACEABLE
                   D_ANON_FACTORIZED_IS_THE_SAME_ARM
                   CAS_TYPED_REPAIR_SIGNAL_UNREACHABLE_BY_CONSTRUCTION
```

**Third design retired at `$0` in a row.** Designed, amended under owner ruling, attacked, and
retired before a line was built. No implementation, no training, no GPU, no spend.

---

## 1. The verdict

**The owner was right that `D5` "may be algebraically vacuous" — and it is worse than *may*.**

`D5_CAS_TYPES_SHUFFLED` is not similar to `D4`. It is **the same function**, and a permutation of
the parameters carries one to the other exactly.

**Verified by me, after fixing an inverted permutation in my own first attempt:**

```
enumerated ALL 720 permutations of 6 channels
worst |logit_D5(perm) - logit_D4(permuted params)|  =  0.0000e+00
```

Not small. **Zero.** Every channel shuffle is undone by relabelling the module parameters — a
relabelling gradient descent is free to find. The owner's own metaphor turns out to be literally
exact: relabelling the drawers and letting the worker relearn where each drawer is proves nothing.

## 2. Why this kills the headline status, not just one arm

`CAS_TYPED_REPAIR_SIGNAL` was registered as requiring **all three** of: beats `D2`, beats `D3`,
**and is destroyed by `D5`**.

> **A necessary conjunct that is identically false cannot be satisfied.**

So the bench's headline status is **unreachable by any `A1.B`-compliant build** — not unlikely,
not underpowered: unreachable. `D0` could only ever return one of its consolation statuses.

## 3. And the ladder loses its top rung too

`A1.E` defines `D_ANON_FACTORIZED` as `D4` with the same channel count, modules, constraints,
parameters and compute — **but anonymous factors**.

Anonymising the factors *is* choosing an assignment of sources to modules with the names
stripped. **That is an element of the same permutation group**, which §1 just enumerated and
found absorbed at `0.0`.

```
D_ANON_FACTORIZED  ==  D5  ==  D4
```

**Three of the seven arms are one arm.** The rung meant to separate *"does factorisation help"*
from *"do the CAS meanings help"* is empty before any data exists — and `FACTORIZED_DIAGNOSIS_
SUFFICIENT` is guaranteed by construction. This is `CJT-OHM-0R`'s `C1` defect (*"those were never
two mechanisms"*) reappearing in a new place, in a design I had just committed.

## 4. The seventh shortcut: the status is a dial

The size of the `D5` effect is **an integer the builder chooses** — how many repair logits each
typed module may write to — and it barely moves the arm being advertised:

| routing sparsity `s` | `D5` damage | `D4` accuracy |
|---|---|---|
| 1 | **0.7283** | 0.9688 |
| 2 | 0.5811 | |
| 3 | 0.3892 | |
| 4 | 0.2027 | |
| 5 | 0.0050 | |
| 6 | **0.0019** | 0.9578 |

`D5` damage moves through **two and a half orders of magnitude** while `D4` accuracy moves
`0.0110` in total. **One integer selects between `CAS_TYPED_REPAIR_SIGNAL` and
`CAS_TYPING_ORNAMENTAL`**, and no registered gate constrains it.

**And both ends are forbidden.** At `s = 6` the arm is `A1.B`-compliant and `D5` is vacuous
(`0.0019`, a third of one seed standard deviation). At `s = 1` the damage is maximal — because
module `j` can only write to repair `j`, which **is** the hard-coded repair table `A1.B`
prohibits, wearing learned weights as a costume.

> **`A1.A` and `A1.B` are a vise: the only structure that makes `D5` bite is the structure
> `A1.B` forbids.**

Same defect class as `CPB-0`'s *"the status was selectable by one line in the corpus generator"* —
the eighth time this program has produced a selectable status or a label-free shortcut.

## 5. The owner's four replacements

`A1.A` offered four alternatives if `D5` proved absorbable. Per the lane, **three are also
absorbed or measured at/below seed noise**, and the fourth — feeding the wrong causal source into
**fixed** repair operators — requires exactly the fixed operators `A1.B` forbids. The vise again.

One is worth stating separately: the **eval-time source shuffle** is genuinely non-equivariant,
but it is **non-diagnostic** — it destroys the *generic* arm too, so it measures "this model was
trained on a different input mapping," not "CAS typing was load-bearing."

## 6. What I could not reproduce, stated plainly

The lane reported the two arms tracking each other to `4.44e-16` across an entire **training
curve**. **My reconstruction did not reproduce that** — I measured `1.33e-01` divergence over 200
steps.

> ⚠ **DIAGNOSED 2026-09-02 BY THE FRESH-GLM AUDIT — the `1.33e-01` was MY HARNESS'S BUG, not a
> failure of the claim.** The audit traced it to an **initialization-permutation defect**: my V2
> setup initialized the supposedly equivalent model with `perm` where it required `perm⁻¹`, so the
> permutation was applied in the wrong direction and the two arms never started from matching
> parameters. **The non-reproduction was mine. `1.33e-01` measures my error, not a discrepancy in
> the lane's claim, and it must not be cited as evidence against that claim.** The V1 forward-pass
> identity (§1, `0.0000e+00`) was and remains correct and is what the verdict rests on.

**The verdict does not rest on it.** §1 plus the from-scratch measurement — `D4` `0.9555` vs `D5`
`0.9544`, a gap of `0.0011` against a seed standard deviation of `0.0065`, i.e. `0.17 sd`, and
holding even when the *task* is made channel-asymmetric — is sufficient and is the practically
relevant form. I am recording the non-reproduction rather than adopting a number I could not
confirm.

## 7. My own error, recorded

My first verification script **inverted the compensating permutation** and measured `9.27`
instead of `0.0` — and then **printed "floating-point ZERO" anyway**, because I had hard-coded
the conclusion instead of deriving it from the measurement.

That is precisely the defect this program keeps catching in others: *a conclusion that
contradicts its own output.* I caught it only because the number was absurd. It is fixed, and
every conclusion in that script is now data-driven.

## 8. What happens now

- **`D0` is retired as designed. Not redesigned.** Fourth appearance of the automatic-second-
  repair temptation; same answer.
- **The `A1.A`/`A1.B` vise is the real finding**, and it generalises beyond this bench: *any*
  "shuffle the type labels" control over a symmetric architecture is vacuous, and the only way to
  make it bite is to hard-wire the correspondence you were trying to test.
- **What is NOT killed:** the underlying question — *does preserving typed causes of identical
  flow help select the right repair?* — is untouched. What died is this way of asking it, and
  specifically the idea that a **label shuffle** can serve as the causal control.
- **A successor would need a genuinely non-equivariant corruption**, and this review found none
  that is both non-equivariant and diagnostic. Until one exists, there is no valid `D5`, and
  without a valid `D5` there is no CAS-specific claim available from this design.

## 9. Cost

```
design                     $0
amendment under ruling     $0
seven-lane attack          $0   local CPU
builder re-verification    $0   local CPU
TOTAL                      $0
```

**Three designs retired for nothing, and this one was killed by a property of its own control
arm that no amount of data would have revealed.**
