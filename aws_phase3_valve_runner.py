"""Package, run, verify, and clean up the Phase 3 fixture suite on AWS."""
from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import boto3
from botocore.config import Config

REGION = "us-west-2"
BUCKET = "cas-harness-runpod-92754088"
AMI = "ami-0dddfa1ffa6b87af7"
SUBNET = "subnet-02deacfa16bdaa4f4"
SG = "sg-0562c483e0364cdab"
PROFILE = "cas-aws-gpu-standby-v1-us-west-2"
INSTANCE_TYPE = "t3.small"
MAX_RUNTIME_SECONDS = 600
DRIVER_TIMEOUT_SECONDS = 300
COST_LIMIT_USD = "0.50"
ON_DEMAND_RATE_USD_PER_HOUR = "0.0208000000"
MAX_COMPUTE_CHARGE_USD_EXACT = "13/3750"
ROOT_VOLUME_GIB = 60

HERE = Path(__file__).resolve().parent
CODEX_DATA = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\lacunarity_e1\data")
CODEX_GUARD = Path(r"C:\Users\wakil\Documents\Codex\2026-10-23\cs_aws\guard")
S3 = boto3.client("s3", region_name=REGION, config=Config(retries={"max_attempts": 5}))
EC2 = boto3.client("ec2", region_name=REGION, config=Config(retries={"max_attempts": 5}))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_payload(run_id: str, build_dir: Path) -> Path:
    if build_dir.exists():
        raise FileExistsError(f"Refusing to reuse a build folder: {build_dir}")
    pkg = build_dir / "pkg"
    pkg.mkdir(parents=True)
    sources = {
        "aws_phase3_driver.py": HERE / "aws_phase3_driver.py",
        "gen_A4-s1_baseline.jsonl": CODEX_GUARD / "gen_A4-s1_baseline.jsonl",
        "gen_A4-s1_steered_d0.2.jsonl": CODEX_GUARD / "gen_A4-s1_steered_d0.2.jsonl",
        "mouth_exam.jsonl": CODEX_DATA / "mouth_exam.jsonl",
        "test_phase3_valve_ctt_acceptance.py": HERE / "test_phase3_valve_ctt_acceptance.py",
        "tks_meta_valve_controller.py": HERE / "tks_meta_valve_controller.py",
        "tks_meta_valve_weights_v0_4.json": HERE / "tks_meta_valve_weights_v0_4.json",
    }
    for name, source in sources.items():
        if not source.is_file():
            raise FileNotFoundError(f"Required AWS input is missing: {source}")
        shutil.copy2(source, pkg / name)
    manifest = {
        "schema": "phase3-valve-aws-job/v2",
        "run_id": run_id,
        "purpose": "Run the bounded G-ABSENT fixture acceptance suite and recompute every receipt on AWS.",
        "source": {
            "project": str(HERE),
            "git_commit": "unavailable: working tree is uncommitted",
            "data": [str(CODEX_DATA / "mouth_exam.jsonl"), str(CODEX_GUARD / "gen_A4-s1_baseline.jsonl"), str(CODEX_GUARD / "gen_A4-s1_steered_d0.2.jsonl")],
        },
        "aws": {
            "region": REGION,
            "instance_type": INSTANCE_TYPE,
            "vcpus": 2,
            "memory_gib": 2,
            "root_volume_gib": ROOT_VOLUME_GIB,
            "root_volume_type": "gp3",
            "max_runtime_seconds": MAX_RUNTIME_SECONDS,
            "driver_timeout_seconds": DRIVER_TIMEOUT_SECONDS,
            "on_demand_rate_usd_per_hour": ON_DEMAND_RATE_USD_PER_HOUR,
            "max_compute_charge_at_runtime_limit_usd_exact": MAX_COMPUTE_CHARGE_USD_EXACT,
            "pricing_source": "AWS Pricing API, AmazonEC2, Linux OnDemand, us-west-2, effective 2026-10-01; price list version 20261023221355.",
            "instance_cost_limit_usd": COST_LIMIT_USD,
            "cost_scope": "EC2 compute and temporary root-volume use; retained S3 audit storage is outside this cap.",
            "cleanup": "Terminate the instance at completion or timeout; delete the root volume on termination; retain S3 input, logs, and results for audit.",
        },
        "files": [
            {"file": name, "size_bytes": (pkg / name).stat().st_size, "sha256": sha256(pkg / name)}
            for name in sorted(sources)
        ],
    }
    manifest_path = pkg / "input_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    archive = build_dir / "input.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(pkg.iterdir()):
            tar.add(path, arcname=path.name)
    return archive


