"""Dedicated saved-prefix AWS parent. Plan is offline; paid execution needs approval.

Only the explicit --execute path may reserve or create resources. The old V7
experiment launcher is never invoked; only its frozen ownership/cleanup helpers
are reused. No neural library is imported or executed on the client.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
WORKER_SOURCE_SHA = "13f424981d7434b1a92815d1ad5759d543bbd3be"
SOURCE_ARCHIVE_SHA = "c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1"
DEVELOPMENT_ARCHIVE_SHA = "1874508d0baad7d6620001505c39f184b3cb091c59de4e96197f309beee0a042"
BUNDLE_MANIFEST_SHA = "b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629"
PREFIX_MANIFEST_SHA = "10f3283e5dcb3045dac2131e021d3ca383c35ae8b34c9e439e7fc82ff58cdd9c"
OLD_HELPER_PINS = {
    "aws/launch_prototype_v7.py": "90f7a8086416ac39c49d9d344d33b128ae19106638f335ceb14cdd26f038577a",
    "aws/budget.py": "77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0",
    "tools/experiment_profiles_prototype_v7.py": "3331ce53d6f3f57b94cb7603f2b53f3c309a899ab2596b4b040fa1b01ccf6ee0",
}
PARENT_FILES = ("aws/launch_prefix_diagnostic_v8.py", "aws/prefix_remote_v8.py",
                "aws/prefix_diagnostic_launch_v8.py")
EXPERIMENT = {"profile": "saved_prefix_diagnostic_v8", "entrypoint": "cas_meta2.diagnostic_v8.gpu"}
INPUT_KEYS = ("source.zip", "development.zip", "remote.py", "permit.json")
RESULT_KEYS = ("artifacts.zip", "complete.json", "bootstrap.log")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
JOB = re.compile(r"cas-meta2-[0-9]{14}-[0-9a-f]{8}\Z")


class LaunchRefused(ValueError):
    pass


def require(value, reason):
    if not value:
        raise LaunchRefused(reason)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decoded(raw):
    def unique(items):
        value = {}
        for key, entry in items:
            require(key not in value, "DUPLICATE_JSON_KEY")
            value[key] = entry
        return value
    value = json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(LaunchRefused("NONFINITE_JSON")))
    encoded(value)
    return value


def digest(raw):
    return sha256(raw).hexdigest()


def safe_file(path, maximum=32 * 1024**2):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "SOURCE_OR_EVIDENCE_LINK_REFUSED")
    require(path.is_file() and path.stat().st_size <= maximum, "BOUNDED_REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "FILE_SIZE_CEILING")
    return raw


def read_pinned(path, expected, maximum=32 * 1024**2):
    require(type(expected) is str and HEX64.fullmatch(expected), "EXACT_SHA256_REQUIRED")
    raw = safe_file(path, maximum)
    require(digest(raw) == expected, "PINNED_FILE_CHANGED")
    return raw


def verify_parent_source(parent_sha):
    """Check new executable files against a separate actual Git commit, pre-import."""
    require(type(parent_sha) is str and re.fullmatch(r"[0-9a-f]{40}", parent_sha),
            "EXACT_PARENT_SOURCE_COMMIT_REQUIRED")
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    resolved = subprocess.check_output(["git", "rev-parse", parent_sha + "^{commit}"], cwd=repo, text=True).strip()
    require(resolved == parent_sha, "EXACT_PARENT_SOURCE_COMMIT_REQUIRED")
    result = {}
    for relative in PARENT_FILES:
        path = ROOT / relative
        committed = subprocess.check_output(["git", "show", parent_sha + ":" + path.relative_to(repo).as_posix()], cwd=repo)
        require(safe_file(path) == committed, "PARENT_SOURCE_BYTES_CHANGED:" + relative)
        result[relative] = digest(committed)
    return result


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "PINNED_MODULE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def helpers(parent_sha, source=None):
    identity = verify_parent_source(parent_sha)
    preparation = load_module("cas_meta2_prefix_preparation_parent", ROOT / "aws/prefix_diagnostic_launch_v8.py")
    if source is not None:
        for relative, expected in OLD_HELPER_PINS.items():
            require(digest(safe_file(ROOT / relative)) == expected
                    and source["files_sha256"]["research/CAS_META_2_COMPOSITION/" + relative] == expected,
                    "FROZEN_HELPER_CHANGED:" + relative)
        old = load_module("cas_meta2_prefix_owned_plumbing", ROOT / "aws/launch_prototype_v7.py")
        remote = load_module("cas_meta2_prefix_remote", ROOT / "aws/prefix_remote_v8.py")
        return preparation, old, remote, identity
    return preparation, identity


def resource_plan():
    return {"instance_count": 1, "gpu_count": 1, "instance_type": "g7.2xlarge",
        "account_id": "807562639912", "region": "us-west-2", "ami_id": "ami-0fbbd0facbc9e3cff",
        "runtime_seconds_max": 3600, "worker_seconds_max": 1800,
        "cloud_shutdown_seconds": 3480, "guest_shutdown_seconds": 3400,
        "automatic_retries": 0, "on_demand_hourly_usd_max": "2.52", "ancillary_reserved_usd": "1.00",
        "per_launch_reserved_cap_usd": "4.00", "ebs_gb": 75, "ebs_type": "gp3",
        "ebs_iops": 3000, "ebs_throughput_mib_per_second": 125,
        "ebs_encrypted": True, "delete_on_termination": True,
        "artifact_bytes_max": 256 * 1024**2, "evidence_expanded_bytes_max": 512 * 1024**2,
        "artifact_objects_max": 3, "s3_retention_days": 7,
        "input_bytes_max": 16 * 1024**2, "download_bytes_max": 256 * 1024**2,
        "s3_read_requests_max": 1000, "s3_write_requests_max": 1000,
        "scheduler_invocations_max": 1,
        "inbound_rules": [], "egress_tcp_ports": [443], "required_gpu_name_contains": "RTX PRO 4500",
        "training": False, "native_execution": False, "later_curriculum_execution": False,
        "local_neural_execution": False}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == "cas-meta2-prefix-launch-request/8",
            "DEDICATED_PREFIX_REQUEST_REQUIRED")
    require(type(request.get("job")) is str and JOB.fullmatch(request["job"]), "EXACT_UNIQUE_JOB_REQUIRED")
    require(request.get("experiment") == EXPERIMENT and request.get("resource_plan") == resource_plan(),
            "EXACT_DIAGNOSTIC_SCOPE_AND_RESOURCE_PLAN_REQUIRED")
    require(request.get("worker_source_sha") == WORKER_SOURCE_SHA
            and request.get("source_archive_sha256") == SOURCE_ARCHIVE_SHA
            and request.get("development_archive_sha256") == DEVELOPMENT_ARCHIVE_SHA
            and request.get("bundle_manifest_sha256") == BUNDLE_MANIFEST_SHA,
            "FROZEN_WORKER_AND_DEVELOPMENT_IDENTITIES_REQUIRED")
    require(type(request.get("subnet_id")) is str and re.fullmatch(r"subnet-[0-9a-f]{8,17}", request["subnet_id"]),
            "EXPLICIT_SUBNET_REQUIRED")
    require(request.get("approval_required") is True and request.get("launch_authorized") is False,
            "REQUEST_IS_NOT_LAUNCH_AUTHORITY")
    require(request.get("task_counts") == {"train_probe": 24, "validation": 96, "checkpoints": 4,
                "reference_decisions_per_checkpoint": 2272, "forced_per_checkpoint": 360},
            "FROZEN_DEVELOPMENT_COUNTS_REQUIRED")


def build_request(parent_sha, subnet_id, source_archive, development_bundle, development_archive):
    preparation, identity = helpers(parent_sha)
    source = preparation.inspect_source_archive(source_archive)
    development = preparation.inspect_development(development_bundle, development_archive, source)
    # Also verify every imported ownership/cleanup helper before claiming a connected parent.
    helpers(parent_sha, source)
    observed_budget = preparation.observe_budget()
    plan = resource_plan()
    preparation._budget_module().validate_plan(plan, "4.00")
    request = {"schema": "cas-meta2-prefix-launch-request/8", "experiment": EXPERIMENT,
        "job": "cas-meta2-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8],
        "parent_source_sha": parent_sha, "parent_file_sha256": identity,
        "worker_source_sha": WORKER_SOURCE_SHA, "source_archive_sha256": SOURCE_ARCHIVE_SHA,
        "development_archive_sha256": DEVELOPMENT_ARCHIVE_SHA, "bundle_manifest_sha256": BUNDLE_MANIFEST_SHA,
        "source_archive": str(Path(source_archive).absolute()), "development_bundle": str(Path(development_bundle).absolute()),
        "development_archive": str(Path(development_archive).absolute()), "subnet_id": subnet_id,
        "resource_plan": plan, "task_counts": {"train_probe": 24, "validation": 96, "checkpoints": 4,
            "reference_decisions_per_checkpoint": 2272, "forced_per_checkpoint": 360},
        "budget_observation": observed_budget, "approval_required": True, "launch_authorized": False,
        "provider_price_or_capacity_checked_by_this_command": False,
        "cost_bound_at_declared_ceiling_usd": "3.52", "not_an_aws_invoice_or_account_spend_cap": True}
    validate_request(request)
    return request


def validate_owner_approval(path, expected, request, request_sha256):
    approval = decoded(read_pinned(path, expected, 1024**2))
    wanted = {"schema": "cas-meta2-prefix-owner-approval/8", "approved": True,
        "launch_request_sha256": request_sha256, "job": request["job"],
        "parent_source_sha": request["parent_source_sha"], "worker_source_sha": WORKER_SOURCE_SHA,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA, "development_archive_sha256": DEVELOPMENT_ARCHIVE_SHA,
        "bundle_manifest_sha256": BUNDLE_MANIFEST_SHA, "max_cost_usd": "4.00"}
    require(all(type(approval.get(k)) is type(v) and approval[k] == v for k, v in wanted.items()),
            "EXPLICIT_JOB_SPECIFIC_FUTURE_OWNER_APPROVAL_REQUIRED")
    evidence = approval.get("user_message", {})
    require(type(evidence.get("path")) is str and Path(evidence["path"]).is_absolute(),
            "ORIGINAL_USER_APPROVAL_MESSAGE_REQUIRED")
    raw = read_pinned(evidence["path"], evidence.get("sha256"), 1024**2)
    require(raw.decode("utf-8").strip().casefold().removesuffix(".") == "approve the $4 diagnostic",
            "EXACT_USER_APPROVAL_LINE_REQUIRED")
    return {**wanted, "approval_artifact_sha256": expected,
            "user_message": {"path": evidence["path"], "sha256": digest(raw)}}


def provider_json(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: provider_json(entry) for key, entry in value.items()}
    if isinstance(value, (list, tuple)):
        return [provider_json(entry) for entry in value]
    return value


class BoundedS3:
    """No transfer-manager retries; reserve 600 requests per class for the guest."""
    def __init__(self, client):
        self.client = client
        self.counts = {"read": 0, "write": 0}

    def __getattr__(self, name):
        require(name not in ("upload_file", "download_file", "get_paginator", "get_waiter"),
                "UNBOUNDED_TRANSFER_OR_ITERATOR_REFUSED")
        method = getattr(self.client, name)
        def call(*args, **kwargs):
            kind = "read" if name.startswith(("get_", "head_", "list_")) else "write"
            require(self.counts[kind] < 400, "PARENT_S3_REQUEST_CEILING")
            self.counts[kind] += 1
            return method(*args, **kwargs)
        return call


def download_once(s3, bucket, key, output, maximum):
    response = s3.get_object(Bucket=bucket, Key=key)
    require(type(response.get("ContentLength")) is int and 0 <= response["ContentLength"] <= maximum,
            "DOWNLOAD_CONTENT_LENGTH_CEILING")
    total = 0
    body = response["Body"]
    try:
        with Path(output).open("xb") as stream:
            while True:
                block = body.read(min(1024**2, maximum - total + 1))
                if not block:
                    break
                total += len(block)
                require(total <= maximum, "DOWNLOAD_STREAM_CEILING")
                stream.write(block)
            require(total == response["ContentLength"], "DOWNLOAD_TRUNCATED")
            stream.flush(); os.fsync(stream.fileno())
    finally:
        body.close()
    return total


def client_factory(profile, region):
    # This function is reached only after exact owner approval and source checks.
    import boto3
    from botocore.config import Config
    cfg = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=profile, region_name=region)
    clients = {name: session.client(name, config=cfg) for name in
               ("sts", "ec2", "iam", "s3", "scheduler", "service-quotas")}
    clients["s3"] = BoundedS3(clients["s3"])
    clients["pricing"] = session.client("pricing", region_name="us-east-1", config=cfg)
    return clients


def current_price_bound(pricing):
    """No free-tier credit; known metered items must fit the $1 ancillary reserve."""
    queries = {
        "gp3_gb_month": ("AmazonEC2", "GB-Mo", "0.08", {"location": "US West (Oregon)", "volumeApiName": "gp3", "productFamily": "Storage"}),
        "ipv4_hour": ("AmazonVPC", "Hrs", "0.005", {"location": "US West (Oregon)", "usagetype": "USW2-PublicIPv4:InUseAddress"}),
        "s3_gb_month": ("AmazonS3", "GB-Mo", "0.023", {"location": "US West (Oregon)", "usagetype": "USW2-TimedStorage-ByteHrs"}),
        "s3_write_request": ("AmazonS3", "Requests", "0.000005", {"location": "US West (Oregon)", "usagetype": "USW2-Requests-Tier1"}),
        "s3_read_request": ("AmazonS3", "Requests", "0.0000004", {"location": "US West (Oregon)", "usagetype": "USW2-Requests-Tier2"}),
        "internet_out_gb": ("AWSDataTransfer", "GB", "0.09", {"fromLocation": "US West (Oregon)", "toLocation": "External", "transferType": "AWS Outbound"}),
    }
    observations, rates = {}, {}
    for key, (service, unit, ceiling, fields) in queries.items():
        response = pricing.get_products(ServiceCode=service, FormatVersion="aws_v1", MaxResults=100,
            Filters=[{"Type": "TERM_MATCH", "Field": k, "Value": v} for k, v in fields.items()])
        require(not response.get("NextToken") and len(response.get("PriceList", [])) == 1,
                "ANCILLARY_PRICE_IDENTITY_OR_PAGINATION:" + key)
        product = decoded(response["PriceList"][0])
        values = [Decimal(d["pricePerUnit"]["USD"]) for term in product["terms"]["OnDemand"].values()
                  for d in term["priceDimensions"].values() if d["unit"] == unit]
        require(values and all(v.is_finite() and v >= 0 for v in values)
                and 0 < max(values) <= Decimal(ceiling), "ANCILLARY_PRICE_EXCEEDS_CEILING:" + key)
        rates[key] = max(values)
        observations[key] = {"response": response, "usd_per_unit": str(rates[key]), "unit": unit}
    gb = Decimal(1024**2) / Decimal(10**9)
    amounts = {"ebs": Decimal(75) * rates["gp3_gb_month"] / Decimal(720),
        "ipv4": rates["ipv4_hour"], "retention": Decimal(272) * gb * Decimal(8) / Decimal(30) * rates["s3_gb_month"],
        "download": Decimal(256) * gb * rates["internet_out_gb"],
        # LIST is Tier1-priced; conservatively price both 1,000-call budgets at Tier1.
        "requests": Decimal(2000) * max(rates["s3_write_request"], rates["s3_read_request"]),
        "scheduler": Decimal("0.000001")}
    total = sum(amounts.values())
    require(total <= Decimal("1.00"), "ANCILLARY_RESERVATION_TOO_SMALL")
    return {"observations": observations, "item_bound_usd": {k: str(v) for k, v in amounts.items()},
        "ancillary_metered_bound_usd": str(total), "compute_plus_metered_bound_usd": str(Decimal("2.52") + total),
        "scheduler_rate_basis": "https://aws.amazon.com/eventbridge/pricing/ ($1 per million invocations, no free-tier credit)",
        "s3_expiration_days": 7, "storage_arithmetic_days": 8,
        "unmodeled": "Taxes and abnormal provider/control-plane delay; reservation is not a provider billing cap."}


def provider_preflight(clients, request):
    """Read-only checks immediately before reservation and provider creation."""
    plan = request["resource_plan"]
    identity = clients["sts"].get_caller_identity()
    require(identity["Account"] == plan["account_id"], "AWS_ACCOUNT_MISMATCH")
    ec2 = clients["ec2"]
    subnets = ec2.describe_subnets(SubnetIds=[request["subnet_id"]])["Subnets"]
    require(len(subnets) == 1 and subnets[0]["State"] == "available"
            and subnets[0]["AvailableIpAddressCount"] > 0, "CURRENT_SUBNET_UNAVAILABLE")
    subnet = subnets[0]
    routes = ec2.describe_route_tables(Filters=[{"Name": "association.subnet-id", "Values": [request["subnet_id"]]}])
    if not routes.get("RouteTables") and not routes.get("NextToken"):
        routes = ec2.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [subnet["VpcId"]]},
            {"Name": "association.main", "Values": ["true"]}])
    require(not routes.get("NextToken") and len(routes.get("RouteTables", [])) == 1,
            "EXACT_EFFECTIVE_ROUTE_TABLE_REQUIRED")
    internet = [r for r in routes["RouteTables"][0]["Routes"] if r.get("DestinationCidrBlock") == "0.0.0.0/0"]
    require(len(internet) == 1 and internet[0].get("State") == "active"
            and re.fullmatch(r"igw-[0-9a-f]+", internet[0].get("GatewayId", "")),
            "DIRECT_INTERNET_GATEWAY_REQUIRED_NO_NAT_CHARGES")
    gateway = ec2.describe_internet_gateways(InternetGatewayIds=[internet[0]["GatewayId"]])["InternetGateways"]
    require(len(gateway) == 1 and any(a.get("VpcId") == subnet["VpcId"] and a.get("State") == "available"
            for a in gateway[0].get("Attachments", [])), "ATTACHED_INTERNET_GATEWAY_REQUIRED")
    dns = ec2.describe_vpc_attribute(VpcId=subnet["VpcId"], Attribute="enableDnsSupport")
    require(dns.get("EnableDnsSupport", {}).get("Value") is True, "VPC_DNS_REQUIRED")
    acls = ec2.describe_network_acls(Filters=[{"Name": "association.subnet-id", "Values": [request["subnet_id"]]}])
    require(not acls.get("NextToken") and len(acls.get("NetworkAcls", [])) == 1, "EXACT_EFFECTIVE_NETWORK_ACL_REQUIRED")
    for direction in (False, True):
        entries = sorted([entry for entry in acls["NetworkAcls"][0]["Entries"]
                          if entry.get("Egress") is direction and "CidrBlock" in entry], key=lambda e: e["RuleNumber"])
        require(entries and entries[0].get("RuleAction") == "allow" and entries[0].get("Protocol") == "-1"
                and entries[0].get("CidrBlock") == "0.0.0.0/0", "UNSUPPORTED_OR_BLOCKING_NETWORK_ACL")
    images = ec2.describe_images(ImageIds=[plan["ami_id"]])["Images"]
    require(len(images) == 1 and images[0]["State"] == "available"
            and images[0]["RootDeviceName"] == "/dev/sda1" and images[0]["OwnerId"] == "898082745236"
            and images[0]["Architecture"] == "x86_64", "PINNED_AMI_UNAVAILABLE")
    quota = clients["service-quotas"].get_service_quota(ServiceCode="ec2", QuotaCode="L-DB2E81BA")
    current_g = ec2.describe_instances(Filters=[{"Name": "instance-type", "Values": ["g*", "vt*"]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "shutting-down"]}])
    require(not current_g.get("NextToken"), "PAGINATED_ACCOUNT_GPU_USAGE_UNCONFIRMED")
    instances = [i for reservation in current_g["Reservations"] for i in reservation["Instances"]]
    types = {i["InstanceType"] for i in instances} | {"g7.2xlarge"}
    descriptions = ec2.describe_instance_types(InstanceTypes=sorted(types))
    require(not descriptions.get("NextToken") and {d["InstanceType"] for d in descriptions["InstanceTypes"]} == types,
            "GPU_VCPU_IDENTITIES_UNCONFIRMED")
    vcpus = {d["InstanceType"]: d["VCpuInfo"]["DefaultVCpus"] for d in descriptions["InstanceTypes"]}
    used = sum(vcpus[i["InstanceType"]] for i in instances)
    require(vcpus["g7.2xlarge"] == 8 and quota["Quota"]["Value"] >= used + 8,
            "CURRENT_ACCOUNT_GPU_QUOTA_HEADROOM_BELOW_EIGHT_VCPUS")
    offerings = ec2.describe_instance_type_offerings(LocationType="availability-zone", Filters=[
        {"Name": "instance-type", "Values": [plan["instance_type"]]},
        {"Name": "location", "Values": [subnet["AvailabilityZone"]]}])
    require(not offerings.get("NextToken") and len(offerings["InstanceTypeOfferings"]) == 1,
            "GPU_TYPE_NOT_OFFERED_IN_SUBNET_ZONE")
    active = ec2.describe_instances(Filters=[{"Name": "tag-key", "Values": ["cas_meta_job"]},
        {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "shutting-down"]}])
    require(not active.get("NextToken") and not any(r["Instances"] for r in active["Reservations"]),
            "EXISTING_ACTIVE_CAS_JOB_REQUIRES_RECONCILIATION")
    fields = {"instanceType": plan["instance_type"], "location": "US West (Oregon)", "operatingSystem": "Linux",
        "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used", "marketoption": "OnDemand", "operation": "RunInstances"}
    price = clients["pricing"].get_products(ServiceCode="AmazonEC2", Filters=[
        {"Type": "TERM_MATCH", "Field": k, "Value": v} for k, v in fields.items()])
    require(not price.get("NextToken"), "PAGINATED_PRICE_NOT_ACCEPTED")
    rates = [Decimal(d["pricePerUnit"]["USD"]) for raw in price["PriceList"]
             for term in decoded(raw)["terms"]["OnDemand"].values()
             for d in term["priceDimensions"].values() if d["unit"] == "Hrs"]
    require(len(rates) == 1 and rates[0].is_finite() and 0 < rates[0] <= Decimal("2.52"),
            "CURRENT_PRICE_EXCEEDS_APPROVED_PLAN")
    ancillary = current_price_bound(clients["pricing"])
    return {"identity": identity, "subnet": subnet, "image": images[0], "quota": quota,
        "effective_routes": routes, "internet_gateway": gateway[0], "dns": dns, "network_acls": acls,
        "account_gpu_vcpus_in_use": used, "account_gpu_instances": current_g,
        "offerings": offerings, "price_response": price, "instance_hourly_usd": str(rates[0]),
        "ancillary_cost_check": ancillary,
        "capacity_reserved_or_guaranteed": False}


def worker_permit(request, source, reservation, ledger, instance_id, deadline):
    require(re.fullmatch(r"i-[0-9a-f]{17}", instance_id), "REAL_INSTANCE_ID_REQUIRED")
    base = "/opt/cas-meta2-prefix/"
    plan = {"schema": "cas-meta2-prefix-diagnostic-plan/8", "launch_enabled": True,
        "job": request["job"], "instance_id": instance_id, "source_sha": WORKER_SOURCE_SHA,
        "bundle_manifest_sha256": BUNDLE_MANIFEST_SHA, "max_seconds": 1800, "batch_size": 16,
        "tasks_per_checkpoint": 120, "seed": 7,
        "checkpoints": ["cas_initial", "cas_selected", "generic_initial", "generic_selected"],
        "max_cost_usd": "4.00", "resource_plan": request["resource_plan"],
        "source_manifest": {"path": base + "package/prefix_source_manifest.json", "sha256": PREFIX_MANIFEST_SHA},
        "source_archive": {"path": base + "source.zip", "sha256": SOURCE_ARCHIVE_SHA},
        "reservation_receipt": {"path": base + "launch/reservation_receipt.json", "sha256": digest(encoded(reservation))},
        "ledger_snapshot": {"path": base + "launch/ledger_snapshot.json", "sha256": digest(encoded(ledger))}}
    return {"job": request["job"], "archive_sha256": SOURCE_ARCHIVE_SHA,
        "cloud_deadline_confirmed": True, "instance_id": instance_id, "deadline": deadline.isoformat(),
        "worker_plan": plan, "worker_plan_sha256": digest(encoded(plan)),
        "reservation_receipt": reservation, "ledger_snapshot": ledger}


def remote_config(request, source):
    with ZipFile(io.BytesIO(read_pinned(request["source_archive"], SOURCE_ARCHIVE_SHA))) as archive:
        manifest = decoded(archive.read("prefix_source_manifest.json"))
    return {"schema": "cas-meta2-prefix-remote-config/8", "job": request["job"],
        "bucket": request["job"] + "-" + request["resource_plan"]["account_id"],
        "region": "us-west-2", "account_id": "807562639912",
        "parent_source_sha": request["parent_source_sha"], "worker_source_sha": WORKER_SOURCE_SHA,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA, "development_archive_sha256": DEVELOPMENT_ARCHIVE_SHA,
        "bundle_manifest_sha256": BUNDLE_MANIFEST_SHA, "source_manifest_sha256": PREFIX_MANIFEST_SHA,
        "source_manifest": manifest, "package_layout": source["package_layout"],
        "resource_plan": request["resource_plan"], "max_worker_seconds": 1800,
        "artifact_bytes_max": 256 * 1024**2, "evidence_expanded_bytes_max": 512 * 1024**2,
        "experiment": EXPERIMENT}


def execute(request_path, request_sha256, approval_path, approval_sha256, receipt_dir, profile="default"):
    request = decoded(read_pinned(request_path, request_sha256, 2 * 1024**2))
    validate_request(request)
    approval = validate_owner_approval(approval_path, approval_sha256, request, request_sha256)
    preparation, identity = helpers(request["parent_source_sha"])
    require(identity == request["parent_file_sha256"], "REQUEST_PARENT_SOURCE_CHANGED")
    source = preparation.inspect_source_archive(request["source_archive"])
    preparation.inspect_development(request["development_bundle"], request["development_archive"], source)
    preparation, old, remote, identity = helpers(request["parent_source_sha"], source)
    output = Path(receipt_dir).absolute()
    require(not output.exists() and output.resolve().is_relative_to((ROOT / "records").resolve())
            and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                        for p in (output, *output.parents)), "NEW_RECEIPT_DIRECTORY_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    preflight_receipt = {"schema": "cas-meta2-prefix-provider-preflight/8", "job": request["job"],
        "request_sha256": request_sha256, "status": "PREFLIGHT_ATTEMPT_STARTED",
        "new_reservation": False, "provider_resources_created": False}
    (output / "preflight_receipt.json").write_bytes(encoded(preflight_receipt))
    with old.campaign_execution_lock():
        try:
            # The request's observation is never substituted for a current canonical read.
            ledger = old.budget.read_ledger()
            require(Decimal(ledger["remaining_unreserved_usd"]) >= Decimal("4.00"), "CAMPAIGN_BUDGET_EXHAUSTED")
            clients = client_factory(profile, "us-west-2")
            preflight = provider_preflight(clients, request)
            preflight_receipt.update(status="PREFLIGHT_READS_PASSED", result=provider_json(preflight))
        except BaseException as error:
            preflight_receipt.update(status="LAUNCH_PREFLIGHT_REFUSED", error=type(error).__name__, reason=str(error))
            (output / "preflight_receipt.json").write_bytes(encoded(preflight_receipt))
            (output / "launch_receipt.json").write_bytes(encoded(preflight_receipt))
            return preflight_receipt
        (output / "preflight_receipt.json").write_bytes(encoded(preflight_receipt))
        return _run_authorized(request, request_sha256, approval, source, old, remote, clients, preflight, output)


def _run_authorized(request, request_sha256, approval, source, old, remote, clients, preflight, output):
    """Dedicated orchestration; contract tests supply fake clients and fake ledger."""
    plan, job = request["resource_plan"], request["job"]
    s3, ec2, iam, scheduler = (clients[name] for name in ("s3", "ec2", "iam", "scheduler"))
    config = remote_config(request, source)
    bucket = config["bucket"]
    worker_role, timer_role = job + "-worker", job + "-timer"
    tags = [{"Key": "cas_meta_job", "Value": job}]
    receipt = {"schema": "cas-meta2-prefix-launch-receipt/8", "status": "STARTING",
        "job": job, "request_sha256": request_sha256, "approval": approval,
        "parent_source_sha": request["parent_source_sha"], "source_sha": WORKER_SOURCE_SHA,
        "archive_sha256": SOURCE_ARCHIVE_SHA, "development_archive_sha256": DEVELOPMENT_ARCHIVE_SHA,
        "bundle_manifest_sha256": BUNDLE_MANIFEST_SHA, "plan": plan, "experiment": EXPERIMENT,
        "provider_preflight": provider_json(preflight), "resources": {}, "events": [], "cleanup_errors": []}
    output.mkdir(parents=True, exist_ok=True)
    def save():
        path = output / "launch_receipt.json"
        raw = encoded(receipt)
        with path.open("wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    def record(event, **details):
        receipt["events"].append({"utc": datetime.now(timezone.utc).isoformat(), "event": event, **provider_json(details)})
        save()
    receipt["budget_reservation_state"] = "NOT_ATTEMPTED"
    save()
    try:
        # Source bytes and rendering are checked before reservation or provider mutation.
        script = remote.render_remote(config)
        bootstrap = remote.user_data(config, digest(script.encode()))
        require(len(bootstrap.encode()) <= 16384, "EC2_USER_DATA_SIZE_CEILING")
        require(verify_parent_source(request["parent_source_sha"]) == request["parent_file_sha256"],
                "PARENT_CHANGED_BEFORE_RESERVATION")
        source_bytes = read_pinned(request["source_archive"], SOURCE_ARCHIVE_SHA)
        development_bytes = read_pinned(request["development_archive"], DEVELOPMENT_ARCHIVE_SHA)
        require(len(source_bytes) + len(development_bytes) + len(script.encode()) + 1024**2 <= plan["input_bytes_max"],
                "INPUT_UPLOAD_CEILING")
        receipt["budget_reservation_state"] = "ATTEMPTED_OUTCOME_UNCONFIRMED"
        record("BUDGET_RESERVATION_ATTEMPTED", reserved_usd="4.00", worker_source_sha=WORKER_SOURCE_SHA)
        reservation = old.budget.reserve_budget(job, WORKER_SOURCE_SHA, SOURCE_ARCHIVE_SHA, "4.00", plan)
        receipt["task_budget_reservation"] = reservation
        receipt["budget_reservation_state"] = "RESERVED_NO_AUTOMATIC_REFUND"
        record("BUDGET_RESERVED_BEFORE_PROVIDER_CREATION", reserved_usd="4.00", worker_source_sha=WORKER_SOURCE_SHA)
        ledger = old.budget.read_ledger()
        require(digest(encoded(ledger)) == reservation["ledger_sha256"], "RESERVED_LEDGER_SNAPSHOT_CHANGED")
        for name, value in (("reservation_receipt.json", reservation), ("ledger_snapshot.json", ledger),
                            ("launch_request.json", request)):
            with (output / name).open("xb") as stream:
                stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())
    except BaseException as error:
        receipt["status"] = "PREPROVIDER_PREPARATION_OR_RESERVATION_FAILED"
        receipt["provider_resources_created"] = False
        record("PREPROVIDER_FAILURE", error=type(error).__name__, message=str(error))
        return receipt
    iid = None
    launch_attempted = artifact_verified = False
    def role(name, service, statements):
        trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}]}
        created = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Tags=tags)["Role"]
        receipt["resources"][name] = created["Arn"]; save()
        iam.put_role_policy(RoleName=name, PolicyName="job-only", PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}))
        return created["Arn"]
    try:
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "us-west-2"})
        receipt["resources"]["bucket"] = bucket; save()
        s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tags})
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={k: True for k in
            ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")})
        s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})
        s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={"Rules": [{"ID": "job-seven-days", "Status": "Enabled", "Filter": {"Prefix": ""}, "Expiration": {"Days": 7}, "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1}}]})
        role(worker_role, "ec2.amazonaws.com", [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": [f"arn:aws:s3:::{bucket}/input/{key}" for key in INPUT_KEYS]},
            {"Effect": "Allow", "Action": ["s3:PutObject"], "Resource": [f"arn:aws:s3:::{bucket}/results/{key}" for key in RESULT_KEYS]}])
        iam.create_instance_profile(InstanceProfileName=worker_role, Tags=tags)
        receipt["resources"]["instance_profile"] = worker_role; save()
        iam.add_role_to_instance_profile(InstanceProfileName=worker_role, RoleName=worker_role)
        timer_arn = role(timer_role, "scheduler.amazonaws.com", [{"Effect": "Allow", "Action": "ec2:TerminateInstances", "Resource": f"arn:aws:ec2:us-west-2:807562639912:instance/*", "Condition": {"StringEquals": {"ec2:ResourceTag/cas_meta_job": job}}}])
        sg = ec2.create_security_group(GroupName=job, Description="CAS prefix diagnostic outbound HTTPS only", VpcId=preflight["subnet"]["VpcId"], TagSpecifications=[{"ResourceType": "security-group", "Tags": tags}])["GroupId"]
        receipt["resources"]["security_group"] = sg; save()
        ec2.revoke_security_group_egress(GroupId=sg, IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        ec2.authorize_security_group_egress(GroupId=sg, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        s3.put_object(Bucket=bucket, Key="input/source.zip", Body=source_bytes)
        s3.put_object(Bucket=bucket, Key="input/development.zip", Body=development_bytes)
        s3.put_object(Bucket=bucket, Key="input/remote.py", Body=script.encode())
        record("REMOTE_AND_BOOTSTRAP_PINNED", remote_sha256=digest(script.encode()), bootstrap_sha256=digest(bootstrap.encode()))
        time.sleep(10)  # IAM propagation only; no job retry.
        launched_at = datetime.now(timezone.utc)
        cloud_deadline = launched_at + timedelta(seconds=plan["cloud_shutdown_seconds"])
        lifetime_deadline = launched_at + timedelta(seconds=3600)
        launch_attempted = True
        record("INSTANCE_LAUNCH_ATTEMPTED", client_token=job, lifetime_deadline=lifetime_deadline.isoformat())
        launched = ec2.run_instances(ImageId=plan["ami_id"], InstanceType="g7.2xlarge", MinCount=1, MaxCount=1,
            ClientToken=job, IamInstanceProfile={"Name": worker_role}, InstanceInitiatedShutdownBehavior="terminate",
            MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"}, NetworkInterfaces=[{"DeviceIndex": 0,
                "SubnetId": request["subnet_id"], "Groups": [sg], "AssociatePublicIpAddress": True, "DeleteOnTermination": True}],
            BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 75, "VolumeType": "gp3", "Iops": 3000,
                "Throughput": 125, "Encrypted": True, "DeleteOnTermination": True}}],
            TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}], UserData=bootstrap)
        require(len(launched["Instances"]) == 1, "ONE_INSTANCE_RESPONSE_REQUIRED")
        iid = launched["Instances"][0]["InstanceId"]
        receipt["resources"]["instance"] = iid
        receipt["provider_launch_time"] = launched["Instances"][0].get("LaunchTime", launched_at).isoformat()
        record("INSTANCE_CREATED", instance_id=iid)
        target = {"Arn": "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances", "RoleArn": timer_arn,
            "Input": json.dumps({"InstanceIds": [iid]}), "RetryPolicy": {"MaximumRetryAttempts": 0, "MaximumEventAgeInSeconds": 60}}
        expression = "at(" + cloud_deadline.strftime("%Y-%m-%dT%H:%M:%S") + ")"
        receipt["resources"]["schedule"] = job; save()
        scheduler.create_schedule(Name=job, ScheduleExpression=expression, ScheduleExpressionTimezone="UTC",
            FlexibleTimeWindow={"Mode": "OFF"}, Target=target, ActionAfterCompletion="DELETE")
        confirmed = scheduler.get_schedule(Name=job)
        old.verify_schedule(confirmed, target, expression)
        require(datetime.now(timezone.utc) < cloud_deadline - timedelta(seconds=2040),
                "INSUFFICIENT_INSTANCE_TIME_FOR_UNSHORTENED_WORKER")
        record("CLOUD_DEADLINE_CONFIRMED", schedule=job, provider_response=confirmed)
        permit = worker_permit(request, source, reservation, ledger, iid, cloud_deadline)
        require(len(encoded(permit)) <= 1024**2, "PERMIT_UPLOAD_CEILING")
        with (output / "worker_plan.json").open("xb") as stream:
            stream.write(encoded(permit["worker_plan"])); stream.flush(); os.fsync(stream.fileno())
        s3.put_object(Bucket=bucket, Key="input/permit.json", Body=encoded(permit))
        record("WORKER_PERMIT_PUBLISHED_AFTER_CONFIRMED_SHUTDOWN", worker_plan_sha256=permit["worker_plan_sha256"])
        while datetime.now(timezone.utc) < cloud_deadline - timedelta(seconds=30):
            try:
                response = s3.get_object(Bucket=bucket, Key="results/complete.json")
                try:
                    raw = response["Body"].read(1024**2 + 1)
                finally:
                    response["Body"].close()
                require(len(raw) <= 1024**2, "RESULT_RECEIPT_CEILING")
                result = decoded(raw)
                require(result.get("job") == job and type(result.get("sha256")) is str and HEX64.fullmatch(result["sha256"])
                    and type(result.get("bytes")) is int and 0 < result["bytes"] <= plan["artifact_bytes_max"] - 2 * 1024**2
                    and result.get("experiment") == EXPERIMENT and type(result.get("returncode")) is int,
                    "REMOTE_RESULT_IDENTITY_SIZE_OR_EXPERIMENT")
                head = s3.head_object(Bucket=bucket, Key="results/artifacts.zip")
                require(head["ContentLength"] == result["bytes"], "REMOTE_RESULT_SIZE_MISMATCH")
                artifact = output / "cloud_artifacts.zip"
                download_once(s3, bucket, "results/artifacts.zip", artifact, result["bytes"])
                collection = old.verify_downloaded_packet(artifact, result, job, WORKER_SOURCE_SHA, plan, experiment=EXPERIMENT)
                artifact_verified = True
                receipt.update(result=result, artifact_collection=collection,
                    status="AWS_DIAGNOSTIC_FINISHED" if result["returncode"] == 0 else "AWS_DIAGNOSTIC_FAILED")
                record("ARTIFACT_DOWNLOADED_AND_HASH_VERIFIED", sha256=result["sha256"], bytes=result["bytes"])
                break
            except Exception as error:
                code = getattr(error, "response", {}).get("Error", {}).get("Code")
                if code not in ("NoSuchKey", "404"):
                    raise
            current = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]
            old.check_tag(current.get("Tags", []), job)
            require(current.get("ClientToken") == job, "INSTANCE_CLIENT_TOKEN_MISMATCH")
            require(current["State"]["Name"] not in ("terminated", "shutting-down"), "INSTANCE_ENDED_WITHOUT_COMPLETION_RECEIPT")
            time.sleep(15)
        else:
            raise LaunchRefused("LOCAL_WATCHDOG_DEADLINE")
    except BaseException as error:
        receipt["status"] = "AWS_DIAGNOSTIC_BLOCKED_OR_FAILED"
        record("ERROR", error=type(error).__name__, message=str(error))
    finally:
        terminated = not launch_attempted
        if launch_attempted and iid is None:
            try:
                recovered = old.reconcile_instance(ec2, job)
                iid = recovered["InstanceId"]
                receipt["resources"]["instance"] = iid
                record("INSTANCE_IDENTITY_RECOVERED", instance_id=iid)
            except Exception as error:
                receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED:" + str(error))
        if iid:
            try:
                old.terminate_owned_instance(ec2, iid, job, artifact_verified=artifact_verified, record=record)
                terminated = True
                record("INSTANCE_TERMINATION_CONFIRMED", instance_id=iid)
            except Exception as error:
                receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED:" + str(error))
        if terminated:
            if iid:
                try:
                    remaining = old.confirm_deleted_volumes(ec2, job, record)
                    receipt["remaining_job_volumes"] = remaining
                    require(not remaining, "EBS_DELETION_NOT_CONFIRMED")
                except Exception as error:
                    receipt["cleanup_errors"].append("EBS_CHECK_FAILED:" + str(error))
            old.remove_owned_auxiliary_resources(ec2, iam, scheduler, receipt, job, worker_role, timer_role, record)
        if "bucket" in receipt["resources"]:
            try:
                head = s3.head_object(Bucket=bucket, Key="results/bootstrap.log")
                require(head["ContentLength"] <= 1024**2, "BOOTSTRAP_LOG_CEILING")
                path = output / "bootstrap.log"
                download_once(s3, bucket, "results/bootstrap.log", path, 1024**2)
                receipt["bootstrap_log_sha256"] = digest(safe_file(path, 1024**2))
            except Exception as error:
                receipt["bootstrap_log_status"] = str(getattr(error, "response", {}).get("Error", {}).get("Code", type(error).__name__))
            try:
                old.check_tag(s3.get_bucket_tagging(Bucket=bucket)["TagSet"], job)
                listed = s3.list_objects_v2(Bucket=bucket, Prefix="results/")
                objects = listed.get("Contents", [])
                require(not listed.get("IsTruncated") and len(objects) <= 3
                    and {x["Key"] for x in objects}.issubset({"results/" + key for key in RESULT_KEYS})
                    and sum(x["Size"] for x in objects) <= plan["artifact_bytes_max"], "RESULT_OBJECT_LIMIT_UNCONFIRMED")
                receipt["stored_result_objects"] = provider_json(objects)
                if terminated and artifact_verified:
                    s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": "input/" + key} for key in INPUT_KEYS]})
                    record("OWNED_INPUTS_REMOVED_AFTER_VERIFIED_DOWNLOAD")
            except Exception as error:
                receipt["cleanup_errors"].append("S3_OWNERSHIP_OR_RETENTION_CHECK:" + str(error))
        receipt["termination_confirmed"] = terminated
        receipt["artifact_verified"] = artifact_verified
        receipt["s3_retention"] = "Dedicated job bucket objects expire after 7 days; local evidence retained."
        receipt["billing_boundary"] = "Reservation and resource/deadline checks, not an AWS invoice or provider-enforced account spending cap."
        if receipt["cleanup_errors"]:
            receipt["status"] = "CLEANUP_REQUIRES_ATTENTION"
        save()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--parent-source-sha")
    parser.add_argument("--source-archive")
    parser.add_argument("--development-bundle")
    parser.add_argument("--development-archive")
    parser.add_argument("--subnet-id")
    parser.add_argument("--request")
    parser.add_argument("--request-sha256")
    parser.add_argument("--approval")
    parser.add_argument("--approval-sha256")
    parser.add_argument("--receipt-dir")
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    try:
        require(not (args.execute and args.plan), "PLAN_AND_EXECUTE_ARE_EXCLUSIVE")
        if not args.execute:
            if args.parent_source_sha:
                request = build_request(args.parent_source_sha, args.subnet_id, args.source_archive,
                                        args.development_bundle, args.development_archive)
                result = {"request": request, "request_sha256": digest(encoded(request)), "provider_calls": False,
                          "new_reservation": False, "approval_required": True}
            else:
                result = {"resource_plan": resource_plan(), "status": "SOURCE_BOUND_REQUEST_NOT_YET_BUILT",
                    "provider_calls": False, "new_reservation": False, "approval_required": True}
            print(json.dumps(result, sort_keys=True, indent=2)); return 0
        require(all((args.request, args.request_sha256, args.approval, args.approval_sha256, args.receipt_dir)),
                "EXPLICIT_EXECUTE_REQUEST_APPROVAL_AND_RECEIPT_REQUIRED")
        receipt = execute(args.request, args.request_sha256, args.approval, args.approval_sha256, args.receipt_dir, args.profile)
        print(json.dumps({"status": receipt["status"], "receipt_dir": args.receipt_dir}, sort_keys=True))
        return 0 if receipt["status"] == "AWS_DIAGNOSTIC_FINISHED" else 1
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "LAUNCH_REFUSED", "reason": str(error)}, sort_keys=True)); return 2


if __name__ == "__main__":
    raise SystemExit(main())
