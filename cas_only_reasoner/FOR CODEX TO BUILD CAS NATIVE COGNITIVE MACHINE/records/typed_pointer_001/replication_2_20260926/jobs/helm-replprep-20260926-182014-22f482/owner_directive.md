OWNER DIRECTIVE — HELM TWO-SEED REPLICATION
Experiment: HELM-CM2X-REPLICATION-2
Date: 2026-09-26

PURPOSE

Repeat the completed HELM 10-versus-20-pass experiment using two additional, predetermined seeds.

The question is:
Does the gain on the harder development questions repeat across different model initializations, and what happens to the other scores?

Do not assume a breakthrough or phase transition.
Do not change the model to make the result more favorable.

AUTHORIZED SCOPE

I authorize the existing Codex coordinator to prepare and execute exactly TWO new 20-pass training jobs:

First:  model seed 20260917
Second: model seed 20260919

Run them sequentially: one experiment GPU machine at a time.

Use the existing DeepSeek reviewer for one focused public-plan/source-difference check and the final public-results review, if that reviewer is available under its established limits. Do not create a new agent team or make Claude availability a dependency.

This directive does not authorize:
- a 4x or 8x training extension;
- a new model architecture;
- CAS-CLOSED-LOOP experiments;
- website migration changes;
- model promotion or production deployment;
- automatic retries.

1. USE THE SUCCESSFUL EXPERIMENT AS THE REFERENCE

Successful completed job:
cas-meta2-tpntr-20260926054903-c45f775f-m-20260918

Successful source commit:
c45f775f225dd06cc20cdf313f0a0398486e0d61

Successful admission commit:
3fee35e9c6da7146f252a29018522709ce78da1f

Reference source-package SHA256:
38761e9595c321eeab09a368a699a993b7db7616c4f2f15fb716dc78a9066119

Reference package-manifest SHA256:
f083fb087ce2eac2394b81856a2aea8f239e7b7d327d27a71160e4dcb6bc2b5d

Public closeout:
D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination/HELM_CORRECTED_RERUN_CLOSEOUT_20260926.json

Reference measurements, seed 20260918:

                         Pass 10    Pass 20
Hard development         8/59       17/59
Held-back course         115/127    111/127
Full course              502/564    487/564
Directly trained subset  322/358    315/358

The completed reference has 2,940 main training updates and 128 required artifacts collected and verified.

Preserve this run, its source package, checkpoints, measurements, reservations, and cleanup evidence unchanged.

Do NOT rerun seed 20260918.
Do NOT confuse older R17/R19 results from different experiments with these new jobs.

Treat seed 20260918 as the already-observed exploratory result that motivated this replication. Report the two new seeds separately before summarizing all three.

2. FREEZE THE PLAN BEFORE EITHER NEW TRAINING JOB

Write and commit one replication plan covering BOTH seeds before reading either new seed’s results.

Keep unchanged from the successful reference:

- model architecture and dimensions;
- model initialization procedure, except the named model seed;
- training data and data split;
- batch construction and ordering;
- all other seeds, including data and encoder seeds;
- AdamW optimizer and all its settings;
- learning rate 0.003;
- CONSTANT_AS_HELM_1_0;
- planned_main_updates unset / None;
- 20 training passes;
- 147 main updates per pass;
- pass 10 at 1,470 main updates;
- pass 20 at 2,940 main updates;
- evaluation questions and scoring;
- all existing required intermediate evaluations;
- retention, interference, replay, and other required checks;
- required checkpoint and evidence delivery.

Preserve the successful deadline-routing correction.
Do not reintroduce the shorter practice-study timeout.

Use the same pinned software environment and GPU/instance configuration where available. Verify and record them.

If a material environment difference is unavoidable, disclose it before spending and do not call that run an exact replication.

Both new models start from scratch with their own designated seed.
Do not initialize them from the trained seed-20260918 checkpoint.

If the admission wrapper hardcodes seed 20260918, change only the experiment-specific seed/job handling needed to admit the two new seeds. Do not change the scientific training or scoring code.

Document every allowed difference:
model seed, new job identity, output destinations, and prospective resource/admission records.

3. DEFINE THE COMPARISON NOW

Primary result for EACH new seed:

hard-development correct at pass 20
MINUS
hard-development correct at pass 10

Compare each seed with ITS OWN pass-10 result.

Do not compare every seed’s final score against the old seed-20260918 baseline of 8/59.

Report:
- correct/59 at pass 10 and pass 20;
- percentages;
- change in correct answers;
- change in percentage points.

Secondary results:
- held-back course correct/127;
- full course correct/564;
- directly trained subset correct/358;
- excluded subset correct/79, reported separately;
- the registered retention measurements;
- the existing training-loss summaries, with their exact definitions;
- runtime and resource use.

Do not label the retention-before/after interference test as a pass-10/pass-20 retention comparison.

Freeze these interpretation rules:

- Both new seeds improve on the hard development set:
  "The direction of the hard-development gain repeated in both additional seeds."

- Only one improves:
  "Mixed replication."

- Neither improves:
  "The original hard-development gain did not repeat in these additional seeds."

Always report magnitude and any regressions alongside that label.

A gain of one question and a gain of nine questions are not equivalent results.

These labels do not establish statistical significance, a critical-mass threshold, general intelligence, or CAS-specific advantage.

The 59-question set is a previously examined development set, NOT a new untouched final test. More seeds test initialization robustness; they do not create new independent test environments.

Do not select the best checkpoint, best seed, or best-looking subset.
Do not alter the second seed’s plan after seeing the first seed’s score.

