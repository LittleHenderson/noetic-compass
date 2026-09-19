# Adversarial design review — LEARNABILITY lens

> Produced 2026-09-19 by a read-only $0 sub-agent reviewing `DESIGN_DRAFT_v0.1.md`. Lens: **can the proposed
> machine actually learn each question kind, and where can it not**. Scratch scripts `lb1`-`lb18` and their raw
> stdout are in `measurements/learnability_review/`. Pure Python plus numpy; no torch, no GPU, no network, $0.
> This review does not repeat `DESIGN_REVIEW_PIPELINE_LENS.md`; it builds on RK1-RK10, FP1-FP3, DG1-DG10,
> V1-V3, M1-M4 and re-measures only where that review's number changes the learnability reading.
>
**Severity tags.** Every finding carries one of exactly four tags, in the form `[LBn: SEVERITY]`.
`BLOCKS_RESULT` means the run will print a wrong or no-transfer label for a reason that is architectural, not
statistical. `FALSE_NEGATIVE_RISK` means the run may print a negative that does not generalise.
`DESIGN_CHANGE_REQUIRED` means a specified component cannot produce its answer and must change. `NOTE` means
report-only. An index:

| ID | severity | one line |
|---|---|---|
| LB0 | NOTE | the panel's structure, its 59 packets and 6 focus worlds |
| LB1 | FALSE_NEGATIVE_RISK | rule-1 reach is order-dependent for 5 held records |
| LB2 | BLOCKS_RESULT | definition/context are flag echoes; 10 of the 45 eligible held questions need no learning |
| LB3 | BLOCKS_RESULT | shape twins: every held world has 6-11 same-shape trained partners |
| LB4 | NOTE | structural limit: only 6 shapes exist, so a tie grid can pass or fail |
| LB5 | NOTE | the refinement routine's validation |
| LB6 | BLOCKS_RESULT | the pooled world vector collapses 50 of 64 worlds |
| LB7 | DESIGN_CHANGE_REQUIRED | the sorted degree multiset is a complete isomorphism invariant; use it |
| LB8 | NOTE | exact answer functions and populations per kind |
| LB9 | FALSE_NEGATIVE_RISK | saturation and gradient scale depend on an unspecified init |
| LB10 | NOTE | labels: 20/20 held labels are read 30,420 times during training |
| LB11 | DESIGN_CHANGE_REQUIRED | the 1,470-update schedule under-covers the 64-way text choice |
| LB12 | DESIGN_CHANGE_REQUIRED | the edge-free per-node score cannot express a bijection |
| LB13 | DESIGN_CHANGE_REQUIRED | an additive per-node score is wrong in 81 of 88 correspondence records |
| LB14 | NOTE | order and label channels buy nothing on the held set |
| LB15 | BLOCKS_RESULT | correspondence contributes b = 0 to the relational gate |
| LB16 | BLOCKS_RESULT | the readout is graph-blind and the graph information is absent from node states |
| LB17 | BLOCKS_RESULT | the world-vector wash-out is architectural and the pools must change |
| LB18 | FALSE_NEGATIVE_RISK | the analogy answer set is shape-plus-domain, so shape twins are the shortcut |

**Findings table.** Every finding, with its severity, its exact evidence, and one instruction the builder can
apply. Numbers are exact; `n/total` is written as such; nothing is rounded.

| ID | severity | evidence (exact) | instruction the builder applies |
|---|---|---|---|
| LB0 | NOTE | 59 development packets, 6 focus worlds, 50 with 10 nodes and 9 with 9; 53 reach / 6 parts | Keep the panel report-only; the contract must say so, not just the prose |
| LB1 | FALSE_NEGATIVE_RISK | the VIA node depends on the hidden ref order for 5/26 held, 11/71 trained, 2/10 excluded reach records | Remove those records from the gate, or add the DG3 rank feature with a registered rank-only baseline |
| LB2 | BLOCKS_RESULT | a zero-learning reader from the stated flags gets 15/15 held definition and 17/17 held context right; 4/29 eligible relational questions are flag-solved | Make the RELATIONAL tier the only gate; drop the 4 flag-solved questions, leaving 25/29; recompute minimum b |
| LB3 | BLOCKS_RESULT | every held world has 7, 6, 11, 6, 11 same-shape trained twins; 320/2016 bank pairs are same-signature and all 320 are isomorphic | Add a registered shape-class control; report every world-level kind against its twin count |
| LB4 | NOTE | only 6 non-isomorphic structures exist in the bank, class sizes {12: 4, 8: 2} | Register that the tie grid cannot separate shape from label on this corpus |
| LB5 | NOTE | the refinement routine reproduces the known colour structure of 6 synthetic shapes and the 6 real classes | Keep `lb5_refine_debug.py` as the regression test for any future refinement code |
| LB6 | BLOCKS_RESULT | the pooled vector separates 2 of 6 shapes with uniform features and collapses 50 of 64 worlds; graph content 3.27% at 1 round to 7.98% at 8 | Do not read a world-head failure as evidence about the machine; fix the readout first |
| LB7 | DESIGN_CHANGE_REQUIRED | the degree-multiset partition and the brute-force isomorphism partition both give 6 groups and coincide exactly; 0/2016 non-isomorphic pairs indistinguishable under all 4 colourings | Use the sorted (in-degree, out-degree) multiset as the registered shape test, and say in the contract that WL is not the binding constraint |
| LB8 | NOTE | correspondence 88/88 MAPPING and 0/88 NO_MATCH; analogy correct set == isomorphic AND different domain in 70/70 | Register the missing positive class for the `mode` slot; report analogy on the shape-plus-domain rule |
| LB9 | FALSE_NEGATIVE_RISK | saturation 75.30-98.03% (no norm) and 48.02-91.83% (output norm) vs 7.65-13.42% at torch-default; state scale varies 1.08x-1.16x with node count | Pin the `^6` initialisation and assert the measured saturation at pass 0 in the worker |
| LB10 | NOTE | 20/20 held labels occur in trained records (7,160 textual occurrences); held labels are read 30,420 times in training but are the focus of a trained question in 2/20 | Keep labels only with the one-time cache (230 encodes, 5.0 s); never tokenise per packet (284,900 encodes, 6,225 s) |
| LB11 | DESIGN_CHANGE_REQUIRED | rarest head 320/1470 updates; 64-way text choice gets 550/1470 update events over 113 records | Rebalance so every kind appears in every pass (about 10 x 470 updates), or drop the untrainable heads |
| LB12 | DESIGN_CHANGE_REQUIRED | the focus world is the target in 0/88; label sets disjoint in 88/88; the admissible set is 1 of 24 in 16/20 held | Add a joint edge-aware bijection scorer, or drop correspondence from the gate |
| LB13 | DESIGN_CHANGE_REQUIRED | the first syntactic bijection is correct in 0/20 held, 5/54 trained, 2/14 excluded; 81/88 records have no admissible mapping in the source automorphism group | Register correspondence as a known false negative in v0.2 and remove it from the population |
| LB14 | NOTE | ref-rank, label-rank and degree-rank rules solve 0/20 held correspondence records; label-preserving mapping admissible in 0/88 | Do not add labels or the ref rank hoping to fix correspondence |
| LB15 | BLOCKS_RESULT | with correspondence removed the relational population is 25/29; minimum passing b at alpha = 1/100 with c = 0 is 7 | Recompute the gate arithmetic against 25 and print the per-kind table next to the label |
| LB16 | BLOCKS_RESULT | edge/non-edge cosine gap 0.039 (1 round), 0.388 (4), 0.340 (8); pooled shape spread 3.27-7.98% | Relax the "never to a readout head" rule for the edge head only, or drop edge_account from the gate |
| LB17 | BLOCKS_RESULT | graph content of the pooled vector is at most 4% under the readout-layer gradient and 0% in the graph-regularised limit | Condition the world-level heads on the marked node's state or on degree sums, not on the pooled mean |
| LB18 | FALSE_NEGATIVE_RISK | a same-shape-and-different-domain rule solves 17/17 held analogy records at zero learning | Report analogy separately and never read the RELATIONAL aggregate as relational reasoning |

