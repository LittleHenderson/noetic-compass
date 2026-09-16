"""Pure package, authority, and worker tests; no tensors or provider calls."""
import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from zipfile import ZipFile

import pytest

from aws import ordered_encoder_launch as launch

JOB = "cas-meta2-orderedencoder-20260916070000-12345678"
SOURCE = "a" * 40


@pytest.fixture(autouse=True)
def pure_inputs(monkeypatch):
    raw = (launch.ROOT / "cas_meta2/__init__.py").read_bytes()
    rows = [{"path": "cas_meta2/__init__.py", "bytes": len(raw), "sha256": launch.digest(raw)}]
    monkeypatch.setattr(launch, "_probe", lambda: SimpleNamespace(input_inventory=lambda root: copy.deepcopy(rows)))


def authority():
    return {"schema": launch.AUTHORITY_SCHEMA, "candidate": launch.CANDIDATE,
        "job": JOB, "source_sha": SOURCE, "archive_sha256": "b" * 64, "manifest_sha256": "c" * 64,
        "owner_authorization_sha256": "d" * 64, **launch.BOUNDS,
        "inputs_sha256": launch.frozen_inputs_hash(),
        "design_sha256": launch.digest(launch.canonical(launch.DESIGN)),
        "evidence_contract_sha256": launch.run_evidence.contract_digest(launch.evidence_contract()),
        "worker_config": launch.worker_config(JOB, source_sha=SOURCE)}


def request(auth):
    return {"schema": launch.REQUEST_SCHEMA, "launch_authorized": False,
        **{key: auth[key] for key in ("job", "source_sha", "archive_sha256", "manifest_sha256")}}


def owner_file(tmp_path, auth, **changes):
    owner = {"schema": launch.OWNER_SCHEMA, "candidate": launch.CANDIDATE,
             "owner_instruction_raw": "TEST FIXTURE ONLY: one bounded diagnostic.",
             "bounds": copy.deepcopy(launch.BOUNDS), **changes}
    path = tmp_path / "owner.json"
    raw = launch.canonical(owner)
    path.write_bytes(raw)
    auth["owner_authorization_sha256"] = launch.digest(raw)
    return path


def test_default_is_inert_and_has_no_client_creation(monkeypatch, capsys):
    clients = Mock(side_effect=AssertionError("Provider creation forbidden in plan mode"))
    monkeypatch.setattr(launch.lifecycle, "_clients", clients)
    assert launch.main([]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["provider_calls"] == 0 and plan["reservation_created"] is False
    assert plan["design"]["training"] is False
    clients.assert_not_called()


@pytest.mark.parametrize("key,value", [("training", True), ("optimizer_updates", 1),
    ("optimizer_updates", False), ("max_wall_seconds", 1200.0), ("max_wall_seconds", 1201),
    ("jobs", 2), ("jobs", True), ("automatic_retries", 1), ("reservation_usd", "8.00"),
    ("instance_type", "g4dn.xlarge"), ("region", "us-east-1"),
    ("inputs_sha256", "0" * 64), ("design_sha256", "0" * 64),
    ("evidence_contract_sha256", "0" * 64), ("source_sha", "broken"),
    ("owner_authorization_sha256", False)])
def test_top_authority_is_exact(key, value):
    auth = authority()
    launch.validate_authority(auth)
    auth[key] = value
    with pytest.raises(ValueError, match="ORDERED_"):
        launch.validate_authority(auth)


@pytest.mark.parametrize("key,value", [("training", True), ("optimizer_updates", False),
    ("max_wall_seconds", 1200.0), ("probe_seed", 2), ("source_sha", "e" * 40),
    ("candidate", "CAS_RDCJT_001"), ("inputs", []), ("inputs_sha256", "0" * 64),
    ("execution_design", {})])
def test_nested_config_cannot_change_execution(key, value):
    auth = authority()
    auth["worker_config"][key] = value
    with pytest.raises(ValueError, match="ORDERED_AUTHORITY_CONFIG"):
        launch.validate_authority(auth)


def test_request_cannot_enable_execution_or_use_previous_job_namespace():
    req = request(authority())
    launch.validate_request(req)
    req["job"] = JOB.replace("orderedencoder", "graph6contrast")
    with pytest.raises(ValueError, match="ORDERED_REQUEST_JOB"):
        launch.validate_request(req)
    req = request(authority())
    req["launch_authorized"] = True
    with pytest.raises(ValueError, match="ORDERED_REQUEST_INERT"):
        launch.validate_request(req)


@pytest.mark.parametrize("change", [{"owner_instruction_raw": " "},
    {"owner_instruction_raw": True}, {"candidate": "CAS_RDCJT_001"},
    {"bounds": {**launch.BOUNDS, "jobs": 2}}, {"bounds": {**launch.BOUNDS, "training": True}}])
def test_invalid_owner_fails_before_provider_binding_or_lifecycle(tmp_path, monkeypatch, change):
    auth = authority()
    path = owner_file(tmp_path, auth, **change)
    provider, execute = Mock(), Mock(side_effect=AssertionError("Lifecycle forbidden"))
    monkeypatch.setattr(launch.lifecycle, "execute", execute)
    with pytest.raises(ValueError, match="ORDERED_OWNER_"):
        launch.execute(request(auth), auth, provider, receipt_dir=tmp_path / "receipts",
                       owner_authorization_path=path, ledger_path=tmp_path / "unused.json")
    provider.bind_authority.assert_not_called()
    execute.assert_not_called()


def test_owner_bytes_and_request_file_hashes_are_checked_before_clients(tmp_path, monkeypatch):
    auth = authority()
    path = owner_file(tmp_path, auth)
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="ORDERED_OWNER_FILE_HASH"):
        launch.validate_owner(path, auth)
    req_path, auth_path = tmp_path / "request.json", tmp_path / "authority.json"
    req_path.write_bytes(launch.canonical(request(auth)))
    auth_path.write_bytes(launch.canonical(auth))
    clients = Mock(side_effect=AssertionError("Client creation forbidden"))
    monkeypatch.setattr(launch.lifecycle, "_clients", clients)
    with pytest.raises(ValueError, match="ORDERED_REQUEST_AUTHORITY_FILE_HASH"):
        launch.main(["--execute", "--request", str(req_path), "--request-sha256", "0" * 64,
            "--authority", str(auth_path), "--authority-sha256", "0" * 64,
            "--receipt-dir", str(tmp_path / "receipts"), "--owner-authorization", str(path),
            "--ledger-path", str(tmp_path / "unused.json")])
    clients.assert_not_called()


