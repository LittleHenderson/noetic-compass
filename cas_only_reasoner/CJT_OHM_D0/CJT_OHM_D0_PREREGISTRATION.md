# CJT-OHM-D0 — EQUAL-CONDUCTANCE DIAGNOSTIC REPAIR BENCH — PREREGISTRATION v0.1

**Status:** `DESIGNED — NOT BUILT — NOT ATTACKED — NOT AUTHORIZED TO RUN`
**Owner ruling 2026-09-02:** typed diagnosis and next-tick repair is the **primary next
hypothesis**. `GPU: NO, until audit and preregistration.`
**Builder:** Claude. **Auditor:** to be named; not Claude.
**Cost:** `$0` to design. Stage 1 is CPU. No GPU is requested by this document.

---

## 0. Conflict of interest

I produced the `C8` result this bench exists to test properly, and the owner has already
corrected my framing of it once — I measured a coefficient-only competitor and reported it as
though it settled something about CAS. **That correction is the reason this bench exists**, and
it is the reason I must not audit it.

## 1. The question, frozen

> Given **identical current conductance** but **different underlying causes**, does the typed
> CAS-Ohm factorisation learn the correct **next-tick repair** better than a matched
> **full-information generic controller** receiving the same raw fields?

**What this is not.** It is not *"can a coefficient pick the repair"* — `CJT-OHM-0R` `C8` already
showed it cannot, and that is a statement about coefficients, not about CAS. The generic
competitor here sees **every field the CAS controller sees**, as a flat vector.

CAS earns something only on: **sample efficiency, unseen combinations, repair-error rate,
next-tick recovery, diagnosis fidelity, and permission enforcement.** Never on expressiveness —
`CJT-OHM-0R` `C15` proved the law restricts nothing.

## 2. Gold by causal simulation, never by declaration

**The owner's constraint, and the most important line in this document:**

```
enumerate the legal repairs
simulate the next tick under each
verify the resulting Effect
select the lowest-cost repair that succeeds
EXCLUDE TIES
```

**No human, and no builder, declares which repair is correct.** In `CPB-0` the status was
selectable by one line in the corpus generator. The equivalent free parameter here is the
**repair-cost function**, and it is where this bench would die.

> **REGISTERED:** the cost function is frozen before any run, and the result **must** include a
> **sensitivity analysis across at least three cost functions**. If the ranking of arms changes
> with the cost function, the result is `STATUS_NOT_EMITTED`. A finding that depends on my
> choice of costs is my choice, not a finding.

## 3. The pre-check that could kill this bench before it is built

**Registered as the first thing to measure, before any arm is scored:**

> **`GATE_REPAIR_NOT_TRIVIALLY_RECOVERABLE`** — is the correct repair recoverable by a rule that
> uses no controller at all? Candidates that must ALL be measured and ALL fail:
> `argmax` over resistance components; `argmin` over `V`; "always repair the largest single
> deficit"; "always pick the cheapest legal repair"; "always pick the most frequent repair in
> training"; the repair implied by the single largest field of the raw state vector.

If any trivial rule reaches high accuracy, **the bench is dead and no controller comparison
means anything.** Six label-free shortcuts have been found in this program's benches; three were
created by the repair for the previous one. This gate exists because I expect a seventh.

## 4. Arms — the owner's list, with what each is for

| arm | receives | role |
|---|---|---|
| `D0_NO_REPAIR` | — | floor: never repairs |
| `D1_RATIO_ONLY` | `g = V/R` and nothing else | the coefficient-only competitor `C8` already beat — kept as the **documented weak arm**, never as the bar |
| `D2_GENERIC_FULL_STATE_MLP` | **all raw nongold fields, flat** | **THE BAR.** The owner's correction made explicit |
| `D3_GENERIC_MONOTONE` | same fields, monotone-constrained | a *structured* generic — tests whether monotonicity alone explains any CAS gain |
| `D4_CAS_TYPED_REPAIR` | same fields, CAS-Ohm factorisation + typed repair rules | the mechanism under test |
| `D5_CAS_TYPES_SHUFFLED` | same fields, type↔repair correspondence broken | **if this does not hurt, the typing is ornamental and the lane closes** |
| `D6_ORACLE` | the simulated gold | ceiling, never a method |

