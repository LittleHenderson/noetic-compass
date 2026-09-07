"""Pure tests for the condition-skill v9 launch lifecycle.

The provider is injected as a fake; no AWS, network, tensor, database, or
provider work occurs. Ledger files are temporary copies.
"""
import json
from pathlib import Path

import pytest

from aws import condition_skill_v9_launch as launch
from aws import condition_skill_v9_resource_plan as plan


JOB = "cas-meta2-20260907160000-abcdef12"


def write_ledger(tmp_path, reserved="98.00", unreserved="302.00", cap="400.00"):
    path = tmp_path / "campaign_ledger.json"
    path.write_text(json.dumps({"revision": 16, "cap_usd": cap,
                                "reserved_usd": reserved, "unreserved_usd": unreserved}))
    return path


def valid_request():
    return {
        "schema": plan.REQUEST_SCHEMA, "job": JOB, "source_sha": "a" * 40,
        "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
        "dataset_manifest_sha256": plan.DATASET_MANIFEST_SHA256,
        "seed": 7, "training": True, "native_execution": False,
        "automatic_retries": 0, "reservation_usd": "4.00",
        "launch_authorized": False, "new_reservation": False,
    }


def valid_authority():
    return {
        "schema": launch.AUTHORITY_SCHEMA, "job": JOB, "source_sha": "a" * 40,
        "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
        "dataset_manifest_sha256": plan.DATASET_MANIFEST_SHA256,
        "seed": 7, "training": True, "native_execution": False,
        "automatic_retries": 0, "reservation_usd": "4.00",
        "task_scope": "condition_skill_v9",
        "campaign_scope": "cas-meta2-composition-campaign",
        "owner_approval_record_sha256": "d" * 64,
    }


class FakeProvider:
    def __init__(self, ledger_path, fail_wait=False):
        self.ledger_path = ledger_path
        self.fail_wait = fail_wait
        self.calls = []

    def preflight(self):
        self.calls.append("preflight")
        return {"account": plan.RESOURCE_PLAN["account"], "region": plan.RESOURCE_PLAN["region"],
                "ami": plan.RESOURCE_PLAN["ami"], "instance_type": plan.RESOURCE_PLAN["instance_type"],
                "instance_count": 1, "gpu_name_contains": plan.RESOURCE_PLAN["gpu_name_contains"],
                "t4_rejected": True, "rate_ceiling_usd": plan.RESOURCE_PLAN["on_demand_rate_ceiling_usd"],
                "conflicting_resources": []}

    def reserve(self, amount):
        self.calls.append("reserve")
        ledger = json.loads(self.ledger_path.read_text())
        ledger["reserved_usd"] = "102.00"
        ledger["unreserved_usd"] = "298.00"
        self.ledger_path.write_text(json.dumps(ledger))
        return {"status": "RESERVED_NO_AUTOMATIC_REFUND", "amount_usd": amount}

    def launch(self, job, permit):
        self.calls.append("launch")
        return {"job": job, "permit": permit}

    def wait(self, job, timeout):
        self.calls.append("wait")
        if self.fail_wait:
            raise RuntimeError("INSTANCE_DIED")
        return {"worker_status": "REMOTE_FINISHED"}

    def collect(self, job):
        self.calls.append("collect")
        return {"result.json": {"sha256": "e" * 64, "bytes": 1}}

    def cleanup(self, job):
        self.calls.append("cleanup")
        return {"complete": True, "instance_terminated": True, "volumes_deleted": True,
                "inputs_deleted": True, "schedule_removed": True, "failures": []}


@pytest.fixture
def ledger(tmp_path):
    return write_ledger(tmp_path)


