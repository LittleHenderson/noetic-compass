"""Pure B/R parent contracts. SDK responses, ledger and native outputs are synthetic."""
from contextlib import nullcontext
from copy import deepcopy
from datetime import datetime, timezone
import io
from pathlib import Path
from types import SimpleNamespace
import sys
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from aws import launch_br_construction_v8 as p


def request():
    return {"schema": "cas-meta2-br-launch-request/8", "experiment": p.EXPERIMENT,
        "job": "cas-meta2-20260906000000-deadbeef", "parent_source_sha": "a" * 40,
        "parent_file_sha256": {name: "b" * 64 for name in (*p.PARENT_FILES, *p.FROZEN_PINS)},
        "worker_source_sha": "c" * 40, "source_archive_sha256": "d" * 64,
        "source_manifest_sha256": "e" * 64, "source_archive": "synthetic-source.zip",
        "source_archive_bytes": 17, "resource_plan": p.resource_plan(),
        "construction_scope": p.construction_scope(), "subnet_id": "subnet-12345678",
        "standing_authority_registration_required": True, "launch_authorized": False}


def test_default_is_pure_unpaid_and_separate(capsys, monkeypatch):
    monkeypatch.setattr(p, "helpers", lambda *a: pytest.fail("Default imported helper"))
    assert p.main([]) == 0
    result = p.decoded(capsys.readouterr().out)
    assert result["provider_calls"] is False and result["new_reservation"] is False
    assert result["resource_plan"]["native_execution"] is True
    assert result["resource_plan"]["training"] is False
    assert result["resource_plan"]["worker_seconds_max"] == 600
    assert result["experiment"]["entrypoint"] == "cas_meta2.br_construction_v8"
    assert not {"torch", "boto3", "botocore", "casformer", "cas_cjt"}.intersection(sys.modules)


@pytest.mark.parametrize("field,value", [("instance_type", "g4dn.xlarge"), ("runtime_seconds_max", 3601),
    ("worker_seconds_max", 601), ("automatic_retries", 1), ("per_launch_reserved_cap_usd", "5.00"),
    ("training", True), ("native_execution", False), ("ebs_iops", 16000), ("instance_count", True)])
def test_resource_expansion_or_boolean_count_refused(field, value):
    current = request()
    current["resource_plan"][field] = value
    with pytest.raises(p.LaunchRefused, match="BR_EXACT_SCOPE"):
        p.validate_request(current)


@pytest.mark.parametrize("field,value", [("max_seconds", 601), ("binding", 1), ("binding", False),
    ("prelude", ["A", "B", "C"]), ("arm_cjt", "B"), ("arm_expected_symbol", "L1"),
    ("prelude_policy_units", 65536), ("arm_policy_units", 16384), ("seed", 8), ("native_execution", False)])
def test_native_scope_is_fixed(field, value):
    current = request()
    current["construction_scope"][field] = value
    with pytest.raises(p.LaunchRefused, match="BR_EXACT_SCOPE"):
        p.validate_request(current)


def test_prefix_or_training_request_is_not_br():
    current = request()
    current["schema"] = "cas-meta2-prefix-launch-request/8"
    with pytest.raises(p.LaunchRefused, match="BR_DEDICATED_REQUEST"):
        p.validate_request(current)
    current = request()
    current["development_archive"] = "not-allowed"
    with pytest.raises(p.LaunchRefused, match="BR_REGISTERED_STANDING"):
        p.validate_request(current)


def authority_fixture(tmp_path, monkeypatch):
    current = request()
    campaign = tmp_path / "synthetic-campaign-authority.txt"
    campaign.write_bytes(b"SYNTHETIC TEST AUTHORITY ONLY")
    message = tmp_path / "synthetic-standing-message.txt"
    message.write_bytes(b"SYNTHETIC TEST STANDING MESSAGE ONLY")
    monkeypatch.setattr(p, "STANDING_MESSAGE_SHA256", p.digest(message.read_bytes()))
    ledger = {"approval": {"path": str(campaign), "sha256": p.digest(campaign.read_bytes())},
              "owner_task_cap_usd": "400.00", "no_automatic_refund": True}
    request_hash = p.digest(p.encoded(current))
    authority = {"schema": "cas-meta2-br-standing-authority/8", "standing_campaign_authorization": True,
        "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00", "experiment": p.EXPERIMENT,
        "training": False, "native_execution": True, "launch_request_sha256": request_hash,
        **{k: current[k] for k in ("job", "parent_source_sha", "worker_source_sha",
                                  "source_archive_sha256", "source_manifest_sha256")},
        "campaign_approval": ledger["approval"],
        "standing_user_message": {"path": str(message), "sha256": p.STANDING_MESSAGE_SHA256}}
    path = tmp_path / "synthetic-authority.json"
    path.write_bytes(p.encoded(authority))
    return current, request_hash, authority, path, ledger


