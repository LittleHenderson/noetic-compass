"""Launch one AWS GPU instance for the dose-0.20 replication (seeds 2,3) and the RPM selector test.

Same shape as aws_score_launch.py: tar.gz payload (no unzip on the image), bridge-control prefix, terminate on finish.

    python aws_replicate_launch.py [--dry-run]
"""
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
BUILD = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\rep_payload")
STAMP = time.strftime("replicate-%Y%m%d-%H%M%S")
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
    for f in ("vocab.json", "FUNCTION_WORDS.json", "FACT_WORDS.json", "mouth_exam.jsonl",
              "notation_new100.jsonl", "labels_notation.jsonl"):
        shutil.copy2(PKG / "data" / f, pkg / "data" / f)
    for f in ("rt_score.py", "composite.py", "rpm_select.py", "gen_steer.py", "aws_replicate_driver.py"):
        shutil.copy2(PKG / f, pkg / f)
    (pkg / "weights").mkdir()
    shutil.copy2(PKG / "weights" / "A4-s1.pt", pkg / "weights" / "A4-s1.pt")
    (pkg / "ckpt").mkdir()
    shutil.copy2(CS / "results" / "out" / "A4-s1" / "step_01000.pt", pkg / "ckpt" / "s1.pt")
    for seed in ("A4-s2", "A4-s3"):
        d = pkg / "ckpt_src" / seed
        d.mkdir(parents=True)
        shutil.copy2(CS / "results" / "out" / seed / "step_01000.pt", d / "step_01000.pt")
    tar = BUILD / "input.tar.gz"
    with tarfile.open(tar, "w:gz") as t:
        t.add(pkg, arcname="pkg")
    print("payload", tar, tar.stat().st_size, flush=True)
    return tar


def user_data() -> str:
    return f"""#!/bin/bash
set -uo pipefail
exec > /var/log/rep.log 2>&1
B='{BUCKET}'; P='{PREFIX}'; export AWS_DEFAULT_REGION=us-west-2 AWS_PAGER=
trap 'echo EXIT=$? > /opt/rep/exit.txt; aws s3 cp /opt/rep/exit.txt s3://$B/${{P}}results/exit.txt 2>/dev/null; aws s3 cp /var/log/rep.log s3://$B/${{P}}results/rep.log 2>/dev/null' EXIT
mkdir -p /opt/rep && cd /opt/rep
echo "start $(date -u)" > /opt/rep/marker.txt
aws s3 cp /opt/rep/marker.txt s3://$B/${{P}}results/marker.txt 2>/dev/null
aws s3 cp s3://$B/${{P}}input.tar.gz /opt/rep/input.tar.gz
tar xzf input.tar.gz
cd /opt/rep/pkg
PY=""
for c in /opt/pytorch/bin/python3 /opt/conda/envs/pytorch/bin/python3 /usr/bin/python3; do
  if [ -x "$c" ] && "$c" -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then echo NO_TORCH > /opt/rep/exit.txt; aws s3 cp /opt/rep/exit.txt s3://$B/${{P}}results/exit.txt; shutdown -h now; exit 1; fi
timeout 5400 "$PY" -X utf8 -B aws_replicate_driver.py --out results.json > /opt/rep/driver.log 2>&1
aws s3 cp results.json s3://$B/${{P}}results/results.json
aws s3 cp /opt/rep/driver.log s3://$B/${{P}}results/driver.log
shutdown -h now
"""


def main() -> int:
    tar = build_payload()
    if "--dry-run" in sys.argv:
        print("dry-run ok", tar.stat().st_size)
        return 0
    s3.upload_file(str(tar), BUCKET, PREFIX + "input.tar.gz")
    print("uploaded", PREFIX + "input.tar.gz", flush=True)
    t0 = time.time()
    r = ec2.run_instances(
        ImageId=AMI, InstanceType=TYPE, MinCount=1, MaxCount=1,
        SubnetId=SUBNET, SecurityGroupIds=[SG],
        IamInstanceProfile={"Name": PROFILE},
        UserData=user_data(),
        BlockDeviceMappings=[{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 60, "VolumeType": "gp3",
                                                                  "DeleteOnTermination": True}}],
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": STAMP}]}],
    )
    iid = r["Instances"][0]["InstanceId"]
    print(json.dumps({"instance": iid, "prefix": PREFIX}), flush=True)
    done = False
    for _ in range(180):                       # 180 × 30 s = 90 min ceiling
        time.sleep(30)
        keys = set()
        try:
            objs = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX + "results/").get("Contents", [])
            keys = {o["Key"].split("/")[-1] for o in objs}
        except Exception:
            pass
        if "exit.txt" in keys:
            done = True
            break
    results = None
    try:
        body = s3.get_object(Bucket=BUCKET, Key=PREFIX + "results/results.json")["Body"].read().decode("utf-8")
        results = json.loads(body)
        (CS / "aws_replicate_results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(json.dumps(results, indent=1), flush=True)
    except Exception as e:
        print("no results:", e, flush=True)
    elapsed = time.time() - t0
    ec2.terminate_instances(InstanceIds=[iid])
    print(json.dumps({"done": done, "instance": iid, "elapsed_s": round(elapsed, 1),
                      "estimated_usd": round(elapsed / 3600.0 * RATE, 4), "prefix": PREFIX}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
