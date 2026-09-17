"""Private loss-contract tests with synthetic scalar scores, never a learner run."""
import builtins
import ast
from copy import deepcopy
from hashlib import sha256
import inspect
import json
import math
from pathlib import Path
import sys
import zipfile

import pytest

from cas_meta2.typed_teaching import checker, course, learner, loss_plan, slots, source

ROOT = Path(__file__).resolve().parents[3]
RECORDS = ROOT / "records/typed_course_001/checks_002"
PINS = {"public_course.json": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
        "private_targets.json": "a02a7d8acef3c88c21ab9d7f6d15ee77377904c464c26af5f6c6306a4a7e5977"}
DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "transformers"}


@pytest.fixture(autouse=True)
def pure_only(monkeypatch):
    original = builtins.__import__
    def guard(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guard)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


@pytest.fixture(scope="module")
def retained():
    values = {}
    for name, pin in PINS.items():
        raw = (RECORDS / name).read_bytes()
        assert sha256(raw).hexdigest() == pin
        values[name] = json.loads(raw)
    return values["public_course.json"], values["private_targets.json"]["targets"]


def synthetic_prediction(packet):
    """Uniform scalar fixture. This is explicitly NOT measured model output."""
    plan = slots.compile_slots(packet)
    scores = {row["slot_id"]: {symbol: 0.0 for symbol in row["symbols"]} for row in plan["slots"]}
    decisions = slots.score_decisions(packet, scores)
    body = {"schema": loss_plan.PREDICTION_SCHEMA, "record_id": plan["record_id"], "packet_digest": plan["packet_digest"],
            "slot_plan_digest": plan["plan_digest"], "depth": 4, "model_revision": 0,
            "run_context_digest": "0" * 64, "encoder_identity_digest": "1" * 64,
            "scores": scores, "decisions": decisions, "answer": slots.assemble_answer(packet, decisions)}
    return {**body, "prediction_id": "typed-prediction-" + source.digest(body)}


def seal(value):
    raw = (source.canonical(value) + "\n").encode()
    return {"sealed_prediction_bytes": raw, "expected_prediction_sha256": sha256(raw).hexdigest()}


@pytest.fixture(scope="module")
def examples(retained):
    public, targets = retained
    selected = {}
    for record in public["registry"]:
        target = targets[record["record_id"]]
        kind = record["query"]["kind"]
        extra = None
        if kind == "correspondence": extra = str(len(target["admissible_answers"]))
        if kind == "role_set": extra = target["admissible_answers"][0]["value"]["status"]
        key = (kind, extra)
        if key in selected: continue
        packet = course.model_packet(public, record["record_id"])
        prediction = synthetic_prediction(packet)
        plan = loss_plan.compile_loss_plan(packet, target, **seal(prediction))
        selected[key] = (packet, target, prediction, plan)
    return selected


def one(examples, kind, extra=None):
    if extra is not None: return examples[kind, extra]
    return next(value for (k, _), value in examples.items() if k == kind)


def test_all_eight_answer_kinds_have_checked_private_plans(examples, retained):
    assert {key[0] for key in examples} == set(course.REQUESTS)
    public, targets = retained
    assert len(public["registry"]) == len(targets) == 564
    assert len(public["presentations"]) == 1152 and len(public["batches"]) == 160
    for packet, target, prediction, plan in examples.values():
        assert plan["target_digest"] == target["target_digest"]
        assert plan["prediction_sha256"] == seal(prediction)["expected_prediction_sha256"]
        assert plan["packet_digest"] == source.digest(packet)
        assert plan["policy"]["training"] == "RAW_FIELD_MEAN_THEN_TASK_MEAN_THEN_BATCH_MEAN"


@pytest.mark.parametrize("kind", tuple(course.REQUESTS))
def test_scalar_reports_are_finite_and_use_raw_training_loss(examples, kind):
    packet, _, prediction, plan = one(examples, kind)
    report = loss_plan.scalar_report(packet, plan, prediction["scores"])
    assert math.isfinite(report["raw_task_loss"]) and report["raw_task_loss"] >= 0
    assert report["training_uses"] == "raw_task_loss" and report["numeric_model_executed"] is False
    assert report["raw_task_loss"] == sum(r["raw_loss"] for r in report["fields"]) / len(report["fields"])
    assert report["normalized_task_loss"] == sum(r["normalized_loss"] for r in report["fields"]) / len(report["fields"])


