"""Read-only AWS GPU, quota and current-price evidence; never launches resources."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "807562639912"
REGION = "us-west-2"
TYPES = ("g7.2xlarge", "p5.4xlarge", "g6e.2xlarge", "g7e.2xlarge")


def collect(output, profile="default"):
    import boto3
    from botocore.config import Config

    output = Path(output).resolve()
    if not output.is_relative_to((ROOT / "records" / "provider").resolve()) or output.exists():
        raise ValueError("NEW_OWNED_PROVIDER_RECEIPT_DIRECTORY_REQUIRED")
    output.mkdir(parents=True)
    config = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=profile, region_name=REGION)
    calls = []
    errors = []

    def call(service, operation, **args):
        client = session.client(service, region_name="us-east-1" if service == "pricing" else REGION, config=config)
        record = {"utc": datetime.now(timezone.utc).isoformat(), "service": service, "operation": operation, "arguments": args}
        try:
            response = getattr(client, operation)(**args)
            record["response"] = response
        except Exception as exc:
            response = None
            # API error codes are useful; credentials and full signed requests are never logged.
            code = getattr(exc, "response", {}).get("Error", {}).get("Code", type(exc).__name__)
            record["error_code"] = code
            errors.append({"service": service, "operation": operation, "code": code})
        calls.append(record)
        return response

    def pages(service, operation, field, **args):
        items = []
        token = None
        while True:
            response = call(service, operation, **args, **({"NextToken": token} if token else {}))
            if response is None:
                break
            items.extend(response[field])
            token = response.get("NextToken")
            if not token:
                break
        return items

    identity = call("sts", "get_caller_identity")
    if not identity or identity.get("Account") != ACCOUNT:
        errors.append({"code": "AWS_ACCOUNT_MISMATCH_OR_UNAVAILABLE"})
        instances, quota, prices, types, offerings = [], [], {}, [], []
    else:
        owned = pages("ec2", "describe_instances", "Reservations", Filters=[{"Name": "tag-key", "Values": ["cas_meta_job"]}])
        gpu = pages("ec2", "describe_instances", "Reservations", Filters=[{"Name": "instance-type", "Values": ["g*", "p*"]}, {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped", "shutting-down"]}])
        # Minimize unrelated-account information in the derived receipt. Raw responses
        # retain request IDs and exact provider evidence but never read user data.
        unique = {instance["InstanceId"]: instance for group in owned + gpu for instance in group["Instances"]}
        instances = [{"instance_id": item["InstanceId"], "instance_type": item["InstanceType"], "state": item["State"]["Name"], "cas_meta_job": {tag["Key"]: tag["Value"] for tag in item.get("Tags", [])}.get("cas_meta_job"), "launch_time": item.get("LaunchTime")} for item in unique.values()]
        all_quota = pages("service-quotas", "list_service_quotas", "Quotas", ServiceCode="ec2")
        quota = [item for item in all_quota if any(term in item.get("QuotaName", "") for term in ("G and VT", "P instances", "All P Spot", "P5"))]
        type_response = call("ec2", "describe_instance_types", InstanceTypes=list(TYPES))
        types = [] if type_response is None else [{"instance_type": item["InstanceType"], "vcpus": item["VCpuInfo"]["DefaultVCpus"], "gpus": item.get("GpuInfo", {})} for item in type_response["InstanceTypes"]]
        offerings = pages("ec2", "describe_instance_type_offerings", "InstanceTypeOfferings", LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": list(TYPES)}, {"Name": "location", "Values": ["us-west-2b"]}])
        prices = {}
        for instance_type in TYPES:
            fields = {"instanceType": instance_type, "location": "US West (Oregon)", "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used", "marketoption": "OnDemand", "operation": "RunInstances"}
            products = pages("pricing", "get_products", "PriceList", ServiceCode="AmazonEC2", Filters=[{"Type": "TERM_MATCH", "Field": key, "Value": value} for key, value in fields.items()])
            rates = [Decimal(dimension["pricePerUnit"]["USD"]) for raw in products for term in json.loads(raw).get("terms", {}).get("OnDemand", {}).values() for dimension in term["priceDimensions"].values() if dimension["unit"] == "Hrs"]
            prices[instance_type] = {"linux_shared_on_demand_hourly_usd": str(rates[0]) if len(rates) == 1 else None, "all_hourly_rates_usd": [str(rate) for rate in rates], "product_count": len(products)}
            if len(rates) != 1:
                errors.append({"code": "PRICE_MISSING_OR_AMBIGUOUS", "instance_type": instance_type})

    raw_path = output / "provider_calls.json"
    raw_path.write_text(json.dumps(calls, indent=2, default=str) + "\n", encoding="utf-8")
    active = [item for item in instances if item["state"] in ("pending", "running", "stopping", "shutting-down")]
    result = {"schema": "cas-meta2-readonly-provider-snapshot/1", "status": "READ_ONLY_SNAPSHOT_COMPLETE" if not errors else "READ_ONLY_SNAPSHOT_PARTIAL", "captured_utc": datetime.now(timezone.utc).isoformat(), "account": identity.get("Account") if identity else None, "region": REGION, "provider_mutations": 0, "gpu_instances_and_tagged_cas_jobs": instances, "active_cas_jobs": [item for item in active if item["cas_meta_job"]], "other_active_gpu_count": len([item for item in active if not item["cas_meta_job"]]), "quotas": [{"name": item["QuotaName"], "code": item["QuotaCode"], "value": item["Value"], "unit": item["Unit"]} for item in quota], "instance_specs": types, "offerings": offerings, "prices": prices, "errors": errors, "provider_calls_file": str(raw_path), "provider_calls_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(), "limits": ["A listed offering does not prove available capacity.", "Quota and prices are a point-in-time snapshot, not a successful capability test.", "Prices exclude storage, IPv4, requests, transfer and taxes; campaign reservations must include a conservative ancillary allowance.", "Stopped and unrelated instances were not changed."]}
    receipt = output / "provider_snapshot.json"
    receipt.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args()
    print(json.dumps(collect(args.output, args.profile), indent=2, default=str))
