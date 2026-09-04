from __future__ import annotations

from dataclasses import replace
import copy

import pytest
import torch

from casformer import (
    CASControl,
    CASformerBlock,
    CASformerConfig,
    CASformerEncoder,
    CASformerLanguageModel,
    CJTRegionGate,
    DifferentialConductanceLinear,
    LearnedCASControlAdapter,
    OhmicMultiheadAttention,
    OperatingRegion,
)


DTYPE = torch.float64


def config(**changes):
    values = dict(
        d_model=8,
        num_heads=2,
        num_relations=3,
        num_layers=2,
        dropout=0.0,
        attention_dropout=0.0,
        initial_beta=1.0,
        beta_max=4.0,
        initial_cutoff=0.25,
        initial_saturation=2.0,
    )
    values.update(changes)
    return CASformerConfig(**values)


@pytest.mark.parametrize(
    "field",
    (
        "minimum_total_resistance",
        "reference_resistance",
        "reference_drive",
        "initial_beta",
        "beta_max",
        "initial_cutoff",
        "initial_saturation",
        "minimum_weight_resistance",
    ),
)
def test_configuration_rejects_nonfinite_scalar_values(field: str):
    with pytest.raises(ValueError, match="finite"):
        config(**{field: float("nan")})


def test_large_finite_cjt_initial_values_construct_without_inverse_overflow():
    cfg = config(initial_cutoff=500.0, initial_saturation=1000.0)
    gate = CJTRegionGate(cfg).to(dtype=DTYPE)
    assert torch.isfinite(gate.cutoff).all()
    assert torch.isfinite(gate.saturation).all()
    assert torch.allclose(gate.cutoff, torch.full_like(gate.cutoff, 500.0))
    assert torch.allclose(gate.saturation, torch.full_like(gate.saturation, 1000.0))

    adapter_cfg = config(reference_drive=1000.0, reference_resistance=1000.0)
    adapter = LearnedCASControlAdapter(adapter_cfg)
    assert all(torch.isfinite(parameter).all() for parameter in adapter.parameters())


@pytest.mark.parametrize("field", ("dropout", "attention_dropout"))
def test_v0_1_rejects_nonzero_dropout(field: str):
    with pytest.raises(ValueError, match="requires dropout"):
        config(**{field: 0.1})


def test_cjt_regions_are_distinct_and_breakdown_fails_closed():
    gate_module = CJTRegionGate(config()).to(dtype=DTYPE)
    with torch.no_grad():
        gate_module.bias_projection.weight.zero_()
        gate_module.diagnostic_projection.weight.zero_()
        gate_module.diagnostic_projection.bias.zero_()
    current = torch.tensor([[[0.1, 1.0, 3.0], [0.1, 1.0, 3.0]]], dtype=DTYPE)
    bias = torch.zeros(1, 3, 8, dtype=DTYPE)
    diagnostics = torch.zeros(1, 2, 3, 5, dtype=DTYPE)
    breakdown = torch.zeros(1, 2, 3, dtype=torch.bool)
    breakdown[0, 0, 1] = True
    gate, _, regions, _ = gate_module(current, bias, diagnostics, breakdown)
    assert regions[0, 1].tolist() == [
        int(OperatingRegion.CUTOFF),
        int(OperatingRegion.ACTIVE),
        int(OperatingRegion.SATURATION),
    ]
    assert regions[0, 0, 1].item() == int(OperatingRegion.BREAKDOWN)
    assert gate[0, 0, 1].item() == 0.0
    assert gate[0, 1, 0].item() == 0.0
    assert gate[0, 1, 2].item() == 1.0
    assert gate[0, 1, 0] < gate[0, 1, 1] < gate[0, 1, 2]


