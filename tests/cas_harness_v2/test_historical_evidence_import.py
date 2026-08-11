from __future__ import annotations

import ast
from dataclasses import replace
import json
import os
from pathlib import Path
import socket
import subprocess
from types import MappingProxyType
import urllib.request

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes, thaw_json
from cas_harness_v2._validation import SchemaValidationError
from cas_harness_v2.artifacts import ArtifactByteRegistry, EvidenceFile
from cas_harness_v2.evidence_packet import EvidencePacketArtifact
from cas_harness_v2.historical_evidence_import import (
    DEFAULT_HISTORICAL_MANIFEST_RELATIVE_PATH,
    DRIFTED,
    HISTORICAL_EVIDENCE_IMPORT_MEDIA_TYPE,
    HISTORICAL_EVIDENCE_IMPORT_SCHEMA,
    HISTORICAL_EVIDENCE_ONLY,
    HISTORICAL_SOURCE_MANIFEST_MEDIA_TYPE,
    HISTORICAL_SOURCE_MANIFEST_SCHEMA,
    MATCHED,
    NON_AUTHORITY,
    PROMOTION_INELIGIBLE,
    READ_ONLY,
    UNLISTED,
    HistoricalEvidenceImportArtifact,
    HistoricalEvidenceRecord,
    HistoricalSourceFileSnapshot,
    build_historical_evidence_import,
    load_historical_evidence_import,
    replay_historical_evidence_import,
)
import cas_harness_v2.historical_evidence_import as sut


def _entry(
    *,
    artifact_id: str,
    bundle_id: str,
    relative_path: str,
    declared_body: bytes,
    media_type: str,
    original_status: str,
) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "source_bundle_id": bundle_id,
        "relative_path": relative_path,
        "sha256": sha256_bytes(declared_body),
        "byte_length": len(declared_body),
        "media_type": media_type,
        "original_status": original_status,
    }


