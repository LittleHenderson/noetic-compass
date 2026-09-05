"""Bounded pure validation with preserved timeout output and exact source checks."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
from uuid import uuid4
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 600
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
BASELINE_MANIFEST_SHA256 = "476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0"
FORBIDDEN_IMPORTS = frozenset({"torch", "tensorflow", "jax", "cupy", "casformer", "cas_cjt",
                             "boto3", "botocore"})
# Installed botocore.exceptions imports only this pure exception-class closure.
# Session, client, endpoint, transport, credentials and all other SDK modules
# remain forbidden; the launcher tests supply their own mocked provider objects.
PURE_EXCEPTION_MODULES = frozenset({"botocore", "botocore.exceptions", "botocore.vendored",
    "botocore.vendored.requests", "botocore.vendored.requests.exceptions",
    "botocore.vendored.requests.packages", "botocore.vendored.requests.packages.urllib3",
    "botocore.vendored.requests.packages.urllib3.exceptions"})
SOURCE_SUFFIXES = frozenset({".py", ".json", ".toml", ".ini", ".txt"})


def forbidden_import(fullname):
    return fullname.split(".")[0] in FORBIDDEN_IMPORTS and fullname not in PURE_EXCEPTION_MODULES


class NoNeuralOrProviderImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if forbidden_import(fullname):
            raise RuntimeError("LOCAL_NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN:" + fullname)
        return None


def require(value, reason):
    if not value:
        raise ValueError(reason)


def utc():
    return datetime.now(timezone.utc).isoformat()


def no_links(path):
    for item in (path, *path.parents):
        require(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)(),
                "VALIDATION_PATH_LINK_REFUSED:" + str(item))


def file_hash(path):
    no_links(path)
    require(path.is_file(), "REGULAR_VALIDATION_INPUT_REQUIRED:" + str(path))
    state = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            state.update(block)
    return state.hexdigest()


def new_output(value):
    raw = Path(value).absolute()
    no_links(raw)
    output = raw.resolve()
    records = (ROOT / "records").resolve()
    require(output.is_relative_to(records) and output != records and not output.exists(),
            "NEW_CONTAINED_VALIDATION_DIRECTORY_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    return output


def source_snapshot():
    paths = []
    for name in ("cas_meta2", "aws", "tools", "tests"):
        base = ROOT / name
        no_links(base)
        require(base.is_dir(), "SOURCE_DIRECTORY_REQUIRED:" + name)
        for directory, directories, files in os.walk(base, followlinks=False):
            for child in directories:
                no_links(Path(directory) / child)
            for child in files:
                path = Path(directory) / child
                if path.suffix in SOURCE_SUFFIXES:
                    paths.append(path)
    paths.extend(path for path in ROOT.iterdir() if path.is_file() and
                 (path.suffix in {".json", ".toml", ".ini"} or path.name == "requirements-gpu.txt"))
    result = {}
    for path in sorted(set(paths)):
        no_links(path)
        relative = path.relative_to(ROOT).as_posix()
        result[relative] = file_hash(path)
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return result


def protected_snapshot():
    research = ROOT.parent
    manifest_path = research / "CAS_META_1_LEARNED_SELECTION/BASELINE_MANIFEST.json"
    manifest_hash = file_hash(manifest_path)
    require(manifest_hash == BASELINE_MANIFEST_SHA256, "ACCEPTED_PROTECTED_MANIFEST_DIGEST_MISMATCH")
    manifest = json.loads(manifest_path.read_bytes())
    require(manifest.get("baseline_sha") == BASELINE_SHA and len(manifest.get("files", [])) == 316,
            "PROTECTED_BASELINE_COVERAGE_MISMATCH")
    observed = {}
    for item in manifest["files"]:
        relative = item["path"]
        require(type(relative) is str and relative and "\\" not in relative and ":" not in relative
                and not relative.startswith("/") and all(part not in ("", ".", "..") for part in relative.split("/")),
                "PROTECTED_PATH_INVALID")
        path = research / relative
        no_links(path)
        require(path.resolve().is_relative_to(research.resolve()) and relative not in observed,
                "PROTECTED_PATH_ESCAPE_OR_DUPLICATE")
        observed[relative] = file_hash(path)
        require(observed[relative] == item["sha256"], "PROTECTED_BASELINE_CHANGED:" + relative)
    return {"baseline_sha": BASELINE_SHA, "manifest_sha256": manifest_hash,
            "files_verified": len(observed), "files_sha256": observed}


def save_json(path, value):
    payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def capture_bytes(value):
    if value is None:
        return b""
    require(type(value) in (bytes, str), "UNEXPECTED_SUBPROCESS_CAPTURE_TYPE")
    return value if isinstance(value, bytes) else value.encode("utf-8")


def run_child(command, env, *, runner=subprocess.run):
    started = utc()
    try:
        run = runner(command, cwd=ROOT, env=env, capture_output=True, timeout=TIMEOUT_SECONDS)
        return {"started_utc": started, "finished_utc": utc(), "returncode": run.returncode,
                "timed_out": False, "capture_available": {"stdout": run.stdout is not None,
                                                        "stderr": run.stderr is not None}}, capture_bytes(run.stdout), capture_bytes(run.stderr)
    except subprocess.TimeoutExpired as error:
        return {"started_utc": started, "finished_utc": utc(), "returncode": None,
                "timed_out": True, "timeout_seconds": TIMEOUT_SECONDS,
                "capture_available": {"stdout": error.stdout is not None, "stderr": error.stderr is not None},
                "failure": {"type": type(error).__name__, "message": str(error)},
                "termination_boundary": "subprocess.run kills and waits for its direct child on timeout; this is not a claim about independently detached grandchildren."}, capture_bytes(error.stdout), capture_bytes(error.stderr)


def junit_counts(path):
    if not path.exists():
        return None
    document = ET.parse(path).getroot()
    suites = [document] if document.tag == "testsuite" else list(document.findall("testsuite"))
    require(bool(suites), "JUNIT_TESTSUITES_REQUIRED")
    return {key: sum(int(suite.get(key, "0")) for suite in suites)
            for key in ("tests", "failures", "errors", "skipped")}


def child_main(output, scratch):
    require(scratch is not None, "EXPLICIT_SHORT_SCRATCH_REQUIRED")
    output, scratch = Path(output).absolute(), Path(scratch).absolute()
    for path in (output, scratch):
        no_links(path)
    require(output.is_dir() and output.resolve().is_relative_to((ROOT / "records").resolve())
            and output.resolve() != (ROOT / "records").resolve()
            and not (output / "tests.xml").exists() and not (output / "receipt.json").exists(),
            "NEW_CHILD_RECEIPT_TARGET_REQUIRED")
    homebases = [path for path in ROOT.parents if path.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"]
    require(bool(homebases) and scratch.parent.resolve() == (homebases[-1] / "_tmp").resolve()
            and re.fullmatch(r"meta2v3-[0-9a-f]{12}", scratch.name) and (scratch / "temp").is_dir(),
            "SHORT_HOMEBASE_SCRATCH_REQUIRED")
    require(os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1"
            and os.environ.get("CUDA_VISIBLE_DEVICES") == ""
            and os.environ.get("CAS_META2_RUN_GPU_TESTS") == "0"
            and os.environ.get("CAS_META1_RUN_GPU_TESTS") == "0", "PURE_CHILD_ENVIRONMENT_REQUIRED")
    require(not any(forbidden_import(name) for name in sys.modules),
            "PRELOADED_NEURAL_OR_PROVIDER_MODULE_REFUSED")
    sys.path.insert(0, str(ROOT))
    sys.meta_path.insert(0, NoNeuralOrProviderImports())
    import pytest
    return pytest.main(["tests", "-q", "-m", "not gpu", "-p", "no:cacheprovider",
                        "--basetemp=" + str(scratch / "pytest"), "--junitxml=" + str(output / "tests.xml")])


def validate(output):
    output = new_output(output)
    started = time.monotonic()
    receipt = {"schema": "cas-meta2-pure-validation/3", "started_utc": utc(),
        "status": "PURE_CHECKS_RUNNING", "completed": False, "timeout_seconds": TIMEOUT_SECONDS,
        "command": None, "cwd": str(ROOT), "launcher_command": [sys.executable, *sys.argv],
        "python": sys.version, "neural_imports_blocked": True, "provider_client_imports_blocked": True,
        "forbidden_imports": sorted(FORBIDDEN_IMPORTS), "plugin_autoload_disabled": True,
        "permitted_pure_exception_modules": sorted(PURE_EXCEPTION_MODULES),
        "local_neural_work": False, "gpu_tests_run": False, "provider_calls": 0,
        "scope": "Syntax, source bytes, pure data/control and mock-backend tests only; not GPU validation.",
        "errors": [], "source_sha256_before": None, "source_sha256_after": None,
        "protected_before": None, "protected_after": None, "child_started": False}
    stdout, stderr = b"", b""
    try:
        receipt["protected_before"] = protected_snapshot()
        receipt["source_sha256_before"] = source_snapshot()
        save_json(output / "source_snapshot_before.json", {
            "utc": utc(), "sources": receipt["source_sha256_before"], "protected": receipt["protected_before"]})
        print(json.dumps({"stage": "source_snapshot_taken", "utc": utc(),
                          "source_files": len(receipt["source_sha256_before"]),
                          "protected_files": 316, "output": str(output)}), flush=True)
        homebases = [path for path in ROOT.parents if path.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"]
        require(bool(homebases), "CNCM_HOMEBASE_REQUIRED")
        scratch = homebases[-1] / "_tmp" / ("meta2v3-" + uuid4().hex[:12])
        no_links(scratch)
        (scratch / "temp").mkdir(parents=True, exist_ok=False)
        receipt.update(test_scratch=str(scratch), scratch_retained=True)
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child",
                   "--output", str(output), "--scratch", str(scratch)]
        receipt["command"] = command
        overrides = {"PYTHONDONTWRITEBYTECODE": "1", "CAS_META2_RUN_GPU_TESTS": "0",
                     "CAS_META1_RUN_GPU_TESTS": "0", "CUDA_VISIBLE_DEVICES": "",
                     "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": "", "PYTEST_PLUGINS": "",
                     "TEMP": str(scratch / "temp"), "TMP": str(scratch / "temp"), "TMPDIR": str(scratch / "temp")}
        env = dict(os.environ, **overrides)
        receipt["environment_overrides"] = overrides
        receipt["child_started"] = True
        child, stdout, stderr = run_child(command, env)
        receipt["child"] = child
    except BaseException as error:
        receipt["errors"].append({"stage": "validation", "type": type(error).__name__,
                                  "message": str(error), "traceback": traceback.format_exc()})
    # Preserve exact captured bytes even when the child exceeded its deadline.
    for name, raw in (("stdout.txt", stdout), ("stderr.txt", stderr)):
        with (output / name).open("xb") as stream:
            stream.write(raw)
        receipt[name + "_sha256"] = sha256(raw).hexdigest()
        receipt[name + "_bytes"] = len(raw)
    for key, function in (("source_sha256_after", source_snapshot), ("protected_after", protected_snapshot)):
        try:
            receipt[key] = function()
        except BaseException as error:
            receipt["errors"].append({"stage": key, "type": type(error).__name__, "message": str(error)})
    receipt["sources_unchanged"] = (receipt["source_sha256_before"] is not None
                                    and receipt["source_sha256_before"] == receipt["source_sha256_after"])
    receipt["protected_unchanged"] = (receipt["protected_before"] is not None
                                      and receipt["protected_before"] == receipt["protected_after"])
    try:
        receipt["counts"] = junit_counts(output / "tests.xml")
    except BaseException as error:
        receipt["counts"] = None
        receipt["errors"].append({"stage": "junit", "type": type(error).__name__, "message": str(error)})
    text = stdout.decode("utf-8", errors="replace")
    functions = re.findall(r"(?<!subtests )(\d+) passed", text)
    subtests = re.findall(r"(\d+) subtests passed", text)
    receipt["passed_test_functions"] = int(functions[-1]) if functions else None
    receipt["passed_subtests"] = int(subtests[-1]) if subtests else None
    receipt["junit_count_includes_subtests"] = True
    child = receipt.get("child", {})
    success = (receipt["child_started"] and child.get("returncode") == 0 and not child.get("timed_out")
               and receipt["sources_unchanged"] and receipt["protected_unchanged"]
               and receipt["counts"] is not None and receipt["counts"]["errors"] == receipt["counts"]["failures"] == 0
               and not receipt["errors"])
    receipt.update(completed=bool(success), finished_utc=utc(), wall_seconds=time.monotonic() - started,
                   status="PURE_CHECKS_PASSED" if success else
                          ("PURE_CHECKS_TIMED_OUT" if child.get("timed_out") else "PURE_CHECKS_FAILED"))
    save_json(output / "receipt.json", receipt)
    print(json.dumps({key: receipt.get(key) for key in
                      ("status", "completed", "counts", "passed_test_functions", "passed_subtests",
                       "sources_unchanged", "protected_unchanged", "errors", "wall_seconds")}), flush=True)
    return 0 if success else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    return child_main(args.output, args.scratch) if args.child else validate(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
