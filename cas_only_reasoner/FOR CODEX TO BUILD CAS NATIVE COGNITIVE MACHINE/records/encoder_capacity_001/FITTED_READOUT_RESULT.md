# FITTED_READOUT_RESULT — a fitted readout lifts half the exam and costs more than it gains

**Round 30. The first change measured to raise the many-decision half — and a net loss overall.**
**$0.00. Pure Python, standard library plus the project's pure modules. No torch, no GPU, no model,
no training, no new run.**

Script: `measure_fitted_readout_score.py`. Raw output: `fitted_readout_score.txt`.

> ## CORRECTION — round 32. The `edge_account` row below is superseded.
>
> The per-slot truth for `edge_account` read a **directed** edge as **undirected**
> (`tuple(sorted((source, target)))`), doubling the apparent edge count. Found in round 31 via an
> impossible reading, diagnosed by `probe_edge_reachability.py`, fixed, re-run. Full account:
> `EDGE_DIRECTION_CORRECTION.md`.
>
> | `edge_account`, fitted readout | as published below | **corrected** |
> |---|---|---|
> | per-slot accuracy | 59.9611% | **77.8426%** |
> | exact answers | 2.8571% / 4.2857% | **1.4286%** (fitted on the five many-decision kinds, λ = 1.0) |
> | **given its one true field** | not measured | **100.0000%** |
>
> `parts` and `context` also move slightly because the fit is shared and `edge_account`'s labels are
> fit inputs: `parts` 15.0943% → 3.7736%, `context` 4.2857% → 4.2857% (participants per-slot
> 55.0562% → 52.8090%). See `EDGE_DIRECTION_CORRECTION.md` §5.
>
> **The conclusions below stand, and one is strengthened:** the answer assembly is correct — giving
> any single-field kind its one true field yields **100.0000%** for `edge_account`, `role_set` and
> `parts` alike.

---

## 0. What was measured

Round 29 left a bridge unbuilt and named it: a fitted linear readout of the encoder's output reads the
many-decision kinds far better **per bit** than the trained block does, but per-bit readability had
been shown not to become answer-level accuracy. Those two results used different readouts, and the
one that matters — the construction `cncm/analytic_decompose.py::decompose_from_free_readout`
installs — had never been scored.

This file scores it. For every slot of every question:

```
encoded  = normalize(packet + slot)        the vector the block is handed, rebuilt exactly
features = tanh(encoded)                   the vector Fix A's block would pass through
W        = (XᵀX + lam I)⁻¹ Xᵀ Y            one-hot Y over the true symbol of each slot
score_c  = W[:,c] · features               exactly what `T = R⁻¹Wᵀ` makes the frozen readout produce
```

and then the score table goes to the project's **own** `slots.score_decisions` and
`slots.assemble_answer`. The whole decision path after the readout is the run's own; only the readout
is substituted. Five folds by question; the truth comes from the project's own
`checker.derive_target` and never enters the fit.

## 1. The harness validated itself against the run

```
                   readout      lam  edge_acc    parts  role_set   context  definition     MANY      ALL
         frozen (recorded)     None   0.0000% 22.6415%   8.3333%   0.0000%     0.0000%  5.0167% 33.5106%
```

The `frozen (recorded)` row is not a fit — it is the run's own submitted answers re-scored through
this harness. It reproduces the run exactly: **MANY DECISIONS 5.0167%** against the recorded 5.02%,
and **ALL 33.5106%**, which is the run's recorded exposed-course score at the final cursor to four
decimal places. Admissible-set sizes come out `{1: 461, 2: 15, 6: 36, 9: 52}`, summing to 564.

**An earlier version of this harness compared answers to `admissible_answers[0]` only and reported
`analogy` at 0.00% and `correspondence` at 59.0909% instead of their true rates.** It was caught
before shipping and fixed to admissible-**set** membership. The validating `ALL` row above is the
fixed version.

## 2. The result

Best fitted readout, `tanh(x)`, λ = 1.0:

| kind | q | recorded | **fitted readout** | lift |
|---|---|---|---|---|
| `edge_account` | 70 | 0.0000% | **2.8571%** | +2.86 |
| `parts` | 53 | 22.6415% | 15.0943% | **−7.55** |
| `role_set` | 36 | 8.3333% | **11.1111%** | +2.78 |
| `context` | 70 | 0.0000% | **4.2857%** | +4.29 |
| `definition` | 70 | 0.0000% | **44.2857%** | **+44.29** |
| **MANY DECISIONS** | 299 | **5.0167%** | **16.0535%** | **+11.0368** |

**This is the first change measured in this investigation that raises the many-decision half.** It
raises it from 5.0167% to 16.0535%, a **+11.0368-point** gain, and the gain is almost entirely
`definition` going from **nothing to 44.2857%** — 0 of 70 to 31 of 70.