def test_zero_flow_keeps_gate_cutoff_even_when_bias_alone_would_saturate():
    gate_module = CJTRegionGate(config()).to(dtype=DTYPE)
    with torch.no_grad():
        gate_module.bias_projection.weight.fill_(10.0)
        gate_module.diagnostic_projection.weight.zero_()
        gate_module.diagnostic_projection.bias.zero_()
    current = torch.zeros(1, 2, 1, dtype=DTYPE)
    bias = torch.ones(1, 1, 8, dtype=DTYPE)
    diagnostics = torch.zeros(1, 2, 1, 5, dtype=DTYPE)

    gate, preactivation, regions, _ = gate_module(current, bias, diagnostics)

    assert torch.equal(preactivation, torch.zeros_like(preactivation))
    assert torch.equal(gate, torch.zeros_like(gate))
    assert torch.equal(
        regions,
        torch.full_like(regions, int(OperatingRegion.CUTOFF)),
    )


def test_exact_cjt_boundaries_have_consistent_gate_and_region_labels():
    gate_module = CJTRegionGate(config()).to(dtype=DTYPE)
    with torch.no_grad():
        gate_module.bias_projection.weight.zero_()
        gate_module.diagnostic_projection.weight.zero_()
        gate_module.diagnostic_projection.bias.zero_()
    current = torch.stack((gate_module.cutoff, gate_module.saturation), dim=-1).unsqueeze(0)
    bias = torch.zeros(1, 2, 8, dtype=DTYPE)
    diagnostics = torch.zeros(1, 2, 2, 5, dtype=DTYPE)

    gate, _, regions, _ = gate_module(current, bias, diagnostics)

    assert torch.equal(gate[..., 0], torch.zeros_like(gate[..., 0]))
    assert torch.equal(gate[..., 1], torch.ones_like(gate[..., 1]))
    assert torch.equal(
        regions[..., 0],
        torch.full_like(regions[..., 0], int(OperatingRegion.CUTOFF)),
    )
    assert torch.equal(
        regions[..., 1],
        torch.full_like(regions[..., 1], int(OperatingRegion.SATURATION)),
    )


def test_cjt_parameterization_preserves_positive_representable_region_span():
    gate_module = CJTRegionGate(config()).to(dtype=DTYPE)
    with torch.no_grad():
        gate_module.raw_beta.fill_(-1000.0)
        gate_module.raw_cutoff.fill_(-1000.0)
        gate_module.raw_span.fill_(-1000.0)
        gate_module.bias_projection.weight.zero_()
        gate_module.diagnostic_projection.weight.zero_()
        gate_module.diagnostic_projection.bias.zero_()
    cutoff = gate_module.cutoff.detach()
    saturation = gate_module.saturation.detach()
    current = torch.stack((cutoff, saturation), dim=-1).unsqueeze(0)
    bias = torch.zeros(1, 2, 8, dtype=DTYPE)
    diagnostics = torch.zeros(1, 2, 2, 5, dtype=DTYPE)

    gate, _, regions, beta = gate_module(current, bias, diagnostics)

    assert torch.all(beta > 0)
    assert torch.all(beta < gate_module.config.beta_max)
    assert torch.all(cutoff > 0)
    assert torch.all(saturation > cutoff)
    assert torch.isfinite(gate).all()
    assert torch.equal(gate[..., 0], torch.zeros_like(gate[..., 0]))
    assert torch.equal(gate[..., 1], torch.ones_like(gate[..., 1]))
    assert torch.equal(
        regions[..., 0],
        torch.full_like(regions[..., 0], int(OperatingRegion.CUTOFF)),
    )
    assert torch.equal(
        regions[..., 1],
        torch.full_like(regions[..., 1], int(OperatingRegion.SATURATION)),
    )
    with torch.no_grad():
        gate_module.raw_beta.fill_(1000.0)
    assert torch.all(gate_module.beta < gate_module.config.beta_max)


@pytest.mark.parametrize(
    ("beta_max", "initial_beta", "message"),
    (
        (1e-46, 5e-47, "beta_max"),
        (1e-40, 1e-50, "initial_beta"),
        (1e39, 5e38, "beta_max"),
    ),
)
def test_cjt_beta_bounds_must_be_representable_in_module_dtype(
    beta_max: float, initial_beta: float, message: str
):
    gate = CJTRegionGate(config(beta_max=beta_max, initial_beta=initial_beta))
    with pytest.raises(ValueError, match=message):
        _ = gate.beta


