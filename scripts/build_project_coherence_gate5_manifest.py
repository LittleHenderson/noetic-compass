#!/usr/bin/env python3
"""Build the non-self-hashing Project Coherence Gate 5 manifest.

The verifier independently recomputes every path, byte count, digest, closure
surface, status, and test receipt.  This builder is only the deterministic
mechanical producer; it is not an admission, signature, or authority.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verify_project_coherence_gate5 import (
    EXACT_DATA_SURFACES,
    EXACT_PYTHON_SURFACE_DIRS,
    MANIFEST_PATH,
    MODEL_BINDING,
    REQUIRED_CONTROL_ARTIFACTS,
    REQUIRED_BOUNDARY_TEXT,
    REQUIRED_OPEN_BOUNDARY_IDS,
    REQUIRED_TEST_SUITES,
    ROOT,
    SECURITY_HOLD,
    TEST_ID_CANONICALIZATION,
    artifact_role,
    collect_gate5_control_surface,
    collect_pytest_environment_surface,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _surface_files() -> set[str]:
    paths = (
        set(REQUIRED_CONTROL_ARTIFACTS)
        | collect_gate5_control_surface()
        | collect_pytest_environment_surface()
    )
    for directory in EXACT_PYTHON_SURFACE_DIRS:
        root = ROOT / directory
        paths.update(
            path.relative_to(ROOT).as_posix()
            for path in root.rglob("*.py")
            if path.is_file() and "__pycache__" not in path.parts
        )
    for directory, pattern in EXACT_DATA_SURFACES:
        root = ROOT / directory
        paths.update(
            path.relative_to(ROOT).as_posix()
            for path in root.rglob(pattern)
            if path.is_file() and "__pycache__" not in path.parts
        )
    paths.discard(MANIFEST_PATH.relative_to(ROOT).as_posix())
    return paths


def build_manifest() -> dict[str, object]:
    artifact_records: list[dict[str, object]] = []
    for raw_path in sorted(_surface_files()):
        path = ROOT / raw_path
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"required regular artifact is missing: {raw_path}")
        artifact_records.append(
            {
                "path": raw_path,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
                "role": artifact_role(raw_path),
            }
        )

    if set(REQUIRED_BOUNDARY_TEXT) != REQUIRED_OPEN_BOUNDARY_IDS:
        raise RuntimeError("builder boundary text differs from verifier boundary IDs")

    test_suites: list[dict[str, object]] = []
    for name, receipt in REQUIRED_TEST_SUITES.items():
        if (
            type(receipt["expected_tests"]) is not int
            or type(receipt["expected_subtests"]) is not int
            or not isinstance(receipt["expected_test_ids_sha256"], str)
            or not isinstance(receipt["pytest_plugins"], list)
            or not all(
                isinstance(plugin, str) and plugin
                for plugin in receipt["pytest_plugins"]
            )
        ):
            raise RuntimeError(f"test receipt is not frozen: {name}")
        test_suites.append(
            {
                "name": name,
                "working_directory": receipt["working_directory"],
                "targets": receipt["targets"],
                "pytest_plugins": receipt["pytest_plugins"],
                "expected_tests": receipt["expected_tests"],
                "expected_subtests": receipt["expected_subtests"],
                "expected_test_ids_sha256": receipt[
                    "expected_test_ids_sha256"
                ],
                "test_id_canonicalization": TEST_ID_CANONICALIZATION,
            }
        )

    return {
        "schema_version": "project_coherence.gate5_artifact_manifest.v0.1",
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
        "manifest_self_hash": None,
        "generated_by": "scripts/build_project_coherence_gate5_manifest.py",
        "artifact_count": len(artifact_records),
        "artifacts": artifact_records,
        "required_open_boundaries": [
            f"[{boundary_id}] {REQUIRED_BOUNDARY_TEXT[boundary_id]}"
            for boundary_id in sorted(REQUIRED_BOUNDARY_TEXT)
        ],
        "model_binding": dict(MODEL_BINDING),
        "dependency_security_hold": {
            **SECURITY_HOLD,
            "container_digest_bound": False,
            "patched_environment_revalidated": False,
        },
        "test_suites": test_suites,
    }


def main() -> int:
    manifest = build_manifest()
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(payload, encoding="utf-8", newline="\n")
    print(
        f"wrote {MANIFEST_PATH.relative_to(ROOT).as_posix()} with "
        f"{manifest['artifact_count']} artifacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
