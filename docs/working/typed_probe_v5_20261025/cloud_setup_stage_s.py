#!/usr/bin/env python3
# Lightweight AWS orchestration only. This file performs no model inference.
import argparse
import base64
import datetime as dt
import decimal
import hashlib
import io
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
import zipfile

import boto3
from botocore.exceptions import ClientError

REGION = "us-west-2"
ACCOUNT = "807562639912"
BUCKET = "cas-harness-runpod-92754088"
RUN_ID = "typed-probe-v5-stage-s-retry1-20261025-0400z"
RUN_PREFIX = f"typed_probe_v5_20261025/{RUN_ID}"
WATCHDOG_PROOF_KEY = RUN_PREFIX + "/provenance/watchdog_proof_attempt3.json"
WATCHDOG_TEST_INSTANCE_TYPE = "t3.nano"
WATCHDOG_TEST_MAX_SECONDS = 300
WATCHDOG_TEST_ROOT_GIB = 8
PARAMETER_NAME = "/cas-harness/typed-probe-v5/anthropic-api-key"
INSTANCE_TYPE = "g5.2xlarge"
AMI_ID = "ami-0d105fd7469b31d32"
SUBNET_ID = "subnet-02deacfa16bdaa4f4"
SECURITY_GROUP_ID = "sg-0562c483e0364cdab"
INSTANCE_ROLE_NAME = "typed-probe-v5-stage-s-role-20261025"
INSTANCE_PROFILE_NAME = "typed-probe-v5-stage-s-profile-20261025"
WATCHDOG_FUNCTION = "typed-probe-v5-stage-s-watchdog-20261025"
WATCHDOG_ROLE_NAME = "typed-probe-v5-stage-s-watchdog-role-20261025"
SCHEDULER_ROLE_NAME = "typed-probe-v5-stage-s-scheduler-role-20261025"
TEST_SCHEDULE_NAME = "typed-probe-v5-stage-s-test-20261025"
RUN_SCHEDULE_NAME = "typed-probe-v5-stage-s-stop-20261025"
RUN_TAG_KEY = "typed-probe-v5-run-id"
RUN_TAG_VALUE = RUN_ID
ROOT = pathlib.Path(__file__).resolve().parent
BANK = pathlib.Path(r"D:\tksCAS-archive\typed_probe_v4_tooling_20260610\candidate_bank_v4_120_20260610.jsonl")
FILES = {
    "run_stage_s_v5.py": ROOT / "run_stage_s_v5.py",
    "watchdog_e2e_proof.py": ROOT / "watchdog_e2e_proof.py",
    "watchdog_e2e_proof_attempt2.py": ROOT / "watchdog_e2e_proof_attempt2.py",
    "watchdog_e2e_proof_attempt3.py": ROOT / "watchdog_e2e_proof_attempt3.py",
    "typed_probe_gate_prereg_v5_bootstrap_retry_amendment_20261025.md": ROOT.parent / "typed_probe_gate_prereg_v5_bootstrap_retry_amendment_20261025.md",
    "candidate_bank_v4_120_20260610.jsonl": BANK,
    "typed_probe_v5_judge_rubric_20261025.txt": ROOT.parent / "typed_probe_v5_judge_rubric_20261025.txt",
    "typed_probe_gate_prereg_v5_safe_handling_20261025.md": ROOT.parent / "typed_probe_gate_prereg_v5_safe_handling_20261025.md",
    "typed_probe_gate_prereg_v5_claude_budget_amendment_20261025.md": ROOT.parent / "typed_probe_gate_prereg_v5_claude_budget_amendment_20261025.md",
}
EXPECTED = {
    "watchdog_e2e_proof.py": "c2dfb1b5e2649d0a7fab04d9d9e63625b66b0a523ca3e8da2e6352c57a1068b2",
    "watchdog_e2e_proof_attempt2.py": "9064bbe18a8b1170f9b0ae8a3aa21af7b0ad410746ccd28c63217450f1969d62",
    "watchdog_e2e_proof_attempt3.py": "94356d18f7b25dcfa7a035f7bda5ea1b7bbb37eae0f41fa4e5144d0e754ec82b",
    "typed_probe_gate_prereg_v5_bootstrap_retry_amendment_20261025.md": "1bf9065c7fab6c8ea93c138308c8150a84c3495782a63b0fc853104266040c54",
    "run_stage_s_v5.py": "b44bcbbd9ee9a41252e72bc9f1c9efef3fee6de07a701ad743c26399dd010268",
    "candidate_bank_v4_120_20260610.jsonl": "4a6b73ecd764fce0373cdb7ce5500b00ea0dc9a4fca6be3e2a8761857b57f32f",
    "typed_probe_v5_judge_rubric_20261025.txt": "e176676df7cd4d1593288daf9a793e0c75a1a81cdc9d9c40980c4d1eb02307fd",
    "typed_probe_gate_prereg_v5_safe_handling_20261025.md": "c3049fbf65565cf062fdddafd91200b96a2c7fbbd3eed7daaeb513900b5e7132",
    "typed_probe_gate_prereg_v5_claude_budget_amendment_20261025.md": "7d259447e5e5bfc8e650694bba25cb99ee0d76760e76665c3d81eea9ffcc22fe",
}
QWEN_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
MISTRAL_REVISION = "c170c708c41dac9275d15a8fff4eca08d52bab71"


