"""Capture only named slice-two tests under the frozen no-neural/no-network guard."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TESTS = frozenset({
    "tests/test_teaching_continuation_plan_v2.py",
    "tests/test_teaching_continuation_preflight_v2.py",
    "tests/test_teaching_continuation_tools_v2.py",
    "tests/test_teaching_continuation_evaluation_v2.py",
    "tests/test_teaching_continuation_package_v2.py",
    "tests/test_teaching_continuation_inspection_v2.py",
    "tests/test_teaching_continuation_second_fixtures.py",
    "tests/test_teaching_continuation_second_restore_probe.py",
    "tests/test_teaching_continuation_second_remote.py",
    "tests/test_teaching_continuation_second_provider.py",
    "tests/test_teaching_continuation_second_launch.py",
})
TIMEOUT_SECONDS = 600


def helper_module():
    path = ROOT / "tools/capture_teaching_continuation_checks.py"
    spec = importlib.util.spec_from_file_location("_slice_two_guarded_capture", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def source_names():
    """Both old frozen and all new transport sources, tests and retained inputs."""
    sys.path.insert(0, str(ROOT))
    from aws.teaching_continuation_provider import source_dependencies as original_sources
    from aws.teaching_continuation_provider_v2 import source_dependencies as new_sources
    from cas_meta2.teaching_cycle.worker_contract import WORKER_FILES
    names = set(original_sources()) | set(new_sources()) | set(WORKER_FILES) | set(TESTS)
    names.update({
        "tools/capture_teaching_continuation_checks.py",
        "tools/capture_teaching_continuation_v2_checks.py",
        "tools/inspect_teaching_continuation_v2.py",
        "tools/evaluate_teaching_continuation_v2.py",
        "cas_meta2/teaching_cycle/continuation_package_v2.py",
        "aws/teaching_cycle_restore_probe_v2.py",
        "records/teaching_cycle_001/CONTINUATION_002_PROPOSAL.json",
        "records/budget/campaign_ledger.json",
        "records/teaching_cycle_001/bundle_002/training.zip",
        "records/teaching_cycle_001/material_001/preparation_receipt.json",
        "records/teaching_cycle_001/continuation_001/launch/result.json",
        "records/teaching_cycle_001/continuation_001/launch/partial_collected/complete.json",
        "records/teaching_cycle_001/continuation_001/launch/partial_collected/artifacts.zip",
    })
    # Some fixtures reuse older fake packets. Bind their actual code too.
    names.update(path.relative_to(ROOT).as_posix() for path in (ROOT / "tests").glob("test_teaching*.py"))
    for name in (
        "records/teaching_cycle_001/continuation_001/continuation_inspection_002.json",
        "records/teaching_cycle_001/continuation_001/cleanup_recovery_002/result.json",
        "records/teaching_cycle_001/continuation_001/prior_package_002/receipt.json",
        "records/teaching_cycle_001/continuation_001/prior_package_002/manifest.json",
        "records/teaching_cycle_001/continuation_001/prior_package_002/prior_state.zip",
    ):
        if (ROOT / name).exists():
            names.add(name)
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--test", action="append", required=True)
    args = parser.parse_args(argv)
    helper = helper_module()
    helper.require(sys.flags.isolated and sys.dont_write_bytecode, "ISOLATED_NO_BYTECODE_REQUIRED")
    tests = sorted(set(args.test))
    helper.require(bool(tests) and len(tests) == len(args.test) and set(tests) <= TESTS,
                   "EXPLICIT_SLICE_TWO_TESTS_ONLY")
    output = helper.safe(args.output)
    helper.require(output.is_relative_to(helper.RECORDS) and not output.exists(), "FRESH_RECORD_DIRECTORY_REQUIRED")
    names = source_names()
    before = {name: helper.identify(ROOT / name) for name in sorted(names)}
    output.mkdir(parents=True)
    arguments = ["-q", "-p", "no:cacheprovider", "--noconftest", "--override-ini", "addopts=",
                 "--basetemp", str(output / "pytest_tmp"), *tests]
    command = [sys.executable, "-I", "-B", "-c", helper.CHILD, *arguments]
    helper.write(output / "invocation.json", {
        "command": command, "cwd": str(ROOT), "timeout_seconds": TIMEOUT_SECONDS,
        "observed_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
        "environment": {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"},
    })
    helper.write(output / "inputs_before.json", before)
    started, timed_out, code = time.monotonic(), False, None
    with (output / "stdout.txt").open("xb") as out, (output / "stderr.txt").open("xb") as err:
        try:
            code = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err, timeout=TIMEOUT_SECONDS,
                env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
    elapsed = time.monotonic() - started
    after = {name: helper.identify(ROOT / name) for name in sorted(names)}
    helper.write(output / "inputs_after.json", after)
    text = (output / "stdout.txt").read_text(encoding="utf-8", errors="replace")
    summaries = re.findall(r"[^\r\n]*(?:passed|failed|error)[^\r\n]* in [0-9.]+s[^\r\n]*", text)
    result = {"schema": "cas-teaching-continuation-v2-guarded-checks/1", "exit_code": code,
        "timed_out": timed_out, "wall_seconds": elapsed, "inputs_unchanged": before == after,
        "pytest_summary": summaries[-1] if summaries else None, "test_files": tests,
        "actual_gpu_restore": "UNEXECUTED", "provider_execution": "UNEXECUTED", "new_reservation": False,
        "boundary": "Pure and fake tests only; no actual training, cloud execution, or learning result.",
        "artifacts": {name: helper.identify(output / name) for name in
            ("invocation.json", "inputs_before.json", "inputs_after.json", "stdout.txt", "stderr.txt")}}
    receipt = helper.write(output / "receipt.json", result)
    print(json.dumps({**result, "receipt": {"path": str(output / "receipt.json"), **receipt}}))
    return 0 if code == 0 and not timed_out and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
