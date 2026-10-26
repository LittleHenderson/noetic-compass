#!/usr/bin/env python3
"""Remove only temporary AWS resources owned by this one v5 run; keep evidence."""
import json
import time

import boto3
from botocore.exceptions import ClientError

REGION = "us-west-2"
ACCOUNT = "807562639912"
RUN_ID = "typed-probe-v5-stage-continuation-retry1-20261025"
TAG_KEY = "typed-probe-v5-run-id"
BUCKET = "cas-harness-runpod-92754088"
INSTANCE_TYPE = "g5.2xlarge"
PARAMETER_NAME = "/cas-harness/typed-probe-v5/typed-probe-v5-stage-continuation-retry1-20261025/anthropic-api-key"
INSTANCE_ROLE = "typed-probe-v5-stage-s-role-continuation-retry1-20261025"
INSTANCE_PROFILE = "typed-probe-v5-stage-s-profile-continuation-retry1-20261025"
WATCHDOG_FUNCTION = "typed-probe-v5-stage-s-watchdog-continuation-retry1-20261025"
WATCHDOG_ROLE = "typed-probe-v5-stage-s-watchdog-role-retry1-20261025"
SCHEDULER_ROLE = "typed-probe-v5-scheduler-continuation-retry1-20261025"
SCHEDULES = [
    "typed-probe-v5-stage-s-test-continuation-retry1-20261025",
    "typed-probe-v5-stage-s-stop-continuation-retry1-20261025",
]


def client(service):
    return boto3.client(service, region_name=REGION)


def missing(exc, *codes):
    return exc.response.get("Error", {}).get("Code") in set(codes)


def delete_schedule(scheduler, name):
    try:
        scheduler.delete_schedule(Name=name, GroupName="default")
    except ClientError as exc:
        if not missing(exc, "ResourceNotFoundException"):
            raise


def run_instances(ec2):
    response = ec2.describe_instances(Filters=[
        {"Name": f"tag:{TAG_KEY}", "Values": [RUN_ID]},
        {"Name": "instance-state-name", "Values": [
            "pending", "running", "stopping", "stopped", "shutting-down"]},
    ])
    return [instance for reservation in response.get("Reservations", [])
            for instance in reservation.get("Instances", [])]


def cleanup_compute(ec2):
    instances = run_instances(ec2)
    ids = [instance["InstanceId"] for instance in instances]
    terminate_ids = [instance["InstanceId"] for instance in instances
                     if instance.get("State", {}).get("Name") in {
                         "pending", "running", "stopping", "stopped"}]
    if terminate_ids:
        ec2.terminate_instances(InstanceIds=terminate_ids)
    for instance_id in ids:
        ec2.get_waiter("instance_terminated").wait(
            InstanceIds=[instance_id], WaiterConfig={"Delay": 5, "MaxAttempts": 60})

    for _ in range(60):
        volumes = ec2.describe_volumes(Filters=[
            {"Name": f"tag:{TAG_KEY}", "Values": [RUN_ID]},
        ]).get("Volumes", [])
        attached_to_other = [volume for volume in volumes
                             if any(attachment.get("InstanceId") not in ids
                                    for attachment in volume.get("Attachments", []))]
        if attached_to_other:
            raise RuntimeError("a run-tagged disk is attached to an instance outside this run")
        busy = [volume for volume in volumes if volume.get("State") in {"creating", "in-use", "deleting"}]
        if busy:
            time.sleep(5)
            continue
        for volume in volumes:
            if volume.get("State") == "available":
                ec2.delete_volume(VolumeId=volume["VolumeId"])
        break
    else:
        raise RuntimeError("run-tagged EBS disks did not detach within five minutes")

    remaining = ec2.describe_volumes(Filters=[
        {"Name": f"tag:{TAG_KEY}", "Values": [RUN_ID]},
    ]).get("Volumes", [])
    if remaining:
        raise RuntimeError("a run-tagged EBS disk remains after cleanup")
    return {"instances_terminated": len(ids), "run_tagged_volumes_remaining": 0}


