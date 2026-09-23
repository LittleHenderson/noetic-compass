"""Launch the analogy-wiring before-readings, the preservation reference and the probe self-test on ONE AWS GPU machine.

Owner order, in chat, 2026-09-23: "use aws" and "use aws as there is only 354 mb of 16 gbs locally".
Limits are in JOB_LIMITS.md and enforced here and on the machine. Adapted from the working CPU launcher
`records/typed_pointer_001/aws_rescore_job/launch.py` (2026-09-21): the same presigned-link design, NO credentials on
the machine, self-termination on shutdown, three kill switches plus the client watcher, and refusal to launch twice.

Differences from that launcher: a GPU machine (g4dn.2xlarge, NVIDIA T4) on the AWS Deep Learning base image (NVIDIA
driver included); a bundle of the model code, course files, 6 checkpoints and the two local wheels
(`cas-neural-cjt 0.2.0`, `casformer-reference 0.1.0`, hash-checked); binary files are bundled byte for byte (only text
files are LF-normalised).

    python launch.py [--dry-run]
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
INSTANCE_TYPE, PRICE_PER_HOUR = "g4dn.2xlarge", 0.752          # AWS pricing API, us-west-2 Linux on-demand, 2026-09-23
AMI_PARAMETER = "/aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-24.04/latest/ami-id"
MAX_SECONDS, CLIENT_DEADLINE_MINUTES, DOLLAR_CEILING = 150 * 60, 160, 3.00
PYTHON_VERSION, TORCH_VERSION, NUMPY_VERSION = "3.14", "2.11.0", "2.5.2"     # = the local cas-gpu venv
WHEEL_DIR = pathlib.Path("C:/Users/wakil/AppData/Local/Temp/claude/rdcjt_wheels")
WHEELS = {"casformer_reference-0.1.0-py3-none-any.whl": "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
          "cas_neural_cjt-0.2.0-py3-none-any.whl": "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9"}
TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".toml", ".yaml", ".yml", ".jsonl", ".csv"}
DATA_DIRS = ["records/typed_course_001", "records/typed_matched_001/development_001", "schemas", "spec"]
DATA_FILES = ["records/typed_interface_001/checks_002/training_tokenizer.json", "records/typed_practice_001/evaluate_gates.py",
              "pyproject.toml"]
CHECKPOINTS = ["records/typed_pointer_001/receipt_%s/checkpoints/%s" % (s, n)
               for s in ("20260917", "20260918", "20260919") for n in ("initial.pt", "final.pt")]
D = "records/helm_eval_design_20260923/"
PROBE_FILES = [D + "analogy_wiring_probe/" + n for n in ("analogy_wiring_probe_v0_2.py", "preservation_digest.py", "probe_self_test.py",
                                                         "PREREG_ANALOGY_WIRING_PROBE_v0_2.md", "PREREG_PROBE_SELF_TEST.md")] + [D + "aws_probe_job/preflight.py"]


def git(*args):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), capture_output=True, text=True, check=True).stdout


def bundle_files():
    tracked = git("ls-files", "--", "cncm", "research", *DATA_DIRS).splitlines()
    code = [p for p in tracked if p.endswith(".py") and (p.startswith("cncm/") or p.startswith("research/"))]
    data = [p for p in tracked if any(p.startswith(d + "/") or p == d for d in DATA_DIRS)]
    files = sorted(set(code) | set(data) | set(DATA_FILES) | set(CHECKPOINTS) | set(PROBE_FILES))
    missing = [p for p in files if not (PACKAGE / p).is_file()]
    if missing:
        raise SystemExit("BUNDLE_REFUSED: files missing on disk: %s" % missing[:20])
    # Directories as pathspecs (1,000+ file paths would overflow the Windows command line); porcelain paths are
    # repository-relative, so compare against the package prefix + each bundled path.
    prefix = git("rev-parse", "--show-prefix").strip()
    wanted = {prefix + f for f in files}
    tops = sorted({f.split("/")[0] for f in files})
    dirty = [line for line in git("status", "--porcelain", "--untracked-files=no", "--", *tops).splitlines()
             if line[3:].strip().strip('"') in wanted]
    if dirty:
        raise SystemExit("BUNDLE_REFUSED: bundle files differ from the commit:\n%s" % "\n".join(dirty[:40]))
    for name, digest in WHEELS.items():
        got = hashlib.sha256((WHEEL_DIR / name).read_bytes()).hexdigest()
        if got != digest:
            raise SystemExit("BUNDLE_REFUSED: wheel %s sha256 %s != recorded %s" % (name, got, digest))
    return files


def build_bundle(files):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6, mtime=0) as zipped, tarfile.open(fileobj=zipped, mode="w") as tar:
        def add(name, data):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
        for rel in files:
            data = (PACKAGE / rel).read_bytes()
            if pathlib.Path(rel).suffix in TEXT_SUFFIXES:
                data = data.replace(b"\r\n", b"\n")                 # what git stores; binaries stay byte for byte
            add(rel, data)
        for name in sorted(WHEELS):
            add("_wheels/" + name, (WHEEL_DIR / name).read_bytes())
    body = buffer.getvalue()
    return body, hashlib.sha256(body).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import boto3

    files = bundle_files()
    commit = git("rev-parse", "HEAD").strip()
    body, bundle_sha = build_bundle(files)
    checkpoint_sha = {p: hashlib.sha256((PACKAGE / p).read_bytes()).hexdigest() for p in CHECKPOINTS}
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prefix = "helm-integration/wiring-probe-%s/" % stamp
    print("bundle: %d files + %d wheels, %.2f MB, sha256 %s, source commit %s" % (len(files), len(WHEELS), len(body) / 1e6, bundle_sha[:16], commit[:8]))

    template = (HERE / "job.sh.template").read_text(encoding="utf-8").replace("\r\n", "\n")
    keys = {"bundle": prefix + "bundle.tar.gz", "results": prefix + "results.tar.gz", "progress": prefix + "progress.log"}
    s3 = boto3.client("s3", region_name=REGION)
    if args.dry_run:
        urls = {k: "https://DRY-RUN/%s" % v for k, v in keys.items()}
    else:
        if (HERE / "launch_record.json").exists():
            raise SystemExit("LAUNCH_REFUSED: launch_record.json already exists -- one approval, one machine")
        s3.put_object(Bucket=BUCKET, Key=keys["bundle"], Body=body)
        expiry = 4 * 3600
        urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=expiry),
                "results": s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys["results"]}, ExpiresIn=expiry),
                "progress": s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys["progress"]}, ExpiresIn=expiry)}
    script = (template.replace("__MAX_SECONDS__", str(MAX_SECONDS)).replace("__MAX_MINUTES__", str(MAX_SECONDS // 60 + 3))
              .replace("__BUNDLE_URL__", urls["bundle"]).replace("__RESULTS_URL__", urls["results"]).replace("__PROGRESS_URL__", urls["progress"])
              .replace("__BUNDLE_SHA256__", bundle_sha).replace("__SOURCE_COMMIT__", commit).replace("__PYTHON_VERSION__", PYTHON_VERSION)
              .replace("__TORCH_VERSION__", TORCH_VERSION).replace("__NUMPY_VERSION__", NUMPY_VERSION))
    assert "__" not in script.replace("__pycache__", ""), "an unfilled placeholder remains"
    assert len(script.encode("utf-8")) < 16000, "user-data limit"
    worst_case = PRICE_PER_HOUR * CLIENT_DEADLINE_MINUTES / 60.0
    assert worst_case < DOLLAR_CEILING, "the time limit does not keep the job under the ceiling"
    if args.dry_run:
        (HERE / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded or launched. Worst case at the client deadline %.2f USD (ceiling %.2f)." % (worst_case, DOLLAR_CEILING))
        return 0

    ec2 = boto3.client("ec2", region_name=REGION)
    ami = boto3.client("ssm", region_name=REGION).get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
    image = ec2.describe_images(ImageIds=[ami])["Images"][0]
    root_size = max(int(image["BlockDeviceMappings"][0]["Ebs"]["VolumeSize"]), 100)
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        raise SystemExit("LAUNCH_REFUSED: the default security group allows inbound traffic from an address range")
    running = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["helm-wiring-probe-*"]},
                                              {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if running:
        raise SystemExit("LAUNCH_REFUSED: a helm-wiring-probe machine is already running")
    tags = [{"Key": "Name", "Value": "helm-wiring-probe-%s" % stamp},
            {"Key": "Purpose", "Value": "Helm analogy wiring probe before-reading; owner order 'use aws' 2026-09-23"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched, last_error = None, None
    for subnet in sorted(subnets, key=lambda s: s["AvailabilityZone"]):   # GPU capacity varies by zone
        try:
            launched = ec2.run_instances(
                ImageId=ami, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnet["SubnetId"], SecurityGroupIds=[group["GroupId"]],
                InstanceInitiatedShutdownBehavior="terminate", UserData=script, ClientToken="helm-wiring-%s-%s" % (stamp, subnet["AvailabilityZone"]),
                MetadataOptions={"HttpTokens": "required"},
                BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"], "Ebs": {"VolumeSize": root_size, "VolumeType": "gp3", "DeleteOnTermination": True}}],
                TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
            break
        except Exception as error:  # noqa: BLE001 -- InsufficientInstanceCapacity in one zone: try the next
            last_error = "%s: %s" % (subnet["AvailabilityZone"], str(error)[:200])
            print("launch in %s refused: %s" % (subnet["AvailabilityZone"], str(error)[:160]), flush=True)
    if launched is None:
        raise SystemExit("LAUNCH_FAILED in every zone; last error %s" % last_error)
    instance = launched["Instances"][0]
    print("LAUNCHED INSTANCE ID: %s" % instance["InstanceId"], flush=True)
    record = {"schema": "claude.aws-probe-launch/0.1",
              "owner_approval_words": ["use aws", "use aws as there is only 354 mb of 16 gbs locally"],
              "approved": {"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                           "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": DOLLAR_CEILING},
              "instance_id": instance["InstanceId"], "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "availability_zone": instance["Placement"]["AvailabilityZone"], "ami": ami, "ami_name": image.get("Name"),
              "root_volume_gb": root_size, "security_group": group["GroupId"], "in_instance_timer_seconds": MAX_SECONDS,
              "client_deadline_minutes": CLIENT_DEADLINE_MINUTES, "worst_case_usd_at_client_deadline": round(worst_case, 4),
              "bucket": BUCKET, "keys": keys, "python": PYTHON_VERSION, "torch": TORCH_VERSION, "numpy": NUMPY_VERSION, "wheels": WHEELS,
              "checkpoint_sha256": checkpoint_sha,
              "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha, "source_commit": commit},
              "links_stored": "no -- time-limited links are never written to disk"}
    (HERE / "launch_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes." % (instance["InstanceId"], INSTANCE_TYPE,
                                                                        instance["Placement"]["AvailabilityZone"], MAX_SECONDS // 60 + 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
