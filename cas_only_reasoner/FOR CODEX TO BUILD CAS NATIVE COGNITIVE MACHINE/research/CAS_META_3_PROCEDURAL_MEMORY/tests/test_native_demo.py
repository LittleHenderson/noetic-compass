"""Pure/native-mocked fixtures only; no real native execution or qualification."""
from copy import deepcopy
from hashlib import sha256
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from cas_meta3 import native_demo as demo
from cas_meta3 import registry as storage
from cas_meta3.linker import link_demonstration


pytestmark = pytest.mark.not_gpu


def fake_hash(label):
    return sha256(("SYNTHETIC ONLY, NOT NATIVE IDENTITY:" + label).encode()).hexdigest()


def mock_reference():
    identity = {"model": {"model_digest": fake_hash("model"), "parameter_bytes_sha256": fake_hash("parameters")},
        "stored_model_digest": fake_hash("model"), "software_digest": fake_hash("software"),
        "topology": [{"source": "A", "target": "B"}], "contracts": {"^6": fake_hash("operation")},
        "decoders": {"A": fake_hash("decoder-a"), "B": fake_hash("decoder-b")}}
    return {"status": "EXECUTED", "reference": True, "runtime_identity": identity,
        "runtime_identity_after": deepcopy(identity), "selected_action": demo.fixed_task()["target"]}


def mock_package():
    reference = mock_reference()
    compatibility = demo.compatibility_from_reference(reference, {"native_schema_sha256": fake_hash("schema")})
    return demo.make_package(compatibility, fake_hash("reference-json"))


def mock_calls():
    """Equal B payload hashes deliberately do not make the Effect IDs equal."""
    package = mock_package()
    link = link_demonstration(package, expected_digest=storage.package_digest(package),
        trusted_compatibility=package["compatibility"], permitted_cjts=("A", "B"))["link_receipt"]
    effect = lambda identifier, producer: {"kind": "effect", "effect_id": identifier,
        "producer_cjt_id": producer, "payload_sha256": fake_hash("a" if producer == "A" else "equal-b-payload")}
    a, first, second = effect("mock-effect-a", "A"), effect("mock-effect-b1", "B"), effect("mock-effect-b2", "B")
    events = [{"kind": "NATIVE", "run_id": "mock-run", "address": "entry/0", "call_id": "mock-run:entry",
               "cjt_id": "A", "output_reference": a}]
    for index, output in enumerate((first, second), start=1):
        events += [{"kind": "ENTER", "run_id": "mock-run", "address": f"entry/{index}",
                    "call_id": f"mock-run:entry/{index}", "procedure": "p0", "input_reference": a},
                   {"kind": "NATIVE", "run_id": "mock-run", "address": f"entry/{index}/0",
                    "call_id": f"mock-run:entry/{index}", "cjt_id": "B", "input_reference": a, "output_reference": output}]
    events.append({"kind": "RETURN", "run_id": "mock-run", "address": "entry", "reference": first})
    result = {"selected_action": demo.fixed_task()["target"], "final_reference": first}
    return result, events, link


def synthetic_env(monkeypatch):
    monkeypatch.setenv("CAS_META3_RUN_GPU_DEMO", "1")
    monkeypatch.setenv("CAS_META3_AWS_JOB_ID", "fixture_only_no_gpu")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", "fixture_only_no_gpu")


def test_import_is_pure_and_native_sources_are_literal_pinned():
    assert "torch" not in sys.modules
    source = demo.source_identity()
    assert source["protected_files"] == 316
    assert source["dependency"]["source_sha"] == storage.META2_SOURCE_SHA
    assert source["native_files_sha256"] == demo.NATIVE_PINS
    assert source["native_schema_sha256"] == demo.file_hash(demo.ROOT.parent / source["native_schema_path"])


def test_native_pins_match_immutable_git_objects_without_model_imports():
    root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=demo.ROOT,
        check=True, capture_output=True, text=True).stdout.strip())
    for relative, checksum in demo.NATIVE_PINS.items():
        path = (demo.ROOT.parent / relative).resolve().relative_to(root.resolve()).as_posix()
        raw = subprocess.run(["git", "show", storage.META2_SOURCE_SHA + ":" + path], cwd=root,
                             check=True, capture_output=True).stdout
        assert sha256(raw).hexdigest() == checksum
    assert "torch" not in sys.modules


