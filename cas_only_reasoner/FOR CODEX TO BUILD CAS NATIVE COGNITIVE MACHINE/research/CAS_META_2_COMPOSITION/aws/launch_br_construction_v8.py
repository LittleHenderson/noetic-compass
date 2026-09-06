"""Dedicated B/R construction launch; ordinary planning is pure and unpaid.

Only execute() can reserve or create resources. It uses registered standing
campaign authority, never a prefix approval parser or a training entrypoint.
"""
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256, file_digest
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import time
import uuid
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = {"profile": "same_state_br_construction_v8", "entrypoint": "cas_meta2.br_construction_v8"}
PARENT_FILES = ("aws/launch_br_construction_v8.py", "aws/br_remote_v8.py", "aws/br_package_v8.py")
FROZEN_PINS = {
    "aws/launch_prefix_diagnostic_v8.py": "d9853e6cbb41fd5efdd927e217bde35fc98a05bf9d784c500cc82b04ba219e48",
    "aws/prefix_remote_v8.py": "e72f5937895d856797e9dae200100b279a39bdbe4850f67b5405a70cb9719f8b",
    "aws/launch_prototype_v7.py": "90f7a8086416ac39c49d9d344d33b128ae19106638f335ceb14cdd26f038577a",
    "aws/budget.py": "77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0",
    "tools/experiment_profiles_prototype_v7.py": "3331ce53d6f3f57b94cb7603f2b53f3c309a899ab2596b4b040fa1b01ccf6ee0",
}
STANDING_MESSAGE_SHA256 = "d0b640ec3059ea73d677b632a4bc2f3188bbcd87b231e4362914e219459fc5bb"
INPUT_KEYS = ("source.zip", "remote.py", "permit.json")
RESULT_KEYS = ("artifacts.zip", "complete.json", "bootstrap.log")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
JOB = re.compile(r"cas-meta2-[0-9]{14}-[0-9a-f]{8}\Z")
WORKER_SUCCESS_FILES = (
    "public.json", "progress.json", "prelude/native.db", "preclose_witness.json",
    "preclose_witness_check.json", "copies/master.sqlite", "copies/B.sqlite",
    "copies/R.sqlite", "copies/receipt.json", "arm_B/before_witness.json",
    "arm_B/before_witness_check.json", "arm_B/result.json",
    "arm_R/before_witness.json", "arm_R/before_witness_check.json", "arm_R/result.json",
)


class LaunchRefused(ValueError):
    pass


def require(value, reason):
    if not value:
        raise LaunchRefused(reason)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decoded(raw):
    def unique(items):
        value = {}
        for key, entry in items:
            require(key not in value, "BR_DUPLICATE_JSON_KEY")
            value[key] = entry
        return value
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: require(False, "BR_NONFINITE_JSON"))


def digest(raw):
    return sha256(raw).hexdigest()


def safe_file(path, maximum=32 * 1024**2):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "BR_SOURCE_OR_EVIDENCE_LINK")
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
            and metadata.st_size <= maximum, "BR_BOUNDED_REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "BR_FILE_SIZE_LIMIT")
    return raw


def read_pinned(path, expected, maximum=32 * 1024**2):
    require(type(expected) is str and HEX64.fullmatch(expected), "BR_EXACT_HASH_REQUIRED")
    raw = safe_file(path, maximum)
    require(digest(raw) == expected, "BR_PINNED_BYTES_CHANGED")
    return raw


