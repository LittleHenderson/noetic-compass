# Two separate defects, and the identification hypothesis is falsified

**Record:** `records/encoder_capacity_001/`
**Scripts:** `measure_world_consistency.py` (output `world_consistency.txt`),
`measure_answer_conjunction.py` (output `answer_conjunction.txt`)
**Spend:** $0.00. Pure standard library. No model, no GPU, no target opened, no provider.

---

## What was hypothesised, and what was measured instead

The previous round proposed that three never-answered question kinds — `context`,
`definition`, `edge_account`, together 210 of 564 questions — fail because they are 64-way
world-identification problems scored by exact match, and that the machine identifies the world
at only about twice chance. That became prediction **P5** in the phase-0 record.

The focus world is **public** — it is a field of the packet's own query — so the hypothesis was
testable against already-recorded answers without spending anything and without opening a
target. `measure_world_consistency.py` rebuilds all 564 registry packets, reads each focus
world, and checks whether the recorded answer names it.

**The hypothesis is falsified.**

| kind | answers naming the focus world (cursor 160) | correct |
|---|---:|---:|
| **definition** | **70 / 70 = 100.00%** | **0** |
| **edge_account** | **70 / 70 = 100.00%** | **0** |
| context | 54 / 70 = 77.14% | 0 |
| parts | 43 / 53 = 81.13% | 12 |
| reach | 89 / 107 = 83.18% | 81 |
| analogy | 7 / 70 = 10.00% | 11 |

`definition` and `edge_account` name the focus world in **every single answer** and are correct
in **none of them**. The machine knows which world it is being asked about and says so,
consistently, and is still never right. Identification is not their defect.

The aggregate says the same thing:

| cursor | one-world answers naming the focus world | correct |
|---|---:|---:|
| 0 (before teaching) | 324 / 370 = **87.57%** | 24 = 7.41% |
| 160 (after teaching) | 326 / 370 = **88.11%** | 80 = 24.54% |

Identification moved by **0.54 percentage points**. Correctness moved by **17.13**. Whatever
teaching improved, it was not identification — identification was already at 88% before
teaching began.

**P5 is therefore withdrawn before it was ever run.** The measurement that killed it cost
nothing and did not need a GPU. That is the intended function of a $0 measurement round.

---

## Defect A — the architecture has no referential consistency

A `definition` answer cites the focus world's declared `kind` **and** its declared `function`.
Both references are declarations of **the same world**, and the question supplies no arguments
at all (`_ARGUMENTS["definition"] = set()`), so both must resolve to the focus world.
`answers.declaration_ref(world_id, field)` builds both from one `world_id` for exactly that
reason.

**What the machine does, in all 70 answers:** it cites the focus world for one reference and a
**different world** for the other. Every `definition` answer names the focus world *plus at
least one other world* — recorded as `focus_plus = 70`, `focus_only = 0`.

This is not an identification failure. It is an **inconsistency** failure: two slots that must
resolve to the same world resolve to different worlds. `context` shows the same shape, 47 of 70
answers naming the focus world alongside another.

**And the recorded evidence says a correct answer names exactly one world.** Of the three
`context` answers that were ever correct — all three at cursor 0 — **all three named the focus
world and nothing else.**

### Why this is architectural and not a training problem

The `^6` block produces **one 64-dimensional vector per slot**. The frozen readout then picks a
symbol per slot, independently, by argmax. Nothing in the forward pass carries a variable from
one slot to another. **There is no binding mechanism and no place to put one.**

So the architecture has no way to express "this reference and that reference are the same
world", and the property that a definition answer needs is exactly that. No amount of gradient
descent on independent per-slot argmaxes will install a constraint that the forward pass cannot
represent.

**Referential consistency is a structural property and must be built, not learned.** This is
the clearest architectural gap found so far, and the strongest candidate for the single highest
payoff in the machine.

---

## Defect B — set-valued answers are classified instead of computed

`edge_account` names the focus world in 70 of 70 answers and is correct in 0. Its answer is the
**complete** edge set of the focus world's graph. `measure_answer_conjunction.py` reads the
public slot plan for every registry packet and counts what each kind's answer actually requires:

Measured, per kind, at cursor 160, with the recorded before/after rates beside it:

| kind | slots (median) | binary slots | wide slots | free bits | before | after |
|---|---:|---:|---:|---:|---:|---:|
| correspondence | 5 | 1 | 0 | 9.0 | 0.00% | **93.18%** |
| reach | 1 | 0 | 0 | 2.6 | 23.36% | **75.70%** |
| parts | 4 | **4** | 0 | 4.0 | 11.32% | 22.64% |
| analogy | 1 | 0 | 1 | 6.0 | 7.14% | 15.71% |
| role_set | 6 | **6** | 0 | 6.0 | 0.00% | 8.33% |
| context | 5 | **4** | 1 | 10.0 | 4.29% | **0.00%** |
| definition | 3 | 0 | 2 | 14.0 | 0.00% | **0.00%** |
| edge_account | **16** | **16** | 0 | **16.0** | 0.00% | **0.00%** |

`edge_account` is a conjunction over **16** binary edge-presence decisions, not the ~49 node
pairs an earlier draft of this record guessed. Sixteen, every one of which must be right. The
`edges` field's normalized loss, where a uniform prior is 1.0, barely moved across the whole
run — **0.967157 → 0.908392** — so each binary decision sat near chance the entire time. A
conjunction of sixteen near-chance events is answered correctly effectively never, which is what
was measured.