@pytest.mark.parametrize("missing", ["CAS_META3_RUN_GPU_DEMO", "CAS_META3_AWS_JOB_ID", "CAS_META2_AWS_JOB_ID"])
def test_missing_aws_authorization_rejects_before_paths_imports_or_construction(monkeypatch, tmp_path, missing):
    synthetic_env(monkeypatch)
    monkeypatch.delenv(missing)
    monkeypatch.setattr(demo, "cuda_runtime", lambda *_: pytest.fail("LOCAL_MODEL_PATH_REACHED"))
    monkeypatch.setattr(demo, "source_identity", lambda: pytest.fail("GUARD_WAS_NOT_FIRST"))
    with pytest.raises(demo.NativeDemoError, match="META3_EXPLICIT_AWS_GPU_JOB_REQUIRED"):
        demo.run(tmp_path / "no_demo", tmp_path / "no_native")
    assert not list(tmp_path.iterdir()) and "torch" not in sys.modules


@pytest.mark.parametrize("job", ["../escape", "a/b", "a.b", "", "x" * 81])
def test_invalid_job_ids_fail_closed(monkeypatch, job):
    synthetic_env(monkeypatch)
    monkeypatch.setenv("CAS_META3_AWS_JOB_ID", job)
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", job)
    with pytest.raises(demo.NativeDemoError, match="META3_EXPLICIT_AWS_GPU_JOB_REQUIRED"):
        demo.aws_guard()


def test_only_exact_new_native_job_subtree_is_allowed(monkeypatch, tmp_path):
    root, dependency = tmp_path / "meta3", tmp_path / "meta2"
    monkeypatch.setattr(demo, "ROOT", root)
    monkeypatch.setattr(storage, "meta2_dependency_path", lambda: dependency)
    output, native = root / "records/new_demo", dependency / "records/meta3_fixture"
    assert demo.checked_paths(output, native, "fixture", new=True) == (output, native)
    assert not output.exists() and not native.exists()
    with pytest.raises(demo.NativeDemoError, match="EXACT_META3_NATIVE_JOB_SUBTREE_REQUIRED"):
        demo.checked_paths(output, dependency / "records/old_run", "fixture", new=True)
    with pytest.raises(demo.NativeDemoError, match="META3_OUTPUT_ROOT_REQUIRED"):
        demo.checked_paths(root / "outside", native, "fixture", new=True)
    output.mkdir(parents=True)
    with pytest.raises(demo.NativeDemoError, match="NEW_MEMORY_OUTPUT_DIRECTORIES_REQUIRED"):
        demo.checked_paths(output, native, "fixture", new=True)


def test_fixed_expectation_is_independent_and_passes_unchanged_pure_native_admission():
    native = demo.checked_native()
    task = demo.fixed_task()
    plan = native.admit_action(task["public"], task["target"])
    assert [{key: row[key] for key in ("cjt_id", "input_node")} for row in plan["runs"]] == [
        {"cjt_id": "A", "input_node": -1}, {"cjt_id": "B", "input_node": 0}, {"cjt_id": "B", "input_node": 0}]
    assert plan["return_node"] == 1
    tree = ast.parse(Path(demo.__file__).read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "fixed_task")
    assert not any(isinstance(node, ast.Name) and node.id in ("link_demonstration", "retrieve_and_link")
                   for node in ast.walk(function))
    assert "torch" not in sys.modules


def test_exact_compatibility_mapping_and_storage_remain_unqualified(tmp_path):
    reference = mock_reference()
    compatibility = demo.compatibility_from_reference(reference, {"native_schema_sha256": fake_hash("schema")})
    assert compatibility == {"baseline_sha": storage.BASELINE_SHA, "meta2_source_sha": storage.META2_SOURCE_SHA,
        "ir_schema": storage.IR_SCHEMA, "native_schema_sha256": fake_hash("schema"), "model_digest": fake_hash("model"),
        "parameter_bytes_sha256": fake_hash("parameters"), "software_digest": fake_hash("software"),
        "topology_sha256": demo.digest(reference["runtime_identity"]["topology"]),
        "operation_contracts": {"^6": fake_hash("operation")},
        "decoder_contracts": {"A": fake_hash("decoder-a"), "B": fake_hash("decoder-b")}}
    package = demo.make_package(compatibility, fake_hash("reference-json"))
    with storage.ProcedureRegistry(tmp_path / "fixture-registry.db") as registry:
        receipt = registry.install(package, expected_digest=storage.package_digest(package),
            trusted_compatibility=compatibility, permitted_cjts=("A", "B"))
    assert receipt["qualification_status"] == "UNQUALIFIED" and receipt["storage_status"] == "STORAGE_ONLY"


