# HSET-2 builder report (`CLAUDE_BUILT_CLAUDE_CHECKED`)

**Who.** Claude, temporary builder while Codex is away. I wrote this code and I checked it myself. No independent
reviewer has read it yet. The design requires a fresh review before any paid run (design s9 step 1).

**What this is.** The build code for HSET-2, the improved Helm test, as `../EVALUATION_DESIGN_v0_4.md` with its
Amendment A1 (`d840ea02`) says. It is code plus committed PUBLIC stage-0 files.

**What this is not.**
- No model was loaded, trained or run. Nothing here is a result about Helm.
- The sealed build has NOT run. No real salt was used. No sealed file exists.
- Every number below comes from THROWAWAY salts (derived from public strings) or from the public stage 0.

**Status words.** `BUILD_ONLY`. The claim-status words (`NOT_TESTABLE`, `can_carry_a_claim`) come from the build program,
not from this prose.

## 1. Files

LF sha256 of each file at the commit that adds this report. Paths are under
`records/helm_eval_design_20260923/`.

| File | LF sha256 | What it is |
|---|---|---|
| `hset2/hset2_stage0_public.py` | `f2636a9e11f66eb5e2bcc0e26a63fe384102ad50ea1f07908d74acad953eb500` | Stage 0 (public): PUBLIC_EXCLUDED, the 6-node enumeration, the group split, DEV_NEW_6, DEV_DECOYS_6 |
| `hset2/PUBLIC_EXCLUDED_v1.json` | `f101cbdd2984e5bcd21389f8ed76ef4550bc3817735c65f0acb8c8afc6d23b98` | Every 5- or 6-node class in the fixture file, by canonical-form digest |
| `hset2/STAGE0_DEV_SIDE_GROUPS.json` | `6b7b6f812af325b3820a7a729aaa50576fa8ec2c9082ae25e713e5b2016f29cc` | The DEV-side degree groups and their classes |
| `hset2/STAGE0_TEST_SIDE_GROUPS.json` | `348d262cc76f20a351174be687f6bf19a4843f986d9d7135446270a757e9be92` | The TEST-side degree groups and their classes (the forbidden set; public by design) |
| `hset2/STAGE0_SUMMARY.json` | `ae2097236a6446aeef592056622b85639542b5cbfb8caff9d749897fefc3ad8c` | Counts, digests, DEV_NEW_6 in draw order, DEV_DECOYS_6, the file hashes of the three lists |
| `hset2/hset2_build.py` | `e8542a3ca04ee242348c92e8483bd65b7001557f83fc08d9d735631fb1e36246` | The sealed stage. Run ONLY on AWS by the coordinator with the real salts |
| `hset2/test_hset2.py` | `12367fcf8f1287db1ea5957d1e015bfcb335005dadfcadc0a21810c3a2303bbd` | Tests (throwaway salts only) |
| `hset2/conftest.py` | `c7df5d551efbf525d36ec5dafafefcd86aead06b09fff4ba4ae845e5fd7f5662` | Registers the `e2e` test marker |
| `hset2/hset2_throwaway_ranges.py` | `c3a6bf77cd9f85da867e87b98024f9bf59cccf4599f9cf74341c646cee977933` | Expected ranges over throwaway salts, with the builder's own code (section 5) |
| `hset2_aws_job/launch.py` | `080dc69c53cbde4ed0dac5fcc34cf5556b22c6bf3f6b318565d878315433a815` | The launcher (not run). Also `--materialize-tree` for local tests |
| `hset2_aws_job/job.sh.template` | `18abfef0127f367d6888b66372a79c89081232d3f648f8118164a7647a6cc4e6` | The machine script |
| `hset2_aws_job/watch.py` | `42571a7eb8d35baff68c168a09b21f981346628418df0ca2acd084ed50a3607c` | The watcher; sealed results go straight to the archive |
| `hset2_aws_job/JOB_LIMITS.md` | `8693532fda0658062b1238a5fd462df1d36f186874431adcb31096f2aa79b242` | Limits, cost arithmetic, the coordinator's steps before launch |

