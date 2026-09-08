"""Pure tests for the condition-skill v9 launch lifecycle.

The provider is injected as a fake; no AWS, network, tensor, database, or
provider work occurs. Ledger files are temporary copies.
"""
import copy
import json
from pathlib import Path

import pytest

from aws import condition_skill_v9_launch as launch
from aws import condition_skill_v9_resource_plan as plan
from aws import budget


JOB = "cas-meta2-20260907160000-abcdef12"


def budget_plan():
    return launch.reservation_plan()


def write_ledger(tmp_path, reserved="98.00", unreserved=None, cap="400.00"):
    """Use the real budget writer, only against this test's private directory."""
    path = tmp_path / "campaign_ledger.json"
    prior = tmp_path / "prior.json"
    approval = tmp_path / "approval.json"
    prior.write_bytes((launch.ROOT.parent / "CAS_META_1_LEARNED_SELECTION" /
                       "records/aws_budget_ledger.json").read_bytes())
    approval.write_bytes((launch.ROOT / "records/budget/OWNER_APPROVAL_SOURCE.json").read_bytes())
    initial = budget.initialize_ledger(prior, approval, path)
    extra = budget.amount(reserved) - budget.amount(initial["total_reserved_usd"])
    if extra:
        budget.reserve_budget("cas-meta2-fixture-earlier", "a" * 40, "b" * 64,
                              str(extra), budget_plan(), path)
    if cap != "400.00" or unreserved is not None:
        state = budget.decoded(path.read_bytes())
        state["owner_task_cap_usd"] = cap
        if unreserved is not None:
            state["remaining_unreserved_usd"] = unreserved
        path.write_bytes(budget.encoded(state))
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
        "owner_approval_record_sha256":
            launch.digest(launch.OWNER_APPROVAL_PATH.read_bytes()),
    }


class FakeProvider:
    def __init__(self, ledger_path, fail_wait=False):
        self.ledger_path = ledger_path
        self.fail_wait = fail_wait
        self.calls = []

    def configure_evidence(self, directory):
        self.evidence = directory

    def preflight(self):
        self.calls.append("preflight")
        return {"account": plan.RESOURCE_PLAN["account"], "region": plan.RESOURCE_PLAN["region"],
                "ami": plan.RESOURCE_PLAN["ami"], "instance_type": plan.RESOURCE_PLAN["instance_type"],
                "instance_count": 1, "gpu_name_contains": plan.RESOURCE_PLAN["gpu_name_contains"],
                "visible_gpu_count": 1, "t4_rejected": True,
                "rate_ceiling_usd": plan.RESOURCE_PLAN["on_demand_rate_ceiling_usd"],
                "conflicting_resources": []}

    def reserve(self, amount):
        assert (self.evidence / "intent.json").is_file()
        self.calls.append("reserve")
        receipt = budget.reserve_budget(JOB, "a" * 40, "b" * 64, amount,
                                        budget_plan(), self.ledger_path)
        return {**receipt, "aws_side_reservation": {"status": "RECORDED"}}

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
    assert document["ledger"]["schema"] == budget.SCHEMA
    assert document["ledger"]["total_reserved_usd"] == "98.00"
    assert launch.validate_reservation_scope(document)["amount"] == "4.00"


def test_reservation_scope_rejects_over_budget(tmp_path):
    document = launch.read_ledger(write_ledger(tmp_path, reserved="398.00", unreserved="2.00"))
    with pytest.raises(ValueError, match="RESERVATION_OUTSIDE_CAMPAIGN_BUDGET"):
        launch.validate_reservation_scope(document)


def test_read_ledger_rejects_changed_cap(tmp_path):
    with pytest.raises(ValueError, match="INVALID_CAMPAIGN_LEDGER"):
        launch.read_ledger(write_ledger(tmp_path, cap="300.00"))


def test_validate_preflight_rejects_mismatches():
    facts = {"account": plan.RESOURCE_PLAN["account"], "region": plan.RESOURCE_PLAN["region"],
             "ami": plan.RESOURCE_PLAN["ami"], "instance_type": plan.RESOURCE_PLAN["instance_type"],
             "instance_count": 1, "gpu_name_contains": plan.RESOURCE_PLAN["gpu_name_contains"],
             "visible_gpu_count": 1, "t4_rejected": True,
             "rate_ceiling_usd": plan.RESOURCE_PLAN["on_demand_rate_ceiling_usd"],
             "conflicting_resources": []}
    assert launch.validate_preflight(facts) == facts
    for key, value, reason in [("account", "0", "PREFLIGHT_ACCOUNT"),
                               ("instance_type", "t3.micro", "PREFLIGHT_INSTANCE_TYPE"),
                               ("visible_gpu_count", 2, "PREFLIGHT_VISIBLE_GPU_COUNT"),
                               ("t4_rejected", False, "PREFLIGHT_T4"),
                               ("conflicting_resources", ["old-instance"], "PREFLIGHT_CONFLICTING_RESOURCES")]:
        broken = dict(facts)
        broken[key] = value
        with pytest.raises(ValueError, match=reason):
            launch.validate_preflight(broken)


