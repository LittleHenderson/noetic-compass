# Recovery implementation milestone

The public native task completed from an empty method registry. The runtime
opened compound and primitive acquisition frames, measured actual work,
qualified and installed procedure memory, returned to the exact caller, and
committed the checked Effect `x=3` for `2*(3*x+5)+7=35`.

Evidence: **43 passed, 0 failed, 0 errors in 101.80 seconds**, covering 29 test
functions. The tests include wrong-method rejection with spent work retained,
insufficient budget, bounded depth/ticks, disabled actuator, forbidden-route
masking, corrupt prior history, incomplete/forged event joins, wrong loaded
dependency origins, wrong Effect despite positive allocation, original-input
binding, fresh-process replay, changed-input reuse (`e=41` gives `x=4`), and
primitive invalidation blocking the still-present compound program.

The retained episode has 12 measured host entries and 18 native events. Existing
executor reports recorded 19,030 primitive instructions, 1,693 original checks
and 32 linear checks. One native record lacks counters. Complete computation,
ordinary reasoning work and calibrated attention remain unknown. The receipt
records wall time separately; it does not convert wall time into work quanta.

`evidence/events.jsonl`, `journal.json`, `bundle.json`, `atlas.json`, and
`result.json` preserve the replayable episode. Caller-retained bundle digest:

```
eae7eb1bedb67af537187d409c89fca9e55a1580d52bf14be9b01e560a198d2c
```

Native journal digest:

```
6e6ecaf1e7c4e96067ca1b3871ba46b03a5cb1900b007f373debfccb67373771
```

Replay independently reconstructs native state, event coverage, event-bound
work counts and original-input Effect validity. Host entry counts and timings
remain retained hash-bound observations; replay does not independently
reproduce those host measurements. Digests are not signatures or attestation.

The compiler's exact Ohm facade supplies separately declared V/R predictions;
the allocation policy floors and caps them at one native host call. The existing
PCBA parser/checker admits three exact board templates whose allowlists govern
which native operations can execute. Static PASS is not general circuit
execution. The existing RPA adapter projects the same verified journal and has
no state-write or resume authority. Historical suspension identities come from
validated native events, not screen coordinates or a reset budget.

The supplied review's identity gap is fixed. Its assertion that fault validation
ran after receipt construction was incorrect; the original checks ran before
construction. Recovery strengthens those checks and retains failure context
without publishing corrupt after-state observations. `Exception` never caught
`KeyboardInterrupt`/`SystemExit`. All four original handoff files are preserved
with byte hashes; the missing historical objects remain explicitly missing from
the live repository.

Attempts are retained in `STATUS.json`: initial adapter 16/16 pass; initial work
join 20 passed/1 failed, then 21/21; first integration 16 passed/3 setup errors;
next full run 37 passed/4 setup errors; final 43/43. The two setup failures were
pytest temp-directory access and a missing task-owned parent directory. The
initial demo refused a misnamed operation; mapping the actual native
`CHECK_MEMORY_RESOLUTION` API fixed it. No failed attempt is called a pass.

Claim boundaries:

- Engineering demo and public procedure acquisition/reuse: checked.
- Original-input use and changed-input sensitivity: checked for literal inputs.
- Learned-model prediction and neural learning: NOT_RUN.
- General task benefit and CAS-specific comparative advantage: UNMEASURED.
- ASOM, full computation, external MemoryRef factual truth, general PCBA
  execution, broad atlas UI acceptance, learned pilot and production readiness:
  OPEN or unavailable. No existing production gate is closed.

No model/AWS job, purchase or process termination occurred. Upstream sources
were read-only. The root agent was the sole writer; a separate agent performed
bounded read-only correctness reviews. DeepSeek review requests use only the
owner-specified bus. Git push status is recorded separately in `STATUS.json`.

Post-commit artifact QA found Git line-ending normalization changed five retained file byte hashes. The follow-up pins exact evidence bytes and Python source line endings. Four artifact integrity tests passed in 0.10 seconds; all 13 evidence/producer/provenance files match their local recorded hashes. Committed-byte verification is required before push.

Committed-byte verification passed for all 13 files at 8f55cc3a462e438bcf706d7b64ddf9171d218039. GitHub directly reported that exact pushed implementation SHA on codex/cas-closed-loop-1-recovery-20260925. A separate observe CLI and broader atlas UI acceptance remain open; demo receipts provide the current observation interface.
