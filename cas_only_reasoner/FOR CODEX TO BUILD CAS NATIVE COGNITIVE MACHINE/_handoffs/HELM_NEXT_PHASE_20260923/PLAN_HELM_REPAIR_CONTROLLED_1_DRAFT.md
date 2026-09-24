# HELM-REPAIR-CONTROLLED-1: named AWS job plan (DRAFT; for the owner's launch approval)

**Status.** `DRAFT`. It is not approved and nothing in it is launched. It is completed and brought to the owner once
the preconditions below have passed. The owner's words (`OWNER_DIRECTION_20260924.md`, item 4): "Prepare the exact
AWS job plan with source, data, starting weights, runs, update/time/dollar limits, stopping conditions, and cleanup.
Bring that named plan to me for launch approval."

## 1. The question

Does the analogy repair (switch ON) make Helm answer analogy questions on unseen 6-node shapes better than the
unchanged Helm, trained the same way, beyond every no-learning rule, without regressions?

## 2. Preconditions (owner direction item 4), with status

| Precondition | Status | Evidence |
|---|---|---|
| OFF preservation | **PASSED** | `OFF_PRESERVED_ON_T4`, research `41071a3f` |
| Enabled-path checks | **OPEN** | The switch-ON smoke: attempt 1 was refused by AWS capacity before launch, $0 compute (`claude/helm-on-launch-20260924` `5715fda0`); the zone decision is with the owner. Also the larger-question T4 checks (below) |
| Larger-question integration | **BUILT, REVIEW RUNNING** | `785c9bd1`; its AWS T4 checks run after the review |
| Evaluation preparation | **DESIGN v0.4 IN REVIEW** | `EVALUATION_DESIGN_v0_4.md` (`7df1923f`); then `hset2_build.py`, its review, and the AWS build printing every cell's W before any model |

## 3. Arms, source and starting weights

| Arm | Code | Starting weights |
|---|---|---|
| **repaired** | the reviewed launch source (currently `70490111`). The worker always builds the switch-ON container (`analogy_focus_comparison=True`, analogy head seeded 20260923) | matched starts: the same seeds as Helm 2.0 (20260917, 20260918, 20260919), whose `initial.pt` sha256 are recorded in `MIGRATION_ON_SHAPES.json`; the 5 analogy-head tensors seeded separately. The A5.5 check confirms this on AWS |
| **unchanged** | the historical Helm 2.0 source `20208c923d41c24614504d4ecc2b289ecb66eda8`, package `package_20208c92` (committed). **No code change is needed** | Helm 2.0's own starts, the same seeds |

**Data and schedule (both arms, identical):**
- the typed course `records/typed_course_001/checks_002/public_course.json` (sha256 `cf7a7181...`);
- the stratified schedule: 10 passes, 147 updates per pass, 1,470 main updates;
- the same held-back panel.

## 4. The owner's choice: how the unchanged arm is obtained

| Option | What runs | Jobs | Expected cost | Ledger reservations | Strength |
|---|---|---|---|---|---|
| **A** | Reuse the 3 Helm 2.0 receipts (trained 2026-09-20/21 on g7.2xlarge) as the unchanged arm | 3 (repaired only) | about $22.50 | 3 x $15 | weakest: the arms ran on different days |
| **C (recommended)** | Re-run `20208c92` for **one** seed (20260917) first, and require its final checkpoint to equal the Helm 2.0 receipt's bit for bit. If it does, reuse the other two receipts; if not, fall back to B | 4 | about $30 | 4 x $15 | proves the old runs are a fair control, at one extra job |
| **B** | Re-run `20208c92` for all 3 seeds, alongside the repaired runs | 6 | about $45 | 6 x $15 | fully controlled |

**Cost basis:**
- Helm 2.0 runs took about 2.9 h each on g7.2xlarge, about $7.50 each.
- The launcher books a fixed $15 per job, and the ledger never refunds.
- The smoke adds one more $15 booking per attempt; attempt 1's booking already stands. The current $60 approval
  covers the smoke plus 3 jobs. Options C and B need more.

## 5. Limits (per job, from the launcher's frozen bounds)

| Item | Value |
|---|---|
| Machine | `g7.2xlarge`, us-west-2; zone placement per the owner's decision |
| Instance lifetime | at most 14,400 s; the guest watchdog powers off at 14,100 s |
| Worker wall time | at most 12,600 s |
| Optimizer updates | at most 1,488 |
| Reservation | $15.00 per job |
| Concurrency | one machine at a time |
| Retries | none automatic |

## 6. Stopping conditions (enforced by `run_on_study.py` or the same rules by hand)

- The smoke must pass before any seed job.
- If any job ends other than delivered, the next job is not launched.
- If spend passes the owner's stated stop before the last job, stop and report.
- Option C: if the reproduction seed does not match bit for bit, do not reuse the old receipts; bring the B decision
  back to the owner.
- Before any TEST reading, the custody manifest check must pass (design v0.4 section 8).

## 7. Reading (fixed before launch)

**The rules.** Design v0.4 section 7 fixes the base claims per arm, `REPAIR_BEATS_UNCHANGED_<cell>`,
`REPAIR_IMPROVES_ANALOGY_6`, and the no-regression gate set (H1, H2, V).

**Also required before any analogy number is read:**
- prereg A5: probe v0.2 on all 18 trained repaired checkpoints;
- the matched-start check.

**Label.** `CLAUDE_BUILT_CLAUDE_CHECKED`, and `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT`.

## 8. Cleanup

- The launcher terminates the instance, and removes its security group, role and instance profile.
- The job's evidence bucket is kept, as the run-evidence rule requires.
- Receipts are committed on the launch branch.
- Checkpoints and results are archived to `D:/tksCAS-archive/`, with three sha256 confirmations, plus a private S3
  copy.
- Every job's measured time and cost are recorded.

## 9. Open before this plan can be approved

- The four preconditions of section 2.
- The owner's choice of option A, C or B, and the matching dollar ceiling.
- The owner's zone decision for g7.2xlarge capacity.
