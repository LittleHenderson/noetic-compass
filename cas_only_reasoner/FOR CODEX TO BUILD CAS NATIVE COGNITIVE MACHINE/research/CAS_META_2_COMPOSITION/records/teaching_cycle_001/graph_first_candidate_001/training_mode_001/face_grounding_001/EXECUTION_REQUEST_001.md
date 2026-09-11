# EXECUTION_REQUEST_001 — CFC Loop × Face-Cue Pilot

**Status: NOT AUTHORISED. Nothing has been reserved, launched or executed.**
This is the finalised request, returned once with the owner's pre-signature
clarifications applied. It becomes actionable only when an owner instruction
arrives and is recorded as a hash-bound authorisation naming this request.

## What would run

| item | value |
| --- | --- |
| experiment | **CFC Loop × Face-Cue Pilot** (`cfc_loop_face_cue_pilot`) |
| entrypoint | `cas_meta2.graph_teaching.face_worker.run` |
| package | `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/face_grounding_001/candidate_package_001/` |
| archive sha256 | `382aa3fc179fb0f7b6f11d2b72a5e7d6786ffa930c124f33ef4f7079b4c8a9ac` |
| manifest sha256 | `8366e225a9c1d24bf0d6cedd2f963c49eb89d5db1faae8e8d9cfd010a7d87fc9` |
| source commit | `b285a10c34fb80745b1d30bd8d9fd310d1f54897` |
| package bytes / members | 543,430 / 53 |
| request file | `candidate_request_001.json` (inert, `launch_authorized: false`) |
| request sha256 | `d5df7cbf2b135315de3ae71d712bbbb4226e31abbcc5312775dfe1b5d5c6e045` |
| job | `cas-meta2-graph6face-20260911120508-382aa3fc` |
| launcher | `aws/graph_training_face_launch.py` (binding); execution lifecycle reused from the proven path |
| reservation | `$7.00`, one reservation, zero automatic retries |
| instance | one `g7.2xlarge` |

## The selected schedule, stated exactly

This job runs the **CFC loop schedule**, not both original schedules in full. The
numbers below are read from the schedule module the worker executes
(`face_schedule`), so the request cannot state counts the run would not deliver.

| per condition | value |
| --- | --- |
| supervised decisions | **4,608** |
| — within-cube (7 stages × 4 cubes × 96 rounds) | 2,688 |
| — across-face (6 roles × 2 decisions × 96 rounds) | 1,152 |
| — return-to-cube (4 cubes × 2 decisions × 96 rounds) | 768 |
| completed rounds | 96 (6 cohorts × 16) |
| worked-support exposures | 6,912 (72 per round) |
| optimizer updates at batch size 8 | **576** |
| evaluation | 96 recognition + 96 application + 24 diagnostics, before and after, no updates |

| across four conditions | value |
| --- | --- |
| supervised decisions | 18,432 |
| optimizer updates | **2,304** |

**Not run:** the face-grounding plan's Phase A/B schedule — 9,216 supervised
queries, 18,432 worked supports, 1,152 updates per condition — is implemented and
selectable (`ORGANIZATION="GROUNDING"`), but it is not what this job delivers. This
is the combined CFC pilot, not delivery of both original schedules in full.

## Conditions — four cells, one job

By owner ruling, the four cells run together so both questions are answered from
one matched initialization and one reservation:

| condition | organization | cue |
| --- | --- | --- |
| `cfc_stable_cues` | CFC loop | per-role markers |
| `cfc_neutral_cue` | CFC loop | one neutral marker |
| `mixed_order_stable_cues` | the same events, fixed shuffled order | per-role markers |
| `mixed_order_neutral_cue` | mixed order | one neutral marker |

Comparisons: loop against mixed (A vs B, C vs D), numbered cues against neutral
(A vs C, B vs D), and whether the loop's advantage changes when the cues are
present.

