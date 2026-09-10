"""CUBE_VERIFIED_TEACHING_001 — the candidate-only connection to the learner.

STATUS: connection and dry-run checks only. No torch import, no model, no GPU, no
launcher, no reservation, no paid run. Nothing here executes a neural step.

The directive asked for the smallest candidate-only execution connection that
reuses the existing learner and training machinery, naming **exactly** where the
teacher's target becomes the training correction. That point is:

    TeacherTarget.expected_answer
        -> record["correct"]                       (built here, from the verified target)
        -> adapter.public_records(record, arm)     (frozen public extraction)
             ["encoded_correct_index"]
        -> trainer.make_task(record, arm)["correct"]
        -> GraphLearner.step(task)
             torch.nn.functional.cross_entropy(scores, encoded_correct_index)
        -> optimizer.step()                        (permitted plasticity group only)

``real_framework.py`` lines 297-307 are that cross-entropy call; the index it uses
is ``self.tasks[position]["encoded_correct_index"]``, produced by the frozen codec
from ``record["correct"]``. So the teacher's checked answer *is* the loss target,
and nothing else in the loop supplies a target.

Two entry points exist, and the difference matters:

* ``trainer.launch(...)`` builds the learner, snapshots parameters, scopes the
  plasticity allowlist, and proves containment — but it has **no parameter for
  injecting records**: it always runs the registered whole-part dataset
  (``training_records(seed)``). Adding one would change registered
  infrastructure, so it is not done here.
* ``trainer.run_training(learner, records, arm, budget)`` takes the records
  directly. The connection therefore enters at that boundary, with the cube
  records handed in, and keeps ``scope_parameters`` and ``containment_report`` for
  the containment proof.

``connection_check`` drives that real loop with a stub learner, so the wiring is
demonstrated end to end without any neural execution. The stub is not a model and
its responses are not predictions.
"""
from __future__ import annotations

from .graph import canonical, digest, require
from .lessons import EXERCISE_SCHEMA
from . import adapter, cube_node, reference, trainer, verified_teaching as vt

CONNECTION_SCHEMA = "cas-cube-verified-teaching-connection/1"

CORRECTION_STAGE = {
    "where": "GraphLearner.step -> cross_entropy(scores, encoded_correct_index)",
    "source_file": "cas_meta2/graph_teaching/real_framework.py",
    "source_lines": "297-307",
    "index_source": "adapter.public_records(record, arm)['encoded_correct_index']",
    "index_built_from": "record['correct']",
    "record_field_origin": "TeacherTarget.expected_answer (verified)",
    "update": "trainer.scope_parameters allowlist only; encoder and readout frozen",
    "note": ("the teacher's checked answer is the loss target; no other target "
             "enters the loop"),
}


def question_record(exercise, index):
    """The question keys the existing adapter already understands."""
    operation = exercise["question"]["operation"]
    named = exercise["question"]["named_arguments"]
    if operation == "LIST_PARTS":
        return {"op": operation, "idea": index.label_of[named["whole_id"]]}
    if operation == "FIND_SHARED_PART":
        return {"op": operation, "a": index.label_of[named["first_whole_id"]],
                "b": index.label_of[named["second_whole_id"]]}
    return {"op": operation, "part": index.label_of[named["candidate_id"]],
            "idea": index.label_of[named["whole_id"]]}


def public_problem(bundle, question, view_id):
    """The learner-visible problem: the graph's own teaching presentation.

    The frozen problem encoder (``real_framework.encode_problem``) is specified
    over the ``node``/``rel`` lines that ``graph.Graph.render`` produces: it
    binds each complete node line and each complete relation line into one joint
    vector, and it fails closed on any other presentation. The cube graph is
    already a ``Graph`` and already renders in exactly that form, so this uses
    its rendering instead of restating the same relations as prose.

    This is not decoration. Attempt 006 died here:

        ValueError: tuple.index(x): x not in tuple
        node_id = vocabulary.index(_word_token("node"))

    The hand-written "Facts:" prose never gave the fitted vocabulary a ``node``
    token at all, and would then have failed the encoder's
    ``PROBLEM_STRUCTURAL_SEGMENTS_REQUIRED`` check, so no cube lesson could
    reach the encoder. The change is syntax only: the same nodes, the same
    containment branches, the same question. It carries no answer, target,
    witness or option marking - ``Graph.render`` is documented as structure only,
    and the three choices still travel as unmarked observations.
    """
    return (cube_node.containment_graph(bundle, view_id).render()
            + _request(question) + "\nChoose one of the three supplied options.\n")


