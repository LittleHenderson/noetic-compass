"""Read-only AWS progress snapshot. Not a completed learning/audit receipt."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parent
JOB = "cas-meta2-20260906002616-34a51f16"
INSTANCE = "i-0ce0176a017bbfced"
BUCKET = JOB + "-807562639912"


def main():
    launch = json.loads((ROOT / "launch_receipt.json").read_bytes())
    assert launch["resources"]["instance"] == INSTANCE
    assert launch["resources"]["bucket"] == BUCKET
    cfg = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 0})
    session = boto3.Session(profile_name="default", region_name="us-west-2")
    response = session.client("s3", config=cfg).get_object(
        Bucket=BUCKET, Key="results/bootstrap.log", Range="bytes=0-65535")
    raw = response["Body"].read(65537)
    assert 0 < len(raw) <= 65536
    rows = []
    for line in raw.decode("utf-8", "replace").splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    progress = [r for r in rows if r.get("stage") == "paired_training"]
    measured = [r for r in progress if r.get("cas_generated_validation")]
    provider = session.client("ec2", config=cfg).describe_instances(InstanceIds=[INSTANCE])
    instance = provider["Reservations"][0]["Instances"][0]
    now = datetime.now(timezone.utc)
    destination = ROOT / "live_snapshots" / now.strftime("%Y%m%dT%H%M%S%fZ")
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "bootstrap.log").write_bytes(raw)
    receipt = {"schema": "cas-meta2-live-observation/0.1", "job": JOB,
        "observed_utc": now.isoformat(), "source_sha": "ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70",
        "instance_id": INSTANCE, "instance_state": instance["State"]["Name"],
        "instance_type": instance["InstanceType"],
        "ec2_request_id": provider["ResponseMetadata"]["RequestId"],
        "s3_request_id": response["ResponseMetadata"]["RequestId"],
        "log_last_modified": response["LastModified"].isoformat(),
        "log_sha256": sha256(raw).hexdigest(), "log_bytes": len(raw),
        "latest_training_epoch": progress[-1]["epoch"] if progress else None,
        "latest_development_measurement": measured[-1] if measured else None,
        "recent_nontraining_events": [r for r in rows if r.get("stage") and r.get("stage") != "paired_training"][-8:],
        "completed_run_verified": False, "learning_accepted": False,
        "boundary": "Read-only live provider/log observation. Not a final held-out outcome, complete packet audit or cleanup receipt."}
    (destination / "observation.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"snapshot": str(destination), "instance_state": receipt["instance_state"],
        "latest_training_epoch": receipt["latest_training_epoch"],
        "recent_nontraining_events": receipt["recent_nontraining_events"]}, indent=2))


if __name__ == "__main__":
    main()
