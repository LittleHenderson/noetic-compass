"""Prepare one new continuation request under existing $400 campaign authority.

Inert: no AWS, reservation, final private targets or neural execution. All helper
working bytes and the static proposal must already exist in the exact HEAD.
"""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import importlib.abc
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/teaching_cycle_001"
PRIOR = RECORDS / "continuation_001"
PROPOSAL = "records/teaching_cycle_001/CONTINUATION_002_PROPOSAL.json"
SCHEMA = "cas-teaching-continuation-preparation/2"
FORBIDDEN = {"boto3", "botocore", "torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt", "cas_meta"}


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("CONTINUATION_PREPARE_FORBIDDEN_IMPORT:" + fullname)


def _modules():
    sys.path.insert(0, str(ROOT))
    from aws import teaching_continuation_plan_v2 as plan, teaching_continuation_launch_v2 as launch
    from aws import teaching_continuation_provider_v2 as provider, teaching_continuation_preflight_v2 as checks
    return plan, launch, provider, checks


def _file(path, launch):
    return sha256(launch._raw(path)).hexdigest()


def _committed_sources(provider, launch):
    source = provider.source_dependencies()
    launch.require({"tools/prepare_teaching_continuation_v2.py", "tools/run_teaching_continuation_v2.py"} <= set(source),
                   "CONTINUATION_TOOLS_MISSING_FROM_SOURCE_MAP")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    prefix = subprocess.check_output(["git", "rev-parse", "--show-prefix"], cwd=ROOT, text=True).strip()
    for name, expected in {**source, PROPOSAL: _file(ROOT / PROPOSAL, launch)}.items():
        launch.require(".." not in Path(name).parts and not Path(name).is_absolute(), "RELATIVE_SOURCE_PATH_REQUIRED")
        blob = subprocess.check_output(["git", "show", commit + ":" + prefix + name], cwd=ROOT)
        launch.require(sha256(blob).hexdigest() == expected, "COMMIT_SOURCE_MISMATCH:" + name)
    return commit, source


def _pricing(path, plan, launch, checks):
    raw = launch._raw(path)
    facts = launch._json(raw)
    expected = {"schema": checks.SCHEMA, "account_id": "807562639912", "region": "us-west-2",
        "instance_type": "g7.2xlarge", "source_sha256": _file(checks.__file__, launch),
        "plan_sha256": _file(plan.__file__, launch), "base_preflight_sha256": _file(checks.base.__file__, launch),
        "logical_run_id": plan.LOGICAL_RUN_ID, "restore_proved": False,
        "read_only": True, "reservation_created": False}
    launch.require(type(facts) is dict and facts.get("status") != "PREFLIGHT_FAILED"
        and all(launch.canonical(facts.get(key)) == launch.canonical(value) for key, value in expected.items())
        and type(facts.get("raw_prices")) is dict, "SUCCESSFUL_CURRENT_CONTINUATION_PREFLIGHT_REQUIRED")
    launch.require(facts.get("cost_worksheet") == plan.worksheet(facts["raw_prices"]), "PREFLIGHT_COST_WORKSHEET_MISMATCH")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(facts["observed_utc"])).total_seconds()
    launch.require(0 <= age <= 3600, "FRESH_READ_ONLY_PRICING_REQUIRED")
    return sha256(raw).hexdigest()