**Reused by import, not copied:** `hset1a/hset_worlds.py`, `hset1a/hset1a_build.py` (`split_five`, `shape_facts`,
`build_items`, `_comparators`, `_independent_gold`, `summarise_cell`, `cut_stats`, `power_given_bar`, `sign_p`),
`hset1a/hset1b_build.py` (`sample_class`, `draw`), `d1_acceptance/oracle_isomorphism.py` (`canonical_form`,
`dag_classes`, `all_isomorphisms_m2`). The only copy-like code is `world_pair` in `hset2_build.py`: it mirrors
`hset1a_build.instance_specs` but takes the domain as an argument, because a bank needs worlds of chosen domains.

**Pinned source for the AWS bundle.** Commit `785c9bd10f1416deb95f9c30aacb43124134fe45` on
`claude/helm-builder-continuation-20260923`. At that commit:
- `checker_v2.py`, `answers_v2.py` and `slots_v2.py` have the D-1 accepted LF sha256 (`d24d8276...`, `b0bdabfc...`,
  `7b9c2c3a...`). Every other typed-teaching file the build calls has the pin that `larger_question_scope.py` checks.
- The branch tip `cc68d8b3` changes only review documents after that commit.
- The launcher records the sha256 (raw and LF) of every bundled file in `anchors.json`, and the machine checks them all
  before anything runs.

## 2. What each test covers

Run as two groups, one at a time, each under 3 minutes on the laptop:
`python -B -m pytest -p no:cacheprovider -q test_hset2.py -m "not e2e"` and `... -m e2e`.
The world-building tests need the pinned tree, written by `launch.py --materialize-tree DIR` outside the repository and
passed as `HSET2_PACKAGE_ROOT`.

**Local results: 17 of 17 passed (13.43 s), and 2 of 2 end-to-end passed (161.13 s, on a busy laptop).**

