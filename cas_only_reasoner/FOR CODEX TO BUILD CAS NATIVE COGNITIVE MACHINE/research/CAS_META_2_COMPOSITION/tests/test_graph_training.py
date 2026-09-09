"""Pure tests for the targeted ^6 specialist training mode.

Injected fakes only: no torch, no cas_cjt, no GPU, no AWS, no network. Locks
the frozen budget, the parameter-scope discipline (only operator.^6 may
change), the containment report, the sealed-split boundary, and the CAS/generic
arm framing.
"""
import json
from hashlib import sha256
from types import SimpleNamespace

import pytest

from cas_meta2.graph_teaching import lessons, trainer
from cas_meta2.graph_teaching.graph import canonical, digest


class FakeParam:
    def __init__(self, value):
        self.value = value
        self.flag = False

    def requires_grad_(self, flag):
        self.flag = flag


class FakeModel:
    def __init__(self):
        self.parameters = {"a": FakeParam(1), "b": FakeParam(2), "c": FakeParam(3)}

    def named_parameters(self):
        for name, param in self.parameters.items():
            yield name, param


class FakeFramework:
    def __init__(self, allowed=("b",), registrations=1):
        self.allowed = list(allowed)
        self.registrations = registrations

    @property
    def operation_registrations(self):
        if self.registrations == 0:
            return []
        entries = [SimpleNamespace(contract_id=trainer.TARGET_CONTRACT_ID)]
        if self.registrations == 2:
            entries.append(SimpleNamespace(contract_id=trainer.TARGET_CONTRACT_ID))
        return entries

    def contract_for(self, contract_id):
        return SimpleNamespace(plasticity_groups=(trainer.TARGET_PLASTICITY_ROLE,
                                                  "bias_update_head"))

    def resolve_plasticity_groups(self, model, role, contract):
        assert role == trainer.TARGET_PLASTICITY_ROLE
        return self.allowed

    @staticmethod
    def tensor_bytes(parameter):
        return json.dumps(parameter.value).encode("utf-8")

    def build_decompose_model(self, seed):
        return FakeModel()


class FakeLearner:
    def __init__(self, model, arm, learning_rate, touch_frozen=False, answers=None):
        self.model = model
        self.arm = arm
        self.learning_rate = learning_rate
        self.touch_frozen = touch_frozen
        self.answers = answers or {}
        self.steps = 0

    def eval_loss(self, op, tasks):
        return {"total": 1.0 + 0.01 * len(tasks)}

    def step(self, task):
        self.steps += 1
        self.model.parameters["b"].value += 1  # permitted group
        if self.touch_frozen:
            self.model.parameters["c"].value += 1  # forbidden group
        return 0.5

    def checkpoint_identity(self):
        return digest(canonical({name: param.value
                                 for name, param in self.model.parameters.items()}))

    def predict(self, task_input):
        assert "correct" not in task_input  # inference input is answer-free
        return self.answers.get(task_input["record_id"], task_input["options"][0])


def launch_args(seed=20260909, **kwargs):
    touch_frozen = kwargs.pop("touch_frozen", False)
    framework = FakeFramework()
    model = FakeModel()
    base = {"run_id": "graph-training-test-run", "arm": "cas", "seed": seed,
            "framework": framework, "model": model,
            "learner_factory": lambda m, arm, learning_rate:
                FakeLearner(m, arm, learning_rate, touch_frozen=touch_frozen)}
    base.update(kwargs)
    return base


def test_frozen_budget_defaults_and_rejection():
    budget = trainer.TrainingBudget().validate()
    assert budget.max_optimizer_steps == 64
    assert budget.max_wall_seconds == 600.0
    assert budget.learning_rate == 0.003
    with pytest.raises(ValueError, match="BUDGET_MAX_OPTIMIZER_STEPS_FROZEN"):
        trainer.TrainingBudget(max_optimizer_steps=48).validate()


def test_select_target_requires_unique_decompose_contract():
    with pytest.raises(ValueError, match="TARGET_CONTRACT_NOT_UNIQUE"):
        trainer.select_target(FakeFramework(registrations=0))
    with pytest.raises(ValueError, match="TARGET_CONTRACT_NOT_UNIQUE"):
        trainer.select_target(FakeFramework(registrations=2))
    registration, contract = trainer.select_target(FakeFramework())
    assert registration.contract_id == trainer.TARGET_CONTRACT_ID
    assert trainer.TARGET_PLASTICITY_ROLE in contract.plasticity_groups


def test_scope_freezes_everything_outside_the_allowlist():
    framework = FakeFramework(allowed=("b",))
    model = FakeModel()
    scope = trainer.scope_parameters(framework, model)
    assert scope["allowed"] == ["b"]
    assert set(scope["frozen"]) == {"a", "c"}
    assert model.parameters["b"].flag is True
    assert model.parameters["a"].flag is False
    assert model.parameters["c"].flag is False


def test_containment_report_flags_forbidden_changes():
    framework = FakeFramework()
    model = FakeModel()
    before = trainer.parameter_snapshot(framework, model)
    model.parameters["b"].value += 1  # permitted
    after = trainer.parameter_snapshot(framework, model)
    report = trainer.containment_report(before, after, ["b"])
    assert report["contained"] is True
    assert report["permitted_changes"] == ["b"]
    assert report["forbidden_changes"] == []
    model.parameters["c"].value += 1  # forbidden
    after = trainer.parameter_snapshot(framework, model)
    report = trainer.containment_report(before, after, ["b"])
    assert report["contained"] is False
    assert report["forbidden_changes"] == ["c"]


