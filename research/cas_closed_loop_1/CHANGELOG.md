# CAS-CLOSED-LOOP-1 change log

## 2026-09-25 — Prospective bootstrap transport correction

Lane A v2 at f6253e1a failed startup and produced no test receipt. Its instance
was terminated and all 13 owned cleanup actions passed. The exact in-instance
exception was not captured. An independent read-only check reproduced failure
of the default global S3 presigned URL and success with the regional endpoint.

The prospective launcher pins the regional endpoint, prints a safe structured
bootstrap error before emergency upload, and captures live console output
before termination. Four launcher regressions join the 57 scientific cases for
a future 61-case run. Only syntax and offline URL construction have passed;
runtime tests remain unexecuted. This correction grants no automatic retry and
does not establish CAS_AWS_ENGINEERING_VALIDATED.

## 2026-09-25 — Prospective adapter correctness amendment

- Emit `return_identity: null` whenever there is no live acquisition frame.
  Preserve the current state and root call separately; only real suspended
  frames have the eleven-field return identity.
- Admit only the exact pinned `advance` bound method and code before dispatch.
  Refuse substituted wrappers, including catch-then-third-call wrappers, before
  they execute. An unexpected re-entry that invalidates the meter yields no
  receipt or usable execution count. Also reject
  any receipt with noninteger counters or `I_executed > I_allocated` after
  recomputing its content digest.
- Validate the native state and complete trace before joining work records.
  Read records and events from that same validated result and record its run,
  state hash, trace head and tick with the work catalog.
- Add regression coverage for no-frame boundaries, repeated native entry,
  rehashed over-allocation, removed/resealed records and corrupt empty windows.
  Adapt existing identity assertions to distinguish root context from return
  authority.

Validation is pending on the newly frozen AWS Lane-A source. Local syntax and
diff checks do not establish `CAS_AWS_ENGINEERING_VALIDATED`. Existing evidence,
source bindings, historical launch records and ledger entries are unchanged.
`HISTORICAL_PRODUCER.json` binds preserved original producer snapshots to the
historical manifest; those checks establish historical integrity, not amended
source acceptance. The fresh source/package freeze binds the current code.

The implementation, regression tests and `HARNESS_SPEC.md` belong in the same
prospective source commit. No model, comparative advantage or production claim
is added.
