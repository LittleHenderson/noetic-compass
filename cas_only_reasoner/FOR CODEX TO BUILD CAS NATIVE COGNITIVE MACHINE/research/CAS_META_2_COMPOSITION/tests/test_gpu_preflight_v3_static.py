"""Pure simulated CUDA accounting tests. Never import Torch or create tensors."""
import ast
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from cas_meta2 import gpu_preflight_v3 as preflight


class FakeCUDA:
    """Accounting-only fake; workspace bytes are distinct from live tensors."""
    def __init__(self, workspace=0, live=0):
        self.workspace, self.live = workspace, live
        self.reserved = workspace + live
        self.peak_allocated = self.reserved
        self.peak_reserved = self.reserved
        self.events = []
        self.available, self.devices = True, 1
        self.name = "NVIDIA RTX PRO 4500 Blackwell Server Edition"
        self.clear_failure = False

    def is_available(self):
        return self.available

    def device_count(self):
        return self.devices

    def get_device_properties(self, device):
        return SimpleNamespace(name=self.name, total_memory=32 * 1024**3)

    def memory_allocated(self, device):
        return self.workspace + self.live

    def memory_reserved(self, device):
        return self.reserved

    def max_memory_allocated(self, device):
        return self.peak_allocated

    def max_memory_reserved(self, device):
        return self.peak_reserved

    def reset_peak_memory_stats(self, device):
        self.events.append("reset_peak")
        self.peak_allocated, self.peak_reserved = self.workspace + self.live, self.reserved

    def synchronize(self, device):
        self.events.append("synchronize")

    def clear_workspaces(self):
        self.events.append("clear_workspaces")
        if self.clear_failure:
            raise RuntimeError("FAKE_WORKSPACE_CLEAR_FAILURE")
        self.workspace = 0

    def empty_cache(self):
        self.events.append("empty_cache")
        self.reserved = self.workspace + self.live


def fake_torch(cuda):
    return SimpleNamespace(__version__=preflight.TORCH_VERSION,
        version=SimpleNamespace(cuda=preflight.CUDA_VERSION), cuda=cuda,
        device=lambda value: value,
        _C=SimpleNamespace(_cuda_clearCublasWorkspaces=cuda.clear_workspaces),
        are_deterministic_algorithms_enabled=lambda: True,
        backends=SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=False)),
            cudnn=SimpleNamespace(allow_tf32=False, benchmark=False, deterministic=True)))


@pytest.fixture
def simulation(monkeypatch):
    monkeypatch.setenv("CAS_META2_RUN_GPU_TESTS", "1")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", "cas-meta2-v3-fixture-only")
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    cuda = FakeCUDA()
    runtime = fake_torch(cuda)
    monkeypatch.setattr(preflight, "_load_runtime", lambda: runtime)
    monkeypatch.setattr(preflight.gc, "collect", lambda: cuda.events.append("gc"))
    def geometry(tasks, config, receipt, deadline, torch, device):
        assert torch is runtime
        assert cuda.workspace == cuda.live == 0
        cuda.events.append("geometry")
        cuda.workspace = 68157440  # The saved v2 residue, simulated rather than allocated.
        cuda.reserved = 96468992
        cuda.peak_allocated, cuda.peak_reserved = 6415442432, 6981419008
        receipt["geometry"] = {"fixture_only": True, "batch_size": 16}
    monkeypatch.setattr(preflight, "_run_geometry", geometry)
    return runtime, cuda


def read_receipt(output):
    return json.loads((output / "gpu_preflight_v3.json").read_bytes())


def test_dependency_pins_match_current_files_and_real_frozen_git_objects():
    identity = preflight._source_identity()
    assert identity["declared_source_sha"] == "410bce98307a5644db51928459b73391c7066b72"
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=preflight.ROOT, text=True).strip())
    for name, expected in preflight.PINNED_GEOMETRY_FILES.items():
        relative = (preflight.ROOT / name).relative_to(repo).as_posix()
        raw = subprocess.check_output(["git", "show", identity["declared_source_sha"] + ":" + relative], cwd=repo)
        assert sha256(raw).hexdigest() == expected


