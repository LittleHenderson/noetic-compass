"""Pure helper tests with fake tensors; never execute the AWS/CUDA probe main."""
from copy import deepcopy
from hashlib import sha256
import ast
import math
import os
from pathlib import Path, PurePosixPath
import struct
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from aws import teaching_cycle_restore_probe_v2 as probe


class Tensor:
    def __init__(self, values=(0.25, 0.5), *, device="cuda:0", dtype="float32", shape=None):
        self.values, self.device, self.dtype = tuple(values), device, dtype
        self.shape = (len(values),) if shape is None else shape
    def numel(self):
        return math.prod(self.shape)
    def element_size(self):
        return 4
    def detach(self):
        return self
    def contiguous(self):
        return self
    def reshape(self, *shape):
        return self
    def view(self, dtype):
        return self
    def cpu(self):
        return self
    def untyped_storage(self):
        return struct.pack("<" + "f" * len(self.values), *self.values)


class Torch:
    uint8 = "uint8"
    @staticmethod
    def is_tensor(value):
        return type(value) is Tensor
    @staticmethod
    def isfinite(value):
        return SimpleNamespace(all=lambda: SimpleNamespace(item=lambda: all(math.isfinite(x) for x in value.values)))


def moments(steps=784):
    return {"step": Tensor((float(steps),), device="cpu", shape=()),
            "exp_avg": Tensor(), "exp_avg_sq": Tensor((0.125, 0.25))}


class Optimizer:
    def __init__(self, calls):
        self.parameter = Tensor()
        self.param_groups = [{"params": [self.parameter]}]
        self.state, self.calls = {}, calls
    def step(self):
        self.calls.append("step")
    def state_dict(self):
        return {"state": {0: deepcopy(self.state[self.parameter])},
                "param_groups": [{"params": [0], "lr": 0.003}]}


class Learner:
    def __init__(self, arm, run_id):
        self.arm, self.run_id, self.device = arm, run_id, "cuda:0"
        self.steps, self.current, self.calls = 0, "1" * 64, []
        self.optimizer = Optimizer(self.calls)
    def state_identity(self):
        return {"run_id": self.run_id, "checkpoint_sha256": self.current,
                "scope_sha256": "2" * 64, "training_cases_sha256": "3" * 64,
                "record_registry_sha256": "4" * 64}
    def teach(self, *args):
        self.calls.append("teach")
    def predict(self, *args):
        self.calls.append("predict")
    def save_checkpoint(self, *args):
        self.calls.append("save")


@pytest.fixture
def case(tmp_path):
    campaign = tmp_path / "campaign"
    learners, arms, reports = {}, {}, {}
    for arm in probe.ARMS:
        learner = Learner(arm, "old-run." + arm)
        learners[arm] = learner
        txn = campaign / arm / "journal/txn-00000002"
        txn.mkdir(parents=True)
        checkpoint, receipt = txn / "candidate.pt", txn / "receipt.json"
        checkpoint.write_bytes(b"opaque fake checkpoint:" + arm.encode())
        receipt.write_bytes(b"{}")
        (txn.parent / "journal.json").write_bytes(b"{}")
        arms[arm] = {"run_id": learner.run_id, "committed_transactions": 2,
            "committed_optimizer_steps": 774 if arm == "generic.ordinary" else 784,
            "committed_cursor": {"epoch": 13, "batch": 6, "stage": 4} if arm == "generic.ordinary"
                else {"epoch": 14, "batch": 0, "stage": 0},
            "pending_development": False, "checkpoint_file_sha256": sha256(checkpoint.read_bytes()).hexdigest(),
            "checkpoint_receipt_sha256": sha256(receipt.read_bytes()).hexdigest(), "checkpoint_state_sha256": "5" * 64}
        reports[arm] = {"initial_checkpoint": {"state_sha256": "1" * 64}}
    manifest = {"arms": arms, "training_cases_sha256": "3" * 64}
    calls = []
    def session(learner, training, development, curriculum, root, source, **kwargs):
        calls.append(learner.arm)
        row = arms[learner.arm]
        assert source == "6" * 64 and kwargs["execution_mode"] == "cuda"
        learner.current, learner.steps = row["checkpoint_state_sha256"], row["committed_optimizer_steps"]
        learner.optimizer.state = {learner.optimizer.parameter: moments(learner.steps)}
        return SimpleNamespace(event_count=learner.steps, cursor=deepcopy(row["committed_cursor"]),
                               pending_development=row["pending_development"])
    def checkpoint_load(path, *, map_location, weights_only):
        assert map_location == "cuda:0" and weights_only is True
        arm = Path(path).parents[2].name
        steps = arms[arm]["committed_optimizer_steps"]
        return {"steps": steps, "run_id": learners[arm].run_id, "model_state_sha256": "5" * 64,
            "optimizer": {"state": {0: moments(steps)}, "param_groups": [{"params": [0], "lr": 0.003}]}}
    return {"learners": learners, "manifest": manifest, "summary": {"arms": reports},
        "campaign_root": campaign, "data": {"training_cases": [], "development_cases": [],
            "manifest": {"source_sha256": "6" * 64, "profile": {"allocation": {}, "seed": 7}}},
        "session_type": session, "allocation_type": lambda **kwargs: kwargs,
        "torch": Torch, "checkpoint_load": checkpoint_load, "session_calls": calls}


