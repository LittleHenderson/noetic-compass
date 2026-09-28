"""Numeric tests for the residual world specialist. RESERVED FOR THE AUTHORIZED NUMERICAL VENUE (GPU).

Written 2026-09-27 (revision 0.2, FORWARD-02) and NOT RUN anywhere: the preparing container has no torch. The
container under test is a TEST DOUBLE (a small nn.Module carrying a ``world_head`` built exactly as the source
defines it, plus two other tensors); it is not the learner, and no HELM checkpoint is read. Tolerances and
preconditions were fixed in ``growth_migration_plan.TOLERANCES`` before any result: exact equality on the same
device when the intermediate is finite. The FORWARD-02 cases cover the four findings of PR #245 comment 5857009736.
"""
import json
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
SEED = gmp.RECORDED_INIT_SEED


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


def _optimizer(params):
    return torch.optim.AdamW(params, lr=CONFIG["learning_rate"], weight_decay=CONFIG["weight_decay"],
                             betas=tuple(CONFIG["betas"]), eps=CONFIG["eps"], foreach=False, fused=False,
                             capturable=False)


def _stepped_optimizer(container, steps=2):
    optimizer = _optimizer(list(container.parameters()))
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        container.world_head(_inputs()).sum().backward()
        (container.world_projection.weight.sum() + container.round_mix.sum()).backward()
        optimizer.step()
    return optimizer


def _attach(container, **kwargs):
    return wrs.attach_specialist(container, init_seed=SEED, parent_checkpoint_sha256=PARENT_SHA, parent_cursor=2940,
                                 device=DEVICE, **kwargs)


def _grown_after_steps(steps=2):
    """Attach, enable, migrate and take ``steps`` optimizer steps so B is nonzero. Returns everything needed."""
    container = _container()
    old_optimizer = _stepped_optimizer(container, steps=1)
    specialist, plan, mapping, old_named = _attach(container)
    specialist.enabled = True
    optimizer, _ = wrs.migrate_optimizer(old_optimizer, container, mapping=mapping, old_named_parameters=old_named,
                                         optimizer_config=CONFIG)
    x = _inputs()
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        wrs.scored_world(container, x).sum().backward()
        optimizer.step()
    assert bool((specialist.B.weight != 0).any()), "precondition: B is nonzero after the steps"
    return container, specialist, plan, mapping, optimizer, x


# ------------------------------------------------------------------------------------ original seven (revised)

def test_disabled_specialist_returns_the_base_object_unchanged():
    container = _container()
    x = _inputs()
    base = container.world_head(x)
    specialist = wrs.WorldResidualSpecialist(init_seed=SEED, device=DEVICE)
    assert specialist.enabled is False
    assert specialist(x, base) is base


def test_initial_contribution_is_exactly_zero_when_the_intermediate_is_finite():
    container = _container()
    x = _inputs()
    base = container.world_head(x)
    specialist = wrs.WorldResidualSpecialist(init_seed=SEED, device=DEVICE)
    specialist.enabled = True
    assert bool(torch.isfinite(specialist.intermediate(x)).all())  # the checked precondition holds for these inputs
    assert torch.equal(specialist.contribution(x, base), torch.zeros_like(base))
    assert torch.equal(specialist(x, base), base + 0.0)
    assert bool((specialist.A.weight != 0).any()) and bool((specialist.B.weight == 0).all())


