"""Pure exact launch/package admission. No providers, reservations or tensors."""
import ast
import builtins
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from zipfile import ZipFile

import pytest

from aws import typed_course_launch as launch

JOB = "cas-meta2-typedcourse-20260916000000-12345678"
SOURCE = "a" * 40


@pytest.fixture(autouse=True)
def pure(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer", "tensorflow", "jax"}:
            raise AssertionError("FORBIDDEN_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture
def authority():
    return {"schema": launch.AUTHORITY_SCHEMA, "candidate": launch.CANDIDATE,
        "job": JOB, "source_sha": SOURCE, "archive_sha256": "b"*64, "manifest_sha256": "c"*64,
        "owner_authorization_sha256": "d"*64, **launch.BOUNDS,
        "inputs_sha256": launch.frozen_inputs_hash(),
        "design_sha256": launch.digest(launch.canonical(launch.DESIGN)),
        "evidence_contract_sha256": launch.run_evidence.contract_digest(launch.evidence_contract()),
        "worker_config": launch.worker_config(JOB, source_sha=SOURCE)}


def request(authority):
    return {"schema": launch.REQUEST_SCHEMA, "launch_authorized": False,
            **{k: authority[k] for k in ("job", "source_sha", "archive_sha256", "manifest_sha256")}}


def provider(clients=None):
    return launch.TypedCourseProvider(job=JOB, source_sha=SOURCE, archive_sha256="b"*64,
        manifest_sha256="c"*64, clients=clients or {}, ledger_path=Path("UNUSED_TEST_LEDGER"))


def test_worker_contract_config_has_exact_full_course_bounds_and_bucket(authority):
    assert launch.validate_authority(authority) is authority
    config = authority["worker_config"]
    assert launch.contract.validate_config(config, launch.PROJECT) == config
    assert config["bucket"] == JOB + "-807562639912"
    assert config["design"]["main_optimizer_updates"] == 160
    assert config["design"]["global_optimizer_updates_max"] == 162
    assert config["design"]["main_presentations"] == 1152
    assert config["design"]["registry_packets"] == 564
    assert config["design"]["automatic_retries"] == 0
    assert config["design"]["reservation_usd"] == "7.00"


@pytest.mark.parametrize("key,value", [("extra", 1), ("training", 1), ("optimizer_updates_max", 162.0),
    ("optimizer_updates_max", 163), ("max_wall_seconds", 3300.0), ("jobs", True), ("automatic_retries", 1),
    ("reservation_usd", "8.00"), ("inputs_sha256", "0"*64), ("evidence_contract_sha256", "0"*64)])
def test_authority_closed_and_exact_before_provider(authority, key, value):
    authority[key] = value
    with pytest.raises(ValueError, match="TYPED_"): launch.validate_authority(authority)


@pytest.mark.parametrize("key,value", [("schema", "wrong"), ("launch_authorized", True), ("launch_authorized", 0),
    ("job", JOB.replace("typedcourse", "ingestionsmoke")), ("source_sha", "a"*39)])
def test_inert_request_is_new_candidate_only(authority, key, value):
    row = request(authority); row[key] = value
    with pytest.raises(ValueError, match="TYPED_REQUEST_"): launch.validate_request(row)


def test_nested_design_and_bucket_cannot_escape_authority(authority):
    bad = deepcopy(authority); bad["worker_config"]["design"]["main_optimizer_updates"] = 159
    with pytest.raises(ValueError, match="TYPED_AUTHORITY_CONFIG"): launch.validate_authority(bad)
    bad = deepcopy(authority); bad["worker_config"]["bucket"] = "other-bucket"
    with pytest.raises(ValueError, match="TYPED_AUTHORITY_CONFIG"): launch.validate_authority(bad)
    instance = provider(); instance.bind_authority(authority)
    assert instance._worker_config(authority["worker_config"]["bucket"]) == authority["worker_config"]
    with pytest.raises(ValueError, match="TYPED_PROVIDER_BUCKET"): instance._worker_config("other-bucket")


def test_exact_canonical_ledger_required(tmp_path, monkeypatch):
    canonical = tmp_path / "canonical.json"; canonical.write_text("{}")
    unrelated = tmp_path / "copy.json"; unrelated.write_text("{}")
    monkeypatch.setattr(launch, "CANONICAL_LEDGER", canonical)
    assert launch.validate_ledger_path(canonical) == canonical.resolve()
    with pytest.raises(ValueError, match="CANONICAL_META1"): launch.validate_ledger_path(unrelated)


def test_default_is_plan_only_without_provider_clients(monkeypatch, capsys):
    clients = Mock(side_effect=AssertionError("PROVIDER_FORBIDDEN"))
    monkeypatch.setattr(launch.lifecycle, "_clients", clients)
    assert launch.main([]) == 0
    row = json.loads(capsys.readouterr().out)
    assert row["provider_calls"] == 0 and row["reservation_created"] is False
    clients.assert_not_called()


def test_owner_disagreement_refuses_before_lifecycle(authority, tmp_path, monkeypatch):
    owner = {"schema": launch.OWNER_SCHEMA, "candidate": launch.CANDIDATE,
        "owner_instruction_raw": "SYNTHETIC TEST ONLY", "bounds": {**launch.BOUNDS, "jobs": 2}}
    path = tmp_path / "owner.json"; path.write_bytes(launch.canonical(owner))
    authority["owner_authorization_sha256"] = launch.digest(path.read_bytes())
    inherited = Mock(side_effect=AssertionError("LIFECYCLE_FORBIDDEN"))
    monkeypatch.setattr(launch.lifecycle, "execute", inherited)
    with pytest.raises(ValueError, match="TYPED_OWNER_BOUND"):
        launch.execute(request(authority), authority, provider(), receipt_dir=tmp_path / "r",
                       owner_authorization_path=path, ledger_path=tmp_path / "absent")
    inherited.assert_not_called()


def test_actual_worker_dispatch_timeout_and_manifest_loader_order():
    tree = ast.parse(launch.render_worker()); compile(tree, "<pure-rendered-worker>", "exec")
    values = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
        and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id in {"INNER_RUNNER", "MAX_WALL_SECONDS", "RESULT_SCHEMA"}}
    assert values["MAX_WALL_SECONDS"] == 3300 and values["RESULT_SCHEMA"] == launch.RESULT_SCHEMA
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and ast.unparse(n.func) == "subprocess.run"
             and any(k.arg == "timeout" for k in n.keywords)]
    assert len(calls) == 1 and ast.unparse(calls[0].args[0]) == "[python, '-B', str(runner), str(root)]"
    assert [ast.unparse(k.value) for k in calls[0].keywords if k.arg == "timeout"] == ["MAX_WALL_SECONDS"]
    assert "config['design']['region']" in ast.unparse(tree)
    inner = values["INNER_RUNNER"]; compile(inner, "<pure-inner>", "exec")
    assert inner.index("exec(compile(RAW") < inner.index("MODULE.install") < inner.index("from cncm import typed_course_worker")
    assert "attestor=ATTESTOR" in inner and "MANIFEST_INPUT_INDEX_HASH" in inner
    assert "get_code" not in inner and "runpy" not in inner
    assert "dont_inherit=True, optimize=0" in inner


