# Evaluation design v0.3: HSET-2, the improved test (`PROPOSED`, frozen at the commit that marks it `AGREED`)

**Authority.** The owner's direction of 2026-09-24, item 1 (`_handoffs/HELM_NEXT_PHASE_20260923/OWNER_DIRECTION_20260924.md`):

> Build the improved test as a new version beside the historical test. Use five- and six-part problems within the
> accepted checker's scope, with six-part problems as the main next difficulty level. Do not add seven-part cases
> until the checker and actual learner path support them through a separately tested change. Bigger is not
> enough. Include different wiring with the same simple counts, genuine no-match/no-path cases, and structures
> withheld from teaching and candidate-bank exposure. Fix the success rules before tuning.

**Owners.**
- Design, sealed build and custody: the Claude coordinator.
- Review: a fresh reviewer before any build.
- Sign-off: the owner, together with the named training plan.

**Status.**
- No model has been run on anything here, and nothing here is a result.
- `EVALUATION_DESIGN_v0_2.md` and HSET-1A stay unchanged. They are the historical test.
- The 6/7-node HSET-1B design (`hset1a/BUILD_SPEC_HSET1B_v0_1.md`) is **superseded, never built**. Its salt stays
  in the archive, unused.

## 0. What changes from v0.2, in one paragraph

- **Sizes.** v0.2 Stage 1 tested reach at 5 nodes, where a no-learning two-hop rule is right on 95-99% of balanced
  cells (W = 2 on TEST). v0.3 moves the main level to **6 nodes** and keeps 5 nodes as a secondary level.
- **Kinds.** It adds the Stage 2 kinds, **analogy** and **correspondence**, which checker v2 (`7f85af1e`,
  ACCEPTED) scores up to 6 nodes.
- **Harder questions.** It requires:
  - decoys with the same simple counts but different wiring;
  - real no-match and no-path answers;
  - shapes withheld from all teaching and from every candidate bank outside TEST.
- **Rules first.** Every success rule is written here, before any cell is built or any model is read or tuned.
- **7 nodes** are out of scope until a separately tested checker and learner change allows them.

## 1. Scope

| Level | Kinds that can carry a claim | Kinds that are diagnostic only |
|---|---|---|
| **6 nodes (main)** | reach (both rule IDs), analogy, correspondence | parts, edge_account |
| **5 nodes (secondary)** | reach (both rule IDs), analogy, correspondence | parts, edge_account |
| 3-4 nodes (historical) | none | the historical panels, unchanged |

**Why parts and edge_account are diagnostic only.** Their bar reads the answer straight off the input: HSET-1A bar
accuracy 1.000000 on every cell.

**Kind definitions** (`course.py` REQUESTS, unchanged):
- **Analogy.** Choose a bank world with a distinct declared domain and an isomorphic complete graph. Answer
  `NO_MATCH` only if none qualifies.
- **Correspondence.** Map every focus node one-to-one onto the target world, preserving every edge. Every valid map
  is accepted. Answer `NO_MATCH` only when no such map exists.

**Learner path.** Every claim-bearing cell needs the actual learner to answer 5- and 6-node questions through the
separately built and tested larger-question path (HELM-LARGER-QUESTION-PATH-1). Until that path passes its AWS
tests, no model is read on any v0.3 cell.

## 2. Shapes and splits

Every shape is acyclic and weakly connected. Every node's in-degree and out-degree is at most 4, so Helm's degree
buckets stay exact. Each shape class is reduced to its canonical form over all n! node orders.

| Level | DEV (public; the builder may use) | TEST (sealed) | WITHHELD (sealed; decoys for TEST banks only) |
|---|---|---|---|
| 5 nodes (all 267 classes known) | HSET-1A `DEV_NEW_5`: the same 60 shapes | HSET-1A `TEST_NEW_5`: the same 60 shapes (same salt, same selection code; **not re-drawn**) | the other 147 classes |
| 6 nodes (sampled) | `DEV_NEW_6`: 60 shapes, public seed `HSET-2-dev-shapes-v0.1` | `TEST_NEW_6`: 60 shapes, from a **new HSET-2 salt** (sha256 committed before the build) | `WITHHELD_6`: 120 more shapes from the same salt |

