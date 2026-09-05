"""Pure geometry and simulated accounting checks; not native/GPU evidence."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

import pytest

from cas_meta2 import gpu_preflight_copy_v3 as preflight
from cas_meta2.codec import canonical_sha256


class FakeCUDA:
    def __init__(self):
        self.workspace, self.live, self.reserved = 0, 0, 0
        self.peak_allocated, self.peak_reserved = 0, 0
        self.events = []
        self.clear_error = False
    def is_available(self): return True
    def device_count(self): return 1
    def get_device_properties(self, device):
        return SimpleNamespace(name="NVIDIA RTX PRO 4500 fixture", total_memory=32 * 1024**3)
    def memory_allocated(self, device): return self.workspace + self.live
    def memory_reserved(self, device): return self.reserved
    def max_memory_allocated(self, device): return self.peak_allocated
    def max_memory_reserved(self, device): return self.peak_reserved
    def reset_peak_memory_stats(self, device):
        self.peak_allocated, self.peak_reserved = self.workspace + self.live, self.reserved
    def synchronize(self, device): self.events.append("synchronize")
    def empty_cache(self, device=None):
        self.events.append("empty_cache")
        self.reserved = self.workspace + self.live
    def clear_workspaces(self):
        self.events.append("clear_workspaces")
        if self.clear_error:
            raise RuntimeError("MOCK_CLEAR_FAILED")
        self.workspace = 0


@pytest.fixture
def simulation(monkeypatch):
    monkeypatch.setenv("CAS_META2_RUN_GPU_TESTS", "1")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", "cas-meta2-copy-preflight-pure-fixture")
    monkeypatch.setenv("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    cuda = FakeCUDA()
    runtime = SimpleNamespace(__version__="2.11.0+cu128", version=SimpleNamespace(cuda="12.8"), cuda=cuda,
        _C=SimpleNamespace(_cuda_clearCublasWorkspaces=cuda.clear_workspaces), device=lambda name: name,
        are_deterministic_algorithms_enabled=lambda: True,
        backends=SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=False)),
            cudnn=SimpleNamespace(allow_tf32=False, benchmark=False, deterministic=True)))
    monkeypatch.setattr(preflight.cleanup_tools, "_load_runtime", lambda: runtime)
    monkeypatch.setattr(preflight.cleanup_tools.gc, "collect", lambda: cuda.events.append("gc"))
    def execute(tasks, config, receipt, deadline, observed_runtime, device):
        assert observed_runtime is runtime and cuda.workspace == cuda.live == 0
        cuda.events.append("mock_geometry")
        cuda.workspace = 68157440
        cuda.reserved = 96468992
        cuda.peak_allocated, cuda.peak_reserved = 6 * 1024**3, 7 * 1024**3
        receipt["geometry"] = {"fixture_only": True, "training_examples": 3072,
                               "training_tasks_sha256": canonical_sha256(tasks)}
        receipt["stress_batches"] = {name: {"fixture_only": True} for name in preflight.STRESS_BATCHES}
    monkeypatch.setattr(preflight, "_execute", execute)
    return runtime, cuda


def receipt(output):
    return json.loads((output / "gpu_preflight_copy_v3.json").read_bytes())


def action(steps=1, depth=1):
    leaf = {"input": "arg", "allowed_cjts": ["A"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v" + str(index)} for index in range(steps)],
            "return": "v" + str(steps - 1)}
    names = ["main", "p0", "p1"][:depth]
    procedures = {names[-1]: leaf}
    for index in reversed(range(depth - 1)):
        procedures[names[index]] = {"input": "arg", "allowed_cjts": ["A"], "steps": [
            {"kind": "CALL", "procedure": names[index + 1], "input": "arg", "output": "v0"}], "return": "v0"}
    return {"binding": 0, "program": {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": procedures}}


def public(problem):
    return {"problem": problem, "observations": [{"slot": slot, "tag": "tag" + str(slot),
        "values": [0.125 * (slot + 1)] * 8} for slot in range(3)]}


@pytest.fixture(scope="module")
def training_fixture():
    # Repeated synthetic rows test only stress selection, not curriculum quality.
    rows = [{"public": public("main"), "target": action(depth=1 + index // 1024),
             "task_id": "meta2-v3-0000000000000000-train-" + str(index).zfill(5),
             "provenance": {"depth": 1 + index // 1024, "evaluation_group": "training", "triplet_id": None}}
            for index in range(3072)]
    rows[0]["public"] = public("word " * 100)
    rows[1].update(public=public("brief"), target=action(steps=20))
    rows[2]["public"] = public("p0 " * 50)
    return rows


def test_actual_candidate_source_pins_match_bytes_and_no_old_geometry_is_used():
    identity = preflight._source_identity()
    assert identity["factory"] == "cas_meta2.policy_v3.build_matched_policies"
    assert identity["loss"] == "cas_meta2.loss_v3.weighted_training_loss"
    for name, expected in identity["files_sha256"].items():
        assert sha256((preflight.ROOT / name).read_bytes()).hexdigest() == expected
    assert "gpu_preflight_v2.py" not in identity["files_sha256"]
    text = Path(preflight.__file__).read_text()
    assert "frozen._execute" not in text and "cleanup_tools._run_geometry" not in text


def test_three_stress_batches_select_existing_rows_and_exact_ties(training_fixture):
    before = canonical_sha256(training_fixture)
    tokenizer, plan = preflight.prepare_training_geometry(training_fixture, dict(preflight.REGISTERED_POLICY))
    assert canonical_sha256(training_fixture) == before == plan["training_tasks_sha256"]
    assert plan["training_examples"] == 3072 and plan["batch_size"] == 16
    assert plan["actual_ir_depth_counts"] == {"1": 1024, "2": 1024, "3": 1024}
    assert plan["explicit_training_provenance_verified"] is True
    assert plan["tokenizer_digest"] == tokenizer.digest
    for label, first in zip(preflight.STRESS_BATCHES, (0, 1, 2)):
        indices = plan["stress_batches"][label]["selected_training_indices"]
        assert len(indices) == len(set(indices)) == 16 and indices[0] == first
        assert all(0 <= index < len(training_fixture) for index in indices)
    assert plan["maximum_training_copy_occurrences"] == 50


@pytest.mark.parametrize("change", [{"batch_size": 15}, {"batch_size": True}, {"policy": {}}])
def test_registration_mismatch_refused_before_geometry(training_fixture, change):
    kwargs = {"policy": dict(preflight.REGISTERED_POLICY), "batch_size": 16, **change}
    with pytest.raises(preflight.CopyPreflightError, match="REGISTERED"):
        preflight.prepare_training_geometry(training_fixture, **kwargs)


def test_boolean_policy_shape_and_old_training_row_count_refused(training_fixture):
    policy = dict(preflight.REGISTERED_POLICY, decoder_layers=True)
    with pytest.raises(preflight.CopyPreflightError, match="REGISTERED_POLICY"):
        preflight.prepare_training_geometry(training_fixture, policy)
    with pytest.raises(preflight.CopyPreflightError, match="3072_TRAINING_ROWS"):
        preflight.prepare_training_geometry(training_fixture[:768], dict(preflight.REGISTERED_POLICY))


def test_explicit_nontraining_row_refused(training_fixture):
    rows = list(training_fixture)
    rows[0] = {**rows[0], "split": "test"}
    with pytest.raises(preflight.CopyPreflightError, match="NONTRAINING_SPLIT"):
        preflight.prepare_training_geometry(rows, dict(preflight.REGISTERED_POLICY))


@pytest.mark.parametrize("group", ["validation", "same_depth", "deeper_calls", None])
def test_actual_provenance_group_must_explicitly_be_training(training_fixture, group):
    rows = list(training_fixture)
    rows[0] = {**rows[0], "provenance": {**rows[0]["provenance"], "evaluation_group": group}}
    with pytest.raises(preflight.CopyPreflightError, match="NONTRAINING_SPLIT"):
        preflight.prepare_training_geometry(rows, dict(preflight.REGISTERED_POLICY))


@pytest.mark.parametrize("task_id", ["meta2-v3-0000000000000000-validation-00000", "train-0", None,
                                    "meta2-v3-0000000000000000-train-00001"])
def test_missing_wrong_or_duplicate_train_task_id_refused(training_fixture, task_id):
    rows = list(training_fixture)
    rows[0] = {**rows[0], "task_id": task_id}
    with pytest.raises(preflight.CopyPreflightError, match="TRAIN_TASK_ID_REQUIRED"):
        preflight.prepare_training_geometry(rows, dict(preflight.REGISTERED_POLICY))


def test_mislabeled_and_unbalanced_actual_ir_depths_refused(training_fixture):
    rows = list(training_fixture)
    rows[0] = {**rows[0], "provenance": {**rows[0]["provenance"], "depth": 2}}
    with pytest.raises(preflight.CopyPreflightError, match="ACTUAL_TRAINING_DEPTH_MISMATCH"):
        preflight.prepare_training_geometry(rows, dict(preflight.REGISTERED_POLICY))
    rows[0] = {**rows[0], "target": action(depth=2)}
    with pytest.raises(preflight.CopyPreflightError, match="TRAINING_DEPTH_COUNTS"):
        preflight.prepare_training_geometry(rows, dict(preflight.REGISTERED_POLICY))


def test_aggregate_95_percent_cannot_hide_an_80_percent_head():
    result = preflight.gate_summary(0, [80, 100, 100, 100], [100] * 4)
    assert result["active_fraction"] == 0.95
    assert result["active_fraction_per_head"] == [0.8, 1.0, 1.0, 1.0]
    assert result["all_heads_meet_active_fraction"] is False
    assert preflight.gate_summary(1, [95] * 4, [100] * 4)["all_heads_meet_active_fraction"] is True


@pytest.mark.parametrize("active,valid", [([True, 100, 100, 100], [100] * 4), ([101] * 4, [100] * 4),
                                        ([0] * 4, [0] * 4), ([1], [1])])
def test_invalid_gate_counters_refused(active, valid):
    with pytest.raises(preflight.CopyPreflightError, match="GATE_COUNTER"):
        preflight.gate_summary(0, active, valid)


@pytest.mark.parametrize("warm", [False, True])
def test_simulated_cold_and_warm_cleanup_precedes_success(tmp_path, simulation, warm):
    _, cuda = simulation
    if warm:
        cuda.workspace, cuda.reserved = 68157440, 96468992
    result = preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert result["completed"] and result["memory_cleanup_confirmed"]
    assert result["status"] == "CAS_META_2_COPY_V3_GPU_PREFLIGHT_PASSED"
    assert result["cuda_allocated_bytes_before"] == result["cuda_allocated_bytes_after_cleanup"] == 0
    assert result["frozen_v2_geometry_called"] is False and result["actual_copy_policy"] is True
    assert result["entry_memory"]["allocated_bytes"] == (68157440 if warm else 0)
    assert cuda.events == ["synchronize", "gc", "clear_workspaces", "empty_cache", "synchronize",
        "mock_geometry", "synchronize", "gc", "clear_workspaces", "empty_cache", "synchronize"]
    assert receipt(tmp_path) == result


def test_simulated_repeated_calls_do_not_accumulate_live_allocations(tmp_path, simulation):
    _, cuda = simulation
    for index in range(2):
        output = tmp_path / str(index)
        output.mkdir()
        result = preflight.run_preflight([], None, output, time.monotonic() + 20)
        assert result["entry_memory"]["allocated_bytes"] == cuda.live == cuda.workspace == 0


def test_live_result_allocation_blocks_success_but_saves_failure(tmp_path, simulation, monkeypatch):
    _, cuda = simulation
    original = preflight._execute
    def leaking(*args):
        original(*args)
        cuda.live = 4096
    monkeypatch.setattr(preflight, "_execute", leaking)
    with pytest.raises(preflight.CopyPreflightError, match="MEMORY_CLEANUP_UNCONFIRMED"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    result = receipt(tmp_path)
    assert result["completed"] is False and result["geometry_checks_completed"] is True
    assert result["cuda_allocated_bytes_after_cleanup"] == cuda.live == 4096
    assert result["failures"][0]["stage"] == "final_cleanup"


def test_preexisting_live_allocation_blocks_geometry_without_deleting_it(tmp_path, simulation, monkeypatch):
    _, cuda = simulation
    cuda.live, cuda.reserved = 4096, 4096
    monkeypatch.setattr(preflight, "_execute", lambda *args: pytest.fail("Geometry must not run"))
    with pytest.raises(preflight.CopyPreflightError, match="PROCESS_NOT_IDLE"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert cuda.live == 4096 and receipt(tmp_path)["geometry_checks_completed"] is False


def test_model_error_cleans_workspaces_without_becoming_success(tmp_path, simulation, monkeypatch):
    _, cuda = simulation
    original = preflight._execute
    def failure(*args):
        original(*args)
        raise RuntimeError("MOCK_COPY_GRADIENT_FAILURE")
    monkeypatch.setattr(preflight, "_execute", failure)
    with pytest.raises(preflight.CopyPreflightError, match="COPY_GRADIENT_FAILURE"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    result = receipt(tmp_path)
    assert result["completed"] is False and result["memory_cleanup_confirmed"] is True
    assert cuda.workspace == 0 and "traceback" in result["failures"][0]


def test_authorization_precedes_runtime_loading_and_saves_typed_failure(tmp_path, simulation, monkeypatch):
    monkeypatch.delenv("CAS_META2_RUN_GPU_TESTS", raising=False)
    monkeypatch.setattr(preflight.cleanup_tools, "_load_runtime", lambda: pytest.fail("Runtime imported before authorization"))
    with pytest.raises(preflight.CopyPreflightError, match="AWS_PREFLIGHT_AUTHORIZATION"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert receipt(tmp_path)["failures"][0]["stage"] == "authorization"


def test_unsupported_runtime_and_missing_cleanup_function_fail_closed(tmp_path, simulation):
    runtime, cuda = simulation
    runtime.__version__ = "future-unsupported"
    with pytest.raises(preflight.CopyPreflightError, match="UNSUPPORTED_RUNTIME"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert cuda.events == []


def test_cleanup_function_failure_is_not_ignored(tmp_path, simulation):
    _, cuda = simulation
    cuda.clear_error = True
    with pytest.raises(preflight.CopyPreflightError, match="MOCK_CLEAR_FAILED"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert receipt(tmp_path)["completed"] is False


@pytest.mark.parametrize("value", [-1, True, 0, 64 * 1024**3])
def test_impossible_peak_memory_counters_block_success(tmp_path, simulation, monkeypatch, value):
    _, cuda = simulation
    original = preflight._execute
    def changed(*args):
        original(*args)
        cuda.peak_allocated = value
    monkeypatch.setattr(preflight, "_execute", changed)
    with pytest.raises(preflight.CopyPreflightError, match="PEAK_MEMORY_COUNTERS_INVALID"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert receipt(tmp_path)["completed"] is False


@pytest.mark.parametrize("linked_part", ["directory", "parent", "receipt"])
@pytest.mark.parametrize("link_kind", ["is_symlink", "is_junction"])
def test_raw_output_links_refused_before_resolve(tmp_path, simulation, monkeypatch, linked_part, link_kind):
    output = tmp_path / "new"
    output.mkdir()
    suspect = {"directory": output, "parent": tmp_path, "receipt": output / "gpu_preflight_copy_v3.json"}[linked_part]
    monkeypatch.setattr(Path, link_kind, lambda path: path == suspect, raising=False)
    monkeypatch.setattr(Path, "resolve", lambda *args, **kwargs: pytest.fail("Resolved before raw link guard"))
    with pytest.raises(preflight.CopyPreflightError, match="RECEIPT_LINK_REFUSED"):
        preflight.run_preflight([], None, output, time.monotonic() + 20)
    assert list(output.iterdir()) == []


def test_new_receipt_only_preserves_old_evidence(tmp_path, simulation):
    old = tmp_path / "gpu_preflight_v3.json"
    old.write_bytes(b"ORIGINAL FIXTURE EVIDENCE")
    preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    original_new = (tmp_path / "gpu_preflight_copy_v3.json").read_bytes()
    with pytest.raises(preflight.CopyPreflightError, match="NEW_RECEIPT"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)
    assert old.read_bytes() == b"ORIGINAL FIXTURE EVIDENCE"
    assert (tmp_path / "gpu_preflight_copy_v3.json").read_bytes() == original_new


def test_changed_copy_source_is_refused_before_runtime(tmp_path, simulation, monkeypatch):
    name = "loss_v3.py"
    (tmp_path / name).write_bytes(b"untrusted changed fixture")
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    monkeypatch.setattr(preflight, "PINNED_FILES", {name: preflight.PINNED_FILES[name]})
    monkeypatch.setattr(preflight.cleanup_tools, "_load_runtime", lambda: pytest.fail("Runtime loaded after changed source"))
    with pytest.raises(preflight.CopyPreflightError, match="SOURCE_BYTES_CHANGED"):
        preflight.run_preflight([], None, tmp_path, time.monotonic() + 20)


def test_actual_factory_loss_and_causal_check_are_in_execution_path():
    text = Path(preflight.__file__).read_text()
    tree = ast.parse(text)
    assert not any(isinstance(node, ast.Import) and any(alias.name == "torch" for alias in node.names) for node in tree.body)
    assert "from .policy_v3 import build_matched_policies" in text
    assert "from .loss_v3 import encode_loss_weights, weighted_training_loss" in text
    assert "loss = weighted_training_loss(" in text and "loss.backward()" in text
    assert "copy_query.weight" in text and 'gate["all_heads_meet_active_fraction"]' in text
    assert "before[field][:, :-3], after[field][:, :-3]" in text
    assert not any(isinstance(node, ast.Attribute) and node.attr in {"step", "AdamW", "SGD"} for node in ast.walk(tree))


def test_aws_tests_skip_before_neural_import_and_bind_real_training_hash():
    text = Path(__file__).with_name("test_gpu_preflight_copy_v3_gpu.py").read_text()
    assert text.index("pytest.skip(") < text.index("import torch")
    assert "CAS_META2_COPY_PREFLIGHT_TRAIN_JSON" in text and "CAS_META2_COPY_PREFLIGHT_TRAIN_SHA256" in text
    assert '"cold", "warm", "repeated"' in text
    assert "train_v3 import TrainingConfig, setup_cuda" in text
    tree = ast.parse(text)
    child = next(node.value.value for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == "CHILD" for target in node.targets))
    ast.parse(child)
