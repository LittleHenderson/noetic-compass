"""Pure verifier controls. Synthetic v0.2 metadata is never execution evidence."""
import ast
from copy import deepcopy
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
from zipfile import ZipFile
from uuid import uuid4

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("v02_delivery_verifier", HERE / "verify_delivered.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "cncm", "cas_meta2",
          "boto3", "botocore", "requests", "httpx", "openai", "anthropic"}


class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in DENIED:
            raise AssertionError("PROHIBITED:" + fullname)


@pytest.fixture(autouse=True)
def no_model_project_provider():
    guard = Deny()
    sys.meta_path.insert(0, guard)
    try:
        yield
        assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)
    finally:
        sys.meta_path.remove(guard)


@pytest.fixture(scope="module")
def base():
    return verifier.load_base()[0]


@pytest.fixture(scope="module")
def historical():
    # Read the already-exposed smoke records and pinned source archive only.
    # Checkpoints remain opaque byte strings: no decoder or project import.
    record = ROOT / "records/learning_smoke_001/receipt_cas-meta2-ingestionsmoke-20260916183635-6ef614bf"
    result = json.loads((record / "result.json").read_bytes())
    assert verifier.digest((record / "result.json").read_bytes()) == "a99859a9bd93af0e502798399737e15a35bb8b2c9de17fad039b8fb860eb92cb"
    results = record / "collected/results"
    artifacts = {path.name: path.read_bytes() for path in (results / "artifacts").iterdir()
                 if path.name != "manifest.json"}
    package = ROOT / "research/CAS_META_2_COMPOSITION/records/ingestion_smoke_001/package_6ef614bf"
    receipt = json.loads((package / "receipt.json").read_bytes())
    archive = (package / "source.zip").read_bytes()
    assert verifier.digest(archive) == receipt["archive_sha256"]
    with ZipFile(package / "source.zip") as zipped:
        members = {name: zipped.read(name) for name in zipped.namelist()}
    return (result, result["authority"]["worker_config"],
            json.loads((results / "result.json").read_bytes()), artifacts, members,
            json.loads(members["graph6_curriculum_source_manifest.json"]))


def test_pinned_original_and_single_ast_change(base):
    _, _, adaptation = verifier.load_base()
    assert verifier.digest(verifier.BASE_PATH.read_bytes()) == verifier.BASE_SHA256
    assert adaptation["comparisons_replaced"] == 1
    assert adaptation["all_other_function_ast_unchanged"] is True
    assert adaptation["original_function_ast_sha256"] != adaptation["adapted_function_ast_sha256"]
    assert base.RECORDS == ROOT / "records/learning_smoke_001"


