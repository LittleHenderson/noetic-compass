"""The instrumented candidate run: explicit execution order and teaching schedule.

STATUS: preparation only. ``run_candidate`` refuses to do anything without an
owner authorization record, and nothing in this module imports torch, a provider,
a launcher, or a reservation. No neural execution is authorized by this file.

Owner review asked for three things, and this module is those three things:

* the **candidate-only wrapper around ``trainer.run_training``** — the frozen
  ``trainer.launch`` is not modified to inject records;
* an **explicit chronological order** for the existing instrumentation: scope the
  permitted parameters and take the BEFORE snapshot before the first update,
  capture each step's actual prediction and correction as they happen, then take
  the AFTER snapshot, compute containment, and save and verify the checkpoint;
* a **proposed teaching schedule** for the supported component-route and
  whole-answer exercises that does not silently inherit the stub's 48/8/8 step
  allocation or the frozen 64-step default as a scientific design.

What this is not: a complete implementation or test of the seven-stage cube
program. It is **checked component teaching**. Stages 1, 2, 3, 4 and 6 have no
numerical delivery path and stay that way.
"""
from __future__ import annotations

from .graph import canonical, require
from . import cube_node, trainer, verified_training as vtr

CANDIDATE_SCHEMA = "cas-cube-verified-teaching-candidate-run/1"
SCHEDULE_SCHEMA = "cas-cube-component-teaching-schedule/1"

# The exact chronological order. A step may not be moved earlier or later
# without a versioned change to this list, because the placement is what makes
# the readings meaningful: the BEFORE snapshot must precede the first update, and
# a step's scores must come from the prediction that step is correcting.
EXECUTION_ORDER = (
    "BUILD_AND_INDEX_FROM_EXACT_RECORDS",
    "APPLY_PERMITTED_PARAMETER_SCOPE",
    "TAKE_BEFORE_SNAPSHOT",
    "PER_STEP_CAPTURE_PREDICTION",
    "PER_STEP_APPLY_CHECKED_TARGET",
    "PER_STEP_PERFORM_PERMITTED_UPDATE",
    "PER_STEP_RECORD_UPDATE_IDENTITY",
    "TAKE_AFTER_SNAPSHOT",
    "COMPUTE_CONTAINMENT",
    "SAVE_AND_VERIFY_CHECKPOINT",
    "WRITE_COLLECTED_OBSERVATIONS",
)

# The schedule proposal. Eight blocks of eight steps: five component-route
# questions, then the three whole-answer questions, repeated.
PROPOSED_SCHEDULE = {
    "schema": SCHEDULE_SCHEMA,
    "profile_id": "cas-cube-component-teaching-schedule/1:8x8",
    "kind": "CHECKED_COMPONENT_TEACHING",
    "component_questions_per_block": 5,
    "whole_answer_questions_per_block": 3,
    "component_to_final_ratio": "5:3",
    "ordering_within_block": "the five component-route questions, then the three "
                             "whole-answer questions",
    "blocks": 8,
    "updates": 64,
    "minimum_repeated_teaching_blocks": 8,
    "stopping_limits": {
        "max_optimizer_updates": 64,
        "max_wall_seconds": 600,
        "stop_on_containment_failure": True,
        "automatic_retries": 0,
        "stop_when_blocks_complete": True,
    },
    "why_this_many": (
        "eight complete passes give every question eight supervised corrections; "
        "the update count is the block structure multiplied out (8 x 8), not the "
        "frozen default adopted as a principle. It happens to fit the frozen "
        "64-update budget profile, so no budget-profile change is needed"),
    "does_not_inherit": [
        "the stub's 48 / 8 / 8 step allocation",
        "the 64-step frozen default as a teaching principle",
        "the earlier binding experiment's 1,024-cycle allocation",
    ],
    "requires_budget_profile_change": False,
    "budget_profile_note": (
        "fits the frozen 64-step budget profile (trainer.FROZEN_MAX_OPTIMIZER_STEPS)"),
    "per_operation_totals_note": (
        "the per-operation totals (48 route, 8 list, 8 shared) coincide with the "
        "stub's, because both give every one of the eight questions equal practice. "
        "The design here is the declared block structure — five component questions "
        "then the three whole-answer questions, eight times — and the declared 5:3 "
        "component-to-final ratio, not the stub's cycle order"),
    "counts": {
        "component_teaching_blocks": 8,
        "component_question_presentations": 40,
        "whole_answer_presentations": 24,
        "supervised_corrections": 64,
        "seven_stage_neural_cycles": 0,
        "distinct_graph_families": 1,
    },
    "counters_note": ("this partial method is counted in component-teaching blocks; "
                      "it is not a complete seven-stage neural cycle and must not "
                      "be reported as one"),
}

