"""Launch the Q4-SDG-1 A-versus-B TRAINING comparison on ONE AWS T4 machine (g4dn.xlarge).

Runner: the Claude coordinator (temporary takeover). Owner authority: OWNER_AUTHORITY_AND_DECISIONS_20260924.md on
research/helm-integration-20260923 (keep Q4's architecture; A versus B; 3 seeds per arm declared before launch; $5.00
ceiling INCLUDING the pinned data build; one GPU machine at a time; no automatic retries; the protected examination
stays out of every loop) and the AWS order of 2026-09-23. Rules: research/helm_cas_expression_lab/q4_ab_rules.py and
Q4_SDG_AB_SPEC_v0_2.md (FROZEN_BEFORE_LAUNCH). Limits: JOB_LIMITS.md in this folder.

Refuses to launch unless, AT THE SOURCE COMMIT: the rules hash to APPROVED_FROZEN_SHA256 (the reviewed rules) and the
spec's status line is '**Status: FROZEN_BEFORE_LAUNCH** frozen_sha256 `<that hash>`'; the four decision programs and
the spec have exactly the APPROVED_LF_SHA256 bytes (LF); the frozen digests are filled in; Q4_SDG_DATA_PINS.json holds
the B package's pin for the frozen package (engine python, size 4096, seeds 20260941 and 20260951); the data build's
results/manifest.json is committed, hashes to the pinned manifest_sha256, and every source hash it recorded (the
package builder, its imports, the compiler snapshot, the Q3 files) equals the same file at the source commit (else the
T4 rebuild would stop at B_PACKAGE_MISMATCH after setup); the data-build job has a watch record, and its measured cost
plus this job's worst case fit $5.00; no GPU machine is running; this folder has no launch record yet.

The bundle is built from GIT OBJECTS at one reviewed commit (--source-commit, 40 hex, on the Q4-SDG-1 branch):
  research/helm_cas_expression_lab/   top-level .py and .json files, the spec, the pinned compiler snapshot, and the
                                      PUBLIC Q3 v0.7 data (manifest, baselines, visible_*.jsonl)
  records/q4_authorized_20260922/run_001/   the original run (Stage 0 must reproduce it on the machine first)
Custody: no path matching *_eval.jsonl, containing "sealed", or containing hset1a/hset1b is bundled (checked twice
here, again on the machine). The machine gets no credentials: one download link and two upload links.

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
DATA_BUILD = HERE.parent / "data_build_job"
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
INSTANCE_TYPE, PRICE_PER_HOUR = "g4dn.xlarge", 0.526
PINNED_AMI = "ami-07d69ce07bfe5628f"                         # the image of the T4 jobs of 2026-09-23/24
AMI_PARAMETER = "/aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-24.04/latest/ami-id"
ROOT_GB = 100
PUBLIC_IPV4_PER_HOUR, GP3_PER_GB_MONTH, HOURS_PER_MONTH = 0.005, 0.08, 730
MAX_SECONDS, CLIENT_DEADLINE_MINUTES = 225 * 60, 240
JOB_WALL_SECONDS = 11400                                      # q4_ab_train.py's own limit (= q4_ab_rules.JOB_WALL_SECONDS)
DOLLAR_CEILING = 5.00                                         # the WHOLE A-versus-B job: data build + training
DATA_BUILD_WORST_CASE_USD = 0.0813                            # data_build_job/launch.py worst case (a test checks it)
PYTHON_VERSION, TORCH_VERSION, NUMPY_VERSION = "3.14.7", "2.11.0", "2.5.2"
BRANCH = "claude/q4-sdg-feedback-20260923"
LAB = "research/helm_cas_expression_lab/"
RUN = "records/q4_authorized_20260922/run_001/"
COMPILER = LAB + "pinned_sources/compiler_pre_ohm_61ed5a45.py"
DATA = LAB + "data/q3_v0_7/"
SPEC = LAB + "Q4_SDG_AB_SPEC_v0_2.md"
WEIGHTS = RUN + "checkpoint/model_state.pt"
WEIGHTS_SHA256 = "d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477"
FORBIDDEN = re.compile(r"(_eval\.jsonl$|sealed|hset1a|hset1b)", re.IGNORECASE)
JOB_FILES = ["launch.py", "job.sh.template", "watch.py", "JOB_LIMITS.md"]
FROZEN_STATUS_LINE = re.compile(rb"^[*][*]Status: FROZEN_BEFORE_LAUNCH[*][*] frozen_sha256 `([0-9a-f]{64})`", re.MULTILINE)
DATA_BUILD_MANIFEST = "records/q4_sdg_1_20260923/data_build_job/results/manifest.json"
# The reviewed rules and programs (spec v0.2 revision 2). Any change to them after review changes these values, and
# the launch is refused until a review approves the change and this file is updated in a commit of its own.
APPROVED_FROZEN_SHA256 = "3100f37603cbc0e351cfbad2e2832bd769819d906338f7cf08966b916ee42f11"
APPROVED_LF_SHA256 = {
    LAB + "q4_ab_rules.py": "e990f76e5b9af11e6abc08b89ba1de2fb496920b4cc436299ef63af3fad011bf",
    LAB + "q4_ab_prep.py": "b0601e5382df15441526bf334fb8c548ee6a379d4b633a81adb60e40fca8fd23",
    LAB + "q4_ab_train.py": "4d793a6afed5ddf6e399fcbcfff2bb1799a28ee725ab98cf4d59578e1bce8cd4",
    LAB + "read_q4_ab_results.py": "40769840df0de81b02ebce738715dc0cf2810cc49457810d50577485c2811e60",
    SPEC: "7829d623fe7bbbb6a41252bf2177c0e73fdd2188dc8e6ae576c62afa7649018a",
}
GPU_FAMILIES = ["g4dn.*", "g5.*", "g6.*", "g6e.*", "g7.*", "p3.*", "p4d.*", "p5.*"]


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
    if rel.startswith(RUN) or rel in (COMPILER, SPEC):
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


def frozen_rules_of(blob):
    """The q4_ab_rules module AS COMMITTED (standard library only), without importing the working tree's copy."""
    namespace = {"__name__": "q4_ab_rules_at_source_commit"}
    exec(compile(blob.decode("utf-8"), "q4_ab_rules.py", "exec"), namespace)
    return namespace