@pytest.mark.parametrize("mutation,error", [("hash", "INPUT_INDEX_HASH"), ("manifest_index", "MANIFEST_INPUT_INDEX_HASH"),
    ("row", "MANIFEST_INPUT_JOIN"), ("source", "SOURCE_SHA")])
def test_bootstrap_pin_failures_precede_any_owned_import(tmp_path, monkeypatch, mutation, error):
    # Execute only the actual stdlib verification prefix. A sentinel fails if
    # execution reaches the first project/loader boundary after these checks.
    row = {"path": "cncm/__init__.py", "bytes": 1, "sha256": "a"*64}
    config = {"source_sha": SOURCE, "inputs": [row], "inputs_sha256": launch.digest(launch.canonical([row])), "design": {}}
    manifest = {"source_sha": SOURCE, "inputs": [row], "inputs_sha256": config["inputs_sha256"],
        "typed_design": {}, "files_sha256": {row["path"]: row["sha256"]}, "files_bytes": {row["path"]: 1}}
    if mutation == "hash": config["inputs_sha256"] = "0"*64
    elif mutation == "manifest_index": manifest["inputs_sha256"] = "0"*64
    elif mutation == "row": manifest["files_sha256"][row["path"]] = "0"*64
    else: manifest["source_sha"] = "b"*40
    (tmp_path / "config.json").write_bytes(launch.canonical(config))
    (tmp_path / launch.shared.MANIFEST_NAME).write_bytes(launch.canonical(manifest))
    monkeypatch.setattr(launch.sys, "argv", ["test", str(tmp_path)])
    prefix = launch.bootstrap_source().split("require(not any(n == 'cncm'", 1)[0]
    with pytest.raises(ValueError, match="TYPED_BOOTSTRAP:" + error):
        exec(compile(prefix, "<pin-refusal>", "exec"), {})


