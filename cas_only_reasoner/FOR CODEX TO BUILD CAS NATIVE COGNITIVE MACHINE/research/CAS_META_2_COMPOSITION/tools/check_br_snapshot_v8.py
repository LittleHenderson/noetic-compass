"""Capture synthetic SQLite-copy and pure scaffold checks; no native/model run."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "br_snapshot_pure_engine", ROOT / "tools/check_child_call_preparation_v8.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.RECORDS = ROOT / "records/child_call_v8_snapshot_001"
checks.TESTS = ("test_br_snapshot_v8.py", "test_child_scaffold_v8.py", "test_br_snapshot_capture_v8.py")
checks.SOURCES = ("cas_meta2/br_snapshot_v8.py", "cas_meta2/child_scaffold_v8.py",
    "tools/check_child_call_preparation_v8.py", "tools/check_br_snapshot_v8.py",
    "aws/launch_prefix_diagnostic_v8.py", "aws/prefix_remote_v8.py",
    "aws/prefix_diagnostic_launch_v8.py", *["tests/" + name for name in checks.TESTS])


def capture(output):
    output = Path(output).absolute()
    if (output.exists() or not output.resolve().is_relative_to(checks.RECORDS.resolve())
        or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
               for p in (output, *output.parents))):
        raise ValueError("BR_NEW_IN_SCOPE_CHECK_DIRECTORY_REQUIRED")
    before = checks.sources()
    budget = ROOT / "records/budget/campaign_ledger.json"
    request_path = ROOT / "records/child_call_v8_launch_connection_001/launch_request.json"
    budget_before, request_before = checks.digest(budget), checks.digest(request_path)
    request = json.loads(request_path.read_bytes())
    for name, expected in request["parent_file_sha256"].items():
        if checks.digest(ROOT / name) != expected:
            raise ValueError("BR_WORK_MUST_NOT_CHANGE_PREFIX_REQUEST_SOURCE:" + name)
    library = Path(importlib.util.find_spec("pytest").origin).resolve().parent.parent
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child",
               str(output / "pytest_tmp"), str(library)]
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    tick, timed_out, pid, start_error, code = time.monotonic(), False, None, None, None
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        try:
            process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
            pid = process.pid
            try:
                code = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                code = process.wait(timeout=15)
        except OSError as error:
            start_error = repr(error)
    postcheck_errors = {}
    def postcheck(name, read):
        try:
            return read()
        except Exception as error:
            postcheck_errors[name] = {"type": type(error).__name__, "error": str(error)}
            return None
    after = postcheck("frozen_sources", checks.sources)
    budget_after = postcheck("budget", lambda: checks.digest(budget))
    request_after = postcheck("prefix_request", lambda: checks.digest(request_path))
    receipt = {
        "schema": "cas-meta2-br-snapshot-pure-checks/8",
        "command": command, "cwd": str(ROOT), "pid": pid, "exit_code": code,
        "process_start_error": start_error, "timed_out": timed_out,
        "postcheck_errors": postcheck_errors,
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic() - tick, "python": sys.version,
        "source_before": before, "source_after": after, "source_unchanged": before == after,
        "budget_before_sha256": budget_before, "budget_after_sha256": budget_after,
        "budget_unchanged": budget_before == budget_after,
        "prefix_request_before_sha256": request_before, "prefix_request_after_sha256": request_after,
        "prefix_request_unchanged": request_before == request_after,
        "tests": list(checks.TESTS), "forbidden_imports": sorted(checks.FORBIDDEN),
        "outputs": {name: {"bytes": (output / name).stat().st_size,
                          "sha256": checks.digest(output / name)}
                    for name in ("stdout.txt", "stderr.txt")},
        "boundary": "Synthetic SQLite byte copies and pure scaffold only. No actual native database, native/model execution, provider access, reservation, paid launch, or measured B/R contrast."
    }
    with (output / "receipt.json").open("xb") as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    passed = (code == 0 and before == after and budget_before == budget_after
              and request_before == request_after and not timed_out and start_error is None
              and not postcheck_errors)
    print(json.dumps({"receipt": str(output / "receipt.json"),
        "sha256": checks.digest(output / "receipt.json"), "passed": passed, "exit_code": code}))
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        raise SystemExit(checks.child(sys.argv[2], sys.argv[3]))
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_br_snapshot_v8.py NEW_CAPTURE_DIRECTORY")
    raise SystemExit(capture(sys.argv[1]))