def record_from_exercise(bundle, exercise, target, index, view_id, split):
    """One frozen-shape exercise record whose ``correct`` IS the teacher target."""
    graph = cube_node.graph_record(bundle, view_id)
    question = question_record(exercise, index)
    options = vt.exercise_choice_values(exercise)
    correct = target["expected_answer"]
    require(any(canonical(option) == canonical(correct) for option in options),
            "VT_CONNECTION_TARGET_NOT_OFFERED")
    question_key = vt.canonical_question_key(exercise["question"]["operation"],
                                             exercise["question"]["named_arguments"],
                                             exercise["context_id"])
    prompt = public_problem(bundle, question, view_id)
    core = {"schema": EXERCISE_SCHEMA, "split": split, "op": question["op"],
            "graph": graph, "question": question, "options": options,
            "framings": {"cas": prompt, "generic": prompt},
            "cube_verified_teaching": {
                "exercise_id": exercise["exercise_id"],
                "task_profile": exercise["task_profile"],
                "assistance_level": "NONE",
                "expected_choice_id": target["expected_choice_id"],
                "witness_kind": target["witness"]["kind"],
                "checker_identity": target["reference_verification"]["checker_identity"],
                "record_id_basis": "public_projection",
                "context_id": exercise["context_id"],
                "question_key": question_key}}
    core["cube_verified_teaching"]["question_key_digest"] = vt.question_key_digest(
        question_key)
    record = {**core, "record_id": digest(canonical(core)), "correct": correct,
              "reference": reference.derivation_for(
                  question["op"], cube_node.containment_graph(bundle, view_id),
                  question)}
    return record


def catalog_question(operation, named_arguments, index):
    """The adapter-ready question dict for a lesson-catalog question."""
    if operation == "LIST_PARTS":
        return {"op": operation, "idea": index.label_of[named_arguments["idea"]]}
    if operation == "FIND_SHARED_PART":
        return {"op": operation, "a": index.label_of[named_arguments["a"]],
                "b": index.label_of[named_arguments["b"]]}
    return {"op": operation, "part": index.label_of[named_arguments["part"]],
            "idea": index.label_of[named_arguments["idea"]]}


def record_from_question(bundle, question, options, correct, view_id, split,
                         extra=None):
    """One frozen-shape record from an adapter-ready question, its choices, its answer.

    Shared by the taught records and the untaught probe records so both travel the
    same encoder path. ``question`` is already in label space.
    """
    graph = cube_node.graph_record(bundle, view_id)
    require(any(canonical(option) == canonical(correct) for option in options),
            "VT_CONNECTION_TARGET_NOT_OFFERED")
    prompt = public_problem(bundle, question, view_id)
    detail = dict(extra or {})
    question_key = detail.pop("question_key", None)
    require(question_key is not None, "VT_RECORD_QUESTION_KEY_REQUIRED")
    detail.pop("context_id", None)
    core = {"schema": EXERCISE_SCHEMA, "split": split, "op": question["op"],
            "graph": graph, "question": question, "options": list(options),
            "framings": {"cas": prompt, "generic": prompt},
            "cube_verified_teaching": {
                "assistance_level": "NONE",
                "record_id_basis": "public_projection",
                "question_key": question_key,
                "question_key_digest": vt.question_key_digest(question_key),
                **detail}}
    return {**core, "record_id": digest(canonical(core)), "correct": correct,
            "reference": reference.derivation_for(
                question["op"], cube_node.containment_graph(bundle, view_id),
                question)}


def _request(question):
    if question["op"] == "LIST_PARTS":
        return "LIST_PARTS(%s): what does it directly contain?" % question["idea"]
    if question["op"] == "FIND_SHARED_PART":
        return ("FIND_SHARED_PART(%s, %s): which constituent do they share?"
                % (question["a"], question["b"]))
    return ("REACHED_VIA(%s, %s): directly inside, reached through another "
            "constituent, or absent?" % (question["part"], question["idea"]))


def training_records(bundle=None, view_id="view_context", ordering_mode="declared",
                     split="cube_verified_teaching", report=None):
    """The eight verified-teaching exercises as records the trainer can consume."""
    if bundle is None:
        bundle = cube_node.load_bundle()
    require(ordering_mode in ("declared", "authored_fixture"),
            "VT_ORDERING_MODE_UNKNOWN:" + str(ordering_mode))
    if report is None:
        report = vt.compile_bundle(bundle, view_id, choice_order=ordering_mode)
    require(report["ordering_mode"] == ordering_mode,
            "VT_CONNECTION_ORDERING_MODE_MISMATCH:%s" % report["ordering_mode"])
    index = vt.Index(bundle, vt.lesson_context(bundle, view_id), view_id)
    targets = {target["exercise_id"]: target
               for target in report["private_teacher_targets"]}
    records = []
    for exercise in report["public_exercises"]:
        target = targets[exercise["exercise_id"]]
        require(target["reference_verification"]["status"] == vt.VERIFIED,
                "VT_CONNECTION_TARGET_NOT_VERIFIED:" + exercise["exercise_id"])
        records.append(record_from_exercise(bundle, exercise, target, index,
                                           view_id, split))
    return records


