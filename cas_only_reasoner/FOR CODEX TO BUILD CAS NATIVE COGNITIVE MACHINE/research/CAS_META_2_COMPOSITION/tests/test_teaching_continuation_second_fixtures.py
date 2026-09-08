"""Shared pure slice-two test inputs; not authorization or paid execution."""
from aws import teaching_continuation_plan_v2 as plan
from aws.teaching_cycle_preflight import PRICE_QUERIES, worksheet as original_worksheet
import json
from hashlib import sha256
import pytest

@pytest.fixture(autouse=True)
def synthetic_unbound_receipts(monkeypatch):
    """Only test-local substitutes while real admission pins are unfinished."""
    for key, value in tuple(plan.FROZEN_CONTINUATION.items()):
        if value.startswith("UNBOUND_"):
            monkeypatch.setitem(plan.FROZEN_CONTINUATION, key,
                                sha256(("SIMULATED_TEST_ONLY:" + key).encode()).hexdigest())

def bindings():
    return {**{key: "1" * 64 for key in plan.BINDING_FIELDS}, **plan.FROZEN_BINDINGS}

def continuation():
    return {**{key: "2" * 64 for key in plan.CONTINUATION_DIGEST_FIELDS},
        **plan.FROZEN_CONTINUATION, "original_campaign_root": plan.ORIGINAL_CAMPAIGN_ROOT,
        "prior_state_archive_bytes": 150_000_000, "prior_state_expanded_bytes": 200_000_000}

def ledger():
    return {"revision": 21, "sha256": "3" * 64, "cap_usd": "400.00",
            "reserved_usd": "126.00", "unreserved_usd": "274.00"}

def prices(**overrides):
    values = {"compute": "2.5200000000", "ebs": "0.08", "ipv4": "0.005",
        "s3_storage": "0.023", "s3_put": "0.000005", "s3_get": "0.0000004", "egress": "0.09"}
    values.update(overrides)
    return {name: {"PriceList": [json.dumps({"terms": {"OnDemand": {"term": {"priceDimensions": {
        "dimension": {"unit": definition[2], "pricePerUnit": {"USD": values[name]}}}}}}})]}
        for name, definition in PRICE_QUERIES.items()}
