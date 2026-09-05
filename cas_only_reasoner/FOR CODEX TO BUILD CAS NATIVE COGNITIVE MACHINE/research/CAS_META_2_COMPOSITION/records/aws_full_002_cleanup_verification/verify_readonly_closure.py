"""Independent read-only closure check for exactly CAS-META2 full job 002."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
JOB = "cas-meta2-20260905170320-4a4c71e5"
ACCOUNT = "807562639912"
INSTANCE = "i-0366123b8921b3856"
VOLUME = "vol-0e4a1a02a71ec540f"
SG = "sg-044bf591651f497e3"
BUCKET = JOB + "-" + ACCOUNT
WORKER, TIMER = JOB + "-worker", JOB + "-timer"
SOURCE = "b5f1718e63a2b5cf72b4b606d513d0524b9226ac"
ARCHIVE = "d648ab877d958b6729882a870c386f70d0e1c4d9ba24e614d719081d396c19bc"
ARTIFACT = "e22412583114e50cbf9e60d8b22864bfb4ca76e6ccecedee7a0f72976ec37ae0"
ARTIFACT_BYTES = 62269330
READ_ONLY_OPERATIONS = {
    "sts": {"get_caller_identity"},
    "ec2": {"describe_instances", "describe_volumes", "describe_security_groups"},
    "iam": {"get_instance_profile", "get_role"},
    "scheduler": {"get_schedule"},
    "s3": {"get_bucket_tagging", "list_objects_v2", "get_bucket_lifecycle_configuration",
           "get_public_access_block", "get_bucket_encryption", "head_object", "get_object"},
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    result_path=OUT/"closure_verification_receipt.json"
    raw_path=OUT/"provider_calls.jsonl"
    require(not result_path.exists() and not raw_path.exists(),"NEW_READ_ONLY_RECEIPT_REQUIRED")
    original_path=ROOT/"records"/"aws_full_002"/"launch_receipt.json"
    original_bytes=original_path.read_bytes()
    original=json.loads(original_bytes)
    resources=original["resources"]
    require(original["status"]=="AWS_JOB_FINISHED" and original["termination_confirmed"] is True and original["cleanup_errors"]==[],"COMPLETED_LAUNCHER_CLOSURE_REQUIRED")
    require(original["job"]==JOB and original["source_sha"]==SOURCE and original["archive_sha256"]==ARCHIVE,"SOURCE_OR_JOB_MISMATCH")
    require(resources["instance"]==INSTANCE and resources["security_group"]==SG and resources["bucket"]==BUCKET and resources["schedule"]==JOB and resources["instance_profile"]==WORKER,"OWNED_RESOURCES_MISMATCH")
    artifact_path=original_path.with_name("cloud_artifacts.zip")
    require(artifact_path.stat().st_size==ARTIFACT_BYTES and sha(artifact_path)==ARTIFACT,"DOWNLOADED_ARTIFACT_IDENTITY_MISMATCH")
    ledger_path=ROOT/"records"/"budget"/"campaign_ledger.json"
    ledger_bytes=ledger_path.read_bytes()
    ledger=json.loads(ledger_bytes)
    total=sum(Decimal(row["reserved_usd"]) for row in ledger["reservations"])
    matching=[row for row in ledger["reservations"] if row["job"]==JOB]
    require(total==Decimal(ledger["total_reserved_usd"])==Decimal("18.00") and Decimal(ledger["remaining_unreserved_usd"])==Decimal("382.00") and ledger["owner_task_cap_usd"]=="400.00","CAMPAIGN_BUDGET_MISMATCH")
    require(len(matching)==1 and matching[0]["reserved_usd"]=="7.00" and matching[0]["source_sha"]==SOURCE and matching[0]["archive_sha256"]==ARCHIVE,"JOB_RESERVATION_MISMATCH")
    receipt={"schema":"cas-meta2-independent-readonly-closure/1","job":JOB,"source_sha":SOURCE,"archive_sha256":ARCHIVE,"started_utc":datetime.now(timezone.utc).isoformat(),"status":"CHECKING","original_launch_receipt":str(original_path),"original_launch_receipt_sha256":hashlib.sha256(original_bytes).hexdigest(),"local_artifact_sha256":ARTIFACT,"artifact_bytes":ARTIFACT_BYTES,"ledger_sha256":hashlib.sha256(ledger_bytes).hexdigest(),"budget":{"cap_usd":"400.00","reserved_usd":"18.00","remaining_unreserved_usd":"382.00","this_job_reserved_usd":"7.00","refunds":0},"provider_mutations":0,"original_receipt_mutations":0,"budget_mutations":0,"checks":{},"raw_provider_calls":str(raw_path)}
    cfg=Config(connect_timeout=10,read_timeout=20,retries={"max_attempts":0})
    session=boto3.Session(profile_name="default",region_name="us-west-2")
    clients={name:session.client(name,config=cfg) for name in READ_ONLY_OPERATIONS}
    def call(service,operation,**kwargs):
        require(operation in READ_ONLY_OPERATIONS.get(service,set()),"NON_READ_ONLY_OPERATION_FORBIDDEN")
        entry={"utc":datetime.now(timezone.utc).isoformat(),"service":service,"operation":operation,"arguments":kwargs}
        try:
            response=getattr(clients[service],operation)(**kwargs)
            if operation=="get_object":
                require(kwargs["Bucket"]==BUCKET and kwargs["Key"]=="results/complete.json","PRIVATE_RESULT_CONTENT_READ_FORBIDDEN")
                body=response["Body"].read(4097)
                require(len(body)<=4096,"COMPLETION_RECEIPT_SIZE_CEILING")
                response={key:value for key,value in response.items() if key!="Body"}
                response["body_json"]=json.loads(body)
                response["body_sha256"]=hashlib.sha256(body).hexdigest()
            entry["response"]=response
            return response
        except ClientError as exc:
            entry["error"]=exc.response
            raise
        finally:
            with raw_path.open("a",encoding="utf-8") as stream:
                stream.write(json.dumps(entry,sort_keys=True,default=str)+"\n")
    def absent(service,operation,expected,**kwargs):
        try:
            call(service,operation,**kwargs)
        except ClientError as exc:
            require(exc.response["Error"]["Code"]==expected,"UNEXPECTED_PROVIDER_ABSENCE_ERROR")
            return True
        return False
    try:
        identity=call("sts","get_caller_identity")
        require(identity["Account"]==ACCOUNT,"AWS_ACCOUNT_MISMATCH")
        response=call("ec2","describe_instances",InstanceIds=[INSTANCE])
        instance=response["Reservations"][0]["Instances"][0]
        require(instance["ClientToken"]==JOB and {tag["Key"]:tag["Value"] for tag in instance.get("Tags",[])}.get("cas_meta_job")==JOB,"INSTANCE_OWNERSHIP_MISMATCH")
        checks=receipt["checks"]
        checks["instance_terminated"]=instance["State"]["Name"]=="terminated"
        receipt["instance_state"]=instance["State"]["Name"]
        checks["volume_absent"]=absent("ec2","describe_volumes","InvalidVolume.NotFound",VolumeIds=[VOLUME])
        tagged=call("ec2","describe_volumes",Filters=[{"Name":"tag:cas_meta_job","Values":[JOB]}])
        checks["no_tagged_volumes"]=not tagged["Volumes"] and not tagged.get("NextToken")
        checks["security_group_absent"]=absent("ec2","describe_security_groups","InvalidGroup.NotFound",GroupIds=[SG])
        checks["profile_absent"]=absent("iam","get_instance_profile","NoSuchEntity",InstanceProfileName=WORKER)
        checks["worker_role_absent"]=absent("iam","get_role","NoSuchEntity",RoleName=WORKER)
        checks["timer_role_absent"]=absent("iam","get_role","NoSuchEntity",RoleName=TIMER)
        checks["schedule_absent"]=absent("scheduler","get_schedule","ResourceNotFoundException",Name=JOB)
        tagging=call("s3","get_bucket_tagging",Bucket=BUCKET)
        checks["bucket_job_owned"]={item["Key"]:item["Value"] for item in tagging["TagSet"]}.get("cas_meta_job")==JOB
        objects=call("s3","list_objects_v2",Bucket=BUCKET)
        expected={"results/artifacts.zip","results/bootstrap.log","results/complete.json"}
        checks["exactly_three_result_objects_retained"]={item["Key"] for item in objects.get("Contents",[])}==expected and not objects.get("IsTruncated")
        checks["result_objects_below_1gib"]=sum(item["Size"] for item in objects.get("Contents",[]))<=1024**3
        receipt["retained_result_objects"]=objects.get("Contents",[])
        lifecycle=call("s3","get_bucket_lifecycle_configuration",Bucket=BUCKET)
        checks["seven_day_expiration"]=any(rule.get("Status")=="Enabled" and rule.get("Filter")=={"Prefix":""} and rule.get("Expiration",{}).get("Days")==7 for rule in lifecycle["Rules"])
        checks["incomplete_upload_cleanup"]=any(rule.get("Status")=="Enabled" and rule.get("AbortIncompleteMultipartUpload",{}).get("DaysAfterInitiation")==1 for rule in lifecycle["Rules"])
        public=call("s3","get_public_access_block",Bucket=BUCKET)
        checks["public_access_blocked"]=all(public["PublicAccessBlockConfiguration"].get(key) is True for key in ("BlockPublicAcls","IgnorePublicAcls","BlockPublicPolicy","RestrictPublicBuckets"))
        encryption=call("s3","get_bucket_encryption",Bucket=BUCKET)
        checks["bucket_default_encrypted"]=any(rule.get("ApplyServerSideEncryptionByDefault",{}).get("SSEAlgorithm")=="AES256" for rule in encryption["ServerSideEncryptionConfiguration"]["Rules"])
        artifact_head=call("s3","head_object",Bucket=BUCKET,Key="results/artifacts.zip")
        checks["remote_artifact_size_matches_download"]=artifact_head["ContentLength"]==ARTIFACT_BYTES
        checks["remote_artifact_encrypted"]=artifact_head.get("ServerSideEncryption")=="AES256"
        completion=call("s3","get_object",Bucket=BUCKET,Key="results/complete.json")["body_json"]
        checks["remote_completion_binds_local_artifact"]=(completion.get("job")==JOB and completion.get("sha256")==ARTIFACT and completion.get("bytes")==ARTIFACT_BYTES and completion.get("returncode")==0 and completion.get("smoke_only") is False and completion.get("partial_evidence") is False and completion.get("omitted_full_file_count")==0)
        checks["original_launch_receipt_unchanged"]=original_path.read_bytes()==original_bytes
        checks["budget_ledger_unchanged"]=ledger_path.read_bytes()==ledger_bytes
        require(all(checks.values()),"ONE_OR_MORE_CLOSURE_CHECKS_FAILED")
        receipt["status"]="CAS_META_2_FULL_002_CLEANUP_INDEPENDENTLY_VERIFIED"
        receipt["cost_estimate_from_original_receipt"]=original.get("cost_estimate")
        receipt["evidence_boundary"]="Independent current provider cleanup and retention checks. Local artifact bytes rehashed; remote artifact size and completion digest checked without rereading private evaluation content. Cost remains an estimate, not an AWS invoice."
    except Exception as exc:
        receipt["status"]="CAS_META_2_FULL_002_CLEANUP_VERIFICATION_FAILED"
        receipt["failure"]={"type":type(exc).__name__,"message":str(exc)}
        raise
    finally:
        receipt["finished_utc"]=datetime.now(timezone.utc).isoformat()
        receipt["helper_sha256"]=sha(__file__)
        if raw_path.exists(): receipt["raw_provider_calls_sha256"]=sha(raw_path)
        result_path.write_text(json.dumps(receipt,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps(receipt,indent=2,default=str),flush=True)


if __name__=="__main__": main()