def test_role_ambiguity_is_exact_six_bit_field_not_singleton_alternatives(examples):
    packet, target, prediction, plan = one(examples, "role_set", "AMBIGUOUS")
    assert target["admissible_answers"][0]["value"] == {"roles": [5, 6], "status": "AMBIGUOUS"}
    assert len(plan["fields"]) == 1
    field = plan["fields"][0]
    assert field["kind"] == "membership" and len(field["slot_ids"]) == 6
    assert sum(symbols == ["PRESENT"] for symbols in field["targets"].values()) == 2
    assert all(len(symbols) == 1 for symbols in field["targets"].values())
    assert math.isclose(loss_plan.scalar_report(packet, plan, prediction["scores"])["raw_task_loss"], math.log(2), abs_tol=1e-12)


@pytest.mark.parametrize("count", ["1", "2", "6"])
def test_correspondence_uses_whole_valid_map_set_and_hierarchical_probability(examples, count):
    packet, target, prediction, plan = one(examples, "correspondence", count)
    assert len(plan["fields"]) == 1
    field = plan["fields"][0]
    assert field["kind"] == "joint_correspondence" and field["targets"] == {}
    assert len(field["valid_candidate_ids"]) == int(count)
    assert all(len(answer["value"]["pairs"]) in (3, 4) for answer in target["admissible_answers"])
    expected = math.log(2) + math.log(field["public_alphabet_size"] - 1) - math.log(int(count))
    actual = loss_plan.scalar_report(packet, plan, prediction["scores"])
    assert math.isclose(actual["raw_task_loss"], expected, abs_tol=1e-12)
    assert math.isclose(actual["normalized_task_loss"], expected / math.log(field["public_alphabet_size"]), abs_tol=1e-12)


def test_analogy_uses_all_valid_worlds_inside_full_public_alphabet(examples):
    packet, target, prediction, plan = one(examples, "analogy")
    field = plan["fields"][0]
    assert field["public_alphabet_size"] == 65
    assert len(next(iter(field["targets"].values()))) == len(target["admissible_answers"])
    expected = math.log(65) - math.log(len(target["admissible_answers"]))
    assert math.isclose(loss_plan.scalar_report(packet, plan, prediction["scores"])["raw_task_loss"], expected, abs_tol=1e-12)


def test_membership_averages_all_public_slots_and_context_then_averages_fields(examples):
    for kind in ("parts", "edge_account"):
        packet, _, prediction, plan = one(examples, kind)
        field = plan["fields"][0]
        assert len(field["targets"]) == len(slots.compile_slots(packet)["slots"])
        assert math.isclose(loss_plan.scalar_report(packet, plan, prediction["scores"])["raw_task_loss"], math.log(2), abs_tol=1e-12)
    packet, _, prediction, plan = one(examples, "context")
    report = loss_plan.scalar_report(packet, plan, prediction["scores"])
    assert len(report["fields"]) == 2
    assert math.isclose(report["raw_task_loss"], (math.log(64) + math.log(2)) / 2, abs_tol=1e-12)
    assert math.isclose(report["normalized_task_loss"], 1.0, abs_tol=1e-12)


def test_wrong_seal_is_refused_before_any_checker_target_access(examples, monkeypatch):
    packet, _, prediction, _ = one(examples, "parts")
    calls = []
    def forbidden(*args, **kwargs): calls.append(True); raise AssertionError("TARGET_OPENED_EARLY")
    monkeypatch.setattr(checker, "validate_target", forbidden)
    with pytest.raises(ValueError, match="SEAL_BYTES"):
        loss_plan.compile_loss_plan(packet, object(), sealed_prediction_bytes=seal(prediction)["sealed_prediction_bytes"], expected_prediction_sha256="f" * 64)
    assert calls == []


@pytest.mark.parametrize("field", ["correct", "target", "source_event"])
def test_private_extra_in_prediction_refused_before_checker(examples, monkeypatch, field):
    packet, _, prediction, _ = one(examples, "parts")
    prediction = deepcopy(prediction); prediction[field] = 1
    def forbidden(*args, **kwargs): raise AssertionError("TARGET_OPENED_EARLY")
    monkeypatch.setattr(checker, "validate_target", forbidden)
    with pytest.raises(ValueError, match="PREDICTION_FIELDS"): loss_plan.compile_loss_plan(packet, object(), **seal(prediction))


