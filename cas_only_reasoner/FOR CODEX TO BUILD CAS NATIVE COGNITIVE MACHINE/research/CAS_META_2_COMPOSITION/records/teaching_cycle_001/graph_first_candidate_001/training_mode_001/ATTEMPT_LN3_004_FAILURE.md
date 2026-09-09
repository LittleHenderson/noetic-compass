# Graph-first ^6 — ln(3) diagnostic AWS attempt 004: FAILED (empty-content guard on real data; fixed)

Status: **AWS_GRAPH_TRAINING_LN3_DIAGNOSTIC_FAILED.** The worker reached the
learner construction and raised the correction-002 guard
`OPTION_CONTENT_REQUIRED` on REAL training data: 10 of the 60
training+practice records have a strict-subset option (its tokens are ALL
shared by the other two options), so removing the all-shared tokens leaves
zero content for that option. The launcher's visibility fixes held: cleanup
completed with zero failures and the instance
(`i-019d1d579572101ad`) confirmed terminated.

## Attempt identity

| Field | Value |
|---|---|
| job | `cas-meta2-ln3-diagnostic-20260909173243-5cc6fae7` |
| request sha256 | `2d88e4a888e7d1dfa1c831b262257040680c3b1af20775279a9bbc570f8bfc92` |
| authority sha256 | `05a231a7dd9ac2acb906ea876e5be70b82091b8fac4b911d942ebda06c40fb54` |
| owner record sha256 | `868c3ba3035c41b492a152fc76f1f067cba3934c96e101fa0bb839533b59b04c` |
| collected result sha256 | `70f3ce3c2faab9bc100e4657f537c39bf5a952c80d0fad9475b327a80356e186` |

Evidence:
`records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/receipt_cas-meta2-ln3-diagnostic-20260909173243-5cc6fae7/`

Ledger 37 → 38 (`$198.00 → $202.00` reserved, `$202.00 → $198.00`
unreserved). The reservation stands — no refund, no automatic retry.

## Preserved error (verbatim)

```
INNER_RUNNER_EXIT_1
...
  File ".../real_framework.py", line 206, in _content_ids
    require(all(content), "OPTION_CONTENT_REQUIRED")
ValueError: OPTION_CONTENT_REQUIRED
```

## Root cause (reproduced locally, measured)

`OPTION_CONTENT_REQUIRED` was my fail-closed guard for empty content — too
strict for the real data. Measured locally with the real tokenizer: 10 of
the 60 training+practice records (5 records × 2 arms, all LIST_PARTS) have
one option that is a strict SUBSET of the other two (e.g. `['idea2',
'idea3']` inside `['idea2','idea3','idea6']` and `['idea1','idea2',
'idea3','idea6']`), so every one of its tokens is shared by all three and its
content after removal is empty.

## Fix (prepared, test-locked, NOT a retry)

An empty-content option is now represented by the ZERO vector: its score
relative to the common baseline is exactly the common shift (the honest
semantics of "nothing beyond what is shared"), never a crash. Tests updated:
the strict-subset case builds a zero vector; 104 graph tests pass.

## What this does NOT change

- The owner's GO authorized ONE run; it failed on this spec guard. A
  replacement run requires a NEW owner authorization, a NEW `$4.00`
  reservation, and a REBUILT package binding the fix.
- No neural measurement was produced; the training pilot stays pending;
  saturation stays a hypothesis; no claim follows.