ALTERNATIVE_SCHEDULE = {
    "schema": SCHEDULE_SCHEMA,
    "profile_id": "cas-cube-component-teaching-schedule/1:12x8",
    "kind": "CHECKED_COMPONENT_TEACHING",
    "blocks": 12,
    "component_to_final_ratio": "5:3",
    "updates": 96,
    "minimum_repeated_teaching_blocks": 12,
    "requires_budget_profile_change": True,
    "budget_profile_note": (
        "trainer.TrainingBudget refuses anything but the frozen 64 steps / 600 s "
        "(BUDGET_MAX_OPTIMIZER_STEPS_FROZEN), so 96 updates needs a declared, "
        "versioned budget profile approved by the owner"),
}


def proposed_schedule(blocks=None):
    """The schedule proposal, or a scaled variant of it."""
    schedule = dict(PROPOSED_SCHEDULE)
    if blocks is None or blocks == PROPOSED_SCHEDULE["blocks"]:
        return schedule
    require(type(blocks) is int and blocks > 0, "CANDIDATE_SCHEDULE_BLOCKS")
    per_block = (PROPOSED_SCHEDULE["component_questions_per_block"]
                 + PROPOSED_SCHEDULE["whole_answer_questions_per_block"])
    updates = blocks * per_block
    scaled = dict(schedule)
    scaled["profile_id"] = "%s:%dx%d" % (SCHEDULE_SCHEMA, blocks, per_block)
    scaled["blocks"] = blocks
    scaled["updates"] = updates
    scaled["minimum_repeated_teaching_blocks"] = blocks
    scaled["stopping_limits"] = {**schedule["stopping_limits"],
                                 "max_optimizer_updates": updates}
    scaled["counts"] = {
        **schedule["counts"],
        "component_teaching_blocks": blocks,
        "component_question_presentations":
            blocks * PROPOSED_SCHEDULE["component_questions_per_block"],
        "whole_answer_presentations":
            blocks * PROPOSED_SCHEDULE["whole_answer_questions_per_block"],
        "supervised_corrections": updates,
    }
    scaled["requires_budget_profile_change"] = updates > trainer.FROZEN_MAX_OPTIMIZER_STEPS
    scaled["budget_profile_note"] = (
        "fits the frozen %d-step budget profile" % trainer.FROZEN_MAX_OPTIMIZER_STEPS
        if not scaled["requires_budget_profile_change"] else
        "exceeds the frozen %d-step budget profile: a versioned profile must be "
        "declared and approved" % trainer.FROZEN_MAX_OPTIMIZER_STEPS)
    return scaled


def scheduled_steps(records, schedule):
    """The exact step order: components first inside each block, then finals."""
    components = [record for record in records
                  if record["cube_verified_teaching"]["task_profile"]
                  == "component-route/0.1"]
    finals = [record for record in records
              if record["cube_verified_teaching"]["task_profile"]
              == "whole-answer/0.1"]
    require(len(components) == schedule["component_questions_per_block"],
            "CANDIDATE_COMPONENT_COUNT:%d" % len(components))
    require(len(finals) == schedule["whole_answer_questions_per_block"],
            "CANDIDATE_FINAL_COUNT:%d" % len(finals))
    steps = []
    for block in range(1, schedule["blocks"] + 1):
        for record in components + finals:
            steps.append({
                "block": block,
                "phase": ("component-route"
                          if record["cube_verified_teaching"]["task_profile"]
                          == "component-route/0.1" else "whole-answer"),
                "record_id": record["record_id"],
                "op": record["op"],
                "expected_answer": record["correct"],
            })
    return steps


