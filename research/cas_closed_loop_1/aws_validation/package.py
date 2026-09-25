"""Freeze one public CPU validation package locally. Does not contact AWS."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = "318b22ad01304f80ed0f539420792cc951fe297a"
LANE = "research/cas_closed_loop_1/"
RUNTIME_FILES = Path("D:/tksCAS-worktrees/helm-integration")
READINESS = Path("D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination/AWS_READINESS_20260925.json")
DIRECTIVE = Path("C:/Users/wakil/Downloads/CODEX_COMPLETE_HELM_CAS_AWS_DIRECTIVE.md")
DIRECTIVE_SHA256 = "c4e5b13b56cff788104eba296cf8d3d44008d03afc5fdd790baef8092b28c780"
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


def freeze(wheelhouse):
    if git("cat-file", "-t", SOURCE).decode().strip() != "commit":
        raise ValueError("EXACT_SCIENTIFIC_SOURCE_REQUIRED")
    operational_commit = git("rev-parse", "HEAD").decode().strip()
    directive = DIRECTIVE.read_bytes()
    if sha(directive) != DIRECTIVE_SHA256:
        raise ValueError("OWNER_DIRECTIVE_CHANGED")
    payload = {}
    names = git("ls-tree", "-r", "--name-only", SOURCE, "--", LANE).decode().splitlines()
    for name in names:
        if not name.startswith(LANE) or "/.." in name:
            raise ValueError("OUTSIDE_PUBLIC_LANE")
        payload[name] = git("show", SOURCE + ":" + name)
    bindings = json.loads(payload[LANE + "SOURCE_BINDINGS.json"])
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
        payload[LANE + "_runtime/" + relative.as_posix()] = raw
    if len(bindings["files"]) != 108:
        raise ValueError("EXPECTED_108_RUNTIME_FILES")
    for name in ("worker.py", "package.py", "launch.py"):
        payload[LANE + "aws_validation/" + name] = (HERE / name).read_bytes()
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
    manifest = {"schema": "cas.cpu.payload/1", "source_commit": SOURCE,
                "runtime_commit": bindings["runtime_commit"], "runtime_files": 108,
                "files": inventory, "dependencies": PINS}
    payload["payload_manifest.json"] = canonical(manifest)
    job = "cas-cpu-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
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
        "schema": "cas.cpu.aws.freeze/1", "job_id": job, "runner": "Codex", "source_commit": SOURCE,
        "operational_commit": operational_commit, "owner_directive_reference": str(DIRECTIVE),
        "owner_directive_sha256": sha(directive),
        "source_branch": "codex/cas-closed-loop-1-recovery-20260925", "tested_implementation_commit": "8f55cc3a462e438bcf706d7b64ddf9171d218039",
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "account_id": "807562639912",
        "sdk_profile": "default", "region": "us-west-2", "zone": "us-west-2a",
        "ami": "ami-07a134137a631b892", "instance_type": "t3.small", "cpu_credits": "standard",
        "subnet_id": "subnet-0bb8fa82c2a7177b3", "vpc_id": "vpc-0df2f8cc1b9f23838",
        "root_device": "/dev/sda1", "root_gib": 8, "root_type": "gp3", "root_encrypted": True,
        "root_delete_on_termination": True, "jobs": 1, "retry_count": 0,
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
        "checks": ["exact source admission", "13 artifact hashes", "47 focused tests", "retained episode replay", "new witness", "fresh-process witness replay"],
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
    args = parser.parse_args()
    download(args.wheelhouse) if args.download_wheels else freeze(args.wheelhouse)


if __name__ == "__main__":
    main()
