# Evaluation design v0.4: HSET-2, the improved test (`PROPOSED`; frozen at the commit that marks it `AGREED`)

**Supersedes** `EVALUATION_DESIGN_v0_3.md`, which stays unchanged as the reviewed version.

**Answers** `REVIEW_v0_3_20260924.md` (verdict `CHANGES_REQUIRED`: B1, M1-M11, m1-m6, N1-N4). Every finding is
answered in section 0.

**Authority.** The owner's direction of 2026-09-24, item 1: "five- and six-part problems within the accepted
checker's scope, with six-part problems as the main next difficulty level ... Include different wiring with the same
simple counts, genuine no-match/no-path cases, and structures withheld from teaching and candidate-bank exposure. Fix
the success rules before tuning."

**Status.** No model has been run on anything here, and nothing here is a result. The reviewer's numbers are
estimates made with throwaway salts. The build prints the real ones before any model is read.

## 0. How each review finding is answered

| Finding | Answer in v0.4 |
|---|---|
| B1 too few decoy problems; clusters can be inflated | The analogy cluster is the **focus class** (s5). The 10-floor applies to foci AND to distinct degree groups (s7). 6-node shapes are split by **whole degree group** (s3). **Analogy at 5 nodes is `NOT_TESTABLE`, declared now** (s1) |
| M1 correspondence bar too weak | Registered: `DEGREE_GUESS_THEN_CHECK` and `FLAG_ANCHOR_GUESS_THEN_CHECK`. The line drawn: a bar may make one guess and check it, but may not search (s6) |
| M2 flags leak | Every world gets its whole, participants and kind word drawn **fresh**. `FLAG_ANCHOR` comparators are registered, and flag-image rates are printed (s4) |
| M3 bank status leaks | Every NO_MATCH bank is the **twin** of a MATCH bank. At least 3 same-degree decoys from other domains. The same-domain distractor goes in both statuses at one rate. Profile equality is asserted, and a status-by-count comparator is registered (s5, s6) |
| M4 three-hop nearly solves reach | `THREE_HOP_FIRST_CHILD` is registered. **Two reach claims are named for what they show:** `REACH_3_STEP_TRANSFER_6` (bars without three-hop) and `REACH_4_STEP_TRANSFER_6` (bars with it). Both are always reported (s7) |
| M5 claim words | Every claim is named `..._BEYOND_DEGREE_...` and carries the scope sentence. 1-WL and colour refinement are printed diagnostics, never bars (s1, s6) |
| M6 collision requirement | Printed, never required. No salt is re-drawn to meet it (s3) |
| M7 DEV cannot copy the recipe | A public `DEV_DECOYS_6` from the DEV side's degree groups. DEV_5 analogy uses a named relaxed recipe and is feedback only (s3, s5) |
| M8 which arm | Every base claim is evaluated **per arm** and named with its arm. Both arms are always reported (s7) |
| M9 no-regression not program-ready | A listed gate set, and a **paired** regression test. Cells that cannot carry a claim are left out, and this is said (s7.2) |
| M10 degree definition | "Degree multiset" is the sorted list of **joint (in-degree, out-degree) pairs**, `hset_worlds.degree_multiset` (s2) |
| M11 fixture custody | A digest-listed `PUBLIC_EXCLUDED` list, asserted at build, open-ended. The digest-leak pattern is never used for sealed material (s3, s8) |
| m1 loose numbers | Exact item counts per focus. The power grid is named (s5, s7) |
| m2 presentations | Each presentation relabels **every** world in the packet. The partner's position is printed (s5) |
| m3 correspondence bank | The correspondence packet's bank holds exactly the target. New packet code is reviewed with `hset2_build.py` (s5) |
| m4 untrained NO_MATCH | Trained answer states are printed beside every cell (s7) |
| m5 bar choice | The model must beat **every** registered comparator of the cell (an intersection-union test), not only the best one (s7) |
| m6 multiplicity | The family-wise risk is stated (s7) |
| N1 sampler secrecy | The whole 6-node TEST side is forbidden to training, not only the drawn foci. The manifest covers DEV readings, fixtures, smoke and probe inputs. TEST_NEW_5's earlier passes are recorded (s8) |
| N2 reach spread | "Distinct shapes behind W" is printed per cell (s7) |
| N3 checker scope | Holds, and is unchanged |
| N4 repair shows degree-only | Per-cell paired results are always reported, even when `REPAIR_IMPROVES_ANALOGY_6` fails (s7.2) |

