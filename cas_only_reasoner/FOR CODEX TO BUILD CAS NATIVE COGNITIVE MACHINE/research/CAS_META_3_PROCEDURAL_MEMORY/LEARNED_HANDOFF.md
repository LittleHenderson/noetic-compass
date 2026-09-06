# Learned-program candidate handoff

This is a data-only connection from a successfully audited learning experiment
to a full-program candidate for fresh reuse tests. It is not a qualified skill,
new learning result, storage implementation, or native reuse demonstration.

It advances the V05 memory, V06 verified skill growth and V15 portable component
requirements in the full vision. It does not replace or narrow the other vision
requirements. Existing fixed-B storage, native demo and audit code are unchanged.

## Implemented connection

- `cas_meta3/learning_evidence.py` reads caller-trusted successful v3 inspection
  and stored-audit bytes, checks their common packet/source identity, recounts
  all 72 references and 360 outcomes, and binds one correct trained action to
  the selected checkpoint and its source map. A positive trained/untrained
  held-out count difference is required; statistical significance is not claimed.
- `cas_meta3/learned_package.py` checks a bounded full RUN/CALL program, selected
  return, declared CJT permissions, I/O, compatibility and explicit lineage.
  Its four pure dependencies are pinned to Git source
  `ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70`. The existing fixed-B schema is separate.
- `cas_meta3/learned_handoff.py` calls both checks and requires the package's
  program, binding and five provenance identities to match the recomputed
  learning proof. It returns `READY_FOR_FRESH_REUSE_TESTS`, always `UNQUALIFIED`.

The caller supplies expected audit hashes, consumer compatibility, permissions,
version and parent independently of the candidate. A digest claimed by a
candidate cannot authenticate itself. The new handoff reruns the evidence reader
from anchored raw bytes; it does not accept a self-asserted eligibility receipt.
Consumer compatibility is caller-supplied and is not a new hardware probe.
Claimed lineage is checked against caller expectations, not independently proved
to have an accepted parent. Package provenance stays `UNVERIFIED` in its original
bytes; a separate handoff receipt records the completed evidence binding.

## Current validation

The full META3 pure suite passed: **531 tests**, zero failures/errors/skips,
60.98 seconds in pytest and 63.0312676 seconds for the validation runner.
All tested source bytes and all 316 protected baseline files were unchanged.
The one warning is the intentional duplicate-ZIP rejection fixture.
Neural and provider imports were blocked. No model ran on the laptop.

Command, from this META3 directory:

```powershell
C:/Python314/python.exe -B tools/validate_local.py --output records/local_learned_handoff_001
```

The output directory must be new when rerunning; choose a new record name.
The record retains exact subprocess command, environment, source hashes, raw
outputs, XML counts and before/after protected-source checks.

- Receipt SHA-256: `df4ccf15a2318ada9e332ecec8b1960ff9496f99344d764be9cf3af079eaf38f`
- Raw stdout SHA-256: `d476dee68aefe8d463baa0011ab477c704382201aeda02d8201e7c0b15927ea5`
- JUnit SHA-256: `67764d575755aeba60a192700617441d436566d02dd4f28696c6f592bb5ac977`

All learning inputs in these unit tests are explicitly synthetic, including
their externally trusted fixture hashes. No actual learning packet has passed
the new handoff yet. These tests prove the checked admission behavior only.
The index boundary tests cover both 65,535 and 65,536 entries and rejection
above the separate tree-size ceiling.

## Remaining native sequence

1. Finish the live v3 AWS campaign and run its frozen complete-packet inspection
   and stored semantic audit without changing either evaluator. Preserve any
   failed or negative result rather than weakening eligibility.
2. If the completed native results show positive learning, select a correct
   learned action, bind its actual evidence through this handoff, and preserve
   a candidate package in separate append-only storage.
3. Retrieve it in a fresh process and execute it on new inputs through the
   accepted native runtime, including use inside a new parent procedure.
   Check actual outputs against independent native references, not just traces.
4. Test retained capabilities, permission rejection, parent/version continuity
   and rollback before any durable skill promotion. Keep accepted weights and
   the executor unchanged. A later scoped learning transition must separately
   preserve a suspended caller and its resource accounting.

The subsequent `LEARNED_STORAGE.md` records pure full-candidate persistence and
fresh-process revalidation. Actual learned-package persistence on AWS, native
reuse, retention, rollback, qualification, learned retrieval and learning during
a suspended call remain open. No extra AWS launch or budget reservation was
made for this pure work.
