# A7 final judgment: historical Helm failure

**Helm 2.0 failed its original rule because seed 20260919 had seven question gains and one question loss, giving p = 9/256 = 0.03515625, above the frozen 0.01 cutoff. Only that seed failed. The records establish several separate weaknesses, but do not establish one neural cause of the version's failure.**

Helm 1.0 keeps its historical `LEARNS_NEW_WORLDS` pass. Helm 2.0-experimental keeps `NO_TRANSFER_TO_NEW_WORLDS`; it is not certified or promoted. These are the original labels, not newly issued certification. The evidence supports useful improvements alongside the failed rule.

## Scope and independence

I am the fresh A7 final judge, session `/root/helm_research_a0/a7_final_judge`. I did not design the investigated fixes or author A1-A6 hypotheses. I reviewed all six first reports, conference responses, A1/A5/A6 addenda, F1/F2 and their raw results, the matrix, follow-up plan, accounting, and actual-session ledger. The integrated research package was supplied at `3f7ac2967c4bc38313a003e2817a3dcab58451d1`. Agreement was not used as a vote.

Subjects are Helm 1.0 source `af0970cfa6d54a85aeb16e5a99a84d791ace59c0` and Helm 2.0 source `20208c923d41c24614504d4ecc2b289ecb66eda8`, each at seeds 20260917, 20260918 and 20260919. The manifest binds original files in the read-only q4-live worktree. My worktree began clean at `59b1dd57e57648ab68c1cc26fbae95a957c20cd3` on `codex/helm-failure-a7-20260922`.

Exposure was not blind. I read the common directive's two-failed-runs story, lineage's broken-loop explanation, AUDIT_PACK's zero-loss shorthand and unseen-world wording, original source comments, and the investigators' interpretations. These are claims to check. My independent calculations and direct source reading below take precedence over those summaries. I did not alter historical documents or receipts.

The authoritative A7 verification is `agents/A7/ORIGINAL_RECORD_CHECKS.json`. It contains original-file hashes, ZIP-member hashes, frozen source excerpts, exact question/record IDs, raw lost-answer predictions, complete analogy answer sets and scores, actual trained-record witnesses, and development targets/results. Paths in this report are relative to the investigation folder unless marked as ZIP members. `agents/A7/COMMANDS_AND_LIMITS.md` records execution and failures. A final custody check bound 26 reviewed package files to the supplied Git commit and checked twelve result-table rows. It detected later cosmetic changes to coordinator documents; the reviewed baseline remains pinned to Git, and all selected investigator reports/raw records still matched. A0 acknowledged the overly broad spacing edit and subsequently reported its correction at integration `2c4f89ed`, with a separate correction receipt and 103 investigator-file comparisons. That correction is A0-attributed; it does not change this judgment or its baseline pin.

## 1. Exact cause of the historical label

The frozen `evaluate_gates.py`, identical in both source commits, requires more gains than losses, an exact one-sided paired probability at most 1/100, gains across at least two kinds and two worlds, and passage in all three seeds. The comparison is initial versus the final main-training checkpoint. A question counts as correct only when every saved presentation is correct.

| Version | Seed | Initial → final /18 | Gains | Losses | Exact p | Primary test |
|---|---:|---:|---:|---:|---|---|
| Helm 1.0 | 20260917 | 2 → 12 | 10 | 0 | 1/1024 | Pass |
| Helm 1.0 | 20260918 | 0 → 12 | 12 | 0 | 1/4096 | Pass |
| Helm 1.0 | 20260919 | 0 → 11 | 11 | 0 | 1/2048 | Pass |
| Helm 2.0 | 20260917 | 2 → 12 | 11 | 1 | 13/4096 | Pass |
| Helm 2.0 | 20260918 | 0 → 12 | 12 | 0 | 1/4096 | Pass |
| Helm 2.0 | 20260919 | 4 → 10 | 7 | 1 | 9/256 | **Fail** |

