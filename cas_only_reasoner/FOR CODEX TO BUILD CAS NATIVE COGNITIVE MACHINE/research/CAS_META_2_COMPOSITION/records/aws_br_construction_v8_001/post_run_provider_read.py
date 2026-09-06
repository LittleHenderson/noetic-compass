"""One read-only, job-scoped AWS cleanup observation. Does not launch or delete."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

JOB = "cas-meta2-20260906150012-7c9f6d00"
ACCOUNT = "807562639912"
REGION = "us-west-2"
INSTANCE = "i-05ba34f47185eb934"
GROUP = "sg-04aa8a1cddde8b065"
BUCKET = JOB + "-" + ACCOUNT
ROOT = Path(__file__).resolve().parent


def main():
    destination = ROOT / "execution_001/post_run_provider_read.json"
    if destination.exists():
        raise SystemExit("Observation already exists; do not overwrite it.")
    receipt = {
        "schema": "cas-meta2-br-post-run-provider-read/8",
        "job": JOB, "account_id": ACCOUNT, "region": REGION,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, *sys.argv],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "read_only": True, "checks": {}, "responses": {},
    }
    responses = receipt["responses"]
    checks = receipt["checks"]
    try:
        session = boto3.Session(profile_name="default", region_name=REGION)
        config = Config(connect_timeout=10, read_timeout=20, retries={"total_max_attempts": 1})
        clients = {name: session.client(name, config=config)
                   for name in ("sts", "ec2", "iam", "scheduler", "s3")}
        identity = clients["sts"].get_caller_identity()
        responses["identity"] = identity
        if identity["Account"] != ACCOUNT:
            raise ValueError("ACCOUNT_MISMATCH")
        responses["instance"] = clients["ec2"].describe_instances(InstanceIds=[INSTANCE])
        instances = [i for r in responses["instance"]["Reservations"] for i in r["Instances"]]
        if len(instances) != 1:
            raise ValueError("INSTANCE_COUNT_MISMATCH")
        instance = instances[0]
        tags = {x["Key"]: x["Value"] for x in instance.get("Tags", [])}
        checks["owned_instance"] = instance["InstanceId"] == INSTANCE and instance.get("ClientToken") == JOB and tags.get("cas_meta_job") == JOB
        checks["instance_terminated"] = instance["State"]["Name"] == "terminated"
        responses["volumes"] = clients["ec2"].describe_volumes(Filters=[{"Name": "tag:cas_meta_job", "Values": [JOB]}])
        checks["zero_job_volumes"] = not responses["volumes"]["Volumes"] and not responses["volumes"].get("NextToken")

        def absent(label, operation, arguments, expected_code):
            try:
                responses[label] = operation(**arguments)
                checks[label + "_absent"] = False
            except ClientError as error:
                responses[label] = error.response
                checks[label + "_absent"] = error.response["Error"]["Code"] == expected_code

        absent("security_group", clients["ec2"].describe_security_groups,
               {"GroupIds": [GROUP]}, "InvalidGroup.NotFound")
        absent("worker_role", clients["iam"].get_role,
               {"RoleName": JOB + "-worker"}, "NoSuchEntity")
        absent("timer_role", clients["iam"].get_role,
               {"RoleName": JOB + "-timer"}, "NoSuchEntity")
        absent("instance_profile", clients["iam"].get_instance_profile,
               {"InstanceProfileName": JOB + "-worker"}, "NoSuchEntity")
        absent("schedule", clients["scheduler"].get_schedule,
               {"Name": JOB, "GroupName": "default"}, "ResourceNotFoundException")

        s3 = clients["s3"]
        responses["bucket_tags"] = s3.get_bucket_tagging(Bucket=BUCKET)
        bucket_tags = {x["Key"]: x["Value"] for x in responses["bucket_tags"]["TagSet"]}
        if bucket_tags.get("cas_meta_job") != JOB:
            raise ValueError("BUCKET_OWNERSHIP_MISMATCH")
        checks["owned_bucket"] = True
        responses["input_objects"] = s3.list_objects_v2(Bucket=BUCKET, Prefix="input/")
        checks["inputs_absent"] = not responses["input_objects"].get("Contents") and not responses["input_objects"].get("IsTruncated")
        responses["result_objects"] = s3.list_objects_v2(Bucket=BUCKET, Prefix="results/")
        objects = responses["result_objects"].get("Contents", [])
        checks["three_result_objects_only"] = not responses["result_objects"].get("IsTruncated") and {x["Key"] for x in objects} == {"results/artifacts.zip", "results/bootstrap.log", "results/complete.json"}
        responses["bucket_lifecycle"] = s3.get_bucket_lifecycle_configuration(Bucket=BUCKET)
        checks["seven_day_result_expiry"] = any(
            rule.get("Status") == "Enabled" and rule.get("Expiration", {}).get("Days") == 7
            and (rule.get("Prefix") == "" or rule.get("Filter") in ({}, {"Prefix": ""}, {"Prefix": "results/"}))
            for rule in responses["bucket_lifecycle"].get("Rules", [])
        )
        receipt["status"] = "POST_RUN_CLEANUP_CONFIRMED" if all(checks.values()) else "POST_RUN_CHECK_FAILED"
    except Exception as error:
        receipt["status"] = "POST_RUN_READ_FAILED"
        receipt["error"] = {"type": type(error).__name__, "message": str(error)}
    receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["boundary"] = "One read-only provider observation, not an invoice. Three result objects remain under a seven-day lifecycle rule; the bucket itself is retained. No deletion or launch was requested."
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, default=str)
        stream.write("\n")
    print(json.dumps({"status": receipt["status"], "checks": checks,
                      "receipt_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
    return 0 if receipt["status"] == "POST_RUN_CLEANUP_CONFIRMED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
