# Stored outcome audit for both decoder modes

`tools/audit_ablation_stored_v4.py` requires the external inspection-receipt
hash, source commit, source archive hash, job and result-packet hash. It accepts
only a complete v5 retrospective inspection with a verified extraction. It
does not relabel that packet as a v3 training success.

Before importing the frozen source-replay primitives, it checks all packaged
local files against the bound source manifest. It rechecks the full extracted
inventory, rejects missing or added files, validates stored trace documents
against the published protected schema, and checks both decoder modes.

For each mode it checks all 72 reference executions and all 360 selected arm
choices. Rejected choices must reproduce the rejection and have no native
writes. Executed choices must match the sealed program and input, recorded
dependency path and final result. It recounts correctness and compute from
those checked executions and compares the complete and three 24-case group
summaries. A valid trace alone is never counted as a correct task.

The audit reads SQLite in read-only mode through the frozen audit primitives.
It never loads a checkpoint, runs tensors, trains, changes original records or
accepts a skill into memory. It reuses the existing stored source-replay engine:
this is not independent neural re-execution or a new restart demonstration.

The new local tests cover extraction/inventory changes, failed inspection
rejection, external identity rejection, pre-import source changes and changed
aggregate counts. A simulated 72-case mode checks 72 reference calls and 360
arm choices, passes the sealed candidate action rather than substituted gold,
and counts 72 valid but wrong candidate traces as zero correct tasks. Mutated
correctness, rejected-action writes and mismatched public tasks are refused.
These are simulated replay-engine tests, not native model runs.

The full guarded suite passed 1,247 test functions and 178 subtests with no
failures and eight GPU modules skipped. All captured source and 316 protected
baseline files stayed unchanged. The final receipt is under
`records/local_ablation_stored_audit_v4_002`; the earlier round is preserved.

The actual first failed experiment was also refused before stored-outcome
acceptance. See `records/ablation_stored_failed_packet_check_v4_001/receipt.json`.
The full outcome path still needs to be exercised on a completed comparison
packet.

The result boundary is explicit: stored outcome consistency may be verified,
but new training, fresh held-out performance and learning acceptance remain
false. The current comparison is retrospective and uses unchanged checkpoints.
