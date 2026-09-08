"""Pure continuation admission tests: no reservation, provider or neural work."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
import importlib.util
from zipfile import ZipFile
from pathlib import Path

import pytest

from aws import budget
from aws import teaching_cycle_plan as original
from aws import teaching_continuation_plan_v2 as plan
from aws.teaching_cycle_preflight import PRICE_QUERIES, worksheet as original_worksheet

spec = importlib.util.spec_from_file_location("v2_plan_shared_fixtures", Path(__file__).with_name("test_teaching_continuation_second_fixtures.py"))
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)
synthetic_unbound_receipts = shared.synthetic_unbound_receipts


def bindings():
    return {**{key: "1" * 64 for key in plan.BINDING_FIELDS}, **plan.FROZEN_BINDINGS}


def continuation():
    return {**{key: "2" * 64 for key in plan.CONTINUATION_DIGEST_FIELDS},
        **plan.FROZEN_CONTINUATION, "original_campaign_root": plan.ORIGINAL_CAMPAIGN_ROOT,
        "prior_state_archive_bytes": 70_000_000, "prior_state_expanded_bytes": 100_000_000}


def ledger():
    return {"revision": 21, "sha256": "3" * 64, "cap_usd": "400.00",
            "reserved_usd": "118.00", "unreserved_usd": "282.00"}


def request():
    return plan.build_request(job="cas-meta2-teaching-20260908090000-abcd1234",
        logical_run_id=plan.LOGICAL_RUN_ID, bindings=bindings(), continuation=continuation(), ledger=ledger())


def validate(value, **changes):
    expected = {"expected_bindings": bindings(), "expected_continuation": continuation(), "expected_ledger": ledger()}
    expected.update(changes)
    return plan.validate_request(value, **expected)


def prices(**overrides):
    values = {"compute": "2.5200000000", "ebs": "0.08", "ipv4": "0.005",
        "s3_storage": "0.023", "s3_put": "0.000005", "s3_get": "0.0000004", "egress": "0.09"}
    values.update(overrides)
    return {name: {"PriceList": [json.dumps({"terms": {"OnDemand": {"term": {"priceDimensions": {
        "dimension": {"unit": definition[2], "pricePerUnit": {"USD": values[name]}}}}}}})]}
        for name, definition in PRICE_QUERIES.items()}


def test_inert_new_cloud_job_retains_original_logical_id_and_exact_budget():
    value = request()
    assert validate(value) is value
    assert value["job"] != value["logical_run_id"]
    assert len(value["job"] + "-807562639912") <= 63
    assert value["new_reservation"] is False and value["launch_authorized"] is False
    assert value["reuses_original_reservation"] is False
    assert budget.validate_plan(value["resource_plan"], "8.00") == Decimal("8.00")
    limits = value["resource_plan"]
    assert limits["runtime_seconds_max"] == 7200
    assert limits["restore_probe_seconds_max"] == 900
    assert limits["training_worker_seconds_max"] == 4800
    assert limits["prediction_process_count_max"] * limits["prediction_seconds_per_process_max"] == 600
    assert limits["worksheet_limits"]["s3_storage_decimal_gb_months_max"] == "6.00"


def test_original_plan_is_unchanged_and_new_plan_is_deep_copied():
    before = original.resource_plan()
    changed = plan.resource_plan()
    changed["ebs"]["size_gib"] = 999
    assert original.resource_plan() == before
    assert "restore_probe_seconds_max" not in before
    assert plan.resource_plan()["ebs"]["size_gib"] == 75


@pytest.mark.parametrize("field", sorted(plan.CONTINUATION_FIELDS))
def test_missing_prior_or_helper_pin_fails(field):
    value = continuation()
    del value[field]
    with pytest.raises(plan.PlanError, match="EXACT_CONTINUATION_BINDINGS_REQUIRED"):
        plan.validate_continuation(value)


@pytest.mark.parametrize("field,value", [("job", plan.LOGICAL_RUN_ID), ("logical_run_id", "different"),
    ("job", "cas-meta2-teaching-continuation-20260908090000-abcd1234"),
    ("schema", original.REQUEST_SCHEMA), ("task_scope", original.TASK_SCOPE),
    ("automatic_retries", True), ("automatic_retries", 1), ("reservation_usd", "8.01"),
    ("launch_authorized", True), ("new_reservation", True), ("reuses_original_reservation", True),
    ("reuses_v9_one_shot_authorization", True)])
def test_relabelled_scope_retries_or_paid_claims_rejected(field, value):
    changed = request()
    changed[field] = value
    with pytest.raises(plan.PlanError):
        validate(changed)


@pytest.mark.parametrize("field", sorted(plan.FROZEN_BINDINGS))
def test_frozen_worker_material_and_scorer_cannot_be_rebound(field):
    changed = bindings()
    changed[field] = "f" * (40 if field == "source_commit" else 64)
    with pytest.raises(plan.PlanError):
        plan.validate_bindings(changed)


@pytest.mark.parametrize("field", sorted(plan.FROZEN_CONTINUATION))
def test_known_prior_evidence_and_profile_cannot_be_relabelled(field):
    changed = continuation()
    changed[field] = "f" * 64
    with pytest.raises(plan.PlanError, match="PRIOR_CONTINUATION_EVIDENCE_OR_PROFILE_CHANGED"):
        plan.validate_continuation(changed)


@pytest.mark.parametrize("field,value", [("prior_state_archive_bytes", 0), ("prior_state_archive_bytes", True),
    ("prior_state_archive_bytes", plan.PRIOR_ARCHIVE_BYTES_MAX + 1),
    ("prior_state_expanded_bytes", plan.PRIOR_EXPANDED_BYTES_MAX + 1),
    ("prior_state_expanded_bytes", 1.0), ("original_campaign_root", "/opt/other"),
    ("restore_probe_sha256", "0" * 64), ("restore_probe_sha256", "f" * 63)])
def test_prior_bounds_and_paths_are_exact(field, value):
    changed = continuation()
    changed[field] = value
    with pytest.raises(plan.PlanError):
        plan.validate_continuation(changed)


def test_request_deep_copies_external_maps_and_requires_rechecked_ledger():
    changed = request()
    changed["continuation"]["restore_probe_sha256"] = "f" * 64
    with pytest.raises(plan.PlanError, match="EXTERNAL_IDENTITY_MISMATCH:continuation"):
        validate(changed)
    with pytest.raises(plan.PlanError, match="EXTERNAL_IDENTITY_MISMATCH:ledger"):
        validate(request(), expected_ledger={**ledger(), "revision": 22, "sha256": "4" * 64})
    with pytest.raises(plan.PlanError, match="CAMPAIGN_CAPACITY_INSUFFICIENT"):
        validate(request(), expected_ledger={**ledger(), "reserved_usd": "393.00", "unreserved_usd": "7.00"})


@pytest.mark.parametrize("authority", [original.V9_AUTHORITY_SHA256, plan.ORIGINAL_AUTHORITY_SHA256,
                                       plan.FIRST_CONTINUATION_AUTHORITY_SHA256])
def test_consumed_authority_is_not_reused(authority):
    changed = bindings()
    changed["authority_sha256"] = authority
    with pytest.raises(plan.PlanError, match="AUTHORITY_REJECTED"):
        plan.validate_bindings(changed)


@pytest.mark.parametrize("field,value", [("restore_probe_seconds_max", 901), ("training_worker_seconds_max", 4801),
    ("runtime_seconds_max", 7201), ("prior_state_archive_bytes_max", plan.PRIOR_ARCHIVE_BYTES_MAX + 1),
    ("prior_state_expanded_bytes_max", plan.PRIOR_EXPANDED_BYTES_MAX + 1), ("instance_count", True)])
def test_resealed_resource_expansions_rejected(field, value):
    changed = request()
    changed["resource_plan"][field] = value
    changed["resource_plan_sha256"] = plan.canonical_sha256(changed["resource_plan"])
    with pytest.raises(plan.PlanError, match="RESOURCE_SCOPE_CHANGED"):
        validate(changed)


def test_new_worksheet_prices_all_six_storage_gb_and_preserves_raw_rates():
    raw = prices()
    copy = deepcopy(raw)
    old, new = original_worksheet(raw), plan.worksheet(raw)
    assert raw == copy
    assert new["rates_usd"]["compute"] == "2.5200000000"
    assert "s3_3gb_full_month_conservative" not in new["cost_components_usd"]
    assert Decimal(new["cost_components_usd"]["s3_6gb_full_month_conservative"]) == Decimal("0.138")
    assert Decimal(new["estimated_bound_usd"]) - Decimal(old["estimated_bound_usd"]) == Decimal("0.069")
    assert new["is_invoice"] is False and new["free_tier_or_credit_assumed"] is False


@pytest.mark.parametrize("overrides,reason", [({"compute": "2.5200000001"}, "COMPUTE_RATE_ABOVE_CEILING"),
    ({"s3_storage": "1"}, "TOTAL_ABOVE_RESERVATION")])
def test_worksheet_refuses_excess_cost_without_rounding(overrides, reason):
    with pytest.raises(plan.PlanError, match=reason):
        plan.worksheet(prices(**overrides))


def test_exact_latest_evidence_constants_match_retained_receipts_without_synthetic_pins():
    # A fresh import bypasses the synthetic fixture. Missing/unbound real pins
    # must fail this test, not be skipped or treated as a valid declaration.
    spec = importlib.util.spec_from_file_location("aws._v2_literal_pin_check", plan.__file__)
    real = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(real)
    assert not any(value.startswith("UNBOUND_") for value in real.FROZEN_CONTINUATION.values())
    root = Path(__file__).resolve().parents[1] / "records/teaching_cycle_001"
    prior = root / "continuation_001"
    files = {"prior_inspection_sha256": "continuation_inspection_002.json",
        "prior_parent_result_sha256": "launch/result.json",
        "prior_complete_sha256": "launch/partial_collected/complete.json",
        "prior_cleanup_sha256": "cleanup_recovery_002/result.json"}
    for key, relative in files.items():
        assert sha256((prior / relative).read_bytes()).hexdigest() == real.FROZEN_CONTINUATION[key]
    complete = json.loads((prior / "launch/partial_collected/complete.json").read_bytes())
    assert complete["campaign_summary_sha256"] == real.FROZEN_CONTINUATION["prior_summary_sha256"]
    assert complete["artifact"]["sha256"] == real.FROZEN_CONTINUATION["prior_result_archive_sha256"]
    with ZipFile(prior / "launch/partial_collected/artifacts.zip") as archive:
        original = archive.read("train/campaign_summary.json")
        resumed = archive.read(real.RESUME_SUMMARY_PATH)
    assert sha256(resumed).hexdigest() == real.FROZEN_CONTINUATION["prior_summary_sha256"]
    assert sha256(original).hexdigest() == "26b23bb5f23ca875375797db155e8520b947bf0b4eada71e596a9ec7493e195f"
    assert real.RESUME_SUMMARY_PATH == "train_continued_001/campaign_summary.json"
    assert real.CONTINUED_SUMMARY_PATH == "train_continued_002/campaign_summary.json"
    rows = json.loads(resumed)["arms"]
    assert {arm: row["observed_optimizer_steps"] for arm, row in rows.items()} == {
        "cas.aligned": 784, "cas.ordinary": 784, "generic.aligned": 784, "generic.ordinary": 774}
    assert 4 * 896 - sum(row["observed_optimizer_steps"] for row in rows.values()) == 458
    original_request = json.loads((root / "job_003/request.json").read_bytes())
    assert all(original_request["bindings"][key] == value for key, value in real.FROZEN_BINDINGS.items())
    assert original_request["job"] == real.LOGICAL_RUN_ID


def test_v2_exact_schema_scope_and_unchanged_16_epoch_profile():
    value = request()
    assert value["schema"] == "cas-teaching-continuation-launch-request/2"
    assert value["task_scope"] == "teaching_cycle_v2_four_arm_binding_continuation_002"
    assert value["resource_plan"]["schema"] == "cas-teaching-continuation-resource-plan/2"
    assert value["resource_plan"]["restore_probe_seconds_max"] == 900
    assert value["resource_plan"]["runtime_seconds_max"] == 7200
    assert value["resource_plan"]["restore_probe_seconds_max"] + value["resource_plan"]["training_worker_seconds_max"] + 600 < 7200
    from aws import teaching_continuation_plan as first
    assert plan.FROZEN_PROFILE == first.FROZEN_PROFILE
    assert plan.FROZEN_BINDINGS == first.FROZEN_BINDINGS
    for field, old in (("schema", first.REQUEST_SCHEMA), ("task_scope", first.TASK_SCOPE)):
        changed = deepcopy(value)
        changed[field] = old
        with pytest.raises(plan.PlanError, match="CONTINUATION_SCOPE_REQUIRED"):
            validate(changed)


def test_synthetic_unbound_marker_is_never_admitted_as_a_digest():
    changed = continuation()
    changed["prior_inspection_sha256"] = "UNBOUND_INSPECTION_RECEIPT"
    with pytest.raises(plan.PlanError, match="CONTINUATION_DIGEST_INVALID"):
        plan.validate_continuation(changed)
