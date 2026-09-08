"""Pure, inert admission contract for continuing the exact incomplete job003.

The new cloud job has its own reservation and shutdown schedule. Its worker
keeps the original logical run ID, frozen source, material and 16-epoch profile.
This module performs no file, provider, ledger or neural operations. External
callers must verify all supplied digests against actual files and current facts.
"""
from copy import deepcopy
from decimal import Decimal
import re

from . import teaching_cycle_plan as base

SCHEMA = "cas-teaching-continuation-resource-plan/1"
REQUEST_SCHEMA = "cas-teaching-continuation-launch-request/1"
TASK_SCOPE = "teaching_cycle_v2_four_arm_binding_continuation"
JOB_PATTERN = base.JOB_PATTERN  # The bucket suffix still fits S3's 63-char bound.
LOGICAL_RUN_ID = "cas-meta2-teaching-20260908052915-8b5df59c"
ORIGINAL_CAMPAIGN_ROOT = "/opt/cas-teaching/job/train/campaign"
RESERVATION_USD = "8.00"
PRIOR_ARCHIVE_BYTES_MAX = 512 * 1024**2
PRIOR_EXPANDED_BYTES_MAX = 1024**3
ORIGINAL_AUTHORITY_SHA256 = "bc80b6e645b339a2b2ffd7ae1ddad0d9c970fb00dd142b37c2a3f9697828049d"
BINDING_FIELDS = base.BINDING_FIELDS
FROZEN_BINDINGS = {**base.FROZEN_BINDINGS,
    "material_receipt_sha256": "32cfb9183d389a880df49bf35dbda518cfcf277ddaf704d42abb169f9704a256",
    "public_sets_sha256": "6f04fb7452cf9f7bb9bd89750f4d5e858f927f1426973729a9c320bdeb356e67",
    "scorer_sha256": "5bc828a258d97314df66e040f4a8d62429f040356d8ac09af060b5c0fec6b455"}
FROZEN_PROFILE = {"version": 2, "batch_size": 32, "seed": 7,
    "training_cases_count": 256, "development_cases_count": 64,
    "allocation": {"minimum_full_cycles": 1024, "maximum_cycles": 4096,
        "development_interval": 256, "consistent_checks": 3,
        "readiness_accuracy": 0.9, "minimum_unique_families": 256,
        "minimum_cycles_per_family": 4, "development_cases_count": 64}}
CONTINUATION_DIGEST_FIELDS = frozenset({"prior_state_archive_sha256", "prior_state_manifest_sha256",
    "prior_package_receipt_sha256", "prior_summary_sha256", "prior_inspection_sha256",
    "prior_parent_result_sha256", "prior_complete_sha256", "prior_cleanup_sha256",
    "prior_result_archive_sha256", "prior_package_validator_sha256", "base_guest_driver_sha256",
    "restore_probe_sha256", "continuation_plan_sha256", "profile_sha256"})
CONTINUATION_FIELDS = CONTINUATION_DIGEST_FIELDS | {
    "prior_state_archive_bytes", "prior_state_expanded_bytes", "original_campaign_root"}
canonical_sha256 = base.canonical_sha256
FROZEN_CONTINUATION = {
    "prior_summary_sha256": "26b23bb5f23ca875375797db155e8520b947bf0b4eada71e596a9ec7493e195f",
    "prior_inspection_sha256": "a47ced1ca072041306f8e4a47f2efb03ec97d5690659b14ab19cd0e19141ef6d",
    "prior_parent_result_sha256": "c12347f65d38dc883221b9f9ddb48099574c851acc858d6d6444a0eaa2295b76",
    "prior_complete_sha256": "72e855be29eef920df8cf4089b6f81347a9b709a952e7f6d9aff44208e7d97a7",
    "prior_cleanup_sha256": "9a1516b871820125bc914bef3c8fef899b532b49e56b80e641067f880a895500",
    "prior_result_archive_sha256": "73a1e22bdf011380527d78fd72f2a343bfffa1d302eedffc57b0f5417aa361e9",
    "base_guest_driver_sha256": "14a09d391435ffc354343f64ede83a079540000694dbd273bc55bedd13928a2e",
    "profile_sha256": canonical_sha256(FROZEN_PROFILE),
}
_RESOURCE_PLAN = base.resource_plan()
_RESOURCE_PLAN.update({"schema": SCHEMA, "task_scope": TASK_SCOPE,
    "restore_probe_seconds_max": 180, "restore_probe_process_count_max": 1,
    "prior_state_archive_bytes_max": PRIOR_ARCHIVE_BYTES_MAX,
    "prior_state_expanded_bytes_max": PRIOR_EXPANDED_BYTES_MAX,
    "prior_state_expanded_bound_includes_manifest": True,
    "prior_input_limits_are_additional_to_output_limit": True,
    "artifact_limit_includes_retained_history": True,
    "same_frozen_worker_and_profile_required": True,
    "new_cloud_job_original_logical_run_required": True,
    "restore_verified_before_training": True,
    "prior_uncommitted_tail_rejected": True,
    "reuses_original_reservation": False})
