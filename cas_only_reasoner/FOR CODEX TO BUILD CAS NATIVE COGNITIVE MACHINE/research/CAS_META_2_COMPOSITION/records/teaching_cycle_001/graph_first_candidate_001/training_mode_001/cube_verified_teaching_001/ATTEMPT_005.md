# Attempt 005 of the checked-component pilot — reserved, launched, failed, and what it exposed

Written 2026-09-10. Every number here is copied from a file on disk, not recalled.
This attempt produced **no learning measurement**. It is recorded as a negative
result and as the source of five defects that were fixed afterwards.

## What was authorised

`OWNER_AUTHORIZATION_CANDIDATE_PILOT_003.json` (sha256
`e23e6e514ea5eb184df483c249e85aa597859d7ec933df56bc631dffb3785ccc`), recording the
owner's raw instruction `GO` and the condition the owner set: run again only if
the package rehearsal passes. The rehearsal passed (9 tests at the time), so the
third paid attempt was launched under that condition.

## What was bound

| item | value |
| --- | --- |
| job | `cas-meta2-graph6cand-20260910164749-db2342b3` |
| request | `candidate_request_003.json`, sha256 `36a95991f45ba067870ad68657fc9e837ee439719bef8e18f774370a62e2dbd5` |
| authority | `candidate_authority_003.json`, sha256 `fa3d1ffe6fac380b593557a2297b7e0c7be3f3870cfd50e62ebecf8de234e9fc` |
| source commit | `ea4112f005c7186f7b0e417e714efc8469b8be37` |
| package | `candidate_package_004/`, archive sha256 `db2342b3c227ac13f1f8c42c75a3a0bf7cc6f14536aaa0fa0857f598e00d4744`, manifest sha256 `7de05cdd12dba902b04b8e55d21e51723cff7f61aeec8494a60b3c52e8ea4e4b`, 497,645 bytes, 46 members |
| reservation | `$7.00`, ledger revision 54, `RESERVED_NO_AUTOMATIC_REFUND` |

## What happened

- 16:50:07–16:50:31 UTC — evidence directory created, preflight passed, the
  `$7.00` reservation recorded, `source.zip` (497,645 bytes) uploaded, and
  instance `i-08f0bc3f273448d50` (g7.2xlarge) launched.
- 16:52:10 UTC — the worker failed and wrote `results/failure.json`:

  ```
  File "/opt/cas-graph6curr/package/graph6_candidate_worker.py", line 40, in main
      torch, device = gpu_adapter._cuda()
  ModuleNotFoundError: No module named 'torch'
  ```

- 16:52:11 UTC — `results/result.json` (the completion marker the launcher waits
  for) and `results/result_partial.json` appeared in the bucket.
- Launcher verdict: `AWS_CANDIDATE_FAILED`; stages `execution: FAILED`,
  `collection: NOT_VERIFIED`, `cleanup: INCOMPLETE`; total elapsed 437.3 s.
- Cleanup: instance `i-08f0bc3f273448d50` **CONFIRMED_TERMINATED**, security group
  deleted, roles removed, evidence bucket
  `cas-meta2-graph6cand-20260910164749-db2342b3-807562639912` **retained** because
  collection was not verified.

Actual EC2 time was about 1 minute 40 seconds, so the real spend on this attempt
is roughly `$0.07` at the `$2.52/h` ceiling. The `$7.00` is a ledger reservation,
not an invoice.

## Why it failed

The rendered candidate worker was written fresh, and it never did what the proven
curriculum worker does before training: create a virtual environment, install
`torch==2.11.0` from the CUDA wheel index, install the two frozen wheels and the
requirements, and run the training body as a subprocess **under that environment's
python**. Instead it ran the training body under the system python, where `torch`
does not exist. The rehearsal could not catch it because the rehearsal unpacked
the package and executed the packaged *modules* directly, in the developer's own
interpreter, which does have torch.

## What the failure exposed (five defects, all now fixed)

1. **No torch environment** — the direct cause above. The worker now performs the
   proven environment sequence and the training body runs under the venv python.
2. **The launcher could never have accepted a candidate result.** `wait` compared
   the result's schema against the *curriculum's* hard-coded schema, so the
   candidate's `cas-graph-training-candidate-result/1` always failed
   `CURRICULUM_RESULT_IDENTITY`. Even a perfect 128-update run would have been
   reported `AWS_CANDIDATE_FAILED` and left uncollected in S3. `wait` and `collect`
   now use the provider's own declared schema and failure statuses.
3. **A candidate failure would have been reported as finished.** `wait` recognised
   only the curriculum's word `REMOTE_WORKER_FAILED`; the candidate writes
   `WORKER_FAILED`, so the run would have been labelled `AWS_CANDIDATE_FINISHED`.
   Fixed by the same provider-declared statuses.
4. **Checkpoints would have been deleted uncollected.** `collection_is_verified`
   returns true when a result promises no artifacts — and the candidate result
   declared none, so a successful run's checkpoints would have been deleted with
   the bucket after only `result.json` was collected. The worker now stages
   checkpoints under `results/artifacts/` with a manifest, and the result envelope
   declares them.
5. **Cleanup reported a failure for work it never had to do.** Removing an instance
   schedule that this launcher never creates was recorded as
   `SCHEDULE_REMOVAL_FAILED`. It now reports `NOT_APPLICABLE`.

Two earlier defects were caught by the rehearsal before this attempt and are
recorded in `OWNER_AUTHORIZATION_CANDIDATE_PILOT_003.json`: the missing pinned cube
bundle in the package, and the checkpoint verifier whose digest rule could never
equal the learner's own identity.

## Evidence

All eight objects in the retained bucket were read out by hand into
`receipt_cas-meta2-graph6cand-20260910164749-db2342b3/` as `remote_*` files and
recorded with sizes and sha256 in `collection_manual.json`: the worker config, the
uploaded `source.zip`, the ledger snapshot and reservation receipt, and
`results/failure.json`, `results/manifest.json`, `results/result.json`,
`results/result_partial.json`. The bucket was then deleted, because every byte it
held is now in the receipt directory with its hash recorded.

## State afterwards

- No learning result exists for this pilot. The only measured graph-learning
  status in this campaign remains `VARIED_CURRICULUM_NOT_ESTABLISHED`.
- Ledger revision 54: `$291.00` reserved, `$109.00` free against the `$400.00` cap.
- `candidate_package_005/` (archive sha256
  `5c8b9efd3c7fc2dd54bb8d739dd38f78a1a703175a08843a03e70074c374f9b9`, manifest
  sha256 `858352a7e209b02e9eeac9c59d43e3e98cd0785a41f6b5c1df6e83900104d2d4`,
  499,425 bytes, 46 members) was built from commit
  `889c37e00fd8cd75aace74b5161f0186ab5a6a99` after the fixes, and the rehearsal
  now passes 12 tests against it — including one that executes the worker's own
  `main()` and fails unless the venv python runs the training body, the envelope
  declares its checkpoints, the sidecar matches, and `result.json` is uploaded
  last.
- A further paid attempt requires a new owner instruction. Nothing is reserved,
  queued, or scheduled.