def test_module_is_pure_and_does_not_change_frozen_v2_or_deterministic_environment():
    source = Path(preflight.__file__).read_text()
    tree = ast.parse(source)
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert not any((isinstance(node, ast.Import) and any(item.name == "torch" for item in node.names))
                   or (isinstance(node, ast.ImportFrom) and node.module == "torch") for node in imports)
    assert 'os.environ["CUBLAS_WORKSPACE_CONFIG"] =' not in source
    assert "gpu_preflight_v2.json" not in source
    assert "clear_documented_cublas_and_cublaslt_workspaces" in source
    assert "optimizer.step(" not in source


@pytest.mark.parametrize("entry_workspace", [0, 68157440])
def test_cold_and_warm_accounting_use_zero_baseline_and_return_to_zero(tmp_path, simulation, entry_workspace):
    _, cuda = simulation
    cuda.workspace = cuda.reserved = entry_workspace
    settings = os.environ["CUBLAS_WORKSPACE_CONFIG"]
    result = preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert result == read_receipt(tmp_path)
    assert result["status"] == "CAS_META_2_V3_GPU_PREFLIGHT_PASSED" and result["completed"] is True
    assert result["entry_memory"]["allocated_bytes"] == entry_workspace
    assert result["cuda_allocated_bytes_before"] == result["cuda_allocated_bytes_after_cleanup"] == 0
    assert result["cuda_reserved_bytes_after_cleanup"] == 0
    assert result["numerical_settings_before"] == result["numerical_settings_after"]
    assert result["memory_cleanup_confirmed"] is True
    assert cuda.events == ["synchronize", "gc", "clear_workspaces", "empty_cache", "synchronize", "reset_peak",
                           "geometry", "synchronize", "gc", "clear_workspaces", "empty_cache", "synchronize"]
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == settings
    assert result["candidate_only"] is True and result["wired_into_frozen_v2"] is False
    assert result["optimizer_updates"] == 0


def test_repeated_calls_do_not_accumulate_simulated_workspaces(tmp_path, simulation):
    _, cuda = simulation
    results = []
    for index in range(3):
        output = tmp_path / str(index)
        output.mkdir()
        results.append(preflight.run_preflight([], None, output, time.monotonic() + 20))
        assert cuda.workspace == cuda.live == 0
    assert all(item["entry_memory"]["allocated_bytes"] == 0 for item in results)


