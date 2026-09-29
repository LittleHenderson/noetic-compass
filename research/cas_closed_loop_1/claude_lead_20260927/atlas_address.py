"""Round-2 origin of the snapshot-bound atlas addresses; now a shim.

Lease packet 2 moved the implementation into the leased adapter
(research/cas_closed_loop_1/native_step_adapter.py). This module re-exports it
so the round-2 evidence path keeps resolving. The round-2 implementation bytes
are in git history (commits c5478882 and 4060126c).
"""
from research.cas_closed_loop_1.native_step_adapter import (  # noqa: F401
    ATLAS_ADDRESS_AUTHORITY as AUTHORITY, ATLAS_ADDRESS_FIELDS as ADDRESS_FIELDS,
    ATLAS_ADDRESS_SCHEMA as ADDRESS_SCHEMA, ATLAS_RESOLUTION_SCHEMA as RESOLUTION_SCHEMA,
    AtlasAddressRefused as AddressRefused, _suspension_event as suspension_event_for,
    atlas_address_chain as address_chain, atlas_address_for_frame as address_for_frame,
    check_atlas_address as check_address, resolve_atlas_address as resolve_address,
)
