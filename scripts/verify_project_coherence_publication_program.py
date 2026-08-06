#!/usr/bin/env python3
"""Verify the source-bound Project Coherence publication-program package.

This verifier checks byte manifests, lead crosswalks, imported local claim IDs,
status boundaries, preserved historical Gate 5 snapshots, and the current
Gate 5 successor snapshot.  A PASS is a
structural/integration result only.  It does not close a gate, validate a
theorem or experiment, authorize publication, or grant product/canon/license/
disclosure authority.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
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


def git_blob_identity(raw: str) -> tuple[str, int, str]:
    """Return the HEAD blob OID, byte count, and content SHA-256 for a path."""
    resolve_repo_path(raw)
    revision = f"HEAD:{raw}"
    oid_result = subprocess.run(
        ["git", "rev-parse", revision],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )
    if oid_result.returncode != 0:
        fail(f"cannot resolve Git blob for {raw}: {oid_result.stderr.strip()}")
    oid = oid_result.stdout.strip()
    blob_result = subprocess.run(
        ["git", "cat-file", "blob", oid],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    if blob_result.returncode != 0:
        fail(f"cannot read Git blob for {raw}")
    blob = blob_result.stdout
    return oid, len(blob), hashlib.sha256(blob).hexdigest().upper()


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


def verify_gate5_snapshot_crosswalk() -> int:
    path = INTEGRATION_ROOT / "GATE5_EVIDENCE_SNAPSHOT_CROSSWALK_v0.1.json"
    data = load_json(path)
    snapshots = data.get("snapshots")
    if not isinstance(snapshots, list):
        fail("Gate 5 snapshot crosswalk has no snapshots list")
    expected_snapshot_ids = [
        "G5-SNAPSHOT-HARNESS-LANE-BASE",
        "G5-SNAPSHOT-HARDENED-INTEGRATION",
        "G5-SNAPSHOT-WORKER-PROTOCOL-SUCCESSOR",
    ]
    actual_snapshot_ids = [
        item.get("snapshot_id") for item in snapshots if isinstance(item, dict)
    ]
    if actual_snapshot_ids != expected_snapshot_ids:
        fail("Gate 5 snapshot IDs or historical order changed")
    historical_expectations = {
        "G5-SNAPSHOT-HARNESS-LANE-BASE": (
            325,
            "5C73F203B4EA7D95B89C3BBB730FFCAE571EECC26E8BA2AF3ABC4A994635B333",
        ),
        "G5-SNAPSHOT-HARDENED-INTEGRATION": (
            340,
            "AF263573DAB68D814A09D75CFEBB2ECDD62B08491BD2D1D66C7D5332F682A72A",
        ),
    }
    for snapshot_id, (artifact_count, manifest_sha256) in historical_expectations.items():
        historical = next(
            item for item in snapshots if item.get("snapshot_id") == snapshot_id
        )
        manifest_record = historical.get("gate5_manifest")
        if not isinstance(manifest_record, dict):
            fail(f"historical Gate 5 snapshot lacks manifest: {snapshot_id}")
        declared_count = manifest_record.get("artifact_count")
        declared_hash = manifest_record.get(
            "sha256_at_snapshot", manifest_record.get("sha256")
        )
        if (declared_count, declared_hash) != (artifact_count, manifest_sha256):
            fail(f"historical Gate 5 snapshot was rewritten: {snapshot_id}")
    current_snapshot_id = data.get("current_snapshot_id")
    if current_snapshot_id != "G5-SNAPSHOT-WORKER-PROTOCOL-SUCCESSOR":
        fail("current Gate 5 successor snapshot pointer is invalid")
    current = next(
        (
            item
            for item in snapshots
            if isinstance(item, dict)
            and item.get("snapshot_id") == current_snapshot_id
        ),
        None,
    )
    if current is None:
        fail("current Gate 5 successor snapshot is missing")
    if current.get("source_commit") != "d24721afe18e05442f3c691f02dcf1608244f0e9":
        fail("current Gate 5 successor source commit is not frozen")
    for key in (
        "gate5_manifest",
        "local_runner_lock",
        "raw_build_security_receipt",
        "gate5_verifier",
        "gate5_redteam",
    ):
        record = current.get(key)
        if not isinstance(record, dict):
            fail(f"current Gate 5 successor snapshot lacks {key}")
        target = resolve_repo_path(record.get("path"))
        if not target.is_file():
            fail(f"current Gate 5 successor snapshot target is missing: {key}")
        if target.stat().st_size != record.get("bytes"):
            fail(f"current Gate 5 successor snapshot byte mismatch: {key}")
        if sha256(target) != record.get("sha256"):
            fail(f"current Gate 5 successor snapshot hash mismatch: {key}")
    gate5_manifest = load_json(resolve_repo_path(current["gate5_manifest"]["path"]))
    artifact_count = gate5_manifest.get("artifact_count")
    if artifact_count != current["gate5_manifest"].get("artifact_count"):
        fail("current Gate 5 successor artifact count mismatch")
    replay = data.get("final_integrated_replay")
    if not isinstance(replay, dict) or replay.get("commit") != (
        "d24721afe18e05442f3c691f02dcf1608244f0e9"
    ):
        fail("successor replay is not bound to the frozen Gate 5 candidate")
    if replay.get("execution_order") != [
        "GATE5",
        "PUBLICATION_PROGRAM",
        "GATE1",
        "GATE4",
    ]:
        fail("final integrated replay order does not preserve Gate 5 isolation")
    results = replay.get("results")
    if not isinstance(results, dict) or set(results) != {
        "gate5",
        "publication_program",
        "gate1",
        "gate4",
    }:
        fail("final integrated replay results are incomplete")
    if any(result.get("result") != "PASS" for result in results.values()):
        fail("final integrated replay contains a non-PASS candidate result")
    if results["gate5"].get("artifact_count") != 348:
        fail("final integrated replay Gate 5 artifact count mismatch")
    if results["publication_program"].get("bound_publication_artifacts") != 71:
        fail("final integrated replay publication artifact count mismatch")
    if results["gate1"].get("artifact_count") != 23:
        fail("final integrated replay Gate 1 artifact count mismatch")
    if results["gate4"].get("artifact_count") != 54:
        fail("final integrated replay Gate 4 artifact count mismatch")
    return int(artifact_count)


def verify_memristive_source_and_evidence_controls(
    mem_root: Path, mem_ids: list[str]
) -> int:
    """Verify source-snapshot, evidence-resolution, and hash-domain controls."""
    crosswalk = load_json(
        INTEGRATION_ROOT / "MEMRISTIVE_SOURCE_SNAPSHOT_CROSSWALK_v0.1.json"
    )
    controls = crosswalk.get("controls")
    if not isinstance(controls, list) or crosswalk.get("control_count") != 3:
        fail("memristive source-snapshot crosswalk does not contain three controls")
    controls_by_id = {
        item.get("control_id"): item for item in controls if isinstance(item, dict)
    }
    expected_control_ids = {
        "PUB-MEM-SNAP-001",
        "PUB-MEM-SNAP-002",
        "PUB-MEM-SNAP-003",
    }
    if set(controls_by_id) != expected_control_ids:
        fail("memristive source-snapshot control IDs do not resolve exactly")
    if crosswalk.get("claim_promotion") != "NONE":
        fail("memristive source reconciliation promotes a claim")

    historical = controls_by_id["PUB-MEM-SNAP-001"]
    active = controls_by_id["PUB-MEM-SNAP-002"]
    eol = controls_by_id["PUB-MEM-SNAP-003"]
    historical_commit = "56c43caca7e61aea03254ffdc5484ecdf35bcdbe"
    active_commit = "e4ccfe309d4f8519fccd8cd4c3a5fd52de02a0a4"
    if historical.get("commit") != historical_commit:
        fail("memristive historical authoring snapshot commit changed")
    if active.get("commit") != active_commit:
        fail("memristive active integration snapshot commit changed")

    historical_items = [historical.get("manifest"), *historical.get("artifacts", [])]
    active_items = [active.get("manifest"), *active.get("artifacts", [])]
    if any(not isinstance(item, dict) for item in historical_items + active_items):
        fail("memristive source-snapshot artifact record is invalid")
    historical_by_path = {item["path"]: item for item in historical_items}
    active_by_path = {item["path"]: item for item in active_items}
    if set(historical_by_path) != set(active_by_path) or len(active_by_path) != 8:
        fail("memristive historical and active engineering source sets differ")
    for raw, item in active_by_path.items():
        target = resolve_repo_path(raw)
        if target.stat().st_size != item.get("bytes") or sha256(target) != item.get(
            "sha256"
        ):
            fail(f"active memristive engineering source identity mismatch: {raw}")

    citation = load_json(
        mem_root / "MEMRISTIVE_SUPPLEMENT_CITATION_LEDGER_v0.1.json"
    )
    if citation.get("integration_source_snapshot_commit") != active_commit:
        fail("memristive citation ledger lacks active engineering snapshot")
    external = citation.get("external_primary_sources")
    internal = citation.get("internal_source_citations")
    if not isinstance(external, list) or not isinstance(internal, list):
        fail("memristive citation ledger collections are invalid")
    external_by_id = {item.get("id"): item for item in external if isinstance(item, dict)}
    internal_by_id = {item.get("id"): item for item in internal if isinstance(item, dict)}
    e11 = external_by_id.get("E11", {})
    exact_e11 = {
        "title": "Steering Language Models With Activation Engineering",
        "container": "arXiv:2308.10248v5",
        "url": "https://arxiv.org/abs/2308.10248v5",
        "version": "v5",
        "last_revised": "2024-10-10",
    }
    if any(e11.get(key) != value for key, value in exact_e11.items()):
        fail("memristive citation E11 is not the exact arXiv v5 record")

    matrix = load_json(
        mem_root / "MEMRISTIVE_SUPPLEMENT_THEOREM_CLAIM_TYPE_MATRIX_v0.1.json"
    )
    matrix_entries = matrix.get("entries")
    if not isinstance(matrix_entries, list):
        fail("memristive claim/type matrix entries are invalid")
    canonical_local_refs = set(mem_ids) | set(external_by_id) | set(internal_by_id)
    for entry in matrix_entries:
        if not isinstance(entry, dict):
            fail("memristive claim/type matrix contains an invalid entry")
        evidence_texts: list[str] = []
        for raw in entry.get("evidence_refs", []):
            target = resolve_repo_path(raw)
            if not target.is_file():
                fail(f"memristive matrix evidence path is missing: {raw}")
            try:
                evidence_texts.append(target.read_text(encoding="utf-8"))
            except (OSError, UnicodeError) as exc:
                fail(f"cannot read memristive matrix evidence path {raw}: {exc}")
        for source_ref in entry.get("source_refs", []):
            if source_ref in canonical_local_refs:
                continue
            if not any(source_ref in text for text in evidence_texts):
                fail(
                    f"memristive matrix source reference lacks direct evidence: "
                    f"{entry.get('id')} -> {source_ref}"
                )
    for source_id in ("S6", "S7", "S8", "S9", "S10", "S11", "S12"):
        record = internal_by_id.get(source_id)
        if not isinstance(record, dict):
            fail(f"memristive citation ledger lacks {source_id}")
        raw = record.get("path")
        active_item = active_by_path.get(raw)
        historical_item = historical_by_path.get(raw)
        if active_item is None or historical_item is None:
            fail(f"memristive citation {source_id} does not resolve to both snapshots")
        if (
            record.get("source_snapshot_commit") != active_commit
            or record.get("bytes") != active_item.get("bytes")
            or record.get("sha256") != active_item.get("sha256")
        ):
            fail(f"memristive citation {source_id} active identity mismatch")
        old = record.get("historical_authoring_snapshot")
        if not isinstance(old, dict) or (
            old.get("commit") != historical_commit
            or old.get("bytes") != historical_item.get("bytes")
            or old.get("sha256") != historical_item.get("sha256")
        ):
            fail(f"memristive citation {source_id} historical identity mismatch")

    inventory = load_json(
        mem_root / "MEMRISTIVE_SUPPLEMENT_SOURCE_INVENTORY_v0.1.json"
    )
    if inventory.get("integration_source_snapshot_commit") != active_commit:
        fail("memristive source inventory lacks active engineering snapshot")
    inventory_sources = inventory.get("key_repository_sources")
    if not isinstance(inventory_sources, list):
        fail("memristive key repository source inventory is invalid")
    inventory_by_path = {
        item.get("path"): item for item in inventory_sources if isinstance(item, dict)
    }
    for raw, active_item in active_by_path.items():
        if raw.endswith("WAVE1_ENGINEERING_ARTIFACT_MANIFEST_v0.1.json"):
            continue
        record = inventory_by_path.get(raw)
        if not isinstance(record, dict):
            fail(f"memristive source inventory lacks active engineering file: {raw}")
        if record.get("bytes") != active_item.get("bytes") or record.get(
            "sha256"
        ) != active_item.get("sha256"):
            fail(f"memristive inventory active identity mismatch: {raw}")
        old = record.get("historical_authoring_snapshot")
        old_item = historical_by_path[raw]
        if not isinstance(old, dict) or (
            old.get("bytes") != old_item.get("bytes")
            or old.get("sha256") != old_item.get("sha256")
        ):
            fail(f"memristive inventory historical identity mismatch: {raw}")

    evidence = load_json(mem_root / "MEMRISTIVE_SUPPLEMENT_EVIDENCE_MAP_v0.1.json")
    anchors = evidence.get("bound_source_anchors")
    clusters = evidence.get("evidence_clusters")
    if not isinstance(anchors, list) or evidence.get("bound_source_anchor_count") != 16:
        fail("memristive evidence map does not bind 16 source anchors")
    if not isinstance(clusters, list) or evidence.get("evidence_cluster_count") != 15:
        fail("memristive evidence map does not contain 15 clusters")
    anchor_by_id = {item.get("id"): item for item in anchors if isinstance(item, dict)}
    if len(anchor_by_id) != 16:
        fail("memristive evidence anchor IDs are invalid or duplicated")
    receipt_ids: set[str] = set()
    for receipt_key in ("current_local_gate4_receipt", "current_local_gate5_receipt"):
        receipt = evidence.get(receipt_key)
        if not isinstance(receipt, dict) or not isinstance(receipt.get("id"), str):
            fail(f"memristive evidence map lacks {receipt_key}")
        receipt_ids.add(receipt["id"])
    for anchor_id in ("EA-SRC-006", "EA-SRC-007"):
        record = anchor_by_id.get(anchor_id)
        if not isinstance(record, dict):
            fail(f"memristive evidence map lacks {anchor_id}")
        raw = record.get("path")
        active_item = active_by_path.get(raw)
        historical_item = historical_by_path.get(raw)
        old = record.get("historical_authoring_snapshot")
        if (
            active_item is None
            or historical_item is None
            or record.get("source_snapshot_commit") != active_commit
            or record.get("bytes") != active_item.get("bytes")
            or record.get("sha256") != active_item.get("sha256")
            or not isinstance(old, dict)
            or old.get("commit") != historical_commit
            or old.get("bytes") != historical_item.get("bytes")
            or old.get("sha256") != historical_item.get("sha256")
        ):
            fail(f"memristive evidence snapshot reconciliation mismatch: {anchor_id}")
    resolved_matrix_ids: set[str] = set()
    for cluster in clusters:
        if not isinstance(cluster, dict):
            fail("memristive evidence map has an invalid cluster")
        for source_ref in cluster.get("source_refs", []):
            if source_ref not in anchor_by_id and source_ref not in receipt_ids:
                fail(f"memristive evidence source reference does not resolve: {source_ref}")
        citation_refs = cluster.get("citation_refs", [])
        if "EC1" in cluster.get("evidence_classes", []) and not citation_refs:
            fail(f"EC1 evidence cluster lacks citations: {cluster.get('id')}")
        for citation_ref in citation_refs:
            if citation_ref not in external_by_id:
                fail(
                    f"memristive external citation reference does not resolve: "
                    f"{citation_ref}"
                )
        for matrix_ref in cluster.get("matrix_entry_refs", []):
            if matrix_ref not in mem_ids:
                fail(f"memristive matrix evidence reference does not resolve: {matrix_ref}")
            resolved_matrix_ids.add(matrix_ref)
    if resolved_matrix_ids != set(mem_ids):
        missing = sorted(set(mem_ids) - resolved_matrix_ids)
        fail(f"memristive matrix entries lack evidence-cluster resolution: {missing}")

    eol_records = eol.get("records")
    if not isinstance(eol_records, list) or len(eol_records) != 3:
        fail("memristive EOL/hash-domain control does not contain three records")
    citation_by_path = {
        item.get("path"): item
        for item in internal
        if isinstance(item, dict) and item.get("id") in {"S25", "S26", "S27"}
    }
    anchors_by_path = {item.get("path"): item for item in anchors if isinstance(item, dict)}
    for expected in eol_records:
        raw = expected.get("path")
        target = resolve_repo_path(raw)
        checkout_fields = (
            expected.get("observed_checkout_bytes"),
            expected.get("observed_checkout_sha256"),
        )
        if checkout_fields != (target.stat().st_size, sha256(target)):
            fail(f"memristive checkout-byte identity mismatch: {raw}")
        actual_blob = git_blob_identity(raw)
        expected_blob = (
            expected.get("git_blob_oid"),
            expected.get("git_blob_bytes"),
            expected.get("git_blob_content_sha256"),
        )
        if actual_blob != expected_blob:
            fail(f"memristive Git-blob identity mismatch: {raw}")
        for record in (
            citation_by_path.get(raw),
            inventory_by_path.get(raw),
            anchors_by_path.get(raw),
        ):
            if not isinstance(record, dict):
                fail(f"memristive dual-domain source record is missing: {raw}")
            recorded = (
                record.get("bytes"),
                record.get("sha256"),
                record.get("git_blob_oid"),
                record.get("git_blob_bytes"),
                record.get("git_blob_sha256"),
            )
            expected_recorded = (
                checkout_fields[0],
                checkout_fields[1],
                expected_blob[0],
                expected_blob[1],
                expected_blob[2],
            )
            if recorded != expected_recorded:
                fail(f"memristive dual-domain record mismatch: {raw}")
    return len(anchors)


def verify_wave2_completion_packages() -> tuple[int, int, int, int]:
    acceptance_path = (
        PUBLICATION_ROOT
        / "wave2"
        / "adversarial_review"
        / "lead_corrections"
        / "FINDING_DISPOSITION_MATRIX_v0.1.json"
    )
    acceptance = load_json(acceptance_path)
    entries = acceptance.get("entries")
    if not isinstance(entries, list) or acceptance.get("entry_count") != len(entries):
        fail("lead-correction acceptance entry count mismatch")
    if acceptance.get("reviewed_head") != (
        "f91e622d30ce83b77cbbff8b947d9b125e51ff54"
    ):
        fail("lead-correction acceptance is not bound to the final corrected head")
    dispositions = acceptance.get("disposition_counts")
    expected_dispositions = {
        "ACCEPTED_AS_TEXT_CORRECTION": 13,
        "PARTIAL_RETAIN_OPEN": 0,
        "FAILED": 0,
    }
    if dispositions != expected_dispositions:
        fail("lead-correction acceptance disposition counts are not 13/0/0")
    if any(item.get("disposition") != "ACCEPTED_AS_TEXT_CORRECTION" for item in entries):
        fail("lead-correction acceptance contains a nonaccepted text disposition")

    mem_root = (
        PUBLICATION_ROOT
        / "wave2"
        / "memristive_context_lacunarity_injection_steering"
    )
    mem_manifest = load_json(
        mem_root / "MEMRISTIVE_SUPPLEMENT_ARTIFACT_MANIFEST_v0.1.json"
    )
    if mem_manifest.get("paper_number") is not None:
        fail("memristive supplemental silently acquired a charter paper number")
    if (
        mem_manifest.get("project_experimental_runpod_or_gpu_job")
        != "NONE_LAUNCHED"
    ):
        fail("memristive supplemental reports a project experimental GPU job")
    if mem_manifest.get("experiment_status") != "NO EXPERIMENT EXECUTED / NOT STARTED":
        fail("memristive supplemental experiment boundary was promoted")

    mem_matrix = load_json(
        mem_root / "MEMRISTIVE_SUPPLEMENT_THEOREM_CLAIM_TYPE_MATRIX_v0.1.json"
    )
    mem_ids = matrix_ids(mem_matrix, mem_matrix.get("schema_version", "memristive"))
    if len(mem_ids) != 50 or mem_matrix.get("entry_count") != 50:
        fail("memristive supplemental claim/type count is not 50")
    if mem_matrix.get("all_empirical_hypotheses_open") is not True:
        fail("memristive empirical hypothesis was promoted")
    if mem_matrix.get("all_authority_claims_open_or_held") is not True:
        fail("memristive authority boundary was promoted")
    mem_anchor_count = verify_memristive_source_and_evidence_controls(
        mem_root, mem_ids
    )

    mem_obligations = load_json(
        mem_root / "MEMRISTIVE_SUPPLEMENT_UNRESOLVED_OBLIGATIONS_v0.1.json"
    )
    obligations = mem_obligations.get("obligations")
    if not isinstance(obligations, list) or len(obligations) != 42:
        fail("memristive obligation count is not 42")
    if mem_obligations.get("obligation_count") != 42:
        fail("memristive declared obligation count is not 42")
    if mem_obligations.get("all_obligations_open") is not True:
        fail("memristive obligation ledger is not fail-closed")
    if (
        mem_obligations.get(
            "project_experimental_runpod_or_gpu_required_for_current_draft"
        )
        is not False
    ):
        fail("memristive draft incorrectly requires a project experimental GPU job")
    return len(entries), len(mem_ids), len(obligations), mem_anchor_count


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
        gate5_artifacts = verify_gate5_snapshot_crosswalk()
        (
            acceptance_count,
            mem_claim_count,
            mem_obligation_count,
            mem_anchor_count,
        ) = (
            verify_wave2_completion_packages()
        )
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
    print(f"  current Gate 5 successor snapshot artifacts: {gate5_artifacts}")
    print(
        f"  correction acceptance: {acceptance_count}/13 text corrections; "
        f"memristive records: {mem_claim_count}; open obligations: "
        f"{mem_obligation_count}; evidence anchors: {mem_anchor_count}; "
        "project experimental RunPod/GPU job: NONE"
    )
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