## 1. Scope and what a claim can say

**The scope sentence.** It is part of every claim below: "At 6 nodes or fewer this test can show that the model does
better than every registered no-learning rule, including degree counting. It cannot tell full structural comparison
from one hop of neighbour-degree matching."

| Level | Claim-bearing cells | Declared `NOT_TESTABLE` now (before any build) | Diagnostic only |
|---|---|---|---|
| **6 nodes (main)** | reach (both rule IDs), analogy, correspondence | — | parts, edge_account |
| 5 nodes (secondary) | correspondence | **analogy**: the whole 5-node universe has only 6 degree groups with 4 or more members (reviewer's count). **reach**: HSET-1A measured W = 2 on `TEST_NEW_5` | parts, edge_account, 5-node analogy (a relaxed recipe) |

## 2. Definitions

- **Degree multiset.** The sorted list of joint (in-degree, out-degree) pairs, as `hset_worlds.degree_multiset`
  computes it. Separate in-degree and out-degree lists are never used.
- **Degree group.** All shape classes that share a node count and a degree multiset.
- **Class.** A shape up to isomorphism: canonical form over all node orders.
- Every node's in-degree and out-degree is at most 4. Shapes are acyclic and weakly connected.

## 3. Shapes and splits

**`PUBLIC_EXCLUDED`.**
- A digest-listed file of every 5- or 6-node class used publicly with a trained model or in any candidate bank.
- It is fixed before the 6-node split and is open-ended: any later public shape joins it before its first use.
- **Version 1:** every 5- or 6-node class in the larger-question fixture file (`785c9bd1`, fixture file sha256
  `7f0760c7...`). The custodian counted 7 classes: 3 at 5 nodes, 4 at 6 nodes. They include the named shapes S5A,
  S5B, S5C, S6A, S6B and S6D. The file lists each class by its canonical-form digest. None of the 7 is in `TEST_NEW_5`
  (`9656dc19`).

**5 nodes (all 267 classes):**
- `DEV_NEW_5` and `TEST_NEW_5`: the HSET-1A splits, the same salt and code, never re-drawn.
- `WITHHELD_5`: every class not in `DEV_NEW_5`, not in `TEST_NEW_5` and not in `PUBLIC_EXCLUDED`. The build asserts
  this.

**6 nodes (all 5,074 classes enumerated):**
1. Remove the `PUBLIC_EXCLUDED` classes.
2. Group the rest into degree groups.
3. Put each whole group on the **DEV side** or the **TEST side**. A group goes to the DEV side when the first byte of
   sha256(`HSET-2-group-side-v0.1:` + group key) is below 64. That is a public, fixed rule giving about 1/4 of groups.
4. **`DEV_NEW_6`:** 60 foci drawn by the reviewed MIX sampler with the public seed `HSET-2-dev-shapes-v0.1`,
   keeping only DEV-side classes.
5. **`DEV_DECOYS_6`:** every other DEV-side class. It is public.
6. **`TEST_NEW_6`:** 60 foci drawn by the MIX sampler with the **new HSET-2 salt**, keeping only TEST-side classes.
   The salt's sha256 is committed before the build.
7. **`WITHHELD_6`:** every other TEST-side class.

**Forbidden to all training and development.** The whole TEST side (TEST and WITHHELD), `TEST_NEW_5` and `WITHHELD_5`.
The group rule is public, so anyone can check the forbidden set without learning which classes are the TEST foci.

**The collision share.** The share of TEST classes in a group with a same-degree partner is **printed, never
required**. No salt is ever re-drawn to change any printed number.

## 4. Worlds, flags and words (every world, every item)

- For **every** world (focus, partner, distractor, decoys, fillers, correspondence target), each item draws fresh, by
  one rule:
  - the declared whole: a uniformly random root;
  - the two other participants: uniformly random other nodes;
  - the kind word: uniformly from that world's domain.

  Nothing is copied from the focus.
- Domain, setting and function words come only from the trained vocabulary (`declaration_labels`).
- **Printed per cell and per status:** how often the partner's (or target's) flags fall on the images of the focus's
  flags.

