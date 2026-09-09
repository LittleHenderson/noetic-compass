# Graph-first ^6 — competence run 002 (REPLACEMENT) — authorization request (PACKAGE BUILT; NOT REGISTERED, NOT RESERVED, NOT LAUNCHED)

Status: **AWAITING_OWNER_APPROVAL.** Replacement for competence run 001,
which the in-job stage-1 gate stopped BEFORE any training — exactly the
fail-and-stop rule. The gate's two defects are fixed and test-locked
(`ATTEMPT_COMPETENCE_001_FAILURE.md`; 129 graph tests pass):

1. The gate now checks the REGISTERED quantity — distinguishable module
   INPUTS (same-token rewiring > 10× the reorder input baseline). Module
   output differences are REPORTED, not gated: the untrained module's fixed
   bias/tanh operating point crushing the tiny bound inputs is a
   measurement to report, not a reason to stop.
2. A stage-1 failure now returns a complete result with the preserved
   stage-1 measurements and `outcome: "STAGE1_CHECK_FAILED"` — never a bare
   exception.

Everything else is UNCHANGED from the preregistration
(`COMPETENCE_RUN_001.md`): one job, one fixed sequence, single arm (cas),
64 steps / 600 s, lr 0.003, learning curve, sealed fresh-example evaluation
only if mean after-loss < mean before-loss − 0.02, and exactly one of the
three registered outcomes.

## Exact package (built; NOT launched)

| Field | Value |
|---|---|
| source_sha | `17a310ec76bce4342ec89bae8f797b64e16f1fd2` |
| archive_sha256 | `bce8325bcf12996b52917214ad65dad50b77802d79d09f996afc88d853ebc9b4` |
| manifest_sha256 | `14c0a4929f3b0cb7d2cacd44a40502540a11e48fbeedb63e40616ea4f683228e` |
| package | `training_mode_001/competence_package_002/` |
| launcher | `aws/graph_training_competence_launch.py` at commit `4489889c` (unchanged) |

## The one-job request

ONE job, single arm, the fixed sequence, one new `$4.00` reservation exactly
once, no refund, no automatic retry. Ledger today: revision 41, `$214.00`
reserved / `$186.00` unreserved; after this job's reservation: revision 42,
`$218.00` / `$182.00`. Original errors preserved; verified cleanup.

On GO I will mint the job id, write the owner record binding these exact
identities, register, and execute — nothing before.
