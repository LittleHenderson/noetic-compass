"""Read-only current AWS gates and independent cleanup; no resource mutation."""
import datetime
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

CONFIG = Config(retries={"total_max_attempts": 1}, connect_timeout=5, read_timeout=30)
def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
def session():
    return boto3.Session(profile_name="default", region_name="us-west-2")
def rate(s, instance):
    filters = {"instanceType": instance, "regionCode": "us-west-2", "operatingSystem": "Linux",
               "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used"}
    reply = s.client("pricing", region_name="us-east-1", config=CONFIG).get_products(
        ServiceCode="AmazonEC2", Filters=[{"Type":"TERM_MATCH","Field":k,"Value":v} for k,v in filters.items()], MaxResults=100)
    prices = []
    for raw in reply["PriceList"]:
        product = json.loads(raw)
        for term in product["terms"].get("OnDemand", {}).values():
            for dimension in term["priceDimensions"].values():
                if dimension["unit"] == "Hrs":
                    prices.append(dimension["pricePerUnit"]["USD"])
    if len(set(prices)) != 1 or reply.get("NextToken"):
        raise ValueError("UNAMBIGUOUS_CURRENT_HOURLY_RATE_REQUIRED")
    return {"usd_per_hour": prices[0], "query": filters, "request_id": reply["ResponseMetadata"]["RequestId"]}

def before_launch(plan, instance="g7.2xlarge"):
    s = session()
    identity = s.client("sts", config=CONFIG).get_caller_identity()
    if identity["Account"] != "807562639912":
        raise ValueError("WRONG_AWS_ACCOUNT")
    ec2 = s.client("ec2", config=CONFIG)
    quoted = rate(s, instance)
    ceiling = "2.52" if instance == "g7.2xlarge" else "0.085"
    if Decimal(quoted["usd_per_hour"]) > Decimal(ceiling):
        raise ValueError("CURRENT_PRICE_EXCEEDS_FROZEN_BOUND")
    expected_image = plan["environment"]["ami"] if instance == "g7.2xlarge" else "ami-07a134137a631b892"
    image = ec2.describe_images(ImageIds=[expected_image])["Images"]
    if len(image) != 1 or image[0]["State"] != "available":
        raise ValueError("PINNED_IMAGE_UNAVAILABLE")
    regions = [x["RegionName"] for x in ec2.describe_regions(AllRegions=False)["Regions"]]
    exemptions = {x["instance_id"]: x for x in plan["concurrency"]["reviewed_production_allowlist"]}
    def regional(region):
        client = s.client("ec2", region_name=region, config=CONFIG)
        rows = []
        for page in client.get_paginator("describe_instances").paginate(
                Filters=[{"Name":"instance-state-name","Values":["pending","running","stopping","shutting-down"]}]):
            for reservation in page["Reservations"]:
                for obj in reservation["Instances"]:
                    tags = {x["Key"]:x["Value"] for x in obj.get("Tags", [])}
                    known = exemptions.get(obj["InstanceId"])
                    permitted = bool(known and known["region"] == region and known["instance_type"] == obj["InstanceType"]
                        and all(tags.get(k) == v for k,v in known["tags"].items())
                        and not any(k in tags for k in ("CASJob", "cas_meta_job")))
                    rows.append({"region":region,"instance_id":obj["InstanceId"],"instance_type":obj["InstanceType"],
                                 "state":obj["State"]["Name"],"production_allowlist_match":permitted,"tags":tags})
        return rows
    with ThreadPoolExecutor(max_workers=4) as pool:
        active = [row for result in pool.map(regional, regions) for row in result]
    conflicts = [row for row in active if not row["production_allowlist_match"]]
    record = {"utc":utc(),"instance_type":instance,"region":"us-west-2","actual_current_price":quoted,
              "image":{k:image[0].get(k) for k in ("ImageId","Name","State","CreationDate","Architecture")},
              "regions_checked":regions,"active_instances":active,"conflicts":conflicts,"provider_mutations":False}
    if conflicts:
        error = ValueError("CONFLICTING_ACTIVE_EXPERIMENT_OR_UNALLOWLISTED_INSTANCE")
        error.public_record = record
        raise error
    return record

def cleanup(job, instance_id):
    s = session(); ec2 = s.client("ec2", config=CONFIG); iam = s.client("iam", config=CONFIG)
    states = [x["State"]["Name"] for rr in ec2.describe_instances(InstanceIds=[instance_id])["Reservations"] for x in rr["Instances"]]
    checks = [{"check":"instance_terminated_or_absent","pass":not states or all(x=="terminated" for x in states),"observed":states}]
    groups = ec2.describe_security_groups(Filters=[{"Name":"group-name","Values":[job]}])["SecurityGroups"]
    checks.append({"check":"job_security_group_absent","pass":not groups,"count":len(groups)})
    live = ec2.describe_instances(Filters=[{"Name":"tag:cas_meta_job","Values":[job]},
        {"Name":"instance-state-name","Values":["pending","running","stopping","stopped","shutting-down"]}])["Reservations"]
    checks.append({"check":"no_nonterminated_job_instance","pass":not any(x.get("Instances") for x in live)})
    calls = [("worker_role",lambda:iam.get_role(RoleName=job+"-worker")),
             ("timer_role",lambda:iam.get_role(RoleName=job+"-timer")),
             ("worker_profile",lambda:iam.get_instance_profile(InstanceProfileName=job+"-worker")),
             ("worker_policy",lambda:iam.get_role_policy(RoleName=job+"-worker",PolicyName="job-only"))]
    for name, fn in calls:
        try:
            fn(); checks.append({"check":name+"_absent","pass":False})
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "NoSuchEntity":
                raise
            checks.append({"check":name+"_absent","pass":True,"observed":"NoSuchEntity",
                           "request_id":exc.response["ResponseMetadata"]["RequestId"]})
    s3 = s.client("s3", config=CONFIG)
    bucket = job + "-807562639912"
    archive_head = s3.head_bucket(Bucket=bucket)
    block = s3.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
    checks.append({"check":"archive_retained_private","pass":all(block.values()),"public_access_block":block,
                   "request_id":archive_head["ResponseMetadata"]["RequestId"]})
    return {"utc":utc(),"job":job,"instance_id":instance_id,"checks":checks,
            "all_passed":all(x["pass"] for x in checks),"scheduler":"NOT_APPLICABLE_FOR_FROZEN_GPU_LAUNCHER",
            "archive_retained":True,"storage_active":True,"deletion_authorized":False,"provider_mutations":False}
