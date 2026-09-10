# CANDIDATE_RUN_001 — checked component teaching: runnable preparation and proposed schedule

**Status:** preparation for approval. `execution_enabled: false`. No neural execution, no
reservation, no launcher, no paid run. `run_candidate` refuses to do anything without an
owner authorization record (`CANDIDATE_RUN_NOT_AUTHORIZED`).

**Label:** **checked component teaching.** Not a complete implementation or test of the
seven-stage cube program. Stages 1, 2, 3, 4 and 6 still have no numerical delivery path
and stay `UNIMPLEMENTED`.

**The question this candidate can answer:**

> Does teaching the smaller relationship decisions help the same learner answer the
> complete whole–part question?

It cannot show that cycling through all six faces and the core helped, because several of
those presentations would never reach the learner.

## 1. The wrapper, and why it is here rather than in `trainer.launch`

`candidate_run.run_candidate(...)` is the candidate-only wrapper. It enters at
`trainer.run_training`, which accepts records. The frozen `trainer.launch` is **not**
modified: it selects its registered whole-part dataset internally and has no
record-injection parameter, and adding one would change registered infrastructure.

Every dependency is injected (`framework`, `model`, `learner_factory`, `scorer`,
`checkpoint_writer`, `checkpoint_verifier`). This module imports no torch and constructs
no model, so preparing the run cannot execute it.

## 2. Execution order (explicit and versioned)

```
BUILD_AND_INDEX_FROM_EXACT_RECORDS     learner indexed from these records' public records
APPLY_PERMITTED_PARAMETER_SCOPE        trainer.scope_parameters -> operation:^6 only
TAKE_BEFORE_SNAPSHOT                   must precede the first update
  for each scheduled step:
    PER_STEP_CAPTURE_PREDICTION        the prediction being corrected, as it is
    PER_STEP_APPLY_CHECKED_TARGET      make_task -> learner.step -> cross-entropy
    PER_STEP_PERFORM_PERMITTED_UPDATE  the optimizer step inside step()
    PER_STEP_RECORD_UPDATE_IDENTITY    block, phase, record, target, update index
TAKE_AFTER_SNAPSHOT
COMPUTE_CONTAINMENT                    fail closed on any forbidden change
SAVE_AND_VERIFY_CHECKPOINT             identity must survive the round trip
WRITE_COLLECTED_OBSERVATIONS           missing measurements stay 'unavailable'
```

Two placements carry the meaning. The **before-snapshot precedes the first update**, or
containment cannot separate a trained change from an initial state. And each step's
**scores come from the prediction being corrected**, not from a fresh prediction
reconstructed after training.

The learner is indexed from the same records and the same encoded ordering the loop uses
(`adapter.public_records(record, arm)`). That is the requirement whose absence caused the
`KeyError` in curriculum attempt 002.

The module enforces the order at run time: each step refuses to begin if the previous
step's update identity was not recorded (`CANDIDATE_STEP_ORDER_VIOLATION`).

## 3. Proposed teaching schedule

| Field | Value |
|---|---|
| Profile | `cas-cube-component-teaching-schedule/1:8x8` |
| Structure | 8 blocks; each block = 5 component-route questions, then the 3 whole-answer questions |
| Component-to-final ratio | **5 : 3** |
| Repetition | **8 complete blocks** |
| Update allowance | **64 supervised corrections** |
| Operation exposure | `REACHED_VIA` 48, `LIST_PARTS` 8, `FIND_SHARED_PART` 8 |
| Stopping limits | 64 updates, 600 s wall clock, stop on containment failure, stop when the blocks complete, **0 automatic retries** |
| Budget profile | fits the frozen 64-step profile; **no profile change requested** |
| Counters | component-teaching blocks 8, component presentations 40, whole-answer presentations 24, seven-stage neural cycles **0** |

**Eight blocks is a chosen pilot allowance, not a proven minimum.** It is not
mathematically necessary and it has not been validated as sufficient for learning. It is
the smallest allowance this desk is willing to defend from the existing frozen budget
profile, and it fits that profile, so no budget-profile change is needed. Whether eight
blocks are enough is exactly what the pilot would measure.

**Repetition is per question, not per record.** Eight teaching records hold **seven
distinct questions**: `REACHED_VIA(Bicycle, Rim)` appears once as a component question and
once as a whole-answer question, so that route receives **16 corrections across the eight
blocks** while the other six distinct questions receive 8 each. The repetition is intended
and is reported rather than hidden.

**What it does not inherit.** The stub's 48/8/8 step allocation, the 64-step frozen
default as a teaching principle, and the earlier binding experiment's 1,024-cycle
allocation.

**An honest coincidence.** The per-operation totals (48 / 8 / 8) *coincide* with the
stub's, because both give every one of the eight questions equal practice. The design here
is the declared block structure and the declared 5:3 component-to-final ratio, not the
stub's cycle order. If the owner wants a different emphasis — for example three component
blocks per whole-answer block — the schedule scales and the totals will differ; that is a
curriculum decision, not a data one.

