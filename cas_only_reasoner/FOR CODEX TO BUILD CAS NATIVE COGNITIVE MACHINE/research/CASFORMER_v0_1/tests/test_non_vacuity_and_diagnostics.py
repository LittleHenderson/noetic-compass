from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
import math

import pytest
import torch

from casformer import (
    CASControl,
    CASformerBlock,
    CASformerConfig,
    audit_flow,
    capability_resistance,
    make_trace,
    quantize_current,
    verify_trace,
)
from casformer.baselines import additive_output_mixture, additive_weight_path


DTYPE = torch.float64


def test_retired_additive_weight_path_matches_output_mixture_and_gradients():
    torch.manual_seed(19)
    x = torch.randn(7, 5, dtype=DTYPE, requires_grad=True)
    base = torch.randn(4, 5, dtype=DTYPE, requires_grad=True)
    deltas = torch.randn(3, 4, 5, dtype=DTYPE, requires_grad=True)
    raw_allocation = torch.randn(3, dtype=DTYPE, requires_grad=True)
    allocation = raw_allocation.softmax(dim=0)
    first = additive_weight_path(x, base, deltas, allocation)
    second = additive_output_mixture(x, base, deltas, allocation)
    assert torch.allclose(first, second, atol=1e-12, rtol=1e-10)
    probes = torch.randn_like(first)
    first_gradients = torch.autograd.grad(
        (first * probes).sum(), (x, base, deltas, raw_allocation), retain_graph=True
    )
    second_gradients = torch.autograd.grad(
        (second * probes).sum(), (x, base, deltas, raw_allocation)
    )
    for left, right in zip(first_gradients, second_gradients, strict=True):
        assert torch.allclose(left, right, atol=1e-11, rtol=1e-9)


def test_additive_twin_requires_a_probability_simplex():
    x = torch.ones(1, 2, dtype=DTYPE)
    base = torch.ones(1, 2, dtype=DTYPE)
    deltas = torch.ones(2, 1, 2, dtype=DTYPE)
    invalid = torch.tensor([2.0, 0.0], dtype=DTYPE)
    for operation in (additive_weight_path, additive_output_mixture):
        with pytest.raises(ValueError, match="sum to one"):
            operation(x, base, deltas, invalid)


def test_capability_quantization_and_flow_audit_keep_raw_evidence():
    capability = torch.tensor([0.0, 5.0, 10.0], dtype=DTYPE)
    resistance = capability_resistance(capability)
    assert torch.allclose(resistance, torch.tensor([10.0, 5.05, 0.1], dtype=DTYPE))

    raw = torch.tensor([2.0, 12.0], dtype=DTYPE)
    reading = quantize_current(raw, full_scale=10.0)
    assert torch.equal(reading.raw_current, raw)
    assert torch.equal(reading.normalized_current, torch.tensor([2.0, 10.0], dtype=DTYPE))
    assert torch.equal(reading.overload_ratio, torch.tensor([0.2, 1.2], dtype=DTYPE))

    audit = audit_flow(
        torch.tensor([4.0, 2.0], dtype=DTYPE),
        torch.tensor([2.0, 2.0], dtype=DTYPE),
        torch.tensor([1.5, 0.0], dtype=DTYPE),
    )
    assert torch.equal(audit.predicted_current, torch.tensor([2.0, 1.0], dtype=DTYPE))
    assert torch.equal(audit.residual, torch.tensor([-0.5, -1.0], dtype=DTYPE))
    assert audit.hidden_resistance_observable.tolist() == [True, False]
    assert torch.isnan(audit.hidden_resistance[1])


