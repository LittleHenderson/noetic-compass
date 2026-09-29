"""Pointer: the ten addendum cases now live in research/cas_closed_loop_1/test_return_addresses.py.

This file keeps one check that the round-2 shim resolves to the leased adapter, so the
round-2 evidence path (RETURN_ADDRESS_CASE_MAP.md) stays truthful without duplicating cases.
"""
from research.cas_closed_loop_1 import native_step_adapter
from research.cas_closed_loop_1.claude_lead_20260927 import atlas_address


def test_round2_shim_resolves_to_the_leased_adapter():
    assert atlas_address.address_for_frame is native_step_adapter.atlas_address_for_frame
    assert atlas_address.resolve_address is native_step_adapter.resolve_atlas_address
    assert atlas_address.AddressRefused is native_step_adapter.AtlasAddressRefused
