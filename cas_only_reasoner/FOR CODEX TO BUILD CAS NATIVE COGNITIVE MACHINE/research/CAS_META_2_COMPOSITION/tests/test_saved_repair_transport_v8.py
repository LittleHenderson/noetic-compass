"""Pure saved-repair contracts. All payloads, accounts and reservations are simulated."""
import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from aws import saved_repair_package_v8 as package
from aws import saved_repair_remote_v8 as remote
from aws import launch_saved_repair_v8 as parent


def request():
    return {"schema": "cas-meta2-saved-repair-launch-request/8", "experiment": parent.EXPERIMENT,
        "job": "cas-meta2-20260906000000-deadbeef", "parent_source_sha": "b" * 40,
        "worker_source_sha": "b" * 40, "parent_file_sha256": {"simulated": "a" * 64},
        "source_archive": "SIMULATED.zip", "source_archive_sha256": "a" * 64,
        "source_archive_bytes": 1234, "source_manifest_sha256": "c" * 64,
        "subnet_id": "subnet-12345678", "resource_plan": parent.resource_plan(), "repair_scope": parent.scope(),
        "standing_authority_registration_required": True, "launch_authorized": False,
        "provider_calls": False, "new_reservation": False}


def manifest():
    names = {"simulated/f%03d" % n: "a" * 64 for n in range(639)}
    names.update({package.PILOT + n: "a" * 64 for n in package.ADDITIONS})
    names[package.DATA_PATH] = package.DATA_SHA
    sizes = {n: 1 for n in names}
    sizes[package.DATA_PATH] = package.DATA_BYTES
    return {"schema": package.SCHEMA, "root_manifest": package.MANIFEST_NAME,
        "source_sha": "b" * 40, "experiment": package.EXPERIMENT,
        "files_sha256": names, "files_bytes": sizes,
        "data": {"path": package.DATA_PATH, "sha256": package.DATA_SHA, "bytes": package.DATA_BYTES,
            "original_job": "cas-meta2-20260906155525-195f5ad8", "role": "inert_prior_failure_archive"},
        "base": {"archive_sha256": package.BASE_SHA, "manifest_sha256": package.BASE_MANIFEST,
            "member_count": 639, "package_layout": {"simulated": True}}}


def config_and_permit(monkeypatch):
    current, source = request(), manifest()
    current["source_manifest_sha256"] = parent.digest(parent.encoded(source))
    config = parent.remote_config(current, source)
    entry = {"job": current["job"], "source_sha": current["worker_source_sha"],
        "archive_sha256": current["source_archive_sha256"], "reserved_usd": "4.00", "plan": current["resource_plan"],
        "status": "RESERVED_NO_AUTOMATIC_REFUND", "plan_sha256": parent.digest(parent.encoded(current["resource_plan"]))}
    ledger = {"owner_task_cap_usd": "400.00", "reservations": [entry]}
    reservation = {"reservation": entry, "ledger_sha256": parent.digest(parent.encoded(ledger))}
    permit = parent.worker_permit(current, source, reservation, ledger, "i-1234567890abcdef0",
        datetime.now(timezone.utc) + timedelta(seconds=3000))
    monkeypatch.setattr(remote, "REMOTE_ROOT", PurePosixPath("/opt/cas-meta2-saved-repair"))
    return current, config, permit


