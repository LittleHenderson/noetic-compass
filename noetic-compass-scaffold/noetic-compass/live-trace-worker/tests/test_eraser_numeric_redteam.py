"""Independent adversarial tests for Stage-27F numeric attestation.

Every model below is a small, typed torch fixture.  No pretrained weights,
tokenizer files, provider calls, network access, or paid compute are used.
The tests deliberately distinguish a hook write from evidence that the write
caused a comparable baseline/intervention output change.
"""

from __future__ import annotations

import asyncio
import json
import math
from types import SimpleNamespace
from typing import Any

import pytest
import torch
from torch import nn

from app.runtime import pythia_runner
from app.runtime.cover_library import coords_for_drive
from app.runtime.probe_runner import (
    EraserIntervention,
    capture_probes,
    finalize_intervention_result,
)
from app.schemas.events import InterventionTensorGeometry, TokenEvent
from app.schemas.requests import CreateSessionRequest


INTERMEDIATE_WIDTH = 3072
PROJECTED_WIDTH = 768
TARGET_LAYER = 5
TARGET_COORDINATE = 2346


class _Projection(nn.Module):
    def __init__(self, *, map_target: bool = True) -> None:
        super().__init__()
        self.in_features = INTERMEDIATE_WIDTH
        self.out_features = PROJECTED_WIDTH
        self.map_target = map_target

    def forward(self, activation: torch.Tensor) -> torch.Tensor:
        output = activation[..., :PROJECTED_WIDTH].clone()
        if self.map_target:
            output[..., 0] = output[..., 0] + activation[..., TARGET_COORDINATE]
        return output


class _MLP(nn.Module):
    def __init__(self, *, map_target: bool = True) -> None:
        super().__init__()
        self.dense_4h_to_h = _Projection(map_target=map_target)

    def forward(self, activation: torch.Tensor) -> torch.Tensor:
        return self.dense_4h_to_h(activation)


class _Layer(nn.Module):
    def __init__(self, *, map_target: bool = True) -> None:
        super().__init__()
        self.mlp = _MLP(map_target=map_target)


class _NeoX(nn.Module):
    def __init__(self, *, map_target: bool = True) -> None:
        super().__init__()
        self.layers = nn.ModuleList(
            [
                _Layer(map_target=map_target)
                for _ in range(TARGET_LAYER + 1)
            ]
        )


class _GeometryFixture(nn.Module):
    def __init__(
        self,
        *,
        map_target: bool = True,
        random_output: bool = False,
        shift_output_shape: bool = False,
        repeat_target_hook: bool = False,
    ) -> None:
        super().__init__()
        self.gpt_neox = _NeoX(map_target=map_target)
        self.random_output = random_output
        self.shift_output_shape = shift_output_shape
        self.repeat_target_hook = repeat_target_hook
        self.forward_count = 0

    def forward(self, activation: torch.Tensor) -> torch.Tensor:
        self.forward_count += 1
        outputs: list[torch.Tensor] = []
        for layer_index, layer in enumerate(self.gpt_neox.layers):
            outputs.append(layer.mlp(activation))
            if self.repeat_target_hook and layer_index == TARGET_LAYER:
                outputs.append(layer.mlp(activation))
        combined = torch.stack(outputs).sum(dim=0)
        if self.random_output:
            return torch.rand(
                (*activation.shape[:-1], 4),
                dtype=activation.dtype,
                device=activation.device,
            )
        if self.shift_output_shape:
            width = 4 if self.forward_count == 1 else 5
            return combined[..., :width]
        return combined


class _MutableCounterOutputFixture(_GeometryFixture):
    """Changes output through model state while leaving global Torch RNG exact."""

    def forward(self, activation: torch.Tensor) -> torch.Tensor:
        self.forward_count += 1
        for layer in self.gpt_neox.layers:
            layer.mlp(activation)
        return torch.full(
            (*activation.shape[:-1], 4),
            float(self.forward_count),
            dtype=activation.dtype,
            device=activation.device,
        )