def learner_index(records, arm="cas"):
    """The exact layout the learner must be indexed by, and its loss target."""
    require(arm in ("cas", "generic"), "ARM_UNKNOWN")
    layout = {}
    for record in records:
        layout[record["record_id"]] = adapter.public_records(record, arm)
    return layout


def correction_point(records, arm="cas"):
    """Where each teacher answer becomes the numerical loss target.

    Reports both indices on purpose: ``expected_slot`` is the position in the
    exercise's declared choices, while ``encoded_correct_index`` is the position
    in the frozen codec's own order. They can differ, so the assertion is on the
    *value* found at the numerical slot the loss uses.
    """
    layout = learner_index(records, arm)
    rows = []
    for record in records:
        encoded = layout[record["record_id"]]
        target_index = encoded["encoded_correct_index"]
        value_at_target = encoded["encoded_options"][target_index]
        declared_slot = next(position for position, option in
                             enumerate(record["options"])
                             if canonical(option) == canonical(record["correct"]))
        rows.append({
            "record_id": record["record_id"],
            "operation": record["op"],
            "teacher_expected_answer": record["correct"],
            "declared_slot": declared_slot,
            "encoded_correct_index": target_index,
            "value_at_encoded_correct_index": value_at_target,
            "slot_carries_teacher_answer":
                canonical(value_at_target) == canonical(record["correct"]),
            "encoded_options_are_a_permutation_of_the_choices":
                sorted(canonical(option) for option in encoded["encoded_options"])
                == sorted(canonical(option) for option in record["options"]),
        })
    return {
        "arm": arm, "records": rows,
        "all_slots_carry_the_teacher_answer": all(
            row["slot_carries_teacher_answer"] for row in rows),
        "all_sets_permuted_only": all(
            row["encoded_options_are_a_permutation_of_the_choices"] for row in rows),
        "correction_stage": CORRECTION_STAGE,
    }


class StubLearner:
    """A recording stub for the compiler check. Not a model, not a prediction."""

    def __init__(self, layout):
        self.layout = layout
        self.steps = []
        self.loss_calls = []

    def step(self, task):
        encoded = self.layout[task["record_id"]]
        require(canonical(task["correct"]) == canonical(
            encoded["encoded_options"][encoded["encoded_correct_index"]]),
            "VT_CONNECTION_TARGET_DRIFT:" + task["record_id"])
        self.steps.append({"record_id": task["record_id"], "op": task["op"],
                           "correct": task["correct"],
                           "encoded_correct_index": encoded["encoded_correct_index"]})
        return 0.0

    def eval_loss(self, op, tasks):
        self.loss_calls.append(op)
        return {"total": 0.0}

    def checkpoint_identity(self):
        return "STUB_NO_PARAMETERS"


def connection_check(bundle=None, view_id="view_context", ordering_mode="declared",
                     arm="cas", wall_clock=None):
    """Drive the REAL trainer loop with a stub learner; no neural execution."""
    if bundle is None:
        bundle = cube_node.load_bundle()
    records = training_records(bundle, view_id, ordering_mode)
    layout = learner_index(records, arm)
    stub = StubLearner(layout)
    budget = trainer.TrainingBudget().validate()
    clock = wall_clock or _monotonic_counter()
    report = trainer.run_training(stub, records, arm, budget, wall_clock=clock)
    seen = {step["record_id"] for step in stub.steps}
    return {
        "schema": CONNECTION_SCHEMA,
        "ordering_mode": ordering_mode, "arm": arm,
        "records": len(records),
        # Field-name correction (owner review): the earlier name
        # "optimizer_updates_in_this_check" read as if a model had been trained.
        # These counts say exactly what happened: the loop was driven, nothing
        # was updated, nothing was delivered.
        "stub_training_step_calls": report["completed_updates"],
        "actual_optimizer_updates": 0,
        "actual_neural_presentations": 0,
        "field_correction": {
            "replaced": "optimizer_updates_in_this_check",
            "with": ["stub_training_step_calls", "actual_optimizer_updates",
                     "actual_neural_presentations"],
            "reason": ("the learner is a stub with no parameters, so no optimizer "
                       "step and no neural presentation occurred; the earlier name "
                       "overstated what the check did"),
            "preserved_from": "the loop's own 'completed_updates' count, renamed "
                              "to say that the calls went to a stub",
        },
        "records_that_received_correction": len(seen),
        "every_record_reached": seen == set(layout),
        "corrective_targets_used": sorted({canonical(step["correct"]).decode("utf-8")
                                           for step in stub.steps}),
        "stub_step_allocation_by_op": {
            op: sum(1 for step in stub.steps if step["op"] == op)
            for op in sorted({step["op"] for step in stub.steps})},
        "stub_step_allocation_note": ("this allocation follows from cycling the "
                                      "eight records over the frozen budget; it is "
                                      "not a proposed teaching schedule"),
        "correction_point": correction_point(records, arm),
        "lesson_exposure": report["lesson_exposure"],
        "checkpoint_identity": report["checkpoint_identity"],
        "neural_execution": False,
        "torch_imported": "torch" in __import__("sys").modules,
        "learner_is_a_stub": True,
        "stub_note": ("the stub records what it is taught; its responses are not "
                      "model predictions and this check delivers nothing"),
        "budget": {"learning_rate": budget.learning_rate,
                   "max_optimizer_steps": budget.max_optimizer_steps,
                   "max_wall_seconds": budget.max_wall_seconds},
    }


