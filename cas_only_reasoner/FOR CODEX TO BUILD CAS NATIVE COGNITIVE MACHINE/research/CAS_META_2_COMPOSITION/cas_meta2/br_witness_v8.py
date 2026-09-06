"""Pure consistency check for two recorded B/R before-state witnesses.

Never imports or executes native/model/provider code and never opens a database.
The caller must collect recovery with coordinator.restore_and_verify(), receipts
with receipt_by_id(), effects with immutable_document(), and artifacts with
load_artifact(). Equality here neither proves those calls occurred nor attests
that an outer caller really is absent. Native validation remains a separate gate.

Witness wrapper keys: recovery={head,state,traces}, transitions (one full
store.reconstruct_transition() result per ordered trace), next_tick, published_effects
(B/R), receipts (keyed by receipt_id), artifacts (keyed by artifact_id),
model_version_record, external, ownership. Artifact transport copies every
StoredArtifact field except bytes payload is represented by lowercase payload_hex.
The wrapper is not an additional native contract or a replacement verifier.
"""
from hashlib import sha256
import json
import re

SCHEMA = "cas-meta2-br-before-state-check/8"
BOUNDARY = (
    "Recorded JSON/byte consistency only. Native restore, durable-store validity, "
    "absence of a real outer caller, numerical contrast and task correctness "
    "are not established by this pure check."
)
# Field names read from the unchanged v0.2 native dataclasses/to_dict methods.
HEAD = "state_digest state_version trace_digest model_digest commit_receipt_id".split()
STATE = "state_version previous_state_digest model_id model_version model_digest model_artifact_ref biases state_digest".split()
BIAS = "bias_id cjt_id version previous_digest stable memory rpm operating theta governance state_digest".split()
COMPARTMENTS = {
    "stable": "cjt_id formation_version registered_operation_id specialization_tags lineage_refs configuration_digest",
    "memory": "recurrent_state_ref recent_cause_ids recent_candidate_effect_ids verifier_receipt_ids repair_frame_ids retrieved_memory_refs provenance_refs",
    "rpm": "readiness unmet_prerequisites open_repair_ids suspended_parent_cause_id return_addresses repair_history",
    "operating": "region stability_status response_model_status semantic_outcome previous_committed_verifier_receipt_id last_tick",
    "theta": "model_id model_version model_digest parameter_artifacts parameter_group_ids beta_microunits operating_profile_id adapter_ids",
    "governance": "hard_permissions topology_permissions learning_permissions compute_ceiling_units quarantined state_write_authorities memory_write_authorities effect_publication_authorities owner_restrictions",
}
TRACE = ("trace_id tick runtime_id software_digest cause_id cjt_ids pre_state_digest post_state_digest pre_model_digest "
         "post_model_digest phases candidate_effect_ids published_effect_ids verifier_receipt_ids commit_receipt_id "
         "memory_read_refs memory_write_refs accepted_intent_ids rejected_intent_ids previous_trace_digest sealed trace_digest").split()
RECEIPT = ("receipt_id tick batch_id coordinator_id authority_contract_id authorized disposition pre_state_digest "
           "post_state_digest pre_model_digest post_model_digest accepted_intent_ids rejected_intent_ids "
           "published_effect_ids opened_repair_ids reason_codes atomic rollback_of_receipt_id persisted_snapshot_id trace_id receipt_digest").split()
EFFECT = "published_effect_id candidate_effect_id tick producer_cjt_id content content_ref verifier_receipt_id commit_receipt_id provenance publication_digest authoritative".split()
EXTERNAL = "source_files_sha256 config network decoder_manifests operation_contracts goal_context route_settings expected_symbol permissions available_limits numeric_settings runtime_identity".split()
ROUTE = "drive_units resistance_capability_units resistance_context_units resistance_resource_units resistance_memory_units unit_scale causal topology_open permission_open budget_open force_breakdown".split()
WRAPPER = "recovery transitions next_tick published_effects receipts artifacts model_version_record external ownership".split()
TRANSITION = ("trace commit_receipt pre_state post_state transition_batches causes candidate_effects verifier_receipts "
              "qualification_receipts state_intents model_intents memory_intents published_effects memory_records "
              "repair_frames repair_outcomes memory_read_records emitted_repair_subgoals model_versions prior_dependencies artifacts").split()
PHASE_ORDER = "READ CANDIDATE READINESS ROUTE EXECUTE OBSERVE VERIFY DIAGNOSE EMIT COMMIT TRACE".split()


class _Refused(ValueError):
    def __init__(self, code, path):
        self.code, self.path = code, path


