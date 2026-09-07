# Agent lane board — condition-skill v9 (established 2026-09-07)

Parallel agents divide the remaining v9 work into lanes. One lane owns each
file set. Before ANY write, an agent re-reads this board and checks
`git status --short` and file timestamps; if its lane's files changed since it
started, it reports back instead of overwriting.

## Sacred single-writer objects (no lane may write)

- `records/budget/campaign_ledger.json` — one writer only, via
  `aws/budget.py` under its lock. Tests use private ledgers.
- Trainer, data builder, dataset partitions, adjudicator, protocol, owner
  approval records, frozen negatives (`0/48`, `0/24`, `0/72`) — read-only.
- The publication packet and its verifier — integrator lane only.

## Lanes

| Lane | Files it may write | Status |
|---|---|---|
| A — AWS provider adapter | `aws/condition_skill_v9_provider.py`, `tests/test_condition_skill_v9_provider.py` | active |
| B — independent adapter audit | `records/condition_skill_v9_001/audit_001/**` only | active |
| C — preregistration freeze docs | `records/condition_skill_v9_001/preregistration_v9_*.md` only | open |
| I — integrator | branch commits, `publication_packet.json`, `tools/check_condition_skill_v9.py`, `CHANGELOG.md`, `README.md`, packet branch pushes | active |

## Rules

1. Write only inside your lane's file set. Everything else is read-only.
2. Do not commit or push. The integrator reviews, runs the guarded checker,
   and commits with attribution.
3. No neural runs, no provider calls, no reservations, no AWS mutation.
4. Pure tests only: no boto3/torch/sqlite imports at test import time; inject
   fakes. The guarded checker blocks forbidden imports.
5. Report findings in your lane directory and in your final message: files
   written, checks run, and anything that looks like another lane's drift.
6. Owner approval remains the only authority for threshold/dataset changes.
