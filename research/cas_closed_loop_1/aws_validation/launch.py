"""One explicitly frozen CPU job. Importing this file never calls AWS.

No launch retry. Evidence is downloaded before job resources are removed.
"""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path
import re
import time
import traceback

HERE = Path(__file__).resolve().parent
EXPECTED_SOURCE = "318b22ad01304f80ed0f539420792cc951fe297a"


def utc():
    return datetime.datetime.now(datetime.timezone.utc)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def userdata(plan, download_url, failure_url, evidence_url):
    # Do not persist or print presigned URLs; they are limited to this job's objects.
    bootstrap = '''import hashlib,json,os,pathlib,subprocess,sys,urllib.request,zipfile
root=pathlib.Path('/opt/cas-job');root.mkdir(exist_ok=False)
try:
    with urllib.request.urlopen(DOWNLOAD,timeout=30) as response: raw=response.read(64*1024*1024+1)
    if len(raw)>64*1024*1024 or hashlib.sha256(raw).hexdigest()!=DIGEST: raise ValueError('PAYLOAD_IDENTITY')
    archive=root/'payload.zip';archive.write_bytes(raw)
    with zipfile.ZipFile(archive) as stream:
        for row in stream.infolist():
            if not (root/row.filename).resolve().is_relative_to(root.resolve()): raise ValueError('UNSAFE_ARCHIVE')
        stream.extractall(root)
    code=subprocess.call([sys.executable,str(root/'research/cas_closed_loop_1/aws_validation/worker.py'),'--bucket',BUCKET,'--region',REGION])
    if code: raise RuntimeError('WORKER_FAILED')
except BaseException as exc:
    failure=json.dumps({'status':'BOOTSTRAP_OR_WORKER_FAILED','error_type':type(exc).__name__,'code':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else None}).encode()
    archive=root/'outputs.tar.gz'
    if archive.is_file() and archive.stat().st_size<=32*1024*1024:
        try: urllib.request.urlopen(urllib.request.Request(EVIDENCE,data=archive.read_bytes(),method='PUT'),timeout=30).close()
        except BaseException: pass
    try: urllib.request.urlopen(urllib.request.Request(FAILURE,data=failure,method='PUT'),timeout=30).close()
    except BaseException: pass
    raise SystemExit(1)
'''
    assignments = {"DOWNLOAD": download_url, "FAILURE": failure_url, "EVIDENCE": evidence_url, "DIGEST": plan["payload_sha256"],
                   "BUCKET": plan["job_id"] + "-" + plan["account_id"], "REGION": plan["region"]}
    source = "\n".join(name + "=" + repr(value) for name, value in assignments.items()) + "\n" + bootstrap
    encoded = base64.b64encode(source.encode()).decode()
    return ("#!/bin/bash\n/sbin/shutdown -h +18 || exit 91\nset -eu\n"
            "export PYTHONDONTWRITEBYTECODE=1\n"
            "python3 - <<'CAS_BOOTSTRAP'\nimport base64\nexec(compile(base64.b64decode('" + encoded + "'),'<job-bootstrap>','exec'))\nCAS_BOOTSTRAP\n")