def _proposal(plan, launch):
    value = launch._json(launch._raw(ROOT / PROPOSAL))
    expected = {"schema": "cas-teaching-continuation-proposal/2", "task_scope": plan.TASK_SCOPE,
        "logical_run_id": plan.LOGICAL_RUN_ID, "source_commit": plan.FROZEN_BINDINGS["source_commit"],
        "source_sha256": plan.FROZEN_BINDINGS["source_sha256"], "original_campaign_root": plan.ORIGINAL_CAMPAIGN_ROOT,
        "remaining_optimizer_steps": 458, "allocated_epochs_per_arm": 16, "allocated_cycles_per_arm": 4096,
        "allocated_optimizer_steps_per_arm": 896, "training_families": 256, "development_cases": 64,
        "batch_size": 32, "stages_per_cycle": 7, "inclusive_campaign_cap_usd": "400.00",
        "source_material_profile_and_scoring_unchanged": True, "new_human_approval_claimed": False,
        "launch_authorized": False, "new_reservation": False}
    resource = plan.resource_plan()
    expected.update({key: resource[key] for key in ("account_id", "region", "instance_type", "instance_count",
        "required_gpu_name_contains", "runtime_seconds_max", "restore_probe_seconds_max", "training_worker_seconds_max",
        "prediction_process_count_max", "prediction_seconds_per_process_max", "prior_state_archive_bytes_max",
        "prior_state_expanded_bytes_max", "artifact_download_bytes_max", "reservation_usd", "automatic_retries")})
    launch.require(type(value) is dict and all(launch.canonical(value.get(key)) == launch.canonical(item)
        for key, item in expected.items()) and value.get("s3_storage_decimal_gb_months_max") == "6.00", "STATIC_PROPOSAL_MISMATCH")
    return _file(ROOT / PROPOSAL, launch)


def _inputs(plan, launch):
    from cas_meta2.teaching_cycle import continuation_package_v2 as package
    from cas_meta2.teaching_cycle.worker_contract import archive_payloads
    archive_payloads(RECORDS / "bundle_002/training.zip", plan.FROZEN_BINDINGS["archive_sha256"], plan.FROZEN_BINDINGS["manifest_sha256"])
    original_files = {"prior_parent_result_sha256": PRIOR / "launch/result.json",
        "prior_complete_sha256": PRIOR / "launch/partial_collected/complete.json",
        "prior_inspection_sha256": PRIOR / "continuation_inspection_002.json",
        "prior_cleanup_sha256": PRIOR / "cleanup_recovery_002/result.json"}
    documents = {}
    for key, path in original_files.items():
        raw = launch._raw(path)
        launch.require(sha256(raw).hexdigest() == plan.FROZEN_CONTINUATION[key], "ORIGINAL_EVIDENCE_CHANGED:" + key)
        documents[key] = launch._json(raw)
    cleanup = documents["prior_cleanup_sha256"]
    launch.require(cleanup.get("status") == "CLEANUP_CLOSED_RESULTS_RETAINED"
        and cleanup.get("ledger_unchanged") is True and cleanup.get("original_parent_result_unchanged") is True
        and cleanup.get("cleanup", {}).get("compute_closed") is True
        and cleanup["cleanup"].get("instance_state") in ("TERMINATED", "CONFIRMED_ABSENT_NOT_TERMINATION_RECEIPT"), "ORIGINAL_CLEANUP_NOT_CLOSED")
    inspection = documents["prior_inspection_sha256"]
    launch.require(inspection.get("structurally_resumable") is True and inspection.get("allocation_finished") is False
        and inspection.get("required_original_run_id") == plan.LOGICAL_RUN_ID, "ORIGINAL_STRUCTURAL_INSPECTION_REQUIRED")
    original_archive = PRIOR / "launch/partial_collected/artifacts.zip"
    observed = package.file_identity(original_archive)
    launch.require(observed["sha256"] == plan.FROZEN_CONTINUATION["prior_result_archive_sha256"], "ORIGINAL_RESULT_ARCHIVE_CHANGED")
    with ZipFile(original_archive) as archive:
        info = archive.getinfo(plan.RESUME_SUMMARY_PATH)
        launch.require(0 < info.file_size <= launch.base.JSON_BOUND, "ORIGINAL_SUMMARY_BYTE_BOUND")
        with archive.open(info) as stream:
            raw = stream.read(launch.base.JSON_BOUND + 1)
        launch.require(len(raw) == info.file_size and sha256(raw).hexdigest() == plan.FROZEN_CONTINUATION["prior_summary_sha256"],
                       "ORIGINAL_SUMMARY_CHANGED")
    package_root = PRIOR / "prior_package_002"
    raw_receipt = launch._raw(package_root / "receipt.json")
    receipt = launch._json(raw_receipt)
    launch.require(receipt.get("schema") == "cas-teaching-prior-state-build/2"
        and receipt.get("logical_run_id") == plan.LOGICAL_RUN_ID and receipt.get("originals_unchanged") is True
        and receipt.get("launch_authorized") is False and receipt.get("new_reservation") is False
        and receipt.get("private_targets_opened") is False, "PRIOR_PACKAGE_RECEIPT_INVALID")
    for key, filename in (("archive", "prior_state.zip"), ("manifest", "manifest.json")):
        expected_path = launch._safe(package_root / filename)
        declared = receipt[key]
        launch.require(launch._safe(declared["path"]) == expected_path
            and package.file_identity(expected_path) == {k: declared[k] for k in ("sha256", "bytes")}, "PRIOR_PACKAGE_MEMBER_CHANGED")
    continuation = {**plan.FROZEN_CONTINUATION,
        "prior_state_archive_sha256": receipt["archive"]["sha256"], "prior_state_manifest_sha256": receipt["manifest"]["sha256"],
        "prior_package_receipt_sha256": sha256(raw_receipt).hexdigest(),
        "prior_package_validator_sha256": _file(package.__file__, launch),
        "restore_probe_sha256": _file(ROOT / "aws/teaching_cycle_restore_probe_v2.py", launch),
        "continuation_plan_sha256": _file(plan.__file__, launch),
        "prior_state_archive_bytes": receipt["archive"]["bytes"],
        "prior_state_expanded_bytes": receipt["expanded_bytes"] + receipt["manifest"]["bytes"],
        "original_campaign_root": plan.ORIGINAL_CAMPAIGN_ROOT}
    plan.validate_continuation(continuation)
    context = {"run_id": plan.LOGICAL_RUN_ID, "bindings": plan.FROZEN_BINDINGS, "continuation": continuation,
        "prior_state_archive_path": str(package_root / "prior_state.zip"),
        "prior_state_manifest_path": str(package_root / "manifest.json")}
    launch._prior_input(context)
    return continuation, {key: str(path) for key, path in original_files.items()}


