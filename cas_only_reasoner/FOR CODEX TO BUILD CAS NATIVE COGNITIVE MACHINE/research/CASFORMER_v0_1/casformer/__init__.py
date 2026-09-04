"""Public API for the isolated CASformer v0.1 research prototype."""

from .core import (
    CASFORMER_VERSION,
    DIAGNOSTIC_FEATURE_NAMES,
    CASControl,
    CASformerBlock,
    CASformerConfig,
    CASformerEncoder,
    CASformerLanguageModel,
    CASformerTelemetry,
    CJTRegionGate,
    DifferentialConductanceLinear,
    OhmicAttentionTelemetry,
    OhmicMultiheadAttention,
    OperatingRegion,
)
from .controls import LearnedCASControlAdapter
from .circuit import ConductanceCircuitResult, DifferentiableConductanceCircuit
from .diagnostics import (
    FlowAudit,
    IQReading,
    audit_flow,
    capability_resistance,
    quantize_current,
)
from .trace import (
    TRACE_SCHEMA_VERSION,
    TRACE_STATUS,
    CASformerTrace,
    make_trace,
    verify_trace,
)
from .schema import load_trace_schema

__version__ = CASFORMER_VERSION

__all__ = [
    "CASFORMER_VERSION",
    "DIAGNOSTIC_FEATURE_NAMES",
    "CASControl",
    "CASformerBlock",
    "CASformerConfig",
    "CASformerEncoder",
    "CASformerLanguageModel",
    "CASformerTelemetry",
    "CJTRegionGate",
    "DifferentialConductanceLinear",
    "OhmicAttentionTelemetry",
    "OhmicMultiheadAttention",
    "OperatingRegion",
    "LearnedCASControlAdapter",
    "ConductanceCircuitResult",
    "DifferentiableConductanceCircuit",
    "FlowAudit",
    "IQReading",
    "audit_flow",
    "capability_resistance",
    "quantize_current",
    "TRACE_SCHEMA_VERSION",
    "TRACE_STATUS",
    "CASformerTrace",
    "make_trace",
    "verify_trace",
    "load_trace_schema",
    "__version__",
]
