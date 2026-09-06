# Completed stored comparison audit

Status: `STORED_COMPARISON_AUDIT_PASSED`, completed true, no errors.
Finished: 2026-09-06T05:26:27.620258+00:00.

The receipt SHA-256 is
`3dc89119685d6c83ee33bc65019f8ea98ad58f6307613d77d1e95ba8e2502580`.
It binds job `cas-meta2-20260906032109-361b34a0`, source
`9f562c761c7cb84c767673b2fab735cdd031b499`, and result packet
`c0fbc413ce94a3b192a5b634bfc246dae96d94f3fe01943caacbff83a4e74708`.

Coverage: 4,712 stored traces across 421 databases, checked against the
published protected schema. Each of the two decoder modes has 72 reference
executions and 360 arm choices checked against sealed programs, inputs,
stored outcomes, permissions/rejections and saved aggregate counts.

Both modes yield CAS trained 0/72, CAS untrained 0/72, generic trained 12/72,
generic untrained 0/72 and rule 72/72 correct tasks. Better input-binding or
trace counts did not become correct CAS task outcomes.

The exact audit command is in `../aws_ablation_v4_002/AUDIT_COMMANDS.ps1`.
Use a new inspection/extraction/output directory for a clean rerun and pass
that newly produced inspection receipt's external SHA-256. Do not overwrite
this evidence. Neural and provider imports were blocked by the auditor.

Boundary: frozen stored source replay, not independent neural re-execution,
new training, fresh held-out performance, restart proof or learning acceptance.
The decoder comparison reused unchanged checkpoints on already-exposed cases.
