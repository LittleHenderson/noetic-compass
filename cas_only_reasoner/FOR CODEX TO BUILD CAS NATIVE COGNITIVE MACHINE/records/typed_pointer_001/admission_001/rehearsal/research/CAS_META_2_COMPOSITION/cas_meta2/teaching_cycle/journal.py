"""Append-only candidate checkpoint journal; no model or provider execution.

Only published transaction directories count as committed. Incomplete staging
is retained and reported. Losing uncommitted learning is not a refund, an undo
of actual work, or permission to retry. The caller authenticates source identity
and supplies a checkpoint writer that obeys its declared size ceiling.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
import tempfile

SCHEMA = "cas-teaching-checkpoint-journal/1"
TOTAL_BYTES = 512 * 1024 * 1024
RECEIPT_BYTES = 65536
IDENTITY_BYTES = 16384
FILES = {"candidate.pt", "metadata.json", "receipt.json"}


class JournalError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise JournalError("TEACHING_JOURNAL:" + reason)


def _finite_json(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        require(math.isfinite(value), "NONFINITE_JSON")
    elif type(value) is list:
        for child in value:
            _finite_json(child)
    elif type(value) is dict:
        require(all(type(key) is str for key in value), "JSON_KEYS_MUST_BE_STRINGS")
        for child in value.values():
            _finite_json(child)
    else:
        raise JournalError("TEACHING_JOURNAL:JSON_TYPE_INVALID")


def _encode(value):
    _finite_json(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def _digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None and value != "0" * 64


def _safe_path(path):
    for item in (path, *path.parents):
        require(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)(), "LINK_PATH_REJECTED")
        if item.exists():
            info = item.stat(follow_symlinks=False)
            if stat.S_ISREG(info.st_mode):
                require(info.st_nlink == 1, "HARDLINK_FILE_REJECTED")


def _regular_file(path):
    _safe_path(path)
    require(path.is_file() and stat.S_ISREG(path.stat(follow_symlinks=False).st_mode), "REGULAR_FILE_REQUIRED")
    return path.stat().st_size


def _hash_file(path):
    _regular_file(path)
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path, limit):
    require(_regular_file(path) <= limit, "JSON_BYTE_LIMIT")
    raw = path.read_bytes()
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=object_pairs)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise JournalError("TEACHING_JOURNAL:INVALID_JSON") from error
    require(_encode(value) == raw, "NONCANONICAL_JSON")
    return value, sha256(raw).hexdigest()


def _write_new(path, payload):
    _safe_path(path)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _sync_directory(path):
    # POSIX workers support directory fsync. Python's Windows directory API
    # does not; local synthetic tests must not claim equivalent power-loss proof.
    if os.name == "nt":
        return False
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return True


class CheckpointJournal:
    def __init__(self, root, run_id, identity, max_checkpoint_bytes=67108864, max_metadata_bytes=33554432):
        require(type(run_id) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", run_id), "RUN_ID_INVALID")
        require(type(identity) is dict and identity and _digest(identity.get("source_sha256")), "SOURCE_IDENTITY_REQUIRED")
        identity_bytes = _encode(identity)
        require(len(identity_bytes) <= IDENTITY_BYTES, "IDENTITY_BYTE_LIMIT")
        require(all(type(value) is int and 0 < value <= TOTAL_BYTES
                    for value in (max_checkpoint_bytes, max_metadata_bytes)), "SIZE_LIMIT_INVALID")
        self.root = Path(root).absolute()
        _safe_path(self.root)
        require(self.root.parent.is_dir(), "ROOT_PARENT_REQUIRED")
        if not self.root.exists():
            self.root.mkdir()
            _sync_directory(self.root.parent)
        require(self.root.is_dir(), "ROOT_DIRECTORY_REQUIRED")
        self.run_id, self.identity = run_id, deepcopy(identity)
        self.identity_sha256 = sha256(identity_bytes).hexdigest()
        self.max_checkpoint_bytes, self.max_metadata_bytes = max_checkpoint_bytes, max_metadata_bytes
        self.incomplete_staging = []
        self.anchor = {"schema": SCHEMA, "run_id": run_id, "identity": self.identity,
                       "identity_sha256": self.identity_sha256, "max_checkpoint_bytes": max_checkpoint_bytes,
                       "max_metadata_bytes": max_metadata_bytes, "total_byte_limit": TOTAL_BYTES}
        anchor_path = self.root / "journal.json"
        if not anchor_path.exists():
            require(not list(self.root.iterdir()), "NONEMPTY_UNINITIALIZED_ROOT")
            _write_new(anchor_path, _encode(self.anchor))
            _sync_directory(self.root)
        self._check_anchor()

    def _check_anchor(self):
        _safe_path(self.root)
        actual, _ = _read_json(self.root / "journal.json", RECEIPT_BYTES)
        require(actual == self.anchor, "JOURNAL_IDENTITY_MISMATCH")

    def _inventory(self):
        self._check_anchor()
        committed, staging, total = [], [], 0
        for entry in self.root.iterdir():
            _safe_path(entry)
            if entry.name == "journal.json":
                total += _regular_file(entry)
                continue
            require(entry.is_dir(), "UNEXPECTED_ROOT_ENTRY")
            match = re.fullmatch(r"txn-([0-9]{8})", entry.name)
            require(match is not None or entry.name.startswith(".staging-"), "UNEXPECTED_ROOT_ENTRY")
            children = list(entry.iterdir())
            size = sum(_regular_file(child) for child in children)
            total += size
            if match is not None:
                require({child.name for child in children} == FILES, "TRANSACTION_FILES_MISMATCH")
                committed.append((int(match[1]), entry))
            else:
                staging.append({"path": str(entry), "bytes": size, "files": sorted(child.name for child in children),
                                "status": "INCOMPLETE_NOT_COMMITTED_NO_AUTOMATIC_RETRY"})
        committed.sort()
        require([index for index, _ in committed] == list(range(1, len(committed) + 1)), "TRANSACTION_CHAIN_GAP")
        self.incomplete_staging = sorted(staging, key=lambda item: item["path"])
        return committed, total

    def latest(self):
        """Validate the entire chain. With no commit, staging is in the property."""
        committed, total = self._inventory()
        previous, latest = None, None
        for sequence, directory in committed:
            receipt, receipt_hash = _read_json(directory / "receipt.json", RECEIPT_BYTES)
            metadata, metadata_hash = _read_json(directory / "metadata.json", self.max_metadata_bytes)
            require(type(metadata) is dict and type(receipt) is dict, "TRANSACTION_OBJECT_REQUIRED")
            expected = {"schema": SCHEMA, "run_id": self.run_id, "identity_sha256": self.identity_sha256,
                        "sequence": sequence, "previous_receipt_sha256": previous,
                        "checkpoint_filename": "candidate.pt", "metadata_filename": "metadata.json",
                        "metadata_sha256": metadata_hash, "metadata_bytes": (directory / "metadata.json").stat().st_size,
                        "candidate_only": True, "neural_execution_by_journal": False}
            require(all(receipt.get(key) == value for key, value in expected.items()), "RECEIPT_CHAIN_OR_IDENTITY_MISMATCH")
            checkpoint = directory / "candidate.pt"
            size = _regular_file(checkpoint)
            require(0 < size <= self.max_checkpoint_bytes and receipt.get("checkpoint_bytes") == size,
                    "CHECKPOINT_BYTE_LIMIT_OR_MISMATCH")
            checkpoint_hash = _hash_file(checkpoint)
            require(receipt.get("checkpoint_sha256") == checkpoint_hash, "CHECKPOINT_DIGEST_MISMATCH")
            writer = receipt.get("writer_receipt")
            require(type(writer) is dict and writer.get("sha256") == checkpoint_hash, "WRITER_RECEIPT_MISMATCH")
            require(type(receipt.get("directory_fsync_supported")) is bool, "DURABILITY_RECEIPT_INVALID")
            previous = receipt_hash
            latest = {"metadata": metadata, "checkpoint_path": str(checkpoint), "checkpoint_sha256": checkpoint_hash,
                      "receipt": {**receipt, "receipt_sha256": receipt_hash, "transaction_path": str(directory)},
                      "incomplete_staging": deepcopy(self.incomplete_staging), "retained_bytes": total,
                      "boundary": "Committed candidate state only; uncommitted teaching and actual spend are not undone."}
        return latest

    def commit(self, metadata, checkpoint_writer):
        require(type(metadata) is dict, "METADATA_OBJECT_REQUIRED")
        metadata_bytes = _encode(metadata)
        require(len(metadata_bytes) <= self.max_metadata_bytes, "METADATA_BYTE_LIMIT")
        require(callable(checkpoint_writer), "CHECKPOINT_WRITER_REQUIRED")
        prior = self.latest()
        _, used = self._inventory()
        # Reserve worst-case declared checkpoint space before invoking the writer.
        require(used + self.max_checkpoint_bytes + len(metadata_bytes) + RECEIPT_BYTES <= TOTAL_BYTES,
                "PROSPECTIVE_JOURNAL_BYTE_LIMIT")
        sequence = 1 if prior is None else prior["receipt"]["sequence"] + 1
        require(sequence <= 99999999, "SEQUENCE_LIMIT")
        previous = None if prior is None else prior["receipt"]["receipt_sha256"]
        staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=self.root))
        checkpoint = staging / "candidate.pt"
        writer = checkpoint_writer(checkpoint)  # Must create this fresh path, never another destination.
        require(type(writer) is dict and type(writer.get("path")) is str, "WRITER_RECEIPT_INVALID")
        _safe_path(Path(writer["path"]).absolute())
        require(Path(writer["path"]).absolute() == checkpoint, "WRITER_PATH_ESCAPE")
        require(len(_encode(writer)) <= IDENTITY_BYTES, "WRITER_RECEIPT_BYTE_LIMIT")
        require({entry.name for entry in staging.iterdir()} == {"candidate.pt"}, "WRITER_EXTRA_FILES")
        size = _regular_file(checkpoint)
        require(0 < size <= self.max_checkpoint_bytes, "CHECKPOINT_BYTE_LIMIT")
        checkpoint_hash = _hash_file(checkpoint)
        require(writer.get("sha256") == checkpoint_hash, "WRITER_CHECKPOINT_DIGEST_MISMATCH")
        with checkpoint.open("r+b") as stream:
            os.fsync(stream.fileno())
        _write_new(staging / "metadata.json", metadata_bytes)
        directory_sync = _sync_directory(staging)
        receipt = {"schema": SCHEMA, "run_id": self.run_id, "identity_sha256": self.identity_sha256,
                   "sequence": sequence, "previous_receipt_sha256": previous,
                   "checkpoint_filename": "candidate.pt", "checkpoint_sha256": checkpoint_hash, "checkpoint_bytes": size,
                   "metadata_filename": "metadata.json", "metadata_sha256": sha256(metadata_bytes).hexdigest(),
                   "metadata_bytes": len(metadata_bytes), "writer_receipt": {key: value for key, value in writer.items() if key != "path"},
                   "candidate_only": True, "neural_execution_by_journal": False,
                   "directory_fsync_supported": directory_sync}
        receipt_bytes = _encode(receipt)
        require(len(receipt_bytes) <= RECEIPT_BYTES, "RECEIPT_BYTE_LIMIT")
        _write_new(staging / "receipt.json", receipt_bytes)
        require(_sync_directory(staging) == directory_sync, "DIRECTORY_SYNC_CHANGED")
        # Optimistic concurrency: another publisher cannot be silently overwritten.
        current = self.latest()
        current_hash = None if current is None else current["receipt"]["receipt_sha256"]
        require(current_hash == previous, "CONCURRENT_COMMIT_DETECTED")
        _, retained = self._inventory()
        require(retained <= TOTAL_BYTES, "JOURNAL_BYTE_LIMIT")
        destination = self.root / f"txn-{sequence:08d}"
        _safe_path(destination)
        require(not destination.exists(), "TRANSACTION_ALREADY_EXISTS")
        os.rename(staging, destination)  # Existing committed directories are nonempty: never replaceable here.
        _sync_directory(self.root)
        committed = self.latest()
        require(committed is not None and committed["receipt"]["sequence"] == sequence, "COMMIT_VERIFICATION_FAILED")
        return committed["receipt"]
