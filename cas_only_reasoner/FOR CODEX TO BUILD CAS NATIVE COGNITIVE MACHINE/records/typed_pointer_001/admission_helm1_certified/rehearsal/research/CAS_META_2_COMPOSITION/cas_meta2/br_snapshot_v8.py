"""Copy pinned SQLite image bytes into independent master/B/R files.

This utility never connects to SQLite. A SQLite header, no observed sidecars,
stable file identities and matching hashes do not establish database validity,
runtime closure, suspended-caller state, or equal outer execution allowances.
The future native caller must establish those facts separately.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat

SCHEMA = "cas-meta2-br-byte-snapshot/8"
SQLITE_HEADER = b"SQLite format 3\x00"
SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")
MAX_IMAGE_BYTES = 256 * 1024**2
CHUNK_BYTES = 1024**2
COPY_NAMES = ("master.sqlite", "B.sqlite", "R.sqlite")


class SnapshotRefused(ValueError):
    """Failure never authorizes consuming any retained partial copy."""
    def __init__(self, code, *, receipt_path=None):
        super().__init__(code)
        self.code = code
        self.receipt_path = receipt_path


def require(condition, code):
    if not condition:
        raise SnapshotRefused(code)


def _canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _unlinked_path(path):
    path = Path(path).absolute()
    # Check every existing component before resolving; resolve() alone would hide links.
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode)
                and not (getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
                and not getattr(item, "is_junction", lambda: False)(), "PATH_LINK_OR_JUNCTION_REFUSED")
    return path.resolve()


def _stat_identity(info):
    return {"device": info.st_dev, "file_id": info.st_ino, "links": info.st_nlink,
            "bytes": info.st_size, "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns}


def _same_shared_identity(path_stat, descriptor_stat):
    # Windows can report different ctime values for Path.stat and os.fstat on
    # one unchanged file. Compare stable shared fields across those two views;
    # retain full ctime-inclusive comparisons before/after within each view.
    return all(path_stat[key] == descriptor_stat[key]
               for key in ("device", "file_id", "links", "bytes", "mtime_ns"))


def _regular_image(path, maximum):
    path = _unlinked_path(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode), "REGULAR_IMAGE_REQUIRED")
    require(info.st_nlink == 1, "HARD_LINKED_IMAGE_REFUSED")
    require(info.st_ino > 0, "PHYSICAL_FILE_ID_REQUIRED")
    require(100 <= info.st_size <= maximum, "SQLITE_IMAGE_SIZE_BOUND")
    return _stat_identity(info)


def _require_no_sidecars(path):
    observed = []
    for suffix in SIDECAR_SUFFIXES:
        sidecar = Path(str(path) + suffix)
        try:
            sidecar.lstat()
        except FileNotFoundError:
            observed.append(str(sidecar))
        else:
            raise SnapshotRefused("SQLITE_SIDECAR_PRESENT:" + suffix)
    return observed


def _read_descriptor(path):
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    return os.fdopen(os.open(path, flags), "rb")


def _verified_image(path, expected_sha256, maximum):
    """Check a file twice by path and by descriptor; do not open a database."""
    path = _unlinked_path(path)
    absent_before = _require_no_sidecars(path)
    before = _regular_image(path, maximum)
    hasher, total = sha256(), 0
    with _read_descriptor(path) as stream:
        descriptor_before = _stat_identity(os.fstat(stream.fileno()))
        require(_same_shared_identity(before, descriptor_before), "IMAGE_CHANGED_BEFORE_READ")
        first = True
        while True:
            block = stream.read(min(CHUNK_BYTES, maximum - total + 1))
            if not block:
                break
            if first:
                require(block.startswith(SQLITE_HEADER), "SQLITE_HEADER_REQUIRED")
                first = False
            total += len(block)
            require(total <= maximum, "SQLITE_IMAGE_SIZE_BOUND")
            hasher.update(block)
        require(_stat_identity(os.fstat(stream.fileno())) == descriptor_before, "IMAGE_CHANGED_DURING_READ")
    require(total == before["bytes"] and _regular_image(path, maximum) == before,
            "IMAGE_CHANGED_AFTER_READ")
    require(_require_no_sidecars(path) == absent_before, "SIDECAR_OBSERVATION_CHANGED")
    require(hasher.hexdigest() == expected_sha256, "SQLITE_IMAGE_SHA256_MISMATCH")
    return {"path": str(path), "sha256": expected_sha256, "stat": before,
            "descriptor_stat": descriptor_before,
            "sqlite_header_observed": True, "absent_sidecars": absent_before}


def _copy_image(source, destination, expected_sha256, maximum):
    """Exclusive sequential copy. A partially written output is never removed."""
    source_record = _verified_image(source, expected_sha256, maximum)
    destination = _unlinked_path(destination)
    _require_no_sidecars(destination)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with _read_descriptor(source) as input_stream:
        descriptor_before = _stat_identity(os.fstat(input_stream.fileno()))
        require(_same_shared_identity(source_record["stat"], descriptor_before)
                and descriptor_before == source_record["descriptor_stat"],
                "COPY_SOURCE_CHANGED_BEFORE_OPEN")
        with os.fdopen(os.open(destination, flags, 0o600), "wb") as output_stream:
            identity = os.fstat(output_stream.fileno())
            require(identity.st_nlink == 1 and identity.st_ino > 0, "INDEPENDENT_COPY_REQUIRED")
            require((identity.st_dev, identity.st_ino) !=
                    (source_record["stat"]["device"], source_record["stat"]["file_id"]), "COPY_ALIASES_SOURCE")
            hasher, total = sha256(), 0
            while True:
                block = input_stream.read(min(CHUNK_BYTES, maximum - total + 1))
                if not block:
                    break
                total += len(block)
                require(total <= maximum, "SQLITE_IMAGE_SIZE_BOUND")
                output_stream.write(block)
                hasher.update(block)
            output_stream.flush()
            os.fsync(output_stream.fileno())
            require(total == source_record["stat"]["bytes"] and hasher.hexdigest() == expected_sha256,
                    "COPY_BYTES_CHANGED")
            require(_stat_identity(os.fstat(input_stream.fileno())) == descriptor_before,
                    "COPY_SOURCE_CHANGED_DURING_READ")
    require(_verified_image(source, expected_sha256, maximum) == source_record,
            "COPY_SOURCE_CHANGED_AFTER_READ")
    return _verified_image(destination, expected_sha256, maximum)


def _limitations():
    return {"proof_kind": "BYTE_COPY_EQUIVALENCE_ONLY",
        "sqlite_connection_opened": False, "checkpoint_backup_repair_or_schema_mutation": False,
        "database_native_validity_verified": False, "runtime_state_closure_verified": False,
        "absence_of_suspended_callers_verified": False, "executor_frames_and_events_verified": False,
        "equal_outer_execution_allowances_verified": False, "native_execution_performed": False,
        "sidecar_absence_proves_closed_database": False, "hash_match_proves_runtime_validity": False,
        "concurrent_writer_exclusion_enforced": False,
        "required_future_checks": [
            "The AWS caller must establish database/native validity and a genuinely closed source before copying.",
            "No connection lock is taken; stable observations do not exclude every concurrent-writer race.",
            "META Executor.frames/events and suspended callers may require a separate Executor.checkpoint JSON.",
            "The AWS caller must establish equal outer execution allowances and all required runtime state for both arms.",
            "Byte-equivalent B/R files do not establish meaningful alternative inputs or task correctness."]}


def _write_receipt(path, value):
    path = _unlinked_path(path)
    with path.open("xb") as stream:
        stream.write(_canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def copy_closed_snapshot(source, expected_sha256, destination, *, owned_output_root,
                         source_closed_self_contained, max_bytes=MAX_IMAGE_BYTES):
    """Retain a master and two independent arm files; return the byte-only receipt.

