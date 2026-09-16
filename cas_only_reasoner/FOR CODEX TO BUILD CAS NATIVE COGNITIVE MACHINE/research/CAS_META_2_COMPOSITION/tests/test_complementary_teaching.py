"""Production compiler/executor/package pure checks; NO torch/model/provider."""
import ast
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from cas_meta2.complementary_teaching import course, data, evaluation, runner
from aws import complementary_teaching_launch as launch

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def compiled():
    return {(seed, condition): course.compile_complementary_course(seed, condition)
            for seed in course.SEEDS for condition in course.CONDITIONS}


@pytest.mark.parametrize("seed", course.SEEDS)
def test_actual_cfc_courses_exactly_matched(compiled, seed):
    schedules = [compiled[(seed, condition)] for condition in course.CONDITIONS]
    for schedule in schedules:
        counts = schedule["counts"]
        assert (counts["decisions"], counts["optimizer_updates"], counts["sample_core_passes_planned"],
                counts["batch_core_forward_calls_planned"]) == (1152, 160, 4320, 600)
        assert Counter(schedule["depths"]) == {1: 4, 2: 4, 4: 4, 8: 4}
        assert counts["duplicate_semantic_exposures"] > 0
    for round_index in range(16):
        groups = [schedule["batches"][round_index * 10:(round_index + 1) * 10] for schedule in schedules]
        for batch in range(10):
            if batch not in (7, 8):
                assert groups[0][batch] == groups[1][batch] == groups[2][batch]
        content = [Counter(course.digest({k: v for k, v in task.items() if k != "teaching_role"})
                           for batch in group[7:9] for task in batch["tasks"]) for group in groups]
        assert content[0] == content[1]
        assert groups[2][7]["tasks"] == groups[2][8]["tasks"]
        assert all(task["teaching_role"] == "WHOLE" for batch in groups[2][7:9] for task in batch["tasks"])


def test_private_target_mutation_does_not_change_any_public_input(compiled):
    for pair in compiled[(101, course.CONDITIONS[0])]["pairs_by_round"][0]:
        for role in ("component", "whole"):
            before = pair[role]
            mutated = deepcopy(before)
            mutated["correct"] = "deliberately_wrong_private_target"
            mutated["encoded_correct_index"] = (before["encoded_correct_index"] + 1) % 3
            assert runner.public_task(mutated) == runner.public_task(before)
            assert course.public_identity(mutated) == course.public_identity(before)


def test_cfc_rendered_variants_keep_semantic_identity_and_exact_base_inputs():
    base = course.base.default_tasks_for_round(0)
    decorated = course.foundation_tasks_for_round(0)
    for phase, tasks in decorated.items():
        for task, original in zip(tasks, base[phase]):
            assert {key: value for key, value in task.items() if key != "semantic_question_id"} == original
    # Stage5 and reinforcement repeat the same graph/question with different
    # support/option/rendering exposure; neither is a new semantic question.
    tasks = decorated["WITHIN_CUBE"]
    assert tasks[4]["semantic_question_id"] == tasks[6]["semantic_question_id"]


def test_transform_cannot_mutate_target_or_question(compiled):
    def mutate(task, **kwargs):
        task["correct"] = "wrong"
        return task
    with pytest.raises(ValueError, match="TRANSFORM_SEMANTIC_MUTATION"):
        course.compile_complementary_course(101, course.CONDITIONS[0], public_transform=mutate)


def test_same_id_different_public_input_refused(compiled):
    schedule = deepcopy(compiled[(101, course.CONDITIONS[0])])
    first = schedule["batches"][0]["tasks"][0]
    other = deepcopy(first)
    other["public"]["problem"] += "changed"
    schedule["batches"][-1]["tasks"][0] = other
    with pytest.raises(ValueError, match="PUBLIC_COLLISION"):
        course.task_index(schedule)


class FakeLearner:
    def __init__(self):
        self.module, self.optimizer = object(), object()
        self.cursor = 0
    def set_depth(self, depth):
        self.depth = depth
    def checkpoint_identity(self):
        return str(self.cursor)


def fake_step(learner, tasks):
    learner.cursor += 1
    return {"optimizer_steps": 1, "mean_loss": 1.0,
            "episodes": [{"scores": [0., 1., 0.], "selected_index": 1} for _ in tasks]}


