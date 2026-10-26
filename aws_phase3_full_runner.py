"""Launch one t3.small to run the full-exam Phase 3 valve acceptance (CAS-LAB-014)."""
from __future__ import annotations

import json
import shutil
import sys
import tarfile
import time
from pathlib import Path

import boto3
from botocore.config import Config

REGION = "us-west-2"
BUCKET = "cas-harness-runpod-92754088"
AMI = "ami-0dddfa1ffa6b87af7"
SUBNET = "subnet-02deacfa16bdaa4f4"
SG = "sg-0562c483e0364cdab"
PROFILE = "cas-aws-gpu-standby-v1-us-west-2"
TYPE = "t3.small"
RATE = 0.0208
REPO = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS")
DATA = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\lacunarity_e1\data")
GEN = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws\generation")
BUILD = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\p3full_payload")
STAMP = time.strftime("p3full-%Y%m%d-%H%M%S")
PREFIX = "bridge-control-20260822/" + STAMP + "/"

s3 = boto3.client("s3", region_name=REGION, config=Config(retries={"max_attempts": 5}))
ec2 = boto3.client("ec2", region_name=REGION)


def build() -> Path:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    pkg = BUILD / "pkg"
    pkg.mkdir(parents=True)
    for f in ("phase3_full_exam.py", "aws_phase3_driver.py", "test_phase3_valve_ctt_acceptance.py",
              "tks_meta_valve_controller.py"):
        shutil.copy2(REPO / f, pkg / f)
    shutil.copy2(REPO / "HELM_DISTRIBUTION_PACKAGE" / "brains" / "tks_meta_valve_weights_v0_4.json",
                 pkg / "tks_meta_valve_weights_v0_4.json")
    shutil.copy2(DATA / "mouth_exam.jsonl", pkg / "mouth_exam.jsonl")
    shutil.copy2(GEN / "gen_A4-s1_step_01000.jsonl", pkg / "gen_step1000.jsonl")
    shutil.copy2(GEN / "gen_A4-s1_final.jsonl", pkg / "gen_final.jsonl")
    with open(pkg / "run.sh", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("cd /opt/p3/payload || exit 2\n")
        fh.write("python3 -B phase3_full_exam.py --generation gen_step1000.jsonl --exam mouth_exam.jsonl --out /opt/p3/r_step1000.json\n")
        fh.write("python3 -B phase3_full_exam.py --generation gen_final.jsonl --exam mouth_exam.jsonl --out /opt/p3/r_final.json\n")
    tar = BUILD / "input.tar.gz"
    with tarfile.open(tar, "w:gz") as t:
        t.add(pkg, arcname="payload")
    print("payload", tar.stat().st_size, flush=True)
    return tar


def user_data() -> str:
    return f"""#!/bin/bash
set -uo pipefail
exec > /var/log/p3.log 2>&1
B='{BUCKET}'; P='{PREFIX}'; export AWS_DEFAULT_REGION=us-west-2 AWS_PAGER=
trap 'echo EXIT=$? > /opt/p3/exit.txt; aws s3 cp /opt/p3/exit.txt s3://$B/${{P}}results/exit.txt 2>/dev/null; aws s3 cp /var/log/p3.log s3://$B/${{P}}results/p3.log 2>/dev/null' EXIT
mkdir -p /opt/p3 && cd /opt/p3
aws s3 cp s3://$B/${{P}}input.tar.gz /opt/p3/input.tar.gz
tar xzf input.tar.gz
cd /opt/p3/payload
bash run.sh
for f in /opt/p3/r_step1000.json /opt/p3/r_final.json; do aws s3 cp "$f" s3://$B/${{P}}results/$(basename "$f"); done
shutdown -h now
"""


def main() -> int:
    tar = build()
    if "--dry-run" in sys.argv:
        return 0
    s3.upload_file(str(tar), BUCKET, PREFIX + "input.tar.gz")
    t0 = time.time()
    r = ec2.run_instances(ImageId=AMI, InstanceType=TYPE, MinCount=1, MaxCount=1, SubnetId=SUBNET,
                          SecurityGroupIds=[SG], IamInstanceProfile={"Name": PROFILE}, UserData=user_data(),
                          BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 20, "VolumeType": "gp3",
                                                                                   "DeleteOnTermination": True}}],
                          TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": STAMP}]}])
    iid = r["Instances"][0]["InstanceId"]
    print(json.dumps({"instance": iid, "prefix": PREFIX}), flush=True)
    done = False
    for _ in range(40):
        time.sleep(15)
        try:
            objs = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX + "results/").get("Contents", [])
            if "exit.txt" in {o["Key"].split("/")[-1] for o in objs}:
                done = True
                break
        except Exception:
            pass
    for name in ("r_step1000.json", "r_final.json"):
        try:
            body = s3.get_object(Bucket=BUCKET, Key=PREFIX + "results/" + name)["Body"].read().decode("utf-8")
            res = json.loads(body)
            (REPO / ("docs/working/ctt_lacunarity_v1/results/" + STAMP + "_" + name)).write_text(
                json.dumps(res, indent=1), encoding="utf-8")
            print(name, json.dumps(res["summary"]), flush=True)
        except Exception as e:
            print("missing", name, e, flush=True)
    elapsed = time.time() - t0
    ec2.terminate_instances(InstanceIds=[iid])
    print(json.dumps({"done": done, "instance": iid, "elapsed_s": round(elapsed, 1),
                      "estimated_usd": round(elapsed / 3600.0 * RATE, 5)}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