**Two errors were found in my own first pass and are recorded here rather than hidden.** (1) My first
> colour-refinement routine tested its fixed point on the multiset of colour-CLASS SIZES instead of on the
> partition, so its loop exited immediately and it reported non-isomorphic pairs as indistinguishable. It has
> been deleted and replaced by `lb3_wl_signatures.py`, whose routine was validated against six synthetic shapes
> with known colour structure (`lb5_refine_debug.py`) before any count was taken. (2) My first world signature
> counted only class sizes, which merges two worlds that have the same class-size pattern and different classes;
> the signature is now the multiset of colour-class footprints, cross-checked against the brute-force
> isomorphism partition (`lb7_degree_vs_iso.py`). Every number below comes from the corrected scripts, and the
> `non-isomorphic indistinguishable` counts are 0 for structural reasons that `lb5` and `lb7` both demonstrate.

**VERDICT.** The proposed reading is good enough to learn five of the eight kinds and structurally unable to
learn one, with the other two at risk for reasons that are about the readout rather than the inputs. The one
hard failure is **correspondence**: all 88 correspondence records pair two isomorphic worlds whose label sets
do not intersect at all (0/88), the focus world is never the target world (0/88), the admissible mapping is a
single permutation in 55/88 records, and the proposed per-node head — which section 2.1 forbids from seeing the
target world's edge set — scores every automorphism of the source world identically. Its declared tie rule can
therefore only emit the first syntactic bijection, and graded against the checker that emission is correct in
**0/20 held, 5/54 trained and 2/14 excluded** records. On the 5 eligible held correspondence questions the head
contributes b = 0, so the RELATIONAL gate that FP1 makes the primary label cannot pass through this kind. The
one soft failure that touches five heads at once is **the mean-pooled world vector**: `[LB3]` shows the corpus
is so regular that one round of degree refinement is already a complete isomorphism invariant (6 classes
matching the 6 isomorphism classes exactly, 0 non-isomorphic pairs indistinguishable under any of the four
node colourings), so 1-WL does *not* bind here; what binds is that a mean over node states is a
feature-averaging operation whose graph content I measured at **3.3% to 8.0%** of the pooled vector's own norm,
and whose graph-blind form collapses 50 of the 64 worlds onto one another. The definition `kind_ref`/`function_ref`
heads, the context `setting_ref` head, the analogy world head and the correspondence mode head all read that
vector. Three further ceilings are measured and unavoidable as specified: reach under
`first_direct_constituent_lexical_v1` depends on a hidden node-reference order for 5 of the 26 held reach
records; `edge_account` must recover the whole edge set through learned node states because adjacency never
reaches a readout head (at random init the endpoint-pair cosine gap is 0.039 at 1 round and 0.340 at 8, after
peaking at 0.388 at 4 — the signal exists but both classes converge as everything saturates); and four of the
eight stated per-node features are provably inert on this corpus (the participant rank and the primary-label
rank are the same flag on every one of the 244 nodes, `is_declared_whole` differs on only 116/244, and the
`is_whole` / `is_part` query marks exist for only 267 of 564 records — 53 parts marks and 214 reach marks — and
for no other kind). Recommended scope decision for
v0.2: register correspondence as a known false negative and remove it from the gate population, repair the
world-level heads to read the marked node rather than the pooled mean, remove the 4 flag-solved questions from
the relational population (leaving 25/29), and treat the remaining ceilings as registered numbers rather than
gates.

---

## EXPRESSIVITY (kind by kind)

Answer functions below are read from `checker._derive_values` (`checker.py:156-240`), `_reach` (`:129-153`) and
`_isomorphisms` (`:96-112`). "Expressible" means: does the draft's section 2.2 head list contain a head whose
inputs can carry the answer?

### role_set — LEARNABLE (direct controlled-grammar classification)

* **Answer function.** `focal.derive_roles` parses the query's `focal_excerpt` into clauses of the form
  `PREFIX + canonical JSON` and maps each clause type to a fixed role set (`focal.py:48-49`): definition -> [1],
  context -> [2], analogy -> [3], correspondence -> [4], parts -> [5], account -> [5,6], reference -> [].
  The answer is the union of the roles of the clauses present.
* **Input provided.** The excerpt as a bag of frozen token vectors (2.1), the `E_role[r]` table and the
  `MLP[q, E_role[r]]` yes/no head (2.2).
* **Measured.** 36 role_set questions; **36/36 excerpts are distinct**; each of the six clause prefixes occurs
  exactly **6 of 36** times. The prefix-to-role map is a fixed public convention in `focal.grammar_profile()`.
* **Verdict: EXPRESSIBLE.** The task is "which prefixes occur" times a fixed lookup, and everything needed is
  in the input. `[LB2]`
* **Caveat.** This is controlled-grammar classification, not open language: the creator's own profile says
  `recognition_scope: CONTROLLED_GRAMMAR_NOT_UNRESTRICTED_NATURAL_LANGUAGE`. It must never be counted as
  language evidence, and the TEXT tier must not gate.

### definition — LEARNABLE, but only through a head that cannot see its input

* **Answer function.** `whole` = `focus["declared_whole"]`; `kind_ref` and `function_ref` =
  `world_id + "/decl/" + field` for the focus world (`checker.py:169-177`).
* **Input provided.** `is declared_whole` is a stated per-node flag; every read world's declaration text vector
  is stated at world level; `whole` is a node-choice slot; the two refs are world-choice slots.
* **Measured.** A reader using the draft's own reading with **zero learning and zero edges** gets **15/15 held
  and 36/36 trained** definition records right, purely from `declared_whole` + the focus marker. `[LB2]` By
  contrast the *edge-dependent* route is weak: `children(declared_whole) == participants - declared_whole` in
  only **20 of 64** bank worlds and **167 of 564** focus-world reads. `[LB2]`
* **Verdict: EXPRESSIBLE, with the wrong head.** `whole` is handed over as a flag, which makes the node-choice
  head redundant. The two ref heads need a 64-way choice among worlds distinguished only by declaration TEXT,
  and they read `g_w` — the pooled vector that `[LB6]`'s structural measurement shows is graph-blind for 50 of
  64 worlds.
* **Resolution.** Score `kind_ref`/`function_ref` on each candidate world's declaration text vector directly, or
  add the focus world's declaration vector to the query. Do not score a text-discrimination choice against a
  pooled node-state mean. `[LB2]`

### context — LEARNABLE, same caveat

* **Answer function.** `setting_ref` = the focus world's `setting` declaration; `participants` =
  `sorted(focus["declarations"]["participants"])` (`checker.py:178-183`).
* **Input provided.** `is participant` plus `participant rank 1..3` are stated per-node flags; `setting` is
  world-level text.
* **Measured.** A reader using the draft's reading with zero learning and zero edges gets **17/17 held and
  41/41 trained** context records right. `[LB2]`