| Test | What it proves |
|---|---|
| `test_group_key_is_pinned_spelling` | The group key is `hset_worlds.canon([6, [[in, out], ...]])`, byte for byte (A1 D1) |
| `test_side_rule_bytes` | DEV iff the first byte of sha256(`HSET-2-group-side-v0.1:` + key) is below 64 |
| `test_enumeration_matches_oracle_at_5_nodes` | The fast enumerator gives exactly the oracle's 267 classes at 5 nodes |
| `test_stage0_committed_outputs_reproduce_and_are_consistent` | Stage 0 recomputed equals the committed files; 5,074 classes; 503/1,324 and 1,434/3,747; whole groups on one side; DEV_NEW_6 on the DEV side and reproduced; DEV_DECOYS_6 = the rest of the DEV side |
| `test_split_five_throwaway_and_withheld_rule` | `split_five` gives two disjoint sets of 60; WITHHELD_5 is exactly the rest minus PUBLIC_EXCLUDED; a wrong WITHHELD_5 fails; a TEST_NEW_5 holding a PUBLIC_EXCLUDED class fails with `CUSTODY_BREACH` |
| `test_public_excluded_version_1` | 7 classes (3 at 5 nodes, 4 at 6 nodes): S5A, S5B, S5C, S6A, S6B, S6D, S6STAR; digests; oracle forms; S6STAR marked outside the degree-4 universe |
| `test_three_hop_first_child_rules` | THREE_HOP_FIRST_CHILD on hand-made chains and forks, both rules |
| `test_reach_comparators_hand_made` | All 9 reach comparators and both gold rules on one hand-made world |
| `test_correspondence_comparators` | All 5 correspondence comparators on hand-made pairs: a valid guess, a broken guess rescued by the flag anchor, and same-degree non-isomorphic pairs where every check fails |
| `test_analogy_comparators` | All 9 analogy comparators on a hand-made bank, including the tuned parameters and the trained-shape rule |
| `test_cluster_counting_and_tuned_choice` | A cluster is right only if all 4 rows are right; tuned comparators take their best value on the cell |
| `test_floor` | `can_carry_a_claim` is false for clusters < 10, binding W < 10, or (analogy) groups < 10; the smallest detectable regression is 7 |
| `test_fresh_flags_kind_words_and_presentations` | Every world draws a root whole, two other participants, a kind word of its domain and trained labels; the two presentations differ; a partner's flags land on an image of the focus's flags in well under half of 200 draws |
| `test_twin_banks_profile_equality` | Twins share every class and domain but position 1; profiles equal; 3 and 4 same-degree other-domain decoys; the distractor is in both twins or neither; a tampered twin changes the profile |
| `test_trained_answer_states_pinned_record` | The pinned trained states: analogy 70 MATCH, correspondence 88 MAPPING, reach as HSET-1A recorded |
| `test_real_mode_refusals` | Real mode refuses while `HSET2_SALT_SHA256` is uncommitted; throwaway mode refuses salt files; a sealed folder inside a git work tree is refused |
| `test_launcher_limits_and_pins` | Worst case $0.6070 < $1.00; the launcher reads the salt pins from the committed builder; every bundled file exists; the machine script has every placeholder, the stage-0 check and the smoke stage |
| `test_tiny_end_to_end` (e2e) | `hset2_build.py` end to end with throwaway salts and 1 focus per split: `build_ok`, all 5 question kinds, every sealed packet read by Helm's reader on the LARGER route, gold equal to the independent rules, checker v2 equal to direct comparison |
| `test_public_outputs_hold_no_test_id_or_shape` (e2e) | No TEST or WITHHELD class key, hashed shape id, record id, query id, source digest, packet hash, cluster id, item id or world id appears in any public output byte; DEV items hold only DEV-side (or DEV_NEW_5) classes |

**Also checked by hand, once:**
- `pyflakes` is clean on all 7 Python files.
- The rendered machine script passes `bash -n`.
- The fast path of section 5 gives the same comparator verdicts as the real builder's checker-v2 grading on
  **224 of 224** items (68 reach, 8 parts, 8 edge account, 60 analogy, 80 correspondence), on three throwaway runs.
- The frozen-checker measurement of the trained states ran once (158 targets, 107.9 s): analogy 70 MATCH,
  correspondence 88 MAPPING. That is the pinned record. NO_MATCH was never trained for either kind (review m4).
- **Not run locally:** the process-pool path (`--processes` above 1). The laptop had under 1.1 GB free. The AWS smoke
  stage runs it with 2 processes before the real build.

## 3. Stage 0 (public, run locally, committed)

| Item | Value | The delta review expected |
|---|---|---|
| PUBLIC_EXCLUDED v1 | 7 classes: 3 at 5 nodes, 4 at 6 nodes. S6STAR has out-degree 5, so it is outside the degree-4 universe; 3 six-node classes are inside it | 7 (3 + 4) |
| Every 6-node class (acyclic, weakly connected, degrees at most 4) | **5,074** | 5,074 |
| After PUBLIC_EXCLUDED | 5,071 classes in 1,937 degree groups | 5,071; 1,937 |
| DEV side | **503 groups, 1,324 classes** (81 groups of 5 or more; 233 of 2 or more) | 503 / 1,324; 81 |
| TEST side | **1,434 groups, 3,747 classes** (221 groups of 5 or more; 625 of 2 or more) | 1,434 / 3,747; 221 |
| DEV_NEW_6 | 60 foci in **253** sampler draws | 253 |
| DEV_DECOYS_6 | 1,264 classes | the rest of the DEV side |
| DEV foci usable for analogy (at least 4 same-group DEV-side partners) | **27**, in 18 degree groups | 27, 18 |
| DEV foci usable for correspondence (at least 1 partner) | **52**, in 35 degree groups | 52 |