def verify_parent_source(parent_sha):
    require(type(parent_sha) is str and SHA1.fullmatch(parent_sha), "BR_PARENT_COMMIT_REQUIRED")
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    require(subprocess.check_output(["git", "rev-parse", parent_sha + "^{commit}"], cwd=repo,
                                   text=True).strip() == parent_sha, "BR_PARENT_COMMIT_REQUIRED")
    identity = {}
    for relative in (*PARENT_FILES, *FROZEN_PINS):
        path = ROOT / relative
        raw = safe_file(path)
        committed = subprocess.check_output(["git", "cat-file", "blob",
            parent_sha + ":" + path.relative_to(repo).as_posix()], cwd=repo)
        require(raw == committed, "BR_PARENT_SOURCE_NOT_COMMITTED:" + relative)
        identity[relative] = digest(raw)
        if relative in FROZEN_PINS:
            require(identity[relative] == FROZEN_PINS[relative], "BR_FROZEN_HELPER_CHANGED:" + relative)
    return identity


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    require(spec is not None and spec.loader is not None, "BR_HELPER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def helpers(parent_sha):
    identity = verify_parent_source(parent_sha)
    return {
        "identity": identity,
        "package": load_module("br_parent_package", "aws/br_package_v8.py"),
        "plumbing": load_module("br_parent_bounded_plumbing", "aws/launch_prefix_diagnostic_v8.py"),
        "old": load_module("br_parent_owned_cleanup", "aws/launch_prototype_v7.py"),
        "remote": load_module("br_parent_remote", "aws/br_remote_v8.py"),
    }


def resource_plan():
    return {"instance_count": 1, "gpu_count": 1, "instance_type": "g7.2xlarge",
        "account_id": "807562639912", "region": "us-west-2", "ami_id": "ami-0fbbd0facbc9e3cff",
        "runtime_seconds_max": 3600, "worker_seconds_max": 600,
        "cloud_shutdown_seconds": 3480, "guest_shutdown_seconds": 3400,
        "automatic_retries": 0, "on_demand_hourly_usd_max": "2.52", "ancillary_reserved_usd": "1.00",
        "per_launch_reserved_cap_usd": "4.00", "ebs_gb": 75, "ebs_type": "gp3",
        "ebs_iops": 3000, "ebs_throughput_mib_per_second": 125, "ebs_encrypted": True,
        "delete_on_termination": True, "artifact_bytes_max": 256 * 1024**2,
        "evidence_expanded_bytes_max": 512 * 1024**2, "artifact_objects_max": 3,
        "s3_retention_days": 7, "input_bytes_max": 16 * 1024**2, "download_bytes_max": 256 * 1024**2,
        "s3_read_requests_max": 1000, "s3_write_requests_max": 1000, "scheduler_invocations_max": 1,
        "inbound_rules": [], "egress_tcp_ports": [443], "required_gpu_name_contains": "RTX PRO 4500",
        "training": False, "native_execution": True, "later_curriculum_execution": False,
        "local_neural_execution": False}


def construction_scope():
    return {"max_seconds": 600, "max_cost_usd": "4.00", "prelude_policy_units": 32768,
        "arm_policy_units": 8192, "binding": 0, "prelude": ["A", "B", "C", "R"],
        "arm_cjt": "C", "arm_expected_symbol": "L2", "seed": 7, "training": False,
        "native_execution": True, "max_image_bytes": 67108864}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == "cas-meta2-br-launch-request/8",
            "BR_DEDICATED_REQUEST_REQUIRED")
    require(type(request.get("job")) is str and JOB.fullmatch(request["job"]), "BR_UNIQUE_JOB_REQUIRED")
    require(request.get("experiment") == EXPERIMENT
            and encoded(request.get("resource_plan")) == encoded(resource_plan())
            and encoded(request.get("construction_scope")) == encoded(construction_scope()),
            "BR_EXACT_SCOPE_REQUIRED")
    for key in ("parent_source_sha", "worker_source_sha"):
        require(type(request.get(key)) is str and SHA1.fullmatch(request[key]), "BR_SOURCE_SHA_REQUIRED")
    for key in ("source_archive_sha256", "source_manifest_sha256"):
        require(type(request.get(key)) is str and HEX64.fullmatch(request[key]), "BR_SOURCE_HASH_REQUIRED")
    require(type(request.get("source_archive_bytes")) is int and 0 < request["source_archive_bytes"] <= 16 * 1024**2,
            "BR_SOURCE_ARCHIVE_BOUND")
    require(type(request.get("subnet_id")) is str and re.fullmatch(r"subnet-[0-9a-f]{8,17}", request["subnet_id"]),
            "BR_SUBNET_REQUIRED")
    require(request.get("standing_authority_registration_required") is True
            and request.get("launch_authorized") is False
            and not any("development" in k or "checkpoint" in k for k in request),
            "BR_REGISTERED_STANDING_AUTHORITY_REQUIRED")


def source_for(request, package):
    source = package.inspect_archive(request["source_archive"],
        expected_sha256=request["source_archive_sha256"], expected_source_sha=request["worker_source_sha"],
        expected_manifest_sha256=request["source_manifest_sha256"])
    require(len(read_pinned(request["source_archive"], request["source_archive_sha256"])) == request["source_archive_bytes"],
            "BR_SOURCE_ARCHIVE_SIZE_CHANGED")
    require(source["files_sha256"]["research/CAS_META_2_COMPOSITION/aws/br_package_v8.py"]
            == digest(safe_file(ROOT / "aws/br_package_v8.py")), "BR_PACKAGER_SOURCE_DIFFERS_FROM_WORKER")
    return source


def build_request(parent_sha, subnet_id, source_archive, source_archive_sha256, worker_source_sha, source_manifest_sha256):
    h = helpers(parent_sha)
    request = {"schema": "cas-meta2-br-launch-request/8", "experiment": EXPERIMENT,
        "job": "cas-meta2-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8],
        "parent_source_sha": parent_sha, "parent_file_sha256": h["identity"],
        "worker_source_sha": worker_source_sha, "source_archive_sha256": source_archive_sha256,
        "source_manifest_sha256": source_manifest_sha256, "source_archive": str(Path(source_archive).absolute()),
        "source_archive_bytes": len(read_pinned(source_archive, source_archive_sha256)),
        "subnet_id": subnet_id, "resource_plan": resource_plan(), "construction_scope": construction_scope(),
        "standing_authority_registration_required": True, "launch_authorized": False,
        "provider_calls": False, "new_reservation": False}
    validate_request(request)
    source_for(request, h["package"])
    return request


