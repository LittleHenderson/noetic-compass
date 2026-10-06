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

CURRENT_GATE5_SNAPSHOT_ID = (
    "G5-SNAPSHOT-CONTROLLER-CONTINUATION-SUCCESSOR"
)
CURRENT_GATE5_SOURCE_COMMIT = "a3236dace93839cd283f1bc8c875340790bb2442"
CURRENT_GATE5_ARTIFACT_COUNT = 377
CURRENT_GATE5_PROSPECTIVE_TESTS = 130
CURRENT_GATE5_PROSPECTIVE_TEST_IDS_SHA256 = (
    "0CA9217040958125285BFA0F6A7C6D517808B4AC4F4078C152620190767B6BB0"
)
CURRENT_GATE5_ADMITTED_TESTS = 90
CURRENT_GATE5_ADMITTED_TEST_IDS_SHA256 = (
    "761038779E00511179D4FC5AA3522829D9BDEFB37C231061D04FB3AAD541F733"
)
HISTORICAL_FINAL_REPLAY_COMMIT = "d24721afe18e05442f3c691f02dcf1608244f0e9"
HISTORICAL_FINAL_REPLAY_ARTIFACT_COUNT = 348
HISTORICAL_B015_REPLAY_COMMIT = "b015da8b46a225168ba3e578d24b9bd0af4c7fe7"
HISTORICAL_B015_REPLAY_ARTIFACT_COUNT = 377
HISTORICAL_B015_REPLAY_CANONICAL_SHA256 = (
    "59197647B9CDDA045D9E60251E1BD6D40682FEC5450831F8642DBB2DB6DE1859"
)
INTEGRATED_REPLAY_ORDER = [
    "GATE5",
    "PUBLICATION_PROGRAM",
    "GATE1",
    "GATE4",
]
GATE5_SNAPSHOT_RECORD_PATHS = {
    "gate5_manifest": (
        "docs/working/project_coherence/gate5/"
        "GATE5_ARTIFACT_MANIFEST_v0.1.json"
    ),
    "local_runner_lock": (
        "docs/working/project_coherence/gate5/"
        "GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json"
    ),
    "raw_build_security_receipt": (
        "docs/working/project_coherence/gate5/"
        "GATE5_RAW_BUILD_AND_SECURITY_EVIDENCE_RECEIPT_v0.1.json"
    ),
    "gate5_verifier": "scripts/verify_project_coherence_gate5.py",
    "gate5_adversarial_review": (
        "docs/working/project_coherence/gate5/"
        "GATE5_ADVERSARIAL_REVIEW_v0.1.md"
    ),
    "gate5_redteam": "tests/cas_harness_v2/test_gate5_verifier_redteam.py",
}

HISTORICAL_GATE5_SNAPSHOT_CANONICAL_SHA256 = {
    "G5-SNAPSHOT-HARNESS-LANE-BASE": (
        "FA1A48F426D8A5A50A0E202759591FCC1BA9F3264BE041104B5138DCABF5EAD8"
    ),
    "G5-SNAPSHOT-HARDENED-INTEGRATION": (
        "F356DB82D63CA6FE02DEF46194F178244FDC8832AC21A71D817D5BCAB6FCF847"
    ),
    "G5-SNAPSHOT-WORKER-PROTOCOL-SUCCESSOR": (
        "0254F078155BD186EC5F698FDFD3D8423DE9390FD2B0F5A1DADB14E91A81C687"
    ),
    "G5-SNAPSHOT-PROSPECTIVE-LIFECYCLE-SUCCESSOR": (
        "1A439D3366CBD94AE79FB7F13B2650FD4C70B314F6C5162B9367BB9E6D601E36"
    ),
    "G5-SNAPSHOT-ADMITTED-ADAPTER-RECONCILIATION-SUCCESSOR": (
        "59722065EF1FDEAD06430A630800763C19BD41353C4D313AFB298AD3D21454CD"
    ),
}


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