**Digests** (content digests are `hset_worlds.sha` of the list):
- DEV-side groups `29349b328b8150719c9f5cc03f65fae43602cc9476e9362c6e388028c84d35de`.
- TEST-side groups `aadefc33892428293b9d56d204e97b7f585ce57291de3027959f3058c179d7a5`.
- PUBLIC_EXCLUDED class digests `afa70ca607c3498fdfeff14f850fc15b369f64843b32c47ceac96fdf4beee27f`.
- DEV_NEW_6 `e1c046a464e794873ccfd7d64344cdc418a5bd4121d6deefa49261ed96cdf682`.
- DEV_DECOYS_6 `7d3b68e489b7e97ddd2e109b27a9f4960579356d4a7e5e93a73e3d2c1cb8ce85`.
- All 5,074 classes `5efdb71e8cc7d6d638d6ce57d5c16e02efb8a9b415ac8f9ff7858f680fbd7472`.

**A custody fact for the owner (printed, not acted on).** The 40 public HSET-1B DEV_NEW_6 classes (public seed
`HSET-1B-dev-shapes-v0.1`) fall **16 on the DEV side and 24 on the TEST side**. None is in PUBLIC_EXCLUDED v1. See open
question 5.

## 4. What the sealed build does (short)

- **5 nodes.** TEST_NEW_5 by `split_five` with the HSET-1A salt. It must reproduce HSET-1A's public
  `test_shapes_digest`. It must hold no PUBLIC_EXCLUDED class. WITHHELD_5 is the rest, asserted.
- **6 nodes.** Stage 0 recomputed and required byte-identical to the committed files. TEST_NEW_6 = 60 TEST-side foci
  from the MIX sampler with the HSET-2 salt. WITHHELD_6 is the rest of the TEST side.
- **Cells.**

  | Cell | Clusters | Role |
  |---|---|---|
  | `TEST_NEW_6/REACH_FIRST_DIRECT`, `TEST_NEW_6/REACH_BFS` | (shape, whole, part) up to automorphism, balanced, ties outside | claims `REACH_3_STEP_TRANSFER_6`, `REACH_4_STEP_TRANSFER_6` |
  | `TEST_NEW_6/ANALOGY` | the focus class (2 twin items x 2 presentations) | `ANALOGY_BEYOND_DEGREE_6` |
  | `TEST_NEW_6/CORRESPONDENCE` | the focus class (MAPPING + NO_MATCH x 2 presentations) | `CORRESPONDENCE_BEYOND_DEGREE_6` |
  | `TEST_NEW_5/CORRESPONDENCE` | the focus class; foci widened per A1 D2 | `CORRESPONDENCE_BEYOND_DEGREE_5` |
  | `TEST_NEW_6/PARTS`, `/EDGE_ACCOUNT` | as HSET-1A | diagnostic |
  | `DEV_NEW_6/*` (all of the above), `DEV_NEW_5/CORRESPONDENCE`, `DEV_NEW_5/ANALOGY_RELAXED` | same | development feedback |

