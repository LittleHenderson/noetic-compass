"""Launch the Q4-SDG-1 error-panel diagnostic (directive questions 3, 4, 5-refined, 6) on ONE AWS T4 machine.

Runner: the Claude coordinator (temporary takeover, 2026-09-23). Owner authority: the Q4 directive (attached in chat,
byte copy at 8eb798a5 on research/helm-integration-20260923) and the AWS order ("use aws as there is only 354 mb of
16 gbs locally"). Limits: JOB_LIMITS.md ($1.00 ceiling, g4dn.xlarge, 45-minute machine timer, 55-minute client deadline),
as written in the ownership record Q4_SDG_TEMPORARY_OWNERSHIP_20260923.md before any Q4 code.

The bundle is built from GIT OBJECTS at one reviewed commit (--source-commit, 40 hex, on claude/q4-sdg-feedback-20260923):
  research/helm_cas_expression_lab/   top-level .py and .json files, the pinned compiler snapshot, and the PUBLIC Q3
                                      v0.7 data (manifest, baselines, visible_*.jsonl)
  records/q4_authorized_20260922/run_001/   the original run's records and checkpoint (read, never changed)
Custody: no path whose name matches *_eval.jsonl or contains "sealed" is ever bundled (checked twice). The machine
gets no credentials: one download link and two upload links, each time-limited.

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
INSTANCE_TYPE, PRICE_PER_HOUR = "g4dn.xlarge", 0.526
PINNED_AMI = "ami-07d69ce07bfe5628f"                         # the image of the T4 jobs of 2026-09-23
AMI_PARAMETER = "/aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-24.04/latest/ami-id"
ROOT_GB = 100
MAX_SECONDS, CLIENT_DEADLINE_MINUTES, DOLLAR_CEILING = 45 * 60, 55, 1.00
PANEL_WALL_SECONDS = 1800                                    # the panel's own limit, inside the machine timer
PYTHON_VERSION, TORCH_VERSION, NUMPY_VERSION = "3.14.7", "2.11.0", "2.5.2"
BRANCH = "claude/q4-sdg-feedback-20260923"
LAB = "research/helm_cas_expression_lab/"
RUN = "records/q4_authorized_20260922/run_001/"
COMPILER = LAB + "pinned_sources/compiler_pre_ohm_61ed5a45.py"
DATA = LAB + "data/q3_v0_7/"
WEIGHTS = RUN + "checkpoint/model_state.pt"
WEIGHTS_SHA256 = "d54f57155a54cbd28621d92af9cb5f45e425c015a559cf80103966ccbf275477"
SELECTION_DIGEST = "0b98bfc94a5aed8af2d4fef72378fec7dfa9d46808b09ff30f750972387a3059"   # builder's local `select`
FORBIDDEN = re.compile(r"(_eval\.jsonl$|sealed)", re.IGNORECASE)
JOB_FILES = ["launch.py", "job.sh.template", "watch.py", "JOB_LIMITS.md"]


def git(*args, data=None):
    return subprocess.run(["git", "-C", str(PACKAGE)] + list(args), input=data, capture_output=True, check=True).stdout


def prefix():
    return git("rev-parse", "--show-prefix").decode().strip()


def wanted(rel):
    name = pathlib.PurePosixPath(rel).name
    if FORBIDDEN.search(rel):
        return False
    if rel.startswith(RUN) or rel == COMPILER:
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
    for needed in (LAB + "q4_error_panel.py", LAB + "q4_sdg_curriculum.py", COMPILER, DATA + "manifest.json",
                   DATA + "visible_G_train.jsonl", DATA + "visible_G_dev.jsonl", RUN + "plan.json", RUN + "result.json",
                   RUN + "updates.jsonl", RUN + "dev_predictions.jsonl", WEIGHTS):
        if needed not in blobs:
            raise SystemExit("BUNDLE_REFUSED: %s not in the bundle" % needed)
    if hashlib.sha256(blobs[WEIGHTS]).hexdigest() != WEIGHTS_SHA256:
        raise SystemExit("BUNDLE_REFUSED: checkpoint weights differ from d54f5715")
    files = {"pkg/" + r: b for r, b in blobs.items()}
    identity = {"source_commit": commit, "branch": BRANCH, "files": len(blobs),
                "weights_sha256": WEIGHTS_SHA256, "expected_selection_digest": SELECTION_DIGEST,
                "lf_sha256": {r: hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest() for r, b in blobs.items()
                              if r.startswith(LAB) and r.endswith(".py")},
                "custody": "no *_eval.jsonl and no *sealed* path bundled (checked by name, twice)"}
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
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if len(args.source_commit) != 40:
        raise SystemExit("give the full 40-character commit")
    import boto3
    files, identity = assemble(args.source_commit)
    body, bundle_sha = build_bundle(files)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key_prefix = "q4-sdg-1/error-panel-%s/" % stamp
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
        if (HERE / "launch_record.json").exists():
            raise SystemExit("LAUNCH_REFUSED: launch_record.json already exists -- one approval, one machine")
        s3.put_object(Bucket=BUCKET, Key=keys["bundle"], Body=body)
        urls = {"bundle": s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": keys["bundle"]}, ExpiresIn=2 * 3600)}
        for k in ("results", "progress"):
            urls[k] = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": keys[k]}, ExpiresIn=2 * 3600)
    script = (template.replace("__MAX_SECONDS__", str(MAX_SECONDS)).replace("__MAX_MINUTES__", str(MAX_SECONDS // 60 + 3))
              .replace("__BUNDLE_URL__", urls["bundle"]).replace("__RESULTS_URL__", urls["results"]).replace("__PROGRESS_URL__", urls["progress"])
              .replace("__BUNDLE_SHA256__", bundle_sha).replace("__PYTHON_VERSION__", PYTHON_VERSION)
              .replace("__TORCH_VERSION__", TORCH_VERSION).replace("__NUMPY_VERSION__", NUMPY_VERSION)
              .replace("__SELECTION_DIGEST__", SELECTION_DIGEST).replace("__PANEL_WALL_SECONDS__", str(PANEL_WALL_SECONDS)))
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
    live = ec2.describe_instances(Filters=[{"Name": "instance-type", "Values": ["g4dn.*", "g5.*", "g6.*", "g6e.*", "g7.*", "p3.*", "p4d.*"]},
                                           {"Name": "instance-state-name", "Values": ["pending", "running"]}])["Reservations"]
    if live:
        raise SystemExit("LAUNCH_REFUSED: a GPU machine is already running (quota 8 vCPU; one GPU job at a time)")
    name = "q4-sdg-1-error-panel-%s" % stamp
    tags = [{"Key": "Name", "Value": name}, {"Key": "Purpose", "Value": "Q4-SDG-1 error-panel diagnostic, no optimizer; Claude coordinator; takeover 2026-09-23"},
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
                InstanceInitiatedShutdownBehavior="terminate", UserData=script, ClientToken="q4-panel-%s-%s" % (stamp, subnet["AvailabilityZone"]),
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
    record = {"schema": "claude.q4-sdg-1-error-panel-launch/0.1",
              "owner_authority": ["Q4 directive attached in chat 2026-09-23 (byte copy 8eb798a5): diagnose the error first",
                                  "AWS order 2026-09-23: 'use aws as there is only 354 mb of 16 gbs locally'",
                                  "limits written before any Q4 code in Q4_SDG_TEMPORARY_OWNERSHIP_20260923.md (0687e20a)"],
              "approved": {"machine": INSTANCE_TYPE, "region": REGION, "price_per_hour_usd": PRICE_PER_HOUR,
                           "time_limit_minutes": CLIENT_DEADLINE_MINUTES, "dollar_ceiling": DOLLAR_CEILING},
              "instance_id": instance["InstanceId"], "instance_name": name, "launched_utc": instance["LaunchTime"].strftime("%Y-%m-%dT%H:%M:%SZ"),
              "availability_zone": instance["Placement"]["AvailabilityZone"], "ami": ami, "ami_name": image.get("Name"), "ami_note": ami_note,
              "root_volume_gb": ROOT_GB, "in_instance_timer_seconds": MAX_SECONDS, "client_deadline_minutes": CLIENT_DEADLINE_MINUTES,
              "panel_wall_seconds": PANEL_WALL_SECONDS, "worst_case_usd_at_client_deadline": round(worst_case, 4),
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
