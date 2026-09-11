"""Tests for the candidate-only execution connection.

The connection is demonstrated by driving the REAL ``trainer.run_training`` loop
with a recording stub learner. No torch, no GPU, no network, no launch, and no
neural execution: the stub is not a model and its responses are not predictions.
"""
import inspect
import json
import sys
from pathlib import Path

import pytest

from cas_meta2.graph_teaching import (adapter, cube_node, trainer,
                                      verified_teaching as vt,
                                      verified_training as vtr)
from cas_meta2.graph_teaching.graph import canonical

MODULE_SOURCE = Path(vtr.__file__).read_text(encoding="utf-8")


def _report(mode="declared"):
    return vt.compile_bundle(cube_node.load_bundle(), choice_order=mode)


def _teacher_answers(mode="declared"):
    report = _report(mode)
    return {canonical(target["expected_answer"]).decode("utf-8")
            for target in report["private_teacher_targets"]}


def test_records_carry_the_teacher_answer_as_the_correction_field():
    report = _report()
    records = vtr.training_records(report=report)
    targets = {target["exercise_id"]: target
               for target in report["private_teacher_targets"]}
    assert len(records) == 8
    assert {record["op"] for record in records} == {"LIST_PARTS", "FIND_SHARED_PART",
                                                   "REACHED_VIA"}
    for record, exercise in zip(records, report["public_exercises"]):
        assert record["schema"].startswith("cas-meta2-graph-teaching-exercise")
        assert record["split"] == "cube_verified_teaching"
        assert canonical(record["correct"]) == canonical(
            targets[exercise["exercise_id"]]["expected_answer"])
        assert record["cube_verified_teaching"]["exercise_id"] == exercise["exercise_id"]
        assert record["cube_verified_teaching"]["checker_identity"] == vt.CHECKER_IDENTITY
        assert record["framings"]["cas"] == record["framings"]["generic"]
        prompt = record["framings"]["cas"]
        assert "Choose one of the three supplied options." in prompt
        for target in targets.values():
            # graph facts are legitimate public evidence; the worked explanation
            # and the witness are not part of the learner's prompt
            assert target["worked_explanation"] not in prompt
            assert target["witness"]["kind"] not in prompt
            assert str(target["expected_choice_id"]) not in prompt
        assert record["reference"]["method"] in ("direct_parts", "shared_parts",
                                                "reach_kind")


def test_correction_point_is_the_index_the_loss_would_use():
    records = vtr.training_records()
    point = vtr.correction_point(records)
    assert point["all_slots_carry_the_teacher_answer"] is True
    assert point["all_sets_permuted_only"] is True
    assert len(point["records"]) == 8
    for row in point["records"]:
        assert canonical(row["value_at_encoded_correct_index"]) == canonical(
            row["teacher_expected_answer"])
        assert row["encoded_correct_index"] in (0, 1, 2)
        assert row["declared_slot"] in (0, 1, 2)
    assert point["correction_stage"]["index_built_from"] == "record['correct']"
    assert "cross_entropy" in point["correction_stage"]["where"]


def test_the_real_trainer_loop_reaches_every_record_with_the_teacher_target():
    check = vtr.connection_check()
    assert check["records"] == 8
    assert check["every_record_reached"] is True
    assert check["records_that_received_correction"] == 8
    # the field-name correction: these calls went to a stub, so no update occurred
    assert check["stub_training_step_calls"] == trainer.FROZEN_MAX_OPTIMIZER_STEPS
    assert check["actual_optimizer_updates"] == 0
    assert check["actual_neural_presentations"] == 0
    assert "optimizer_updates_in_this_check" not in check
    correction = check["field_correction"]
    assert correction["replaced"] == "optimizer_updates_in_this_check"
    assert correction["with"] == ["stub_training_step_calls",
                                  "actual_optimizer_updates",
                                  "actual_neural_presentations"]
    assert set(check["corrective_targets_used"]) == _teacher_answers()
    assert check["neural_execution"] is False
    assert check["torch_imported"] is False
    assert check["learner_is_a_stub"] is True
    assert "not model predictions" in check["stub_note"]
    exposure = check["lesson_exposure"]
    assert sum(exposure["updates_by_op"].values()) == trainer.FROZEN_MAX_OPTIMIZER_STEPS
    assert exposure["records_by_op"] == {"REACHED_VIA": 6, "LIST_PARTS": 1,
                                        "FIND_SHARED_PART": 1}
    assert "not a complete teaching cycle" in exposure["boundary"]
    assert check["stub_step_allocation_by_op"] == {"REACHED_VIA": 48,
                                                   "LIST_PARTS": 8,
                                                   "FIND_SHARED_PART": 8}
    assert "not a proposed teaching schedule" in check["stub_step_allocation_note"]


