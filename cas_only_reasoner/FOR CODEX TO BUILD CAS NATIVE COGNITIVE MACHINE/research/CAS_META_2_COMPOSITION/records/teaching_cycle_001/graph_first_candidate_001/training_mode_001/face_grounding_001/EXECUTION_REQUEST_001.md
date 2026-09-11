# EXECUTION_REQUEST_001 — CUBE_FACE_GROUNDING_001 / CFC_LOOP_001

**Status: NOT AUTHORISED. Nothing has been reserved, launched or executed.**
This document is the single bounded execution request the builder handoff asks for.
It becomes actionable only when an owner instruction arrives and is recorded as a
hash-bound authorisation naming this request.

## What would run

| item | value |
| --- | --- |
| experiment | `cube_face_grounding_cfc` |
| entrypoint | `cas_meta2.graph_teaching.face_worker.run` |
| package | `records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/face_grounding_001/candidate_package_001/` |
| archive sha256 | `d7fe838ea9c82684f79686336ed07c08f636235e0b2e910dc8e40e6f89df3df9` |
| manifest sha256 | `f2fe66322a1ea8b34a5e566df619c94ed454e4b1ec64e2e8b44d26beff8c7c16` |
| source commit | `c307d6071c584e9fdb7ca3def787f9bdfbf1c630` |
| package bytes / members | 543,119 / 53 |
| request file | `candidate_request_001.json` (inert, `launch_authorized: false`) |
| request sha256 | `c645bc4948c5423faf628fb82dc3d7523f6eb5773126084eabfd76a02564b8f6` |
| job | `cas-meta2-graph6face-20260911063736-d7fe838e` |
| launcher | `aws/graph_training_face_launch.py` (binding), execution lifecycle reused from the proven path |
| reservation | `$7.00`, the campaign's standard ceiling, one reservation, no automatic retry |

## Conditions — four cells, and this is a declared deviation

Both owner plans proposed **one paired two-condition pilot**. This request instead
runs the four cells in one job, because the two questions are orthogonal and the
same events serve both:

| condition | organization | cue | question it answers |
| --- | --- | --- | --- |
| `cfc_stable_cues` | CFC loop (within → across → return) | per-role markers | does the loop teach at all? |
| `cfc_neutral_cue` | CFC loop | one neutral marker | does the explicit numbering add value inside the loop? |
| `mixed_order_stable_cues` | the same events, fixed shuffled order | per-role markers | does the alternation beat the same material in mixed order? |
| `mixed_order_neutral_cue` | mixed order | one neutral marker | the fourth cell; both plans' controls in one job |

The deviation is flagged rather than assumed: if the owner prefers the plans
verbatim, the same package runs any two of the four (`--conditions` in the worker
config selects them) as two sequential jobs, at the cost of a second reservation.
Everything else - the corpus, the tasks, the panel, the encoder, the scope - is
identical across the four cells.

## Schedule and resource bound

| quantity | value |
| --- | --- |
| events per condition | 4,608 supervised decisions (CFC loop: 6 cohorts x 16 rounds x 48) |
| batch size | 8 independent query episodes per optimizer step |
| optimizer updates per condition | 576 |
| total optimizer updates | 2,304 |
| supervised query presentations per condition | 4,608 (the grounding sweeps' 9,216 are the other declared organization) |
| evaluation | 96 recognition + 96 application + 24 diagnostics per condition, before and after, no updates |
| instance | one `g7.2xlarge`, the campaign's standard type |
| wall-clock ceiling | 3,600 s per condition, declared in the frozen design |
| reservation | `$7.00` |

The grounding-sweep organization (6,144 + 3,072 = 9,216 queries, 1,152 updates at
batch 8, 18,432 worked supports) is implemented and can be selected instead; it is
not what this request runs, and switching to it would be a design change requiring
its own approval.

## Shared and trainable state

- **Shared**: one frozen encoder, fitted once on the declared fitting corpus (2,740
  distinct texts covering every label, cue and panel item, all arms included), the
  same tokenizer, the same corpus, the same panel, the same schedule length and
  the same seed for every condition.
- **Matched**: each condition starts from weights built from the same seed, and the
  run fails closed if the initial snapshots differ.
- **Separate**: optimizer state and checkpoint per condition; four checkpoints are
  delivered with their hashes.
- **Trainable scope**: the accepted `operation:^6` allowlist only, checked before
  and after teaching by `trainer.scope_parameters` and
  `trainer.containment_report`; any forbidden change fails the run closed.
- **No architecture change**: no new head, no readout change, no parameter scope
  change. `batch_step` reaches the learner's own forward and optimizer.

## What the run does, in order

1. Build the corpus, the tasks, both schedules and the frozen panel (no model).
2. Fit the shared encoder and build the framework.
3. **Representation checks**, recorded whether or not they pass: changed roles,
   changed contents, a changed cue and a same-token rewiring must produce different
   model-facing vectors; scores and losses must be finite; a gradient must depend on
   the target. If these fail, that is a finding with a named restriction.
4. Teach every condition, batched, with per-episode rows carrying the correction
   pass's own scores and losses and the per-batch checkpoint linkage.
5. Evaluate the frozen panel before and after each condition with no updates.
6. Write the measurements, four checkpoints, the artifact manifest, the result
   envelope and its sidecar.

## Delivery, collection and shutdown policy

- The body writes `result.json` and its sidecar; the worker uploads artifacts and
  the manifest first and **`result.json` last**, because that is the completion
  marker the launcher waits for.
- Collection is verified against the artifacts the result declares; the evidence
  bucket is **deleted only after** verified collection, and retained otherwise.
- The instance is terminated on every exit path, including failure; the security
  group and IAM roles are removed; the run makes **zero automatic retries**.
- A failure writes `failure.json`, preserves any completed result as
  `result_partial.json`, and keeps the original error verbatim.
- If the wall-clock ceiling is reached before the planned exposure, the condition
  reports `TEACHING_INCOMPLETE` with the counts it reached, and the run does not
  present a partial allocation as the declared schedule.

## What the run will not do

- No retraining of anything already measured; Attempt 007 and its checkpoints stay
  untouched, as do the accepted models, historical negatives and the pending
  retained-checkpoint investigation.
- No claim about the earlier answer-selection question: this is a new, separately
  named candidate.
- No probe change after seeing an outcome, no threshold lowered after an outcome,
  and no checkpoint selected by final-panel performance - the final scheduled
  checkpoint is the one evaluated.
- No extension of the trainable scope, no new operation, no general language
  teacher at inference.
- Nothing is authorised by this document.

## What would make the result interpretable, and what would not

Recognising an unlabelled role while failing to apply it is category recognition
without demonstrated operational use. Repeating role names when the number is shown
is association only. Recognising and applying on held-out families is bounded
evidence of face-role grounding in this profile. Both cue arms performing similarly
means no demonstrated benefit from the explicit numbering, even if both learned. A
role that fails while others succeed is reported as that role's boundary, never
hidden in a macro average. The plans' capability targets are declared engineering
targets and do not by themselves establish that stable cues beat the neutral
control.
