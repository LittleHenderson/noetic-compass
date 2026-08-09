"""Portable current-byte checks for the host-local V1-V4 recovery boundary.

The authoritative recovery verifier also resolves the historical ``d9c18797``
Git tree.  That commit is intentionally not advertised by the remote used by
GitHub Actions, so this CI companion does not claim independent source-tree
verification.  It verifies every currently retained byte against the sealed
recovery manifest and preserves the exact negative classifications.  The full
source-tree proof remains a local Gate 5 verifier obligation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    ROOT
    / "docs/working/project_coherence/gate5/history/"
    "HISTORICAL_HARNESS_V1_V4_CURRENT_TREE_SHA256.json"
)
SOURCE_REVISION = "d9c1879762233855cd5974676b8179b1e4e75d16"
INVENTORY_SHA256 = (
    "361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f"
)


def _manifest() -> dict[str, object]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def test_portable_current_bytes_match_the_sealed_recovery_inventory() -> None:
    manifest = _manifest()
    assert manifest["source_revision"] == SOURCE_REVISION
    files = manifest["files"]
    assert isinstance(files, list)
    assert len(files) == 537

    paths: list[str] = []
    canonical_lines: list[bytes] = []
    total_bytes = 0
    for record in files:
        assert isinstance(record, dict)
        relative_path = str(record["path"])
        payload = (ROOT / relative_path).read_bytes()
        paths.append(relative_path)
        total_bytes += len(payload)
        assert len(payload) == record["byte_count"]
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert _git_blob_sha1(payload) == record["current_git_blob_sha1"]
        assert record["current_git_blob_sha1"] == record["source_git_blob_sha1"]
        assert record["exact_source_bytes"] is True
        canonical_lines.append(
            (
                f"{relative_path}\0{len(payload)}\0{record['sha256']}\n"
            ).encode("utf-8")
        )

    assert paths == sorted(paths)
    current = manifest["current_tree"]
    assert isinstance(current, dict)
    assert current["file_count"] == len(files)
    assert current["total_byte_count"] == total_bytes == 95_945_579
    assert current["exact_source_file_count"] == len(files)
    assert current["source_byte_mismatch_count"] == 0
    assert hashlib.sha256(b"".join(canonical_lines)).hexdigest() == INVENTORY_SHA256
    assert current["inventory_sha256"] == INVENTORY_SHA256


def test_portable_boundary_preserves_negative_status_and_missing_dependencies() -> None:
    manifest = _manifest()
    verification = manifest["frozen_binding_verification"]
    supplemental = manifest["supplemental_v1_worker_test_run"]
    assert isinstance(verification, dict)
    assert isinstance(supplemental, dict)
    assert verification["terminal_binding_classification"] == (
        "HISTORICALLY_INCONSISTENT / NOT_INDEPENDENTLY_BYTE_CLOSED / FAIL_CLOSED"
    )
    assert supplemental["classification"] == "HISTORICAL_FIXTURE_DEPENDENCIES_ABSENT"
    assert supplemental["model_loads"] == 0
    assert supplemental["network_calls"] == 0
    assert supplemental["live_worker_calls"] == 0
    assert supplemental["paid_compute_calls"] == 0
    assert manifest["claim_and_gate_status_change"] == "NONE"

    absent = (
        "noetic-compass-scaffold/noetic-compass/api/services/"
        "cas_harness_research_intervention_auditor.py",
        "noetic-compass-scaffold/noetic-compass/scenarios/"
        "research_intervention_plan_v0.json",
        "noetic-compass-scaffold/noetic-compass/scenarios/"
        "research_intervention_synthetic_fixture_v0.json",
        "noetic-compass-scaffold/noetic-compass/tests/"
        "test_cas_harness_research_intervention_auditor.py",
        "docs/working/cas_harness_research_intervention_worker_v0.md",
    )
    for relative_path in absent:
        assert not (ROOT / relative_path).exists()

