#!/usr/bin/env python3
"""Verify the source-bound Project Coherence publication-program package.

This verifier checks byte manifests, lead crosswalks, imported local claim IDs,
status boundaries, and the current hardened Gate 5 snapshot.  A PASS is a
structural/integration result only.  It does not close a gate, validate a
theorem or experiment, authorize publication, or grant product/canon/license/
disclosure authority.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_ROOT = (
    REPO_ROOT / "docs" / "working" / "project_coherence" / "publication"
)
INTEGRATION_ROOT = PUBLICATION_ROOT / "integration"


class VerificationError(RuntimeError):
    """Raised when a publication integration invariant fails."""


def fail(message: str) -> None:
    raise VerificationError(message)


def duplicate_safe_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=duplicate_safe_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot parse JSON {path.relative_to(REPO_ROOT)}: {exc}")
    if not isinstance(value, dict):
        fail(f"top-level JSON value is not an object: {path.relative_to(REPO_ROOT)}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def resolve_repo_path(raw: str) -> Path:
    if not isinstance(raw, str) or not raw:
        fail(f"invalid repository path value: {raw!r}")
    if "\\" in raw:
        fail(f"publication path is not POSIX-normalized: {raw}")
    candidate = (REPO_ROOT / raw).resolve()
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError:
        fail(f"publication path escapes repository: {raw}")
    return candidate


def require_unique(values: Iterable[str], label: str) -> list[str]:
    items = list(values)
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in items:
        if value in seen:
            duplicates.append(value)
        seen.add(value)
    if duplicates:
        fail(f"duplicate {label}: {sorted(set(duplicates))}")
    return items


def verify_publication_json_and_statuses() -> int:
    json_count = 0
    for path in sorted(PUBLICATION_ROOT.rglob("*.json")):
        data = load_json(path)
        json_count += 1
        if data.get("public_disclosure_authorized") is True:
            fail(f"public disclosure promoted in {path.relative_to(REPO_ROOT)}")
        if "canon_effect" in data and data["canon_effect"] != "NONE":
            fail(f"non-NONE canon effect in {path.relative_to(REPO_ROOT)}")
        if "product_claim_effect" in data and data["product_claim_effect"] != "NONE":
            fail(f"non-NONE product claim effect in {path.relative_to(REPO_ROOT)}")
        if "license_status" in data and data["license_status"] != "NOT LICENSED":
            fail(f"license status promoted in {path.relative_to(REPO_ROOT)}")
    return json_count


def verify_manifests() -> tuple[int, int]:
    manifest_count = 0
    artifact_total = 0
    for path in sorted(PUBLICATION_ROOT.rglob("*MANIFEST*.json")):
        data = load_json(path)
        artifacts = data.get("artifacts")
        if artifacts is None:
            continue
        if not isinstance(artifacts, list):
            fail(f"manifest artifacts is not a list: {path.relative_to(REPO_ROOT)}")
        declared = data.get("artifact_count")
        if declared != len(artifacts):
            fail(
                f"manifest count mismatch {path.relative_to(REPO_ROOT)}: "
                f"declared={declared!r} actual={len(artifacts)}"
            )
        listed_paths = require_unique(
            (item.get("path") for item in artifacts if isinstance(item, dict)),
            f"artifact paths in {path.relative_to(REPO_ROOT)}",
        )
        if len(listed_paths) != len(artifacts):
            fail(f"non-object artifact record in {path.relative_to(REPO_ROOT)}")
        manifest_relative = path.relative_to(REPO_ROOT).as_posix()
        if manifest_relative in listed_paths:
            fail(f"manifest self-hashes: {manifest_relative}")
        for item in artifacts:
            raw = item.get("path")
            target = resolve_repo_path(raw)
            if not target.is_file():
                fail(f"manifest artifact is missing: {raw}")
            expected_bytes = item.get("bytes")
            actual_bytes = target.stat().st_size
            if expected_bytes != actual_bytes:
                fail(
                    f"manifest byte mismatch {raw}: "
                    f"expected={expected_bytes!r} actual={actual_bytes}"
                )
            expected_hash = item.get("sha256")
            actual_hash = sha256(target)
            if expected_hash != actual_hash:
                fail(
                    f"manifest hash mismatch {raw}: "
                    f"expected={expected_hash!r} actual={actual_hash}"
                )
        manifest_count += 1
        artifact_total += len(artifacts)
    if manifest_count == 0:
        fail("no publication artifact manifests found")
    return manifest_count, artifact_total


def matrix_ids(matrix: dict[str, Any], path: str) -> list[str]:
    collection = matrix.get("records")
    if collection is None:
        collection = matrix.get("entries")
    if not isinstance(collection, list):
        fail(f"claim matrix has neither records nor entries list: {path}")
    ids: list[str] = []
    for item in collection:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            fail(f"claim matrix has invalid record: {path}")
        ids.append(item["id"])
    return require_unique(ids, f"claim IDs in {path}")


def verify_claim_registry() -> tuple[int, int, int]:
    path = INTEGRATION_ROOT / "PUBLICATION_CLAIM_REGISTRY_CROSSWALK_v0.1.json"
    registry = load_json(path)
    claim_sets = registry.get("local_claim_sets")
    if not isinstance(claim_sets, list) or not claim_sets:
        fail("lead claim registry has no local claim sets")

    lane_index: dict[str, set[str]] = {}
    all_ids: list[str] = []
    for item in claim_sets:
        if not isinstance(item, dict):
            fail("lead claim registry has a non-object lane record")
        lane = item.get("lane")
        raw_matrix = item.get("matrix_path")
        raw_manifest = item.get("manifest_path")
        declared_ids = item.get("local_ids")
        if not isinstance(lane, str) or not isinstance(declared_ids, list):
            fail("lead claim registry has an invalid lane or local_ids")
        matrix_path = resolve_repo_path(raw_matrix)
        manifest_path = resolve_repo_path(raw_manifest)
        if not matrix_path.is_file() or not manifest_path.is_file():
            fail(f"lead claim lane points to a missing matrix or manifest: {lane}")
        actual_ids = matrix_ids(load_json(matrix_path), raw_matrix)
        if item.get("local_record_count") != len(declared_ids):
            fail(f"lead claim lane count mismatch: {lane}")
        if declared_ids != actual_ids:
            fail(f"lead claim lane IDs do not exactly match matrix order: {lane}")
        lane_index[lane] = set(actual_ids)
        all_ids.extend(actual_ids)

    require_unique(all_ids, "imported local claim IDs")
    integrated = registry.get("integrated_summary", {})
    if integrated.get("imported_local_record_total") != len(all_ids):
        fail("lead integrated claim total does not match imported matrices")
    if integrated.get("imported_lanes") != len(claim_sets):
        fail("lead integrated lane total does not match local claim sets")
    if integrated.get("claims_promoted_by_integration") != 0:
        fail("lead claim registry promotes a claim")
    if integrated.get("claims_closed_by_integration") != 0:
        fail("lead claim registry closes a claim")

    crosswalks = registry.get("crosswalks")
    if not isinstance(crosswalks, list):
        fail("lead claim crosswalks is not a list")
    require_unique(
        (item.get("id") for item in crosswalks if isinstance(item, dict)),
        "crosswalk IDs",
    )
    for crosswalk in crosswalks:
        if not isinstance(crosswalk, dict):
            fail("lead claim crosswalk has a non-object record")
        members = crosswalk.get("members")
        if not isinstance(members, list) or not members:
            fail(f"crosswalk has no members: {crosswalk.get('id')}")
        for member in members:
            if not isinstance(member, dict):
                fail(f"crosswalk has invalid member: {crosswalk.get('id')}")
            lane = member.get("lane")
            local_id = member.get("local_id")
            if lane not in lane_index or local_id not in lane_index[lane]:
                fail(
                    f"crosswalk member does not resolve: "
                    f"{crosswalk.get('id')} -> {lane}|{local_id}"
                )
    return len(claim_sets), len(all_ids), len(crosswalks)


def verify_notation_crosswalk() -> int:
    path = INTEGRATION_ROOT / "CANONICAL_NOTATION_AND_TYPE_CROSSWALK_v0.1.json"
    data = load_json(path)
    records = data.get("records")
    if not isinstance(records, list):
        fail("notation crosswalk records is not a list")
    if data.get("record_count") != len(records):
        fail("notation record_count mismatch")
    require_unique(
        (item.get("id") for item in records if isinstance(item, dict)),
        "notation IDs",
    )
    for item in records:
        if not isinstance(item, dict):
            fail("notation crosswalk has a non-object record")
        refs = item.get("source_refs")
        if not isinstance(refs, list) or not refs:
            fail(f"notation record lacks source refs: {item.get('id')}")
        for raw in refs:
            if not resolve_repo_path(raw).is_file():
                fail(f"notation source is missing: {item.get('id')} -> {raw}")
    return len(records)


def verify_dependency_and_obligation_maps() -> tuple[int, int]:
    dependency_path = (
        INTEGRATION_ROOT / "PUBLICATION_DEPENDENCY_STATUS_AND_REVIEW_MAP_v0.1.json"
    )
    dependency = load_json(dependency_path)
    tracks = dependency.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        fail("dependency map has no tracks")
    require_unique(
        (item.get("track_id") for item in tracks if isinstance(item, dict)),
        "publication track IDs",
    )
    for item in tracks:
        if not isinstance(item, dict):
            fail("dependency map has a non-object track")
        if item.get("submission_eligible") is not False:
            fail(f"publication track is not fail-closed: {item.get('track_id')}")

    obligation_path = (
        INTEGRATION_ROOT / "UNRESOLVED_OBLIGATION_RECONCILIATION_v0.1.json"
    )
    obligations = load_json(obligation_path)
    clusters = obligations.get("dependency_clusters")
    if not isinstance(clusters, list) or not clusters:
        fail("obligation reconciliation has no dependency clusters")
    require_unique(
        (item.get("cluster_id") for item in clusters if isinstance(item, dict)),
        "obligation cluster IDs",
    )
    declared_clusters = obligations.get("current_counts", {}).get(
        "dependency_clusters"
    )
    if declared_clusters != len(clusters):
        fail("obligation cluster count mismatch")
    if (
        obligations.get("current_counts", {}).get(
            "local_or_review_items_closed_by_this_reconciliation"
        )
        != 0
    ):
        fail("obligation reconciliation closes an item")
    for source in obligations.get("source_ledgers", []):
        if not isinstance(source, dict):
            fail("obligation source ledger record is not an object")
        raw = source.get("path")
        if raw is not None and not resolve_repo_path(raw).is_file():
            fail(f"obligation source ledger is missing: {raw}")
    return len(tracks), len(clusters)


def verify_hardened_gate5_snapshot() -> int:
    path = INTEGRATION_ROOT / "GATE5_EVIDENCE_SNAPSHOT_CROSSWALK_v0.1.json"
    data = load_json(path)
    snapshots = data.get("snapshots")
    if not isinstance(snapshots, list):
        fail("Gate 5 snapshot crosswalk has no snapshots list")
    current = next(
        (
            item
            for item in snapshots
            if isinstance(item, dict)
            and item.get("snapshot_id") == "G5-SNAPSHOT-HARDENED-INTEGRATION"
        ),
        None,
    )
    if current is None:
        fail("hardened Gate 5 integration snapshot is missing")
    for key in (
        "gate5_manifest",
        "local_runner_lock",
        "raw_build_security_receipt",
        "gate5_verifier",
        "gate5_redteam",
    ):
        record = current.get(key)
        if not isinstance(record, dict):
            fail(f"hardened Gate 5 snapshot lacks {key}")
        target = resolve_repo_path(record.get("path"))
        if not target.is_file():
            fail(f"hardened Gate 5 snapshot target is missing: {key}")
        if target.stat().st_size != record.get("bytes"):
            fail(f"hardened Gate 5 snapshot byte mismatch: {key}")
        if sha256(target) != record.get("sha256"):
            fail(f"hardened Gate 5 snapshot hash mismatch: {key}")
    gate5_manifest = load_json(resolve_repo_path(current["gate5_manifest"]["path"]))
    artifact_count = gate5_manifest.get("artifact_count")
    if artifact_count != current["gate5_manifest"].get("artifact_count"):
        fail("hardened Gate 5 artifact count mismatch")
    return int(artifact_count)


def main() -> int:
    if not PUBLICATION_ROOT.is_dir():
        print(f"FAIL: publication root is missing: {PUBLICATION_ROOT}", file=sys.stderr)
        return 1
    try:
        json_count = verify_publication_json_and_statuses()
        manifest_count, artifact_total = verify_manifests()
        lane_count, claim_count, crosswalk_count = verify_claim_registry()
        notation_count = verify_notation_crosswalk()
        track_count, cluster_count = verify_dependency_and_obligation_maps()
        gate5_artifacts = verify_hardened_gate5_snapshot()
    except VerificationError as exc:
        print(f"Project Coherence publication program verification: FAIL\n  {exc}")
        return 1

    print("Project Coherence publication program structural verification: PASS")
    print(f"  publication JSON files: {json_count}")
    print(
        f"  non-self-hashing manifests: {manifest_count}; "
        f"bound publication artifacts: {artifact_total}"
    )
    print(
        f"  imported local claim/control records: {claim_count} "
        f"across {lane_count} lanes; crosswalks: {crosswalk_count}"
    )
    print(
        f"  notation/type records: {notation_count}; publication tracks: "
        f"{track_count}; obligation clusters: {cluster_count}"
    )
    print(f"  hardened Gate 5 snapshot artifacts: {gate5_artifacts}")
    print(
        "  status: DRAFT / OPEN / RING 4 / NOT LICENSED / HELD / "
        "NOT FROZEN"
    )
    print(
        "This PASS is structural only; it is not theorem admission, empirical "
        "validation, gate closure, publication approval, product readiness, "
        "canon, license, WORM, or disclosure authority."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
