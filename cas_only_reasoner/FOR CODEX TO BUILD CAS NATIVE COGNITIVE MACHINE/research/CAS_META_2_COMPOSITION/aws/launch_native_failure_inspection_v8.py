"""One new AWS read-only SQLite inspection; default CLI use never launches.

The pinned CHQ lifecycle is used only as transport through a private module with
explicit inspection callbacks. Its old execute(), source_for(), native worker
and paid capture are never called. No SQLite/model work runs on this parent.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import uuid
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = {"profile": "native_failure_sqlite_inspection_v8", "entrypoint": "read_only_sqlite_export"}
ORIGINAL_JOB = "cas-meta2-20260906155525-195f5ad8"
EVIDENCE_SHA256 = "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"
EVIDENCE_BYTES = 893323
PARENT_FILES = ("aws/launch_native_failure_inspection_v8.py", "aws/native_failure_inspection_v8.py")
FROZEN_PINS = {
    "aws/launch_child_qualification_v8.py": "05739bcc5514f1f0dcde736d972c44984610e4441d8fd69f8c31c61a4e87bedf",
    "aws/launch_prefix_diagnostic_v8.py": "d9853e6cbb41fd5efdd927e217bde35fc98a05bf9d784c500cc82b04ba219e48",
    "aws/prefix_remote_v8.py": "e72f5937895d856797e9dae200100b279a39bdbe4850f67b5405a70cb9719f8b",
    "aws/launch_prototype_v7.py": "90f7a8086416ac39c49d9d344d33b128ae19106638f335ceb14cdd26f038577a",
    "aws/budget.py": "77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0",
    "tools/experiment_profiles_prototype_v7.py": "3331ce53d6f3f57b94cb7603f2b53f3c309a899ab2596b4b040fa1b01ccf6ee0",
}
STANDING_MESSAGE_SHA256 = "d0b640ec3059ea73d677b632a4bc2f3188bbcd87b231e4362914e219459fc5bb"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
JOB = re.compile(r"cas-meta2-[0-9]{14}-[0-9a-f]{8}\Z")
DB_MEMBER = "qualification/cases/case_00/candidate_03/native.db"
TABLES = frozenset(("store_metadata", "artifacts", "state_versions", "model_versions", "trace_events",
    "commit_receipts", "published_effects", "memory_records", "repair_frames", "repair_outcomes",
    "transition_batches", "causes", "candidate_effects", "verifier_receipts", "qualification_receipts",
    "state_intents", "model_intents", "memory_intents", "rejection_audits", "active_head"))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decoded(raw):
    def unique(items):
        value = {}
        for key, item in items:
            require(key not in value, "INSPECTION_DUPLICATE_JSON_KEY")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False, "INSPECTION_NONFINITE_JSON"))


def digest(raw):
    return sha256(raw).hexdigest()


def safe_file(path, maximum=32 * 1024**2):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "INSPECTION_LINK_OR_PATH_ESCAPE")
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum,
            "INSPECTION_BOUNDED_REGULAR_FILE_REQUIRED")
    raw = path.read_bytes()
    require(len(raw) <= maximum, "INSPECTION_SIZE_BOUND")
    return raw


def read_pinned(path, expected, maximum=32 * 1024**2):
    require(type(expected) is str and HEX64.fullmatch(expected), "INSPECTION_EXACT_HASH_REQUIRED")
    raw = safe_file(path, maximum)
    require(digest(raw) == expected, "INSPECTION_PINNED_BYTES_CHANGED")
    return raw


def verify_parent_source(source_sha):
    require(type(source_sha) is str and SHA1.fullmatch(source_sha), "INSPECTION_SOURCE_COMMIT_REQUIRED")
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    require(subprocess.check_output(["git", "rev-parse", source_sha + "^{commit}"], cwd=repo,
            text=True).strip() == source_sha, "INSPECTION_EXACT_COMMIT_REQUIRED")
    identity = {}
    for relative in (*PARENT_FILES, *FROZEN_PINS):
        path = ROOT / relative
        raw = safe_file(path)
        committed = subprocess.check_output(["git", "cat-file", "blob",
            source_sha + ":" + path.relative_to(repo).as_posix()], cwd=repo)
        require(raw == committed, "INSPECTION_SOURCE_NOT_COMMITTED:" + relative)
        identity[relative] = digest(raw)
        if relative in FROZEN_PINS:
            require(identity[relative] == FROZEN_PINS[relative], "INSPECTION_FROZEN_HELPER_CHANGED:" + relative)
    return identity


def load_module(label, relative):
    if relative in FROZEN_PINS:
        read_pinned(ROOT / relative, FROZEN_PINS[relative])
    spec = importlib.util.spec_from_file_location(label, ROOT / relative)
    require(spec is not None and spec.loader is not None, "INSPECTION_HELPER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resource_plan():
    # Same already-reviewed resource/price/deadline envelope, shorter read-only worker.
    base = load_module("inspection_resource_template", "aws/launch_child_qualification_v8.py").resource_plan()
    return {**base, "worker_seconds_max": 180, "native_execution": False, "sqlite_read_only": True}


def helpers(source_sha):
    identity = verify_parent_source(source_sha)
    return {"identity": identity,
        "transport": load_module("inspection_private_chq_lifecycle", "aws/launch_child_qualification_v8.py"),
        "plumbing": load_module("inspection_pinned_plumbing", "aws/launch_prefix_diagnostic_v8.py"),
        "old": load_module("inspection_pinned_owned_cleanup", "aws/launch_prototype_v7.py"),
        "remote": load_module("inspection_new_remote", "aws/native_failure_inspection_v8.py")}


def input_manifest(source_sha, identities):
    return {"schema": "cas-meta2-native-failure-inspection-input/8", "original_job": ORIGINAL_JOB,
        "source_archive_sha256": EVIDENCE_SHA256, "source_archive_bytes": EVIDENCE_BYTES,
        "worker_source_sha": source_sha, "parent_source_sha": source_sha,
        "exporter_source_sha256": identities["aws/native_failure_inspection_v8.py"]}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == "cas-meta2-native-failure-inspection-request/8",
            "INSPECTION_DEDICATED_REQUEST_REQUIRED")
    require(type(request.get("job")) is str and JOB.fullmatch(request["job"]) and request["job"] != ORIGINAL_JOB,
            "INSPECTION_NEW_JOB_REQUIRED")
    require(type(request.get("parent_source_sha")) is str and SHA1.fullmatch(request["parent_source_sha"])
            and request.get("worker_source_sha") == request["parent_source_sha"], "INSPECTION_SOURCE_IDENTITY")
    require(request.get("experiment") == EXPERIMENT and request.get("original_job") == ORIGINAL_JOB
            and request.get("source_archive_sha256") == EVIDENCE_SHA256
            and type(request.get("source_archive_bytes")) is int and request["source_archive_bytes"] == EVIDENCE_BYTES
            and encoded(request.get("resource_plan")) == encoded(resource_plan()),
            "INSPECTION_SCOPE_CHANGED")
    expected = input_manifest(request["parent_source_sha"], request["parent_file_sha256"])
    require(request.get("inspection_input_manifest") == expected
            and request.get("source_manifest_sha256") == digest(encoded(expected)), "INSPECTION_INPUT_MANIFEST_CHANGED")
    require(type(request.get("subnet_id")) is str and re.fullmatch(r"subnet-[0-9a-f]{8,17}", request["subnet_id"]),
            "INSPECTION_SUBNET_REQUIRED")
    require(request.get("standing_authority_registration_required") is True and request.get("launch_authorized") is False
            and request.get("provider_calls") is False and request.get("new_reservation") is False,
            "INSPECTION_REGISTERED_AUTHORITY_REQUIRED")
    return request


def source_for(request):
    raw = read_pinned(request["source_archive"], EVIDENCE_SHA256)
    require(len(raw) == EVIDENCE_BYTES, "INSPECTION_EVIDENCE_LENGTH_CHANGED")
    return request["inspection_input_manifest"]


def build_request(source_sha, subnet_id, source_archive):
    h = helpers(source_sha)
    manifest = input_manifest(source_sha, h["identity"])
    request = {"schema": "cas-meta2-native-failure-inspection-request/8", "experiment": EXPERIMENT,
        "job": "cas-meta2-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8],
        "parent_source_sha": source_sha, "worker_source_sha": source_sha, "parent_file_sha256": h["identity"],
        "source_archive": str(Path(source_archive).absolute()), "source_archive_sha256": EVIDENCE_SHA256,
        "source_archive_bytes": EVIDENCE_BYTES, "original_job": ORIGINAL_JOB,
        "inspection_input_manifest": manifest, "source_manifest_sha256": digest(encoded(manifest)),
        "subnet_id": subnet_id, "resource_plan": resource_plan(), "standing_authority_registration_required": True,
        "launch_authorized": False, "provider_calls": False, "new_reservation": False}
    validate_request(request)
    source_for(request)
    return request


def validate_authority(path, expected, request, request_sha256, ledger):
    record = decoded(read_pinned(path, expected, 1024**2))
    wanted = {"schema": "cas-meta2-native-failure-inspection-standing-authority/8",
        "standing_campaign_authorization": True, "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00",
        "experiment": EXPERIMENT, "training": False, "native_execution": False, "sqlite_read_only": True,
        "launch_request_sha256": request_sha256, **{key: request[key] for key in ("job", "parent_source_sha",
            "worker_source_sha", "source_archive_sha256", "source_manifest_sha256", "original_job")}}
    require(all(type(record.get(key)) is type(value) and record[key] == value for key, value in wanted.items()),
            "INSPECTION_STANDING_AUTHORITY_SCOPE_CHANGED")
    campaign = record.get("campaign_approval", {})
    require(campaign == {key: ledger["approval"][key] for key in ("path", "sha256")}
            and Path(campaign["path"]).is_absolute(), "INSPECTION_CANONICAL_AUTHORITY_REQUIRED")
    read_pinned(campaign["path"], campaign["sha256"])
    message = record.get("standing_user_message", {})
    require(type(message.get("path")) is str and Path(message["path"]).is_absolute()
            and message.get("sha256") == STANDING_MESSAGE_SHA256, "INSPECTION_STANDING_MESSAGE_REQUIRED")
    read_pinned(message["path"], STANDING_MESSAGE_SHA256, 1024**2)
    require(ledger.get("owner_task_cap_usd") == "400.00" and ledger.get("no_automatic_refund") is True,
            "INSPECTION_EXISTING_CAMPAIGN_REQUIRED")
    return {**record, "authority_artifact_sha256": expected}


def remote_config(request, source):
    return {"schema": "cas-meta2-native-failure-inspection-remote/8", "job": request["job"],
        "bucket": request["job"] + "-807562639912", "region": "us-west-2", "account_id": "807562639912",
        **{key: request[key] for key in ("parent_source_sha", "worker_source_sha", "source_archive_sha256",
            "source_archive_bytes", "source_manifest_sha256", "original_job", "resource_plan")},
        "inspection_input_manifest": source, "experiment": EXPERIMENT, "max_worker_seconds": 180}


def worker_permit(request, source, reservation, ledger, instance_id, deadline):
    require(type(instance_id) is str and re.fullmatch(r"i-[0-9a-f]{17}", instance_id),
            "INSPECTION_REAL_INSTANCE_REQUIRED")
    plan = {"schema": "cas-meta2-native-failure-inspection-plan/8", "launch_enabled": True,
        "job": request["job"], "instance_id": instance_id, "source_sha": request["worker_source_sha"],
        **{key: request[key] for key in ("parent_source_sha", "source_archive_sha256", "source_manifest_sha256",
            "original_job", "resource_plan")}, "experiment": EXPERIMENT, "training": False,
        "native_execution": False, "sqlite_read_only": True, "max_seconds": 180, "max_cost_usd": "4.00"}
    return {"job": request["job"], "archive_sha256": request["source_archive_sha256"], "instance_id": instance_id,
        "deadline": deadline.isoformat(), "cloud_deadline_confirmed": True, "worker_plan": plan,
        "worker_plan_sha256": digest(encoded(plan)), "reservation_receipt": reservation, "ledger_snapshot": ledger}


def safe_member(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name
            and not any(ord(c) < 32 for c in name) and all(p not in ("", ".", "..") for p in name.split("/")),
            "INSPECTION_UNSAFE_MEMBER")
    return name


def verify_packet(artifact, result, request, worker_plan_sha256):
    raw = read_pinned(artifact, result["sha256"], request["resource_plan"]["artifact_bytes_max"])
    require(len(raw) == result["bytes"], "INSPECTION_RESULT_LENGTH_CHANGED")
    expected = {"job": request["job"], "source_sha": request["worker_source_sha"],
                "parent_source_sha": request["parent_source_sha"], "experiment": EXPERIMENT}
    require(all(result.get(key) == value for key, value in expected.items())
            and type(result.get("returncode")) is int, "INSPECTION_RESULT_IDENTITY_CHANGED")
    with ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        names = [safe_member(entry.filename) for entry in entries]
        require(len(names) == len(set(names)) and len(names) <= 2048
                and len({n.casefold() for n in names}) == len(names)
                and all(not entry.is_dir() and not entry.flag_bits & 1
                        and stat.S_IFMT(entry.external_attr >> 16) in (0, stat.S_IFREG) for entry in entries)
                and sum(entry.file_size for entry in entries) <= request["resource_plan"]["evidence_expanded_bytes_max"],
                "INSPECTION_RESULT_ARCHIVE_BOUND_OR_DUPLICATE")
        require("artifact_collection_receipt.json" in names, "INSPECTION_COLLECTION_RECEIPT_REQUIRED")
        members = {name: archive.read(name) for name in names}
    collection = decoded(members.pop("artifact_collection_receipt.json"))
    require(all(collection.get(key) == value for key, value in expected.items())
            and type(collection.get("returncode")) is int and collection["returncode"] == result["returncode"],
            "INSPECTION_COLLECTION_IDENTITY")
    files = collection.get("files", {})
    require(type(files) is dict and set(members).issubset(files), "INSPECTION_COLLECTION_INDEX_REQUIRED")
    for name, raw_member in members.items():
        require(files[name] == {"bytes": len(raw_member), "sha256": digest(raw_member)},
                "INSPECTION_RESULT_MEMBER_CHANGED:" + name)
    success = result["returncode"] == 0
    receipt = decoded(members["inspection/receipt.json"]) if "inspection/receipt.json" in members else None
    if receipt is not None:
        require(type(receipt) is dict and receipt.get("schema") == "cas-meta2-native-failure-inspection/8"
                and all(receipt.get(key) == value for key, value in expected.items())
                and receipt.get("source_archive_sha256") == request["source_archive_sha256"]
                and receipt.get("training") is False and receipt.get("native_execution") is False
                and receipt.get("sqlite_read_only") is True
                and receipt.get("plan_sha256") in (None, worker_plan_sha256), "INSPECTION_WORKER_RECEIPT_CHANGED")
    if success:
        require(collection.get("returncode") == 0 and collection.get("partial_evidence") is False
                and collection.get("omitted_full_file_count") == 0 and set(members) == set(files),
                "INSPECTION_COMPLETE_OUTPUT_REQUIRED")
        require(receipt is not None and receipt.get("status") == "NATIVE_FAILURE_DATABASE_EXPORTED"
                and receipt.get("training") is False and receipt.get("native_execution") is False
                and receipt.get("sqlite_read_only") is True and receipt.get("input_unchanged") is True
                and receipt.get("job") == request["job"] and receipt.get("source_sha") == request["worker_source_sha"]
                and receipt.get("source_archive_sha256") == request["source_archive_sha256"]
                and receipt.get("plan_sha256") == worker_plan_sha256
                and receipt.get("failure") is None, "INSPECTION_WORKER_RECEIPT_CHANGED")
        exported = decoded(members["inspection/export.json"])
        require(type(exported) is dict and all(exported.get(key) == value for key, value in expected.items()
                if key != "experiment") and exported.get("plan_sha256") == worker_plan_sha256
                and exported.get("database") == receipt.get("database")
                and exported.get("quick_check") == "ok" and exported.get("read_only_uri") is True
                and exported.get("query_only") is True and exported.get("trusted_schema") is False
                and exported.get("authorizer_select_only") is True, "INSPECTION_EXPORT_REQUIRED")
        binding = exported.get("database", {})
        require(binding.get("archive_sha256") == EVIDENCE_SHA256 and binding.get("member") == DB_MEMBER
                and type(binding.get("sha256")) is str and HEX64.fullmatch(binding["sha256"])
                and type(binding.get("bytes")) is int and 0 < binding["bytes"] <= 8 * 1024**2
                and binding.get("sidecars_present") is False
                and binding.get("historical_uncaptured_state_recovered") is False, "INSPECTION_DATABASE_BINDING")
        tables = exported.get("tables")
        require(type(tables) is dict and set(tables) == TABLES, "INSPECTION_EXPORT_TABLE_SET")
        counts = {}
        for name, table in tables.items():
            require(type(table) is dict and type(table.get("columns")) is list
                    and all(type(column) is str for column in table["columns"])
                    and len(set(table["columns"])) == len(table["columns"])
                    and type(table.get("rows")) is list and type(table.get("row_count")) is int
                    and 0 <= table["row_count"] == len(table["rows"]) <= 10000
                    and all(type(row) is dict and set(row) == set(table["columns"]) for row in table["rows"]),
                    "INSPECTION_EXPORT_ROW_COUNTS:" + name)
            counts[name] = table["row_count"]
        require(type(exported.get("total_rows")) is int and sum(counts.values()) == exported["total_rows"] <= 50000
                and receipt.get("total_rows") == exported["total_rows"] and receipt.get("table_counts") == counts,
                "INSPECTION_EXPORTED_RECEIPT_COUNTS")
    elif receipt is not None:
        require(receipt.get("status") == "INSPECTION_FAILED" and type(receipt.get("failure")) is dict,
                "INSPECTION_FAILURE_RECEIPT_CONTRADICTION")
    return {"inspection_success": success, "files_verified": len(members),
        "collection": collection, "worker_receipt": receipt,
        "boundary": "Read-only stored database export; no model, training, native execution or qualification claim."}


def bind_lifecycle(transport):
    """A private module only; do not patch any shared or accepted module object."""
    require(transport.__name__ == "inspection_private_chq_lifecycle", "INSPECTION_PRIVATE_TRANSPORT_REQUIRED")
    transport.remote_config = remote_config
    transport.worker_permit = worker_permit
    transport.verify_parent_source = verify_parent_source
    transport.verify_packet = verify_packet
    transport.EXPERIMENT = dict(EXPERIMENT)
    transport.INPUT_KEYS = ("source.zip", "remote.py", "permit.json")
    transport.RESULT_KEYS = ("artifacts.zip", "complete.json", "bootstrap.log")
    return transport._run_authorized


def write_receipt(path, value):
    with Path(path).open("wb") as stream:
        stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())


def execute(request_path, request_sha256, authority_path, authority_sha256, receipt_dir, profile="default"):
    request = validate_request(decoded(read_pinned(request_path, request_sha256, 2 * 1024**2)))
    h = helpers(request["parent_source_sha"])
    require(h["identity"] == request["parent_file_sha256"], "INSPECTION_REQUEST_SOURCE_CHANGED")
    source = source_for(request)
    output = Path(receipt_dir).absolute()
    require(not output.exists() and output.is_relative_to(ROOT / "records") and output != ROOT / "records"
            and ".." not in output.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (output, *output.parents)), "INSPECTION_NEW_RECEIPT_DIRECTORY_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schema": "cas-meta2-native-failure-inspection-launch-receipt/8", "status": "STARTING",
        "job": request["job"], "experiment": EXPERIMENT, "request_sha256": request_sha256,
        "source_sha": request["worker_source_sha"], "parent_source_sha": request["parent_source_sha"],
        "source_archive_sha256": request["source_archive_sha256"],
        "transport_receipt_path": str(output / "lifecycle/launch_receipt.json"),
        "training": False, "native_execution": False, "sqlite_read_only": True,
        "boundary": "Inner CHQ-named receipt/status is reused lifecycle transport only; not a CHQ qualification run.",
        "provider_resources_created": False, "new_reservation": False}
    write_receipt(output / "launch_receipt.json", receipt)
    try:
        with h["old"].campaign_execution_lock():
            ledger = h["old"].budget.read_ledger()
            authority = validate_authority(authority_path, authority_sha256, request, request_sha256, ledger)
            require(Decimal(ledger["remaining_unreserved_usd"]) >= Decimal("4.00"), "INSPECTION_BUDGET_EXHAUSTED")
            clients = h["plumbing"].client_factory(profile, "us-west-2")
            preflight = h["plumbing"].provider_preflight(clients, request)
            receipt.update(delegation_started=True, new_reservation=None, provider_resources_created=None)
            write_receipt(output / "launch_receipt.json", receipt)
            inner = bind_lifecycle(h["transport"])(request, request_sha256, authority, source,
                h["old"], h["remote"], h["plumbing"], clients, preflight, output / "lifecycle")
            receipt.update(inner)
            receipt.update(schema="cas-meta2-native-failure-inspection-launch-receipt/8",
                transport_schema=inner.get("schema"), transport_status=inner.get("status"),
                transport_receipt_sha256=digest(safe_file(output / "lifecycle/launch_receipt.json")),
                status=("AWS_NATIVE_FAILURE_INSPECTION_FINISHED"
                    if inner.get("status") == "AWS_CHILD_QUALIFICATION_FINISHED"
                    and inner.get("artifact_collection", {}).get("inspection_success") is True
                    else "AWS_NATIVE_FAILURE_INSPECTION_FAILED"),
                training=False, native_execution=False, sqlite_read_only=True,
                new_reservation=({"NOT_ATTEMPTED": False, "RESERVED_NO_AUTOMATIC_REFUND": True}
                    .get(inner.get("budget_reservation_state"))),
                provider_resources_created=(True if inner.get("resources") else
                    False if inner.get("provider_resources_created") is False else None),
                boundary="Pinned CHQ lifecycle transport only. No qualification, training, model or native execution was requested.",
                cloud_artifacts_path=str(output / "lifecycle/cloud_artifacts.zip"))
    except BaseException as error:
        receipt.update(status="AWS_NATIVE_FAILURE_INSPECTION_REFUSED_OR_FAILED",
            error={"type": type(error).__name__, "message": str(error)})
    finally:
        try:
            require(verify_parent_source(request["parent_source_sha"]) == request["parent_file_sha256"],
                    "INSPECTION_PARENT_CHANGED_AFTER_ATTEMPT")
            receipt["source_postcheck"] = {"ok": True}
        except Exception as error:
            receipt.update(status="AWS_NATIVE_FAILURE_INSPECTION_REFUSED_OR_FAILED",
                source_postcheck={"ok": False, "type": type(error).__name__, "message": str(error)})
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        write_receipt(output / "launch_receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--execute", action="store_true")
    for name in ("request", "request-sha256", "authority", "authority-sha256", "receipt-dir"):
        parser.add_argument("--" + name)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"status": "PLAN_ONLY_NOT_EXECUTED", "experiment": EXPERIMENT,
            "training": False, "native_execution": False, "sqlite_read_only": True}))
        return 0
    require(all(getattr(args, name) for name in ("request", "request_sha256", "authority",
            "authority_sha256", "receipt_dir")), "INSPECTION_EXPLICIT_REGISTERED_INPUTS_REQUIRED")
    result = execute(args.request, args.request_sha256, args.authority, args.authority_sha256,
                     args.receipt_dir, args.profile)
    print(json.dumps({"status": result["status"], "receipt_dir": args.receipt_dir}))
    return 0 if result["status"] == "AWS_NATIVE_FAILURE_INSPECTION_FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