def test_nonfinite_and_wrong_shape_inputs_are_refused():
    container = _container()
    x = _inputs()
    base = container.world_head(x)
    specialist = wrs.WorldResidualSpecialist(init_seed=SEED, device=DEVICE)
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
    specialist, plan, mapping, old_named = _attach(container)
    assert plan.expected_new_parameter_count == 624
    new_names = {name for name, _ in container.named_parameters()} - set(old_tensors)
    assert new_names == set(gmp.NEW_PARAMETER_NAMES)
    new_optimizer, log = wrs.migrate_optimizer(old_optimizer, container, mapping=mapping, old_named_parameters=old_named,
                                               optimizer_config=CONFIG)
    report = wrs.preservation_report(old_tensors, container, old_optimizer, new_optimizer, mapping)
    assert report["parameters_exactly_equal"] and report["optimizer_state_exactly_equal"]
    assert set(log["carried_by_name"]) == set(old_tensors) and log["original_without_state"] == []
    assert log["old_group_names"] == list(old_tensors) and log["new_group_names"][-2:] == list(gmp.NEW_PARAMETER_NAMES)
    assert len(new_optimizer.param_groups[0]["params"]) == len(old_tensors) + 2
    for name in gmp.NEW_PARAMETER_NAMES:
        entry = new_optimizer.state_dict()["state"][mapping["new"][name]["new_index"]]
        assert float(entry["step"]) == 0.0 and bool((entry["exp_avg"] == 0).all()) and bool((entry["exp_avg_sq"] == 0).all())
        assert entry["step"].device.type == "cpu" and entry["exp_avg"].device == torch.device(DEVICE)
    assert log["placement"]["step_device"] == "cpu" and log["placement"]["moment_devices"] == [str(torch.device(DEVICE))]
    with pytest.raises(gmp.PlanRefused, match="^SPECIALIST_ALREADY_ATTACHED"):
        _attach(container)


def test_state_dict_save_reload_and_plan_consistency(tmp_path):
    container = _container()
    specialist, plan, mapping, _ = _attach(container)
    torch.save(container.state_dict(), tmp_path / "grown.pt")
    (tmp_path / "plan.json").write_text(gmp.plan_to_json(plan))
    fresh = _container()
    _attach(fresh)
    fresh.load_state_dict(torch.load(tmp_path / "grown.pt", map_location=DEVICE, weights_only=True), strict=True)
    assert all(torch.equal(a, b) for (_, a), (_, b) in zip(container.state_dict().items(), fresh.state_dict().items()))
    reloaded = gmp.plan_from_json((tmp_path / "plan.json").read_text())
    assert reloaded == plan and tuple(sorted(container.state_dict())) == plan.learnable_names_after


def test_two_step_trainability_b_first_then_a_under_generic_inputs_and_sum_loss():
    container = _container()
    old_optimizer = _stepped_optimizer(container, steps=1)
    specialist, plan, mapping, old_named = _attach(container)
    specialist.enabled = True
    optimizer, _ = wrs.migrate_optimizer(old_optimizer, container, mapping=mapping, old_named_parameters=old_named,
                                         optimizer_config=CONFIG)
    x = _inputs()
    assert bool((specialist.intermediate(x) != 0).any()), "the stated condition GELU(A x) != 0 holds for these inputs"
    optimizer.zero_grad(set_to_none=True)
    wrs.scored_world(container, x).sum().backward()  # sum loss: dL/dy = 1, the stated nonzero upstream gradient
    assert bool((specialist.B.weight.grad != 0).any()), "B receives gradient on step 1"
    assert bool((specialist.A.weight.grad == 0).all()), "A's gradient is exactly zero while B is zero"
    optimizer.step()
    assert bool((specialist.B.weight != 0).any())
    optimizer.zero_grad(set_to_none=True)
    wrs.scored_world(container, x).sum().backward()
    assert bool((specialist.A.weight.grad != 0).any()), "A's gradient is informative once B has updated"


def test_contribution_ablation_after_two_steps():
    container, specialist, plan, mapping, optimizer, x = _grown_after_steps(steps=2)
    with_specialist = wrs.scored_world(container, x).detach().clone()
    specialist.enabled = False
    without = wrs.scored_world(container, x).detach().clone()
    assert not torch.equal(with_specialist, without), "after two steps the specialist contributes"


# ------------------------------------------------------------------------------------ FORWARD-02: finding 1

def test_finding1_constructing_the_specialist_leaves_cpu_and_cuda_generators_exactly_unchanged():
    torch.manual_seed(12345)
    torch.cuda.manual_seed_all(12345)
    specialist, report = wrs.rng_neutrality_probe(lambda: wrs.WorldResidualSpecialist(init_seed=SEED, device=DEVICE))
    assert report["cpu_rng_unchanged"] is True and report["cuda_rng_unchanged"] is True
    assert report["cuda_generators_checked"] >= 1
    # the next draw from the shared generator is the same as if the specialist had never been built
    torch.manual_seed(12345)
    expected = torch.rand(4)
    torch.manual_seed(12345)
    wrs.WorldResidualSpecialist(init_seed=SEED, device=DEVICE)
    assert torch.equal(torch.rand(4), expected)
    # and the same seed gives the same A, so the initialization is recorded, not incidental
    again = wrs.WorldResidualSpecialist(init_seed=SEED, device=DEVICE)
    assert torch.equal(specialist.A.weight, again.A.weight) and bool((again.B.weight == 0).all())