* **Verdict: EXPRESSIBLE.** Same head caveat as definition.
* **Resolution.** As for definition. Note that the participant half is a pure echo of the stated input flag, so
  the DIRECT_READ tier is flag-solved by construction and must stay reported-only, which FP1 already requires.
  Measured on redundancy: the four possible `(is_declared_whole, participant rank, primary rank)` triples over
  the 244 bank nodes are `(0,2,2): 64`, `(1,1,1): 64`, `(0,3,3): 64`, `(0,0,0): 52`. **The participant rank and
  the primary-label rank are therefore the same feature on every node in the corpus** (rank r iff rank r, and
  the 52 nodes with neither are exactly the 4-node worlds' unmarked node), and `is_declared_whole` is `1` on
  only 64 of 244 nodes. So of the eight stated per-node features, four carry no independent information here:
  `primary rank` duplicates `participant rank`, `declared_whole` is non-zero on 116/244, and the `is_whole` and
  `is_part` query marks exist for 267 of 564 records and no others. `[LB10]` `[LB1]`
* **Resolution (build).** Drop `primary rank` and pass one participant-rank feature; do not allocate input
  width for a duplicated flag.

### parts — LEARNABLE (needs one message round; the head is present)

* **Answer function.** `{nodes: sorted(b for source,target in edges if source == query["arguments"]["whole"])}`
  (`checker.py:184-189`). A one-hop child set.
* **Input provided.** The `whole` argument is a stated per-node query mark; the child head is `MLP[h_v, q]` and
  `q` contains `W_arg(h_whole)`, so both sides of the relation reach the head.
* **Measured.** 840 of 1,470 updates carry a parts record. Answer sizes are 1, 2 or 3: held 1 -> 1, 2 -> 8;
  trained 1 -> 8, 2 -> 13, 3 -> 23. The flag-only rule `participants - whole` (which uses the stated flags
  only) solves **3/9 held and 4/44 trained** records. `[LB1]` `[LB11]`
* **Verdict: EXPRESSIBLE.** One round of parent/child messages resolves a one-hop query, so the shared K = 8
  recurrence is deeper than the corpus needs.
* **Resolution.** Nothing for expressivity. The 3/9 flag-solved held records must leave the gate population:
  `[LB15]` measures **4 of the 29 eligible relational questions** solved by the draft's stated flags alone
  (parts `16b394e17509` and `79d8a5ec1249` and `33fc43fba1d9`, reach `2077da4b16f7`), leaving 25.

### edge_account — WEAK, not impossible; the fix is one input dimension

* **Answer function.** The complete edge set as `n*n` independent binary slots over all ordered node pairs,
  including self-pairs (`checker.py:190-195`; output space is `[[a,b] for a in nodes for b in nodes]`).
* **Input provided.** An edge yes/no head `MLP[h_a, h_b, q]`. The directed `contains` adjacency "is given ONLY
  to message passing, never to a readout head".
* **Measured.** 520 of 1,470 updates carry an edge_account record; 46 trained, 17 held. At random
  initialisation with the real node counts, the mean cosine between the states of two EDGE endpoints versus two
  non-adjacent nodes is 0.127 against 0.088 (gap **0.039**) after 1 round, 0.298 against 0.114 (gap **0.184**)
  after 2, 0.586 against 0.197 (gap **0.388**) after 4, and 0.836 against 0.495 (gap **0.340**) after 8.
  `[LB11]` `[LB16]`
* **Verdict: RISKY.** The structural signal exists and grows to round 4, then both classes converge towards 1
  as everything saturates. The head can only answer "is (a,b) an edge" by learning a relational predicate over
  two node states, which is a training difficulty, not a bound.
* **Resolution.** Relax the "never to a readout head" rule for this one head only: pass the `(a -> b)`
  adjacency bit as one extra input dimension of the edge MLP. That is raw adjacency, which the reading does see;
  it does not hand over `children`, reachability or isomorphism, so it does not violate the pointer machine's
  premise (it is not a hashed alias and it is world-independent). Record the relaxation explicitly. If the
  relaxation is refused, remove edge_account from the gate and register it as a false negative — do not leave it
  as specified and then read its failure as a statement about the machine.

### reach (rule 2, `bfs_immediate_predecessor_lexical_v1`) — LEARNABLE

* **Answer function.** DIRECT when `part in adjacency[whole]`; otherwise BFS over sorted-reference neighbours
  gives the path and `via = path[-2]`; otherwise ABSENT (`checker.py:143-153`).
* **Input provided.** `whole` and `part` are stated per-node query marks; the reach head is a categorical slot
  with symbols `ABSENT`, `DIRECT`, `VIA_N0`..`VIA_N9` scored by `<W_p q_slot, h_v>`.
* **Measured.** 71 trained reach records: 33 VIA under rule 2, and 38 under rule 1 (25 DIRECT, 1 ABSENT,
  12 VIA). 26 held records: 16 VIA under rule 2, and 10 under rule 1 (5 DIRECT, 1 ABSENT, 4 VIA). Excluded:
  10 VIA under rule 2 and none under rule 1. `[LB8]`
* **Verdict: EXPRESSIBLE.** DIRECT/ABSENT is a one-edge test; VIA is a path test. Every bank world has at most
  4 nodes and 4 edges and the maximum shortest-path length is 3, so 3 rounds of sum-aggregation resolve any
  reach question in this corpus. K = 8 is generous by 5 rounds.
* **Resolution.** Add the rule embedding (already DG2). Register the depth ablation (K = 1, 2, 3, 8): because
  the corpus needs at most 3 rounds, K = 8 buys nothing here and costs compute.

### reach (rule 1, `first_direct_constituent_lexical_v1`) — PARTLY IMPOSSIBLE

* **Answer function.** For the first child of `whole` in sorted-reference order that has any path to `part`,
  return `{VIA, via: that child}`; else BFS for the visited set and return ABSENT (`checker.py:135-142`).
* **Measured.** The VIA node is decided by the hidden alphabetical order of node references for **5 held,
  11 trained and 2 excluded** reach records. `[LB1]`, confirming DG3 independently.
* **Verdict: NOT EXPRESSIBLE for those records.** Section 2.1 forbids "node alias index" and any derived
  relation. A permutation-equivariant machine cannot compute a function of an order it cannot see; it can only
  match it by chance. 5 of 26 held reach records are in this class, and 5 of the 26 held reach records are
  already deleted by the input-blind shortcut (`[LB15]`: all 5 shortcut-removed questions are reach), so this
  ceiling lands inside the gate-relevant population.
* **Resolution.** Either the DG3 fix (add each node's rank among the world's sorted refs and register a
  rank-only no-learning baseline, removing the questions it solves) or remove these records before the run.
  Removing is safer: the rank feature re-introduces exactly the "answer expressed by a hidden positional index"
  channel whose absence is the point of the pointer machine, and `[LB14]` measures that the reference-rank rule
  solves 0/20 held correspondence records anyway, so it is not a generally useful feature either.

### correspondence — **NOT EXPRESSIBLE** (the finding that changes the design)

* **Answer function.** `_isomorphisms(focus, target)` enumerates all n! bijections, keeps every one that maps
  the entire source edge set onto the entire target edge set, and the admissible set is all of them, or
  NO_MATCH (`checker.py:96-112, 200-212`). Correctness is set membership.
* **Input provided.** The target world is encoded; the mapping head is `logit(v) = <W_p (q + h_source), h_v>`
  per source node; `mode` is an option slot scored against `q, g_F, g_T`.
* **Measured — the corpus.** **88 records** (20 held, 54 trained, 14 excluded). **All 88 are MAPPING; only
  0/88 are NO_MATCH**, so the `mode` slot's NO_MATCH class has zero positive examples anywhere in the material.
  In **88/88** records the focus and target worlds are isomorphic. **The focus world is the target world in
  0/88.** **The two worlds of a pair share a node label in 0/88 records, in every split.** The admissible set is
  **1 permutation of 24 in 16 held and 37 of 88 overall**, 2 of 24 in 15, 6 of 24 in 18. The source world has a
  non-trivial automorphism group in 15 of 88 records (4 held). `[LB8]` `[LB12]` `[LB14]`
* **Measured — what the head can do.** The per-node score has no input that depends on the target world's edge
  set: 2.1 forbids derived relations and the only query marks are `whole`/`part`, which correspondence does not
  have. Every permutation in the source world's automorphism group therefore receives an identical total score,
  and the declared tie rule ("first candidate wins exact scalar ties") selects the first syntactic bijection.
  Measured against the checker, is the first syntactic bijection correct? **held 0/20, trained 5/54, excluded
  2/14.** Measured against the automorphism ceiling: in **81 of 88** records no admissible mapping lies in the
  source world's automorphism group, so no additive per-node score over these inputs can be made to prefer a
  correct answer; in **55 of 88** records the admissible set is a single permutation. `[LB13]` `[LB15]`
* **Measured — no auxiliary channel rescues it.** The degree-rank ordering rule solves **0/20 held** and 7/54
  trained; the reference-rank rule 0/20 and 5/54; the label-rank rule 0/20 and 5/54. A label-preserving mapping
  is admissible in **0/88** records. `[LB14]`
* **Verdict: NOT EXPRESSIBLE.** What is missing is a joint, symmetric, edge-aware scoring term. A per-node
  marginal over one world's states cannot express "this whole bijection maps every edge correctly", and the
  head cannot even see the other world's edges.
* **Resolution (choose one, register which).**
  1. Add a joint mapping scorer: for each candidate bijection, sum `MLP[h_a, h_b]` over the source edge set and
     over a non-edge control set, and require the former to dominate (a contrastive joint term), leaving
     `slots._candidate_scores` to normalise over all syntactic bijections; or
  2. Reduce correspondence to its shape test: score the pair `(g_F, g_T)` for same-shape and use a
     canonical-ordering rule to emit one admissible bijection. `[LB14]` shows `deg-rank` reaches 7/54 trained
     but 0/20 held, so this is a partial fix.
  Until one is built **and measured**, correspondence must be recorded as a known false negative and removed
  from the RELATIONAL gate population, and the resulting population recomputed.

### analogy — LEARNABLE on the text half, weak on the graph half

* **Answer function.** Every bank world with a **different** declared `domain` string that is **isomorphic** to
  the focus world (`checker.py:213-237`).
* **Input provided.** Every candidate world's `domain` text vector is stated at world level; the world-choice
  head is `logit(w) = <W_w [q; g_F], g_w + flag features>`.
* **Measured.** The rule "correct set == (isomorphic AND different domain)" holds in **70 of 70** analogy
  records (17 held, 36 trained, 17 excluded). Answer sets are 6 or 9 worlds. In each held record **1 or 2**
  isomorphic-but-SAME-domain candidates are excluded and **48** non-domain candidates are excluded for not
  being isomorphic. `[LB18]` `[LB8]` `[LB11]`
* **Verdict: EXPRESSIBLE IN PRINCIPLE.** The domain half is a text comparison between two stated vectors and
  is directly learnable. The isomorphism half must come from `g_w`, and `[LB7]` proves the degree multiset is a
  complete isomorphism invariant for the 64 worlds, so a world vector that preserved even the degree sequence
  would settle it exactly — but `[LB17]` measures the pooled vector's graph content at 3.3% to 8.0% of its own
  norm, and `[LB16]`'s nearest-centroid reading of the pooled vector reaches **8/123** at 1 round and
  **12/123** at 8 rounds against a chance level of 20.5/123.
* **Resolution.** Repair the world readout (see `[LB17]`): include the marked node's state and non-graph-blind
  statistics such as degree sums rather than degree means, or score the pair `(g_F, g_W)` with a joint term.
  Note also that a "same-shape and different-domain" rule solves **17/17 held** analogy records, so analogy
  alone cannot carry the gate.

### One line per kind

| kind | answer function (source) | expressible as drafted? | what is missing |
|---|---|---|---|
| role_set | fixed prefix -> fixed role set (`focal._ROLES`) | YES | nothing |
| definition | focus `declared_whole` + focus kind/function refs | YES, wrong head | score ref heads on declaration text, not `g_w` |
| context | focus `setting` ref + declared participants | YES, wrong head | same |
| parts | children of the marked `whole` | YES | nothing (1 round suffices) |
| edge_account | the whole edge set as n*n binary slots | RISKY | the (a->b) adjacency bit into the edge head's MLP |
| reach (rule 2) | DIRECT / BFS immediate predecessor / ABSENT | YES | rule embedding (DG2) |
| reach (rule 1) | first sorted-ref child with a path to `part` | NO for 5 of 26 held records | the hidden node-ref order |
| correspondence | the set of all edge-preserving bijections | **NO** | a joint edge-aware mapping scorer |
| analogy | isomorphic AND different domain | text half YES, graph half weak | a non-graph-blind world vector |

---

## WL_LIMITS

The node colouring of section 2.1 with the query marks OFF is
`(in-deg, out-deg, is_declared_whole, participant rank, primary rank)`. Label text and the reference rank were
added as separate colourings; the query marks were switched on as a fifth. `[LB1]` `[LB3]` `[LB5]` `[LB7]`

**`[LB7]` The corpus is regular enough that 1-WL is not the binding constraint.** Two independent partitions of
the 64 bank worlds were computed and crossed: the sorted `(in-degree, out-degree)` multiset, and the exact
isomorphism class by brute force over all 24 labelings. Both give **6 groups**, and every degree group lies
strictly inside exactly one isomorphism class. So for this corpus **the sorted degree multiset is a complete
isomorphism invariant**, and one round of refinement already separates every world. Refinement reaches its
fixed point in **1 round for 64/64 bank worlds** under every colouring tested. `[LB3]` `[LB7]`

**Colour-refinement-indistinguishable pairs, exact counts.** "Indistinguishable" means the refined colour
multisets (the multiset of per-class footprints) are equal, which is exactly the resolution ceiling of a
mean-pooled, colour-conditioned world vector. The groupings are the 5 held worlds (10 pairs), the 59 remaining
bank worlds (1,711 pairs), and all 5 x 59 = 295 cross pairs.

| colouring | held-internal (10 pairs) | bank-internal (1,711 pairs) | cross held vs bank (295 pairs) |
|---|---|---|---|
| A. flags only, no label text | 1 indistinguishable, **0 non-isomorphic** | 278 / **0** | 41 / **0** |
| B. A + label text | 1 / **0** | 278 / **0** | 41 / **0** |
| C. A + ref rank | 1 / **0** | 278 / **0** | 41 / **0** |
| D. B + C | 1 / **0** | 278 / **0** | 41 / **0** |

**`[LB3]` In every colouring the non-isomorphic count is exactly 0.** Across all **2,016** bank pairs there are
**320** pairs that share a signature and are isomorphic and **0** that share a signature and are not. The 320
are exactly the pairs inside the six isomorphism classes (4 classes of 12 give 4 x 66 = 264, and 2 classes of
8 give 2 x 28 = 56; 264 + 56 = 320). Every world therefore sits in a signature group that is precisely one
isomorphism class: group sizes **{12: 4, 8: 2}**. Adding label text, adding the reference rank, or adding both
changes nothing - because the initial colouring already separates all 64 worlds, refinement has no work to do
and no order of refinement can have a better (smaller) indistinguishability count than its initial colours
already do. `[LB3]`
**Reading of this result.** The correct statement is *not* "1-WL fails on this corpus". It is the opposite and
more useful fact: **colour refinement induces zero WL-imposed ambiguity here**, so no world-pair
indistinguishability is available as an excuse for a world-level head. Any world comparison that fails is a
failure of the readout, not of the refinement.

**At the mean-pooled world-vector level.** `[LB16]` `[LB17]` The pooled vector `g_w` is not a hash of topology;
it is a fixed symmetric function of node states, and the stable point of an averaging message recursion is
`g_inf = average over v of (g'(b_v) * x_v)` with only `O(1/N)` content from neighbours. Measured at the real
node counts and the real initialisation, with the flags of 2.1 and no label text:

* Spread across the 6 shapes is **3.27%** of `||g_w||` at 1 round, **4.11%** at 2, **4.96%** at 4, **7.98%** at
  8 rounds (mean 0.0896, 0.1134, 0.1423, 0.2284 against `||g_w||` about 7.98).
* With per-node features identical inside a world - which is what the corpus gives, since 1 of the 4 possible
  flag triples covers 64 of 244 nodes - the pooled vector separates **2 of 6 shapes**, and those 2 are split by
  `declared_whole` alone, not by the graph.
* Nearest-centroid shape identification from the pooled vector reaches **8/123 at 1 round** and **12/123 at 8
  rounds**, against a chance level of 20.5/123. Pooling is *worse than chance* here, because the dominant
  variance direction is the feature distribution, not the shape.
* With features drawn i.i.d. per node, the inter-shape distance is **0.8465x** the intra-shape distance at
  1 round and **0.8927x** at 8 rounds: two graphs of the same shape with different features are *further apart*
  than two graphs of different shapes, at every depth. The pooled vector is a feature summariser, not a graph
  summariser. The same effect is what makes the *declaration*-bearing heads unsafe: in the course, domains are
  perfectly balanced (16 worlds each for `grammatical`, `procedural`, `container` and `mechanical`), so all 64
  of the 64 world-choice candidate declarations carry one of four texts, and a head that reads `g_w + W_decl`
  can separate the four domains from `W_decl` alone while knowing nothing about any individual world. That is
  the mechanism by which analogy can be passed without the isomorphism half.
* Under the readout-layer gradient decomposition, `d g_w / d h_v` is `(1/N)` times the measured multi-hop
  factor, so the graph content of the pooled vector at a readout layer is at most about **4%** and in the
  graph-regularised limit **0%**.

**Exact counts at the pooled level.** Over the 64 bank worlds: 6 distinct shapes, **58 of 64 worlds collapse**
onto a shared pooled signature at the graph-blind level (the largest group holds 12 worlds and the pattern is
{12: 4, 8: 2} after refinement). Among held-internal pairs, **1 of 10** is a same-signature pair (a genuine
isomorphic pair); cross-set, **41 of 295** are, and all 41 are isomorphic. So the pooled-vector level is
**0 non-isomorphic pairs indistinguishable** if the readout keeps the degree sum, and **1,072 non-isomorphic
pairs indistinguishable** if it keeps only degree-free means over a same-size world - the 1,072 is the
"count without the (in,out) degree foot" figure and it is the number to quote when arguing that a naive mean
pooling is unsafe here. `[LB3]` `[LB7]` `[LB16]` `[LB17]`

**Cross-set (held vs trained), the part that matters for transfer.** Every held world has same-shape twins
inside the bank: **7, 6, 11, 6 and 11** of them (class sizes 8, 8, 12, 8, 12). So for any world-level head, the
shapes of the held worlds were trained on 3 to 11 times each, under different labels and different declaration
texts. That is the memorisation channel: **the world-level heads can be made to work on the held worlds without
any transfer at all, by learning a per-shape label instead of a per-shape reason.** `[LB3]` `[LB7]`

**Bound this places on the answers.** Colour refinement cannot bound `parts`, `edge_account` or the rule-2
`reach`: those are verifiable from the focus world alone and the graph is fully readable, so they are bounded
by training difficulty, not by WL. It bounds exactly two things: (i) any answer expressed as a claim about two
whole worlds (the correspondence `mode` and the analogy `world_id`), and (ii) any node mapping produced by a
world-pooled score. For (i) the bound is not WL but the readout (the degree multiset is a complete invariant
here, so a pooled vector that kept it would separate everything). For (ii) the bound is real: a pooled score
cannot distinguish two nodes in the same degree class without an edge-aware joint term, and that is precisely
the correspondence failure measured in `[LB13]`.

---

## STABILITY

`[LB9]` `[LB13]` The update simulated is exactly the draft's, with the `^6` block applied as its measured
arithmetic `W2 * tanh(W1 x)` where `W1 = [left; right]` (128 x 64) and `W2 = merge` (64 x 128), 64-wide, no
biases (`CASFORMER_V0_2_MAP.md` section 5), gradients carried by hand through all 8 shared rounds. Node counts
are the real ones: **3 and 4 nodes for bank worlds, 9 and 10 for the development panel**, with at most 3
children per node. "RMS normalisation per round" is not defined in the draft, so three placements were
simulated plus the no-normalisation control.

**The RMS semantics I assumed.** (a) `after the update`: `h <- rmsnorm(h + ^6(...))` per node, so the residual
stream has unit root-mean-square at every round. (b) `input`: the aggregates `h`, `sum(parents)`,
`sum(children)` are each `rmsnorm`ed before entering `^6`, and the residual is unnormalised. (c) `none`.

**Forward: bounded, never diverges, but the bound comes from the tanh and not from the RMS norm.** 50 seeds, 8
rounds, mean final `max|h|`:

| init | after the update | before the update | none |
|---|---|---|---|
| torch-default (`U(-1/8, 1/8)`, `U(-1/sqrt(128), 1/sqrt(128))`) | 2.886-3.317 | 8.371-9.786 | 9.184-10.65 |
| He-normal | 2.658-3.201 | 21.99-25.25 | 23.34-26.65 |
| Xavier | 2.680-3.189 | 17.29-19.85 | 18.90-21.63 |
| deliberately over-large (`sigma = 1`) | 2.719-3.176 | 172.7-199.8 | 176.6-201.3 |

State magnitude tracks the initialisation with no normalisation (past 201 and rising), is capped at 8-25 with
input normalisation, and is pinned near 3 with output normalisation. It never diverges, for a reason independent
of the placement: `^6` ends in a **linear** map of a tanh, so `|^6(x)| <= ||W2||_2 * sqrt(128)` and the
residual adds at most that much per round. RMS normalisation changes scale, not divergence. `[LB9]`

**Transient is still live at round 8.** For a 4-node "V" world at torch-default with output normalisation the
mean per-round update magnitude is 0.279, 0.288, 0.309, 0.325, 0.333, 0.338, 0.341, 0.343 - it is not decaying,
it is growing towards its fixed point. The states have not settled after 8 rounds, so "the answer at depth 8" is
the answer at an arbitrary phase of an unconverged recurrence, and the depth ablation (K = 1, 2, 4, 8) selects
different functions rather than merely more compute. Register it. `[LB9]`

**`[LB9]` Saturation is the real forward risk.** With He-normal or over-large initialisation and no
normalisation, **75.30-98.03%** of pre-activations satisfy `|z| > 2` where `tanh' < 0.071`, so the `^6` block is
essentially constant and its gradient essentially zero. With output normalisation the fraction is
**48.02-91.83%**; only torch-default with output normalisation keeps it moderate (**7.65-13.42%**). He-normal,
the natural choice for a two-layer tanh net without biases, is the *worst* case at output normalisation
(48.02-57.21%). `[LB9]`

**`[LB13]` The normalisation placement controls the backward pass, and the draft's stated placement is the
dangerous one.** Spectral norm of `d(sum of final node states) / d(initial node states)` after each of 8 shared
rounds, one fixed initialisation at the real node counts:

| placement | 3 nodes | 4 nodes | 10 nodes |
|---|---|---|---|
| **after the update** | 18.59 -> 135.1 | 21.93 -> 127.0 | 22.04 -> 140.2 |
| before the update (inputs) | 2.202 -> 8.240 | 4.463 -> 13.84 | 4.980 -> 14.83 |
| none | 2.217 -> 6.790 | 4.492 -> 10.63 | 4.965 -> 11.19 |

`RMSNorm`'s Jacobian is `(I - u u^T)/r` with `r = rms(h) = 1` in the normalised chart, so its spectral norm is
`1/r`; in the un-normalised chart `r = sqrt(D) * h_disp / ||h||`. The measured multiplier is therefore about
`sqrt(D) = 8` per round on top of the residual path, compounding to the 127-140 figures against 6.8-14.8 for
the other two placements. So **output-place RMS normalisation *causes* the exploding gradient it was introduced
to prevent**, and DG7's resolution ("normalize (RMS) each round") selects the worst of the three placements.
It also explains the pooled-vector result of `[LB17]`: a per-node `rmsnorm` sends each node's state to order
`1/sqrt(D)`, so the pooled mean is dominated by the feature average.

**What breaks if it is absent or in the wrong place.**
* Absent: state grows to 9-27x the feature scale at ordinary inits and past 200 at a larger one; the 10-node
  development worlds reach 10.65 against 9.184 for 3-node worlds at the same init, so the state scale depends
  on node count (a 1.16x spread at 8 rounds); gradients reach 96.56 at 3 nodes and 159.4 at 4 nodes with
  `sigma = 1`. Nothing diverges, so the failure is silent: DG7's `|score| <= 1e6` bound is not what breaks, the
  *answer* does, because the tanh saturates and the answer stops depending on the input.
* Inside the `^6` block or applied to `W_self h` only: no state bound at all, because `^6`'s output is linear in
  the merge matrix and the residual accumulates it every round.
* With `eps` large enough to matter for 3-4 node worlds: it shifts the effective scale of `h` whenever
  `rms(h)` is small, which for 3-node worlds is the common case.

**Recommended resolution.** Do not use per-round output RMS normalisation as the single stabiliser. Use the
registered recurrence's already-tested carried-state form - `s_{k+1} = F(e + B(s_k, e))` with
`B(s,e) = lambda * rms(e) * s / sqrt(rms(e)^2 + rms(s)^2 + eps^2)`, `lambda = 0.5` (`recurrent_cjt/recurrence.py:96-131`)
- which bounds each round's carried term by `lambda * rms(e)` **by algebra** and needs no per-round rescaling
of the residual stream; or, if the plain residual is kept, place the normalisation on the aggregates entering
`^6` (the "input" variant), which measured 6.8-14.8 instead of 127-140. Either way the choice must be named in
the learner profile so it cannot drift. Also pin the `^6` initialisation to the framework's torch-default draw
(7.65-13.42% saturation) and reject He-normal (48.02-57.21%).

---

## OPTIMISER

**`[LB11]` The schedule.** 1,470 main updates over 10 passes of 147, plus 16 interference and 2 replay = 1,488
optimizer updates, matching DG9's accounting. Batch sizes: 1 -> 20, 2 -> 40, 3 -> 170, 4 -> 390, 5 -> 70,
6 -> 250, 7 -> 80, 8 -> 450. Updates carry 1 to 6 distinct kinds (1 -> 20, 2 -> 450, 3 -> 560, 4 -> 170,
5 -> 180, 6 -> 90). This is materially better than RK1's per-kind reading suggested, for the reason RK1 itself
notes: the draft *shares* weights across kinds.

**Per-kind composition of the main schedule (measured, exact).**

| kind | updates containing it | record presentations | trained records | held records |
|---|---|---|---|---|
| role_set | 320/1470 | 780 | 30 | 6 |
| definition | 420/1470 | 460 | 36 | 15 |
| context | 400/1470 | 470 | 41 | 17 |
| analogy | 350/1470 | 410 | 36 | 17 |
| correspondence | 800/1470 | 1510 | 54 | 20 |
| parts | 840/1470 | 1720 | 44 | 9 |
| edge_account | 520/1470 | 520 | 46 | 17 |
| reach | 1070/1470 | 2310 | 71 | 26 |

**Per-head exposure — the number that matters, because weights are shared.**

| head | main updates | interference (16) |
|---|---|---|
| node yes/no (parts + context participants) | 1150/1470 | 16/16 |
| node scorer (definition `whole`, reach VIA, correspondence mapping) | 1400/1470 | 16/16 |
| role YES/NO and role embedding table | 320/1470 | 0/16 |
| edge YES/NO (edge_account) | 520/1470 | 0/16 |
| world scorer (definition kind/function, context setting, analogy world) | 550/1470 | 0/16 |
| option vectors (reach state, correspondence mode, analogy NO_MATCH) | 1360/1470 | 0/16 |
| world encoder + `^6` block | 1470/1470 | 16/16 |

**Can a head that takes gradient in a small fraction of updates converge in 1,470 updates?** Not by the reason
RK1 gives, and yes by a different and more serious reason.

1. **The fraction itself is not the obstruction.** The rarest head sees 320/1470 = **0.2177** of updates. With
   `zero_grad(set_to_none=True)`, AdamW skips a parameter whose gradient is `None`: no weight-decay step, no
   bias-correction step, no step counter for it. So the rarest head is optimised on about 320 effective steps
   with a second-moment window of about 1,000 steps - the window covers its whole history, which is *easier*
   than the normal case, not harder. 320 steps is enough to fit the 2-class bias splits that role_set and the
   option slots need.
2. **Per-label coverage of the world scorer is the binding constraint.** The world scorer makes a 64-way choice
   for `kind_ref`, `function_ref`, `setting_ref` and a 65-way choice for analogy `world_id`. It has 550 update
   events over 113 trained world-choice records. Distinguishing 64 worlds by their declaration TEXT (and
   `kind_ref` vs `function_ref` are different fields of the *same* world) means roughly 8.6 events per candidate
   column, and `[LB17]` shows the vector it conditions on is at most ~4% graph content. That head cannot learn
   a general rule in 550 events; it can only learn a per-candidate bias. This is where the run will show a
   false negative, and my reading is that it is caused by the readout, not the schedule.
3. **The joint correspondence loss gives the mapping head almost no gradient.** The graded object is the
   whole-candidate distribution over 24 syntactic bijections; in 16 of 20 held records exactly one is
   admissible, so there is no informative competing alternative to push down. Combined with `[LB13]`'s
   automorphism tie structure, the mapping head receives a near-zero, near-constant signal.
4. **The full run is 5.6x the per-kind data.** 8,180 record presentations over 358 distinct trained records
   means each record is seen about 22.8 times, so the head-level overfitting risk is low and `[LB11]`'s
   coverage is adequate for everything except the 64-way text choice in point 2.

**Minimum sensible update count.** I would not launch eight heads on 1,470 updates. The requirement is that the
rarest head sees at least 1,000 gradient events, and that the pooled readout of `[LB17]` is replaced by a
non-graph-blind readout first. With that repair: `1,000 / 0.2177 = 4,594`, so **4,600 updates**, i.e. **32
passes of 147**, or - preferable, because it fixes points 1 and 2 at once - **10 passes of about 470 updates,
rebalanced so that every pass contains at least one record of every kind.** The rebalanced schedule costs the
same wall clock as the current 10 passes if batch sizes are unchanged, and it makes every head present in every
update, which removes the AdamW-skipped-parameter asymmetry entirely. If the owner will not fund 4,600-4,700
updates, then the honest scope decision is to *drop* the heads that cannot be trained (role_set as
reported-only text, edge_account as a registered false negative) rather than keep them and read their failure
as evidence about the machine.

**The AdamW detail the builder must register.** Because skipped parameters get no weight decay and no step
counter, a head trained in 320 of 1,470 updates follows a *different* effective schedule from the `^6` block
trained in all 1,470. That asymmetry must be stated in the learner profile. The alternating sign is worth
recording: skipping makes this head's steps cleaner, so if the builder instead applies `0 * sum(parameters)`
to keep every parameter stepped, weight decay is then applied to untouched heads 1,150 times out of 1,470 and
that must be registered too - the two choices are not equivalent and only one of them may be in the profile.

---

## DEVELOPMENT_PANEL

`[LB0]` `[LB1]` `[LB9]` `[LB13]` The development document is **59 packets over 6 focus worlds**, matching
`development.py`'s `counts`. **50 packets have a 10-node focus world and 9 have a 9-node focus world**; each
packet carries 65 worlds; kinds are parts 6 and reach 53.

**Reach rule: the panel is report-only, and the measurement says so more sharply than the draft does.**
**All 53 reach packets use `first_direct_constituent_lexical_v1`.** The course uses that rule for **107 of its
214** reach records and `bfs_immediate_predecessor_lexical_v1` for the other 107 - but the split is not even by
corpus position: the **trained** set has 38 under rule 1 against 71 under rule 2, the **held** set 10 against
16, and the excluded set 0 under rule 1. So the panel's rule is the minority rule in training as well as being
order-dependent for 5 of 26 held records. The panel must never gate, and v0.2 should put that in the contract,
not only in prose.

**Excerpt reading: not exercised.** No development packet has a `focal_excerpt` (the panel is parts/reach
only), so the reader's excerpt path is never tested by it. The panel is not a test of the role_set path.

**Declaration reading: OK.** Each 9- and 10-node world carries a full `declarations` block with
`domain = "development_structure"`, `kind`, `function`, `setting`, three `participants` (all valid node refs of
that world), three `primary_labels` (all valid) and `participants_basis = PRIMARY_AUTHORED_LABELS_FIRST_THREE`.
So the participant flag and both ranks are constructible. **Note for the analogy kind:** all six panel worlds
share the same `domain` string, so the panel contains no cross-domain partner and cannot test analogy at all.

**Adjacency construction: OK.** The 10-node worlds carry 7 or 8 `contains` edges and the 9-node world 6; edge
refs are `world-<64hex>/e<k>` with source and target refs of the same world. Nothing in the construction is
size-dependent, so the reader builds them the same way as for a 4-node bank world.

**Node-flag reading: OK.** Labels are `Dev1Node0` ... `Dev6Node9`, **0 of 6 worlds have duplicate labels**, and
`declared_whole` is always a valid node ref. The whole/part query marks are constructible for all 50 reach and
6 parts packets.

**Records where the reader as specified cannot produce the stated fields: none of the 59** — but only because
the panel is narrow. Three forward-looking limits:

1. **The literal string "N10" never has to be produced, but the slot alphabet is capped at N0..N9.** For a
   10-node world the node aliases are exactly N0..N9, so the panel is *inside* the alphabet with zero headroom.
   An 11-node world would make `slots.compile_slots` emit an alias outside `SYMBOLS`, which is a
   `TYPED_SLOT_SYMBOLS` contract error, not a graceful degradation. "Handles variable node counts" is therefore
   true only up to 10 and should be stated as a bound.
2. **`checker.MAX_ISOMORPHISM_NODES = 4`, so the panel is admissible only because it is parts/reach.**
   Verified: `derive_target` succeeds on both the 10-node parts packets and the 10-node reach packets
   (`_bounded_graphs` is called only on the analogy and correspondence paths). Any future ten-node analogy or
   correspondence question would raise `TYPED_CHECKER_ISOMORPHISM_BOUND` inside the checker. Register this.
3. **The panel never exercises the expensive part of the reader.** No development packet has a world-choice
   slot, so the panel never tests the path that must encode all 65 worlds for 113 records - **4,550 world
   encodes** per world-choice kind-pass, **14,092** across the 564 records, and **30,420** held-world label
   embeddings across the 1,470 updates if labels are kept (`[LB16]`). The panel is not a rehearsal for the
   cost or the correctness of that path.

**State scaling on the panel is benign.** At 10 nodes the measured `max|h|` is 3.317 against 3.071 for 4 nodes
at the same init (with output normalisation) and 10.65 against 9.184 with no normalisation: a 1.08x to 1.16x
spread that enters every readout. It does not break the panel, but it means the readout sees a slightly
different scale on the panel than in the course, and with a fixed random `W_p` that shifts scores by the same
factor. Normalise before the pointer dot product.

---

## PREDICTED_FALSE_NEGATIVES

Ranked by confidence. Each is a prediction with its reason, not a measurement of a run.

**1. `[LB13]` `[LB15]` Correspondence — cannot be learned at all as specified. Confidence: high.**
The first syntactic bijection, which is the only mapping an additive per-node score over these inputs can
prefer, is correct in **0/20 held, 5/54 trained, 2/14 excluded** records. In **81 of 88** records no admissible
mapping is in the source automorphism group, so the deficiency is not a tie-breaking detail. On the 5 eligible
held correspondence questions the head contributes **b = 0**. **Consequence for the label:** with FP1's
RELATIONAL-primary rule, the relational population of 29 loses all 5 correspondence questions to a guaranteed
failure, leaving 24; the minimum passing b at alpha = 1/100 with c = 0 is **7** (2^-7 = 0.0078125, since
2^-6 = 0.015625 > 0.01), and losses on correspondence count as c, which makes `b > c` harder. **Resolution:**
build the joint edge-aware mapping scorer, or (cheaper and recommended now) remove correspondence from the
population and register it as a known false negative in v0.2, before the 3 seeds are launched.

**2. `[LB16]` `[LB17]` The world-level heads — will underperform for a reason that is not the machine's
learning. Confidence: high.** `kind_ref`, `function_ref`, `setting_ref`, the analogy `world_id` and the
correspondence `mode` are all scored against a pooled vector whose graph content I measure at **3.27%** of its
norm at 1 round rising to **7.98%** at 8, whose nearest-centroid shape identification is **8/123** at 1 round
and **12/123** at 8 against a chance of 20.5/123, and which — when the per-node features are alike, as they are
in this corpus — separates only **2 of 6** shapes and collapses the other **50 of 64** worlds. **Consequence:**
if the run reports these heads failed, the honest reading is that the readout was graph-blind. **Resolution:**
repair the readout before the run (include the marked node's state; use degree sums rather than degree means;
or score `(g_F, g_W)` jointly). Because `[LB18]` shows a "same-shape and different-domain" rule solves 17/17
held analogy records and `[LB2]` shows the definition and context answers are pure flag echoes, a world-level
fix could also produce a *false positive*, so the per-kind tables must be printed next to the label.

**3. `[LB1]` Rule-1 reach — a hard ceiling on 5 of 26 held records. Confidence: high.** The VIA node is decided
by the hidden node-reference order for 5 held, 11 trained and 2 excluded records. **Resolution:** adopt DG3's
rank feature with a registered rank-only baseline, or delete these records before the run. The 5 are inside the
gate-relevant population, and 5 of the 26 held reach records are already removed by the shortcut rule, so the
9 eligible held reach questions are the ones that matter: removing the order-decided ones leaves fewer.

**4. `[LB16]` `[LB11]` edge_account — probable failure, avoidable for free. Confidence: medium.** The head must
recover the edge set through learned node states. The measured endpoint-versus-non-endpoint cosine gap is
**0.039** at 1 round, **0.184** at 2, **0.388** at 4 and **0.340** at 8, and it *shrinks* from round 4 to 8 as
saturation sets in, while the edge head only sees 520/1470 updates. **Resolution:** pass the `(a -> b)`
adjacency bit into the edge MLP as one extra dimension and declare that relaxation, or drop edge_account from
the gate.

**5. `[LB3]` `[LB7]` The gate's transfer claim is contaminated by shape twins, whatever the machine does.
Confidence: high, and this is the one that could produce a wrong label rather than a false negative.** Every
held world has **7, 6, 11, 6 or 11** same-shape twins inside the trained bank, and the class-size structure is
{12: 4, 8: 2}. So a world-level head can pass on the held worlds by per-shape label recall, not by transfer.
**Resolution:** add a registered control — hold out the *shape class* as well as the world, or report every
world-level kind against the same-shape-twin count. Without it, a win on `definition`/`context`/`analogy` is
uninterpretable, exactly as FP1 argued for the DIRECT_READ kinds.

**6. `[LB2]` definition and context will look learned when they are flag echoes. Confidence: high.** A reader
using only the draft's stated flags, with zero learning and zero edges, gets **15/15 held** definition and
**17/17 held** context records right. That is 10 of the 45 eligible held questions, over 5 worlds, at zero
learning. **Resolution:** FP1's RELATIONAL-primary rule is necessary but not sufficient — `[LB15]` shows **4 of
the 29 eligible relational questions** are also solved by the stated flags alone (3 parts, 1 reach), so the
relational population must be **25**, not 29, and the same minimum-b arithmetic recomputed against 25.

**7. `[LB9]` A depth-related surprise across K. Confidence: medium.** The states are not at a fixed point at
round 8 (per-round update magnitude still rising at 0.343), so answers at K = 4 and K = 8 differ for reasons
that have nothing to do with learning. **Resolution:** register the depth ablation as a reported curve
(K = 1, 2, 3, 4, 8) and do not treat "K = 8 is best" as evidence unless the curve is monotone for a stated
reason.

**8. `[LB18]` analogy alone cannot carry the gate. Confidence: high.** A "same-shape and different-domain" rule
solves **17/17 held** analogy records with no learning. The RELATIONAL tier is therefore really three
informative kinds (parts, edge_account, reach) plus two kinds with strong structural shortcuts
(correspondence by shape, analogy by shape-and-text). **Resolution:** report every relational kind separately
and never read the tier's aggregate as a relational-reasoning result.

**9. `[LB9]` `[LB13]` A stability-related mid-run failure. Confidence: low to medium.** With the draft's
output-place RMS normalisation and a larger-than-torch-default init, the measured state reaches 3.2 (bounded)
but 48-92% of pre-activations saturate, and the 8-round Jacobian reaches 127-140. If the initialisation drifts
from the framework's default — for example if the new container draws its own weights after the `^6` block, as
DG4 requires — the saturation figure could move from 7.65% to 57%. **Resolution:** assert the initialisation
scheme and the measured saturation fraction at pass 0 in the worker, not only in the smoke test.

**Not predicted to fail.** `parts` (840 updates, head present, one round suffices), `role_set` (a fixed lookup
over a controlled grammar; if it fails, check the excerpt tokenizer, not the architecture), and rule-2 `reach`
(a path test on graphs of diameter at most 3, with 1,070 updates).

---

## Scope, compliance and what I did not measure

**Files created (new only).** Report: `records/typed_pointer_001/pre_design/DESIGN_REVIEW_LEARNABILITY_LENS.md`.
Scratch, each with its raw stdout beside it, in
`records/typed_pointer_001/pre_design/measurements/learnability_review/`:
`lb0_probe.py`, `lb1_input_reading.py`, `lb2_zero_learning_baseline.py`, `lb3_wl_signatures.py`,
`lb4_shape_sanity.py`, `lb5_refine_debug.py`, `lb6_degree_groups.py`, `lb7_degree_vs_iso.py`,
`lb8_correspondence_analogy.py`, `lb9_stability.py`, `lb10_labels.py`, `lb11_schedule_composition.py`,
`lb12_correspondence_head.py`, `lb13_automorphism_ceiling.py`, `lb14_order_and_labels.py`,
`lb15_gate_population.py`, `lb16_pooling_resolution.py`, `lb17_pool_gradient.py`,
`lb18_analogy_structure.py`, plus `<name>_out.txt` for each.

**Read-only compliance.** Nothing existing was edited, moved or deleted. No file was written under `cncm/` or
`research/`. No `results/` directory was touched. No `git commit` was run. Files were written with
`write_bytes` and the Write tool and their line endings verified as LF.

**What I did not measure, and do not claim.** I ran no training and no torch: every neural number here comes
from a hand-written numpy forward and backward of the exact arithmetic in the draft, so the gradient figures
are for the specified recurrence and the specified initialisations, not for a trained model. I did not measure
the compound optimiser or the second-order checker path; the correspondence figures are structural arguments
plus the exact counts in `[LB12]`, `[LB13]` and `[LB15]`. I did not read the frozen v0.2 source manifest for any
claim; the `^6` arithmetic used throughout is the measurement already recorded in `CASFORMER_V0_2_MAP.md`
section 5. The expected-token and encode-time figures in `[LB16]` are my own measurements of
`FrameTokenizer.encode_text` on this machine and they vary run to run; the cycle counts are exact and the
seconds are not.

**Two corrections I make to my own first pass.** `[LB3]`'s first version had a refinement routine that exited
immediately (it tested its fixed point on the multiset of colour-class sizes instead of on the partition) and
its first world signature counted only class sizes, which merges two worlds that share a class-size pattern and
differ in classes. Both were caught by cross-checking against `lb5_refine_debug.py`'s six synthetic shapes and
against `lb7_degree_vs_iso.py`'s two independent partitions; the corrected `lb3_wl_signatures.py` regenerates
`lb7`'s 6 classes and its 320 same-class pairs as an independent count. The defective script and its output were
deleted, not kept.
