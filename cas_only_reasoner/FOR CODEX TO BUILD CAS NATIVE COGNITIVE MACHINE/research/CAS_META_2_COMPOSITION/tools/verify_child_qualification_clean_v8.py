"""Run the five pure child-qualification test files from an exact source ZIP.

No dependency install, native/model/database execution, provider call or budget
operation. The only repository code imported is the extracted, pinned code.
"""
from datetime import datetime, timezone
from hashlib import sha256, file_digest
import importlib.abc
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import time
from types import ModuleType
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/child_qualification_v8_001/clean"
PILOT = "research/CAS_META_2_COMPOSITION"
MANIFEST = "child_qualification_source_manifest.json"
INSPECTOR = "aws/child_qualification_package_v8.py"
EXPECTED_MEMBERS = 639
TESTS = ("test_child_curriculum_v8.py", "test_child_qualification_v8.py",
         "test_child_qualification_gpu_v8.py", "test_child_qualification_package_v8.py",
         "test_child_scaffold_v8.py")
FORBIDDEN = frozenset(("torch", "numpy", "casformer", "cas_cjt", "cas_meta", "tensorflow",
                      "jax", "cupy", "boto3", "botocore"))
BOUNDARY = ("Pure tests from a fresh extracted archive only. No neural/native execution, SQLite connection, "
            "provider access, reservation, training or actual task qualification. Synthetic operations remain synthetic.")


class CleanCheckRefused(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise CleanCheckRefused(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "CHQ_CLEAN_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: require(False, "CHQ_CLEAN_NONFINITE_JSON"))
    canonical(value)
    return value


def unlinked(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
            for p in (path, *path.parents)), "CHQ_CLEAN_LINK_OR_TRAVERSAL")
    return path


def read_file(path, maximum):
    path = unlinked(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum, "CHQ_CLEAN_BOUNDED_REGULAR_FILE")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "CHQ_CLEAN_FILE_SIZE_LIMIT")
    return raw


