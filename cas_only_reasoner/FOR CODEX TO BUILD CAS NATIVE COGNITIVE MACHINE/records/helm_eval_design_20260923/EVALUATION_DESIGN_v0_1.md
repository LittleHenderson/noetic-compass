# Prospective evaluation design v0.1: `PROPOSED_FOR_AGREEMENT`

**Owners.**
- Design and custody of the sealed test answers: Claude.
- Review of whether it can be built: Codex.
- Sign-off: the owner.

**Written:** 2026-09-23. No model has been run on anything in this design. Nothing here is a result.

**Why this exists.** The owner's order is: define the next evaluation before tuning, repair the missing
analogy comparison, then test the late reach loss with one controlled change. The old tests could not tell
structure transfer from renamed copies:
- the 64-world bank has only **6** contains-shapes;
- each shape appears in all 4 domains;
- every "held" world repeated a practised shape.

This design fixes that first.

**What stays frozen.** The frozen grader, the frozen 18 questions and every historical label are unchanged.
The historical panels stay as **diagnostics**, each reported with its own denominator and never mixed into
the new numbers.

**Four experiments, never pooled.** Each has exactly one runner, per the coordination record.

| Id | Experiment | Runner | Checker |
|---|---|---|---|
| `HSET-1` | Helm structure-transfer evaluation (this design, Part A) | Claude runs predictions on the sealed test; Codex supplies the model | Codex reviews the design |
| `HELM-ANALOGY-REPAIR-1` | analogy focus-to-candidate repair, compared with and without the repair (Part B) | Codex | Claude |
| `HELM-REACH-LATE-1` | the late reach loss, rate 0.003 vs 0.0003 from pass 1 (Part C) | Codex | Claude |
| `Q4-RECON-2` | Q4 expression reconstruction, three readouts (Part D) | Codex | Claude |

---

## Part A: `HSET-1`, the Helm structure-transfer set

### A1. The facts this design is built on

These were measured on 2026-09-23 by Claude over `records/typed_course_001/checks_002/public_course.json`.

- **The bank.** 64 worlds, of sizes 3 (12 worlds) and 4 (52 worlds). There are **6** distinct contains-shapes
  up to renaming. Each shape appears in all four domains (grammatical, procedural, container, mechanical):

  | Nodes | Shape (canonical edges) | Worlds |
  |---|---|---|
  | 3 | chain `0->1->2` | 12 |
  | 4 | star `0->{1,2,3}` | 12 |
  | 4 | diamond `0->{1,2}, {1,2}->3` | 12 |
  | 4 | chain `0->1->2->3` | 12 |
  | 4 | two roots `0->{1,2}, 3->1` | 8 |
  | 4 | fork and tail `0->{1,2}, 1->3` | 8 |

- **Shapes that are genuinely new.** These are weakly connected directed acyclic "contains" graphs, counted up
  to renaming by exhaustive enumeration, that are not isomorphic to any bank shape:
  - at 3 nodes: **3** (of 4);
  - at 4 nodes: **19** (of 24);
  - at 5 nodes: **267** (of 267).
- **The analogy rule** is `cross_domain_full_graph_isomorphism_v1`. The answer is any bank world with a
  different declared domain and an isomorphic complete contains-graph. `NO_MATCH` is correct only if none
  qualifies.

### A2. Three structure splits, reported separately and never pooled

| Split | What varies from training | Why it is there |
|---|---|---|
| `FAMILIAR_RENAMED` | Only names change: a bank shape with fresh node labels, fresh declarations and a permuted node order | Measures renamed copies, which is what the old "held" worlds were |
| `NEW_SHAPE_SAME_SIZE` | A 3- or 4-node shape not isomorphic to any bank shape | **The primary transfer test.** Size is held equal to training |
| `NEW_SHAPE_LARGER` | A 5-node shape | Separates size from structure. Its result is never used to claim structure transfer on its own |

**Two disjoint pools of new shapes.**
- **`DEV_NEW`:** the builder may see and use these during development.
- **`TEST_NEW`:** sealed. Claude alone holds them until evaluation.

