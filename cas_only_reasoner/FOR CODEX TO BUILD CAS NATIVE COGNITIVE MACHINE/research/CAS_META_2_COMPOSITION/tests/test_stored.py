"""Pure documentary SQLite fixtures. These are NOT native-CJT/GPU evidence."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import struct

import pytest

from cas_meta2.executor import CompositionExecutor, canonical, digest
from cas_meta2.stored import PHASES, QUANTA, verify_stored_composition
from test_executor import nested_program, reseal

pytestmark = pytest.mark.not_gpu


class DocumentaryBackend:
    """Writes fabricated documents only. Never imports a native module."""
    def __init__(self, output, public):
        self.output, self.public = output, public
        self.db = sqlite3.connect(output / "native.db")
        self.db.executescript("""
        CREATE TABLE artifacts(artifact_id TEXT PRIMARY KEY,sha256 TEXT,kind TEXT,
          media_type TEXT,encoding TEXT,metadata_json TEXT,payload BLOB);
        CREATE TABLE model_versions(model_digest TEXT PRIMARY KEY,parent_model_digest TEXT,
          artifact_id TEXT,payload_sha256 TEXT,payload_json TEXT);
        CREATE TABLE causes(record_id TEXT PRIMARY KEY,commit_receipt_id TEXT,payload_sha256 TEXT,payload_json TEXT);
        CREATE TABLE published_effects(record_id TEXT PRIMARY KEY,commit_receipt_id TEXT,payload_sha256 TEXT,payload_json TEXT);
        CREATE TABLE trace_events(sequence INTEGER PRIMARY KEY,trace_id TEXT,trace_digest TEXT,
          previous_trace_digest TEXT,pre_state_digest TEXT,post_state_digest TEXT,payload_sha256 TEXT,payload_json TEXT);
        CREATE TABLE commit_receipts(receipt_id TEXT PRIMARY KEY,batch_id TEXT,request_digest TEXT,
          pre_state_digest TEXT,post_state_digest TEXT,trace_digest TEXT,rollback_of_receipt_id TEXT,
          payload_sha256 TEXT,payload_json TEXT);
        CREATE TABLE active_head(singleton INTEGER PRIMARY KEY,state_digest TEXT,state_version INTEGER,
          trace_digest TEXT,model_digest TEXT,commit_receipt_id TEXT);
        CREATE TABLE state_versions(state_digest TEXT PRIMARY KEY,state_version INTEGER,
          parent_state_digest TEXT,payload_sha256 TEXT,payload_json TEXT);
        """)
        self.refs, self.receipts, self.traces, self.artifacts = {}, {}, [], {}
        model_payload = b"MOCK ONLY: not model weights"
        model_ref = self.artifact(model_payload, tensor=False)
        model_digest = model_ref["sha256"]
        topology = {"mock_topology": ["A", "B", "C"]}
        self._identity = {"model": {"model_digest": model_digest,
                                    "parameter_bytes_sha256": sha256(model_payload).hexdigest()},
                          "stored_model_digest": model_digest, "topology": topology,
                          "contracts": {"mock-operation": digest("contract")},
                          "decoders": {"mock-decoder": digest("decoder")}}
        self._identity["software_digest"] = digest({"runtime_id": "mock-runtime",
            "authority_contract_id": "mock-authority", "topology": topology,
            "operation_contracts": self._identity["contracts"], "decoders": self._identity["decoders"]})
        model = {"model_digest": model_digest, "network": topology, "model_artifact_ref": model_ref}
        raw = canonical(model).decode()
        self.db.execute("INSERT INTO model_versions VALUES(?,?,?,?,?)",
                        (model_digest, None, model_ref["artifact_id"], sha256(raw.encode()).hexdigest(), raw))
        self._head = {"state_digest": digest("genesis"), "state_version": 0,
                      "trace_digest": None, "model_digest": model_digest, "commit_receipt_id": None}
        self.db.execute("INSERT INTO active_head VALUES(1,?,?,?,?,?)", tuple(self._head.values()))
        self.db.commit()

    def artifact(self, payload, *, tensor=True):
        metadata = {"mock_only": True}
        header = {"encoding": "raw", "kind": "tensor" if tensor else "model", "media_type": "application/octet-stream",
                  "metadata": metadata, "payload_byte_length": len(payload)}
        checksum = sha256(canonical(header) + b"\n" + payload).hexdigest()
        identifier = "artifact-" + checksum[:24]
        self.db.execute("INSERT OR IGNORE INTO artifacts VALUES(?,?,?,?,?,?,?)",
                        (identifier, checksum, header["kind"], header["media_type"], "raw", canonical(metadata).decode(), payload))
        return {"artifact_id": identifier, "sha256": checksum, "encoding": "raw",
                "dtype": "float32" if tensor else "mock-model", "shape": [1, 2, 4] if tensor else [len(payload)],
                "byte_length": len(payload)}

    def identity(self):
        return deepcopy(self._identity)

    def head(self):
        return deepcopy(self._head)

    def input_reference(self, binding):
        row = self.public["observations"][binding]
        return {"kind": "observation", "slot": binding, "public_digest": digest(self.public),
                "payload_sha256": sha256(struct.pack("<8f", *row["values"])).hexdigest()}

    def validate_reference(self, ref):
        expected = self.input_reference(ref["slot"]) if ref["kind"] == "observation" else self.refs[ref["effect_id"]]
        assert ref == expected

    def prepare(self, cjt, ref):
        wire = {field: [[i + 1]] for i, field in enumerate(QUANTA)}
        return {"units": 15, "plan_digest": digest(wire), "wire": wire}

    def put_document(self, table, identifier, receipt_id, document):
        raw = canonical(document).decode()
        self.db.execute("INSERT INTO " + table + " VALUES(?,?,?,?)",
                        (identifier, receipt_id, sha256(raw.encode()).hexdigest(), raw))

    def execute(self, cjt, ref, plan):
        index = len(self.traces)
        request_digest = digest(["mock-request", index])
        receipt_id, cause_id, effect_id = "commit-" + request_digest[:24], f"cause-{index}", f"effect-{index}"
        state = {"state_version": index + 1, "model_digest": self._head["model_digest"], "mock_index": index,
                 "previous_state_digest": self._head["state_digest"]}
        state_digest = digest(state)
        state["state_digest"] = state_digest
        raw = canonical(state).decode()
        self.db.execute("INSERT INTO state_versions VALUES(?,?,?,?,?)",
                        (state_digest, index + 1, self._head["state_digest"], sha256(raw.encode()).hexdigest(), raw))
        if ref["kind"] == "observation":
            row = self.public["observations"][ref["slot"]]
            input_artifact = self.artifact(struct.pack("<8f", *row["values"]))
            content = {"task": "cas-meta2-observation", "public_digest": digest(self.public),
                       "binding_slot": ref["slot"], "binding_tag": row["tag"]}
            parent, producer = None, None
        else:
            input_artifact = self.artifacts[ref["effect_id"]]
            content, parent, producer = {}, ref["effect_id"], ref["producer_cjt_id"]
        cause = {"cause_id": cause_id, "tick": index + 1, "parent_effect_id": parent,
                 "originating_cjt_id": producer, "content": content, "content_ref": input_artifact}
        output_payload = struct.pack("<8f", *([float(index + 1)] * 8))
        output_artifact = self.artifact(output_payload)
        effect = {"published_effect_id": effect_id, "commit_receipt_id": receipt_id, "tick": index + 1,
                  "authoritative": True, "producer_cjt_id": cjt, "content_ref": output_artifact}
        effect["publication_digest"] = digest(effect)
        self.put_document("causes", cause_id, receipt_id, cause)
        self.put_document("published_effects", effect_id, receipt_id, effect)
        trace = {"tick": index + 1, "runtime_id": "mock-runtime", "software_digest": self._identity["software_digest"],
                 "cause_id": cause_id, "cjt_ids": [cjt], "pre_state_digest": self._head["state_digest"],
                 "post_state_digest": state_digest, "pre_model_digest": self._head["model_digest"],
                 "post_model_digest": self._head["model_digest"], "phases": [{"phase": p} for p in PHASES],
                 "sealed": True, "published_effect_ids": [effect_id], "commit_receipt_id": receipt_id,
                 "compute_plan": plan["wire"], "previous_trace_digest": self._head["trace_digest"]}
        trace["trace_id"] = "trace-" + digest(trace)[:24]
        trace["trace_digest"] = digest(trace)
        raw = canonical(trace).decode()
        self.db.execute("INSERT INTO trace_events VALUES(?,?,?,?,?,?,?,?)",
                        (index + 1, trace["trace_id"], trace["trace_digest"], trace["previous_trace_digest"],
                         trace["pre_state_digest"], state_digest, sha256(raw.encode()).hexdigest(), raw))
        receipt = {key: trace[key] for key in ("trace_id", "tick", "pre_state_digest", "post_state_digest",
                                              "pre_model_digest", "post_model_digest", "published_effect_ids")}
        receipt.update(receipt_id=receipt_id, batch_id=f"batch-{index}", rollback_of_receipt_id=None,
                       authority_contract_id="mock-authority", authorized=True, atomic=True, disposition="COMMITTED",
                       persisted_snapshot_id="snapshot-" + state_digest[:24])
        receipt["receipt_digest"] = digest(receipt)
        raw = canonical(receipt).decode()
        self.db.execute("INSERT INTO commit_receipts VALUES(?,?,?,?,?,?,?,?,?)",
                        (receipt_id, receipt["batch_id"], request_digest, trace["pre_state_digest"], state_digest,
                         trace["trace_digest"], None, sha256(raw.encode()).hexdigest(), raw))
        self._head = {"state_digest": state_digest, "state_version": index + 1,
                      "trace_digest": trace["trace_digest"], "model_digest": self._head["model_digest"],
                      "commit_receipt_id": receipt_id}
        self.db.execute("UPDATE active_head SET state_digest=?,state_version=?,trace_digest=?,model_digest=?,commit_receipt_id=?",
                        tuple(self._head.values()))
        self.db.commit()
        output = {"kind": "effect", "effect_id": effect_id, "producer_cjt_id": cjt,
                  "payload_sha256": sha256(output_payload).hexdigest()}
        compact = {"receipt_id": receipt_id, "trace_id": trace["trace_id"], "published_effect_ids": [effect_id],
                   "units": plan["units"], "plan_digest": plan["plan_digest"]}
        self.refs[effect_id], self.artifacts[effect_id], self.receipts[receipt_id] = output, output_artifact, compact
        self.traces.append(trace)
        return {"reference": deepcopy(output), "native_receipt": deepcopy(compact)}

    def validate_receipt(self, receipt, ref):
        assert receipt == self.receipts[receipt["receipt_id"]]
        assert receipt["published_effect_ids"] == [ref["effect_id"]]


def refresh_manifest(result):
    output = Path(result["output_dir"])
    result["evidence_sha256"] = {name: sha256((output / name).read_bytes()).hexdigest() for name in
        ("native.db", "native_traces.json", "composition_events.json", "native_kernel_events.json")}


@pytest.fixture
def documentary(tmp_path):
    public = {"observations": [{"slot": i, "tag": f"tag-{i}", "values": [0.1 + 0.01 * i] * 8} for i in range(3)]}
    backend = DocumentaryBackend(tmp_path, public)
    action = {"program": nested_program(), "binding": 2}
    executor = CompositionExecutor(backend, action["program"], binding=2)
    final = executor.run()
    result = {"output_dir": str(tmp_path), "native_database": str(tmp_path / "native.db"),
              "public_digest": digest(public), "selected_action": action, "reference": False,
              "runtime_identity": backend.identity(), "runtime_identity_after": backend.identity(),
              "final_reference": final, "native_trace_count": len(backend.traces),
              "reserved_policy_units": executor.spent, "execution_receipt": executor.validate_evidence()}
    (tmp_path / "native_traces.json").write_bytes(canonical(backend.traces))
    (tmp_path / "composition_events.json").write_bytes(canonical(executor.events))
    (tmp_path / "native_kernel_events.json").write_bytes(b"[]")
    backend.db.close()
    refresh_manifest(result)
    return public, result


def mutate_document(result, table, fn):
    conn = sqlite3.connect(result["native_database"])
    rowid, raw = conn.execute("SELECT rowid,payload_json FROM " + table + " ORDER BY rowid LIMIT 1").fetchone()
    doc = json.loads(raw)
    fn(doc)
    raw = canonical(doc).decode()
    conn.execute("UPDATE " + table + " SET payload_json=?,payload_sha256=? WHERE rowid=?",
                 (raw, sha256(raw.encode()).hexdigest(), rowid))
    conn.commit()
    conn.close()
    refresh_manifest(result)


def mutate_events(result, fn):
    path = Path(result["output_dir"]) / "composition_events.json"
    events = json.loads(path.read_bytes())
    fn(events)
    reseal(events)
    path.write_bytes(canonical(events))
    result["execution_receipt"]["event_head"] = events[-1]["digest"]
    refresh_manifest(result)


def test_mock_read_only_nested_replay_uses_actual_head_and_returns_earlier_effect(documentary):
    public, result = documentary
    before = sha256(Path(result["native_database"]).read_bytes()).hexdigest()
    report = verify_stored_composition(result, public, expected_action=deepcopy(result["selected_action"]))
    assert report["stored_call_tree_verified"] and report["expected_action_checked"]
    assert report["reserved_policy_units"] == 90 and report["trace_count"] == 6
    assert report["return_node"] == 2
    assert [r["input_node"] for r in report["rows"]] == [-1, 0, 1, -1, 0, 4]
    assert report["native_head"] == result["execution_receipt"]["native_head"]
    assert before == sha256(Path(result["native_database"]).read_bytes()).hexdigest()


def test_mock_private_direct_reference_explicitly_has_no_composition_claim(documentary):
    public, result = documentary
    result["reference"], result["execution_receipt"] = True, None
    (Path(result["output_dir"]) / "composition_events.json").write_bytes(b"[]")
    refresh_manifest(result)
    report = verify_stored_composition(result, public, allow_private_reference=True)
    assert report["stored_call_tree_verified"] is False
    assert report["execution_receipt"] is None and report["reserved_policy_units"] == 90


@pytest.mark.parametrize("field", ["reserved_policy_units", "native_trace_count"])
def test_mock_summary_counts_are_not_authority(documentary, field):
    public, result = documentary
    result[field] += 1
    with pytest.raises(ValueError, match="STORED_SUMMARY_ACCOUNTING_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_expected_sealed_action_is_external_not_summary(documentary):
    public, result = documentary
    expected = deepcopy(result["selected_action"])
    expected["binding"] = 0
    with pytest.raises(ValueError, match="SEALED_ACTION_MISMATCH"):
        verify_stored_composition(result, public, expected_action=expected)


def test_mock_missing_required_file_hash_rejected(documentary):
    public, result = documentary
    del result["evidence_sha256"]["composition_events.json"]
    with pytest.raises(ValueError, match="MISSING_REQUIRED_STORED_EVIDENCE"):
        verify_stored_composition(result, public)


def test_mock_resealed_wrong_named_source_rejected(documentary):
    public, result = documentary
    mutate_events(result, lambda ev: next(e for e in ev if e["kind"] == "NATIVE").update(input_name="v1"))
    with pytest.raises(ValueError, match="EVENT_PROGRAM_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_resealed_wrong_charge_rejected(documentary):
    public, result = documentary
    mutate_events(result, lambda ev: next(e for e in ev if e["kind"] == "CHARGE").update(units=14))
    with pytest.raises(ValueError, match="NATIVE_RESERVATION_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_resealed_receipt_plan_lie_rejected(documentary):
    public, result = documentary
    mutate_events(result, lambda ev: next(e for e in ev if e["kind"] == "NATIVE")["native_receipt"].update(plan_digest="0" * 64))
    with pytest.raises(ValueError, match="STORED_NATIVE_EVENT_BINDING_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_resealed_caller_return_wrong_rejected(documentary):
    public, result = documentary
    mutate_events(result, lambda ev: next(e for e in ev if e["kind"] == "RESUME").update(pc=99))
    with pytest.raises(ValueError, match="EVENT_PROGRAM_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_later_valid_effect_cannot_replace_source_selected_return(documentary):
    public, result = documentary
    events = json.loads((Path(result["output_dir"]) / "composition_events.json").read_bytes())
    result["final_reference"] = [e for e in events if e["kind"] == "NATIVE"][-1]["output_reference"]
    with pytest.raises(ValueError, match="EVENT_RESULT_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_actual_head_change_even_with_file_rehash_rejected(documentary):
    public, result = documentary
    conn = sqlite3.connect(result["native_database"])
    conn.execute("UPDATE active_head SET trace_digest=?", ("0" * 64,))
    conn.commit()
    conn.close()
    refresh_manifest(result)
    with pytest.raises(ValueError, match="STORED_FINAL_HEAD_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_raw_receipt_digest_corruption_rejected(documentary):
    public, result = documentary
    mutate_document(result, "commit_receipts", lambda d: d.update(authorized=False))
    with pytest.raises(ValueError, match="STORED_COMMIT_RECEIPT_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_changed_public_input_is_bound_to_actual_cause(documentary):
    public, result = documentary
    mutate_document(result, "causes", lambda d: d["content"].update(binding_tag="wrong"))
    with pytest.raises(ValueError, match="STORED_PUBLIC_INPUT_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_effect_payload_binding_rejected(documentary):
    public, result = documentary
    def change(doc):
        doc["content_ref"]["sha256"] = "0" * 64
        doc["publication_digest"] = digest({k: v for k, v in doc.items() if k != "publication_digest"})
    mutate_document(result, "published_effects", change)
    with pytest.raises(ValueError, match="STORED_ARTIFACT_BINDING_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_raw_model_bytes_bound_independently_of_result_flags(documentary):
    public, result = documentary
    result["runtime_identity"]["model"]["parameter_bytes_sha256"] = "0" * 64
    result["runtime_identity_after"] = deepcopy(result["runtime_identity"])
    with pytest.raises(ValueError, match="STORED_PARAMETER_BYTES_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_contract_map_bound_through_actual_trace_software_digest(documentary):
    public, result = documentary
    result["runtime_identity"]["contracts"]["mock-operation"] = "0" * 64
    result["runtime_identity_after"] = deepcopy(result["runtime_identity"])
    with pytest.raises(ValueError, match="STORED_SOFTWARE_IDENTITY_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_trace_column_hash_rewrite_without_trace_reseal_rejected(documentary):
    public, result = documentary
    mutate_document(result, "trace_events", lambda d: d.update(previous_trace_digest="0" * 64))
    with pytest.raises(ValueError, match="STORED_TRACE_CHAIN_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_partial_candidate_not_a_complete_stored_tree(documentary):
    public, result = documentary
    mutate_events(result, lambda events: events.pop())
    with pytest.raises(ValueError, match="EVENT_SEQUENCE_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_record_cannot_self_declare_private_to_bypass_source_replay(documentary):
    public, result = documentary
    result["reference"], result["execution_receipt"] = True, None
    (Path(result["output_dir"]) / "composition_events.json").write_bytes(b"[]")
    refresh_manifest(result)
    with pytest.raises(ValueError, match="PRIVATE_REFERENCE_ROLE_NOT_AUTHORIZED"):
        verify_stored_composition(result, public)


def test_mock_event_native_receipts_cannot_be_reordered(documentary):
    public, result = documentary
    def exchange(events):
        first, second = [event for event in events if event["kind"] == "NATIVE"][:2]
        first["native_receipt"], second["native_receipt"] = second["native_receipt"], first["native_receipt"]
    mutate_events(result, exchange)
    with pytest.raises(ValueError, match="STORED_NATIVE_EVENT_BINDING_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_artifact_metadata_not_only_bytes_is_checked(documentary):
    public, result = documentary
    conn = sqlite3.connect(result["native_database"])
    conn.execute("UPDATE artifacts SET metadata_json=?", ('{"mock_only":false}',))
    conn.commit()
    conn.close()
    refresh_manifest(result)
    with pytest.raises(ValueError, match="STORED_ARTIFACT_BINDING_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_events_export_cannot_hide_missing_native_commit(documentary):
    public, result = documentary
    path = Path(result["output_dir"]) / "native_traces.json"
    traces = json.loads(path.read_bytes())
    path.write_bytes(canonical(traces[:-1]))
    refresh_manifest(result)
    with pytest.raises(ValueError, match="SAVED_TRACE_EXPORT_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_source_binding_cannot_change_to_another_valid_public_slot(documentary):
    public, result = documentary
    result["selected_action"]["binding"] = 0
    with pytest.raises(ValueError, match="EVENT_PROGRAM_MISMATCH"):
        verify_stored_composition(result, public)


def test_mock_stored_auditor_has_no_neural_imports():
    import ast
    import cas_meta2.stored as stored
    tree = ast.parse(Path(stored.__file__).read_text())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    assert not any(name.split(".")[0] in {"torch", "numpy", "cas_cjt", "cas_meta1", "cas_meta0"} for name in names)
