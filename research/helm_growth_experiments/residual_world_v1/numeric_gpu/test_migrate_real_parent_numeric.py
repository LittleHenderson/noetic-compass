"""Reserved GPU tests for the L2 driver on a LABELED TEST-DOUBLE LOADER. Written 2026-09-28, NOT RUN anywhere.

The loader double has the exact keyword signature of ``PointerCourseLearner.restore_checkpoint`` (pointer_learner.py
2144-2145 at c45f775f), verifies the copy's sha256 like the real loader, and returns a double learner whose ``module``
is a small container with the source's world head. No HELM checkpoint is read; the "parent copy" is a file of
arbitrary bytes written by the test. These cases show the driver's mechanics, not a real migration (L2 needs the
real loader, framework, encoder and a real parent copy in the runner job). NOT part of the 15-case package.
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
import migrate_real_parent as mrp  # noqa: E402
import world_residual_specialist as wrs  # noqa: E402

if not torch.cuda.is_available():
    raise RuntimeError("GPU_REQUIRED: these tests run only in the authorized numerical venue; no CPU fallback")

DEVICE = "cuda:0"
DIGEST = "ab" * 32
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


class DoubleLearner:
    """TEST DOUBLE of the restored learner: only the interface the driver reads."""

    def __init__(self, device, *, foreign_optimizer=False):
        torch.manual_seed(7)
        self.module = DoubleContainer().to(device)
        params = list(self.module.parameters())
        if foreign_optimizer:
            params = params + [torch.nn.Parameter(torch.zeros(3, device=device))]
        self.optimizer = torch.optim.AdamW(params, lr=0.003, weight_decay=0.01, betas=(0.9, 0.999), eps=1e-08,
                                           foreach=False, fused=False, capturable=False)
        self.optimizer.zero_grad(set_to_none=True)
        self.module.world_head(torch.randn(4, gmp.WORLD_CANDIDATE_WIDTH, device=device)).sum().backward()
        (self.module.world_projection.weight.sum() + self.module.round_mix.sum()).backward()
        self.optimizer.step()
        self.optimizer_config = dict(CONFIG)
        self.cursor = self.model_revision = 2940
        self.run_identity_digest = DIGEST


def make_restore_double(calls, *, foreign_optimizer=False):
    def restore(torch_, framework, encoder, *, path, expected_sha256, expected_run_identity_digest, device,
                expected_learnable_names=None):
        calls.append({"path": path, "expected_sha256": expected_sha256, "names": expected_learnable_names})
        assert gmp.file_sha256(path) == expected_sha256, "the double verifies bytes like the real loader"
        return DoubleLearner(device, foreign_optimizer=foreign_optimizer)
    return restore


def _parent(tmp_path):
    directory = tmp_path / "parent_copy_dir"
    directory.mkdir()
    path = directory / "parent_copy.pt"
    path.write_bytes(b"\x07\x11" * 4096)
    return path, gmp.file_sha256(path)


def _names(device):
    torch.manual_seed(7)
    return tuple(sorted(DoubleContainer().to(device).state_dict()))


def _run(tmp_path, **overrides):
    calls = []
    path, sha = _parent(tmp_path)
    args = dict(torch=torch, restore=make_restore_double(calls), framework=object(), encoder=object(),
                parent_copy_path=path, expected_sha256=sha, expected_run_identity_digest=DIGEST,
                expected_learnable_names=_names(DEVICE), device=DEVICE, out_dir=tmp_path / "out" / "grown",
                probe_batch=torch.randn(5, gmp.WORLD_CANDIDATE_WIDTH, device=DEVICE), venue="TEST_DOUBLE_LOADER_GPU")
    args.update(overrides)
    return calls, args


def test_full_driver_run_on_the_double_loader_writes_rollback_record_and_grown_candidate(tmp_path):
    calls, args = _run(tmp_path)
    record = mrp.run_real_parent_migration(**args)
    out = args["out_dir"]
    assert len(calls) == 1 and calls[0]["expected_sha256"] == args["expected_sha256"]
    assert calls[0]["names"] == list(args["expected_learnable_names"])
    rollback = json.loads((out / mrp.ROLLBACK_FILE).read_text())
    assert rollback["rollback_parent"]["sha256"] == args["expected_sha256"] and rollback["cursor"] == 2940
    assert record["preservation"]["parameters_exactly_equal"] and record["preservation"]["optimizer_state_exactly_equal"]
    assert record["probe"] == {"rows": 5, "same_object": True, "torch_equal": True}
    assert record["specialist"]["enabled"] is False and record["specialist"]["new_parameter_count"] == 624
    assert record["mapping"]["new_group_parameters"] == record["mapping"]["old_group_parameters"] + 2
    assert record["claim_boundary"]["forward_path_integration"].startswith("NOT_DONE")
    for name in mrp.GROWN_FILES:
        assert gmp.file_sha256(out / mrp.GROWN_DIR / name) == record["grown_candidate"]["files_sha256"][name]
    assert mrp.verify_record(json.loads((out / mrp.RECORD_FILE).read_text()))
    # the grown candidate reloads into a fresh double container, disabled, with the migrated optimizer
    torch.manual_seed(7)
    fresh = DoubleContainer().to(DEVICE)
    specialist, optimizer, sidecar, plan = wrs.load_grown(fresh, out / mrp.GROWN_DIR, device=DEVICE)
    assert specialist.enabled is False and sidecar["sidecar_digest"] == record["grown_candidate"]["sidecar_digest"]
    assert len(optimizer.param_groups[0]["params"]) == record["mapping"]["new_group_parameters"]
    # the parent copy is untouched
    assert gmp.file_sha256(args["parent_copy_path"]) == args["expected_sha256"]


def test_driver_refuses_a_loader_whose_optimizer_group_is_not_the_container(tmp_path):
    calls, args = _run(tmp_path)
    args["restore"] = make_restore_double(calls, foreign_optimizer=True)
    with pytest.raises(gmp.PlanRefused, match="^OPTIMIZER_BINDING_INVALID: foreign"):
        mrp.run_real_parent_migration(**args)
    assert not (args["out_dir"] / mrp.GROWN_DIR).exists()  # nothing grown was written


def test_driver_refuses_when_the_restored_layout_differs_from_the_declared_names(tmp_path):
    calls, args = _run(tmp_path)
    args["expected_learnable_names"] = tuple(list(args["expected_learnable_names"]) + ["extra.weight"])
    with pytest.raises(mrp.DriverRefused, match="^PARENT_LAYOUT_MISMATCH"):
        mrp.run_real_parent_migration(**args)


def test_driver_refuses_an_infinite_probe_batch_before_restoring(tmp_path):
    calls, args = _run(tmp_path)
    bad = args["probe_batch"].clone()
    bad[0, 0] = float("inf")
    args["probe_batch"] = bad
    with pytest.raises(mrp.DriverRefused, match="^PROBE_BATCH_INVALID"):
        mrp.run_real_parent_migration(**args)
    assert calls == []