def check_pin_blob(pins_blob, rules_ns):
    """The pin must exist and describe exactly the frozen B package (same checks as q4_ab_prep.read_pin_entry)."""
    frozen = rules_ns["B_PACKAGE"]
    try:
        pins = json.loads(pins_blob.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise SystemExit("LAUNCH_REFUSED: B_PACKAGE_NOT_PINNED (pin file unreadable)") from None
    entry = (pins.get("data_versions") or {}).get(frozen["schema"]) if isinstance(pins, dict) else None
    if not isinstance(entry, dict):
        raise SystemExit("LAUNCH_REFUSED: B_PACKAGE_NOT_PINNED -- run the data-build job and pin_package.py --write first")
    for key in ("engine", "size", "seed", "feedback_seed", "data_dir"):
        if entry.get(key) != frozen[key]:
            raise SystemExit("LAUNCH_REFUSED: B_PIN_NOT_THE_FROZEN_PACKAGE (%s)" % key)
    if not re.fullmatch(r"[0-9a-f]{64}", str(entry.get("manifest_sha256"))):
        raise SystemExit("LAUNCH_REFUSED: B_PIN_NOT_THE_FROZEN_PACKAGE (manifest_sha256)")
    return entry


def lf_sha256(body):
    return hashlib.sha256(body.replace(b"\r\n", b"\n")).hexdigest()


def check_frozen(blobs, approved_frozen=None, approved_lf=None):
    """The rules, the spec's status line and the decision programs must be the reviewed ones (review MINOR 3)."""
    approved_frozen = APPROVED_FROZEN_SHA256 if approved_frozen is None else approved_frozen
    approved_lf = APPROVED_LF_SHA256 if approved_lf is None else approved_lf
    if not re.fullmatch(r"[0-9a-f]{64}", approved_frozen) or any(
            not re.fullmatch(r"[0-9a-f]{64}", v) for v in approved_lf.values()):
        raise SystemExit("LAUNCH_REFUSED: the approved hashes in launch.py are not filled in")
    rules_ns = frozen_rules_of(blobs[LAB + "q4_ab_rules.py"])
    digests = rules_ns["frozen_record"]()["digests"]
    if any(value in ("TO_BE_MEASURED", -1) for value in digests.values()):
        raise SystemExit("LAUNCH_REFUSED: frozen digests are not filled in")
    if rules_ns["frozen_sha256"]() != approved_frozen:
        raise SystemExit("LAUNCH_REFUSED: FROZEN_RULES_NOT_THE_APPROVED_ONES (%s at this commit, approved %s)" % (
            rules_ns["frozen_sha256"]()[:12], approved_frozen[:12]))
    status = FROZEN_STATUS_LINE.search(blobs[SPEC])
    if not status:
        raise SystemExit("LAUNCH_REFUSED: the spec's status line is not '**Status: FROZEN_BEFORE_LAUNCH** frozen_sha256 "
                         "`<hash>`' at this commit")
    if status.group(1).decode("ascii") != approved_frozen:
        raise SystemExit("LAUNCH_REFUSED: the spec's frozen status names another frozen_sha256")
    changed = sorted(rel for rel, want in approved_lf.items() if rel not in blobs or lf_sha256(blobs[rel]) != want)
    if changed:
        raise SystemExit("LAUNCH_REFUSED: APPROVED_SOURCE_CHANGED since the review: %s" % changed)
    if rules_ns["JOB_WALL_SECONDS"] != JOB_WALL_SECONDS or JOB_WALL_SECONDS >= MAX_SECONDS:
        raise SystemExit("LAUNCH_REFUSED: the runner's wall limit must equal JOB_WALL_SECONDS and sit inside the machine timer")
    entry = check_pin_blob(blobs[LAB + "Q4_SDG_DATA_PINS.json"], rules_ns)
    return rules_ns, entry


def check_data_build_manifest(manifest_blob, blobs, entry):
    """Review MINOR 6: the T4 machine rebuilds B from the source commit, and its manifest records the LF sha256 of the
    builder's sources. Compare, at $0, what the pinned data build recorded with the same files at the source commit."""
    if lf_sha256(manifest_blob) != entry["manifest_sha256"]:
        raise SystemExit("LAUNCH_REFUSED: DATA_BUILD_MANIFEST_NOT_THE_PINNED_ONE")
    try:
        manifest = json.loads(manifest_blob.replace(b"\r\n", b"\n").decode("utf-8"))
    except (UnicodeError, ValueError):
        raise SystemExit("LAUNCH_REFUSED: the data build's manifest.json is unreadable") from None
    sources = manifest.get("sources_lf_sha256") if isinstance(manifest, dict) else None
    immutable = manifest.get("q3_immutable_lf_sha256") if isinstance(manifest, dict) else None
    if not isinstance(sources, dict) or not sources or not isinstance(immutable, dict) or not immutable:
        raise SystemExit("LAUNCH_REFUSED: the data build's manifest has no source hashes")
    differ = sorted(name for name, digest in list(sources.items()) + list(immutable.items())
                    if LAB + name not in blobs or lf_sha256(blobs[LAB + name]) != digest)
    if (manifest.get("compiler") or {}).get("sha256") != lf_sha256(blobs[COMPILER]):
        differ.append("compiler snapshot")
    if manifest.get("q3_v0_7_manifest_sha256") != lf_sha256(blobs[DATA + "manifest.json"]):
        differ.append("q3_v0_7 manifest")
    if differ:
        raise SystemExit("LAUNCH_REFUSED: B_PACKAGE_SOURCES_CHANGED_SINCE_THE_DATA_BUILD: %s (the T4 rebuild would "
                         "differ from the pin)" % differ)
    return manifest


def money_check(watch_record_path=DATA_BUILD / "watch_record.json"):
    """Measured data-build cost bound + this job's worst case must fit the $5.00 ceiling."""
    if not pathlib.Path(watch_record_path).is_file():
        raise SystemExit("LAUNCH_REFUSED: the data-build job has no watch record (run it and pin first)")
    spent = json.loads(pathlib.Path(watch_record_path).read_text(encoding="utf-8")).get("cost_upper_bound_usd")
    if not isinstance(spent, (int, float)) or spent < 0:
        raise SystemExit("LAUNCH_REFUSED: the data-build cost bound is unreadable")
    if spent + worst_case_usd() > DOLLAR_CEILING:
        raise SystemExit("LAUNCH_REFUSED: data build %.4f + training worst case %.4f exceeds %.2f" % (
            spent, worst_case_usd(), DOLLAR_CEILING))
    return spent


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
    for needed in (LAB + "q4_ab_train.py", LAB + "q4_ab_prep.py", LAB + "q4_ab_rules.py", LAB + "read_q4_ab_results.py",
                   LAB + "q4_error_panel.py", LAB + "q4_sdg_curriculum.py", LAB + "Q4_SDG_DATA_PINS.json", SPEC, COMPILER,
                   DATA + "manifest.json", DATA + "visible_G_train.jsonl", DATA + "visible_G_dev.jsonl",
                   DATA + "visible_R_dev.jsonl", RUN + "plan.json", RUN + "result.json", RUN + "updates.jsonl",
                   RUN + "dev_predictions.jsonl", WEIGHTS):
        if needed not in blobs:
            raise SystemExit("BUNDLE_REFUSED: %s not in the bundle" % needed)
    if hashlib.sha256(blobs[WEIGHTS]).hexdigest() != WEIGHTS_SHA256:
        raise SystemExit("BUNDLE_REFUSED: checkpoint weights differ from d54f5715")
    rules_ns, entry = check_frozen(blobs)
    try:
        manifest_blob = read_blobs(commit, [DATA_BUILD_MANIFEST])[DATA_BUILD_MANIFEST]
    except SystemExit:
        raise SystemExit("LAUNCH_REFUSED: commit data_build_job/results/manifest.json with the pin; it is missing at "
                         "%s" % commit[:8]) from None
    check_data_build_manifest(manifest_blob, blobs, entry)
    files = {"pkg/" + r: b for r, b in blobs.items()}
    identity = {"source_commit": commit, "branch": BRANCH, "files": len(blobs), "weights_sha256": WEIGHTS_SHA256,
                "b_package_pin": {k: entry[k] for k in ("manifest_sha256", "engine", "size", "seed", "feedback_seed")},
                "frozen_sha256": rules_ns["frozen_sha256"](), "approved_frozen_sha256": APPROVED_FROZEN_SHA256,
                "approved_lf_sha256": APPROVED_LF_SHA256,
                "data_build_manifest_lf_sha256": lf_sha256(manifest_blob),
                "lf_sha256": {r: hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest() for r, b in blobs.items()
                              if r.startswith(LAB) and r.endswith((".py", ".json", ".md"))},
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
    if (HERE / "launch_record.json").exists():
        raise SystemExit("LAUNCH_REFUSED: launch_record.json already exists -- one approval, one machine, no retry")
    spent = money_check()
    import boto3
    files, identity = assemble(args.source_commit)
    body, bundle_sha = build_bundle(files)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key_prefix = "q4-sdg-1/ab-%s/" % stamp
    print("bundle: %d files, %.2f MB, sha256 %s; source %s" % (len(files), len(body) / 1e6, bundle_sha[:16], args.source_commit[:8]))
    template = (HERE / "job.sh.template").read_text(encoding="utf-8").replace("\r\n", "\n")
    keys = {"bundle": key_prefix + "bundle.tar.gz", "results": key_prefix + "results.tar.gz", "progress": key_prefix + "progress.log"}
    s3 = boto3.client("s3", region_name=REGION)
    ec2 = boto3.client("ec2", region_name=REGION)
    try:
        image = ec2.describe_images(ImageIds=[PINNED_AMI])["Images"][0]
        ami, ami_note = PINNED_AMI, "pinned image"
    except Exception as error:  # noqa: BLE001 -- the pinned image may be retired: record the substitute
        ami = boto3.client("ssm", region_name=REGION).get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
        image = ec2.describe_images(ImageIds=[ami])["Images"][0]
        ami_note = "SUBSTITUTE: pinned %s unavailable (%s)" % (PINNED_AMI, type(error).__name__)
    print("image: %s (%s) %s" % (ami, image.get("Name"), ami_note))
    if args.dry_run:
        urls = {k: "https://DRY-RUN/%s" % v for k, v in keys.items()}
    else:
        s3.put_object(Bucket=BUCKET, Key=keys["bundle"], Body=body)
        urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=5 * 3600)}
        for k in ("results", "progress"):
            urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=5 * 3600)
    script = fill(template, {"MAX_SECONDS": MAX_SECONDS, "MAX_MINUTES": MAX_SECONDS // 60 + 3,
                             "BUNDLE_URL": urls["bundle"], "RESULTS_URL": urls["results"],
                             "PROGRESS_URL": urls["progress"], "BUNDLE_SHA256": bundle_sha,
                             "PYTHON_VERSION": PYTHON_VERSION, "TORCH_VERSION": TORCH_VERSION,
                             "NUMPY_VERSION": NUMPY_VERSION, "JOB_WALL_SECONDS": JOB_WALL_SECONDS})
    if args.dry_run:
        (HERE / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded or launched. Worst case %.4f USD; with the data build %.4f (ceiling %.2f)." % (
            worst_case_usd(), worst_case_usd() + spent, DOLLAR_CEILING))
        return 0
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        raise SystemExit("LAUNCH_REFUSED: the default security group allows inbound traffic from an address range")
    live = ec2.describe_instances(Filters=[{"Name": "instance-type", "Values": GPU_FAMILIES},
                                           {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if live:
        raise SystemExit("LAUNCH_REFUSED: a GPU machine is already running (quota 8 vCPU; one GPU job at a time)")
    name = "q4-sdg-1-ab-%s" % stamp
    tags = [{"Key": "Name", "Value": name}, {"Key": "Purpose", "Value": "Q4-SDG-1 A-versus-B training comparison; Claude coordinator; takeover 2026-09-23"},
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
                InstanceInitiatedShutdownBehavior="terminate", UserData=script, ClientToken="q4-ab-%s-%s" % (stamp, subnet["AvailabilityZone"]),
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
    record = {"schema": "claude.q4-sdg-1-ab-launch/0.2",
              "owner_authority": ["OWNER_AUTHORITY_AND_DECISIONS_20260924.md: A versus B, 3 seeds per arm, $5.00 ceiling "
                                  "including the pinned data build, one GPU machine, no automatic retries",
                                  "AWS order 2026-09-23: 'use aws as there is only 354 mb of 16 gbs locally'"],
              "approved": {"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                           "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling_whole_ab_job": DOLLAR_CEILING},
              "data_build_cost_upper_bound_usd": spent,
              "instance_id": instance["InstanceId"], "instance_name": name, "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "availability_zone": instance["Placement"]["AvailabilityZone"], "ami": ami, "ami_name": image.get("Name"), "ami_note": ami_note,
              "root_volume_gb": ROOT_GB, "in_instance_timer_seconds": MAX_SECONDS, "client_deadline_minutes": CLIENT_DEADLINE_MINUTES,
              "runner_wall_seconds": JOB_WALL_SECONDS, "worst_case_usd_at_client_deadline": round(worst_case_usd(), 4),
              "bucket": BUCKET, "keys": keys, "python": PYTHON_VERSION, "torch": TORCH_VERSION, "numpy": NUMPY_VERSION,
              "identity": identity, "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha},
              "machine_script_template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
              "label": "CLAUDE_BUILT_CLAUDE_CHECKED", "links_stored": "no -- time-limited links are never written to disk"}
    (HERE / "launch_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes." % (instance["InstanceId"], INSTANCE_TYPE,
                                                                        instance["Placement"]["AvailabilityZone"], MAX_SECONDS // 60 + 3))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