All six runs satisfy the kind/world breadth requirements. Two Helm 2 runs lose a question; only one fails the statistical test. There is no zero-loss veto. `MIN_PASSING_B=7` describes the zero-loss minimum, not an unconditional seven-gain pass mark.

The 18-question population contains five edge-account, two parts, six reach and five analogy questions; correspondence contributes zero. It is a subset of 50 held questions represented by 127 records. A1 verified the population digest and removal subtraction, not a new execution of every shortcut/exclusion discovery. A6 and A7 reused the frozen population. No full integrity recertification occurred; the original gate records have no taken VOID paths.

The failing seed's lost query is `typed-query-369885551a553d5fa430a4f0389a1e547fb4b7a6234e85d2c9aace042f4fd46f`. Its world is `world-28f61f2d7941a373f50285be7e57b1a9b8ec85bc0aff9e2d18c683e9f86b4547`. The path is `/n2 → /n3 → /n0`; the required answer is `VIA /n3`. All four presentations change to `VIA /n1`. This is **one lost question**, not four independent losses. The other final errors are five analogy questions, one parts question and one additional reach question.

The exact final seed19 scores are `VIA_N1 = 26.474693298339844` and correct `VIA_N3 = 22.808488845825195`, a margin of `3.6662044525146484`. The correct candidate exists and ranks second. All four presentations agree. Seed17's separate lost query, `typed-query-404166e8b8180ddc5758d193239cd0f8a5f91804f2f87bc6141ab9f782157005`, changes from correct `VIA /n3` to `DIRECT`; it still passes the primary test.

F1 and my original-record check confirm ten saved endpoint choices across these five records: complete candidate sets, finite scores, unique maxima, and agreement with the frozen selector. Reach uses one slot containing complete ABSENT/DIRECT/VIA answers. It has no separate mode/VIA normalization. The observed defect is wrong score ordering, not omitted candidates, a winning tie, or a selector disagreement. Why training produced that ordering remains unproved.

A4's saved chronology places seed17's loss within updates 1-147 and seed19's loss within updates 1177-1470, after correctness through pass 8. The separate sixteen-update retention interval starts after update 1470 and cannot cause either earlier endpoint loss. Retaining the seed19 answer while keeping its seven gains would change the arithmetic to 1/128; that is a counterfactual calculation, not an achieved repair.

## 2. Strengths and weaknesses, with separate denominators

The following figures cover **all 50 held questions**, not just the 18-question gate. Each cell is initial → final correct questions / family total. I independently regrouped original scoring; A1 additionally rechecked endpoint semantics with the packaged checker.

| Version / seed | Analogy /5 | Context /5 | Correspondence /5 | Definition /5 | Edges /5 | Parts /5 | Reach /14 | Roles /6 |
|---|---|---|---|---|---|---|---|---|
| H1 / 20260917 | 0 → 0 | 0 → 5 | 0 → 0 | 0 → 5 | 0 → 5 | 0 → 5 | 3 → 13 | 0 → 1 |
| H1 / 20260918 | 0 → 0 | 0 → 5 | 0 → 0 | 0 → 5 | 0 → 5 | 0 → 5 | 1 → 13 | 1 → 5 |
| H1 / 20260919 | 0 → 0 | 0 → 5 | 0 → 0 | 0 → 5 | 0 → 5 | 0 → 2 | 2 → 11 | 0 → 3 |
| H2 / 20260917 | 0 → 0 | 1 → 5 | 0 → 5 | 0 → 5 | 0 → 5 | 0 → 3 | 2 → 11 | 0 → 4 |
| H2 / 20260918 | 0 → 0 | 0 → 5 | 0 → 5 | 0 → 5 | 0 → 5 | 0 → 5 | 0 → 13 | 0 → 2 |
| H2 / 20260919 | 0 → 0 | 0 → 5 | 0 → 5 | 0 → 5 | 0 → 5 | 0 → 2 | 6 → 11 | 0 → 4 |