def test_default_is_unpaid_and_imports_are_pure(monkeypatch, capsys):
    monkeypatch.setattr(parent, "execute", lambda *a: pytest.fail("launch called"))
    monkeypatch.setattr(parent, "helpers", lambda *a: pytest.fail("helpers called"))
    assert parent.main([]) == 0
    assert parent.decoded(capsys.readouterr().out)["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert not {"torch", "cas_cjt", "casformer", "boto3", "botocore"}.intersection(sys.modules)


def test_packaged_additions_must_match_committed_parent_identity(monkeypatch):
    current, source = request(), manifest()
    current["parent_file_sha256"] = {n: "a" * 64 for n in package.ADDITIONS}
    monkeypatch.setattr(parent, "read_pinned", lambda *a: b"X" * current["source_archive_bytes"])
    fake = SimpleNamespace(PILOT=package.PILOT, ADDITIONS=package.ADDITIONS, inspect_archive=lambda *a, **kw: source)
    assert parent.source_for(current, fake) == source
    source["files_sha256"][package.PILOT + package.ADDITIONS[0]] = "f" * 64
    with pytest.raises(ValueError, match="SAVED_WORKER_ADDITIONS_DIFFER_FROM_COMMITTED_PARENT"):
        parent.source_for(current, fake)


@pytest.mark.parametrize("field,value", [("max_seconds", 601), ("max_seconds", 600.0),
    ("max_policy_units", 16385), ("max_policy_units", 16384.0), ("max_native_calls", 3),
    ("training", True), ("outer_caller_restored", True), ("automatic_retries", 1), ("max_cost_usd", "5.00")])
def test_request_scope_expansion_refused(field, value):
    current = request()
    current["repair_scope"][field] = value
    with pytest.raises(ValueError, match="SAVED_EXACT_SCOPE"):
        parent.validate_request(current)


@pytest.mark.parametrize("field,value", [("instance_type", "g4dn.xlarge"), ("worker_seconds_max", 601),
    ("runtime_seconds_max", 3601), ("max_policy_units", 16385), ("per_launch_reserved_cap_usd", "5.00")])
def test_resource_changes_refused(field, value):
    current = request()
    current["resource_plan"][field] = value
    with pytest.raises(ValueError, match="SAVED_EXACT_SCOPE"):
        parent.validate_request(current)


def test_parent_remote_gpu_plan_agrees_without_neural_import(monkeypatch):
    from cas_meta2 import saved_repair_gpu_v8 as gpu
    current, config, permit = config_and_permit(monkeypatch)
    parent.validate_request(current)
    remote.validate_config(config)
    assert remote.checked_permit(config, permit) > datetime.now(timezone.utc).timestamp()
    assert gpu.validate_plan(permit["worker_plan"], current["job"]) == permit["worker_plan"]
    assert parent.scope() == remote.FIXED_SCOPE == gpu.FIXED_SCOPE
    assert permit["worker_plan_sha256"] == parent.digest(parent.encoded(permit["worker_plan"]))


@pytest.mark.parametrize("field,value", [("max_native_calls", 3), ("max_policy_units", 16385),
    ("max_seconds", 600.0), ("training", True), ("outer_caller_restored", True)])
def test_resealed_plan_expansions_refused(monkeypatch, field, value):
    _, config, permit = config_and_permit(monkeypatch)
    permit["worker_plan"][field] = value
    permit["worker_plan_sha256"] = parent.digest(parent.encoded(permit["worker_plan"]))
    with pytest.raises(ValueError, match="SAVED_PERMIT_PLAN"):
        remote.checked_permit(config, permit)


def test_generated_remote_has_only_new_run_and_correct_bootstrap(monkeypatch):
    _, config, _ = config_and_permit(monkeypatch)
    raw = remote.render_remote(config)
    nodes = ast.parse(raw).body
    assert sum(isinstance(n, ast.FunctionDef) and n.name == "run_remote" for n in nodes) == 1
    namespace = {"__name__": "pure_rendered_saved_repair", "__file__": "not-read-on-import.py"}
    exec(compile(raw, "<pure-rendered-saved-repair>", "exec"), namespace)
    assert namespace["EXPERIMENT"] == parent.EXPERIMENT
    assert namespace["FIXED_SCOPE"] == parent.scope()
    script = remote.user_data(config, "d" * 64)
    assert "CAS_META2_SAVED_REPAIR_REMOTE=1" in script
    assert "CAS_META2_CHILD_QUALIFICATION_REMOTE" not in script
    assert "/opt/cas-meta2-saved-repair" in script and "3400" in script
    assert "cas_meta2.child_qualification_gpu_v8" not in raw


def fake_lifecycle(tmp_path, monkeypatch, **flags):
    transport = parent.u.load_module("saved_repair_private_chq_lifecycle", "aws/launch_child_qualification_v8.py")
    parent.bind_lifecycle(transport)
    transport.execute = transport.source_for = lambda *a, **k: pytest.fail("old experiment entrypoint called")
    old_tests = Path(__file__).with_name("test_launch_br_construction_v8.py")
    raw = old_tests.read_bytes()
    assert parent.digest(raw) == "b26f5a4b94bf2e03f430f6a263fa627ddea06c24a4c455cb50596f25db6ebfcd"
    wanted = {"MissingObject", "FakeS3", "fake_run"}
    nodes = [n for n in ast.parse(raw).body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in wanted]
    assert {n.name for n in nodes} == wanted
    namespace = {"p": transport, "request": request, "pytest": pytest, "SimpleNamespace": SimpleNamespace,
        "datetime": datetime, "timezone": timezone, "io": io}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(old_tests), "exec"), namespace)
    return namespace["fake_run"](tmp_path, monkeypatch, **flags)


