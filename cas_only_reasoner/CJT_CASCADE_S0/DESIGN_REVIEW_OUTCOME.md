# CJT-CASCADE-S0 — `S0_DO_NOT_BUILD_AS_A_CAS_BENCH`

```
S0_DO_NOT_BUILD_AS_A_CAS_BENCH: SPAN_GATE_VACUOUS
                                ORDER_ABSORBED_NO_CAUSAL_CONTROL_AVAILABLE
                                EFFECT_SIZE_IS_A_FREE_DIAL
                                EFFECT_EXISTS_ONLY_WHERE_DEPTH_IS_UNMATCHED
```

**Fourth design retired at `$0` in a row.** Authorized as design; the design review killed it
before a line of bench code was written. No implementation, no training, no GPU, no spend.

> **The owner authorized this lane on the strength of one surviving result. That result does not
> survive re-measurement. I checked it first, before designing anything on top of it.**

---

## 1. The lane's justification is gone

`CJT-CASCADE-S0` existed because `CJT-OHM-0R`'s `C13_SPAN_GATE` reported the cascade sitting
**outside** the additive family while a matched additive control sat **inside** it. That was the
one non-vacuous fact left after the additive weight-generation claim closed.

**Three separate defects, all measured on the committed code** (artifact:
[`verify_span_gate.py`](verify_span_gate.py), runnable, `$0`):

### 1.1 The recorded number was never this package's

```
committed, standalone      cascade 0.054458   additive 1.785643e-15
committed, full run        cascade 0.0746     additive 1.473e-15
recorded everywhere        cascade 0.2096     additive 3.0e-16
```

`0.2096` was **GLM's figure from its own independent reimplementation**, transcribed by me into
`CJT_OHM_0R_FINDINGS.md` §13 and from there into the spec sheet and memory as if it were ours.
The implementations differ by **`3.85×`**. The two committed figures differ from **each other**
because the value depends on how much of the shared random stream ran first — **it is not a
stable quantity**.

### 1.2 The object measured contains no CAS

**`Basis.__init__` draws `W0`, `A`, `B` and `U` entirely from `RNG.normal`.** There is no CAS
content in the thing being scored. So the honest reading of `C13` is: *what does a random system
score?*

Fifteen independent random systems, exact `c13` protocol (`trials=200`):

```
min 0.026937   mean 0.047810   max 0.071911   sd 0.013662
```

**Every one is "outside the additive span."** The committed value sits at the **60th percentile,
`0.49` sd from the random mean.**

> **The gate distinguishes a PRODUCT of matrices from a SUM of matrices. That is linear algebra,
> not a finding, and it carries no information about CAS.**

### 1.3 Ninth shortcut — the effect size is a free dial

`s = 0.7` is hard-coded in `Basis.__init__`; no registered gate constrains it. Fresh `Basis` and
fresh trial stream per row:

| `s` | additive | cascade | mean `‖s·ΔW_j‖₂` | `c13` gate |
|---|---|---|---|---|
| 1.000 | `1.4046e-15` | `9.508132e-02` | `1.2403` | **PASS** |
| 0.700 | `3.1552e-15` | `7.815411e-02` | `0.9994` | **PASS** ← default |
| 0.500 | `1.8583e-15` | `1.502731e-02` | `0.6489` | **PASS** |
| 0.300 | `7.8447e-15` | `6.064390e-03` | `0.3897` | **PASS** |
| 0.100 | `6.2334e-15` | `1.046009e-03` | `0.1593` | **PASS** |
| 0.050 | `4.9564e-15` | `2.257632e-04` | `0.0742` | **FAIL** |
| 0.030 | `6.6746e-15` | `7.082362e-05` | `0.0422` | **FAIL** |
| 0.010 | `5.7141e-15` | `5.990553e-06` | `0.0130` | **FAIL** |

Range **`15872×`**, exponent **`2.24`** — second order in `s`, exactly as the algebra requires:
the cross term `s²·aᵢaⱼ·ΔWⱼΔWᵢ` is the only part the additive mixture cannot express, and it
vanishes quadratically while the arms' own effect vanishes linearly.

