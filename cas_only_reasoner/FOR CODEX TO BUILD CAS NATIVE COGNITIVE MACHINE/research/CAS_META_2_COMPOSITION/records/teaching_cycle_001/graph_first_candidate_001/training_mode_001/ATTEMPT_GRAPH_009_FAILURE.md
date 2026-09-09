# Graph-first ^6 training — AWS attempt 009: TRAINING + SEALED EVALUATION COMPLETED; serialization seam (preserved)

Status: AWS_GRAPH_TRAINING_FAILED (serialization stage). This attempt completed
the registered training loop AND the post-training sealed evaluation; the only
failure was JSON serialization of the final report (tuple dict keys). `$4.00`
reserved; job closed; no retry.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909071727-23c7cca1` |
| request sha256 | `5665d2ddd2b8862d637bdf46fdc5a4a8b010eca428b218167aaff3f7ebde0f1c` |
| authority sha256 | `90193eaf7c2465223db92ad3f9b2e902fdc44b435af552c80d4885694a67da75` |
| owner record sha256 | `66486236c5647ff1c32cf87266c9f9d1d51bf5034cdc24c0a2d6e24d92e6531c` |
| reservation | `4.00` USD, ledger 31 → 32 (`178.00` reserved, `222.00` unreserved) |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909071727-23c7cca1/`

## Preserved original error (verbatim tail)

```text
File ".../_inner_runner.py", line 33, in <module>
    raw = (json.dumps({'schema': 'cas-graph-training-result/1', 'job': job, ...
TypeError: keys must be str, int, float, bool or None, not tuple
```

Root cause: `evaluate_sealed`'s per-split-op metrics used tuple keys
`(split, op)`; the final report serialization requires string keys. Fixed:
keys are now `"<split>:<op>"`. The training loop and the sealed predictions
both completed before this serialization step.

## New package (package member changed)

| Field | Value |
|---|---|
| source_sha | `a8e0ad13686bb61cb24717445d17babd2d73befa` |
| archive_sha256 | `81ff23213f00066b3252918acab07ca833945d5d9968c67fbb73740fa6cafef0` |
| manifest_sha256 | `7e3852609ca5e4863028dbcae4aee3486ba2881328109707c6efa1b97e8cf3de` |
| package | `training_mode_001/package_010/` |

## Policy status

- Zero automatic retries; `$4.00` stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the NEW identities above.