Correspondence is a clear recorded improvement: H2 gets 5/5 held questions, represented by 20/20 records, in each seed; H1 gets zero. Across the full registry A5 finds H2 88/88 versus H1 7/88 correspondence records. These are shared questions reused across runs. They are not proof of fresh structural transfer or an isolated component's causal benefit.

Analogy remains 0/5 held questions, represented by 0/17 records, in every run; all six finish at 16/70 full-registry records. Definition, context and edge accounting finish perfectly on this held panel. Their answers are available directly from supplied declarations/edges, so those successes alone do not establish multi-step reasoning. Parts, reach and role results vary; H2 is not uniformly better than H1.

The **59 development questions** are a different panel: six parts and 53 reach, over five ten-node worlds and one nine-node world. I independently derived the exact targets and checked all 708 saved endpoint answers against the original scores. VIA requires the correct intermediate node.

| Version / seed | ABSENT /42 | DIRECT /8 | VIA /3 | Parts /6 | All /59 |
|---|---|---|---|---|---|
| H1 / 20260917 | 0 → 0 | 0 → 3 | 0 → 3 | 0 → 1 | 0 → 7 |
| H1 / 20260918 | 0 → 1 | 0 → 5 | 0 → 2 | 0 → 1 | 0 → 9 |
| H1 / 20260919 | 0 → 0 | 0 → 2 | 0 → 3 | 0 → 1 | 0 → 6 |
| H2 / 20260917 | 0 → 0 | 0 → 0 | 3 → 2 | 0 → 0 | 3 → 2 |
| H2 / 20260918 | 10 → 2 | 0 → 7 | 0 → 3 | 0 → 0 | 10 → 12 |
| H2 / 20260919 | 0 → 2 | 0 → 0 | 0 → 3 | 0 → 1 | 0 → 6 |

Five runs improve positive-path answers; H2 seed17 loses one. H2 seed18 reaches 10/11 positive paths while losing eight ABSENT answers. All final ABSENT scores are poor. Thus apparent success is not mainly a majority-ABSENT prediction shortcut. A constant ABSENT answer would match 42/53 reach targets, exceeding every recorded final total, while concealing zero positive-path ability. Size and class balance change together, and these are already examined development examples.

The separate **96-record retention panel** changes as follows: H1 seeds 17/18/19 are 93→93, 93→93, 87→87; H2 is 86→78, 93→93, 84→82. H1 seed19's unchanged total includes one loss and one gain; H2 seed17 includes ten losses and two gains. A4 establishes these from saved before/after scoring. These records are not the gate's 18 questions and must not be added to them.

## 3. Mechanisms established within a stated scope

**Analogy has an inadequate source-comparison path in both versions.** The witness records are `typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e` and `typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a`. One focus is a four-node chain; the other is a three-branch star, both in the grammatical domain. I independently enumerated the entire 64-world bank: each accepts nine worlds, their accepted sets are disjoint, and neither focus belongs to either set.

In the historical source, empty node arguments leave the analogy query constant. Graph updates and pooling are per world. The candidate scorer receives candidate features/domain and flags, without the focus-world graph/domain comparison needed here. `_query_vector`, `_encode_query` and `_world_scores` are unchanged between versions. The original H2 seed18 final file has identical scores for all 62 candidates that remain non-focus across this pair, including every one of the 18 potentially correct candidates. Complete sets, lexical candidate order and scores are saved in my evidence file. Both answers choose the same wrong world.

A fixed relative ranking with a fixed tie order cannot select from both disjoint accepted sets. Changing the two focus rows cannot rescue this because both focus worlds are invalid answers. This is a concrete restriction of that answer path, not a claim that the complete inputs are identical, every analogy answer is impossible, or the entire network lacks graph information. A2's broader checks cover twelve endpoint files; my independent score check covers one. A5 also finds no valid answer in any wrong final analogy top tie. An optimization-only cure for satisfying this pair through the unchanged path is therefore contradicted. This shared limitation does not explain why H2's label differs from H1's.

