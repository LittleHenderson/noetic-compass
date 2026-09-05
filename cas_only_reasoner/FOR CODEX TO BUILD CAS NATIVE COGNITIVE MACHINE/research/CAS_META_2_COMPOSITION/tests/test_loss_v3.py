"""Pure construction/alignment checks. No neural or provider imports."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from cas_meta2.codec import PAD_ID, PolicyContractError, action_to_ids
from cas_meta2.loss_v3 import LOSS_CONTRACT, encode_loss_weights, loss_weight_rows, weighted_training_loss


def action(steps=1):
    return {"binding": 0, "program": {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v" + str(index)} for index in range(steps)],
            "return": "v" + str(steps - 1)}}}}


def test_simple_weight_alignment_matches_independent_fixed_role_list():
    actual = loss_weight_rows([action()])
    assert actual["weights"] == [[3.0, 1.0, 3.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 1.0, 1.0, 3.0, 1.0, 1.0]]
    ids = action_to_ids(action())
    assert actual["decoder_input_ids"] == [ids[:-1]]
    assert actual["target_ids"] == [ids[1:]]
    assert actual["lengths"] == [len(ids) - 1]
    assert LOSS_CONTRACT["pad_weight"] == 0.0


def test_right_padding_zeroes_weights_without_changing_targets_or_actions():
    actions = [action(), action(3)]
    before = deepcopy(actions)
    result = loss_weight_rows(actions)
    assert actions == before
    assert len(set(map(len, result["weights"]))) == 1
    for index, length in enumerate(result["lengths"]):
        assert result["weights"][index][length:] == [0.0] * (len(result["weights"][index]) - length)
        assert result["target_ids"][index][length:] == [PAD_ID] * (len(result["weights"][index]) - length)
        assert all(value > 0 for value in result["weights"][index][:length])


@pytest.mark.parametrize("actions", [None, [], {}, ()])
def test_invalid_action_batches_refused(actions):
    with pytest.raises(PolicyContractError, match="ACTION_BATCH_REQUIRED"):
        loss_weight_rows(actions)


@pytest.mark.parametrize("bound", [True, 15, 513, 256.0])
def test_invalid_lengths_refused(bound):
    with pytest.raises(PolicyContractError, match="ACTION_BOUND_INVALID"):
        loss_weight_rows([action()], max_length=bound)


def test_cpu_weight_creation_refused_before_neural_import():
    with pytest.raises(PolicyContractError, match="NO_CPU_FALLBACK"):
        encode_loss_weights([action()], {}, device="cpu")
    with pytest.raises(PolicyContractError, match="NO_CPU_FALLBACK"):
        weighted_training_loss(SimpleNamespace(device="cpu"), {}, None)


def test_shared_loss_module_has_no_top_level_neural_import_or_optimizer():
    source = (Path(__file__).parents[1] / "cas_meta2" / "loss_v3.py").read_text()
    tree = ast.parse(source)
    assert {node.module for node in tree.body if isinstance(node, ast.ImportFrom)} == {"__future__", "codec", "selection_v3"}
    assert not any(isinstance(node, ast.Import) for node in tree.body)
    assert "target_loss_weights(action" in source
    assert "(per_token * weights).sum() / denominator" in source
    assert "weights[~valid] == 0" in source
    assert "logsumexp(log_probabilities.detach()" in source
    assert not any(isinstance(node, ast.Attribute) and node.attr in {"step", "AdamW", "SGD"} for node in ast.walk(tree))
