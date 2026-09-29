"""Pure-Python cases for the configuration/readout bridge (no torch, no model). Written, NOT RUN locally.

Acceptance rows exercised: HH01 (contract pin, reuse manifest), HH02 (probe compatibility vs validity),
HH04 (coverage), HH05 (coordinate meaning, no hidden-unit relabeling), HH07 (Harness detector reused
unchanged, readout calibration labeled), HH08 (no confirmation fitting, freeze), HH09 (canonical CAS names,
no EXACT mapping), HH16 (record digest and tamper detection), HH20 (claim levels).
"""
import json

import pytest

from . import diagnostic_configuration as dc
from .harness_capture_vendor import probe_runner as harness

CKPT = "a" * 64
SRC = dc.LEARNER_SHA256
INPUT_A = "1" * 64
INPUT_B = "2" * 64


def _capture(site="graph.round_input", *, round_index=0, rows=3, width=8, values=None, input_sha256=INPUT_A,
             call_index=0, meaning=None):
    if values is None:
        values = [((r * width + c) % 7 - 3) * 0.5 for r in range(rows) for c in range(width)]
    return dc.raw_capture(checkpoint_sha256=CKPT, input_sha256=input_sha256, source_sha256=SRC, site=site,
                          call_index=call_index, round_index=round_index, shape=(rows, width), dtype="float32",
                          device="cuda:0",
                          coordinate_meaning=dc.SITE_SEMANTICS[site]["coordinate_meaning"] if meaning is None else meaning,
                          signed_values=values)


def _refused(code, function, *args, **kwargs):
    with pytest.raises(dc.ConfigurationRefused) as info:
        function(*args, **kwargs)
    assert info.value.code == code, (info.value.code, code)


def test_hh01_contract_file_matches_module_constants_and_vendored_harness_hash():
    contract = dc.load_contract()
    pinned = dc.check_contract(contract)
    assert pinned["sites"] == 14 and tuple(contract["sites"]) == dc.SITES
    import hashlib
    vendored = dc.CONTRACT_PATH.parent.parent / "harness_capture_vendor" / "probe_runner.py"
    assert hashlib.sha256(vendored.read_bytes()).hexdigest() == dc.HARNESS_VENDOR_SHA256
    drifted = dict(contract)
    drifted["sites"] = list(contract["sites"])[:-1]
    _refused("CONTRACT_SITES", dc.check_contract, drifted)


def test_hh01_reuse_manifest_classifies_every_vendored_name_and_pins_both_parents():
    manifest = dc.reuse_manifest()
    for name in ("CaptureState", "_top_k_neurons", "_softmax_margin", "EraserIntervention", "capture_probes"):
        assert hasattr(harness, name)
        assert manifest["reuse"][name]["relationship"] in dc.REUSE_RELATIONSHIPS
    assert manifest["reuse"]["_top_k_neurons"]["relationship"] == "EXACT_SHARED_IMPLEMENTATION"
    assert manifest["reuse"]["_softmax_margin"]["relationship"] == "VERSIONED_ADAPTATION"
    assert manifest["helm"]["learner_sha256"] == dc.LEARNER_SHA256
    assert manifest["cas_parent"]["noetics"]["^6"] == "Male" and manifest["cas_parent"]["noetics"]["^9"] == "Below/Effect"
    assert all(not row["hidden_unit"] for row in manifest["sites"].values())
    assert manifest["authority"] == "OBSERVATION_ONLY_NO_PROMOTION" and manifest["capture_default"] == "OFF"


def test_hh04_missing_hook_is_incomplete_coverage_and_overcount_is_refused():
    assert dc.coverage(8, 8, 8).complete
    missing = dc.coverage(8, 7, 7)
    assert not missing.complete and missing.observed_calls == 7
    assert not dc.coverage(8, 8, 8, errors=("hook raised",)).complete
    assert not dc.coverage(8, 8, 7).complete
    _refused("COVERAGE_OVERCOUNT", dc.coverage, 8, 9, 9)
    _refused("COVERAGE_INCOMPLETE", dc.require_complete, missing, "readout")


def test_hh05_capture_refuses_relabeled_coordinate_meaning_nonfinite_values_and_wrong_counts():
    capture = _capture()
    assert capture.basis == "NODE_ROW_BLOCK_INPUT" and capture.rows == 3 and capture.width == 8
    _refused("COORDINATE_MEANING_MISMATCH", _capture, meaning="hidden MLP neuron index")
    _refused("CAPTURE_NONFINITE", _capture, values=[float("nan")] * 24)
    _refused("CAPTURE_VALUE_COUNT", _capture, values=[0.0] * 23)
    _refused("CAPTURE_ROUND_INDEX", _capture, round_index=dc.CORE_ROUNDS)
    _refused("CAPTURE_ROUND_INDEX", _capture, site="head.reach", round_index=0)
    _refused("SITE_NOT_TENSOR", _capture, site="answer.assembly", round_index=None)
    # explicit meaning: the helper must not look the unknown site up itself; the refusal has to come from raw_capture
    _refused("SITE_UNKNOWN", _capture, site="mlp.layer3", meaning="unknown site meaning")


def test_hh07_top_k_detector_is_the_vendored_harness_function_with_relabeled_output():
    captures = [_capture(round_index=r) for r in range(3)]
    record = dc.detect_top_k(captures, row=1, k=4, split="DISCOVERY", family="F-fixture")
    state = harness.CaptureState()
    for capture in captures:
        state.mlp_post[capture.round_index] = list(dc.row_values(capture, 1))
    expected = harness._top_k_neurons(state, 4)
    assert record.coordinates == tuple((e["layer"], e["index"]) for e in expected)
    assert record.signed_values == tuple(e["activation"] for e in expected)
    assert any(v < 0 for v in record.signed_values), "inhibition must survive abs-ranking"
    assert record.kind == "PROJECTED_COORDINATE_SET" and record.hidden_unit is False
    assert record.detector["harness_function"] == "_top_k_neurons"
    assert record.claim_level == "OBSERVED_CONFIGURATION" and record.cas_definition["mapping_class"] == "UNKNOWN"
    assert record.configuration_id.startswith("helm-configuration-")


