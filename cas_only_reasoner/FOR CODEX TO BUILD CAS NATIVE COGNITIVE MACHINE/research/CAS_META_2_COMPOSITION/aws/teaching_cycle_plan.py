"""Pure new teaching-launch contract. Validation neither authorizes nor reserves.

Prices here are conservative ceilings, not live quotes. The caller must verify
external source files, authority, pricing and the current canonical ledger.
The consumed condition-v9 authorization is expressly outside this scope.
"""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
import re

SCHEMA = "cas-teaching-cycle-resource-plan/2"
REQUEST_SCHEMA = "cas-teaching-cycle-launch-request/2"
TASK_SCOPE = "teaching_cycle_v2_four_arm_binding"
JOB_PATTERN = r"cas-meta2-teaching-\d{14}-[0-9a-f]{8}"
RESERVATION_USD = "8.00"
V9_AUTHORITY_SHA256 = "c247aa0c6be9a6536b4012b76c6b3a997798e3dab9b40385128a971ed9c4f79e"
FROZEN_BINDINGS = {
    "source_commit": "c8c0e558cf30cd5fe06c2bf3d475697e97698a3e",
    "source_sha256": "60340b5865c674cc5558a27da6524928ec0db7042163b1ef031591ad7794555e",
    "archive_sha256": "494f44d467a85e2edd54b568cf4b0822db6e25355003a8a6ae8c7d4c09dd8cec",
    "manifest_sha256": "975296defc543e234d4bd09fcf9e46a25dc42792e4cf6aed5ad35332de3167a9",
    "training_cases_sha256": "0ff9a38451aac68ec59fbc49b84cadc3cb6ccb318b4459738fb85c95f0e5c496",
    "development_cases_sha256": "45682abc65433707099691c3e849536c06a47c12604022ff97527922e886b667",
}
BINDING_FIELDS = frozenset((*FROZEN_BINDINGS, "material_receipt_sha256", "public_sets_sha256",
    "scorer_sha256", "parent_driver_sha256", "guest_driver_sha256", "bootstrap_sha256",
    "provider_source_sha256", "provider_dependencies_sha256", "proposal_sha256",
    "authority_sha256", "pricing_receipt_sha256"))
_RESOURCE_PLAN = {
    "schema": SCHEMA, "task_scope": TASK_SCOPE,
    "account_id": "807562639912", "region": "us-west-2",
    "instance_type": "g7.2xlarge", "instance_count": 1,
    "visible_gpu_count": 1, "required_gpu_name_contains": "RTX PRO 4500", "t4_rejected": True,
    "runtime_seconds_max": 7200, "training_worker_seconds_max": 4800,
    "prediction_process_count_max": 2, "prediction_seconds_per_process_max": 300,
    "shared_lifetime_not_reset_between_processes": True,
    "automatic_retries": 0, "reservation_usd": RESERVATION_USD,
    "on_demand_hourly_usd_max": "2.52", "ancillary_reserved_usd": "2.96",
    "compute_at_ceiling_usd": "5.04", "rate_is_current_quote": False,
    "cost_worksheet_and_live_pricing_required": True,
    "ebs": {"type": "gp3", "size_gib": 75, "iops": 3000, "throughput_mib_s": 125,
            "encrypted": True, "delete_on_termination": True},
    "inbound_rules": [], "egress_tcp_ports": [443],
    "training_archive_bytes_max": 33554432, "training_expanded_bytes_max": 67108864,
    "artifact_expanded_bytes_max": 2684354560, "artifact_download_bytes_max": 2684354560,
    "artifact_upload_bytes_max": 2684354560, "artifact_bytes_bound_shared_across_processes": True,
    "public_release_bytes_max": 1048576, "cloud_evidence_retention_days_max": 7,
    "independent_shutdown_verified_before_worker_release": True,
    "final_public_inputs_released_only_after_checkpoint_seal": True,
    "native_execution": False, "retention_after_intervening_learning": False,
    "seed": 7, "arms": ["cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary"],
    "worksheet_limits": {
        "s3_api_attempts_max": 2048, "parent_s3_api_attempts_max": 1024,
        "guest_s3_api_attempts_max": 896, "bootstrap_s3_api_attempts_max": 128,
        "ebs_gib_hours_max": "150.00",
        "public_ipv4_hours_max": "2.00", "charged_artifact_download_gib_max": "2.50",
        "request_caps_include_failed_attempts_and_polls": True,
        "caps_shared_by_parent_guest_and_all_processes": True,
        "prices_verified": False,
        "boundary": "Worksheet input ceilings only; actual rates, billed units and sufficient ancillary cover must be verified before launch.",
    },
    "requirements_are_not_observed_provider_receipts": True,
    "reuses_v9_one_shot_authorization": False,
}


class PlanError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise PlanError("TEACHING_PLAN:" + reason)


