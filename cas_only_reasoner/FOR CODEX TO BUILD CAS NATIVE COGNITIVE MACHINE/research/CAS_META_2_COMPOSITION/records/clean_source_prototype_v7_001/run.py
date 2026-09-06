"""Clean-source v7 audit. Uses only exact committed source and known diagnostic inputs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

SOURCE = "80e44f20a3f2c66a62754212729ce6e11ff9c8fe"
RECORD = Path(__file__).resolve().parent
REPO = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/contrast-v7-audit-80e44f20")
ROOT = REPO / "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION"
OUTER = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
INTEGRATION = ROOT / "records/prototype_training_integration_v7_001"
BRIDGE = ROOT / "records/clean_source_v7_bridge_001"
FULL_OUTPUT = ROOT / "records/clean_source_prototype_v7_001/full_validation"
ADAPTER_OUTPUT = INTEGRATION / "checks_clean_source_001"
LOADER_PIN = "5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0"

def digest(raw):
    return sha256(raw).hexdigest()

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode()+b"\n")

def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, check=True, timeout=60).stdout

def committed(paths):
    result = subprocess.run(["git", "-C", str(REPO), "cat-file", "--batch"],
        input="".join(SOURCE + ":" + path + "\n" for path in paths).encode(),
        capture_output=True, check=True, timeout=60)
    stream, values = io.BytesIO(result.stdout), {}
    for path in paths:
        header = stream.readline().decode().strip().split()
        assert len(header) == 3 and header[1] == "blob", (path, header)
        raw = stream.read(int(header[2]))
        assert len(raw) == int(header[2]) and stream.read(1) == b"\n"
        values[path] = raw
    assert stream.read() == b""
    return values

def checked_module(path, name):
    key = path.relative_to(REPO).as_posix()
    assert committed([key])[key] == path.read_bytes()
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def snapshot(validator, profile):
    assert git("rev-parse", "HEAD").decode().strip() == SOURCE
    tracked = git("status", "--porcelain", "--untracked-files=no").decode()
    assert not tracked.strip()
    sources, protected = validator.source_snapshot(), validator.protected_snapshot()
    required = {(ROOT / name).relative_to(REPO).as_posix(): pin for name, pin in sources.items()}
    for name, pin in protected["files_sha256"].items():
        required[(ROOT.parent / name).relative_to(REPO).as_posix()] = pin
    path = ROOT.parent / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
    required[path.relative_to(REPO).as_posix()] = protected["manifest_sha256"]
    for name, pin in profile.EXTRA_INPUTS.items():
        required[(ROOT.parent.parent / name).relative_to(REPO).as_posix()] = pin
    for name in profile.V6_LOCAL_FILES:
        path = ROOT / name
        required[path.relative_to(REPO).as_posix()] = digest(path.read_bytes())
    # Explicitly select preparation files, not the current v6 campaign/result records.
    selected = []
    for directory in ("records/contrast_curriculum_v6_probe_001",
                      "records/contrast_v6_bundle_probe_001/dataset",
                      "records/prototype_training_integration_v7_001",
                      "records/contrast_v7_bridge_checks_001",
                      "records/contrast_v7_exclusions_001"):
        prefix = (ROOT / directory).relative_to(REPO).as_posix()
        for name in git("ls-files", "-z", "--", prefix).decode().split("\0"):
            if name:
                required[name] = digest((REPO / name).read_bytes())
                selected.append(name)
    raw = committed(sorted(required))
    identities = {}
    for name, expected in sorted(required.items()):
        disk = (REPO / name).read_bytes()
        identities[name] = {"expected_sha256": expected, "git_sha256": digest(raw[name]),
                            "checkout_sha256": digest(disk), "bytes": len(disk)}
        assert digest(raw[name]) == expected == digest(disk), name
    original = json.loads((INTEGRATION / "checks_002/positive_merge/bundle/manifest.json").read_bytes())
    assert original["base"]["seed"] == 926603
    tasks = json.loads((ROOT / "records/contrast_curriculum_v6_probe_001/tasks.json").read_bytes())
    assert len(tasks) == 256
    pins = ROOT / "records/contrast_v7_bridge_checks_001/source_pins.json"
    assert json.loads(pins.read_bytes()) == original["source"]
    assert digest((INTEGRATION / "public_data.py").read_bytes()) == LOADER_PIN
    return {"source_sha": SOURCE, "tracked_status": tracked,
            "source_files": len(sources), "protected_files": protected["files_verified"],
            "protected_manifest_sha256": protected["manifest_sha256"],
            "all_checked_files": len(identities), "files": identities,
            "preparation_input_files": len(set(selected)), "original_tasks": len(tasks),
            "known_fixture_seed": 926603, "no_current_campaign_inputs": True}

def copy_top_records(source, target):
    target.mkdir(parents=True, exist_ok=False)
    for path in sorted(source.iterdir()):
        if path.is_file():
            assert not path.is_symlink() and not getattr(path, "is_junction", lambda: False)()
            shutil.copyfile(path, target / path.name)

def run_stage(name, command, env, timeout):
    started = datetime.now(timezone.utc).isoformat()
    print(json.dumps({"stage": name, "state": "started", "utc": started}), flush=True)
    monotonic = time.monotonic()
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired as error:
        result = subprocess.CompletedProcess(command, 124, error.stdout or b"", error.stderr or b"")
        timed_out = True
    with (RECORD / (name + ".stdout.txt")).open("xb") as stream:
        stream.write(result.stdout)
    with (RECORD / (name + ".stderr.txt")).open("xb") as stream:
        stream.write(result.stderr)
    receipt = {"name": name, "command": command, "cwd": str(ROOT), "returncode": result.returncode,
               "timeout_seconds": timeout, "timed_out": timed_out, "started_utc": started,
               "finished_utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.monotonic()-monotonic,
               "stdout_sha256": digest(result.stdout), "stderr_sha256": digest(result.stderr)}
    save(RECORD / (name + ".process.json"), receipt)
    print(json.dumps(receipt), flush=True)
    return receipt

def main():
    assert not (RECORD / "source_before.json").exists()
    initial = git("status", "--porcelain", "--untracked-files=all").decode()
    assert not initial.strip(), "PRISTINE_CHECKOUT_REQUIRED"
    validator = checked_module(ROOT / "tools/validate_local_v3.py", "clean_v7_validator")
    sys.meta_path.insert(0, validator.NoNeuralOrProviderImports())
    profile = checked_module(ROOT / "tools/experiment_profiles_contrast_v6.py", "clean_v7_profile")
    before = snapshot(validator, profile)
    save(RECORD / "source_before.json", before)
    assert not any(path.exists() for path in (BRIDGE, FULL_OUTPUT, ADAPTER_OUTPUT))
    BRIDGE.mkdir()
    original_runner = ROOT / "records/contrast_v7_bridge_checks_001/run.py"
    shutil.copyfile(original_runner, BRIDGE / "run.py")
    assert (BRIDGE / "run.py").read_bytes() == original_runner.read_bytes()
    scratch = OUTER / "_tmp" / ("prototype-v7-clean-" + uuid4().hex[:12])
    assert scratch.parent.resolve() == (OUTER / "_tmp").resolve()
    assert not scratch.exists()
    for path in (scratch, *scratch.parents):
        assert not path.is_symlink() and not getattr(path, "is_junction", lambda: False)()
    (scratch / "temp").mkdir(parents=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTEST_ADDOPTS="", PYTEST_PLUGINS="", CUDA_VISIBLE_DEVICES="",
        CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0",
        TEMP=str(scratch/"temp"), TMP=str(scratch/"temp"), TMPDIR=str(scratch/"temp"))
    env.pop("PYTHONPATH", None)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=1) as pool:
        full = pool.submit(run_stage, "full_validator",
            [sys.executable, "-B", str(ROOT/"tools/validate_local_v3.py"), "--output", str(FULL_OUTPUT)], env, 660)
        stages = []
        stages.append(run_stage("portable_bridge", [sys.executable, "-B", str(BRIDGE/"run.py")], env, 780))
        stages.append(run_stage("adapter", [sys.executable, "-B", str(INTEGRATION/"run_checks.py"),
            "--run-name", ADAPTER_OUTPUT.name], env, 660))
        stages.append(run_stage("public", [sys.executable, "-B", str(INTEGRATION/"test_public_data.py")], env, 180))
        stages.append(full.result())
    after = snapshot(validator, profile)
    save(RECORD / "source_after.json", after)
    copied = {}
    for name, location in (("full_validator_artifacts", FULL_OUTPUT), ("adapter_artifacts", ADAPTER_OUTPUT),
                           ("portable_bridge_artifacts", BRIDGE)):
        if location.exists():
            copy_top_records(location, RECORD/name)
            copied[name] = {"source": str(location),
                "files_sha256": {path.name: digest(path.read_bytes()) for path in sorted((RECORD/name).iterdir())}}
    full_receipt = json.loads((FULL_OUTPUT/"receipt.json").read_bytes()) if (FULL_OUTPUT/"receipt.json").exists() else None
    adapter_receipt = json.loads((ADAPTER_OUTPUT/"receipt.json").read_bytes()) if (ADAPTER_OUTPUT/"receipt.json").exists() else None
    bridge_receipt = json.loads((BRIDGE/"receipt.json").read_bytes()) if (BRIDGE/"receipt.json").exists() else None
    versions = {}
    for distribution in ("pytest", "jsonschema", "botocore", "boto3", "torch"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    success = all(stage["returncode"] == 0 for stage in stages) and before == after
    success = success and full_receipt and full_receipt["completed"] and bridge_receipt and bridge_receipt["completed"]
    success = bool(success and adapter_receipt and adapter_receipt["sources_unchanged"])
    receipt = {"schema": "cas-meta2-clean-source-preparation-audit/7",
        "status": "CLEAN_SOURCE_V7_PREPARATION_CHECKS_PASSED" if success else "CLEAN_SOURCE_V7_PREPARATION_CHECKS_FAILED",
        "completed": success, "source_sha": SOURCE, "source_worktree": str(REPO), "source_package": str(ROOT),
        "initial_git_status": initial, "final_git_status": git("status", "--porcelain", "--untracked-files=all").decode(),
        "source_unchanged": before == after, "source_files": before["source_files"],
        "protected_files": before["protected_files"], "all_checked_files": before["all_checked_files"],
        "git_blob_or_checkout_mismatches": [], "preparation_input_files": before["preparation_input_files"],
        "processes": stages, "raw_artifacts": copied, "wall_seconds": time.monotonic()-started,
        "full_validator": {key: full_receipt.get(key) for key in ("completed", "counts", "passed_test_functions",
            "passed_subtests", "sources_unchanged", "protected_unchanged")} if full_receipt else None,
        "adapter": {key: adapter_receipt.get(key) for key in ("returncode", "counts", "sources_unchanged")} if adapter_receipt else None,
        "public_tests": {"expected_methods": 18, "count_evidence": "public.stderr.txt"},
        "bridge": {"completed": bridge_receipt["completed"], "copied_runner_sha256": digest(original_runner.read_bytes()),
                   "receipt_path": str(BRIDGE/"receipt.json")} if bridge_receipt else None,
        "do_not_sum_overlapping_suites": True, "existing_environment": {"python": sys.version,
            "executable": sys.executable, "distribution_metadata_only": versions},
        "fresh_installation": False, "scratch": str(scratch), "scratch_retained": True,
        "inherited_pythonpath_removed": True, "core_autocrlf_on_checkout": False,
        "neural_or_provider_work": False, "registered_dataset_generated": False, "current_v6_data_opened": False,
        "boundary": "Clean committed preparation source and saved diagnostic seed926603 only; not GPU training, release installation, or held-out learning."}
    save(RECORD/"receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "completed", "full_validator", "adapter",
          "source_files", "all_checked_files", "source_unchanged", "wall_seconds")}, indent=2), flush=True)
    return 0 if success else 1

if __name__ == "__main__":
    raise SystemExit(main())

