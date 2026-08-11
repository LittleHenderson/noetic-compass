from __future__ import annotations

import importlib
from types import MappingProxyType

import pytest


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
    ("cas_harness_v2.universal_probe_contract", "_STATUS"),
    ("cas_harness_v2.universal_probe_contract", "_BOUNDARY"),
    ("cas_harness_v2.surface_meaning_preservation", "_STATUS"),
    ("cas_harness_v2.surface_meaning_preservation", "_BOUNDARY"),
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
