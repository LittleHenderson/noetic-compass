"""Close this one finished smoke job; preserve all S3 evidence and original receipts."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import time
import zipfile

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
JOB = "cas-meta2-20260905164134-b6dc38fe"
INSTANCE = "i-0ff419349834386fd"
VOLUME = "vol-0189027e5c1f303a7"
SG = "sg-09035f3dd489acab9"
ACCOUNT = "807562639912"
BUCKET = JOB + "-" + ACCOUNT
WORKER, TIMER = JOB + "-worker", JOB + "-timer"
ARTIFACT_HASH = "66582357c3c39078ae1788eed2988abcc7342504b3fa216b168b2f6130711fc0"
RECEIPT = ROOT / "records" / "aws_smoke_001" / "launch_receipt.json"
ARTIFACT = RECEIPT.with_name("cloud_artifacts.zip")


def require(condition, reason):
    if not condition: raise ValueError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    require(not (OUT/"correction_receipt.json").exists(),"NEW_CORRECTION_RECEIPT_REQUIRED")
    original_bytes = RECEIPT.read_bytes()
    original = json.loads(original_bytes)
    resources = original["resources"]
    require(original["job"] == JOB and resources["instance"] == INSTANCE and resources["security_group"] == SG and resources["bucket"] == BUCKET,"OWNED_RESOURCE_BINDING_MISMATCH")
    require(original["status"] == "CLEANUP_REQUIRES_ATTENTION" and original["result"]["sha256"] == ARTIFACT_HASH,"FINISHED_CLIENT_AND_VERIFIED_ARTIFACT_REQUIRED")
    require(sha(ARTIFACT) == ARTIFACT_HASH,"ARTIFACT_BYTES_CHANGED")
    with zipfile.ZipFile(ARTIFACT) as archive:
        require(archive.testzip() is None,"ARTIFACT_CRC_FAILURE")
        collection=json.loads(archive.read("artifact_collection_receipt.json"))
        require(collection["job"]==JOB and collection["source_sha"]==original["source_sha"],"ARTIFACT_SOURCE_BINDING_MISMATCH")
    receipt={"schema":"cas-meta2-owned-cleanup-correction/1","job":JOB,"source_sha":original["source_sha"],"started_utc":datetime.now(timezone.utc).isoformat(),"original_launch_receipt_sha256":hashlib.sha256(original_bytes).hexdigest(),"artifact_sha256":ARTIFACT_HASH,"status":"CHECKING","events":[],"provider_mutations":0,"s3_mutations":0,"ledger_changes":0,"termination_requests_repeated":0}
    config=Config(connect_timeout=10,read_timeout=20,retries={"max_attempts":0})
    session=boto3.Session(profile_name="default",region_name="us-west-2")
    clients={name:session.client(name,config=config) for name in ("sts","ec2","iam","scheduler","s3")}

    def save():
        (OUT/"correction_receipt.json").write_text(json.dumps(receipt,indent=2,default=str)+"\n",encoding="utf-8")

    def call(service,operation,**kwargs):
        entry={"utc":datetime.now(timezone.utc).isoformat(),"service":service,"operation":operation,"arguments":kwargs}
        if operation.startswith(("delete_","remove_")):
            receipt["provider_mutations"]+=1
        try:
            response=getattr(clients[service],operation)(**kwargs)
            entry["response"]=response
            return response
        except ClientError as exc:
            entry["error"]=exc.response
            raise
        finally:
            with (OUT/"provider_calls.jsonl").open("a",encoding="utf-8") as stream:
                stream.write(json.dumps(entry,default=str,sort_keys=True)+"\n")

    def tags(value):
        require({tag["Key"]:tag["Value"] for tag in value}.get("cas_meta_job")==JOB,"RESOURCE_TAG_MISMATCH")

    def absent(service,operation,code,**kwargs):
        try:
            call(service,operation,**kwargs)
        except ClientError as exc:
            require(exc.response["Error"]["Code"]==code,"UNEXPECTED_ABSENCE_ERROR")
            return True
        return False

    try:
        identity=call("sts","get_caller_identity")
        require(identity["Account"]==ACCOUNT,"AWS_ACCOUNT_MISMATCH")
        deadline=time.monotonic()+300
        while True:
            response=call("ec2","describe_instances",InstanceIds=[INSTANCE])
            instance=response["Reservations"][0]["Instances"][0]
            tags(instance.get("Tags",[]))
            require(instance["ClientToken"]==JOB,"INSTANCE_CLIENT_TOKEN_MISMATCH")
            receipt["instance_state"]=instance["State"]["Name"]
            print(json.dumps({"utc":datetime.now(timezone.utc).isoformat(),"instance_state":receipt["instance_state"]}),flush=True)
            save()
            if receipt["instance_state"]=="terminated": break
            require(receipt["instance_state"]=="shutting-down","UNEXPECTED_INSTANCE_STATE_NO_DUPLICATE_TERMINATION")
            if time.monotonic()>=deadline: raise ValueError("TERMINATION_STILL_PENDING_NO_DUPLICATE_REQUEST")
            time.sleep(20)
        receipt["termination_confirmed_utc"]=datetime.now(timezone.utc).isoformat()
        elapsed=Decimal(str((datetime.now(timezone.utc)-instance["LaunchTime"]).total_seconds()))
        receipt["cost_observation"]={"provider_launch_time":instance["LaunchTime"],"elapsed_seconds_upper_observation":str(elapsed),"compute_only_conservative_estimate_usd":str(elapsed/Decimal(3600)*Decimal("2.52")),"reservation_usd":"7.00","caveat":"Elapsed-to-observed-termination estimate, not AWS invoice; excludes storage, IPv4, requests, transfer and taxes. No refund."}
        volume_deadline=time.monotonic()+120
        while True:
            response=call("ec2","describe_volumes",Filters=[{"Name":"tag:cas_meta_job","Values":[JOB]}])
            require(not response.get("NextToken"),"VOLUME_QUERY_PAGINATED")
            volumes=response["Volumes"]
            require(len(volumes)<=1,"UNEXPECTED_MULTIPLE_JOB_VOLUMES")
            if not volumes: break
            for volume in volumes:
                tags(volume.get("Tags",[]))
                require(volume["VolumeId"]==VOLUME,"UNEXPECTED_OWNED_VOLUME_ID")
            if time.monotonic()>=volume_deadline: raise ValueError("AUTOMATIC_VOLUME_DELETION_PENDING")
            time.sleep(10)
        receipt["volume_absent"]=absent("ec2","describe_volumes","InvalidVolume.NotFound",VolumeIds=[VOLUME])
        require(receipt["volume_absent"],"VOLUME_STILL_EXISTS")
        # The scheduler cannot be tagged individually: bind its exact job name,
        # role ARN and one-instance target before removing it.
        try:
            schedule=call("scheduler","get_schedule",Name=JOB)
            require(schedule["Name"]==JOB and schedule["Target"]["RoleArn"]==resources[TIMER] and json.loads(schedule["Target"]["Input"])=={"InstanceIds":[INSTANCE]},"SCHEDULE_OWNERSHIP_MISMATCH")
            call("scheduler","delete_schedule",Name=JOB)
        except ClientError as exc:
            require(exc.response["Error"]["Code"]=="ResourceNotFoundException","SCHEDULE_DELETE_FAILED")
        try:
            profile=call("iam","get_instance_profile",InstanceProfileName=WORKER)["InstanceProfile"]
            tags(profile.get("Tags",[]))
            require(all(role["RoleName"]==WORKER for role in profile.get("Roles",[])),"UNEXPECTED_PROFILE_ROLE")
            if profile.get("Roles"): call("iam","remove_role_from_instance_profile",InstanceProfileName=WORKER,RoleName=WORKER)
            call("iam","delete_instance_profile",InstanceProfileName=WORKER)
        except ClientError as exc:
            require(exc.response["Error"]["Code"]=="NoSuchEntity","PROFILE_DELETE_FAILED")
        for name in (WORKER,TIMER):
            try:
                role=call("iam","get_role",RoleName=name)["Role"]
                tags(role.get("Tags",[]))
                require(role["Arn"]==resources[name],"ROLE_ARN_MISMATCH")
                policies=call("iam","list_role_policies",RoleName=name)
                attached=call("iam","list_attached_role_policies",RoleName=name)
                require(not policies.get("IsTruncated") and set(policies["PolicyNames"]).issubset({"job-only"}) and not attached.get("IsTruncated") and not attached["AttachedPolicies"],"UNEXPECTED_ROLE_POLICY")
                if policies["PolicyNames"]: call("iam","delete_role_policy",RoleName=name,PolicyName="job-only")
                call("iam","delete_role",RoleName=name)
            except ClientError as exc:
                require(exc.response["Error"]["Code"]=="NoSuchEntity","ROLE_DELETE_FAILED")
        try:
            groups=call("ec2","describe_security_groups",GroupIds=[SG])["SecurityGroups"]
            require(len(groups)==1 and groups[0]["GroupName"]==JOB,"SECURITY_GROUP_IDENTITY_MISMATCH")
            tags(groups[0].get("Tags",[]))
            call("ec2","delete_security_group",GroupId=SG)
        except ClientError as exc:
            require(exc.response["Error"]["Code"]=="InvalidGroup.NotFound","SECURITY_GROUP_DELETE_FAILED")
        checks={"instance_terminated":True,"volume_absent":receipt["volume_absent"],"schedule_absent":absent("scheduler","get_schedule","ResourceNotFoundException",Name=JOB),"profile_absent":absent("iam","get_instance_profile","NoSuchEntity",InstanceProfileName=WORKER),"worker_role_absent":absent("iam","get_role","NoSuchEntity",RoleName=WORKER),"timer_role_absent":absent("iam","get_role","NoSuchEntity",RoleName=TIMER),"security_group_absent":absent("ec2","describe_security_groups","InvalidGroup.NotFound",GroupIds=[SG])}
        tags(call("s3","get_bucket_tagging",Bucket=BUCKET)["TagSet"])
        objects=call("s3","list_objects_v2",Bucket=BUCKET)
        require(not objects.get("IsTruncated"),"S3_OBJECT_QUERY_TRUNCATED")
        expected={"input/payload.zip","input/remote.py","input/permit.json","results/artifacts.zip","results/bootstrap.log","results/complete.json"}
        checks["all_six_evidence_objects_preserved"]={obj["Key"] for obj in objects.get("Contents",[])}==expected
        lifecycle=call("s3","get_bucket_lifecycle_configuration",Bucket=BUCKET)
        checks["seven_day_retention"]=any(rule.get("Status")=="Enabled" and rule.get("Expiration",{}).get("Days")==7 for rule in lifecycle["Rules"])
        require(RECEIPT.read_bytes()==original_bytes,"ORIGINAL_LAUNCH_RECEIPT_CHANGED")
        checks["original_receipt_unchanged"]=True
        checks["artifact_unchanged"]=sha(ARTIFACT)==ARTIFACT_HASH
        receipt["checks"]=checks
        receipt["retained_s3_objects"]=objects.get("Contents",[])
        require(all(checks.values()),"CLEANUP_FINAL_CHECK_FAILED")
        receipt["status"]="CAS_META_2_SMOKE_001_CLEANUP_VERIFIED"
    except Exception as exc:
        receipt["status"]="CAS_META_2_SMOKE_001_CLEANUP_PENDING"
        receipt["failure"]={"type":type(exc).__name__,"message":str(exc)}
        raise
    finally:
        receipt["finished_utc"]=datetime.now(timezone.utc).isoformat()
        log=OUT/"provider_calls.jsonl"
        if log.exists(): receipt["provider_calls_sha256"]=sha(log)
        receipt["helper_sha256"]=sha(__file__)
        save()
        print(json.dumps(receipt,indent=2,default=str),flush=True)


if __name__=="__main__": main()
