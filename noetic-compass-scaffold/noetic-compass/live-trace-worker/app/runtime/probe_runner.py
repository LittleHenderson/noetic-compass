"""Probe runner — real forward-hook capture for Pythia-160M.

Captures, per emitted token:
  * the activated MLP intermediate immediately before the selected binding's
    MLP down-projection (3,072 -> 768 at dense_4h_to_h for Pythia-160M;
    4,864 -> 896 at down_proj for pinned Qwen2.5-0.5B-Instruct)
  * attention patterns (for Mode 7 attribution: edges from earlier tokens
    to the current one, weighted by attention)
  * lm_head logits (for the softmax-margin confidence)

The Stage-27F eraser uses a forward pre-hook on dense_4h_to_h input[0]. It
never reinterprets those coordinates on the post-projection MLP output.
Hooks are removed on every exit path.
"""

from __future__ import annotations

import hashlib
import logging
import math
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Literal

from ..schemas.events import (
    EraserInterventionResult,
    InterventionCoordinate,
    InterventionTensorGeometry,
)
from ..schemas.manifest import ModelExecutionKind
from .cover_library import MLP_INTERMEDIATE_POST_ACTIVATION
from .model_loader import (
    ModelBinding,
    PYTHIA_160M_BINDING_KEY,
    active_model_binding,
    probe_hook_module_path,
    resolve_probe_layer_stack,
    resolve_probe_projection,
)

logger = logging.getLogger(__name__)

ProbeName = Literal[
    "active_trace",
    "blindspot_covers",
    "blindspots_f1",
    "mode7_attribution",
    "confidence_margin",
]

DEFAULT_PROBES: tuple[ProbeName, ...] = (
    "active_trace",
    "blindspot_covers",
    "mode7_attribution",
    "confidence_margin",
)

LEGACY_PROBE_ALIASES: dict[ProbeName, ProbeName] = {
    "blindspots_f1": "blindspot_covers",
}


def resolve_probes(requested: list[ProbeName]) -> tuple[ProbeName, ...]:
    """Empty request = default pipeline. Explicit list = only those probes."""
    if not requested:
        return DEFAULT_PROBES
    seen: set[ProbeName] = set()
    out: list[ProbeName] = []
    for p in requested:
        canonical = LEGACY_PROBE_ALIASES.get(p, p)
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return tuple(out)


# ---------------------------------------------------------------------------
# Capture state — populated by the forward hooks during a single forward pass.
# ---------------------------------------------------------------------------


@dataclass
class CaptureState:
    """One forward-pass worth of captured tensors.

    Lists are indexed by layer (0..n_layers-1). Each entry is a Python
    list of floats — the conversion from torch.Tensor happens inside the
    hook so the caller never holds a Tensor reference and CUDA memory is
    released promptly.
    """

    # mlp_post[layer] is a list[float] of length mlp_intermediate_dim
    # (3072 for Pythia-160M) — the per-token MLP post-activation across
    # the intermediate dimension at the final-prompt-token position.
    mlp_post: dict[int, list[float]] = field(default_factory=dict)
    # attention_pattern[layer] is a list[list[float]] shape [seq, seq]
    # (NOT averaged across heads — we keep the per-layer attention map
    # collapsed to mean-over-heads for size).
    attention_pattern: dict[int, list[list[float]]] = field(default_factory=dict)
    # logits at the last token position — shape [vocab].
    logits: list[float] | None = None
    # Exact geometry of the activated input to dense_4h_to_h. For Pythia-160M
    # the width is 3072; this is not the 768-wide projected MLP output.
    tensor_geometry: dict[int, InterventionTensorGeometry] = field(default_factory=dict)
    hook_call_counts: dict[int, int] = field(default_factory=dict)
    rng_state_sha256: str = "UNAVAILABLE"
    rng_state_after_sha256: str = "UNAVAILABLE"
    intervention_receipt: _MutableInterventionReceipt | None = None


@dataclass(frozen=True)
class TorchRngSnapshot:
    """Cloned global Torch RNG state used to pair counterfactual forwards."""

    cpu_state: Any
    cuda_states: tuple[Any, ...]


def snapshot_torch_rng_state() -> TorchRngSnapshot:
    """Snapshot CPU and all available CUDA generators without retaining aliases."""
    import torch

    cpu_state = torch.get_rng_state().clone()
    cuda_states: tuple[Any, ...] = ()
    if torch.cuda.is_available():
        cuda_states = tuple(state.clone() for state in torch.cuda.get_rng_state_all())
    return TorchRngSnapshot(cpu_state=cpu_state, cuda_states=cuda_states)


def restore_torch_rng_state(snapshot: TorchRngSnapshot) -> None:
    """Restore a snapshot exactly; fail rather than silently pair unlike RNGs."""
    import torch

    torch.set_rng_state(snapshot.cpu_state.clone())
    if snapshot.cuda_states:
        if not torch.cuda.is_available():
            raise RuntimeError("captured CUDA RNG state cannot be restored without CUDA")
        if len(snapshot.cuda_states) != torch.cuda.device_count():
            raise RuntimeError("CUDA RNG snapshot device count changed")
        torch.cuda.set_rng_state_all([state.clone() for state in snapshot.cuda_states])


