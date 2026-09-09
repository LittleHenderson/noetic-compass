# GRAPH6_CONFIRMATION_001 — attempt 001 FAILURE (preserved error, root cause, fix)

Status: **FAILED.** One owner-authorized job ran; it died in the first candidate's
before-loss pass. Cleanup verified complete. No result numbers exist to report.

## Preserved evidence

| Item | Value |
| --- | --- |
| job | `cas-meta2-graph6conf-20260910013000-e485b07c` |
| receipt dir | `receipt_cas-meta2-graph6conf-20260910013000-e485b07c/` |
| worker status | `REMOTE_FAILED` |
| failure type | `SystemExit` (inner runner exit 1) |
| elapsed | 549.2 s |
| instance | `i-0f40206d59d6b8b7a` → `CONFIRMED_TERMINATED` |
| cleanup | `complete: true`, failures `[]`, bucket deleted, results deleted |
| independent hygiene check | 0 active `cas_meta_job`-tagged instances; instance `terminated`; 0 graph6 buckets; 0 leftover security groups |
| reservation | `$6.00` created exactly once; ledger revision 45 → 46 (`$236.00` reserved / `$164.00` unreserved) |
| result | none — the run stopped before the first candidate produced any measurement |

Preserved error (verbatim tail):

```
INNER_RUNNER_EXIT_1
Traceback (most recent call last):
  File "/opt/cas-graph6conf/package/_inner_runner.py", line 20, in <module>
    report = confirmation.launch(run_id=job, torch=torch, device=device,
  File ".../cas_meta2/graph_teaching/confirmation.py", line 462, in launch
    candidates.append(run_candidate(
  File ".../cas_meta2/graph_teaching/confirmation.py", line 348, in run_candidate
    training = trainer_module.launch(
  File ".../cas_meta2/graph_teaching/trainer.py", line 216, in launch
    training = run_training(learner, records, arm, budget,
  File ".../cas_meta2/graph_teaching/trainer.py", line 138, in run_training
    before = {op: learner.eval_loss(op, tasks) for op in ops}
  File ".../cas_meta2/graph_teaching/real_framework.py", line 310, in eval_loss
    positions = [self._position(task) for task in tasks if task["op"] == op]
  File ".../cas_meta2/graph_teaching/real_framework.py", line 289, in _position
    return self._index[task["record_id"]]
KeyError: '26da6b16e1ec5c804bb90149c47b3a1980d731c877d0aa49c95e3192aecf5cb2'
```

## Root cause (mine, not the frozen machinery)

`trainer.launch(seed=...)` uses its `seed` argument to build the **teaching
dataset** (`records = training_records(seed)`); it is the dataset seed, not a
learner-init seed. `confirmation.run_candidate` passed the candidate's
**learner-init seed** (`20260913`). The trainer therefore generated the dataset
for seed `20260913` while the learner's index had been built from the frozen
dataset (`training_records(20260909)`), so the very first `eval_loss` looked up a
record id that the learner's index did not contain and raised `KeyError`.

Nothing about the frozen candidate is implicated: the encoder, module, teaching
records, teaching order, scope and allowance were all as registered.

## Fix (implemented before any further launch)

1. `confirmation.run_candidate` now passes `seed=FROZEN_ENCODER_SEED` (the frozen
   dataset seed) to `trainer.launch`, with a comment recording this failure; the
   learner-init seed continues to be applied by the caller through
   `torch.manual_seed` immediately before the module bank is built.
2. Fail-closed guard added: the training report's dataset seed must equal the
   frozen dataset seed, otherwise `TRAINING_DATASET_SEED_CHANGED` is raised
   (this would have converted the silent `KeyError` into an explicit, early
   error).
3. The candidate record now carries `training_dataset_seed` next to
   `learner_seed` and `encoder_seed`, so the audit cannot confuse the two.
4. Two regression tests: the trainer must always receive the frozen dataset seed
   (and never the learner seed), a trainer reporting another dataset seed must
   be rejected, and the three learner seeds must genuinely produce different
   datasets from the frozen one.

## Cost and next step

The `$6.00` reservation is spent; the run produced no measurement. Per the
standing rule (no automatic retry, one new owner GO and one new reservation per
paid attempt), a replacement attempt requires a fresh authorization. The
replacement runs the identical pre-registered design on the fixed source.