If the first job completes correctly, run the second even if its scientific result is disappointing.

4. FINITE NEW BUDGET

I authorize a NEW maximum of USD 45.00 for this two-seed replication campaign.

This is separate from all historical studies and reservations. It does not reuse or refund the previous USD 21.50 allocation.

Allocation:
- up to USD 20.00 all-services bound for seed 20260917;
- up to USD 20.00 all-services bound for seed 20260919;
- up to USD 5.00 shared preparation, focused validation, review, and final results collection.

These allocations are ceilings, not spending targets.

Before each paid job, record:
- actual current provider price;
- instance type and region;
- maximum runtime;
- all-services cost bound;
- startup and required evaluation time;
- storage, evidence transfer, and cleanup allowances;
- the remaining campaign balance.

Use the measured runtime of the SUCCESSFUL 20-pass job for forecasting, not the failed short-deadline attempt.

Price and disclose the evidence-retention period and any continuing storage obligation. Do not delete evidence automatically to meet the cap.

No paid call or helper job may sit outside the campaign accounting.

Preserve historical ledger entries and failed-job reservations unchanged. Distinguish reservations and estimates from actual bills.

If the complete plan cannot fit the stated caps, stop before new spending and report the exact shortfall and smallest workable finite adjustment.

Do not ask for routine approval again when the plan fits this directive.

5. PREPARE ONCE, THEN RUN THE TWO JOBS

First reconcile current public records and task ownership.
Do not duplicate a job or overwrite another agent’s work.

Use an isolated working branch and the exact public source inventory required for this experiment.

No blanket repository/history searches.
No access to protected Q3 material, answer keys, salts, credentials, or unrelated private files.
Use the established protected scoring path without exposing its contents to coding/review agents.

Reuse valid unchanged test evidence tied to the successful source.
Run the focused checks needed for changed seed/admission handling and relevant deadline, update-count, checkpoint, and artifact requirements.

Do not reopen a broad scientific audit.
Do not repeat expensive unchanged tests without a concrete reason.

Do not edit frozen graders or their criteria to make a check pass.

Keep sustained tests, builds, and model computation off the RAM-constrained laptop, using the established bounded AWS workflow.

Create unique job IDs, receipt directories, and reservations for both seeds.

Before each launch verify:
- exact source and package identities;
- the registered seed;
- all normal admission checks;
- canonical ledger access;
- sufficient remaining budget;
- no conflicting experiment job;
- working time limits and independent shutdown controls.

Production website instances are not HELM experiment jobs.
Use the reviewed exact production-resource allowlist when checking conflicts. Do not blanket-ignore arbitrary instances, stop web services, or change their permissions.

LAUNCH seed 20260917 when its checks pass.

After it finishes, collect its evidence and verify experiment compute cleanup.

Then LAUNCH seed 20260919 under its already-frozen plan, provided operational checks and budget still pass.

Automatic retries remain zero.

If a job fails operationally, preserve everything and diagnose the exact failure. Do not silently retry, substitute another seed, or discard the failed attempt from the report.

6. PRESERVE THE FULL EVIDENCE

Require the same 128 evidence requirements as the successful reference, with identifiers and hashes appropriate to each new job.

Do not lower the required count to hide missing outputs.

Preserve:
- pass-10 model/checkpoint state and metadata;
- pass-20/final state and metadata;
- both endpoint measurements;
- training/update records;
- required retention, replay, and other checks;
- source/package identities;
- receiver verification;
- cost and cleanup records.

Do not automatically promote pass 20 over pass 10.

Keep both states because harder-problem performance may improve while other performance declines.

7. MAKE PROGRESS VISIBLE

Use the existing working Codex/DeepSeek coordination channel.

During active hands-on work, publish a useful status at least every five minutes:
- current task and seed;
- work completed since the previous update;
- current blocker, if any;
- next action;
- whether cloud compute is active;
- job ID and receipt location when available.

Do not report an application process or an empty heartbeat as proof of training.

The previous completed HELM monitor was recorded as deleted. Check whether a newer suitable monitor exists. Reuse it if present; otherwise establish ONE read-only five-minute monitor for these two jobs.

A monitor must never launch, retry, or alter a job.
Do not claim monitoring is active without verifying its actual configuration and first check.

End the replication monitor after both jobs reach recorded terminal states. Do not kill active work merely to end a monitor.

8. REPORT LAUNCHES AND THE ACTUAL RESULTS

After each launch, report:
- seed;
- exact source and admission commit;
- package hash;
- job ID;
- instance ID;
- launch time;
- observed state;
- reservation and hard cost bound;
- receipt location.

Distinguish "instance running" from "training started."
Training has started only when worker progress confirms it.

After both jobs finish, return this table:

Seed | Hard 10 | Hard 20 | Change | Held-back 10 | Held-back 20 | Course 10 | Course 20
20260917
20260918 — existing exploratory reference
20260919

Also report:
- the mean hard-score change across the TWO NEW seeds;
- each new seed’s result separately;
- an explicitly descriptive three-seed summary;
- trained-subset and retention results;
- losses and their definitions;
- completed main updates;
- evidence verified/required;
- runtime;
- reservations versus actual costs available;
- compute cleanup and retained storage;
- all failures, deviations, and unresolved limits.

No "dragon awakened" claim based only on completed jobs or passing software tests.

The useful outcome is an honest answer:
Did the harder-question improvement repeat, by how much, and what did it cost elsewhere?

Proceed with the bounded two-seed replication once this plan is frozen and the normal launch checks pass.