def torch_rng_state_sha256(snapshot: TorchRngSnapshot | None = None) -> str:
    """Hash exact cloned global Torch generator bytes with device boundaries."""
    captured = snapshot if snapshot is not None else snapshot_torch_rng_state()
    digest = hashlib.sha256()
    states = (("cpu", captured.cpu_state),) + tuple(
        (f"cuda:{index}", state)
        for index, state in enumerate(captured.cuda_states)
    )
    for label, state in states:
        payload = bytes(state.detach().cpu().reshape(-1).tolist())
        label_bytes = label.encode("ascii")
        digest.update(len(label_bytes).to_bytes(4, "big"))
        digest.update(label_bytes)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


@dataclass(frozen=True)
class EraserIntervention:
    """Explicitly typed activated-intermediate suppression request."""

    coords: tuple[tuple[int, int], ...]
    gain: float
    coordinate_space: str
    execution_kind: ModelExecutionKind
    source_kind: Literal["stage27f_calibrated_cover", "typed_test_fixture"]
    expected_coordinate_width: int
    expected_projected_output_width: int

    def __post_init__(self) -> None:
        if (
            type(self.expected_coordinate_width) is not int
            or self.expected_coordinate_width < 1
            or type(self.expected_projected_output_width) is not int
            or self.expected_projected_output_width < 1
        ):
            raise TypeError("eraser tensor widths must be positive exact integers")
        for coord in self.coords:
            if (
                type(coord) is not tuple
                or len(coord) != 2
                or type(coord[0]) is not int
                or type(coord[1]) is not int
            ):
                raise TypeError("eraser coordinates must be exact (int, int) tuples")


@dataclass
class _MutableInterventionReceipt:
    intervention: EraserIntervention
    structural_status: str = "PENDING_OUTPUT_ATTESTATION"
    structurally_valid: bool = False
    effective_gain: float | None = None
    requested_gain: float | None = None
    hook_fired: bool = False
    observed_tensor_geometry: dict[int, InterventionTensorGeometry] = field(
        default_factory=dict
    )
    reference_tensor_geometry: dict[int, InterventionTensorGeometry] = field(
        default_factory=dict
    )
    stability_control_tensor_geometry: dict[int, InterventionTensorGeometry] = field(
        default_factory=dict
    )
    requested_coordinates: list[InterventionCoordinate] = field(default_factory=list)
    valid_coordinates: list[InterventionCoordinate] = field(default_factory=list)
    invalid_coordinates: list[InterventionCoordinate] = field(default_factory=list)
    applied_coordinates: list[InterventionCoordinate] = field(default_factory=list)
    fired_layers: set[int] = field(default_factory=set)
    activation_changed: bool | None = None
    output_changed: bool | None = None
    stability_control_performed: bool = False
    baseline_output_stable: bool | None = None
    baseline_geometry_stable: bool | None = None
    detail: str = "intervention result has not been finalized"

    @property
    def target_layers(self) -> set[int]:
        return {item.layer for item in self.valid_coordinates}

    @property
    def required_layers(self) -> set[int]:
        return {item.layer for item in self.requested_coordinates if item.layer >= 0}

    def public_result(self) -> EraserInterventionResult:
        if self.structural_status == "PENDING_OUTPUT_ATTESTATION":
            raise RuntimeError("intervention result is missing output attestation")
        return EraserInterventionResult(
            execution_kind=self.intervention.execution_kind,
            source_kind=self.intervention.source_kind,
            structural_status=self.structural_status,
            structurally_valid=self.structurally_valid,
            coordinate_space=self.intervention.coordinate_space,
            requested_gain=self.requested_gain,
            effective_gain=self.effective_gain,
            expected_coordinate_width=self.intervention.expected_coordinate_width,
            expected_projected_output_width=(
                self.intervention.expected_projected_output_width
            ),
            hook_fired=self.hook_fired,
            required_hook_layers=sorted(self.required_layers),
            hook_fired_layers=sorted(self.fired_layers),
            observed_tensor_geometry=[
                self.observed_tensor_geometry[layer]
                for layer in sorted(self.observed_tensor_geometry)
            ],
            reference_tensor_geometry=[
                self.reference_tensor_geometry[layer]
                for layer in sorted(self.reference_tensor_geometry)
            ],
            stability_control_tensor_geometry=[
                self.stability_control_tensor_geometry[layer]
                for layer in sorted(self.stability_control_tensor_geometry)
            ],
            requested_coordinates=self.requested_coordinates,
            valid_coordinates=self.valid_coordinates,
            invalid_coordinates=self.invalid_coordinates,
            applied_coordinates=self.applied_coordinates,
            activation_changed=self.activation_changed,
            output_changed=self.output_changed,
            stability_control_performed=self.stability_control_performed,
            baseline_output_stable=self.baseline_output_stable,
            baseline_geometry_stable=self.baseline_geometry_stable,
            detail=self.detail,
        )


