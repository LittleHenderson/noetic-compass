"""Capture the new unpaid preparation checks; refuse neural/provider imports."""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/child_call_v8_preparation_002"
TESTS = ("test_prefix_diagnostic_launch_v8.py", "test_child_scaffold_v8.py",
         "test_verify_prefix_clean_package_v8.py")
SOURCES = ("aws/prefix_diagnostic_launch_v8.py", "aws/budget.py", "cas_meta2/child_scaffold_v8.py",
           "tools/verify_prefix_clean_package_v8.py", "tools/check_child_call_preparation_v8.py",
           *["tests/" + name for name in TESTS])
FORBIDDEN = frozenset(("torch", "numpy", "casformer", "cas_cjt", "cas_meta", "tensorflow",
                       "jax", "cupy", "boto3", "botocore"))


class PureGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("V8_PREPARATION_NEURAL_PROVIDER_IMPORT_REFUSED:" + fullname)


def digest(path):
    with Path(path).open("rb") as stream:
        return __import__("hashlib").file_digest(stream, "sha256").hexdigest()


def sources():
    # This separate tool does not edit or extend the worker source archive.
    receipt = ROOT / "records/child_call_v8_diagnostic_001/source_001/receipt.json"
    frozen = json.loads(receipt.read_bytes())["files_sha256"]
    checked = {}
    for name, expected in frozen.items():
        if name == "launch_manifest.json":
            continue  # historical ZIP-only manifest, not a worktree source
        actual = digest(ROOT.parents[1] / name)
        if actual != expected:
            raise ValueError("V8_FROZEN_SOURCE_CHANGED:" + name)
        checked[name] = actual
    checked.update({"research/CAS_META_2_COMPOSITION/" + name: digest(ROOT / name) for name in SOURCES})
    return checked


def child(temporary, test_library):
    temporary = Path(temporary).absolute()
    if temporary.exists() or not temporary.resolve().is_relative_to(RECORDS.resolve()):
        raise ValueError("V8_NEW_IN_SCOPE_TEST_TEMP_REQUIRED")
    if FORBIDDEN.intersection(name.split(".")[0] for name in sys.modules):
        raise RuntimeError("V8_PREPARATION_IMPORT_BEFORE_GUARD")
    sys.meta_path.insert(0, PureGuard())
    sys.path.insert(0, str(ROOT))
    library = Path(test_library).absolute()
    if not (library / "pytest/__init__.py").is_file():
        raise ValueError("V8_EXPLICIT_PYTEST_LIBRARY_REQUIRED")
    sys.path.append(str(library))
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    import pytest
    code = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(temporary),
                        "--override-ini", "addopts=", *[str(ROOT / "tests" / name) for name in TESTS]])
    if FORBIDDEN.intersection(name.split(".")[0] for name in sys.modules):
        raise RuntimeError("V8_PREPARATION_IMPORT_BOUNDARY_CHANGED")
    return code


def capture(output):
    output = Path(output).absolute()
    if (output.exists() or not output.resolve().is_relative_to(RECORDS.resolve())
            or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                   for p in (output, *output.parents))):
        raise ValueError("V8_NEW_IN_SCOPE_CAPTURE_REQUIRED")
    before = sources()
    library = Path(importlib.util.find_spec("pytest").origin).resolve().parent.parent
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child",
               str(output / "pytest_tmp"), str(library)]
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            process.kill()
            code = process.wait(timeout=15)
    after = sources()
    receipt = {"schema": "cas-meta2-child-call-preparation-pure-checks/8",
               "command": command, "cwd": str(ROOT), "pid": process.pid, "exit_code": code,
               "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.monotonic() - tick, "python": sys.version,
               "source_before": before, "source_after": after, "source_unchanged": before == after,
               "tests": list(TESTS), "forbidden_imports": sorted(FORBIDDEN),
               "outputs": {name: {"bytes": (output / name).stat().st_size, "sha256": digest(output / name)}
                           for name in ("stdout.txt", "stderr.txt")},
               "boundary": "Pure source, plan, and scaffold checks. No model, tensor, native run, provider, paid launch, or reservation."}
    with (output / "receipt.json").open("xb") as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    print(json.dumps({"receipt": str(output / "receipt.json"), "sha256": digest(output / "receipt.json"),
                      "exit_code": code, "source_unchanged": before == after}))
    return code if code else (0 if before == after else 2)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        raise SystemExit(child(sys.argv[2], sys.argv[3]))
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_child_call_preparation_v8.py NEW_CAPTURE_DIRECTORY")
    raise SystemExit(capture(sys.argv[1]))
