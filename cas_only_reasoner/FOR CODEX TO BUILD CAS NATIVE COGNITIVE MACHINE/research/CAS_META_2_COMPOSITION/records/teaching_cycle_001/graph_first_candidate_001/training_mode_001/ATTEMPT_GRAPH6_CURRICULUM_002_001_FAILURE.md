# GRAPH6_CURRICULUM_002 — attempt 001 FAILURE (preserved error, root cause, fixes)

Status: **FAILED.** One owner-authorized job ran; it died in the FIRST checkpoint
reload, before any training. Cleanup verified complete. No measurement exists.

## Preserved evidence

| Item | Value |
| --- | --- |
| job | `cas-meta2-graph6curr-20260910053000-951cab20` |
| receipt dir | `receipt_cas-meta2-graph6curr-20260910053000-951cab20/` |
| worker status | `REMOTE_WORKER_FAILED` |
| launcher status | `AWS_CURRICULUM_LAUNCH_FAILED` (see defect 2 below) |
| failure type | `SystemExit` (inner runner exit 1) |
| elapsed | 564.5 s |
| instance | `i-0b56a1eed5c813cc9` → `CONFIRMED_TERMINATED` |
| cleanup | `complete: true`, failures `[]`, bucket deleted, results deleted |
| reservation | `$7.00` created exactly once; ledger revision 47 → **48** (`$249.00` reserved / `$151.00` unreserved) |
| result | none — the run stopped at the first checkpoint reload |

Preserved error (verbatim tail):

```
INNER_RUNNER_EXIT_1
  File ".../cas_meta2/graph_teaching/curriculum_experiment.py", line 172, in verify_checkpoint
    payload = load_checkpoint(torch, path)
  File ".../curriculum_experiment.py", line 165, in load_checkpoint
    return torch.load(str(path), map_location="cpu")
  File ".../torch/serialization.py", line 1578, in load
    raise pickle.UnpicklingError(_get_wo_message(str(e))) from None
_pickle.UnpicklingError: Weights only load failed. ... WeightsUnpickler error:
Unsupported global: GLOBAL torch.torch_version.TorchVersion was not an allowed
global by default.
```

## Defect 1 (mine): the checkpoint payload was not weights-only-safe

PyTorch 2.6 changed `torch.load`'s default to `weights_only=True`. The payload
written by `save_checkpoint` embedded `torch.__version__`, whose runtime type is
`torch.torch_version.TorchVersion` — not an allowed global under the safe default —
so the in-job reload verification refused the file it had just written. Because
the reload verification runs immediately after the FIRST save (step 0), the job
died before training.

**Fix:** the payload stores `str(torch.__version__)`, so every value is a
str / int / float / tensor / dict / list; `load_checkpoint` now passes
`weights_only=True` **explicitly** and the safe default is never disabled to make
a checkpoint load. Two regression tests pin it (the loader source must pass
`weights_only=True`; an unsafe payload must be refused).

## Defect 2 (mine): a failed worker was reported as a launch failure

`collect()` demanded `results/artifacts/manifest.json`. A worker that fails before
the artifact-upload step never writes that manifest, so `collect()` raised
`NoSuchKey` and the launcher reported `AWS_CURRICULUM_LAUNCH_FAILED` even though
the worker's own failure report had been retrieved, recorded and cleaned up
correctly. **Fix:** when the worker reports `REMOTE_WORKER_FAILED`, `collect()`
records the result and returns `artifacts: []`, `artifacts_available: false`,
`reason: REMOTE_WORKER_FAILED` instead of demanding artifacts. Regression test
added.

## What did work

The launcher's fail-closed path behaved exactly as designed: one reservation
created once, the worker's error preserved verbatim, evidence persisted, and
cleanup complete (instance terminated, bucket and results deleted) with no
retries.

## Cost and next step

The `$7.00` reservation is spent and the run produced no measurement. Per the
standing rule (no automatic retry; one new owner GO and one new reservation per
paid attempt), a replacement requires fresh authorization. The replacement runs
the identical pre-registered design on the fixed source — the panel, the
curricula, the seeds, the schedule, the decision rules and the budgets are
unchanged.
