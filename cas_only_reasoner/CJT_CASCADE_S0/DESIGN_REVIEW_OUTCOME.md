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
2. **`SEQUENTIAL_CASCADE_COMPOSITION_VALUE` is reachable but is not our question.** "Does
   sequential composition beat a parallel mixture at matched depth and parameters?" is a general
   architecture question, extensively studied outside this program, and answering it would consume
   GPU budget to produce a result with no CAS content.

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
