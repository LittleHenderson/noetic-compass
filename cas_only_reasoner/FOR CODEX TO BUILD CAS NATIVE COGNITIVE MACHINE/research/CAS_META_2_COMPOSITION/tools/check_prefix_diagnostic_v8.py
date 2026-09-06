"""Capture focused pure checks in an isolated process; never load a model."""
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
TESTS = (
    "test_diagnostic_v8_bundle.py", "test_diagnostic_v8_sites.py",
    "test_diagnostic_v8_gpu_contract.py", "test_grammar_v3.py",
    "test_codec.py", "test_features_v2.py", "test_features_v3.py",
    "test_selection_v3.py",
)
FORBIDDEN = frozenset(("torch", "casformer", "cas_cjt", "cas_meta", "tensorflow",
                       "jax", "cupy", "boto3", "botocore"))


def sources():
    paths = list((ROOT / "cas_meta2/diagnostic_v8").glob("*.py"))
    paths += [ROOT / "tests" / name for name in TESTS]
    paths += [Path(__file__).resolve()]
    return {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


class PureGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("V8_PURE_CHECK_NEURAL_PROVIDER_IMPORT_REFUSED:" + fullname)


def child(temporary, test_library):
    temporary = Path(temporary).absolute()
    if temporary.exists() or not temporary.resolve().is_relative_to(
            (ROOT / "records/child_call_v8_diagnostic_001").resolve()):
        raise ValueError("V8_NEW_IN_SCOPE_TEST_TEMP_REQUIRED")
    if any(name in sys.modules for name in FORBIDDEN):
        raise RuntimeError("V8_PURE_CHECK_ALREADY_IMPORTED_NEURAL_PROVIDER")
    sys.meta_path.insert(0, PureGuard())
    sys.path.insert(0, str(ROOT))
    # -I intentionally omits user-site startup hooks. Make the explicitly
    # recorded pytest library available without executing its .pth files.
    test_library = Path(test_library).absolute()
    if not (test_library / "pytest/__init__.py").is_file():
        raise ValueError("V8_EXPLICIT_PYTEST_LIBRARY_MISSING")
    sys.path.append(str(test_library))
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    import pytest
    code = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(temporary),
                        "--override-ini", "addopts=",
                        *[str(ROOT / "tests" / name) for name in TESTS]])
    if any(name in sys.modules for name in FORBIDDEN):
        raise RuntimeError("V8_PURE_CHECK_IMPORT_BOUNDARY_CHANGED")
    return code


def capture(output):
    output = Path(output).absolute()
    records = ROOT / "records/child_call_v8_diagnostic_001"
    if (output.exists() or not output.resolve().is_relative_to(records.resolve())
            or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                   for p in (output, *output.parents))):
        raise ValueError("V8_NEW_IN_SCOPE_CAPTURE_DIRECTORY_REQUIRED")
    before = sources()
    test_spec = importlib.util.find_spec("pytest")
    if test_spec is None or test_spec.origin is None:
        raise ValueError("V8_PYTEST_INSTALL_REQUIRED_FOR_PURE_CHECKS")
    test_library = Path(test_spec.origin).resolve().parent.parent
    command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child",
               str(output / "pytest_tmp"), str(test_library)]
    started = datetime.now(timezone.utc).isoformat()
    tick = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        code = process.wait()
    after = sources()
    receipt = {"schema": "cas-meta2-prefix-pure-checks/8", "command": command,
               "cwd": str(ROOT), "pid": process.pid, "exit_code": code,
               "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.monotonic() - tick, "source_before": before,
               "source_after": after, "source_unchanged": before == after,
               "python": sys.version, "tests": list(TESTS),
               "boundary": "Pure tests only. No checkpoint, tensor, model, native execution or provider.",
               "outputs": {name: {"bytes": (output/name).stat().st_size,
                                    "sha256": sha256((output/name).read_bytes()).hexdigest()}
                           for name in ("stdout.txt", "stderr.txt")}}
    raw = (json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with (output / "execution_receipt.json").open("xb") as stream:
        stream.write(raw)
    print(json.dumps({"receipt": str(output / "execution_receipt.json"),
                      "sha256": sha256(raw).hexdigest(), "exit_code": code,
                      "source_unchanged": before == after}))
    return code if code else (0 if before == after else 2)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        raise SystemExit(child(sys.argv[2], sys.argv[3]))
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_prefix_diagnostic_v8.py NEW_CAPTURE_DIRECTORY")
    raise SystemExit(capture(sys.argv[1]))
