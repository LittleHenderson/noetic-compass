"""Read-only, exact-job cleanup observation. Never mutate cloud or the ledger."""
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
JOB = "cas-meta2-20260905214620-cfdbb893"
ACCOUNT = "807562639912"
REGION = "us-west-2"
INSTANCE = "i-016458110296bf671"
SG = "sg-0c8a5a9d9a9695ec0"
SOURCE = "410bce98307a5644db51928459b73391c7066b72"
ARCHIVE = "11311cf8451a95014b162e7b3b65e6854cf5eb72a61532e4c04168f59520bc5f"
ARTIFACT = "0d1b13aa711685cc488bdfdb981d8682d3d1b02b8e67530a3742add44dd13e93"
ARTIFACT_BYTES = 59648802
BUCKET = JOB + "-" + ACCOUNT
WORKER, TIMER = JOB + "-worker", JOB + "-timer"
BUDGET_SHA = "77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0"
READ_ONLY = {
    "sts": {"get_caller_identity"},
    "ec2": {"describe_instances", "describe_volumes", "describe_security_groups"},
    "iam": {"get_instance_profile", "get_role"},
    "scheduler": {"get_schedule"},
    "s3": {"get_bucket_tagging", "list_objects_v2", "get_bucket_lifecycle_configuration",
           "get_public_access_block", "get_bucket_encryption", "head_object", "get_object"},
}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    state = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            state.update(block)
    return state.hexdigest()


