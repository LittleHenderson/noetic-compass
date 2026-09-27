"""Numeric tests for the residual world specialist. RESERVED FOR THE AUTHORIZED NUMERICAL VENUE (GPU).

Written 2026-09-27 and NOT RUN anywhere: the preparing container has no torch. The container under test is a
TEST DOUBLE (a small nn.Module carrying a ``world_head`` built exactly as the source defines it, plus two other
tensors); it is not the learner, and no HELM checkpoint is read. Tolerances were fixed in
``growth_migration_plan.TOLERANCES`` before any result: exact equality on the same device for finite inputs.
"""
import pathlib
import sys

import pytest
import torch

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))
import growth_migration_plan as gmp  # noqa: E402
import world_residual_specialist as wrs  # noqa: E402

if not torch.cuda.is_available():
    raise RuntimeError("GPU_REQUIRED: these tests run only in the authorized numerical venue; no CPU fallback")

DEVICE = torch.device("cuda:0")
PARENT_SHA = "5a8a306911bbe50b7d65e13227e8d4acfbaac871f2eb2b0ae0c0f5bb1b6e7341"
CONFIG = {"learning_rate": 0.003, "weight_decay": 0.01, "betas": [0.9, 0.999], "eps": 1e-08}


class DoubleContainer(torch.nn.Module):
    """TEST DOUBLE of the pointer container: the source's world head (lines 856-858) plus two other tensors."""

    def __init__(self):
        super().__init__()
        self.world_projection = torch.nn.Linear(196, 64, bias=False)
        self.world_head = torch.nn.Sequential(
            torch.nn.Linear(gmp.WORLD_CANDIDATE_WIDTH, gmp.WIDTH, bias=False), torch.nn.GELU(),
            torch.nn.LayerNorm(gmp.WIDTH), torch.nn.Linear(gmp.WIDTH, 1, bias=True))
        self.round_mix = torch.nn.Parameter(torch.zeros(8))


def _container():
    torch.manual_seed(7)
    return DoubleContainer().to(DEVICE)


def _inputs(n=6):
    g = torch.Generator(device="cpu").manual_seed(11)
    return torch.randn(n, gmp.WORLD_CANDIDATE_WIDTH, generator=g).to(DEVICE)


def _stepped_optimizer(container, steps=2):
    optimizer = torch.optim.AdamW(list(container.parameters()), lr=CONFIG["learning_rate"],
                                  weight_decay=CONFIG["weight_decay"], betas=tuple(CONFIG["betas"]),
                                  eps=CONFIG["eps"], foreach=False, fused=False, capturable=False)
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        container.world_head(_inputs()).sum().backward()
        (container.world_projection.weight.sum() + container.round_mix.sum()).backward()
        optimizer.step()
    return optimizer


def test_disabled_specialist_returns_the_base_object_unchanged():
    container = _container()
    x = _inputs()
    base = container.world_head(x)
    specialist = wrs.WorldResidualSpecialist(init_seed=20260927, device=DEVICE)
    assert specialist.enabled is False
    assert specialist(x, base) is base


def test_initial_contribution_is_exactly_zero_for_finite_inputs():
    container = _container()
    x = _inputs()
    base = container.world_head(x)
    specialist = wrs.WorldResidualSpecialist(init_seed=20260927, device=DEVICE)
    specialist.enabled = True
    assert torch.equal(specialist.contribution(x, base), torch.zeros_like(base))
    assert torch.equal(specialist(x, base), base + 0.0)
    assert bool((specialist.A.weight != 0).any()) and bool((specialist.B.weight == 0).all())


def test_nonfinite_and_wrong_shape_inputs_are_refused():
    container = _container()
    x = _inputs()
    base = container.world_head(x)
    specialist = wrs.WorldResidualSpecialist(init_seed=20260927, device=DEVICE)
    bad = x.clone()
    bad[0, 0] = float("inf")
    with pytest.raises(gmp.PlanRefused, match="^SPECIALIST_NONFINITE_INPUT"):
        specialist(bad, base)
    with pytest.raises(gmp.PlanRefused, match="^SPECIALIST_INPUT_INVALID"):
        specialist(torch.zeros(6, 40, device=DEVICE), base)
    with pytest.raises(gmp.PlanRefused, match="^SPECIALIST_INPUT_INVALID"):
        specialist(x, base.reshape(-1))


