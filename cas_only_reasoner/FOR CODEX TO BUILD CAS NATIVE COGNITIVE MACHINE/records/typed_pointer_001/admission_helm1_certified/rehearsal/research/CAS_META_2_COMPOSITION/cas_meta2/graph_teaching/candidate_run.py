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
from . import (cube_node, reference, trainer, verified_teaching as vt,
               verified_training as vtr)

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
        "eight complete passes give every question eight supervised corrections. "
        "This is a CHOSEN PILOT ALLOWANCE, not a proven minimum for learning and "
        "not a mathematically necessary number: it is the smallest allowance this "
        "desk is willing to defend from the existing frozen budget profile, and it "
        "happens to fit that profile so no budget-profile change is needed. Whether "
        "eight blocks are enough is exactly what the pilot would measure"),
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
        "allowance_status": ("a chosen pilot allowance, not a proven minimum for "
                            "learning"),
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


def taught_questions(records):
    """The distinct questions the records teach, and any question taught twice.

    Eight teaching records can hold fewer distinct questions: the same route can
    be asked once as a component question and once as a whole-answer question.
    Identity ignores exercise ids, task-profile labels, phase labels and option
    order, so that repetition is visible rather than counted as two questions.
    """
    by_key = {}
    for record in records:
        key = record["cube_verified_teaching"]["question_key"]
        digest = record["cube_verified_teaching"]["question_key_digest"]
        entry = by_key.setdefault(digest, {"key": key, "digest": digest,
                                           "records": []})
        entry["records"].append({
            "record_id": record["record_id"],
            "exercise_id": record["cube_verified_teaching"]["exercise_id"],
            "task_profile": record["cube_verified_teaching"]["task_profile"],
            "operation": record["op"]})
    doubled = [entry for entry in by_key.values() if len(entry["records"]) > 1]
    return {
        "records": len(records),
        "distinct_questions": len(by_key),
        "questions": [by_key[digest] for digest in sorted(by_key)],
        "taught_more_than_once": doubled,
        "double_exposure_note": (
            "a question taught once per block as a component question and again as "
            "a whole-answer question receives two corrections per block; that "
            "repetition is intended and is reported rather than hidden"),
    }


def probe_questions(bundle=None, records=None, view_id="view_context"):
    """The within-scene probe: every catalog question not taught in either condition.

    Membership comes from the union of semantically taught questions, so the same
    set serves both conditions. The control teaches a subset of the same
    questions, so the union is unchanged by the choice of condition.
    """
    if bundle is None:
        bundle = cube_node.load_bundle()
    if records is None:
        records = vtr.training_records(bundle, view_id)
    labels = cube_node.view_labels(bundle, view_id)
    node_of = {label: ref for ref, label in labels.items()}
    taught = {entry["digest"] for entry in taught_questions(records)["questions"]}
    context_id = records[0]["cube_verified_teaching"]["question_key"]["context_id"]
    cases = cube_node.answer_cases(bundle, view_id)["cases"]
    remaining, excluded = [], []
    for case in cases:
        named = {role: node_of[value] for role, value in case["question"].items()}
        key = vt.catalog_question_key(case["op"], named, context_id)
        entry = {"operation": case["op"],
                 "named_arguments": key["named_arguments"],
                 "question_key_digest": vt.question_key_digest(key),
                 "answer": case["correct"]}
        if entry["question_key_digest"] in taught:
            excluded.append(entry)
        else:
            remaining.append(entry)
    by_operation = {}
    for entry in remaining:
        by_operation[entry["operation"]] = by_operation.get(entry["operation"], 0) + 1
    return {
        "schema": CANDIDATE_SCHEMA,
        "catalog_questions": len(cases),
        "distinct_taught_questions": len(taught),
        "excluded_taught_questions": len(excluded),
        "probe_questions": len(remaining),
        "probe_by_operation": by_operation,
        "membership_rule": ("catalog minus the union of semantically taught "
                            "questions, keyed on graph context, operation and named "
                            "arguments; exercise ids, task-profile labels, phase "
                            "labels and option order are ignored"),
        "same_set_for_both_conditions": True,
        "interpretation": ("can the learner answer additional questions about this "
                           "same graph after practising some of its relationships? "
                           "Within-scene generalisation only, never transfer to a "
                           "new graph arrangement"),
        "may_not_be_used_for": ["checkpoint selection", "curriculum adjustment",
                                "extending training mid-run"],
        "additional_exclusions": [],
        "questions": remaining,
        "excluded": excluded,
    }


