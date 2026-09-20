"""Read-only documentary audit of completed compositions; no neural imports.

This adds a source replay to the native schema/integrity checks. It does not
re-execute a CJT, prove GPU use, or establish crash/restart recovery. An external
prediction seal must supply ``expected_action`` to bind selection provenance.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import struct

from .executor import CompositionExecutor, ExecutionLimits, canonical, digest


QUANTA = ("route_quanta", "reasoning_step_quanta", "branch_quanta",
          "memory_read_quanta", "diagnostic_probe_quanta")
PHASES = ("READ", "CANDIDATE", "READINESS", "ROUTE", "EXECUTE", "OBSERVE",
          "VERIFY", "DIAGNOSE", "EMIT", "COMMIT", "TRACE")
REQUIRED_FILES = {"native.db", "native_traces.json", "composition_events.json",
                  "native_kernel_events.json"}


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "DUPLICATE_JSON_FIELD")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
    canonical(value)  # Also rejects nonfinite values produced by huge exponents.
    return value


def _document(row):
    _require(row is not None, "MISSING_STORED_DOCUMENT")
    raw = row["payload_json"]
    value = _json(raw)
    _require(canonical(value).decode("ascii") == raw
             and sha256(raw.encode("utf-8")).hexdigest() == row["payload_sha256"],
             "STORED_DOCUMENT_HASH_MISMATCH")
    return value


def _units(plan):
    def total(value):
        if type(value) is list:
            return sum(total(item) for item in value)
        _require(type(value) is int and value >= 0, "INVALID_STORED_COMPUTE_QUANTA")
        return value
    _require(type(plan) is dict and all(key in plan for key in QUANTA), "MISSING_STORED_COMPUTE_PLAN")
    units = sum(total(plan[key]) for key in QUANTA)
    _require(units > 0, "EMPTY_STORED_COMPUTE_PLAN")
    return units


class _ReadOnlyBackend:
    """Only already-checked observations, Effects, receipts and head are exposed."""

    def __init__(self, identity, head, observations, effects, receipts):
        self._identity, self._head = identity, head
        self.observations, self.effects, self.receipts = observations, effects, receipts

    def identity(self):
        return deepcopy(self._identity)

    def head(self):
        return deepcopy(self._head)

    def input_reference(self, binding):
        _require(binding in self.observations, "MISSING_STORED_OBSERVATION")
        return deepcopy(self.observations[binding])

    def validate_reference(self, reference):
        _require(type(reference) is dict, "INVALID_STORED_REFERENCE")
        if reference.get("kind") == "observation":
            expected = self.observations.get(reference.get("slot"))
        else:
            expected = self.effects.get(reference.get("effect_id"))
        _require(reference == expected, "FORGED_OR_MISSING_STORED_REFERENCE")

    def validate_receipt(self, receipt, reference):
        _require(type(receipt) is dict, "INVALID_STORED_RECEIPT")
        expected = self.receipts.get(receipt.get("receipt_id"))
        _require(receipt == expected and receipt["published_effect_ids"] == [reference.get("effect_id")],
                 "STORED_NATIVE_RECEIPT_MISMATCH")

    def prepare(self, *args):
        raise RuntimeError("READ_ONLY_AUDIT_CANNOT_PREPARE")

    def execute(self, *args):
        raise RuntimeError("READ_ONLY_AUDIT_CANNOT_EXECUTE")


def verify_stored_composition(result, public, *, traces=None, expected_action=None,
                              allow_private_reference=False):
    """Verify saved source, ordered commits, named references, return and charges.

    The caller still validates each trace against the published native schema.
    The result below makes the private direct-reference exception explicit.
    No summary count, final reference, compute charge or head is trusted alone.
    """
    output = Path(result["output_dir"]).resolve()
    manifest = result["evidence_sha256"]
    _require(type(manifest) is dict and REQUIRED_FILES <= set(manifest), "MISSING_REQUIRED_STORED_EVIDENCE")
    for name, expected in manifest.items():
        path = (output / name).resolve()
        _require(type(name) is str and Path(name).name == name and path.parent == output,
                 "INVALID_STORED_EVIDENCE_PATH")
        _require(sha256(path.read_bytes()).hexdigest() == expected, "STORED_EVIDENCE_HASH_MISMATCH")
    _require(result["native_database"] == str(output / "native.db"), "NATIVE_DATABASE_PATH_MISMATCH")
    _require(result["public_digest"] == digest(public), "STORED_PUBLIC_DIGEST_MISMATCH")
    _require(type(result["reference"]) is bool and (not result["reference"] or allow_private_reference),
             "PRIVATE_REFERENCE_ROLE_NOT_AUTHORIZED")
    if expected_action is not None:
        _require(canonical(result["selected_action"]) == canonical(expected_action), "SEALED_ACTION_MISMATCH")
    observations, tags = {}, {}
    for row in public["observations"]:
        slot = row["slot"]
        _require(type(slot) is int and slot in (0, 1, 2) and slot not in observations,
                 "INVALID_STORED_OBSERVATION_SLOT")
        observations[slot] = {"kind": "observation", "slot": slot, "public_digest": digest(public),
                              "payload_sha256": sha256(struct.pack("<8f", *row["values"])).hexdigest()}
        tags[slot] = row["tag"]
    _require(set(observations) == {0, 1, 2}, "MISSING_STORED_OBSERVATION")
    events = _json((output / "composition_events.json").read_bytes())
    _require(type(events) is list, "INVALID_STORED_EVENTS")
    connection = sqlite3.connect((output / "native.db").as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return _verify(connection, result, observations, tags, events, traces, expected_action is not None)
    finally:
        connection.close()


def _verify(conn, result, observations, tags, events, supplied_traces, action_checked):
    def artifact(ref, *, tensor=False):
        row = conn.execute("SELECT * FROM artifacts WHERE artifact_id=?", (ref["artifact_id"],)).fetchone()
        _require(row is not None, "MISSING_STORED_ARTIFACT")
        metadata, payload = _json(row["metadata_json"]), bytes(row["payload"])
        header = {"encoding": row["encoding"], "kind": row["kind"], "media_type": row["media_type"],
                  "metadata": metadata, "payload_byte_length": len(payload)}
        checksum = sha256(canonical(header) + b"\n" + payload).hexdigest()
        _require(canonical(metadata).decode("ascii") == row["metadata_json"]
                 and row["sha256"] == checksum and row["artifact_id"] == "artifact-" + checksum[:24]
                 and ref["sha256"] == checksum and ref["byte_length"] == len(payload)
                 and ref["encoding"] == row["encoding"], "STORED_ARTIFACT_BINDING_MISMATCH")
        if tensor:
            _require(ref["dtype"] == "float32" and ref["shape"] == [1, 2, 4]
                     and len(payload) == 32, "STORED_TENSOR_REFERENCE_MISMATCH")
        return payload

    def record(table, key, receipt_id):
        _require(table in ("causes", "published_effects"), "UNSUPPORTED_STORED_TABLE")
        row = conn.execute("SELECT * FROM " + table + " WHERE record_id=?", (key,)).fetchone()
        doc = _document(row)
        _require(row["commit_receipt_id"] == receipt_id, "STORED_DOCUMENT_COMMIT_MISMATCH")
        return doc

    identity = deepcopy(result["runtime_identity"])
    _require(identity == result["runtime_identity_after"], "STORED_RUNTIME_IDENTITY_CHANGED")
    model_digest = identity["model"]["model_digest"]
    model_row = conn.execute("SELECT * FROM model_versions WHERE model_digest=?", (model_digest,)).fetchone()
    model = _document(model_row)
    _require(model["model_digest"] == model_digest == identity["stored_model_digest"]
             and model["model_artifact_ref"]["sha256"] == model_digest
             and model_row["artifact_id"] == model["model_artifact_ref"]["artifact_id"]
             and model["network"] == identity["topology"], "STORED_MODEL_IDENTITY_MISMATCH")
    _require(sha256(artifact(model["model_artifact_ref"])).hexdigest()
             == identity["model"]["parameter_bytes_sha256"], "STORED_PARAMETER_BYTES_MISMATCH")
    traces, native_events, receipts, effects, produced, rows = [], [], {}, {}, {}, []
    previous_trace, previous_state = None, None
    for index, row in enumerate(conn.execute("SELECT * FROM trace_events ORDER BY sequence")):
        trace = _document(row)
        body = {key: value for key, value in trace.items() if key not in ("trace_digest", "trace_id")}
        trace_id = "trace-" + digest(body)[:24]
        _require(row["sequence"] == index + 1 and type(trace["tick"]) is int and trace["tick"] == index + 1
                 and trace["trace_id"] == trace_id
                 and trace["trace_digest"] == digest({**body, "trace_id": trace_id})
                 and trace["previous_trace_digest"] == previous_trace
                 and (previous_state is None or trace["pre_state_digest"] == previous_state),
                 "STORED_TRACE_CHAIN_MISMATCH")
        _require(all(row[key] == trace[key] for key in (
            "trace_id", "trace_digest", "previous_trace_digest", "pre_state_digest", "post_state_digest")),
            "STORED_TRACE_COLUMN_MISMATCH")
        _require(trace["sealed"] is True
                 and tuple(p.get("phase", p.get("name")) for p in trace["phases"]) == PHASES
                 and trace["pre_model_digest"] == trace["post_model_digest"] == model_digest
                 and trace["software_digest"] == identity["software_digest"], "STORED_TRACE_IDENTITY_MISMATCH")
        receipt_row = conn.execute("SELECT * FROM commit_receipts WHERE receipt_id=?",
                                   (trace["commit_receipt_id"],)).fetchone()
        receipt = _document(receipt_row)
        _require(receipt["receipt_digest"] == digest({k: v for k, v in receipt.items() if k != "receipt_digest"})
                 and receipt["receipt_id"] == "commit-" + receipt_row["request_digest"][:24]
                 and all(receipt[k] == receipt_row[k] for k in (
                     "receipt_id", "batch_id", "pre_state_digest", "post_state_digest", "rollback_of_receipt_id"))
                 and receipt_row["trace_digest"] == trace["trace_digest"]
                 and all(receipt[k] == trace[k] for k in (
                     "trace_id", "tick", "pre_state_digest", "post_state_digest", "pre_model_digest", "post_model_digest"))
                 and receipt["authorized"] is True and receipt["atomic"] is True
                 and receipt["disposition"] == "COMMITTED"
                 and receipt["persisted_snapshot_id"] == "snapshot-" + trace["post_state_digest"][:24],
                 "STORED_COMMIT_RECEIPT_MISMATCH")
        software = {"runtime_id": trace["runtime_id"], "authority_contract_id": receipt["authority_contract_id"],
                    "topology": identity["topology"], "operation_contracts": identity["contracts"],
                    "decoders": identity["decoders"]}
        _require(digest(software) == identity["software_digest"], "STORED_SOFTWARE_IDENTITY_MISMATCH")
        ids = trace["published_effect_ids"]
        _require(type(ids) is list and len(ids) == 1 and ids == receipt["published_effect_ids"]
                 and ids[0] not in effects, "STORED_EFFECT_PUBLICATION_MISMATCH")
        effect = record("published_effects", ids[0], receipt["receipt_id"])
        _require(effect["published_effect_id"] == ids[0] and effect["commit_receipt_id"] == receipt["receipt_id"]
                 and effect["tick"] == trace["tick"] and effect["authoritative"] is True
                 and effect["producer_cjt_id"] in trace["cjt_ids"]
                 and effect["publication_digest"] == digest({k: v for k, v in effect.items() if k != "publication_digest"}),
                 "STORED_EFFECT_BINDING_MISMATCH")
        output_ref = {"kind": "effect", "effect_id": ids[0], "producer_cjt_id": effect["producer_cjt_id"],
                      "payload_sha256": sha256(artifact(effect["content_ref"], tensor=True)).hexdigest()}
        cause = record("causes", trace["cause_id"], receipt["receipt_id"])
        _require(cause["cause_id"] == trace["cause_id"] and cause["tick"] == trace["tick"],
                 "STORED_CAUSE_BINDING_MISMATCH")
        input_sha = sha256(artifact(cause["content_ref"], tensor=True)).hexdigest()
        parent = cause["parent_effect_id"]
        if parent is None:
            slot = cause["content"]["binding_slot"]
            _require(slot in observations and cause["content"].get("task") == "cas-meta2-observation"
                     and cause["content"]["public_digest"] == result["public_digest"]
                     and cause["content"]["binding_tag"] == tags[slot], "STORED_PUBLIC_INPUT_MISMATCH")
            input_ref, source = observations[slot], -1
        else:
            _require(parent in effects, "UNKNOWN_OR_FUTURE_STORED_EFFECT")
            input_ref, source = effects[parent], produced[parent]
            _require(cause["originating_cjt_id"] == input_ref["producer_cjt_id"], "STORED_PARENT_SCOPE_MISMATCH")
        _require(input_sha == input_ref["payload_sha256"], "STORED_INPUT_PAYLOAD_MISMATCH")
        plan = trace["compute_plan"]
        units = _units(plan)
        compact = {"receipt_id": receipt["receipt_id"], "trace_id": trace_id,
                   "published_effect_ids": ids, "units": units, "plan_digest": digest(plan)}
        _require(compact["receipt_id"] not in receipts, "DUPLICATE_STORED_RECEIPT")
        receipts[compact["receipt_id"]] = compact
        effects[ids[0]], produced[ids[0]] = output_ref, index
        native_events.append({"cjt_id": effect["producer_cjt_id"], "input_reference": input_ref,
                              "output_reference": output_ref, "native_receipt": compact})
        rows.append({"cjt_id": effect["producer_cjt_id"], "input_node": source,
                     "input_sha256": input_sha, "output_sha256": output_ref["payload_sha256"]})
        traces.append(trace)
        previous_trace, previous_state = trace["trace_digest"], trace["post_state_digest"]
    _require(traces and (supplied_traces is None or supplied_traces == traces), "STORED_TRACE_LIST_MISMATCH")
    _require(_json((Path(result["output_dir"]) / "native_traces.json").read_bytes()) == traces,
             "SAVED_TRACE_EXPORT_MISMATCH")
    _require(conn.execute("SELECT COUNT(*) FROM commit_receipts").fetchone()[0] == len(traces)
             and conn.execute("SELECT COUNT(*) FROM published_effects").fetchone()[0] == len(traces),
             "UNACCOUNTED_STORED_COMMITS")
    head_rows = list(conn.execute("SELECT * FROM active_head"))
    _require(len(head_rows) == 1 and head_rows[0]["singleton"] == 1, "INVALID_STORED_HEAD")
    head = {key: head_rows[0][key] for key in (
        "state_digest", "state_version", "trace_digest", "model_digest", "commit_receipt_id")}
    last = traces[-1]
    _require(head["state_digest"] == last["post_state_digest"] and head["trace_digest"] == last["trace_digest"]
             and head["model_digest"] == model_digest and head["commit_receipt_id"] == last["commit_receipt_id"],
             "STORED_FINAL_HEAD_MISMATCH")
    state_row = conn.execute("SELECT * FROM state_versions WHERE state_digest=?", (head["state_digest"],)).fetchone()
    state = _document(state_row)
    _require(state_row["state_version"] == head["state_version"] == state["state_version"]
             and state["model_digest"] == model_digest and state["state_digest"] == head["state_digest"]
             and digest({key: value for key, value in state.items() if key != "state_digest"}) == head["state_digest"]
             and state_row["parent_state_digest"] == state["previous_state_digest"] == last["pre_state_digest"],
             "STORED_HEAD_STATE_MISMATCH")
    backend = _ReadOnlyBackend(identity, head, observations, effects, receipts)
    final = result["final_reference"]
    backend.validate_reference(final)
    _require(final.get("kind") == "effect", "STORED_FINAL_EFFECT_REQUIRED")
    spent = sum(r["units"] for r in receipts.values())
    limits = ExecutionLimits()
    _require(spent <= limits.policy_units and len(traces) <= limits.max_native_runs, "STORED_POLICY_BUDGET_EXCEEDED")
    _require(type(result["reserved_policy_units"]) is int and result["reserved_policy_units"] == spent
             and type(result["native_trace_count"]) is int and result["native_trace_count"] == len(traces),
             "STORED_SUMMARY_ACCOUNTING_MISMATCH")
    _require(type(result["reference"]) is bool, "INVALID_PRIVATE_REFERENCE_FLAG")
    if result["reference"]:
        _require(events == [] and result["execution_receipt"] is None, "PRIVATE_REFERENCE_HAS_CALL_TREE")
        report = None
    else:
        selected = result["selected_action"]
        _require(events and re.fullmatch(r"[0-9a-f]{32}", events[0]["run_id"]) is not None,
                 "MISSING_STORED_RUNTIME_ID")
        saved_native = [{key: event.get(key) for key in (
            "cjt_id", "input_reference", "output_reference", "native_receipt")}
            for event in events if event.get("kind") == "NATIVE"]
        _require(saved_native == native_events, "STORED_NATIVE_EVENT_BINDING_MISMATCH")
        replay = CompositionExecutor(backend, selected["program"], binding=selected["binding"],
                                     chain_id=events[0]["chain_id"])
        # Restore only completed documentary evidence. There is no checkpoint
        # continuation API here and neither prepare() nor execute() is called.
        replay.run_id = events[0]["run_id"]
        replay._events, replay._frames = deepcopy(events), []
        replay.result_reference = deepcopy(final)
        replay._runs, replay._spent = len(traces), spent
        report = replay.validate_evidence()
        _require(report == result["execution_receipt"], "STORED_EXECUTION_RECEIPT_MISMATCH")
    return {"rows": rows, "return_node": produced[final["effect_id"]],
            "final_output_sha256": final["payload_sha256"], "trace_count": len(traces),
            "reserved_policy_units": spent, "native_head": head,
            "stored_call_tree_verified": not result["reference"],
            "expected_action_checked": action_checked,
            "audit_method": "read-only-sqlite-source-replay/0.1",
            "execution_receipt": report}
