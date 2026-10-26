#!/usr/bin/env python3
"""Prove the v5 Stage S AWS watchdog on a short-lived, non-public sentinel."""
import datetime as dt
import decimal
import hashlib
import json
import math
import pathlib
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

REGION = "us-west-2"
ACCOUNT = "807562639912"
BUCKET = "cas-harness-runpod-92754088"
RUN_ID = "typed-probe-v5-stage-s-transformers-retry-20261025"
RUN_PREFIX = f"typed_probe_v5_20261025/{RUN_ID}"
PROOF_KEY = RUN_PREFIX + "/provenance/watchdog_proof.json"
SCRIPT_KEY = RUN_PREFIX + "/provenance/watchdog_e2e_proof_transformers_retry.py"
FUNCTION = "typed-probe-v5-stage-s-watchdog-transformers-retry-20261025"
WATCHDOG_ROLE = "typed-probe-v5-stage-s-watchdog-role-transformers-retry-20261025"
TAG_KEY = "typed-probe-v5-run-id"
INSTANCE_TYPE = "t3.nano"
MAX_SECONDS = 300
EXPECTED_PRIOR_SECONDS = 213
EXPECTED_REMAINING_SECONDS = 87
ROOT_GIB = 8
SUBNET_ID = "subnet-0eb3ca4bf5ca98f24"
SECURITY_GROUP_ID = "sg-0562c483e0364cdab"
AMI_PARAMETER = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
ROOT = pathlib.Path(__file__).resolve().parent


def client(service, region=REGION):
    return boto3.client(service, region_name=region)


def single_attempt_ec2_client():
    return boto3.client(
        "ec2", region_name=REGION,
        config=Config(retries={"total_max_attempts": 1, "mode": "standard"}),
    )


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def watchdog_sha256():
    return sha256((ROOT / "cloud_watchdog.py").read_bytes())


def check_timed_smoke(logs):
    deadline = time.monotonic() + 240
    group = f"/aws/lambda/{FUNCTION}"
    while time.monotonic() < deadline:
        response = logs.filter_log_events(
            logGroupName=group,
            startTime=int((utc_now() - dt.timedelta(minutes=10)).timestamp() * 1000),
            filterPattern="scheduler_smoke",
            limit=50,
        )
        for event in response.get("events", []):
            message = event.get("message", "")
            if (RUN_ID in message and "event_kind': 'scheduler_smoke'" in message
                    and "found': 0" in message and "terminated': 0" in message):
                return event.get("timestamp")
        time.sleep(5)
    raise RuntimeError("timed AWS Scheduler watchdog smoke did not pass within 240 seconds")


def simulate_tag_policy(iam):
    role_arn = f"arn:aws:iam::{ACCOUNT}:role/{WATCHDOG_ROLE}"
    instance_arn = f"arn:aws:ec2:{REGION}:{ACCOUNT}:instance/i-0123456789abcdef0"
    context_key = f"ec2:ResourceTag/{TAG_KEY}"
    outcomes = {}
    for label, value, expected in (
        ("exact_run_tag", RUN_ID, "allowed"),
        ("different_run_tag", RUN_ID + "-other", "implicitDeny"),
    ):
        result = iam.simulate_principal_policy(
            PolicySourceArn=role_arn,
            ActionNames=["ec2:TerminateInstances"],
            ResourceArns=[instance_arn],
            ContextEntries=[{
                "ContextKeyName": context_key,
                "ContextKeyValues": [value],
                "ContextKeyType": "string",
            }],
        )
        decision = result["EvaluationResults"][0]["EvalDecision"]
        outcomes[label] = decision
        if decision != expected:
            raise RuntimeError(f"watchdog IAM tag check {label} returned {decision}")
    return outcomes


def describe_instance_retry(ec2, instance_id, deadline):
    while True:
        try:
            return ec2.describe_instances(InstanceIds=[instance_id])
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code != "InvalidInstanceID.NotFound" or time.monotonic() >= deadline:
                raise
            time.sleep(3)