def canonical_sha256(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PlanError("TEACHING_PLAN:NONCANONICAL_VALUE") from error
    return sha256(raw).hexdigest()


def resource_plan():
    return deepcopy(_RESOURCE_PLAN)


def validate_resource_plan(plan):
    require(type(plan) is dict and canonical_sha256(plan) == canonical_sha256(_RESOURCE_PLAN),
            "RESOURCE_SCOPE_CHANGED")
    return plan


def validate_bindings(bindings):
    require(type(bindings) is dict and set(bindings) == BINDING_FIELDS, "EXACT_EXTERNAL_BINDINGS_REQUIRED")
    for name, value in bindings.items():
        length = 40 if name == "source_commit" else 64
        require(type(value) is str and re.fullmatch(r"[0-9a-f]{" + str(length) + "}", value) is not None
                and value != "0" * length, "BINDING_DIGEST_INVALID:" + name)
    require(all(bindings[name] == value for name, value in FROZEN_BINDINGS.items()), "FROZEN_WORKER_BUNDLE_CHANGED")
    require(bindings["authority_sha256"] != V9_AUTHORITY_SHA256, "CONSUMED_V9_AUTHORITY_REJECTED")
    return bindings


def validate_ledger_snapshot(ledger):
    require(type(ledger) is dict and set(ledger) ==
            {"revision", "sha256", "cap_usd", "reserved_usd", "unreserved_usd"}, "LEDGER_BINDING_REQUIRED")
    require(type(ledger["revision"]) is int and ledger["revision"] >= 17, "LEDGER_REVISION_INVALID")
    require(type(ledger["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", ledger["sha256"]) is not None
            and ledger["sha256"] != "0" * 64, "LEDGER_DIGEST_INVALID")
    for name in ("cap_usd", "reserved_usd", "unreserved_usd"):
        require(type(ledger[name]) is str and re.fullmatch(r"(?:0|[1-9]\d*)\.\d{2}", ledger[name]) is not None,
                "CANONICAL_USD_REQUIRED:" + name)
    require(ledger["cap_usd"] == "400.00", "INCLUSIVE_CAMPAIGN_CAP_REQUIRED")
    require(Decimal(ledger["reserved_usd"]) + Decimal(ledger["unreserved_usd"]) == Decimal("400.00"),
            "LEDGER_TOTALS_INCONSISTENT")
    require(Decimal(ledger["unreserved_usd"]) >= Decimal(RESERVATION_USD), "CAMPAIGN_CAPACITY_INSUFFICIENT")
    return ledger


def build_request(*, job, bindings, ledger):
    plan = resource_plan()
    request = {"schema": REQUEST_SCHEMA, "job": job, "task_scope": TASK_SCOPE,
        "bindings": deepcopy(bindings), "ledger": deepcopy(ledger), "resource_plan": plan,
        "resource_plan_sha256": canonical_sha256(plan), "reservation_usd": RESERVATION_USD,
        "automatic_retries": 0, "launch_authorized": False, "new_reservation": False,
        "reuses_v9_one_shot_authorization": False}
    return validate_request(request, expected_bindings=bindings, expected_ledger=ledger)


def validate_request(request, *, expected_bindings, expected_ledger):
    validate_bindings(expected_bindings)
    validate_ledger_snapshot(expected_ledger)
    require(type(request) is dict and set(request) == {"schema", "job", "task_scope", "bindings", "ledger",
        "resource_plan", "resource_plan_sha256", "reservation_usd", "automatic_retries", "launch_authorized",
        "new_reservation", "reuses_v9_one_shot_authorization"}, "REQUEST_FIELDS_INVALID")
    require(request["schema"] == REQUEST_SCHEMA and request["task_scope"] == TASK_SCOPE, "TEACHING_SCOPE_REQUIRED")
    require(type(request["job"]) is str and re.fullmatch(JOB_PATTERN, request["job"]) is not None,
            "FRESH_TEACHING_JOB_REQUIRED")
    validate_bindings(request["bindings"])
    validate_ledger_snapshot(request["ledger"])
    require(canonical_sha256(request["bindings"]) == canonical_sha256(expected_bindings), "EXTERNAL_IDENTITY_MISMATCH")
    require(canonical_sha256(request["ledger"]) == canonical_sha256(expected_ledger), "RECHECKED_LEDGER_MISMATCH")
    validate_resource_plan(request["resource_plan"])
    require(request["resource_plan_sha256"] == canonical_sha256(request["resource_plan"]), "RESOURCE_PLAN_DIGEST_MISMATCH")
    require(request["reservation_usd"] == RESERVATION_USD, "RESERVATION_CEILING_CHANGED")
    require(type(request["automatic_retries"]) is int and request["automatic_retries"] == 0, "NO_RETRIES_REQUIRED")
    require(request["launch_authorized"] is False and request["new_reservation"] is False, "REQUEST_MUST_REMAIN_INERT")
    require(request["reuses_v9_one_shot_authorization"] is False, "V9_AUTHORITY_REUSE_REJECTED")
    return request
