"""Fail closed when committed browser runtime assets drift from CNCM sources."""

from __future__ import annotations

import ast
from io import BytesIO
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo


SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
TARGET_ROOT = SITE_ROOT.parent
CNCM_ROOT = TARGET_ROOT / "cncm"
FIXTURES_ROOT = TARGET_ROOT / "fixtures"
SOURCE_SPEC = TARGET_ROOT / "cas_reasoner.txt"
GOLDEN_MANIFEST = TARGET_ROOT / "golden" / "manifest.json"
BRIDGE_SOURCE = SCRIPT_DIR / "cncm_browser_bridge.py"
PUBLIC_RUNTIME = SITE_ROOT / "public" / "runtime"
PUBLIC_FIXTURES = SITE_ROOT / "public" / "fixtures"
PUBLIC_MATH_FIXTURES = PUBLIC_FIXTURES / "math"
PUBLIC_PYODIDE = SITE_ROOT / "public" / "pyodide"
PYODIDE_PACKAGE = SITE_ROOT / "node_modules" / "pyodide"

RUNTIME_SCHEMA_VERSION = "cncm.browser-runtime/0.7"
RUNTIME_VERSION = "0.1.0"
CONVERSATION_PROTOCOL_VERSION = "0.2.0"
CAPABILITIES = [
    "problem_lab",
    "controlled_english_conversation",
    "exact_math",
    "verified_language_apprenticeship_local",
    "verified_cognitive_apprenticeship_local",
]
EXPECTED_CNCM_FILES = (
    "__init__.py",
    "__main__.py",
    "api.py",
    "canonical.py",
    "cli.py",
    "cognitive_apprenticeship.py",
    "conversation.py",
    "engine.py",
    "kernel.py",
    "language_apprenticeship.py",
    "math_api.py",
    "math_counterexample.py",
    "math_engine.py",
    "math_kernel.py",
    "math_model.py",
    "math_normalize.py",
    "math_parser.py",
    "model.py",
    "semantics.py",
    "verification.py",
)
EXPECTED_FIXTURES = (
    "branch_rollback",
    "contradiction",
    "deduction",
    "memory_recall",
    "missing_information",
    "rpm_failure",
    "rpm_recursion",
    "transitive_reasoning",
)
EXPECTED_MATH_STATUS = {
    "algebra": "EXECUTABLE",
    "arithmetic": "EXECUTABLE",
    "contradiction": "EXECUTABLE",
    "counterexamples": "EXECUTABLE",
    "recursive_learning": "CONTRACT_ONLY",
    "transitive_relations": "EXECUTABLE",
}
PYODIDE_ASSETS = (
    "pyodide.mjs",
    "pyodide.asm.mjs",
    "pyodide.asm.wasm",
    "pyodide-lock.json",
    "python_stdlib.zip",
)