@pytest.mark.parametrize("mutation", ["bool_depth", "float_revision", "wrong_packet", "wrong_answer", "wrong_decisions", "stale_prediction_id"])
def test_prediction_binding_cannot_be_resealed_around_false_public_join(examples, mutation):
    packet, target, prediction, _ = one(examples, "parts")
    prediction = deepcopy(prediction)
    if mutation == "bool_depth": prediction["depth"] = True
    elif mutation == "float_revision": prediction["model_revision"] = 0.0
    elif mutation == "wrong_packet": prediction["packet_digest"] = "0" * 64
    elif mutation == "wrong_answer": prediction["answer"]["value"]["nodes"] = [packet["record"]["query"]["arguments"]["whole"]]
    elif mutation == "wrong_decisions": prediction["decisions"]["selected"][next(iter(prediction["decisions"]["selected"]))] = "PRESENT"
    else: prediction["prediction_id"] += "x"
    if mutation != "stale_prediction_id": prediction["prediction_id"] = "typed-prediction-" + source.digest({k: v for k, v in prediction.items() if k != "prediction_id"})
    with pytest.raises(ValueError): loss_plan.compile_loss_plan(packet, target, **seal(prediction))


def test_noncanonical_seal_and_duplicate_json_keys_are_refused(examples):
    packet, target, prediction, _ = one(examples, "parts")
    for raw in (json.dumps(prediction, indent=2).encode(), (source.canonical(prediction)[:-1] + ',"depth":4}\n').encode()):
        with pytest.raises(ValueError, match="NONCANONICAL"):
            loss_plan.compile_loss_plan(packet, target, sealed_prediction_bytes=raw, expected_prediction_sha256=sha256(raw).hexdigest())


def test_foreign_or_resealed_incomplete_target_is_independently_refused(examples):
    packet, target, prediction, _ = one(examples, "correspondence", "6")
    forged = deepcopy(target); forged["admissible_answers"].pop(); forged["witnesses"].pop()
    forged["target_digest"] = source.digest({k: v for k, v in forged.items() if k != "target_digest"})
    with pytest.raises(ValueError, match="TARGET_BINDING"): loss_plan.compile_loss_plan(packet, forged, **seal(prediction))
    with pytest.raises(ValueError, match="TARGET_BINDING"): loss_plan.compile_loss_plan(packet, one(examples, "parts")[1], **seal(prediction))


def test_resealed_loss_plan_cannot_change_targets_or_training_normalization(examples):
    packet, target, prediction, plan = one(examples, "parts")
    for mutation in ("targets", "policy"):
        changed = deepcopy(plan)
        if mutation == "targets": changed["fields"][0]["targets"][next(iter(changed["fields"][0]["targets"]))] = ["PRESENT", "ABSENT"]
        else: changed["policy"]["training"] = "NORMALIZED"
        changed["loss_plan_digest"] = source.digest({k: v for k, v in changed.items() if k != "loss_plan_digest"})
        with pytest.raises(ValueError, match="RECONSTRUCTION"): loss_plan.validate_loss_plan(packet, target, changed, **seal(prediction))


def test_loss_plan_and_sealed_input_are_not_mutated(examples):
    packet, target, prediction, plan = one(examples, "parts")
    before = source.canonical([packet, target, prediction, plan])
    rebuilt = loss_plan.validate_loss_plan(packet, target, plan, **seal(prediction))
    rebuilt["fields"].clear()
    assert source.canonical([packet, target, prediction, plan]) == before


def test_worker_import_is_inert_and_predict_signature_has_no_private_argument():
    assert list(inspect.signature(learner.TypedCourseLearner.predict).parameters) == ["self", "packet", "depth"]
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)
    assert learner.profile()["status"] == "WORKER_IMPLEMENTATION_NUMERIC_ACCEPTANCE_PENDING"


def test_registered_parameter_shapes_match_pinned_wheel_source_without_import():
    path = ROOT / "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/cas_neural_cjt-0.2.0-py3-none-any.whl"
    assert sha256(path.read_bytes()).hexdigest() == "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9"
    with zipfile.ZipFile(path) as archive: raw = archive.read("cas_cjt/neural.py")
    assert sha256(raw).hexdigest() == "03521d2b17311680fd91cde7076e4bf5b38393f0d6db115d47be20f63413fc96"
    cls = next(n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == "_DecomposeTransform")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    def dimension(node):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "config" and node.attr == "d_model": return 64
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult) and isinstance(node.left, ast.Constant) and type(node.left.value) is int:
            return node.left.value * dimension(node.right)
        raise AssertionError("UNKNOWN_PINNED_LINEAR_DIMENSION")
    shapes = {}
    for node in init.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "_linear":
            assert len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute)
            shapes[node.targets[0].attr + ".weight"] = (dimension(node.value.args[2]), dimension(node.value.args[1]))
    assert learner.PARAMETER_SHAPES == shapes
    assert tuple(sorted(shapes)) == learner.PARAMETERS
