# CJT-OHM-D1 — `D1_DO_NOT_BUILD` as specified, **and the first constructive result in the arc**

```
D1_DO_NOT_BUILD: ZERO_HEADROOM_MODEL_BASED_SEARCH_IS_FREE_AND_OPTIMAL
                 GOLD_NOT_UNIQUE_UNDER_ITS_OWN_SIMULATOR
                 GOLD_UNSTABLE_ACROSS_FROZEN_COST_LAWS
                 REQUIREMENT_2_FAILS_ON_ITS_OWN_WORKED_EXAMPLE

KEPT, OWNER-LABELLED (NOT "LICENSED" -- that status was not granted):
ANCHORED_PRECEDENCE_NON_EQUIVARIANCE_PROVISIONAL
  = PROMISING FORMAL RESULT, PENDING INDEPENDENT AUDIT

EXPLICITLY NOT LABELLED:
CAS_OHM_SIGNAL | CAS_PRECEDENCE_ADVANTAGE | NEURAL_CJT_SIGNAL
CAS_PRECEDENCE_VALUE  ->  UNTESTED
```

**Fifth design retired at `$0`.** Design attack only, per owner authorization — no
implementation, no training, no AWS GPU, no CNCM integration.

> **This death is a DIFFERENT KIND from the previous three.** `EX1`, `D0` and `S0` died because
> the CAS content was a **nameplate**. `D1` does not die that way. **`D1` dies because its TASK is
> trivial** — and on the way to killing it, the attack found, and I confirmed, the thing three
> reviews had failed to find: **a symmetry-breaking device that is not an answer key.**
>
> **Owner ruling: this is a CJT TOPOLOGY result, not a CAS-Ohm result, and non-equivariance
> is NOT advantage. See §6.2 for the full scope limit.**

---

## 1. Why it dies: model-based search is free and optimal, so nothing can be learned

**My own re-measurement** (artifact: [`verify_d1_attack.py`](verify_d1_attack.py)):

```
200,000 items   (99,730 mask OPEN, 100,270 mask CLOSED)
max shortfall of the ZERO-CALL rule vs the 4-CALL oracle = 1.421085e-14
median oracle flow over mask-open items = 0.770163  ->  RELATIVE shortfall = 1.845175e-14
action agreement = 1.000000
0.501350 of items are settled by the 1-bit mask read alone
```

**The zero-call closed form does not approximate the oracle. It IS the oracle**, on every item.

**Why, algebraically, and this is the load-bearing point:** under `g = m·ρ·ψ·V/(R+ε)` every repair
multiplies the flow by a **gain that does not depend on the flow**. So `post = pre × gain`, and
**ranking by gain is the same ranking as ranking by outcome.**

> **The hypothesis D1 was built to test is FALSE under D1's own physics.** The premise was: *two
> states with identical present flow require different repairs because their causes differ.* Under
> a scalar flow that every repair simply scales, **the best repair does not depend on the cause at
> all** — only on which repair has the largest gain. There is nothing to diagnose.

And the structural version, which no parameter change escapes:

> **With full observability (Requirement 5 gives every arm the whole state), a 4-action set, and a
> deterministic one-tick simulator (Requirement 3), `A_SEARCH` is OPTIMAL BY CONSTRUCTION at a
> cost of 4 calls — and here, 0. It ceilings the bench. No learned arm, CAS or generic, can beat
> a free optimum.**

`A_SEARCH` was already in the registered roster. It was never a competitor; it was the ceiling.

## 2. The other blocking findings

Attack-measured unless marked. **Provenance is labelled throughout** — the `0.2096` error is not
repeated.

