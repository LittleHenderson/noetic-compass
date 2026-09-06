"""Cold portable v7 bridge proof; fixed exposed data only, never a GPU job."""
from __future__ import annotations
import faulthandler
import sys
if "--phase" in sys.argv:
    faulthandler.enable()
    faulthandler.dump_traceback_later(60, repeat=True)
    print("V7_BRIDGE_CHILD_STARTED", flush=True)
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import unittest
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL = ROOT / "records/prototype_training_integration_v7_001/checks_002/positive_merge/bundle"
ORIGINAL_PIN = "19162857679b3eb2e698c58ee8e0ac5dc3c7ffe7265e11e8ae1c726834067f29"
LOADER_PIN = "5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0"
BASE = ROOT / "records/contrast_v6_bundle_probe_001/dataset"
BASE_PIN = "36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1"
CONFIG = {"train_flat": 32, "train_pairs_per_cell": 8, "validation_flat": 8,
          "validation_pairs_per_cell": 2, "test_triplets": 3}
FORBIDDEN = {"torch", "tensorflow", "jax", "cupy", "casformer", "cas_cjt", "boto3", "botocore"}
RUNTIME_FILES = ["cas_meta2/contrast_v7/" + name + ".py" for name in
                 ("__init__", "data", "parent", "train", "checks", "evaluation")]
TEST_FILES = ["tests/test_contrast_v7_bridge.py", "records/contrast_v7_exclusions_001/build.py",
              "records/contrast_v7_exclusions_001/test_build.py"]
INTEGRATION = "records/prototype_training_integration_v7_001"

def digest(raw):
    return sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def read(path):
    path = Path(path).absolute()
    assert not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents))
    assert path.is_file() and path.stat().st_size <= 32*1024**2
    return path.read_bytes()

def save(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value) + b"\n")

