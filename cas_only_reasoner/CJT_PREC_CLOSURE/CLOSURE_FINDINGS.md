# CJT PRECEDENCE CLOSURE PACKAGE — `$0`, four holes closed, and TWO of my own claims corrected

```
C1  K = 4 registered arity           REPRODUCES -- 0 of 23 relabellings absorbed
C3  "FOR ALL PARAMETERS"             FALSE -- counterexample found
C2  free-lunch claim                 MY NUMBER WAS FABRICATED; re-measured, holds only IN EXPECTATION
C4  arity / capacity                 effect is TOPOLOGICAL, present from K = 2
Item 4  attack-side numbers          MARKED UNVERIFIED_AND_NON_LOAD_BEARING
Item 5  the stale 1.33e-01           ANNOTATED -- it was MY harness bug
```

Artifacts: [`closure.py`](closure.py), [`leakage_sweep.py`](leakage_sweep.py). Both runnable,
`$0`, local CPU, numpy only. No GPU, no neural training, no network.

---

## C2 — the hole that was mine, and it is worse than "sloppy"

**What I committed:**

```python
hits_chain += (int(RNG.integers(0, ACT)) == cause)   # random guessing
hits_mask  += (cause == cause)                        # a tautology
```

**The device was never read.** `0.201300` was a coin flip and `1.000000` was `True`. I then wrote
prose describing it as *"accuracy a zero-parameter reader gets from the device alone"* and had the
script print **"CONFIRMED, AND THIS IS THE FIRST CONSTRUCTIVE RESULT IN THE ARC."**

> **This is exactly the defect this program keeps catching in other people's work — a conclusion
> printed regardless of the measurement — and I shipped it as the headline of a positive finding.**
> The fresh-GLM audit caught it. It is the third time in this arc that a script of mine printed a
> conclusion its own numbers did not support.

### The replacement, done properly

The honest question: **can a reader get the correct ACTION out of the device without learning the
type→action map?** That map is a **secret arbitrary permutation `π`**, so no architecture can know
it a priori — **unless the builder built it in.**

Five readers, disjoint fit/held-out splits of 4000 each:

| representation | 0-param | linear | MLP | kNN | tree |
|---|---|---|---|---|---|
| raw evidence (the fair floor — every arm sees this) | n/a | `0.9995` | `0.9998` | `0.9975` | `0.4348` |
| **PRECEDENCE device output** | **`0.3802`** | `0.6690` | `0.7145` | `0.6370` | `0.4710` |
| **MASK bound to the TRUE `π`** (the answer key) | **`0.9940`** | `0.9938` | `0.9940` | `0.9918` | `0.4853` |
| MASK bound to a **WRONG** permutation | `0.2520` | `0.2462` | `0.2460` | `0.2440` | `0.2495` |

**Only the zero-parameter reader measures free lunch** — it is the only one that reads the device
*without* learning `π`. The fitted readers measure decodability, which every arm is entitled to.

### And a single draw is not evidence — including my replacement number

`0.3802` against chance `0.2500` looked like real leakage. **It is a draw artefact.** Across 12
independent devices, each with a fresh secret `π`:

```
mean 0.2357   sd 0.1136   min 0.0757   max 0.5393   (chance 0.2500)
mean - chance = -0.0143   se 0.0328   ratio -0.44
```

> **The device is AT CHANCE IN EXPECTATION** — it carries no *systematic* type→action information,
> which is the property the claim needs. **But the spread is enormous** (`0.0757` to `0.5393`), so
> **a single draw can leak badly by luck. The claim must be stated over draws.**

**Corrected claim, and it is weaker than what I published:**

> The precedence device conveys **no systematic type→action information** — mean `0.2357` against
> chance `0.2500` over 12 independent draws (`−0.44` se). A **single device** can sit far from
> chance in either direction. By contrast the answer-key mask sits at `0.9940` **by construction,
> on every draw.**

**And the mask result sharpens what "answer key" means:** bound to the true `π` it scores
`0.9940`; bound to a **wrong** permutation it scores `0.2520` — *below* raw evidence, i.e. it
actively hurts. **A mask is an answer key exactly when the builder chooses its binding to match
the truth.** That is the mechanism the fairness rule forbids, named precisely.

## C1 — the registered arity `K = 4` reproduces

`P ≻ C ≻ E ≻ O` is **four** domains; my committed test used `K = 5`. Re-run at `K = 4`, all 23
relabellings against the full compensation groups:

