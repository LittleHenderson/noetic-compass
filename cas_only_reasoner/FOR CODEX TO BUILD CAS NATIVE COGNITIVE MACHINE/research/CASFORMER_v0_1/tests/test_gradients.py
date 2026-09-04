from __future__ import annotations

from dataclasses import replace

import torch

from casformer import CASControl, CASformerBlock, CASformerConfig
from casformer.baselines import compiled_ohmic_attention


DTYPE = torch.float64


def test_router_passes_first_and_second_order_gradchecks():
    torch.manual_seed(37)
    scores = torch.randn(1, 1, 2, 3, dtype=DTYPE, requires_grad=True)
    log_drive = torch.randn(1, 1, 2, 3, dtype=DTYPE, requires_grad=True)
    log_resistance = torch.randn(1, 1, 2, 3, dtype=DTYPE, requires_grad=True)
    readiness = torch.full_like(scores, 0.8)
    region = torch.full_like(scores, 0.9)
    mask = torch.ones_like(scores, dtype=torch.bool)

    def route(score, authored_log_drive, authored_log_resistance):
        return compiled_ohmic_attention(
            score,
            authored_log_drive.exp(),
            authored_log_resistance.exp(),
            readiness,
            region,
            mask,
        )

    assert torch.autograd.gradcheck(route, (scores, log_drive, log_resistance), fast_mode=True)
    assert torch.autograd.gradgradcheck(
        route, (scores, log_drive, log_resistance), fast_mode=True
    )


def test_full_smooth_block_passes_input_and_drive_gradcheck():
    torch.manual_seed(41)
    config = CASformerConfig(
        d_model=2,
        num_heads=1,
        num_relations=1,
        num_layers=1,
        d_ff=3,
        initial_cutoff=0.1,
        initial_saturation=5.0,
    )
    block = CASformerBlock(config).to(dtype=DTYPE).eval()
    x = torch.randn(1, 2, 2, dtype=DTYPE, requires_grad=True)
    drive = torch.full((1, 1, 2, 2), 0.7, dtype=DTYPE, requires_grad=True)
    control = CASControl.uniform(x.detach(), num_heads=1, drive=0.7)

    def execute(hidden, authored_drive):
        return block(hidden, replace(control, drive=authored_drive))[0]

    assert torch.autograd.gradcheck(execute, (x, drive), fast_mode=True)


def test_all_closed_attention_has_finite_backward_path():
    torch.manual_seed(43)
    config = CASformerConfig(d_model=4, num_heads=1, num_relations=1, d_ff=8)
    block = CASformerBlock(config).to(dtype=DTYPE)
    x = torch.randn(2, 3, 4, dtype=DTYPE, requires_grad=True)
    control = CASControl.uniform(x, num_heads=1)
    closed = torch.zeros_like(control.topology_mask)
    output, telemetry = block(x, replace(control, topology_mask=closed))
    output.square().sum().backward()
    assert torch.isfinite(output).all()
    assert torch.isfinite(x.grad).all()
    assert torch.equal(telemetry.attention.attention, torch.zeros_like(telemetry.attention.attention))
    assert torch.equal(telemetry.cjt_effect, torch.zeros_like(telemetry.cjt_effect))

