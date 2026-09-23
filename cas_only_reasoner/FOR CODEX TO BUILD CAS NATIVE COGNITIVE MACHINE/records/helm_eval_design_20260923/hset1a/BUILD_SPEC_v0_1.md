# HSET-1A Stage 1 build specification v0.1 (written before the build ran)

**Owner of this file:** Claude (evaluation designer and sealed-test custodian).
**Implements:** `../EVALUATION_DESIGN_v0_2.md` section 1.
**Owner order:** "build the Stage 1 cells on aws" (chat, 2026-09-23).
**Status:** `BUILD_ONLY`.
- No model is run on any cell.
- No success rule is decided here. Section 1.3 of the design is still the owner's to sign.
- The printed bars, cluster counts and power are the input to that signature, not a result about Helm.

The design left some choices open. This file fixes them in writing before any number exists.

## 1. What each question looks like

| Choice | Fixed as | Why |
|---|---|---|
| Worked examples in a packet | **0 supports** | A packet may carry 0 or 3 (`course.py:318`). Supports come from other trained worlds, so 0 keeps the test about the focus world alone |
| Reach rules | **both rules, as two separate cells.** `REACH_FIRST_DIRECT` uses `first_direct_constituent_lexical_v1` with no cue. `REACH_BFS` uses `bfs_immediate_predecessor_lexical_v1` with cue `CUBE_FACE_5` | This is how the trained course asked them: `course.py:139` (no cue) and `course.py:123` (face 5). History had 48 and 59 such records |
| Parts | rule `direct_contains_v1`, no cue | as `course.py:137` |
| Edge account | cue `CUBE_FACE_6` | the only way the course asked it (`course.py:145`) |
| The whole in a reach or parts question | **the declared whole, which is a root** | every historical reach and parts question used the declared whole (`course.py:113,137,141`) |
| Words | only trained words: the 4 training domains' settings, 16 kinds each, node labels (56 to 60 per domain) and function templates | fresh words go through untrained byte tokens (review F5). They are read from the same pinned literals `source.training_families()` reads |
| Node labels | a random sample from the domain's labels, assigned to nodes at random | so rank order is uniformly random with respect to structure |
| Participants | [whole, then 2 other nodes drawn at random] | independent of the answer (design 1.1) |
| Presentations | 2 per question. The same world with the same label set, permuted so the rank order differs | design 1.2 |
| Degrees | every node's in-degree and out-degree is at most 4 | automatic at 5 nodes, and checked for every packet (D-1 spec S5) |

## 2. Units and cells

- **Clusters** are counted up to automorphism:
  - reach: (shape, whole, part);
  - parts: (shape, whole);
  - edge account: the shape.
- **One instance per cluster.** The domain is drawn from the 4 training domains, the kind from that domain's 16 kinds.
- **A comparator gets a cluster right** only if it is right on both presentations. A model is held to the same rule.

### 2.1 Tie questions (a change from v0.2, `PROPOSED` for the owner)

**A reach question is a TIE** when its gold answer changes under some ranking of the nodes. The build checks this
over all n! rankings.

- **Primary reach cell.** It uses **non-tie clusters only**, balanced ABSENT / DIRECT / VIA.
- **Ties** are a separate `TIE_STRATUM`, reported but never in the primary cell.
- **Why.** Helm 2.0's reader gives no node rank (`pointer_contract.py:896`, `node_rank_feature: False`). A tie's
  gold depends on the lexical rank. With 2 presentations at different ranks, a rank-blind model cannot be right on
  both except by the participant flags. The rank-using comparators get ties right for free. So ties measure
  access to rank, not structure.
- Non-tie clusters left over after balancing are reported as `SURPLUS_NON_TIE`.

### 2.2 Parts and edge account cannot carry a claim

For both kinds, a no-learning rule that simply reads the arrows gives the exact answer:
- for parts, the one-hop children;
- for edge account, all the edges.

So their bar is 1.0 by construction. These cells measure only whether Helm reads its own input. The build prints
this as `can_carry_a_claim: false`.

## 3. The comparators (no learning; read off the packet's own focus world)

**Reach.** "Direct" means the part is a child of the whole.

| Name | Rule |
|---|---|
| `CONSTANT_ABSENT` | always ABSENT |
| `CONSTANT_DIRECT` | always DIRECT |
| `ONE_HOP` | DIRECT if direct, else ABSENT |
| `LOWEST_RANK_CHILD` | DIRECT if direct, else VIA the whole's lowest-rank child, else ABSENT |
| `RANK_LAST_CHILD` | the same with the highest-rank child |
| `TWO_HOP_FIRST_CHILD` | DIRECT if direct, else VIA the lowest-rank child that has an arrow to the part, else ABSENT |
| `PARTICIPANT_2` | DIRECT if direct, else VIA participant 2 if the whole has any child, else ABSENT |
| `DEGREE_RULE` | DIRECT if direct; ABSENT if the part has no parent; else VIA the child with the most children (ties go to the lower rank) |

