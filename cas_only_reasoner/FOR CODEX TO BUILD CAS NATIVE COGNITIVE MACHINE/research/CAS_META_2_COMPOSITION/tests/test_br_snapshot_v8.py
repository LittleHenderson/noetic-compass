"""Synthetic byte-only snapshot tests; never open a SQLite/native/model runtime."""
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace

import pytest

from cas_meta2 import br_snapshot_v8 as b


@pytest.fixture
def image(tmp_path):
    # Deliberately not a validated database. The utility must claim only bytes.
    raw = b.SQLITE_HEADER + bytes(range(256)) * 4
    source = tmp_path / "source.sqlite"
    source.write_bytes(raw)
    output_root = tmp_path / "owned"
    output_root.mkdir()
    return source, sha256(raw).hexdigest(), output_root, raw


def run_copy(image, **changes):
    source, expected, output_root, _ = image
    arguments = {"source": source, "expected_sha256": expected, "destination": output_root / "copies",
                 "owned_output_root": output_root, "source_closed_self_contained": True}
    arguments.update(changes)
    return b.copy_closed_snapshot(**arguments)


def test_master_and_b_r_copies_match_bytes_but_have_distinct_physical_files(image):
    source, expected, output_root, raw = image
    before = source.stat()
    result = run_copy(image)
    assert result["status"] == "BYTE_EQUIVALENT_INDEPENDENT_COPIES"
    assert result["source_unchanged"] is True
    assert result["all_four_file_identities_distinct"] is True
    assert set(result["copies"]) == {"master.sqlite", "B.sqlite", "R.sqlite"}
    paths = [source, *(output_root / "copies" / name for name in b.COPY_NAMES)]
    assert len({(path.stat().st_dev, path.stat().st_ino) for path in paths}) == 4
    assert all(path.stat().st_nlink == 1 and path.read_bytes() == raw for path in paths)
    assert all(record["sha256"] == expected for record in result["copies"].values())
    assert b._stat_identity(before) == b._stat_identity(source.stat())
    assert json.loads((output_root / "copies/receipt.json").read_bytes()) == result


def test_changing_one_arm_does_not_change_master_other_arm_or_source(image):
    source, _, output_root, raw = image
    run_copy(image)
    (output_root / "copies/B.sqlite").write_bytes(b"changed arm B only")
    assert source.read_bytes() == raw
    assert (output_root / "copies/master.sqlite").read_bytes() == raw
    assert (output_root / "copies/R.sqlite").read_bytes() == raw


def test_sqlite_header_and_equal_hash_never_become_native_validity_or_runtime_closure(image):
    result = run_copy(image)
    limits = result["limitations"]
    assert limits["proof_kind"] == "BYTE_COPY_EQUIVALENCE_ONLY"
    for key in ("sqlite_connection_opened", "checkpoint_backup_repair_or_schema_mutation",
                "database_native_validity_verified", "runtime_state_closure_verified",
                "absence_of_suspended_callers_verified", "executor_frames_and_events_verified",
                "equal_outer_execution_allowances_verified", "native_execution_performed",
                "sidecar_absence_proves_closed_database", "hash_match_proves_runtime_validity",
                "concurrent_writer_exclusion_enforced"):
        assert limits[key] is False
    assert result["caller_assertion"] == {"source_closed_self_contained": True, "verified_by_utility": False}
    assert any("Executor.checkpoint JSON" in value for value in limits["required_future_checks"])


def test_pure_copy_opens_no_sqlite_connection_and_imports_no_neural_or_provider_module(image, monkeypatch):
    class Guard:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {"sqlite3", "torch", "numpy", "casformer", "cas_cjt",
                                         "cas_meta", "boto3", "botocore", "tensorflow", "jax"}:
                raise AssertionError("Unexpected non-byte-copy import: " + fullname)
    monkeypatch.setattr(sys, "meta_path", [Guard(), *sys.meta_path])
    assert run_copy(image)["status"] == "BYTE_EQUIVALENT_INDEPENDENT_COPIES"


