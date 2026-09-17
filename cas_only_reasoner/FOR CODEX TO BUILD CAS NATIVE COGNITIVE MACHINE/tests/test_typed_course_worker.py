"""Pure delivery/admission regressions; no numerical runtime is executed."""
from copy import deepcopy
from hashlib import sha256
import ast
import importlib.abc
import json
from pathlib import Path
import sys

import pytest

from cncm import typed_course_worker as worker

ROOT = Path(__file__).resolve().parents[1]


def test_artifact_contract_flat_unique_and_complete():
    names = worker.EXPECTED_ARTIFACTS
    assert len(names) == 344 == len(set(names))
    assert all(Path(name).name == name and "/" not in name for name in names)
    assert "manifest.json" not in names
    assert all("batch_%03d.json" % n in names and "update_%03d.json" % n in names for n in range(160))
    assert {"initial.pt", "prelast.pt", "final.pt", "replay_report.json"} <= set(names)


def test_counter_delta_does_not_recount_restored_history():
    assert worker.counter_delta({"updates": 160, "calls": 180}, {"updates": 159, "calls": 172}) == {"updates": 1, "calls": 8}


@pytest.mark.parametrize("after,before", [({"x": True}, {"x": 0}), ({"x": 1.0}, {"x": 0}),
    ({"x": 1}, {"x": -1}), ({"x": 0}, {"x": 1}), ({"x": 1}, {"y": 0})])
def test_counter_aliases_and_regressions_refused(after, before):
    with pytest.raises(ValueError):
        worker.counter_delta(after, before)


def training_delta():
    return {"slot_forwards": 4613, "core_forward_calls": 17178, "core_forward_attempts": 17178,
        "sample_core_passes": 17178, "prediction_calls": 1152, "staged_batches": 160,
        "private_loss_plan_calls": 1152, "backward_attempts": 160, "backward_calls": 160,
        "optimizer_step_attempts": 160, "optimizer_updates": 160}


def test_exact_main_contract():
    assert worker.validate_training_delta(training_delta()) == training_delta()


@pytest.mark.parametrize("key", list(training_delta()))
def test_partial_main_is_not_success(key):
    delta = training_delta()
    delta[key] -= 1
    with pytest.raises(ValueError, match="MAIN_TRAINING_COUNTERS"):
        worker.validate_training_delta(delta)


def test_seal_exact_bytes_and_no_overwrite(tmp_path):
    raw = b'{"only":"public"}\n'
    path = tmp_path / "batch.json"
    receipt = worker._write_bytes(path, raw)
    assert receipt == {"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    with pytest.raises(FileExistsError):
        worker._write_bytes(path, b"changed")
    assert path.read_bytes() == raw


def test_scoring_rejects_stale_seal_before_private_import(tmp_path):
    path = tmp_path / "predictions.json"
    receipt = worker._write(path, {"predictions": []})
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="SCORING_SEAL_CHANGED"):
        worker._score_seal(path, receipt, {}, started=worker.time.monotonic())


def test_failure_delivery_preserves_partial_files(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    worker._write(artifacts / "batch_000.json", {"public": True})
    report = {"job": "example", "source_sha": "a" * 40, "status": "TYPED_COURSE_FAILED",
              "failure": {"schema": worker.FAILURE_SCHEMA, "type": "ValueError", "detail": "refused"}}
    result = worker.deliver(tmp_path, artifacts, report, failed=True)
    assert result["status"] == "TYPED_COURSE_FAILED"
    for row in result["artifacts"]:
        raw = (artifacts / row["name"]).read_bytes()
        assert len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"]
    assert (tmp_path / "result.json.sha256").read_text().strip() == sha256((tmp_path / "result.json").read_bytes()).hexdigest()
    assert result["summary"]["learning_advantage_established"] is False


def test_success_delivery_requires_every_batch(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    with pytest.raises(ValueError, match="REQUIRED_ARTIFACTS"):
        worker.deliver(tmp_path, artifacts, {"job": "example"}, failed=False)


def test_real_material_windows_refusal_is_delivered_before_numerical_import(tmp_path, monkeypatch):
    from cas_meta2.teaching_cycle import gpu_adapter
    forbidden = {"torch", "numpy", "cas_cjt", "casformer", "boto3", "requests"}
    attempted = []
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in forbidden:
                attempted.append(fullname)
                raise AssertionError("numerical/provider import attempted")
    guard = Guard()
    monkeypatch.setattr(gpu_adapter.platform, "system", lambda: "Windows")
    config = worker.contract.make_config(ROOT, source_sha="a" * 40,
        job="cas-meta2-typedcourse-20260917000000-aaaaaaaa", bucket="typed-pure-test")
    sys.meta_path.insert(0, guard)
    try:
        with pytest.raises(ValueError, match="^TEACHING_GPU:LINUX_WORKER_REQUIRED$"):
            worker.run(config, ROOT, tmp_path, tmp_path / "artifacts")
    finally:
        sys.meta_path.remove(guard)
    receipt = json.loads((tmp_path / "result.json").read_bytes())
    assert receipt["failure"] == {"schema": worker.FAILURE_SCHEMA, "type": "ValueError",
                                  "detail": "TEACHING_GPU:LINUX_WORKER_REQUIRED"}
    assert receipt["status"] == "TYPED_COURSE_FAILED" and attempted == []
    assert not forbidden.intersection(sys.modules)


def test_fresh_builder_seeds_before_registered_construction():
    tree = ast.parse(Path(worker.__file__).read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_fresh_framework")
    text = ast.unparse(function)
    assert text.index("torch.manual_seed") < text.index("return build_graph_training_framework")
    assert text.index("torch.cuda.manual_seed_all") < text.index("return build_graph_training_framework")
    assert "encoder={'d_model': 64}" in text


def test_no_eager_numerical_or_private_import():
    tree = ast.parse(Path(worker.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] + [getattr(node, "module", "") or ""]
            assert not any(name.split(".")[0] in {"torch", "numpy", "boto3", "checker", "loss_plan"} for name in names)