def test_finding1_counterexample_of_the_0_1_layout_is_detected_by_the_probe():
    """The probe must catch an unguarded constructor: a plain Linear built outside any fork consumes the CPU RNG."""
    torch.manual_seed(1)
    _, report = wrs.rng_neutrality_probe(lambda: torch.nn.Linear(16, 1, bias=False))
    assert report["cpu_rng_unchanged"] is False


# ------------------------------------------------------------------------------------ FORWARD-02: finding 2

def test_finding2_migration_refuses_a_group_that_is_not_the_verified_parameter_set():
    container = _container()
    params = list(container.parameters())
    reordered = _optimizer(params[::-1])
    subset = _optimizer(params[:-1])
    foreign = _optimizer(params + [torch.nn.Parameter(torch.zeros(3, device=DEVICE))])
    duplicate = _optimizer(params + [params[0]])
    specialist, plan, mapping, old_named = _attach(container)
    with pytest.raises(gmp.PlanRefused, match="^OPTIMIZER_BINDING_INVALID: old index"):
        wrs.migrate_optimizer(reordered, container, mapping=mapping, old_named_parameters=old_named)
    with pytest.raises(gmp.PlanRefused, match="^OPTIMIZER_BINDING_INVALID: module parameters absent"):
        wrs.migrate_optimizer(subset, container, mapping=mapping, old_named_parameters=old_named)
    with pytest.raises(gmp.PlanRefused, match="^OPTIMIZER_BINDING_INVALID: foreign"):
        wrs.migrate_optimizer(foreign, container, mapping=mapping, old_named_parameters=old_named)
    with pytest.raises(gmp.PlanRefused, match="^OPTIMIZER_BINDING_INVALID: duplicate"):
        wrs.migrate_optimizer(duplicate, container, mapping=mapping, old_named_parameters=old_named)
    with pytest.raises(gmp.PlanRefused, match="^OPTIMIZER_BINDING_INVALID"):  # post-attach names are not the old set
        wrs.migrate_optimizer(_optimizer(params), container, mapping=mapping,
                              old_named_parameters=tuple(container.named_parameters()))


def test_finding2_group_settings_come_from_the_old_group_and_a_differing_config_is_refused():
    container = _container()
    old_optimizer = _stepped_optimizer(container, steps=1)
    old_optimizer.param_groups[0]["initial_lr"] = 0.003  # an extra key, as a scheduler would leave behind
    old_optimizer.param_groups[0]["lr"] = 0.001  # the group is the truth, not the config
    specialist, plan, mapping, old_named = _attach(container)
    with pytest.raises(gmp.PlanRefused, match="^OPTIMIZER_CONFIG_MISMATCH: learning_rate=0.003"):
        wrs.migrate_optimizer(old_optimizer, container, mapping=mapping, old_named_parameters=old_named,
                              optimizer_config=CONFIG)
    new_optimizer, log = wrs.migrate_optimizer(old_optimizer, container, mapping=mapping, old_named_parameters=old_named,
                                               optimizer_config=dict(CONFIG, learning_rate=0.001))
    new_group = new_optimizer.param_groups[0]
    for key, value in gmp.group_settings(old_optimizer.param_groups[0]).items():
        assert key in new_group and (list(value) == list(new_group[key]) if isinstance(value, (tuple, list)) else new_group[key] == value)
    assert new_group["lr"] == 0.001 and new_group["initial_lr"] == 0.003 and new_group["foreach"] is False
    assert "initial_lr" in log["settings_preserved"]


# ------------------------------------------------------------------------------------ FORWARD-02: finding 3

