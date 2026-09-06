"""Pure inspection-parent tests. Providers, budget, and all SQLite data are fake."""
import ast
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
from types import SimpleNamespace
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from aws import launch_native_failure_inspection_v8 as p


def request():
    ids = {name: "a" * 64 for name in (*p.PARENT_FILES, *p.FROZEN_PINS)}
    source = p.input_manifest("b" * 40, ids)
    return {"schema": "cas-meta2-native-failure-inspection-request/8", "experiment": p.EXPERIMENT,
        "job": "cas-meta2-20260906000000-deadbeef", "parent_source_sha": "b" * 40,
        "worker_source_sha": "b" * 40, "parent_file_sha256": ids,
        "source_archive": "SIMULATED.zip", "source_archive_sha256": p.EVIDENCE_SHA256,
        "source_archive_bytes": p.EVIDENCE_BYTES, "original_job": p.ORIGINAL_JOB,
        "inspection_input_manifest": source, "source_manifest_sha256": p.digest(p.encoded(source)),
        "subnet_id": "subnet-12345678", "resource_plan": p.resource_plan(),
        "standing_authority_registration_required": True, "launch_authorized": False,
        "provider_calls": False, "new_reservation": False}


def test_default_never_calls_helpers_or_paid_function(capsys, monkeypatch):
    monkeypatch.setattr(p, "helpers", lambda *a: pytest.fail("helper called"))
    monkeypatch.setattr(p, "execute", lambda *a: pytest.fail("paid function called"))
    assert p.main([]) == 0
    value = p.decoded(capsys.readouterr().out)
    assert value["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert value["training"] is value["native_execution"] is False
    assert value["sqlite_read_only"] is True
    assert not {"boto3", "botocore", "torch", "cas_cjt", "casformer"}.intersection(sys.modules)


@pytest.mark.parametrize("field,value", [
    ("worker_seconds_max", 181), ("worker_seconds_max", 180.0), ("runtime_seconds_max", 3601),
    ("training", True), ("native_execution", True), ("sqlite_read_only", False),
    ("instance_type", "g4dn.xlarge"), ("automatic_retries", 1), ("per_launch_reserved_cap_usd", "5.00")])
def test_resource_expansion_refused(field, value):
    current = request()
    current["resource_plan"][field] = value
    with pytest.raises(ValueError, match="INSPECTION_SCOPE_CHANGED"):
        p.validate_request(current)


@pytest.mark.parametrize("field,value", [
    ("job", p.ORIGINAL_JOB), ("experiment", {"profile": "one_child_full_task_qualification_v8"}),
    ("source_archive_sha256", "0" * 64), ("source_archive_bytes", p.EVIDENCE_BYTES + 1),
    ("source_manifest_sha256", "0" * 64), ("launch_authorized", True),
    ("worker_source_sha", "c" * 40)])
def test_request_cannot_reuse_old_job_or_other_evidence(field, value):
    current = request()
    current[field] = value
    with pytest.raises(ValueError):
        p.validate_request(current)


def test_real_parent_remote_permit_interface_uses_fake_ledger():
    from aws import native_failure_inspection_v8 as remote
    current = p.validate_request(request())
    config = p.remote_config(current, current["inspection_input_manifest"])
    remote.validate_config(config)
    reservation = {"job": current["job"], "source_sha": current["worker_source_sha"],
        "archive_sha256": current["source_archive_sha256"], "reserved_usd": "4.00", "plan": current["resource_plan"],
        "status": "RESERVED_NO_AUTOMATIC_REFUND", "plan_sha256": p.digest(p.encoded(current["resource_plan"]))}
    ledger = {"owner_task_cap_usd": "400.00", "reservations": [reservation]}
    receipt = {"reservation": reservation, "ledger_sha256": p.digest(p.encoded(ledger))}
    permit = p.worker_permit(current, {}, receipt, ledger, "i-1234567890abcdef0",
                             datetime.now(timezone.utc) + timedelta(seconds=1000))
    identity = {"instanceId": permit["instance_id"], "accountId": config["account_id"],
                "region": config["region"], "instanceType": "g7.2xlarge"}
    assert remote.checked_permit(config, permit, identity) > datetime.now(timezone.utc).timestamp()
    assert permit["worker_plan"]["max_seconds"] == 180
    assert permit["worker_plan"]["native_execution"] is False
    assert permit["worker_plan_sha256"] == p.digest(p.encoded(permit["worker_plan"]))
    assert config["inspection_input_manifest"]["exporter_source_sha256"] == "a" * 64


def fake_lifecycle(tmp_path, monkeypatch, **flags):
    """Reuse only byte-pinned synthetic definitions, with the real private lifecycle."""
    transport = p.load_module("inspection_private_chq_lifecycle", "aws/launch_child_qualification_v8.py")
    p.bind_lifecycle(transport)
    transport.execute = transport.source_for = lambda *a, **k: pytest.fail("old experiment entrypoint called")
    old_tests = Path(__file__).with_name("test_launch_br_construction_v8.py")
    raw = old_tests.read_bytes()
    assert p.digest(raw) == "b26f5a4b94bf2e03f430f6a263fa627ddea06c24a4c455cb50596f25db6ebfcd"
    wanted = {"MissingObject", "FakeS3", "fake_run"}
    nodes = [node for node in ast.parse(raw).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
             and node.name in wanted]
    assert {node.name for node in nodes} == wanted
    namespace = {"p": transport, "request": request, "pytest": pytest, "SimpleNamespace": SimpleNamespace,
                 "datetime": datetime, "timezone": timezone, "io": io}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(old_tests), "exec"), namespace)
    return namespace["fake_run"](tmp_path, monkeypatch, **flags)