- **Bar.** The design's "degree multiset" comparator is a Stage 2 (analogy) rule. For reach, `DEGREE_RULE` is its
  counterpart.
- **Ceilings.** Exact search and the checker are ceilings, not bars.

**Parts.** `CONSTANT_EMPTY`, `ONE_HOP` (exact), `PARTICIPANTS_2_3`, `ALL_OTHERS`, `DESCENDANTS`.

**Edge account.** `ONE_HOP_ALL_EDGES` (exact), `STAR_FROM_DECLARED_WHOLE`, `RANK_CHAIN`, `PARTICIPANT_CHAIN`.

**How the bar is chosen.** The bar is the comparator with the best cluster accuracy on the cell's primary clusters.
A tie goes to the first in the table order. Every comparator's accuracy is printed.

**How comparators are scored.** Each is scored by the **frozen checker** (`check_answer`). The build also requires
that this agrees with a direct comparison to the gold answer.

## 4. Splits

| Split | Shapes | Instance seed |
|---|---|---|
| `FAMILIAR_RELABELLED` | the 6 bank shapes | the public string `HSET-1A-public-instances-v0.1` |
| `NEW_SHAPE_4` | the 3 new 3-node and 19 new 4-node shapes | the public string |
| `DEV_NEW_5` | 60 of the 267 five-node shapes | the sealed salt |
| `TEST_NEW_5` | 60 more, **secret** | the sealed salt |

- **Shapes.** They come from Claude's independent enumeration (`../d1_acceptance/oracle_isomorphism.py`). The build
  requires class counts of 4, 24 and 267.
- **Five-node strata.** The strata are (has a VIA question, edge count).
- **Quotas.** DEV and TEST get the same quota in every stratum. The quotas are proportional to stratum size by the
  largest remainder, and never more than half a stratum.
- **Order within a stratum.** sha256(salt, "split", shape): DEV takes the first quota, TEST the next.
- **Balancing within a reach cell.** It takes the first k clusters of each state, in keyed-hash order, where k is
  the size of the smallest state.

## 5. Custody

- **The salt.** It is 32 random bytes, made on the laptop. It is kept in
  `D:/tksCAS-archive/hset1a_sealed_20260923/`, outside every repository. Only its sha256 is committed:
  `33f9d350700470cc968597a525f1c50ae0598d11e99f8604463a730fe0909754` (the sha256 of its 64 hex characters). It is
  fixed here, before any cell exists.
- **The sealed file** `HSET1A_SEALED_TEST_NEW_5.json` goes to the same archive folder.
  - It holds the TEST shapes, worlds, answers and per-cluster comparator results.
  - The AWS watcher writes it straight there and never into a repository folder.
- **Public outputs** carry TEST numbers only as totals and digests:
  - the TEST shape-list digest;
  - the sealed file's sha256;
  - cell sizes, bars and power.

  Error texts from sealed items are cut down to their error type.
- **The honest limit.** Codex can technically read the same disk and the same AWS account. So custody here is a
  procedure, not a technical barrier. The design's label `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT` stands.

## 6. Checks that fail the build

A single failure in any of these fails the build:
- any packet fails the frozen packet validator, the frozen slot compiler or Helm's frozen reader
  (`pointer_inputs.read_packet`);
- the reader shows more than the focus world;
- the reader's whole or part rank is wrong;
- any node has a degree over 4;
- the frozen checker gives other than exactly one admissible answer;
- the frozen gold differs from the independent re-implementation of the rules (`hset_worlds.reach_gold` and the
  direct parts and edge rules);
- the checker's scoring of a comparator differs from direct comparison with the gold;
- the rebuilt bank differs from the trained course's bank;
- the frozen checker's profile digest differs from the historical anchor
  `2c95354e62994fb8a0c0ab56254d1527f5f4d2c79ea5ecbed5679de730bd8a81`.

## 7. Power (printed per cell)

- **The test.** The exact one-sided sign test over clusters at alpha 0.01, with no zero-loss veto.
- **Model accuracies used.** The bar plus 0.10, plus 0.20 and plus 0.30, and 1.0.
- **Stated assumption.** The model and the bar are right on each cluster independently.
- **Three runs.** The 3-run requirement is not folded in. If the runs were independent, it would cube each number.
- **Too small to claim.** A cell with fewer than 10 clusters is marked as unable to carry a claim.
