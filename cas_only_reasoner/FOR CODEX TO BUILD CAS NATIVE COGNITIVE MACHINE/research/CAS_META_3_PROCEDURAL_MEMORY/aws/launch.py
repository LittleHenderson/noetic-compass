"""Separate, plan-by-default AWS launch for fixed unqualified META3 native reuse.

No neural work runs locally. This file does not change the frozen META2
launcher, its validator authority, or the one shared campaign budget.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys
import time
import tempfile
import uuid
import zipfile
import importlib.util

PILOT_ROOT = Path(__file__).resolve().parents[1]
_FROZEN_SPEC = importlib.util.spec_from_file_location("cas_meta3_launch_frozen", PILOT_ROOT / "aws/frozen_helpers.py")
frozen = importlib.util.module_from_spec(_FROZEN_SPEC)
_FROZEN_SPEC.loader.exec_module(frozen)
shared = frozen.load_helpers()
budget = shared.budget
PLAN_FILE = Path(__file__).with_name("launch_plan.json")
EXECUTION_LOCK_FILE = PILOT_ROOT / "records" / "aws_campaign_execution.lock"
EXECUTION_LOCK_SCOPE = "One local META3 checkout only; not a cross-host or cross-version mutex. The live AWS job gate is still required."
SHA256, SHA1 = shared.SHA256, shared.SHA1
ACCEPTED_BASELINE = frozen.BASELINE_SHA
ACCEPTED_BASELINE_MANIFEST_SHA256 = frozen.BASELINE_MANIFEST_SHA
LaunchRefused = shared.LaunchRefused
digest, safe_relative, check_tag = shared.digest, shared.safe_relative, shared.check_tag
confirm_deleted_volumes = shared.confirm_deleted_volumes
remove_owned_auxiliary_resources = shared.remove_owned_auxiliary_resources
reconcile_instance, verify_schedule = shared.reconcile_instance, shared.verify_schedule
terminate_owned_instance = shared.terminate_owned_instance
build_evidence_bundle, sample_artifact_bytes = shared.build_evidence_bundle, shared.sample_artifact_bytes


def validate_approval(cap, plan):
    shared.validate_approval(cap, plan)
    expected = {"demo_seconds_max": 1200, "entrypoint": frozen.ENTRYPOINT,
                "learning_performed": False, "qualification_status": "UNQUALIFIED"}
    if any(type(plan.get(key)) is not type(value) or plan.get(key) != value for key, value in expected.items()):
        raise LaunchRefused("UNREGISTERED_META3_DEMO_PLAN")


def reserve_budget(job, source_sha, archive_sha, plan):
    # No ledger argument, initialization, reset or refund is available here.
    return budget.reserve_budget(job, source_sha, archive_sha, plan["per_launch_reserved_cap_usd"], plan)


@contextmanager
def campaign_execution_lock():
    """Serialize this META3 checkout through cleanup; never clear another owner's lock.

    META2 uses its unchanged launcher, so this lock deliberately does not claim
    to serialize other versions or machines. A stale lock requires an explicit
    operator reconciliation; a PID alone is not authority to remove it.
    """
    path = EXECUTION_LOCK_FILE
    if any(item.is_symlink() or getattr(item, "is_junction", lambda: False)()
           for item in (path, *path.parents)):
        raise LaunchRefused("EXECUTION_LOCK_LINK_REFUSED")
    path.parent.mkdir(parents=True, exist_ok=True)
    owner = {"schema": "cas-meta3-execution-lock/1", "token": uuid.uuid4().hex,
             "pid": os.getpid(), "created_utc": datetime.now(timezone.utc).isoformat(),
             "scope": EXECUTION_LOCK_SCOPE}
    raw = (json.dumps(owner, sort_keys=True) + "\n").encode()
    try:
        stream = path.open("xb")
    except FileExistsError as exc:
        raise LaunchRefused("META3_EXECUTION_ALREADY_LOCKED_NO_AUTOMATIC_STALE_CLEAR") from exc
    try:
        with stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        yield {**owner, "path": str(path)}
    finally:
        # Compare all original bytes, not just a reusable PID or task name.
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise LaunchRefused("EXECUTION_LOCK_OWNERSHIP_CHANGED_NOT_REMOVED")
        deadline = time.monotonic() + 2
        while True:
            try:
                path.unlink()
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise LaunchRefused("EXECUTION_LOCK_RELEASE_FAILED_CLOSED")
                time.sleep(0.05)


def _check_auxiliary_intent(key, intent, receipt, job):
    """Only the exact names generated for this job can enter recovery/cleanup."""
    account = receipt["plan"]["account_id"]
    if not re.fullmatch(r"cas-meta3-[A-Za-z0-9-]+", job):
        raise LaunchRefused("EXACT_META3_JOB_REQUIRED")
    kind, name = intent.get("kind"), intent.get("name")
    expected = {"bucket": ("bucket", job + "-" + account),
                "instance_profile": ("instance_profile", job + "-worker"),
                "security_group": ("security_group", job)}
    if kind == "role":
        valid = name in (job + "-worker", job + "-timer") and key == name
    else:
        valid = kind in expected and (key, name) == expected[kind]
    if (not valid or intent.get("job") != job or intent.get("account_id") != account
            or (kind == "security_group" and not re.fullmatch(r"vpc-[0-9a-f]+", intent.get("vpc_id", "")))):
        raise LaunchRefused("AUXILIARY_INTENT_SCOPE_MISMATCH")


def create_declared_auxiliary(receipt, key, kind, name, operation, record, *, vpc_id=None):
    """Persist intent before creation, including when the response is lost."""
    intent = {"kind": kind, "name": name, "job": receipt["job"],
              "account_id": receipt["plan"]["account_id"], "status": "CREATE_ATTEMPTED"}
    if vpc_id is not None:
        intent["vpc_id"] = vpc_id
    _check_auxiliary_intent(key, intent, receipt, receipt["job"])
    intents = receipt.setdefault("resource_intents", {})
    if key in intents or key in receipt["resources"]:
        raise LaunchRefused("AUXILIARY_CREATE_ALREADY_ATTEMPTED_NO_RETRY")
    intents[key] = intent
    record("AUXILIARY_CREATE_ATTEMPTED", resource_key=key, identity=dict(intent))
    try:
        result = operation()
    except BaseException as exc:
        intent.update(status="CREATE_FAILED_OR_UNCERTAIN", error=type(exc).__name__ + ": " + str(exc))
        record("AUXILIARY_CREATE_RESPONSE_UNCONFIRMED", resource_key=key)
        raise
    intent["status"] = "CREATE_RESPONSE_RECEIVED"
    record("AUXILIARY_CREATE_RESPONSE_RECEIVED", resource_key=key)
    return result


def reconcile_auxiliary_intents(ec2, iam, s3, receipt, job, record):
    """Read exact identities; admit cleanup only after independent ownership checks.

    S3 cannot tag a general-purpose bucket atomically at creation. A lost
    CreateBucket response followed by missing tags is therefore UNCONFIRMED,
    not permission to tag, delete, or claim retention for that bucket.
    """
    for key, intent in receipt.get("resource_intents", {}).items():
        if key in receipt["resources"]:
            continue  # The unchanged cleanup helper rechecks these recorded IDs.
        try:
            _check_auxiliary_intent(key, intent, receipt, job)
            name, kind, account = intent["name"], intent["kind"], intent["account_id"]
            if kind == "role":
                current = iam.get_role(RoleName=name)["Role"]
                expected_arn = f"arn:aws:iam::{account}:role/{name}"
                if current.get("RoleName") != name or current.get("Arn") != expected_arn:
                    raise LaunchRefused("ROLE_RECOVERY_IDENTITY_MISMATCH")
                check_tag(current.get("Tags", []), job)
                resource = expected_arn
            elif kind == "instance_profile":
                current = iam.get_instance_profile(InstanceProfileName=name)["InstanceProfile"]
                if (current.get("InstanceProfileName") != name
                        or current.get("Arn") != f"arn:aws:iam::{account}:instance-profile/{name}"):
                    raise LaunchRefused("PROFILE_RECOVERY_IDENTITY_MISMATCH")
                check_tag(current.get("Tags", []), job)
                if any(role.get("RoleName") != job + "-worker" for role in current.get("Roles", [])):
                    raise LaunchRefused("PROFILE_HAS_UNEXPECTED_ROLE")
                resource = name
            elif kind == "security_group":
                response = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [name]},
                                                                {"Name": "vpc-id", "Values": [intent["vpc_id"]]}])
                groups = response.get("SecurityGroups", [])
                if response.get("NextToken") or len(groups) != 1:
                    raise LaunchRefused("EXACT_RECOVERED_SECURITY_GROUP_REQUIRED")
                current = groups[0]
                if (current.get("GroupName") != name or current.get("VpcId") != intent["vpc_id"]
                        or current.get("OwnerId") != account
                        or not re.fullmatch(r"sg-[0-9a-f]+", current.get("GroupId", ""))):
                    raise LaunchRefused("SECURITY_GROUP_RECOVERY_IDENTITY_MISMATCH")
                check_tag(current.get("Tags", []), job)
                resource = current["GroupId"]
            else:  # kind has already been checked against the closed set above.
                response = s3.get_bucket_tagging(Bucket=name, ExpectedBucketOwner=account)
                check_tag(response.get("TagSet", []), job)
                resource = name
            receipt["resources"][key] = resource
            intent["status"] = "OWNERSHIP_RECOVERED"
            record("AUXILIARY_IDENTITY_RECOVERED", resource_key=key, identity=resource)
        except Exception as exc:
            intent.update(status="OWNERSHIP_UNCONFIRMED", recovery_error=type(exc).__name__ + ": " + str(exc))
            receipt["cleanup_errors"].append("AUXILIARY_OWNERSHIP_UNCONFIRMED:" + key + ": " + str(exc))
            record("AUXILIARY_UNCONFIRMED_NOT_DELETED", resource_key=key, identity=dict(intent))


def verify_launcher_identity(manifest):
    frozen.verify_dependencies()
    repo, prefix = frozen.git_context(PILOT_ROOT)
    members = frozen.git_members(repo, prefix, manifest["source_sha"])
    upstream = frozen.git_members(repo, prefix, frozen.UPSTREAM_SHA, frozen.UPSTREAM_PACKAGES)
    actual = {name: hashlib.sha256(raw).hexdigest() for name, raw in members.items()}
    if actual != manifest["files_sha256"]:
        raise LaunchRefused("ARCHIVE_DOES_NOT_MATCH_REAL_SOURCE_COMMIT")
    frozen.check_upstream(members, upstream)
    for name, checksum in actual.items():
        path = PILOT_ROOT.parent / name.removeprefix("research/")
        if not path.is_file() or path.is_symlink() or digest(path) != checksum:
            raise LaunchRefused("LOCAL_SOURCE_ARCHIVE_IDENTITY_MISMATCH:" + name)
    spec = importlib.util.spec_from_file_location("cas_meta3_verified_bundle_builder", PILOT_ROOT / "tools/build_launch_bundle.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    if builder.make_manifest(members, manifest["source_sha"], upstream) != manifest:
        raise LaunchRefused("EXACT_META3_MANIFEST_REQUIRED")
    return {"upstream_sha": frozen.UPSTREAM_SHA, "files_sha256": actual,
            "canonical_budget_ledger": str(budget.CANONICAL_LEDGER)}


def validate_archive(path: Path, expected_sha: str, source_sha: str, plan: dict) -> dict:
    if not SHA256.fullmatch(expected_sha) or not SHA1.fullmatch(source_sha):
        raise LaunchRefused("FULL_SHA_REQUIRED")
    if digest(path) != expected_sha:
        raise LaunchRefused("ARCHIVE_SHA_MISMATCH")
    with zipfile.ZipFile(path) as archive:
        names, aliases, total = set(), set(), 0
        for info in archive.infolist():
            name = safe_relative(info.filename.rstrip("/"))
            if name in names or name.casefold() in aliases or stat.S_ISLNK(info.external_attr >> 16):
                raise LaunchRefused("DUPLICATE_OR_SYMLINK_ARCHIVE_ENTRY")
            names.add(name)
            aliases.add(name.casefold())
            total += info.file_size
            if total > plan["archive_expanded_bytes_max"]:
                raise LaunchRefused("ARCHIVE_SIZE_CEILING")
        manifest = frozen.strict_json(archive.read("launch_manifest.json"))
        if manifest.get("schema") != frozen.SCHEMA or manifest.get("source_sha") != source_sha:
            raise LaunchRefused("SOURCE_IDENTITY_MISMATCH")
        if manifest.get("baseline_sha") != ACCEPTED_BASELINE:
            raise LaunchRefused("ACCEPTED_BASELINE_REQUIRED")
        for key in ("pilot_dir", "meta2_dir", "meta1_dir", "meta_runtime_dir", "dependency_lock"):
            safe_relative(manifest[key])
        if manifest["pilot_dir"] != frozen.PILOT or manifest["meta2_dir"] != frozen.META2 or manifest["meta1_dir"] != frozen.META1 or manifest["meta_runtime_dir"] != frozen.META_RUNTIME:
            raise LaunchRefused("EXACT_PACKAGE_DIRECTORIES_REQUIRED")
        wheels = manifest.get("wheel_paths", [])
        dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
        expected_wheels = [dist+"casformer_reference-0.1.0-py3-none-any.whl",dist+"cas_neural_cjt-0.2.0-py3-none-any.whl"]
        if wheels != expected_wheels:
            raise LaunchRefused("TWO_FROZEN_WHEELS_REQUIRED")
        if manifest["dependency_lock"] != frozen.META2+"/requirements-gpu.txt":
            raise LaunchRefused("EXACT_CAMPAIGN_DEPENDENCY_LOCK_REQUIRED")
        hashes = manifest.get("files_sha256", {})
        actual = {i.filename for i in archive.infolist() if not i.is_dir()} - {"launch_manifest.json"}
        if set(hashes) != actual:
            raise LaunchRefused("ARCHIVE_MANIFEST_COVERAGE_MISMATCH")
        for name, sha in hashes.items():
            safe_relative(name)
            if not SHA256.fullmatch(sha) or hashlib.sha256(archive.read(name)).hexdigest() != sha:
                raise LaunchRefused("ARCHIVE_MEMBER_HASH_MISMATCH")
        baseline_bytes = archive.read(manifest["meta1_dir"]+"/BASELINE_MANIFEST.json")
        if hashlib.sha256(baseline_bytes).hexdigest() != ACCEPTED_BASELINE_MANIFEST_SHA256:
            raise LaunchRefused("PROTECTED_BASELINE_MANIFEST_CHANGED")
        protected = json.loads(baseline_bytes)
        for entry in protected["files"]:
            if hashes.get("research/"+entry["path"]) != entry["sha256"]:
                raise LaunchRefused("ACCEPTED_SOURCE_OR_WHEEL_BYTES_CHANGED")
        if not all(w in actual for w in wheels) or manifest["dependency_lock"] not in actual:
            raise LaunchRefused("DECLARED_INPUT_MISSING")
        for key in ("pilot_dir", "meta2_dir", "meta1_dir", "meta_runtime_dir"):
            if not any(n.startswith(manifest[key] + "/") for n in actual):
                raise LaunchRefused("DECLARED_DIRECTORY_MISSING")
        lock = archive.read(manifest["dependency_lock"]).decode("utf-8")
        for line in lock.splitlines():
            pin = line.strip()
            if not pin or pin.startswith("#"): continue
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9_.+!-]+",pin) or pin.lower().startswith("torch==") or "+cpu" in pin:
                raise LaunchRefused("GPU_LOCK_REQUIRES_EXACT_PINS_AND_SEPARATE_TORCH")
        if manifest.get("upstream_sha") != frozen.UPSTREAM_SHA or manifest.get("entrypoint") != frozen.ENTRYPOINT:
            raise LaunchRefused("EXACT_META3_ENTRYPOINT_AND_UPSTREAM_REQUIRED")
        if manifest.get("learning_performed") is not False or manifest.get("qualification_status") != "UNQUALIFIED":
            raise LaunchRefused("META3_NO_LEARNING_OR_QUALIFICATION_CLAIM")
        expected_helpers = {frozen.META2+"/"+name: checksum for name, checksum in frozen.PINNED_FILES.items()}
        if manifest.get("helper_files_sha256") != expected_helpers or any(hashes.get(name) != checksum for name, checksum in expected_helpers.items()):
            raise LaunchRefused("IMMUTABLE_HELPER_MANIFEST_MISMATCH")
        if any(name not in actual for name in frozen.REQUIRED):
            raise LaunchRefused("META3_DEMO_SOURCE_NOT_READY_IN_COMMIT")
        foreign = {name: checksum for name, checksum in hashes.items() if not name.startswith(frozen.PILOT+"/")}
        if manifest.get("upstream_files_sha256") != foreign:
            raise LaunchRefused("FROZEN_UPSTREAM_HASH_COVERAGE_MISMATCH")
        return manifest


def collect_roots(roots, destination, expanded_limit):
    """Copy only explicit new job outputs; never collect a package/records parent."""
    import hashlib, json, os, pathlib, shutil
    destination = pathlib.Path(destination)
    if destination.exists():
        raise RuntimeError("NEW_ARTIFACT_STAGING_ROOT_REQUIRED")
    destination.mkdir(parents=True)
    entries, total, seen = [], 0, set()
    for label, source, required in roots:
        if label.startswith("/") or any(part in ("", ".", "..") for part in label.split("/")) or "\\" in label:
            raise RuntimeError("UNSAFE_ARTIFACT_ROOT_LABEL")
        source = pathlib.Path(source)
        if not source.exists():
            if required:
                raise RuntimeError("REQUIRED_ARTIFACT_ROOT_MISSING:" + label)
            continue
        if not source.is_dir() or any(path.is_symlink() or getattr(path, "is_junction", lambda: False)()
                                    for path in (source, *source.parents)):
            raise RuntimeError("ARTIFACT_ROOT_LINK_REFUSED")
        for directory, directories, files in os.walk(source, followlinks=False):
            directory = pathlib.Path(directory)
            for name in directories:
                path = directory / name
                if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                    raise RuntimeError("ARTIFACT_DIRECTORY_LINK_REFUSED")
            for name in files:
                path = directory / name
                if not path.is_file() or path.is_symlink():
                    raise RuntimeError("ARTIFACT_FILE_LINK_REFUSED")
                relative = label + "/" + path.relative_to(source).as_posix()
                if relative.casefold() in seen or len(seen) >= 10000:
                    raise RuntimeError("ARTIFACT_ALIAS_OR_COUNT_CEILING")
                seen.add(relative.casefold())
                size = path.stat().st_size
                total += size
                if total > expanded_limit - 4194304:
                    raise RuntimeError("ARTIFACT_ROOTS_EXPANDED_CEILING")
                def checksum(location):
                    h = hashlib.sha256()
                    with location.open("rb") as stream:
                        for block in iter(lambda: stream.read(1048576), b""):
                            h.update(block)
                    return h.hexdigest()
                before = checksum(path)
                target = destination.joinpath(*relative.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                if path.stat().st_size != size or target.stat().st_size != size or checksum(path) != before or checksum(target) != before:
                    raise RuntimeError("ARTIFACT_CHANGED_DURING_COPY")
                entries.append({"path": relative, "bytes": size, "sha256": before})
    entries.sort(key=lambda row: row["path"])
    record = {"schema": "cas-meta3-collected-roots/1", "entries": entries,
              "entries_sha256": hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
              "all_source_bytes_verified_before_after_copy": True}
    (destination / "artifact_roots_index.json").write_text(json.dumps(record, sort_keys=True, indent=2), encoding="utf-8")
    return record


def verify_demo_evidence(read_bytes, names, job):
    """Mandatory complete native-reuse evidence, not a neural or skill audit."""
    import hashlib, json, re
    if not re.fullmatch(r"cas-meta3-[A-Za-z0-9-]+", job):
        raise RuntimeError("EXACT_META3_JOB_REQUIRED")
    demo = "cloud_job/demo/"
    native = "meta2_native/meta3_" + job + "/"
    def document(name):
        return json.loads(read_bytes(name))
    def check(condition, reason):
        if not condition:
            raise RuntimeError(reason)
    required = ("memory_demo_receipt.json", "package.json", "registry.db", "trusted_compatibility.json",
        "writer_receipt.json", "writer_process.json", "reader_receipt.json", "reader_process.json",
        "rejection_receipt.json", "link_receipt.json", "identity_probe_receipt.json",
        "reference_result.json", "reference_verdict.json", "candidate_result.json", "candidate_verdict.json",
        "call_mapping_receipt.json", "file_index.json", "writer.stdout.log", "writer.stderr.log",
        "reader.stdout.log", "reader.stderr.log")
    check(all(demo + name in names for name in required), "META3_MANDATORY_DEMO_EVIDENCE_MISSING")
    for name in ("reference/native.db", "candidate/native.db", "fresh_reader_identity/native.db"):
        check(native + name in names, "META3_MANDATORY_NATIVE_DATABASE_MISSING")
    receipt = document(demo + "memory_demo_receipt.json")
    check(receipt.get("schema") == "cas-meta3-native-reuse/0.1"
          and receipt.get("status") == "CAS_META_3_NATIVE_REUSE_DEMONSTRATED"
          and receipt.get("completed") is True and receipt.get("job") == job,
          "META3_DEMO_NOT_COMPLETED")
    check(receipt.get("qualification_status") == "UNQUALIFIED" and receipt.get("learning_performed") is False
          and receipt.get("automatic_retries") == 0
          and receipt.get("reference_native_runs") == 3 and receipt.get("candidate_native_runs") == 3
          and receipt.get("identity_probe_native_ticks") == 0, "META3_DEMO_SCOPE_OR_COUNTS_MISMATCH")
    check(type(receipt.get("max_wall_seconds")) is int and 60 <= receipt["max_wall_seconds"] <= 1200,
          "META3_DEMO_TIME_LIMIT_MISMATCH")
    index_raw = read_bytes(demo + "file_index.json")
    check(hashlib.sha256(index_raw).hexdigest() == receipt["file_index_sha256"], "META3_DEMO_INDEX_HASH_MISMATCH")
    index = json.loads(index_raw)
    check(index.get("schema") == "cas-meta3-file-index/0.1" and set(index["roots"]) == {"demo", "native"},
          "META3_DEMO_INDEX_SCHEMA_MISMATCH")
    check(index["roots"] == {"demo": receipt["output"], "native": receipt["native_output"]}
          and receipt["output"].endswith("/research/CAS_META_3_PROCEDURAL_MEMORY/runs/cloud_job/demo")
          and receipt["native_output"].endswith("/research/CAS_META_2_COMPOSITION/records/meta3_" + job),
          "META3_DEMO_OUTPUT_BINDING_MISMATCH")
    entries, covered, aliases = index["entries"], set(), set()
    expected = {name for name in names if name.startswith(demo) or name.startswith(native)}
    expected -= {demo + "file_index.json", demo + "memory_demo_receipt.json"}
    for row in entries:
        check(type(row) is dict and set(row) == {"root", "path", "bytes", "sha256"}
              and row["root"] in ("demo", "native"), "META3_DEMO_INDEX_ENTRY_INVALID")
        relative = row["path"]
        check(type(relative) is str and "\\" not in relative and ":" not in relative
              and all(part not in ("", ".", "..") for part in relative.split("/")),
              "META3_DEMO_INDEX_PATH_INVALID")
        name = (demo if row["root"] == "demo" else native) + relative
        check(name in expected and name.casefold() not in aliases, "META3_DEMO_INDEX_MEMBERSHIP_MISMATCH")
        aliases.add(name.casefold())
        covered.add(name)
        raw = read_bytes(name)
        check(type(row["bytes"]) is int and len(raw) == row["bytes"]
              and hashlib.sha256(raw).hexdigest() == row["sha256"], "META3_DEMO_MEMBER_HASH_MISMATCH")
    check(covered == expected, "META3_DEMO_FULL_INDEX_COVERAGE_MISMATCH")
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    check(hashlib.sha256(encoded).hexdigest() == index["entries_sha256"], "META3_DEMO_ENTRIES_HASH_MISMATCH")
    writer, reader = (document(demo + role + "_receipt.json") for role in ("writer", "reader"))
    for role, value in (("writer", writer), ("reader", reader)):
        process = document(demo + role + "_process.json")
        check(value["job"] == job and value["qualification_status"] == "UNQUALIFIED"
              and value["learning_performed"] is False and process["returncode"] == 0
              and process["pid"] == value["pid"] and process["stage"] == role,
              "META3_FRESH_PROCESS_RECEIPT_MISMATCH")
    check(writer["pid"] != reader["pid"] and writer["process_nonce"] != reader["process_nonce"]
          and writer["registry_closed"] is True, "META3_FRESH_READER_NOT_ESTABLISHED")
    return {"status": "META3_COMPLETE_BYTE_INVENTORY_VERIFIED",
            "indexed_files": len(entries), "qualification_status": "UNQUALIFIED",
            "memory_demo_receipt_sha256": hashlib.sha256(read_bytes(demo + "memory_demo_receipt.json")).hexdigest(),
            "file_index_sha256": hashlib.sha256(index_raw).hexdigest(),
            "demo_prefix": demo, "native_prefix": native,
            "learning_performed": False,
            "boundary": "Recorded fresh reader and native reuse only; no suspended-call restart or skill qualification."}


def verify_downloaded_packet(artifact, result, job, source_sha, plan):
    record = shared.verify_downloaded_packet(artifact, result, job, source_sha, plan)
    if record.get("entrypoint") != frozen.ENTRYPOINT or result.get("entrypoint") != frozen.ENTRYPOINT:
        raise LaunchRefused("META3_RESULT_ENTRYPOINT_MISMATCH")
    if result["returncode"] == 0:
        with zipfile.ZipFile(artifact) as archive:
            names = {info.filename for info in archive.infolist() if not info.is_dir()}
            stage = frozen.strict_json(archive.read("artifact_roots_index.json"))
            if stage.get("schema") != "cas-meta3-collected-roots/1" or stage.get("all_source_bytes_verified_before_after_copy") is not True:
                raise LaunchRefused("VERIFIED_DUAL_ROOT_COLLECTION_REQUIRED")
            expected = names - {"artifact_roots_index.json", "artifact_collection_receipt.json"}
            rows = stage["entries"]
            if len(rows) != len(expected) or {row["path"] for row in rows} != expected:
                raise LaunchRefused("FULL_COLLECTED_ROOT_INDEX_REQUIRED")
            encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
            if hashlib.sha256(encoded).hexdigest() != stage["entries_sha256"]:
                raise LaunchRefused("COLLECTED_INDEX_HASH_MISMATCH")
            for row in rows:
                raw = archive.read(row["path"])
                if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
                    raise LaunchRefused("COLLECTED_MEMBER_HASH_MISMATCH")
            checked = verify_demo_evidence(archive.read, names, job)
            binding = {**checked, "job": job, "source_sha": source_sha}
            if record.get("native_demo_binding") != binding or result.get("native_demo_binding") != binding:
                raise LaunchRefused("META3_TRUSTED_DEMO_SIDECAR_BINDING_MISMATCH")
    return record


def remote_program(config):
    """Fixed remote-only demo driver; this string never runs on the client."""
    if config["manifest"].get("entrypoint") != frozen.ENTRYPOINT:
        raise LaunchRefused("EXACT_META3_ENTRYPOINT_REQUIRED")
    helpers = (build_evidence_bundle, sample_artifact_bytes, collect_roots, verify_demo_evidence)
    return "CONFIG = " + repr(config) + "\n" + "\n".join(inspect.getsource(helper) for helper in helpers) + r'''
import hashlib, json, os, pathlib, platform, shutil, signal, subprocess, sys, time, traceback, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
root = pathlib.Path('/opt/cas-meta3')
payload = root / 'payload.zip'
def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()
def run(argv, **kwargs):
    print(json.dumps({'command': argv}), flush=True)
    return subprocess.run(argv, check=True, **kwargs)
def s3_get(key, target):
    run(['aws','s3','cp','s3://'+CONFIG['bucket']+'/'+key,str(target),'--region',CONFIG['region']])
start = time.time()
returncode = 1
out = root/'early_failure'
out.mkdir(parents=True,exist_ok=True)
artifact_root = out
native_root = None
m = CONFIG['manifest']

def publish_progress(log_path, status):
    # Best effort: one existing result key, <=64 KiB, and at most five seconds.
    try:
        def tail(path, count):
            try:
                with path.open('rb') as stream:
                    stream.seek(max(0,path.stat().st_size-count))
                    return stream.read(count)
            except OSError: return b''
        header = json.dumps({'job':CONFIG['job'],'utc':datetime.now(timezone.utc).isoformat(),
                             'stage_log':log_path.name,**status},sort_keys=True).encode()
        progress = tail(out/'demo'/'memory_demo_receipt.json',8192)
        content = header+b'\nMEMORY DEMO STATUS\n'+progress+b'\nCURRENT STAGE LOG TAIL\n'+tail(log_path,49152)
        target = root/'live-progress.log'
        target.write_bytes(content[:65536])
        subprocess.run(['aws','s3','cp',str(target),'s3://'+CONFIG['bucket']+'/results/bootstrap.log',
                        '--region',CONFIG['region'],'--cli-connect-timeout','5','--cli-read-timeout','5'],
                       timeout=5,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                       env={**os.environ,'AWS_MAX_ATTEMPTS':'1','AWS_PAGER':''})
    except Exception:
        pass

def bounded_process(argv, log_path, *, env, cwd, seconds, deadline):
    stage_start = time.time()
    next_progress = stage_start
    with log_path.open('w') as log:
        process = subprocess.Popen(argv,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while process.poll() is None:
                size = sample_artifact_bytes(artifact_root)
                if 'package' in globals(): size += sample_artifact_bytes(package/m['meta1_dir']/'runs')
                if native_root is not None and native_root.exists(): size += sample_artifact_bytes(native_root)
                if size > CONFIG['evidence_expanded_bytes_max'] - 2097152 or time.time()-stage_start > seconds or time.time() > deadline-120:
                    raise RuntimeError('PROCESS_TIME_OR_ARTIFACT_CEILING')
                if time.time() >= next_progress:
                    next_progress = time.time()+30
                    publish_progress(log_path,{'state':'RUNNING','elapsed_seconds':time.time()-stage_start,'artifact_bytes':size})
                time.sleep(2)
            publish_progress(log_path,{'state':'EXITED','returncode':process.returncode,'elapsed_seconds':time.time()-stage_start})
            return process.returncode
        finally:
            # Stop the parent and all spawned workers before packaging a failed stage.
            if process.poll() is None or process.returncode != 0:
                try: os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired: pass
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                if process.poll() is None:
                    process.wait(timeout=15)

try:
    # No neural work or dependency installation before the external deadline is confirmed.
    permit = root / 'permit.json'
    for attempt in range(60):
        try:
            s3_get('input/permit.json', permit)
            p = json.loads(permit.read_text())
            if p['job'] != CONFIG['job'] or p['archive_sha256'] != CONFIG['archive_sha256'] or not p['cloud_deadline_confirmed']:
                raise RuntimeError('INVALID_CLOUD_DEADLINE_PERMIT')
            break
        except subprocess.CalledProcessError: time.sleep(5)
    else: raise RuntimeError('CLOUD_DEADLINE_NOT_CONFIRMED')
    deadline = datetime.fromisoformat(p['deadline']).timestamp()
    if deadline - time.time() < 300: raise RuntimeError('INSUFFICIENT_REMAINING_CLOUD_TIME')
    s3_get('input/payload.zip', payload)
    if sha(payload) != CONFIG['archive_sha256']: raise RuntimeError('ARCHIVE_SHA_MISMATCH')
    with zipfile.ZipFile(payload) as z:
        m = json.loads(z.read('launch_manifest.json'))
        if m != CONFIG['manifest']: raise RuntimeError('MANIFEST_MISMATCH')
        for name, expected in m['files_sha256'].items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected: raise RuntimeError('MEMBER_HASH_MISMATCH')
        z.extractall(root / 'package') # names and membership were checked before publication
    package = root / 'package'
    out = package / m['pilot_dir'] / 'runs' / 'cloud_job'
    out.mkdir(parents=True)
    artifact_root = out
    native_root = package / m['meta2_dir'] / 'records' / ('meta3_' + CONFIG['job'])
    if native_root.exists(): raise RuntimeError('NEW_NATIVE_JOB_ROOT_REQUIRED')
    py = root / 'venv' / 'bin' / 'python'
    run([sys.executable,'-m','venv',str(root / 'venv')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--disable-pip-version-check','torch==2.11.0','--index-url',CONFIG['torch_index_url'],'--report',str(out/'torch_install.json')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--disable-pip-version-check','-r',str(package/m['dependency_lock']),'--report',str(out/'dependency_install.json')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--no-deps',*[str(package/w) for w in m['wheel_paths']],'--report',str(out/'frozen_wheel_install.json')],timeout=max(1,deadline-time.time()-240))
    probe = "import torch,json,sys,platform; assert torch.__version__=='2.11.0+cu128'; assert torch.version.cuda=='12.8'; assert torch.cuda.is_available(); assert torch.cuda.device_count()==1; gpu=torch.cuda.get_device_name(0); assert " + repr(CONFIG['required_gpu_name_contains']) + " in gpu; x=torch.ones((32,32),device='cuda'); assert (x@x).sum().item()==32768; torch.cuda.synchronize(); print(json.dumps({'python':sys.version,'platform':platform.platform(),'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':gpu,'cuda_matmul_passed':True}))"
    with (out/'runtime.json').open('w') as f: run([str(py),'-c',probe],stdout=f,timeout=60)
    with (out/'pip_freeze.txt').open('w') as f: run([str(py),'-m','pip','freeze','--all'],stdout=f,timeout=30)
    env = dict(os.environ)
    env['PYTHONPATH'] = ':'.join(str(package/m[key]) for key in ('pilot_dir','meta2_dir','meta1_dir','meta_runtime_dir'))
    env['CUDA_VISIBLE_DEVICES'] = '0'
    env['CAS_META1_AWS_JOB_ID'] = CONFIG['job']
    env['CAS_META1_SOURCE_SHA'] = m['source_sha']
    env['CAS_META1_RUN_GPU_TESTS'] = '1'
    env['CAS_META2_AWS_JOB_ID'] = CONFIG['job']
    env['CAS_META3_AWS_JOB_ID'] = CONFIG['job']
    env['CAS_META2_SOURCE_SHA'] = m['source_sha']
    env['OMP_NUM_THREADS'] = '1'
    env['MKL_NUM_THREADS'] = '1'
    gpu_argv = [str(py),'-m','pytest','-m','gpu','tests/test_execution_contract.py','-q','--junitxml',str(out/'gpu_contract_tests.xml'),'-p','no:cacheprovider']
    (out/'gpu_contract_command.json').write_text(json.dumps(gpu_argv,indent=2))
    if deadline-time.time() < 300: raise RuntimeError('INSUFFICIENT_GPU_PREFLIGHT_TIME')
    gpu_code = bounded_process(gpu_argv,out/'gpu_contract_tests.log',env=env,cwd=package/m['meta1_dir'],seconds=600,deadline=deadline)
    suites = list(ET.parse(out/'gpu_contract_tests.xml').getroot().iter('testsuite'))
    totals = {key:sum(int(s.get(key,'0')) for s in suites) for key in ('tests','failures','errors','skipped')}
    if gpu_code != 0 or totals != {'tests':4,'failures':0,'errors':0,'skipped':0}:
        raise RuntimeError('GPU_CONTRACT_TESTS_MUST_REPORT_EXACTLY_FOUR_PASSED:'+str(totals))
    (out/'gpu_contract_receipt.json').write_text(json.dumps({'passed':4,**totals}))
    env.pop('CAS_META1_RUN_GPU_TESTS')
    env['CAS_META2_RUN_GPU_TESTS'] = '1'
    policy_argv = [str(py),'-m','pytest','-m','gpu','tests/test_policy_gpu.py','-q','--junitxml',str(out/'gpu_policy_tests.xml'),'-p','no:cacheprovider']
    policy_expected_tests = 4
    (out/'gpu_policy_command.json').write_text(json.dumps(policy_argv,indent=2))
    policy_code = bounded_process(policy_argv,out/'gpu_policy_tests.log',env=env,cwd=package/m['meta2_dir'],seconds=600,deadline=deadline)
    policy_suites = list(ET.parse(out/'gpu_policy_tests.xml').getroot().iter('testsuite'))
    policy_totals = {key:sum(int(s.get(key,'0')) for s in policy_suites) for key in ('tests','failures','errors','skipped')}
    if policy_code != 0 or policy_totals != {'tests':policy_expected_tests,'failures':0,'errors':0,'skipped':0}:
        label = 'META2_GPU_POLICY_TESTS_MUST_REPORT_EXACTLY_FOUR_PASSED:'
        raise RuntimeError(label+str(policy_totals))
    (out/'gpu_policy_receipt.json').write_text(json.dumps({'passed':policy_expected_tests,**policy_totals}))
    env.pop('CAS_META2_RUN_GPU_TESTS')
    effective_demo_seconds = min(CONFIG['demo_seconds_max'],CONFIG['compute_seconds_max'],int(deadline-time.time()-180))
    if effective_demo_seconds < 60:
        raise RuntimeError('INSUFFICIENT_DEMO_TIME_AFTER_GPU_GATES')
    env['CAS_META3_RUN_GPU_DEMO'] = '1'
    argv = [str(py),'-m','cas_meta3.native_demo','--output',str(out/'demo'),
            '--native-output',str(native_root),'--max-wall-seconds',str(effective_demo_seconds)]
    (out/'command.json').write_text(json.dumps(argv,indent=2))
    returncode = bounded_process(argv,out/'native_demo.log',env=env,cwd=package/m['pilot_dir'],seconds=effective_demo_seconds,deadline=deadline)
    env.pop('CAS_META3_RUN_GPU_DEMO')

except BaseException as exc:
    returncode = 1
    (out/'remote_failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()},indent=2))
finally:
    job_record = {'job':CONFIG['job'],'source_sha':m['source_sha'],'baseline_sha':m['baseline_sha'],
                  'archive_sha256':CONFIG['archive_sha256'],'returncode':returncode,
                  'remote_wall_seconds':time.time()-start,'entrypoint':'cas_meta3.native_demo',
                  'learning_performed':False,'qualification_status':'UNQUALIFIED',
                  'boundary':'Fresh reader process and recorded native reuse, not native suspended-call restart or skill qualification.'}
    (out/'job.json').write_text(json.dumps(job_record,indent=2))
    roots = [('cloud_job',out,True)]
    if native_root is not None:
        roots.append(('meta2_native/meta3_'+CONFIG['job'],native_root,returncode==0))
    if 'package' in globals():
        roots.append(('meta1_runs',package/m['meta1_dir']/'runs',False))
    staging = root/'artifact_staging'
    collection_failed = False
    try:
        collect_roots(roots,staging,CONFIG['evidence_expanded_bytes_max'])
        if returncode == 0:
            inventory = {p.relative_to(staging).as_posix() for p in staging.rglob('*') if p.is_file()}
            checked = verify_demo_evidence(lambda name:(staging/name).read_bytes(),inventory,CONFIG['job'])
            job_record['native_demo_binding'] = {**checked,'job':CONFIG['job'],'source_sha':m['source_sha']}
    except BaseException as exc:
        collection_failed = True
        returncode = 1
        job_record.update(returncode=1,failure=type(exc).__name__+':'+str(exc))
        staging.mkdir(parents=True,exist_ok=True)
        (staging/'collection_failure.json').write_text(json.dumps(job_record,indent=2))
    bundle = root/'artifacts.zip'
    collected = build_evidence_bundle(staging,bundle,CONFIG['artifact_bytes_max']-2097152,job_record,
                                     CONFIG['evidence_expanded_bytes_max'],collection_failed)
    returncode = collected['returncode']
    run(['aws','s3','cp',str(bundle),'s3://'+CONFIG['bucket']+'/results/artifacts.zip','--region',CONFIG['region']])
    complete = {'sha256':sha(bundle),'bytes':bundle.stat().st_size,'returncode':returncode,'job':CONFIG['job'],
                'entrypoint':'cas_meta3.native_demo','learning_performed':False,'qualification_status':'UNQUALIFIED',
                'partial_evidence':collected['partial_evidence'],'omitted_full_file_count':collected['omitted_full_file_count']}
    if 'native_demo_binding' in collected:
        complete['native_demo_binding'] = collected['native_demo_binding']
    (root/'complete.json').write_text(json.dumps(complete))
    run(['aws','s3','cp',str(root/'complete.json'),'s3://'+CONFIG['bucket']+'/results/complete.json','--region',CONFIG['region']])
sys.exit(returncode)
'''

def user_data(config: dict, remote_sha256: str | None = None) -> str:
    remote_sha256 = remote_sha256 or hashlib.sha256(remote_program(config).encode()).hexdigest()
    if not SHA256.fullmatch(remote_sha256): raise LaunchRefused("REMOTE_SCRIPT_SHA_REQUIRED")
    # Timer is armed before network access; EXIT covers bootstrap errors as well.
    text = "\n".join([
        "#!/bin/bash", "set -eu", "umask 077", "export PYTHONDONTWRITEBYTECODE=1",
        "trap 'test ! -f /opt/cas-meta3/bootstrap.log || { tail -c 1048576 /opt/cas-meta3/bootstrap.log > /opt/cas-meta3/bootstrap-tail.log; aws s3 cp /opt/cas-meta3/bootstrap-tail.log " + shlex.quote("s3://" + config["bucket"] + "/results/bootstrap.log") + " --region " + shlex.quote(config["region"]) + " || true; }; shutdown -h now' EXIT",
        "( sleep " + str(config['runtime_seconds_max']-100) + "; shutdown -h now ) >/dev/null 2>&1 &",
        "mkdir -p /opt/cas-meta3",
        "exec > /opt/cas-meta3/bootstrap.log 2>&1",
        "command -v aws >/dev/null || { echo AWS_CLI_REQUIRED; exit 1; }",
        "PY=''",
        "for p in python3.12 python3.11 /opt/conda/bin/python /opt/pytorch/bin/python /home/ubuntu/anaconda3/bin/python /home/ubuntu/miniconda3/bin/python python3; do",
        "  if command -v \"$p\" >/dev/null 2>&1 && \"$p\" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,12)' 2>/dev/null; then PY=\"$p\"; break; fi",
        "done",
        "test -n \"$PY\" || { echo SUPPORTED_PYTHON_REQUIRED; exit 1; }",
        "aws s3 cp " + shlex.quote("s3://"+config["bucket"]+"/input/remote.py") + " /opt/cas-meta3/remote.py --region " + shlex.quote(config["region"]),
        "echo '" + remote_sha256 + "  /opt/cas-meta3/remote.py' | sha256sum -c -",
        '"$PY" /opt/cas-meta3/remote.py', "",
    ])
    if len(text.encode()) > 16384:
        raise LaunchRefused("EC2_USER_DATA_SIZE_CEILING")
    return text


def execute(args: argparse.Namespace, plan: dict, manifest: dict) -> dict:
    validate_approval(args.approved_cap_usd, plan)
    with campaign_execution_lock() as execution_lock:
        return _execute_locked(args, plan, manifest, execution_lock)


def _execute_locked(args: argparse.Namespace, plan: dict, manifest: dict, execution_lock: dict) -> dict:
    """The public execute wrapper owns its local lock until all cleanup ends."""
    validate_approval(args.approved_cap_usd, plan)
    launcher_identity = verify_launcher_identity(manifest)
    continued_budget = budget.read_ledger()
    if Decimal(continued_budget["remaining_unreserved_usd"]) < Decimal(plan["per_launch_reserved_cap_usd"]):
        raise LaunchRefused("CAMPAIGN_BUDGET_EXHAUSTED")
    # boto3 is intentionally unavailable to the plan/contract-test path.
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    if not re.fullmatch(r"subnet-[0-9a-f]+", args.subnet_id or ""):
        raise LaunchRefused("EXPLICIT_SUBNET_REQUIRED")
    output = Path(args.receipt_dir).resolve()
    if not output.is_relative_to(PILOT_ROOT) or output == PILOT_ROOT or output.exists():
        raise LaunchRefused("NEW_RECEIPT_DIRECTORY_INSIDE_PILOT_REQUIRED")
    cfg = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=args.profile, region_name=plan["region"])
    clients = {s: session.client(s, config=cfg) for s in ("sts", "ec2", "iam", "s3", "scheduler")}
    sts, ec2, iam, s3, scheduler = (clients[s] for s in clients)
    identity = sts.get_caller_identity()
    if identity["Account"] != plan["account_id"]:
        raise LaunchRefused("AWS_ACCOUNT_MISMATCH")
    subnet = ec2.describe_subnets(SubnetIds=[args.subnet_id])["Subnets"][0]
    images = ec2.describe_images(ImageIds=[plan["ami_id"]])["Images"]
    if len(images) != 1 or images[0]["State"] != "available" or images[0].get("RootDeviceName") != "/dev/sda1" or images[0].get("OwnerId") != "898082745236":
        raise LaunchRefused("PINNED_AMI_UNAVAILABLE")
    quota = session.client("service-quotas",config=cfg).get_service_quota(ServiceCode="ec2",QuotaCode="L-DB2E81BA")
    if quota["Quota"]["Value"] < 8:
        raise LaunchRefused("CURRENT_G_GPU_QUOTA_BELOW_EIGHT_VCPUS")
    active = ec2.describe_instances(Filters=[{"Name":"tag-key","Values":["cas_meta_job"]},{"Name":"instance-state-name","Values":["pending","running","stopping","shutting-down"]}])
    if active.get("NextToken") or any(group["Instances"] for group in active["Reservations"]):
        raise LaunchRefused("EXISTING_ACTIVE_CAS_JOB_REQUIRES_RECONCILIATION")
    pricing = session.client("pricing", region_name="us-east-1", config=cfg)
    fields = {"instanceType": plan["instance_type"], "location": "US West (Oregon)", "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used", "marketoption":"OnDemand", "operation":"RunInstances"}
    prices = pricing.get_products(ServiceCode="AmazonEC2", Filters=[{"Type":"TERM_MATCH","Field":k,"Value":v} for k,v in fields.items()])["PriceList"]
    rates = [Decimal(d["pricePerUnit"]["USD"]) for raw in prices for t in json.loads(raw)["terms"]["OnDemand"].values() for d in t["priceDimensions"].values() if d["unit"] == "Hrs"]
    if rates != [Decimal(plan["on_demand_hourly_usd_max"])]:
        raise LaunchRefused("CURRENT_PRICE_REQUIRES_NEW_PLAN")
    job = "cas-meta3-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]
    budget_reservation = reserve_budget(job,args.source_sha,args.sha256,plan)
    bucket = job + "-" + plan["account_id"]
    worker_role, timer_role = job + "-worker", job + "-timer"
    tags = [{"Key":"cas_meta_job","Value":job}]
    receipt = {"status":"STARTING","job":job,"plan":plan,"explicit_approved_cap_argument_usd":args.approved_cap_usd,"task_budget_reservation":budget_reservation,"local_launcher_identity":launcher_identity,"source_sha":args.source_sha,"archive_sha256":args.sha256,"manifest":manifest,"caller_arn":identity["Arn"],"official_price_response":prices,"resources":{},"resource_intents":{},"execution_lock":execution_lock,"events":[],"cleanup_errors":[]}
    receipt.update(entrypoint=frozen.ENTRYPOINT,learning_performed=False,qualification_status="UNQUALIFIED")
    output.mkdir(parents=True)
    def save():
        (output / "launch_receipt.json").write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
    def record(event, **details):
        receipt["events"].append({"time":datetime.now(timezone.utc).isoformat(),"event":event,**details}); save()
    def role(name, service, statements):
        trust = {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":service},"Action":"sts:AssumeRole"}]}
        created = create_declared_auxiliary(receipt,name,"role",name,
            lambda: iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Tags=tags),record)["Role"]
        receipt["resources"][name] = created["Arn"]; save()
        iam.put_role_policy(RoleName=name, PolicyName="job-only", PolicyDocument=json.dumps({"Version":"2012-10-17","Statement":statements}))
        return created["Arn"]
    iid = None
    launch_attempted = False
    artifact_verified = False
    try:
        create_declared_auxiliary(receipt,"bucket","bucket",bucket,
            lambda: s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint":plan["region"]}),record)
        receipt["resources"]["bucket"] = bucket; save()
        s3.put_bucket_tagging(Bucket=bucket,Tagging={"TagSet":tags})
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={k:True for k in ("BlockPublicAcls","IgnorePublicAcls","BlockPublicPolicy","RestrictPublicBuckets")})
        s3.put_bucket_encryption(Bucket=bucket,ServerSideEncryptionConfiguration={"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]})
        s3.put_bucket_lifecycle_configuration(Bucket=bucket,LifecycleConfiguration={"Rules":[{"ID":"job-seven-days","Status":"Enabled","Filter":{"Prefix":""},"Expiration":{"Days":7},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":1}}]})
        receipt["s3_lifecycle_confirmed"] = True; save()
        role(worker_role,"ec2.amazonaws.com",[{"Effect":"Allow","Action":["s3:GetObject"],"Resource":[f"arn:aws:s3:::{bucket}/input/{key}" for key in ("payload.zip","permit.json","remote.py")]},{"Effect":"Allow","Action":["s3:PutObject"],"Resource":[f"arn:aws:s3:::{bucket}/results/{key}" for key in ("artifacts.zip","complete.json","bootstrap.log")]}])
        create_declared_auxiliary(receipt,"instance_profile","instance_profile",worker_role,
            lambda: iam.create_instance_profile(InstanceProfileName=worker_role, Tags=tags),record)
        receipt["resources"]["instance_profile"] = worker_role; save()
        iam.add_role_to_instance_profile(InstanceProfileName=worker_role,RoleName=worker_role)
        timer_arn = role(timer_role,"scheduler.amazonaws.com",[{"Effect":"Allow","Action":"ec2:TerminateInstances","Resource":f"arn:aws:ec2:{plan['region']}:{plan['account_id']}:instance/*","Condition":{"StringEquals":{"ec2:ResourceTag/cas_meta_job":job}}}])
        sg = create_declared_auxiliary(receipt,"security_group","security_group",job,
            lambda: ec2.create_security_group(GroupName=job, Description="CAS-META-3 outbound HTTPS only", VpcId=subnet["VpcId"], TagSpecifications=[{"ResourceType":"security-group","Tags":tags}]),record,vpc_id=subnet["VpcId"])["GroupId"]
        receipt["resources"]["security_group"] = sg; save()
        ec2.revoke_security_group_egress(GroupId=sg,IpPermissions=[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}])
        ec2.authorize_security_group_egress(GroupId=sg,IpPermissions=[{"IpProtocol":"tcp","FromPort":443,"ToPort":443,"IpRanges":[{"CidrIp":"0.0.0.0/0"}]}])
        s3.upload_file(str(Path(args.archive).resolve()),bucket,"input/payload.zip")
        config = {**plan,"job":job,"bucket":bucket,"archive_sha256":args.sha256,"manifest":manifest}
        # Put the complete manifest outside EC2's 16KiB user-data limit.
        remote = remote_program(config)
        s3.put_object(Bucket=bucket,Key="input/remote.py",Body=remote.encode())
        script_sha = hashlib.sha256(remote.encode()).hexdigest()
        bootstrap = user_data(config,script_sha)
        if len(bootstrap.encode()) > 16384: raise LaunchRefused("EC2_USER_DATA_SIZE_CEILING")
        record("BOOTSTRAP_PINNED",sha256=hashlib.sha256(bootstrap.encode()).hexdigest(),remote_sha256=script_sha)
        time.sleep(10) # IAM propagation, not a retry of a job.
        launch_time = datetime.now(timezone.utc)
        deadline = launch_time + timedelta(seconds=plan["runtime_seconds_max"])
        launch_attempted = True
        receipt["run_instances_client_token"] = job
        record("INSTANCE_LAUNCH_ATTEMPTED",client_token=job)
        launched = ec2.run_instances(ImageId=plan["ami_id"],InstanceType=plan["instance_type"],MinCount=1,MaxCount=1,ClientToken=job,IamInstanceProfile={"Name":worker_role},InstanceInitiatedShutdownBehavior="terminate",MetadataOptions={"HttpTokens":"required","HttpEndpoint":"enabled"},NetworkInterfaces=[{"DeviceIndex":0,"SubnetId":args.subnet_id,"Groups":[sg],"AssociatePublicIpAddress":True,"DeleteOnTermination":True}],BlockDeviceMappings=[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":75,"VolumeType":"gp3","Encrypted":True,"DeleteOnTermination":True}}],TagSpecifications=[{"ResourceType":"instance","Tags":tags},{"ResourceType":"volume","Tags":tags}],UserData=bootstrap)
        iid = launched["Instances"][0]["InstanceId"]
        receipt["provider_launch_time"] = launched["Instances"][0].get("LaunchTime",launch_time).isoformat()
        receipt["resources"]["instance"] = iid; record("INSTANCE_CREATED",instance_id=iid,deadline=deadline.isoformat())
        target = {"Arn":"arn:aws:scheduler:::aws-sdk:ec2:terminateInstances","RoleArn":timer_arn,"Input":json.dumps({"InstanceIds":[iid]}),"RetryPolicy":{"MaximumRetryAttempts":0,"MaximumEventAgeInSeconds":60}}
        expression = "at("+deadline.strftime("%Y-%m-%dT%H:%M:%S")+")"
        # Record the exact name before creation so a lost response cannot orphan it.
        receipt["resources"]["schedule"] = job; save()
        scheduler.create_schedule(Name=job,ScheduleExpression=expression,ScheduleExpressionTimezone="UTC",FlexibleTimeWindow={"Mode":"OFF"},Target=target,ActionAfterCompletion="DELETE")
        confirmed = scheduler.get_schedule(Name=job)
        verify_schedule(confirmed,target,expression)
        record("CLOUD_DEADLINE_CONFIRMED",schedule=job,target=target)
        s3.put_object(Bucket=bucket,Key="input/permit.json",Body=json.dumps({"job":job,"archive_sha256":args.sha256,"cloud_deadline_confirmed":True,"deadline":deadline.isoformat()}).encode())
        while datetime.now(timezone.utc) < deadline:
            try:
                result = json.loads(s3.get_object(Bucket=bucket,Key="results/complete.json")["Body"].read())
                if result["job"] != job or not SHA256.fullmatch(result["sha256"]) or not 0 < result["bytes"] <= plan["artifact_bytes_max"]:
                    raise LaunchRefused("REMOTE_RESULT_IDENTITY_OR_SIZE")
                if result.get("entrypoint") != frozen.ENTRYPOINT or result.get("learning_performed") is not False or result.get("qualification_status") != "UNQUALIFIED":
                    raise LaunchRefused("REMOTE_RESULT_MODE_MISMATCH")
                head = s3.head_object(Bucket=bucket,Key="results/artifacts.zip")
                if head["ContentLength"] != result["bytes"]: raise LaunchRefused("REMOTE_RESULT_SIZE_MISMATCH")
                artifact = output / "cloud_artifacts.zip"
                s3.download_file(bucket,"results/artifacts.zip",str(artifact))
                collection = verify_downloaded_packet(artifact,result,job,args.source_sha,plan)
                artifact_verified = True
                receipt["result"] = result
                receipt["artifact_collection"] = collection
                receipt["status"] = "AWS_JOB_FINISHED" if result["returncode"] == 0 else "AWS_JOB_FAILED"
                record("ARTIFACT_DOWNLOADED_AND_HASH_VERIFIED",path=str(artifact),sha256=result["sha256"])
                break
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in ("NoSuchKey","404"): raise
            state = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]["State"]["Name"]
            if state in ("terminated","shutting-down"):
                raise LaunchRefused("INSTANCE_ENDED_WITHOUT_COMPLETION_RECEIPT")
            time.sleep(15)
        else: raise LaunchRefused("LOCAL_WATCHDOG_DEADLINE")
    except BaseException as exc:
        receipt["status"] = "AWS_JOB_BLOCKED_OR_FAILED"
        record("ERROR",error=type(exc).__name__,message=str(exc))
    finally:
        # A missing RunInstances response is not evidence that no instance exists.
        terminated = not launch_attempted
        if launch_attempted and iid is None:
            try:
                recovered = reconcile_instance(ec2,job)
                iid = recovered["InstanceId"]
                receipt["resources"]["instance"] = iid
                receipt["provider_launch_time"] = recovered["LaunchTime"].isoformat()
                record("INSTANCE_IDENTITY_RECOVERED",instance_id=iid,client_token=job)
            except Exception as exc:
                receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED: "+str(exc))
                record("INSTANCE_IDENTITY_UNCONFIRMED_RESOURCES_RETAINED")
        if iid:
            try:
                terminate_owned_instance(ec2,iid,job,artifact_verified=artifact_verified,record=record)
                terminated = True; record("INSTANCE_TERMINATION_CONFIRMED",instance_id=iid)
                seconds = (datetime.now(timezone.utc)-datetime.fromisoformat(receipt["provider_launch_time"])).total_seconds()
                receipt["cost_estimate"] = {"instance_wall_clock_seconds_upper_observation":seconds,"compute_ebs_ipv4_usd_estimate":str((Decimal(str(seconds))/Decimal(3600))*(Decimal(plan['on_demand_hourly_usd_max'])+Decimal(75)*Decimal("0.08")/Decimal(720)+Decimal("0.005"))),"excluded":"S3 requests and retention, transfer, taxes; not an AWS invoice"}
            except Exception as exc: receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED: "+str(exc))
        if terminated:
            if iid:
                try:
                    receipt["remaining_job_volumes"] = confirm_deleted_volumes(ec2,job,record)
                    if receipt["remaining_job_volumes"]: receipt["cleanup_errors"].append("EBS_DELETION_NOT_YET_CONFIRMED")
                except Exception as exc: receipt["cleanup_errors"].append("EBS_CHECK_FAILED: "+str(exc))
            reconcile_auxiliary_intents(ec2,iam,s3,receipt,job,record)
            remove_owned_auxiliary_resources(ec2,iam,scheduler,receipt,job,worker_role,timer_role,record)
            save()
        if "bucket" in receipt["resources"]:
            try:
                head = s3.head_object(Bucket=bucket,Key="results/bootstrap.log")
                if head["ContentLength"] > 1048576: raise LaunchRefused("BOOTSTRAP_LOG_CEILING")
                bootstrap_log = output / "bootstrap.log"
                s3.download_file(bucket,"results/bootstrap.log",str(bootstrap_log))
                receipt["bootstrap_log_sha256"] = digest(bootstrap_log)
            except ClientError as exc:
                receipt["bootstrap_log_status"] = exc.response["Error"]["Code"]
            except Exception as exc:
                receipt["bootstrap_log_status"] = type(exc).__name__ + ": " + str(exc)
        receipt["termination_confirmed"] = terminated
        if terminated and "bucket" in receipt["resources"]:
            try:
                check_tag(s3.get_bucket_tagging(Bucket=bucket)["TagSet"],job)
                if artifact_verified:
                    s3.delete_objects(Bucket=bucket,Delete={"Objects":[{"Key":"input/"+key} for key in ("payload.zip","remote.py","permit.json")]})
                    record("OWNED_SOURCE_INPUT_OBJECTS_REMOVED_AFTER_VERIFIED_DOWNLOAD")
                result_objects = s3.list_objects_v2(Bucket=bucket,Prefix="results/")
                keys = [item["Key"] for item in result_objects.get("Contents",[])]
                if result_objects.get("IsTruncated") or not set(keys).issubset({"results/artifacts.zip","results/complete.json","results/bootstrap.log"}) or len(keys)>3:
                    raise LaunchRefused("UNEXPECTED_RESULT_OBJECTS")
                if sum(item["Size"] for item in result_objects.get("Contents",[])) > plan["artifact_bytes_max"]:
                    raise LaunchRefused("RESULT_OBJECT_TOTAL_SIZE_CEILING")
                receipt["stored_result_objects"] = result_objects.get("Contents",[])
            except Exception as exc:
                receipt["cleanup_errors"].append("S3_RETENTION_OR_OBJECT_LIMIT_UNCONFIRMED: "+str(exc))
        receipt["s3_retention"] = ("Dedicated job bucket objects were configured to expire after 7 days; empty bucket may remain without storage charges. Local evidence is retained."
            if receipt.get("s3_lifecycle_confirmed") is True else
            "NOT_CONFIRMED: no successful lifecycle configuration was recorded; inspect any exact predeclared bucket identity. No retention or deletion is claimed for an ownership-unconfirmed bucket.")
        if receipt["cleanup_errors"]: receipt["status"] = "CLEANUP_REQUIRES_ATTENTION"
        save()
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--archive")
    parser.add_argument("--sha256")
    parser.add_argument("--source-sha")
    parser.add_argument("--approved-cap-usd")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--subnet-id")
    parser.add_argument("--receipt-dir")
    args = parser.parse_args(argv)
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    try:
        manifest = None
        if args.archive:
            manifest = validate_archive(Path(args.archive),args.sha256 or "",args.source_sha or "",plan)
        if not args.execute:
            print(json.dumps({"plan":plan,"archive_verified":manifest is not None,"aws_actions_performed":False},indent=2)); return 0
        validate_approval(args.approved_cap_usd,plan)
        if manifest is None or not args.receipt_dir:
            raise LaunchRefused("PINNED_ARCHIVE_AND_RECEIPT_DIRECTORY_REQUIRED")
        receipt = execute(args,plan,manifest)
        print(json.dumps({"status":receipt["status"],"receipt_dir":args.receipt_dir},indent=2))
        return 0 if receipt["status"] == "AWS_JOB_FINISHED" else 1
    except (LaunchRefused,budget.BudgetRefused,ValueError,KeyError,OSError,RuntimeError,zipfile.BadZipFile,json.JSONDecodeError) as exc:
        print(json.dumps({"status":"LAUNCH_REFUSED","reason":str(exc)})); return 2


if __name__ == "__main__":
    raise SystemExit(main())