def test_connection_reuses_existing_machinery_and_imports_no_neural_code():
    for forbidden in ("import torch", "boto3", "gpu_adapter", "from .real_framework"):
        assert forbidden not in MODULE_SOURCE
    assert vtr.CONNECTION_SCHEMA in MODULE_SOURCE
    assert "torch" not in sys.modules or vtr.connection_check()["torch_imported"] is False
    assert list(inspect.signature(trainer.run_training).parameters)[:4] == \
        ["learner", "records", "arm", "budget"]
    assert list(inspect.signature(trainer.make_task).parameters) == ["record", "arm"]
    budget = trainer.TrainingBudget().validate()
    assert budget.learning_rate == trainer.FROZEN_LEARNING_RATE
    assert budget.max_optimizer_steps == trainer.FROZEN_MAX_OPTIMIZER_STEPS
    assert budget.max_wall_seconds == trainer.FROZEN_MAX_WALL_SECONDS
    task = trainer.make_task(vtr.training_records()[0], "cas")
    assert set(task) >= {"record_id", "op", "correct", "options", "prompt", "graph"}


def test_launch_has_no_record_injection_parameter_which_is_why_the_connection_is_here():
    parameters = inspect.signature(trainer.launch).parameters
    assert "records" not in parameters
    plan = vtr.dry_run_plan()
    assert any("no record-injection parameter" in item for item in plan["not_used"])
    assert plan["execution_enabled"] is False
    assert "no paid run" in plan["authorization"]
    assert plan["seven_stage_status"].startswith("stages 1, 2, 3, 4 and 6 remain")
    assert "UNIMPLEMENTED" in plan["seven_stage_status"]
    assert "KeyError" in plan["learner_indexing_requirement"]
    assert len(plan["sequence"]) == 9
    steps = {item["step"]: item["call"] for item in plan["sequence"]}
    assert "trainer.run_training" in steps[7]
    assert "public_records" in steps[4]


def test_stub_learner_records_what_it_is_taught_and_predicts_nothing():
    stub = vtr.StubLearner(vtr.learner_index(vtr.training_records()))
    assert not hasattr(stub, "predict")
    record = vtr.training_records()[0]
    task = trainer.make_task(record, "cas")
    assert stub.step(task) == 0.0
    assert stub.steps[0]["correct"] == record["correct"]
    assert stub.eval_loss(record["op"], [task]) == {"total": 0.0}
    assert stub.checkpoint_identity() == "STUB_NO_PARAMETERS"


def test_ordering_mode_is_explicit_and_mismatches_are_refused():
    authored = _report("authored_fixture")
    with pytest.raises(ValueError) as error:
        vtr.training_records(ordering_mode="declared", report=authored)
    assert "VT_CONNECTION_ORDERING_MODE_MISMATCH" in str(error.value)
    records = vtr.training_records(ordering_mode="authored_fixture", report=authored)
    assert len(records) == 8
    assert vtr.correction_point(records)["all_slots_carry_the_teacher_answer"] is True


def test_unverified_targets_are_refused():
    report = _report()
    tampered = json.loads(canonical(report))
    tampered["private_teacher_targets"][0]["reference_verification"]["status"] = \
        "PENDING_REFERENCE_CHECK"
    with pytest.raises(ValueError) as error:
        vtr.training_records(report=tampered)
    assert "VT_CONNECTION_TARGET_NOT_VERIFIED" in str(error.value)


def test_connection_check_and_dry_run_are_deterministic_and_serializable():
    first = vtr.connection_check()
    second = vtr.connection_check()
    assert json.dumps(first, sort_keys=True, allow_nan=False) == \
        json.dumps(second, sort_keys=True, allow_nan=False)
    plan = vtr.dry_run_plan()
    assert json.dumps(plan, sort_keys=True, allow_nan=False)
    assert plan["correction_point"]["arm"] == "cas"
    assert plan["ordering_mode"] == "declared"


