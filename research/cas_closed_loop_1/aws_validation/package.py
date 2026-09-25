"""Freeze one public CPU validation package locally. Does not contact AWS."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import uuid
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUNTIME_COMMIT = "8182ad52b4468f18f140837dffee0e7debcfe786"
LANE = "research/cas_closed_loop_1/"
RUNTIME_FILES = Path("D:/tksCAS-worktrees/helm-integration")
READINESS = Path("D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination/AWS_READINESS_20260925.json")
GIT_VERSION = "1:2.43.0-1ubuntu7.3"
GIT_PACKAGES = [
    {"filename": "git_2.43.0-1ubuntu7.3_amd64.deb", "bytes": 3679758,
     "sha256": "099bb129f543adc4c14203334b0fa0a909f8bf038c4d56bc9cc7c774ebf78f87"},
    {"filename": "git-man_2.43.0-1ubuntu7.3_all.deb", "bytes": 1100178,
     "sha256": "5701f931ed2cd30644700b0fc1cda7c2214f93a63ef84c0c80e43ce40d2cf1d2"},
]
PINS = {
    "pip": "25.2", "pytest": "9.0.2", "pydantic": "2.12.5", "pydantic_core": "2.41.5",
    "annotated-types": "0.7.0", "typing_extensions": "4.15.0", "typing-inspection": "0.4.2",
    "pluggy": "1.6.0", "packaging": "25.0", "iniconfig": "2.3.0", "pygments": "2.19.2",
    "boto3": "1.43.87", "botocore": "1.43.87", "jmespath": "1.1.0", "s3transfer": "0.19.2",
    "python-dateutil": "2.9.0.post0", "six": "1.17.0", "urllib3": "2.6.2",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def git(*args):
    import os
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1")
    return subprocess.check_output(["git", "-c", "core.longpaths=true", "-c",
            "safe.directory=" + REPO.as_posix(), "-C", str(REPO), *args], env=env, timeout=30)


def download(directory):
    directory.mkdir(exist_ok=False)
    subprocess.run([sys.executable, "-m", "pip", "download", "--disable-pip-version-check",
                    "--retries", "0", "--timeout", "30", "--only-binary=:all:", "--no-deps",
                    "--platform", "manylinux2014_x86_64", "--python-version", "312", "--implementation", "cp",
                    "--abi", "cp312", "--dest", str(directory),
                    *[f"{name}=={version}" for name, version in PINS.items()]], check=True, timeout=300)


def freeze(wheelhouse, source, expected_tests, authorization_file, authorization_sha256):
    if re.fullmatch(r"[0-9a-f]{40}", source) is None or git("cat-file", "-t", source).decode().strip() != "commit":
        raise ValueError("EXACT_SCIENTIFIC_SOURCE_REQUIRED")
    operational_commit = git("rev-parse", "HEAD").decode().strip()
    if source != operational_commit:
        raise ValueError("FREEZE_NEW_COMMITTED_HEAD_EXPLICITLY")
    if source in {"318b22ad01304f80ed0f539420792cc951fe297a", "8f55cc3a462e438bcf706d7b64ddf9171d218039", "5f16e9fde60eab0838da1b6b57515227c212c1b4"}:
        raise ValueError("SUPERSEDED_LANE_A_SOURCE_NOT_ACCEPTED")
    if expected_tests < 47:
        raise ValueError("PREDECLARE_ALL_FOCUSED_AND_NEW_REGRESSION_CASES")
    directive = authorization_file.read_bytes()
    if sha(directive) != authorization_sha256:
        raise ValueError("OWNER_DIRECTIVE_CHANGED")
    payload = {}
    objects = {}
    object_rows = {}
    commit_cache = {}
    def include_object(kind, raw, oid, purpose):
        packed = (kind + " " + str(len(raw)) + "\0").encode() + raw
        if hashlib.sha1(packed).hexdigest() != oid:
            raise ValueError("ORIGINAL_GIT_OBJECT_IDENTITY_DIFFERS:" + purpose)
        objects[".git/objects/" + oid[:2] + "/" + oid[2:]] = zlib.compress(packed)
        object_rows[oid] = {"oid": oid, "type": kind, "bytes": len(raw), "sha256": sha(raw), "purpose": purpose}
    tree_cache = {}
    def include_path(commit, path, raw):
        if commit not in commit_cache:
            commit_cache[commit] = git("cat-file", "commit", commit)
        commit_raw = commit_cache[commit]
        include_object("commit", commit_raw, commit, "original exact commit")
        tree_oid = commit_raw.splitlines()[0].decode().removeprefix("tree ")
        parts = path.split("/")
        for depth, part in enumerate(parts):
            if tree_oid not in tree_cache:
                tree_raw = git("cat-file", "tree", tree_oid)
                include_object("tree", tree_raw, tree_oid, "ancestor metadata for allowlisted paths; sibling blobs absent")
                entries = {}
                cursor = 0
                while cursor < len(tree_raw):
                    mode_end = tree_raw.index(b" ", cursor)
                    name_end = tree_raw.index(b"\0", mode_end)
                    mode = tree_raw[cursor:mode_end].decode()
                    name = tree_raw[mode_end + 1:name_end].decode("utf-8")
                    oid = tree_raw[name_end + 1:name_end + 21].hex()
                    entries[name] = (mode, oid)
                    cursor = name_end + 21
                tree_cache[tree_oid] = entries
            mode, oid = tree_cache[tree_oid][part]
            if depth == len(parts) - 1:
                if mode not in {"100644", "100755"}:
                    raise ValueError("PUBLIC_REGULAR_BLOB_REQUIRED:" + path)
                include_object("blob", raw, oid, path)
            else:
                if mode not in {"40000", "040000"}:
                    raise ValueError("TREE_ANCESTOR_REQUIRED:" + path)
                tree_oid = oid
    names = git("ls-tree", "-r", "--name-only", source, "--", LANE).decode().splitlines()
    excluded_job_paths = []
    for name in names:
        if not name.startswith(LANE) or "/.." in name:
            raise ValueError("OUTSIDE_PUBLIC_LANE")
        if name.startswith(LANE + "aws_validation/jobs/"):
            excluded_job_paths.append(name)
            continue
        raw = git("show", source + ":" + name)
        payload[name] = raw
        include_path(source, name, raw)
    bindings = json.loads(payload[LANE + "SOURCE_BINDINGS.json"])
    if bindings["runtime_commit"] != RUNTIME_COMMIT:
        raise ValueError("HISTORICAL_RUNTIME_BINDING_MUST_NOT_CHANGE")
    for row in bindings["files"]:
        path = RUNTIME_FILES / row["source"]
        raw = path.read_bytes() if path.is_file() else b""
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raw = git("show", bindings["runtime_commit"] + ":" + row["source"])
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise ValueError("RUNTIME_BYTES_DIFFER:" + row["destination"])
        relative = Path(row["destination"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("UNSAFE_RUNTIME_DESTINATION")
        # Bootstrap on the instance must materialize this original blob itself.
        include_path(RUNTIME_COMMIT, row["source"], raw)
    if len(bindings["files"]) != 108:
        raise ValueError("EXPECTED_108_RUNTIME_FILES")
    for name in ("worker.py", "package.py", "launch.py"):
        if payload.get(LANE + "aws_validation/" + name) != (HERE / name).read_bytes():
            raise ValueError("COMMIT_OPERATIONAL_SOURCE_BEFORE_FREEZE:" + name)
    payload.update(objects)
    payload[".git/config"] = b"[core]\nrepositoryformatversion = 0\nbare = false\nfilemode = false\nlogallrefupdates = false\n"
    payload[".git/HEAD"] = (source + "\n").encode()
    payload[".git/refs/heads/public-validation"] = (source + "\n").encode()
    payload[".git/shallow"] = (source + "\n" + RUNTIME_COMMIT + "\n").encode()
    partial_git = {"status": "EXPLICITLY_PARTIAL_PUBLIC_OBJECT_STORE", "source_commit": source,
                   "runtime_commit": RUNTIME_COMMIT, "objects": list(object_rows.values()),
                   "excluded_prefixes": [LANE + "aws_validation/jobs/"],
                   "excluded_job_paths": excluded_job_paths,
                   "boundary": "Original exact objects only. Necessary ancestor tree metadata includes sibling names; unrelated child objects and protected blobs are absent. No connected-history, fsck-complete or clone-complete claim. No remote, replace refs, grafts, lazy fetch or synthesized commit."}
    payload["public_git_objects.json"] = canonical(partial_git)
    for row in GIT_PACKAGES:
        url = "https://archive.ubuntu.com/ubuntu/pool/main/g/git/" + row["filename"]
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read(row["bytes"] + 1)
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise ValueError("PINNED_UBUNTU_GIT_PACKAGE_CHANGED")
        payload["system-packages/" + row["filename"]] = raw
    wheels = sorted(wheelhouse.glob("*.whl"))
    normalized = lambda value: re.sub(r"[-_.]+", "_", value).lower()
    actual = {}
    for wheel in wheels:
        parts = wheel.name.split("-")
        name, version = normalized(parts[0]), parts[1]
        if name in actual:
            raise ValueError("DUPLICATE_WHEEL")
        actual[name] = version
        payload["wheelhouse/" + wheel.name] = wheel.read_bytes()
    if actual != {normalized(k): v for k, v in PINS.items()}:
        raise ValueError("EXACT_WHEEL_SET_REQUIRED")
    lock = []
    for name, version in PINS.items():
        wheel = next(w for w in wheels if normalized(w.name.split("-")[0]) == normalized(name))
        lock.append(f"{name}=={version} --hash=sha256:{sha(wheel.read_bytes())}")
    payload["requirements.lock"] = ("\n".join(lock) + "\n").encode()
    inventory = [{"path": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in sorted(payload.items())]
    manifest = {"schema": "cas.cpu.payload/2", "source_commit": source,
                "runtime_commit": bindings["runtime_commit"], "runtime_files": 108,
                "files": inventory, "dependencies": PINS, "expected_tests": expected_tests,
                "git_object_store": "EXPLICITLY_PARTIAL_PUBLIC_OBJECT_STORE", "git_version": GIT_VERSION,
                "git_packages": GIT_PACKAGES}
    payload["payload_manifest.json"] = canonical(manifest)
    job = "cas-cpu-v2-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    directory = HERE / "jobs" / job
    directory.mkdir(parents=True, exist_ok=False)
    archive = directory / "payload.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as stream:
        for name, raw in sorted(payload.items()):
            item = zipfile.ZipInfo(name, date_time=(2026, 9, 25, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            stream.writestr(item, raw)
    readiness = READINESS.read_bytes()
    (directory / "readiness_reference.json").write_bytes(readiness)
    (directory / "owner_directive.md").write_bytes(directive)
    plan = {
        "schema": "cas.cpu.aws.freeze/2", "job_id": job, "runner": "Codex", "source_commit": source,
        "operational_commit": operational_commit, "owner_directive_reference": str(authorization_file.resolve()),
        "owner_directive_sha256": sha(directive),
        "source_branch": git("branch", "--show-current").decode().strip(),
        "historical_tested_implementation_commit": "8f55cc3a462e438bcf706d7b64ddf9171d218039",
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "account_id": "807562639912",
        "sdk_profile": "default", "region": "us-west-2", "zone": "us-west-2a",
        "ami": "ami-07a134137a631b892", "instance_type": "t3.small", "cpu_credits": "standard",
        "subnet_id": "subnet-0bb8fa82c2a7177b3", "vpc_id": "vpc-0df2f8cc1b9f23838",
        "root_device": "/dev/sda1", "root_gib": 8, "root_type": "gp3", "root_encrypted": True,
        "root_delete_on_termination": True, "jobs": 1, "retry_count": 0,
        "permitted_concurrent_helm": {
            "instance_id": "i-0adf52b7fa801e08b", "instance_type": "g7.2xlarge", "region": "us-west-2",
            "job_id": "cas-meta2-tpntr-20260925151836-b981625f-m-20260918",
            "control": "Root alone controls this known HELM GPU. CPU launcher must not preempt or modify it."},
        "worker_seconds": 900, "operator_seconds": 1020, "os_shutdown_minutes": 18,
        "scheduler_after_seconds": 1080, "hard_wall_seconds": 1200,
        "maximum_all_services_usd": "1.00", "engineering_pool_maximum_usd": "5.00",
        "forecast_all_services_usd": "0.10", "ec2_usd_per_hour_observed": "0.0208",
        "price_readiness_reference": str(READINESS), "price_readiness_sha256": sha(readiness),
        "cost_boundary": "Prospective envelope, not a billing receipt or AWS enforced monetary cap; timers bound compute. Cleanup failure requires immediate operator attention.",
        "payload_file": "payload.zip", "payload_bytes": archive.stat().st_size, "payload_sha256": sha(archive.read_bytes()),
        "payload_manifest_sha256": sha(payload["payload_manifest.json"]),
        "dependency_lock_sha256": sha(payload["requirements.lock"]),
        "launcher_sha256": sha((HERE / "launch.py").read_bytes()), "worker_sha256": sha((HERE / "worker.py").read_bytes()),
        "package_builder_sha256": sha((HERE / "package.py").read_bytes()),
        "output_prefix": "outputs/", "output_destination": str(directory / "evidence"),
        "expected_tests": expected_tests,
        "git_preflight": {"runtime_commit": RUNTIME_COMMIT, "source_commit": source,
            "object_store": "EXPLICITLY_PARTIAL_PUBLIC_OBJECT_STORE", "inventory_sha256": sha(payload["public_git_objects.json"]),
            "commands": ["git config core.longpaths true", "git cat-file -e " + RUNTIME_COMMIT,
                "python3 research/cas_closed_loop_1/check_artifacts.py --git-ref " + source,
                "python3 research/cas_closed_loop_1/bootstrap_runtime.py"]},
        "git_install": {"version": GIT_VERSION, "packages": GIT_PACKAGES,
            "condition": "Install only if dpkg Git package version differs; installed version must match before preflight",
            "download_source": "https://archive.ubuntu.com/ubuntu/pool/main/g/git/",
            "dependency_sources": ["https://archive.ubuntu.com/ubuntu", "https://security.ubuntu.com/ubuntu"],
            "update_limit_seconds": 120, "install_limit_seconds": 120, "apt_retries": 0,
            "boundary": "Two Git package bytes are pinned and bundled. Any missing OS libraries resolve from signed Noble repositories; installed package inventory is retained. All bootstrap time is inside the existing worker/operator limits."},
        "checks": ["instance Git and exact commit preflight", "committed artifact hashes", "instance bootstrap from exact original Git objects", "exact source admission", "predeclared focused cases", "retained episode replay", "new witness", "fresh-process witness replay"],
        "test_command": "python3 -m pytest -q -p no:cacheprovider --junitxml=/opt/cas-job/aws-output/pytest.xml research/cas_closed_loop_1/test_native_step_adapter.py research/cas_closed_loop_1/test_closed_loop.py research/cas_closed_loop_1/test_artifacts.py",
        "witness_command": "python3 research/cas_closed_loop_1/run_closed_loop.py demo --output /opt/cas-job/aws-output/witness",
        "replay_command": "python3 research/cas_closed_loop_1/run_closed_loop.py replay --directory /opt/cas-job/aws-output/witness --expected-bundle-digest <digest retained from fresh witness stdout>",
        "cleanup": "terminate and verify; collect exact output and console bytes; then delete only owned job bucket, security group, IAM roles/profile and watchdog schedule",
    }
    raw = canonical(plan)
    (directory / "freeze.json").write_bytes(raw)
    (directory / "freeze.sha256").write_text(sha(raw) + "\n")
    print(json.dumps({"job_directory": str(directory), "freeze_sha256": sha(raw), "payload_sha256": plan["payload_sha256"], "status": "FROZEN_NOT_LAUNCHED"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--download-wheels", action="store_true")
    group.add_argument("--freeze", action="store_true")
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--source")
    parser.add_argument("--expected-tests", type=int)
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--authorization-sha256")
    args = parser.parse_args()
    if args.download_wheels:
        download(args.wheelhouse)
    else:
        if not all((args.source, args.expected_tests, args.authorization_file, args.authorization_sha256)):
            parser.error("--freeze requires --source, --expected-tests, --authorization-file and --authorization-sha256")
        freeze(args.wheelhouse, args.source, args.expected_tests, args.authorization_file, args.authorization_sha256)


if __name__ == "__main__":
    main()