**The organization difference is real at the update-batch level, not cosmetic.**
Loop and mixed share **zero whole update batches out of 576**, and **no batch
coincides anywhere** between the two organizations, while the teaching-event
multiset and each event's supports stay identical (pinned by tests). Within each
condition a single learner carries continuing weights and optimizer state across
all 4,608 decisions, and the loop orders within-cube before across-face before the
return in every round, so earlier phases can affect later ones.

## Bounds

| item | value |
| --- | --- |
| per-condition wall-clock ceiling | 1,500 s |
| environment install allowance | 600 s |
| total job ceiling | **6,600 s** |
| reservation instance ceiling | 7,200 s |
| fits | yes, with 600 s of slack — and `validate_bounds` now refuses any design that does not |

A condition that reaches its ceiling before its planned exposure reports
`TEACHING_INCOMPLETE` with the counts it reached; the run never presents a partial
allocation as the declared schedule.

## Shared and trainable state

- **Shared**: one frozen encoder, fitted once on the declared fitting corpus (2,740
  distinct texts covering every label, cue and panel item, all arms included); the
  same tokenizer, corpus, panel, schedule length and seed for every condition.
- **Matched**: every condition starts from weights built from the same seed, and the
  run fails closed if the initial snapshots differ.
- **Separate**: optimizer state and checkpoint per condition; four checkpoints are
  delivered with their hashes.
- **Trainable scope**: the accepted `operation:^6` allowlist only, checked before
  and after teaching by `trainer.scope_parameters` and `trainer.containment_report`.
- **No architecture change**: no new head, no readout change, no scope change.

## What the run does, in order

1. Build the corpus, tasks, schedule and frozen panel (no model).
2. Fit the shared encoder and build the framework.
3. **Representation and gradient checks, recorded whether or not they pass**:
   changed roles, changed contents, a changed cue and a same-token rewiring must
   produce different model-facing vectors; scores and losses must be finite; a
   gradient must depend on the target. These check that the inputs are usable and
   the correction path functions — they do **not** demand mastery before the
   repeated teaching has occurred, and the job proceeds into the declared training
   without a further approval interruption.
4. Teach all four conditions, batched, keeping per-episode rows with the correction
   pass's own scores and losses and the per-batch checkpoint linkage.
5. Evaluate the frozen panel before and after each condition, no updates.
6. Write measurements, four checkpoints, the artifact manifest, the result envelope
   and its sidecar.

## Delivery, collection and shutdown

- The body writes `result.json` and its sidecar; the worker uploads artifacts and
  manifest first and **`result.json` last**, because that is the completion marker.
- Collection is verified against the artifacts the result declares; the evidence
  bucket is deleted **only after** verified collection, and retained otherwise.
- The instance is terminated on every exit path; security group and roles removed;
  **zero automatic retries**.
- A failure writes `failure.json`, preserves any completed result as
  `result_partial.json`, and keeps the original error verbatim.

## What would make the result interpretable, and what would not

Reported separately, never pooled: recognising a face role from unfamiliar content;
applying that role correctly; returning to an idea and answering correctly; and any
additional benefit from the loop, the numbered cues, or their combination. Per-face
counts are reported, and a role that fails while others succeed is reported as that
role's boundary rather than hidden in a macro average. Baselines are reported from
the delivered option order, so an aggregate above a constant-rule baseline is not
mistaken for the intended skill.

The 192 primary questions are views of 16 held-out families, not 192 independent
ideas, and the corpus has 96 families over six structural arrangements, so
structure overlap is reported separately from family overlap. The four conditions
are four candidates trained from **one** matched initialization: this is an
exploratory comparison, not a replicated finding across seeds, and the report says
so.

## What the run will not do

- No retraining of anything already measured; Attempt 007, its checkpoints, the
  accepted models, historical negatives and the pending retained-checkpoint
  investigation stay untouched.
- No claim about the earlier answer-selection question: this is a new, separately
  named candidate.
- No probe change after seeing an outcome, no threshold lowered after an outcome,
  no checkpoint chosen by final-panel performance.
- No scope extension, no new operation, no general language teacher at inference.
- Nothing is authorised by this document.
