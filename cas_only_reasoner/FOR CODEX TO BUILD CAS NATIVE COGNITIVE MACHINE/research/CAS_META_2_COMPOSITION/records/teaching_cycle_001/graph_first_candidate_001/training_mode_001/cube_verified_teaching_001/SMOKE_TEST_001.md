# Execution smoke run of the deployed package — local GPU, not a measurement

Written 2026-09-10. This is an engineering check, not a result. It exists because
three paid attempts died on the instance in ways no local test had reached: a
missing import root, a missing torch environment, and a problem presentation the
frozen encoder cannot parse.

## What was run

`tools/graph6_candidate_smoke.py` unpacked `candidate_package_006/source.zip` —
the exact bytes the launcher uploads — installed the two frozen wheels from that
package into a scratch target, and executed the deployed code on the local
NVIDIA RTX 4070 Laptop GPU with `torch 2.11.0+cu128`, the same torch version the
worker installs. Both conditions were truncated to 3 updates each.

The machine-readable output is `SMOKE_RUN_001.json` (sha256
`1ea8c3a4ce0e3f02b68765f2a8b5af4a374f952167384f8caf36028cd9705c6a`).

## What it proves

| step | outcome |
| --- | --- |
| frozen encoder built on the device | ok, from the 52 publics (8 taught + 44 probe) |
| `encode_problem` on every public | 52 of 52, each a 64-dimensional vector — this is the call that failed on the instance at `vocabulary.index(_word_token('node'))` |
| training framework and model | built; `model is framework.module` |
| matched initial weights across conditions | true |
| parameter scope and containment check | contained: true for both conditions |
| checkpoint written, read back, verified | true for both conditions |
| probe measurement | 44 of 44 items for both conditions |
| bookkeeping | 6 optimizer updates, 0 automatic retries, 0 seven-stage neural cycles |

Every step of the pilot's own execution order (`EXECUTION_ORDER`, eleven phases)
is covered by that sequence.

## What it does not prove, and what none of its numbers are

- **No number in `SMOKE_RUN_001.json` is a measurement.** Three updates per
  condition on a laptop GPU say nothing about learning, and none of these figures
  may be reported as a result. The pilot's measurement requires the frozen 64
  updates per condition on the AWS instance.
- It runs the **local development GPU**, which the standing order permits for
  smoke and development only. Every claim-bearing run stays on AWS.
- It contacted no provider, created no reservation, and uploaded nothing.
- It cannot cover Linux-specific behaviour, the A10G on the paid instance, the
  venv install as the worker performs it, or data-transfer and delivery on S3 —
  though the environment stage is itself rehearsed by the package rehearsal and
  was observed working on the instance during attempt 006.

## What is left for a paid attempt to discover

The 64-update budget itself, the real probe numbers, and whatever the AWS
environment does that a laptop does not. The three defect classes found so far —
import root, torch environment, problem presentation — are each now covered by a
test or by this smoke run, so they cannot return silently.