def test_residual_live_allocation_is_a_saved_failure_not_a_pass(tmp_path, simulation, monkeypatch):
    _, cuda = simulation
    original = preflight._run_geometry
    def leaked(*args):
        original(*args)
        cuda.live = 4096
    monkeypatch.setattr(preflight, "_run_geometry", leaked)
    with pytest.raises(preflight.GPUPreflightError, match="MEMORY_CLEANUP_UNCONFIRMED"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    result = read_receipt(tmp_path)
    assert result["geometry_checks_completed"] is True
    assert result["completed"] is False and result["status"] == "CAS_META_2_V3_GPU_PREFLIGHT_FAILED"
    assert result["cuda_allocated_bytes_after_cleanup"] == 4096
    assert cuda.live == 4096  # The helper does not destroy someone else's tensor.
    assert result["failures"][0]["stage"] == "final_cleanup"


def test_preexisting_live_allocations_refuse_geometry_without_deleting_them(tmp_path, simulation):
    _, cuda = simulation
    cuda.live = 4096
    with pytest.raises(preflight.GPUPreflightError, match="PROCESS_NOT_IDLE"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    result = read_receipt(tmp_path)
    assert "geometry" not in cuda.events and cuda.live == 4096
    assert result["completed"] is False and result["geometry_checks_completed"] is False
    assert result["entry_memory"]["allocated_bytes"] == 4096


def test_workspace_clear_exception_is_receipted_and_never_passes(tmp_path, simulation):
    _, cuda = simulation
    cuda.clear_failure = True
    with pytest.raises(preflight.GPUPreflightError, match="FAKE_WORKSPACE_CLEAR_FAILURE"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    result = read_receipt(tmp_path)
    assert result["completed"] is False and "geometry" not in cuda.events
    assert result["cleanup"]["baseline"]["completed"] is False
    assert result["failures"]


@pytest.mark.parametrize("version,cuda_version", [("2.10.0+cu128", "12.8"), ("2.11.0+cpu", None),
                                                  ("2.11.0+cu130", "13.0")])
def test_unknown_runtime_versions_fail_before_geometry_or_cleanup(tmp_path, simulation, version, cuda_version):
    runtime, cuda = simulation
    runtime.__version__, runtime.version.cuda = version, cuda_version
    with pytest.raises(preflight.GPUPreflightError, match="UNSUPPORTED_RUNTIME_VERSION"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert cuda.events == [] and read_receipt(tmp_path)["completed"] is False


@pytest.mark.parametrize("api", [None, 17, "not callable"])
def test_unavailable_documented_api_fails_closed_before_cuda_work(tmp_path, simulation, api):
    runtime, cuda = simulation
    runtime._C._cuda_clearCublasWorkspaces = api
    with pytest.raises(preflight.GPUPreflightError, match="WORKSPACE_CLEAR_API_UNAVAILABLE"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert cuda.events == [] and read_receipt(tmp_path)["completed"] is False


@pytest.mark.parametrize("available,count,name", [(False, 1, "RTX"), (True, 2, "RTX"), (True, 1, "Tesla T4")])
def test_unavailable_multiple_or_t4_devices_never_run_geometry(tmp_path, simulation, available, count, name):
    _, cuda = simulation
    cuda.available, cuda.devices, cuda.name = available, count, name
    with pytest.raises(preflight.GPUPreflightError):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert cuda.events == [] and read_receipt(tmp_path)["completed"] is False


def test_authorization_is_checked_before_loading_any_runtime(tmp_path, monkeypatch):
    monkeypatch.delenv("CAS_META2_RUN_GPU_TESTS", raising=False)
    monkeypatch.setattr(preflight, "_load_runtime", lambda: (_ for _ in ()).throw(AssertionError("TOO_EARLY")))
    with pytest.raises(preflight.GPUPreflightError, match="AUTHORIZATION_REQUIRED"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert read_receipt(tmp_path)["completed"] is False


def test_deterministic_settings_are_required_not_silently_changed(tmp_path, simulation, monkeypatch):
    _, cuda = simulation
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":16:8")
    with pytest.raises(preflight.GPUPreflightError, match="DETERMINISTIC_SETTINGS_REQUIRED"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert cuda.events == [] and os.environ["CUBLAS_WORKSPACE_CONFIG"] == ":16:8"


def test_numerical_settings_changed_during_geometry_prevent_success(tmp_path, simulation, monkeypatch):
    runtime, _ = simulation
    original = preflight._run_geometry
    def changed(*args):
        original(*args)
        runtime.backends.cuda.matmul.allow_tf32 = True
    monkeypatch.setattr(preflight, "_run_geometry", changed)
    with pytest.raises(preflight.GPUPreflightError, match="NUMERICAL_SETTINGS_CHANGED"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    result = read_receipt(tmp_path)
    assert result["completed"] is False and result["memory_cleanup_confirmed"] is True


def test_geometry_exception_still_cleans_workspaces_and_preserves_failure(tmp_path, simulation, monkeypatch):
    _, cuda = simulation
    original = preflight._run_geometry
    def failed(*args):
        original(*args)
        raise RuntimeError("FAKE_GRADIENT_FAILURE")
    monkeypatch.setattr(preflight, "_run_geometry", failed)
    with pytest.raises(preflight.GPUPreflightError, match="FAKE_GRADIENT_FAILURE"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    result = read_receipt(tmp_path)
    assert result["completed"] is False and result["memory_cleanup_confirmed"] is True
    assert cuda.workspace == 0


@pytest.mark.parametrize("metric", [float("nan"), float("inf"), object()])
def test_invalid_metrics_preserve_a_complete_failed_receipt(tmp_path, simulation, monkeypatch, metric):
    original = preflight._run_geometry
    def invalid(*args):
        original(*args)
        args[2]["diagnostic_fixture"] = metric
    monkeypatch.setattr(preflight, "_run_geometry", invalid)
    with pytest.raises(preflight.GPUPreflightError, match="INVALID_DIAGNOSTIC_METRIC"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    result = read_receipt(tmp_path)
    assert result["completed"] is False and result["geometry_checks_completed"] is True
    assert result["memory_cleanup_confirmed"] is True
    assert result["failures"][0]["metric_paths"] == ["receipt/diagnostic_fixture"]
    assert type(result["diagnostic_fixture"]) is dict


@pytest.mark.parametrize("deadline", [0, float("nan"), float("inf")])
def test_invalid_or_elapsed_deadline_is_saved_without_loading_runtime(tmp_path, simulation, monkeypatch, deadline):
    monkeypatch.setattr(preflight, "_load_runtime", lambda: (_ for _ in ()).throw(AssertionError("TOO_EARLY")))
    with pytest.raises(preflight.GPUPreflightError, match="PREFLIGHT_DEADLINE"):
        preflight.run_preflight([], None, tmp_path, deadline)
    assert read_receipt(tmp_path)["completed"] is False


def test_original_v2_receipt_is_never_replaced(tmp_path, simulation):
    original = tmp_path / "gpu_preflight_v2.json"
    original.write_bytes(b"PRESERVE ORIGINAL FAILED GATE FIXTURE")
    preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert original.read_bytes() == b"PRESERVE ORIGINAL FAILED GATE FIXTURE"
    v3 = (tmp_path / "gpu_preflight_v3.json").read_bytes()
    with pytest.raises(preflight.GPUPreflightError, match="NEW_RECEIPT"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert (tmp_path / "gpu_preflight_v3.json").read_bytes() == v3


@pytest.mark.parametrize("linked_part", ["directory", "parent", "receipt"])
@pytest.mark.parametrize("link_kind", ["is_symlink", "is_junction"])
def test_raw_output_links_are_refused_before_resolution(tmp_path, simulation, monkeypatch, linked_part, link_kind):
    # Mock only the link identity, not the guard or resolution. This also tests
    # Windows junctions without needing special link-creation privileges.
    output = tmp_path / "new-output"
    output.mkdir()
    suspect = {"directory": output, "parent": tmp_path,
               "receipt": output / "gpu_preflight_v3.json"}[linked_part]
    monkeypatch.setattr(Path, link_kind, lambda path: path == suspect, raising=False)
    monkeypatch.setattr(Path, "resolve", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("Raw caller path must be checked before resolve")))
    with pytest.raises(preflight.GPUPreflightError, match="RECEIPT_LINK_REFUSED"):
        preflight.run_preflight([], None, output, time.monotonic() + 20)
    assert list(output.iterdir()) == []


def test_changed_dependency_bytes_are_refused_before_runtime_import(tmp_path, simulation, monkeypatch):
    for name in preflight.PINNED_GEOMETRY_FILES:
        (tmp_path / name).write_bytes((preflight.ROOT / name).read_bytes())
    (tmp_path / "gpu_preflight_v2.py").write_bytes(b"changed fixture, not frozen geometry")
    # Remove only module-path checks in this temporary copied package by using a
    # filename that is checked before an already loaded package identity.
    pins = {"gpu_preflight_v2.py": preflight.PINNED_GEOMETRY_FILES["gpu_preflight_v2.py"]}
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    monkeypatch.setattr(preflight, "PINNED_GEOMETRY_FILES", pins)
    monkeypatch.setattr(preflight, "_load_runtime", lambda: (_ for _ in ()).throw(AssertionError("TOO_EARLY")))
    with pytest.raises(preflight.GPUPreflightError, match="FROZEN_GEOMETRY_SOURCE_CHANGED"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)


def test_gpu_module_skips_before_neural_import_and_requires_real_training_input():
    path = Path(__file__).with_name("test_gpu_preflight_v3_gpu.py")
    source = path.read_text()
    assert source.index('pytest.skip(') < source.index('import torch')
    assert "CAS_META2_PREFLIGHT_V3_TRAIN_JSON" in source
    assert "CAS_META2_PREFLIGHT_V3_TRAIN_SHA256" in source
    assert 'len(tasks) == 768' in source
    assert '"cold", "warm", "repeated"' in source
    assert "subprocess.run(" in source
