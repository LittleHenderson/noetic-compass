"""Scoped retries of one preserved Windows receipt-replacement failure."""
import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

HERE = Path(__file__).resolve().parent
SOURCE = "4bbb91628ad5b5f7e32d33eb8f7f07fedaa05a3e"
OUTER = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
REPO = OUTER / "_worktrees/prototype-v7-audit-4bbb9162"
ROOT = REPO / "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION"
TARGETS = {
    "single": "tests/test_ablation_campaign_v4.py::test_simulated_parent_order_and_failures[False-True]",
    "file": "tests/test_ablation_campaign_v4.py",
}
FAILED = OUTER / "_tmp/meta2v3-daf842cd5ea8/pytest/test_simulated_parent_order_an2/campaign"

def checked(path, name):
    raw = subprocess.check_output(["git", "-C", str(REPO), "cat-file", "blob",
                                   SOURCE + ":" + path.relative_to(REPO).as_posix()])
    assert raw == path.read_bytes(), str(path)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def child(mode, output, scratch):
    validator = checked(ROOT / "tools/validate_local_v3.py", "retry_canonical_guard")
    assert not any(validator.forbidden_import(name) for name in sys.modules)
    sys.meta_path.insert(0, validator.NoNeuralOrProviderImports())
    sys.path.insert(0, str(ROOT))
    validator.no_links(output)
    validator.no_links(scratch)
    assert output.is_dir() and output.resolve().is_relative_to(ROOT / "records")
    assert scratch.parent.resolve() == (OUTER / "_tmp").resolve()
    assert scratch.name.startswith("meta2v7-retry-") and (scratch / "temp").is_dir()
    assert not (scratch / "pytest").exists() and not (output / "tests.xml").exists()
    import pytest
    command = [TARGETS[mode], "-q", "-m", "not gpu", "-p", "no:cacheprovider",
               "--basetemp=" + str(scratch / "pytest"), "--junitxml=" + str(output / "tests.xml")]
    result = pytest.main(command)
    forbidden = [name for name in sys.modules if validator.forbidden_import(name)]
    assert not forbidden, forbidden
    validator.save_json(output / "child_receipt.json", {
        "mode": mode, "source_sha": SOURCE, "pytest_arguments": command, "returncode": result,
        "cwd": str(Path.cwd()), "python": sys.version, "source_test": TARGETS[mode],
        "forbidden_modules": forbidden, "canonical_guard_unchanged": True,
        "provider_calls": False, "neural_execution": False, "registered_task_generation": False,
        "saved_fixture_only": True, "scratch": str(scratch), "pid": os.getpid()})
    return result

def metadata():
    values = []
    for name in ("campaign_receipt.json", "campaign_receipt.json.tmp"):
        path = FAILED / name
        row = {"path": str(path), "exists": path.exists()}
        if path.exists():
            state = path.stat()
            row.update(bytes=state.st_size, mode=oct(state.st_mode),
                       windows_file_attributes=getattr(state, "st_file_attributes", None),
                       mtime_ns=state.st_mtime_ns, sha256=sha256(path.read_bytes()).hexdigest())
        values.append(row)
    return {"failed_files": values, "inspection": "Read/stat/hash only; no replacement, permission edit, or deletion.",
            "path_contains_onedrive": "OneDrive" in FAILED.parts,
            "onedrive_lock_or_other_owner_identified": False}

def main():
    output = HERE / "outputs"
    assert not output.exists()
    output.mkdir()
    helper = checked(ROOT / "records/clean_source_prototype_v7_002/run.py", "committed_clean_audit_helpers")
    audit = helper.Audit(SOURCE, output)
    audit.validator = audit.checked_module("tools/validate_local_v3.py", "retry_validator")
    assert not any(audit.validator.forbidden_import(name) for name in sys.modules)
    sys.meta_path.insert(0, audit.validator.NoNeuralOrProviderImports())
    audit.profile = audit.checked_module("tools/experiment_profiles_prototype_v7.py", "retry_profile")
    audit.builder = audit.checked_module("tools/build_launch_bundle_prototype_v7.py", "retry_builder")
    before = audit.snapshot()
    helper.save(output / "source_before.json", before)
    assert not before["git_blob_or_checkout_mismatches"] and not before["tracked_status"]
    helper.save(output / "failed_files_before.json", metadata())
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTEST_ADDOPTS="", PYTEST_PLUGINS="", CUDA_VISIBLE_DEVICES="",
        CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0", CAS_META2_RUN_DECODER_ABLATION="0")
    env.pop("PYTHONPATH", None)
    results = {}
    for mode in ("single", "file"):
        destination = ROOT / "records/clean_source_prototype_v7_002/diagnosis_001" / mode
        helper.no_links(destination)
        assert not destination.exists()
        destination.mkdir(parents=True)
        scratch = OUTER / "_tmp" / ("meta2v7-retry-" + uuid4().hex[:12])
        helper.no_links(scratch)
        assert not scratch.exists()
        (scratch / "temp").mkdir(parents=True)
        stage_env = dict(env, TEMP=str(scratch / "temp"), TMP=str(scratch / "temp"),
                         TMPDIR=str(scratch / "temp"))
        process = audit.stage(mode, [sys.executable, "-B", str(Path(__file__).resolve()),
            "--child", mode, "--output", str(destination), "--scratch", str(scratch)],
            ROOT, 180, stage_env)
        xml = destination / "tests.xml"
        results[mode] = {"process": process, "junit": audit.validator.junit_counts(xml),
                         "scratch": str(scratch), "destination": str(destination)}
        for path in destination.iterdir():
            if path.is_file():
                helper.write(output / mode / path.name, helper.read(path))
        if process["timed_out"]:
            break
    after = audit.snapshot()
    helper.save(output / "source_after.json", after)
    helper.save(output / "failed_files_after.json", metadata())
    helper.save(output / "git_commands.json", audit.commands)
    passed = len(results) == 2 and all(row["process"]["returncode"] == 0 for row in results.values())
    result = {"source_sha": SOURCE, "source_unchanged": before == after, "checked_files": before["all_checked_files"],
        "closed_files": before["closed_v7_source_files"], "protected_files": before["protected_files"],
        "all_retries_passed": passed, "results": results,
        "original_failure_receipt": str(HERE.parent / "run_002/receipt.json"),
        "original_failure_receipt_sha256": sha256((HERE.parent / "run_002/receipt.json").read_bytes()).hexdigest(),
        "classification": "NOT_REPRODUCED_IN_TWO_SCOPED_RETRIES" if passed else "SEE_EXACT_RETRY_FAILURES",
        "initial_full_suite_failure_preserved": True, "full_suite_rerun": False,
        "cause_identified": False, "old_files_modified": False, "production_or_tests_changed": False,
        "neural_or_provider_execution": False, "registered_task_generation": False,
        "boundary": "Scoped pure retries only. A passing retry does not erase the earlier full-suite failure or establish the cause."}
    helper.save(output / "receipt.json", result)
    print(json.dumps(result, indent=2), flush=True)
    return 0 if passed and before == after else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", choices=TARGETS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    raise SystemExit(child(args.child, args.output, args.scratch) if args.child else main())
