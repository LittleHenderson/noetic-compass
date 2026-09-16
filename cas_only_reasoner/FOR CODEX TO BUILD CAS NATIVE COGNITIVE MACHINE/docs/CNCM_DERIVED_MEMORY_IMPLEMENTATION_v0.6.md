# Checked derived-result memory v0.6

The new runtime can resolve a typed reference to a checked mathematical result,
reuse that result in a later task, and refuse it when its declared inputs have
changed. It can also store a committed compound result for another task to use.
Acceptance status and exact receipts are in `records/derived_memory_001/STATUS.md`.

This is a bounded symbolic memory mechanism. It does not establish neural
learning, independently verified world facts, arbitrary procedure acquisition,
general mathematical reasoning or the complete CNCM charter.

## Two governed paths

`DerivedDefinition` declares an authorized equation of the form
`a*(b*x+c)+d=e`. Its exact digest must be present in the caller's ingress
allowlist. `DerivedResultRef` names a checked result in an explicit scope.
Definitions and source statements retain their separate authority boundaries.

For a missing supported value, `DerivedMachine` preserves the outer task in a
`DerivedFrame`, proposes an exact candidate, checks the formal proof independently,
stores the checked result, and returns to the saved task. Acquisition cannot
recursively acquire another derived definition in version 0.6. A nonempty saved
frame cannot be bypassed by starting an episode with a fresh budget.

For `store_result`, the ordinary compound result must first be independently
checked and committed. The new coordinator then binds the original typed inputs
to the authorized destination definition, records the proof and complete source
and derived-result dependencies, stores the result, and only then halts. A store
label alone cannot authorize a result or invent a definition.

Both paths use the new coordinator's intents and immutable history records.
Accepted runtime 0.2–0.5 source files and behaviors remain unchanged. Recovery
requires the caller's genesis, ordered ingress authority and expected journal
digest. A content digest is an integrity binding, not principal authentication.

## Reuse and correction

A retained result names its exact definition revision, proof, current source
sets, transitive derived dependencies and runtime source profile. The new input
checker independently reconstructs the compound task from the original typed
inputs; it does not trust the candidate generator's translation or a report
copied from a different task.

Every use rechecks that scope and supporting inputs still match. Superseded
definitions, corrected sources, new disagreeing source heads and stale transitive
support cannot silently reuse an old scalar. Historical records remain available;
new use records identify the result actually consumed. Confidence is explicitly
uncalibrated, not an invented probability.

The actual reproduction uses two five-episode sequences:

| Sequence | Checked outcomes |
|---|---|
| Missing scalar `y`, reuse, correction, refresh, later reuse | `3`, `4`, stale refusal, `2`, `3` |
| Store producer `x`, store consumer `y`, transitive correction, renew producer, renew consumer | `3`, `7/2`, stale refusal, `2`, `11/2` |

The first source correction changes the RHS from 11 to 17. The second changes
the producer's offset from 5 to 8. The final consumer inputs contain references,
not the stored numeric answers. New candidate generation and procedure acquisition
are separately disabled where specified. The current consumer still executes
and checks its own arithmetic; reuse does not waive verification.

## Bounds and evidence

Memory rationals are limited to 128 bits. The complete support graph, including
the new stored root and every dependency path, is limited to 16 nodes and depth 8.
Exact source/profile and input checks remain necessary even when a record fits
these bounds. Work reservations consume conservative policy units, including
failed expensive work; they are not measurements of CPU time or total checker
calls. Observed alias-entry counts are reported separately.

The reproduction reconstructs and continues every saved prefix in one fresh
child process. It compares exact resulting journals, including the interval
between commitment and storage. Parent-held manifest hashes bind the child's
inputs; before/after source checks bind the runtime, helpers, tests and retained
test reports. Parent and child record their actual imported source files.
Public engineering fixtures and injected failures are identified as such.

Independent review found and repaired several meaningful defects during
development: mutable frame containers; foreign-task inspection substitution;
shared incorrect input translation; wrongly bound post-commit storage; combined
dependency limits; and ignored generation-disable requests after a pause.
The failing test records remain retained alongside their passing replacements.

## What this changes for the learning question

Correct memory reuse can reduce repeated symbolic work and improve assisted task
completion. Those benefits require their own comparison against memory-off and
an ordinary dependency-aware cache under equal supplied facts and budgets.
They cannot be relabeled as improved neural learning.

`docs/CNCM_NEXT_LEARNING_EXPERIMENT_GATE.md` identifies the separate learner
ingestion gap and the next controlled learning experiment. A real optimizer
update is only a connection test; improved learning requires matched results on
untouched families, retention and transfer checks, and a closed answer boundary.
