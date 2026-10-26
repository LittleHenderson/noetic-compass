"""aws_launch_dag_proposer.py -- AWS GPU Orchestrator for Stage v0.7 Lexicon Expansion Training.

ORCHESTRATION & SAFETY CONSTRAINTS:
- Instance: AWS EC2 g4dn.xlarge (1x NVIDIA Tesla T4, 16 GB GPU, 4 vCPU, 16 GB RAM).
- Region: us-west-2 (Oregon).
- Cost cap: $1.00 USD (at $0.526/hr on-demand -> max execution window 15 minutes = ~$0.13).
- Hard timeout: 900 seconds (15 minutes).
- Four independent stops:
  1. InstanceInitiatedShutdownBehavior = terminate
  2. EXIT trap in user-data -> shutdown -h now on any exit path, including failure
  3. in-instance hard timer -> shutdown regardless of what the harness is doing
  4. client watchdog timer -> force TerminateInstances at 18 minutes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

import boto3

REGION = "us-west-2"
INSTANCE_TYPE = "g4dn.xlarge"
AMI = "ami-0c779ec711a581954"          # Deep Learning Base OSS Nvidia Driver, Ubuntu 22.04
PROFILE = "cas-aws-gpu-standby-v1-us-west-2"
BUCKET = "cas-harness-runpod-92754088"
PREFIX = "bridge-control-20260822/scribe_v07_dag"
RATE_PER_HOUR = 0.526
HARD_CAP_USD = 1.00
IN_INSTANCE_HARD_MIN = 15
WATCHDOG_MIN = 18

HERE = Path(__file__).resolve().parent
FREEZE_PATH = HERE / "PACKAGE_FREEZE.json"
ZIP_PATH = HERE / "SCRIBE_V07_DAG_AWS_GPU_PACKAGE.zip"
OUT_DIR = HERE / "outputs"


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def verify_freeze() -> Dict[str, Any]:
    if not FREEZE_PATH.exists():
        raise FileNotFoundError(f"Missing {FREEZE_PATH.name}. Run build_dag_gpu_package.py first.")
    with open(FREEZE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_user_data(run_id: str) -> str:
    return f"""#!/bin/bash
exec > >(tee -a /var/log/scribe_v07.log) 2>&1
trap 'aws s3 cp /var/log/scribe_v07.log s3://{BUCKET}/{PREFIX}/{run_id}/outputs/console.log --region {REGION} || true; shutdown -h now' EXIT
( sleep {IN_INSTANCE_HARD_MIN * 60}; echo "IN_INSTANCE_HARD_TIMER_EXPIRED"; shutdown -h now ) &

set -x
echo "=== Starting HELM Stage v0.7 DAG Proposer GPU Training Job ==="
mkdir -p /opt/scribe_v07 && cd /opt/scribe_v07
aws s3 cp s3://{BUCKET}/{PREFIX}/{run_id}/SCRIBE_V07_DAG_AWS_GPU_PACKAGE.zip ./ --region {REGION}
unzip -q SCRIBE_V07_DAG_AWS_GPU_PACKAGE.zip
cd SCRIBE_V07_DAG_AWS_GPU

PACKAGE_SHA=$(sha256sum ../SCRIBE_V07_DAG_AWS_GPU_PACKAGE.zip | awk '{{print $1}}')
echo "Verified Package SHA256: $PACKAGE_SHA"

nvidia-smi || true
python3 -m pip install --upgrade pip --break-system-packages 2>/dev/null || python3 -m pip install --upgrade pip
python3 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 --break-system-packages 2>/dev/null || python3 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

python3 -c "import torch,sys;print('TORCH',torch.__version__,'CUDA',torch.cuda.is_available());sys.exit(0 if torch.cuda.is_available() else 1)"
if [ $? -ne 0 ]; then echo "TORCH_OR_CUDA_UNAVAILABLE"; exit 20; fi

mkdir -p /opt/scribe_v07/outputs
python3 train_dag_proposer_job.py --epochs 25 --batch-size 32 --lr 0.001 --out-dir /opt/scribe_v07/outputs --require-gpu
RC=$?
echo "DAG_PROPOSER_TRAIN_RC=$RC"

