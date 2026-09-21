"""Launch the owner-approved T01 re-check job on AWS. Owner approval, in chat, 2026-09-21: "yes run the AWS job".

The approved job, exactly: ONE c7i.2xlarge in us-west-2, on-demand (0.357 USD/hour, checked against the AWS
pricing API the same day), 90 minutes at most, 2.00 USD ceiling. The ceiling is enforced by TIME, three ways:
  1. the machine shuts itself down after MAX_SECONDS (85 minutes) whatever happens;
  2. the job script shuts the machine down on ANY exit (success, error, signal);
  3. `watch.py` terminates the machine from here at 95 minutes.
The machine is launched with "terminate on shutdown", so a shutdown destroys it and its disk.
1.5 hours x 0.357 = 0.54 USD, plus cents of disk and of the auto-assigned public address (0.005 USD/hour, released at
termination). Nothing that outlives the machine is created: no key pair, no role, no Elastic IP, no snapshot.
launch.py REFUSES to run twice: one approval, one machine.

The machine gets NO credentials. It can download one object (the bundle) and upload two (progress log, results)
through time-limited links. The bundle holds only the files the job reads (about 6 MB of course material and
code plus 24 prediction/scoring files), taken from a CLEAN working tree at a recorded commit.

Usage:  python launch.py --trace <load_trace.json> [--dry-run]
        --dry-run builds the bundle and the machine script and prints them, and launches NOTHING.
"""
import argparse
import datetime
import gzip
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[2]
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
INSTANCE_TYPE, PRICE_PER_HOUR = "c7i.2xlarge", 0.357
AMI_PARAMETER = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
MAX_SECONDS, CLIENT_DEADLINE_MINUTES, DOLLAR_CEILING = 85 * 60, 95, 2.00
PYTHON_VERSION = "3.14"
R = "records/typed_pointer_001/"
RECEIPTS = ["receipt_helm1_certified_20260917", "receipt_helm1_certified_20260918", "receipt_helm1_certified_20260919",
            "receipt_20260917", "receipt_20260918", "receipt_20260919"]
RECORD_FILES = [R + name for name in (
    "trusted_rescore.py", "test_trusted_rescore.py", "evaluate_gates.py", "study_helm1_certified.json",
    "admission_001/study.json", "admission_001/gate_reading.json", "admission_helm1_certified/gate_reading.json",
    "trust_anchor_helm1_certified.json", "trust_anchor_helm2_experimental_20208c92.json",
    "trusted_rescore_reading_helm1_certified.json", "trusted_rescore_reading_helm2_experimental.json")] + [
    R + "%s/collected/results/artifacts/course_%s_%s.json" % (rec, ph, kind)
    for rec in RECEIPTS for ph in ("p00", "p10") for kind in ("predictions", "scoring")]


def git(*args):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), capture_output=True, text=True, check=True).stdout.strip()


def bundle_files(trace_path):
    sys.path.insert(0, str(PACKAGE / R))
    import trusted_rescore as T
    trace = json.loads(pathlib.Path(trace_path).read_text(encoding="utf-8"))
    traced = [p for p in trace["opened"] if "__pycache__" not in p]
    files = sorted(set(traced) | set(T.CODE_CLOSURE) | set(RECORD_FILES))
    missing = [p for p in files if not (PACKAGE / p).is_file()]
    if missing:
        raise SystemExit("BUNDLE_REFUSED: files missing on disk: %s" % missing)
    return files


