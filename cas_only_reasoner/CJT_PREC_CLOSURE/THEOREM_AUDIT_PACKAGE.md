# AUDIT PACKAGE — the *generic* non-absorption theorem for the anchored precedence chain

**For a SECOND, INDEPENDENT MATHEMATICAL AUDITOR.**

**Recusals.** The first auditor (Zhipu GLM) **authored** the proof sketch under review and is
therefore a contributor, not an auditor, for this theorem. Claude built the artifacts and is also
ineligible. **The auditor must be a different model family or a human mathematician.**

**You are asked to BREAK this, or to state exactly what weaker claim survives. A verdict of
"the generic claim is not provable as stated" is a successful outcome.**

---

## 1. The object

Fix `K` typed modules at **fixed positions** in a chain. The position order is fixed **externally**
by a domain law (`P ≻ C ≻ E ≻ O`, so `K = 4`). Each **type** owns a grounded evidence vector; the
evidence travels with the type, not with the position.

```
h_{-1} = 0
h_k    = tanh( E[σ(k)] · W_k  +  U_k · h_{k-1}  +  b_k )      k = 0 … K-1
out(E ; θ, σ) = h_{K-1} · Rd
```

| symbol | shape | meaning |
|---|---|---|
| `E` | `(K, DE)` | grounded evidence; **row `t` belongs to TYPE `t`** |
| `σ` | permutation of `{0..K-1}` | `σ(k)` = which **type** sits at chain **position** `k` |
| `W_k` | `(DE, H)` | read-in of the module at **position** `k` |
| `U_k` | `(H, H)` | the module at position `k` reads the **previous** module's state |
| `b_k` | `(H,)` | bias |
| `Rd` | `(H, ACT)` | **shared** readout. **There is no action mask.** |

Write `θ = (W, U, b, Rd)`. For a permutation `τ` define the **relabelled parameters**

```
θ^τ :  (W_k, U_k, b_k)  ←  (W_{τ(k)}, U_{τ(k)}, b_{τ(k)}) ,   Rd unchanged
```

and the **signed** variant `θ^{τ,s}` multiplying each relabelled triple by `s_k ∈ {+1,−1}`
(`tanh` is odd, so signed permutations are exactly the linear maps `T` with `tanh(Tx) = T tanh(x)`).

## 2. The claims, and their current status

```
(U)  UNIVERSAL   for ALL θ and all σ ≠ id, no τ satisfies out(·;θ^τ,id) ≡ out(·;θ,σ)
                 STATUS: DISPROVED  (§3)

(G)  GENERIC     for θ outside a measure-zero exceptional set, and all σ ≠ id,
                 no τ (or signed τ) satisfies the identity
                 STATUS: SUPPORTED NUMERICALLY, NOT PROVED   <-- THIS IS WHAT YOU AUDIT

(E)  EXPRESSIVITY  the architecture with FREELY FITTED parameters cannot represent
                 out(·;θ,σ) for σ ≠ id
                 STATUS: NOT ESTABLISHED -- our own measurement goes against it (§5)
```

**A previous auditor upgraded this to "not absorbed, full stop." That wording is wrong** — see §3.
The owner refused to freeze it, and the refusal was correct.

## 3. `(U)` is DISPROVED — two counterexample families

Both keep the model **non-degenerate** (it still computes a non-constant function).

**(a) `U_k = 0` for all `k`.** The recurrence dies, so `out` depends only on the module at the
**last** position. Every `σ` fixing position `K-1` is absorbed **exactly**.

```
K = 4, U = 0 :  5 / 23 relabellings absorbed at residual 0.0000e+00
                all 5 of those that fix the last position
                |baseline output|_max = 0.848874          (NOT degenerate)
```

**(b) `W_k = 0` for `k ∈ B`.** Positions in `B` become **type-blind**: they ignore which type sits
there. Every `σ` permuting within `B` and fixing the complement is absorbed exactly. The chain
stays alive (`rank U_k = H` throughout).

```
K = 4, |B| = 1 :  0 of 23 absorbed          predicted 0     MATCH
K = 4, |B| = 2 :  1 of 23 absorbed          predicted 1     MATCH   -- (1,0,2,3)
K = 4, |B| = 3 :  5 of 23 absorbed          predicted 5     MATCH
                  absorbed set = [(0,2,1,3), (1,0,2,3), (1,2,0,3), (2,0,1,3), (2,1,0,3)]
                  |baseline output|_max = 1.020928e+00     (NOT degenerate)
                  rank(U_k) = [6,6,6,6] throughout          (chain alive)
```

