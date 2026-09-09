# Graph-first ^6 — representation follow-up 001 — training attempt 011 (AUTHORIZED, REGISTERED)

Status: **AUTHORIZED_BY_OWNER / REGISTERED.** Owner instruction
**"IF THE FOLLOWING IS TRUE IMPLEMENT IT IF NOT IT'S YOUR CALL"** (recorded
`2026-09-09T09:57:12Z`) with the attempt-002 result record pasted. The record
was re-verified TRUE, so the follow-up it names is implemented: exactly ONE
variable changes — option-slot aggregation in the frozen readout goes from
mean-pooling (measured collapse) to sum-pooling. Everything else is
attempt-010-identical (module, config, contract, lessons, scoring, seeds,
budgets, sealed splits). Preregistration:
`REPRESENTATION_FOLLOW_UP_001.md`; adapter-spec amendment appended.

| Field | Value |
|---|---|
| job | `cas-meta2-teaching-graph-20260909095712-4ca46fce` |
| source_sha | `c985d2f4a44c73a6f007c3ee4a5ad1676e438bba` |
| archive_sha256 | `f2ef785bd093c2555d3094d7e368d774b94fad67bfece73d94406e4528c926a0` |
| manifest_sha256 | `4b77518d1f3c70a846e8ee1a954dc0d6e4d4e2c1da12f23e64376660b4b26c3a` |
| package | `training_mode_001/package_011/` |
| launcher | `aws/graph_training_launch.py` at commit `7d9d43ee` (unchanged) |
| request sha256 | `5adc103b06557897a149adea398f830e7dd5fdc59cca93770fb9caf44bab62bd` |
| authority sha256 | `38446d88b60f3ab92ad484306ba2e2cc291e8337788ff405de37f06c78269a34` |
| owner record sha256 | `b7df9c1614a57a28d848c7ccc14022048dbaba96f7098fa4a58a35c3bbb0dd7a` |

Launch inputs: `training_mode_001/launch_inputs_011/` (request inert,
`launch_authorized: false`). Owner record:
`training_mode_001/OWNER_AUTHORIZATION_AWS_011.json`.

Budget: one new `$4.00` reservation, exactly once, no refund, no automatic
retry. Ledger before: revision 35, `$190.00` reserved / `$210.00`
unreserved; after: revision 36, `$194.00` / `$206.00`.

Preregistered outcomes: (A) losses move below ln 3 and sealed accuracy moves
above chance → the representation was the blocker; (B) flat losses persist →
the next measured suspect is the module's operating point, separately
authorizable. Either way the result is recorded honestly; no learning claim
is precommitted.
