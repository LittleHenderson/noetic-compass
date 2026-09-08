"""Prepare a new teaching request from standing campaign authority; never launch.

The canonical ledger's owner approval supplies the existing $400 authority.
This creates a fresh, $8 job-specific record. It does not invent a new human
approval, reserve money, reuse v9 permission, open private gold, or call AWS.
"""
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import importlib.abc
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/teaching_cycle_001"
FORBIDDEN = {"boto3", "botocore", "torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt", "cas_meta"}


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("PREPARE_ONLY_FORBIDDEN_IMPORT:" + fullname)


def prepare(output, pricing_receipt, *, job=None):
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    from aws import teaching_cycle_plan as plan
    from aws import teaching_cycle_launch as launch
    from aws import teaching_cycle_provider as provider
    from aws import teaching_cycle_preflight as checks
    from cas_meta2.teaching_cycle.evaluation import export_public
    from cas_meta2.teaching_cycle.worker_contract import archive_payloads
    output = launch._safe(output)
    launch.require(output.is_relative_to(RECORDS) and not output.exists(), "FRESH_PREPARATION_REQUIRED")
    source = provider.source_dependencies()
    # Working bytes must already exist in this exact commit. Untracked source
    # cannot silently become part of a purported source freeze.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    prefix = subprocess.check_output(["git", "rev-parse", "--show-prefix"], cwd=ROOT, text=True).strip()
    for name, expected in source.items():
        blob = subprocess.check_output(["git", "show", commit + ":" + prefix + name], cwd=ROOT)
        launch.require(sha256(blob).hexdigest() == expected, "COMMIT_SOURCE_MISMATCH:" + name)
    archive_payloads(RECORDS / "bundle_002/training.zip", plan.FROZEN_BINDINGS["archive_sha256"],
                     plan.FROZEN_BINDINGS["manifest_sha256"])
    pricing_raw = launch._raw(pricing_receipt)
    pricing = launch._json(pricing_raw)
    launch.require(type(pricing) is dict and pricing.get("schema") == "cas-teaching-live-preflight/1"
        and pricing.get("status") != "PREFLIGHT_FAILED"
        and pricing.get("account_id") == "807562639912" and pricing.get("region") == "us-west-2"
        and pricing.get("instance_type") == "g7.2xlarge"
        and pricing.get("source_sha256") == sha256(launch._raw(checks.__file__)).hexdigest()
        and type(pricing.get("raw_prices")) is dict and type(pricing.get("cost_worksheet")) is dict,
        "SUCCESSFUL_CURRENT_PREFLIGHT_REQUIRED")
    launch.require(pricing["cost_worksheet"] == checks.worksheet(pricing["raw_prices"]),
                   "PREFLIGHT_COST_WORKSHEET_MISMATCH")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(pricing["observed_utc"])).total_seconds()
    launch.require(pricing.get("read_only") is True and pricing.get("reservation_created") is False
                   and 0 <= age <= 3600, "FRESH_READ_ONLY_PRICING_REQUIRED")
    ledger = launch.ledger_snapshot(launch.budget.CANONICAL_LEDGER)
    job = job or "cas-meta2-teaching-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]
    output.mkdir(parents=True)
    material_sha = "32cfb9183d389a880df49bf35dbda518cfcf277ddaf704d42abb169f9704a256"
    export_public(RECORDS / "material_001", material_sha, output / "public.json")
    def file_hash(path):
        return sha256(launch._raw(path)).hexdigest()
    bindings = {**plan.FROZEN_BINDINGS, "material_receipt_sha256": material_sha,
        "public_sets_sha256": file_hash(output / "public.json"),
        "scorer_sha256": file_hash(ROOT / "cas_meta2/teaching_cycle/evaluation.py"),
        "parent_driver_sha256": file_hash(ROOT / "aws/teaching_cycle_launch.py"),
        "guest_driver_sha256": file_hash(ROOT / "aws/teaching_cycle_remote.py"),
        "bootstrap_sha256": file_hash(ROOT / "aws/teaching_cycle_bootstrap.py"),
        "provider_source_sha256": file_hash(ROOT / "aws/teaching_cycle_provider.py"),
        "provider_dependencies_sha256": plan.canonical_sha256(source),
        "proposal_sha256": file_hash(RECORDS / "LAUNCH_PROPOSAL.json"),
        "pricing_receipt_sha256": sha256(pricing_raw).hexdigest()}
    authority = {"schema": launch.AUTHORITY_SCHEMA, "task_scope": plan.TASK_SCOPE, "job": job,
        "bindings": bindings.copy(), "resource_plan_sha256": plan.canonical_sha256(plan.resource_plan()),
        "reservation_usd": "8.00", "automatic_retries": 0, "training": True,
        "native_execution": False, "launch_authorized": True, "reuses_v9_one_shot_authorization": False}
    authority_file = launch.write_evidence(output / "authority.json", authority)
    bindings["authority_sha256"] = authority_file["sha256"]
    request = plan.build_request(job=job, bindings=bindings, ledger=ledger["binding"])
    request_file = launch.write_evidence(output / "request.json", request)
    source_file = launch.write_evidence(output / "provider_sources.json", source)
    standing = launch.write_evidence(output / "standing_authority.json", {
        "evidence_kind": "existing_canonical_campaign_owner_approval",
        "new_human_approval_claimed": False, "scope": "Candidate teaching within the inclusive $400 CAS/CNCM goal.",
        "canonical_approval": ledger["ledger"]["approval"], "ledger_binding": ledger["binding"]})
    receipt = {"schema": "cas-teaching-launch-preparation/1", "status": "PREPARED_NOT_RESERVED_NOT_LAUNCHED",
        "job": job, "transport_source_commit": commit, "bindings": bindings, "ledger": ledger["binding"],
        "request": request_file, "authority": authority_file, "provider_sources": source_file,
        "standing_authority": standing, "public_sets_path": str(output / "public.json"),
        "pricing_receipt_path": str(Path(pricing_receipt).absolute()),
        "source_archive": str(RECORDS / "bundle_002/training.zip"),
        "guest_driver": str(ROOT / "aws/teaching_cycle_remote.py"), "new_reservation": False,
        "paid_execution": False, "private_targets_opened": False,
        "boundary": "Explicit execution must recheck these bytes, the canonical ledger and live provider state."}
    result = launch.write_evidence(output / "receipt.json", receipt)
    launch.require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_RUNTIME_LOADED")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pricing-receipt", required=True)
    parser.add_argument("--job")
    args = parser.parse_args(argv)
    print(json.dumps(prepare(args.output, args.pricing_receipt, job=args.job)))


if __name__ == "__main__":
    main()
