from copy import deepcopy
import pytest

from cas_meta2.selection_v2 import generated_metrics, selection_key


def target():
    return {"binding": 0, "program": {"schema": "cas-meta2-program/0.1", "entry": "main",
            "procedures": {"main": {"input": "arg", "allowed_cjts": ["A"],
              "steps": [{"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"}],
              "return": "v0"}}}}


def score(actions):
    return {"token_cross_entropy": 0.2,
            "generation": generated_metrics(actions, [{"target": target()} for _ in actions])}


def test_generation_keeps_rejections_in_denominator():
    wrong_binding = target()
    wrong_binding["binding"] = 1
    metrics = score([target(), wrong_binding, {"status": "REJECTED"}])["generation"]
    assert metrics["total"] == 3 and metrics["valid_programs"] == 2
    assert metrics["program_correct"] == 2 and metrics["joint_correct"] == 1
    assert metrics["binding_correct"] == 1


def test_correct_generation_beats_lower_teacher_forced_loss():
    good = score([target()])
    bad = score([{"status": "REJECTED"}])
    bad["token_cross_entropy"] = 0.001
    assert selection_key(good) > selection_key(bad)


def test_program_then_binding_then_loss_tie_break():
    program = target()
    program["binding"] = 1
    binding = target()
    binding["program"]["procedures"]["main"]["return"] = "arg"
    assert selection_key(score([program])) > selection_key(score([binding]))
    first = score([target()])
    second = deepcopy(first)
    second["token_cross_entropy"] = 0.3
    assert selection_key(first) > selection_key(second)
    assert selection_key(first) == selection_key(deepcopy(first))


@pytest.mark.parametrize("actions,tasks", [([], []), ([target()], []), ([], [{"target": target()}])])
def test_bad_denominators(actions, tasks):
    with pytest.raises(ValueError):
        generated_metrics(actions, tasks)


@pytest.mark.parametrize("loss", [True, None, -1, float("nan"), float("inf"), "0"])
def test_invalid_loss(loss):
    record = score([target()])
    record["token_cross_entropy"] = loss
    with pytest.raises(ValueError):
        selection_key(record)


@pytest.mark.parametrize("key,value", [("total", True), ("total", 0), ("joint_correct", 2),
    ("valid_programs", 0), ("binding_correct", -1), ("program_correct", 0),
    ("native_execution_performed", True), ("all_cases_in_denominator", False)])
def test_invalid_generation_records(key, value):
    record = score([target()])
    record["generation"][key] = value
    with pytest.raises(ValueError):
        selection_key(record)


def test_teacher_forced_only_not_eligible():
    with pytest.raises(ValueError, match="SELECTION_GENERATION_REQUIRED"):
        selection_key({"token_cross_entropy": 0.1})
