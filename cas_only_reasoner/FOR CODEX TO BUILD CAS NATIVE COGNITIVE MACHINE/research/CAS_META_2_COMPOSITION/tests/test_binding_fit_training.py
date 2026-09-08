"""Pure tests for the small training-fit mode; no real tensor library is imported.

Fake torch/model/tokenizer/optimizer objects exercise the identity-checked
backward/step contract without importing torch. The mode's ``import_torch`` seam
is monkeypatched to prove real tensors are never reached.
"""
import ast
from copy import deepcopy
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

import cas_meta2.binding_fit_training.mode as mode
from cas_meta2.teaching_cycle import data, lesson_contract as lesson

FORBIDDEN_LIBS = {"torch", "numpy", "casformer", "boto3", "botocore", "sqlite3"}


# --------------------------------------------------------------------------- #
# Fakes: injected tensors/models/tokenizers/optimizers only.
# --------------------------------------------------------------------------- #

class FakeScalar:
    def __init__(self, value, log):
        self.value = float(value)
        self._log = log

    def item(self):
        return self.value

    def backward(self):
        self._log.append("backward")


class FakeTensor:
    def __init__(self, data, dtype=None):
        self.data = data
        self.dtype = dtype

    @property
    def shape(self):
        if not self.data:
            return (0,)
        if isinstance(self.data[0], (list, tuple)):
            return (len(self.data), len(self.data[0]))
        return (len(self.data),)

    def tolist(self):
        return [list(row) if isinstance(row, (list, tuple)) else row for row in self.data]


class _NoGrad:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeTorch:
    long = "long"
    float32 = "float32"

    def __init__(self, log):
        self.log = log
        self.nn = SimpleNamespace(functional=SimpleNamespace(cross_entropy=self.cross_entropy))

    def tensor(self, data, dtype=None):
        return FakeTensor(data, dtype)

    def no_grad(self):
        return _NoGrad()

    def isfinite(self, value):
        return math.isfinite(value.item() if hasattr(value, "item") else value)

    def cross_entropy(self, logits, labels):
        self.log.append("cross_entropy")
        return FakeScalar(0.5, self.log)


class FakeModel:
    def __init__(self, log):
        self.log = log
        self._weights = [0.0]

    def state_dict(self):
        return {"w": list(self._weights)}

    def train(self):
        return None

    def eval(self):
        return None

    def __call__(self, batch):
        self.log.append("forward")
        batch_size = len(batch["ids"].data)
        return {"binding_logits": FakeTensor([[2.0, 0.0, 0.0] for _ in range(batch_size)])}


class FakeTokenizer:
    max_length = 512

    def encode_public(self, public):
        return {"ids": [1, 2, 3, 4, 5], "values": [[0.0] * 8 for _ in range(3)]}


class FakeOptimizer:
    def __init__(self, model, log, mutate=True):
        self.model = model
        self.log = log
        self.mutate = mutate

    def zero_grad(self, set_to_none=True):
        self.log.append("zero_grad")

    def step(self):
        self.log.append("step")
        if self.mutate:
            self.model._weights[0] += 0.1


def make_fake_learner(family, log, mutate=True):
    model = FakeModel(log)
    return mode.BindingFitLearner(
        FakeTorch(log), model, FakeTokenizer(), FakeOptimizer(model, log, mutate=mutate),
        family=family, run_id="run." + family)


# --------------------------------------------------------------------------- #
# 1. 24-case balance validation.
# --------------------------------------------------------------------------- #

def test_build_balanced_cases_has_24_and_8_per_slot_from_known_families():
    cases = mode.build_balanced_cases()
    assert len(cases) == mode.TOTAL_CASES == 24
    assert [sum(c["target_binding"] == slot for c in cases) for slot in mode.BINDING_SLOTS] == [8, 8, 8]
    assert all(c["split"] == "train" for c in cases)
    assert len({c["family_id"] for c in cases}) == 24
    known = {c["family_id"] for c in data.build_dataset()["splits"]["train"]}
    assert all(c["family_id"] in known for c in cases)