def test_real_pinned_lifecycle_single_fake_reservation_launch_and_cleanup(tmp_path, monkeypatch):
    result, events, ec2, s3 = fake_lifecycle(tmp_path, monkeypatch)
    assert result["experiment"] == p.EXPERIMENT
    assert events.count("reserve") == events.count("run_instances") == 1
    assert events.index("reserve") < events.index("run_instances") < events.index("verify_schedule") < events.index("put:input/permit.json")
    assert events.index("verify_packet") < events.index("terminate:True") < events.index("cleanup")
    assert result["termination_confirmed"] is result["artifact_verified"] is True
    assert ec2.run["InstanceType"] == "g7.2xlarge"
    permit = p.decoded(s3.objects["input/permit.json"])
    assert permit["worker_plan"]["max_seconds"] == 180 and permit["worker_plan"]["sqlite_read_only"] is True
    assert permit["worker_plan"]["native_execution"] is False


@pytest.mark.parametrize("flag", ["failed", "schedule_bad", "uncertain", "ledger_bad"])
def test_fake_lifecycle_failure_is_retained_without_retry(tmp_path, monkeypatch, flag):
    result, events, _, _ = fake_lifecycle(tmp_path, monkeypatch, **{flag: True})
    assert events.count("reserve") == 1 and events.count("run_instances") <= 1
    assert result["status"] != "AWS_CHILD_QUALIFICATION_FINISHED"
    assert (tmp_path / "fake_run/launch_receipt.json").is_file()
    if flag == "ledger_bad":
        assert events == ["reserve"]
    else:
        assert "cleanup" in events


def test_private_adapter_does_not_change_fresh_original_module():
    private = p.load_module("inspection_private_chq_lifecycle", "aws/launch_child_qualification_v8.py")
    other = p.load_module("inspection_unmodified_comparison", "aws/launch_child_qualification_v8.py")
    original = other.EXPERIMENT.copy()
    entry = p.bind_lifecycle(private)
    assert entry.__globals__ is private.__dict__
    assert private.EXPERIMENT == p.EXPERIMENT and other.EXPERIMENT == original != p.EXPERIMENT
    assert private.verify_packet is p.verify_packet and private.worker_permit is p.worker_permit
    assert private.verify_parent_source is p.verify_parent_source
    with pytest.raises(ValueError, match="PRIVATE_TRANSPORT"):
        p.bind_lifecycle(other)


