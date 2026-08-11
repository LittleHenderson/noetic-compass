# Test and review receipt

Source commit:
`50cd375fdc179e6a60fbed785e5b726d1fd34c23`

## Fresh root verification

- `python -m pytest live-trace-worker`:
  `576 passed in 121.44s`.
- `python -m pytest tests/test_cas_harness_audit.py
  tests/test_cas_harness_evidence_bridge.py
  tests/test_cas_harness_fleet_executor.py`:
  `100 passed in 2.54s`.
- Focused evidence/trust matrix:
  `158 passed`.
- Staged patch hygiene:
  `git diff --cached --check` passed.
- Post-commit worktree:
  clean.

## Independent post-repair decisions

1. Producer failure-path, claim-boundary, and integration audit:
   `APPROVE`.
2. Trust-boundary and independent-receiver audit:
   `APPROVE for source checkpoint, commit, and preregistration
   preparation`.

The audits confirmed typed fixture reopening; atomic create-once success and
failure publication; preservation of outcomes on late failure; independent
Git-bundle reconstruction; exact Cosign transcript validation; Rekor UUID
compatibility; offline drand BLS reexecution; and out-of-package
post-execution RFC3161 chronology binding.

The obsolete alternate failure-receipt helper and ambiguous
`official_outcomes_published` field were removed. A Windows/Node
incompatibility hidden by mocks was repaired by reading standard input through
`process.stdin`; an unmocked real-Node regression now reaches the actual BLS
code and rejects a nonzero forged signature.

## Remaining untested success-path limitation

No genuine valid retained drand beacon fixture exists locally. The real pinned
BLS *acceptance* path is therefore not yet proven. When the exact registered
beacon exists, both the official runner and independent receiver must accept
it before any outcomes run; any failure is a fail-closed abort.

## Claim boundary

This receipt covers source behavior only. It is not a live-model result,
chronology proof, model/GPU receipt, Evidence Packet, production acceptance,
customer verdict, or capability license.