class RuntimeDriftError(RuntimeError):
    """A generated runtime artifact does not match its current source."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeDriftError(message)


def require_file(path: Path, label: str) -> Path:
    require(path.is_file(), f"missing {label}: {path}")
    return path


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_bytes(path: Path, label: str) -> bytes:
    return require_file(path, label).read_bytes()


def load_json(path: Path, label: str) -> dict[str, Any]:
    payload = read_bytes(path, label)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeDriftError(f"invalid {label}: {path}: {exc}") from exc
    require(type(value) is dict, f"{label} must contain one JSON object: {path}")
    return value


def zip_entry(name: str) -> ZipInfo:
    entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = ZIP_DEFLATED
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    return entry


def bridge_version_from_source() -> str:
    tree = ast.parse(BRIDGE_SOURCE.read_text(encoding="utf-8"), filename=str(BRIDGE_SOURCE))
    matches: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Name)
            and target.id == "_BRIDGE_VERSION"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            matches.append(node.value.value)
    require(
        len(matches) == 1 and bool(matches[0]),
        "browser bridge must declare exactly one nonempty _BRIDGE_VERSION",
    )
    return matches[0]


def first_difference(expected: Any, actual: Any, path: str = "$") -> str | None:
    if type(expected) is not type(actual):
        return (
            f"{path}: expected type {type(expected).__name__}, "
            f"found {type(actual).__name__}"
        )
    if isinstance(expected, dict):
        expected_keys = set(expected)
        actual_keys = set(actual)
        if expected_keys != actual_keys:
            missing = sorted(expected_keys - actual_keys)
            extra = sorted(actual_keys - expected_keys)
            return f"{path}: missing keys {missing!r}; extra keys {extra!r}"
        for key in sorted(expected):
            difference = first_difference(expected[key], actual[key], f"{path}.{key}")
            if difference is not None:
                return difference
        return None
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"{path}: expected {len(expected)} items, found {len(actual)}"
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            difference = first_difference(
                expected_item,
                actual_item,
                f"{path}[{index}]",
            )
            if difference is not None:
                return difference
        return None
    if expected != actual:
        return f"{path}: expected {expected!r}, found {actual!r}"
    return None


def expected_archive(package_payloads: list[tuple[str, bytes]], bridge: bytes) -> bytes:
    buffer = BytesIO()
    with ZipFile(
        buffer,
        "w",
        compression=ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for relative, payload in package_payloads:
            archive.writestr(zip_entry(relative), payload)
        archive.writestr(zip_entry("cncm_browser_bridge.py"), bridge)
    return buffer.getvalue()


def check_runtime() -> dict[str, Any]:
    bridge_version = bridge_version_from_source()
    actual_cncm_files = tuple(sorted(path.name for path in CNCM_ROOT.glob("*.py")))
    require(
        actual_cncm_files == EXPECTED_CNCM_FILES,
        f"unexpected CNCM package surface: {actual_cncm_files!r}",
    )

    package_payloads: list[tuple[str, bytes]] = []
    package_records: list[dict[str, Any]] = []
    tree_lines: list[str] = []
    for filename in EXPECTED_CNCM_FILES:
        source = CNCM_ROOT / filename
        payload = read_bytes(source, "CNCM package file")
        relative = f"cncm/{filename}"
        file_hash = sha256_bytes(payload)
        package_payloads.append((relative, payload))
        package_records.append(
            {"path": relative, "bytes": len(payload), "sha256": file_hash}
        )
        tree_lines.append(f"{relative} {len(payload)} {file_hash}\n")

    bridge_payload = read_bytes(BRIDGE_SOURCE, "browser bridge source")
    expected_archive_payload = expected_archive(package_payloads, bridge_payload)
    expected_archive_hash = sha256_bytes(expected_archive_payload)
    archive_path = PUBLIC_RUNTIME / "cncm-runtime.zip"
    actual_archive_payload = read_bytes(archive_path, "runtime archive")

    expected_members = [relative for relative, _ in package_payloads] + [
        "cncm_browser_bridge.py"
    ]
    expected_member_payloads = dict(package_payloads)
    expected_member_payloads["cncm_browser_bridge.py"] = bridge_payload
    try:
        with ZipFile(BytesIO(actual_archive_payload), "r") as archive:
            actual_members = [entry.filename for entry in archive.infolist()]
            require(
                actual_members == expected_members,
                f"runtime archive members differ: {actual_members!r}",
            )
            require(
                len(actual_members) == len(set(actual_members)),
                "runtime archive contains duplicate member names",
            )
            for name in expected_members:
                require(
                    archive.read(name) == expected_member_payloads[name],
                    f"runtime archive member differs from source: {name}",
                )
    except BadZipFile as exc:
        raise RuntimeDriftError(f"invalid runtime archive: {archive_path}: {exc}") from exc
    require(
        actual_archive_payload == expected_archive_payload,
        "runtime archive bytes differ from the deterministic current-source build",
    )

    fixture_records: list[dict[str, Any]] = []
    for name in EXPECTED_FIXTURES:
        source = FIXTURES_ROOT / name / "problem.json"
        source_payload = read_bytes(source, "fixture source")
        public_payload = read_bytes(
            PUBLIC_FIXTURES / f"{name}.json",
            "published fixture",
        )
        require(public_payload == source_payload, f"published fixture differs: {name}")
        fixture_records.append(
            {
                "name": name,
                "bytes": len(source_payload),
                "sha256": sha256_bytes(source_payload),
            }
        )

    math_sources = sorted((FIXTURES_ROOT / "math").glob("*/case.json"))
    math_categories = tuple(path.parent.name for path in math_sources)
    require(
        math_categories == tuple(sorted(EXPECTED_MATH_STATUS)),
        f"unexpected math fixture surface: {math_categories!r}",
    )
    math_fixture_records: list[dict[str, Any]] = []
    for source in math_sources:
        category = source.parent.name
        source_payload = read_bytes(source, "math fixture source")
        document = load_json(source, "math fixture source")
        require(
            document.get("schema_version") == "cncm.math-fixture/0.1",
            f"math fixture schema mismatch: {source}",
        )
        require(document.get("category") == category, f"math fixture category mismatch: {source}")
        require(
            document.get("runtime_status") == EXPECTED_MATH_STATUS[category],
            f"math fixture runtime status mismatch: {source}",
        )
        public_payload = read_bytes(
            PUBLIC_MATH_FIXTURES / f"{category}.json",
            "published math fixture",
        )
        require(public_payload == source_payload, f"published math fixture differs: {category}")
        math_fixture_records.append(
            {
                "name": category,
                "path": f"/fixtures/math/{category}.json",
                "fixture_id": document["fixture_id"],
                "operation": document["operation"],
                "runtime_status": document["runtime_status"],
                "bytes": len(source_payload),
                "sha256": sha256_bytes(source_payload),
            }
        )

    pyodide_package = load_json(PYODIDE_PACKAGE / "package.json", "Pyodide package")
    pyodide_version = pyodide_package.get("version")
    require(
        isinstance(pyodide_version, str) and bool(pyodide_version),
        "Pyodide package version must be a nonempty string",
    )
    for name in PYODIDE_ASSETS:
        installed_payload = read_bytes(PYODIDE_PACKAGE / name, "installed Pyodide asset")
        published_payload = read_bytes(PUBLIC_PYODIDE / name, "published Pyodide asset")
        require(
            published_payload == installed_payload,
            f"published Pyodide asset differs from the installed package: {name}",
        )

    source_payload = read_bytes(SOURCE_SPEC, "authoritative source specification")
    golden_payload = read_bytes(GOLDEN_MANIFEST, "golden manifest")
    package_tree_hash = sha256_bytes("".join(tree_lines).encode("utf-8"))
    expected_metadata = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "bridge_version": bridge_version,
        "conversation_protocol_version": CONVERSATION_PROTOCOL_VERSION,
        "capabilities": CAPABILITIES,
        "pyodide_version": pyodide_version,
        "runtime_archive": {
            "path": "/runtime/cncm-runtime.zip",
            "bytes": len(expected_archive_payload),
            "sha256": expected_archive_hash,
        },
        "package_tree_sha256": package_tree_hash,
        "package_files": package_records,
        "fixtures": fixture_records,
        "math_fixtures": math_fixture_records,
        "source_spec": {
            "path": "cas_reasoner.txt",
            "bytes": len(source_payload),
            "sha256": sha256_bytes(source_payload),
        },
        "golden_manifest_sha256": sha256_bytes(golden_payload),
    }

    metadata_path = PUBLIC_RUNTIME / "runtime-meta.json"
    actual_metadata = load_json(metadata_path, "runtime metadata")
    difference = first_difference(expected_metadata, actual_metadata)
    require(difference is None, f"runtime metadata differs: {difference}")
    expected_metadata_payload = (
        json.dumps(expected_metadata, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    require(
        metadata_path.read_bytes() == expected_metadata_payload,
        "runtime metadata JSON is not in its deterministic generated form",
    )

    expected_module = (
        "// Generated by scripts/build-runtime.py.\n"
        f"export const EXPECTED_RUNTIME_SHA256 = {json.dumps(expected_archive_hash)};\n"
        f"export const EXPECTED_RUNTIME_BYTES = {len(expected_archive_payload)};\n"
        f"export const EXPECTED_RUNTIME_VERSION = {json.dumps(RUNTIME_VERSION)};\n"
        f"export const BRIDGE_VERSION = {json.dumps(bridge_version)};\n"
        "export const CONVERSATION_PROTOCOL_VERSION = "
        f"{json.dumps(CONVERSATION_PROTOCOL_VERSION)};\n"
        f"export const PACKAGE_TREE_SHA256 = {json.dumps(package_tree_hash)};\n"
        f"export const SOURCE_SPEC_SHA256 = {json.dumps(sha256_bytes(source_payload))};\n"
        f"export const PYODIDE_VERSION = {json.dumps(pyodide_version)};\n"
    ).encode("utf-8")
    require(
        read_bytes(PUBLIC_RUNTIME / "runtime-meta.mjs", "runtime metadata module")
        == expected_module,
        "runtime metadata module differs from current sources and metadata",
    )

    worker_text = read_bytes(
        PUBLIC_RUNTIME / "cncm-worker.mjs",
        "browser worker",
    ).decode("utf-8")
    require("BRIDGE_VERSION" in worker_text, "browser worker lacks bridge-version binding")
    require(
        "bridgeVersion !== BRIDGE_VERSION" in worker_text,
        "browser worker lacks runtime bridge-version handshake",
    )
    require(
        f'bridge_version: "{bridge_version}"' not in worker_text,
        "browser worker duplicated the bridge version instead of using metadata",
    )

    return {
        "valid": True,
        "runtime_archive_sha256": expected_archive_hash,
        "package_tree_sha256": package_tree_hash,
        "package_files": len(package_records),
        "fixtures": len(fixture_records),
        "math_fixtures": len(math_fixture_records),
        "source_spec_sha256": sha256_bytes(source_payload),
        "golden_manifest_sha256": sha256_bytes(golden_payload),
        "pyodide_version": pyodide_version,
    }


def main() -> int:
    try:
        summary = check_runtime()
    except Exception as exc:
        print(f"runtime check failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