def schedule_report(records, schedule=None):
    """What the schedule asks for, with the counters kept apart."""
    schedule = schedule or proposed_schedule()
    steps = scheduled_steps(records, schedule)
    by_op = {}
    for step in steps:
        by_op[step["op"]] = by_op.get(step["op"], 0) + 1
    by_phase = {}
    for step in steps:
        by_phase[step["phase"]] = by_phase.get(step["phase"], 0) + 1
    return {
        "schema": SCHEDULE_SCHEMA,
        "profile_id": schedule["profile_id"],
        "kind": schedule["kind"],
        "blocks": schedule["blocks"],
        "steps": len(steps),
        "component_to_final_ratio": schedule["component_to_final_ratio"],
        "steps_by_operation": by_op,
        "steps_by_phase": by_phase,
        "minimum_repeated_teaching_blocks": schedule["minimum_repeated_teaching_blocks"],
        "stopping_limits": schedule["stopping_limits"],
        "counts": {**schedule["counts"], "scheduled_steps": len(steps)},
        "fits_frozen_budget_profile":
            len(steps) <= trainer.FROZEN_MAX_OPTIMIZER_STEPS,
        "requires_budget_profile_change":
            len(steps) > trainer.FROZEN_MAX_OPTIMIZER_STEPS,
        "does_not_inherit": schedule["does_not_inherit"],
        "per_operation_totals_note": schedule.get("per_operation_totals_note"),
        "stub_allocation_not_used": ("the stub cycled the records over the frozen "
                                     "budget and produced 48 / 8 / 8; the schedule "
                                     "above is the proposed design instead"),
        "counters_note": schedule["counters_note"],
        "every_record_practiced": len({step["record_id"] for step in steps})
        == len(records),
    }


def execution_sequence(records=None, schedule=None, arm="cas", ordering_mode="declared"):
    """The chronological plan, step by step, with the placement made explicit."""
    schedule = schedule or proposed_schedule()
    steps = scheduled_steps(records, schedule) if records is not None else []
    return {
        "schema": CANDIDATE_SCHEMA,
        "ordering_mode": ordering_mode, "arm": arm,
        "execution_enabled": False,
        "order": list(EXECUTION_ORDER),
        "phases": [
            {"phase": "BUILD_AND_INDEX_FROM_EXACT_RECORDS",
             "what": ("construct the candidate from these exact records and index "
                      "the learner with adapter.public_records(record, arm) for "
                      "the same records and the same encoded ordering the loop "
                      "uses"),
             "why": ("curriculum attempt 002 failed with KeyError because the "
                     "learner was indexed from a different record set")},
            {"phase": "APPLY_PERMITTED_PARAMETER_SCOPE",
             "what": "trainer.scope_parameters(framework, model)",
             "why": "only operation:^6 may change"},
            {"phase": "TAKE_BEFORE_SNAPSHOT",
             "what": "trainer.parameter_snapshot(framework, model)",
             "why": ("must precede the first update, otherwise containment cannot "
                     "distinguish a trained change from an initial state")},
            {"phase": "PER_STEP_CAPTURE_PREDICTION",
             "what": ("record the learner's scores and selected answer for the "
                      "record about to be taught, from the prediction being "
                      "corrected"),
             "why": ("a prediction reconstructed after training is not the "
                     "behaviour that was corrected")},
            {"phase": "PER_STEP_APPLY_CHECKED_TARGET",
             "what": ("make_task(record, arm) -> learner.step(task): cross-entropy "
                      "against the teacher's verified encoded_correct_index"),
             "why": "this is where the teacher's answer becomes the correction"},
            {"phase": "PER_STEP_PERFORM_PERMITTED_UPDATE",
             "what": "the optimizer step inside learner.step",
             "why": "one correction on one record; not a teaching cycle"},
            {"phase": "PER_STEP_RECORD_UPDATE_IDENTITY",
             "what": ("block, phase, record_id, op, target, and the update index "
                      "in the run"),
             "why": "later audits need the update identity, not only a loss value"},
            {"phase": "TAKE_AFTER_SNAPSHOT",
             "what": "trainer.parameter_snapshot after the last update",
             "why": "endpoint comparison only"},
            {"phase": "COMPUTE_CONTAINMENT",
             "what": ("trainer.containment_report(before, after, scope['allowed']) "
                      "and fail closed on any forbidden change"),
             "why": "the plasticity claim must be checked, not assumed"},
            {"phase": "SAVE_AND_VERIFY_CHECKPOINT",
             "what": ("write the candidate state through the injected writer and "
                      "verify it reads back with the same identity"),
             "why": "an unsaved result is not evidence"},
            {"phase": "WRITE_COLLECTED_OBSERVATIONS",
             "what": ("the per-step observation record, with missing measurements "
                      "marked 'unavailable' rather than zero"),
             "why": "the earlier practice passes lost their predicted options"},
        ],
        "scheduled_steps": steps,
        "step_count": len(steps),
        "note": ("the per-step phases repeat in the listed order for every "
                 "scheduled step; the surrounding phases occur once"),
    }


