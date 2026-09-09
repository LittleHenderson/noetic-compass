# Graph-first ^6 — competence run 003 (REPLACEMENT) — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** Replacement for competence run 002,
whose stage-1 gate stopped BEFORE any training and this time RETURNED the
preserved measurements. Those numbers proved the remaining defect: the raw
Hadamard-bound lines were ~8 orders of magnitude smaller than the pooled
framing text, so in float32 the relationship distinctions sat below the
noise floor of the summed module input. Recorded in
`ATTEMPT_COMPETENCE_002_FAILURE.md`.

## The fix (one documented change to the encoding rule)

Each bound line is now **unit-normalized** after the Hadamard product — a
fixed computation with no learned parameters — so every structural line
contributes at O(1) scale and the structure dominates the input. The rule
amendment is in `RELATIONSHIP_ENCODER_001.md`; the structural test verifies
the rewire-vs-reorder contrast on balanced fake rows. 129 graph tests pass.

Everything else is UNCHANGED from the preregistration
(`COMPETENCE_RUN_001.md`): one job, one fixed sequence, single arm (cas),
stage 1 checks (input-level gate + forward/backward sanity, zero updates),
stage 2 bounded training (64 steps / 600 s, lr 0.003, learning curve,
containment), stage 3 sealed fresh examples only if the fit criterion is
met — and exactly one of the registered outcomes.

## Exact package (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `f5d30db8ac965ab6e94d24b6e898b89a6d2ae7ab` |
| archive_sha256 | `82bcaf6c6d8eec5904381c6eb684645358aa89f16be276f116b3d1c5c2b8c55d` |
| manifest_sha256 | `950d9cf209cff0fe85fe684c6767e1d8345657e1f3ba9fc22f2173282487a3bb` |
| package | `training_mode_001/competence_package_003/` |
| launcher | `aws/graph_training_competence_launch.py` at commit `4489889c` (unchanged) |

## The one-job request

ONE job, single arm, the fixed sequence, one new `$4.00` reservation exactly
once, no refund, no automatic retry. Ledger today: revision 42, `$218.00`
reserved / `$182.00` unreserved; after this job's reservation: revision 43,
`$222.00` / `$178.00`. Original errors preserved; verified cleanup.

On GO I will mint the job id, write the owner record binding these exact
identities, register, and execute — nothing before.
