# GRAPH6_CURRICULUM_002 — attempt 002 FAILURE (preserved error, root cause, fixes)

Status: **FAILED.** One owner-authorized replacement job ran; it died in the FIRST
learner's before-loss pass, before any training. Cleanup verified complete. No
measurement exists.

## Preserved evidence

| Item | Value |
| --- | --- |
| job | `cas-meta2-graph6curr-20260910073000-210109c7` |
| receipt dir | `receipt_cas-meta2-graph6curr-20260910073000-210109c7/` |
| worker status | `REMOTE_WORKER_FAILED` |
| failure type | `SystemExit` (inner runner exit 1) |
| elapsed | 564.5 s class (same profile as attempt 001: installs then immediate failure) |
| instance | terminated (cleanup `complete: true`, failures `[]`, bucket + results deleted) |
| reservation | `$7.00` created exactly once; ledger revision 48 → **49** (`$256.00` reserved / `$144.00` unreserved) |
| result | none — the run stopped at the first before-loss pass |

Preserved error (verbatim tail):

```
INNER_RUNNER_EXIT_1
  File ".../cas_meta2/graph_teaching/curriculum_experiment.py", line 370, in launch
    learners[(condition, seed)] = run_learner(
  File ".../curriculum_experiment.py", line 229, in run_learner
    segment = run_segmented_training(
  File ".../curriculum_experiment.py", line 93, in run_segmented_training
    before = {op: learner.eval_loss(op, tasks) for op in ops}
  File ".../cas_meta2/graph_teaching/real_framework.py", line 310, in eval_loss
    positions = [self._position(task) for task in tasks if task["op"] == op]
  File ".../real_framework.py", line 289, in _position
    return self._index[task["record_id"]]
KeyError: '2032cbffce8b95884fd4838e57f814c5b0a08229f1ab25031813a143d9c28f30'
```

## Root cause (mine): each learner was indexed by the wrong lesson set

A real `GraphLearner` builds an index over the records it is handed and raises
`KeyError` for any other record id. `launch` built **every** learner over the
frozen train+practice tasks, but the **varied** condition trains on the varied
curriculum — different record ids — so the varied learner's first before-loss
pass looked up a record it had never been given.

This is the same *class* of defect as GRAPH6_CONFIRMATION_001 attempt 001
(training data and learner index disagreeing), which is why the fix is a contract
change rather than a one-line patch.

## Fixes (all before any further launch)

1. **Per-condition learner tasks.** `launch` now builds the learner over ITS OWN
   condition's lesson records; the injected factory contract is explicit:
   `learner_factory(framework, own_tasks)` returns `(model, arm, lr) -> learner`.
2. **Fail-closed pre-flight guard.** `_require_indexed_learner` scores the
   learner's own records before any training and raises
   `LEARNER_INDEX_MISSING_OWN_CONDITION_RECORDS` instead of a bare `KeyError`.
3. **Reload verification corrected.** `verify_checkpoint` now takes
   `learner_for(framework)` and predicts with the **reloaded** module; previously
   it rebuilt a fresh module but constructed the learner from the *original*
   framework, which would have made the "reload restores behaviour" check
   vacuous.
4. **Practice measurement clarified.** The comparable practice number is measured
   on the frozen train+practice records for BOTH conditions (through the sealed
   predict path, which handles records outside the index), and each learner's
   accuracy on its **own** curriculum is reported separately as
   `own_curriculum`.
5. **Three regression tests** that would have caught this locally: an
   index-enforcing learner double whose `KeyError` reproduces the real contract,
   an end-to-end `launch` test asserting every learner (and every reload
   verification) is bound to exactly one of the two condition lesson sets, and a
   state-dependent learner showing the reload check fails when the file does not
   match. 54 curriculum tests pass.

## What did work

The launcher's fail-closed path behaved correctly again: one reservation created
once, the worker's error preserved verbatim, evidence persisted, cleanup complete,
zero retries.

## Cost and next step

The `$7.00` reservation is spent and the run produced no measurement. Three paid
attempts have now failed, all three on defects in the new experiment code, all
three caught before any training: `$6.00` (confirmation attempt 001, dataset-seed
argument), `$7.00` + `$7.00` (curriculum attempts 001 and 002). Per the standing
rule (no automatic retry; one new owner GO and one new reservation per paid
attempt), a replacement requires fresh authorization.
