"""One-shot cleanup after continuation 001's exact instance listing expired.

No launch, termination, volume deletion, S3 mutation, or budget call is possible.
Absence is not a termination receipt. Import performs no reads or SDK calls.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import importlib.util
from importlib.util import find_spec
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tools/recover_teaching_continuation001_cleanup.py"
HELPER_SHA = "05acae6c6b3507a36e2a94b3a14640ebd211461416c922117987f900110c3aa8"
ORIGINAL = ROOT / "records/teaching_cycle_001/continuation_001/launch"
PREVIOUS = ORIGINAL.parent / "cleanup_recovery_001"
DESTINATION = ORIGINAL.parent / "cleanup_recovery_002"
PREVIOUS_PINS = {
    "result.json": "49afeaa7bbfea89036e875336f22c65e7442a26f5fa3768875516d782d949a2e",
    "intent.json": "b80af4e1f9f26cfe4fd7587d914f1c99ad434772614addb0cc2a43b9a43c967f",
    "002_ec2_describe_instances_result.json": "b482a3089a65120d0cea7a05ed86556c5d99d6a9aace7a1d7054ed76bfd4de3d",
    "002_ec2_describe_instances_intent.json": "5b8b21d8cfac7a32df5e7aff70b778a33044f19c2606be63b20701ed2fd91e82",
    "001_sts_get_caller_identity_result.json": "e230d40ad58cd3b18995e8773f96dab927179dcf1fc3c2c1dd5a918335648ff2",
}
JOB = "cas-meta2-teaching-20260908080138-5518e287"
ACCOUNT, REGION = "807562639912", "us-west-2"
INSTANCE, GROUP = "i-0c89cf580dd58a803", "sg-0b4587c7ff2d2b173"
BUCKET, WORKER, TIMER = JOB + "-" + ACCOUNT, JOB + "-worker", JOB + "-timer"
CONTROL_CONSUMED, S3_CONSUMED, DOWNLOADED = 347, 532, 201761654
MAX_CALLS, MAX_SECONDS = 192, 600
COMPUTE_STATE = "CONFIRMED_ABSENT_NOT_TERMINATION_RECEIPT"
BOUNDARY = "Cleanup only. Current absence is not a fresh termination receipt. No workload or learning claim."
EXACT_INSTANCE = {"InstanceIds": [INSTANCE]}
TAG_INSTANCE = {"Filters": [{"Name": "tag:cas_meta_job", "Values": [JOB]}]}
TOKEN_INSTANCE = {"Filters": [{"Name": "client-token", "Values": [JOB]}]}


def require(value, code):
    if not value:
        raise ValueError("CONTINUATION001_ABSENT_CLEANUP:" + code)


def load_helper():
    require(sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA, "HELPER_PIN")
    spec = importlib.util.spec_from_file_location("_continuation001_absent_helpers", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.ORIGINAL = ORIGINAL
    require(sha256(helper.read(HELPER)).hexdigest() == HELPER_SHA, "HELPER_PIN")
    return helper


def inputs(helper):
    require(sha256(helper.read(HELPER)).hexdigest() == HELPER_SHA, "HELPER_PIN")
    documents = helper.inputs()
    previous = {}
    for name, digest in PREVIOUS_PINS.items():
        raw = helper.read(PREVIOUS / name)
        require(sha256(raw).hexdigest() == digest, "PREVIOUS_PIN:" + name)
        previous[name] = json.loads(raw)
    result, intent = previous["result.json"], previous["intent.json"]
    require(result["status"] == "BLOCKED" and result["mutations_admitted"] is False
            and result["cleanup"] is None and result["counters_after"] == {
                "control": CONTROL_CONSUMED, "s3": S3_CONSUMED,
                "downloaded_bytes": DOWNLOADED, "recovery_sdk_calls": 2}, "PREVIOUS_COUNTERS_OR_EFFECTS")
    require(result["original_parent_result_unchanged"] and result["provider_sources_unchanged"]
            and result["ledger_unchanged"] and result["job"] == JOB
            and intent["job"] == JOB and intent["request_sha256"] == helper.REQUEST_SHA
            and intent["environment"]["tool_sha256"] == HELPER_SHA
            and intent["resources"] == helper.RESOURCES, "PREVIOUS_IDENTITY")
    require(previous["002_ec2_describe_instances_intent.json"] == {
        "service": "ec2", "method": "describe_instances", "arguments": EXACT_INSTANCE}, "PREVIOUS_QUERY")
    require(previous["002_ec2_describe_instances_result.json"]["response"]["Reservations"] == []
            and not previous["002_ec2_describe_instances_result.json"]["response"].get("NextToken")
            and previous["001_sts_get_caller_identity_result.json"]["response"]["Account"] == ACCOUNT,
            "PREVIOUS_ABSENCE_OBSERVATION")
    return documents


def check_sources(helper, context):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from aws import teaching_continuation_provider as provider
    require(sha256(helper.read(provider.__file__)).hexdigest() == context["bindings"]["provider_source_sha256"]
            and provider.plan.canonical_sha256(provider.source_dependencies())
            == context["bindings"]["provider_dependencies_sha256"]
            and sha256(helper.read(ORIGINAL / "source.zip", 32 * 1024**2)).hexdigest()
            == context["bindings"]["archive_sha256"], "PROVIDER_SOURCE_PINS")


def policies():
    return {
        WORKER: {"Version": "2012-10-17", "Statement": [
            {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::" + BUCKET]},
            {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::" + BUCKET + "/input/" + name
                for name in ("source.zip", "remote.py", "config.json", "permit.json", "public.json", "public_release.json",
                    "base_remote.py", "continuation_package.py", "restore_probe.py", "prior_state.zip",
                    "prior_state_manifest.json", "train_release.json")]},
            {"Effect": "Allow", "Action": ["s3:PutObject"], "Resource": ["arn:aws:s3:::" + BUCKET + "/results/*"]}]},
        TIMER: {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "ec2:TerminateInstances",
            "Resource": "arn:aws:ec2:" + REGION + ":" + ACCOUNT + ":instance/*",
            "Condition": {"StringEquals": {"ec2:ResourceTag/cas_meta_job": JOB}}}]},
    }


class Scope:
    """Exact operations, raw receipts, bounded calls, and fail-closed admission."""
    def __init__(self, helper, clients, output, schedule, clock=time.monotonic):
        self.helper, self.clients, self.output, self.clock = helper, clients, output, clock
        self.base = helper.Scope(clients, output, schedule, clock)
        self.started, self.calls, self.armed = clock(), 0, False
        self.control, self.s3 = CONTROL_CONSUMED, S3_CONSUMED
        self.absent_instance_queries = set()

    def allowed(self, service, method, args):
        if service == "ec2" and method == "describe_instances":
            require(args in (EXACT_INSTANCE, TAG_INSTANCE, TOKEN_INSTANCE), "INSTANCE_QUERY_SCOPE")
        elif service == "iam" and method in ("list_role_policies", "list_attached_role_policies",
                                               "list_instance_profiles_for_role", "get_role_policy"):
            expected = {"RoleName": args.get("RoleName")}
            require(expected["RoleName"] in (WORKER, TIMER), "ROLE_SCOPE")
            if method == "get_role_policy":
                expected["PolicyName"] = "job-only"
            require(args == expected, "ROLE_QUERY_SCOPE")
        else:
            self.base.armed = self.armed
            self.base.allowed(service, method, args)

    def validate(self, service, method, args, value):
        require(isinstance(value, dict), "SDK_RESPONSE_TYPE")
        require(not any(value.get(key) for key in ("NextToken", "NextMarker", "Marker", "IsTruncated",
                                                   "NextContinuationToken")), "PAGINATED_RESPONSE")
        if method == "describe_instances":
            require(value.get("Reservations") == [], "INSTANCE_QUERY_NOT_EMPTY")
            self.absent_instance_queries.add(json.dumps(args, sort_keys=True))
        elif method == "list_role_policies":
            names = value.get("PolicyNames")
            require(names in ([], ["job-only"]), "UNRELATED_INLINE_POLICY")
        elif method == "list_attached_role_policies":
            require(value.get("AttachedPolicies") == [], "ATTACHED_POLICIES_REMAIN")
        elif method == "list_instance_profiles_for_role":
            rows = value.get("InstanceProfiles")
            require(isinstance(rows, list) and len(rows) <= (1 if args["RoleName"] == WORKER else 0),
                    "UNRELATED_PROFILE_ASSOCIATION")
            for row in rows:
                # IAM list responses may omit tags; the exact get-profile call
                # above separately proves ownership through its tags and ARN.
                require(row.get("InstanceProfileName") == WORKER
                        and row.get("Arn") == "arn:aws:iam::" + ACCOUNT + ":instance-profile/" + WORKER,
                        "UNRELATED_PROFILE_ASSOCIATION")
        elif method == "get_role_policy":
            require(value.get("RoleName") == args["RoleName"] and value.get("PolicyName") == "job-only"
                    and value.get("PolicyDocument") == policies()[args["RoleName"]], "INLINE_POLICY_IDENTITY")
        else:
            if method == "describe_security_groups":
                require(isinstance(value.get("SecurityGroups"), list), "GROUP_LIST_MISSING")
            elif method == "get_instance_profile":
                require(isinstance(value.get("InstanceProfile", {}).get("Roles"), list), "PROFILE_ROLES_MISSING")
            elif method == "list_objects_v2":
                require(value.get("IsTruncated") is False, "OBJECT_PAGINATION_UNDECLARED")
            self.base.validate(service, method, args, value)

    def call(self, service, method, args):
        self.allowed(service, method, args)
        require(self.calls < MAX_CALLS and self.clock() - self.started < MAX_SECONDS,
                "RECOVERY_CALL_OR_TIME_BOUND")
        self.calls += 1
        if service == "s3": self.s3 += 1
        else: self.control += 1
        stem = "%03d_%s_%s" % (self.calls, service, method)
        self.helper.write(self.output / (stem + "_intent.json"),
                          {"service": service, "method": method, "arguments": args})
        try:
            value = getattr(self.clients[service], method)(**args)
        except Exception as error:
            response = getattr(error, "response", {})
            self.helper.write(self.output / (stem + "_error.json"), {
                "type": type(error).__name__, "code": response.get("Error", {}).get("Code"),
                "message": str(error)[:1000], "response": self.serializable(response)})
            code = response.get("Error", {}).get("Code")
            require(self.clock() - self.started < MAX_SECONDS, "RECOVERY_CALL_OR_TIME_BOUND")
            exact_missing = service == "ec2" and method == "describe_instances" and args == EXACT_INSTANCE
            control_missing = (service == "iam" and method in ("get_role", "get_instance_profile", "get_role_policy")
                               and code == "NoSuchEntity") or (service == "scheduler" and method == "get_schedule"
                               and code == "ResourceNotFoundException")
            if exact_missing and code == "InvalidInstanceID.NotFound":
                self.absent_instance_queries.add(json.dumps(args, sort_keys=True))
                return None
            if control_missing:
                return None
            raise
        self.helper.write(self.output / (stem + "_result.json"), {"response": self.serializable(value)})
        require(self.clock() - self.started < MAX_SECONDS, "RECOVERY_CALL_OR_TIME_BOUND")
        self.validate(service, method, args, value)
        return value

    @staticmethod
    def serializable(value):
        return json.loads(json.dumps(value, default=lambda x: x.isoformat() if isinstance(x, datetime) else str(x)))

    def compute_absence(self):
        for args in (EXACT_INSTANCE, TAG_INSTANCE, TOKEN_INSTANCE):
            self.call("ec2", "describe_instances", args)
        require(len(self.absent_instance_queries) == 3, "THREE_ABSENCE_QUERIES_REQUIRED")
        self.call("ec2", "describe_volumes", {"Filters": [{"Name": "tag:cas_meta_job", "Values": [JOB]}]})

    def results(self):
        self.call("s3", "list_objects_v2", {"Bucket": BUCKET})
        self.call("s3", "get_bucket_lifecycle_configuration", {"Bucket": BUCKET})

    def controls(self):
        observed = {
            "group": self.call("ec2", "describe_security_groups", {"Filters": [{"Name": "group-name", "Values": [JOB]}]}),
            "schedule": self.call("scheduler", "get_schedule", {"Name": JOB}),
            "profile": self.call("iam", "get_instance_profile", {"InstanceProfileName": WORKER}),
            "roles": {}, "policies": {},
        }
        for role in (WORKER, TIMER):
            value = self.call("iam", "get_role", {"RoleName": role})
            observed["roles"][role] = value
            if value is not None:
                names = self.call("iam", "list_role_policies", {"RoleName": role})["PolicyNames"]
                self.call("iam", "list_attached_role_policies", {"RoleName": role})
                self.call("iam", "list_instance_profiles_for_role", {"RoleName": role})
                if names:
                    require(self.call("iam", "get_role_policy", {"RoleName": role, "PolicyName": "job-only"})
                            is not None, "INLINE_POLICY_VANISHED_DURING_ADMISSION")
                observed["policies"][role] = names
        return observed

    def cleanup(self, observed):
        if observed["schedule"] is not None:
            self.call("scheduler", "delete_schedule", {"Name": JOB})
        require(self.call("scheduler", "get_schedule", {"Name": JOB}) is None, "SCHEDULE_REMOVAL_UNCONFIRMED")
        if observed["profile"] is not None:
            if observed["profile"]["InstanceProfile"].get("Roles"):
                self.call("iam", "remove_role_from_instance_profile", {"InstanceProfileName": WORKER, "RoleName": WORKER})
                value = self.call("iam", "get_instance_profile", {"InstanceProfileName": WORKER})
                require(value is not None and value["InstanceProfile"].get("Roles") == [], "PROFILE_DETACH_UNCONFIRMED")
            self.call("iam", "delete_instance_profile", {"InstanceProfileName": WORKER})
        require(self.call("iam", "get_instance_profile", {"InstanceProfileName": WORKER}) is None, "PROFILE_REMOVAL_UNCONFIRMED")
        for role in (WORKER, TIMER):
            if observed["roles"][role] is not None:
                if observed["policies"][role]:
                    self.call("iam", "delete_role_policy", {"RoleName": role, "PolicyName": "job-only"})
                    require(self.call("iam", "get_role_policy", {"RoleName": role, "PolicyName": "job-only"}) is None,
                            "POLICY_REMOVAL_UNCONFIRMED")
                require(self.call("iam", "list_role_policies", {"RoleName": role})["PolicyNames"] == [], "INLINE_POLICY_REMAINING")
                self.call("iam", "list_attached_role_policies", {"RoleName": role})
                require(self.call("iam", "list_instance_profiles_for_role", {"RoleName": role})["InstanceProfiles"] == [],
                        "ROLE_PROFILE_REMAINING")
                self.call("iam", "delete_role", {"RoleName": role})
            require(self.call("iam", "get_role", {"RoleName": role}) is None, "ROLE_REMOVAL_UNCONFIRMED")
        if observed["group"]["SecurityGroups"]:
            self.call("ec2", "delete_security_group", {"GroupId": GROUP})
        require(self.call("ec2", "describe_security_groups", {"Filters": [{"Name": "group-name", "Values": [JOB]}]})
                ["SecurityGroups"] == [], "GROUP_REMOVAL_UNCONFIRMED")


def recover(output, *, clients=None, profile="default", clock=time.monotonic):
    helper = load_helper()
    output = helper.safe(output)
    require(output == helper.safe(DESTINATION) and not output.exists(), "EXACT_FRESH_DESTINATION")
    documents = inputs(helper)
    context = deepcopy(documents["intent.json"])
    check_sources(helper, context)
    ledger_before = helper.ledger_hash(context["ledger_path"])
    require(ledger_before == json.loads(helper.read(PREVIOUS / "intent.json"))["ledger_sha256_before"], "PRIOR_LEDGER_DRIFT")
    if clients is None:
        require(all(find_spec(name) is not None for name in ("boto3", "botocore")), "SDK_UNAVAILABLE_NO_OUTPUT_CONSUMED")
    self_pin = sha256(helper.read(__file__)).hexdigest()
    output.mkdir()
    environment = helper.environment_identity(output, profile, clients is not None)
    environment.update(tool_path=str(Path(__file__).resolve()), tool_sha256=self_pin)
    environment["absolute_cli_equivalent"][1] = str(Path(__file__).resolve())
    helper.write(output / "intent.json", {"job": JOB, "request_sha256": helper.REQUEST_SHA,
        "resources": helper.RESOURCES, "previous_sha256": PREVIOUS_PINS, "helper_sha256": HELPER_SHA,
        "original_sha256": helper.PINS, "ledger_sha256_before": ledger_before, "environment": environment,
        "counters_before": {"control": CONTROL_CONSUMED, "s3": S3_CONSUMED, "downloaded_bytes": DOWNLOADED},
        "boundary": BOUNDARY})
    result = {"schema": "cas-teaching-continuation001-absent-cleanup/1", "job": JOB,
        "run_id": helper.LOGICAL_RUN, "request_sha256": helper.REQUEST_SHA, "status": "BLOCKED",
        "compute_state": "UNCONFIRMED", "fresh_termination_receipt": False, "boundary": BOUNDARY,
        "cloud_copy_retained": False, "results_deleted": False, "bucket_deleted": False,
        "ledger_unchanged": False, "original_and_previous_unchanged": False, "sources_unchanged": False,
        "original_parent_result_unchanged": False, "provider_sources_unchanged": False,
        "prior_recovery_unchanged": False, "cleanup": None}
    scope = None
    try:
        scope = Scope(helper, clients if clients is not None else helper.clients_for(profile), output,
                      documents["teaching_provider_0045.json"]["schedule"], clock)
        scope.call("sts", "get_caller_identity", {})
        scope.compute_absence()
        observed = scope.controls()
        scope.results()
        inputs(helper)
        check_sources(helper, context)
        require(helper.ledger_hash(context["ledger_path"]) == ledger_before, "LEDGER_CHANGED_BEFORE_CLEANUP")
        require(sha256(helper.read(__file__)).hexdigest() == self_pin, "SELF_SOURCE_CHANGED")
        scope.results()  # Repeat object identities immediately before mutation.
        helper.write(output / "admission.json", {"all_read_only_gates_passed": True, "compute_state": COMPUTE_STATE,
            "tagged_volumes_absent": True, "observed_controls": scope.serializable(observed),
            "result_inventory": scope.base.inventory, "control_attempts": scope.control, "s3_attempts": scope.s3})
        result["compute_state"] = COMPUTE_STATE
        result["cleanup"] = {"complete": False, "compute_closed": True, "instance_state": COMPUTE_STATE,
            "instance_terminated": False, "tagged_volumes_absent": True, "cloud_copy_retained": False,
            "results_deleted": False, "bucket_deleted": False}
        scope.armed = True
        scope.cleanup(observed)
        result["compute_state"] = "UNCONFIRMED"
        result["cleanup"].update(compute_closed=False, instance_state="UNCONFIRMED")
        scope.compute_absence()
        result["compute_state"] = COMPUTE_STATE
        result["cleanup"].update(compute_closed=True, instance_state=COMPUTE_STATE)
        scope.results()
        result.update(status="CLEANUP_CLOSED_RESULTS_RETAINED", cloud_copy_retained=True,
                      retained_inventory=scope.base.inventory, retention_policy_days=7,
                      retention_policy_is_exact_deletion_deadline=False)
        result["cleanup"].update(complete=True, cloud_copy_retained=True,
            schedules_removed=True, instance_profile_removed=True, roles_removed=True, security_group_removed=True)
    except Exception as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)[:1500]}
    finally:
        try:
            inputs(helper)
            result["original_and_previous_unchanged"] = True
            result["original_parent_result_unchanged"] = True
            result["prior_recovery_unchanged"] = True
            result["ledger_unchanged"] = helper.ledger_hash(context["ledger_path"]) == ledger_before
            require(result["ledger_unchanged"], "LEDGER_CHANGED_AFTER_CLEANUP")
            check_sources(helper, context)
            require(sha256(helper.read(__file__)).hexdigest() == self_pin, "SELF_SOURCE_CHANGED")
            result["sources_unchanged"] = True
            result["provider_sources_unchanged"] = True
        except Exception as error:
            result["status"] = "BLOCKED"
            result["postcheck_failure"] = str(error)[:1500]
        result["counters_after"] = {"control": scope.control if scope else CONTROL_CONSUMED,
            "s3": scope.s3 if scope else S3_CONSUMED, "downloaded_bytes": DOWNLOADED,
            "recovery_sdk_calls": scope.calls if scope else 0}
        result["mutations_admitted"] = scope.armed if scope else False
        helper.write(output / "result.json", result)
    return result


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    result = recover(args.output, profile=args.profile)
    print(json.dumps({"status": result["status"], "compute_state": result["compute_state"], "job": JOB}))
    return 0 if result["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