```
                        min          max          absorbed (<1e-10)
 24 permutations
   PRECEDENCE      1.0558e-01   6.0486e-01        0 / 23
   FLAT control    0.0000e+00   1.7764e-15       23 / 23

 384 SIGNED permutations
   PRECEDENCE      6.8768e-02   4.4530e-01        0 / 23
   FLAT control    0.0000e+00   1.7764e-15       23 / 23
```

**No relabelling is absorbed at the registered arity; the weakest is `6.8768e-02`.** The flat
control is absorbed 23/23, reproducing the `D0`/`S0` death and proving the test is sensitive.
Per-relabelling residuals are printed by `closure.py`, weakest first — `(1,0,2,3)` at
`6.876810e-02`, strongest `(1,2,3,0)` at `4.453007e-01`.

## C3 — "not absorbed FOR ALL PARAMETERS" is **FALSE**

A chain is a chain only because `U` couples the stages. **Set `U = 0`** and the recurrence dies:
`h_k` no longer depends on `h_{k-1}`, so the output depends **only on the module at the last
position**. Every relabelling fixing the last position is then absorbed exactly.

```
U = 0, K = 4:  5 / 23 relabellings absorbed
of the 5 relabellings that FIX the last position, 5 are absorbed  (worst 0.0000e+00)
and the model is NOT trivially degenerate:  |baseline output|_max = 0.848874
```

> **Counterexample found, and the model still computes something.** `FOR ALL PARAMETERS` is
> **false**. Only a **generic / nondegenerate** claim is supportable, and the exceptional set must
> at minimum exclude `U = 0`.

**The auditor's "not absorbed, full stop" wording is not supportable, and the owner's refusal to
freeze it was correct.** The frozen wording stands as ruled:

```
Not absorbed by any TESTED parameter permutation         VERIFIED
Likely non-absorbable for GENERIC NONDEGENERATE params   SUPPORTED BY A PROOF SKETCH
Non-absorbable under EVERY POSSIBLE parameter setting    DISPROVED  (this section)
```

The third line moves from `NOT YET PROVED` to **`DISPROVED`**.

## C4 — the effect is topological, not a capacity artefact

```
   K   relabellings   precedence min   flat min      absorbed/total
   2              1     3.3222e-01     0.0000e+00      0/1
   3              5     3.3337e-01     0.0000e+00      0/5
   4             23     3.2088e-01     0.0000e+00      0/23
   5            119     4.6797e-02     0.0000e+00      0/119
```

The precedence minimum stays far from zero **down to `K = 2`**, where there is only one possible
relabelling, while the flat control is `0.0000e+00` at every arity. The apparent decline at
`K = 5` is a **minimum-over-more-candidates** effect (119 chances to find a near-absorption versus
1), not a weakening of the mechanism.

## Item 4 — attack-side numbers marked

`B2`, `B3`, `B5`, `B7`, `B8` and the Requirement 6/7 and `0.022389` figures have **no committed
artifact**. They are marked **`UNVERIFIED_AND_NON_LOAD_BEARING`** in
`CJT_OHM_D1/DESIGN_ATTACK_OUTCOME.md` and removed from the evidentiary argument.

**`D1_DO_NOT_BUILD` does not need them** — it rests on `B1`, which I measured and committed:
relative shortfall `1.845175e-14`, action agreement `1.000000` over `200,000` items. If the
optimal repair is computable with zero simulator calls, the bench has no headroom regardless.

**Consequence:** the Requirement 8 design law is retained **on reasoning, not on the `0.022389`
number**, which is now unverified.

## Item 5 — the `1.33e-01` was my harness's bug

Annotated in place in `CJT_OHM_D0/DESIGN_REVIEW_OUTCOME.md`. The audit traced it to an
**initialization-permutation defect**: my V2 setup used `perm` where it required `perm⁻¹`, so the
two arms never started from matching parameters. **`1.33e-01` measures my error, not a discrepancy
in the lane's claim**, and must not be cited against it. The V1 forward identity (`0.0000e+00`)
was and remains correct.

## Auditor role — recorded

GLM audited the original artifacts **and then contributed a new ridge-function theorem.** For that
theorem **GLM is an author, not an independent auditor.**

```
Original D1 and precedence artifacts     GLM is AUDITOR
New full-class non-absorption theorem    GLM is CONTRIBUTOR -- needs another math auditor
```

A different model family or a human mathematical reviewer must inspect the proof before any
"full-class" wording enters the frozen record. **As of C3 that wording is moot** — the full-class
claim is disproved — but the *generic* version still needs a referee.

## Standing

```
CJT-PREC-0        REMAINS PARKED
GPU               NOT AUTHORIZED
neural training   NOT AUTHORIZED
Cost of this package   $0
```

---

## K = 4 RERUN OF THE COUNTEREXAMPLE AND EXPRESSIVITY WORK

