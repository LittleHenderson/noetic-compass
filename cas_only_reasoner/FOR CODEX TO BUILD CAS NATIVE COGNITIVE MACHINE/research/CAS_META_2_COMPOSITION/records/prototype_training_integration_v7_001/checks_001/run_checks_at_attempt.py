"""Run audit-only tests and a saved-fixture merge in a guarded child."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OWN_FILES = ("adapter.py", "test_adapter.py", "run_checks.py")

def write(name, value):
    path = HERE / name
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--run-name", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(HERE))
    import adapter as a
    if args.child:
        sys.meta_path.insert(0, a.Guard())
        import pytest
        output = HERE / args.run_name
        return pytest.main([str(HERE / "test_adapter.py"), "-q", "-p", "no:cacheprovider",
            "--basetemp=" + str(output / "temp"), "--junitxml=" + str(output / "tests.xml")])
    output = HERE / args.run_name
    if output.exists() or "/" in args.run_name or "\\" in args.run_name:
        raise ValueError("NEW_LOCAL_CHECK_RECORD_REQUIRED")
    output.mkdir()
    source_before = a.source_identity()
    source_files = {name: a.digest(a.read(HERE / name)) for name in OWN_FILES}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTEST_ADDOPTS="", PYTEST_PLUGINS="", CUDA_VISIBLE_DEVICES="",
               CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0")
    env.pop("PYTHONPATH", None)
    # Keep all Python temporary output in the designated record subtree.
    temp = output / "process_temp"
    temp.mkdir()
    env.update(TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp))
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", "--run-name", args.run_name]
    started = time.monotonic()
    run = subprocess.run(command, cwd=a.ROOT, env=env, capture_output=True, timeout=600)
    (output / "stdout.txt").write_bytes(run.stdout)
    (output / "stderr.txt").write_bytes(run.stderr)
    receipt = {"schema": "cas-meta2-prototype-integration-pure-checks/7",
        "command": command, "returncode": run.returncode,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic()-started,
        "source_before": source_before, "source_after": a.source_identity(),
        "adapter_test_runner_sha256": source_files,
        "sources_unchanged": source_before == a.source_identity()
            and source_files == {name: a.digest(a.read(HERE / name)) for name in OWN_FILES},
        "python": sys.version, "pytest": importlib.metadata.version("pytest"),
        "fixture_seed": 926603, "registered_seed_generated": False,
        "neural_or_provider_work": False, "training_performed": False,
        "stdout_sha256": a.digest(run.stdout), "stderr_sha256": a.digest(run.stderr)}
    import xml.etree.ElementTree as ET
    suites = ET.parse(output / "tests.xml").getroot().findall("testsuite")
    receipt["counts"] = {key: sum(int(s.get(key, "0")) for s in suites)
                         for key in ("tests", "failures", "errors", "skipped")}
    write(args.run_name + "/receipt.json", receipt)
    print(run.stdout.decode(errors="replace"))
    print(json.dumps({k: receipt[k] for k in ("returncode", "counts", "sources_unchanged", "wall_seconds")}, indent=2))
    return run.returncode

if __name__ == "__main__":
    raise SystemExit(main())
