"""One-shot supplemental cleanup for teaching continuation 001; never a workload launch.

Run only after review, with -B in an environment that can import boto3/botocore.
Do not require -I for the AWS runtime; it can hide user-site SDK installations.
Import is inert. The fixed destination prevents
replaying this tool with the old consumed-call counters. All S3 writes, launches,
termination requests, volume deletion and budget mutations are forbidden.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from importlib import metadata
from importlib.util import find_spec
import os
from pathlib import Path
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "records/teaching_cycle_001/continuation_001/launch"
DESTINATION = ORIGINAL.parent / "cleanup_recovery_001"
JOB = "cas-meta2-teaching-20260908080138-5518e287"
LOGICAL_RUN = "cas-meta2-teaching-20260908052915-8b5df59c"
ACCOUNT, REGION = "807562639912", "us-west-2"
INSTANCE, GROUP = "i-0c89cf580dd58a803", "sg-0b4587c7ff2d2b173"
BUCKET, WORKER, TIMER = JOB + "-" + ACCOUNT, JOB + "-worker", JOB + "-timer"
REQUEST_SHA = "af9117250d5e6400b981315e75e025b13c931d9be2a1adfb5b40b37591d30d97"
PINS = {
    "result.json": "ffb42912a72759a2c440571bcd929c397a8cc653b3d288d3a758221d52e4d86d",
    "intent.json": "4f612339c04fc3dcc0ccf8d3dc8fa932133c9609948cd3827259611f867a4220",
    "teaching_provider_0052.json": "e6fe634480cc71a6592caacceb33fe0b76332c3102fb898c80ff74f6ae95d664",
    "teaching_provider_0045.json": "aa6f08761fc32ac3cbdfc4bf88ceaed1d570477f6f7f8aeb98e6ed17aef7fbe9",
}
RESOURCES = {"bucket": BUCKET, "instance": INSTANCE, "instance_profile": WORKER,
             "schedule": JOB, "security_group": GROUP, "timer_role": TIMER, "worker_role": WORKER}
RESULT_KEYS = {"results/artifacts.zip", "results/complete.json", "results/new_update.json",
               "results/restore/restore_receipt.json", "results/restore_ready.json",
               "results/train_continued_001/campaign_summary.json"}
RETENTION_RULES = [{"ID": "bounded-job-evidence", "Status": "Enabled",
    "Filter": {"Prefix": ""}, "Expiration": {"Days": 7},
    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1}}]
S3_CONSUMED, CONTROL_CONSUMED, DOWNLOADED = 532, 345, 201761654
MAX_CALLS, MAX_SECONDS = 192, 600
BOUNDARY = "Cleanup only; no training, scoring, restart, native execution or learning claim."


def require(value, code):
    if not value:
        raise ValueError("CONTINUATION001_CLEANUP:" + code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "LINKED_PATH")
    return path


def read(path, maximum=1024 * 1024):
    path = safe(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= maximum, "FILE_BOUND_OR_TYPE")
    raw = path.read_bytes()
    require(len(raw) == info.st_size, "FILE_CHANGED")
    return raw


def write(path, value):
    raw = canonical(value)
    require(len(raw) <= 1024 * 1024, "RECEIPT_BOUND")
    with safe(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(read(path) == raw, "RECEIPT_READBACK")
    return sha256(raw).hexdigest()


def ledger_hash(path):
    return sha256(read(path, 8 * 1024 * 1024)).hexdigest()


def environment_identity(output, profile, clients_injected):
    try:
        boto3_version = metadata.version("boto3")
    except metadata.PackageNotFoundError:
        boto3_version = None
    return {"python": sys.version, "python_executable": str(Path(sys.executable).resolve()),
            "platform": sys.platform, "boto3_distribution_version": boto3_version,
            "clients_injected": clients_injected, "tool_path": str(Path(__file__).resolve()),
            "tool_sha256": sha256(read(__file__)).hexdigest(),
            "process_orig_argv": list(sys.orig_argv),
            "absolute_cli_equivalent": [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()),
                                        "--output", str(output), "--profile", profile],
            "argv_boundary": "process_orig_argv is exact; absolute_cli_equivalent normalizes paths and omits interpreter flags."}


def inputs():
    documents = {}
    for name, pin in PINS.items():
        raw = read(ORIGINAL / name)
        require(sha256(raw).hexdigest() == pin, "ORIGINAL_PIN:" + name)
        documents[name] = json.loads(raw)
    context, parent, event = (documents[name] for name in ("intent.json", "result.json", "teaching_provider_0052.json"))
    require(all(doc.get("job") == JOB and doc.get("run_id") == LOGICAL_RUN
                and doc.get("request_sha256") == REQUEST_SHA
                for doc in documents.values()), "ORIGINAL_JOB")
    require(context["run_id"] == LOGICAL_RUN and context["resource_plan"]["account_id"] == ACCOUNT
            and context["resource_plan"]["region"] == REGION, "ORIGINAL_SCOPE")
    require(event["resources"] == RESOURCES and event["s3_attempts"] == S3_CONSUMED
            and event["control_attempts_observed"] == CONTROL_CONSUMED
            and event["result_downloaded_bytes"] == DOWNLOADED, "ORIGINAL_RESOURCE_COUNTERS")
    require(parent["archive"]["guest_status"] == "TEACHING_INCOMPLETE"
            and parent["archive"]["key"] == "results/artifacts.zip"
            and parent["cleanup"]["provider_receipt"]["instance_ids"] == [INSTANCE]
            and set(event["cleanup"]["retained_keys"]) == RESULT_KEYS
            and event["cleanup"]["results_deleted"] is False, "ORIGINAL_RESULT_BOUNDARY")
    require(documents["teaching_provider_0045.json"]["resources"] == RESOURCES
            and documents["teaching_provider_0045.json"]["operation"] == "shutdown_schedule"
            and documents["teaching_provider_0045.json"]["state"] == "CONFIRMED",
            "ORIGINAL_SHUTDOWN_IDENTITY")
    return documents


class NoBudget:
    def __getattr__(self, name):
        raise ValueError("CONTINUATION001_CLEANUP:BUDGET_CALL_FORBIDDEN:" + name)


class Scope:
    """Only the exact cleanup operations below can reach the SDK."""
    def __init__(self, clients, output, schedule, clock=time.monotonic):
        self.clients, self.output, self.schedule, self.clock = clients, output, schedule, clock
        self.started, self.calls, self.armed, self.inventory = clock(), 0, False, None
        for service in ("sts", "ec2", "scheduler", "s3"):
            require(clients[service].meta.region_name == REGION, "CLIENT_REGION:" + service)
        require(clients["iam"].meta.region_name in (REGION, "aws-global"), "CLIENT_REGION:iam")

    def client(self, service):
        owner = self
        class Client:
            def __getattr__(self, method):
                return lambda **arguments: owner.call(service, method, arguments)
        return Client()

    def allowed(self, service, method, args):
        exact = {
            ("sts", "get_caller_identity"): {},
            ("ec2", "describe_instances"): {"InstanceIds": [INSTANCE]},
            ("ec2", "describe_volumes"): {"Filters": [{"Name": "tag:cas_meta_job", "Values": [JOB]}]},
            ("ec2", "describe_security_groups"): {"Filters": [{"Name": "group-name", "Values": [JOB]}]},
            ("ec2", "delete_security_group"): {"GroupId": GROUP},
            ("scheduler", "get_schedule"): {"Name": JOB},
            ("scheduler", "delete_schedule"): {"Name": JOB},
            ("iam", "get_instance_profile"): {"InstanceProfileName": WORKER},
            ("iam", "delete_instance_profile"): {"InstanceProfileName": WORKER},
            ("iam", "remove_role_from_instance_profile"): {"InstanceProfileName": WORKER, "RoleName": WORKER},
            ("s3", "list_objects_v2"): {"Bucket": BUCKET},
            ("s3", "get_bucket_lifecycle_configuration"): {"Bucket": BUCKET},
        }
        if service == "iam" and method in ("get_role", "delete_role", "delete_role_policy"):
            expected = {"RoleName": args.get("RoleName")}
            require(expected["RoleName"] in (WORKER, TIMER), "ROLE_SCOPE")
            if method == "delete_role_policy":
                expected["PolicyName"] = "job-only"
        else:
            require((service, method) in exact, "CALL_FORBIDDEN:" + service + "." + method)
            expected = exact[service, method]
        require(args == expected, "CALL_ARGUMENTS:" + method)
        if method.startswith(("delete_", "remove_")):
            require(self.armed, "MUTATION_BEFORE_ADMISSION")

    def validate(self, service, method, args, value):
        if method == "get_caller_identity":
            require(value.get("Account") == ACCOUNT, "LIVE_ACCOUNT")
        elif method == "describe_instances":
            instances = [i for r in value.get("Reservations", []) for i in r.get("Instances", [])]
            require(not value.get("NextToken") and len(instances) == 1, "INSTANCE_COUNT")
            instance = instances[0]
            require(instance.get("InstanceId") == INSTANCE and instance.get("ClientToken") == JOB
                    and {t["Key"]: t["Value"] for t in instance.get("Tags", [])}.get("cas_meta_job") == JOB,
                    "INSTANCE_IDENTITY")
            require(instance.get("State", {}).get("Name") == "terminated", "INSTANCE_NOT_TERMINATED")
        elif method == "describe_volumes":
            require(value.get("Volumes") == [] and not value.get("NextToken"), "TAGGED_VOLUMES_REMAIN")
        elif method == "describe_security_groups":
            groups = value.get("SecurityGroups", [])
            require(not value.get("NextToken") and len(groups) <= 1, "GROUP_COUNT")
            for group in groups:
                require(group.get("GroupId") == GROUP and group.get("GroupName") == JOB
                        and group.get("OwnerId") == ACCOUNT
                        and {t["Key"]: t["Value"] for t in group.get("Tags", [])}.get("cas_meta_job") == JOB,
                        "GROUP_IDENTITY")
        elif method == "get_schedule":
            require(all(value.get(key) == expected for key, expected in self.schedule.items()), "SCHEDULE_IDENTITY")
        elif method == "get_role":
            role = value.get("Role", {})
            require(role.get("RoleName") == args["RoleName"]
                    and role.get("Arn") == "arn:aws:iam::" + ACCOUNT + ":role/" + args["RoleName"]
                    and {t["Key"]: t["Value"] for t in role.get("Tags", [])}.get("cas_meta_job") == JOB,
                    "ROLE_IDENTITY")
        elif method == "get_instance_profile":
            profile = value.get("InstanceProfile", {})
            require(profile.get("InstanceProfileName") == WORKER
                    and profile.get("Arn") == "arn:aws:iam::" + ACCOUNT + ":instance-profile/" + WORKER
                    and {t["Key"]: t["Value"] for t in profile.get("Tags", [])}.get("cas_meta_job") == JOB,
                    "PROFILE_IDENTITY")
            roles = profile.get("Roles", [])
            require(len(roles) <= 1 and all(r.get("RoleName") == WORKER
                    and r.get("Arn") == "arn:aws:iam::" + ACCOUNT + ":role/" + WORKER for r in roles), "PROFILE_ROLES")
        elif method == "list_objects_v2":
            rows = value.get("Contents", [])
            require(not value.get("IsTruncated") and not value.get("NextContinuationToken")
                    and len(rows) == len(RESULT_KEYS) and {r.get("Key") for r in rows} == RESULT_KEYS, "RESULT_INVENTORY")
            current = sorted((r["Key"], r.get("Size"), r.get("ETag")) for r in rows)
            require(all(type(size) is int and size > 0 and type(tag) is str and tag for _, size, tag in current),
                    "RESULT_OBJECT_IDENTITY")
            if self.inventory is None:
                self.inventory = current
            require(current == self.inventory, "RESULT_OBJECTS_CHANGED")
        elif method == "get_bucket_lifecycle_configuration":
            require(value.get("Rules") == RETENTION_RULES, "RESULT_RETENTION")

    def call(self, service, method, args):
        self.allowed(service, method, args)
        require(self.calls < MAX_CALLS and self.clock() - self.started < MAX_SECONDS, "RECOVERY_CALL_OR_TIME_BOUND")
        self.calls += 1
        stem = "%03d_%s_%s" % (self.calls, service, method)
        write(self.output / (stem + "_intent.json"), {"service": service, "method": method, "arguments": args})
        try:
            value = getattr(self.clients[service], method)(**args)
            # Datetimes in SDK responses become ISO text; no credentials are requested.
            saved = json.loads(json.dumps(value, default=lambda x: x.isoformat() if isinstance(x, datetime) else str(x)))
            write(self.output / (stem + "_result.json"), {"response": saved})
            self.validate(service, method, args, value)
            return value
        except Exception as error:
            write(self.output / (stem + "_error.json"), {"type": type(error).__name__,
                  "code": getattr(error, "response", {}).get("Error", {}).get("Code"), "message": str(error)[:1000]})
            raise


def clients_for(profile):
    import boto3
    from botocore.config import Config
    session = boto3.Session(profile_name=profile, region_name=REGION)
    config = Config(connect_timeout=5, read_timeout=10, retries={"total_max_attempts": 1})
    return {name: session.client(name, config=config) for name in ("sts", "ec2", "iam", "scheduler", "s3")}


def recover(output, *, clients=None, profile="default", clock=time.monotonic):
    output = safe(output)
    require(output == safe(DESTINATION) and not output.exists(), "EXACT_FRESH_DESTINATION_REQUIRED")
    documents = inputs()  # Exact original bytes before client creation or effects.
    context = deepcopy(documents["intent.json"])
    ledger_before = ledger_hash(context["ledger_path"])
    if clients is None:
        require(all(find_spec(name) is not None for name in ("boto3", "botocore")), "SDK_UNAVAILABLE_NO_OUTPUT_CONSUMED")
    output.mkdir()  # Exclusive, one-shot counter continuation; never exist_ok.
    write(output / "intent.json", {"schema": "cas-teaching-continuation001-cleanup-recovery/1", "job": JOB,
          "run_id": LOGICAL_RUN, "request_sha256": REQUEST_SHA, "original_sha256": PINS, "resources": RESOURCES,
          "counters_before": {"s3": S3_CONSUMED, "control": CONTROL_CONSUMED, "downloaded_bytes": DOWNLOADED},
          "ledger_sha256_before": ledger_before, "environment": environment_identity(output, profile, clients is not None),
          "boundary": BOUNDARY, "workload_retry": False})
    provider = scope = module = None
    result = {"schema": "cas-teaching-continuation001-cleanup-recovery/1", "job": JOB, "status": "BLOCKED",
              "run_id": LOGICAL_RUN, "provider_sources_unchanged": False,
              "original_parent_result_unchanged": False, "ledger_unchanged": False,
              "boundary": BOUNDARY, "workload_retry": False, "cleanup": None}
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from aws import teaching_continuation_provider as module
        require(sha256(read(module.__file__)).hexdigest() == context["bindings"]["provider_source_sha256"]
                and module.plan.canonical_sha256(module.source_dependencies())
                == context["bindings"]["provider_dependencies_sha256"], "PROVIDER_SOURCE_PINS")
        source = read(ORIGINAL / "source.zip", 32 * 1024 * 1024)
        require(sha256(source).hexdigest() == context["bindings"]["archive_sha256"], "LOCAL_SOURCE_PIN")
        scope = Scope(clients if clients is not None else clients_for(profile), output,
                      documents["teaching_provider_0045.json"]["schedule"], clock)
        provider = module.TeachingContinuationProvider(clients={n: scope.client(n) for n in scope.clients},
            source_archive=ORIGINAL / "source.zip", guest_driver=ROOT / "aws/teaching_continuation_remote.py",
            pricing_receipt_path=None, ledger_path=context["ledger_path"], budget_module=NoBudget())
        context["receipt_dir"] = str(output)
        provider._context(context)
        provider._resources, provider._instance_ids = deepcopy(RESOURCES), [INSTANCE]
        provider._instance_id, provider._launch_attempted, provider._run_state = INSTANCE, True, "INSTANCE_OBSERVED"
        provider.s3_attempts, provider.control_attempts = S3_CONSUMED, CONTROL_CONSUMED
        provider.result_downloaded_bytes = DOWNLOADED
        provider._source_copy = {"path": str(ORIGINAL / "source.zip"), "sha256": sha256(source).hexdigest(), "bytes": len(source)}
        provider._durable_results, provider._cleaning = False, True
        for service, method, args in (
            ("sts", "get_caller_identity", {}), ("ec2", "describe_instances", {"InstanceIds": [INSTANCE]}),
            ("ec2", "describe_volumes", {"Filters": [{"Name": "tag:cas_meta_job", "Values": [JOB]}]}),
            ("ec2", "describe_security_groups", {"Filters": [{"Name": "group-name", "Values": [JOB]}]}),
            ("scheduler", "get_schedule", {"Name": JOB}), ("iam", "get_instance_profile", {"InstanceProfileName": WORKER}),
            ("iam", "get_role", {"RoleName": WORKER}), ("iam", "get_role", {"RoleName": TIMER}),
            ("s3", "list_objects_v2", {"Bucket": BUCKET}), ("s3", "get_bucket_lifecycle_configuration", {"Bucket": BUCKET}),
        ):
            try:
                getattr(provider.clients[service], method)(**args)
            except Exception as error:
                code = getattr(error, "response", {}).get("Error", {}).get("Code")
                require((service == "iam" and code == "NoSuchEntity")
                        or (service == "scheduler" and code == "ResourceNotFoundException"),
                        "READ_ONLY_ADMISSION_FAILED:" + str(error))
        require(ledger_hash(context["ledger_path"]) == ledger_before, "LEDGER_CHANGED_BEFORE_CLEANUP")
        inputs()  # Recheck all original records immediately before mutation.
        write(output / "admission.json", {"read_only_gates_passed": True, "instance_terminated": True,
              "tagged_volumes_absent": True, "result_inventory": scope.inventory,
              "s3_attempts": provider.s3_attempts, "control_attempts": provider.control_attempts})
        scope.armed = True
        result["cleanup"] = provider.cleanup(context, retain_cloud_copy=True)
        require(result["cleanup"].get("complete") is True
                and result["cleanup"].get("cloud_copy_retained") is True
                and result["cleanup"].get("results_deleted") is False
                and result["cleanup"].get("bucket_deleted") is False, "CLEANUP_INCOMPLETE")
        result["status"] = "CLEANUP_CLOSED_RESULTS_RETAINED"
    except Exception as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)[:1500]}
    finally:
        try:
            inputs()
            result["original_parent_result_unchanged"] = True
            result["ledger_unchanged"] = ledger_hash(context["ledger_path"]) == ledger_before
            require(result["ledger_unchanged"], "LEDGER_CHANGED_AFTER_CLEANUP")
            require(module is not None
                    and sha256(read(module.__file__)).hexdigest() == context["bindings"]["provider_source_sha256"]
                    and module.plan.canonical_sha256(module.source_dependencies())
                    == context["bindings"]["provider_dependencies_sha256"]
                    and sha256(read(ORIGINAL / "source.zip", 32 * 1024 * 1024)).hexdigest()
                    == context["bindings"]["archive_sha256"], "PROVIDER_SOURCE_PINS_CHANGED")
            result["provider_sources_unchanged"] = True
        except Exception as error:
            result["status"] = "BLOCKED"
            result["postcheck_failure"] = str(error)[:1500]
        result["counters_after"] = {"s3": provider.s3_attempts if provider else S3_CONSUMED,
            "control": provider.control_attempts if provider else CONTROL_CONSUMED,
            "downloaded_bytes": provider.result_downloaded_bytes if provider else DOWNLOADED,
            "recovery_sdk_calls": scope.calls if scope else 0}
        result["mutations_admitted"] = scope.armed if scope else False
        write(output / "result.json", result)
    return result


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    result = recover(args.output, profile=args.profile)
    print(json.dumps({"status": result["status"], "job": JOB, "boundary": BOUNDARY}))
    return 0 if result["status"] == "CLEANUP_CLOSED_RESULTS_RETAINED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