def test_hh05_actual_unit_kind_is_refused_for_every_contract_site():
    capture = _capture()
    for site in dc.TENSOR_SITES:
        assert dc.SITE_SEMANTICS[site]["hidden_unit"] is False
    _refused("CONFIGURATION_NOT_HIDDEN_UNIT", dc.build_configuration, captures=[capture], row=0,
             coordinates=[(0, 1)], signed_values=[0.5], split="DISCOVERY", family="F",
             detector={"name": "x", "version": "1", "harness_function": "_top_k_neurons",
                       "relationship": "EXACT_SHARED_IMPLEMENTATION"}, kind="ACTUAL_UNIT_SET")


def test_hh08_configuration_cannot_be_named_on_confirmation_and_unfrozen_cannot_be_used_there():
    capture = _capture()
    _refused("CONFIGURATION_FIT_ON_CONFIRMATION", dc.detect_top_k, [capture], row=0, k=2, split="CONFIRMATION",
             family="F")
    record = dc.detect_top_k([capture], row=0, k=2, split="DISCOVERY", family="F")
    _refused("CONFIGURATION_NOT_FROZEN", dc.require_frozen, record, "CONFIRMATION")
    frozen = dc.freeze_configuration(record)
    assert dc.require_frozen(frozen, "CONFIRMATION") is frozen
    _refused("CONFIGURATION_ALREADY_FROZEN", dc.freeze_configuration, frozen)
    from dataclasses import replace
    moved = replace(frozen, coordinates=((0, 7),) + frozen.coordinates[1:])
    _refused("CONFIGURATION_NOT_FROZEN", dc.require_frozen, moved, "CONFIRMATION")


def test_support_keeps_signed_coactivation_and_inhibition_per_coordinate():
    base = _capture(round_index=0)
    record = dc.detect_top_k([base], row=2, k=3, split="DISCOVERY", family="F")
    flipped = _capture(round_index=0, input_sha256=INPUT_B, values=[-v for v in base.signed_values])
    response = dc.support(record, [base, flipped])
    assert response["support"] == 2 and response["inputs"] == (INPUT_A, INPUT_B)
    for row in response["per_coordinate"]:
        assert row["positive"] + row["negative"] + row["zero"] == 2
        assert abs(row["mean_signed"]) < 1e-12 and row["stdev"] is not None
    _refused("SUPPORT_ROUND_MISSING", dc.support, record, [_capture(round_index=1, input_sha256=INPUT_B)])


def test_hh09_cas_mapping_uses_canonical_names_only_and_is_never_exact():
    mapping = dc.cas_mapping("^3", "E", "f", "PROPOSED")
    assert mapping["name"] == "Negative" and mapping["domain"] == "E" and mapping["register"] == "f"
    assert dc.cas_mapping() == {"noetic": None, "name": None, "domain": None, "register": None, "mapping_class": "UNKNOWN"}
    _refused("CAS_MAPPING_EXACT_UNSUPPORTED", dc.cas_mapping, "^3", mapping_class="EXACT")
    _refused("CAS_NOETIC_NONCANONICAL", dc.cas_mapping, "Aversion", mapping_class="PROPOSED")
    _refused("CAS_NOETIC_NONCANONICAL", dc.cas_mapping, "^10", mapping_class="PROPOSED")
    _refused("CAS_DOMAIN", dc.cas_mapping, "^3", "X", None, "PROPOSED")
    _refused("CAS_MAPPING_CLASS", dc.cas_mapping, "^3", mapping_class="UNKNOWN")
    _refused("CAS_MAPPING_UNLABELED", dc.cas_mapping, None, "P", None, "UNKNOWN")
    capture = _capture()
    _refused("CAS_MAPPING_PREMATURE", dc.build_configuration, captures=[capture], row=0, coordinates=[(0, 0)],
             signed_values=[1.0], split="DISCOVERY", family="F", kind="PROJECTED_COORDINATE_SET",
             detector={"name": "x", "version": "1", "harness_function": "_top_k_neurons",
                       "relationship": "EXACT_SHARED_IMPLEMENTATION"},
             cas_definition=dc.cas_mapping("^3", mapping_class="ADAPTED"))


def _anchored_record(site="graph.round_input", row=0, k=2, kind="parts"):
    receipt = _emitted_receipt(kind=kind)
    return dc.detect_from_observation(receipt, site=site, row=row, k=k, split="DISCOVERY", family="F-emitted",
                                      retained_receipt_sha256=receipt["receipt_sha256"])


