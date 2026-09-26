"""Prepare public partial-Git HELM validation payload; no tests/models/AWS run here."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = None
PREFIX = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/"
TESTS = [
    "tests/test_typed_pointer_deadline_routing.py",
    "tests/test_typed_pointer_critical_mass_2x.py",
    "tests/test_typed_pointer_critical_mass_2x_admission.py",
    "tests/test_typed_pointer_critical_mass_update_counts.py",
    "tests/test_typed_pointer_critical_mass_2x_rerun_admission.py",
    "tests/test_typed_pointer_study.py",
]
PINS = {
    "pip": "25.2", "pytest": "9.0.2", "pluggy": "1.6.0", "packaging": "25.0",
    "iniconfig": "2.3.0", "pygments": "2.19.2", "boto3": "1.43.87",
    "botocore": "1.43.87", "jmespath": "1.1.0", "s3transfer": "0.19.2",
    "python-dateutil": "2.9.0.post0", "six": "1.17.0", "urllib3": "2.6.2",
}
GIT_PACKAGES = [
    {"filename": "git_2.43.0-1ubuntu7.3_amd64.deb", "bytes": 3679758,
     "sha256": "099bb129f543adc4c14203334b0fa0a909f8bf038c4d56bc9cc7c774ebf78f87"},
    {"filename": "git-man_2.43.0-1ubuntu7.3_all.deb", "bytes": 1100178,
     "sha256": "5701f931ed2cd30644700b0fc1cda7c2214f93a63ef84c0c80e43ce40d2cf1d2"},
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def git(*args, input=None):
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1")
    return subprocess.check_output(["git", "-c", "core.longpaths=true", "-c", "core.autocrlf=false",
                                   "-C", str(ROOT), *args], input=input, env=env, timeout=90)


def batch_objects(oids):
    raw = git("cat-file", "--batch", input=("\n".join(oids) + "\n").encode())
    at, result = 0, {}
    for expected in oids:
        end = raw.index(b"\n", at)
        oid, kind, size = raw[at:end].decode().split()
        if oid != expected:
            raise ValueError("GIT_BATCH_IDENTITY")
        count = int(size)
        body = raw[end + 1:end + 1 + count]
        if len(body) != count or raw[end + 1 + count:end + 2 + count] != b"\n":
            raise ValueError("GIT_BATCH_LENGTH")
        result[oid] = (kind, body)
        at = end + 2 + count
    if at != len(raw):
        raise ValueError("GIT_BATCH_TRAILING")
    return result


def prepare(wheelhouse, git_packages_dir, authorization_file, authorization_sha256, provider_file):
    if git("rev-parse", "HEAD").decode().strip() != SOURCE:
        raise ValueError("EXACT_RERUN_SOURCE_CHECKOUT_REQUIRED")
    directive = authorization_file.read_bytes()
    if sha(directive) != authorization_sha256:
        raise ValueError("OWNER_DIRECTIVE_CHANGED")
    provider_raw = provider_file.read_bytes()
    provider = json.loads(provider_raw)
    required_provider = ("account_id", "region", "zone", "ami", "subnet_id", "vpc_id", "root_device")
    if any(not provider.get(name) for name in required_provider):
        raise ValueError("EXPLICIT_CURRENT_PROVIDER_IDENTITIES_REQUIRED")
    if provider["account_id"] != "807562639912" or provider["region"] != "us-west-2":
        raise ValueError("WRONG_PROVIDER_SCOPE")
    # Pure public packaging import derives the established member allowlist.
    # No package build, model, test or provider call occurs on this laptop.
    sys.path[:0] = [str(ROOT), str(ROOT / "research/CAS_META_2_COMPOSITION")]
    from aws import typed_pointer_launch as launch
    names = set(launch.package_data_files())
    names.update(TESTS)
    names.update({
        "records/typed_pointer_001/admission_cm2x_001/prepare_cm2x_study.py",
        "records/typed_pointer_001/admission_cm2x_001/OWNER_LAUNCH_DIRECTIVE_20260925.md",
        "records/typed_pointer_001/admission_analogy_on_001/seeds/20260918/request.json",
    })
    names.update({
        "records/typed_pointer_001/admission_cm2x_rerun_001/prepare_cm2x_rerun.py",
        "records/typed_pointer_001/admission_cm2x_rerun_001/OWNER_AMENDMENT_20260926.md",
        "records/typed_pointer_001/admission_cm2x_rerun_001/PRIOR_PUBLIC_CLOSEOUT.json",
        "records/typed_pointer_001/pre_design/contract_pins/checkpoint_pins.json",
        "records/typed_practice_001/evaluate_gates.py",
    })
    if any("/.." in name or name.startswith("/") for name in names):
        raise ValueError("UNSAFE_ALLOWLIST")
    excluded = ("records/typed_pointer_001/admission_cm2x_001/seeds/",
                "records/typed_pointer_001/receipt_cm2x_20260918/")
    if any(name.startswith(excluded) for name in names):
        raise ValueError("HISTORICAL_OUTPUT_ACCIDENTALLY_INCLUDED")
    repository = git("rev-parse", "--show-toplevel").decode().strip()
    wanted = {PREFIX + item for item in names}
    entries, tree_oids = {}, set()
    # Git read-tree/status needs tree metadata. No non-allowlisted blobs read.
    listing = subprocess.check_output(["git", "-c", "core.longpaths=true", "-C", repository,
                                      "ls-tree", "-r", "-t", "-z", SOURCE], timeout=90)
    for row in listing.split(b"\0"):
        if not row:
            continue
        meta, name = row.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = name.decode()
        if kind == "tree":
            tree_oids.add(oid)
        elif path in wanted:
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise ValueError("REGULAR_PUBLIC_BLOB_REQUIRED:" + path)
            entries[path] = (mode, oid)
    if set(entries) != wanted:
        raise ValueError("ALLOWLIST_PATHS_MISSING:" + str(sorted(wanted - set(entries))))
    commit_raw = git("cat-file", "commit", SOURCE)
    tree_oids.add(commit_raw.splitlines()[0].decode().removeprefix("tree "))
    objects = batch_objects(sorted(tree_oids | {oid for _, oid in entries.values()} | {SOURCE}))
    payload, object_rows = {}, []
    for oid, (kind, raw) in objects.items():
        packed = (kind + " " + str(len(raw)) + "\0").encode() + raw
        if hashlib.sha1(packed).hexdigest() != oid:
            raise ValueError("ORIGINAL_GIT_OBJECT_IDENTITY")
        payload["repo/.git/objects/" + oid[:2] + "/" + oid[2:]] = zlib.compress(packed)
        object_rows.append({"oid": oid, "type": kind, "bytes": len(raw), "sha256": sha(raw)})
    for path, (mode, oid) in entries.items():
        payload["repo/" + path] = objects[oid][1]
    payload["repo/.git/config"] = b"[core]\nrepositoryformatversion = 0\nbare = false\nfilemode = false\nlongpaths = true\nautocrlf = false\nlogallrefupdates = false\n"
    payload["repo/.git/HEAD"] = (SOURCE + "\n").encode()
    payload["repo/.git/refs/heads/helm-public-validation"] = (SOURCE + "\n").encode()
    payload["repo/.git/shallow"] = (SOURCE + "\n").encode()
    payload["public_git_objects.json"] = canonical({
        "source_commit": SOURCE, "status": "EXPLICITLY_PARTIAL_PUBLIC_OBJECT_STORE",
        "objects": object_rows, "allowlisted_paths": sorted(entries),
        "excluded_historical_output_prefixes": [PREFIX + p for p in excluded],
        "boundary": "Exact original commit, tree metadata, public allowlisted blobs only. Protected blob contents absent. No remote, lazy fetch, synthesized commit or complete clone claim. Historical outputs omitted only in disposable validation fixture; original records unchanged.",
    })
    for item in GIT_PACKAGES:
        raw = (git_packages_dir / item["filename"]).read_bytes()
        if len(raw) != item["bytes"] or sha(raw) != item["sha256"]:
            raise ValueError("PINNED_GIT_PACKAGE_CHANGED")
        payload["system-packages/" + item["filename"]] = raw
    normalized = lambda value: re.sub(r"[-_.]+", "_", value).lower()
    wheels = {}
    for path in wheelhouse.glob("*.whl"):
        name, version = path.name.split("-")[:2]
        name = normalized(name)
        if name in {normalized(k) for k in PINS}:
            if name in wheels:
                raise ValueError("DUPLICATE_WHEEL")
            wheels[name] = (version, path)
    if {k: v[0] for k, v in wheels.items()} != {normalized(k): v for k, v in PINS.items()}:
        raise ValueError("PINNED_WHEEL_SET_REQUIRED")
    lock = []
    for name, version in PINS.items():
        path = wheels[normalized(name)][1]
        raw = path.read_bytes()
        payload["wheelhouse/" + path.name] = raw
        lock.append(name + "==" + version + " --hash=sha256:" + sha(raw))
    payload["requirements.lock"] = ("\n".join(lock) + "\n").encode()
    for name in ("worker.py", "package.py", "launch.py"):
        payload[name] = (HERE / name).read_bytes()
    files = [{"path": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in sorted(payload.items())]
    manifest = {"schema": "helm.validation.payload/1", "source_commit": SOURCE,
                "files": files, "dependencies": PINS, "expected_tests": 69,
                "test_files": TESTS, "cncm_prefix": PREFIX, "allowlisted_paths": sorted(entries),
                "git_version": "1:2.43.0-1ubuntu7.3", "git_packages": GIT_PACKAGES,
                "test_checkout_boundary": "Historical outputs omitted only in disposable fixture; exact unchanged scientific code/tests."}
    payload["payload_manifest.json"] = canonical(manifest)
    job = "helm-prep-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    directory = HERE / "jobs" / job
    directory.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(directory / "payload.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(payload.items()):
            item = zipfile.ZipInfo(name, date_time=(2026, 9, 26, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, raw)
    archive_raw = (directory / "payload.zip").read_bytes()
    if len(archive_raw) > 64 * 1024 * 1024 or sum(map(len, payload.values())) > 128 * 1024 * 1024:
        raise ValueError("BOUNDED_PAYLOAD_SIZE")
    (directory / "owner_directive.md").write_bytes(directive)
    (directory / "provider_reference.json").write_bytes(provider_raw)
    plan = {
        "schema": "helm.validation.aws.freeze/1", "job_id": job, "runner": "Codex",
        "source_commit": SOURCE, "operational_source": "Separate exact-hash files; science unchanged",
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "owner_directive_reference": str(authorization_file.resolve()), "owner_directive_sha256": sha(directive),
        **{key: provider[key] for key in required_provider},
        "provider_reference_sha256": sha(provider_raw), "sdk_profile": provider.get("sdk_profile", "default"),
        "instance_type": "t3.small", "cpu_credits": "standard", "root_gib": 8,
        "root_type": "gp3", "root_encrypted": True, "root_delete_on_termination": True,
        "jobs": 1, "retry_count": 0, "permitted_concurrent_instances": [],
        "worker_seconds": 900, "operator_seconds": 1020, "os_shutdown_minutes": 18,
        "scheduler_after_seconds": 1080, "hard_wall_seconds": 1200,
        "maximum_all_services_usd": "0.60", "forecast_all_services_usd": "0.10",
        "ec2_usd_per_hour_upper_bound": "0.021",
        "purpose": "69 public HELM prelaunch tests and exact-source source.zip build; no training",
        "payload_file": "payload.zip", "payload_sha256": sha(archive_raw), "payload_bytes": len(archive_raw),
        "payload_manifest_sha256": sha(payload["payload_manifest.json"]),
        "launcher_sha256": sha((HERE / "launch.py").read_bytes()),
        "worker_sha256": sha((HERE / "worker.py").read_bytes()),
        "package_builder_sha256": sha((HERE / "package.py").read_bytes()),
        "expected_tests": 69, "test_files": TESTS, "package_source_commit": SOURCE,
        "cleanup_required": True,
        "cleanup": "Terminate and verify; collect/hash outputs; remove owned compute/security/IAM/scheduler resources. Retain private validation evidence bucket with storage active. Prior HELM/CAS evidence and reservations untouched.",
        "cost_boundary": "Prospective cap, not provider invoice or monetary kill switch; guest/operator/scheduler timers bound compute.",
    }
    raw = canonical(plan)
    (directory / "freeze.json").write_bytes(raw)
    (directory / "freeze.sha256").write_text(sha(raw) + "\n")
    print(json.dumps({"status": "FROZEN_NOT_LAUNCHED", "job_directory": str(directory),
                      "freeze_sha256": sha(raw), "payload_sha256": sha(archive_raw),
                      "expected_tests": 69, "source_commit": SOURCE}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--git-packages-dir", type=Path, required=True)
    parser.add_argument("--authorization-file", type=Path, required=True)
    parser.add_argument("--authorization-sha256", required=True)
    parser.add_argument("--provider-file", type=Path, required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    SOURCE = args.source_sha
    if not re.fullmatch("[0-9a-f]{40}", SOURCE):
        raise ValueError("SOURCE_SHA_FORM")
    prepare(args.wheelhouse, args.git_packages_dir, args.authorization_file, args.authorization_sha256, args.provider_file)
