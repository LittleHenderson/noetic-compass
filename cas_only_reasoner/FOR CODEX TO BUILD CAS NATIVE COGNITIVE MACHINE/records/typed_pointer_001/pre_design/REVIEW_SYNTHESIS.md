# Review synthesis — what the two adversarial lenses have established so far

> Living document, started 2026-09-19 at HEAD `10aef90c`. Grown as the two reviews report. The reviewers' own
> reports are authoritative for their findings; this file exists so that a single reading gives the decision-relevant
> picture and so that a finding cannot be lost between rounds.
>
> **Status: INTERIM.** Both reviews were still running when this was written. Every number here is copied from a
> reviewer's raw output and is attributed.

## 1. The finding that matters most: the proposed input contains the answers to two of the five relational kinds

Measured by the leaks lens (`measurements/leaks_review/lk1_answer_carriers_out.txt`, lines 58-66). The design feeds
each read world's directed `contains` adjacency into message passing. That adjacency is not merely helpful — for two
kinds it **is** the answer:

| Kind | Zero-learning rule | Held-eligible questions solved |
|---|---|---|
| `parts` | answer = children of the whole argument, one adjacency hop | **5 / 5** |
| `edge_account` | answer = the complete `contains` edge set, read straight off the input | **5 / 5** |

The reviewer's own sanity line for `edge_account` reads: *"the full adjacency recomputed by the checker's own rule
(sanity: the input contains it)"* — held-eligible **5/5**, trained 19/19, records 17/17 held and 46/46 trained.

The FP2 rule this project already knew about (`parts(declared_whole) = participants − declared_whole`) solves only
**3 / 5**; the adjacency hop solves **5 / 5**. The adjacency is the wider leak.

**Why this is decisive.** The owner confirmed on 2026-09-19 that the label must require gains on the RELATIONAL kinds
— *"the ones that need the machine to follow links between a world's parts"* — and named parts, edge_account, reach,
correspondence and analogy. The measurement now shows that for two of those five, a copy of the input already
produces the answer with **no learned weights at all**. Gating on them would let the exact failure the owner wanted
to prevent pass the gate.

Applying the owner's own criterion honestly — "kinds whose answer needs relations among input elements, not one
input flag" — yields the three kinds whose answers are **not** in the input:

| Kind | Best zero-learning rule found | Held-eligible solved |
|---|---|---|
| `reach` | DIRECT iff part is a child of whole, else ABSENT | 1 / 9 |
| `analogy` | name the single different-domain world, else NO_MATCH | 0 / 17 |
| `correspondence` | node-count or edge-count rule | 0 / 20 |

So the honest RELATIONAL tier is **reach + analogy + correspondence = 19 eligible questions**, not 29.

## 2. What that does to the gate arithmetic

- Eligible held-back questions in total: **45** (50 held questions minus the 5 registered input-blind shortcuts).
- By kind: analogy 5, context 5, correspondence 5, definition 5, edge_account 5, parts 5, reach 9, role_set 6
  (`lk1_answer_carriers_out.txt` line 11; independently reproduced by `pipeline_review/r3_inputs.py`).
- A flag-copy of definition + context solves **10 of 45** with b = 10, c = 0, p = 1/1024 = **0.0009765625**. That
  alone passes the unchanged gate. This is finding FP1 and it is why the gate had to change.
- After removing the copy-solvable kinds: reach 9 + analogy 5 + correspondence 5 = **19**.
- `reach` loses a further **2** questions to the node-order dependence (finding DG3: 5 of 26 held reach records
  depend on hidden lexical ref order; 2 of the 9 eligible held reach questions).
- **Working population ≈ 17 questions.** Minimum passing b at c = 0 and p ≤ 0.01 is **7** (2^-7 = 0.0078125), and the
  rule also demands gains in at least 2 kinds and at least 2 held worlds, in **all three seeds**.

That is a materially tighter gate than the 24-26 the earlier paperwork implied. It must be stated in the protocol
before the run, not discovered after it.

## 3. The TEXT tier is not a world-reading test at all

