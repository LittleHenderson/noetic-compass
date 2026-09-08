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
import os
from pathlib import Path
import re
import time
from hashlib import sha256

from aws import condition_skill_v9_resource_plan as plan
from aws import budget

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cas-meta2-condition-skill-v9-launch/9"
AUTHORITY_SCHEMA = "cas-meta2-condition-skill-v9-authority/9"
LEDGER_PATH = ROOT / "records/budget/campaign_ledger.json"
OWNER_APPROVAL_PATH = ROOT / "records/condition_skill_v9_001/OWNER_PHASE_APPROVAL.json"
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


def evidence_directory(path):
    """Reject linked ancestors before writing durable task-local evidence."""
    path = Path(path).absolute()
    require(".." not in path.parts, "EVIDENCE_PATH_PARENT_COMPONENT")
    for ancestor in (path, *path.parents):
        require(not ancestor.is_symlink() and not getattr(ancestor, "is_junction", lambda: False)(),
                "EVIDENCE_LINKED_PATH")
    return path


def write_evidence(path, raw):
    """Create once, flush to disk, and read back the exact bytes before return."""
    path = evidence_directory(path)
    require(type(raw) is bytes and len(raw) <= 256 * 1024**2,
            "EVIDENCE_BYTES_BOUND")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.stat().st_nlink == 1 and path.read_bytes() == raw,
            "EVIDENCE_READBACK_MISMATCH")
    return {"path": str(path), "sha256": digest(raw), "bytes": len(raw)}


def prepare_evidence(path):
    path = evidence_directory(path)
    require(not path.exists() and path.parent.is_dir(),
            "FRESH_RECEIPT_DIRECTORY_REQUIRED")
    path.mkdir()
    return path


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
    """Read a validated canonical snapshot without creating a lock or reservation.

    This is a preflight observation, not the spending transaction. The real
    reservation must still use budget.reserve_budget(), which locks and checks
    the full append-only history again. Never translate a fabricated short
    ledger into campaign authority.
    """
    path = Path(path)
    raw = path.read_bytes()
    ledger = budget.validate_state(budget.decoded(raw))
    return {"ledger": ledger, "ledger_sha256": sha256(raw).hexdigest(),
            "ledger_path": str(path.resolve())}


def reservation_plan():
    """Exact task/resource binding for the canonical budget helper."""
    frozen = json.loads(canonical(scope()))
    return {"instance_count": frozen["instance_count"],
            "runtime_seconds_max": frozen["instance_seconds_max"],
            "instance_type": frozen["instance_type"], "account_id": frozen["account"],
            "region": frozen["region"], "automatic_retries": frozen["automatic_retries"],
            "on_demand_hourly_usd_max": frozen["on_demand_rate_ceiling_usd"],
            "ancillary_reserved_usd": "1.48", "task_scope": "condition_skill_v9",
            "campaign_scope": "cas-meta2-composition-campaign", "condition_skill_v9": frozen}


def validate_reservation_scope(ledger_document, amount=RESERVATION_USD):
    ledger = ledger_document["ledger"]
    amount = budget.amount(amount, positive=True)
    reserved, unreserved, cap = (budget.amount(ledger["total_reserved_usd"]),
                                 budget.amount(ledger["remaining_unreserved_usd"]),
                                 budget.amount(ledger["owner_task_cap_usd"]))
    require(cap == budget.amount(CAMPAIGN_CAP_USD), "LEDGER_CAP_CHANGED")
    require(reserved + unreserved == cap, "INCONSISTENT_CAMPAIGN_TOTALS")
    require(amount == budget.amount(RESERVATION_USD), "RESERVATION_AMOUNT_FROZEN")
    require(unreserved >= amount and reserved + amount <= cap,
            "RESERVATION_OUTSIDE_CAMPAIGN_BUDGET")
    return {"amount": str(amount), "reserved_before": str(reserved),
            "unreserved_before": str(unreserved), "campaign_cap": str(cap)}