def validate_authority(path, expected, request, request_sha256, ledger):
    record = decoded(read_pinned(path, expected, 1024**2))
    wanted = {"schema": "cas-meta2-br-standing-authority/8", "standing_campaign_authorization": True,
        "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00", "experiment": EXPERIMENT,
        "training": False, "native_execution": True, "launch_request_sha256": request_sha256,
        **{k: request[k] for k in ("job", "parent_source_sha", "worker_source_sha",
                                  "source_archive_sha256", "source_manifest_sha256")}}
    require(all(type(record.get(k)) is type(v) and record[k] == v for k, v in wanted.items()),
            "BR_STANDING_AUTHORITY_SCOPE_OR_JOB_CHANGED")
    campaign = record.get("campaign_approval", {})
    require(campaign == {k: ledger["approval"][k] for k in ("path", "sha256")},
            "BR_CANONICAL_CAMPAIGN_AUTHORITY_REQUIRED")
    require(Path(campaign["path"]).is_absolute(), "BR_ABSOLUTE_AUTHORITY_PATH_REQUIRED")
    read_pinned(campaign["path"], campaign["sha256"])
    message = record.get("standing_user_message", {})
    require(type(message.get("path")) is str and Path(message["path"]).is_absolute()
            and message.get("sha256") == STANDING_MESSAGE_SHA256, "BR_FULL_STANDING_MESSAGE_REQUIRED")
    read_pinned(message["path"], STANDING_MESSAGE_SHA256, 1024**2)
    require(ledger["owner_task_cap_usd"] == "400.00" and ledger["no_automatic_refund"] is True,
            "BR_EXISTING_CAMPAIGN_CAP_REQUIRED")
    return {**record, "authority_artifact_sha256": expected}


