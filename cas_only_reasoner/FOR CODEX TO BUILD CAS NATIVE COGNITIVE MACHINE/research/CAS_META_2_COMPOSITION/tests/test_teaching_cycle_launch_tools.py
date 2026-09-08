"""The public command is inert by default and preparation cannot import CUDA."""
import ast
import builtins
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location("test_" + name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_default_has_no_provider_or_sdk_effect(capsys, monkeypatch):
    import builtins
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.startswith(("aws", "boto3", "botocore", "torch", "numpy", "sqlite3")):
            raise AssertionError("Default command must not import provider/runtime: " + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)
    assert load_tool("run_teaching_launch").main([]) == 0
    assert '"reservation_created": false' in capsys.readouterr().out


@pytest.mark.parametrize("name", ["torch", "numpy", "sqlite3", "boto3", "botocore", "casformer", "cas_cjt"])
def test_preparation_explicitly_blocks_runtime(name):
    module = load_tool("prepare_teaching_launch")
    with pytest.raises(RuntimeError, match="PREPARE_ONLY_FORBIDDEN_IMPORT"):
        module.Guard().find_spec(name)


def test_entrypoints_are_explicit_and_no_top_level_execution():
    for name in ("prepare_teaching_launch", "run_teaching_launch"):
        tree = ast.parse((ROOT / "tools" / (name + ".py")).read_text())
        assert any(isinstance(node, ast.If) and "__name__" in ast.unparse(node.test) for node in tree.body)
        assert not any(isinstance(node, ast.Import) and any(item.name in {"torch", "boto3", "numpy"}
            for item in node.names) for node in tree.body)


@pytest.fixture
def preparation(tmp_path, monkeypatch):
    from aws import budget, teaching_cycle_launch as launch, teaching_cycle_provider as provider
    from aws import teaching_cycle_preflight as checks
    module = load_tool("prepare_teaching_launch")
    # The tool's git calls remain real and read-only against the current HEAD.
    source_name = "cas_meta2/codec.py"
    source_map = {source_name: sha256((ROOT / source_name).read_bytes()).hexdigest()}
    monkeypatch.setattr(provider, "source_dependencies", lambda: source_map.copy())
    records = tmp_path / "records"
    records.mkdir()
    monkeypatch.setattr(module, "RECORDS", records)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "meta_path", list(sys.meta_path))
    original = ROOT / "records/teaching_cycle_001"
    (records / "bundle_002").mkdir()
    shutil.copyfile(original / "bundle_002/training.zip", records / "bundle_002/training.zip")
    (records / "material_001").mkdir()
    shutil.copyfile(original / "material_001/preparation_receipt.json", records / "material_001/preparation_receipt.json")
    shutil.copytree(original / "material_001/evaluation_public", records / "material_001/evaluation_public")
    # Deliberately no evaluator_private directory in this test material.
    shutil.copyfile(original / "LAUNCH_PROPOSAL.json", records / "LAUNCH_PROPOSAL.json")
    ledger = tmp_path / "ledger.json"
    shutil.copyfile(budget.CANONICAL_LEDGER, ledger)
    shutil.copytree(budget.CANONICAL_LEDGER.with_suffix(".json.history"), ledger.with_suffix(".json.history"))
    monkeypatch.setattr(budget, "CANONICAL_LEDGER", ledger)
    rates = {"compute": "2.00", "ebs": "0.08", "ipv4": "0.005", "s3_storage": "0.023",
             "s3_put": "0.000005", "s3_get": "0.0000004", "egress": "0.09"}
    prices = {name: {"PriceList": [json.dumps({"terms": {"OnDemand": {"synthetic": {
        "priceDimensions": {"synthetic": {"unit": definition[2], "pricePerUnit": {"USD": rates[name]}}}}}}})]}
        for name, definition in checks.PRICE_QUERIES.items()}
    pricing = {"schema": "cas-teaching-live-preflight/1", "observed_utc": datetime.now(timezone.utc).isoformat(),
               "account_id": checks.ACCOUNT, "region": checks.REGION, "instance_type": checks.INSTANCE,
               "source_sha256": sha256(Path(checks.__file__).read_bytes()).hexdigest(),
               "read_only": True, "reservation_created": False,
               "raw_prices": prices, "cost_worksheet": checks.worksheet(prices)}
    path = tmp_path / "pricing.json"
    path.write_bytes(launch.canonical(pricing))
    return SimpleNamespace(module=module, records=records, output=records / "prepared", pricing_path=path,
        pricing=pricing, source_map=source_map, ledger=ledger, ledger_before=ledger.read_bytes(),
        job="cas-meta2-teaching-20260908000000-abcdef12")


