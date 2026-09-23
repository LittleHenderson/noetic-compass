# Prospective evaluation design v0.2: `PROPOSED_FOR_AGREEMENT`

**Supersedes** `EVALUATION_DESIGN_v0_1.md`, which is kept unchanged as the reviewed version. The review and every
disposition are in `REVIEW_20260923.md`.

**Owners.**
- Design and custody of the sealed test: Claude.
- Review of whether it can be built: Codex.
- Sign-off: the owner.

**Status.** No model has been run on anything here, and nothing here is a result.

## 0. What changed, in one paragraph

v0.1 would have certified the wrong thing:
- at 3-4 nodes, an arrow-counting rule already solves analogy and correspondence;
- a "take the first child" rule passes VIA-only reach;
- small test shapes cannot be kept secret;
- "80 items" were about 7 real questions.

v0.2 therefore does three things:
1. It separates what the **frozen** checker can score (**Stage 1**, buildable now) from what needs a **new
   checker version** (**Stage 2**, an owner decision).
2. It counts evidence in **structural clusters**, not relabelled copies.
3. It registers the rules that broke v0.1 as comparators.

## 1. Stage 1: buildable now on the frozen checker (`HSET-1A`)

**Kinds.** `reach`, `parts` and `edge_account` only. The frozen checker scores these at 5 nodes; its
isomorphism bound (`MAX_ISOMORPHISM_NODES = 4`) applies only to analogy and correspondence.

| Split | Worlds | What it measures | Claim-bearing? |
|---|---|---|---|
| `FAMILIAR_RELABELLED` | the 6 bank shapes, node ranks re-permuted at random | renamed copies | diagnostic |
| `NEW_SHAPE_4` | the 19 new 4-node shapes, plus 3 new 3-node shapes | new structure at a trained size | diagnostic: too few clusters (the review counted 14 non-tie VIA questions across all 22 shapes) |
| `NEW_SHAPE_5` | 5-node shapes: `DEV_NEW_5` = 60 shapes (builder may use), `TEST_NEW_5` = 60 shapes (**secret**), drawn from the 267 by a sealed salted hash, **stratified by VIA-capability and by edge count** | new structure at a new size | **primary for reach**, if it reaches at least 10 clusters per stratum (see 1.3) |

### 1.1 Generating worlds

- **Kept from training.** The domain, setting, kind and function strings stay within the trained
  vocabulary. The review showed that fresh words go through untrained byte tokens.
- **Node labels.** They are drawn so that the rank order they induce is **uniformly random with respect to
  structure**.
- **Participants.** The declared whole must be a root and comes first. The other two participants are drawn
  at random from the remaining nodes, independently of the answer.
- **Proved at build and printed for every cell:** the hit rate of each flag rule (participant-2, lowest-rank
  child, rank-last).

### 1.2 Reach cells

- **Composition.** Each cell is balanced ABSENT / DIRECT / VIA **by clusters**. ABSENT items include wholes
  that do have children, so a never-ABSENT policy is penalised.
- **Strata.** VIA is reported as a stratum, and so are **tie cases** (more than one qualifying intermediate,
  where the gold depends on the lexical tie-break).
- **Presentations.** Each question has 2 presentations, each a rank permutation by relabelling. A question is
  correct only if every presentation is correct. **Comparators are held to the same rule.**

### 1.3 Unit of analysis and success rule (`PROPOSED`, owner signs; read by a program)

- **Cluster.** A cluster is (shape, whole, part) up to automorphism. A model gets a cluster right only if every
  instance and every presentation in it is right.
- **Bar.** The bar for a cell is the best, on that cell, of these no-learning comparators:
  1. constant;
  2. rank-last;
  3. one-hop;
  4. lowest-rank child;
  5. two-hop via the first child;
  6. participant-2;
  7. degree multiset.

  Exact search and the reference checker are ceilings, not bars.
- **`BEATS_NO_LEARNING_BAR`** for a run on a cell: pair each cluster's model result with the bar's result. Let b
  = clusters the model gets right and the bar gets wrong, and c = the reverse. The run passes iff b > c and the
  exact one-sided p(b, b + c) <= 1/100. There is **no zero-loss veto**.