def test_distinct_stable_path_and_descriptor_ctimes_do_not_imply_changed_bytes(image, monkeypatch):
    original = os.fstat
    def descriptor_view(fd):
        info = original(fd)
        fields = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
        fields["st_ctime_ns"] += 1_000_000_000
        return SimpleNamespace(**fields)
    monkeypatch.setattr(b.os, "fstat", descriptor_view)
    result = run_copy(image)
    assert result["status"] == "BYTE_EQUIVALENT_INDEPENDENT_COPIES"
    assert result["source"]["stat"]["ctime_ns"] != result["source"]["descriptor_stat"]["ctime_ns"]
    assert b._same_shared_identity(result["source"]["stat"], result["source"]["descriptor_stat"])
    assert result["source_unchanged"] is True


def test_descriptor_ctime_change_within_one_read_is_still_refused(image, monkeypatch):
    original = os.fstat
    source_id = (image[0].stat().st_dev, image[0].stat().st_ino)
    reads = 0
    def changing_descriptor_view(fd):
        nonlocal reads
        info = original(fd)
        if (info.st_dev, info.st_ino) != source_id:
            return info
        reads += 1
        fields = {name: getattr(info, name) for name in dir(info) if name.startswith("st_")}
        fields["st_ctime_ns"] += reads * 1_000_000_000
        return SimpleNamespace(**fields)
    monkeypatch.setattr(b.os, "fstat", changing_descriptor_view)
    with pytest.raises(b.SnapshotRefused, match="IMAGE_CHANGED_DURING_READ"):
        run_copy(image)
    assert not (image[2] / "copies").exists()


@pytest.mark.parametrize("pin", ["0" * 64, "A" * 64, "", None, "sha256:abcd"])
def test_wrong_or_missing_explicit_pin_creates_nothing(image, pin):
    with pytest.raises(b.SnapshotRefused):
        run_copy(image, expected_sha256=pin)
    assert not (image[2] / "copies").exists()


@pytest.mark.parametrize("assertion", [False, None, 1, "true"])
def test_source_closed_assertion_must_be_explicit_true(image, assertion):
    with pytest.raises(b.SnapshotRefused, match="EXPLICIT_CALLER_CLOSED_SOURCE_ASSERTION_REQUIRED"):
        run_copy(image, source_closed_self_contained=assertion)
    assert not (image[2] / "copies").exists()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_even_empty_sidecar_refuses_copy_without_checkpointing_or_deleting_it(image, suffix):
    source, _, output_root, raw = image
    sidecar = Path(str(source) + suffix)
    sidecar.write_bytes(b"")
    with pytest.raises(b.SnapshotRefused, match="SQLITE_SIDECAR_PRESENT"):
        run_copy(image)
    assert source.read_bytes() == raw and sidecar.read_bytes() == b""
    assert not (output_root / "copies").exists()


def test_source_without_sqlite_header_is_refused_even_with_correct_hash(image):
    source = image[0]
    source.write_bytes(b"not sqlite" * 100)
    with pytest.raises(b.SnapshotRefused, match="SQLITE_HEADER_REQUIRED"):
        run_copy(image, expected_sha256=sha256(source.read_bytes()).hexdigest())
    assert not (image[2] / "copies").exists()


@pytest.mark.parametrize("maximum", [99, 100, b.MAX_IMAGE_BYTES + 1, True, "1000"])
def test_bounded_image_limit_is_enforced(image, maximum):
    with pytest.raises(b.SnapshotRefused):
        run_copy(image, max_bytes=maximum)
    assert not (image[2] / "copies").exists()


def test_existing_destination_is_not_overwritten(image):
    output = image[2] / "copies"
    output.mkdir()
    retained = output / "master.sqlite"
    retained.write_bytes(b"existing user bytes")
    with pytest.raises(b.SnapshotRefused, match="DESTINATION_ALREADY_EXISTS"):
        run_copy(image)
    assert retained.read_bytes() == b"existing user bytes"
    assert set(p.name for p in output.iterdir()) == {"master.sqlite"}


