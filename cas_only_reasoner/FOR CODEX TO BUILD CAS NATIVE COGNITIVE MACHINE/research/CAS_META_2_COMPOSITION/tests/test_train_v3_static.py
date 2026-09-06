"""Pure source/contract checks. Never import the CUDA trainer or construct tensors."""
import ast
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from types import SimpleNamespace
import sys
import time
import traceback

import pytest

from cas_meta2.ir import validate_program

ROOT = Path(__file__).parents[1]
PATH = ROOT / "cas_meta2" / "train_v3.py"
TEXT = PATH.read_text(encoding="utf-8")
TREE = ast.parse(TEXT)


def segment(name):
    return ast.get_source_segment(TEXT, next(node for node in TREE.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name))


def load_pure(names, **namespace):
    nodes = [node for node in TREE.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
             and node.name in names]
    assert {node.name for node in nodes} == set(names)
    env = {"validate_program": validate_program, "RuntimeError": RuntimeError,
           "Path": Path, "math": math, **namespace}
    exec(compile(ast.Module(body=deepcopy(nodes), type_ignores=[]), str(PATH), "exec"), env)
    return env


def task(depth, index=0):
    names = ["main", "p0", "p1"][:depth]
    procedures = {}
    for i, name in enumerate(names):
        steps = [{"kind": "RUN", "cjt_id": "ABC"[i], "input": "arg", "output": "v0"}]
        if i + 1 < depth:
            steps.append({"kind": "CALL", "procedure": names[i + 1], "input": "v0", "output": "v1"})
        procedures[name] = {"input": "arg", "allowed_cjts": ["A", "B", "C"],
                            "steps": steps, "return": "v1" if i + 1 < depth else "v0"}
    return {"task_id": f"pure-{depth}-{index}", "target": {"binding": 0,
            "program": {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": procedures}}}


def test_frozen_trainer_unchanged():
    assert sha256((ROOT / "cas_meta2" / "train_v2.py").read_bytes()).hexdigest() == "882976ac24fb808c2da8ab5e1a5f80388946693077e7dfdfd7a00d4e029c0665"


def test_actual_policy_and_loss_imports_not_old_trainer():
    modules = {node.module for node in ast.walk(TREE) if isinstance(node, ast.ImportFrom)}
    assert {"policy_v3", "selection_v3", "loss_v3", "curriculum_v3"} <= modules
    assert not {"policy", "selection_v2", "train_v2"} & modules
    impl = segment("_train_and_seal_impl")
    assert "weighted_training_loss(logits, target, weights)" in impl
    assert "encode_loss_weights(" in impl
    assert "F.cross_entropy" not in impl
    assert "F.nll_loss(" in segment("_validation_loss")


def test_private_gold_never_parsed_in_training():
    parsed = []
    for node in ast.walk(TREE):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "read_json":
            parsed.append(ast.unparse(node.args[0]))
    assert set(parsed) == {"data / 'dataset_manifest.json'", "data / 'train.json'",
                           "data / 'validation.json'", "data / 'test_public.json'"}
    assert '"test_private_labels_loaded": False' in TEXT


def test_registered_exclusions_seed_and_counts_reach_manifest_validation():
    impl = segment("_train_and_seal_impl")
    assert "expected_seed=config.curriculum_seed" in impl
    assert "excluded_graph_signatures=registered_development_exclusions()" in impl
    assert '"train": config.training_examples_per_depth * 3' in impl
    assert '"validation": config.validation_examples_per_depth * 3' in impl
    assert '"test": config.test_triplets * 3' in impl


def test_all_neural_arms_use_same_loader_and_prediction_path():
    impl = segment("_train_and_seal_impl")
    assert 'for arm in ARMS:' in impl
    assert 'family = "cas" if arm.startswith("cas") else "generic"' in impl
    assert 'state = "initial" if arm.endswith("untrained") else "selected"' in impl
    assert '_load_checkpoint(models[family], checkpoints[family][state], tokenizer, device, config, family)' in impl
    assert "predict_public(" in segment("_predict_chunks")
    assert "parse_problem" not in segment("_predict_chunks")


def test_train_probe_not_used_for_selection():
    impl = segment("_train_and_seal_impl")
    assert 'key=lambda row: row["task_id"]' in impl
    assert '"used_for_checkpoint_selection": False' in impl
    assert 'selection_key(validation) > selection_key(best["validation"])' in impl
    assert "selection_key(probe" not in impl
    assert "selection_key(initial" not in impl
    assert 'validation["epoch"] = epoch' in impl


def test_validation_denominators_are_fixed():
    fn = load_pure(["_require_validation_counts"])["_require_validation_counts"]
    fn({"overall": {"total": 96}, "by_depth": {str(d): {"total": 32} for d in (1, 2, 3)}}, 32)
    with pytest.raises(RuntimeError, match="FIXED_VALIDATION_DENOMINATOR"):
        fn({"overall": {"total": 96}, "by_depth": {"1": {"total": 31}, "2": {"total": 33}, "3": {"total": 32}}}, 32)


def test_actual_target_depth_not_untrusted_metadata():
    fn = load_pure(["_require_depth_counts"])["_require_depth_counts"]
    rows = [task(depth, i) for depth in (1, 2, 3) for i in range(2)]
    for row in rows:
        row["provenance"] = {"depth": 99}
    assert {depth: len(items) for depth, items in fn(rows, 2, "train").items()} == {1: 2, 2: 2, 3: 2}
    with pytest.raises(RuntimeError, match="DENOMINATOR"):
        fn(rows[:-1], 2, "train")


def test_training_deadline_reaches_batches_and_validation():
    impl = segment("_train_and_seal_impl")
    start = impl.index('    try:\n        for family, model in models.items():')
    end = impl.index('    training_record = {', start)
    training = impl[start:end]
    assert "require_time(deadline)" not in training
    assert "config, device, deadline)" not in training
    assert training.index("require_time(training_deadline)", training.index("for offset in range")) < training.index("for family, model in models.items():", training.index("for offset in range"))
    assert "longest_epoch_seconds = max(longest_epoch_seconds, epoch_seconds)" in training
    assert "reserve = max(10.0, longest_epoch_seconds * 1.25)" in training


def test_prediction_reserve_constant_matches_registered_spec_without_neural_import():
    assignment = next(node for node in TREE.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PREDICTION_RESERVE_SECONDS" for target in node.targets))
    reserve = ast.literal_eval(assignment.value)
    spec = json.loads((ROOT / "EXPERIMENT_V3.json").read_text())
    assert type(reserve) is int and reserve == spec["execution"]["phase_seconds"]["prediction_seal"] == 480
    impl = next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "_train_and_seal_impl")
    deadline = next(node.value for node in ast.walk(impl) if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "training_deadline" for target in node.targets))
    assert ast.unparse(deadline) == "min(deadline - PREDICTION_RESERVE_SECONDS, training_started + config.max_training_seconds)"


@pytest.mark.parametrize("setup_seconds", [0, 1, 120, 360, 479, 1000, 2700])
def test_actual_training_deadline_preserves_prediction_reserve_after_setup(setup_seconds):
    # Evaluate only the actual arithmetic AST, never the tensor-owning trainer.
    impl = next(node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name == "_train_and_seal_impl")
    expression = next(node.value for node in ast.walk(impl) if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "training_deadline" for target in node.targets))
    reserve_node = next(node.value for node in TREE.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PREDICTION_RESERVE_SECONDS" for target in node.targets))
    spec = json.loads((ROOT / "EXPERIMENT_V3.json").read_text())
    maximum = spec["training"]["max_training_seconds"]
    learning_start = 100.0
    deadline = learning_start + maximum + spec["execution"]["phase_seconds"]["prediction_seal"]
    training_started = learning_start + setup_seconds
    result = eval(compile(ast.Expression(body=deepcopy(expression)), str(PATH), "eval"),
        {"min": min, "deadline": deadline, "training_started": training_started,
         "PREDICTION_RESERVE_SECONDS": ast.literal_eval(reserve_node),
         "config": SimpleNamespace(max_training_seconds=maximum)})
    assert deadline - result >= 480
    assert result <= training_started + maximum
    assert result == learning_start + maximum
    if setup_seconds == maximum:
        assert result == training_started  # No training time remains; next guard must fail.


def test_checkpoint_version_and_cuda_loading_are_distinct():
    assert "cas-meta2-candidate-checkpoint/2" not in TEXT
    assert "cas-meta2-candidate-checkpoint/3" in TEXT
    assert "map_location=device, weights_only=True" in segment("_load_checkpoint")
    assert 'model.load_state_dict(payload["state_dict"], strict=True)' in segment("_load_checkpoint")
    assert '.cpu(' not in TEXT and 'device="cpu"' not in TEXT


@dataclass(frozen=True)
class FakePolicyConfig:
    max_length: int = 1024
    max_action_length: int = 256

    def validate(self):
        pass


def config_class():
    return load_pure(["TrainingConfig"], dataclass=dataclass, field=field,
                     PolicyConfig=FakePolicyConfig)["TrainingConfig"]


def test_registered_config_defaults():
    config = config_class()()
    config.validate()
    assert (config.curriculum_seed, config.training_examples_per_depth,
            config.validation_examples_per_depth, config.test_triplets) == (20260919, 1024, 32, 24)


@pytest.mark.parametrize("kwargs", [{"curriculum_seed": True}, {"training_examples_per_depth": 0},
    {"validation_examples_per_depth": 0}, {"test_triplets": 0}, {"train_probe_examples_per_depth": 1025},
    {"max_training_seconds": 0}, {"validation_generation_interval": 0}])
def test_invalid_config(kwargs):
    with pytest.raises(ValueError):
        config_class()(**kwargs).validate()


def checkpoint_fixture():
    config = config_class()()
    payload = {"schema": "cas-meta2-candidate-checkpoint/3", "family": "cas", "epoch": 5,
        "optimizer_steps": 960, "validation": {"example": 1}, "config": asdict(config),
        "policy_source_sha256": {"source": "a"}, "tokenizer_digest": "tokenizer",
        "action_vocabulary": ["example"], "state_dict": {"mock": "no tensor"}}
    record = {key: payload[key] for key in ("schema", "family", "epoch", "optimizer_steps", "validation", "policy_source_sha256")}
    record.update(path="mock-checkpoint", sha256="checkpoint")
    events = []
    def fake_load(path, **kwargs):
        events.append((path, kwargs))
        return payload
    model = SimpleNamespace(load_state_dict=lambda state, strict: events.append((state, strict)),
                            parameters=lambda: [SimpleNamespace(device=SimpleNamespace(type="cuda"))])
    env = load_pure(["_load_checkpoint"], require_cuda=lambda device: device,
        file_hash=lambda path: "checkpoint", torch=SimpleNamespace(load=fake_load),
        asdict=asdict, ACTION_VOCABULARY=["example"], policy_source_identity=lambda: {"source": "a"})
    return env["_load_checkpoint"], model, record, payload, config, events


def test_checkpoint_strict_reload_metadata_only_mock():
    fn, model, record, payload, config, events = checkpoint_fixture()
    fn(model, record, SimpleNamespace(digest="tokenizer"), "cuda", config, "cas")
    assert events == [("mock-checkpoint", {"map_location": "cuda", "weights_only": True}),
                      ({"mock": "no tensor"}, True)]


@pytest.mark.parametrize("field,value", [("schema", "cas-meta2-candidate-checkpoint/2"),
    ("family", "generic"), ("epoch", 99), ("optimizer_steps", 0), ("validation", None),
    ("config", {}), ("policy_source_sha256", {}), ("tokenizer_digest", "wrong")])
def test_changed_checkpoint_identity_rejected(field, value):
    fn, model, record, payload, config, events = checkpoint_fixture()
    payload[field] = value
    with pytest.raises(RuntimeError):
        fn(model, record, SimpleNamespace(digest="tokenizer"), "cuda", config, "cas")
    assert len(events) == 1


def test_cleanup_outside_tensor_owning_frame_and_exception_suite():
    text = segment("train_and_seal")
    assert text.index('result = _train_and_seal_impl(') < text.index('"after_training_frame_exit"')
    assert "torch.cuda.empty_cache()" not in segment("_train_and_seal_impl")
    node = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == "train_and_seal")
    first_try = next(n for n in node.body if isinstance(n, ast.Try))
    assert all("_cleanup" not in ast.unparse(handler) for handler in first_try.handlers)
    assert '"traceback": traceback.format_exc()' in text
    assert 'if not record["completed"]:' in text
    assert 'TRAINING_CUDA_MEMORY_NOT_RELEASED' in text


def test_checkpoint_sources_cover_copier_grammar_loss_and_data_identity():
    assignment = next(node for node in TREE.body if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "POLICY_SOURCE_FILES" for t in node.targets))
    assert {"policy_v3.py", "features_v3.py", "grammar_v3.py", "selection_v3.py", "loss_v3.py",
            "curriculum_v3.py", "development_exclusions_v3.json", "exclusions_v3.json"} <= set(ast.literal_eval(assignment.value))


