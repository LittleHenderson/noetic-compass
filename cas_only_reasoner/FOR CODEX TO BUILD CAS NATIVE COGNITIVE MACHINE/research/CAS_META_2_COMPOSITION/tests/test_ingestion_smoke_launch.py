"""Pure candidate binding/package tests; no credentials, SDK or neural runtime."""
import ast
import builtins
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest

from aws import ingestion_smoke_launch as launch

JOB = "cas-meta2-ingestionsmoke-20260916000000-12345678"
SOURCE = "a" * 40


@pytest.fixture(autouse=True)
def forbid_execution_imports(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer", "transformers", "safetensors"}:
            raise AssertionError("PROHIBITED_TEST_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture
def authority():
    return {"schema": launch.AUTHORITY_SCHEMA, "candidate": launch.CANDIDATE,
        "job": JOB, "source_sha": SOURCE, "archive_sha256": "b" * 64,
        "manifest_sha256": "c" * 64, "owner_authorization_sha256": "d" * 64,
        **launch.BOUNDS, "inputs_sha256": launch.frozen_inputs_hash(),
        "design_sha256": launch.digest(launch.canonical(launch.DESIGN)),
        "evidence_contract_sha256": launch.run_evidence.contract_digest(launch.evidence_contract()),
        "worker_config": launch.worker_config(JOB, source_sha=SOURCE)}


def request(authority):
    return {"schema": launch.REQUEST_SCHEMA, "launch_authorized": False,
            **{k: authority[k] for k in ("job", "source_sha", "archive_sha256", "manifest_sha256")}}


def test_actual_worker_config_is_accepted_by_worker(authority):
    assert launch.validate_authority(authority) is authority
    config = {**authority["worker_config"], "bucket": "smoke-test-bucket"}
    assert launch.worker.validate_config(config, launch.PROJECT) is config
    assert len(config["material"]["training_requests"]) == 3
    assert len(config["material"]["prediction_requests"]) == 6


@pytest.mark.parametrize("key,value", [("unexpected", 1), ("launch_authorized", True),
    ("launch_authorized", 0), ("schema", "wrong"), ("source_sha", "a" * 39),
    ("archive_sha256", False), ("job", JOB.replace("ingestionsmoke", "orderedencoder"))])
def test_request_is_closed_inert_and_candidate_specific(authority, key, value):
    req = request(authority)
    launch.validate_request(req)
    req[key] = value
    with pytest.raises(ValueError, match="INGESTION_REQUEST_"):
        launch.validate_request(req)


@pytest.mark.parametrize("key,value", [("unknown", 1), ("training", 1),
    ("optimizer_updates_max", 64.0), ("optimizer_updates_max", 65),
    ("max_wall_seconds", 1200.0), ("jobs", True), ("automatic_retries", 1),
    ("reservation_usd", "8.00"), ("region", "us-east-1"),
    ("inputs_sha256", "0" * 64), ("design_sha256", "0" * 64),
    ("evidence_contract_sha256", "0" * 64), ("owner_authorization_sha256", False)])
def test_authority_closes_numeric_aliases_and_all_bindings(authority, key, value):
    authority[key] = value
    with pytest.raises(ValueError, match="INGESTION_"):
        launch.validate_authority(authority)


@pytest.mark.parametrize("key,value", [("unknown", 1), ("training", 1),
    ("optimizer_updates_max", 64.0), ("source_sha", "e" * 40),
    ("inputs", []), ("material", {}), ("execution_design", {})])
def test_nested_config_cannot_diverge_from_authority(authority, key, value):
    authority["worker_config"][key] = value
    with pytest.raises(ValueError, match="INGESTION_AUTHORITY_CONFIG"):
        launch.validate_authority(authority)


def test_default_plan_never_constructs_provider_clients(monkeypatch, capsys):
    clients = Mock(side_effect=AssertionError("Provider import forbidden"))
    monkeypatch.setattr(launch.lifecycle, "_clients", clients)
    assert launch.main([]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "PLAN_ONLY"
    assert output["provider_calls"] == 0 and output["reservation_created"] is False
    clients.assert_not_called()


def test_owner_disagreement_refused_before_lifecycle(authority, tmp_path, monkeypatch):
    owner = {"schema": launch.OWNER_SCHEMA, "candidate": launch.CANDIDATE,
        "owner_instruction_raw": "EXPLICIT TEST FIXTURE ONLY",
        "bounds": {**launch.BOUNDS, "training": False}}
    path = tmp_path / "owner.json"
    path.write_bytes(launch.canonical(owner))
    authority["owner_authorization_sha256"] = launch.digest(path.read_bytes())
    inherited = Mock(side_effect=AssertionError("Lifecycle forbidden"))
    provider = Mock()
    monkeypatch.setattr(launch.lifecycle, "execute", inherited)
    with pytest.raises(ValueError, match="INGESTION_OWNER_BOUND"):
        launch.execute(request(authority), authority, provider,
            receipt_dir=tmp_path / "receipts", owner_authorization_path=path,
            ledger_path=tmp_path / "unused.json")
    inherited.assert_not_called()
    provider.bind_authority.assert_not_called()


def test_provider_adds_only_bucket_and_retains_closed_config(authority):
    provider = launch.IngestionSmokeProvider(job=JOB, source_sha=SOURCE,
        archive_sha256="b" * 64, manifest_sha256="c" * 64,
        clients={}, ledger_path=Path("UNUSED_TEST_LEDGER"))
    with pytest.raises(ValueError, match="INGESTION_AUTHORITY_NOT_BOUND"):
        provider._worker_config("test-bucket")
    provider.bind_authority(authority)
    config = provider._worker_config("test-bucket")
    assert config == {**authority["worker_config"], "bucket": "test-bucket"}
    config["material"]["training_requests"].clear()
    assert len(provider._worker_config("test-bucket")["material"]["training_requests"]) == 3
    assert provider.worker_name == launch.WORKER_NAME
    assert provider.result_schema == launch.RESULT_SCHEMA
    assert "INGESTION_SMOKE_FAILED" in provider.failure_statuses


def test_rendered_actual_subprocess_timeout_paths_and_exact_evidence_contract():
    source = launch.render_worker()
    tree = ast.parse(source)
    compile(tree, "<test-only-worker>", "exec")
    relevant = {"INNER_RUNNER", "MAX_WALL_SECONDS", "RESULT_SCHEMA", "FAILURE_SCHEMA"}
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
        if isinstance(n, ast.Assign) and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name) and n.targets[0].id in relevant}
    assert constants["MAX_WALL_SECONDS"] == 1200
    assert constants["RESULT_SCHEMA"] == launch.RESULT_SCHEMA
    assert constants["FAILURE_SCHEMA"] == launch.FAILURE_SCHEMA
    timeouts = [k.value for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and ast.unparse(n.func) == "subprocess.run"
                for k in n.keywords if k.arg == "timeout"]
    assert len(timeouts) == 1 and ast.unparse(timeouts[0]) == "MAX_WALL_SECONDS"
    inner = ast.parse(constants["INNER_RUNNER"])
    compile(inner, "<test-only-inner>", "exec")
    paths = [ast.unparse(n.args[1]) for n in ast.walk(inner)
             if isinstance(n, ast.Call) and ast.unparse(n.func) == "sys.path.insert"]
    assert "str(ROOT)" in paths
    assert "str(ROOT / 'research/CAS_META_2_COMPOSITION')" in paths
    assert any(isinstance(n, ast.Call) and ast.unparse(n.func) == "rpa_learning_worker.run" for n in ast.walk(inner))
    expected = {"origin.pt", "initial.pt", "final.pt", "initial_checkpoint.json", "final_checkpoint.json",
        "before_predictions.json", "after_predictions.json", "initial_reload_predictions.json",
        "final_reload_predictions.json", "receipt.json", "installed_sources.json", "worker_report.json", "measurements.json", "manifest.json"}
    contract = launch.evidence_contract()
    required = {x["key"] for x in contract["required"]}
    assert required == {"results/result.json", "results/result.json.sha256"} | {"results/artifacts/" + n for n in expected}


def package_fixture(tmp_path, monkeypatch):
    actual = launch.ROOT
    project = launch.PROJECT
    fake = tmp_path / "pilot"
    (fake / "records").mkdir(parents=True)
    for name in launch.PACKAGING_SOURCES:
        p = fake / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((actual / name).read_bytes())
    monkeypatch.setattr(launch, "ROOT", fake)
    def get_bytes(root, commit, name):
        assert commit == SOURCE
        return (project / name).read_bytes()
    def get_paths(root, commit, prefix):
        assert commit == SOURCE
        return sorted(p.relative_to(project).as_posix() for p in (project / prefix).rglob("*.py"))
    return fake, get_bytes, get_paths


def test_package_contains_exact_exposed_fixture_sources_and_hashes(tmp_path, monkeypatch):
    fake, get_bytes, get_paths = package_fixture(tmp_path, monkeypatch)
    receipt = launch.build_smoke_package(fake / "records/package", source_sha=SOURCE,
        git_bytes_fn=get_bytes, git_paths_fn=get_paths)
    with ZipFile(receipt["archive"]) as archive:
        names = set(archive.namelist())
        assert {launch.worker.FIXTURE, "cncm/rpa_learning_worker.py", "cncm/rpa_learning_smoke.py", launch.WORKER_NAME} <= names
        assert not any(n.endswith(".pt") or n.endswith("data_manifest.json") for n in names)
        assert sha256(archive.read(launch.worker.FIXTURE)).hexdigest() == launch.worker.FIXTURE_SHA
        for name, expected in receipt["manifest"]["files_sha256"].items():
            assert sha256(archive.read(name)).hexdigest() == expected
    assert receipt["manifest"]["frozen_budget"]["optimizer_updates_max"] == 64
    assert receipt["manifest"]["frozen_budget"]["reload_phases"] == 2


@pytest.mark.parametrize("changed", ["cncm/rpa_learning_worker.py", "research/CAS_META_2_COMPOSITION/aws/ingestion_smoke_launch.py"])
def test_uncommitted_source_refused_before_package_creation(tmp_path, monkeypatch, changed):
    fake, get_bytes, get_paths = package_fixture(tmp_path, monkeypatch)
    def changed_bytes(root, commit, name):
        raw = get_bytes(root, commit, name)
        return raw + b"\n# UNCOMMITTED TEST CHANGE\n" if name == changed else raw
    output = fake / "records/package"
    with pytest.raises(ValueError, match="INGESTION_(INPUT|PACKAGING_SOURCE)_NOT_COMMITTED"):
        launch.build_smoke_package(output, source_sha=SOURCE,
            git_bytes_fn=changed_bytes, git_paths_fn=get_paths)
    assert not output.exists()


# This immutable commit actually contains the new CNCM sources. Earlier package
# tests replaced git_bytes entirely, so they missed its research-only scope.
PACKAGE_REGRESSION_COMMIT = "8697c6ff761d33a33ed489a11f6407ca095d602c"


@pytest.mark.parametrize("name,size,expected_sha256", [
    ("cncm/canonical.py", 1696, "424323335452fecd26cd6659136475c0fd19bda695ab07811d34d1734564877a"),
    ("cncm/rpa_learning_smoke.py", 27547, "19c3f5d1a2eb105b48f5b6d8398096e85e3bdf9d962169f6b09012167683d122"),
])
def test_real_committed_cncm_package_bytes_are_read_without_worktree_fallback(
        monkeypatch, name, size, expected_sha256):
    research_reader = Mock(wraps=launch.shared.git_bytes)
    monkeypatch.setattr(launch.shared, "git_bytes", research_reader)
    original_read = Path.read_bytes
    worktree_path = (launch.PROJECT / name).resolve()
    def forbid_worktree_read(path):
        if path.resolve() == worktree_path:
            raise AssertionError("Committed package input must come from Git, not current file bytes")
        return original_read(path)
    monkeypatch.setattr(Path, "read_bytes", forbid_worktree_read)
    raw = launch.git_package_bytes(launch.ROOT, PACKAGE_REGRESSION_COMMIT, name)
    assert type(raw) is bytes and len(raw) == size
    assert sha256(raw).hexdigest() == expected_sha256
    research_reader.assert_not_called()


def test_real_committed_research_package_bytes_use_unchanged_research_reader(monkeypatch):
    reader = Mock(wraps=launch.shared.git_bytes)
    monkeypatch.setattr(launch.shared, "git_bytes", reader)
    name = "research/CAS_META_2_COMPOSITION/cas_meta2/graph_teaching/real_framework.py"
    raw = launch.git_package_bytes(launch.ROOT, PACKAGE_REGRESSION_COMMIT, name)
    reader.assert_called_once_with(launch.ROOT, PACKAGE_REGRESSION_COMMIT, name)
    assert len(raw) == 20252
    assert sha256(raw).hexdigest() == "82c177e8f70e6931d90a79b65defe9fe6848cce6ab690c67f890b12c4799cd3c"


@pytest.mark.parametrize("name", [
    "tests/test.py", "docs/private.md", "cncm_extra/model.py", "cncm/model.txt",
    "cncm/subdir/model.py", "cncm/../model.py", "cncm\\model.py", "/cncm/model.py",
    "C:/cncm/model.py", None,
])
def test_package_git_reader_rejects_foreign_or_unsafe_members_before_git(monkeypatch, name):
    run_git = Mock(side_effect=AssertionError("Invalid member must not reach Git"))
    monkeypatch.setattr(launch.shared, "_run_git", run_git)
    with pytest.raises(ValueError, match="(INGESTION_SOURCE_MEMBER_SCOPE|PACKAGE_UNSAFE_MEMBER_PATH)"):
        launch.git_package_bytes(launch.ROOT, PACKAGE_REGRESSION_COMMIT, name)
    run_git.assert_not_called()


@pytest.mark.parametrize("commit", ["HEAD", "a" * 39, "a" * 41, None])
def test_package_git_reader_requires_exact_commit_before_git(monkeypatch, commit):
    run_git = Mock(side_effect=AssertionError("Unpinned commit must not reach Git"))
    monkeypatch.setattr(launch.shared, "_run_git", run_git)
    with pytest.raises(ValueError, match="INGESTION_SOURCE_COMMIT"):
        launch.git_package_bytes(launch.ROOT, commit, "cncm/canonical.py")
    run_git.assert_not_called()


def test_package_builder_selects_scoped_reader_by_default(tmp_path, monkeypatch):
    fake, _, _ = package_fixture(tmp_path, monkeypatch)
    reader = Mock(side_effect=LookupError("SCOPED_PACKAGE_READER_SELECTED"))
    monkeypatch.setattr(launch, "git_package_bytes", reader)
    output = fake / "records/package"
    with pytest.raises(LookupError, match="SCOPED_PACKAGE_READER_SELECTED"):
        launch.build_smoke_package(output, source_sha=PACKAGE_REGRESSION_COMMIT)
    assert reader.call_count == 1
    assert reader.call_args.args[:2] == (fake, PACKAGE_REGRESSION_COMMIT)
    assert not output.exists()