def test_plan_only_is_inert_and_calls_nothing():
    result = launch.plan_only()
    assert result["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert result["reservation_created"] is False
    assert result["provider_calls"] == 0
    assert result["scope"]["account"] == "807562639912"


def test_valid_authority_is_accepted():
    assert launch.validate_authority(valid_authority())["job"] == JOB


@pytest.mark.parametrize("mutate,reason", [
    (lambda a: a.update(schema="cas-meta2-other/1"), "CONDITION_SKILL_V9_AUTHORITY_SCHEMA"),
    (lambda a: a.update(job="bad"), "CONDITION_SKILL_V9_AUTHORITY_JOB"),
    (lambda a: a.update(source_sha="zz"), "CONDITION_SKILL_V9_AUTHORITY_SOURCE_SHA"),
    (lambda a: a.update(owner_approval_record_sha256="zz"), "CONDITION_SKILL_V9_AUTHORITY_HASH"),
    (lambda a: a.update(seed=8), "CONDITION_SKILL_V9_AUTHORITY_SEED"),
    (lambda a: a.update(training=False), "CONDITION_SKILL_V9_AUTHORITY_SCOPE"),
    (lambda a: a.update(automatic_retries=1), "CONDITION_SKILL_V9_AUTHORITY_NO_RETRIES"),
    (lambda a: a.update(reservation_usd="5.00"), "CONDITION_SKILL_V9_AUTHORITY_RESERVATION"),
    (lambda a: a.update(campaign_scope="other"), "CONDITION_SKILL_V9_AUTHORITY_BUDGET_SCOPES"),
    (lambda a: a.pop("job"), "CONDITION_SKILL_V9_AUTHORITY_FIELDS"),
    (lambda a: a.update(extra=1), "CONDITION_SKILL_V9_AUTHORITY_FIELDS"),
])
def test_authority_rejects_mutations(mutate, reason):
    authority = valid_authority()
    mutate(authority)
    with pytest.raises(ValueError, match=reason):
        launch.validate_authority(authority)


def test_read_ledger_and_reservation_scope(ledger):
    document = launch.read_ledger(ledger)
    assert document["ledger"]["revision"] == 16
    assert launch.validate_reservation_scope(document)["amount"] == 4.00


def test_reservation_scope_rejects_over_budget(tmp_path):
    document = launch.read_ledger(write_ledger(tmp_path, reserved="398.00", unreserved="2.00"))
    with pytest.raises(ValueError, match="RESERVATION_OUTSIDE_CAMPAIGN_BUDGET"):
        launch.validate_reservation_scope(document)


def test_read_ledger_rejects_changed_cap(tmp_path):
    with pytest.raises(ValueError, match="LEDGER_CAP_CHANGED"):
        launch.read_ledger(write_ledger(tmp_path, cap="300.00"))


def test_validate_preflight_rejects_mismatches():
    facts = {"account": plan.RESOURCE_PLAN["account"], "region": plan.RESOURCE_PLAN["region"],
             "ami": plan.RESOURCE_PLAN["ami"], "instance_type": plan.RESOURCE_PLAN["instance_type"],
             "instance_count": 1, "gpu_name_contains": plan.RESOURCE_PLAN["gpu_name_contains"],
             "t4_rejected": True, "rate_ceiling_usd": plan.RESOURCE_PLAN["on_demand_rate_ceiling_usd"],
             "conflicting_resources": []}
    assert launch.validate_preflight(facts) == facts
    for key, value, reason in [("account", "0", "PREFLIGHT_ACCOUNT"),
                               ("instance_type", "t3.micro", "PREFLIGHT_INSTANCE_TYPE"),
                               ("t4_rejected", False, "PREFLIGHT_T4"),
                               ("conflicting_resources", ["old-instance"], "PREFLIGHT_CONFLICTING_RESOURCES")]:
        broken = dict(facts)
        broken[key] = value
        with pytest.raises(ValueError, match=reason):
            launch.validate_preflight(broken)


def test_execute_end_to_end_success(ledger):
    provider = FakeProvider(ledger)
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert result["status"] == "AWS_CONDITION_SKILL_V9_FINISHED"
    assert result["reservation"]["status"] == "RESERVED_NO_AUTOMATIC_REFUND"
    assert result["cleanup"]["complete"] is True
    assert result["ledger_after"]["ledger"]["reserved_usd"] == "102.00"
    assert provider.calls == ["reserve", "launch", "wait", "collect", "cleanup"]
    assert result["claims"]["composition_proved"] is False


def test_execute_records_failure_and_still_cleans_up(ledger):
    provider = FakeProvider(ledger, fail_wait=True)
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert result["status"] == "AWS_CONDITION_SKILL_V9_LAUNCH_FAILED"
    assert result["cleanup"]["complete"] is True
    assert "INSTANCE_DIED" in result["outcome"]["exception"]
    assert "retry" not in provider.calls


def test_execute_requires_matching_request_and_authority(ledger):
    authority = valid_authority()
    authority["job"] = "cas-meta2-20260907170000-abcdef12"
    with pytest.raises(ValueError, match="REQUEST_AUTHORITY_JOB_MISMATCH"):
        launch.execute(valid_request(), authority, FakeProvider(ledger), ledger_path=ledger)


def test_execute_requires_provider(ledger):
    with pytest.raises(ValueError, match="PROVIDER_ADAPTER_REQUIRED"):
        launch.execute(valid_request(), valid_authority(), None, ledger_path=ledger)


def test_execute_requires_cleanup_complete(ledger):
    provider = FakeProvider(ledger)
    original = provider.cleanup

    def broken(job):
        original(job)
        return {"complete": False, "failures": ["volume-left-behind"]}

    provider.cleanup = broken
    with pytest.raises(ValueError, match="CLEANUP_INCOMPLETE_BLOCKS_RESULT"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)


def test_execute_rejects_second_reservation(ledger):
    provider = FakeProvider(ledger)
    original = provider.reserve

    def double(amount):
        original(amount)
        provider.calls.append("reserve-again")
        return {"status": "RESERVED_NO_AUTOMATIC_REFUND", "amount_usd": amount}

    provider.reserve = double
    with pytest.raises(ValueError, match="RESERVATION_MUST_BE_FIRST_AND_SINGLE"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