def test_hh20_claim_levels_are_monotone_evidenced_and_capped_at_the_pilot_ceiling():
    fixture_record = dc.freeze_configuration(dc.detect_top_k([_capture()], row=0, k=2, split="DISCOVERY", family="F"))
    evidence = {"controls": ["shuffled_labels", "input_only"], "artifact": "x.json", "artifact_sha256": "b" * 64}
    assert fixture_record.provenance["anchor"] == "NONE_FIXTURE_CAPTURES"
    _refused("CLAIM_PROVENANCE", dc.assign_claim, fixture_record, "STIMULUS_SELECTIVE", evidence)
    record = dc.freeze_configuration(_anchored_record())
    assert record.provenance["receipt_complete"] is True and record.provenance["anchor"] == "EXTERNAL_ANCHOR_VERIFIED"
    selective = dc.assign_claim(record, "STIMULUS_SELECTIVE", evidence)
    assert selective.claim_level == "STIMULUS_SELECTIVE" and len(selective.evidence) == 1
    _refused("CLAIM_EVIDENCE", dc.assign_claim, record, "STIMULUS_SELECTIVE", {"controls": [], "artifact": "x"})
    _refused("CLAIM_LEVEL_DOWNGRADE", dc.assign_claim, selective, "OBSERVED_CONFIGURATION", evidence)
    _refused("CLAIM_LEVEL_OUTSIDE_PILOT", dc.assign_claim, selective, "TARGETED_REPAIR_GAIN_SUPPORTED", evidence)
    _refused("CLAIM_EVIDENCE", dc.assign_claim, selective, "TASK_CAUSAL_CONTRIBUTION_SUPPORTED", evidence)
    causal = dc.assign_claim(selective, "TASK_CAUSAL_CONTRIBUTION_SUPPORTED",
                             dict(evidence, intervention_receipt_sha256="c" * 64,
                                  matched_control_receipt_sha256="d" * 64, task_metric="PARTS_REACH_SCORES"))
    assert causal.claim_level == "TASK_CAUSAL_CONTRIBUTION_SUPPORTED"
    _refused("CLAIM_EVIDENCE", dc.assign_claim, selective, "TASK_CAUSAL_CONTRIBUTION_SUPPORTED",
             dict(evidence, intervention_receipt_sha256="c" * 64, matched_control_receipt_sha256="d" * 64,
                  task_metric="PROBE_ACCURACY"))
    unfrozen = _anchored_record()
    _refused("CONFIGURATION_NOT_FROZEN", dc.assign_claim, unfrozen, "STIMULUS_SELECTIVE", evidence)


def test_hh09_proposed_label_becomes_adapted_only_through_readout_evidence():
    receipt = _emitted_receipt(kind="parts")
    anchor = receipt["receipt_sha256"]
    captures, cov = dc.captures_from_observation(receipt, "graph.round_input", retained_receipt_sha256=anchor)
    provenance = {"receipt_sha256": anchor, "receipt_complete": True, "anchor": "EXTERNAL_ANCHOR_VERIFIED", "coverage": None}
    _refused("CONFIGURATION_PROVENANCE", dc.build_configuration, captures=captures, row=0, coordinates=[(0, 0)],
             signed_values=[1.0], split="DISCOVERY", family="F", kind="PROJECTED_COORDINATE_SET",
             detector={"name": "x", "version": "1", "harness_function": "_top_k_neurons",
                       "relationship": "EXACT_SHARED_IMPLEMENTATION"},
             provenance=dict(provenance, receipt_complete=False))
    record = dc.build_configuration(captures=captures, row=0, coordinates=[(0, 0), (0, 1)], signed_values=[1.0, -1.0],
                                    split="DISCOVERY", family="F", kind="PROJECTED_COORDINATE_SET",
                                    detector={"name": "x", "version": "1", "harness_function": "_top_k_neurons",
                                              "relationship": "EXACT_SHARED_IMPLEMENTATION"},
                                    cas_definition=dc.cas_mapping("^4", "C", None, "PROPOSED"), provenance=provenance)
    frozen = dc.freeze_configuration(record)
    evidence = {"controls": ["shuffled_labels", "capacity_matched_generic"], "artifact": "r.json",
                "artifact_sha256": "e" * 64}
    supported = dc.assign_claim(dc.assign_claim(frozen, "STIMULUS_SELECTIVE", evidence), "CAS_READOUT_SUPPORTED", evidence)
    assert supported.cas_definition["mapping_class"] == "ADAPTED" and supported.cas_definition["name"] == "Vibration"
    assert frozen.cas_definition["mapping_class"] == "PROPOSED"


def test_hh16_configuration_json_round_trips_only_with_the_retained_anchor_and_detects_tampering():
    import hashlib as _hashlib
    record = dc.freeze_configuration(dc.detect_top_k([_capture(round_index=r) for r in range(2)], row=1, k=3,
                                                     split="DISCOVERY", family="F"))
    text = dc.configuration_to_json(record)
    anchor = _hashlib.sha256(text.encode()).hexdigest()
    _refused("EXTERNAL_ANCHOR_REQUIRED", dc.configuration_from_json, text, retained_record_sha256=None)
    assert dc.configuration_from_json(text, retained_record_sha256=anchor) == record
    _refused("CONFIGURATION_ANCHOR_MISMATCH", dc.configuration_from_json, text, retained_record_sha256="0" * 64)
    body = json.loads(text)
    body["signed_values"][0] = body["signed_values"][0] + 1.0
    edited = json.dumps(body)
    _refused("CONFIGURATION_RECORD_TAMPERED", dc.configuration_from_json, edited,
             retained_record_sha256=_hashlib.sha256(edited.encode()).hexdigest())
    body = json.loads(text)
    body["coordinates"][0] = [0, 0]
    body["record_digest"] = dc.digest({k: v for k, v in body.items() if k != "record_digest"})
    resealed = json.dumps(body)
    # an editor who recomputes the carried digest still fails: the freeze digest and the outside anchor both differ
    _refused("CONFIGURATION_RECORD_TAMPERED", dc.configuration_from_json, resealed,
             retained_record_sha256=_hashlib.sha256(resealed.encode()).hexdigest())
    _refused("CONFIGURATION_ANCHOR_MISMATCH", dc.configuration_from_json, resealed, retained_record_sha256=anchor)


