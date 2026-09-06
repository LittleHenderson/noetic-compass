"""Summarize saved read-only responses and declared parent resource ceilings."""
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = Decimal


def load(name):
    return json.loads((HERE/name).read_bytes())


def response(name):
    data = load(name)
    assert data["status"] == "OK" and not data["response"].get("NextToken")
    return data["response"]


def rate(name, unit, attribute=None):
    raw = response(name)
    products = [json.loads(item) for item in raw["PriceList"]]
    if attribute:
        products = [p for p in products if all(p["product"]["attributes"].get(k) == v for k,v in attribute.items())]
    assert len(products) == 1
    product = products[0]
    dims = [dim for term in product["terms"]["OnDemand"].values() for dim in term["priceDimensions"].values()]
    assert dims and all(dim["unit"] == unit for dim in dims)
    highest = max(D(dim["pricePerUnit"]["USD"]) for dim in dims)
    return {"usd": str(highest), "unit": unit, "source_file": name, "sku": product["product"]["sku"],
            "publication_date": product["publicationDate"], "tier_policy": "Highest published tier; no free-tier credit used."}


prices = {
    "compute": rate("21_compute_price.json", "Hrs"),
    "ebs_gp3": rate("22_ebs_price.json", "GB-Mo"),
    "ipv4": rate("23_ipv4_price.json", "Hrs"),
    "s3_standard": rate("24_s3_storage.json", "GB-Mo", {"usagetype": "USW2-TimedStorage-ByteHrs", "volumeType": "Standard"}),
    "s3_tier1": rate("25_s3_requests_tier1.json", "Requests"),
    "s3_tier2": rate("26_s3_requests_tier2.json", "Requests"),
    "internet_out": rate("29_internet_transfer.json", "GB"),
    "scheduler": {"usd": "0.000001", "unit": "invocation",
        "url": "https://aws.amazon.com/eventbridge/pricing/", "section": "Scheduler pricing example, US West",
        "basis": "Published one USD per million invocations; no free-tier credit used.",
        "verification": "Official AWS page read through browser tool on 2026-09-06; query31 returned no product and is retained."},
}
assert D(prices["compute"]["usd"]) == D("2.52")
assert D(prices["ebs_gp3"]["usd"]) == D("0.08")
assert D(prices["ipv4"]["usd"]) == D("0.005")
assert D(prices["s3_standard"]["usd"]) == D("0.023")
assert D(prices["internet_out"]["usd"]) == D("0.09")

limits = {"instance_count": 1, "instance_type": "g7.2xlarge", "instance_lifetime_seconds": 3600,
    "lifetime_includes": ["boot", "installation", "CUDA check", "worker", "output collection", "shutdown"],
    "worker_seconds": 1800, "automatic_retries": 0, "ebs_provisioned_gb": 75,
    "ebs_iops": 3000, "ebs_throughput_mib_per_second": 125, "public_ipv4_count": 1,
    "input_bytes_max": 16*1024**2, "total_result_bytes_max": 256*1024**2,
    "result_keys": 3, "result_archive_bytes_max": 254*1024**2,
    "bootstrap_and_complete_bytes_max_each": 1024**2, "download_bytes_max": 256*1024**2,
    "s3_lifecycle_days": 7, "storage_days_costed": 8,
    "get_head_list_requests_max": 1000, "put_delete_config_requests_max": 1000,
    "scheduler_invocations_max": 1, "s3_same_region": "us-west-2",
    "no_nat_gateway": True, "no_transfer_acceleration": True, "no_new_customer_managed_kms_key": True,
    "resource_limits_are_parent_contract_not_executed_here": True}
