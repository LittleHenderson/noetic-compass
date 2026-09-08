"""Read-only continuation preflight with fake clients and literal fake prices."""
from decimal import Decimal
from hashlib import sha256
import importlib.util
from pathlib import Path

import pytest

from aws import teaching_continuation_preflight as subject

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fake_original_preflight",
    ROOT / "tests/test_teaching_cycle_preflight.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def test_current_source_and_original_run_identity_bound():
    result = subject.observe(fixture.clients())
    assert result["schema"] == subject.SCHEMA
    assert result["logical_run_id"] == subject.plan.LOGICAL_RUN_ID
    assert result["source_sha256"] == sha256(Path(subject.__file__).read_bytes()).hexdigest()
    assert result["base_preflight_sha256"] == sha256(Path(subject.base.__file__).read_bytes()).hexdigest()
    assert result["plan_sha256"] == sha256(Path(subject.plan.__file__).read_bytes()).hexdigest()
    for key in ("restore_proved", "reservation_created", "capacity_guaranteed", "runtime_cuda_proved",
                "iam_propagation_proved", "shutdown_schedule_proved"):
        assert result[key] is False
    assert result["read_only"] is True and not result["conflicting_resources"]


def test_exact_six_gb_worksheet_and_raw_quotes():
    prices = fixture.prices()
    result = subject.observe(fixture.clients())
    assert result["raw_prices"] == prices
    worksheet = result["cost_worksheet"]
    assert worksheet == subject.plan.worksheet(prices)
    components = {key: Decimal(value) for key, value in worksheet["cost_components_usd"].items()}
    assert components == {"compute_7200_seconds": Decimal("5.04"),
        "ebs_75_gib_7200_seconds": Decimal(".08") * 75 * 2 / (28 * 24),
        "one_ipv4_7200_seconds": Decimal(".01"),
        "s3_6gb_full_month_conservative": Decimal(".138"),
        "s3_2048_calls_highest_tier": Decimal(".000005") * 2048,
        "internet_egress_3gb": Decimal(".27"), "other_allowance": Decimal("1")}
    assert Decimal(worksheet["estimated_bound_usd"]) == sum(components.values())
    assert Decimal(worksheet["remaining_buffer_usd"]) == Decimal("8") - sum(components.values())
    assert worksheet["is_invoice"] is worksheet["free_tier_or_credit_assumed"] is False
    original = subject.base.worksheet(prices)
    assert Decimal(worksheet["estimated_bound_usd"]) - Decimal(original["estimated_bound_usd"]) == Decimal(".069")


def test_six_gb_cost_can_refuse_quote_original_three_gb_would_accept():
    prices = fixture.prices()
    prices["s3_storage"] = fixture.quote(subject.base.PRICE_QUERIES["s3_storage"][2], [".40"])
    assert Decimal(subject.base.worksheet(prices)["estimated_bound_usd"]) < 8
    stack = fixture.clients()
    quotes = iter(prices.values())
    stack["pricing"].get_products = lambda **kwargs: next(quotes)
    with pytest.raises(subject.plan.PlanError, match="TOTAL_ABOVE_RESERVATION"):
        subject.observe(stack)


@pytest.mark.parametrize("fault,reason", [("account", "ACCOUNT_MISMATCH"), ("type", "TYPE_MISMATCH"),
    ("gpu", "GPU_MISMATCH"), ("quota", "QUOTA_TOO_LOW"), ("conflict", "QUOTA_CONFLICT"),
    ("pagination", "PAGINATION"), ("offering", "NO_OFFERING"), ("image", "AMI_MISMATCH")])
def test_original_provider_guards_remain_active(fault, reason):
    stack = fixture.clients()
    if fault == "account":
        stack["sts"].get_caller_identity = lambda: {"Account": "000000000000"}
    elif fault in ("type", "gpu"):
        data = stack["ec2"].describe_instance_types()
        if fault == "type":
            data["InstanceTypes"][0]["InstanceType"] = "g4dn.xlarge"
        else:
            data["InstanceTypes"][0]["GpuInfo"]["Gpus"][0]["Name"] = "T4"
        stack["ec2"].describe_instance_types = lambda **kwargs: data
    elif fault == "quota":
        stack["service-quotas"].get_service_quota = lambda **kwargs: {"Quota": {"Value": 4}}
    elif fault == "conflict":
        stack["ec2"].describe_instances = lambda **kwargs: {"Reservations": [{"Instances": [
            {"InstanceId": "i-synthetic", "InstanceType": "g7.2xlarge", "State": {"Name": "running"}}]}]}
    elif fault == "pagination":
        stack["ec2"].describe_instances = lambda **kwargs: {"Reservations": [], "NextToken": "more"}
    elif fault == "offering":
        stack["ec2"].describe_instance_type_offerings = lambda **kwargs: {"InstanceTypeOfferings": []}
    else:
        stack["ec2"].describe_images = lambda **kwargs: {"Images": []}
    with pytest.raises(ValueError, match=reason):
        subject.observe(stack)


@pytest.mark.parametrize("rate", ["2.5200000001", "NaN", "Infinity", "-1", "0"])
def test_invalid_or_above_ceiling_compute_rate_rejected(rate):
    stack, prices = fixture.clients(), fixture.prices()
    prices["compute"] = fixture.quote("Hrs", [rate])
    quotes = iter(prices.values())
    stack["pricing"].get_products = lambda **kwargs: next(quotes)
    with pytest.raises(ValueError):
        subject.observe(stack)


def test_live_shaped_trailing_zero_quote_is_retained_exactly():
    stack, prices = fixture.clients(), fixture.prices()
    prices["compute"] = fixture.quote("Hrs", ["2.5200000000"])
    quotes = iter(prices.values())
    stack["pricing"].get_products = lambda **kwargs: next(quotes)
    result = subject.observe(stack)
    assert result["raw_prices"] == prices
    assert result["cost_worksheet"]["rates_usd"]["compute"] == "2.5200000000"
