# Graph-first ^6 training — AWS attempt 003: preserved error #2 (tokenizer list contract)

Status: AWS_GRAPH_TRAINING_FAILED. The lifecycle was fully clean (launch,
reservation, wait, collect, cleanup — zero leftovers); the worker failed at
the encoder step, and the **original inner error was preserved verbatim** for
the second time. The `$4.00` reservation is consumed; this job is closed; no
retry.

## Attempt identity (byte-bound)

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909024008-f27c195e` |
| request sha256 | `3f6990a646bb0bc2c083764d13b562a4a4db9a706eda1d8bfc88f9e26c00ec21` |
| authority sha256 | `0f70988acb784c89e87ffd9c50a2f5e28fcd27fab149db419ddce5548ee6fd78` |
| owner record sha256 | `408bd8d99950aa8d825e95625e944652d72451569eca016c69cb21e62cff0d03` |
| package identities | source `fec63492…` / archive `e6c87689…` / manifest `e435e411…` |
| reservation | `4.00` USD, ledger 25 → 26 (`total_reserved_usd` 150.00 → 154.00, `remaining_unreserved_usd` 250.00 → 246.00) |
| instance | launched and terminated cleanly; cleanup `complete: true`, no leftovers |

Evidence directory:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-teaching-graph-20260909024008-f27c195e/`

## Preserved original error (verbatim tail)

```text
File ".../cas_meta2/graph_teaching/real_framework.py", line 90, in build_encoder
    tokenizer = LosslessPublicTokenizer.fit_train(tuple(texts),
File ".../cas_meta2/features_v2.py", line 108, in fit_train
    _require(type(train_public) is list and 1 <= len(train_public) <= MAX_TRAIN_EXAMPLES,
cas_meta2.codec.PolicyContractError: LOSSLESS_TRAIN_INPUT_INVALID
```

Root cause: the frozen public tokenizer's `fit_train` requires a `list`;
the encoder passed a `tuple`. Fixed in `real_framework.build_encoder`
(`fit_train(list(texts), ...)`) with a source-level regression test.

## New package (the fix IS a package member)

| Field | Value |
|---|---|
| source_sha | `27f5efffb0f53acfa495fa74ff639ae23d08bec1` |
| archive_sha256 | `a4c07dda808615a250379f962db04aa9b9b1bbc4832f5dd686bfbfd6673605ae` |
| manifest_sha256 | `1f554acf769fc612ed0b8de8300d40728afc53beda122ea0033bd526b4aec1ec` |
| package | `training_mode_001/package_003/` (356,569 bytes, 30 members, SOURCE_ONLY_NO_LAUNCH) |

## Policy status

- Zero automatic retries; the `$4.00` reservation stands; no refund.
- A corrected re-attempt requires the owner to authorize a NEW job id, a new
  `$4.00` reservation, and a new owner record binding the NEW identities above.