Also from `lk1_answer_carriers_out.txt` lines 43-50:

- `role_set`'s answer comes from the query's `focal_excerpt` text alone (`focal.py:246-272`).
- A public clause-prefix map (`definition`→1, `context`→2, `analogy`→3, `correspondence`→4, `parts`→5,
  `account`→5,6) solves **6 / 6** held-eligible with zero learned weights.
- A **position-free token-bag** rule also solves **6 / 6**.
- 36 distinct token-bag signatures, and **0** of them carry more than one distinct answer.

So the answer text is part of the input. `role_set` stays OUT of the primary label and is reported only — which the
design already did, but now for a measured reason rather than a judgement call.

## 4. Do node LABEL words only buy memorisation? (learnability lens, `lb10_labels_out.txt`)

- **20 of 20** held-world node labels have their text somewhere in a trained record — 7,160 textual occurrences across
  (label, trained record) pairs. So every held world's labels are "seen" in training text, which is a memorisation
  channel of the same family as the old machine's hashed names.
- Only **2 of 20** held-world labels are ever the FOCUS of a trained question, so the exposure is not as the subject
  of a question.
- Over the 1,470-update schedule (8,180 presentations) the reader would embed held-world node labels **30,420** times,
  every one of the 20 distinct labels included.
- **Cost.** `FrameTokenizer.encode_text` measured **0.0219 s** per call. Uncached, the full 10-pass run needs 284,900
  label encodes = **6,225 s**, which is over half the 12,300 s worker deadline on its own. A one-time cache of the
  **230** distinct labels costs **5.0 s**.
- Only **one** checker line mentions a label at all (`checker.py:97`), so almost no answer depends on the words.

**Reading:** the cost argument is answered by caching and does not by itself justify dropping labels. The leak
argument does — 20/20 held labels appearing in trained text is exactly the channel this project removed from the old
machine. The outgoing agent's recommendation to drop node label words is therefore supported, but the reviewer's final
report should confirm that `checker.py:97` is not load-bearing for any kind.

## 4.5 🔴 THE LEARNABILITY LENS HAS REPORTED — and the relational tier is largely compromised ON THIS CORPUS

`DESIGN_REVIEW_LEARNABILITY_LENS.md` (60,599 bytes, 18 findings LB0–LB18, each with a severity of exactly
`BLOCKS_RESULT`, `FALSE_NEGATIVE_RISK`, `DESIGN_CHANGE_REQUIRED` or `NOTE`). Its per-kind verdict:

| kind | expressible as drafted? | what is missing |
|---|---|---|
| `role_set` | YES | nothing |
| `definition` | YES, wrong head | score ref heads on declaration text, not `g_w` |
| `context` | YES, wrong head | same |
| `parts` | YES | nothing (1 round suffices) |
| `edge_account` | RISKY | the `a→b` adjacency bit into the edge head's MLP |
| `reach` rule 2 | YES | the rule embedding (DG2) |
| `reach` rule 1 | **NO for 5 of 26 held records** | the hidden node-ref order |
| **`correspondence`** | **NO** | **a joint edge-aware mapping scorer** |
| `analogy` | text half YES, graph half weak | a non-graph-blind world vector |

**The two findings that matter most, and they hit the two kinds the leaks lens called "clean".**

1. **`correspondence` is NOT EXPRESSIBLE** (LB12, LB13, LB15). The per-node score has no input depending on the
   target world's edge set, so every permutation in the source world's automorphism group gets an identical score,
   and the tie rule picks the first syntactic bijection — measured correct in **0 of 20 held** records. In **81 of 88**
   records no admissible mapping lies in the source's automorphism group at all, so *no additive per-node score over
   these inputs can be made to prefer a correct answer*. No auxiliary channel rescues it: degree-rank 0/20 held,
   ref-rank 0/20, label-rank 0/20, and a label-preserving mapping is admissible in **0 of 88**. **Until a joint
   scorer is built and measured, correspondence must be recorded as a known false negative and removed from the
   RELATIONAL population.**

