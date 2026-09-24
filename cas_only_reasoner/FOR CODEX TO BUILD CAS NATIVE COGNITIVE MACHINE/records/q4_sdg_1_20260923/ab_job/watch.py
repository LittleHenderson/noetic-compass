"""Watch the Q4-SDG-1 A-versus-B T4 machine and hold the client-side kill switch: terminate it at the client deadline.

Reads `launch_record.json`. Every 30 seconds: the machine's state, and whether the results object exists.
  * results present  -> make sure the machine is gone, download the results to `results/`, unpacking NESTED folders
                        safely (safe_members: regular files only, under out/, at most MAX_DEPTH simple-name parts, no
                        '..', no absolute path, no link, no eval/sealed name, size caps; every target path is checked
                        to stay inside results/); exit 0 if the job's STATUS is "done", else 5
  * machine gone and no results -> keep the last progress log if there is one, exit 3
  * client deadline reached     -> TERMINATE the machine (retrying until AWS confirms), exit 4
It only ever touches the ONE instance id in the launch record. A network error never stops the watch. It ends by
writing `watch_record.json` with the measured run time and cost bound.
"""
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
SAFE_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
FORBIDDEN = re.compile(r"(_eval\.jsonl$|sealed|hset1a|hset1b)", re.IGNORECASE)
MAX_DEPTH = 6                       # out/ab/runs/<run>/checkpoint/<file> is 5 parts deep
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024


def utc():
    return datetime.datetime.now(datetime.timezone.utc)


def safe_members(tar):
    """(member, relative parts) for every archive member that may be written; everything else is listed as skipped.

A member is written only if: it is a regular file; its name is out/<p1>/.../<pk> with 1 <= k <= MAX_DEPTH; every
part is a simple name (letters, digits, '.', '_', '-'; not starting with '.'; so no '..', no absolute path, no drive,
no backslash); the name has no eval/sealed/hset1a/hset1b part; it is at most MAX_MEMBER_BYTES; the running total stays
under MAX_TOTAL_BYTES.
"""
    keep, skipped, total = [], [], 0
    for member in tar.getmembers():
        parts = member.name.split("/")
        ok = (member.isfile() and len(parts) >= 2 and parts[0] == "out" and len(parts) - 1 <= MAX_DEPTH
              and all(SAFE_PART.match(p) for p in parts[1:]) and not FORBIDDEN.search(member.name)
              and 0 <= member.size <= MAX_MEMBER_BYTES and total + member.size <= MAX_TOTAL_BYTES)
        if ok:
            keep.append((member, parts[1:]))
            total += member.size
        elif not member.isdir():
            skipped.append(member.name)
    return keep, skipped


def extract(body, out):
    out = pathlib.Path(out)
    out.mkdir(exist_ok=True)
    root, written = out.resolve(), 0
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:gz") as tar:
        keep, skipped = safe_members(tar)
        for member, parts in keep:                  # never extractall: plain bytes into checked paths only
            target = out.joinpath(*parts)
            if not target.resolve().is_relative_to(root):
                skipped.append(member.name)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
            written += 1
    for name in skipped:
        print("  skipped archive member %r" % name, flush=True)
    return written, skipped


