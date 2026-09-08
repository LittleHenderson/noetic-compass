"""Fake-only recovery tests: no SDK, neural imports, SQLite or ledger writes."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("continuation001_cleanup_test_subject", ROOT / "tools/recover_teaching_continuation001_cleanup.py")
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class CloudError(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}
        super().__init__(code)


class Cloud:
    def __init__(self, schedule):
        self.calls = []
        self.account = subject.ACCOUNT
        self.instance = {"InstanceId": subject.INSTANCE, "ClientToken": subject.JOB,
                         "Tags": [{"Key": "cas_meta_job", "Value": subject.JOB}], "State": {"Name": "terminated"}}
        self.volumes = []
        self.group = {"GroupId": subject.GROUP, "GroupName": subject.JOB, "OwnerId": subject.ACCOUNT,
                      "Tags": [{"Key": "cas_meta_job", "Value": subject.JOB}]}
        self.roles = {name: {"RoleName": name, "Arn": "arn:aws:iam::" + subject.ACCOUNT + ":role/" + name,
                            "Tags": [{"Key": "cas_meta_job", "Value": subject.JOB}]}
                      for name in (subject.WORKER, subject.TIMER)}
        self.profile = {"InstanceProfileName": subject.WORKER,
                        "Arn": "arn:aws:iam::" + subject.ACCOUNT + ":instance-profile/" + subject.WORKER,
                        "Tags": [{"Key": "cas_meta_job", "Value": subject.JOB}],
                        "Roles": [deepcopy(self.roles[subject.WORKER])]}
        self.schedule = deepcopy(schedule)
        self.objects = [{"Key": key, "Size": 100, "ETag": '"' + sha256(key.encode()).hexdigest() + '"'}
                        for key in sorted(subject.RESULT_KEYS)]
        self.lifecycle = {"Rules": deepcopy(subject.RETENTION_RULES)}
        self.fail_delete = None

    def client(self, service):
        owner = self
        class Client:
            meta = SimpleNamespace(region_name="aws-global" if service == "iam" else subject.REGION)
            def __getattr__(self, method):
                return lambda **arguments: owner.call(service, method, arguments)
        return Client()

    def call(self, service, method, args):
        self.calls.append((service, method, deepcopy(args)))
        if method == self.fail_delete:
            raise CloudError("AccessDenied")
        if method == "get_caller_identity":
            return {"Account": self.account}
        if method == "describe_instances":
            return {"Reservations": [{"Instances": [deepcopy(self.instance)]}]}
        if method == "describe_volumes":
            return {"Volumes": deepcopy(self.volumes)}
        if method == "describe_security_groups":
            return {"SecurityGroups": [] if self.group is None else [deepcopy(self.group)]}
        if method == "delete_security_group":
            self.group = None
        elif method == "get_schedule":
            if self.schedule is None:
                raise CloudError("ResourceNotFoundException")
            return deepcopy(self.schedule)
        elif method == "delete_schedule":
            self.schedule = None
        elif method == "get_role":
            if args["RoleName"] not in self.roles:
                raise CloudError("NoSuchEntity")
            return {"Role": deepcopy(self.roles[args["RoleName"]])}
        elif method == "delete_role":
            self.roles.pop(args["RoleName"])
        elif method == "delete_role_policy":
            pass
        elif method == "get_instance_profile":
            if self.profile is None:
                raise CloudError("NoSuchEntity")
            return {"InstanceProfile": deepcopy(self.profile)}
        elif method == "remove_role_from_instance_profile":
            self.profile["Roles"] = []
        elif method == "delete_instance_profile":
            self.profile = None
        elif method == "list_objects_v2":
            return {"Contents": deepcopy(self.objects), "IsTruncated": False}
        elif method == "get_bucket_lifecycle_configuration":
            return deepcopy(self.lifecycle)
        else:
            raise AssertionError("Unexpected fake SDK call: " + service + "." + method)
        return {"ResponseMetadata": {"RequestId": "fake-cleanup-request"}}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    original = tmp_path / "original"
    original.mkdir()
    for name in (*subject.PINS, "source.zip"):
        (original / name).write_bytes((subject.ORIGINAL / name).read_bytes())
    monkeypatch.setattr(subject, "ORIGINAL", original)
    monkeypatch.setattr(subject, "DESTINATION", tmp_path / "cleanup_recovery_001")
    monkeypatch.setattr(subject, "ledger_hash", lambda path: "9" * 64)
    schedule = json.loads((original / "teaching_provider_0045.json").read_bytes())["schedule"]
    cloud = Cloud(schedule)
    clients = {name: cloud.client(name) for name in ("sts", "ec2", "iam", "scheduler", "s3")}
    return cloud, clients


def run(setup, **kwargs):
    return subject.recover(subject.DESTINATION, clients=setup[1], **kwargs)


def mutations(cloud):
    return [(s, m, a) for s, m, a in cloud.calls if m.startswith(("delete_", "remove_", "put_", "create_", "terminate_"))]


def test_real_provider_cleanup_completes_and_retains_all_results(setup):
    cloud, _ = setup
    before = deepcopy(cloud.objects)
    result = run(setup)
    assert result["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED", result
    assert result["ledger_unchanged"] and result["original_parent_result_unchanged"]
    assert result["provider_sources_unchanged"] and result["run_id"] == subject.LOGICAL_RUN
    assert result["job"] != result["run_id"]
    assert result["cleanup"]["instance_terminated"] and result["cleanup"]["volumes_deleted"]
    assert result["cleanup"]["cloud_copy_retained"] and not result["cleanup"]["results_deleted"]
    assert cloud.objects == before
    assert cloud.group is None and cloud.profile is None and cloud.schedule is None and cloud.roles == {}
    assert all(s != "s3" for s, _, _ in mutations(cloud))
    assert all(m not in ("terminate_instances", "run_instances", "delete_volume") for _, m, _ in cloud.calls)
    assert result["counters_after"]["s3"] > subject.S3_CONSUMED
    assert result["counters_after"]["control"] > subject.CONTROL_CONSUMED
    assert result["counters_after"]["downloaded_bytes"] == subject.DOWNLOADED
    assert (subject.DESTINATION / "admission.json").is_file()
    assert (subject.DESTINATION / "teaching_provider_0001.json").is_file()
    intent = json.loads((subject.DESTINATION / "intent.json").read_bytes())
    environment = intent["environment"]
    assert environment["tool_sha256"] == sha256(Path(subject.__file__).read_bytes()).hexdigest()
    assert Path(environment["python_executable"]).is_absolute() and environment["clients_injected"] is True
    assert Path(environment["absolute_cli_equivalent"][1]).is_absolute()


def test_already_absent_control_resources_are_observed_without_delete(setup):
    cloud, _ = setup
    cloud.group = cloud.profile = cloud.schedule = None
    cloud.roles = {}
    result = run(setup)
    assert result["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED", result
    assert not mutations(cloud)


@pytest.mark.parametrize("kind", ["account", "region", "running", "instance", "token", "tag", "volume",
                                  "group", "group_owner", "role", "role_tag", "profile", "profile_tag",
                                  "schedule", "result_key", "retention", "additional_retention_rule"])
def test_read_only_identity_refusals_precede_every_mutation(setup, kind):
    cloud, clients = setup
    if kind == "account": cloud.account = "000000000000"
    elif kind == "region": clients["ec2"].meta = SimpleNamespace(region_name="us-east-1")
    elif kind == "running": cloud.instance["State"]["Name"] = "running"
    elif kind == "instance": cloud.instance["InstanceId"] = "i-0123456789abcdef0"
    elif kind == "token": cloud.instance["ClientToken"] = "different-job"
    elif kind == "tag": cloud.instance["Tags"] = []
    elif kind == "volume": cloud.volumes = [{"VolumeId": "vol-0123456789abcdef0"}]
    elif kind == "group": cloud.group["GroupId"] = "sg-0123456789abcdef0"
    elif kind == "group_owner": cloud.group["OwnerId"] = "000000000000"
    elif kind == "role": cloud.roles[subject.TIMER]["Arn"] += "-changed"
    elif kind == "role_tag": cloud.roles[subject.TIMER]["Tags"] = []
    elif kind == "profile": cloud.profile["Arn"] += "-changed"
    elif kind == "profile_tag": cloud.profile["Tags"] = []
    elif kind == "schedule": cloud.schedule["Target"]["Input"] = '{"InstanceIds": ["i-0123456789abcdef0"]}'
    elif kind == "result_key": cloud.objects.append({"Key": "input/source.zip", "Size": 1, "ETag": "x"})
    elif kind == "retention": cloud.lifecycle["Rules"][0]["Expiration"]["Days"] = 1
    elif kind == "additional_retention_rule": cloud.lifecycle["Rules"].append(
        {"ID": "early-delete", "Status": "Enabled", "Filter": {"Prefix": "results/"}, "Expiration": {"Days": 1}})
    result = run(setup)
    assert result["status"] == "BLOCKED" and not result["mutations_admitted"], result
    assert not mutations(cloud)


@pytest.mark.parametrize("name", list(subject.PINS))
def test_each_original_hash_is_required_before_client_calls(setup, name):
    path = subject.ORIGINAL / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="ORIGINAL_PIN"):
        run(setup)
    assert not setup[0].calls and not subject.DESTINATION.exists()


def test_one_shot_destination_refuses_counter_reset(setup):
    first = run(setup)
    calls = len(setup[0].calls)
    with pytest.raises(ValueError, match="EXACT_FRESH_DESTINATION"):
        run(setup)
    assert len(setup[0].calls) == calls and first["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED"


def test_wrong_output_refused_before_client_calls(setup):
    with pytest.raises(ValueError, match="EXACT_FRESH_DESTINATION"):
        subject.recover(subject.DESTINATION.parent / "another", clients=setup[1])
    assert not setup[0].calls


@pytest.mark.parametrize("missing", ["boto3", "botocore"])
def test_missing_sdk_refuses_without_consuming_output(setup, monkeypatch, missing):
    monkeypatch.setattr(subject, "find_spec", lambda name: None if name == missing else object())
    monkeypatch.setattr(subject, "clients_for", lambda profile: pytest.fail("SDK factory must not run"))
    with pytest.raises(ValueError, match="SDK_UNAVAILABLE_NO_OUTPUT_CONSUMED"):
        subject.recover(subject.DESTINATION)
    assert not subject.DESTINATION.exists() and not setup[0].calls


@pytest.mark.parametrize("service,method,args", [
    ("ec2", "run_instances", {}), ("ec2", "terminate_instances", {"InstanceIds": [subject.INSTANCE]}),
    ("ec2", "delete_volume", {"VolumeId": "vol-0123456789abcdef0"}),
    ("s3", "delete_objects", {"Bucket": subject.BUCKET}), ("s3", "delete_bucket", {"Bucket": subject.BUCKET}),
    ("s3", "put_object", {"Bucket": subject.BUCKET}),
    ("iam", "delete_role", {"RoleName": "other"}),
    ("ec2", "delete_security_group", {"GroupId": "sg-other"}),
])
def test_operation_allowlist_forbids_broader_calls(setup, service, method, args):
    cloud, clients = setup
    scope = subject.Scope(clients, subject.DESTINATION.parent, cloud.schedule)
    scope.armed = True
    with pytest.raises(ValueError): scope.call(service, method, args)
    assert not cloud.calls


def test_delete_requires_completed_read_only_admission(setup):
    cloud, clients = setup
    scope = subject.Scope(clients, subject.DESTINATION.parent, cloud.schedule)
    with pytest.raises(ValueError, match="MUTATION_BEFORE_ADMISSION"):
        scope.call("scheduler", "delete_schedule", {"Name": subject.JOB})
    assert not cloud.calls


def test_ledger_drift_before_cleanup_refuses_mutations(setup, monkeypatch):
    values = iter(["9" * 64, "8" * 64, "8" * 64])
    monkeypatch.setattr(subject, "ledger_hash", lambda path: next(values))
    result = run(setup)
    assert result["status"] == "BLOCKED" and not result["ledger_unchanged"]
    assert not mutations(setup[0])


def test_provider_failure_is_supplemental_and_does_not_delete_results(setup):
    cloud, _ = setup
    cloud.fail_delete = "delete_schedule"
    result = run(setup)
    assert result["status"] == "BLOCKED" and not result["cleanup"]["complete"]
    assert result["original_parent_result_unchanged"] and result["ledger_unchanged"]
    assert all(s != "s3" for s, _, _ in mutations(cloud))


def test_call_and_time_ceiling_precede_sdk(setup):
    cloud, clients = setup
    scope = subject.Scope(clients, subject.DESTINATION.parent, cloud.schedule)
    scope.calls = subject.MAX_CALLS
    with pytest.raises(ValueError, match="RECOVERY_CALL_OR_TIME_BOUND"):
        scope.call("sts", "get_caller_identity", {})
    assert not cloud.calls
    ticks = iter([0, subject.MAX_SECONDS + 1])
    scope = subject.Scope(clients, subject.DESTINATION.parent, cloud.schedule, lambda: next(ticks))
    with pytest.raises(ValueError, match="RECOVERY_CALL_OR_TIME_BOUND"):
        scope.call("sts", "get_caller_identity", {})
    assert not cloud.calls


def test_budget_interface_is_unusable():
    with pytest.raises(ValueError, match="BUDGET_CALL_FORBIDDEN"):
        subject.NoBudget().reserve_budget