- **Primary claim (`REACH_TRANSFERS_TO_NEW_STRUCTURE_5`).** `NEW_SHAPE_5` on `TEST_NEW_5` reads
  `BEATS_NO_LEARNING_BAR` in all 3 runs.
- **Before the owner signs,** Claude builds the cells and prints for each: the effective n (clusters), the
  measured bar, and the power of this exact test at a stated effect size. **A cell with fewer than 10 clusters
  cannot carry a claim, and that is said before any run.**
- **Always printed as well:** the gain over each run's own untrained start. This is the historical view.

### 1.4 Custody (review S3, F5)

- **At 3-4 nodes** there is no secrecy. The shapes are public, so the evidence there is diagnostic.
- **At 5 nodes:**
  - `TEST_NEW_5`, its instances, its answers and the salt stay with Claude. Only digests are committed.
  - The builder receives the design, the generator code, `DEV_NEW_5` and the comparators.
- **The rule for the builder.** No update and no development evaluation may use a new shape outside `DEV_NEW`.
- **Commitment at evaluation.** The builder submits:
  - the checkpoint digest;
  - a digest-listed manifest of every world that any update or development evaluation touched.

  Claude checks every manifest world against `TEST_NEW_5` by two isomorphism methods, and fails closed on any
  match.
- **Scoring.** Claude runs the forward passes on the local GPU and scores them with the frozen checker, then
  publishes the inputs, answers, predictions and scores together.
- **The label** stays `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT` until an outside custodian repeats the
  scoring.

## 2. Stage 2: analogy and correspondence structure tests. Needs an owner decision.

- **Why Stage 1 is not enough.** At 3-4 nodes the degree rule answers analogy and correspondence almost
  exactly, so there they can only ever "match the degree rule". A structure test needs worlds that share node
  count, edge count and degree multiset but are **not** isomorphic. That happens only at 5 nodes or more
  (105 of 267 5-node classes collide).
- **The decision (D-1).** It requires a **new checker version** with a raised isomorphism bound. It is **not**
  the frozen checker and must never be called frozen. It needs:
  - its own name and profile digest;
  - a proof that it reproduces the frozen checker bit-for-bit on every existing record of 4 nodes or fewer;
  - a capacity table: a per-question evaluation bank of at most 64 worlds, with the frozen training bank and
    the evaluation bank named separately.
- **Its builder would be Codex, and its checker Claude.** It changes the answer path, so **it is the owner's
  decision (D-1)**.
- **If D-1 is approved,** the analogy and correspondence cells use:
  - degree-colliding decoys;
  - at least k same-size, same-edge-count, non-partner, non-training-shape decoys per item;
  - about 25% NO_MATCH, where NO_MATCH negatives have equal node and edge counts;
  - flag-matching and focus-blind comparators (the best fixed candidate ranking, and a candidate-only novelty
    rule).

**What follows for the analogy repair.** Until D-1 is decided, the repair can be checked for **wiring** (the
probe) and for **no regressions** (the historical panels). It **cannot** be checked for structural analogy
transfer. Stage 1 at 4 nodes can only show "matches the degree rule".

## 3. Experiments: each has one runner, and they are never pooled

| Id | Runner | Checker | What must hold before its numbers are read |
|---|---|---|---|
| `HSET-1A` (Stage 1) | Claude scores the sealed test; Codex supplies the model | Codex reviews buildability | cells built, bars and effective n printed, owner signs 1.3 |
| `HELM-ANALOGY-REPAIR-1` | Codex | Claude | probe v0.2 `PRESENT_GRAPH_AND_DOMAIN` on every trained switch-ON checkpoint that is read; switch OFF matches the preservation digests of `20208c92` bit for bit; declared shapes and migration record; matched starts, with reshaped tensors holding the old weights bitwise in their old part and the new part separately seeded |
| `HELM-REACH-LATE-1` | Codex | Claude | the 0.003 control branch reproduces the original endpoint (see 3.1) |
| `Q4-RECON-2` | Codex | Claude | the fixed familiar pool is reserved before any arm runs (see 3.2) |