def client(service):
    return boto3.client(service, region_name=REGION)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    return sha256(path.read_bytes())


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def model_ids_check(api_key):
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/models?limit=100",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Anthropic model-list check failed with HTTP {exc.code}") from None
    ids = {row.get("id") for row in body.get("data", [])}
    required = {"claude-sonnet-5-5", "claude-haiku-5-5"}
    if not required.issubset(ids):
        raise RuntimeError("a frozen Claude model ID is unavailable")
    return sorted(required)


def quote_instance_hourly(instance_type):
    pricing = boto3.client("pricing", region_name="us-east-1")
    filters = [
        {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
        {"Type": "TERM_MATCH", "Field": "location", "Value": "US West (Oregon)"},
        {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
        {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
        {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
        {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
    ]
    products = pricing.get_products(ServiceCode="AmazonEC2", Filters=filters, MaxResults=20)
    for raw in products.get("PriceList", []):
        product = json.loads(raw)
        terms = product.get("terms", {}).get("OnDemand", {})
        for term in terms.values():
            for dimension in term.get("priceDimensions", {}).values():
                if dimension.get("unit") == "Hrs" and dimension.get("pricePerUnit", {}).get("USD"):
                    return decimal.Decimal(dimension["pricePerUnit"]["USD"])
    raise RuntimeError(f"AWS Price List API returned no Linux {instance_type} On-Demand rate")


def quote_g5_hourly():
    return quote_instance_hourly(INSTANCE_TYPE)

def verify_account_and_limits():
    identity = client("sts").get_caller_identity()
    if identity.get("Account") != ACCOUNT:
        raise RuntimeError("AWS identity is not the frozen project account")
    hourly = quote_g5_hourly()
    sentinel_hourly = quote_instance_hourly(WATCHDOG_TEST_INSTANCE_TYPE)
    main_seconds = decimal.Decimal("10800")
    sentinel_seconds = decimal.Decimal(str(WATCHDOG_TEST_MAX_SECONDS))
    main_hours = main_seconds / decimal.Decimal("3600")
    sentinel_hours = sentinel_seconds / decimal.Decimal("3600")
    ebs_main = decimal.Decimal("100") * decimal.Decimal("0.08") * main_hours / decimal.Decimal("720")
    ebs_sentinel = decimal.Decimal(str(WATCHDOG_TEST_ROOT_GIB)) * decimal.Decimal("0.08") * sentinel_hours / decimal.Decimal("720")
    s3_month = decimal.Decimal("1") * decimal.Decimal("0.023")
    public_ipv4_main = decimal.Decimal("0.005") * main_hours
    total = hourly * main_hours + sentinel_hourly * sentinel_hours + ebs_main + ebs_sentinel + s3_month + public_ipv4_main
    if total > decimal.Decimal("5.00"):
        raise RuntimeError(f"refreshed AWS maximum-scenario estimate exceeds the approved cap: {total}")
    return identity["Arn"], str(hourly), str(sentinel_hourly), str(total)


def assume_role_trust(service):
    return {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": service},
            "Action": "sts:AssumeRole",
        }],
    }


def ensure_role(iam, name, trust, description):
    try:
        role = iam.get_role(RoleName=name)["Role"]
        iam.update_assume_role_policy(
            RoleName=name, PolicyDocument=json.dumps(trust, separators=(",", ":")))
        return role["Arn"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise
    role = iam.create_role(
        RoleName=name,
        AssumeRolePolicyDocument=json.dumps(trust, separators=(",", ":")),
        Description=description,
        Tags=[
            {"Key": "Project", "Value": "typed-probe-v5"},
            {"Key": "RunId", "Value": RUN_ID},
        ],
    )["Role"]
    return role["Arn"]


def put_inline_policy(iam, role, policy_name, document):
    iam.put_role_policy(
        RoleName=role,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(document, separators=(",", ":")),
    )


def ensure_instance_profile(iam):
    role_arn = ensure_role(
        iam, INSTANCE_ROLE_NAME, assume_role_trust("ec2.amazonaws.com"),
        "Reads only v5 Stage S inputs/key, uploads its evidence, and terminates its tagged instance.",
    )
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ReadOnlyStageKey",
                "Effect": "Allow",
                "Action": ["ssm:GetParameter"],
                "Resource": f"arn:aws:ssm:{REGION}:{ACCOUNT}:parameter{PARAMETER_NAME}",
            },
            {
                "Sid": "StageSPrefixEvidence",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject"],
                "Resource": f"arn:aws:s3:::{BUCKET}/{RUN_PREFIX}/*",
            },
            {
                "Sid": "TerminateOnlyThisStudyInstance",
                "Effect": "Allow",
                "Action": ["ec2:TerminateInstances"],
                "Resource": f"arn:aws:ec2:{REGION}:{ACCOUNT}:instance/*",
                "Condition": {
                    "StringEquals": {f"ec2:ResourceTag/{RUN_TAG_KEY}": RUN_TAG_VALUE}
                },
            },
        ],
    }
    put_inline_policy(iam, INSTANCE_ROLE_NAME, "typed-probe-v5-stage-s", policy)
    try:
        profile = iam.get_instance_profile(InstanceProfileName=INSTANCE_PROFILE_NAME)["InstanceProfile"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchEntity":
            raise
        profile = iam.create_instance_profile(
            InstanceProfileName=INSTANCE_PROFILE_NAME,
            Tags=[{"Key": "Project", "Value": "typed-probe-v5"}],
        )["InstanceProfile"]
    attached = {role["RoleName"] for role in profile.get("Roles", [])}
    if INSTANCE_ROLE_NAME not in attached:
        iam.add_role_to_instance_profile(
            InstanceProfileName=INSTANCE_PROFILE_NAME, RoleName=INSTANCE_ROLE_NAME)
    return role_arn, policy


def ensure_watchdog(iam, lambdas):
    function_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{WATCHDOG_FUNCTION}"
    log_group_arn = f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/lambda/{WATCHDOG_FUNCTION}:*"
    role_arn = ensure_role(
        iam, WATCHDOG_ROLE_NAME, assume_role_trust("lambda.amazonaws.com"),
        "Terminates only the v5 Stage S instance with the exact run tag.",
    )
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["ec2:DescribeInstances"], "Resource": "*"},
            {
                "Effect": "Allow",
                "Action": ["ec2:TerminateInstances"],
                "Resource": f"arn:aws:ec2:{REGION}:{ACCOUNT}:instance/*",
                "Condition": {
                    "StringEquals": {f"ec2:ResourceTag/{RUN_TAG_KEY}": RUN_TAG_VALUE}
                },
            },
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": log_group_arn,
            },
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogGroup"],
                "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/lambda/{WATCHDOG_FUNCTION}",
            },
        ],
    }
    put_inline_policy(iam, WATCHDOG_ROLE_NAME, "typed-probe-v5-watchdog", policy)
    package_buffer = io.BytesIO()
    source = (ROOT / "cloud_watchdog.py").read_bytes()
    with zipfile.ZipFile(package_buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("cloud_watchdog.py", source)
    code = package_buffer.getvalue()
    try:
        existing = lambdas.get_function(FunctionName=WATCHDOG_FUNCTION)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {"ResourceNotFoundException"}:
            raise
        create_args = {
            "FunctionName": WATCHDOG_FUNCTION,
            "Runtime": "python3.12",
            "Role": role_arn,
            "Handler": "cloud_watchdog.handler",
            "Code": {"ZipFile": code},
            "Description": "One-time v5 Stage S EC2 shutdown watchdog.",
            "Timeout": 30,
            "MemorySize": 128,
            "Publish": True,
            "Environment": {"Variables": {"STAGE_S_RUN_ID": RUN_ID}},
            "Tags": {"Project": "typed-probe-v5", "RunId": RUN_ID},
        }
        for attempt in range(24):
            try:
                lambdas.create_function(**create_args)
                break
            except ClientError as create_exc:
                error = create_exc.response.get("Error", {})
                message = error.get("Message", "").lower()
                if (error.get("Code") != "InvalidParameterValueException"
                        or "cannot be assumed" not in message or attempt == 23):
                    raise
                time.sleep(5)
    else:
        expected_code_sha = base64.b64encode(hashlib.sha256(code).digest()).decode("ascii")
        current = existing["Configuration"]
        if current.get("CodeSha256") != expected_code_sha:
            lambdas.update_function_code(FunctionName=WATCHDOG_FUNCTION, ZipFile=code)
        current = lambdas.get_function_configuration(FunctionName=WATCHDOG_FUNCTION)
        desired_environment = {"STAGE_S_RUN_ID": RUN_ID}
        if (current.get("Role") != role_arn
                or current.get("Handler") != "cloud_watchdog.handler"
                or current.get("Runtime") != "python3.12"
                or current.get("Timeout") != 30
                or current.get("MemorySize") != 128
                or current.get("Environment", {}).get("Variables", {}) != desired_environment):
            lambdas.update_function_configuration(
                FunctionName=WATCHDOG_FUNCTION,
                Role=role_arn,
                Handler="cloud_watchdog.handler",
                Runtime="python3.12",
                Timeout=30,
                MemorySize=128,
                Environment={"Variables": desired_environment},
            )
    for _ in range(24):
        current = lambdas.get_function_configuration(FunctionName=WATCHDOG_FUNCTION)
        if current.get("State") == "Active" and current.get("LastUpdateStatus") == "Successful":
            break
        time.sleep(5)
    else:
        raise RuntimeError("watchdog Lambda did not become active and current")

    scheduler_trust = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "scheduler.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": ACCOUNT,
                    "aws:SourceArn":
                        f"arn:aws:scheduler:{REGION}:{ACCOUNT}:schedule-group/default"
                },
            },
        }],
    }
    scheduler_role_arn = ensure_role(
        iam, SCHEDULER_ROLE_NAME, scheduler_trust,
        "Invokes only the v5 Stage S shutdown watchdog Lambda.",
    )
    put_inline_policy(
        iam, SCHEDULER_ROLE_NAME, "invoke-v5-stage-s-watchdog",
        {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": ["lambda:InvokeFunction"],
                "Resource": function_arn,
            }],
        },
    )
    return function_arn, role_arn, scheduler_role_arn, sha256(source)