At 3 and 4 nodes the 22 new shapes are split 11 / 11, deterministically, by a sealed salted hash of their
canonical form. At 5 nodes, 40 shapes go to `TEST_NEW` and 40 to `DEV_NEW`.

**Independent split checks, run before any use.**
- Every `TEST_NEW` world is checked non-isomorphic to all 64 bank worlds, all `DEV_NEW` shapes and every
  world any training record carries.
- Two methods are used: canonical form by exhaustive permutation, and sorted (in-degree, out-degree)
  multiset followed by brute-force isomorphism.
- They must agree on every pair.

### A3. Worlds and the candidate bank

- **Worlds.** Each test shape is instantiated in at least two domains, so that analogy has a correct
  cross-domain partner. The analogy items also include these cases:
  - a same-shape, **same-domain** decoy (a wrong answer);
  - different-shape, different-domain decoys;
  - about 25% of items where **no** cross-domain partner exists, so `NO_MATCH` is correct.
- **Labels.** Node labels and declaration words are fresh. Their overlap with every label and word the
  course ever showed must be **0**, proven when the set is built, as the ladder already does.
- **Presentations.** Each question is shown in **2** presentations: the node order is permuted and the
  labels are renamed. As in the frozen grader, a question counts correct only if every presentation is
  correct. Per-presentation accuracy is reported as well.
- **Candidate bank. This is a buildability question for Codex (Q-A1).** Helm's world-choice slots alias
  `W0..W64`, and `_query_vector` feeds `min(world_count, 64) / 64`. The requirement is:
  - the evaluation bank is exactly **64** worlds, so the `world_count` input matches training;
  - its composition is recorded;
  - every accepted-answer set is enumerated exactly by the reference checker.

  Codex should say whether the reading and slot code accept a bank other than the frozen one without edits.
  If they need edits, those edits must be ruled out as a change to the answer path.

### A4. Question families and balance

Each cell below is one (family × split) pair.

| Family | Composition per cell | Role |
|---|---|---|
| `reach` | ABSENT / DIRECT / VIA in equal thirds. VIA must name the checker's intermediate (`first_direct_constituent_lexical_v1`). **Tie cases**, where more than one intermediate qualifies and the gold depends on the lexical tie-break (the "diamond" issue), are a separate reported stratum | Primary (VIA) |
| `correspondence` | Half with an isomorphic target (valid bijections enumerated and counted); half non-isomorphic (`NO_MATCH`). Shapes with many automorphisms are flagged | Primary |
| `analogy` | About 75% with at least one accepted partner; about 25% `NO_MATCH` | **Primary. This is the family the repair targets** |
| `parts`, `edge_account` | Natural composition | Size controls only. A one-hop rule solves them, so they are never learning evidence |
| `definition`, `context`, `role_set` | Natural composition | Regression controls for declaration reading. Not structural evidence |

### A5. Sample size (`PROPOSED`, for the owner to sign)

- **80 test questions per primary cell** (reach-VIA, correspondence and analogy, in each of the three
  splits), plus presentations.
- **Why 80.** The exact one-sided binomial is computed at alpha = 0.01. Against a no-learning comparator
  at 0.25, a true accuracy of 0.50 needs **30/80** correct. Its power is **0.9908** per run and **0.9728**
  across three independent runs.
- **At 60 questions per cell,** the same numbers are 24/60, power 0.9538, and 0.8676 across three runs.
- **At 40 questions per cell,** the three-run power is 0.4841. That is too weak, which is the same failure the
  frozen 18 had (its three-run pass chance was at most 0.6839).

### A6. Comparators, registered before any output and reported separately