def test_attach_preserves_originals_and_optimizer_state_exactly_and_counts_new_parameters():
    container = _container()
    old_optimizer = _stepped_optimizer(container)
    old_tensors = {name: p.detach().clone() for name, p in container.named_parameters()}
    specialist, plan, mapping = wrs.attach_specialist(container, init_seed=20260927, parent_checkpoint_sha256=PARENT_SHA,
                                                      parent_cursor=2940, device=DEVICE)
    assert plan.expected_new_parameter_count == 624
    new_names = {name for name, _ in container.named_parameters()} - set(old_tensors)
    assert new_names == set(gmp.NEW_PARAMETER_NAMES)
    new_optimizer, log = wrs.migrate_optimizer(old_optimizer, container, optimizer_config=CONFIG, mapping=mapping)
    report = wrs.preservation_report(old_tensors, container, old_optimizer, new_optimizer, mapping)
    assert report["parameters_exactly_equal"] and report["optimizer_state_exactly_equal"]
    assert set(log["carried_by_name"]) == set(old_tensors) and log["original_without_state"] == []
    assert len(new_optimizer.param_groups[0]["params"]) == len(old_tensors) + 2
    for name in gmp.NEW_PARAMETER_NAMES:
        entry = new_optimizer.state_dict()["state"][mapping["new"][name]["new_index"]]
        assert float(entry["step"]) == 0.0 and bool((entry["exp_avg"] == 0).all()) and bool((entry["exp_avg_sq"] == 0).all())
    with pytest.raises(gmp.PlanRefused, match="^SPECIALIST_ALREADY_ATTACHED"):
        wrs.attach_specialist(container, init_seed=1, parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940, device=DEVICE)


def test_save_reload_and_plan_consistency(tmp_path):
    container = _container()
    specialist, plan, mapping = wrs.attach_specialist(container, init_seed=20260927, parent_checkpoint_sha256=PARENT_SHA,
                                                      parent_cursor=2940, device=DEVICE)
    torch.save(container.state_dict(), tmp_path / "grown.pt")
    (tmp_path / "plan.json").write_text(gmp.plan_to_json(plan))
    fresh = _container()
    wrs.attach_specialist(fresh, init_seed=20260927, parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940, device=DEVICE)
    fresh.load_state_dict(torch.load(tmp_path / "grown.pt", map_location=DEVICE, weights_only=True), strict=True)
    assert all(torch.equal(a, b) for (_, a), (_, b) in zip(container.state_dict().items(), fresh.state_dict().items()))
    reloaded = gmp.plan_from_json((tmp_path / "plan.json").read_text())
    assert reloaded == plan and tuple(sorted(container.state_dict())) == plan.learnable_names_after


def test_two_step_trainability_b_first_then_a():
    container = _container()
    old_optimizer = _stepped_optimizer(container, steps=1)
    specialist, plan, mapping = wrs.attach_specialist(container, init_seed=20260927, parent_checkpoint_sha256=PARENT_SHA,
                                                      parent_cursor=2940, device=DEVICE)
    specialist.enabled = True
    optimizer, _ = wrs.migrate_optimizer(old_optimizer, container, optimizer_config=CONFIG, mapping=mapping)
    x = _inputs()
    optimizer.zero_grad(set_to_none=True)
    wrs.scored_world(container, x).sum().backward()
    assert bool((specialist.B.weight.grad != 0).any()), "B receives gradient on step 1"
    assert bool((specialist.A.weight.grad == 0).all()), "A's gradient is exactly zero while B is zero"
    optimizer.step()
    assert bool((specialist.B.weight != 0).any())
    optimizer.zero_grad(set_to_none=True)
    wrs.scored_world(container, x).sum().backward()
    assert bool((specialist.A.weight.grad != 0).any()), "A's gradient is informative once B has updated"


def test_contribution_ablation_after_two_steps():
    container = _container()
    old_optimizer = _stepped_optimizer(container, steps=1)
    specialist, plan, mapping = wrs.attach_specialist(container, init_seed=20260927, parent_checkpoint_sha256=PARENT_SHA,
                                                      parent_cursor=2940, device=DEVICE)
    specialist.enabled = True
    optimizer, _ = wrs.migrate_optimizer(old_optimizer, container, optimizer_config=CONFIG, mapping=mapping)
    x = _inputs()
    for _ in range(2):
        optimizer.zero_grad(set_to_none=True)
        wrs.scored_world(container, x).sum().backward()
        optimizer.step()
    with_specialist = wrs.scored_world(container, x).detach().clone()
    specialist.enabled = False
    without = wrs.scored_world(container, x).detach().clone()
    assert not torch.equal(with_specialist, without), "after two steps the specialist contributes"