def test_hh02_pythia_probe_is_mechanically_compatible_but_never_valid_without_helm_calibration():
    probe = dc.ProbeIdentity("blindspot_covers", "e8537e6c", "PYTHIA_160M", 8, "PYTHIA_DISCOVERY", "f" * 64)
    mechanical = dc.probe_compatibility(probe, "graph.round_input", 8)
    assert mechanical["mechanical"] is True and mechanical["valid_on_helm"] is False
    _refused("PROBE_WIDTH_MISMATCH", dc.probe_compatibility, probe, "graph.round_input", 64)
    _refused("PROBE_VALIDITY_UNESTABLISHED", dc.probe_validity, probe, None)
    _refused("PROBE_SUBSTRATE_TRANSFER_UNVALIDATED", dc.probe_validity, probe,
             {"substrate": "PYTHIA_160M", "source_sha256": SRC, "split": "DISCOVERY"})
    _refused("PROBE_FIT_SPLIT", dc.probe_validity, probe,
             {"substrate": "HELM", "source_sha256": SRC, "split": "CONFIRMATION"})
    valid = dc.probe_validity(probe, {"substrate": "HELM", "source_sha256": SRC, "split": "DISCOVERY",
                                      "checkpoint_sha256": CKPT, "cases": 12, "coefficients_sha256": "f" * 64,
                                      "controls": ["shuffled_labels"]})
    assert valid["valid_on_helm"] is True and valid["cases"] == 12


def test_hh07_readout_margin_reuses_harness_formula_and_labels_pythia_calibration():
    readout = dc.readout_margin([2.0, -1.0], "head.reach")
    assert readout["raw_margin"] == 3.0 and readout["normalised"] == harness._softmax_margin([2.0, -1.0])
    assert readout["calibration"] == "PYTHIA_160M_EMPIRICAL_NOT_HELM_CALIBRATED"
    assert readout["claim"] == "READOUT_LEVEL_ONLY_NOT_TASK_CAUSAL"
    _refused("READOUT_SITE", dc.readout_margin, [1.0, 2.0], "graph.round_input")
    _refused("READOUT_OPTIONS", dc.readout_margin, [1.0], "head.reach")
    _refused("READOUT_NONFINITE", dc.readout_margin, [1.0, float("inf")], "head.node_pointer")


def test_site_table_names_parts_and_reach_paths_without_world_head():
    assert dc.SITE_SEMANTICS["head.node"]["answer_path"] == "PARTS"
    assert dc.SITE_SEMANTICS["head.reach"]["answer_path"] == "REACH"
    assert dc.SITE_SEMANTICS["head.node_pointer"]["answer_path"] == "REACH"
    assert not any("world_head" in row["tensor"] for row in dc.SITE_SEMANTICS.values())
    assert all(row["anchor"].startswith("pointer_learner.py:") for row in dc.SITE_SEMANTICS.values())


def test_witness_protocol_is_source_bound_and_inside_the_pilot_envelope():
    from . import diagnostic_intervention as di
    protocol = di.witness_protocol()
    resources = protocol["resources"]
    assert resources["packet_forwards_max"] <= resources["packet_forwards_envelope"]
    assert resources["conditions"] == len(protocol["conditions"]) <= resources["conditions_max"]
    assert len(protocol["hypotheses"]) <= resources["hypotheses_max"] and resources["helm_optimizer_updates"] == 0
    assert resources["claude_launches"] == 0 and protocol["checkpoint"]["count"] == 1
    assert protocol["source"]["learner_sha256"] == dc.LEARNER_SHA256
    assert protocol["source"]["site_module"] == ("core_block", "pre")
    injected = [h for h in protocol["hypotheses"] if h["kind"] == "INJECTED_FAULT_PLUMBING_CHECK"]
    assert len(injected) == 1 and injected[0]["not_evidence_of"] == "any natural HELM fault"
    assert [c["id"] for c in protocol["conditions"] if c.get("label") == "INJECTED"] == ["C5"]
    assert all(c["action"] in di.ACTIONS or c["action"] == "BASELINE_UNINSTRUMENTED" for c in protocol["conditions"])
    assert protocol["expected_calls_per_forward"]["core_block"] == dc.CORE_ROUNDS


def _finalized_receipt(declaration, di, status_hits):
    receipt = di.Receipt(di.RECEIPT_SCHEMA, di.declaration_digest(declaration), declaration.action, declaration.operation,
                         declaration.site, declaration.module_attribute, declaration.hook_kind, 1, 1, 1)
    receipt.hits.extend(status_hits)
    receipt.hooks_removed, receipt.parameters_unchanged = True, True
    receipt.model_binding, receipt.restored_by = "CALLER_VERIFIED", "test-double-loader"
    return di.finalize(receipt)