`D3` is the arm I expect to be decisive. If a *generic monotone* controller matches `D4`, the
finding is `MONOTONE_STRUCTURE_SUFFICIENT` — structure helped, the CAS form did not.

## 5. Task families

Each case: a state with **matched conductance** across junctions but a **different cause**.

```
LOW_DRIVE            V weak, resistance ordinary       -> clarify goal / deprioritise
HIGH_CONTEXT_R       Drive strong, context conflict    -> remove a context constraint
HIGH_RESOURCE_R      Drive strong, compute short       -> allocate compute / split
MISSING_WISDOM       readiness zero, prerequisite gone -> retrieve / ask / learn
POLICY_BLOCKED       hard mask closed                  -> refuse, regardless of Drive
SATURATED            operating region at ceiling       -> cap or decompose
```

**Held out:** unseen cause combinations, unseen resistance-component orderings, and a family
withheld entirely to test transfer.

## 6. Status vocabulary — separate, never OR-ed

```
STATUS_NOT_EMITTED               a precondition failed, or the cost-function sensitivity failed
REPAIR_TRIVIALLY_RECOVERABLE     a no-controller rule solved it; the bench is void
CAS_TYPED_REPAIR_SIGNAL          D4 beats D2 AND D3, and D5 shuffling destroys it
MONOTONE_STRUCTURE_SUFFICIENT    D3 matches D4; structure helped, the CAS form did not
GENERIC_FULL_STATE_SUFFICIENT    D2 matches D4; the factorisation adds nothing
CAS_TYPING_ORNAMENTAL            D5 shuffling does NOT hurt
SAMPLE_EFFICIENCY_SIGNAL         same ceiling, materially fewer examples -- reported SEPARATELY
```

`CAS_TYPED_REPAIR_SIGNAL` requires **all three**: beat `D2`, beat `D3`, and be destroyed by `D5`.
Any two without the third is not the status.

## 7. What this bench cannot settle

- **It does not test weight generation.** That claim is closed (`CJT-OHM-0R` `C1`, `C14`).
- **It does not test the cascade.** That is `CJT-CASCADE-S0`, a separate design, and the owner
  ruled it is *not* a continuation of the retired weight claim.
- **It does not license any CAS-specific claim** about cognition, only about this bench.
- **Whether it needs a GPU at all is an open question I want answered before asking for one.**
  A repair-selection task over small state vectors may be a CPU problem; `CJT-OHM-0R` was.

## 8. Not yet attacked

**Two designs in a row have been retired at `$0` by their own adversarial review** — `CMB-RP1`
(the curve could not exist; the diagnostic was misattributed) and `CPB-0` (the status was
selectable by one line). Both reviews found the shortcut *inside a preregistration I had just
committed*.

**This document gets the same treatment before a line is written.** Three things I already
expect an attacker to say, registered now so they cannot be presented as novel later:

1. *"The repair is recoverable by `argmax` over resistance components."* — §3 exists for this and
   it is the likeliest way the bench dies.
2. *"The gold depends on your cost function, so you chose the answer."* — §2 registers the
   sensitivity analysis; if the ranking moves, no status is emitted.
3. *"`D2` with enough data matches `D4`, so this is a sample-efficiency question dressed as an
   accuracy question."* — probably correct, which is why `SAMPLE_EFFICIENCY_SIGNAL` is a separate
   status and not a component of the main one.

---

# AMENDMENT A1 — OWNER RULING 2026-09-02, seven load-bearing requirements

**v0.1 is committed untouched at `47259705`.** This amendment is dated, attributed, and openly
attached — the "commit untouched first" rule exists to stop a design being *quietly* rewritten
to dodge critics, and an owner ruling recorded in the open is the opposite of that.

**Primary outcome changed.** It is **`VERIFIED NEXT-TICK RECOVERY`**, not *"predicted the repair
label"*. Predicting a label is not repairing anything.

