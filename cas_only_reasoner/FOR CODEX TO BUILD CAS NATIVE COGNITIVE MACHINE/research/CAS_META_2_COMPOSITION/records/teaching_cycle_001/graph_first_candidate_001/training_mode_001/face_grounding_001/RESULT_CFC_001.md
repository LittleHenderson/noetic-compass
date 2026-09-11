# CFC Loop × Face-Cue Pilot — result of attempt 004

Job `cas-meta2-graph6face-20260911133305-9723735f`, receipt
`receipt_cas-meta2-graph6face-20260911133305-9723735f/`.
Status `AWS_CANDIDATE_FINISHED`, `completed_deliverable: true`, execution
FINISHED, collection VERIFIED, cleanup COMPLETE, elapsed 724.33 s.
Instance `i-046de3ddc12d5835e` (`g7.2xlarge`, RTX PRO 4500, us-west-2)
CONFIRMED_TERMINATED, bucket deleted, no cleanup failures.
Ledger revision 60 = `$333.00` reserved / `$67.00` free.

## What was executed

Four conditions, one initialization, batch of 8, seed 20260912, encoder seed
20260909, learning rate 0.003:

| condition | organization | cue | delivered | updates | checkpoint |
|---|---|---|---|---|---|
| `cfc_stable_cues` | CFC loop | stable | 4608/4608 | 576 | verified |
| `cfc_neutral_cue` | CFC loop | neutral | 4608/4608 | 576 | verified |
| `mixed_order_stable_cues` | mixed order | stable | 4608/4608 | 576 | verified |
| `mixed_order_neutral_cue` | mixed order | neutral | 4608/4608 | 576 | verified |

2,304 updates total, as derived from the packaged schedule. Boundary recorded
in the envelope: 0 automatic retries, 0 seven-stage neural cycles, scores taken
from the correction pass.

## What the collected evidence contains

Three layer totals per condition, and nothing else:

| condition | recognition (96) | application (96) | targeted check (24) |
|---|---|---|---|
| `cfc_stable_cues` | 55 = 0.572917 | 76 = 0.791667 | 15 = 0.625000 |
| `cfc_neutral_cue` | 56 = 0.583333 | 75 = 0.781250 | 15 = 0.625000 |
| `mixed_order_stable_cues` | 47 = 0.489583 | 74 = 0.770833 | 16 = 0.666667 |
| `mixed_order_neutral_cue` | 52 = 0.541667 | 76 = 0.791667 | 16 = 0.666667 |

Chance on a three-option question is 1/3 = 0.333333.

### Evidence lost in this attempt (my defect)

`results/measurements.json` was written by the body and uploaded by the outer
worker, but the body declared only the four `.pt` checkpoints as artefacts.
Verified collection keeps exactly the declared artefacts, so the five objects
collected were the four checkpoints plus the result envelope, and cleanup then
deleted the bucket. The lost object held: the representation and gradient
checks, the per-face breakdowns, the before/after readings per condition, the
per-question rows, the constant-rule baselines and the milestone report. Its
digest survives in the envelope as `measurements_sha256 =
796658502cba1d3a03f026d3c7f5c97365de7bb35d7f312a5b105e0fa59dffee`, which
fixes what was lost without recovering it.

Consequences for what may be reported:

- **Per-face reporting is unavailable.** The design requires each face's count
  and the macro average, never one pooled number. Only the pooled totals survive.
- **No paired comparison is available.** The four conditions answered the same
  192 questions, so any valid test is paired, and the paired rows are gone. The
  differences below are counts of questions, not tested effects.
- **The milestone report cannot be evaluated as declared**, because two of its
  three clauses need the per-face buckets.

Two derivations are still sound, because the retained panel manifest
(`EVALUATION_PANEL.json`) records exactly 16 questions per face in each
96-question layer:

- For those two layers the aggregate over 96 questions equals the macro average
  over the six faces. So the recognition macro is 0.489583–0.583333, below the
  declared 0.75 target in all four conditions (NOT MET), and the application
  macro is 0.770833–0.791667, at or above the declared 0.70 target in all four
  conditions (MET).
- In `mixed_order_stable_cues` the recognition aggregate is 0.489583. If every
  face were at or above the declared 0.50 minimum, the mean could not be below
  0.50, so **at least one face is below 0.50 in that condition**. Which face is
  not recoverable from the retained evidence.

## What the numbers license

- **Applying a requested face role to a held-out family is above chance in all
  four conditions** (0.770833–0.791667 against 0.333333), with no condition
  near chance. This is bounded evidence of face-role grounding in the
  application layer.
- **Recognition is above chance in all four conditions but below the declared
  target in all four** (0.489583–0.583333 against 0.75). Reading a role from
  another cube's presentation is learned only weakly at this budget.
- **No benefit from the CFC loop is established.** Against the mixed-order
  control: application 76 vs 74 (+2 of 96) with stable cues and 75 vs 76 (−1 of
  96) with neutral cues; recognition 55 vs 47 (+8 of 96) and 56 vs 52 (+4 of
  96). The recognition differences agree in sign, and are 4.2–8.3 percentage
  points, but with no paired rows they carry no test result.
- **No benefit from the numbered cue is established.** Against the neutral cue:
  application +1 and −2 of 96; recognition −1 and −5 of 96. The sign flips
  between cue comparisons, which is the pattern expected of noise.
- Recognition without application, or application without recognition, is not
  separably reported here, because the per-question rows are lost.

## Scope limits

- Four conditions from one initialization: exploratory, not a replication.
- The 192 primary questions are views of 16 held-out families, not 192
  independent families.
- 96 authored graphs but only 6 distinct topologies, so a "correct" answer can
  in principle be reached by topology matching rather than whole-part reasoning.
- `measurements_sha256` proves what was lost; it does not stand in for it.

## Recovery, if the owner wants it

The four checkpoints were collected and their hashes match the envelope, so a
**zero-update reread** would regenerate the per-face, per-question, baseline and
milestone detail for the trained conditions, and re-derive the before readings
from the recorded seeds. That is neural execution on a claim-bearing reading and
therefore needs its own authorisation and its own reservation. Its cost is far
below attempt 004's `$7.00`, since no training is done.

## Change made in response

`face_worker.deliver` now writes the measurements object **into** the artefact
directory and declares it alongside the checkpoints, and the staging rule takes
every regular file except the manifest rather than `.pt` files only. The
declaration is now exercised end to end by
`tests/test_graph_teaching_face_grounding.py::
test_the_measurements_payload_is_declared_so_collection_cannot_drop_it`, which
runs the real stager and then the worker's own uploader, so a future run cannot
upload a payload that verified collection will discard.