> ⚠ **These three numbers were WRONG in the first version of this package** (`1, 2, 5` instead of
> `0, 1, 5`). They were filled in from a wrong mental model rather than read off the run. Corrected
> here before any auditor saw them. **Treat it as further reason to check everything.**

The absorbed set was **predicted from the structure before being measured**, and matched exactly
in all three cases.

**Q1 for the auditor: are (a) and (b) correct, and is the "non-degenerate" check adequate? Are
there OTHER counterexample families we have missed — in particular ones with `U` full rank and all
`W_k ≠ 0`?**

## 4. Evidence for `(G)`, and it is only numerical

**4.1 Generic draws at the registered arity `K = 4`,** all `23` non-identity relabellings, each
against the attacker's best compensation:

```
compensation group          min residual    max residual    absorbed (<1e-10)
24 permutations             1.0558e-01      6.0486e-01      0 / 23
384 signed permutations     6.8768e-02      4.4530e-01      0 / 23

FLAT CONTROL (U removed, stage outputs summed instead of chained):
                            0.0000e+00      1.7764e-15     23 / 23
```

**The flat control is the sensitivity check** — the same modules, same evidence, same test, chain
removed — and it is absorbed `23/23`. So the test can detect absorption when it is present.

**4.2 The exceptional set looks like a knife edge.** Perturb the `W_0 = W_1 = 0` counterexample by
`ε·N(0,0.5)` and track the absorbed relabelling `(1,0,2,3)`:

```
ε          best residual over 24 compensations
0e+00      0.000000e+00
1e-12      2.461142e-12
1e-09      2.461037e-09
1e-06      2.461036e-06
1e-03      2.459727e-03
1e-02      2.446654e-02
1e-01      2.335064e-01
1e+00      8.545328e-01
```

**Linear in `ε` across nine orders of magnitude.**

**4.3 Random sweep.** `200` independent random draws at `K = 4`:
**draws absorbing ANY relabelling = `0`; smallest best-residual over all 200 = `2.1682e-01`.**

**4.4 Arity sweep** (permutation group), showing the effect is not a capacity artefact:

```
K   relabellings   precedence min   flat min       absorbed
2              1     3.3222e-01     0.0000e+00       0/1
3              5     3.3337e-01     0.0000e+00       0/5
4             23     3.2088e-01     0.0000e+00       0/23
5            119     4.6797e-02     0.0000e+00       0/119
```

(The `K = 5` dip is a minimum-over-more-candidates effect: 119 chances to find a near-absorption
versus 1.)

## 5. `(E)` EXPRESSIVITY — a different question, and our measurement goes AGAINST us

Non-absorption says no **relabelling** of `θ` reproduces `out(·;θ,σ)`. It does **not** say the
architecture cannot **represent** that function with freely fitted parameters. We fit it:
analytic gradients, Adam, 1500 steps × 3 restarts, 3000 train / 3000 held out, `K=4, DE=4, H=6,
ACT=4`. Metric = relative RMSE on the held-out set.

```
POS CTRL  the baseline model itself                1.5953e-03
POS CTRL  another random in-class model            1.0947e-02
NEG CTRL  random 2-layer MLP (out of class)        3.4469e-01
NEG CTRL  flat / no-U summed model (out of class)  1.2469e-01
RELABEL   σ=(1, 0, 2, 3)                           4.4291e-02      <-- BELOW the out-of-class floor
RELABEL   σ=(0, 1, 3, 2)                           1.2410e-01
RELABEL   σ=(1, 2, 3, 0)                           1.4322e-01
RELABEL   σ=(3, 2, 1, 0)                           1.7093e-01
RELABEL   σ=(2, 0, 3, 1)                           1.4040e-01
```

Both controls passed. **The weakest relabelling `(1,0,2,3)` fits at `4.4291e-02` — only `4.0×` the
in-class floor and BELOW the out-of-class floor. It is partially expressible.** We recorded this as
`NOT DECISIVE` and did **not** claim non-expressibility.

Note `(1,0,2,3)` is also the *weakest* relabelling under the absorption test (`6.876810e-02`, the
minimum of §4.1). The two measurements agree on which relabelling is closest.

**Q2 for the auditor: does `(G)`, even if true, imply anything about hypothesis-class separation?
Our position is NO. Confirm or correct it.**

## 6. The proof sketch under review, and every gap we can see

The sketch (from the recused auditor) argues that a `tanh` chain is *"generically multi-ridge"*, so
permuting which evidence row enters at which depth changes the composed function, and no
relabelling of the module parameters can restore it. **We flag the following gaps and ask you to
find more:**

