"""Verify/extract the pinned B/R source ZIP and run its six pure test files.

No dependency installation, native/model execution, database connection, provider
access or reservation. Run only after review; all output goes to a new
records/child_call_v8_construction_001/br_clean/checks_* directory.
"""
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
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
RECORDS = ROOT / "records/child_call_v8_construction_001/br_clean"
PILOT = "research/CAS_META_2_COMPOSITION"
MANIFEST = "br_source_manifest.json"
TESTS = ("test_br_construction_v8.py", "test_br_witness_v8.py", "test_br_package_v8.py",
         "test_br_snapshot_v8.py", "test_child_scaffold_v8.py", "test_br_snapshot_capture_v8.py")
FORBIDDEN = frozenset(("torch", "numpy", "casformer", "cas_cjt", "cas_meta", "tensorflow",
                       "jax", "cupy", "boto3", "botocore"))
BOUNDARY = ("Clean extracted-source pure tests only. No neural/native execution, actual SQLite connection, "
            "provider call, reservation, paid launch, training or measured B/R result. "
            "Harmless sqlite3 and pure adapter imports are allowed.")


class CleanCheckRefused(ValueError):
    pass


def require(value, code):
    if not value:
        raise CleanCheckRefused(code)


def digest(path):
    with Path(path).open("rb") as stream:
        return __import__("hashlib").file_digest(stream, "sha256").hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value))


def unlinked(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "BR_CLEAN_LINK_OR_TRAVERSAL_REFUSED")
    return path


def new_output(output):
    output = unlinked(output)
    require(not output.exists() and output.resolve().parent == RECORDS.resolve()
            and re.fullmatch(r"checks_[0-9]{3,}", output.name) is not None,
            "BR_CLEAN_NEW_SCOPED_OUTPUT_REQUIRED")
    return output


