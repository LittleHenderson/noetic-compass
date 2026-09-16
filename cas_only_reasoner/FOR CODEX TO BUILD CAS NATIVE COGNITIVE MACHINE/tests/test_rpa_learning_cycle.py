"""Pure control tests: these doubles perform no tensor or neural execution."""
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "research/CAS_META_2_COMPOSITION"
if str(PILOT) not in sys.path:
    sys.path.insert(0, str(PILOT))

from cncm import rpa_cube_adapter as bridge
from cncm import rpa_learning_adapter as adapter
from cncm import rpa_learning_cycle as cycle
from cncm.canonical import canonical_json, digest
from cncm.model import ContractError
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.graph_teaching import ordered_encoder, trainer


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "requests", "cas_cjt"}:
            raise AssertionError("PROHIBITED_EXECUTION_IMPORT:" + fullname)


@pytest.fixture(autouse=True)
def deny_execution():
    guard = Deny()
    sys.meta_path.insert(0, guard)
    yield
    sys.meta_path.remove(guard)


@pytest.fixture
def sample():
    bundle = bridge.cube_node.load_bundle()
    raw = canonical_json(bundle).encode()
    receipt = bridge.cube_source_receipt(
        raw, expected_file_sha256=sha256(raw).hexdigest(),
        expected_bundle_digest=bridge.cube_node.bundle_digest(bundle),
        source_namespace="cycle_test_fixture", observation_id="cycle_test",
        observation_time="supplied test fixture", record_version=1)
    document = bridge.cube_atlas_from_bundle(
        bundle, expected_bundle_digest=receipt.canonical_bundle_digest,
        source_receipt=receipt, view_id="view_context")
    case = bridge.cube_node.answer_cases(bundle, "view_context")["cases"][0]
    prepared = adapter.prepare_public_lesson(
        document, operation=case["op"], question=case["question"])
    tokenizer = LosslessPublicTokenizer.fit_train([prepared["public"]], max_length=1024)
    profile = ordered_encoder.profile_identity(
        tokenizer, d_model=64, seed=13, projection_sha256="1" * 64)
    context = {"model_id": "EXPLICIT_TEST_DOUBLE", "checkpoint_sha256": "2" * 64}
    args = {"document": document, "tokenizer": tokenizer,
            "ordered_profile": profile, "model_context": context}
    lesson = adapter.bind_prepared_lesson(prepared, **args)
    public_args = {key: value for key, value in args.items() if key != "document"}
    packet = adapter.prediction_packet(lesson, **public_args)
    target = adapter.check_source_target(lesson, **args)
    return SimpleNamespace(args=args, public_args=public_args, lesson=lesson,
                           packet=packet, target=target)


class Param:
    def __init__(self):
        self.value = 0
        self.requires_grad = False

    def requires_grad_(self, flag):
        self.requires_grad = flag


class Module:
    def __init__(self):
        self.allowed, self.frozen = Param(), Param()

    def named_parameters(self):
        return [("allowed", self.allowed), ("frozen", self.frozen)]


class Framework:
    def __init__(self):
        self.module = Module()
        self.operation_registrations = [SimpleNamespace(contract_id=trainer.TARGET_CONTRACT_ID)]

    def contract_for(self, contract_id):
        assert contract_id == trainer.TARGET_CONTRACT_ID
        return SimpleNamespace(plasticity_groups=[trainer.TARGET_PLASTICITY_ROLE])

    def resolve_plasticity_groups(self, model, role, contract):
        return ("allowed",)

    def tensor_bytes(self, parameter):
        return str(parameter.value).encode("ascii")


class Learner:
    def __init__(self, sample):
        self.tasks = [{**deepcopy(sample.packet),
                       "encoded_correct_index": sample.target["encoded_correct_index"]}]
        self._index = {sample.packet["record_id"]: 0}
        self.framework = Framework()
        self.module = self.framework.module
        self.steps = []
        self.predictions = 0

    def predict(self, packet):
        assert set(packet) == {"record_id", "public", "encoded_options"}
        self.predictions += 1
        return deepcopy(packet["encoded_options"][0])

    def eval_loss(self, op, tasks):
        return {"total": 1.0}

    def step(self, task):
        self.steps.append(deepcopy(task))
        self.module.allowed.value += 1
        return 1.0

    def checkpoint_identity(self):
        return sha256(str(self.module.allowed.value).encode()).hexdigest()


def setup(sample):
    learner = Learner(sample)
    predictor = cycle.PublicPredictor(
        learner, training_packets=[sample.packet], **sample.public_args)
    candidate = {**sample.args, "lessons": [sample.lesson], "learner": learner,
                 "framework": learner.framework, "predictor": predictor,
                 "scope": trainer.scope_parameters(learner.framework, learner.module)}
    return learner, predictor, candidate


def target_map(sample):
    return {sample.packet["record_id"]: {
        "public_input_digest": digest(sample.packet),
        "encoded_correct_index": sample.target["encoded_correct_index"],
        "expected_answer": deepcopy(sample.target["expected_answer"]),
        "operation": sample.lesson["provenance"]["request"]["operation"]}}


