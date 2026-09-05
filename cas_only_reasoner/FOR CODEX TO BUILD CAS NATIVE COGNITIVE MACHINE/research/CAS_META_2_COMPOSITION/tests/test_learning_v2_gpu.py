"""AWS-only v2 preflight tests. Never import Torch on local pure test runs."""

import json
import os
import time

import pytest

pytestmark = pytest.mark.gpu
if os.environ.get("CAS_META2_RUN_GPU_TESTS") != "1":
    pytest.skip("AWS GPU test authorization flag required", allow_module_level=True)

import torch

from cas_meta2.gpu_preflight_v2 import GPUPreflightError, run_preflight
from cas_meta2.policy import PolicyConfig, require_cuda
from cas_meta2.train_v2 import TrainingConfig, setup_cuda


def _training_fixture():
    # Synthetic training-only rows test this helper. The campaign separately
    # passes its actual 768 training tasks, not these fixtures.
    program = {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A", "B"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"}], "return": "v1"},
        "p0": {"input": "arg", "allowed_cjts": ["B"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}
    return [{"public": {
        "problem": "Use " + ("amber", "Blue", "green")[index % 3] + ". Run A; then CALL p0 for B. " + "Exact " * (index + 1),
        "observations": [{"slot": slot, "tag": tag,
                          "values": [(slot + 1) * (axis + 1) / 30 for axis in range(8)]}
                         for slot, tag in enumerate(("amber", "Blue", "green"))]},
        "target": {"binding": index % 3, "program": program}} for index in range(16)]


def test_preflight_uses_lossless_registered_geometry_and_releases_memory(tmp_path, record_property):
    require_cuda()
    setup_cuda(7)
    config = TrainingConfig(policy=PolicyConfig(max_length=1024, max_action_length=256))
    receipt = run_preflight(_training_fixture(), config, tmp_path, time.monotonic() + 180)
    assert receipt["status"] == "CAS_META_2_V2_GPU_PREFLIGHT_PASSED"
    assert receipt["completed"] is True
    assert receipt["geometry"]["training_examples"] == 16
    assert receipt["geometry"]["batch_size"] == 16
    assert receipt["geometry"]["configured_input_limit"] == 1024
    assert receipt["geometry"]["selected_training_indices"] == list(reversed(range(16)))
    assert receipt["optimizer_updates"] == 0
    assert receipt["held_out_labels_accessed"] is False
    assert set(receipt["families"]) == {"cas", "generic"}
    for family in receipt["families"].values():
        assert family["all_parameters_cuda"] and family["all_buffers_cuda"]
        assert family["all_trainable_parameter_tensors_have_finite_nonzero_gradient"]
        assert not family["missing_or_invalid_gradient_parameter_names"]
    assert receipt["identical_common_initial_parameter_names"]
    assert len(receipt["families"]["cas"]["gate_layers"]) == 2
    assert all(row["active_fraction"] >= 0.95 for row in receipt["families"]["cas"]["gate_layers"])
    assert receipt["peak_cuda_allocated_bytes"] > 0
    assert receipt["peak_cuda_reserved_bytes"] >= receipt["peak_cuda_allocated_bytes"]
    assert receipt["cuda_allocated_bytes_after_cleanup"] == receipt["cuda_allocated_bytes_before"]
    assert json.loads((tmp_path / "gpu_preflight_v2.json").read_text()) == receipt
    record_property("v2_synthetic_training_geometry_preflight", json.dumps(receipt, sort_keys=True))


def test_preflight_rejects_missing_authorization_before_model_construction(tmp_path, monkeypatch):
    def no_construction(*args, **kwargs):
        raise AssertionError("A model was constructed before AWS authorization")
    monkeypatch.setattr(torch.nn.Module, "__init__", no_construction)
    monkeypatch.delenv("CAS_META2_RUN_GPU_TESTS", raising=False)
    with pytest.raises(GPUPreflightError, match="AWS_AUTHORIZATION_REQUIRED"):
        run_preflight([], None, tmp_path, time.monotonic() + 30)
    receipt = json.loads((tmp_path / "gpu_preflight_v2.json").read_text())
    assert receipt["completed"] is False
    assert receipt["status"] == "CAS_META_2_V2_GPU_PREFLIGHT_FAILED"
    assert receipt["stage"] == "authorization"
    assert "peak_cuda_allocated_bytes" not in receipt
    assert receipt["optimizer_updates"] == 0