def simulate_permission(iam, role_arn, action, resource, expected, context=None):
    request = {
        "PolicySourceArn": role_arn,
        "ActionNames": [action],
        "ResourceArns": [resource],
    }
    if context is not None:
        request["ContextEntries"] = context
    result = iam.simulate_principal_policy(**request)
    decision = result["EvaluationResults"][0]["EvalDecision"]
    if decision != expected:
        raise RuntimeError(f"IAM policy check failed for {action}: {decision}, expected {expected}")
    return decision


def direct_watchdog_smoke(lambdas):
    response = lambdas.invoke(
        FunctionName=WATCHDOG_FUNCTION,
        InvocationType="RequestResponse",
        Payload=json.dumps({"test_kind": "direct_smoke"}).encode("utf-8"),
    )
    body = json.loads(response["Payload"].read().decode("utf-8"))
    if response.get("FunctionError") or body.get("found") != 0 or body.get("terminated") != 0:
        raise RuntimeError("direct watchdog smoke check did not return zero targets")
    return body


def scheduler_smoke(scheduler, function_arn, role_arn):
    scheduled_for = (utc_now() + dt.timedelta(minutes=2)).replace(second=0, microsecond=0)
    expression = "at(" + scheduled_for.strftime("%Y-%m-%dT%H:%M:%S") + ")"
    try:
        scheduler.get_schedule(Name=TEST_SCHEDULE_NAME, GroupName="default")
        scheduler.delete_schedule(Name=TEST_SCHEDULE_NAME, GroupName="default")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            raise
    create_args = {
        "Name": TEST_SCHEDULE_NAME,
        "GroupName": "default",
        "ScheduleExpression": expression,
        "ScheduleExpressionTimezone": "UTC",
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "ActionAfterCompletion": "DELETE",
        "State": "ENABLED",
        "Target": {
            "Arn": function_arn,
            "RoleArn": role_arn,
            "Input": json.dumps({"test_kind": "scheduler_smoke"}),
            "RetryPolicy": {"MaximumEventAgeInSeconds": 300, "MaximumRetryAttempts": 2},
        },
        "Description": "No-instance smoke test for the v5 Stage S cloud watchdog.",
    }
    for attempt in range(24):
        try:
            scheduler.create_schedule(**create_args)
            break
        except ClientError as create_exc:
            error = create_exc.response.get("Error", {})
            message = error.get("Message", "").lower()
            if (error.get("Code") != "ValidationException"
                    or "execution role" not in message
                    or "assume the role" not in message or attempt == 23):
                raise
            time.sleep(5)
    return expression