def test_validate_balanced_cases_refuses_empty_and_wrong_count():
    cases = mode.build_balanced_cases()
    with pytest.raises(ValueError, match="CASE_COUNT_INVALID"):
        mode.validate_balanced_cases([])
    with pytest.raises(ValueError, match="CASE_COUNT_INVALID"):
        mode.validate_balanced_cases(cases[:-1])


def test_validate_balanced_cases_refuses_non_train_split():
    cases = mode.build_balanced_cases()
    relabeled = deepcopy(cases)
    relabeled[0]["split"] = "test_fresh"
    with pytest.raises(ValueError, match="NON_TRAIN_CASE_REJECTED"):
        mode.validate_balanced_cases(relabeled)


def test_validate_balanced_cases_refuses_binding_imbalance():
    train = data.build_dataset()["splits"]["train"]
    by_slot = {s: [c for c in train if c["target_binding"] == s] for s in mode.BINDING_SLOTS}
    cases = by_slot[0][:9] + by_slot[1][:8] + by_slot[2][:7]
    assert len(cases) == 24
    with pytest.raises(ValueError, match="BINDING_BALANCE_INVALID"):
        mode.validate_balanced_cases(cases)


def test_validate_balanced_cases_refuses_duplicate_family():
    cases = mode.build_balanced_cases()
    duplicated = deepcopy(cases)
    duplicated[1] = deepcopy(cases[0])
    with pytest.raises(ValueError, match="DUPLICATE_FAMILY"):
        mode.validate_balanced_cases(duplicated)


def test_validate_balanced_cases_refuses_unknown_family_by_seed():
    cases = mode.build_balanced_cases(seed=1)
    with pytest.raises(ValueError, match="UNKNOWN_FAMILY_REJECTED"):
        mode.validate_balanced_cases(cases, seed=2)


# --------------------------------------------------------------------------- #
# 2. Short task-only presentation.
# --------------------------------------------------------------------------- #

def test_short_presentation_is_task_only_without_answer_or_guidance():
    records = mode.build_records(mode.build_balanced_cases())
    for record in records:
        problem = record["public"]["problem"]
        assert "BIND" not in problem
        for marker in ("Worked", "Hint", "parcel", "Read the request", "Rule"):
            assert marker not in problem
        # The answer is independently recoverable from the public, never printed.
        assert lesson.recover_binding(record["public"]) == record["target_binding"]
        assert len(problem.split()) <= 40


def test_records_carry_target_separately_never_inside_public():
    records = mode.build_records(mode.build_balanced_cases())
    for record in records:
        assert set(record) == {"family_id", "split", "public", "target_binding"}
        assert "target_binding" not in record["public"]


# --------------------------------------------------------------------------- #
# 3. Optimizer actually called through the identity-checked adapter contract.
# --------------------------------------------------------------------------- #

def test_train_runs_identity_checked_backward_then_step_in_order():
    records = mode.build_records(mode.build_balanced_cases())
    log = []
    learner = make_fake_learner("cas", log)
    receipt = learner.train(records)
    assert receipt["optimizer_steps"] == 1
    assert receipt["state_changed"] is True
    assert receipt["before_checkpoint_sha256"] != receipt["after_checkpoint_sha256"]
    assert log.index("zero_grad") < log.index("cross_entropy") < log.index("backward") < log.index("step")
    assert log.count("zero_grad") == log.count("backward") == log.count("step") == 1


def test_train_identity_check_blocks_step_after_premature_state_change():
    records = mode.build_records(mode.build_balanced_cases())
    log = []
    model = FakeModel(log)

    class MutatingOptimizer(FakeOptimizer):
        def zero_grad(self, set_to_none=True):
            self.log.append("zero_grad")
            self.model._weights[0] += 0.5  # state changes before the optimizer step

    learner = mode.BindingFitLearner(
        FakeTorch(log), model, FakeTokenizer(), MutatingOptimizer(model, log),
        family="cas", run_id="run.cas")
    with pytest.raises(ValueError, match="STATE_CHANGED_BEFORE_STEP"):
        learner.train(records)


# --------------------------------------------------------------------------- #
# 4. Before/after loss and accuracy per family.
# --------------------------------------------------------------------------- #

