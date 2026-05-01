"""CAS runtime-frame primitives for transition firing and traceability."""

from .runtime_frame import (
    AffectState,
    AmbiguityState,
    CASRuntimeFrame,
    DefaultStateDistribution,
    DriveLevel,
    DriveState,
    FeedbackEvent,
    FeedbackHistory,
    IdentityState,
    SaliencePolicy,
    SalienceResult,
    TemporalGrain,
    TransitionTraceRecord,
)
from .turn_execution import (
    CandidateSalience,
    CandidateTransition,
    RuntimeDelta,
    TurnExecutionRecord,
    diff_runtime_frames,
    evolve_runtime_frame,
    execute_turn,
)

__all__ = [
    "AffectState",
    "AmbiguityState",
    "CASRuntimeFrame",
    "DefaultStateDistribution",
    "DriveLevel",
    "DriveState",
    "FeedbackEvent",
    "FeedbackHistory",
    "IdentityState",
    "SaliencePolicy",
    "SalienceResult",
    "TemporalGrain",
    "TransitionTraceRecord",
    "CandidateSalience",
    "CandidateTransition",
    "RuntimeDelta",
    "TurnExecutionRecord",
    "diff_runtime_frames",
    "evolve_runtime_frame",
    "execute_turn",
]