def run(case, **overrides):
    args = {key: value for key, value in case.items() if key != "session_calls"}
    args.update(overrides)
    return probe.restore_arms(**args)


def hooks(learner):
    return [learner.teach, learner.predict, learner.save_checkpoint, learner.optimizer.step]


def test_four_arm_restore_controls_and_hooks(case):
    before = {arm: hooks(learner) for arm, learner in case["learners"].items()}
    result = run(case)
    assert case["session_calls"] == list(probe.ARMS)
    for arm, row in result.items():
        assert row["optimizer_state_sha256"] == row["saved_optimizer_state_sha256"]
        assert row["optimizer_steps_performed"] == 0 and row["predictions_run"] is False
        assert row["optimizer_tensors_device_checked"] == 3
        assert not case["learners"][arm].calls
        assert hooks(case["learners"][arm]) == before[arm]


@pytest.mark.parametrize("method", ["teach", "predict", "save_checkpoint", "step"])
def test_learning_writing_and_prediction_denied_with_hook_restoration(case, method):
    learner = case["learners"][probe.ARMS[0]]
    original = hooks(learner)
    def attempted(learner, *args, **kwargs):
        owner = learner.optimizer if method == "step" else learner
        getattr(owner, method)()
    with pytest.raises(probe.RestoreError, match="LEARNING_OR_WRITE_FORBIDDEN"):
        run(case, session_type=attempted)
    assert hooks(learner) == original and not learner.calls


@pytest.mark.parametrize("fault", ["steps", "cursor", "model", "scope", "registry"])
def test_restored_state_and_counts_must_match(case, fault):
    original_session = case["session_type"]
    def changed(learner, *args, **kwargs):
        result = original_session(learner, *args, **kwargs)
        if fault == "steps":
            learner.steps += 1
        elif fault == "cursor":
            result.cursor["stage"] += 1
        elif fault == "model":
            learner.current = "f" * 64
        else:
            prior = learner.state_identity
            key = "scope_sha256" if fault == "scope" else "record_registry_sha256"
            learner.state_identity = lambda: {**prior(), key: "f" * 64}
        return result
    with pytest.raises(probe.RestoreError, match="RESTORED_"):
        run(case, session_type=changed)


def test_changed_saved_optimizer_values_rejected(case):
    original = case["checkpoint_load"]
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        result["optimizer"]["state"][0]["exp_avg"] = Tensor((0.75, 0.5))
        return result
    with pytest.raises(probe.RestoreError, match="RESTORED_OPTIMIZER_MISMATCH"):
        run(case, checkpoint_load=changed)


def test_deadline_check_stops_before_any_session(case):
    def stop():
        raise probe.RestoreError("TEACHING_RESTORE:RESTORE_DEADLINE_REACHED")
    with pytest.raises(probe.RestoreError, match="DEADLINE"):
        run(case, tick=stop)
    assert not case["session_calls"]