def test_run_fit_records_before_after_loss_accuracy_and_drives_optimizer():
    records = mode.build_records(mode.build_balanced_cases())
    log = []
    learners = {family: make_fake_learner(family, log) for family in mode.FAMILIES}
    result = mode.run_fit(records, learners)
    assert result["status"] == "TRAINING_FIT_CHECK_COMPLETE"
    steps_per_family = mode.DEFAULT_MAX_OPTIMIZER_STEPS // 2
    for family in mode.FAMILIES:
        fam = result["families"][family]
        assert math.isfinite(fam["before"]["loss"]) and math.isfinite(fam["after"]["loss"])
        assert 0.0 <= fam["before"]["accuracy"] <= 1.0 and 0.0 <= fam["after"]["accuracy"] <= 1.0
        assert fam["before"]["accuracy"] == fam["after"]["accuracy"] == 8 / 24
        assert fam["state_changed"] is True
        assert fam["training_fit"] == "OPTIMIZER_UPDATES_PERFORMED"
        assert fam["optimizer_steps_performed"] == steps_per_family
        assert fam["after"]["optimizer_steps"] == fam["before"]["optimizer_steps"] + steps_per_family
        assert fam["after"]["checkpoint_sha256"] != fam["before"]["checkpoint_sha256"]
    assert result["training_updates_performed"] is True
    assert result["budget"]["optimizer_steps_used"] == mode.DEFAULT_MAX_OPTIMIZER_STEPS
    assert log.count("zero_grad") == log.count("backward") == log.count("step") == mode.DEFAULT_MAX_OPTIMIZER_STEPS


def test_forward_only_measurement_never_reported_as_training_fit():
    records = mode.build_records(mode.build_balanced_cases())
    log = []
    learners = {family: make_fake_learner(family, log, mutate=False) for family in mode.FAMILIES}
    result = mode.run_fit(records, learners)
    for family in mode.FAMILIES:
        fam = result["families"][family]
        assert fam["state_changed"] is False
        assert fam["training_fit"] == "FORWARD_ONLY_NOT_FIT"
    assert result["training_updates_performed"] is False
    assert result["forward_only_never_reported_as_fit"] is True
    assert result["final_targets_read"] is False


# --------------------------------------------------------------------------- #
# 5. Budget refusals and strict bounds.
# --------------------------------------------------------------------------- #

def test_budget_parameters_have_strict_bounds():
    with pytest.raises(ValueError, match="OPTIMIZER_STEP_BUDGET_INVALID"):
        mode.validate_budget(0, 600)
    with pytest.raises(ValueError, match="OPTIMIZER_STEP_BUDGET_INVALID"):
        mode.validate_budget(-1, 600)
    with pytest.raises(ValueError, match="OPTIMIZER_STEP_BUDGET_INVALID"):
        mode.validate_budget(1.5, 600)
    with pytest.raises(ValueError, match="WALL_BUDGET_INVALID"):
        mode.validate_budget(48, 0)
    with pytest.raises(ValueError, match="WALL_BUDGET_INVALID"):
        mode.validate_budget(48, float("nan"))


def test_run_fit_respects_small_optimizer_step_budget():
    records = mode.build_records(mode.build_balanced_cases())
    learners = {family: make_fake_learner(family, []) for family in mode.FAMILIES}
    result = mode.run_fit(records, learners, max_optimizer_steps=1)
    assert result["budget"]["optimizer_steps_used"] == 1
    assert sum(f["optimizer_steps_performed"] for f in result["families"].values()) == 1


def test_run_fit_refuses_when_wall_budget_is_exceeded():
    records = mode.build_records(mode.build_balanced_cases())
    learners = {family: make_fake_learner(family, []) for family in mode.FAMILIES}
    clock = iter([0.0, 601.0])
    with pytest.raises(ValueError, match="WALL_BUDGET_EXCEEDED"):
        mode.run_fit(records, learners, max_wall_seconds=600, wall_clock=lambda: next(clock))


# --------------------------------------------------------------------------- #
# 6. Final-target access refusal and missing-observer refusals.
# --------------------------------------------------------------------------- #

