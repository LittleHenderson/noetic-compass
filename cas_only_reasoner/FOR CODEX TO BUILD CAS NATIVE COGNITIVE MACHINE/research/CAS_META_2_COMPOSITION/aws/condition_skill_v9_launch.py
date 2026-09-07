"""Launch lifecycle for condition-skill v9. Plan is inert by default.

Paid execution requires an explicit, hash-bound launch request AND a separate
standing authority that names the job, exact source/archive identities, the
frozen resource plan values, and the owner phase-approval record. The single
$4.00 reservation is created exactly once under the campaign ledger, after
read-only provider preflight, and is never refunded or retried. Provider calls
are injected, so this module is pure-testable; the real AWS adapter is a
separate module and remains a required gate.

Every exit path runs cleanup and records its failures. A timeout, refusal, or
crash is a recorded failed launch, never authority to rerun.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time
from hashlib import sha256

from aws import condition_skill_v9_resource_plan as plan

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cas-meta2-condition-skill-v9-launch/9"
AUTHORITY_SCHEMA = "cas-meta2-condition-skill-v9-authority/9"
LEDGER_PATH = ROOT / "records/budget/campaign_ledger.json"
RESERVATION_USD = "4.00"
CAMPAIGN_CAP_USD = "400.00"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return sha256(raw).hexdigest()


def scope():
    """The frozen resource plan; returning it is not an authorization."""
    return plan.scope()


def validate_request(request):
    """The request stays inert; only the separate authority authorizes."""
    return plan.validate_launch_request(request)


def validate_authority(authority):
    """Strict standing authority; exact fields only, all bound to the job."""
    require(type(authority) is dict and authority.get("schema") == AUTHORITY_SCHEMA,
            "CONDITION_SKILL_V9_AUTHORITY_SCHEMA")
    require(set(authority) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "dataset_manifest_sha256", "seed", "training", "native_execution",
        "automatic_retries", "reservation_usd", "task_scope", "campaign_scope",
        "owner_approval_record_sha256"}, "CONDITION_SKILL_V9_AUTHORITY_FIELDS")
    require(type(authority["job"]) is str
            and re.fullmatch(r"cas-meta2-\d{14}-[a-f0-9]{8}", authority["job"]) is not None,
            "CONDITION_SKILL_V9_AUTHORITY_JOB")
    require(type(authority["source_sha"]) is str
            and re.fullmatch(r"[a-f0-9]{40}", authority["source_sha"]) is not None,
            "CONDITION_SKILL_V9_AUTHORITY_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "dataset_manifest_sha256",
                "owner_approval_record_sha256"):
        require(type(authority[key]) is str
                and re.fullmatch(r"[a-f0-9]{64}", authority[key]) is not None,
                "CONDITION_SKILL_V9_AUTHORITY_HASH:" + key)
    require(authority["seed"] == plan.RESOURCE_PLAN["seed"], "CONDITION_SKILL_V9_AUTHORITY_SEED")
    require(authority["training"] is True and authority["native_execution"] is False,
            "CONDITION_SKILL_V9_AUTHORITY_SCOPE")
    require(authority["automatic_retries"] == 0, "CONDITION_SKILL_V9_AUTHORITY_NO_RETRIES")
    require(authority["reservation_usd"] == RESERVATION_USD,
            "CONDITION_SKILL_V9_AUTHORITY_RESERVATION")
    require(authority["task_scope"] == "condition_skill_v9"
            and authority["campaign_scope"] == "cas-meta2-composition-campaign",
            "CONDITION_SKILL_V9_AUTHORITY_BUDGET_SCOPES")
    return authority


def plan_only(request=None, authority=None):
    if request is not None:
        validate_request(request)
    if authority is not None:
        validate_authority(authority)
    return {"schema": SCHEMA, "status": "PLAN_ONLY_NOT_EXECUTED",
            "experiment": plan.EXPERIMENT, "scope": scope(),
            "reservation_created": False, "provider_calls": 0,
            "boundary": "No provider client, reservation, model import, or output mutation occurred."}


def read_ledger(path=LEDGER_PATH):
    path = Path(path)
    raw = path.read_bytes()
    ledger = json.loads(raw)
    require(type(ledger.get("revision")) is int and ledger["revision"] >= 1,
            "LEDGER_REVISION_REQUIRED")
    for key in ("cap_usd", "reserved_usd", "unreserved_usd"):
        require(type(ledger.get(key)) is str and float(ledger[key]) >= 0,
                "LEDGER_FIELD:" + key)
    require(float(ledger["cap_usd"]) == float(CAMPAIGN_CAP_USD), "LEDGER_CAP_CHANGED")
    return {"ledger": ledger, "ledger_sha256": sha256(raw).hexdigest()}


def validate_reservation_scope(ledger_document, amount=RESERVATION_USD):
    ledger = ledger_document["ledger"]
    amount = float(amount)
    reserved, unreserved, cap = (float(ledger["reserved_usd"]),
                                 float(ledger["unreserved_usd"]), float(ledger["cap_usd"]))
    require(amount == float(RESERVATION_USD), "RESERVATION_AMOUNT_FROZEN")
    require(unreserved >= amount and reserved + amount <= cap,
            "RESERVATION_OUTSIDE_CAMPAIGN_BUDGET")
    return {"amount": amount, "reserved_before": reserved, "unreserved_before": unreserved,
            "campaign_cap": cap}


def validate_preflight(facts):
    frozen = plan.RESOURCE_PLAN
    require(type(facts) is dict, "PREFLIGHT_FACTS_REQUIRED")
    require(facts.get("account") == frozen["account"], "PREFLIGHT_ACCOUNT")
    require(facts.get("region") == frozen["region"], "PREFLIGHT_REGION")
    require(facts.get("ami") == frozen["ami"], "PREFLIGHT_AMI")
    require(facts.get("instance_type") == frozen["instance_type"], "PREFLIGHT_INSTANCE_TYPE")
    require(facts.get("instance_count") == 1, "PREFLIGHT_INSTANCE_COUNT")
    require(facts.get("gpu_name_contains") == frozen["gpu_name_contains"], "PREFLIGHT_GPU_NAME")
    require(facts.get("t4_rejected") is True, "PREFLIGHT_T4")
    require(facts.get("rate_ceiling_usd") == frozen["on_demand_rate_ceiling_usd"],
            "PREFLIGHT_RATE_CEILING")
    require(facts.get("conflicting_resources") in (None, [], {}), "PREFLIGHT_CONFLICTING_RESOURCES")
    return facts


def execute(request, authority, provider, *, ledger_path=LEDGER_PATH, now=None):
    """One-shot paid execution with injected provider; never retries."""
    validate_request(request)
    validate_authority(authority)
    require(authority["job"] == request["job"], "REQUEST_AUTHORITY_JOB_MISMATCH")
    require(authority["source_sha"] == request["source_sha"], "REQUEST_AUTHORITY_SOURCE_MISMATCH")
    for key in ("archive_sha256", "manifest_sha256", "dataset_manifest_sha256"):
        require(authority[key] == request[key], "REQUEST_AUTHORITY_HASH_MISMATCH:" + key)
    require(provider is not None, "PROVIDER_ADAPTER_REQUIRED")
    started = time.monotonic()
    ledger_before = read_ledger(ledger_path)
    reservation_scope = validate_reservation_scope(ledger_before)
    preflight = validate_preflight(provider.preflight())
    provider.calls.clear()
    reservation = provider.reserve(RESERVATION_USD)
    require(provider.calls == ["reserve"], "RESERVATION_MUST_BE_FIRST_AND_SINGLE")
    require(reservation.get("status") == "RESERVED_NO_AUTOMATIC_REFUND",
            "RESERVATION_STATUS_REQUIRED")
    ledger_after = read_ledger(ledger_path)
    require(ledger_after["ledger"]["reserved_usd"] != ledger_before["ledger"]["reserved_usd"],
            "LEDGER_NOT_UPDATED_AFTER_RESERVATION")
    permit = {"job": request["job"], "source_sha": request["source_sha"],
              "archive_sha256": request["archive_sha256"],
              "manifest_sha256": request["manifest_sha256"],
              "dataset_manifest_sha256": request["dataset_manifest_sha256"],
              "reservation": reservation, "preflight": preflight,
              "resource_plan": scope()}
    cleanup = None
    try:
        launch = provider.launch(request["job"], permit)
        outcome = provider.wait(request["job"], timeout=plan.RESOURCE_PLAN["instance_seconds_max"])
        collected = provider.collect(request["job"])
        status = "AWS_CONDITION_SKILL_V9_FINISHED" if outcome.get("worker_status") == "REMOTE_FINISHED" else "AWS_CONDITION_SKILL_V9_FAILED"
    except Exception as error:
        status = "AWS_CONDITION_SKILL_V9_LAUNCH_FAILED"
        outcome = {"exception_type": type(error).__name__, "exception": str(error)[:2000]}
        collected = None
    finally:
        cleanup = provider.cleanup(request["job"])
    result = {"schema": SCHEMA, "status": status, "job": request["job"],
              "request": request, "authority": authority,
              "ledger_before": ledger_before, "ledger_after": ledger_after,
              "reservation_scope": reservation_scope, "reservation": reservation,
              "preflight": preflight, "outcome": outcome, "collected": collected,
              "cleanup": cleanup, "elapsed_seconds": time.monotonic() - started,
              "claims": {"native_admission": False, "repair_proved": False,
                         "caller_return_proved": False, "composition_proved": False,
                         "cas_advantage_claimed": False}}
    require(cleanup.get("complete") is True, "CLEANUP_INCOMPLETE_BLOCKS_RESULT")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--request")
    parser.add_argument("--request-sha256")
    parser.add_argument("--authority")
    parser.add_argument("--authority-sha256")
    parser.add_argument("--receipt-dir")
    arguments = parser.parse_args(argv)
    if not arguments.execute:
        print(json.dumps(plan_only(), sort_keys=True))
        return 0
    require(all(getattr(arguments, name) for name in
               ("request", "request_sha256", "authority", "authority_sha256", "receipt_dir")),
            "EXPLICIT_REGISTERED_INPUTS_REQUIRED")
    request_raw = Path(arguments.request).read_bytes()
    authority_raw = Path(arguments.authority).read_bytes()
    require(digest(request_raw) == arguments.request_sha256, "REQUEST_HASH_MISMATCH")
    require(digest(authority_raw) == arguments.authority_sha256, "AUTHORITY_HASH_MISMATCH")
    request = json.loads(request_raw)
    authority = json.loads(authority_raw)
    from aws import condition_skill_v9_provider  # noqa: F401  (separate admitted adapter)
    provider = condition_skill_v9_provider.build(arguments)
    result = execute(request, authority, provider)
    receipt_dir = Path(arguments.receipt_dir)
    require(not receipt_dir.exists() and receipt_dir.parent.is_dir(),
            "FRESH_RECEIPT_DIRECTORY_REQUIRED")
    receipt_dir.mkdir()
    with (receipt_dir / "result.json").open("xb") as stream:
        stream.write(canonical(result))
    print(json.dumps({"status": result["status"], "receipt_dir": str(receipt_dir)}, sort_keys=True))
    return 0 if result["status"] == "AWS_CONDITION_SKILL_V9_FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
