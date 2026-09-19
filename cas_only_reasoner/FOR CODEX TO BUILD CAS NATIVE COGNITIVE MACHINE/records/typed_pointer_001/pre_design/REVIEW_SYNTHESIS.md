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

## 6. The node rank feature is the public node alias — and that reopens a decision I had made

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

Note this does **not** change the gate population: the 2 eligible held `reach` questions that the order decides are
removed whether rank is in or out (`DG3`). The choice affects the training signal (with rank, those targets stop being
contradictory) and the engineering claims, not the bar.

## 7. Slot-plan symbol alphabets, from the leaks lens (`lk1_answer_carriers_out.txt` Part F)

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

## 8. What is still outstanding

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
