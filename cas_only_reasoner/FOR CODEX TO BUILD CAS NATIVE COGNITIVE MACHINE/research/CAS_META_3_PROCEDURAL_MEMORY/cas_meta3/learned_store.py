"""Append-only candidate storage with fresh evidence checks on every retrieval.

Stored audit bytes are not trust anchors. A caller must independently supply
the expected package and audit identities, source, scope, compatibility and
lineage. This stores no model weights and grants no activation or qualification.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sqlite3

from . import learned_package as packages
from . import learning_evidence as evidence
from .learned_handoff import prepare_reuse_candidate

SCHEMA = "cas-meta3-learned-candidate-store/0.1"
MAX_FILE_BYTES = 512 * 1024**2
MAX_TOTAL_PAYLOAD = 400 * 1024**2
MAX_CANDIDATES = 64
RAW_FIELDS = ("inspection_bytes", "stored_audit_bytes", "index_bytes",
              "predictions_bytes", "checkpoints_bytes")
TRUST_FIELDS = frozenset(("trusted_compatibility", "permitted_cjts",
    "expected_parent_digest", "expected_version", "expected_inspection_sha256",
    "expected_stored_audit_sha256", "trusted_source_sha", "arm", "case_index"))
SQL = {
    "metadata": "CREATE TABLE metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1),payload BLOB NOT NULL)",
    "candidates": "CREATE TABLE candidates(sequence INTEGER PRIMARY KEY,package_sha256 TEXT UNIQUE NOT NULL,package BLOB NOT NULL,inspection_bytes BLOB NOT NULL,stored_audit_bytes BLOB NOT NULL,index_bytes BLOB NOT NULL,predictions_bytes BLOB NOT NULL,checkpoints_bytes BLOB NOT NULL,handoff BLOB NOT NULL,receipt BLOB NOT NULL)",
    "candidates_no_update": "CREATE TRIGGER candidates_no_update BEFORE UPDATE ON candidates BEGIN SELECT RAISE(ABORT,'immutable candidates'); END",
    "candidates_no_delete": "CREATE TRIGGER candidates_no_delete BEFORE DELETE ON candidates BEGIN SELECT RAISE(ABORT,'immutable candidates'); END",
    "metadata_no_update": "CREATE TRIGGER metadata_no_update BEFORE UPDATE ON metadata BEGIN SELECT RAISE(ABORT,'immutable metadata'); END",
    "metadata_no_delete": "CREATE TRIGGER metadata_no_delete BEFORE DELETE ON metadata BEGIN SELECT RAISE(ABORT,'immutable metadata'); END",
}
PAYLOAD_NAMES = ("package", *RAW_FIELDS, "handoff")
METADATA = evidence.canonical({"schema": SCHEMA, "package_schema": packages.PACKAGE_SCHEMA,
    "learning_evidence_schema": evidence.SCHEMA, "source_sha": packages.META2_SOURCE_SHA,
    "qualification_status": "UNQUALIFIED"})


class StoreError(ValueError):
    pass


def require(value, code):
    if not value:
        raise StoreError(code)


def _path(path):
    for part in (path, *path.parents):
        require(not part.is_symlink() and not getattr(part, "is_junction", lambda: False)(), "STORE_LINK_PATH_REFUSED")
    require(not path.exists() or path.is_file(), "STORE_FILE_REQUIRED")
    if path.exists():
        require(path.stat().st_size <= MAX_FILE_BYTES, "STORE_BYTE_CEILING")


def _receipt(sequence, identifier, payloads, previous):
    body = {"schema": "cas-meta3-learned-storage-receipt/0.1", "sequence": sequence,
        "package_sha256": identifier, "previous_receipt_sha256": previous,
        "payloads": {name: {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}
                     for name, raw in zip(PAYLOAD_NAMES, payloads)},
        "status": "CANDIDATE_STORED", "qualification_status": "UNQUALIFIED",
        "promotion_granted": False, "native_execution_performed": False}
    return {**body, "receipt_sha256": evidence.digest(body)}


def _scan(conn):
    definitions = {name: sql for name, sql in conn.execute(
        "SELECT name,sql FROM sqlite_master WHERE type != 'index'")}
    require(definitions == SQL, "STORE_SCHEMA_MISMATCH")
    require(list(conn.execute("SELECT * FROM metadata")) == [(1, METADATA)], "STORE_METADATA_MISMATCH")
    count = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    require(count <= MAX_CANDIDATES, "STORE_CANDIDATE_CEILING")
    names = (*PAYLOAD_NAMES, "receipt")
    lengths = conn.execute("SELECT " + ",".join("length(" + name + ")" for name in names) + " FROM candidates")
    total = 0
    for row in lengths:
        require(all(type(size) is int and 0 < size <= evidence.MAX_BYTES for size in row), "STORED_PAYLOAD_CEILING")
        require(row[0] <= packages.MAX_PACKAGE_BYTES, "STORED_PACKAGE_CEILING")
        total += sum(row)
        require(total <= MAX_TOTAL_PAYLOAD, "STORE_TOTAL_PAYLOAD_CEILING")
    result, previous = {}, None
    for row in conn.execute("SELECT * FROM candidates ORDER BY sequence"):
        sequence, identifier, *raw = row
        require(type(sequence) is int and sequence == len(result) + 1, "STORE_SEQUENCE_CHANGED")
        require(all(type(value) is bytes for value in raw), "STORED_BLOB_REQUIRED")
        payloads, receipt_bytes = raw[:-1], raw[-1]
        require(sha256(payloads[0]).hexdigest() == identifier, "STORED_PACKAGE_CHANGED")
        require(packages.canonical_package(payloads[0]) == payloads[0], "STORED_PACKAGE_NOT_CANONICAL")
        receipt = _receipt(sequence, identifier, payloads, previous)
        require(evidence.canonical(receipt) == receipt_bytes, "STORED_RECEIPT_CHANGED")
        result[identifier] = (payloads, receipt)
        previous = receipt["receipt_sha256"]
    return result, total


def _parent_check(package, rows):
    parent = package["lineage"]["parent_package_sha256"]
    if parent is not None:
        require(parent in rows, "STORED_PARENT_REQUIRED")
        parent_package = evidence._json(rows[parent][0][0])
        require(parent_package["lineage"]["version"] + 1 == package["lineage"]["version"], "STORED_PARENT_VERSION_MISMATCH")
        require(parent_package["compatibility"] == package["compatibility"], "STORED_PARENT_COMPATIBILITY_MISMATCH")


class LearnedCandidateStore:
    """Explicit save/retrieve only. No execution, activation or delete API."""
    def __init__(self, path):
        self.path = Path(path).absolute()
        _path(self.path)

    def _connect(self, readonly):
        _path(self.path)
        require(self.path.is_file(), "STORE_NOT_FOUND")
        conn = sqlite3.connect(self.path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True, timeout=10)
        conn.execute("PRAGMA trusted_schema=OFF")
        if not readonly:
            size = conn.execute("PRAGMA page_size").fetchone()[0]
            conn.execute("PRAGMA max_page_count=" + str(MAX_FILE_BYTES // size))
        return conn

    def save(self, package, **handoff_inputs):
        # Fully validate the caller and package BEFORE creating directories or DB.
        prepared = prepare_reuse_candidate(package, **handoff_inputs)
        identifier = prepared["package_sha256"]
        payloads = (packages.canonical_package(prepared["package"]),
            *(handoff_inputs[name] for name in RAW_FIELDS), evidence.canonical(prepared))
        require(sum(map(len, payloads)) < MAX_TOTAL_PAYLOAD, "STORE_TOTAL_PAYLOAD_CEILING")
        _path(self.path)
        if prepared["package"]["lineage"]["parent_package_sha256"] is not None:
            require(self.path.is_file(), "STORED_PARENT_REQUIRED")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _path(self.path)
        created = False
        try:
            with self.path.open("xb"):
                created = True
        except FileExistsError:
            pass
        conn = self._connect(False)
        try:
            conn.execute("BEGIN IMMEDIATE")
            if created:
                for statement in SQL.values():
                    conn.execute(statement)
                conn.execute("INSERT INTO metadata VALUES(1,?)", (METADATA,))
            rows, total = _scan(conn)
            _parent_check(prepared["package"], rows)
            if identifier in rows:
                require(tuple(rows[identifier][0]) == payloads, "EXISTING_CANDIDATE_EVIDENCE_MISMATCH")
                conn.rollback()
                return deepcopy(rows[identifier][1])
            require(len(rows) < MAX_CANDIDATES, "STORE_CANDIDATE_CEILING")
            previous = next(reversed(rows.values()))[1]["receipt_sha256"] if rows else None
            receipt = _receipt(len(rows) + 1, identifier, payloads, previous)
            receipt_raw = evidence.canonical(receipt)
            require(total + sum(map(len, payloads)) + len(receipt_raw) <= MAX_TOTAL_PAYLOAD, "STORE_TOTAL_PAYLOAD_CEILING")
            conn.execute("INSERT INTO candidates VALUES(?,?,?,?,?,?,?,?,?,?)",
                (len(rows) + 1, identifier, *payloads, receipt_raw))
            conn.commit()
            return deepcopy(receipt)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def retrieve(self, expected_digest, **trust_inputs):
        require(TRUST_FIELDS <= set(trust_inputs) <= TRUST_FIELDS | {"minimum_correct_gain"}, "EXTERNAL_RETRIEVAL_TRUST_REQUIRED")
        conn = self._connect(True)
        try:
            rows, _ = _scan(conn)
            require(expected_digest in rows, "UNKNOWN_CANDIDATE")
            payloads, receipt = rows[expected_digest]
            prepared = prepare_reuse_candidate(payloads[0], expected_digest=expected_digest,
                **dict(zip(RAW_FIELDS, payloads[1:6])), **trust_inputs)
            require(evidence.canonical(prepared) == payloads[6], "STORED_HANDOFF_CHANGED")
            _parent_check(prepared["package"], rows)
            return {"package": prepared["package"], "handoff": prepared,
                    "storage_receipt": deepcopy(receipt), "retrieval_revalidated": True,
                    "qualification_status": "UNQUALIFIED", "promotion_granted": False}
        finally:
            conn.close()
