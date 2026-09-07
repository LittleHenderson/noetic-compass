# Owner ruling: historical 256 practice records

Recorded on 2026-09-07 from the owner’s direct answer in the active builder session.

## Ruling

**Include with isolation safeguards.**

The 256 historical practice records may be included only as declared
practice/training data. They must be deduplicated. Validation and test examples
must remain sealed and disjoint from them.

This ruling does not authorize a launch, retraining, checkpoint selection,
claim promotion, or reuse of validation/test targets. It does not alter any
historical score. In particular, the recorded depth-3 `0/48`, depth-4 `0/24`,
and total held-out `0/72` results remain unchanged.

## Required executable gates before any affected protocol runs

1. Bind the exact 256-record input by byte count, record count, and SHA-256.
2. Mark every record as training/practice provenance. No record may enter
   validation, testing, checkpoint selection, or test-target construction.
3. Reject duplicate semantic task identities within the 256-record set and
   between that set and the new training base, unless the protocol explicitly
   defines one deterministic deduplication winner before reading any test gold.
4. Reject overlap between every admitted practice record and every validation
   or test family, task identity, program graph, target-bearing public form, and
   other protocol-specific leakage key.
5. Keep validation and test bytes unchanged before and after the append.
6. Keep paired or grouped practice examples together when splitting or
   deduplicating them.
7. Record attempted, retained, duplicate-rejected, and overlap-rejected counts.
   The retained total must never be inferred from a requested count.
8. Freeze the resulting training manifest before training. Choose checkpoints
   from validation only. Save predictions before opening test gold.
9. Treat the 256 records as known practice data forever. They cannot later be
   relabelled as fresh held-out evidence.
10. Run any neural work on admitted AWS CUDA only, with a new preregistration,
    source freeze, explicit reservation, one declared seed, and no automatic
    retry.

## Scope note

The current condition-skill v9 pilot builds a new, separate synthetic dataset.
This ruling does not automatically append the historical 256 records to that
pilot. Any protocol that uses them must first implement and pass the gates above.
