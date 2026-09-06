# V7 composition result — partial evaluation, checked evidence

Training improved some individual program choices and shallow validation matches, but **CAS solved no new nested test task: 0/72 before training and 0/72 after**. The generic model has no confirmed test success either: 0 correct, 71 incorrect and one unfinished result from 72 trained attempts. The rule control solved its 71 attempted tasks; one scheduled task never started.

The full experiment **failed at its existing time limit**. This is a checked partial result, not a successful completed campaign. No retry, retraining, cutoff extension or new launch was made.

Job: `cas-meta2-20260906094002-39762c47`. Frozen source: `42f9164754312f12850d9b8789c062fa7fb8069f`.

## Actual held-out task results

Each ratio is confirmed correct / actual attempted tasks. An unfinished result stays unknown, not incorrect. Every arm was scheduled for 72 tasks. The common-71 row is an additional matched view, not a replacement for the full assigned denominator.

| Group | CAS before | CAS after | Generic before | Generic after | Rule |
|---|---|---|---|---|---|
| All | 0/72 | 0/72 | 0/72 | 0/72 (1 unfinished) | 71/71 (1 not started) |
| Depth 3 | 0/48 | 0/48 | 0/48 | 0/48 | 48/48 |
| Depth 4 | 0/24 | 0/24 | 0/24 | 0/24 (1 unfinished) | 23/23 (1 not started) |
| Same-depth condition | 0/24 | 0/24 | 0/24 | 0/24 | 24/24 |
| Changed wording | 0/24 | 0/24 | 0/24 | 0/24 | 24/24 |
| Deeper calls | 0/24 | 0/24 | 0/24 | 0/24 (1 unfinished) | 23/23 (1 not started) |
| Common 71 completed cases | 0/71 | 0/71 | 0/71 | 0/71 | 71/71 |

The two missing outcomes are both in case 45, at depth 4: generic-trained unfinished, rule not started. All 72 private references and all 358 saved arm outcomes were checked. Seventy-one cases have all five outcomes; case 45 has its reference and three saved neural outcomes. CAS has a complete 72-task negative result despite the partial campaign.

| Arm | Scheduled | Attempted | Saved outcomes | Rejected | Executed | Known post-start failure | Unfinished | Not started | Correct |
|---|---|---|---|---|---|---|---|---|---|
| CAS before | 72 | 72 | 72 | 72 | 0 | 0 | 0 | 0 | 0 |
| CAS after | 72 | 72 | 72 | 59 | 12 | 1 | 0 | 0 | 0 |
| Generic before | 72 | 72 | 72 | 72 | 0 | 0 | 0 | 0 | 0 |
| Generic after | 72 | 72 | 71 | 53 | 14 | 4 | 1 | 0 | 0 |
| Rule | 72 | 71 | 71 | 0 | 71 | 0 | 0 | 1 | 71 |

The 12 CAS and 14 generic trained executions all returned wrong task answers. A completed execution or valid trace is not a correct answer. Both untrained candidates were rejected on all 72 tasks.

## Binding, child choices and first recorded errors

The verifier table uses **correct / incorrect / unknown** for each metric; scheduled denominator is 72. A failure before a final verifier can leave component correctness unknown even where the complete-task result is known to be unsuccessful.

| Arm | Attempted | Input binding C/I/U | Procedure C/I/U | Dependencies C/I/U | Complete trace C/I/U |
|---|---|---|---|---|---|
| CAS before | 72 | 0 / 72 / 0 | 0 / 72 / 0 | 0 / 72 / 0 | 0 / 72 / 0 |
| CAS after | 72 | 12 / 59 / 1 | 0 / 71 / 1 | 0 / 71 / 1 | 12 / 60 / 0 |
| Generic before | 72 | 0 / 72 / 0 | 0 / 72 / 0 | 0 / 72 / 0 | 0 / 72 / 0 |
| Generic after | 72 | 14 / 53 / 5 | 0 / 67 / 5 | 0 / 67 / 5 | 14 / 57 / 1 |
| Rule | 71 | 71 / 0 / 1 | 71 / 0 / 1 | 71 / 0 / 1 | 71 / 0 / 1 |

The next table measures literal matching in **all 72 saved selected actions**, including the unstarted rule action. These are names and input sites, not semantic correctness of executed tasks. Equivalent renaming can fail this literal check.

