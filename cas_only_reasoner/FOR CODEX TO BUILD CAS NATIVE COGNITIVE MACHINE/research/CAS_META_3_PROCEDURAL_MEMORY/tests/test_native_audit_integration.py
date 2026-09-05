"""Synthetic audit integration only: real storage, never real neural outputs.

Registry databases below contain explicitly synthetic compatibility identities.
Native replay is mocked only to examine adapter boundaries. No fixture is a
complete successful native run, and every full-audit receipt tested is rejected.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import struct
import sys
from types import SimpleNamespace

import pytest

from cas_meta3 import registry, linker
from tools import audit_native_demo as audit


pytestmark = pytest.mark.not_gpu
SOURCE = {"native_schema_sha256": "a" * 64, "synthetic_identity_only": True}
JOB = "synthetic_registry_audit"


def fake_hash(label):
    return sha256(("SYNTHETIC NOT NATIVE:" + label).encode()).hexdigest()


class DiskFixture:
    def __init__(self, base):
        self.roots = {"demo": base / "demo", "native": base / "native"}
        for root in self.roots.values():
            root.mkdir(parents=True)
        self.inventory = {}
        self.receipt = {"job": JOB, "synthetic_component_only": True}

    def local_path(self, name):
        root, relative = name.split("/", 1)
        return self.roots[root] / relative

    def register(self, name):
        path = self.local_path(name)
        root, relative = name.split("/", 1)
        self.inventory[name] = {"root": root, "path": relative, "bytes": path.stat().st_size,
                                "sha256": audit.file_hash(path)}
        return self.inventory[name]["sha256"]

    def put(self, name, value):
        path = self.local_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else audit.canonical(value) + b"\n")
        return self.register(name)

    def path(self, name):
        path = self.local_path(name)
        audit.require(name in self.inventory and path.is_file(), "UNINDEXED_FIXTURE_FILE")
        audit.require(audit.file_hash(path) == self.inventory[name]["sha256"], "FIXTURE_BYTES_CHANGED")
        return path

    def raw(self, name):
        return self.path(name).read_bytes()

    def json(self, name):
        return audit.json_bytes(self.raw(name))

    def same_hash(self, name, expected):
        self.path(name)
        audit.require(self.inventory[name]["sha256"] == expected, "SEALED_MEMBER_HASH_MISMATCH:" + name)

    def mutate(self, name, change):
        value = self.json(name)
        change(value)
        return self.put(name, value)


def compatibility_fixture(tmp_path):
    packet = DiskFixture(tmp_path)
    identity = {"model": {"model_digest": fake_hash("model"), "parameter_bytes_sha256": fake_hash("parameters")},
        "stored_model_digest": fake_hash("model"), "software_digest": fake_hash("software"),
        "topology": {"fixture-only": "A to B"}, "contracts": {"^6": fake_hash("operation")},
        "decoders": {"A": fake_hash("decoder-a"), "B": fake_hash("decoder-b")}}
    reference = {"status": "EXECUTED", "reference": True, "runtime_identity": identity,
        "runtime_identity_after": deepcopy(identity), "synthetic_component_only": True}
    expected = {"baseline_sha": registry.BASELINE_SHA, "meta2_source_sha": registry.META2_SOURCE_SHA,
        "ir_schema": registry.IR_SCHEMA, "native_schema_sha256": SOURCE["native_schema_sha256"],
        "model_digest": fake_hash("model"), "parameter_bytes_sha256": fake_hash("parameters"),
        "software_digest": fake_hash("software"), "topology_sha256": audit.digest(identity["topology"]),
        "operation_contracts": {"^6": fake_hash("operation")},
        "decoder_contracts": {"A": fake_hash("decoder-a"), "B": fake_hash("decoder-b")}}
    reference_hash = packet.put("demo/reference_result.json", reference)
    verdict_hash = packet.put("demo/reference_verdict.json", {"synthetic_placeholder": "NOT A NATIVE VERDICT"})
    packet.put("demo/trusted_compatibility.json", {"schema": "cas-meta3-trusted-native-compatibility/0.1",
        "job": JOB, "source": deepcopy(SOURCE), "source_kind": "INDEPENDENT_DIRECT_NATIVE_REFERENCE",
        "package_identity_used_as_authority": False, "runtime_identity": deepcopy(identity), "compatibility": expected,
        "reference_result_sha256": reference_hash, "reference_verdict_sha256": verdict_hash})
    return packet, reference, expected


def registry_fixture(tmp_path):
    packet, reference, compatibility = compatibility_fixture(tmp_path)
    program = {"schema": registry.IR_SCHEMA, "entry": "stored_b", "procedures": {"stored_b": {
        "input": "arg", "allowed_cjts": ["B"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}
    package = {"schema": registry.PACKAGE_SCHEMA, "kind": "UNARY_CJT_PROCEDURE", "program": program,
        "io": {name: {"kind": "ACCEPTED_EFFECT", "producer_cjt_id": producer, "dtype": "float32", "shape": [1, 2, 4]}
               for name, producer in (("input", "A"), ("output", "B"))},
        "required_cjts": ["B"], "compatibility": compatibility,
        "provenance": {"source_program_sha256": audit.digest(program),
            "source_receipt_sha256": packet.inventory["demo/reference_result.json"]["sha256"], "parent_package_sha256": None}}
    expected = registry.package_digest(package)
    path = packet.local_path("demo/registry.db")
    with registry.ProcedureRegistry(path) as store:
        installed = store.install(package, expected_digest=expected, trusted_compatibility=compatibility, permitted_cjts=("A", "B"))
    checksum = packet.register("demo/registry.db")
    linked = linker.link_demonstration(package, expected_digest=expected, trusted_compatibility=compatibility, permitted_cjts=("A", "B"))
    packet.receipt["package_digest"] = expected
    packet.put("demo/package.json", package)
    packet.put("demo/retrieved_package.json", package)
    packet.put("demo/writer_receipt.json", {"storage_receipt": installed, "synthetic_component_only": True})
    packet.put("demo/link_receipt.json", linked["link_receipt"])
    reasons = {"forged_package_digest": "UNKNOWN_PACKAGE_DIGEST", "wrong_compatibility": "CALLER_COMPATIBILITY_MISMATCH",
        "denied_child_scope": "CALLER_CJT_SCOPE_DENIED", "denied_parent_scope": "DEMONSTRATION_PARENT_SCOPE_DENIED",
        "wrong_package_schema": "UNSUPPORTED_PACKAGE_KIND"}
    packet.put("demo/rejection_receipt.json", {"schema": "cas-meta3-native-admission-rejections/0.1",
        "cases": [{"case": name, "rejected": True, "reason": reason,
            "candidate_directory_existed_before": False, "candidate_directory_exists_after": False,
            "registry_sha256_before": checksum, "registry_sha256_after": checksum, "native_entrypoint_called": False}
            for name, reason in reasons.items()]})
    return packet, package, compatibility


def test_actual_synthetic_registry_reproduces_all_five_rejections_read_only(tmp_path):
    packet, _, compatibility = registry_fixture(tmp_path)
    before = packet.raw("demo/registry.db")
    linked, report = audit.check_registry(packet, compatibility, registry, linker)
    assert linked == packet.json("demo/link_receipt.json")
    assert report == {"stored_packages": 1, "reproduced_rejections": 5, "qualification_status": "UNQUALIFIED",
                      "altered_package_bytes_cloud_rejection_not_claimed": True}
    assert packet.raw("demo/registry.db") == before and not list(packet.roots["native"].iterdir())


@pytest.mark.parametrize("fail_scan", [False, True])
def test_registry_readonly_connection_is_explicitly_closed_on_success_and_error(tmp_path, monkeypatch, fail_scan):
    packet, _, compatibility = registry_fixture(tmp_path)
    actual_connect = sqlite3.connect
    opened = []
    class TrackedConnection:
        def __init__(self, connection):
            self.connection, self.closed = connection, False
        def execute(self, *args, **kwargs):
            return self.connection.execute(*args, **kwargs)
        def close(self):
            self.closed = True
            self.connection.close()
        def __enter__(self):
            self.connection.__enter__()
            return self
        def __exit__(self, *args):
            return self.connection.__exit__(*args)
    def tracked(database_uri, **kwargs):
        assert database_uri.endswith("?mode=ro&immutable=1") and kwargs == {"uri": True}
        value = TrackedConnection(actual_connect(database_uri, **kwargs))
        opened.append(value)
        return value
    monkeypatch.setattr(audit.sqlite3, "connect", tracked)
    if fail_scan:
        monkeypatch.setattr(registry.ProcedureRegistry, "_scan", lambda *_: (_ for _ in ()).throw(audit.AuditError("SYNTHETIC_SCAN_FAILURE")))
        with pytest.raises(audit.AuditError, match="SYNTHETIC_SCAN_FAILURE"):
            audit.check_registry(packet, compatibility, registry, linker)
    else:
        audit.check_registry(packet, compatibility, registry, linker)
    assert opened and all(value.closed for value in opened)


@pytest.mark.parametrize("mutation", ["retrieved", "provenance", "install-receipt", "link", "rejection-reason", "rejection-count", "rejection-native-write"])
def test_registry_component_rejects_altered_records_even_with_rehashed_files(tmp_path, mutation):
    packet, _, compatibility = registry_fixture(tmp_path)
    if mutation == "retrieved":
        packet.mutate("demo/retrieved_package.json", lambda row: row.__setitem__("kind", "wrong"))
    elif mutation == "provenance":
        packet.mutate("demo/package.json", lambda row: row["provenance"].__setitem__("source_receipt_sha256", "0" * 64))
        packet.receipt["package_digest"] = registry.package_digest(packet.json("demo/package.json"))
        packet.put("demo/retrieved_package.json", packet.json("demo/package.json"))
    elif mutation == "install-receipt":
        packet.mutate("demo/writer_receipt.json", lambda row: row["storage_receipt"].__setitem__("qualification_status", "QUALIFIED"))
    elif mutation == "link":
        packet.mutate("demo/link_receipt.json", lambda row: row.__setitem__("qualification", "QUALIFIED"))
    elif mutation == "rejection-reason":
        packet.mutate("demo/rejection_receipt.json", lambda row: row["cases"][1].__setitem__("reason", "not reproduced"))
    elif mutation == "rejection-count":
        packet.mutate("demo/rejection_receipt.json", lambda row: row["cases"].pop())
    else:
        packet.mutate("demo/rejection_receipt.json", lambda row: row["cases"][0].__setitem__("native_entrypoint_called", True))
    with pytest.raises(ValueError):
        audit.check_registry(packet, compatibility, registry, linker)


def test_registry_stored_payload_tampering_rejects_after_outer_file_rehash(tmp_path):
    packet, _, compatibility = registry_fixture(tmp_path)
    path = packet.local_path("demo/registry.db")
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TRIGGER packages_no_update")
        connection.execute("UPDATE packages SET package_bytes=?", (b'{"synthetic_corruption":true}',))
        connection.commit()
    finally:
        connection.close()
    packet.register("demo/registry.db")
    with pytest.raises(ValueError):
        audit.check_registry(packet, compatibility, registry, linker)


def test_compatibility_is_derived_from_independent_reference_identity(tmp_path):
    packet, reference, expected = compatibility_fixture(tmp_path)
    assert audit.check_compatibility(packet, SOURCE) == (reference, expected)


@pytest.mark.parametrize("field", ["baseline_sha", "meta2_source_sha", "ir_schema", "native_schema_sha256", "model_digest",
    "parameter_bytes_sha256", "software_digest", "topology_sha256", "operation_contracts", "decoder_contracts"])
def test_each_compatibility_field_is_checked_not_taken_from_package(tmp_path, field):
    packet, _, _ = compatibility_fixture(tmp_path)
    packet.mutate("demo/trusted_compatibility.json", lambda row: row["compatibility"].__setitem__(field, "wrong"))
    with pytest.raises(audit.AuditError, match="REFERENCE_DERIVED_COMPATIBILITY_MISMATCH"):
        audit.check_compatibility(packet, SOURCE)


@pytest.mark.parametrize("mutation", ["source", "job", "authority", "runtime-copy", "reference-hash", "verdict-hash", "stored-model", "after-model"])
def test_trusted_compatibility_authority_and_byte_bindings_reject(tmp_path, mutation):
    packet, _, _ = compatibility_fixture(tmp_path)
    if mutation in ("stored-model", "after-model"):
        def change(row):
            if mutation == "stored-model":
                row["runtime_identity"]["stored_model_digest"] = "0" * 64
                row["runtime_identity_after"] = deepcopy(row["runtime_identity"])
            else:
                row["runtime_identity_after"]["software_digest"] = "0" * 64
        packet.mutate("demo/reference_result.json", change)
    else:
        key = {"source": "source", "job": "job", "authority": "package_identity_used_as_authority",
            "runtime-copy": "runtime_identity", "reference-hash": "reference_result_sha256", "verdict-hash": "reference_verdict_sha256"}[mutation]
        packet.mutate("demo/trusted_compatibility.json", lambda row: row.__setitem__(key, True if mutation == "authority" else "wrong"))
    with pytest.raises(audit.AuditError):
        audit.check_compatibility(packet, SOURCE)


def stored_component_fixture(tmp_path, reference):
    packet = DiskFixture(tmp_path)
    folder = "native/reference" if reference else "native/candidate"
    packet.put(folder + "/native.db", b"SYNTHETIC BOUNDARY ONLY, NOT NATIVE SQLITE")
    result = {"status": "EXECUTED", "reference": reference, "selected_action": audit.expected_task()["target"],
        "output_dir": "/old/remote/path", "native_database": "/old/remote/path/native.db", "fixture_only": True}
    packet.put(folder + "/result.json", result)
    input_sha = sha256(struct.pack("<8f", *audit.expected_task()["public"]["observations"][0]["values"])).hexdigest()
    checked = {"expected_action_checked": True, "stored_call_tree_verified": not reference, "trace_count": 3,
        "return_node": 1, "reserved_policy_units": 9, "rows": [
            {"cjt_id": "A", "input_node": -1, "input_sha256": input_sha, "output_sha256": fake_hash("a")},
            {"cjt_id": "B", "input_node": 0, "input_sha256": fake_hash("a"), "output_sha256": fake_hash("b1")},
            {"cjt_id": "B", "input_node": 0, "input_sha256": fake_hash("a"), "output_sha256": fake_hash("b2")}],
        "final_output_sha256": fake_hash("b1")}
    verdict = {name: True for name in ("task_correct", "procedure_correct", "binding_correct", "dependency_correct", "actual_output_correct", "trace_valid")}
    verdict.update(repair_required=False, repair_success=None, stored_call_tree_verified=not reference, native_runs=3, reserved_policy_units=9)
    packet.put("demo/" + ("reference" if reference else "candidate") + "_verdict.json", verdict)
    return packet, result, checked


@pytest.mark.parametrize("reference", [False, True])
def test_stored_adapter_rebases_only_detached_paths_and_requires_frozen_replay(tmp_path, reference):
    packet, result, checked = stored_component_fixture(tmp_path, reference)
    before = deepcopy(result)
    calls = []
    def mock_replay(rebased, public, *, expected_action, allow_private_reference):
        assert rebased is not result and result == before
        assert rebased["output_dir"] != result["output_dir"]
        assert Path(rebased["native_database"]).parent == Path(rebased["output_dir"])
        assert public == audit.expected_task()["public"] and expected_action == audit.expected_task()["target"]
        assert allow_private_reference is reference
        calls.append(True)
        return deepcopy(checked)
    returned = audit._stored_result(packet, result, reference=reference, stored=SimpleNamespace(verify_stored_composition=mock_replay))
    assert returned == checked and calls == [True] and result == before


@pytest.mark.parametrize("mutation", ["expected-action", "call-tree", "trace-count", "return-node", "dependency", "input-bytes", "false-verdict", "native-error"])
def test_stored_adapter_never_promotes_wrong_or_unverified_replay(tmp_path, mutation):
    packet, result, checked = stored_component_fixture(tmp_path, False)
    if mutation == "expected-action": checked["expected_action_checked"] = False
    elif mutation == "call-tree": checked["stored_call_tree_verified"] = False
    elif mutation == "trace-count": checked["trace_count"] = 2
    elif mutation == "return-node": checked["return_node"] = 2
    elif mutation == "dependency": checked["rows"][2]["input_node"] = 1
    elif mutation == "input-bytes": checked["rows"][0]["input_sha256"] = "0" * 64
    elif mutation == "false-verdict":
        packet.mutate("demo/candidate_verdict.json", lambda row: row.__setitem__("actual_output_correct", False))
    def mock_replay(*args, **kwargs):
        if mutation == "native-error":
            raise ValueError("SYNTHETIC_STORED_BYTE_VERIFICATION_FAILED")
        return checked
    with pytest.raises(ValueError):
        audit._stored_result(packet, result, reference=False, stored=SimpleNamespace(verify_stored_composition=mock_replay))


def test_audit_failure_cannot_become_success_even_when_final_bytes_are_unchanged(tmp_path, monkeypatch):
    packet = DiskFixture(tmp_path / "evidence")
    packet.put("demo/component.json", {"synthetic_inventory_only": True})
    packet.put("native/component.bin", b"NOT NATIVE EVIDENCE")
    entries = list(packet.inventory.values())
    index = {"schema": "cas-meta3-file-index/0.1", "roots": {name: str(path) for name, path in packet.roots.items()},
             "entries": entries, "entries_sha256": audit.digest(entries)}
    index_path = packet.roots["demo"] / "file_index.json"
    index_path.write_bytes(audit.canonical(index) + b"\n")
    header = {"file_index_sha256": audit.file_hash(index_path), "source": {"synthetic": True},
              "note": "NOT A NATIVE SUCCESS RECEIPT"}
    receipt_path = packet.roots["demo"] / "memory_demo_receipt.json"
    receipt_path.write_bytes(audit.canonical(header) + b"\n")
    monkeypatch.setattr(audit, "ROOT", tmp_path / "audit_root")
    monkeypatch.setattr(audit, "checked_header", lambda *_a, **_k: None)
    monkeypatch.setattr(audit, "source_checks", lambda *_: (_ for _ in ()).throw(audit.AuditError("SYNTHETIC_SOURCE_REJECTION")))
    receipt = audit.audit_demo(demo_root=packet.roots["demo"], native_root=packet.roots["native"],
        source_sha="a" * 40, job=JOB, demo_receipt_sha256=audit.file_hash(receipt_path),
        file_index_sha256=audit.file_hash(index_path), output=tmp_path / "audit_root/records/rejected_fixture")
    assert receipt["completed"] is False
    assert receipt["status"] == "CAS_META_3_STORED_NATIVE_DEMO_AUDIT_REJECTED"
    assert receipt["all_indexed_files_unchanged_before_after"] is True
    assert receipt["errors"][0]["reason"] == "SYNTHETIC_SOURCE_REJECTION"
    assert receipt["neural_execution_performed"] is False and receipt["checkpoint_loading_performed"] is False


def test_unauthorized_source_imports_cannot_enter_pure_auditor(monkeypatch):
    monkeypatch.setitem(sys.modules, "cupy", SimpleNamespace(__file__="synthetic_not_a_real_library"))
    with pytest.raises(audit.AuditError, match="PURE_AUDITOR_PROCESS_REQUIRED"):
        audit._pure_imports()


def test_all_neural_libraries_remain_unimported():
    assert not any(name in sys.modules for name in ("torch", "tensorflow", "jax", "cupy", "casformer"))
