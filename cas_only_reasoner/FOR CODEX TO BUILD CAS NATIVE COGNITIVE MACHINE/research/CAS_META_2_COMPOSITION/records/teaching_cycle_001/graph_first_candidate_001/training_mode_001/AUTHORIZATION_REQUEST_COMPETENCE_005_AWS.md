# Graph-first ^6 — competence run 005 (REPLACEMENT) — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** Replacement for competence run 004,
which went the farthest yet: stage 1 passed, stage 2 trained, and **the
registered fit criterion was MET** (mean after-loss < mean before-loss −
0.02) — then stage 3 crashed on a sealed record with an all-shared option,
because the sealed predict path lacked the zero-vector fallback training
already has. One-line fix + behavioral test; 130 graph tests pass
(`ATTEMPT_COMPETENCE_004_FAILURE.md`).

## What this means

Two of the three stages are now proven on the GPU (relationship gate +
training that improves the familiar examples past the registered margin).
The remaining step is the sealed fresh-example evaluation, whose only
defect was the empty-content asymmetry — now fixed.

## Exact package (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `52068640b6464867c303b5f7d8b4aacff8c12a8c` |
| archive_sha256 | `2f3b027d57bc67e0d763b0b08ff433b53b1cb2d90e2c17ebca2e23004c52eff4` |
| manifest_sha256 | `0dd008e7e189f050c081cae3e114f7eec29d113cbd354396636022f37828a8c5` |
| package | `training_mode_001/competence_package_005/` |
| launcher | `aws/graph_training_competence_launch.py` at commit `4489889c` (unchanged) |

## The one-job request

ONE job, single arm (cas), the fixed sequence, one new `$4.00` reservation
exactly once, no refund, no automatic retry. Ledger today: revision 44,
`$226.00` reserved / `$174.00` unreserved; after this job's reservation:
revision 45, `$230.00` / `$170.00`. Original errors preserved; verified
cleanup.

On GO I will mint the job id, write the owner record binding these exact
identities, register, and execute — nothing before.
