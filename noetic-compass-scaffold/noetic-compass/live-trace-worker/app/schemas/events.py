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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .manifest import ModelExecutionKind, ModelManifest


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
VerificationMode = Literal["BALANCED", "HIGH_PRECISION", "MAX_COVERAGE_TRIAGE"]
VerificationVerdict = Literal["ACCEPT", "FLAG", "SUPPRESS"]
VerificationScoreSource = Literal["confidence", "proxy_confidence", "unavailable"]
InterventionStructuralStatus = Literal[
    "DEMO_NOT_EXECUTED",
    "REJECTED_NO_COORDINATES",
    "REJECTED_INVALID_GAIN",
    "REJECTED_WRONG_COORDINATE_SPACE",
    "REJECTED_MISSING_PREFLIGHT",
    "REJECTED_HOOK_CONTRACT",
    "REJECTED_HOOK_CARDINALITY",
    "REJECTED_NONFINITE_TENSOR",
    "REJECTED_RNG_STATE_MISMATCH",
    "REJECTED_MISSING_STABILITY_CONTROL",
    "REJECTED_UNSTABLE_BASELINE",
    "REJECTED_ALL_COORDINATES_INVALID",
    "REJECTED_PARTIALLY_INVALID_COORDINATES",
    "REJECTED_RUNTIME_GEOMETRY",
    "HOOK_NOT_FIRED",
    "ACTIVATION_UNCHANGED",
    "OUTPUT_CHANGE_UNAVAILABLE",
    "OUTPUT_UNCHANGED",
    "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED",
]