def test_hh17_evidence_record_binds_branch_to_input_checkpoint_action_outcome_and_rpa_view_cannot_execute():
    from . import diagnostic_intervention as di
    declaration = di.declare(action="SUPPRESS", site="head.reach", checkpoint_sha256=CKPT, input_sha256=INPUT_A,
                             source_sha256=SRC, rows=(0,), coordinates=(1,), gain=1.0, hypothesis_id="H1",
                             predicted_change="reach margin falls")
    hit = {"call_index": 0, "round_index": None, "shape": [2], "dtype": "float32", "device": "cuda:0", "targeted": True,
           "changed_count": 1, "untargeted_unchanged": True, "max_abs_delta": 0.7, "delta_norm": 0.7,
           "target_norm_before": 0.7, "before": [0.7], "after": [0.0]}
    receipt = _finalized_receipt(declaration, di, [hit])
    assert receipt.status == "APPLIED"
    outcome = {"metric": "CHECKED_ANSWER", "evaluator": "UNCHANGED_INDEPENDENT_EVALUATOR", "baseline_correct": True,
               "changed_correct": False}
    evidence = di.evidence_record(declaration=declaration, receipt=receipt, configuration_id="helm-configuration-" + "c" * 64,
                                  split="CONFIRMATION", baseline_prediction_id="typed-prediction-" + "1" * 64,
                                  changed_prediction_id="typed-prediction-" + "2" * 64, checked_outcome=outcome)
    assert evidence["harvest_ingestion"] == "DISABLED_NOT_ADMITTED" and evidence["native_decision"] is False
    assert evidence["model_binding"] == "CALLER_VERIFIED" and evidence["restored_by"] == "test-double-loader"
    unbound = _finalized_receipt(declaration, di, [hit])
    unbound.model_binding, unbound.restored_by = "UNVERIFIED_SELF_REPORTED", None
    with pytest.raises(di.InterventionRefused) as info:
        di.evidence_record(declaration=declaration, receipt=unbound, configuration_id="helm-configuration-" + "c" * 64,
                           split="CONFIRMATION", baseline_prediction_id="p", changed_prediction_id="q", checked_outcome=outcome)
    assert info.value.code == "MODEL_BINDING_UNVERIFIED"
    with pytest.raises(di.InterventionRefused) as info:
        di.require_applied(unbound)
    assert info.value.code == "MODEL_BINDING_UNVERIFIED"
    assert evidence["promotion"] == "NOT_POSSIBLE_FROM_THIS_RECORD" and evidence["selected_by"] == di.ACTOR
    with pytest.raises(di.InterventionRefused) as info:
        di.rpa_projection(evidence, retained_evidence_sha256=None)
    assert info.value.code == "EXTERNAL_ANCHOR_REQUIRED"
    view = di.rpa_projection(evidence, retained_evidence_sha256=evidence["evidence_digest"])
    assert view["executable"] is False and view["mutation_authority"] is None and view["anchor"] == "EXTERNAL_ANCHOR_VERIFIED"
    assert view["parent_checkpoint_sha256"] == CKPT and view["input_sha256"] == INPUT_A and view["action"] == "SUPPRESS"
    assert view["outcome"]["checked_outcome"] == outcome and view["lineage"]["evidence_digest"] == evidence["evidence_digest"]
    assert view["branch_id"].startswith("helm-branch-")
    tampered = dict(evidence)
    tampered["applied"] = False
    with pytest.raises(di.InterventionRefused) as info:
        di.rpa_projection(tampered, retained_evidence_sha256=evidence["evidence_digest"])
    assert info.value.code == "EVIDENCE_TAMPERED"
    # DeepSeek F4: an editor who recomputes the carried digest passes the self-check; only the outside anchor catches it
    recomputed = {k: v for k, v in tampered.items() if k != "evidence_digest"}
    recomputed["evidence_digest"] = dc.digest(recomputed)
    with pytest.raises(di.InterventionRefused) as info:
        di.verify_evidence(recomputed, retained_evidence_sha256=None)
    assert info.value.code == "EXTERNAL_ANCHOR_REQUIRED"
    with pytest.raises(di.InterventionRefused) as info:
        di.rpa_projection(recomputed, retained_evidence_sha256=evidence["evidence_digest"])
    assert info.value.code == "EVIDENCE_ANCHOR_MISMATCH"
    with pytest.raises(di.InterventionRefused) as info:
        di.evidence_record(declaration=declaration, receipt=receipt, configuration_id="helm-configuration-" + "c" * 64,
                           split="CONFIRMATION", baseline_prediction_id="typed-prediction-" + "1" * 64,
                           changed_prediction_id=None, checked_outcome=outcome)
    assert info.value.code == "EVIDENCE_PREDICTION"
    with pytest.raises(di.InterventionRefused) as info:
        di.evidence_record(declaration=declaration, receipt=receipt, configuration_id="helm-configuration-" + "c" * 64,
                           split="CONFIRMATION", baseline_prediction_id="p", changed_prediction_id="q",
                           checked_outcome={"metric": "CHECKED_ANSWER", "evaluator": "CANDIDATE_SELF_REPORT"})
    assert info.value.code == "EVIDENCE_OUTCOME"


def test_hh17_unfinalized_receipt_and_not_applied_branches_are_recorded_honestly():
    from . import diagnostic_intervention as di
    declaration = di.declare(action="NO_OP_CONTROL", site="head.node", checkpoint_sha256=CKPT, input_sha256=INPUT_A,
                             source_sha256=SRC, rows=(0,), coordinates=(0,), hypothesis_id="H1", predicted_change="none")
    raw = di.Receipt(di.RECEIPT_SCHEMA, di.declaration_digest(declaration), declaration.action, declaration.operation,
                     declaration.site, declaration.module_attribute, declaration.hook_kind, 1, 1, 1)
    with pytest.raises(di.InterventionRefused) as info:
        di.evidence_record(declaration=declaration, receipt=raw, configuration_id="helm-configuration-" + "c" * 64,
                           split="DISCOVERY", baseline_prediction_id="p", changed_prediction_id="p",
                           checked_outcome={"metric": "NONE"})
    assert info.value.code == "EVIDENCE_RECEIPT_UNFINALIZED"
    failed = _finalized_receipt(declaration, di, [])
    assert failed.status == "NO_OP_FAILED"
    evidence = di.evidence_record(declaration=declaration, receipt=failed, configuration_id="helm-configuration-" + "c" * 64,
                                  split="DISCOVERY", baseline_prediction_id="p", changed_prediction_id=None,
                                  checked_outcome={"metric": "NONE"})
    assert evidence["receipt_status"] == "NO_OP_FAILED" and evidence["applied"] is False
    view = di.rpa_projection(evidence, retained_evidence_sha256=evidence["evidence_digest"])
    assert view["outcome"]["receipt_status"] == "NO_OP_FAILED"


