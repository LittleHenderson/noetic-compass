"""Pure tests for the binding-fit AWS launcher.

Fake git objects and fake client stacks only; no AWS, network, tensor, or
provider work occurs. Ledger files are temporary copies initialized from the
real predecessor/approval evidence (read-only).
"""
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aws import binding_fit_launch as launch
from aws import budget


JOB = "cas-meta2-teaching-binding-20260908170000-abcdef12"
COMMIT = "f" * 40


def valid_request():
    return {"schema": launch.REQUEST_SCHEMA, "job": JOB, "source_sha": "a" * 40,
            "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            "launch_authorized": False}


def valid_authority():
    return {"schema": launch.AUTHORITY_SCHEMA, "job": JOB, "source_sha": "a" * 40,
            "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
            "owner_authorization_sha256":
                launch.digest(launch.OWNER_AUTHORIZATION_PATH.read_bytes()),
            "learning_rate": 0.003, "max_optimizer_steps": 48,
            "max_wall_seconds": 600.0, "reservation_usd": "4.00"}


def write_ledger(tmp_path):
    path = tmp_path / "campaign_ledger.json"
    prior = launch.ROOT.parent / "CAS_META_1_LEARNED_SELECTION" / "records/aws_budget_ledger.json"
    approval = launch.ROOT / "records/budget/OWNER_APPROVAL_SOURCE.json"
    budget.initialize_ledger(prior, approval, path)
    return path


@pytest.fixture
def ledger(tmp_path):
    return write_ledger(tmp_path)


class FakeProvider:
    def __init__(self, ledger_path):
        self.ledger_path = ledger_path
        self.calls = []

    def configure_evidence(self, directory):
        self.evidence = directory

    def preflight(self):
        self.calls.append("preflight")
        return {"account": launch.RESOURCE_PLAN["account"], "region": launch.RESOURCE_PLAN["region"],
                "ami": launch.RESOURCE_PLAN["ami"], "instance_type": launch.RESOURCE_PLAN["instance_type"],
                "instance_count": 1, "gpu_name_contains": launch.RESOURCE_PLAN["gpu_name_contains"],
                "visible_gpu_count": 1, "t4_rejected": True,
                "rate_ceiling_usd": launch.RESOURCE_PLAN["on_demand_rate_ceiling_usd"],
                "conflicting_resources": []}

    def reserve(self, amount):
        self.calls.append("reserve")
        receipt = budget.reserve_budget(JOB, "a" * 40, "b" * 64, amount,
                                        launch.reservation_plan(), self.ledger_path)
        return {**receipt, "aws_side_reservation": {"status": "RECORDED"}}

    def launch(self, job, permit):
        self.calls.append("launch")
        return {"job": job, "instance_id": "i-0123456789abcdef0", "permit": permit}

    def wait(self, job, timeout):
        self.calls.append("wait")
        return {"worker_status": "REMOTE_FINISHED"}

    def collect(self, job):
        self.calls.append("collect")
        return {"result": "collected"}

    def cleanup(self, job):
        self.calls.append("cleanup")
        return {"complete": True, "instance_ids": [], "instances": {},
                "security_group_deleted": True, "schedule_removed": True,
                "roles_removed": True, "bucket_deleted": True, "results_deleted": True,
                "failures": []}


# --------------------------------------------------------------------------- #
# plan-only / request / authority
# --------------------------------------------------------------------------- #
def test_plan_only_is_inert():
    result = launch.plan_only()
    assert result["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert result["reservation_created"] is False
    assert result["provider_calls"] == 0
    assert result["scope"]["account"] == "807562639912"
    assert result["scope"]["instance_type"] == "g7.2xlarge"


def test_valid_request_and_authority_accepted():
    assert launch.validate_request(valid_request())["job"] == JOB
    assert launch.validate_authority(valid_authority())["job"] == JOB


@pytest.mark.parametrize("mutate,reason", [
    (lambda r: r.update(schema="other/1"), "BINDING_FIT_REQUEST_SCHEMA"),
    (lambda r: r.update(job="bad"), "BINDING_FIT_REQUEST_JOB"),
    (lambda r: r.update(source_sha="zz"), "BINDING_FIT_REQUEST_SOURCE_SHA"),
    (lambda r: r.update(archive_sha256="zz"), "BINDING_FIT_REQUEST_HASH:archive_sha256"),
    (lambda r: r.update(manifest_sha256="zz"), "BINDING_FIT_REQUEST_HASH:manifest_sha256"),
    (lambda r: r.update(launch_authorized=True), "BINDING_FIT_REQUEST_INERT"),
    (lambda r: r.pop("job"), "BINDING_FIT_REQUEST_FIELDS"),
    (lambda r: r.update(extra=1), "BINDING_FIT_REQUEST_FIELDS"),
])
def test_request_rejects_mutations(mutate, reason):
    request = valid_request()
    mutate(request)
    with pytest.raises(ValueError, match=reason):
        launch.validate_request(request)


@pytest.mark.parametrize("mutate,reason", [
    (lambda a: a.update(schema="other/1"), "BINDING_FIT_AUTHORITY_SCHEMA"),
    (lambda a: a.update(job="bad"), "BINDING_FIT_AUTHORITY_JOB"),
    (lambda a: a.update(source_sha="zz"), "BINDING_FIT_AUTHORITY_SOURCE_SHA"),
    (lambda a: a.update(owner_authorization_sha256="zz"), "BINDING_FIT_AUTHORITY_HASH"),
    (lambda a: a.update(learning_rate=0.1), "BINDING_FIT_AUTHORITY_BUDGET:learning_rate"),
    (lambda a: a.update(max_optimizer_steps=1), "BINDING_FIT_AUTHORITY_BUDGET:max_optimizer_steps"),
    (lambda a: a.update(max_wall_seconds=1.0), "BINDING_FIT_AUTHORITY_BUDGET:max_wall_seconds"),
    (lambda a: a.update(reservation_usd="5.00"), "BINDING_FIT_AUTHORITY_RESERVATION"),
    (lambda a: a.pop("job"), "BINDING_FIT_AUTHORITY_FIELDS"),
    (lambda a: a.update(extra=1), "BINDING_FIT_AUTHORITY_FIELDS"),
])
def test_authority_rejects_mutations(mutate, reason):
    authority = valid_authority()
    mutate(authority)
    with pytest.raises(ValueError, match=reason):
        launch.validate_authority(authority)


def test_frozen_budget_matches_mode_defaults():
    from cas_meta2.binding_fit_training import mode
    assert launch.FROZEN_MAX_OPTIMIZER_STEPS == mode.DEFAULT_MAX_OPTIMIZER_STEPS
    assert launch.FROZEN_MAX_WALL_SECONDS == mode.DEFAULT_MAX_WALL_SECONDS
    assert launch.FROZEN_LEARNING_RATE == 0.003


def test_reservation_plan_is_cost_bounded():
    plan = launch.reservation_plan()
    assert budget.validate_plan(plan, "4.00") == budget.amount("4.00")


# --------------------------------------------------------------------------- #
# package builder (fake git)
# --------------------------------------------------------------------------- #
@pytest.fixture
def fake_git(monkeypatch):
    blobs = {}
    for index, name in enumerate(launch.EXPLICIT_FILES):
        blobs[name] = b"explicit-%d" % index
    for directory in launch.SOURCE_DIRS:
        if "binding_fit_training" in directory:
            suffixes = ("__init__.py", "mode.py")
        else:
            suffixes = ("__init__.py", "data.py", "lesson_contract.py",
                        "gpu_adapter.py", "guided_application.py")
        for suffix in suffixes:
            blobs[directory + "/" + suffix] = (directory + "/" + suffix).encode("utf-8")
    wheel_hashes = {}
    for index, name in enumerate(launch.WHEELS):
        blobs[name] = b"synthetic-wheel-%d" % index
        wheel_hashes[name] = launch.digest(blobs[name])
    monkeypatch.setattr(launch, "WHEELS", wheel_hashes)

    class Fake:
        def bytes_fn(self, root, commit, path):
            assert commit == COMMIT
            return blobs[path]

        def paths_fn(self, root, commit, directory):
            assert commit == COMMIT
            return sorted(key for key in blobs if key.startswith(directory + "/"))
    return Fake(), blobs


def resolve(fake):
    return launch.resolve_members(Path("unused"), COMMIT,
                                  git_bytes_fn=fake.bytes_fn, git_paths_fn=fake.paths_fn)


def test_resolve_members_uses_git_objects_and_worker(fake_git):
    fake, blobs = fake_git
    members = resolve(fake)
    assert launch.WORKER_NAME in members
    for name in launch.EXPLICIT_FILES:
        assert name in members
    assert launch.PILOT + "cas_meta2/features_v2.py" in members
    assert launch.PILOT + "cas_meta2/policy.py" in members
    assert launch.PILOT + "cas_meta2/binding_fit_training/mode.py" in members
    assert launch.PILOT + "cas_meta2/teaching_cycle/gpu_adapter.py" in members
    for name in launch.WHEELS:
        assert name in members
    # the rendered worker is a package member, not a git object
    assert members[launch.WORKER_NAME].startswith(b"#!/usr/bin/env python3")


def test_package_build_zip_readback_and_manifest(fake_git, monkeypatch, tmp_path):
    fake, blobs = fake_git
    root = tmp_path / "repo"
    root.mkdir()
    (root / "records").mkdir()
    monkeypatch.setattr(launch, "ROOT", root)
    output = root / "records" / "binding_fit_package_001"
    receipt = launch.build_package(output, source_sha=COMMIT,
                                   git_bytes_fn=fake.bytes_fn, git_paths_fn=fake.paths_fn)
    assert receipt["status"] == "SOURCE_ONLY_NO_LAUNCH"
    assert receipt["manifest"]["launch_enabled"] is False
    assert receipt["manifest"]["reservation_created"] is False
    assert receipt["manifest"]["frozen_budget"]["max_optimizer_steps"] == 48
    archive = output / "source.zip"
    assert archive.read_bytes()
    inspected = launch.inspect_archive(archive, expected_sha256=receipt["archive_sha256"],
                                       expected_source_sha=COMMIT,
                                       expected_manifest_sha256=receipt["manifest_sha256"])
    assert inspected["schema"] == launch.PACKAGE_SCHEMA
    assert inspected["launch_enabled"] is False
    assert launch.WORKER_NAME in inspected["members"]


def test_worker_script_text(fake_git):
    fake, blobs = fake_git
    members = resolve(fake)
    text = members[launch.WORKER_NAME].decode("utf-8")
    assert "venv" in text
    assert "https://download.pytorch.org/whl/cu128" in text
    assert "torch==2.11.0" in text
    assert "casformer_reference-0.1.0-py3-none-any.whl" in text
    assert "cas_neural_cjt-0.2.0-py3-none-any.whl" in text
    assert "--no-deps" in text
    assert ("mode.launch(run_id=job, max_optimizer_steps=48, "
            "max_wall_seconds=600.0, learning_rate=0.003)") in text
    assert "hashlib.sha256" in text
    assert "results/result.json" in text
    assert "results/result.json.sha256" in text
    assert "put_object" in text
    # inner runner output is captured so the original error is preserved
    assert "capture_output=True" in text
    assert "INNER_RUNNER_EXIT_" in text
    assert "inner.stderr or inner.stdout" in text
    # no template placeholders
    assert "{job}" not in text
    assert "{bucket}" not in text
    assert "{{" not in text and "}}" not in text


# --------------------------------------------------------------------------- #
# budget + launch lifecycle
# --------------------------------------------------------------------------- #
def test_budget_single_reservation_refusal(ledger):
    first = budget.reserve_budget(JOB, "a" * 40, "b" * 64, "4.00",
                                  launch.reservation_plan(), ledger)
    assert first["reservation"]["status"] == "RESERVED_NO_AUTOMATIC_REFUND"
    with pytest.raises(budget.BudgetRefused, match="JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY"):
        budget.reserve_budget(JOB, "a" * 40, "b" * 64, "4.00",
                              launch.reservation_plan(), ledger)


def test_execute_end_to_end_success(ledger):
    provider = FakeProvider(ledger)
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert result["status"] == "AWS_BINDING_FIT_FINISHED"
    assert result["reservation"]["reservation"]["status"] == "RESERVED_NO_AUTOMATIC_REFUND"
    assert result["cleanup"]["complete"] is True
    assert result["ledger_after"]["ledger"]["total_reserved_usd"] == "8.00"
    assert provider.calls == ["preflight", "reserve", "launch", "wait", "collect", "cleanup"]
    assert result["claims"]["final_targets_read"] is False


def test_execute_refuses_already_reserved_job(ledger):
    provider = FakeProvider(ledger)
    launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    before = ledger.read_bytes()
    with pytest.raises(ValueError, match="JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert ledger.read_bytes() == before


def test_execute_rejects_authority_not_bound_to_owner_record(ledger):
    authority = valid_authority()
    authority["owner_authorization_sha256"] = "0" * 64
    provider = FakeProvider(ledger)
    with pytest.raises(ValueError, match="OWNER_AUTHORIZATION_RECORD_MISMATCH"):
        launch.execute(valid_request(), authority, provider, ledger_path=ledger)
    assert provider.calls == []


def test_execute_records_incomplete_cleanup_instead_of_raising(ledger):
    provider = FakeProvider(ledger)
    original = provider.cleanup

    def broken(job):
        original(job)
        return {"complete": False, "failures": ["volume-left-behind"]}

    provider.cleanup = broken
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert result["status"] == "AWS_BINDING_FIT_FAILED"
    assert result["cleanup"]["complete"] is False
    assert result["cleanup_incomplete_reason"] == ["volume-left-behind"]
    saved = json.loads((Path(result["receipt_dir"]) / "result.json").read_bytes())
    assert saved["status"] == "AWS_BINDING_FIT_FAILED"
    assert saved["cleanup"]["complete"] is False


def test_execute_persists_evidence_when_cleanup_raises(ledger):
    provider = FakeProvider(ledger)

    def boom(job):
        raise RuntimeError("cleanup also failed")

    provider.cleanup = boom
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    saved = json.loads((Path(result["receipt_dir"]) / "result.json").read_bytes())
    assert saved["launch"]["job"] == JOB
    assert "cleanup also failed" in saved["cleanup"]["failures"][0]
    assert (Path(result["receipt_dir"]) / "reservation.json").is_file()


def test_execute_binds_provided_owner_record(ledger, tmp_path):
    """A later authorization record can be supplied explicitly; the authority
    must bind that exact file's digest."""
    provider = FakeProvider(ledger)
    alt_record = tmp_path / "OWNER_AUTHORIZATION_003.json"
    alt_record.write_text('{"owner": "attempt-003"}\n')
    authority = valid_authority()
    authority["owner_authorization_sha256"] = launch.digest(alt_record.read_bytes())
    result = launch.execute(valid_request(), authority, provider, ledger_path=ledger,
                            owner_authorization_path=alt_record)
    assert result["status"] == "AWS_BINDING_FIT_FINISHED"


def test_execute_owner_record_mismatch_raises(ledger, tmp_path):
    """Binding the default record digest against a different supplied record
    must refuse loudly before any provider call."""
    provider = FakeProvider(ledger)
    alt_record = tmp_path / "OWNER_AUTHORIZATION_003.json"
    alt_record.write_text('{"owner": "attempt-003"}\n')
    with pytest.raises(ValueError, match="OWNER_AUTHORIZATION_RECORD_MISMATCH"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger,
                       owner_authorization_path=alt_record)
    assert provider.calls == []


def test_build_prices_client_from_us_east_1(tmp_path):
    """The Price List API only serves us-east-1; all other clients stay us-west-2."""
    ledger_path = tmp_path / "ledger.json"
    created = []

    class FakeConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeSession:
        def __init__(self, profile_name, region_name):
            self.profile_name = profile_name
            self.region_name = region_name
            self.calls = []
            created.append(self)

        def client(self, name, config=None, region_name=None):
            self.calls.append((name, region_name))
            return SimpleNamespace()

    fake_module = SimpleNamespace(Config=FakeConfig, ClientError=FakeClientError,
                                  Session=FakeSession)
    arguments = SimpleNamespace(profile="binding_fit_training")
    launch.build(arguments, fake_module, job=JOB, source_sha="a" * 40,
                 archive_sha256="b" * 64, manifest_sha256="c" * 64,
                 ledger_path=ledger_path, client_error=FakeClientError)
    assert len(created) == 1
    assert created[0].profile_name == "binding_fit_training"
    assert created[0].region_name == "us-west-2"
    assert created[0].calls == [
        ("sts", None), ("ec2", None), ("iam", None), ("s3", None),
        ("scheduler", None), ("pricing", "us-east-1")]


# --------------------------------------------------------------------------- #
# provider cleanup with fake client stacks
# --------------------------------------------------------------------------- #
class FakeClientError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


def fake_clients(sg_groups=()):
    deleted_groups = []

    def raiser(code):
        def _raise(**kwargs):
            raise FakeClientError(code)
        return _raise

    ec2 = SimpleNamespace(
        describe_instances=raiser("InvalidInstanceID.NotFound"),
        describe_security_groups=lambda **k: {"SecurityGroups": list(sg_groups), "NextToken": None},
        delete_security_group=lambda GroupId: deleted_groups.append(GroupId),
    )
    scheduler = SimpleNamespace(get_schedule=raiser("ResourceNotFoundException"))
    iam = SimpleNamespace(get_role=raiser("NoSuchEntity"),
                          get_instance_profile=raiser("NoSuchEntity"),
                          remove_role_from_instance_profile=raiser("NoSuchEntity"),
                          delete_role_policy=raiser("NoSuchEntity"))
    s3 = SimpleNamespace(list_objects_v2=raiser("NoSuchBucket"))
    clients = {"ec2": ec2, "s3": s3, "iam": iam, "scheduler": scheduler}
    return clients, deleted_groups


def make_provider(ledger_path, clients):
    return launch.BindingFitProvider(job=JOB, source_sha="a" * 40, archive_sha256="b" * 64,
                                     manifest_sha256="c" * 64, ledger_path=ledger_path,
                                     clients=clients, client_error=FakeClientError)


def test_cleanup_already_absent_tolerance(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    clients, _ = fake_clients()
    provider = make_provider(ledger_path, clients)
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert status["complete"] is True
    assert status["failures"] == []
    assert status["security_group_deleted"] is True
    assert status["schedule_removed"] is True
    assert status["roles_removed"] is True
    assert status["bucket_deleted"] is True


def test_cleanup_security_group_deletion(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    clients, deleted_groups = fake_clients(sg_groups=[{"GroupId": "sg-0123456789abcdef0",
                                                        "GroupName": JOB}])
    provider = make_provider(ledger_path, clients)
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert deleted_groups == ["sg-0123456789abcdef0"]
    assert status["security_group_deleted"] is True
    assert status["complete"] is True


def test_cleanup_records_failure_instead_of_raising(tmp_path):
    ledger_path = tmp_path / "ledger.json"

    def deny(**kwargs):
        raise FakeClientError("AccessDenied")

    clients, _ = fake_clients()
    clients["s3"] = SimpleNamespace(list_objects_v2=deny)
    provider = make_provider(ledger_path, clients)
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert status["complete"] is False
    assert status["bucket_deleted"] is False
    assert any("EVIDENCE_CLEANUP_FAILED" in failure for failure in status["failures"])


def test_cleanup_detaches_role_before_deleting(tmp_path):
    """IAM answers DeleteConflict unless the role is detached first, so
    cleanup must order remove_role_from_instance_profile and delete_role_policy
    ahead of delete_role/delete_instance_profile."""
    ledger_path = tmp_path / "ledger.json"
    calls = []
    clients, _ = fake_clients()

    def present(**kwargs):
        return {}

    def record(op):
        def _record(**kwargs):
            calls.append((op, kwargs))
        return _record

    clients["iam"] = SimpleNamespace(
        get_role=present, get_instance_profile=present,
        remove_role_from_instance_profile=record("remove_role_from_instance_profile"),
        delete_role_policy=record("delete_role_policy"),
        delete_role=record("delete_role"), delete_instance_profile=record("delete_instance_profile"))
    provider = make_provider(ledger_path, clients)
    provider._resources["bucket"] = "job-bucket"
    status = provider.cleanup(JOB)
    assert [call[0] for call in calls] == [
        "remove_role_from_instance_profile", "delete_role_policy",
        "delete_role", "delete_role", "delete_instance_profile"]
    assert status["complete"] is True
    assert status["roles_removed"] is True


def test_await_instance_profile_waits_until_role_visible(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    clients, _ = fake_clients()
    profile_name = JOB + "-worker"
    state = {"calls": 0}

    def get_instance_profile(**kwargs):
        state["calls"] += 1
        roles = [{"RoleName": profile_name}] if state["calls"] >= 3 else []
        return {"InstanceProfile": {"Roles": roles}}

    clients["iam"] = SimpleNamespace(get_instance_profile=get_instance_profile)
    provider = make_provider(ledger_path, clients)
    (tmp_path / "evidence").mkdir()
    provider.configure_evidence(tmp_path / "evidence")
    observed = provider._await_instance_profile(clients["iam"], profile_name, profile_name,
                                                timeout=5.0, settle=0.0, poll_interval=0.01)
    assert observed["InstanceProfile"]["Roles"][0]["RoleName"] == profile_name
    assert state["calls"] == 3


def test_await_instance_profile_times_out(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    clients, _ = fake_clients()
    profile_name = JOB + "-worker"
    clients["iam"] = SimpleNamespace(
        get_instance_profile=lambda **kwargs: {"InstanceProfile": {"Roles": []}})
    provider = make_provider(ledger_path, clients)
    (tmp_path / "evidence").mkdir()
    provider.configure_evidence(tmp_path / "evidence")
    with pytest.raises(ValueError, match="BINDING_FIT_IAM_PROFILE_PROPAGATION_TIMEOUT"):
        provider._await_instance_profile(clients["iam"], profile_name, profile_name,
                                         timeout=0.05, settle=0.0, poll_interval=0.01)


def test_collect_writes_training_result_names(tmp_path):
    """collect() must write training_result.json, never result.json: execute()
    writes its own lifecycle summary to result.json in the same directory."""
    ledger_path = tmp_path / "ledger.json"
    clients, _ = fake_clients()
    raw = b'{"status": "REMOTE_FINISHED"}'
    sidecar = launch.digest(raw).encode("utf-8") + b"\n"
    clients["s3"] = SimpleNamespace(get_object=lambda **k: {"Body": io.BytesIO(sidecar)})
    provider = make_provider(ledger_path, clients)
    provider._resources["bucket"] = "job-bucket"
    provider._instance_id = "i-0123456789abcdef0"
    provider._result_raw = raw
    (tmp_path / "evidence").mkdir()
    provider.configure_evidence(tmp_path / "evidence")
    collected = provider.collect(JOB)
    assert collected["result_sha256"] == launch.digest(raw)
    assert (tmp_path / "evidence" / "training_result.json").is_file()
    assert (tmp_path / "evidence" / "training_result.json.sha256").is_file()
    assert not (tmp_path / "evidence" / "result.json").exists()


def test_await_terminated_waits(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    clients, _ = fake_clients()
    state = {"calls": 0}

    def describe(**kwargs):
        state["calls"] += 1
        name = "running" if state["calls"] < 3 else "terminated"
        return {"Reservations": [{"Instances": [{"State": {"Name": name}}]}]}

    clients["ec2"] = SimpleNamespace(describe_instances=describe)
    provider = make_provider(ledger_path, clients)
    pending = provider._await_terminated(clients["ec2"], ["i-0123456789abcdef0"],
                                         timeout=5.0, poll_interval=0.01)
    assert pending == []
    assert state["calls"] == 3


def test_await_terminated_treats_absent_as_terminated(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    clients, _ = fake_clients()  # describe_instances raises InvalidInstanceID.NotFound
    provider = make_provider(ledger_path, clients)
    pending = provider._await_terminated(clients["ec2"], ["i-0123456789abcdef0"],
                                         timeout=1.0, poll_interval=0.01)
    assert pending == []
