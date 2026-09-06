"""Pure AWS-admission and receipt tests. No native/model/provider execution."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from cas_meta2 import child_qualification_gpu_v8 as g

JOB = "cas-meta2-20260906170000-1234abcd"


def plan():
    return {"schema": g.PLAN_SCHEMA, "job": JOB, "launch_enabled": True,
        "experiment": deepcopy(g.EXPERIMENT), **g.FIXED_SCOPE,
        "source_sha": "a" * 40, "instance_id": "i-" + "b" * 17,
        "source_archive": {"path": "synthetic-source", "sha256": "c" * 64},
        "source_manifest": {"path": "synthetic-manifest", "sha256": "d" * 64}}


def test_import_is_pure_and_plan_never_trains():
    before = set(sys.modules)
    importlib.reload(g)
    assert not {"torch", "cas_cjt", "casformer", "boto3", "botocore"}.intersection(
        n.split(".")[0] for n in set(sys.modules) - before)
    assert g.validate_plan(plan(), JOB)["training"] is False


@pytest.mark.parametrize("key,value", [("max_seconds", 1801), ("max_seconds", True),
    ("max_cost_usd", "4.01"), ("seed", 8), ("task_count", 5), ("binding", 1),
    ("binding", False), ("training", True), ("native_execution", False),
    ("max_output_bytes", 536870913), ("candidates_per_task", 5),
    ("planned_complete_executions", 21), ("planned_native_ticks", 111),
    ("return_child_result", False), ("automatic_retries", 1),
    ("source_sha", None), ("instance_id", 4), ("launch_enabled", 1),
    ("experiment", {"profile": "same_state_br_construction_v8"})])
def test_changed_scope_refused(key, value):
    candidate = plan()
    candidate[key] = value
    with pytest.raises(g.QualificationRefused):
        g.validate_plan(candidate, JOB)


@pytest.mark.parametrize("platform,enable,bound_job", [("win32", "1", JOB),
    ("linux", "0", JOB), ("linux", "1", "different-job")])
def test_wrong_host_or_job_refuses_before_work(tmp_path, monkeypatch, platform, enable, bound_job):
    monkeypatch.setattr(g.sys, "platform", platform)
    monkeypatch.setenv("CAS_META2_RUN_CHILD_QUALIFICATION", enable)
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", bound_job)
    monkeypatch.setattr(g, "check_sources", lambda _: pytest.fail("source checked before admission"))
    with pytest.raises(g.QualificationRefused, match="AWS_LINUX_EXPLICIT_JOB"):
        g.run(tmp_path / "no", job=JOB, plan_path="absent", plan_sha256="a" * 64)
    assert list(tmp_path.iterdir()) == []


def test_existing_neural_import_refused(monkeypatch):
    monkeypatch.setattr(g.sys, "platform", "linux")
    monkeypatch.setenv("CAS_META2_RUN_CHILD_QUALIFICATION", "1")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", JOB)
    monkeypatch.setitem(sys.modules, "torch.synthetic_marker", ModuleType("marker"))
    with pytest.raises(g.QualificationRefused, match="NEURAL_IMPORT_BEFORE_ADMISSION"):
        g.require_cloud_request(JOB)


def test_new_output_scope(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "ROOT", tmp_path)
    root = tmp_path / "runs"
    root.mkdir()
    used = root / "used"
    used.mkdir()
    for path in (root, used, tmp_path / "outside", root / ".." / "escape"):
        with pytest.raises(g.QualificationRefused):
            g.new_output(path)
    assert g.new_output(root / "new") == root / "new"


def fake_run(tmp_path, monkeypatch, *, core_result=None, setup_error=False, post_error=False):
    from cas_meta2.diagnostic_v8 import gpu as admission
    monkeypatch.setattr(g, "ROOT", tmp_path)
    monkeypatch.setattr(g, "require_cloud_request", lambda _: None)
    monkeypatch.setattr(admission, "read_pinned", lambda *args: plan())
    monkeypatch.setattr(admission, "reservation_binding", lambda _: {"synthetic": "reserved"})
    monkeypatch.setattr(admission, "ec2_identity", lambda _: {"synthetic": "ec2"})
    source_calls = []
    def sources(_):
        source_calls.append(1)
        if post_error and len(source_calls) > 1:
            raise ValueError("synthetic source changed")
        return {"synthetic": "source"}
    monkeypatch.setattr(g, "check_sources", sources)
    ops = SimpleNamespace(assert_identity=lambda: None)
    def configure():
        if setup_error:
            raise ValueError("synthetic CUDA setup failure")
        return ops, {"synthetic": "GPU"}
    monkeypatch.setattr(g, "configure_cuda", configure)
    curriculum = ModuleType("cas_meta2.child_curriculum_v8")
    curriculum.qualification_tasks = lambda: [{"synthetic": i} for i in range(4)]
    core = ModuleType("cas_meta2.child_qualification_v8")
    def qualify(tasks, operations, output, **kwargs):
        assert tasks == curriculum.qualification_tasks() and operations is ops
        assert 0 < kwargs["max_seconds"] <= 1800
        assert kwargs["max_output_bytes"] == 536870912
        Path(output).mkdir()
        return core_result if core_result is not None else {"status": "QUALIFIED", "qualified": True, "training": False}
    core.run_qualification = qualify
    monkeypatch.setitem(sys.modules, curriculum.__name__, curriculum)
    monkeypatch.setitem(sys.modules, core.__name__, core)
    destination = tmp_path / "runs/test"
    result = g.run(destination, job=JOB, plan_path="synthetic-plan", plan_sha256="e" * 64)
    assert json.loads((destination / "worker_receipt.json").read_bytes()) == result
    assert len(source_calls) == 2
    return result


def test_simulated_success_receipt(tmp_path, monkeypatch):
    result = fake_run(tmp_path, monkeypatch)
    assert result["status"] == "CHILD_CURRICULUM_NATIVE_QUALIFIED"
    assert result["postchecks"] == {"source": {"ok": True}, "reservation": {"ok": True}}
    assert result["training"] is False


def test_refused_core_not_promoted(tmp_path, monkeypatch):
    result = fake_run(tmp_path, monkeypatch, core_result={"status": "REFUSED", "qualified": False, "training": False})
    assert result["status"] == "QUALIFICATION_REFUSED_OR_FAILED"


@pytest.mark.parametrize("core_result", [{"status": "QUALIFIED", "qualified": False, "training": False},
    {"status": "QUALIFIED", "qualified": True, "training": True}, {"status": "UNKNOWN", "qualified": True}])
def test_malformed_core_verdict_refused(tmp_path, monkeypatch, core_result):
    result = fake_run(tmp_path, monkeypatch, core_result=core_result)
    assert result["status"] == "QUALIFICATION_STOPPED_OR_FAILED"
    assert result["failure"]["message"] == "CHQ_INVALID_CORE_VERDICT"


def test_setup_failure_receipted_after_cloud_admission(tmp_path, monkeypatch):
    result = fake_run(tmp_path, monkeypatch, setup_error=True)
    assert result["status"] == "QUALIFICATION_STOPPED_OR_FAILED"
    assert result["qualification"] is None
    assert "setup failure" in result["failure"]["message"]
    assert result["postchecks"]["source"]["ok"] is True


def test_source_postcheck_failure_downgrades_result(tmp_path, monkeypatch):
    result = fake_run(tmp_path, monkeypatch, post_error=True)
    assert result["status"] == "QUALIFICATION_STOPPED_OR_FAILED"
    assert result["postchecks"]["source"]["ok"] is False
    assert result["cleanup_errors"] == ["POSTCHECK:source"]
