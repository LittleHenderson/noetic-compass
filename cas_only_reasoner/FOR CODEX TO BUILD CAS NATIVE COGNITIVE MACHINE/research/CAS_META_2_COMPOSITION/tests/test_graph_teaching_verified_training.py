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
    assert check["optimizer_updates_in_this_check"] == \
        trainer.FROZEN_MAX_OPTIMIZER_STEPS
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