def test_diagnostics_reject_nonfinite_scalar_limits():
    value = torch.ones(1, dtype=DTYPE)
    with pytest.raises(ValueError, match="finite"):
        capability_resistance(value, minimum=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        quantize_current(value, full_scale=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        audit_flow(value, value, value, residual_floor=float("nan"))


def test_trace_is_serializable_checksum_bound_and_has_zero_authority():
    torch.manual_seed(23)
    config = CASformerConfig(d_model=8, num_heads=2, num_relations=3)
    block = CASformerBlock(config).to(dtype=DTYPE)
    x = torch.randn(1, 3, 8, dtype=DTYPE)
    control = CASControl.uniform(
        x,
        num_heads=2,
        profile_id="fixture-profile-v0",
        provenance="tests/test_non_vacuity_and_diagnostics.py",
        control_tick=2,
        feedback_source_tick=1,
    )
    _, telemetry = block(x, control)
    trace = make_trace(telemetry, control, layer_index=0, include_tensors=True)
    record = trace.to_dict()
    assert verify_trace(record)
    assert record["status"] == "NEURAL_PROXY_UNVALIDATED"
    assert not any(record["authority"].values())
    assert record["feedback_source_tick"] < record["control_tick"]
    tampered = copy.deepcopy(record)
    tampered["summaries"]["total_current"]["mean"] += 1
    assert not verify_trace(tampered)

    forged_authority = copy.deepcopy(record)
    forged_authority["authority"]["truth"] = True
    payload = {key: value for key, value in forged_authority.items() if key != "payload_sha256"}
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    forged_authority["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    assert not verify_trace(forged_authority)

    forged_status = copy.deepcopy(record)
    forged_status["status"] = "CLAIMED_VALID"
    payload = {key: value for key, value in forged_status.items() if key != "payload_sha256"}
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    forged_status["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    assert not verify_trace(forged_status)

    forged_tensor_type = copy.deepcopy(record)
    forged_tensor_type["tensors"]["attention"] = "not-an-array"
    payload = {
        key: value for key, value in forged_tensor_type.items() if key != "payload_sha256"
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    forged_tensor_type["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    assert not verify_trace(forged_tensor_type)

    forged_region = copy.deepcopy(record)
    forged_region["tensors"]["operating_region"] = [
        [[99 for _ in row] for row in head]
        for head in forged_region["tensors"]["operating_region"]
    ]
    payload = {key: value for key, value in forged_region.items() if key != "payload_sha256"}
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    forged_region["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    assert not verify_trace(forged_region)

    forged_huge_integer = copy.deepcopy(record)
    forged_huge_integer["tensors"]["semantic_scores"][0][0][0][0] = 10**400
    payload = {
        key: value
        for key, value in forged_huge_integer.items()
        if key != "payload_sha256"
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    forged_huge_integer["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    assert not verify_trace(forged_huge_integer)


def test_trace_redacts_closed_route_fields_and_records_the_effective_mask():
    torch.manual_seed(61)
    config = CASformerConfig(d_model=4, num_heads=1, num_relations=1)
    block = CASformerBlock(config).to(dtype=DTYPE)
    x = torch.randn(1, 2, 4, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    permission = control.permission_mask.clone()
    permission[0, 0, 0, 1] = False
    resistance = control.resistance_capability.clone()
    resistance[0, 0, 0, 1] = 1e9
    control = replace(
        control,
        permission_mask=permission,
        resistance_capability=resistance,
    )
    _, telemetry = block(x, control)
    record = make_trace(
        telemetry, control, layer_index=0, include_tensors=True
    ).to_dict()
    tensors = record["tensors"]
    assert tensors["effective_path_mask"][0][0][0][1] is False
    for field in (
        "semantic_scores",
        "total_resistance",
        "conductance",
        "edge_current",
        "semantic_allocation",
        "attention",
    ):
        assert tensors[field][0][0][0][1] == 0.0
    assert verify_trace(record)

    forged_redaction = copy.deepcopy(record)
    forged_redaction["tensors"]["total_resistance"][0][0][0][1] = 123.0
    serialized = torch.tensor(
        forged_redaction["tensors"]["total_resistance"], dtype=DTYPE
    )
    forged_redaction["summaries"]["total_resistance"] = {
        "shape": list(serialized.shape),
        "count": serialized.numel(),
        "minimum": float(serialized.min().item()),
        "maximum": float(serialized.max().item()),
        "mean": float(serialized.mean().item()),
    }
    payload = {
        key: value for key, value in forged_redaction.items() if key != "payload_sha256"
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    forged_redaction["payload_sha256"] = hashlib.sha256(canonical).hexdigest()
    assert not verify_trace(forged_redaction)


def test_trace_mean_stays_finite_for_extreme_finite_open_resistance():
    config = CASformerConfig(d_model=4, num_heads=1, num_relations=1)
    block = CASformerBlock(config).to(dtype=DTYPE)
    x = torch.randn(1, 2, 4, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    extreme = torch.full_like(control.resistance_capability, torch.finfo(DTYPE).max)
    zero = torch.zeros_like(extreme)
    control = replace(
        control,
        resistance_capability=extreme,
        resistance_policy=zero,
        resistance_context=zero,
        resistance_resource=zero,
    )

    output, telemetry = block(x, control)
    record = make_trace(telemetry, control, layer_index=0).to_dict()

    assert torch.isfinite(output).all()
    assert math.isfinite(record["summaries"]["total_resistance"]["mean"])
    assert verify_trace(record)