def put_s3_once(s3, relative_key, body, content_type="application/octet-stream"):
    key = RUN_PREFIX + "/" + relative_key
    digest = sha256(body)
    try:
        head = s3.head_object(Bucket=BUCKET, Key=key)
        if head.get("Metadata", {}).get("sha256") != digest:
            raise RuntimeError(f"existing S3 input differs: {key}")
        return {"key": key, "sha256": digest, "bytes": len(body), "uploaded": False}
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchKey", "NotFound"}:
            raise
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=body,
        ContentType=content_type,
        ServerSideEncryption="AES256",
        Metadata={"sha256": digest},
    )
    return {"key": key, "sha256": digest, "bytes": len(body), "uploaded": True}


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not present; key value was not read or printed")
    return key


def put_secure_parameter(ssm, api_key):
    try:
        current = ssm.get_parameter(Name=PARAMETER_NAME, WithDecryption=True)["Parameter"]["Value"]
        if current != api_key:
            raise RuntimeError("the existing secure parameter does not match the current API key")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ParameterNotFound":
            raise
        ssm.put_parameter(
            Name=PARAMETER_NAME,
            Description="Temporary v5 Stage S Anthropic key; remove after Stage S cleanup.",
            Value=api_key,
            Type="SecureString",
            Tier="Standard",
            Overwrite=False,
        )
        current = ssm.get_parameter(Name=PARAMETER_NAME, WithDecryption=True)["Parameter"]["Value"]
        if current != api_key:
            raise RuntimeError("secure parameter round-trip verification failed")
    return "SecureString round-trip PASS; key value not displayed"