def prepare_fixture(value):
    receipt = value.module.prepare(value.output, value.pricing_path, job=value.job)
    return receipt, json.loads(Path(receipt["path"]).read_bytes())


def test_prepare_uses_real_committed_source_queries_and_complete_bound_records(preparation, monkeypatch):
    from aws import teaching_cycle_launch as launch, teaching_cycle_plan as plan
    actual = preparation.module.subprocess.check_output
    commands = []
    def read_only_git(command, **kwargs):
        assert command[0] == "git" and command[1] in ("rev-parse", "show")
        assert kwargs["cwd"] == ROOT
        commands.append(command)
        return actual(command, **kwargs)
    monkeypatch.setattr(preparation.module.subprocess, "check_output", read_only_git)
    receipt, prepared = prepare_fixture(preparation)
    assert [command[1] for command in commands] == ["rev-parse", "rev-parse", "show"]
    assert ":" in commands[-1][2] and commands[-1][2].endswith("cas_meta2/codec.py")
    assert prepared["transport_source_commit"] == actual(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert prepared["new_reservation"] is prepared["paid_execution"] is prepared["private_targets_opened"] is False
    assert preparation.ledger.read_bytes() == preparation.ledger_before
    request = json.loads(Path(prepared["request"]["path"]).read_bytes())
    plan.validate_request(request, expected_bindings=prepared["bindings"], expected_ledger=prepared["ledger"])
    raw = Path(prepared["authority"]["path"]).read_bytes()
    launch._authority({"raw_utf8": raw.decode(), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}, request)
    standing = json.loads(Path(prepared["standing_authority"]["path"]).read_bytes())
    assert standing["new_human_approval_claimed"] is False
    assert len(json.loads(Path(prepared["public_sets_path"]).read_bytes())["test_fresh"]) == 64
    assert receipt["sha256"] == sha256(Path(receipt["path"]).read_bytes()).hexdigest()


def test_prepare_refuses_uncommitted_source_bytes_before_creating_output(preparation):
    preparation.source_map["cas_meta2/codec.py"] = "8" * 64
    with pytest.raises(ValueError, match="COMMIT_SOURCE_MISMATCH"):
        prepare_fixture(preparation)
    assert not preparation.output.exists()
    assert preparation.ledger.read_bytes() == preparation.ledger_before


@pytest.mark.parametrize("change,reason", [
    ("failed", "SUCCESSFUL_CURRENT_PREFLIGHT_REQUIRED"),
    ("account", "SUCCESSFUL_CURRENT_PREFLIGHT_REQUIRED"),
    ("region", "SUCCESSFUL_CURRENT_PREFLIGHT_REQUIRED"),
    ("instance", "SUCCESSFUL_CURRENT_PREFLIGHT_REQUIRED"),
    ("source", "SUCCESSFUL_CURRENT_PREFLIGHT_REQUIRED"),
    ("worksheet", "PREFLIGHT_COST_WORKSHEET_MISMATCH"),
    ("stale", "FRESH_READ_ONLY_PRICING_REQUIRED"),
    ("already_reserved", "FRESH_READ_ONLY_PRICING_REQUIRED"),
])
def test_failed_stale_or_mismatched_pricing_never_prepares(preparation, change, reason):
    from aws import teaching_cycle_launch as launch
    updates = {"failed": {"status": "PREFLIGHT_FAILED"}, "account": {"account_id": "000000000000"},
        "region": {"region": "us-east-1"}, "instance": {"instance_type": "g4dn.xlarge"},
        "source": {"source_sha256": "8" * 64}, "worksheet": {"cost_worksheet": {}},
        "stale": {"observed_utc": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()},
        "already_reserved": {"reservation_created": True}}
    preparation.pricing.update(updates[change])
    preparation.pricing_path.write_bytes(launch.canonical(preparation.pricing))
    with pytest.raises(ValueError, match=reason):
        prepare_fixture(preparation)
    assert not preparation.output.exists()
    assert preparation.ledger.read_bytes() == preparation.ledger_before


def fake_sdk(monkeypatch, calls):
    """Intercept imports without importing or installing fake SDK modules."""
    original = builtins.__import__
    class ClientError(Exception):
        pass
    class Config:
        def __init__(self, **kwargs):
            self.values = kwargs
            calls.append(("config", kwargs))
    class Session:
        def __init__(self, **kwargs):
            calls.append(("session", kwargs))
        def client(self, name, **kwargs):
            calls.append(("client", name, kwargs))
            return SimpleNamespace(service_name=name, settings=kwargs)
    def imported(name, *args, **kwargs):
        if name == "boto3":
            return SimpleNamespace(Session=Session)
        if name == "botocore.config":
            return SimpleNamespace(Config=Config)
        if name == "botocore.exceptions":
            return SimpleNamespace(ClientError=ClientError)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", imported)
    return ClientError


def test_execute_cli_constructs_actual_provider_and_passes_every_bound_input(preparation, monkeypatch, capsys):
    from aws import teaching_cycle_launch as launch, teaching_cycle_provider as provider
    receipt, prepared = prepare_fixture(preparation)
    calls = []
    client_error = fake_sdk(monkeypatch, calls)
    executions = []
    def execute(request, authority, adapter, **kwargs):
        assert isinstance(adapter, provider.TeachingCycleProvider)
        assert adapter.source_archive_path == prepared["source_archive"]
        assert adapter.guest_driver_path == prepared["guest_driver"]
        assert adapter.pricing_receipt_path == prepared["pricing_receipt_path"]
        assert adapter.teaching_ledger_path == preparation.ledger
        assert adapter.teaching_error is client_error
        assert set(adapter.raw_clients) == {"sts", "ec2", "s3", "iam", "scheduler", "service-quotas", "pricing"}
        assert kwargs["expected_bindings"] == prepared["bindings"] and kwargs["expected_ledger"] == prepared["ledger"]
        assert kwargs["public_sets_path"] == prepared["public_sets_path"]
        launch._authority(authority, request)
        executions.append((request, kwargs))
        return {"status": "TEACHING_CYCLE_COLLECTED_NOT_SCORED", "receipt_dir": kwargs["receipt_dir"],
                "job": request["job"], "learning_results": "SYNTHETIC_CLI_ONLY"}
    monkeypatch.setattr(launch, "execute", execute)
    module = load_tool("run_teaching_launch")
    assert module.main(["--execute", "--preparation", receipt["path"], "--preparation-sha256", receipt["sha256"],
                        "--receipt-dir", str(preparation.records / "run"), "--profile", "fake-test-profile"]) == 0
    assert len(executions) == 1 and preparation.ledger.read_bytes() == preparation.ledger_before
    assert ("session", {"profile_name": "fake-test-profile", "region_name": "us-west-2"}) in calls
    price_client = next(row for row in calls if row[0] == "client" and row[1] == "pricing")
    assert price_client[2]["region_name"] == "us-east-1"
    assert not {"boto3", "botocore"}.intersection(sys.modules)
    assert "SYNTHETIC_CLI_ONLY" in capsys.readouterr().out


@pytest.mark.parametrize("target", ["preparation", "request", "authority", "provider_sources", "source_map"])
def test_changed_preparation_bindings_stop_before_sdk_import(preparation, monkeypatch, target):
    from aws import teaching_cycle_provider as provider
    receipt, prepared = prepare_fixture(preparation)
    if target == "source_map":
        monkeypatch.setattr(provider, "source_dependencies", lambda: {"changed": "8" * 64})
    else:
        path = Path(receipt["path"] if target == "preparation" else prepared[target]["path"])
        path.write_bytes(path.read_bytes() + b" ")
    original = builtins.__import__
    def no_sdk(name, *args, **kwargs):
        assert name not in {"boto3", "botocore.config", "botocore.exceptions"}, "Invalid preparation reached SDK import"
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_sdk)
    with pytest.raises(ValueError):
        load_tool("run_teaching_launch").main(["--execute", "--preparation", receipt["path"],
            "--preparation-sha256", receipt["sha256"], "--receipt-dir", str(preparation.records / "run")])
    assert preparation.ledger.read_bytes() == preparation.ledger_before