def package_validator():
    # Parent-only loader. The fresh child never calls this function and does
    # not add ROOT to sys.path; it imports the extracted package validator.
    path = unlinked(ROOT / "aws/br_package_v8.py")
    spec = importlib.util.spec_from_file_location("br_clean_parent_package_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_checked(archive, output, *, archive_sha256, source_sha, manifest_sha256):
    """Inspect and close the ZIP/map identity before creating the output."""
    output = new_output(output)
    checker = package_validator()
    manifest = checker.inspect_archive(archive, expected_sha256=archive_sha256,
        expected_source_sha=source_sha, expected_manifest_sha256=manifest_sha256)
    inspector_path = ROOT / "aws/br_package_v8.py"
    require(digest(inspector_path) == manifest["files_sha256"][PILOT + "/aws/br_package_v8.py"],
            "BR_CLEAN_INSPECTOR_NOT_ARCHIVE_VERSION")
    raw = checker.read_file(archive)
    require(sha256(raw).hexdigest() == archive_sha256, "BR_CLEAN_ARCHIVE_CHANGED_BEFORE_EXTRACTION")
    members = checker.zip_members(raw)
    require(set(members) == set(manifest["files_sha256"]) | {MANIFEST},
            "BR_CLEAN_MEMBER_SET_CHANGED")
    expected = {**manifest["files_sha256"], MANIFEST: manifest_sha256}
    require(all(sha256(data).hexdigest() == expected[name] for name, data in members.items()),
            "BR_CLEAN_MEMBER_BYTES_CHANGED")
    for filename in TESTS:
        require(PILOT + "/tests/" + filename in members, "BR_CLEAN_SHIPPED_TEST_MISSING:" + filename)
    output.mkdir(parents=True, exist_ok=False)
    package = output / "package"
    package.mkdir()
    for name, data in sorted(members.items()):
        checker.safe_name(name)
        path = package.joinpath(*name.split("/"))
        require(path.resolve().is_relative_to(package.resolve()), "BR_CLEAN_EXTRACTION_ESCAPE")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    checked = checker.verify_extracted(package, manifest)
    require(digest(archive) == archive_sha256, "BR_CLEAN_ARCHIVE_CHANGED_AFTER_EXTRACTION")
    return {"package": str(package), "manifest": manifest, "member_sha256": expected,
            "member_bytes": {name: len(data) for name, data in members.items()},
            "extracted_check": checked, "inspector_sha256": digest(inspector_path)}


class ImportGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("BR_CLEAN_NEURAL_PROVIDER_IMPORT_REFUSED:" + fullname)


def module_paths(package, modules=None):
    """No cas_meta2/aws import may resolve outside this extracted pilot."""
    modules = sys.modules if modules is None else modules
    pilot = (Path(package) / PILOT).resolve()
    records = {}
    for name, module in sorted(modules.items()):
        if name.split(".")[0] not in {"cas_meta2", "aws"}:
            continue
        filename = getattr(module, "__file__", None)
        if filename is not None:
            path = unlinked(filename).resolve()
            require(path.is_relative_to(pilot) and path.is_file(), "BR_CLEAN_ORIGINAL_WORKTREE_IMPORT:" + name)
            records[name] = {"path": str(path), "sha256": digest(path)}
        else:
            paths = list(getattr(module, "__path__", ()))
            require(paths and all(unlinked(p).resolve().is_relative_to(pilot) for p in paths),
                    "BR_CLEAN_UNOWNED_NAMESPACE_IMPORT:" + name)
            records[name] = {"namespace_paths": [str(Path(p).resolve()) for p in paths]}
    return records


def child(package, temporary, test_library, receipt_path, manifest_sha256):
    package, temporary, receipt_path = map(unlinked, (package, temporary, receipt_path))
    require(not temporary.exists() and not receipt_path.exists()
            and temporary.parent == package.parent and receipt_path.parent == package.parent,
            "BR_CLEAN_CHILD_OUTPUT_CUSTODY")
    require(not FORBIDDEN.intersection(name.split(".")[0] for name in sys.modules),
            "BR_CLEAN_FORBIDDEN_IMPORT_BEFORE_GUARD")
    sys.meta_path.insert(0, ImportGuard())
    def audit(event, arguments):
        if event == "sqlite3.connect":
            raise RuntimeError("BR_CLEAN_DATABASE_CONNECTION_REFUSED")
        if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.sendto", "socket.getaddrinfo"}:
            raise RuntimeError("BR_CLEAN_NETWORK_OPERATION_REFUSED:" + event)
    sys.addaudithook(audit)
    pilot = package / PILOT
    # No sibling source directories, original ROOT, cwd, or PYTHONPATH added.
    sys.path.insert(0, str(pilot))
    library = unlinked(test_library)
    require((library / "pytest/__init__.py").is_file(), "BR_CLEAN_EXPLICIT_PYTEST_LIBRARY_REQUIRED")
    sys.path.append(str(library))
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = {"schema": "cas-meta2-br-clean-child/8", "passed": False, "tests": list(TESTS),
              "package": str(package), "pilot": str(pilot), "boundary": BOUNDARY}
    code = None
    try:
        require(digest(package / MANIFEST) == manifest_sha256, "BR_CLEAN_CHILD_MANIFEST_CHANGED")
        from aws import br_package_v8 as checker
        manifest = checker.decode((package / MANIFEST).read_bytes())
        result["before_check"] = checker.verify_extracted(package, manifest)
        import pytest
        code = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(temporary),
                            "-c", str(pilot / "pyproject.toml"), "--rootdir", str(pilot), "--confcutdir", str(pilot),
                            "--override-ini", "addopts=", *[str(pilot / "tests" / name) for name in TESTS]])
        result["imported_modules"] = module_paths(package)
        require(not FORBIDDEN.intersection(name.split(".")[0] for name in sys.modules),
                "BR_CLEAN_FORBIDDEN_IMPORT_AFTER_TESTS")
        result["after_check"] = checker.verify_extracted(package, manifest,
            imported_paths=[record["path"] for record in result["imported_modules"].values() if "path" in record])
        require(result["before_check"] == result["after_check"], "BR_CLEAN_EXTRACTED_SOURCE_CHANGED")
        result["passed"] = code == 0
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        result["pytest_exit_code"] = code
        result["python"] = sys.version
        result["sys_path"] = list(sys.path)
        write_new(receipt_path, result)
    return 0 if result["passed"] else 1