def _intervention(
    *,
    coords: tuple[tuple[int, int], ...] = ((TARGET_LAYER, TARGET_COORDINATE),),
    gain: Any = 1.0,
) -> EraserIntervention:
    return EraserIntervention(
        coords=coords,
        gain=gain,
        coordinate_space="mlp_intermediate_post_activation",
        execution_kind="typed_test_fixture",
        source_kind="typed_test_fixture",
        expected_coordinate_width=INTERMEDIATE_WIDTH,
        expected_projected_output_width=PROJECTED_WIDTH,
    )


def _run_pair(
    model: nn.Module,
    baseline_activation: torch.Tensor,
    intervention: EraserIntervention | None = None,
    *,
    intervention_activation: torch.Tensor | None = None,
    reference_geometry: dict[int, InterventionTensorGeometry] | None = None,
):
    intervention = intervention or _intervention()
    with capture_probes(model, TARGET_LAYER + 1) as baseline_state:
        baseline_output = model(baseline_activation)
    with capture_probes(model, TARGET_LAYER + 1) as stability_control_state:
        stability_control_output = model(baseline_activation)
    if reference_geometry is None:
        reference_geometry = baseline_state.tensor_geometry
    attempted_activation = (
        baseline_activation
        if intervention_activation is None
        else intervention_activation
    )
    with capture_probes(
        model,
        TARGET_LAYER + 1,
        intervention=intervention,
        reference_geometry=reference_geometry,
    ) as attempted_state:
        attempted_output = model(attempted_activation)
    result = finalize_intervention_result(
        attempted_state,
        baseline_output,
        attempted_output,
        stability_control_state=stability_control_state,
        stability_control_output=stability_control_output,
    )
    assert result is not None
    return result, baseline_output, attempted_output, baseline_state, attempted_state


def _ones(*, dtype: torch.dtype = torch.float32) -> torch.Tensor:
    return torch.ones((1, 2, INTERMEDIATE_WIDTH), dtype=dtype)


def test_rng_only_output_drift_cannot_attest_intervention_causality() -> None:
    torch.manual_seed(17)
    model = _GeometryFixture(map_target=False, random_output=True)

    result, baseline, attempted, _, _ = _run_pair(model, _ones())

    assert not torch.equal(baseline, attempted)
    assert result.activation_changed is True
    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


def test_model_state_only_output_drift_cannot_attest_intervention_causality() -> None:
    model = _MutableCounterOutputFixture(map_target=False)

    result, baseline, attempted, baseline_state, attempted_state = _run_pair(
        model,
        _ones(),
    )

    assert not torch.equal(baseline, attempted)
    assert baseline_state.rng_state_sha256 == attempted_state.rng_state_sha256
    assert (
        baseline_state.rng_state_after_sha256
        == attempted_state.rng_state_after_sha256
    )
    assert result.activation_changed is True
    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


@pytest.mark.parametrize("nonfinite", [math.nan, math.inf, -math.inf])
def test_nonfinite_activation_or_output_never_counts_as_measured_change(
    nonfinite: float,
) -> None:
    activation = _ones()
    activation[0, -1, TARGET_COORDINATE] = nonfinite

    result, _, _, _, _ = _run_pair(_GeometryFixture(), activation)

    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


def test_reference_geometry_requires_unmodified_phase_and_exact_hook_path() -> None:
    model = _GeometryFixture()
    activation = _ones()
    with capture_probes(model, TARGET_LAYER + 1) as baseline_state:
        model(activation)
    observed = baseline_state.tensor_geometry[TARGET_LAYER]
    forged_reference = {
        TARGET_LAYER: InterventionTensorGeometry(
            layer=TARGET_LAYER,
            shape=list(observed.shape),
            rank=observed.rank,
            width=observed.width,
            projected_output_width=observed.projected_output_width,
            observation_phase="intervention_attempt",
            hook_module_path="attacker.controlled.module",
        )
    }

    result, _, _, _, _ = _run_pair(
        model,
        activation,
        reference_geometry=forged_reference,
    )

    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


def test_dtype_drift_between_baseline_and_attempt_is_not_comparable() -> None:
    model = _GeometryFixture()

    result, baseline, attempted, _, _ = _run_pair(
        model,
        _ones(dtype=torch.float32),
        intervention_activation=_ones(dtype=torch.float64),
    )

    assert baseline.dtype != attempted.dtype
    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