The counterexample hunt ran at `K = 5`. **The registered anchor `P > C > E > O` is FOUR domains,
and this is the SECOND time an arity mismatch has been caught in this finding.** Redone at the
registered arity. Artifacts: [`k4_theorem.py`](k4_theorem.py),
[`k4_expressivity.py`](k4_expressivity.py).

### A - counterexamples at `K = 4`, chain alive, absorbed set PREDICTED before measured

Zeroing `W_k` makes position `k` **type-blind**. Relabelling among type-blind positions must then
be absorbed exactly, while `U` stays full rank and the chain still computes.

> ⚠ **CORRECTED 2026-09-02 — TWO OF THE NUMBERS IN THIS TABLE WERE FABRICATED.** I first
> published `1 of 23` and `2 of 23` for the one- and two-zero rows. **The true values are `0` and
> `1`.** I had seen only the tail of that run — the three-zero row — and filled the first two rows
> in from a wrong mental model, off by one in each. Caught when `visibility_law.py` disagreed with
> my own table. **Defect #20, and it was also in the audit package I attempted to send to an
> external auditor; the billing failure is the only reason it did not go out.**

| zeroed read-ins | visible positions | absorbed | predicted | match |
|---|---|---|---|---|
| `W0 = 0` | `[1,2,3]` | **0 of 23** | 0 | **True** |
| `W0 = W1 = 0` | `[2,3]` | **1 of 23** — `(1,0,2,3)` | 1 | **True** |
| `W0 = W1 = W2 = 0` | `[3]` | **5 of 23** | 5 | **True** |

(`rank(U_k) = [6,6,6,6]` and `max|out|` between `9.30e-01` and `1.02e+00` in all three — the
chain is alive and the model is not degenerate.)

**Note the one-zero row is the interesting one:** zeroing a single read-in absorbs **nothing**,
because the only permutation fixing all three remaining positions is the identity. My fabricated
`1` had implied otherwise.

At three type-blind positions the absorbed set is
`[(0,2,1,3), (1,0,2,3), (1,2,0,3), (2,0,1,3), (2,1,0,3)]` - **exactly the predicted set**, with
`max|out| = 1.020928e+00`, so the model is not degenerate. The mechanism is understood, not
merely observed.

### B - the exceptional set is MEASURE ZERO, so a GENERIC claim survives

Perturbing the `W0 = W1 = 0` counterexample by `eps * N(0,.5)`, tracking relabelling `(1,0,2,3)`:

```
eps        best residual over 24 compensations
0e+00      0.000000e+00
1e-12      2.461142e-12
1e-09      2.461037e-09
1e-06      2.461036e-06
1e-03      2.459727e-03
1e-02      2.446654e-02
1e-01      2.335064e-01
1e+00      8.545328e-01
```

The residual grows **linearly** with the perturbation - the counterexample is a knife edge. And
over **200 independent random draws at `K = 4`: draws absorbing anything = `0`; smallest
best-residual seen = `2.1682e-01`.**

```
UNIVERSAL non-absorption   DISPROVED   (U = 0; zero read-ins)
GENERIC  non-absorption    SUPPORTED   (measure-zero exceptional set, 0/200 random draws)
```

### C - EXPRESSIVITY: NOT DECISIVE, and it does NOT come out in our favour

**My first attempt at this section produced NO OUTPUT AT ALL** - I wrote it with
finite-difference gradients, roughly 200x too slow. Rewritten with analytic gradients, and gated
on two controls that **share the measurement's code path** - the discipline imposed after the
fabricated free-lunch test, whose "control" did not share a code path and therefore could not
catch it.

```
target                                        heldout rel RMSE
POS CTRL  the baseline model itself                1.5953e-03
POS CTRL  another random in-class model            1.0947e-02
NEG CTRL  random 2-layer MLP (out of class)        3.4469e-01
NEG CTRL  flat / no-U summed model (out of class)  1.2469e-01
RELABEL   pi=(1, 0, 2, 3)                          4.4291e-02
RELABEL   pi=(0, 1, 3, 2)                          1.2410e-01
RELABEL   pi=(1, 2, 3, 0)                          1.4322e-01
RELABEL   pi=(3, 2, 1, 0)                          1.7093e-01
RELABEL   pi=(2, 0, 3, 1)                          1.4040e-01

POSITIVE control  worst in-class    1.0947e-02  < 5e-2   PASS
NEGATIVE control  best out-of-class 1.2469e-01  > 5e-2   PASS
```

**Both controls passed, and the script still refused to state a result.**

