"""Regression controls; case identities must be collected and executed in AWS."""
from dataclasses import asdict, replace
import json

import pytest

from .admission import TrustedHost
from .contracts import (COMPONENTS, FailureObservation, HarnessConfig, ModificationProposal,
                        ParentIdentity, SelfDescription, build_candidate, digest, execution_config,
                        public_observation)
from .conftest import host_for
from .episode import read_observation


def proposal(observation, operation="CHANGE_CONFIG", parameters=(True,)):
    return ModificationProposal(observation.parent, digest(asdict(observation)), operation, parameters)


@pytest.mark.parametrize("field,value", [
    ("source_sha", "f" * 40), ("runtime_sha", "f" * 40), ("branch", "foreign/branch"),
    ("source_manifest_sha256", "f" * 64), ("harness_sha256", "f" * 64)], ids=['case_00', 'case_01', 'case_02', 'case_03', 'case_04'])
def test_all_caller_records_agree_but_foreign_parent_is_refused(admitted_case, field, value):
    host, description, _, observation = admitted_case
    foreign = replace(host.parent, **{field: value})
    foreign_obs = replace(observation, parent=foreign)
    with pytest.raises(ValueError, match="PARENT_NOT_ADMITTED"):
        build_candidate(host, replace(description, parent=foreign), foreign_obs, proposal(foreign_obs))


@pytest.mark.parametrize("checkpoint", ["NOT-A-SHA256", "f" * 64, {}, 1], ids=['case_00', 'case_01', 'case_02', 'case_03'])
def test_no_model_fixture_refuses_every_non_null_checkpoint(admitted_case, checkpoint):
    host, _, _, _ = admitted_case
    with pytest.raises(ValueError, match="CHECKPOINT_NOT_SUPPORTED"):
        replace(host.parent, checkpoint_sha256=checkpoint)
    assert ParentIdentity(**asdict(host.parent)).checkpoint_sha256 is None


def test_wrong_schema_refused_on_deserialization(admitted_case):
    host, _, _, _ = admitted_case
    with pytest.raises(ValueError, match="INCOMPATIBLE_PARENT_SCHEMA"):
        ParentIdentity(**(asdict(host.parent) | {"schema": "foreign/999"}))


@pytest.mark.parametrize("route", ["direct", "json", "bypass_init"], ids=['case_00', 'case_01', 'case_02'])
def test_observation_provenance_validated_at_every_boundary(admitted_case, route):
    host, description, _, observation = admitted_case
    with pytest.raises(ValueError, match="NON_PUBLIC_OBSERVATION_PROVENANCE"):
        if route == "direct":
            bad = replace(observation, visibility="EVALUATOR_ONLY")
        elif route == "json":
            bad = read_observation(json.loads(json.dumps(asdict(observation))) | {"provenance": "FUTURE_OUTCOME"})
        else:
            bad = object.__new__(FailureObservation)
            for key, value in asdict(observation).items():
                object.__setattr__(bad, key, observation.parent if key == "parent" else value)
            object.__setattr__(bad, "visibility", "EVALUATOR_ONLY")
        build_candidate(host, description, bad, proposal(observation))


@pytest.mark.parametrize("field,value", [
    ("input_sha256", "f" * 64), ("trace_sha256", "f" * 64), ("journal_digest", "f" * 64),
    ("run_id", "run_999999"), ("run_sequence", 999999), ("original_prediction", "fabricated")], ids=['case_00', 'case_01', 'case_02', 'case_03', 'case_04', 'case_05'])
def test_plausible_fabricated_observation_cannot_be_self_authenticated(admitted_case, field, value):
    host, description, _, observation = admitted_case
    bad = replace(observation, **{field: value})
    with pytest.raises(ValueError, match="OBSERVATION_NOT_HOST_EVIDENCE|RUN_NOT_HOST_RECORDED"):
        build_candidate(host, description, bad, proposal(bad))


