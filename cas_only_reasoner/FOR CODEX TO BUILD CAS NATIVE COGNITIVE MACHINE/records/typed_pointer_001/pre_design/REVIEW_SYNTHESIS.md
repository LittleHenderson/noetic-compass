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

## 4. What is still outstanding

- The leaks lens had not yet reported its shortcut-policy table (pointer-space policies), its permutation-vacuity
  list, its other pipeline-routes check, or its final removal list and minimum b.
- The learnability lens had not yet reported its per-kind expressivity table, the colour-refinement/1-WL limits, the
  recurrence-stability result, the optimiser adequacy analysis, or its predicted false negatives.
- Both must be folded in before the protocol is frozen.

## 5. Owner decision this creates

One consolidated question is owed to the owner, and it should be asked **once**, when both lenses have reported:
the relational tier the owner confirmed by name included two kinds whose answers the input hands over. Narrowing the
tier to the three kinds whose answers are genuinely not in the input makes a pass *harder* and the label *honest*,
but it also shrinks the population to about 17 questions with a floor of 7 improvements per seed. The owner should
confirm that trade knowingly rather than have it applied silently.
