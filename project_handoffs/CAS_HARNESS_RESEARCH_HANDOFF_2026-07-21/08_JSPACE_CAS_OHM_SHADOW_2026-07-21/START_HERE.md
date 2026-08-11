# J-Space / Jacobian-lens / CAS-Ohm shadow continuation — 2026-07-21

This directory is an append-only continuation of the dated CAS Harness research
handoff. It records the first executable foundation for J-Space,
Jacobian-lens, and CAS-Ohm research without claiming that those methods are
operational or licensed.

## What was added

- A strict, disabled-by-default research-shadow schema and CLI.
- A fail-closed reader for the recovered sign-preserving hidden-state NPZ.
- Exact model, revision, capture-point, direction, dose, and response contracts.
- A canonical metadata-only receipt whose content is hash-bound.
- Full source-provenance verification before local application modules import.
- Tests proving malformed artifacts, thin bundles, source mismatch, and
  imported-module tampering fail closed.

## Current method status

- JSPACE_CORRESPONDENCE_V0: BASELINE_ONLY
- JACOBIAN_LENS_V0: NOT_COMPUTABLE_FROM_ACTIVATION_ONLY
- CAS_OHM_RESPONSE_PROFILE_V0: BASELINE_ONLY

For every method:

- execution mode: SHADOW
- verdict influence: NONE
- claim status: NOT_LICENSED
- claim eligible: false

The existing artifact has full signed activations at dose zero. It does not
contain a registered comparison basis, computational graph, output functional,
JVP/VJP, intervention direction, or multi-dose response sweep. Therefore it
cannot establish actual J-Space correspondence, a Jacobian-lens result, or a
CAS-Ohm response law.

## Exact identities

- Feature branch: codex/jspace-ohm-shadow-20260721
- Final commit: de1a117d028e655840931e9702911c1967a3d6a4
- Protected parent: 81b5c18bd83e1f01ccd398dcad3865a674335b7f
- Full Git bundle: cas-jspace-ohm-shadow-de1a117d.bundle
- Bundle bytes: 35,679,656
- Bundle SHA-256:
  13034E27046C689AA1FE8AEC12959D2D94C58A601AB9C49014AE4335B70C68CD
- Final receipt: research_shadow_baseline_final.json
- Receipt file bytes: 6,598
- Receipt file SHA-256:
  308673144C7A373EEE3666B3D95DD70559A843D23FE6069741020FB7C29EB99D
- Canonical receipt-content SHA-256:
  0f1c18ffc42acb28ea9626529f759faeb36782557a2e2bfaf0894b4ec6a0f886
- Input NPZ SHA-256:
  454A4F017D56ED393E50D7E88D29486B3379E96AE930A1123698C6275298EAD6
- Model: EleutherAI/pythia-160m
- Exact model revision:
  50f5173d932e8e61f858120bcb800b97af589f46

## Verification result

- Python compilation: PASS
- Focused research-shadow suite: 13 passed
- Complete live-trace-worker suite: 248 passed
- Final receipt canonical content hash: VALID
- Independent final read-only review: no remaining provenance or
  claim-integrity blocker

## Important boundary

This is not a production deployment, API integration, customer Evidence
Packet field, proof chip, verdict input, prompt-injection detector, causal
output controller, cross-architecture validation, or 300B result. The receipt
is hash-bound but not digitally signed, WORM-anchored, or independently
escrowed. The files remain local to this OneDrive handoff.

Read IMPLEMENTATION_AND_TEST_REPORT.md, then use REPRODUCTION_COMMANDS.md to
verify or continue the work.

## Additive continuation at 5d9a9d42

Continue with
`CONTINUATION_CANARY_AND_VERDICT_QUARANTINE_2026-07-21/START_HERE.md`.
That folder preserves the earlier payload and adds the exact-token Jacobian
canary, Stage-27F eraser correction, verdict-authority quarantine, external
CJT-drive boundary, and prospective CJT Bias/corrected-RPM/CAS-Ohm contract.
Its final source is commit
`5d9a9d4206990e673d86a0c62518fd1a44ab6b1e`. The retained
`405fb389` bundle is an intermediate checkpoint, not the final source.