def wait_for_state(ec2, instance_id, wanted, deadline):
    while time.monotonic() < deadline:
        response = describe_instance_retry(ec2, instance_id, deadline)
        instances = [i for r in response.get("Reservations", []) for i in r.get("Instances", [])]
        if not instances:
            if wanted == "terminated":
                return None
            raise RuntimeError("watchdog sentinel disappeared before reaching running state")
        instance = instances[0]
        state = instance.get("State", {}).get("Name")
        if state == wanted:
            return instance
        if state == "terminated" and wanted != "terminated":
            raise RuntimeError("watchdog terminated the sentinel before the proof invocation")
        time.sleep(5)
    raise RuntimeError(f"sentinel did not reach {wanted} before its 300-second limit")


def volume_is_gone(ec2, volume_id, deadline):
    while time.monotonic() < deadline:
        try:
            response = ec2.describe_volumes(VolumeIds=[volume_id])
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"InvalidVolume.NotFound", "InvalidVolume.NotFoundException"}:
                return True
            raise
        volumes = response.get("Volumes", [])
        if not volumes:
            return True
        if all(volume.get("State") == "deleted" for volume in volumes):
            return True
        time.sleep(5)
    return False


def upload_receipt(s3, receipt):
    proof_script = (ROOT / "watchdog_e2e_proof_transformers_retry.py").read_bytes()
    s3.put_object(Bucket=BUCKET, Key=SCRIPT_KEY, Body=proof_script,
                  ContentType="text/x-python", ServerSideEncryption="AES256",
                  Metadata={"sha256": sha256(proof_script)})
    setup_script = (ROOT / "cloud_setup_stage_s.py").read_bytes()
    s3.put_object(Bucket=BUCKET, Key=RUN_PREFIX + "/provenance/cloud_setup_stage_s.py",
                  Body=setup_script, ContentType="text/x-python", ServerSideEncryption="AES256",
                  Metadata={"sha256": sha256(setup_script)})
    body = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    s3.put_object(
        Bucket=BUCKET,
        Key=PROOF_KEY,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
        Metadata={"sha256": sha256(body)},
    )


