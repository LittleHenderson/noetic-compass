"""Pure launch-contract tests. No ledger reservation or provider interaction."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path

import pytest

from aws import budget
from aws import teaching_cycle_plan as plan


def bindings():
    return {**{key: "1" * 64 for key in plan.BINDING_FIELDS}, **plan.FROZEN_BINDINGS}


def ledger():
    return {"revision": 17, "sha256": "83fd87829a34a559ae901b553a851d79ec27359601230561afffb55955df2b92",
            "cap_usd": "400.00", "reserved_usd": "102.00", "unreserved_usd": "298.00"}


def request():
    return plan.build_request(job="cas-meta2-teaching-20260908050000-abcd1234", bindings=bindings(), ledger=ledger())


def test_exact_plan_is_budget_compatible_and_does_not_reserve():
    resource = plan.resource_plan()
    assert budget.validate_plan(resource, "8.00") == Decimal("8.00")
    assert resource["compute_at_ceiling_usd"] == "5.04"
    assert resource["rate_is_current_quote"] is False
    assert request()["new_reservation"] is False


def test_request_roundtrip_has_all_external_pins_and_is_inert():
    value = request()
    assert plan.validate_request(value, expected_bindings=bindings(), expected_ledger=ledger()) is value
    assert value["launch_authorized"] is False
    assert value["reuses_v9_one_shot_authorization"] is False
    assert len(value["bindings"]) == 17


def test_frozen_bundle_identities_match_stored_package_receipt():
    root = Path(__file__).resolve().parents[1]
    receipt = json.loads((root / "records/teaching_cycle_001/bundle_002/receipt.json").read_text())
    assert all(receipt[key] == value for key, value in plan.FROZEN_BINDINGS.items())


def test_plan_matches_proposal_and_does_not_reset_shared_budgets():
    root = Path(__file__).resolve().parents[1]
    proposal = json.loads((root / "records/teaching_cycle_001/LAUNCH_PROPOSAL.json").read_text())
    resource = plan.resource_plan()
    for key in ("account_id", "region", "instance_type", "instance_count", "training_worker_seconds_max",
                "prediction_process_count_max", "prediction_seconds_per_process_max", "artifact_expanded_bytes_max",
                "artifact_download_bytes_max", "cloud_evidence_retention_days_max", "training_archive_bytes_max",
                "training_expanded_bytes_max", "shared_lifetime_not_reset_between_processes"):
        assert resource[key] == proposal[key]
    assert resource["runtime_seconds_max"] == proposal["instance_seconds_max"]
    assert resource["artifact_upload_bytes_max"] == resource["artifact_download_bytes_max"]
    assert resource["worksheet_limits"]["prices_verified"] is False


@pytest.mark.parametrize("key,value", [("job", "cas-meta2-20260907155404-80e827c9"),
    ("task_scope", "condition_skill_v9"), ("launch_authorized", True), ("new_reservation", True),
    ("reuses_v9_one_shot_authorization", True), ("automatic_retries", 1), ("automatic_retries", False),
    ("reservation_usd", "8.01")])
def test_wrong_scope_paid_flags_or_retries_rejected(key, value):
    changed = request()
    changed[key] = value
    with pytest.raises(plan.PlanError):
        plan.validate_request(changed, expected_bindings=bindings(), expected_ledger=ledger())


@pytest.mark.parametrize("key", sorted(plan.BINDING_FIELDS))
def test_missing_external_pin_is_rejected(key):
    missing = bindings()
    del missing[key]
    with pytest.raises(plan.PlanError, match="EXACT_EXTERNAL_BINDINGS_REQUIRED"):
        plan.build_request(job=request()["job"], bindings=missing, ledger=ledger())


def test_known_consumed_v9_authority_is_rejected_even_with_teaching_label():
    value = bindings()
    value["authority_sha256"] = plan.V9_AUTHORITY_SHA256
    with pytest.raises(plan.PlanError, match="CONSUMED_V9_AUTHORITY_REJECTED"):
        plan.build_request(job=request()["job"], bindings=value, ledger=ledger())


def test_external_driver_change_and_stale_ledger_rejected():
    changed = request()
    changed["bindings"]["guest_driver_sha256"] = "2" * 64
    with pytest.raises(plan.PlanError, match="EXTERNAL_IDENTITY_MISMATCH"):
        plan.validate_request(changed, expected_bindings=bindings(), expected_ledger=ledger())
    expected = {**ledger(), "revision": 18, "sha256": "3" * 64,
                "reserved_usd": "110.00", "unreserved_usd": "290.00"}
    with pytest.raises(plan.PlanError, match="RECHECKED_LEDGER_MISMATCH"):
        plan.validate_request(request(), expected_bindings=bindings(), expected_ledger=expected)


@pytest.mark.parametrize("key,value", [("runtime_seconds_max", 7201), ("instance_count", True),
    ("artifact_download_bytes_max", 2684354561), ("training_worker_seconds_max", 4801)])
def test_resource_changes_rejected_even_when_request_hash_is_resealed(key, value):
    changed = request()
    changed["resource_plan"][key] = value
    changed["resource_plan_sha256"] = plan.canonical_sha256(changed["resource_plan"])
    with pytest.raises(plan.PlanError, match="RESOURCE_SCOPE_CHANGED"):
        plan.validate_request(changed, expected_bindings=bindings(), expected_ledger=ledger())


def test_returned_plan_does_not_mutate_the_canonical_scope():
    changed = plan.resource_plan()
    changed["ebs"]["size_gib"] = 999
    assert plan.resource_plan()["ebs"]["size_gib"] == 75


def test_insufficient_remaining_capacity_is_not_an_implicit_cap_increase():
    with pytest.raises(plan.PlanError, match="CAMPAIGN_CAPACITY_INSUFFICIENT"):
        plan.build_request(job=request()["job"], bindings=bindings(), ledger={**ledger(),
            "reserved_usd": "393.00", "unreserved_usd": "7.00"})
