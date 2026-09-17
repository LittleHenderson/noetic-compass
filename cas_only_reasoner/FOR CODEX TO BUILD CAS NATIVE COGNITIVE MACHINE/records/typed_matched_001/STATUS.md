# Matched teaching study

Status at **2026-09-17 11:45:51 UTC: 6/6 arms completed and independently verified; study execution finished**.

See [the completed comparison](MATCHED_STUDY_RESULT.md). Component-first teaching led in two paired seeds and tied in one: mean family-balanced final transfer 3.7423% versus 0.3472%, and normalized learning-curve score 2.4788% versus 2.0544%. Absolute transfer was poor: 4/177 versus 1/177 correct across three runs of the same 59-question panel, down from 21/177 in each method before teaching. All three retention comparisons remain unassessed under the preset competence rule; all six raw probe scores fell. A useful or general learning advantage is not established.

Independent audit: PASS for 3,504 collected files, 2,364 artifacts, 2,382 required objects, 18 checkpoint reconstructions, 12 exact replay updates and three paired initializations. All six lifecycle receipts confirm compute cleanup. The latest EC2 query returned the final two instances terminated; four older IDs were not returned. Campaign budget: revision 84, $501 reserved, $4,499 unreserved; six $7 reservations for this study, no retries. Private evidence archives retained.

Next: diagnose the unfamiliar-graph collapse, zero-score question kinds and forgetting from saved outputs, then freeze a targeted correction and fresh matched test. The full CNCM goal remains active and incomplete.

## Frozen protocol and historical observations

The observations below preserve their original timestamps and do not describe current running jobs.

The study compares component-first teaching with mixing the same component/whole lessons. It holds the learner, initial state per seed, information and counted work fixed. This measures one teaching-order contrast, not general CAS architecture superiority.

- Three paired model seeds: 20260917, 20260918, 20260919.
- Full main course per arm: eight kinds, 1,152 presentations, 160 updates.
- Speed/transfer: 59 development questions at updates 0, 40, 80, 120, 160.
- Retention: 96 no-support probes before/after 16 other-question teaching updates.
- Validation: two independent last-main-update replays; 178 total actual updates.
- Six sequential jobs, $7 reservation each, $42 maximum, no automatic retries.

Worker source: `e6bdf30524c0cea3da05e8c39899ca6fc059553d`.
Frozen admission publication: `44553c76`.
Study record: `admission_001/study.json`, SHA-256 `154dee19e678aa3520b47528100642d73303c836230abcb7db6bc02d242a5099`.
Archive SHA-256: `2feff28c52fbbe5a230d4f1f32c936c9d9434bc514d5cf92d998fc917cbc72fc`.
Pure tests: **166 passed**. These tests are preparation evidence, not learning results.

First job at launch: `cas-meta2-tmat-20260917072721-e6bdf305-a-20260917`.
Instance at the 07:33:48 UTC launch observation: `i-0dcbfc8321769d483`, then `running`.
The supervisor is `execute_study.py`; it stops on a failed/incomplete arm or cleanup failure. The frozen schedules and endpoints do not change after scores arrive. `live_readonly_monitor.py` records scoped provider observations without mutations.

Campaign ledger after first reservation: revision 79, $466 reserved, $4,534 unreserved of $5,000. The actual hourly compute quote is $2.52; reservations are bounds, not invoices.

The initial automatic approval rejection concerned private-package destination trust. `destination_verification_001.json` binds the user's supplied handoff account statement to live AWS STS and prior-bucket ownership checks. The resubmitted identical bounded launch was accepted; the block is resolved. No new budget reservation or provider launch occurred during the rejected invocation.

Earlier completed-course results and the negative three-seed recurrence result remain preserved. No matched learning advantage is established yet.

## 2026-09-17 07:43:35 UTC observation

The first instance remains running. All 564 initial input checks and cache checks have finished; the worker entered `initial_predictions` at 387.83 worker seconds. Optimizer updates and completed comparison results are not yet reported. See the timestamped record in `live_observations/`.

The supplementary public-only work audit independently derived identical phase counts for both frozen schedules: 71,922 core forward calls, 11,482 slot forwards, 2,951 predictions, 1,296 training presentations and 178 updates per complete arm. Main teaching remains 17,178 core calls and 160 updates. `independent_work_plan_001.json` has SHA-256 `3e4f31ddb56c1b8088fc7918fecb57a09fcab96ad75e7696d464a99dba3c6205`.

This audit was added during the first running arm to verify the existing work contract. It introduces no teaching change or new scoring endpoint. These are expected counts; acceptance still requires matching measured counters from completed worker evidence.

## 2026-09-17 07:50:51 UTC observation

The first arm has entered actual training and reports **20 of 160 main optimizer updates completed** at 787.10 worker seconds (`main_training`, progress index 53). Both before-teaching evaluations have finished. The same instance remains running and the supervisor session is live. This is partial execution evidence; 0/6 complete arms have been accepted and the paired outcomes remain pending. Five predeclared jobs are queued; no retry or schedule change has occurred.

## First arm accepted; control started

The first arm completed in 1,673.87 worker seconds. Its lifecycle reports `completed_deliverable: true`, all 397 required objects present, and confirmed termination of `i-0dcbfc8321769d483`. Independent checks verified all 584 collected files, 394 worker artifacts, exact declared work, 49 loaded project modules, three checkpoint reconstructions and both byte-identical last-update replays.

The control job `cas-meta2-tmat-20260917072721-e6bdf305-m-20260917` is running on `i-025f80988385e8af2`, observed at 08:14:35 UTC. Four further predeclared jobs remain queued. The original controller continues sequentially, without a retry or experiment change.