def test_persistent_optimizer_phase_commit_and_seventeen_readonly_points(compiled):
    schedule = compiled[(101, course.CONDITIONS[0])]
    learner = FakeLearner()
    observations, committed, calls = [], [], []
    def step(current, tasks):
        calls.append((current.cursor, tasks[0]["teaching_role"], id(current.optimizer)))
        return fake_step(current, tasks)
    outcome = course.run_complementary_course(learner=learner, schedule=schedule, batch_step=step,
        observer=lambda current, point: observations.append((current.cursor, point)),
        checkpoint=lambda current, cursor, rows, kind: committed.append(cursor))
    assert outcome["status"] == "TEACHING_COMPLETE" and learner.cursor == 160
    assert len({row[2] for row in calls}) == 1
    assert calls[7][:2] == (7, "COMPONENT") and calls[8][:2] == (8, "WHOLE")
    assert committed == list(range(1, 161))
    assert len(observations) == 17 and observations[0][0] == 0 and observations[-1][0] == 160


def test_recovery_does_not_duplicate_committed_updates(compiled):
    schedule = compiled[(101, course.CONDITIONS[0])]
    learner = FakeLearner()
    ticks = iter([0, 0, 0, 0, 0, 0, 2])
    incomplete = course.run_complementary_course(learner=learner, schedule=schedule,
        batch_step=fake_step, deadline=1, clock=lambda: next(ticks, 2))
    assert incomplete["status"] == "TEACHING_INCOMPLETE"
    prior = incomplete["next_cursor"]
    outcome = course.run_complementary_course(learner=learner, schedule=schedule,
        batch_step=fake_step, prior_rows=incomplete["rows"], next_cursor=prior)
    assert len(outcome["rows"]) == learner.cursor == 160
    assert [row["cursor"] for row in outcome["rows"]] == list(range(160))


def test_recovery_cursor_mismatch_and_original_error_survive(compiled):
    learner = FakeLearner()
    with pytest.raises(ValueError, match="RECOVERY_CURSOR"):
        course.run_complementary_course(learner=learner, schedule=compiled[(101, course.CONDITIONS[0])],
            batch_step=fake_step, next_cursor=1)
    def broken(*args):
        raise RuntimeError("ORIGINAL_FAILURE")
    with pytest.raises(RuntimeError, match="ORIGINAL_FAILURE"):
        course.run_complementary_course(learner=learner, schedule=compiled[(101, course.CONDITIONS[0])], batch_step=broken)
    assert learner.cursor == 0


def test_optimizer_replacement_rejected(compiled):
    learner = FakeLearner()
    def replace(current, tasks):
        current.optimizer = object()
        return fake_step(current, tasks)
    with pytest.raises(ValueError, match="OPTIMIZER_REPLACED"):
        course.run_complementary_course(learner=learner, schedule=compiled[(101, course.CONDITIONS[0])], batch_step=replace)


def test_full_historical_exclusions_and_new_root_families():
    path = ROOT / "records/complementary_teaching_001/preparation_20260916"
    exclusions = json.loads((path / "historical_exclusions.json").read_bytes())
    assert exclusions["complete"] and not exclusions["failures"]
    assert len({row["sha256"] for row in exclusions["archives"]}) == 15
    manifest = data.validate_manifest(json.loads((path / "data_manifest.json").read_bytes()))
    assert not set(exclusions["excluded_topologies"]) & {row["topology"] for row in manifest["families"]}
    assert manifest["counts"]["final_application"] == 90
    assert {task["audit_face"] for task in manifest["panels"]["final_earlier_skills"]} == set(range(1, 7))


def test_all_heldout_audits_are_disjoint_from_actual_maintenance(compiled):
    manifest = json.loads((ROOT / runner.DATA_PATH).read_bytes())
    audit_families = {task["family_id"] for rows in manifest["panels"].values() for task in rows}
    teaching = {task["family_id"] for batch in compiled[(101, course.CONDITIONS[0])]["batches"] for task in batch["tasks"]}
    assert not audit_families & teaching


