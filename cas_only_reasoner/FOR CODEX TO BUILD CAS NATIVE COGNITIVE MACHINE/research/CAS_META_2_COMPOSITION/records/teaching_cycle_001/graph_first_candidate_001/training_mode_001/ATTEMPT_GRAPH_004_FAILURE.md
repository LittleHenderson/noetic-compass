# Graph-first ^6 training — AWS attempt 004 (approved job): preserved error #3 (public-record contract)

Status: AWS_GRAPH_TRAINING_FAILED. Fully clean lifecycle (launch, reservation,
wait, collect, cleanup — zero leftovers); the worker failed at the encoder and
the **original inner error was preserved verbatim** for the third time. The
`$4.00` reservation is consumed; job closed; no retry.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909030210-e1408e1a` |
| request sha256 | `fdb7cb6e5bf68b4672c970986a3ba5e04dd92a0112c6ac728da148785c78a7bf` |
| authority sha256 | `e6a5170140880951141446de65bb188ec265c36ea404edaa11930d648f788a0f` |
| owner record sha256 | `142b7c5a191049f337a6cdc0eda36dd3bfd5bb9206c2c0ec2b8d0b3d4a428b17` |
| reservation | `4.00` USD, ledger 26 → 27 (`158.00` reserved, `242.00` unreserved) |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909030210-e1408e1a/`

## Preserved original error (verbatim tail)

```text
File ".../real_framework.py", line 92, in build_encoder
    tokenizer = LosslessPublicTokenizer.fit_train(list(texts),
File ".../features_v2.py", line 113, in fit_train
    _validated(public)
File ".../features_v2.py", line 75, in _validated
    validate_public(public)
File ".../codec.py", line 45, in validate_public
    raise PolicyContractError("PUBLIC_INPUT_FIELDS_INVALID")
```

Root cause: the frozen public codec accepts only records shaped
`{"problem", "observations"}` with EXACTLY three observations covering slots
0,1,2 (tag <=256 chars, 8 finite values). The encoder passed raw prompt text.

## Fix (committed `238af1b5`, package members)

`adapter.public_records(record, arm)` now builds the exact frozen public
record (problem = framing prompt; three observations = correct option +
distractors, padded with a literal `none` option when needed; the correct
option is always exactly one of the three). The real encoder fits the
campaign's `LosslessPublicTokenizer` on those records and
`GraphLearner` consumes `encode_public` (problem ids + per-slot observation
ids) with the frozen dot-product readout over the three slots. Regression
tests: every whole-part record must satisfy the frozen contract; padding
behavior; worker renderer uses `adapter.public_records` (suite 101 passed,
24 subtests).

## New package (package members changed)

| Field | Value |
|---|---|
| source_sha | `238af1b519b9fc821236e6b2473079938b333b39` |
| archive_sha256 | `53af40ad0a829426baac8aca48c04d272003f917e6985f648a2d088e77b8b581` |
| manifest_sha256 | `a90323c89f1218362d7c8b8ff20030e95883b2b76910a40e3f4de5eae3f969a8` |
| package | `training_mode_001/package_004/` |

## Policy status

- Zero automatic retries; `$4.00` stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the NEW identities above.