CONTROL_EXTRA_FIRST = True


def control_schedule(records, updates=None):
    """The frozen final-answer-only schedule: 64 updates over three questions.

    The ordering is fixed here, before any result is seen: round-robin over the
    whole-answer questions in their frozen export order, with the remainder given
    to the first one. That yields 22 / 21 / 21 and is stated, not chosen later.
    """
    updates = updates or PROPOSED_SCHEDULE["updates"]
    finals = [record for record in records
              if record["cube_verified_teaching"]["task_profile"]
              == "whole-answer/0.1"]
    require(finals, "CANDIDATE_CONTROL_REQUIRES_FINAL_QUESTIONS")
    counts = {record["record_id"]: updates // len(finals) for record in finals}
    for record in finals[:updates % len(finals)]:
        counts[record["record_id"]] += 1
    order, index = [], 0
    while sum(1 for record_id in order if record_id) < updates:
        for record in finals:
            if order.count(record["record_id"]) < counts[record["record_id"]]:
                order.append(record["record_id"])
                index += 1
    return {
        "schema": CANDIDATE_SCHEMA,
        "condition": "final_answer_only",
        "updates": updates,
        "component_corrections": 0,
        "whole_answer_corrections": updates,
        "questions": [{"record_id": record["record_id"],
                       "operation": record["op"],
                       "expected_answer": record["correct"],
                       "corrections": counts[record["record_id"]]}
                      for record in finals],
        "distribution": {record["record_id"]: counts[record["record_id"]]
                         for record in finals},
        "ordering": order,
        "ordering_rule": ("round-robin over the whole-answer questions in their "
                          "frozen export order; the remainder goes to the first"),
        "frozen_before_results": True,
        "final_question_exposure": {
            record["op"]: counts[record["record_id"]] for record in finals},
        "note": ("the control practises the three final questions far more often "
                 "than the component condition does; that is the difference being "
                 "measured, not a defect"),
    }


def matched_comparison_requirements():
    """What must be identical for the two conditions, and what may differ."""
    return {
        "identical": ["initial weights (two candidate copies from the same initial "
                      "state)",
                      "the frozen encoder and its fitted tokenizer",
                      "the public exercise set's graph, framing and scoring path",
                      "the update allowance: %d per condition"
                      % PROPOSED_SCHEDULE["updates"],
                      "the seed and the stopping limits"],
        "separate": ["optimizer state", "checkpoint identity",
                     "per-condition observation records"],
        "may_differ": ["the teaching allocation: 40 component + 24 whole-answer "
                       "versus 0 + 64"],
        "why": ("the allocation must be the intended difference; a different "
                "starting learner would confound it"),
        "restart_policy": "zero automatic retries; a failed condition is reported",
    }


def comparison_semantics():
    """Exactly what the two-condition comparison can and cannot show."""
    return {
        "question": ("at the same number of updates, is it better to spend some "
                     "practice on the parts of the problem rather than spend every "
                     "update on the complete questions?"),
        "conditions": {
            "checked_component_teaching": {"component_corrections": 40,
                                           "whole_answer_corrections": 24},
            "final_answer_only": {"component_corrections": 0,
                                  "whole_answer_corrections": 64},
        },
        "does_not_show": ("it does not isolate the effect of adding component "
                          "instruction while holding final-question practice "
                          "equal: the control practises the final questions far "
                          "more often. A third condition would be needed for that, "
                          "and none is proposed now"),
        "negative_result_means": ("this component-teaching allocation did not help "
                                  "under these conditions"),
        "negative_result_does_not_mean": ("the complete seven-stage method failed; "
                                          "several of its presentations have no "
                                          "numerical delivery path yet"),
        "primary_set_size_warning": ("the primary set holds three taught "
                                    "whole-answer questions, so one changed answer "
                                    "moves accuracy by 33.3 percentage points; no "
                                    "single percentage carries the conclusion"),
    }


def proposed_evaluation(bundle=None, view_id="view_context", records=None):
    """What this candidate could and could not show, and how it would be scored.

    The taught set is the whole authored scene, so the honest primary measure is
    independent performance on the taught complete questions, with a held-out
    probe drawn from the same scene's remaining questions. That is within-scene
    generalisation, not transfer to a new graph family, and the record says so.
    """
    if bundle is None:
        bundle = cube_node.load_bundle()
    if records is None:
        records = vtr.training_records(bundle, view_id)
    probe = probe_questions(bundle, records, view_id)
    control = control_schedule(records)
    return {
        "schema": CANDIDATE_SCHEMA,
        "primary_question": ("does teaching the smaller relationship decisions help "
                             "the same learner answer the complete whole-part "
                             "question?"),
        "comparison_semantics": comparison_semantics(),
        "matched_comparison": matched_comparison_requirements(),
        "conditions": [
            {"name": "checked_component_teaching",
             "teaches": "five component-route questions then the three whole-answer "
                        "questions, per block",
             "updates": PROPOSED_SCHEDULE["updates"],
             "component_supervision_counted_separately":
                 PROPOSED_SCHEDULE["counts"]["component_question_presentations"],
             "whole_answer_corrections":
                 PROPOSED_SCHEDULE["counts"]["whole_answer_presentations"]},
            {"name": "final_answer_only",
             "teaches": "the three whole-answer questions only, same update "
                        "allowance",
             "updates": control["updates"],
             "component_supervision_counted_separately": 0,
             "whole_answer_corrections": control["whole_answer_corrections"],
             "frozen_ordering": control["ordering_rule"],
             "final_question_exposure": control["final_question_exposure"]},
        ],
        "condition_note": ("the two conditions must differ in component supervision "
                           "only; the update allowance is held equal"),
        "primary_measure": ("independent accuracy on the taught whole-answer "
                            "questions: no worked answer, no teacher-verified "
                            "subanswers, no correct prefix. 'Independent' means no "
                            "worked answer is supplied during prediction; it does "
                            "not mean the taught questions have become unseen"),
        "secondary_measures": [
            "component-question accuracy, reported separately from the complete "
            "question",
            "assisted performance during teaching, never mixed into the independent "
            "figure"],
        "reporting_plan": {
            "taught_whole_answer_questions": ("before and after: the selected "
                                              "answer, all three scores, and the "
                                              "loss for each of the three"),
            "component_questions": "reported separately",
            "untaught_probe": "counts by operation, same set for both conditions",
            "checkpoint_rule": ("the final checkpoint is fixed by the declared "
                                "schedule; the probe never selects a checkpoint, "
                                "adjusts the curriculum, or extends training"),
        },
        "probe": {key: probe[key] for key in                  ("catalog_questions", "distinct_taught_questions",
                   "excluded_taught_questions", "probe_questions",
                   "probe_by_operation", "membership_rule",
                   "same_set_for_both_conditions", "interpretation",
                   "may_not_be_used_for", "additional_exclusions")},
        "taught_question_repetition": {
            key: taught_questions(records)[key]
            for key in ("records", "distinct_questions", "taught_more_than_once",
                        "double_exposure_note")},
        "not_measured": ["definition, analogy, correspondence and story content: no "
                         "numerical delivery path exists for them"],
        "requires_owner_decisions": [
            "how many conditions to run and their update allowance",
            "whether the held-out probe questions are used",
            "whether any budget-profile change is approved for a larger schedule"],
        "cost_note": ("no reservation or cost estimate is proposed here; the frozen "
                      "budget profile bounds one condition at %d updates and %d "
                      "seconds. A pilot authorization request must state the "
                      "per-condition and combined limits, the total reservation, and "
                      "the collection and cleanup policy"
                      % (trainer.FROZEN_MAX_OPTIMIZER_STEPS,
                         trainer.FROZEN_MAX_WALL_SECONDS)),
    }


def _list_options(index, whole_id, answer):
    """Three part-list choices for any catalog question, with declared fallbacks.

    Preference order: the complete list, one foreign-part substitute, one
    indirect-part substitute. Where the scene cannot supply one of those (a leaf
    cube, or an empty answer) the fallback is another whole's list, then a single
    part. The geometry is reported by ``probe_geometry`` rather than assumed.
    """
    direct = set(index.direct_parts(whole_id))
    reachable = set(reference.transitive_parts(index.graph, index.label_of[whole_id]))
    part_labels = {index.label_of[branch["target_node_id"]]
                   for branch in index.context["branches"]
                   if branch["predicate"] == "contains"}
    foreign = sorted(label for label in part_labels
                     if label not in direct and label not in reachable)
    indirect = sorted(reachable - direct)
    options = [sorted(answer)]
    if answer and foreign:
        options.append(sorted(list(answer)[:-1] + [foreign[0]]))
    if answer and indirect:
        options.append(sorted([indirect[0]] + list(answer)[1:]))
    for node_id in sorted(index.label_of):
        if len(options) == 3:
            break
        candidate = sorted(index.direct_parts(node_id))
        if canonical(candidate) not in {canonical(item) for item in options}:
            options.append(candidate)
    for label in sorted(part_labels):
        if len(options) == 3:
            break
        candidate = [label]
        if canonical(candidate) not in {canonical(item) for item in options}:
            options.append(candidate)
    require(len(options) == 3, "CANDIDATE_LIST_OPTIONS")
    require(any(canonical(option) == canonical(answer) for option in options),
            "CANDIDATE_LIST_ANSWER_OFFERED")
    return options


def _shared_options(index, first_id, second_id, answer):
    """Three choices for a shared-part question, including the 'none' answer."""
    values = [answer]
    part_labels = {index.label_of[branch["target_node_id"]]
                   for branch in index.context["branches"]
                   if branch["predicate"] == "contains"}
    pool = (["none"] + sorted(index.direct_parts(first_id))
            + sorted(index.direct_parts(second_id)) + sorted(part_labels)
            + sorted(index.label_of.values()))
    for candidate in pool:
        if len(values) == 3:
            break
        if canonical(candidate) not in {canonical(item) for item in values}:
            values.append(candidate)
    require(len(values) == 3, "CANDIDATE_SHARED_OPTIONS")
    require(any(canonical(option) == canonical(answer) for option in values),
            "CANDIDATE_SHARED_ANSWER_OFFERED")
    return values


def _options_for(index, operation, named, answer):
    """Three public choices for any catalog question, including an empty answer."""
    if operation == "LIST_PARTS":
        return _list_options(index, named["idea"], answer)
    if operation == "FIND_SHARED_PART":
        return _shared_options(index, named["a"], named["b"], answer)
    return vt.reach_choice_values(index, named["idea"], named["part"], answer)


def probe_records(bundle=None, records=None, view_id="view_context",
                  ordering_mode="declared", report=None):
    """The 44 untaught questions as records on the same encoder path.

    They are never taught. The run only evaluates them, after the final
    checkpoint, and the learner answers them through its on-demand encoding path
    because they sit outside its training index.
    """
    if bundle is None:
        bundle = cube_node.load_bundle()
    if records is None:
        records = vtr.training_records(bundle, view_id, ordering_mode, report=report)
    probe = probe_questions(bundle, records, view_id)
    index = vt.Index(bundle, vt.lesson_context(bundle, view_id), view_id)
    context_id = records[0]["cube_verified_teaching"]["question_key"]["context_id"]
    built = []
    for entry in probe["questions"]:
        operation = entry["operation"]
        named = entry["named_arguments"]
        answer = entry["answer"]
        options = _options_for(index, operation, named, answer)
        built.append(vtr.record_from_question(
            bundle, vtr.catalog_question(operation, named, index), options, answer,
            view_id, "candidate_probe",
            extra={"probe": True, "context_id": context_id,
                   "question_key": vt.catalog_question_key(operation, named,
                                                           context_id)}))
    require(len(built) == probe["probe_questions"], "CANDIDATE_PROBE_RECORD_COUNT")
    return built


def probe_geometry(probe_records_list):
    """Option geometry of the probe, reported rather than judged."""
    unequal = []
    for record in probe_records_list:
        counts = [len(option) if isinstance(option, list) else 1
                  for option in record["options"]]
        if len(set(counts)) != 1:
            unequal.append({"record_id": record["record_id"], "op": record["op"],
                            "item_counts": counts,
                            "answer_is_empty": record["correct"] == []})
    return {
        "questions": len(probe_records_list),
        "equal_item_counts": len(probe_records_list) - len(unequal),
        "unequal_item_counts": len(unequal),
        "unequal_because_the_answer_is_empty": sum(
            1 for item in unequal if item["answer_is_empty"]),
        "unequal_detail": unequal[:8],
        "note": ("an empty answer cannot offer equal item counts; the alternative "
                 "is one foreign part and one indirect part, and the geometry is "
                 "reported rather than assumed balanced"),
    }


def control_steps(records, updates=None):
    """The control condition's step list, built from the frozen ordering."""
    control = control_schedule(records, updates)
    by_id = {record["record_id"]: record for record in records}
    width = len(control["questions"])
    return [{"block": index // width + 1, "phase": "whole-answer",
             "record_id": record_id, "op": by_id[record_id]["op"],
             "expected_answer": by_id[record_id]["correct"]}
            for index, record_id in enumerate(control["ordering"])]


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
                  arm="cas", schedule=None, steps=None, scorer=None,
                  checkpoint_writer=None, checkpoint_verifier=None, wall_clock=None,
                  before_hook=None, after_hook=None):
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
    # The BEFORE measurement is taken here: after scoping and the before
    # snapshot, before the first update. A prediction reconstructed later is not
    # the behaviour the run started from.
    pre_measurement = before_hook(learner) if before_hook else None
    budget = trainer.TrainingBudget().validate()
    recorder = ObservationRecorder()
    clock = wall_clock or _counter_clock()
    deadline = clock() + budget.max_wall_seconds
    steps = list(steps) if steps is not None else scheduled_steps(records, schedule)
    require(steps, "CANDIDATE_STEPS_REQUIRED")

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
    result = {
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
        "pre_measurement": pre_measurement,
        "observations": recorder.observations,
        "observation_summary": recorder.summary(),
        "actual_optimizer_updates": len(recorder.updates),
        "actual_neural_presentations": len(recorder.updates),
        "automatic_retries": 0,
        "stopping_reason": ("blocks complete" if len(recorder.updates) == len(steps)
                            else "wall-clock limit reached"),
        "sequence": list(EXECUTION_ORDER),
    }
    # The AFTER measurement is taken here: after the final checkpoint, with no
    # further update, so the probe can never steer training.
    result["post_measurement"] = after_hook(learner, result) if after_hook else None
    return result


def _capture(learner, task, scorer):
    """The selected answer and, when one is available, the scores.

    An injected ``scorer`` wins. Without one the learner's own ``scores`` method
    is used, because a run whose per-step scores are all 'unavailable' (attempt
    007 reported 64 of 64 that way) cannot deliver the declared reporting plan.
    When neither exists the field stays 'unavailable': a run must never print
    zeros for a value it did not measure.
    """
    selected = learner.predict(task) if hasattr(learner, "predict") else "unavailable"
    if scorer is None:
        own = getattr(learner, "scores", None)
        if callable(own):
            scores = own(task)
            if scores is not None:
                return selected, scores, None
        return selected, None, ("unavailable: no scorer was supplied and the learner "
                                "exposes no scores; a run must not report zeros for "
                                "unmeasured scores")
    scores = scorer(learner, task)
    require(scores is not None, "CANDIDATE_SCORER_RETURNED_NOTHING")
    return selected, scores, None


def _counter_clock(start=0.0):
    state = {"now": start}

    def clock():
        state["now"] += 0.001
        return state["now"]
    return clock