class NoNeuralProvider(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN:" + fullname)
        return None

def snapshot(source):
    names = sorted(set(RUNTIME_FILES + TEST_FILES + list(source["frozen_files_sha256"])
                       + [INTEGRATION + "/adapter.py", INTEGRATION + "/public_data.py"]))
    result = {name: digest(read(ROOT / name)) for name in names}
    assert result[INTEGRATION + "/public_data.py"] == LOADER_PIN
    assert result[INTEGRATION + "/adapter.py"] == source["adapter_sha256"]
    assert all(result[name] == expected for name, expected in source["frozen_files_sha256"].items())
    return result

def install_api_traps(*, public=False):
    counts = {"subprocess_or_shell_attempts": 0, "network_attempts": 0,
              "private_read_attempts": 0, "parent_import_attempts": 0, "parser_or_generator_attempts": 0}
    parent_files = {(ROOT / name).resolve() for name in
                    (INTEGRATION+"/adapter.py", "cas_meta2/contrast_v7/parent.py",
                     "records/contrast_curriculum_v6_probe_001/build.py",
                     "records/contrast_curriculum_v6_probe_001/verify.py")}
    def audit(event, args):
        if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.spawn"}:
            counts["subprocess_or_shell_attempts"] += 1
            raise AssertionError("SUBPROCESS_OR_GIT_FORBIDDEN_DURING_API")
        if event in {"socket.connect", "socket.connect_ex", "socket.bind"}:
            counts["network_attempts"] += 1
            raise AssertionError("NETWORK_FORBIDDEN")
        if public and event == "open" and isinstance(args[0], (str, bytes)):
            name = os.fsdecode(args[0]).replace("\\", "/").rsplit("/", 1)[-1]
            if name == "test_private.json":
                counts["private_read_attempts"] += 1
                raise AssertionError("PRIVATE_FILE_READ_FORBIDDEN")
        if public and event == "exec":
            filename = getattr(args[0], "co_filename", "")
            if filename and not filename.startswith("<") and Path(filename).resolve() in parent_files:
                counts["parent_import_attempts"] += 1
                raise AssertionError("PARENT_CODE_IMPORT_FORBIDDEN")
    sys.addaudithook(audit)
    def forbidden(*args, **kwargs):
        counts["parser_or_generator_attempts"] += 1
        raise AssertionError("PARSER_OR_GENERATOR_FORBIDDEN")
    from cas_meta2 import curriculum, curriculum_v2, curriculum_v3
    from cas_meta2.contrast_v6 import curriculum as c
    for module in (curriculum, curriculum_v2, curriculum_v3, c):
        for name in ("generate", "generate_dataset", "_construct", "_legacy_dataset"):
            if hasattr(module, name):
                setattr(module, name, forbidden)
        if public and hasattr(module, "parse_problem"):
            setattr(module, "parse_problem", forbidden)
    if public:
        c.write = forbidden
    return counts

def parent_phase(plan):
    from cas_meta2.contrast_v7 import parent
    from cas_meta2.contrast_v6.curriculum import Config
    counts = install_api_traps()
    root = HERE / "roundtrip"
    options = dict(expected_sha256=BASE_PIN, seed=926603, config=Config(**CONFIG),
        excluded=frozenset(), pins=HERE/"source_pins.json",
        expected_pins_sha256=plan["source_pins_sha256"], expected_loader_sha256=LOADER_PIN)
    merge_receipt = parent.merge(root/"base_dataset", root/"dataset", **options)
    actual = {p.name: digest(read(p)) for p in (root/"dataset").iterdir()}
    assert actual == plan["original_bundle_sha256"] and len(actual) == 9
    assert merge_receipt["manifest_sha256"] == ORIGINAL_PIN
    options["expected_sha256"] = ORIGINAL_PIN
    export_receipt = parent.export_training_bundle(root/"dataset", root/"trainer_input", **options)
    assert not (root/"trainer_input/test_private.json").exists()
    exported = {p.name: digest(read(p)) for p in (root/"trainer_input").iterdir()}
    assert len(exported) == 8 and exported == {name: pin for name, pin in actual.items() if name != "test_private.json"}
    assert not any(counts.values())
    save(HERE/"parent_result.json", {"completed": True, "all_nine_parent_files_byte_identical": True,
        "merged": merge_receipt, "exported": export_receipt, "parent_file_sha256": actual,
        "public_file_sha256": exported, "traps": counts, "subprocess_git_calls_allowed": False,
        "parent_private_reads_permitted": True, "neural_or_provider_work": False})

def public_phase(plan):
    from cas_meta2.contrast_v7 import data
    from cas_meta2.contrast_v6.curriculum import Config
    assert not any(name.startswith("cas_meta2.contrast_v7.parent") for name in sys.modules)
    counts = install_api_traps(public=True)
    paths_before, hooks_before = list(sys.path), list(sys.meta_path)
    loads = []
    for _ in range(2):
        result = data.load_training_bundle(HERE/"roundtrip/trainer_input",
            expected_sha256=ORIGINAL_PIN, seed=926603, config=Config(**CONFIG),
            excluded=frozenset(), expected_loader_sha256=LOADER_PIN)
        assert (len(result["train"]), len(result["validation"]), len(result["test_public"])) == (352,24,9)
        assert result["receipt"]["private_labels_read_by_loader"] is False
        assert result["receipt"]["test_programs_parsed_by_loader"] is False
        assert result["receipt"]["parent_validation_replayed_by_loader"] is False
        assert result["tokenizer"].fitted_examples == 352
        loads.append(result["receipt"])
        assert list(sys.path) == paths_before and list(sys.meta_path) == hooks_before
    assert loads[0] == loads[1] and not any(counts.values())
    assert not any(name.startswith("cas_meta2.contrast_v7.parent") for name in sys.modules)
    assert not any(name.split(".")[0] in FORBIDDEN for name in sys.modules)
    save(HERE/"public_result.json", {"completed": True, "fresh_child": True, "load_count": 2,
        "receipts_equal": True, "loader_added_import_hooks": False, "loader_changed_sys_path": False,
        "traps": counts, "loads": loads, "private_test_data_opened": False,
        "test_programs_parsed": False, "parent_api_called": False, "neural_or_provider_work": False})

def unit_phase(phase):
    path = ROOT / (TEST_FILES[0] if phase == "bridge" else TEST_FILES[2])
    spec = importlib.util.spec_from_file_location("portable_v7_" + phase + "_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    class Result(unittest.TextTestResult):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.passed_ids, self.subtest_count = [], 0
        def addSuccess(self, test):
            self.passed_ids.append(test.id())
            return super().addSuccess(test)
        def addSubTest(self, test, subtest, err):
            self.subtest_count += 1
            return super().addSubTest(test, subtest, err)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    expected = 12 if phase == "bridge" else 8
    save(HERE/(phase+"_tests.json"), {"tests": result.testsRun, "expected_tests": expected,
        "subtests": result.subtest_count, "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "passed_ids": result.passed_ids,
        "completed": result.wasSuccessful() and result.testsRun == expected,
        "boundary": "Separate pure process; synthetic exposure tests open no completed experiment data."})
    assert result.wasSuccessful() and result.testsRun == expected

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("parent", "public", "bridge", "exposure"))
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    sys.meta_path.insert(0, NoNeuralProvider())
    if args.phase:
        try:
            plan = json.loads(read(HERE/"plan.json"))
            before = snapshot(plan["source"])
            if args.phase == "parent":
                parent_phase(plan)
            elif args.phase == "public":
                public_phase(plan)
            else:
                unit_phase(args.phase)
            assert before == snapshot(plan["source"])
            return 0
        finally:
            faulthandler.cancel_dump_traceback_later()
    assert not (HERE/"plan.json").exists() and not (HERE/"receipt.json").exists()
    original_raw = read(ORIGINAL/"manifest.json")
    assert digest(original_raw) == ORIGINAL_PIN
    original = json.loads(original_raw)
    assert original["base"]["seed"] == 926603
    base_raw = read(BASE/"manifest.json")
    assert digest(base_raw) == BASE_PIN
    base = json.loads(base_raw)
    assert base["seed"] == 926603 and base["config"] == CONFIG
    files = {p.name: digest(read(p)) for p in ORIGINAL.iterdir()}
    assert files == {**original["sha256"], "manifest.json": ORIGINAL_PIN} and len(files) == 9
    before = snapshot(original["source"])
    pins_raw = canonical(original["source"]) + b"\n"
    (HERE/"source_pins.json").write_bytes(pins_raw)
    root = HERE/"roundtrip"
    (root/"base_dataset").mkdir(parents=True, exist_ok=False)
    for name in ("manifest.json", "train.json", "validation.json", "test_public.json", "test_private.json"):
        raw = read(BASE/name)
        assert digest(raw) == (BASE_PIN if name == "manifest.json" else base["sha256"][name])
        with (root/"base_dataset"/name).open("xb") as stream:
            stream.write(raw)
    plan = {"source": original["source"], "source_pins_sha256": digest(pins_raw),
            "source_before": before, "original_bundle_sha256": files, "base_manifest_sha256": BASE_PIN,
            "loader_sha256": LOADER_PIN, "original_manifest_sha256": ORIGINAL_PIN, "fixture_seed": 926603}
    save(HERE/"plan.json", plan)
    homebases = [p for p in HERE.parents if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"]
    scratch = homebases[-1]/"_tmp"/("prototype-v7-bridge-"+uuid4().hex[:12])
    assert scratch.parent.resolve() == (homebases[-1]/"_tmp").resolve()
    assert not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (scratch,*scratch.parents))
    (scratch/"temp").mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTEST_ADDOPTS="", PYTEST_PLUGINS="", CUDA_VISIBLE_DEVICES="", CAS_META1_RUN_GPU_TESTS="0",
        CAS_META2_RUN_GPU_TESTS="0", TEMP=str(scratch/"temp"), TMP=str(scratch/"temp"), TMPDIR=str(scratch/"temp"))
    env.pop("PYTHONPATH", None)
    started, processes = time.monotonic(), []
    for phase in ("parent", "public", "bridge", "exposure"):
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--phase", phase]
        launch_utc = datetime.now(timezone.utc).isoformat()
        timed_out = False
        try:
            run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=180)
        except subprocess.TimeoutExpired as error:
            timed_out = True
            run = subprocess.CompletedProcess(command, 124, error.stdout or b"", error.stderr or b"")
        (HERE/(phase+".stdout.txt")).write_bytes(run.stdout)
        (HERE/(phase+".stderr.txt")).write_bytes(run.stderr)
        processes.append({"phase": phase, "command": command, "cwd": str(ROOT), "returncode": run.returncode,
            "started_utc": launch_utc, "finished_utc": datetime.now(timezone.utc).isoformat(),
            "timed_out": timed_out, "stdout_sha256": digest(run.stdout), "stderr_sha256": digest(run.stderr)})
        print(json.dumps(processes[-1]), flush=True)
        if run.returncode != 0:
            break
    after = snapshot(original["source"])
    success = len(processes) == 4 and all(row["returncode"] == 0 for row in processes) and before == after
    receipt = {"schema": "cas-meta2-portable-v7-bridge-proof/7",
        "status": "PORTABLE_PARENT_AND_PUBLIC_BRIDGE_CHECKS_PASSED" if success else "PORTABLE_BRIDGE_CHECK_FAILED",
        "completed": success, "processes": processes, "source_before": before, "source_after": after,
        "source_unchanged": before == after, "source_anchor": "Externally pinned original merged manifest and public-loader SHA",
        "original_manifest_sha256": ORIGINAL_PIN, "loader_sha256": LOADER_PIN,
        "source_pins_sha256": digest(pins_raw), "fixture_seed": 926603,
        "python": sys.version, "executable": sys.executable, "existing_environment": True,
        "scratch": str(scratch), "scratch_retained": True, "wall_seconds": time.monotonic()-started,
        "neural_or_provider_work": False, "registered_dataset_opened_or_generated": False,
        "training_performed": False, "boundary": "Cold pure preparation proof, not AWS execution or model learning.",
        "artifact_sha256": {p.name: digest(read(p)) for p in sorted(HERE.iterdir()) if p.is_file()}}
    save(HERE/"receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "completed", "source_unchanged", "wall_seconds")}, indent=2))
    return 0 if success else 1

if __name__ == "__main__":
    raise SystemExit(main())

