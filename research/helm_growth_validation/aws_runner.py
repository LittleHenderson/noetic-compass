"""Growth15 transport copied from cd5ce96 CONT19 transport; scientific source remains c70e1a.
New child admission and accounting; legacy runner remains unchanged.

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
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from admission import validate_freeze

HERE = Path(__file__).resolve().parent
# SOURCE is supplied only by the hash-bound freeze record.


def utc():
    return datetime.datetime.now(datetime.timezone.utc)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def service_client(session, config, name, region):
    from botocore.config import Config
    options = {"region_name": region, "config": config}
    if name == "s3":
        # Pin the endpoint itself: region_name alone can still presign a global
        # S3 host. This regional path-style form has a read-only transport receipt.
        options["endpoint_url"] = "https://s3." + region + ".amazonaws.com"
        options["config"] = config.merge(Config(signature_version="s3v4", s3={"addressing_style": "path"}))
    return session.client(name, **options)


def userdata(plan, download_url, failure_url, evidence_url):
    # Do not persist or print presigned URLs; they are limited to this job's objects.
    bootstrap = '''import hashlib,json,os,pathlib,subprocess,sys,urllib.error,urllib.request,zipfile,xml.etree.ElementTree as ET
def safe_failure(exc):
    error_type=type(exc).__name__
    if error_type not in {'HTTPError','URLError','ValueError','RuntimeError','OSError','FileExistsError','BadZipFile','TimeoutError'}:
        error_type='UNCLASSIFIED_ERROR'
    result={'status':'BOOTSTRAP_OR_WORKER_FAILED','error_type':error_type,'http_status':None,'code':None}
    if isinstance(exc,urllib.error.HTTPError):
        if isinstance(exc.code,int) and 100<=exc.code<=599: result['http_status']=exc.code
        try:
            code=ET.fromstring(exc.read(8192)).findtext('Code')
            if code in {'AuthorizationQueryParametersError','SignatureDoesNotMatch','AccessDenied','NoSuchKey','InvalidAccessKeyId','ExpiredToken','RequestTimeTooSkewed','InvalidToken','RequestExpired','PermanentRedirect','AuthorizationHeaderMalformed'}:
                result['code']=code
        except BaseException: pass
    elif isinstance(exc,(ValueError,RuntimeError)) and exc.args in [('PAYLOAD_IDENTITY',),('UNSAFE_ARCHIVE',),('WORKER_FAILED',)]:
        result['code']=exc.args[0]
    return result
root=pathlib.Path('/opt/helm-validation')
try:
    root.mkdir(exist_ok=False)
    with urllib.request.urlopen(DOWNLOAD,timeout=30) as response: raw=response.read(64*1024*1024+1)
    if len(raw)>64*1024*1024 or hashlib.sha256(raw).hexdigest()!=DIGEST: raise ValueError('PAYLOAD_IDENTITY')
    archive=root/'payload.zip';archive.write_bytes(raw)
    with zipfile.ZipFile(archive) as stream:
        for row in stream.infolist():
            if not (root/row.filename).resolve().is_relative_to(root.resolve()): raise ValueError('UNSAFE_ARCHIVE')
        stream.extractall(root)
    code=subprocess.call([sys.executable,str(root/'worker.py'),'--bucket',BUCKET,'--region',REGION])
    if code: raise RuntimeError('WORKER_FAILED')
except BaseException as exc:
    failure=json.dumps(safe_failure(exc)).encode()
    print(failure.decode('utf-8'),flush=True)
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
    return ("#!/bin/bash\nset -eu\n/sbin/shutdown -h +" + str((plan["hard_wall_seconds"] - 120) // 60) + " || exit 91\n"
            "export PYTHONDONTWRITEBYTECODE=1\n"
            "timeout --signal=TERM --kill-after=30s " + str(plan["hard_wall_seconds"] - 180) + " python3 - <<'CAS_BOOTSTRAP'\nimport base64\nexec(compile(base64.b64decode('" + encoded + "'),'<job-bootstrap>','exec'))\nCAS_BOOTSTRAP\n")


def execute(directory, expected_hash):
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
    directory = directory.resolve()
    frozen = (directory / "freeze.json").read_bytes()
    if sha(frozen) != expected_hash:
        raise ValueError("FROZEN_RECORD_HASH_REQUIRED")
    plan = json.loads(frozen)
    SOURCE = plan["source_commit"]
    if not re.fullmatch("[0-9a-f]{40}", SOURCE):
        raise ValueError("SOURCE_SHA_FORM")
    if plan.get("schema") != "helm.growth15.aws.freeze/1":
        raise ValueError("WRONG_GROWTH15_FREEZE")
    if plan["source_commit"] != SOURCE or plan["package_source_commit"] != SOURCE:
        raise ValueError("EXACT_HELM_SOURCE_REQUIRED")
    exemptions = {row["instance_id"]: row for row in plan["permitted_concurrent_instances"]}
    if set(exemptions) != {"i-0bd0a082507a51ae3", "i-02137d196e671b5c1"}:
        raise ValueError("EXACT_EXISTING_PRODUCTION_APP_IDENTITIES_REQUIRED")
    for row in exemptions.values():
        if (row["instance_type"] != "t3.small" or row["region"] != "us-west-2" or
                row["tags"].get("Project") != "noetic-compass" or
                row["tags"].get("Purpose") != "render-to-aws-migration" or
                row["tags"].get("Lane") not in {"customer-production", "accounts-canary"} or
                "CASJob" in row["tags"]):
            raise ValueError("PRODUCTION_APP_EXEMPTION_SCOPE")
    validate_freeze(plan, directory)
    directive = (directory / "owner_directive.md").read_bytes()
    if sha(directive) != plan["owner_directive_sha256"]:
        raise ValueError("OWNER_DIRECTIVE_CHANGED")
    if sha((HERE / "aws_runner.py").read_bytes()) != plan["launcher_sha256"]:
        raise ValueError("LAUNCHER_CHANGED_AFTER_FREEZE")
    payload = (directory / plan["payload_file"]).read_bytes()
    if sha(payload) != plan["payload_sha256"] or len(payload) != plan["payload_bytes"]:
        raise ValueError("PAYLOAD_CHANGED_AFTER_FREEZE")
    # Generated by the new admission.reserve API; no historical ledger is opened.
    reservation = json.loads((directory / "reservation.json").read_bytes())
    # Atomic local ownership: subsequent execute attempts are always refused.
    with (directory / "ATTEMPT_STARTED.json").open("x", encoding="utf-8") as stream:
        json.dump({"freeze_sha256": expected_hash, "utc": utc().isoformat(), "retry_count": 0}, stream)
    session = boto3.Session(profile_name=plan["sdk_profile"], region_name=plan["region"])
    config = Config(retries={"total_max_attempts": 1}, connect_timeout=5, read_timeout=30)
    def client(name, region=None):
        return service_client(session, config, name, region or plan["region"])
    ec2, iam, s3, scheduler = (client(name) for name in ("ec2", "iam", "s3", "scheduler"))
    job = plan["job_id"]
    bucket = job + "-" + plan["account_id"]
    role, profile, watchdog_role = job + "-worker", job + "-worker", job + "-watchdog"
    tag = [{"Key": "CASJob", "Value": job}, {"Key": "Runner", "Value": "Codex"}]
    state = {"schema": "helm.validation.aws.execution/1", "job_id": job, "freeze_sha256": expected_hash,
             "source_commit": plan["source_commit"], "payload_sha256": plan["payload_sha256"],
             "runner": "Codex", "start_utc": utc().isoformat(), "resources": {}, "cleanup": [],
             "status": "PRELAUNCH", "cloud_calls_retry_count": 0, "maximum_all_services_usd": plan["maximum_all_services_usd"]}
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
               "current_task": "Growth15 standalone numerical validation: " + job,
               "work_done_since_last_heartbeat": state["status"],
               "blocker": state.get("error"), "next_action": "Observe frozen job; retain evidence and confirm cleanup",
               "relevant_commit_or_file": str(directory / "execution.json"),
               "paid_cloud_work_active": bool(state.get("launch_attempted") and not state.get("instance_terminal")),
               "instance_id": state["resources"].get("instance_id")}
        path = Path("D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination/helm_rnd_three_lead_v1/codex_heartbeat.jsonl")
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
        history = directory / "state_history"
        history.mkdir(exist_ok=True)
        target = history / (str(time.time_ns()) + ".json")
        raw = (json.dumps(redact(state), indent=2, default=str) + "\n").encode()
        with target.open("xb") as stream:
            stream.write(raw); stream.flush(); __import__('os').fsync(stream.fileno())
        # Append-only snapshot is authoritative even if Windows blocks this convenience view.
        temporary = directory / ("execution." + str(time.time_ns()) + ".tmp")
        temporary.write_bytes(raw)
        for attempt in range(4):
            try:
                temporary.replace(directory / "execution.json")
                break
            except PermissionError:
                time.sleep(0.1 * (attempt + 1))
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
    save()  # Verify a durable state snapshot before the first mutating AWS call.
    try:
        identity = client("sts").get_caller_identity()
        if identity["Account"] != plan["account_id"]:
            raise ValueError("WRONG_AWS_ACCOUNT")
        state["caller_arn"] = identity["Arn"]
        # Serial experiments: only the two exact frozen existing production apps are exempt.
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
                active.extend({"instance_id": i["InstanceId"], "instance_type": i["InstanceType"],
                               "region": region["RegionName"], "tags": {t["Key"]: t["Value"] for t in i.get("Tags", [])}}
                              for r in data["Reservations"] for i in r["Instances"])
                token = data.get("NextToken")
                if not token:
                    break
            checks.append({"region": region["RegionName"], "active_instances": active})
            heartbeat()
            unexpected = [row for row in active if row["instance_id"] not in exemptions or
                          any(row[key] != exemptions[row["instance_id"]][key]
                              for key in ("instance_type", "region", "tags"))]
            if unexpected:
                state["global_concurrency"] = checks
                save()
                raise ValueError("UNDECLARED_ACTIVE_INSTANCE_CONCURRENCY_BLOCK")
        state["global_concurrency"] = checks
        save()
        pricing = client("pricing", "us-east-1").get_products(ServiceCode="AmazonEC2", Filters=[
            {"Type": "TERM_MATCH", "Field": key, "Value": value} for key, value in {
                "instanceType": "g7.2xlarge", "location": "US West (Oregon)",
                "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA",
                "capacitystatus": "Used", "marketoption": "OnDemand", "operation": "RunInstances"}.items()])
        rates = sorted({d["pricePerUnit"]["USD"] for raw in pricing["PriceList"]
                        for term in json.loads(raw).get("terms", {}).get("OnDemand", {}).values()
                        for d in term["priceDimensions"].values() if d.get("unit") == "Hrs"})
        from decimal import Decimal
        if not rates or any(Decimal(value) != Decimal("2.52") for value in rates):
            raise ValueError("GROWTH15_FRESH_PRICE_DIFFERS")
        state["fresh_pricing"] = {"rates": rates, "request_id": pricing["ResponseMetadata"]["RequestId"],
                                  "observed_utc": utc().isoformat(), "actual_bill": False}
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
        sg = ec2.create_security_group(GroupName=job, Description="Single frozen growth15 numerical check", VpcId=plan["vpc_id"],
                                       TagSpecifications=[{"ResourceType": "security-group", "Tags": tag}])["GroupId"]
        owned("security_group", sg)
        permissions = ec2.describe_security_groups(GroupIds=[sg])["SecurityGroups"][0]["IpPermissionsEgress"]
        if permissions:
            ec2.revoke_security_group_egress(GroupId=sg, IpPermissions=permissions)
        ec2.authorize_security_group_egress(GroupId=sg, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443,
                                                                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        # A single bounded propagation delay, not a repeated failed launch.
        time.sleep(15)
        download_url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": "inputs/payload.zip"}, ExpiresIn=plan["hard_wall_seconds"] + 600)
        failure_url = s3.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": "outputs/bootstrap_failure.json"}, ExpiresIn=plan["hard_wall_seconds"] + 600)
        evidence_url = s3.generate_presigned_url("put_object", Params={"Bucket": bucket, "Key": "outputs/emergency_evidence.tar.gz"}, ExpiresIn=plan["hard_wall_seconds"] + 600)
        secret_strings.extend((download_url, failure_url, evidence_url))
        data = userdata(plan, download_url, failure_url, evidence_url)
        secret_strings.append(data)
        secret_strings.extend(re.findall(r"b64decode\('([^']+)'\)", data))
        if len(data.encode()) > 16384:
            raise ValueError("USER_DATA_SIZE_LIMIT")
        request = {"ImageId": plan["ami"], "InstanceType": plan["instance_type"], "MinCount": 1, "MaxCount": 1,
            "ClientToken": job, "Placement": {"AvailabilityZone": plan["zone"]},
            "NetworkInterfaces": [{"DeviceIndex": 0, "SubnetId": plan["subnet_id"], "Groups": [sg], "AssociatePublicIpAddress": True, "DeleteOnTermination": True}],
            "IamInstanceProfile": {"Name": profile},
            "MetadataOptions": {"HttpTokens": "required", "HttpEndpoint": "enabled", "HttpPutResponseHopLimit": 1},
            "InstanceInitiatedShutdownBehavior": "terminate", "DisableApiTermination": False,
            "BlockDeviceMappings": [{"DeviceName": plan["root_device"], "Ebs": {"VolumeSize": plan["root_gib"], "VolumeType": "gp3", "Encrypted": True, "DeleteOnTermination": True}}],
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
            try:
                failure_raw = s3.get_object(Bucket=bucket, Key="outputs/bootstrap_failure.json")["Body"].read(16385)
                if len(failure_raw) > 16384:
                    raise ValueError("BOOTSTRAP_FAILURE_RECEIPT_BOUND")
                state["bootstrap_failure"] = json.loads(failure_raw)
                (evidence / "bootstrap_failure.json").write_bytes(failure_raw)
                break
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in ("NoSuchKey", "404"):
                    raise
            status = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]["State"]["Name"]
            if status == "terminated":
                break
            time.sleep(10)
        if terminal:
            if terminal.get("source_commit") != SOURCE:
                raise ValueError("TERMINAL_SOURCE_MISMATCH")
            if terminal.get("status") == plan["expected_status"]:
                if terminal.get("growth_source_commit") != plan["growth_source_commit"] or terminal.get("tests") != {"tests":15,"failures":0,"errors":0,"skipped":0}:
                    raise ValueError("GROWTH_SOURCE_AND_CASE_COUNTS_REQUIRED")
        state["status"] = terminal["status"] if terminal else ("FAILED_BOOTSTRAP_UNACCEPTED" if "bootstrap_failure" in state else "NO_TERMINAL_RECEIPT")
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
            def console(filename):
                result = ec2.get_console_output(InstanceId=instance_id, Latest=True)
                output = result.pop("Output", "")
                result["provider_output_sha256"] = sha(output.encode())
                try:
                    output = base64.b64decode("".join(output.split()), validate=True).decode("utf-8", errors="replace")
                except ValueError:
                    pass
                result["ConsoleText"] = redact(output)
                (evidence / filename).write_text(json.dumps(redact(result), default=str, indent=2))
            # Capture while live: terminated instances can return empty console text.
            # A collection failure must not prevent the termination attempt.
            action("collect_console_before_termination", lambda: console("console_before_termination.json"))
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
            action("collect_console", lambda: console("console.json"))
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
                    target.parent.mkdir(parents=True, exist_ok=True)
                    response = s3.get_object(Bucket=bucket, Key=key)
                    observed, size = hashlib.sha256(), 0
                    with target.open("wb") as stream:
                        for block in iter(lambda: response["Body"].read(1024 * 1024), b""):
                            size += len(block)
                            if size > 1024 ** 3:
                                raise ValueError("COLLECTION_OBJECT_BOUND")
                            observed.update(block); stream.write(block)
                    inventory.append({"key": key, "sha256": observed.hexdigest(), "bytes": size})
                if terminal:
                    archive = evidence / "outputs.tar.gz"
                    with archive.open("rb") as stream:
                        observed = hashlib.file_digest(stream, "sha256").hexdigest()
                    if observed != terminal["sha256"] or archive.stat().st_size != terminal["bytes"]:
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
                state["retained_evidence_archive"] = {"bucket": bucket, "status": "RETAINED_PRIVATE_EVIDENCE",
                    "storage_active": True, "deletion_authorized": False,
                    "reason": "Owner requires evidence preservation; compute and job dependencies cleaned separately."}
        state["end_utc"] = utc().isoformat()
        state["compute_elapsed_seconds"] = None if launched_at is None else time.monotonic() - launched_at
        state["cleanup_complete"] = cleanup_safe and collected and all(row["status"] == "PASS" for row in state["cleanup"])
        state["cost"] = {"all_services_authorized_maximum_usd": plan["maximum_all_services_usd"], "forecast_usd": plan["maximum_all_services_usd"],
                         "actual_billing_usd": None, "note": "Billing actual unavailable; resource timestamps and prospective envelope retained."}
        heartbeat("END", force=True)
        save()
        print(json.dumps({"status": state["status"], "instance_id": instance_id,
                          "cleanup_complete": state["cleanup_complete"], "record": str(directory / "execution.json")}))
    return 0 if state["status"] == plan["expected_status"] and state["cleanup_complete"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--job-directory", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.job_directory, args.freeze_sha256))


if __name__ == "__main__":
    main()