**How 6-node shapes are drawn.**
- Sampler: the reviewed MIX sampler of the HSET-1B spec (half uniform density, half deeper tree-like).
- TEST and WITHHELD skip every class DEV took. No class appears in two splits; this is asserted at build.
- **Collision requirement.** At least half of the TEST classes at each level must belong to a **degree-collision
  group**: at least one other non-isomorphic class with the same node count, edge count and in/out-degree multiset,
  inside TEST ∪ WITHHELD. The share achieved is printed.

**Withheld from teaching and from candidate banks:**
- TEST and WITHHELD shapes never appear in any training update, development evaluation, or candidate bank outside a
  TEST question.
- DEV banks draw only from DEV shapes.
- The training course of the next experiment is the unchanged Helm 2.0 course (3-4 nodes), so it touches no 5- or
  6-node shape. This is still checked (section 6).

## 3. Questions

**All kinds:**
- Words come from the trained vocabulary only (`declaration_labels`).
- Each question has 2 presentations, each a random relabelling of node ranks. A question counts as right only if
  both presentations are right. Every comparator is held to the same rule.

### 3.1 Reach (as HSET-1A, at 5 and 6 nodes)

- **Balance.** Cells are balanced ABSENT / DIRECT / VIA **by clusters**, for both rule IDs.
- **Genuine no-path.** ABSENT includes wholes that have children but no path to the part.
- **Ties.** Tie questions (the gold depends on the lexical tie-break) stay outside the primary cells and are
  reported.

### 3.2 Analogy (5 and 6 nodes)

- **The focus world** is a TEST shape.
- **The bank** has 8 worlds: the focus plus 7 others, all TEST or WITHHELD shapes of the same level.
- **MATCH items (about 70%)** contain exactly one qualifying partner: isomorphic, with a distinct domain.
  - At least 3 decoys are **degree-colliding and not isomorphic**: the same counts, different wiring.
  - About one item in four also holds a **same-domain isomorphic distractor**, which is not a valid answer.
- **NO_MATCH items (about 30%)** contain no qualifying world. Every non-focus world has the focus's node and edge
  counts, and at least 3 have its degree multiset. The no-match is genuine: counting cannot reject the candidates.

### 3.3 Correspondence (5 and 6 nodes)

- **MAPPING items (about 70%).** The target is a relabelled isomorphic copy. Every valid map (automorphisms
  included) is accepted, as the checker already does.
- **NO_MATCH items (about 30%).** The target is a degree-colliding, non-isomorphic TEST or WITHHELD shape, with the
  same counts and different wiring.

## 4. Clusters, bars and power

### Clusters: the unit of evidence

| Kind | One cluster is |
|---|---|
| Reach | (shape, whole, part), up to automorphism |
| Analogy | (focus class, the multiset of bank classes, the answer status) |
| Correspondence | (focus class, target class) |

A model gets a cluster right only if every item and every presentation in it is right.

### The bar for each cell: the best of these no-learning rules on that cell

| Kind | Comparators |
|---|---|
| Reach | constant; rank-last; one-hop; lowest-rank child; two-hop via the first child; participant-2; degree multiset (v0.2) |
| Analogy | always NO_MATCH; the first candidate; node and edge count match; degree-multiset match; flag match; the best fixed candidate position (focus-blind); candidate-only novelty |
| Correspondence | always NO_MATCH; identity by rank order; degree-sorted matching (NO_MATCH when the degree multisets differ) |

**Ceilings, not bars:**
- the checker's exact search (checker v2);
- a 1-dimensional Weisfeiler-Lehman colour refinement (the same colour-passing idea as message rounds), printed for
  analogy and correspondence as a reference.

### Printed per cell BEFORE any model is read

- clusters;
- W = the primary clusters the bar gets wrong;
- the bar's name and accuracy;
- conditional power of the exact test at a stated effect size.

**Floor.** A cell with fewer than 10 clusters or W below 10 reads `can_carry_a_claim: false`. That is said before
any run.

## 5. Success rules, FIXED BEFORE ANY TUNING (read by a program, never from prose)