def delete_parameter(ssm):
    try:
        ssm.get_parameter(Name=PARAMETER_NAME)
    except ClientError as exc:
        if missing(exc, "ParameterNotFound"):
            return "absent"
        raise
    try:
        tags = {row["Key"]: row["Value"] for row in ssm.list_tags_for_resource(
            ResourceType="Parameter", ResourceId=PARAMETER_NAME).get("TagList", [])}
        if tags.get("RunId") != RUN_ID:
            raise RuntimeError("refusing to delete a secure parameter not tagged to this run")
        ssm.delete_parameter(Name=PARAMETER_NAME)
        return "deleted"
    except ClientError as exc:
        if missing(exc, "ParameterNotFound", "InvalidResourceId"):
            return "absent"
        raise


def delete_lambda(lambdas):
    try:
        lambdas.delete_function(FunctionName=WATCHDOG_FUNCTION)
    except ClientError as exc:
        if not missing(exc, "ResourceNotFoundException"):
            raise
        return "absent"
    for _ in range(60):
        try:
            lambdas.get_function(FunctionName=WATCHDOG_FUNCTION)
        except ClientError as exc:
            if missing(exc, "ResourceNotFoundException"):
                return "deleted"
            raise
        time.sleep(2)
    raise RuntimeError("watchdog Lambda remained after the delete request")


def delete_instance_profile(iam):
    try:
        profile = iam.get_instance_profile(InstanceProfileName=INSTANCE_PROFILE)["InstanceProfile"]
    except ClientError as exc:
        if missing(exc, "NoSuchEntity"):
            return "absent"
        raise
    roles = {row["RoleName"] for row in profile.get("Roles", [])}
    if roles - {INSTANCE_ROLE}:
        raise RuntimeError("instance profile contains an unexpected role; refusing to remove it")
    if INSTANCE_ROLE in roles:
        iam.remove_role_from_instance_profile(
            InstanceProfileName=INSTANCE_PROFILE, RoleName=INSTANCE_ROLE)
    iam.delete_instance_profile(InstanceProfileName=INSTANCE_PROFILE)
    return "deleted"


def delete_role(iam, role_name):
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
    except ClientError as exc:
        if missing(exc, "NoSuchEntity"):
            return "absent"
        raise
    tags = {row["Key"]: row["Value"] for row in role.get("Tags", [])}
    if tags.get("RunId") != RUN_ID:
        raise RuntimeError(f"refusing to delete IAM role not tagged to this run: {role_name}")
    managed = iam.list_attached_role_policies(RoleName=role_name).get("AttachedPolicies", [])
    if managed:
        raise RuntimeError(f"refusing to detach unexpected managed policies from {role_name}")
    for name in iam.list_role_policies(RoleName=role_name).get("PolicyNames", []):
        iam.delete_role_policy(RoleName=role_name, PolicyName=name)
    iam.delete_role(RoleName=role_name)
    return "deleted"


def main():
    identity = client("sts").get_caller_identity()
    if identity.get("Account") != ACCOUNT:
        raise RuntimeError("AWS identity does not match the approved project account")
    ec2 = client("ec2")
    compute = cleanup_compute(ec2)
    scheduler = client("scheduler")
    for name in SCHEDULES:
        delete_schedule(scheduler, name)
    parameter = delete_parameter(client("ssm"))
    watchdog = delete_lambda(client("lambda"))
    iam = client("iam")
    profile = delete_instance_profile(iam)
    roles = {
        name: delete_role(iam, name)
        for name in (INSTANCE_ROLE, WATCHDOG_ROLE, SCHEDULER_ROLE)
    }
    print(json.dumps({
        "status": "CLEANUP_PASS",
        "run_id": RUN_ID,
        "region": REGION,
        "instance_type": INSTANCE_TYPE,
        "compute": compute,
        "schedules_deleted_or_absent": SCHEDULES,
        "secure_parameter": parameter,
        "watchdog_lambda": watchdog,
        "instance_profile": profile,
        "roles": roles,
        "evidence_bucket_preserved": BUCKET,
        "cloudwatch_logs_preserved": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