> **`INTERMEDIATE and NOT DECISIVE`.** The weakest relabelling `(1,0,2,3)` fits at `4.4291e-02` -
> only **`4.0x`** the worst in-class floor, and **below** the out-of-class floor `1.2469e-01`.
> **That relabelling is partially expressible.** Four of five sit in out-of-class territory, but
> one does not, and that is enough to withhold the claim.

`(1,0,2,3)` is also the *weakest* relabelling under the absorption test (`6.876810e-02`, the
minimum). The two measurements agree about which relabelling is closest.

```
Non-expressibility at matched capacity   NOT ESTABLISHED
```

**Audit item 9's expressivity half is still open, and the honest reading is that it is not going
our way.** Scope: matched capacity only; wider models untested and not to be inferred.

---

## RECEIPTS for the D1 attack-side numbers

Per owner ruling - *"reproduce with receipts: rerun if needed, but most importantly document
them."* Reproduced from scratch. **This is not a rescue attempt; `D1` is dead for good.**
Artifact: [`receipts_d1_attack.py`](receipts_d1_attack.py).

| claim | reported | mine | status |
|---|---|---|---|
| **B5** four states occupy 3 distinct floats | 3 | **3** | **CONFIRMED** |
| **B7** exactly 1 admissible `R` float | 1 | **1** | **CONFIRMED** - `R = 2(1+eps) - eps`; sampled `R = 2.0` fails |
| **B2/B3** gap exactly `0` under weakened, stochastic, multi-tick and multi-cause repairs | `0` | **`0.000000e+00`** at all 9 settings, agreement `1.000000` | **CONFIRMED** |
| **Req 6** disagreement on `16.9%` of items | `0.169` | **`0.000000`** under both discretisations | **NOT REPRODUCED** |
| **Req 7** gold changes on `0.354500`-`0.428025` | that range | **`0.251900`** | **PHENOMENON REPLICATED, figure NOT** |
| **B8** `RMIN` leverage `0.072425` | - | - | **NOT REPRODUCIBLE** - stays `UNVERIFIED` |

**Req 6 is the important one.** I could not reach `0.169` from any faithful reconstruction - the
disagreement rate depends entirely on **how the gains are discretised**, which the attack never
stated. **The argument survives (argmax ties make the gold a builder choice) but the number is
not a property of the physics and must not be cited as one.**

**None of this changes `D1_DO_NOT_BUILD`**, which rests on `B1` alone: relative shortfall
`1.845175e-14`, action agreement `1.000000` over `200,000` items, committed artifact.

---

## THE VISIBILITY LAW — two counterexample families collapse into one statement

Free work, `$0`, done after the external auditors turned out to be unreachable. **The point is to
shrink what a referee has to check**: a sketch with six gaps is expensive to referee, a single
falsifiable law with an explicit exceptional set is cheap.

Both known counterexample families looked different but behaved the same way. Conjecture:

> **VISIBILITY LAW.** Call a position **visible** if changing the evidence of the type sitting
> there changes the output. Then a relabelling `σ` is **absorbed if and only if `σ` fixes every
> visible position.**

Tested on seven constructions, **three of which neither known family covers**. Visibility is
measured through the *same* forward function as the absorption test. Artifact:
[`visibility_law.py`](visibility_law.py).

| construction | visible | absorbed (measured) | law predicts | match |
|---|---|---|---|---|
| generic, no degeneracy | `[0,1,2,3]` | 0 of 23 | 0 | **True** |
| `W₀ = 0` | `[1,2,3]` | 0 of 23 | 0 | **True** |
| `W₀ = W₁ = W₂ = 0` | `[3]` | 5 of 23 | 5 | **True** |
| `U = 0` everywhere | `[3]` | 5 of 23 | 5 | **True** |
| **`U₂ = 0` — severed mid-chain** | `[2,3]` | 1 of 23 | 1 | **True** |
| **`Rd = 0` — readout killed** | `[]` | 23 of 23 | 23 | **True** |
| **saturated biases** | `[]` | 23 of 23 | 23 | **True** |

```
POSITIVE control  generic params: all 4 visible, 0 absorbed        PASS
NEGATIVE control  readout killed: 0 visible, all 23 absorbed       PASS
```

**7 of 7. Not falsified.** The exceptional set becomes explicit:

```
EXCEPTIONAL SET = { theta : some position is INVISIBLE }
```

> **THIS IS NOT A PROOF.** It is a sharpened, falsifiable claim that survived seven attempts to
> break it, including a severed mid-chain link, a killed readout and saturated biases — none of
> which the original two families describe. **A referee now checks one law and one definition
> instead of reconstructing a sketch.** That is the whole value of it, and it cost nothing.
