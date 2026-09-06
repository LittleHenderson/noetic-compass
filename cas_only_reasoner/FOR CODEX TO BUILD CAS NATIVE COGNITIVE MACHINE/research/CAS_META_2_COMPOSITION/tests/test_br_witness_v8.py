"""Synthetic dict/byte tests only: no CAS database, tensor, native or cloud run."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from cas_meta2 import br_witness_v8 as w


def wire(contract, fields=()):
    return {"contract_type": contract, "schema_version": "synthetic-structure-only",
            **{name: None for name in fields}}


def seal(value, field):
    value[field] = w._digest({k: v for k, v in value.items() if k != field})


def artifact(payload, *, checkpoint=False):
    metadata = {} if checkpoint else {"dtype": "float32", "shape": [1, 2, 4]}
    encoding = "synthetic-model-bytes" if checkpoint else "synthetic-tensor-bytes"
    kind = "model-checkpoint" if checkpoint else "recurrent-state"
    header = {"encoding": encoding, "kind": kind, "media_type": "application/octet-stream",
              "metadata": metadata, "payload_byte_length": len(payload)}
    identity = sha256(w._canonical(header) + b"\n" + payload).hexdigest()
    record = {"artifact_id": "artifact-" + identity[:24], "sha256": identity, "kind": kind,
              "media_type": "application/octet-stream", "encoding": encoding,
              "metadata_json": w._canonical(metadata).decode("ascii"), "payload_hex": payload.hex()}
    ref = wire("TENSOR_ARTIFACT_REF")
    ref.update(artifact_id=record["artifact_id"], sha256=identity, dtype="uint8" if checkpoint else "float32",
               shape=[len(payload)] if checkpoint else [1, 2, 4], encoding=encoding, byte_length=len(payload))
    return ref, record


@pytest.fixture
def witness():
    model_ref, model_artifact = artifact(b"not a checkpoint", checkpoint=True)
    b_ref, b_artifact = artifact(b"synthetic B tensor")
    r_ref, r_artifact = artifact(b"synthetic R tensor")
    c_ref, c_artifact = artifact(b"synthetic C state")
    biases = []
    for name in ("A", "B", "C", "R"):
        bias = wire("BIAS_STATE", w.BIAS)
        bias.update(bias_id="bias-" + name, cjt_id=name, version=2, previous_digest="a" * 64)
        for compartment, fields in w.COMPARTMENTS.items():
            bias[compartment] = wire(compartment.upper(), fields.split())
        bias["stable"].update(cjt_id=name, formation_version=1, registered_operation_id="^6",
                              specialization_tags=[], lineage_refs=[], configuration_digest="b" * 64)
        bias["memory"].update(recurrent_state_ref=deepcopy(c_ref) if name == "C" else None,
                              recent_cause_ids=[], recent_candidate_effect_ids=[], verifier_receipt_ids=[],
                              repair_frame_ids=[], retrieved_memory_refs=[], provenance_refs=[])
        readiness = wire("READINESS_STATE")
        readiness["profile_id"] = "synthetic"
        for axis in ("desire", "wisdom", "power"):
            readiness[axis] = wire("READINESS_AXIS")
            readiness[axis].update(axis=axis.upper(), status="READY", score_ppm=1000000, threshold_ppm=1,
                                   reason_codes=[], evidence_refs=[], provenance=[])
        bias["rpm"].update(readiness=readiness, unmet_prerequisites=[], open_repair_ids=[],
                           suspended_parent_cause_id=None, return_addresses=[], repair_history=[])
        bias["operating"].update(region="ACTIVE", stability_status="synthetic", response_model_status="synthetic",
                                  semantic_outcome="SUPPORTED", previous_committed_verifier_receipt_id=None, last_tick=2)
        bias["theta"].update(model_id="synthetic-model", model_version=0, model_digest=model_ref["sha256"],
                              parameter_artifacts=[deepcopy(model_ref)], parameter_group_ids=[],
                              beta_microunits=1000000, operating_profile_id="synthetic", adapter_ids=[])
        bias["governance"].update(hard_permissions=["infer"], topology_permissions=[], learning_permissions=[],
                                   compute_ceiling_units=8, quarantined=False, state_write_authorities=[],
                                   memory_write_authorities=[], effect_publication_authorities=[], owner_restrictions=[])
        seal(bias, "state_digest")
        biases.append(bias)
    state = wire("NETWORK_STATE_ENVELOPE")
    state.update(schema_version="cas.neural-cjt.network-state-envelope/0.2", state_version=2,
                 previous_state_digest="c" * 64, model_id="synthetic-model", model_version=0,
                 model_digest=model_ref["sha256"], model_artifact_ref=model_ref, biases=biases)
    seal(state, "state_digest")
    traces, receipts, effects = [], {}, {}
    for i, (producer, ref) in enumerate((("B", b_ref), ("R", r_ref)), 1):
        trace = wire("TICK_TRACE", w.TRACE)
        trace.update(trace_id="trace-" + producer, tick=i, runtime_id="synthetic", software_digest="d" * 64,
                     cause_id="cause-" + producer, cjt_ids=[producer], pre_state_digest="c" * 64,
                     post_state_digest=state["state_digest"] if i == 2 else "c" * 64,
                     pre_model_digest=model_ref["sha256"], post_model_digest=model_ref["sha256"],
                     phases=[], candidate_effect_ids=[], published_effect_ids=["effect-" + producer],
                     verifier_receipt_ids=[], commit_receipt_id="receipt-" + producer,
                     memory_read_refs=[], memory_write_refs=[], accepted_intent_ids=[], rejected_intent_ids=[],
                     previous_trace_digest=None if i == 1 else traces[-1]["trace_digest"], sealed=True,
                     trace_digest=str(i) * 64)
        trace["phases"] = [dict(wire("TICK_PHASE_RECORD"), phase=phase, tick=i, inputs={}, outputs={}, diagnostics={}, compute_units=0)
                           for phase in w.PHASE_ORDER]
        receipt = wire("COMMIT_RECEIPT", w.RECEIPT)
        receipt.update(receipt_id=trace["commit_receipt_id"], tick=i, batch_id="batch-" + producer,
                       coordinator_id="synthetic", authority_contract_id="synthetic", authorized=True,
                       disposition="COMMITTED", accepted_intent_ids=[], rejected_intent_ids=[],
                       published_effect_ids=trace["published_effect_ids"], opened_repair_ids=[], reason_codes=["synthetic"],
                       atomic=True, rollback_of_receipt_id=None, persisted_snapshot_id="snapshot-" + producer,
                       trace_id=trace["trace_id"])
        for field in ("pre_state_digest", "post_state_digest", "pre_model_digest", "post_model_digest"):
            receipt[field] = trace[field]
        seal(receipt, "receipt_digest")
        effect = wire("PUBLISHED_EFFECT", w.EFFECT)
        effect.update(published_effect_id="effect-" + producer, candidate_effect_id="candidate-" + producer,
                      tick=i, producer_cjt_id=producer, content={"symbol": "synthetic"}, content_ref=ref,
                      verifier_receipt_id="verifier-" + producer, commit_receipt_id=receipt["receipt_id"],
                      provenance=["synthetic"], authoritative=True)
        seal(effect, "publication_digest")
        traces.append(trace)
        receipts[receipt["receipt_id"]] = receipt
        effects[producer] = effect
    model_record = {k: deepcopy(state[k]) for k in ("model_id", "model_version", "model_digest", "model_artifact_ref")}
    model_record.update(schema_version="cas.neural-cjt.model-version/0.2", config={"d_model": 4},
                        network={"nodes": ["A", "B", "C", "R"]}, decoder_labels=["L0", "L1", "L2", "L3"])
    return {
        "recovery": {"head": {"state_digest": state["state_digest"], "state_version": 2,
                                "trace_digest": traces[-1]["trace_digest"], "model_digest": model_ref["sha256"],
                                "commit_receipt_id": traces[-1]["commit_receipt_id"]},
                     "state": state, "traces": traces},
        "next_tick": 3, "published_effects": effects, "receipts": receipts,
        "transitions": [dict({field: [] for field in w.TRANSITION}, trace=deepcopy(trace),
                             commit_receipt=deepcopy(receipts[trace["commit_receipt_id"]]),
                             pre_state={}, post_state={}, prior_dependencies={}) for trace in traces],
        "artifacts": {a["artifact_id"]: a for a in (model_artifact, b_artifact, r_artifact, c_artifact)},
        "model_version_record": model_record,
        "external": {"source_files_sha256": {"synthetic.py": "a" * 64}, "config": model_record["config"],
                     "network": model_record["network"],
                     "decoder_manifests": {name: {"labels": model_record["decoder_labels"]} for name in ("A", "B", "C", "R")},
                     "operation_contracts": {"^6": {"synthetic": True}}, "goal_context": {"goal": "synthetic"},
                     "route_settings": {name: 1 if name.endswith("units") or name == "unit_scale" else False for name in w.ROUTE},
                     "expected_symbol": "L2", "permissions": ["infer"], "available_limits": {"compute_units": 8},
                     "numeric_settings": {"synthetic": True}, "runtime_identity": {"synthetic": True}},
        "ownership": {"mode": "DIRECT_NATIVE", "active_outer_executor": None, "suspended_outer_call": False, "outer_frames": []}}


def codes(result):
    return {item["code"] for item in result["reasons"]}


def reseal_state(value):
    for bias in value["recovery"]["state"]["biases"]:
        seal(bias, "state_digest")
    seal(value["recovery"]["state"], "state_digest")


def test_equal_complete_synthetic_records_pass_only_recorded_consistency(witness):
    before = deepcopy(witness)
    result = w.validate_before_state_pair(witness, deepcopy(witness))
    assert result["ok"] is True
    assert result["status"] == "RECORDED_BEFORE_STATE_CONSISTENT"
    assert result["native_verified"] is False
    assert result["outer_ownership_verified"] is False
    assert result["details"]["left"]["ownership_status"] == "EXPLICIT_CALLER_ASSERTION_ONLY"
    assert result["witness_sha256"]["left"] == result["witness_sha256"]["right"]
    assert witness == before
    assert "not established" in result["boundary"]


@pytest.mark.parametrize("field", w.WRAPPER)
def test_missing_sections_have_typed_reason(witness, field):
    del witness[field]
    result = w.validate_before_state_pair(witness, deepcopy(witness))
    assert not result["ok"]
    assert "MISSING_FIELD" in codes(result)


@pytest.mark.parametrize("cjt", ("A", "B", "C", "R"))
@pytest.mark.parametrize("field,value", [
    ("open_repair_ids", ["repair-1"]),
    ("suspended_parent_cause_id", "suspended-cause"),
    ("return_addresses", ["return-1"]),
])
def test_any_cjt_pending_repair_or_suspension_is_refused(witness, cjt, field, value):
    bias = next(b for b in witness["recovery"]["state"]["biases"] if b["cjt_id"] == cjt)
    bias["rpm"][field] = value
    reseal_state(witness)
    witness["recovery"]["head"]["state_digest"] = witness["recovery"]["state"]["state_digest"]
    result = w.validate_before_state_pair(witness, deepcopy(witness))
    assert "PENDING_REPAIR_OR_SUSPENSION" in codes(result)


@pytest.mark.parametrize("kind", ("model", "C", "B", "R"))
def test_required_artifact_coverage(witness, kind):
    if kind == "model":
        ref = witness["recovery"]["state"]["model_artifact_ref"]
    elif kind == "C":
        ref = witness["recovery"]["state"]["biases"][2]["memory"]["recurrent_state_ref"]
    else:
        ref = witness["published_effects"][kind]["content_ref"]
    del witness["artifacts"][ref["artifact_id"]]
    assert "ARTIFACT_EVIDENCE_MISSING" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_equal_changed_payload_is_not_accepted_from_dict_equality(witness):
    key = witness["published_effects"]["B"]["content_ref"]["artifact_id"]
    witness["artifacts"][key]["payload_hex"] = b"changed".hex()
    assert "ARTIFACT_BOUND_DIGEST_MISMATCH" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_raw_payload_hash_is_not_the_native_bound_artifact_digest(witness):
    key = witness["published_effects"]["B"]["content_ref"]["artifact_id"]
    artifact_value = witness["artifacts"][key]
    assert sha256(bytes.fromhex(artifact_value["payload_hex"])).hexdigest() != artifact_value["sha256"]
    artifact_value["sha256"] = sha256(bytes.fromhex(artifact_value["payload_hex"])).hexdigest()
    assert "ARTIFACT_BOUND_DIGEST_MISMATCH" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


@pytest.mark.parametrize("field,value", [("mode", "META2_PAUSED"), ("active_outer_executor", "executor"),
                                       ("suspended_outer_call", True), ("outer_frames", [{"pc": 3}])])
def test_explicit_no_outer_owner_is_required(witness, field, value):
    witness["ownership"][field] = value
    assert "ACTIVE_OR_UNSUPPORTED_OUTER_CALLER" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


@pytest.mark.parametrize("field", ("source_files_sha256", "decoder_manifests", "operation_contracts", "permissions",
                                    "available_limits", "route_settings", "goal_context"))
def test_changed_external_controls_never_pass_pair_equality(witness, field):
    other = deepcopy(witness)
    if type(other["external"][field]) is dict:
        other["external"][field]["changed"] = 1
    else:
        other["external"][field].append("changed")
    result = w.validate_before_state_pair(witness, other)
    assert "BEFORE_STATE_MISMATCH" in codes(result)


def test_missing_bias_compartment_is_not_equal_complete_state(witness):
    del witness["recovery"]["state"]["biases"][0]["governance"]
    reseal_state(witness)
    witness["recovery"]["head"]["state_digest"] = witness["recovery"]["state"]["state_digest"]
    assert "MISSING_FIELD" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_trace_order_and_next_tick_are_not_optional(witness):
    witness["recovery"]["traces"].reverse()
    assert "TRACE_ORDER_LINK_MISMATCH" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


@pytest.mark.parametrize("value", (2, 4, True))
def test_next_tick_rejects_wrong_values_and_bool(witness, value):
    witness["next_tick"] = value
    assert "NEXT_TICK_MISMATCH" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_effect_receipt_must_exist(witness):
    witness["receipts"].clear()
    assert "COMMIT_RECEIPT_MISSING" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_resealed_receipt_cannot_point_to_a_different_trace(witness):
    receipt = witness["receipts"]["receipt-B"]
    receipt["trace_id"] = "trace-R"
    seal(receipt, "receipt_digest")
    assert "EFFECT_TRACE_LINK_MISMATCH" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_comparison_retains_extra_nested_values(witness):
    other = deepcopy(witness)
    other["model_version_record"]["new_metadata"] = "must be compared"
    result = w.validate_before_state_pair(witness, other)
    assert {"arm": "pair", "code": "BEFORE_STATE_MISMATCH", "path": "model_version_record"} in result["reasons"]


def test_missing_transition_is_refused(witness):
    witness["transitions"].pop()
    assert "TRANSITION_COVERAGE_MISMATCH" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_changed_transition_values_are_compared_in_full(witness):
    other = deepcopy(witness)
    other["transitions"][0]["prior_dependencies"]["changed"] = {"value": 7}
    result = w.validate_before_state_pair(witness, other)
    assert {"arm": "pair", "code": "BEFORE_STATE_MISMATCH", "path": "transitions"} in result["reasons"]


def test_transition_trace_order_must_match_recovery(witness):
    witness["transitions"].reverse()
    assert "TRANSITION_TRACE_MISMATCH" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_prior_transition_tensor_reference_requires_retained_bytes(witness):
    ref, _ = artifact(b"an old tensor not retained in the witness")
    witness["transitions"][0]["prior_dependencies"]["example"] = {"content_ref": ref}
    assert "ARTIFACT_EVIDENCE_MISSING" in codes(w.validate_before_state_pair(witness, deepcopy(witness)))


def test_import_is_pure_in_a_fresh_process():
    root = Path(__file__).resolve().parents[1]
    code = """
import builtins, sys
blocked = {'torch','casformer','cas_cjt','tensorflow','jax','numpy','boto3','botocore','sqlite3','socket'}
original = builtins.__import__
def guard(name, *args, **kwargs):
    if name.split('.')[0] in blocked:
        raise RuntimeError('FORBIDDEN_IMPORT:' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guard
sys.path.insert(0, sys.argv[1])
from cas_meta2.br_witness_v8 import validate_before_state_pair
assert not validate_before_state_pair({}, {})['ok']
assert not any(name.split('.')[0] in blocked for name in sys.modules)
"""
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(root)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