def provider_json(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: provider_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [provider_json(v) for v in value]
    return value


def worker_permit(request, source, reservation, ledger, instance_id, deadline):
    require(type(instance_id) is str and re.fullmatch(r"i-[0-9a-f]{17}", instance_id), "BR_REAL_INSTANCE_REQUIRED")
    base = "/opt/cas-meta2-br/"
    plan = {"schema": "cas-meta2-br-construction-plan/8", "launch_enabled": True,
        "job": request["job"], "instance_id": instance_id, "source_sha": request["worker_source_sha"],
        **construction_scope(), "resource_plan": request["resource_plan"],
        "source_manifest": {"path": base + "package/br_source_manifest.json", "sha256": request["source_manifest_sha256"]},
        "source_archive": {"path": base + "source.zip", "sha256": request["source_archive_sha256"]},
        "reservation_receipt": {"path": base + "launch/reservation_receipt.json", "sha256": digest(encoded(reservation))},
        "ledger_snapshot": {"path": base + "launch/ledger_snapshot.json", "sha256": digest(encoded(ledger))}}
    return {"job": request["job"], "archive_sha256": request["source_archive_sha256"],
        "cloud_deadline_confirmed": True, "instance_id": instance_id, "deadline": deadline.isoformat(),
        "worker_plan": plan, "worker_plan_sha256": digest(encoded(plan)),
        "reservation_receipt": reservation, "ledger_snapshot": ledger}


def remote_config(request, source):
    return {"schema": "cas-meta2-br-remote-config/8", "job": request["job"],
        "bucket": request["job"] + "-807562639912", "region": "us-west-2", "account_id": "807562639912",
        **{k: request[k] for k in ("parent_source_sha", "worker_source_sha", "source_archive_sha256",
                                  "source_archive_bytes", "source_manifest_sha256")},
        "source_manifest": source, "package_layout": source["base"]["package_layout"],
        "resource_plan": request["resource_plan"], "max_worker_seconds": 600,
        "artifact_bytes_max": 256 * 1024**2, "evidence_expanded_bytes_max": 512 * 1024**2,
        "experiment": EXPERIMENT}


def safe_member(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name
            and not any(ord(c) < 32 for c in name)
            and all(p not in ("", ".", "..") for p in name.split("/")), "BR_UNSAFE_RESULT_PATH")
    return name


def verify_packet(artifact, result, request, worker_plan_sha256):
    """Verify full bytes and explicit B/R outputs without native or model imports."""
    plan = request["resource_plan"]
    require(type(result.get("returncode")) is int and result["returncode"] in (0, 1)
            and result.get("source_sha") == request["worker_source_sha"]
            and result.get("parent_source_sha") == request["parent_source_sha"]
            and result.get("job") == request["job"] and result.get("experiment") == EXPERIMENT,
            "BR_RESULT_IDENTITY")
    raw = read_pinned(artifact, result["sha256"], plan["artifact_bytes_max"])
    require(len(raw) == result["bytes"], "BR_RESULT_BYTES")
    # Parse the same pinned bytes; do not reopen a pathname after hashing it.
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [safe_member(i.orig_filename) for i in infos]
        require(len(names) == len(set(names)) == len({n.casefold() for n in names})
                and all(i.orig_filename == i.filename and not i.is_dir()
                    and stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG)
                    and not i.flag_bits & 1 for i in infos), "BR_UNSAFE_RESULT_ARCHIVE")
        require(sum(i.file_size for i in infos) <= plan["evidence_expanded_bytes_max"], "BR_RESULT_EXPANDED_LIMIT")
        archive_hashes = {}
        for name in names:
            with archive.open(name) as stream:
                archive_hashes[name] = file_digest(stream, "sha256").hexdigest()
        def value(name):
            require(archive.getinfo(name).file_size <= 32 * 1024**2, "BR_JSON_RECEIPT_SIZE_LIMIT")
            return decoded(archive.read(name))
        collection = value("artifact_collection_receipt.json")
        require(collection.get("job") == request["job"] and collection.get("source_sha") == request["worker_source_sha"]
                and collection.get("parent_source_sha") == request["parent_source_sha"]
                and collection.get("experiment") == EXPERIMENT and collection.get("returncode") == result["returncode"],
                "BR_COLLECTION_IDENTITY")
        if collection.get("full_file_counts_known") is False:
            require(result["returncode"] == 1 and collection.get("partial_evidence") is True
                    and collection.get("original_file_count") is None
                    and collection.get("included_full_file_count") == 0
                    and collection.get("omitted_full_file_count") is None
                    and type(collection.get("collection_failure")) is dict
                    and set(names) == {"artifact_collection_receipt.json"}, "BR_INVALID_EMERGENCY_PACKET")
            return {**collection, "parent_member_hashes_verified": 0, "archive_files_sha256": archive_hashes,
                    "original_member_coverage_verified": False,
                    "construction_status": None, "native_component_success": False,
                    "not_task_correctness_or_learning": True}
        require(type(collection.get("partial_evidence")) is bool
                and collection["partial_evidence"] == result.get("partial_evidence")
                and collection.get("omitted_full_file_count") == result.get("omitted_full_file_count"),
                "BR_RESULT_COLLECTION_DISAGREEMENT")
        index = collection.get("files", {})
        require(type(index) is dict, "BR_COLLECTION_INDEX_REQUIRED")
        for name, item in index.items():
            safe_member(name)
            require(type(item) is dict and type(item.get("bytes")) is int and item["bytes"] >= 0
                    and type(item.get("sha256")) is str and HEX64.fullmatch(item["sha256"]), "BR_COLLECTION_INDEX_INVALID")
            if name in names:
                require(archive_hashes[name] == item["sha256"] and archive.getinfo(name).file_size == item["bytes"],
                        "BR_COLLECTED_MEMBER_HASH_CHANGED:" + name)
        present = set(names) - {"artifact_collection_receipt.json"}
        extras = present - set(index)
        require(all(n.startswith("failure_tails/") and archive.getinfo(n).file_size <= 16384 for n in extras),
                "BR_UNINDEXED_ARCHIVE_MEMBER")
        if collection.get("partial_evidence") is False:
            require(present == set(index) and collection.get("omitted_full_file_count") == 0,
                    "BR_FULL_COLLECTION_COVERAGE")
        require(collection.get("original_file_count") == len(index)
                and collection.get("included_full_file_count") == len(present - extras)
                and collection.get("omitted_full_file_count") == len(set(index) - present),
                "BR_COLLECTION_COUNT_MISMATCH")
        worker_name = "construction/construction_receipt.json"
        worker = value(worker_name) if worker_name in names else None
        if worker is not None:
            require(worker.get("schema") == "cas-meta2-br-construction/8"
                    and worker.get("job") == request["job"] and worker.get("source_sha") == request["worker_source_sha"]
                    and worker.get("source_archive_sha256") == request["source_archive_sha256"]
                    and worker.get("source_manifest_sha256") == request["source_manifest_sha256"]
                    and worker.get("plan_sha256") == worker_plan_sha256 and worker.get("training") is False,
                    "BR_WORKER_RECEIPT_IDENTITY")
            mapping = worker.get("files_sha256", {})
            require(type(mapping) is dict, "BR_WORKER_FILE_MAP_REQUIRED")
            for relative, pin in mapping.items():
                safe_member(relative)
                name = "construction/" + relative
                require(type(pin) is str and HEX64.fullmatch(pin), "BR_WORKER_FILE_PIN_INVALID")
                if name in present:
                    require(name in index and index[name]["sha256"] == pin, "BR_WORKER_MEMBER_HASH_CHANGED")
            if collection.get("partial_evidence") is False:
                require({"construction/" + n for n in mapping} | {worker_name}
                        == {n for n in present if n.startswith("construction/")}, "BR_WORKER_FILE_COVERAGE")
        if result["returncode"] == 0:
            require(collection.get("partial_evidence") is False and worker is not None
                    and worker.get("status") == "BR_COMPONENT_EXECUTED" and worker.get("native_execution") is True
                    and worker.get("cleanup_errors") == [] and "failure" not in worker
                    and worker.get("task_conditioned_correctness") is None
                    and worker.get("postchecks", {}).get("source", {}).get("ok") is True
                    and worker.get("postchecks", {}).get("reservation", {}).get("ok") is True
                    and [r.get("cjt_id") for r in worker.get("prelude", [])] == ["A", "B", "C", "R"],
                    "BR_SUCCESS_WITHOUT_COMPLETE_NATIVE_RECEIPT")
            require({"construction/" + n for n in WORKER_SUCCESS_FILES} <= present, "BR_MANDATORY_NATIVE_OUTPUT_MISSING")
            for name in ("preclose_witness_check.json", "arm_B/before_witness_check.json", "arm_R/before_witness_check.json"):
                require(value("construction/" + name).get("ok") is True, "BR_NATIVE_BEFORE_STATE_REJECTED")
            for arm in ("B", "R"):
                arm_record = value("construction/arm_" + arm + "/result.json")
                require(arm_record == worker["arms"][arm] and arm_record.get("status") == "ACCEPTED"
                        and arm_record.get("input_producer") == arm
                        and arm_record.get("same_fixed_expectation") == "L2"
                        and [r.get("cjt_id") for r in arm_record.get("rows", [])] == ["C"],
                        "BR_ARM_RESULT_MISMATCH")
            for name in ("lifecycle/worker/receipt.json", "lifecycle/remote_receipt.json"):
                require(name in present, "BR_MANDATORY_LIFECYCLE_RECEIPT_MISSING")
            process = value("lifecycle/worker/receipt.json")
            remote = value("lifecycle/remote_receipt.json")
            require(process.get("exit_code") == 0 and process.get("failure") is None
                    and process.get("maximum_seconds") == 600
                    and remote.get("returncode") == 0 and remote.get("worker_process_started") is True
                    and remote.get("worker_component_completed") is True
                    and remote.get("neural_training") is False
                    and remote.get("source_sha") == request["worker_source_sha"]
                    and remote.get("parent_source_sha") == request["parent_source_sha"]
                    and remote.get("archive_sha256") == request["source_archive_sha256"]
                    and remote.get("source_manifest_sha256") == request["source_manifest_sha256"],
                    "BR_LIFECYCLE_EXIT_OR_IDENTITY_MISMATCH")
            for log in ("stdout.txt", "stderr.txt"):
                require(process.get("outputs", {}).get(log) == index.get("lifecycle/worker/" + log)
                        and "lifecycle/worker/" + log in present, "BR_PROCESS_RAW_OUTPUT_MISMATCH")
        return {**collection, "parent_member_hashes_verified": len(present - extras),
                "archive_files_sha256": archive_hashes, "original_member_coverage_verified": not collection["partial_evidence"],
                "construction_status": worker.get("status") if worker else None,
                "native_component_success": result["returncode"] == 0,
                "not_task_correctness_or_learning": True}