REQUIRED_INSTRUMENTATION = (
    "framework", "model", "learner_factory", "authorization",
)


def prepare_candidate_run(bundle=None, view_id="view_context", ordering_mode="declared",
                          arm="cas", schedule=None):
    """The runnable preparation: what would run, in what order, with what counts."""
    if bundle is None:
        bundle = cube_node.load_bundle()
    schedule = schedule or proposed_schedule()
    records = vtr.training_records(bundle, view_id, ordering_mode)
    report = schedule_report(records, schedule)
    return {
        "schema": CANDIDATE_SCHEMA,
        "kind": schedule["kind"],
        "execution_enabled": False,
        "authorization_required": ("an owner GO record; run_candidate refuses "
                                   "without one"),
        "ordering_mode": ordering_mode,
        "arm": arm,
        "records": len(records),
        "record_ids": [record["record_id"] for record in records],
        "schedule": report,
        "proposed_evaluation": proposed_evaluation(bundle, view_id),
        "sequence": execution_sequence(records, schedule, arm, ordering_mode),
        "required_instrumentation": list(REQUIRED_INSTRUMENTATION),
        "learning_question": ("does practicing checked component relationships "
                              "help the same ^6 learner answer the complete "
                              "whole-part question?"),
        "not_the_seven_stage_program": (
            "stages 1, 2, 3, 4 and 6 have no numerical delivery path and stay "
            "unimplemented; this is checked component teaching only"),
        "expected_counters": {
            "scheduled_supervised_corrections": report["counts"]["supervised_corrections"],
            "component_teaching_blocks": report["counts"]["component_teaching_blocks"],
            "seven_stage_neural_cycles": 0,
            "automatic_retries": 0,
        },
        "checkpoint_identity": "determined at run time; this preparation records none",
        "boundary": {
            "neural_execution": "not performed here",
            "reservation": "none", "launcher": "none", "aws_calls": 0,
            "unchanged": ["the frozen trainer.launch", "the pending contrast probe",
                          "all earlier evidence and checkpoints"],
        },
    }


