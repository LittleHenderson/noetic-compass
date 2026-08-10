from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.artifacts import EvidenceFile
import cas_harness_v2.diagnostic_stagec_prerequisite_admission as admission
import cas_harness_v2.diagnostic_stagec_prerequisite_external_intake as sut
from tests.cas_harness_v2.test_diagnostic_stagec_prerequisite_admission import (
    build_fx,
)


_FX = None


@pytest.fixture
def fx(monkeypatch):
    global _FX
    monkeypatch.setattr(
        admission,
        "_utc_now",
        lambda: datetime(2026, 8, 9, 9, 30, tzinfo=timezone.utc),
    )
    if _FX is None:
        _FX = build_fx()
    return _FX


def _ref_value(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _role_bodies(fx) -> dict[str, tuple[ArtifactRef, bytes]]:
    result = {
        "detector_drc": (fx.drc.artifact_ref, fx.drc.raw_bytes),
        "frozen_corpus": (fx.corpus.artifact_ref, fx.corpus.raw_bytes),
        "trusted_storage": (fx.storage.artifact_ref, fx.storage.raw_bytes),
        "execution_authorization": (
            fx.authorization.artifact_ref,
            fx.authorization.raw_bytes,
        ),
    }
    groups = (
        (("drc_profile", "detector_ruleset", "known_fault_fixture"), fx.drc),
        (
            ("corpus_rows", "adjudication", "split_assignment", "surface_bundle"),
            fx.corpus,
        ),
        (
            (
                "object_lock_receipt",
                "readback_receipt",
                "trusted_time_receipt",
                "verifier_identity",
            ),
            fx.storage,
        ),
        (("authorization_instrument",), fx.authorization),
    )
    for names, carrier in groups:
        for name, body in zip(names, carrier.artifact_bodies, strict=True):
            result[name] = body
    assert set(result) == set(sut.STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER)
    return result


def _write_kit(root: Path, fx, *, path_prefix: str = "payload") -> dict[str, object]:
    bodies = _role_bodies(fx)
    artifacts: dict[str, object] = {}
    for index, role in enumerate(sut.STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER, start=1):
        relative_path = f"{path_prefix}/{index:02d}-{role}.json"
        target = root.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        reference, raw_bytes = bodies[role]
        target.write_bytes(raw_bytes)
        artifacts[role] = {
            "relative_path": relative_path,
            "artifact_ref": _ref_value(reference),
        }
    manifest = {
        "schema_version": sut.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_SCHEMA,
        "target_binding_sha256": fx.context.target_binding_sha256,
        "artifacts": artifacts,
    }
    (root / sut.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME).write_bytes(
        canonical_json_bytes(manifest)
    )
    return manifest


def _write_manifest(root: Path, value: dict[str, object]) -> None:
    (root / sut.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME).write_bytes(
        canonical_json_bytes(value)
    )


def _mutate_carrier(root: Path, manifest: dict[str, object], role: str) -> None:
    entry = manifest["artifacts"][role]
    target = root.joinpath(*entry["relative_path"].split("/"))
    value = json.loads(target.read_bytes())
    value["domain"] = "WRONG_STAGE_C_DOMAIN"
    raw_bytes = canonical_json_bytes(value)
    target.write_bytes(raw_bytes)
    entry["artifact_ref"]["sha256"] = sha256_bytes(raw_bytes)
    entry["artifact_ref"]["byte_length"] = len(raw_bytes)
    _write_manifest(root, manifest)


def test_success_is_deterministic_detached_and_binding_is_caller_supplied(
    tmp_path: Path, fx
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_kit(first, fx)
    _write_kit(second, fx)
    snapshot = sut.load_stagec_external_prerequisite_snapshot(first, context=fx.context)
    repeated = sut.load_stagec_external_prerequisite_snapshot(second, context=fx.context)

    assert len(snapshot.roles) == 16
    assert snapshot.report_raw_bytes == repeated.report_raw_bytes
    assert snapshot.report_sha256 == repeated.report_sha256
    assert snapshot.report["status"] == sut.STAGEC_EXTERNAL_PREREQUISITE_IMPORT_SUCCESS
    assert snapshot.report["error_code"] == "NONE"
    assert snapshot.report["external_trust_authentication"] == "NOT_ESTABLISHED"
    assert snapshot.report["runtime_authorization"] == "NOT_GRANTED_BY_IMPORTER"
    assert b"relative_path" not in snapshot.report_raw_bytes
    assert snapshot.report_raw_bytes == canonical_json_bytes(snapshot.report)
    with pytest.raises(TypeError):
        snapshot.report["status"] = "FORGED"

    for item in snapshot.roles:
        first.joinpath(*item.relative_path.split("/")).write_bytes(b"changed")
    binding = sut.load_stagec_external_prerequisite_binding(
        snapshot,
        context=fx.context,
        replay_bundles=fx.bundles,
        intake_bytes=fx.intake.raw_bytes,
        admission_bytes=fx.admission.raw_bytes,
    )
    assert binding.intake.artifact_ref == fx.intake.artifact_ref
    assert binding.admission.artifact_ref == fx.admission.artifact_ref
    assert binding.report["runtime_authorization"] == "NOT_GRANTED_BY_IMPORTER"


@pytest.mark.parametrize(
    ("role", "error_code"),
    (
        ("detector_drc", "DRC_REPLAY_FAILED"),
        ("frozen_corpus", "CORPUS_REPLAY_FAILED"),
        ("trusted_storage", "STORAGE_REPLAY_FAILED"),
        ("execution_authorization", "AUTHORIZATION_REPLAY_FAILED"),
    ),
)
def test_each_semantic_replay_stage_has_a_closed_error_code(
    tmp_path: Path, fx, role: str, error_code: str
) -> None:
    root = tmp_path / role
    manifest = _write_kit(root, fx)
    _mutate_carrier(root, manifest, role)
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as observed:
        sut.load_stagec_external_prerequisite_snapshot(root, context=fx.context)
    assert observed.value.error_code == error_code


@pytest.mark.parametrize(
    "bad_path",
    ("../escape.json", "/absolute.json", "C:/absolute.json", "CON.json", "foo."),
)
def test_unsafe_paths_fail_before_file_access(tmp_path: Path, fx, bad_path: str) -> None:
    root = tmp_path / "kit"
    manifest = _write_kit(root, fx)
    manifest["artifacts"]["detector_drc"]["relative_path"] = bad_path
    _write_manifest(root, manifest)
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as observed:
        sut.load_stagec_external_prerequisite_snapshot(root, context=fx.context)
    assert observed.value.error_code == "RELATIVE_PATH_INVALID"


def test_role_path_ref_and_target_mismatches_fail_closed(tmp_path: Path, fx) -> None:
    cases = []
    for name in ("missing", "extra", "case_collision", "swapped", "target"):
        root = tmp_path / name
        manifest = _write_kit(root, fx)
        if name == "missing":
            del manifest["artifacts"]["drc_profile"]
            expected = "ROLE_SET_INVALID"
        elif name == "extra":
            manifest["artifacts"]["unexpected"] = manifest["artifacts"]["drc_profile"]
            expected = "ROLE_SET_INVALID"
        elif name == "case_collision":
            first = manifest["artifacts"]["detector_drc"]["relative_path"]
            manifest["artifacts"]["drc_profile"]["relative_path"] = first.swapcase()
            expected = "PATH_COLLISION"
        elif name == "swapped":
            left = manifest["artifacts"]["detector_drc"]
            right = manifest["artifacts"]["frozen_corpus"]
            left["relative_path"], right["relative_path"] = (
                right["relative_path"],
                left["relative_path"],
            )
            expected = "ARTIFACT_BYTES_MISMATCH"
        else:
            manifest["target_binding_sha256"] = "F" * 64
            expected = "MANIFEST_TARGET_MISMATCH"
        _write_manifest(root, manifest)
        cases.append((root, expected))
    for root, expected in cases:
        with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as observed:
            sut.load_stagec_external_prerequisite_snapshot(root, context=fx.context)
        assert observed.value.error_code == expected


def test_global_context_collision_and_carrier_id_alias_are_rejected(
    tmp_path: Path, fx
) -> None:
    collision_root = tmp_path / "collision"
    manifest = _write_kit(collision_root, fx)
    manifest["artifacts"]["drc_profile"]["artifact_ref"]["artifact_id"] = (
        fx.split.artifact_ref.artifact_id
    )
    _write_manifest(collision_root, manifest)
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as collision:
        sut.load_stagec_external_prerequisite_snapshot(
            collision_root, context=fx.context
        )
    assert collision.value.error_code == "ARTIFACT_REFERENCE_INVALID"

    alias_root = tmp_path / "alias"
    manifest = _write_kit(alias_root, fx)
    manifest["artifacts"]["detector_drc"]["artifact_ref"]["artifact_id"] = (
        "stagec-detector-drc-alias-001"
    )
    _write_manifest(alias_root, manifest)
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as alias:
        sut.load_stagec_external_prerequisite_snapshot(alias_root, context=fx.context)
    assert alias.value.error_code == "ARTIFACT_REFERENCE_INVALID"


def test_hardlink_and_during_collection_change_are_rejected(
    tmp_path: Path, fx, monkeypatch
) -> None:
    hardlink_root = tmp_path / "hardlink"
    manifest = _write_kit(hardlink_root, fx)
    entry = manifest["artifacts"]["detector_drc"]
    target = hardlink_root.joinpath(*entry["relative_path"].split("/"))
    os.link(target, hardlink_root / "alias.json")
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as hardlink:
        sut.load_stagec_external_prerequisite_snapshot(
            hardlink_root, context=fx.context
        )
    assert hardlink.value.error_code == "FILE_SNAPSHOT_INVALID"

    changing_root = tmp_path / "changing"
    _write_kit(changing_root, fx)
    original = EvidenceFile.snapshot_bytes
    changed = False

    def sabotaged(self, *, maximum_byte_count):
        nonlocal changed
        result = original(self, maximum_byte_count=maximum_byte_count)
        if not changed and self.artifact_id.endswith("detector_drc"):
            changed = True
            self.path.write_bytes(result.raw_bytes + b" ")
        return result

    monkeypatch.setattr(EvidenceFile, "snapshot_bytes", sabotaged)
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as changing:
        sut.load_stagec_external_prerequisite_snapshot(
            changing_root, context=fx.context
        )
    assert changing.value.error_code == "FILE_SNAPSHOT_INVALID"


def test_report_artifact_ids_are_content_derived(tmp_path: Path, fx) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_kit(first, fx, path_prefix="one")
    _write_kit(second, fx, path_prefix="two")
    left = sut.load_stagec_external_prerequisite_snapshot(first, context=fx.context)
    right = sut.load_stagec_external_prerequisite_snapshot(second, context=fx.context)
    assert left.manifest_artifact_ref.artifact_id != right.manifest_artifact_ref.artifact_id
    assert left.report_artifact_ref.artifact_id != right.report_artifact_ref.artifact_id
    assert left.report_artifact_ref.artifact_id.endswith(left.report_sha256.lower())


def test_mapping_source_and_snapshot_tamper_fail_closed(tmp_path: Path, fx) -> None:
    root = tmp_path / "mapping"
    manifest = _write_kit(root, fx)
    relative_paths = {
        sut.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME,
        *(
            entry["relative_path"]
            for entry in manifest["artifacts"].values()
        ),
    }
    sources = {
        relative_path: EvidenceFile.from_path(
            f"mapping-source-{index:02d}",
            root.joinpath(*relative_path.split("/")),
        )
        for index, relative_path in enumerate(sorted(relative_paths), start=1)
    }
    snapshot = sut.load_stagec_external_prerequisite_snapshot(
        sources, context=fx.context
    )
    role = snapshot.role_snapshot("drc_profile")
    object.__setattr__(role, "relative_path", "payload/forged.json")
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as tampered:
        sut.load_stagec_external_prerequisite_binding(
            snapshot,
            context=fx.context,
            replay_bundles=fx.bundles,
            intake_bytes=fx.intake.raw_bytes,
            admission_bytes=fx.admission.raw_bytes,
        )
    assert tampered.value.error_code == "SNAPSHOT_INVALID"


def test_binding_rejects_nonbytes_and_different_caller_admission(
    tmp_path: Path, fx
) -> None:
    root = tmp_path / "binding"
    _write_kit(root, fx)
    snapshot = sut.load_stagec_external_prerequisite_snapshot(root, context=fx.context)
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as nonbytes:
        sut.load_stagec_external_prerequisite_binding(
            snapshot,
            context=fx.context,
            replay_bundles=fx.bundles,
            intake_bytes=bytearray(fx.intake.raw_bytes),
            admission_bytes=fx.admission.raw_bytes,
        )
    assert nonbytes.value.error_code == "CALLER_BINDING_INVALID"

    value = json.loads(fx.admission.raw_bytes)
    value["domain"] = "WRONG_CALLER_ADMISSION_DOMAIN"
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as changed:
        sut.load_stagec_external_prerequisite_binding(
            snapshot,
            context=fx.context,
            replay_bundles=fx.bundles,
            intake_bytes=fx.intake.raw_bytes,
            admission_bytes=canonical_json_bytes(value),
        )
    assert changed.value.error_code == "CALLER_BINDING_REPLAY_FAILED"


@pytest.mark.skipif(os.name != "nt", reason="NTFS alternate data streams are Windows-only")
def test_evidence_file_rejects_ntfs_alternate_data_stream(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    base.write_bytes(b"base")
    alternate = Path(str(base) + ":stagec")
    try:
        alternate.write_bytes(b"stream")
    except OSError as exc:
        pytest.skip(f"NTFS alternate data streams unavailable: {exc}")
    with pytest.raises(SchemaValidationError, match="alternate data stream"):
        EvidenceFile.from_path("stagec-ads-source", alternate)


def test_mapping_remote_path_manifest_collision_and_size_bound_fail_closed(
    tmp_path: Path, fx
) -> None:
    remote_root = tmp_path / "remote"
    manifest = _write_kit(remote_root, fx)
    relative_paths = {
        sut.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME,
        *(entry["relative_path"] for entry in manifest["artifacts"].values()),
    }
    sources = {
        relative_path: EvidenceFile.from_path(
            f"remote-source-{index:02d}",
            remote_root.joinpath(*relative_path.split("/")),
        )
        for index, relative_path in enumerate(sorted(relative_paths), start=1)
    }
    if os.name == "nt":
        object.__setattr__(
            sources[sut.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME],
            "path",
            Path(r"\\server\share\manifest.json"),
        )
        with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as remote:
            sut.load_stagec_external_prerequisite_snapshot(
                sources, context=fx.context
            )
        assert remote.value.error_code == "SOURCE_INVALID"

    collision_root = tmp_path / "manifest-collision"
    manifest = _write_kit(collision_root, fx)
    manifest["artifacts"]["detector_drc"]["relative_path"] = (
        sut.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME
    )
    _write_manifest(collision_root, manifest)
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as collision:
        sut.load_stagec_external_prerequisite_snapshot(
            collision_root, context=fx.context
        )
    assert collision.value.error_code == "PATH_COLLISION"

    large_root = tmp_path / "large"
    manifest = _write_kit(large_root, fx)
    entry = manifest["artifacts"]["detector_drc"]
    target = large_root.joinpath(*entry["relative_path"].split("/"))
    with target.open("wb") as handle:
        handle.truncate(sut.STAGEC_EXTERNAL_PREREQUISITE_MAXIMUM_FILE_BYTES + 1)
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as large:
        sut.load_stagec_external_prerequisite_snapshot(large_root, context=fx.context)
    assert large.value.error_code == "FILE_SNAPSHOT_INVALID"


def test_noncanonical_manifest_and_symlink_are_rejected(tmp_path: Path, fx) -> None:
    noncanonical_root = tmp_path / "noncanonical"
    manifest = _write_kit(noncanonical_root, fx)
    path = noncanonical_root / sut.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME
    path.write_bytes(json.dumps(manifest, indent=2).encode("utf-8"))
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as noncanonical:
        sut.load_stagec_external_prerequisite_snapshot(
            noncanonical_root, context=fx.context
        )
    assert noncanonical.value.error_code == "MANIFEST_INVALID"

    link_root = tmp_path / "symlink"
    manifest = _write_kit(link_root, fx)
    entry = manifest["artifacts"]["detector_drc"]
    link = link_root.joinpath(*entry["relative_path"].split("/"))
    target = link.with_name("real-detector.json")
    link.replace(target)
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symbolic links unavailable: {exc}")
    with pytest.raises(sut.StageCExternalPrerequisiteIntakeError) as symlink:
        sut.load_stagec_external_prerequisite_snapshot(link_root, context=fx.context)
    assert symlink.value.error_code == "FILE_SNAPSHOT_INVALID"