**Helm 1 correspondence cannot rank mappings by their source nodes.** Its source sends the same target-score row to each source-node slot. Complete bijections therefore have the same summed score in exact arithmetic. The actual decoder already enumerates bijections; it never independently chooses duplicate targets. A5 traces the final lexical tie selection to 7/88 full-registry and 0/20 held records. H2's pair-dependent scores remove that restriction and succeed on the recorded panel. Several other components and whole-container initializations also changed, so the improvement is not an isolated causal measurement of the new pair scorer.

**Row/column normalization alone does not change the complete-assignment decision under the checked conditions.** Every bijection uses each row and column once. Subtracting row/column constants shifts every sum equally; the decoder's normalization cancels that shift. A2/A5's finite-matrix checks support this identity. This rules out a normalization-only decoding explanation with fixed mode logits in exact arithmetic. It does not rule out finite-precision or training effects.

**Helm 1's frozen local message input is real, but the whole-model one-hop claim is too strong.** Updated neighbors do not feed its next-round message input. Node states still change, initial rows already contain degree information, and other answer paths read global pools, marked node states or direct adjacency. H2 already uses updated states. The old local defect neither proves universal multi-edge impossibility nor explains the exact H2 loss.

**The held graphs repeat trained structures.** I checked actual first-pass batch IDs for H2 seed19 and independently found flagged graph matches for all five held focus worlds among 19 trained focus worlds, with match counts 2, 1, 3, 1, 3. For example, held `world-22704554...` maps to trained `world-00d90ef0...` by exchanging n1/n2 and preserving n0/n3; all edges, the declared whole and ordered participants match. The complete IDs, graphs, mapping and fourteen actual trained record IDs for this witness are in the evidence file. A3 establishes the shared data and all six first-pass orders; A4 checks the repeated ten-pass order. Declaration text and query marks are not claimed identical.

World-choice training also carries all 64 candidate worlds, including held graphs. This is graph exposure, not proof of held-focus answer training or memorization. A5's registered degree comparator solves 70/70 analogy records; exact edge-preserving search solves 70/70 analogy and 88/88 correspondence records on this bank. These deterministic algorithms show inexpensive available solutions. They are not learned Helm predictions, compiler-learning evidence or fresh transfer results.

## 4. Plausible causes that remain unproved

Shared-parameter updates, the constant learning rate, repeated order, initialization differences, and interactions among the changed representations can all affect score preservation. A4 verifies constant 0.003, active H2 clipping, all eight kinds in every main batch, and a fixed final endpoint. There is no explicit held-answer preservation objective. These facts make optimization interference plausible; they do not identify a causal parameter, update, rate, head or missing capability.

An initially correct random-model answer is not necessarily a learned skill. Correctness through pass 8 shows this seed19 answer was expressible at recorded weights, but does not prove reliable competence or simultaneous representability of every target. Lower mean loss, balanced kind counts and clipping do not prove answer retention. No matched model/training intervention here distinguishes these alternatives.

## 5. Explanations contradicted or overstated

- Two failed seeds, a compulsory zero-loss gate, or later retention interference causing the primary failure: contradicted by the original rule and chronology.
- Missing correct candidates, winning ties or wrong decoder order for the two inspected reach losses: contradicted by original scores and F1/A7 replay of selection only.
- A hidden effective focus comparison that merely failed to learn the two analogy witnesses: contradicted for this fixed-bank scoring path. Generic whole-network impossibility is not established.
- Duplicate-target correspondence outputs, or Sinkhorn alone newly enforcing the recorded bijections: contradicted by the actual joint decoder and the stated algebra.
- Completely unseen held structures, or never reading held graphs at all: contradicted. Held-focus label leakage and learned shortcut use remain unproved.
- Missing task kinds, an active warmup/cosine schedule, frozen learned heads, or NaN-invalid versions of these six completed jobs: contradicted within A4's source/log scope. Finite logs do not prove good conditioning.
- Majority-ABSENT success explaining the final development results: contradicted by F2 and my independent exact-answer checks. The weak ABSENT class still dominates aggregate error.
- Compiler, PCBA, Ohm, atlas or the later Q4 smoke explaining these historical checkpoints: unsupported chronology. They are separate engineering or experimental records and do not change these labels.

