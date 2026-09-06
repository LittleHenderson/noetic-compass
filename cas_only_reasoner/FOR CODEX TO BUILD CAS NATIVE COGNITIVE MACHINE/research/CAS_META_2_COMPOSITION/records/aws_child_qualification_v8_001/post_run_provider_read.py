"""Read-only cleanup observation for one completed qualification job.

No AWS import or call occurs before the recorded parent exit and exact-job
termination confirmation pass. This script never launches or deletes anything.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parent
JOB = "cas-meta2-20260906155525-195f5ad8"
ACCOUNT, REGION = "807562639912", "us-west-2"
INSTANCE, GROUP = "i-093f35093d672bcae", "sg-0e0df05cf543290ca"
BUCKET = JOB + "-" + ACCOUNT
SOURCE_SHA = "b61b011c3d53ae49a1f7f988397df632e95e82a6"
REGISTRATION_COMMIT = "a8376f663acc76fa966d9663a9c28a8d61dcba87"
REQUEST_SHA = "0b1b73e0b750c3c657eed42686e5aebdcd2b768786f7240134ac4d67899bf861"
AUTHORITY_SHA = "3c7e5dcfd574257aed2a6e855284f5f6183e6ff89272b4ff737fefb803adcf49"
CAPTURE_SHA = "9d92311d10b93aa72738de8b59754193e1f0bb782f2a43a2ae453f05f66472b1"
REGISTRATION_SHA = "fcf4f468101fa7019b4394b02b04762c7c2aa7ead5b5295b171a46e1d9473fd8"
ARCHIVE_SHA = "d93a39f3a264c23f27ac7dcdd2779eca665150a6bd739820651e953958e8f7d3"
MANIFEST_SHA = "a19590941a53a7c3aa0a343501a7330ea5f89e56f10454ad82603eb4c6d0b69d"
EXPERIMENT = {"entrypoint": "cas_meta2.child_qualification_gpu_v8",
              "profile": "one_child_full_task_qualification_v8"}
PINNED = {
    "registration_001/launch_request.json": REQUEST_SHA,
    "registration_001/standing_authority.json": AUTHORITY_SHA,
    "registration_001/capture_parent.py": CAPTURE_SHA,
    "registration_001/registration_receipt.json": REGISTRATION_SHA,
}
RESULT_KEYS = {"results/artifacts.zip", "results/bootstrap.log", "results/complete.json"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def utc():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False, default=str) + "\n").encode()


def safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(
        p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)),
        "POST_RUN_LINK_OR_TRAVERSAL_REFUSED")
    return path


def read(path, limit=8 * 1024**2):
    path = safe(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= limit,
            "POST_RUN_BOUNDED_REGULAR_FILE_REQUIRED")
    return path.read_bytes()


def load_gate():
    """Only local reads. A missing completion or termination record refuses AWS."""
    names = [*PINNED, "registration_001/parent_process_start.json",
        "registration_001/parent_process_identity.json", "registration_001/parent_process_completion.json",
        "execution_001/launch_request.json", "execution_001/launch_receipt.json"]
    raw = {name: read(ROOT / name) for name in names}
    for name, expected in PINNED.items():
        require(sha256(raw[name]).hexdigest() == expected, "POST_RUN_REGISTERED_BYTES_CHANGED:" + name)
    require(sha256(raw["execution_001/launch_request.json"]).hexdigest() == REQUEST_SHA,
            "POST_RUN_EXECUTION_REQUEST_CHANGED")
    values = {name: json.loads(value) for name, value in raw.items() if name.endswith(".json")}
    request = values["registration_001/launch_request.json"]
    launch = values["execution_001/launch_receipt.json"]
    completion = values["registration_001/parent_process_completion.json"]
    start = values["registration_001/parent_process_start.json"]
    process = values["registration_001/parent_process_identity.json"]
    require(completion.get("schema") == "cas-meta2-child-qualification-parent-capture/8"
            and type(completion.get("exit_code")) is int and completion.get("process_created") is True
            and "capture_failure" not in completion and completion.get("capture_source_sha256") == CAPTURE_SHA
            and completion.get("request_sha256") == REQUEST_SHA
            and completion.get("authority_sha256") == AUTHORITY_SHA,
            "POST_RUN_PARENT_EXIT_NOT_CONFIRMED")
    require(type(completion.get("pid")) is int and completion["pid"] == process.get("pid")
            and completion.get("command") == process.get("command") == start.get("command")
            and all(completion.get(key) == value for key, value in start.items()),
            "POST_RUN_PARENT_CAPTURE_IDENTITY_CHANGED")
    finished = datetime.fromisoformat(completion["finished_utc"])
    begun = datetime.fromisoformat(completion["started_utc"])
    require(finished.tzinfo is not None and begun.tzinfo is not None
            and begun <= finished <= datetime.now(timezone.utc), "POST_RUN_PARENT_COMPLETION_TIME")
    require(launch.get("schema") == "cas-meta2-child-qualification-launch-receipt/8"
            and launch.get("job") == request.get("job") == JOB
            and launch.get("request_sha256") == REQUEST_SHA
            and launch.get("source_sha") == launch.get("parent_source_sha") == SOURCE_SHA
            and launch.get("archive_sha256") == ARCHIVE_SHA
            and launch.get("source_manifest_sha256") == MANIFEST_SHA
            and launch.get("experiment") == EXPERIMENT, "POST_RUN_LAUNCH_IDENTITY_CHANGED")
    resources = launch["resources"]
    require(resources.get("instance") == INSTANCE and resources.get("security_group") == GROUP
            and resources.get("bucket") == BUCKET and resources.get("instance_profile") == JOB + "-worker"
            and resources.get("schedule") == JOB, "POST_RUN_RESOURCE_IDENTITY_CHANGED")
    require(launch.get("termination_confirmed") is True and any(
        event.get("event") == "INSTANCE_TERMINATION_CONFIRMED" and event.get("instance_id") == INSTANCE
        for event in launch.get("events", [])), "POST_RUN_TERMINATION_NOT_CONFIRMED")
    for name, metadata in completion.get("outputs", {}).items():
        require(name in ("parent_stdout.txt", "parent_stderr.txt"), "POST_RUN_CAPTURE_OUTPUT_NAME")
        relative = "registration_001/" + name
        raw[relative] = read(ROOT / relative)
        require(sha256(raw[relative]).hexdigest() == metadata["sha256"]
                and len(raw[relative]) == metadata["bytes"], "POST_RUN_CAPTURE_OUTPUT_CHANGED")
    require(set(completion.get("outputs", {})) == {"parent_stdout.txt", "parent_stderr.txt"},
            "POST_RUN_CAPTURE_OUTPUTS_MISSING")
    return raw, launch, completion


def safe_response(value):
    """Getter responses contain no credentials; additionally strip known secret fields."""
    if isinstance(value, dict):
        secret = {"authorization", "cookie", "set-cookie", "secretaccesskey", "sessiontoken",
                  "accesskeyid", "credentials", "password"}
        return {str(k): ("[REDACTED]" if str(k).lower() in secret else safe_response(v))
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_response(v) for v in value]
    return value


def observe(clients, receipt, launch):
    """One bounded sequence of approved getter calls; injectable for pure checks."""
    checks = receipt["checks"]
    queries = receipt["queries"]

    def query(label, service, operation, arguments):
        row = {"label": label, "service": service, "operation": operation,
               "arguments": arguments, "started_utc": utc()}
        queries.append(row)
        try:
            response = getattr(clients[service], operation)(**arguments)
            row.update(response=safe_response(response), outcome="RETURNED")
            return response, None
        except Exception as error:
            response = getattr(error, "response", {})
            details = response.get("Error", {})
            row.update(outcome="ERROR", error={"type": type(error).__name__,
                "code": details.get("Code"), "message": details.get("Message", str(error))},
                response=safe_response(response))
            return None, details.get("Code")
        finally:
            row["finished_utc"] = utc()

    def absent(label, service, operation, arguments, code):
        _, actual = query(label, service, operation, arguments)
        checks[label + "_absent"] = actual == code

    identity, _ = query("identity", "sts", "get_caller_identity", {})
    require(identity is not None and identity.get("Account") == ACCOUNT, "POST_RUN_ACCOUNT_MISMATCH_OR_UNAVAILABLE")
    checks["account_identity"] = True
    response, _ = query("instance", "ec2", "describe_instances", {"InstanceIds": [INSTANCE]})
    instances = [item for group in (response or {}).get("Reservations", []) for item in group.get("Instances", [])]
    instance = instances[0] if len(instances) == 1 else {}
    tags = {row["Key"]: row["Value"] for row in instance.get("Tags", [])}
    checks["owned_instance"] = (instance.get("InstanceId") == INSTANCE
        and instance.get("ClientToken") == JOB and tags.get("cas_meta_job") == JOB
        and instance.get("InstanceType") == "g7.2xlarge")
    checks["instance_terminated"] = instance.get("State", {}).get("Name") == "terminated"
    response, _ = query("volumes", "ec2", "describe_volumes",
        {"Filters": [{"Name": "tag:cas_meta_job", "Values": [JOB]}]})
    checks["zero_job_volumes"] = response is not None and not response.get("Volumes") and not response.get("NextToken")
    absent("security_group", "ec2", "describe_security_groups", {"GroupIds": [GROUP]}, "InvalidGroup.NotFound")
    absent("worker_role", "iam", "get_role", {"RoleName": JOB + "-worker"}, "NoSuchEntity")
    absent("timer_role", "iam", "get_role", {"RoleName": JOB + "-timer"}, "NoSuchEntity")
    absent("instance_profile", "iam", "get_instance_profile",
        {"InstanceProfileName": JOB + "-worker"}, "NoSuchEntity")
    absent("schedule", "scheduler", "get_schedule", {"Name": JOB, "GroupName": "default"},
        "ResourceNotFoundException")
    response, _ = query("bucket_tags", "s3", "get_bucket_tagging", {"Bucket": BUCKET})
    tags = {row["Key"]: row["Value"] for row in (response or {}).get("TagSet", [])}
    checks["owned_bucket"] = tags.get("cas_meta_job") == JOB
    response, _ = query("input_objects", "s3", "list_objects_v2", {"Bucket": BUCKET, "Prefix": "input/"})
    checks["inputs_absent"] = response is not None and not response.get("Contents") and response.get("IsTruncated") is False
    response, _ = query("result_objects", "s3", "list_objects_v2", {"Bucket": BUCKET, "Prefix": "results/"})
    objects = (response or {}).get("Contents", [])
    checks["three_result_objects_only"] = (response is not None and response.get("IsTruncated") is False
        and len(objects) == 3 and {row["Key"] for row in objects} == RESULT_KEYS)
    artifact, _ = query("retained_archive_metadata", "s3", "head_object",
        {"Bucket": BUCKET, "Key": "results/artifacts.zip"})
    result = launch.get("result", {})
    checks["retained_archive_size_matches_parent"] = (artifact is not None
        and type(result.get("bytes")) is int and result["bytes"] > 0
        and artifact.get("ContentLength") == result["bytes"])
    response, _ = query("bucket_lifecycle", "s3", "get_bucket_lifecycle_configuration", {"Bucket": BUCKET})
    checks["seven_day_result_expiry"] = any(
        rule.get("Status") == "Enabled" and rule.get("Expiration", {}).get("Days") == 7
        and (rule.get("Prefix") == "" or rule.get("Filter") in ({}, {"Prefix": ""}, {"Prefix": "results/"}))
        for rule in (response or {}).get("Rules", []))
    receipt["status"] = "POST_RUN_CLEANUP_CONFIRMED" if all(checks.values()) else "POST_RUN_CHECK_FAILED"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path, default=ROOT / "provider_check_001")
    args = parser.parse_args(argv)
    output = safe(args.output)
    require(output.parent == safe(ROOT) and re.fullmatch(r"provider_check_[0-9]{3}", output.name)
            and not output.exists(), "POST_RUN_FRESH_SCOPED_OUTPUT_REQUIRED")
    raw, launch, completion = load_gate()  # Must finish BEFORE SDK import or provider access.
    script_raw = read(Path(__file__))
    output.mkdir()
    receipt = {"schema": "cas-meta2-child-qualification-post-run-provider-read/8",
        "job": JOB, "account_id": ACCOUNT, "region": REGION, "source_sha": SOURCE_SHA,
        "parent_source_sha": SOURCE_SHA, "registration_commit": REGISTRATION_COMMIT,
        "request_sha256": REQUEST_SHA, "source_archive_sha256": ARCHIVE_SHA,
        "source_manifest_sha256": MANIFEST_SHA, "resources": launch["resources"],
        "parent_exit_code": completion["exit_code"], "parent_finished_utc": completion["finished_utc"],
        "parent_launch_status": launch["status"], "parent_result": launch.get("result"),
        "started_utc": utc(), "command": [sys.executable, *sys.argv], "cwd": str(Path.cwd()),
        "python": sys.version, "script_sha256": sha256(script_raw).hexdigest(),
        "read_only": True, "automatic_retries": 0, "provider_calls_started": False,
        "checks": {}, "queries": [], "input_files": {
            name: {"bytes": len(value), "sha256": sha256(value).hexdigest()} for name, value in raw.items()}}
    try:
        import boto3
        from botocore.config import Config
        session = boto3.Session(profile_name="default", region_name=REGION)
        config = Config(connect_timeout=10, read_timeout=20, retries={"total_max_attempts": 1})
        clients = {name: session.client(name, config=config) for name in ("sts", "ec2", "iam", "scheduler", "s3")}
        receipt["provider_calls_started"] = True
        observe(clients, receipt, launch)
    except Exception as error:
        receipt.update(status="POST_RUN_READ_FAILED", error={"type": type(error).__name__, "message": str(error)})
    finally:
        try:
            unchanged = read(Path(__file__)) == script_raw and all(read(ROOT / name) == value for name, value in raw.items())
        except Exception as error:
            unchanged = False
            receipt["local_evidence_postcheck_error"] = {"type": type(error).__name__, "message": str(error)}
        receipt["checks"]["local_evidence_unchanged"] = unchanged
        if not unchanged:
            receipt["status"] = "POST_RUN_CHECK_FAILED"
        receipt["finished_utc"] = utc()
        receipt["boundary"] = ("One read-only provider observation, not an invoice or a native task result. "
            "The bucket and result objects remain under the observed lifecycle rule. Object bytes were not "
            "downloaded or rehashed by this check; archive length alone is not content identity. No cleanup mutation or launch.")
        destination = output / "receipt.json"
        with destination.open("xb") as stream:
            stream.write(encoded(receipt))
    print(json.dumps({"status": receipt["status"], "checks": receipt["checks"],
        "receipt": str(destination), "receipt_sha256": sha256(read(destination)).hexdigest()}))
    return 0 if receipt["status"] == "POST_RUN_CLEANUP_CONFIRMED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
