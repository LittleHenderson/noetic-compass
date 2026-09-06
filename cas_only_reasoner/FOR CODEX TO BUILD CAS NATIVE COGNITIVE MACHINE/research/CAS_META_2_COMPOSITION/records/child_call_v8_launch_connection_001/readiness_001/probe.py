"""One read-only AWS readiness/pricing observation. Never reserve or launch."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import sys
import time

import boto3
import botocore
from botocore.config import Config
from botocore.exceptions import ClientError

HERE = Path(__file__).resolve().parent
ACCOUNT = "807562639912"
REGION = "us-west-2"
SUBNET = "subnet-0eb3ca4bf5ca98f24"
VPC = "vpc-0df2f8cc1b9f23838"
AMI = "ami-0fbbd0facbc9e3cff"
OLD_JOB = "cas-meta2-20260906094002-39762c47"
OLD_INSTANCE = "i-0cba54498bb3a3745"
ALLOW = {
    "sts": {"get_caller_identity"},
    "ec2": {"describe_instance_types", "describe_images", "describe_subnets", "describe_vpcs",
            "describe_vpc_attribute", "describe_route_tables", "describe_network_acls",
            "describe_internet_gateways", "describe_instance_type_offerings", "describe_instances",
            "describe_volumes"},
    "service-quotas": {"get_service_quota"},
    "pricing": {"get_products"},
    "scheduler": {"get_schedule"},
    "iam": {"get_role", "get_instance_profile"},
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def encoded(data):
    return (json.dumps(data, sort_keys=True, indent=2, default=str, allow_nan=False) + "\n").encode()


def save(name, data):
    raw = encoded(data)
    with (HERE / name).open("xb") as stream:
        stream.write(raw)
    return {"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def metadata(raw):
    return {k: raw.get("ResponseMetadata", {}).get(k) for k in
            ("RequestId", "HTTPStatusCode", "RetryAttempts")}


def instance_rows(raw):
    rows = []
    for group in raw.get("Reservations", []):
        for item in group["Instances"]:
            rows.append({k: item.get(k) for k in ("InstanceId", "InstanceType", "InstanceLifecycle",
                "State", "StateTransitionReason", "LaunchTime", "ImageId", "SubnetId", "VpcId",
                "Placement", "CpuOptions", "BlockDeviceMappings")}
                | {"cas_meta_job": {x["Key"]: x["Value"] for x in item.get("Tags", [])}.get("cas_meta_job")})
    return {"Instances": rows, "NextToken": raw.get("NextToken")}


def selector(*keys):
    return lambda raw: {k: raw.get(k) for k in keys}


def call(clients, label, service, method, params, select=None):
    assert method in ALLOW[service]
    started, tick = utc(), time.monotonic()
    record = {"schema": "cas-meta2-readonly-provider-query/8", "label": label,
              "service": service, "method": method, "parameters": params,
              "profile": "default", "region": "us-east-1" if service == "pricing" else REGION,
              "started_utc": started, "provider_mutations": 0}
    try:
        raw = getattr(clients[service], method)(**params)
        record.update(status="OK", response=(select(raw) if select else
                      {k: v for k, v in raw.items() if k != "ResponseMetadata"}),
                      response_metadata=metadata(raw))
    except ClientError as error:
        record.update(status="AWS_ERROR", error=error.response.get("Error"),
                      response_metadata=metadata(error.response))
    except Exception as error:
        # No credential values, request signing data or environment variables.
        record.update(status="LOCAL_ERROR", error={"type": type(error).__name__})
    record.update(finished_utc=utc(), wall_seconds=time.monotonic() - tick,
                  sanitization="HTTP headers and signing data omitted; instance responses restricted to scoped state/resource fields.")
    receipt = save(label + ".json", record)
    print(json.dumps({"label": label, "status": record["status"], "file": receipt}), flush=True)
    return record


def price(label, service, fields):
    return (label, "pricing", "get_products", {"ServiceCode": service, "FormatVersion": "aws_v1",
        "MaxResults": 100, "Filters": [{"Type": "TERM_MATCH", "Field": k, "Value": v}
                                        for k, v in fields.items()]}, None)


def main():
    if (HERE / "execution_receipt.json").exists() or (HERE / "01_identity.json").exists():
        raise SystemExit("NEW_OBSERVATION_REQUIRED")
    started, tick = utc(), time.monotonic()
    session = boto3.Session(profile_name="default", region_name=REGION)
    config = Config(connect_timeout=10, read_timeout=20, retries={"max_attempts": 0})
    clients = {name: session.client(name, region_name="us-east-1" if name == "pricing" else REGION,
                                    config=config) for name in ALLOW}
    identity = call(clients, "01_identity", "sts", "get_caller_identity", {}, selector("Account", "Arn"))
    results = [identity]
    if identity.get("response", {}).get("Account") != ACCOUNT:
        save("execution_receipt.json", {"status": "READINESS_BLOCKED:ACCOUNT_OR_CREDENTIALS", "identity": identity,
             "provider_mutations": 0, "started_utc": started, "finished_utc": utc()})
        return 2
    jobs = [
        ("02_instance_type", "ec2", "describe_instance_types", {"InstanceTypes": ["g7.2xlarge"]}, None),
        ("03_ami", "ec2", "describe_images", {"ImageIds": [AMI]}, None),
        ("04_subnet", "ec2", "describe_subnets", {"SubnetIds": [SUBNET]}, None),
        ("05_vpc", "ec2", "describe_vpcs", {"VpcIds": [VPC]}, None),
        ("06_routes", "ec2", "describe_route_tables", {"Filters": [{"Name": "vpc-id", "Values": [VPC]}]}, None),
        ("07_network_acl", "ec2", "describe_network_acls", {"Filters": [{"Name": "association.subnet-id", "Values": [SUBNET]}]}, None),
        ("08_internet_gateway", "ec2", "describe_internet_gateways", {"Filters": [{"Name": "attachment.vpc-id", "Values": [VPC]}]}, None),
        ("09_dns_support", "ec2", "describe_vpc_attribute", {"VpcId": VPC, "Attribute": "enableDnsSupport"}, None),
        ("10_dns_hostnames", "ec2", "describe_vpc_attribute", {"VpcId": VPC, "Attribute": "enableDnsHostnames"}, None),
        ("11_offering", "ec2", "describe_instance_type_offerings", {"LocationType": "availability-zone", "Filters": [
            {"Name": "instance-type", "Values": ["g7.2xlarge"]}, {"Name": "location", "Values": ["us-west-2c"]}]}, None),
        ("12_gpu_quota", "service-quotas", "get_service_quota", {"ServiceCode": "ec2", "QuotaCode": "L-DB2E81BA"}, None),
        ("13_tagged_jobs", "ec2", "describe_instances", {"Filters": [{"Name": "tag-key", "Values": ["cas_meta_job"]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped", "shutting-down"]}]}, instance_rows),
        ("14_running_gpu_usage", "ec2", "describe_instances", {"Filters": [{"Name": "instance-type", "Values": ["g*", "vt*"]},
            {"Name": "instance-state-name", "Values": ["pending", "running"]}]}, instance_rows),
        ("15_previous_instance", "ec2", "describe_instances", {"InstanceIds": [OLD_INSTANCE]}, instance_rows),
        ("16_previous_volumes", "ec2", "describe_volumes", {"Filters": [{"Name": "tag:cas_meta_job", "Values": [OLD_JOB]}]}, None),
        ("17_previous_schedule", "scheduler", "get_schedule", {"Name": OLD_JOB}, selector("Name", "State", "ScheduleExpression", "ActionAfterCompletion")),
        ("18_previous_worker_role", "iam", "get_role", {"RoleName": OLD_JOB + "-worker"}, lambda r: {"Role": {k: r["Role"].get(k) for k in ("RoleName", "Arn", "CreateDate")}}),
        ("19_previous_timer_role", "iam", "get_role", {"RoleName": OLD_JOB + "-timer"}, lambda r: {"Role": {k: r["Role"].get(k) for k in ("RoleName", "Arn", "CreateDate")}}),
        ("20_previous_profile", "iam", "get_instance_profile", {"InstanceProfileName": OLD_JOB + "-worker"}, lambda r: {"InstanceProfile": {k: r["InstanceProfile"].get(k) for k in ("InstanceProfileName", "Arn", "CreateDate")}}),
        price("21_compute_price", "AmazonEC2", {"instanceType": "g7.2xlarge", "location": "US West (Oregon)",
              "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used",
              "marketoption": "OnDemand", "operation": "RunInstances"}),
        price("22_ebs_price", "AmazonEC2", {"location": "US West (Oregon)", "volumeApiName": "gp3", "productFamily": "Storage"}),
        price("23_ipv4_price", "AmazonVPC", {"location": "US West (Oregon)", "usagetype": "USW2-PublicIPv4:InUseAddress"}),
        price("24_s3_storage", "AmazonS3", {"location": "US West (Oregon)", "productFamily": "Storage", "storageClass": "General Purpose"}),
        price("25_s3_requests_tier1", "AmazonS3", {"location": "US West (Oregon)", "usagetype": "USW2-Requests-Tier1"}),
        price("26_s3_requests_tier2", "AmazonS3", {"location": "US West (Oregon)", "usagetype": "USW2-Requests-Tier2"}),
        price("27_s3_transfer", "AmazonS3", {"location": "US West (Oregon)", "usagetype": "USW2-DataTransfer-Out-Bytes"}),
    ]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(call, clients, *args) for args in jobs]
        results.extend(future.result() for future in futures)
    receipt = {"schema": "cas-meta2-readonly-readiness-execution/8", "status": "READONLY_QUERIES_COMPLETED",
        "started_utc": started, "finished_utc": utc(), "wall_seconds": time.monotonic() - tick,
        "command": [sys.executable, "-B", str(Path(__file__).resolve())], "cwd": str(Path.cwd()),
        "python": sys.version, "boto3": boto3.__version__, "botocore": botocore.__version__,
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "profile": "default",
        "account": ACCOUNT, "region": REGION, "provider_mutations": 0, "reservation_created": False,
        "worker_launched": False, "query_status": {r["label"]: r["status"] for r in results},
        "files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p.read_bytes()).hexdigest()}
                  for p in sorted(HERE.glob("[0-9][0-9]_*.json"))},
        "boundaries": ["Read access is not proof of provisioning permissions.",
          "Instance-type offering and quota are not an allocation/capacity guarantee.",
          "No paid run, no GPU test, no quota request, no resource creation or deletion.",
          "Prices are current informational published list prices, not an invoice or provider-enforced spend cap."]}
    result = save("execution_receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "receipt": result, "query_count": len(results)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