def test_finding3_enabled_nonzero_b_and_optimizer_state_survive_save_and_reload_together(tmp_path):
    container, specialist, plan, mapping, optimizer, x = _grown_after_steps(steps=2)
    before_output = wrs.scored_world(container, x).detach().clone()
    before_state = {k: v.detach().clone() for k, v in container.state_dict().items()}
    before_optimizer = optimizer.state_dict()
    sidecar = wrs.save_grown(container, optimizer, plan, tmp_path)
    assert sidecar["enabled"] is True and sidecar["init_seed"] == SEED and sidecar["hidden"] == gmp.SPECIALIST_HIDDEN
    assert set(json.loads((tmp_path / gmp.SIDECAR_FILE).read_text())["files"]) == {gmp.GROWN_STATE_FILE, gmp.GROWN_OPTIMIZER_FILE}
    fresh = _container()
    specialist2, optimizer2, sidecar2, plan2 = wrs.load_grown(fresh, tmp_path, device=DEVICE)
    assert sidecar2 == sidecar and plan2 == plan
    assert specialist2.enabled is True and bool((specialist2.B.weight != 0).any())
    for name, tensor in fresh.state_dict().items():
        assert torch.equal(tensor, before_state[name]), name
    after_optimizer = optimizer2.state_dict()
    assert set(after_optimizer["state"]) == set(before_optimizer["state"])
    for index, entry in before_optimizer["state"].items():
        for key, value in entry.items():
            other = after_optimizer["state"][index][key]
            if torch.is_tensor(value):
                # device and dtype are part of exactness: the real job's failure was a CPU step versus a CUDA step
                assert value.device == other.device and value.dtype == other.dtype, (index, key, value.device, other.device)
                assert torch.equal(value, other), (index, key)
            else:
                assert value == other, (index, key)
        assert entry["step"].device.type == "cpu" and after_optimizer["state"][index]["step"].device.type == "cpu", index
        for key in ("exp_avg", "exp_avg_sq"):
            assert after_optimizer["state"][index][key].device == torch.device(DEVICE), (index, key)
    assert wrs.verify_optimizer_placement(optimizer2)["step_device"] == "cpu"
    old_group = {k: v for k, v in before_optimizer["param_groups"][0].items() if k != "params"}
    gmp.settings_preserved(old_group, optimizer2.param_groups[0])
    assert torch.equal(wrs.scored_world(fresh, x).detach(), before_output)
    # one more step on both must keep them identical (same state, same settings, same parameters, same device)
    for opt, cont in ((optimizer, container), (optimizer2, fresh)):
        opt.zero_grad(set_to_none=True)
        wrs.scored_world(cont, x).sum().backward()
        opt.step()
    assert torch.equal(specialist.B.weight, specialist2.B.weight) and torch.equal(specialist.A.weight, specialist2.A.weight)


def test_finding3_missing_or_tampered_sidecar_and_files_are_refused(tmp_path):
    container, specialist, plan, mapping, optimizer, x = _grown_after_steps(steps=1)
    with pytest.raises(gmp.PlanRefused, match="^SIDECAR_MISSING"):
        wrs.load_grown(_container(), tmp_path / "nothing_here", device=DEVICE)
    wrs.save_grown(container, optimizer, plan, tmp_path)
    data = json.loads((tmp_path / gmp.SIDECAR_FILE).read_text())
    data["enabled"] = False
    (tmp_path / gmp.SIDECAR_FILE).write_text(json.dumps(data))
    with pytest.raises(gmp.PlanRefused, match="^SIDECAR_MISMATCH: sidecar_digest"):
        wrs.load_grown(_container(), tmp_path, device=DEVICE)
    wrs.save_grown(container, optimizer, plan, tmp_path)
    with open(tmp_path / gmp.GROWN_OPTIMIZER_FILE, "ab") as handle:
        handle.write(b"\x00")
    with pytest.raises(gmp.PlanRefused, match="^SIDECAR_MISMATCH: grown_optimizer.pt"):
        wrs.load_grown(_container(), tmp_path, device=DEVICE)
    with pytest.raises(gmp.PlanRefused, match="^SPECIALIST_NOT_ATTACHED"):
        wrs.save_grown(_container(), optimizer, plan, tmp_path / "other")


# ------------------------------------------------------------------------------------ FORWARD-02: finding 4

