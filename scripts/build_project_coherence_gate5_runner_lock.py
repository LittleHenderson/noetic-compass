#!/usr/bin/env python3
"""Build a local, non-hermetic Gate 5 pytest runner content lock."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import stat
import sys
import sysconfig
from typing import Any


REQUIRED_DISTRIBUTIONS = (
    "pytest",
    "pytest-asyncio",
    "pluggy",
    "iniconfig",
    "packaging",
    "Pygments",
    "colorama",
)


def _canonical_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


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


def _require_alias_free_components(path: Path, *, anchor: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    anchor_absolute = Path(os.path.abspath(anchor))
    try:
        relative = absolute.relative_to(anchor_absolute)
    except ValueError as exc:
        raise RuntimeError(f"runner-lock input escaped its anchor: {absolute}") from exc
    current = anchor_absolute
    for part in relative.parts:
        current = current / part
        identity = current.lstat()
        if current.is_symlink() or _is_reparse(identity):
            raise RuntimeError(f"runner-lock path contains a symlink/reparse alias: {current}")
    return absolute


def _regular_file_record(path: Path, *, anchor: Path | None = None) -> dict[str, Any]:
    path = _require_alias_free_components(path, anchor=anchor or Path(path.anchor))
    before = path.lstat()
    if (
        path.is_symlink()
        or _is_reparse(before)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
    ):
        raise RuntimeError(f"runner-lock input is not a unique regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        handle_before = os.fstat(descriptor)
        digest = hashlib.sha256()
        byte_count = 0
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            byte_count += len(block)
            digest.update(block)
        handle_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after = path.lstat()
    if not (
        _identity(before) == _identity(after)
        and _identity(handle_before) == _identity(handle_after)
        and before.st_dev == handle_before.st_dev
        and before.st_ino == handle_before.st_ino
        and before.st_size == handle_before.st_size == byte_count
    ):
        raise RuntimeError(f"runner-lock input changed while hashing: {path}")
    return {
        "path": str(path),
        "bytes": byte_count,
        "sha256": digest.hexdigest().upper(),
    }


def _distribution_records(site_root: Path) -> list[dict[str, Any]]:
    available: dict[str, importlib.metadata.Distribution] = {}
    for distribution in importlib.metadata.distributions(path=[str(site_root)]):
        name = distribution.metadata.get("Name")
        if isinstance(name, str):
            canonical_name = _canonical_distribution_name(name)
            if canonical_name in available:
                raise RuntimeError(
                    f"duplicate normalized runner distribution: {canonical_name}"
                )
            available[canonical_name] = distribution

    records: list[dict[str, Any]] = []
    global_file_owners: dict[str, str] = {}
    for required_name in REQUIRED_DISTRIBUTIONS:
        key = _canonical_distribution_name(required_name)
        distribution = available.get(key)
        if distribution is None:
            raise RuntimeError(f"required runner distribution is missing: {required_name}")
        files: list[tuple[str, int, str]] = []
        excluded_outside_site_files: list[dict[str, str]] = []
        for package_path in distribution.files or ():
            record_path = str(package_path).replace("\\", "/")
            relative = Path(record_path)
            if "__pycache__" in relative.parts or relative.suffix.casefold() in {
                ".pyc",
                ".pyo",
            }:
                continue
            path = Path(os.path.abspath(distribution.locate_file(package_path)))
            try:
                path.relative_to(site_root)
            except ValueError:
                # Console entry points live in the sibling Scripts directory.
                # The same-process runner imports packages directly and never
                # executes those wrappers, so they are explicitly inventoried
                # as excluded rather than silently omitted from the lock.
                scripts_root = site_root.parent / "Scripts"
                try:
                    path.relative_to(scripts_root)
                except ValueError as exc:
                    raise RuntimeError(
                        f"runner distribution RECORD path escaped the site/Scripts roots: {path}"
                    ) from exc
                if not path.is_file():
                    raise RuntimeError(
                        f"runner distribution RECORD entry is missing: {path}"
                    )
                excluded_outside_site_files.append(
                    {
                        "record_path": record_path,
                        "path": str(path),
                        "reason": "SIBLING_SCRIPTS_ENTRY_POINT / NOT EXECUTED",
                    }
                )
                continue
            if not path.is_file():
                raise RuntimeError(f"runner distribution RECORD entry is missing: {path}")
            record = _regular_file_record(path, anchor=Path(site_root.anchor))
            raw_relative = path.relative_to(site_root).as_posix()
            folded_relative = raw_relative.casefold()
            previous_owner = global_file_owners.get(folded_relative)
            if previous_owner is not None:
                raise RuntimeError(
                    f"runner file has duplicate/case-colliding owners: {raw_relative} "
                    f"({previous_owner}, {key})"
                )
            global_file_owners[folded_relative] = key
            files.append((raw_relative, record["bytes"], record["sha256"]))
        files.sort(key=lambda item: item[0])
        if not files:
            raise RuntimeError(f"runner distribution has no bound files: {required_name}")
        digest = hashlib.sha256()
        for raw_path, byte_count, file_sha256 in files:
            digest.update(raw_path.encode("utf-8"))
            digest.update(b"\x00")
            digest.update(str(byte_count).encode("ascii"))
            digest.update(b"\x00")
            digest.update(file_sha256.encode("ascii"))
            digest.update(b"\n")
        records.append(
            {
                "distribution": distribution.metadata["Name"],
                "canonical_distribution": key,
                "version": distribution.version,
                "file_count": len(files),
                "byte_count": sum(item[1] for item in files),
                "tree_sha256": digest.hexdigest().upper(),
                "files": [
                    {
                        "path": raw_path,
                        "bytes": byte_count,
                        "sha256": file_sha256,
                        "owner_distribution": key,
                    }
                    for raw_path, byte_count, file_sha256 in files
                ],
                "excluded_outside_site_files": sorted(
                    excluded_outside_site_files,
                    key=lambda item: item["record_path"].casefold(),
                ),
                "tree_digest_rule": (
                    "ordinal-sorted site-root-contained distribution file path + "
                    "NUL + decimal bytes + NUL + uppercase file SHA-256 + LF; "
                    "pyc/pyo and sibling Scripts entry points excluded"
                ),
            }
        )
    return sorted(records, key=lambda item: item["distribution"].casefold())


def build_lock(site_root: Path) -> dict[str, Any]:
    site_root = _require_alias_free_components(
        site_root, anchor=Path(os.path.abspath(site_root)).anchor
    )
    if not site_root.is_dir():
        raise RuntimeError("pytest site root is not a directory")
    interpreter_paths = [
        Path(sys.executable).resolve(strict=True),
        (Path(sys.base_prefix) / "python314.dll").resolve(strict=True),
        (Path(sys.base_prefix) / "python3.dll").resolve(strict=True),
    ]
    pth_records = []
    for path in sorted(site_root.glob("*.pth"), key=lambda item: item.name.casefold()):
        record = _regular_file_record(path, anchor=Path(site_root.anchor))
        pth_records.append(
            {
                "name": path.name,
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "executed_at_runner_startup": False,
            }
        )
    distributions = _distribution_records(site_root)
    pytest_record = next(
        record for record in distributions if record["distribution"].casefold() == "pytest"
    )
    return {
        "schema_version": "project_coherence.gate5_local_test_runner_lock.v0.1",
        "document_status": "DRAFT / OPEN / NOT FROZEN",
        "gate5_status": "OPEN",
        "gate_decision": "KEEP_OPEN",
        "experimental_execution_status": "NOT_STARTED",
        "admission_ring": 4,
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "public_disclosure_authorized": False,
        "canon_effect": "NONE",
        "product_claim_effect": "NONE",
        "lock_scope": "LOCAL_CONTENT_LOCK / SELF-OBSERVED / NOT HERMETIC / NOT INDEPENDENTLY ATTESTED",
        "required_child_invocation": "python -I -S -B -X pycache_prefix=<fresh-empty-directory>",
        "python_identity": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "cache_tag": sys.implementation.cache_tag,
            "compiler": platform.python_compiler(),
            "architecture": platform.machine(),
            "soabi": sysconfig.get_config_var("SOABI"),
            "interpreter_files": [
                _regular_file_record(path, anchor=Path(path.anchor))
                for path in interpreter_paths
            ],
            "stdlib_root": str(Path(sysconfig.get_path("stdlib")).resolve()),
            "stdlib_content_lock": "NOT ESTABLISHED",
        },
        "admitted_pytest_site_root": str(site_root),
        "pytest_version": pytest_record["version"],
        "admitted_runner_distributions": distributions,
        "startup_pth_inventory": pth_records,
        "startup_pth_execution": "DISABLED BY -I -S",
        "unbound_runtime_surface": {
            "stdlib_content": "OPEN",
            "test_import_dependencies_outside_admitted_runner_distributions": "OPEN",
            "distribution_files_absent_from_upstream_record": "OPEN",
            "transient_unloaded_or_dynamic_module_execution": "OPEN",
            "exact_loader_executed_bytecode": "OPEN",
            "unresolved_or_deleted_module_origins": "OPEN",
            "native_dependency_closure": "OPEN",
            "child_process_closure": "OPEN",
            "kernel_and_filesystem_trust": "OPEN",
            "independent_signer_or_trust_root": "OPEN",
        },
        "claim_boundary": {
            "same_run_receipt_effect": "LOCAL ENGINEERING REGRESSION ONLY",
            "hermeticity_effect": "NONE",
            "scientific_effect": "NONE",
            "canon_effect": "NONE",
            "product_claim_effect": "NONE",
            "license_effect": "NONE",
            "disclosure_effect": "NONE",
        },
    }


def main() -> int:
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise SystemExit(
            "runner-lock generation requires `python -I -S -B "
            "scripts/build_project_coherence_gate5_runner_lock.py ...`"
        )
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-root", required=True)
    parser.add_argument(
        "--output",
        default=(
            "docs/working/project_coherence/gate5/"
            "GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json"
        ),
    )
    args = parser.parse_args()
    output = Path(args.output).resolve()
    payload = json.dumps(
        build_lock(Path(args.site_root)), indent=2, ensure_ascii=False
    ) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