def test_non_train_records_are_refused():
    records = mode.build_records(mode.build_balanced_cases())
    for split in ("test_fresh", "test_context", "test_names", "development"):
        bad = deepcopy(records)
        bad[0]["split"] = split
        with pytest.raises(ValueError, match="NON_TRAIN_RECORD_REJECTED"):
            mode.validate_records(bad)


def test_answer_bearing_record_is_refused():
    records = mode.build_records(mode.build_balanced_cases())
    bad = deepcopy(records)
    bad[0]["public"]["problem"] += " Worked answer: BIND0."
    with pytest.raises(ValueError, match="ANSWER_IN_PRESENTATION"):
        mode.validate_records(bad)


def test_missing_family_learner_is_refused():
    records = mode.build_records(mode.build_balanced_cases())
    with pytest.raises(ValueError, match="LEARNERS_REQUIRED"):
        mode.run_fit(records, {"cas": make_fake_learner("cas", [])})


def test_missing_learner_observer_is_refused():
    records = mode.build_records(mode.build_balanced_cases())

    class NoObserver:
        def evaluate(self, records):
            return {"loss": 0.0, "accuracy": 0.0}

        def train(self, records):
            return {"loss": 0.0}

    learners = {family: make_fake_learner(family, []) for family in mode.FAMILIES}
    learners["cas"] = NoObserver()
    with pytest.raises(ValueError, match="LEARNER_OBSERVER_MISSING"):
        mode.run_fit(records, learners)


def test_learner_requires_model_tokenizer_optimizer_and_state_observer():
    log = []
    with pytest.raises(ValueError, match="MODEL_REQUIRED"):
        mode.BindingFitLearner(FakeTorch(log), None, FakeTokenizer(), FakeOptimizer(FakeModel(log), log),
                               family="cas", run_id="run.cas")
    model = FakeModel(log)
    with pytest.raises(ValueError, match="TOKENIZER_REQUIRED"):
        mode.BindingFitLearner(FakeTorch(log), model, None, FakeOptimizer(model, log),
                               family="cas", run_id="run.cas")
    with pytest.raises(ValueError, match="OPTIMIZER_REQUIRED"):
        mode.BindingFitLearner(FakeTorch(log), model, FakeTokenizer(), None,
                               family="cas", run_id="run.cas")


def test_missing_torch_is_refused_through_import_seam(monkeypatch):
    monkeypatch.setattr(mode, "import_torch", lambda: None)
    log = []
    model = FakeModel(log)
    with pytest.raises(ValueError, match="TORCH_REQUIRED"):
        mode.BindingFitLearner(None, model, FakeTokenizer(), FakeOptimizer(model, log),
                               family="cas", run_id="run.cas")


# --------------------------------------------------------------------------- #
# 7. No real tensor library import at module scope.
# --------------------------------------------------------------------------- #

def test_no_tensor_library_imported_at_module_scope():
    source = Path(mode.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert not {name.name.split(".")[0] for name in node.names} & FORBIDDEN_LIBS
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in FORBIDDEN_LIBS


def test_mode_source_has_no_final_target_paths_or_evaluation_import():
    source = Path(mode.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "evaluation"
    for forbidden in ("test_fresh", "test_context", "test_names", "development"):
        assert forbidden not in source
    assert '["splits"]["train"]' in source


def test_train_method_follows_adapter_step_contract_order():
    source = Path(mode.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BindingFitLearner")
    train = next(node for node in method.body if isinstance(node, ast.FunctionDef) and node.name == "train")
    segment = ast.get_source_segment(source, train)
    assert segment.index("self.optimizer.zero_grad(set_to_none=True)") < segment.index("loss.backward()")
    assert segment.index("NONFINITE_LOSS") < segment.index("loss.backward()")
    assert segment.index("loss.backward()") < segment.index("self.optimizer.step()")
    assert segment.count("self.optimizer.step()") == 1
    assert "STATE_CHANGED_BEFORE_STEP" in segment
    assert "before = self._state_hash()" in segment and "after = self._state_hash()" in segment


def test_no_real_tensor_modules_loaded():
    assert not {"torch", "numpy"}.intersection(sys.modules)
