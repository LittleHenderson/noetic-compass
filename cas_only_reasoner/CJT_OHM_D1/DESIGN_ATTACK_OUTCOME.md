# CJT-OHM-D1 — `D1_DO_NOT_BUILD` as specified, **and the first constructive result in the arc**

```
D1_DO_NOT_BUILD: ZERO_HEADROOM_MODEL_BASED_SEARCH_IS_FREE_AND_OPTIMAL
                 GOLD_NOT_UNIQUE_UNDER_ITS_OWN_SIMULATOR
                 GOLD_UNSTABLE_ACROSS_FROZEN_COST_LAWS
                 REQUIREMENT_2_FAILS_ON_ITS_OWN_WORKED_EXAMPLE

KEPT AS A LICENSED ASSET:
PRECEDENCE_CHAIN_BREAKS_SYMMETRY_WITHOUT_AN_ANSWER_KEY
```

**Fifth design retired at `$0`.** Design attack only, per owner authorization — no
implementation, no training, no AWS GPU, no CNCM integration.

> **This death is a DIFFERENT KIND from the previous three.** `EX1`, `D0` and `S0` died because
> the CAS content was a **nameplate**. `D1` does not die that way. **`D1` dies because its TASK is
> trivial** — and on the way to killing it, the attack found, and I confirmed, the thing three
> reviews had failed to find: **a symmetry-breaking device that is not an answer key.**

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