def verify_bucket(s3, check_empty):
    location = s3.get_bucket_location(Bucket=BUCKET).get("LocationConstraint") or "us-east-1"
    if location != REGION:
        raise RuntimeError("evidence bucket is outside the frozen us-west-2 region")
    public = s3.get_public_access_block(Bucket=BUCKET)["PublicAccessBlockConfiguration"]
    if not all(public.values()):
        raise RuntimeError("S3 public-access blocking is not fully enabled")
    encryption = s3.get_bucket_encryption(Bucket=BUCKET)["ServerSideEncryptionConfiguration"]
    algorithms = {
        rule["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"]
        for rule in encryption["Rules"]
    }
    if algorithms != {"AES256"}:
        raise RuntimeError("the evidence bucket is not using the frozen AES256 encryption")
    versioning = s3.get_bucket_versioning(Bucket=BUCKET)
    if versioning.get("Status") != "Enabled":
        raise RuntimeError("the evidence bucket versioning state changed")
    try:
        s3.get_bucket_lifecycle_configuration(Bucket=BUCKET)
        raise RuntimeError("an S3 lifecycle policy exists; verify it cannot delete v5 evidence before archive")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchLifecycleConfiguration":
            raise
        lifecycle = "absent"
    if check_empty:
        result = s3.list_objects_v2(Bucket=BUCKET, Prefix=RUN_PREFIX + "/", MaxKeys=1000)
        unexpected = [
            row["Key"] for row in result.get("Contents", [])
            if not (row["Key"].startswith(RUN_PREFIX + "/input/")
                    or row["Key"].startswith(RUN_PREFIX + "/provenance/"))
        ]
        if unexpected:
            raise RuntimeError("unexpected Stage S output objects already exist")
    return {"region": location, "public_access_block": public, "encryption": "AES256",
            "versioning": "Enabled", "lifecycle": lifecycle}


