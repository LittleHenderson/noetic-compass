"""Pure mock packets and documentary records, NOT a native/GPU campaign audit."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import struct
import sys

import pytest
from jsonschema import Draft202012Validator, ValidationError

from cas_meta2.campaign import ARMS, _smoke_tasks
from cas_meta2.curriculum import check_native_topology, generate_dataset, write_dataset
from cas_meta2.executor import CompositionExecutor, canonical, digest
from tools import audit_stored_packet as audit
from test_stored import DocumentaryBackend

pytestmark = pytest.mark.not_gpu


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def inspection(root, extracted, *, mode="smoke"):
    entries = [{"path": p.relative_to(extracted).as_posix(), "bytes": p.stat().st_size,
                "sha256": sha256(p.read_bytes()).hexdigest()} for p in sorted(extracted.rglob("*")) if p.is_file()]
    folder = root / "inspection"
    folder.mkdir(exist_ok=True)
    index_path = folder / "full_member_index.json"
    write(index_path, {"schema": "cas-meta2-full-packet-index/1", "packet_sha256": "a" * 64, "entries": entries})
    receipt = {"schema": "cas-meta2-packet-inspection/1", "status": "CAS_META_2_PACKET_" + mode.upper() + "_EVIDENCE_VERIFIED",
               "packet_sha256": "a" * 64, "source_sha": "b" * 40, "issues": [],
               "completed_run_evidence_verified": True, "archive_safety_and_all_included_bytes_checked": True,
               "original_full_index_verified": True, "collection": {"returncode": 0, "partial_evidence": False,
                   "omitted_full_file_count": 0, "smoke_only": mode == "smoke"},
               "extraction": {"path": str(extracted), "files_verified": len(entries), "all_member_bytes_verified_after_write": True},
               "full_member_index": str(index_path), "full_member_index_sha256": sha256(index_path.read_bytes()).hexdigest(),
               "member_files": len(entries)}
    path = folder / "inspection_receipt.json"
    write(path, receipt)
    return path


def mock_run(extracted, folder, task, *, private):
    path = extracted / folder
    path.mkdir(parents=True)
    backend = DocumentaryBackend(path, task["public"])
    executor = CompositionExecutor(backend, task["target"]["program"], binding=task["target"]["binding"])
    final = executor.run()
    result = {"status": "EXECUTED", "reference": private, "selected_action": deepcopy(task["target"]),
              "public_digest": digest(task["public"]), "runtime_identity": backend.identity(),
              "runtime_identity_after": backend.identity(), "final_reference": final,
              "native_trace_count": len(backend.traces), "reserved_policy_units": executor.spent,
              "execution_receipt": None if private else executor.validate_evidence(),
              "output_dir": "/remote-original/" + folder, "native_database": "/remote-original/" + folder + "/native.db"}
    write(path / "native_traces.json", backend.traces)
    write(path / "composition_events.json", [] if private else executor.events)
    write(path / "native_kernel_events.json", [])
    backend.db.close()
    result["evidence_sha256"] = {p.name: sha256(p.read_bytes()).hexdigest() for p in path.iterdir() if p.is_file()}
    write(path / "result.json", result)
    verdict = {**{key: True for key in audit.FIELDS}, "repair_success": None, "repair_required": False,
               "native_runs": len(backend.traces), "reserved_policy_units": executor.spent}
    return result, verdict


@pytest.fixture
def mock_smoke(tmp_path, monkeypatch):
    extracted = tmp_path / "packet_extracted"
    dataset = extracted / audit.BASE / "dataset"
    write_dataset(dataset, counts={"train": 8, "validation": 4, "test": 4})
    training = json.loads((dataset / "train.json").read_bytes())
    for name, task in _smoke_tasks(training):
        folder = audit.BASE + "smoke/" + name
        reference, ref_verdict = mock_run(extracted, folder + "/reference", task, private=True)
        candidate, verdict = mock_run(extracted, folder + "/execution", task, private=False)
        for filename, value in (("reference_result.json", reference), ("reference_verdict.json", ref_verdict),
                                ("execution_result.json", candidate), ("verification.json", verdict)):
            write(extracted / folder / filename, value)
    receipt = inspection(tmp_path, extracted)
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    schema_path = tmp_path / "mock_schema.json"
    schema = {"type": "object", "required": ["tick", "compute_plan"]}
    write(schema_path, schema)
    monkeypatch.setattr(audit, "SCHEMA_PATH", schema_path)
    monkeypatch.setattr(audit, "protected_schema", lambda: (Draft202012Validator(schema),
        {"sha256": sha256(schema_path.read_bytes()).hexdigest(), "boundary": "MOCK NOT PUBLISHED SCHEMA"}))
    monkeypatch.setattr(audit, "_code_hashes", lambda: {"mock": "c" * 64})
    return tmp_path, extracted, receipt


def test_complete_mock_smoke_rebases_only_memory_and_preserves_every_member(mock_smoke, monkeypatch):
    root, extracted, receipt = mock_smoke
    before = {p: p.read_bytes() for p in extracted.rglob("*") if p.is_file()}
    # The fake records are not full native schema objects, so keep that gate
    # explicitly mocked; stored replay itself is real and unpatched.
    monkeypatch.setattr(audit, "validate_all_traces", lambda packet, validator, **kw: {"databases": 6, "stored_traces": 30, "mock_only": True})
    report = audit.audit_packet(receipt, output=root / "records" / "audit")
    assert report["status"] == "CAS_META_2_STORED_SMOKE_AUDIT_PASSED"
    assert report["smoke"]["reference_runs"] == report["smoke"]["candidate_runs"] == 3
    assert report["full"] is None and report["neural_execution_performed"] is False
    assert report["restart_execution_performed"] is False
    assert {p: p.read_bytes() for p in before} == before
    assert all(json.loads(raw)["output_dir"].startswith("/remote-original/")
               for path, raw in before.items() if path.name == "result.json")


def test_mock_resealed_wrong_saved_correctness_is_detected(mock_smoke):
    root, extracted, receipt = mock_smoke
    path = extracted / audit.BASE / "smoke/training_anchor/verification.json"
    verdict = json.loads(path.read_bytes());verdict["task_correct"] = False;write(path, verdict)
    receipt = inspection(root, extracted)
    with pytest.raises(audit.StoredPacketInvalid, match="SAVED_CORRECTNESS_DIFFERS"):
        audit.audit_smoke(audit.Extracted(receipt))


def test_mock_failure_writes_typed_receipt_and_partial_counts_without_passing(mock_smoke, monkeypatch):
    root, extracted, receipt = mock_smoke
    monkeypatch.setattr(audit, "validate_all_traces", lambda packet, validator, **kw: {"databases": 6, "stored_traces": 30, "mock_only": True})
    path = extracted / audit.BASE / "smoke/training_anchor/verification.json"
    verdict = json.loads(path.read_bytes());verdict["task_correct"] = False;write(path, verdict)
    receipt = inspection(root, extracted)
    result = audit.audit_packet(receipt, output=root / "records" / "failed_audit")
    assert result["status"] == "CAS_META_2_STORED_SMOKE_AUDIT_REJECTED" and result["completed"] is False
    assert result["all_extracted_files_unchanged_before_after"] is True
    assert result["errors"][0]["stage"] == "smoke_stored_semantics"
    assert result["errors"][0]["type"] == "StoredPacketInvalid"
    assert "Traceback" in result["errors"][0]["traceback"]
    assert result["partial_stage_counts"]["smoke_stored_semantics"]["reference_runs_checked"] == 1
    assert result["partial_stage_counts"]["smoke_stored_semantics"]["candidate_runs_checked"] == 0
    assert json.loads((root / "records/failed_audit/stored_audit_receipt.json").read_bytes()) == result


def test_mock_failed_inspection_writes_new_rejected_receipt_without_false_immutability_claim(mock_smoke):
    root, extracted, receipt = mock_smoke
    value = json.loads(receipt.read_bytes());value["completed_run_evidence_verified"] = False;write(receipt, value)
    result = audit.audit_packet(receipt, output=root / "records/rejected_inspection", extracted=extracted)
    assert result["completed"] is False and result["all_extracted_files_unchanged_before_after"] is False
    assert result["errors"][0]["stage"] == "inspection_inputs"
    assert result["inspection_receipt_sha256"] == sha256(receipt.read_bytes()).hexdigest()


def test_mock_rejected_input_cannot_make_audit_write_inside_extracted_tree(mock_smoke, monkeypatch):
    root, extracted, receipt = mock_smoke
    value = json.loads(receipt.read_bytes());value["completed_run_evidence_verified"] = False;write(receipt, value)
    # Make the requested location meet the records rule but remain inside the
    # claimed extracted input. Neither success nor failure may write there.
    monkeypatch.setattr(audit, "ROOT", extracted)
    output = extracted / "records/unsafe_audit"
    with pytest.raises(audit.StoredPacketInvalid, match="AUDIT_OUTPUT_INSIDE_EVIDENCE"):
        audit.audit_packet(receipt, output=output)
    assert not output.exists()


@pytest.mark.parametrize("which", ["changed", "missing", "extra"])
def test_mock_inventory_rechecks_every_extracted_file(mock_smoke, which):
    root, extracted, receipt = mock_smoke
    path = next(extracted.rglob("native_kernel_events.json"))
    if which == "changed":path.write_bytes(b"[1]")
    elif which == "missing":path.unlink()
    else:(extracted / "unindexed.txt").write_bytes(b"extra")
    with pytest.raises(audit.StoredPacketInvalid):
        audit.Extracted(receipt)


def test_mock_failed_inspection_never_enters_semantic_audit(mock_smoke):
    root, extracted, receipt = mock_smoke
    document = json.loads(receipt.read_bytes());document["status"] = "CAS_META_2_PACKET_FAILED_RUN";write(receipt, document)
    with pytest.raises(audit.StoredPacketInvalid, match="SUCCESSFUL_FULL_INSPECTION_REQUIRED"):
        audit.Extracted(receipt)


def test_mock_index_file_is_bound_to_inspection_hash(mock_smoke):
    root, extracted, receipt = mock_smoke
    path = receipt.with_name("full_member_index.json")
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(audit.StoredPacketInvalid, match="FULL_INDEX_HASH_MISMATCH"):
        audit.Extracted(receipt)


def test_mock_native_action_is_bound_to_external_sealed_action(mock_smoke):
    root, extracted, receipt = mock_smoke
    packet = audit.Extracted(receipt)
    folder = audit.BASE + "smoke/training_anchor"
    result = packet.json(folder + "/execution_result.json")
    action = deepcopy(result["selected_action"]);action["binding"] = (action["binding"] + 1) % 3
    with pytest.raises(audit.StoredPacketInvalid, match="SELECTED_ACTION_DIFFERS_FROM_SEAL"):
        audit._native(packet, result, folder + "/execution", {}, action)


def test_mock_all_traces_schema_gate_rejects_malformed_stored_trace(tmp_path):
    extracted = tmp_path / "packet_extracted";extracted.mkdir()
    database = extracted / "native.db"
    conn = sqlite3.connect(database)
    conn.execute("CREATE TABLE trace_events(sequence INTEGER,payload_sha256 TEXT,payload_json TEXT)")
    malformed = {"schema_version": "cas.neural-cjt.tick-trace/0.2", "contract_type": "TICK_TRACE"}
    raw = canonical(malformed).decode()
    conn.execute("INSERT INTO trace_events VALUES(1,?,?)", (sha256(raw.encode()).hexdigest(), raw));conn.commit();conn.close()
    packet = audit.Extracted(inspection(tmp_path, extracted))
    with pytest.raises(ValidationError):
        audit.validate_all_traces(packet, Draft202012Validator({"required": ["tick"]}))


def test_published_schema_is_verified_against_real_accepted_git_object_without_neural_import():
    before = "torch" in sys.modules
    validator, receipt = audit.protected_schema()
    assert receipt["baseline_sha"] == "0917267b1354e5d036263eaa6ba9a7197eafb776"
    assert receipt["sha256"] == sha256(audit.SCHEMA_PATH.read_bytes()).hexdigest()
    with pytest.raises(ValidationError):
        validator.validate({"contract_type": "TICK_TRACE"})
    assert ("torch" in sys.modules) == before


class MemoryPacket:
    def __init__(self, documents):
        self.documents, self.inventory = documents, {}
    def json(self, name):return deepcopy(self.documents[name])


def test_mock_full_denominator_reproduces_72_references_and_360_choices(monkeypatch):
    task = generate_dataset(counts={"train": 2, "validation": 2, "test": 2})["splits"]["test"][0]
    observations = task["public"]["observations"]
    observation = next(row for row in observations if row["slot"] == task["target"]["binding"])
    input_sha = sha256(struct.pack("<8f", *observation["values"])).hexdigest()
    structure = check_native_topology(task["target"]["program"])
    evidence = {"rows": [{"cjt_id": r["cjt_id"], "input_node": r["input_node"], "input_sha256": input_sha,
                          "output_sha256": "a" * 64} for r in structure["runs"]], "return_node": structure["return_node"],
                "final_output_sha256": "a" * 64, "trace_count": len(structure["runs"]), "reserved_policy_units": 42}
    documents, predictions = {}, []
    success = audit.reference_verdict(task, evidence)
    failed = {**{key: False for key in audit.FIELDS}, "native_runs": 0, "reserved_policy_units": 0}
    for index in range(72):
        folder = audit.BASE + f"evaluation/case_{index:04d}"
        documents[folder + "/reference_result.json"] = {"runtime_identity": {"mock": True}}
        documents[folder + "/reference_verdict.json"] = {**success, "repair_required": False, "repair_success": None}
        actions = {arm: deepcopy(task["target"]) if arm == "rule" else {"status": "REJECTED", "reason": "mock syntax"} for arm in ARMS}
        predictions.append({"actions": actions})
        for arm, action in actions.items():
            good = arm == "rule"
            verdict = {**(success if good else failed), "repair_required": False, "repair_success": None}
            result = {"runtime_identity": {"mock": True}} if good else {"status": "REJECTED", "action": action,
                "failure": audit.admission_error(action, task["public"]), "reserved_policy_units": 0, "native_runs": 0}
            directory = folder + "/" + arm
            documents[directory + "/execution_result.json"] = result
            documents[directory + "/verification.json"] = verdict
            documents[directory + "/case_receipt.json"] = {"action": action, "verification": verdict,
                "case_index": index, "arm": arm, "model_rejection": not good}
    metrics = {}
    for arm in ARMS:
        good = arm == "rule"
        values = success if good else failed
        metrics[arm] = {"total": 72, **{key: values[key] * 72 for key in (*audit.FIELDS, "native_runs", "reserved_policy_units")},
                        "model_rejections": 0 if good else 72, "task_accuracy": 1 if good else 0,
                        "all_cases_in_denominator": True}
        # Boolean aggregates are true integer counts, not bools.
    documents[audit.BASE + "evaluation_results.json"] = {"results": metrics}
    monkeypatch.setattr(audit, "_test_mapping", lambda packet: ([deepcopy(task) for _ in range(72)], predictions))
    calls = []
    def fake_native(packet, result, folder, public, action, *, reference=False):
        calls.append(reference)
        return deepcopy(evidence)
    monkeypatch.setattr(audit, "_native", fake_native)
    report = audit.audit_full(MemoryPacket(documents))
    assert report["reference_runs"] == 72 and report["arm_choices"] == 360
    assert calls.count(True) == calls.count(False) == 72
    assert report["metrics"]["rule"]["task_correct"] == 72
    assert report["metrics"]["cas_trained"]["model_rejection"] == 72
    documents[audit.BASE + "evaluation/case_0000/cas_trained/execution_result.json"]["failure"] = {"code": "invented"}
    with pytest.raises(audit.StoredPacketInvalid, match="MODEL_REJECTION_NOT_REPRODUCED"):
        audit.audit_full(MemoryPacket(documents))
