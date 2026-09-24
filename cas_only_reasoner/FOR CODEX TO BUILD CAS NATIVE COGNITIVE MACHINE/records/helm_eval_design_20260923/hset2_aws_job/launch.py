"""Launch the HSET-2 sealed build on ONE AWS CPU machine. DO NOT RUN until the coordinator has done every step in
JOB_LIMITS.md ("Before launch"). Label: CLAUDE_BUILT_CLAUDE_CHECKED (temporary takeover while Codex is away).

Adapted from `../hset1b_aws_job/launch.py` (presigned links only, NO credentials on the machine, self-termination on
shutdown, three kill switches plus the client watcher, refusal to launch twice) and from the T4 job's two-tree bundle.
The bundle is built from GIT OBJECTS only, never from working files:
  tree/    the CNCM tree at SOURCE_COMMIT (785c9bd1, on claude/helm-builder-continuation-20260923): cas_meta2 with the
           accepted checker v2 and slot compiler v2, Helm's input reader, eval_paths (the larger-question route and the
           public fixture file), and the data the reader and the course need
  claude/  the HSET-2 builder, stage 0 and its committed outputs, and the reused HSET-1A/1B code, at this branch's HEAD
           (refused if the working copy differs)
  sealed/  the two salts, read from the archive, each checked against its committed sha256
plus anchors.json: the sha256 (raw and LF) of EVERY bundled file.

    python launch.py [--dry-run]                    # --dry-run makes no AWS call (boto3 is not imported)
    python launch.py --materialize-tree DIR         # local tests only: write tree/ (no salts) into a new folder
"""
import argparse
import ast
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
INSTANCE_TYPE, PRICE_PER_HOUR = "c7i.2xlarge", 0.357          # AWS on-demand, us-west-2, Linux; as HSET-1A/1B
AMI_PARAMETER = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
ROOT_GB = 20
MAX_SECONDS, CLIENT_DEADLINE_MINUTES, DOLLAR_CEILING = 90 * 60, 100, 1.00
# Third-party tools, pinned (review F9). The machine installs them BEFORE the bundle (and its salts) reaches its disk.
# PYTHON_VERSION is the exact patch version the laptop tests used; the pinned uv checks the Python download against
# the checksum list built into that uv release. UV_VERSION is the uv the laptop has. UV_TARBALL_SHA256 is the sha256
# of https://github.com/astral-sh/uv/releases/download/<UV_VERSION>/uv-x86_64-unknown-linux-gnu.tar.gz: the
# coordinator copies it from that release's published .sha256 file and commits it before launch (JOB_LIMITS.md);
# None refuses the launch. The machine refuses to run if the downloaded tarball does not match it.
PYTHON_VERSION = "3.14.0"
UV_VERSION = "0.12.7"
# Set 2026-09-24 (pre-salt round) from the official release checksum file
#   https://github.com/astral-sh/uv/releases/download/0.12.7/uv-x86_64-unknown-linux-gnu.tar.gz.sha256
# (101 bytes: "<sha256>  uv-x86_64-unknown-linux-gnu.tar.gz"), and cross-checked against the asset "digest" field of
#   https://api.github.com/repos/astral-sh/uv/releases/tags/0.12.7 (published 2026-08-27T22:14:06Z; not a pre-release).
UV_TARBALL_SHA256 = "788f18abea7c5f55d6216e4f5613fd89d4d59b631efeec117b2b07fe72f1da21"
SOURCE_COMMIT = "785c9bd10f1416deb95f9c30aacb43124134fe45"
SOURCE_BRANCH = "claude/helm-builder-continuation-20260923"
ARCHIVE_HSET1A = pathlib.Path("D:/tksCAS-archive/hset1a_sealed_20260923")
# The coordinator creates the HSET-2 salt here (32 random bytes as 64 lowercase hex characters) and commits its sha256
# as hset2_build.HSET2_SALT_SHA256 BEFORE launch. The sealed results come back to a new run_<stamp> folder here.
ARCHIVE_HSET2 = pathlib.Path("D:/tksCAS-archive/hset2_sealed_20260924")
# HSET-1A's PUBLIC `test_shapes_digest`; the build proves TEST_NEW_5 is reproduced exactly. Set 2026-09-24 (pre-salt
# round) from records/helm_eval_design_20260923/hset1a_aws_job/RESULTS_READING.json ("test_shapes_digest", the build
# whose "salt_sha256" is 33f9d350..., = HSET1A_SALT_SHA256). PUBLIC_EXCLUDED version 2 does not change it: version 2
# adds only 6-node classes, and TEST_NEW_5 is hset1a_build.split_five of the HSET-1A salt over the 267 five-node classes
# (test_hset2.py checks that no 5-node class was added). None would refuse the launch.
EXPECTED_TEST5_SHAPES_DIGEST = "1b5a1d6872a69c350a73e51888cf7a942e00d5ea5747fa883a85f43444792bf9"
CODE_TOPS = ("cncm/", "research/")
DATA_DIRS = ("records/typed_course_001/", "records/typed_matched_001/development_001/", "schemas/", "spec/")
DATA_FILES = ("records/typed_interface_001/checks_002/training_tokenizer.json", "records/typed_practice_001/evaluate_gates.py",
              "records/typed_pointer_001/evaluate_gates.py", "pyproject.toml",
              "research/CAS_META_2_COMPOSITION/eval_paths/fixtures/larger_question_fixtures_v0_1.json")
