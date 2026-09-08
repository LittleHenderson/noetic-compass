"""Pure, inert admission contract for continuing the exact incomplete first continuation.

The new cloud job has its own reservation and shutdown schedule. Its worker
keeps the original logical run ID, frozen source, material and 16-epoch profile.
This module performs no file, provider, ledger or neural operations. External
callers must verify all supplied digests against actual files and current facts.
"""
from copy import deepcopy
from decimal import Decimal
import re

from . import teaching_cycle_plan as base

SCHEMA = "cas-teaching-continuation-resource-plan/2"
REQUEST_SCHEMA = "cas-teaching-continuation-launch-request/2"
TASK_SCOPE = "teaching_cycle_v2_four_arm_binding_continuation_002"
JOB_PATTERN = base.JOB_PATTERN  # The bucket suffix still fits S3's 63-char bound.
LOGICAL_RUN_ID = "cas-meta2-teaching-20260908052915-8b5df59c"
ORIGINAL_CAMPAIGN_ROOT = "/opt/cas-teaching/job/train/campaign"
RESUME_SUMMARY_PATH = "train_continued_001/campaign_summary.json"
CONTINUED_SUMMARY_PATH = "train_continued_002/campaign_summary.json"
# These receipt pins bind the completed local structural inspection and cleanup.
RESERVATION_USD = "8.00"
PRIOR_ARCHIVE_BYTES_MAX = 512 * 1024**2
PRIOR_EXPANDED_BYTES_MAX = 1024**3
ORIGINAL_AUTHORITY_SHA256 = "bc80b6e645b339a2b2ffd7ae1ddad0d9c970fb00dd142b37c2a3f9697828049d"
FIRST_CONTINUATION_AUTHORITY_SHA256 = "637482e436da4f6050cc8acbfaf1cec45e1bc60aa88474a5a7753733dfd0e905"
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
    "prior_summary_sha256": "2cb6f5659a0377695b00e49f5a45d9edff6f87db6fe648927c4719d26a15d33b",
    "prior_inspection_sha256": "e21c3ad7aa7cd2b2c278f5eff11a215ed4fb785beb16154d07413c7a1544d6db",
    "prior_parent_result_sha256": "ffb42912a72759a2c440571bcd929c397a8cc653b3d288d3a758221d52e4d86d",
    "prior_complete_sha256": "aac9bfe609b3c9d04c0ad83f8fb209bcf7da12f1c79529e02c39b4f162db7d84",
    "prior_cleanup_sha256": "4e49318d473776359a2c2097a180604e1d72e56aa1e4555569d7d6a3e06efc63",
    "prior_result_archive_sha256": "43795d51cdc1fba4c70b0d7c0cd27f4beaedbb7dbfbf1c89dc358946f069cd38",
    "base_guest_driver_sha256": "14a09d391435ffc354343f64ede83a079540000694dbd273bc55bedd13928a2e",
    "profile_sha256": canonical_sha256(FROZEN_PROFILE),
}
_RESOURCE_PLAN = base.resource_plan()
_RESOURCE_PLAN.update({"schema": SCHEMA, "task_scope": TASK_SCOPE,
    "restore_probe_seconds_max": 900, "restore_probe_process_count_max": 1,
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
    require(bindings["authority_sha256"] != FIRST_CONTINUATION_AUTHORITY_SHA256,
            "CONSUMED_FIRST_CONTINUATION_AUTHORITY_REJECTED")
    return bindings


def validate_continuation(continuation):
    require(type(continuation) is dict and set(continuation) == CONTINUATION_FIELDS,
            "EXACT_CONTINUATION_BINDINGS_REQUIRED")
    for key in CONTINUATION_DIGEST_FIELDS:
        value = continuation[key]
        require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None
                and value != "0" * 64, "CONTINUATION_DIGEST_INVALID:" + key)
    require(all(continuation[key] == value for key, value in FROZEN_CONTINUATION.items()),
            "PRIOR_CONTINUATION_EVIDENCE_OR_PROFILE_CHANGED")
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
            "One restore probe <=900s, training <=4800s, and two predictions <=300s each; no retries.",
            "75 GiB gp3 at included 3000 IOPS / 125 MiB/s, deleted with instance.",
            "At most 2048 shared S3 attempts, including helper requests, failures and polls.",
            "Prior input ZIP <=512MiB and all prior unpacked members <=1GiB; output archive <=2.5GiB includes retained history.",
            "Prior input, source, result and control objects together <6 decimal GB; outbound result/control bytes <3 decimal GB.",
            "Same-region S3, no NAT gateway, snapshots or extra volumes; seven-day expiration costed for a full month.",
            "Actual fees, taxes, resource failures and timing must be reconciled afterward."]}