### 3.1 `HELM-REACH-LATE-1`: details the review found missing

- **The query:** `typed-query-369885551a553d5fa430a4f0389a1e547fb4b7a6234e85d2c9aace042f4fd46f`.
- **The endpoint:** the final main-training checkpoint (`course_p10`).
- **The control.** Starting from the saved pass-1 checkpoint with its optimizer and RNG state, the 0.003
  branch must end with `VIA /n1` chosen in all 4 presentations. Its `VIA_N1` and `VIA_N3` scores must be within
  1e-3 of 26.474693298339844 and 22.808488845825195.
- **The settings:** deterministic algorithms and `CUBLAS_WORKSPACE_CONFIG` are on, and the GPU type is
  recorded.
- **Stop rule.** If the control does not reproduce, the experiment stops and the mismatch is the finding.

### 3.2 `Q4-RECON-2`: readouts, fixed before any arm

| Readout | Rows | Claim status |
|---|---|---|
| `TEACHING_FIT` | exactly the rows an arm updates on, with showings per row | diagnostic |
| `FAMILIAR_STRUCTURE_NEW_CONTENT` | a **fixed, digest-listed pool** of visible train-pool rows, stratified by bare shape. It is reserved before any arm and **excluded from every arm's teaching rows**. No row shares a leaf sequence with any teaching row | diagnostic; the same pool for every arm |
| `NEW_STRUCTURE_DEV` | the visible dev split (256 rows, depth 3, 9 bare shapes, 0 shared with the 16 train shapes). Rows containing atoms never seen in training are reported separately | `DEVELOPMENT_FEEDBACK_NOT_CLAIM_BEARING` |
| `NEW_STRUCTURE_SEALED` | the sealed eval split (depths 4-5) | the only transfer claim; used once, for a pre-registered arm |

- **Reported per readout:** exact canonical AST, bare-shape match, leaf-sequence match and per-token accuracy.
- **Comparators:** the most-common training tree, R0 (byte-bag nearest neighbour), leaf-copy into a training
  shape, and the deterministic parser (the ceiling).
- **No arm is presumed.** Longer training and a changed representation are separately named arms, never
  combined in one arm.
- **An arm chosen on `NEW_STRUCTURE_DEV`** must be confirmed on `NEW_STRUCTURE_SEALED` before any transfer
  statement.

## 4. To agree before any comparison is read

| Item | Proposed | Status |
|---|---|---|
| Starting source for the Helm experiments | `20208c923d41c24614504d4ecc2b289ecb66eda8` | PROPOSED |
| Stage 1 success rule (1.3) and minimum clusters | cluster sign test vs the measured bar; at least 10 clusters | PROPOSED, owner |
| **D-1: new checker version for Stage 2** | build it, or declare analogy and correspondence structure tests out of scope for now | **OPEN, owner** |
| Custody (1.4) | as written | PROPOSED |
| Probe and preservation rules | `PREREG_ANALOGY_WIRING_PROBE_v0_2.md` | FROZEN before any reading |
| This design's digest | the LF sha256 of this file at the commit that marks it `AGREED` | OPEN |

## Update 2026-09-23: D-1 APPROVED by the owner

**The owner's words:** "D-1 approved: build the new checker version". The transcription is recorded in
`_handoffs/HELM_NEXT_PHASE_20260923/OWNER_DECISION_D1_20260923.md`.

- **Builder:** Codex.
- **Independent checker:** Claude.
- **Specification and acceptance tests A1-A6:** `_handoffs/HELM_NEXT_PHASE_20260923/D1_CHECKER_V2_SPEC_AND_ACCEPTANCE.md`.
- **Claude's independent tools:** `d1_acceptance/`.

Stage 2 cells may be built only after checker v2 passes A1-A6. They may be read only after section 1.3 is
signed. The row "D-1" in section 4 now reads **APPROVED**; the table itself is left as written.
