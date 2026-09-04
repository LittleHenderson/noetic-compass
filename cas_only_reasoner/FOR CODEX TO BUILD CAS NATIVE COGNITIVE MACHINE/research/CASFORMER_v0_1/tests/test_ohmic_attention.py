from __future__ import annotations

from dataclasses import replace

import pytest
import torch

from casformer import CASControl, CASformerConfig, OhmicMultiheadAttention
from casformer.baselines import compiled_ohmic_attention, safe_masked_softmax


DTYPE = torch.float64


def setup_attention(*, sequence: int = 4):
    torch.manual_seed(20260903)
    config = CASformerConfig(
        d_model=8,
        num_heads=2,
        num_relations=3,
        initial_cutoff=0.05,
        initial_saturation=20.0,
    )
    module = OhmicMultiheadAttention(config).to(dtype=DTYPE)
    x = torch.randn(2, sequence, config.d_model, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=config.num_heads)
    return config, module, x, control


def test_neutral_conductance_matches_ordinary_masked_attention():
    _, module, x, control = setup_attention()
    _, telemetry = module(x, control)
    expected = safe_masked_softmax(telemetry.semantic_scores, control.path_mask)
    assert torch.allclose(telemetry.semantic_allocation, expected, atol=1e-12, rtol=1e-10)
    assert torch.allclose(telemetry.attention, expected, atol=1e-12, rtol=1e-10)
    assert torch.allclose(telemetry.total_current, torch.full_like(telemetry.total_current, 4.0))


def test_neutral_routing_matches_the_complete_effective_mask_domain():
    _, module, x, control = setup_attention(sequence=6)
    topology = control.topology_mask.clone()
    permission = control.permission_mask.clone()
    drive = control.drive.clone()
    readiness = control.readiness.clone()
    region = control.region_multiplier.clone()
    breakdown = torch.zeros(2, 2, 6, dtype=torch.bool)
    topology[0, 0, 0, 0] = False
    permission[0, 0, 0, 1] = False
    drive[0, 0, 0, 2] = 0
    readiness[0, 0, 0, 3] = 0
    region[0, 0, 0, 4] = 0
    breakdown[0, 0, 1] = True
    control = replace(
        control,
        topology_mask=topology,
        permission_mask=permission,
        drive=drive,
        readiness=readiness,
        region_multiplier=region,
        breakdown_mask=breakdown,
    )

    _, telemetry = module(x, control)
    expected = safe_masked_softmax(
        telemetry.semantic_scores, telemetry.effective_path_mask
    )

    assert torch.equal(telemetry.semantic_allocation, expected)
    assert torch.equal(telemetry.attention, expected)
    assert not telemetry.effective_path_mask[0, 0, 0, :5].any()
    assert not telemetry.effective_path_mask[0, 0, 1].any()


def test_scalar_router_matches_ordinary_compiled_logit_bias():
    config, module, x, control = setup_attention()
    drive = control.drive * torch.linspace(0.5, 2.0, x.shape[1], dtype=DTYPE)
    capability = control.resistance_capability.clone()
    capability[..., 0] = 1.25
    control = replace(control, drive=drive, resistance_capability=capability)
    _, telemetry = module(x, control)
    expected_attention, expected_current, expected_total = compiled_ohmic_attention(
        telemetry.semantic_scores,
        control.drive,
        control.total_resistance,
        control.readiness,
        control.region_multiplier,
        control.candidate_path_mask,
        reference_drive=config.reference_drive,
        reference_resistance=config.reference_resistance,
    )
    assert torch.allclose(telemetry.attention, expected_attention, atol=1e-12, rtol=1e-10)
    assert torch.allclose(telemetry.current, expected_current, atol=1e-12, rtol=1e-10)
    assert torch.allclose(telemetry.total_current, expected_total, atol=1e-12, rtol=1e-10)


