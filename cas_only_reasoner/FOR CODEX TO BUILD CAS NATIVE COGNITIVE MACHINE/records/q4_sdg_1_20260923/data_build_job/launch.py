"""Launch the Q4-SDG-1 B-package DATA BUILD on ONE small AWS CPU machine (no GPU, no torch, no model).

Runner: the Claude coordinator (temporary takeover). Owner authority: OWNER_AUTHORITY_AND_DECISIONS_20260924.md on
research/helm-integration-20260923 ($5.00 ceiling for the A-versus-B job INCLUDING its pinned data build; one GPU
machine at a time; no automatic retries) and the AWS order of 2026-09-23. Limits: JOB_LIMITS.md in this folder.

What the machine does (job.sh.template): builds the B lesson package TWICE with `--expect-engine python` (two hash
seeds), checks the two builds are byte-identical, re-verifies build 1 with the pinned compiler (`--verify --unpinned
--recompile`), and returns ONLY digests and the manifest (results) -- never a row file. The whole package goes to S3 as
an archive the watcher never downloads. The coordinator then pins it with pin_package.py (review item A1).

The bundle is built from GIT OBJECTS at one reviewed commit (--source-commit, 40 hex, on the Q4-SDG-1 branch):
  research/helm_cas_expression_lab/   top-level .py and .json files, the pinned compiler snapshot, and the PUBLIC Q3
                                      v0.7 data (manifest, baselines, visible_*.jsonl)
Custody: no path matching *_eval.jsonl, containing "sealed", or containing hset1a/hset1b is ever bundled (checked
twice here, again on the machine). The machine gets no credentials: one download link and three upload links.

    python launch.py --source-commit <sha> [--dry-run]
"""
import argparse
import datetime
import gzip
import hashlib
import io
import json
import pathlib
import re
import subprocess
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[2]
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
INSTANCE_TYPE, PRICE_PER_HOUR = "c7i.large", 0.0893             # 2 vCPU, 4 GiB; on-demand us-west-2
AMI_PARAMETER = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
ROOT_GB = 30
PUBLIC_IPV4_PER_HOUR, GP3_PER_GB_MONTH, HOURS_PER_MONTH = 0.005, 0.08, 730
MAX_SECONDS, CLIENT_DEADLINE_MINUTES = 40 * 60, 50
DOLLAR_CEILING = 5.00                                            # the WHOLE A-versus-B job: data build + training
TRAINING_WORST_CASE_USD = 2.1678                                 # ab_job/launch.py worst case (a test checks it)
PYTHON_VERSION = "3.14.7"
BRANCH = "claude/q4-sdg-feedback-20260923"
LAB = "research/helm_cas_expression_lab/"
COMPILER = LAB + "pinned_sources/compiler_pre_ohm_61ed5a45.py"
DATA = LAB + "data/q3_v0_7/"
FORBIDDEN = re.compile(r"(_eval\.jsonl$|sealed|hset1a|hset1b)", re.IGNORECASE)
JOB_FILES = ["launch.py", "job.sh.template", "watch.py", "JOB_LIMITS.md", "pin_package.py"]
NAME_PREFIX = "q4-sdg-1-data-build"


def worst_case_usd():
    per_hour = PRICE_PER_HOUR + PUBLIC_IPV4_PER_HOUR + ROOT_GB * GP3_PER_GB_MONTH / HOURS_PER_MONTH
    return per_hour * CLIENT_DEADLINE_MINUTES / 60.0


def git(*args, data=None):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), input=data, capture_output=True, check=True).stdout


def prefix():
    return git("rev-parse", "--show-prefix").decode().strip()


def wanted(rel):
    name = pathlib.PurePosixPath(rel).name
    if FORBIDDEN.search(rel):
        return False
    if rel == COMPILER:
        return True
    if rel.startswith(DATA):
        return rel.count("/") == DATA.count("/") and (name in ("manifest.json", "baselines.json") or
                                                      (name.startswith("visible_") and name.endswith(".jsonl")))
    return rel.startswith(LAB) and rel.count("/") == LAB.count("/") and name.endswith((".py", ".json"))


def read_blobs(commit, rels):
    pre = prefix()
    request = "".join("%s:%s%s\n" % (commit, pre, r) for r in rels).encode("utf-8")
    raw, out, pos = git("cat-file", "--batch", data=request), {}, 0
    for r in rels:
        end = raw.index(b"\n", pos)
        header = raw[pos:end].decode()
        if header.endswith("missing"):
            raise SystemExit("BUNDLE_REFUSED: %s missing at %s" % (r, commit[:8]))
        size = int(header.split()[2])
        out[r] = raw[end + 1:end + 1 + size]
        pos = end + 1 + size + 1
    return out


