# Execution request — CFC Pilot Readout (recovery of attempt 004's lost detail)

Prepared for the owner's specific GO. Nothing has been launched, reserved or
executed. The package is built and inert (`launch_authorized: false`), the request
and authority validate, and the packaged worker has been rehearsed locally.

## What this job does

Attempt 004 trained all four conditions and delivered four verified checkpoints. It
also wrote a `measurements.json` holding the per-face breakdowns, the per-question
rows, the before/after pairing, the constant-rule baselines and the milestone
report. The body declared only the four `.pt` files as artefacts, so verified
collection kept the checkpoints, and cleanup then deleted the bucket. The payload is
gone; its digest survives.

This job loads those four checkpoints and answers the frozen panel from them, with
**zero optimizer steps**, and writes the missing detail into its own record
directory.

What it will produce:

- per-condition, per-face counts and macro accuracy for `role_recognition`,
  `role_application` and `targeted_check`;
- every per-question row for the 192 primary questions and the 24 diagnostics;
- the before/after pairing per layer (before readings from a deterministically
  reconstructed initial state — labelled as reconstructed, because the run's own
  initial-weight digest was in the lost payload);
- the constant-rule baselines per layer, from the delivered option order;
- the plan's milestone report, including which faces fall below the 0.50 minimum;
- the four declared paired comparisons, which the delivered envelope could not
  carry because a valid paired test needs the per-question rows.

## Why it is a recovery and not a new measurement

Three gates, all bound into the authority:

1. **The weights are the delivered ones.** Each checkpoint file's sha256 is bound in
   the authority and checked before the file is read; after loading, the live
   module's parameter digest must equal the identity recorded inside the checkpoint.
2. **Zero updates is measured, not asserted.** The parameter digest is taken again
   after each panel pass; a change during the before pass or the after pass fails
   the job closed. Both guards have tests.
3. **The arithmetic must reproduce what was published.** The recomputed per-layer
   totals must equal the totals attempt 004 published — 76/96, 75/96, 74/96, 76/96
   application; 55/96, 56/96, 47/96, 52/96 recognition; 15/24, 15/24, 16/24, 16/24
   diagnostics — with those numbers bound by digest. A mismatch is delivered as
   `READOUT_FAILED` and is not presented as the recovered detail.

## What it explicitly does not do

No training. No optimizer step. No gradient computed. No checkpoint written. No
attempt-004 or attempt-007 record touched. No panel, threshold or comparison
changed. No claim about why recognition is weak, or which arm is better — it
reports counts, and the paired comparison it recovers is a count of discordant
questions, not a significance result.

## Identities

| item | value |
|---|---|
| job | `cas-meta2-graph6read-20260911144249-35a06773` |
| source commit | `b3fa9d9fa6a50967f3ca9bd19b36ba5e6f0cb353` |
| package | `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/face_grounding_001/readout_package_001/` |
| archive sha256 | `35a0677326b0fea5da1aa8bf1c45ca370b5dc80d01c1bd4e14320ec0001de0c2` |
| manifest sha256 | `2ab95d91d3a854909c6e0309616131f0c0d98634ea4783f76e45f3164d2b814d` |
| archive bytes | 802,771 |
| request | `candidate_request_readout_001.json` sha256 `75021d689ba7a692d25775f5fa920e750d4a9f0c05e365d7a79b6f52c071ed9d` |
| authority | `candidate_authority_readout_001.json` sha256 `62134bce3ea873df696afb525b39d2df27f1702eb584da1293221d6b1516164a` |
| owner authorisation | `OWNER_AUTHORIZATION_READOUT_001.json` sha256 `e88cdca96ccfc6d3ac63167689887c8dc3fa74954b262e9c5204ac0414068c05` |
| readout of | job `cas-meta2-graph6face-20260911133305-9723735f` (attempt 004) |
| lost payload digest | `796658502cba1d3a03f026d3c7f5c97365de7bb35d7f312a5b105e0fa59dffee` |

## Bounds and cost

| bound | value |
|---|---|
| jobs | 1 |
| conditions | the four declared conditions |
| optimizer updates | 0 |
| training | false |
| panel | 192 primary + 24 diagnostics |
| readout ceiling | 1200 s |
| install allowance | 600 s (the proven venv/torch scaffolding) |
| total wall-clock ceiling | 1800 s, inside the 7200 s instance ceiling |
| reservation | `$7.00` — the campaign's standard single-instance reservation |
| automatic retries | 0 |
| instance | `g7.2xlarge`, RTX PRO 4500, us-west-2, AMI `ami-0fbbd0facbc9e3cff` |

The `$7.00` figure is the resource plan's instance envelope, not a measure of this
job's work: the same reservation covers a two-hour instance ceiling, and this job's
own work is minutes. The reservation amount is fixed by the proven provider path,
which reserves exactly `$7.00`; changing it would alter the shared lifecycle rather
than this job. Ledger: `$67.00` free now, `$60.00` after the reservation, revision
60 → 61.

## Local rehearsal already done

- 50 readout tests pass: the module's control flow under stub factories (including a
  module that drifts during the before pass and one that drifts after the load), the
  launcher's plan, bounds, every frozen authority field, and the package inputs.
- The package rehearsal unpacks the delivered `source.zip`, confirms the worker is
  byte-identical to the rendered one, confirms each checkpoint member hashes to the
  delivered value **inside the archive**, and compiles the plan in a subprocess under
  the packaged code — where the four checkpoint paths must resolve and each file must
  hash to the bound value. That last check is the one that would otherwise be
  discovered on a paid run.
- The four checkpoints round-trip through git byte-identically, which is what makes
  a binary artefact survive the builder's read-from-git path.

## The command, on GO

```
python -m aws.graph6_face_readout_launch --execute \
  --request  records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/face_grounding_001/candidate_request_readout_001.json \
  --request-sha256 75021d689ba7a692d25775f5fa920e750d4a9f0c05e365d7a79b6f52c071ed9d \
  --authority records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/face_grounding_001/candidate_authority_readout_001.json \
  --authority-sha256 62134bce3ea873df696afb525b39d2df27f1702eb584da1293221d6b1516164a \
  --owner-authorization records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/face_grounding_001/OWNER_AUTHORIZATION_READOUT_001.json \
  --receipt-dir records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/face_grounding_001/receipt_cas-meta2-graph6read-20260911144249-35a06773
```

Awaiting the owner's specific GO for this one reservation and one launch.