1. constant (`ABSENT` / `NO_MATCH`);
2. rank-last lexical guess;
3. one-hop adjacency rule;
4. degree-multiset comparator (A5's registered rule, which solves 70/70 historical analogy records);
5. exact graph search (the ceiling);
6. the reference checker's answer (the oracle, 1.0).

Items 5 and 6 are ceilings, not bars. The **bar** for a cell is the best of items 1 to 4 on that cell.
Deterministic comparator outputs are never labelled learned predictions.

### A7. Success rule (`PROPOSED`, for the owner to sign; to be read by a deterministic program)

- **Per cell, per run.** Pair each learned answer with the bar comparator's answer on the same questions.
  Let b = the questions the model gets right and the bar gets wrong; c = the reverse. The cell is
  `BEATS_NO_LEARNING_BAR` iff:
  - b > c; and
  - the exact one-sided p(b, b + c) <= 1/100.

  This deliberately mirrors the historical rule. It has no zero-loss veto.
- **`TRANSFERS_TO_NEW_STRUCTURE`, per family.** The cell `NEW_SHAPE_SAME_SIZE` is `BEATS_NO_LEARNING_BAR`
  in all three runs.
- **A second number, always printed beside the first:** each run's gain over its own untrained start. This
  is the historical view. It is printed as well, never instead.
- **Wiring is a prerequisite, not a success.** The analogy wiring probe (Part B1) must read PRESENT before
  any analogy cell is interpreted.

### A8. Custody: final answers stay out of the builder's development feedback

- Claude generates `TEST_NEW` and every test instance from a sealed salt. The inputs, answers and salt stay
  in Claude's custody, archived under `D:/tksCAS-archive/`. Only their **digests** are committed until
  evaluation.
- The builder receives this design, the generator code, the `DEV_NEW` split and the comparator code. From
  these the builder can reproduce everything except which shapes are `TEST_NEW`.
- **Evaluation.**
  1. The builder hands over a checkpoint and the inference code at a pinned commit.
  2. Claude runs predictions on the sealed test on the local GPU (forward only) and scores them with the
     frozen checker.
  3. Claude then publishes the inputs, answers, predictions and scores together.
- **Custody limit, stated plainly.** Claude is not an independent third party to the project, only to this
  build. The label stays `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT` until an outside custodian repeats the
  scoring.

### A9. Historical panels: diagnostics only, own denominators

Each keeps its own denominator:
- the frozen 18, through the frozen grader, unchanged;
- the 50 held questions (127 records);
- the 564 full registry records;
- the 96 retention records;
- the 59-question ten-node development panel (classes ABSENT/DIRECT/VIA/parts);
- the ladder `4436fb6b481ff606`, with its own reach rule.

The ladder's rule differs from the checker's on 18 of 373 VIA questions, so ladder numbers are always
quoted with the ladder's scorer, never mixed with checker-scored numbers.

---

## Part B: `HELM-ANALOGY-REPAIR-1`. Codex builds and runs; Claude checks.

- **B1. Wiring (the first thing to establish).** The probe in `analogy_wiring_probe/` has its rules frozen
  in `PREREG_ANALOGY_WIRING_PROBE.md`.
  - The repair must read `FOCUS_TO_CANDIDATE_DEPENDENCY_PRESENT` on fresh containers with its switch on.
  - With its switch off, it must reproduce the unchanged Helm 2.0 before-reading **exactly**.
  - Historical checkpoints must still load with `strict=True` with the switch off.
  - "Changing the arrangement Helm is asked to compare can now affect the relevant answer scores" is the
    whole claim of B1. Correct answers are not part of it.
- **B2. Declared change.** The record must include:
  - every new or reshaped tensor;
  - the parameter-count change from 174,303;
  - how the new tensors are initialised;
  - a migration record for loading 2.0 weights, listing each tensor as carried, reshaped, absent or fresh.

  The correspondence complete-assignment decoder is **not** touched. Before this investigation, some records
  described it wrongly: they said "per-node heads cannot express a bijection" and that it "needs Sinkhorn".
  The actual decoder already enumerates complete bijections. Helm 1.0's limit was a source-independent score
  row (A7).
- **B3. Matched comparison.**
  - **Two arms:** unchanged source `20208c923d41c24614504d4ecc2b289ecb66eda8`, and the same source with only
    the repair switched on.
  - **Seeds:** 20260917, 20260918 and 20260919.
  - **Same across arms:** course, schedule, rate, clipping and limits.
  - **Matched starts:** every tensor the arms share is bitwise equal at update 0. New tensors are drawn from a
    separate recorded seed.
  - **One change only.** No other change (message passing, normalisation, rate) enters this comparison.
- **B4. What is read.**
  - `HSET-1`, all families and all splits, per run.
  - Every historical panel.
  - The two A7 witness records, as a diagnostic only.
  - Regressions in any family are reported as plainly as gains.
- **B5. Limits.** These are set by Codex's job record under the current authorization before launch. A
  claim-bearing run goes to AWS GPU, under the compute rule.

## Part C: `HELM-REACH-LATE-1`. Codex runs; Claude checks. Kept apart from Parts B and D.

- **The design.** As in A7's `NEXT_ACTIONS.md` action 3: start from Helm 2.0 seed 20260919's saved pass-1
  checkpoint, with its optimizer and RNG state, at source `20208c92`. Run two branches: constant rate 0.003
  and constant rate 0.0003. The data, order and everything else are identical. The ceiling is 1,323 updates
  per branch.
- **What Claude checks before the modified branch is read.** The 0.003 branch must reproduce the original
  endpoint at p10 on query `typed-query-369885551a55...`:
  - `VIA_N1 = 26.474693298339844` against `VIA_N3 = 22.808488845825195`;
  - all four presentations answer `VIA /n1`.

  If it does not reproduce, the experiment stops there and the mismatch is the finding.

## Part D: `Q4-RECON-2`. Codex runs; Claude designs the readouts and checks. Never pooled with Helm.

Q4's model (StrictR1, a 70,818-parameter GRU) is a separate lab model. It is not Helm.

### D1. Three readouts, always reported separately

| Readout | Rows | Question it answers |
|---|---|---|
| `TEACHING_FIT` | exactly the rows used in updates, with showings per row recorded | Did it learn what it was taught? |
| `FAMILIAR_STRUCTURE_NEW_CONTENT` | visible train-pool rows **never used in an update**, whose bare tree shape occurs among the teaching rows. None may repeat a teaching row's expression string | Does it generalise to new content on shapes it has seen? |
| `NEW_STRUCTURE` | the visible dev split: 256 rows, depth 3, **9** bare shapes, **0** shared with the 16 train-pool shapes | Does it handle shapes it has never seen? |

The sealed eval split (depths 4 and 5) stays sealed for a later confirmatory claim.

### D2. Per readout

Report all of these:
- exact canonical AST;
- bare-shape match;
- leaf-sequence match;
- per-token accuracy.

Beside them, the comparators:
- the constant most-common training tree;
- R0 (byte-bag nearest neighbour);
- leaf-copy into a training shape;
- the deterministic parser (ceiling 1.0; a 20-line parser rebuilds 16/16).

### D3. No arm is presumed to be the answer

Longer training and a larger or different representation are **hypotheses**. Each becomes a separately
named, pre-registered arm, and each arm reports all three readouts. A budget-only arm and a
representation-only arm are run separately, so their effects are never confounded.

These existing diagnostics are labelled `DIAGNOSTIC_NOT_CLAIM_BEARING`. They are context only, not results:
- RT7 (8 rows, 2,000 updates): teaching 8/8 exact; dev 0/16.
- RT2 (256 rows, 2,000 updates): teaching 0/256; familiar 0/128; new 0/256.

---

## Part E: to agree before any comparison is read

| Item | Proposed value | Status |
|---|---|---|
| Starting source for the Helm experiments | `20208c923d41c24614504d4ecc2b289ecb66eda8` | PROPOSED |
| This design's digest | the LF sha256 of this file at the commit that marks it `AGREED` | OPEN |
| Test size per primary cell | 80 questions | PROPOSED, owner |
| Success rule | A7 | PROPOSED, owner |
| Test custody | Claude (A8) | PROPOSED |
| Per-job limits | each runner's job record under `docs/OWNER_RUN_AUTHORIZATION_20260922.md` | per job |

**Open buildability questions for Codex:**
- **Q-A1:** can a non-frozen 64-world bank be read without edits?
- **Q-A2:** can the course generator produce packets for new worlds with the frozen checker unchanged?
- **Q-A3:** can new tensors for B3 be seeded separately, so that the shared tensors match bitwise?
