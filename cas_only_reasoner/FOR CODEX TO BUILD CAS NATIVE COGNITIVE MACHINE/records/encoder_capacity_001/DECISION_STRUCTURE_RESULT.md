# The score decomposes exactly by the shape of the decision each kind requires

**Record:** `records/encoder_capacity_001/`
**Script:** `measure_decision_structure.py` (output `decision_structure.txt`)
**Spend:** $0.00. Pure standard library. No model, no GPU, no target opened, no provider.

---

## The claim

The eight question kinds are not eight difficulties. They split into **two shapes**, the split is
visible in the public slot plan before any model runs, and it accounts for the recorded score
**exactly** — 30 + 9 = 39 at cursor 0 and 174 + 15 = 189 at cursor 160, with nothing left over.

| shape | questions | before | after | factor |
|---|---:|---:|---:|---:|
| **ONE DECISION** | **265** = 46.99% | 30/265 = **11.32%** | 174/265 = **65.66%** | **5.80×** |
| **MANY INDEPENDENT DECISIONS ABOUT ONE ENTITY** | **299** = 53.01% | 9/299 = **3.01%** | 15/299 = **5.02%** | **1.67×** |

## What each shape is

**One decision** — the answer is a single choice, from one slot or one enumerated candidate:

| kind | questions | slots | after |
|---|---:|---:|---:|
| `correspondence` | 88 | one candidate, list enumerated **in code**, 7–25 entries | **93.18%** |
| `reach` | 107 | 1 slot; `whole` and `part` supplied in the query | **75.70%** |
| `analogy` | 70 | 1 slot; a 64-way choice of isomorphic world | **15.71%** |

**Many independent decisions about one entity** — the answer is one determined fact about one
entity, and the architecture produces it as N separate per-slot classifications:

| kind | questions | slots | what the slots are readings of | after |
|---|---:|---:|---|---:|
| `edge_account` | 70 | **16** binary | the focus world's complete edge set | **0.00%** |
| `role_set` | 36 | 6 binary | roles present in a supplied focal excerpt | 8.33% |
| `parts` | 53 | 4 binary | the focus world's directly contained nodes | 22.64% |
| `context` | 70 | 5 | the focus world's declared setting and participants | **0.00%** |
| `definition` | 70 | 3 | the focus world's declared kind and function | **0.00%** |

## The corroboration, recorded per question

`admissible_answer_count` is **1** for every question of all five many-decision kinds — in both
arms, at both cursors, no exceptions:

| kind | admissible answer counts observed |
|---|---|
| `context`, `definition`, `edge_account`, `parts`, `reach`, `role_set` | **`[1]`** |
| `analogy` | `[6, 9]` |
| `correspondence` | `[1, 2, 6]` |

A question with **one** admissible answer is not sixteen free choices. It is **one fact that has
to come out right in sixteen places**, and the recorded schema says so.

## The inversion is the point

The two columns are not merely different. They are **inverted**:

> The machine scores **65.66%** where the answer is a **single choice among several admissible
> answers**, and **5.02%** where the answer is a **uniquely determined fact** that the
> architecture nonetheless spreads over many independent per-slot decisions.

Being *told the answer is unique* is the worse case, not the better one, because uniqueness is
exactly what the architecture has no way to exploit: the forward pass emits one vector per slot
and the readout takes an independent argmax per slot, so nothing can force slot 3 to agree with
slot 1, and nothing knows that the sixteen edge slots are sixteen readings of one graph.

## How this lines up with everything already measured

The same split predicts the `free bits` ordering in `answer_conjunction.txt` (above roughly 10
bits of required answer content the machine has never once been right), and it explains why
`correspondence` — the one kind whose composition is done **in code**, by
`answers.correspondence_candidates` — is the best result in the run at 93.18% while the kind with
the most slots is the worst at 0.00%.

It also explains the whole-course numbers without any other factor: teaching moved the
one-decision half by **5.80×** and the many-decision half by **1.67×**, and both halves together
account for the recorded 6.9149% → 33.5106%.

## The design tension this exposes, stated but not resolved

For four of the five many-decision kinds (`context`, `definition`, `edge_account`, and `parts`
given its argument) the query states `focus_world_id` directly, and the world's declarations are
in the packet. So the machine is being asked to **reproduce, by 64-way classification, an
identifier the question supplies and the document declares.**

That is a defect in the task's decision structure. It is **also** a boundary problem, and the
boundary is not mine to draw: if every one of those 34 slots is derived from the declared
structure, the answer becomes a lookup and the evaluation stops measuring the machine. Round 7 of
this record already found one variant that crossed that line — pre-selecting the focus world's row
into the *encoding* — and withdrew it as task deletion.

**The two are not the same thing, and the difference matters:**

- **Task deletion** gives the machine the answer in its input. It does not make the task easier;
  it removes it.
- **A composition layer** leaves the machine to resolve which entity the question is about, and
  requires that the readings of that entity be **derived and consistent** rather than decided
  independently. It does not hand over an answer; it removes an architectural inability.

Which of those two a proposed change actually is has to be judged per change, by the owner, against
the frozen course contract. This record states the measured gap and does not choose.

## What is NOT established here

- **Nothing was executed.** Every number is a grouping of recorded correctness flags.
- **The kind-to-shape mapping is a reading of the schema**, taken from `answers.RULES`,
  `answers._ARGUMENTS` and the public slot plans. It is not a claim that the course contract
  intends those shapes.
- **The exactness of the decomposition is arithmetic, not causation.** The two groups partition
  the kinds, so their totals must sum to the recorded total. What is informative is the **contrast**
  between 65.66% and 5.02%, not the arithmetic identity.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`. The other five runs of the study
  have not been decomposed this way.
- **No architecture change is proposed here.** The proposal is a separate document and is not
  authorised by this measurement.