> **One hard-coded float decides whether the gate passes. It flips to `FAIL` at `s ≤ 0.05`.**

### 1.4 And the effect lives only where the comparison is unfair

At the default `s = 0.7` the stages have mean operator norm **`1.2385` — greater than one**.
`(I + s·α·ΔW)` is nowhere near the identity. **This is not "the same model composed
sequentially"; it is a deeper, different model.** The residual is large only in the regime where
the additive arm is not a matched competitor — the unfair-depth problem the owner flagged and the
audit believed had been deferred to a GPU stage.

**`C13_SPAN_GATE` is downgraded to `VACUOUS`.**

## 2. The `D0` defect transplants exactly — there is no causal control available

The decisive question for any CAS claim here: **could a "shuffle the CAS ordering and retrain"
control ever bite?**

Measured on the **committed** construction, `Basis(12,12,3,4)`, `s = 0.7`, `n = 4`:

```
enumerated all 24 orderings of 4 stages
worst |CAS_ordered - generic_relabelled| = 0.0000e+00
```

A generic learned cascade reaches the CAS-ordered cascade's function **for free**, by indexing its
own learned stages differently. Order is a **coordinate choice**, not a mechanism.

> **This is `D0`'s `D5` failure, transplanted intact. The owner already retired
> label-shuffle-after-retraining as a control for symmetric architectures; this lane is such an
> architecture, so the retirement binds here and no `D5`-class control exists.**

**Consequence, identical in form to `D0`:** any registered status requiring *"destroyed by
shuffling the CAS order"* is **unreachable by construction**.

## 3. What that leaves, stated exactly

The cascade's genuine mathematical content reduces to one sentence, and it is not about CAS:

> **A sequential composition of matrix stages is not a member of the additive family. This is a
> property of matrix multiplication. It is true of random matrices, its magnitude is set by a free
> scale parameter, and it carries no information about CAS.**

Two things follow:

1. **`CAS_OHM_VALUE` is unreachable in this lane.** The owner's standing rule already said a tie
   yields `SEQUENTIAL_CASCADE_COMPOSITION_VALUE` rather than `CAS_OHM_VALUE`. The measurements
   above are stronger than a tie: **the CAS-specific arm and the generic arm are the same function
   class**, so the CAS branch is not merely likely to tie — it cannot differ.
2. **`SEQUENTIAL_CASCADE_COMPOSITION_VALUE` is ALSO unreachable from this gate — see §7 B4.**
   I originally wrote that the fallback status was "reachable but not our question." **That was
   wrong, and the adversarial attack caught it.** `C13_SPAN_GATE` does not measure sequence at
   all, so it cannot license the fallback either.

## 4. Applying the owner's new law to this lane

> **A CAS type must govern mechanism, not merely nomenclature.**

In the cascade lane, the only thing "CAS" contributes is **which stage runs first**. A stage
ordering is precisely a name for a coordinate, and §2 shows a renaming absorbs it exactly.

**The cascade gives CAS nothing to govern.** Ordering is not one of the eight type-bound
properties the owner registered — input authority, legal intervention, temporal law,
state-transition law, memory interface, monotonic constraint, governance authority, output
contract. It is the ninth thing on nobody's list: an index.

## 5. What would have to be true for a cascade bench to be worth building

All of these, and none is currently true:

1. **A non-absorbable corruption exists.** Some perturbation of the CAS cascade that a
   compensating reparameterization provably cannot undo. §2 found none, and the group-theoretic
   reason is that stage relabelling is a symmetry of the whole model family.
2. **The effect survives at matched depth.** The stages must be small perturbations
   (`‖s·ΔW‖₂ ≪ 1`) so the cascade and the mixture are genuinely the same capacity. §1.4 shows the
   effect is `2.3e-04` there — below any plausible seed noise.
3. **`s` is bound by a registered gate**, not chosen by the builder. No such gate exists and none
   was proposed.
4. **The ordering is externally anchored**, so that it is a claim about the world rather than a
   choice of index — and it must be anchored to something a permutation cannot follow.