def execute(request_path, request_sha256, authority_path, authority_sha256, receipt_dir, profile="default"):
    request = decoded(read_pinned(request_path, request_sha256, 2 * 1024**2))
    validate_request(request)
    h = helpers(request["parent_source_sha"])
    require(h["identity"] == request["parent_file_sha256"], "BR_PARENT_REQUEST_IDENTITY_CHANGED")
    source = source_for(request, h["package"])
    output = Path(receipt_dir).absolute()
    require(not output.exists() and output.is_relative_to(ROOT / "records")
            and ".." not in output.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (output, *output.parents)), "BR_NEW_RECEIPT_DIRECTORY_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    preflight_receipt = {"schema": "cas-meta2-br-provider-preflight/8", "job": request["job"],
        "request_sha256": request_sha256, "status": "PREFLIGHT_ATTEMPT_STARTED",
        "new_reservation": False, "provider_resources_created": False}
    def save_preflight():
        (output / "preflight_receipt.json").write_bytes(encoded(preflight_receipt))
    save_preflight()
    try:
        lock = h["old"].campaign_execution_lock()
        lock.__enter__()
    except BaseException as error:
        preflight_receipt.update(status="BR_LAUNCH_PREFLIGHT_REFUSED", error=type(error).__name__, reason=str(error))
        save_preflight()
        (output / "launch_receipt.json").write_bytes(encoded(preflight_receipt))
        return preflight_receipt
    try:
        try:
            ledger = h["old"].budget.read_ledger()
            authority = validate_authority(authority_path, authority_sha256, request, request_sha256, ledger)
            require(Decimal(ledger["remaining_unreserved_usd"]) >= Decimal("4.00"), "BR_CAMPAIGN_BUDGET_EXHAUSTED")
            clients = h["plumbing"].client_factory(profile, "us-west-2")
            preflight = h["plumbing"].provider_preflight(clients, request)
            preflight_receipt.update(status="PREFLIGHT_READS_PASSED", result=provider_json(preflight))
        except BaseException as error:
            preflight_receipt.update(status="BR_LAUNCH_PREFLIGHT_REFUSED", error=type(error).__name__, reason=str(error))
            save_preflight()
            (output / "launch_receipt.json").write_bytes(encoded(preflight_receipt))
            return preflight_receipt
        save_preflight()
        return _run_authorized(request, request_sha256, authority, source, h["old"], h["remote"],
                               h["plumbing"], clients, preflight, output)
    finally:
        lock.__exit__(None, None, None)