def validate_reserved_transition(before, after, receipt, request):
    """Bind the canonical helper receipt to exactly one new $4 reservation."""
    prior, current = before["ledger"], after["ledger"]
    require(current["revision"] == prior["revision"] + 1,
            "RESERVATION_REVISION_MISMATCH")
    require(current["reservations"][:-1] == prior["reservations"],
            "RESERVATION_NOT_APPEND_ONLY")
    require(current["previous_state_sha256"] == budget.digest(budget.encoded(prior)),
            "RESERVATION_PREDECESSOR_MISMATCH")
    for key in ("approval", "predecessor", "owner_task_cap_usd", "scope", "no_automatic_refund"):
        require(current.get(key) == prior.get(key), "RESERVATION_CONTEXT_CHANGED:" + key)
    entry = current["reservations"][-1]
    for key in ("job", "source_sha", "archive_sha256"):
        require(entry[key] == request[key], "RESERVATION_IDENTITY_MISMATCH:" + key)
    require(entry["status"] == budget.STATUS, "RESERVATION_STATUS_REQUIRED")
    require(entry["plan"] == reservation_plan() and
            entry["plan_sha256"] == budget.digest(budget.encoded(reservation_plan())),
            "RESERVATION_RESOURCE_PLAN_MISMATCH")
    amount = budget.amount(RESERVATION_USD)
    require(budget.amount(entry["reserved_usd"]) == amount,
            "RESERVATION_AMOUNT_FROZEN")
    require(budget.amount(current["total_reserved_usd"]) ==
            budget.amount(prior["total_reserved_usd"]) + amount and
            budget.amount(current["remaining_unreserved_usd"]) ==
            budget.amount(prior["remaining_unreserved_usd"]) - amount,
            "RESERVATION_TOTAL_DELTA_MISMATCH")
    require(type(receipt) is dict and receipt.get("reservation") == entry,
            "RESERVATION_RECEIPT_ENTRY_MISMATCH")
    require(receipt.get("ledger_sha256") == after["ledger_sha256"],
            "RESERVATION_RECEIPT_HASH_MISMATCH")
    require(receipt.get("ledger_path") == after["ledger_path"] == before["ledger_path"],
            "RESERVATION_RECEIPT_PATH_MISMATCH")
    for key in ("revision", "total_reserved_usd", "remaining_unreserved_usd"):
        require(receipt.get(key) == current[key], "RESERVATION_RECEIPT_FIELD:" + key)
    return receipt


def validate_preflight(facts):
    """Pre-launch AWS-visible identity facts only.

    torch_version, cuda_version, and actual_cuda_operation are worker-side
    facts that cannot exist before launch; they are collected by the provider
    into the outer receipt and enforced by the adjudicator's provider
    attestation after the run, never before the reservation.
    """
    frozen = plan.RESOURCE_PLAN
    require(type(facts) is dict, "PREFLIGHT_FACTS_REQUIRED")
    require(facts.get("account") == frozen["account"], "PREFLIGHT_ACCOUNT")
    require(facts.get("region") == frozen["region"], "PREFLIGHT_REGION")
    require(facts.get("ami") == frozen["ami"], "PREFLIGHT_AMI")
    require(facts.get("instance_type") == frozen["instance_type"], "PREFLIGHT_INSTANCE_TYPE")
    require(facts.get("instance_count") == 1, "PREFLIGHT_INSTANCE_COUNT")
    require(facts.get("gpu_name_contains") == frozen["gpu_name_contains"], "PREFLIGHT_GPU_NAME")
    require(facts.get("visible_gpu_count") == 1, "PREFLIGHT_VISIBLE_GPU_COUNT")
    require(facts.get("t4_rejected") is True, "PREFLIGHT_T4")
    require(facts.get("rate_ceiling_usd") == frozen["on_demand_rate_ceiling_usd"],
            "PREFLIGHT_RATE_CEILING")
    require(facts.get("conflicting_resources") in (None, [], {}), "PREFLIGHT_CONFLICTING_RESOURCES")
    return facts


