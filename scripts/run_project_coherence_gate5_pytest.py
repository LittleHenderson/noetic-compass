#!/usr/bin/env python3
"""Run one Gate 5 pytest suite and emit a same-process outcome receipt.

This is a local engineering control, not a hermetic or independently attested
test runner.  It deliberately starts with ``-I -S -B`` so user ``.pth`` files
cannot execute before the runner validates and admits the locked pytest path.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from typing import Any


RECEIPT_SCHEMA = "project_coherence.gate5_same_run_pytest_receipt.v0.1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _is_reparse(value: os.stat_result) -> bool:
    attributes = getattr(value, "st_file_attributes", 0)
    tag = getattr(value, "st_reparse_tag", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)) or bool(
        tag
    )


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        stat.S_IFMT(value.st_mode),
        int(value.st_nlink),
        int(value.st_size),
        int(value.st_mtime_ns),
        int(value.st_ctime_ns),
        int(getattr(value, "st_file_attributes", 0)),
        int(getattr(value, "st_reparse_tag", 0)),
    )


def _alias_free_path(path: Path, *, anchor: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    anchor_absolute = Path(os.path.abspath(anchor))
    try:
        relative = absolute.relative_to(anchor_absolute)
    except ValueError as exc:
        raise ValueError(f"path escaped its admitted anchor: {absolute}") from exc
    current = anchor_absolute
    for part in relative.parts:
        current = current / part
        identity = current.lstat()
        if current.is_symlink() or _is_reparse(identity):
            raise ValueError(f"path contains a symlink/reparse alias: {current}")
    return absolute


def _read_stable_unique_file(path: Path) -> bytes:
    path = _alias_free_path(path, anchor=Path(os.path.abspath(path)).anchor)
    before = path.lstat()
    if (
        path.is_symlink()
        or _is_reparse(before)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
    ):
        raise ValueError(f"input is not a unique regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        handle_before = os.fstat(descriptor)
        blocks: list[bytes] = []
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            blocks.append(block)
        handle_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = path.lstat()
    payload = b"".join(blocks)
    if not (
        _identity(before) == _identity(after)
        and _identity(handle_before) == _identity(handle_after)
        and before.st_dev == handle_before.st_dev
        and before.st_ino == handle_before.st_ino
        and before.st_size == handle_before.st_size == len(payload)
    ):
        raise ValueError(f"input identity changed while reading: {path}")
    return payload


def _load_unique_json(payload: bytes) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key!r}")
            result[key] = value
        return result

    value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ValueError("runner lock is not an object")
    return value


def _locked_site_file_map(
    lock: dict[str, Any], site_root: Path
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for distribution in lock.get("admitted_runner_distributions", []):
        if not isinstance(distribution, dict):
            raise ValueError("locked runner distribution is malformed")
        owner = distribution.get("canonical_distribution")
        files = distribution.get("files")
        if not isinstance(owner, str) or not owner or not isinstance(files, list):
            raise ValueError("locked runner distribution inventory is malformed")
        for record in files:
            if not isinstance(record, dict) or set(record) != {
                "path",
                "bytes",
                "sha256",
                "owner_distribution",
            }:
                raise ValueError("locked runner file record is malformed")
            raw_path = record["path"]
            if (
                not isinstance(raw_path, str)
                or not raw_path
                or "\\" in raw_path
                or PurePosixPath(raw_path).is_absolute()
                or any(
                    part in {"", ".", ".."}
                    for part in PurePosixPath(raw_path).parts
                )
                or record["owner_distribution"] != owner
            ):
                raise ValueError("locked runner file path/owner is malformed")
            path = _alias_free_path(
                site_root.joinpath(*PurePosixPath(raw_path).parts),
                anchor=Path(site_root.anchor),
            )
            try:
                path.relative_to(site_root)
            except ValueError as exc:
                raise ValueError("locked runner file escaped the site root") from exc
            key = str(path).casefold()
            if key in result:
                raise ValueError("duplicate/case-colliding locked runner file")
            result[key] = record
    if not result:
        raise ValueError("locked runner file map is empty")
    return result


def _locked_import_origin(
    module_name: str,
    *,
    site_root: Path,
    locked_files: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    spec = importlib.util.find_spec(module_name)
    if spec is None or not isinstance(spec.origin, str):
        raise ValueError(f"locked import has no file origin: {module_name}")
    origin = _alias_free_path(Path(spec.origin), anchor=Path(site_root.anchor))
    record = locked_files.get(str(origin).casefold())
    if record is None:
        raise ValueError(f"locked import resolved outside its file lock: {module_name} -> {origin}")
    payload = _read_stable_unique_file(origin)
    digest = hashlib.sha256(payload).hexdigest().upper()
    if record["bytes"] != len(payload) or record["sha256"] != digest:
        raise ValueError(f"locked import identity drifted: {module_name}")
    if spec.submodule_search_locations is not None:
        for raw_location in spec.submodule_search_locations:
            location = _alias_free_path(
                Path(raw_location), anchor=Path(site_root.anchor)
            )
            try:
                location.relative_to(site_root)
            except ValueError as exc:
                raise ValueError(
                    f"locked package search location escaped the site root: {module_name}"
                ) from exc
    return {
        "path": str(origin),
        "bytes": len(payload),
        "sha256": digest,
        "module_names": [module_name],
        "kind": (
            "NATIVE"
            if origin.suffix.casefold() in {".dll", ".pyd", ".so", ".dylib"}
            else "PYTHON_OR_DATA"
        ),
    }


def _import_locked_module(
    module_name: str,
    *,
    site_root: Path,
    locked_files: dict[str, dict[str, Any]],
    origin_records: list[dict[str, Any]],
) -> Any:
    names = [module_name.split(".", 1)[0]]
    if names[0] != module_name:
        names.append(module_name)
    imported = None
    for name in names:
        if any(record["module_names"] == [name] for record in origin_records):
            imported = importlib.import_module(name)
            continue
        origin = _locked_import_origin(
            name, site_root=site_root, locked_files=locked_files
        )
        imported = importlib.import_module(name)
        raw_imported_path = getattr(imported, "__file__", None)
        if not isinstance(raw_imported_path, str):
            raise ValueError(f"locked import did not retain a file origin: {name}")
        imported_path = _alias_free_path(
            Path(raw_imported_path), anchor=Path(site_root.anchor)
        )
        if str(imported_path).casefold() != origin["path"].casefold():
            raise ValueError(f"locked import origin changed during import: {name}")
        origin_records.append(origin)
    return imported


def _canonical_nodeid(nodeid: str) -> str:
    if not isinstance(nodeid, str) or not nodeid:
        raise ValueError("pytest emitted an empty node ID")
    value = nodeid.replace("\\", "/")
    if any(marker in value for marker in ("\x00", "\r", "\n")):
        raise ValueError("pytest emitted a multiline or NUL-containing node ID")
    return value


def _module_inventory() -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for module_name, module in sorted(sys.modules.items()):
        raw_path = getattr(module, "__file__", None)
        if not isinstance(raw_path, str) or not raw_path:
            continue
        path = Path(raw_path)
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved.suffix.casefold() in {".pyc", ".pyo"}:
            source = Path(importlib.util.source_from_cache(str(resolved)))
            if source.is_file():
                resolved = source.resolve(strict=True)
        if not resolved.is_file():
            continue
        key = str(resolved).casefold()
        record = records.setdefault(
            key,
            {
                "path": str(resolved),
                "bytes": resolved.stat().st_size,
                "sha256": _sha256_file(resolved),
                "module_names": [],
                "kind": (
                    "NATIVE"
                    if resolved.suffix.casefold() in {".dll", ".pyd", ".so", ".dylib"}
                    else "PYTHON_OR_DATA"
                ),
            },
        )
        record["module_names"].append(module_name)
    for record in records.values():
        record["module_names"].sort()
    return sorted(records.values(), key=lambda item: item["path"].casefold())


class SameRunReceiptPlugin:
    def __init__(self) -> None:
        self.collected_nodeids: list[str] = []
        self.started_nodeids: list[str] = []
        self.finished_nodeids: list[str] = []
        self.ordinary_reports: list[dict[str, Any]] = []
        self.subtest_reports: list[dict[str, Any]] = []
        self.collection_errors: list[dict[str, str]] = []
        self.internal_errors: list[str] = []
        self.deselected_nodeids: list[str] = []
        self.warning_count = 0
        self.rootdir: str | None = None
        self.inifile: str | None = None
        self.plugin_inventory: list[dict[str, str]] = []

    def pytest_collection_finish(self, session: Any) -> None:
        self.collected_nodeids = [_canonical_nodeid(item.nodeid) for item in session.items]

    def pytest_collectreport(self, report: Any) -> None:
        if report.failed:
            self.collection_errors.append(
                {
                    "nodeid": _canonical_nodeid(report.nodeid),
                    "longrepr_sha256": hashlib.sha256(
                        str(report.longrepr).encode("utf-8")
                    ).hexdigest().upper(),
                }
            )

    def pytest_deselected(self, items: list[Any]) -> None:
        self.deselected_nodeids.extend(_canonical_nodeid(item.nodeid) for item in items)

    def pytest_runtest_logstart(self, nodeid: str, location: Any) -> None:
        del location
        self.started_nodeids.append(_canonical_nodeid(nodeid))

    def pytest_runtest_logreport(self, report: Any) -> None:
        record = {
            "nodeid": _canonical_nodeid(report.nodeid),
            "when": str(report.when),
            "outcome": str(report.outcome),
            "wasxfail": bool(getattr(report, "wasxfail", False)),
        }
        if "subtest" in type(report).__name__.casefold():
            context = getattr(report, "context", None)
            record["context"] = "" if context is None else str(context)
            self.subtest_reports.append(record)
        else:
            self.ordinary_reports.append(record)

    def pytest_runtest_logfinish(self, nodeid: str, location: Any) -> None:
        del location
        self.finished_nodeids.append(_canonical_nodeid(nodeid))

    def pytest_internalerror(self, excrepr: Any, excinfo: Any) -> None:
        del excinfo
        self.internal_errors.append(
            hashlib.sha256(str(excrepr).encode("utf-8")).hexdigest().upper()
        )

    def pytest_warning_recorded(
        self, warning_message: Any, when: str, nodeid: str, location: Any
    ) -> None:
        del warning_message, when, nodeid, location
        self.warning_count += 1

    def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> None:
        del exitstatus
        config = session.config
        self.rootdir = str(config.rootpath.resolve())
        self.inifile = None if config.inipath is None else str(config.inipath.resolve())
        inventory: list[dict[str, str]] = []
        for name, plugin in config.pluginmanager.list_name_plugin():
            if plugin is None:
                continue
            inventory.append(
                {
                    "name": str(name),
                    "implementation": (
                        getattr(plugin, "__name__", None)
                        or f"{type(plugin).__module__}.{type(plugin).__qualname__}"
                    ),
                }
            )
        self.plugin_inventory = sorted(
            inventory, key=lambda item: (item["name"], item["implementation"])
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--expected-lock-sha256", required=True)
    parser.add_argument("--suite-name", required=True)
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--expected-parent-pid", type=int, required=True)
    parser.add_argument("--working-directory", required=True)
    parser.add_argument("--pycache-prefix", required=True)
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--plugin", action="append", default=[])
    parser.add_argument("--repo-import-root", action="append", default=[])
    args = parser.parse_args()
    if not args.target:
        parser.error("at least one --target is required")
    return args


def main() -> int:
    args = _parse_args()
    required_flags = {
        "isolated": 1,
        "no_site": 1,
        "no_user_site": 1,
        "safe_path": True,
        "ignore_environment": 1,
        "dont_write_bytecode": 1,
    }
    actual_flags = {
        name: getattr(sys.flags, name) for name in required_flags
    }
    if actual_flags != required_flags:
        raise SystemExit(f"unsafe Python startup flags: {actual_flags!r}")
    if os.getppid() != args.expected_parent_pid:
        raise SystemExit("runner parent PID differs from the verifier receipt")
    if len(args.nonce) != 64 or any(ch not in "0123456789abcdef" for ch in args.nonce):
        raise SystemExit("runner nonce is not 256-bit lowercase hexadecimal")

    pycache_prefix = Path(args.pycache_prefix).resolve(strict=True)
    if any(pycache_prefix.iterdir()):
        raise SystemExit("fresh pycache prefix is not empty before runner startup")
    if Path(sys.pycache_prefix or "").resolve() != pycache_prefix:
        raise SystemExit("Python pycache prefix differs from the verifier argument")

    lock_path = _alias_free_path(
        Path(args.lock), anchor=Path(Path(os.path.abspath(args.lock)).anchor)
    )
    lock_bytes = _read_stable_unique_file(lock_path)
    lock_sha256 = hashlib.sha256(lock_bytes).hexdigest().upper()
    if lock_sha256 != args.expected_lock_sha256:
        raise SystemExit("runner lock hash differs from the verifier argument")
    lock = _load_unique_json(lock_bytes)
    site_root = _alias_free_path(
        Path(lock["admitted_pytest_site_root"]),
        anchor=Path(Path(lock["admitted_pytest_site_root"]).anchor),
    )
    if not site_root.is_dir():
        raise SystemExit("locked pytest site root is not a directory")
    startup_sys_path = list(sys.path)
    repo_root = _alias_free_path(
        Path(__file__).absolute().parents[1],
        anchor=Path(Path(os.path.abspath(__file__)).anchor),
    )
    working_directory = _alias_free_path(
        Path(args.working_directory), anchor=Path(Path(args.working_directory).anchor)
    )
    repo_import_roots = [
        _alias_free_path(Path(path), anchor=Path(Path(path).anchor))
        for path in args.repo_import_root
    ]
    for path in [working_directory, *repo_import_roots]:
        try:
            path.relative_to(repo_root)
        except ValueError as exc:
            raise SystemExit(f"repository runtime path escaped the runner repository: {path}") from exc
    if any(not path.is_dir() for path in repo_import_roots):
        raise SystemExit("an admitted repository import root is not a directory")
    if len({str(path).casefold() for path in repo_import_roots}) != len(
        repo_import_roots
    ):
        raise SystemExit("admitted repository import roots contain a duplicate")
    repo_runtime_paths = [working_directory, *repo_import_roots]
    if len({str(path).casefold() for path in repo_runtime_paths}) != len(
        repo_runtime_paths
    ):
        raise SystemExit("suite working directory duplicates a repository import root")

    # Admit only the locked pytest site long enough to load pytest and the
    # explicit plugins.  Then put the exact repository roots first so a
    # user-site package cannot shadow the bound implementation under test.
    sys.path.append(str(site_root))

    locked_site_files = _locked_site_file_map(lock, site_root)
    locked_import_origin_files: list[dict[str, Any]] = []
    pytest = _import_locked_module(
        "pytest",
        site_root=site_root,
        locked_files=locked_site_files,
        origin_records=locked_import_origin_files,
    )

    if pytest.__version__ != lock["pytest_version"]:
        raise SystemExit("pytest version differs from the local runner lock")
    plugin_modules = [
        _import_locked_module(
            name,
            site_root=site_root,
            locked_files=locked_site_files,
            origin_records=locked_import_origin_files,
        )
        for name in args.plugin
    ]
    pre_test_loaded_module_files = _module_inventory()
    sys.path[0:0] = [str(path) for path in repo_runtime_paths]
    plugin = SameRunReceiptPlugin()
    os.chdir(working_directory)
    pytest_args = [
        "-q",
        "-p",
        "no:cacheprovider",
        "--tb=short",
        "--color=no",
        "--disable-warnings",
        "--import-mode=importlib",
        *args.target,
    ]
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(
        captured_stderr
    ):
        exit_status = int(pytest.main(pytest_args, plugins=[plugin, *plugin_modules]))

    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "suite_name": args.suite_name,
        "nonce": args.nonce,
        "pid": os.getpid(),
        "parent_pid": os.getppid(),
        "working_directory": str(working_directory),
        "targets": args.target,
        "explicit_pytest_plugins": args.plugin,
        "admitted_repo_import_roots": [str(path) for path in repo_import_roots],
        "pytest_version": pytest.__version__,
        "pytest_exit_status": exit_status,
        "runner_lock_sha256": lock_sha256,
        "python_flags": actual_flags,
        "startup_sys_path": startup_sys_path,
        "locked_import_origin_files": locked_import_origin_files,
        "pre_test_loaded_module_files": pre_test_loaded_module_files,
        "final_sys_path": list(sys.path),
        "pytest_rootdir": plugin.rootdir,
        "pytest_inifile": plugin.inifile,
        "plugin_inventory": plugin.plugin_inventory,
        "collected_nodeids": plugin.collected_nodeids,
        "started_nodeids": plugin.started_nodeids,
        "finished_nodeids": plugin.finished_nodeids,
        "ordinary_reports": plugin.ordinary_reports,
        "subtest_reports": plugin.subtest_reports,
        "collection_errors": plugin.collection_errors,
        "internal_errors": plugin.internal_errors,
        "deselected_nodeids": plugin.deselected_nodeids,
        "warning_count": plugin.warning_count,
        "captured_stdout_sha256": hashlib.sha256(
            captured_stdout.getvalue().encode("utf-8")
        ).hexdigest().upper(),
        "captured_stderr_sha256": hashlib.sha256(
            captured_stderr.getvalue().encode("utf-8")
        ).hexdigest().upper(),
        "loaded_module_files": _module_inventory(),
        "pycache_prefix_empty_after_run": not any(pycache_prefix.iterdir()),
    }
    receipt_path = Path(args.receipt).resolve()
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = receipt_path.with_name(receipt_path.name + ".tmp")
    payload = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    temporary_path.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temporary_path, receipt_path)
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
