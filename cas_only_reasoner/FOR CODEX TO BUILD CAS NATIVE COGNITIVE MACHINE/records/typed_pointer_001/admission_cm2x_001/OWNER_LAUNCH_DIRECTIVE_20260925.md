# CODEX DIRECTIVE — COMPLETE HELM CRITICAL-MASS + CAS-CLOSED-LOOP AWS LANES

**Owner:** Little Henderson  
**Role:** Codex is the sole active implementation and AWS launch operator for this bounded completion round.  
**Heartbeat:** At START, END, every substantive milestone, and at least every 120 seconds while active.  
**Goal:** Do actual execution now. Do not stop at plan-only review.

## 1. OWNER AUTHORITY

The owner directly requests completion of:

1. **CAS-CLOSED-LOOP-1 AWS validation**
2. **HELM critical-mass longer-training experiment**

This authority remains subject to finite prospective budgets, one GPU machine globally, no automatic retry, no protected Q3 answers, no salts, no sealed outputs, no credential disclosure, no historical-result rewriting, no silent admission bypass, and no hidden-grader access.

Do not forge Claude/DeepSeek/owner identity.

## 2. CURRENT CAS-CLOSED-LOOP-1 STATE

Current pushed branch:
`codex/cas-closed-loop-1-recovery-20260925`

Current status commit:
`318b22ad01304f80ed0f539420792cc951fe297a`

Tested implementation commit:
`8f55cc3a462e438bcf706d7b64ddf9171d218039`

Known local engineering evidence:
- 43 integration tests passed
- 4 artifact-integrity tests passed
- output `x=3`
- 12 host entries
- 18 native events
- replay parity demonstrated
- negative controls passed
- no AWS validation yet
- no learned-model proof
- no CAS-specific advantage proof yet

## 3. LANE A — CAS-CLOSED-LOOP-1 AWS VALIDATION

### Goal
Run the same bounded public engineering acceptance on AWS.

This is an **AWS engineering validation**, not a learned-model experiment.

### Required prelaunch freeze
Before launch, record:
- exact source commit
- exact branch
- exact test command
- exact runtime/witness command
- instance type
- region/AZ
- wall limit
- all-services maximum cost
- watchdog/cleanup mechanism
- retry count = 0
- runner identity
- output/receipt destination
- source/package hashes

Prefer a CPU instance if GPU is not technically required.

### Required AWS execution
At minimum execute:
- `research/cas_closed_loop_1` focused tests
- closed-loop witness
- replay/restart path
- tamper/negative controls already part of the focused suite

Preserve stdout/stderr, test result counts, runtime result, evidence bundle, artifact hashes, instance ID, region, start/end UTC, cost upper bound or actual cost, and cleanup/termination confirmation.

### Required success report
Report exactly:
- tests passed/failed/errors
- witness output
- host entries
- native events
- replay status
- negative-control status
- source commit
- instance ID/type
- cost
- cleanup status

Do not call this model intelligence, generalization, or CAS superiority.

### Blocked case
If the current launcher has a hard-coded immutable Claude-only runner identity that cannot lawfully be amended prospectively, return:

`CAS_RUNNER_BLOCKED`

with exact file, exact field, exact failing check, and smallest lawful prospective fix.

Do not bypass it.

## 4. LANE B — HELM CRITICAL-MASS EXPERIMENT

### Scientific question
Does the hard new-problem score improve materially as training amount increases?

Target cumulative main updates:
- 1x = 1,470
- 2x = 2,940
- 4x = 5,880
- 8x = 11,760

### Keep fixed
Where scientifically required, keep fixed:
- architecture
- seed `20260918`
- data split
- teaching order
- hard 59-item panel
- 127-item unseen-similar set
- 564-item normal-course set
- 358-item trained set
- 96-item retention set
- scorer
- optimizer law
- loss law
- failure accounting
- readout rule

Do not tune on the hard test.

## 5. REQUIRED HELM PREFLIGHT BEFORE 2x

### H1 — Prefix optimizer equality
For steps `1..1470`, show that learning rate, betas, epsilon, weight decay, batch size, loss scale, and update order are identical between 1x and the proposed longer-training run.

If any differ due to total-horizon scheduling, then “training amount only” is false. Fix prospectively before launch.

