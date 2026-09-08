"""Fake-only tests: no AWS, neural code, SQLite, or budget mutations."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


subject = load("absent_cleanup_subject", ROOT / "tools/recover_teaching_continuation001_absent_cleanup.py")
previous_tests = load("absent_cleanup_previous_fakes", ROOT / "tests/test_teaching_continuation_cleanup_recovery.py")
CloudError = previous_tests.CloudError


class Cloud(previous_tests.Cloud):
    def __init__(self, schedule):
        super().__init__(schedule)
        self.instance_answers = {}
        self.inline = {role: ["job-only"] for role in (subject.WORKER, subject.TIMER)}
        self.attached = {role: [] for role in self.inline}
        self.extra_profiles = {role: [] for role in self.inline}
        self.policy_docs = subject.policies()
        self.response_changes = {}
        self.keep_resource = None
        self.change_results_after_delete = False

    def call(self, service, method, args):
        if method == "describe_instances":
            self.calls.append((service, method, deepcopy(args)))
            value = self.instance_answers.get(json.dumps(args, sort_keys=True), {"Reservations": []})
            if isinstance(value, Exception): raise value
            answer = deepcopy(value)
        elif method in ("list_role_policies", "list_attached_role_policies", "list_instance_profiles_for_role", "get_role_policy"):
            self.calls.append((service, method, deepcopy(args)))
            role = args["RoleName"]
            if role not in self.roles: raise CloudError("NoSuchEntity")
            if method == "list_role_policies": answer = {"PolicyNames": deepcopy(self.inline[role])}
            elif method == "list_attached_role_policies": answer = {"AttachedPolicies": deepcopy(self.attached[role])}
            elif method == "list_instance_profiles_for_role":
                rows = [deepcopy(self.profile)] if role == subject.WORKER and self.profile and self.profile["Roles"] else []
                answer = {"InstanceProfiles": rows + deepcopy(self.extra_profiles[role])}
            else:
                if not self.inline[role]: raise CloudError("NoSuchEntity")
                answer = {"RoleName": role, "PolicyName": "job-only", "PolicyDocument": deepcopy(self.policy_docs[role])}
        elif method == "delete_role_policy":
            self.calls.append((service, method, deepcopy(args)))
            if self.keep_resource != method: self.inline[args["RoleName"]] = []
            answer = {}
        elif self.keep_resource == method:
            self.calls.append((service, method, deepcopy(args)))
            answer = {}
        else:
            answer = super().call(service, method, args)
        if method.startswith(("delete_", "remove_")) and self.change_results_after_delete:
            self.objects[0]["ETag"] = '"changed"'
        if method in self.response_changes:
            answer.update(deepcopy(self.response_changes[method]))
        return answer


@pytest.fixture
def setup(tmp_path, monkeypatch):
    helper = subject.load_helper()
    original, prior = tmp_path / "original", tmp_path / "previous"
    original.mkdir()
    prior.mkdir()
    for name in (*helper.PINS, "source.zip"):
        (original / name).write_bytes((subject.ORIGINAL / name).read_bytes())
    for name in subject.PREVIOUS_PINS:
        (prior / name).write_bytes((subject.PREVIOUS / name).read_bytes())
    helper_copy = tmp_path / "helper.py"
    helper_copy.write_bytes(subject.HELPER.read_bytes())
    monkeypatch.setattr(subject, "ORIGINAL", original)
    monkeypatch.setattr(subject, "PREVIOUS", prior)
    monkeypatch.setattr(subject, "HELPER", helper_copy)
    monkeypatch.setattr(subject, "DESTINATION", tmp_path / "cleanup_recovery_002")
    helper.ORIGINAL = original
    ledger = json.loads((prior / "intent.json").read_bytes())["ledger_sha256_before"]
    monkeypatch.setattr(helper, "ledger_hash", lambda path: ledger)
    monkeypatch.setattr(subject, "load_helper", lambda: helper)
    schedule = json.loads((original / "teaching_provider_0045.json").read_bytes())["schedule"]
    cloud = Cloud(schedule)
    clients = {name: cloud.client(name) for name in ("sts", "ec2", "iam", "scheduler", "s3")}
    return cloud, clients, helper, ledger


def run(setup, **kwargs):
    return subject.recover(subject.DESTINATION, clients=setup[1], **kwargs)


def mutations(cloud):
    return [row for row in cloud.calls if row[1].startswith(("delete_", "remove_", "put_", "create_", "terminate_"))]


def test_owned_resources_removed_after_three_absence_checks_and_results_retained(setup):
    cloud, _, _, _ = setup
    before = deepcopy(cloud.objects)
    result = run(setup)
    assert result["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED", result
    assert result["compute_state"] == "CONFIRMED_ABSENT_NOT_TERMINATION_RECEIPT"
    assert result["fresh_termination_receipt"] is False
    assert result["cleanup"]["compute_closed"] is True and result["cleanup"]["instance_terminated"] is False
    assert result["cleanup"]["instance_state"] == subject.COMPUTE_STATE and result["cleanup"]["complete"]
    assert result["original_parent_result_unchanged"] and result["provider_sources_unchanged"] and result["prior_recovery_unchanged"]
    assert result["original_and_previous_unchanged"] and result["sources_unchanged"] and result["ledger_unchanged"]
    assert cloud.roles == {} and cloud.group is cloud.schedule is cloud.profile is None
    assert cloud.objects == before and result["cloud_copy_retained"]
    assert not result["results_deleted"] and not result["bucket_deleted"]
    assert all(s != "s3" for s, _, _ in mutations(cloud))
    first_mutation = next(i for i, (_, method, _) in enumerate(cloud.calls) if method.startswith(("delete_", "remove_")))
    prefix = cloud.calls[:first_mutation]
    assert len([r for r in prefix if r[1] == "describe_instances"]) == 3
    assert len([r for r in prefix if r[1] == "list_objects_v2"]) == 2
    assert len([r for r in cloud.calls if r[1] == "list_objects_v2"]) == 3
    assert result["counters_after"] == {"control": 347 + sum(s != "s3" for s, _, _ in cloud.calls),
        "s3": 532 + sum(s == "s3" for s, _, _ in cloud.calls), "downloaded_bytes": 201761654,
        "recovery_sdk_calls": len(cloud.calls)}
    for index, (service, method, args) in enumerate(cloud.calls, 1):
        path = subject.DESTINATION / ("%03d_%s_%s_intent.json" % (index, service, method))
        assert json.loads(path.read_bytes())["arguments"] == args
    environment = json.loads((subject.DESTINATION / "intent.json").read_bytes())["environment"]
    assert environment["tool_sha256"] == sha256(Path(subject.__file__).read_bytes()).hexdigest()
    assert environment["clients_injected"] is True


def test_exact_not_found_error_is_accepted_only_for_exact_instance(setup):
    cloud = setup[0]
    cloud.instance_answers[json.dumps(subject.EXACT_INSTANCE, sort_keys=True)] = CloudError("InvalidInstanceID.NotFound")
    result = run(setup)
    assert result["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED", result
    raw = json.loads((subject.DESTINATION / "002_ec2_describe_instances_error.json").read_bytes())
    assert raw["response"]["Error"]["Code"] == "InvalidInstanceID.NotFound"


def test_already_absent_controls_do_not_trigger_mutations(setup):
    cloud = setup[0]
    cloud.group = cloud.schedule = cloud.profile = None
    cloud.roles = {}
    result = run(setup)
    assert result["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED", result
    assert not mutations(cloud)


def test_profile_list_may_omit_tags_when_exact_get_proves_ownership(setup):
    cloud = setup[0]
    original = cloud.call
    def call(service, method, args):
        result = original(service, method, args)
        if method == "list_instance_profiles_for_role":
            for row in result["InstanceProfiles"]: row.pop("Tags", None)
        return result
    cloud.call = call
    result = run(setup)
    assert result["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED", result


@pytest.mark.parametrize("method,key", [("describe_security_groups", "SecurityGroups"),
    ("get_instance_profile", "Roles"), ("list_objects_v2", "IsTruncated")])
def test_missing_resource_response_fields_refuse_all_mutations(setup, method, key):
    cloud = setup[0]
    original = cloud.call
    def call(service, requested, args):
        result = original(service, requested, args)
        if requested == method:
            (result["InstanceProfile"] if method == "get_instance_profile" else result).pop(key, None)
        return result
    cloud.call = call
    result = run(setup)
    assert result["status"] == "BLOCKED" and not mutations(cloud)


@pytest.mark.parametrize("query", [subject.EXACT_INSTANCE, subject.TAG_INSTANCE, subject.TOKEN_INSTANCE])
@pytest.mark.parametrize("answer", [{}, {"Reservations": [{"Instances": []}]},
    {"Reservations": [{"Instances": [{"InstanceId": subject.INSTANCE, "State": {"Name": "terminated"}}]}]},
    {"Reservations": [], "NextToken": "page"}])
def test_instance_query_ambiguity_or_nonempty_refuses_all_mutations(setup, query, answer):
    setup[0].instance_answers[json.dumps(query, sort_keys=True)] = answer
    result = run(setup)
    assert result["status"] == "BLOCKED" and not result["mutations_admitted"]
    assert not mutations(setup[0])


@pytest.mark.parametrize("query,code", [(subject.TAG_INSTANCE, "InvalidInstanceID.NotFound"),
    (subject.TOKEN_INSTANCE, "InvalidInstanceID.NotFound"), (subject.EXACT_INSTANCE, "UnauthorizedOperation")])
def test_wrong_query_not_found_or_denial_is_not_absence(setup, query, code):
    setup[0].instance_answers[json.dumps(query, sort_keys=True)] = CloudError(code)
    result = run(setup)
    assert result["status"] == "BLOCKED" and not mutations(setup[0])


@pytest.mark.parametrize("kind", ["account", "region", "volume", "group", "group_tag", "role", "role_tag",
    "profile", "profile_tag", "profile_roles", "schedule", "inline", "attached", "association", "policy",
    "result_key", "result_identity", "retention"])
def test_ownership_and_preservation_gates_precede_mutations(setup, kind):
    cloud, clients, _, _ = setup
    if kind == "account": cloud.account = "000000000000"
    elif kind == "region": clients["ec2"].meta = SimpleNamespace(region_name="us-east-1")
    elif kind == "volume": cloud.volumes = [{"VolumeId": "vol-other"}]
    elif kind == "group": cloud.group["GroupId"] = "sg-other"
    elif kind == "group_tag": cloud.group["Tags"] = []
    elif kind == "role": cloud.roles[subject.WORKER]["Arn"] += "-other"
    elif kind == "role_tag": cloud.roles[subject.TIMER]["Tags"] = []
    elif kind == "profile": cloud.profile["Arn"] += "-other"
    elif kind == "profile_tag": cloud.profile["Tags"] = []
    elif kind == "profile_roles": cloud.profile["Roles"].append({"RoleName": "other"})
    elif kind == "schedule": cloud.schedule["Target"]["Input"] = "{}"
    elif kind == "inline": cloud.inline[subject.WORKER].append("other")
    elif kind == "attached": cloud.attached[subject.TIMER] = [{"PolicyArn": "arn:other"}]
    elif kind == "association": cloud.extra_profiles[subject.TIMER] = [{"InstanceProfileName": "other"}]
    elif kind == "policy": cloud.policy_docs[subject.WORKER]["Statement"][0]["Resource"] = ["*"]
    elif kind == "result_key": cloud.objects.append({"Key": "other", "Size": 1, "ETag": "x"})
    elif kind == "result_identity": cloud.objects[0]["ETag"] = ""
    elif kind == "retention": cloud.lifecycle["Rules"][0]["Expiration"]["Days"] = 1
    result = run(setup)
    assert result["status"] == "BLOCKED" and not result["mutations_admitted"], result
    assert not mutations(cloud)


@pytest.mark.parametrize("method", ["describe_volumes", "describe_security_groups", "get_schedule", "get_role",
    "get_instance_profile", "list_role_policies", "list_attached_role_policies", "list_instance_profiles_for_role",
    "get_role_policy", "list_objects_v2", "get_bucket_lifecycle_configuration"])
def test_any_pagination_is_rejected(setup, method):
    setup[0].response_changes[method] = {"NextToken": "another-page"}
    result = run(setup)
    assert result["status"] == "BLOCKED" and not mutations(setup[0])


@pytest.mark.parametrize("name", list(subject.PREVIOUS_PINS))
def test_previous_receipt_pins_checked_before_output_or_sdk(setup, name):
    path = subject.PREVIOUS / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="PREVIOUS_PIN"):
        run(setup)
    assert not setup[0].calls and not subject.DESTINATION.exists()


@pytest.mark.parametrize("what", ["helper", "original", "source"])
def test_source_and_original_pins_checked_before_output_or_sdk(setup, what):
    path = subject.HELPER if what == "helper" else subject.ORIGINAL / ("source.zip" if what == "source" else "result.json")
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="PIN"):
        run(setup)
    assert not setup[0].calls and not subject.DESTINATION.exists()


@pytest.mark.parametrize("when", ["prior", "before_mutation", "after_mutation"])
def test_ledger_drift_refuses_success(setup, monkeypatch, when):
    values = {"prior": ["0" * 64], "before_mutation": [setup[3], "0" * 64, "0" * 64],
              "after_mutation": [setup[3], setup[3], "0" * 64]}[when]
    iterator = iter(values)
    monkeypatch.setattr(setup[2], "ledger_hash", lambda path: next(iterator))
    if when == "prior":
        with pytest.raises(ValueError, match="PRIOR_LEDGER_DRIFT"): run(setup)
        assert not subject.DESTINATION.exists()
    else:
        result = run(setup)
        assert result["status"] == "BLOCKED" and not result["ledger_unchanged"]
    if when != "after_mutation": assert not mutations(setup[0])


def test_changed_results_after_control_deletion_cannot_close(setup):
    setup[0].change_results_after_delete = True
    result = run(setup)
    assert result["status"] == "BLOCKED" and "RESULT_OBJECTS_CHANGED" in result["failure"]["message"]
    assert not result["cloud_copy_retained"]


def test_compute_reappearance_during_final_readback_cannot_claim_closed(setup):
    cloud = setup[0]
    original = cloud.call
    def call(service, method, args):
        result = original(service, method, args)
        if method == "describe_instances" and mutations(cloud):
            result["Reservations"] = [{"Instances": [{"InstanceId": "i-other"}]}]
        return result
    cloud.call = call
    result = run(setup)
    assert result["status"] == "BLOCKED" and result["compute_state"] == "UNCONFIRMED"
    assert result["cleanup"]["compute_closed"] is False


@pytest.mark.parametrize("method", ["delete_schedule", "remove_role_from_instance_profile", "delete_instance_profile",
                                    "delete_role_policy", "delete_role", "delete_security_group"])
def test_every_removal_requires_live_readback(setup, method):
    setup[0].keep_resource = method
    result = run(setup)
    assert result["status"] == "BLOCKED", result


@pytest.mark.parametrize("missing", ["boto3", "botocore"])
def test_sdk_presence_checked_before_consuming_destination(setup, monkeypatch, missing):
    monkeypatch.setattr(subject, "find_spec", lambda name: None if name == missing else object())
    with pytest.raises(ValueError, match="SDK_UNAVAILABLE_NO_OUTPUT_CONSUMED"):
        subject.recover(subject.DESTINATION)
    assert not subject.DESTINATION.exists() and not setup[0].calls


def test_destination_is_exact_and_one_shot(setup):
    with pytest.raises(ValueError, match="EXACT_FRESH_DESTINATION"):
        subject.recover(subject.DESTINATION.parent / "other", clients=setup[1])
    run(setup)
    calls = len(setup[0].calls)
    with pytest.raises(ValueError, match="EXACT_FRESH_DESTINATION"): run(setup)
    assert len(setup[0].calls) == calls


@pytest.mark.parametrize("service,method,args", [
    ("ec2", "run_instances", {}), ("ec2", "terminate_instances", subject.EXACT_INSTANCE),
    ("ec2", "delete_volume", {"VolumeId": "vol-other"}), ("s3", "put_object", {"Bucket": subject.BUCKET}),
    ("s3", "delete_objects", {"Bucket": subject.BUCKET}), ("s3", "delete_bucket", {"Bucket": subject.BUCKET}),
    ("iam", "delete_role", {"RoleName": "other"}), ("iam", "delete_role_policy", {"RoleName": subject.WORKER, "PolicyName": "other"}),
])
def test_operation_allowlist_even_when_armed(setup, service, method, args):
    scope = subject.Scope(setup[2], setup[1], subject.DESTINATION.parent, setup[0].schedule)
    scope.armed = True
    with pytest.raises(ValueError): scope.call(service, method, args)
    assert not setup[0].calls


def test_mutations_and_call_ceiling_fail_before_sdk(setup):
    scope = subject.Scope(setup[2], setup[1], subject.DESTINATION.parent, setup[0].schedule)
    with pytest.raises(ValueError, match="MUTATION_BEFORE_ADMISSION"):
        scope.call("scheduler", "delete_schedule", {"Name": subject.JOB})
    scope.calls = subject.MAX_CALLS
    with pytest.raises(ValueError, match="RECOVERY_CALL_OR_TIME_BOUND"):
        scope.call("sts", "get_caller_identity", {})
    scope.calls = 0
    scope.started -= subject.MAX_SECONDS + 1
    with pytest.raises(ValueError, match="RECOVERY_CALL_OR_TIME_BOUND"):
        scope.call("sts", "get_caller_identity", {})
    assert not setup[0].calls


def test_budget_interface_remains_unusable(setup):
    with pytest.raises(ValueError, match="BUDGET_CALL_FORBIDDEN"):
        setup[2].NoBudget().reserve_budget