def prepare(output, pricing_receipt, *, job=None):
    guard = Guard()
    sys.meta_path.insert(0, guard)
    try:
        plan, launch, provider, checks = _modules()
        output = launch._safe(output)
        launch.require(output.is_relative_to(RECORDS) and not output.exists(), "FRESH_PREPARATION_REQUIRED")
        job = job or "cas-meta2-teaching-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]
        launch.require(type(job) is str and re.fullmatch(plan.JOB_PATTERN, job) and job != plan.LOGICAL_RUN_ID, "FRESH_CLOUD_JOB_REQUIRED")
        commit, source = _committed_sources(provider, launch)
        pricing_sha = _pricing(pricing_receipt, plan, launch, checks)
        proposal_sha = _proposal(plan, launch)
        continuation, original_evidence = _inputs(plan, launch)
        ledger = launch.ledger_snapshot(launch.budget.CANONICAL_LEDGER)
        plan.validate_ledger_snapshot(ledger["binding"])
        launch.require(not any(row["job"] == job for row in ledger["ledger"]["reservations"]), "JOB_ALREADY_RESERVED_NO_RETRY")
        output.mkdir(parents=True)
        from cas_meta2.teaching_cycle.evaluation import export_public
        export_public(RECORDS / "material_001", plan.FROZEN_BINDINGS["material_receipt_sha256"], output / "public.json")
        launch.require(_file(output / "public.json", launch) == plan.FROZEN_BINDINGS["public_sets_sha256"], "FROZEN_PUBLIC_EXPORT_CHANGED")
        bindings = {**plan.FROZEN_BINDINGS,
            "parent_driver_sha256": _file(ROOT / "aws/teaching_continuation_launch_v2.py", launch),
            "guest_driver_sha256": _file(ROOT / "aws/teaching_continuation_remote_v2.py", launch),
            "bootstrap_sha256": _file(ROOT / "aws/teaching_continuation_bootstrap.py", launch),
            "provider_source_sha256": _file(ROOT / "aws/teaching_continuation_provider_v2.py", launch),
            "provider_dependencies_sha256": plan.canonical_sha256(source), "proposal_sha256": proposal_sha,
            "pricing_receipt_sha256": pricing_sha}
        authority = {"schema": launch.AUTHORITY_SCHEMA, "task_scope": plan.TASK_SCOPE, "job": job,
            "logical_run_id": plan.LOGICAL_RUN_ID, "continuation": continuation, "bindings": bindings.copy(),
            "resource_plan_sha256": plan.canonical_sha256(plan.resource_plan()), "reservation_usd": "8.00",
            "automatic_retries": 0, "training": True, "native_execution": False, "launch_authorized": True,
            "reuses_v9_one_shot_authorization": False, "reuses_original_reservation": False}
        authority_file = launch.write_evidence(output / "authority.json", authority)
        bindings["authority_sha256"] = authority_file["sha256"]
        request = plan.build_request(job=job, logical_run_id=plan.LOGICAL_RUN_ID, bindings=bindings,
                                    continuation=continuation, ledger=ledger["binding"])
        request_file = launch.write_evidence(output / "request.json", request)
        source_file = launch.write_evidence(output / "provider_sources.json", source)
        standing = launch.write_evidence(output / "standing_authority.json", {
            "evidence_kind": "existing_canonical_campaign_owner_approval", "new_human_approval_claimed": False,
            "scope": "One continuation slice under the unchanged inclusive $400 CAS/CNCM campaign cap.",
            "canonical_approval": ledger["ledger"]["approval"], "ledger_binding": ledger["binding"]})
        receipt = {"schema": SCHEMA, "status": "PREPARED_NOT_RESERVED_NOT_LAUNCHED", "job": job,
            "logical_run_id": plan.LOGICAL_RUN_ID, "transport_source_commit": commit, "bindings": bindings,
            "continuation": continuation, "ledger": ledger["binding"], "request": request_file,
            "authority": authority_file, "provider_sources": source_file, "standing_authority": standing,
            "original_evidence": original_evidence, "public_sets_path": str(output / "public.json"),
            "pricing_receipt_path": str(launch._safe(pricing_receipt)), "source_archive": str(RECORDS / "bundle_002/training.zip"),
            "guest_driver": str(ROOT / "aws/teaching_continuation_remote_v2.py"),
            "base_guest_driver_path": str(ROOT / "aws/teaching_cycle_remote.py"),
            "package_validator_path": str(ROOT / "cas_meta2/teaching_cycle/continuation_package_v2.py"),
            "restore_probe_path": str(ROOT / "aws/teaching_cycle_restore_probe_v2.py"),
            "prior_state_archive_path": str(PRIOR / "prior_package_002/prior_state.zip"),
            "prior_state_manifest_path": str(PRIOR / "prior_package_002/manifest.json"),
            "new_reservation": False, "paid_execution": False, "private_targets_opened": False,
            "boundary": "Existing campaign approval only. Explicit execution must recheck all bytes, the canonical ledger and current provider state."}
        result = launch.write_evidence(output / "receipt.json", receipt)
        launch.require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_RUNTIME_LOADED")
        return result
    finally:
        sys.meta_path.remove(guard)


