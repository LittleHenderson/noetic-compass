# -*- coding: utf-8 -*-
import boto3, base64, json, pathlib, sys, time
SP = pathlib.Path(__file__).resolve().parent
s = boto3.Session(region_name="us-west-2")
ec2, iam, s3 = s.client("ec2"), s.client("iam"), s.client("s3")
BUCKET, PREFIX = "cas-harness-runpod-92754088", "bridge-control-20260822"

# 1. upload bundle
s3.upload_file(str(SP / "bundle.zip"), BUCKET, f"{PREFIX}/bundle.zip")
print("bundle uploaded")

# 2. launch
ud = base64.b64encode((SP / "bootstrap_userdata.sh").read_text(encoding="utf-8").encode()).decode()
r = ec2.run_instances(
    LaunchTemplate={"LaunchTemplateId": "lt-0521aede1946e3bd7", "Version": "1"},
    MinCount=1, MaxCount=1, UserData=ud,
    TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "cas-bridge-control-20260822"}]}],
)
iid = r["Instances"][0]["InstanceId"]
print("INSTANCE_ID", iid)

# 3. scoped inline policy on the standby role
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"],
         "Resource": [f"arn:aws:s3:::{BUCKET}/{PREFIX}/*"]},
        {"Effect": "Allow", "Action": ["ec2:DescribeInstances", "ec2:ModifyInstanceAttribute", "ec2:TerminateInstances"],
         "Resource": [f"arn:aws:ec2:us-west-2:807562639912:instance/{iid}"]},
    ],
}
iam.put_role_policy(RoleName="cas-aws-gpu-standby-v1-us-west-2", PolicyName="bridge-control-20260822", PolicyDocument=json.dumps(policy))
print("policy attached")

(SP / "launch_state.json").write_text(json.dumps({"instance_id": iid, "launched_at": time.time()}, indent=2))
print("launch_state.json written")
