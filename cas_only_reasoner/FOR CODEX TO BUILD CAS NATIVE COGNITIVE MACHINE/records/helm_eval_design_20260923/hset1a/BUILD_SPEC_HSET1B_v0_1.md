# HSET-1B build specification v0.1: Stage 1 reach cells at 6 and 7 nodes (written before the build ran)

**The owner's decision, in chat, 2026-09-23.** "2. GO WITH YOUR RECOMMENDATION 6 AND 7 NODE". The record is
`_handoffs/HELM_NEXT_PHASE_20260923/OWNER_DECISIONS_TAKEOVER_20260923.md`.

**Why.** HSET-1A (`HSET1A_BUILD_RESULT.md`) showed that at 5 nodes the no-learning rule `TWO_HOP_FIRST_CHILD` is
wrong on only W=2 reach clusters of TEST. A pass needs at least 7. Across all 267 five-node shapes, only 27 or 28
non-tie reach questions need 3 or more steps.

**Status.** `BUILD_ONLY`. No model is run on any cell.

## What is unchanged

HSET-1B imports the reviewed HSET-1A builder (`hset1a_build.py`) and does not copy it. Everything in
`BUILD_SPEC_v0_1.md` sections 1 to 3 and 5 to 6a applies unchanged:
- worlds, packets with 0 supports, the cues and rules, whole = declared root, trained words (`declaration_labels`),
  and 2 presentations;
- the frozen-checker gold with the independent cross-check, and Helm's reader check;
- all comparators, clusters, ties outside the primary cell, and ABSENT / DIRECT / VIA balancing;
- W, conditional power and the alternative cuts;
- custody.

## What is new

| Item | HSET-1B |
|---|---|
| Node counts | 6 and 7 |
| Degrees | every node's in-degree and out-degree is at most 4. Helm's reader buckets degrees 0 to 4, so it stays exact. Proved for every shape at build |
| Shapes | the classes are too many to list (thousands at 6 nodes, far more at 7), so they are **sampled**. Each draw uses generator D or generator T with equal probability (see Sampler choice). It is kept only if acyclic, weakly connected and within the degree limit, then reduced to its canonical form (`oracle_isomorphism.canonical_form`, over all n! orders). Duplicate classes are skipped |
| Splits | `DEV_NEW_6`, `DEV_NEW_7` (public seed `HSET-1B-dev-shapes-v0.1`) and `TEST_NEW_6`, `TEST_NEW_7` (the new sealed salt), **40 shapes each** |
| Disjointness | no TEST class is isomorphic to a DEV class (canonical forms compared; asserted at build) |
| Strata | none are imposed. DEV and TEST come from the same sampler, but TEST skips the classes DEV already took, so it leans slightly toward rarer shapes (review finding 4). Both are printed (edge counts; structural reach counts by state, tie and distance) |
| Tie detection | as in HSET-1A: the gold answer set over **all** n! rankings (720 or 5,040) |

## Sampler choice, made before the build from structure only

**Why a choice was needed.** A first sampler with uniform edge density only (generator D) made mostly short paths.

**How it was measured.** A structural estimate on a separate **public tuning seed** (`HSET-1B-sampler-tuning`,
neither the DEV seed nor the salt), 200 shapes per node count, scaled to 40 shapes:
- non-tie VIA counted with a quick structural tie test;
- k = the smallest of the ABSENT, DIRECT and non-tie VIA counts;
- W is estimated as k times the share of non-tie VIA at 3 or more steps, where the two-hop bar fails.

No model and no TEST shape was involved.

| Sampler | 6 nodes, first-child | 6 nodes, BFS | 7 nodes, first-child | 7 nodes, BFS |
|---|---|---|---|---|
| D only (uniform density) | W about 6.0 | 6.0 | 11.0 | 10.2 |
| T only (deeper, tree-like, with extra roots) | 28.2 | 26.9 | 44.9 | 44.6 |
| **MIX, half D and half T (chosen)** | **22.4** | **23.0** | **41.0** | **44.6** |

The equal 44.6 for T-only and MIX at 7 nodes (BFS) is a coincidence of two different ratios: 115.4 x 57.4 / 148.6 and
137.2 x 44.6 / 137.2. The tuning script is committed as `tune_hset1b_sampler.py`. The pre-launch reviewer's own
estimate on the real public DEV draw, with exact balancing, was 23 and 22 at 6 nodes and 35 and 31 at 7 nodes: above
the floor, though below the tuning estimate at 7 nodes.

**Choice: MIX.** It keeps the variety of D and the depth of T. The expected W is above the floor of 10 in every
cell. These are estimates; the build prints the real W.

**Generator T.** It uses a random node order.
- Each new node hangs under an earlier node, with a bias toward recent ones to make depth.
- With probability 0.2 it instead becomes a new root pointing at an earlier node, so ABSENT questions exist.
- 0 to 2 extra forward edges are added.
- Draws with a cycle, a disconnection or any degree above 4 are rejected.

## The sealed salt, fixed before the build

- It is 32 random bytes, made on the laptop, and kept only in `D:/tksCAS-archive/hset1b_sealed_20260923/salt.hex`.
- Its sha256 is `b3cf84e2828e84a4a2d7a3215830ecd35f9f267d66ba2e560f8b6cc7c70d7f1e` (the sha256 of its 64 hex
  characters).
- It is never re-drawn to change W.

## The success rule, pinned before the build prints any W (review finding 2)

It is carried unchanged from `EVALUATION_DESIGN_v0_2.md` section 1.3, and is part of the recommendation the owner
accepted:
- **Per cell, per run.** `BEATS_NO_LEARNING_BAR` means the cluster sign test against that cell's measured bar:
  - b = clusters the model gets right and the bar gets wrong; c = the reverse;
  - pass iff b > c and the exact one-sided p(b, b + c) <= 1/100;
  - no zero-loss veto.
- **The claim `REACH_TRANSFERS_TO_NEW_STRUCTURE_67` needs all four TEST reach cells**, in each of the 3 runs:
  `TEST_NEW_6/REACH_FIRST_DIRECT`, `TEST_NEW_6/REACH_BFS`, `TEST_NEW_7/REACH_FIRST_DIRECT` and
  `TEST_NEW_7/REACH_BFS`. Requiring all four, not any one, avoids adding up four chances at 0.01.
- **A cell that reads `can_carry_a_claim: false`** (W below 10, or fewer than 10 clusters) makes the claim
  `NOT_TESTABLE`. The cell is never dropped to rescue the claim.
- The builder applies the floor of 10 to W.

## A rule for anyone who trains (review finding 5)

The salt hides which shapes are in TEST, not what shapes the sampler can make. In a check with throwaway salts,
5,000 draws from this sampler reproduced 34 of 40 TEST 6-node shapes and 20 to 27 of 40 TEST 7-node shapes.
- **No update and no development evaluation may use a 6- or 7-node shape outside `DEV_NEW_6` / `DEV_NEW_7`.**
- **Before any TEST reading,** the custodian checks the builder's digest-listed training and development manifest
  against the sealed canonical forms, by two isomorphism methods, and fails closed on any match.

## Checks that fail the build

These are HSET-1A section 6, plus two more:
- any shape exceeds the degree limit;
- any TEST class equals a DEV class.