def capture(archive, output, *, archive_sha256, source_sha, manifest_sha256):
    started, tick = datetime.now(timezone.utc).isoformat(), time.monotonic()
    output = new_output(output)
    self_before = digest(__file__)
    result = {"schema": "cas-meta2-br-clean-package-check/8", "passed": False, "status": "INCOMPLETE",
              "source_sha": source_sha, "archive": str(Path(archive).absolute()),
              "archive_sha256": archive_sha256, "manifest_sha256": manifest_sha256,
              "started_utc": started, "boundary": BOUNDARY, "tests": list(TESTS),
              "tool_sha256_before": self_before}
    process, code, timed_out = None, None, False
    try:
        extracted = extract_checked(archive, output, archive_sha256=archive_sha256,
                                    source_sha=source_sha, manifest_sha256=manifest_sha256)
        result.update(extracted)
        library_spec = importlib.util.find_spec("pytest")
        require(library_spec is not None and library_spec.origin is not None, "BR_CLEAN_PYTEST_UNAVAILABLE")
        library = Path(library_spec.origin).resolve().parent.parent
        command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child",
                   extracted["package"], str(output / "pytest_tmp"), str(library),
                   str(output / "child_receipt.json"), manifest_sha256]
        result["command"] = command
        # Windows CreateProcess rejects very long cwd values. A short interpreter
        # directory is inert; -I and the explicit extracted sys.path entry keep
        # both original-worktree and cwd imports out of the child.
        child_cwd = Path(sys.executable).resolve().parent
        result["child_cwd"] = str(child_cwd)
        environment = dict(os.environ)
        for name in tuple(environment):
            if name.startswith("CAS_META2_RUN_") or name in {"CAS_META2_AWS_JOB_ID", "PYTHONPATH"}:
                del environment[name]
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(command, cwd=child_cwd,
                                       env=environment, stdout=stdout, stderr=stderr)
            try:
                code = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                code = process.wait(timeout=15)
        result["child_receipt"] = json.loads((output / "child_receipt.json").read_bytes())
        result["archive_sha256_after"] = digest(archive)
        checker = package_validator()
        result["postcheck"] = checker.verify_extracted(extracted["package"], extracted["manifest"])
        result["tool_sha256_after"] = digest(__file__)
        require(result["archive_sha256_after"] == archive_sha256 and result["tool_sha256_after"] == self_before,
                "BR_CLEAN_SOURCE_OR_TOOL_CHANGED")
        require(digest(ROOT / "aws/br_package_v8.py") == extracted["inspector_sha256"],
                "BR_CLEAN_INSPECTOR_CHANGED")
        result["passed"] = code == 0 and not timed_out and result["child_receipt"]["passed"] is True
        result["status"] = "CLEAN_PURE_TESTS_PASSED" if result["passed"] else "CLEAN_PURE_TESTS_FAILED"
    except BaseException as error:
        result["status"] = "CLEAN_CHECK_REFUSED_OR_FAILED"
        result["failure"] = {"type": type(error).__name__, "message": str(error)}
        # Invalid archives fail before extraction. Retain only a small failure
        # receipt in the already validated, new output path.
        if not output.exists():
            output.mkdir(parents=True, exist_ok=False)
    finally:
        result.update(exit_code=code, timed_out=timed_out, pid=None if process is None else process.pid,
                      finished_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic() - tick,
                      environment={"python": sys.version, "executable": sys.executable,
                                   "platform": platform.platform(), "isolated_child": True,
                                   "bytecode_disabled": True, "pytest_plugin_autoload_disabled": True},
                      forbidden_imports=sorted(FORBIDDEN), network_operations_blocked=True,
                      sqlite_connections_blocked=True, native_execution=False, provider_access=False)
        result["outputs"] = {name: {"sha256": digest(output / name), "bytes": (output / name).stat().st_size}
                            for name in ("stdout.txt", "stderr.txt", "child_receipt.json") if (output / name).is_file()}
        write_new(output / "receipt.json", result)
    print(json.dumps({"receipt": str(output / "receipt.json"), "sha256": digest(output / "receipt.json"),
                      "passed": result["passed"], "status": result["status"]}))
    return 0 if result["passed"] else 1


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    return capture(args.archive, args.output, archive_sha256=args.archive_sha256,
                   source_sha=args.source_sha, manifest_sha256=args.manifest_sha256)


if __name__ == "__main__":
    if len(sys.argv) == 7 and sys.argv[1] == "--child":
        raise SystemExit(child(*sys.argv[2:]))
    raise SystemExit(main())