_RESOURCE_PLAN["worksheet_limits"]["s3_storage_decimal_gb_months_max"] = "6.00"


class PlanError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise PlanError("TEACHING_CONTINUATION_PLAN:" + reason)


def resource_plan():
    return deepcopy(_RESOURCE_PLAN)


def validate_resource_plan(plan):
    require(type(plan) is dict and canonical_sha256(plan) == canonical_sha256(_RESOURCE_PLAN),
            "RESOURCE_SCOPE_CHANGED")
    return plan


def validate_bindings(bindings):
    try:
        base.validate_bindings(bindings)
    except base.PlanError as error:
        raise PlanError(str(error)) from error
    require(all(bindings[key] == value for key, value in FROZEN_BINDINGS.items()),
            "FROZEN_WORKER_MATERIAL_OR_SCORER_CHANGED")
    require(bindings["authority_sha256"] != ORIGINAL_AUTHORITY_SHA256,
            "CONSUMED_ORIGINAL_AUTHORITY_REJECTED")
    return bindings


def validate_continuation(continuation):
    require(type(continuation) is dict and set(continuation) == CONTINUATION_FIELDS,
            "EXACT_CONTINUATION_BINDINGS_REQUIRED")
    for key in CONTINUATION_DIGEST_FIELDS:
        value = continuation[key]
        require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None
                and value != "0" * 64, "CONTINUATION_DIGEST_INVALID:" + key)
    require(all(continuation[key] == value for key, value in FROZEN_CONTINUATION.items()),
            "ORIGINAL_JOB003_EVIDENCE_OR_PROFILE_CHANGED")
    require(continuation["original_campaign_root"] == ORIGINAL_CAMPAIGN_ROOT,
            "ORIGINAL_CAMPAIGN_PATH_REQUIRED")
    for key, maximum in (("prior_state_archive_bytes", PRIOR_ARCHIVE_BYTES_MAX),
                         ("prior_state_expanded_bytes", PRIOR_EXPANDED_BYTES_MAX)):
        # Expanded size is ALL ZIP members, including raw manifest.json bytes.
        require(type(continuation[key]) is int and 0 < continuation[key] <= maximum,
                "PRIOR_STATE_BYTE_BOUND:" + key)
    return continuation


def validate_ledger_snapshot(ledger):
    try:
        return base.validate_ledger_snapshot(ledger)
    except base.PlanError as error:
        raise PlanError(str(error)) from error


def build_request(*, job, logical_run_id, bindings, continuation, ledger):
    plan = resource_plan()
    request = {"schema": REQUEST_SCHEMA, "task_scope": TASK_SCOPE, "job": job,
        "logical_run_id": logical_run_id, "bindings": deepcopy(bindings),
        "continuation": deepcopy(continuation), "ledger": deepcopy(ledger),
        "resource_plan": plan, "resource_plan_sha256": canonical_sha256(plan),
        "reservation_usd": RESERVATION_USD, "automatic_retries": 0,
        "launch_authorized": False, "new_reservation": False,
        "reuses_v9_one_shot_authorization": False, "reuses_original_reservation": False}
    return validate_request(request, expected_bindings=bindings,
                            expected_continuation=continuation, expected_ledger=ledger)


