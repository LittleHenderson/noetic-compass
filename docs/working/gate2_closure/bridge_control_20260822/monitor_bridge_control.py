# -*- coding: utf-8 -*-
import boto3, json, pathlib, time, datetime, sys
SP = pathlib.Path(__file__).resolve().parent
s = boto3.Session(region_name="us-west-2")
ec2, s3 = s.client("ec2"), s.client("s3")
BUCKET, PREFIX = "cas-harness-runpod-92754088", "bridge-control-20260822"
st = json.loads((SP / "launch_state.json").read_text())
iid, t0 = st["instance_id"], st["launched_at"]
DEADLINE = t0 + 150 * 60
def state():
    r = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]
    return r["State"]["Name"]
def log_tail():
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=f"{PREFIX}/logs/job.log")
        return obj["Body"].read().decode(errors="replace")[-1500:]
    except Exception:
        return None
print("monitor start", iid, flush=True)
while True:
    now = time.time()
    st_ = state()
    log = log_tail()
    print(f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%SZ')}] state={st_}", flush=True)
    if log:
        print(log, flush=True)
    if st_ == "terminated":
        print("DONE: instance terminated", flush=True)
        break
    if now > DEADLINE:
        print("DEADLINE: forcing termination", flush=True)
        ec2.modify_instance_attribute(InstanceId=iid, DisableApiTermination={"Value": False})
        ec2.terminate_instances(InstanceIds=[iid])
        break
    time.sleep(60)