λ is not load-bearing here: λ = 0.1 through 0.0001 give an identical 15.3846% on MANY, and λ = 1.0
gives 16.0535%. `tanh(x)` and `x` as features give identical numbers at every λ. Round 24's lesson —
that a fixed ridge penalty across differently-scaled features manufactures an apparent capability
difference — does not bite on this measurement.

`parts` **falls** 7.55 points. It is the one kind the trained block had learned (70.5314% per bit),
and a linear readout replaces a nonlinear one that had succeeded there.

λ is not load-bearing here: λ = 0.1 through 0.0001 give an identical 15.3846% on MANY, and λ = 1.0
gives 16.0535%. `tanh(x)` and `x` as features give identical numbers at every λ. Round 24's lesson —
that a fixed ridge penalty across differently-scaled features manufactures an apparent capability
difference — does not bite on this measurement.

## 2b. The fair variant, and it reverses the conclusion

Run 1 excluded `correspondence` from the fit, which made its slots uncalibrated and its share of the
score incomparable. Run 2 labels `correspondence` too — 2,598 labelled slots instead of 2,176 — so
one shared readout is fitted over the whole course:

| kind | q | recorded | run 1, correspondence **excluded** | run 2, correspondence **included** |
|---|---|---|---|---|
| `edge_account` | 70 | 0.0000% | 2.8571% | **4.2857%** |
| `parts` | 53 | 22.6415% | 15.0943% | 15.0943% |
| `role_set` | 36 | 8.3333% | 11.1111% | **11.1111%** |
| `context` | 70 | 0.0000% | 4.2857% | 2.8571% |
| `definition` | 70 | 0.0000% | **44.2857%** | 25.7143% – 27.1429% |
| **MANY DECISIONS** | 299 | **5.0167%** | **16.0535%** | **11.7057% – 12.0401%** |
| **ALL** | 564 | **33.5106%** | 18.6170% | **16.1348% – 16.4894%** |

**Putting `correspondence` into the same solve costs the many-decision half 4.0 points** (16.0535% →
12.0401%) and costs `definition` 17.1 points (44.2857% → 27.1429%). The 88 `correspondence`
questions carry long 64-symbol slot vocabularies and they dominate a single 90-class ridge fit.

**And `ALL` is a regression in both runs: 33.5106% recorded against 16.4894% at best — −17.0213
points.** Splitting that out by family:

| family | q | recorded | fitted readout (run 2) |
|---|---|---|---|
| ONE DECISION | 265 | **65.6604%** | **21.5094%** |
| MANY DECISIONS | 299 | 5.0167% | 12.0401% |
| ALL | 564 | 33.5106% | 16.4894% |

**So a fitted linear readout trades a −44.1510-point loss on the one-decision half for a +7.0234-point
gain on the many-decision half. Net, it is a loss, and the "first positive measurement" of §2 is a
positive on half the exam only.**

**Why the one-decision half collapses.** `correspondence` scores 93.18%–96.59% because the joint
candidate decoder ranks whole bijections from the readout's scores. Ridge fitted on one-hot targets
produces accurate *argmaxes* where it can, and it produces them for **25 different symbol
vocabularies at once**; it does not preserve the *relative* score structure the joint decoder ranks
on. **The frozen readout plus the trained block is a better score generator for the joint decoder
than a one-hot ridge readout is.** That is a separate and unexpected finding.

**The architectural consequence.** The architecture has **one** block and **one** readout, and the
substitution `T = R⁻¹Wᵀ` is a **single 64×64 map**. A single linear map cannot serve both task
families: fitting it for the many-decision kinds costs the one-decision kinds 44 points, and fitting
it for both is worse than the tuned machine on both counts except `definition`, `role_set`,
`edge_account` and, marginally, `context`.

**But the contract already admits two plasticity groups.** `plasticity_groups =
('operation:^6', 'bias_update_head')` — the run uses one, and the `bias_update_head` is a real
4,096-parameter module that is **absent** from the run's module (Fix C, OS-027). **Round 30's
measurement is the first evidence that the second group is not decorative: one shared map is
measurably the binding constraint.**

## 3. Why `definition` moves and `context` does not

The eight kinds differ in what their answer actually is. Read from
`cas_meta2/typed_teaching/checker.py::_derive_values`:

| kind | q | how the checker derives the answer | shape |
|---|---|---|---|
| `edge_account` | 70 | `{"edges": _edge_rows(_edges(focus))}` | **verbatim packet field** |
| `context` | 70 | `declaration_ref(focus, "setting")`, `sorted(focus["declarations"]["participants"])` | **verbatim packet fields** |
| `definition` | 70 | `focus["declared_whole"]`, `declaration_ref(focus, "kind"/"function")` | **verbatim packet fields** |
| `parts` | 53 | `_edges(focus)` filtered by `whole` | one filter step on a packet field |
| `role_set` | 36 | `focal.derive_roles(public, query)` | derivation from a supplied excerpt |
| `reach` | 107 | `_reach(focus, query)` | graph traversal |
| `correspondence` | 88 | `_isomorphisms(focus, other)` | real graph computation |
| `analogy` | 70 | `_isomorphisms(focus, other)` over the bank | real graph computation |