def validate_request(request, *, expected_bindings, expected_continuation, expected_ledger):
    validate_bindings(expected_bindings)
    validate_continuation(expected_continuation)
    validate_ledger_snapshot(expected_ledger)
    require(type(request) is dict and set(request) == {"schema", "task_scope", "job", "logical_run_id",
        "bindings", "continuation", "ledger", "resource_plan", "resource_plan_sha256", "reservation_usd",
        "automatic_retries", "launch_authorized", "new_reservation", "reuses_v9_one_shot_authorization",
        "reuses_original_reservation"}, "REQUEST_FIELDS_INVALID")
    require(request["schema"] == REQUEST_SCHEMA and request["task_scope"] == TASK_SCOPE,
            "CONTINUATION_SCOPE_REQUIRED")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]) is not None
            and request["job"] != LOGICAL_RUN_ID, "FRESH_CLOUD_JOB_REQUIRED")
    require(request["logical_run_id"] == LOGICAL_RUN_ID, "ORIGINAL_LOGICAL_RUN_REQUIRED")
    validate_bindings(request["bindings"])
    validate_continuation(request["continuation"])
    validate_ledger_snapshot(request["ledger"])
    for key, expected in (("bindings", expected_bindings), ("continuation", expected_continuation),
                          ("ledger", expected_ledger)):
        require(canonical_sha256(request[key]) == canonical_sha256(expected), "EXTERNAL_IDENTITY_MISMATCH:" + key)
    validate_resource_plan(request["resource_plan"])
    require(request["resource_plan_sha256"] == canonical_sha256(request["resource_plan"]),
            "RESOURCE_PLAN_DIGEST_MISMATCH")
    require(request["reservation_usd"] == RESERVATION_USD, "RESERVATION_CEILING_CHANGED")
    require(type(request["automatic_retries"]) is int and request["automatic_retries"] == 0,
            "NO_RETRIES_REQUIRED")
    require(all(request[key] is False for key in ("launch_authorized", "new_reservation",
            "reuses_v9_one_shot_authorization", "reuses_original_reservation")), "REQUEST_MUST_REMAIN_INERT")
    return request


def worksheet(prices):
    """Fresh raw-price calculation; no quote, free tier, credit or bill invented."""
    from .teaching_cycle_preflight import PRICE_QUERIES, highest_rate
    rates = {name: highest_rate(prices[name], query[2]) for name, query in PRICE_QUERIES.items()}
    require(rates["compute"] <= Decimal("2.52"), "COMPUTE_RATE_ABOVE_CEILING")
    costs = {"compute_7200_seconds": rates["compute"] * 2,
        "ebs_75_gib_7200_seconds": rates["ebs"] * 75 * 2 / (28 * 24),
        "one_ipv4_7200_seconds": rates["ipv4"] * 2,
        "s3_6gb_full_month_conservative": rates["s3_storage"] * 6,
        "s3_2048_calls_highest_tier": max(rates["s3_put"], rates["s3_get"]) * 2048,
        "internet_egress_3gb": rates["egress"] * 3,
        "other_allowance": Decimal("1.00")}
    total = sum(costs.values())
    require(total <= Decimal(RESERVATION_USD), "TOTAL_ABOVE_RESERVATION")
    return {"rates_usd": {key: str(value) for key, value in rates.items()},
        "cost_components_usd": {key: str(value) for key, value in costs.items()},
        "estimated_bound_usd": str(total), "reservation_usd": RESERVATION_USD,
        "remaining_buffer_usd": str(Decimal(RESERVATION_USD) - total),
        "is_invoice": False, "free_tier_or_credit_assumed": False,
        "conditions": ["One instance and IPv4 address; 7200 seconds shared by setup, restore, training, prediction and collection.",
            "One restore probe <=180s, training <=4800s, and two predictions <=300s each; no retries.",
            "75 GiB gp3 at included 3000 IOPS / 125 MiB/s, deleted with instance.",
            "At most 2048 shared S3 attempts, including helper requests, failures and polls.",
            "Prior input ZIP <=512MiB and all prior unpacked members <=1GiB; output archive <=2.5GiB includes retained history.",
            "Prior input, source, result and control objects together <6 decimal GB; outbound result/control bytes <3 decimal GB.",
            "Same-region S3, no NAT gateway, snapshots or extra volumes; seven-day expiration costed for a full month.",
            "Actual fees, taxes, resource failures and timing must be reconciled afterward."]}