def test_evidence_contract_declares_every_full_course_artifact():
    expected = launch._probe().EXPECTED_ARTIFACTS
    keys = set(launch.run_evidence.contract_keys(launch.evidence_contract()))
    assert {"results/artifacts/" + n for n in expected} <= keys
    assert {"batch_%03d.json" % n for n in range(160)} <= set(expected)
    assert {"update_%03d.json" % n for n in range(160)} <= set(expected)
    assert {"initial.pt", "prelast.pt", "final.pt", "encoding_checks.json", "loaded_sources.json", "installed_sources.json", "replay_report.json"} <= set(expected)
    assert len(keys) == len(expected) + 3


def test_material_scope_getter_allows_only_two_root_records(monkeypatch):
    run = Mock(return_value=b"EXPLICIT TEST")
    monkeypatch.setattr(launch.shared, "_run_git", run)
    for name in launch.contract.MATERIAL:
        assert launch.git_package_bytes(launch.ROOT, SOURCE, name) == b"EXPLICIT TEST"
        assert run.call_args.args[0][-1] == SOURCE + ":" + launch.shared.GIT_PREFIX + name
    for name in ("records/private_targets.json", "cncm/../secrets.py", "cncm/source.txt"):
        with pytest.raises(ValueError): launch.git_package_bytes(launch.ROOT, SOURCE, name)


def test_package_exact_members_and_source_refusal(tmp_path, monkeypatch):
    real = launch.ROOT; fake = tmp_path / "comp"; fake.mkdir(); (fake / "records").mkdir()
    for name in launch.PACKAGING_SOURCES + ("requirements-gpu.txt",):
        destination = fake / name; destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((real / name).read_bytes())
    monkeypatch.setattr(launch, "ROOT", fake)
    def read(root, commit, name): return (launch.PROJECT / name).read_bytes()
    result = launch.build_typed_package(fake / "records/good", source_sha=SOURCE, git_bytes_fn=read)
    with ZipFile(result["archive"]) as archive:
        names = set(archive.namelist())
        assert names == set(launch.package_data_files()) | {launch.WORKER_NAME, launch.shared.MANIFEST_NAME}
        assert {n for n in names if n.startswith("records/")} == set(launch.contract.MATERIAL)
        assert len(archive.read(launch.contract.COURSE_PATH)) == 4165195
        assert len(archive.read(launch.contract.TOKENIZER_PATH)) == 447140
        manifest = json.loads(archive.read(launch.shared.MANIFEST_NAME))
        assert manifest["inputs_sha256"] == launch.frozen_inputs_hash()
        for name in manifest["members"]:
            raw = archive.read(name)
            assert len(raw) == manifest["files_bytes"][name] and launch.digest(raw) == manifest["files_sha256"][name]
    def changed(root, commit, name):
        raw = read(root, commit, name)
        return raw + b" " if name == launch.contract.COURSE_PATH else raw
    with pytest.raises(ValueError, match="TYPED_INPUT_NOT_COMMITTED"):
        launch.build_typed_package(fake / "records/bad", source_sha=SOURCE, git_bytes_fn=changed)
    assert not (fake / "records/bad").exists()