## A1.A — `D5` may be algebraically vacuous. `PROOF_OF_NON_EQUIVARIANCE_REQUIRED`

**The most important risk, and I had missed it entirely.** If the CAS channels are renamed and
`D5` is *trained from scratch* with symmetric learnable machinery, the model simply relearns the
permutation. `D4` and `D5` would then be **the same function class under renamed parameters**,
and the shuffle would prove nothing.

> Changing the labels on the storage drawers, then letting the worker relearn where every drawer
> is, does not show the labels mattered.

**Registered:** before `D5` is accepted, enumerate the channel permutations and test whether a
parameter permutation restores the same computation and loss. **If it can, `D5` is demoted to an
implementation-conformance test** and a valid eval-time corruption replaces it:

```
train D4 normally, then shuffle source->type at EVALUATION
keep repair operators fixed, feed the WRONG causal source into each
freeze the typed read-in BEFORE training
zero-shot transfer to fault combinations where type meaning cannot be relearned
```

## A1.B — `D4` must not carry a disguised answer key

`CAS_TYPED_REPAIR` may **not** hard-code `Wisdom low → retrieve`, `resource high → allocate`,
`policy closed → refuse` and then race an MLP that must *learn* those mappings. That hands CAS
the repair table and calls the result a finding.

**`D4` receives typed channels and structural constraints. The repair policy is LEARNED, from
the same examples available to `D2` and `D3`.** A hard-coded rule controller may exist only as
**`CAS_RULE_ORACLE`** — a ceiling, never the hypothesis arm.

## A1.C — cost-robust construction gold (this replaces my rule, and it is better)

My v0.1 rule — *"if the arm ranking changes across cost functions, emit no status"* — is too
blunt. It voids a whole study for a property of individual episodes. The owner's rule filters
**episodes before training**:

```
1. enumerate all legal repairs
2. simulate the next tick
3. drop repairs that fail verification or violate authority
4. score survivors under ALL THREE frozen cost functions
5. KEEP the episode only if the same repair is uniquely optimal under all three
6. otherwise mark COST_SENSITIVE and exclude from the primary set
```

Arm rankings may then legitimately vary somewhat without voiding the study, because the gold
itself is cost-invariant by construction. **`COST_SENSITIVE` episodes are retained and reported,
never deleted** — they are the honest measure of how much of the space is cost-dependent.

## A1.D — `D_SEARCH_MODEL_BASED`: the awkward baseline that must be beaten

The gold is *made* by enumerating repairs and simulating. So the obvious question is: **why learn
a controller if the machine can just try every legal repair?**

```
D_SEARCH_MODEL_BASED   enumerate legal repairs at inference, simulate each,
                       take the cheapest verified one
```

This is an *oracle* only if the deployed system cannot reach the simulator. **If the search is
deployable and cheap, a learned controller cannot claim an accuracy win over it** — it must win
on **latency, compute, number of simulations, or operation under partial information**, and those
must be measured.

## A1.E — `D_ANON_FACTORIZED`: does factorisation help, or do CAS *meanings* help?

A CAS win might come from **having factors at all**, not from what they mean. So:

```
D_ANON_FACTORIZED   same channel count, modules, monotonic constraints, parameters and
                    compute as D4 -- but the factors are ANONYMOUS
```

The ladder now separates four different questions:

| arm | question it answers |
|---|---|
| `D2_GENERIC_FULL_STATE_MLP` | does any structure help? |
| `D3_GENERIC_MONOTONE` | does *monotone* structure help? |
| `D_ANON_FACTORIZED` | does *factorisation* help? |
| `D4_CAS_TYPED_REPAIR` | do the *particular CAS meanings* help? |

**If anonymous factorisation matches CAS, the status is `FACTORIZED_DIAGNOSIS_SUFFICIENT`** — not
a CAS-typed repair signal.

## A1.F — every practical arm sits behind the SAME hard policy mask

`CJT-OHM-0R` `C9` was reclassified: the exact-zero mask is **governance, not CAS arithmetic**. So
`D2`, `D3`, `D_ANON_FACTORIZED` and `D4` are **all** placed behind the same external hard
permission mask.

