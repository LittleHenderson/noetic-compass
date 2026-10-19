# Owner approval record: score the old small English model (Scribe L4) on the sealed 98

Job: helm-claude-scribe-l4-score-20261019-c41. Written 2026-10-19 by the Claude Code operator (sub-agent) for the coordinator.

## The owner's words (verbatim)

The owner's line for the record is exactly the two words:

"SCORE L4"

Source: `C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md` (sha256 at reading
`a40af3e4da98d0c4c5a4caad6fb7740c730a91fa97f512532cc1b2850b5053f1`), 2026-10-19 block, heading at line 138
(`## Owner order (2026-10-19, verbatim): ""SCORE L4"; I WANT THIS BUILT AND TRAINED I'M LIFTING THE GPU DIRECTIVE: ...`).
Recorded meaning (line 139): approves scoring the old sealed small English model (SCRIBE_L4_SEALED_98) at about
0.01 USD on AWS.

## Mapping (made by the coordinator, not by the owner)

The plan asks for an approval file that contains one fixed line. The owner did not paste that line. The coordinator
maps the owner's two words "SCORE L4" to that line and to the sealed plan and hashes below. The owner was not asked
to re-paste.

- Plan: `docs/working/scribe_l4_eval/SCORE_SCRIBE_L4_PLAN.md` sha256
  `18e350f5d026a9e9ec21d62b3e696ecb5c3ec4b9940775c0964a19a9171d929e` (added in commit `9453853a`; read at
  `origin/claude/project-thread-pmbzd6` = `2615d8d7`).
- Script: `docs/working/scribe_l4_eval/score_scribe_l4.py` sha256
  `969c845e6636547afcc4d2d8f9eefe3c66e31657d8da981a885e669d182a0b72`.
- Model package: `HELM_DISTRIBUTION_PACKAGE/scribe_l4_aws_gpu_training/SCRIBE_L4_AWS_GPU_PACKAGE.zip` sha256
  `7179250cbb17a800280d1b6459f2bb3ee4a23048d6b5a2382020296e8cceb58b` (equals its PACKAGE_FREEZE.json); weights
  `e36cf3cb50fe8ae168b2986a97000a47e7632b058b34b44629f4f17f99af9dc1`; vocabulary
  `6746e5dbd77dc6ddaa7bd7270b21ca2558c4da2e439522a2fbcffc66ce4dbc1a`; source commit
  `84812689b6fb6de4250dc9bf2e400df88a95944c`.
- Sealed set: `cas-synthetic/data/l4_split/real_heldout_unparseables_98.jsonl` sha256
  `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe`.
- Limits (from the plan): one AWS t3.medium CPU job, us-west-2, about 0.01 USD, cap 0.10 USD and 30 minutes;
  one scored attempt plus at most one plumbing retry.

APPROVE SCORE_SCRIBE_L4_SEALED_98