| Arm | Observation binding | Named input sites | Named child sites |
|---|---|---|---|
| CAS before | 0/72 | 0/1047 | 0/216 |
| CAS after | 13/72 | 122/1047 | 7/216 |
| Generic before | 0/72 | 0/1047 | 0/216 |
| Generic after | 20/72 | 196/1047 | 15/216 |
| Rule | 72/72 | 1047/1047 | 216/216 |

The rule's 72/72 literal score does **not** mean it executed 72 tasks. The table includes the sealed choice for its unstarted case.

For completed wrong executions, the first recorded trajectory difference has these categories. Categories can overlap within a single case, so totals are not failed-task counts.

| First recorded difference | CAS (12 completed wrong) | Generic (14 completed wrong) |
|---|---|---|
| Wrong input binding | 7 | 5 |
| Wrong child procedure | 4 | 8 |
| Early return | 1 | 1 |
| Wrong output binding/value | 1 | 2 |
| Wrong CJT | 1 | 1 |

Other failure boundaries remain separate: CAS had 59 pre-execution rejections and one known post-start failure; generic had 53 rejections, four known post-start failures and one deadline-unfinished attempt. The receipt retains the rejection reason for each case.

The known post-start failures are CAS case 19 and generic cases 32, 51, 66 and 71. They retain the exact runtime error `repair cannot open without a durable distinct ^6 round trip`; this is not a pre-execution model rejection. Generic case 32 first disagrees with the reference at committed RUN index 3. The other known failures have no difference in their available committed prefix; that does not establish correctness of later missing work.

The unfinished generic case 45 first differs from the independently checked private reference at committed RUN index 2. Its next uncommitted sealed node is 37; those are different facts. No last CPU/GPU instruction or cause of the delay is inferred.

Per-case evidence is in [the partial audit receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_partial_native_001/run_001/partial_native_receipt.json>) under `diagnostics.rows`: all 360 assigned slots retain their task ID, arm, action, evidence directory, comparison source, boundary and available first difference. The receipt also gives every metric by depth and condition. These are first **recorded** differences, not proof of the earliest causal neural decision.

## Native work and evidence checks

For a smaller audit view, [the first-error CSV](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_report_001/first_errors.csv>) contains all 360 scheduled rows with 17 checked columns, including action hashes, full available differences and exact evidence paths. Its SHA256 is `6cf5a2af784bd04b5b9539a3128f55f30c0edc2d689a69cbecd0be1b9f2a9d72`. The unstarted rule row labels its evidence directory as uncreated, not recorded. [The export receipt](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_report_001/first_errors_export_receipt.json>) binds the round-trip field checks to the partial-native receipt; this export performs no new scoring.

| Arm | Committed native runs | Reserved policy units | Compute complete? |
|---|---|---|---|
| CAS before | 0 | 0 | Yes, for recorded attempts |
| CAS after | 177 | 12744 | No; lower bound |
| Generic before | 0 | 0 | Yes, for recorded attempts |
| Generic after | 240 | 17280 | No; lower bound |
| Rule | 820 | 59040 | Yes, for recorded attempts |

These are policy reservations and recorded native runs, not FLOPs or dollar charges. Trained totals include available committed prefixes. The generic total includes the separately checked 37-run/2,664-unit timeout prefix; common-71 generic work is 203 runs/14,616 units. Unknown failed-tick work is not assigned a fabricated value. Rule compute completeness refers only to its 71 actual attempts.

The schema pass checked 2,245 stored traces in 201 closed databases, including separately collected smoke/contract records. It also checked 2,227 exported trace entries; these overlap database traces and must not be added as independent executions. Case 45's 37 committed WAL-view traces were checked separately. These counts do not inflate the 72-task evaluation denominator.

The partial audit completed with process exit 0 and empty stderr at 2026-09-06 11:45:24 UTC. Captured child PID: 68180. Captured wall time: 654.4237456 seconds. Audit status: `PARTIAL_NATIVE_EVIDENCE_CHECKED`; `campaign_completed=false` and `native_evaluation_completed=false`.

Receipt SHA256: `bc700054e18dad6de9e2516f441adccdfac0a9ace25a39fd0fce6a0879d37f4f`.
Capture receipt SHA256: `2be450826c3d91c8671d8fe06094e2d48427f75a15918a22a853027f55c55696`.
Training recount SHA256: `452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76`.
Original packet SHA256: `f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799`.