def test_output_shape_drift_is_not_evidence_of_intervention_effect() -> None:
    model = _GeometryFixture(shift_output_shape=True)

    result, baseline, attempted, _, _ = _run_pair(model, _ones())

    assert baseline.shape != attempted.shape
    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


def test_repeated_target_hook_is_not_collapsed_into_one_attested_application() -> None:
    model = _GeometryFixture(repeat_target_hook=True)

    result, _, _, _, _ = _run_pair(model, _ones())

    assert len(result.applied_coordinates) == 1
    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


def test_duplicate_coordinates_are_deduplicated_without_gain_amplification() -> None:
    model = _GeometryFixture()
    duplicate = (TARGET_LAYER, TARGET_COORDINATE)

    result, _, _, _, _ = _run_pair(
        model,
        _ones(),
        _intervention(coords=(duplicate, duplicate, duplicate)),
    )

    assert (
        result.structural_status
        == "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
    )
    assert result.structurally_valid is False
    assert len(result.requested_coordinates) == 1
    assert len(result.valid_coordinates) == 1
    assert len(result.applied_coordinates) == 1


def test_one_out_of_range_coordinate_rejects_the_whole_write_set() -> None:
    valid = (TARGET_LAYER, TARGET_COORDINATE)
    out_of_range = (TARGET_LAYER, INTERMEDIATE_WIDTH)

    result, baseline, attempted, _, _ = _run_pair(
        _GeometryFixture(),
        _ones(),
        _intervention(coords=(valid, out_of_range)),
    )

    assert result.structural_status == "REJECTED_PARTIALLY_INVALID_COORDINATES"
    assert len(result.valid_coordinates) == 1
    assert len(result.invalid_coordinates) == 1
    assert result.applied_coordinates == ()
    assert result.structurally_valid is False
    assert torch.equal(baseline, attempted)


def test_rank_drift_at_attempt_rejects_before_attestation() -> None:
    result, _, _, _, _ = _run_pair(
        _GeometryFixture(),
        _ones(),
        intervention_activation=torch.ones((2, INTERMEDIATE_WIDTH)),
    )

    assert result.structural_status == "REJECTED_RUNTIME_GEOMETRY"
    assert result.structurally_valid is False
    assert result.applied_coordinates == ()


@pytest.mark.parametrize("gain", [-1.0, math.nan, math.inf, -math.inf, True])
def test_invalid_numeric_gain_edges_are_typed_rejections(gain: Any) -> None:
    result, baseline, attempted, _, _ = _run_pair(
        _GeometryFixture(),
        _ones(),
        _intervention(gain=gain),
    )

    assert result.structural_status == "REJECTED_INVALID_GAIN"
    assert result.structurally_valid is False
    assert result.applied_coordinates == ()
    assert torch.equal(baseline, attempted)


@pytest.mark.parametrize("gain", [None, "not-a-number", object()])
def test_uncoercible_gain_returns_a_typed_rejection_instead_of_crashing(
    gain: Any,
) -> None:
    result, baseline, attempted, _, _ = _run_pair(
        _GeometryFixture(),
        _ones(),
        _intervention(gain=gain),
    )

    assert result.structural_status == "REJECTED_INVALID_GAIN"
    assert result.structurally_valid is False
    assert result.applied_coordinates == ()
    assert torch.equal(baseline, attempted)


def test_subnormal_gain_that_rounds_to_no_change_cannot_attest() -> None:
    result, baseline, attempted, _, _ = _run_pair(
        _GeometryFixture(),
        _ones(),
        _intervention(gain=5e-324),
    )

    assert result.structural_status == "ACTIVATION_UNCHANGED"
    assert result.structurally_valid is False
    assert torch.equal(baseline, attempted)


def test_gain_above_one_is_capped_once_at_full_suppression() -> None:
    result, _, _, _, _ = _run_pair(
        _GeometryFixture(),
        _ones(),
        _intervention(gain=10_000.0),
    )

    assert result.requested_gain == 10_000.0
    assert result.effective_gain == 1.0
    assert (
        result.structural_status
        == "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
    )
    assert result.structurally_valid is False


