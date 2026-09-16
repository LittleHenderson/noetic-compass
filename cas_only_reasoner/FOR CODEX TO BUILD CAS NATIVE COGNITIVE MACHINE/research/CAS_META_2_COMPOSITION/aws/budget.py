"""One continued $400 campaign budget; no refunds, resets, or silent retries.

All amounts are conservative reservations, not an AWS invoice. A reservation
must cover compute and all planned ancillary charges. The launcher must also
enforce its declared wall-clock deadline and resource limits.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LEDGER = ROOT / "records" / "budget" / "campaign_ledger.json"
#: The owner instruction that raised the operating cap above CAP_ORIGINAL.
CANONICAL_AMENDMENT = ROOT / "records" / "budget" / "OWNER_BUDGET_AMENDMENT_001.json"
#: What the owner's captured get_goal artifact approved. NEVER change this: it
#: describes a real piece of evidence, and the artifact still says $400.
CAP_ORIGINAL = Decimal("400.00")
#: The floor the owner set in the same breath as the raise: "NO LESS THAN $400".
CAP_FLOOR = Decimal("400.00")
#: The OPERATING cap. Raised from $400.00 to $5000.00 on 2026-09-12 by explicit
#: owner instruction, recorded verbatim in
#: records/budget/OWNER_BUDGET_AMENDMENT_001.json and hash-bound into the ledger
#: exactly like the predecessor and approval bindings.
#:
#: This is a MONEY-PATH EDIT and is meant to be conspicuous. It was made only
#: after the owner was shown, and acknowledged, that:
#:   * the cap is a self-imposed ceiling, not a bill;
#:   * the whole of 2026-09-12 cost $1.68 of real AWS charges;
#:   * the alternative was to supply a captured get_goal artifact, which is
#:     STRONGER evidence, and the owner chose this route knowingly.
#: The original approval is not replaced or weakened - it stays bound in the
#: ledger as it was, and the amendment sits beside it.
CAP = Decimal("5000.00")
STATUS = "RESERVED_NO_AUTOMATIC_REFUND"
SCHEMA = "cas-meta-campaign-budget/2"


class BudgetRefused(ValueError):
    """No paid resource may be created after this exception."""


def require(condition, reason):
    if not condition:
        raise BudgetRefused(reason)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def decoded(raw):
    try:
        return json.loads(raw, object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(BudgetRefused("NONFINITE_JSON")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BudgetRefused("MALFORMED_BUDGET_JSON") from exc


def amount(value, *, positive=False):
    require(type(value) is str and bool(re.fullmatch(r"\d+(?:\.\d{1,8})?", value)), "INVALID_USD_AMOUNT")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise BudgetRefused("INVALID_USD_AMOUNT") from exc
    require(result.is_finite() and result >= 0 and (not positive or result > 0), "INVALID_USD_AMOUNT")
    return result


def utc(value):
    try:
        result = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise BudgetRefused("INVALID_RESERVATION_TIME") from exc
    require(result.utcoffset() is not None and result.utcoffset().total_seconds() == 0, "UTC_TIME_REQUIRED")


def reservations_total(entries):
    require(type(entries) is list, "INVALID_RESERVATIONS")
    seen = set()
    total = Decimal(0)
    for entry in entries:
        require(type(entry) is dict, "INVALID_RESERVATION")
        require(type(entry.get("job")) is str and bool(re.fullmatch(r"cas-meta[0-9]+-[a-zA-Z0-9-]+", entry["job"])), "INVALID_JOB_ID")
        require(entry["job"] not in seen, "DUPLICATE_JOB_RESERVATION")
        seen.add(entry["job"])
        require(entry.get("status") == STATUS, "REFUNDS_OR_STATUS_MUTATIONS_FORBIDDEN")
        require(bool(re.fullmatch(r"[a-f0-9]{40}", entry.get("source_sha", ""))), "INVALID_SOURCE_SHA")
        require(bool(re.fullmatch(r"[a-f0-9]{64}", entry.get("archive_sha256", ""))), "INVALID_ARCHIVE_SHA")
        utc(entry.get("reserved_utc"))
        total += amount(entry.get("reserved_usd"), positive=True)
    return total


def validate_plan(plan, reserved_usd):
    require(type(plan) is dict, "RESOURCE_PLAN_REQUIRED")
    require(type(plan.get("instance_count")) is int and plan["instance_count"] == 1, "ONE_INSTANCE_ONLY")
    require(type(plan.get("runtime_seconds_max")) is int and 1 <= plan["runtime_seconds_max"] <= 43200, "BOUNDED_RUNTIME_REQUIRED")
    require(type(plan.get("instance_type")) is str and bool(re.fullmatch(r"(?:g6e?|g7e?|p4d|p4de|p5|p5e|p5en|p6)[.][a-z0-9]+", plan["instance_type"])), "NO_T4_OR_UNREGISTERED_GPU_FAMILY")
    require(plan.get("account_id") == "807562639912" and plan.get("region") == "us-west-2", "CAMPAIGN_AWS_IDENTITY_MISMATCH")
    require(plan.get("automatic_retries") == 0, "AUTOMATIC_RETRIES_FORBIDDEN")
    rate = amount(plan.get("on_demand_hourly_usd_max"), positive=True)
    ancillary = amount(plan.get("ancillary_reserved_usd"), positive=True)
    bound = rate * Decimal(plan["runtime_seconds_max"]) / Decimal(3600) + ancillary
    require(amount(reserved_usd, positive=True) >= bound, "RESERVATION_BELOW_DECLARED_COST_BOUND")
    return bound


def validate_predecessor(prior):
    require(type(prior) is dict and prior.get("schema_version") == 1 and prior.get("owner_task_cap_usd") == "100.00", "INVALID_PREDECESSOR_LEDGER")
    total = reservations_total(prior.get("reservations"))
    require(total <= Decimal(100), "PREDECESSOR_OVER_CAP")
    require(amount(prior.get("total_reserved_usd")) == total and amount(prior.get("remaining_unreserved_usd")) == Decimal(100) - total, "INCONSISTENT_PREDECESSOR_TOTALS")


def validate_approval(approval):
    require(type(approval) is dict and approval.get("schema") == "cas-meta2-owner-budget-approval/1", "OWNER_APPROVAL_REQUIRED")
    require(approval.get("evidence_kind") == "active_user_goal_returned_by_get_goal", "OWNER_GOAL_PROVENANCE_REQUIRED")
    goal = approval.get("goal", {})
    require(type(goal.get("objective")) is str and "AMENDENDED AWS SPENDING BUDGET IS $400" in goal["objective"], "EXPLICIT_400_DOLLAR_APPROVAL_REQUIRED")
    require(goal.get("threadId") == "01a065e4-1cc3-7a02-8fd6-8c2d00775ab4", "OWNER_TASK_IDENTITY_MISMATCH")
    require(type(goal.get("createdAt")) is int and type(goal.get("updatedAt")) is int, "OWNER_GOAL_TIME_REQUIRED")
    interpretation = approval.get("interpretation", {})
    require(interpretation.get("total_task_cap_usd") == "400.00" and all(interpretation.get(key) is True for key in ("includes_prior_spending_and_reservations", "includes_campaign_and_further_research", "no_t4", "all_neural_work_on_aws")), "INCLUSIVE_CAP_OR_GPU_RESTRICTION_MISSING")


def validate_amendment(amendment):
    """The owner instruction that raised the operating cap.

    Deliberately strict about what it is. ``evidence_kind`` must say
    ``owner_instruction_in_session`` - it is NOT a get_goal artifact, and a
    record claiming otherwise is refused, because the difference between the two
    is the whole reason the original approval is trustworthy.
    """
    require(type(amendment) is dict
            and amendment.get("schema") == "cas-meta2-owner-budget-amendment/1",
            "OWNER_AMENDMENT_REQUIRED")
    require(amendment.get("evidence_kind") == "owner_instruction_in_session",
            "OWNER_AMENDMENT_PROVENANCE_MUST_BE_HONEST")
    require(type(amendment.get("owner_instruction_raw")) is str
            and amendment["owner_instruction_raw"].strip(),
            "OWNER_AMENDMENT_VERBATIM_INSTRUCTION_REQUIRED")
    require(amendment.get("supersedes_cap_usd") == str(CAP_ORIGINAL),
            "OWNER_AMENDMENT_MUST_NAME_WHAT_IT_SUPERSEDES")
    require(amendment.get("total_task_cap_usd") == str(CAP),
            "OWNER_AMENDMENT_CAP_MISMATCH")
    require(amendment.get("cap_floor_usd") == str(CAP_FLOOR),
            "OWNER_AMENDMENT_FLOOR_MISMATCH")
    require(amount(amendment["total_task_cap_usd"]) >= CAP_FLOOR,
            "OWNER_AMENDMENT_BELOW_FLOOR")
    return amendment


def validate_state(state, expected_cap=None):
    """Validate ONE ledger state.

    ``expected_cap`` is the cap the state must carry, and it is passed only for
    the OPERATING HEAD. A history entry is validated against the cap it recorded
    for itself, because a state written before a cap raise legitimately carries
    the old cap.

    This was a real defect, not a hypothetical. The line read
    ``state.get("owner_task_cap_usd") == str(CAP)`` and was applied to every
    entry in the write-ahead history as well as to the head. When the owner
    raised the operating cap from $400.00 to $5000.00, the 70 existing history
    entries all still recorded "400.00", so read_locked refused the FIRST one
    with INVALID_CAMPAIGN_LEDGER and every paid launch stopped - the ledger was
    right and the validator was wrong. History is a record of what was
    authorised THEN, not of what is authorised now.
    """
    require(type(state) is dict and state.get("schema") == SCHEMA,
            "INVALID_CAMPAIGN_LEDGER")
    recorded = amount(state.get("owner_task_cap_usd"), positive=True)
    # Either the cap the get_goal artifact approved, or the amended operating
    # cap. Nothing else is a cap this campaign has ever operated under.
    require(recorded in (CAP_ORIGINAL, CAP), "INVALID_CAMPAIGN_LEDGER")
    require(recorded >= CAP_FLOOR, "OPERATING_CAP_BELOW_OWNER_FLOOR")
    if expected_cap is not None:
        require(recorded == expected_cap, "LEDGER_CAP_CHANGED")
    require(state.get("no_automatic_refund") is True, "REFUND_POLICY_MISSING")
    require(type(state.get("revision")) is int and state["revision"] >= 0, "INVALID_LEDGER_REVISION")
    for key in ("predecessor", "approval"):
        binding = state.get(key, {})
        require(type(binding.get("path")) is str and Path(binding["path"]).is_absolute(), "ABSOLUTE_EVIDENCE_PATH_REQUIRED")
        require(bool(re.fullmatch(r"[a-f0-9]{64}", binding.get("sha256", ""))), "INVALID_EVIDENCE_DIGEST")
        try:
            raw = Path(binding["path"]).read_bytes()
        except OSError as exc:
            raise BudgetRefused("REQUIRED_BUDGET_EVIDENCE_UNAVAILABLE") from exc
        require(digest(raw) == binding["sha256"], "PREDECESSOR_OR_APPROVAL_CHANGED")
        require(decoded(raw) == binding.get("snapshot"), "EVIDENCE_SNAPSHOT_MISMATCH")
    prior = state["predecessor"]["snapshot"]
    validate_predecessor(prior)
    validate_approval(state["approval"]["snapshot"])
    # A cap above what the get_goal artifact approved REQUIRES the amendment,
    # bound by hash and snapshot exactly like the other two. Without it the
    # ledger falls back to the approved $400 and refuses to operate above it.
    # Keyed on THIS state's recorded cap, not on the module constant: a state
    # written before the raise records the original cap and legitimately needs no
    # amendment, and demanding one of it would refuse the whole history.
    if recorded != CAP_ORIGINAL:
        binding = state.get("amendment", {})
        require(type(binding.get("path")) is str
                and Path(binding["path"]).is_absolute(),
                "ABSOLUTE_EVIDENCE_PATH_REQUIRED")
        require(bool(re.fullmatch(r"[a-f0-9]{64}", binding.get("sha256", ""))),
                "INVALID_EVIDENCE_DIGEST")
        try:
            raw = Path(binding["path"]).read_bytes()
        except OSError as exc:
            raise BudgetRefused("REQUIRED_BUDGET_EVIDENCE_UNAVAILABLE") from exc
        require(digest(raw) == binding["sha256"], "AMENDMENT_CHANGED")
        require(decoded(raw) == binding.get("snapshot"),
                "EVIDENCE_SNAPSHOT_MISMATCH")
        validate_amendment(binding["snapshot"])
    entries = state.get("reservations")
    total = reservations_total(entries)
    original = prior["reservations"]
    require(entries[:len(original)] == original, "PRIOR_RESERVATIONS_MUST_BE_PRESERVED_EXACTLY")
    require(len(entries) == len(original) + state["revision"], "RESERVATION_REVISION_MISMATCH")
    for entry in entries[len(original):]:
        require(entry.get("plan_sha256") == digest(encoded(entry.get("plan"))), "RESOURCE_PLAN_DIGEST_MISMATCH")
        validate_plan(entry.get("plan"), entry["reserved_usd"])
    require(total <= recorded, "CAMPAIGN_BUDGET_EXHAUSTED")
    # Free space is DERIVED: it must equal THIS state's cap minus what it had
    # reserved. Keyed on the recorded cap for the same reason as above - a
    # pre-raise state with $400.00 of cap and $396.00 reserved is internally
    # consistent at $4.00 free, and comparing it against today's cap would call
    # a correct historical record inconsistent.
    require(amount(state.get("total_reserved_usd")) == total
            and amount(state.get("remaining_unreserved_usd")) == recorded - total,
            "INCONSISTENT_CAMPAIGN_TOTALS")
    return state


def paths(ledger_path):
    ledger = Path(ledger_path).resolve()
    return ledger, ledger.with_suffix(ledger.suffix + ".lock"), ledger.with_suffix(ledger.suffix + ".history")


@contextmanager
def exclusive(ledger_path):
    ledger, lock_path, history = paths(ledger_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    try:
        lock = lock_path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise BudgetRefused("CAMPAIGN_LEDGER_LOCKED_FAIL_CLOSED") from exc
    try:
        with lock:
            lock.write(json.dumps({"token": token, "pid": os.getpid()}))
            lock.flush()
            os.fsync(lock.fileno())
        yield ledger, history
    finally:
        # Never delete another process's lock or silently clear a stale lock.
        require(decoded(lock_path.read_bytes()).get("token") == token, "LOCK_OWNERSHIP_CHANGED")
        deadline = time.monotonic() + 2
        while True:
            try:
                lock_path.unlink()
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise BudgetRefused("WINDOWS_LOCK_RELEASE_FAILED_CLOSED")
                time.sleep(0.05)


def replace_atomic(temporary, ledger):
    deadline = time.monotonic() + 2
    while True:
        try:
            os.replace(temporary, ledger)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise BudgetRefused("WINDOWS_LEDGER_REPLACEMENT_FAILED_CLOSED")
            time.sleep(0.05)


def read_locked(ledger, history):
    require(ledger.is_file() and history.is_dir(), "CAMPAIGN_LEDGER_NOT_INITIALIZED")
    # The HEAD is the state money is spent from, so it must carry the OPERATING
    # cap. History entries below are validated against their own recorded cap.
    state = validate_state(decoded(ledger.read_bytes()), expected_cap=CAP)
    records = sorted(history.iterdir())
    require([item.name for item in records] == [f"{n:08d}.json" for n in range(state["revision"] + 1)], "PENDING_OR_MISSING_BUDGET_HISTORY_FAIL_CLOSED")
    previous = None
    for revision, item in enumerate(records):
        raw = item.read_bytes()
        entry = validate_state(decoded(raw))
        require(entry["revision"] == revision, "HISTORY_REVISION_MISMATCH")
        require(entry.get("previous_state_sha256") == (digest(encoded(previous)) if previous is not None else None), "BROKEN_BUDGET_HISTORY_CHAIN")
        if previous is not None:
            require(entry["reservations"][:-1] == previous["reservations"] and entry["predecessor"] == previous["predecessor"] and entry["approval"] == previous["approval"], "BUDGET_HISTORY_NOT_APPEND_ONLY")
        previous = entry
    # reserve_budget hashes the complete head for the next history link. The
    # head must therefore equal the complete history tail before any write,
    # including authorization and metadata. Otherwise a head-only amendment
    # passes this read, consumes a reservation, then breaks the history chain.
    # A future cap amendment needs an explicit migration/event design; accepting
    # an unmatched head here does not provide one.
    require(previous == state, "LEDGER_HISTORY_MISMATCH")
    return state


def publish(state, ledger, history):
    validate_state(state)
    history.mkdir(exist_ok=True)
    # Persist a write-ahead state first. An interrupted ledger replacement leaves
    # an unmatched history record, which blocks every subsequent paid launch.
    raw = encoded(state)
    with (history / f'{state["revision"]:08d}.json').open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=ledger.parent, prefix=".campaign-budget-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        replace_atomic(temporary, ledger)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return read_locked(ledger, history)


def initialize_ledger(predecessor_path, approval_path, ledger_path=CANONICAL_LEDGER, amendment_path=CANONICAL_AMENDMENT):
    """Bind, preserve and continue the original ledger; never create a fresh cap."""
    with exclusive(ledger_path) as (ledger, history):
        if ledger.exists() or history.exists():
            state = read_locked(ledger, history)
            require(state["predecessor"]["path"] == str(Path(predecessor_path).resolve()) and state["approval"]["path"] == str(Path(approval_path).resolve()), "LEDGER_REINITIALIZATION_SOURCE_MISMATCH")
            return state
        bindings = {}
        for key, path in (("predecessor", predecessor_path), ("approval", approval_path)):
            path = Path(path).resolve()
            raw = path.read_bytes()
            bindings[key] = {"path": str(path), "sha256": digest(raw), "snapshot": decoded(raw)}
        if CAP != CAP_ORIGINAL:
            # An operating cap above what the get_goal artifact approved cannot
            # exist without the amendment bound beside it.
            path = Path(amendment_path).resolve()
            raw = path.read_bytes()
            bindings["amendment"] = {"path": str(path), "sha256": digest(raw),
                                     "snapshot": decoded(raw)}
            validate_amendment(bindings["amendment"]["snapshot"])
        validate_predecessor(bindings["predecessor"]["snapshot"])
        validate_approval(bindings["approval"]["snapshot"])
        entries = bindings["predecessor"]["snapshot"]["reservations"]
        total = reservations_total(entries)
        state = {"schema": SCHEMA, "owner_task_cap_usd": str(CAP), "scope": "All CASformer campaign and further research, inclusive of prior META1 reservations", "no_automatic_refund": True, "revision": 0, "previous_state_sha256": None, **bindings, "reservations": entries, "total_reserved_usd": str(total), "remaining_unreserved_usd": str(CAP - total), "updated_utc": datetime.now(timezone.utc).isoformat()}
        return publish(state, ledger, history)


def read_ledger(ledger_path=CANONICAL_LEDGER):
    with exclusive(ledger_path) as (ledger, history):
        return read_locked(ledger, history)


def reserve_budget(job, source_sha, archive_sha256, reserved_usd, plan, ledger_path=CANONICAL_LEDGER):
    """Reserve once before provider mutations. Duplicate job IDs are refused."""
    validate_plan(plan, reserved_usd)
    with exclusive(ledger_path) as (ledger, history):
        state = read_locked(ledger, history)
        require(not any(entry["job"] == job for entry in state["reservations"]), "JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY")
        previous_hash = digest(encoded(state))
        entry = {"job": job, "source_sha": source_sha, "archive_sha256": archive_sha256, "reserved_usd": reserved_usd, "reserved_utc": datetime.now(timezone.utc).isoformat(), "status": STATUS, "plan": decoded(encoded(plan)), "plan_sha256": digest(encoded(plan))}
        total = reservations_total(state["reservations"] + [entry])
        require(total <= CAP, "CAMPAIGN_BUDGET_EXHAUSTED")
        state.update(revision=state["revision"] + 1, previous_state_sha256=previous_hash, reservations=state["reservations"] + [entry], total_reserved_usd=str(total), remaining_unreserved_usd=str(CAP - total), updated_utc=datetime.now(timezone.utc).isoformat())
        publish(state, ledger, history)
        return {"reservation": entry, "ledger_path": str(ledger), "ledger_sha256": digest(ledger.read_bytes()), "revision": state["revision"], "total_reserved_usd": state["total_reserved_usd"], "remaining_unreserved_usd": state["remaining_unreserved_usd"]}
