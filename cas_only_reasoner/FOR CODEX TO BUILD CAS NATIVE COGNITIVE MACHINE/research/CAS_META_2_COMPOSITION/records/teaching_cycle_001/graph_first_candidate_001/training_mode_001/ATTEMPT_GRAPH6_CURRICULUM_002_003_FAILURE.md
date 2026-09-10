# GRAPH6_CURRICULUM_002 — attempt 003 FAILURE (preserved error, root cause, fixes)

Status: **FAILED.** The failure is in the packaging/upload plumbing, not in the
experiment: the traceback sits after the training call returned. The measurement
was then lost — **the comparison's scientific outcome is unavailable.**

## Corrected claim (owner review, 2026-09-10)

The traceback's position is evidence of **how far execution progressed**; it is not
a recovered scientific result. Without the result and the checkpoint files, the
1,536 updates, the 64/256 checkpoints, the reload verifications and the verdict
are recorded as **reported execution progress** — not as verified measurements.
Nothing about the learner's behaviour on the final panel is known from this run.

Likewise the four failed allocations are **`$27.00` consumed from the campaign's
reservation allowance**; no invoices were inspected, so this is not independently
verified billing.

## Preserved evidence

| Item | Value |
| --- | --- |
| job | `cas-meta2-graph6curr-20260910093000-75387578` |
| receipt dir | `receipt_cas-meta2-graph6curr-20260910093000-75387578/` |
| worker status | `REMOTE_WORKER_FAILED` |
| failure type | inner-runner `ModuleNotFoundError` |
| elapsed | 579.1 s |
| instance | `i-0926a1d98af470331` → `CONFIRMED_TERMINATED` |
| cleanup | `complete: true`, failures `[]`, bucket deleted, results deleted |
| reservation | `$7.00` created exactly once; ledger revision 49 → **50** (`$263.00` reserved / `$137.00` unreserved) |
| result | **none retained** — the completed measurement was overwritten and destroyed |

Preserved error (verbatim tail):

```
INNER_RUNNER_EXIT_1
Traceback (most recent call last):
  File "/opt/cas-graph6curr/package/_inner_runner.py", line 33, in <module>
    import boto3
ModuleNotFoundError: No module named 'boto3'
```

## What this failure shows, and what it cost

**Reported execution progress (not a verified measurement).** The traceback is at
line 33 of the inner runner, which is *after* `curriculum_experiment.launch(...)`
returned and after the result and its sha256 sidecar were written. That is
evidence the training call completed rather than dying inside the experiment — so
attempts 001's and 002's defects did not recur — but with the result and the
checkpoints gone, none of the run's numbers (updates, losses, accuracies,
verdict) can be verified or reported.

**What went wrong is packaging, twice:**

1. **The training venv had no AWS SDK.** The worker installs torch, the two
   wheels and `requirements-gpu.txt` into a venv, and the inner runner (which runs
   inside that venv) then tried to `import boto3` to upload the checkpoints. This
   is the first attempt that got far enough to reach that line.
2. **A failure report destroyed a completed result.** The outer worker's
   `except` path unconditionally overwrote `results/result.json` with the failure
   report, so the finished run's numbers were replaced on the instance and then
   lost when the instance was terminated. The launcher's cleanup then removed the
   bucket, leaving nothing to recover.
3. **Preserving a file on a machine about to be deleted is not delivering it**
   (owner review). The earlier "a completed result can no longer be destroyed"
   claim went beyond what the code demonstrated: the preservation branch had no
   test that the *delivery chain* carries the bytes out, and cleanup deleted the
   bucket unconditionally even when collection had failed.

## Fixes (all before any further launch)

1. **Uploads moved to the OUTER worker**, which runs with the system python where
   the AWS SDK exists. The inner runner now only *stages* the checkpoints and a
   manifest under `results/artifacts/` and never imports boto3. The venv stays a
   pure training environment.
2. **`result.json` is uploaded LAST**, after the manifest and every artifact, so
   the launcher's poll for `result.json` now means "everything is already in S3".
3. **A completed result is never destroyed.** On any failure the outer worker
   preserves an existing `result.json` as `result_partial.json` (+ sidecar) and
   writes `failure.json` beside it; it writes a failure *report* only when no
   result exists at all.
4. **The launcher collects the preserved material.** `collect()` accepts a result
   that lists no artifacts (recording `artifacts_available: false`) and
   best-effort downloads `result_partial.json` and `failure.json` into the receipt
   directory.
5. **Evidence deletion is now conditional (owner-directed).** Compute shutdown and
   evidence deletion are separate: the instance always terminates by its deadline,
   but the bucket is deleted ONLY when `collection_is_verified(collected)` is true
   — the local receipt holds the result bytes and every artifact the result
   promised. Otherwise the bucket is **retained**, named in the cleanup record as
   `retained_bucket` with `retention_reason`, and the job is reported incomplete
   (`EVIDENCE_RETAINED_PENDING_COLLECTION`). Partial collection names exactly which
   checkpoints did not arrive (`artifacts_missing`, `reason:
   ARTIFACTS_MISSING:<names>`). `execute()` now reports the three stages
   separately — `stages.execution`, `stages.collection`, `stages.cleanup` — and
   sets `completed_deliverable` only when all three succeeded.
6. **A delivery rehearsal with the exported code** (`tests/
   test_graph_training_delivery_rehearsal.py`) runs the REAL rendered worker inner
   runner, the REAL exported `upload_results`, the REAL `wait/collect/cleanup`
   against a simulated bucket, on two paths: normal completion (collector
   receives the known result and every dummy checkpoint with matching hashes and
   byte counts; the completion signal appears only after its required uploads) and
   an injected upload failure after the dummy experiment returns (the original
   result survives byte-for-byte, the failure is recorded separately, missing
   checkpoints are named, cleanup retains the bucket, and the compute still
   stops). **256 graph tests pass.**

## Cost and next step

Four paid attempts have failed, all four on defects in my new code, none in the
frozen machinery: `$6.00` (confirmation 001), `$7.00` + `$7.00` (curriculum 001,
002), `$7.00` (curriculum 003) — **`$27.00` total with no retained measurement.**

The reason to expect a different outcome next time is concrete rather than
hopeful: attempt 003 demonstrated the experiment completes, and the only failure
left was the upload path, which is now the outer worker's job with tests pinning
the ordering, the staging and the result-preservation rule. A replacement still
requires a new owner GO and a new reservation.