> The bench must not let the generic arm violate policy and then award CAS a safety victory for
> owning a Boolean gate.

## A1.G — the trivial-rule gate, widened

`GATE_REPAIR_NOT_TRIVIALLY_RECOVERABLE` now tests **all** of:

```
largest resistance component      cheapest legal repair          decision tree
smallest Drive                    most common training repair    nearest neighbour
first failed D/W/P prerequisite   one-field lookup table         linear classifier
repair by operating region        two-field lookup table         process of elimination
repair by previous verifier status                               model-based exhaustive search
```

**and every small subset of raw fields.** If one field or one simple rule predicts the repair
nearly perfectly, `D0` is not testing typed diagnosis — **it is testing whether a model can read
a label disguised as a number.**

## A1.H — required construction shape

Collision groups where **everything immediately visible is identical**:

```
same g    same alpha    same I_total    same immediate Effect
                    but
different underlying causal state    ->    different uniquely successful repair
```

And the cases must not be one-field mappings. Required combinations include:

```
low Drive + resource abundance            Wisdom missing + abundant compute
high Drive + severe context conflict      two simultaneous resistance sources
previous rejection + newly supplied prerequisite
policy open in one context, closed in another
```

## A1.I — three kinds of value, never OR-ed into one status

```
INFORMATION VALUE       ratio-only fails, full state succeeds
                        -> conductance alone discards causal information.
                           THIS IS NOT YET CAS VALUE.

INDUCTIVE-BIAS VALUE    CAS typed learns faster or transfers better than the
                        full-state generic controls.

GOVERNANCE/TRACE VALUE  arms perform alike, but CAS gives faithful typed reasons,
                        hard authority compliance and auditable transitions.
                        -> inspectability, NOT accuracy.
```

## A1.J — the review must be able to say no

The attack returns **exactly one**:

```
D0_DESIGN_INVALID:<typed reason>        or        D0_READY_FOR_BUILD_REVIEW
```

**No automatic build follows either.** In the owner's words: *a design review whose only possible
answer is "proceed" is a parade, not a gate.*

---

# AMENDMENT A2 — GLM AUDIT F1: the ε equality class is a SIDE CHANNEL in this bench

GLM's audit of `cbffa4a0` returned **PASS** with one minor finding. It is minor for
`CJT-OHM-0R`. **It is not minor here**, because it lands directly on `D0`'s core construction.

## A2.1 — two ε effects, one removable and one not

| ε | where | removable? | consequence |
|---|---|---|---|
| `α = i/(I + ε)` | `split_flow`, inside the `I > 0` branch | **YES — redundant, the branch already handles `I = 0`** | fixed; common-mode invariance now **exact** |
| `V/(R + ε)` | `conductance`, guards `R = 0` | **NO — load-bearing** | same-conductance equality holds only to `O(ε/R)` |

**The removable one is fixed** (`ψ` common-mode drift `1.241e-07 → 0.000e+00`). The other stays,
and its consequence is what this amendment is about.

## A2.2 — measured, and worse than the audit stated

The drift is `O(ε/I)` and `O(ε/R)`, so it **grows as flow and resistance shrink**:

```
common-mode drift      I = 10      3.750e-08
                       I = 0.1     3.750e-06
                       I = 0.01    3.750e-05

same-conductance gap   (1, 2)          vs (10, 20)     2.250e-07
                       (10, 20)        vs (100, 200)   2.250e-08
                       (0.001, 0.002)  vs (1, 2)       2.496e-04
```

## A2.3 — why this is BLOCKING for `D0`, not a footnote

`D0` requires collision groups where `g`, `α`, `I_total` and the immediate Effect are
**identical** while the cause differs. **They are not identical.** They differ by the ε-residue —
up to `2.5e-04` at small `R`.

> **A residue that varies systematically with `(V, R)` is a SIDE CHANNEL. A controller can read
> it and recover the cause it was supposed to be unable to see.**

That is an **eighth shortcut**, sitting in the construction I committed two commits ago, and it
would have manufactured a `CAS_TYPED_REPAIR_SIGNAL` out of floating-point arithmetic.