def build_bundle(files):
    """A deterministic tar.gz of the listed files, with text files LF-normalised (what git stores)."""
    dirty = git("status", "--porcelain", "--", *files)
    if dirty:
        raise SystemExit("BUNDLE_REFUSED: these bundle files differ from the commit:\n%s" % dirty)
    buffer = io.BytesIO()
    # mtime=0 in the gzip header too, so the same files always give the same bytes and the same sha256
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6, mtime=0) as zipped, tarfile.open(fileobj=zipped, mode="w") as tar:
        for rel in files:
            data = (PACKAGE / rel).read_bytes().replace(b"\r\n", b"\n")
            info = tarfile.TarInfo(rel)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
    body = buffer.getvalue()
    return body, hashlib.sha256(body).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import boto3

    files = bundle_files(args.trace)
    commit = git("rev-parse", "HEAD")
    body, bundle_sha = build_bundle(files)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "helm3-lab/t01-rescore-%s/" % stamp
    print("bundle: %d files, %.2f MB, sha256 %s, source commit %s" % (len(files), len(body) / 1e6, bundle_sha[:16], commit[:8]))

    s3 = boto3.client("s3", region_name=REGION)
    template = (HERE / "job.sh.template").read_text(encoding="utf-8").replace("\r\n", "\n")
    keys = {"bundle": prefix + "bundle.tar.gz", "results": prefix + "results.tar.gz", "progress": prefix + "progress.log"}
    if args.dry_run:
        urls = {k: "https://DRY-RUN/%s" % v for k, v in keys.items()}
    else:
        s3.put_object(Bucket=BUCKET, Key=keys["bundle"], Body=body)
        urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=3 * 3600),
                "results": s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys["results"]}, ExpiresIn=3 * 3600),
                "progress": s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys["progress"]}, ExpiresIn=3 * 3600)}
    script = (template.replace("__MAX_SECONDS__", str(MAX_SECONDS)).replace("__MAX_MINUTES__", str(MAX_SECONDS // 60 + 3)).replace("__BUNDLE_URL__", urls["bundle"])
              .replace("__RESULTS_URL__", urls["results"]).replace("__PROGRESS_URL__", urls["progress"])
              .replace("__BUNDLE_SHA256__", bundle_sha).replace("__SOURCE_COMMIT__", commit).replace("__PYTHON_VERSION__", PYTHON_VERSION))
    assert "__" not in script.replace("__pycache__", ""), "an unfilled placeholder remains in the machine script"
    assert len(script.encode("utf-8")) < 16000, "user-data limit"
    worst_case = PRICE_PER_HOUR * CLIENT_DEADLINE_MINUTES / 60.0
    assert worst_case < DOLLAR_CEILING, "the time limit does not keep the job under the owner's ceiling"

    if not args.dry_run and (HERE / "launch_record.json").exists():
        raise SystemExit("LAUNCH_REFUSED: launch_record.json already exists -- the owner approved ONE machine")
    if args.dry_run:
        (HERE / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded, nothing launched. Worst case at the client deadline: %.2f USD (ceiling %.2f)." % (worst_case, DOLLAR_CEILING))
        print("machine script written to dry_run_machine_script.sh (%d bytes)" % len(script.encode("utf-8")))
        return 0

    ec2 = boto3.client("ec2", region_name=REGION)
    ami = boto3.client("ssm", region_name=REGION).get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
    image = ec2.describe_images(ImageIds=[ami])["Images"][0]
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    subnet = sorted(subnets, key=lambda s: s["AvailabilityZone"])[0]
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    open_rules = [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]
    if open_rules:
        raise SystemExit("LAUNCH_REFUSED: the default security group allows inbound traffic from an address range: %s" % open_rules)
    running = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["helm3-t01-rescore-*"]},
                                              {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if running:
        raise SystemExit("LAUNCH_REFUSED: a helm3-t01-rescore machine is already running: %s" % [i["InstanceId"] for r in running for i in r["Instances"]])
    tags = [{"Key": "Name", "Value": "helm3-t01-rescore-%s" % stamp}, {"Key": "Purpose", "Value": "T01 trusted rescore - owner approved in chat 2026-09-21"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched = ec2.run_instances(
        ImageId=ami, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnet["SubnetId"], SecurityGroupIds=[group["GroupId"]],
        InstanceInitiatedShutdownBehavior="terminate", UserData=script, ClientToken="helm3-t01-%s" % stamp, MetadataOptions={"HttpTokens": "required"},
        BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"], "Ebs": {"VolumeSize": 20, "VolumeType": "gp3", "DeleteOnTermination": True}}],
        TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
    instance = launched["Instances"][0]
    print("LAUNCHED INSTANCE ID: %s  (printed FIRST, before anything else can fail)" % instance["InstanceId"], flush=True)
    record = {"schema": "cncm.aws-rescore-launch/0.1", "owner_approval_words": "yes run the AWS job", "approved": {"machine": INSTANCE_TYPE, "region": REGION,
              "price_per_hour_usd": PRICE_PER_HOUR, "time_limit_minutes": 90, "dollar_ceiling": DOLLAR_CEILING},
              "instance_id": instance["InstanceId"], "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "ami": ami, "ami_name": image.get("Name"), "subnet": subnet["SubnetId"], "availability_zone": subnet["AvailabilityZone"],
              "security_group": group["GroupId"], "security_group_inbound_rules": group["IpPermissions"], "in_instance_timer_seconds": MAX_SECONDS, "client_deadline_minutes": CLIENT_DEADLINE_MINUTES,
              "worst_case_usd_at_client_deadline": round(worst_case, 4), "bucket": BUCKET, "keys": keys,
              "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha, "source_commit": commit, "file_list": files},
              "python_version_requested": PYTHON_VERSION, "links_stored": "no -- time-limited links are never written to disk"}
    (HERE / "launch_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes. Record: launch_record.json" % (
        instance["InstanceId"], INSTANCE_TYPE, subnet["AvailabilityZone"], MAX_SECONDS // 60))
    return 0


if __name__ == "__main__":
    sys.exit(main())
