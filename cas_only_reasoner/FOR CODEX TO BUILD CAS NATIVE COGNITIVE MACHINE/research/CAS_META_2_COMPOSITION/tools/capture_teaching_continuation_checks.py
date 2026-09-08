"""Capture guarded, fake-only continuation tests without importing neural code."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/teaching_cycle_001"
CHILD = r'''
import sys, os, importlib.abc
banned = frozenset(('torch','numpy','sqlite3','_sqlite3','casformer','cas_cjt','cas_meta',
                    'boto3','botocore','tensorflow','jax'))
assert not banned.intersection(sys.modules)
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in banned:
            raise RuntimeError('FORBIDDEN_IMPORT:' + fullname)
sys.meta_path.insert(0, Guard())
def audit(event, args):
    if event.startswith('socket.') or event == 'sqlite3.connect':
        raise RuntimeError('FORBIDDEN_OPERATION:' + event)
sys.addaudithook(audit)
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
sys.path.insert(0, os.getcwd())
import pytest
result = pytest.main(sys.argv[1:])
assert not banned.intersection(sys.modules)
raise SystemExit(result)
'''


def require(condition, reason):
    if not condition:
        raise ValueError("CONTINUATION_CHECKS:" + reason)


def safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "UNSAFE_PATH")
    return path


def identify(path):
    path = safe(path)
    info = path.stat()
    require(path.is_file() and info.st_nlink == 1, "REGULAR_SINGLE_LINK_FILE_REQUIRED")
    digest, count = sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024**2):
            count += len(chunk)
            digest.update(chunk)
    require(count == info.st_size == path.stat().st_size, "FILE_CHANGED")
    return {"bytes": count, "sha256": digest.hexdigest()}


def write(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with safe(path).open("xb") as stream:
        stream.write(raw)
    return identify(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--test", action="append", required=True)
    args = parser.parse_args(argv)
    require(sys.flags.isolated and sys.dont_write_bytecode, "ISOLATED_NO_BYTECODE_REQUIRED")
    output = safe(args.output)
    require(output.is_relative_to(RECORDS) and not output.exists(), "FRESH_RECORD_DIRECTORY_REQUIRED")
    tests = sorted(set(args.test))
    require(len(tests) == len(args.test) and 0 < len(tests) <= 16, "TEST_LIST_INVALID")
    for name in tests:
        require(re.fullmatch(r"tests/test_teaching_(?:continuation_[a-z_]+|cycle_restore_probe)\.py", name),
                "SCOPED_NEW_TEST_REQUIRED")
        identify(ROOT / name)
    # Preserve all current local implementation/test bytes plus exact originals.
    names = {"tools/capture_teaching_continuation_checks.py", *tests}
    for directory, pattern in (("aws", "teaching_continuation_*.py"),
                               ("tools", "*teaching_continuation*.py")):
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT / directory).glob(pattern))
    names.update({"aws/teaching_cycle_restore_probe.py", "cas_meta2/teaching_cycle/continuation_package.py",
        "records/budget/campaign_ledger.json", "records/teaching_cycle_001/bundle_002/training.zip",
        "records/teaching_cycle_001/job_003/launch/result.json",
        "records/teaching_cycle_001/job_003/launch/partial_collected/complete.json",
        "records/teaching_cycle_001/job_003/launch/partial_collected/artifacts.zip",
        "records/teaching_cycle_001/job_003/continuation_inspection_001.json",
        "records/teaching_cycle_001/job_003/cleanup_recovery_001/result.json",
        "records/teaching_cycle_001/job_003/prior_package_001/prior_state.zip",
        "records/teaching_cycle_001/job_003/prior_package_001/manifest.json",
        "records/teaching_cycle_001/job_003/prior_package_001/receipt.json"})
    # Pure declaration read only. This module never imports torch or the worker.
    sys.path.insert(0, str(ROOT))
    from cas_meta2.teaching_cycle.worker_contract import WORKER_FILES
    names.update(WORKER_FILES)
    from aws.teaching_continuation_provider import source_dependencies
    names.update(source_dependencies())
    names.add("records/teaching_cycle_001/CONTINUATION_PROPOSAL.json")
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / "tests").glob("test_teaching*.py"))
    names.update(p.relative_to(ROOT).as_posix() for p in
                 (ROOT / "records/budget/campaign_ledger.json.history").iterdir() if p.is_file())
    before = {name: identify(ROOT / name) for name in sorted(names)}
    output.mkdir(parents=True)
    arguments = ['-q', '-p', 'no:cacheprovider', '--noconftest', '--override-ini', 'addopts=',
                 '--basetemp', str(output / 'pytest_tmp'), *tests]
    command = [sys.executable, '-I', '-B', '-c', CHILD, *arguments]
    write(output / "invocation.json", {"command": command, "cwd": str(ROOT), "timeout_seconds": 900,
        "observed_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "environment": {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}})
    write(output / "inputs_before.json", before)
    started, timed_out, code = time.monotonic(), False, None
    with (output / "stdout.txt").open("xb") as out, (output / "stderr.txt").open("xb") as err:
        try:
            code = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err, timeout=900,
                env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    elapsed = time.monotonic() - started
    after = {name: identify(ROOT / name) for name in sorted(names)}
    write(output / "inputs_after.json", after)
    raw = (output / "stdout.txt").read_text(encoding="utf-8", errors="replace")
    summaries = re.findall(r"[^\r\n]*(?:passed|failed|error)[^\r\n]* in [0-9.]+s[^\r\n]*", raw)
    result = {"schema": "cas-teaching-continuation-guarded-checks/1", "exit_code": code,
        "timed_out": timed_out, "wall_seconds": elapsed, "inputs_unchanged": before == after,
        "pytest_summary": summaries[-1] if summaries else None, "test_files": tests,
        "actual_gpu_restore": "UNEXECUTED", "provider_execution": "UNEXECUTED",
        "new_reservation": False, "boundary": "Pure and simulated tests only; not live restore, training or cloud readiness.",
        "artifacts": {name: identify(output / name) for name in
            ("invocation.json", "inputs_before.json", "inputs_after.json", "stdout.txt", "stderr.txt")}}
    receipt = write(output / "receipt.json", result)
    print(json.dumps({**result, "receipt": {"path": str(output / "receipt.json"), **receipt}}))
    return 0 if code == 0 and not timed_out and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
