# Paid v9 launch: correction from AWS's event record

Source launched: `331f2746d75cdad369cb549784e3ce77c0ff6173`.
Source reviewed afterward: `67eb46a684cc158d2c051f9926502691a1075943`.
Job: `cas-meta2-20260907155404-80e827c9`.

This is an append-only correction, not a replacement for the original failed
run report. No retry or budget reservation was made during this investigation.

## Observed AWS failure

A read-only CloudTrail lookup in account `807562639912`, region `us-west-2`,
covered `2026-09-07T22:53:00Z` through `2026-09-07T23:02:00Z`.
The query returned one page, without a continuation token. The agent filtered
the response to event identity, time, operation and error; this note is a
transcription of that tool result, not an independently signed raw receipt.

- Event: `18c74df7-abe6-4488-9d92-8e7904072df6`
- Time: `2026-09-07T22:55:08Z`
- Operation: `ec2.amazonaws.com / RunInstances`
- Error: `Client.InvalidParameterValue`
- Exact message: `Value (cas-meta2-20260907155404-80e827c9-worker) for parameter iamInstanceProfile.name is invalid. Invalid IAM Instance Profile name`
- No instance ID was returned by this request.

This corrects the saved report's claim that this request created an instance
which was then terminated. The request was rejected before the later schedule
creation step. There is no new model-training result from this launch.

IAM propagation delay is a candidate explanation, not an established cause.
An IAM timeline/readiness observation is still needed to settle that detail.
Cleanup booleans alone must not be interpreted as proof an instance existed.

## Separate source findings before any future launch

A read-only review of both commits found these later hazards. They are not
explanations for the observed RunInstances error and are not neural defects.

1. Profile creation and role attachment lead directly to RunInstances, without
   a bounded readiness check.
2. The scheduler receives a role name where RoleArn is required. The worker
   permit is uploaded and embedded before a shutdown schedule is confirmed.
3. The generated bootstrap extracts into `ROOT/package`, then calls an
   extraction routine that requires that same destination not exist.
4. Collection retains artifact hashes but not the actual checkpoint archive;
   cleanup deletes the cloud archive. Save and verify evidence before deletion.
5. Cleanup sometimes labels never-created or unobserved resources as removed.
6. Durable failure recording needs to precede side effects and retain the
   original launch receipt even if cleanup also fails.

These findings remain open. The source, tests, and original evidence were not
changed by this read-only review. The separate teaching-cycle proposal does
not silently amend frozen v9 or authorize a retry of its one-shot run.