**Larger schedules must declare a budget change.** `proposed_schedule(12)` gives 96
updates and sets `requires_budget_profile_change: true`, because
`trainer.TrainingBudget` refuses anything but the frozen 64 steps / 600 s
(`BUDGET_MAX_OPTIMIZER_STEPS_FROZEN`). Restarting a 64-step call repeatedly to evade the
limit is not an option; a versioned profile would need the owner's approval.

## 4. Proposed evaluation

| Item | Proposal |
|---|---|
| Conditions | `checked_component_teaching` (**40** component + **24** whole-answer) versus `final_answer_only` (**0** + **64**), same update allowance |
| Control schedule | frozen before any result: round-robin over the three whole-answer questions, remainder to the first → **22 / 21 / 21**; exposure `LIST_PARTS` 22, `FIND_SHARED_PART` 21, `REACHED_VIA` 21 |
| Matched comparison | two candidate copies from the **same initial weights**; same frozen encoder, graph, framing, scoring, seed and limits; **separate** optimizer state and checkpoints; the allocation is the only intended difference |
| Primary measure | **independent** accuracy on the three taught whole-answer questions — no worked answer, no teacher-verified subanswers, no correct prefix. "Independent" means no worked answer during prediction; it does **not** mean the taught questions became unseen |
| Reporting | before and after: selected answer, all three scores, and loss for each of the three taught questions; component questions separately; probe by operation |
| Untaught probe | **44 questions** = 51 catalog − **7 distinct taught** (`REACHED_VIA` 25, `FIND_SHARED_PART` 14, `LIST_PARTS` 5), the **same set for both conditions**, keyed on graph context + operation + named arguments with exercise ids and phase labels ignored, no additional exclusions — **within-scene generalisation only, never transfer to a new graph arrangement** |
| Probe constraints | it never selects a checkpoint, adjusts the curriculum, or extends training mid-run; the final checkpoint is fixed by the declared schedule |
| Sample-size warning | three taught questions: one changed answer moves accuracy by 33.3 percentage points, so no single percentage carries the conclusion |
| Not measured | definition, analogy, correspondence and story content |
| Owner decisions still needed | condition count, allowance, whether the probe is used, whether any budget-profile change is approved |
| Cost | see `AUTHORIZATION_REQUEST_001.md`: `$7.00` proposed by reusing the existing resource plan, or `$4.00` with a changed `instance_seconds_max`; **an unspecified cost is not approved** |

**What the comparison can show:** at the same number of updates, is it better to spend some
practice on the parts of the problem rather than spend every update on the complete
questions?

**What it cannot show:** it does not isolate the effect of adding component instruction
while holding final-question practice equal — the control practises the final questions far
more often. A third condition would be needed, and none is proposed.

**A negative result would mean:** this component-teaching allocation did not help under
these conditions. It would not mean the complete seven-stage method failed.

## 5. What the counters say

From the successor check report (`check_report.json`, revision 3):

```json
{"stub_training_step_calls": 64,
 "actual_optimizer_updates": 0,
 "actual_neural_presentations": 0,
 "learner_is_a_stub": true, "torch_imported": false, "neural_execution": false}
```

The earlier field name `optimizer_updates_in_this_check` read as though a model had been
trained. It has been replaced by the three fields above, and the correction is recorded in
the successor report under `field_correction`. The previous report is preserved unchanged
as `check_report_rev2.json` (sha256 `5e145595…e545b`).

The rehearsal in `tests/test_graph_teaching_candidate_run.py` drives the wrapper with
injected stubs and confirms the placement: 64 recorded predictions, each taken before its
own update (`predictions_taken_before_their_update: true`), 40 component-phase and 24
whole-answer-phase steps, containment clean, checkpoint verified. **That is an instrumented
software rehearsal, not a neural result.**

## 6. What a real run would still need

1. An owner authorization record naming the run (`owner_go: true`, `run_id`) — the fields
   are laid out in `AUTHORIZATION_REQUEST_001.md`.
2. **An approved launcher binding.** The existing launcher's frozen design block belongs to
   the curriculum experiment, so this pilot needs its own bound request (two conditions, 64
   updates each, seed `20260909`, the 44-question probe, its own entrypoint and job
   pattern). That binding is proposed, not built: the owner asked to reuse the
   infrastructure rather than add another launcher, so the change is made only after this
   request is approved.
3. A framework, model, and learner factory from the real path, indexed from these records.
4. A scorer, so the scores are captured rather than recorded as `unavailable`.
5. A checkpoint writer and verifier.

No neural execution, reservation, or paid launch is authorized until that specific request
is approved. The fixed architecture, readout, previous results, checkpoints, and the
pending zero-update contrast probe are untouched.