def _require(condition, code, path):
    if not condition:
        raise _Refused(code, path)


def _canonical(value):
    # JSON serialization preserves bool versus int, ordered arrays and all fields.
    def check(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("Only JSON objects, arrays, strings, integers, booleans and null are accepted")
    check(value)
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def _required(value, fields, path, *, native=False):
    _require(type(value) is dict, "OBJECT_REQUIRED", path)
    for name in (*(["contract_type", "schema_version"] if native else []), *fields):
        _require(name in value, "MISSING_FIELD", path + "." + name)
    return value


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def _declared(value, field, path):
    _require(value[field] == _digest({k: v for k, v in value.items() if k != field}),
             "DECLARED_DIGEST_MISMATCH", path + "." + field)


def _hex_digest(value, path):
    _require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None, "SHA256_REQUIRED", path)


def _artifact(value, key, path):
    _required(value, "artifact_id sha256 kind media_type encoding metadata_json payload_hex".split(), path)
    _require(value["artifact_id"] == key, "ARTIFACT_ID_MISMATCH", path)
    for name in ("artifact_id", "kind", "media_type", "encoding"):
        _require(type(value[name]) is str and bool(value[name]), "ARTIFACT_TEXT_REQUIRED", path + "." + name)
    raw_hex = value["payload_hex"]
    _require(type(raw_hex) is str and re.fullmatch("(?:[0-9a-f]{2})*", raw_hex) is not None,
             "ARTIFACT_HEX_REQUIRED", path + ".payload_hex")
    payload = bytes.fromhex(raw_hex)
    try:
        metadata = json.loads(value["metadata_json"])
        _require(type(metadata) is dict, "ARTIFACT_METADATA_OBJECT_REQUIRED", path)
        # Artifact metadata allows finite floats, unlike authoritative contract JSON.
        meta_raw = json.dumps(metadata, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
        _require(meta_raw == value["metadata_json"], "ARTIFACT_METADATA_NOT_CANONICAL", path)
        header = json.dumps({"encoding": value["encoding"], "kind": value["kind"],
                             "media_type": value["media_type"], "metadata": metadata,
                             "payload_byte_length": len(payload)},
                            ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    except (TypeError, ValueError) as error:
        if isinstance(error, _Refused):
            raise
        raise _Refused("ARTIFACT_METADATA_INVALID", path) from error
    expected = sha256(header + b"\n" + payload).hexdigest()
    _require(value["sha256"] == expected and key == "artifact-" + expected[:24],
             "ARTIFACT_BOUND_DIGEST_MISMATCH", path)
    return {"byte_length": len(payload), "payload_sha256": sha256(payload).hexdigest(),
            "sha256": expected, "metadata": metadata}


def _reference(ref, artifacts, artifact_checks, path):
    _required(ref, "artifact_id sha256 dtype shape encoding byte_length".split(), path, native=True)
    _require(ref["contract_type"] == "TENSOR_ARTIFACT_REF", "TENSOR_REFERENCE_REQUIRED", path)
    key = ref["artifact_id"]
    _require(type(key) is str and key in artifacts, "ARTIFACT_EVIDENCE_MISSING", path)
    record, checked = artifacts[key], artifact_checks[key]
    _require(ref["sha256"] == record["sha256"] and ref["encoding"] == record["encoding"]
             and type(ref["byte_length"]) is int and ref["byte_length"] == checked["byte_length"],
             "ARTIFACT_REFERENCE_MISMATCH", path)
    shape = ref["shape"]
    _require(type(shape) is list and bool(shape) and all(type(x) is int and x >= 0 for x in shape),
             "TENSOR_SHAPE_REQUIRED", path)
    # Checkpoint metadata differs from ordinary tensors; dtype/shape are checked
    # when those keys are declared by the stored artifact itself.
    for name in ("dtype", "shape"):
        if name in checked["metadata"]:
            _require(ref[name] == checked["metadata"][name], "ARTIFACT_METADATA_REFERENCE_MISMATCH", path + "." + name)
    return key


def _all_references(value, artifacts, checks, path):
    if type(value) is dict:
        if value.get("contract_type") == "TENSOR_ARTIFACT_REF":
            _reference(value, artifacts, checks, path)
        for key, child in value.items():
            _all_references(child, artifacts, checks, path + "." + key)
    elif type(value) is list:
        for index, child in enumerate(value):
            _all_references(child, artifacts, checks, path + "." + str(index))


def _one(witness, expected_cjt_ids):
    _required(witness, WRAPPER, "witness")
    recovery = _required(witness["recovery"], ("head", "state", "traces"), "recovery")
    head = _required(recovery["head"], HEAD, "recovery.head")
    state = _required(recovery["state"], STATE, "recovery.state", native=True)
    _require(state["contract_type"] == "NETWORK_STATE_ENVELOPE"
             and state["schema_version"] == "cas.neural-cjt.network-state-envelope/0.2",
             "NETWORK_STATE_SCHEMA_MISMATCH", "recovery.state")
    _declared(state, "state_digest", "recovery.state")
    for name in ("state_digest", "state_version", "model_digest"):
        _require(_canonical(head[name]) == _canonical(state[name]), "HEAD_STATE_MISMATCH", "recovery.head." + name)
    _require(type(state["state_version"]) is int and state["state_version"] >= 0,
             "STATE_VERSION_REQUIRED", "recovery.state")
    biases = state["biases"]
    _require(type(biases) is list and all(type(b) is dict for b in biases), "BIASES_REQUIRED", "recovery.state.biases")
    ids = [b.get("cjt_id") for b in biases]
    _require(len(ids) == len(expected_cjt_ids) and set(ids) == set(expected_cjt_ids),
             "CJT_COVERAGE_MISMATCH", "recovery.state.biases")
    artifacts = witness["artifacts"]
    _require(type(artifacts) is dict and bool(artifacts), "ARTIFACTS_REQUIRED", "artifacts")
    checks = {key: _artifact(value, key, "artifacts." + key) for key, value in artifacts.items()}
    _reference(state["model_artifact_ref"], artifacts, checks, "recovery.state.model_artifact_ref")
    _require(state["model_artifact_ref"]["sha256"] == state["model_digest"],
             "MODEL_ARTIFACT_MISMATCH", "recovery.state")
    c_ref = None
    for bias in biases:
        path = "recovery.state.biases." + bias["cjt_id"]
        _required(bias, BIAS, path, native=True)
        _declared(bias, "state_digest", path)
        for compartment, fields in COMPARTMENTS.items():
            _required(bias[compartment], fields.split(), path + "." + compartment, native=True)
        _require(bias["stable"]["cjt_id"] == bias["cjt_id"], "CJT_IDENTITY_MISMATCH", path)
        rpm = bias["rpm"]
        _require(rpm["open_repair_ids"] == [] and rpm["suspended_parent_cause_id"] is None
                 and rpm["return_addresses"] == [], "PENDING_REPAIR_OR_SUSPENSION", path + ".rpm")
        ready = _required(rpm["readiness"], ("profile_id", "desire", "wisdom", "power"), path + ".rpm.readiness", native=True)
        for axis in ("desire", "wisdom", "power"):
            _required(ready[axis], "axis status score_ppm threshold_ppm reason_codes evidence_refs provenance".split(),
                      path + ".rpm.readiness." + axis, native=True)
        for name in ("model_id", "model_version", "model_digest"):
            _require(_canonical(bias["theta"][name]) == _canonical(state[name]), "BIAS_MODEL_MISMATCH", path + ".theta." + name)
        _require(type(bias["theta"]["parameter_artifacts"]) is list and bool(bias["theta"]["parameter_artifacts"]),
                 "PARAMETER_ARTIFACTS_REQUIRED", path + ".theta")
        for ref in bias["theta"]["parameter_artifacts"]:
            _reference(ref, artifacts, checks, path + ".theta.parameter_artifacts")
        ref = bias["memory"]["recurrent_state_ref"]
        if ref is not None:
            _reference(ref, artifacts, checks, path + ".memory.recurrent_state_ref")
        if bias["cjt_id"] == "C":
            _require(ref is not None, "C_RECURRENT_STATE_MISSING", path + ".memory")
            c_ref = ref
    traces = recovery["traces"]
    _require(type(traces) is list and bool(traces), "ORDERED_TRACES_REQUIRED", "recovery.traces")
    trace_map = {}
    previous = None
    for index, trace in enumerate(traces):
        path = "recovery.traces." + str(index)
        _required(trace, TRACE, path, native=True)
        _require(trace["contract_type"] == "TICK_TRACE" and trace["sealed"] is True, "SEALED_TRACE_REQUIRED", path)
        phases = trace["phases"]
        _require(type(phases) is list and all(type(p) is dict for p in phases)
                 and [p.get("phase") for p in phases] == PHASE_ORDER, "TRACE_PHASES_INCOMPLETE", path + ".phases")
        for phase in phases:
            _required(phase, "phase tick inputs outputs diagnostics compute_units".split(), path + ".phases", native=True)
        _require(type(trace["tick"]) is int and trace["tick"] >= 1
                 and (index == 0 or trace["tick"] == traces[index - 1]["tick"] + 1),
                 "TRACE_TICK_ORDER_MISMATCH", path)
        _require(trace["previous_trace_digest"] == previous, "TRACE_ORDER_LINK_MISMATCH", path)
        _require(type(trace["trace_id"]) is str and trace["trace_id"] not in trace_map,
                 "TRACE_ID_DUPLICATE_OR_INVALID", path)
        trace_map[trace["trace_id"]] = trace
        previous = trace["trace_digest"]
    last = traces[-1]
    _require(head["trace_digest"] == last["trace_digest"]
             and head["commit_receipt_id"] == last["commit_receipt_id"]
             and head["state_digest"] == last["post_state_digest"]
             and head["model_digest"] == last["post_model_digest"], "HEAD_TRACE_MISMATCH", "recovery.head")
    _require(type(witness["next_tick"]) is int and witness["next_tick"] == last["tick"] + 1,
             "NEXT_TICK_MISMATCH", "next_tick")
    transitions = witness["transitions"]
    _require(type(transitions) is list and len(transitions) == len(traces),
             "TRANSITION_COVERAGE_MISMATCH", "transitions")
    for index, transition in enumerate(transitions):
        path = "transitions." + str(index)
        _required(transition, TRANSITION, path)
        _require(_canonical(transition["trace"]) == _canonical(traces[index]),
                 "TRANSITION_TRACE_MISMATCH", path + ".trace")
        _require(type(transition["artifacts"]) is list, "TRANSITION_ARTIFACTS_REQUIRED", path + ".artifacts")
        for descriptor in transition["artifacts"]:
            _required(descriptor, ("artifact_id", "sha256"), path + ".artifacts")
            key = descriptor["artifact_id"]
            _require(key in checks and descriptor["sha256"] == checks[key]["sha256"],
                     "TRANSITION_ARTIFACT_EVIDENCE_MISSING", path + ".artifacts")
    # Coverage only: the unchanged native reconstruct_transition remains the
    # authority for the validity of transition evidence and dependencies.
    for section in ("recovery", "transitions", "published_effects", "model_version_record"):
        _all_references(witness[section], artifacts, checks, section)
    effects = _required(witness["published_effects"], ("B", "R"), "published_effects")
    receipts = witness["receipts"]
    _require(type(receipts) is dict, "RECEIPTS_REQUIRED", "receipts")
    for producer in ("B", "R"):
        path = "published_effects." + producer
        effect = _required(effects[producer], EFFECT, path, native=True)
        _require(effect["contract_type"] == "PUBLISHED_EFFECT" and effect["authoritative"] is True
                 and effect["producer_cjt_id"] == producer, "PUBLISHED_EFFECT_IDENTITY_MISMATCH", path)
        _declared(effect, "publication_digest", path)
        receipt_id = effect["commit_receipt_id"]
        _require(type(receipt_id) is str and receipt_id in receipts, "COMMIT_RECEIPT_MISSING", path)
        receipt = _required(receipts[receipt_id], RECEIPT, "receipts." + receipt_id, native=True)
        _declared(receipt, "receipt_digest", "receipts." + receipt_id)
        _require(receipt["receipt_id"] == receipt_id and receipt["disposition"] == "COMMITTED"
                 and receipt["authorized"] is True and receipt["atomic"] is True
                 and effect["published_effect_id"] in receipt["published_effect_ids"],
                 "EFFECT_RECEIPT_LINK_MISMATCH", path)
        trace = trace_map.get(receipt["trace_id"])
        _require(trace is not None and trace["commit_receipt_id"] == receipt_id
                 and effect["published_effect_id"] in trace["published_effect_ids"]
                 and producer in trace["cjt_ids"], "EFFECT_TRACE_LINK_MISMATCH", path)
        for name in ("tick", "pre_state_digest", "post_state_digest", "pre_model_digest", "post_model_digest"):
            _require(receipt[name] == trace[name], "RECEIPT_TRACE_LINK_MISMATCH", path + "." + name)
        _require(effect["tick"] == receipt["tick"] < witness["next_tick"], "EFFECT_TICK_MISMATCH", path)
        _reference(effect["content_ref"], artifacts, checks, path + ".content_ref")
        _require(effect["content_ref"]["shape"] == c_ref["shape"], "C_INPUT_STATE_SHAPE_MISMATCH", path)
    _require(effects["B"]["published_effect_id"] != effects["R"]["published_effect_id"],
             "B_R_EFFECTS_NOT_DISTINCT", "published_effects")
    model = _required(witness["model_version_record"],
                      "schema_version model_id model_version model_digest model_artifact_ref network config decoder_labels".split(),
                      "model_version_record")
    for name in ("model_id", "model_version", "model_digest", "model_artifact_ref"):
        _require(_canonical(model[name]) == _canonical(state[name]), "MODEL_MANIFEST_STATE_MISMATCH", "model_version_record." + name)
    external = _required(witness["external"], EXTERNAL, "external")
    for name in ("numeric_settings", "runtime_identity"):
        _require(type(external[name]) is dict and bool(external[name]), "EXTERNAL_IDENTITY_MISSING", "external." + name)
    for name in ("config", "network"):
        _require(_canonical(external[name]) == _canonical(model[name]) and bool(external[name]),
                 "EXTERNAL_MODEL_IDENTITY_MISMATCH", "external." + name)
    source = external["source_files_sha256"]
    _require(type(source) is dict and bool(source), "SOURCE_IDENTITIES_MISSING", "external.source_files_sha256")
    for name, value in source.items():
        _hex_digest(value, "external.source_files_sha256." + name)
    _require(type(external["decoder_manifests"]) is dict and set(external["decoder_manifests"]) == set(expected_cjt_ids)
             and all(type(v) is dict and v for v in external["decoder_manifests"].values()),
             "DECODER_COVERAGE_MISMATCH", "external.decoder_manifests")
    _require(type(external["operation_contracts"]) is dict and bool(external["operation_contracts"]),
             "OPERATION_CONTRACTS_MISSING", "external.operation_contracts")
    _required(external["route_settings"], ROUTE, "external.route_settings")
    _require(external["expected_symbol"] == "L2", "C_EXPECTATION_MISMATCH", "external.expected_symbol")
    _require(type(external["goal_context"]) is dict and bool(external["goal_context"]),
             "GOAL_CONTEXT_MISSING", "external.goal_context")
    _require(type(external["permissions"]) in (list, dict) and bool(external["permissions"]),
             "PERMISSIONS_MISSING", "external.permissions")
    limits = external["available_limits"]
    _require(type(limits) is dict and bool(limits) and all(type(v) is int and v >= 0 for v in limits.values()),
             "AVAILABLE_LIMITS_REQUIRED", "external.available_limits")
    owner = _required(witness["ownership"], ("mode", "active_outer_executor", "suspended_outer_call", "outer_frames"), "ownership")
    _require(owner["mode"] == "DIRECT_NATIVE" and owner["active_outer_executor"] is None
             and owner["suspended_outer_call"] is False and owner["outer_frames"] == [],
             "ACTIVE_OR_UNSUPPORTED_OUTER_CALLER", "ownership")
    return {"trace_count": len(traces), "cjt_ids": ids, "next_tick": witness["next_tick"],
            "artifact_checks": checks, "ownership_status": "EXPLICIT_CALLER_ASSERTION_ONLY"}


def validate_before_state_pair(left, right, *, expected_cjt_ids=("A", "B", "C", "R")):
    """Return typed recorded-evidence checks; never mutates inputs or performs IO.

    Native dataclass tuples must first be serialized as JSON arrays. Every native
    field is retained and compared. A successful result is not native verification.
    """
    reasons, digests, details = [], {}, {}
    if tuple(expected_cjt_ids) != ("A", "B", "C", "R"):
        reasons.append({"arm": "pair", "code": "FIXED_FOUR_CJT_SCOPE_REQUIRED", "path": "expected_cjt_ids"})
    for arm, witness in (("left", left), ("right", right)):
        try:
            digests[arm] = _digest(witness)
            details[arm] = _one(witness, expected_cjt_ids)
        except _Refused as error:
            reasons.append({"arm": arm, "code": error.code, "path": error.path})
        except (TypeError, ValueError, KeyError, IndexError) as error:
            reasons.append({"arm": arm, "code": "MALFORMED_WITNESS", "path": type(error).__name__})
    if set(digests) == {"left", "right"}:
        for field in WRAPPER:
            if type(left) is dict and type(right) is dict and field in left and field in right:
                if _canonical(left[field]) != _canonical(right[field]):
                    reasons.append({"arm": "pair", "code": "BEFORE_STATE_MISMATCH", "path": field})
    return {"schema": SCHEMA, "ok": not reasons,
            "status": "RECORDED_BEFORE_STATE_CONSISTENT" if not reasons else "BEFORE_STATE_REFUSED",
            "reasons": reasons, "witness_sha256": digests, "details": details,
            "native_verified": False, "outer_ownership_verified": False, "boundary": BOUNDARY}
