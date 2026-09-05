"""AWS-only numerical loss tests; no local neural import or training run."""
import os
import re

import pytest

pytestmark = pytest.mark.gpu
if os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1":
    pytest.skip("Explicit AWS GPU loss-test authorization required", allow_module_level=True)
if re.fullmatch(r"cas-meta2-[A-Za-z0-9-]+", os.environ.get("CAS_META2_AWS_JOB_ID", "")) is None:
    raise RuntimeError("COPY_LOSS_AWS_JOB_ID_REQUIRED_BEFORE_NEURAL_IMPORT")

import torch

from cas_meta2.codec import ACTION_VOCABULARY, PolicyContractError
from cas_meta2.loss_v3 import encode_loss_weights, weighted_training_loss
from cas_meta2.policy_v3 import encode_targets, require_cuda
from cas_meta2.train_v3 import setup_cuda


def action(steps=1):
    return {"binding": 0, "program": {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v" + str(index)} for index in range(steps)],
            "return": "v" + str(steps - 1)}}}}


def fixture():
    require_cuda()
    setup_cuda(7)
    actions = [action(), action(3)]
    target = encode_targets(actions, max_length=64)
    weights = encode_loss_weights(actions, target, device="cuda", max_length=64)
    raw = torch.randn((*target["target_ids"].shape, len(ACTION_VOCABULARY)), device="cuda", requires_grad=True)
    return actions, target, weights, raw


def test_weighted_nll_matches_independent_sum_and_pad_gradients_are_zero():
    _, target, weights, raw = fixture()
    logp = torch.log_softmax(raw, dim=-1)
    actual = weighted_training_loss(logp, target, weights)
    numerator, denominator = 0.0, 0.0
    for row in range(target["target_ids"].shape[0]):
        for column in range(target["target_ids"].shape[1]):
            weight = float(weights[row, column])
            numerator -= float(logp[row, column, int(target["target_ids"][row, column])]) * weight
            denominator += weight
    assert float(actual) == pytest.approx(numerator / denominator, rel=1e-6, abs=1e-6)
    actual.backward()
    assert torch.isfinite(raw.grad).all() and raw.grad.abs().sum() > 0
    assert int(torch.count_nonzero(raw.grad[~target["valid"]])) == 0
    assert actual.device.type == weights.device.type == "cuda"


def test_weight_encoding_rejects_misaligned_target_or_decoder_inputs():
    actions, target, _, _ = fixture()
    for field in ("target_ids", "decoder_input_ids"):
        changed = {key: value.clone() for key, value in target.items()}
        changed[field][0, 1] = 20
        with pytest.raises(PolicyContractError, match="ALIGNMENT_MISMATCH"):
            encode_loss_weights(actions, changed, device="cuda", max_length=64)


@pytest.mark.parametrize("fault", ["negative", "nan", "zero_valid", "positive_pad", "learnable", "cpu"])
def test_invalid_weights_are_refused(fault):
    _, target, weights, raw = fixture()
    if fault == "negative": weights[0, 0] = -1
    elif fault == "nan": weights[0, 0] = float("nan")
    elif fault == "zero_valid": weights[0, 0] = 0
    elif fault == "positive_pad": weights[0, -1] = 1
    elif fault == "learnable": weights.requires_grad_(True)
    else: weights = weights.cpu()  # Negative fixture on AWS; never a fallback.
    with pytest.raises(PolicyContractError, match="V3_LOSS_"):
        weighted_training_loss(torch.log_softmax(raw, -1), target, weights)


@pytest.mark.parametrize("fault", ["raw_logits", "nan", "wrong_vocabulary", "bad_valid", "bad_lengths"])
def test_bad_log_probabilities_and_target_layout_are_refused(fault):
    _, target, weights, raw = fixture()
    logp = torch.log_softmax(raw, -1)
    if fault == "raw_logits": logp = raw
    elif fault == "nan":
        logp = logp.clone()
        logp[0, 0, 0] = float("nan")
    elif fault == "wrong_vocabulary": logp = logp[..., :-1]
    elif fault == "bad_valid": target["valid"][0, 0] = False
    else: target["lengths"][0] -= 1
    with pytest.raises(PolicyContractError, match="V3_LOSS_"):
        weighted_training_loss(logp, target, weights)