def canonical_json_sha256(value: Any) -> str:
    """Hash one JSON value with a deterministic, lossless semantic encoding."""
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def git_blob_identity(
    raw: str, *, commit: str = "HEAD"
) -> tuple[str, int, str]:
    """Return a commit's blob OID, byte count, and content SHA-256 for a path.

    The exact repository path is admitted for this invocation only.  This keeps
    Git source-binding checks usable in ownership-restricted sandboxes without
    mutating system, global, or repository configuration.
    """
    resolve_repo_path(raw)
    safe_directory = REPO_ROOT.resolve().as_posix()
    git_prefix = ["git", "-c", f"safe.directory={safe_directory}"]
    revision = f"{commit}:{raw}"
    oid_result = subprocess.run(
        [*git_prefix, "rev-parse", "--verify", revision],
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
        [*git_prefix, "cat-file", "blob", oid],
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


def verify_current_gate5_pointer_reconciliation(
    *, snapshot_id: str, source_commit: str, artifact_count: int
) -> None:
    """Require every integration-owned current Gate 5 pointer to agree."""
    dependency = load_json(
        INTEGRATION_ROOT
        / "PUBLICATION_DEPENDENCY_STATUS_AND_REVIEW_MAP_v0.1.json"
    )
    lead = dependency.get("lead_integration")
    if not isinstance(lead, dict):
        fail("dependency map lacks lead integration Gate 5 pointers")
    dependency_pointer = (
        lead.get("gate5_spine_commit"),
        lead.get("gate5_current_snapshot_id"),
        lead.get("gate5_current_artifact_count"),
    )
    expected_pointer = (source_commit, snapshot_id, artifact_count)
    if dependency_pointer != expected_pointer:
        fail("dependency map current Gate 5 pointer disagrees with crosswalk")

    integration_manifest = load_json(
        INTEGRATION_ROOT
        / "PUBLICATION_INTEGRATION_ARTIFACT_MANIFEST_v0.1.json"
    )
    validation = integration_manifest.get("validation_snapshot")
    if not isinstance(validation, dict):
        fail("integration manifest lacks validation snapshot Gate 5 pointers")
    integration_pointer = (
        validation.get("clean_candidate_commit"),
        validation.get("gate5_current_snapshot_id"),
        validation.get("gate5_current_artifact_count"),
    )
    if integration_pointer != expected_pointer:
        fail("integration manifest current Gate 5 pointer disagrees with crosswalk")


def verify_integrated_replay(
    replay: Any,
    *,
    label: str,
    expected_commit: str,
    expected_gate5_artifact_count: int,
) -> None:
    """Verify one complete ordered Gate 5/publication/Gate 1/Gate 4 replay."""
    if not isinstance(replay, dict):
        fail(f"{label} is not an object")
    if replay.get("commit") != expected_commit:
        fail(f"{label} commit mismatch")
    if replay.get("execution_order") != INTEGRATED_REPLAY_ORDER:
        fail(f"{label} execution order is invalid")
    results = replay.get("results")
    if not isinstance(results, dict) or set(results) != {
        "gate5",
        "publication_program",
        "gate1",
        "gate4",
    }:
        fail(f"{label} results are incomplete")
    if any(not isinstance(result, dict) for result in results.values()):
        fail(f"{label} contains a non-object result")
    if any(result.get("result") != "PASS" for result in results.values()):
        fail(f"{label} contains a non-PASS result")
    gate5 = results["gate5"]
    if gate5.get("artifact_count") != expected_gate5_artifact_count:
        fail(f"{label} Gate 5 artifact count mismatch")
    if gate5.get("experimental_execution") != "NOT_STARTED":
        fail(f"{label} promotes Gate 5 experimental execution")
    if gate5.get("dependency_security") != "OPEN_SECURITY / HELD":
        fail(f"{label} promotes Gate 5 dependency security")
    if expected_commit == CURRENT_GATE5_SOURCE_COMMIT:
        expected_current_fields = {
            "controller_continuations_admitted": True,
            "prospective_lifecycle_sqlite_dark_route_tests": (
                CURRENT_GATE5_PROSPECTIVE_TESTS
            ),
            "prospective_lifecycle_sqlite_dark_route_test_ids_sha256": (
                CURRENT_GATE5_PROSPECTIVE_TEST_IDS_SHA256
            ),
            "admitted_adapter_bounded_reconciliation_tests": (
                CURRENT_GATE5_ADMITTED_TESTS
            ),
            "admitted_adapter_bounded_reconciliation_test_ids_sha256": (
                CURRENT_GATE5_ADMITTED_TEST_IDS_SHA256
            ),
        }
        if any(
            gate5.get(key) != value
            for key, value in expected_current_fields.items()
        ):
            fail(f"{label} current Gate 5 test receipt drifted")
    if results["publication_program"].get("bound_publication_artifacts") != 71:
        fail(f"{label} publication artifact count mismatch")
    if results["gate1"].get("artifact_count") != 23:
        fail(f"{label} Gate 1 artifact count mismatch")
    if results["gate4"].get("artifact_count") != 54:
        fail(f"{label} Gate 4 artifact count mismatch")
    if results["gate1"].get("status_after_pass") != (
        "OPEN / Ring 4 / NOT LICENSED / NOT FROZEN"
    ):
        fail(f"{label} promotes Gate 1 status")
    if results["gate4"].get("status_after_pass") != (
        "OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN"
    ):
        fail(f"{label} promotes Gate 4 status")


def verify_current_successor_candidate(
    data: dict[str, Any], *, clean_candidate_replay: dict[str, Any]
) -> None:
    """Verify the current default-dark candidate separately from old replay."""
    candidate = data.get("current_successor_candidate")
    if not isinstance(candidate, dict):
        fail("current Gate 5 successor candidate is missing")
    if candidate.get("status") != (
        "CLEAN GATE 5 CANDIDATE PASS / PUBLICATION REBIND PASS ON RECEIPT "
        "WORKTREE / ORDERED RECEIPT-COMMIT REPLAY REQUIRED"
    ):
        fail("current Gate 5 successor candidate status is invalid")
    if candidate.get("commit") != CURRENT_GATE5_SOURCE_COMMIT:
        fail("current Gate 5 successor candidate commit mismatch")
    if candidate.get("snapshot_id") != CURRENT_GATE5_SNAPSHOT_ID:
        fail("current Gate 5 successor candidate snapshot mismatch")
    gate5 = candidate.get("gate5")
    if not isinstance(gate5, dict):
        fail("current Gate 5 successor candidate lacks Gate 5 result")
    expected_fields = {
        "result": "PASS WITH GATE OPEN",
        "artifact_count": CURRENT_GATE5_ARTIFACT_COUNT,
        "route_enabled": False,
        "packaged_adapter_admitted": True,
        "controller_continuations_admitted": True,
        "configured_scope_only": True,
        "prospective_lifecycle_sqlite_dark_route_tests": (
            CURRENT_GATE5_PROSPECTIVE_TESTS
        ),
        "prospective_lifecycle_sqlite_dark_route_test_ids_sha256": (
            CURRENT_GATE5_PROSPECTIVE_TEST_IDS_SHA256
        ),
        "admitted_adapter_bounded_reconciliation_tests": (
            CURRENT_GATE5_ADMITTED_TESTS
        ),
        "admitted_adapter_bounded_reconciliation_test_ids_sha256": (
            CURRENT_GATE5_ADMITTED_TEST_IDS_SHA256
        ),
        "experimental_execution": "NOT_STARTED",
        "dependency_security": "OPEN_SECURITY / HELD",
    }
    if any(gate5.get(key) != value for key, value in expected_fields.items()):
        fail("current Gate 5 successor candidate boundary mismatch")
    for key in (
        "result",
        "route_enabled",
        "packaged_adapter_admitted",
        "controller_continuations_admitted",
        "configured_scope_only",
        "prospective_lifecycle_sqlite_dark_route_tests",
        "prospective_lifecycle_sqlite_dark_route_test_ids_sha256",
        "admitted_adapter_bounded_reconciliation_tests",
        "admitted_adapter_bounded_reconciliation_test_ids_sha256",
        "experimental_execution",
        "dependency_security",
    ):
        if gate5.get(key) != clean_candidate_replay.get(key):
            fail(f"current Gate 5 successor candidate disagrees on {key}")
    if candidate.get("next_execution_order") != [
        "PUBLICATION_PROGRAM",
        "GATE1",
        "GATE4",
        "CLEAN_RECEIPT_COMMIT_REPLAY",
    ]:
        fail("current Gate 5 successor candidate next execution order is invalid")
    scope = candidate.get("receipt_scope")
    if not isinstance(scope, str) or any(
        marker not in scope
        for marker in (
            "DEFAULT-DARK ROUTE",
            "PACKAGED AND ADMITTED BOUNDED ADAPTER",
            "CONTROLLER CONTINUATIONS ADMITTED",
            "CONFIGURED-SCOPE RECONCILIATION",
            "NO LIVE PROVIDER EXECUTION",
            "NOT SCIENTIFIC EVIDENCE",
        )
    ):
        fail("current Gate 5 successor candidate scope is not fail-closed")


def verify_optional_current_integrated_replay(data: dict[str, Any]) -> None:
    """Allow a pending current replay, but verify it exactly once represented."""
    if "current_integrated_replay" not in data:
        return
    replay = data["current_integrated_replay"]
    if not isinstance(replay, dict):
        fail("current integrated replay is not an object")
    if replay.get("status") == "PENDING / NOT_STARTED":
        if replay.get("commit") != CURRENT_GATE5_SOURCE_COMMIT:
            fail("pending current integrated replay commit mismatch")
        if replay.get("execution_order") != INTEGRATED_REPLAY_ORDER:
            fail("pending current integrated replay execution order is invalid")
        if "results" in replay:
            fail("pending current integrated replay contains result claims")
        return
    if replay.get("status") != "PASS WITH GATE OPEN":
        fail("completed current integrated replay status is not fail-closed")
    verify_integrated_replay(
        replay,
        label="current integrated replay",
        expected_commit=CURRENT_GATE5_SOURCE_COMMIT,
        expected_gate5_artifact_count=CURRENT_GATE5_ARTIFACT_COUNT,
    )


def verify_gate5_snapshot_crosswalk() -> int:
    path = INTEGRATION_ROOT / "GATE5_EVIDENCE_SNAPSHOT_CROSSWALK_v0.1.json"
    data = load_json(path)
    snapshots = data.get("snapshots")
    if not isinstance(snapshots, list):
        fail("Gate 5 snapshot crosswalk has no snapshots list")
    if any(not isinstance(item, dict) for item in snapshots):
        fail("Gate 5 snapshot crosswalk contains a non-object snapshot")
    expected_snapshot_ids = [
        "G5-SNAPSHOT-HARNESS-LANE-BASE",
        "G5-SNAPSHOT-HARDENED-INTEGRATION",
        "G5-SNAPSHOT-WORKER-PROTOCOL-SUCCESSOR",
        "G5-SNAPSHOT-PROSPECTIVE-LIFECYCLE-SUCCESSOR",
        "G5-SNAPSHOT-ADMITTED-ADAPTER-RECONCILIATION-SUCCESSOR",
        CURRENT_GATE5_SNAPSHOT_ID,
    ]
    actual_snapshot_ids = [item.get("snapshot_id") for item in snapshots]
    if actual_snapshot_ids != expected_snapshot_ids:
        fail("Gate 5 snapshot IDs or historical order changed")
    historical_expectations = {
        "G5-SNAPSHOT-HARNESS-LANE-BASE": (
            325,
            "5C73F203B4EA7D95B89C3BBB730FFCAE571EECC26E8BA2AF3ABC4A994635B333",
            None,
        ),
        "G5-SNAPSHOT-HARDENED-INTEGRATION": (
            340,
            "AF263573DAB68D814A09D75CFEBB2ECDD62B08491BD2D1D66C7D5332F682A72A",
            "fbac9909a2b600ac8bc9f1217c073e4a3269beea",
        ),
        "G5-SNAPSHOT-WORKER-PROTOCOL-SUCCESSOR": (
            348,
            "E370F1CE68550ED166612E90791A5E3A3701D22F5777DDF7831EE36EA0A5A24E",
            "d24721afe18e05442f3c691f02dcf1608244f0e9",
        ),
        "G5-SNAPSHOT-PROSPECTIVE-LIFECYCLE-SUCCESSOR": (
            355,
            "624E7D577E770BF7CC4490D1D3AC315837E8E753CCD454D2F4E96E6685DC17AB",
            "e0405bf58dfe2a132476fa2672f288dcc097cd77",
        ),
        "G5-SNAPSHOT-ADMITTED-ADAPTER-RECONCILIATION-SUCCESSOR": (
            377,
            "2E5C549679BE5C7C5FD23F172EB52D8F73DC7606529CB9B32F1854DCEE8FB4B2",
            "b015da8b46a225168ba3e578d24b9bd0af4c7fe7",
        ),
    }
    snapshots_by_id = {item["snapshot_id"]: item for item in snapshots}
    if set(HISTORICAL_GATE5_SNAPSHOT_CANONICAL_SHA256) != set(
        historical_expectations
    ):
        fail("historical Gate 5 snapshot fingerprint registry is incomplete")
    for snapshot_id, (
        artifact_count,
        manifest_sha256,
        source_commit,
    ) in historical_expectations.items():
        historical = snapshots_by_id[snapshot_id]
        manifest_record = historical.get("gate5_manifest")
        if not isinstance(manifest_record, dict):
            fail(f"historical Gate 5 snapshot lacks manifest: {snapshot_id}")
        declared_count = manifest_record.get("artifact_count")
        declared_hash = manifest_record.get(
            "sha256_at_snapshot", manifest_record.get("sha256")
        )
        if (declared_count, declared_hash) != (artifact_count, manifest_sha256):
            fail(f"historical Gate 5 snapshot was rewritten: {snapshot_id}")
        if (
            source_commit is not None
            and historical.get("source_commit") != source_commit
        ):
            fail(f"historical Gate 5 source commit was rewritten: {snapshot_id}")
        if canonical_json_sha256(historical) != (
            HISTORICAL_GATE5_SNAPSHOT_CANONICAL_SHA256[snapshot_id]
        ):
            fail(f"historical Gate 5 snapshot object was rewritten: {snapshot_id}")
    current_snapshot_id = data.get("current_snapshot_id")
    if current_snapshot_id != CURRENT_GATE5_SNAPSHOT_ID:
        fail("current Gate 5 successor snapshot pointer is invalid")
    current = snapshots_by_id[current_snapshot_id]
    if current.get("source_commit") != CURRENT_GATE5_SOURCE_COMMIT:
        fail("current Gate 5 successor source commit is not frozen")
    if current.get("parent_snapshot_id") != (
        "G5-SNAPSHOT-ADMITTED-ADAPTER-RECONCILIATION-SUCCESSOR"
    ):
        fail("current Gate 5 successor parent linkage is invalid")
    for key, expected_path in GATE5_SNAPSHOT_RECORD_PATHS.items():
        record = current.get(key)
        if not isinstance(record, dict):
            fail(f"current Gate 5 successor snapshot lacks {key}")
        if record.get("path") != expected_path:
            fail(f"current Gate 5 successor snapshot path mismatch: {key}")
        target = resolve_repo_path(record.get("path"))
        if not target.is_file():
            fail(f"current Gate 5 successor snapshot target is missing: {key}")
        if target.stat().st_size != record.get("bytes"):
            fail(f"current Gate 5 successor snapshot byte mismatch: {key}")
        if sha256(target) != record.get("sha256"):
            fail(f"current Gate 5 successor snapshot hash mismatch: {key}")
        _, blob_bytes, blob_sha256 = git_blob_identity(
            record.get("path"), commit=CURRENT_GATE5_SOURCE_COMMIT
        )
        if (record.get("bytes"), record.get("sha256")) != (
            blob_bytes,
            blob_sha256,
        ):
            fail(
                f"current Gate 5 successor source-commit blob mismatch: {key}"
            )
    gate5_manifest = load_json(resolve_repo_path(current["gate5_manifest"]["path"]))
    artifact_count = gate5_manifest.get("artifact_count")
    if artifact_count != current["gate5_manifest"].get("artifact_count"):
        fail("current Gate 5 successor artifact count mismatch")
    if artifact_count != CURRENT_GATE5_ARTIFACT_COUNT:
        fail(
            "current Gate 5 successor artifact count is not "
            f"{CURRENT_GATE5_ARTIFACT_COUNT}"
        )

    candidate_replay = current.get("clean_candidate_replay")
    if not isinstance(candidate_replay, dict):
        fail("current Gate 5 successor lacks a clean candidate replay")
    if candidate_replay.get("commit") != current.get("source_commit"):
        fail("current Gate 5 successor replay commit differs from source commit")
    if candidate_replay.get("experimental_execution") != "NOT_STARTED":
        fail("current Gate 5 successor replay promotes experimental execution")
    if candidate_replay.get("dependency_security") != "OPEN_SECURITY / HELD":
        fail("current Gate 5 successor replay promotes dependency security")
    if candidate_replay.get("result") != "PASS WITH GATE OPEN":
        fail("current Gate 5 successor replay does not preserve the open gate")
    if candidate_replay.get("route_enabled") is not False:
        fail("current Gate 5 successor replay does not preserve default-dark routing")
    if candidate_replay.get("packaged_adapter_admitted") is not True:
        fail("current Gate 5 successor replay omits the admitted adapter")
    if candidate_replay.get("configured_scope_only") is not True:
        fail("current Gate 5 successor replay promotes reconciliation scope")
    expected_current_replay_fields = {
        "controller_continuations_admitted": True,
        "prospective_lifecycle_sqlite_dark_route_tests": (
            CURRENT_GATE5_PROSPECTIVE_TESTS
        ),
        "prospective_lifecycle_sqlite_dark_route_test_ids_sha256": (
            CURRENT_GATE5_PROSPECTIVE_TEST_IDS_SHA256
        ),
        "admitted_adapter_bounded_reconciliation_tests": (
            CURRENT_GATE5_ADMITTED_TESTS
        ),
        "admitted_adapter_bounded_reconciliation_test_ids_sha256": (
            CURRENT_GATE5_ADMITTED_TEST_IDS_SHA256
        ),
    }
    if any(
        candidate_replay.get(key) != value
        for key, value in expected_current_replay_fields.items()
    ):
        fail("current Gate 5 successor replay test receipt drifted")

    verify_current_successor_candidate(
        data, clean_candidate_replay=candidate_replay
    )
    verify_integrated_replay(
        data.get("final_integrated_replay"),
        label="historical d247 final integrated replay",
        expected_commit=HISTORICAL_FINAL_REPLAY_COMMIT,
        expected_gate5_artifact_count=HISTORICAL_FINAL_REPLAY_ARTIFACT_COUNT,
    )
    historical_replays = data.get("historical_integrated_replays")
    if not isinstance(historical_replays, list) or len(historical_replays) != 1:
        fail("historical integrated replay archive is incomplete")
    historical_b015_replay = historical_replays[0]
    if canonical_json_sha256(historical_b015_replay) != (
        HISTORICAL_B015_REPLAY_CANONICAL_SHA256
    ):
        fail("historical b015 integrated replay object was rewritten")
    verify_integrated_replay(
        historical_b015_replay,
        label="historical b015 integrated replay",
        expected_commit=HISTORICAL_B015_REPLAY_COMMIT,
        expected_gate5_artifact_count=HISTORICAL_B015_REPLAY_ARTIFACT_COUNT,
    )
    verify_optional_current_integrated_replay(data)
    verify_current_gate5_pointer_reconciliation(
        snapshot_id=current_snapshot_id,
        source_commit=current["source_commit"],
        artifact_count=artifact_count,
    )
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
