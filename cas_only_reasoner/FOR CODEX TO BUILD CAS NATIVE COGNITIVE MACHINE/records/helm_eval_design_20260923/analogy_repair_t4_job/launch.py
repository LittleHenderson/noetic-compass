"""Launch the HELM-ANALOGY-REPAIR-1 item-1 acceptance job (prereg amendments A3 + A4) on ONE AWS T4 machine.

Runner: the Claude coordinator (temporary takeover, 2026-09-23). Owner authority: the takeover instruction in chat
("Complete the required historical OFF-control and ON-effect checks"; "Follow my current AWS preference and the
actual standing authorization, job limits and cleanup requirements") and the AWS order ("use aws ..."). Limits are in
JOB_LIMITS.md and are the same as the previous T4 job's ($3.00 ceiling, g4dn.2xlarge, 150/160 minutes).

The bundle is built from GIT OBJECTS only (no working files):
  frozen/    CNCM tree at 20208c92 (the unchanged Helm 2.0 source), plus the 6 Helm 2.0 checkpoints
  repaired/  CNCM tree at R (the reviewed read-only-switch commit), plus the switch tests, their fixtures and the
             same 6 checkpoints
  claude/    the probe v0.2, preservation_digest.py (both from this branch's HEAD) and switch_read_only_check.py
  _wheels/   the two local wheels, hash-checked
R must be passed explicitly (--repaired-commit, 40 hex) and must be on claude/helm-builder-continuation-20260923.
Inside the bundle scope, R may differ from 20208c92 in EXISTING code only in pointer_learner.py (added files allowed).

    python launch.py --repaired-commit <sha> [--dry-run]
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
import sys
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = HERE.parents[2]
REGION, BUCKET = "us-west-2", "cas-harness-runpod-92754088"
INSTANCE_TYPE, PRICE_PER_HOUR = "g4dn.2xlarge", 0.752
PINNED_AMI = "ami-07d69ce07bfe5628f"                         # the T4 reference job's image (A4.5)
AMI_PARAMETER = "/aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-24.04/latest/ami-id"
ROOT_GB = 100
MAX_SECONDS, CLIENT_DEADLINE_MINUTES, DOLLAR_CEILING = 150 * 60, 160, 3.00
PYTHON_VERSION, TORCH_VERSION, NUMPY_VERSION = "3.14.7", "2.11.0", "2.5.2"
WHEEL_DIR = pathlib.Path("C:/Users/wakil/AppData/Local/Temp/claude/rdcjt_wheels")
WHEELS = {"casformer_reference-0.1.0-py3-none-any.whl": "0487363cc7258c0e07ad65d137987088e01d5b95fc637cb0d63cfe41fd65d2ee",
          "cas_neural_cjt-0.2.0-py3-none-any.whl": "6f1ceac9140027a14cecc79fb399ef90a993cd0bd411e47970798860c4217ac9"}
ORIGINAL = "20208c923d41c24614504d4ecc2b289ecb66eda8"
BUILDER_BRANCH = "claude/helm-builder-continuation-20260923"
CODE_TOPS = ("cncm/", "research/")
DATA_DIRS = ("records/typed_course_001/", "records/typed_matched_001/development_001/", "schemas/", "spec/")
DATA_FILES = ("records/typed_interface_001/checks_002/training_tokenizer.json", "records/typed_practice_001/evaluate_gates.py",
              "pyproject.toml")
TEST_FILES = ("tests/test_helm_analogy_focus_comparison.py", "tests/test_helm_analogy_switch_read_only.py",
              "records/helm_integrated_repairs_20260923/analogy_tensor_inventory.json")
TEST_DIRS = ("records/helm_failure_research_20260922/agents/A2/source_copies/helm2/",)
SEEDS = ("20260917", "20260918", "20260919")
CHECKPOINTS = ["records/typed_pointer_001/receipt_%s/checkpoints/%s" % (s, n) for s in SEEDS for n in ("initial.pt", "final.pt")]
D = "records/helm_eval_design_20260923/"
CLAUDE_FILES = [D + "analogy_wiring_probe/analogy_wiring_probe_v0_2.py", D + "analogy_wiring_probe/preservation_digest.py",
                D + "analogy_repair_t4_job/switch_read_only_check.py",
                D + "analogy_wiring_probe/PREREG_ANALOGY_WIRING_PROBE_v0_2.md"]   # the probe hashes it beside itself (attempt 1 crashed without it)
JOB_FILES = [D + "analogy_repair_t4_job/launch.py", D + "analogy_repair_t4_job/job.sh.template", D + "analogy_repair_t4_job/watch.py",
             D + "analogy_repair_t4_job/read_results.py", D + "analogy_repair_t4_job/JOB_LIMITS.md",
             D + "analogy_wiring_probe/PREREG_ANALOGY_WIRING_PROBE_v0_2.md"]
PINS = {"records/typed_course_001/checks_002/public_course.json": "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987",
        "records/typed_interface_001/checks_002/training_tokenizer.json": "bee9ab50688eb7ca4e63780810bf280bb1490fd58a1bc25f93f1ac24d19e533c",
        "records/typed_matched_001/development_001/compact_development.json": "5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4"}
LEARNER = "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py"


def git(*args, data=None):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), input=data, capture_output=True, check=True).stdout


def prefix():
    return git("rev-parse", "--show-prefix").decode().strip()


def tree_paths(commit, extra_files=(), extra_dirs=()):
    pre = prefix()
    names = [n for n in git("ls-tree", "-r", "-z", "--name-only", "--full-tree", commit, "--", pre).decode("utf-8").split("\0") if n]
    rel = [n[len(pre):] for n in names if n.startswith(pre)]
    return sorted(r for r in rel if (r.startswith(CODE_TOPS) and r.endswith(".py")) or r.startswith(DATA_DIRS + tuple(extra_dirs))
                  or r in DATA_FILES or r in extra_files)


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


def verify_commit(c):
    try:
        found = git("rev-parse", "--verify", "--quiet", c + "^{commit}").decode().strip()
    except subprocess.CalledProcessError:
        found = None
    if found != c:
        raise SystemExit("BUNDLE_REFUSED: commit %s not found" % c)


def assemble(repaired):
    head = git("rev-parse", "HEAD").decode().strip()
    for c in (ORIGINAL, repaired):
        verify_commit(c)
    try:
        git("merge-base", "--is-ancestor", repaired, BUILDER_BRANCH)
    except subprocess.CalledProcessError:
        raise SystemExit("BUNDLE_REFUSED: %s is not on %s" % (repaired, BUILDER_BRANCH))
    dirty = git("status", "--porcelain", "--", *(CLAUDE_FILES + JOB_FILES)).decode().strip()
    if dirty:
        raise SystemExit("BUNDLE_REFUSED: commit the job files first:\n" + dirty)
    frozen_paths = tree_paths(ORIGINAL)
    repaired_paths = tree_paths(repaired, TEST_FILES, TEST_DIRS)
    frozen, rep = read_blobs(ORIGINAL, frozen_paths), read_blobs(repaired, repaired_paths)
    changed = sorted(p for p in set(frozen) & set(rep) if frozen[p] != rep[p])
    if changed != [LEARNER]:
        raise SystemExit("BUNDLE_REFUSED: R differs from 20208c92 in existing bundled code beyond pointer_learner.py: %s" % changed[:20])
    missing = [p for p in TEST_FILES if p not in rep]
    if missing:
        raise SystemExit("BUNDLE_REFUSED: test files missing at R: %s" % missing)
    for tree, name in ((frozen, "frozen"), (rep, "repaired")):
        for path, pin in PINS.items():
            if hashlib.sha256(tree[path]).hexdigest() != pin:
                raise SystemExit("BUNDLE_REFUSED: %s/%s does not match its pin" % (name, path))
    checkpoints = read_blobs(head, CHECKPOINTS)
    reference = json.loads((HERE.parent / "aws_probe_job" / "launch_record.json").read_text(encoding="utf-8"))["checkpoint_sha256"]
    for p, b in checkpoints.items():
        if hashlib.sha256(b).hexdigest() != reference[p]:
            raise SystemExit("BUNDLE_REFUSED: checkpoint %s differs from the T4 reference job's" % p)
    claude = read_blobs(head, CLAUDE_FILES)
    # Every file a bundled tool reads beside itself (HERE / "<name>") must be in the bundle: attempt 1 lost its probe
    # verdicts because PREREG_ANALOGY_WIRING_PROBE_v0_2.md was missing next to the probe.
    names = {pathlib.PurePosixPath(p).name for p in claude}
    for p, b in claude.items():
        for needed in re.findall(rb'HERE / "([^"]+)"', b):
            if needed.decode() not in names:
                raise SystemExit("BUNDLE_REFUSED: %s reads %s beside itself, which is not bundled" % (p, needed.decode()))
    for name, digest in WHEELS.items():
        if hashlib.sha256((WHEEL_DIR / name).read_bytes()).hexdigest() != digest:
            raise SystemExit("BUNDLE_REFUSED: wheel %s hash mismatch" % name)
    files = {}
    files.update({"frozen/" + p: b for p, b in frozen.items()})
    files.update({"frozen/" + p: b for p, b in checkpoints.items()})
    files.update({"repaired/" + p: b for p, b in rep.items()})
    files.update({"repaired/" + p: b for p, b in checkpoints.items()})
    files.update({"claude/" + pathlib.PurePosixPath(p).name: b for p, b in claude.items()})
    files.update({"_wheels/" + n: (WHEEL_DIR / n).read_bytes() for n in WHEELS})
    identity = {"original_commit": ORIGINAL, "repaired_commit": repaired, "claude_commit": head,
                "learner_sha256_raw": {"frozen": hashlib.sha256(frozen[LEARNER]).hexdigest(), "repaired": hashlib.sha256(rep[LEARNER]).hexdigest()},
                "learner_sha256_lf": {"frozen": hashlib.sha256(frozen[LEARNER].replace(b"\r\n", b"\n")).hexdigest(),
                                      "repaired": hashlib.sha256(rep[LEARNER].replace(b"\r\n", b"\n")).hexdigest()},
                "test_files_sha256": {p: hashlib.sha256(rep[p]).hexdigest() for p in TEST_FILES},
                "claude_files_sha256_lf": {p: hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest() for p, b in claude.items()},
                "checkpoint_sha256": {p: hashlib.sha256(b).hexdigest() for p, b in checkpoints.items()},
                "changed_existing_files_vs_original": changed}
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repaired-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if len(args.repaired_commit) != 40:
        raise SystemExit("give the full 40-character commit")
    import boto3
    files, identity = assemble(args.repaired_commit)
    body, bundle_sha = build_bundle(files)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key_prefix = "helm-integration/analogy-repair-t4-%s/" % stamp
    print("bundle: %d files, %.2f MB, sha256 %s; R %s; changed vs original: %s" % (len(files), len(body) / 1e6, bundle_sha[:16],
                                                                                   args.repaired_commit[:8], identity["changed_existing_files_vs_original"]))
    template = (HERE / "job.sh.template").read_text(encoding="utf-8").replace("\r\n", "\n")
    keys = {"bundle": key_prefix + "bundle.tar.gz", "results": key_prefix + "results.tar.gz", "progress": key_prefix + "progress.log"}
    s3 = boto3.client("s3", region_name=REGION)
    ec2 = boto3.client("ec2", region_name=REGION)
    try:
        image = ec2.describe_images(ImageIds=[PINNED_AMI])["Images"][0]
        ami, ami_note = PINNED_AMI, "pinned reference image"
    except Exception as error:  # noqa: BLE001 -- the pinned image may be retired: record the substitute (A4.5)
        ami = boto3.client("ssm", region_name=REGION).get_parameter(Name=AMI_PARAMETER)["Parameter"]["Value"]
        image = ec2.describe_images(ImageIds=[ami])["Images"][0]
        ami_note = "SUBSTITUTE: pinned %s unavailable (%s)" % (PINNED_AMI, type(error).__name__)
    print("image: %s (%s) %s" % (ami, image.get("Name"), ami_note))
    if args.dry_run:
        urls = {k: "https://DRY-RUN/%s" % v for k, v in keys.items()}
    else:
        if (HERE / "launch_record.json").exists():
            raise SystemExit("LAUNCH_REFUSED: launch_record.json already exists -- one approval, one machine")
        s3.put_object(Bucket=BUCKET, Key=keys["bundle"], Body=body)
        urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=4 * 3600)}
        for k in ("results", "progress"):
            urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=4 * 3600)
    script = (template.replace("__MAX_SECONDS__", str(MAX_SECONDS)).replace("__MAX_MINUTES__", str(MAX_SECONDS // 60 + 3))
              .replace("__BUNDLE_URL__", urls["bundle"]).replace("__RESULTS_URL__", urls["results"]).replace("__PROGRESS_URL__", urls["progress"])
              .replace("__BUNDLE_SHA256__", bundle_sha).replace("__PYTHON_VERSION__", PYTHON_VERSION)
              .replace("__TORCH_VERSION__", TORCH_VERSION).replace("__NUMPY_VERSION__", NUMPY_VERSION))
    assert "__" not in script.replace("__pycache__", ""), "an unfilled placeholder remains"
    assert len(script.encode("utf-8")) < 16000, "user-data limit"
    worst_case = (PRICE_PER_HOUR + 0.005 + ROOT_GB * 0.08 / 730) * CLIENT_DEADLINE_MINUTES / 60.0
    assert worst_case < DOLLAR_CEILING
    if args.dry_run:
        (HERE / "dry_run_machine_script.sh").write_text(script, encoding="utf-8", newline="\n")
        print("DRY RUN: nothing uploaded or launched. Worst case %.2f USD (ceiling %.2f)." % (worst_case, DOLLAR_CEILING))
        return 0
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    offered = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]}
    subnets = [s for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
               if s["AvailabilityZone"] in offered and s["MapPublicIpOnLaunch"]]
    group = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "group-name", "Values": ["default"]}])["SecurityGroups"][0]
    if [p for p in group["IpPermissions"] if p.get("IpRanges") or p.get("Ipv6Ranges")]:
        raise SystemExit("LAUNCH_REFUSED: the default security group allows inbound traffic from an address range")
    live = ec2.describe_instances(Filters=[{"Name": "instance-type", "Values": ["g4dn.*", "g5.*", "g6.*", "g6e.*", "p3.*", "p4d.*"]},
                                           {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if live:
        raise SystemExit("LAUNCH_REFUSED: a GPU machine is already running (quota 8 vCPU; one T4 at a time)")
    name = "helm-analogy-repair-t4-%s" % stamp
    tags = [{"Key": "Name", "Value": name}, {"Key": "Purpose", "Value": "HELM-ANALOGY-REPAIR-1 item 1 (A3+A4); Claude coordinator; takeover 2026-09-23"},
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
                InstanceInitiatedShutdownBehavior="terminate", UserData=script, ClientToken="helm-t4-%s-%s" % (stamp, subnet["AvailabilityZone"]),
                MetadataOptions={"HttpTokens": "required"},
                BlockDeviceMappings=[{"DeviceName": image["RootDeviceName"], "Ebs": {"VolumeSize": ROOT_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
                TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}])
            break
        except Exception as error:  # noqa: BLE001
            last_error = "%s: %s" % (subnet["AvailabilityZone"], str(error)[:200])
            print("launch in %s refused: %s" % (subnet["AvailabilityZone"], str(error)[:160]), flush=True)
    if launched is None:
        raise SystemExit("LAUNCH_FAILED in every zone; last error %s" % last_error)
    instance = launched["Instances"][0]
    record = {"schema": "claude.analogy-repair-t4-launch/0.1",
              "owner_authority": ["takeover instruction in chat 2026-09-23: 'Complete the required historical OFF-control and ON-effect checks'",
                                  "AWS order 2026-09-23: 'use aws as there is only 354 mb of 16 gbs locally'"],
              "approved": {"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                           "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": DOLLAR_CEILING},
              "instance_id": instance["InstanceId"], "instance_name": name, "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "availability_zone": instance["Placement"]["AvailabilityZone"], "ami": ami, "ami_name": image.get("Name"), "ami_note": ami_note,
              "root_volume_gb": ROOT_GB, "in_instance_timer_seconds": MAX_SECONDS, "client_deadline_minutes": CLIENT_DEADLINE_MINUTES,
              "worst_case_usd_at_client_deadline": round(worst_case, 4), "bucket": BUCKET, "keys": keys,
              "python": PYTHON_VERSION, "torch": TORCH_VERSION, "numpy": NUMPY_VERSION, "wheels": WHEELS, "identity": identity,
              "bundle": {"files": len(files), "bytes": len(body), "sha256": bundle_sha},
              "machine_script_template_sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
              "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
              "links_stored": "no -- time-limited links are never written to disk"}
    (HERE / "launch_record.json").write_text(json.dumps(record, indent=1), encoding="utf-8", newline="\n")
    print("LAUNCHED %s (%s, %s). It destroys itself within %d minutes." % (instance["InstanceId"], INSTANCE_TYPE,
                                                                        instance["Placement"]["AvailabilityZone"], MAX_SECONDS // 60 + 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