## A2.4 — registered, and measured rather than assumed

> **`GATE_EPS_NOT_A_SIDE_CHANNEL`.** Collision groups must satisfy `R ≫ ε` and `I ≫ ε` —
> registered floor `R ≥ 10⁴·ε` and `I ≥ 10⁴·ε`, putting the residue below `10⁻⁴` of the signal —
> **or** the design must state the ε equality class explicitly and construct the groups to be
> exactly equal within it.
>
> **And it must be MEASURED:** the trivial-rule gate (`A1.G`) is extended with **a classifier
> trained on the ε-residue alone**. If it recovers the cause above chance, the construction is
> invalid and the status is `REPAIR_TRIVIALLY_RECOVERABLE`.

## A2.5 — the auditor's own eligibility

GLM records that it is **no longer eligible** as the third auditor for any claim-bearing neural
result on this line, having now audited the design such a result would test. A third distinct
auditor is required. 🔒 owner-actionable.

---

# AMENDMENT A3 — `GATE_EPS_NOT_A_SIDE_CHANNEL` (A2) IS INEFFECTIVE AS WRITTEN. I wrote it; it does not work.

Found by the `CJT-CASCADE-S0` adversarial attack and **confirmed by my own re-measurement**
(artifact: `CJT_CASCADE_S0/verify_attack_findings.py`).

## A3.1 — what A2 said, and why it fails

A2 registered a floor: collision groups must satisfy `R ≥ 10⁴·ε` and `I ≥ 10⁴·ε`, "putting the
residue below `10⁻⁴` of the signal."

**Measured at exactly that floor**, with 200 collision pairs whose *ideal* conductance is
identical by construction (`V/R = 1` for every state, so `g` should be `1.0` exactly):

```
actual g range   [0.999905646599079, 0.999996657437111]
spread           9.101084e-05
best SINGLE THRESHOLD on g recovers the hidden cause at 0.820000   (chance 0.5)
```

And raising the floor does not help — it shrinks the gap without removing it:

```
R floor   relative g gap    separable by g alone?
1e+02     4.950495e-03      YES
1e+04     4.999500e-05      YES   <-- the registered floor
1e+06     4.999995e-07      YES
1e+08     5.000000e-09      YES
```

> **THE ERROR IN MY OWN REASONING: I bounded the residue's SIZE and assumed that bounded its
> USEFULNESS. It does not. The residue is SYSTEMATIC — it varies monotonically with `R` — and a
> learned controller reads sign and order, not magnitude. An arbitrarily small but consistently
> signed difference is a perfect side channel.**

This is the same class of mistake as the `D0` sparsity dial: a quantity I treated as
"small enough to ignore" turned out to be a free channel for the answer.

## A3.2 — the replacement gate

> **`GATE_EPS_EXACT_COLLISION`.** States that the design calls indistinguishable must be
> **bit-identical** in every quantity any controller can read. Two admissible constructions:
>
> 1. **Remove `ε` from the divisor.** Guard `R = 0` by construction — reject or clamp at the
>    world generator — so `g = m·ρ·ψ·V/R` is computed exactly.
> 2. **Quantize `g` before any controller sees it**, at a resolution coarser than the largest
>    achievable `ε` residue, so equal-ideal-conductance states collapse to the same float.
>
> **And it must be MEASURED, not assumed.** The trivial-rule gate is extended with a classifier
> — and, cheaper and stricter, a **single-threshold scan** — trained on the readable quantities
> alone. Above chance ⇒ `REPAIR_TRIVIALLY_RECOVERABLE`. The measurement A2 already demanded is
> retained; only A2's *floor* is withdrawn.

## A3.3 — scope

**A2's finding stands; A2's remedy is withdrawn.** The ε residue IS a side channel — that part
was right, and it came from GLM's F1. What was wrong was my belief that a magnitude floor closes
it.

`D0` remains `D0_DESIGN_INVALID` and is not revived by this amendment. A3 is recorded because
the defective gate would otherwise be inherited by `CJT-OHM-D1`, which reuses the
identical-conductance collision construction.
