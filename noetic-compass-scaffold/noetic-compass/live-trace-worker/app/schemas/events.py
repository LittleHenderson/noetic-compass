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


# --- neuron-cover member with confidence + evidence ----------------------


ConfidenceBand = Literal["high", "medium", "low", "unavailable"]


class NeuronCoverMember(BaseModel):
    """One neuron entry in a cover class.

    `label` is the canonical "L{layer}N{index}" coordinate the UI already
    consumes. The extra fields carry the interpretive payload the cockpit
    needs to translate a red blindspot into a human-readable concern.

    `confidence`:
      A scalar in [0, 1] indicating how strongly per-neuron evidence
      (probe + ablation + control separation) supports membership in
      this cover class. ``None`` is used when probe scores are not
      available in-tree yet — see comment in
      ``app/runtime/cover_library.py``. Values strictly > 0.95 or
      < 0.40 fall to the "unavailable" band so they don't silently
      get re-bucketed; a reported >0.95 deserves a closer look.

    `confidence_band`:
      Categorical bucket the UI shows ("80-95% high", "60-79% medium",
      "40-59% low", or "unavailable"). Computed via
      ``band_for_confidence`` so worker + UI stay in lock-step.

    `evidence_sources`:
      Free-form labels for which evidence streams agree, e.g.
      ``["probe", "ablation"]`` or ``["probe", "ablation",
      "control_separation"]``. Empty list when band is "unavailable".
      The UI joins this list with " + " for the "Evidence:" line.
    """

    label: str
    confidence: float | None = Field(default=None)
    confidence_band: ConfidenceBand = "unavailable"
    evidence_sources: list[str] = Field(default_factory=list)


def band_for_confidence(c: float | None) -> ConfidenceBand:
    """Same bands the UI computes — keep both sides in sync.

    Bands (per product spec):
      80-95% high    — probe + ablation + control separation agree
      60-79% medium  — measurable but not fully replicated
      40-59% low     — weak/intermittent signal
      unavailable    — out-of-range / None / NaN — do not score
    """
    if c is None:
        return "unavailable"
    try:
        c_float = float(c)
    except (TypeError, ValueError):
        return "unavailable"
    # NaN check
    if c_float != c_float:
        return "unavailable"
    if 0.80 <= c_float <= 0.95:
        return "high"
    if 0.60 <= c_float < 0.80:
        return "medium"
    if 0.40 <= c_float < 0.60:
        return "low"
    return "unavailable"


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

    Each cover class maps to a list of ``NeuronCoverMember`` records carrying
    label + confidence + band + evidence_sources, so the cockpit can render
    a plain-English interpretation per blindspot rather than just the red
    overlay.

    Format is a SUPERSET of the offline trace's
    ``neuron_covers.per_class_neuron_covers`` (which used bare strings).
    UI tolerates both by promoting bare strings to placeholder members at
    parse time.
    """

    type: Literal["neuron_covers"] = "neuron_covers"
    per_class_neuron_covers: dict[str, list[NeuronCoverMember]] = Field(
        default_factory=dict,
    )


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