storage_gb = D(limits["input_bytes_max"] + limits["total_result_bytes_max"]) / D(10**9)
out_gb = D(limits["download_bytes_max"]) / D(10**9)
parts = {
    "compute": D(prices["compute"]["usd"]),
    "ebs_gp3_one_hour": D(75)*D(prices["ebs_gp3"]["usd"])/D(30*24),
    "ipv4_one_hour": D(prices["ipv4"]["usd"]),
    "s3_standard_all_inputs_results_eight_days": storage_gb*D(prices["s3_standard"]["usd"])*D(8)/D(30),
    "all_2000_s3_requests_at_higher_tier1_rate": D(2000)*D(prices["s3_tier1"]["usd"]),
    "all_downloads_at_paid_internet_rate": out_gb*D(prices["internet_out"]["usd"]),
    "one_scheduler_invocation": D(prices["scheduler"]["usd"]),
}
known = sum(parts.values())
ancillary = known-parts["compute"]
assert ancillary < D("1.00") and known < D("3.52") < D("4.00")
old_path = ROOT / "records/aws_prototype_v7_001/cleanup_cost_check_001.json"
old_raw = old_path.read_bytes()
old = json.loads(old_raw)
old_check = next(check for check in old["checks"] if check["check"] == "instance_terminated")
assert old_check["state"] == "terminated" and old_check["passed"] is True
inst = response("02_instance_type.json")["InstanceTypes"][0]
ami = response("03_ami.json")["Images"][0]
subnet = response("04_subnet.json")["Subnets"][0]
quota = response("12_gpu_quota.json")["Quota"]
assert response("01_identity.json")["Account"] == "807562639912"
assert inst["GpuInfo"]["Gpus"][0]["Name"] == "RTX PRO 4500" and inst["GpuInfo"]["Gpus"][0]["Count"] == 1
assert inst["VCpuInfo"]["DefaultVCpus"] == 8 and quota["Value"] == 8
assert ami["State"] == "available" and ami["OwnerId"] == "898082745236" and ami["RootDeviceName"] == "/dev/sda1"
assert subnet["State"] == "available" and subnet["AvailabilityZone"] == "us-west-2c"
assert not response("13_tagged_jobs.json")["Instances"] and not response("14_running_gpu_usage.json")["Instances"]
report = {"schema": "cas-meta2-prefix-provider-readiness-summary/8",
    "status": "CURRENT_READ_ACCESS_AND_PRICE_FIT_OBSERVED_NO_LAUNCH",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "source_probe_interval": {"start": load("execution_receipt.json")["started_utc"],
                              "end": load("supplement_receipt.json")["finished_utc"]},
    "account": "807562639912", "region": "us-west-2", "profile": "default",
    "instance": {"type": "g7.2xlarge", "gpu_count": 1, "gpu_name": "RTX PRO 4500", "gpu_memory_mib": 32768,
                 "vcpus": 8, "on_demand_g_vt_quota_vcpus": 8, "observed_pending_running_g_vt_instances": 0},
    "image": {"id": ami["ImageId"], "state": ami["State"], "owner": ami["OwnerId"], "name": ami["Name"]},
    "network": {"subnet": subnet["SubnetId"], "vpc": subnet["VpcId"], "zone": subnet["AvailabilityZone"],
        "available_ip_addresses": subnet["AvailableIpAddressCount"], "public_ip_on_launch": subnet["MapPublicIpOnLaunch"],
        "evidence": ["06_routes.json", "07_network_acl.json", "08_internet_gateway.json", "09_dns_support.json", "10_dns_hostnames.json"],
        "assessment": "Existing default main route has active direct IGW; attached IGW and default ACL allow return traffic. Both DNS attributes enabled. A new zero-inbound HTTPS-only group remains a launch-time action."},
    "offering": response("11_offering.json"),
    "previous_job": {"job": old["job"], "instance": old["resources"]["instance"],
        "historical_termination_observation": old_check, "historical_receipt_path": str(old_path),
        "historical_receipt_sha256": sha256(old_raw).hexdigest(),
        "current_instance_response": response("15_previous_instance.json"),
        "current_instance_interpretation": "No instance row returned now; not a fresh provider terminated-state observation.",
        "current_active_tagged_jobs": [], "current_old_job_volumes": response("16_previous_volumes.json")["Volumes"],
        "current_old_schedule_roles_profile": "Absent according to recorded ResourceNotFoundException/NoSuchEntity responses17-20."},
    "prices": prices, "resource_limits": limits, "cost": {
        "currency": "USD", "components": {k: str(v) for k,v in parts.items()},
        "known_resource_bound_before_tax": str(known), "known_ancillary_bound": str(ancillary),
        "fixed_ancillary_allowance": "1.00", "compute_plus_ancillary_allowance": "3.52",
        "proposed_reservation": "4.00", "remaining_inside_ancillary_allowance": str(D("1")-ancillary),
        "remaining_above_compute_plus_allowance": "0.48", "fits_proposed_reservation_under_declared_limits": True,
        "byte_conversion": "Use decimal GB for S3 bytes as a conservative conversion; EBS uses75 provisioned billing units. September30-day month.",
        "not_an_invoice": True, "provider_enforced_account_cap": False,
        "caveats": ["Taxes/support allocation are not known from these pricing reads.",
            "AWS control-plane failure or shutdown delay can exceed intended lifetime; independent cleanup must be enforced and observed.",
            "No free-tier credit, promotional credit or negotiated discount is assumed.",
            "Input/output/request/lifetime bounds still require the parent implementation; no worker has run."]},
    "official_secondary_references": [
        {"url": "https://aws.amazon.com/ec2/instance-types/g7/", "supports": "G7 RTX PRO4500 specification"},
        {"url": "https://aws.amazon.com/ebs/pricing/", "supports": "gp3 baseline3000IOPS/125MBps; per-second GB-month pro-rating"},
        {"url": "https://aws.amazon.com/s3/pricing/", "supports": "Same-region S3 transfer and inbound internet not charged; no free-tier credit assumed for output"},
        {"url": "https://aws.amazon.com/eventbridge/pricing/", "supports": "USWest Scheduler paid price1USD per million invocations"}],
    "provider_blockers_observed": [],
    "remaining_gates": ["OWNER_EXPLICIT_PAID_LAUNCH_APPROVAL", "COMPLETED_AND_TESTED_DEDICATED_PARENT_ADAPTER",
        "LIVE_PRICE_AND_IDENTITY_RECHECK_BEFORE_RESERVATION", "INDEPENDENT_SHUTDOWN_CONFIRMED_BEFORE_WORKER_PERMISSION",
        "REAL_RESERVATION_AND_INSTANCE_PLAN_BINDING", "ON_INSTANCE_PYTHON_CUDA_CHECKPOINT_AND_GENERATION_CHECKS"],
    "limitations": ["Read-access success does not prove resource-creation permissions.",
        "Quota and offered instance type do not guarantee spare GPU capacity in the AZ.",
        "AMI metadata support is not a live CUDA or installation test."],
    "provider_mutations": 0, "reservation_created": False, "worker_launched": False,
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "summarizer_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
    "query_files": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p.read_bytes()).hexdigest()}
                    for p in sorted(HERE.glob("[0-9][0-9]_*.json"))}}
raw = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
with (HERE / "readiness_summary.json").open("xb") as stream:
    stream.write(raw)
print(json.dumps({"status": report["status"], "known_resource_bound": str(known),
                  "compute_plus_allowance": "3.52", "proposed_reservation": "4.00",
                  "receipt": str(HERE/"readiness_summary.json"), "sha256": sha256(raw).hexdigest()}))