@pytest.mark.parametrize("mutation", ["status", "reference", "changed", "stored-model"])
def test_untrusted_runtime_identity_cannot_become_compatibility(mutation):
    reference = mock_reference()
    if mutation == "status":
        reference["status"] = "REJECTED"
    elif mutation == "reference":
        reference["reference"] = False
    elif mutation == "changed":
        reference["runtime_identity_after"]["software_digest"] = fake_hash("changed")
    else:
        reference["runtime_identity"]["stored_model_digest"] = fake_hash("not-model")
        reference["runtime_identity_after"] = deepcopy(reference["runtime_identity"])
    with pytest.raises(demo.NativeDemoError):
        demo.compatibility_from_reference(reference, {"native_schema_sha256": fake_hash("schema")})


def test_pure_rejections_preserve_registry_and_never_make_native_candidate(tmp_path, monkeypatch):
    package = mock_package()
    with storage.ProcedureRegistry(tmp_path / "registry.db") as registry:
        registry.install(package, expected_digest=storage.package_digest(package),
            trusted_compatibility=package["compatibility"], permitted_cjts=("A", "B"))
        monkeypatch.setattr(demo, "cuda_runtime", lambda *_: pytest.fail("PURE_REJECTION_REACHED_CUDA"))
        monkeypatch.setattr(demo, "checked_native", lambda: pytest.fail("PURE_REJECTION_REACHED_NATIVE"))
        before = (tmp_path / "registry.db").read_bytes()
        receipt = demo.rejection_checks(registry, tmp_path, tmp_path / "native_never_created",
                                       storage.package_digest(package), package["compatibility"])
    assert len(receipt["cases"]) == 5
    assert {row["case"] for row in receipt["cases"]} == {"forged_package_digest", "wrong_compatibility",
        "denied_child_scope", "denied_parent_scope", "wrong_package_schema"}
    assert all(row["rejected"] and not row["native_entrypoint_called"] for row in receipt["cases"])
    assert (tmp_path / "registry.db").read_bytes() == before
    assert not (tmp_path / "native_never_created").exists()


def test_call_mapping_separates_package_link_and_runtime_addresses():
    result, events, link = mock_calls()
    receipt = demo.check_call_mapping(result, events, link)
    assert receipt["calls"][0] == {"caller": "main", "pc": 1, "functional_address": "entry:main/steps/1",
        "runtime_address": "entry/1", "call_id": "mock-run:entry/1",
        "input_effect_id": "mock-effect-a", "output_effect_id": "mock-effect-b1"}
    assert receipt["calls"][1]["call_id"] == "mock-run:entry/2"
    assert receipt["final_effect_id"] == "mock-effect-b1" and receipt["return_node"] == 1
    assert receipt["package_address"].startswith("package:")
    assert receipt["package_address_is_not_call_id"] is True


@pytest.mark.parametrize("mutation", ["last-return", "duplicate-effect", "duplicate-call", "wrong-input",
                                    "wrong-site", "wrong-link-hash", "wrong-program", "wrong-run-id"])
def test_identity_or_named_reference_errors_reject_even_when_b_bytes_match(mutation):
    result, events, link = mock_calls()
    if mutation == "last-return":
        result["final_reference"] = events[-2]["output_reference"]
        events[-1]["reference"] = result["final_reference"]
    elif mutation == "duplicate-effect":
        events[-2]["output_reference"] = deepcopy(events[2]["output_reference"])
    elif mutation == "duplicate-call":
        events[3]["call_id"] = events[1]["call_id"]
    elif mutation == "wrong-input":
        events[-2]["input_reference"] = events[2]["output_reference"]
    elif mutation == "wrong-site":
        link["call_sites"][0]["functional_address"] = "entry/1"
        link["receipt_sha256"] = demo.digest({k: v for k, v in link.items() if k != "receipt_sha256"})
    elif mutation == "wrong-link-hash":
        link["receipt_sha256"] = "0" * 64
    elif mutation == "wrong-program":
        result["selected_action"]["program"]["procedures"]["main"]["return"] = "v2"
    else:
        events[-2]["run_id"] = "foreign-run"
    with pytest.raises(demo.NativeDemoError):
        demo.check_call_mapping(result, events, link)


