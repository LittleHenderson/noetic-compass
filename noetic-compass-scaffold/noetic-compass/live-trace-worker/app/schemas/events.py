"""Trace event types emitted on the SSE stream.

Each `data: ...` line in the SSE response carries one of the LiveTraceEvent
variants below, serialised as JSON. The UI's ReplayController-equivalent
consumes these in order and feeds them into the NeuralNetScene / Mode7Timeline
/ SpatialEvidencePanel.

The event schema is intentionally close to the offline ReplayTrace fixture
shape so the UI can reuse most of its rendering code unchanged.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .manifest import ModelManifest
from .methods import MethodRuntimeStatus


class NeuronActivation(BaseModel):
    layer: int = Field(..., ge=0)
    index: int = Field(..., ge=0)
    activation: float


class Mode7Edge(BaseModel):
    from_token_index: int | None
    to_token_index: int
    weight: float = Field(..., ge=0.0, le=1.0)


class CoverConfidence(BaseModel):
    """Cover-level confidence derived from Stage 27F row evidence.

    This is a cover-level metric, not a single-neuron certainty. Real scores
    must come from targeted_drop / clean_margin; unavailable and unsupported
    states carry explicit reasons instead of placeholder numbers.
    """

    status: Literal["real", "unavailable", "unsupported"]
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    label: Literal["low", "medium", "high"] | None = None
    reason: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_state(self):
        if self.status == "real":
            if self.score is None:
                raise ValueError("real cover confidence requires score")
            if self.label is None:
                raise ValueError("real cover confidence requires label")
            return self
        if self.score is not None:
            raise ValueError("unavailable/unsupported cover confidence cannot carry score")
        if self.label is not None:
            raise ValueError("unavailable/unsupported cover confidence cannot carry label")
        if not self.reason:
            raise ValueError("unavailable/unsupported cover confidence requires reason")
        return self


class CoverRowEvidence(BaseModel):
    """Stage 27F evidence for one Foundation-register cover row."""

    target: str
    candidate_layers: list[int] = Field(default_factory=list)
    neuron_cover: list[str] = Field(default_factory=list)
    clean_margin: float | None = None
    targeted_drop: float | None = None
    pair_kind: str | None = None
    partner: str | None = None
    sample_id: str | None = None
    confidence: CoverConfidence


class AttentionSummary(BaseModel):
    layer: int = Field(..., ge=0)
    head: int = Field(..., ge=0)
    weight: float = Field(..., ge=0.0, le=1.0)


class RpmGateCheckTrace(BaseModel):
    strictness_threshold: float = Field(..., ge=0.0, le=1.0)
    score: float = Field(..., ge=0.0, le=1.0)
    passed: bool
    attention_summary: list[AttentionSummary] | None = None


class VerificationStackTrace(BaseModel):
    mode: str
    verdict: str
    margin: float = Field(..., ge=0.0, le=1.0)


# --- envelope types ------------------------------------------------------


class ManifestEvent(BaseModel):
    """First event on every session — tells the UI what model it's looking at."""

    type: Literal["manifest"] = "manifest"
    manifest: ModelManifest


class MethodRuntimeStatusEvent(BaseModel):
    """Explicit method support/effect report for this LIVE run."""

    type: Literal["method_runtime_status"] = "method_runtime_status"
    methods: list[MethodRuntimeStatus]


class TokenEvent(BaseModel):
    """A token has been emitted by the model.

    Carries the activations + Mode 7 attribution + confidence for THIS token.
    The UI replaces its current_frame with this payload.
    """

    type: Literal["token"] = "token"
    token_index: int = Field(..., ge=0)
    token: str
    top_activated_neurons: list[NeuronActivation] = Field(default_factory=list)
    mode7_attribution: list[Mode7Edge] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    foundation_probe: list[float] | None = None
    rpm_gate_check: RpmGateCheckTrace | None = None
    verification_stack: VerificationStackTrace | None = None


class NeuronCoversEvent(BaseModel):
    """One-shot cover-set emission (typically sent once after manifest).

    The neuron cover sets per CAS class. Used to paint the Blindspots overlay.
    Format mirrors the offline trace's neuron_covers.per_class_neuron_covers.
    When Stage 27F row evidence is available, cover_evidence carries the real
    cover-level confidence contract alongside the legacy coordinate map.
    """

    type: Literal["neuron_covers"] = "neuron_covers"
    per_class_neuron_covers: dict[str, list[str]] = Field(default_factory=dict)
    cover_evidence: dict[str, CoverRowEvidence] = Field(default_factory=dict)


class ErrorEvent(BaseModel):
    """Fatal session error — UI must surface this and fall back to REPLAY."""

    type: Literal["error"] = "error"
    message: str
    retryable: bool = Field(default=False)


class CompleteEvent(BaseModel):
    """Last event on a successful session."""

    type: Literal["complete"] = "complete"
    total_tokens: int = Field(..., ge=0)


LiveTraceEvent = (
    ManifestEvent
    | MethodRuntimeStatusEvent
    | TokenEvent
    | NeuronCoversEvent
    | ErrorEvent
    | CompleteEvent
)