def test_execute_rejects_authority_not_bound_to_owner_approval(ledger):
    authority = valid_authority()
    authority["owner_approval_record_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="OWNER_APPROVAL_RECORD_MISMATCH"):
        launch.execute(valid_request(), authority, FakeProvider(ledger), ledger_path=ledger)


def test_execute_end_to_end_success(ledger):
    provider = FakeProvider(ledger)
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert result["status"] == "AWS_CONDITION_SKILL_V9_FINISHED"
    assert result["reservation"]["reservation"]["status"] == "RESERVED_NO_AUTOMATIC_REFUND"
    assert result["cleanup"]["complete"] is True
    assert result["ledger_after"]["ledger"]["total_reserved_usd"] == "102.00"
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


def test_execute_records_incomplete_cleanup_instead_of_raising(ledger):
    provider = FakeProvider(ledger)
    original = provider.cleanup

    def broken(job):
        original(job)
        return {"complete": False, "failures": ["volume-left-behind"]}

    provider.cleanup = broken
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert result["status"] == "AWS_CONDITION_SKILL_V9_FAILED"
    assert result["cleanup"]["complete"] is False
    assert result["cleanup_incomplete_reason"] == ["volume-left-behind"]


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


def test_read_actual_campaign_ledger_is_read_only():
    before = launch.LEDGER_PATH.read_bytes()
    document = launch.read_ledger()
    assert document["ledger"] == budget.validate_state(budget.decoded(before))
    assert document["ledger_sha256"] == budget.digest(before)
    assert launch.LEDGER_PATH.read_bytes() == before
    assert launch.validate_reservation_scope(document)["campaign_cap"] == "400.00"


def test_old_fabricated_short_ledger_cannot_authorize_spending(tmp_path):
    path = tmp_path / "short.json"
    path.write_text(json.dumps({"revision": 16, "cap_usd": "400.00",
                               "reserved_usd": "98.00", "unreserved_usd": "302.00"}))
    provider = FakeProvider(path)
    with pytest.raises(ValueError, match="INVALID_CAMPAIGN_LEDGER"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=path)
    assert provider.calls == []


def test_inconsistent_totals_cannot_reach_provider(tmp_path):
    path = write_ledger(tmp_path, unreserved="303.00")
    provider = FakeProvider(path)
    with pytest.raises(ValueError, match="INCONSISTENT_CAMPAIGN_TOTALS"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=path)
    assert provider.calls == []


@pytest.mark.parametrize("raw,reason", [
    (b'{"revision":1,"revision":2}', "DUPLICATE_JSON_KEY"),
    (b'{"total_reserved_usd":NaN}', "NONFINITE_JSON"),
])
def test_read_ledger_rejects_ambiguous_json(tmp_path, raw, reason):
    path = tmp_path / "bad.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match=reason):
        launch.read_ledger(path)


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-4", "4e0", 4, True, None, "4.001"])
def test_reservation_amount_uses_exact_decimal_strings(ledger, amount):
    with pytest.raises(ValueError):
        launch.validate_reservation_scope(launch.read_ledger(ledger), amount)


def test_same_job_cannot_run_twice(ledger):
    provider = FakeProvider(ledger)
    launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    before, calls = ledger.read_bytes(), list(provider.calls)
    with pytest.raises(ValueError, match="JOB_ALREADY_RESERVED_NO_AUTOMATIC_RETRY"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert ledger.read_bytes() == before
    assert provider.calls == calls


@pytest.mark.parametrize("mutate,reason", [
    (lambda r: r.update(ledger_sha256="0" * 64), "RESERVATION_RECEIPT_HASH_MISMATCH"),
    (lambda r: r.update(revision=999), "RESERVATION_RECEIPT_FIELD:revision"),
    (lambda r: r.update(total_reserved_usd="98.00"), "RESERVATION_RECEIPT_FIELD:total_reserved_usd"),
    (lambda r: r.update(remaining_unreserved_usd="302.00"), "RESERVATION_RECEIPT_FIELD:remaining_unreserved_usd"),
    (lambda r: r.update(ledger_path="another-ledger.json"), "RESERVATION_RECEIPT_PATH_MISMATCH"),
    (lambda r: r["reservation"].update(job="cas-meta2-not-this-job"), "RESERVATION_RECEIPT_ENTRY_MISMATCH"),
])
def test_changed_receipt_cannot_reach_launch(ledger, mutate, reason):
    provider = FakeProvider(ledger)
    real = provider.reserve
    def reserve(amount):
        receipt = copy.deepcopy(real(amount))
        mutate(receipt)
        return receipt
    provider.reserve = reserve
    with pytest.raises(ValueError, match=reason):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert provider.calls == ["reserve", "cleanup"]
    assert budget.read_ledger(ledger)["total_reserved_usd"] == "102.00"


def test_wrong_job_reservation_cannot_reach_launch(ledger):
    provider = FakeProvider(ledger)
    def reserve(amount):
        provider.calls.append("reserve")
        return budget.reserve_budget("cas-meta2-other-job", "a" * 40, "b" * 64,
                                     amount, budget_plan(), ledger)
    provider.reserve = reserve
    with pytest.raises(ValueError, match="RESERVATION_IDENTITY_MISMATCH:job"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert provider.calls == ["reserve", "cleanup"]


def test_no_ledger_update_cannot_reach_launch(ledger):
    provider = FakeProvider(ledger)
    def reserve(amount):
        provider.calls.append("reserve")
        return {"reservation": {"reserved_usd": amount}}
    provider.reserve = reserve
    with pytest.raises(ValueError, match="RESERVATION_REVISION_MISMATCH"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert provider.calls == ["reserve", "cleanup"]


@pytest.mark.parametrize("change", [
    {"runtime_seconds_max": 1800}, {"instance_type": "g6e.2xlarge"},
    {"task_scope": "some-other-task"}, {"campaign_scope": "some-other-campaign"},
])
def test_other_valid_budget_plan_cannot_authorize_this_job(ledger, change):
    provider = FakeProvider(ledger)
    def reserve(amount):
        provider.calls.append("reserve")
        return budget.reserve_budget(JOB, "a" * 40, "b" * 64, amount,
                                     {**budget_plan(), **change}, ledger)
    provider.reserve = reserve
    with pytest.raises(ValueError, match="RESERVATION_RESOURCE_PLAN_MISMATCH"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert provider.calls == ["reserve", "cleanup"]


@pytest.mark.parametrize("source,archive,reason", [
    ("c" * 40, "b" * 64, "source_sha"), ("a" * 40, "c" * 64, "archive_sha256"),
])
def test_other_source_reservation_cannot_reach_launch(ledger, source, archive, reason):
    provider = FakeProvider(ledger)
    def reserve(amount):
        provider.calls.append("reserve")
        return budget.reserve_budget(JOB, source, archive, amount, budget_plan(), ledger)
    provider.reserve = reserve
    with pytest.raises(ValueError, match="RESERVATION_IDENTITY_MISMATCH:" + reason):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert provider.calls == ["reserve", "cleanup"]


def test_reservation_plan_is_detached_and_cost_bounded():
    snapshot = launch.reservation_plan()
    assert budget.validate_plan(snapshot, "4.00") == budget.amount("4.00")
    snapshot["condition_skill_v9"]["worker_seconds_max"] = 999
    assert launch.reservation_plan()["condition_skill_v9"]["worker_seconds_max"] == 600


def test_existing_receipt_directory_blocks_before_provider_or_reservation(ledger):
    directory = ledger.parent / "already-present"
    directory.mkdir()
    before = ledger.read_bytes()
    provider = FakeProvider(ledger)
    with pytest.raises(ValueError, match="FRESH_RECEIPT_DIRECTORY_REQUIRED"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger,
                       receipt_dir=directory)
    assert ledger.read_bytes() == before
    assert provider.calls == []


def test_launch_identity_and_raw_error_survive_cleanup_exception(ledger):
    provider = FakeProvider(ledger, fail_wait=True)
    provider.cleanup = lambda job: (_ for _ in ()).throw(RuntimeError("cleanup also failed"))
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    directory = Path(result["receipt_dir"])
    saved = json.loads((directory / "result.json").read_bytes())
    assert saved["launch"]["job"] == JOB
    assert saved["outcome"]["exception"] == "INSTANCE_DIED"
    assert "cleanup also failed" in saved["cleanup"]["failures"][0]
    assert json.loads((directory / "failure.json").read_bytes())["exception"] == "INSTANCE_DIED"
    assert (directory / "intent.json").is_file()
    assert (directory / "reservation.json").is_file()


def test_failed_reservation_record_is_durable_and_never_launches(ledger):
    provider = FakeProvider(ledger)
    original = provider.reserve
    def failed(amount):
        receipt = original(amount)
        receipt["aws_side_reservation"] = {"status": "FAILED", "failure": "fixture S3 denial"}
        return receipt
    provider.reserve = failed
    with pytest.raises(ValueError, match="AWS_RESERVATION_RECORD_REQUIRED"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    directory = ledger.parent / ("condition_skill_v9_" + JOB)
    result = json.loads((directory / "result.json").read_bytes())
    assert result["reservation"]["aws_side_reservation"]["failure"] == "fixture S3 denial"
    assert result["launch"] is None
    assert provider.calls == ["reserve", "cleanup"]
    assert launch.read_ledger(ledger)["ledger"]["total_reserved_usd"] == "102.00"


def test_evidence_write_failure_prevents_reservation(ledger, monkeypatch):
    provider = FakeProvider(ledger)
    before = ledger.read_bytes()
    monkeypatch.setattr(launch, "write_evidence", lambda *args: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert ledger.read_bytes() == before
    assert provider.calls == []


def test_keyboard_interrupt_after_launch_is_recorded_and_cleaned(ledger):
    provider = FakeProvider(ledger)
    provider.wait = lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt("stop"))
    result = launch.execute(valid_request(), valid_authority(), provider, ledger_path=ledger)
    assert result["outcome"]["exception_type"] == "KeyboardInterrupt"
    assert result["cleanup"]["complete"] is True
    assert json.loads((Path(result["receipt_dir"]) / "result.json").read_bytes()) == result
