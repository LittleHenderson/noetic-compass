"""Run in admitted AWS; these are conformance controls, not improvement scores."""
from dataclasses import asdict, replace
import pytest

from .contracts import (COMPONENTS, HarnessConfig, ModificationProposal, ParentIdentity,
                        SelfDescription, build_candidate, digest, execution_config, public_observation)


def case(operation="CHANGE_CONFIG", parameters=(True,)):
    parent = ParentIdentity("a" * 40, "b" * 40, "test", "c" * 64)
    description = SelfDescription(parent, HarnessConfig(False))
    observation = public_observation(parent, {"input_sha256": "d" * 64, "trace_sha256": "e" * 64,
                                  "original_prediction": None, "checked_effect": False, "feedback": "BLOCKED"})
    proposal = ModificationProposal(parent, digest(asdict(observation)), operation, parameters,
                                    "public fixture", "acquire missing prerequisite", ("NO_CHANGE",))
    return description, observation, proposal


@pytest.mark.parametrize("field,value", [("source_sha", "f" * 40), ("runtime_sha", "f" * 40),
    ("branch", "foreign"), ("checkpoint_sha256", "f" * 64), ("schema", "foreign"),
    ("source_manifest_sha256", "f" * 64), ("harness_sha256", "f" * 64)])
def test_parent_binding_rejects_every_identity_mismatch(field, value):
    d, o, p = case()
    with pytest.raises(ValueError, match="STALE_OR_FOREIGN"):
        build_candidate(d, o, replace(p, parent=replace(p.parent, **{field: value})))


@pytest.mark.parametrize("field", ["answer_key", "future_outcome", "evaluator_score", "checkpoint_path"])
def test_observation_rejects_hidden_or_extra_channels(field):
    d, _, _ = case()
    payload = {"input_sha256": "d" * 64, "trace_sha256": "e" * 64,
               "original_prediction": None, "checked_effect": False, "feedback": "BLOCKED", field: "x"}
    with pytest.raises(ValueError, match="NON_PUBLIC"):
        public_observation(d.parent, payload)


@pytest.mark.parametrize("parameters", [(1,), (float("nan"),), (True, 500), ("../grader.py",), ("import os",)])
def test_configuration_cannot_expand_authority_or_execute_code(parameters):
    d, o, p = case(parameters=parameters)
    with pytest.raises(ValueError, match="ONLY_ALLOW_ACQUISITION"):
        build_candidate(d, o, p)


@pytest.mark.parametrize("operation", ["PATCH_ALLOWED_MODULE", "ADD_TYPED_MODULE", "RAISE_BUDGET"])
def test_unisolated_edit_modes_are_not_exposed(operation):
    d, o, p = case(operation)
    with pytest.raises(ValueError, match="UNSUPPORTED_EDIT_MODE"):
        build_candidate(d, o, p)


def test_shadow_and_disabled_keep_parent_config_but_active_consumes_candidate():
    d, o, p = case()
    c = build_candidate(d, o, p)
    assert execution_config(d, o, c, "disabled") == d.config
    assert execution_config(d, o, c, "shadow") == d.config
    assert execution_config(d, o, c, "active").allow_acquisition is True
    with pytest.raises(ValueError, match="CANDIDATE_BUILD_ALTERED"):
        execution_config(d, o, replace(c, config=HarnessConfig(False)), "active")


def test_composition_preserves_required_verification_stage():
    d, o, p = case("COMPOSE_SUPPORTED_COMPONENTS", COMPONENTS)
    assert build_candidate(d, o, p).edit_level == "H2"
    with pytest.raises(ValueError, match="MISSING_OBLIGATION"):
        build_candidate(d, o, replace(p, parameters=COMPONENTS[:-1]))


def test_no_change_and_wrong_observation():
    d, o, p = case("NO_CHANGE", ())
    assert build_candidate(d, o, p).config == d.config
    with pytest.raises(ValueError, match="WRONG_OBSERVATION"):
        build_candidate(d, o, replace(p, observation_sha256="0" * 64))