## 5. Questions and exact counts

**Presentations.** Each item has 2 presentations. Each presentation relabels **every** world in the packet, so the
candidate aliases W0.. reorder too. An item is right only if both presentations are right. Every comparator is held to
the same rule. The partner's alias in each presentation is printed.

### 5.1 Reach (6 nodes, both rule IDs)

- As HSET-1A and HSET-1B, on `TEST_NEW_6` foci.
- **Balance.** Cells are balanced ABSENT / DIRECT / VIA by clusters, with k per state = the smallest available count.
- **Genuine no-path.** ABSENT includes wholes that have children but no path to the part.
- **Ties** stay outside the primary cells and are reported.
- **Cluster:** (shape, whole, part) up to automorphism.

### 5.2 Analogy (6 nodes)

**Eligible foci.** Every `TEST_NEW_6` class with **at least 4** non-isomorphic classes in its degree group on the TEST
side. The count, and how these foci differ from the rest of TEST, are printed.

**Items per focus: exactly 2.** Each has an 8-world bank (the focus plus 7):
- **MATCH:** the partner (a relabelled isomorphic copy in another domain) + 3 same-degree, non-isomorphic decoys in
  other domains + 3 slots, described in the next bullet.
- **NO_MATCH, the twin:** the same bank, with the partner replaced by one more same-degree, non-isomorphic,
  other-domain decoy.
- **The 3 slots,** identical in both twins:
  - for exactly half of the eligible foci (chosen by salted hash): 1 same-domain isomorphic distractor (a genuine
    near-miss) + 2 fillers;
  - for the other half: 3 fillers.
  - Fillers have the focus's node count and a different degree multiset. Their domains are drawn uniformly.

