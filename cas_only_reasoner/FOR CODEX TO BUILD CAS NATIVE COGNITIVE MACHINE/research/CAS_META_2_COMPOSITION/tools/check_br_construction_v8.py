"""Capture local pure B/R construction checks; no native/database/provider run.

Usage: python -B tools/check_br_construction_v8.py records/child_call_v8_construction_001/checks_001
The destination must be new. Missing mandatory tests stop before execution.
Optional parent/remote tests are named explicitly and their presence is recorded.
"""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/child_call_v8_construction_001"
MANDATORY_TESTS = (
    "test_br_construction_v8.py", "test_br_witness_v8.py", "test_br_package_v8.py",
    "test_br_snapshot_v8.py", "test_child_scaffold_v8.py", "test_br_snapshot_capture_v8.py",
)
OPTIONAL_TEST_SOURCES = {
    "test_br_remote_v8.py": "aws/br_remote_v8.py",
    "test_launch_br_construction_v8.py": "aws/launch_br_construction_v8.py",
}
FIXED_SOURCES = (
    "cas_meta2/br_construction_v8.py", "cas_meta2/br_witness_v8.py",
    "aws/br_package_v8.py", "cas_meta2/br_snapshot_v8.py", "cas_meta2/child_scaffold_v8.py",
    "aws/budget.py", "tools/check_child_call_preparation_v8.py",
    "tools/check_br_snapshot_v8.py", "tools/check_br_construction_v8.py",
)
BOUNDARY = (
    "Local pure tests with synthetic evidence and byte-only SQLite images. "
    "No actual native database, model/tensor execution, provider calls, reservation, "
    "paid launch, native B/R execution, numerical contrast or training result. "
    "Importing sqlite3 or a pure adapter helper is allowed; actual SQLite connections are blocked."
)
spec = importlib.util.spec_from_file_location(
    "br_construction_pure_engine", ROOT / "tools/check_child_call_preparation_v8.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.RECORDS = RECORDS


def select_tests():
    missing = [name for name in MANDATORY_TESTS if not (ROOT / "tests" / name).is_file()]
    if missing:
        raise ValueError("BR_CONSTRUCTION_MANDATORY_TEST_MISSING:" + ",".join(missing))
    present = [name for name in OPTIONAL_TEST_SOURCES if (ROOT / "tests" / name).is_file()]
    absent = [name for name in OPTIONAL_TEST_SOURCES if name not in present]
    checks.TESTS = (*MANDATORY_TESTS, *present)
    checks.SOURCES = (*FIXED_SOURCES, *(OPTIONAL_TEST_SOURCES[name] for name in present),
                      *("tests/" + name for name in checks.TESTS))
    return present, absent


def protected_files():
    # Preserve the accepted prefix request independently of this new construction.
    request_path = ROOT / "records/child_call_v8_launch_connection_001/launch_request.json"
    request = json.loads(request_path.read_bytes())
    values = {}
    for name, expected in request["parent_file_sha256"].items():
        actual = checks.digest(ROOT / name)
        if actual != expected:
            raise ValueError("BR_WORK_CHANGED_ACCEPTED_PREFIX_REQUEST_SOURCE:" + name)
        values[name] = actual
    for relative in (
        "records/child_call_v8_launch_connection_001/launch_request.json",
        "records/child_call_v8_diagnostic_001/source_001/receipt.json",
    ):
        values[relative] = checks.digest(ROOT / relative)
    return values


def child(temporary, test_library):
    select_tests()
    # Import guarding is supplied by the existing isolated pure-test engine.
    # Also block actual network/socket operations without forbidding unittest's
    # harmless imports of asyncio/socket. Synthetic mocks remain usable.
    def audit(event, arguments):
        if event == "sqlite3.connect":
            raise RuntimeError("BR_LOCAL_PURE_TEST_DATABASE_CONNECTION_REFUSED:" + event)
        if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.sendto", "socket.getaddrinfo"}:
            raise RuntimeError("BR_LOCAL_PURE_TEST_NETWORK_OPERATION_REFUSED:" + event)
    sys.addaudithook(audit)
    return checks.child(temporary, test_library)


def capture(output):
    output = Path(output).absolute()
    if (output.exists() or ".." in output.parts
            or output.resolve().parent != RECORDS.resolve()
            or re.fullmatch(r"checks_[0-9]{3,}", output.name) is None
            or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                   for p in (output, *output.parents))):
        raise ValueError("BR_NEW_EXCLUSIVE_CONSTRUCTION_CHECK_DIRECTORY_REQUIRED")
    present, absent = select_tests()
    selected_tests = tuple(checks.TESTS)
    before = checks.sources()
    protected_before = protected_files()
    budget_path = ROOT / "records/budget/campaign_ledger.json"
    budget_before = checks.digest(budget_path)
    pytest_spec = importlib.util.find_spec("pytest")
    if pytest_spec is None or pytest_spec.origin is None:
        raise ValueError("BR_PYTEST_LIBRARY_UNAVAILABLE")
    library = Path(pytest_spec.origin).resolve().parent.parent
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child",
               str(output / "pytest_tmp"), str(library)]
    child_environment = dict(os.environ)
    removed_launch_flags = []
    for name in tuple(child_environment):
        if name.startswith("CAS_META2_RUN_") or name == "CAS_META2_AWS_JOB_ID":
            removed_launch_flags.append(name)
            del child_environment[name]
    child_environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    child_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    tick, timed_out, pid, start_error, code = time.monotonic(), False, None, None, None
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        try:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr, env=child_environment)
            pid = process.pid
            try:
                code = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                code = process.wait(timeout=15)
        except OSError as error:
            start_error = {"type": type(error).__name__, "message": str(error)}
    postcheck_errors = {}
    def postcheck(name, read):
        try:
            return read()
        except Exception as error:
            postcheck_errors[name] = {"type": type(error).__name__, "message": str(error)}
            return None
    after = postcheck("sources", checks.sources)
    protected_after = postcheck("protected_files", protected_files)
    budget_after = postcheck("canonical_budget", lambda: checks.digest(budget_path))
    after_selection = postcheck("test_selection", select_tests)
    tests_unchanged = after_selection is not None and tuple(checks.TESTS) == selected_tests
    stdout_text = (output / "stdout.txt").read_text(encoding="utf-8", errors="replace")
    summary_lines = [line for line in stdout_text.splitlines()
                     if re.search(r"\b[0-9]+ (passed|failed|error|errors|skipped|deselected)\b", line)]
    passed = (code == 0 and before == after and protected_before == protected_after
              and budget_before == budget_after and tests_unchanged
              and not timed_out and start_error is None and not postcheck_errors)
    receipt = {
        "schema": "cas-meta2-br-construction-pure-checks/8",
        "status": "PURE_CHECKS_PASSED" if passed else "PURE_CHECKS_FAILED_OR_INCOMPLETE",
        "passed": passed, "command": command, "cwd": str(ROOT), "pid": pid, "exit_code": code,
        "process_start_error": start_error, "timed_out": timed_out, "timeout_seconds": 180,
        "postcheck_errors": postcheck_errors, "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.monotonic() - tick,
        "environment": {"python": sys.version, "python_executable": sys.executable,
                        "python_executable_sha256": checks.digest(sys.executable),
                        "platform": platform.platform(), "os_name": os.name,
                        "isolated_child": True, "bytecode_disabled": True,
                        "pytest_library": str(library), "plugin_autoload_disabled": True,
                        "removed_launch_environment_names": sorted(removed_launch_flags),
                        "environment_recording": "Allowlisted identity/settings only; credentials and complete environment omitted."},
        "source_before": before, "source_after": after, "source_unchanged": before == after,
        "protected_files_before": protected_before, "protected_files_after": protected_after,
        "protected_files_unchanged": protected_before == protected_after,
        "canonical_budget_path": str(budget_path),
        "budget_before_sha256": budget_before, "budget_after_sha256": budget_after,
        "budget_unchanged": budget_before == budget_after,
        "mandatory_tests": list(MANDATORY_TESTS), "optional_tests_present": present,
        "optional_tests_absent": absent, "tests": list(selected_tests), "test_selection_unchanged": tests_unchanged,
        "pytest_summary_lines": summary_lines, "forbidden_imports": sorted(checks.FORBIDDEN),
        "network_operations_blocked_in_test_process": True,
        "sqlite_connections_blocked_in_test_process": True,
        "sqlite_imports_allowed": True,
        "outputs": {name: {"bytes": (output / name).stat().st_size, "sha256": checks.digest(output / name)}
                    for name in ("stdout.txt", "stderr.txt")},
        "boundary": BOUNDARY,
    }
    with (output / "receipt.json").open("xb") as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    print(json.dumps({"receipt": str(output / "receipt.json"), "sha256": checks.digest(output / "receipt.json"),
                      "passed": passed, "exit_code": code}))
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        raise SystemExit(child(sys.argv[2], sys.argv[3]))
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_br_construction_v8.py NEW_CAPTURE_DIRECTORY")
    raise SystemExit(capture(sys.argv[1]))