def test_standing_authority_binds_existing_campaign_new_job_source_and_full_message(tmp_path, monkeypatch):
    current, request_hash, authority, path, ledger = authority_fixture(tmp_path, monkeypatch)
    result = p.validate_authority(path, p.digest(path.read_bytes()), current, request_hash, ledger)
    assert result["worker_source_sha"] != result["parent_source_sha"]
    assert result["campaign_cap_usd"] == "400.00" and result["max_job_cost_usd"] == "4.00"


@pytest.mark.parametrize("field,value", [("job", "different"), ("max_job_cost_usd", "8.00"),
    ("worker_source_sha", "f" * 40), ("launch_request_sha256", "f" * 64), ("training", True),
    ("standing_campaign_authorization", 1), ("schema", "cas-meta2-prefix-owner-approval/8")])
def test_authority_cannot_expand_or_reuse_prefix_approval(tmp_path, monkeypatch, field, value):
    current, request_hash, authority, path, ledger = authority_fixture(tmp_path, monkeypatch)
    authority[field] = value
    path.write_bytes(p.encoded(authority))
    with pytest.raises(p.LaunchRefused, match="BR_STANDING_AUTHORITY_SCOPE"):
        p.validate_authority(path, p.digest(path.read_bytes()), current, request_hash, ledger)


def test_authority_message_bytes_must_match(tmp_path, monkeypatch):
    current, request_hash, authority, path, ledger = authority_fixture(tmp_path, monkeypatch)
    Path(authority["standing_user_message"]["path"]).write_bytes(b"changed")
    with pytest.raises(p.LaunchRefused, match="BR_PINNED_BYTES"):
        p.validate_authority(path, p.digest(path.read_bytes()), current, request_hash, ledger)


def test_permit_binds_distinct_worker_source_and_reservation():
    current = request()
    reservation, ledger = {"synthetic": "reservation"}, {"synthetic": "ledger"}
    permit = p.worker_permit(current, {}, reservation, ledger, "i-1234567890abcdef0", datetime.now(timezone.utc))
    plan = permit["worker_plan"]
    assert plan["source_sha"] == current["worker_source_sha"] != current["parent_source_sha"]
    assert plan["max_seconds"] == 600 and plan["training"] is False and plan["native_execution"] is True
    assert plan["reservation_receipt"]["sha256"] == p.digest(p.encoded(reservation))
    assert plan["ledger_snapshot"]["sha256"] == p.digest(p.encoded(ledger))
    assert plan["source_manifest"]["path"] == "/opt/cas-meta2-br/package/br_source_manifest.json"
    assert permit["worker_plan_sha256"] == p.digest(p.encoded(plan))