def proposed_evaluation(bundle=None, view_id="view_context"):
    """What this candidate could and could not show, and how it would be scored.

    The taught set is the whole authored scene, so the honest primary measure is
    independent performance on the taught complete questions, with a held-out
    probe drawn from the same scene's remaining questions. That is within-scene
    generalisation, not transfer to a new graph family, and the record says so.
    """
    if bundle is None:
        bundle = cube_node.load_bundle()
    cases = cube_node.answer_cases(bundle, view_id)["cases"]
    taught = 8
    return {
        "schema": CANDIDATE_SCHEMA,
        "primary_question": ("does teaching the smaller relationship decisions help "
                             "the same learner answer the complete whole-part "
                             "question?"),
        "conditions": [
            {"name": "checked_component_teaching",
             "teaches": "five component-route questions then the three whole-answer "
                        "questions, per block",
             "updates": PROPOSED_SCHEDULE["updates"],
             "component_supervision_counted_separately":
                 PROPOSED_SCHEDULE["counts"]["component_question_presentations"]},
            {"name": "final_answer_only",
             "teaches": "the three whole-answer questions only, same update "
                        "allowance",
             "updates": PROPOSED_SCHEDULE["updates"],
             "component_supervision_counted_separately": 0},
        ],
        "condition_note": ("the two conditions must differ in component supervision "
                           "only; the update allowance is held equal"),
        "primary_measure": ("independent accuracy on the taught whole-answer "
                            "questions: no worked answer, no teacher-verified "
                            "subanswers, no correct prefix"),
        "secondary_measures": [
            "component-question accuracy, reported separately from the complete "
            "question",
            "assisted performance during teaching, never mixed into the independent "
            "figure"],
        "held_out_probe": {
            "available_questions_in_the_scene": len(cases),
            "taught_questions": taught,
            "candidate_probe_questions": len(cases) - taught,
            "caveat": ("same authored scene: within-scene generalisation, not "
                       "transfer to a new graph family")},
        "reporting_rules": [
            "the learner's own prediction is recorded before any correction",
            "all three scores or logits are retained, or marked unavailable",
            "the teacher checker never selects among the learner's test answers",
            "independent and assisted figures are never merged",
            "missing measurements are unavailable, never zero"],
        "not_measured": ["definition, analogy, correspondence and story content: no "
                         "numerical delivery path exists for them"],
        "requires_owner_decisions": [
            "how many conditions to run and their update allowance",
            "whether the held-out probe questions are used",
            "whether any budget-profile change is approved for a larger schedule"],
        "cost_note": ("no reservation or cost estimate is proposed here; the frozen "
                      "budget profile bounds the candidate at %d updates and %d "
                      "seconds" % (trainer.FROZEN_MAX_OPTIMIZER_STEPS,
                                   trainer.FROZEN_MAX_WALL_SECONDS)),
    }


class ObservationRecorder:
    """Per-step observations. A missing measurement is 'unavailable', never zero."""

    def __init__(self):
        self.observations = []
        self.updates = []

    def observe(self, index, step, selected, scores, scores_note=None):
        row = {
            "update_index": index,
            "block": step["block"],
            "phase": step["phase"],
            "record_id": step["record_id"],
            "operation": step["op"],
            "expected_answer": step["expected_answer"],
            "selected_answer": selected,
            "selected_is_correct": canonical(selected) == canonical(
                step["expected_answer"]),
            "scores_or_logits": scores if scores is not None else "unavailable",
            "scores_note": scores_note or ("unavailable: no scorer was supplied, "
                                           "so the run must not report zeros"),
            "assistance_state": "NONE",
            "correction_released_after_this_recording": True,
            "update_identity": None,
        }
        self.observations.append(row)
        return row

    def record_update(self, index, before_identity, after_identity):
        row = self.observations[index]
        row["update_identity"] = {"index": index,
                                  "checkpoint_before": before_identity,
                                  "checkpoint_after": after_identity}
        self.updates.append(row["update_identity"])
        return row["update_identity"]

    def summary(self):
        released = [row for row in self.observations if row["update_identity"]]
        return {
            "recorded_predictions": len(self.observations),
            "recorded_updates": len(self.updates),
            "predictions_taken_before_their_update":
                all(row["update_identity"]["index"] == position
                    for position, row in enumerate(self.observations)
                    if row["update_identity"]),
            "scores_unavailable_count": sum(
                1 for row in self.observations
                if row["scores_or_logits"] == "unavailable"),
            "by_phase": {phase: sum(1 for row in self.observations
                                    if row["phase"] == phase)
                         for phase in sorted({row["phase"]
                                              for row in self.observations})},
            "missing_measurement_rule": "unavailable, never zero",
            "corrections_applied": len(released),
        }


