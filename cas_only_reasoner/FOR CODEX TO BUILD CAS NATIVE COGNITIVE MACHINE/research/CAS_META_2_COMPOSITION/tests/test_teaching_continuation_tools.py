"""Fake Git/ledger/package/SDK seams; no real preparation or paid execution."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

from aws import teaching_continuation_launch as launch, teaching_continuation_plan as plan
from aws import teaching_continuation_provider as provider, teaching_continuation_preflight as checks
from cas_meta2.teaching_cycle import evaluation
from tools import prepare_teaching_continuation as prepare
from tools import run_teaching_continuation as run


spec = importlib.util.spec_from_file_location("_continuation_tool_plan_fixtures", Path(__file__).with_name("test_teaching_continuation_plan.py"))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
REAL_ROOT = prepare.ROOT
JOB = "cas-meta2-teaching-20260908120000-1234abcd"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def setup(tmp_path, monkeypatch):
    records = tmp_path / "records/teaching_cycle_001"
    (records / "bundle_002").mkdir(parents=True)
    (records / "bundle_002/training.zip").write_bytes((REAL_ROOT / "records/teaching_cycle_001/bundle_002/training.zip").read_bytes())
    monkeypatch.setattr(prepare, "RECORDS", records)
    monkeypatch.setattr(run, "ROOT", tmp_path)
    git_calls = []
    def fake_git(command, *, cwd, text=False):
        assert cwd == REAL_ROOT
        git_calls.append(command)
        if command == ["git", "rev-parse", "HEAD"]:
            return "e" * 40 + "\n"
        if command == ["git", "rev-parse", "--show-prefix"]:
            return "fixture/\n"
        assert command[:2] == ["git", "show"]
        prefix = "e" * 40 + ":fixture/"
        assert command[2].startswith(prefix)
        return (REAL_ROOT / command[2][len(prefix):]).read_bytes()
    monkeypatch.setattr(prepare.subprocess, "check_output", fake_git)
    continuation = fixtures.continuation()
    continuation.update(prior_package_validator_sha256=digest(REAL_ROOT / "cas_meta2/teaching_cycle/continuation_package.py"),
        restore_probe_sha256=digest(REAL_ROOT / "aws/teaching_cycle_restore_probe.py"),
        continuation_plan_sha256=digest(plan.__file__))
    monkeypatch.setattr(prepare, "_inputs", lambda *_: (deepcopy(continuation), {"synthetic_prior_evidence": "never contacted provider"}))
    ledger = {"binding": fixtures.ledger(), "ledger": {"approval": {"fixture": "existing synthetic400 approval"}, "reservations": []}}
    monkeypatch.setattr(launch, "ledger_snapshot", lambda _: deepcopy(ledger))
    public_raw = (REAL_ROOT / "records/teaching_cycle_001/job_003/public.json").read_bytes()
    def fake_public(material_root, receipt_sha, destination):
        assert material_root == records / "material_001"
        assert receipt_sha == plan.FROZEN_BINDINGS["material_receipt_sha256"]
        with Path(destination).open("xb") as stream:
            stream.write(public_raw)
    monkeypatch.setattr(evaluation, "export_public", fake_public)
    pricing = {"schema": checks.SCHEMA, "account_id": "807562639912", "region": "us-west-2",
        "instance_type": "g7.2xlarge", "source_sha256": digest(checks.__file__),
        "base_preflight_sha256": digest(checks.base.__file__), "plan_sha256": digest(plan.__file__),
        "logical_run_id": plan.LOGICAL_RUN_ID, "restore_proved": False,
        "read_only": True, "reservation_created": False,
        "observed_utc": datetime.now(timezone.utc).isoformat(), "raw_prices": fixtures.prices()}
    pricing["cost_worksheet"] = plan.worksheet(pricing["raw_prices"])
    path = records / "fake_pricing.json"
    path.write_bytes(launch.canonical(pricing))
    return {"records": records, "output": records / "prepared", "pricing": path,
        "pricing_value": pricing, "ledger": ledger, "git_calls": git_calls, "fake_git": fake_git}


def prepared(setup):
    return prepare.prepare(setup["output"], setup["pricing"], job=JOB)


def test_preparation_checks_committed_sources_and_preserves_standing_authority(setup):
    ref = prepared(setup)
    receipt = json.loads(Path(ref["path"]).read_bytes())
    assert receipt["status"] == "PREPARED_NOT_RESERVED_NOT_LAUNCHED"
    assert receipt["new_reservation"] is False and receipt["paid_execution"] is False
    assert receipt["job"] == JOB != receipt["logical_run_id"] == plan.LOGICAL_RUN_ID
    checked = {row[2].split(":fixture/")[1] for row in setup["git_calls"] if row[:2] == ["git", "show"]}
    assert set(provider.DEPENDENCIES) <= checked
    assert prepare.PROPOSAL in checked
    authority = json.loads(Path(receipt["standing_authority"]["path"]).read_bytes())
    assert authority["new_human_approval_claimed"] is False
    assert authority["canonical_approval"] == setup["ledger"]["ledger"]["approval"]
    value, request, envelope = prepare.load_preparation(ref["path"], ref["sha256"])
    assert value == receipt and request["continuation"] == receipt["continuation"]
    assert launch._authority(envelope, request)["reservation_usd"] == "8.00"


def test_working_source_not_in_claimed_commit_is_rejected_before_output(setup, monkeypatch):
    def changed(command, **kwargs):
        if command[:2] == ["git", "show"] and command[2].endswith("tools/run_teaching_continuation.py"):
            return b"Different committed source, not the current file"
        return setup["fake_git"](command, **kwargs)
    monkeypatch.setattr(prepare.subprocess, "check_output", changed)
    with pytest.raises(launch.LaunchError, match="COMMIT_SOURCE_MISMATCH"):
        prepared(setup)
    assert not setup["output"].exists()


def test_missing_new_tool_in_dependency_map_is_rejected(setup, monkeypatch):
    source = provider.source_dependencies()
    del source["tools/run_teaching_continuation.py"]
    monkeypatch.setattr(provider, "source_dependencies", lambda: source)
    with pytest.raises(launch.LaunchError, match="CONTINUATION_TOOLS_MISSING"):
        prepared(setup)


@pytest.mark.parametrize("key,value", [("status", "PREFLIGHT_FAILED"), ("schema", "cas-teaching-live-preflight/1"),
    ("read_only", False), ("reservation_created", True), ("restore_proved", True),
    ("account_id", "000000000000"), ("instance_type", "g4dn.xlarge"),
    ("plan_sha256", "f" * 64), ("source_sha256", "f" * 64), ("base_preflight_sha256", "f" * 64),
    ("logical_run_id", JOB)])
def test_bad_pricing_receipt_never_creates_preparation(setup, key, value):
    changed = deepcopy(setup["pricing_value"])
    changed[key] = value
    setup["pricing"].write_bytes(launch.canonical(changed))
    with pytest.raises(launch.LaunchError, match="SUCCESSFUL_CURRENT_CONTINUATION_PREFLIGHT_REQUIRED"):
        prepared(setup)
    assert not setup["output"].exists()


@pytest.mark.parametrize("age", [-10, 3601])
def test_future_or_stale_pricing_is_rejected(setup, age):
    changed = deepcopy(setup["pricing_value"])
    changed["observed_utc"] = (datetime.now(timezone.utc) - timedelta(seconds=age)).isoformat()
    setup["pricing"].write_bytes(launch.canonical(changed))
    with pytest.raises(launch.LaunchError, match="FRESH_READ_ONLY_PRICING_REQUIRED"):
        prepared(setup)


def test_old_three_gb_worksheet_is_rejected(setup):
    changed = deepcopy(setup["pricing_value"])
    changed["cost_worksheet"] = fixtures.original_worksheet(changed["raw_prices"])
    setup["pricing"].write_bytes(launch.canonical(changed))
    with pytest.raises(launch.LaunchError, match="PREFLIGHT_COST_WORKSHEET_MISMATCH"):
        prepared(setup)


def test_changed_or_resealed_preparation_cannot_reach_provider_factory(setup, monkeypatch):
    ref = prepared(setup)
    called = []
    monkeypatch.setattr(run, "_live_provider", lambda *_: called.append(True))
    with pytest.raises(launch.LaunchError, match="PREPARATION_DIGEST_MISMATCH"):
        run.run(ref["path"], "f" * 64, setup["records"] / "execution")
    assert not called
    setup["ledger"]["binding"]["revision"] += 1
    with pytest.raises(launch.LaunchError, match="STANDING_AUTHORITY_OR_LEDGER_CHANGED"):
        run.run(ref["path"], ref["sha256"], setup["records"] / "execution")
    assert not called


def test_run_inert_without_execute_never_constructs_sdk(monkeypatch, capsys):
    monkeypatch.setattr(run, "_live_provider", lambda *_: pytest.fail("SDK factory called"))
    assert run.main([]) == 0
    assert json.loads(capsys.readouterr().out)["reservation_created"] is False


def test_explicit_run_passes_exact_original_run_prior_paths_and_provider_contract(setup, monkeypatch):
    ref = prepared(setup)
    sent = {}
    adapter = object()
    def factory(receipt, profile):
        sent.update(prepared=receipt, profile=profile)
        return adapter
    def execute(request, authority, provider_object, **kwargs):
        assert provider_object is adapter
        sent.update(request=request, arguments=kwargs)
        return {"status": "TEACHING_CONTINUATION_COLLECTED_NOT_SCORED", "job": request["job"],
            "run_id": request["logical_run_id"], "receipt_dir": str(kwargs["receipt_dir"]),
            "learning_results": "INDEPENDENT_SCORING_REQUIRED"}
    monkeypatch.setattr(run, "_live_provider", factory)
    monkeypatch.setattr(launch, "execute", execute)
    result = run.run(ref["path"], ref["sha256"], setup["records"] / "execution", profile="fake-profile")
    assert sent["profile"] == "fake-profile"
    assert result["run_id"] == plan.LOGICAL_RUN_ID != result["job"]
    assert sent["arguments"]["expected_continuation"] == sent["prepared"]["continuation"]
    assert sent["arguments"]["prior_state_archive_path"] == sent["prepared"]["prior_state_archive_path"]
    assert sent["arguments"]["prior_state_manifest_path"] == sent["prepared"]["prior_state_manifest_path"]


def test_live_factory_uses_actual_constructor_names_but_only_fake_sdk_modules(monkeypatch):
    fake_sdk = ModuleType("botocore")
    fake_errors = ModuleType("botocore.exceptions")
    class FakeClientError(Exception):
        pass
    fake_errors.ClientError = FakeClientError
    monkeypatch.setitem(sys.modules, "botocore", fake_sdk)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", fake_errors)
    clients, captured = {"fake": object()}, {}
    monkeypatch.setattr(provider, "build_clients", lambda profile: clients)
    monkeypatch.setattr(provider, "TeachingContinuationProvider", lambda **kwargs: captured.update(kwargs) or captured)
    receipt = {key: "fake/" + key for key in ("source_archive", "guest_driver", "pricing_receipt_path",
        "base_guest_driver_path", "package_validator_path", "restore_probe_path")}
    run._live_provider(receipt, "fake-profile")
    assert set(captured) == {"clients", "source_archive", "guest_driver", "pricing_receipt_path", "ledger_path",
        "client_error", "base_guest_driver_path", "package_validator_path", "restore_probe_path"}
    assert captured["clients"] is clients and captured["client_error"] is FakeClientError
    assert all(captured[key] == value for key, value in receipt.items())


def test_static_proposal_preserves_allocation_and_warns_of_staged_completion():
    value = json.loads((REAL_ROOT / prepare.PROPOSAL).read_bytes())
    assert value["remaining_optimizer_steps"] == 4 * 896 - sum(value["committed_optimizer_steps"].values()) == 1997
    assert value["remaining_time_estimate_minutes"] == 100 and value["time_estimate_is_guarantee"] is False
    assert value["staged_slices_likely"] is True and value["automatic_retries"] == 0
    prepare._proposal(plan, launch)
