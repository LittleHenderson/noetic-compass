# GRAPH6_CURRICULUM_002 — attempt 003 FAILURE (preserved error, root cause, fixes)

Status: **FAILED — but for the first time the EXPERIMENT ITSELF RAN TO
COMPLETION.** The failure is in the packaging/upload plumbing at the very end of
the job, after the six-learner comparison had finished. The measured result was
then lost when the failure report overwrote it and the instance was terminated.

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

## What this failure proves, and what it cost

**The experiment ran.** The traceback is at line 33 of the inner runner, which is
*after* `curriculum_experiment.launch(...)` returned, after the result was
serialised and written, and after the sha256 sidecar was written. The six learners
(three paired seeds × control/varied), the 1,536 updates, the 64- and 256-update
checkpoints, the reload verifications and the final verdict were all produced
inside that call. Attempt 003 therefore cleared every defect that killed attempts
001 and 002.

**What went wrong is packaging, twice:**

1. **The training venv had no AWS SDK.** The worker installs torch, the two
   wheels and `requirements-gpu.txt` into a venv, and the inner runner (which runs
   inside that venv) then tried to `import boto3` to upload the checkpoints. This
   is the first attempt that got far enough to reach that line.
2. **A failure report destroyed a completed measurement.** The outer worker's
   `except` path unconditionally overwrote `results/result.json` with the failure
   report, so the finished run's numbers were replaced on the instance and then
   lost when the instance was terminated. The launcher's cleanup then removed the
   bucket, leaving nothing to recover.

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
   directory, so an "it worked but the plumbing failed" case can no longer lose
   its numbers.
5. **Four new tests** pin all of it: the inner runner must not import boto3 and
   must stage the manifest; `upload_results` must send the result last; the
   preservation branch must exist and only fire when no result exists; collection
   must tolerate a result without artifacts. **255 graph tests pass.**

## Cost and next step

Four paid attempts have failed, all four on defects in my new code, none in the
frozen machinery: `$6.00` (confirmation 001), `$7.00` + `$7.00` (curriculum 001,
002), `$7.00` (curriculum 003) — **`$27.00` total with no retained measurement.**

The reason to expect a different outcome next time is concrete rather than
hopeful: attempt 003 demonstrated the experiment completes, and the only failure
left was the upload path, which is now the outer worker's job with tests pinning
the ordering, the staging and the result-preservation rule. A replacement still
requires a new owner GO and a new reservation.