def read_previous_sentinel_seconds(s3, ec2):
    old_run_ids = [
        "typed-probe-v5-stage-s-retry1-20261025-0400z",
        "typed-probe-v5-stage-s-retry2-20261025-0430z",
        "typed-probe-v5-stage-s-capacity-retry-20261025",
        "typed-probe-v5-stage-s-capacity-retry2-20261025",
    ]
    for old_run_id in old_run_ids:
        active = ec2.describe_instances(Filters=[
            {"Name": f"tag:{TAG_KEY}", "Values": [old_run_id]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped", "shutting-down"]},
        ])
        if any(r.get("Instances") for r in active.get("Reservations", [])):
            raise RuntimeError(f"a previous v5 instance is still active: {old_run_id}")
        volumes = ec2.describe_volumes(Filters=[
            {"Name": f"tag:{TAG_KEY}", "Values": [old_run_id]}
        ]).get("Volumes", [])
        if volumes:
            raise RuntimeError(f"a disk from a previous v5 run still exists: {old_run_id}")

    prior_receipts = [
        ("typed-probe-v5-stage-s-retry1-20261025-0400z", "provenance/watchdog_proof.json", 17, "FAIL"),
        ("typed-probe-v5-stage-s-retry1-20261025-0400z", "provenance/watchdog_proof_attempt2.json", 13, "FAIL"),
        ("typed-probe-v5-stage-s-retry1-20261025-0400z", "provenance/watchdog_proof_attempt3.json", 49, "PASS"),
        ("typed-probe-v5-stage-s-retry2-20261025-0430z", "provenance/watchdog_proof.json", 54, "PASS"),
        ("typed-probe-v5-stage-s-capacity-retry-20261025", "provenance/watchdog_proof.json", 32, "PASS"),
        ("typed-probe-v5-stage-s-capacity-retry2-20261025", "provenance/watchdog_proof.json", 48, "PASS"),
    ]
    total_seconds = 0
    for old_run_id, relative_key, expected_seconds, expected_status in prior_receipts:
        key = f"typed_probe_v5_20261025/{old_run_id}/{relative_key}"
        response = s3.get_object(Bucket=BUCKET, Key=key)
        body = response["Body"].read()
        if response.get("Metadata", {}).get("sha256") != sha256(body):
            raise RuntimeError(f"a prior watchdog receipt has a bad S3 hash: {key}")
        receipt = json.loads(body.decode("utf-8"))
        if (receipt.get("run_id") != old_run_id
                or receipt.get("tracked_ec2_seconds") != expected_seconds
                or receipt.get("status") != expected_status):
            raise RuntimeError(f"a prior watchdog receipt does not match the frozen count: {key}")
        total_seconds += expected_seconds
    if total_seconds != EXPECTED_PRIOR_SECONDS:
        raise RuntimeError(f"prior watchdog time is {total_seconds}, expected {EXPECTED_PRIOR_SECONDS} seconds")
    return total_seconds

def wait_for_volume_attachment(ec2, instance_id, deadline):
    while time.monotonic() < deadline:
        response = describe_instance_retry(ec2, instance_id, deadline)
        instances = [i for r in response.get("Reservations", []) for i in r.get("Instances", [])]
        if instances and instances[0].get("BlockDeviceMappings"):
            return instances[0]
        time.sleep(2)
    raise RuntimeError("sentinel root disk did not attach within the proof window")

def main():
    identity = client("sts").get_caller_identity()
    if identity.get("Account") != ACCOUNT:
        raise RuntimeError("AWS identity is not the frozen v5 project account")

    s3 = client("s3")
    manifest_object = s3.get_object(Bucket=BUCKET, Key=RUN_PREFIX + "/input/input_manifest.json")
    manifest = json.loads(manifest_object["Body"].read().decode("utf-8"))
    if manifest.get("run_id") != RUN_ID:
        raise RuntimeError("prepared S3 manifest has the wrong v5 run ID")
    direct_smoke = manifest.get("watchdog_direct_smoke", {})
    if direct_smoke.get("found") != 0 or direct_smoke.get("terminated") != 0:
        raise RuntimeError("direct AWS watchdog smoke did not record zero targets")
    ec2 = client("ec2")
    prior_watchdog_ec2_seconds = read_previous_sentinel_seconds(s3, ec2)
    remaining_seconds = MAX_SECONDS - prior_watchdog_ec2_seconds
    if (prior_watchdog_ec2_seconds != EXPECTED_PRIOR_SECONDS
            or remaining_seconds != EXPECTED_REMAINING_SECONDS):
        raise RuntimeError("verified watchdog seconds do not match the remaining owner limit")

    lambdas = client("lambda")
    configuration = lambdas.get_function_configuration(FunctionName=FUNCTION)
    expected_role = f"arn:aws:iam::{ACCOUNT}:role/{WATCHDOG_ROLE}"
    if (configuration.get("State") != "Active"
            or configuration.get("LastUpdateStatus") != "Successful"
            or configuration.get("Role") != expected_role
            or configuration.get("Environment", {}).get("Variables", {}).get("STAGE_S_RUN_ID") != RUN_ID):
        raise RuntimeError("deployed watchdog configuration does not match this v5 run")
    current_watchdog_hash = watchdog_sha256()
    if manifest.get("watchdog_sha256") != current_watchdog_hash:
        raise RuntimeError("deployed watchdog source hash differs from the prepared manifest")

    scheduler_log_timestamp = check_timed_smoke(client("logs"))
    iam_results = simulate_tag_policy(client("iam"))

    ssm = client("ssm")
    ami_id = ssm.get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
    image = ec2.describe_images(ImageIds=[ami_id])["Images"][0]
    if image.get("OwnerId") != "137112412989" or not image.get("RootDeviceName"):
        raise RuntimeError("Amazon Linux sentinel image ownership or root disk could not be verified")
    subnet = ec2.describe_subnets(SubnetIds=[SUBNET_ID])["Subnets"][0]
    if subnet.get("AvailabilityZone") != "us-west-2c":
        raise RuntimeError("sentinel subnet is not the frozen us-west-2c zone")
    security_group = ec2.describe_security_groups(GroupIds=[SECURITY_GROUP_ID])["SecurityGroups"][0]
    if security_group.get("IpPermissions"):
        raise RuntimeError("sentinel security group has inbound access")
    active = ec2.describe_instances(
        Filters=[
            {"Name": f"tag:{TAG_KEY}", "Values": [RUN_ID]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )
    if any(r.get("Instances") for r in active.get("Reservations", [])):
        raise RuntimeError("an instance with the Stage S run tag is already active")

    armed_body = json.dumps({
        "run_id": RUN_ID, "purpose": "one exact-tag watchdog proof attempt",
        "created_at_utc": utc_now().isoformat(), "remaining_ec2_seconds": remaining_seconds,
    }, sort_keys=True).encode("utf-8")
    try:
        s3.put_object(
            Bucket=BUCKET, Key=RUN_PREFIX + "/provenance/watchdog_proof_attempt_armed.json",
            Body=armed_body, ContentType="application/json", ServerSideEncryption="AES256",
            Metadata={"sha256": sha256(armed_body)}, IfNoneMatch="*",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"PreconditionFailed", "ConditionalRequestConflict", "412"}:
            raise RuntimeError("the single authorized watchdog proof attempt is already consumed") from None
        raise

    proof_instance = None
    volume_id = None
    invoke_result = None
    launch_time = None
    start_monotonic = None
    invoke_at = None
    terminated_at = None
    volume_deleted = False
    failure = None
    try:
        start_monotonic = time.monotonic()
        launch_response = single_attempt_ec2_client().run_instances(
            ImageId=ami_id,
            InstanceType=INSTANCE_TYPE,
            MinCount=1,
            MaxCount=1,
            NetworkInterfaces=[{
                "DeviceIndex": 0,
                "SubnetId": SUBNET_ID,
                "Groups": [SECURITY_GROUP_ID],
                "AssociatePublicIpAddress": False,
                "DeleteOnTermination": True,
            }],
            BlockDeviceMappings=[{
                "DeviceName": image["RootDeviceName"],
                "Ebs": {
                    "VolumeSize": ROOT_GIB,
                    "VolumeType": "gp3",
                    "Encrypted": True,
                    "DeleteOnTermination": True,
                },
            }],
            InstanceInitiatedShutdownBehavior="terminate",
            MetadataOptions={"HttpEndpoint": "enabled", "HttpTokens": "required", "HttpPutResponseHopLimit": 1},
            TagSpecifications=[
                {"ResourceType": "instance", "Tags": [
                    {"Key": "Name", "Value": "typed-probe-v5-watchdog-proof"},
                    {"Key": TAG_KEY, "Value": RUN_ID},
                    {"Key": "Project", "Value": "typed-probe-v5"},
                    {"Key": "Stage", "Value": "watchdog-proof"},
                ]},
                {"ResourceType": "volume", "Tags": [
                    {"Key": TAG_KEY, "Value": RUN_ID},
                    {"Key": "Project", "Value": "typed-probe-v5"},
                    {"Key": "Stage", "Value": "watchdog-proof"},
                ]},
            ],
        )
        proof_instance = launch_response["Instances"][0]
        instance_id = proof_instance["InstanceId"]
        launch_time = proof_instance["LaunchTime"].astimezone(dt.timezone.utc).isoformat()
        running = wait_for_state(ec2, instance_id, "running", start_monotonic + min(180, remaining_seconds))
        running = wait_for_volume_attachment(ec2, instance_id, start_monotonic + min(180, remaining_seconds))
        proof_instance = running
        if running.get("PublicIpAddress") or running.get("PublicDnsName"):
            raise RuntimeError("sentinel unexpectedly received a public IP or DNS name")
        mappings = running.get("BlockDeviceMappings", [])
        if len(mappings) != 1 or mappings[0].get("Ebs", {}).get("DeleteOnTermination") is not True:
            raise RuntimeError("sentinel root disk is missing or lacks DeleteOnTermination")
        volume_id = mappings[0]["Ebs"]["VolumeId"]

        invoke_at = utc_now().isoformat()
        response = lambdas.invoke(
            FunctionName=FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps({"test_kind": "live_target_proof"}).encode("utf-8"),
        )
        invoke_body = response["Payload"].read().decode("utf-8")
        if response.get("FunctionError") or response.get("StatusCode") != 200:
            raise RuntimeError("watchdog Lambda invocation failed on the live sentinel")
        invoke_result = json.loads(invoke_body)
        if (invoke_result.get("run_id") != RUN_ID
                or invoke_result.get("found") != 1
                or invoke_result.get("terminated") != 1
                or invoke_result.get("states") != ["running"]):
            raise RuntimeError("watchdog did not select and terminate exactly the running sentinel")

        end_deadline = start_monotonic + remaining_seconds
        wait_for_state(ec2, instance_id, "terminated", end_deadline)
        terminated_at = utc_now().isoformat()
        elapsed = math.ceil(time.monotonic() - start_monotonic)
        volume_deleted = volume_is_gone(ec2, volume_id, end_deadline)
        if not volume_deleted:
            raise RuntimeError("sentinel root disk was not deleted on termination")
        if elapsed > remaining_seconds:
            raise RuntimeError("sentinel exceeded the remaining cumulative 300-second maximum")
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        try:
            if proof_instance is None and start_monotonic is not None:
                response = ec2.describe_instances(Filters=[
                    {"Name": f"tag:{TAG_KEY}", "Values": [RUN_ID]},
                    {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
                ])
                found = [i for r in response.get("Reservations", []) for i in r.get("Instances", [])]
                if found:
                    proof_instance = found[0]
                    mappings = proof_instance.get("BlockDeviceMappings", [])
                    if mappings:
                        volume_id = mappings[0].get("Ebs", {}).get("VolumeId")
            if proof_instance:
                instance_id = proof_instance["InstanceId"]
                if proof_instance.get("State", {}).get("Name") not in {"shutting-down", "terminated"}:
                    ec2.terminate_instances(InstanceIds=[instance_id])
                cleanup_deadline = max(start_monotonic + remaining_seconds, time.monotonic() + 15)
                wait_for_state(ec2, instance_id, "terminated", cleanup_deadline)
                if volume_id:
                    volume_deleted = volume_is_gone(ec2, volume_id, time.monotonic() + 45)
        except Exception as cleanup_exc:
            failure += f"; cleanup: {type(cleanup_exc).__name__}: {cleanup_exc}"
        terminated_at = utc_now().isoformat() if proof_instance else None

    elapsed_seconds = (math.ceil(time.monotonic() - start_monotonic)
                       if start_monotonic is not None else 0)
    cumulative_seconds = prior_watchdog_ec2_seconds + elapsed_seconds
    if cumulative_seconds > MAX_SECONDS:
        failure = failure or "watchdog proof attempts exceeded the cumulative 300-second limit"
    receipt = {
        "status": "PASS" if failure is None else "FAIL",
        "run_id": RUN_ID,
        "aws_account_id": ACCOUNT,
        "verified_at_utc": utc_now().isoformat(),
        "watchdog_function": FUNCTION,
        "watchdog_sha256": current_watchdog_hash,
        "proof_script_sha256": sha256((ROOT / "watchdog_e2e_proof_transformers_retry.py").read_bytes()),
        "prior_watchdog_ec2_seconds": prior_watchdog_ec2_seconds,
        "cumulative_watchdog_ec2_seconds": cumulative_seconds,
        "direct_smoke": direct_smoke,
        "scheduler_smoke_log_timestamp_ms": scheduler_log_timestamp,
        "iam_tag_policy_results": iam_results,
        "instance_type": INSTANCE_TYPE,
        "ami_id": ami_id,
        "instance_id": proof_instance.get("InstanceId") if proof_instance else None,
        "launch_time_utc": launch_time,
        "watchdog_invoked_at_utc": invoke_at,
        "terminated_observed_at_utc": terminated_at,
        "tracked_ec2_seconds": elapsed_seconds,
        "max_ec2_seconds": remaining_seconds,
        "cumulative_max_ec2_seconds": MAX_SECONDS,
        "no_public_ip": bool(proof_instance and not proof_instance.get("PublicIpAddress")),
        "root_volume_id": volume_id,
        "root_volume_gib": ROOT_GIB,
        "root_volume_deleted": volume_deleted,
        "lambda_watchdog_result": invoke_result,
        "failure": failure,
    }
    upload_receipt(s3, receipt)
    print(json.dumps({
        "status": receipt["status"],
        "run_id": RUN_ID,
        "instance_id": receipt["instance_id"],
        "tracked_ec2_seconds": elapsed_seconds,
        "root_volume_deleted": volume_deleted,
        "proof_s3_key": PROOF_KEY,
        "failure": failure,
    }, sort_keys=True))
    if failure:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