**And against that table, the recorded per-kind scores line up almost exactly with how close the
answer is to a verbatim packet field:**

```
verbatim packet field    edge_account  70 q   0.0000%
verbatim packet field    context       70 q   0.0000%
verbatim packet field    definition    70 q   0.0000%   ->  44.2857% under a fitted readout
one filter step          parts         53 q  22.6415%
derivation               role_set      36 q   8.3333%
```

**The three kinds whose answer is a verbatim copy of a visible packet field are the three that score
exactly zero, and all three of them move under a fitted readout.** 210 of 564 questions sit in that
class. **The machine has no read path, and the tasks that require one are precisely the tasks it
fails entirely.**

`context` moves only 4.2857 points where `definition` moves 44.2857, and both are verbatim-field
kinds of the same size and the same slot arity. Why they separate is **unmeasured**, and it is the
next question.

## 4. What this means for the objective

**The measured position, without dressing it up:**

- A fitted linear readout is the **first change measured to lift the many-decision half**: +7.0234
  points with `correspondence` sharing the fit, +11.0368 without. `definition` goes from 0 of 70 to
  18–31 of 70. `edge_account`, `context` and `role_set` all move off the floor.
- **As a whole-machine replacement it is a loss**: −17.0213 points overall, because the one-decision
  half falls 44.1510 points. `parts` also falls.
- **So it is a partial, not a fix.** Its value is diagnostic: it localises the defect to the
  **readout**, not the encoder, and it shows the deficit is *recoverable* — 210 questions whose answer
  is a verbatim packet field go from exactly zero to non-zero under a closed-form solve with no new
  information path and no new capacity.

**The architectural consequence, and where the payoff is.** The architecture has **one** block and
**one** readout, and `T = R⁻¹Wᵀ` is a **single 64×64 map**. Round 30 measures that one shared map is
the binding constraint: fitting it for the many-decision kinds costs the one-decision kinds 44
points, fitting it for both is worse than the tuned machine on both halves, and
`correspondence`'s 93.18%–96.59% depends on *relative* score structure that a one-hot ridge fit does
not preserve.

**And the contract already admits two plasticity groups.** `plasticity_groups =
('operation:^6', 'bias_update_head')`. The run uses one. The `bias_update_head` is a real
4,096-parameter module producing a proposal-only bias delta, and it is **absent** from the run's
module (Fix C, OS-027). **Round 30's measurement is the first evidence that the second group is not
decorative: one shared map is measurably the constraint, and the exam splits cleanly into two
families that need different score structure.** Separately, `/memory` appears as a `target_path` in
the recorded `aws_saved_repair_v8_001` lifecycle receipt, so a memory bias path is admitted by the
contract and unused by this run.

**Claim status, stated plainly:**

- **REAL, validated:** §1. The harness reproduces the run's own exposed-course score at 33.5106% and
  its many-decision rate at 5.0167%, from recorded artifacts plus the frozen encoder's own
  checksum-gated bytes.
- **REAL, measured:** §2 and §2b's tables. A fitted linear readout of `tanh(encoded)`, scored through
  the project's own decoder, lifts the many-decision half by **+7.0234** points (correspondence
  sharing the fit) or **+11.0368** (correspondence excluded), and costs **−17.0213** points overall.
- **NOT LICENSED:** that a run would realise either figure. The readouts are fitted out-of-fold on
  the same 564 questions. A run must *learn* one through `decompose_from_free_readout`, which today
  **refuses**: it requires `nclass == core_width` and the frozen readout is `[90, 64]`. The
  rectangular solve is an engineering step, untaken.
- **WITHDRAWN in round 29 and still withdrawn:** the 63.8% projection, and the "name the pair as one
  token" proposal.
- **OPEN:** why `definition` responds to a fitted readout (+25.71 to +44.29) and `context` barely does
  (+2.86 to +4.29), when both are verbatim-field kinds of the same size and the same slot arity. This
  is now the sharpest open question in the record.
- **OPEN:** whether two plasticity groups, rather than a better single map, is the right reading.

## 5. What this does not say

- It does not say the machine would score 16.4894% or 12.0401%. It says a readout fitted
  out-of-fold on these same 564 questions scores that, through the run's own decoder. Generalisation
  to unseen questions is untested, and the held-out development panel still cannot be scored at all.
- It does not say `parts` should be given up, only that a linear readout costs it 7.55 points. That
  cost is recorded rather than smoothed over.
- It does not authorise code. `PHASE0_RECORD_DRAFT.md` remains unsigned, and the rectangular solve
  is a proposed engineering task, not a licence.
