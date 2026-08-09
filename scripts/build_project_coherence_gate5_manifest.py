#!/usr/bin/env python3
"""Build the non-self-hashing Project Coherence Gate 5 manifest.

The verifier independently recomputes every path, byte count, digest, closure
surface, status, and test receipt.  This builder is only the deterministic
mechanical producer; it is not an admission, signature, or authority.
"""

from __future__ import annotations

import sys

if not sys.flags.isolated:
    raise SystemExit(
        "Gate 5 manifest generation requires isolated Python; run "
        "`python -I -B scripts/build_project_coherence_gate5_manifest.py`."
    )

import importlib.util
import json
from pathlib import Path

_VERIFIER_PATH = Path(__file__).resolve().with_name("verify_project_coherence_gate5.py")
_SPEC = importlib.util.spec_from_file_location("gate5_manifest_verifier", _VERIFIER_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load the Gate 5 verifier by exact file path")
_VERIFIER = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _VERIFIER
_SPEC.loader.exec_module(_VERIFIER)

EXACT_API_LAUNCHER_SURFACE = _VERIFIER.EXACT_API_LAUNCHER_SURFACE
EXACT_ALL_FILE_SURFACE_DIRS = _VERIFIER.EXACT_ALL_FILE_SURFACE_DIRS
EXACT_DATA_SURFACES = _VERIFIER.EXACT_DATA_SURFACES
MANIFEST_PATH = _VERIFIER.MANIFEST_PATH
MODEL_BINDING = _VERIFIER.MODEL_BINDING
REQUIRED_CONTROL_ARTIFACTS = _VERIFIER.REQUIRED_CONTROL_ARTIFACTS
REQUIRED_BOUNDARY_TEXT = _VERIFIER.REQUIRED_BOUNDARY_TEXT
REQUIRED_OPEN_BOUNDARY_IDS = _VERIFIER.REQUIRED_OPEN_BOUNDARY_IDS
REQUIRED_TEST_SUITES = _VERIFIER.REQUIRED_TEST_SUITES
ROOT = _VERIFIER.ROOT
FILESYSTEM_ANCHOR = _VERIFIER.FILESYSTEM_ANCHOR
CURRENT_SECURITY_HOLD = _VERIFIER.CURRENT_SECURITY_HOLD
TEST_ID_CANONICALIZATION = _VERIFIER.TEST_ID_CANONICALIZATION
artifact_role = _VERIFIER.artifact_role
collect_api_runtime_surface = _VERIFIER.collect_api_runtime_surface
collect_gate5_control_surface = _VERIFIER.collect_gate5_control_surface
collect_pytest_environment_surface = _VERIFIER.collect_pytest_environment_surface
observe_regular_file = _VERIFIER.observe_regular_file


def _surface_files() -> set[str]:
    paths = (
        set(REQUIRED_CONTROL_ARTIFACTS)
        | set(EXACT_API_LAUNCHER_SURFACE)
        | collect_api_runtime_surface()
        | collect_gate5_control_surface()
        | collect_pytest_environment_surface()
    )
    for directory in EXACT_ALL_FILE_SURFACE_DIRS:
        root = ROOT / directory
        paths.update(
            path.relative_to(ROOT).as_posix()
            for path in root.rglob("*")
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
        observation = observe_regular_file(path, anchor=FILESYSTEM_ANCHOR)
        artifact_records.append(
            {
                "path": raw_path,
                "sha256": observation.sha256,
                "bytes": observation.byte_count,
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
            or not isinstance(receipt["expected_setup_skipped_nodeids"], list)
            or not isinstance(receipt["pytest_plugins"], list)
            or not isinstance(receipt["repo_import_roots"], list)
            or not all(
                isinstance(plugin, str) and plugin
                for plugin in receipt["pytest_plugins"]
            )
            or not all(
                isinstance(path, str) and path
                for path in receipt["repo_import_roots"]
            )
            or len(receipt["expected_setup_skipped_nodeids"])
            != len(set(receipt["expected_setup_skipped_nodeids"]))
            or not all(
                isinstance(nodeid, str) and nodeid
                for nodeid in receipt["expected_setup_skipped_nodeids"]
            )
        ):
            raise RuntimeError(f"test receipt is not frozen: {name}")
        test_suites.append(
            {
                "name": name,
                "working_directory": receipt["working_directory"],
                "targets": receipt["targets"],
                "pytest_plugins": receipt["pytest_plugins"],
                "repo_import_roots": receipt["repo_import_roots"],
                "expected_tests": receipt["expected_tests"],
                "expected_subtests": receipt["expected_subtests"],
                "expected_test_ids_sha256": receipt[
                    "expected_test_ids_sha256"
                ],
                "expected_setup_skipped_nodeids": receipt[
                    "expected_setup_skipped_nodeids"
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
            **CURRENT_SECURITY_HOLD,
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