def make_user_data(prefix: str, run_id: str) -> str:
    return f"""#!/bin/bash
set -u
exec > /var/log/phase3_valve.log 2>&1
B='{BUCKET}'; P='{prefix}'; export AWS_DEFAULT_REGION='{REGION}' AWS_PAGER=
mkdir -p /opt/phase3
cd /opt/phase3 || exit 100
RUN_RC=101
if aws s3 cp "s3://$B/${{P}}input.tar.gz" input.tar.gz && tar xzf input.tar.gz; then
  export PHASE3_RUN_ID='{run_id}'
  export PHASE3_S3_PREFIX='s3://{BUCKET}/{prefix}'
  export PHASE3_INSTANCE_TYPE='{INSTANCE_TYPE}'
  timeout -k 10 {DRIVER_TIMEOUT_SECONDS} /usr/bin/python3 -X utf8 aws_phase3_driver.py > driver.log 2>&1
  RUN_RC=$?
else
  printf 'Input download or extraction failed.\\n' > driver.log
fi
printf '%s\\n' "$RUN_RC" > exit.txt
if [ -f phase3_valve_acceptance_results.json ]; then aws s3 cp phase3_valve_acceptance_results.json "s3://$B/${{P}}results/phase3_valve_acceptance_results.json" || true; fi
if [ -f test_log.txt ]; then aws s3 cp test_log.txt "s3://$B/${{P}}results/test_log.txt" || true; fi
if [ -f driver.log ]; then aws s3 cp driver.log "s3://$B/${{P}}results/driver.log" || true; fi
aws s3 cp exit.txt "s3://$B/${{P}}results/exit.txt" || true
shutdown -h now
"""


def download_result(key: str, target: Path) -> dict:
    S3.download_file(BUCKET, key, str(target))
    return {"key": key, "size_bytes": target.stat().st_size, "sha256": sha256(target)}