`free bits` is a lower bound on the information the answer carries. It is **not** a predicted
accuracy, and no per-slot accuracy has been measured, so no score is predicted from it here.

---

## The law the structure gives

Reading the table against the outcome, the ordering is almost perfectly monotone in required
answer content, with one instructive exception:

    2.6 bits  ->  75.70%
    4.0 bits  ->  22.64%
    6.0 bits  ->  15.71%   and   8.33%
   10.0 bits  ->   0.00%
   14.0 bits  ->   0.00%
   16.0 bits  ->   0.00%

**Above roughly 10 bits of required answer content the machine has never once been right**, on
210 of 564 questions, before or after teaching.

The exception is the best result in the table, and it is the most useful one.

| kind | what the machine is actually asked | candidate set | accuracy |
|---|---|---|---:|
| **correspondence** | **one choice from an enumerated list** | **7–25 candidates, median 25** | **93.18%** |
| reach | one choice from a small alphabet | 2–6 symbols | 75.70% |
| analogy | one 64-way choice | 64 worlds | 15.71% |

`correspondence` is the **only** kind in the whole run whose decision carries a
`correspondence_candidate_id`: 88 of 88, and 82 of 88 of those are correct. Not one of the
other 476 questions has one. Its candidates are enumerated **by code** —
`answers.correspondence_candidates` builds the bijections and `slots.compile_slots` puts them
in the plan — so the hard part, composing a graph bijection, is **computed, not learned**. The
machine is left with a single choice from 25 items and gets it right 93.18% of the time.

`analogy` is a single 64-way choice with **no** enumerated candidates, and it gets 15.71%.

> **The machine reaches 75–93% exactly when the composition is done in code and it is asked to
> make one choice. It reaches 0% exactly when the composition must be done by the network
> across independent per-slot decisions.**

This is not a coincidence of task difficulty. The recorded forward pass produces **one vector
per slot** and the frozen readout takes an independent argmax per slot. There is no mechanism by
which slot 3 can depend on slot 1's choice, and no penalty for two slots that must agree
choosing differently. So the exact-match rate is the **product** of the per-slot accuracies, and
with per-slot accuracy well below 1 that product is indistinguishable from zero past a handful
of bits.

**The architecture's missing piece is compositional structure**, in two parts:

1. **Binding** — a way for references that must denote the same object to be forced to agree
   (Defect A). `definition` splits the focus world across its two references in **70 of 70**
   answers; `context` in **47 of 70**.
2. **Computation** — set-valued and multi-part answers read off the declared structure instead
   of decided element by element (Defect B). `edge_account` spends 16 independent decisions on
   something the public declarations already state.

Both are architectural. Neither is reachable by more gradient descent, and neither is touched
by the analytic initialisation.

---

## What survives of the earlier architecture reading

The analytic initialisation is **not** refuted; its scope narrows and becomes precise.

- It raises **focus-world identification from the frozen readout's 1.24% to 63.83%**. That is
  a real gain on the slot that names the world.
- It touches **the world-naming slot only**. It does nothing for referential consistency, and
  nothing for a conjunctive edge set.
- So it is predicted to help `context` (77.14% naming, 0 correct), `analogy` (10.00% naming —
  the worst in the table) and `role_set` (0% naming, 3/36 correct), and to leave `definition`,
  `edge_account` and `parts` unmoved.

The three kinds it cannot help are **exactly the three that have never been answered**. So the
analytic initialisation, on its own, does not reach the part of the machine that is broken.

## What this says about where the payoff is

Ordered by how much of the machine each unlocks:

1. **A binding mechanism for referential consistency** (Defect A). Without it, every kind whose
   answer cites more than one declaration is unreachable by construction. `definition` 0/70,
   `context` 0/70.
2. **Set-valued answers read off the declared structure instead of classified per element**
   (Defect B). `edge_account` 0/70, `parts` 12/53. The declared structure is public and
   deterministic; the answer is a *lookup* of it, and the architecture currently spends ~49
   independent decisions on it.
3. **Analytic initialisation of the world-naming slot** (already built and validated). Real,
   bounded, and it does not touch (1) or (2).

Points 1 and 2 are the architectural payoffs the project's instructions point at. Point 3 was
the round-9 conclusion and is now correctly sized as the smallest of the three.

---

## What is NOT established here

- **Nothing was executed.** Every number is read from bytes already on disk plus public packets.
- **One arm, one seed.** `MIXED_SAME_ITEMS`, seed `20260919`.
- **"Names the focus world" is a necessary condition, not a sufficient one.** An answer can name
  the focus world and still be wrong, and `edge_account` is exactly that case. The script reports
  both counts separately and neither is presented as a score.
- **The one-world expectation is established for `context` and `definition`**, from the answer
  contract (`_ARGUMENTS` is empty for both), from `declaration_ref` building every reference from
  one `world_id`, and empirically from the three correct `context` answers. It is **not**
  asserted for `edge_account`, whose answer carries node references rather than world
  references.
- **No accuracy is predicted from `free bits`.** The structural numbers and the recorded rates
  are shown side by side and no causal model is fitted between them.
- **The referential-consistency mechanism is not proposed in detail here.** This record
  establishes the gap and its measurement, not its design. A design would need its own spec and
  its own gates.
