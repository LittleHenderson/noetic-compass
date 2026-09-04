"""Build the deterministic browser runtime and copy its pinned local assets."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


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


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def zip_entry(name: str, payload: bytes) -> ZipInfo:
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
    if len(matches) != 1 or not matches[0]:
        raise RuntimeError("browser bridge must declare exactly one nonempty _BRIDGE_VERSION")
    return matches[0]


def main() -> None:
    bridge_version = bridge_version_from_source()
    for directory in (
        PUBLIC_RUNTIME,
        PUBLIC_FIXTURES,
        PUBLIC_MATH_FIXTURES,
        PUBLIC_PYODIDE,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    actual_cncm_files = tuple(sorted(path.name for path in CNCM_ROOT.glob("*.py")))
    if actual_cncm_files != EXPECTED_CNCM_FILES:
        raise RuntimeError(
            f"unexpected CNCM package surface: {actual_cncm_files!r}"
        )

    package_records = []
    tree_lines = []
    archive_path = PUBLIC_RUNTIME / "cncm-runtime.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for filename in EXPECTED_CNCM_FILES:
            source = CNCM_ROOT / filename
            payload = source.read_bytes()
            relative = f"cncm/{filename}"
            file_hash = sha256_bytes(payload)
            archive.writestr(zip_entry(relative, payload), payload)
            package_records.append({
                "path": relative,
                "bytes": len(payload),
                "sha256": file_hash,
            })
            tree_lines.append(f"{relative} {len(payload)} {file_hash}\n")

        bridge_payload = BRIDGE_SOURCE.read_bytes()
        archive.writestr(
            zip_entry("cncm_browser_bridge.py", bridge_payload),
            bridge_payload,
        )

    fixture_records = []
    for name in EXPECTED_FIXTURES:
        source = FIXTURES_ROOT / name / "problem.json"
        if not source.is_file():
            raise RuntimeError(f"missing fixture: {source}")
        destination = PUBLIC_FIXTURES / f"{name}.json"
        shutil.copyfile(source, destination)
        fixture_records.append({
            "name": name,
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
        })

    math_sources = sorted((FIXTURES_ROOT / "math").glob("*/case.json"))
    math_categories = tuple(path.parent.name for path in math_sources)
    if math_categories != tuple(sorted(EXPECTED_MATH_STATUS)):
        raise RuntimeError(
            f"unexpected math fixture surface: {math_categories!r}"
        )
    math_fixture_records = []
    for source in math_sources:
        category = source.parent.name
        document = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise RuntimeError(f"math fixture must be an object: {source}")
        if document.get("schema_version") != "cncm.math-fixture/0.1":
            raise RuntimeError(f"math fixture schema mismatch: {source}")
        if document.get("category") != category:
            raise RuntimeError(f"math fixture category mismatch: {source}")
        if document.get("runtime_status") != EXPECTED_MATH_STATUS[category]:
            raise RuntimeError(f"math fixture runtime status mismatch: {source}")
        destination = PUBLIC_MATH_FIXTURES / f"{category}.json"
        shutil.copyfile(source, destination)
        math_fixture_records.append({
            "name": category,
            "path": f"/fixtures/math/{category}.json",
            "fixture_id": document["fixture_id"],
            "operation": document["operation"],
            "runtime_status": document["runtime_status"],
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
        })

    pyodide_package_json = json.loads(
        (PYODIDE_PACKAGE / "package.json").read_text(encoding="utf-8")
    )
    for name in PYODIDE_ASSETS:
        source = PYODIDE_PACKAGE / name
        if not source.is_file():
            raise RuntimeError(f"missing pinned Pyodide asset: {source}")
        shutil.copyfile(source, PUBLIC_PYODIDE / name)

    archive_hash = sha256_file(archive_path)
    package_tree_hash = sha256_bytes("".join(tree_lines).encode("utf-8"))
    metadata = {
        "schema_version": "cncm.browser-runtime/0.7",
        "runtime_version": "0.1.0",
        "bridge_version": bridge_version,
        "conversation_protocol_version": "0.2.0",
        "capabilities": [
            "problem_lab",
            "controlled_english_conversation",
            "exact_math",
            "verified_language_apprenticeship_local",
            "verified_cognitive_apprenticeship_local",
        ],
        "pyodide_version": pyodide_package_json["version"],
        "runtime_archive": {
            "path": "/runtime/cncm-runtime.zip",
            "bytes": archive_path.stat().st_size,
            "sha256": archive_hash,
        },
        "package_tree_sha256": package_tree_hash,
        "package_files": package_records,
        "fixtures": fixture_records,
        "math_fixtures": math_fixture_records,
        "source_spec": {
            "path": "cas_reasoner.txt",
            "bytes": SOURCE_SPEC.stat().st_size,
            "sha256": sha256_file(SOURCE_SPEC),
        },
        "golden_manifest_sha256": sha256_file(GOLDEN_MANIFEST),
    }
    (PUBLIC_RUNTIME / "runtime-meta.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (PUBLIC_RUNTIME / "runtime-meta.mjs").write_text(
        "// Generated by scripts/build-runtime.py.\n"
        f"export const EXPECTED_RUNTIME_SHA256 = {json.dumps(archive_hash)};\n"
        f"export const EXPECTED_RUNTIME_BYTES = {archive_path.stat().st_size};\n"
        f"export const EXPECTED_RUNTIME_VERSION = \"0.1.0\";\n"
        f"export const BRIDGE_VERSION = {json.dumps(bridge_version)};\n"
        f"export const CONVERSATION_PROTOCOL_VERSION = \"0.2.0\";\n"
        f"export const PACKAGE_TREE_SHA256 = {json.dumps(package_tree_hash)};\n"
        f"export const SOURCE_SPEC_SHA256 = {json.dumps(sha256_file(SOURCE_SPEC))};\n"
        f"export const PYODIDE_VERSION = {json.dumps(pyodide_package_json['version'])};\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