def digest(path):
    path = unlinked(path)
    require(path.stat().st_nlink == 1 and path.is_file(), "CHQ_CLEAN_REGULAR_SINGLE_LINK")
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def write_new(path, value):
    with unlinked(path).open("xb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def new_output(output):
    output = unlinked(output)
    require(not output.exists() and output.resolve().parent == RECORDS.resolve()
            and re.fullmatch(r"checks_[0-9]{3,}", output.name), "CHQ_CLEAN_NEW_SCOPED_OUTPUT")
    return output


def safe_names(infos):
    names = [i.orig_filename for i in infos]
    for name in names:
        require(type(name) is str and name and ":" not in name and "\\" not in name
                and not any(ord(c) < 32 for c in name)
                and all(part not in ("", ".", "..") and not part.endswith((" ", ".")) for part in name.split("/")),
                "CHQ_CLEAN_UNSAFE_ZIP_NAME")
    folded = {n.casefold() for n in names}
    require(len(names) == len(set(names)) == len(folded)
            and not any("/".join(n.split("/")[:i]).casefold() in folded
                        for n in names for i in range(1, len(n.split("/")))), "CHQ_CLEAN_MEMBER_COLLISION")
    require(all(i.orig_filename == i.filename and not i.is_dir() and not i.flag_bits & 1
                and stat.S_IFMT(i.external_attr >> 16) in (0, stat.S_IFREG) for i in infos),
            "CHQ_CLEAN_ZIP_LINK_SPECIAL_OR_ENCRYPTED")
    return names


def inspect_bytes(raw, *, archive_sha256, source_sha, manifest_sha256):
    require(type(source_sha) is str and re.fullmatch("[a-f0-9]{40}", source_sha)
            and all(type(h) is str and re.fullmatch("[a-f0-9]{64}", h) for h in (archive_sha256, manifest_sha256)),
            "CHQ_CLEAN_EXTERNAL_PINS_REQUIRED")
    require(len(raw) <= 16 * 1024**2 and sha256(raw).hexdigest() == archive_sha256, "CHQ_CLEAN_ARCHIVE_PIN")
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = safe_names(infos)
        require(len(names) == EXPECTED_MEMBERS and sum(i.file_size for i in infos) <= 128 * 1024**2,
                "CHQ_CLEAN_MEMBER_COUNT_OR_EXPANDED_LIMIT")
        manifest_raw = archive.read(MANIFEST)
        require(sha256(manifest_raw).hexdigest() == manifest_sha256, "CHQ_CLEAN_MANIFEST_PIN")
        manifest = decode(manifest_raw)
        require(manifest.get("schema") == "cas-meta2-child-qualification-source-package/8"
                and manifest.get("root_manifest") == MANIFEST and manifest.get("source_sha") == source_sha,
                "CHQ_CLEAN_ROOT_SOURCE_IDENTITY")
        mapping, sizes = manifest["files_sha256"], manifest["files_bytes"]
        require(set(mapping) == set(sizes) and set(names) == set(mapping) | {MANIFEST}
                and MANIFEST not in mapping, "CHQ_CLEAN_ROOT_FILE_MAP")
        for name in (*[PILOT + "/tests/" + n for n in TESTS], PILOT + "/pyproject.toml", PILOT + "/" + INSPECTOR):
            require(name in mapping, "CHQ_CLEAN_SHIPPED_TEST_OR_INSPECTOR_MISSING:" + name)
        members = {}
        expected = {**mapping, MANIFEST: manifest_sha256}
        for info in infos:
            content = archive.read(info)
            require(sha256(content).hexdigest() == expected[info.filename], "CHQ_CLEAN_MEMBER_HASH:" + info.filename)
            if info.filename != MANIFEST:
                require(type(sizes[info.filename]) is int and len(content) == sizes[info.filename],
                        "CHQ_CLEAN_MEMBER_SIZE:" + info.filename)
            members[info.filename] = content
    return manifest, members


def package_validator(package, manifest):
    """Load only externally pinned extracted bytes, never the original inspector."""
    path = unlinked(Path(package) / PILOT / INSPECTOR)
    raw = read_file(path, 1024**2)
    require(sha256(raw).hexdigest() == manifest["files_sha256"][PILOT + "/" + INSPECTOR],
            "CHQ_CLEAN_EXTRACTED_INSPECTOR_CHANGED")
    module = ModuleType("child_qualification_clean_extracted_inspector")
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def extract_checked(archive, output, *, archive_sha256, source_sha, manifest_sha256):
    output = new_output(output)
    raw = read_file(archive, 16 * 1024**2)
    manifest, members = inspect_bytes(raw, archive_sha256=archive_sha256,
                                     source_sha=source_sha, manifest_sha256=manifest_sha256)
    output.mkdir(parents=True, exist_ok=False)
    package = output / "package"
    package.mkdir()
    for name, content in sorted(members.items()):
        path = package.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
    checker = package_validator(package, manifest)
    verified = checker.verify_extracted(package, manifest)
    require(verified.get("files_verified") == EXPECTED_MEMBERS, "CHQ_CLEAN_INSPECTOR_COUNT")
    require(digest(archive) == archive_sha256, "CHQ_CLEAN_ARCHIVE_CHANGED_DURING_EXTRACTION")
    return {"package": str(package), "manifest": manifest, "extracted_check": verified,
        "member_sha256": {n: sha256(v).hexdigest() for n, v in members.items()},
        "member_bytes": {n: len(v) for n, v in members.items()}}


class ImportGuard(importlib.abc.MetaPathFinder):
    def __init__(self, pilot):
        self.pilot = Path(pilot).resolve()

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in FORBIDDEN:
            raise RuntimeError("CHQ_CLEAN_NEURAL_PROVIDER_IMPORT_REFUSED:" + fullname)
        if root in {"cas_meta2", "aws"}:
            spec = importlib.machinery.PathFinder.find_spec(fullname, path)
            if spec is not None:
                locations = list(spec.submodule_search_locations or ())
                if spec.origin not in (None, "namespace"):
                    locations.append(spec.origin)
                require(locations and all(unlinked(p).resolve().is_relative_to(self.pilot) for p in locations),
                        "CHQ_CLEAN_IMPORT_FALLBACK_REFUSED:" + fullname)
        return None


def module_paths(package, modules=None):
    pilot = (Path(package) / PILOT).resolve()
    records = {}
    for name, module in sorted((sys.modules if modules is None else modules).items()):
        if name.split(".")[0] not in {"cas_meta2", "aws"}:
            continue
        filename = getattr(module, "__file__", None)
        if filename is not None:
            path = unlinked(filename).resolve()
            require(path.is_relative_to(pilot) and path.is_file(), "CHQ_CLEAN_ORIGINAL_WORKTREE_IMPORT:" + name)
            records[name] = {"path": str(path), "sha256": digest(path)}
        else:
            paths = list(getattr(module, "__path__", ()))
            require(paths and all(unlinked(p).resolve().is_relative_to(pilot) for p in paths),
                    "CHQ_CLEAN_UNOWNED_NAMESPACE:" + name)
            records[name] = {"namespace_paths": [str(Path(p).resolve()) for p in paths]}
    return records


class TestReceipt:
    def __init__(self):
        self.collected = 0
        self.files = []
        self.reports = []

    def pytest_collection_finish(self, session):
        self.collected = len(session.items)
        self.files = sorted({Path(item.path).name for item in session.items})

    def pytest_runtest_logreport(self, report):
        self.reports.append({"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome,
                             "subtest": getattr(report, "context", None) is not None})

    def counts(self):
        regular = [r for r in self.reports if not r["subtest"]]
        return {"collected": self.collected,
            "passed": sum(r["when"] == "call" and r["outcome"] == "passed" for r in regular),
            "failed_reports": sum(r["outcome"] == "failed" for r in regular),
            "skipped_reports": sum(r["outcome"] == "skipped" for r in regular),
            "subtest_reports": sum(r["subtest"] for r in self.reports),
            "failed_subtest_reports": sum(r["subtest"] and r["outcome"] == "failed" for r in self.reports)}


def child(package, temporary, test_library, receipt_path, manifest_sha256):
    package, temporary, receipt_path = map(unlinked, (package, temporary, receipt_path))
    require(not temporary.exists() and not receipt_path.exists() and temporary.parent == package.parent
            and receipt_path.parent == package.parent, "CHQ_CLEAN_CHILD_OUTPUT_CUSTODY")
    result = {"schema": "cas-meta2-child-qualification-clean-child/8", "passed": False,
              "package": str(package), "tests": list(TESTS), "boundary": BOUNDARY}
    code, checker, manifest = None, None, None
    reports = TestReceipt()
    try:
        require(not FORBIDDEN.intersection(n.split(".")[0] for n in sys.modules), "CHQ_CLEAN_PRELOADED_FORBIDDEN_MODULE")
        pilot = package / PILOT
        sys.meta_path.insert(0, ImportGuard(pilot))
        def audit(event, arguments):
            if event == "sqlite3.connect":
                raise RuntimeError("CHQ_CLEAN_DATABASE_CONNECTION_REFUSED")
            if event in {"socket.connect", "socket.connect_ex", "socket.bind", "socket.sendto", "socket.getaddrinfo"}:
                raise RuntimeError("CHQ_CLEAN_NETWORK_OPERATION_REFUSED:" + event)
        sys.addaudithook(audit)
        sys.path.insert(0, str(pilot))
        library = unlinked(test_library)
        require((library / "pytest/__init__.py").is_file(), "CHQ_CLEAN_EXPLICIT_PYTEST_LIBRARY")
        sys.path.append(str(library))
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        require(digest(package / MANIFEST) == manifest_sha256, "CHQ_CLEAN_CHILD_MANIFEST_CHANGED")
        manifest = decode(read_file(package / MANIFEST, 4 * 1024**2))
        checker = package_validator(package, manifest)
        result["before_check"] = checker.verify_extracted(package, manifest)
        require(result["before_check"]["files_verified"] == EXPECTED_MEMBERS, "CHQ_CLEAN_CHILD_SOURCE_COUNT")
        import pytest
        command = ["-q", "-p", "no:cacheprovider", "--basetemp", str(temporary),
            "-c", str(pilot / "pyproject.toml"), "--rootdir", str(pilot), "--confcutdir", str(pilot),
            "--override-ini", "addopts=", *[str(pilot / "tests" / n) for n in TESTS]]
        result["pytest_argv"] = command
        code = pytest.main(command, plugins=[reports])
        result["counts"] = reports.counts()
        require(reports.files == sorted(TESTS) and reports.collected > 0, "CHQ_CLEAN_MANDATORY_TEST_COLLECTION")
        counts = result["counts"]
        require(counts["passed"] == counts["collected"] and not counts["failed_reports"]
                and not counts["skipped_reports"] and not counts["failed_subtest_reports"], "CHQ_CLEAN_TESTS_NOT_ALL_PASSED")
        result["passed"] = code == 0
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        result["postcheck_errors"] = {}
        try:
            result["imported_modules"] = module_paths(package)
            require(not FORBIDDEN.intersection(n.split(".")[0] for n in sys.modules), "CHQ_CLEAN_FORBIDDEN_IMPORT_AFTER")
            if checker is not None and manifest is not None:
                result["after_check"] = checker.verify_extracted(package, manifest,
                    imported_paths=[v["path"] for v in result["imported_modules"].values() if "path" in v])
                require(result.get("before_check") == result["after_check"], "CHQ_CLEAN_SOURCE_CHANGED")
        except BaseException as error:
            result["postcheck_errors"]["source_or_imports"] = {"type": type(error).__name__, "message": str(error)}
        if result["postcheck_errors"]:
            result["passed"] = False
        result.update(pytest_exit_code=code, counts=reports.counts(), collected_test_files=reports.files,
                      python=sys.version, sys_path=list(sys.path))
        write_new(receipt_path, result)
    return 0 if result["passed"] else 1


def capture(archive, output, *, archive_sha256, source_sha, manifest_sha256):
    output = new_output(output)
    started, tick, self_hash = datetime.now(timezone.utc).isoformat(), time.monotonic(), digest(__file__)
    result = {"schema": "cas-meta2-child-qualification-clean-package/8", "passed": False,
        "status": "CLEAN_CHECK_REFUSED_OR_FAILED", "source_sha": source_sha,
        "archive": str(Path(archive).absolute()), "archive_sha256": archive_sha256,
        "manifest_sha256": manifest_sha256, "tool_sha256": self_hash, "tests": list(TESTS),
        "started_utc": started, "boundary": BOUNDARY, "postcheck_errors": {}}
    process, code, timed_out, extracted = None, None, False, None
    try:
        extracted = extract_checked(archive, output, archive_sha256=archive_sha256,
                                    source_sha=source_sha, manifest_sha256=manifest_sha256)
        result.update(extracted)
        spec = importlib.util.find_spec("pytest")
        require(spec is not None and spec.origin is not None, "CHQ_CLEAN_PYTEST_UNAVAILABLE")
        library = Path(spec.origin).resolve().parent.parent
        command = [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--child",
            extracted["package"], str(output / "pytest_tmp"), str(library), str(output / "child_receipt.json"), manifest_sha256]
        child_cwd = Path(sys.executable).resolve().parent
        result.update(command=command, child_cwd=str(child_cwd), pytest_library=str(library))
        environment = dict(os.environ)
        removed = []
        for name in tuple(environment):
            if name.startswith("CAS_META2_RUN_") or name in {"CAS_META2_AWS_JOB_ID", "PYTHONPATH", "PYTHONHOME"}:
                removed.append(name)
                del environment[name]
        environment.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
        result["removed_environment_names"] = sorted(removed)
        with (output / "stdout.txt").open("xb") as stdout, (output / "stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(command, cwd=child_cwd, env=environment, stdout=stdout, stderr=stderr)
            try:
                code = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                code = process.wait(timeout=15)
        result["child_receipt"] = decode(read_file(output / "child_receipt.json", 16 * 1024**2))
        result["passed"] = code == 0 and not timed_out and result["child_receipt"].get("passed") is True
    except BaseException as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)}
        if not output.exists():
            output.mkdir(parents=True, exist_ok=False)
    finally:
        def postcheck(name, operation):
            try:
                return operation()
            except BaseException as error:
                result["postcheck_errors"][name] = {"type": type(error).__name__, "message": str(error)}
                return None
        archive_after = postcheck("archive", lambda: digest(archive))
        tool_after = postcheck("tool", lambda: digest(__file__))
        if extracted is not None:
            result["postcheck"] = postcheck("extracted_source", lambda: package_validator(
                extracted["package"], extracted["manifest"]).verify_extracted(extracted["package"], extracted["manifest"]))
        if archive_after != archive_sha256 or tool_after != self_hash:
            result["postcheck_errors"]["input_identity"] = {"archive_sha256": archive_after, "tool_sha256": tool_after}
        result["passed"] = result["passed"] and not result["postcheck_errors"]
        result.update(status="CLEAN_PURE_TESTS_PASSED" if result["passed"] else "CLEAN_CHECK_REFUSED_OR_FAILED",
            exit_code=code, timed_out=timed_out, pid=None if process is None else process.pid,
            finished_utc=datetime.now(timezone.utc).isoformat(), wall_seconds=time.monotonic()-tick,
            environment={"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
                "isolated_child": True, "bytecode_disabled": True, "pytest_plugin_autoload_disabled": True},
            forbidden_imports=sorted(FORBIDDEN), sqlite_connections_blocked=True, network_operations_blocked=True,
            native_execution=False, provider_access=False)
        result["outputs"] = {name: {"bytes": (output / name).stat().st_size, "sha256": digest(output / name)}
            for name in ("stdout.txt", "stderr.txt", "child_receipt.json") if (output / name).is_file()}
        write_new(output / "receipt.json", result)
    print(json.dumps({"receipt": str(output / "receipt.json"), "sha256": digest(output / "receipt.json"),
                      "passed": result["passed"], "status": result["status"]}))
    return 0 if result["passed"] else 1


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for flag in ("archive", "archive-sha256", "source-sha", "manifest-sha256", "output"):
        parser.add_argument("--" + flag, required=True)
    args = parser.parse_args(argv)
    return capture(args.archive, args.output, archive_sha256=args.archive_sha256,
                   source_sha=args.source_sha, manifest_sha256=args.manifest_sha256)


if __name__ == "__main__":
    if len(sys.argv) == 7 and sys.argv[1] == "--child":
        raise SystemExit(child(*sys.argv[2:]))
    raise SystemExit(main())

