"""Dedicated one-child task qualification launch; ordinary planning is pure and unpaid.

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
EXPERIMENT = {"profile": "one_child_full_task_qualification_v8", "entrypoint": "cas_meta2.child_qualification_gpu_v8"}
PARENT_FILES = ("aws/launch_child_qualification_v8.py", "aws/child_qualification_remote_v8.py", "aws/child_qualification_package_v8.py")
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
    "admission.json", "cases/candidates_sealed.json", "cases/qualification_receipt.json",
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
            require(key not in value, "CHQ_DUPLICATE_JSON_KEY")
            value[key] = entry
        return value
    return json.loads(raw, object_pairs_hook=unique,
        parse_constant=lambda _: require(False, "CHQ_NONFINITE_JSON"))


def digest(raw):
    return sha256(raw).hexdigest()


def safe_file(path, maximum=32 * 1024**2):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "CHQ_SOURCE_OR_EVIDENCE_LINK")
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
            and metadata.st_size <= maximum, "CHQ_BOUNDED_REGULAR_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "CHQ_FILE_SIZE_LIMIT")
    return raw


def read_pinned(path, expected, maximum=32 * 1024**2):
    require(type(expected) is str and HEX64.fullmatch(expected), "CHQ_EXACT_HASH_REQUIRED")
    raw = safe_file(path, maximum)
    require(digest(raw) == expected, "CHQ_PINNED_BYTES_CHANGED")
    return raw


def verify_parent_source(parent_sha):
    require(type(parent_sha) is str and SHA1.fullmatch(parent_sha), "CHQ_PARENT_COMMIT_REQUIRED")
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    require(subprocess.check_output(["git", "rev-parse", parent_sha + "^{commit}"], cwd=repo,
                                   text=True).strip() == parent_sha, "CHQ_PARENT_COMMIT_REQUIRED")
    identity = {}
    for relative in (*PARENT_FILES, *FROZEN_PINS):
        path = ROOT / relative
        raw = safe_file(path)
        committed = subprocess.check_output(["git", "cat-file", "blob",
            parent_sha + ":" + path.relative_to(repo).as_posix()], cwd=repo)
        require(raw == committed, "CHQ_PARENT_SOURCE_NOT_COMMITTED:" + relative)
        identity[relative] = digest(raw)
        if relative in FROZEN_PINS:
            require(identity[relative] == FROZEN_PINS[relative], "CHQ_FROZEN_HELPER_CHANGED:" + relative)
    return identity


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    require(spec is not None and spec.loader is not None, "CHQ_HELPER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def helpers(parent_sha):
    identity = verify_parent_source(parent_sha)
    return {
        "identity": identity,
        "package": load_module("child_qualification_parent_package", "aws/child_qualification_package_v8.py"),
        "plumbing": load_module("child_qualification_parent_bounded_plumbing", "aws/launch_prefix_diagnostic_v8.py"),
        "old": load_module("child_qualification_parent_owned_cleanup", "aws/launch_prototype_v7.py"),
        "remote": load_module("child_qualification_parent_remote", "aws/child_qualification_remote_v8.py"),
    }


def resource_plan():
    return {"instance_count": 1, "gpu_count": 1, "instance_type": "g7.2xlarge",
        "account_id": "807562639912", "region": "us-west-2", "ami_id": "ami-0fbbd0facbc9e3cff",
        "runtime_seconds_max": 3600, "worker_seconds_max": 1800,
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


def qualification_scope():
    return {"max_seconds": 1800, "max_cost_usd": "4.00", "seed": 7,
        "task_count": 4, "candidates_per_task": 4, "planned_complete_executions": 20,
        "planned_native_ticks": 110, "binding": 0, "training": False,
        "native_execution": True, "max_output_bytes": 512 * 1024**2,
        "return_child_result": True, "automatic_retries": 0}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == "cas-meta2-child-qualification-launch-request/8",
            "CHQ_DEDICATED_REQUEST_REQUIRED")
    require(type(request.get("job")) is str and JOB.fullmatch(request["job"]), "CHQ_UNIQUE_JOB_REQUIRED")
    require(request.get("experiment") == EXPERIMENT
            and encoded(request.get("resource_plan")) == encoded(resource_plan())
            and encoded(request.get("qualification_scope")) == encoded(qualification_scope()),
            "CHQ_EXACT_SCOPE_REQUIRED")
    for key in ("parent_source_sha", "worker_source_sha"):
        require(type(request.get(key)) is str and SHA1.fullmatch(request[key]), "CHQ_SOURCE_SHA_REQUIRED")
    for key in ("source_archive_sha256", "source_manifest_sha256"):
        require(type(request.get(key)) is str and HEX64.fullmatch(request[key]), "CHQ_SOURCE_HASH_REQUIRED")
    require(type(request.get("source_archive_bytes")) is int and 0 < request["source_archive_bytes"] <= 16 * 1024**2,
            "CHQ_SOURCE_ARCHIVE_BOUND")
    require(type(request.get("subnet_id")) is str and re.fullmatch(r"subnet-[0-9a-f]{8,17}", request["subnet_id"]),
            "CHQ_SUBNET_REQUIRED")
    require(request.get("standing_authority_registration_required") is True
            and request.get("launch_authorized") is False
            and not any("development" in k or "checkpoint" in k for k in request),
            "CHQ_REGISTERED_STANDING_AUTHORITY_REQUIRED")


def source_for(request, package):
    source = package.inspect_archive(request["source_archive"],
        expected_sha256=request["source_archive_sha256"], expected_source_sha=request["worker_source_sha"],
        expected_manifest_sha256=request["source_manifest_sha256"])
    require(len(read_pinned(request["source_archive"], request["source_archive_sha256"])) == request["source_archive_bytes"],
            "CHQ_SOURCE_ARCHIVE_SIZE_CHANGED")
    require(source["files_sha256"]["research/CAS_META_2_COMPOSITION/aws/child_qualification_package_v8.py"]
            == digest(safe_file(ROOT / "aws/child_qualification_package_v8.py")), "CHQ_PACKAGER_SOURCE_DIFFERS_FROM_WORKER")
    return source


def build_request(parent_sha, subnet_id, source_archive, source_archive_sha256, worker_source_sha, source_manifest_sha256):
    h = helpers(parent_sha)
    request = {"schema": "cas-meta2-child-qualification-launch-request/8", "experiment": EXPERIMENT,
        "job": "cas-meta2-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8],
        "parent_source_sha": parent_sha, "parent_file_sha256": h["identity"],
        "worker_source_sha": worker_source_sha, "source_archive_sha256": source_archive_sha256,
        "source_manifest_sha256": source_manifest_sha256, "source_archive": str(Path(source_archive).absolute()),
        "source_archive_bytes": len(read_pinned(source_archive, source_archive_sha256)),
        "subnet_id": subnet_id, "resource_plan": resource_plan(), "qualification_scope": qualification_scope(),
        "standing_authority_registration_required": True, "launch_authorized": False,
        "provider_calls": False, "new_reservation": False}
    validate_request(request)
    source_for(request, h["package"])
    return request


def validate_authority(path, expected, request, request_sha256, ledger):
    record = decoded(read_pinned(path, expected, 1024**2))
    wanted = {"schema": "cas-meta2-child-qualification-standing-authority/8", "standing_campaign_authorization": True,
        "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00", "experiment": EXPERIMENT,
        "training": False, "native_execution": True, "launch_request_sha256": request_sha256,
        **{k: request[k] for k in ("job", "parent_source_sha", "worker_source_sha",
                                  "source_archive_sha256", "source_manifest_sha256")}}
    require(all(type(record.get(k)) is type(v) and record[k] == v for k, v in wanted.items()),
            "CHQ_STANDING_AUTHORITY_SCOPE_OR_JOB_CHANGED")
    campaign = record.get("campaign_approval", {})
    require(campaign == {k: ledger["approval"][k] for k in ("path", "sha256")},
            "CHQ_CANONICAL_CAMPAIGN_AUTHORITY_REQUIRED")
    require(Path(campaign["path"]).is_absolute(), "CHQ_ABSOLUTE_AUTHORITY_PATH_REQUIRED")
    read_pinned(campaign["path"], campaign["sha256"])
    message = record.get("standing_user_message", {})
    require(type(message.get("path")) is str and Path(message["path"]).is_absolute()
            and message.get("sha256") == STANDING_MESSAGE_SHA256, "CHQ_FULL_STANDING_MESSAGE_REQUIRED")
    read_pinned(message["path"], STANDING_MESSAGE_SHA256, 1024**2)
    require(ledger["owner_task_cap_usd"] == "400.00" and ledger["no_automatic_refund"] is True,
            "CHQ_EXISTING_CAMPAIGN_CAP_REQUIRED")
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
    require(type(instance_id) is str and re.fullmatch(r"i-[0-9a-f]{17}", instance_id), "CHQ_REAL_INSTANCE_REQUIRED")
    base = "/opt/cas-meta2-child-qualification/"
    plan = {"schema": "cas-meta2-child-qualification-plan/8", "launch_enabled": True,
        "job": request["job"], "instance_id": instance_id, "source_sha": request["worker_source_sha"],
        **qualification_scope(), "experiment": EXPERIMENT, "resource_plan": request["resource_plan"],
        "source_manifest": {"path": base + "package/child_qualification_source_manifest.json", "sha256": request["source_manifest_sha256"]},
        "source_archive": {"path": base + "source.zip", "sha256": request["source_archive_sha256"]},
        "reservation_receipt": {"path": base + "launch/reservation_receipt.json", "sha256": digest(encoded(reservation))},
        "ledger_snapshot": {"path": base + "launch/ledger_snapshot.json", "sha256": digest(encoded(ledger))}}
    return {"job": request["job"], "archive_sha256": request["source_archive_sha256"],
        "cloud_deadline_confirmed": True, "instance_id": instance_id, "deadline": deadline.isoformat(),
        "worker_plan": plan, "worker_plan_sha256": digest(encoded(plan)),
        "reservation_receipt": reservation, "ledger_snapshot": ledger}


def remote_config(request, source):
    return {"schema": "cas-meta2-child-qualification-remote-config/8", "job": request["job"],
        "bucket": request["job"] + "-807562639912", "region": "us-west-2", "account_id": "807562639912",
        **{k: request[k] for k in ("parent_source_sha", "worker_source_sha", "source_archive_sha256",
                                  "source_archive_bytes", "source_manifest_sha256")},
        "source_manifest": source, "package_layout": source["base"]["package_layout"],
        "resource_plan": request["resource_plan"], "max_worker_seconds": 1800,
        "artifact_bytes_max": 256 * 1024**2, "evidence_expanded_bytes_max": 512 * 1024**2,
        "experiment": EXPERIMENT}


def safe_member(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name
            and not any(ord(c) < 32 for c in name)
            and all(p not in ("", ".", "..") for p in name.split("/")), "CHQ_UNSAFE_RESULT_PATH")
    return name


def verify_qualification_receipt(qualified, value, present):
    """Replay the saved panel decisions without running a model or database."""
    require(qualified.get("schema") == "cas-meta2-one-child-qualification/8"
            and qualified.get("status") == "QUALIFIED" and qualified.get("qualified") is True
            and qualified.get("training") is False and "failure" not in qualified
            and qualified.get("attempted_execution_count") == 20
            and qualified.get("reported_executed_count") == 20
            and qualified.get("completed_execution_count") == 20
            and qualified.get("audited_native_ticks") == 110
            and qualified.get("completed_native_ticks") == 110
            and qualified.get("all_scheduled_executions_completed") is True
            and qualified.get("unattempted_execution_count") == 0
            and qualified.get("failed_or_unaudited_attempts") == 0,
            "CHQ_INCOMPLETE_QUALIFICATION_COUNTS")
    cases = qualified.get("cases")
    require(type(cases) is list and len(cases) == 4
            and [c.get("index") for c in cases] == list(range(4))
            and {c.get("target_combination") for c in cases} == {"B_C", "B_CR", "R_C", "R_CR"},
            "CHQ_QUALIFICATION_CASE_COVERAGE")
    total_executions = total_ticks = 0
    for case in cases:
        folder = "qualification/cases/case_%02d/" % case["index"]
        require(case.get("status") == "QUALIFIED" and value(folder + "panel_qualification.json") == case,
                "CHQ_PANEL_RECEIPT_MISMATCH")
        rows = case.get("comparisons")
        require(type(rows) is list and len(rows) == 4
                and {r.get("combination") for r in rows} == {"B_C", "B_CR", "R_C", "R_CR"}
                and sum(r.get("correct_target") is True for r in rows) == 1, "CHQ_PANEL_CHOICES_MISSING")
        for row in rows:
            target = row["combination"] == case["target_combination"]
            require(row.get("correct_target") is target and row.get("task_correct") is target
                    and row.get("final_output_differs_from_reference") is (not target)
                    and type(row.get("final_output_sha256")) is str
                    and HEX64.fullmatch(row["final_output_sha256"])
                    and type(row.get("reference_final_output_sha256")) is str
                    and HEX64.fullmatch(row["reference_final_output_sha256"])
                    and (row["final_output_sha256"] == row["reference_final_output_sha256"]) is target,
                    "CHQ_TASK_OUTPUT_DISCRIMINATION_NOT_RECORDED")
        executions = case.get("executions")
        require(type(executions) is list and len(executions) == 5
                and [r.get("slot") for r in executions] == ["reference", *["candidate_%02d" % n for n in range(4)]],
                "CHQ_FULL_EXECUTIONS_MISSING")
        audited = {}
        for execution in executions:
            slot = execution["slot"]
            require(execution.get("status") == "EXECUTED_AND_STORED_AUDITED"
                    and value(folder + slot + "_qualification.json") == execution,
                    "CHQ_EXECUTION_AUDIT_COPY_MISMATCH")
            require({folder + slot + "/" + name for name in
                    ("native.db", "native_traces.json", "composition_events.json",
                     "native_kernel_events.json", "result.json")} <= present,
                    "CHQ_NATIVE_EXECUTION_FILES_MISSING")
            actual = execution["execution_result"]
            require(value(folder + slot + "/result.json") == actual
                    and actual.get("status") == "EXECUTED"
                    and actual.get("reference") is (slot == "reference")
                    and actual.get("fixed_weights") is True and actual.get("integrity") is True,
                    "CHQ_NATIVE_EXECUTION_IDENTITY")
            combination = (case["target_combination"] if slot == "reference" else
                           ("B_C", "B_CR", "R_C", "R_CR")[int(slot[-2:])])
            expected_ticks = 6 if combination.endswith("CR") else 5
            stored, verdict = execution.get("stored_audit", {}), execution.get("verification", {})
            require(type(actual.get("native_trace_count")) is int
                    and type(stored.get("trace_count")) is int
                    and type(verdict.get("native_runs")) is int
                    and actual["native_trace_count"] == stored["trace_count"] == verdict["native_runs"] == expected_ticks
                    and type(actual.get("reserved_policy_units")) is int and actual["reserved_policy_units"] > 0
                    and actual["reserved_policy_units"] == stored.get("reserved_policy_units") == verdict.get("reserved_policy_units")
                    and stored.get("audit_method") == "read-only-sqlite-source-replay/0.1"
                    and stored.get("expected_action_checked") is True
                    and stored.get("stored_call_tree_verified") is (slot != "reference")
                    and type(stored.get("final_output_sha256")) is str
                    and HEX64.fullmatch(stored["final_output_sha256"]), "CHQ_STORED_EXECUTION_COUNTS_OR_AUDIT")
            target = slot == "reference" or combination == case["target_combination"]
            require(all(verdict.get(k) is target for k in
                    ("task_correct", "procedure_correct", "dependency_correct", "actual_output_correct"))
                    and verdict.get("binding_correct") is True and verdict.get("trace_valid") is True
                    and verdict.get("stored_call_tree_verified") is (slot != "reference"),
                    "CHQ_SAVED_VERIFIER_VERDICT_CONTRADICTS_PANEL")
            if slot == "reference":
                require(verdict.get("candidate_task_evaluation") is False
                        and verdict.get("verdict_kind") == "PRIVATE_NATIVE_REFERENCE_CHECK",
                        "CHQ_PRIVATE_REFERENCE_VERDICT_REQUIRED")
            audited[slot] = stored["final_output_sha256"]
            total_executions += 1
            total_ticks += stored["trace_count"]
        for number, combination in enumerate(("B_C", "B_CR", "R_C", "R_CR")):
            row = next(r for r in rows if r["combination"] == combination)
            require(row["final_output_sha256"] == audited["candidate_%02d" % number]
                    and row["reference_final_output_sha256"] == audited["reference"],
                    "CHQ_COMPARISON_HASH_NOT_BOUND_TO_STORED_AUDIT")
    require(total_executions == 20 and total_ticks == 110, "CHQ_EXECUTION_TOTALS_DISAGREE")
    return True


def verify_packet(artifact, result, request, worker_plan_sha256):
    """Verify full bytes and explicit one-child qualification outputs without native or model imports."""
    plan = request["resource_plan"]
    require(type(result.get("returncode")) is int and result["returncode"] in (0, 1)
            and result.get("source_sha") == request["worker_source_sha"]
            and result.get("parent_source_sha") == request["parent_source_sha"]
            and result.get("job") == request["job"] and result.get("experiment") == EXPERIMENT,
            "CHQ_RESULT_IDENTITY")
    raw = read_pinned(artifact, result["sha256"], plan["artifact_bytes_max"])
    require(len(raw) == result["bytes"], "CHQ_RESULT_BYTES")
    # Parse the same pinned bytes; do not reopen a pathname after hashing it.
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [safe_member(i.orig_filename) for i in infos]
        require(len(names) == len(set(names)) == len({n.casefold() for n in names})
                and all(i.orig_filename == i.filename and not i.is_dir()
                    and stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG)
                    and not i.flag_bits & 1 for i in infos), "CHQ_UNSAFE_RESULT_ARCHIVE")
        require(sum(i.file_size for i in infos) <= plan["evidence_expanded_bytes_max"], "CHQ_RESULT_EXPANDED_LIMIT")
        archive_hashes = {}
        for name in names:
            with archive.open(name) as stream:
                archive_hashes[name] = file_digest(stream, "sha256").hexdigest()
        def value(name):
            require(archive.getinfo(name).file_size <= 32 * 1024**2, "CHQ_JSON_RECEIPT_SIZE_LIMIT")
            return decoded(archive.read(name))
        collection = value("artifact_collection_receipt.json")
        require(collection.get("job") == request["job"] and collection.get("source_sha") == request["worker_source_sha"]
                and collection.get("parent_source_sha") == request["parent_source_sha"]
                and collection.get("experiment") == EXPERIMENT and collection.get("returncode") == result["returncode"],
                "CHQ_COLLECTION_IDENTITY")
        if collection.get("full_file_counts_known") is False:
            require(result["returncode"] == 1 and collection.get("partial_evidence") is True
                    and collection.get("original_file_count") is None
                    and collection.get("included_full_file_count") == 0
                    and collection.get("omitted_full_file_count") is None
                    and type(collection.get("collection_failure")) is dict
                    and set(names) == {"artifact_collection_receipt.json"}, "CHQ_INVALID_EMERGENCY_PACKET")
            return {**collection, "parent_member_hashes_verified": 0, "archive_files_sha256": archive_hashes,
                    "original_member_coverage_verified": False,
                    "qualification_status": None, "native_component_success": False,
                    "not_learning_or_generalization": True}
        require(type(collection.get("partial_evidence")) is bool
                and collection["partial_evidence"] == result.get("partial_evidence")
                and collection.get("omitted_full_file_count") == result.get("omitted_full_file_count"),
                "CHQ_RESULT_COLLECTION_DISAGREEMENT")
        index = collection.get("files", {})
        require(type(index) is dict, "CHQ_COLLECTION_INDEX_REQUIRED")
        for name, item in index.items():
            safe_member(name)
            require(type(item) is dict and type(item.get("bytes")) is int and item["bytes"] >= 0
                    and type(item.get("sha256")) is str and HEX64.fullmatch(item["sha256"]), "CHQ_COLLECTION_INDEX_INVALID")
            if name in names:
                require(archive_hashes[name] == item["sha256"] and archive.getinfo(name).file_size == item["bytes"],
                        "CHQ_COLLECTED_MEMBER_HASH_CHANGED:" + name)
        present = set(names) - {"artifact_collection_receipt.json"}
        extras = present - set(index)
        require(all(n.startswith("failure_tails/") and archive.getinfo(n).file_size <= 16384 for n in extras),
                "CHQ_UNINDEXED_ARCHIVE_MEMBER")
        if collection.get("partial_evidence") is False:
            require(present == set(index) and collection.get("omitted_full_file_count") == 0,
                    "CHQ_FULL_COLLECTION_COVERAGE")
        require(collection.get("original_file_count") == len(index)
                and collection.get("included_full_file_count") == len(present - extras)
                and collection.get("omitted_full_file_count") == len(set(index) - present),
                "CHQ_COLLECTION_COUNT_MISMATCH")
        worker_name = "qualification/worker_receipt.json"
        worker = value(worker_name) if worker_name in names else None
        if worker is not None:
            require(worker.get("schema") == "cas-meta2-child-qualification-gpu/8"
                    and worker.get("job") == request["job"] and worker.get("source_sha") == request["worker_source_sha"]
                    and worker.get("source_archive_sha256") == request["source_archive_sha256"]
                    and worker.get("source_manifest_sha256") == request["source_manifest_sha256"]
                    and worker.get("plan_sha256") == worker_plan_sha256 and worker.get("training") is False,
                    "CHQ_WORKER_RECEIPT_IDENTITY")
            mapping = worker.get("files_sha256", {})
            require(type(mapping) is dict, "CHQ_WORKER_FILE_MAP_REQUIRED")
            for relative, pin in mapping.items():
                safe_member(relative)
                name = "qualification/" + relative
                require(type(pin) is str and HEX64.fullmatch(pin), "CHQ_WORKER_FILE_PIN_INVALID")
                if name in present:
                    require(name in index and index[name]["sha256"] == pin, "CHQ_WORKER_MEMBER_HASH_CHANGED")
            if collection.get("partial_evidence") is False:
                require({"qualification/" + n for n in mapping} | {worker_name}
                        == {n for n in present if n.startswith("qualification/")}, "CHQ_WORKER_FILE_COVERAGE")
        if result["returncode"] == 0:
            require(collection.get("partial_evidence") is False and worker is not None
                    and worker.get("status") == "CHILD_CURRICULUM_NATIVE_QUALIFIED"
                    and worker.get("native_execution") is True and worker.get("experiment") == EXPERIMENT
                    and worker.get("cleanup_errors") == [] and "failure" not in worker
                    and worker.get("postchecks", {}).get("source", {}).get("ok") is True
                    and worker.get("postchecks", {}).get("reservation", {}).get("ok") is True,
                    "CHQ_SUCCESS_WITHOUT_COMPLETE_NATIVE_RECEIPT")
            require({"qualification/" + n for n in WORKER_SUCCESS_FILES} <= present,
                    "CHQ_MANDATORY_NATIVE_OUTPUT_MISSING")
            qualified = value("qualification/cases/qualification_receipt.json")
            require(qualified == worker.get("qualification"), "CHQ_CORE_RECEIPT_COPY_MISMATCH")
            verify_qualification_receipt(qualified, value, present)
            for name in ("lifecycle/worker/receipt.json", "lifecycle/remote_receipt.json"):
                require(name in present, "CHQ_MANDATORY_LIFECYCLE_RECEIPT_MISSING")
            process = value("lifecycle/worker/receipt.json")
            remote = value("lifecycle/remote_receipt.json")
            require(process.get("exit_code") == 0 and process.get("failure") is None
                    and process.get("maximum_seconds") == 1800
                    and remote.get("returncode") == 0 and remote.get("worker_process_started") is True
                    and remote.get("worker_qualification_completed") is True
                    and remote.get("neural_training") is False
                    and remote.get("source_sha") == request["worker_source_sha"]
                    and remote.get("parent_source_sha") == request["parent_source_sha"]
                    and remote.get("archive_sha256") == request["source_archive_sha256"]
                    and remote.get("source_manifest_sha256") == request["source_manifest_sha256"],
                    "CHQ_LIFECYCLE_EXIT_OR_IDENTITY_MISMATCH")
            for log in ("stdout.txt", "stderr.txt"):
                require(process.get("outputs", {}).get(log) == index.get("lifecycle/worker/" + log)
                        and "lifecycle/worker/" + log in present, "CHQ_PROCESS_RAW_OUTPUT_MISMATCH")
        return {**collection, "parent_member_hashes_verified": len(present - extras),
                "archive_files_sha256": archive_hashes, "original_member_coverage_verified": not collection["partial_evidence"],
                "qualification_status": worker.get("status") if worker else None,
                "native_component_success": result["returncode"] == 0,
                "not_learning_or_generalization": True}


def execute(request_path, request_sha256, authority_path, authority_sha256, receipt_dir, profile="default"):
    request = decoded(read_pinned(request_path, request_sha256, 2 * 1024**2))
    validate_request(request)
    h = helpers(request["parent_source_sha"])
    require(h["identity"] == request["parent_file_sha256"], "CHQ_PARENT_REQUEST_IDENTITY_CHANGED")
    source = source_for(request, h["package"])
    output = Path(receipt_dir).absolute()
    require(not output.exists() and output.is_relative_to(ROOT / "records")
            and ".." not in output.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (output, *output.parents)), "CHQ_NEW_RECEIPT_DIRECTORY_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    preflight_receipt = {"schema": "cas-meta2-child-qualification-provider-preflight/8", "job": request["job"],
        "request_sha256": request_sha256, "status": "PREFLIGHT_ATTEMPT_STARTED",
        "new_reservation": False, "provider_resources_created": False}
    def save_preflight():
        (output / "preflight_receipt.json").write_bytes(encoded(preflight_receipt))
    save_preflight()
    try:
        lock = h["old"].campaign_execution_lock()
        lock.__enter__()
    except BaseException as error:
        preflight_receipt.update(status="CHQ_LAUNCH_PREFLIGHT_REFUSED", error=type(error).__name__, reason=str(error))
        save_preflight()
        (output / "launch_receipt.json").write_bytes(encoded(preflight_receipt))
        return preflight_receipt
    try:
        try:
            ledger = h["old"].budget.read_ledger()
            authority = validate_authority(authority_path, authority_sha256, request, request_sha256, ledger)
            require(Decimal(ledger["remaining_unreserved_usd"]) >= Decimal("4.00"), "CHQ_CAMPAIGN_BUDGET_EXHAUSTED")
            clients = h["plumbing"].client_factory(profile, "us-west-2")
            preflight = h["plumbing"].provider_preflight(clients, request)
            preflight_receipt.update(status="PREFLIGHT_READS_PASSED", result=provider_json(preflight))
        except BaseException as error:
            preflight_receipt.update(status="CHQ_LAUNCH_PREFLIGHT_REFUSED", error=type(error).__name__, reason=str(error))
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
    receipt = {"schema": "cas-meta2-child-qualification-launch-receipt/8", "status": "STARTING",
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
        sg = ec2.create_security_group(GroupName=job, Description="CAS one-child task qualification outbound HTTPS only", VpcId=preflight["subnet"]["VpcId"], TagSpecifications=[{"ResourceType": "security-group", "Tags": tags}])["GroupId"]
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
        require(datetime.now(timezone.utc) < cloud_deadline - timedelta(seconds=2040),
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
                    status="AWS_CHILD_QUALIFICATION_FINISHED" if result["returncode"] == 0 else "AWS_CHQ_CONSTRUCTION_FAILED")
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
        receipt["status"] = "AWS_CHILD_QUALIFICATION_BLOCKED_OR_FAILED"
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
    require(not (args.execute and args.plan), "CHQ_ONE_ACTION_ONLY")
    if args.execute:
        require(all(getattr(args, k) for k in ("request", "request_sha256", "authority",
                "authority_sha256", "receipt_dir")), "CHQ_EXECUTION_INPUTS_REQUIRED")
        result = execute(args.request, args.request_sha256, args.authority, args.authority_sha256,
                         args.receipt_dir, args.profile)
        print(encoded(result).decode(), end="")
        return 0 if result.get("status") == "AWS_CHILD_QUALIFICATION_FINISHED" else 1
    if args.plan:
        require(all(getattr(args, k) for k in ("parent_source_sha", "subnet_id", "source_archive",
                "source_archive_sha256", "worker_source_sha", "source_manifest_sha256")), "CHQ_PLAN_INPUTS_REQUIRED")
        result = build_request(args.parent_source_sha, args.subnet_id, args.source_archive,
                               args.source_archive_sha256, args.worker_source_sha, args.source_manifest_sha256)
    else:
        result = {"schema": "cas-meta2-child-qualification-launch-capability/8", "experiment": EXPERIMENT,
                  "resource_plan": resource_plan(), "qualification_scope": qualification_scope(),
                  "standing_authority_registration_required": True, "launch_authorized": False,
                  "provider_calls": False, "new_reservation": False}
    print(encoded(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