@pytest.mark.parametrize("fault", ["cpu_moment", "shape", "dtype", "extra_parameter", "empty", "non_tensor", "step_device"])
def test_optimizer_state_device_and_geometry_checks(case, fault):
    learner = case["learners"][probe.ARMS[0]]
    learner.steps = 392
    state = moments()
    learner.optimizer.state = {learner.optimizer.parameter: state}
    if fault == "cpu_moment":
        state["exp_avg"].device = "cpu"
    elif fault == "shape":
        state["exp_avg"].shape = (1, 2)
    elif fault == "dtype":
        state["exp_avg"].dtype = "float64"
    elif fault == "extra_parameter":
        learner.optimizer.state[Tensor()] = moments()
    elif fault == "empty":
        learner.optimizer.state = {}
    elif fault == "non_tensor":
        state["exp_avg"] = [1, 2]
    else:
        state["step"].device = "cuda:1"
    with pytest.raises(probe.RestoreError):
        probe.verify_optimizer_devices(learner, Torch)


def test_fingerprint_exactness_and_permitted_step_device_change():
    left, right = moments(), moments()
    right["step"].device = "cuda:0"
    assert probe.optimizer_fingerprint(left, Torch) == probe.optimizer_fingerprint(right, Torch)
    right["exp_avg"].dtype = "float64"
    assert probe.optimizer_fingerprint(left, Torch) != probe.optimizer_fingerprint(right, Torch)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {False: 1}, object(), Tensor((float("nan"),))])
def test_fingerprint_rejects_nonfinite_and_unknown_structure(value):
    with pytest.raises(probe.RestoreError):
        probe.optimizer_fingerprint(value, Torch)


@pytest.fixture
def tree(tmp_path):
    entries = {"train/campaign_summary.json": b"{}", "train/campaign/arm/journal/file.pt": b"opaque",
               "train_continued_001/campaign_summary.json": b'{"synthetic":"latest"}'}
    for name, payload in entries.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    manifest = {"schema": "cas-teaching-prior-state/2", "summary_path": probe.RESUME_SUMMARY,
                "retained_summary_path": probe.RETAINED_SUMMARY,
                "members": {name: {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}
                            for name, raw in entries.items()}, "expanded_bytes": sum(map(len, entries.values()))}
    return tmp_path, manifest


def test_prior_tree_exact_bytes_and_empty_directory_rejection(tree):
    root, manifest = tree
    assert probe.verify_tree(root, manifest)["files"] == 3
    (root / "train/extra").mkdir()
    with pytest.raises(probe.RestoreError, match="UNEXPECTED_PRIOR_DIRECTORY"):
        probe.verify_tree(root, manifest)


@pytest.mark.parametrize("fault", ["changed", "missing", "extra_file", "empty_directory", "hardlink"])
def test_latest_prior_root_is_checked_as_strictly_as_original_root(tree, fault):
    root, manifest = tree
    path = root / probe.RESUME_SUMMARY
    if fault == "changed":
        path.write_bytes(b"changed")
    elif fault == "missing":
        path.unlink()
    elif fault == "extra_file":
        (path.parent / "extra.json").write_bytes(b"{}")
    elif fault == "empty_directory":
        (path.parent / "empty").mkdir()
    else:
        os.link(path, root / "outside-latest-hardlink.json")
    with pytest.raises(probe.RestoreError):
        probe.verify_tree(root, manifest)


@pytest.mark.parametrize("field,wrong", [("schema", "cas-teaching-prior-state/1"),
    ("summary_path", "train/campaign_summary.json"),
    ("retained_summary_path", "train_continued_002/campaign_summary.json")])
def test_first_slice_or_relabelled_summary_manifest_is_rejected(tree, field, wrong):
    root, manifest = tree
    manifest[field] = wrong
    with pytest.raises(probe.RestoreError, match="SLICE_TWO_PRIOR_SUMMARIES_REQUIRED"):
        probe.verify_tree(root, manifest)


def test_restored_steps_match_the_actual_mixed_second_slice_counts(case):
    result = run(case)
    assert {arm: row["committed_optimizer_steps"] for arm, row in result.items()} == {
        "cas.aligned": 784, "cas.ordinary": 784, "generic.aligned": 784, "generic.ordinary": 774}


@pytest.mark.parametrize("fault", ["bytes", "missing", "extra", "hardlink", "total"])
def test_prior_tree_integrity_rejections(tree, fault):
    root, manifest = tree
    path = root / "train/campaign_summary.json"
    if fault == "bytes":
        path.write_bytes(b"[]")
    elif fault == "missing":
        path.unlink()
    elif fault == "extra":
        (root / "train/extra.json").write_bytes(b"{}")
    elif fault == "hardlink":
        os.link(path, root / "outside-hardlink.json")
    else:
        manifest["expanded_bytes"] += 1
    with pytest.raises(probe.RestoreError):
        probe.verify_tree(root, manifest)