def assemble(commit):
    try:
        found = git("rev-parse", "--verify", "--quiet", commit + "^{commit}").decode().strip()
    except subprocess.CalledProcessError:
        found = None
    if found != commit:
        raise SystemExit("BUNDLE_REFUSED: commit %s not found" % commit)
    try:
        git("merge-base", "--is-ancestor", commit, BRANCH)
    except subprocess.CalledProcessError:
        raise SystemExit("BUNDLE_REFUSED: %s is not on %s" % (commit, BRANCH))
    job_rel = [str((HERE / f).relative_to(PACKAGE)).replace("\\", "/") for f in JOB_FILES]
    dirty = git("status", "--porcelain", "--", *job_rel).decode().strip()
    if dirty:
        raise SystemExit("BUNDLE_REFUSED: commit the job files first:\n" + dirty)
    pre = prefix()
    names = [n for n in git("ls-tree", "-r", "-z", "--name-only", "--full-tree", commit, "--", pre).decode("utf-8").split("\0") if n]
    rels = sorted(n[len(pre):] for n in names if n.startswith(pre) and wanted(n[len(pre):]))
    blobs = read_blobs(commit, rels)
    leaked = [r for r in blobs if FORBIDDEN.search(r)]
    if leaked:
        raise SystemExit("BUNDLE_REFUSED: custody: %s" % leaked)
    for needed in (LAB + "q4_sdg_curriculum.py", LAB + "q4_ab_prep.py", LAB + "q4_ab_rules.py", COMPILER,
                   DATA + "manifest.json", DATA + "visible_G_train.jsonl", DATA + "visible_G_dev.jsonl",
                   DATA + "visible_R_dev.jsonl", LAB + "Q3_DATA_PINS.json"):
        if needed not in blobs:
            raise SystemExit("BUNDLE_REFUSED: %s not in the bundle" % needed)
    files = {"pkg/" + r: b for r, b in blobs.items()}
    identity = {"source_commit": commit, "branch": BRANCH, "files": len(blobs),
                "lf_sha256": {r: hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest() for r, b in blobs.items()
                              if r.startswith(LAB) and r.endswith((".py", ".json"))},
                "custody": "no *_eval.jsonl, no *sealed*, no hset1a/hset1b path bundled (checked by name, twice)"}
    files["identity.json"] = json.dumps(identity, indent=1, sort_keys=True).encode()
    return files, identity


def build_bundle(files):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6, mtime=0) as zipped, tarfile.open(fileobj=zipped, mode="w") as tar:
        for name in sorted(files):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(files[name]), 0, 0o644
            tar.addfile(info, io.BytesIO(files[name]))
    body = buffer.getvalue()
    return body, hashlib.sha256(body).hexdigest()