def execute(directory, expected_hash):
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    directory = directory.resolve()
    frozen = (directory / "freeze.json").read_bytes()
    if sha(frozen) != expected_hash:
        raise ValueError("FROZEN_RECORD_HASH_REQUIRED")
    plan = json.loads(frozen)
    for field, expected in {"source_commit": EXPECTED_SOURCE, "runner": "Codex", "jobs": 1,
                           "retry_count": 0, "maximum_all_services_usd": "1.00", "hard_wall_seconds": 1200,
                           "instance_type": "t3.small", "cpu_credits": "standard", "root_gib": 8,
                           "region": "us-west-2", "account_id": "807562639912"}.items():
        if plan[field] != expected:
            raise ValueError("FROZEN_ENVELOPE_DIFFERS:" + field)
    if sha((HERE / "launch.py").read_bytes()) != plan["launcher_sha256"]:
        raise ValueError("LAUNCHER_CHANGED_AFTER_FREEZE")
    payload = (directory / plan["payload_file"]).read_bytes()
    if sha(payload) != plan["payload_sha256"] or len(payload) != plan["payload_bytes"]:
        raise ValueError("PAYLOAD_CHANGED_AFTER_FREEZE")
    # Atomic local ownership: subsequent execute attempts are always refused.
    with (directory / "ATTEMPT_STARTED.json").open("x", encoding="utf-8") as stream:
        json.dump({"freeze_sha256": expected_hash, "utc": utc().isoformat(), "retry_count": 0}, stream)
    session = boto3.Session(profile_name=plan["sdk_profile"], region_name=plan["region"])
    config = Config(retries={"total_max_attempts": 1}, connect_timeout=5, read_timeout=30)
    def client(name, region=None):
        selected = config.merge(Config(signature_version="s3v4")) if name == "s3" else config
        return session.client(name, region_name=region or plan["region"], config=selected)
    ec2, iam, s3, scheduler = (client(name) for name in ("ec2", "iam", "s3", "scheduler"))
    job = plan["job_id"]
    bucket = job + "-" + plan["account_id"]
    role, profile, watchdog_role = job + "-worker", job + "-worker", job + "-watchdog"
    tag = [{"Key": "CASJob", "Value": job}, {"Key": "Runner", "Value": "Codex"}]
    state = {"schema": "cas.cpu.aws.execution/1", "job_id": job, "freeze_sha256": expected_hash,
             "source_commit": plan["source_commit"], "payload_sha256": plan["payload_sha256"],
             "runner": "Codex", "start_utc": utc().isoformat(), "resources": {}, "cleanup": [],
             "status": "PRELAUNCH", "cloud_calls_retry_count": 0, "maximum_all_services_usd": "1.00"}
    secret_strings = []
    last_heartbeat = 0.0
    def redact(value):
        if isinstance(value, dict):
            return {k: redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [redact(v) for v in value]
        if isinstance(value, str):
            for secret in sorted(secret_strings, key=len, reverse=True):
                value = value.replace(secret, "[REDACTED_JOB_BOOTSTRAP_TOKEN]")
        return value
    def heartbeat(status="PROGRESS", force=False):
        nonlocal last_heartbeat
        if not force and time.monotonic() - last_heartbeat < 90:
            return
        row = {"utc": utc().isoformat(), "agent": "Codex", "status": status,
               "current_task": "CAS-CLOSED-LOOP-1 single AWS CPU validation: " + job,
               "work_done_since_last_heartbeat": state["status"],
               "blocker": state.get("error"), "next_action": "Observe frozen job; retain evidence and confirm cleanup",
               "relevant_commit_or_file": str(directory / "execution.json"),
               "paid_cloud_work_active": bool(state.get("launch_attempted") and not state.get("instance_terminal")),
               "instance_id": state["resources"].get("instance_id")}
        path = Path("D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination/codex_heartbeat.jsonl")
        try:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(redact(row)) + "\n")
        except OSError as exc:
            state["heartbeat_delivery_error"] = type(exc).__name__
        last_heartbeat = time.monotonic()
    evidence = directory / "evidence"
    evidence.mkdir(exist_ok=False)
    def save():
        heartbeat()
        (directory / "execution.json").write_text(json.dumps(redact(state), indent=2, default=str) + "\n")
    def owned(name, value):
        state["resources"][name] = value
        save()
    def action(name, function):
        try:
            value = function()
            state["cleanup"].append({"action": name, "status": "PASS"})
            save()
            return value
        except BaseException as exc:
            state["cleanup"].append({"action": name, "status": "FAILED", "error_type": type(exc).__name__, "error": str(exc)})
            save()
            return None
    def trust(service):
        return json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Allow",
            "Principal": {"Service": service}, "Action": "sts:AssumeRole"}]})
    instance_id = None
    terminal = None
    launched_at = None
    cleanup_safe = True
    heartbeat("START", force=True)
    try:
        identity = client("sts").get_caller_identity()
        if identity["Account"] != plan["account_id"]:
            raise ValueError("WRONG_AWS_ACCOUNT")
        state["caller_arn"] = identity["Arn"]
        # Fresh global one-machine check. Any unobserved region or active machine blocks.
        checks = []
        for region in ec2.describe_regions(AllRegions=False)["Regions"]:
            regional = client("ec2", region["RegionName"])
            token = None
            active = []
            while True:
                kwargs = {"Filters": [{"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "shutting-down"]}]}
                if token:
                    kwargs["NextToken"] = token
                data = regional.describe_instances(**kwargs)
                active.extend(i["InstanceId"] for r in data["Reservations"] for i in r["Instances"])
                token = data.get("NextToken")
                if not token:
                    break
            checks.append({"region": region["RegionName"], "active_instances": active})
            heartbeat()
            if active:
                raise ValueError("ONE_MACHINE_CONCURRENCY_BLOCK")
        state["global_concurrency"] = checks
        save()
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": plan["region"]})
        owned("bucket", bucket)
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
        s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tag})
        s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={"Rules": [{
            "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})
        s3.put_object(Bucket=bucket, Key="inputs/payload.zip", Body=payload)
        iam.create_role(RoleName=role, AssumeRolePolicyDocument=trust("ec2.amazonaws.com"), Tags=tag)
        owned("worker_role", role)
        iam.put_role_policy(RoleName=role, PolicyName="job-objects", PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [
            {"Effect": "Allow", "Action": "s3:GetObject", "Resource": f"arn:aws:s3:::{bucket}/inputs/payload.zip"},
            {"Effect": "Allow", "Action": "s3:PutObject", "Resource": f"arn:aws:s3:::{bucket}/outputs/*"}]}))
        owned("worker_policy", "job-objects")
        iam.create_instance_profile(InstanceProfileName=profile, Tags=tag)
        owned("profile", profile)
        iam.add_role_to_instance_profile(InstanceProfileName=profile, RoleName=role)
        owned("profile_role", role)
        iam.create_role(RoleName=watchdog_role, AssumeRolePolicyDocument=trust("scheduler.amazonaws.com"), Tags=tag)
        owned("watchdog_role", watchdog_role)
        iam.put_role_policy(RoleName=watchdog_role, PolicyName="tagged-termination", PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [{
            "Effect": "Allow", "Action": "ec2:TerminateInstances", "Resource": f"arn:aws:ec2:{plan['region']}:{plan['account_id']}:instance/*",
            "Condition": {"StringEquals": {"ec2:ResourceTag/CASJob": job}}}]}))
        owned("watchdog_policy", "tagged-termination")
        sg = ec2.create_security_group(GroupName=job, Description="Single frozen public CAS CPU job", VpcId=plan["vpc_id"],
                                       TagSpecifications=[{"ResourceType": "security-group", "Tags": tag}])["GroupId"]
        owned("security_group", sg)
        permissions = ec2.describe_security_groups(GroupIds=[sg])["SecurityGroups"][0]["IpPermissionsEgress"]
        if permissions:
            ec2.revoke_security_group_egress(GroupId=sg, IpPermissions=permissions)
        ec2.authorize_security_group_egress(GroupId=sg, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
                                                                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        # A single bounded propagation delay, not a repeated failed launch.
        time.sleep(15)
        download_url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": "inputs/payload.zip"}, ExpiresIn=1500)
        failure_url = s3.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": "outputs/bootstrap_failure.json"}, ExpiresIn=1500)
        evidence_url = s3.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": "outputs/emergency_evidence.tar.gz"}, ExpiresIn=1500)
        secret_strings.extend((download_url, failure_url, evidence_url))
        data = userdata(plan, download_url, failure_url, evidence_url)
        secret_strings.append(data)
        secret_strings.extend(re.findall(r"b64decode\('([^']+)'\)", data))
        if len(data.encode()) > 16384:
            raise ValueError("USER_DATA_SIZE_LIMIT")
        request = {"ImageId": plan["ami"], "InstanceType": plan["instance_type"], "MinCount": 1, "MaxCount": 1,
            "ClientToken": job, "Placement": {"AvailabilityZone": plan["zone"]},
            "NetworkInterfaces": [{"DeviceIndex": 0, "SubnetId": plan["subnet_id"], "Groups": [sg], "AssociatePublicIpAddress": True, "DeleteOnTermination": True}],
            "IamInstanceProfile": {"Name": profile}, "CreditSpecification": {"CpuCredits": "standard"},
            "MetadataOptions": {"HttpTokens": "required", "HttpEndpoint": "enabled", "HttpPutResponseHopLimit": 1},
            "InstanceInitiatedShutdownBehavior": "terminate", "DisableApiTermination": False,
            "BlockDeviceMappings": [{"DeviceName": plan["root_device"], "Ebs": {"VolumeSize": 8, "VolumeType": "gp3", "Encrypted": True, "DeleteOnTermination": True}}],
            "TagSpecifications": [{"ResourceType": kind, "Tags": tag} for kind in ("instance", "volume")], "UserData": data}
        state["request_without_userdata"] = {k: v for k, v in request.items() if k != "UserData"}
        state["userdata_sha256"] = sha(data.encode())
        try:
            ec2.run_instances(DryRun=True, **request)
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "DryRunOperation":
                raise
            state["exact_request_dry_run"] = "DryRunOperation"
        else:
            raise ValueError("EXPECTED_DRY_RUN_OPERATION")
        state["launch_attempted"] = True
        launched_at = time.monotonic()
        launch_utc = utc()
        save()
        response = ec2.run_instances(**request)  # exactly one call; no retry/resubmission
        instance_id = response["Instances"][0]["InstanceId"]
        owned("instance_id", instance_id)
        state["launch_utc"] = launch_utc.isoformat()
        when = launch_utc + datetime.timedelta(seconds=plan["scheduler_after_seconds"])
        scheduler.create_schedule(Name=job, ClientToken=job, ScheduleExpression="at(" + when.strftime("%Y-%m-%dT%H:%M:%S") + ")",
            ScheduleExpressionTimezone="UTC", FlexibleTimeWindow={"Mode": "OFF"}, ActionAfterCompletion="DELETE",
            Target={"Arn": "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances", "RoleArn": f"arn:aws:iam::{plan['account_id']}:role/{watchdog_role}",
                    "Input": json.dumps({"InstanceIds": [instance_id]}), "RetryPolicy": {"MaximumRetryAttempts": 0, "MaximumEventAgeInSeconds": 60}})
        owned("schedule", job)
        state["watchdog_at_utc"] = when.isoformat()
        state["status"] = "RUNNING"
        save()
        while time.monotonic() - launched_at < plan["operator_seconds"]:
            heartbeat()
            try:
                response = s3.get_object(Bucket=bucket, Key="outputs/terminal.json")
                raw = response["Body"].read()
                terminal = json.loads(raw)
                (evidence / "terminal.json").write_bytes(raw)
                break
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in ("NoSuchKey", "404"):
                    raise
            status = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]["State"]["Name"]
            if status == "terminated":
                break
            time.sleep(10)
        state["status"] = terminal["status"] if terminal else "NO_TERMINAL_RECEIPT"
    except BaseException as exc:
        state["status"] = "FAILED"
        state["error_type"] = type(exc).__name__
        state["error"] = str(exc)
        (evidence / "operator_exception.txt").write_text(redact(traceback.format_exc()))
    finally:
        # If RunInstances returned uncertainly, discover this exact unique job tag once.
        if not instance_id and state.get("launch_attempted"):
            def find_uncertain():
                rows = ec2.describe_instances(Filters=[{"Name": "tag:CASJob", "Values": [job]}])
                ids = [i["InstanceId"] for r in rows["Reservations"] for i in r["Instances"]]
                if len(ids) > 1:
                    raise ValueError("MULTIPLE_JOB_INSTANCES")
                return ids[0] if ids else None
            instance_id = action("resolve_uncertain_launch", find_uncertain)
            if instance_id:
                owned("instance_id", instance_id)
            else:
                # One empty eventually-consistent describe is not proof that no VM exists.
                cleanup_safe = False
                state["uncertain_launch"] = "Instance not resolved; retain dependencies and require operator observation, never resubmit launch."
        if instance_id:
            action("terminate_instance", lambda: ec2.terminate_instances(InstanceIds=[instance_id]))
            def wait_terminated():
                deadline = time.monotonic() + 150
                while time.monotonic() < deadline:
                    heartbeat()
                    result = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
                    if result["State"]["Name"] == "terminated":
                        state["instance_terminal"] = result["State"]
                        return True
                    time.sleep(5)
                raise TimeoutError("TERMINATION_NOT_CONFIRMED")
            if not action("confirm_terminated", wait_terminated):
                cleanup_safe = False
            def console():
                result = ec2.get_console_output(InstanceId=instance_id, Latest=True)
                output = result.pop("Output", "")
                result["provider_output_sha256"] = sha(output.encode())
                try:
                    output = base64.b64decode("".join(output.split()), validate=True).decode("utf-8", errors="replace")
                except ValueError:
                    pass
                result["ConsoleText"] = redact(output)
                (evidence / "console.json").write_text(json.dumps(redact(result), default=str, indent=2))
            action("collect_console", console)
        collected = True
        if "bucket" in state["resources"]:
            def collect():
                rows, token = [], None
                while True:
                    kwargs = {"Bucket": bucket, "Prefix": "outputs/"}
                    if token:
                        kwargs["ContinuationToken"] = token
                    listing = s3.list_objects_v2(**kwargs)
                    rows.extend(listing.get("Contents", []))
                    token = listing.get("NextContinuationToken")
                    if not token:
                        break
                inventory = []
                for row in rows:
                    key = row["Key"]
                    relative = Path(key.removeprefix("outputs/"))
                    target = evidence / relative
                    if relative.is_absolute() or not target.resolve().is_relative_to(evidence.resolve()):
                        raise ValueError("UNSAFE_OUTPUT_KEY")
                    raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
                    inventory.append({"key": key, "sha256": sha(raw), "bytes": len(raw)})
                if terminal:
                    raw = (evidence / "outputs.tar.gz").read_bytes()
                    if sha(raw) != terminal["sha256"] or len(raw) != terminal["bytes"]:
                        raise ValueError("OUTPUT_ARCHIVE_MISMATCH")
                (evidence / "download_inventory.json").write_text(json.dumps(inventory, indent=2))
                return True
            collected = bool(action("collect_all_outputs", collect))
        if cleanup_safe and collected:
            if "schedule" in state["resources"]:
                def remove_schedule():
                    try:
                        scheduler.delete_schedule(Name=job)
                    except ClientError as exc:
                        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
                            raise
                action("delete_schedule", remove_schedule)
            if "security_group" in state["resources"]:
                action("delete_security_group", lambda: ec2.delete_security_group(GroupId=state["resources"]["security_group"]))
            if "profile_role" in state["resources"]:
                action("remove_profile_role", lambda: iam.remove_role_from_instance_profile(InstanceProfileName=profile, RoleName=role))
            if "profile" in state["resources"]:
                action("delete_profile", lambda: iam.delete_instance_profile(InstanceProfileName=profile))
            for kind, name, policy in (("worker", role, "job-objects"), ("watchdog", watchdog_role, "tagged-termination")):
                if kind + "_policy" in state["resources"]:
                    action("delete_" + kind + "_policy", lambda n=name, p=policy: iam.delete_role_policy(RoleName=n, PolicyName=p))
                if kind + "_role" in state["resources"]:
                    action("delete_" + kind + "_role", lambda n=name: iam.delete_role(RoleName=n))
            if "bucket" in state["resources"]:
                def delete_bucket():
                    listing = s3.list_objects_v2(Bucket=bucket)
                    if listing.get("IsTruncated"):
                        raise ValueError("UNEXPECTED_LARGE_JOB_BUCKET")
                    keys = [r["Key"] for r in listing.get("Contents", [])]
                    if any(k != "inputs/payload.zip" and not k.startswith("outputs/") for k in keys):
                        raise ValueError("UNOWNED_BUCKET_OBJECT")
                    for key in keys:
                        s3.delete_object(Bucket=bucket, Key=key)
                    s3.delete_bucket(Bucket=bucket)
                action("delete_owned_bucket", delete_bucket)
        state["end_utc"] = utc().isoformat()
        state["compute_elapsed_seconds"] = None if launched_at is None else time.monotonic() - launched_at
        state["cleanup_complete"] = cleanup_safe and collected and all(row["status"] == "PASS" for row in state["cleanup"])
        state["cost"] = {"all_services_authorized_maximum_usd": "1.00", "forecast_usd": "0.10",
                         "actual_billing_usd": None, "note": "Billing actual unavailable; resource timestamps and prospective envelope retained."}
        heartbeat("END", force=True)
        save()
        print(json.dumps({"status": state["status"], "instance_id": instance_id,
                          "cleanup_complete": state["cleanup_complete"], "record": str(directory / "execution.json")}))
    return 0 if state["status"] == "PASS_ENGINEERING_VALIDATION_ONLY" and state["cleanup_complete"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--job-directory", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.job_directory, args.freeze_sha256))


if __name__ == "__main__":
    main()
