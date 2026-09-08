"""Pure price-unit, account, GPU, pagination and budget checks."""
import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from aws import teaching_cycle_preflight as subject


def quote(unit, rates):
    return {"PriceList": [json.dumps({"terms": {"OnDemand": {"sku": {
        "priceDimensions": {str(i): {"unit": unit, "pricePerUnit": {"USD": rate}}
                            for i, rate in enumerate(rates)}}}}})]}


def prices():
    values = ["2.52", ".08", ".005", ".023", ".000005", ".0000004", ".09"]
    return {name: quote(spec[2], [value]) for (name, spec), value in zip(subject.PRICE_QUERIES.items(), values)}


def clients():
    ec2 = SimpleNamespace(
        describe_images=lambda **_: {"Images": [{"State": "available", "OwnerId": "898082745236", "Architecture": "x86_64"}]},
        describe_instance_types=lambda **_: {"InstanceTypes": [{"InstanceType": subject.INSTANCE,
            "GpuInfo": {"Gpus": [{"Name": "RTX PRO 4500", "Count": 1}]}, "VCpuInfo": {"DefaultVCpus": 8}}]},
        describe_instances=lambda **_: {"Reservations": []},
        describe_instance_type_offerings=lambda **_: {"InstanceTypeOfferings": [{"InstanceType": subject.INSTANCE}]})
    iterator = iter(prices().values())
    return {"ec2": ec2, "sts": SimpleNamespace(get_caller_identity=lambda: {"Account": subject.ACCOUNT}),
        "service-quotas": SimpleNamespace(get_service_quota=lambda **_: {"Quota": {"Value": 8}}),
        "pricing": SimpleNamespace(get_products=lambda **_: next(iterator))}


def test_worksheet_uses_conservative_rates_and_no_credits():
    result = subject.worksheet(prices())
    assert Decimal(result["estimated_bound_usd"]) < 8
    assert Decimal(result["cost_components_usd"]["compute_7200_seconds"]) == Decimal("5.04")
    assert result["free_tier_or_credit_assumed"] is False
    assert result["is_invoice"] is False


@pytest.mark.parametrize("response,unit,error", [
    ({"PriceList": []}, "Hrs", "PRICE_PRODUCTS_REQUIRED"),
    ({**quote("Hrs", ["2"]), "NextToken": "more"}, "Hrs", "PRICE_PAGINATION"),
    (quote("Requests", [".1"]), "Hrs", "PRICE_UNIT"),
    (quote("Hrs", ["NaN"]), "Hrs", "INVALID_PRICE"),
    (quote("Hrs", ["Infinity"]), "Hrs", "INVALID_PRICE"),
    (quote("Hrs", ["-1"]), "Hrs", "INVALID_PRICE"),
    (quote("Hrs", ["0"]), "Hrs", "NONZERO_PRICE"),
])
def test_invalid_quotes_fail(response, unit, error):
    with pytest.raises(ValueError, match=error):
        subject.highest_rate(response, unit)


def test_free_tier_does_not_hide_maximum_rate():
    assert subject.highest_rate(quote("GB", ["0", ".09", ".05"]), "GB") == Decimal(".09")


@pytest.mark.parametrize("name,value,error", [("compute", "2.53", "COMPUTE_RATE"),
    ("s3_storage", "10", "TOTAL_ABOVE"), ("egress", "10", "TOTAL_ABOVE")])
def test_over_budget_rejected(name, value, error):
    data = prices()
    data[name] = quote(subject.PRICE_QUERIES[name][2], [value])
    with pytest.raises(ValueError, match=error):
        subject.worksheet(data)


def test_observe_is_explicitly_not_capacity_or_launch_proof():
    result = subject.observe(clients())
    assert result["read_only"] is True
    assert result["reservation_created"] is False
    assert result["capacity_guaranteed"] is False
    assert result["runtime_cuda_proved"] is False


@pytest.mark.parametrize("kind", ["account", "gpu", "quota", "image", "active", "pagination", "offering"])
def test_preflight_identity_and_resource_refusals(kind):
    stack = clients()
    if kind == "account":
        stack["sts"].get_caller_identity = lambda: {"Account": "000000000000"}
    if kind == "gpu":
        data = stack["ec2"].describe_instance_types()
        data["InstanceTypes"][0]["GpuInfo"]["Gpus"][0]["Name"] = "T4"
        stack["ec2"].describe_instance_types = lambda **_: data
    if kind == "image":
        stack["ec2"].describe_images = lambda **_: {"Images": []}
    if kind == "quota":
        stack["service-quotas"].get_service_quota = lambda **_: {"Quota": {"Value": 4}}
    if kind == "active":
        stack["ec2"].describe_instances = lambda **_: {"Reservations": [{"Instances": [
            {"InstanceId": "i-other", "InstanceType": "g6.2xlarge", "State": {"Name": "running"}}]}]}
    if kind == "pagination":
        stack["ec2"].describe_instances = lambda **_: {"Reservations": [], "NextToken": "hidden"}
    if kind == "offering":
        stack["ec2"].describe_instance_type_offerings = lambda **_: {"InstanceTypeOfferings": []}
    with pytest.raises(ValueError):
        subject.observe(stack)
