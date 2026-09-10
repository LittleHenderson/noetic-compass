"""Executes the RENDERED worker inner-runner locally with stub modules.

The inner runner is generated at package time and never runs locally, so a wrong
keyword, a missing import or bad wiring in it can only fail on the paid GPU run.
This test executes the real rendered source against stubs and asserts the
sequence the job depends on: encoder from the FROZEN teaching records, the
untouched final panel, one launch call with the registered kwargs, a result file
with its sha256, and the checkpoint artifacts uploaded.
"""
import inspect
import json
import sys
import types
from hashlib import sha256
from types import SimpleNamespace

import pytest

from aws import graph_training_curriculum_launch as launch
from cas_meta2.graph_teaching import adapter, curriculum, trainer


class StubS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body):
        self.objects[Key] = Body
        return {}


@pytest.fixture()
def worker_run(tmp_path, monkeypatch):
    """Execute the rendered INNER_RUNNER and return what it did."""
    recorded = {}
    s3 = StubS3()

    # --- stub only the heavy LEAVES, keeping the real packages importable ----
    stub_torch = SimpleNamespace(__version__="stub",
                                 manual_seed=lambda seed: None)
    gpu_adapter = types.ModuleType("cas_meta2.teaching_cycle.gpu_adapter")
    gpu_adapter._cuda = lambda: (stub_torch, "cpu")
    monkeypatch.setitem(sys.modules, "cas_meta2.teaching_cycle.gpu_adapter",
                        gpu_adapter)

    from cas_meta2.graph_teaching import (curriculum_experiment as experiment,
                                          final_panel as panel_module,
                                          real_framework as framework_module)

    def build_encoder(torch, publics, d_model, seed, device):
        recorded["encoder"] = {"publics": publics, "seed": seed, "d_model": d_model}
        return {"vocabulary_size": 2, "d_model": d_model, "seed": seed}

    monkeypatch.setattr(framework_module, "build_encoder", build_encoder)

    def build_final_panel():
        recorded["panel_called"] = True
        return {"schema": "cas-graph-training-final-panel/1",
                "panel_seed": 20260930, "family_count": 30, "case_count": 90,
                "cases": []}

    monkeypatch.setattr(panel_module, "build_final_panel", build_final_panel)

    def launch_experiment(**kwargs):
        recorded["launch_kwargs"] = kwargs
        checkpoint_dir = kwargs["checkpoint_dir"]
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        artifact = checkpoint_dir / "control_seed20260913_step064.pt"
        artifact.write_bytes(b"weights")
        return {"schema": "cas-graph-training-curriculum-result/1",
                "job": kwargs["run_id"],
                "artifacts": [{"path": str(artifact), "step": 64,
                               "condition": "control",
                               "learner_seed": 20260913}]}

    monkeypatch.setattr(experiment, "launch", launch_experiment)
    monkeypatch.setitem(sys.modules, "boto3",
                        types.ModuleType("boto3"))
    sys.modules["boto3"].client = lambda service, region_name=None: s3

    # --- run the real inner runner ---------------------------------------
    outer = {}
    exec(compile(launch.render_worker(), "worker.py", "exec"), outer)
    inner_source = outer["INNER_RUNNER"]
    root = tmp_path / "root"
    (root / "results").mkdir(parents=True)
    (root / "config.json").write_bytes(json.dumps(
        {"job": "cas-meta2-graph6curr-test", "bucket": "bucket",
         "region": "us-west-2"}).encode())
    import os
    cwd = os.getcwd()
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "argv", ["inner_runner.py", str(root)])
    try:
        exec(compile(inner_source, "inner_runner.py", "exec"),
             {"__name__": "__main__"})
    finally:
        monkeypatch.chdir(cwd)
    return recorded, s3, root


