# Targeted ^6 specialist — REPLACEMENT AWS authorization request (NOT LAUNCHED, NOT RESERVED)

Status: **AWAITING_OWNER_APPROVAL.** One corrected replacement job is
registered; no reservation has been made and nothing has been launched. The
owner's signed record must bind the identities below.

## What this replacement fixes (established, evidence-backed)

| Prior attempt | Stopped by | Class |
|---|---|---|
| graph 001 | result-wait mishandled "not available yet" | launcher error handling — nothing about learning |
| graph 002 | missing `CAS_META2_RUN_TEACHING_CYCLE=1` | startup permission switch — nothing about learning |
| graph 003 | `fit_train` received a tuple instead of a list | package encoder contract — nothing about learning |

Binding-fit attempt 003's lost error remains **UNKNOWN** (hypothesis-only).

## Environment wiring — PROVEN to reach the child process

A non-neural probe executed the VERBATIM export lines of the rendered
bootstrap in a real shell and ran a real child process that recorded what it
actually observed:

- `training_mode_001/checks_003/env_probe.json` (sha256
  `d6af9f74633e542a114103b15193d8f4e8418718909a562e046b39f2f46291ee`):
  `child_observed = {"CAS_META2_RUN_TEACHING_CYCLE": "1"}` with
  `aws_calls: 0`, `model_execution: false`.
- Regression test
  `tests/test_graph_training_launch.py::test_user_data_env_reaches_the_child_process`
  locks the same proof (launcher suite now 17).

## Replacement job identity (inert until signed)

| Field | Value |
|---|---|
| proposed job | `cas-meta2-teaching-graph-20260909030210-e1408e1a` |
| launch request sha256 | `fdb7cb6e5bf68b4672c970986a3ba5e04dd92a0112c6ac728da148785c78a7bf` |
| training package (UNCHANGED from corrected package_003) | source `27f5efffb0f53acfa495fa74ff639ae23d08bec1` / archive `a4c07dda808615a250379f962db04aa9b9b1bbc4832f5dd686bfbfd6673605ae` / manifest `1f554acf769fc612ed0b8de8300d40728afc53beda122ea0033bd526b4aec1ec` |
| corrected launcher | `aws/graph_training_launch.py` at commit `65fa6b46` (ClientError wiring `4fd22968`; enable export + 600 s termination wait `7eec3604`; child-process env probe test) |

## Preserved limits and protections (unchanged)

- Per condition: 64 optimizer steps, 600.0 wall seconds, lr 0.003; totals 128
  steps / 1200 s in ONE job; conditions `prompt_framing_only`.
- Data: train 48 + practice 16 (whole-part); validation 16 + test 16 sealed,
  predictions recorded before answers.
- One `$4.00` reservation, no refund, no automatic retry; bounded readiness
  checks; error capture preserving the original error; shutdown protection
  (600 s termination wait); verified cleanup on every exit; containment
  report naming any parameter change outside `operation:^6`.

## Ledger arithmetic (exact, current)

Campaign ledger is at revision 26: `total_reserved_usd = 154.00`,
`remaining_unreserved_usd = 246.00` (cap `400.00`). A separately approved
`$4.00` replacement reservation would move it to `158.00` reserved /
`242.00` unreserved. These are campaign reservations, not AWS invoices.

## Next substantive result required

Actual lesson exposure per operation, actual completed optimizer updates,
before/after per-op losses, checkpoint identities, the containment report,
sealed-split evaluation — or an intact preserved error naming the next
failed stage. No automatic reservation or launch will occur.