def execute(request, authority, provider, *, ledger_path=LEDGER_PATH, now=None,
            receipt_dir=None):
    """One-shot paid execution with injected provider; never retries.

    The provider.calls list is advisory instrumentation for tests; the
    authoritative exactly-once guard is the canonical ledger transition
    (validate_reserved_transition) plus the job-in-ledger refusal.
    """
    validate_request(request)
    validate_authority(authority)
    require(authority["owner_approval_record_sha256"] ==
            digest(OWNER_APPROVAL_PATH.read_bytes()), "OWNER_APPROVAL_RECORD_MISMATCH")
    require(authority["job"] == request["job"], "REQUEST_AUTHORITY_JOB_MISMATCH")
    require(authority["source_sha"] == request["source_sha"], "REQUEST_AUTHORITY_SOURCE_MISMATCH")
    for key in ("archive_sha256", "manifest_sha256", "dataset_manifest_sha256"):
        require(authority[key] == request[key], "REQUEST_AUTHORITY_HASH_MISMATCH:" + key)
    require(provider is not None, "PROVIDER_ADAPTER_REQUIRED")
    started = time.monotonic()
    ledger_before = read_ledger(ledger_path)
    reservation_scope = validate_reservation_scope(ledger_before)
    require(not any(entry["job"] == request["job"] for entry in
                    ledger_before["ledger"]["reservations"]),
            "JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY")
    # Establish the evidence sink before reservation or any provider mutation.
    # This is a transport correction, not a change to the frozen experiment.
    directory = prepare_evidence(receipt_dir if receipt_dir is not None else
        Path(ledger_path).parent / ("condition_skill_v9_" + request["job"]))
    write_evidence(directory / "intent.json", canonical({
        "schema": SCHEMA, "request": request, "authority": authority,
        "ledger_before": ledger_before, "automatic_retries": 0}))
    provider.configure_evidence(directory)
    try:
        preflight = validate_preflight(provider.preflight())
    except Exception as error:
        write_evidence(directory / "failure.json", canonical({"stage": "preflight",
            "exception_type": type(error).__name__, "exception": str(error)[:2000]}))
        raise
    write_evidence(directory / "preflight.json", canonical(preflight))
    provider.calls.clear()
    reservation, ledger_after, launched, collected = None, None, None, None
    reservation_valid, reservation_error = False, None
    try:
        reservation = provider.reserve(RESERVATION_USD)
        require(provider.calls == ["reserve"], "RESERVATION_MUST_BE_FIRST_AND_SINGLE")
        ledger_after = read_ledger(ledger_path)
        validate_reserved_transition(ledger_before, ledger_after, reservation, request)
        require(reservation.get("aws_side_reservation", {}).get("status") == "RECORDED",
                "AWS_RESERVATION_RECORD_REQUIRED")
        write_evidence(directory / "reservation.json", canonical(reservation))
        reservation_valid = True
        permit = {"job": request["job"], "source_sha": request["source_sha"],
                  "archive_sha256": request["archive_sha256"],
                  "manifest_sha256": request["manifest_sha256"],
                  "dataset_manifest_sha256": request["dataset_manifest_sha256"],
                  "reservation": reservation, "preflight": preflight,
                  "resource_plan": scope()}
        launched = provider.launch(request["job"], permit)
        write_evidence(directory / "launch.json", canonical(launched))
        outcome = provider.wait(request["job"], timeout=plan.RESOURCE_PLAN["instance_seconds_max"])
        collected = provider.collect(request["job"])
        status = "AWS_CONDITION_SKILL_V9_FINISHED" if outcome.get("worker_status") == "REMOTE_FINISHED" else "AWS_CONDITION_SKILL_V9_FAILED"
    except BaseException as error:
        status = "AWS_CONDITION_SKILL_V9_LAUNCH_FAILED"
        outcome = {"exception_type": type(error).__name__, "exception": str(error)[:2000]}
        if not reservation_valid:
            reservation_error = error
        # An independent immutable record survives even a later cleanup error.
        try:
            write_evidence(directory / "failure.json", canonical(outcome))
        except Exception as record_error:
            outcome["failure_record_error"] = type(record_error).__name__ + ":" + str(record_error)[:1000]
    finally:
        try:
            cleanup = provider.cleanup(request["job"])
        except BaseException as error:
            cleanup = {"complete": False, "failures": [
                "CLEANUP_EXCEPTION:" + type(error).__name__ + ":" + str(error)[:2000]]}
    result = {"schema": SCHEMA, "status": status, "job": request["job"],
              "request": request, "authority": authority,
              "ledger_before": ledger_before, "ledger_after": ledger_after,
              "reservation_scope": reservation_scope, "reservation": reservation,
              "preflight": preflight, "launch": launched, "outcome": outcome,
              "collected": collected, "receipt_dir": str(directory),
              "cleanup": cleanup, "elapsed_seconds": time.monotonic() - started,
              "claims": {"native_admission": False, "repair_proved": False,
                         "caller_return_proved": False, "composition_proved": False,
                         "cas_advantage_claimed": False}}
    # Evidence on every exit: an incomplete cleanup fails the result but is
    # recorded, never raised away — raising here previously destroyed the
    # launch outcome and cleanup details entirely.
    if not cleanup.get("complete"):
        result["status"] = "AWS_CONDITION_SKILL_V9_FAILED"
        result["cleanup_incomplete_reason"] = cleanup.get("failures")
    write_evidence(directory / "result.json", canonical(result))
    if reservation_error is not None:
        raise reservation_error
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--request")
    parser.add_argument("--request-sha256")
    parser.add_argument("--authority")
    parser.add_argument("--authority-sha256")
    parser.add_argument("--receipt-dir")
    parser.add_argument("--profile", default="default")
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
    result = execute(request, authority, provider, receipt_dir=arguments.receipt_dir)
    print(json.dumps({"status": result["status"], "receipt_dir": result["receipt_dir"]}, sort_keys=True))
    return 0 if result["status"] == "AWS_CONDITION_SKILL_V9_FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