def test_worker_runs_the_registered_sequence(worker_run):
    recorded, s3, root = worker_run
    # the encoder is fitted on the FROZEN teaching records only
    assert recorded["encoder"]["seed"] == 20260909
    assert recorded["encoder"]["d_model"] == 64
    assert len(recorded["encoder"]["publics"]) == 30
    # the untouched final panel is built by the panel module
    assert recorded["panel_called"] is True
    kwargs = recorded["launch_kwargs"]
    assert set(kwargs) == {"run_id", "torch", "device", "encoder", "tasks",
                           "panel", "checkpoint_dir"}
    assert kwargs["run_id"] == "cas-meta2-graph6curr-test"
    assert kwargs["device"] == "cpu"
    # the familiar tasks are the frozen teaching records
    assert [task["record_id"] for task in kwargs["tasks"]] == \
        [task["record_id"] for task in
         [adapter.public_records(record, "cas")
          for record in trainer.training_records(20260909)]]
    # result.json and its sha256 were written
    raw = (root / "results" / "result.json").read_bytes()
    assert json.loads(raw)["job"] == "cas-meta2-graph6curr-test"
    sidecar = (root / "results" / "result.json.sha256").read_text().strip()
    assert sidecar == sha256(raw).hexdigest()


def test_inner_runner_stages_artifacts_without_needing_the_aws_sdk(worker_run):
    """Attempt 003 died on 'import boto3' INSIDE the training venv at the very
    end, after the whole run had succeeded. The inner runner must not import it,
    and must stage the checkpoints plus a manifest under results/artifacts."""
    recorded, _s3, root = worker_run
    outer = {}
    exec(compile(launch.render_worker(), "worker.py", "exec"), outer)
    executable = [line for line in outer["INNER_RUNNER"].splitlines()
                  if not line.strip().startswith("#")]
    assert not any("boto3" in line for line in executable)
    results = root / "results"
    manifest = json.loads((results / "artifacts" / "manifest.json").read_text())
    entry = manifest["artifacts"][0]
    assert entry["name"] == "control_seed20260913_step064.pt"
    assert entry["bytes"] == len(b"weights")
    assert entry["sha256"] == sha256(b"weights").hexdigest()
    assert (results / "artifacts" / entry["name"]).read_bytes() == b"weights"


def test_upload_results_sends_artifacts_before_the_result(tmp_path):
    """The launcher polls for result.json, so it must be uploaded LAST."""
    outer = {}
    exec(compile(launch.render_worker(), "worker.py", "exec"), outer)
    results = tmp_path / "results"
    (results / "artifacts").mkdir(parents=True)
    (results / "artifacts" / "cp.pt").write_bytes(b"weights")
    (results / "artifacts" / "manifest.json").write_text(json.dumps(
        {"artifacts": [{"name": "cp.pt", "bytes": 7,
                        "sha256": sha256(b"weights").hexdigest(), "step": 64,
                        "condition": "control", "learner_seed": 20260913}]}))
    (results / "result.json").write_bytes(b"{}")
    (results / "result.json.sha256").write_text(sha256(b"{}").hexdigest() + "\n")
    s3 = StubS3()
    uploaded = outer["upload_results"](s3, "bucket", results)
    assert uploaded["manifest"] is True
    assert uploaded["artifacts"] == ["cp.pt"]
    assert uploaded["result"] is True
    assert s3.objects["results/artifacts/cp.pt"] == b"weights"
    assert "results/artifacts/manifest.json" in s3.objects
    assert list(s3.objects)[-1] == "results/result.json"          # result last


def test_a_completed_result_is_never_destroyed_by_a_later_failure():
    """Attempt 003 completed the whole run and then failed at upload; the failure
    report overwrote the real result. The preservation branch must exist and must
    only write a failure report when no result exists."""
    source = launch.render_worker()
    assert "result_partial.json" in source
    assert "NEVER destroy a result" in source
    main_source = source.split("def main():", 1)[1]
    preservation = main_source.split("if failure is not None:", 1)[1]
    assert "result_partial.json" in preservation
    assert "if existing.exists():" in preservation
    assert "    else:" in preservation          # failure report only when absent
