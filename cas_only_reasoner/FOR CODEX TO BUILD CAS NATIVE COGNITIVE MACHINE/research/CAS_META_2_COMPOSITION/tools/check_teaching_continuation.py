"""Capture fake-only transport and continuation checks; never restore a model.

Run with Python -I -B and a fresh directory below records/teaching_cycle_001.
This wrapper does not reserve money, contact AWS, or touch an existing process.
"""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/teaching_cycle_001"
_spec = importlib.util.spec_from_file_location(
    "_teaching_transport_capture", ROOT / "tools/check_teaching_launch.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
TEST_FILES = [name for name in base.FILES if name.startswith("tests/")]
TEST_FILES += ["tests/test_teaching_cycle_continuation_inspection.py"]
# Fixture modules are hashed, but are not independently collected as tests.
EXTRA_FILES = [
    "tools/check_teaching_continuation.py",
    "tools/inspect_teaching_continuation.py",
    "tests/test_teaching_cycle_continuation_inspection.py",
    "tests/test_teaching_cycle_runner.py",
    "tests/test_teaching_cycle_evaluation.py",
    "aws/__init__.py", "aws/condition_skill_v9_package.py",
    "cas_meta2/__init__.py", "cas_meta2/codec.py", "cas_meta2/features_v2.py",
    "cas_meta2/teaching_cycle/__init__.py",
    "cas_meta2/teaching_cycle/lesson_contract.py",
    "cas_meta2/teaching_cycle/guided_application.py",
    "cas_meta2/teaching_cycle/data.py",
    "records/teaching_cycle_001/bundle_002/training.zip",
    "records/teaching_cycle_001/bundle_002/manifest.json",
    "records/teaching_cycle_001/bundle_002/receipt.json",
    "records/teaching_cycle_001/LAUNCH_PROPOSAL.json",
    "records/teaching_cycle_001/material_001/preparation_receipt.json",
    "records/teaching_cycle_001/material_001/teaching/train.json",
    "records/teaching_cycle_001/material_001/teaching/development.json",
    "records/teaching_cycle_001/material_001/evaluation_public/test_fresh.json",
    "records/teaching_cycle_001/material_001/evaluation_public/test_context.json",
    "records/teaching_cycle_001/material_001/evaluation_public/test_names.json",
]


def digest(path):
    value = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def hashes():
    names = set(base.FILES + EXTRA_FILES)
    history = ROOT / "records/budget/campaign_ledger.json.history"
    if not history.is_dir():
        raise RuntimeError("CANONICAL_LEDGER_HISTORY_MISSING")
    names.update(path.relative_to(ROOT).as_posix() for path in history.glob("*.json"))
    return {name: digest(ROOT / name) for name in sorted(names)}


def environment():
    return {"python": sys.version, "executable": sys.executable,
            "platform": platform.platform(), "os_name": os.name,
            "isolated": sys.flags.isolated,
            "dont_write_bytecode": sys.dont_write_bytecode,
            "cwd": str(Path.cwd()),
            "pytest_disable_plugin_autoload": os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")}


def write_json(path, document):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(document, stream, sort_keys=True, indent=2)
        stream.write("\n")


def child(directory, library):
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    write_json(Path(directory) / "child_environment.json", environment())
    # Reuse the frozen import/network guard without changing its source file.
    # Only selected test files go here, not the wider hash inventory.
    base.FILES = list(TEST_FILES)
    return base.child(directory, library)


def main(destination):
    candidate = Path(destination).absolute()
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
           for p in (candidate, *candidate.parents)):
        raise RuntimeError("OUTPUT_LINK_NOT_ALLOWED")
    output = candidate.resolve()
    if output == RECORDS or not output.is_relative_to(RECORDS) or output.exists():
        raise RuntimeError("FRESH_TEACHING_RECORDS_DIRECTORY_REQUIRED")
    before = hashes()
    pytest_spec = importlib.util.find_spec("pytest")
    if pytest_spec is None:
        raise RuntimeError("PYTEST_NOT_AVAILABLE")
    library = str(Path(pytest_spec.origin).parent.parent)
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()),
               "--child", str(output), library]
    output.mkdir(parents=True)
    write_json(output / "command.json", {"command": command, "tests": TEST_FILES})
    write_json(output / "environment.json", environment())
    write_json(output / "before.json", before)
    started, timer = datetime.now(timezone.utc).isoformat(), time.monotonic()
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=Path(sys.executable).parent,
            stdout=stdout, stderr=stderr, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        timed_out = False
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()  # Only the child created above, never another session.
            code = process.wait(timeout=15)
    after_error = None
    try:
        after = hashes()
    except (OSError, RuntimeError) as exc:
        after, after_error = None, str(exc)
    write_json(output / "after.json", after)
    receipt = {
        "schema": "cas-teaching-continuation-pure-check/1", "command": command,
        "tests": TEST_FILES, "pytest_library": library,
        "cwd": str(Path(sys.executable).parent), "child_pid": process.pid,
        "exit_code": code, "timed_out": timed_out, "timeout_seconds": 300,
        "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic() - timer,
        "before": before, "after": after, "after_hash_error": after_error,
        "unchanged": before == after,
        "boundary": "Fake-only checks. No AWS/network/neural/NumPy/SQLite execution. "
                    "Synthetic checkpoints do not prove GPU restoration. Actual private final targets are not read or hashed.",
        "outputs": {path.name: {"bytes": path.stat().st_size, "sha256": digest(path)}
                    for path in output.iterdir() if path.is_file()},
    }
    write_json(output / "receipt.json", receipt)
    print(json.dumps({"exit_code": code, "unchanged": receipt["unchanged"],
                      "receipt": str(output / "receipt.json")}))
    return code if code else (0 if receipt["unchanged"] and not timed_out else 2)


if __name__ == "__main__":
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise SystemExit("Use Python -I -B for this pure evidence capture.")
    raise SystemExit(child(sys.argv[2], sys.argv[3]) if sys.argv[1] == "--child" else main(sys.argv[1]))
