"""Pure procedural-storage tests. Synthetic identities are NOT native evidence."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import types

import pytest

from cas_meta3 import registry as r


def make_package(entry="stored_b"):
    """Fixture-only compatibility hashes; no model or qualification is present."""
    program = {"schema": r.IR_SCHEMA, "entry": entry, "procedures": {entry: {
        "input": "arg", "allowed_cjts": ["B"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}
    fake = lambda label: sha256(("MOCK IDENTITY ONLY:" + label).encode()).hexdigest()
    return {"schema": r.PACKAGE_SCHEMA, "kind": "UNARY_CJT_PROCEDURE", "program": program,
        "io": {"input": {"kind": "ACCEPTED_EFFECT", "producer_cjt_id": "A", "dtype": "float32", "shape": [1, 2, 4]},
               "output": {"kind": "ACCEPTED_EFFECT", "producer_cjt_id": "B", "dtype": "float32", "shape": [1, 2, 4]}},
        "required_cjts": ["B"], "compatibility": {"baseline_sha": r.BASELINE_SHA, "meta2_source_sha": r.META2_SOURCE_SHA,
            "ir_schema": r.IR_SCHEMA, "native_schema_sha256": fake("schema"), "model_digest": fake("model"),
            "parameter_bytes_sha256": fake("parameters"), "software_digest": fake("software"),
            "topology_sha256": fake("topology"), "operation_contracts": {"^6": fake("operation")},
            "decoder_contracts": {"A": fake("decoder-a"), "B": fake("decoder-b")}},
        "provenance": {"source_program_sha256": r._digest(program), "source_receipt_sha256": None,
                       "parent_package_sha256": None}}


def arguments(package):
    return {"expected_digest": r.package_digest(package), "trusted_compatibility": deepcopy(package["compatibility"]),
            "permitted_cjts": ("B",)}


def install(path, package=None):
    package = package or make_package()
    with r.ProcedureRegistry(path) as registry:
        receipt = registry.install(package, **arguments(package))
    return package, receipt


def read(path, package):
    with r.ProcedureRegistry(path) as registry:
        args = arguments(package)
        expected = args.pop("expected_digest")
        return registry.retrieve(expected, **args)


def corrupt_payload(path, raw):
    """Simulate out-of-band disk tampering, deliberately bypassing the API."""
    conn = sqlite3.connect(path)
    trigger = conn.execute("SELECT sql FROM sqlite_master WHERE name='packages_no_update'").fetchone()[0]
    conn.execute("DROP TRIGGER packages_no_update")
    conn.execute("UPDATE packages SET package_bytes=? WHERE sequence=1", (raw,))
    conn.execute(trigger)
    conn.commit()
    conn.close()


def test_dependency_files_are_verified_against_exact_frozen_git_revision():
    before = "torch" in sys.modules
    receipt = r.dependency_receipt()
    assert receipt["source_sha"] == "b5f1718e63a2b5cf72b4b606d513d0524b9226ac"
    assert receipt["verified_against_git"] is False
    assert receipt["binding"] == "LITERAL_SHA256_PINS"
    verified = r.verify_dependency_git()
    assert verified == {**receipt, "verified_against_git": True}
    assert set(receipt["files"]) == {"cas_meta2/__init__.py", "cas_meta2/ir.py", "cas_meta2/codec.py"}
    for name, checksum in receipt["files"].items():
        assert sha256((r.meta2_dependency_path() / name).read_bytes()).hexdigest() == checksum
    assert ("torch" in sys.modules) == before


def test_install_retrieve_is_storage_only_and_detached(tmp_path):
    path = tmp_path / "registry.db"
    package, receipt = install(path)
    assert receipt["storage_status"] == "STORAGE_ONLY" and receipt["qualification_status"] == "UNQUALIFIED"
    assert receipt["sequence"] == 1 and receipt["previous_receipt_digest"] is None
    result = read(path, package)
    assert result == package and result is not package
    result["program"]["entry"] = "caller-mutated-copy"
    assert read(path, package) == package


def test_repeated_same_install_is_read_only_idempotent(tmp_path):
    path = tmp_path / "registry.db"
    package, first = install(path)
    before = path.read_bytes()
    _, second = install(path, package)
    assert first == second and path.read_bytes() == before


def test_distinct_entry_appends_and_preserves_unrelated_package(tmp_path):
    path = tmp_path / "registry.db"
    original, receipt1 = install(path)
    other, receipt2 = install(path, make_package("another_b"))
    assert receipt2["sequence"] == 2 and receipt2["previous_receipt_digest"] == receipt1["receipt_digest"]
    assert read(path, original) == original and read(path, other) == other
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM packages").fetchone()[0] == 2
    conn.close()


def test_provenance_hash_claims_do_not_promote_or_qualify(tmp_path):
    package = make_package()
    package["provenance"]["source_receipt_sha256"] = "1" * 64
    package["provenance"]["parent_package_sha256"] = "2" * 64
    _, receipt = install(tmp_path / "registry.db", package)
    assert receipt["qualification_status"] == "UNQUALIFIED"
    assert receipt["storage_status"] == "STORAGE_ONLY"


def test_real_fresh_subprocess_reopens_bytes_without_parent_objects_or_neural_import(tmp_path):
    path = tmp_path / "registry.db"
    package, receipt = install(path)
    before = path.read_bytes()
    payload = {"path": str(path), **arguments(package)}
    script = '''
import json,os,sys
from cas_meta3.registry import ProcedureRegistry,package_digest,dependency_receipt
request=json.loads(sys.stdin.read())
with ProcedureRegistry(request['path']) as registry:
    package=registry.retrieve(request['expected_digest'],trusted_compatibility=request['trusted_compatibility'],permitted_cjts=request['permitted_cjts'])
print(json.dumps({'pid':os.getpid(),'package':package,'digest':package_digest(package),'torch_loaded':'torch' in sys.modules,'dependency':dependency_receipt()}))
'''
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    process = subprocess.run([sys.executable, "-B", "-c", script], input=json.dumps(payload), text=True,
                             check=True, capture_output=True, env=environment, timeout=30)
    result = json.loads(process.stdout)
    assert result["pid"] != os.getpid() and result["package"] == package
    assert result["digest"] == receipt["package_digest"] and result["torch_loaded"] is False
    assert result["dependency"]["source_sha"] == r.META2_SOURCE_SHA and path.read_bytes() == before


@pytest.mark.parametrize("grant", [(), ("A",), ("C", "R")])
def test_denied_install_does_not_create_database_or_parent_directory(tmp_path, grant):
    package = make_package()
    path = tmp_path / "new-parent" / "registry.db"
    args = arguments(package);args["permitted_cjts"] = grant
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="CALLER_CJT_SCOPE_DENIED"):
            registry.install(package, **args)
    assert not path.parent.exists()


@pytest.mark.parametrize("field", ["native_schema_sha256", "model_digest", "parameter_bytes_sha256", "software_digest", "topology_sha256"])
def test_wrong_trusted_identity_rejects_install_and_retrieval_without_writes(tmp_path, field):
    path = tmp_path / "registry.db"
    package, _ = install(path)
    args = arguments(package);args["trusted_compatibility"][field] = "0" * 64
    before = path.read_bytes()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="CALLER_COMPATIBILITY_MISMATCH"):
            registry.install(package, **args)
        with pytest.raises(r.RegistryError, match="CALLER_COMPATIBILITY_MISMATCH"):
            registry.retrieve(args.pop("expected_digest"), **args)
    assert path.read_bytes() == before


@pytest.mark.parametrize("section,key", [("operation_contracts", "^6"), ("decoder_contracts", "A"), ("decoder_contracts", "B")])
def test_changed_operation_or_decoder_identity_rejects(tmp_path, section, key):
    package = make_package();args = arguments(package)
    args["trusted_compatibility"][section][key] = "0" * 64
    path = tmp_path / "registry.db"
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="CALLER_COMPATIBILITY_MISMATCH"):
            registry.install(package, **args)
    assert not path.exists()


def test_retrieval_grant_cannot_be_inferred_from_package_scope(tmp_path):
    path = tmp_path / "registry.db";package, _ = install(path);before = path.read_bytes()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="CALLER_CJT_SCOPE_DENIED"):
            registry.retrieve(r.package_digest(package), trusted_compatibility=package["compatibility"], permitted_cjts=("A",))
    assert path.read_bytes() == before


def test_invented_digest_and_wrong_external_digest_are_rejected(tmp_path):
    path = tmp_path / "registry.db";package, _ = install(path);before = path.read_bytes()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="UNKNOWN_PACKAGE_DIGEST"):
            registry.retrieve("0" * 64, trusted_compatibility=package["compatibility"], permitted_cjts=("B",))
        args = arguments(package);args["expected_digest"] = "0" * 64
        with pytest.raises(r.RegistryError, match="EXPECTED_PACKAGE_DIGEST_MISMATCH"):
            registry.install(package, **args)
    assert path.read_bytes() == before


@pytest.mark.parametrize("section", [None, "io", "compatibility", "provenance"])
def test_unknown_fields_never_write_even_with_matching_self_digest(tmp_path, section):
    package = make_package()
    target = package if section is None else package[section]
    target["execute_python"] = "raise RuntimeError('must remain inert data')"
    path = tmp_path / "registry.db"
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError):
            registry.install(package, **arguments(package))
    assert not path.exists()


@pytest.mark.parametrize("replacement", [True, False, 1.0, "1"])
def test_integer_shape_types_are_exact_and_not_python_equal_values(tmp_path, replacement):
    package = make_package();package["io"]["input"]["shape"][0] = replacement
    path = tmp_path / "registry.db"
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="INVALID_UNARY_IO_CONTRACT"):
            registry.install(package, **arguments(package))
    assert not path.exists()


def test_only_exact_one_run_b_contract_is_admitted(tmp_path):
    package = make_package();proc = package["program"]["procedures"]["stored_b"]
    proc["steps"].append({"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v1"})
    package["provenance"]["source_program_sha256"] = r._digest(package["program"])
    with r.ProcedureRegistry(tmp_path / "registry.db") as registry:
        with pytest.raises(r.RegistryError, match="ONE_B_PROCEDURE_REQUIRED"):
            registry.install(package, **arguments(package))


def test_source_program_digest_is_not_an_unchecked_claim(tmp_path):
    package = make_package();package["provenance"]["source_program_sha256"] = "0" * 64
    path = tmp_path / "registry.db"
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="SOURCE_PROGRAM_DIGEST_MISMATCH"):
            registry.install(package, **arguments(package))
    assert not path.exists()


def test_database_triggers_reject_overwrite_and_delete(tmp_path):
    path = tmp_path / "registry.db";install(path)
    conn = sqlite3.connect(path)
    for sql in ("UPDATE packages SET package_bytes=x'00'", "DELETE FROM packages", "DELETE FROM registry_metadata"):
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(sql)
        conn.rollback()
    conn.close()


def test_changed_stored_bytes_rejected_without_further_writes(tmp_path):
    path = tmp_path / "registry.db";package, _ = install(path)
    corrupt_payload(path, r.canonical_package(make_package("other_name")))
    before = path.read_bytes()
    with pytest.raises(r.RegistryError, match="STORED_PACKAGE_BYTES_CHANGED"):
        read(path, package)
    assert path.read_bytes() == before


def test_stored_payload_ceiling_is_checked_before_json_parse(tmp_path, monkeypatch):
    path = tmp_path / "registry.db";package, _ = install(path)
    corrupt_payload(path, b"x" * (r.MAX_PACKAGE_BYTES + 1))
    def should_not_parse(_):raise AssertionError("oversized stored bytes reached JSON parser")
    monkeypatch.setattr(r, "_decode", should_not_parse)
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="PACKAGE_BYTE_CEILING"):
            registry.retrieve(r.package_digest(package), trusted_compatibility=package["compatibility"], permitted_cjts=("B",))


def test_incoming_bytes_ceiling_precedes_json_parse():
    with pytest.raises(r.RegistryError, match="PACKAGE_BYTE_CEILING"):
        r.canonical_package(b"{" + b"x" * r.MAX_PACKAGE_BYTES)
    with pytest.raises(r.RegistryError, match="DUPLICATE_JSON_FIELD"):
        r.canonical_package(b'{"schema":1,"schema":2}')


def test_unrelated_existing_sqlite_database_is_not_modified(tmp_path):
    path = tmp_path / "other.db"
    conn = sqlite3.connect(path);conn.execute("CREATE TABLE unrelated(value TEXT)");conn.commit();conn.close()
    before = path.read_bytes();package = make_package()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="REGISTRY_SCHEMA_MISMATCH"):
            registry.install(package, **arguments(package))
    assert path.read_bytes() == before


def test_closed_registry_cannot_reopen_itself(tmp_path):
    registry = r.ProcedureRegistry(tmp_path / "registry.db");registry.close();package = make_package()
    with pytest.raises(r.RegistryError, match="REGISTRY_CLOSED"):
        registry.install(package, **arguments(package))


def test_archive_without_git_reopens_checkout_registry_in_fresh_process(tmp_path):
    """Real file/process persistence, but synthetic identities and no native run."""
    original = tmp_path / "original.db"
    package, _ = install(original)
    archive = tmp_path / "source-archive"
    meta3 = archive / "CAS_META_3_PROCEDURAL_MEMORY"
    meta2 = archive / "CAS_META_2_COMPOSITION"
    (meta3 / "cas_meta3").mkdir(parents=True)
    (meta2 / "cas_meta2").mkdir(parents=True)
    for name in ("__init__.py", "registry.py"):
        shutil.copyfile(Path(r.__file__).parent / name, meta3 / "cas_meta3" / name)
    for name in r.DEPENDENCY_FILES:
        shutil.copyfile(r.DEPENDENCY_ROOT / name, meta2 / name)
    db = archive / "copied-registry.db"
    shutil.copyfile(original, db)
    before = db.read_bytes()
    environment = {**os.environ, "PYTHONPATH": str(meta3), "PATH": ""}
    script = '''
import json,sys
from cas_meta3.registry import ProcedureRegistry,dependency_receipt,checked_codec,verify_dependency_git,RegistryError
request=json.loads(sys.stdin.read())
with ProcedureRegistry(request['path']) as registry:
    package=registry.retrieve(request['expected_digest'],trusted_compatibility=request['trusted_compatibility'],permitted_cjts=request['permitted_cjts'])
codec=checked_codec()
try:
    verify_dependency_git()
except RegistryError as error:
    git_error=error.code
else:
    raise AssertionError('Git was unavailable but verification claimed success')
print(json.dumps({'package':package,'dependency':dependency_receipt(),'git_error':git_error,'codec_file':codec.__file__,'torch_loaded':'torch' in sys.modules}))
'''
    process = subprocess.run([sys.executable, "-B", "-c", script], input=json.dumps({"path": str(db), **arguments(package)}),
        text=True, check=True, capture_output=True, env=environment, cwd=archive, timeout=30)
    result = json.loads(process.stdout)
    assert result["package"] == package and result["dependency"] == r.dependency_receipt()
    assert result["dependency"]["verified_against_git"] is False
    assert result["git_error"] == "PINNED_META2_DEPENDENCY_UNAVAILABLE"
    assert Path(result["codec_file"]).resolve() == (meta2 / "cas_meta2/codec.py").resolve()
    assert result["torch_loaded"] is False and db.read_bytes() == before
    assert not list(archive.rglob(".git"))


@pytest.mark.parametrize("module_name", ["cas_meta2", "cas_meta2.ir", "cas_meta2.codec"])
def test_alternate_preloaded_module_path_is_rejected_before_import(monkeypatch, module_name):
    package = make_package()
    fake_module = types.ModuleType(module_name)
    fake_module.__file__ = str(Path(r.__file__).parent / "untrusted.py")
    monkeypatch.setitem(sys.modules, module_name, fake_module)
    for action in (r.checked_codec, lambda: r.validate_package(package, **arguments(package))):
        with pytest.raises(r.RegistryError, match="UNTRUSTED_META2_IMPORT_PATH"):
            action()


def test_checked_codec_uses_exact_pinned_path_without_neural_import():
    before = "torch" in sys.modules
    codec = r.checked_codec()
    assert Path(codec.__file__).resolve() == r.meta2_dependency_path() / "cas_meta2/codec.py"
    assert ("torch" in sys.modules) == before


def test_changed_dependency_pin_is_not_silently_accepted(monkeypatch):
    pins = dict(r.PINNED_DEPENDENCY_HASHES)
    pins["cas_meta2/codec.py"] = "0" * 64
    monkeypatch.setattr(r, "PINNED_DEPENDENCY_HASHES", pins)
    with pytest.raises(r.RegistryError, match="PINNED_META2_DEPENDENCY_CHANGED"):
        r.dependency_receipt()


def test_invalid_existing_non_sqlite_file_is_not_modified(tmp_path):
    path = tmp_path / "not-sqlite.db"
    path.write_bytes(b"fixture-only invalid database bytes")
    before = path.read_bytes()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="MALFORMED_EXISTING_REGISTRY"):
            registry.install(make_package(), **arguments(make_package()))
    assert path.read_bytes() == before


@pytest.mark.parametrize("value", ["not a blob", 123])
def test_wrong_stored_sqlite_cell_types_are_typed_rejections_and_no_writes(tmp_path, value):
    path = tmp_path / "registry.db"
    package, _ = install(path)
    corrupt_payload(path, value)
    before = path.read_bytes()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="MALFORMED_EXISTING_REGISTRY"):
            registry.install(package, **arguments(package))
    assert path.read_bytes() == before


def test_missing_program_in_stored_object_is_typed_rejection_and_no_writes(tmp_path):
    path = tmp_path / "registry.db"
    package, _ = install(path)
    malformed = deepcopy(package)
    del malformed["program"]
    raw = r.canonical_package(malformed)
    conn = sqlite3.connect(path)
    trigger = conn.execute("SELECT sql FROM sqlite_master WHERE name='packages_no_update'").fetchone()[0]
    conn.execute("DROP TRIGGER packages_no_update")
    conn.execute("UPDATE packages SET package_bytes=?,package_digest=?", (raw, sha256(raw).hexdigest()))
    conn.execute(trigger)
    conn.commit();conn.close()
    before = path.read_bytes()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="MALFORMED_EXISTING_REGISTRY"):
            registry.install(package, **arguments(package))
    assert path.read_bytes() == before


def test_same_named_but_weakened_trigger_is_not_append_only_evidence(tmp_path):
    path = tmp_path / "registry.db"
    package, _ = install(path)
    conn = sqlite3.connect(path)
    conn.execute("DROP TRIGGER packages_no_update")
    conn.execute("CREATE TRIGGER packages_no_update BEFORE UPDATE ON packages BEGIN SELECT 1; END")
    conn.commit();conn.close()
    before = path.read_bytes()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="REGISTRY_SCHEMA_MISMATCH"):
            registry.install(package, **arguments(package))
    assert path.read_bytes() == before


def test_nullable_schema_and_null_lengths_are_rejected_without_writes(tmp_path):
    path = tmp_path / "registry.db"
    conn = sqlite3.connect(path)
    conn.executescript(r._DDL.replace("package_bytes BLOB NOT NULL", "package_bytes BLOB"))
    conn.execute("INSERT INTO registry_metadata VALUES(1,?)", (r._canonical({"schema": r.REGISTRY_SCHEMA, "dependency": r.dependency_receipt()}),))
    conn.execute("INSERT INTO packages VALUES(1,?,?,?)", ("0" * 64, None, b"{}"))
    assert conn.execute("SELECT length(package_bytes) FROM packages").fetchone()[0] is None
    conn.commit();conn.close()
    before = path.read_bytes()
    package = make_package()
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="REGISTRY_SCHEMA_MISMATCH"):
            registry.install(package, **arguments(package))
    assert path.read_bytes() == before


def test_malformed_program_is_a_registry_error_not_an_unhandled_ir_error(tmp_path):
    package = make_package()
    package["program"] = {"schema": r.IR_SCHEMA}
    path = tmp_path / "registry.db"
    with r.ProcedureRegistry(path) as registry:
        with pytest.raises(r.RegistryError, match="INVALID_META2_PROGRAM:"):
            registry.install(package, **arguments(package))
    assert not path.exists()