## 6. Priorities and decision boundary

The three prioritized next steps are specified in `NEXT_ACTIONS.md`: first freeze a prospective evaluation design, then repair and compare the source-sensitive analogy path, then test one matched training intervention for the decisive late reach loss. Each has a predicted benefit, risk and verification condition. None has run or been authorized by this judgment.

This investigation can now be committed and integrated with its corrections and unchanged first reports. No second follow-up round is warranted by the checked records. Model edits, neural runs, spending, fresh release criteria and changes to historical receipts are outside this task. The owner's next decision is the future experiment/design and its resource envelope; this report grants neither authority nor funds.

## 7. Evidence gaps and unresolved dissent

The main remaining disagreement is causal strength, not the historical arithmetic. A5's initial analogy uncertainty was narrowed after the witness challenge; A3/A5 corrected their retention-gate wording. I accept those corrections because the raw evidence supports them. I do not accept architecture-only or optimizer-only attribution of the gate loss.

The full integrity chain, evaluator custody and statistical independence assumptions were not recertified. Shared graph structures and repeated question presentations limit inference beyond the frozen rule. No fresh hidden examples, new predictions, checkpoint tensor inspection, component ablation or matched training comparison ran. There is no saved pass-8 tensor checkpoint in the subject manifest. Exact loss-producing updates and learned feature use remain unknown. A7 directly verifies a selected scope; A4's full update-log analysis, A5's wider comparator runs and A2's twelve-file invariance are attributed to those investigators, not relabelled A7 reproductions. Python 3.14.0 is this investigation's stdlib analysis runtime, not evidence of the historical training runtime. Historical dependencies and runtime were not fully recovered or reproduced here despite the pinned source packages, loaded-source records and checkpoint identities.

Root separately reports preserved original files and worktree status in `coordinator/ROOT_FINAL_PRESERVATION_RECEIPT.json`. That is root-attributed custody evidence, not an A7 behavioral check or proof that unrelated dirty-file contents were hashed.

## 8. A7 execution accounting

One completed stdlib suite ran in `0.6102173999970546` seconds, exit 0, on Python 3.14.0. Five named check functions cover six gate subjects / 108 question pairs, all 50 held questions per run by saved scoring, ten lost-answer endpoint instances / sixty scores, two analogy witness records / 64-world enumeration / one score file, five overlap witnesses from 147 batches, and 59 development inputs / 708 endpoint instances. These scopes overlap earlier investigators and each other. They are not additive independent test totals.

The suite verified 56 unique original files, 22 ZIP-member observations and two frozen grader Git versions. Three earlier short partial attempts failed on probe schema assumptions, not evidence disagreements: expecting every ZIP to have its own member-inventory row, treating an empty VOID-path list as integer zero, and treating F2's empty disagreement list as integer zero. The third attempt repeated substantive checks before failing at the final peer-summary assertion; the successful attempt repeated those observations. There was one completed suite, four total attempts, and three partial failures. No failure is hidden by the per-invocation counters in the successful JSON. Separate missing-file/range inspection failures and truncations are logged.

No Torch import, model initialization, checkpoint deserialization, inference, training, GPU, cloud, paid API, install or allowance expansion occurred. Native agent/tool dollar cost is unavailable; this is not a zero-cost claim.

Probe SHA256: `a84df4e8b125e9cef69815c3a13975dbee76f2a1f07110dfb182a6056cb828f3`.

Original-record result SHA256: `277d34f31c586dea42cc4346b818596346bc5fb16581c8b33b88015659d2f8e6`.

Frozen grader LF SHA256: `d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d`.