def packet(tmp_path, change=None, failure=False, corrupt=False):
    current, plan_hash = request(), "c" * 64
    common = {"job": current["job"], "source_sha": current["worker_source_sha"],
              "parent_source_sha": current["parent_source_sha"], "experiment": p.EXPERIMENT}
    exported = {**{k: v for k, v in common.items() if k != "experiment"}, "plan_sha256": plan_hash,
        "database": {"archive_sha256": p.EVIDENCE_SHA256, "member": p.DB_MEMBER,
            "sha256": "e" * 64, "bytes": 1024, "sidecars_present": False, "historical_uncaptured_state_recovered": False},
        "quick_check": "ok", "read_only_uri": True,
        "query_only": True, "trusted_schema": False, "authorizer_select_only": True,
        "tables": {name: {"columns": ["SIMULATED"], "row_count": 0, "rows": []} for name in p.TABLES}, "total_rows": 0}
    receipt = {**common, "schema": "cas-meta2-native-failure-inspection/8",
        "plan_sha256": plan_hash, "source_archive_sha256": p.EVIDENCE_SHA256,
        "database": exported["database"], "status": "NATIVE_FAILURE_DATABASE_EXPORTED",
        "training": False, "native_execution": False, "sqlite_read_only": True,
        "input_unchanged": True, "failure": None, "total_rows": 0, "table_counts": {name: 0 for name in p.TABLES}}
    if failure:
        receipt.update(status="INSPECTION_FAILED", failure={"type": "SIMULATED"}, input_unchanged=False)
    if change:
        change(receipt, exported)
    members = {"inspection/receipt.json": p.encoded(receipt)}
    if not failure:
        members["inspection/export.json"] = p.encoded(exported)
    collection = {**common, "returncode": 1 if failure else 0, "partial_evidence": False,
        "omitted_full_file_count": 0,
        "files": {name: {"bytes": len(raw), "sha256": p.digest(raw)} for name, raw in members.items()}}
    if corrupt:
        members["inspection/receipt.json"] += b"changed"
    path = tmp_path / "fake-output.zip"
    with ZipFile(path, "x", ZIP_DEFLATED) as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
        archive.writestr("artifact_collection_receipt.json", p.encoded(collection))
    result = {**common, "returncode": collection["returncode"], "bytes": path.stat().st_size,
              "sha256": p.digest(path.read_bytes())}
    return path, result, current, plan_hash


def test_success_packet_is_only_a_read_only_export(tmp_path):
    result = p.verify_packet(*packet(tmp_path))
    assert result["inspection_success"] is True and result["files_verified"] == 2
    assert "no model" in result["boundary"]


def test_failed_export_packet_still_hash_verified_without_missing_export(tmp_path):
    result = p.verify_packet(*packet(tmp_path, failure=True))
    assert result["inspection_success"] is False and result["files_verified"] == 1
    assert result["worker_receipt"]["failure"] == {"type": "SIMULATED"}


def test_changed_member_refused_even_if_outer_archive_resealed(tmp_path):
    with pytest.raises(ValueError, match="MEMBER_CHANGED"):
        p.verify_packet(*packet(tmp_path, corrupt=True))


@pytest.mark.parametrize("field,value", [("training", True), ("native_execution", True),
    ("sqlite_read_only", False), ("input_unchanged", False), ("plan_sha256", "d" * 64),
    ("source_archive_sha256", "d" * 64), ("failure", {"type": "simulated"}),
    ("status", "CHILD_CURRICULUM_NATIVE_QUALIFIED")])
def test_resealed_false_success_is_refused(tmp_path, field, value):
    with pytest.raises(ValueError, match="WORKER_RECEIPT"):
        p.verify_packet(*packet(tmp_path, change=lambda r, e: r.update({field: value})))


def test_resealed_export_identity_mismatch_is_refused(tmp_path):
    with pytest.raises(ValueError, match="EXPORT_REQUIRED"):
        p.verify_packet(*packet(tmp_path, change=lambda r, e: e.update(job="wrong")))


@pytest.mark.parametrize("fault", ["missing_table", "row_count", "database_member", "total_rows"])
def test_resealed_export_counts_and_database_scope_are_checked(tmp_path, fault):
    def change(receipt, exported):
        if fault == "missing_table":
            exported["tables"].pop("trace_events")
        elif fault == "row_count":
            exported["tables"]["trace_events"]["row_count"] = 1
        elif fault == "database_member":
            exported["database"]["member"] = "another.db"
        else:
            receipt["total_rows"] = exported["total_rows"] = 1
    with pytest.raises(ValueError):
        p.verify_packet(*packet(tmp_path, change=change))