> ⚠ **RECEIPTS RULING 2026-09-02.** The fresh-GLM audit found that `B2`, `B3`, `B5`, `B7`, `B8`
> and the Requirement 6/7 figures **have no committed artifact** from which an auditor could
> reproduce them. They were produced inside subagent sessions whose scripts were not committed.
> Owner ruling: such numbers must be *committed and reproducible*, or removed from the
> evidentiary argument — **they may not hover in the report as ghost numbers.**
>
> **They are hereby marked `UNVERIFIED_AND_NON_LOAD_BEARING` and are NOT part of the evidence for
> `D1_DO_NOT_BUILD`.** They are retained only as a record of what the attack reported.
>
> **The verdict does not need them.** It rests on `B1` alone, which I measured myself and
> committed: relative shortfall `1.845175e-14`, action agreement `1.000000` over `200,000` items,
> artifact `verify_d1_attack.py`. `B1` is sufficient: if the optimal repair is computable with
> zero simulator calls, the bench has no headroom regardless of anything B2–B8 say.
>
> **Requirement 6 and 7 are consequently downgraded from "FAIL, measured" to "FAIL asserted by the
> attack, UNVERIFIED".** The `0.022389` correlation supporting Requirement 8 carries the same mark
> — it is attack-measured and uncommitted, so **the design law it supports is retained on
> reasoning, not on that number.**

| # | Finding | Number | Repair? |
|---|---|---|---|
| **B1** | zero headroom (§1) | mine `1.845175e-14` relative, agreement `1.000000`; theirs `0.000000e+00` | **NO** |
| **B2** | the proposed fixes change nothing — partial/stochastic repair strength and a multi-tick budget all leave the gap at zero | attack: gap `0.000000e+00` at strength `1.00, 0.75, 0.50, 0.25, 0.10` | **NO** |
| **B3** | multi-cause opens no window against the correct baseline | attack: gap `0.000000e+00` at 1, 2 and 3 simultaneous causes | **NO** |
| **B4** | `A_CAS` and `A_ANON` are the same function at the base architecture | attack: worst `7.1054e-15` over all 120 permutations, negative control `2.2122e+01` | **YES — §3** |
| **B5** | Requirement 2 fails on the specification's own worked example: the four states said to share conductance `0.5` occupy **3 distinct floats**, and the closed-policy state sits at exactly `0.0` | attack | **PARTIAL** — 3-way collision constructible, 4-way arithmetically impossible |
| **B6** | a large share of the bench is settled by a 1-bit read | **mine: `0.501350`**; attack: `0.249850` (different cause priors) — `m==0 → REFUSE` at recall `1.000000`, FPR `0.000000` | **YES** — score it separately, unscored |
| **B7** | the collision can only be built by back-solving from `ε`, breaking Requirement 1 | attack: exactly **1** admissible `R` float in 8193 tested, `R = 2.00000099999999969569 = 2(1+ε) − ε`; sampled `R = 2.0` fails | **NO** while `ε` is additive |
| **B8** | the headline is selectable by unstated constants — `RMIN` alone moves the CAS-minus-GEN gap by `0.072425`, exceeding the largest genuine arm separation the bench can produce (`0.068025`), and flips its sign seed-stably | attack: leverage/effect ratio `1.0647` | **PARTIAL**, moot given B1 |

### Requirement 6 and 7 both fail

- **Gold is not unique.** The simulator that Requirement 3 says *determines* the gold returns
  ties: oracle and closed form choose **different actions on `16.9%`** of items yet recover
  identically. **The gold label is a builder choice among tied outputs** — forbidden as a status
  source.
- **Gold is not stable across cost laws.** The argmax repair changes under at least one of four
  plausible frozen cost laws on **`0.354500`–`0.428025`** of states; fully disjoint argmax sets on
  **`0.016550`**. Under a magnitude cost, **`0.056125`** of states carry a gold label that
  verifiably **fails to recover a recoverable state** — Requirement 3 contradicting Requirement 8.

### Requirement 8 survives, and the attack's own refuters proved it

One lens claimed Requirement 8 was cosmetic. **It was refuted, and I accept the refutation:**
across six real arms, Pearson correlation between label accuracy and next-tick recovery is
**`0.022389`** (reproduced at `0.022779` on a second seed), with one arm ranking 3rd on label
accuracy and **last** on recovery. Recovery lost per error spans **`0.023898` to `1.000000`** — a
factor of `41.8`.