# ---------------------------------------------------------------------------------------------------------
# Binding to Codex's actual emitter (`observation.py` at fd421572)
# ---------------------------------------------------------------------------------------------------------

class _StubTensor:
    """Duck-typed stand-in for the emitter's tensor protocol (detach/shape/numel/reshape/cpu/tolist); no torch."""

    def __init__(self, shape, values):
        self.shape, self._values = list(shape), list(values)
        self.dtype, self.device = "torch.float32", "cuda:0"

    def numel(self):
        return len(self._values)

    def detach(self):
        return self

    def reshape(self, *_):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return list(self._values)


def _emitted_receipt(*, kind="parts", skip_site=None, nodes=3, width=64, checkpoint_sha256=CKPT, input_sha256=INPUT_A):
    from . import observation
    cap = observation.Capture(checkpoint_sha256=checkpoint_sha256, input_sha256=input_sha256, kind=kind,
                              rounds=dc.CORE_ROUNDS, mode="OBSERVE_ONLY")

    def emit(site, value, round_index=None):
        if site != skip_site:
            cap.emit(site, value, round_index)

    def block(seed):
        return _StubTensor((nodes, width), [((seed * 7 + i) % 11 - 5) * 0.25 for i in range(nodes * width)])
    emit("input.mapping", {"record_id": "r", "query": {"kind_name": kind}})
    emit("graph.initial_state", block(1))
    for r in range(dc.CORE_ROUNDS):
        emit("graph.round_input", block(10 + r), r)
        emit("graph.round_update", block(20 + r), r)
        emit("graph.round_state", block(30 + r), r)
    emit("graph.node_state", block(2))
    emit("graph.query_state", _StubTensor((width,), [0.5] * width))
    emit("graph.pointer_query", _StubTensor((width,), [-0.5] * width))
    emit("head.node", _StubTensor((nodes, 2), [1.0, -1.0] * nodes))
    if kind == "reach":
        emit("head.reach", _StubTensor((2,), [0.3, -0.3]))
        emit("head.node_pointer", _StubTensor((nodes,), [0.1, 0.2, 0.3]))
    emit("answer.scores", {"s": [0.0, 1.0]})
    emit("answer.decisions", {"s": "A"})
    emit("answer.assembly", {"answer": "A"})
    cap.closed = cap.cleanup_complete = True
    return cap.receipt()


def test_hh01_emitter_constants_are_the_codex_observation_module_values():
    from . import observation
    assert observation.MEANINGS == dc.EMITTER_MEANINGS
    assert observation.MODES == dc.OBSERVATION_MODES
    for kind in dc.OBSERVATION_KINDS:
        cap = observation.Capture(checkpoint_sha256=CKPT, input_sha256=INPUT_A, kind=kind, rounds=dc.CORE_ROUNDS)
        assert {s: cap.expected[s] for s in dc.SITES} == {s: dc.expected_hits_for(s, kind) for s in dc.SITES}
    sample = {"z": [1.5, -2, None], "a": {"b": "c"}}
    assert dc._emitter_canonical(sample) == observation.canonical(sample)
    assert observation.LEARNER_SHA256 == dc.LEARNER_SHA256 and observation.SCIENTIFIC_SOURCE == dc.SCIENTIFIC_SOURCE
    _refused("OBSERVATION_KIND", dc.expected_hits_for, "head.reach", "world")


def test_hh04_complete_emitter_receipt_binds_to_captures_and_detection_matches_direct_top_k():
    receipt = _emitted_receipt(kind="parts")
    assert receipt["complete"] is True and receipt["status"] == "CAPTURED"
    anchor = receipt["receipt_sha256"]
    _refused("EXTERNAL_ANCHOR_REQUIRED", dc.captures_from_observation, receipt, "graph.round_input", retained_receipt_sha256=None)
    captures, cov = dc.captures_from_observation(receipt, "graph.round_input", retained_receipt_sha256=anchor)
    assert cov.complete and cov.expected_calls == cov.observed_calls == cov.stored_calls == dc.CORE_ROUNDS
    assert [c.round_index for c in captures] == list(range(dc.CORE_ROUNDS))
    assert captures[0].dtype == "float32" and captures[0].shape == (3, 64) and captures[0].basis == "NODE_ROW_BLOCK_INPUT"
    assert captures[0].coordinate_meaning == dc.EMITTER_MEANINGS["graph.round_input"]
    record = dc.detect_from_observation(receipt, site="graph.round_input", row=1, k=4, split="DISCOVERY", family="F-emitted",
                                        retained_receipt_sha256=anchor)
    direct = dc.detect_top_k(captures, row=1, k=4, split="DISCOVERY", family="F-emitted")
    assert (record.coordinates, record.signed_values) == (direct.coordinates, direct.signed_values)
    assert record.provenance == {"receipt_sha256": anchor, "receipt_complete": True, "anchor": "EXTERNAL_ANCHOR_VERIFIED",
                                 "coverage": {"expected_calls": 8, "observed_calls": 8, "stored_calls": 8, "errors": [], "complete": True}}
    assert direct.provenance["anchor"] == "NONE_FIXTURE_CAPTURES"
    assert record.kind == "PROJECTED_COORDINATE_SET" and record.checkpoint_sha256 == CKPT
    heads, head_cov = dc.captures_from_observation(receipt, "head.node", retained_receipt_sha256=anchor)
    assert head_cov.complete and heads[0].shape == (3, 2) and heads[0].round_index is None
    reach, reach_cov = dc.captures_from_observation(receipt, "head.reach", retained_receipt_sha256=anchor)
    assert reach == () and reach_cov.expected_calls == 0 and reach_cov.complete
    _refused("SITE_NOT_TENSOR", dc.captures_from_observation, receipt, "answer.assembly", retained_receipt_sha256=anchor)
    verified = dc.verify_observation(receipt, retained_receipt_sha256=anchor)
    assert verified["anchor"] == "EXTERNAL_ANCHOR_VERIFIED"
    _refused("EXTERNAL_ANCHOR_REQUIRED", dc.verify_observation, receipt, retained_receipt_sha256=None)