def test_training_injects_new_records_and_preserves_scope(sample, monkeypatch):
    learner, predictor, candidate = setup(sample)
    monkeypatch.setattr(trainer, "training_records",
                        lambda *a, **kw: pytest.fail("legacy dataset must not be selected"))
    report = cycle.run_bound_training(candidate, wall_clock=lambda: 0.0)
    assert report["training"]["completed_updates"] == 64
    assert len(learner.steps) == 64
    assert {row["record_id"] for row in learner.steps} == {sample.packet["record_id"]}
    assert all(row["correct"] == sample.target["expected_answer"] for row in learner.steps)
    assert report["containment"]["permitted_changes"] == ["allowed"]
    assert learner.module.frozen.value == 0
    assert "test doubles" in report["boundary"]


def test_prediction_seals_before_private_loader(sample, tmp_path):
    learner, predictor, candidate = setup(sample)
    path = tmp_path / "predictions.json"
    seal = cycle.seal_predictions(predictor, [sample.packet], path=path)
    calls = []
    def loader():
        assert path.is_file()
        assert learner.predictions == 1
        assert sha256(path.read_bytes()).hexdigest() == seal["sha256"]
        calls.append("private opened")
        return target_map(sample)
    result = cycle.score_sealed_predictions(seal, targets_loader=loader)
    assert calls == ["private opened"]
    assert result["total"] == 1
    assert result["prediction_seal_sha256"] == seal["sha256"]
    assert "encoded_correct_index" not in path.read_text()
    assert "expected_answer" not in path.read_text()
    assert "UNAVAILABLE" in json.loads(path.read_bytes())["scores"]


def test_tampered_seal_never_opens_targets(sample, tmp_path):
    _, predictor, _ = setup(sample)
    path = tmp_path / "predictions.json"
    seal = cycle.seal_predictions(predictor, [sample.packet], path=path)
    path.write_bytes(path.read_bytes().replace(b'"selected_index":0', b'"selected_index":1'))
    with pytest.raises(ContractError, match="DIGEST"):
        cycle.score_sealed_predictions(seal, targets_loader=lambda: pytest.fail("private opened"))


def test_existing_seal_is_not_overwritten(sample, tmp_path):
    _, predictor, _ = setup(sample)
    path = tmp_path / "predictions.json"
    path.write_bytes(b"preserve earlier result")
    with pytest.raises(FileExistsError):
        cycle.seal_predictions(predictor, [sample.packet], path=path)
    assert path.read_bytes() == b"preserve earlier result"


def test_duplicate_panel_refused_before_predict(sample, tmp_path):
    learner, predictor, _ = setup(sample)
    with pytest.raises(ContractError, match="DUPLICATE"):
        cycle.seal_predictions(predictor, [sample.packet, sample.packet],
                               path=tmp_path / "predictions.json")
    assert learner.predictions == 0


def test_private_target_cannot_change_sealed_input(sample, tmp_path):
    _, predictor, _ = setup(sample)
    seal = cycle.seal_predictions(predictor, [sample.packet], path=tmp_path / "predictions.json")
    old_bytes = Path(seal["path"]).read_bytes()
    targets = target_map(sample)
    index = (sample.target["encoded_correct_index"] + 1) % 3
    targets[sample.packet["record_id"]].update(
        encoded_correct_index=index, expected_answer=sample.packet["encoded_options"][index])
    result = cycle.score_sealed_predictions(seal, targets_loader=lambda: targets)
    assert result["rows"][0]["correct_index"] == index
    assert Path(seal["path"]).read_bytes() == old_bytes
    # Deliberately swapped private scoring is not source verification.


def test_scoring_refuses_wrong_public_binding(sample, tmp_path):
    _, predictor, _ = setup(sample)
    seal = cycle.seal_predictions(predictor, [sample.packet], path=tmp_path / "predictions.json")
    targets = target_map(sample)
    targets[sample.packet["record_id"]]["public_input_digest"] = "0" * 64
    with pytest.raises(ContractError, match="BINDING"):
        cycle.score_sealed_predictions(seal, targets_loader=lambda: targets)


def test_worker_refuses_cpu_before_numeric_construction(sample, tmp_path):
    runtime = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    with pytest.raises(ContractError, match="CUDA_REQUIRED"):
        cycle.create_worker_candidate(runtime, "cpu", document=sample.args["document"],
                                      requests=[], seed=1,
                                      initial_checkpoint_path=tmp_path / "initial.pt")
    assert not (tmp_path / "initial.pt").exists()


def test_worker_requires_existing_explicit_enable_before_output(sample, tmp_path, monkeypatch):
    from cas_meta2.teaching_cycle import gpu_adapter
    monkeypatch.setattr(gpu_adapter.platform, "system", lambda: "Linux")
    monkeypatch.delenv("CAS_META2_RUN_TEACHING_CYCLE", raising=False)
    runtime = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True))
    output = tmp_path / "must_not_exist"
    with pytest.raises(ValueError, match="EXPLICIT_ENABLE_REQUIRED"):
        cycle.run_worker_smoke(runtime, "cuda:0", document=sample.args["document"],
                               training_requests=[], prediction_requests=[], seed=1, output=output)
    assert not output.exists()
