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

from pydantic import BaseModel, Field, model_validator

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


class WordSpan(BaseModel):
    """One word in the generated continuation, with token-backing.

    Word-boundary policy (deterministic, MUST match the worker reconstruction
    in ``app.runtime.word_spans.build_word_spans``):

    1. The "output text" is the concatenation of every ``TokenEvent.token``
       string, in token-index order. This is exactly what the user sees.
    2. A "word" is a maximal run of non-whitespace characters in that output
       text (regex: ``\\S+``). Whitespace between words is structural and
       belongs to NO span. ``char_start`` / ``char_end`` are half-open
       indices into the output text.
    3. Token-backing is lossless and atomic. Every TokenEvent.token_index
       appears in exactly one of:
         a. ``token_indices`` of exactly one WordSpan (the first word its
            non-whitespace content touches; if a single token decodes to
            text crossing two ``\\S+`` runs, those runs are MERGED into one
            span so the token is not split), OR
         b. ``WordSpansEvent.structural_token_indices`` (the token decodes
            to whitespace only — e.g. a leading-space-only BPE token, or a
            standalone newline).
    4. Leading-whitespace tokens (e.g. " hello"): the leading space sits in
       the inter-word gap (it is structural at the character level inside the
       token), but the TOKEN INDEX belongs to the span of the word that
       follows ("hello"). This is the "leading whitespace stays with the
       following word's span" rule.

    UI contract: clicking a word displays all tokens listed in
    ``token_indices``. ``char_start`` / ``char_end`` let the UI highlight
    the exact substring of the displayed continuation.
    """

    word: str = Field(..., min_length=1)
    token_indices: list[int] = Field(..., min_length=1)
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., gt=0)

    @model_validator(mode="after")
    def _validate_range(self) -> "WordSpan":
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be strictly greater than char_start")
        return self


class WordSpansEvent(BaseModel):
    """Word-level token-backing for the generated continuation.

    Emitted ONCE per session, immediately before ``CompleteEvent``. The UI
    consumes it to render the streamed text as clickable word spans. Single
    emission (rather than incremental per-word) was chosen because:

    - the word boundary of token N can shift if token N+1 contains no
      leading whitespace (it would EXTEND the prior word), so incremental
      emission would force re-emission of the last word; a single
      end-of-stream emission is cheaper and always correct;
    - click-on-word is a post-stream interaction: users only click words
      that have already been rendered.

    Invariants (enforced by the producer; UI may assume):
    - ``total_tokens_covered`` equals the number of TokenEvent.token_index
      values represented (sum over span.token_indices PLUS the length of
      ``structural_token_indices``).
    - Spans are non-overlapping and sorted by ``char_start``.
    - The union of ``token_indices`` across all spans and
      ``structural_token_indices`` equals the contiguous range
      ``[0, total_tokens_covered)``.
    """

    type: Literal["word_spans"] = "word_spans"
    spans: list[WordSpan] = Field(default_factory=list)
    structural_token_indices: list[int] = Field(
        default_factory=list,
        description=(
            "Token indices whose decoded text is whitespace-only and which "
            "therefore belong to no word span. The UI should treat these "
            "as inter-word gap material."
        ),
    )
    total_tokens_covered: int = Field(..., ge=0)


LiveTraceEvent = (
    ManifestEvent
    | TokenEvent
    | NeuronCoversEvent
    | WordSpansEvent
    | ErrorEvent
    | CompleteEvent
)
