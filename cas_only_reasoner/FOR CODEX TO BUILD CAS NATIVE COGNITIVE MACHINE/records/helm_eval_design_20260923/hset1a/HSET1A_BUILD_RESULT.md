# HSET-1A Stage 1 build result (2026-09-23)

**What this is.**
- These are the built Stage 1 test cells, with their bars (the best no-learning rule on each cell), sizes and power.
- **It is not a result about Helm.** No model was run on any cell.
- The claim-status words below come from the build program (`can_carry_a_claim`), not from this prose.

## The run

| Item | Value |
|---|---|
| Job | AWS `c7i.2xlarge` `i-0681fa3905a7bb0eb` (attempt 2; attempt 1 crashed on Claude's bug, see `../hset1a_aws_job/RUN_LOG.md`) |
| Time and cost | 30.1 minutes, at most **$0.1827** (attempts 1 and 2 together: at most $0.2050) |
| Code | bundle built from commit `6dcf035c`; builder LF sha256 `1e3d04fed3c27f8cd843087fb7c61a2c403e030cdba14c51aed95147803a5a9e` |
| Frozen checker | profile `2c95354e62994fb8a0c0ab56254d1527f5f4d2c79ea5ecbed5679de730bd8a81` (equals the historical anchor) |
| Bank | digest `0f563762a70e67513ca3e6996d988afd4421dd90fe63e1a04942a31a79e9c388` (equals the trained course's bank) |
| Salt | sha256 `33f9d350700470cc968597a525f1c50ae0598d11e99f8604463a730fe0909754` (committed before the build; not re-drawn) |
| First stage on the machine | both programs end to end at tiny size with a throwaway salt: passed |
| Outputs | `../hset1a_aws_job/results/`: `HSET1A_BUILD_SUMMARY.json`, `HSET1A_CELLS_PUBLIC.json`, `build.log` |

## The build is valid

- **Build verdict.** `build_ok: true`.
- **Size.** 3,370 packets in 1,685 clusters:
  - 1,844 public packets: FAMILIAR_RELABELLED 94, NEW_SHAPE_4 358, DEV_NEW_5 1,392;
  - 1,526 sealed packets: TEST_NEW_5.
- **Failure counters, all 0:**
  - errors;
  - packets without exactly one admissible answer;
  - disagreements between the frozen checker's gold and the independent rules;
  - checker scoring that differs from direct comparison;
  - failures of Helm's frozen reader;
  - duplicate records.
- **Helm can read every packet.** All of them pass Helm's own frozen input reader (`pointer_inputs.read_packet`).
- **Codex's checker v2 agrees on all of them.** It gives the same answer as the frozen gold on all 3,370 packets,
  including the 1,526 sealed ones (`d1_acceptance/D1_ACCEPTANCE_RESULT.md`, check X).

## The cells: none can carry a claim

"W" is the number of primary clusters the bar gets wrong. It is the only place a model can win. A pass needs at
least 7 wins with no loss, and the design's 10-cluster floor is applied to W.

| Cell | Primary clusters | W (bar wrong) | Bar | Bar accuracy | Can carry a claim |
|---|---|---|---|---|---|
| `DEV_NEW_5/EDGE_ACCOUNT` | 60 | 0 | `ONE_HOP_ALL_EDGES` | 1.000000 | no |
| `DEV_NEW_5/PARTS` | 76 | 0 | `ONE_HOP` | 1.000000 | no |
| `DEV_NEW_5/REACH_BFS` | 153 | 6 | `TWO_HOP_FIRST_CHILD` | 0.960784 | no |
| `DEV_NEW_5/REACH_FIRST_DIRECT` | 126 | 6 | `TWO_HOP_FIRST_CHILD` | 0.952381 | no |
| `FAMILIAR_RELABELLED/EDGE_ACCOUNT` | 6 | 0 | `ONE_HOP_ALL_EDGES` | 1.000000 | no |
| `FAMILIAR_RELABELLED/PARTS` | 7 | 0 | `ONE_HOP` | 1.000000 | no |
| `FAMILIAR_RELABELLED/REACH_BFS` | 9 | 1 | `TWO_HOP_FIRST_CHILD` | 0.888889 | no |
| `FAMILIAR_RELABELLED/REACH_FIRST_DIRECT` | 9 | 1 | `TWO_HOP_FIRST_CHILD` | 0.888889 | no |
| `NEW_SHAPE_4/EDGE_ACCOUNT` | 22 | 0 | `ONE_HOP_ALL_EDGES` | 1.000000 | no |
| `NEW_SHAPE_4/PARTS` | 25 | 0 | `ONE_HOP` | 1.000000 | no |
| `NEW_SHAPE_4/REACH_BFS` | 30 | 0 | `TWO_HOP_FIRST_CHILD` | 1.000000 | no |
| `NEW_SHAPE_4/REACH_FIRST_DIRECT` | 27 | 0 | `TWO_HOP_FIRST_CHILD` | 1.000000 | no |
| `TEST_NEW_5/EDGE_ACCOUNT` | 60 | 0 | `ONE_HOP_ALL_EDGES` | 1.000000 | no |
| `TEST_NEW_5/PARTS` | 83 | 0 | `ONE_HOP` | 1.000000 | no |
| `TEST_NEW_5/REACH_BFS` | 156 | 2 | `TWO_HOP_FIRST_CHILD` | 0.987179 | no |
| `TEST_NEW_5/REACH_FIRST_DIRECT` | 123 | 2 | `TWO_HOP_FIRST_CHILD` | 0.983740 | no |

**The primary claim cannot be tested.** The design's primary claim, `REACH_TRANSFERS_TO_NEW_STRUCTURE_5`, needed
`TEST_NEW_5` reach to beat the bar. On `TEST_NEW_5` the bar is wrong on 2 clusters in each reach cell. Even a
perfect model can win at most 2. So the claim **cannot be tested with these cells**, whatever model is run.

- The alternative cuts do not rescue it on TEST:
  - all non-tie clusters: 284 and 295, with W = 2 and 2;
  - VIA only: W = 1 and 2;
  - VIA 3 or more steps away: 2 and 2 clusters.
- DEV reach has W = 6 in both cells. That is below 7 as well.

## Why: at 5 nodes, two hops almost always suffice

`TWO_HOP_FIRST_CHILD` is right on every non-tie ABSENT, DIRECT and two-step VIA question. It fails only where the
path needs 3 or more steps.

Counted over **all 267 five-node shapes**, from the declared whole (a root), with each count independent of node
order:

| Rule | Non-tie VIA at 2 steps | at 3 steps | at 4 steps | Tie questions | All questions (ABSENT / DIRECT / VIA) |
|---|---|---|---|---|---|
| first-child | 181 | 26 | 1 | 99 | 277 / 714 / 307 |
| BFS | 217 | 27 | 1 | 62 | 277 / 714 / 307 |

- So only 27 (first-child) or 28 (BFS) questions in the whole 5-node universe can separate a learned multi-step
  rule from two hops.
- DEV drew 6 of them and TEST drew 2.
- Even a TEST made of every non-DEV five-node shape would hold at most 21 or 22.

## Other measured facts, printed for the owner

- **The second-best comparator is `DEGREE_RULE`**, at cluster accuracy 0.869919 (TEST, first-child) and 0.858974
  (TEST, BFS).
- **Ties.** Every tie cluster has a different gold in its two presentations: 26/26 and 15/15 on TEST, 23/23 on DEV.
  Ties stay outside the primary cells.
- **The trained course's answer states,** printed beside the cells: the BFS rule was only ever trained with VIA (59
  of 59). The first-child rule was trained with 30 DIRECT, 16 VIA and 2 ABSENT.
- **Flag hit rates on TEST primary VIA presentations,** first-child rule. The gold VIA node is:
  - the lowest-rank child in 0.658537;
  - the rank-last child in 0.646341;
  - participant 2 in 0.390244.

## What this does and does not show

- **It does not show** that Helm can or cannot transfer reach. No model was run.
- **It does show a limit of the test.** At 5 nodes, from a root, a reach question almost never needs more than
  two steps. So a no-learning two-hop rule already answers 95 to 99 percent of the balanced cells: 0.983740 and
  0.987179 on TEST, 0.952381 and 0.960784 on DEV. A reach-transfer
  claim needs questions whose paths are longer.

## For the owner's decision (design section 1.3; nothing is chosen here)

1. **Rebuild the reach cells at 6 and 7 nodes.**
   - The frozen checker scores reach at up to 10 nodes. Its isomorphism bound only matters for analogy and
     correspondence.
   - Helm's reader stays exact while every node's in-degree and out-degree is at most 4.
   - Longer paths are common there, so W can be large.
   - W is printed again before anything is read.
   - **Claude's recommendation.**
2. **Keep 5 nodes, and pool every non-DEV shape into TEST.** At most 21 or 22 winnable clusters, before
   balancing. That is borderline against the floor of 10 per run.
3. **Declare Stage 1 reach diagnostic only,** and rely on Stage 2 (analogy and correspondence at 5 or more nodes).
   Checker v2 is now accepted for Stage 2.

Parts and edge account stay diagnostic in every option. Their bar reads the answer straight off the input.