@pytest.mark.parametrize("flag", [None, "failed", "schedule_bad", "uncertain", "ledger_bad"])
def test_private_lifecycle_one_fake_job_and_cleanup_without_old_worker(tmp_path, monkeypatch, flag):
    result, events, ec2, s3 = fake_lifecycle(tmp_path, monkeypatch, **({flag: True} if flag else {}))
    assert events.count("reserve") == 1 and events.count("run_instances") <= 1
    if flag == "ledger_bad":
        assert events == ["reserve"]
    else:
        assert "cleanup" in events
    if flag is None:
        assert events.index("verify_schedule") < events.index("put:input/permit.json")
        assert events.index("verify_packet") < events.index("terminate:True") < events.index("cleanup")
        assert ec2.run["InstanceType"] == "g7.2xlarge"
        permit = parent.decoded(s3.objects["input/permit.json"])
        assert permit["worker_plan"]["max_policy_units"] == 16384
        assert permit["worker_plan"]["max_seconds"] == 600
        assert result["experiment"] == parent.EXPERIMENT
    else:
        assert result["status"] != "AWS_CHILD_QUALIFICATION_FINISHED"


def packet(tmp_path, change=None, failure=False):
    current, plan_hash = request(), "c" * 64
    common = {"job": current["job"], "source_sha": current["worker_source_sha"],
        "parent_source_sha": current["parent_source_sha"], "experiment": parent.EXPERIMENT}
    core = {"status": "REPAIR_RESUMED", "repaired": True, "training": False,
        "native_call_attempts": 2, "returned_native_calls": 2, "completed_new_ticks": 2,
        "accepted_new_ticks": 2, "attempted_policy_units": 144}
    worker = {"schema": "cas-meta2-saved-repair-gpu/8", **common,
        "source_archive_sha256": current["source_archive_sha256"],
        "source_manifest_sha256": current["source_manifest_sha256"], "plan_sha256": plan_hash,
        "status": "SAVED_NATIVE_REPAIR_SUCCEEDED", "training": False, "native_execution": True,
        "outer_caller_restored": False, "failure": None, "cleanup_errors": [], "repair": core,
        "postchecks": {k: {"ok": True} for k in
            ("source", "reservation", "accepted_sources", "original_database", "output_bound", "deadline")}}
    if failure:
        worker.update(status="SAVED_NATIVE_REPAIR_REFUSED_OR_FAILED", failure={"type": "SIMULATED"})
        core.update(status="REPAIR_REFUSED", repaired=False, completed_new_ticks=0, accepted_new_ticks=0)
    if change:
        change(worker, core)
    members = {"repair/repair/repair_receipt.json": parent.encoded(core)}
    worker["files_sha256"] = {n.removeprefix("repair/"): parent.digest(raw) for n, raw in members.items()}
    members["repair/worker_receipt.json"] = parent.encoded(worker)
    collection = {**common, "returncode": 1 if failure else 0, "partial_evidence": False,
        "omitted_full_file_count": 0, "original_file_count": len(members), "included_full_file_count": len(members),
        "files": {n: {"bytes": len(raw), "sha256": parent.digest(raw)} for n, raw in members.items()}}
    path = tmp_path / "SIMULATED.zip"
    with ZipFile(path, "x", ZIP_DEFLATED) as archive:
        for n, raw in members.items():
            archive.writestr(n, raw)
        archive.writestr("artifact_collection_receipt.json", parent.encoded(collection))
    result = {**common, "returncode": collection["returncode"], "bytes": path.stat().st_size,
        "sha256": parent.digest(path.read_bytes()), "partial_evidence": False, "omitted_full_file_count": 0}
    return path, result, current, plan_hash