def run_candidate(*, framework, model, learner_factory, authorization,
                  bundle=None, view_id="view_context", ordering_mode="declared",
                  arm="cas", schedule=None, scorer=None, checkpoint_writer=None,
                  checkpoint_verifier=None, wall_clock=None):
    """Run the candidate once, in the declared order. Refuses without authority.

    Every dependency is injected: this module imports no torch and constructs no
    model. ``authorization`` must be an owner record naming the run.
    """
    require(isinstance(authorization, dict) and authorization.get("owner_go") is True,
            "CANDIDATE_RUN_NOT_AUTHORIZED")
    require(authorization.get("run_id"), "CANDIDATE_RUN_ID_REQUIRED")
    require(callable(learner_factory), "CANDIDATE_LEARNER_FACTORY_REQUIRED")
    require(callable(checkpoint_writer) and callable(checkpoint_verifier),
            "CANDIDATE_RUN_CHECKPOINT_PATH_REQUIRED")
    if bundle is None:
        bundle = cube_node.load_bundle()
    schedule = schedule or proposed_schedule()
    records = vtr.training_records(bundle, view_id, ordering_mode)
    layout = vtr.learner_index(records, arm)
    tasks = {record["record_id"]: trainer.make_task(record, arm) for record in records}

    # BUILD_AND_INDEX_FROM_EXACT_RECORDS: the learner is built from these records
    # and their encoded ordering, not from another record set.
    learner = learner_factory(model, arm=arm, records=records, layout=layout)
    scope = trainer.scope_parameters(framework, model)
    before = trainer.parameter_snapshot(framework, model)
    budget = trainer.TrainingBudget().validate()
    recorder = ObservationRecorder()
    clock = wall_clock or _counter_clock()
    deadline = clock() + budget.max_wall_seconds
    steps = scheduled_steps(records, schedule)

    for index, step in enumerate(steps):
        # the previous step's update must already be recorded before the next
        # prediction is captured: the placement is the point of this loop
        if recorder.observations:
            require(recorder.observations[-1]["update_identity"] is not None,
                    "CANDIDATE_STEP_ORDER_VIOLATION")
        task = tasks[step["record_id"]]
        selected, scores, note = _capture(learner, task, scorer)
        recorder.observe(index, step, selected, scores, note)
        identity_before = learner.checkpoint_identity()
        learner.step(task)
        recorder.record_update(index, identity_before, learner.checkpoint_identity())
        if clock() >= deadline:
            break

    after = trainer.parameter_snapshot(framework, model)
    containment = trainer.containment_report(before, after, scope["allowed"])
    require(containment["contained"], "CANDIDATE_CONTAINMENT_VIOLATION")
    identity = learner.checkpoint_identity()
    saved = checkpoint_writer(learner, identity)
    verified = checkpoint_verifier(saved, identity)
    require(verified, "CANDIDATE_CHECKPOINT_NOT_VERIFIED")
    return {
        "schema": CANDIDATE_SCHEMA,
        "run_id": authorization["run_id"],
        "kind": schedule["kind"],
        "ordering_mode": ordering_mode, "arm": arm,
        "records": len(records),
        "schedule": schedule_report(records, schedule),
        "planned_steps": len(steps),
        "completed_steps": len(recorder.updates),
        "scope": scope,
        "containment": containment,
        "checkpoint": {"identity": identity, "saved": saved, "verified": verified},
        "observations": recorder.observations,
        "observation_summary": recorder.summary(),
        "actual_optimizer_updates": len(recorder.updates),
        "actual_neural_presentations": len(recorder.updates),
        "automatic_retries": 0,
        "stopping_reason": ("blocks complete" if len(recorder.updates) == len(steps)
                            else "wall-clock limit reached"),
        "sequence": list(EXECUTION_ORDER),
    }


def _capture(learner, task, scorer):
    """The selected answer and, when a scorer is supplied, the scores."""
    selected = learner.predict(task) if hasattr(learner, "predict") else "unavailable"
    if scorer is None:
        return selected, None, ("unavailable: no scorer was supplied; a run must "
                                "not report zeros for unmeasured scores")
    scores = scorer(learner, task)
    require(scores is not None, "CANDIDATE_SCORER_RETURNED_NOTHING")
    return selected, scores, None


def _counter_clock(start=0.0):
    state = {"now": start}

    def clock():
        state["now"] += 0.001
        return state["now"]
    return clock