@pytest.mark.parametrize("field", ["answer_key", "future_outcome", "evaluator_score", "checkpoint_path"], ids=['case_00', 'case_01', 'case_02', 'case_03'])
def test_observation_unknown_fields_refused_without_reading_any_protected_value(admitted_case, field):
    host, _, _, observation = admitted_case
    data = {k: v for k, v in asdict(observation).items() if k not in ("parent", "provenance", "visibility")}
    with pytest.raises(ValueError, match="NON_PUBLIC_OR_UNKNOWN"):
        public_observation(host.parent, data | {field: "synthetic disallowed field"})


@pytest.mark.parametrize("field,value", [("hypothesis", "arbitrary text"), ("alternatives", ("arbitrary",)), ("proposer", "foreign")], ids=['case_00', 'case_01', 'case_02'])
def test_proposal_text_channels_are_finite_identifiers(admitted_case, field, value):
    _, _, _, observation = admitted_case
    with pytest.raises(ValueError, match="UNSUPPORTED_PROPOSAL_CHANNEL"):
        replace(proposal(observation), **{field: value})


@pytest.mark.parametrize("parameters", [(1,), (float("nan"),), (True, 500), ("../grader.py",), ("import os",)], ids=['case_00', 'case_01', 'case_02', 'case_03', 'case_04'])
def test_configuration_cannot_expand_authority_or_execute_code(admitted_case, parameters):
    host, description, _, observation = admitted_case
    with pytest.raises(ValueError, match="ONLY_ALLOW_ACQUISITION"):
        build_candidate(host, description, observation, proposal(observation, parameters=parameters))


@pytest.mark.parametrize("operation", ["PATCH_ALLOWED_MODULE", "ADD_TYPED_MODULE", "RAISE_BUDGET"], ids=['case_00', 'case_01', 'case_02'])
def test_unisolated_edit_modes_are_unavailable(admitted_case, operation):
    _, _, _, observation = admitted_case
    with pytest.raises(ValueError, match="UNSUPPORTED_EDIT_MODE"):
        proposal(observation, operation=operation)


@pytest.mark.parametrize("field,value", [("entrypoint", "foreign"), ("supported_edits", ("NO_CHANGE",)),
                                        ("observed_memory_bytes", -1), ("tensor_dtypes", ("float32",))], ids=['case_00', 'case_01', 'case_02', 'case_03'])
def test_unsupported_self_description_is_refused(admitted_case, field, value):
    _, description, _, _ = admitted_case
    with pytest.raises(ValueError):
        replace(description, **{field: value})


def test_fabricated_baseline_config_refused_even_when_disabled(admitted_case):
    host, description, _, observation = admitted_case
    with pytest.raises(ValueError, match="BASELINE_NOT_HOST_ADMITTED"):
        execution_config(host, replace(description, config=HarnessConfig(True)), observation, None, "disabled")


def test_build_order_and_candidate_identity_are_bound_to_host_ledger(admitted_case):
    host, description, _, observation = admitted_case
    candidate = build_candidate(host, description, observation, proposal(observation))
    assert candidate.build_sequence > observation.run_sequence
    with pytest.raises(ValueError, match="CANDIDATE_BUILD_ALTERED"):
        host.verify_candidate(description, observation, replace(candidate, build_sequence=observation.run_sequence))
    assert execution_config(host, description, observation, candidate, "shadow") == host.baseline_config


def test_no_change_and_h2_preserve_required_components(admitted_case):
    host, description, _, observation = admitted_case
    assert build_candidate(host, description, observation, proposal(observation, "NO_CHANGE", ())).config == host.baseline_config
    assert build_candidate(host, description, observation, proposal(observation, "COMPOSE_SUPPORTED_COMPONENTS", COMPONENTS)).edit_level == "H2"
    with pytest.raises(ValueError, match="MISSING_OBLIGATION"):
        build_candidate(host, description, observation, proposal(observation, "COMPOSE_SUPPORTED_COMPONENTS", COMPONENTS[:-1]))


def test_changed_external_policy_cannot_be_accepted_by_old_anchor(tmp_path):
    host = host_for(tmp_path / "host")
    data = json.loads(host.policy_path.read_bytes())
    data["branch"] = "attacker/branch"
    host.policy_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="HOST_POLICY_ANCHOR_MISMATCH"):
        TrustedHost(host.policy_path, host.policy_sha256, host.evidence_root)