class _FrozenReplayModel(BaseModel):
    """Deep-container-safe carrier whose public copy path always revalidates."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    def model_copy(
        self,
        *,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> "_FrozenReplayModel":
        payload = self.model_dump(mode="python")
        if update:
            payload.update(update)
        # `deep` has no semantic effect because every nested public collection
        # in these carriers is immutable and validation reconstructs children.
        _ = deep
        return type(self).model_validate(payload)

    def copy(
        self,
        *,
        include: Any = None,
        exclude: Any = None,
        update: dict[str, Any] | None = None,
        deep: bool = False,
    ) -> "_FrozenReplayModel":
        if include is not None or exclude is not None:
            raise TypeError("partial copies are not valid intervention carriers")
        return self.model_copy(update=update, deep=deep)

    @classmethod
    def model_construct(
        cls,
        _fields_set: set[str] | None = None,
        **values: Any,
    ) -> "_FrozenReplayModel":
        # The Pydantic default intentionally skips validation. That is unsafe
        # for a public evidence carrier, so this schema closes that escape.
        _ = _fields_set
        return cls.model_validate(values)


class InterventionCoordinate(_FrozenReplayModel):
    """One coordinate with its declared tensor space kept attached."""

    layer: int = Field(..., strict=True)
    index: int = Field(..., strict=True)
    coordinate_space: str = Field(..., min_length=1)


class InterventionTensorGeometry(_FrozenReplayModel):
    """Observed tensor geometry at the exact intervention hook."""

    layer: int = Field(..., ge=0)
    shape: tuple[int, ...] = Field(..., min_length=1)
    rank: int = Field(..., ge=1)
    width: int = Field(..., ge=1)
    projected_output_width: int = Field(..., ge=1)
    coordinate_space: Literal["mlp_intermediate_post_activation"] = (
        "mlp_intermediate_post_activation"
    )
    observation_phase: Literal[
        "unmodified_forward",
        "intervention_attempt",
    ]
    hook_module_path: str = Field(..., min_length=1)
    tensor_role: Literal["forward_pre_hook.input[0]"] = "forward_pre_hook.input[0]"
    dtype: str = Field(default="UNKNOWN", min_length=1)
    device: str = Field(default="UNKNOWN", min_length=1)
    all_finite: bool = False
    rng_state_sha256: str = Field(default="UNAVAILABLE", min_length=1)
    rng_state_after_sha256: str = Field(default="UNAVAILABLE", min_length=1)
    hook_call_count: int = Field(default=1, ge=1, strict=True)

    @model_validator(mode="after")
    def _validate_shape(self) -> "InterventionTensorGeometry":
        if self.rank != len(self.shape):
            raise ValueError("rank must equal len(shape)")
        if self.shape[-1] != self.width:
            raise ValueError("width must equal the last tensor dimension")
        for digest in (self.rng_state_sha256, self.rng_state_after_sha256):
            if digest != "UNAVAILABLE" and not (
                len(digest) == 64
                and digest == digest.lower()
                and all(character in "0123456789abcdef" for character in digest)
            ):
                raise ValueError("RNG state identity must be lowercase SHA-256 or UNAVAILABLE")
        return self


class EraserInterventionResult(_FrozenReplayModel):
    """Fail-closed structural receipt for one drive-local intervention pass."""

    contract_version: Literal["harness_v2.mlp_intermediate_eraser.v2"] = (
        "harness_v2.mlp_intermediate_eraser.v2"
    )
    method_id: Literal["drive_local_eraser"] = "drive_local_eraser"
    execution_kind: ModelExecutionKind
    source_kind: Literal[
        "stage27f_calibrated_cover",
        "typed_test_fixture",
        "demo_schema_only",
    ]
    structural_status: InterventionStructuralStatus
    structurally_valid: bool
    coordinate_space: str = Field(..., min_length=1)
    hook_semantics: Literal[
        "gpt_neox.layers[{layer}].mlp.dense_4h_to_h:forward_pre_hook.input[0]"
    ] = "gpt_neox.layers[{layer}].mlp.dense_4h_to_h:forward_pre_hook.input[0]"
    token_selection: Literal["batch_0_last_sequence_position"] = (
        "batch_0_last_sequence_position"
    )
    requested_gain: float | None = Field(default=None, allow_inf_nan=False)
    effective_gain: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_coordinate_width: int = Field(..., ge=1)
    expected_projected_output_width: int = Field(..., ge=1)
    hook_fired: bool = Field(
        ...,
        description="True only when every required intervention hook fired.",
    )
    required_hook_layers: tuple[int, ...] = Field(default_factory=tuple)
    hook_fired_layers: tuple[int, ...] = Field(default_factory=tuple)
    observed_tensor_geometry: tuple[InterventionTensorGeometry, ...] = Field(
        default_factory=tuple
    )
    reference_tensor_geometry: tuple[InterventionTensorGeometry, ...] = Field(
        default_factory=tuple
    )
    stability_control_tensor_geometry: tuple[InterventionTensorGeometry, ...] = Field(
        default_factory=tuple
    )
    requested_coordinates: tuple[InterventionCoordinate, ...] = Field(default_factory=tuple)
    valid_coordinates: tuple[InterventionCoordinate, ...] = Field(default_factory=tuple)
    invalid_coordinates: tuple[InterventionCoordinate, ...] = Field(default_factory=tuple)
    applied_coordinates: tuple[InterventionCoordinate, ...] = Field(default_factory=tuple)
    activation_changed: bool | None = Field(
        default=None,
        description=(
            "Exact tensor comparison at the selected last-sequence-position "
            "activated-intermediate hook."
        ),
    )
    output_changed: bool | None = Field(
        default=None,
        description=(
            "Exact comparison of paired baseline/intervention last-token logits; "
            "a structural observation, not a causal/utility claim."
        ),
    )
    stability_control_performed: bool = False
    baseline_output_stable: bool | None = None
    baseline_geometry_stable: bool | None = None
    detail: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate_structural_receipt(self) -> "EraserInterventionResult":
        def _keys(items: tuple[InterventionCoordinate, ...]) -> set[tuple[int, int, str]]:
            keys = {(item.layer, item.index, item.coordinate_space) for item in items}
            if len(keys) != len(items):
                raise ValueError("coordinate attestation lists cannot contain duplicates")
            return keys

        requested = _keys(self.requested_coordinates)
        valid = _keys(self.valid_coordinates)
        invalid = _keys(self.invalid_coordinates)
        applied = _keys(self.applied_coordinates)
        if not valid.issubset(requested) or not invalid.issubset(requested):
            raise ValueError("valid/invalid coordinates must be requested coordinates")
        if not applied.issubset(valid):
            raise ValueError("applied coordinates must be valid coordinates")
        if self.execution_kind != "demo_schema_only" and valid | invalid != requested:
            raise ValueError("non-demo coordinates must be partitioned valid/invalid")
        for item in self.valid_coordinates:
            if (
                item.layer < 0
                or item.index < 0
                or item.coordinate_space != "mlp_intermediate_post_activation"
                or item.coordinate_space != self.coordinate_space
            ):
                raise ValueError("valid coordinates must be non-negative and in hook space")
        required_layers = set(self.required_hook_layers)
        fired_layers = set(self.hook_fired_layers)
        requested_nonnegative_layers = {
            item.layer for item in self.requested_coordinates if item.layer >= 0
        }
        if self.execution_kind != "demo_schema_only" and (
            required_layers != requested_nonnegative_layers
        ):
            raise ValueError("required hook layers must equal requested coordinate layers")
        if self.hook_fired != (bool(required_layers) and required_layers <= fired_layers):
            raise ValueError("hook_fired must attest every required hook layer")

        unattributed_delta = (
            self.structural_status
            == "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
        )
        if self.structurally_valid:
            raise ValueError(
                "eraser v2 has no causal attestation path; structurally_valid must be false"
            )
        if unattributed_delta and not (
            not self.structurally_valid
            and self.hook_fired
            and self.activation_changed is True
            and self.output_changed is True
            and bool(applied)
            and not invalid
            and self.requested_gain is not None
            and self.effective_gain is not None
            and self.stability_control_performed
            and self.baseline_output_stable is True
            and self.baseline_geometry_stable is True
        ):
            raise ValueError(
                "unattributed delta requires exact observed application and stable controls"
            )
        if unattributed_delta:
            geometry_by_layer = {
                item.layer: item for item in self.observed_tensor_geometry
            }
            if len(geometry_by_layer) != len(self.observed_tensor_geometry):
                raise ValueError("observed tensor geometry must be unique per layer")
            if any(
                layer not in geometry_by_layer
                or geometry_by_layer[layer].observation_phase
                != "intervention_attempt"
                or geometry_by_layer[layer].width != self.expected_coordinate_width
                or geometry_by_layer[layer].projected_output_width
                != self.expected_projected_output_width
                or geometry_by_layer[layer].hook_module_path
                != f"gpt_neox.layers[{layer}].mlp.dense_4h_to_h"
                or geometry_by_layer[layer].tensor_role
                != "forward_pre_hook.input[0]"
                or geometry_by_layer[layer].dtype == "UNKNOWN"
                or geometry_by_layer[layer].device == "UNKNOWN"
                or not geometry_by_layer[layer].all_finite
                or len(geometry_by_layer[layer].rng_state_sha256) != 64
                or len(geometry_by_layer[layer].rng_state_after_sha256) != 64
                or geometry_by_layer[layer].hook_call_count != 1
                for layer in required_layers
            ):
                raise ValueError("unattributed delta requires exact attempted geometry")
            reference_by_layer = {
                item.layer: item for item in self.reference_tensor_geometry
            }
            stability_by_layer = {
                item.layer: item for item in self.stability_control_tensor_geometry
            }
            if (
                len(reference_by_layer) != len(self.reference_tensor_geometry)
                or len(stability_by_layer)
                != len(self.stability_control_tensor_geometry)
            ):
                raise ValueError("paired tensor geometry must be unique per layer")
            if any(
                layer not in reference_by_layer
                or layer not in stability_by_layer
                or reference_by_layer[layer].observation_phase
                != "unmodified_forward"
                or stability_by_layer[layer].observation_phase
                != "unmodified_forward"
                or reference_by_layer[layer].hook_call_count != 1
                or stability_by_layer[layer].hook_call_count != 1
                or not reference_by_layer[layer].all_finite
                or not stability_by_layer[layer].all_finite
                for layer in required_layers
            ):
                raise ValueError("unattributed delta requires exact stability geometry")
            for layer in required_layers:
                reference_payload = reference_by_layer[layer].model_dump()
                stability_payload = stability_by_layer[layer].model_dump()
                attempted_payload = geometry_by_layer[layer].model_dump()
                if reference_payload != stability_payload:
                    raise ValueError("stability geometry must exactly replay reference")
                attempted_payload["observation_phase"] = "unmodified_forward"
                if attempted_payload != reference_payload:
                    raise ValueError("attempted geometry must exactly match reference contract")
        if self.execution_kind == "demo_schema_only":
            if self.source_kind != "demo_schema_only":
                raise ValueError("demo execution requires demo_schema_only source")
            if self.structural_status != "DEMO_NOT_EXECUTED":
                raise ValueError("demo execution must be typed DEMO_NOT_EXECUTED")
            if applied or self.activation_changed is not None or self.output_changed is not None:
                raise ValueError("demo execution cannot claim intervention measurements")
            if (
                self.stability_control_performed
                or self.baseline_output_stable is not None
                or self.baseline_geometry_stable is not None
            ):
                raise ValueError("demo execution cannot claim a stability control")
        elif self.execution_kind == "typed_test_fixture":
            if self.source_kind != "typed_test_fixture":
                raise ValueError("typed fixtures require typed_test_fixture source")
        elif self.source_kind != "stage27f_calibrated_cover":
            raise ValueError("real execution requires the calibrated cover source")
        return self


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
    verification_mode: VerificationMode | None = Field(default=None)
    verification_verdict: VerificationVerdict | None = Field(default=None)
    verification_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    verification_score: float | None = Field(default=None, ge=0.0, le=1.0)
    verification_score_source: VerificationScoreSource | None = Field(default=None)
    verification_invalid_mode: str | None = Field(default=None)
    eraser_intervention_result: EraserInterventionResult | None = Field(
        default=None,
        description=(
            "Typed structural receipt when drive_local_eraser was requested. "
            "Absent only when no such intervention was requested."
        ),
    )


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


class AblationEffectEvent(BaseModel):
    """Result of a single-target causal ablation / intervention probe.

    Emitted ONCE per session (after the token stream, before ``word_spans``)
    when an ablation was requested via ``CreateSessionRequest.ablation_target``
    or a ``"causal_ablation"`` probe. This is the FIRST causal proof the live
    worker produces: the model is run once normally and once with the target
    MLP-output unit ablated, and the deltas are the measured causal effect of
    that unit on the next-token distribution.

    Honesty contract (load-bearing — the whole product depends on it):

    * ``is_real_model`` is ``True`` ONLY when these deltas were measured on
      actual loaded weights (``LoadedModel.is_real``). In demo mode the worker
      still emits a schema-valid event so downstream parsers don't break, but
      ``is_real_model`` is ``False`` AND the numeric deltas are ``None`` (a
      demo event reports "no causal measurement", never a fabricated number).
    * The runner flips its ``causal_proof`` chip to ``present`` ONLY when it
      sees an ``ablation_effect`` event with ``is_real_model = True``. A
      demo-mode event must never read as a real causal proof.

    ``baseline_top_token`` / ``ablated_top_token`` are the greedy argmax tokens
    of the un-ablated vs ablated last-token logits. ``logit_delta`` is the
    change in the baseline-top-token's own logit (ablated minus baseline), so a
    negative value means ablating the unit *suppressed* the token the model
    would otherwise have produced. ``confidence_delta`` is the change in the
    softmax-margin confidence (ablated minus baseline).
    """

    type: Literal["ablation_effect"] = "ablation_effect"
    target: dict[str, int] = Field(
        ...,
        description="The ablated unit, e.g. {'layer': 5, 'unit': 1234}.",
    )
    mode: Literal["zero", "mean"] = "zero"
    is_real_model: bool = Field(
        default=False,
        description=(
            "True only when the deltas were measured on real loaded weights. "
            "False => demo-mode stand-in; numeric deltas are None."
        ),
    )
    baseline_top_token: str | None = Field(default=None)
    ablated_top_token: str | None = Field(default=None)
    baseline_top_token_id: int | None = Field(default=None)
    ablated_top_token_id: int | None = Field(default=None)
    logit_delta: float | None = Field(
        default=None,
        description=(
            "Change in the baseline-top-token's logit under ablation "
            "(ablated - baseline). None in demo mode."
        ),
    )
    confidence_delta: float | None = Field(
        default=None,
        description=(
            "Change in softmax-margin confidence under ablation "
            "(ablated - baseline). None in demo mode."
        ),
    )
    top_token_changed: bool | None = Field(
        default=None,
        description="Whether ablation changed the greedy top token. None in demo mode.",
    )
    detail: str | None = Field(
        default=None,
        description="Human-readable note, e.g. why a demo event carries no measurement.",
    )


class AblationControlEffectEvent(BaseModel):
    """Matched-control selectivity test for the single-target ablation.

    Emitted ONCE per session immediately AFTER ``AblationEffectEvent`` (and
    before ``word_spans``) whenever an ablation was requested. It answers the
    question the single-target ablation alone cannot: *was the chosen unit's
    next-token effect actually selective, or would ablating ANY sibling unit in
    the same layer have moved the distribution just as much?*

    Method (real mode): re-run the SAME zero/mean ablation on ``n_controls``
    randomly-sampled OTHER units in the SAME layer, each measured by the change
    in the baseline-top-token's logit (the same metric as the ablation event).
    The target's absolute logit change is compared against the control
    distribution. ``selectivity_passed`` is True only when the target moved that
    token strictly more than the largest control move — the single-unit
    forward-pass analog of the Stage-9 'beat random same-rank controls' guard.

    Scope honesty (load-bearing): this is a SINGLE-UNIT, next-token selectivity
    control. It is NOT the 40-Element subspace matched-control (that is a
    separate, readout-level proof produced by the offline Stage-9 pipeline).
    Both are real matched controls, but they make different-strength claims, and
    this event's ``detail`` states which one it is.

    Honesty contract (mirrors AblationEffectEvent):

    * ``is_real_model`` is True ONLY when the control deltas were measured on
      real loaded weights AND at least one control unit was actually ablated.
      In demo mode (or when no sibling unit could be sampled) the event is
      schema-valid but ``is_real_model`` is False and every numeric field is
      None — it reports "no matched control was measured", never a fabricated
      number.
    * The runner flips its ``control_proof`` chip to ``present`` ONLY when it
      sees an ``ablation_control_effect`` event with ``is_real_model = True``.
      ``control_proof = present`` means a real matched control RAN; whether the
      target beat the controls is carried separately in ``selectivity_passed``
      for the verifier / human reviewer to weigh.
    """

    type: Literal["ablation_control_effect"] = "ablation_control_effect"
    target: dict[str, int] = Field(
        ...,
        description="The ablated target unit the random controls are compared against.",
    )
    mode: Literal["zero", "mean"] = "zero"
    is_real_model: bool = Field(
        default=False,
        description=(
            "True only when control deltas were measured on real loaded weights "
            "with at least one control unit ablated. False => demo-mode "
            "stand-in; numeric fields are None."
        ),
    )
    n_controls: int = Field(
        default=0,
        ge=0,
        description="Number of random same-layer control units actually measured.",
    )
    control_units: list[int] | None = Field(
        default=None,
        description="The sampled control unit indices (same layer as the target).",
    )
    target_abs_logit_delta: float | None = Field(
        default=None,
        description=(
            "Absolute change in the baseline-top-token's logit when the TARGET "
            "unit is ablated (|ablated - baseline|). None in demo mode."
        ),
    )
    control_mean_abs_logit_delta: float | None = Field(
        default=None,
        description="Mean |logit delta| across the random control units. None in demo mode.",
    )
    control_max_abs_logit_delta: float | None = Field(
        default=None,
        description="Largest |logit delta| across the random control units. None in demo mode.",
    )
    margin_over_control_max: float | None = Field(
        default=None,
        description=(
            "target_abs_logit_delta - control_max_abs_logit_delta. Positive "
            "means the target moved the baseline-top token more than every "
            "control did. None in demo mode."
        ),
    )
    selectivity_passed: bool | None = Field(
        default=None,
        description=(
            "True iff the target's |logit delta| strictly exceeds every "
            "control's. None in demo mode (no measurement was taken)."
        ),
    )
    seed: int | None = Field(
        default=None,
        description="RNG seed used to sample the control units (reproducibility).",
    )
    detail: str | None = Field(
        default=None,
        description="Human-readable note, e.g. why a demo event carries no measurement.",
    )


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
    | AblationEffectEvent
    | AblationControlEffectEvent
    | WordSpansEvent
    | ErrorEvent
    | CompleteEvent
)