def test_hh04_incomplete_emitter_receipt_yields_captures_but_names_no_configuration():
    receipt = _emitted_receipt(kind="parts", skip_site="graph.round_state")
    assert receipt["complete"] is False and receipt["status"] == "INCOMPLETE"
    anchor = receipt["receipt_sha256"]
    captures, cov = dc.captures_from_observation(receipt, "graph.round_input", retained_receipt_sha256=anchor)
    assert len(captures) == dc.CORE_ROUNDS and not cov.complete and "RECEIPT_INCOMPLETE" in cov.errors
    _refused("COVERAGE_INCOMPLETE", dc.detect_from_observation, receipt, site="graph.round_input", row=0, k=2,
             split="DISCOVERY", family="F", retained_receipt_sha256=anchor)
    missing, missing_cov = dc.captures_from_observation(receipt, "graph.round_state", retained_receipt_sha256=anchor)
    assert missing == () and missing_cov.observed_calls == 0 and missing_cov.expected_calls == dc.CORE_ROUNDS
    off = _emitted_receipt(kind="reach")
    reach, reach_cov = dc.captures_from_observation(off, "head.reach", retained_receipt_sha256=off["receipt_sha256"])
    assert reach_cov.complete and reach[0].shape == (2,) and reach[0].signed_values == (0.3, -0.3)


def test_hh16_emitter_receipt_tamper_and_anchor_mismatch_are_refused():
    receipt = _emitted_receipt(kind="parts")
    tampered = dict(receipt)
    tampered["complete"] = True
    tampered["errors"] = []
    tampered["events"] = list(receipt["events"])
    tampered["events"][3] = dict(tampered["events"][3], signed_values=[0.0] * (3 * 64))
    _refused("OBSERVATION_TAMPERED", dc.captures_from_observation, tampered, "graph.round_input",
             retained_receipt_sha256=tampered["receipt_sha256"])
    _refused("OBSERVATION_ANCHOR_MISMATCH", dc.captures_from_observation, receipt, "graph.round_input",
             retained_receipt_sha256="0" * 64)
    from . import observation
    cap = observation.Capture(checkpoint_sha256=CKPT, input_sha256=INPUT_A, kind="parts", rounds=dc.CORE_ROUNDS, mode="OFF")
    cap.closed = cap.cleanup_complete = True
    off = cap.receipt()
    _refused("OBSERVATION_DISABLED", dc.captures_from_observation, off, "graph.round_input", retained_receipt_sha256=off["receipt_sha256"])

    def reseal(edited):
        body = {k: v for k, v in edited.items() if k != "receipt_sha256"}
        edited["receipt_sha256"] = dc._emitter_sha(dc._emitter_canonical(body))
        return edited
    relabeled = dict(receipt)
    relabeled["events"] = [dict(e, coordinate_meaning="hidden MLP neuron index") if e["site"] == "graph.round_input" else e
                           for e in receipt["events"]]
    reseal(relabeled)
    _refused("COORDINATE_MEANING_MISMATCH", dc.captures_from_observation, relabeled, "graph.round_input",
             retained_receipt_sha256=relabeled["receipt_sha256"])
    # round/call order is enforced inside the converter, not only by the emitter or Codex's reader
    swapped = dict(receipt)
    swapped["events"] = [dict(e, round_index=(e["round_index"] + 1) % dc.CORE_ROUNDS) if e["site"] == "graph.round_input" else e
                         for e in receipt["events"]]
    reseal(swapped)
    _refused("CAPTURE_ROUND_ORDER", dc.captures_from_observation, swapped, "graph.round_input",
             retained_receipt_sha256=swapped["receipt_sha256"])
    duplicated = dict(receipt)
    duplicated["events"] = [dict(e, call_index=0, round_index=0) if e["site"] == "graph.round_input" and e["call_index"] == 1 else e
                            for e in receipt["events"]]
    reseal(duplicated)
    _refused("CAPTURE_CALL_ORDER", dc.captures_from_observation, duplicated, "graph.round_input",
             retained_receipt_sha256=duplicated["receipt_sha256"])


def test_hh16_convert_observation_is_versioned_anchored_and_reports_every_site_honestly():
    receipt = _emitted_receipt(kind="parts")
    _refused("EXTERNAL_ANCHOR_REQUIRED", dc.convert_observation, receipt, retained_receipt_sha256=None)
    _refused("OBSERVATION_ANCHOR_MISMATCH", dc.convert_observation, receipt, retained_receipt_sha256="0" * 64)
    converted = dc.convert_observation(receipt, retained_receipt_sha256=receipt["receipt_sha256"])
    assert converted["schema"] == dc.CONVERSION_SCHEMA and converted["emitter_source"] == dc.EMITTER_SOURCE
    assert converted["anchor"] == "EXTERNAL_ANCHOR_VERIFIED" and converted["receipt_sha256"] == receipt["receipt_sha256"]
    assert converted["identity"]["checkpoint_sha256"] == CKPT and converted["identity"]["source_sha256"] == SRC
    assert set(converted["sites"]) == set(dc.SITES) and converted["tensor_sites"] == len(dc.TENSOR_SITES)
    rounds = converted["sites"]["graph.round_input"]
    assert rounds["tensor"] is True and len(rounds["captures"]) == dc.CORE_ROUNDS and rounds["coverage"]["complete"]
    assert rounds["raw_meaning"] == dc.EMITTER_MEANINGS["graph.round_input"]
    assert rounds["captures"][0].coordinate_meaning == dc.EMITTER_MEANINGS["graph.round_input"]
    assert rounds["captures"][0].dtype == "float32" and converted["dtype_map"]["torch.float32"] == "float32"
    reach = converted["sites"]["head.reach"]
    assert reach["tensor"] is True and reach["captures"] == () and reach["expected_zero"] is True and reach["coverage"]["complete"]
    mapping = converted["sites"]["input.mapping"]
    assert mapping["tensor"] is False and mapping["events"] == 1 and len(mapping["public_value_sha256"]) == 1
    assert converted["sites"]["answer.assembly"]["tensor"] is False and converted["claim"] == "OBSERVATION_ONLY_CAUSALITY_UNMEASURED"
    assert len(converted["conversion_digest"]) == 64
    assert "DISPLAY ONLY" in converted["conventions"]["emitter_preview"] and "never flat" in converted["conventions"]["configuration"]
    again = dc.convert_observation(receipt, retained_receipt_sha256=receipt["receipt_sha256"])
    assert again["conversion_digest"] == converted["conversion_digest"]


