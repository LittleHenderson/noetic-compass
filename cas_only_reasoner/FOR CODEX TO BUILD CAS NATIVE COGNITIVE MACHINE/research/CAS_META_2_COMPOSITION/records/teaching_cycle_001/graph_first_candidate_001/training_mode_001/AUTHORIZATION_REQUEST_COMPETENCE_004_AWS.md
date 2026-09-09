# Graph-first ^6 — competence run 004 (REPLACEMENT) — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** Replacement for competence run 003,
which PASSED the stage-1 gate on the GPU (the unit-normalized relationship
encoder works) and TRAINED stage 2 to completion — then crashed in MY
`fit_criterion` helper on the per-op loss shape before the numbers could be
serialized. Fixed and test-locked (`ATTEMPT_COMPETENCE_003_FAILURE.md`;
130 graph tests pass): per-op `{"total": float}` losses are handled by the
same `_loss_total` extraction the trainer already uses for its learning
curve.

## What this means

The relationship encoder is now PROVEN on the GPU: same-token rewiring
produces a distinguishable module input beyond the reorder baseline, and
the forward/backward path carries finite losses with nonzero gradients.
The replacement re-runs the whole fixed sequence to produce the actual
training numbers and one of the registered outcomes.

## Exact package (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `e0f1e83eed8dfacc6879b63067846b8538733ec7` |
| archive_sha256 | `838f93a719b90fc262ffd682f414485d283e42debcbc928fe5cce80acdd63b58` |
| manifest_sha256 | `39ba61c1908b6f1c39a70047975c9110452399feaac0735b8f2c0c433d852003` |
| package | `training_mode_001/competence_package_004/` |
| launcher | `aws/graph_training_competence_launch.py` at commit `4489889c` (unchanged) |

## The one-job request

ONE job, single arm (cas), the fixed sequence (stage 1 checks → 64 steps /
600 s training with learning curve → sealed fresh examples only if the fit
criterion is met), one new `$4.00` reservation exactly once, no refund, no
automatic retry. Ledger today: revision 43, `$222.00` reserved / `$178.00`
unreserved; after this job's reservation: revision 44, `$226.00` /
`$174.00`. Original errors preserved; verified cleanup.

On GO I will mint the job id, write the owner record binding these exact
identities, register, and execute — nothing before.