> **Requirement 8 is load-bearing, not decorative. Keep it.** One convention must be frozen
> first: the recovery credit for a **correct refusal** is unspecified and it *selects the winner* —
> at credit `1.0` one arm is last (`0.182571`); at credit `0.0` the same arm ties for first
> (`0.278576`).

## 3. THE CONSTRUCTIVE RESULT — a symmetry breaker that is not an answer key

**This is the crux `D0` and `S0` both died on**, and the attack answered it **against the
direction of its own verdict**, which is the behaviour a review is for.

**The vise:** a type-specific **action mask** breaks permutation symmetry — but it *is* the
hard-coded repair table the fairness rule forbids. Three reviews found nothing in between.

**The construction that escapes it — a NON-COMMUTATIVE PRECEDENCE CHAIN:**

- typed modules arranged in a chain, **each module's state feeding the next**;
- **position fixed externally** by the framework's own domain law `P ≻ C ≻ E ≻ O`;
- the **grounded evidence channel travels with the type**;
- **no action mask** — every module emits into the full shared action space.

**My own measurement**, all `5! − 1 = 119` relabelings, each with an inner search over all `120`
compensating parameter permutations:

```
PRECEDENCE CHAIN   best-case residual = 4.6108e-02   (logit scale 1.116813)   -> NOT ABSORBED
FLAT / no chain    best-case residual = 0.0000e+00                            -> ABSORBED
```

**The flat control is the point.** Same modules, same evidence, same relabeling test — chain
removed. It returns exactly `0.0`, reproducing the `D0`/`S0` death. **So the test is sensitive,
and the chain is what breaks the symmetry.**

**And it hands over nothing.** "Free lunch" = what a **zero-parameter** reader gets from the
device alone:

```
precedence chain       0.201300     (chance = 0.200000)
singleton action mask  1.000000     -- this one IS the answer key
```

> **`0.201300` against a chance of `0.200000`. A precedence order carries no module-to-repair
> binding, so it hands over zero bits of the answer, while breaking the symmetry that made three
> previous designs vacuous.**

**Why it works:** the module at position `k` reads its type's grounded evidence **and** the
previous module's state. Relabelling types across positions changes **which evidence enters at
which depth**. A parameter permutation can move modules around, but **it cannot move a module's
place in the chain**, because the position order is fixed externally by the domain law. The
composition genuinely differs.

**In the owner's own terms:** the type governs **what evidence it may read** and **when it may
read it** — two of the eight mechanism-governing properties. **Not a label. Not an index.**

**Attack's figure for the same quantity was `8.4932e-01`** from its own construction and scale;
mine is `4.6108e-02` from mine. **Different constructions, not interchangeable numbers** — both
are far from zero, and both have a `0.0` negative control.

## 4. What a successor would need

`D1`'s defect is **its world, not its architecture.** The architecture question now has a positive
answer; the task does not.

For any successor to have headroom, **the optimal repair must stop being computable without
diagnosis.** That requires breaking at least one of these three, all of which `D1` currently has:

1. **Full observability** — Requirement 5 gives every arm the whole state, and the whole state
   determines the cause. **Parity is satisfiable, so the bench is trivial; the only way to make
   CAS win is to break parity, which the fairness rule forbids.** This is the real vise in `D1`.
2. **A free optimal oracle** — a deterministic one-tick simulator with a 4-action set makes
   `A_SEARCH` optimal at 4 calls. A larger action space, a longer horizon, or a costly/absent
   simulator would change this.
3. **Purely multiplicative repairs on a scalar flow** — which makes gain-ranking equal
   outcome-ranking. Saturation, budgets, or cause-dependent gains break the identity; the attack
   measured that partial strength, stochastic strength and multi-tick budgets do **not**.

**No repair to `D1` is proposed here, and none should be attempted without a ruling.** The
program's rule stands: *no automatic second repair.* Four previous repairs in this program each
manufactured the next problem.