# ---------------------------------------------------------------------------
# Hook registration — context manager so cleanup is always called.
# ---------------------------------------------------------------------------


@contextmanager
def capture_probes(
    model: Any,
    n_layers: int,
    intervention: EraserIntervention | None = None,
    *,
    reference_geometry: dict[int, InterventionTensorGeometry] | None = None,
    probe_binding: ModelBinding | None = None,
) -> Iterator[CaptureState]:
    """Register forward hooks on the model, yield a CaptureState, clean up.

    Hooks attach to the exact selected binding's down-projection input[0] via a
    forward pre-hook: the activated intermediate, pre-projection tensor.
    Pythia remains ``model.gpt_neox.layers[i].mlp.dense_4h_to_h``; the pinned
    Qwen binding uses ``model.model.layers[i].mlp.down_proj``. Attention data
    is read separately from the model's ``output_attentions=True`` return.

    Important: we DO NOT hold tensor references after the hook fires. The
    hook converts to Python lists immediately so that when the
    ``capture_probes`` block exits, no GPU memory is retained.
    """
    binding = probe_binding or active_model_binding()
    if intervention is not None and not binding.stage27f_intervention_supported:
        raise RuntimeError(
            "selected model binding has no Stage-27F coordinate adapter; "
            f"intervention refused for {binding.key}"
        )

    handles: list[Any] = []
    rng_snapshot = snapshot_torch_rng_state()
    state = CaptureState(rng_state_sha256=torch_rng_state_sha256(rng_snapshot))
    if intervention is not None:
        state.intervention_receipt = _preflight_intervention(
            intervention,
            reference_geometry=reference_geometry,
        )

    try:
        if binding.key == PYTHIA_160M_BINDING_KEY:
            # Preserve the historical Pythia lookup, partial-stack test-fixture
            # behavior, and fail-closed intervention receipts byte-for-byte.
            layers = _get_pythia_layers(model)
            layer_projections: list[tuple[int, Any]] = []
            if layers is None:
                logger.warning(
                    "capture_probes: could not locate gpt_neox.layers; "
                    "MLP-post capture will be empty"
                )
            else:
                for layer_idx in range(min(n_layers, len(layers))):
                    mlp = getattr(layers[layer_idx], "mlp", None)
                    projection = getattr(mlp, "dense_4h_to_h", None)
                    if projection is None or not hasattr(
                        projection, "register_forward_pre_hook"
                    ):
                        continue
                    layer_projections.append((layer_idx, projection))
        else:
            # The additive Qwen path is strict: selected architecture, exact
            # down-projection, and declared 4,864 -> 896 geometry only.
            layers = resolve_probe_layer_stack(
                model,
                binding,
                expected_layers=n_layers,
            )
            layer_projections = [
                (
                    layer_idx,
                    resolve_probe_projection(
                        layers[layer_idx],
                        binding,
                        layer_index=layer_idx,
                    ),
                )
                for layer_idx in range(n_layers)
            ]

        for layer_idx, projection in layer_projections:
            handle = projection.register_forward_pre_hook(
                _make_intermediate_pre_hook(
                    state,
                    layer_idx,
                    projection,
                    observation_phase=(
                        "intervention_attempt"
                        if intervention is not None
                        else "unmodified_forward"
                    ),
                    hook_module_path=probe_hook_module_path(binding, layer_idx),
                ),
            )
            handles.append(handle)
        yield state
    finally:
        _seal_rng_geometry(state)
        _close_hook_attestation(state)
        for h in handles:
            try:
                h.remove()
            except Exception:  # pragma: no cover — defensive cleanup
                logger.exception("capture_probes: hook removal failed")


def _coord(layer: int, index: int, coordinate_space: str) -> InterventionCoordinate:
    return InterventionCoordinate(
        layer=layer,
        index=index,
        coordinate_space=coordinate_space,
    )


def _finite_float(value: Any) -> float | None:
    if type(value) is bool:
        return None
    try:
        normalized = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return normalized if math.isfinite(normalized) else None