def _run_authorized(request, request_sha256, authority, source, old, remote, plumbing, clients, preflight, output):
    """Dedicated orchestration; contract tests supply fake clients and fake ledger."""
    plan, job = request["resource_plan"], request["job"]
    s3, ec2, iam, scheduler = (clients[name] for name in ("s3", "ec2", "iam", "scheduler"))
    config = remote_config(request, source)
    bucket = config["bucket"]
    worker_role, timer_role = job + "-worker", job + "-timer"
    tags = [{"Key": "cas_meta_job", "Value": job}]
    receipt = {"schema": "cas-meta2-br-launch-receipt/8", "status": "STARTING",
        "job": job, "request_sha256": request_sha256, "standing_authority": authority,
        "parent_source_sha": request["parent_source_sha"], "source_sha": request["worker_source_sha"],
        "archive_sha256": request["source_archive_sha256"],
        "source_manifest_sha256": request["source_manifest_sha256"], "plan": plan, "experiment": EXPERIMENT,
        "provider_preflight": provider_json(preflight), "resources": {}, "events": [], "cleanup_errors": []}
    output.mkdir(parents=True, exist_ok=True)
    def save():
        path = output / "launch_receipt.json"
        raw = encoded(receipt)
        with path.open("wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    def record(event, **details):
        receipt["events"].append({"utc": datetime.now(timezone.utc).isoformat(), "event": event, **provider_json(details)})
        save()
    receipt["budget_reservation_state"] = "NOT_ATTEMPTED"
    save()
    try:
        # Source bytes and rendering are checked before reservation or provider mutation.
        script = remote.render_remote(config)
        bootstrap = remote.user_data(config, digest(script.encode()))
        require(len(bootstrap.encode()) <= 16384, "EC2_USER_DATA_SIZE_CEILING")
        require(verify_parent_source(request["parent_source_sha"]) == request["parent_file_sha256"],
                "PARENT_CHANGED_BEFORE_RESERVATION")
        source_bytes = read_pinned(request["source_archive"], request["source_archive_sha256"])
        require(len(source_bytes) + len(script.encode()) + 1024**2 <= plan["input_bytes_max"],
                "INPUT_UPLOAD_CEILING")
        receipt["budget_reservation_state"] = "ATTEMPTED_OUTCOME_UNCONFIRMED"
        record("BUDGET_RESERVATION_ATTEMPTED", reserved_usd="4.00", worker_source_sha=request["worker_source_sha"])
        reservation = old.budget.reserve_budget(job, request["worker_source_sha"], request["source_archive_sha256"], "4.00", plan)
        receipt["task_budget_reservation"] = reservation
        receipt["budget_reservation_state"] = "RESERVED_NO_AUTOMATIC_REFUND"
        record("BUDGET_RESERVED_BEFORE_PROVIDER_CREATION", reserved_usd="4.00", worker_source_sha=request["worker_source_sha"])
        ledger = old.budget.read_ledger()
        require(digest(encoded(ledger)) == reservation["ledger_sha256"], "RESERVED_LEDGER_SNAPSHOT_CHANGED")
        for name, value in (("reservation_receipt.json", reservation), ("ledger_snapshot.json", ledger),
                            ("launch_request.json", request)):
            with (output / name).open("xb") as stream:
                stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())
    except BaseException as error:
        receipt["status"] = "PREPROVIDER_PREPARATION_OR_RESERVATION_FAILED"
        receipt["provider_resources_created"] = False
        record("PREPROVIDER_FAILURE", error=type(error).__name__, message=str(error))
        return receipt
    iid = None
    launch_attempted = artifact_verified = False
    def role(name, service, statements):
        trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}]}
        created = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Tags=tags)["Role"]
        receipt["resources"][name] = created["Arn"]; save()
        iam.put_role_policy(RoleName=name, PolicyName="job-only", PolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": statements}))
        return created["Arn"]
    try:
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "us-west-2"})
        receipt["resources"]["bucket"] = bucket; save()
        s3.put_bucket_tagging(Bucket=bucket, Tagging={"TagSet": tags})
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={k: True for k in
            ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")})
        s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})
        s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={"Rules": [{"ID": "job-seven-days", "Status": "Enabled", "Filter": {"Prefix": ""}, "Expiration": {"Days": 7}, "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1}}]})
        role(worker_role, "ec2.amazonaws.com", [{"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": [f"arn:aws:s3:::{bucket}/input/{key}" for key in INPUT_KEYS]},
            {"Effect": "Allow", "Action": ["s3:PutObject"], "Resource": [f"arn:aws:s3:::{bucket}/results/{key}" for key in RESULT_KEYS]}])
        iam.create_instance_profile(InstanceProfileName=worker_role, Tags=tags)
        receipt["resources"]["instance_profile"] = worker_role; save()
        iam.add_role_to_instance_profile(InstanceProfileName=worker_role, RoleName=worker_role)
        timer_arn = role(timer_role, "scheduler.amazonaws.com", [{"Effect": "Allow", "Action": "ec2:TerminateInstances", "Resource": f"arn:aws:ec2:us-west-2:807562639912:instance/*", "Condition": {"StringEquals": {"ec2:ResourceTag/cas_meta_job": job}}}])
        sg = ec2.create_security_group(GroupName=job, Description="CAS B/R construction outbound HTTPS only", VpcId=preflight["subnet"]["VpcId"], TagSpecifications=[{"ResourceType": "security-group", "Tags": tags}])["GroupId"]
        receipt["resources"]["security_group"] = sg; save()
        ec2.revoke_security_group_egress(GroupId=sg, IpPermissions=[{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        ec2.authorize_security_group_egress(GroupId=sg, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        s3.put_object(Bucket=bucket, Key="input/source.zip", Body=source_bytes)
        s3.put_object(Bucket=bucket, Key="input/remote.py", Body=script.encode())
        record("REMOTE_AND_BOOTSTRAP_PINNED", remote_sha256=digest(script.encode()), bootstrap_sha256=digest(bootstrap.encode()))
        time.sleep(10)  # IAM propagation only; no job retry.
        launched_at = datetime.now(timezone.utc)
        cloud_deadline = launched_at + timedelta(seconds=plan["cloud_shutdown_seconds"])
        lifetime_deadline = launched_at + timedelta(seconds=3600)
        launch_attempted = True
        record("INSTANCE_LAUNCH_ATTEMPTED", client_token=job, lifetime_deadline=lifetime_deadline.isoformat())
        launched = ec2.run_instances(ImageId=plan["ami_id"], InstanceType="g7.2xlarge", MinCount=1, MaxCount=1,
            ClientToken=job, IamInstanceProfile={"Name": worker_role}, InstanceInitiatedShutdownBehavior="terminate",
            MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"}, NetworkInterfaces=[{"DeviceIndex": 0,
                "SubnetId": request["subnet_id"], "Groups": [sg], "AssociatePublicIpAddress": True, "DeleteOnTermination": True}],
            BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 75, "VolumeType": "gp3", "Iops": 3000,
                "Throughput": 125, "Encrypted": True, "DeleteOnTermination": True}}],
            TagSpecifications=[{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}], UserData=bootstrap)
        require(len(launched["Instances"]) == 1, "ONE_INSTANCE_RESPONSE_REQUIRED")
        iid = launched["Instances"][0]["InstanceId"]
        receipt["resources"]["instance"] = iid
        receipt["provider_launch_time"] = launched["Instances"][0].get("LaunchTime", launched_at).isoformat()
        record("INSTANCE_CREATED", instance_id=iid)
        target = {"Arn": "arn:aws:scheduler:::aws-sdk:ec2:terminateInstances", "RoleArn": timer_arn,
            "Input": json.dumps({"InstanceIds": [iid]}), "RetryPolicy": {"MaximumRetryAttempts": 0, "MaximumEventAgeInSeconds": 60}}
        expression = "at(" + cloud_deadline.strftime("%Y-%m-%dT%H:%M:%S") + ")"
        receipt["resources"]["schedule"] = job; save()
        scheduler.create_schedule(Name=job, ScheduleExpression=expression, ScheduleExpressionTimezone="UTC",
            FlexibleTimeWindow={"Mode": "OFF"}, Target=target, ActionAfterCompletion="DELETE")
        confirmed = scheduler.get_schedule(Name=job)
        old.verify_schedule(confirmed, target, expression)
        require(datetime.now(timezone.utc) < cloud_deadline - timedelta(seconds=840),
                "INSUFFICIENT_INSTANCE_TIME_FOR_UNSHORTENED_WORKER")
        record("CLOUD_DEADLINE_CONFIRMED", schedule=job, provider_response=confirmed)
        permit = worker_permit(request, source, reservation, ledger, iid, cloud_deadline)
        require(len(encoded(permit)) <= 1024**2, "PERMIT_UPLOAD_CEILING")
        with (output / "worker_plan.json").open("xb") as stream:
            stream.write(encoded(permit["worker_plan"])); stream.flush(); os.fsync(stream.fileno())
        s3.put_object(Bucket=bucket, Key="input/permit.json", Body=encoded(permit))
        record("WORKER_PERMIT_PUBLISHED_AFTER_CONFIRMED_SHUTDOWN", worker_plan_sha256=permit["worker_plan_sha256"])
        while datetime.now(timezone.utc) < cloud_deadline - timedelta(seconds=30):
            try:
                response = s3.get_object(Bucket=bucket, Key="results/complete.json")
                try:
                    raw = response["Body"].read(1024**2 + 1)
                finally:
                    response["Body"].close()
                require(len(raw) <= 1024**2, "RESULT_RECEIPT_CEILING")
                result = decoded(raw)
                require(result.get("job") == job and type(result.get("sha256")) is str and HEX64.fullmatch(result["sha256"])
                    and type(result.get("bytes")) is int and 0 < result["bytes"] <= plan["artifact_bytes_max"] - 2 * 1024**2
                    and result.get("experiment") == EXPERIMENT and type(result.get("returncode")) is int,
                    "REMOTE_RESULT_IDENTITY_SIZE_OR_EXPERIMENT")
                head = s3.head_object(Bucket=bucket, Key="results/artifacts.zip")
                require(head["ContentLength"] == result["bytes"], "REMOTE_RESULT_SIZE_MISMATCH")
                artifact = output / "cloud_artifacts.zip"
                plumbing.download_once(s3, bucket, "results/artifacts.zip", artifact, result["bytes"])
                collection = verify_packet(artifact, result, request, permit["worker_plan_sha256"])
                artifact_verified = True
                receipt.update(result=result, artifact_collection=collection,
                    status="AWS_BR_CONSTRUCTION_FINISHED" if result["returncode"] == 0 else "AWS_BR_CONSTRUCTION_FAILED")
                record("ARTIFACT_DOWNLOADED_AND_HASH_VERIFIED", sha256=result["sha256"], bytes=result["bytes"])
                break
            except Exception as error:
                code = getattr(error, "response", {}).get("Error", {}).get("Code")
                if code not in ("NoSuchKey", "404"):
                    raise
            current = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]
            old.check_tag(current.get("Tags", []), job)
            require(current.get("ClientToken") == job, "INSTANCE_CLIENT_TOKEN_MISMATCH")
            require(current["State"]["Name"] not in ("terminated", "shutting-down"), "INSTANCE_ENDED_WITHOUT_COMPLETION_RECEIPT")
            time.sleep(15)
        else:
            raise LaunchRefused("LOCAL_WATCHDOG_DEADLINE")
    except BaseException as error:
        receipt["status"] = "AWS_BR_CONSTRUCTION_BLOCKED_OR_FAILED"
        record("ERROR", error=type(error).__name__, message=str(error))
    finally:
        terminated = not launch_attempted
        if launch_attempted and iid is None:
            try:
                recovered = old.reconcile_instance(ec2, job)
                iid = recovered["InstanceId"]
                receipt["resources"]["instance"] = iid
                record("INSTANCE_IDENTITY_RECOVERED", instance_id=iid)
            except Exception as error:
                receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED:" + str(error))
        if iid:
            try:
                old.terminate_owned_instance(ec2, iid, job, artifact_verified=artifact_verified, record=record)
                terminated = True
                record("INSTANCE_TERMINATION_CONFIRMED", instance_id=iid)
            except Exception as error:
                receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED:" + str(error))
        if terminated:
            if iid:
                try:
                    remaining = old.confirm_deleted_volumes(ec2, job, record)
                    receipt["remaining_job_volumes"] = remaining
                    require(not remaining, "EBS_DELETION_NOT_CONFIRMED")
                except Exception as error:
                    receipt["cleanup_errors"].append("EBS_CHECK_FAILED:" + str(error))
            old.remove_owned_auxiliary_resources(ec2, iam, scheduler, receipt, job, worker_role, timer_role, record)
        if "bucket" in receipt["resources"]:
            try:
                head = s3.head_object(Bucket=bucket, Key="results/bootstrap.log")
                require(head["ContentLength"] <= 1024**2, "BOOTSTRAP_LOG_CEILING")
                path = output / "bootstrap.log"
                plumbing.download_once(s3, bucket, "results/bootstrap.log", path, 1024**2)
                receipt["bootstrap_log_sha256"] = digest(safe_file(path, 1024**2))
            except Exception as error:
                receipt["bootstrap_log_status"] = str(getattr(error, "response", {}).get("Error", {}).get("Code", type(error).__name__))
            try:
                old.check_tag(s3.get_bucket_tagging(Bucket=bucket)["TagSet"], job)
                listed = s3.list_objects_v2(Bucket=bucket, Prefix="results/")
                objects = listed.get("Contents", [])
                require(not listed.get("IsTruncated") and len(objects) <= 3
                    and {x["Key"] for x in objects}.issubset({"results/" + key for key in RESULT_KEYS})
                    and sum(x["Size"] for x in objects) <= plan["artifact_bytes_max"], "RESULT_OBJECT_LIMIT_UNCONFIRMED")
                receipt["stored_result_objects"] = provider_json(objects)
                if terminated and artifact_verified:
                    removed = s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": "input/" + key} for key in INPUT_KEYS]})
                    receipt["input_delete_response"] = provider_json(removed)
                    require(not removed.get("Errors") and {x.get("Key") for x in removed.get("Deleted", [])}
                            == {"input/" + key for key in INPUT_KEYS}, "INPUT_DELETION_NOT_CONFIRMED")
                    record("OWNED_INPUTS_REMOVED_AFTER_VERIFIED_DOWNLOAD", provider_response=removed)
            except Exception as error:
                receipt["cleanup_errors"].append("S3_OWNERSHIP_OR_RETENTION_CHECK:" + str(error))
        receipt["termination_confirmed"] = terminated
        receipt["artifact_verified"] = artifact_verified
        receipt["s3_retention"] = "Dedicated job bucket objects expire after 7 days; local evidence retained."
        receipt["billing_boundary"] = "Reservation and resource/deadline checks, not an AWS invoice or provider-enforced account spending cap."
        if receipt["cleanup_errors"]:
            receipt["status"] = "CLEANUP_REQUIRES_ATTENTION"
        save()
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--plan", action="store_true")
    for name in ("parent-source-sha", "source-archive", "source-archive-sha256",
                 "worker-source-sha", "source-manifest-sha256", "subnet-id",
                 "request", "request-sha256", "authority", "authority-sha256", "receipt-dir"):
        parser.add_argument("--" + name)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    require(not (args.execute and args.plan), "BR_ONE_ACTION_ONLY")
    if args.execute:
        require(all(getattr(args, k) for k in ("request", "request_sha256", "authority",
                "authority_sha256", "receipt_dir")), "BR_EXECUTION_INPUTS_REQUIRED")
        result = execute(args.request, args.request_sha256, args.authority, args.authority_sha256,
                         args.receipt_dir, args.profile)
        print(encoded(result).decode(), end="")
        return 0 if result.get("status") == "AWS_BR_CONSTRUCTION_FINISHED" else 1
    if args.plan:
        require(all(getattr(args, k) for k in ("parent_source_sha", "subnet_id", "source_archive",
                "source_archive_sha256", "worker_source_sha", "source_manifest_sha256")), "BR_PLAN_INPUTS_REQUIRED")
        result = build_request(args.parent_source_sha, args.subnet_id, args.source_archive,
                               args.source_archive_sha256, args.worker_source_sha, args.source_manifest_sha256)
    else:
        result = {"schema": "cas-meta2-br-launch-capability/8", "experiment": EXPERIMENT,
                  "resource_plan": resource_plan(), "construction_scope": construction_scope(),
                  "standing_authority_registration_required": True, "launch_authorized": False,
                  "provider_calls": False, "new_reservation": False}
    print(encoded(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
