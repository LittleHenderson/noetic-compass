# HSET-2 builder report (`CLAUDE_BUILT_CLAUDE_CHECKED`)

**Who.** Claude, temporary builder while Codex is away. I wrote this code and I checked it myself. Two independent
reviewers read the first version (`853e645d`). Their findings and my disposition of each are in
`REVIEW_HSET2_BUILD_20260924.md`. No independent reviewer has read the fixes yet. The design requires a fresh review
before any paid run (design s9 step 1).

**What this is.** The build code for HSET-2, the improved Helm test, as `../EVALUATION_DESIGN_v0_4.md` with its
Amendment A1 (`d840ea02`) says, **plus the builder's PROPOSED Amendment A2** (five more registered bars; text in
`REVIEW_HSET2_BUILD_20260924.md` section 2). It is code plus committed PUBLIC stage-0 files.
**Later round (2026-09-24):** the section "Conformance round, 2026-09-24" at the end records the changes that follow
Codex's proposed Amendment A2 (the statistical policy), finding V-1 and note N1. Sections 1 to 8 describe the earlier
rounds and are kept as written.

**What this is not.**
- No model was loaded, trained or run. Nothing here is a result about Helm.
- The sealed build has NOT run. No real salt was used. No sealed file exists.
- A2 is not agreed. The designer or owner must accept it, or choose the other option each finding names, **before the
  HSET-2 salt is made**.
- Every number below comes from THROWAWAY salts (derived from public strings) or from the public stage 0.

**Status words.** `BUILD_ONLY`. The claim-status words (`NOT_TESTABLE`, `can_carry_a_claim`) come from the build program,
not from this prose.

## 1. Files

LF sha256 of each file at the commit that adds this report. Paths are under
`records/helm_eval_design_20260923/`.

| File | LF sha256 | What it is |
|---|---|---|
| `hset2/hset2_stage0_public.py` | `f2636a9e11f66eb5e2bcc0e26a63fe384102ad50ea1f07908d74acad953eb500` | Stage 0 (public): PUBLIC_EXCLUDED, the 6-node enumeration, the group split, DEV_NEW_6, DEV_DECOYS_6 (unchanged) |
| `hset2/PUBLIC_EXCLUDED_v1.json` | `f101cbdd2984e5bcd21389f8ed76ef4550bc3817735c65f0acb8c8afc6d23b98` | Every 5- or 6-node class in the fixture file, by canonical-form digest (unchanged) |
| `hset2/STAGE0_DEV_SIDE_GROUPS.json` | `6b7b6f812af325b3820a7a729aaa50576fa8ec2c9082ae25e713e5b2016f29cc` | The DEV-side degree groups and their classes (unchanged) |
| `hset2/STAGE0_TEST_SIDE_GROUPS.json` | `348d262cc76f20a351174be687f6bf19a4843f986d9d7135446270a757e9be92` | The TEST-side degree groups and their classes (the forbidden set; public by design; unchanged) |
| `hset2/STAGE0_SUMMARY.json` | `ae2097236a6446aeef592056622b85639542b5cbfb8caff9d749897fefc3ad8c` | Counts, digests, DEV_NEW_6 in draw order, DEV_DECOYS_6, the file hashes of the three lists (unchanged) |
| `hset2/hset2_build.py` | `95cd867e8f8c1a3687466ee3924520de6f2c17f8c225ed1b88f914b202c480e3` | The sealed stage. Run ONLY on AWS by the coordinator with the real salts |
| `hset2/test_hset2.py` | `fb2f3afce480ffce2f70b8330964bba23c56b684adf3c779fc675adf0e8563ec` | Tests (throwaway salts only) |
| `hset2/conftest.py` | `7349eb95bb4435c0706a682310b9cc11ff971cb947c059d54f8f6f220bab0110` | Registers the `e2e` and `slow` test markers |
| `hset2/hset2_throwaway_ranges.py` | `fe323bf8529fff01a6cd4fdd500242c9a1bd8064294fba3708e73bae7244ee40` | Expected ranges over throwaway salts, with the builder's own code (section 5) |
| `hset2/REVIEW_HSET2_BUILD_20260924.md` | `46c5ae9d52da6933b1d2756a61ef648818b07cc120f581255fbc5ffb16b1d4d2` | The two reviews, the dispositions, and the proposed Amendment A2 |
| `hset2_aws_job/launch.py` | `0575ac882226f1f89c946cd16275fd36cc1f10c79726618cd102585d60d59dab` | The launcher (not run). Also `--materialize-tree` for local tests |
| `hset2_aws_job/job.sh.template` | `9766c45310e7ccba9298cd5212c434b4aff261ef0c31d1da7053029af5055e40` | The machine script |
| `hset2_aws_job/watch.py` | `42571a7eb8d35baff68c168a09b21f981346628418df0ca2acd084ed50a3607c` | The watcher; sealed results go straight to the archive (unchanged) |
| `hset2_aws_job/JOB_LIMITS.md` | `277d217b321c9a09f4af859ec9a8b9bfa1fcce3992230fbde8ad9dd9534c106f` | Limits, cost arithmetic, the coordinator's steps before launch |

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

Run as three groups, one at a time, each under 3 minutes on the laptop:
`python -B -m pytest -p no:cacheprovider -q test_hset2.py -m "not e2e and not slow"`, then `-m e2e`, then `-m slow`.
The world-building tests need the pinned tree, written by `launch.py --materialize-tree DIR` outside the repository and
passed as `HSET2_PACKAGE_ROOT`.

**Local results after the review fixes: 24 of 24 passed.** Fast group 21 of 21 (49.11 s; again after later edits,
130.84 s and, on the final files, 110.50 s, with the laptop at 100% CPU from other programs). End-to-end group 2 of 2
(160.91 s). Slow group 1 of 1 (95.56 s). One more end-to-end run on the final files stopped at my 290 s time limit
because of that load; it did not fail. The only builder change after the passing end-to-end run is whitespace in two
lines, and the file's syntax tree is identical with and without it (checked).

