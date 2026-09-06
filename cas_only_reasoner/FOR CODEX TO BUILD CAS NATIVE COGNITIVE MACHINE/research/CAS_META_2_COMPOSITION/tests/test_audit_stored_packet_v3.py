"""Pure mock receipts and read-only inventory checks; not native/GPU evidence."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stored_v3_under_test", ROOT / "tools/audit_stored_packet_v3.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
pytestmark = pytest.mark.not_gpu


def test_import_is_standard_library_only_and_does_not_execute_inspector():
    assert audit.outer is None


def test_hash_pattern_accepts_exact_digest():
    assert audit.SHA256.fullmatch("a" * 64)
    assert not audit.SHA256.fullmatch("a" * 64 + "\n")


def inspected(tmp_path, monkeypatch):
    root = tmp_path / "extracted"
    root.mkdir()
    (root / "one.json").write_bytes(b'{"mock":true}')
    rows = [{"path": "one.json", "bytes": 13, "sha256": audit.file_hash(root / "one.json")}]
    packet_hash = "a" * 64
    directory = tmp_path / "inspection"
    directory.mkdir()
    index = {"schema": "cas-meta2-full-packet-index/1", "packet_sha256": packet_hash, "entries": rows}
    (directory / "full_member_index.json").write_bytes(audit.canonical(index))
    experiment = {"profile": "learning_v3", "entrypoint": "cas_meta2.campaign_v3",
                  "spec_path": "research/CAS_META_2_COMPOSITION/EXPERIMENT_V3.json", "spec_sha256": "b" * 64}
    manifest = {"source_sha": "c" * 40}
    receipt = {"schema": "cas-meta2-packet-inspection/3", "status": "CAS_META_2_V3_PACKET_FULL_EVIDENCE_VERIFIED",
        "issues": [], "completed_run_evidence_verified": True, "archive_safety_and_all_included_bytes_checked": True,
        "original_full_index_verified": True, "experiment": experiment, "source_sha": manifest["source_sha"],
        "source_manifest": manifest, "source_manifest_sha256": audit.digest(manifest),
        "collection": {"returncode": 0, "partial_evidence": False, "omitted_full_file_count": 0, "smoke_only": False},
        "extraction": {"all_member_bytes_verified_after_write": True, "path": str(root), "files_verified": 1},
        "full_member_index": str(directory / "full_member_index.json"),
        "full_member_index_sha256": audit.file_hash(directory / "full_member_index.json"),
        "packet_sha256": packet_hash, "member_files": 1}
    path = directory / "inspection_receipt.json"
    path.write_bytes(audit.canonical(receipt))
    # Deliberately mock the already-tested independent source authority gate.
    monkeypatch.setattr(audit, "_configure", lambda manifest, source_sha: None)
    monkeypatch.setattr(audit, "outer", SimpleNamespace(profiles=SimpleNamespace(validate_manifest=lambda m: experiment)))
    def safe_name(value):
        audit.require(type(value) is str and value and "/" not in value and "\\" not in value and value not in (".", ".."),
                      "MOCK_BAD_NAME")
        return value
    monkeypatch.setattr(audit, "safe_name", safe_name)
    return path, root, receipt


def test_full_index_is_rehashed_before_and_after_without_writes(tmp_path, monkeypatch):
    path, root, _ = inspected(tmp_path, monkeypatch)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    packet = audit.Extracted(path)
    assert packet.mode == "full"
    packet.verify_all()
    assert {p.name: p.read_bytes() for p in root.iterdir()} == before


@pytest.mark.parametrize("fault", ["old_status", "issue", "incomplete", "omission", "profile", "manifest_hash",
                                      "index_hash", "changed_member", "added_member", "missing_member"])
def test_incomplete_or_changed_inspection_cannot_be_promoted(tmp_path, monkeypatch, fault):
    path, root, receipt = inspected(tmp_path, monkeypatch)
    if fault == "old_status":
        receipt["status"] = "CAS_META_2_V2_PACKET_FULL_EVIDENCE_VERIFIED"
    elif fault == "issue":
        receipt["issues"] = ["V2_PREFLIGHT_MEMORY_CLEANUP_UNCONFIRMED"]
    elif fault == "incomplete":
        receipt["completed_run_evidence_verified"] = False
    elif fault == "omission":
        receipt["collection"]["omitted_full_file_count"] = 1
    elif fault == "profile":
        receipt["experiment"]["profile"] = "learning_v2"
    elif fault == "manifest_hash":
        receipt["source_manifest_sha256"] = "d" * 64
    elif fault == "index_hash":
        receipt["full_member_index_sha256"] = "d" * 64
    elif fault == "changed_member":
        (root / "one.json").write_bytes(b'{"mock":false}')
    elif fault == "added_member":
        (root / "two.json").write_bytes(b"{}")
    else:
        (root / "one.json").unlink()
    path.write_bytes(audit.canonical(receipt))
    with pytest.raises(ValueError):
        audit.Extracted(path)


def test_loaded_inventory_rejects_later_tampering(tmp_path, monkeypatch):
    path, root, _ = inspected(tmp_path, monkeypatch)
    packet = audit.Extracted(path)
    (root / "one.json").write_bytes(b"changed")
    with pytest.raises(ValueError):
        packet.verify_all()


@pytest.mark.parametrize("reference", [False, True])
def test_native_replay_receives_sealed_action_and_only_detached_rebased_paths(tmp_path, monkeypatch, reference):
    action, public = {"mock": "action"}, {"mock": "public"}
    native = tmp_path / "native"
    native.mkdir()
    (native / "native.db").write_bytes(b"mock-only")
    result = {"status": "EXECUTED", "reference": reference, "selected_action": action,
              "output_dir": "/remote/native", "native_database": "/remote/native/native.db"}
    original = deepcopy(result)
    class Packet:
        def json(self, name):
            return result
        def path(self, name):
            return native / "native.db"
    monkeypatch.setattr(audit, "admission_error", lambda a, p: None, raising=False)
    def replay(detached, observations, *, expected_action, allow_private_reference):
        assert detached is not result and detached["output_dir"] == str(native.resolve())
        assert observations == public and expected_action == action and allow_private_reference is reference
        return {"stored_call_tree_verified": not reference, "expected_action_checked": True}
    monkeypatch.setattr(audit, "verify_stored_composition", replay, raising=False)
    audit._native(Packet(), result, "native", public, action, reference=reference)
    assert result == original and (native / "native.db").read_bytes() == b"mock-only"


def test_private_role_and_forged_seal_are_rejected_before_replay(monkeypatch):
    monkeypatch.setattr(audit, "verify_stored_composition", lambda *a, **k: pytest.fail("Replay must not run"), raising=False)
    result = {"status": "EXECUTED", "reference": True, "selected_action": {"a": 1}}
    packet = SimpleNamespace(json=lambda name: result)
    with pytest.raises(ValueError, match="ROLE"):
        audit._native(packet, result, "n", {}, {"a": 1})
    result["reference"] = False
    with pytest.raises(ValueError, match="SEAL"):
        audit._native(packet, result, "n", {}, {"a": 2})


def test_correct_final_digest_does_not_hide_wrong_intermediate_or_binding(monkeypatch):
    monkeypatch.setattr(audit, "graph_signature", lambda p: p, raising=False)
    task = {"target": {"program": "same", "binding": 0}}
    row = {"cjt_id": "A", "input_node": -1, "input_sha256": "in", "output_sha256": "out"}
    reference = {"rows": [row], "return_node": 0, "final_output_sha256": "final", "trace_count": 1, "reserved_policy_units": 5}
    actual = deepcopy(reference)
    actual["rows"][0]["output_sha256"] = "different"
    verdict = audit.candidate_verdict(task, task["target"], actual, reference)
    assert verdict["trace_valid"] and not verdict["actual_output_correct"] and not verdict["task_correct"]
    actual = deepcopy(reference)
    verdict = audit.candidate_verdict(task, {"program": "same", "binding": 1}, actual, reference)
    assert not verdict["binding_correct"] and not verdict["task_correct"]


def test_failed_audit_preserves_input_and_emits_new_typed_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    monkeypatch.setattr(audit, "_code_hashes", lambda: {"mock_test_only": "a" * 64})
    path = tmp_path / "invalid.json"
    path.write_bytes(b'{"schema":"wrong"}')
    before = path.read_bytes()
    output = tmp_path / "records/rejected"
    result = audit.audit_packet(path, output=output)
    assert result["completed"] is False and result["status"] == "CAS_META_2_V3_STORED_PACKET_AUDIT_REJECTED"
    assert result["errors"] and result["partial_stage_counts"] == {}
    assert result["neural_execution_performed"] is False and result["checkpoint_loading_performed"] is False
    assert path.read_bytes() == before
    assert (output / "stored_audit_receipt.json").is_file()
    with pytest.raises(ValueError):
        audit.audit_packet(path, output=output)


def test_helper_cannot_execute_before_external_git_identity_check(monkeypatch):
    monkeypatch.setattr(audit, "outer", None)
    monkeypatch.setattr(audit.importlib.util, "module_from_spec", lambda *args: pytest.fail("Unbound helper executed"))
    with pytest.raises(ValueError, match="EXTERNAL_SOURCE"):
        audit._configure({"source_sha": "a" * 40}, "b" * 40)

