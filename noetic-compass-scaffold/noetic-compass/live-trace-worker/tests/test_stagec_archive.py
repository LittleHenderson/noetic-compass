"""Fake-only durability and adversarial tests for the Stage C local archive.

These tests reuse the tiny Stage C fake model carrier.  They perform no real
model-file load, provider call, Docker/HTTP activity, generation, intervention,
or authorized Stage C execution.
"""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import stat
from typing import Any

import pytest

from app.runtime import model_loader, stagec_archive
from app.runtime.stagec_archive import (
    DIRECTORY_FSYNC_PERFORMED,
    DIRECTORY_FSYNC_UNAVAILABLE,
    LOCAL_ARCHIVE_AUTHORITY,
    MANIFEST_MEMBERSHIP_BOUNDARY,
    MANIFEST_PUBLICATION_BOUNDARY,
    RELOCATABILITY_BOUNDARY,
    SOURCE_RETENTION_BOUNDARY,
    STAGEC_ARCHIVE_MEMBER_ROLES,
    STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME,
    STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE,
    STAGEC_LOCAL_ARCHIVE_SCHEMA,
    StageCArchiveConflict,
    StageCArchiveError,
    StageCArchivedCapture,
    StageCLocalArchiveReceipt,
    load_stagec_capture_archive,
    retain_stagec_capture,
)
from app.runtime.stagec_capture import (
    IN_MEMORY_LOCATION,
    NOT_DURABLY_RETAINED,
    ArtifactIdentity,
)
from tests.test_stagec_capture import _capture


_WRITE_BITS = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH


