# CAS-CLOSED-LOOP-1 adapter contract

This specification describes the prospective 2026-09-25 correctness amendment.
The pinned native coordinator remains the only writer of native state. The
adapter is a trusted host boundary, not an isolation boundary against arbitrary
Python code that changes interpreter hooks or mutates native objects.

## Return location

With no live acquisition frame, `return_identity` is null and
`frame_identities` is empty. This applies at genesis, during ordinary root work
and after all checked returns. The location still records the current state
hash, logical tick, root goal and root call. These fields describe current
context and do not create a suspension or grant return authority.

Each live frame has the eleven fields listed in `RETURN_IDENTITY_FIELDS`.
Its source snapshot and Bias basis come from the unique authorized suspension
event's pre-state hash. The active return identity is the top frame's identity.
Coordinates and this read-only record cannot select or resume a caller.

## Grant and observed native entry

The grant permits zero or one native host call. `I_attempted` counts the host
dispatch attempt separately. Before work, the dispatcher requires the exact
pinned bound `CompoundMachine.advance` method, including its receiver, function
identity and code object. Substituted wrappers cannot enter the native code.
The pinned implementation does not recursively enter `advance`.

The CPython call hook meters native entry and refuses an unexpected second
entry. A hook exception disables profiling, so code that catches that exception
could execute unmetered work. Any such breach invalidates the entire observation
and produces no receipt or usable count. This remains an error even if the
exception was caught. An ordinary internal native fault with an intact meter
uses the existing invalid-native-error receipt and leaves complete work unknown.

Every usable receipt must have exact integer counters satisfying
`0 <= I_executed <= I_allocated <= 1`, as well as a valid content digest.
Disabled and zero grants execute no native call. Native policy budgets remain
independent of this host-call count. These counts are not total compute or a
calibrated attention measurement.

## State-bound work join

Before reading work records, `primitive_work_for_events` obtains the validated
native result. This verifies the state content hash and its binding to the
complete sealed event chain, including profile, problem and ingress. The
catalog and event lookup both come from that exact result. A changed state,
even with a newly computed self-consistent hash, is refused if it is not the
state reached by the native trace. Empty event selections still require this
validation.

The existing catalog join then requires run, tick, intent and sealed event
identity. The report retains `catalog_state_binding` with the validated run,
state hash, trace head and logical tick. When replay checks an earlier window
against the final validated state, its catalog may contain later records;
the selected event-work rows and measured totals must still match exactly.
Historical receipts remain unchanged. Content hashes provide integrity, not
external signatures or fresh semantic authority.

## Acceptance boundary

New focused regression cases cover the three rules above. They must run on
the freshly admitted AWS Lane-A source together with existing public cases,
the checked engineering witness and fresh-process replay. AST parsing alone
is not acceptance. No current AWS validation claim is made by this document.

`HISTORICAL_PRODUCER.json` identifies the preserved original source snapshots
checked against the historical `RUN_MANIFEST.json`. That historical evidence
proves the original producer's retained bytes; it does not accept this amended
source. The fresh prospective source/package freeze binds the current code.