def test_public_schema_rejects_manufactured_retired_causal_attestation() -> None:
    result, _, _, _, _ = _run_pair(_GeometryFixture(), _ones())
    forged = result.model_dump(mode="python")
    forged["structural_status"] = "APPLIED_CHANGE_ATTESTED"
    forged["structurally_valid"] = True

    with pytest.raises(ValueError):
        type(result).model_validate(forged)


def test_validated_public_receipt_cannot_be_mutated_into_retired_attestation() -> None:
    result, _, _, _, _ = _run_pair(_GeometryFixture(), _ones())
    forged = result.model_dump(mode="python")
    forged["structural_status"] = "APPLIED_CHANGE_ATTESTED"
    forged["structurally_valid"] = True

    with pytest.raises(ValueError):
        result.structural_status = "APPLIED_CHANGE_ATTESTED"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        result.structurally_valid = True
    with pytest.raises(AttributeError):
        result.requested_coordinates.append(  # type: ignore[attr-defined]
            result.requested_coordinates[0]
        )
    with pytest.raises(ValueError):
        result.requested_coordinates[0].layer = 999  # type: ignore[misc]
    with pytest.raises(ValueError):
        result.observed_tensor_geometry[0].shape = (9, 9, 9)
    with pytest.raises(ValueError):
        result.model_copy(
            update={
                "structural_status": "APPLIED_CHANGE_ATTESTED",
                "structurally_valid": True,
            }
        )
    with pytest.raises(ValueError):
        result.copy(  # type: ignore[deprecated]
            update={
                "structural_status": "APPLIED_CHANGE_ATTESTED",
                "structurally_valid": True,
            }
        )
    with pytest.raises(ValueError):
        type(result).model_construct(**forged)

    exported = result.model_dump(mode="python")
    exported["structural_status"] = "APPLIED_CHANGE_ATTESTED"
    exported["structurally_valid"] = True
    exported["requested_coordinates"][0]["layer"] = 999

    assert result.structural_status == (
        "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
    )
    assert result.structurally_valid is False
    assert result.requested_coordinates[0].layer == TARGET_LAYER

    event = TokenEvent(
        token_index=0,
        token="<1>",
        eraser_intervention_result=result,
    )
    public_receipt = json.loads(event.model_dump_json())["eraser_intervention_result"]
    assert public_receipt["contract_version"] == (
        "harness_v2.mlp_intermediate_eraser.v2"
    )
    assert public_receipt["structural_status"] == (
        "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
    )
    assert public_receipt["structurally_valid"] is False


def test_cross_device_output_comparison_is_unavailable_not_attested() -> None:
    model = _GeometryFixture()
    activation = _ones()
    with capture_probes(model, TARGET_LAYER + 1) as baseline_state:
        baseline_output = model(activation)
    with capture_probes(model, TARGET_LAYER + 1) as stability_control_state:
        stability_control_output = model(activation)
    with capture_probes(
        model,
        TARGET_LAYER + 1,
        intervention=_intervention(),
        reference_geometry=baseline_state.tensor_geometry,
    ) as attempted_state:
        model(activation)

    result = finalize_intervention_result(
        attempted_state,
        baseline_output,
        torch.empty(baseline_output.shape, device="meta"),
        stability_control_state=stability_control_state,
        stability_control_output=stability_control_output,
    )

    assert result is not None
    assert result.structural_status == "OUTPUT_CHANGE_UNAVAILABLE"
    assert result.output_changed is None
    assert result.structurally_valid is False


def test_hook_uses_a_clone_and_does_not_mutate_the_caller_activation() -> None:
    activation = _ones()
    before = activation.clone()

    result, _, _, _, _ = _run_pair(_GeometryFixture(), activation)

    assert (
        result.structural_status
        == "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
    )
    assert result.structurally_valid is False
    assert torch.equal(activation, before)


class _RunnerOutput:
    def __init__(self, logits: torch.Tensor) -> None:
        self.logits = logits
        self.attentions = None


class _RunnerTokenizer:
    eos_token_id = None

    def __call__(self, prompt: str, return_tensors: str = "pt"):  # noqa: ARG002
        return SimpleNamespace(input_ids=torch.tensor([[1, 2]], dtype=torch.long))

    def decode(self, ids: list[int]) -> str:
        return f"<{int(ids[0])}>"