def test_run_training_bounds_steps_and_reports_losses():
    records = trainer.training_records(20260909)
    framework = FakeFramework()
    model = FakeModel()
    learner = FakeLearner(model, arm="cas", learning_rate=0.003)
    budget = trainer.TrainingBudget(max_optimizer_steps=7, max_wall_seconds=60.0)
    training = trainer.run_training(learner, records, "cas", budget)
    assert training["completed_updates"] == 7
    assert learner.steps == 7
    assert set(training["before_loss"]) == {"FIND_SHARED_PART", "LIST_PARTS", "REACHED_VIA"}
    assert set(training["after_loss"]) == set(training["before_loss"])
    assert training["automatic_retries"] == 0


def test_training_records_are_train_practice_whole_part_only():
    records = trainer.training_records(20260909)
    dataset = lessons.build_dataset(seed=20260909)
    train_practice_ids = {r["record_id"] for split in ("train", "practice")
                          for r in dataset[split]}
    sealed_ids = {r["record_id"] for split in ("validation", "test")
                  for r in dataset[split]}
    for record in records:
        assert record["record_id"] in train_practice_ids
        assert record["record_id"] not in sealed_ids
        assert record["family"] == "whole_part"
        assert record["op"] in trainer.WHOLE_PART_OPS


def test_launch_reports_scope_containment_and_honest_claims():
    report = trainer.launch(**launch_args())
    assert report["schema"] == trainer.MODE_SCHEMA
    assert report["condition"]["arm"] == "cas"
    assert report["condition"]["kind"] == "prompt_framing_only"
    assert report["target"]["contract_id"] == trainer.TARGET_CONTRACT_ID
    assert report["target"]["plasticity_role"] == "operation:^6"
    assert report["scope"]["allowed"] == ["b"]
    assert report["containment"]["contained"] is True
    assert report["containment"]["permitted_changes"] == ["b"]
    assert report["training"]["completed_updates"] == 64
    assert report["budget"]["per_arm"]["max_optimizer_steps"] == 64
    assert report["budget"]["total"] == {"arms": 2, "optimizer_steps": 128,
                                         "wall_seconds": 1200.0}
    assert report["claims"] == {"specialist_claimed": False,
                                "sealed_splits_read": False,
                                "answer_edges_present": False}


def test_real_target_matches_the_real_contract():
    assert trainer.TARGET_CONTRACT_ID == "cas.cjt.operation.^6.decompose/0.2"
    assert trainer.TARGET_PLASTICITY_ROLE == "operation:^6"


def test_lesson_exposure_counts_records_and_updates_per_op():
    records = trainer.training_records(20260909)
    framework = FakeFramework()
    model = FakeModel()
    learner = FakeLearner(model, arm="cas", learning_rate=0.003)
    budget = trainer.TrainingBudget(max_optimizer_steps=7, max_wall_seconds=60.0)
    training = trainer.run_training(learner, records, "cas", budget)
    exposure = training["lesson_exposure"]
    assert sum(exposure["records_by_op"].values()) == len(records)
    assert sum(exposure["updates_by_op"].values()) == 7
    assert exposure["boundary"]  # an optimizer step is not a teaching cycle


def test_prediction_input_is_answer_free():
    records = trainer.training_records(20260909)
    task = trainer.make_task(records[0], arm="generic")
    task_input = trainer.prediction_input(task)
    assert "correct" not in task_input
    assert task_input["record_id"] == task["record_id"]


def test_launch_flags_any_forbidden_parameter_change():
    report = trainer.launch(**launch_args(touch_frozen=True))
    assert report["containment"]["contained"] is False
    assert report["containment"]["forbidden_changes"] == ["c"]
    assert report["claims"]["specialist_claimed"] is False


def test_launch_rejects_budget_mismatch():
    with pytest.raises(ValueError, match="BUDGET_LEARNING_RATE_FROZEN"):
        trainer.launch(**launch_args(learning_rate=0.1))


def test_arm_framing_controls_the_task_prompt():
    records = trainer.training_records(20260909)
    record = records[0]
    cas_task = trainer.make_task(record, arm="cas")
    generic_task = trainer.make_task(record, arm="generic")
    assert "^6" in cas_task["prompt"] and "^8" in cas_task["prompt"]
    assert "^6" not in generic_task["prompt"]
    assert cas_task["graph"] == generic_task["graph"]
    assert cas_task["correct"] == generic_task["correct"]


def test_evaluate_sealed_reads_only_sealed_splits():
    dataset = lessons.build_dataset(seed=20260909)
    answers = {record["record_id"]: record["correct"] for split in ("validation", "test")
               for record in dataset[split] if record["family"] == "whole_part"}
    framework = FakeFramework()
    model = FakeModel()
    learner = FakeLearner(model, arm="generic", learning_rate=0.003, answers=answers)
    metrics = trainer.evaluate_sealed(learner, seed=20260909)
    assert set(metrics["per_split_op"]) == {
        ("validation", "LIST_PARTS"), ("validation", "FIND_SHARED_PART"),
        ("validation", "REACHED_VIA"), ("test", "LIST_PARTS"),
        ("test", "FIND_SHARED_PART"), ("test", "REACHED_VIA")}
    for bucket in metrics["per_split_op"].values():
        assert bucket["correct"] == bucket["attempted"]
    # the seal: every recorded prediction is answer-free and precedes scoring
    for prediction in metrics["sealed_predictions"]:
        assert "correct" not in prediction
        assert set(prediction) == {"record_id", "split", "op", "predicted"}


def test_trainer_module_imports_nothing_heavy():
    assert not hasattr(trainer, "torch")
    assert "cas_cjt" not in trainer.__dict__
    assert "boto3" not in trainer.__dict__
