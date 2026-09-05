from copy import deepcopy
from fractions import Fraction

import pytest

from cas_meta2.codec import action_to_tokens
from cas_meta2.selection_v3 import (depth_generated_metrics, selection_key,
                                  target_loss_weights, target_token_roles, SEMANTIC_ROLES)


def action(depth):
    names = ["main"] + [f"p{i}" for i in range(depth - 1)]
    procedures = {}
    for index, name in enumerate(names):
        step = ({"kind": "CALL", "procedure": names[index + 1]} if index + 1 < len(names)
                else {"kind": "RUN", "cjt_id": "A"})
        procedures[name] = {"input": "arg", "allowed_cjts": ["A"], "steps": [
            {**step, "input": "arg", "output": "v0"}], "return": "v0"}
    return {"binding": 0, "program": {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": procedures}}


def score(successes, *, per_depth=4, epoch=1, loss=.2):
    tasks, outputs = [], []
    for depth, count in enumerate(successes, 1):
        for index in range(per_depth):
            tasks.append({"target": action(depth), "provenance": {"depth": depth}})
            outputs.append(action(depth) if index < count else {"status": "REJECTED"})
    return {"epoch": epoch, "token_cross_entropy": loss, "generation": depth_generated_metrics(outputs, tasks)}


def test_worst_depth_beats_shallow_success_and_lower_loss():
    assert selection_key(score([1, 1, 1], loss=.8)) > selection_key(score([4, 4, 0], loss=.001))


def test_macro_overall_loss_and_early_ties():
    assert selection_key(score([1, 2, 3])) > selection_key(score([1, 1, 3]))
    assert selection_key(score([1, 2, 3], loss=.1)) > selection_key(score([1, 2, 3], loss=.2))
    assert selection_key(score([1, 2, 3], epoch=2)) > selection_key(score([1, 2, 3], epoch=3))
    assert selection_key(score([1, 2, 3]))[:2] == (Fraction(1, 4), Fraction(1, 2))


def test_every_rejection_stays_in_its_depth_denominator():
    metrics = score([0, 0, 0])["generation"]
    assert metrics["overall"]["total"] == 12
    assert all(row["total"] == 4 and row["valid_programs"] == 0 for row in metrics["by_depth"].values())


def test_cannot_improve_selection_by_dropping_hard_depths():
    row = {"epoch": 1, "token_cross_entropy": .1,
           "generation": depth_generated_metrics([action(1)], [{"target": action(1)}], expected_depths=(1,))}
    with pytest.raises(ValueError, match="REGISTERED_DEPTHS_CHANGED"):
        selection_key(row)
    assert selection_key(row, expected_depths=(1,))[0] == 1


@pytest.mark.parametrize("depths", [[], [1, 1], [3, 2, 1], [True], [0], [33], None, "123"])
def test_invalid_registered_depths(depths):
    with pytest.raises(ValueError):
        depth_generated_metrics([action(1)], [{"target": action(1)}], expected_depths=depths)


def test_missing_unregistered_and_forged_depths_rejected():
    with pytest.raises(ValueError, match="MISSING"):
        depth_generated_metrics([action(1)], [{"target": action(1)}])
    with pytest.raises(ValueError, match="UNREGISTERED"):
        depth_generated_metrics([action(2)], [{"target": action(2)}], expected_depths=(1,))
    with pytest.raises(ValueError, match="MISMATCH"):
        depth_generated_metrics([action(1)], [{"target": action(1), "provenance": {"depth": 2}}], expected_depths=(1,))


@pytest.mark.parametrize("loss", [True, None, -1, float("nan"), float("inf"), "0"])
def test_invalid_selection_loss(loss):
    with pytest.raises(ValueError):
        selection_key(score([1, 1, 1], loss=loss))


@pytest.mark.parametrize("epoch", [True, None, 0, -1, 1.5])
def test_no_initial_or_unmeasured_checkpoint_eligible(epoch):
    with pytest.raises(ValueError):
        selection_key(score([1, 1, 1], epoch=epoch))


@pytest.mark.parametrize("mutation", ["missing", "extra", "totals", "native", "negative", "boolean"])
def test_forged_group_receipts_rejected(mutation):
    row = score([1, 1, 1])
    groups = row["generation"]["by_depth"]
    if mutation == "missing": del groups["3"]
    elif mutation == "extra": groups["4"] = deepcopy(groups["1"])
    elif mutation == "totals": groups["1"]["total"] += 1
    elif mutation == "native": groups["1"]["native_execution_performed"] = True
    elif mutation == "negative": groups["1"]["joint_correct"] = -1
    else: groups["1"]["total"] = True
    with pytest.raises(ValueError):
        selection_key(row)


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
def test_training_roles_and_weights_align_exactly_with_codec(depth):
    target = action(depth)
    tokens = action_to_tokens(target)
    roles, weights = target_token_roles(target), target_loss_weights(target)
    assert len(roles) == len(tokens) and len(weights) == len(tokens) - 1
    assert roles[0] == "bos" and roles[-1] == "eos"
    assert weights == tuple(3.0 if role in SEMANTIC_ROLES else 1.0 for role in roles[1:])
    for role, token in zip(roles, tokens):
        if role == "step_kind": assert token in ("RUN", "CALL")
        if role == "run_cjt": assert token == "A"
        if role == "call_target": assert token.startswith("p")
        if role == "return_value": assert token == "v0"


def test_role_order_ignores_serialized_dictionary_order():
    target = action(4)
    reversed_target = deepcopy(target)
    reversed_target["program"]["procedures"] = dict(reversed(list(target["program"]["procedures"].items())))
    assert target_token_roles(target) == target_token_roles(reversed_target)
    assert target_loss_weights(target) == target_loss_weights(reversed_target)


def test_roles_refuse_invalid_action_or_truncation():
    with pytest.raises(ValueError):
        target_token_roles({"status": "REJECTED"})
    with pytest.raises(ValueError):
        target_token_roles(action(4), max_length=16)


def test_metrics_and_roles_do_not_mutate_inputs():
    tasks = [{"target": action(n)} for n in (1, 2, 3)]
    outputs = [task["target"] for task in tasks]
    before = deepcopy((outputs, tasks))
    depth_generated_metrics(outputs, tasks)
    for target in outputs:
        target_loss_weights(target)
    assert (outputs, tasks) == before