def _write_bundle(root: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    bundle_id = "handoff-bundle-2026-07-21"
    bodies = {
        "attempt11/evidence.json": (
            b'{"attempt":"Attempt11","authority":"historical","status":"ACCEPT"}'
        ),
        "j-space/jvp.bin": b"observed-j-space-bytes",
        "notes/unlisted.txt": b"unlisted historical note",
    }
    for relative_path, body in bodies.items():
        path = root.joinpath(*relative_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    manifest = {
        "schema": HISTORICAL_SOURCE_MANIFEST_SCHEMA,
        "source_bundle_id": bundle_id,
        "entries": [
            _entry(
                artifact_id="attempt11-historical-evidence",
                bundle_id=bundle_id,
                relative_path="attempt11/evidence.json",
                declared_body=bodies["attempt11/evidence.json"],
                media_type="application/json",
                original_status="ACCEPT",
            ),
            _entry(
                artifact_id="j-space-jvp-historical",
                bundle_id=bundle_id,
                relative_path="j-space/jvp.bin",
                declared_body=b"original-j-space-bytes",
                media_type="application/octet-stream",
                original_status="PASS",
            ),
        ],
    }
    (root / DEFAULT_HISTORICAL_MANIFEST_RELATIVE_PATH).write_bytes(
        canonical_json_bytes(manifest)
    )
    return manifest, bodies


def _mapping(root: Path) -> dict[str, EvidenceFile]:
    return {
        relative_path: EvidenceFile.from_path(
            f"source-{index:03d}",
            path,
        )
        for index, path in enumerate(
            sorted(path for path in root.rglob("*") if path.is_file()),
            start=1,
        )
        for relative_path in (path.relative_to(root).as_posix(),)
    }


def _build(root: Path) -> HistoricalEvidenceImportArtifact:
    return build_historical_evidence_import(
        import_id="historical-import-test-001",
        source=root,
    )


def _rewrite_manifest(root: Path, manifest: dict[str, object]) -> None:
    (root / DEFAULT_HISTORICAL_MANIFEST_RELATIVE_PATH).write_bytes(
        canonical_json_bytes(manifest)
    )


def test_directory_import_reports_matched_drifted_and_unlisted_without_promotion(
    tmp_path: Path,
) -> None:
    root = tmp_path / "bundle"
    manifest, bodies = _write_bundle(root)
    artifact = _build(root)
    assert artifact.source_bundle_id == manifest["source_bundle_id"]
    assert artifact.covered_count == 2
    assert artifact.matched_count == 1
    assert artifact.drifted_count == 1
    assert artifact.unlisted_count == 1
    assert artifact.payload["manifest"] == {
        "relative_path": DEFAULT_HISTORICAL_MANIFEST_RELATIVE_PATH,
        "sha256": sha256_bytes(canonical_json_bytes(manifest)),
        "byte_length": len(canonical_json_bytes(manifest)),
        "media_type": HISTORICAL_SOURCE_MANIFEST_MEDIA_TYPE,
        "covered": 2,
        "matched": 1,
        "drifted": 1,
        "unlisted": 1,
    }
    by_path = {record.relative_path: record for record in artifact.records}
    attempt = by_path["attempt11/evidence.json"]
    jspace = by_path["j-space/jvp.bin"]
    unlisted = by_path["notes/unlisted.txt"]
    assert attempt.manifest_disposition == MATCHED
    assert attempt.original_status == "ACCEPT"
    assert jspace.manifest_disposition == DRIFTED
    assert jspace.original_status == "PASS"
    assert unlisted.manifest_disposition == UNLISTED
    assert unlisted.original_status is None
    assert all(
        record.evidence_classification == HISTORICAL_EVIDENCE_ONLY
        and record.promotion_eligibility == PROMOTION_INELIGIBLE
        for record in artifact.records
    )
    snapshots = {item.relative_path: item for item in artifact.source_files}
    assert snapshots["attempt11/evidence.json"].raw_bytes == bodies[
        "attempt11/evidence.json"
    ]
    assert snapshots["j-space/jvp.bin"].raw_bytes == bodies["j-space/jvp.bin"]


def test_mapping_build_load_and_replay_are_canonical_and_exact(tmp_path: Path) -> None:
    root = tmp_path / "mapping"
    _write_bundle(root)
    artifact = build_historical_evidence_import(
        import_id="historical-import-mapping-001",
        source=_mapping(root),
    )
    assert artifact.raw_bytes == canonical_json_bytes(thaw_json(artifact.payload))
    assert artifact.payload["schema"] == HISTORICAL_EVIDENCE_IMPORT_SCHEMA
    assert artifact.payload["status"] == {
        "classification": HISTORICAL_EVIDENCE_ONLY,
        "scope": READ_ONLY,
        "authority": NON_AUTHORITY,
    }
    assert artifact.payload["boundary"] == {
        "promotion": "FORBIDDEN",
        "current_result": "NOT_CREATED",
        "current_evidence_packet": "NOT_CREATED",
        "authorization": "NOT_GRANTED",
        "provider_calls": 0,
        "model_calls": 0,
        "network_calls": 0,
        "filesystem_writes": 0,
        "live_backend_calls": 0,
    }
    assert replay_historical_evidence_import(artifact) == artifact
    assert (
        load_historical_evidence_import(
            artifact.raw_bytes,
            import_id=artifact.import_id,
            manifest_relative_path=artifact.manifest_relative_path,
            source_files=artifact.source_files,
        )
        == artifact
    )


def test_payload_bytes_are_not_parsed_or_schema_coerced(tmp_path: Path) -> None:
    root = tmp_path / "opaque"
    manifest, _ = _write_bundle(root)
    opaque = b'not-json\x00{"schema":"current_result","authority":"ACCEPT"}'
    path = root / "attempt11" / "evidence.json"
    path.write_bytes(opaque)
    manifest["entries"][0] = _entry(
        artifact_id="attempt11-historical-evidence",
        bundle_id=manifest["source_bundle_id"],
        relative_path="attempt11/evidence.json",
        declared_body=opaque,
        media_type="application/octet-stream",
        original_status="ACCEPT",
    )
    _rewrite_manifest(root, manifest)
    artifact = _build(root)
    snapshot = next(
        item
        for item in artifact.source_files
        if item.relative_path == "attempt11/evidence.json"
    )
    assert snapshot.raw_bytes == opaque
    assert artifact.records[0].promotion_eligibility == PROMOTION_INELIGIBLE


@pytest.mark.parametrize(
    "relative_path",
    [
        "/absolute.json",
        "C:/absolute.json",
        "../traversal.json",
        "dir/../traversal.json",
        r"dir\backslash.json",
        "dir/file.json:stream",
        "CON.txt",
        "dir/PRN.json",
        "dir/trailing.",
        "current/result.json",
        "current-result/output.json",
        "current_authority/output.json",
        "current_authorization/output.json",
        "current_evidence_packet/output.json",
        "current_authority_output/result.json",
    ],
)
def test_manifest_rejects_absolute_traversal_backslash_ads_reserved_and_current_paths(
    tmp_path: Path,
    relative_path: str,
) -> None:
    root = tmp_path / "bad-path"
    manifest, _ = _write_bundle(root)
    manifest["entries"][0]["relative_path"] = relative_path
    _rewrite_manifest(root, manifest)
    with pytest.raises(SchemaValidationError, match="relative path|current result"):
        _build(root)


def test_mapping_rejects_casefold_collision_and_duplicate_source_id(tmp_path: Path) -> None:
    root = tmp_path / "mapping-collision"
    _write_bundle(root)
    first = root / "one.bin"
    second = root / "two.bin"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    mapping = _mapping(root)
    mapping["Case/File.bin"] = EvidenceFile.from_path("case-source-one", first)
    mapping["case/file.bin"] = EvidenceFile.from_path("case-source-two", second)
    with pytest.raises(SchemaValidationError, match="casefold path collision"):
        build_historical_evidence_import(
            import_id="historical-import-casefold",
            source=mapping,
        )

    mapping = _mapping(root)
    shared = EvidenceFile.from_path("duplicate-source-id", first)
    mapping["extra/one.bin"] = shared
    mapping["extra/two.bin"] = shared
    with pytest.raises(SchemaValidationError, match="source_file_id"):
        build_historical_evidence_import(
            import_id="historical-import-source-id",
            source=mapping,
        )


def test_mapping_rejects_current_and_cross_role_source_ids(tmp_path: Path) -> None:
    root = tmp_path / "mapping-id-boundary"
    _write_bundle(root)
    attempt_path = root / "attempt11" / "evidence.json"

    current_mapping = _mapping(root)
    current_mapping["attempt11/evidence.json"] = EvidenceFile.from_path(
        "current-result-source",
        attempt_path,
    )
    with pytest.raises(SchemaValidationError, match="current result or authority identity"):
        build_historical_evidence_import(
            import_id="historical-import-current-source-id",
            source=current_mapping,
        )

    reused_mapping = _mapping(root)
    reused_mapping["attempt11/evidence.json"] = EvidenceFile.from_path(
        "attempt11-historical-evidence",
        attempt_path,
    )
    with pytest.raises(SchemaValidationError, match="globally distinct"):
        build_historical_evidence_import(
            import_id="historical-import-cross-role-source-id",
            source=reused_mapping,
        )


def test_directory_rejects_relative_source(tmp_path: Path) -> None:
    with pytest.raises(SchemaValidationError, match="must be absolute"):
        build_historical_evidence_import(
            import_id="historical-import-relative",
            source="relative/source",
        )


def test_directory_rejects_hostile_path_protocol_before_callback() -> None:
    calls = 0

    class HostilePath:
        def __fspath__(self) -> str:
            nonlocal calls
            calls += 1
            raise AssertionError("hostile path callback ran")

    with pytest.raises(SchemaValidationError, match="exact str or platform Path"):
        build_historical_evidence_import(
            import_id="historical-import-hostile-path",
            source=HostilePath(),
        )
    assert calls == 0


def test_source_dispatch_rejects_hostile_class_callback_before_access() -> None:
    calls = 0

    class HostileSource:
        def __getattribute__(self, name: str):
            nonlocal calls
            if name == "__class__":
                calls += 1
                raise AssertionError("hostile class callback ran")
            return object.__getattribute__(self, name)

    with pytest.raises(SchemaValidationError, match="exact str or platform Path"):
        build_historical_evidence_import(
            import_id="historical-import-hostile-class",
            source=HostileSource(),
        )
    assert calls == 0


def test_source_dispatch_rejects_hostile_mapping_proxy_before_access() -> None:
    calls = 0

    class HostileMapping(dict):
        def items(self):
            nonlocal calls
            calls += 1
            raise AssertionError("hostile mapping callback ran")

    source = MappingProxyType(HostileMapping())
    with pytest.raises(SchemaValidationError, match="exact dict"):
        build_historical_evidence_import(
            import_id="historical-import-hostile-mapping",
            source=source,
        )
    assert calls == 0


def test_directory_rejects_symlink(tmp_path: Path) -> None:
    symlink_root = tmp_path / "symlink"
    _write_bundle(symlink_root)
    target = symlink_root / "real.bin"
    link = symlink_root / "linked.bin"
    target.write_bytes(b"real symlink target")
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(SchemaValidationError, match="symbolic link|reparse"):
        _build(symlink_root)


def test_directory_rejects_reparse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reparse_root = tmp_path / "synthetic-reparse"
    _write_bundle(reparse_root)
    monkeypatch.setattr(sut, "_is_reparse_stat", lambda value: True)
    with pytest.raises(SchemaValidationError, match="reparse"):
        _build(reparse_root)


def test_directory_rejects_hardlink(tmp_path: Path) -> None:
    hardlink_root = tmp_path / "hardlink"
    _write_bundle(hardlink_root)
    target = hardlink_root / "attempt11" / "evidence.json"
    alias = hardlink_root / "alias.bin"
    try:
        os.link(target, alias)
    except OSError as exc:
        pytest.skip(f"hardlink creation unavailable: {exc}")
    with pytest.raises(SchemaValidationError, match="hard-link"):
        _build(hardlink_root)


def test_during_snapshot_mutation_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "mutation"
    _write_bundle(root)
    original = EvidenceFile.snapshot_bytes
    changed = False

    def sabotaged(self, *, maximum_byte_count):
        nonlocal changed
        result = original(self, maximum_byte_count=maximum_byte_count)
        if not changed and self.path.name == "evidence.json":
            changed = True
            self.path.write_bytes(result.raw_bytes + b"changed")
        return result

    monkeypatch.setattr(EvidenceFile, "snapshot_bytes", sabotaged)
    with pytest.raises(SchemaValidationError, match="changed|unsafe"):
        _build(root)


def test_missing_file_and_strict_manifest_extra_field_are_rejected(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    _write_bundle(missing_root)
    (missing_root / "j-space" / "jvp.bin").unlink()
    with pytest.raises(SchemaValidationError, match="missing files"):
        _build(missing_root)

    extra_root = tmp_path / "extra-manifest-field"
    manifest, _ = _write_bundle(extra_root)
    manifest["current_result_slot"] = "ACCEPT"
    _rewrite_manifest(extra_root, manifest)
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        _build(extra_root)


def test_duplicate_manifest_id_content_and_source_content_are_rejected(
    tmp_path: Path,
) -> None:
    duplicate_id_root = tmp_path / "duplicate-id"
    manifest, _ = _write_bundle(duplicate_id_root)
    manifest["entries"][1]["artifact_id"] = manifest["entries"][0]["artifact_id"]
    _rewrite_manifest(duplicate_id_root, manifest)
    with pytest.raises(SchemaValidationError, match="duplicate artifact IDs"):
        _build(duplicate_id_root)

    duplicate_declared_root = tmp_path / "duplicate-declared-content"
    manifest, _ = _write_bundle(duplicate_declared_root)
    manifest["entries"][1]["sha256"] = manifest["entries"][0]["sha256"]
    manifest["entries"][1]["byte_length"] = manifest["entries"][0]["byte_length"]
    _rewrite_manifest(duplicate_declared_root, manifest)
    with pytest.raises(SchemaValidationError, match="duplicate content identities"):
        _build(duplicate_declared_root)

    duplicate_source_root = tmp_path / "duplicate-source-content"
    _write_bundle(duplicate_source_root)
    first = duplicate_source_root / "copy-one.bin"
    second = duplicate_source_root / "copy-two.bin"
    first.write_bytes(b"same source bytes")
    second.write_bytes(b"same source bytes")
    with pytest.raises(SchemaValidationError, match="duplicate content identities"):
        _build(duplicate_source_root)


def test_import_bundle_manifest_and_source_owner_ids_are_globally_distinct(
    tmp_path: Path,
) -> None:
    import_owner_root = tmp_path / "import-owner"
    manifest, _ = _write_bundle(import_owner_root)
    manifest["entries"][0]["artifact_id"] = "historical-import-test-001"
    _rewrite_manifest(import_owner_root, manifest)
    with pytest.raises(SchemaValidationError, match="owner identities collide"):
        _build(import_owner_root)

    bundle_owner_root = tmp_path / "bundle-owner"
    manifest, _ = _write_bundle(bundle_owner_root)
    manifest["source_bundle_id"] = "attempt11-historical-evidence"
    for entry in manifest["entries"]:
        entry["source_bundle_id"] = "attempt11-historical-evidence"
    _rewrite_manifest(bundle_owner_root, manifest)
    with pytest.raises(SchemaValidationError, match="owner identities collide"):
        _build(bundle_owner_root)

    source_owner_root = tmp_path / "source-owner"
    _write_bundle(source_owner_root)
    mapping = _mapping(source_owner_root)
    path = source_owner_root / "attempt11" / "evidence.json"
    mapping["attempt11/evidence.json"] = EvidenceFile.from_path(
        "historical-import-source-owner",
        path,
    )
    with pytest.raises(SchemaValidationError, match="owner identities collide"):
        build_historical_evidence_import(
            import_id="historical-import-source-owner",
            source=mapping,
        )


def test_public_loader_enforces_fixed_file_count_and_byte_bounds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "loader-bounds"
    _write_bundle(root)
    artifact = _build(root)
    monkeypatch.setattr(sut, "MAXIMUM_HISTORICAL_FILE_COUNT", 2)
    with pytest.raises(SchemaValidationError, match="file-count bound"):
        load_historical_evidence_import(
            artifact.raw_bytes,
            import_id=artifact.import_id,
            manifest_relative_path=artifact.manifest_relative_path,
            source_files=artifact.source_files,
        )
    monkeypatch.setattr(sut, "MAXIMUM_HISTORICAL_FILE_COUNT", 10_000)
    monkeypatch.setattr(sut, "MAXIMUM_HISTORICAL_FILE_BYTES", 1)
    with pytest.raises(SchemaValidationError, match="per-file bound"):
        load_historical_evidence_import(
            artifact.raw_bytes,
            import_id=artifact.import_id,
            manifest_relative_path=artifact.manifest_relative_path,
            source_files=artifact.source_files,
        )


def test_mixed_bundle_current_media_status_identity_and_import_slot_are_rejected(
    tmp_path: Path,
) -> None:
    mutations = (
        (
            lambda manifest: manifest["entries"][0].__setitem__(
                "source_bundle_id", "different-bundle"
            ),
            "mixes source bundle",
        ),
        (
            lambda manifest: manifest["entries"][0].__setitem__(
                "media_type", "application/vnd.cas-harness.evidence-packet-v2+json"
            ),
            "current evidence or authority media slot",
        ),
        (
            lambda manifest: manifest["entries"][0].__setitem__(
                "media_type", "application/vnd.cas-harness.worker-authorization-v1+json"
            ),
            "current evidence or authority media slot",
        ),
        (
            lambda manifest: manifest["entries"][0].__setitem__(
                "original_status", "CURRENT_AUTHORITY"
            ),
            "current-authority relabeling",
        ),
        (
            lambda manifest: manifest["entries"][0].__setitem__(
                "original_status", "CURRENT-AUTHORITY"
            ),
            "current-authority relabeling",
        ),
        (
            lambda manifest: manifest["entries"][0].__setitem__(
                "original_status", "CURRENT-RESULT"
            ),
            "current-authority relabeling",
        ),
        (
            lambda manifest: manifest["entries"][0].__setitem__(
                "original_status", "CURRENT-AUTHORITY-PENDING"
            ),
            "current-authority relabeling",
        ),
        (
            lambda manifest: manifest["entries"][0].__setitem__(
                "artifact_id", "current-result-attempt11"
            ),
            "current result or authority identity",
        ),
    )
    for index, (mutate, match) in enumerate(mutations):
        root = tmp_path / f"relabel-{index}"
        manifest, _ = _write_bundle(root)
        mutate(manifest)
        _rewrite_manifest(root, manifest)
        with pytest.raises(SchemaValidationError, match=match):
            _build(root)

    root = tmp_path / "import-slot"
    _write_bundle(root)
    with pytest.raises(
        SchemaValidationError,
        match="current result or authority identity|historical-import namespace",
    ):
        build_historical_evidence_import(import_id="current-result", source=root)


def test_noncanonical_manifest_and_report_extra_bool_and_promotion_drift_fail(
    tmp_path: Path,
) -> None:
    noncanonical_root = tmp_path / "noncanonical"
    manifest, _ = _write_bundle(noncanonical_root)
    (noncanonical_root / DEFAULT_HISTORICAL_MANIFEST_RELATIVE_PATH).write_bytes(
        json.dumps(manifest, indent=2).encode("utf-8")
    )
    with pytest.raises(SchemaValidationError, match="canonical JSON"):
        _build(noncanonical_root)

    root = tmp_path / "report-drift"
    _write_bundle(root)
    artifact = _build(root)
    for mutate, match in (
        (lambda value: value.__setitem__("extra", True), "forbidden extra"),
        (
            lambda value: value["manifest"].__setitem__("covered", True),
            "exact integer",
        ),
        (
            lambda value: value["records"][0].__setitem__(
                "promotion_eligibility", "ELIGIBLE"
            ),
            "promote historical evidence",
        ),
        (
            lambda value: value["boundary"].__setitem__("model_calls", 1),
            "provider/model/network/write/live",
        ),
    ):
        payload = thaw_json(artifact.payload)
        mutate(payload)
        raw = canonical_json_bytes(payload)
        with pytest.raises(SchemaValidationError, match=match):
            load_historical_evidence_import(
                raw,
                import_id=artifact.import_id,
                manifest_relative_path=artifact.manifest_relative_path,
                source_files=artifact.source_files,
            )


def test_replay_rejects_mutable_and_forged_carriers(tmp_path: Path) -> None:
    root = tmp_path / "forgery"
    _write_bundle(root)
    artifact = _build(root)
    assert "payload" not in HistoricalEvidenceImportArtifact.__dataclass_fields__
    with pytest.raises(TypeError):
        replace(artifact, payload=thaw_json(artifact.payload))
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        replay_historical_evidence_import(
            replace(artifact, matched_count=artifact.matched_count + 1)
        )
    original_record = artifact.records[0]
    forged_record = object.__new__(HistoricalEvidenceRecord)
    for field_name in HistoricalEvidenceRecord.__dataclass_fields__:
        object.__setattr__(
            forged_record,
            field_name,
            getattr(original_record, field_name),
        )
    object.__setattr__(forged_record, "promotion_eligibility", "ELIGIBLE")
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        replay_historical_evidence_import(
            replace(artifact, records=(forged_record, *artifact.records[1:]))
        )


def test_record_constructor_and_replay_reject_hostile_objects_without_callbacks(
    tmp_path: Path,
) -> None:
    root = tmp_path / "hostile-record"
    _write_bundle(root)
    artifact = _build(root)
    original = artifact.records[0]
    equality_calls = 0

    class HostileDisposition:
        def __eq__(self, other: object) -> bool:
            del other
            nonlocal equality_calls
            equality_calls += 1
            raise AssertionError("hostile equality callback ran")

    fields = {
        name: getattr(original, name)
        for name in HistoricalEvidenceRecord.__dataclass_fields__
    }
    fields["manifest_disposition"] = HostileDisposition()
    with pytest.raises(SchemaValidationError, match="exact strings"):
        HistoricalEvidenceRecord(**fields)
    assert equality_calls == 0

    class_calls = 0

    class HostileRecord:
        def __getattribute__(self, name: str):
            nonlocal class_calls
            if name == "__class__":
                class_calls += 1
                raise AssertionError("hostile class callback ran")
            return object.__getattribute__(self, name)

    with pytest.raises(SchemaValidationError, match="exact HistoricalEvidenceRecord"):
        replay_historical_evidence_import(
            replace(artifact, records=(HostileRecord(), *artifact.records[1:]))
        )
    assert class_calls == 0
    source = artifact.source_files[0]
    forged_source = object.__new__(HistoricalSourceFileSnapshot)
    for field_name in HistoricalSourceFileSnapshot.__dataclass_fields__:
        object.__setattr__(
            forged_source,
            field_name,
            getattr(source, field_name),
        )
    object.__setattr__(forged_source, "raw_bytes", source.raw_bytes + b"forged")
    with pytest.raises(SchemaValidationError, match="retained bytes"):
        replay_historical_evidence_import(
            replace(artifact, source_files=(forged_source, *artifact.source_files[1:]))
        )


def test_no_current_carrier_api_or_external_write_live_backend_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "boundary"
    _write_bundle(root)

    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("external seam was touched")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    artifact = _build(root)
    assert type(artifact) is HistoricalEvidenceImportArtifact
    assert not isinstance(artifact, EvidencePacketArtifact)
    assert not hasattr(artifact, "artifact_ref")
    with pytest.raises(SchemaValidationError):
        ArtifactByteRegistry({"historical": artifact})
    assert artifact.payload["boundary"]["filesystem_writes"] == 0
    assert artifact.payload["boundary"]["live_backend_calls"] == 0


def test_public_exports_are_literal_unique_and_source_is_current_path_isolated() -> None:
    source = Path(sut.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    exports = ast.literal_eval(assignments[0].value)
    assert type(exports) is tuple
    assert len(exports) == len(set(exports))
    assert exports == sut.__all__
    forbidden_imports = {
        "authorization",
        "comparison_execution_boundary",
        "evidence_packet",
        "evidence_packet_builder",
        "stagec_outcome",
    }
    imported = {
        alias.name.rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert forbidden_imports.isdisjoint(imported)
    source_folded = source.casefold()
    assert "requests" not in source_folded
    assert "urlopen" not in source_folded
    assert "subprocess" not in source_folded
    assert ".write_" not in source_folded
    assert HISTORICAL_EVIDENCE_IMPORT_MEDIA_TYPE not in {
        HISTORICAL_SOURCE_MANIFEST_MEDIA_TYPE
    }


def test_exact_public_carrier_types_are_frozen_and_distinct() -> None:
    assert HistoricalEvidenceImportArtifact is not EvidencePacketArtifact
    assert HistoricalEvidenceRecord is not HistoricalSourceFileSnapshot