def test_cjt_beta_extreme_raw_values_remain_strictly_interior_after_dtype_cast():
    gate = CJTRegionGate(
        config(beta_max=1e300, initial_beta=5e299)
    ).double()
    with torch.no_grad():
        gate.raw_beta.fill_(-1000)
    low = gate.beta
    with torch.no_grad():
        gate.raw_beta.fill_(1000)
    high = gate.beta

    assert torch.isfinite(low).all()
    assert torch.isfinite(high).all()
    assert torch.all(low > 0)
    assert torch.all(high < gate.config.beta_max)


def test_breakdown_masks_extreme_finite_bias_before_all_cjt_projections():
    cfg = config(d_model=4, num_heads=1, num_relations=1, num_layers=1)
    block = CASformerBlock(cfg).to(dtype=DTYPE)
    x = torch.randn(1, 2, cfg.d_model, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    breakdown = torch.ones(1, 1, 2, dtype=torch.bool)
    extreme_bias = torch.full_like(x, torch.finfo(DTYPE).max)
    with torch.no_grad():
        block.cjt_gate.bias_projection.weight.fill_(2.0)
        block.cjt_effect_bias.weight.fill_(2.0)

    output, telemetry = block(
        x,
        replace(control, bias=extreme_bias, breakdown_mask=breakdown),
    )

    assert torch.isfinite(output).all()
    assert torch.equal(telemetry.cjt_gate, torch.zeros_like(telemetry.cjt_gate))
    assert torch.equal(telemetry.cjt_effect, torch.zeros_like(telemetry.cjt_effect))
    assert torch.equal(
        telemetry.operating_region,
        torch.full_like(telemetry.operating_region, int(OperatingRegion.BREAKDOWN)),
    )


def test_breakdown_isolates_extreme_route_flow_before_attention_reduction():
    cfg = config(d_model=4, num_heads=1, num_relations=1, num_layers=1)
    block = CASformerBlock(cfg).to(dtype=DTYPE)
    x = torch.randn(1, 2, cfg.d_model, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    breakdown = torch.tensor([[[True, False]]])
    drive = control.drive.clone()
    drive[:, :, 0, :] = torch.finfo(DTYPE).max

    output, telemetry = block(
        x,
        replace(control, drive=drive, breakdown_mask=breakdown),
    )

    assert torch.isfinite(output).all()
    assert torch.equal(
        telemetry.attention.current[:, :, 0],
        torch.zeros_like(telemetry.attention.current[:, :, 0]),
    )
    assert torch.equal(
        telemetry.attention.attention[:, :, 0],
        torch.zeros_like(telemetry.attention.attention[:, :, 0]),
    )
    assert telemetry.operating_region[0, 0, 0].item() == int(
        OperatingRegion.BREAKDOWN
    )


def test_all_closed_flow_masks_irrelevant_extreme_bias_and_returns_zero_effect():
    cfg = config(d_model=4, num_heads=1, num_relations=1, num_layers=1)
    block = CASformerBlock(cfg).to(dtype=DTYPE)
    x = torch.randn(1, 2, cfg.d_model, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    topology_mask = torch.zeros_like(control.topology_mask)
    extreme_bias = torch.full_like(x, torch.finfo(DTYPE).max)
    with torch.no_grad():
        block.cjt_gate.bias_projection.weight.fill_(2.0)
        block.cjt_effect_bias.weight.fill_(2.0)

    output, telemetry = block(
        x,
        replace(control, bias=extreme_bias, topology_mask=topology_mask),
    )

    assert torch.isfinite(output).all()
    assert torch.equal(telemetry.cjt_gate, torch.zeros_like(telemetry.cjt_gate))
    assert torch.equal(telemetry.cjt_effect, torch.zeros_like(telemetry.cjt_effect))
    assert torch.equal(
        telemetry.operating_region,
        torch.full_like(telemetry.operating_region, int(OperatingRegion.CUTOFF)),
    )


def test_beta_changes_cjt_effect_but_not_attention_routing():
    torch.manual_seed(7)
    block = CASformerBlock(config(num_layers=1)).to(dtype=DTYPE)
    x = torch.randn(1, 4, 8, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=2, drive=0.2)
    with torch.no_grad():
        block.cjt_gate.bias_projection.weight.zero_()
        block.cjt_gate.diagnostic_projection.weight.zero_()
        block.cjt_gate.diagnostic_projection.bias.zero_()
    first_output, first = block(x, control)
    with torch.no_grad():
        block.cjt_gate.raw_beta.add_(1.0)
    second_output, second = block(x, control)
    assert torch.equal(first.attention.current, second.attention.current)
    assert torch.equal(first.attention.attention, second.attention.attention)
    assert torch.equal(first.cjt_gate, second.cjt_gate)
    assert not torch.allclose(first.cjt_effect, second.cjt_effect)
    assert not torch.allclose(first_output, second_output)


def test_relation_type_selects_a_different_operator():
    torch.manual_seed(9)
    block = CASformerBlock(config(num_layers=1)).to(dtype=DTYPE)
    x = torch.randn(1, 3, 8, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=2)
    with torch.no_grad():
        block.attention.relation_operators[0].copy_(
            torch.eye(4, dtype=DTYPE).repeat(2, 1, 1)
        )
        block.attention.relation_operators[1].copy_(
            -torch.eye(4, dtype=DTYPE).repeat(2, 1, 1)
        )
    first, _ = block(x, control)
    second, _ = block(
        x, replace(control, relation_ids=torch.ones_like(control.relation_ids))
    )
    assert not torch.allclose(first, second)


def test_type_label_permutation_is_not_a_valid_negative_control_by_itself():
    torch.manual_seed(33)
    original = CASformerBlock(config(num_layers=1)).to(dtype=DTYPE).eval()
    relabeled = copy.deepcopy(original)
    x = torch.randn(1, 3, 8, dtype=DTYPE)
    relation_ids = (
        torch.tensor([[0, 1, 2], [2, 0, 1], [1, 2, 0]], dtype=torch.long)
        .view(1, 1, 3, 3)
        .expand(1, 2, 3, 3)
        .clone()
    )
    control = replace(
        CASControl.uniform(x, num_heads=2), relation_ids=relation_ids
    )
    permutation = torch.tensor([2, 0, 1])
    inverse = torch.empty_like(permutation)
    inverse[permutation] = torch.arange(3)
    with torch.no_grad():
        # New label permutation[old] receives the old label's operator.
        relabeled.attention.relation_operators.copy_(
            original.attention.relation_operators[inverse]
        )
    relabeled_control = replace(control, relation_ids=permutation[control.relation_ids])
    with torch.no_grad():
        expected, _ = original(x, control)
        actual, _ = relabeled(x, relabeled_control)
    assert torch.allclose(actual, expected, atol=1e-12, rtol=1e-10)


def test_zero_flow_produces_zero_cjt_effect_and_finite_residual_block():
    torch.manual_seed(10)
    block = CASformerBlock(config(num_layers=1)).to(dtype=DTYPE)
    x = torch.randn(1, 3, 8, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=2, drive=0.0)
    output, telemetry = block(x, control)
    assert torch.equal(telemetry.attention.current, torch.zeros_like(telemetry.attention.current))
    assert torch.equal(telemetry.cjt_gate, torch.zeros_like(telemetry.cjt_gate))
    assert torch.equal(telemetry.cjt_effect, torch.zeros_like(telemetry.cjt_effect))
    assert torch.isfinite(output).all()


def test_encoder_forward_backward_and_state_dict_replay_are_finite_and_exact():
    torch.manual_seed(11)
    model = CASformerEncoder(config()).to(dtype=DTYPE)
    x = torch.randn(2, 4, 8, dtype=DTYPE, requires_grad=True)
    control = CASControl.uniform(x, num_heads=2, causal=True)
    output, telemetry = model(x, control)
    assert output.shape == x.shape
    assert len(telemetry) == 2
    loss = output.square().mean() + sum(item.cjt_gate.mean() for item in telemetry)
    loss.backward()
    assert x.grad is not None and torch.isfinite(x.grad).all()
    gradients = [parameter.grad for parameter in model.parameters() if parameter.requires_grad]
    assert all(gradient is not None for gradient in gradients)
    assert all(torch.isfinite(gradient).all() for gradient in gradients if gradient is not None)

    replay = CASformerEncoder(config()).to(dtype=DTYPE)
    replay.load_state_dict(model.state_dict())
    with torch.no_grad():
        expected, _ = model(x.detach(), control)
        actual, _ = replay(x.detach(), control)
    assert torch.equal(expected, actual)


def test_graph_encoder_is_permutation_equivariant_without_position_features():
    torch.manual_seed(13)
    model = CASformerEncoder(config(num_layers=1)).to(dtype=DTYPE).eval()
    x = torch.randn(1, 4, 8, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=2)
    base, _ = model(x, control)
    permutation = torch.tensor([2, 0, 3, 1])

    def permute_edges(value: torch.Tensor) -> torch.Tensor:
        return value.index_select(2, permutation).index_select(3, permutation)

    permuted_control = replace(
        control,
        drive=permute_edges(control.drive),
        resistance_capability=permute_edges(control.resistance_capability),
        resistance_policy=permute_edges(control.resistance_policy),
        resistance_context=permute_edges(control.resistance_context),
        resistance_resource=permute_edges(control.resistance_resource),
        readiness=permute_edges(control.readiness),
        region_multiplier=permute_edges(control.region_multiplier),
        topology_mask=permute_edges(control.topology_mask),
        permission_mask=permute_edges(control.permission_mask),
        relation_ids=permute_edges(control.relation_ids),
        bias=control.bias.index_select(1, permutation),
    )
    permuted, _ = model(x.index_select(1, permutation), permuted_control)
    assert torch.allclose(permuted, base.index_select(1, permutation), atol=1e-11, rtol=1e-10)


def test_differential_conductance_is_positive_railed_signed_and_differentiable():
    torch.manual_seed(17)
    layer = DifferentialConductanceLinear(4, 3, minimum_resistance=0.1, bias=False).to(
        dtype=DTYPE
    )
    x = torch.randn(5, 4, dtype=DTYPE, requires_grad=True)
    positive = layer.positive_resistance
    negative = layer.negative_resistance
    assert torch.all(positive > 0)
    assert torch.all(negative > 0)
    expected = torch.nn.functional.linear(x, positive.reciprocal() - negative.reciprocal())
    actual = layer(x)
    assert torch.allclose(actual, expected, atol=1e-12, rtol=1e-10)

    with torch.no_grad():
        before = layer(x).clone()
        temporary = layer.raw_positive_resistance.clone()
        layer.raw_positive_resistance.copy_(layer.raw_negative_resistance)
        layer.raw_negative_resistance.copy_(temporary)
        after = layer(x).clone()
    assert torch.allclose(after, -before, atol=1e-12, rtol=1e-10)

    layer.zero_grad(set_to_none=True)
    layer(x).square().mean().backward()
    assert torch.isfinite(x.grad).all()
    assert torch.isfinite(layer.raw_positive_resistance.grad).all()
    assert torch.isfinite(layer.raw_negative_resistance.grad).all()


def test_differential_conductance_rejects_a_nonfinite_resistance_floor():
    with pytest.raises(ValueError, match="finite"):
        DifferentialConductanceLinear(2, 2, minimum_resistance=float("nan"))


def test_differential_conductance_rejects_floor_with_overflowing_reciprocal():
    smallest_positive = torch.nextafter(
        torch.tensor(0.0), torch.tensor(1.0)
    ).item()
    layer = DifferentialConductanceLinear(
        2, 2, minimum_resistance=smallest_positive
    )
    with torch.no_grad():
        layer.raw_positive_resistance.fill_(-1000)
        layer.raw_negative_resistance.fill_(-1000)

    with pytest.raises(ValueError, match="finite positive conductance"):
        layer(torch.ones(1, 2))


def test_differential_conductance_floor_is_checked_after_dtype_conversion():
    layer = DifferentialConductanceLinear(2, 2, minimum_resistance=1e-300)
    with pytest.raises(ValueError, match="representably positive"):
        _ = layer.positive_resistance

    double_layer = layer.double()
    positive = double_layer.positive_resistance
    negative = double_layer.negative_resistance
    assert torch.isfinite(positive).all()
    assert torch.isfinite(negative).all()
    assert torch.isfinite(positive.reciprocal()).all()
    assert torch.isfinite(negative.reciprocal()).all()
    assert torch.all(positive > double_layer.minimum_resistance)
    assert torch.all(negative > double_layer.minimum_resistance)


def test_differential_relation_operator_matches_its_nonsymmetric_linear_module():
    cfg = config(
        d_model=2,
        num_heads=1,
        num_relations=1,
        num_layers=1,
        linear_weight_mode="differential_conductance",
    )
    attention = OhmicMultiheadAttention(cfg).to(dtype=DTYPE).eval()
    assert attention.relation_operator_modules is not None
    relation_module = attention.relation_operator_modules[0][0]
    with torch.no_grad():
        relation_module.raw_positive_resistance.copy_(
            torch.tensor([[-2.0, -0.5], [0.75, 2.0]], dtype=DTYPE)
        )
        relation_module.raw_negative_resistance.copy_(
            torch.tensor([[1.5, 0.25], [-1.25, 0.5]], dtype=DTYPE)
        )
    x = torch.tensor([[[0.5, -1.0], [1.25, 0.75]]], dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)

    actual, telemetry = attention(x, control)
    projected_value = attention._split_heads(attention.v_proj(x))[:, 0]
    transformed_value = relation_module(projected_value)
    expected = torch.einsum(
        "bqk,bkd->bqd", telemetry.attention[:, 0], transformed_value
    )

    assert not torch.allclose(
        relation_module.effective_weight,
        relation_module.effective_weight.transpose(0, 1),
    )
    assert torch.allclose(actual[:, 0], expected, atol=1e-12, rtol=1e-10)


def test_optional_differential_conductance_weight_mode_runs_and_backpropagates():
    torch.manual_seed(71)
    cfg = config(
        num_layers=1,
        linear_weight_mode="differential_conductance",
        minimum_weight_resistance=0.2,
    )
    block = CASformerBlock(cfg).to(dtype=DTYPE)
    assert isinstance(block.attention.q_proj, DifferentialConductanceLinear)
    assert isinstance(block.attention.k_proj, DifferentialConductanceLinear)
    assert isinstance(block.attention.v_proj, DifferentialConductanceLinear)
    assert isinstance(block.attention.out_proj, DifferentialConductanceLinear)
    assert block.attention.relation_operators is None
    assert block.attention.relation_operator_modules is not None
    assert isinstance(block.cjt_effect_bias, DifferentialConductanceLinear)
    assert isinstance(block.cjt_gate.bias_projection, DifferentialConductanceLinear)
    assert isinstance(block.cjt_gate.diagnostic_projection, DifferentialConductanceLinear)
    assert isinstance(block.feed_forward[0], DifferentialConductanceLinear)
    assert isinstance(block.feed_forward[3], DifferentialConductanceLinear)

    x = torch.randn(1, 3, 8, dtype=DTYPE, requires_grad=True)
    control = CASControl.uniform(x.detach(), num_heads=2, causal=True)
    output, _ = block(x, control)
    differential_modules = [
        module
        for module in block.modules()
        if isinstance(module, DifferentialConductanceLinear)
    ]
    regularizer = sum(module.common_mode_penalty() for module in differential_modules)
    (output.square().mean() + 1e-6 * regularizer).backward()
    assert torch.isfinite(output).all()
    assert x.grad is not None and torch.isfinite(x.grad).all()
    for module in differential_modules:
        assert torch.all(module.positive_resistance > cfg.minimum_weight_resistance)
        assert torch.all(module.negative_resistance > cfg.minimum_weight_resistance)
        assert module.raw_positive_resistance.grad is not None
        assert module.raw_negative_resistance.grad is not None

    model = CASformerLanguageModel(
        cfg,
        vocab_size=13,
        max_sequence_length=4,
        tie_embeddings=False,
    ).to(dtype=DTYPE)
    ids = torch.tensor([[1, 2, 3]], dtype=torch.long)
    logits, _ = model(ids, control)
    assert logits.shape == (1, 3, 13)
    assert torch.isfinite(logits).all()


def test_differential_language_head_rejects_embedding_tying():
    cfg = config(num_layers=1, linear_weight_mode="differential_conductance")
    with pytest.raises(ValueError, match="tie_embeddings must be false"):
        CASformerLanguageModel(cfg, vocab_size=13, max_sequence_length=4)


def test_learned_control_is_positive_trainable_and_policy_is_not_trainable():
    torch.manual_seed(47)
    cfg = config(num_layers=1)
    adapter = LearnedCASControlAdapter(cfg).to(dtype=DTYPE)
    block = CASformerBlock(cfg).to(dtype=DTYPE)
    x = torch.randn(2, 3, 8, dtype=DTYPE, requires_grad=True)
    shape = (2, 2, 3, 3)
    policy = torch.full(shape, 0.2, dtype=DTYPE, requires_grad=True)
    control = adapter(
        x,
        bias=torch.zeros_like(x),
        policy_resistance=policy,
        readiness=torch.ones(shape, dtype=DTYPE),
        region_multiplier=torch.ones(shape, dtype=DTYPE),
        topology_mask=torch.ones(shape, dtype=torch.bool),
        permission_mask=torch.ones(shape, dtype=torch.bool),
        relation_ids=torch.zeros(shape, dtype=torch.long),
    )
    assert torch.all(control.drive > 0)
    assert torch.all(control.total_resistance >= cfg.minimum_total_resistance)
    output, _ = block(x, control)
    output.square().mean().backward()
    assert policy.grad is None
    adapter_gradients = [parameter.grad for parameter in adapter.parameters()]
    assert all(gradient is not None and torch.isfinite(gradient).all() for gradient in adapter_gradients)


def test_language_model_is_causal_and_backpropagates():
    torch.manual_seed(53)
    cfg = config(num_layers=1)
    model = CASformerLanguageModel(
        cfg, vocab_size=17, max_sequence_length=8
    ).to(dtype=DTYPE)
    token_ids = torch.tensor([[1, 4, 2, 9], [3, 2, 5, 6]], dtype=torch.long)
    template = torch.zeros(2, 4, 8, dtype=DTYPE)
    causal = CASControl.uniform(template, num_heads=2, causal=True)
    logits, telemetry = model(token_ids, causal)
    assert logits.shape == (2, 4, 17)
    assert len(telemetry) == 1
    loss = torch.nn.functional.cross_entropy(
        logits[:, :-1].reshape(-1, 17), token_ids[:, 1:].reshape(-1)
    )
    loss.backward()
    assert all(
        parameter.grad is None or torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    )

    noncausal = CASControl.uniform(template, num_heads=2, causal=False)
    with torch.no_grad():
        try:
            model(token_ids, noncausal)
        except ValueError as exc:
            assert "causal topology_mask" in str(exc)
        else:
            raise AssertionError("noncausal language-model control was accepted")


def test_causal_language_model_prefix_is_invariant_to_later_token_changes():
    torch.manual_seed(67)
    cfg = config(num_layers=2)
    model = CASformerLanguageModel(
        cfg, vocab_size=19, max_sequence_length=8
    ).to(dtype=DTYPE).eval()
    first = torch.tensor([[1, 4, 2, 9, 3]], dtype=torch.long)
    second = torch.tensor([[1, 4, 8, 7, 6]], dtype=torch.long)
    template = torch.zeros(1, 5, 8, dtype=DTYPE)
    control = CASControl.uniform(template, num_heads=2, causal=True)
    with torch.no_grad():
        first_logits, _ = model(first, control)
        second_logits, _ = model(second, control)
    assert torch.equal(first_logits[:, :2], second_logits[:, :2])
