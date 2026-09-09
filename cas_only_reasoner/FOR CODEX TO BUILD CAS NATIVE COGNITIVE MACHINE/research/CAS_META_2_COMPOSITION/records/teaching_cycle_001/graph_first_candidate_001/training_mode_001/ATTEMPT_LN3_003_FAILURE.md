# Graph-first ^6 — ln(3) diagnostic AWS attempt 003: FAILED (AWS visibility error; instance was live; fix prepared)

Status: **AWS_GRAPH_TRAINING_LN3_DIAGNOSTIC_FAILED.** The run aborted at the
AWS layer ~30 s after launch — before the worker ever started — on a
transient EC2 visibility error, not on any neural computation. The instance
was actually RUNNING; it has been terminated in a bounded hygiene pass. The
measurements remain outstanding; a replacement needs a new owner
authorization and one new `$4.00` reservation (no automatic retry).

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-ln3-diagnostic-20260909170435-5a0d662e` |
| request sha256 | `2427e1b650111b5638ea166170455e586c2a6cc22dda24dccbefc919f052e1a4` |
| authority sha256 | `fc99ed22597efefa99f1d77b03a31dbd0d8a147c6d3c9f6fc1418ff015d349b2` |
| owner record sha256 | `23073f81c4c247b04ade16555fdbbbd628e698581dfd27e3922fbbe647370130` |
| instance | `i-0c644583d35ab7987` (was RUNNING; terminated + confirmed) |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-ln3-diagnostic-20260909170435-5a0d662e/`

Ledger 36 → 37 (`$194.00 → $198.00` reserved, `$206.00 → $202.00`
unreserved). The reservation stands — no refund, no automatic retry.

## Preserved error (verbatim)

```
ClientError: An error occurred (InvalidInstanceID.NotFound) when calling the
DescribeInstances operation: The instance ID 'i-0c644583d35ab7987' does not
exist
```

Elapsed: 30.31 s (preflight + reservation + launch succeeded; the FIRST
wait-loop poll failed).

## Root cause (measured, not inferred)

1. `wait()` tolerated s3 `NoSuchKey` but NOT ec2 `InvalidInstanceID.NotFound`
   on the instance-state poll. AWS briefly answered NotFound for the freshly
   launched instance — the bounded hygiene pass measured it RUNNING minutes
   later. The launcher aborted instead of polling.
2. `cleanup()` treated the same transient NotFound as CONFIRMED_ABSENT and
   skipped termination — the launcher's own cleanup left the live instance
   and its security group (`sg-0d7b6e96f32b9fb82`, DependencyViolation).

## Hygiene performed (this job's own resources only)

Instance `i-0c644583d35ab7987` terminated and confirmed terminated;
security group deleted; bucket and IAM role/profile already absent
(verified). No other campaign resources were touched.

## Fix (prepared, test-locked, NOT a retry)

Both launchers (`aws/graph_training_ln3_diagnostic_launch.py`,
`aws/graph_training_launch.py`):

- `wait()` now tolerates `InvalidInstanceID.NotFound` on the instance poll
  and keeps polling (the S3 result remains the authoritative completion
  signal).
- `cleanup()` now retries describe within a bounded 60 s visibility window
  before concluding absence (`CONFIRMED_ABSENT_AFTER_RETRY`), so a live-but-
  invisible instance is terminated, never skipped.
- Six new regression tests; all 104 graph tests pass.

## What this does NOT change

- The owner's GO authorized ONE run; it failed at the AWS layer. A
  replacement run requires a NEW owner authorization and a NEW `$4.00`
  reservation.
- No neural measurement was produced; the training pilot stays pending;
  saturation stays a hypothesis; no claim follows.
