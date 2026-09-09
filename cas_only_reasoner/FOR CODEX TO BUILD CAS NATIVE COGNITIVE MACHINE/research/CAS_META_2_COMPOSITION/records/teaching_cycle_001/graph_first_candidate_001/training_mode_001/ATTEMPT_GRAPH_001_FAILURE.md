# Graph-first ^6 training — AWS attempt 001 FAILED (launcher defect destroyed the in-flight run)

Status: AWS_GRAPH_TRAINING_FAILED. The launch, reservation, and instance all
succeeded; the run was destroyed by a launcher-side error-class defect during
the result wait. No training result exists. The one owner-authorized `$4.00`
reservation is consumed (`RESERVED_NO_AUTOMATIC_REFUND`); this job is closed
and never re-run.

## Attempt identity (byte-bound)

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909011302-e654ae56` |
| request sha256 | `b7d7e6b74dc2cd890fe07bf955d4e8f8f173ec702afc386232059f0e3428543d` |
| authority sha256 | `45d8489664fcb94c894fcfacb853babed5d2e8a1ba25b3eddaf2314acda48019` |
| owner record sha256 | `10d2f67116ca31183d14237896106df91b5f11fc44686241a63abdc950aab739` |
| source_sha | `fec6349211fa3d67e612314f9280879dcd87dd53` |
| archive_sha256 | `e6c8768952076668bae74633d3416457234f2f3b3eaa0fb310733c0e47c1b97a` |
| manifest_sha256 | `e435e411c955f5ea7cc15dad33da28b14f1e80c9a41a2bca4b1e21f658bd9bc7` |
| reservation | created, `4.00` USD, ledger revision 23 → 24 (`total_reserved_usd` 142.00 → 146.00, `remaining_unreserved_usd` 258.00 → 254.00) |
| instance | `i-0b8e902eab4019ff9` — launched, then terminated by cleanup; never delivered results |

Evidence directory:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909011302-e654ae56/`
(`intent.json`, `preflight.json`, `reservation.json`, `launch.json`,
`provider_0001..0026.json`, `failure.json`, `result.json`, `source.zip`).

## What succeeded

Preflight (including the us-east-1 pricing call); the single `$4.00`
reservation; bucket + uploads; role/policy/profile with the bounded IAM
verification wait (visible on the first poll); security group; the single
`run_instances` (instance `i-0b8e902eab4019ff9`, IMDSv2 required).

## What failed (root cause)

The launcher's result wait polls `s3.get_object(results/result.json)` and is
designed to tolerate `NoSuchKey` until the worker uploads the result. The
provider was wired with the DEFAULT fake error class, so the real
`botocore.exceptions.ClientError` (code `NoSuchKey`) escaped the tolerance
path, the wait aborted ~5 minutes into the worker's bootstrap, and the
`finally` cleanup terminated the instance and deleted the bucket while the
worker was still installing torch — destroying the authorized in-flight run.

The same unwired class made cleanup mislabel two already-absent resources as
failures (`ResourceNotFoundException` for the schedule, `NoSuchEntity` for the
nonexistent timer role). Nothing was actually left behind: instance confirmed
terminated, zero security groups, all roles/profiles absent, bucket `404`.

## Fix (committed with this record)

`aws/graph_training_launch.main()` now wires
`from botocore.exceptions import ClientError` and passes
`client_error=ClientError` to the provider — the same wiring the binding-fit
launcher already had. Four regression tests added (launcher suite now 14):
wait tolerates repeated `NoSuchKey` then succeeds; non-missing codes still
propagate; cleanup tolerates schedule/timer-role absence; and a source-level
assertion pins the `ClientError` wiring in `main()`.

**The launcher module is not a package member**, so the finished package
identities above are UNCHANGED and remain valid for a corrected re-attempt.

## Policy status

- Zero automatic retries: this job id is closed forever.
- The `$4.00` reservation stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the SAME package
  identities (source `fec63492…`, archive `e6c87689…`, manifest `e435e411…`).