## 5. Verdict

```
CJT-OHM-D1 as specified          D1_DO_NOT_BUILD
Cause of death                   the TASK is trivial, NOT that the typing was a nameplate
Requirement 8                    SURVIVES -- keep it, freeze the refusal-credit convention
Requirements 2, 6, 7             FAIL as written
Precedence-chain symmetry break  CONFIRMED, and free-lunch is at chance
Cost                             $0 -- design attack only, no build, no GPU, no training
```

**What is now OPEN and better posed than before:** the typed-diagnosis hypothesis needs a world
where knowing *why* the flow is low actually changes what you should do. `D1` proved that its own
world is not such a world. **That is a real narrowing of the search space, not a null result.**

---

## 6. OWNER RULING 2026-09-02 — `D1_DO_NOT_BUILD` RATIFIED; the finding is RELABELLED; and I was WRONG about observability

```
RATIFY                D1_DO_NOT_BUILD
PRESERVE              the epsilon-side-channel repair
                      the next-tick recovery metric
                      the typed-diagnosis hypothesis
                      the precedence-chain artifacts
LABEL IT              ANCHORED_PRECEDENCE_NON_EQUIVARIANCE_PROVISIONAL
DO NOT LABEL IT       CAS_OHM_SIGNAL
                      CAS_PRECEDENCE_ADVANTAGE
                      NEURAL_CJT_SIGNAL
EXTEND AUDIT          include commit 90248303
DO NOT AUTHORIZE      D1 implementation | neural training | GPU spend | CNCM integration
AFTER A PASSING AUDIT authorize DESIGN ONLY for CJT-PREC-0
```

### 6.1 MY ERROR — the "full observability vise" was wrong

I wrote in §4 that breaking full observability *"is forbidden by the fairness rule."* **That is
incorrect, and it mattered, because it was the reason I said the successor had no clean exit.**

> **Owner:** *Fairness requires that all **practical** controllers receive the same information.
> Fairness does NOT require that every practical controller receive the complete hidden state.
> The oracle may receive the hidden state, but only as a ceiling.*

**I conflated "the same information across arms" with "all the information."** They are different
constraints. Equal **partial** observability satisfies fairness perfectly.

**And that is the clean way out of the D1 trap.** Instead of handing every controller the full
state plus an exact simulator, require **diagnostic actions that cost something**:

```
inspect goal state
check knowledge availability
probe resource pressure
inspect contextual conflict
request one additional observation
```

The controller must decide **what to inspect, in what order, and when it has seen enough to
repair**. **Now diagnosis has a real job.** §4's list of three things to break stands, but the
first one is not blocked at all — it is the recommended route.

### 6.2 SCOPE NARROWED — what the precedence result does and does not support

**Supported, provisionally, pending audit:**

> **`ANCHORED_PRECEDENCE_NON_EQUIVARIANCE_PROVISIONAL`** — a type can become computationally
> meaningful when it governs **where evidence enters and when it is processed**.

**NOT supported. None of this was tested:**

```
P > C > E > O is the best processing order
CAS beats a generic recurrent chain
the precedence chain learns faster
the precedence chain generalizes better
CAS-Ohm improves the chain
the mechanism works in a neural network
the resulting system reasons better
```

**Two limits the owner named, both correct:**

1. **This is a CJT TOPOLOGY result, not a CAS-Ohm result.** CAS-Ohm may later regulate flow
   through those stages, but `V/R` is **not** what produced the non-absorption.
2. **A generic controller with the same fixed stages may still LEARN the same function.** My test
   covered **compensating permutations**, not every possible learned reparameterization or
   alternative recurrent controller. **Non-equivariance is not advantage.**

```
PRECEDENCE_CHAIN_MECHANISM_NON_EQUIVARIANCE   PROVISIONALLY SUPPORTED
CAS_PRECEDENCE_VALUE                          UNTESTED
```

### 6.3 Enlarged absorption group — audit item 9, partially answered by me

