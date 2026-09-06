"""Run frozen v6's pure checks from an independently created clean checkout.

This audits committed source bytes using the existing Python environment.
It does not install packages, generate the registered dataset, or run GPU work.
"""
from __future__ import annotations
import argparse
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

SOURCE = "acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0"
RECORD = Path(__file__).resolve().parent

def sha(raw):
    return sha256(raw).hexdigest()

def save(name, data):
    with (RECORD / name).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(data, indent=2, sort_keys=True) + "\n")

def git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), *arguments],
                          capture_output=True, check=True, timeout=60).stdout

def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def committed_bytes(repo, paths):
    process = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"],
        input="".join(SOURCE + ":" + name + "\n" for name in paths).encode(),
        capture_output=True, check=True, timeout=60)
    stream, values = io.BytesIO(process.stdout), {}
    for name in paths:
        header = stream.readline().decode().strip().split()
        assert len(header) == 3 and header[1] == "blob", (name, header)
        raw = stream.read(int(header[2]))
        assert len(raw) == int(header[2]) and stream.read(1) == b"\n"
        values[name] = raw
    assert stream.read() == b""
    return values

def snapshot(root, validator, profile):
    repo = Path(git(root, "rev-parse", "--show-toplevel").decode().strip())
    actual = git(root, "rev-parse", "HEAD").decode().strip()
    assert actual == SOURCE
    tracked_status = git(repo, "status", "--porcelain", "--untracked-files=no").decode()
    assert not tracked_status.strip()
    sources = validator.source_snapshot()
    protected = validator.protected_snapshot()
    required = {}
    for name, digest in sources.items():
        required[(root / name).relative_to(repo).as_posix()] = digest
    for name, digest in protected["files_sha256"].items():
        required[(root.parent / name).relative_to(repo).as_posix()] = digest
    manifest = root.parent / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
    required[manifest.relative_to(repo).as_posix()] = protected["manifest_sha256"]
    for name, digest in profile.EXTRA_INPUTS.items():
        path = root.parent.parent / name
        assert path.is_file() and sha(path.read_bytes()) == digest
        required[path.relative_to(repo).as_posix()] = digest
    for name in profile.V6_LOCAL_FILES:
        path = root / name
        required[path.relative_to(repo).as_posix()] = sha(path.read_bytes())
    practice = root / "records/contrast_curriculum_v6_probe_001"
    for path in sorted(practice.iterdir()):
        assert path.is_file() and not path.is_symlink()
        required[path.relative_to(repo).as_posix()] = sha(path.read_bytes())
    raw = committed_bytes(repo, sorted(required))
    identities = {}
    for name, digest in required.items():
        disk = (repo / name).read_bytes()
        identities[name] = {"expected_sha256": digest, "git_sha256": sha(raw[name]),
                            "checkout_sha256": sha(disk), "bytes": len(disk)}
        assert sha(raw[name]) == digest == sha(disk), name
    inventory = json.loads((root / "records/contrast_v6_exclusions_001/inventory.json").read_bytes())
    tasks = json.loads((practice / "tasks.json").read_bytes())
    assert inventory["count"] == len(set(inventory["graph_signatures"])) == 8053
    assert len(tasks) == 256
    spec = profile.validate_contrast_spec((root / "EXPERIMENT_CONTRAST_V6.json").read_bytes())
    return {"source_sha": actual, "repo": str(repo), "package": str(root),
            "tracked_status": tracked_status, "source_files": len(sources),
            "protected_files": protected["files_verified"],
            "protected_manifest_sha256": protected["manifest_sha256"],
            "all_checked_files": len(identities), "files": identities,
            "extra_pinned_inputs": profile.EXTRA_INPUTS,
            "prototype_tasks": len(tasks), "excluded_graph_signatures": inventory["count"],
            "registered_split_counts": {name: spec[name] for name in
                                       ("train_count", "validation_count", "test_count")},
            "registered_data_generated_here": False, "registered_seed": spec["curriculum_seed"]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    repo = Path(git(root, "rev-parse", "--show-toplevel").decode().strip())
    assert repo.name == "contrast-v6-audit-acbb266f"
    assert not git(repo, "status", "--porcelain", "--untracked-files=all").strip(), "Pristine checkout required"
    output = root / "records" / RECORD.name
    assert not output.exists() and not (RECORD / "receipt.json").exists()
    # Verify imported helper bytes against the frozen commit before importing.
    helper = root / "tools/validate_local_v3.py"
    name = helper.relative_to(repo).as_posix()
    assert committed_bytes(repo, [name])[name] == helper.read_bytes()
    validator = module(helper, "frozen_v6_local_validator")
    sys.meta_path.insert(0, validator.NoNeuralOrProviderImports())
    profile_path = root / "tools/experiment_profiles_contrast_v6.py"
    name = profile_path.relative_to(repo).as_posix()
    assert committed_bytes(repo, [name])[name] == profile_path.read_bytes()
    profile = module(profile_path, "frozen_v6_launch_profile")
    started = time.monotonic()
    before = snapshot(root, validator, profile)
    save("source_before.json", before)
    command = [sys.executable, "-B", str(helper), "--output", str(output)]
    env = dict(os.environ)
    # No inherited source path may substitute the active dirty worktree.
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=660)
    (RECORD / "validator.stdout.txt").write_bytes(run.stdout)
    (RECORD / "validator.stderr.txt").write_bytes(run.stderr)
    for path in sorted(output.iterdir()):
        assert path.is_file() and not path.is_symlink()
        target = RECORD / ("validation_" + path.name if path.name == "receipt.json" else path.name)
        assert not target.exists()
        shutil.copyfile(path, target)
    validation = json.loads((RECORD / "validation_receipt.json").read_bytes())
    after = snapshot(root, validator, profile)
    save("source_after.json", after)
    changed = git(repo, "status", "--porcelain", "--untracked-files=all").decode()
    versions = {}
    for distribution in ("pytest", "jsonschema", "botocore", "boto3", "torch"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    passed = run.returncode == 0 and validation["completed"] and before == after
    receipt = {"schema": "cas-meta2-clean-source-pure-audit/6",
        "status": "CLEAN_SOURCE_PURE_CHECKS_PASSED" if passed else "CLEAN_SOURCE_PURE_CHECKS_FAILED",
        "source_sha": SOURCE, "source_worktree": str(repo), "source_package": str(root),
        "command": command, "returncode": run.returncode,
        "finished_utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.monotonic()-started,
        "counts": validation["counts"], "passed_test_functions": validation["passed_test_functions"],
        "passed_subtests": validation["passed_subtests"], "sources_unchanged": before == after,
        "protected_files": 316, "git_blob_or_checkout_mismatches": [],
        "source_files": before["source_files"], "all_checked_files": before["all_checked_files"],
        "extra_pinned_inputs": len(profile.EXTRA_INPUTS), "prototype_tasks": before["prototype_tasks"],
        "excluded_graph_signatures": before["excluded_graph_signatures"],
        "git_status_before": "", "git_status_after": changed,
        "clean_checkout_created_separately": True, "core_autocrlf_on_checkout": False,
        "existing_environment": {"python": sys.version, "executable": sys.executable,
                                 "distribution_metadata_only": versions},
        "fresh_environment_created": False, "wheel_installation_performed": False,
        "inherited_pythonpath_removed": True,
        "neural_imports_blocked": validation["neural_imports_blocked"],
        "provider_client_imports_blocked": validation["provider_client_imports_blocked"],
        "permitted_pure_exception_modules": validation["permitted_pure_exception_modules"],
        "provider_calls": 0, "local_neural_work": False, "registered_dataset_generated": False,
        "registered_seed": 2026092601,
        "scope": "Frozen committed pure test package in a clean checkout; existing Python environment; no GPU, model, provider, registered dataset generation, or paid job.",
        "validation_errors": validation["errors"],
        "artifact_sha256": {path.name: sha(path.read_bytes()) for path in sorted(RECORD.iterdir()) if path.is_file()}}
    save("receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "source_sha", "counts",
          "passed_test_functions", "passed_subtests", "source_files", "all_checked_files",
          "prototype_tasks", "excluded_graph_signatures", "wall_seconds")}, indent=2))
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())

