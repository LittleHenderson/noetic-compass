"""Separate saved-repair launch. Default is pure; the old lifecycle is transport only."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import importlib.util
import io
from pathlib import Path
import re
import stat
import uuid
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = {"profile": "saved_native_repair_v8", "entrypoint": "cas_meta2.saved_repair_gpu_v8"}
UTILITY_PIN = "2b79a1e8ed73066a6618afedbdfc56c769290ccc221e84fe51d4eb6b01ed1bb6"


def _utility():
    path = Path(__file__).with_name("launch_native_failure_inspection_v8.py")
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)):
        raise ValueError("SAVED_PARENT_HELPER_LINK")
    if not path.is_file() or sha256(path.read_bytes()).hexdigest() != UTILITY_PIN:
        raise ValueError("SAVED_PARENT_HELPER_CHANGED")
    spec = importlib.util.spec_from_file_location("saved_repair_private_parent_utilities", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PARENT_FILES = ("aws/launch_saved_repair_v8.py", "aws/saved_repair_remote_v8.py", "aws/saved_repair_package_v8.py",
                          "cas_meta2/saved_repair_v8.py", "cas_meta2/saved_repair_gpu_v8.py")
    module.FROZEN_PINS = {**module.FROZEN_PINS,
        "aws/launch_native_failure_inspection_v8.py": UTILITY_PIN,
        "aws/child_qualification_remote_v8.py": "fbecb2a6e06bde2052983a9073b72e2791b4ebff29c52909d7244c4366b6ab2d",
        "aws/child_qualification_package_v8.py": "9925514d1d017cd6b247f3db634a276cc3b4b7ce69cfc858758b32e8e66d4bf7",
        "aws/br_package_v8.py": "23a30b7e4e3862702699e078bee953436be630f1390127f8668f519c1119b2e8"}
    return module


u = _utility()
require, encoded, decoded, digest, safe_file, read_pinned = u.require, u.encoded, u.decoded, u.digest, u.safe_file, u.read_pinned
verify_parent_source, safe_member = u.verify_parent_source, u.safe_member
STANDING_MESSAGE_SHA256 = u.STANDING_MESSAGE_SHA256
PARENT_FILES, FROZEN_PINS = u.PARENT_FILES, u.FROZEN_PINS


def resource_plan():
    template = u.load_module("saved_repair_resource_template", "aws/launch_child_qualification_v8.py").resource_plan()
    return {**template, "worker_seconds_max": 600, "max_native_calls": 2, "max_policy_units": 16384,
            "outer_caller_restored": False}


def helpers(source_sha):
    identity = verify_parent_source(source_sha)
    return {"identity": identity,
        "transport": u.load_module("saved_repair_private_chq_lifecycle", "aws/launch_child_qualification_v8.py"),
        "old": u.load_module("saved_repair_owned_cleanup", "aws/launch_prototype_v7.py"),
        "plumbing": u.load_module("saved_repair_plumbing", "aws/launch_prefix_diagnostic_v8.py"),
        "remote": u.load_module("saved_repair_remote", "aws/saved_repair_remote_v8.py"),
        "package": u.load_module("saved_repair_package", "aws/saved_repair_package_v8.py")}


def scope():
    return {"max_seconds": 600, "max_cost_usd": "4.00", "seed": 7, "max_native_calls": 2, "max_policy_units": 16384,
        "training": False, "native_execution": True, "max_output_bytes": 536870912,
        "automatic_retries": 0, "outer_caller_restored": False}


def validate_request(request):
    require(type(request) is dict and request.get("schema") == "cas-meta2-saved-repair-launch-request/8"
            and re.fullmatch(r"cas-meta2-[0-9]{14}-[a-f0-9]{8}", request.get("job", "")),
            "SAVED_SEPARATE_REQUEST_REQUIRED")
    require(request["job"] not in ("cas-meta2-20260906155525-195f5ad8", "cas-meta2-20260906162339-56837284"),
            "SAVED_FRESH_JOB_REQUIRED")
    require(request.get("experiment") == EXPERIMENT and encoded(request.get("resource_plan")) == encoded(resource_plan())
            and encoded(request.get("repair_scope")) == encoded(scope()), "SAVED_EXACT_SCOPE")
    require(re.fullmatch("[a-f0-9]{40}", request.get("parent_source_sha", ""))
            and request.get("worker_source_sha") == request["parent_source_sha"], "SAVED_SOURCE_COMMIT")
    for key in ("source_archive_sha256", "source_manifest_sha256"):
        require(re.fullmatch("[a-f0-9]{64}", request.get(key, "")), "SAVED_SOURCE_DIGEST")
    require(type(request.get("source_archive_bytes")) is int and 0 < request["source_archive_bytes"] <= 16 * 1024**2
            and re.fullmatch(r"subnet-[a-f0-9]{8,17}", request.get("subnet_id", "")), "SAVED_INPUT_OR_SUBNET")
    require(request.get("launch_authorized") is False and request.get("standing_authority_registration_required") is True
            and request.get("provider_calls") is False and request.get("new_reservation") is False, "SAVED_REGISTERED_AUTHORITY")
    return request


def source_for(request, package):
    require(len(read_pinned(request["source_archive"], request["source_archive_sha256"])) == request["source_archive_bytes"],
            "SAVED_PACKAGE_BYTES")
    manifest = package.inspect_archive(request["source_archive"], expected_sha256=request["source_archive_sha256"],
        expected_source_sha=request["worker_source_sha"], expected_manifest_sha256=request["source_manifest_sha256"])
    require(all(manifest["files_sha256"][package.PILOT + name] == request["parent_file_sha256"].get(name)
                for name in package.ADDITIONS), "SAVED_WORKER_ADDITIONS_DIFFER_FROM_COMMITTED_PARENT")
    return manifest


def build_request(source_sha, subnet_id, archive, archive_sha256, manifest_sha256):
    h = helpers(source_sha)
    request = {"schema": "cas-meta2-saved-repair-launch-request/8", "experiment": EXPERIMENT,
        "job": "cas-meta2-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8],
        "parent_source_sha": source_sha, "worker_source_sha": source_sha, "parent_file_sha256": h["identity"],
        "source_archive": str(Path(archive).absolute()), "source_archive_sha256": archive_sha256,
        "source_archive_bytes": len(read_pinned(archive, archive_sha256)), "source_manifest_sha256": manifest_sha256,
        "subnet_id": subnet_id, "resource_plan": resource_plan(), "repair_scope": scope(),
        "launch_authorized": False, "standing_authority_registration_required": True,
        "provider_calls": False, "new_reservation": False}
    validate_request(request)
    source_for(request, h["package"])
    return request


def validate_authority(path, expected, request, request_sha256, ledger):
    record = decoded(read_pinned(path, expected, 1024**2))
    wanted = {"schema": "cas-meta2-saved-repair-standing-authority/8", "standing_campaign_authorization": True,
        "campaign_cap_usd": "400.00", "max_job_cost_usd": "4.00", "experiment": EXPERIMENT,
        "training": False, "native_execution": True, "outer_caller_restored": False,
        "max_native_calls": 2, "max_policy_units": 16384,
        "launch_request_sha256": request_sha256, **{k: request[k] for k in ("job", "parent_source_sha",
            "worker_source_sha", "source_archive_sha256", "source_manifest_sha256")}}
    require(all(type(record.get(k)) is type(v) and record[k] == v for k, v in wanted.items()), "SAVED_AUTHORITY_SCOPE")
    campaign = record.get("campaign_approval", {})
    require(campaign == {k: ledger["approval"][k] for k in ("path", "sha256")}
            and Path(campaign["path"]).is_absolute(), "SAVED_CANONICAL_CAMPAIGN")
    read_pinned(campaign["path"], campaign["sha256"])
    message = record.get("standing_user_message", {})
    require(type(message.get("path")) is str and Path(message["path"]).is_absolute()
            and message.get("sha256") == STANDING_MESSAGE_SHA256, "SAVED_FULL_STANDING_MESSAGE")
    read_pinned(message["path"], STANDING_MESSAGE_SHA256, 1024**2)
    require(ledger.get("owner_task_cap_usd") == "400.00" and ledger.get("no_automatic_refund") is True, "SAVED_CAMPAIGN_CAP")
    return {**record, "authority_artifact_sha256": expected}


def remote_config(request, source):
    return {"schema": "cas-meta2-saved-repair-remote/8", "job": request["job"], "bucket": request["job"] + "-807562639912",
        "region": "us-west-2", "account_id": "807562639912", "experiment": EXPERIMENT,
        **{k: request[k] for k in ("parent_source_sha", "worker_source_sha", "source_archive_sha256",
            "source_archive_bytes", "source_manifest_sha256", "resource_plan")},
        "source_manifest": source, "package_layout": source["base"]["package_layout"],
        "max_worker_seconds": 600, "artifact_bytes_max": 268435456, "evidence_expanded_bytes_max": 536870912}


def worker_permit(request, source, reservation, ledger, instance_id, deadline):
    require(re.fullmatch("i-[a-f0-9]{17}", instance_id), "SAVED_INSTANCE_ID")
    base = "/opt/cas-meta2-saved-repair/"
    plan = {"schema": "cas-meta2-saved-repair-plan/8", "launch_enabled": True, "experiment": EXPERIMENT,
        **scope(), "job": request["job"], "instance_id": instance_id, "source_sha": request["worker_source_sha"],
        "resource_plan": request["resource_plan"],
        "source_manifest": {"path": base + "package/saved_repair_source_manifest.json", "sha256": request["source_manifest_sha256"]},
        "source_archive": {"path": base + "source.zip", "sha256": request["source_archive_sha256"]},
        "evidence_archive": {"path": base + "package/data/prior_failure.zip",
                            "sha256": "39a2441a2eaa4c7403af11225356a98aee2a4477e26acffbc483254befa1ed7f"},
        "reservation_receipt": {"path": base + "launch/reservation_receipt.json", "sha256": digest(encoded(reservation))},
        "ledger_snapshot": {"path": base + "launch/ledger_snapshot.json", "sha256": digest(encoded(ledger))}}
    return {"job": request["job"], "archive_sha256": request["source_archive_sha256"], "instance_id": instance_id,
        "cloud_deadline_confirmed": True, "deadline": deadline.isoformat(), "worker_plan": plan,
        "worker_plan_sha256": digest(encoded(plan)), "reservation_receipt": reservation, "ledger_snapshot": ledger}


def verify_packet(artifact, result, request, plan_hash):
    raw = read_pinned(artifact, result["sha256"], 268435456)
    require(len(raw) == result["bytes"], "SAVED_RESULT_SIZE")
    common = {"job": request["job"], "source_sha": request["worker_source_sha"],
        "parent_source_sha": request["parent_source_sha"], "experiment": EXPERIMENT}
    require(all(result.get(k) == v for k, v in common.items()) and type(result.get("returncode")) is int, "SAVED_RESULT_IDENTITY")
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [safe_member(i.filename) for i in infos]
        require(len(names) == len(set(names)) == len({n.casefold() for n in names}) and len(names) <= 4096
                and all(not i.is_dir() and not i.flag_bits & 1 and stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG) for i in infos)
                and sum(i.file_size for i in infos) <= 536870912, "SAVED_RESULT_MEMBER_BOUND")
        files = {n: archive.read(n) for n in names}
    collection = decoded(files.pop("artifact_collection_receipt.json"))
    require(all(collection.get(k) == v for k, v in common.items()) and collection.get("returncode") == result["returncode"],
            "SAVED_COLLECTION_IDENTITY")
    if collection.get("full_file_counts_known") is False:
        require(result["returncode"] == 1 and collection.get("partial_evidence") is True
                and collection.get("original_file_count") is None and collection.get("included_full_file_count") == 0
                and collection.get("omitted_full_file_count") is None and not files
                and type(collection.get("collection_failure")) is dict, "SAVED_EMERGENCY_PACKET")
        return {"native_success": False, "worker_receipt": None, "collection": collection,
            "files_verified": 0, "original_member_coverage_verified": False,
            "boundary": "Emergency collection receipt only; native result unavailable."}
    index = collection.get("files", {})
    require(type(index) is dict and type(collection.get("partial_evidence")) is bool
            and collection["partial_evidence"] == result.get("partial_evidence")
            and collection.get("omitted_full_file_count") == result.get("omitted_full_file_count"), "SAVED_COLLECTION_INDEX")
    for name, item in index.items():
        safe_member(name)
        require(type(item) is dict and type(item.get("bytes")) is int and 0 <= item["bytes"] <= 536870912
                and type(item.get("sha256")) is str and re.fullmatch("[a-f0-9]{64}", item["sha256"]),
                "SAVED_COLLECTION_INDEX_ITEM")
        if name in files:
            require(item == {"bytes": len(files[name]), "sha256": digest(files[name])}, "SAVED_COLLECTED_BYTES:" + name)
    tails = set(files) - set(index)
    require(len(tails) <= 12 and all(re.fullmatch(r"failure_tails/(?:[0-9]|1[01])\.txt", n)
            and len(files[n]) <= 16384 for n in tails)
            and (not tails or collection["partial_evidence"] is True), "SAVED_UNINDEXED_MEMBER")
    require(collection.get("original_file_count") == len(index)
            and collection.get("included_full_file_count") == len(set(files) - tails)
            and collection.get("omitted_full_file_count") == len(set(index) - set(files)), "SAVED_COLLECTION_COUNTS")
    worker = decoded(files["repair/worker_receipt.json"]) if "repair/worker_receipt.json" in files else None
    missing_worker_files = []
    if worker is not None:
        require(worker.get("schema") == "cas-meta2-saved-repair-gpu/8" and worker.get("job") == request["job"]
                and worker.get("source_sha") == request["worker_source_sha"]
                and worker.get("source_archive_sha256") == request["source_archive_sha256"]
                and worker.get("source_manifest_sha256") == request["source_manifest_sha256"]
                and worker.get("plan_sha256") == plan_hash and worker.get("training") is False
                and worker.get("native_execution") is True and worker.get("outer_caller_restored") is False
                and worker.get("experiment") == EXPERIMENT and worker.get("status") in
                ("SAVED_NATIVE_REPAIR_SUCCEEDED", "SAVED_NATIVE_REPAIR_REFUSED_OR_FAILED",
                 "SAVED_NATIVE_REPAIR_STOPPED_OR_FAILED"), "SAVED_WORKER_BINDING")
        mapping = worker["files_sha256"]
        expected_worker = {"repair/" + safe_member(n) for n in mapping} | {"repair/worker_receipt.json"}
        require({n for n in files if n.startswith("repair/")} <= expected_worker
                and all(type(pin) is str and re.fullmatch("[a-f0-9]{64}", pin)
                    and ("repair/" + n not in files or digest(files["repair/" + n]) == pin)
                    for n, pin in mapping.items()), "SAVED_WORKER_FILE_BINDING")
        missing_worker_files = sorted(expected_worker - set(files))
    success = result["returncode"] == 0
    if success:
        require(collection.get("partial_evidence") is False and collection.get("omitted_full_file_count") == 0
                and set(index) == set(files) and not missing_worker_files
                and worker is not None and worker.get("status") == "SAVED_NATIVE_REPAIR_SUCCEEDED"
                and worker.get("failure") is None and worker.get("cleanup_errors") == []
                and all(worker.get("postchecks", {}).get(k) == {"ok": True} for k in
                    ("source", "reservation", "accepted_sources", "original_database", "output_bound", "deadline")),
                "SAVED_COMPLETE_REPAIR_REQUIRED")
        repair = worker.get("repair", {})
        require(repair.get("status") == "REPAIR_RESUMED" and repair.get("repaired") is True
                and repair.get("training") is False
                and all(type(repair.get(k)) is int and repair[k] == 2 for k in
                    ("native_call_attempts", "returned_native_calls", "completed_new_ticks", "accepted_new_ticks"))
                and type(repair.get("attempted_policy_units")) is int and 0 < repair["attempted_policy_units"] <= 16384,
                "SAVED_CORE_REPAIR_REQUIRED")
        require("repair/repair/repair_receipt.json" in files
                and decoded(files["repair/repair/repair_receipt.json"]) == repair, "SAVED_CORE_RECEIPT_COPY")
    return {"native_success": success, "worker_receipt": worker, "collection": collection,
        "files_verified": len(set(files) - tails), "failure_tail_hashes": {n: digest(files[n]) for n in sorted(tails)},
        "missing_worker_files": missing_worker_files, "original_member_coverage_verified": not collection["partial_evidence"],
        "boundary": "Saved native repair only; no restored outer caller, task qualification or training claim."}


def bind_lifecycle(transport):
    require(transport.__name__ == "saved_repair_private_chq_lifecycle", "SAVED_PRIVATE_TRANSPORT")
    for name, value in {"remote_config": remote_config, "worker_permit": worker_permit,
        "verify_parent_source": verify_parent_source, "verify_packet": verify_packet, "EXPERIMENT": EXPERIMENT,
        "INPUT_KEYS": ("source.zip", "remote.py", "permit.json"),
        "RESULT_KEYS": ("artifacts.zip", "complete.json", "bootstrap.log")}.items():
        setattr(transport, name, value)
    return transport._run_authorized


def execute(request_path, request_sha256, authority_path, authority_sha256, receipt_dir, profile="default"):
    request = validate_request(decoded(read_pinned(request_path, request_sha256, 2 * 1024**2)))
    h = helpers(request["parent_source_sha"])
    require(h["identity"] == request["parent_file_sha256"], "SAVED_PARENT_CHANGED")
    source = source_for(request, h["package"])
    output = Path(receipt_dir).absolute()
    require(not output.exists() and output.is_relative_to(ROOT / "records") and output != ROOT / "records"
            and ".." not in output.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (output, *output.parents)), "SAVED_FRESH_RECEIPT_DIRECTORY")
    output.mkdir(parents=True)
    receipt = {"schema": "cas-meta2-saved-repair-launch-receipt/8", "status": "STARTING", "job": request["job"],
        "experiment": EXPERIMENT, "request_sha256": request_sha256, "source_sha": request["worker_source_sha"],
        "parent_source_sha": request["parent_source_sha"], "training": False, "native_execution": True,
        "outer_caller_restored": False, "new_reservation": False, "provider_resources_created": False,
        "transport_receipt_path": str(output / "lifecycle/launch_receipt.json")}
    u.write_receipt(output / "launch_receipt.json", receipt)
    try:
        with h["old"].campaign_execution_lock():
            ledger = h["old"].budget.read_ledger()
            authority = validate_authority(authority_path, authority_sha256, request, request_sha256, ledger)
            require(Decimal(ledger["remaining_unreserved_usd"]) >= Decimal("4.00"), "SAVED_BUDGET_EXHAUSTED")
            clients = h["plumbing"].client_factory(profile, "us-west-2")
            preflight = h["plumbing"].provider_preflight(clients, request)
            receipt.update(delegation_started=True, new_reservation=None, provider_resources_created=None)
            u.write_receipt(output / "launch_receipt.json", receipt)
            inner = bind_lifecycle(h["transport"])(request, request_sha256, authority, source, h["old"],
                h["remote"], h["plumbing"], clients, preflight, output / "lifecycle")
            receipt.update(inner)
            receipt.update(schema="cas-meta2-saved-repair-launch-receipt/8", transport_schema=inner.get("schema"),
                transport_status=inner.get("status"), transport_receipt_sha256=digest(safe_file(output / "lifecycle/launch_receipt.json")),
                status=("AWS_SAVED_NATIVE_REPAIR_FINISHED" if inner.get("status") == "AWS_CHILD_QUALIFICATION_FINISHED"
                    and inner.get("artifact_collection", {}).get("native_success") is True else "AWS_SAVED_NATIVE_REPAIR_FAILED"),
                training=False, native_execution=True, outer_caller_restored=False,
                new_reservation={"NOT_ATTEMPTED": False, "RESERVED_NO_AUTOMATIC_REFUND": True}.get(inner.get("budget_reservation_state")),
                provider_resources_created=True if inner.get("resources") else None,
                cloud_artifacts_path=str(output / "lifecycle/cloud_artifacts.zip"),
                boundary="CHQ-named inner lifecycle is transport only; this is saved repair, not task qualification or learning.")
    except BaseException as error:
        receipt.update(status="AWS_SAVED_NATIVE_REPAIR_REFUSED_OR_FAILED", error={"type": type(error).__name__, "message": str(error)})
    finally:
        try:
            require(verify_parent_source(request["parent_source_sha"]) == request["parent_file_sha256"], "SAVED_SOURCE_POSTCHECK")
            receipt["source_postcheck"] = {"ok": True}
        except Exception as error:
            receipt.update(status="AWS_SAVED_NATIVE_REPAIR_REFUSED_OR_FAILED",
                source_postcheck={"ok": False, "type": type(error).__name__, "message": str(error)})
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        u.write_receipt(output / "launch_receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--execute", action="store_true")
    for name in ("request", "request-sha256", "authority", "authority-sha256", "receipt-dir"):
        parser.add_argument("--" + name)
    parser.add_argument("--profile", default="default")
    args = parser.parse_args(argv)
    if not args.execute:
        print(encoded({"status": "PLAN_ONLY_NOT_EXECUTED", "experiment": EXPERIMENT, "scope": scope()}).decode())
        return 0
    require(all(getattr(args, n) for n in ("request", "request_sha256", "authority", "authority_sha256", "receipt_dir")),
            "SAVED_EXPLICIT_REGISTERED_INPUTS")
    result = execute(args.request, args.request_sha256, args.authority, args.authority_sha256, args.receipt_dir, args.profile)
    print(encoded({"status": result["status"], "receipt_dir": args.receipt_dir}).decode())
    return 0 if result["status"] == "AWS_SAVED_NATIVE_REPAIR_FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