def test_output_root_itself_is_not_a_new_destination(image):
    with pytest.raises(b.SnapshotRefused, match="NEW_DISTINCT_IN_SCOPE_DESTINATION_REQUIRED"):
        run_copy(image, destination=image[2])


def test_path_escape_is_refused(image):
    outside = image[2] / ".." / "outside"
    with pytest.raises(b.SnapshotRefused, match="NEW_DISTINCT_IN_SCOPE_DESTINATION_REQUIRED"):
        run_copy(image, destination=outside)
    assert not outside.exists()


def test_missing_output_parent_is_not_silently_created(image):
    with pytest.raises(b.SnapshotRefused, match="EXISTING_DESTINATION_PARENT_REQUIRED"):
        run_copy(image, destination=image[2] / "missing" / "copies")
    assert not (image[2] / "missing").exists()


def test_original_cannot_be_used_as_destination(image):
    with pytest.raises(b.SnapshotRefused):
        run_copy(image, destination=image[0], owned_output_root=image[0].parent)
    assert image[0].read_bytes() == image[3]


def test_hard_linked_original_is_refused(image):
    alias = image[0].with_name("alias.sqlite")
    os.link(image[0], alias)
    with pytest.raises(b.SnapshotRefused, match="HARD_LINKED_IMAGE_REFUSED"):
        run_copy(image)
    assert alias.read_bytes() == image[3] and not (image[2] / "copies").exists()


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_link_and_windows_junction_metadata_are_rejected_before_resolving(image, monkeypatch, kind):
    # Portable metadata-level test: no OS privilege for creating links is needed.
    original = Path.lstat
    target = image[2]
    def lstat(path):
        info = original(path)
        if path == target:
            return SimpleNamespace(st_mode=(stat.S_IFLNK if kind == "symlink" else stat.S_IFDIR),
                                   st_file_attributes=(0x400 if kind == "junction" else 0))
        return info
    monkeypatch.setattr(Path, "lstat", lstat)
    if kind == "junction":
        monkeypatch.setattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400, raising=False)
    with pytest.raises(b.SnapshotRefused, match="PATH_LINK_OR_JUNCTION_REFUSED"):
        run_copy(image)
    assert not (image[2] / "copies").exists()


def test_source_changes_after_first_copy_are_rejected_and_copies_retained(image, monkeypatch):
    original = b._copy_image
    def changing(source, destination, expected, maximum):
        record = original(source, destination, expected, maximum)
        if destination.name == "master.sqlite":
            image[0].write_bytes(image[3][:-1] + b"x")
        return record
    monkeypatch.setattr(b, "_copy_image", changing)
    with pytest.raises(b.SnapshotRefused) as error:
        run_copy(image)
    assert (image[2] / "copies/master.sqlite").read_bytes() == image[3]
    assert not (image[2] / "copies/B.sqlite").exists()
    receipt = json.loads(Path(error.value.receipt_path).read_bytes())
    assert receipt["status"] == "COPY_FAILED_PARTIAL_FILES_RETAINED"
    assert receipt["source_unchanged"] is None