def test_zero_tick_identity_probe_truthfully_records_initial_database_write(tmp_path):
    identity = mock_reference()["runtime_identity"]
    closed = []
    class FakeBackend:
        def __init__(self, public, output, device):
            (output / "native.db").write_bytes(b"SYNTHETIC ZERO-TICK DATABASE ONLY")
            self.native = SimpleNamespace(store=SimpleNamespace(trace_events=lambda: []))
        def identity(self):
            return identity
        def head(self):
            return {"fixture": "zero-tick"}
        def close(self):
            closed.append(True)
    receipt = demo._identity_probe(SimpleNamespace(NativeBackend=FakeBackend), {}, tmp_path / "probe", "mock-no-device", identity)
    assert receipt["native_database_initialized"] is True and receipt["native_ticks_executed"] is False
    assert receipt["native_trace_count"] == 0 and closed == [True]
    with pytest.raises(demo.NativeDemoError, match="FRESH_RUNTIME_COMPATIBILITY_MISMATCH"):
        demo._identity_probe(SimpleNamespace(NativeBackend=FakeBackend), {}, tmp_path / "mismatch", "mock-no-device", {})
    assert (tmp_path / "mismatch/native.db").exists() and closed == [True, True]


def test_writer_uses_real_storage_and_closes_without_native_import(tmp_path, monkeypatch):
    synthetic_env(monkeypatch)
    package = mock_package()
    demo.save(tmp_path / "package.json", package)
    source = {"fixture": "NOT REAL NATIVE EVIDENCE"}
    request = {"job": "fixture_only_no_gpu", "package_digest": storage.package_digest(package)}
    monkeypatch.setattr(demo, "_request", lambda *_: (request, tmp_path, None, {"compatibility": package["compatibility"]}, package, None))
    monkeypatch.setattr(demo, "source_identity", lambda: source)
    monkeypatch.setattr(demo, "cuda_runtime", lambda *_: pytest.fail("WRITER_REACHED_CUDA"))
    receipt = demo.writer_stage(tmp_path / "mock_request", fake_hash("request"))
    assert receipt["registry_closed"] is True and receipt["native_execution_performed"] is False
    assert receipt["qualification_status"] == "UNQUALIFIED"
    assert receipt["storage_receipt"]["storage_status"] == "STORAGE_ONLY"
    with storage.ProcedureRegistry(tmp_path / "registry.db") as registry:
        assert registry.retrieve(request["package_digest"], trusted_compatibility=package["compatibility"], permitted_cjts=("A", "B")) == package
    assert "torch" not in sys.modules


def test_inventory_includes_both_roots_and_only_omits_two_top_level_files(tmp_path):
    output, native = tmp_path / "demo", tmp_path / "native"
    (output / "nested").mkdir(parents=True)
    native.mkdir()
    for path in (output / "file_index.json", output / "memory_demo_receipt.json",
                 output / "nested/file_index.json", output / "writer.stdout.log", native / "native.db"):
        path.write_bytes(b"FIXTURE ONLY")
    index = demo.inventory(output, native)
    assert index["schema"] == "cas-meta3-file-index/0.1"
    assert index["entries_sha256"] == demo.digest(index["entries"])
    assert {(row["root"], row["path"]) for row in index["entries"]} == {
        ("demo", "nested/file_index.json"), ("demo", "writer.stdout.log"), ("native", "native.db")}
    assert all(row["bytes"] == 12 and row["sha256"] == sha256(b"FIXTURE ONLY").hexdigest() for row in index["entries"])


def test_inventory_enforces_total_size_without_silent_omissions(tmp_path, monkeypatch):
    output, native = tmp_path / "demo", tmp_path / "native"
    output.mkdir()
    native.mkdir()
    (native / "native.db").write_bytes(b"FIXTURE ONLY")
    monkeypatch.setattr(demo, "MAX_OUTPUT_BYTES", 1)
    with pytest.raises(demo.NativeDemoError, match="MEMORY_EVIDENCE_SIZE_CEILING"):
        demo.inventory(output, native)