| Test | What it proves |
|---|---|
| `test_group_key_is_pinned_spelling` | The group key is `hset_worlds.canon([6, [[in, out], ...]])`, byte for byte (A1 D1) |
| `test_side_rule_bytes` | DEV iff the first byte of sha256(`HSET-2-group-side-v0.1:` + key) is below 64 |
| `test_enumeration_matches_oracle_at_5_nodes` | The fast enumerator gives exactly the oracle's 267 classes at 5 nodes |
| `test_stage0_committed_outputs_reproduce_and_are_consistent` | Stage 0 recomputed equals the committed files; 5,074 classes; 503/1,324 and 1,434/3,747; whole groups on one side; DEV_NEW_6 on the DEV side and reproduced; DEV_DECOYS_6 = the rest of the DEV side |
| `test_split_five_throwaway_and_withheld_rule` | `split_five` gives two disjoint sets of 60; WITHHELD_5 is exactly the rest minus PUBLIC_EXCLUDED; a wrong WITHHELD_5 fails; a TEST_NEW_5 holding a PUBLIC_EXCLUDED class fails with `CUSTODY_BREACH` |
| `test_disjointness_is_counted_not_constant` | Review F5: every printed disjointness value is counted; a hand-made breach shows as non-zero counts |
| `test_test5_digest_is_checked_before_any_item_is_built` | Review F10: a wrong TEST_NEW_5 digest stops `derive` right after `split_five`, with no item built; the right digest passes |
| `test_public_excluded_version_1` | 7 classes (3 at 5 nodes, 4 at 6 nodes): S5A, S5B, S5C, S6A, S6B, S6D, S6STAR; digests; oracle forms; S6STAR marked outside the degree-4 universe |
| `test_three_hop_first_child_rules` | THREE_HOP_FIRST_CHILD on hand-made chains and forks, both rules; the reach bar list |
| `test_single_root_fallback_rules` | Review F2: `SINGLE_ROOT_FALLBACK` and its three-hop form on one-root and two-root shapes, both rules; the BFS form names the lowest-rank parent even off the path; the 3-step claim's bars leave out exactly the two rules built on three-hop |
| `test_reach_comparators_hand_made` | The eight HSET-1A reach comparators plus three-hop on one hand-made world, against both gold rules |
| `test_correspondence_comparators` | All 6 correspondence comparators on hand-made pairs: a valid guess, a broken guess rescued by the flag anchor, a whole-anchored guess that breaks, same-degree non-isomorphic pairs where every check fails, different node counts |
| `test_analogy_comparators` | All 12 analogy comparators on hand-made banks, including review F1's per-candidate guesses: a partner one guess finds, and a partner numbered so the one degree guess breaks an edge (the guess rules must miss it; they may not search) |
| `test_cluster_counting_and_tuned_choice` | A cluster is right only if all 4 rows are right; tuned comparators take their best value on the cell |
| `test_floor` | `can_carry_a_claim` is false for clusters < 10, binding W < 10, or (analogy) groups < 10; the smallest detectable regression is 7 |
| `test_fresh_flags_kind_words_and_presentations` | Every world draws a root whole, two other participants, a kind word of its domain and trained labels; the two presentations differ; a partner's flags land on an image of the focus's flags in well under half of 200 draws |
| `test_twin_banks_profile_equality` | Twins share every class and domain but position 1; profiles equal; 3 and 4 same-degree other-domain decoys; the distractor is in both twins or neither; a tampered twin changes the profile |
| `test_trained_answer_states_pinned_record` | The pinned trained states: analogy 70 MATCH, correspondence 88 MAPPING, reach as HSET-1A recorded |
| `test_trained_answer_states_remeasured` (slow) | Review F10: the re-measurement the sealed build runs (158 frozen-checker targets) gives the pinned record |
| `test_real_mode_refusals` | Review F7: passes whether or not `HSET2_SALT_SHA256` is committed. Throwaway salt files and a throwaway pin only: wrong salt, missing salt file, bad digest and missing arguments are clean `REFUSED:` exits; throwaway mode refuses salt files; a sealed or throwaway output folder inside a git work tree is refused |
| `test_sealed_mode_hides_uncaught_exception_text` | Review F6/F8: in real mode an uncaught exception's text goes only to the sealed folder; the public message holds only its type; refusals pass through unchanged |
| `test_launcher_limits_and_pins` | Worst case $0.6070 < $1.00; the launcher reads the salt pins from the committed builder; each coordinator pin is None or 64 hex; exact tool versions; every bundled file exists; every placeholder; the stage-0 check, the smoke with the re-measurement; tools installed and checked before the bundle; the salts removed |
| `test_tiny_end_to_end` (e2e) | `hset2_build.py` end to end with throwaway salts and 1 focus per split: `build_ok`; outputs named `THROWAWAY_*` with every role `THROWAWAY_NOT_DEV`; all 5 question kinds; every A2 bar registered, printed and scored; every required disjointness count 0; every sealed packet read by Helm's reader on the LARGER route; gold equal to the independent rules; checker v2 equal to direct comparison |
| `test_public_outputs_hold_no_test_id_or_shape` (e2e) | No TEST or WITHHELD class key, hashed shape id, record id, query id, source digest, packet hash, cluster id, item id or world id appears in any public output byte; DEV items hold only DEV-side (or DEV_NEW_5) classes |

**Also checked by hand:**
- `pyflakes` is clean on all 7 Python files. The machine script passes `bash -n`.
- **The process-pool path, now run locally.** A command-line throwaway build with `--processes 2` (seed `tiny-9`,
  `--limit-foci 1`): `build_ok`, 68 items, evaluation 78.7 s, 126.0 s in all. One worker holds about 81 MB.
