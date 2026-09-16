"""Independent, bounded, read-only AWS closure and retained-archive observations."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
JOB = "cas-meta2-ingestionsmoke-20260916183635-6ef614bf"
INSTANCE = "i-0df9728e05ae06711"
ACCOUNT, REGION = "807562639912", "us-west-2"
BUCKET = JOB + "-" + ACCOUNT
RESULT = BASE / ("receipt_" + JOB) / "result.json"
EXPECTED_RESULT = "a99859a9bd93af0e502798399737e15a35bb8b2c9de17fad039b8fb860eb92cb"
ALLOWED = {"GetCallerIdentity", "DescribeInstances", "DescribeSecurityGroups", "DescribeVolumes",
    "DescribeNetworkInterfaces", "GetRole", "GetInstanceProfile", "ListRoles", "ListInstanceProfiles",
    "GetSchedule", "ListSchedules", "HeadBucket", "GetBucketLocation", "GetPublicAccessBlock",
    "GetBucketEncryption", "GetBucketVersioning", "GetBucketOwnershipControls", "GetBucketPolicyStatus",
    "GetBucketLifecycleConfiguration", "GetObjectLockConfiguration", "ListObjectsV2", "HeadObject"}


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"torch", "numpy", "casformer", "cas_cjt", "transformers", "safetensors"}:
            raise RuntimeError("MODEL_IMPORT_FORBIDDEN:" + fullname)


sys.meta_path.insert(0, Deny())
import boto3
from botocore.config import Config


def now():
    return datetime.now(timezone.utc).isoformat()


def pin(path):
    raw = Path(path).read_bytes()
    return {"path": str(Path(path).resolve()), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def write(name, value):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, default=str) + "\n")
    return pin(OUT / name)


def readonly(model, **kwargs):
    if model.name not in ALLOWED:
        raise RuntimeError("PROVIDER_MUTATION_OR_UNLISTED_CALL_FORBIDDEN:" + model.name)


def instances(data):
    return {"instances": [{"id": i["InstanceId"], "state": i["State"]["Name"],
              "type": i["InstanceType"], "transition": i.get("StateTransitionReason"),
              "job": [t["Value"] for t in i.get("Tags", []) if t["Key"] == "cas_meta_job"]}
             for reservation in data.get("Reservations", []) for i in reservation.get("Instances", [])],
            "next_token": data.get("NextToken")}


def plain(data):
    return {k: v for k, v in data.items() if k != "ResponseMetadata"}


result_pin = pin(RESULT)
if result_pin["sha256"] != EXPECTED_RESULT:
    raise RuntimeError("LIFECYCLE_CALLER_PIN_MISMATCH")
result = json.loads(RESULT.read_bytes())
if result["job"] != JOB or result["launch"]["instance_id"] != INSTANCE or result["launch"]["bucket"] != BUCKET:
    raise RuntimeError("LIFECYCLE_RESOURCE_BINDING_MISMATCH")
session = boto3.Session(profile_name="default", region_name=REGION)
config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
clients = {name: session.client(name, region_name=REGION, config=config) for name in ("sts", "ec2", "iam", "scheduler", "s3")}
for client in clients.values():
    client.meta.events.register("before-call", readonly)
identity = clients["sts"].get_caller_identity()
if identity["Account"] != ACCOUNT:
    raise RuntimeError("AWS_ACCOUNT_MISMATCH")
observations = {"schema": "cncm-ingestion-provider-closure/1", "observed_start_utc": now(),
    "account": ACCOUNT, "region": REGION, "profile": "default", "job": JOB, "instance_id": INSTANCE,
    "retained_bucket": BUCKET, "lifecycle_result": result_pin, "script": pin(__file__),
    "caller_identity": {"account": identity["Account"], "http_status": identity["ResponseMetadata"]["HTTPStatusCode"],
                        "request_id": identity["ResponseMetadata"]["RequestId"]}, "calls": {},
    "provider_mutations": 0, "model_loads": 0, "object_body_downloads": 0}
ec2, iam, s3, scheduler = (clients[k] for k in ("ec2", "iam", "s3", "scheduler"))
tagged = [{"Name": "tag-key", "Values": ["cas_meta_job"]}]
active = [{"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped", "shutting-down"]}]
calls = {
    "exact_instance": ("ec2.describe_instances", lambda: ec2.describe_instances(InstanceIds=[INSTANCE]), instances),
    "all_active_cas_instances": ("ec2.describe_instances", lambda: ec2.describe_instances(Filters=tagged + active), instances),
    "all_active_account_instances": ("ec2.describe_instances", lambda: ec2.describe_instances(Filters=active), instances),
    "job_security_group": ("ec2.describe_security_groups", lambda: ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [JOB]}]),
        lambda d: {"groups": [{"id": r["GroupId"], "name": r["GroupName"]} for r in d["SecurityGroups"]], "next_token": d.get("NextToken")}),
    "all_tagged_cas_security_groups": ("ec2.describe_security_groups", lambda: ec2.describe_security_groups(Filters=tagged),
        lambda d: {"groups": [{"id": r["GroupId"], "name": r["GroupName"]} for r in d["SecurityGroups"]], "next_token": d.get("NextToken")}),
    "all_tagged_cas_volumes": ("ec2.describe_volumes", lambda: ec2.describe_volumes(Filters=tagged),
        lambda d: {"volumes": [{"id": r["VolumeId"], "state": r["State"], "size_gib": r["Size"],
             "attachments": [{"instance_id": a.get("InstanceId"), "state": a.get("State")} for a in r["Attachments"]]} for r in d["Volumes"]], "next_token": d.get("NextToken")}),
    "all_tagged_cas_interfaces": ("ec2.describe_network_interfaces", lambda: ec2.describe_network_interfaces(Filters=tagged),
        lambda d: {"interfaces": [{"id": r["NetworkInterfaceId"], "state": r["Status"]} for r in d["NetworkInterfaces"]], "next_token": d.get("NextToken")}),
    "exact_instance_interfaces": ("ec2.describe_network_interfaces", lambda: ec2.describe_network_interfaces(Filters=[{"Name": "attachment.instance-id", "Values": [INSTANCE]}]),
        lambda d: {"interfaces": [{"id": r["NetworkInterfaceId"], "state": r["Status"]} for r in d["NetworkInterfaces"]], "next_token": d.get("NextToken")}),
    "worker_role": ("iam.get_role", lambda: iam.get_role(RoleName=JOB + "-worker"), lambda d: {"role": d["Role"]["RoleName"]}),
    "worker_profile": ("iam.get_instance_profile", lambda: iam.get_instance_profile(InstanceProfileName=JOB + "-worker"), lambda d: {"profile": d["InstanceProfile"]["InstanceProfileName"]}),
    "timer_role": ("iam.get_role", lambda: iam.get_role(RoleName=JOB + "-timer"), lambda d: {"role": d["Role"]["RoleName"]}),
    "job_schedule": ("scheduler.get_schedule", lambda: scheduler.get_schedule(Name=JOB, GroupName="default"), lambda d: {"name": d["Name"], "state": d["State"]}),
    "retained_bucket": ("s3.head_bucket", lambda: s3.head_bucket(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
    "bucket_region": ("s3.get_bucket_location", lambda: s3.get_bucket_location(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
    "public_access_block": ("s3.get_public_access_block", lambda: s3.get_public_access_block(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
    "encryption": ("s3.get_bucket_encryption", lambda: s3.get_bucket_encryption(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
    "versioning": ("s3.get_bucket_versioning", lambda: s3.get_bucket_versioning(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
    "ownership": ("s3.get_bucket_ownership_controls", lambda: s3.get_bucket_ownership_controls(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
    "policy_public_status": ("s3.get_bucket_policy_status", lambda: s3.get_bucket_policy_status(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
    "lifecycle_configuration": ("s3.get_bucket_lifecycle_configuration", lambda: s3.get_bucket_lifecycle_configuration(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
    "object_lock_configuration": ("s3.get_object_lock_configuration", lambda: s3.get_object_lock_configuration(Bucket=BUCKET, ExpectedBucketOwner=ACCOUNT), plain),
}


def run_call(name, api, call, project):
    record = {"api": api, "queried_utc": now()}
    try:
        response = call(); meta = response.get("ResponseMetadata", {})
        record.update(http_status=meta.get("HTTPStatusCode"), request_id=meta.get("RequestId"), observed=project(response))
    except Exception as error:
        response = getattr(error, "response", {}); meta = response.get("ResponseMetadata", {})
        record.update(http_status=meta.get("HTTPStatusCode"), request_id=meta.get("RequestId"),
                      error_type=type(error).__name__, error_code=response.get("Error", {}).get("Code"))
    return name, record


with ThreadPoolExecutor(max_workers=6) as pool:
    futures = [pool.submit(run_call, name, *arguments) for name, arguments in calls.items()]
    for future in as_completed(futures):
        name, record = future.result(); observations["calls"][name] = record
        print(name, record.get("http_status"), record.get("error_code"), flush=True)


def pages(method, row_key, name_key, *, prefix=None, **kwargs):
    records, page_meta = [], []
    paginator = method[0].get_paginator(method[1])
    for count, page in enumerate(paginator.paginate(**kwargs), 1):
        if count > 100:
            raise RuntimeError("READONLY_PAGINATION_BOUND")
        page_meta.append({k: page["ResponseMetadata"].get(k) for k in ("RequestId", "HTTPStatusCode")})
        records.extend(row for row in page.get(row_key, []) if prefix is None or row[name_key].startswith(prefix))
    return {"pages": page_meta, "matches": [{"name": row[name_key], "state": row.get("State")} for row in records]}


for name, call in {
    "cas_roles": lambda: pages((iam, "list_roles"), "Roles", "RoleName", prefix="cas-meta2-"),
    "cas_instance_profiles": lambda: pages((iam, "list_instance_profiles"), "InstanceProfiles", "InstanceProfileName", prefix="cas-meta2-"),
    "cas_schedules": lambda: pages((scheduler, "list_schedules"), "Schedules", "Name", NamePrefix="cas-meta2-"),
}.items():
    try:
        observations["calls"][name] = {"queried_utc": now(), "observed": call()}
    except Exception as error:
        observations["calls"][name] = {"queried_utc": now(), "error_type": type(error).__name__,
            "error_code": getattr(error, "response", {}).get("Error", {}).get("Code")}

objects, object_pages = [], []
try:
    for count, page in enumerate(s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix="results/", ExpectedBucketOwner=ACCOUNT), 1):
        if count > 10:
            raise RuntimeError("ARCHIVE_LISTING_BOUND")
        object_pages.append({k: page["ResponseMetadata"].get(k) for k in ("RequestId", "HTTPStatusCode")})
        objects.extend({"key": row["Key"], "bytes": row["Size"], "last_modified": row["LastModified"],
                        "etag": row.get("ETag"), "storage_class": row.get("StorageClass")} for row in page.get("Contents", []))
    observations["retained_results_inventory"] = {"pages": object_pages, "objects": objects,
        "count": len(objects), "bytes": sum(row["bytes"] for row in objects), "body_hashes_rechecked": False}
except Exception as error:
    observations["retained_results_inventory"] = {"pages": object_pages, "error_type": type(error).__name__,
        "error_code": getattr(error, "response", {}).get("Error", {}).get("Code")}

for name in ("result.json", "artifacts/manifest.json", "artifacts/origin.pt", "artifacts/initial.pt", "artifacts/final.pt"):
    key = "results/" + name
    _, record = run_call(key, "s3.head_object", lambda k=key: s3.head_object(Bucket=BUCKET, Key=k, ExpectedBucketOwner=ACCOUNT),
        lambda d: {k: d.get(k) for k in ("ContentLength", "LastModified", "ETag", "VersionId", "ServerSideEncryption", "ObjectLockMode", "ObjectLockRetainUntilDate")})
    local_path = RESULT.parent / "collected" / key
    if local_path.is_file():
        record["local_verified_file"] = pin(local_path)
        record["remote_size_matches_local"] = record.get("observed", {}).get("ContentLength") == local_path.stat().st_size
    observations["calls"]["head:" + key] = record

observations["observed_end_utc"] = now()
observations["lifecycle_result_unchanged"] = pin(RESULT) == result_pin
provider_pin = write("provider.json", observations)
calls = observations["calls"]


def empty(name, field):
    value = calls[name]
    return value.get("http_status") == 200 and value.get("observed", {}).get(field) == [] and not value.get("observed", {}).get("next_token")


requirements = {
    "exact_instance_terminated": calls["exact_instance"].get("observed", {}).get("instances") == [{
        "id": INSTANCE, "state": "terminated", "type": "g7.2xlarge", "transition": calls["exact_instance"].get("observed", {}).get("instances", [{}])[0].get("transition"), "job": [JOB]}],
    "job_security_group_absent": empty("job_security_group", "groups"),
    "worker_role_absent": calls["worker_role"].get("error_code") == "NoSuchEntity",
    "worker_profile_absent": calls["worker_profile"].get("error_code") == "NoSuchEntity",
    "timer_role_absent": calls["timer_role"].get("error_code") == "NoSuchEntity",
    "job_schedule_absent": calls["job_schedule"].get("error_code") == "ResourceNotFoundException",
    "no_active_tagged_cas_instances": empty("all_active_cas_instances", "instances"),
    "no_tagged_cas_security_groups": empty("all_tagged_cas_security_groups", "groups"),
    "no_tagged_cas_volumes": empty("all_tagged_cas_volumes", "volumes"),
    "no_tagged_cas_interfaces": empty("all_tagged_cas_interfaces", "interfaces"),
    "no_instance_interfaces": empty("exact_instance_interfaces", "interfaces"),
    "retained_bucket_present": calls["retained_bucket"].get("http_status") == 200,
    "retained_bucket_region": calls["bucket_region"].get("observed", {}).get("LocationConstraint") == REGION,
    "public_access_block_all_enabled": calls["public_access_block"].get("observed", {}).get("PublicAccessBlockConfiguration") == {
        "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True},
    "retained_checkpoint_and_marker_sizes": all(calls["head:results/" + name].get("remote_size_matches_local") is True
        for name in ("result.json", "artifacts/manifest.json", "artifacts/origin.pt", "artifacts/initial.pt", "artifacts/final.pt")),
    "lifecycle_result_unchanged": observations["lifecycle_result_unchanged"],
}
for name in ("cas_roles", "cas_instance_profiles", "cas_schedules"):
    requirements["no_" + name] = calls[name].get("observed", {}).get("matches") == []
receipt = {"schema": "cncm-ingestion-provider-closure-receipt/1", "status": "PASSED" if all(requirements.values()) else "PARTIAL_OR_OPEN",
    "checks": requirements, "provider_evidence": provider_pin, "source": pin(__file__), "lifecycle_result": result_pin,
    "observed_start_utc": observations["observed_start_utc"], "observed_end_utc": observations["observed_end_utc"],
    "provider_mutations": 0, "object_body_downloads": 0, "model_loads": 0,
    "boundary": "Account/region/time-scoped provider readback. S3 listing and HEAD sizes are presence/configuration evidence, not a second content-hash verification, independent backup, WORM claim or final bill. Untagged resources without CAS names are outside CAS resource attribution."}
print(json.dumps(write("receipt.json", receipt)), flush=True)
print(json.dumps({"status": receipt["status"], "open_checks": [k for k, v in requirements.items() if not v]}), flush=True)