def load_preparation(path, expected_sha256):
    """Recheck all input/commit pins before constructing even an SDK client."""
    plan, launch, provider, checks = _modules()
    raw = launch._raw(path)
    launch.require(sha256(raw).hexdigest() == expected_sha256, "PREPARATION_DIGEST_MISMATCH")
    prepared = launch._json(raw)
    launch.require(prepared.get("schema") == SCHEMA and prepared.get("status") == "PREPARED_NOT_RESERVED_NOT_LAUNCHED"
        and prepared.get("new_reservation") is False and prepared.get("paid_execution") is False
        and prepared.get("private_targets_opened") is False and prepared.get("logical_run_id") == plan.LOGICAL_RUN_ID,
        "PREPARATION_SCHEMA_MISMATCH")
    def bound(name):
        declaration = prepared[name]
        value = launch._raw(declaration["path"])
        launch.require(len(value) == declaration["bytes"] and sha256(value).hexdigest() == declaration["sha256"],
                       "PREPARATION_FILE_CHANGED:" + name)
        return {"raw_utf8": value.decode(), "bytes": len(value), "sha256": declaration["sha256"]}
    request = launch.envelope_document(bound("request"))
    authority = bound("authority")
    standing = launch.envelope_document(bound("standing_authority"))
    sources = launch.envelope_document(bound("provider_sources"))
    commit, current_sources = _committed_sources(provider, launch)
    launch.require(commit == prepared["transport_source_commit"] and sources == current_sources
        and plan.canonical_sha256(sources) == prepared["bindings"]["provider_dependencies_sha256"], "PREPARED_SOURCE_FREEZE_CHANGED")
    continuation, originals = _inputs(plan, launch)
    launch.require(continuation == prepared["continuation"] and originals == prepared["original_evidence"], "PREPARED_PRIOR_STATE_CHANGED")
    launch.require(_pricing(prepared["pricing_receipt_path"], plan, launch, checks) == prepared["bindings"]["pricing_receipt_sha256"]
        and _proposal(plan, launch) == prepared["bindings"]["proposal_sha256"], "PREPARED_PRICING_OR_PROPOSAL_CHANGED")
    ledger = launch.ledger_snapshot(launch.budget.CANONICAL_LEDGER)
    launch.require(ledger["binding"] == prepared["ledger"] and standing.get("new_human_approval_claimed") is False
        and standing.get("canonical_approval") == ledger["ledger"]["approval"]
        and standing.get("ledger_binding") == prepared["ledger"], "STANDING_AUTHORITY_OR_LEDGER_CHANGED")
    plan.validate_request(request, expected_bindings=prepared["bindings"],
        expected_continuation=prepared["continuation"], expected_ledger=prepared["ledger"])
    launch._authority(authority, request)
    launch.require(request["job"] == prepared["job"] and request["logical_run_id"] == prepared["logical_run_id"], "PREPARATION_JOB_MISMATCH")
    for key, local, digest in (("source_archive", RECORDS / "bundle_002/training.zip", prepared["bindings"]["archive_sha256"]),
        ("guest_driver", ROOT / "aws/teaching_continuation_remote_v2.py", prepared["bindings"]["guest_driver_sha256"]),
        ("base_guest_driver_path", ROOT / "aws/teaching_cycle_remote.py", continuation["base_guest_driver_sha256"]),
        ("package_validator_path", ROOT / "cas_meta2/teaching_cycle/continuation_package_v2.py", continuation["prior_package_validator_sha256"]),
        ("restore_probe_path", ROOT / "aws/teaching_cycle_restore_probe_v2.py", continuation["restore_probe_sha256"])):
        launch.require(launch._safe(prepared[key]) == launch._safe(local) and _file(local, launch) == digest, "PREPARED_FILE_CHANGED:" + key)
    for key, filename in (("prior_state_archive_path", "prior_state.zip"), ("prior_state_manifest_path", "manifest.json")):
        launch.require(launch._safe(prepared[key]) == launch._safe(PRIOR / "prior_package_002" / filename), "PREPARED_PRIOR_PATH_CHANGED")
    launch.require(_file(prepared["public_sets_path"], launch) == prepared["bindings"]["public_sets_sha256"], "PREPARED_PUBLIC_CHANGED")
    return prepared, request, authority


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pricing-receipt", required=True)
    parser.add_argument("--job")
    args = parser.parse_args(argv)
    print(json.dumps(prepare(args.output, args.pricing_receipt, job=args.job)))


if __name__ == "__main__":
    main()