def prepare():
    api_key = get_api_key()
    model_ids = model_ids_check(api_key)
    caller_arn, hourly_rate, sentinel_hourly_rate, total_estimate = verify_account_and_limits()
    s3 = client("s3")
    bucket_security = verify_bucket(s3, check_empty=True)
    ssm = client("ssm")
    hashes = {}
    for name, path in FILES.items():
        data = path.read_bytes()
        digest = sha256(data)
        if name in EXPECTED and digest != EXPECTED[name]:
            raise RuntimeError(f"frozen input hash mismatch: {name}")
        hashes[name] = digest

    iam = client("iam")
    instance_role_arn, instance_policy = ensure_instance_profile(iam)
    function_arn, watchdog_role_arn, scheduler_role_arn, watchdog_sha = ensure_watchdog(
        iam, client("lambda"))
    simulate_permission(
        iam, instance_role_arn, "ssm:GetParameter",
        f"arn:aws:ssm:{REGION}:{ACCOUNT}:parameter{PARAMETER_NAME}", "allowed")
    instance_arn = f"arn:aws:ec2:{REGION}:{ACCOUNT}:instance/i-0123456789abcdef0"
    tag_context = [{
        "ContextKeyName": f"ec2:ResourceTag/{RUN_TAG_KEY}",
        "ContextKeyValues": [RUN_TAG_VALUE],
        "ContextKeyType": "string",
    }]
    simulate_permission(
        iam, instance_role_arn, "ec2:TerminateInstances", instance_arn, "allowed",
        context=tag_context)
    simulate_permission(
        iam, instance_role_arn, "ec2:TerminateInstances", instance_arn, "implicitDeny")

    lambda_client = client("lambda")
    direct_result = direct_watchdog_smoke(lambda_client)
    schedule_expression = scheduler_smoke(client("scheduler"), function_arn, scheduler_role_arn)

    entries = {}
    for name, path in FILES.items():
        content_type = "application/x-ndjson" if name.endswith(".jsonl") else "application/octet-stream"
        entries[name] = put_s3_once(s3, "input/" + name, path.read_bytes(), content_type)
    entries["user_data_stage_s.sh"] = put_s3_once(
        s3, "provenance/user_data_stage_s.sh",
        (ROOT / "user_data_stage_s.sh").read_bytes(), "text/x-shellscript")
    input_manifest = {
        "run_id": RUN_ID,
        "caller_arn": caller_arn,
        "bucket_security": bucket_security,
        "aws_hourly_rate_usd": hourly_rate,
        "watchdog_test_hourly_rate_usd": sentinel_hourly_rate,
        "aws_max_scenario_estimate_usd": total_estimate,
        "max_public_ipv4_estimate_usd": str(decimal.Decimal("0.005") * decimal.Decimal("3")),
        "anthropic_model_ids_verified": model_ids,
        "qwen_model": "Qwen/Qwen2.5-1.5B-Instruct",
        "qwen_revision": QWEN_REVISION,
        "mistral_model": "mistralai/Mistral-7B-Instruct-v0.3",
        "mistral_revision": MISTRAL_REVISION,
        "watchdog_sha256": watchdog_sha,
        "source_sha256": hashes,
        "cloud_setup_sha256": file_hash(ROOT / "cloud_setup_stage_s.py"),
        "inputs": {
            name: {key: value for key, value in entry.items() if key != "uploaded"}
            for name, entry in entries.items()
        },
        "watchdog_direct_smoke": direct_result,
        "watchdog_scheduler_smoke_scheduled": True,
        "watchdog_target_proof_required": True,
        "watchdog_test_instance_type": WATCHDOG_TEST_INSTANCE_TYPE,
        "watchdog_test_max_seconds": WATCHDOG_TEST_MAX_SECONDS,
        "watchdog_test_root_volume_gib": WATCHDOG_TEST_ROOT_GIB,
        "watchdog_proof_script_sha256": hashes["watchdog_e2e_proof.py"],
        "parameter_name": PARAMETER_NAME,
        "parameter_type": "SecureString",
        "secret_value_recorded": False,
        "ec2_role_name": INSTANCE_ROLE_NAME,
        "instance_profile_name": INSTANCE_PROFILE_NAME,
        "lambda_function_name": WATCHDOG_FUNCTION,
        "aws_instance_type": INSTANCE_TYPE,
        "aws_ami_id": AMI_ID,
        "aws_subnet_id": SUBNET_ID,
        "aws_security_group_id": SECURITY_GROUP_ID,
        "aws_instance_permissions": instance_policy,
    }
    put_s3_once(s3, "input/input_manifest.json",
                json.dumps(input_manifest, indent=2, sort_keys=True).encode("utf-8"),
                "application/json")
    secret_status = put_secure_parameter(ssm, api_key)
    del api_key
    print(json.dumps({
        "prepare": "PASS",
        "caller_arn": caller_arn,
        "aws_hourly_rate_usd": hourly_rate,
        "watchdog_test_hourly_rate_usd": sentinel_hourly_rate,
        "aws_max_scenario_estimate_usd": total_estimate,
        "anthropic_model_ids": model_ids,
        "bucket_security": bucket_security,
        "watchdog_direct_smoke": direct_result,
        "watchdog_scheduler_smoke_at": schedule_expression,
        "secure_parameter": secret_status,
        "s3_input_count": len(entries) + 1,
        "no_model_inference_performed": True,
    }, sort_keys=True))


