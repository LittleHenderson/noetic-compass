"""One throwaway AWS machine for the Lean check of the CAS compiler. Run from the laptop; it only talks to AWS.

    python box.py launch     # needs the owner's yes in chat first
    python box.py status
    python box.py teardown   # terminate the machine, delete its key pair and firewall group, delete the local key

What it creates, and nothing else:
  * ONE c7i.xlarge (4 vCPU, 8 GB) on-demand in us-west-2, Ubuntu 24.04, 30 GB gp3 disk deleted with the machine;
  * ONE key pair and ONE security group (inbound SSH from this laptop's current public address only).
Limits: the machine powers itself off after MAX_MINUTES and is set to be DESTROYED on power-off.
Worst case: MAX_MINUTES at PRICE_PER_HOUR plus cents of disk and address, under DOLLAR_CEILING.
The machine gets no AWS credentials. The private key lives only in the session scratchpad and is deleted by teardown.
"""
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE / "box_record.json"
REGION = "us-west-2"
INSTANCE_TYPE, PRICE_PER_HOUR = "c7i.xlarge", 0.1785
MAX_MINUTES, DOLLAR_CEILING = 180, 1.00
AMI_PARAMETER = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
KEY_DIR = pathlib.Path(os.environ.get("CAS_LEAN_KEY_DIR", str(HERE)))
NAME_PREFIX = "cas-lean-check"

USER_DATA = """#!/bin/bash
# Kill switch: the operating system powers off after %d minutes whatever happens; power-off destroys the machine.
shutdown -h +%d "cas-lean-check hard limit" || true
echo "cas-lean-check box up $(date -u +%%FT%%TZ)" > /var/log/cas_lean_box.log
""" % (MAX_MINUTES, MAX_MINUTES)


def clients():
    import boto3
    return boto3.client("ec2", region_name=REGION), boto3.client("ssm", region_name=REGION)


def launch():
    if RECORD.exists() and json.loads(RECORD.read_text()).get("state") != "torn_down":
        raise SystemExit("LAUNCH_REFUSED: box_record.json shows a machine that has not been torn down")
    worst = PRICE_PER_HOUR * MAX_MINUTES / 60.0 + 0.05
    assert worst < DOLLAR_CEILING, "time limit does not keep the job under the ceiling"
    ec2, ssm = clients()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = "%s-%s" % (NAME_PREFIX, stamp)
    running = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [NAME_PREFIX + "-*"]},
                                              {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if running:
        raise SystemExit("LAUNCH_REFUSED: a cas-lean-check machine is already running")
    my_ip = urllib.request.urlopen("https://checkip.amazonaws.com", timeout=20).read().decode().strip()
    ami = ssm.get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
    image = ec2.describe_images(ImageIds=[ami])["Images"][0]
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    subnet = sorted(subnets, key=lambda s: s["AvailabilityZone"])[0]

    record = {"schema": "cas-lean-check.box/0.1", "state": "creating", "name": name, "region": REGION,
              "instance_type": INSTANCE_TYPE, "price_per_hour_usd": PRICE_PER_HOUR, "max_minutes": MAX_MINUTES,
              "dollar_ceiling": DOLLAR_CEILING, "worst_case_usd": round(worst, 4), "ami": ami, "ami_name": image.get("Name"),
              "ssh_allowed_from": my_ip + "/32", "purpose": "Lean 4 check of the CAS compiler (compiler.py blob 439c4908)"}
    key = ec2.create_key_pair(KeyName=name, KeyType="ed25519")
    record["key_pair"] = name
    pem = KEY_DIR / (name + ".pem")
    pem.write_text(key["KeyMaterial"], encoding="utf-8", newline="\n")
    record["local_key_file"] = str(pem)
    RECORD.write_text(json.dumps(record, indent=1), encoding="utf-8")
    group = ec2.create_security_group(GroupName=name, Description="cas-lean-check SSH from one address", VpcId=vpc)["GroupId"]
    record["security_group"] = group
    RECORD.write_text(json.dumps(record, indent=1), encoding="utf-8")
    ec2.authorize_security_group_ingress(GroupId=group, IpPermissions=[{
        "IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": my_ip + "/32", "Description": "laptop"}]}])
    tags = [{"Key": "Name", "Value": name}, {"Key": "Purpose", "Value": "Lean check of the CAS compiler"},
            {"Key": "SelfTerminates", "Value": "yes-%d-minutes" % MAX_MINUTES}]
    out = ec2.run_instances(
        ImageId=ami, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, KeyName=name,
        NetworkInterfaces=[{"DeviceIndex": 0, "SubnetId": subnet["SubnetId"], "Groups": [group], "AssociatePublicIpAddress": True}],
        InstanceInitiatedShutdownBehavior="terminate", UserData=USER_DATA, MetadataOptions={"HttpTokens": "required"},
        BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"], "Ebs": {"VolumeSize": 30, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
    iid = out["Instances"][0]["InstanceId"]
    print("LAUNCHED INSTANCE ID: %s" % iid, flush=True)
    record.update({"state": "running", "instance_id": iid, "launched_utc": out["Instances"][0]["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "subnet": subnet["SubnetId"], "availability_zone": subnet["AvailabilityZone"]})
    RECORD.write_text(json.dumps(record, indent=1), encoding="utf-8")
    ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
    ip = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0].get("PublicIpAddress")
    record["public_ip"] = ip
    RECORD.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("instance_id", "public_ip", "availability_zone", "max_minutes", "worst_case_usd")}))


def status():
    record = json.loads(RECORD.read_text())
    ec2, _ = clients()
    if record.get("instance_id"):
        inst = ec2.describe_instances(InstanceIds=[record["instance_id"]])["Reservations"][0]["Instances"][0]
        print(record["instance_id"], inst["State"]["Name"], inst.get("PublicIpAddress"), inst["LaunchTime"])
    print(json.dumps(record, indent=1))


def teardown():
    record = json.loads(RECORD.read_text())
    ec2, _ = clients()
    if record.get("instance_id"):
        ec2.terminate_instances(InstanceIds=[record["instance_id"]])
        ec2.get_waiter("instance_terminated").wait(InstanceIds=[record["instance_id"]])
        print("terminated", record["instance_id"])
    if record.get("security_group"):
        for attempt in range(10):
            try:
                ec2.delete_security_group(GroupId=record["security_group"])
                print("deleted security group", record["security_group"])
                break
            except Exception as exc:  # the network interface can take a moment to go
                if attempt == 9:
                    raise
                print("waiting to delete security group:", exc)
                time.sleep(15)
    if record.get("key_pair"):
        ec2.delete_key_pair(KeyName=record["key_pair"])
        print("deleted key pair", record["key_pair"])
    pem = pathlib.Path(record.get("local_key_file", ""))
    if pem.is_file():
        pem.unlink()
        print("deleted local key file")
    record["state"] = "torn_down"
    record["torn_down_utc"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    RECORD.write_text(json.dumps(record, indent=1), encoding="utf-8")


if __name__ == "__main__":
    {"launch": launch, "status": status, "teardown": teardown}[sys.argv[1]]()