class _RunnerFixture(nn.Module):
    def __init__(self, *, drop_target_after_first: bool = False) -> None:
        super().__init__()
        self.gpt_neox = _NeoX()
        self.config = SimpleNamespace(
            intermediate_size=INTERMEDIATE_WIDTH,
            hidden_size=PROJECTED_WIDTH,
        )
        self.anchor = nn.Parameter(torch.zeros(1))
        self.drop_target_after_first = drop_target_after_first
        self.forward_count = 0

    def _run_hooks(self, input_ids: torch.Tensor) -> int:
        self.forward_count += 1
        activation = torch.ones(
            (input_ids.shape[0], input_ids.shape[1], INTERMEDIATE_WIDTH),
            device=input_ids.device,
        )
        fired = 0
        for layer_index, layer in enumerate(self.gpt_neox.layers):
            if (
                self.drop_target_after_first
                and self.forward_count > 1
                and layer_index == TARGET_LAYER
            ):
                continue
            layer.mlp(activation)
            fired += 1
        return fired


class _AliasedFallbackRunner(_RunnerFixture):
    def __init__(self) -> None:
        super().__init__(drop_target_after_first=True)
        self.register_buffer("shared_logits", torch.zeros((1, 2, 3)))

    def forward(
        self,
        input_ids: torch.Tensor,
        output_hidden_states: bool = False,  # noqa: ARG002
        output_attentions: bool = False,  # noqa: ARG002
    ) -> _RunnerOutput:
        fired = self._run_hooks(input_ids)
        self.shared_logits.zero_()
        chosen = 1 if fired == TARGET_LAYER + 1 else 2
        self.shared_logits[:, -1, chosen] = 10.0
        return _RunnerOutput(self.shared_logits)


class _RngConsumingRunner(_RunnerFixture):
    def __init__(self, *, drop_target_after_first: bool) -> None:
        super().__init__(drop_target_after_first=drop_target_after_first)

    def forward(
        self,
        input_ids: torch.Tensor,
        output_hidden_states: bool = False,  # noqa: ARG002
        output_attentions: bool = False,  # noqa: ARG002
    ) -> _RunnerOutput:
        self._run_hooks(input_ids)
        torch.rand(1)
        logits = torch.zeros(
            (input_ids.shape[0], input_ids.shape[1], 2),
            device=input_ids.device,
        )
        return _RunnerOutput(logits)


class _RandomOutputRunner(_RunnerFixture):
    def forward(
        self,
        input_ids: torch.Tensor,
        output_hidden_states: bool = False,  # noqa: ARG002
        output_attentions: bool = False,  # noqa: ARG002
    ) -> _RunnerOutput:
        self._run_hooks(input_ids)
        logits = torch.rand(
            (input_ids.shape[0], input_ids.shape[1], 4),
            device=input_ids.device,
        )
        return _RunnerOutput(logits)


class _StatefulFallbackRunner(_RunnerFixture):
    """Makes later-token logits depend on how many forwards already ran."""

    def __init__(self, *, drop_target_after_first: bool) -> None:
        super().__init__(drop_target_after_first=drop_target_after_first)

    def forward(
        self,
        input_ids: torch.Tensor,
        output_hidden_states: bool = False,  # noqa: ARG002
        output_attentions: bool = False,  # noqa: ARG002
    ) -> _RunnerOutput:
        self._run_hooks(input_ids)
        logits = torch.zeros(
            (input_ids.shape[0], input_ids.shape[1], 3),
            device=input_ids.device,
        )
        logits[:, -1, 1 if self.forward_count <= 2 else 2] = 10.0
        return _RunnerOutput(logits)


@pytest.fixture
def typed_runner(monkeypatch):
    original = pythia_runner._eraser_intervention

    def _typed_builder(request, **kwargs):
        return original(
            request,
            execution_kind="typed_test_fixture",
            expected_coordinate_width=INTERMEDIATE_WIDTH,
            expected_projected_output_width=PROJECTED_WIDTH,
        )

    monkeypatch.setattr(pythia_runner, "_eraser_intervention", _typed_builder)
    return pythia_runner.run_pythia