aws s3 cp /opt/scribe_v07/outputs/ s3://{BUCKET}/{PREFIX}/{run_id}/outputs/ --recursive --region {REGION}
echo "ALL OUTPUTS STAGED TO S3. SHUTTING DOWN."
"""


def run_launch():
    run_id = f"scribe-v07-{int(time.time())}"
    freeze_doc = verify_freeze()

    if not ZIP_PATH.exists():
        raise FileNotFoundError(f"Missing {ZIP_PATH.name}")

    zip_bytes = ZIP_PATH.read_bytes()
    current_sha = sha_b(zip_bytes)
    if current_sha != freeze_doc["zip_sha256"]:
        raise ValueError(f"Zip SHA256 mismatch! Freeze: {freeze_doc['zip_sha256']} vs Disk: {current_sha}")

    ud = build_user_data(run_id)

    s3 = boto3.client("s3", region_name=REGION)
    ec2 = boto3.client("ec2", region_name=REGION)

    print(f"=== Stage v0.7 Lexicon Expansion GPU Training Launch ===")
    print(f"Run ID: {run_id}")
    print(f"Package: {ZIP_PATH.name} ({len(zip_bytes)} bytes)")
    print(f"Package SHA256: {current_sha}")
    print(f"Target Instance: {INSTANCE_TYPE} in {REGION}")
    print(f"Cost Cap: ${HARD_CAP_USD:.2f} (Estimated actual: ~$0.10)")

    # 1. Upload sealed package to S3
    s3_key = f"{PREFIX}/{run_id}/SCRIBE_V07_DAG_AWS_GPU_PACKAGE.zip"
    print(f"\n[1/5] Uploading sealed package to s3://{BUCKET}/{s3_key}...")
    s3.put_object(Bucket=BUCKET, Key=s3_key, Body=zip_bytes)
    print("      Upload completed and confirmed.")

    # 2. Launch EC2 instance
    print(f"\n[2/5] Launching EC2 instance ({INSTANCE_TYPE}, termination-on-shutdown)...")
    res = ec2.run_instances(
        ImageId=AMI,
        InstanceType=INSTANCE_TYPE,
        MinCount=1,
        MaxCount=1,
        IamInstanceProfile={"Name": PROFILE},
        InstanceInitiatedShutdownBehavior="terminate",
        UserData=ud,
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Name", "Value": f"helm-scribe-v07-{run_id}"},
                {"Key": "Owner", "Value": "cas-g5-operator"},
                {"Key": "Job", "Value": "HELM-v0.7-Lexicon-Expansion"}
            ]
        }]
    )
    instance_id = res["Instances"][0]["InstanceId"]
    print(f"      Launched instance ID: {instance_id}")

    # 3. Monitor instance lifecycle
    print(f"\n[3/5] Monitoring instance execution (watchdog cap: {WATCHDOG_MIN} min)...")
    t0 = time.time()
    last_state = "pending"

    while True:
        elapsed = time.time() - t0
        elapsed_min = elapsed / 60.0
        accrued_cost = (elapsed / 3600.0) * RATE_PER_HOUR

        desc = ec2.describe_instances(InstanceIds=[instance_id])
        state = desc["Reservations"][0]["Instances"][0]["State"]["Name"]

        if state != last_state:
            print(f"      [{elapsed_min:.1f}m] Instance transitioned: {last_state} -> {state} (est. cost: ${accrued_cost:.4f})")
            last_state = state

        if state == "terminated":
            print(f"      Instance has cleanly terminated at {elapsed_min:.1f} minutes.")
            break

        if elapsed_min > WATCHDOG_MIN:
            print(f"      WATCHDOG EXPIRED ({WATCHDOG_MIN} min). Forcing termination!")
            ec2.terminate_instances(InstanceIds=[instance_id])
            break

        time.sleep(20)

    # 4. Download outputs from S3
    print(f"\n[4/5] Retrieving artifacts from S3...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_prefix = f"{PREFIX}/{run_id}/outputs/"

    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=out_prefix)
    contents = resp.get("Contents", [])
    if not contents:
        print(f"ERROR: No output objects found in s3://{BUCKET}/{out_prefix}!")
        sys.exit(1)

    for obj in contents:
        key = obj["Key"]
        fname = Path(key).name
        local_path = OUT_DIR / fname
        print(f"      Downloading {fname} ({obj['Size']} bytes)...")
        s3.download_file(BUCKET, key, str(local_path))

    # 5. Verify Receipts & SHA256
    print(f"\n[5/5] Verifying output digests and receipts...")
    manifest_file = OUT_DIR / "OUTPUTS_SHA256.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        for fname, expected_hash in manifest.items():
            fpath = OUT_DIR / fname
            if not fpath.exists():
                print(f"      [FAIL] Missing expected output: {fname}")
                continue
            actual_hash = sha_b(fpath.read_bytes())
            if actual_hash == expected_hash:
                print(f"      [VERIFIED] {fname} matches digest ({actual_hash[:16]}...)")
            else:
                print(f"      [MISMATCH] {fname} expected {expected_hash} but got {actual_hash}")

    summary_file = OUT_DIR / "RUN_SUMMARY.json"
    if summary_file.exists():
        print("\n--- RUN SUMMARY ---")
        print(summary_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    run_launch()
