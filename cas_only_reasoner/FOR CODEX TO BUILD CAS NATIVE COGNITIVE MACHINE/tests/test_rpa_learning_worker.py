"""Pure smoke-boundary/evidence tests; CUDA is an explicit test double only."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import builtins
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "research/CAS_META_2_COMPOSITION"
if str(PILOT) not in sys.path:
    sys.path.insert(0, str(PILOT))
from cncm import rpa_learning_worker as worker
from cncm.model import ContractError

DENIED = {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer", "transformers", "safetensors"}
JOB = "cas-meta2-ingestionsmoke-20260916000000-12345678"


@pytest.fixture(autouse=True)
def forbid_execution_imports(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED:
            raise AssertionError("PROHIBITED_TEST_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture
def config():
    inputs = worker.input_inventory(ROOT)
    return {"schema": worker.CONFIG_SCHEMA, "candidate": worker.CANDIDATE,
        "job": JOB, "bucket": "smoke-test-bucket", "region": "us-west-2",
        "source_sha": "a" * 40, "training": True, "optimizer_updates_max": 64,
        "max_wall_seconds": 1200, "seed": 20260916, "inputs": inputs,
        "inputs_sha256": worker.digest(worker.canonical(inputs)),
        "execution_design": deepcopy(worker.EXECUTION_DESIGN),
        "material": worker.material_identity(ROOT)}


def test_actual_exposed_material_has_three_training_and_six_prediction_requests():
    document, training, prediction = worker.smoke_material(ROOT)
    assert len(training) == 3 and len(prediction) == 6
    assert Counter(r["operation"] for r in training) == {
        "LIST_PARTS": 1, "FIND_SHARED_PART": 1, "REACHED_VIA": 1}
    assert Counter(r["operation"] for r in prediction) == {
        "LIST_PARTS": 2, "FIND_SHARED_PART": 2, "REACHED_VIA": 2}
    assert prediction[::2] == training
    assert all(set(r) == {"operation", "question", "assistance"}
               and r["assistance"] == "unassisted" for r in prediction)
    assert len({worker.canonical(r) for r in prediction}) == 6
    identity = worker.material_identity(ROOT)
    assert identity["document_sha256"] == worker.digest(worker.canonical(document.to_dict()))
    assert "not held-out" in identity["boundary"]


def test_inventory_binds_actual_source_fixture_and_no_checkpoint_inputs():
    rows = worker.input_inventory(ROOT)
    assert [r["path"] for r in rows] == sorted({r["path"] for r in rows})
    assert {"cncm/rpa_learning_worker.py", "cncm/rpa_learning_smoke.py", worker.FIXTURE} <= {r["path"] for r in rows}
    assert all(not r["path"].endswith(".pt") and not r["path"].endswith("data_manifest.json") for r in rows)
    for row in rows:
        raw = (ROOT / row["path"]).read_bytes()
        assert set(row) == {"path", "bytes", "sha256"}
        assert row["bytes"] == len(raw) and row["sha256"] == sha256(raw).hexdigest()


@pytest.mark.parametrize("field,value", [
    ("unknown", 1), ("schema", "wrong"), ("training", 1),
    ("optimizer_updates_max", 64.0), ("optimizer_updates_max", 65),
    ("seed", 20260916.0), ("max_wall_seconds", 1200.0),
    ("bucket", "../escape"), ("region", "us-east-1"), ("source_sha", "bad"),
    ("job", JOB.replace("ingestionsmoke", "orderedencoder")),
    ("execution_design", {**worker.EXECUTION_DESIGN, "launch_enabled": 0}),
    ("material", {}), ("inputs_sha256", "0" * 64),
])
def test_bad_config_refused_before_cuda_or_output(config, tmp_path, monkeypatch, field, value):
    from cas_meta2.teaching_cycle import gpu_adapter
    cuda = Mock(side_effect=AssertionError("CUDA must not be acquired"))
    monkeypatch.setattr(gpu_adapter, "_cuda", cuda)
    config[field] = value
    results = tmp_path / "results"
    with pytest.raises(ContractError, match="SMOKE_"):
        worker.run(config, root=ROOT, results=results, artifacts=results / "artifacts")
    cuda.assert_not_called()
    assert not results.exists()


def test_resealed_input_manifest_type_alias_is_refused_before_cuda(config, tmp_path, monkeypatch):
    from cas_meta2.teaching_cycle import gpu_adapter
    cuda = Mock(side_effect=AssertionError("CUDA forbidden"))
    monkeypatch.setattr(gpu_adapter, "_cuda", cuda)
    config["inputs"][0]["bytes"] = float(config["inputs"][0]["bytes"])
    config["inputs_sha256"] = worker.digest(worker.canonical(config["inputs"]))
    with pytest.raises(ContractError, match="SMOKE_INPUT_BINDING"):
        worker.run(config, root=ROOT, results=tmp_path, artifacts=tmp_path / "artifacts")
    cuda.assert_not_called()


def test_changed_fixture_is_rejected_without_checking_teacher(tmp_path):
    path = tmp_path / worker.FIXTURE
    path.parent.mkdir(parents=True)
    path.write_bytes((ROOT / worker.FIXTURE).read_bytes() + b" ")
    with pytest.raises(ContractError, match="SMOKE_EXPOSED_FIXTURE_CHANGED"):
        worker.smoke_material(tmp_path)


def test_preexisting_artifact_directory_refused_before_cuda(config, tmp_path, monkeypatch):
    from cas_meta2.teaching_cycle import gpu_adapter
    cuda = Mock(side_effect=AssertionError("CUDA forbidden"))
    monkeypatch.setattr(gpu_adapter, "_cuda", cuda)
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    with pytest.raises(ContractError, match="SMOKE_FRESH_ARTIFACT_DIRECTORY"):
        worker.run(config, root=ROOT, results=tmp_path, artifacts=artifacts)
    cuda.assert_not_called()


def fake_runtime(monkeypatch):
    from cas_meta2.teaching_cycle import gpu_adapter
    fake = SimpleNamespace(__version__="2.11.0+cu128",
        version=SimpleNamespace(cuda="12.8"),
        cuda=SimpleNamespace(get_device_name=lambda device: "RTX PRO 4500 TEST DOUBLE"))
    monkeypatch.setattr(gpu_adapter, "_cuda", lambda: (fake, "EXPLICIT_TEST_DOUBLE"))
    monkeypatch.setattr(worker, "verify_worker_packages", lambda root: {
        "status": "EXPLICIT_TEST_DOUBLE_NOT_INSTALLED_RUNTIME_EVIDENCE", "source_files": [],
        "loaded_modules": [{"module": n} for n in ("cas_cjt.neural", "cas_cjt.state", "casformer")]})


@pytest.mark.parametrize("tamper", ["installed_bytes", "foreign_loaded_module"])
def test_package_provenance_refuses_changed_or_foreign_source_without_importing_it(tmp_path, monkeypatch, tamper):
    import importlib
    from zipfile import ZipFile
    from cas_meta2.teaching_cycle import gpu_adapter
    monkeypatch.setattr(gpu_adapter, "execution_guard", lambda: None)
    packages = {}
    for name, (package, _) in worker.WHEELS.items():
        with ZipFile(ROOT / worker.WHEEL_DIR / name) as archive:
            for member in archive.namelist():
                if member.startswith(package + "/") and member.endswith((".py", ".json")):
                    path = tmp_path / member
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.read(member))
        module = SimpleNamespace(__file__=str(tmp_path / package / "__init__.py"))
        packages[package] = module
        monkeypatch.setitem(sys.modules, package, module)
    original = importlib.import_module
    monkeypatch.setattr(importlib, "import_module", lambda name, *a, **k:
                        packages[name] if name in packages else original(name, *a, **k))
    good = worker.verify_worker_packages(ROOT)
    assert good["source_files"] and good["status"] == "INSTALLED_AND_LOADED_SOURCES_MATCH_PINNED_WHEELS"
    if tamper == "installed_bytes":
        path = tmp_path / "cas_cjt/neural.py"
        path.write_bytes(path.read_bytes() + b"\n# CHANGED TEST SOURCE\n")
        code = "SMOKE_INSTALLED_SOURCE_MISMATCH"
    else:
        path = tmp_path / "foreign.py"
        path.write_text("# INERT TEST FILE\n", encoding="utf-8")
        monkeypatch.setitem(sys.modules, "cas_cjt.foreign", SimpleNamespace(__file__=str(path)))
        code = "SMOKE_FOREIGN_LOADED_PACKAGE"
    with pytest.raises(ContractError, match=code):
        worker.verify_worker_packages(ROOT)


def assert_failed_evidence(results, expected_detail):
    envelope = json.loads((results / "result.json").read_bytes())
    assert envelope["status"] == "INGESTION_SMOKE_FAILED"
    assert expected_detail in envelope["failure"]["detail"]
    assert envelope["summary"]["learning_improvement_established"] is False
    assert (results / "result.json.sha256").read_text().strip() == sha256((results / "result.json").read_bytes()).hexdigest()
    manifest = json.loads((results / "artifacts/manifest.json").read_bytes())
    assert manifest["artifacts"] == envelope["artifacts"]
    for row in manifest["artifacts"]:
        raw = (results / "artifacts" / row["name"]).read_bytes()
        assert len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"]


def test_partial_checkpoint_bytes_survive_worker_failure(config, tmp_path, monkeypatch):
    from cncm import rpa_learning_smoke as smoke
    fake_runtime(monkeypatch)
    def fail(*args, output, **kwargs):
        output.mkdir()
        (output / "origin.pt").write_bytes(b"EXPLICIT TEST BYTES - never deserialized")
        raise RuntimeError("INJECTED_CHECKPOINT_FAILURE")
    monkeypatch.setattr(smoke, "run_worker_smoke", fail)
    results = tmp_path / "results"
    with pytest.raises(RuntimeError, match="INJECTED_CHECKPOINT_FAILURE"):
        worker.run(config, root=ROOT, results=results, artifacts=results / "artifacts")
    assert (results / "artifacts/origin.pt").read_bytes() == b"EXPLICIT TEST BYTES - never deserialized"
    assert_failed_evidence(results, "INJECTED_CHECKPOINT_FAILURE")


def test_missing_success_artifacts_still_publish_original_failure(config, tmp_path, monkeypatch):
    from cncm import rpa_learning_smoke as smoke
    fake_runtime(monkeypatch)
    def incomplete(*args, output, **kwargs):
        output.mkdir()
        (output / "origin.pt").write_bytes(b"PARTIAL TEST BYTES")
        return {"status": "MECHANICAL_SMOKE_AND_RELOAD_OBSERVED",
                "checkpoint_reload_verified": True,
                "training": {"training": {"completed_updates": 1}}, "forward_calls": {}}
    monkeypatch.setattr(smoke, "run_worker_smoke", incomplete)
    results = tmp_path / "results"
    with pytest.raises(ContractError, match="SMOKE_REQUIRED_ARTIFACT_MISSING"):
        worker.run(config, root=ROOT, results=results, artifacts=results / "artifacts")
    assert (results / "artifacts/origin.pt").read_bytes() == b"PARTIAL TEST BYTES"
    assert_failed_evidence(results, "SMOKE_REQUIRED_ARTIFACT_MISSING")


def test_pure_worker_and_launcher_import_in_guarded_subprocess():
    code = r'''
import importlib.abc, json, pathlib, sys
blocked={'torch','numpy','boto3','botocore','cas_cjt','casformer','transformers','safetensors'}
class Guard(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in blocked:raise AssertionError('FORBIDDEN:'+fullname)
sys.meta_path.insert(0,Guard())
root=pathlib.Path(sys.argv[1]);sys.path[:0]=[str(root),str(root/'research/CAS_META_2_COMPOSITION')]
from cncm import rpa_learning_worker as worker
from aws import ingestion_smoke_launch as launch
config=launch.worker_config('cas-meta2-ingestionsmoke-20260916000000-12345678',source_sha='a'*40)
worker.validate_config({**config,'bucket':'test-smoke-bucket'},root)
assert not blocked & {name.split('.')[0] for name in sys.modules}
print(json.dumps({'training':len(config['material']['training_requests']),'prediction':len(config['material']['prediction_requests'])}))
'''
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT)],
                            cwd=ROOT, env=env, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"training": 3, "prediction": 6}