The owner's audit item 9 asks whether a **more general transformation than a simple parameter
permutation** absorbs the mechanism. My original test used the weakest group, so it proved less
than I implied. I enlarged it.

`tanh` is **odd**, so the transformations satisfying `tanh(Tx) = T·tanh(x)` are exactly the
**signed permutations** — a group `2⁵ = 32` times larger, and the correct natural absorption group
for this architecture. Artifact: [`extend_absorption_test.py`](extend_absorption_test.py).

```
over 119 relabelings x 3840 SIGNED permutations

  PRECEDENCE CHAIN      4.0097e-02      (permutation-only test gave 4.6108e-02)
  FLAT (D0/S0 shape)    0.0000e+00      (permutation-only test gave 0.0000e+00)
```

**The chain survives the 32x larger group; the flat control is still exactly absorbed.** The
attacker having more options moved the residual only from `4.6108e-02` to `4.0097e-02`.

> **This strengthens the ABSORPTION result. It does NOT touch the EXPRESSIVITY question** — a
> generic recurrent chain of the same depth may still *learn* the same function. That is a
> different question, it remains open, and it is the real limit on the claim.

### 6.4 The one D1 result that survives, and why it is a design law

Repair-label accuracy and actual next-tick recovery correlate at **`0.022389`** — nearly no
relationship. **A controller can be good at naming a repair category while being terrible at
actually fixing the state.**

> **PRESERVED AS A DESIGN LAW: the primary measurement must be "did the selected repair produce a
> verified recovery on the next tick?" — never "did the controller predict the expected repair
> label?"**

### 6.5 `CJT-PREC-0` — Precedence-Anchored Diagnostic Control Bench

**SPECIFICATION RECORDED. NOT AUTHORIZED. Design may be authorized only AFTER a passing audit,
and it is a NEW LANE, not a repair of `D1`.**

**Question:** does an anchored CJT precedence chain learn to **gather evidence** and repair a
**partially observed** fault more efficiently or reliably than matched generic controllers?

**World:** hidden causes that initially produce the same conductance, relative allocation, total
flow and immediate Effect. Controllers **cannot see the cause** — they must probe. Repairs must be
**state-dependent, bounded, nonlinear or noncommutative, able to change later observations, and
able to succeed in one state and fail in another**. Worked examples the owner gave:

```
retrieve knowledge before splitting        may succeed
split before retrieving knowledge          may waste the budget
clarify the goal before allocating         may expose that no extra compute was needed
allocate resources before checking policy  may perform prohibited work
```

**Now order genuinely matters.**

**Arms:**

```
P0  ZERO-CALL RULE               cheap closed-form shortcut (mechanism-free baseline)
P1  FLAT GENERIC CONTROLLER      same observation history, one generic model
P2  GENERIC RECURRENT            same observations and action budget
P3  ANONYMOUS FIXED CHAIN        same depth and factorization, no CAS meanings
P4  LEARNED-ORDER CHAIN          learns its own processing order
P5  CAS PRECEDENCE CHAIN         frozen P > C > E > O
P6  REVERSED OR RANDOM PRECEDENCE matched sequential machinery
P7  MODEL-BASED SEARCH           same observation and simulation budget
P8  FULL-STATE ORACLE            CEILING ONLY
```

**A real result requires** the CAS precedence chain to: recover more states · use fewer diagnostic
probes · need fewer training examples · transfer better to unseen fault combinations · stay above
the anonymous fixed chain · beat or match the learned-order generic chain · **lose its advantage
when source-to-position wiring is corrupted after training** · and **never receive hidden state or
a repair table**.

**Registered outcomes:**

```
anonymous or learned generic chain ties it   SEQUENTIAL FACTORIZATION SUFFICIENT
CAS wins on examples / unseen combinations   CAS_PRECEDENCE_INDUCTIVE_BIAS_SIGNAL
cheap rule or bounded search solves it       BENCH_INVALID_OR_GENERIC_SEARCH_SUFFICIENT
```