def test_complete_and_negative_packets_preserve_exact_claim_boundary(tmp_path):
    result = parent.verify_packet(*packet(tmp_path))
    assert result["native_success"] is True
    assert "no restored outer caller" in result["boundary"]


def test_negative_worker_receipt_is_retained_not_promoted(tmp_path):
    result = parent.verify_packet(*packet(tmp_path, failure=True))
    assert result["native_success"] is False
    assert result["worker_receipt"]["repair"]["completed_new_ticks"] == 0
    assert result["worker_receipt"]["failure"] == {"type": "SIMULATED"}


def test_partial_collection_preserves_worker_and_marks_missing_files(tmp_path):
    path, result, current, plan = packet(tmp_path, failure=True)
    with ZipFile(path) as archive:
        members = {n: archive.read(n) for n in archive.namelist()}
    receipt = parent.decoded(members["artifact_collection_receipt.json"])
    del members["repair/repair/repair_receipt.json"]
    members["failure_tails/0.txt"] = b"SIMULATED failure tail"
    receipt.update(partial_evidence=True, included_full_file_count=1, omitted_full_file_count=1)
    members["artifact_collection_receipt.json"] = parent.encoded(receipt)
    changed = tmp_path / "partial.zip"
    with ZipFile(changed, "x", ZIP_DEFLATED) as archive:
        for n, raw in members.items():
            archive.writestr(n, raw)
    result.update(bytes=changed.stat().st_size, sha256=parent.digest(changed.read_bytes()),
        partial_evidence=True, omitted_full_file_count=1)
    checked = parent.verify_packet(changed, result, current, plan)
    assert checked["native_success"] is checked["original_member_coverage_verified"] is False
    assert checked["worker_receipt"]["status"] == "SAVED_NATIVE_REPAIR_REFUSED_OR_FAILED"
    assert checked["missing_worker_files"] == ["repair/repair/repair_receipt.json"]
    assert checked["files_verified"] == 1 and len(checked["failure_tail_hashes"]) == 1


def test_remote_result_checks_exact_saved_core_copy(tmp_path, monkeypatch):
    _, config, permit = config_and_permit(monkeypatch)
    path, result, current, plan = packet(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    with ZipFile(path) as archive:
        for n in archive.namelist():
            if n.startswith("repair/"):
                dest = output / n.removeprefix("repair/")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.read(n))
    config["source_manifest_sha256"] = current["source_manifest_sha256"]
    permit["worker_plan_sha256"] = plan
    assert remote.validate_result(output, config, permit)["status"] == "SAVED_NATIVE_REPAIR_SUCCEEDED"
    record = parent.decoded((output / "worker_receipt.json").read_bytes())
    record["postchecks"]["deadline"] = {"ok": False}
    (output / "worker_receipt.json").write_bytes(parent.encoded(record))
    with pytest.raises(ValueError, match="SAVED_WORKER_SUCCESS_IDENTITY"):
        remote.validate_result(output, config, permit)


