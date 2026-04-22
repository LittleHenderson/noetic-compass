"""CAS-Native validation bridge — ADR-06 (Python side).

Batch-cached Python gateway to the Rust CAS engine. See
``docs/architecture/cas_native_v2_adrs.md`` (ADR-06) for the architectural
decision record.
"""

from .rust_bridge import (
    BatchValidationCache,
    BridgeConfig,
    CacheStats,
    RustValidationBridge,
)
from .structural_hash import StructuralPattern, canonicalize, structural_hash

__all__ = [
    "BatchValidationCache",
    "BridgeConfig",
    "CacheStats",
    "RustValidationBridge",
    "StructuralPattern",
    "canonicalize",
    "structural_hash",
]
