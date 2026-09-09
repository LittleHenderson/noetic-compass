# Graph-first ^6 — competence run 001 — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** One complete learning experiment, per
the owner's process review: the whole fixed sequence runs inside ONE job —
no separate launches between stages, no two-arm comparison, no silent
patches. Preregistration: `COMPETENCE_RUN_001.md`.

## The fixed in-job sequence (single arm: cas framing)

1. **Checks (zero optimizer steps):** same-token relationship rewiring must
   move the module input/output beyond the connection-list-reorder baseline
   (tolerance: rewire > 10× reorder); forward/backward sanity (finite
   losses, nonzero gradients). Failure stops the job with preserved numbers.
2. **Training:** the candidate ^6 module trains on the familiar
   train+practice whole-part examples — 64 optimizer steps / 600 s,
   lr 0.003, learning curve every 8 steps, digest containment.
3. **Fresh examples, only if the registered fit criterion is met** (mean
   after-loss < mean before-loss − 0.02): sealed validation/test evaluation
   with predictions before answers, plus familiar-example accuracy —
   reported separately.

## The deliverable — exactly one registered outcome

- `LEARNED_AND_TRANSFERRED` (criterion met AND sealed ≥ 6/12, chance ≈ 4/12)
- `LEARNED_NO_TRANSFER` (criterion met, sealed < 6/12)
- `DID_NOT_FIT` (criterion not met — actual losses, predictions, and the
  measured limitation reported regardless)

Computed by a deterministic rule from the recorded numbers. No claim beyond
the outcome sentence and its supporting numbers.

## Exact package (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `4489889c9813260d76a376f234765015cacca5ae` |
| archive_sha256 | `71e72bae410ca3d90c57f067f2fa8507326fbcb24346f7166b4d343b0524b66d` |
| manifest_sha256 | `5c329419531bd695c6bc781de1ec94c52490b6def6cb26d7bd2df3fbed69ff2f` |
| package | `training_mode_001/competence_package_001/` |
| launcher | `aws/graph_training_competence_launch.py` at commit `4489889c` (new) |

## The one-job request

- ONE job, single arm, `max_optimizer_steps: 64`, `max_wall_seconds: 600.0`,
  `learning_rate: 0.003`; sealed splits read only in stage 3.
- ONE new `$4.00` reservation, exactly once, no refund, no automatic retry.
  Ledger today: revision 40, `$210.00` reserved / `$190.00` unreserved;
  after this job's reservation: revision 41, `$214.00` / `$186.00`.
- Original errors preserved on any failure; evidence persisted on every
  exit; verified cleanup.

128 graph tests pass. On GO I will mint the job id, write the owner record
binding these exact identities, register, and execute — nothing before.
