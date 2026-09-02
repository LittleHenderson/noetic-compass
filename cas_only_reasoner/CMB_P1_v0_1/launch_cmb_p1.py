"""CMB-P1 AWS GPU launcher -- one instance, self-terminating, hard cost cap.

Run with the boto3-bearing venv:
    ~/venvs/cas-gpu/Scripts/python.exe launch_cmb_p1.py

Compute law (owner): one remote AWS GPU instance; all substantive numerical operations on
CUDA; fail closed on silent CPU fallback; local CPU is not used for the workload.

Four independent stops, so a hung run cannot bill indefinitely:
  1. InstanceInitiatedShutdownBehavior = terminate
  2. EXIT trap in user-data  -> shutdown -h now on any exit path, including failure
  3. in-instance hard timer  -> shutdown regardless of what the harness is doing
  4. client watchdog here    -> force TerminateInstances at the cap
"""
import hashlib
import json
import os
import sys
import time

import boto3

REGION = "us-west-2"
INSTANCE_TYPE = "g4dn.xlarge"          # Tesla T4, 4 vCPU (G-quota in us-west-2 is 8)
AMI = "ami-0c779ec711a581954"          # Deep Learning Base OSS Nvidia Driver, Ubuntu 22.04
PROFILE = "cas-aws-gpu-standby-v1-us-west-2"
BUCKET = "cas-harness-runpod-92754088"
# The instance role (cas-aws-gpu-standby-v1-us-west-2) grants s3:GetObject/PutObject ONLY
# under this prefix. Writing anywhere else in the bucket is DENIED -- verified before
# launch, not assumed. Do not "tidy" this to a cmb_p1/ top-level prefix without an IAM
# change, which is the owner's to make, not mine.
PREFIX = "bridge-control-20260822/cmb_p1"
RATE_PER_HOUR = 0.526

HARD_CAP_USD = 0.80
CAP_MIN = HARD_CAP_USD / RATE_PER_HOUR * 60          # 91.3 min of billable runtime
IN_INSTANCE_HARD_MIN = 60                            # stop 3
WATCHDOG_MIN = 65                                    # stop 4
RUN_ID = None                                        # set from argv or clock at launch
FILES = ("cmb_p1.py", "run_cmb_p1.py", "../CMB_P0_v0_1/cmb_p0.py")


def payload():
    """The harness source, as {filename: text}, staged to S3 (too large for user-data).

    Read by ABSOLUTE path and hashed, so the run is tied to the exact reviewed bytes.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    blob, digests = {}, {}
    for f in FILES:
        with open(os.path.join(here, f), "r", encoding="utf-8") as fh:
            blob[os.path.basename(f)] = fh.read()
        digests[os.path.basename(f)] = hashlib.sha256(blob[os.path.basename(f)].encode()).hexdigest()
    return json.dumps(blob), digests


def user_data(run_id):
    """Harness is staged through S3 -- gzip+base64 in user-data exceeded the 16 KB cap."""
    return f"""#!/bin/bash
exec > >(tee -a /var/log/cmbp1.log) 2>&1
trap 'aws s3 cp /var/log/cmbp1.log s3://{BUCKET}/{PREFIX}/{run_id}/console.log --region {REGION} || true; shutdown -h now' EXIT
( sleep {IN_INSTANCE_HARD_MIN * 60}; echo "IN_INSTANCE_HARD_TIMER"; shutdown -h now ) &

set -x
mkdir -p /opt/cmbp1 && cd /opt/cmbp1
aws s3 cp s3://{BUCKET}/{PREFIX}/{run_id}/harness.json /opt/cmbp1/harness.json --region {REGION}
python3 - <<'PYEOF'
import json
blob = json.load(open("/opt/cmbp1/harness.json"))
for name, text in blob.items():
    open("/opt/cmbp1/" + name, "w").write(text)
print("UNPACKED", list(blob))
PYEOF

nvidia-smi || true
python3 -m pip install --upgrade pip --break-system-packages 2>/dev/null || python3 -m pip install --upgrade pip
python3 -m pip install torch --index-url https://download.pytorch.org/whl/cu124 --break-system-packages 2>/dev/null || python3 -m pip install torch --index-url https://download.pytorch.org/whl/cu124
# Fail loudly RIGHT HERE if torch is missing or CPU-only. Without this the script would
# continue to a run that dies on `import torch`, after paying for boot and the download.
python3 -c "import torch,sys;print('TORCH',torch.__version__,'CUDA',torch.cuda.is_available());sys.exit(0 if torch.cuda.is_available() else 1)"
if [ $? -ne 0 ]; then echo "TORCH_OR_CUDA_UNAVAILABLE"; exit 1; fi

cd /opt/cmbp1 && python3 run_cmb_p1.py; RC=$?
echo "HARNESS_RC=$RC"
for f in CMB_P1_RECEIPT.json CMB_P1_RAW.json; do
  aws s3 cp /opt/cmbp1/$f s3://{BUCKET}/{PREFIX}/{run_id}/$f --region {REGION} || true
