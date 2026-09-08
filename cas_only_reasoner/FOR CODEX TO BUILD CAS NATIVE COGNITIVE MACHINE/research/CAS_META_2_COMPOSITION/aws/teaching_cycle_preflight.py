"""Read-only AWS observations and conservative teaching-job cost worksheet.

No reservation or resource creation. The SDK is imported only by the explicit
CLI. Raw price responses are retained; public rates are not a final invoice.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ACCOUNT = "807562639912"
REGION = "us-west-2"
AMI = "ami-0fbbd0facbc9e3cff"
INSTANCE = "g7.2xlarge"
PRICE_QUERIES = {
    "compute": ("AmazonEC2", {"instanceType": INSTANCE, "regionCode": REGION,
        "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA",
        "capacitystatus": "Used", "marketoption": "OnDemand", "operation": "RunInstances"}, "Hrs"),
    "ebs": ("AmazonEC2", {"regionCode": REGION, "usagetype": "USW2-EBS:VolumeUsage.gp3"}, "GB-Mo"),
    "ipv4": ("AmazonVPC", {"regionCode": REGION, "usagetype": "USW2-PublicIPv4:InUseAddress"}, "Hrs"),
    "s3_storage": ("AmazonS3", {"regionCode": REGION, "usagetype": "USW2-TimedStorage-ByteHrs"}, "GB-Mo"),
    "s3_put": ("AmazonS3", {"regionCode": REGION, "usagetype": "USW2-Requests-Tier1"}, "Requests"),
    "s3_get": ("AmazonS3", {"regionCode": REGION, "usagetype": "USW2-Requests-Tier2"}, "Requests"),
    "egress": ("AWSDataTransfer", {"fromRegionCode": REGION, "transferType": "AWS Outbound"}, "GB"),
}


def require(condition, code):
    if not condition:
        raise ValueError("TEACHING_PREFLIGHT:" + code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False, default=str) + "\n").encode()


def highest_rate(response, unit):
    require(not response.get("NextToken"), "PRICE_PAGINATION_REJECTED")
    require(type(response.get("PriceList")) is list and 0 < len(response["PriceList"]) <= 20,
            "PRICE_PRODUCTS_REQUIRED")
    rates = []
    for raw in response["PriceList"]:
        product = json.loads(raw)
        for term in product.get("terms", {}).get("OnDemand", {}).values():
            for dimension in term.get("priceDimensions", {}).values():
                require(dimension.get("unit") == unit, "PRICE_UNIT_MISMATCH")
                rate = Decimal(dimension["pricePerUnit"]["USD"])
                require(rate.is_finite() and rate >= 0, "INVALID_PRICE")
                rates.append(rate)
    require(rates and max(rates) > 0, "NONZERO_PRICE_REQUIRED")
    return max(rates)  # No free-tier, volume discount, or account credit assumption.


def worksheet(prices):
    rates = {name: highest_rate(prices[name], definition[2]) for name, definition in PRICE_QUERIES.items()}
    require(rates["compute"] <= Decimal("2.52"), "COMPUTE_RATE_ABOVE_CEILING")
    # Round bytes UP to 3 decimal GB, storage duration UP to a full month,
    # EBS month DOWN to 28 days. Charge every S3 call at the more expensive tier.
    # $1 is additional allowance for setup traffic, scheduler and taxes/rounding;
    # not a claim about an unknown account's final tax treatment.
    costs = {
        "compute_7200_seconds": rates["compute"] * 2,
        "ebs_75_gib_7200_seconds": rates["ebs"] * 75 * 2 / (28 * 24),
        "one_ipv4_7200_seconds": rates["ipv4"] * 2,
        "s3_3gb_full_month_conservative": rates["s3_storage"] * 3,
        "s3_2048_calls_highest_tier": max(rates["s3_put"], rates["s3_get"]) * 2048,
        "internet_egress_3gb": rates["egress"] * 3,
        "other_allowance": Decimal("1.00"),
    }
    total = sum(costs.values())
    require(total <= Decimal("8.00"), "TOTAL_ABOVE_RESERVATION")
    return {"rates_usd": {k: str(v) for k, v in rates.items()},
        "cost_components_usd": {k: str(v) for k, v in costs.items()},
        "estimated_bound_usd": str(total), "reservation_usd": "8.00",
        "remaining_buffer_usd": str(Decimal("8.00") - total),
        "is_invoice": False, "free_tier_or_credit_assumed": False,
        "conditions": ["At most 7200 instance seconds and one public IPv4 address.",
            "75 GiB gp3 at included 3000 IOPS / 125 MiB/s, deleted with instance.",
            "At most 2048 shared S3 calls; no workload or download retries.",
            "One <=2.5GiB result archive plus bounded control files, <3GB total stored/outbound.",
            "Same-region S3 traffic; no NAT gateway, snapshots or extra volumes.",
            "Seven-day S3 expiration policy, conservatively costed for one full month.",
            "Actual fees, taxes, service failures and timing must be reconciled afterward."]}


def observe(clients):
    ec2 = clients["ec2"]
    identity = clients["sts"].get_caller_identity()
    require(identity.get("Account") == ACCOUNT, "ACCOUNT_MISMATCH")
    images = ec2.describe_images(ImageIds=[AMI])
    image = images.get("Images", [])
    require(len(image) == 1 and image[0].get("State") == "available"
            and image[0].get("OwnerId") == "898082745236"
            and image[0].get("Architecture") == "x86_64", "AMI_MISMATCH")
    description = ec2.describe_instance_types(InstanceTypes=[INSTANCE])
    types = description.get("InstanceTypes", [])
    require(len(types) == 1 and types[0].get("InstanceType") == INSTANCE, "TYPE_MISMATCH")
    gpus = types[0].get("GpuInfo", {}).get("Gpus", [])
    require(len(gpus) == 1 and gpus[0].get("Name") == "RTX PRO 4500"
            and gpus[0].get("Count") == 1, "GPU_MISMATCH_NO_T4")
    require(types[0].get("VCpuInfo", {}).get("DefaultVCpus") == 8, "VCPU_MISMATCH")
    quota = clients["service-quotas"].get_service_quota(ServiceCode="ec2", QuotaCode="L-DB2E81BA")
    require(quota.get("Quota", {}).get("Value", 0) >= 8, "VCPU_QUOTA_TOO_LOW")
    active = ec2.describe_instances(Filters=[{"Name": "instance-state-name",
        "Values": ["pending", "running", "stopping", "shutting-down"]}])
    require(not active.get("NextToken"), "ACTIVE_PAGINATION_REJECTED")
    conflicts = []
    for reservation in active.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            tags = {v["Key"]: v["Value"] for v in instance.get("Tags", [])}
            if "cas_meta_job" in tags or instance.get("InstanceType", "").startswith(("g", "vt")):
                conflicts.append({"instance_id": instance["InstanceId"], "type": instance["InstanceType"],
                                  "state": instance["State"]["Name"]})
    require(not conflicts, "ACTIVE_CAS_OR_G_QUOTA_CONFLICT")
    offerings = ec2.describe_instance_type_offerings(LocationType="region", Filters=[
        {"Name": "instance-type", "Values": [INSTANCE]}])
    require(not offerings.get("NextToken") and offerings.get("InstanceTypeOfferings"), "NO_OFFERING")
    prices = {}
    for name, (service, fields, _) in PRICE_QUERIES.items():
        prices[name] = clients["pricing"].get_products(ServiceCode=service, MaxResults=20,
            Filters=[{"Type": "TERM_MATCH", "Field": k, "Value": v} for k, v in fields.items()])
    return {"schema": "cas-teaching-live-preflight/1", "observed_utc": datetime.now(timezone.utc).isoformat(),
        "account_id": ACCOUNT, "region": REGION, "instance_type": INSTANCE, "ami": AMI,
        "gpu_name": "RTX PRO 4500", "visible_gpu_count": 1, "conflicting_resources": conflicts,
        "cost_worksheet": worksheet(prices), "raw_prices": prices,
        "observations": {"image": images, "instance_type": description, "quota": quota,
            "offerings": offerings, "active_observation_request_id": active.get("ResponseMetadata", {}).get("RequestId"),
            "identity_request_id": identity.get("ResponseMetadata", {}).get("RequestId")},
        "read_only": True, "reservation_created": False, "capacity_guaranteed": False,
        "iam_propagation_proved": False, "shutdown_schedule_proved": False,
        "runtime_cuda_proved": False}


def build_clients(profile="default"):
    import boto3
    from botocore.config import Config
    config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=profile, region_name=REGION)
    clients = {name: session.client(name, config=config) for name in ("sts", "ec2", "service-quotas")}
    clients["pricing"] = session.client("pricing", config=config, region_name="us-east-1")
    return clients


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    output = Path(args.output).absolute()
    records = Path(__file__).resolve().parents[1] / "records/teaching_cycle_001"
    require(output.is_relative_to(records) and not output.exists(), "FRESH_RECORD_REQUIRED")
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (output, *output.parents)), "LINK_REJECTED")
    output.mkdir(parents=True)
    try:
        result = observe(build_clients(args.profile))
        code = 0
    except Exception as error:
        result = {"schema": "cas-teaching-live-preflight/1", "status": "PREFLIGHT_FAILED",
            "observed_utc": datetime.now(timezone.utc).isoformat(),
            "error": type(error).__name__ + ":" + str(error)[:1500], "read_only": True,
            "reservation_created": False}
        code = 1
    result["source_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    result["command"] = [sys.executable, *sys.argv]
    raw = encoded(result)
    with (output / "receipt.json").open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"exit_code": code, "receipt": str(output / "receipt.json"), "sha256": sha256(raw).hexdigest()}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
