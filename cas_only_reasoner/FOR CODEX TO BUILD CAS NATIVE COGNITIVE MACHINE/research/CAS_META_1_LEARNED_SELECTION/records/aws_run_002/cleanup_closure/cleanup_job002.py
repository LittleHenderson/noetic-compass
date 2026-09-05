"""Only the explicitly authorized CAS-META-1 job002 cleanup; no S3 deletion."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ACCOUNT = "807562639912"
REGION = "us-west-2"
JOB = "cas-meta1-20260905115219-33ee1c8f"
INSTANCE = "i-04ac8e28d607c2e53"
VOLUME = "vol-0c4fe87a14872b103"
GROUP = "sg-09495a2dbccdfc648"
WORKER = JOB + "-worker"
TIMER = JOB + "-timer"
ROOT = Path(__file__).resolve().parent
ABSENT = {"NoSuchEntity", "ResourceNotFoundException", "InvalidGroup.NotFound", "InvalidVolume.NotFound"}


class CleanupRefused(RuntimeError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    raw_path = ROOT / (stamp + ".provider_calls.jsonl")
    receipt_path = ROOT / (stamp + ".receipt.json")
    receipt = {"job": JOB, "instance_id": INSTANCE, "volume_id": VOLUME,
               "security_group_id": GROUP, "region": REGION, "account": ACCOUNT,
               "command": [sys.executable, *sys.argv], "python": sys.version,
               "platform": platform.platform(), "started_utc": datetime.now(timezone.utc).isoformat(),
               "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "requested_cleanup": args.cleanup, "status": "STARTED", "calls": [],
               "remaining": [], "errors": [], "s3_untouched": True,
               "original_launch_receipt_untouched": True}
    launch_receipt = ROOT.parent / "launch_receipt.json"
    receipt["original_launch_receipt_sha256"] = hashlib.sha256(launch_receipt.read_bytes()).hexdigest()
    receipt["source_sha"] = json.loads(launch_receipt.read_text(encoding="utf-8"))["source_sha"]
    config = Config(connect_timeout=10, read_timeout=20, retries={"max_attempts": 0})
    session = boto3.Session(region_name=REGION)
    clients = {name: session.client(name, config=config) for name in ("sts", "ec2", "iam", "scheduler")}

    def call(service, method, **arguments):
        event = {"utc": datetime.now(timezone.utc).isoformat(), "service": service,
                 "method": method, "arguments": arguments}
        try:
            response = getattr(clients[service], method)(**arguments)
            event["response"] = response
            return response
        except Exception as exc:
            event["exception_type"] = type(exc).__name__
            event["exception"] = str(exc)
            if isinstance(exc, ClientError): event["response"] = exc.response
            raise
        finally:
            with raw_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, sort_keys=True, default=str) + "\n")
            receipt["calls"].append({"service": service, "method": method,
                                     "utc": event["utc"], "request_id": event.get("response", {}).get("ResponseMetadata", {}).get("RequestId"),
                                     "exception": event.get("exception_type")})

    def tags(value):
        if {row["Key"]: row["Value"] for row in value.get("Tags", [])}.get("cas_meta_job") != JOB:
            raise CleanupRefused("EXACT_JOB_TAG_REQUIRED")

    def optional(service, method, **arguments):
        try:
            return call(service, method, **arguments)
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ABSENT: raise
            return None

    def volume_state():
        response = optional("ec2", "describe_volumes", VolumeIds=[VOLUME])
        if response is None: return "deleted_or_not_found"
        values = response["Volumes"]
        if len(values) != 1 or values[0]["VolumeId"] != VOLUME:
            raise CleanupRefused("UNEXPECTED_VOLUME_IDENTITY")
        tags(values[0])
        if any(a["InstanceId"] != INSTANCE for a in values[0].get("Attachments", [])):
            raise CleanupRefused("VOLUME_ATTACHED_TO_DIFFERENT_INSTANCE")
        return values[0]["State"]

    try:
        early_path = ROOT.parent.parent / "aws_run_002_provider_state_early" / "provider_state_receipt.json"
        early = json.loads(early_path.read_text(encoding="utf-8"))
        if early.get("job") != JOB or early.get("instance_id") != INSTANCE or early.get("volume_ids") != [VOLUME]:
            raise CleanupRefused("EARLY_VOLUME_SNAPSHOT_IDENTITY_MISMATCH")
        early_instance_path = early_path.parent / "raw" / "instance.json"
        if hashlib.sha256(early_instance_path.read_bytes()).hexdigest() != early["raw_response_sha256"]["raw/instance.json"]:
            raise CleanupRefused("EARLY_INSTANCE_RESPONSE_BYTES_CHANGED")
        early_response = json.loads(early_instance_path.read_text(encoding="utf-8"))["response"]
        early_instances = [i for r in early_response["Reservations"] for i in r["Instances"]]
        if len(early_instances) != 1 or early_instances[0].get("ClientToken") != JOB or early_instances[0].get("InstanceId") != INSTANCE:
            raise CleanupRefused("EARLY_INSTANCE_IDENTITY_MISMATCH")
        tags(early_instances[0])
        if [item["Ebs"]["VolumeId"] for item in early_instances[0]["BlockDeviceMappings"] if "Ebs" in item] != [VOLUME]:
            raise CleanupRefused("EARLY_ATTACHED_VOLUME_MISMATCH")
        receipt["early_snapshot_sha256"] = hashlib.sha256(early_path.read_bytes()).hexdigest()
        if call("sts", "get_caller_identity")["Account"] != ACCOUNT:
            raise CleanupRefused("WRONG_AWS_ACCOUNT")
        response = call("ec2", "describe_instances", InstanceIds=[INSTANCE])
        values = [i for reservation in response["Reservations"] for i in reservation["Instances"]]
        if len(values) != 1 or values[0]["InstanceId"] != INSTANCE:
            raise CleanupRefused("UNEXPECTED_INSTANCE_IDENTITY")
        instance = values[0]
        tags(instance)
        if instance.get("ClientToken") != JOB:
            raise CleanupRefused("EXACT_INSTANCE_CLIENT_TOKEN_REQUIRED")
        receipt["instance_state"] = instance["State"]["Name"]
        receipt["volume_state"] = volume_state()
        receipt["termination_confirmed"] = receipt["instance_state"] == "terminated"
        if not receipt["termination_confirmed"]:
            receipt["status"] = "WAITING_FOR_TERMINATION_NO_RESOURCES_REMOVED"
            receipt["remaining"] = [INSTANCE, VOLUME, JOB, WORKER, TIMER, GROUP]
            return 3
        if not args.cleanup:
            receipt["status"] = "TERMINATED_READ_ONLY_CHECK"
            return 0

        # All owned-resource deletion follows both confirmed termination and a
        # byte-verified local copy of the completed recovery evidence.
        launch = json.loads(launch_receipt.read_text(encoding="utf-8"))
        packet = ROOT.parent / "cloud_artifacts.zip"
        expected_packet = "b42598370145843182515afe202a2b340e14d9a248517b4e35d62bc4daaa541e"
        if (launch.get("job") != JOB or launch.get("result", {}).get("job") != JOB
                or launch["result"].get("returncode") != 0
                or launch["result"].get("sha256") != expected_packet
                or packet.stat().st_size != launch["result"].get("bytes")
                or hashlib.sha256(packet.read_bytes()).hexdigest() != expected_packet):
            raise CleanupRefused("VERIFIED_LOCAL_RECOVERY_PACKET_REQUIRED")
        receipt["verified_local_packet_sha256"] = expected_packet

        # Scheduler schedules do not carry per-schedule tags. Validate its exact
        # recorded name, job role, and sole instance target before removal.
        schedule = optional("scheduler", "get_schedule", Name=JOB)
        if schedule is not None:
            target = schedule["Target"]
            if (schedule["Name"] != JOB
                    or target["Arn"] != "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances"
                    or target["RoleArn"] != f"arn:aws:iam::{ACCOUNT}:role/{TIMER}"
                    or json.loads(target["Input"]) != {"InstanceIds": [INSTANCE]}):
                raise CleanupRefused("SCHEDULE_JOB_TARGET_MISMATCH")
            call("scheduler", "delete_schedule", Name=JOB)

        profile = optional("iam", "get_instance_profile", InstanceProfileName=WORKER)
        if profile is not None:
            profile = profile["InstanceProfile"]
            tags(profile)
            if profile["Arn"] != f"arn:aws:iam::{ACCOUNT}:instance-profile/{WORKER}":
                raise CleanupRefused("PROFILE_ARN_MISMATCH")
            if any(role["RoleName"] != WORKER for role in profile["Roles"]):
                raise CleanupRefused("PROFILE_HAS_UNRELATED_ROLE")
            if profile["Roles"]:
                worker = call("iam", "get_role", RoleName=WORKER)["Role"]
                tags(worker)
                call("iam", "remove_role_from_instance_profile", InstanceProfileName=WORKER, RoleName=WORKER)
            call("iam", "delete_instance_profile", InstanceProfileName=WORKER)

        for role_name in (WORKER, TIMER):
            role = optional("iam", "get_role", RoleName=role_name)
            if role is None: continue
            tags(role["Role"])
            if role["Role"]["Arn"] != f"arn:aws:iam::{ACCOUNT}:role/{role_name}":
                raise CleanupRefused("ROLE_ARN_MISMATCH")
            policies = call("iam", "list_role_policies", RoleName=role_name)
            attached = call("iam", "list_attached_role_policies", RoleName=role_name)
            if policies.get("IsTruncated") or attached.get("IsTruncated") or attached["AttachedPolicies"]:
                raise CleanupRefused("UNEXPECTED_ROLE_POLICY_ATTACHMENTS")
            if any(name != "job-only" for name in policies["PolicyNames"]):
                raise CleanupRefused("UNEXPECTED_INLINE_ROLE_POLICY")
            if "job-only" in policies["PolicyNames"]:
                call("iam", "get_role_policy", RoleName=role_name, PolicyName="job-only")
                call("iam", "delete_role_policy", RoleName=role_name, PolicyName="job-only")
            call("iam", "delete_role", RoleName=role_name)

        group = optional("ec2", "describe_security_groups", GroupIds=[GROUP])
        if group is not None:
            values = group["SecurityGroups"]
            if len(values) != 1 or values[0]["GroupId"] != GROUP or values[0]["OwnerId"] != ACCOUNT or values[0]["GroupName"] != JOB:
                raise CleanupRefused("SECURITY_GROUP_IDENTITY_MISMATCH")
            tags(values[0])
            call("ec2", "delete_security_group", GroupId=GROUP)

        volume = optional("ec2", "describe_volumes", VolumeIds=[VOLUME])
        if volume is not None:
            values = volume["Volumes"]
            if len(values) != 1 or values[0]["VolumeId"] != VOLUME:
                raise CleanupRefused("UNEXPECTED_VOLUME_IDENTITY")
            tags(values[0])
            if values[0].get("Attachments"):
                raise CleanupRefused("SCRATCH_VOLUME_STILL_ATTACHED")
            if values[0]["State"] == "available":
                call("ec2", "delete_volume", VolumeId=VOLUME)
                receipt["dedicated_scratch_volume_delete_requested"] = True

        for service, method, arguments, identity in (
            ("scheduler", "get_schedule", {"Name": JOB}, JOB),
            ("iam", "get_instance_profile", {"InstanceProfileName": WORKER}, WORKER + ":profile"),
            ("iam", "get_role", {"RoleName": WORKER}, WORKER),
            ("iam", "get_role", {"RoleName": TIMER}, TIMER),
            ("ec2", "describe_security_groups", {"GroupIds": [GROUP]}, GROUP),
        ):
            if optional(service, method, **arguments) is not None:
                receipt["remaining"].append(identity)
        receipt["volume_state"] = volume_state()
        if receipt["volume_state"] != "deleted_or_not_found": receipt["remaining"].append(VOLUME)
        receipt["status"] = "CLEANUP_CLOSED_EVIDENCE_RETAINED" if not receipt["remaining"] else "CLEANUP_STILL_PENDING"
        return 0 if not receipt["remaining"] else 2
    except Exception as exc:
        receipt["status"] = "CLEANUP_REQUIRES_ATTENTION"
        receipt["errors"].append({"type": type(exc).__name__, "message": str(exc)})
        return 1
    finally:
        receipt["completed_utc"] = datetime.now(timezone.utc).isoformat()
        receipt["provider_calls_file"] = raw_path.name
        if raw_path.exists(): receipt["provider_calls_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        receipt["original_launch_receipt_unchanged"] = hashlib.sha256(launch_receipt.read_bytes()).hexdigest() == receipt["original_launch_receipt_sha256"]
        receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps({"status": receipt["status"], "instance_state": receipt.get("instance_state"),
                          "volume_state": receipt.get("volume_state"), "remaining": receipt["remaining"],
                          "errors": receipt["errors"], "receipt": str(receipt_path)}))


if __name__ == "__main__":
    raise SystemExit(main())