- **The smoke's re-measurement flag through the command line** (`--only correspondence --limit-foci 1
  --remeasure-trained-states`): re-measured and equal; `build_ok`.
- **The fast path of section 5 against checker v2, with every new bar:** analogy 36 items / 972 verdicts,
  correspondence 64 items / 384 verdicts, reach 5 items / 55 verdicts; 0 disagreements. Before the fixes: 224 of 224
  items on three throwaway runs.
- The frozen-checker measurement of the trained states (158 targets): analogy 70 MATCH, correspondence 88 MAPPING. That
  is the pinned record. NO_MATCH was never trained for either kind (review m4).

## 3. Stage 0 (public, run locally, committed; unchanged by the review)

| Item | Value | The delta review expected |
|---|---|---|
| PUBLIC_EXCLUDED v1 | 7 classes: 3 at 5 nodes, 4 at 6 nodes. S6STAR has out-degree 5, so it is outside the degree-4 universe; 3 six-node classes are inside it | 7 (3 + 4) |
| Every 6-node class (acyclic, weakly connected, degrees at most 4) | **5,074** | 5,074 |
| After PUBLIC_EXCLUDED | 5,071 classes in 1,937 degree groups | 5,071; 1,937 |
| DEV side | **503 groups, 1,324 classes** (81 groups of 5 or more; 233 of 2 or more) | 503 / 1,324; 81 |
| TEST side | **1,434 groups, 3,747 classes** (221 groups of 5 or more; 625 of 2 or more) | 1,434 / 3,747; 221 |
| DEV_NEW_6 | 60 foci in **253** sampler draws | 253 |
| DEV_DECOYS_6 | 1,264 classes | the rest of the DEV side |
| DEV foci usable for analogy (at least 4 same-group DEV-side partners) | **27**, in 18 degree groups (22 in 16 if partners come from `DEV_DECOYS_6` only; review F3) | 27, 18 |
| DEV foci usable for correspondence (at least 1 partner) | **52**, in 35 degree groups (43 in 31 from `DEV_DECOYS_6` only) | 52 |

**Digests** (content digests are `hset_worlds.sha` of the list):
- DEV-side groups `29349b328b8150719c9f5cc03f65fae43602cc9476e9362c6e388028c84d35de`.
- TEST-side groups `aadefc33892428293b9d56d204e97b7f585ce57291de3027959f3058c179d7a5`.
- PUBLIC_EXCLUDED class digests `afa70ca607c3498fdfeff14f850fc15b369f64843b32c47ceac96fdf4beee27f`.
- DEV_NEW_6 `e1c046a464e794873ccfd7d64344cdc418a5bd4121d6deefa49261ed96cdf682`.
- DEV_DECOYS_6 `7d3b68e489b7e97ddd2e109b27a9f4960579356d4a7e5e93a73e3d2c1cb8ce85`.
- All 5,074 classes `5efdb71e8cc7d6d638d6ce57d5c16e02efb8a9b415ac8f9ff7858f680fbd7472`.

**A custody fact for the owner (printed, not acted on).** The 40 public HSET-1B DEV_NEW_6 classes (public seed
`HSET-1B-dev-shapes-v0.1`) fall **16 on the DEV side and 24 on the TEST side**. None is in PUBLIC_EXCLUDED v1. See open
question 7.

## 4. What the sealed build does (short)

- **5 nodes.** TEST_NEW_5 by `split_five` with the HSET-1A salt. It must reproduce HSET-1A's public
  `test_shapes_digest`, checked right after `split_five`, before any item is built. It must hold no PUBLIC_EXCLUDED
  class. WITHHELD_5 is the rest, checked as a partition.
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

- **The registered bars** (design s6 plus proposed A2; printed in every summary with a digest, as
  `identity.registered_comparators`):
  - reach: the eight HSET-1A rules, `THREE_HOP_FIRST_CHILD`, and (A2) `SINGLE_ROOT_FALLBACK` and
    `SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP`. The 3-step claim leaves out the two built on three-hop.
  - analogy: the nine of s6 and (A2) `DEGREE_GUESS_THEN_CHECK`, `WHOLE_ANCHOR_GUESS_THEN_CHECK`,
    `FLAG_ANCHOR_GUESS_THEN_CHECK`, each one guess per same-degree other-domain candidate.
  - correspondence: the five of s6 and (A2) `WHOLE_ANCHOR_GUESS_THEN_CHECK`.
- **Every packet.** The frozen packet validator; the larger-question route must be LARGER; slots v2; Helm's reader
  (`pointer_inputs.read_packet`) with its record, world count, target and ranks checked; checker v2's gold; an
  independent gold (the reach rules re-implemented; the oracle's canonical form for analogy; the oracle's method-M2
  isomorphism list for correspondence, which must equal checker v2's whole admissible set); every comparator graded by
  checker v2 and by direct comparison, which must agree.
- **Printed before any model is read, per cell:** clusters; W for every comparator; the binding W and its comparator;
  distinct degree groups (and behind W); distinct shapes behind W; the power grid (bar +0.10, +0.20, +0.30, 1.0;
  never-loses 0.5, 0.75, 1.0) for the binding comparator; trained answer states; flag-image rates per status; partner
  and target alias positions; the distractor split (A1 D5); for reach, the primary clusters by state and root count;
  the printed diagnostics (longest path, reachable pairs, node signatures, 1-round and full colour refinement);
  `can_carry_a_claim` from the floor. Also: the claims table, the no-regression gate set with the pinned
  `evaluate_gates.py` and the smallest detectable regression (7), the family-wise risk, split disjointness (counted
  from the sets), and the collision share (printed, never required).
- **Custody.** TEST and WITHHELD lists, items, answers and cluster tables go only to the sealed file. The sealed
  folder must not be inside a git work tree. Public files hold TEST numbers only as totals and list digests. In real
  mode an uncaught exception's traceback goes only to the sealed folder; the public log gets its type.
- **Throwaway mode.** Files are named `THROWAWAY_*`; every cell's role is `THROWAWAY_NOT_DEV`; neither output folder may
  be inside a git work tree.
- **To rebuild one sealed packet later:** `hset2_build._init(root)`, then `hset2_build.build_packet(item)`.

## 5. Throwaway-salt numbers against the reviews' expected ranges

**How they were made.**
- `hset2_throwaway_ranges.py` runs the builder's own `load_stage0` and `derive` (the same splits, eligibility and
  items), the builder's own comparator functions and cell summaries. It skips packet validation, the reader and
  checker v2, and compares each comparator directly with the independent gold.
- The real build requires checker v2 to agree with exactly that direct comparison on every packet. They agreed on every
  verdict checked (section 2).
- **With A2 (after the review):** 21 seeds for analogy and reach: `REVIEWER-a5`, `-a7`, `-a8`, `-a9`, `-a12`, `-a16`
  (the second-round reviewer's), `tiny-9` to `tiny-19` without `tiny-13`, and `reach-4`, `-5`, `-6`, `-7`, `-9`; the
  first 16 for correspondence. (`reach-0` to `-3` and `reach-8` were refused with `CUSTODY_BREACH`, correctly: their
  throwaway TEST_NEW_5 held a PUBLIC_EXCLUDED class.)
- **Before A2 (the first version):** seeds `tiny-9` to `tiny-19` without `tiny-13`; 300 seeds for the 5-node focus
  count; the delta reviewer's ten 6-node salts and ten more for reach.
- min / mean / max over seeds.

**With A2 (the numbers the owner must hear; detail in `REVIEW_HSET2_BUILD_20260924.md` section 3):**

| Number | With A2 | Before A2 |
|---|---|---|
| Analogy binding W | **9 / 13.9 / 19** (`DEGREE_GUESS_THEN_CHECK` in 21 of 21) | 20 / 23.4 / 27 (`FLAG_ANCHOR`) |
| Analogy `can_carry_a_claim` | **19 of 21** | 10 of 10 |
| Reach 3-step binding W, first-child | **9 / 16.0 / 22** (`SINGLE_ROOT_FALLBACK`) | 26 / 33.1 / 40 (two-hop) |
| Reach 3-step binding W, BFS | **6 / 11.4 / 20** (`SINGLE_ROOT_FALLBACK`) | 26 / 34.7 / 43 (two-hop) |
| `REACH_3_STEP_TRANSFER_6` testable (both cells) | **14 of 21** | 10 of 10 |
| Reach 4-step binding W, first-child / BFS | **0 / 2.0 / 5** and **0 / 1.6 / 4** | 2 / 7.6 / 11 and 2 / 7.9 / 12 |
| `REACH_4_STEP_TRANSFER_6` testable | **0 of 21** | 3 of 30 |
| Correspondence-6 binding W | 19 / 28.5 / 34 (the whole-anchored bar is 1 lower in 1 of 16) | 19 / 29.0 / 33 |
| Correspondence-5 binding W | 14 / 20.8 / 26 | 14 / 21.0 / 26 |

**The second-round reviewer's own numbers are reproduced exactly** on their six seeds (analogy clusters, `FLAG_ANCHOR`
W and the per-candidate rule's W; reach two-hop W and the fallback rule's W, both rules).

**Before A2, against the delta review (kept as the record of the first version):**

| Number | This build (throwaway) | The delta review |
|---|---|---|
| TEST_NEW_6 sampler draws | 92 / 108.8 / 125 | 101 to 130 |
| Analogy-eligible TEST foci | 21 / 24.3 / 28 | 20 / 24.5 / 32 |
| ... their degree groups | 15 / 17.6 / 20 | 14 / 18.3 / 27 |
| Analogy binding W | 20 / 23.4 / 27 (`FLAG_ANCHOR`; every other comparator of v0.4 is wrong on every cluster) | about foci minus 1 |
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
| Reach 4-step: both cells W >= 10 | 3 of 10 seeds (`tiny-10`, `tiny-12`, `tiny-16`) | 0 of 10 |

**Why the 5-node maximum differs (83 or 85 against 81).** `split_five` orders classes by a salted hash of the class key.
The reviewer used their own canonical form, so their keys, and therefore their splits, differ from the build's for the
same salt. The min (58) and the mean (71.3 to 71.8) agree; the tail differs by chance.

**Printed diagnostics (never bars).** On TEST analogy focus-versus-decoy pairs (972 over 10 seeds): 1-round colour
refinement separates 971, full refinement 972, longest path 499, reachable pairs 731, node signatures 961. On
correspondence-6 NO_MATCH pairs (467): 466, 467, 207, 352, 460. Full refinement separates every pair, as the review said.

**Flag-image rates (fresh flags, M2).** The partner's whole and both participants land on an image of the focus's in
0.0 / 0.04 / 0.087 of MATCH items; the MAPPING target's in 0.0 / 0.03 / 0.045 (6 nodes).

**DEV (public; the same in every seed), with A2.** Analogy: 27 foci, 18 groups, binding W 15 (`DEGREE_GUESS_THEN_CHECK`;
26 before A2). Correspondence-6: 52 foci, 35 groups, W 32. Reach first-child: k 119, 3-step W 23 (32 before A2),
4-step W 2 (4 before). Reach BFS: k 125, 3-step W 14 (33 before), 4-step W 1 (5 before). DEV_NEW_5 correspondence:
5 to 17 foci, W 0 to 6 (feedback only). DEV_NEW_5 relaxed analogy: 60 foci, but degree matching nearly solves it
(binding W 0 to 4). That is expected for the relaxed recipe, which is feedback only. (In throwaway runs these DEV_NEW_5
cells come from a throwaway 5-node split, so they vary by seed; review F11.)

## 6. Runtime and cost on AWS

- **Size.** About 5,300 to 5,540 packets (two throwaway seeds: 5,538 and 5,286). About 3,540 to 3,740 reach, 380
  parts, 240 edge account, 430 to 450 analogy, about 710 correspondence. A2 adds comparators, not packets.
- **Measured per packet** on the laptop, one process, when it was lightly loaded: reach, parts and edge account about
  0.6 s (almost all of it is the frozen validator re-checking the 65-world source); analogy about 0.47 s;
  correspondence about 0.1 s. On 2026-09-24, with the laptop at 100% CPU from other programs, reach packets took 5 to
  24 s each; that is the laptop, not the code.
- **Estimate.** About 2,900 CPU-seconds, so about 6 to 8 minutes on 8 vCPU. With setup, the stage-0 check, the smoke
  stage (now with the trained-state re-measurement, about 2 more minutes), start-up and the build's own re-measurement:
  **about 17 to 22 minutes, about $0.10 to $0.13.**
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
   the whole DEV side (DEV_NEW_6 and DEV_DECOYS_6), the exact mirror of TEST. Fillers follow A1 D3. **Review F3: the
   owner should confirm this reading.** With `DEV_DECOYS_6` only, the DEV counts would be 22 analogy foci in 16 groups
   and 43 correspondence foci in 31 groups (instead of 27 in 18 and 52 in 35).
10. **Correspondence target domain** is drawn uniformly from the 3 other domains, in both statuses. The NO_MATCH class
    is drawn from the focus's group on the same side.
11. **Salts.** The HSET-1A salt is used only for `split_five`. Every new HSET-2 TEST draw, including the 5-node
    correspondence items, uses the HSET-2 salt. DEV items use the public DEV seed.
12. **Reach packets** carry the frozen 64-world training bank unchanged, as HSET-1A and HSET-1B did. Only the focus is
    relabelled between presentations; Helm's reader reads only the focus for reach. **Review F4, the rule written
    down:** design s5's relabel-every-world rule applies to the bank kinds (analogy, correspondence). Reach, parts and
    edge-account packets keep the frozen bank, which the reader never reads. (Also in proposed A2.)
13. **Reach cells** show two floors, one per claim. The cell-level `can_carry_a_claim` is the 3-step one. A cell joins
    the gate set V if any of its claims can carry.
14. **Trained answer states.** Analogy and correspondence are pinned from one frozen-checker measurement. The sealed
    build re-measures them first, before stage 0 and the splits (fail closed). The AWS smoke re-measures them too
    (review F10). Reach reuses HSET-1A's record.
15. **Flag-image rate** = whether one automorphism maps the focus's whole and both participants onto the other world's
    (also printed for the whole alone).
16. **Printed diagnostics** use focus-versus-decoy class pairs: 4 per analogy focus, 1 per correspondence focus.
17. **The power grid** is printed for the binding comparator. Passing it is necessary, not sufficient.
18. **Extra DEV cell.** `DEV_NEW_5/CORRESPONDENCE` (feedback only) mirrors the secondary claim. The design does not
    name it.
19. **Not rebuilt.** TEST_NEW_5 parts and edge account (HSET-1A has them) and any TEST 5-node analogy (declared
    `NOT_TESTABLE`).
20. **The one-guess family (review F1, proposed A2).** The same three rules in both bank kinds: 0, 1 or 3 declared
    participants mapped first, then the rest paired by (in-degree, out-degree, rank), then one check of every edge.
    In a bank each rule makes that one guess for each same-degree other-domain candidate, in alias order, and answers
    the first that passes.
21. **`SINGLE_ROOT_FALLBACK_AFTER_THREE_HOP` (review F2, proposed A2)** was not asked for by the reviewers. It is the
    same gap as F2 one step deeper, so it is a bar of the 4-step claim only.
22. **Throwaway outputs (review F11)** are named `THROWAWAY_*`, carry the role `THROWAWAY_NOT_DEV`, and are refused
    inside a git work tree.

## 8. Open questions

1. **Amendment A2** (review F1, F2): the designer or owner accepts it, edits it, or chooses option (b) of either
   finding, **before the HSET-2 salt is made**. With A2 the owner must hear: the 3-step reach claim could carry in 14 of
   21 throwaway salts; the 4-step reach claim in 0 of 21; the analogy claim in 19 of 21.
2. **The HSET-2 salt** is not made and its sha256 is not committed. The build and the launcher refuse until the
   coordinator commits `HSET2_SALT_SHA256` (design s3 step 6).
3. **`EXPECTED_TEST5_SHAPES_DIGEST`** must be copied from HSET-1A's public build summary. I did not open that
   `results/` folder (standing rule), so the launcher refuses until it is set.
4. **`UV_TARBALL_SHA256`** (review F9) must be copied from the uv 0.12.7 release's published `.sha256` file for
   `uv-x86_64-unknown-linux-gnu.tar.gz`. The launcher refuses until it is set.
5. **The DEV decoy pool** (review F3): confirm the whole-DEV-side reading, or ask for `DEV_DECOYS_6` only.
6. **The old throwaway copies** in the session scratchpad (review F11: `e2e_an/`, `e2e_co/`, `run1/`, `t_analogy/`,
   `t_correspondence/`) carry real-looking names. The owner decides whether to keep them. I deleted nothing.
7. **HSET-1B's 40 public DEV_NEW_6 classes: 24 are on HSET-2's TEST side.** If any was ever used with a trained model or
   a candidate bank, it must join PUBLIC_EXCLUDED **before** the sealed stage. That would change the committed stage-0
   files, so it must be decided now.
8. **The twin reading.** I drew flags, kind words and labels fresh per item, so the NO_MATCH twin is a fresh draw of the
   same classes and domains. The other reading (identical worlds except position 1) is also defensible.
9. **The widened 5-node cell** keeps the design's name `TEST_NEW_5/CORRESPONDENCE`, although its foci include
   WITHHELD_5 classes (A1 D2).
10. **The extra DEV cell** `DEV_NEW_5/CORRESPONDENCE`: keep or drop?
11. **A fresh independent review** of the fixes is still required before any paid run (design s9 step 1). This build
    is `CLAUDE_BUILT_CLAUDE_CHECKED`.
12. **Not updated:** the repository `CHANGELOG.md` and `docs/CAS_HARNESS_SPEC_SHEET.md` are outside this sparse checkout.
    The coordinator decides whether they need a line.

## EXPOSURE (every file outside my working copy that I opened)

**First version (`853e645d`).** Read through `git show` / `git cat-file` from `claude/helm-builder-continuation-20260923`
(commits `cc68d8b3` and `785c9bd1`):
- in full: `typed_teaching/checker_v2.py`, `answers_v2.py`, `slots_v2.py`, `source.py`, `answers.py`, `course.py`,
  `pointer_inputs.py`; `eval_paths/larger_question_scope.py`, `larger_question_learner.py`, `__init__.py`;
- in part: `larger_question_fixtures.py` (lines 1 to 200); `pointer_contract.py` (grep, and lines 395 to 470);
  `practice_contract.py` and `matched_contract.py` (grep hits and nearby lines);
- `eval_paths/fixtures/larger_question_fixtures_v0_1.json`: its sha256, top-level keys, the shape table, one world and
  one fixture's keys; the stage-0 program parses all of it.
- Git metadata only: `git log`, `git ls-tree` (names and sizes), `git diff --stat`, `git merge-base`.
- The materialized tree `785c9bd1` (1,186 files written from git objects into the session scratchpad, outside every
  repository): the build and tests import code from it and load `public_course.json`, the tokenizer and the development
  material through the frozen loaders. I read `public_course.json` directly once, to count registry records by kind
  (counts only). The tree also holds `records/typed_course_001/checks_002/private_targets.json` (the course's own
  training targets); neither I nor my programs opened it.
- My own throwaway outputs in the scratchpad (public and `sealed_throwaway` files made with throwaway salts only).

**Review fixes (this commit).** Listed in full in `REVIEW_HSET2_BUILD_20260924.md` (EXPOSURE): a fresh materialized
tree `785c9bd1` in the scratchpad folder `hset2_fix/tree/` (the same tree digest `fe2eaa17...`), used through imports
and the frozen loaders, plus a `grep` of its `typed_teaching/source.py` (3 lines); my scratch scripts and throwaway
outputs in `hset2_fix/`; directory listings (names and sizes only) of the scratchpad; the laptop's process list and
free memory.

**Not opened, in either round:** any `*_eval.jsonl`; any file or folder named sealed except my own throwaway outputs;
anything under `D:/tksCAS-archive/`; any `salt.hex`; S3 or AWS; the meta1 budget ledger; any `results/` or
`results_attempt1/` folder; Claude transcripts. Nothing was downloaded. A directory listing of the scratchpad showed
other files' names; I did not open them.

## Conformance round, 2026-09-24: Codex's proposed A2, finding V-1 and note N1 (`CLAUDE_BUILT_CLAUDE_CHECKED`)

**Who.** Claude, the temporary builder. I wrote these changes and checked them myself. No independent reviewer has
read them yet.

**What this is.** Code that follows the text of Codex's **proposed** Amendment A2, the statistical policy. The text is
in `EVALUATION_DESIGN_v0_4.md` (sections A2.1 to A2.6 and the analogy line of the section 6 table) and in
`../helm_controlled_prelaunch_20260924/STATISTICAL_POLICY.json`, both at commit `f287f965` on Codex's branch
`codex/helm-controlled-prelaunch-20260924`. I read them with `git show`. I did not check out that branch.

**What this is not.**
- Codex's A2 is not agreed. The design owner decides later. This is conformance to proposed text only.
- No model was loaded or run. No real salt exists, and none was made. Every number comes from throwaway salts or
  from public files. Nothing ran on AWS.
- `STATISTICAL_POLICY.json` says `"launch_authorized": true`. That is Codex's record. It gives this builder no launch
  authority, and I launched nothing.

**One name, two texts.** Two different proposals are both called "A2".
- The builder's A2 (`REVIEW_HSET2_BUILD_20260924.md` section 2): five more bars.
- Codex's A2: the statistical policy.

Below, "Codex A2" always means the statistical policy. The code keeps both.

### C.1 What changed, task by task

**T1. Complete comparator families (Codex A2.1).**
- New bars `FIXED_POSITION_1` to `FIXED_POSITION_7`. Each always answers the j-th non-focus world, in numeric alias
  order (W0, W1, ...). If the bank has fewer than j other worlds, it answers NO_MATCH.
- New bars `STATUS_BY_COUNT_0` to `STATUS_BY_COUNT_8`. E is the list of other worlds with the focus's joint degree
  list and another domain, in alias order. The rule answers NO_MATCH if E is empty or has fewer than m members.
  Otherwise it answers E[0].
- Every member is its own bar, with its own W, gains, losses and p. A cluster counts as right only when both twins
  and both presentations are right, as for the model. Checker v2 grades every member.
- **The tuned choice is gone from every claim decision.** Before, `BEST_FIXED_POSITION` and `STATUS_BY_COUNT` took
  their best setting on the TEST cell (`cluster_results` in the lines Codex cited, `hset2_build.py` 686 to 751 at
  `853e645d`). That code is removed.
- **No bar was dropped.** The old `BEST_FIXED_POSITION` always chose one displayed alias, W0 to W7, focus included.
  All eight are now bars (`FIXED_ALIAS_W0` to `FIXED_ALIAS_W7`), untuned. The old `STATUS_BY_COUNT` table is exactly
  `STATUS_BY_COUNT_0` to `STATUS_BY_COUNT_8`. The tuned choice was always one of these, so the new set is at least as
  hard to beat.
- The old tuned choices are still printed, as `tuned_on_this_cell_diagnostic_not_a_bar`, labelled
  `DIAGNOSTIC_ONLY_NEVER_A_BAR`. No floor, bar or claim reads them.
- The analogy cell now has 35 bars. Before this round it had 12.

**T2. Two more views (Codex A2.2).** For every cell with bars, TEST and DEV:
- The original cluster calculation is unchanged. It is now labelled `CONDITIONAL_CLUSTER_DIAGNOSTIC`.
- **Degree groups.** Clusters are grouped by the focus's node count and joint degree list (the stage-0 group key).
  A group's difference is the exact mean of its clusters' score differences (Python `Fraction`). The group is a win
  if the mean is above 0, a loss if below 0, and a tie if 0. Each group counts once.
- **Shared-shape components.** For each degree group, the build collects every canonical class used in any packet
  role and presentation: focus, partner, target, decoy, distractor, filler. Two groups join when these sets share a
  class. Joining is transitive. A component's difference is the equal-weight mean of its groups' differences.
- **The test in both views.** B wins and C losses; ties are left out. The exact tail is
  `sum(comb(B+C,k), k=B..B+C) / 2**(B+C)`, and p = 1 when B + C = 0. A view passes only if B > C, the overall
  accuracy difference is above 0, and p <= 1/100. The comparison with 1/100 is exact.
- **New functions.** `view_units` (groups and components), `paired_views` (one comparison in all three views),
  `evaluate_cell_views` (the model against every bar of a cell; for the future scorer), `views_block` (the counts
  before any model).
- **Custody.** Group keys and component membership stay on the cluster tables. For TEST cells those tables go only
  to the sealed file. The public summary carries counts and size distributions only.
- **A reading I made (reach).** A reach packet has one listed role, the focus. The frozen 64-world training bank
  rides unchanged in every reach packet, but it is not a listed role, so it joins no groups. So for reach,
  components equal groups. If the bank counted, every reach group would join one component, and the reach
  component view would have 1 unit.

**T3. The feasibility table (Codex A2.4).** The summary has a new block, `a2_4_feasibility`. For every cell with bars
(and for each reach claim) it gives:
- the units: clusters, degree groups and components; distinct focus shapes; the size distributions (clusters per
  group, groups per component, clusters per component);
- W of every bar in every view (the units where a perfect model could beat that bar), and each view's binding
  minimum;
- the A2.4 floors: at least 10 clusters, 10 groups and 10 components, and binding W >= 10 in every view. Each failure
  is written as a `NOT_TESTABLE` reason. The floors are **binding only for `TEST_NEW_6/ANALOGY`**, the confirmatory
  claim's cell. For every other cell they are printed and labelled `PRINTED_NOT_BINDING`, because A2.4 names them only
  for the confirmatory claim. Every original floor is kept.
- the power: the HSET-1A grid at the cluster level (unchanged; a diagnostic); `NOT_IDENTIFIED_FROM_RAW_ACCURACY` at the
  group and component levels; and the exact conditional sign-power grid for every unit count n that occurs, for
  d = 0 to n discordant units and q = 0.60, 0.70, 0.80 and 1.00. The sums are exact fractions, rounded only when
  printed. The all-win minimum is printed: 7 discordant units.
- the repaired-versus-unchanged informative count: `NOT_YET_OBSERVED`, with the structural maximum (each view's unit
  count).
- In throwaway mode the block's state reads `THROWAWAY: ... NOT the A2.4 table and never a result`. The build also
  prints the table to its log.

Also in the summary:
- The claims table has a new row, `REPAIR_IMPROVES_ANALOGY_6`, marked as the one confirmatory claim (PROPOSED). Before
  any model it can only read `NOT_TESTABLE` (with reasons) or stay open.
- Each base claim gets the role `MANDATORY_EXPLORATORY` and its binding W per view, printed but not binding.
- A new block, `inference_assumptions`, has the state `OPEN_FOR_THE_BUILDER_SCORER_REVIEW`. It lists seven
  dependencies built into the sampling. I did not decide whether the assumptions hold. Under A2.2 that is the
  review's job; if they are not supported, the status is `INFERENCE_ASSUMPTIONS_UNSUPPORTED`.

**T4. Two switches for the design owner.**
- `REGISTER_FRONTIER_FALLBACK = True`. `FRONTIER_FALLBACK` is the rule of finding V-1, coded as
  `REVIEW_HSET2_BUILD_20260924.md` section V.3 writes it (the verifier's `V4_FRONTIER_MAXOUT`). It is a bar of both
  reach claims. It never follows an edge more than 2 steps from the whole.
- `REGISTER_FLAGS_TIEBREAK_GUESS = True`. `FLAGS_TIEBREAK_GUESS_THEN_CHECK` is the rule of note N1. For each
  same-degree other-domain candidate, in alias order, it makes one guess (every node sorted by in-degree, out-degree,
  declared-flag position, then rank) and one edge check. It answers the first candidate that passes, else NO_MATCH.
  It is an analogy bar.
- Setting a switch to False takes the rule off the bar lists. The rule is still computed, and its W is printed as
  `computed_not_registered_W`. The switch values are part of `registered_comparators`, so the digest records them.
- **The bar-set digest changed.** `registered_comparators_digest` was
  `1a233f311ac4585149600a7812748aa33ac27253640db22c8931dcfae0f8de17` at `1520e17c`. It is now
  `cf88cebafa9169964aff041d3c1bcb652b2067b86854befc253dd452291c78af` (both switches on). With only FRONTIER off it
  would be `49d9d28959cb4862c34ec9d975247133ccd955d2884c1908f05bc8297b53e32b`; with only FLAGS off,
  `51c5f1d4bfa49145ec9b684e9e8ff06543047969ea28a6893c4a2ac9e2b6ad31`; with both off,
  `e408b423cfd1b28350c039cf34ca3d4091a2f8c4a4156f9bd3dedf4ec7077cfb`. The build prints the digest in its log.
- Decision D1 option (a) is the default. Options (b) (declare `REACH_3_STEP_TRANSFER_6` `NOT_TESTABLE` now, or rename
  it) and (c) (rebalance the reach cell) are design changes. A switch cannot make them; each needs its own amendment.

**T5. The older public classes on the proposed TEST side** (Codex item 4; section 3 "A custody fact" and open
question 7 of this report). From public files only. Nothing was applied. Details and the class digests are in the new
file `PROPOSED_T5_OLDER_PUBLIC_TEST_SIDE.json`, which no build code reads.
- **Which classes.** The 40 public HSET-1B `DEV_NEW_6` classes: public seed `HSET-1B-dev-shapes-v0.1`,
  `hset1b_build.draw`, 47 sampler draws. **24 sit on HSET-2's TEST side and 16 on the DEV side.** 6 of the 16 DEV-side
  classes are also HSET-2 `DEV_NEW_6` foci. The 24 TEST-side classes have 5 to 10 edges and sit in 23 degree groups.
- **Did they enter training?** No, as far as I searched. The frozen public course at `785c9bd1` has 64 families and
  64 bank worlds, all with 3 or 4 nodes (12 and 52). Its 564 registry records all take their source world from those
  64. So no 6-node class entered that course, and none of the 40.
- **Did they enter a candidate bank?** No, as far as I searched. The course's candidate bank is the same 64 worlds.
  The development material at `785c9bd1` holds 70 distinct worlds, of 3, 4, 9 and 10 nodes; none of the 40.
  `OWNER_DIRECTION_20260924.md` (row 1) records the HSET-1B design as never built or launched, so no HSET-1B packet was
  ever made.
- **How far I searched.** The frozen course, its bank and its development material, through the frozen loaders; a
  text search of this working copy for the HSET-1B DEV seed string; the committed HSET, probe and repair-job code in
  this design folder. **Not searched:** other branches or repositories, AWS, S3, the archive, and any training run
  outside the frozen course. So "not found" holds only inside that search.
- **Why they still matter.** Anyone can rebuild the 40 from the public seed and code. `BUILD_SPEC_HSET1B_v0_1.md`
  allows development to use `DEV_NEW_6` classes. Any such use, past or future, would touch 24 HSET-2 TEST-side classes.
- **How PUBLIC_EXCLUDED handles them now.** It does not. `PUBLIC_EXCLUDED_v1.json` lists only the 7 fixture classes.
  The 24 are ordinary TEST-side classes: they can be drawn as `TEST_NEW_6` foci and used as TEST partners, decoys,
  distractors and fillers.
- **Proposed rule (not applied).** Before the HSET-2 salt is made: `PUBLIC_EXCLUDED` v2 = v1 plus the 24 TEST-side
  classes, then stage 0 is run again and committed again. General form: any class that a committed public seed or
  file named for development, training, probing or a candidate bank before the salt, and that falls on the TEST side,
  joins `PUBLIC_EXCLUDED` before the salt. (After the salt, A1 D6 already refuses new public 6-node shapes off the DEV
  side.)
- **Its measured effect (public stage-0 lists; not applied).** The DEV side, `DEV_NEW_6` and `DEV_DECOYS_6` stay
  byte-identical by construction (the DEV sampler keeps only DEV-side classes). The TEST side goes from 3,747 to 3,723
  classes, and from 1,434 to 1,429 non-empty groups. Groups with 5 or more classes (where an analogy focus can have 4
  partners) go from 221 to 219. Classes in those groups go from 1,847 to 1,828. The throwaway ranges were not measured
  again under this rule.

**T6. Throwaway ranges.** All 21 seeds were measured. The numbers are in `REVIEW_HSET2_BUILD_20260924.md`, section
"Conformance to Codex A2 (PROPOSED)".

### C.2 Files changed in this round

LF sha256 at this commit. The stage-0 files, `PUBLIC_EXCLUDED_v1.json` and `hset2_stage0_public.py` are unchanged.

| File | LF sha256 | Change |
|---|---|---|
| `hset2/hset2_build.py` | `97d3e73bc8be19b4e2f0ab770ed1eb182d1890fa7f9ce4d61c76c4e0028895cd` | T1 to T4 |
| `hset2/hset2_throwaway_ranges.py` | `2849515a0fe4fc8515acec40f65fff7f87c4d978cfc02460da64c32b61aa1497` | no tuned tables; views in the headline; `--splits`; refuses an output inside a git work tree |
| `hset2/test_hset2.py` | `eed494a31068c0b6e77b1ce31dbff58705d8c6db909f1ce1a997c5493113ce1a` | 5 new tests, 4 changed |
| `hset2/PROPOSED_T5_OLDER_PUBLIC_TEST_SIDE.json` | `397ddefb24abc557d95760c09feb3e1176ffa6f0e256961b13ab36c3056d3201` | new; T5; read by no code |

The summary schema is now `claude.hset2-build-summary/0.3`.

### C.3 Tests and checks

**Tests: 28 run, 28 passed.** Fast group 26 of 26 (28.06 s, on the final files). End-to-end group 2 of 2 (96.11 s, on
the final files). The slow group (1 test, the trained-state re-measurement) was **not run** this round; its code path
did not change. `pyflakes` is clean on the three changed Python files.

New and changed tests:

| Test | What it proves |
|---|---|
| `test_frontier_fallback_rules` (new) | V-1's rule on hand-made worlds: it answers VIA where `SINGLE_ROOT_FALLBACK` says ABSENT and both vias equal the gold; the first-child form answers VIA wrongly on a no-path world, the BFS form keeps ABSENT; the most-children via; two-hop first; the switch (both claims; off leaves both bar lists; the digest changes) |
| `test_codex_a2_1_families_and_switches` (new) | Every family member is one registered bar; no tuned bar remains; every first-version bar is still a bar; the old tuned tables are kept whole; the digest differs from `1a233f31...`; the N1 switch off leaves the list and changes the digest |
| `test_view_units_and_feasibility_counts` (new) | Groups; components joined through a shared filler and transitively; W in every view; size distributions; the floor reasons; binding versus printed floors; `NOT_YET_OBSERVED`; no class or group key in the printed block |
| `test_paired_views_exact` (new) | Exact means (4/7, 1/3); the cluster view passes while the group view cannot (every win in one group: B = 1, p = 1/2); `evaluate_cell_views` against every bar |
| `test_sign_tail_and_conditional_power_exact` (new) | Exact tails (1/128, 11/1024, p = 1 at B + C = 0); the smallest winning counts (7 of 7, 9 of 9, 10 of 10, 11 of 12); the power equals a brute-force exact sum; the all-win minimum 7 |
| `test_analogy_comparators` (changed) | Adds every family member on a hand-made bank, and the N1 guess (it finds a partner the degree guess misses) |
| `test_cluster_counting_and_tuned_diagnostic` (replaces `..._tuned_choice`) | No parameter is chosen for a claim; the diagnostic picks the first family member with the fewest wrong clusters |
| `test_three_hop_first_child_rules` (changed) | The reach bar list now ends with `FRONTIER_FALLBACK` |
| `test_tiny_end_to_end` (changed) | Every new bar scored in its cells; no tuned field; the A2.4 block (labelled THROWAWAY, every claim cell, units ordered, W within units, a power row for every unit count); `REPAIR_IMPROVES_ANALOGY_6` reads `NOT_TESTABLE` with reasons at 1 focus per split |

**Checker v2 against direct comparison, every new bar, small throwaway builds** (scratch script
`checker_vs_direct.py`, not committed):
- Analogy, seed `tiny-9`, `--limit-foci 3`: 36 items (12 TEST_NEW_6, 12 DEV_NEW_6, 12 DEV_NEW_5), 1,260 verdicts,
  **0 disagreements**. All 25 new analogy rules were compared (7 + 8 + 9 family members and the N1 guess).
- Reach, seed `REVIEWER-a5`, full foci: 24 TEST items where two-hop says ABSENT, 12 where `FRONTIER_FALLBACK` answers
  VIA and 12 where it keeps ABSENT. 288 verdicts, **0 disagreements**. Checker v2 marked FRONTIER right on 10 VIA and 12
  ABSENT items, and wrong on 2 VIA items.
- The end-to-end test also requires checker v2 to agree with direct comparison on every item of the tiny build.

### C.4 Choices where the proposed text is silent

1. `FIXED_POSITION_j` for a bank with fewer than j other worlds answers NO_MATCH. (Every real analogy packet has 8
   worlds, so this happens only in hand-made tests.)
2. The pre-A2 tuned table is kept as `FIXED_ALIAS_W0` to `W7`, so no bar is dropped. Codex's text names only the
   non-focus positions.
3. For reach, the focus is the only listed role, so components equal groups (T2 above).
4. The A2.4 floors bind only on `TEST_NEW_6/ANALOGY`. They are printed for every other cell.
5. Reach views use the claim's primary clusters, the same clusters as the original calculation.
6. When bars tie for the binding W, the first in the bar list is named; all tied bars are listed.
7. At the group and component levels the power is `NOT_IDENTIFIED_FROM_RAW_ACCURACY` plus the conditional sign grid.
   I did not build a per-unit model of group signs from cluster accuracies.
8. The N1 guess is registered for analogy only, as note N1 asks. It is not added to correspondence.
9. No three-hop form of `FRONTIER_FALLBACK` was added for the 4-step claim. That claim already reads `NOT_TESTABLE` in
   every throwaway salt.

### C.5 Open questions for the design owner

1. **Codex A2**: accept, edit or reject the conformance above, before the salt is made. The same holds for the
   builder's A2 (five bars).
2. **Decision D1** (finding V-1): keep `REGISTER_FRONTIER_FALLBACK = True` (then `REACH_3_STEP_TRANSFER_6` reads
   `NOT_TESTABLE` in 21 of 21 throwaway salts), or choose (b) or (c) with an amendment.
3. **Note N1**: keep `REGISTER_FLAGS_TIEBREAK_GUESS = True` (the analogy claim's original floor then holds in 17 of 21
   throwaway salts instead of 19), or switch it off.
4. **T5**: accept the proposed `PUBLIC_EXCLUDED` v2 rule (24 classes) or not. It must be decided before the salt,
   because it changes the committed stage-0 TEST-side files.
5. **Inference assumptions** (Codex A2.2): the builder/scorer review must state whether they hold. The seven known
   dependencies are listed in the summary.
6. **The reach reading of components** (T2): confirm that the frozen training bank is not a packet role.
7. **A fresh independent review** of this round is needed before any paid run. This round is
   `CLAUDE_BUILT_CLAUDE_CHECKED`.

### EXPOSURE (this round: files outside my working copy, and the public files inside it that bear on T5)

- **Codex's branch, read-only, by `git show` of commit `f287f965`:** `EVALUATION_DESIGN_v0_4.md` (in full),
  `records/helm_controlled_prelaunch_20260924/STATISTICAL_POLICY.json` (in full), and
  `_handoffs/HELM_NEXT_PHASE_20260923/CODEX_AMENDMENTS_20260924.md` (a search for headings and "HSET-2", then lines 55
  to 68, its item 4). Copies of these three went to the Git Bash `/tmp` folder (`ed04_codex.md`, `stat_policy.json`,
  `codex_amend.md`), outside every repository. A `git fetch` of that branch and a `git ls-tree` of the commit (names
  only). No checkout.
- **The pinned CNCM tree `785c9bd1`,** written from git objects by `launch.py --materialize-tree` into
  `a2conf/tree/` of the session scratchpad (1,186 files, tree digest
  `fe2eaa174b6d7265bcb78de25a13b6898a158ee808bfaf87a419c3ff10190db6`). The tests, the build and my scripts imported
  code from it and loaded the public course, the tokenizer and the development material through the frozen loaders.
  By hand I read `typed_teaching/source.py` lines 255 to 290 (`freeze_bank`) and searched the `typed_teaching` folder
  for `load_material`. Neither I nor my programs opened `records/typed_course_001/checks_002/private_targets.json`.
- **Public files of this working copy:** the HSET-1B build spec, `hset1b_build.py` (`draw`), the analogy probe
  (`analogy_wiring_probe_v0_2.py`, a search for world and shape words), the repair job (`RUN_LOG.md` lines 1 to 40, a
  search of `launch.py` and `job.sh.template`), the handoff files that mention HSET-1B (a search, and row 1 of
  `OWNER_DIRECTION_20260924.md`). A text search of the working copy for the HSET-1B DEV seed string, with `results/`
  folders and `*_eval.jsonl` files excluded. A name-only search showed that no sealed, salt, `*_eval.jsonl` or
  `private_targets.json` file exists in the working copy.
- **Earlier session scratch files, read:** the verifier's `verify_1520/probe_reach.py`, `probe_analogy.py` and
  `check_v4_checker.py` (the rules' exact code), its `r_*.json`, `a_*.json` and `r_b1.log` (timings and results), and
  the builder's `hset2_fix/fastpath_vs_checker.py` and `m_re_1.json`, `m_an_1.json` (timings). A directory listing of
  the scratchpad (names only).
- **My scratch files** in `a2conf/` of the session scratchpad: `checker_vs_direct.py`, `summarise_t6.py`,
  `t5_older_public.py`, `t5.log`, the range outputs `t6_analogy.json`, `t6_reach_1.json`, `t6_reach_2.json`,
  `t6_reach.json`, `t6_reach_dev.json`, `t5_older_public.json`, `builder_section.md`, `review_section.md`, and the
  pytest folders `pt_fast1`, `pt_fast2`, `pt_e2e1`, `pt_fast_final`, `pt_e2e_final` (their throwaway builds include
  `sealed_throwaway/THROWAWAY_HSET2_SEALED_TEST.json`, made with a throwaway salt). Not committed.
- **Laptop state:** free memory and the Python process list (PowerShell).
- **Not opened:** any `*_eval.jsonl`; any sealed file or folder except my own throwaway outputs; anything under
  `D:/tksCAS-archive/`; any real salt; S3 or AWS; the meta1 ledger; any `results/` folder;
  `private_targets.json`; Claude transcripts. No real salt was used or made. Nothing was downloaded.

## Fix round after the review of 4c402209, 2026-09-24 (`CLAUDE_BUILT_CLAUDE_CHECKED`)

The review, its seven findings and the builder's disposition of each are in `REVIEW_HSET2_BUILD_20260924.md`, section
"Review of 4c402209...". No independent reviewer has read this round. No model was run, no real salt was used or made,
and nothing ran on AWS.

**What this round supersedes in the section above** (the text above is kept as it was written):
- **T4, first switch.** `REGISTER_FRONTIER_FALLBACK` no longer exists. It is replaced by `D1_FRONTIER_DECISION`, one
  constant with one value per option of decision D1: `a` (default; the same bars as before), `b_not_testable`,
  `b_rename` or `c` (refused until its own amendment exists). `FRONTIER_FALLBACK` stays a bar of
  `REACH_4_STEP_TRANSFER_6` under every value.
- **T4, the digests.** Under the default settings every claim has the same bars as at `4c402209`. The digest changed only
  because the record's shape changed: it is now `14be05d5a0845e52a194628974fd0bfd6763b0fc0b1e1e96dfe3dd779671edfd`.
  - With `b_not_testable`: `42928c8681b59064ed5feb200a4072171c580147f7c73927c2e156bb1fd94bb9`.
  - With `b_rename`: `f24cbbc878a08ef6a5750e3043e7898bbb23623d835926459efc3271e8a45781`.
  - With D1 `a` and N1 off: `47a7777b481a47a5b28730432744cd405878e8cf736e0ad590f2449bfea9b8e8`.
  - The four digests printed in T4 above belong to `4c402209`.
- **C.4 item 7.** The HSET-1A power grid is now computed exactly at the group and component levels, for each view's
  binding bar (`exact_power_under_hset1a_model`, assumptions in `power_assumptions`). In those two views it is an upper
  bound on the pass chance, except in the never-loses rows, where it is exact. Every exact power is also printed to 12
  significant digits.
- **C.5.** The open questions for the design owner are now the list in the review file, section R.4.

**Added to the output, no bar or floor changed:**
- `both_arm_packet_route_acceptance: NOT_YET_CHECKED`, naming the unchanged arm's reader check that is still required;
- on `REPAIR_IMPROVES_ANALOGY_6`: `inference_assumptions_status`, `mechanism_gate_status` (`MECHANISM_GATE_OPEN`, read
  from `STATISTICAL_POLICY.json` at `f287f965`) and `status_words_the_scorer_must_use`;
- on `ANALOGY_BEYOND_DEGREE_6` and `REPAIR_IMPROVES_ANALOGY_6`: `open_design_question_before_the_salt`. This is the
  review's MAJOR finding, a design choice, recorded and not decided.

**Tests:** fast group 29 of 29 passed, end-to-end group 2 of 2 passed, both on the final files. The slow group was not
run; its code path did not change.

**Files** (LF sha256):
- `hset2_build.py` `a21d022bfc9a8b851dbea23b3f96c79d4cd1ff3c8b5f5cb2e70a9448d7c037ba`
- `test_hset2.py` `997345c922e5184db55b99b08eba60592e0081ea83cf61bf9bdaade2242ad4af`
- `hset2_throwaway_ranges.py` `6d4bf43158642bcee275d1e49e4746a05eb5af05e3c4b32b99ecec7b01a7f917`
