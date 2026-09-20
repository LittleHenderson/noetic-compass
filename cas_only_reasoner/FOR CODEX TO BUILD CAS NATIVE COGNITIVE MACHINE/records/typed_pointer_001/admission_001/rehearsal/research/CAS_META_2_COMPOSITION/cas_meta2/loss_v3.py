"""One fixed weighted training loss shared by candidate trainer and preflight.

Module import and loss_weight_rows are pure Python. Neural operations require
CUDA and import Torch only inside that path. Targets are training labels, not
prediction inputs. No private evaluation file, optimizer or model is opened.
"""
from __future__ import annotations

from .codec import ACTION_VOCABULARY, PAD_ID, PolicyContractError, action_to_ids
from .selection_v3 import STRUCTURAL_LOSS_WEIGHT, SEMANTIC_LOSS_WEIGHT, target_loss_weights

SCHEMA = "cas-meta2-fixed-role-weighted-nll/3"
LOSS_CONTRACT = {"schema": SCHEMA, "semantic_weight": SEMANTIC_LOSS_WEIGHT,
    "structural_weight": STRUCTURAL_LOSS_WEIGHT, "pad_weight": 0.0,
    "normalization": "Sum of positive non-PAD weights across the batch.",
    "input": "Normalized next-token log probabilities, not probabilities or raw logits."}


def _require(condition, reason):
    if not condition:
        raise PolicyContractError(reason)


def loss_weight_rows(actions, *, max_length=256):
    """Pure exact target/weight alignment, with zero weights for right padding."""
    _require(type(actions) is list and bool(actions), "V3_LOSS_ACTION_BATCH_REQUIRED")
    _require(type(max_length) is int and 16 <= max_length <= 512, "V3_LOSS_ACTION_BOUND_INVALID")
    token_rows = [action_to_ids(action, max_length=max_length) for action in actions]
    weight_rows = [list(target_loss_weights(action, max_length=max_length)) for action in actions]
    lengths = [len(row) - 1 for row in token_rows]
    _require(all(len(weights) == count and all(type(value) is float and value in (1.0, 3.0)
                 for value in weights) for weights, count in zip(weight_rows, lengths)),
             "V3_FIXED_ROLE_WEIGHT_ALIGNMENT_INVALID")
    width = max(lengths)
    return {"decoder_input_ids": [row[:-1] + [PAD_ID] * (width - count) for row, count in zip(token_rows, lengths)],
            "target_ids": [row[1:] + [PAD_ID] * (width - count) for row, count in zip(token_rows, lengths)],
            "weights": [weights + [0.0] * (width - count) for weights, count in zip(weight_rows, lengths)],
            "lengths": lengths}


def _runtime(device):
    # Reject an explicit CPU path before importing any neural dependency.
    _require(str(device).split(":", 1)[0] == "cuda", "V3_LOSS_GPU_REQUIRED:NO_CPU_FALLBACK")
    import torch
    from .policy_v3 import require_cuda
    return torch, require_cuda(device)


def _checked_target_batch(target_batch, torch, device):
    _require(type(target_batch) is dict and set(target_batch) == {
        "decoder_input_ids", "target_ids", "valid", "lengths"}, "V3_LOSS_TARGET_FIELDS_INVALID")
    _require(all(isinstance(value, torch.Tensor) and value.device == device for value in target_batch.values()),
             "V3_LOSS_TARGETS_MUST_BE_ALL_CUDA")
    targets, valid = target_batch["target_ids"], target_batch["valid"]
    inputs, lengths = target_batch["decoder_input_ids"], target_batch["lengths"]
    _require(targets.ndim == 2 and targets.shape[0] > 0 and targets.shape[1] > 0
             and inputs.shape == targets.shape and valid.shape == targets.shape
             and lengths.shape == (targets.shape[0],), "V3_LOSS_TARGET_GEOMETRY_INVALID")
    _require(targets.dtype == inputs.dtype == lengths.dtype == torch.long and valid.dtype == torch.bool,
             "V3_LOSS_TARGET_DTYPE_INVALID")
    _require(bool(((targets >= 0) & (targets < len(ACTION_VOCABULARY))).all())
             and bool(((inputs >= 0) & (inputs < len(ACTION_VOCABULARY))).all()), "V3_LOSS_TARGET_ID_INVALID")
    positions = torch.arange(targets.shape[1], device=device)[None, :]
    _require(bool(((lengths > 0) & (lengths <= targets.shape[1])).all())
             and torch.equal(valid, targets != PAD_ID)
             and torch.equal(valid, positions < lengths[:, None]), "V3_LOSS_TARGET_PADDING_INVALID")
    return targets, valid


def encode_loss_weights(actions, target_batch, *, device="cuda", max_length=256):
    """Create weights only when the supplied CUDA targets match these actions."""
    rows = loss_weight_rows(actions, max_length=max_length)
    torch, device = _runtime(device)
    targets, _ = _checked_target_batch(target_batch, torch, device)
    expected = torch.tensor(rows["target_ids"], dtype=torch.long, device=device)
    expected_inputs = torch.tensor(rows["decoder_input_ids"], dtype=torch.long, device=device)
    expected_lengths = torch.tensor(rows["lengths"], dtype=torch.long, device=device)
    _require(torch.equal(targets, expected)
             and torch.equal(target_batch["decoder_input_ids"], expected_inputs)
             and torch.equal(target_batch["lengths"], expected_lengths), "V3_LOSS_ACTION_TARGET_ALIGNMENT_MISMATCH")
    return torch.tensor(rows["weights"], dtype=torch.float32, device=device)


def weighted_training_loss(log_probabilities, target_batch, weights):
    """Return sum(weight * -log P(gold token)) / sum(positive weights)."""
    torch, device = _runtime(getattr(log_probabilities, "device", None))
    targets, valid = _checked_target_batch(target_batch, torch, device)
    _require(isinstance(log_probabilities, torch.Tensor) and log_probabilities.device == device
             and log_probabilities.shape == (*targets.shape, len(ACTION_VOCABULARY))
             and log_probabilities.dtype in (torch.float32, torch.float64), "V3_LOSS_LOG_PROBABILITY_GEOMETRY_INVALID")
    _require(isinstance(weights, torch.Tensor) and weights.device == device and weights.shape == targets.shape
             and weights.dtype == torch.float32 and not weights.requires_grad, "V3_LOSS_WEIGHT_GEOMETRY_INVALID")
    _require(bool(torch.isfinite(log_probabilities).all()) and bool(torch.isfinite(weights).all()),
             "V3_LOSS_NONFINITE_INPUT")
    normalizer = torch.logsumexp(log_probabilities.detach(), dim=-1)
    _require(bool((normalizer.abs() <= 1e-5).all()), "V3_LOSS_NORMALIZED_LOG_PROBABILITIES_REQUIRED")
    _require(bool((weights[~valid] == 0).all())
             and bool(((weights[valid] == STRUCTURAL_LOSS_WEIGHT) | (weights[valid] == SEMANTIC_LOSS_WEIGHT)).all()),
             "V3_LOSS_FIXED_WEIGHTS_AND_PAD_ZERO_REQUIRED")
    denominator = weights.sum()
    _require(bool(denominator > 0), "V3_LOSS_WEIGHT_DENOMINATOR_EMPTY")
    per_token = -log_probabilities.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
    loss = (per_token * weights).sum() / denominator
    _require(bool(torch.isfinite(loss)), "V3_LOSS_NONFINITE_RESULT")
    return loss
