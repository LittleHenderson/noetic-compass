"""Launch one AWS GPU instance for the fixed RPM selector test (CAS-LAB-007)."""
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
TYPE = "g5.xlarge"
RATE = 1.10
PKG = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\lacunarity_e1")
CS = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws")
BUILD = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\op_payload")
STAMP = time.strftime("operator-%Y%m%d-%H%M%S")
PREFIX = "bridge-control-20260822/" + STAMP + "/"

s3 = boto3.client("s3", region_name=REGION, config=Config(retries={"max_attempts": 5}))
ec2 = boto3.client("ec2", region_name=REGION)


def build_payload() -> Path:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    pkg = BUILD / "pkg"
    pkg.mkdir(parents=True)
    for mod in ("helm_cas_translator", "mouth_task", "cube_task"):
        shutil.copytree(PKG / mod, pkg / mod, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (pkg / "data").mkdir()
    for f in ("vocab.json", "notation_new100.jsonl", "labels_notation.jsonl"):
        shutil.copy2(PKG / "data" / f, pkg / "data" / f)
    for f in ("rpm_select.py", "aws_operator_driver.py"):
        shutil.copy2(PKG / f, pkg / f)
    (pkg / "ckpt").mkdir()
    for seed in ("A4-s1", "A4-s2", "A4-s3"):
        shutil.copy2(CS / "results" / "out" / seed / "step_01000.pt", pkg / "ckpt" / (seed + ".pt"))
    tar = BUILD / "input.tar.gz"
    with tarfile.open(tar, "w:gz") as t:
        t.add(pkg, arcname="pkg")
    print("payload", tar.stat().st_size, flush=True)
    return tar


def user_data() -> str:
    return f"""#!/bin/bash
set -uo pipefail
exec > /var/log/op.log 2>&1
B='{BUCKET}'; P='{PREFIX}'; export AWS_DEFAULT_REGION=us-west-2 AWS_PAGER=
trap 'echo EXIT=$? > /opt/op/exit.txt; aws s3 cp /opt/op/exit.txt s3://$B/${{P}}results/exit.txt 2>/dev/null; aws s3 cp /var/log/op.log s3://$B/${{P}}results/op.log 2>/dev/null' EXIT
mkdir -p /opt/op && cd /opt/op
aws s3 cp s3://$B/${{P}}input.tar.gz /opt/op/input.tar.gz
tar xzf input.tar.gz
cd /opt/op/pkg
PY=""
for c in /opt/pytorch/bin/python3 /opt/conda/envs/pytorch/bin/python3 /usr/bin/python3; do
  if [ -x "$c" ] && "$c" -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then echo NO_TORCH > /opt/op/exit.txt; aws s3 cp /opt/op/exit.txt s3://$B/${{P}}results/exit.txt; shutdown -h now; exit 1; fi
timeout 5400 "$PY" -X utf8 -B aws_operator_driver.py > /opt/op/driver.log 2>&1
aws s3 cp results.json s3://$B/${{P}}results/results.json
aws s3 cp /opt/op/driver.log s3://$B/${{P}}results/driver.log
shutdown -h now
"""


def main() -> int:
    tar = build_payload()
    if "--dry-run" in sys.argv:
        print("dry-run ok")
        return 0
    s3.upload_file(str(tar), BUCKET, PREFIX + "input.tar.gz")
    print("uploaded", flush=True)
    t0 = time.time()
    r = ec2.run_instances(ImageId=AMI, InstanceType=TYPE, MinCount=1, MaxCount=1, SubnetId=SUBNET,
                          SecurityGroupIds=[SG], IamInstanceProfile={"Name": PROFILE}, UserData=user_data(),
                          BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 60, "VolumeType": "gp3",
                                                                                   "DeleteOnTermination": True}}],
                          TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": STAMP}]}])
    iid = r["Instances"][0]["InstanceId"]
    print(json.dumps({"instance": iid, "prefix": PREFIX}), flush=True)
    done = False
    for _ in range(120):
        time.sleep(30)
        try:
            objs = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX + "results/").get("Contents", [])
            if "exit.txt" in {o["Key"].split("/")[-1] for o in objs}:
                done = True
                break
        except Exception:
            pass
    try:
        body = s3.get_object(Bucket=BUCKET, Key=PREFIX + "results/results.json")["Body"].read().decode("utf-8")
        res = json.loads(body)
        (CS / "aws_operator_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(json.dumps(res, indent=1), flush=True)
    except Exception as e:
        print("no results:", e, flush=True)
    elapsed = time.time() - t0
    ec2.terminate_instances(InstanceIds=[iid])
    print(json.dumps({"done": done, "instance": iid, "elapsed_s": round(elapsed, 1),
                      "estimated_usd": round(elapsed / 3600.0 * RATE, 4)}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

