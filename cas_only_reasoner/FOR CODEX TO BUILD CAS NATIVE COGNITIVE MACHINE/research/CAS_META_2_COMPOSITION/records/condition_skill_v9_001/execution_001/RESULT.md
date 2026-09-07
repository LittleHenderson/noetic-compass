# Paid run 001 — FAILED launch, recorded honestly

- Job: `cas-meta2-20260907155404-80e827c9`
- Source freeze: `331f2746d75cdad369cb549784e3ce77c0ff6173`
- Package: archive SHA-256 `87a557aece2d6035aefa5133423243700273d2d55c00a84b5d037e4cbe5ec371`,
  3,701,818 bytes, 362 members; manifest `bb356c0b…`
- Request/authority: bound in `launch_inputs_001/` (request `a4cd6a92…`,
  authority `c247aa0c…`), owner approval record hash verified.

## What happened

1. Read-only preflight passed against the frozen AWS identity.
2. The single `$4.00` reservation was appended to the campaign ledger
   (revision 16 → 17; `$98.00` → `$102.00` reserved) with status
   `RESERVED_NO_AUTOMATIC_REFUND`. No refund, by policy.
3. The launch did not complete. The instance was registered and later
   terminated and confirmed; the job bucket was emptied and deleted. The
   exact launch error was **lost**: `execute()` raised on an incomplete
   cleanup before writing its result, discarding the recorded outcome. The
   only observable cleanup miss was the scheduler reporting that the job's
   schedule did not exist.
4. Recovery (same job, not a retry): inventory and cleanup were re-run. All
   resources are now gone — instance terminated and confirmed, bucket
   deleted, roles and profiles removed, security group `sg-0a00c1e60f1b9ab6d`
   deleted, no live instances, no remaining security groups. Evidence in
   `execution_001/recovery_receipt.json`.
5. **No training results exist** — no `results/complete.json` or
   `results/artifacts.zip` was ever produced, and the bucket contents were
   deleted by cleanup. The development scorecard remains `NO_RUN`.

## Defects found and fixed (pre-run adapter code, not the frozen experiment)

- `execute()` now persists its result on every exit and downgrades the status
  to `AWS_CONDITION_SKILL_V9_FAILED` when cleanup is incomplete, instead of
  raising and destroying the evidence.
- `cleanup()` now treats an already-absent schedule
  (`ResourceNotFoundException`) and an already-absent security group as
  clean, and now deletes the job's security group (previously never deleted).
- Tests updated: 88 pass across the provider and launch suites (full guarded
  re-capture recorded separately).

## Standing

- The single authorized run was consumed. **No retry is permitted or
  attempted.**
- Campaign ledger: revision 17, `$102.00` reserved, `$298.00` unreserved.
- Any new run requires the owner to authorize a new job, a new request and
  authority pair at the current freeze, and a new single reservation.
- Frozen negatives (`0/48`, `0/24`, `0/72`) and the accepted runtime remain
  untouched.