done
echo "DONE"
"""


def main():
    global RUN_ID
    RUN_ID = f"cmb-p1-{int(time.time())}"
    harness, digests = payload()
    ud = user_data(RUN_ID)
    print(f"run_id={RUN_ID}  user_data={len(ud)} bytes (EC2 limit 16384)  "
          f"harness={len(harness)} bytes -> S3")
    for f, d in digests.items():
        print(f"  staged {f}  sha256 {d[:32]}")
    if len(ud) > 16384:
        sys.exit("USER_DATA_TOO_LARGE")
    if "--dry-run" in sys.argv:
        print("DRY RUN -- nothing launched, $0 spent.")
        return 0

    s = boto3.Session(region_name=REGION)
    ec2 = s.client("ec2")
    s.client("s3").put_object(Bucket=BUCKET, Key=f"{PREFIX}/{RUN_ID}/harness.json",
                              Body=harness.encode())
    print(f"staged harness -> s3://{BUCKET}/{PREFIX}/{RUN_ID}/harness.json")
    r = ec2.run_instances(
        ImageId=AMI, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1,
        IamInstanceProfile={"Name": PROFILE},
        InstanceInitiatedShutdownBehavior="terminate",          # stop 1
        UserData=ud,
        BlockDeviceMappings=[{"DeviceName": "/dev/sda1",
                              "Ebs": {"VolumeSize": 120, "DeleteOnTermination": True,
                                      "VolumeType": "gp3"}}],
        TagSpecifications=[{"ResourceType": "instance",
                            "Tags": [{"Key": "Name", "Value": RUN_ID},
                                     {"Key": "project", "Value": "CMB-P1"}]}],
    )
    iid = r["Instances"][0]["InstanceId"]
    t0 = time.time()
    print(f"launched {iid}  cap={WATCHDOG_MIN} min  hard_cap=${HARD_CAP_USD}")

    s3 = s.client("s3")
    key = f"{PREFIX}/{RUN_ID}/CMB_P1_RECEIPT.json"
    got = False
    while True:
        el = (time.time() - t0) / 60.0
        try:
            st = ec2.describe_instances(InstanceIds=[iid])[
                "Reservations"][0]["Instances"][0]["State"]["Name"]
        except Exception:
            st = "unknown"
        try:
            s3.head_object(Bucket=BUCKET, Key=key)
            got = True
        except Exception:
            pass
        print(f"  [{el:5.1f}m] state={st} receipt={'YES' if got else 'no'} "
              f"est=${el / 60 * RATE_PER_HOUR:.4f}", flush=True)
        if got or st in ("terminated", "shutting-down"):
            break
        if el > WATCHDOG_MIN:                                    # stop 4
            print("WATCHDOG: force terminate")
            ec2.terminate_instances(InstanceIds=[iid])
            break
        time.sleep(20)

    for name in ("CMB_P1_RECEIPT.json", "console.log"):
        try:
            s3.download_file(BUCKET, f"{PREFIX}/{RUN_ID}/{name}", name)
            print("downloaded", name)
        except Exception as e:
            print("could not download", name, type(e).__name__)
    if not got:
        # No receipt: recover the console output so a failed run still yields a diagnosis
        # rather than nothing at all.
        try:
            out = ec2.get_console_output(InstanceId=iid).get("Output", "")
            open("CMB_P1_CONSOLE_FALLBACK.log", "w", encoding="utf-8").write(out or "")
            print(f"no receipt; wrote {len(out or '')} bytes of console output to "
                  "CMB_P1_CONSOLE_FALLBACK.log")
        except Exception as e:
            print("console fallback failed:", type(e).__name__)
    try:
        ec2.terminate_instances(InstanceIds=[iid])
    except Exception:
        pass
    el = (time.time() - t0) / 60.0
    json.dump({"receipt_id": "CLOUD_EXECUTION_RECEIPT_CMB_P1", "run_id": RUN_ID,
               "instance_id": iid, "instance_type": INSTANCE_TYPE, "region": REGION,
               "ami": AMI, "gpu": "NVIDIA Tesla T4", "account": "807562639912",
               "wall_minutes_instance": round(el, 2),
               "cost": {"authoritative_method": "instance_runtime_estimate",
                        "instance_runtime_estimate_usd": round(el / 60 * RATE_PER_HOUR, 4),
                        "rate_per_hour_usd": RATE_PER_HOUR,
                        "note": "the harness compute wall is a LOWER BOUND and is never "
                                "presented as the spend; methods are not mixed"},
               "budget": {"hard_cap_usd": HARD_CAP_USD,
                          "cap_minutes": round(CAP_MIN, 1),
                          "in_instance_hard_timer_min": IN_INSTANCE_HARD_MIN,
                          "watchdog_force_terminate_min": WATCHDOG_MIN},
               "termination": "self-terminated (InstanceInitiatedShutdownBehavior=terminate "
                              "+ EXIT-trap + in-instance timer); client watchdog armed",
               "receipt_retrieved": got,
               "staged_sha256": digests,
               "torch_wheel": "cu124 index, version NOT pinned; the resolved version is recorded in the receipt compute block. Determinism is same-instance.",},
              open("CLOUD_EXECUTION_RECEIPT_CMB_P1.json", "w"), indent=1, sort_keys=True)
    print(f"instance_runtime_estimate = ${el / 60 * RATE_PER_HOUR:.4f}  receipt={got}")
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
