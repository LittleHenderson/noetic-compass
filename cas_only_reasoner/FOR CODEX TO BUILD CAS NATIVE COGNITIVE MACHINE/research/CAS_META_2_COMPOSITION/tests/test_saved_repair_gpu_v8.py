"""Pure wrapper tests using simulated modules and non-database byte fixtures."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

ROOT = Path(__file__).resolve().parents[1]
JOB = "cas-meta2-20260906180000-aabbccdd"
SOURCE = "a" * 40
PACKAGE = "simulated_saved_repair"


@pytest.fixture
def worker(monkeypatch):
    package = ModuleType(PACKAGE)
    package.__path__ = []
    monkeypatch.setitem(sys.modules, PACKAGE, package)
    spec = importlib.util.spec_from_file_location(
        PACKAGE + ".worker", ROOT / "cas_meta2/saved_repair_gpu_v8.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def plan_for(worker):
    return {
        **deepcopy(worker.FIXED_SCOPE),
        "schema": "cas-meta2-saved-repair-plan/8", "job": JOB, "launch_enabled": True,
        "experiment": deepcopy(worker.EXPERIMENT), "source_sha": SOURCE,
        "instance_id": "i-0123456789abcdef0",
        "source_archive": {"path": "/not-accessed/source.zip", "sha256": "b" * 64},
        "source_manifest": {"path": "/not-accessed/saved_repair_source_manifest.json", "sha256": "c" * 64},
        "evidence_archive": {"path": "/not-accessed/data/prior_failure.zip", "sha256": worker.EVIDENCE_SHA},
    }


def fake_module(monkeypatch, name, **members):
    module = ModuleType(name)
    for key, value in members.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


def fake_run(monkeypatch, tmp_path, worker, *, result=None, core_error=None,
             configure_error=None, post_failure=None, mutate_original=False,
             elapsed=0, output_bound=False):
    """Never executes the frozen admission, CUDA configuration or native core."""
    records, clock = [], [0.0]
    monkeypatch.setattr(worker, "ROOT", tmp_path)
    monkeypatch.setattr(worker, "cloud_request", lambda job: records.append(("cloud_request", job)))
    monkeypatch.setattr(worker.time, "monotonic", lambda: clock[0])
    if output_bound:
        monkeypatch.setattr(worker, "FIXED_SCOPE", {**worker.FIXED_SCOPE, "max_output_bytes": 128})
    plan = plan_for(worker)
    counts = {"source": 0, "reservation": 0, "identity": 0}
    def sources(_plan):
        counts["source"] += 1
        records.append(("source", counts["source"]))
        return {"simulated": "changed" if post_failure == "source" and counts["source"] > 1 else "fixed"}
    def reservation(_plan):
        counts["reservation"] += 1
        records.append(("reservation", counts["reservation"]))
        if post_failure == "reservation" and counts["reservation"] > 1:
            raise ValueError("SIMULATED_RESERVATION_POSTCHECK_FAILURE")
        return {"simulated": True, "no_actual_reservation": True}
    def identity():
        counts["identity"] += 1
        if post_failure == "accepted_sources":
            raise ValueError("SIMULATED_ACCEPTED_SOURCE_POSTCHECK_FAILURE")
        return None
    def configure():
        records.append(("configure",))
        if configure_error:
            raise configure_error
        return SimpleNamespace(assert_identity=identity), {
            "evidence_kind": "SIMULATED_NO_CUDA_OR_NATIVE_EXECUTION"}
    payload = b"SIMULATED_OPAQUE_BYTES_NOT_A_SQLITE_DATABASE"
    monkeypatch.setattr(worker, "DB_SHA", sha256(payload).hexdigest())
    def extract(_source, destination):
        records.append(("extract", str(destination)))
        Path(destination).write_bytes(payload)
        return {"path": str(destination), "bytes": len(payload), "sha256": worker.DB_SHA}
    def repair(output, original, *, device):
        records.append(("core", str(output), str(original), device))
        clock[0] = elapsed
        if mutate_original:
            Path(original).write_bytes(b"SIMULATED_CHANGED_ORIGINAL_BYTES")
        if core_error:
            raise core_error
        return deepcopy(result if result is not None else {
            "status": "REPAIR_RESUMED", "repaired": True, "training": False,
            "evidence_kind": "SIMULATED_NO_NATIVE_EXECUTION"})
    monkeypatch.setattr(worker, "check_sources", sources)
    monkeypatch.setattr(worker, "extract_failure", extract)
    diagnostic_package = fake_module(monkeypatch, PACKAGE + ".diagnostic_v8")
    diagnostic_package.__path__ = []
    fake_module(monkeypatch, PACKAGE + ".diagnostic_v8.gpu",
                read_pinned=lambda path, digest: deepcopy(plan),
                reservation_binding=reservation,
                ec2_identity=lambda value: {"instanceId": value["instance_id"], "simulated": True})
    fake_module(monkeypatch, PACKAGE + ".child_qualification_gpu_v8", configure_cuda=configure)
    fake_module(monkeypatch, PACKAGE + ".saved_repair_v8", run=repair)
    return worker.run(tmp_path / "runs/result", job=JOB,
                      plan_path="SIMULATED_PLAN", plan_sha256="d" * 64), records, counts


def test_plan_has_exact_two_call_no_training_boundary(worker):
    plan = plan_for(worker)
    assert worker.validate_plan(plan, JOB) is plan
    assert worker.FIXED_SCOPE == {
        "max_seconds": 600, "max_cost_usd": "4.00", "seed": 7,
        "max_native_calls": 2, "max_policy_units": 16384, "training": False,
        "native_execution": True, "max_output_bytes": 536870912,
        "automatic_retries": 0, "outer_caller_restored": False}
    assert worker.EVIDENCE_BYTES == 893323
    assert worker.DB_BYTES == 1523712


@pytest.mark.parametrize(("key", "value"), [
    ("max_seconds", 601), ("max_cost_usd", "5.00"), ("seed", 8),
    ("max_native_calls", 3), ("max_policy_units", 16385), ("training", True),
    ("native_execution", False), ("max_output_bytes", 536870913),
    ("automatic_retries", 1), ("outer_caller_restored", True),
    ("max_native_calls", True),
])
def test_fixed_scope_refuses_changes(worker, key, value):
    plan = plan_for(worker)
    plan[key] = value
    with pytest.raises(ValueError, match="REPAIR_SCOPE_CHANGED"):
        worker.validate_plan(plan, JOB)


@pytest.mark.parametrize(("key", "value", "reason"), [
    ("schema", "other/8", "REPAIR_ENABLED_EXACT_PLAN"),
    ("job", "other-job", "REPAIR_ENABLED_EXACT_PLAN"),
    ("launch_enabled", False, "REPAIR_ENABLED_EXACT_PLAN"),
    ("experiment", {}, "REPAIR_ENABLED_EXACT_PLAN"),
    ("source_sha", "A" * 40, "REPAIR_SOURCE_INSTANCE"),
    ("instance_id", "i-placeholder", "REPAIR_SOURCE_INSTANCE"),
    ("evidence_archive", {"sha256": "0" * 64}, "REPAIR_EXACT_FAILURE_ARCHIVE"),
])
def test_plan_identity_refusals(worker, key, value, reason):
    plan = plan_for(worker)
    plan[key] = value
    with pytest.raises(ValueError, match=reason):
        worker.validate_plan(plan, JOB)


@pytest.mark.parametrize(("platform", "flag", "job"), [
    ("win32", "1", JOB), ("linux", None, JOB), ("linux", "0", JOB),
    ("linux", "1", "another-job"),
])
def test_cloud_gate_rejects_before_relative_imports(worker, monkeypatch, platform, flag, job):
    monkeypatch.setattr(worker.sys, "platform", platform)
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", job)
    if flag is None:
        monkeypatch.delenv("CAS_META2_RUN_SAVED_REPAIR", raising=False)
    else:
        monkeypatch.setenv("CAS_META2_RUN_SAVED_REPAIR", flag)
    with pytest.raises(ValueError, match="REPAIR_AWS_LINUX_JOB_REQUIRED"):
        worker.run("never-created", job=JOB, plan_path="never-read", plan_sha256="0" * 64)
    assert PACKAGE + ".diagnostic_v8.gpu" not in sys.modules


def test_neural_module_presence_refused_without_importing_it(worker, monkeypatch):
    monkeypatch.setattr(worker.sys, "platform", "linux")
    monkeypatch.setenv("CAS_META2_RUN_SAVED_REPAIR", "1")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", JOB)
    # This inert marker is not a torch import or a tensor implementation.
    monkeypatch.setitem(sys.modules, "torch", ModuleType("torch"))
    with pytest.raises(ValueError, match="REPAIR_NEURAL_IMPORT_BEFORE_ADMISSION"):
        worker.cloud_request(JOB)


def test_help_does_not_enter_cloud_or_native(worker, monkeypatch, capsys):
    monkeypatch.setattr(worker, "run", lambda *a, **k: pytest.fail("help must not run worker"))
    with pytest.raises(SystemExit) as stopped:
        worker.main(["--help"])
    assert stopped.value.code == 0
    assert "--plan-sha256" in capsys.readouterr().out


def test_simulated_success_preserves_boundary_and_postchecks(worker, monkeypatch, tmp_path):
    receipt, records, counts = fake_run(monkeypatch, tmp_path, worker)
    assert receipt["status"] == "SAVED_NATIVE_REPAIR_SUCCEEDED"
    assert receipt["training"] is False and receipt["outer_caller_restored"] is False
    assert receipt["repair"]["evidence_kind"] == "SIMULATED_NO_NATIVE_EXECUTION"
    assert receipt["cleanup_errors"] == []
    assert all(item["ok"] for item in receipt["postchecks"].values())
    assert counts == {"source": 2, "reservation": 2, "identity": 1}
    assert len([r for r in records if r[0] == "core"]) == 1
    path = tmp_path / "runs/result/worker_receipt.json"
    assert json.loads(path.read_bytes())["status"] == receipt["status"]
    assert "worker_receipt.json" not in receipt["files_sha256"]


def test_simulated_native_refusal_is_not_worker_success(worker, monkeypatch, tmp_path):
    negative = {"status": "REPAIR_REFUSED", "repaired": False, "training": False,
                "evidence_kind": "SIMULATED_NO_NATIVE_EXECUTION"}
    receipt, _, counts = fake_run(monkeypatch, tmp_path, worker, result=negative)
    assert receipt["status"] == "SAVED_NATIVE_REPAIR_REFUSED_OR_FAILED"
    assert receipt["repair"] == negative
    assert counts["identity"] == 1
    assert receipt["postchecks"]["original_database"]["ok"] is True


@pytest.mark.parametrize("result", [
    {"status": "REPAIR_RESUMED", "repaired": False, "training": False},
    {"status": "REPAIR_REFUSED", "repaired": True, "training": False},
    {"status": "REPAIR_RESUMED", "repaired": 1, "training": False},
    {"status": "REPAIR_RESUMED", "repaired": True, "training": True},
    {"status": "CLAIMED_SUCCESS", "repaired": True, "training": False},
    ["invalid core result"],
])
def test_malformed_core_result_is_retained_but_not_promoted(worker, monkeypatch, tmp_path, result):
    receipt, _, _ = fake_run(monkeypatch, tmp_path, worker, result=result)
    assert receipt["status"] == "SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED"
    assert receipt["repair"] == result
    assert receipt["failure"]["message"] == "REPAIR_CORE_VERDICT"


@pytest.mark.parametrize("post_failure", ["source", "reservation", "accepted_sources"])
def test_postcheck_failure_overrides_simulated_success(worker, monkeypatch, tmp_path, post_failure):
    receipt, _, _ = fake_run(monkeypatch, tmp_path, worker, post_failure=post_failure)
    assert receipt["repair"]["repaired"] is True
    assert receipt["status"] == "SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED"
    assert receipt["postchecks"][post_failure]["ok"] is False
    assert "POSTCHECK:" + post_failure in receipt["cleanup_errors"]


def test_original_byte_mutation_checked_even_when_core_raises(worker, monkeypatch, tmp_path):
    receipt, _, counts = fake_run(monkeypatch, tmp_path, worker,
        core_error=ValueError("SIMULATED_NATIVE_REFUSAL"), mutate_original=True)
    assert receipt["status"] == "SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED"
    assert receipt["failure"]["message"] == "SIMULATED_NATIVE_REFUSAL"
    assert receipt["postchecks"]["original_database"]["ok"] is False
    assert counts["identity"] == 1


def test_configuration_failure_still_receipts_sources_and_budget(worker, monkeypatch, tmp_path):
    receipt, records, counts = fake_run(monkeypatch, tmp_path, worker,
        configure_error=ValueError("SIMULATED_CUDA_UNAVAILABLE"))
    assert receipt["status"] == "SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED"
    assert receipt["failure"]["message"] == "SIMULATED_CUDA_UNAVAILABLE"
    assert not any(r[0] in ("extract", "core") for r in records)
    assert counts == {"source": 2, "reservation": 2, "identity": 0}
    assert "original_database" not in receipt["postchecks"]


def test_existing_output_is_not_overwritten(worker, monkeypatch, tmp_path):
    output = tmp_path / "runs/result"
    output.mkdir(parents=True)
    marker = output / "keep.txt"
    marker.write_text("existing user evidence", encoding="utf-8")
    with pytest.raises(ValueError, match="REPAIR_NEW_SCOPED_OUTPUT"):
        fake_run(monkeypatch, tmp_path, worker)
    assert marker.read_text(encoding="utf-8") == "existing user evidence"
    assert list(output.iterdir()) == [marker]


@pytest.mark.parametrize("fault", [None, "manifest_name", "evidence_path", "evidence_hash"])
def test_packaged_source_checks_use_exact_paths_and_pins(worker, monkeypatch, tmp_path, fault):
    plan = plan_for(worker)
    package = tmp_path / "package"
    plan["source_manifest"]["path"] = str(package / worker.MANIFEST_NAME)
    plan["evidence_archive"]["path"] = str(package / "data/prior_failure.zip")
    if fault == "manifest_name":
        plan["source_manifest"]["path"] = str(package / "other_manifest.json")
    elif fault == "evidence_path":
        plan["evidence_archive"]["path"] = str(package / "outside.zip")
    aws = fake_module(monkeypatch, "aws")
    aws.__path__ = []
    calls = []
    manifest = {"evidence_kind": "SIMULATED_PACKAGE"}
    def inspect(path, **kwargs):
        calls.append(("inspect", path, kwargs))
        return manifest
    def verify(path, received, **kwargs):
        calls.append(("verify", path, received, kwargs))
        return None
    fake_module(monkeypatch, "aws.saved_repair_package_v8", inspect_archive=inspect, verify_extracted=verify)
    monkeypatch.setattr(worker, "file_hash", lambda path: "0" * 64 if fault == "evidence_hash" else worker.EVIDENCE_SHA)
    if fault:
        with pytest.raises(ValueError, match="REPAIR_MANIFEST_NAME" if fault == "manifest_name" else "REPAIR_PACKAGED_EVIDENCE_IDENTITY"):
            worker.check_sources(plan)
    else:
        assert worker.check_sources(plan) == manifest
        assert calls[0][2] == {"expected_sha256": "b" * 64,
                               "expected_source_sha": SOURCE,
                               "expected_manifest_sha256": "c" * 64}
        assert calls[1][1] == package
        assert calls[1][3]["imported_paths"] == (Path(worker.__file__),)


@pytest.mark.parametrize(("option", "check"), [("elapsed", "deadline"), ("output_bound", "output_bound")])
def test_post_run_limits_prevent_success(worker, monkeypatch, tmp_path, option, check):
    options = {"elapsed": 601} if option == "elapsed" else {"output_bound": True}
    receipt, _, _ = fake_run(monkeypatch, tmp_path, worker, **options)
    assert receipt["status"] == "SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED"
    assert receipt["postchecks"][check]["ok"] is False


def synthetic_archive(worker, monkeypatch, tmp_path, *, entries=None):
    payload = b"SIMULATED_OPAQUE_BYTES_NOT_A_DATABASE"
    rows = [(worker.DB_MEMBER, payload)] if entries is None else entries
    stream = io.BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        for name, value in rows:
            archive.writestr(name, value)
    raw = stream.getvalue()
    path = tmp_path / "synthetic.zip"
    path.write_bytes(raw)
    monkeypatch.setattr(worker, "EVIDENCE_BYTES", len(raw))
    monkeypatch.setattr(worker, "EVIDENCE_SHA", sha256(raw).hexdigest())
    monkeypatch.setattr(worker, "DB_BYTES", len(payload))
    monkeypatch.setattr(worker, "DB_SHA", sha256(payload).hexdigest())
    return path, payload


def test_exact_extraction_is_exclusive_byte_copy_only(worker, monkeypatch, tmp_path):
    source, payload = synthetic_archive(worker, monkeypatch, tmp_path)
    before = source.read_bytes()
    output = tmp_path / "new_copy.bin"
    receipt = worker.extract_failure(source, output)
    assert output.read_bytes() == payload
    assert source.read_bytes() == before
    assert receipt["bytes"] == len(payload)
    with pytest.raises(FileExistsError):
        worker.extract_failure(source, output)
    assert output.read_bytes() == payload


@pytest.mark.parametrize("fault", ["archive_hash", "archive_size", "database_hash", "database_size"])
def test_extraction_pin_faults_create_no_destination(worker, monkeypatch, tmp_path, fault):
    source, _ = synthetic_archive(worker, monkeypatch, tmp_path)
    key, value = {
        "archive_hash": ("EVIDENCE_SHA", "0" * 64),
        "archive_size": ("EVIDENCE_BYTES", 1),
        "database_hash": ("DB_SHA", "0" * 64),
        "database_size": ("DB_BYTES", 1),
    }[fault]
    monkeypatch.setattr(worker, key, value)
    output = tmp_path / "not_created.bin"
    with pytest.raises(ValueError, match={
        "archive_hash": "REPAIR_ORIGINAL_ARCHIVE_PIN", "archive_size": "REPAIR_ORIGINAL_ARCHIVE_PIN",
        "database_hash": "REPAIR_DATABASE_PIN", "database_size": "REPAIR_DATABASE_SIZE"}[fault]):
        worker.extract_failure(source, output)
    assert not output.exists()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecar_archive_refused(worker, monkeypatch, tmp_path, suffix):
    payload = b"SIMULATED_OPAQUE_BYTES_NOT_A_DATABASE"
    source, _ = synthetic_archive(worker, monkeypatch, tmp_path,
        entries=[(worker.DB_MEMBER, payload), (worker.DB_MEMBER + suffix, b"sidecar")])
    output = tmp_path / "not_created.bin"
    with pytest.raises(ValueError, match="REPAIR_SINGLE_DB_NO_SIDECAR"):
        worker.extract_failure(source, output)
    assert not output.exists()


@pytest.mark.parametrize(("status", "expected"), [
    ("SAVED_NATIVE_REPAIR_SUCCEEDED", 0),
    ("SAVED_NATIVE_REPAIR_REFUSED_OR_FAILED", 1),
    ("SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED", 1),
])
def test_cli_exit_matches_status_without_running_worker(worker, monkeypatch, capsys, status, expected):
    monkeypatch.setattr(worker, "run", lambda *a, **k: {"status": status})
    code = worker.main(["--output", "not-used", "--job", JOB,
                        "--plan", "not-read", "--plan-sha256", "d" * 64])
    assert code == expected
    assert json.loads(capsys.readouterr().out)["job"] == JOB