def test_finding4_extreme_finite_input_overflows_the_intermediate_and_is_refused_before_b():
    specialist = wrs.WorldResidualSpecialist(init_seed=SEED, device=DEVICE)
    specialist.enabled = True
    with torch.no_grad():
        specialist.A.weight.fill_(1.0)  # the recorded counterexample: A = ones
    x = torch.full((2, gmp.WORLD_CANDIDATE_WIDTH), torch.finfo(torch.float32).max, device=DEVICE)
    base = torch.zeros(2, 1, device=DEVICE)
    assert bool(torch.isfinite(x).all()), "the input passes the input check"
    raw = specialist.gelu(specialist.A(x))
    assert not bool(torch.isfinite(raw).all()), "A x overflows to inf for a finite input"
    assert bool(torch.isnan(specialist.B(raw)).any()), "without the check, 0.0 x inf = nan would be returned"
    with pytest.raises(gmp.PlanRefused, match="^SPECIALIST_NONFINITE_INTERMEDIATE"):
        specialist(x, base)
    with pytest.raises(gmp.PlanRefused, match="^SPECIALIST_NONFINITE_INTERMEDIATE"):
        specialist.contribution(x, base)


def test_finding4_zero_input_and_zero_upstream_gradient_leave_b_without_gradient():
    specialist = wrs.WorldResidualSpecialist(init_seed=SEED, device=DEVICE)
    specialist.enabled = True
    base = torch.zeros(3, 1, device=DEVICE)
    zero_x = torch.zeros(3, gmp.WORLD_CANDIDATE_WIDTH, device=DEVICE)
    specialist(zero_x, base).sum().backward()  # x = 0: GELU(0) = 0, so dL/dB = 0 even with dL/dy = 1
    assert bool((specialist.B.weight.grad == 0).all())
    specialist.zero_grad(set_to_none=True)
    x = _inputs(3)
    (specialist(x, base) * 0.0).sum().backward()  # zero upstream gradient: dL/dB = 0 for generic x
    assert bool((specialist.B.weight.grad == 0).all())
    specialist.zero_grad(set_to_none=True)
    specialist(x, base).sum().backward()  # the stated conditions: generic nonzero x and dL/dy = 1
    assert bool((specialist.B.weight.grad != 0).any())


def test_finding3_reload_keeps_cpu_step_and_device_moments_and_the_0_2_defect_is_reproduced(tmp_path):
    """Revision 0.3 regression for the real failure in job helm-growth15-c70e1a-20260928-a1 (14 passed, 1 failed at
    c70e1a04): loading the optimizer file with map_location=<cuda> moved the CPU scalar step to CUDA."""
    container, specialist, plan, mapping, optimizer, x = _grown_after_steps(steps=2)
    assert wrs.verify_optimizer_placement(optimizer)["step_device"] == "cpu"  # the source's AdamW keeps step on CPU
    wrs.save_grown(container, optimizer, plan, tmp_path)
    # the 0.2 defect, reproduced on purpose: a device map_location moves step to CUDA
    moved = torch.load(tmp_path / gmp.GROWN_OPTIMIZER_FILE, map_location=DEVICE, weights_only=True)
    first = next(iter(moved["state"].values()))
    assert first["step"].device.type == "cuda", "map_location=<cuda> relocates the scalar step: the defect's mechanism"
    # the 0.3 loader keeps CPU step and device moments, and every value is exactly equal
    fresh = _container()
    specialist2, optimizer2, sidecar2, plan2 = wrs.load_grown(fresh, tmp_path, device=DEVICE)
    placement = wrs.verify_optimizer_placement(optimizer2)
    assert placement["step_device"] == "cpu" and placement["moment_devices"] == [str(torch.device(DEVICE))]
    assert placement["entries_with_state"] == len(optimizer2.param_groups[0]["params"])
    before, after = optimizer.state_dict()["state"], optimizer2.state_dict()["state"]
    for index in before:
        for key in ("step", "exp_avg", "exp_avg_sq"):
            assert before[index][key].device == after[index][key].device and torch.equal(before[index][key], after[index][key]), (index, key)
    # an optimizer whose step was relocated is refused by the verifier
    bad = torch.optim.AdamW(list(fresh.parameters()), foreach=False, fused=False, capturable=False)
    bad.load_state_dict(moved)
    with torch.no_grad():
        for entry in bad.state.values():
            entry["step"] = entry["step"].to(DEVICE)
    with pytest.raises(gmp.PlanRefused, match="^OPTIMIZER_STATE_INCOMPATIBLE: step"):
        wrs.verify_optimizer_placement(bad)