5. **A mechanism-free baseline is registered and beaten.** For "sequential composition helps", the
   cheapest competitor is a plain deeper model with matched parameters. Nothing in this lane
   proposes one.

## 6. Verdict and disposition

```
CJT-CASCADE-S0                 S0_DO_NOT_BUILD_AS_A_CAS_BENCH
C13_SPAN_GATE                  VACUOUS   (downgraded, §1)
The 0.2096 figure              CORRECTED (§1.1) -- was never this package's output
Shuffle-order control          UNAVAILABLE (§2) -- absorbed at 0.0000e+00
CAS_OHM_VALUE in this lane     UNREACHABLE BY CONSTRUCTION
Sequential-composition value   REACHABLE, but carries no CAS content and is not our question
Cost                           $0 -- no build, no GPU, no training
```

**What is NOT killed.** The typed-diagnosis hypothesis is untouched: *can two states with
identical present flow require different repairs because their causes differ?* That question does
not run through the cascade at all. `CJT-OHM-D1` remains the registered specification for
attacking it, and this review changes nothing about it.

**No negative deleted. No status upgraded. `C1`, `C9`, `C12`, `C14` and the ε repair all stand.**

---

## 7. FIVE-LENS ADVERSARIAL ATTACK — independent `S0_DO_NOT_BUILD`, and it found more than I did

A five-lens attack (symmetry, mechanism-free baseline, free dials, fairness/matching, metric
gaming), each lens adversarially refuted, returned **`S0_DO_NOT_BUILD`** independently.

**Provenance discipline:** numbers below are labelled by who measured them. Mixing an outside
party's figure into our record as our own is exactly the `0.2096` error corrected in §1.1, and it
will not be repeated.

### B4 — THE GATE IS BLIND TO ORDER. **Confirmed by my own measurement.**

The attack claimed `C13_SPAN_GATE` passes even when the stages **commute exactly**, so sequence
is provably irrelevant. **I re-measured it** (artifact:
[`verify_attack_findings.py`](verify_attack_findings.py)) using diagonal stages, which commute by
construction:

```
run 1   max commutator ||dW_i dW_j - dW_j dW_i||_inf = 0.0000000000e+00   residual 6.7079809108e-03   PASS
run 2   max commutator ||dW_i dW_j - dW_j dW_i||_inf = 0.0000000000e+00   residual 7.8983833366e-03   PASS
run 3   max commutator ||dW_i dW_j - dW_j dW_i||_inf = 0.0000000000e+00   residual 3.6665606453e-03   PASS
```

Every commutator is **exactly zero** — every ordering yields the identical `W_eff` — and the gate
**passes anyway**.

> **`C13_SPAN_GATE` never measured sequential composition. It measures degree-≥2 curvature: the
> product picks up `s²` terms whether or not the factors commute.**

**This is stronger than §1 and it corrects me.** I had said the gate fails to be *CAS*-specific
but could still license the weaker sequential finding. It cannot. It reads no order at all.

### B1 — the absorption is an ALGEBRAIC IDENTITY, needing no training

Attack-measured: `worst |generic − CAS| = 0.0000000000e+00` over all `6 / 24 / 120 / 720`
permutations at `n = 3,4,5,6`. **Consistent with my own `0.0000e+00` over 24 orderings on the
committed construction** (§2).

The attack's sharpening is right and worth keeping: **`D0`'s zero was found by gradient descent
after retraining, so it could in principle have been absent. This one cannot be.** Applying
stages in order `p` *is* applying relabelled stages in canonical order. It holds before the first
gradient step.

It also counts the collapse: **4 arms collapse into 1 here** — CAS-order, fixed-random-order,
order-search, and free-matrix cascade. `D0` collapsed 3 of 7.

### B2 — TENTH SHORTCUT: the world generator is the status dial

Attack-measured, holding arms, parameter count (`36` each), training set (`N = 64`) and held-out
set (`2000`) fixed and changing **only which world is generated**:

