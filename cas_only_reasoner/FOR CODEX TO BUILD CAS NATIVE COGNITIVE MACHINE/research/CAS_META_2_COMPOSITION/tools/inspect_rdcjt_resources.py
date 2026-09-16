"""Read-only AWS inventory for the RDCJT handoff; prints sanitized JSON.

No mutation, billing API, checkpoint loading, or neural work. Credentials use
the existing default profile and are never serialized. Requests do not retry.
"""
import datetime
import json

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def inspect():
    config = Config(connect_timeout=5, read_timeout=15,
                    retries={"total_max_attempts": 1})
    session = boto3.Session(profile_name="default", region_name="us-west-2")
    result = {"schema": "cas-rdcjt-resource-inspection/1",
              "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "region": "us-west-2", "provider_mutations": 0,
              "billing": "NOT_QUERIED", "checks": {}}

    def check(name, function):
        try:
            result["checks"][name] = {"status": "READ_OK", "data": function()}
        except ClientError as error:
            result["checks"][name] = {"status": "UNAVAILABLE",
                "error_code": error.response.get("Error", {}).get("Code", "UNKNOWN")}
        except BotoCoreError as error:
            result["checks"][name] = {"status": "UNAVAILABLE", "error_type": type(error).__name__}

    account = session.client("sts", config=config).get_caller_identity()["Account"]
    if account != "807562639912":
        raise ValueError("EXPECTED_ACCOUNT_REQUIRED")
    result["account"] = account
    ec2 = session.client("ec2", config=config)
    s3 = session.client("s3", config=config)

    def instances():
        rows = []
        for page in ec2.get_paginator("describe_instances").paginate(Filters=[{
                "Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped", "shutting-down"]}]):
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    rows.append({"id": instance["InstanceId"], "type": instance["InstanceType"],
                                 "state": instance["State"]["Name"]})
        return rows

    check("nonterminated_instances", instances)
    check("retained_volume", lambda: [{"id": row["VolumeId"], "state": row["State"],
        "size_gib": row["Size"], "type": row["VolumeType"],
        "attachments": [{"instance": item["InstanceId"], "state": item["State"],
                         "delete_on_termination": item["DeleteOnTermination"]}
                        for item in row["Attachments"]]}
        for row in ec2.describe_volumes(VolumeIds=["vol-01cc880a770c10854"])["Volumes"]])
    for suffix in ("20260913183000-d27a44e4", "20260913184000-d27a44e4"):
        bucket = "cas-meta2-rdcjt-" + suffix + "-" + account
        check(bucket + ":lifecycle", lambda bucket=bucket:
              s3.get_bucket_lifecycle_configuration(Bucket=bucket).get("Rules", []))

        def objects(bucket=bucket):
            count = size = 0
            for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
                for item in page.get("Contents", []):
                    count += 1
                    size += item["Size"]
            return {"objects": count, "bytes": size}

        check(bucket + ":inventory", objects)
    return result


if __name__ == "__main__":
    print(json.dumps(inspect(), indent=2, sort_keys=True))