Twenty pure partial-report/boundary tests passed, including an independent repeat. These narrow tests supplement, not replace, the actual saved-evidence audit. See [the exact commands and raw process outputs](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_partial_native_001/README.md>).

## What was trained and what the splits test

| Partition | Tasks | Depth 1 | Depth 2 | Depth 3 | Depth 4 |
|---|---:|---:|---:|---:|---:|
| Training | 896 | 128 | 384 | 384 | 0 |
| Validation | 96 | 32 | 32 | 32 | 0 |
| Test | 72 | 0 | 0 | 48 | 24 |

The exact original 256 practice records were appended only to the new 640-record training base. Their 128 pairs stayed together. The independent recount checked all 8,837 program exclusions and unchanged validation/test bytes. Training received its eight declared public input files, not private test targets. All 360 comparison choices were sealed before the recorded private-target opening.

The test contains 24 related triplets, not 72 independent structures:

- Same-depth: 24 unseen depth-3 program graphs and fresh observations, with familiar wording combinations.
- Changed wording: the same 24 depth-3 graphs and observations, with a wording shift.
- Deeper calls: 24 paired unseen depth-4 graphs using the paired observations.

These jointly test new instances and new program combinations; they do not isolate a fresh-instance-only effect on familiar programs. The condition and depth tables overlap and must not be added. There is no held-out depth-1 or depth-2 native task group.

## Learning curves and selected candidates

Both families completed 200 epochs and 11,200 optimizer steps. Checkpoint selection used validation only. CAS selected epoch 200; generic selected epoch 180, not its final epoch 200.

| Validation depth | CAS before → selected | Generic before → selected |
|---|---:|---:|
| 1 | 0/32 → 26/32 | 0/32 → 26/32 |
| 2 | 0/32 → 0/32 | 0/32 → 0/32 |
| 3 | 0/32 → 0/32 | 0/32 → 0/32 |

These are exact freely generated program-plus-input matches, not native task answers. Both learned shallow validation selection in the saved records; neither produced a full exact validation program at depths 2 or 3. The generic final checkpoint scored 22/96, compared with its selected checkpoint's 26/96.

The new 24-example training probe is part of this run's training set, not the earlier familiar-program experiment. At epoch 200 it scored CAS 22/24 and generic 24/24. Every measured epoch is preserved: epoch 0, epoch 1, then each tenth epoch through 200. No intervening generation measurements were invented.

See [all depth curves and checkpoint identities](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_learning_curve_001/run_001/learning_curve.md>) and [machine-readable curves](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_learning_curve_001/run_001/learning_curve.csv>). The rendering check covered all 1,980 curve CSV fields, 60 checkpoint CSV fields and 708 Markdown data cells; 19 pure tests also passed.

Selected checkpoint hashes:

- CAS: `bf709539d8a462fe73909553659ad046305e75428a15d80e83124bc28ee84b46`.
- Generic: `53e2acdd4635d843210a7aa0a5b194e395f57c0b7f71ca59b1a64dbeae4ca532`.

The [audit file index](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_report_001/AUDIT_FILES.md>) lists the full local addresses for all six initial/selected/final checkpoints.

## Matched conditions and compute

Both candidates used the same data/order, 200 epochs, batch 16, AdamW learning rate 0.001 and weight decay 0.01, output grammar, permitted problem information, and unchanged executor/verifier. The frozen construction copies the common decoder/binding/copy parameters before training. The generic encoder's feed-forward width is 200, with no disconnected filler parameters.

Parameter counts: CAS 183,852; generic 183,892 (40 apart, approximately 0.02176%). Equal step counts and similar parameter counts do not establish equal wall time or FLOPs. The hand-written rule control has the same permitted observations but different prior machinery; it is not a learned model.

Recorded AWS CUDA environment: NVIDIA RTX PRO 4500 Blackwell Server Edition, PyTorch 2.11.0+cu128, CUDA 12.8, Python 3.12.3. No T4 was used. No neural training, inference or tensor loading was performed locally during these reviews.

| Recorded time | Seconds |
|---|---:|
| CAS training steps | 1628.876326619009 |
| Generic training steps | 240.20945939201647 |
| Whole training stage | 2596.375743874 |
| Native evaluation before deadline error | 2700.688235096 |

