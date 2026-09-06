"""Pure B/R remote contracts; no AWS, subprocess, SQLite, or neural execution."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("br_remote_v8_tested", ROOT / "aws/br_remote_v8.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


@pytest.fixture
def config():
    dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
    layout = {"pilot_dir": r.PILOT, "meta1_dir": "research/CAS_META_1_LEARNED_SELECTION",
        "meta_runtime_dir": "research/CASFORMER_v0_3_META_LOGIC_WIP", "dependency_lock": r.PILOT + "/requirements-gpu.txt",
        "wheel_paths": [dist + "casformer_reference-0.1.0-py3-none-any.whl", dist + "cas_neural_cjt-0.2.0-py3-none-any.whl"]}
    names = [layout["dependency_lock"], *layout["wheel_paths"], r.PILOT + "/aws/br_package_v8.py",
             r.PILOT + "/cas_meta2/br_construction_v8.py"]
    manifest = {"schema": "cas-meta2-br-source-package/8", "source_sha": "b" * 40,
        "root_manifest": r.MANIFEST_NAME, "files_sha256": {n: r.sha256(b"fixture").hexdigest() for n in names},
        "files_bytes": {n: 7 for n in names}, "launch_enabled": False, "neural_execution": False,
        "native_execution": False, "training": False, "reservation_created": False,
        "base": {"source_sha": r.BASE_SOURCE_SHA, "archive_sha256": r.BASE_ARCHIVE_SHA256,
            "archive_bytes": 7952045, "member_count": 616, "prefix_manifest_sha256": r.BASE_MANIFEST_SHA256,
            "accepted_baseline": {"source_sha": "0917267b1354e5d036263eaa6ba9a7197eafb776",
                "manifest_sha256": r.BASELINE_MANIFEST_SHA256, "file_count": 316}, "package_layout": layout}}
    return {"schema": "cas-meta2-br-remote-config/8", "job": "cas-meta2-20260906000000-12345678",
        "bucket": "cas-meta2-20260906000000-12345678-807562639912", "account_id": "807562639912", "region": "us-west-2",
        "parent_source_sha": "c" * 40, "worker_source_sha": "b" * 40, "source_archive_sha256": "d" * 64,
        "source_archive_bytes": 123, "source_manifest_sha256": r.sha256(r.canonical(manifest)).hexdigest(),
        "source_manifest": manifest, "package_layout": layout, "max_worker_seconds": 600,
        "artifact_bytes_max": 256 * 1024**2, "evidence_expanded_bytes_max": 512 * 1024**2,
        "resource_plan": {"instance_type": "g7.2xlarge", "instance_count": 1, "runtime_seconds_max": 3600,
            "automatic_retries": 0, "ebs_gb": 75, "ebs_iops": 3000, "ebs_throughput_mib_per_second": 125}}


def permit_for(config):
    receipt, ledger = {"reservation": "synthetic only"}, {"ledger": "synthetic only"}
    plan = {**deepcopy(r.FIXED_PLAN), "job": config["job"], "source_sha": config["worker_source_sha"],
        "instance_id": "i-0123456789abcdef0", "resource_plan": config["resource_plan"],
        "source_archive": {"path": (r.REMOTE_ROOT / "source.zip").as_posix(), "sha256": config["source_archive_sha256"]},
        "source_manifest": {"path": (r.REMOTE_ROOT / "package" / r.MANIFEST_NAME).as_posix(), "sha256": config["source_manifest_sha256"]},
        "reservation_receipt": {"path": (r.REMOTE_ROOT / "launch/reservation_receipt.json").as_posix(), "sha256": r.sha256(r.canonical(receipt)).hexdigest()},
        "ledger_snapshot": {"path": (r.REMOTE_ROOT / "launch/ledger_snapshot.json").as_posix(), "sha256": r.sha256(r.canonical(ledger)).hexdigest()}}
    return {"job": config["job"], "archive_sha256": config["source_archive_sha256"],
        "cloud_deadline_confirmed": True, "instance_id": plan["instance_id"],
        "deadline": datetime.fromtimestamp(r.time.time() + 3500, timezone.utc).isoformat(),
        "worker_plan": plan, "worker_plan_sha256": r.sha256(r.canonical(plan)).hexdigest(),
        "reservation_receipt": receipt, "ledger_snapshot": ledger}


def result_for(config, permit):
    return {"schema": "cas-meta2-br-construction/8", "status": "BR_COMPONENT_EXECUTED",
        "job": config["job"], "source_sha": config["worker_source_sha"],
        "source_archive_sha256": config["source_archive_sha256"], "source_manifest_sha256": config["source_manifest_sha256"],
        "plan_sha256": permit["worker_plan_sha256"], "training": False, "native_execution": True,
        "task_conditioned_correctness": None, "cleanup_errors": [], "files_sha256": {},
        "prelude": [{"cjt_id": n} for n in ("A", "B", "C", "R")],
        "arms": {a: {"status": "ACCEPTED", "rows": [{"cjt_id": "C"}], "same_fixed_expectation": "L2"} for a in ("B", "R")}}


def test_render_is_standalone_and_embeds_only_generic_helpers(config, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure render must not run anything")
    monkeypatch.setattr(r.subprocess, "run", forbidden)
    monkeypatch.setattr(r.subprocess, "Popen", forbidden)
    source = r.render_remote(config)
    namespace = {"__name__": "synthetic_render_no_main", "__file__": "/absent/remote.py"}
    exec(compile(source, "rendered-br-remote", "exec"), namespace)
    assert namespace["validate_config"](config) == config
    assert namespace["EXPERIMENT"] == r.EXPERIMENT
    assert "cas_meta2.diagnostic_v8.gpu" not in source
    assert "development.zip" not in source
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(sys.modules)


def test_helper_edit_is_refused_before_embedding(config, monkeypatch):
    monkeypatch.setattr(r, "HELPER_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="BR_GENERIC_HELPER_SOURCE_CHANGED"):
        r.render_remote(config)


@pytest.mark.parametrize("key,value", [("max_worker_seconds", 601), ("region", "us-east-1"),
    ("account_id", "wrong"), ("job", "cas-meta2-;bad"), ("bucket", "outside"),
    ("source_archive_bytes", True), ("source_archive_bytes", 17 * 1024**2),
    ("worker_source_sha", "short"), ("source_manifest_sha256", "f" * 64),
    ("artifact_bytes_max", 2**30)])
def test_changed_remote_scope_refused(config, key, value):
    config[key] = value
    with pytest.raises(ValueError, match="BR_REMOTE"):
        r.validate_config(config)


def test_changed_base_or_layout_refused_even_with_resealed_manifest(config):
    config["source_manifest"]["base"]["source_sha"] = "a" * 40
    config["source_manifest_sha256"] = r.sha256(r.canonical(config["source_manifest"])).hexdigest()
    with pytest.raises(ValueError, match="BR_REMOTE_BASE_IDENTITY"):
        r.validate_config(config)


def test_guest_shutdown_precedes_any_network_and_uses_linux_paths(config):
    source = r.user_data(config, "a" * 64)
    assert source.index("sleep 3400") < source.index("timeout 90 aws s3api")
    assert "shutdown -h now' EXIT" in source
    assert "/opt/cas-meta2-br/remote.py" in source and "\\opt\\" not in source
    assert "AWS_MAX_ATTEMPTS=1" in source and "CAS_META2_BR_REMOTE=1" in source
    assert "SUPPORTED_PYTHON_REQUIRED" in source and len(source.encode()) <= 16384


def test_no_local_execution_before_files_or_processes(config, monkeypatch):
    monkeypatch.setattr(r.sys, "platform", "win32")
    with pytest.raises(ValueError, match="BR_AWS_GUEST_REQUIRED"):
        r.run_remote(config)


@pytest.mark.parametrize("key,value", [("max_seconds", 601), ("arm_policy_units", 8193),
    ("prelude_policy_units", 32769), ("training", True), ("binding", 1), ("seed", 8),
    ("prelude", ["A", "B", "C", "R", "C"]), ("arm_expected_symbol", "L1"),
    ("max_image_bytes", 2**30), ("max_cost_usd", "4.01"), ("native_execution", False)])
def test_resealed_changed_worker_plan_refused(config, key, value):
    permit = permit_for(config)
    permit["worker_plan"][key] = value
    permit["worker_plan_sha256"] = r.sha256(r.canonical(permit["worker_plan"])).hexdigest()
    with pytest.raises(ValueError, match="BR_WORKER_PLAN_SCOPE"):
        r.checked_permit(config, permit)


def test_permit_binds_cloud_shutdown_paths_and_reservation_bytes(config):
    permit = permit_for(config)
    assert r.checked_permit(config, permit) > r.time.time()
    for changes, match in (({"cloud_deadline_confirmed": False}, "BR_CLOUD_PERMISSION"),
                           ({"worker_plan_sha256": "0" * 64}, "BR_WORKER_PLAN_HASH"),
                           ({"reservation_receipt": {"changed": True}}, "BR_PLAN_PATH_OR_BYTES"),
                           ({"deadline": "2099-01-01T00:00:00+00:00"}, "BR_UTC_DEADLINE_BOUND")):
        with pytest.raises(ValueError, match=match):
            r.checked_permit(config, {**deepcopy(permit), **changes})


@pytest.mark.parametrize("names", [["../x"], ["/x"], ["x\\y"], ["x:y"], ["x\0y"],
    ["x/./y"], ["x", "X"], ["x", "x/y"], ["x."]])
def test_unsafe_zip_names_refused(names):
    with pytest.raises(ValueError):
        r.checked_names(names)


def source_zip(tmp_path, config, *, extra=None):
    path = tmp_path / "synthetic-source.zip"
    with ZipFile(path, "x") as zipped:
        for name in config["source_manifest"]["files_sha256"]:
            zipped.writestr(name, b"fixture")
        zipped.writestr(r.MANIFEST_NAME, r.canonical(config["source_manifest"]))
        if extra is not None:
            zipped.writestr(extra, b"extra")
    config["source_archive_sha256"] = r.file_hash(path)
    config["source_archive_bytes"] = path.stat().st_size
    return path


def test_extract_checks_every_byte_and_refuses_existing_output(tmp_path, config):
    archive = source_zip(tmp_path, config)
    out = tmp_path / "extracted"
    r.extract_source(archive, out, config)
    assert (out / r.MANIFEST_NAME).read_bytes() == r.canonical(config["source_manifest"])
    with pytest.raises(ValueError, match="BR_SOURCE_ARCHIVE_OR_DESTINATION"):
        r.extract_source(archive, out, config)
    config["source_manifest"]["files_sha256"][config["package_layout"]["dependency_lock"]] = "a" * 64
    with pytest.raises(ValueError, match="BR_ARCHIVE_MEMBER_CHANGED"):
        r.extract_source(archive, tmp_path / "changed", config)
    assert not (tmp_path / "changed").exists()


def test_extra_source_member_refused_before_extract(tmp_path, config):
    archive = source_zip(tmp_path, config, extra="unexpected.txt")
    with pytest.raises(ValueError, match="BR_ARCHIVE_COVERAGE_SIZE_OR_TYPE"):
        r.extract_source(archive, tmp_path / "extracted", config)
    assert not (tmp_path / "extracted").exists()


def test_source_zip_symlink_refused(tmp_path, config):
    archive = source_zip(tmp_path, config)
    with ZipFile(archive) as zipped:
        members = {i.filename: zipped.read(i) for i in zipped.infolist()}
    changed = tmp_path / "link.zip"
    with ZipFile(changed, "x") as zipped:
        for index, (name, raw) in enumerate(members.items()):
            info = ZipInfo(name)
            info.external_attr = (0o120777 if index == 0 else 0o100644) << 16
            zipped.writestr(info, raw)
    config.update(source_archive_sha256=r.file_hash(changed), source_archive_bytes=changed.stat().st_size)
    with pytest.raises(ValueError, match="BR_ARCHIVE_COVERAGE_SIZE_OR_TYPE"):
        r.extract_source(changed, tmp_path / "extracted", config)


def test_complete_result_requires_exact_native_counts_and_files(tmp_path, config):
    permit = permit_for(config)
    result = result_for(config, permit)
    r.write_new(tmp_path / "construction_receipt.json", result)
    assert r.validate_result(tmp_path, config, permit) == result
    (tmp_path / "extra.txt").write_bytes(b"not indexed")
    with pytest.raises(ValueError, match="BR_WORKER_FILE_COVERAGE"):
        r.validate_result(tmp_path, config, permit)


@pytest.mark.parametrize("change", ["refusal", "training", "extra_tick", "missing_arm", "cleanup"])
def test_result_cannot_soften_failure(tmp_path, config, change):
    permit = permit_for(config)
    result = result_for(config, permit)
    if change == "refusal": result["status"] = "BR_CONSTRUCTION_REFUSED_OR_FAILED"
    if change == "training": result["training"] = True
    if change == "extra_tick": result["arms"]["B"]["rows"].append({"cjt_id": "C"})
    if change == "missing_arm": result["arms"].pop("R")
    if change == "cleanup": result["cleanup_errors"].append("failed close")
    r.write_new(tmp_path / "construction_receipt.json", result)
    with pytest.raises(ValueError, match="BR_WORKER"):
        r.validate_result(tmp_path, config, permit)


def fake_guest(tmp_path, config, monkeypatch, *, stage_failure=None, permit_failure=False, collection_failure=False):
    """All command, instance, package-check and worker actions below are fakes."""
    monkeypatch.setattr(r, "REMOTE_ROOT", tmp_path)
    monkeypatch.setattr(r.sys, "platform", "linux")
    monkeypatch.setattr(r.sys, "version_info", (3, 12, 0))
    monkeypatch.setenv("CAS_META2_BR_REMOTE", "1")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", config["job"])
    monkeypatch.setenv("CAS_META2_GUEST_DEADLINE_EPOCH", str(int(r.time.time()) + 3399))
    permit = permit_for(config)
    if permit_failure: permit["cloud_deadline_confirmed"] = False
    archive = source_zip(tmp_path, config)
    permit = permit_for(config) if not permit_failure else {**permit_for(config), "cloud_deadline_confirmed": False}
    commands, uploads, checks = [], {}, []
    def run(argv, **kwargs):
        commands.append(argv)
        assert argv[:2] == ["aws", "s3api"]
        key = argv[argv.index("--key") + 1]
        if argv[2] == "get-object":
            target = Path(argv[argv.index("--key") + 2])
            target.write_bytes(r.canonical(permit) if key == "input/permit.json" else archive.read_bytes())
        else:
            uploads[key] = Path(argv[argv.index("--body") + 1]).read_bytes()
        return SimpleNamespace(returncode=0)
    def stage(argv, directory, **kwargs):
        commands.append(argv)
        directory.mkdir(parents=True)
        (directory / "stdout.txt").write_bytes(b"synthetic stdout")
        (directory / "stderr.txt").write_bytes(b"synthetic stderr")
        r.write_new(directory / "receipt.json", {"pid": 123, "exit_code": 1 if directory.name == stage_failure else 0})
        if directory.name == "worker":
            assert kwargs["seconds"] == 600
            assert kwargs["env"]["CAS_META2_RUN_BR_CONSTRUCTION"] == "1"
            assert "--bundle" not in argv and "--plan-sha256" in argv
            output = Path(argv[argv.index("--output") + 1])
            output.mkdir(parents=True)
            result = result_for(config, permit)
            if directory.name == stage_failure:
                result["status"] = "BR_CONSTRUCTION_REFUSED_OR_FAILED"
                result["failure"] = {"message": "ordinary C refused; no repair substitute"}
            r.write_new(output / "construction_receipt.json", result)
        if directory.name == stage_failure:
            raise ValueError("SYNTHETIC_STAGE_FAILED:" + directory.name)
    monkeypatch.setattr(r.subprocess, "run", run)
    monkeypatch.setattr(r, "stage_process", stage)
    monkeypatch.setattr(r, "instance_identity", lambda: {"accountId": config["account_id"], "region": config["region"],
        "instanceId": permit["instance_id"], "instanceType": "g7.2xlarge"})
    def verify(*args):
        checks.append("source checked")
        return {"source_sha": config["worker_source_sha"], "fixture": True}
    monkeypatch.setattr(r, "verify_package", verify)
    if collection_failure:
        monkeypatch.setattr(r, "collect_artifacts", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("synthetic collection failure")))
    return commands, uploads, checks


@pytest.mark.parametrize("failure", [None, "worker", "torch_install"])
def test_fake_guest_collects_success_or_failure_without_real_execution(tmp_path, config, monkeypatch, failure):
    commands, uploads, checks = fake_guest(tmp_path, config, monkeypatch, stage_failure=failure)
    assert r.run_remote(config) == (0 if failure is None else 1)
    assert len(checks) == 2
    assert set(uploads) == {"results/artifacts.zip", "results/complete.json"}
    complete = json.loads(uploads["results/complete.json"])
    assert complete["returncode"] == (0 if failure is None else 1)
    assert complete["sha256"] == r.sha256(uploads["results/artifacts.zip"]).hexdigest()
    assert complete["experiment"] == r.EXPERIMENT and complete["parent_source_sha"] == config["parent_source_sha"]
    with ZipFile(tmp_path / "artifacts.zip") as zipped:
        receipt = json.loads(zipped.read("lifecycle/remote_receipt.json"))
        assert receipt["neural_training"] is False and receipt["task_conditioned_correctness"] is None
        assert receipt["worker_component_completed"] is (failure is None)
        if failure == "worker":
            native = json.loads(zipped.read("construction/construction_receipt.json"))
            assert native["status"] == "BR_CONSTRUCTION_REFUSED_OR_FAILED"
            assert "ordinary C refused" in native["failure"]["message"]


def test_unconfirmed_shutdown_prevents_source_install_worker(tmp_path, config, monkeypatch):
    commands, uploads, checks = fake_guest(tmp_path, config, monkeypatch, permit_failure=True)
    assert r.run_remote(config) == 1
    assert checks == []
    assert not (tmp_path / "package").exists()
    assert not (tmp_path / "evidence/worker").exists()
    assert all(command[:2] == ["aws", "s3api"] for command in commands)


def test_collection_failure_is_explicit_partial_emergency(tmp_path, config, monkeypatch):
    commands, uploads, checks = fake_guest(tmp_path, config, monkeypatch, collection_failure=True)
    assert r.run_remote(config) == 1
    complete = json.loads(uploads["results/complete.json"])
    assert complete["partial_evidence"] is True and complete["omitted_full_file_count"] is None
    with ZipFile(tmp_path / "failure_artifacts.zip") as zipped:
        receipt = json.loads(zipped.read("artifact_collection_receipt.json"))
        assert receipt["full_file_counts_known"] is False


def test_source_postcheck_failure_is_retained_and_not_success(tmp_path, config, monkeypatch):
    commands, uploads, checks = fake_guest(tmp_path, config, monkeypatch)
    def verify(*args):
        checks.append("attempt")
        if len(checks) == 2: raise ValueError("synthetic source changed")
        return {"fixture": True}
    monkeypatch.setattr(r, "verify_package", verify)
    assert r.run_remote(config) == 1
    with ZipFile(tmp_path / "artifacts.zip") as zipped:
        receipt = json.loads(zipped.read("lifecycle/remote_receipt.json"))
        assert receipt["failure"]["stage"] == "SOURCE_POSTCHECK"
        assert receipt["returncode"] == 1
