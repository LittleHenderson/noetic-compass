# Graph-first ^6 training — AWS attempt 008: TRAINING COMPLETED; sealed-eval seam failure (preserved)

Status: AWS_GRAPH_TRAINING_FAILED (evaluation stage). This attempt reached and
completed the registered training loop for the first time — the failure is a
seam defect in the post-training sealed evaluation, NOT a training failure.
`$4.00` reserved; job closed; no retry.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909065540-823842d3` |
| request sha256 | `3500a160315d0787ac6c11207e4e479b8eba5e344f9cd5caf7dd894bbdaee285` |
| authority sha256 | `5ae7f6c79df6b0b17ee6a3233921d9d5d955ef830ae5656df89d655ce5b47145` |
| owner record sha256 | `5936a9d16497fa0f18a33889529bb4a38bc0ea8b1178c9a5767c1f1379fd0f69` |
| reservation | `4.00` USD, ledger 30 → 31 (`174.00` reserved, `226.00` unreserved) |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909065540-823842d3/`

## Preserved original error (verbatim tail)

```text
File ".../_inner_runner.py", line 30, in <module>
    sealed = trainer.evaluate_sealed(learner_factory(framework.module), ...)
File ".../trainer.py", line 243, in evaluate_sealed
    "predicted": learner.predict(prediction_input(task))}
File ".../real_framework.py", line 197, in predict
    position = self._position(task_input)
File ".../real_framework.py", line 158, in _position
    return self._index[task["record_id"]]
KeyError: 'e8387a304f0c410531b94d38f0c31c968d950822a4ae21967045dc6e9e15a7c4'
```

Root cause: the sealed evaluator built `make_task` inputs while the learner
consumes public-record tasks (with the `public` encoding) and its index covers
only training records. Fixed: `evaluate_sealed` now builds
`adapter.public_records` tasks (the same kind the learner consumes), and
`GraphLearner.predict` encodes sealed records on demand from their public
record. The training loop itself completed — both framing conditions' updates
ran before this stage.

## New package (package members changed)

| Field | Value |
|---|---|
| source_sha | `838c6f7a2190ff3007ba74aa2642248f984338b4` |
| archive_sha256 | `3536504718803e05d82c4cca6dc3b5c7c36d44c644fcfc40db887a601555ba4f` |
| manifest_sha256 | `181b17999712c2b2788cb7a3ff56109213b7652d12a5b228f19fc49143484366` |
| package | `training_mode_001/package_009/` |

## Policy status

- Zero automatic retries; `$4.00` stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the NEW identities above.
