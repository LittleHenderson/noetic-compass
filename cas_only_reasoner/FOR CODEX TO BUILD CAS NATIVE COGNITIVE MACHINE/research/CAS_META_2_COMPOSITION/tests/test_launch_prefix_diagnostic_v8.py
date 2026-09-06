"""Pure dedicated-parent tests. Every provider and reservation in tests is fake."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import io
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from aws import launch_prefix_diagnostic_v8 as p


def request():
    return {"schema": "cas-meta2-prefix-launch-request/8", "experiment": p.EXPERIMENT,
        "job": "cas-meta2-20260906000000-deadbeef", "parent_source_sha": "a" * 40,
        "parent_file_sha256": {name: "b" * 64 for name in p.PARENT_FILES},
        "worker_source_sha": p.WORKER_SOURCE_SHA, "source_archive_sha256": p.SOURCE_ARCHIVE_SHA,
        "development_archive_sha256": p.DEVELOPMENT_ARCHIVE_SHA, "bundle_manifest_sha256": p.BUNDLE_MANIFEST_SHA,
        "source_archive": "source.zip", "development_bundle": "bundle_001", "development_archive": "development.zip",
        "resource_plan": p.resource_plan(), "subnet_id": "subnet-12345678", "approval_required": True,
        "launch_authorized": False, "task_counts": {"train_probe": 24, "validation": 96, "checkpoints": 4,
            "reference_decisions_per_checkpoint": 2272, "forced_per_checkpoint": 360}}


def test_default_plan_never_imports_provider_or_neural_modules(monkeypatch, capsys):
    class Guard:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {"boto3", "botocore", "torch", "casformer", "cas_cjt", "numpy"}:
                raise AssertionError("Forbidden import: " + fullname)
    monkeypatch.setattr(sys, "meta_path", [Guard(), *sys.meta_path])
    monkeypatch.setattr(p, "client_factory", lambda *a: pytest.fail("Provider path reached"))
    assert p.main([]) == 0
    out = p.decoded(capsys.readouterr().out)
    assert out["approval_required"] is True
    assert out["provider_calls"] is False and out["new_reservation"] is False
    assert out["resource_plan"]["training"] is False


def test_execute_without_future_approval_is_refused_before_helpers(monkeypatch, tmp_path):
    raw = p.encoded(request())
    path = tmp_path / "request.json"
    path.write_bytes(raw)
    monkeypatch.setattr(p, "helpers", lambda *a: pytest.fail("Helper import before approval"))
    monkeypatch.setattr(p, "client_factory", lambda *a: pytest.fail("Provider import before approval"))
    with pytest.raises(p.LaunchRefused, match="EXACT_SHA256_REQUIRED"):
        p.execute(path, p.digest(raw), None, None, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def approval_fixture(tmp_path, text="Approve the $4 diagnostic."):
    current = request()
    request_sha = p.digest(p.encoded(current))
    message = tmp_path / "synthetic_unit_test_message.txt"
    message.write_text(text, encoding="utf-8")
    approval = {"schema": "cas-meta2-prefix-owner-approval/8", "approved": True,
        "launch_request_sha256": request_sha, "job": current["job"],
        "parent_source_sha": current["parent_source_sha"], "worker_source_sha": p.WORKER_SOURCE_SHA,
        "source_archive_sha256": p.SOURCE_ARCHIVE_SHA, "development_archive_sha256": p.DEVELOPMENT_ARCHIVE_SHA,
        "bundle_manifest_sha256": p.BUNDLE_MANIFEST_SHA, "max_cost_usd": "4.00",
        "user_message": {"path": str(message.absolute()), "sha256": p.digest(message.read_bytes())}}
    path = tmp_path / "synthetic_unit_test_approval.json"
    raw = p.encoded(approval)
    path.write_bytes(raw)
    return current, request_sha, approval, path, p.digest(raw)


def test_exact_future_approval_binds_message_request_job_and_both_sources(tmp_path):
    current, request_sha, approval, path, sha = approval_fixture(tmp_path)
    result = p.validate_owner_approval(path, sha, current, request_sha)
    assert result["parent_source_sha"] != result["worker_source_sha"]
    assert result["max_cost_usd"] == "4.00"
    assert result["user_message"]["sha256"] == approval["user_message"]["sha256"]


@pytest.mark.parametrize("text", ["go", "approved for $100", "No paid launch until I approve it.",
    "Please ask me to say: Approve the $4 diagnostic.", "Approve the $7 training."])
def test_previous_authorization_or_quoted_approval_is_not_launch_permission(tmp_path, text):
    current, request_sha, _, path, sha = approval_fixture(tmp_path, text)
    with pytest.raises(p.LaunchRefused, match="EXACT_USER_APPROVAL_LINE_REQUIRED"):
        p.validate_owner_approval(path, sha, current, request_sha)


@pytest.mark.parametrize("key,value", [("job", "cas-meta2-20260906000000-12345678"),
    ("parent_source_sha", "c" * 40), ("worker_source_sha", "c" * 40),
    ("launch_request_sha256", "c" * 64), ("max_cost_usd", "7.00")])
def test_approval_binding_mutations_are_refused(tmp_path, key, value):
    current, request_sha, approval, path, _ = approval_fixture(tmp_path)
    approval[key] = value
    raw = p.encoded(approval); path.write_bytes(raw)
    with pytest.raises(p.LaunchRefused, match="EXPLICIT_JOB_SPECIFIC_FUTURE_OWNER_APPROVAL_REQUIRED"):
        p.validate_owner_approval(path, p.digest(raw), current, request_sha)


@pytest.mark.parametrize("field,value", [("instance_type", "g4dn.xlarge"), ("runtime_seconds_max", 3601),
    ("worker_seconds_max", 1801), ("automatic_retries", 1), ("per_launch_reserved_cap_usd", "7.00"),
    ("training", True), ("later_curriculum_execution", True), ("ebs_iops", 16000)])
def test_scope_or_resource_expansion_is_refused(field, value):
    current = request(); current["resource_plan"][field] = value
    with pytest.raises(p.LaunchRefused, match="EXACT_DIAGNOSTIC_SCOPE_AND_RESOURCE_PLAN_REQUIRED"):
        p.validate_request(current)


def test_real_instance_is_required_before_enabled_plan_can_be_sealed():
    with pytest.raises(p.LaunchRefused, match="REAL_INSTANCE_ID_REQUIRED"):
        p.worker_permit(request(), {}, {}, {}, "pending", datetime.now(timezone.utc))


def test_enabled_plan_binds_reservation_snapshot_and_frozen_worker():
    reservation, ledger = {"test": "reservation"}, {"test": "ledger"}
    permit = p.worker_permit(request(), {}, reservation, ledger, "i-1234567890abcdef0", datetime.now(timezone.utc))
    plan = permit["worker_plan"]
    from cas_meta2.diagnostic_v8.gpu import plan_bounds
    plan_bounds(plan, request()["job"], p.BUNDLE_MANIFEST_SHA)
    assert plan["source_sha"] == p.WORKER_SOURCE_SHA != request()["parent_source_sha"]
    assert plan["source_archive"]["sha256"] == p.SOURCE_ARCHIVE_SHA
    assert plan["reservation_receipt"]["sha256"] == p.digest(p.encoded(reservation))
    assert plan["ledger_snapshot"]["sha256"] == p.digest(p.encoded(ledger))
    assert permit["worker_plan_sha256"] == p.digest(p.encoded(plan))
    assert plan["source_manifest"]["path"] == "/opt/cas-meta2-prefix/package/prefix_source_manifest.json"


class MissingObject(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class FakeS3:
    def __init__(self, events, current, returncode=0):
        self.events, self.current = events, current
        self.objects = {"results/artifacts.zip": b"synthetic-test-packet", "results/bootstrap.log": b"test log"}
        self.result = {"job": current["job"], "source_sha": p.WORKER_SOURCE_SHA,
            "experiment": p.EXPERIMENT, "returncode": returncode,
            "sha256": p.digest(self.objects["results/artifacts.zip"]), "bytes": len(self.objects["results/artifacts.zip"])}
        self.objects["results/complete.json"] = p.encoded(self.result)

    def __getattr__(self, name):
        def call(**kwargs):
            self.events.append(name)
            return {}
        return call

    def put_object(self, **kwargs):
        self.events.append("put:" + kwargs["Key"])
        self.objects[kwargs["Key"]] = kwargs["Body"]
        return {}

    def get_object(self, **kwargs):
        key = kwargs["Key"]
        if key not in self.objects:
            raise MissingObject()
        raw = self.objects[key]
        return {"ContentLength": len(raw), "Body": io.BytesIO(raw)}

    def head_object(self, **kwargs):
        key = kwargs["Key"]
        if key not in self.objects:
            raise MissingObject()
        return {"ContentLength": len(self.objects[key])}

    def get_bucket_tagging(self, **kwargs):
        return {"TagSet": [{"Key": "cas_meta_job", "Value": self.current["job"]}]}

    def list_objects_v2(self, **kwargs):
        return {"Contents": [{"Key": k, "Size": len(v), "LastModified": datetime.now(timezone.utc)}
                             for k, v in self.objects.items() if k.startswith("results/")]}


def fake_run(tmp_path, monkeypatch, *, failed=False, schedule_bad=False, uncertain=False, ledger_bad=False):
    current, events = request(), []
    ledger = {"revision": 1, "remaining_unreserved_usd": "318.00"}
    def reserve(*args):
        events.append("reserve")
        assert args == (current["job"], p.WORKER_SOURCE_SHA, p.SOURCE_ARCHIVE_SHA, "4.00", current["resource_plan"])
        return {"ledger_sha256": p.digest(p.encoded(ledger)), "reservation": {"job": current["job"]}}
    def read_ledger():
        if ledger_bad:
            raise ValueError("synthetic snapshot failure")
        return ledger
    budget = SimpleNamespace(reserve_budget=reserve, read_ledger=read_ledger)
    def verify_schedule(confirmed, target, expression):
        events.append("verify_schedule")
        if schedule_bad:
            raise ValueError("synthetic bad schedule")
        assert confirmed["Target"] == target and confirmed["ScheduleExpression"] == expression
    def verify_packet(path, result, job, source, plan, **kwargs):
        assert p.digest(path.read_bytes()) == result["sha256"]
        assert source == p.WORKER_SOURCE_SHA and kwargs["experiment"] == p.EXPERIMENT
        events.append("verify_packet")
        return {"returncode": result["returncode"], "partial_evidence": failed}
    def terminate(*args, artifact_verified, record):
        events.append("terminate:" + str(artifact_verified))
    def reconcile(*args):
        events.append("reconcile")
        return {"InstanceId": "i-1234567890abcdef0"}
    old = SimpleNamespace(budget=budget, verify_schedule=verify_schedule, verify_downloaded_packet=verify_packet,
        terminate_owned_instance=terminate, reconcile_instance=reconcile,
        confirm_deleted_volumes=lambda *a: [], remove_owned_auxiliary_resources=lambda *a: events.append("cleanup"),
        check_tag=lambda *a: None)
    s3 = FakeS3(events, current, 1 if failed else 0)
    class IAM:
        def create_role(self, **kwargs):
            events.append("create_role")
            return {"Role": {"Arn": "arn:aws:iam::807562639912:role/" + kwargs["RoleName"]}}
        def __getattr__(self, name):
            return lambda **kwargs: events.append(name)
    class EC2:
        def create_security_group(self, **kwargs):
            events.append("create_security_group")
            return {"GroupId": "sg-12345678"}
        def run_instances(self, **kwargs):
            events.append("run_instances")
            self.run = kwargs
            if uncertain:
                raise ValueError("synthetic lost RunInstances response")
            return {"Instances": [{"InstanceId": "i-1234567890abcdef0", "LaunchTime": datetime.now(timezone.utc)}]}
        def __getattr__(self, name):
            return lambda **kwargs: events.append(name)
    class Scheduler:
        def create_schedule(self, **kwargs):
            events.append("create_schedule"); self.created = kwargs
        def get_schedule(self, **kwargs):
            events.append("get_schedule")
            return {**self.created, "CreationDate": datetime.now(timezone.utc)}
    ec2, scheduler = EC2(), Scheduler()
    remote = SimpleNamespace(render_remote=lambda _: "# test-only", user_data=lambda *a: "#!/bin/bash\n# test-only")
    monkeypatch.setattr(p, "remote_config", lambda *a: {"bucket": "test-only-bucket"})
    monkeypatch.setattr(p, "verify_parent_source", lambda _: current["parent_file_sha256"])
    monkeypatch.setattr(p, "read_pinned", lambda *a: b"synthetic test artifact")
    monkeypatch.setattr(p.time, "sleep", lambda _: None)
    result = p._run_authorized(current, "d" * 64, {"synthetic_test_only": True}, {}, old, remote,
        {"s3": s3, "ec2": ec2, "iam": IAM(), "scheduler": scheduler},
        {"subnet": {"VpcId": "vpc-12345678"}}, tmp_path / "fake_run")
    return result, events, ec2, s3


def test_dedicated_orchestration_reserves_then_schedules_then_permits_then_collects(tmp_path, monkeypatch):
    result, events, ec2, s3 = fake_run(tmp_path, monkeypatch)
    assert result["status"] == "AWS_DIAGNOSTIC_FINISHED"
    assert events.index("reserve") < events.index("create_bucket") < events.index("run_instances")
    assert events.index("run_instances") < events.index("create_schedule") < events.index("verify_schedule")
    assert events.index("verify_schedule") < events.index("put:input/permit.json") < events.index("verify_packet")
    assert events.index("verify_packet") < events.index("terminate:True") < events.index("cleanup")
    assert events.count("reserve") == events.count("run_instances") == 1
    assert result["termination_confirmed"] is True and result["artifact_verified"] is True
    assert ec2.run["InstanceType"] == "g7.2xlarge"
    assert ec2.run["MinCount"] == ec2.run["MaxCount"] == 1
    assert ec2.run["BlockDeviceMappings"][0]["Ebs"] == {"VolumeSize": 75, "VolumeType": "gp3",
        "Iops": 3000, "Throughput": 125, "Encrypted": True, "DeleteOnTermination": True}
    permit = p.decoded(s3.objects["input/permit.json"])
    assert permit["worker_plan"]["instance_id"] == "i-1234567890abcdef0"
    assert permit["worker_plan"]["source_sha"] == p.WORKER_SOURCE_SHA


def test_bad_independent_schedule_never_publishes_worker_permission(tmp_path, monkeypatch):
    result, events, _, _ = fake_run(tmp_path, monkeypatch, schedule_bad=True)
    assert result["status"] == "AWS_DIAGNOSTIC_BLOCKED_OR_FAILED"
    assert "put:input/permit.json" not in events
    assert "terminate:False" in events and "cleanup" in events


def test_failed_worker_artifacts_are_verified_and_kept_before_shutdown(tmp_path, monkeypatch):
    result, events, _, _ = fake_run(tmp_path, monkeypatch, failed=True)
    assert result["status"] == "AWS_DIAGNOSTIC_FAILED"
    assert result["result"]["returncode"] == 1 and result["artifact_verified"] is True
    assert events.index("verify_packet") < events.index("terminate:True")


def test_lost_instance_creation_response_is_reconciled_not_retried(tmp_path, monkeypatch):
    result, events, _, _ = fake_run(tmp_path, monkeypatch, uncertain=True)
    assert result["status"] == "AWS_DIAGNOSTIC_BLOCKED_OR_FAILED"
    assert events.count("run_instances") == 1
    assert "reconcile" in events and "terminate:False" in events
    assert "put:input/permit.json" not in events


def test_reservation_snapshot_failure_retains_receipt_without_provider_creation(tmp_path, monkeypatch):
    result, events, _, _ = fake_run(tmp_path, monkeypatch, ledger_bad=True)
    assert events == ["reserve"]
    assert result["status"] == "PREPROVIDER_PREPARATION_OR_RESERVATION_FAILED"
    assert result["budget_reservation_state"] == "RESERVED_NO_AUTOMATIC_REFUND"
    stored = p.decoded((tmp_path / "fake_run/launch_receipt.json").read_bytes())
    assert stored["task_budget_reservation"] == result["task_budget_reservation"]
    assert stored["provider_resources_created"] is False


def test_provider_preflight_error_is_durable_and_does_not_reserve(tmp_path, monkeypatch):
    current = request()
    path = tmp_path / "request.json"; raw = p.encoded(current); path.write_bytes(raw)
    prep = SimpleNamespace(inspect_source_archive=lambda _: {}, inspect_development=lambda *a: {},
                           observe_budget=lambda: None)
    old = SimpleNamespace(campaign_execution_lock=nullcontext,
        budget=SimpleNamespace(read_ledger=lambda: {"remaining_unreserved_usd": "322.00"},
                               reserve_budget=lambda *a: pytest.fail("Reserved during failed preflight")))
    def helper(*args):
        return (prep, current["parent_file_sha256"]) if len(args) == 1 else (prep, old, None, current["parent_file_sha256"])
    monkeypatch.setattr(p, "helpers", helper)
    monkeypatch.setattr(p, "validate_owner_approval", lambda *a: {"synthetic_test_only": True})
    monkeypatch.setattr(p, "client_factory", lambda *a: {})
    monkeypatch.setattr(p, "provider_preflight", lambda *a: (_ for _ in ()).throw(MissingObject()))
    output = tmp_path / "failed_preflight"
    result = p.execute(path, p.digest(raw), "synthetic-only", "f" * 64, output)
    assert result["status"] == "LAUNCH_PREFLIGHT_REFUSED"
    assert result["new_reservation"] is False and result["provider_resources_created"] is False
    assert p.decoded((output / "launch_receipt.json").read_bytes()) == result


def test_parent_request_count_ceiling_blocks_before_extra_call():
    calls = []
    client = p.BoundedS3(SimpleNamespace(get_object=lambda **k: calls.append(k)))
    for _ in range(400):
        client.get_object(Bucket="test")
    with pytest.raises(p.LaunchRefused, match="PARENT_S3_REQUEST_CEILING"):
        client.get_object(Bucket="test")
    assert len(calls) == 400


@pytest.mark.parametrize("name", ["upload_file", "download_file", "get_paginator", "get_waiter"])
def test_hidden_transfer_retries_and_iterators_are_not_exposed(name):
    with pytest.raises(p.LaunchRefused, match="UNBOUNDED_TRANSFER_OR_ITERATOR_REFUSED"):
        getattr(p.BoundedS3(SimpleNamespace()), name)


def test_stream_download_checks_actual_bytes_and_never_retries(tmp_path):
    client = SimpleNamespace(get_object=lambda **k: {"ContentLength": 3, "Body": io.BytesIO(b"long")})
    with pytest.raises(p.LaunchRefused, match="DOWNLOAD_STREAM_CEILING"):
        p.download_once(client, "test", "test", tmp_path / "download", 3)


class FakePricing:
    def __init__(self, changed=None, paginated=False):
        self.changed, self.paginated = changed, paginated
    def get_products(self, **kwargs):
        fields = {f["Field"]: f["Value"] for f in kwargs["Filters"]}
        key = fields.get("usagetype", fields.get("volumeApiName", "internet"))
        unit, rate = {"gp3": ("GB-Mo", "0.08"), "USW2-PublicIPv4:InUseAddress": ("Hrs", "0.005"),
            "USW2-TimedStorage-ByteHrs": ("GB-Mo", "0.023"), "USW2-Requests-Tier1": ("Requests", "0.000005"),
            "USW2-Requests-Tier2": ("Requests", "0.0000004"), "internet": ("GB", "0.09")}[key]
        if self.changed == key:
            rate = "99"
        result = {"PriceList": [p.encoded({"terms": {"OnDemand": {"term": {"priceDimensions": {
            "dimension": {"unit": unit, "pricePerUnit": {"USD": rate}}}}}}}).decode()]}
        if self.paginated:
            result["NextToken"] = "more"
        return result


def test_cost_prices_both_request_buckets_at_tier1_and_stays_under_allowance():
    result = p.current_price_bound(FakePricing())
    assert result["item_bound_usd"]["requests"] == "0.010000"
    assert p.Decimal(result["ancillary_metered_bound_usd"]) < p.Decimal("1.00")
    assert p.Decimal(result["compute_plus_metered_bound_usd"]) < p.Decimal("3.52")
    assert "Taxes" in result["unmodeled"]


@pytest.mark.parametrize("changed", ["gp3", "USW2-PublicIPv4:InUseAddress", "USW2-TimedStorage-ByteHrs",
    "USW2-Requests-Tier1", "USW2-Requests-Tier2", "internet"])
def test_current_ancillary_price_over_plan_blocks_reservation(changed):
    with pytest.raises(p.LaunchRefused, match="ANCILLARY_PRICE_EXCEEDS_CEILING"):
        p.current_price_bound(FakePricing(changed=changed))


def test_paginated_current_price_is_not_assumed_complete():
    with pytest.raises(p.LaunchRefused, match="ANCILLARY_PRICE_IDENTITY_OR_PAGINATION"):
        p.current_price_bound(FakePricing(paginated=True))


def test_owner_approval_is_not_implied_by_execute_flag(capsys):
    assert p.main(["--execute"]) == 2
    assert "EXPLICIT_EXECUTE_REQUEST_APPROVAL_AND_RECEIPT_REQUIRED" in capsys.readouterr().out