def test_source_metadata_change_without_byte_change_is_rejected(image, monkeypatch):
    original = b._copy_image
    def changing(source, destination, expected, maximum):
        record = original(source, destination, expected, maximum)
        if destination.name == "master.sqlite":
            info = image[0].stat()
            os.utime(image[0], ns=(info.st_atime_ns, info.st_mtime_ns + 10_000_000))
        return record
    monkeypatch.setattr(b, "_copy_image", changing)
    with pytest.raises(b.SnapshotRefused, match="ORIGINAL_SOURCE_CHANGED"):
        run_copy(image)
    assert image[0].read_bytes() == image[3]


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecar_appearing_during_copy_blocks_success_and_is_not_removed(image, monkeypatch, suffix):
    original = b._copy_image
    sidecar = Path(str(image[0]) + suffix)
    def changing(source, destination, expected, maximum):
        record = original(source, destination, expected, maximum)
        if destination.name == "master.sqlite":
            sidecar.write_bytes(b"newly active")
        return record
    monkeypatch.setattr(b, "_copy_image", changing)
    with pytest.raises(b.SnapshotRefused, match="SQLITE_SIDECAR_PRESENT"):
        run_copy(image)
    assert sidecar.read_bytes() == b"newly active"
    assert (image[2] / "copies/master.sqlite").exists()


def test_copy_corruption_after_initial_verification_is_caught_by_final_pass(image, monkeypatch):
    original = b._copy_image
    def corrupting(source, destination, expected, maximum):
        record = original(source, destination, expected, maximum)
        if destination.name == "B.sqlite":
            destination.write_bytes(image[3][:-1] + b"z")
        return record
    monkeypatch.setattr(b, "_copy_image", corrupting)
    with pytest.raises(b.SnapshotRefused, match="SQLITE_IMAGE_SHA256_MISMATCH") as error:
        run_copy(image)
    receipt = json.loads(Path(error.value.receipt_path).read_bytes())
    assert receipt["status"] == "COPY_FAILED_PARTIAL_FILES_RETAINED"
    assert receipt["limitations"]["database_native_validity_verified"] is False
    assert (image[2] / "copies/B.sqlite").read_bytes() != image[3]
    assert (image[2] / "copies/R.sqlite").read_bytes() == image[3]


def test_partial_write_failure_retains_master_and_partial_arm_without_false_success(image, monkeypatch):
    original = b._copy_image
    def failing(source, destination, expected, maximum):
        if destination.name == "B.sqlite":
            with destination.open("xb") as stream:
                stream.write(b.SQLITE_HEADER + b"partial")
            raise OSError("synthetic write interruption")
        return original(source, destination, expected, maximum)
    monkeypatch.setattr(b, "_copy_image", failing)
    with pytest.raises(b.SnapshotRefused, match="COPY_IO_OR_VALIDATION_FAILURE:OSError") as error:
        run_copy(image)
    receipt = json.loads(Path(error.value.receipt_path).read_bytes())
    assert receipt["status"] == "COPY_FAILED_PARTIAL_FILES_RETAINED"
    assert receipt["partial_files_deleted"] is False
    assert receipt["all_four_file_identities_distinct"] is None
    assert set(receipt["copies"]) == {"master.sqlite"}
    assert (image[2] / "copies/master.sqlite").read_bytes() == image[3]
    assert (image[2] / "copies/B.sqlite").read_bytes() == b.SQLITE_HEADER + b"partial"
    assert not (image[2] / "copies/R.sqlite").exists()
    assert image[0].read_bytes() == image[3]


def test_receipt_write_failure_retains_every_copy_and_reports_missing_receipt(image, monkeypatch):
    monkeypatch.setattr(b, "_write_receipt", lambda *a: (_ for _ in ()).throw(OSError("synthetic receipt failure")))
    with pytest.raises(b.SnapshotRefused) as error:
        run_copy(image)
    assert error.value.receipt_path is None
    assert all((image[2] / "copies" / name).read_bytes() == image[3] for name in b.COPY_NAMES)


def test_copy_destination_precreated_during_run_is_never_overwritten(image, monkeypatch):
    original = b._copy_image
    def racing(source, destination, expected, maximum):
        if destination.name == "B.sqlite":
            destination.write_bytes(b"concurrent existing file")
        return original(source, destination, expected, maximum)
    monkeypatch.setattr(b, "_copy_image", racing)
    with pytest.raises(b.SnapshotRefused):
        run_copy(image)
    assert (image[2] / "copies/B.sqlite").read_bytes() == b"concurrent existing file"