1. **"Generically" is never defined.** No exceptional set is characterised. §3 shows it must at
   minimum exclude `U = 0` and every `W_k = 0`.
2. **Measure zero is asserted, not proved.** §4.2–4.3 are numerical. A real argument would show
   the absorption condition is a nontrivial algebraic variety in `θ`.
3. **The compensation group is not characterised.** We tested permutations and signed
   permutations. Signed permutations are exactly the linear maps commuting with `tanh` — **but
   absorption does not require commuting with `tanh`**, only that the composed outputs agree.
   **A larger compensating family may exist and we have not ruled it out.**
4. **The recursive step is summarised, not formalised.** The sketch handles a base case and asserts
   the rest by recursion without writing it out.
5. **No analytic mechanism.** The intuition is *"permuting types changes which evidence enters at
   which depth."* That is not yet an argument. In particular it does not explain why residuals vary
   by nearly an order of magnitude across relabellings (`6.88e-02` to `4.45e-01`).
6. **Narrow instantiation.** One activation (`tanh`), one shape family (`DE=4, H=6, ACT=4`), one
   initialisation distribution. Behaviour under saturation, rank-deficient `Rd`, or `H < DE` is
   untested.

## 7. What we are asking you to return

```
1. Is (U) correctly DISPROVED? Verify or refute §3.
2. Is (G) PROVABLE as stated? If yes, give the proof and define the exceptional set
   precisely. If no, give the strongest claim that IS provable.
3. Is the numerical evidence in §4 adequate for a GENERIC claim, or is there a
   confound? (e.g. does the flat control really isolate the chain?)
4. Is there a LARGER compensating family than signed permutations that could absorb
   the relabelling? This is gap 3 and we consider it the most dangerous.
5. Is our reading of §5 right -- that non-absorption does NOT imply hypothesis-class
   separation?
6. Any counterexample family we missed, especially with U full rank and all W_k nonzero.

Return one of:
    PRECEDENCE_THEOREM_AUDIT_PASS:<the exact claim you certify>
    PRECEDENCE_THEOREM_AUDIT_PARTIAL:<what is unresolved>
    PRECEDENCE_THEOREM_AUDIT_FAIL:<the contradiction or counterexample>

Do not fix anything. Do not redesign the architecture. State what is true.
```

## 8. Reproduction

All numbers above come from committed, runnable scripts (`$0`, local CPU, numpy only):

| section | script |
|---|---|
| §3(b), §4.2, §4.3 | `CJT_PREC_CLOSURE/k4_theorem.py` |
| §4.1, §3(a), §4.4 | `CJT_PREC_CLOSURE/closure.py` |
| §5 | `CJT_PREC_CLOSURE/k4_expressivity.py` |

**A note on this project's error record, so you calibrate your scepticism correctly:** the authors
of this package have shipped, and later caught, a fabricated measurement (a "control" that was a
coin flip against a tautology), two arity mismatches (`K=5` where the claim is `K=4`), and several
conclusions that did not follow from their own output. **Assume the numbers above may be wrong and
check them.**

---

## 9. ADDENDUM — the VISIBILITY LAW replaces the two counterexample families

Added after this package was first written, and it is the main thing we would like you to attack.

> **VISIBILITY LAW.** Call a position **visible** if changing the evidence of the type sitting
> there changes the output. Then `σ` is **absorbed if and only if `σ` fixes every visible
> position.** Equivalently: `EXCEPTIONAL SET = { θ : some position is invisible }`.

Tested on seven constructions, three of which neither family in §3 covers:

| construction | visible | absorbed | law predicts | match |
|---|---|---|---|---|
| generic | `[0,1,2,3]` | 0 | 0 | True |
| `W₀ = 0` | `[1,2,3]` | 0 | 0 | True |
| `W₀=W₁=W₂=0` | `[3]` | 5 | 5 | True |
| `U = 0` | `[3]` | 5 | 5 | True |
| `U₂ = 0` severed mid-chain | `[2,3]` | 1 | 1 | True |
| `Rd = 0` readout killed | `[]` | 23 | 23 | True |
| saturated biases | `[]` | 23 | 23 | True |

**7 of 7, with both controls passing.** This is **not a proof** — it is a falsifiable statement
that survived seven attempts to break it.

**Q3 for the auditor, and it now replaces much of §6: is the visibility law TRUE? A proof, or a
counterexample — a `θ` with every position visible and some `σ ≠ id` absorbed, or a `θ` with an
invisible position and a `σ` fixing all visible positions that is NOT absorbed.**

If the law is true, the generic theorem follows immediately: for generic `θ` every position is
visible, so the only `σ` fixing all of them is the identity.
