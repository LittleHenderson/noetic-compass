"""Append-only storage of one bounded unary B procedure, not skill learning.

Every admission uses an externally expected content digest, compatibility
identity and CJT grant. Stored provenance is a claim, not qualification. There
is no evaluation of user code, no native state write and no model import.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

PACKAGE_SCHEMA = "cas-meta3-procedure-package/0.1"
BASELINE_SHA = "0917267b1354e5d036263eaa6ba9a7197eafb776"
META2_SOURCE_SHA = "b5f1718e63a2b5cf72b4b606d513d0524b9226ac"
IR_SCHEMA = "cas-meta2-program/0.1"
MAX_PACKAGE_BYTES = 65536
MAX_REGISTRY_BYTES = 512 * 1024 * 1024
MAX_PACKAGES = 4096
REGISTRY_SCHEMA = "cas-meta3-procedure-registry/0.1"
DEPENDENCY_ROOT = Path(__file__).resolve().parents[2] / "CAS_META_2_COMPOSITION"
DEPENDENCY_FILES = ("cas_meta2/__init__.py", "cas_meta2/ir.py", "cas_meta2/codec.py")
# Build-checked against the exact META2_SOURCE_SHA Git objects. Runtime archives
# need only these public source bytes, not a Git executable or .git directory.
PINNED_DEPENDENCY_HASHES = {
    "cas_meta2/__init__.py": "07b7b2f1a52806b819e3820655fa578f3e5241ce2327695f157e542ce06a63da",
    "cas_meta2/ir.py": "02f3ce65ef9c3b54901a38abab2d4f9f272268e7c195f7001fb119bf1d384637",
    "cas_meta2/codec.py": "c6ca7f489f91e4b43225b7ffc4d496490f038c18842266b6d5da05570ca29030",
}
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class RegistryError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise RegistryError(code)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def _sha(value, code="INVALID_SHA256"):
    _require(type(value) is str and _HEX.fullmatch(value) is not None, code)


def _keys(value, expected, code="UNEXPECTED_PACKAGE_FIELDS"):
    _require(type(value) is dict and set(value) == set(expected), code)


def _pairs(items):
    value = {}
    for key, item in items:
        _require(key not in value, "DUPLICATE_JSON_FIELD")
        value[key] = item
    return value


def _decode(payload):
    _require(type(payload) is bytes and 0 < len(payload) <= MAX_PACKAGE_BYTES, "PACKAGE_BYTE_CEILING")
    def forbidden(_):
        raise RegistryError("NONFINITE_PACKAGE_VALUE")
    try:
        result = json.loads(payload, object_pairs_hook=_pairs, parse_constant=forbidden)
    except RegistryError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise RegistryError("INVALID_PACKAGE_JSON") from error
    _require(type(result) is dict, "PACKAGE_OBJECT_REQUIRED")
    return result


def canonical_package(package):
    """Canonicalize bounded JSON data. This alone grants no admission."""
    if type(package) is bytes:
        package = _decode(package)
    _require(type(package) is dict, "PACKAGE_OBJECT_REQUIRED")
    try:
        payload = _canonical(package)
    except (TypeError, ValueError, RecursionError) as error:
        raise RegistryError("INVALID_PACKAGE_JSON") from error
    _require(0 < len(payload) <= MAX_PACKAGE_BYTES, "PACKAGE_BYTE_CEILING")
    return payload


def package_digest(package):
    return sha256(canonical_package(package)).hexdigest()


def verify_dependency_git():
    """Optional build check; actually compare literal pins with frozen Git objects.

    This separate result is not stored in registry metadata, so an archived
    runtime and a Git checkout use exactly the same portable dependency identity.
    """
    receipt = dependency_receipt()
    try:
        root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=DEPENDENCY_ROOT,
            check=True, capture_output=True, text=True).stdout.strip()).resolve()
        hashes = {}
        for name in DEPENDENCY_FILES:
            relative = (DEPENDENCY_ROOT / name).resolve().relative_to(root).as_posix()
            raw = subprocess.run(["git", "show", META2_SOURCE_SHA + ":" + relative], cwd=root,
                                 check=True, capture_output=True).stdout
            hashes[name] = sha256(raw).hexdigest()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise RegistryError("PINNED_META2_DEPENDENCY_UNAVAILABLE") from error
    _require(hashes == PINNED_DEPENDENCY_HASHES, "PINNED_META2_GIT_OBJECT_MISMATCH")
    return {**receipt, "verified_against_git": True}


def dependency_receipt():
    """Fresh byte checks against literal b5f1718e pins; no Git/model execution."""
    for name, checksum in PINNED_DEPENDENCY_HASHES.items():
        path = DEPENDENCY_ROOT / name
        _require(path.is_file() and not path.is_symlink()
                 and sha256(path.read_bytes()).hexdigest() == checksum, "PINNED_META2_DEPENDENCY_CHANGED")
    return {"schema": "cas-meta3-pure-dependency-receipt/0.1", "source_sha": META2_SOURCE_SHA,
            "files": dict(PINNED_DEPENDENCY_HASHES), "binding": "LITERAL_SHA256_PINS",
            "verified_against_git": False}


def meta2_dependency_path():
    """Return the checked sibling root; caller may import its pinned pure modules."""
    dependency_receipt()
    return DEPENDENCY_ROOT.resolve()


def _pure_module(name):
    path = meta2_dependency_path()
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    # A preloaded module from a different checkout must not defeat file hashes.
    for loaded_name in ("cas_meta2", "cas_meta2.ir", "cas_meta2.codec"):
        if loaded_name in sys.modules:
            filename = getattr(sys.modules[loaded_name], "__file__", None)
            relative = "cas_meta2/__init__.py" if loaded_name == "cas_meta2" else loaded_name.replace(".", "/") + ".py"
            expected = path / relative
            _require(type(filename) is str and Path(filename).resolve() == expected, "UNTRUSTED_META2_IMPORT_PATH")
    module = importlib.import_module("cas_meta2." + name)
    package = sys.modules["cas_meta2"]
    _require(Path(module.__file__).resolve() == path / ("cas_meta2/" + name + ".py")
             and Path(package.__file__).resolve() == path / "cas_meta2/__init__.py", "UNTRUSTED_META2_IMPORT_PATH")
    dependency_receipt()
    return module


def _ir():
    return _pure_module("ir")


def checked_codec():
    """Import the pinned pure codec and reject alternate preloaded module paths."""
    return _pure_module("codec")


def _compatibility(value):
    _keys(value, ("baseline_sha", "meta2_source_sha", "ir_schema", "native_schema_sha256", "model_digest",
                  "parameter_bytes_sha256", "software_digest", "topology_sha256", "operation_contracts", "decoder_contracts"),
          "INVALID_COMPATIBILITY_FIELDS")
    _require(value["baseline_sha"] == BASELINE_SHA and value["meta2_source_sha"] == META2_SOURCE_SHA
             and value["ir_schema"] == IR_SCHEMA, "UNSUPPORTED_COMPATIBILITY_VERSION")
    for key in ("native_schema_sha256", "model_digest", "parameter_bytes_sha256", "software_digest", "topology_sha256"):
        _sha(value[key], "INVALID_COMPATIBILITY_DIGEST")
    _keys(value["operation_contracts"], ("^6",), "INVALID_OPERATION_IDENTITY")
    _keys(value["decoder_contracts"], ("A", "B"), "INVALID_DECODER_IDENTITY")
    for checksum in (*value["operation_contracts"].values(), *value["decoder_contracts"].values()):
        _sha(checksum, "INVALID_COMPATIBILITY_DIGEST")


def validate_package(package, *, expected_digest, trusted_compatibility, permitted_cjts):
    """Admit data only. Caller must independently establish its trusted inputs."""
    _sha(expected_digest, "INVALID_EXPECTED_PACKAGE_DIGEST")
    payload = canonical_package(package)
    _require(sha256(payload).hexdigest() == expected_digest, "EXPECTED_PACKAGE_DIGEST_MISMATCH")
    value = _decode(payload)
    _keys(value, ("schema", "kind", "program", "io", "required_cjts", "compatibility", "provenance"))
    _require(value["schema"] == PACKAGE_SCHEMA and value["kind"] == "UNARY_CJT_PROCEDURE", "UNSUPPORTED_PACKAGE_KIND")
    _compatibility(value["compatibility"])
    _compatibility(trusted_compatibility)
    _require(value["compatibility"] == trusted_compatibility, "CALLER_COMPATIBILITY_MISMATCH")
    _require(type(permitted_cjts) in (list, tuple, set, frozenset)
             and all(type(cjt) is str and cjt in ("A", "B", "C", "R") for cjt in permitted_cjts), "INVALID_CALLER_CJT_GRANT")
    _require(value["required_cjts"] == ["B"], "B_ONLY_SCOPE_REQUIRED")
    _require("B" in permitted_cjts, "CALLER_CJT_SCOPE_DENIED")
    _keys(value["io"], ("input", "output"), "INVALID_UNARY_IO_CONTRACT")
    for name, producer in (("input", "A"), ("output", "B")):
        port = value["io"][name]
        _keys(port, ("kind", "producer_cjt_id", "dtype", "shape"), "INVALID_UNARY_IO_CONTRACT")
        _require(port["kind"] == "ACCEPTED_EFFECT" and port["producer_cjt_id"] == producer
                 and port["dtype"] == "float32" and type(port["shape"]) is list
                 and all(type(size) is int for size in port["shape"]) and port["shape"] == [1, 2, 4],
                 "INVALID_UNARY_IO_CONTRACT")
    ir = _ir()
    try:
        ir.validate_program(value["program"])
    except ir.IRValidationError as error:
        raise RegistryError("INVALID_META2_PROGRAM:" + error.code) from error
    program = value["program"]
    _require(len(program["procedures"]) == 1 and program["entry"] in program["procedures"], "ONE_B_PROCEDURE_REQUIRED")
    procedure = program["procedures"][program["entry"]]
    _require(procedure == {"input": "arg", "allowed_cjts": ["B"], "steps": [
        {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}, "ONE_B_PROCEDURE_REQUIRED")
    provenance = value["provenance"]
    _keys(provenance, ("source_program_sha256", "source_receipt_sha256", "parent_package_sha256"), "INVALID_PROVENANCE_FIELDS")
    _require(provenance["source_program_sha256"] == sha256(ir.canonical_program(program)).hexdigest(), "SOURCE_PROGRAM_DIGEST_MISMATCH")
    for key in ("source_receipt_sha256", "parent_package_sha256"):
        if provenance[key] is not None:
            _sha(provenance[key], "INVALID_PROVENANCE_DIGEST")
    return value


_SCHEMA_SQL = {
    "registry_metadata": "CREATE TABLE registry_metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1),payload BLOB NOT NULL)",
    "packages": "CREATE TABLE packages(sequence INTEGER PRIMARY KEY,package_digest TEXT UNIQUE NOT NULL,package_bytes BLOB NOT NULL,receipt_bytes BLOB NOT NULL)",
    "packages_no_update": "CREATE TRIGGER packages_no_update BEFORE UPDATE ON packages BEGIN SELECT RAISE(ABORT,'immutable packages'); END",
    "packages_no_delete": "CREATE TRIGGER packages_no_delete BEFORE DELETE ON packages BEGIN SELECT RAISE(ABORT,'immutable packages'); END",
    "metadata_no_update": "CREATE TRIGGER metadata_no_update BEFORE UPDATE ON registry_metadata BEGIN SELECT RAISE(ABORT,'immutable metadata'); END",
    "metadata_no_delete": "CREATE TRIGGER metadata_no_delete BEFORE DELETE ON registry_metadata BEGIN SELECT RAISE(ABORT,'immutable metadata'); END",
}
_DDL = ";\n".join(_SCHEMA_SQL.values()) + ";"


def _path_check(path):
    for item in (path, *path.parents):
        _require(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)(), "REGISTRY_LINK_PATH_REFUSED")
    _require(not path.exists() or path.is_file(), "REGISTRY_FILE_REQUIRED")
    if path.exists():
        _require(path.stat().st_size <= MAX_REGISTRY_BYTES, "REGISTRY_BYTE_CEILING")


class ProcedureRegistry:
    """An explicit storage boundary. No update/delete/promote/execute methods."""
    def __init__(self, path):
        self.path = Path(path).absolute()
        self._closed = False
        _path_check(self.path)

    def __enter__(self):
        _require(not self._closed, "REGISTRY_CLOSED")
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._closed = True

    def _check(self):
        _require(not self._closed, "REGISTRY_CLOSED")
        _path_check(self.path)

    @staticmethod
    def _scan(conn, dependency):
        try:
            return ProcedureRegistry._scan_rows(conn, dependency)
        except RegistryError:
            raise
        except (sqlite3.DatabaseError, KeyError, TypeError, ValueError, OverflowError) as error:
            raise RegistryError("MALFORMED_EXISTING_REGISTRY") from error

    @staticmethod
    def _scan_rows(conn, dependency):
        definitions = {name: sql for name, sql in conn.execute(
            "SELECT name,sql FROM sqlite_master WHERE type IN ('table','trigger')")}
        _require(definitions == _SCHEMA_SQL, "REGISTRY_SCHEMA_MISMATCH")
        metadata = list(conn.execute("SELECT singleton,payload FROM registry_metadata"))
        expected_meta = {"schema": REGISTRY_SCHEMA, "dependency": dependency}
        _require(len(metadata) == 1 and metadata[0][0] == 1 and type(metadata[0][1]) is bytes
                 and metadata[0][1] == _canonical(expected_meta), "REGISTRY_DEPENDENCY_MISMATCH")
        count = conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0]
        _require(count <= MAX_PACKAGES, "REGISTRY_PACKAGE_CEILING")
        # Check lengths in SQL before asking SQLite to materialize a payload.
        lengths = list(conn.execute("SELECT length(package_bytes),length(receipt_bytes) FROM packages"))
        _require(all(type(a) is int and type(b) is int and 0 < a <= MAX_PACKAGE_BYTES
                     and 0 < b <= MAX_PACKAGE_BYTES for a, b in lengths), "PACKAGE_BYTE_CEILING")
        previous, result = None, {}
        for sequence, identifier, payload, receipt_payload in conn.execute("SELECT * FROM packages ORDER BY sequence"):
            _sha(identifier, "STORED_PACKAGE_DIGEST_INVALID")
            _require(type(payload) is bytes and type(receipt_payload) is bytes, "MALFORMED_EXISTING_REGISTRY")
            _require(type(sequence) is int and sequence == len(result) + 1 and identifier not in result
                     and sha256(payload).hexdigest() == identifier, "STORED_PACKAGE_BYTES_CHANGED")
            package = _decode(payload)
            _require(canonical_package(package) == payload, "STORED_PACKAGE_NOT_CANONICAL")
            receipt = {"schema": "cas-meta3-storage-receipt/0.1", "sequence": sequence,
                "package_digest": identifier, "package_bytes": len(payload),
                "program_digest": _digest(package["program"]), "previous_receipt_digest": previous,
                "storage_status": "STORAGE_ONLY", "qualification_status": "UNQUALIFIED",
                "dependency_digest": _digest(dependency)}
            receipt["receipt_digest"] = _digest(receipt)
            _require(_canonical(receipt) == receipt_payload, "STORED_INSTALL_RECEIPT_MISMATCH")
            result[identifier] = (payload, receipt)
            previous = receipt["receipt_digest"]
        return result

    def _open_existing(self, *, readonly):
        _require(self.path.is_file(), "REGISTRY_NOT_FOUND")
        return sqlite3.connect(self.path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True)

    def install(self, package, *, expected_digest, trusted_compatibility, permitted_cjts):
        self._check()
        # Every caller-controlled rejection precedes database creation/writes.
        checked = validate_package(package, expected_digest=expected_digest,
                                   trusted_compatibility=trusted_compatibility, permitted_cjts=permitted_cjts)
        payload, dependency = canonical_package(checked), dependency_receipt()
        existing = self.path.exists()
        if existing:
            conn = self._open_existing(readonly=False)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            _path_check(self.path)
            conn = sqlite3.connect(self.path)
        try:
            if not existing:
                conn.executescript(_DDL)
                conn.execute("INSERT INTO registry_metadata VALUES(1,?)", (_canonical({"schema": REGISTRY_SCHEMA, "dependency": dependency}),))
                conn.commit()
            conn.execute("BEGIN IMMEDIATE")
            rows = self._scan(conn, dependency)
            if expected_digest in rows:
                _require(rows[expected_digest][0] == payload, "PACKAGE_DIGEST_COLLISION")
                conn.rollback()
                return deepcopy(rows[expected_digest][1])
            _require(len(rows) < MAX_PACKAGES, "REGISTRY_PACKAGE_CEILING")
            last = list(rows.values())[-1][1]["receipt_digest"] if rows else None
            receipt = {"schema": "cas-meta3-storage-receipt/0.1", "sequence": len(rows) + 1,
                "package_digest": expected_digest, "package_bytes": len(payload), "program_digest": _digest(checked["program"]),
                "previous_receipt_digest": last, "storage_status": "STORAGE_ONLY", "qualification_status": "UNQUALIFIED",
                "dependency_digest": _digest(dependency)}
            receipt["receipt_digest"] = _digest(receipt)
            conn.execute("INSERT INTO packages VALUES(?,?,?,?)", (len(rows) + 1, expected_digest, payload, _canonical(receipt)))
            conn.commit()
            return deepcopy(receipt)
        except sqlite3.DatabaseError as error:
            conn.rollback()
            raise RegistryError("MALFORMED_EXISTING_REGISTRY") from error
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def retrieve(self, expected_digest, *, trusted_compatibility, permitted_cjts):
        self._check()
        _sha(expected_digest, "INVALID_EXPECTED_PACKAGE_DIGEST")
        dependency = dependency_receipt()
        conn = self._open_existing(readonly=True)
        try:
            rows = self._scan(conn, dependency)
            _require(expected_digest in rows, "UNKNOWN_PACKAGE_DIGEST")
            return validate_package(rows[expected_digest][0], expected_digest=expected_digest,
                                    trusted_compatibility=trusted_compatibility, permitted_cjts=permitted_cjts)
        finally:
            conn.close()