@pytest.mark.parametrize("check", ["source", "reservation", "accepted_sources", "original_database", "output_bound", "deadline"])
def test_each_failed_postcheck_blocks_success(tmp_path, check):
    args = packet(tmp_path, lambda worker, core: worker["postchecks"].update({check: {"ok": False}}))
    with pytest.raises(ValueError, match="SAVED_COMPLETE_REPAIR_REQUIRED"):
        parent.verify_packet(*args)


@pytest.mark.parametrize("field,value", [("native_call_attempts", 1), ("returned_native_calls", 1),
    ("completed_new_ticks", None), ("accepted_new_ticks", 1), ("accepted_new_ticks", 2.0),
    ("attempted_policy_units", 16385), ("attempted_policy_units", 0)])
def test_counts_and_compute_cannot_be_promoted(tmp_path, field, value):
    args = packet(tmp_path, lambda worker, core: core.update({field: value}))
    with pytest.raises(ValueError, match="SAVED_CORE_REPAIR_REQUIRED"):
        parent.verify_packet(*args)


def test_outer_caller_claim_cannot_be_promoted(tmp_path):
    args = packet(tmp_path, lambda worker, core: worker.update(outer_caller_restored=True))
    with pytest.raises(ValueError, match="SAVED_WORKER_BINDING"):
        parent.verify_packet(*args)


def synthetic_members(monkeypatch):
    base = {"simulated/f%03d" % n: b"SIMULATED" for n in range(639)}
    identity = {"source_sha": package.BASE_SOURCE, "archive_sha256": package.BASE_SHA,
        "archive_bytes": package.BASE_BYTES, "manifest_sha256": package.BASE_MANIFEST,
        "root_manifest": "child_qualification_source_manifest.json", "member_count": 639, "package_layout": {}}
    def check_base(values):
        assert values == base
        return identity
    monkeypatch.setattr(package, "base_identity", check_base)
    data = b"INERT SIMULATED DATA"
    monkeypatch.setattr(package, "DATA_SHA", package.digest(data))
    monkeypatch.setattr(package, "DATA_BYTES", len(data))
    members = {**base, **{package.PILOT + n: b"# SIMULATED SOURCE" for n in package.ADDITIONS}, package.DATA_PATH: data}
    document = package.manifest_for(members, "b" * 40)
    members[package.MANIFEST_NAME] = package.canonical(document)
    return members, document


def test_synthetic_closed_644_package_hashes_and_no_execution_claim(monkeypatch):
    members, document = synthetic_members(monkeypatch)
    assert len(members) == 644
    assert package.validate_members(members, source_sha="b" * 40,
        manifest_sha256=package.digest(package.canonical(document))) == document
    assert document["launch_enabled"] is document["training"] is document["native_execution"] is False
    assert len(document["additions"]) == 3 and document["data"]["role"] == "inert_prior_failure_archive"


@pytest.mark.parametrize("mutation", ["extra", "missing", "data", "source"])
def test_synthetic_package_changed_bytes_or_members_refused(monkeypatch, mutation):
    members, document = synthetic_members(monkeypatch)
    name = package.PILOT + package.ADDITIONS[0]
    if mutation == "extra":
        members["extra.py"] = b"changed"
    elif mutation == "missing":
        del members[name]
    else:
        members[package.DATA_PATH if mutation == "data" else name] = b"changed"
    with pytest.raises(ValueError):
        package.validate_members(members, source_sha="b" * 40,
            manifest_sha256=package.digest(package.canonical(document)))


def test_existing_output_refused_before_input_reads(tmp_path, monkeypatch):
    monkeypatch.setattr(package, "ROOT", tmp_path)
    output = tmp_path / "records/existing"
    output.mkdir(parents=True)
    monkeypatch.setattr(package, "read_file", lambda *a: pytest.fail("input read before output check"))
    with pytest.raises(ValueError, match="SAVED_REPAIR_NEW_OUTPUT_REQUIRED"):
        package.build_package("unused", "unused", output, source_sha="b" * 40)