def _request(
    *,
    eraser: bool,
    temperature: float = 0.0,
    seed: int | None = None,
    max_new_tokens: int = 1,
) -> CreateSessionRequest:
    method_config: dict[str, Any] = {}
    if eraser:
        method_config = {
            "enabled_methods": ["drive_local_eraser"],
            "knobs": {"drive_local_eraser": {"drive": "F5", "gain": 1.0}},
        }
    return CreateSessionRequest(
        prompt="typed numeric red team",
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        seed=seed,
        method_config=method_config,
    )


def _drain_runner(run, request, model):
    async def _drain():
        return [
            item
            async for item in run(
                request,
                model,
                _RunnerTokenizer(),
                TARGET_LAYER + 1,
            )
        ]

    return asyncio.run(_drain())


def test_rejected_fallback_is_snapshot_atomic_under_output_aliasing(
    typed_runner,
) -> None:
    payload = _drain_runner(
        typed_runner,
        _request(eraser=True),
        _AliasedFallbackRunner(),
    )[0]
    result = payload["eraser_intervention_result"]

    assert result.execution_kind == "typed_test_fixture"
    assert result.structural_status == "REJECTED_UNSTABLE_BASELINE"
    assert result.structurally_valid is False
    assert payload["token"] == "<1>"


def test_rejected_fallback_restores_rng_before_sampling(typed_runner) -> None:
    control = _drain_runner(
        typed_runner,
        _request(eraser=False, temperature=1.0, seed=3),
        _RngConsumingRunner(drop_target_after_first=True),
    )[0]
    rejected = _drain_runner(
        typed_runner,
        _request(eraser=True, temperature=1.0, seed=3),
        _RngConsumingRunner(drop_target_after_first=True),
    )[0]
    result = rejected["eraser_intervention_result"]

    assert result.execution_kind == "typed_test_fixture"
    assert result.structural_status == "REJECTED_UNSTABLE_BASELINE"
    assert control["token"] == rejected["token"]


def test_runner_rng_only_output_delta_cannot_attest_application(typed_runner) -> None:
    payload = _drain_runner(
        typed_runner,
        _request(eraser=True, seed=11),
        _RandomOutputRunner(),
    )[0]
    result = payload["eraser_intervention_result"]

    assert result.execution_kind == "typed_test_fixture"
    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


def test_two_stable_controls_do_not_prove_third_pass_output_is_intervention_caused(
    typed_runner,
) -> None:
    payload = _drain_runner(
        typed_runner,
        _request(eraser=True),
        _StatefulFallbackRunner(drop_target_after_first=False),
    )[0]
    result = payload["eraser_intervention_result"]

    # This fixture's first two unmodified forwards are bit-exact, while its
    # third forward changes logits solely because of hidden mutable state. The
    # intervention hook also fires and changes its activation, so attestation
    # must still distinguish temporal drift from intervention-caused output.
    assert payload["token"] == "<1>"
    assert result.activation_changed is True
    assert result.output_changed is True
    assert result.structural_status != "APPLIED_CHANGE_ATTESTED"
    assert result.structurally_valid is False


def test_rejected_fallback_does_not_advance_mutable_model_state(typed_runner) -> None:
    control = _drain_runner(
        typed_runner,
        _request(eraser=False, max_new_tokens=2),
        _StatefulFallbackRunner(drop_target_after_first=False),
    )
    rejected = _drain_runner(
        typed_runner,
        _request(eraser=True, max_new_tokens=2),
        _StatefulFallbackRunner(drop_target_after_first=True),
    )

    assert len(control) == 2
    assert len(rejected) == 1
    assert rejected[0]["eraser_intervention_result"].structurally_valid is False
    assert rejected[0]["token"] == control[0]["token"]


def test_stage27f_fixture_coordinates_cover_only_declared_tensor_bounds() -> None:
    coordinates = coords_for_drive("F5")

    assert coordinates
    assert len({(item.layer, item.index) for item in coordinates}) == len(coordinates)
    assert all(item.layer >= 0 for item in coordinates)
    assert all(0 <= item.index < INTERMEDIATE_WIDTH for item in coordinates)
    assert all(
        item.coordinate_space == "mlp_intermediate_post_activation"
        for item in coordinates
    )
