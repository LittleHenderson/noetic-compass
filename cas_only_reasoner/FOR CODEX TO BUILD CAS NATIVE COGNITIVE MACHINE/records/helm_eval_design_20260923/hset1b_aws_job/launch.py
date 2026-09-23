"""Launch the HSET-1B build (Stage 1 reach cells at 6 and 7 nodes) on ONE AWS CPU machine.

Owner decision, in chat, 2026-09-23: "GO WITH YOUR RECOMMENDATION 6 AND 7 NODE" (and "build the Stage 1 cells on aws") (and earlier: "use aws", "use aws as there is only
354 mb of 16 gbs locally"). Limits are in JOB_LIMITS.md and enforced here and on the machine. Adapted from
`../aws_probe_job/launch.py`: presigned links only, NO credentials on the machine, self-termination on shutdown, three
kill switches plus the client watcher, refusal to launch twice.

What differs: a CPU machine (no model, no GPU work); the bundle is built from GIT OBJECTS, not the working tree, so the
machine gets exactly the committed bytes of three sources:
  frozen/  the CNCM tree at Helm 2.0's source 20208c92 (the frozen checker, course and reader)
  v2/      the CNCM tree at Codex's checker-v2 commit 7f85af1e, plus the 12 historical prediction files (from this
           branch's HEAD) that test A2 needs
  claude/  Claude's builder and acceptance scripts at this branch's HEAD (refused if the working copy differs)
plus the sealed salt (read from the archive folder, never from a repository) and anchors.json (the LF sha256 of the
five frozen files, computed from the ORIGINAL commit's blobs).

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
INSTANCE_TYPE, PRICE_PER_HOUR = "c7i.2xlarge", 0.357          # AWS on-demand, us-west-2, Linux; as used 2026-09-21
AMI_PARAMETER = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
ROOT_GB = 20
MAX_SECONDS, CLIENT_DEADLINE_MINUTES, DOLLAR_CEILING = 120 * 60, 130, 1.50
PYTHON_VERSION = "3.14"
ORIGINAL = "20208c923d41c24614504d4ecc2b289ecb66eda8"
V2_COMMIT = "7f85af1eb9eb0ed991d5a8c82fa7ec4db43e539d"
ARCHIVE = pathlib.Path("D:/tksCAS-archive/hset1b_sealed_20260923")
SALT = ARCHIVE / "salt.hex"
CODE_TOPS = ("cncm/", "research/")
DATA_DIRS = ("records/typed_course_001/", "records/typed_matched_001/development_001/", "schemas/", "spec/")
DATA_FILES = ("records/typed_interface_001/checks_002/training_tokenizer.json", "records/typed_practice_001/evaluate_gates.py",
              "pyproject.toml")
PINS = {"records/typed_course_001/checks_002/public_course.json": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
        "records/typed_interface_001/checks_002/training_tokenizer.json": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c",
        "records/typed_matched_001/development_001/compact_development.json": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4"}
FROZEN_FILES = ("checker.py", "answers.py", "slots.py", "source.py", "pointer_inputs.py")
TT = "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/"
PREDICTIONS = ["records/typed_pointer_001/%s/collected/results/artifacts/%s_predictions.json" % (r, p)
               for r in ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")]
               + ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")] for p in ("course_p00", "course_p10")]
D = "records/helm_eval_design_20260923/"
CLAUDE_FILES = [D + "hset1a/hset_worlds.py", D + "hset1a/hset1a_build.py", D + "hset1a/hset1b_build.py",
                D + "d1_acceptance/oracle_isomorphism.py"]
JOB_FILES = [D + "hset1b_aws_job/launch.py", D + "hset1b_aws_job/job.sh.template", D + "hset1b_aws_job/watch.py"]


def git(*args, data=None):
    out = subprocess.run(["git", "-C", str(PACKAGE)] + list(args), input=data, capture_output=True, check=True)
    return out.stdout


def prefix():
    return git("rev-parse", "--show-prefix").decode().strip()


def tree_paths(commit):
    """Repository-relative CNCM paths at `commit` that the job needs (code under cncm/ and research/, the data)."""
    pre = prefix()
    names = [n for n in git("ls-tree", "-r", "-z", "--name-only", "--full-tree", commit, "--", pre).decode("utf-8").split("\0") if n]
    rel = [n[len(pre):] for n in names if n.startswith(pre)]
    keep = [r for r in rel if (r.startswith(CODE_TOPS) and r.endswith(".py")) or r.startswith(DATA_DIRS) or r in DATA_FILES]
    return sorted(keep)


def read_blobs(commit, rels):
    """Exact stored bytes of each path at `commit`, through one `git cat-file --batch` (no line-ending conversion)."""
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


def lf(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def assemble():
    head = git("rev-parse", "HEAD").decode().strip()
    for c in (ORIGINAL, V2_COMMIT):
        try:
            found = git("rev-parse", "--verify", "--quiet", c + "^{commit}").decode().strip()
        except subprocess.CalledProcessError:
            found = None
        if found != c:
            raise SystemExit("BUNDLE_REFUSED: commit %s not found in this repository" % c)
    dirty = git("status", "--porcelain", "--", *(CLAUDE_FILES + JOB_FILES)).decode().strip()   # pathspecs relative to PACKAGE
    if dirty:
        # any line means a script, the machine template or this launcher differs from HEAD
        raise SystemExit("BUNDLE_REFUSED: commit the scripts first:\n" + dirty)
    frozen_paths, v2_paths = tree_paths(ORIGINAL), tree_paths(V2_COMMIT)
    frozen, v2 = read_blobs(ORIGINAL, frozen_paths), read_blobs(V2_COMMIT, v2_paths)
    predictions = read_blobs(head, PREDICTIONS)
    claude = read_blobs(head, CLAUDE_FILES)
    for tree, name in ((frozen, "frozen"), (v2, "v2")):
        for path, pin in PINS.items():
            if hashlib.sha256(tree[path]).hexdigest() != pin:
                raise SystemExit("BUNDLE_REFUSED: %s/%s does not match its pinned sha256" % (name, path))
    for f in ("checker_v2.py", "answers_v2.py", "slots_v2.py"):
        if TT + f not in v2:
            raise SystemExit("BUNDLE_REFUSED: v2 file %s missing" % f)
    anchors = {"schema": "claude.d1-anchors/0.1", "original_commit": ORIGINAL, "v2_commit": V2_COMMIT, "claude_commit": head,
               "frozen_files_sha256_lf": {f: lf(frozen[TT + f]) for f in FROZEN_FILES},
               "v2_tree_frozen_files_sha256_lf_at_launch": {f: lf(v2[TT + f]) for f in FROZEN_FILES},
               "prediction_files_sha256": {p: hashlib.sha256(b).hexdigest() for p, b in predictions.items()},
               "prediction_source_commit": head}
    salt = SALT.read_bytes().strip()
    if len(salt) != 64:
        raise SystemExit("BUNDLE_REFUSED: salt file is not 64 hex characters")
    files = {}
    files.update({"frozen/" + p: b for p, b in frozen.items()})
    files.update({"v2/" + p: b for p, b in v2.items()})
    files.update({"v2/" + p: b for p, b in predictions.items()})
    files.update({"claude/" + p: b for p, b in claude.items()})
    files["sealed/salt.hex"] = salt + b"\n"
    files["anchors.json"] = json.dumps(anchors, indent=1, sort_keys=True).encode()
    return files, anchors, head


def build_bundle(files):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6, mtime=0) as zipped, tarfile.open(fileobj=zipped, mode="w") as tar:
        for name in sorted(files):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(files[name]), 0, 0o644
            tar.addfile(info, io.BytesIO(files[name]))
    body = buffer.getvalue()
    return body, hashlib.sha256(body).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import boto3

    files, anchors, head = assemble()
    body, bundle_sha = build_bundle(files)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key_prefix = "helm-integration/hset1b-build-%s/" % stamp
    print("bundle: %d files, %.2f MB, sha256 %s; claude commit %s" % (len(files), len(body) / 1e6, bundle_sha[:16], head[:8]))
    print("frozen-file anchors (original %s): %s" % (ORIGINAL[:8], json.dumps(anchors["frozen_files_sha256_lf"])))
    same = anchors["frozen_files_sha256_lf"] == anchors["v2_tree_frozen_files_sha256_lf_at_launch"]
    print("v2 tree frozen files equal the original at launch: %s (the machine re-checks this as test A1)" % same)

    template = (HERE / "job.sh.template").read_text(encoding="utf-8").replace("\r\n", "\n")
    keys = {"bundle": key_prefix + "bundle.tar.gz", "results": key_prefix + "results.tar.gz",
            "sealed": key_prefix + "sealed.tar.gz", "progress": key_prefix + "progress.log"}
    s3 = boto3.client("s3", region_name=REGION)
    if args.dry_run:
        urls = {k: "https://DRY-RUN/%s" % v for k, v in keys.items()}
    else:
        if (HERE / "launch_record.json").exists():
            raise SystemExit("LAUNCH_REFUSED: launch_record.json already exists -- one approval, one machine")
        s3.put_object(Bucket=BUCKET, Key=keys["bundle"], Body=body)
        expiry = 4 * 3600
        urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=expiry)}
        for k in ("results", "sealed", "progress"):
            urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=expiry)
    script = (template.replace("__MAX_SECONDS__", str(MAX_SECONDS)).replace("__MAX_MINUTES__", str(MAX_SECONDS // 60 + 3))
              .replace("__BUNDLE_URL__", urls["bundle"]).replace("__RESULTS_URL__", urls["results"])
              .replace("__SEALED_URL__", urls["sealed"]).replace("__PROGRESS_URL__", urls["progress"])
              .replace("__BUNDLE_SHA256__", bundle_sha).replace("__SOURCE_COMMIT__", head).replace("__PYTHON_VERSION__", PYTHON_VERSION))
    assert "__" not in script.replace("__pycache__", ""), "an unfilled placeholder remains"
    assert len(script.encode("utf-8")) < 16000, "user-data limit"
    worst_case = (PRICE_PER_HOUR + 0.005 + ROOT_GB * 0.08 / 730) * CLIENT_DEADLINE_MINUTES / 60.0   # machine + public address + disk
    assert worst_case < DOLLAR_CEILING, "the time limit does not keep the job under the ceiling"
    if args.dry_run:
        (HERE / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded or launched. Worst case at the client deadline %.2f USD (ceiling %.2f)." % (worst_case, DOLLAR_CEILING))
        return 0

    ec2 = boto3.client("ec2", region_name=REGION)
    ami = boto3.client("ssm", region_name=REGION).get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
    image = ec2.describe_images(ImageIds=[ami])["Images"][0]
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        raise SystemExit("LAUNCH_REFUSED: the default security group allows inbound traffic from an address range")
    running = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["hset1b-build-*"]},
                                              {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if running:
        raise SystemExit("LAUNCH_REFUSED: an hset1b-build machine is already running")
    tags = [{"Key": "Name", "Value": "hset1b-build-%s" % stamp},
            {"Key": "Purpose", "Value": "HSET-1B 6/7-node reach cells (Claude custodian); owner decision 2026-09-23"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched, last_error = None, None
    for subnet in sorted(subnets, key=lambda s: s["AvailabilityZone"]):
        # A launch that timed out on our side may still have started a machine: never start a second one.
        existing = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["hset1b-build-%s" % stamp]},
                                                  {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
        if existing:
            launched = {"Instances": existing[0]["Instances"]}
            print("a machine from an earlier zone attempt is running: using it, not launching another", flush=True)
            break
        try:
            launched = ec2.run_instances(
                ImageId=ami, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnet["SubnetId"], SecurityGroupIds=[group["GroupId"]],
                InstanceInitiatedShutdownBehavior="terminate", UserData=script, ClientToken="hset1b-%s-%s" % (stamp, subnet["AvailabilityZone"]),
                MetadataOptions={"HttpTokens": "required"},
                BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"], "Ebs": {"VolumeSize": ROOT_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
                TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
            break
        except Exception as error:  # noqa: BLE001 -- capacity in one zone: try the next
            last_error = "%s: %s" % (subnet["AvailabilityZone"], str(error)[:200])
            print("launch in %s refused: %s" % (subnet["AvailabilityZone"], str(error)[:160]), flush=True)
    if launched is None:
        raise SystemExit("LAUNCH_FAILED in every zone; last error %s" % last_error)
    instance = launched["Instances"][0]
    print("LAUNCHED INSTANCE ID: %s" % instance["InstanceId"], flush=True)
    record = {"schema": "claude.hset1b-launch/0.1",
              "owner_approval_words": ["GO WITH YOUR RECOMMENDATION 6 AND 7 NODE", "build the Stage 1 cells on aws", "use aws"],
              "approved": {"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                           "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": DOLLAR_CEILING},
              "instance_id": instance["InstanceId"], "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "availability_zone": instance["Placement"]["AvailabilityZone"], "ami": ami, "ami_name": image.get("Name"),
              "root_volume_gb": ROOT_GB, "security_group": group["GroupId"], "in_instance_timer_seconds": MAX_SECONDS,
              "client_deadline_minutes": CLIENT_DEADLINE_MINUTES, "worst_case_usd_at_client_deadline": round(worst_case, 4),
              "bucket": BUCKET, "keys": keys, "python": PYTHON_VERSION, "anchors": anchors,
              "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha, "claude_commit": head,
                         "original_commit": ORIGINAL, "v2_commit": V2_COMMIT},
              "sealed_destination": str(ARCHIVE / ("run_" + stamp)),
              "machine_script_template_sha256_lf": hashlib.sha256(template.encode("utf-8")).hexdigest(),
              "machine_script_rendered_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
              "custody_note": ("the bundle (with the salt) and the sealed results stay in the private bucket under keys; "
                               "anyone who can read that bucket, or this machine's startup script while its links are "
                               "valid (4 hours), could rebuild TEST_NEW_5. Claude does not delete them (no permanent "
                               "deletion); removing them is an owner decision"),
              "links_stored": "no -- time-limited links are never written to disk"}
    (HERE / "launch_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes." % (instance["InstanceId"], INSTANCE_TYPE,
                                                                        instance["Placement"]["AvailabilityZone"], MAX_SECONDS // 60 + 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