**Checked at build:**
- the bank profile (counts of worlds with the focus's node count, edge count, degree multiset and domain) has the same
  distribution in both statuses;
- 3 same-degree other-domain decoys in every bank.

**Cluster = the focus class** (both items and both presentations must be right). Distinct degree groups are also
printed.

### 5.3 Correspondence (6 nodes main, 5 nodes secondary)

**Eligible foci.** TEST foci with at least 1 same-degree, non-isomorphic partner on the TEST side (at 5 nodes: in
`TEST_NEW_5` ∪ `WITHHELD_5`).

**Items per focus: exactly 2:**
- **MAPPING:** the target is a relabelled isomorphic copy. Every valid map, automorphisms included, is accepted.
- **NO_MATCH:** the target is one same-degree, non-isomorphic class from the focus's group.

**The packet's bank holds exactly the target world.** This is new packet code, and it is reviewed with
`hset2_build.py`.

**Cluster = the focus class.**

### 5.4 DEV

- DEV_6 items follow the same recipes, using `DEV_DECOYS_6`.
- DEV_5 analogy uses a named relaxed recipe (decoys = any same-node-count, non-isomorphic DEV_5 class). It is
  feedback only.

## 6. Comparators (every one registered, every one a bar)

| Kind | Registered comparators |
|---|---|
| Reach | constant ABSENT; constant DIRECT; rank-last child; one-hop; lowest-rank child; two-hop via the first child; **three-hop via the first child** (the BFS variant for the BFS rule); participant-2; degree rule |
| Analogy | always NO_MATCH; first candidate; node and edge count match; joint degree-multiset match; **`FLAG_ANCHOR`** (a same-degree candidate whose whole and participants have the focus's (in, out) degrees); best fixed candidate position; candidate-only novelty; **`STATUS_BY_COUNT`** (NO_MATCH if fewer than m same-degree other-domain candidates, m at its best value on the cell); other-domain-only (the unique other-domain same-degree candidate, else NO_MATCH) |
| Correspondence | always NO_MATCH; identity by rank order; degree-sorted matching; **`DEGREE_GUESS_THEN_CHECK`** (one degree-sorted guess, check every edge, NO_MATCH on failure); **`FLAG_ANCHOR_GUESS_THEN_CHECK`** (map the whole and participants first, then guess by degree, then check) |

**The line.** A comparator may make **one** guess and check it. It may not search. Exact search is the ceiling.

**Printed diagnostics, never bars:**
- longest path;
- number of reachable pairs;
- each node's (in, out, descendants, ancestors) signature;
- 1-round and full directed colour refinement. On this universe full refinement separates every pair, so it equals
  exact search.

## 7. Success rules, FIXED BEFORE ANY TUNING (read by a program)

**Per cell, per run: `BEATS_ALL_REGISTERED_BARS`.**
- For **every** registered comparator X of the cell: b_X = clusters the model gets right and X gets wrong, and c_X =
  the reverse.
- The cell passes iff, for every X, b_X > c_X and the exact one-sided p(b_X, b_X + c_X) <= 1/100. There is no
  zero-loss veto.
- This is an intersection-union test, so it needs no multiplicity correction.

**Before any model is read, printed per cell:**
- clusters;
- W_X for every comparator; the binding W is the smallest W_X;
- for analogy, distinct degree groups;
- distinct shapes behind the binding W;
- conditional power on the HSET-1A grid (bar accuracy +0.10, +0.20, +0.30 and 1.0; never-loses fractions 0.5, 0.75
  and 1.0);
- the trained answer states of the kind (for example, whether NO_MATCH was ever trained).

**Floor.** A cell reads `can_carry_a_claim: false` if clusters < 10, or binding W < 10, or (analogy) distinct degree
groups < 10. Its claim is then `NOT_TESTABLE`, and the cell is never dropped to rescue it.

### 7.1 Base claims, evaluated per arm and always reported for both arms

Each claim below means: that arm's cell(s) pass in **all 3 runs of that arm**, with the scope sentence of section 1.

| Claim | Cells | Bars |
|---|---|---|
| `REACH_3_STEP_TRANSFER_6[arm]` | `TEST_NEW_6/REACH_FIRST_DIRECT`, `TEST_NEW_6/REACH_BFS` | every registered reach comparator **except** three-hop |
| `REACH_4_STEP_TRANSFER_6[arm]` | the same two cells | every registered reach comparator, three-hop included |
| `ANALOGY_BEYOND_DEGREE_6[arm]` | `TEST_NEW_6/ANALOGY` | all analogy comparators |
| `CORRESPONDENCE_BEYOND_DEGREE_6[arm]` | `TEST_NEW_6/CORRESPONDENCE` | all correspondence comparators |
| `CORRESPONDENCE_BEYOND_DEGREE_5[arm]` (secondary) | `TEST_NEW_5/CORRESPONDENCE` | all correspondence comparators |
| `ANALOGY_BEYOND_DEGREE_5`, `REACH_..._5` | — | **`NOT_TESTABLE`, declared now** |

**Family-wise risk.** There are up to 5 testable base claims per arm, each with a false-pass risk of at most about 0.01
per run. None is pooled or traded against another.

### 7.2 The controlled repaired-versus-unchanged comparison (the owner's next model experiment)

**Arms:**
- **repaired:** switch ON;
- **unchanged:** switch OFF, the Helm 2.0 layout.

Both train on the same course, with the same seeds and matched starts. Each seed gives one pair.

**`REPAIR_BEATS_UNCHANGED_<cell>`**, per seed pair, on the same TEST clusters:
- b = clusters the repaired run gets right and the unchanged run gets wrong; c = the reverse;
- pass iff b > c and the exact one-sided p <= 1/100.
- It is **always reported for every claim-bearing cell**, whatever else passes.

**`REPAIR_IMPROVES_ANALOGY_6`** requires all four:
1. `REPAIR_BEATS_UNCHANGED_ANALOGY` on `TEST_NEW_6/ANALOGY` in all 3 seed pairs;
2. `ANALOGY_BEYOND_DEGREE_6[repaired]`;
3. probe v0.2 `PRESENT_GRAPH_AND_DOMAIN` on every trained repaired checkpoint that is read (prereg A5);
4. **no regression** on the gate set below.

**The gate set, fixed now:**
- **H1:** `G_LEARN_population`, computed by `records/typed_pointer_001/evaluate_gates.py` on Helm's historical
  held-back questions. Its own rule: b > c, exact p <= 1/100, at least 2 kinds and 2 worlds.
- **H2:** `G_LEARN_all_kinds`, from the same program.
- **V:** every v0.4 cell of section 7.1 that reads `can_carry_a_claim: true`. Cells that cannot carry a claim are left
  out, and the list of left-out cells is printed.

**Regression, per seed pair and per gate.**
- On the gate's own question or cluster set: c′ = items the unchanged run gets right and the repaired run gets wrong;
  b′ = the reverse.
- It is a regression iff c′ > b′ and the exact one-sided p(c′, b′ + c′) <= 1/100.
- Threshold crossings (one arm passes a gate and the other fails it) are reported by name, as information only.

**What is always reported.** Every paired result, even when `REPAIR_IMPROVES_ANALOGY_6` fails. That keeps findings such
as "focus-aware, but only by degree" (review N4).

### 7.3 Tuning

- Hyperparameters, schedules and model choices may be tuned only on DEV.
- Every change after a DEV reading is logged with its date and reason.
- TEST is read once per registered run, only after the owner approves the run plan.

## 8. Custody

- **Where sealed material lives.** The TEST side's chosen foci, the questions, answers, and the HSET-2 salt live only
  in `D:/tksCAS-archive/hset2_sealed_<date>/` and its private S3 second copy. **Nothing sealed goes into git.** Only
  digests go there.
- **Manifest check before any TEST reading.** The runner lists every world touched by any update, development
  evaluation, DEV reading, probe or smoke input, and every larger-question fixture. The custodian checks the list
  against the whole forbidden set by two isomorphism methods, and fails closed on any match.
- **A digest can leak an answer.** A digest that covers both the answer and a correct/incorrect flag can be inverted
  when the answer space is small. So sealed-item receipts never publish such a digest.
- **`TEST_NEW_5` has been handled before.** It already passed through the HSET-1A AWS build and D-1 check X. Both are
  custodian runs, recorded.
- **The label** stays `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT` until an outside custodian repeats the scoring.

## 9. Build, before any model

1. **Code.** `hset2_build.py` (6-node enumeration, the group split, bank twins, every comparator, the new packets), plus
   the `PUBLIC_EXCLUDED` file. A fresh review runs before any paid run.
2. **Salt.** A new HSET-2 salt, with its sha256 committed first.
3. **Run.** An AWS CPU job, with a throwaway-salt smoke stage first. Ceiling $1.00.
4. **Print.** Everything in section 7's "printed before any model is read", plus split disjointness and the flag-image
   rates.
5. **To the owner.** The printed table goes with the named training plan. Any cell that cannot carry a claim is
   reported before training.