def test_paths_links_and_member_bounds(tree, monkeypatch):
    root, manifest = tree
    with pytest.raises(probe.RestoreError, match="PARENT_PATH"):
        probe.safe(root / ".." / "outside")
    with pytest.raises(probe.RestoreError, match="MEMBER_BOUND"):
        probe.verify_tree(root, {**manifest, "members": {}})
    with pytest.raises(probe.RestoreError, match="BOUNDED_FILE"):
        probe.identity(root / "train/campaign_summary.json", maximum=1)
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == root / "train" or original(path))
    with pytest.raises(probe.RestoreError, match="LINK_PATH"):
        probe.verify_tree(root, manifest)


def source_fixture(tmp_path):
    bundle, archive = tmp_path / "bundle", tmp_path / "source.zip"
    bundle.mkdir()
    with ZipFile(archive, "w") as target:
        for number in range(17):
            name, raw = f"module{number:02d}.py", b"raise RuntimeError('must not execute')\n"
            (bundle / name).write_bytes(raw)
            target.writestr(name, raw)
    return bundle, archive


def test_source_bytes_checked_without_importing_them(tmp_path):
    bundle, archive = source_fixture(tmp_path)
    assert probe.verify_source_bundle(bundle, archive)["files"] == 17
    (bundle / "module00.py").write_bytes(b"changed")
    with pytest.raises(probe.RestoreError, match="EXTRACTED_SOURCE_CHANGED"):
        probe.verify_source_bundle(bundle, archive)


def test_source_inventory_and_link_rejected(tmp_path):
    bundle, archive = source_fixture(tmp_path)
    (bundle / "unexpected.py").write_bytes(b"extra")
    with pytest.raises(probe.RestoreError, match="SOURCE_INVENTORY"):
        probe.verify_source_bundle(bundle, archive)
    (bundle / "unexpected.py").unlink()
    os.link(bundle / "module00.py", tmp_path / "source-hardlink")
    with pytest.raises(probe.RestoreError, match="SINGLE_LINK"):
        probe.verify_source_bundle(bundle, archive)


def test_environment_guard_is_before_neural_imports_and_output_writes():
    syntax = ast.parse(Path(probe.__file__).read_text())
    main = next(node for node in syntax.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    guard = next(node.lineno for node in ast.walk(main) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "_environment_guard")
    imports = [node.lineno for node in ast.walk(main) if isinstance(node, ast.ImportFrom)
               and (node.module or "").startswith("cas_meta2")]
    writes = [node.lineno for node in ast.walk(main) if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Attribute) and node.func.attr == "mkdir"]
    assert imports and writes and guard < min(imports + writes)
    verify = next(node.lineno for node in ast.walk(main) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name) and node.func.id == "verify_source_bundle")
    assert verify < min(imports)


def test_environment_scope_and_budget_gate_without_running_main(monkeypatch):
    args = SimpleNamespace(max_seconds=900, job="cas-meta2-teaching-20260908000000-aaaaaaaa",
        run_id="cas-meta2-teaching-20260907000000-bbbbbbbb", expected_account="807562639912",
        expected_region="us-west-2", expected_instance_type="g7.2xlarge", output=probe.JOB_ROOT + "/restore")
    monkeypatch.setattr(probe.platform, "system", lambda: "Linux")
    monkeypatch.setattr(probe, "sys", SimpleNamespace(flags=SimpleNamespace(isolated=True),
        dont_write_bytecode=True, version_info=(3, 12)))
    monkeypatch.setattr(probe, "safe", lambda path: PurePosixPath(path))
    monkeypatch.setenv("CAS_META2_RUN_TEACHING_CYCLE", "1")
    probe._environment_guard(args)
    for field, bad in (("max_seconds", 901), ("job", args.run_id),
                       ("expected_instance_type", "g4dn.xlarge"), ("output", "/tmp/restore")):
        changed = deepcopy(args)
        setattr(changed, field, bad)
        with pytest.raises(probe.RestoreError):
            probe._environment_guard(changed)
    monkeypatch.delenv("CAS_META2_RUN_TEACHING_CYCLE")
    with pytest.raises(probe.RestoreError, match="EXPLICIT_ENABLE"):
        probe._environment_guard(args)
