# F3 — the difficulty ladder, v0.1

**Built 2026-09-20. `$0`, pure Python, no torch, no GPU. No model has been run on it.**
Build: `python records/typed_pointer_001/ladder/build_ladder.py` → `LADDER_BUILD_PASS`.
Deterministic: two builds produce **byte-identical** files. Ladder digest `4436fb6b481ff606`.

**This sits BESIDE the frozen 18 and never replaces it.** `BRAIN_LINEAGE.md` rule 4 holds: the
frozen 18 and the pass mark do not move. Nothing here reads, writes or imports them. The frozen
18 remains the GATE; this is the RULER.

---

## What it is

| | |
|---|---|
| worlds | **18** — three each at 4, 6, 10, 16, 25 and 40 nodes |
| questions | **1,072** |
| kinds | `reach` (the difficulty axis), `parts` and `edge_account` (the size control) |
| difficulty axis | **hop distance** from the whole to the part: 1, 2, 3, 4, 5, plus 0 = not reachable |
| labels | 116, **zero overlap** with the 78 labels the frozen study ever showed — proven in the build, not promised |
| score | **exact match AND a continuous graded score** in [0,1], reported together |

### Why hop distance is the axis

A `reach` question asks whether a part sits inside a whole and through what. The honest measure
of how hard that is, is **how many containment links separate them**. That axis is continuous, and
it is precisely the thing Helm 1.0's broken loop could not climb: a loop that iterates reaches
distance k at round k; one that does not is stuck at 1 forever, at round 8 or at round 800.

World size is the **second** axis and is reported separately, because size and distance are
different kinds of hard. Forty nodes at one hop is a search problem. Six nodes at four hops is a
chaining problem. Confusing them would hide which one a model actually failed.

---

## The zero-learning curves — read these before any model score

These ship **inside the artifact**, computed on the same questions. A win by a mechanism is
uninterpretable until it beats the cheapest method without that mechanism.

### `reach`, graded score, by hop distance

| baseline | d=0 | d=1 | d=2 | d=3 | d=4 | d=5 |
|---|---|---|---|---|---|---|
| `one_hop_adjacency` | 1.000 | **1.000** | **0.000** | **0.000** | **0.000** | **0.000** |
| `rank_last_guess` | 0.000 | 0.000 | 0.534 | 0.522 | 0.533 | 0.537 |
| `constant_answer` | 1.000 | 0.500 | 0.000 | 0.000 | 0.000 | 0.000 |
| **`best_zero_learning`** | **1.000** | **1.000** | **0.534** | **0.522** | **0.533** | **0.537** |
| `true_oracle_ceiling` | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

**The cliff is the whole point.** `one_hop_adjacency` — the checker's own rule applied to the
input, no learned weights — scores **1.000 at one hop and 0.000 at two**. That cliff is exactly
where Helm 1.0 lived, and it is why Helm 1.0's certified 12 of 18 sat on a floor of 11 that a
zero-learning rule already reached.

### Two things the baselines caught in my own instrument

I found both by running the zero-learning rules against this ladder, and fixed them rather than
leave them to flatter somebody later. Both are calibration facts a reader **must** have:

1. **At distance 2 and beyond the bar is about 0.53, NOT 0.00.** `rank_last_guess` — point at the
   alphabetically last label, read no links at all — scores ~0.53 at every distance ≥ 2, because
   half the graded score is the *state* and "VIA" is the correct state for everything two hops or
   further. **A model scoring 0.40 at distance 3 is worse than guessing.** Always read against
   `best_zero_learning`, never against zero.

2. **Answering nothing gets better as the task gets bigger.** `constant_answer` on `parts` climbs
   from 0.250 at n=4 to **0.567 at n=40**, because bigger worlds have more leaf nodes whose correct
   answer is the empty set, and F1 scores empty-against-empty as 1.0. So `parts` is also reported
   over the **non-empty subset** (`parts_non_empty`, 159 of 303 questions), where that same rule
   scores **0.000** at every size. A model must be able to say "nothing" — it must not be paid for
   saying it.

### `parts` and `edge_account` are a CONTROL, not evidence

`best_zero_learning` scores **1.000 on both at every size**, including `parts_non_empty`. They are
one-hop tasks, so a one-hop rule solves them perfectly, and **no score on them can ever be evidence
of learning.** They exist to answer one question: when a model's `reach` falls off, did it fall off
because of *distance* or merely because of *size*? If `parts` holds at n=40 and `reach` collapses
at d=3, the answer is distance. That is the only job those two kinds have here.

This is the same trap the frozen 18 had, named up front this time.

---

## Where a model can actually demonstrate something

**`reach` at hop distance ≥ 2. 373 questions, 18 worlds.**

| world size | 4 | 6 | 10 | 16 | 25 | 40 |
|---|---|---|---|---|---|---|
| evidence questions | 3 | 21 | 67 | 72 | 106 | 104 |

That is **twenty times** the frozen 18's population, and every one of them is a question a
zero-learning rule answers at ~0.53 by guessing and at 0.000 by reading one hop.

**A known limit, stated plainly:** at 4 and 6 nodes the distance axis is thin (3 and 21 questions)
because a small world cannot hold a long chain. Read the distance curve at **n ≥ 10**. The 4-node
rung exists to connect this ladder to the frozen study's own world size, not to carry the argument.

---

## How to use it

1. Run a model over `ladder_v0_1.json`'s `questions`, producing one answer per question.
2. Score with `build_ladder.py:score(kind, predicted, gold)` — it returns `(exact, graded)`.
   **Report both.** Exact match is what the frozen grader speaks; graded is what a curve needs.
3. Plot against **`best_zero_learning` from `ladder_baselines_v0_1.json`**, on the same axes, every
   time. A curve above that line is a result. A curve tracking it is not, however good the headline
   number looks.
4. Quote the ladder digest `4436fb6b481ff606` with any number taken from it.

### What a working F1 should look like here

A prediction, not a result, recorded now so it can be checked honestly later: **Helm 1.0's
architecture cannot beat `one_hop_adjacency` at any distance ≥ 2, because one hop is its ceiling.**
Helm 2.0's loop reaches distance k at round k with `CORE_ROUNDS = 8`, so if F1 landed, its `reach`
curve should stay above `best_zero_learning` out to distance 5 and then fall. If Helm 2.0 also
tracks the cliff, F1 did not deliver what the $0 gate says it did, and that is a finding worth
more than another point on the frozen 18.

---

## Files

| file | what |
|---|---|
| `build_ladder.py` | generator, scorer and baselines — one reviewable file |
| `ladder_v0_1.json` | 18 worlds, 1,072 questions, gold answers, digest |
| `ladder_baselines_v0_1.json` | every zero-learning curve, per kind × axis × value |

## What this is NOT

- **Not a gate.** It cannot pass or fail anything. It has no threshold and no label.
- **Not a result.** No model has been run on it. Nothing is claimed.
- **Not a replacement for the frozen 18**, which is untouched, and not a licence to change it.
- **Not a claim about novel domains.** Same kind of thing: parts and containment links.