def test_changed_inherited_pin_refused(monkeypatch):
    monkeypatch.setattr(verifier, "BASE_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="INHERITED_SOURCE_CHANGED"):
        verifier.load_base()


@pytest.mark.parametrize("count", [0, 2])
def test_ambiguous_or_missing_schema_guard_refused(count):
    check = "source['rendering_schema'] == 'cncm.cube-contains-node-rel/0.1'"
    body = "\n".join("    x = " + check for _ in range(count)) or "    pass"
    with pytest.raises(ValueError, match="UNIQUE_SCHEMA_GUARD_REQUIRED"):
        verifier._adapt_measurement_tree(ast.parse("def measured_evidence():\n" + body))


@pytest.mark.parametrize("value", ["cncm.cube-contains-node-rel/0.1", "cncm.cube-contains-node-rel/0.3", None, True, 2])
def test_rendering_guard_refuses_non_v02(value):
    assert verifier.exact_v02_rendering(value) is False


def test_rendering_guard_accepts_only_exact_string():
    class Alias(str):
        pass
    assert verifier.exact_v02_rendering(verifier.RENDERING_SCHEMA) is True
    assert verifier.exact_v02_rendering(Alias(verifier.RENDERING_SCHEMA)) is False


def test_original_historical_measurements_still_pass_only_original_guard(base, historical):
    result = base.measured_evidence(base.Audit(), *historical)
    assert result["optimizer_updates"] == 64
    _, adapted, _ = verifier.load_base()
    with pytest.raises(ValueError, match="CHECKPOINT_SOURCE_CONTEXT"):
        adapted(base.Audit(), *historical)
    with pytest.raises(ValueError, match="V02_CHECKPOINT_RENDERING_REQUIRED"):
        verifier.check_v02_checkpoint_contexts(base, historical[3])


def synthetic_v02(base, historical):
    result, config, envelope, artifacts, members, manifest = deepcopy(historical)
    smoke = base.parse(artifacts["receipt.json"])
    for phase in ("initial", "final"):
        record = base.parse(artifacts[phase + "_checkpoint.json"])
        record["metadata"]["source_binding"]["rendering_schema"] = verifier.RENDERING_SCHEMA
        artifacts[phase + "_checkpoint.json"] = base.canonical(record)
        smoke["checkpoints"][phase] = record
    artifacts["receipt.json"] = base.canonical(smoke)
    return result, config, envelope, artifacts, members, manifest


def test_synthetic_v02_metadata_passes_adapted_measurement_logic_only(base, historical):
    rows = synthetic_v02(base, historical)
    assert verifier.check_v02_checkpoint_contexts(base, rows[3]) is True
    _, adapted, _ = verifier.load_base()
    report = adapted(base.Audit(), *rows)
    assert report["optimizer_updates"] == 64
    with pytest.raises(ValueError, match="CHECKPOINT_SOURCE_CONTEXT"):
        base.measured_evidence(base.Audit(), *rows)
    # This constructed metadata does NOT admit the old packaged source as v0.2.
    with pytest.raises(ValueError, match="PACKAGED_ADAPTER_CONTRACT"):
        verifier.check_v02_package(base, rows[1], rows[4], source_commit=rows[1]["source_sha"],
            adapter_source_sha256=verifier.digest(rows[4][verifier.ADAPTER_PATH]))


def v02_package(base, historical):
    config, members = deepcopy(historical[1]), deepcopy(historical[4])
    members[verifier.ADAPTER_PATH] = (ROOT / verifier.ADAPTER_PATH).read_bytes()
    return config, members


def test_current_v02_source_contract_is_caller_bound(base, historical):
    config, members = v02_package(base, historical)
    report = verifier.check_v02_package(base, config, members, source_commit=config["source_sha"],
        adapter_source_sha256=verifier.digest(members[verifier.ADAPTER_PATH]))
    assert report["rendering_schema"] == verifier.RENDERING_SCHEMA
    assert report["contains_inventory_complete"] is True


@pytest.mark.parametrize("changed", ["commit", "source_hash", "old_source", "disclosure", "duplicate"])
def test_package_pin_and_contract_refusals(base, historical, changed):
    config, members = v02_package(base, historical)
    commit = config["source_sha"]
    if changed == "commit":
        commit = "0" * 40
    elif changed == "old_source":
        members[verifier.ADAPTER_PATH] = historical[4][verifier.ADAPTER_PATH]
    elif changed == "disclosure":
        members[verifier.ADAPTER_PATH] = members[verifier.ADAPTER_PATH].replace(b"an unlisted direct", b"an unlisted indirect")
    elif changed == "duplicate":
        members[verifier.ADAPTER_PATH] += b"\nRENDERING_SCHEMA = 'cncm.cube-contains-node-rel/0.2'\n"
    pin = "0" * 64 if changed == "source_hash" else verifier.digest(members[verifier.ADAPTER_PATH])
    with pytest.raises(ValueError):
        verifier.check_v02_package(base, config, members, source_commit=commit, adapter_source_sha256=pin)


@pytest.mark.parametrize("value", [False, 0, 1, None])
def test_exact_completeness_flag_refused_even_with_synthetic_fixture_pin(base, historical, monkeypatch, value):
    config, members = v02_package(base, historical)
    fixture = base.parse(members[verifier.FIXTURE_PATH])
    fixture["context"]["contains_inventory_complete"] = value
    members[verifier.FIXTURE_PATH] = base.canonical(fixture)
    monkeypatch.setattr(verifier, "FIXTURE_SHA256", verifier.digest(members[verifier.FIXTURE_PATH]))
    with pytest.raises(ValueError, match="EXACT_COMPLETE_SNAPSHOT_REQUIRED"):
        verifier.check_v02_package(base, config, members, source_commit=config["source_sha"],
            adapter_source_sha256=verifier.digest(members[verifier.ADAPTER_PATH]))


def test_phase_mismatch_rejected_before_measurement(base, historical):
    rows = synthetic_v02(base, historical)
    rows[3]["final_checkpoint.json"] = historical[3]["final_checkpoint.json"]
    with pytest.raises(ValueError, match="V02_CHECKPOINT_RENDERING_REQUIRED"):
        verifier.check_v02_checkpoint_contexts(base, rows[3])


def test_failed_caller_pin_is_preserved_and_output_never_reused():
    parent = HERE / "failure_controls"
    parent.mkdir(exist_ok=True)
    output = parent / ("bad_caller_pin_" + uuid4().hex)
    source_pin = verifier.digest((ROOT / verifier.ADAPTER_PATH).read_bytes())
    report = verifier.verify(HERE / "test_verify_delivered.py", "0" * 64, output,
        source_commit="d" * 40, adapter_source_sha256=source_pin)
    assert report["accepted"] is False
    assert "CALLER_OR_PARENT_PIN_MISMATCH" in report["failure"]["detail"]
    raw = (output / "receipt.json").read_bytes()
    assert json.loads(raw) == report
    assert report["provider_calls"] == report["numeric_or_checkpoint_decoder_calls"] == 0
    with pytest.raises(ValueError, match="NEW_OUTPUT_REQUIRED"):
        verifier.verify(HERE / "test_verify_delivered.py", "0" * 64, output,
            source_commit="d" * 40, adapter_source_sha256=source_pin)
    assert (output / "receipt.json").read_bytes() == raw