2. **`analogy` is solved by a zero-learning rule** (LB18). A *same-shape-and-different-domain* rule solves **17 of 17
   held analogy records**. The cause is LB3/LB4: only **6 non-isomorphic structures exist** in the 64-world bank
   (class sizes 12, 12, 12, 12, 8, 8), and every held world has **7, 6, 11, 6, 11** same-shape trained twins. So
   "isomorphic" is coarse enough to be found by a cheap rule.

**And the machinery that makes this work is exact, not statistical** (LB7): the **sorted (in-degree, out-degree)
multiset is a complete isomorphism invariant on this corpus** — its partition and the brute-force isomorphism
partition give the same 6 groups and coincide exactly, with **0 of 2016** non-isomorphic pairs indistinguishable
under any of the four colourings. So 1-WL is *not* the binding constraint here; the binding constraint is that
the worlds are 3–4 nodes and their isomorphism class is a degree multiset.

**Three more blockers on the learning side, all `DESIGN_CHANGE_REQUIRED` or `BLOCKS_RESULT`:**

- **LB11 — the schedule under-covers.** The rarest head sees 320 of 1,470 updates; the 64-way text choice gets
  **550 update events over 113 records**. The instruction is to rebalance so every kind appears in every pass
  (about 10 × 470 updates), or drop the untrainable heads.
- **LB9 — the `^6` initialisation is unspecified and changes everything.** Saturation ranges **75.30–98.03 %** with
  no norm, **48.02–91.83 %** with the output norm, against **7.65–13.42 %** at the torch default. Pin the
  initialisation and assert the measured saturation at pass 0.
- **LB17 — the world-level heads must not read the pooled mean.** Condition them on the marked node's state or on
  degree sums. This agrees with §5.5 and gives the concrete fix: **degree sums**, which LB7 shows are exact here.

## 4.6 What this means for the primary objective — the reframe

**On this corpus, most of the RELATIONAL answers are computable by short exact rules**, because the worlds are tiny
and their isomorphism class is a degree multiset. That is a property of the course, not of the machine. It has a
consequence that matters more than any gate tweak:

- The **RELATIONAL tier cannot be the place a learning result is won.** `correspondence` is not expressible by the
  drafted head; `analogy` falls to a shape rule; `reach` is contaminated by the rank and constant channels. The
  honest thing is to say so and grade it strictly.
- The **GRAPH-READING tier is where the neurons can genuinely be shown to learn something that transfers.**
  `parts` and `edge_account` ask the machine to read a world's own structure and answer about it. Yes, a flag rule
  or a single adjacency hop produces those answers — but **the machine does not have that rule hard-wired**; it must
  learn the mapping from node states to pointers, and whether that learned mapping transfers to a never-practised
  world is a real, falsifiable question with a real positive answer available.
- So the study can still deliver the owner's objective, **provided the label is not asked to carry more than it can**:
  report `GRAPH_READING` learning as the learning result, and the RELATIONAL tier as a strict, likely-negative test
  of something this corpus cannot demonstrate.

None of this has been acted on. It is recorded, not applied, and it is the substance of the consolidated question
now owed to the owner.

## 4.7 LB11 economics: the starving-heads fix costs 44 %, not 360 %

Finding LB11 says the schedule under-covers and instructs "rebalance so every kind appears in every pass (about
10 x 470 updates), or drop the untrainable heads". `lb11_economics.py` measured the as-is coverage and the two ways
to obey that instruction. **Measured, $0, and nothing applied.**

**As-is, at 147 updates per pass, each kind is ABSENT from a large share of updates:**

| kind | updates where ABSENT (of 147) | present |
|---|---|---|
| `role_set` | **115** | 32 |
| `analogy` | **112** | 35 |
| `context` | 107 | 40 |
| `definition` | 105 | 42 |
| `edge_account` | 95 | 52 |
| `correspondence` | 67 | 80 |
| `parts` | 63 | 84 |
| `reach` | 40 | 107 |

So a `role_set` head receives a gradient in **32 of 147** updates and an `analogy` head in **35**. The per-kind heads
are starved for most of the run. This is the mechanism behind the lens's "rarest head 320/1470".