- **Every packet.** The frozen packet validator; the larger-question route must be LARGER; slots v2; Helm's reader
  (`pointer_inputs.read_packet`) with its record, world count, target and ranks checked; checker v2's gold; an
  independent gold (the reach rules re-implemented; the oracle's canonical form for analogy; the oracle's method-M2
  isomorphism list for correspondence, which must equal checker v2's whole admissible set); every comparator graded by
  checker v2 and by direct comparison, which must agree.
- **Printed before any model is read, per cell:** clusters; W for every comparator; the binding W and its comparator;
  distinct degree groups (and behind W); distinct shapes behind W; the power grid (bar +0.10, +0.20, +0.30, 1.0;
  never-loses 0.5, 0.75, 1.0) for the binding comparator; trained answer states; flag-image rates per status; partner
  and target alias positions; the distractor split (A1 D5); the printed diagnostics (longest path, reachable pairs,
  node signatures, 1-round and full colour refinement); `can_carry_a_claim` from the floor. Also: the claims table, the
  no-regression gate set with the pinned `evaluate_gates.py` and the smallest detectable regression (7), the
  family-wise risk, split disjointness, and the collision share (printed, never required).
- **Custody.** TEST and WITHHELD lists, items, answers and cluster tables go only to the sealed file. The sealed
  folder must not be inside a git work tree. Public files hold TEST numbers only as totals and list digests.
- **To rebuild one sealed packet later:** `hset2_build._init(root)`, then `hset2_build.build_packet(item)`.

## 5. Throwaway-salt numbers against the review's expected ranges

**How they were made.**
- `hset2_throwaway_ranges.py` runs the builder's own `load_stage0` and `derive` (the same splits, eligibility and
  items), the builder's own comparator functions and cell summaries. It skips packet validation, the reader and
  checker v2, and compares each comparator directly with the independent gold.
- The real build requires checker v2 to agree with exactly that direct comparison on every packet. On 224 items the
  two paths agreed on every verdict (section 2).
- Seeds: `tiny-9` to `tiny-19` without `tiny-13` (10 seeds; each gives a throwaway HSET-1A-side and HSET-2 salt). The
  5-node focus count also used 300 seeds. Reach also used the reviewer's own 10 six-node salt strings and 10 more seeds.
- min / mean / max over seeds.