def test_json_evidence_rejects_overwrites_changed_hashes_and_duplicate_fields(tmp_path):
    path = tmp_path / "receipt.json"
    checksum = demo.save(path, {"fixture": True})
    assert demo.read(path, checksum) == {"fixture": True}
    with pytest.raises(FileExistsError):
        demo.save(path, {"changed": True})
    with pytest.raises(demo.NativeDemoError, match="JSON_FILE_DIGEST_MISMATCH"):
        demo.read(path, "0" * 64)
    (tmp_path / "duplicate.json").write_bytes(b'{"a":1,"a":2}')
    with pytest.raises(demo.NativeDemoError, match="DUPLICATE_JSON_FIELD"):
        demo.read(tmp_path / "duplicate.json")


def test_stage_parent_receipts_record_exit_before_a_reader_can_be_requested(tmp_path, monkeypatch):
    class FakeProcess:
        pid, returncode = 987654321, None
        def __init__(self, command, **kwargs):
            self.command = command
            assert kwargs["env"]["PYTHONPATH"] == os.pathsep.join(map(str, demo.child_source_paths()))
            assert "UNTRUSTED_INHERITED_PATH" not in kwargs["env"]["PYTHONPATH"]
        def wait(self, timeout):
            self.returncode = 0
            return 0
    monkeypatch.setattr(demo.subprocess, "Popen", FakeProcess)
    monkeypatch.setenv("PYTHONPATH", "UNTRUSTED_INHERITED_PATH")
    request = {"schema": "fixture-only", "stage": "writer"}
    result = demo.process_stage("writer", tmp_path, request, time.monotonic() + 10)
    assert result["stage"] == "writer" and result["returncode"] == 0
    assert result["pid"] == 987654321 and result["parent_pid"] == os.getpid()
    assert result["request_sha256"] == demo.file_hash(tmp_path / "writer_request.json")
    assert result["command"][2:5] == ["-m", "cas_meta3.native_demo", "--stage"]
    assert result["automatic_retries"] == 0
    assert result["python_source_paths"] == list(map(str, demo.child_source_paths()))
    assert not (tmp_path / "reader_request.json").exists()


def test_fresh_child_discovers_all_pinned_runtime_sources_without_neural_import(tmp_path):
    code = (
        "import sys,json,importlib.util;from tools.validate_local import NoNeuralImports;"
        "sys.meta_path.insert(0,NoNeuralImports());"
        "names=('cas_meta3.native_demo','cas_meta2.native','cas_meta1.execution',"
        "'cas_meta.compiler','cas_meta.executor','cas_meta.fixture');"
        "found={name:importlib.util.find_spec(name).origin for name in names};"
        "assert not any(name in sys.modules for name in ('torch','tensorflow','jax','casformer'));"
        "print(json.dumps(found))")
    completed = subprocess.run([sys.executable, "-B", "-c", code], cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(map(str, demo.child_source_paths())),
             "PYTHONDONTWRITEBYTECODE": "1", "CUDA_VISIBLE_DEVICES": ""},
        capture_output=True, text=True, check=True, timeout=30)
    found = json.loads(completed.stdout)
    paths = demo.child_source_paths()
    expected = {"cas_meta3.native_demo": paths[0] / "cas_meta3/native_demo.py",
        "cas_meta2.native": paths[1] / "cas_meta2/native.py", "cas_meta1.execution": paths[2] / "cas_meta1/execution.py",
        **{"cas_meta." + name: paths[3] / ("cas_meta/" + name + ".py") for name in ("compiler", "executor", "fixture")}}
    assert {name: Path(path).resolve() for name, path in found.items()} == expected


def test_source_has_no_neural_imports_or_runtime_root_override():
    text = Path(demo.__file__).read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(name.startswith(("torch", "tensorflow", "jax", "casformer", "numpy")) for name in imports)
    assert "native.ROOT =" not in text and "shutil.copy" not in text
    assert "native.verify_task(task, candidate, reference)" in text
    assert "native.verify_reference_task(task, reference)" in text
    assert "candidate_directory_exists_after" in text and "native_database_initialized" in text
    assert "torch" not in sys.modules