def test_guest_deadlines_config_and_manifest_pins_before_worker(authority):
    instance = provider(); instance.bind_authority(authority)
    script = instance._user_data(authority["worker_config"]["bucket"])
    assert script.index("is-active --quiet") < script.index("aws s3api get-object")
    assert "--on-boot=6900s" in script and "--signal=TERM --kill-after=30s 4200s" in script
    assert "--poweroff +1" in script and "--poweroff now" in script
    assert launch.digest(launch.canonical(authority["worker_config"])) + "  /opt/cas-graph6curr/package/config.json" in script
    assert authority["manifest_sha256"] + "  /opt/cas-graph6curr/package/" + launch.shared.MANIFEST_NAME in script
    assert script.index("package/config.json' | sha256sum") < script.index('"$PY" -B')


@pytest.mark.parametrize("state,complete", [("terminated", True), ("running", False), ("shutting-down", False), ("unknown", False)])
def test_cleanup_requires_observed_termination(monkeypatch, state, complete):
    monkeypatch.setattr(launch.lifecycle.CandidateProvider, "cleanup", lambda *a, **k:
        {"complete": True, "failures": [], "instances": {}, "instances_termination_pending": []})
    ec2 = Mock(); ec2.describe_instances.return_value = {"Reservations": [{"Instances": [{"InstanceId": "i-test", "State": {"Name": state}}]}]}
    instance = provider({"ec2": ec2}); instance._instance_ids = ["i-test"]
    assert instance.cleanup(JOB)["complete"] is complete


def test_unknown_launch_response_is_incomplete(monkeypatch):
    monkeypatch.setattr(launch.lifecycle.CandidateProvider, "cleanup", lambda *a, **k:
        {"complete": True, "failures": [], "instances": {}, "instances_termination_pending": []})
    instance = provider(); instance._event = Mock(); instance._launch_called = True
    with pytest.raises(TimeoutError):
        instance._effect("run_instances", Mock(side_effect=TimeoutError("SYNTHETIC_LOSS")))
    report = instance.cleanup(JOB)
    assert report["compute_identity_uncertain"] is True and report["complete"] is False


@pytest.mark.parametrize("rates", [[], ["0"], ["-1"], ["NaN"], ["Infinity"], ["2.53"], ["2.52"]])
def test_price_must_be_observed_finite_positive_and_under_ceiling(rates):
    frozen = launch.shared.RESOURCE_PLAN
    ec2, sts, pricing = Mock(), Mock(), Mock()
    sts.get_caller_identity.return_value = {"Account": frozen["account"]}
    ec2.describe_images.return_value = {"Images": [{"State": "available"}]}
    ec2.describe_instance_types.return_value = {"InstanceTypes": [{"GpuInfo": {"Gpus": [{"Name": frozen["gpu_name_contains"]}]}}]}
    ec2.describe_instances.return_value = {"Reservations": []}
    dims = {str(i): {"unit": "Hrs", "pricePerUnit": {"USD": rate}} for i, rate in enumerate(rates)}
    pricing.get_products.return_value = {"PriceList": [json.dumps({"terms": {"OnDemand": {"term": {"priceDimensions": dims}}}})],
                                         "ResponseMetadata": {"RequestId": "EXPLICIT_TEST"}}
    instance = provider({"ec2": ec2, "sts": sts, "pricing": pricing})
    instance.reserve = Mock(side_effect=AssertionError("RESERVATION_FORBIDDEN"))
    if rates == ["2.52"]:
        assert instance.preflight()["observed_on_demand_hourly_usd"] == rates
    else:
        with pytest.raises(ValueError): instance.preflight()
    instance.reserve.assert_not_called()