PINS = {"records/typed_course_001/checks_002/public_course.json": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
        "records/typed_interface_001/checks_002/training_tokenizer.json": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c",
        "records/typed_matched_001/development_001/compact_development.json": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4",
        "research/CAS_META_2_COMPOSITION/eval_paths/fixtures/larger_question_fixtures_v0_1.json":
            "7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3"}
LF_PINS = {"records/typed_pointer_001/evaluate_gates.py": "d3e0ea979835fa548ae4fe4081280839b5b629296f24735a70e90e8880cdc90d",
           "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/checker_v2.py": "d24d8276955bacbe626ebe6293efe7b64c2cf36544100b60175f6d0ab80e6258",
           "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/answers_v2.py": "b0bdabfcfac656e4071f192d9bda8ff7dec8b88baf077f29131d8f94497d1bb5",
           "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/slots_v2.py": "7b9c2c3a0aca938acf0979aa7d74f1fea422726333926f079a5f8e06f5e7d2fb"}
D = "records/helm_eval_design_20260923/"
CLAUDE_FILES = [D + "hset2/hset2_build.py", D + "hset2/hset2_stage0_public.py", D + "hset2/PUBLIC_EXCLUDED_v1.json",
                D + "hset2/PUBLIC_EXCLUDED_v2.json", D + "hset2/STAGE0_DEV_SIDE_GROUPS.json", D + "hset2/STAGE0_TEST_SIDE_GROUPS.json", D + "hset2/STAGE0_SUMMARY.json",
                D + "hset1a/hset_worlds.py", D + "hset1a/hset1a_build.py", D + "hset1a/hset1b_build.py",
                D + "d1_acceptance/oracle_isomorphism.py"]
JOB_FILES = [D + "hset2_aws_job/launch.py", D + "hset2_aws_job/job.sh.template", D + "hset2_aws_job/watch.py",
             D + "hset2_aws_job/JOB_LIMITS.md"]
FORBIDDEN_NAME_PARTS = ("sealed", "_eval.jsonl", "salt.hex")


def git(*args, data=None):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), input=data, capture_output=True, check=True).stdout


def prefix():
    return git("rev-parse", "--show-prefix").decode().strip()


def tree_paths(commit):
    pre = prefix()
    names = [n for n in git("ls-tree", "-r", "-z", "--name-only", "--full-tree", commit, "--", pre).decode("utf-8").split("\0") if n]
    rel = [n[len(pre):] for n in names if n.startswith(pre)]
    keep = sorted(r for r in rel if (r.startswith(CODE_TOPS) and r.endswith(".py")) or r.startswith(DATA_DIRS) or r in DATA_FILES)
    bad = [r for r in keep if any(part in r.lower() for part in FORBIDDEN_NAME_PARTS)]
    if bad:
        raise SystemExit("BUNDLE_REFUSED: a forbidden file name would enter the bundle: %d paths" % len(bad))
    return keep


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