def test_hh16_convert_observation_refuses_incomplete_unknown_dtype_and_unknown_site():
    incomplete = _emitted_receipt(kind="parts", skip_site="graph.round_update")
    _refused("OBSERVATION_INCOMPLETE", dc.convert_observation, incomplete, retained_receipt_sha256=incomplete["receipt_sha256"])
    receipt = _emitted_receipt(kind="reach")

    def reseal(edited):
        body = {k: v for k, v in edited.items() if k != "receipt_sha256"}
        edited["receipt_sha256"] = dc._emitter_sha(dc._emitter_canonical(body))
        return edited
    odd_dtype = dict(receipt)
    odd_dtype["events"] = [dict(e, dtype="torch.int64") if e["site"] == "head.reach" else e for e in receipt["events"]]
    reseal(odd_dtype)
    _refused("CAPTURE_DTYPE_UNKNOWN", dc.convert_observation, odd_dtype, retained_receipt_sha256=odd_dtype["receipt_sha256"])
    foreign_site = dict(receipt)
    foreign_site["events"] = list(receipt["events"]) + [dict(receipt["events"][2], site="mlp.layer3")]
    reseal(foreign_site)
    _refused("SITE_UNKNOWN", dc.convert_observation, foreign_site, retained_receipt_sha256=foreign_site["receipt_sha256"])
    tensor_in_public_site = dict(receipt)
    tensor_in_public_site["events"] = [dict(e, signed_values=[0.0, 1.0], shape=[2]) if e["site"] == "answer.scores" else e
                                       for e in receipt["events"]]
    reseal(tensor_in_public_site)
    _refused("SITE_NOT_TENSOR", dc.convert_observation, tensor_in_public_site,
             retained_receipt_sha256=tensor_in_public_site["receipt_sha256"])


def test_protocol_checks_are_all_named_and_fail_closed_on_scope_drift():
    from . import diagnostic_intervention as di
    receipt = _emitted_receipt(kind="reach")
    anchor = receipt["receipt_sha256"]
    declaration = di.declare(action="SUPPRESS", site="head.reach", checkpoint_sha256=CKPT, input_sha256=INPUT_A,
                             source_sha256=SRC, rows=(0,), coordinates=(0,), gain=1.0, hypothesis_id="H1",
                             predicted_change="reach margin falls")
    configuration = dc.freeze_configuration(dc.detect_from_observation(receipt, site="head.reach", row=0, k=1, split="DISCOVERY",
                                                                       family="F", retained_receipt_sha256=anchor))
    control = di.matched_control(declaration, width=2, seed=3)
    witness = dc.digest(di.witness_protocol())
    passing = di.protocol_checks(declaration=declaration, passive_receipt=receipt, retained_passive_receipt_sha256=anchor,
                                 configuration=configuration, control=control, witness_protocol_digest=witness, learner_pending=None)
    assert passing["all_passed"] is True and set(passing["checks"]) == set(di.PROTOCOL_CHECKS)
    assert passing["declaration_digest"] == di.declaration_digest(declaration)
    other_input = _emitted_receipt(kind="reach", input_sha256=INPUT_B)
    drift = di.protocol_checks(declaration=declaration, passive_receipt=other_input,
                               retained_passive_receipt_sha256=other_input["receipt_sha256"], configuration=configuration,
                               control=control, witness_protocol_digest=witness, learner_pending=None)
    assert drift["all_passed"] is False and drift["checks"]["passive_receipt_captured_same_scope"] is False
    unanchored = di.protocol_checks(declaration=declaration, passive_receipt=receipt, retained_passive_receipt_sha256=None,
                                    configuration=configuration, control=control, witness_protocol_digest=witness, learner_pending=None)
    assert unanchored["checks"]["passive_receipt_anchored"] is False and unanchored["all_passed"] is False
    unfrozen = di.protocol_checks(declaration=declaration, passive_receipt=receipt, retained_passive_receipt_sha256=anchor,
                                  configuration=dc.detect_from_observation(receipt, site="head.reach", row=0, k=1, split="DISCOVERY",
                                                                           family="F", retained_receipt_sha256=anchor),
                                  control=control, witness_protocol_digest=witness, learner_pending=None)
    assert unfrozen["checks"]["configuration_frozen_and_anchored"] is False
    pending = di.protocol_checks(declaration=declaration, passive_receipt=receipt, retained_passive_receipt_sha256=anchor,
                                 configuration=configuration, control=control, witness_protocol_digest=witness,
                                 learner_pending={"results": []})
    assert pending["checks"]["no_training_entry"] is False
    assert di.CONNECTION_ENABLED_BY_DEFAULT is False