The required source_closed_self_contained=True is a caller assertion, not a
conclusion of this function. A failed call leaves all created files in place.
The caller must reject every partial/failure output, even if one file hashes.
"""
    require(type(expected_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_sha256),
            "EXPLICIT_LOWERCASE_SHA256_REQUIRED")
    require(source_closed_self_contained is True, "EXPLICIT_CALLER_CLOSED_SOURCE_ASSERTION_REQUIRED")
    require(type(max_bytes) is int and 100 <= max_bytes <= MAX_IMAGE_BYTES, "IMAGE_BOUND_REQUIRED")
    source, output_root, destination = (_unlinked_path(path) for path in (source, owned_output_root, destination))
    require(output_root.is_dir() and output_root != Path(output_root.anchor), "OWNED_EXISTING_OUTPUT_DIRECTORY_REQUIRED")
    require(destination != output_root and destination.is_relative_to(output_root)
            and source != destination and not source.is_relative_to(destination), "NEW_DISTINCT_IN_SCOPE_DESTINATION_REQUIRED")
    require(not destination.exists(), "DESTINATION_ALREADY_EXISTS")
    before = _verified_image(source, expected_sha256, max_bytes)
    receipt = {"schema": SCHEMA, "status": "COPY_IN_PROGRESS_NOT_USABLE", "source": before,
        "destination": str(destination), "owned_output_root": str(output_root), "max_image_bytes": max_bytes,
        "caller_assertion": {"source_closed_self_contained": True, "verified_by_utility": False},
        "copies": {}, "limitations": _limitations(), "partial_files_deleted": False}
    # Do not create hidden ancestor directories outside the declared new destination.
    require(destination.parent.is_dir(), "EXISTING_DESTINATION_PARENT_REQUIRED")
    destination.mkdir(exist_ok=False)
    receipt_path = destination / "receipt.json"
    try:
        all_ids = {(before["stat"]["device"], before["stat"]["file_id"])}
        for name in COPY_NAMES:
            require(_verified_image(source, expected_sha256, max_bytes) == before, "ORIGINAL_SOURCE_CHANGED")
            source_for_copy = source if name == "master.sqlite" else destination / "master.sqlite"
            record = _copy_image(source_for_copy, destination / name, expected_sha256, max_bytes)
            identity = (record["stat"]["device"], record["stat"]["file_id"])
            require(identity not in all_ids, "COPY_PHYSICAL_IDENTITY_ALIAS")
            all_ids.add(identity)
            receipt["copies"][name] = record
            require(_verified_image(source, expected_sha256, max_bytes) == before, "ORIGINAL_SOURCE_CHANGED")
        # Recheck retained master and both arms after all writes, before success.
        for name, record in receipt["copies"].items():
            require(_verified_image(destination / name, expected_sha256, max_bytes) == record,
                    "RETAINED_COPY_CHANGED:" + name)
        require(_verified_image(source, expected_sha256, max_bytes) == before, "ORIGINAL_SOURCE_CHANGED")
        receipt.update(status="BYTE_EQUIVALENT_INDEPENDENT_COPIES", source_unchanged=True,
            all_four_file_identities_distinct=len(all_ids) == 4,
            observed_utc=datetime.now(timezone.utc).isoformat())
        _write_receipt(receipt_path, receipt)
        return receipt
    except Exception as error:
        receipt.update(status="COPY_FAILED_PARTIAL_FILES_RETAINED", source_unchanged=None,
            all_four_file_identities_distinct=None, failure_type=type(error).__name__, failure=str(error),
            observed_utc=datetime.now(timezone.utc).isoformat())
        # Never overwrite a partially written success receipt or any caller file.
        failure_path = receipt_path if not receipt_path.exists() else destination / "failure_receipt.json"
        try:
            _write_receipt(failure_path, receipt)
            written = str(failure_path)
        except Exception:
            written = None  # Disk/permission failure can prevent recording; copies remain.
        code = error.code if isinstance(error, SnapshotRefused) else "COPY_IO_OR_VALIDATION_FAILURE:" + type(error).__name__
        raise SnapshotRefused(code, receipt_path=written) from error