def source_tree():
    try:
        found = git("rev-parse", "--verify", "--quiet", SOURCE_COMMIT + "^{commit}").decode().strip()
        git("merge-base", "--is-ancestor", SOURCE_COMMIT, SOURCE_BRANCH)
    except subprocess.CalledProcessError:
        found = None
    if found != SOURCE_COMMIT:
        raise SystemExit("BUNDLE_REFUSED: %s is not a commit on %s here" % (SOURCE_COMMIT, SOURCE_BRANCH))
    tree = read_blobs(SOURCE_COMMIT, tree_paths(SOURCE_COMMIT))
    for path, pin in PINS.items():
        if path not in tree or hashlib.sha256(tree[path]).hexdigest() != pin:
            raise SystemExit("BUNDLE_REFUSED: tree/%s does not match its pinned sha256" % path)
    for path, pin in LF_PINS.items():
        if path not in tree or lf(tree[path]) != pin:
            raise SystemExit("BUNDLE_REFUSED: tree/%s does not match its pinned LF sha256" % path)
    return tree


def builder_pins(blob):
    """HSET1A_SALT_SHA256 and HSET2_SALT_SHA256 as committed in hset2_build.py (read by syntax tree, not imported)."""
    values = {}
    for node in ast.parse(blob).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("HSET1A_SALT_SHA256", "HSET2_SALT_SHA256", "SOURCE_COMMIT"):
                values[node.targets[0].id] = ast.literal_eval(node.value)
    return values


def read_salt(path, pin, name):
    salt = path.read_bytes().strip()
    if len(salt) != 64 or any(ch not in b"0123456789abcdef" for ch in salt):
        raise SystemExit("BUNDLE_REFUSED: the %s salt file is not 64 lowercase hex characters" % name)
    if hashlib.sha256(salt).hexdigest() != pin:
        raise SystemExit("BUNDLE_REFUSED: the %s salt is not the one whose sha256 was committed" % name)
    return salt