### H2 — Checkpoint / continuation identity
Prove the continuation state contains or preserves:
- exact optimizer update count
- model state
- optimizer state
- data/sampler cursor
- RNG state
- source identity
- seed identity

If exact continuation from the saved R18 state is not supported, do **not** fake continuation. Use the prospective from-scratch 20-pass 2x design instead.

### H3 — R18 identity diff
Diff the proposed 2x request/package against R18.

Every scientific field must be identical except:
- training amount / pass count
- job/receipt identity
- prospective resource caps

If more changed, record them and fix or version the experiment.

## 6. 2x EXECUTION PATH

Use the current exact prospective 2x implementation, not stale prose.

Prior work indicated:
- 20 passes
- seed 20260918
- LR 0.003
- no best-checkpoint selection
- first-arm envelope around $20

Verify the current exact commit and package before launch.

Freeze:
- source
- package
- request
- authority/admission
- study record
- instance type
- wall limit
- per-job cap
- total all-services cap
- cleanup
- no-retry rule

Then launch **2x**.

Do not launch 4x/8x until:
- 2x receipt exists
- readout is written
- cleanup/termination is confirmed
- next finite envelope is prospectively frozen

## 7. REQUIRED READOUT PER HELM ARM

For each completed arm, report:
- hard new-problem: correct / 59 and %
- unseen-similar: correct / 127 and %
- normal course: correct / 564 and %
- trained set: correct / 358 and %
- retention: correct / 96 and %
- training loss start
- training loss end
- elapsed time
- actual or conservative cost
- source commit
- checkpoint identity
- instance ID/type
- cleanup confirmation

The decisive curve is:
`hard-new-problem score vs cumulative training amount`

## 8. 4x / 8x RULE

Do not run 4x or 8x under stale 2x caps.

Each extension requires:
- prospective versioned limits
- finite cost envelope
- checkpoint identity
- same scientific controls
- same scorer/panels
- one-GPU sequencing
- no auto retry

If one-GPU limits require multiple sequential segments, preserve the exact cumulative chain.

## 9. CONCURRENCY ORDER

1. Check if an AWS/GPU job is already active.
2. Do not duplicate or preempt an active GPU job.
3. If CAS AWS validation is CPU-only, it may run without interfering with HELM GPU work.
4. Only one GPU machine globally.
5. After every paid GPU job, collect result, verify receipt, verify cleanup/termination, then start the next GPU job.

## 10. HEARTBEAT

Append to the existing Codex heartbeat path at least every 120 seconds while active.

```json
{
  "utc": "...",
  "status": "START|ACTIVE|BLOCKED|LAUNCHED|RESULT|END",
  "current_task": "...",
  "last_completed": "...",
  "blocker": null,
  "next": "..."
}
```

Do not go silent during active work.

## 11. REQUIRED COMPLETION ORDER

1. Freeze CAS AWS engineering validation.
2. Freeze HELM 2x preflight/admission.
3. Run CAS AWS validation if it is CPU-only and non-conflicting.
4. Launch HELM 2x.
5. Collect 2x readout and cleanup receipt.
6. Freeze/launch 4x if scientifically valid and budgeted.
7. Collect 4x readout.
8. Freeze/launch 8x if scientifically valid and budgeted.
9. Collect 8x readout.
10. Commit and push all receipts/results.
11. Produce final comparison table and claim boundaries.

## 12. STOP CONDITIONS

Stop only for a concrete blocker such as failed admission, missing required AWS access, incompatible runner identity, budget cap conflict, source identity mismatch, invalid checkpoint law, active conflicting GPU job, provider capacity failure, or custody requirement that cannot lawfully transfer.

Do not stop for cosmetic cleanup, wording, broad architecture discussion, optional future work, or minor documentation polish.

## 13. FINAL STATUS FORMAT

```text
STATUS:
ACTIVE | BLOCKED | COMPLETE

CAS AWS:
- source:
- instance:
- tests:
- witness:
- replay:
- cost:
- cleanup:

HELM 2x:
- source/checkpoint:
- hard 59:
- unseen 127:
- normal 564:
- trained 358:
- retention 96:
- loss:
- elapsed:
- cost:
- cleanup:

HELM 4x:
...

HELM 8x:
...

BLOCKERS:
...

NEXT:
...
```

Do the work now. Do not return only a plan.
