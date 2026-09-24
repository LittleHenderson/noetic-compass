# Evaluation design v0.4: HSET-2, the improved test (`PROPOSED`; frozen at the commit that marks it `AGREED`)

**Supersedes** `EVALUATION_DESIGN_v0_3.md`, which stays unchanged as the reviewed version.

**Answers** `REVIEW_v0_3_20260924.md` (verdict `CHANGES_REQUIRED`: B1, M1-M11, m1-m6, N1-N4). Every finding is
answered in section 0.

**Authority.** The owner's direction of 2026-09-24, item 1: "five- and six-part problems within the accepted
checker's scope, with six-part problems as the main next difficulty level ... Include different wiring with the same
simple counts, genuine no-match/no-path cases, and structures withheld from teaching and candidate-bank exposure. Fix
the success rules before tuning."

**Status.** No model has been run on anything here, and nothing here is a result. The reviewer's numbers are
estimates made with throwaway salts. The build prints the actual informative-case and effective-unit counts before
main-comparison training. Amendment A2 below is a proposed correction for final owner review; it authorizes no run.

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
| Analogy | always NO_MATCH; first candidate; node and edge count match; joint degree-multiset match; **`FLAG_ANCHOR`** (a same-degree candidate whose whole and participants have the focus's (in, out) degrees); **every fixed non-focus candidate position 1 through 7**; candidate-only novelty; **every `STATUS_BY_COUNT_m`, m = 0 through 8**, with the complete answer rule fixed in A2.1; other-domain-only (the unique other-domain same-degree candidate, else NO_MATCH) |
| Correspondence | always NO_MATCH; identity by rank order; degree-sorted matching; **`DEGREE_GUESS_THEN_CHECK`** (one degree-sorted guess, check every edge, NO_MATCH on failure); **`FLAG_ANCHOR_GUESS_THEN_CHECK`** (map the whole and participants first, then guess by degree, then check) |

**The line.** A comparator may make **one** guess and check it. It may not search. Exact search is the ceiling.

**Printed diagnostics, never bars:**
- longest path;
- number of reachable pairs;
- each node's (in, out, descendants, ancestors) signature;
- 1-round and full directed colour refinement. On this universe full refinement separates every pair, so it equals
  exact search.

## 7. Success rules, FIXED BEFORE ANY TUNING (read by a program)

**Per cell, per run: the original cluster-level `BEATS_ALL_REGISTERED_BARS` calculation.**
- For **every** registered comparator X of the cell: b_X = clusters the model gets right and X gets wrong, and c_X =
  the reverse.
- The cell passes iff, for every X, b_X > c_X and the exact one-sided p(b_X, b_X + c_X) <= 1/100. There is no
  zero-loss veto.
- Beating all bars is a single conjunction. The intersection-union argument needs no correction *within that
  conjunction* if its component tests are valid. It does not establish independence, nor does it cover the separate
  claims below. A2 adds group and shared-shape sensitivity checks for the one confirmatory claim; the original
  cluster calculations remain visible as conditional/diagnostic results.

**Before main-comparison training, printed per cell (actual build, never a throwaway-salt estimate):**
- clusters;
- W_X for every comparator; the binding W is the smallest W_X;
- for analogy, distinct degree groups;
- distinct shapes behind the binding W;
- conditional power on the HSET-1A grid (bar accuracy +0.10, +0.20, +0.30 and 1.0; never-loses fractions 0.5, 0.75
  and 1.0);
- the trained answer states of the kind (for example, whether NO_MATCH was ever trained).
- A2's degree-group and shared-shape component counts, informative counts and power grid, alongside the original
  cluster counts. No raw-question or raw-cluster power number is labelled effective-unit power.

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

**Multiple claims.** A2 fixes one confirmatory claim: `REPAIR_IMPROVES_ANALOGY_6`. Every base claim in this table,
including each arm's three-run conjunction, remains registered and reported as exploratory. Its nominal 0.01
calculation does not carry a study-wide 0.01 guarantee. Neither repeated seeds nor correlated checkpoints justify
multiplying p-values. No exploratory finding becomes confirmatory after TEST is read.

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
3. the corrected, version-pinned probe's `PRESENT_GRAPH_AND_DOMAIN` on every preregistered trained repaired checkpoint
   in A5; the v0.2 bystander-normalization flaw must be resolved and validated before this gate can pass (A2.6);
4. **no regression detected by the listed paired tests** on the gate set below. This is not a preservation or
   noninferiority claim. A2 also requires the group and shared-shape checks for the primary analogy claim.

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
- Always print b′, c′, ties, both accuracies, the accuracy difference and all old-gate crossings, even if no test
  flags regression. Six losses and zero gains have p = 1/64 and are not flagged at 0.01. The historical grader and
  its frozen rule are unchanged; A2 adds reporting and limits the wording of the new comparison.

**What is always reported.** Every paired result, even when `REPAIR_IMPROVES_ANALOGY_6` fails. That keeps findings such
as "focus-aware, but only by degree" (review N4).

### 7.3 Tuning

- Hyperparameters, schedules and model choices may be tuned only on DEV.
- Every change after a DEV reading is logged with its date and reason.
- TEST is read once per registered run, only after the owner approves the run plan.
- The fixed primary endpoint is `final.pt` after 1,470 main updates. Intermediate checkpoint probes
  are mandatory mechanism checks, not a way to select a better TEST endpoint (A2.5).

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

## Amendment A1 (2026-09-24): the delta review's six changes (`REVIEW_v0_3_20260924.md`, delta section, `6b70f01c`)

The delta review's verdict was `APPROVE_WITH_CHANGES`. No build has run, and no model has been read.

- **D1: the group key is pinned byte for byte.**
  - The key is `hset_worlds.canon([6, [[i, o], ...]])`: canonical JSON (sorted keys, separators `,` and `:`,
    UTF-8), where the list is `hset_worlds.degree_multiset(n, edges)`, the sorted (in-degree, out-degree) pairs.
  - A group is on the DEV side iff `sha256(b"HSET-2-group-side-v0.1:" + key.encode("utf-8")).digest()[0] < 64`.
  - Stage 0 of the build is **public and runs first**. It enumerates the 6-node classes, removes `PUBLIC_EXCLUDED`,
    groups them, and writes the DEV-side group list and the TEST-side group list with their digests. Those are
    committed **before** the sealed stage runs.
  - No other spelling may be tried.
- **D2: 5-node correspondence foci are widened (a design choice made before any build; the owner signs it with the
  plan).**
  - As v0.4 was first written, `CORRESPONDENCE_BEYOND_DEGREE_5` would almost surely read `NOT_TESTABLE`: expected
    binding W 5.89, and W >= 10 in only 14 of 300 throwaway salts.
  - The foci are now **every class in `TEST_NEW_5` ∪ `WITHHELD_5` with at least one same-degree, non-isomorphic
    partner in that union**. The reviewer measured W 12 to 33, and >= 10 in 300 of 300 throwaway salts.
  - Custody is unchanged: all of these classes are already sealed and forbidden to training.
  - **The owner is told now that `REACH_4_STEP_TRANSFER_6` will almost surely read `NOT_TESTABLE`** (binding W 2 to 9
    in 10 of 10 salts). It stays registered and reported, and is never dropped.
- **D3: filler pools.** TEST items take fillers from the TEST side (TEST ∪ WITHHELD) of the same level; DEV items take
  them from `DEV_DECOYS_6`.
- **D4: gate pins and sensitivity.**
  - `records/typed_pointer_001/evaluate_gates.py` is pinned at LF sha256
    `d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d`.
  - Each gate's smallest detectable regression (the smallest c′ with b′ = 0 that gives p <= 1/100; that is 7) is
    printed beside it.
- **D5: the distractor split.** The analogy cell is also reported separately for the half of foci with the
  same-domain distractor and for the half without. This is diagnostic; the pass rule is unchanged.
- **D6: future public shapes.** After the build, any new public 6-node shape must be a DEV-side class, and any new
  public 5-node shape must be a `DEV_NEW_5` class. Anything else is refused before use.

## Amendment A2 (2026-09-24): controlled-study statistical policy (`PROPOSED`; no launch authority)

This amendment fixes the remaining choices before results. It preserves A1, every protected split, every registered
cell and every `NOT_TESTABLE` result. It does not modify the historical grader or reinterpret completed historical
receipts. The machine-readable companion is `../helm_controlled_prelaunch_20260924/STATISTICAL_POLICY.json`.
These are specification changes; they are not evidence that the builder or scorer already implements them.

### A2.1 Complete finite comparator families

- For an eight-world analogy packet, remove the focus and order the seven remaining displayed aliases by their
  numeric alias index (W0, W1, ...). `FIXED_POSITION_j`, j = 1,...,7, always returns that position as its candidate.
- For `STATUS_BY_COUNT_m`, m = 0,...,8, let E be the ordered non-focus candidates with the focus's joint degree
  multiset and a different domain. Return NO_MATCH if `len(E) < m` or E is empty; otherwise return E[0]. The answer
  carries the ordinary analogy candidate reference and is scored by the same frozen checker. Both presentations
  must pass, as for the model. This freezes both the status decision and the candidate chosen after it.
- Every family member is a registered bar, with its own W, gains, losses and p-value. There is no TEST-fitted
  threshold, no TEST-fitted position and no selection by highest accuracy or most favourable paired p-value.
  Duplicate predictions may share a calculation, but all registered rule IDs remain in the report. DEV may be
  used for model development; it cannot delete a bar or change these comparator families.

### A2.2 Units, dependencies and the limits of inference

The two presentations of an item, MATCH/NO_MATCH twins, and rooted questions from the same shape are not treated
as independent observations. Keep the original section 5 binary cluster scores and their exact paired calculations
unchanged. Label those calculations `CONDITIONAL_CLUSTER_DIAGNOSTIC`; report their sampling assumptions.

Add these two predeclared views for every claim-bearing cell:

1. **Degree groups.** Group the original clusters by their focus's joint degree multiset and node count. In a paired
   model/comparator or repaired/unchanged comparison, compute each group's mean of the original binary-score
   differences using exact rational arithmetic. The group is a win if the mean is positive, a loss if negative,
   and a tie if zero. Groups receive equal weight in the sign test. Also report the original aggregate accuracy
   difference; a passing direction must be positive in both views.
2. **Shared-shape components.** Before models are read, collect the canonical shape classes appearing in every
   packet role and presentation for each degree group: focus, partner, target, decoy, distractor and filler. Connect
   two degree groups if those sets intersect, and take transitive connected components. Never split a component
   after outcomes. For each component, take the equally weighted mean of its constituent degree-group differences;
   its sign is one sensitivity-test observation. Print the component count and size distribution. The class list
   and membership stay with the custodian; only permitted aggregates and non-answer-revealing receipts are public.

For either view, with B positive signs and C negative signs, use the exact one-sided sign-test tail
`sum(comb(B+C,k), k=B..B+C) / 2**(B+C)`; if B+C is zero, p = 1. Ties do not enter the denominator. Require B > C,
positive overall accuracy difference, and p <= 0.01. The shared-shape view is a conservative sensitivity check;
components do **not** prove independence. A p-value interpretation is conditional on independent units and
exchangeability of positive and negative paired differences under the null. The builder/scorer review must state
whether its sampling construction supports those assumptions. If it cannot, set `INFERENCE_ASSUMPTIONS_UNSUPPORTED`:
report all scores and conditional p-values, but issue no confirmatory statistical claim.

The MIX sampler is not a promise of representative performance on arbitrary graphs. The claim concerns the
registered generator, eligible protected strata and these three seed pairs. It does not establish that the repair
helps every seed, arbitrary larger graphs, or every possible no-learning algorithm. The 10-group floor measures
available information and variety; it is not proof of independence.

### A2.3 One confirmatory claim; all other results remain visible

- The sole confirmatory claim is `REPAIR_IMPROVES_ANALOGY_6`, at alpha = 0.01. Its performance component requires
  repaired to beat unchanged and every registered analogy bar at **each of the three** fixed seed pairs, using
  both additional views in A2.2. Its inferential p-value is the maximum of the required degree-group and
  shared-shape-component p-values. This intersection-union rule is valid only when those component tests are valid;
  it does not require independent seeds and never uses `0.01 ** 3`. Also retain the original cluster-level nominal
  pass as an additional acceptance condition, labelled conditional/diagnostic. It is not included as a claimed
  valid inferential p-value. Requiring this extra condition cannot increase the grouped test's false-pass risk.
- The corrected mechanism gate and the absence of a listed regression flag are additional acceptance conditions.
  Passing them does not turn a failure to detect regression into proof of preservation. Use the caption:
  **"The repair improved registered six-node analogy performance in all three seed pairs, cleared the registered
  bars and mechanism checks, and had no regression detected by the listed tests."** Attach the scope and control
  provenance limitation, including the two historical controls when option C is retained.
- Every other arm/cell result, the section 7.1 base claims, reach variants, five-node correspondence and distractor
  halves are mandatory exploratory results. Preserve their original nominal 0.01 calculations and report
  `EXPLORATORY_NOMINAL_PASS`, `EXPLORATORY_NO_NOMINAL_PASS`, or `NOT_TESTABLE`. They have no confirmatory allocation
  and no claimed study-wide false-positive guarantee. No selective omission, post-TEST promotion, or pooled rescue.
- A `NOT_TESTABLE` primary cell makes the primary claim `NOT_TESTABLE`; it does not make another cell primary.
  A failed assumption check makes it `INFERENCE_ASSUMPTIONS_UNSUPPORTED`. A missing required mechanism validation
  makes it `MECHANISM_GATE_OPEN`. Keep the underlying scores and reasons in every case.

### A2.4 Actual feasibility table before main training

The authorized custodian build must emit the following **actual** aggregate table before the main comparison is
submitted for launch approval. Do not use a throwaway-salt estimate, a count from HSET-1A, or a blank schema as a result.

- For every registered cell and bar: original cluster count; shapes; degree groups; shared-shape components;
  their size distributions; original W_X; W_X in the group and component views; and each view's binding minimum.
  Here W_X is the number of units in which a perfect model could improve on X under that view's aggregation.
  For repaired versus unchanged the corresponding actual informative count is unknowable before both models are
  scored; report `NOT_YET_OBSERVED`, plus the structural maximum and conditional power scenarios. Do not call it
  the realized discordant count. Report actual B, C and B+C once both outputs exist.
- Keep all existing floors. In addition, a confirmatory analogy claim needs at least 10 degree groups, 10
  shared-shape components, and binding W >= 10 in **each** additional view. If any floor fails, preserve
  `NOT_TESTABLE` and its reason. Do not redraw the salt, substitute foci, remove fillers, drop a bar or change a
  grouping rule to pass. A later design would require a new preregistration and new authorization before results.
- Recompute the HSET-1A power grid at the original-cluster, group and component levels separately, using that
  level's actual unit weights and sizes. Print the assumed gain/loss model, bar accuracy +0.10/+0.20/+0.30/1.0
  settings and never-loses fractions 0.5/0.75/1.0. Where a raw accuracy grid does not identify group-sign power,
  print `NOT_IDENTIFIED_FROM_RAW_ACCURACY` and use the explicit conditional sign-power calculation below.
- For each available unit count n, print conditional sign-test power for discordant counts d = 0,...,n and positive
  sign probabilities q = 0.60, 0.70, 0.80, 1.00: sum the Binomial(d,q) probability over B values whose exact null
  tail at q=0.5 is <= 0.01. Include the all-win minimum of 7 discordant units, and distinguish this sensitivity
  calculation from a forecast of actual model power. Use exact sums; no simulated performance may stand in for results.
- Print answer-state exposure, split disjointness, both-arm packet-route acceptance, flag-image rates, and the
  full listed/omitted regression-gate set. The actual table and immutable builder/scorer receipts must be attached
  to the final request. Missing or failed receipts are a pretraining blocker, even if training could run technically.

### A2.5 Endpoint and checkpoint accounting

`final.pt`, after 1,470 main updates, is the sole primary endpoint for every arm and seed. The separate 16
interference and 2 replay updates make the whole job's maximum allowance 1,488; they are not part of `final.pt`.
Fix this before running and print the phase schedule and artifact hash in each manifest.
The eighteen preregistered trained-checkpoint mechanism checks are an all-checkpoint requirement under A5, not
eighteen chances to select a passing endpoint. The launch manifest must enumerate all eighteen by seed, phase,
checkpoint path and update count; a mismatch or missing entry blocks launch. Initial untrained controls, if probed,
are labelled separately and do not replace any of the eighteen checks.

Intermediate checkpoints are evaluated only on the preregistered public mechanism probe; protected TEST is read
only at the fixed final endpoint, once per registered run. Retain every failed or missing mechanism check and all
final losses. Training more, selecting an earlier checkpoint or switching to a favourable seed after a TEST reading
is not permitted under this plan. Historical before/after grading remains unchanged.

### A2.6 Mechanism validation and non-regression language

Probe v0.2 recomputes candidate-set normalization after changing the bystander. That can change unchanged
candidates' normalized scores without a raw-score interaction. Its present result cannot close the repaired
mechanism gate. Before any main run, pin a reviewed correction that holds the reference normalization fixed or
uses a validated raw-score interaction metric, and freeze its thresholds and directional criterion before model
results. Required public validation includes candidate-independent scorers returning zero bystander interaction,
a scorer with a known true interaction returning the expected nonzero change, invariance to the permitted score
offset/scale transformation, and a signed test for the claimed movement toward the favoured set. Preserve v0.2
receipts as historical diagnostics; do not grandfather them into the corrected gate. Missing validation stays open.

Report **"no regression detected by the listed paired tests"** when that is the actual outcome. Always show every
loss, gain, tie, accuracy change, p-value and old-gate crossing; include six-loss/zero-gain sensitivity explicitly.
Do not say "no ability lost", "preserved performance" or "noninferior" from failure to reject this test. A stronger
zero-observed-loss or noninferiority rule would require its own owner-approved predeclared margin and analysis;
this amendment does not silently add one or alter the historical grader.

### A2.7 Builder comparator decisions, before the protected key

This is the single A2 specification. It incorporates the builder's proposed bars in the public review at
`bd960bc1ae351f9cf653fd865a9a9996e3c3aa75`; that proposal is not a competing amendment. These decisions resolve
D1-D4 in `claude-0019`. Claude implements and checks them before creating the protected key or sealed set.

- **D1: choose option (a), register the shortcut.** Add `FRONTIER_FALLBACK` to both reach variants and both
  registered reach claims. It first uses the registered two-hop answer. If that is ABSENT, it returns VIA only
  when a node exactly two steps from the whole has a child and the part has a parent. For first-child, choose
  the whole's child with most children, breaking ties by lowest rank. For BFS, choose among the part's parents
  that themselves have a parent, maximizing parent count and then minimizing rank. An empty eligible via set
  returns ABSENT. Freeze these deterministic choices in source; validate the full packet answer with checker v2.
  Reading a frontier node's degree is not evidence of following a path to the requested part at distance three.
- Keep `SINGLE_ROOT_FALLBACK` and `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP` exactly as specified in the public builder
  review section 2. The three-step claim excludes only the two explicitly three-hop rules
  `THREE_HOP_FIRST_CHILD` and `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP`; the four-step claim includes them.
  `FRONTIER_FALLBACK` is not excluded from the three-step bars. Every new bar is scored in all required views.
- Do not rebalance cells, rename a failed claim into a success, redraw the key, or remove a bar to restore power.
  The throwaway finding is 21/21 `NOT_TESTABLE` salts after this bar, with binding W 1/3.4/6 for first-child and
  0/1.1/2 for BFS. These are development estimates, not actual protected counts. Keep the reach claim registered
  and exploratory; actual counts determine its status. Even a nominal pass establishes only performance against
  the registered finite rules, not proof of learned three-step path following or exclusion of every shallow rule.
  A comparator defined by the best possible answer from an entire two-step information view is deferred to a
  separately preregistered successor design: neither its equivalence relation nor its allowed fitting procedure
  is currently specified. Do not label this finite list an exhaustive information-view control.
- **D2: add the one-guess bars.** For analogy register `DEGREE_GUESS_THEN_CHECK`,
  `WHOLE_ANCHOR_GUESS_THEN_CHECK`, `FLAG_ANCHOR_GUESS_THEN_CHECK`, and
  `DEGREE_FLAGS_TIEBREAK_GUESS_THEN_CHECK`. Each may make one deterministic mapping guess for each same-degree,
  other-domain candidate in displayed-alias order, check all required relations and flags, and return the first
  accepted candidate or NO_MATCH. No backtracking or second guess per candidate. The first three use the builder
  section-2 definitions. The fourth is verifier N1's degree sort, ties broken by declared flags and then rank;
  Claude must publish and pin the exact flag-key order and tie convention with public toy examples before the
  key is made. This name is distinct from anchoring the whole and participants. Correspondence also registers
  `WHOLE_ANCHOR_GUESS_THEN_CHECK` alongside its existing bars. Retain the exact-search ceiling separately.
- **D3: whole DEV side for eligible decoys and NO_MATCH targets.** Use the focus's degree group within
  `DEV_NEW_6` union `DEV_DECOYS_6`, excluding the focus and respecting the existing recipe's eligibility rules.
  This resolves section 5.4's ambiguity by matching TEST's same-side recipe. It does not cross the DEV/TEST
  boundary. A1 D3 is unchanged: filler worlds come only from `DEV_DECOYS_6`. Reprint actual DEV counts and label
  whether a count concerns foci, eligible decoys, targets or fillers. Published 27/52 foci are not a protected result.
- Clarify F4: the relabel-every-world requirement applies to analogy/correspondence bank tasks. Reach, parts and
  edge-account tasks retain their frozen 64-world bank and relabel the focus only. Before accepting this as
  implementation-conformant, the public review must verify both arms and their comparators consume only that
  focus for these tasks. This clarification does not permit information from ignored bank worlds to affect answers.
- **D4: retain every floor in A2.4.** In particular, confirmatory analogy needs ten degree groups, ten shared-shape
  components, and binding W at least ten in each additional view. The reported analogy W minimum of nine is a
  reason to report `NOT_TESTABLE`, never to lower a floor. Reach retains its existing floors; the new grouped
  views are reported as specified in A2.2. No salt is selected for favourable feasibility.

Before protected-key creation, Claude supplies the reviewed comparator manifest, digest, complete throwaway
feasibility ranges including groups/components, exact tie rules and public split/exposure attestation. After the
single authorized custodian build, publish only the permitted actual aggregate feasibility table, with every
`NOT_TESTABLE` row and reason, before main training. A1's protected partitions and grader pin are unchanged.
The documented overlap of 24/40 older public DEV classes with the TEST-side candidate pool remains an exposure
question requiring an attestation; do not assert clean novelty from stage-0 counts alone. This decision permits
continued preparation under existing roles; it does not itself establish a ready sealed build or main launch.