@pytest.mark.parametrize("mask_name", ["topology_mask", "permission_mask"])
def test_hard_masks_are_exact_and_all_closed_rows_are_finite(mask_name: str):
    _, module, x, control = setup_attention()
    mask = getattr(control, mask_name).clone()
    mask[0, 0, 0, :] = False
    mask[1, 1, 2, 1] = False
    control = replace(control, **{mask_name: mask})
    output, telemetry = module(x, control)
    assert torch.equal(telemetry.current[0, 0, 0], torch.zeros_like(telemetry.current[0, 0, 0]))
    assert torch.equal(telemetry.attention[0, 0, 0], torch.zeros_like(telemetry.attention[0, 0, 0]))
    assert telemetry.current[1, 1, 2, 1].item() == 0.0
    assert telemetry.attention[1, 1, 2, 1].item() == 0.0
    assert telemetry.semantic_scores[1, 1, 2, 1].item() == 0.0
    assert telemetry.total_resistance[1, 1, 2, 1].item() == 0.0
    assert telemetry.conductance[1, 1, 2, 1].item() == 0.0
    assert not telemetry.effective_path_mask[1, 1, 2, 1].item()
    assert torch.isfinite(output).all()
    assert torch.isfinite(telemetry.attention).all()


def test_fully_closed_relation_cannot_poison_output_with_extreme_finite_weights():
    config = CASformerConfig(d_model=4, num_heads=1, num_relations=2)
    module = OhmicMultiheadAttention(config).to(dtype=DTYPE)
    x = torch.randn(1, 2, config.d_model, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    relation_ids = control.relation_ids.clone()
    relation_ids[..., 0] = 0
    relation_ids[..., 1] = 1
    permission_mask = control.permission_mask.clone()
    permission_mask[..., 1] = False
    with torch.no_grad():
        assert module.relation_operators is not None
        module.relation_operators[1].fill_(torch.finfo(DTYPE).max)

    output, telemetry = module(
        x,
        extreme_control := replace(
            control,
            relation_ids=relation_ids,
            permission_mask=permission_mask,
        ),
    )
    compiled_attention, compiled_current, compiled_total = compiled_ohmic_attention(
        telemetry.semantic_scores,
        extreme_control.drive,
        extreme_control.total_resistance,
        extreme_control.readiness,
        extreme_control.region_multiplier,
        extreme_control.candidate_path_mask,
    )

    assert torch.isfinite(output).all()
    assert torch.equal(
        telemetry.attention[..., 1], torch.zeros_like(telemetry.attention[..., 1])
    )
    assert torch.equal(
        telemetry.current[..., 1], torch.zeros_like(telemetry.current[..., 1])
    )
    assert torch.equal(telemetry.attention, compiled_attention)
    assert torch.equal(telemetry.current, compiled_current)
    assert torch.equal(telemetry.total_current, compiled_total)


def test_exact_zero_attention_relation_is_skipped_before_extreme_transform():
    config = CASformerConfig(d_model=2, num_heads=1, num_relations=2)
    module = OhmicMultiheadAttention(config).to(dtype=DTYPE).eval()
    scale = (1000.0 * (2.0**0.5)) ** 0.5
    with torch.no_grad():
        module.q_proj.weight.zero_()
        module.k_proj.weight.zero_()
        module.v_proj.weight.copy_(torch.eye(2, dtype=DTYPE))
        module.q_proj.weight[0, 0] = scale
        module.k_proj.weight[0, 0] = scale
        assert module.relation_operators is not None
        module.relation_operators[0].copy_(torch.eye(2, dtype=DTYPE).unsqueeze(0))
        module.relation_operators[1].fill_(torch.finfo(DTYPE).max)
    x = torch.tensor([[[1.0, 1.0], [-1.0, -1.0]]], dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    relation_ids = control.relation_ids.clone()
    relation_ids[0, 0, 0, 1] = 1

    output, telemetry = module(x, replace(control, relation_ids=relation_ids))

    assert telemetry.attention[0, 0, 0, 1].item() == 0.0
    assert torch.isfinite(output).all()


def test_closed_control_values_cannot_overflow_a_masked_route():
    config, module, x, control = setup_attention(sequence=2)
    permission_mask = control.permission_mask.clone()
    permission_mask[..., 1] = False
    extreme = torch.finfo(DTYPE).max
    drive = control.drive.clone()
    resistance_capability = control.resistance_capability.clone()
    resistance_policy = control.resistance_policy.clone()
    resistance_context = control.resistance_context.clone()
    resistance_resource = control.resistance_resource.clone()
    readiness = control.readiness.clone()
    region_multiplier = control.region_multiplier.clone()
    drive[..., 1] = extreme
    resistance_capability[..., 1] = extreme
    resistance_policy[..., 1] = extreme
    resistance_context[..., 1] = extreme
    resistance_resource[..., 1] = extreme
    readiness[..., 1] = extreme
    region_multiplier[..., 1] = extreme

    extreme_control = replace(
        control,
        drive=drive,
        resistance_capability=resistance_capability,
        resistance_policy=resistance_policy,
        resistance_context=resistance_context,
        resistance_resource=resistance_resource,
        readiness=readiness,
        region_multiplier=region_multiplier,
        permission_mask=permission_mask,
    )
    output, telemetry = module(x, extreme_control)
    compiled_attention, compiled_current, compiled_total = compiled_ohmic_attention(
        telemetry.semantic_scores,
        extreme_control.drive,
        extreme_control.total_resistance,
        extreme_control.readiness,
        extreme_control.region_multiplier,
        extreme_control.candidate_path_mask,
    )

    assert torch.isfinite(output).all()
    assert torch.isfinite(telemetry.diagnostic_features).all()
    assert torch.equal(
        telemetry.attention[..., 1], torch.zeros_like(telemetry.attention[..., 1])
    )
    assert torch.equal(
        telemetry.current[..., 1], torch.zeros_like(telemetry.current[..., 1])
    )
    assert torch.equal(telemetry.attention, compiled_attention)
    assert torch.equal(telemetry.current, compiled_current)
    assert torch.equal(telemetry.total_current, compiled_total)


def test_open_route_reduction_overflow_is_rejected_before_telemetry_returns():
    _, module, x, control = setup_attention(sequence=2)
    drive = torch.full_like(control.drive, torch.finfo(DTYPE).max)
    with pytest.raises(ValueError, match="total_current"):
        module(x, replace(control, drive=drive))


def test_log_domain_current_avoids_spurious_intermediate_overflow():
    _, module, x, control = setup_attention(sequence=2)
    maximum = torch.finfo(DTYPE).max
    tiny = torch.finfo(DTYPE).tiny
    stable_control = replace(
        control,
        drive=torch.full_like(control.drive, maximum),
        resistance_capability=torch.full_like(
            control.resistance_capability, maximum
        ),
        resistance_policy=torch.zeros_like(control.resistance_policy),
        resistance_context=torch.zeros_like(control.resistance_context),
        resistance_resource=torch.zeros_like(control.resistance_resource),
        readiness=torch.full_like(control.readiness, maximum),
        region_multiplier=torch.full_like(control.region_multiplier, tiny),
    )

    output, telemetry = module(x, stable_control)
    expected_attention, expected_current, expected_total = compiled_ohmic_attention(
        telemetry.semantic_scores,
        stable_control.drive,
        stable_control.total_resistance,
        stable_control.readiness,
        stable_control.region_multiplier,
        stable_control.candidate_path_mask,
    )

    assert torch.isfinite(output).all()
    assert torch.allclose(
        telemetry.current, torch.full_like(telemetry.current, 4.0), rtol=1e-12
    )
    assert torch.equal(telemetry.attention, expected_attention)
    assert torch.equal(telemetry.current, expected_current)
    assert torch.equal(telemetry.total_current, expected_total)


def test_log_domain_current_and_diagnostics_avoid_reference_ratio_overflow():
    tiny = torch.finfo(DTYPE).tiny
    config = CASformerConfig(
        d_model=4,
        num_heads=1,
        num_relations=1,
        reference_drive=tiny,
    )
    module = OhmicMultiheadAttention(config).to(dtype=DTYPE)
    x = torch.randn(1, 2, 4, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    stable_control = replace(
        control,
        drive=torch.full_like(control.drive, torch.finfo(DTYPE).max),
        readiness=torch.full_like(control.readiness, tiny),
        region_multiplier=torch.full_like(control.region_multiplier, tiny),
    )

    output, telemetry = module(x, stable_control)

    assert torch.isfinite(output).all()
    assert torch.isfinite(telemetry.current).all()
    assert torch.isfinite(telemetry.diagnostic_features).all()


@pytest.mark.parametrize("reference_name", ("reference_drive", "reference_resistance"))
def test_reference_scale_must_be_representably_positive_in_runtime_dtype(
    reference_name: str,
):
    config = CASformerConfig(
        d_model=4,
        num_heads=1,
        num_relations=1,
        **{reference_name: 1e-300},
    )
    module = OhmicMultiheadAttention(config)
    x = torch.randn(1, 2, 4)
    control = CASControl.uniform(x, num_heads=1)

    with pytest.raises(ValueError, match=reference_name):
        module(x, control)


@pytest.mark.parametrize("mode", ("overflow", "underflow"))
def test_candidate_relative_conductance_must_be_representable(mode: str):
    maximum = torch.finfo(DTYPE).max
    tiny = torch.finfo(DTYPE).tiny
    reference_resistance = maximum if mode == "overflow" else tiny
    config = CASformerConfig(
        d_model=4,
        num_heads=1,
        num_relations=1,
        reference_resistance=reference_resistance,
    )
    module = OhmicMultiheadAttention(config).to(dtype=DTYPE)
    x = torch.randn(1, 2, 4, dtype=DTYPE)
    control = CASControl.uniform(x, num_heads=1)
    capability = torch.full_like(
        control.resistance_capability, 0.1 if mode == "overflow" else maximum
    )
    zero = torch.zeros_like(capability)
    control = replace(
        control,
        resistance_capability=capability,
        resistance_policy=zero,
        resistance_context=zero,
        resistance_resource=zero,
        readiness=torch.full_like(control.readiness, tiny),
    )

    with pytest.raises(ValueError, match="relative conductance"):
        module(x, control)
    with pytest.raises(ValueError, match="relative conductance"):
        compiled_ohmic_attention(
            torch.zeros_like(control.drive),
            control.drive,
            control.total_resistance,
            control.readiness,
            control.region_multiplier,
            control.candidate_path_mask,
            reference_resistance=reference_resistance,
        )


def test_unrepresentable_positive_flow_closes_in_both_router_and_twin():
    _, module, x, control = setup_attention(sequence=2)
    tiny = torch.finfo(DTYPE).tiny
    underflow_control = replace(
        control,
        drive=torch.full_like(control.drive, tiny),
        readiness=torch.full_like(control.readiness, tiny),
    )

    output, telemetry = module(x, underflow_control)
    expected_attention, expected_current, expected_total = compiled_ohmic_attention(
        telemetry.semantic_scores,
        underflow_control.drive,
        underflow_control.total_resistance,
        underflow_control.readiness,
        underflow_control.region_multiplier,
        underflow_control.candidate_path_mask,
    )

    assert torch.isfinite(output).all()
    assert not telemetry.effective_path_mask.any()
    assert torch.equal(telemetry.attention, torch.zeros_like(telemetry.attention))
    assert torch.equal(telemetry.current, torch.zeros_like(telemetry.current))
    assert torch.equal(telemetry.attention, expected_attention)
    assert torch.equal(telemetry.current, expected_current)
    assert torch.equal(telemetry.total_current, expected_total)


def test_compiled_twin_uses_the_same_breakdown_aware_effective_mask():
    _, module, x, control = setup_attention(sequence=2)
    breakdown = torch.zeros(2, 2, 2, dtype=torch.bool)
    breakdown[0, 0, 0] = True
    control = replace(control, breakdown_mask=breakdown)

    _, telemetry = module(x, control)
    expected_attention, expected_current, expected_total = compiled_ohmic_attention(
        telemetry.semantic_scores,
        control.drive,
        control.total_resistance,
        control.readiness,
        control.region_multiplier,
        control.candidate_path_mask,
    )

    assert torch.equal(telemetry.attention, expected_attention)
    assert torch.equal(telemetry.current, expected_current)
    assert torch.equal(telemetry.total_current, expected_total)


def test_masked_fields_have_zero_gradient():
    scores = torch.tensor([[[[0.3, -0.1, 0.7]]]], dtype=DTYPE, requires_grad=True)
    drive = torch.tensor([[[[2.0, 1e9, 3.0]]]], dtype=DTYPE, requires_grad=True)
    resistance = torch.tensor([[[[2.0, 1e9, 4.0]]]], dtype=DTYPE, requires_grad=True)
    readiness = torch.ones_like(drive, requires_grad=True)
    region = torch.ones_like(drive, requires_grad=True)
    mask = torch.tensor([[[[True, False, True]]]])
    attention, current, _ = compiled_ohmic_attention(
        scores, drive, resistance, readiness, region, mask
    )
    loss = attention[..., 0].sum() + 0.01 * current.sum()
    gradients = torch.autograd.grad(loss, (scores, drive, resistance, readiness, region))
    for gradient in gradients:
        assert gradient[0, 0, 0, 1].item() == 0.0


def test_main_attention_telemetry_has_zero_gradient_to_closed_control_fields():
    _, module, x, control = setup_attention(sequence=3)
    permission = control.permission_mask.clone()
    permission[0, 0, 0, 1] = False
    drive = control.drive.clone().requires_grad_()
    capability = control.resistance_capability.clone().requires_grad_()
    readiness = control.readiness.clone().requires_grad_()
    region = control.region_multiplier.clone().requires_grad_()
    authored = replace(
        control,
        drive=drive,
        resistance_capability=capability,
        readiness=readiness,
        region_multiplier=region,
        permission_mask=permission,
    )
    output, telemetry = module(x, authored)
    loss = (
        output.square().sum()
        + telemetry.total_resistance.sum()
        + telemetry.conductance.sum()
        + telemetry.current.sum()
        + telemetry.attention.sum()
        + telemetry.diagnostic_features.sum()
    )
    gradients = torch.autograd.grad(loss, (drive, capability, readiness, region))
    for gradient in gradients:
        assert gradient[0, 0, 0, 1].item() == 0.0


def test_one_route_resistance_reduces_its_current_and_allocation():
    _, module, x, control = setup_attention(sequence=3)
    _, before = module(x, control)
    capability = control.resistance_capability.clone()
    capability[..., 0] = 4.25
    _, after = module(x, replace(control, resistance_capability=capability))
    assert torch.all(after.current[..., 0] < before.current[..., 0])
    assert torch.all(after.attention[..., 0] < before.attention[..., 0])
    assert torch.all(after.attention[..., 1:] > before.attention[..., 1:])
    assert torch.all(after.total_current < before.total_current)


def test_resistance_log_derivatives_match_the_closed_form_over_1024_cases():
    torch.manual_seed(29)
    cases = 1024
    scores = torch.randn(cases, 2, dtype=DTYPE)
    log_resistance = torch.empty(cases, 2, dtype=DTYPE).uniform_(
        torch.log(torch.tensor(0.1, dtype=DTYPE)),
        torch.log(torch.tensor(10.0, dtype=DTYPE)),
    )
    log_resistance.requires_grad_()
    resistance = log_resistance.exp()
    allocation = torch.softmax(scores - log_resistance, dim=-1)
    route_conductance = resistance.reciprocal()
    own_alpha_gradient = torch.autograd.grad(
        allocation[:, 0].sum(), log_resistance, retain_graph=True
    )[0]
    conductance_gradient = torch.autograd.grad(
        route_conductance[:, 0].sum(), log_resistance
    )[0]
    expected_own = -allocation[:, 0] * (1 - allocation[:, 0])
    expected_other = allocation[:, 0] * allocation[:, 1]
    assert torch.allclose(own_alpha_gradient[:, 0], expected_own, atol=1e-12, rtol=1e-10)
    assert torch.allclose(own_alpha_gradient[:, 1], expected_other, atol=1e-12, rtol=1e-10)
    assert torch.allclose(
        conductance_gradient[:, 0], -route_conductance[:, 0], atol=1e-12, rtol=1e-10
    )
    assert torch.equal(conductance_gradient[:, 1], torch.zeros(cases, dtype=DTYPE))


def test_common_drive_and_joint_drive_resistance_invariances():
    _, module, x, control = setup_attention()
    _, base = module(x, control)
    _, drive_scaled = module(x, replace(control, drive=control.drive * 4))
    assert torch.allclose(base.attention, drive_scaled.attention, atol=1e-12, rtol=1e-10)
    assert torch.allclose(drive_scaled.total_current, base.total_current * 4, atol=1e-12, rtol=1e-10)

    joint = replace(
        control,
        drive=control.drive * 4,
        resistance_capability=control.resistance_capability * 4,
        resistance_policy=control.resistance_policy * 4,
        resistance_context=control.resistance_context * 4,
        resistance_resource=control.resistance_resource * 4,
    )
    _, joint_scaled = module(x, joint)
    assert torch.allclose(base.attention, joint_scaled.attention, atol=1e-12, rtol=1e-10)
    assert torch.allclose(base.total_current, joint_scaled.total_current, atol=1e-12, rtol=1e-10)


def test_causal_fan_in_scales_flow_and_an_explicit_query_budget_normalizes_it():
    _, module, x, control = setup_attention(sequence=4)
    control = replace(control, topology_mask=CASControl.uniform(x, num_heads=2, causal=True).topology_mask)
    _, unbudgeted = module(x, control)
    expected = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=DTYPE)
    assert torch.equal(unbudgeted.total_current[0, 0], expected)

    open_paths = control.path_mask.sum(dim=-1, keepdim=True).to(dtype=DTYPE)
    budgeted_drive = torch.where(
        control.path_mask,
        control.drive / open_paths,
        torch.zeros_like(control.drive),
    )
    _, budgeted = module(x, replace(control, drive=budgeted_drive))
    assert torch.allclose(
        budgeted.total_current,
        torch.ones_like(budgeted.total_current),
        atol=1e-12,
        rtol=1e-10,
    )


def test_semantic_logit_gauge_shift_does_not_change_flow_or_attention():
    torch.manual_seed(31)
    scores = torch.randn(4, 2, 3, 5, dtype=DTYPE)
    drive = torch.rand_like(scores) + 0.5
    resistance = torch.rand_like(scores) + 0.1
    readiness = torch.rand_like(scores) + 0.25
    region = torch.rand_like(scores) + 0.25
    mask = torch.ones_like(scores, dtype=torch.bool)
    first = compiled_ohmic_attention(scores, drive, resistance, readiness, region, mask)
    second = compiled_ohmic_attention(scores + 1000, drive, resistance, readiness, region, mask)
    for left, right in zip(first, second, strict=True):
        assert torch.allclose(left, right, atol=1e-11, rtol=1e-10)


def test_independent_components_survive_only_in_diagnostic_readout_for_equal_ratio():
    _, module, x, control = setup_attention()
    alternative = replace(
        control,
        drive=control.drive * 4,
        resistance_capability=control.resistance_capability * 13,
    )
    # Total R moves from 1 to 4 while V moves from 1 to 4: identical conductance flow.
    _, first = module(x, control)
    _, second = module(x, alternative)
    assert torch.allclose(first.attention, second.attention, atol=1e-12, rtol=1e-10)
    assert torch.allclose(first.total_current, second.total_current, atol=1e-12, rtol=1e-10)
    assert not torch.allclose(first.diagnostic_features, second.diagnostic_features)


def test_invalid_or_nonfinite_control_fails_closed():
    _, module, x, control = setup_attention()
    bad = control.resistance_capability.clone()
    bad.fill_(-1.0)
    with pytest.raises(ValueError, match="nonnegative"):
        module(x, replace(control, resistance_capability=bad))
    nan_drive = control.drive.clone()
    nan_drive[0, 0, 0, 0] = torch.nan
    with pytest.raises(ValueError, match="finite"):
        module(x, replace(control, drive=nan_drive))


def test_same_tick_feedback_is_rejected_and_prior_tick_is_accepted():
    _, module, x, control = setup_attention()
    with pytest.raises(ValueError, match="same-tick"):
        module(
            x,
            replace(control, control_tick=4, feedback_source_tick=4),
        )
    module(x, replace(control, control_tick=4, feedback_source_tick=3))