| branch | updates/pass | presentations/pass | every kind every update? | vs as-is |
|---|---|---|---|---|
| **A as-is** | 147 | 818 | no | — |
| **B stratified** | **147** | **1,176** | **yes** | **+43.8 %** |
| **C widened (the lens's literal reading)** | 470 | 3,760 | yes | +359.7 % |

**B is the sweet spot: it fixes coverage completely for a 43.8 % presentation increase at the SAME update count.**
C multiplies presentations by 4.6× and its 10 passes need **4,716** updates, which is **above the raised ceiling of
3,544** — so C is not affordable as literally stated.

Cost context, from the practice receipts rather than modelled: 1,470 updates and 8,180 presentations took
5,465.811116 s of worker clock, i.e. about **0.6682 s per presentation**. B's extra 358 presentations per pass cost
roughly **+2,392 s** over ten passes at the old machine's rate — which fits the 12,300 s deadline against the
practice run's 5,465.811116 s, but the pointer machine's own rate is **unmeasured** and the smoke job measures it.

**Not applied.** Whether to change the registered MIXED_SAME_ITEMS composition is a design decision, and it is part
of the consolidated question owed to the owner.

## 5. Is the optimiser adequate? (learnability lens, `lb11_schedule_composition_out.txt`)
Per-head gradient exposure over the 1,470 main updates, with AdamW's second moment decaying at 0.999:

| Head | Updates receiving its gradient | Updates needed for the second moment to describe its own scale |
|---|---|---|
| node YES/NO (`parts`, `context` participants) | 1,150 / 1,470 | 1 |
| edge YES/NO (`edge_account`) | 520 / 1,470 | 3 |
| role YES/NO (`role_set`) | 320 / 1,470 | 5 |
| node scorer (`definition` whole, `reach` VIA, `correspondence` mapping) | 1,400 / 1,470 | 1 |
| world scorer (`definition` refs, `context` setting, `analogy` world) | 550 / 1,470 | 3 |
| option vectors (`reach` ABSENT/DIRECT, `correspondence` mode, `analogy` NO_MATCH) | 1,360 / 1,470 | 1 |
| role embedding table | 320 / 1,470 | 5 |
| world encoder + ^6 block | 1,470 / 1,470 | 1 |

Every head clears its own second-moment requirement by a wide margin, so the per-head gradient rule the design adopts
(review RK1) is sufficient and the 1,470-update budget is not obviously too small for the heads.

The wide output spaces are worth naming: `analogy` `world_id` has **65** symbols and `definition`
`kind_ref` / `function_ref` have **64** each, against only 36, 36 and 41 trained records of those kinds. The
world scorer is an embedding scorer rather than a classifier, so this is not automatically fatal — but it is the
place to look first if those kinds show no movement.

## 5.5 🔴 THE READOUT THROWS AWAY THE STRUCTURE THE NEURONS LEARN — the biggest learning risk found so far

From `measurements/learnability_review/lb16_pooling_resolution_out.txt` and `lb17_pool_gradient_out.txt`. These bear
directly on the main goal, so they are stated in full.

**The good news: the message passing does learn structure at the node level.** Mean cosine between node states,
`rms_after=output`:

| rounds | mean cosine of EDGE pairs | of NON-edge pairs | **gap** |
|---|---|---|---|
| 1 | 0.127477 | 0.088478 | 0.039000 |
| 2 | 0.298346 | 0.114129 | 0.184217 |
| 4 | 0.585565 | 0.197146 | **0.388418** |
| 8 | 0.835563 | 0.495154 | 0.340409 |

Two rounds already separate an edge from a non-edge, and four rounds separate them strongly. **The node states carry
the graph structure.** With `rms_after=none` the gap keeps growing through eight rounds (0.048761, 0.197758, 0.382743,
**0.406388**), so where the normalisation is applied changes which round count is best — `output` peaks at 4, `none`
peaks at 8. That is a real, testable choice the design has not made deliberately.

**The bad news: mean pooling to `g_w` destroys it.** In lb16, with node features drawn randomly per node:

```
inter-shape distance 0.831003   intra-shape distance 1.213181   ratio 0.68
```

**Two worlds with *different* shapes are CLOSER to each other than two draws of the *same* shape.** Nearest-centroid
over 123 samples recovers only **8 to 13**. The pooled world vector is dominated by node features, not by shape.

lb17 confirms it from the other direction:

| node features | relative spread of `g_w` across the 6 shape families |
|---|---|
| all identical within a world (no feature noise) | **0.0327 → 0.0798** over 1–8 rounds |
| only the 3 real flag dimensions | **0.1264 → 0.1555** |
| random per node | different-shape distance is only **0.8465–0.8927 ×** same-shape distance |

So the pure-shape signal in `g_w` is **3–8 %** of the vector, and with the real flags **13–16 %**. The world vector is
mostly a summary of *which nodes have which flags*, not of *how the world is wired*.

**Why this matters for the goal.** Every world-choice slot scores `<W [q; g_focus], g_w>` — a comparison of pooled
vectors. Those slots include `analogy` (`world_id`, 65 symbols) and `correspondence`'s target selection, which are
exactly the two kinds this review found to be the *clean, hard* tests where a genuine transferable relational skill
would show. And `lb18_analogy_structure_out.txt` sharpens it: **all 17 held analogy records require shape AND domain
together** (`correct set == isomorphic AND different domain` in 17 of 17), while a shape test alone leaves **24**
alternative candidates it cannot reject. So analogy needs the machine to read shape *and* combine it with the domain
word — and shape is the half the pooled readout is weak at.

**Claim state — corrected 2026-09-19, and this matters.** The numbers above are (a) **MEASURED** in a numpy
simulation of the draft's exact recurrence at unit level with **untrained** weights, and (b) **ANALYSED** from the
gradient path. `lb17`'s header shows the argument is stronger than "random weights happened to do this": it derives
`d g_w / d h_v^{k} = (1/N) · d h_v^{K} / d h_v^{k}`, cites a measured spectral norm of that map near **1** from LB13,
and concludes that the pooled vector receives per node essentially that node's own local update — **its own feature
plus a normalised sum of its neighbours' features, still dominated by the O(1) features rather than by a topology
readout.** So training cannot easily make `g_w` shape-sensitive.

**What this is NOT:** a measurement on a trained model. **No pointer machine exists yet**, so nothing here is trained
evidence, and the sentence *"a readout that cannot see shape cannot learn shape, however long it trains"* — which an
earlier revision of this section used — **overstated it and is withdrawn.** The precise statement is: the pooled
readout **starts** unable to separate shapes, and its gradient path is feature-dominated by construction; whether
training overcomes that is **untested**, and settling it is exactly what the local $0 smoke test in point 4 below
would do. Calling it "the most plausible way the study still fails to learn" is a judgement about risk, not a
finding.

What survives unchanged is the actionable part: the structure **is** present in the node states (gap 0.388418), so
read it there rather than through a pooling that is gradient-starved for topology.

**What to do about it — a design change, not a tweak.** The node-level signal exists, so keep it and read it out:

1. **Score structural answers at the node level, not after pooling.** `correspondence`'s mapping is already
   node-pairwise (`mapping_target` per rank) — verify the head reads node states and never `g_w`. `analogy`'s
   isomorphism test and world-choice comparison are the ones that currently go through `g_w`.
2. **Replace mean pooling with a permutation-invariant readout that preserves more.** Over 3–4 nodes, plain options
   that cost almost nothing: concatenate the **rank-sorted** node states (the rank is already a registered input, so
   sorting by it is well defined); or a sum of outer products; or attention pooling with a learned query. Any of these
   gives the head access to the wiring instead of a blur of it.
3. **Choose the round count and normalisation placement deliberately**, from the table above rather than by
   inheritance. K=4 with `rms_after=output` and K=8 with `rms_after=none` are the two candidates; the current design
   pins K=8 without having measured this.
4. **Add a smoke test that asserts it.** A local, $0 check: build the model untrained, and require that the readout's
   separation of two different shapes exceeds its separation of two draws of the same shape. Today it does not. That
   test is the guard against this class of failure ever returning unnoticed.

None of this weakens the gate or changes the claim rules. It is aimed squarely at the primary objective: giving the
neurons a readout through which the structure they learn can actually reach the answer.

## 6. The single-flag table, and the rule that reopens the rank decision

`measurements/leaks_review/lk2_single_flag_out.txt`. Best no-learning rule per kind, scored by the private checker,
over held-back **eligible** questions:

| Kind | best zero-learning rule | held-eligible solved |
|---|---|---|
| `definition` | R13, all flags | **5 / 5** |
| `context` | R13, all flags | **5 / 5** |
| `reach` | **R10, node rank == alphabetically last ref (rank only, no adjacency)** | **4 / 9** |
| `parts` | R12, the FP2 line | 3 / 5 |
| `role_set` | best rule scores nothing | 0 / 6 |
| `analogy` | best rule scores nothing | 0 / 5 |
| `correspondence` | best rule scores nothing | 0 / 5 |
| `edge_account` | best rule scores nothing **without adjacency** (R13 scores 0/5) — but the input's own adjacency solves **5 / 5**, see §1 | 0 / 5 by flag rules |

Two things stand out.

**R10 is the surprise.** A rule reading *only* the node rank, with no adjacency at all, answers 4 of the 9 eligible
held `reach` questions correctly — the largest single-flag score of any kind outside the DIRECT_READ pair. If the rank
feature is in the input, that baseline must be registered and its 4 questions removed from the gate. Those questions
are precisely the ones that do **not** require following links between a world's parts.

**R13 (all flags together) scores 13 of 45** — the definition 5 and context 5 that make finding FP1 what it is, plus
the 3 `parts` from FP2. It confirms exactly why the unchanged gate would print a false positive.

### 6.2 The naive pointing policies are weak — but the table does not cover constant answers

`measurements/leaks_review/lk3_pointer_policies_out.txt`. Zero-learning pointing policies, scored on held-eligible
questions:

| policy | held-eligible solved |
|---|---|
| point at the argument node (the query's `whole`) | 5 / 45 (all `definition`) |
| point at the query's `part` argument | 0 / 45 |
| point at the focus world plus the declared whole | 5 / 45 (all `definition`) |
| PRESENT for every non-argument node | 1 / 45 |
| PRESENT for every node and every edge pair including self-pairs | 1 / 45 |

So the pointer space is **not** trivially exploitable by pointing alone — good news for the design. But note what this
table does **not** contain: a **constant answer symbol**. It tests *pointing rules*, not *always emit symbol X*. The
`VIA n1` constant that scores 4 of 9 held `reach` (§6.1) is a choice-slot policy and is absent here. Both classes must
be registered; registering only the pointing class would leave the bigger hole open.

### 6.3 Node labels carry no information for the two hard kinds — dropping them costs nothing

`measurements/learnability_review/lb14_order_and_labels_out.txt`:

- The paired worlds of a **correspondence** question share **no** node label: `label sets equal` is 0 of 20 held,
  0 of 54 trained, 0 of 14 excluded. `label-preserving admissible` is **0** on every side.
- **Analogy**: of 123 correct candidate worlds (held), **123** have zero label overlap with the focus world.
- Rank-based shortcut rules on `correspondence` solve **0 of 20** held (`ref-rank` 0, `label-rank` 0, `degree-rank` 0).

Two consequences. First, this **confirms the decision to drop node label words**: for the two kinds where genuine
relational learning would be measured, labels carry no signal at all, so removing them (and closing the 20-of-20
memorisation channel, §4) costs the machine nothing. Second, **`correspondence` and `analogy` are clean tests** — no
cheap rule found so far solves any held question of either kind, and their answer sets are narrow (most held
correspondence questions admit exactly 1 of 24 permutations, `lb12_correspondence_head_out.txt`).

That matters for the main goal: these two kinds, with **54 and 36 trained records** behind them, are where a genuine
transferable relational skill would show, and where a gain would be hard to fake.

### 6.4 R10 re-derived and confirmed — and a claim of mine withdrawn

R10 was re-derived independently and **confirmed at exactly 4 of 9**.

**Withdrawn claim.** This section previously added that a constant `VIA n1` answer is a *second* no-learning policy
also scoring 4 of 9, and concluded that registering both would collapse `reach` to 1 question and the relational tier
to 11. **That was wrong and is withdrawn.** The lens's completed policy table
(`lk3_pointer_policies_out.txt` lines 113-139) fits a majority-symbol baseline the only honest way — on the **trained**
records' answers — and it scores **0 of 45** held-eligible and **0 of 9** on `reach`, because the trained majority for
`reach` is `DIRECT`, not `VIA n1`. The 4 × `VIA n1` breakdown of the held answers can only be reached by reading the
held answers, which the custody rule forbids; that is the answer key, not a baseline.

**Corrected position:** `reach` loses R10's 4 and DG3's 2, overlap unmeasured → **3 to 5** remaining, and the
relational tier is **13 to 15**. The §7 table already used those figures and stands.

The lesson is worth keeping: a skew is only a confound if a baseline can reach it **from training data**. My error was
computing arithmetic over the held answers and then treating the result as a policy.

## 7. The rank decision, reopened

| | Gate population | Training signal |
|---|---|---|
| rank **IN** | `reach` loses up to 4 to R10 **and** 2 to DG3 (overlap unmeasured) + `analogy` 5 + `correspondence` 5 → **as low as 13–15** | order-dependent `reach` targets stop being contradictory (5/26 held, 11/71 trained) |
| rank **OUT** | `reach` loses 2 to DG3 + `analogy` 5 + `correspondence` 5 → **17** | 11 of 71 trained `reach` records keep contradictory targets |

**Reopened because the evidence changed after the first decision.** The rank feature was chosen for the training-signal
reason before R10 was measured; R10 shows it also removes up to 4 of the 9 remaining `reach` questions, and those are
the questions that most clearly satisfy the owner's criterion of needing the machine to follow links. 17 leaves more
headroom above the floor of `b = 7` than 13–15 does.

**Not settled here.** It waits on lens A's authoritative required-removals table, which computes the real overlap
between the R10 set and the DG3 set and the real surviving population. Building `pointer_inputs.py` on either branch
before that lands would be building on a guess.

## 8. Background: the rank feature is the public node alias

`lk1_answer_carriers_out.txt` Parts G and H:

- `checker._nodes = sorted(node['ref'])` (`checker.py:72-73`) and `slots.alias_table` N0..N9 = the sorted refs
  (`slots.py:55-60`), so "rank among the world's sorted node refs" IS the alphabetical position of the hidden ref.
- **Node refs whose position in the sorted ref list equals their own stored index (`n<i>` == position `i`):
  244 of 244.** The alias table example printed by the reviewer is `[('N0', '0'), ('N1', '1'), ('N2', '2'), ('N3', '3')]`.
- Reach records whose answer changes under a node-name relabelling: held **5/26**, trained **11/71**, excluded **2/10**.

So the rank feature is the node's own public index, and it is not new information smuggled in: the node's ref
already ends in `n<i>`, and the reach answer space is literally `VIA_<node>`, so any machine that can point at a node
already carries node identity. The reviewer's concern is not that rank leaks a secret; it is that:

1. the input list in design v0.1 says in terms **"NO node alias index"**, so including rank contradicts a written
   exclusion the design did not revisit, and
2. the draft's vacuity paragraph leans on the machine being permutation-equivariant over node order, and a per-node
   index weakens that argument and changes what engineering test S9 can assert.

`INTERFACE_SPEC_POINTER.md` §2 already records the decision to include rank, with a registered rank-only no-learning
baseline and removal of the questions that baseline solves. What was **missing** is the consequence: the input list's
"no node alias index" line must be amended, and the vacuity/symmetry paragraph must stop resting on equivariance that
the design has chosen to give up. **This must be resolved explicitly in v0.2 §5 and §6, and S9 re-specified, before
the protocol is frozen** — not left as an unremarked contradiction between two documents.

Note this section was written **before** R10 was measured, and its closing claim — that the choice does **not** change
the gate population — is **superseded by §7 and is wrong**. R10 removes up to 4 `reach` questions if rank is in.
The rank feature's identity as the public alias stands as recorded here; only the conclusion about the population is
withdrawn.

## 9. Slot-plan symbol alphabets, from the leaks lens (`lk1_answer_carriers_out.txt` Part F)

The answer spaces a head must cover, with the record counts in parentheses:

```
analogy          world_id        65 symbols  (70)
definition       kind_ref        64          (70)
definition       function_ref    64          (70)
context          setting_ref     64          (70)
correspondence   mapping_target  3 or 4      (54 / 280)
definition       whole           3 or 4      (15 / 55)
reach            reach           6 or 5      (79 / 28)
role_set         role            2           (216)
parts            node            2           (207)
context          participant     2           (267)
edge_account     edge            2           (1029)
correspondence   mode            2           (88)
```

The four 64/65-symbol slots and the wide `mapping_target` are where the output space, not the input, is hardest.

## 10. What is still outstanding

### 🔴 THE REMOVAL TABLE IS INCOMPLETE — `lk6_gate_population.py` CRASHED PART-WAY

`measurements/leaks_review/lk6_gate_population_out.txt` is a **truncated** run, not a finished population. It
completed REMOVAL 1 and REMOVAL 2 and then raised on REMOVAL 3:

```
REMOVAL 1 -- registered input-blind shortcut       removes  0 eligible: {}
REMOVAL 2 -- FP2 parts(declared_whole)             removes  3 eligible: {'parts': 3}
            reach flag rule                        removes  0
            edge flag rule                         removes  0
REMOVAL 3 -- DG3 node-order-dependent questions    ValueError: TYPED_SOURCE_WORLD_RECONSTRUCTION
```

The crash is in the reviewer's own relabelling harness: it rebuilds a relabelled public source and
`source.validate_public` rejects the reconstruction (`source.py:254`, `TYPED_SOURCE_WORLD_RECONSTRUCTION`). It is a
defect in the probe, **not** a property of the study.

**So the definitive removal list does not exist yet, and no population may be quoted as final.** What the truncated
run does establish, and they are consistent with the other tables:

- the registered input-blind shortcut removal takes **0** of the 45 eligible questions;
- the FP2 flag rule takes **3** (`parts`), the `reach` flag rule **0**, the `edge_account` flag rule **0**;
- the RELATIONAL tier is 29 (analogy 5, correspondence 5, edge_account 5, parts 5, reach 9) over five held worlds
  (5, 5, 7, 6, 6).

**Three classes of removal are still not reconciled**, and they were found by different lenses:
1. the **flag rules** (leak lens `lk2`, learnability LB2 — which says **4**, not 3);
2. the **one-hop adjacency read**, which the leak lens measured as solving `parts` **5/5** and `edge_account` **5/5**
   (`lk1_answer_carriers_out.txt` lines 58-66) — this is *not* a flag rule, and it is absent from REMOVAL 2;
3. the **rank and constant channels** on `reach` (R10 at 4/9, and DG3's 2/9).

Until those are reconciled into one list, the honest population is an interval, not a number.

- The leaks lens had not yet reported its shortcut-policy table (pointer-space policies), its permutation-vacuity
  list, its other pipeline-routes check, or its final removal list and minimum b.
- The learnability lens had not yet reported its per-kind expressivity table, the colour-refinement/1-WL limits, the
  recurrence-stability result, the optimiser adequacy analysis, or its predicted false negatives.
- Both must be folded in before the protocol is frozen.

## 11. Owner decision this creates

One consolidated question is owed to the owner, and it should be asked **once**, when both lenses have reported:
the relational tier the owner confirmed by name included two kinds whose answers the input hands over. Narrowing the
tier to the three kinds whose answers are genuinely not in the input makes a pass *harder* and the label *honest*,
but it also shrinks the population to about 17 questions with a floor of 7 improvements per seed. The owner should
confirm that trade knowingly rather than have it applied silently.