| Number | This build (throwaway) | The delta review |
|---|---|---|
| TEST_NEW_6 sampler draws | 92 / 108.8 / 125 | 101 to 130 |
| Analogy-eligible TEST foci | 21 / 24.3 / 28 | 20 / 24.5 / 32 |
| ... their degree groups | 15 / 17.6 / 20 | 14 / 18.3 / 27 |
| Analogy binding W | 20 / 23.4 / 27 (`FLAG_ANCHOR`; every other comparator is wrong on every cluster) | about foci minus 1 |
| Analogy `can_carry_a_claim` | 10 of 10 | floors met 10 of 10 |
| Analogy, distractor half / other half: binding W | 9 / 11.2 / 13 and 11 / 12.2 / 14 | (new print, A1 D5) |
| Correspondence-6 foci | 43 / 46.7 / 50 | 45 to 53 (mean 47.9) |
| Correspondence-6 binding W | 19 / 29.0 / 33 (`DEGREE_GUESS_THEN_CHECK`) | 21 / 28.5 / 34 |
| Correspondence-6 `FLAG_ANCHOR_GUESS_THEN_CHECK` W | 42 to 49 | 43 to 52 |
| Correspondence-5 (widened) foci | 69 / 74.0 / 83 | 58 to 81 (mean 71.77) |
| ... over 300 seeds | 58 / 71.54 / 83 (the reviewer's salt strings: 58 / 71.30 / 85) | 58 to 81 |
| ... degree groups | 26 / 28.6 / 33 | 21 to 33 |
| Correspondence-5 binding W | 14 / 21.0 / 26 | 12 / 20.71 / 33 |
| Correspondence-5 `can_carry_a_claim` | 10 of 10 | 300 of 300 |
| Reach first-child, primary clusters per state (k) | 95 / 109.9 / 122 | 96 to 126 |
| Reach BFS, k | 102 / 121.8 / 138 | 111 to 135 |
| Reach 3-step binding W (two-hop), first-child | 26 / 33.1 / 40 | 22 / 31.1 / 41 |
| Reach 3-step binding W, BFS | 26 / 34.7 / 43 | 25 / 32.8 / 44 |
| ... distinct shapes behind W | 18 to 25 and 19 to 28 | 17 to 26 |
| Reach 4-step binding W (three-hop), first-child / BFS | 2 / 7.6 / 11 and 2 / 7.9 / 12 | 2 / 6.1 / 9 and 2 / 6.2 / 9 |
| Reach 4-step: both cells W >= 10 | **3 of 10** seeds (`tiny-10`, `tiny-12`, `tiny-16`) | 0 of 10 |

**The reviewer's own ten 6-node TEST salts** (`sha256("reviewer-throwaway6-v04-<i>")`, i = 0 to 9), run through this
builder: k 96 to 126 and 111 to 135; 3-step W 22 / 31.1 / 41 and 25 / 32.7 / 43; 4-step W 2 / 6.1 / 9 and
2 / 6.2 / 9. These match the review almost exactly (one BFS salt differs by 1). Ten more seeds (`reach-0` to `reach-9`):
4-step W 4 to 8, never 10. **In all, `REACH_4_STEP_TRANSFER_6` could carry a claim in 3 of 30 throwaway salts.** The
owner was told it "will almost surely read NOT_TESTABLE". That is still the likely reading, but not a certainty.

**Why the 5-node maximum differs (83 or 85 against 81).** `split_five` orders classes by a salted hash of the class key.
The reviewer used their own canonical form, so their keys, and therefore their splits, differ from the build's for the
same salt. The min (58) and the mean (71.3 to 71.8) agree; the tail differs by chance.

**Printed diagnostics (never bars).** On TEST analogy focus-versus-decoy pairs (972 over 10 seeds): 1-round colour
refinement separates 971, full refinement 972, longest path 499, reachable pairs 731, node signatures 961. On
correspondence-6 NO_MATCH pairs (467): 466, 467, 207, 352, 460. Full refinement separates every pair, as the review said.

**Flag-image rates (fresh flags, M2).** The partner's whole and both participants land on an image of the focus's in
0.0 / 0.04 / 0.087 of MATCH items; the MAPPING target's in 0.0 / 0.03 / 0.045 (6 nodes).

**DEV (public; the same in every seed).** Analogy: 27 foci, 18 groups, binding W 26. Correspondence-6: 52 foci,
35 groups, W 32. Reach first-child: k 119, 3-step W 32, 4-step W 4. Reach BFS: k 125, W 33 and 5.
DEV_NEW_5 correspondence: 5 to 14 foci, W 0 to 4 (feedback only). DEV_NEW_5 relaxed analogy: 60 foci, but degree
matching solves it (binding W 0 to 2). That is expected for the relaxed recipe, which is feedback only.

## 6. Runtime and cost on AWS

- **Size.** About 5,300 to 5,540 packets (two throwaway seeds: 5,538 and 5,286). About 3,540 to 3,740 reach, 380
  parts, 240 edge account, 430 to 450 analogy, about 710 correspondence.
- **Measured per packet** on the laptop, one process: reach, parts and edge account about 0.6 s (almost all of it is the
  frozen validator re-checking the 65-world source); analogy about 0.47 s; correspondence about 0.1 s.
- **Estimate.** About 2,900 CPU-seconds, so about 6 to 8 minutes on 8 vCPU. With setup, the stage-0 check, the smoke
  stage, start-up and the trained-state re-measurement: **about 15 to 20 minutes, about $0.09 to $0.12.**
- **Bounds.** In-machine timer 90 minutes; client deadline 100 minutes; worst case **$0.6070**; ceiling $1.00
  (`../hset2_aws_job/JOB_LIMITS.md` shows the arithmetic).
- **Output size.** By the tiny runs, about 8 KB per item: the sealed file about 20 MB, the public cells file about
  10 to 20 MB.

## 7. Choices where the design is silent (the simplest reading, written down)

1. **PUBLIC_EXCLUDED v1** lists every 5- or 6-node class in the fixture file's shape table and in every world it builds,
   including S6STAR (degree 5, outside this test's universe). Each is re-derived with the oracle and checked against
   the file's own canonical form.
2. **Canonical form and class key** are the D-1 oracle's method M1 and HSET-1A's key, so sampler draws and the
   enumeration agree. The enumeration reduces each edge set on a topological numbering; it matched the oracle at 5
   nodes and gave 5,074 at 6.
3. **Samplers.** DEV: `Random(keyed_int("HSET-2-dev-shapes-v0.1", "dev", 6))`, as the review ran it. TEST:
   `Random(keyed_int(salt, "test", 6))`, as HSET-1B.
4. **THREE_HOP_FIRST_CHILD.** First-child rule: VIA the lowest-rank child with a path of at most 2 steps to the part.
   BFS rule: the two-hop answer if there is one, else VIA the first node 2 steps away (BFS order, neighbours by rank)
   with an arrow to the part. It is two-hop one step deeper, never weaker. On the reviewer's salts it gives their W.
5. **Analogy comparators.** Candidates are the bank worlds other than the focus, in alias order. The count, degree,
   flag and novelty rules also require another domain (the instruction states the domain rule). `FLAG_ANCHOR`
   compares the (in, out) degrees of whole, participant 2 and participant 3, in order, and answers NO_MATCH if none
   fits. `CANDIDATE_ONLY_NOVELTY` = the first other-domain candidate of the focus's node count whose class is not a
   trained shape. `BEST_FIXED_POSITION` = always W_k, k chosen best on the cell. `STATUS_BY_COUNT` = NO_MATCH if fewer
   than m same-degree other-domain candidates, else the first of them; m in 0 to 8 chosen best on the cell. Ties go
   to the smaller parameter.
6. **Correspondence comparators.** Degree sort key (in-degree, out-degree, rank). `IDENTITY_BY_RANK` maps N_i to N_i.
   `FLAG_ANCHOR_GUESS_THEN_CHECK` maps whole to whole, participant 2 to 2 and 3 to 3, then sorts the rest by degree.
7. **Twins.** Both twins share every class and every domain except position 1 (partner against the 4th decoy). Flags,
   kind words and labels are drawn fresh for each item (design s4, "each item draws fresh"). The focus domain is
   drawn once per focus; partner and decoy domains uniformly from the other 3; filler domains uniformly from all 4.
8. **Exactly half with the distractor.** The first floor(n/2) eligible foci in salted-hash order.
9. **Pools.** TEST decoys come from the focus's degree group on the TEST side. DEV decoys come from the focus's group on
   the whole DEV side (DEV_NEW_6 and DEV_DECOYS_6). Fillers follow A1 D3.
10. **Correspondence target domain** is drawn uniformly from the 3 other domains, in both statuses. The NO_MATCH class
    is drawn from the focus's group on the same side.
11. **Salts.** The HSET-1A salt is used only for `split_five`. Every new HSET-2 TEST draw, including the 5-node
    correspondence items, uses the HSET-2 salt. DEV items use the public DEV seed.
12. **Reach packets** carry the frozen 64-world training bank unchanged, as HSET-1A and HSET-1B did. Only the focus is
    relabelled between presentations; Helm's reader reads only the focus for reach.
13. **Reach cells** show two floors, one per claim. The cell-level `can_carry_a_claim` is the 3-step one. A cell joins
    the gate set V if any of its claims can carry.
14. **Trained answer states.** Analogy and correspondence are pinned from one frozen-checker measurement and
    re-measured by the sealed build (fail closed). Reach reuses HSET-1A's record.
15. **Flag-image rate** = whether one automorphism maps the focus's whole and both participants onto the other world's
    (also printed for the whole alone).
16. **Printed diagnostics** use focus-versus-decoy class pairs: 4 per analogy focus, 1 per correspondence focus.
17. **The power grid** is printed for the binding comparator. Passing it is necessary, not sufficient.
18. **Extra DEV cell.** `DEV_NEW_5/CORRESPONDENCE` (feedback only) mirrors the secondary claim. The design does not
    name it.
19. **Not rebuilt.** TEST_NEW_5 parts and edge account (HSET-1A has them) and any TEST 5-node analogy (declared
    `NOT_TESTABLE`).

## 8. Open questions

1. **The HSET-2 salt** is not made and its sha256 is not committed. The build and the launcher refuse until the
   coordinator commits `HSET2_SALT_SHA256` (design s3 step 6).
2. **`EXPECTED_TEST5_SHAPES_DIGEST`** must be copied from HSET-1A's public build summary. I did not open that
   `results/` folder (standing rule), so the launcher refuses until it is set.
3. **The archive folder date** is `D:/tksCAS-archive/hset2_sealed_20260924/`. Change `ARCHIVE_HSET2` if another date is
   wanted.
4. **`REACH_4_STEP_TRANSFER_6`** could carry a claim in 3 of 30 throwaway salts (section 5). Should the owner hear that
   the earlier "almost surely NOT_TESTABLE" is about 90 percent, not 100?
5. **HSET-1B's 40 public DEV_NEW_6 classes: 24 are on HSET-2's TEST side.** If any was ever used with a trained model or
   a candidate bank, it must join PUBLIC_EXCLUDED **before** the sealed stage. That would change the committed stage-0
   files, so it must be decided now.
6. **The twin reading.** I drew flags, kind words and labels fresh per item, so the NO_MATCH twin is a fresh draw of the
   same classes and domains. The other reading (identical worlds except position 1) is also defensible.
7. **The widened 5-node cell** keeps the design's name `TEST_NEW_5/CORRESPONDENCE`, although its foci include
   WITHHELD_5 classes (A1 D2).
8. **The extra DEV cell** `DEV_NEW_5/CORRESPONDENCE`: keep or drop?
9. **A fresh independent review** of `hset2_build.py` is still required before any paid run (design s9 step 1). This
   build is `CLAUDE_BUILT_CLAUDE_CHECKED`.
10. **Not updated:** the repository `CHANGELOG.md` and `docs/CAS_HARNESS_SPEC_SHEET.md` are outside this sparse checkout.
    The coordinator decides whether they need a line.

## EXPOSURE (every file outside my working copy that I opened)

**Read through `git show` / `git cat-file` from `claude/helm-builder-continuation-20260923`** (commits `cc68d8b3` and
`785c9bd1`):
- in full: `typed_teaching/checker_v2.py`, `answers_v2.py`, `slots_v2.py`, `source.py`, `answers.py`, `course.py`,
  `pointer_inputs.py`; `eval_paths/larger_question_scope.py`, `larger_question_learner.py`, `__init__.py`;
- in part: `larger_question_fixtures.py` (lines 1 to 200); `pointer_contract.py` (grep, and lines 395 to 470);
  `practice_contract.py` and `matched_contract.py` (grep hits and nearby lines);
- `eval_paths/fixtures/larger_question_fixtures_v0_1.json`: its sha256, top-level keys, the shape table, one world and
  one fixture's keys; the stage-0 program parses all of it.
- Git metadata only: `git log`, `git ls-tree` (names and sizes), `git diff --stat`, `git merge-base`.

**The materialized tree** `785c9bd1` (1,186 files written from git objects into my session scratchpad, outside every
repository): the build and tests import code from it and load `public_course.json`, the tokenizer and the development
material through the frozen loaders. I read `public_course.json` directly once, to count registry records by kind
(counts only). The tree also holds `records/typed_course_001/checks_002/private_targets.json` (the course's own
training targets); neither I nor my programs opened it.

**My own throwaway outputs** in the scratchpad (public and `sealed_throwaway` files made with throwaway salts only).

**Not opened:** any `*_eval.jsonl`; any file or folder named sealed except my own throwaway outputs; anything under
`D:/tksCAS-archive/`; any `salt.hex`; S3 or AWS; the meta1 budget ledger; any `results/` or `results_attempt1/`
folder; Claude transcripts. A directory listing of the scratchpad showed other files' names; I did not open them.