def main():
    import boto3
    import botocore.exceptions as bx
    errors = (bx.ClientError, bx.BotoCoreError)
    record = json.loads((HERE / "launch_record.json").read_text(encoding="utf-8"))
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
        for attempt in range(40):
            try:
                ec2.terminate_instances(InstanceIds=[iid])
            except errors as error:
                print("  terminate attempt %d failed: %s" % (attempt + 1, type(error).__name__), flush=True)
            if state() in GONE:
                return True
            time.sleep(30)
        print("MACHINE MAY STILL BE RUNNING: %s in %s -- terminate it by hand in the EC2 console" % (iid, region), flush=True)
        return False

    try:
        ec2.terminate_instances(InstanceIds=[iid], DryRun=True)
    except bx.ClientError as error:
        allowed = error.response["Error"]["Code"] == "DryRunOperation"
        print("permission to terminate %s: %s" % (iid, "yes" if allowed else "NO (%s) -- only the machine's own timers bound it" % error.response["Error"]["Code"]), flush=True)
    except bx.BotoCoreError:
        print("permission check skipped: network error", flush=True)

    outcome, last_state, last_beat = None, None, 0.0
    while outcome is None:
        now, st = utc(), state()
        if st != last_state:
            print("%s  machine %s: %s" % (now.strftime("%H:%M:%S"), iid, st), flush=True)
            last_state = st
        if exists(keys["results"]):
            outcome = "RESULTS_RECEIVED"
        elif st in GONE or st == "stopped":
            for _ in range(12):
                if exists(keys["results"]):
                    break
                time.sleep(10)
            outcome = "RESULTS_RECEIVED" if exists(keys["results"]) else "MACHINE_ENDED_WITHOUT_RESULTS"
        elif now >= deadline:
            terminate("client deadline of %d minutes reached" % record["client_deadline_minutes"])
            for _ in range(18):
                if exists(keys["results"]):
                    break
                time.sleep(10)
            outcome = "CLIENT_DEADLINE_TERMINATED_RESULTS_RECEIVED" if exists(keys["results"]) else "CLIENT_DEADLINE_TERMINATED"
        else:
            if time.time() - last_beat > 300:
                print("%s  still running, %d min since launch" % (now.strftime("%H:%M:%S"), (now - launched).total_seconds() // 60), flush=True)
                last_beat = time.time()
            time.sleep(30)

    for _ in range(12):
        if state() in GONE:
            break
        time.sleep(10)
    else:
        terminate("still up after the run ended")

    out, job_status, downloaded = HERE / "results", None, 0
    try:
        if outcome in ("RESULTS_RECEIVED", "CLIENT_DEADLINE_TERMINATED_RESULTS_RECEIVED"):
            body = s3.get_object(Bucket=bucket, Key=keys["results"])["Body"].read()
            out.mkdir(exist_ok=True)
            (out / "results.tar.gz").write_bytes(body)
            downloaded, _ = extract(body, out)
            status_file = out / "STATUS"
            job_status = status_file.read_text(encoding="utf-8").strip() if status_file.is_file() else None
            print("results downloaded: %d files; the job's own status: %s" % (downloaded, job_status), flush=True)
        if exists(keys["progress"]):
            out.mkdir(exist_ok=True)
            (out / "progress.log").write_bytes(s3.get_object(Bucket=bucket, Key=keys["progress"])["Body"].read())
    except Exception as error:                               # a bad download must not hide the final state below
        print("download problem: %s: %s" % (type(error).__name__, str(error)[:160]), flush=True)

    for _ in range(40):
        if state() in ("terminated", "gone"):
            break
        time.sleep(15)
    try:
        left = ec2.describe_volumes(Filters=[{"Name": "tag:Name", "Values": [record["instance_name"]]}])["Volumes"]
        volumes_left = [(v["VolumeId"], v["State"]) for v in left]
    except errors as error:
        volumes_left = "unknown:%s" % type(error).__name__
    end_state, ended = state(), utc()
    minutes = (ended - launched).total_seconds() / 60.0
    per_hour = record["approved"]["price_per_hour_usd"] + 0.005 + record["root_volume_gb"] * 0.08 / 730
    watch = {"schema": "claude.q4-sdg-1-ab-watch/0.2", "instance_id": iid, "outcome": outcome, "job_status": job_status,
             "final_state": end_state, "files_downloaded": downloaded, "launched_utc": record["launched_utc"],
             "watch_ended_utc": ended.strftime("%Y-%m-%dT%H:%M:%SZ"), "minutes_from_launch_to_watch_end": round(minutes, 1),
             "cost_upper_bound_usd": round(minutes / 60.0 * per_hour, 4),
             "data_build_cost_upper_bound_usd": record.get("data_build_cost_upper_bound_usd"),
             "whole_ab_job_cost_upper_bound_usd": round(minutes / 60.0 * per_hour
                                                        + (record.get("data_build_cost_upper_bound_usd") or 0.0), 4),
             "cost_note": "upper bound: billed time ends at shutdown, before the watch ended; includes the public address and the gp3 disk",
             "terminated_confirmed": end_state in ("terminated", "gone"), "volumes_of_this_job_remaining": volumes_left,
             "dollar_ceiling_whole_ab_job": record["approved"]["dollar_ceiling_whole_ab_job"]}
    (HERE / "watch_record.json").write_text(json.dumps(watch, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(watch), flush=True)
    if end_state not in GONE:
        print("MACHINE NOT CONFIRMED GONE: %s is %s" % (iid, end_state), flush=True)
        return 6
    if outcome in ("RESULTS_RECEIVED", "CLIENT_DEADLINE_TERMINATED_RESULTS_RECEIVED"):
        return 0 if job_status == "done" and outcome == "RESULTS_RECEIVED" else 5
    return {"MACHINE_ENDED_WITHOUT_RESULTS": 3, "CLIENT_DEADLINE_TERMINATED": 4}[outcome]


if __name__ == "__main__":
    sys.exit(main())
