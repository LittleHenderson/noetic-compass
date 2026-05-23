"""Trace event types emitted on the SSE stream.

Each `data: ...` line in the SSE response carries one of the LiveTraceEvent
variants below, serialised as JSON. The UI's ReplayController-equivalent
consumes these in order and feeds them into the NeuralNetScene / Mode7Timeline
/ SpatialEvidencePanel.

The event schema is intentionally close to the offline ReplayTrace fixture
shape so the UI can reuse most of its rendering code unchanged.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .manifest import ModelManifest


class NeuronActivation(BaseModel):
    layer: int = Field(..., ge=0)
    index: int = Field(..., ge=0)
    activation: float


class Mode7Edge(BaseModel):
    from_token_index: int | None
    to_token_index: int
    weight: float = Field(..., ge=0.0, le=1.0)


# --- envelope types ------------------------------------------------------


class ManifestEvent(BaseModel):
    """First event on every session — tells the UI what model it's looking at."""

    type: Literal["manifest"] = "manifest"
    manifest: ModelManifest


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
    inversion_risk: float | None = Field(default=None, ge=0.0, le=1.0)


class NeuronCoversEvent(BaseModel):
    """One-shot cover-set emission (typically sent once after manifest).

    The neuron cover sets per CAS class. Used to paint the Blindspots overlay.
    Format mirrors the offline trace's neuron_covers.per_class_neuron_covers.
    """

    type: Literal["neuron_covers"] = "neuron_covers"
    per_class_neuron_covers: dict[str, list[str]] = Field(default_factory=dict)


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
    ManifestEvent | TokenEvent | NeuronCoversEvent | ErrorEvent | CompleteEvent
)