These are recorded elapsed times, not FLOPs or an independent neural arithmetic replay. CAS's training-step time was about 6.78 times the generic time in this run.

## Deadline, collection, cleanup and cost

The native evaluation ran from 2026-09-06 10:32:26.634120 UTC to 11:17:27.322357 UTC. Its inner 2,700-second limit raised `TimeoutError: 1 (of 72) futures unfinished`. The process returned 1. Its outer wrapper's `timed_out=false` does not cancel the inner deadline. The launcher's later `V7_REMOTE_CAMPAIGN_COMPLETION_INVALID` is a secondary completion check, not the underlying failure.

The missing case is 45, a depth-4 deeper-call task. Its generic-trained arm saved 37 committed runs/traces from a selected 39-run program, reserving at least 2,664 policy units. The next sealed run is node 37, CJT B, reading node 0 in frame 13. This is a position in the selected program, not proof of the worker's last instruction or why it stalled. Final output, failed/unfinished tick compute and underlying cause remain unknown. The case's rule arm never started.

The separate prefix check used a copy of the original SQLite database plus WAL; original DB/WAL/SHM hashes stayed unchanged. It created a closed derived database and verified its schema and execution records. “Committed” means present in the collected transaction view, not a new power-loss durability test. Ten prefix tests passed, including an independent repeat.

The packet contains all 2,940 original produced files plus its collection receipt: 2,941 ZIP members, 131,895,861 compressed bytes. No original file was omitted. Complete collection of produced bytes is not completion of the experiment.

AWS termination was confirmed and a separate read-only provider check passed all seven cleanup checks: instance terminated; job volumes, security group, worker profile, worker role, timer role and schedule absent. Results remain in the local packet and the S3 bucket under its existing seven-day lifecycle.

The launcher estimate is $4.339111523370370370370370370 for compute, EBS and public IPv4, excluding S3, transfer, taxes and other fees; it is not an invoice. A later conservative read-only observation gives $4.3715 compute-only plus the pre-existing $1 planning allowance = $5.3715, still within this job's $7 reservation. That later observation is not an exact termination timestamp.

Canonical ledger revision 11 remains unchanged: $400 campaign cap, $78 reserved, $322 unreserved. The $7 job reservation remains held; no automatic refund or additional launch was made.

## Reproduction, history and limits

Frozen experiment source: `42f9164754312f12850d9b8789c062fa7fb8069f`. The audit repeatedly matched all 603 source files and 316 protected baseline files against the source archive and Git. The accepted baseline remains `0917267b1354e5d036263eaa6ba9a7197eafb776`.

The separate clean-source check recorded 1,908 passing test functions and 356 passing subtests, with 11 skipped, 2 deselected and one intentional duplicate-ZIP warning. These are distinct count types, not 2,264 independent tests. It used an existing Python 3.14 environment, not a new wheel installation.

The full-success reviewer was not run on this failed packet. The separate partial reviewer checks saved outcomes without weakening full-success requirements. Local checks hash checkpoint bytes but do not load tensors or independently repeat neural calculations. Known-fixture GPU smoke and four original GPU contract tests are separate logged gates, not additional held-out successes; they are not folded into the 72 tasks.

The META-3 issue at `63f5b421` is closed as auditor-reported checkout line-ending conversion: converted checkout 518 passed/13 failed, byte-preserving checkout 531 passed. The checker-defect and missing-committed-file interpretations are withdrawn. Original reports remain preserved; newly reported auditor logs and exact mismatch hashes were not supplied and were not invented. Scoped byte-preserving attributes and pre-test manifest verification were added separately, without changing frozen source, accepted hashes or checker logic.

Historical experiments remain separate:

- Earlier familiar-program fit: 0/24 → 24/24; not unseen-task evidence.
- Earlier held-out composition: CAS 0/72, generic 12/72, rule 72/72.
- Recovered v6 evaluation: CAS 0/72 → 0/72, generic 0/72 → 0/72, rule 72/72. Recovery reused sealed predictions; it was not fresh training.

See [historical evidence](<C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/prototype_v7_report_001/HISTORICAL_EVIDENCE.md>) for their own source and receipt identities.

No automatic acceptance, merge, new paid run, CAS-specific advantage, general reasoning capability, AGI or production-readiness claim follows. The full CASformer/CNCM vision remains unfinished. This report closes the current run with its actual partial results; it does not redefine that larger goal as complete.