@pytest.mark.parametrize("training_error,residual", [(False, 0), (True, 0), (False, 1)])
def test_cleanup_receipt_cannot_promote_failure(monkeypatch, tmp_path, training_error, residual):
    import cas_meta2.gpu_preflight_v3 as cleanup
    events, saved = [], []
    def checked_runtime(torch, receipt):
        receipt["numerical_settings_before"] = {"fixed": True}
    def fake_cleanup(torch, device, receipt, phase):
        events.append(phase)
        return {"allocated_bytes": residual if phase == "after_training_frame_exit" else 0,
                "reserved_bytes": 0}
    def implementation(*args):
        events.append("inner_training")
        if training_error:
            raise ValueError("saved mock failure")
        return {"primitive_result": True}
    monkeypatch.setattr(cleanup, "_checked_runtime", checked_runtime)
    monkeypatch.setattr(cleanup, "_cleanup", fake_cleanup)
    monkeypatch.setattr(cleanup, "_settings", lambda torch: {"fixed": True})
    env = load_pure(["train_and_seal"], __package__="cas_meta2", torch=SimpleNamespace(),
        setup_cuda=lambda seed: (None, "cuda"), require_time=lambda deadline: None,
        _train_and_seal_impl=implementation, datetime=datetime, timezone=timezone,
        traceback=traceback, json=json, write_json=lambda path, value: saved.append(deepcopy(value)))
    fn = env["train_and_seal"]
    if training_error or residual:
        with pytest.raises(RuntimeError, match="TRAINING_CLEANUP_BLOCKED"):
            fn("mock-data", tmp_path, config_class()(), 100)
        assert saved[0]["completed"] is False and saved[0]["failures"]
    else:
        assert fn("mock-data", tmp_path, config_class()(), 100) == {"primitive_result": True}
        assert saved[0]["completed"] is True and saved[0]["failures"] == []
    assert events == ["before_training", "inner_training", "after_training_frame_exit"]
    assert all(not isinstance(value, BaseException) for failure in saved[0]["failures"] for value in failure.values())