def test_config_disabled_before_cuda_or_model_loading():
    config = launch.worker_config("test")
    with pytest.raises(ValueError, match="EXECUTION_DISABLED"):
        runner.validate_config(config, ROOT)
    config["execution_enabled"] = True
    runner.validate_config(config, ROOT)
    config["data_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="DATA_IDENTITY"):
        runner.validate_config(config, ROOT)


def test_packaged_dispatch_and_all_dependency_inputs_exist():
    worker = launch.render_worker()
    ast.parse(worker)
    assert "from cas_meta2.complementary_teaching import runner" in worker
    assert "from cas_meta2.recurrent_cjt import runner" not in worker
    assert "RESULT_SCHEMA = 'cas.complementary-result/0.1'" in worker
    assert "MAX_WALL_SECONDS = 3000.0" in worker
    assert "timeout=MAX_WALL_SECONDS +" not in worker
    for relative in launch.package_data_files():
        assert (ROOT.parent.parent / relative).is_file(), relative
    assert "torch" not in sys.modules


def test_total_job_cost_includes_all_nine_courses_monitors_and_reload():
    request = launch.costed_request()
    assert request["owner_authorization"] is request["signature"] is None
    assert request["all_courses"]["optimizer_updates"] == 1440
    assert request["all_courses"]["total_inference_core_passes"] == 187632
    assert request["resource_limits"]["reservation_usd"] == "7.00"
    assert len(launch.evidence_contract()["required"]) == 184


def test_unsigned_authority_cannot_launch():
    with pytest.raises(ValueError, match="AUTHORITY_SCHEMA"):
        launch.validate_authority(launch.costed_request())


@pytest.mark.parametrize("field,value", [("training", False), ("training", None),
    ("max_wall_seconds", 1200), ("max_wall_seconds", None), ("optimizer_updates", 0),
    ("total_optimizer_steps", 960), ("conditions", []), ("seeds", [101])])
def test_top_level_authority_cannot_understate_real_worker_scope(field, value):
    job = "cas-meta2-complementary-20260916000000-00000000"
    authority = {"schema": launch.AUTHORITY_SCHEMA, "candidate": launch.IMPLEMENTATION_ID,
        "job": job, "reservation_usd": "7.00", "training": True,
        "optimizer_updates": 1440, "total_optimizer_steps": 1440, "max_wall_seconds": 3000,
        "conditions": list(course.CONDITIONS), "seeds": list(course.SEEDS),
        "worker_config": launch.worker_config(job, execution_enabled=True),
        "owner_authorization_sha256": "0" * 64,
        "evidence_contract_sha256": launch.run_evidence.contract_digest(launch.evidence_contract())}
    launch.validate_authority(authority)
    authority[field] = value
    with pytest.raises(ValueError, match="COMPLEMENTARY_AUTHORITY"):
        launch.validate_authority(authority)


def test_missing_course_and_missing_paired_rows_not_negative_scores():
    with pytest.raises(ValueError, match="NINE_COMPLETE_COURSES"):
        evaluation.analyze({"courses": []})
    with pytest.raises(ValueError, match="PAIRED_ROWS_MISSING"):
        evaluation._paired([{"record_id": "a", "family_id": "f", "correct": True}], [])


def test_pairing_and_bootstrap_keep_families_as_units():
    a = [{"record_id": "x%d" % i, "family_id": "f%d" % (i // 3), "correct": True} for i in range(9)]
    b = [{**row, "correct": False} for row in a]
    paired = evaluation._paired(a, b)
    assert len(paired) == 3 and evaluation.bootstrap(paired.values()) == [1.0, 1.0]


def test_missing_starting_competence_means_retention_unassessed():
    row = {"record_id": "a", "family_id": "f", "correct": False}
    rows = {"final_components": [row], "final_earlier_skills": [row]}
    index = {(condition, seed): {"initial": {"rows": rows}, "final": {"rows": rows}}
             for condition in course.CONDITIONS for seed in course.SEEDS}
    assert evaluation.retention(index)["status"] == "RETENTION_UNASSESSED"


def test_retention_keeps_per_face_changes_and_intervals():
    initial = [{"record_id": "r%d" % face, "family_id": "family", "op": "ROLE_FROM_CONTENT",
                "audit_face": face, "correct": True} for face in (1, 2)]
    final = [dict(row, correct=row["audit_face"] == 2) for row in initial]
    def panels(rows):
        return {"final_components": rows, "final_earlier_skills": rows}
    index = {(condition, seed): {"initial": {"rows": panels(initial)},
             "final": {"rows": panels(final if condition == course.CONDITIONS[0] else initial)}}
             for condition in course.CONDITIONS for seed in course.SEEDS}
    result = evaluation.retention(index)
    assert result["status"] == "OBSERVED_RETENTION_CONSTRAINT_NOT_MET"
    faces = {row["face"]: row for row in result["rows"][0]["per_operation_face"]}
    assert faces[1]["difference_from_initial"] == -1
    assert faces[1]["control_difference_interval_95"] == [-1, -1]
    assert faces[2]["difference_from_initial"] == 0