def authority_fixture(tmp_path, monkeypatch):
    current = request()
    campaign, message = tmp_path / "FAKE-campaign", tmp_path / "FAKE-message"
    campaign.write_bytes(b"SIMULATED campaign")
    message.write_bytes(b"SIMULATED standing direction")
    monkeypatch.setattr(p, "STANDING_MESSAGE_SHA256", p.digest(message.read_bytes()))
    ledger = {"approval": {"path": str(campaign), "sha256": p.digest(campaign.read_bytes())},
              "owner_task_cap_usd": "400.00", "no_automatic_refund": True}
    req_hash = p.digest(p.encoded(current))
    record = {"schema": "cas-meta2-native-failure-inspection-standing-authority/8",
        "standing_campaign_authorization": True, "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00",
        "experiment": p.EXPERIMENT, "training": False, "native_execution": False, "sqlite_read_only": True,
        "launch_request_sha256": req_hash, **{k: current[k] for k in ("job", "parent_source_sha",
            "worker_source_sha", "source_archive_sha256", "source_manifest_sha256", "original_job")},
        "campaign_approval": ledger["approval"],
        "standing_user_message": {"path": str(message), "sha256": p.STANDING_MESSAGE_SHA256}}
    path = tmp_path / "FAKE-authority.json"
    path.write_bytes(p.encoded(record))
    return current, req_hash, record, path, ledger


def test_authority_requires_existing_campaign_and_full_message(tmp_path, monkeypatch):
    current, req_hash, record, path, ledger = authority_fixture(tmp_path, monkeypatch)
    assert p.validate_authority(path, p.digest(path.read_bytes()), current, req_hash, ledger)["sqlite_read_only"] is True
    Path(record["standing_user_message"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="PINNED_BYTES"):
        p.validate_authority(path, p.digest(path.read_bytes()), current, req_hash, ledger)


@pytest.mark.parametrize("field,value", [("job", p.ORIGINAL_JOB), ("sqlite_read_only", False),
    ("max_job_cost_usd", "5.00"), ("native_execution", True), ("standing_campaign_authorization", 1)])
def test_authority_cannot_expand_or_reuse_prior_job(tmp_path, monkeypatch, field, value):
    current, req_hash, record, path, ledger = authority_fixture(tmp_path, monkeypatch)
    record[field] = value
    path.write_bytes(p.encoded(record))
    with pytest.raises(ValueError, match="AUTHORITY_SCOPE_CHANGED"):
        p.validate_authority(path, p.digest(path.read_bytes()), current, req_hash, ledger)


@pytest.mark.parametrize("failure", ["lock", "authority", "preflight"])
def test_outer_refusal_never_reserves_or_uses_old_execute(tmp_path, monkeypatch, failure):
    current = request()
    path = tmp_path / "FAKE-request.json"
    path.write_bytes(p.encoded(current))
    calls = []
    def fail(label):
        calls.append(label)
        raise ValueError("SIMULATED " + label)
    old = SimpleNamespace(campaign_execution_lock=lambda: fail("lock") if failure == "lock" else nullcontext(),
        budget=SimpleNamespace(read_ledger=lambda: {"remaining_unreserved_usd": "310.00"},
            reserve_budget=lambda *a: pytest.fail("unexpected reservation")))
    plumbing = SimpleNamespace(client_factory=lambda *a: calls.append("clients") or {},
        provider_preflight=lambda *a: fail("preflight"))
    monkeypatch.setattr(p, "ROOT", tmp_path)
    monkeypatch.setattr(p, "resource_plan", lambda: current["resource_plan"])
    monkeypatch.setattr(p, "helpers", lambda *a: {"identity": current["parent_file_sha256"],
        "old": old, "plumbing": plumbing})
    monkeypatch.setattr(p, "source_for", lambda *a: current["inspection_input_manifest"])
    monkeypatch.setattr(p, "verify_parent_source", lambda *a: current["parent_file_sha256"])
    monkeypatch.setattr(p, "validate_authority", lambda *a: fail("authority") if failure == "authority" else {})
    result = p.execute(path, p.digest(path.read_bytes()), "FAKE", "c" * 64, tmp_path / "records/refusal")
    assert result["status"] == "AWS_NATIVE_FAILURE_INSPECTION_REFUSED_OR_FAILED"
    assert result["new_reservation"] is result["provider_resources_created"] is False
    assert "clients" not in calls if failure != "preflight" else True
    assert p.decoded((tmp_path / "records/refusal/launch_receipt.json").read_bytes()) == result