- **Per cell, per run: `BEATS_NO_LEARNING_BAR`** (unchanged from v0.2 section 1.3).
  - b = clusters the model gets right and the bar gets wrong; c = the reverse.
  - Pass iff b > c and the exact one-sided p(b, b + c) <= 1/100.
  - There is no zero-loss veto.
- **Claims**, each needing its cells to pass in **every one of the 3 runs:**

| Claim | Cells | Level |
|---|---|---|
| `REACH_TRANSFERS_TO_NEW_STRUCTURE_6` | `TEST_NEW_6/REACH_FIRST_DIRECT` and `TEST_NEW_6/REACH_BFS` | main |
| `ANALOGY_STRUCTURE_TRANSFER_6` | `TEST_NEW_6/ANALOGY` | main |
| `CORRESPONDENCE_STRUCTURE_TRANSFER_6` | `TEST_NEW_6/CORRESPONDENCE` | main |
| `..._5` versions of the three above | the `TEST_NEW_5` cells | secondary |

- **Claims are separate.** None is pooled or traded against another. All are reported.
- **A missing cell makes the claim `NOT_TESTABLE`.** If any cell of a claim cannot carry a claim, the claim reads
  `NOT_TESTABLE`, and the cell is never dropped to rescue it.

### 5.1 The controlled repaired-versus-unchanged comparison (the owner's next model experiment)

- **Arms.** Repaired (switch ON) and unchanged (switch OFF, the Helm 2.0 layout). Both are trained on the same
  course, with the same seeds and matched starts. Each seed gives one pair.
- **`REPAIR_BEATS_UNCHANGED_<cell>`**, per seed pair, on the SAME TEST clusters:
  - b = clusters the repaired run gets right and the unchanged run gets wrong; c = the reverse;
  - pass iff b > c and the exact one-sided p <= 1/100.
- **`REPAIR_IMPROVES_ANALOGY_6`** requires all of these:
  - `REPAIR_BEATS_UNCHANGED_ANALOGY` on `TEST_NEW_6/ANALOGY` in **all 3 seed pairs**;
  - the repaired runs reading `ANALOGY_STRUCTURE_TRANSFER_6`;
  - probe v0.2 `PRESENT_GRAPH_AND_DOMAIN` on every trained repaired checkpoint that is read (prereg A5);
  - **no regression:** on every historical held-back gate and every other claim-bearing v0.3 cell, the repaired run
    does not fail a cell or gate that the unchanged run of the same seed passes. A regression is reported by name,
    and it blocks the claim.
- **Other cells.** The same paired rule is reported for every other claim-bearing cell. None is required, and none
  may replace the analogy requirement after results are seen.

### 5.2 Tuning

- Hyperparameters, schedules and model choices may be tuned only on DEV.
- Every change made after any DEV reading is logged with its date and reason.
- TEST is read once per registered run, only after the owner approves the run plan.

## 6. Custody

- **Where sealed material lives.** TEST and WITHHELD shapes, their questions, answers and the new salt stay only in
  `D:/tksCAS-archive/hset2_sealed_<date>/`, with a second private copy (see the inventory proposal). **Nothing
  sealed is committed to git.** Only digests are committed.
- **What the builder gets:** this design, the generator code, DEV and the comparators.
- **Manifest check before any TEST reading.**
  - The runner submits a digest-listed manifest of every world touched by any update, development evaluation or
    candidate bank.
  - The custodian checks it against the sealed canonical forms by two isomorphism methods, and fails closed on any
    match.
- **Scoring.** The custodian runs the forward passes on AWS, scores with checker v2, and publishes inputs, answers,
  predictions and scores together.
- **The label** stays `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT` until an outside custodian repeats the scoring.

## 7. Build, before any model

1. **Code.** `hset2_build.py`, reusing the reviewed HSET-1A/1B code by import. A fresh review runs before any
   paid run.
2. **Salt.** A new HSET-2 salt is made, and its sha256 is committed before the build.
3. **Run.** An AWS CPU job, with a throwaway-salt smoke stage first. Ceiling $1.00 (precedent: HSET-1A cost at
   most $0.1827).
4. **Print.** Every cell's clusters, W, bar and power, the collision share, and the split disjointness.
5. **To the owner.** The printed table goes to the owner with the named training plan. **If a claim-bearing cell
   cannot carry a claim, that is reported before any training, not after.**