@pytest.fixture(autouse=True)
def _select_qwen_and_make_read_only_archive_files_cleanup_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    yield
    for path in sorted(tmp_path.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        try:
            if path.is_symlink():
                continue
            os.chmod(path, 0o700 if path.is_dir() else 0o600)
        except OSError:
            pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _manifest_payload(root: Path) -> dict[str, Any]:
    value = json.loads(
        (root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME).read_text(encoding="utf-8")
    )
    assert type(value) is dict
    return value


def _replace_manifest(
    root: Path,
    payload: dict[str, Any],
    *,
    artifact_id: str,
) -> ArtifactIdentity:
    raw = _canonical_bytes(payload)
    path = root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME
    os.chmod(path, 0o600)
    path.write_bytes(raw)
    os.chmod(path, 0o444)
    return ArtifactIdentity(
        artifact_id=artifact_id,
        sha256=sha256(raw).hexdigest().upper(),
        byte_length=len(raw),
        media_type=STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE,
    )


def _created_archive(tmp_path: Path):
    result = _capture()
    root = tmp_path / "stagec-archive"
    receipt = retain_stagec_capture(result, root)
    loaded = load_stagec_capture_archive(
        root,
        expected_manifest_ref=receipt.manifest_ref,
    )
    return result, root, receipt, loaded


def test_manifest_last_archive_retains_all_seven_exact_artifacts_and_association(
    tmp_path: Path,
) -> None:
    result, root, receipt, loaded = _created_archive(tmp_path)
    payload = _manifest_payload(root)

    assert payload["schema_version"] == STAGEC_LOCAL_ARCHIVE_SCHEMA
    assert payload["authority"] == dict(LOCAL_ARCHIVE_AUTHORITY)
    assert payload["source_retention_boundary"] == SOURCE_RETENTION_BOUNDARY
    assert payload["relocatability_boundary"] == RELOCATABILITY_BOUNDARY
    assert payload["manifest_membership_boundary"] == MANIFEST_MEMBERSHIP_BOUNDARY
    assert payload["manifest_publication_boundary"] == MANIFEST_PUBLICATION_BOUNDARY
    assert payload["member_directory_fsync_status"] in {
        DIRECTORY_FSYNC_PERFORMED,
        DIRECTORY_FSYNC_UNAVAILABLE,
    }
    assert "manifest_ref" not in payload
    assert tuple(row["role"] for row in payload["members"]) == (
        STAGEC_ARCHIVE_MEMBER_ROLES
    )
    assert payload["association"] == {
        name: result.index.association[name]
        for name in (
            "study_id",
            "case_id",
            "split_id",
            "base_intent_group_id",
            "frozen_variant",
            "frozen_label",
            "invocation_id",
            "plan_id",
        )
    }
    assert receipt.manifest_ref == loaded.manifest_artifact.ref
    assert dict(receipt.association) == payload["association"]
    assert receipt.to_payload()["association"] == payload["association"]
    assert loaded.index.to_payload() == result.index.to_payload()
    assert loaded.request_artifact.raw_bytes == result.request_artifact.raw_bytes
    assert (
        loaded.authorization_projection_artifact.raw_bytes
        == result.authorization_projection_artifact.raw_bytes
    )
    assert loaded.index_artifact.raw_bytes == result.index_artifact.raw_bytes
    assert loaded.input_ids.raw_bytes == result.input_ids.raw_bytes
    assert loaded.attention_mask.raw_bytes == result.attention_mask.raw_bytes
    assert loaded.target_vector.raw_bytes == result.target_vector.raw_bytes
    assert loaded.wrong_layer_vector.raw_bytes == result.wrong_layer_vector.raw_bytes
    assert receipt.to_payload()["authority"]["worm_authority"] == "NOT_ESTABLISHED"


def test_archive_preserves_capture_time_in_memory_refs_but_binds_local_copies(
    tmp_path: Path,
) -> None:
    _, root, _, loaded = _created_archive(tmp_path)
    payload = _manifest_payload(root)

    for role in ("input_ids", "attention_mask", "target_vector", "wrong_layer_vector"):
        row = next(item for item in payload["members"] if item["role"] == role)
        assert row["ref"]["retention_location"] == IN_MEMORY_LOCATION
        assert row["ref"]["durability_status"] == NOT_DURABLY_RETAINED
        assert row["archive_copy_status"] == (
            "LOCAL_FILE_COPY_RETAINED_AND_REVALIDATED"
        )
        path = loaded.member_paths[role]
        assert path.is_file()
        assert os.lstat(path).st_mode & _WRITE_BITS == 0


def test_restart_loader_uses_artifact_replay_not_process_local_result_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _capture()
    root = tmp_path / "restart-archive"
    receipt = retain_stagec_capture(result, root)

    def process_local_replay_must_not_run(_result: object):
        raise AssertionError("restart loader used process-local result provenance")

    monkeypatch.setattr(
        stagec_archive,
        "replay_stagec_capture_result",
        process_local_replay_must_not_run,
    )
    loaded = load_stagec_capture_archive(
        root,
        expected_manifest_ref=receipt.manifest_ref,
    )
    assert loaded.index.to_payload() == result.index.to_payload()
    assert loaded.authority["capture_provenance"] == (
        "NOT_CONFERRED_BY_ARCHIVE_REPLAY"
    )


def test_partial_failure_leaves_no_manifest_and_same_root_cannot_be_repaired(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _capture()
    root = tmp_path / "partial-archive"
    original = stagec_archive._write_create_only_file
    calls = 0

    def fail_during_member_write(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("injected partial archive failure")
        return original(**kwargs)

    monkeypatch.setattr(
        stagec_archive,
        "_write_create_only_file",
        fail_during_member_write,
    )
    with pytest.raises(RuntimeError, match="injected partial"):
        retain_stagec_capture(result, root)
    assert root.is_dir()
    assert not (root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME).exists()
    assert any(path.is_file() for path in (root / "objects").rglob("*"))

    monkeypatch.setattr(stagec_archive, "_write_create_only_file", original)
    with pytest.raises(StageCArchiveConflict, match="root already exists"):
        retain_stagec_capture(result, root)


def test_file_fsync_failure_leaves_no_completion_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "fsync-failure-archive"
    real_fsync = stagec_archive.os.fsync

    def fail_regular_file_fsync(descriptor: int) -> None:
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("injected regular-file fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(stagec_archive.os, "fsync", fail_regular_file_fsync)
    with pytest.raises(OSError, match="regular-file fsync"):
        retain_stagec_capture(_capture(), root)

    assert root.is_dir()
    assert not (root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME).exists()


def test_existing_archive_root_is_a_create_only_conflict(tmp_path: Path) -> None:
    root = tmp_path / "existing"
    root.mkdir()
    sentinel = root / "user-owned.txt"
    sentinel.write_text("preserve", encoding="utf-8")

    with pytest.raises(StageCArchiveConflict, match="root already exists"):
        retain_stagec_capture(_capture(), root)
    assert sentinel.read_text(encoding="utf-8") == "preserve"
    assert list(root.iterdir()) == [sentinel]


def test_member_byte_mutation_fails_identity_or_hash_revalidation(tmp_path: Path) -> None:
    _, root, receipt, loaded = _created_archive(tmp_path)
    target = loaded.member_paths["target_vector"]
    raw = bytearray(target.read_bytes())
    raw[17] ^= 0x01
    os.chmod(target, 0o600)
    target.write_bytes(bytes(raw))
    os.chmod(target, 0o444)

    with pytest.raises(StageCArchiveError, match="identity|SHA-256|byte"):
        load_stagec_capture_archive(root, expected_manifest_ref=receipt.manifest_ref)


def test_read_only_permission_drift_fails_even_when_bytes_match(tmp_path: Path) -> None:
    _, root, receipt, loaded = _created_archive(tmp_path)
    target = loaded.member_paths["attention_mask"]
    os.chmod(target, 0o600)
    if os.lstat(target).st_mode & _WRITE_BITS == 0:
        pytest.skip("platform chmod did not expose writable permission bits")

    with pytest.raises(StageCArchiveError, match="read-only permission"):
        load_stagec_capture_archive(root, expected_manifest_ref=receipt.manifest_ref)


def test_manifest_byte_tampering_fails_expected_ref_before_semantic_replay(
    tmp_path: Path,
) -> None:
    _, root, receipt, _ = _created_archive(tmp_path)
    path = root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME
    raw = bytearray(path.read_bytes())
    raw[-2] ^= 0x01
    os.chmod(path, 0o600)
    path.write_bytes(bytes(raw))
    os.chmod(path, 0o444)

    with pytest.raises(StageCArchiveError, match="SHA-256|byte length"):
        load_stagec_capture_archive(root, expected_manifest_ref=receipt.manifest_ref)


@pytest.mark.parametrize(
    ("field", "promoted_value"),
    [
        ("worm_authority", "ESTABLISHED"),
        ("trusted_time", "ESTABLISHED"),
        ("external_anchor", "ESTABLISHED"),
        ("capture_provenance", "AUTHENTICATED_CAPTURE"),
        ("execution_authority", "GRANTED"),
    ],
)
def test_direct_provenance_or_authority_overclaim_is_rejected_even_when_rehashed(
    tmp_path: Path,
    field: str,
    promoted_value: str,
) -> None:
    _, root, receipt, _ = _created_archive(tmp_path)
    payload = _manifest_payload(root)
    payload["authority"][field] = promoted_value
    forged_ref = _replace_manifest(
        root,
        payload,
        artifact_id=receipt.manifest_ref.artifact_id,
    )

    with pytest.raises(StageCArchiveError, match="authority overclaims"):
        load_stagec_capture_archive(root, expected_manifest_ref=forged_ref)


@pytest.mark.parametrize(
    "mutation",
    [
        "association",
        "request_auth_ref_swap",
        "array_ref_swap",
        "row_order",
        "missing_row",
    ],
)
def test_association_ref_and_order_swaps_fail_closed(
    tmp_path: Path,
    mutation: str,
) -> None:
    _, root, receipt, _ = _created_archive(tmp_path)
    payload = _manifest_payload(root)
    if mutation == "association":
        payload["association"]["case_id"] = "stagec-case-substituted"
    elif mutation == "request_auth_ref_swap":
        request = payload["members"][0]
        authorization = payload["members"][1]
        for field in (
            "ref",
            "relative_path",
            "file_identity",
            "path_ancestors",
        ):
            request[field], authorization[field] = authorization[field], request[field]
    elif mutation == "array_ref_swap":
        target = payload["members"][5]
        wrong = payload["members"][6]
        for field in (
            "ref",
            "relative_path",
            "file_identity",
            "path_ancestors",
        ):
            target[field], wrong[field] = wrong[field], target[field]
    elif mutation == "row_order":
        payload["members"][5], payload["members"][6] = (
            payload["members"][6],
            payload["members"][5],
        )
    else:
        payload["members"].pop()
    forged_ref = _replace_manifest(
        root,
        payload,
        artifact_id=receipt.manifest_ref.artifact_id,
    )

    with pytest.raises(
        StageCArchiveError,
        match="association|media type|index role|role order|role/layer|exactly seven",
    ):
        load_stagec_capture_archive(root, expected_manifest_ref=forged_ref)


def test_manifest_relative_path_escape_is_rejected_even_when_rehashed(
    tmp_path: Path,
) -> None:
    _, root, receipt, _ = _created_archive(tmp_path)
    payload = _manifest_payload(root)
    payload["members"][0]["relative_path"] = "../outside"
    forged_ref = _replace_manifest(
        root,
        payload,
        artifact_id=receipt.manifest_ref.artifact_id,
    )

    with pytest.raises(StageCArchiveError, match="safe canonical relative path"):
        load_stagec_capture_archive(root, expected_manifest_ref=forged_ref)


def test_member_hard_link_alias_is_rejected_where_supported(tmp_path: Path) -> None:
    _, root, receipt, loaded = _created_archive(tmp_path)
    target = loaded.member_paths["input_ids"]
    alias = root / "hard-link-alias"
    try:
        os.link(target, alias)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"hard links unavailable: {exc}")

    with pytest.raises(StageCArchiveError, match="hard-link"):
        load_stagec_capture_archive(root, expected_manifest_ref=receipt.manifest_ref)


def test_member_symlink_or_windows_reparse_substitution_is_rejected_where_supported(
    tmp_path: Path,
) -> None:
    _, root, receipt, loaded = _created_archive(tmp_path)
    target = loaded.member_paths["wrong_layer_vector"]
    external = tmp_path / "same-bytes-external.bin"
    external.write_bytes(target.read_bytes())
    os.chmod(target, 0o600)
    target.unlink()
    try:
        os.symlink(external, target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symbolic links/reparse points unavailable: {exc}")

    with pytest.raises(StageCArchiveError, match="symbolic link|reparse"):
        load_stagec_capture_archive(root, expected_manifest_ref=receipt.manifest_ref)


def test_manifest_self_reference_and_wrong_expected_ref_type_fail_closed(
    tmp_path: Path,
) -> None:
    _, root, receipt, _ = _created_archive(tmp_path)
    payload = _manifest_payload(root)
    payload["manifest_ref"] = receipt.manifest_ref.to_payload()
    forged_ref = _replace_manifest(
        root,
        payload,
        artifact_id=receipt.manifest_ref.artifact_id,
    )
    with pytest.raises(StageCArchiveError, match="keys drifted"):
        load_stagec_capture_archive(root, expected_manifest_ref=forged_ref)

    with pytest.raises(StageCArchiveError, match="exact ArtifactIdentity"):
        load_stagec_capture_archive(
            root,
            expected_manifest_ref=receipt.manifest_ref.to_payload(),  # type: ignore[arg-type]
        )


def test_manifest_ref_id_is_bound_to_full_capture_index_reference(tmp_path: Path) -> None:
    _, root, receipt, _ = _created_archive(tmp_path)
    wrong = ArtifactIdentity(
        artifact_id="stagec-local-archive-forged-id",
        sha256=receipt.manifest_ref.sha256,
        byte_length=receipt.manifest_ref.byte_length,
        media_type=receipt.manifest_ref.media_type,
    )
    with pytest.raises(StageCArchiveError, match="artifact ID is not bound"):
        load_stagec_capture_archive(root, expected_manifest_ref=wrong)


def test_archive_root_symlink_is_rejected_without_following_it(tmp_path: Path) -> None:
    actual = tmp_path / "actual-root"
    actual.mkdir()
    link = tmp_path / "archive-link"
    try:
        os.symlink(actual, link, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symbolic links/reparse points unavailable: {exc}")

    with pytest.raises(StageCArchiveConflict, match="root already exists"):
        retain_stagec_capture(_capture(), link)
    assert list(actual.iterdir()) == []


def test_archive_carriers_require_factories_and_freeze_all_public_mappings(
    tmp_path: Path,
) -> None:
    with pytest.raises(StageCArchiveError, match="retention factory"):
        StageCLocalArchiveReceipt()
    with pytest.raises(StageCArchiveError, match="strict loader"):
        StageCArchivedCapture()
    with pytest.raises(StageCArchiveError, match="strict loaded archive"):
        stagec_archive._new_local_archive_receipt(
            loaded_archive=None,  # type: ignore[arg-type]
            manifest_parent_directory_fsync_status=DIRECTORY_FSYNC_PERFORMED,
        )
    with pytest.raises(StageCArchiveError, match="manifest has the wrong exact type"):
        stagec_archive._new_archived_capture(
            root=tmp_path,
            manifest_artifact=None,  # type: ignore[arg-type]
            index_artifact=None,  # type: ignore[arg-type]
            request_artifact=None,  # type: ignore[arg-type]
            authorization_projection_artifact=None,  # type: ignore[arg-type]
            input_ids=None,  # type: ignore[arg-type]
            attention_mask=None,  # type: ignore[arg-type]
            target_vector=None,  # type: ignore[arg-type]
            wrong_layer_vector=None,  # type: ignore[arg-type]
            index=None,  # type: ignore[arg-type]
            member_paths={},
        )

    _, _, receipt, loaded = _created_archive(tmp_path)
    receipt_payload = receipt.to_payload()
    receipt_payload["association"]["case_id"] = "changed-copy"
    receipt_payload["authority"]["worm_authority"] = "changed-copy"
    assert receipt.association["case_id"] != "changed-copy"
    assert receipt.authority["worm_authority"] == "NOT_ESTABLISHED"
    with pytest.raises(TypeError):
        receipt.association["case_id"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        receipt.authority["worm_authority"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        loaded.member_paths["target_vector"] = tmp_path  # type: ignore[index]
    with pytest.raises(TypeError):
        loaded.authority["capture_provenance"] = "changed"  # type: ignore[index]


def test_held_parent_identity_keeps_creation_bound_to_the_checked_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "held-parent"
    parent.mkdir()
    parked = tmp_path / "held-parent-parked"
    root = parent / "archive"
    original = stagec_archive._create_directory
    replacement_completed = False
    attempted = False

    def attempt_parent_replacement(path: Path, *, session: object):
        nonlocal attempted, replacement_completed
        if path == root and not attempted:
            attempted = True
            try:
                parent.rename(parked)
                parent.mkdir()
                replacement_completed = True
            except OSError:
                replacement_completed = False
        return original(path, session=session)

    monkeypatch.setattr(
        stagec_archive,
        "_create_directory",
        attempt_parent_replacement,
    )
    try:
        receipt = retain_stagec_capture(_capture(), root)
    except StageCArchiveError as exc:
        assert attempted
        assert replacement_completed
        assert "held archive directory" in str(exc)
        assert not root.exists()
        assert not (parked / "archive").exists()
    else:
        assert attempted
        assert not replacement_completed
        assert receipt.root == root
        assert not parked.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-relative regression")
def test_windows_handle_relative_create_does_not_use_a_replacement_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "relative-parent"
    parent.mkdir()
    parked = tmp_path / "relative-parent-held"
    root = parent / "archive"
    original = stagec_archive._windows_relative_descriptor
    replacement_completed = False

    def replace_after_parent_check(
        parent_descriptor: int,
        name: str,
        *,
        directory: bool,
        create: bool,
    ):
        nonlocal replacement_completed
        if directory and create and name == root.name and not replacement_completed:
            parent.rename(parked)
            parent.mkdir()
            replacement_completed = True
        return original(
            parent_descriptor,
            name,
            directory=directory,
            create=create,
        )

    monkeypatch.setattr(
        stagec_archive,
        "_windows_relative_descriptor",
        replace_after_parent_check,
    )
    with pytest.raises(StageCArchiveError, match="held archive directory identity drifted"):
        retain_stagec_capture(_capture(), root)

    assert replacement_completed
    assert not root.exists()
    assert list(parent.iterdir()) == []
    held_root = parked / "archive"
    assert held_root.is_dir()
    assert list(held_root.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows handle-relative regression")
def test_windows_handle_relative_load_does_not_read_a_replacement_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, root, receipt, _ = _created_archive(tmp_path)
    parked = tmp_path / "archive-held-during-load"
    original = stagec_archive._windows_relative_descriptor
    replacement_completed = False

    def replace_before_manifest_open(
        parent_descriptor: int,
        name: str,
        *,
        directory: bool,
        create: bool,
    ):
        nonlocal replacement_completed
        if (
            not directory
            and not create
            and name == STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME
            and not replacement_completed
        ):
            root.rename(parked)
            root.mkdir()
            (root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME).write_bytes(
                b"replacement bytes must not be consumed"
            )
            replacement_completed = True
        return original(
            parent_descriptor,
            name,
            directory=directory,
            create=create,
        )

    monkeypatch.setattr(
        stagec_archive,
        "_windows_relative_descriptor",
        replace_before_manifest_open,
    )
    with pytest.raises(StageCArchiveError, match="held archive directory identity drifted"):
        load_stagec_capture_archive(
            root,
            expected_manifest_ref=receipt.manifest_ref,
        )

    assert replacement_completed
    assert (parked / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME).is_file()
    assert (root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME).read_bytes() == (
        b"replacement bytes must not be consumed"
    )


def test_stop_before_manifest_publication_leaves_no_final_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "before-publication"
    original = stagec_archive._write_create_only_file

    def stop_before_publication(**kwargs):
        if kwargs["relative_path"] == STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME:
            raise RuntimeError("injected before manifest publication")
        return original(**kwargs)

    monkeypatch.setattr(
        stagec_archive,
        "_write_create_only_file",
        stop_before_publication,
    )
    with pytest.raises(RuntimeError, match="before manifest publication"):
        retain_stagec_capture(_capture(), root)
    assert root.is_dir()
    assert not (root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME).exists()
    assert any(path.is_file() for path in (root / "objects").rglob("*"))


def test_stop_after_manifest_publication_leaves_a_replayable_local_orphan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _capture()
    root = tmp_path / "after-publication"
    original_loader = stagec_archive.load_stagec_capture_archive

    def stop_after_publication(*_args, **_kwargs):
        raise RuntimeError("injected after manifest publication")

    monkeypatch.setattr(
        stagec_archive,
        "load_stagec_capture_archive",
        stop_after_publication,
    )
    with pytest.raises(RuntimeError, match="after manifest publication"):
        retain_stagec_capture(result, root)

    manifest_path = root / STAGEC_LOCAL_ARCHIVE_MANIFEST_NAME
    assert manifest_path.is_file()
    assert os.lstat(manifest_path).st_mode & _WRITE_BITS == 0
    manifest_bytes = manifest_path.read_bytes()
    reconstructed_ref = ArtifactIdentity(
        artifact_id=stagec_archive._manifest_artifact_id(result.index_artifact.ref),
        sha256=sha256(manifest_bytes).hexdigest().upper(),
        byte_length=len(manifest_bytes),
        media_type=STAGEC_LOCAL_ARCHIVE_MEDIA_TYPE,
    )
    monkeypatch.setattr(
        stagec_archive,
        "load_stagec_capture_archive",
        original_loader,
    )
    loaded = original_loader(root, expected_manifest_ref=reconstructed_ref)
    assert loaded.index.to_payload() == result.index.to_payload()


def test_archive_declares_manifest_listed_only_and_same_location_replay(
    tmp_path: Path,
) -> None:
    _, root, receipt, _ = _created_archive(tmp_path)
    unlisted = root / "unlisted-local-note.txt"
    unlisted.write_text("not a manifest member", encoding="utf-8")

    loaded = load_stagec_capture_archive(
        root,
        expected_manifest_ref=receipt.manifest_ref,
    )
    assert loaded.authority["membership_scope"] == (
        "MANIFEST_LISTED_MEMBERS_ONLY_CLOSED_WORLD_NOT_ESTABLISHED"
    )
    assert "unlisted-local-note.txt" not in loaded.member_paths

    moved = tmp_path / "moved-archive"
    root.rename(moved)
    with pytest.raises(StageCArchiveError, match="root path drifted"):
        load_stagec_capture_archive(
            moved,
            expected_manifest_ref=receipt.manifest_ref,
        )
    moved.rename(root)
    replayed = load_stagec_capture_archive(
        root,
        expected_manifest_ref=receipt.manifest_ref,
    )
    assert replayed.authority["relocatability"] == (
        "SAME_ABSOLUTE_PATH_AND_FILE_IDENTITIES_ONLY"
    )