| world | A1 (CAS order) | A2 (other fixed order) | A3 (order search) | A5 (additive, mechanism-free) | winner |
|---|---|---|---|---|---|
| cascade built in `πA` | `3.7475169164e-32` | `7.8348118691e-06` | `3.7475169164e-32` | `2.5961624335e-05` | **A1** |
| cascade built in `πB` | `1.8352175489e-04` | `3.6139328105e-32` | `3.6139328105e-32` | `1.8711245099e-05` | **A2** |
| additive world | `4.5481219199e-05` | `1.3114128926e-05` | `6.0096453119e-06` | `8.1203448801e-33` | **A5** |

CAS wins 3/3 seeds in one world and loses 3/3 in another.

> **The builder writes both the simulator's true stage order AND the arm's claimed CAS order. The
> experiment then measures only whether those two choices were made to match.** That is the
> answer-key handoff the owner explicitly prohibited, arriving through the back door.

**No repair from inside the bench.** Only an outside source fixing the generative order,
hash-committed before any arm is written, with all worlds reported.

### B3 — the FAIR generic comparator CONTAINS the CAS arm

Attack-measured: an order-searching generic arm — which is what "matched compute" actually
licenses — never loses in any world. It ties the winning fixed-order arm to the last digit in
both cascade worlds and **beats** the CAS arm in the additive world
(`3.9917752780e-06` vs `2.1692074005e-05`).

> **No reachable outcome is a CAS win.** The only channel left is sample efficiency, worth
> `6.9069` bits at `n = 5` — i.e. `120` cheap refits, a constant the generic arm buys independent
> of `N`.

Handicapping the generic arm to make room is the prohibited answer-key move.

### B5 — `GATE_EPS_NOT_A_SIDE_CHANNEL` DOES NOT FIRE. **Confirmed. This gate is mine, and it is broken.**

I registered this gate as `D0` amendment A2 two commits ago, with a floor of `R ≥ 10⁴·ε`. **I
re-measured it and the attack is right.**

```
eps = 1e-06,  collision pairs with V/R identical so IDEAL g is identical

R floor    R1             R2             relative g gap   separable by g alone?
1e+02      1.000000e-04   2.000000e-04   4.950495e-03     YES
1e+04      1.000000e-02   2.000000e-02   4.999500e-05     YES   <== MY REGISTERED FLOOR
1e+06      1.000000e+00   2.000000e+00   4.999995e-07     YES
1e+08      1.000000e+02   2.000000e+02   5.000000e-09     YES

200 collision pairs at the registered floor, ideal g = 1.0 exactly for every state:
  actual g range  [0.999905646599079, 0.999996657437111]   spread 9.101084e-05
  best SINGLE THRESHOLD on g recovers the hidden cause at 0.820000   (chance 0.5)
```

> **A magnitude floor bounds the residue's SIZE. It does not remove its CORRELATION with the
> cause. A vanishing but SYSTEMATIC difference is a perfect side channel, because a learned
> controller reads sign and order, not magnitude.**

**Repair — registered as `D0` amendment A3:** a floor cannot work. Either remove `ε` from the
divisor and guard `R = 0` by construction, **or quantize `g` before any controller sees it**, so
states with equal ideal conductance are **bit-identical** downstream. And it must be measured,
not assumed.

### What the attack found and I am NOT carrying forward

The adversarial refuters killed two of their own side's findings, which is the process working:

- **"the cascade is exactly inside an additive span"** — **refuted.** Its `1e-15` fit was a
  dictionary-rank artefact (16 vectors in `R¹²`). The matched additive control genuinely sits
  inside the span at `1.7306628453e-15` while the cascade does not.
- **one dial-lens evidence line** — **withdrawn as a tautology.** Its conclusion survives on the
  closed-form containment measured in B1 instead.

### Net effect on the verdict

`S0_DO_NOT_BUILD` was already established by §1–§2 from my own measurements on the committed
code. The attack does not change the verdict; it **removes the fallback** (B4), adds a **tenth
shortcut** (B2), shows **no outcome is a CAS win** (B3), and **breaks a gate I had registered
elsewhere** (B5).