def is_hex64(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


PIN_REFUSALS = {
    "EXPECTED_TEST5_SHAPES_DIGEST": "EXPECTED_TEST5_SHAPES_DIGEST is not set (JOB_LIMITS.md, before launch)",
    "UV_TARBALL_SHA256": "UV_TARBALL_SHA256 is not set (JOB_LIMITS.md, before launch; review F9)",
    "SOURCE_COMMIT": "hset2_build.SOURCE_COMMIT differs from this launcher's",
    "HSET1A_SALT_SHA256": "hset2_build.HSET1A_SALT_SHA256 is not 64 lowercase hex characters",
    "HSET2_SALT_SHA256": "hset2_build.HSET2_SALT_SHA256 is not committed (design s3 step 6; the custodian's step)"}


def pin_refusals(builder_blob):
    """Every pin the launch needs, checked TOGETHER, so a refusal names all that are missing (no AWS call, no archive
    read). `builder_blob` is hset2_build.py as committed. Returns the list of PIN_REFUSALS keys that fail."""
    pins = builder_pins(builder_blob)
    bad = [name for name, value in (("EXPECTED_TEST5_SHAPES_DIGEST", EXPECTED_TEST5_SHAPES_DIGEST),
                                    ("UV_TARBALL_SHA256", UV_TARBALL_SHA256)) if not is_hex64(value)]
    if pins.get("SOURCE_COMMIT") != SOURCE_COMMIT:
        bad.append("SOURCE_COMMIT")
    for name in ("HSET1A_SALT_SHA256", "HSET2_SALT_SHA256"):
        if not is_hex64(pins.get(name)):
            bad.append(name)
    return bad


def assemble():
    """Checks everything that needs no salt first (uncommitted files, the pinned source tree, every pin), refusing with
    the COMPLETE list of what is missing; only then reads the two salts from the archive."""
    head = git("rev-parse", "HEAD").decode().strip()
    refusals = []
    pre = prefix()
    dirty = git("status", "--porcelain", "--", *(CLAUDE_FILES + JOB_FILES)).decode().strip()
    at_head = set(git("ls-tree", "-r", "-z", "--name-only", "--full-tree", head, "--",
                      *(pre + p for p in CLAUDE_FILES + JOB_FILES)).decode("utf-8").split("\0"))
    absent = [p for p in CLAUDE_FILES + JOB_FILES if pre + p not in at_head]
    if dirty or absent:
        refusals.append("UNCOMMITTED_BUILDER_OR_JOB_FILES: commit them first:\n" + "\n".join(
            [dirty] * bool(dirty) + ["not at HEAD: " + p for p in absent]))
    tree = source_tree()                                  # refuses by itself if the pinned tree is not reproduced
    builder = read_blobs(head, [D + "hset2/hset2_build.py"])[D + "hset2/hset2_build.py"]
    refusals += [PIN_REFUSALS[name] for name in pin_refusals(builder)]
    if refusals:
        raise SystemExit("BUNDLE_REFUSED (%d): %s" % (len(refusals), " | ".join(refusals)))
    claude = read_blobs(head, CLAUDE_FILES)
    pins = builder_pins(claude[D + "hset2/hset2_build.py"])
    salt1a = read_salt(ARCHIVE_HSET1A / "salt.hex", pins["HSET1A_SALT_SHA256"], "HSET-1A")
    salt2 = read_salt(ARCHIVE_HSET2 / "salt.hex", pins["HSET2_SALT_SHA256"], "HSET-2")
    files = {"tree/" + p: b for p, b in tree.items()}
    files.update({"claude/" + p: b for p, b in claude.items()})
    anchors = {"schema": "claude.hset2-anchors/0.1", "source_commit": SOURCE_COMMIT, "source_branch": SOURCE_BRANCH,
               "claude_commit": head, "files": {name: {"sha256": hashlib.sha256(b).hexdigest(), "sha256_lf": lf(b), "bytes": len(b)}
                                                for name, b in sorted(files.items())},
               "salt_sha256": {"hset1a": pins["HSET1A_SALT_SHA256"], "hset2": pins["HSET2_SALT_SHA256"]},
               "expected_test5_shapes_digest": EXPECTED_TEST5_SHAPES_DIGEST,
               "tools": {"uv_version": UV_VERSION, "uv_tarball_sha256": UV_TARBALL_SHA256, "python_version": PYTHON_VERSION,
                         "installed_before_the_bundle": True}}
    files["sealed/salt_hset1a.hex"] = salt1a + b"\n"
    files["sealed/salt_hset2.hex"] = salt2 + b"\n"
    files["anchors.json"] = json.dumps(anchors, indent=1, sort_keys=True).encode()
    return files, anchors, head


def materialize_tree(out):
    """Local tests only: write tree/ (the pinned CNCM tree; no salt, no claude/ files) into a NEW folder."""
    out = pathlib.Path(out).resolve()
    if out.exists():
        raise SystemExit("REFUSED: %s exists" % out)
    if any((q / ".git").exists() for q in out.parents):
        raise SystemExit("REFUSED: the folder must not be inside a git work tree")
    tree = source_tree()
    for rel, data in tree.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    record = {"source_commit": SOURCE_COMMIT, "files": len(tree),
              "tree_digest": hashlib.sha256(json.dumps({p: hashlib.sha256(b).hexdigest() for p, b in sorted(tree.items())},
                                                       sort_keys=True).encode()).hexdigest()}
    (out / "MATERIALIZED_TREE.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(record))
    return 0


def build_bundle(files):
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=6, mtime=0) as zipped, tarfile.open(fileobj=zipped, mode="w") as tar:
        for name in sorted(files):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(files[name]), 0, 0o644
            tar.addfile(info, io.BytesIO(files[name]))
    body = buffer.getvalue()
    return body, hashlib.sha256(body).hexdigest()


def worst_case_usd():
    """Machine + auto-assigned public address + gp3 disk, for the whole client deadline."""
    return (PRICE_PER_HOUR + 0.005 + ROOT_GB * 0.08 / 730) * CLIENT_DEADLINE_MINUTES / 60.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--materialize-tree", default=None)
    args = parser.parse_args()
    if args.materialize_tree:
        return materialize_tree(args.materialize_tree)
    worst_case = worst_case_usd()
    assert worst_case < DOLLAR_CEILING, "the time limit does not keep the job under the ceiling"
    # every refusal comes before boto3 is imported: a dry run makes no AWS call and creates no AWS client
    files, anchors, head = assemble()
    body, bundle_sha = build_bundle(files)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key_prefix = "helm-integration/hset2-build-%s/" % stamp
    print("bundle: %d files, %.2f MB, sha256 %s; claude commit %s; source %s" % (len(files), len(body) / 1e6, bundle_sha[:16],
                                                                             head[:8], SOURCE_COMMIT[:8]))
    template = (HERE / "job.sh.template").read_text(encoding="utf-8").replace("\r\n", "\n")
    keys = {"bundle": key_prefix + "bundle.tar.gz", "results": key_prefix + "results.tar.gz",
            "sealed": key_prefix + "sealed.tar.gz", "progress": key_prefix + "progress.log"}
    if args.dry_run:
        urls = {k: "https://DRY-RUN/%s" % v for k, v in keys.items()}
    else:
        import boto3
        s3 = boto3.client("s3", region_name=REGION)
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
              .replace("__BUNDLE_SHA256__", bundle_sha).replace("__SOURCE_COMMIT__", head)
              .replace("__EXPECT_TEST5__", EXPECTED_TEST5_SHAPES_DIGEST).replace("__PYTHON_VERSION__", PYTHON_VERSION)
              .replace("__UV_VERSION__", UV_VERSION).replace("__UV_SHA256__", UV_TARBALL_SHA256))
    assert "__" not in script.replace("__pycache__", ""), "an unfilled placeholder remains"
    assert len(script.encode("utf-8")) < 16000, "user-data limit"
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
    running = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["hset2-build-*"]},
                                              {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if running:
        raise SystemExit("LAUNCH_REFUSED: an hset2-build machine is already running")
    tags = [{"Key": "Name", "Value": "hset2-build-%s" % stamp},
            {"Key": "Purpose", "Value": "HSET-2 sealed build (Claude temporary builder, CLAUDE_BUILT_CLAUDE_CHECKED)"},
            {"Key": "SelfTerminates", "Value": "yes-%d-seconds" % MAX_SECONDS}]
    launched, last_error = None, None
    for subnet in sorted(subnets, key=lambda s: s["AvailabilityZone"]):
        existing = ec2.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["hset2-build-%s" % stamp]},
                                                  {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
        if existing:
            launched = {"Instances": existing[0]["Instances"]}
            print("a machine from an earlier zone attempt is running: using it, not launching another", flush=True)
            break
        try:
            launched = ec2.run_instances(
                ImageId=ami, InstanceType=INSTANCE_TYPE, MinCount=1, MaxCount=1, SubnetId=subnet["SubnetId"], SecurityGroupIds=[group["GroupId"]],
                InstanceInitiatedShutdownBehavior="terminate", UserData=script, ClientToken="hset2-%s-%s" % (stamp, subnet["AvailabilityZone"]),
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
    record = {"schema": "claude.hset2-launch/0.1", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
              "approved": {"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                           "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": DOLLAR_CEILING},
              "instance_id": instance["InstanceId"], "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "availability_zone": instance["Placement"]["AvailabilityZone"], "ami": ami, "ami_name": image.get("Name"),
              "root_volume_gb": ROOT_GB, "security_group": group["GroupId"], "in_instance_timer_seconds": MAX_SECONDS,
              "client_deadline_minutes": CLIENT_DEADLINE_MINUTES, "worst_case_usd_at_client_deadline": round(worst_case, 4),
              "bucket": BUCKET, "keys": keys, "python": PYTHON_VERSION, "anchors": anchors,
              "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha, "claude_commit": head,
                         "source_commit": SOURCE_COMMIT},
              "sealed_destination": str(ARCHIVE_HSET2 / ("run_" + stamp)),
              "machine_script_template_sha256_lf": hashlib.sha256(template.encode("utf-8")).hexdigest(),
              "machine_script_rendered_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
              "custody_note": ("the bundle (with both salts) and the sealed results stay in the private bucket under keys; "
                               "anyone who can read that bucket, or this machine's startup script while its links are "
                               "valid (4 hours), could rebuild TEST_NEW_5 and TEST_NEW_6. Claude does not delete them (no "
                               "permanent deletion); removing them is an owner decision"),
              "links_stored": "no -- time-limited links are never written to disk"}
    (HERE / "launch_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes." % (instance["InstanceId"], INSTANCE_TYPE,
                                                                        instance["Placement"]["AvailabilityZone"], MAX_SECONDS // 60 + 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