def main() -> int:
    run_id = time.strftime("phase3-valve-v2-%Y%m%d-%H%M%S", time.gmtime()) + "-" + uuid4().hex[:8]
    prefix = f"bridge-control-20260822/{run_id}/"
    temp_root = Path(tempfile.gettempdir()).resolve()
    build_dir = temp_root / f"codex-{run_id}"
    instance_id: Optional[str] = None
    receipt_path: Optional[Path] = None
    termination_confirmed = False
    started = time.perf_counter()
    utc_started = datetime.now(timezone.utc).isoformat()
    print(f"AWS Phase 3 acceptance run: {run_id}")
    print(f"Instance: {INSTANCE_TYPE} in {REGION}; 2 vCPU; 2 GiB memory; {ROOT_VOLUME_GIB} GiB gp3 root volume")
    print(f"Limits: {MAX_RUNTIME_SECONDS} seconds maximum; EC2 spend ceiling ${COST_LIMIT_USD} USD")
    print("Cleanup: terminate on completion or timeout; delete root disk; retain S3 evidence.")

    try:
        archive = build_payload(run_id, build_dir)
        archive_sha = sha256(archive)
        manifest_path = build_dir / "pkg" / "input_manifest.json"
        prefix_key = prefix + "input.tar.gz"
        S3.upload_file(str(archive), BUCKET, prefix_key)
        print(f"Uploaded input archive SHA-256: {archive_sha}")

        launched = EC2.run_instances(
            ImageId=AMI,
            InstanceType=INSTANCE_TYPE,
            MinCount=1,
            MaxCount=1,
            SubnetId=SUBNET,
            SecurityGroupIds=[SG],
            IamInstanceProfile={"Name": PROFILE},
            UserData=make_user_data(prefix, run_id),
            InstanceInitiatedShutdownBehavior="terminate",
            BlockDeviceMappings=[{
                "DeviceName": "/dev/xvda",
                "Ebs": {"VolumeSize": ROOT_VOLUME_GIB, "VolumeType": "gp3", "DeleteOnTermination": True},
            }],
            TagSpecifications=[{
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": run_id},
                    {"Key": "Purpose", "Value": "Phase3ValveFixtureAcceptance"},
                    {"Key": "RunId", "Value": run_id},
                    {"Key": "CostLimitUSD", "Value": COST_LIMIT_USD},
                ],
            }],
        )
        instance_id = launched["Instances"][0]["InstanceId"]
        print(f"Launched AWS instance: {instance_id}")

        deadline = time.monotonic() + MAX_RUNTIME_SECONDS
        result_found = False
        while time.monotonic() < deadline:
            try:
                objects = S3.list_objects_v2(Bucket=BUCKET, Prefix=prefix + "results/").get("Contents", [])
                if any(obj["Key"] == prefix + "results/exit.txt" for obj in objects):
                    result_found = True
                    break
            except Exception as exc:
                print(f"S3 status check failed; retrying: {type(exc).__name__}")
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(10, remaining))

        results_dir = HERE / "docs" / "working" / "ctt_lacunarity_v1" / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        downloaded = {}
        outputs = (
            ("phase3_valve_acceptance_results.json", "phase3_valve_acceptance_results_v2.json"),
            ("test_log.txt", "phase3_valve_test_log_v2.txt"),
            ("driver.log", "phase3_valve_driver_log_v2.txt"),
            ("exit.txt", "phase3_valve_exit_v2.txt"),
        )
        for remote_name, local_name in outputs:
            try:
                downloaded[remote_name] = download_result(prefix + "results/" + remote_name, results_dir / local_name)
            except Exception as exc:
                print(f"Could not download {remote_name}: {type(exc).__name__}")

        shutil.copy2(manifest_path, results_dir / "phase3_valve_input_manifest_v2.json")
        cloud_receipt = {
            "schema": "phase3-valve-cloud-run-receipt/v1",
            "run_id": run_id,
            "aws_instance_id": instance_id,
            "region": REGION,
            "instance_type": INSTANCE_TYPE,
            "vcpus": 2,
            "memory_gib": 2,
            "root_volume_gib": ROOT_VOLUME_GIB,
            "max_runtime_seconds": MAX_RUNTIME_SECONDS,
            "driver_timeout_seconds": DRIVER_TIMEOUT_SECONDS,
            "on_demand_rate_usd_per_hour": ON_DEMAND_RATE_USD_PER_HOUR,
            "max_compute_charge_at_runtime_limit_usd_exact": MAX_COMPUTE_CHARGE_USD_EXACT,
            "pricing_source": "AWS Pricing API, AmazonEC2, Linux OnDemand, us-west-2, effective 2026-10-01; price list version 20261023221355.",
            "instance_cost_limit_usd": COST_LIMIT_USD,
            "cost_scope": "EC2 compute and temporary root-volume use; retained S3 audit storage is outside this cap.",
            "actual_billed_cost_usd": "unavailable from EC2 run receipts",
            "utc_started": utc_started,
            "elapsed_seconds": time.perf_counter() - started,
            "runner_observed_exit_object": result_found,
            "s3_prefix": f"s3://{BUCKET}/{prefix}",
            "input_archive": {"key": prefix_key, "size_bytes": archive.stat().st_size, "sha256": archive_sha},
            "downloaded_results": downloaded,
            "cleanup": "Termination requested by the runner; shutdown behavior is terminate; root volume DeleteOnTermination=true; S3 evidence retained.",
        }
        receipt_path = results_dir / "phase3_valve_cloud_receipt_v2.json"
        receipt_path.write_text(json.dumps(cloud_receipt, indent=2) + "\n", encoding="utf-8")

        if not result_found:
            print(f"Timed out after {MAX_RUNTIME_SECONDS} seconds; instance termination requested.")
            return 1
        exit_path = results_dir / "phase3_valve_exit_v2.txt"
        if not exit_path.is_file() or exit_path.read_text(encoding="utf-8").strip() != "0":
            print("AWS driver did not return exit code 0; inspect the saved AWS logs.")
            return 1
        result_path = results_dir / "phase3_valve_acceptance_results_v2.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not result.get("acceptance_tests_passed"):
            print("AWS result does not confirm the acceptance tests passed.")
            return 1
        print(f"AWS result saved to {result_path}")
        print(f"Cloud receipt saved to {receipt_path}")
        print(json.dumps(result.get("summary", {}), indent=2, ensure_ascii=False))
        return 0
    finally:
        if instance_id:
            try:
                EC2.terminate_instances(InstanceIds=[instance_id])
                print(f"Termination requested for {instance_id}")
                EC2.get_waiter("instance_terminated").wait(
                    InstanceIds=[instance_id],
                    WaiterConfig={"Delay": 5, "MaxAttempts": 24},
                )
                termination_confirmed = True
                print(f"Confirmed AWS instance terminated: {instance_id}")
            except Exception as exc:
                print(f"Termination request failed: {type(exc).__name__}; check instance {instance_id}")
        if receipt_path and receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["termination_confirmed"] = termination_confirmed
            receipt["utc_cleanup_completed"] = datetime.now(timezone.utc).isoformat()
            if termination_confirmed:
                receipt["cleanup"] = "Instance termination confirmed; root volume DeleteOnTermination=true; S3 evidence retained."
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if build_dir.exists():
            resolved = build_dir.resolve()
            if resolved.parent == temp_root and resolved.name == f"codex-{run_id}":
                shutil.rmtree(resolved)
            else:
                print(f"Kept unexpected build folder for safety: {resolved}")


if __name__ == "__main__":
    raise SystemExit(main())