def packet(tmp_path, *, failure=False, mutate=None, corrupt_member=None, emergency=False):
    current = request()
    plan_hash = "f" * 64
    files = {}
    worker = {"schema": "cas-meta2-br-construction/8", "job": current["job"],
        "status": "BR_CONSTRUCTION_REFUSED_OR_FAILED" if failure else "BR_COMPONENT_EXECUTED",
        "source_sha": current["worker_source_sha"], "source_archive_sha256": current["source_archive_sha256"],
        "source_manifest_sha256": current["source_manifest_sha256"], "plan_sha256": plan_hash,
        "training": False, "native_execution": True, "cleanup_errors": [],
        "task_conditioned_correctness": None, "postchecks": {"source": {"ok": True}, "reservation": {"ok": True}},
        "prelude": [{"cjt_id": name} for name in ["A", "B", "C", "R"]],
        "arms": {a: {"status": "ACCEPTED", "input_producer": a, "same_fixed_expectation": "L2",
                     "rows": [{"cjt_id": "C"}]} for a in ("B", "R")}}
    if failure:
        worker["failure"] = {"type": "SYNTHETIC_FAILURE", "message": "not native execution"}
        files["construction/progress.json"] = b"synthetic failure progress"
    else:
        for name in p.WORKER_SUCCESS_FILES:
            files["construction/" + name] = p.encoded({"synthetic_test_only": True})
        for name in ("preclose_witness_check.json", "arm_B/before_witness_check.json", "arm_R/before_witness_check.json"):
            files["construction/" + name] = p.encoded({"ok": True, "synthetic_test_only": True})
        for arm in ("B", "R"):
            files["construction/arm_" + arm + "/result.json"] = p.encoded(worker["arms"][arm])
        files["lifecycle/worker/stdout.txt"] = b"SYNTHETIC stdout"
        files["lifecycle/worker/stderr.txt"] = b""
        files["lifecycle/worker/receipt.json"] = p.encoded({"exit_code": 0, "failure": None,
            "maximum_seconds": 600, "outputs": {n: {"sha256": p.digest(files["lifecycle/worker/" + n]),
            "bytes": len(files["lifecycle/worker/" + n])} for n in ("stdout.txt", "stderr.txt")}})
        files["lifecycle/remote_receipt.json"] = p.encoded({"returncode": 0,
            "worker_process_started": True, "worker_component_completed": True, "neural_training": False,
            "source_sha": current["worker_source_sha"], "parent_source_sha": current["parent_source_sha"],
            "archive_sha256": current["source_archive_sha256"], "source_manifest_sha256": current["source_manifest_sha256"]})
    if mutate:
        mutate(worker, files)
    worker["files_sha256"] = {n.removeprefix("construction/"): p.digest(raw)
                             for n, raw in files.items() if n.startswith("construction/")}
    files["construction/construction_receipt.json"] = p.encoded(worker)
    collection = {"job": current["job"], "source_sha": current["worker_source_sha"],
        "parent_source_sha": current["parent_source_sha"], "experiment": p.EXPERIMENT,
        "returncode": 1 if failure else 0, "partial_evidence": False, "original_file_count": len(files),
        "included_full_file_count": len(files), "omitted_full_file_count": 0,
        "files": {n: {"sha256": p.digest(raw), "bytes": len(raw)} for n, raw in files.items()}}
    if emergency:
        files = {}
        collection.update(returncode=1, partial_evidence=True, original_file_count=None,
            included_full_file_count=0, omitted_full_file_count=None, full_file_counts_known=False,
            collection_failure={"type": "SYNTHETIC_ONLY", "message": "collection unavailable"})
        collection.pop("files")
    if corrupt_member:
        files[corrupt_member] += b"changed after file map"
    path = tmp_path / "synthetic-packet.zip"
    with ZipFile(path, "x", ZIP_DEFLATED) as zipped:
        for name, raw in files.items():
            zipped.writestr(name, raw)
        zipped.writestr("artifact_collection_receipt.json", p.encoded(collection))
    result = {k: collection[k] for k in ("job", "source_sha", "parent_source_sha", "experiment",
                                       "returncode", "partial_evidence", "omitted_full_file_count")}
    result.update(sha256=p.digest(path.read_bytes()), bytes=path.stat().st_size)
    return path, result, current, plan_hash


def test_full_synthetic_packet_all_members_verified_but_not_learning(tmp_path):
    actual = p.verify_packet(*packet(tmp_path))
    assert actual["native_component_success"] is True
    assert actual["parent_member_hashes_verified"] == actual["original_file_count"]
    assert actual["not_task_correctness_or_learning"] is True
    assert len(actual["archive_files_sha256"]) == actual["original_file_count"] + 1


def test_native_setup_failure_retained_without_requiring_absent_arms(tmp_path):
    actual = p.verify_packet(*packet(tmp_path, failure=True))
    assert actual["construction_status"] == "BR_CONSTRUCTION_REFUSED_OR_FAILED"
    assert actual["native_component_success"] is False
    assert actual["original_member_coverage_verified"] is True


def test_emergency_receipt_is_failed_partial_not_complete_native_evidence(tmp_path):
    actual = p.verify_packet(*packet(tmp_path, failure=True, emergency=True))
    assert actual["native_component_success"] is False
    assert actual["original_member_coverage_verified"] is False
    assert actual["parent_member_hashes_verified"] == 0


@pytest.mark.parametrize("member", ["construction/copies/B.sqlite", "lifecycle/worker/stdout.txt",
                                   "construction/arm_R/result.json"])
def test_resealed_archive_does_not_hide_member_hash_change(tmp_path, member):
    with pytest.raises(p.LaunchRefused, match="BR_COLLECTED_MEMBER_HASH"):
        p.verify_packet(*packet(tmp_path, corrupt_member=member))


