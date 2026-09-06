"""Receipt pure dedicated-launch tests; no real reservation or provider creation."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prefix_preparation_test_engine",
    ROOT / "tools/check_child_call_preparation_v8.py")
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)
checks.RECORDS = ROOT / "records/child_call_v8_launch_connection_001"
checks.TESTS = ("test_launch_prefix_diagnostic_v8.py", "test_prefix_remote_v8.py", "test_prefix_remote_v8_review.py")
checks.SOURCES = ("aws/launch_prefix_diagnostic_v8.py", "aws/prefix_remote_v8.py",
                  "aws/prefix_diagnostic_launch_v8.py", "tools/check_child_call_preparation_v8.py",
                  "tools/check_prefix_launch_connection_v8.py", *["tests/" + name for name in checks.TESTS])


def capture(output):
    output = Path(output).absolute()
    if output.exists() or not output.resolve().is_relative_to(checks.RECORDS.resolve()) or any(
            p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (output, *output.parents)):
        raise ValueError("PREFIX_NEW_IN_SCOPE_CHECK_DIRECTORY_REQUIRED")
    before = checks.sources()
    library = Path(importlib.util.find_spec("pytest").origin).resolve().parent.parent
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child",
               str(output / "pytest_tmp"), str(library)]
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    timed_out = False
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=15)
    after = checks.sources()
    receipt = {"schema": "cas-meta2-prefix-launch-connection-pure-checks/8", "command": command,
               "cwd": str(ROOT), "pid": process.pid, "exit_code": code, "timed_out": timed_out,
               "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.monotonic() - tick, "python": sys.version,
               "source_before": before, "source_after": after, "source_unchanged": before == after,
               "tests": list(checks.TESTS), "forbidden_imports": sorted(checks.FORBIDDEN),
               "outputs": {name: {"bytes": (output / name).stat().st_size, "sha256": checks.digest(output / name)}
                           for name in ("stdout.txt", "stderr.txt")},
               "boundary": "Pure contracts with fake providers/processes where stated. No AWS mutation, reservation, neural or native execution. Not a cloud shutdown test."}
    with (output / "receipt.json").open("xb") as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    print(json.dumps({"receipt": str(output / "receipt.json"), "sha256": checks.digest(output / "receipt.json"),
                      "exit_code": code, "source_unchanged": before == after, "timed_out": timed_out}))
    return 0 if code == 0 and before == after and not timed_out else 1


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        raise SystemExit(checks.child(sys.argv[2], sys.argv[3]))
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_prefix_launch_connection_v8.py NEW_CAPTURE_DIRECTORY")
    raise SystemExit(capture(sys.argv[1]))