def test_provider_requires_bound_exact_identity_and_preserves_nested_config():
    auth = authority()
    provider = launch.OrderedEncoderProvider(job=JOB, source_sha=SOURCE,
        archive_sha256="b" * 64, manifest_sha256="c" * 64, clients={}, ledger_path=Path("unused"))
    with pytest.raises(ValueError, match="ORDERED_AUTHORITY_NOT_BOUND"):
        provider._worker_config("bucket")
    provider.bind_authority(auth)
    config = provider._worker_config("actual-bucket")
    assert config == {**auth["worker_config"], "bucket": "actual-bucket"}
    assert provider.worker_name == launch.WORKER_NAME
    assert provider.result_schema == launch.RESULT_SCHEMA
    assert "ORDERED_ENCODER_DIAGNOSTIC_FAILED" in provider.failure_statuses
    config["inputs"].clear()
    assert provider._worker_config("actual-bucket")["inputs"]
    auth["source_sha"] = "f" * 40
    auth["worker_config"]["source_sha"] = "f" * 40
    with pytest.raises(ValueError, match="ORDERED_PROVIDER_BINDING:source_sha"):
        provider.bind_authority(auth)


def test_execute_reuses_exact_common_lifecycle_and_contract(tmp_path, monkeypatch):
    auth = authority()
    owner = owner_file(tmp_path, auth)
    provider = Mock()
    ledger = tmp_path / "ledger.json"
    ledger.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(launch, "WORKSPACE_HOME", tmp_path)
    provider.ledger_path = ledger
    inherited = Mock(return_value={"status": "FAKE_TEST_ONLY"})
    monkeypatch.setattr(launch.lifecycle, "execute", inherited)
    assert launch.execute(request(auth), auth, provider, receipt_dir=tmp_path / "receipts",
                          owner_authorization_path=owner, ledger_path=ledger)["status"] == "FAKE_TEST_ONLY"
    provider.bind_authority.assert_called_once_with(auth)
    assert inherited.call_args.kwargs["validate_authority_fn"] is launch.validate_authority
    assert inherited.call_args.kwargs["evidence_contract"] == launch.evidence_contract()
    assert inherited.call_args.kwargs["ledger_path"] == ledger.resolve()