@pytest.mark.parametrize("key,value", [("source_sha", "f" * 40), ("plan_sha256", "a" * 64),
    ("training", True), ("native_execution", False), ("status", "OTHER"),
    ("cleanup_errors", ["unclosed"]), ("postchecks", {})])
def test_success_claim_mutations_refused(tmp_path, key, value):
    with pytest.raises(p.LaunchRefused):
        p.verify_packet(*packet(tmp_path, mutate=lambda worker, files: worker.update({key: value})))


def test_missing_mandatory_native_output_refused_even_with_resealed_maps(tmp_path):
    with pytest.raises(p.LaunchRefused, match="BR_MANDATORY_NATIVE_OUTPUT"):
        p.verify_packet(*packet(tmp_path, mutate=lambda worker, files: files.pop("construction/copies/R.sqlite")))


class MissingObject(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class FakeS3:
    def __init__(self, events, current, returncode=0):
        self.events, self.current = events, current
        self.objects = {"results/artifacts.zip": b"synthetic-test-packet", "results/bootstrap.log": b"test log"}
        self.result = {"job": current["job"], "source_sha": current["worker_source_sha"],
            "parent_source_sha": current["parent_source_sha"], "experiment": p.EXPERIMENT, "returncode": returncode,
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

    def delete_objects(self, **kwargs):
        self.events.append("delete_objects")
        return {"Deleted": kwargs["Delete"]["Objects"]}

    def get_object(self, **kwargs):
        if kwargs["Key"] not in self.objects:
            raise MissingObject()
        raw = self.objects[kwargs["Key"]]
        return {"ContentLength": len(raw), "Body": io.BytesIO(raw)}

    def head_object(self, **kwargs):
        if kwargs["Key"] not in self.objects:
            raise MissingObject()
        return {"ContentLength": len(self.objects[kwargs["Key"]])}

    def get_bucket_tagging(self, **kwargs):
        return {"TagSet": [{"Key": "cas_meta_job", "Value": self.current["job"]}]}

    def list_objects_v2(self, **kwargs):
        return {"Contents": [{"Key": k, "Size": len(v), "LastModified": datetime.now(timezone.utc)}
                             for k, v in self.objects.items() if k.startswith("results/")]}


def fake_run(tmp_path, monkeypatch, *, failed=False, schedule_bad=False, uncertain=False, ledger_bad=False):
    current, events = request(), []
    ledger = {"revision": 1, "remaining_unreserved_usd": "314.00"}
    def reserve(*args):
        events.append("reserve")
        assert args == (current["job"], current["worker_source_sha"], current["source_archive_sha256"], "4.00", current["resource_plan"])
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
    def verify_packet(path, result, req, plan_hash):
        assert p.digest(path.read_bytes()) == result["sha256"]
        assert req == current and len(plan_hash) == 64
        events.append("verify_packet")
        return {"returncode": result["returncode"], "partial_evidence": failed}
    def terminate(*args, artifact_verified, record):
        events.append("terminate:" + str(artifact_verified))
    def reconcile(*args):
        events.append("reconcile")
        return {"InstanceId": "i-1234567890abcdef0"}
    old = SimpleNamespace(budget=budget, verify_schedule=verify_schedule,
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
            events.append("create_schedule")
            self.created = kwargs
        def get_schedule(self, **kwargs):
            events.append("get_schedule")
            return {**self.created, "CreationDate": datetime.now(timezone.utc)}
    def download(s3, bucket, key, path, maximum):
        raw = s3.objects[key]
        assert len(raw) <= maximum
        path.write_bytes(raw)
    plumbing = SimpleNamespace(download_once=download)
    ec2, scheduler = EC2(), Scheduler()
    remote = SimpleNamespace(render_remote=lambda _: "# test-only", user_data=lambda *a: "#!/bin/bash\n# test-only")
    monkeypatch.setattr(p, "remote_config", lambda *a: {"bucket": "test-only-bucket"})
    monkeypatch.setattr(p, "verify_parent_source", lambda _: current["parent_file_sha256"])
    monkeypatch.setattr(p, "read_pinned", lambda *a: b"synthetic test artifact")
    monkeypatch.setattr(p, "verify_packet", verify_packet)
    monkeypatch.setattr(p.time, "sleep", lambda _: None)
    result = p._run_authorized(current, "d" * 64, {"synthetic_test_only": True}, {}, old, remote, plumbing,
        {"s3": s3, "ec2": ec2, "iam": IAM(), "scheduler": scheduler},
        {"subnet": {"VpcId": "vpc-12345678"}}, tmp_path / "fake_run")
    return result, events, ec2, s3


def test_lifecycle_reserves_schedules_permits_collects_then_shuts_down(tmp_path, monkeypatch):
    result, events, ec2, s3 = fake_run(tmp_path, monkeypatch)
    assert result["status"] == "AWS_BR_CONSTRUCTION_FINISHED"
    assert events.index("reserve") < events.index("create_bucket") < events.index("run_instances")
    assert events.index("run_instances") < events.index("verify_schedule") < events.index("put:input/permit.json")
    assert events.index("verify_packet") < events.index("terminate:True") < events.index("cleanup")
    assert events.count("reserve") == events.count("run_instances") == 1
    assert result["termination_confirmed"] is True and result["artifact_verified"] is True
    assert ec2.run["InstanceType"] == "g7.2xlarge"
    assert ec2.run["MinCount"] == ec2.run["MaxCount"] == 1
    assert ec2.run["BlockDeviceMappings"][0]["Ebs"] == {"VolumeSize": 75, "VolumeType": "gp3",
        "Iops": 3000, "Throughput": 125, "Encrypted": True, "DeleteOnTermination": True}
    assert "input/development.zip" not in s3.objects
    permit = p.decoded(s3.objects["input/permit.json"])
    assert permit["worker_plan"]["source_sha"] == request()["worker_source_sha"]
    assert permit["worker_plan"]["max_seconds"] == 600


def test_bad_schedule_never_publishes_permission_and_still_terminates(tmp_path, monkeypatch):
    result, events, _, _ = fake_run(tmp_path, monkeypatch, schedule_bad=True)
    assert result["status"] == "AWS_BR_CONSTRUCTION_BLOCKED_OR_FAILED"
    assert "put:input/permit.json" not in events
    assert "terminate:False" in events and "cleanup" in events


def test_native_failure_artifacts_kept_before_shutdown(tmp_path, monkeypatch):
    result, events, _, _ = fake_run(tmp_path, monkeypatch, failed=True)
    assert result["status"] == "AWS_BR_CONSTRUCTION_FAILED"
    assert result["artifact_verified"] is True
    assert events.index("verify_packet") < events.index("terminate:True")


def test_uncertain_run_instances_is_reconciled_never_retried(tmp_path, monkeypatch):
    result, events, _, _ = fake_run(tmp_path, monkeypatch, uncertain=True)
    assert result["status"] == "AWS_BR_CONSTRUCTION_BLOCKED_OR_FAILED"
    assert events.count("run_instances") == 1
    assert "reconcile" in events and "terminate:False" in events
    assert "put:input/permit.json" not in events


def test_snapshot_failure_keeps_reservation_receipt_before_any_resource(tmp_path, monkeypatch):
    result, events, _, _ = fake_run(tmp_path, monkeypatch, ledger_bad=True)
    assert events == ["reserve"]
    assert result["status"] == "PREPROVIDER_PREPARATION_OR_RESERVATION_FAILED"
    assert result["budget_reservation_state"] == "RESERVED_NO_AUTOMATIC_REFUND"
    stored = p.decoded((tmp_path / "fake_run/launch_receipt.json").read_bytes())
    assert stored["task_budget_reservation"] == result["task_budget_reservation"]
    assert stored["provider_resources_created"] is False


@pytest.mark.parametrize("lock_failure", [False, True])
def test_preflight_or_lock_failure_has_durable_receipt_no_reservation(tmp_path, monkeypatch, lock_failure):
    current = request()
    raw = p.encoded(current)
    path = tmp_path / "request.json"
    path.write_bytes(raw)
    def lock():
        if lock_failure:
            raise ValueError("synthetic lock unavailable")
        return nullcontext()
    old = SimpleNamespace(campaign_execution_lock=lock,
        budget=SimpleNamespace(read_ledger=lambda: {"remaining_unreserved_usd": "318.00"},
                               reserve_budget=lambda *a: pytest.fail("Reservation in failed preflight")))
    def refused(*a):
        raise ValueError("synthetic preflight refused")
    plumbing = SimpleNamespace(client_factory=lambda *a: {}, provider_preflight=refused)
    monkeypatch.setattr(p, "ROOT", tmp_path)
    monkeypatch.setattr(p, "helpers", lambda *a: {"old": old, "plumbing": plumbing,
        "identity": current["parent_file_sha256"], "package": None})
    monkeypatch.setattr(p, "source_for", lambda *a: {})
    monkeypatch.setattr(p, "validate_authority", lambda *a: {"synthetic_test_only": True})
    output = tmp_path / "records/refused"
    result = p.execute(path, p.digest(raw), "synthetic-only", "f" * 64, output)
    assert result["status"] == "BR_LAUNCH_PREFLIGHT_REFUSED"
    assert result["new_reservation"] is False and result["provider_resources_created"] is False
    assert p.decoded((output / "launch_receipt.json").read_bytes()) == result


def test_existing_output_directory_is_not_overwritten(tmp_path, monkeypatch):
    current = request()
    raw = p.encoded(current)
    path = tmp_path / "request.json"
    path.write_bytes(raw)
    monkeypatch.setattr(p, "ROOT", tmp_path)
    monkeypatch.setattr(p, "helpers", lambda *a: {"identity": current["parent_file_sha256"], "package": None})
    monkeypatch.setattr(p, "source_for", lambda *a: {})
    output = tmp_path / "records/existing"
    output.mkdir(parents=True)
    with pytest.raises(p.LaunchRefused, match="BR_NEW_RECEIPT_DIRECTORY"):
        p.execute(path, p.digest(raw), None, None, output)
    assert not list(output.iterdir())


def test_execute_cli_requires_bound_records_before_any_action():
    with pytest.raises(p.LaunchRefused, match="BR_EXECUTION_INPUTS"):
        p.main(["--execute"])


@pytest.mark.parametrize("response", [{"Errors": [{"Key": "input/source.zip", "Code": "AccessDenied"}]},
                                    {"Deleted": [{"Key": "input/source.zip"}]}])
def test_partial_s3_delete_never_claims_all_inputs_removed(tmp_path, monkeypatch, response):
    monkeypatch.setattr(FakeS3, "delete_objects", lambda self, **kwargs: response)
    result, events, _, _ = fake_run(tmp_path, monkeypatch)
    assert result["status"] == "CLEANUP_REQUIRES_ATTENTION"
    assert result["input_delete_response"] == response
    assert any("INPUT_DELETION_NOT_CONFIRMED" in e for e in result["cleanup_errors"])
    assert not any(e["event"] == "OWNED_INPUTS_REMOVED_AFTER_VERIFIED_DOWNLOAD" for e in result["events"])
    assert result["termination_confirmed"] is True and result["artifact_verified"] is True


def test_source_bytes_checked_against_commit_and_frozen_pin_before_import(tmp_path, monkeypatch):
    parent = "a" * 40
    target = tmp_path / "aws/new_parent.py"
    target.parent.mkdir()
    target.write_bytes(b"SYNTHETIC PURE PARENT")
    frozen = tmp_path / "aws/old_helper.py"
    frozen.write_bytes(b"SYNTHETIC PURE HELPER")
    committed = {"aws/new_parent.py": target.read_bytes(), "aws/old_helper.py": frozen.read_bytes()}
    monkeypatch.setattr(p, "ROOT", tmp_path)
    monkeypatch.setattr(p, "PARENT_FILES", ("aws/new_parent.py",))
    monkeypatch.setattr(p, "FROZEN_PINS", {"aws/old_helper.py": p.digest(frozen.read_bytes())})
    def git(argv, **kwargs):
        if argv[1:] == ["rev-parse", "--show-toplevel"]:
            return str(tmp_path)
        if argv[1] == "rev-parse":
            return parent
        assert argv[1:3] == ["cat-file", "blob"]
        return committed[argv[3].split(":", 1)[1]]
    monkeypatch.setattr(p.subprocess, "check_output", git)
    assert p.verify_parent_source(parent) == {n: p.digest(raw) for n, raw in committed.items()}
    frozen.write_bytes(b"CHANGED")
    monkeypatch.setattr(p, "load_module", lambda *a: pytest.fail("Imported changed helper"))
    with pytest.raises(p.LaunchRefused, match="BR_PARENT_SOURCE_NOT_COMMITTED"):
        p.helpers(parent)


def test_raw_process_receipt_must_bind_collected_logs_even_when_archive_is_resealed(tmp_path):
    def change(worker, files):
        process = p.decoded(files["lifecycle/worker/receipt.json"])
        process["outputs"]["stdout.txt"]["sha256"] = "0" * 64
        files["lifecycle/worker/receipt.json"] = p.encoded(process)
    with pytest.raises(p.LaunchRefused, match="BR_PROCESS_RAW_OUTPUT_MISMATCH"):
        p.verify_packet(*packet(tmp_path, mutate=change))