def scheduler_smoke_passed(logs):
    group = "/aws/lambda/" + WATCHDOG_FUNCTION
    response = logs.filter_log_events(
        logGroupName=group,
        startTime=int((utc_now() - dt.timedelta(minutes=5)).timestamp() * 1000),
        filterPattern="scheduler_smoke",
        limit=20,
    )
    for event in response.get("events", []):
        message = event.get("message", "")
        if RUN_ID in message and "found': 0" in message and "event_kind': 'scheduler_smoke'" in message:
            return True
    return False


def watchdog_target_proof_passed(s3):
    try:
        response = s3.get_object(Bucket=BUCKET, Key=WATCHDOG_PROOF_KEY)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404", "NotFound"}:
            return False
        raise
    body = response["Body"].read()
    if response.get("Metadata", {}).get("sha256") != sha256(body):
        return False
    proof = json.loads(body.decode("utf-8"))
    watchdog_result = proof.get("lambda_watchdog_result") or {}
    tag_results = proof.get("iam_tag_policy_results") or {}
    direct = proof.get("direct_smoke") or {}
    return (
        proof.get("status") == "PASS"
        and proof.get("run_id") == RUN_ID
        and proof.get("watchdog_sha256") == file_hash(ROOT / "cloud_watchdog.py")
        and proof.get("proof_script_sha256") == file_hash(ROOT / "watchdog_e2e_proof_attempt3.py")
        and proof.get("instance_type") == WATCHDOG_TEST_INSTANCE_TYPE
        and proof.get("no_public_ip") is True
        and proof.get("root_volume_gib") == WATCHDOG_TEST_ROOT_GIB
        and proof.get("root_volume_deleted") is True
        and 0 <= proof.get("prior_watchdog_ec2_seconds", WATCHDOG_TEST_MAX_SECONDS + 1)
        and 0 < proof.get("tracked_ec2_seconds", WATCHDOG_TEST_MAX_SECONDS + 1)
        and proof.get("cumulative_watchdog_ec2_seconds", WATCHDOG_TEST_MAX_SECONDS + 1) == proof.get("prior_watchdog_ec2_seconds", WATCHDOG_TEST_MAX_SECONDS + 1) + proof.get("tracked_ec2_seconds", WATCHDOG_TEST_MAX_SECONDS + 1)
        and proof.get("cumulative_watchdog_ec2_seconds", WATCHDOG_TEST_MAX_SECONDS + 1) <= WATCHDOG_TEST_MAX_SECONDS
        and direct.get("found") == 0
        and direct.get("terminated") == 0
        and proof.get("scheduler_smoke_log_timestamp_ms") is not None
        and tag_results.get("exact_run_tag") == "allowed"
        and tag_results.get("different_run_tag") == "implicitDeny"
        and watchdog_result.get("run_id") == RUN_ID
        and watchdog_result.get("found") == 1
        and watchdog_result.get("terminated") == 1
        and watchdog_result.get("states") == ["running"]
    )