def test_ledger_must_be_explicit_scoped_and_match_provider(tmp_path, monkeypatch):
    auth = authority()
    owner = owner_file(tmp_path, auth)
    allowed = tmp_path / "home"
    allowed.mkdir()
    ledger = allowed / "ledger.json"
    ledger.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(launch, "WORKSPACE_HOME", allowed)
    with pytest.raises(ValueError, match="ORDERED_LEDGER_HOMEBASE_FILE"):
        launch.validate_ledger_path(owner)
    provider = Mock(ledger_path=allowed / "different.json")
    inherited = Mock(side_effect=AssertionError("Lifecycle forbidden"))
    monkeypatch.setattr(launch.lifecycle, "execute", inherited)
    with pytest.raises(ValueError, match="ORDERED_PROVIDER_LEDGER_MISMATCH"):
        launch.execute(request(auth), auth, provider, receipt_dir=tmp_path / "receipts",
                       owner_authorization_path=owner, ledger_path=ledger)
    provider.bind_authority.assert_not_called()
    inherited.assert_not_called()
    with pytest.raises(ValueError, match="ORDERED_EXPLICIT_INPUTS"):
        launch.main(["--execute"])


def test_rendered_worker_dispatch_timeout_and_collection_contract():
    source = launch.render_worker()
    tree = ast.parse(source)
    compile(tree, "<worker>", "exec")
    names = {"INNER_RUNNER", "RESULT_SCHEMA", "FAILURE_SCHEMA", "MAX_WALL_SECONDS"}
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id in names}
    assert constants["RESULT_SCHEMA"] == launch.RESULT_SCHEMA
    assert constants["FAILURE_SCHEMA"] == launch.FAILURE_SCHEMA
    assert constants["MAX_WALL_SECONDS"] == 1200
    inner = constants["INNER_RUNNER"]
    compile(inner, "<inner>", "exec")
    assert "ordered_encoder_probe.run" in inner
    assert "contrast_readout" not in inner and "recurrent_cjt" not in inner
    assert "timeout=MAX_WALL_SECONDS)" in source
    assert "MAX_WALL_SECONDS + 1800" not in source
    required = {item["key"] for item in launch.evidence_contract()["required"]}
    assert required == {"results/result.json", "results/result.json.sha256",
        "results/artifacts/manifest.json", "results/artifacts/encoder_probe.json",
        "results/artifacts/measurements.json"}


def test_package_committed_members_zero_budget_and_no_checkpoints(tmp_path, monkeypatch):
    actual_root = launch.ROOT
    source_home = actual_root.parents[1]
    fake_root = tmp_path / "pilot"
    (fake_root / "records").mkdir(parents=True)
    for name in launch.PACKAGING_SOURCES:
        target = fake_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((actual_root / name).read_bytes())
    monkeypatch.setattr(launch, "ROOT", fake_root)
    def get_bytes(root, sha, name):
        assert sha == SOURCE
        return (source_home / name).read_bytes()
    def get_paths(root, sha, directory):
        return sorted(path.relative_to(source_home).as_posix()
                      for path in (source_home / directory).rglob("*.py"))
    receipt = launch.build_ordered_package(fake_root / "records" / "package", source_sha=SOURCE,
                                           git_bytes_fn=get_bytes, git_paths_fn=get_paths)
    assert receipt["manifest"]["training"] is False
    assert receipt["manifest"]["frozen_budget"]["optimizer_updates"] == 0
    assert receipt["manifest"]["frozen_budget"]["checkpoints"] == 0
    assert receipt["manifest"]["experiment"]["entrypoint"] == launch.EXPERIMENT["entrypoint"]
    with ZipFile(receipt["archive"]) as archive:
        assert not any(name.endswith((".pt", ".bundle")) for name in archive.namelist())
        for name, expected in receipt["manifest"]["files_sha256"].items():
            assert launch.digest(archive.read(name)) == expected
        worker = archive.read(launch.WORKER_NAME).decode()
        assert "ordered_encoder_probe.run" in worker
        compile(worker, "<packaged-worker>", "exec")
    (fake_root / launch.PACKAGING_SOURCES[0]).write_text("# changed", encoding="utf-8")
    with pytest.raises(ValueError, match="ORDERED_PACKAGING_SOURCE_NOT_COMMITTED"):
        launch.build_ordered_package(fake_root / "records" / "changed", source_sha=SOURCE,
                                    git_bytes_fn=get_bytes, git_paths_fn=get_paths)