def fill(template, values):
    script = template
    for key, value in values.items():
        script = script.replace("__%s__" % key, str(value))
    if "__" in script.replace("__pycache__", ""):
        raise SystemExit("an unfilled placeholder remains")
    if len(script.encode("utf-8")) >= 16000:
        raise SystemExit("user-data limit")
    return script


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if len(args.source_commit) != 40:
        raise SystemExit("give the full 40-character commit")
    if worst_case_usd() + TRAINING_WORST_CASE_USD > DOLLAR_CEILING:
        raise SystemExit("LAUNCH_REFUSED: data build %.4f + training %.4f exceeds %.2f" % (
            worst_case_usd(), TRAINING_WORST_CASE_USD, DOLLAR_CEILING))
    if (HERE / "launch_record.json").exists():
        raise SystemExit("LAUNCH_REFUSED: launch_record.json already exists -- one approval, one machine, no retry")
    import boto3
    files, identity = assemble(args.source_commit)
    body, bundle_sha = build_bundle(files)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key_prefix = "q4-sdg-1/data-build-%s/" % stamp
    print("bundle: %d files, %.2f MB, sha256 %s; source %s" % (len(files), len(body) / 1e6, bundle_sha[:16], args.source_commit[:8]))
    template = (HERE / "job.sh.template").read_text(encoding="utf-8").replace("\r\n", "\n")
    keys = {"bundle": key_prefix + "bundle.tar.gz", "results": key_prefix + "results.tar.gz",
            "progress": key_prefix + "progress.log", "package": key_prefix + "package.tar.gz"}
    ec2, ssm = boto3.client("ec2", region_name=REGION), boto3.client("ssm", region_name=REGION)
    ami = ssm.get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
    image = ec2.describe_images(ImageIds=[ami])["Images"][0]
    print("image: %s (%s)" % (ami, image.get("Name")))
    if args.dry_run:
        urls = {k: "https://DRY-RUN/%s" % v for k, v in keys.items()}
    else:
        s3 = boto3.client("s3", region_name=REGION)
        s3.put_object(Bucket=BUCKET, Key=keys["bundle"], Body=body)
        urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=2 * 3600)}
        for k in ("results", "progress", "package"):
            urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=2 * 3600)
    script = fill(template, {"MAX_SECONDS": MAX_SECONDS, "MAX_MINUTES": MAX_SECONDS // 60 + 3,
                             "BUNDLE_URL": urls["bundle"], "RESULTS_URL": urls["results"],
                             "PROGRESS_URL": urls["progress"], "PACKAGE_URL": urls["package"],
                             "BUNDLE_SHA256": bundle_sha, "PYTHON_VERSION": PYTHON_VERSION})
    if args.dry_run:
        (HERE / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded or launched. Worst case %.4f USD; with training %.4f (ceiling %.2f)." % (
            worst_case_usd(), worst_case_usd() + TRAINING_WORST_CASE_USD, DOLLAR_CEILING))
        return 0
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        raise SystemExit("LAUNCH_REFUSED: the default security group allows inbound traffic from an address range")
    live = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [NAME_PREFIX + "-*"]},
                                           {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if live:
        raise SystemExit("LAUNCH_REFUSED: a data-build machine is already running")
    name = "%s-%s" % (NAME_PREFIX, stamp)
    tags = [{"Key": "Name", "Value": name}, {"Key": "Purpose", "Value": "Q4-SDG-1 B-package data build, CPU only; Claude coordinator"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched, last_error = None, None
    for subnet in sorted(subnets, key=lambda s: s["AvailabilityZone"]):
        existing = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": [name]},
                                                   {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
        if existing:
            launched = {"Instances": existing[0]["Instances"]}
            break
        try:
            launched = ec2.run_instances(
                ImageId=ami, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnet["SubnetId"], SecurityGroupIds=[group["GroupId"]],
                InstanceInitiatedShutdownBehavior="terminate", UserData=script, ClientToken="q4-build-%s-%s" % (stamp, subnet["AvailabilityZone"]),
                MetadataOptions={"HttpTokens": "required"},
                BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"], "Ebs": {"VolumeSize": ROOT_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
                TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
            break
        except Exception as error:  # noqa: BLE001 -- placement in the next zone is not a retry of the job
            last_error = "%s: %s" % (subnet["AvailabilityZone"], str(error)[:200])
            print("launch in %s refused: %s" % (subnet["AvailabilityZone"], str(error)[:160]), flush=True)
    if launched is None:
        raise SystemExit("LAUNCH_FAILED in every zone; last error %s" % last_error)
    instance = launched["Instances"][0]
    record = {"schema": "claude.q4-sdg-1-data-build-launch/0.2",
              "owner_authority": ["OWNER_AUTHORITY_AND_DECISIONS_20260924.md: A-versus-B, $5.00 ceiling including the pinned data build",
                                  "AWS order 2026-09-23: 'use aws as there is only 354 mb of 16 gbs locally'"],
              "approved": {"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                           "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling_whole_ab_job": DOLLAR_CEILING},
              "instance_id": instance["InstanceId"], "instance_name": name, "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "availability_zone": instance["Placement"]["AvailabilityZone"], "ami": ami, "ami_name": image.get("Name"),
              "root_volume_gb": ROOT_GB, "in_instance_timer_seconds": MAX_SECONDS, "client_deadline_minutes": CLIENT_DEADLINE_MINUTES,
              "worst_case_usd_at_client_deadline": round(worst_case_usd(), 4),
              "training_worst_case_usd": TRAINING_WORST_CASE_USD, "bucket": BUCKET, "keys": keys, "python": PYTHON_VERSION,
              "identity": identity, "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha},
              "machine_script_template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
              "label": "CLAUDE_BUILT_CLAUDE_CHECKED", "links_stored": "no -- time-limited links are never written to disk"}
    (HERE / "launch_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes." % (instance["InstanceId"], INSTANCE_TYPE,
                                                                        instance["Placement"]["AvailabilityZone"], MAX_SECONDS // 60 + 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