def test_the_public_problem_is_the_shape_the_frozen_encoder_parses():
    """The learner's problem must be the graph's node/rel presentation.

    Attempt 006 died on the instance with

        ValueError: tuple.index(x): x not in tuple
        node_id = vocabulary.index(_word_token("node"))

    because the records restated their relations as "Facts:" prose. The frozen
    encoder (``real_framework.build_encoder``) fits its vocabulary on these very
    publics and then requires a ``node`` token, a ``rel`` token, a newline token,
    and at least one structural segment per problem - it fails closed on anything
    else (``PROBLEM_STRUCTURAL_SEGMENTS_REQUIRED``). No torch is needed to check
    any of that: the tokenizer is pure text.
    """
    from cas_meta2.features_v2 import LosslessPublicTokenizer, _word_token
    from cas_meta2.graph_teaching import candidate_experiment as ce, real_framework

    inputs = ce.build_inputs()
    publics = [adapter.public_records(record, "cas")["public"]
               for record in inputs["records"] + inputs["probe"]]
    assert len(publics) == 52, "8 taught plus the 44-question probe"
    tokenizer = LosslessPublicTokenizer.fit_train(
        publics, max_length=real_framework.FROZEN_ENCODER_MAX_LENGTH)
    vocabulary = tuple(tokenizer.vocabulary)
    for unit in ("node", "rel", "\n"):
        assert _word_token(unit) in vocabulary, unit
    markers = {vocabulary.index(_word_token("node")),
               vocabulary.index(_word_token("rel"))}
    newline = vocabulary.index(_word_token("\n"))
    for index, public in enumerate(publics):
        lines = public["problem"].splitlines()
        assert lines[0].startswith("node "), (index, lines[0])
        assert any(line.startswith("rel ") for line in lines), index
        encoded = tokenizer.encode_public(public)
        problem_ids = [token for token, kind in zip(encoded["ids"], encoded["kinds"])
                       if kind == 0]
        segments, current = 0, None
        for token in problem_ids:                      # the encoder's own rule
            if token == newline:
                current = None
            elif token in markers:
                current = [token]
                segments += 1
            elif current is not None:
                current.append(token)
        assert segments, ("PROBLEM_STRUCTURAL_SEGMENTS_REQUIRED", index)
        slots = {slot - 1 for token, kind, slot
                 in zip(encoded["ids"], encoded["kinds"], encoded["slots"])
                 if kind == 2 and slot in (1, 2, 3)}
        assert slots == {0, 1, 2}, (index, slots)


def test_the_private_teacher_target_cannot_reach_the_public_bytes():
    """The id, the visible problem and the visible option order are public-only.

    The records delivered by Attempt 007 folded the private target's
    ``expected_choice_id`` and ``witness_kind`` into the digest that becomes
    ``record_id``, and the adapter derives the learner-visible option ORDER from
    that id. Measured on the eight taught records, flipping the private target to
    another offered choice left every prompt identical and changed the record id
    on 8 of 8 and the visible option order on 4 of 8. New compilations digest a
    public projection instead; the delivered records keep the ids they were
    measured with, so nothing already measured is rewritten.
    """
    bundle = cube_node.load_bundle()
    report = vt.compile_bundle(bundle, choice_order="declared")
    index = vt.Index(bundle, vt.lesson_context(bundle, "view_context"),
                     "view_context")
    targets = {target["exercise_id"]: target
               for target in report["private_teacher_targets"]}
    for exercise in report["public_exercises"]:
        target = targets[exercise["exercise_id"]]
        choices = {choice["choice_id"]: choice["value"]
                   for choice in exercise["choices"]}
        choice_id, value = sorted(
            (cid, option) for cid, option in choices.items()
            if option != target["expected_answer"])[0]
        flipped = dict(target, expected_answer=value,
                       expected_choice_id=choice_id)
        first = vtr.record_from_exercise(bundle, exercise, target, index,
                                         "view_context", "audit")
        second = vtr.record_from_exercise(bundle, exercise, flipped, index,
                                          "view_context", "audit")
        assert first["record_id"] == second["record_id"], exercise["exercise_id"]
        assert first["correct"] != second["correct"], "the target did change"
        first_public = adapter.public_records(first, "cas")
        second_public = adapter.public_records(second, "cas")
        assert first_public["public"] == second_public["public"]
        assert first_public["encoded_options"] == second_public["encoded_options"]
        assert first["cube_verified_teaching"]["expected_choice_id"] == \
            target["expected_choice_id"]
        assert first["cube_verified_teaching"]["witness_kind"] == \
            target["witness"]["kind"]
        assert first["cube_verified_teaching"]["record_id_basis"] == \
            "public_projection"
