import boto3
import os

RUN_ID = os.environ["STAGE_S_RUN_ID"]
REGION = os.environ.get("AWS_REGION", "us-west-2")


def handler(event, context):
    ec2 = boto3.client("ec2", region_name=REGION)
    response = ec2.describe_instances(
        Filters=[
            {"Name": "tag:typed-probe-v5-run-id", "Values": [RUN_ID]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )
    ids = []
    states = []
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            ids.append(instance["InstanceId"])
            states.append(instance.get("State", {}).get("Name", "unknown"))
    if ids:
        ec2.terminate_instances(InstanceIds=ids)
    result = {
        "run_id": RUN_ID,
        "event_kind": event.get("test_kind", "scheduled_watchdog"),
        "found": len(ids),
        "terminated": len(ids),
        "states": states,
    }
    print("typed_probe_v5_watchdog " + str(result))
    return result