def _is_sha256(value: str) -> bool:
    return bool(
        len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _expected_hook_path(layer: int) -> str:
    return f"gpt_neox.layers[{layer}].mlp.dense_4h_to_h"


def _preflight_intervention(
    intervention: EraserIntervention,
    *,
    reference_geometry: dict[int, InterventionTensorGeometry] | None,
) -> _MutableInterventionReceipt:
    """Classify every coordinate before any intervention hook can apply."""
    receipt = _MutableInterventionReceipt(intervention=intervention)
    seen: set[tuple[int, int]] = set()
    for layer, index in intervention.coords:
        key = (layer, index)
        if key in seen:
            continue
        seen.add(key)
        receipt.requested_coordinates.append(
            _coord(layer, index, intervention.coordinate_space)
        )

    if not receipt.requested_coordinates:
        receipt.structural_status = "REJECTED_NO_COORDINATES"
        receipt.detail = "no calibrated coordinates were supplied; nothing was applied"
        return receipt

    gain = _finite_float(intervention.gain)
    receipt.requested_gain = gain
    if gain is None or gain < 0.0:
        receipt.structural_status = "REJECTED_INVALID_GAIN"
        receipt.invalid_coordinates = list(receipt.requested_coordinates)
        receipt.detail = "gain must be a finite non-negative number"
        return receipt
    receipt.effective_gain = min(1.0, gain)

    if intervention.coordinate_space != MLP_INTERMEDIATE_POST_ACTIVATION:
        receipt.structural_status = "REJECTED_WRONG_COORDINATE_SPACE"
        receipt.invalid_coordinates = list(receipt.requested_coordinates)
        receipt.detail = (
            "coordinates were not declared in mlp_intermediate_post_activation space"
        )
        return receipt

    if reference_geometry is None:
        receipt.structural_status = "REJECTED_MISSING_PREFLIGHT"
        receipt.invalid_coordinates = list(receipt.requested_coordinates)
        receipt.detail = "an unmodified reference forward pass is required"
        return receipt

    requested_layers = {item.layer for item in receipt.requested_coordinates}
    missing_reference_layers = requested_layers - set(reference_geometry)
    receipt.reference_tensor_geometry = {
        layer: reference_geometry[layer]
        for layer in requested_layers
        if layer in reference_geometry
    }
    receipt.observed_tensor_geometry = {
        layer: reference_geometry[layer]
        for layer in requested_layers
        if layer in reference_geometry
    }
    if missing_reference_layers:
        receipt.structural_status = "REJECTED_HOOK_CONTRACT"
        receipt.invalid_coordinates = list(receipt.requested_coordinates)
        receipt.detail = (
            "the unmodified forward pass did not observe every required "
            "dense_4h_to_h activated-intermediate hook"
        )
        return receipt

    if any(
        not reference_geometry[layer].all_finite
        for layer in requested_layers
    ):
        receipt.structural_status = "REJECTED_NONFINITE_TENSOR"
        receipt.invalid_coordinates = list(receipt.requested_coordinates)
        receipt.detail = "the unmodified hook observed a non-finite activation"
        return receipt

    for item in receipt.requested_coordinates:
        geometry = reference_geometry.get(item.layer)
        expected_path = _expected_hook_path(item.layer)
        geometry_is_valid = bool(
            geometry is not None
            and geometry.rank == 3
            and len(geometry.shape) == 3
            and geometry.shape[0] >= 1
            and geometry.shape[1] >= 1
            and geometry.width == intervention.expected_coordinate_width
            and geometry.projected_output_width
            == intervention.expected_projected_output_width
            and geometry.coordinate_space == MLP_INTERMEDIATE_POST_ACTIVATION
            and geometry.observation_phase == "unmodified_forward"
            and geometry.hook_module_path == expected_path
            and geometry.tensor_role == "forward_pre_hook.input[0]"
            and geometry.dtype != "UNKNOWN"
            and geometry.device != "UNKNOWN"
            and _is_sha256(geometry.rng_state_sha256)
            and _is_sha256(geometry.rng_state_after_sha256)
        )
        coordinate_is_valid = bool(
            geometry_is_valid
            and item.layer >= 0
            and item.index >= 0
            and item.index < geometry.width
        )
        if coordinate_is_valid:
            receipt.valid_coordinates.append(item)
        else:
            receipt.invalid_coordinates.append(item)

    if receipt.invalid_coordinates:
        if receipt.valid_coordinates:
            receipt.structural_status = "REJECTED_PARTIALLY_INVALID_COORDINATES"
            receipt.detail = (
                "at least one coordinate was invalid; fail-closed policy applied none"
            )
        else:
            receipt.structural_status = "REJECTED_ALL_COORDINATES_INVALID"
            receipt.detail = (
                "all coordinates were outside the observed hook contract; none applied"
            )
        return receipt

    receipt.detail = "coordinate preflight passed; awaiting hook and output attestation"
    return receipt


def _projection_output_width(projection: Any) -> int:
    observed = getattr(projection, "out_features", None)
    if type(observed) is not int or observed < 1:
        raise ValueError("dense_4h_to_h must expose a positive exact out_features")
    return observed


def _observed_geometry(
    activation: Any,
    layer_idx: int,
    projection: Any,
    observation_phase: Literal["unmodified_forward", "intervention_attempt"],
    *,
    rng_state_sha256: str,
    hook_call_count: int,
    hook_module_path: str,
) -> InterventionTensorGeometry:
    shape = [int(value) for value in activation.shape]
    if len(shape) != 3 or min(shape) < 1:
        raise ValueError("intervention tensor must have [batch, sequence, width] geometry")
    in_features = getattr(projection, "in_features", None)
    if type(in_features) is not int or in_features != shape[-1]:
        raise ValueError("dense_4h_to_h in_features does not match observed input width")
    try:
        import torch

        all_finite = bool(torch.isfinite(activation).all().item())
    except Exception as exc:
        raise ValueError("intervention tensor finiteness could not be established") from exc
    return InterventionTensorGeometry(
        layer=layer_idx,
        shape=shape,
        rank=len(shape),
        width=shape[-1],
        projected_output_width=_projection_output_width(projection),
        observation_phase=observation_phase,
        hook_module_path=hook_module_path,
        dtype=str(activation.dtype),
        device=str(activation.device),
        all_finite=all_finite,
        rng_state_sha256=rng_state_sha256,
        hook_call_count=hook_call_count,
    )


def _same_geometry(
    left: InterventionTensorGeometry,
    right: InterventionTensorGeometry,
) -> bool:
    return bool(
        left.shape == right.shape
        and left.rank == right.rank
        and left.width == right.width
        and left.projected_output_width == right.projected_output_width
        and left.coordinate_space == right.coordinate_space
        and left.tensor_role == right.tensor_role
        and left.observation_phase == "unmodified_forward"
        and right.observation_phase == "intervention_attempt"
        and left.hook_module_path == _expected_hook_path(left.layer)
        and right.hook_module_path == _expected_hook_path(right.layer)
        and left.layer == right.layer
        and left.dtype == right.dtype
        and left.device == right.device
        and left.all_finite
        and right.all_finite
    )


def _capture_last_activation(state: CaptureState, layer_idx: int, activation: Any) -> None:
    last = activation[0, -1].detach()
    state.mlp_post[layer_idx] = [
        float(value) for value in last.float().cpu().tolist()
    ]


def _make_intermediate_pre_hook(
    state: CaptureState,
    layer_idx: int,
    projection: Any,
    observation_phase: Literal["unmodified_forward", "intervention_attempt"],
    *,
    hook_module_path: str,
) -> Any:
    """Capture and, only after global preflight, alter the 4h activation."""

    def _hook(_module: Any, inputs: Any) -> Any:
        receipt = state.intervention_receipt
        try:
            if type(inputs) is not tuple or not inputs:
                raise ValueError("dense_4h_to_h hook received no positional activation")
            activation = inputs[0]
            hook_call_count = state.hook_call_counts.get(layer_idx, 0) + 1
            state.hook_call_counts[layer_idx] = hook_call_count
            geometry = _observed_geometry(
                activation,
                layer_idx,
                projection,
                observation_phase,
                rng_state_sha256=state.rng_state_sha256,
                hook_call_count=hook_call_count,
                hook_module_path=hook_module_path,
            )
            state.tensor_geometry[layer_idx] = geometry

            requested_layers = (
                {item.layer for item in receipt.requested_coordinates}
                if receipt is not None
                else set()
            )
            if receipt is not None and layer_idx in requested_layers:
                expected = receipt.observed_tensor_geometry.get(layer_idx)
                receipt.observed_tensor_geometry[layer_idx] = geometry
                if receipt.structural_status == "PENDING_OUTPUT_ATTESTATION":
                    receipt.fired_layers.add(layer_idx)
                if (
                    receipt.structural_status == "PENDING_OUTPUT_ATTESTATION"
                    and hook_call_count != 1
                ):
                    receipt.structural_status = "REJECTED_HOOK_CARDINALITY"
                    receipt.detail = "each required intervention hook must fire exactly once"
                if (
                    receipt.structural_status == "PENDING_OUTPUT_ATTESTATION"
                    and not geometry.all_finite
                ):
                    receipt.structural_status = "REJECTED_NONFINITE_TENSOR"
                    receipt.detail = "the intervention hook observed a non-finite activation"
                if (
                    receipt.structural_status == "PENDING_OUTPUT_ATTESTATION"
                    and (expected is None or not _same_geometry(expected, geometry))
                ):
                    receipt.structural_status = "REJECTED_RUNTIME_GEOMETRY"
                    receipt.detail = (
                        "intervention-pass tensor geometry differed from preflight"
                    )

            if (
                receipt is None
                or receipt.structural_status != "PENDING_OUTPUT_ATTESTATION"
                or layer_idx not in receipt.target_layers
            ):
                _capture_last_activation(state, layer_idx, activation)
                return None

            import torch

            modified = activation.clone()
            factor = 1.0 - float(receipt.effective_gain)
            layer_coordinates = [
                item for item in receipt.valid_coordinates if item.layer == layer_idx
            ]
            for item in layer_coordinates:
                modified[0, -1, item.index] = (
                    modified[0, -1, item.index] * factor
                )
                if item not in receipt.applied_coordinates:
                    receipt.applied_coordinates.append(item)
            changed = not torch.equal(activation, modified)
            receipt.activation_changed = bool(receipt.activation_changed or changed)
            _capture_last_activation(state, layer_idx, modified)
            return (modified, *inputs[1:])
        except Exception as exc:
            if receipt is not None:
                receipt.structural_status = "REJECTED_RUNTIME_GEOMETRY"
                receipt.structurally_valid = False
                receipt.detail = f"intervention hook failed closed: {type(exc).__name__}"
            logger.exception("activated-intermediate hook failed at layer %d", layer_idx)
            return None

    return _hook


def _seal_rng_geometry(state: CaptureState) -> None:
    """Bind post-forward RNG state into every observed geometry and compare pairs."""
    state.rng_state_after_sha256 = torch_rng_state_sha256()
    for layer, geometry in tuple(state.tensor_geometry.items()):
        updated = geometry.model_copy(
            update={"rng_state_after_sha256": state.rng_state_after_sha256}
        )
        state.tensor_geometry[layer] = updated
        receipt = state.intervention_receipt
        if receipt is not None and layer in receipt.observed_tensor_geometry:
            receipt.observed_tensor_geometry[layer] = updated

    receipt = state.intervention_receipt
    if receipt is None or receipt.structural_status != "PENDING_OUTPUT_ATTESTATION":
        return
    for layer in receipt.required_layers:
        reference = receipt.reference_tensor_geometry.get(layer)
        observed = state.tensor_geometry.get(layer)
        if reference is None or observed is None:
            continue
        if reference.hook_call_count != 1 or observed.hook_call_count != 1:
            receipt.structural_status = "REJECTED_HOOK_CARDINALITY"
            receipt.structurally_valid = False
            receipt.detail = "each paired required hook must fire exactly once"
            return
        if (
            reference.rng_state_sha256 != observed.rng_state_sha256
            or reference.rng_state_after_sha256 != observed.rng_state_after_sha256
        ):
            receipt.structural_status = "REJECTED_RNG_STATE_MISMATCH"
            receipt.structurally_valid = False
            receipt.detail = (
                "baseline and intervention forwards did not end in the same Torch RNG state"
            )
            return


def _close_hook_attestation(state: CaptureState) -> None:
    receipt = state.intervention_receipt
    if receipt is None:
        return
    required = receipt.required_layers
    receipt.hook_fired = bool(required) and required <= receipt.fired_layers
    if (
        receipt.structural_status == "PENDING_OUTPUT_ATTESTATION"
        and not receipt.hook_fired
    ):
        receipt.structural_status = "HOOK_NOT_FIRED"
        receipt.detail = "one or more required intervention hooks did not fire"


def _tensor_changed(left: Any, right: Any) -> bool | None:
    try:
        import torch

        if not isinstance(left, torch.Tensor) or not isinstance(right, torch.Tensor):
            return None
        left_tensor = left.detach()
        right_tensor = right.detach()
        if (
            left_tensor.shape != right_tensor.shape
            or left_tensor.dtype != right_tensor.dtype
            or left_tensor.device != right_tensor.device
            or left_tensor.layout != right_tensor.layout
        ):
            return None
        if not bool(torch.isfinite(left_tensor).all().item()) or not bool(
            torch.isfinite(right_tensor).all().item()
        ):
            return None
        return not torch.equal(left_tensor, right_tensor)
    except Exception:
        logger.exception("could not compare baseline and intervention outputs")
        return None


def _same_unmodified_geometry(
    left: InterventionTensorGeometry,
    right: InterventionTensorGeometry,
) -> bool:
    return bool(
        left.layer == right.layer
        and left.shape == right.shape
        and left.rank == right.rank
        and left.width == right.width
        and left.projected_output_width == right.projected_output_width
        and left.coordinate_space == right.coordinate_space
        and left.observation_phase == "unmodified_forward"
        and right.observation_phase == "unmodified_forward"
        and left.hook_module_path == _expected_hook_path(left.layer)
        and right.hook_module_path == _expected_hook_path(right.layer)
        and left.tensor_role == right.tensor_role == "forward_pre_hook.input[0]"
        and left.dtype == right.dtype
        and left.device == right.device
        and left.all_finite
        and right.all_finite
        and left.hook_call_count == right.hook_call_count == 1
        and left.rng_state_sha256 == right.rng_state_sha256
        and left.rng_state_after_sha256 == right.rng_state_after_sha256
    )


def assess_baseline_stability(
    baseline_state: CaptureState,
    baseline_output: Any,
    stability_control_state: CaptureState,
    stability_control_output: Any,
    required_layers: set[int],
) -> tuple[bool | None, bool]:
    """Compare two unmodified forwards before any intervention is attempted."""
    changed = _tensor_changed(baseline_output, stability_control_output)
    output_stable = None if changed is None else not changed
    geometry_stable = bool(required_layers) and all(
        layer in baseline_state.tensor_geometry
        and layer in stability_control_state.tensor_geometry
        and _same_unmodified_geometry(
            baseline_state.tensor_geometry[layer],
            stability_control_state.tensor_geometry[layer],
        )
        for layer in required_layers
    )
    return output_stable, geometry_stable


def mark_unstable_baseline_without_attempt(state: CaptureState) -> None:
    """Record that intervention execution was withheld after failed controls."""
    receipt = state.intervention_receipt
    if receipt is not None and receipt.structural_status == "PENDING_OUTPUT_ATTESTATION":
        receipt.structural_status = "REJECTED_UNSTABLE_BASELINE"
        receipt.structurally_valid = False
        receipt.detail = (
            "the intervention was not attempted because unmodified stability "
            "controls did not match exactly"
        )


def finalize_intervention_result(
    state: CaptureState,
    baseline_output: Any,
    intervention_output: Any,
    *,
    stability_control_state: CaptureState | None = None,
    stability_control_output: Any | None = None,
) -> EraserInterventionResult | None:
    """Bind hook evidence to a measured baseline-vs-intervention output delta."""
    receipt = state.intervention_receipt
    if receipt is None:
        return None
    _close_hook_attestation(state)
    receipt.output_changed = _tensor_changed(baseline_output, intervention_output)
    receipt.stability_control_performed = bool(
        stability_control_state is not None and stability_control_output is not None
    )
    if receipt.stability_control_performed:
        assert stability_control_state is not None
        receipt.stability_control_tensor_geometry = {
            layer: stability_control_state.tensor_geometry[layer]
            for layer in receipt.required_layers
            if layer in stability_control_state.tensor_geometry
        }
        (
            receipt.baseline_output_stable,
            receipt.baseline_geometry_stable,
        ) = assess_baseline_stability(
            CaptureState(tensor_geometry=receipt.reference_tensor_geometry),
            baseline_output,
            stability_control_state,
            stability_control_output,
            receipt.required_layers,
        )

    if receipt.structural_status == "PENDING_OUTPUT_ATTESTATION":
        if not receipt.stability_control_performed:
            receipt.structural_status = "REJECTED_MISSING_STABILITY_CONTROL"
            receipt.detail = "a second unmodified stability-control forward is required"
        elif (
            receipt.baseline_output_stable is not True
            or receipt.baseline_geometry_stable is not True
        ):
            receipt.structural_status = "REJECTED_UNSTABLE_BASELINE"
            receipt.detail = "paired unmodified forwards were not exactly stable"
        elif receipt.activation_changed is not True:
            receipt.structural_status = "ACTIVATION_UNCHANGED"
            receipt.detail = "valid coordinates were written but activation did not change"
        elif receipt.output_changed is None:
            receipt.structural_status = "OUTPUT_CHANGE_UNAVAILABLE"
            receipt.detail = "baseline/intervention output comparison was unavailable"
        elif receipt.output_changed is not True:
            receipt.structural_status = "OUTPUT_UNCHANGED"
            receipt.detail = "activation changed but the measured model output did not"
        else:
            receipt.structural_status = (
                "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
            )
            receipt.structurally_valid = False
            receipt.detail = (
                "coordinates changed the declared activation and a paired output delta "
                "was observed, but arbitrary mutable model state is not hermetically "
                "excluded; no causal application attestation is issued"
            )
    elif receipt.activation_changed is None and receipt.structural_status != "HOOK_NOT_FIRED":
        receipt.activation_changed = False

    return receipt.public_result()


def demo_intervention_result(
    intervention: EraserIntervention,
) -> EraserInterventionResult:
    """Emit an explicit non-measurement receipt for the schema-only fake stream."""
    requested = [
        _coord(layer, index, intervention.coordinate_space)
        for layer, index in dict.fromkeys(intervention.coords)
    ]
    gain = _finite_float(intervention.gain)
    effective_gain = min(1.0, gain) if gain is not None and gain >= 0.0 else None
    return EraserInterventionResult(
        execution_kind="demo_schema_only",
        source_kind="demo_schema_only",
        structural_status="DEMO_NOT_EXECUTED",
        structurally_valid=False,
        coordinate_space=intervention.coordinate_space,
        requested_gain=gain,
        effective_gain=effective_gain,
        expected_coordinate_width=intervention.expected_coordinate_width,
        expected_projected_output_width=intervention.expected_projected_output_width,
        hook_fired=False,
        required_hook_layers=[],
        hook_fired_layers=[],
        observed_tensor_geometry=[],
        requested_coordinates=requested,
        valid_coordinates=[],
        invalid_coordinates=[],
        applied_coordinates=[],
        activation_changed=None,
        output_changed=None,
        detail="demo_schema_only emitted no intervention measurement",
    )


def _get_pythia_layers(model: Any) -> Any | None:
    """Locate the transformer block list on a Pythia model.

    Returns ``model.gpt_neox.layers`` if present, otherwise None.
    """
    gpt_neox = getattr(model, "gpt_neox", None)
    if gpt_neox is None:
        return None
    return getattr(gpt_neox, "layers", None)


# ---------------------------------------------------------------------------
# Post-capture summarisation — converts CaptureState into the event-stream
# payloads the UI expects (top-K activations, Mode 7 edges, confidence).
# ---------------------------------------------------------------------------


@dataclass
class TokenProbeSummary:
    """One token's worth of probe-derived payloads, schema-friendly."""

    top_activated_neurons: list[dict]
    """List of {layer, index, activation} dicts. Top-K across the union of
    layer MLP-post vectors."""
    mode7_edges: list[dict]
    """List of {from_token_index, to_token_index, weight} dicts."""
    confidence: float | None
    """Softmax margin (top-1 minus top-2 logit), normalised into [0, 1]."""


def summarise(
    state: CaptureState,
    token_index: int,
    attentions: list[Any] | None,
    top_k: int = 8,
    layer_filter: set[int] | None = None,
) -> TokenProbeSummary:
    """Reduce a CaptureState to a TokenProbeSummary the event stream can ship.

    ``attentions`` comes from the model's forward output when
    ``output_attentions=True``. Each entry is a tensor of shape
    ``[batch, heads, seq, seq]``; we mean across heads and read the last
    row (the current token's attention back over the prompt).
    """
    return TokenProbeSummary(
        top_activated_neurons=_top_k_neurons(state, top_k, layer_filter),
        mode7_edges=_mode7_edges_from_attentions(attentions, token_index),
        confidence=_softmax_margin(state.logits),
    )


def _top_k_neurons(
    state: CaptureState,
    k: int,
    layer_filter: set[int] | None = None,
) -> list[dict]:
    """Top-K activated neurons across all hooked layers, by absolute value."""
    if not state.mlp_post:
        return []
    scored: list[tuple[int, int, float]] = []  # (layer, index, abs_act)
    for layer_idx, vec in state.mlp_post.items():
        if layer_filter is not None and layer_idx not in layer_filter:
            continue
        for n_idx, val in enumerate(vec):
            scored.append((layer_idx, n_idx, abs(float(val))))
    scored.sort(key=lambda t: t[2], reverse=True)
    out: list[dict] = []
    for layer_idx, n_idx, abs_act in scored[:k]:
        # Carry the raw (signed) activation forward, not the absolute value,
        # so the UI can paint excitatory vs inhibitory if it wants to.
        signed = float(state.mlp_post[layer_idx][n_idx])
        out.append({"layer": layer_idx, "index": n_idx, "activation": signed})
    return out


def _mode7_edges_from_attentions(
    attentions: list[Any] | None,
    token_index: int,
) -> list[dict]:
    """Derive Mode 7 arcs from the attention patterns at the final-prompt-token.

    Mean across heads, mean across layers, then keep the top edges by
    weight. Schema requires weight in [0, 1] (attention probs are already).
    The first token (token_index == 0) has a single self-edge.
    """
    if token_index == 0:
        return [{"from_token_index": None, "to_token_index": 0, "weight": 1.0}]
    if not attentions:
        return []
    try:
        # Reduce: stack layers -> mean over layers -> mean over heads.
        # Each attention tensor: [batch=1, heads, seq, seq]. We want the
        # row at position seq-1 (the predicting token) over earlier
        # positions [0..seq-2].
        # We deliberately avoid importing torch at module level; do it
        # locally so the module remains importable in demo mode.
        import torch

        stacked = torch.stack(
            [att.detach().to(dtype=torch.float32) for att in attentions],
            dim=0,
        )
        # stacked: [n_layers, 1, heads, seq, seq]
        mean = stacked.mean(dim=(0, 2))  # -> [1, seq, seq]
        last_row = mean[0, -1]  # [seq]
        weights = last_row[:-1].cpu().tolist()  # earlier-position weights
    except Exception:  # pragma: no cover
        logger.exception("mode7 attention reduce failed")
        return []

    if not weights:
        return []

    # Keep top-3 to match the offline trace's typical Mode 7 footprint.
    indexed = [(i, float(w)) for i, w in enumerate(weights)]
    indexed.sort(key=lambda t: t[1], reverse=True)
    top = indexed[:3]
    return [
        {
            "from_token_index": int(i),
            "to_token_index": int(token_index),
            "weight": max(0.0, min(1.0, round(float(w), 4))),
        }
        for i, w in top
    ]


def _softmax_margin(logits: list[float] | None) -> float | None:
    """Top-1 minus top-2 logit, normalised into [0, 1].

    Normalisation: a logit-margin of 0 -> confidence 0; logit-margin of
    >= MARGIN_SAT -> confidence 1. The saturation point is set empirically;
    Pythia-160M margins on confident next-tokens land in the 4-8 range.
    """
    if not logits:
        return None
    top2 = sorted(logits, reverse=True)[:2]
    if len(top2) < 2:
        return 1.0
    margin = float(top2[0] - top2[1])
    MARGIN_SAT = 6.0
    norm = max(0.0, min(1.0, margin / MARGIN_SAT))
    return round(norm, 3)
