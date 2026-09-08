"""Teaching-only AWS adapter. Importing this module makes no provider call.

The parent owns authority checks and independently checks all returned bytes.
Only generic, corrected transport helpers are reused from v9; none of its
reservation, authority, bootstrap, launch, wait or collection paths are called.
Results are streamed and the cloud result copy keeps its seven-day expiration
policy even after local verification. Expiration is not an hour-168 guarantee.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
import time

from aws import budget
from aws import condition_skill_v9_provider as generic
from aws import teaching_cycle_bootstrap as bootstrap
from aws import teaching_cycle_plan as plan
from aws import teaching_cycle_preflight as checks

ROOT = Path(__file__).resolve().parents[1]
JSON_BOUND = 32 * 1024**2
CHUNK = 1024**2
CONFIG_SCHEMA = "cas-teaching-guest-config/1"
PERMIT_SCHEMA = "cas-teaching-guest-permit/1"
DEPENDENCIES = (
    "aws/__init__.py", "cas_meta2/__init__.py", "cas_meta2/teaching_cycle/__init__.py",
    "cas_meta2/codec.py", "cas_meta2/features_v2.py", "cas_meta2/teaching_cycle/lesson_contract.py",
    "cas_meta2/teaching_cycle/worker_contract.py",
    "aws/budget.py", "aws/condition_skill_v9_provider.py", "aws/condition_skill_v9_launch.py",
    "aws/condition_skill_v9_resource_plan.py", "aws/condition_skill_v9_remote.py",
    "aws/condition_skill_v9_package.py", "aws/teaching_cycle_plan.py",
    "aws/teaching_cycle_launch.py", "aws/teaching_cycle_preflight.py",
    "aws/teaching_cycle_bootstrap.py", "aws/teaching_cycle_provider.py",
    "aws/teaching_cycle_remote.py", "cas_meta2/teaching_cycle/evaluation.py",
    "tools/prepare_teaching_launch.py", "tools/run_teaching_launch.py", "tools/evaluate_teaching_launch.py",
)


def require(condition, code):
    if not condition:
        raise ValueError("TEACHING_PROVIDER:" + code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def safe_path(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "LINKED_PATH")
    return path


def local_bytes(path, maximum=JSON_BOUND):
    path = safe_path(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= maximum,
            "LOCAL_FILE_TYPE_OR_BOUND")
    raw = path.read_bytes()
    require(len(raw) == info.st_size, "LOCAL_FILE_CHANGED")
    return raw


def write_bytes(path, raw):
    path = safe_path(path)
    require(type(raw) is bytes and 0 < len(raw) <= JSON_BOUND, "EVIDENCE_BOUND")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(local_bytes(path) == raw, "EVIDENCE_READBACK")
    return {"path": str(path), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


class _Evidence:
    evidence_directory = staticmethod(safe_path)
    write_evidence = staticmethod(write_bytes)


def source_dependencies():
    """Exact local source map, including imports of reused generic helpers."""
    return {name: sha256(local_bytes(ROOT / name)).hexdigest() for name in DEPENDENCIES}


def normalize_hourly_rate(raw, ceiling):
    """Remove insignificant zeroes only; never round a quote into acceptance."""
    require(type(raw) is str and 0 < len(raw) <= 64 and re.fullmatch(r"\d+(?:\.\d+)?", raw), "HOURLY_RATE_FORMAT")
    value = Decimal(raw)
    require(value.is_finite() and value > 0, "HOURLY_RATE_INVALID")
    require(value <= Decimal(ceiling), "HOURLY_RATE_ABOVE_CEILING")
    exact = raw.rstrip("0").rstrip(".") if "." in raw else raw
    require(re.fullmatch(r"\d+(?:\.\d{1,8})?", exact), "HOURLY_RATE_EXACT_PRECISION_UNSUPPORTED")
    return exact


def validate_first_update(envelope, context):
    """Admit a worker report, never independent GPU identity or learning proof."""
    from aws.teaching_cycle_launch import envelope_document
    document = envelope_document(envelope, key="results/first_update.json", maximum=1048576)
    expected = {"schema": "cas-teaching-first-update/1", "job": context["job"], "run_id": context["run_id"],
        "source_sha256": context["bindings"]["source_sha256"], "manifest_sha256": context["bindings"]["manifest_sha256"],
        "material_sha256": context["bindings"]["material_receipt_sha256"], "request_sha256": context["request_sha256"],
        "boundary": "WORKER_REPORTED_NOT_INDEPENDENT_LEARNING_PROOF"}
    require(type(document) is dict and set(document) == {*expected, "arm", "event"}
            and all(document.get(key) == value for key, value in expected.items()), "FIRST_UPDATE_IDENTITY")
    arm = document["arm"]
    require(type(arm) is str and arm in context["resource_plan"]["arms"], "FIRST_UPDATE_ARM")
    event = document["event"]
    require(type(event) is dict and set(event) == {"key", "raw_utf8", "sha256", "bytes"}, "FIRST_UPDATE_EVENT_ENVELOPE")
    payload = envelope_document(event, key="train/campaign/" + arm + "/events/step-00000001.result.json", maximum=1048576)
    require(type(payload) is dict and set(payload) == {"sequence", "intent_sha256", "receipt"}
            and type(payload["sequence"]) is int and payload["sequence"] == 1
            and type(payload["intent_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", payload["intent_sha256"])
            and payload["intent_sha256"] != "0" * 64, "FIRST_UPDATE_EVENT")
    family, curriculum = arm.split(".")
    receipt = payload["receipt"]
    require(type(receipt) is dict and receipt.get("schema") == "cas-teaching-binding-cuda/1"
            and receipt.get("run_id") == context["job"] + "." + curriculum + "." + family
            and receipt.get("execution_mode") == "cuda" and receipt.get("accepted_weights_updated") is False
            and type(receipt.get("optimizer_steps")) is int and receipt["optimizer_steps"] == 1
            and type(receipt.get("cumulative_optimizer_steps")) is int and receipt["cumulative_optimizer_steps"] >= 1,
            "FIRST_UPDATE_OPTIMIZER_RECEIPT")
    return {"arm": arm, "event_sha256": event["sha256"], "cumulative_optimizer_steps": receipt["cumulative_optimizer_steps"]}


def build_clients(profile="default"):
    """Explicit live factory only; SDK retries are disabled, including S3."""
    import boto3
    from botocore.config import Config
    config = Config(connect_timeout=5, read_timeout=10, retries={"total_max_attempts": 1})
    session = boto3.Session(profile_name=profile, region_name=checks.REGION)
    result = {name: session.client(name, config=config) for name in
              ("sts", "ec2", "service-quotas", "iam", "scheduler", "s3")}
    result["pricing"] = session.client("pricing", region_name="us-east-1", config=config)
    return result


class _CountedClient:
    def __init__(self, provider, name, client):
        self.provider, self.name, self.client = provider, name, client

    def __getattr__(self, method):
        callback = getattr(self.client, method)

        def call(**kwargs):
            owner = self.provider
            if not owner._cleaning:
                require(owner.now() < owner._context_value["deadline_unix"], "SHARED_DEADLINE")
            if self.name == "s3":
                # Reserve 32 of the same 1,024 attempts for cleanup observations.
                bound = 1024 if owner._cleaning else 992
                require(owner.s3_attempts < bound, "PARENT_S3_ATTEMPT_LIMIT")
                owner.s3_attempts += 1  # Failed calls count too; never reset.
            else:
                owner.control_attempts += 1
            return callback(**kwargs)
        return call


class TeachingCycleProvider(generic.ConditionSkillV9Provider):
    def __init__(self, *, clients, source_archive, guest_driver, pricing_receipt_path,
                 ledger_path, clock=time.time, sleeper=time.sleep, budget_module=budget,
                 client_error=None, observer=checks.observe, monotonic_clock=time.monotonic):
        self.raw_clients = clients
        self.source_archive_path, self.guest_driver_path = source_archive, guest_driver
        self.pricing_receipt_path, self.teaching_ledger_path = pricing_receipt_path, ledger_path
        self.now, self.sleep, self.observer = clock, sleeper, observer
        self.monotonic = monotonic_clock
        # All AWS errors carry a code; generic helpers rethrow unknown errors.
        # Exception keeps pure imports independent of the lazy botocore SDK.
        self.teaching_budget, self.teaching_error = budget_module, client_error or Exception
        self._context_value = None
        self._cleaning = False
        self._reservation_attempted = False
        self._collection_attempted = False
        self._public_released = False
        self.s3_attempts = self.control_attempts = 0
        self.result_downloaded_bytes = 0
        self._first_update_finished = False
        self._first_update_next_poll = 0.0

    def _context(self, context):
        require(type(context) is dict, "CONTEXT_REQUIRED")
        request = context["request"]
        plan.validate_request(request, expected_bindings=context["bindings"], expected_ledger=request["ledger"])
        require(context["job"] == request["job"] == context["run_id"]
                and context["request_sha256"] == plan.canonical_sha256(request)
                and plan.canonical_sha256(context["resource_plan"]) == request["resource_plan_sha256"], "CONTEXT_IDENTITY")
        require(type(context["started_unix"]) in (int, float) and type(context["deadline_unix"]) in (int, float)
                and 0 < context["deadline_unix"] - context["started_unix"] <= 7200, "LIFETIME_BOUND")
        require(Path(context["ledger_path"]).absolute() == Path(self.teaching_ledger_path).absolute(), "LEDGER_PATH")
        if self._context_value is None:
            super().__init__(job=context["job"], source_sha=context["bindings"]["source_commit"],
                archive_sha256=context["bindings"]["archive_sha256"], manifest_sha256=context["bindings"]["manifest_sha256"],
                dataset_manifest_sha256=context["bindings"]["training_cases_sha256"],
                ledger_path=self.teaching_ledger_path, clients={}, source_archive=self.source_archive_path,
                client_error=self.teaching_error, budget_module=self.teaching_budget, launch_module=_Evidence)
            self.clients = {name: _CountedClient(self, name, client) for name, client in self.raw_clients.items()}
            self._evidence = safe_path(context["receipt_dir"])
            require(self._evidence.is_dir(), "EVIDENCE_DIRECTORY_REQUIRED")
            self._context_value = deepcopy(context)
        else:
            require(context["request_sha256"] == self._context_value["request_sha256"]
                    and context["started_unix"] == self._context_value["started_unix"]
                    and context["deadline_unix"] == self._context_value["deadline_unix"], "CONTEXT_CHANGED")
        return context["resource_plan"]

    def _event(self, operation, state, **details):
        self._event_number += 1
        return write_bytes(self._evidence / ("teaching_provider_%04d.json" % self._event_number), canonical({
            "schema": "cas-teaching-provider-event/2", "job": self.job,
            "request_sha256": self._context_value["request_sha256"], "operation": operation, "state": state,
            "observed_unix": self.now(), "resources": dict(self._resources),
            "s3_attempts": self.s3_attempts, "control_attempts_observed": self.control_attempts,
            "result_downloaded_bytes": self.result_downloaded_bytes, **details}))

    def _check_pins(self, context):
        pins = context["bindings"]
        require(sha256(local_bytes(__file__)).hexdigest() == pins["provider_source_sha256"], "PROVIDER_SOURCE_PIN")
        require(plan.canonical_sha256(source_dependencies()) == pins["provider_dependencies_sha256"], "PROVIDER_DEPENDENCIES_PIN")
        for path, key in ((self.guest_driver_path, "guest_driver_sha256"),
                          (bootstrap.__file__, "bootstrap_sha256"), (self.pricing_receipt_path, "pricing_receipt_sha256")):
            require(sha256(local_bytes(path)).hexdigest() == pins[key], "SOURCE_PIN:" + key)
        require(sha256(local_bytes(self.source_archive_path, 33554432)).hexdigest() == pins["archive_sha256"], "ARCHIVE_PIN")

    def preflight(self, context):
        self._context(context)
        self._check_pins(context)  # No AWS before all local identities match.
        facts = self.observer(self.clients)
        raw_rate = facts["cost_worksheet"]["rates_usd"]["compute"]
        exact_rate = normalize_hourly_rate(raw_rate, context["resource_plan"]["on_demand_hourly_usd_max"])
        self._preflight_passed = True
        return {**facts, "instance_count": 1, "t4_rejected": True,
            "rate_hourly_usd": exact_rate, "rate_hourly_usd_raw": raw_rate,
            "rate_normalization": "INSIGNIFICANT_TRAILING_ZERO_REMOVAL_ONLY_NO_ROUNDING",
            "pricing_receipt_sha256": context["bindings"]["pricing_receipt_sha256"],
            "shutdown_capability_verified": False, "shutdown_verification_stage": "BEFORE_WORKER_RELEASE",
            "pinned_pricing_and_fresh_observation_are_distinct": True}

    def reservation_plan(self):
        return plan.resource_plan()

    def reserve(self, context):
        self._context(context)
        require(getattr(self, "_preflight_passed", False), "PREFLIGHT_REQUIRED")
        require(not self._reservation_attempted, "ONE_RESERVATION_ATTEMPT_ONLY")
        require(self.now() < context["deadline_unix"], "RESERVATION_DEADLINE")
        self._reservation_attempted = True
        self._event("budget_reservation", "REQUESTED", amount="8.00")
        receipt = self.budget.reserve_budget(self.job, self.source_sha, self.archive_sha256,
                                             "8.00", plan.resource_plan(), self.ledger_path)
        self._reserved = True
        cloud_receipt = self._record_aws_side_reservation(receipt)
        self._reservation_cloud_recorded = cloud_receipt.get("status") == "RECORDED"
        return {**receipt, "aws_side_reservation": cloud_receipt}

    def _bucket_name(self):
        return self.job + "-" + checks.ACCOUNT

    def _ensure_bucket(self, s3, tags=None):
        first_attempt = "bucket" not in self._resources
        try:
            return super()._ensure_bucket(s3, tags)
        except Exception as error:
            if first_attempt and self._error_code(error) in ("BucketAlreadyExists", "BucketAlreadyOwnedByYou"):
                # An explicit collision is not ownership, even in this account.
                self._resources.pop("bucket", None)
                self._bucket_ready = False
                self._event("bucket_collision", "REFUSED_WITHOUT_OWNERSHIP")
            raise

    def _config(self, context):
        return {"schema": CONFIG_SCHEMA, "job": self.job, "run_id": self.job,
            "request_sha256": context["request_sha256"], "resource_plan_sha256": context["request"]["resource_plan_sha256"],
            "bindings": context["bindings"], "resource_plan": context["resource_plan"],
            "bucket": self._bucket_name(), "prefix": "",
            "launch_started_unix": int(context["started_unix"]), "deadline_unix": int(context["deadline_unix"])}

    def _wait_for_iam(self, worker, timer, worker_arn, timer_arn, profile_arn):
        first = super()._wait_for_iam(worker, timer, worker_arn, timer_arn, profile_arn)
        started, started_unix = self.monotonic(), self.now()
        require(type(started) in (int, float) and math.isfinite(started), "IAM_SETTLE_CLOCK")
        deadline = self._context_value["deadline_unix"]
        self._event("iam_settling", "STARTED", required_seconds=120, first_readback=first,
                    ec2_propagation_proved=False)
        while True:
            elapsed = self.monotonic() - started
            require(math.isfinite(elapsed) and elapsed >= 0, "IAM_SETTLE_CLOCK")
            require(self.now() < deadline, "IAM_SETTLE_SHARED_DEADLINE")
            remaining = 120 - elapsed
            if remaining <= 0:
                break
            require(deadline - self.now() > remaining, "IAM_SETTLE_SHARED_DEADLINE")
            self.sleep(min(30, remaining))
        iam = self.clients["iam"]
        roles = [iam.get_role(RoleName=name)["Role"] for name in (worker, timer)]
        profile = iam.get_instance_profile(InstanceProfileName=worker)["InstanceProfile"]
        attached = [role.get("Arn") for role in profile.get("Roles", [])]
        require([role.get("Arn") for role in roles] == [worker_arn, timer_arn]
                and profile.get("Arn") == profile_arn and attached == [worker_arn], "IAM_SETTLE_FINAL_IDENTITY")
        receipt = {**first, "settling_seconds_required": 120, "settling_elapsed_seconds": self.monotonic() - started,
            "settling_started_unix": started_unix, "settling_finished_unix": self.now(),
            "final_profile_arn": profile["Arn"], "final_attached_role_arns": attached,
            "final_role_arns": [role["Arn"] for role in roles], "ec2_propagation_proved": False}
        self._event("iam_settling", "DELAY_AND_FINAL_READBACK_COMPLETED", receipt=receipt)
        return receipt

    def launch(self, context):
        resource = self._context(context)
        require(self._reserved and not self._launch_called and getattr(self, "_reservation_cloud_recorded", False), "ONE_RESERVED_LAUNCH_ONLY")
        self._launch_called = True
        self._check_pins(context)
        ec2, s3, iam, scheduler = (self.clients[name] for name in ("ec2", "s3", "iam", "scheduler"))
        bucket = self._ensure_bucket(s3)
        tags = [{"Key": "cas_meta_job", "Value": self.job}]
        source = local_bytes(self.source_archive_path, resource["training_archive_bytes_max"])
        self._source_copy = write_bytes(self._evidence / "source.zip", source)
        driver = local_bytes(self.guest_driver_path)
        config_raw = canonical(self._config(context))
        config_sha = sha256(config_raw).hexdigest()
        write_bytes(self._evidence / "guest_config.json", config_raw)
        for key, raw in (("input/source.zip", source), ("input/remote.py", driver), ("input/config.json", config_raw)):
            self._effect("upload_input", s3.put_object, Bucket=bucket, Key=key, Body=raw)

        def role(name, service, statements):
            self._resources[name.rsplit("-", 1)[-1] + "_role"] = name
            trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}]}
            created = self._effect("create_role", iam.create_role, RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Tags=tags)
            arn = created.get("Role", {}).get("Arn")
            require(arn == "arn:aws:iam::" + checks.ACCOUNT + ":role/" + name, "ROLE_ARN")
            self._effect("put_role_policy", iam.put_role_policy, RoleName=name, PolicyName="job-only",
                         PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}))
            return arn

        worker, timer = self.job + "-worker", self.job + "-timer"
        worker_arn = role(worker, "ec2.amazonaws.com", [
            # S3 needs this exact-bucket permission to distinguish a missing
            # public-release key (404) from denied access (403) during polling.
            {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": ["arn:aws:s3:::" + bucket]},
            {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::" + bucket + "/input/" + name
                for name in ("source.zip", "remote.py", "config.json", "permit.json", "public.json", "public_release.json")]},
            {"Effect": "Allow", "Action": ["s3:PutObject"], "Resource": ["arn:aws:s3:::" + bucket + "/results/*"]}])
        self._resources["instance_profile"] = worker
        profile = self._effect("create_instance_profile", iam.create_instance_profile, InstanceProfileName=worker, Tags=tags)["InstanceProfile"]
        profile_arn = profile.get("Arn")
        require(profile_arn == "arn:aws:iam::" + checks.ACCOUNT + ":instance-profile/" + worker, "PROFILE_ARN")
        self._effect("attach_profile", iam.add_role_to_instance_profile, InstanceProfileName=worker, RoleName=worker)
        timer_arn = role(timer, "scheduler.amazonaws.com", [{"Effect": "Allow", "Action": "ec2:TerminateInstances",
            "Resource": "arn:aws:ec2:" + checks.REGION + ":" + checks.ACCOUNT + ":instance/*",
            "Condition": {"StringEquals": {"ec2:ResourceTag/cas_meta_job": self.job}}}])
        iam_readback = self._wait_for_iam(worker, timer, worker_arn, timer_arn, profile_arn)
        vpc, subnet = self._default_network(ec2)
        group = self._effect("create_security_group", ec2.create_security_group, GroupName=self.job,
            Description="CAS teaching HTTPS only", VpcId=vpc, TagSpecifications=[{"ResourceType": "security-group", "Tags": tags}])
        sg = self._resources["security_group"] = group["GroupId"]
        self._effect("remove_default_egress", ec2.revoke_security_group_egress, GroupId=sg,
                     IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        self._effect("allow_https", ec2.authorize_security_group_egress, GroupId=sg,
                     IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        deadline = int(context["deadline_unix"])
        userdata = bootstrap.render_bootstrap(bucket=bucket, job=self.job, source_sha256=self.archive_sha256,
            driver_sha256=context["bindings"]["guest_driver_sha256"], config_sha256=config_sha, deadline_unix=deadline)
        self._launch_attempted, self._run_state = True, "REQUESTED_UNKNOWN"
        try:
            response = self._effect("run_instances", ec2.run_instances, ImageId=checks.AMI, InstanceType=checks.INSTANCE,
                MinCount=1, MaxCount=1, ClientToken=self.job, IamInstanceProfile={"Arn": profile_arn},
                InstanceInitiatedShutdownBehavior="terminate", MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
                NetworkInterfaces=[{"DeviceIndex": 0, "SubnetId": subnet, "Groups": [sg], "AssociatePublicIpAddress": True, "DeleteOnTermination": True}],
                BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 75, "VolumeType": "gp3", "Iops": 3000,
                    "Throughput": 125, "Encrypted": True, "DeleteOnTermination": True}}],
                TagSpecifications=[{"ResourceType": kind, "Tags": tags} for kind in ("instance", "volume")], UserData=userdata)
        except BaseException as error:
            if self._error_code(error) in ("InvalidParameterValue", "InvalidParameterCombination", "UnauthorizedOperation",
                    "AuthFailure", "InsufficientInstanceCapacity", "InstanceLimitExceeded", "Unsupported"):
                self._run_state = "REJECTED"
            try:
                self._discover_instances()
            except Exception as discovery_error:
                self._event("instance_discovery", "FAILED", error=type(discovery_error).__name__)
            raise
        require(len(response.get("Instances", [])) == 1, "ONE_INSTANCE_RESPONSE")
        self._instance_id = response["Instances"][0]["InstanceId"]
        require(type(self._instance_id) is str and re.fullmatch(r"i-[0-9a-f]{17}", self._instance_id), "INSTANCE_ID")
        self._instance_ids, self._run_state = [self._instance_id], "INSTANCE_OBSERVED"
        self._resources["instance"] = self._instance_id
        target = {"Arn": "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances", "RoleArn": timer_arn,
            "Input": json.dumps({"InstanceIds": [self._instance_id]}), "RetryPolicy": {"MaximumRetryAttempts": 0, "MaximumEventAgeInSeconds": 60}}
        expression = "at(" + datetime.fromtimestamp(deadline, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + ")"
        self._resources["schedule"] = self.job
        self._effect("create_shutdown_schedule", scheduler.create_schedule, Name=self.job, ScheduleExpression=expression,
            ScheduleExpressionTimezone="UTC", FlexibleTimeWindow={"Mode": "OFF"}, Target=target, ActionAfterCompletion="DELETE")
        observed = scheduler.get_schedule(Name=self.job)
        expected = {"Arn": "arn:aws:scheduler:" + checks.REGION + ":" + checks.ACCOUNT + ":schedule/default/" + self.job,
            "State": "ENABLED", "Target": target, "ScheduleExpression": expression, "ScheduleExpressionTimezone": "UTC",
            "FlexibleTimeWindow": {"Mode": "OFF"}, "ActionAfterCompletion": "DELETE"}
        require(all(observed.get(key) == value for key, value in expected.items()) and self.now() < deadline, "SCHEDULE_READBACK")
        schedule_receipt = self._event("shutdown_schedule", "CONFIRMED", schedule=expected)
        permit = {"schema": PERMIT_SCHEMA, "job": self.job, "run_id": self.job, "config_sha256": config_sha,
            "request_sha256": context["request_sha256"], "instance_id": self._instance_id, "deadline_unix": deadline,
            "shutdown_schedule_arn": expected["Arn"], "shutdown_schedule_confirmed": True, "automatic_retries": 0}
        self._effect("release_worker_after_verified_shutdown", s3.put_object, Bucket=bucket, Key="input/permit.json", Body=canonical(permit))
        return {"job": self.job, "instance_id": self._instance_id, "instance_type": checks.INSTANCE, "instance_count": 1,
            "bucket": bucket, "iam_readback": iam_readback, "config_sha256": config_sha,
            "shutdown_gate": {"verified": True, "instance_id": self._instance_id, "deadline_unix": deadline,
                "receipt_sha256": schedule_receipt["sha256"], "worker_released_after_verification": True}}

    def _object_bytes(self, key, maximum=JSON_BOUND):
        try:
            response = self.clients["s3"].get_object(Bucket=self._bucket_name(), Key=key)
        except self._client_error as error:
            if self._error_code(error) in ("NoSuchKey", "404", "NotFound"):
                return None
            raise
        body, size = response["Body"], response.get("ContentLength")
        try:
            require(type(size) is int and 0 < size <= maximum, "S3_OBJECT_SIZE")
            require(self.result_downloaded_bytes + size <= 2684354560, "SHARED_RESULT_DOWNLOAD_BOUND")
            raw = body.read(size + 1)
            self.result_downloaded_bytes += len(raw)
            require(type(raw) is bytes and len(raw) == size, "S3_OBJECT_TRUNCATED_OR_OVERSIZED")
        finally:
            body.close()
        return raw

    def _get(self, key, maximum=JSON_BOUND):
        raw = self._object_bytes(key, maximum)
        if raw is None:
            return None
        from aws.teaching_cycle_launch import envelope_document
        envelope = {"raw_utf8": raw.decode("utf-8"), "sha256": sha256(raw).hexdigest(), "bytes": len(raw), "key": key}
        envelope_document(envelope, key=key, maximum=maximum)
        return envelope

    def _observe_first_update(self):
        if self._first_update_finished or self.now() < self._first_update_next_poll:
            return
        self._first_update_next_poll = self.now() + 60
        try:
            envelope = self._get("results/first_update.json", 1048576)
            if envelope is None:
                return
            self._first_update_finished = True
            local = write_bytes(self._evidence / "first_update.json", envelope["raw_utf8"].encode("utf-8"))
            report = validate_first_update(envelope, self._context_value)
        except Exception as error:
            # Optional progress is not a new training/selection/release gate.
            # Ordinary lifecycle reads still enforce the same shared limits.
            self._first_update_finished = True
            self._event("first_cuda_update_marker", "UNAVAILABLE_OR_REJECTED", exception_type=type(error).__name__)
            return
        self._event("first_cuda_update_marker", "WORKER_REPORTED", marker=local, **report,
                    independent_learning_proof=False)
        print(json.dumps({"status": "WORKER_REPORTED_FIRST_CUDA_UPDATE", "job": self.job,
            **report, "independent_learning_proof": False}, sort_keys=True), flush=True)

    def _poll(self, key, timeout):
        stop = min(self.now() + timeout, self._context_value["deadline_unix"] - 60)
        while self.now() < stop:
            if key == "results/train_ready.json":
                self._observe_first_update()
            result = self._get(key)
            if result is not None:
                return result
            complete = self._get("results/complete.json") if key != "results/complete.json" else None
            if complete is not None:
                return complete
            if self._instance_id is not None:
                observed = self.clients["ec2"].describe_instances(InstanceIds=[self._instance_id])
                instances = [item for group in observed.get("Reservations", []) for item in group.get("Instances", [])]
                require(len(instances) == 1 and instances[0].get("InstanceId") == self._instance_id
                    and instances[0].get("ClientToken") == self.job
                    and {tag["Key"]: tag["Value"] for tag in instances[0].get("Tags", [])}.get("cas_meta_job") == self.job,
                    "WAIT_INSTANCE_IDENTITY")
                state = instances[0].get("State", {}).get("Name")
                if state in ("shutting-down", "terminated", "stopping", "stopped"):
                    final = self._get("results/complete.json")
                    if final is not None:
                        return final
                    failure = self._object_bytes("results/bootstrap_failure.log", 1048576)
                    receipt = None if failure is None else write_bytes(self._evidence / "bootstrap_failure.log", failure)
                    self._event("guest_exit_without_complete", "OBSERVED", instance_state=state, bootstrap_failure=receipt)
                    raise RuntimeError("TEACHING_PROVIDER:GUEST_EXIT_WITHOUT_COMPLETE:" + str(state))
            self.sleep(min(20, max(0, stop - self.now())))
        raise TimeoutError("TEACHING_PROVIDER:WAIT_DEADLINE:" + key)

    def wait_training(self, context, timeout):
        self._context(context)
        ready = self._poll("results/train_ready.json", timeout)
        if ready["key"] == "results/complete.json":
            return {"complete": ready}
        campaign = self._get("results/train/campaign_summary.json")
        require(campaign is not None, "CAMPAIGN_MISSING_AFTER_SEAL")
        return {"ready": ready, "campaign": campaign}

    def release_public(self, context, release):
        self._context(context)
        require(not self._public_released and context.get("training_ready_sha256") and context.get("campaign_summary_sha256"), "ONE_SEALED_PUBLIC_RELEASE")
        raw = local_bytes(context["public_sets_path"], 1048576)
        require(sha256(raw).hexdigest() == context["bindings"]["public_sets_sha256"], "PUBLIC_INPUT_PIN")
        require(release.get("training_ready_sha256") == context["training_ready_sha256"]
                and release.get("job") == self.job and release.get("campaign_summary_sha256") == context["campaign_summary_sha256"], "PUBLIC_RELEASE_IDENTITY")
        self._public_released = True
        release_raw = canonical(release)
        for key, value in (("input/public.json", raw), ("input/public_release.json", release_raw)):
            self._effect("release_public", self.clients["s3"].put_object, Bucket=self._bucket_name(), Key=key, Body=value)
        return {"uploaded": True, "release_sha256": sha256(release_raw).hexdigest(), "public_sha256": sha256(raw).hexdigest()}

    def wait_prediction(self, context, run_index, timeout):
        self._context(context)
        require(type(run_index) is int and run_index in (1, 2) and self._public_released, "PREDICTION_PHASE")
        ready = self._poll("results/prediction%d_ready.json" % run_index, timeout)
        if ready["key"] == "results/complete.json":
            return {"complete": ready}
        seal = self._get("results/predict%d/prediction_seal.json" % run_index)
        require(seal is not None, "PREDICTION_SEAL_MISSING")
        return {"ready": ready, "seal": seal}

    def collect(self, context, destination, timeout):
        resource = self._context(context)
        require(not self._collection_attempted, "ONE_COLLECTION_ATTEMPT_ONLY")
        self._collection_attempted = True
        stop = min(self.now() + timeout, context["deadline_unix"])
        complete = self._poll("results/complete.json", timeout)
        document = json.loads(complete["raw_utf8"])
        artifact = document.get("artifact", {})
        require(set(artifact) == {"key", "sha256", "bytes"} and artifact.get("key") == "results/artifacts.zip"
                and type(artifact.get("bytes")) is int and 0 < artifact["bytes"] <= resource["artifact_download_bytes_max"]
                and type(artifact.get("sha256")) is str and re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]), "ARTIFACT_ENVELOPE")
        destination = safe_path(destination)
        require(destination.is_dir(), "COLLECTION_DIRECTORY")
        write_bytes(destination / "complete.json", complete["raw_utf8"].encode("utf-8"))
        path = destination / "artifacts.zip"
        require(self.result_downloaded_bytes + artifact["bytes"] <= resource["artifact_download_bytes_max"], "SHARED_RESULT_DOWNLOAD_BOUND")
        response = self.clients["s3"].get_object(Bucket=self._bucket_name(), Key=artifact["key"])
        body = response["Body"]
        try:
            require(type(response.get("ContentLength")) is int and response["ContentLength"] == artifact["bytes"], "ARTIFACT_CONTENT_LENGTH")
            digest, count = sha256(), 0
            with safe_path(path).open("xb") as stream:
                while True:
                    require(self.now() < stop, "COLLECTION_SHARED_DEADLINE")
                    chunk = body.read(min(CHUNK, artifact["bytes"] - count + 1))
                    if not chunk:
                        break
                    count += len(chunk)
                    self.result_downloaded_bytes += len(chunk)
                    require(count <= artifact["bytes"], "ARTIFACT_EXCESS_BYTES")
                    digest.update(chunk)
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            require(count == artifact["bytes"] and digest.hexdigest() == artifact["sha256"] and path.stat().st_nlink == 1,
                    "ARTIFACT_LOCAL_IDENTITY")
        finally:
            body.close()
        # Deliberately never enable generic cleanup's RAM-reading result branch.
        self._durable_results = False
        return {"complete": complete, "archive": {**artifact, "path": str(path)}}

    def cleanup(self, context, retain_cloud_copy):
        self._context(context)
        # Parent also calls cleanup for refusals before reserve. A job name is
        # not ownership: do not discover or remove another attempt's resources.
        if not self._resources and not self._launch_attempted:
            return {"complete": True, "compute_closed": True, "instance_state": "NOT_CREATED",
                "instance_terminated": False, "schedules_removed": True,
                "schedule_state": "NOT_CREATED_BY_THIS_ATTEMPT", "cleanup_scope": "CURRENT_ATTEMPT_ONLY_NO_EFFECTS",
                "cloud_copy_retained": False, "cloud_copy_state": "NOT_CREATED", "cloud_copy_deleted": False,
                "s3_attempts": self.s3_attempts, "result_downloaded_bytes": self.result_downloaded_bytes, "provider_cleanup_calls": 0}
        self._cleaning = True
        self._durable_results = False
        try:
            result = super().cleanup(self.job)
        finally:
            self._cleaning = False
        closed = result.get("compute_closed", result.get("instance_terminated", False))
        if not self._instance_ids and self._run_state in ("NOT_ATTEMPTED", "REJECTED"):
            closed = True
            state = "NOT_CREATED" if self._run_state == "NOT_ATTEMPTED" else "REJECTED_NO_INSTANCE_OBSERVED"
        else:
            state = "TERMINATED" if closed else "UNKNOWN"
        bucket_state = result.get("bucket_state")
        if bucket_state == "RETAINED_BOUNDED_EVIDENCE":
            retained = any(key.startswith("results/") for key in result.get("retained_keys", []))
            copy_state = "OBSERVED_RETAINED" if retained else "NO_RESULT_OBJECT_OBSERVED"
        elif bucket_state in ("NOT_CREATED", "CONFIRMED_ABSENT"):
            retained = False
            copy_state = "NOT_CREATED" if bucket_state == "NOT_CREATED" else "NO_RESULT_OBJECT_OBSERVED"
        else:
            retained, copy_state = None, "UNKNOWN_PRESERVED"
        return {**result, "compute_closed": closed, "instance_state": state,
            "schedules_removed": result.get("schedule_removed") is True,
            "cloud_copy_retained": retained, "cloud_copy_state": copy_state, "cloud_copy_deleted": False,
            "retention_policy_days": 7, "retention_policy_is_exact_deletion_deadline": False,
            "s3_attempts": self.s3_attempts, "result_downloaded_bytes": self.result_downloaded_bytes,
            "bootstrap_s3_attempts_allocated": 128, "guest_s3_attempts_allocated": 896}

    def _validate_permit(self, *args, **kwargs):
        raise ValueError("TEACHING_PROVIDER:LEGACY_LIFECYCLE_DISABLED")

    _source_bytes = _render_remote = _user_data = wait = _validate_permit
