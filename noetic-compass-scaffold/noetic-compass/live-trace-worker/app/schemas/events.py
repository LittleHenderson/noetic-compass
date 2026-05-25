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
      A scalar in [0, 1] indicating how strongly the cover-level
      evidence supports this class. For the Stage 27F Pythia-160M live
      worker, this is targeted_drop / clean_margin for the cover class,
      projected onto each member row so the UI can render an
      interpretable cover. It is NOT an independent monosemantic score
      for each individual neuron. ``None`` is used when no calibrated
      cover score is available. Values strictly > 0.95 or < 0.40 fall
      to the "unavailable" band so they don't silently get re-bucketed;
      a reported >0.95 deserves a closer look.

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


class KnobResolutionEvent(BaseModel):
    """Emitted right after ManifestEvent so the cockpit can prove that the
    method-panel knobs it sent are the values the worker actually used.

    ``resolved_knobs`` is keyed by ``method_id`` (matches the ids in
    ``atlas-viewer/src/lib/testingMethods.ts``) and carries the
    post-default/clamp/coerce values the worker resolved from
    ``req.method_config["knobs"]``. The UI's diagnostic disclosure
    cross-references this against what it sent.

    This event is a NEW envelope variant; downstream consumers that
    pre-date it must tolerate unknown types — the cockpit's
    ``appendLiveEvent`` already returns the trace unchanged for
    unrecognised types so the worker can emit safely.
    """

    type: Literal["knob_resolution"] = "knob_resolution"
    resolved_knobs: dict[str, dict[str, Any]] = Field(default_factory=dict)


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

    @model_validator(mode="after")
    def _validate_zero_based_contiguous(self) -> "WordSpansEvent":
        """Enforce the 0-based contiguous coverage invariant.

        The UI indexes per-token frames by token_index. If the worker ever
        emits non-contiguous or non-0-based indices, frame lookups will
        silently desync. Validate at emit time instead.
        """
        seen: set[int] = set()
        for span in self.spans:
            for idx in span.token_indices:
                if idx in seen:
                    raise ValueError(
                        f"token_index {idx} appears in multiple WordSpans; "
                        "token-backing must be lossless"
                    )
                seen.add(idx)
        for idx in self.structural_token_indices:
            if idx in seen:
                raise ValueError(
                    f"token_index {idx} is in both a span and "
                    "structural_token_indices; choose one bucket"
                )
            seen.add(idx)
        expected = set(range(self.total_tokens_covered))
        if seen != expected:
            missing = sorted(expected - seen)
            extra = sorted(seen - expected)
            raise ValueError(
                "WordSpansEvent coverage must equal [0, total_tokens_covered); "
                f"missing={missing[:8]}{'...' if len(missing) > 8 else ''} "
                f"extra={extra[:8]}{'...' if len(extra) > 8 else ''}"
            )
        return self


LiveTraceEvent = (
    ManifestEvent
    | KnobResolutionEvent
    | TokenEvent
    | NeuronCoversEvent
    | WordSpansEvent
    | ErrorEvent
    | CompleteEvent
)