def _monotonic_counter(start=0.0):
    state = {"now": start}

    def clock():
        state["now"] += 0.001
        return state["now"]
    return clock


def dry_run_plan(bundle=None, view_id="view_context", ordering_mode="declared",
                 arm="cas"):
    """The exact calls a candidate run would make, with execution disabled."""
    if bundle is None:
        bundle = cube_node.load_bundle()
    records = training_records(bundle, view_id, ordering_mode)
    checkpoint = correction_point(records, arm)
    return {
        "schema": CONNECTION_SCHEMA,
        "execution_enabled": False,
        "authorization": ("no launcher, no reservation, no paid run, no neural "
                          "execution is authorized by this preparation"),
        "ordering_mode": ordering_mode,
        "sequence": [
            {"step": 1, "call": "cube_node.load_bundle()",
             "gives": "the pinned public graph"},
            {"step": 2,
             "call": "verified_teaching.compile_bundle(bundle, choice_order=...)",
             "gives": "8 public exercises and 8 verified teacher targets"},
            {"step": 3,
             "call": "verified_training.training_records(bundle, ...)",
             "gives": "%d records whose 'correct' field IS the teacher answer"
                      % len(records)},
            {"step": 4,
             "call": "adapter.public_records(record, arm) for every record",
             "gives": "the learner's own task layout, including "
                      "encoded_correct_index"},
            {"step": 5,
             "call": "trainer.TrainingBudget().validate()",
             "gives": "the frozen budget: %s" % (
                 "learning_rate=%s, max_optimizer_steps=%s, max_wall_seconds=%s"
                 % (trainer.FROZEN_LEARNING_RATE, trainer.FROZEN_MAX_OPTIMIZER_STEPS,
                    trainer.FROZEN_MAX_WALL_SECONDS))},
            {"step": 6,
             "call": "trainer.scope_parameters(framework, model)",
             "gives": ("the permitted plasticity allowlist and the frozen set "
                       "(operation:^6 only)")},
            {"step": 7,
             "call": "trainer.run_training(learner, records, arm, budget)",
             "gives": ("make_task(record, arm) -> learner.step(task) -> "
                       "cross-entropy against encoded_correct_index -> one "
                       "optimizer step"),
             "note": ("this is the frozen 64-step budget running the records in "
                      "cycle order; it is a wiring default, NOT a teaching "
                      "schedule. The proposed schedule lives in "
                      "candidate_run.proposed_schedule()")},
            {"step": 8,
             "call": "trainer.parameter_snapshot + containment_report",
             "gives": ("proof that only allowlisted parameters changed; the BEFORE "
                       "snapshot must be taken before the first update and the "
                       "AFTER snapshot after the last one (see "
                       "candidate_run.execution_sequence)")},
            {"step": 9,
             "call": "record the observation contract",
             "gives": ("per-event prediction, all three scores, released "
                       "correction, option lengths; missing values stay "
                       "'unavailable'")},
        ],
        "not_used": [
            "trainer.launch: it has no record-injection parameter and always runs "
            "the registered whole-part dataset; adding one would change registered "
            "infrastructure",
            "any new head, loss, reward model, or output vocabulary",
            "any GPU, provider, launcher, or reservation call",
        ],
        "correction_point": checkpoint,
        "learner_indexing_requirement": (
            "the learner must be indexed by the same records' public records "
            "(_position raises KeyError otherwise; preserved failure from "
            "curriculum attempt 002)"),
        "seven_stage_status": ("stages 1, 2, 3, 4 and 6 remain presentation-only "
                              "with numeric_delivery_binding UNIMPLEMENTED; this "
                              "connection covers the five component-route "
                              "questions and the three final questions only"),
    }
