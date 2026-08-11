from __future__ import annotations

import importlib
from types import MappingProxyType

import pytest

from cas_harness_v2._strict_json import StrictJSONError, thaw_json


_IMMUTABLE_AUTHORITY_MAPPINGS = (
    ("cas_harness_v2.comparison_model_protocol", "_STATUS"),
    ("cas_harness_v2.comparison_model_protocol", "_BOUNDARY"),
    ("cas_harness_v2.comparison_prompt_injection_layers", "_STATUS"),
    ("cas_harness_v2.comparison_prompt_injection_layers", "_BOUNDARY"),
    ("cas_harness_v2.comparison_departure_metrics", "_STATUS"),
    ("cas_harness_v2.comparison_departure_metrics", "_BOUNDARY"),
    ("cas_harness_v2.comparison_steering_effects", "_STATUS"),
    ("cas_harness_v2.comparison_steering_effects", "_BOUNDARY"),
    ("cas_harness_v2.comparison_shared_runner", "_STATUS"),
    ("cas_harness_v2.comparison_shared_runner", "_BOUNDARY"),
    ("cas_harness_v2.comparison_shared_protocol", "_STATUS"),
    ("cas_harness_v2.comparison_shared_protocol", "_BOUNDARY"),
    ("cas_harness_v2.comparison_steering_protocol", "_STATUS"),
    ("cas_harness_v2.comparison_steering_protocol", "_STEERING_BOUNDARY"),
    ("cas_harness_v2.comparison_steering_protocol", "_BLACK_BOX_BOUNDARY"),
    ("cas_harness_v2.comparison_steering_protocol", "_STEERING_CONTROL_EVIDENCE"),
    ("cas_harness_v2.comparison_steering_protocol", "_BLACK_BOX_CONTROL_EVIDENCE"),
    ("cas_harness_v2.universal_probe_contract", "_STATUS"),
    ("cas_harness_v2.universal_probe_contract", "_BOUNDARY"),
    ("cas_harness_v2.universal_probe_contract", "_SITE_PROJECTION"),
    ("cas_harness_v2.universal_probe_contract", "_SITE_TRANSFORMS"),
    ("cas_harness_v2.universal_probe_contract", "_FAMILY_REQUIRED_SITES"),
    ("cas_harness_v2.universal_probe_contract", "_FAMILY_CONFIG_TOKENS"),
    ("cas_harness_v2.surface_meaning_preservation", "_STATUS"),
    ("cas_harness_v2.surface_meaning_preservation", "_BOUNDARY"),
    ("cas_harness_v2.historical_evidence_import", "_STATUS"),
    ("cas_harness_v2.historical_evidence_import", "_BOUNDARY"),
    ("cas_harness_v2.jspace_shadow_contract", "_STATUS"),
    ("cas_harness_v2.jspace_shadow_contract", "_BOUNDARY"),
    ("cas_harness_v2.jspace_shadow_contract", "_COMPONENT_SEMANTICS"),
)

_IMMUTABLE_VALIDATION_SETS = (
    ("cas_harness_v2.comparison_model_protocol", "_MUTABLE_REVISION_ALIASES"),
    ("cas_harness_v2.comparison_departure_metrics", "_MUTABLE_REVISIONS"),
    ("cas_harness_v2.comparison_steering_protocol", "_FORBIDDEN_STAGEC_PHASES"),
    ("cas_harness_v2.universal_probe_contract", "_FORBIDDEN_INFERENCE_TOKENS"),
    ("cas_harness_v2.historical_evidence_import", "_CURRENT_SLOT_TOKENS"),
    ("cas_harness_v2.historical_evidence_import", "_CURRENT_STATUS_VALUES"),
)

_FROZEN_JSON_VALIDATORS = (
    ("cas_harness_v2.comparison_model_protocol", "_require_frozen_json"),
    ("cas_harness_v2.comparison_shared_protocol", "_require_frozen_json"),
    ("cas_harness_v2.comparison_shared_runner", "_require_frozen_json"),
    ("cas_harness_v2.comparison_prompt_injection_layers", "_require_frozen"),
    ("cas_harness_v2.surface_meaning_preservation", "_require_frozen"),
    ("cas_harness_v2.comparison_departure_metrics", "_require_frozen_json"),
    ("cas_harness_v2.comparison_steering_protocol", "_require_frozen"),
    ("cas_harness_v2.comparison_steering_effects", "_require_frozen"),
    ("cas_harness_v2.comparison_execution_boundary", "_require_frozen"),
    ("cas_harness_v2.universal_probe_contract", "_require_frozen_json"),
)


@pytest.mark.parametrize(("module_name", "attribute_name"), _IMMUTABLE_AUTHORITY_MAPPINGS)
def test_authority_status_and_boundary_mappings_are_immutable(
    module_name: str,
    attribute_name: str,
) -> None:
    module = importlib.import_module(module_name)
    mapping = getattr(module, attribute_name)
    assert type(mapping) is type(MappingProxyType({}))
    before = dict(mapping)
    key = next(iter(mapping))

    with pytest.raises(TypeError):
        mapping[key] = "FORGED"  # type: ignore[index]

    assert dict(mapping) == before
    for value in mapping.values():
        if type(value) is frozenset:
            with pytest.raises(AttributeError):
                value.clear()  # type: ignore[attr-defined]


@pytest.mark.parametrize(("module_name", "attribute_name"), _IMMUTABLE_VALIDATION_SETS)
def test_validation_sets_are_immutable(module_name: str, attribute_name: str) -> None:
    module = importlib.import_module(module_name)
    values = getattr(module, attribute_name)
    assert type(values) is frozenset
    before = frozenset(values)

    with pytest.raises(AttributeError):
        values.clear()

    assert values == before


def _hostile_mapping_proxy(calls: list[str]) -> MappingProxyType:
    class HostileMapping(dict):
        def __iter__(self):
            calls.append("iter")
            raise AssertionError("hostile mapping callback ran")

        def keys(self):
            calls.append("keys")
            raise AssertionError("hostile mapping callback ran")

        def items(self):
            calls.append("items")
            raise AssertionError("hostile mapping callback ran")

    return MappingProxyType(HostileMapping())


def test_strict_json_rejects_hostile_mapping_proxy_without_callbacks() -> None:
    calls: list[str] = []
    with pytest.raises(StrictJSONError, match="must wrap an exact dict"):
        thaw_json(_hostile_mapping_proxy(calls))
    assert calls == []


@pytest.mark.parametrize(("module_name", "validator_name"), _FROZEN_JSON_VALIDATORS)
def test_frozen_json_validators_reject_hostile_mapping_proxy_without_callbacks(
    module_name: str,
    validator_name: str,
) -> None:
    calls: list[str] = []
    module = importlib.import_module(module_name)
    validator = getattr(module, validator_name)

    with pytest.raises(Exception, match="mapping proxy must wrap an exact dict"):
        validator(_hostile_mapping_proxy(calls), "artifact.payload")

    assert calls == []