def launch():
    caller_arn, hourly_rate, sentinel_hourly_rate, total_estimate = verify_account_and_limits()
    if not scheduler_smoke_passed(client("logs")):
        raise RuntimeError("cloud Scheduler smoke test has not fired successfully; no EC2 launch")
    s3 = client("s3")
    verify_bucket(s3, check_empty=False)
    if not watchdog_target_proof_passed(s3):
        raise RuntimeError("live-target AWS watchdog proof is missing or failed; no EC2 launch")
    ssm = client("ssm")
    ssm.get_parameter(Name=PARAMETER_NAME)
    ec2 = client("ec2")
    active = ec2.describe_instances(
        Filters=[
            {"Name": "instance-type", "Values": [INSTANCE_TYPE]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping"]},
            {"Name": f"tag:{RUN_TAG_KEY}", "Values": [RUN_TAG_VALUE]},
        ])
    if any(reservation.get("Instances") for reservation in active.get("Reservations", [])):
        raise RuntimeError("a tagged Stage S EC2 instance is already active")
    offerings = ec2.describe_instance_type_offerings(
        LocationType="availability-zone",
        Filters=[
            {"Name": "instance-type", "Values": [INSTANCE_TYPE]},
            {"Name": "location", "Values": ["us-west-2b"]},
        ],
    )
    if not offerings.get("InstanceTypeOfferings"):
        raise RuntimeError("g5.2xlarge is not offered in the frozen Stage S subnet AZ")

    scheduler = client("scheduler")
    stop_at = (utc_now() + dt.timedelta(minutes=86)).replace(second=0, microsecond=0)
    if stop_at <= utc_now() + dt.timedelta(minutes=85):
        stop_at += dt.timedelta(minutes=1)
    expression = "at(" + stop_at.strftime("%Y-%m-%dT%H:%M:%S") + ")"
    function_arn = f"arn:aws:lambda:{REGION}:{ACCOUNT}:function:{WATCHDOG_FUNCTION}"
    scheduler_role_arn = f"arn:aws:iam::{ACCOUNT}:role/{SCHEDULER_ROLE_NAME}"
    scheduler.create_schedule(
        Name=RUN_SCHEDULE_NAME,
        GroupName="default",
        ScheduleExpression=expression,
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        ActionAfterCompletion="DELETE",
        State="ENABLED",
        Target={
            "Arn": function_arn,
            "RoleArn": scheduler_role_arn,
            "Input": json.dumps({"test_kind": "scheduled_watchdog"}),
            "RetryPolicy": {"MaximumEventAgeInSeconds": 300, "MaximumRetryAttempts": 2},
        },
        Description="Terminates only the tagged v5 Stage S instance before its 90-minute cap.",
    )
    user_data = (ROOT / "user_data_stage_s.sh").read_text(encoding="utf-8")
    try:
        result = ec2.run_instances(
            ImageId=AMI_ID,
            InstanceType=INSTANCE_TYPE,
            MinCount=1,
            MaxCount=1,
            IamInstanceProfile={"Name": INSTANCE_PROFILE_NAME},
            NetworkInterfaces=[{
                "DeviceIndex": 0,
                "SubnetId": SUBNET_ID,
                "Groups": [SECURITY_GROUP_ID],
                "AssociatePublicIpAddress": True,
                "DeleteOnTermination": True,
            }],
            BlockDeviceMappings=[{
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "VolumeSize": 100,
                    "VolumeType": "gp3",
                    "DeleteOnTermination": True,
                },
            }],
            InstanceInitiatedShutdownBehavior="terminate",
            MetadataOptions={
                "HttpEndpoint": "enabled",
                "HttpTokens": "required",
                "HttpPutResponseHopLimit": 1,
            },
            TagSpecifications=[
                {"ResourceType": "instance", "Tags": [
                    {"Key": "Name", "Value": "typed-probe-v5-stage-s"},
                    {"Key": RUN_TAG_KEY, "Value": RUN_TAG_VALUE},
                    {"Key": "Project", "Value": "typed-probe-v5"},
                    {"Key": "Stage", "Value": "S"},
                ]},
                {"ResourceType": "volume", "Tags": [
                    {"Key": RUN_TAG_KEY, "Value": RUN_TAG_VALUE},
                    {"Key": "Project", "Value": "typed-probe-v5"},
                    {"Key": "Stage", "Value": "S"},
                ]},
            ],
            UserData=user_data,
        )
    except Exception:
        scheduler.delete_schedule(Name=RUN_SCHEDULE_NAME, GroupName="default")
        raise
    instance = result["Instances"][0]
    print(json.dumps({
        "launch": "SUBMITTED",
        "instance_id": instance["InstanceId"],
        "state": instance["State"]["Name"],
        "availability_zone": instance["Placement"]["AvailabilityZone"],
        "instance_type": instance["InstanceType"],
        "watchdog_schedule": expression,
        "caller_arn": caller_arn,
        "aws_hourly_rate_usd": hourly_rate,
        "watchdog_test_hourly_rate_usd": sentinel_hourly_rate,
        "aws_max_scenario_estimate_usd": total_estimate,
        "root_volume_gib": 100,
        "root_delete_on_termination": True,
        "model_inference_location": "AWS EC2 only",
    }, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "launch"])
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    else:
        launch()


if __name__ == "__main__":
    main()
