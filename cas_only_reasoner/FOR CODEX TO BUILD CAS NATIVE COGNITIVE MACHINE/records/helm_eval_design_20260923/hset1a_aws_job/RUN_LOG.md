# HSET-1A job run log

## Attempt 1: 2026-09-23 15:43:14Z -> 15:46:53Z. The build CRASHED on Claude's bug; acceptance A2 hit the same bug

**The run.**

| Item | Value |
|---|---|
| Machine | `i-0c8907f61b2d5fbc4`, c7i.2xlarge, us-west-2a |
| Bundle | sha256 `d0dfb09e...`, built from commit `1f3ed3ae` |
| Time | 3.7 minutes from launch to the end of the watch |
| Cost | at most **$0.0223** |
| Status | `finished_with_failures build=1 acceptance=3` |
| Machine now | shutting down, destroyed on shutdown |
| Records | `attempt1_launch_record.json`, `attempt1_watch_record.json`, `attempt1_watch.log`, `results_attempt1/` |

**The cause, one bug in Claude's code.**
- On Python 3.14, `multiprocessing.Pool.imap_unordered` returns a plain generator, which has no `.next(timeout)`.
- Claude had added that call after the pre-launch review, to stop a stuck worker from hanging the job. Neither the
  local checks nor the review ran the process-pool path on Python 3.14.
- So the build stopped with `AttributeError: 'generator' object has no attribute 'next'`. It had built 3,370 items in
  1,685 clusters in 11.6 s, but evaluated none.
- The acceptance runner's test A2 failed the same way.

**What still ran, and measured.**
- **A1 PASS.**
  - The five frozen files equal the original anchors.
  - The profile equals the historical anchor and the original tree.
  - Every module imported from the v2 tree.
- **A3 PASS.**
  - 105 degree-colliding classes.
  - 210 analogy and 442 correspondence questions, plus 233 six-node correspondence questions.
  - 0 mismatches with the oracle.
  - Exactly 64 analogy answers accepted; 120-map cases refused.
  - Every 7-node case refused.
  - The new slot path gave 121 and 721 candidates.
- **A4 PASS.**
- **A5 PASS.**
- **A6 PASS.**
  - 1,000 five-node analogy questions on 64-world banks took **88.655 s** on one process, against a 600 s budget.
  - At most 3,240 permutations per question, 1,187,640 in total.
  - 1,000 of 1,000 answers equal the oracle.
  - The 100 six-node questions took 10.067 s, with at most 17,280 permutations per question.
- **X was skipped**, because no HSET-1A file existed.

**The status of these numbers.** They are recorded, but the acceptance verdict comes only from a complete run of
one code version. Attempt 2 re-runs every test.

**Nothing secret was made.**
- The build stopped before any cell existed.
- The sealed folder `D:/tksCAS-archive/hset1a_sealed_20260923/run_20260923T154310Z/` holds an empty tarball.
- The bundle, which holds the salt, is in S3 under `helm-integration/hset1a-build-20260923T154310Z/`.

**The fix, in `hset1a_build.py` and `d1_acceptance_run.py`.**
- `concurrent.futures.ProcessPoolExecutor.map(..., timeout=...)` is used instead. A dead worker, or a failed
  start-up, raises `BrokenProcessPool` instead of an endless restart. The whole map is bounded in time.
- It was checked locally with 2 spawned workers.

**A new first stage in the job script.** Both programs now run end to end at tiny size before the full run, with a
throwaway all-zero salt, so no real TEST data is made. The job stops at once if either fails, or if any acceptance
test records an error. The laptop has too little free memory (827 MB) to run `main()` locally with the course loaded.
