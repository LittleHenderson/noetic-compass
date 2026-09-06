"""Scoped bridge-hook regression and unchanged full validator; pure work only."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FOCUSED = ["tests/test_contrast_v7_bridge.py",
    "tests/test_launch.py::LaunchTests::test_cleanup_deletes_owned_role_when_policy_already_absent",
    "tests/test_launch.py::LaunchTests::test_cleanup_will_not_delete_untagged_security_group",
    "tests/test_validate_local_v3.py::test_real_sdk_exception_import_works_without_live_client_modules"]

def sha(path):
    return sha256(path.read_bytes()).hexdigest()

def save(path, value):
    with path.open("xb") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode()+b"\n")

def helper():
    path = ROOT/"tools/validate_local_v3.py"
    spec = importlib.util.spec_from_file_location("scope_fix_canonical_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("focused", "full"), required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    output = HERE/args.stage
    validator = helper()
    if args.child:
        assert args.stage == "focused" and args.scratch
        sys.path.insert(0, str(ROOT))
        assert not any(validator.forbidden_import(name) for name in sys.modules)
        sys.meta_path.insert(0, validator.NoNeuralOrProviderImports())
        import pytest
        return pytest.main([*FOCUSED, "-q", "-p", "no:cacheprovider",
            "--basetemp="+str(args.scratch/"pytest"), "--junitxml="+str(output/"tests.xml")])
    assert not output.exists()
    output.mkdir()
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          check=True, capture_output=True, timeout=60).stdout.decode().strip()
    watched = {"tests/test_contrast_v7_bridge.py", "tools/validate_local_v3.py",
               "tests/test_launch.py", "tests/test_validate_local_v3.py", "aws/launch.py"}
    watched.update(p.relative_to(ROOT).as_posix() for p in (ROOT/"cas_meta2/contrast_v7").glob("*.py"))
    before = {name: sha(ROOT/name) for name in sorted(watched)}
    outer = [p for p in ROOT.parents if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"][-1]
    scratch = outer/"_tmp"/("v7-guard-"+uuid4().hex[:12])
    assert scratch.parent.resolve() == (outer/"_tmp").resolve() and not scratch.exists()
    for path in (scratch, *scratch.parents):
        assert not path.is_symlink() and not getattr(path, "is_junction", lambda: False)()
    (scratch/"temp").mkdir(parents=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTEST_ADDOPTS="", PYTEST_PLUGINS="", CUDA_VISIBLE_DEVICES="",
        CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0",
        TEMP=str(scratch/"temp"), TMP=str(scratch/"temp"), TMPDIR=str(scratch/"temp"))
    env.pop("PYTHONPATH", None)
    command = ([sys.executable, "-B", str(Path(__file__).resolve()), "--stage", "focused",
                "--child", "--scratch", str(scratch)] if args.stage == "focused" else
               [sys.executable, "-B", str(ROOT/"tools/validate_local_v3.py"),
                "--output", str(output/"validator")])
    started, started_utc = time.monotonic(), datetime.now(timezone.utc).isoformat()
    try:
        run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=660)
        timed_out = False
    except subprocess.TimeoutExpired as error:
        run = subprocess.CompletedProcess(command, 124, error.stdout or b"", error.stderr or b"")
        timed_out = True
    (output/"stdout.txt").write_bytes(run.stdout)
    (output/"stderr.txt").write_bytes(run.stderr)
    after = {name: sha(ROOT/name) for name in sorted(watched)}
    receipt = {"schema": "cas-meta2-scoped-bridge-guard-check/1", "stage": args.stage,
        "command": command, "cwd": str(ROOT), "returncode": run.returncode, "timed_out": timed_out,
        "started_utc": started_utc, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic()-started, "head_at_start": head,
        "watched_source_before": before, "watched_source_after": after,
        "watched_sources_unchanged": before == after,
        "stdout_sha256": sha(output/"stdout.txt"), "stderr_sha256": sha(output/"stderr.txt"),
        "python": sys.version, "executable": sys.executable, "existing_environment": True,
        "scratch": str(scratch), "scratch_retained": True, "neural_or_provider_work": False,
        "current_v6_data_opened": False, "registered_dataset_generated": False}
    if args.stage == "full" and (output/"validator/receipt.json").exists():
        full = json.loads((output/"validator/receipt.json").read_bytes())
        receipt["validator"] = {key: full.get(key) for key in ("completed", "counts", "passed_test_functions",
            "passed_subtests", "sources_unchanged", "protected_unchanged", "errors")}
    xml = output/"tests.xml"
    if xml.exists():
        suites = ET.parse(xml).getroot().findall("testsuite")
        receipt["counts"] = {key: sum(int(item.get(key, "0")) for item in suites)
                            for key in ("tests", "failures", "errors", "skipped")}
    save(output/"receipt.json", receipt)
    print(run.stdout.decode(errors="replace"), flush=True)
    print(json.dumps(receipt, indent=2), flush=True)
    return 0 if run.returncode == 0 and before == after else 1

if __name__ == "__main__":
    raise SystemExit(main())