def owned_receipt(raw):
    value = json.loads(raw)
    require(value["job"] == JOB and value["source_sha"] == SOURCE and value["archive_sha256"] == ARCHIVE,
            "SOURCE_OR_JOB_MISMATCH")
    resources = value["resources"]
    require(resources["instance"] == INSTANCE and resources["security_group"] == SG
            and resources["bucket"] == BUCKET and resources["instance_profile"] == WORKER
            and resources["schedule"] == JOB, "EXACT_OWNED_RESOURCES_MISMATCH")
    require(value["result"]["sha256"] == ARTIFACT and value["result"]["bytes"] == ARTIFACT_BYTES,
            "DOWNLOADED_ARTIFACT_RECEIPT_MISMATCH")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observation", type=int, required=True)
    args = parser.parse_args()
    require(1 <= args.observation <= 9, "BOUNDED_OBSERVATION_NUMBER_REQUIRED")
    receipt_path = OUT / ("closure_observation_%02d.json" % args.observation)
    raw_path = OUT / ("provider_calls_%02d.jsonl" % args.observation)
    require(not receipt_path.exists() and not raw_path.exists(), "NEW_OBSERVATION_FILES_REQUIRED")
    original_path = ROOT / "records/aws_learning_v2_001/launch_receipt.json"
    original_bytes = original_path.read_bytes()
    original = owned_receipt(original_bytes)
    artifact_path = original_path.with_name("cloud_artifacts.zip")
    require(artifact_path.stat().st_size == ARTIFACT_BYTES and sha(artifact_path) == ARTIFACT,
            "LOCAL_ARTIFACT_BYTES_MISMATCH")
    budget_path = ROOT / "aws/budget.py"
    require(sha(budget_path) == BUDGET_SHA, "FROZEN_BUDGET_CHECKER_CHANGED")
    spec = importlib.util.spec_from_file_location("closure_readonly_budget", budget_path)
    budget = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(budget)
    ledger_path = budget.CANONICAL_LEDGER
    ledger_bytes = ledger_path.read_bytes()
    # This pure reader creates no lock, reservation, refund or other file.
    state = budget.read_locked(ledger_path, ledger_path.with_suffix(".json.history"))
    require(state["owner_task_cap_usd"] == "400.00" and state["total_reserved_usd"] == "25.00"
            and state["remaining_unreserved_usd"] == "375.00", "EXPECTED_SHARED_BUDGET_MISMATCH")
    matching = [row for row in state["reservations"] if row["job"] == JOB]
    require(len(matching) == 1 and matching[0]["reserved_usd"] == "7.00"
            and matching[0]["source_sha"] == SOURCE and matching[0]["archive_sha256"] == ARCHIVE,
            "EXACT_JOB_RESERVATION_MISMATCH")
    receipt = {"schema": "cas-meta2-independent-readonly-closure/1", "job": JOB, "source_sha": SOURCE,
        "archive_sha256": ARCHIVE, "region": REGION, "account": ACCOUNT, "started_utc": utc(),
        "status": "CHECKING", "original_launch_receipt": str(original_path),
        "original_launch_receipt_sha256_before": hashlib.sha256(original_bytes).hexdigest(),
        "local_artifact_sha256": ARTIFACT, "artifact_bytes": ARTIFACT_BYTES,
        "ledger_path": str(ledger_path), "ledger_sha256": hashlib.sha256(ledger_bytes).hexdigest(),
        "budget": {"cap_usd": "400.00", "reserved_usd": "25.00", "remaining_unreserved_usd": "375.00",
                   "this_job_reserved_usd": "7.00", "refunds": 0, "history_checked": True},
        "command": [sys.executable, "-B", str(Path(__file__).resolve()), *sys.argv[1:]],
        "python": sys.version, "provider_mutations": 0, "budget_mutations": 0,
        "original_receipt_mutations": 0, "neural_execution_performed": False,
        "checks": {}, "raw_provider_calls": str(raw_path),
        "evidence_boundary": "Point-in-time provider cleanup and retention observation, not an AWS invoice or provider-enforced spending cap. The active launcher alone owns cleanup. No private evaluation contents are opened; local archive is hashed as opaque bytes."}
    config = Config(connect_timeout=10, read_timeout=20, retries={"max_attempts": 0})
    session = boto3.Session(profile_name="default", region_name=REGION)
    clients = {name: session.client(name, config=config) for name in READ_ONLY}
    def call(service, operation, **kwargs):
        require(operation in READ_ONLY.get(service, set()), "PROVIDER_MUTATION_FORBIDDEN")
        if operation == "get_object":
            require(kwargs == {"Bucket": BUCKET, "Key": "results/complete.json"}, "RESULT_CONTENT_READ_FORBIDDEN")
        entry = {"utc": utc(), "service": service, "operation": operation, "arguments": kwargs}
        try:
            response = getattr(clients[service], operation)(**kwargs)
            if operation == "get_object":
                with response["Body"] as stream:
                    body = stream.read(16385)
                require(len(body) <= 16384, "COMPLETION_RECEIPT_SIZE_CEILING")
                response = {key: value for key, value in response.items() if key != "Body"}
                response["body_json"] = json.loads(body)
                response["body_sha256"] = hashlib.sha256(body).hexdigest()
            entry["response"] = response
            return response
        except ClientError as exc:
            entry["error"] = exc.response
            raise
        finally:
            entry["finished_utc"] = utc()
            with raw_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
    def absent(service, operation, expected_code, **kwargs):
        try:
            call(service, operation, **kwargs)
        except ClientError as exc:
            require(exc.response["Error"]["Code"] == expected_code, "UNEXPECTED_PROVIDER_ABSENCE_ERROR")
            return True
        return False
    try:
        identity = call("sts", "get_caller_identity")
        require(identity["Account"] == ACCOUNT, "AWS_ACCOUNT_MISMATCH")
        checks = receipt["checks"]
        try:
            response = call("ec2", "describe_instances", InstanceIds=[INSTANCE])
            require(not response.get("NextToken"), "INCOMPLETE_EXACT_INSTANCE_LOOKUP")
            instances = [i for r in response["Reservations"] for i in r["Instances"]]
        except ClientError as exc:
            require(exc.response["Error"]["Code"] == "InvalidInstanceID.NotFound", "UNEXPECTED_INSTANCE_LOOKUP_ERROR")
            instances = []
        require(len(instances) <= 1, "UNEXPECTED_INSTANCE_COUNT")
        volumes = set()
        if instances:
            instance = instances[0]
            require(instance["InstanceId"] == INSTANCE and instance["ClientToken"] == JOB
                    and {t["Key"]: t["Value"] for t in instance.get("Tags", [])}.get("cas_meta_job") == JOB,
                    "INSTANCE_OWNERSHIP_MISMATCH")
            receipt["instance_state"] = instance["State"]["Name"]
            receipt["provider_launch_time"] = instance["LaunchTime"]
            volumes.update(row["Ebs"]["VolumeId"] for row in instance.get("BlockDeviceMappings", []) if "Ebs" in row)
        else:
            receipt["instance_state"] = "absent_from_exact_id_lookup"
        checks["exact_instance_terminated_or_absent"] = not instances or receipt["instance_state"] == "terminated"
        tagged = call("ec2", "describe_instances", Filters=[{"Name": "tag:cas_meta_job", "Values": [JOB]}])
        require(not tagged.get("NextToken"), "INCOMPLETE_JOB_INSTANCE_LOOKUP")
        checks["no_nonterminated_job_instances"] = not any(i["State"]["Name"] != "terminated"
            for reservation in tagged["Reservations"] for i in reservation["Instances"])
        volume_response = call("ec2", "describe_volumes", Filters=[{"Name": "tag:cas_meta_job", "Values": [JOB]}])
        require(not volume_response.get("NextToken"), "INCOMPLETE_JOB_VOLUME_LOOKUP")
        volumes.update(row["VolumeId"] for row in volume_response["Volumes"])
        receipt["observed_owned_volume_ids"] = sorted(volumes)
        checks["no_job_volumes"] = not volume_response["Volumes"]
        for volume in sorted(volumes):
            checks["exact_volume_absent:" + volume] = absent("ec2", "describe_volumes", "InvalidVolume.NotFound", VolumeIds=[volume])
        checks["security_group_absent"] = absent("ec2", "describe_security_groups", "InvalidGroup.NotFound", GroupIds=[SG])
        checks["profile_absent"] = absent("iam", "get_instance_profile", "NoSuchEntity", InstanceProfileName=WORKER)
        checks["worker_role_absent"] = absent("iam", "get_role", "NoSuchEntity", RoleName=WORKER)
        checks["timer_role_absent"] = absent("iam", "get_role", "NoSuchEntity", RoleName=TIMER)
        checks["schedule_absent"] = absent("scheduler", "get_schedule", "ResourceNotFoundException", Name=JOB)
        tags = call("s3", "get_bucket_tagging", Bucket=BUCKET)
        checks["retained_bucket_job_owned"] = {t["Key"]: t["Value"] for t in tags["TagSet"]}.get("cas_meta_job") == JOB
        objects = call("s3", "list_objects_v2", Bucket=BUCKET)
        checks["exactly_three_results_retained"] = not objects.get("IsTruncated") and {r["Key"] for r in objects.get("Contents", [])} == {"results/artifacts.zip", "results/complete.json", "results/bootstrap.log"}
        checks["result_bytes_below_1gib"] = sum(r["Size"] for r in objects.get("Contents", [])) <= 1024**3
        receipt["retained_objects"] = objects.get("Contents", [])
        rules = call("s3", "get_bucket_lifecycle_configuration", Bucket=BUCKET)["Rules"]
        checks["seven_day_expiration"] = any(r.get("Status") == "Enabled" and r.get("Filter") == {"Prefix": ""} and r.get("Expiration", {}).get("Days") == 7 for r in rules)
        checks["incomplete_upload_cleanup"] = any(r.get("Status") == "Enabled" and r.get("AbortIncompleteMultipartUpload", {}).get("DaysAfterInitiation") == 1 for r in rules)
        block = call("s3", "get_public_access_block", Bucket=BUCKET)["PublicAccessBlockConfiguration"]
        checks["public_access_blocked"] = all(block.get(k) is True for k in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"))
        encryption = call("s3", "get_bucket_encryption", Bucket=BUCKET)["ServerSideEncryptionConfiguration"]["Rules"]
        checks["default_encryption"] = any(r.get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm") == "AES256" for r in encryption)
        head = call("s3", "head_object", Bucket=BUCKET, Key="results/artifacts.zip")
        checks["remote_artifact_size_and_encryption"] = head["ContentLength"] == ARTIFACT_BYTES and head.get("ServerSideEncryption") == "AES256"
        completion = call("s3", "get_object", Bucket=BUCKET, Key="results/complete.json")["body_json"]
        checks["remote_completion_matches_download"] = completion.get("job") == JOB and completion.get("sha256") == ARTIFACT and completion.get("bytes") == ARTIFACT_BYTES and completion.get("returncode") == 0 and completion.get("partial_evidence") is False and completion.get("omitted_full_file_count") == 0 and completion.get("smoke_only") is False
        final_bytes = original_path.read_bytes()
        final = owned_receipt(final_bytes)
        receipt["original_launch_receipt_sha256_after"] = hashlib.sha256(final_bytes).hexdigest()
        receipt["active_launcher_updated_its_receipt_during_observation"] = final_bytes != original_bytes
        checks["launcher_confirmed_final_cleanup"] = final.get("termination_confirmed") is True and final.get("cleanup_errors") == []
        receipt["cost_estimate_from_launcher"] = final.get("cost_estimate")
        checks["ledger_unchanged"] = ledger_path.read_bytes() == ledger_bytes and sha(budget_path) == BUDGET_SHA
        receipt["status"] = "CAS_META_2_LEARNING_V2_CLEANUP_INDEPENDENTLY_VERIFIED" if all(checks.values()) else "CAS_META_2_LEARNING_V2_CLEANUP_STILL_PENDING"
    except Exception as exc:
        receipt["status"] = "CAS_META_2_LEARNING_V2_CLEANUP_OBSERVATION_FAILED"
        receipt["failure"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        receipt["finished_utc"] = utc()
        receipt["helper_sha256"] = sha(__file__)
        if raw_path.exists():
            receipt["raw_provider_calls_sha256"] = sha(raw_path)
        with receipt_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, indent=2, default=str) + "\n")
        print(json.dumps({key: receipt.get(key) for key in ("status", "instance_state", "started_utc", "finished_utc", "checks", "budget", "failure")}, indent=2), flush=True)
    return 0 if receipt["status"].endswith("INDEPENDENTLY_VERIFIED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
