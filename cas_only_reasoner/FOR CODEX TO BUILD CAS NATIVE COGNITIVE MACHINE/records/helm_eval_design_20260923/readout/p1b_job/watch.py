"""Watch the P1b machine and hold the client-side kill switch: terminate it from here at the client deadline (62 min).
Copied from ../gates_job/watch.py (itself from T01's aws_rescore_job); one record per mode. CLAUDE_BUILT_CLAUDE_CHECKED.

    python watch.py --mode acceptance|reading

Reads `launch_record_<mode>.json`. Every 30 seconds: the machine's state, and whether the results object exists.
  * results present  -> make sure the machine is gone, download to `results_<mode>/`, exit 0 if the job's own STATUS is
                        "done", else 5
  * machine gone and no results -> keep the last progress log if there is one, exit 3
  * client deadline reached     -> TERMINATE the machine (retrying until AWS confirms), exit 4
It only ever touches the ONE instance id in the launch record. A network error never stops the watch. It ends by
writing `watch_record_<mode>.json` with the measured time and the cost bound. It refuses to overwrite an existing
results folder or watch record (old results must never pass as new ones).
"""
import argparse
import datetime
import io
import json
import pathlib
import re
import sys
import tarfile
import time

HERE = pathlib.Path(__file__).resolve().parent
GONE = ("terminated", "shutting-down", "gone")
SAFE_MEMBER = re.compile(r"^out/[A-Za-z0-9._-]+$")
HOURLY_EXTRAS = 0.005 + 75 * 0.08 / 730                  # public address + 75 GiB gp3, per hour (as launch.worst_case_usd)


def utc():
    return datetime.datetime.now(datetime.timezone.utc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("acceptance", "reading"), required=True)
    args = parser.parse_args()
    record_path = HERE / ("launch_record_%s.json" % args.mode)
    watch_path = HERE / ("watch_record_%s.json" % args.mode)
    out = HERE / ("results_%s" % args.mode)
    if watch_path.exists() or out.exists():
        print("WATCH_REFUSED: %s or %s already exists" % (watch_path.name, out.name))
        return 2
    import boto3
    import botocore.exceptions as bx
    errors = (bx.ClientError, bx.BotoCoreError)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    iid, region, bucket, keys = record["instance_id"], record["approved"]["region"], record["bucket"], record["keys"]
    launched = datetime.datetime.strptime(record["launched_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    deadline = launched + datetime.timedelta(minutes=record["client_deadline_minutes"])
    ec2, s3 = boto3.client("ec2", region_name=region), boto3.client("s3", region_name=region)

    def state():
        try:
            res = ec2.describe_instances(InstanceIds=[iid])["Reservations"]
            return res[0]["Instances"][0]["State"]["Name"] if res else "gone"
        except bx.ClientError as error:
            code = error.response["Error"]["Code"]
            return "gone" if code == "InvalidInstanceID.NotFound" else "unknown:%s" % code
        except bx.BotoCoreError:
            return "unknown:network"

    def exists(key):
        try:
            s3.head_object(Bucket=bucket, Key=key)
            return True
        except errors:
            return False

    def terminate(why):
        print("TERMINATING %s: %s" % (iid, why), flush=True)
        for attempt in range(40):                            # up to 20 minutes of retries
            try:
                ec2.terminate_instances(InstanceIds=[iid])
            except errors as error:
                print("  terminate attempt %d failed: %s" % (attempt + 1, type(error).__name__), flush=True)
            if state() in GONE:
                return True
            time.sleep(30)
        print("MACHINE MAY STILL BE RUNNING: %s in %s -- terminate it by hand in the EC2 console" % (iid, region), flush=True)
        return False

    outcome, last_state, last_beat = None, None, 0.0
    while outcome is None:
        now, st = utc(), state()
        if st != last_state:
            print("%s  machine %s: %s" % (now.strftime("%H:%M:%S"), iid, st), flush=True)
            last_state = st
        if exists(keys["results"]):
            outcome = "RESULTS_RECEIVED"
        elif st in GONE or st == "stopped":
            time.sleep(20)                                   # the upload is the machine's last act; give it a moment
            outcome = "RESULTS_RECEIVED" if exists(keys["results"]) else "MACHINE_ENDED_WITHOUT_RESULTS"
        elif now >= deadline:
            terminate("client deadline of %d minutes reached" % record["client_deadline_minutes"])
            outcome = "CLIENT_DEADLINE_TERMINATED"
        else:
            if time.time() - last_beat > 300:
                print("%s  still running, %d min since launch" % (now.strftime("%H:%M:%S"),
                                                                   (now - launched).total_seconds() // 60), flush=True)
                last_beat = time.time()
            time.sleep(30)

    for _ in range(12):                                      # FIRST make sure the machine is gone; only then fetch
        if state() in GONE:
            break
        time.sleep(10)
    else:
        terminate("still up after the run ended")

    job_status, downloaded = None, 0
    out.mkdir()
    try:
        if outcome == "RESULTS_RECEIVED":
            body = s3.get_object(Bucket=bucket, Key=keys["results"])["Body"].read()
            (out / "results.tar.gz").write_bytes(body)
            with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tar:
                for member in tar.getmembers():              # never extractall: plain files named out/<simple name> only
                    if member.isfile() and SAFE_MEMBER.match(member.name):
                        (out / member.name.split("/", 1)[1]).write_bytes(tar.extractfile(member).read())
                        downloaded += 1
                    else:
                        print("  skipped archive member %r" % member.name, flush=True)
            status_file = out / "STATUS"
            job_status = status_file.read_text(encoding="utf-8").strip() if status_file.is_file() else None
            print("results downloaded: %d files; the job's own status: %s" % (downloaded, job_status), flush=True)
        if exists(keys["progress"]):
            (out / "progress.log").write_bytes(s3.get_object(Bucket=bucket, Key=keys["progress"])["Body"].read())
    except Exception as error:                               # noqa: BLE001 - a bad download must not hide the final state
        print("download problem: %s: %s" % (type(error).__name__, str(error)[:160]), flush=True)

    end_state, ended = state(), utc()
    minutes = (ended - launched).total_seconds() / 60.0
    watch = {"schema": "claude.p1b-job-watch/0.1", "mode": args.mode, "instance_id": iid, "outcome": outcome,
             "job_status": job_status, "final_state": end_state, "files_downloaded": downloaded,
             "launched_utc": record["launched_utc"], "watch_ended_utc": ended.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "minutes_from_launch_to_watch_end": round(minutes, 1),
             "cost_upper_bound_usd": round(minutes / 60.0 * (record["approved"]["price_per_hour_usd"] + HOURLY_EXTRAS), 4),
             "cost_note": "upper bound: machine + public address + 75 GiB gp3 for the whole time from launch to the end "
                          "of the watch. The $0.10 allowance is added in the ledger.",
             "dollar_ceiling": record["approved"]["dollar_ceiling"]}
    watch_path.write_text(json.dumps(watch, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(watch), flush=True)
    if end_state not in GONE:
        print("MACHINE NOT CONFIRMED GONE: %s is %s" % (iid, end_state), flush=True)
        return 6
    if outcome == "RESULTS_RECEIVED":
        return 0 if job_status == "done" else 5
    return {"MACHINE_ENDED_WITHOUT_RESULTS": 3, "CLIENT_DEADLINE_TERMINATED": 4}[outcome]


if __name__ == "__main__":
    sys.exit(main())
