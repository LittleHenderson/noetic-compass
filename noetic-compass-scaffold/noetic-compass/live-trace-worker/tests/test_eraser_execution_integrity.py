"""Adversarial Harness v2 tests for Stage-27F coordinate execution integrity.

These tests use an explicitly typed torch fixture. They never load or contact a
model provider. The fixture preserves Pythia-160M's load-bearing geometry:
3,072-wide activated MLP intermediate -> 768-wide projected output.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Iterable

import torch
from torch import nn

from app.runtime.event_stream import stream_fake_trace
from app.runtime.pythia_runner import run_pythia
from app.runtime.probe_runner import (
    EraserIntervention,
    capture_probes,
    finalize_intervention_result,
)
from app.schemas.events import TokenEvent
from app.schemas.requests import CreateSessionRequest


INTERMEDIATE_WIDTH = 3072
PROJECTED_WIDTH = 768
TARGET_LAYER = 5
HIGH_INTERMEDIATE_COORDINATE = 2346


class _Projection(nn.Module):
    def __init__(self, mapped_indices: Iterable[int]) -> None:
        super().__init__()
        self.in_features = INTERMEDIATE_WIDTH
        self.out_features = PROJECTED_WIDTH
        self.mapped_indices = tuple(mapped_indices)

    def forward(self, activation):
        output = activation[..., :PROJECTED_WIDTH].clone()
        for index in self.mapped_indices:
            output[..., index % PROJECTED_WIDTH] += activation[..., index]
        return output


class _MLP(nn.Module):
    def __init__(self, mapped_indices: Iterable[int]) -> None:
        super().__init__()
        self.dense_4h_to_h = _Projection(mapped_indices)

    def forward(self, activation):
        return self.dense_4h_to_h(activation)


class _Layer(nn.Module):
    def __init__(self, mapped_indices: Iterable[int]) -> None:
        super().__init__()
        self.mlp = _MLP(mapped_indices)


class _GptNeoX(nn.Module):
    def __init__(self, mapped_indices: Iterable[int]) -> None:
        super().__init__()
        self.layers = nn.ModuleList(
            [_Layer(mapped_indices) for _ in range(TARGET_LAYER + 1)]
        )


class _TypedPythiaGeometryFixture(nn.Module):
    def __init__(
        self,
        *,
        mapped_indices: Iterable[int] = (),
        skip_target_after_first_forward: bool = False,
    ) -> None:
        super().__init__()
        self.gpt_neox = _GptNeoX(mapped_indices)
        self.skip_target_after_first_forward = skip_target_after_first_forward
        self.forward_count = 0

    def forward(self, activation):
        self.forward_count += 1
        outputs = []
        for layer_index, layer in enumerate(self.gpt_neox.layers):
            if (
                self.skip_target_after_first_forward
                and self.forward_count > 1
                and layer_index == TARGET_LAYER
            ):
                continue
            outputs.append(layer.mlp(activation))
        return torch.stack(outputs).sum(dim=0)


def _intervention(
    coords: tuple[tuple[int, int], ...],
    *,
    gain: float = 1.0,
    coordinate_space: str = "mlp_intermediate_post_activation",
) -> EraserIntervention:
    return EraserIntervention(
        coords=coords,
        gain=gain,
        coordinate_space=coordinate_space,
        execution_kind="typed_test_fixture",
        source_kind="typed_test_fixture",
        expected_coordinate_width=INTERMEDIATE_WIDTH,
        expected_projected_output_width=PROJECTED_WIDTH,
    )


def _run_pair(model, activation, intervention):
    with capture_probes(model, TARGET_LAYER + 1) as baseline_state:
        baseline_output = model(activation)
    with capture_probes(model, TARGET_LAYER + 1) as stability_control_state:
        stability_control_output = model(activation)
    with capture_probes(
        model,
        TARGET_LAYER + 1,
        intervention=intervention,
        reference_geometry=baseline_state.tensor_geometry,
    ) as intervention_state:
        intervention_output = model(activation)
    result = finalize_intervention_result(
        intervention_state,
        baseline_output,
        intervention_output,
        stability_control_state=stability_control_state,
        stability_control_output=stability_control_output,
    )
    assert result is not None
    return result, baseline_output, intervention_output


def test_pythia_intermediate_coordinate_is_not_checked_against_projected_width():
    model = _TypedPythiaGeometryFixture(
        mapped_indices=(HIGH_INTERMEDIATE_COORDINATE,)
    )
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, _, _ = _run_pair(
        model,
        activation,
        _intervention(((TARGET_LAYER, HIGH_INTERMEDIATE_COORDINATE),)),
    )

    assert HIGH_INTERMEDIATE_COORDINATE >= PROJECTED_WIDTH
    assert HIGH_INTERMEDIATE_COORDINATE < INTERMEDIATE_WIDTH
    assert (
        result.structural_status
        == "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
    )
    assert result.structurally_valid is False
    geometry = next(
        item for item in result.observed_tensor_geometry if item.layer == TARGET_LAYER
    )
    assert geometry.width == INTERMEDIATE_WIDTH
    assert geometry.projected_output_width == PROJECTED_WIDTH
    assert geometry.observation_phase == "intervention_attempt"
    assert geometry.tensor_role == "forward_pre_hook.input[0]"
    assert result.applied_coordinates[0].index == HIGH_INTERMEDIATE_COORDINATE


def test_all_invalid_coordinates_fail_closed_without_application():
    model = _TypedPythiaGeometryFixture()
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(((TARGET_LAYER, INTERMEDIATE_WIDTH), (TARGET_LAYER, 9000))),
    )

    assert result.structural_status == "REJECTED_ALL_COORDINATES_INVALID"
    assert result.valid_coordinates == ()
    assert len(result.invalid_coordinates) == 2
    assert result.applied_coordinates == ()
    assert result.activation_changed is False
    assert result.output_changed is False
    assert torch.equal(baseline, attempted)


def test_enabled_intervention_with_no_coordinates_is_typed_rejection():
    model = _TypedPythiaGeometryFixture()
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(()),
    )

    assert result.structural_status == "REJECTED_NO_COORDINATES"
    assert result.requested_coordinates == ()
    assert result.applied_coordinates == ()
    assert result.structurally_valid is False
    assert result.activation_changed is False
    assert result.output_changed is False
    assert torch.equal(baseline, attempted)


def test_partially_invalid_coordinates_reject_the_entire_intervention():
    model = _TypedPythiaGeometryFixture(
        mapped_indices=(HIGH_INTERMEDIATE_COORDINATE,)
    )
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(
            (
                (TARGET_LAYER, HIGH_INTERMEDIATE_COORDINATE),
                (TARGET_LAYER, INTERMEDIATE_WIDTH),
            )
        ),
    )

    assert result.structural_status == "REJECTED_PARTIALLY_INVALID_COORDINATES"
    assert [item.index for item in result.valid_coordinates] == [
        HIGH_INTERMEDIATE_COORDINATE
    ]
    assert [item.index for item in result.invalid_coordinates] == [INTERMEDIATE_WIDTH]
    assert result.applied_coordinates == ()
    assert result.activation_changed is False
    assert result.output_changed is False
    assert torch.equal(baseline, attempted)


def test_wrong_coordinate_space_fails_closed_without_reinterpretation():
    model = _TypedPythiaGeometryFixture(mapped_indices=(12,))
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(
            ((TARGET_LAYER, 12),),
            coordinate_space="mlp_output_post_projection",
        ),
    )

    assert result.structural_status == "REJECTED_WRONG_COORDINATE_SPACE"
    assert result.hook_fired is False
    assert result.applied_coordinates == ()
    assert result.activation_changed is False
    assert result.output_changed is False
    assert torch.equal(baseline, attempted)


def test_hook_not_fired_is_typed_and_never_counts_as_valid_application():
    model = _TypedPythiaGeometryFixture(
        mapped_indices=(12,),
        skip_target_after_first_forward=True,
    )
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, _, _ = _run_pair(
        model,
        activation,
        _intervention(((TARGET_LAYER, 12),)),
    )

    assert result.structural_status == "HOOK_NOT_FIRED"
    assert result.hook_fired is False
    assert TARGET_LAYER in result.required_hook_layers
    assert TARGET_LAYER not in result.hook_fired_layers
    target_geometry = next(
        item for item in result.observed_tensor_geometry if item.layer == TARGET_LAYER
    )
    assert target_geometry.observation_phase == "unmodified_forward"
    assert result.applied_coordinates == ()
    assert result.structurally_valid is False


def test_unchanged_activation_is_not_an_attested_intervention():
    model = _TypedPythiaGeometryFixture(mapped_indices=(12,))
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))
    activation[0, -1, 12] = 0.0

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(((TARGET_LAYER, 12),)),
    )

    assert result.structural_status == "ACTIVATION_UNCHANGED"
    assert result.hook_fired is True
    assert result.activation_changed is False
    assert result.output_changed is False
    assert len(result.applied_coordinates) == 1
    assert torch.equal(baseline, attempted)


def test_zero_gain_is_explicitly_applied_but_cannot_attest_activation_change():
    model = _TypedPythiaGeometryFixture(mapped_indices=(12,))
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(((TARGET_LAYER, 12),), gain=0.0),
    )

    assert result.structural_status == "ACTIVATION_UNCHANGED"
    assert result.requested_gain == 0.0
    assert result.effective_gain == 0.0
    assert result.hook_fired is True
    assert result.activation_changed is False
    assert result.output_changed is False
    assert len(result.applied_coordinates) == 1
    assert result.structurally_valid is False
    assert torch.equal(baseline, attempted)


def test_activation_change_without_output_change_is_typed_fail_closed():
    model = _TypedPythiaGeometryFixture(mapped_indices=())
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(((TARGET_LAYER, HIGH_INTERMEDIATE_COORDINATE),)),
    )

    assert result.structural_status == "OUTPUT_UNCHANGED"
    assert result.hook_fired is True
    assert result.activation_changed is True
    assert result.output_changed is False
    assert result.structurally_valid is False
    assert torch.equal(baseline, attempted)


class _LegacyPostProjectionOnlyMLP(nn.Module):
    def forward(self, activation):
        return activation[..., :PROJECTED_WIDTH]


class _LegacyPostProjectionOnlyLayer(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.mlp = _LegacyPostProjectionOnlyMLP()


class _LegacyPostProjectionOnlyModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.gpt_neox = SimpleNamespace(
            layers=[_LegacyPostProjectionOnlyLayer() for _ in range(TARGET_LAYER + 1)]
        )

    def forward(self, activation):
        return torch.stack(
            [layer.mlp(activation) for layer in self.gpt_neox.layers]
        ).sum(dim=0)


def test_legacy_full_mlp_postprojection_hook_shape_is_refused():
    model = _LegacyPostProjectionOnlyModel()
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(((TARGET_LAYER, 12),)),
    )

    assert result.structural_status == "REJECTED_HOOK_CONTRACT"
    assert result.hook_fired is False
    assert result.observed_tensor_geometry == ()
    assert result.applied_coordinates == ()
    assert result.activation_changed is False
    assert result.output_changed is False
    assert torch.equal(baseline, attempted)


def test_valid_coordinate_fires_hook_and_changes_activation_and_output():
    model = _TypedPythiaGeometryFixture(mapped_indices=(12,))
    activation = torch.ones((1, 2, INTERMEDIATE_WIDTH))

    result, baseline, attempted = _run_pair(
        model,
        activation,
        _intervention(((TARGET_LAYER, 12),)),
    )

    assert (
        result.structural_status
        == "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED"
    )
    assert result.structurally_valid is False
    assert result.hook_fired is True
    assert result.hook_fired_layers == (TARGET_LAYER,)
    assert result.activation_changed is True
    assert result.output_changed is True
    assert len(result.requested_coordinates) == 1
    assert result.requested_coordinates == result.valid_coordinates
    assert result.valid_coordinates == result.applied_coordinates
    assert not torch.equal(baseline, attempted)


class _RunnerOutput:
    def __init__(self, logits) -> None:
        self.logits = logits
        self.attentions = None


class _HookDropRunnerModel(_TypedPythiaGeometryFixture):
    def __init__(self) -> None:
        super().__init__(
            mapped_indices=(12,),
            skip_target_after_first_forward=True,
        )
        self.config = SimpleNamespace(
            intermediate_size=INTERMEDIATE_WIDTH,
            hidden_size=PROJECTED_WIDTH,
        )
        self._anchor = nn.Parameter(torch.zeros(1))

    def forward(
        self,
        input_ids,
        output_hidden_states=False,  # noqa: ARG002
        output_attentions=False,  # noqa: ARG002
    ):
        activation = torch.ones(
            (input_ids.shape[0], input_ids.shape[1], INTERMEDIATE_WIDTH),
            device=input_ids.device,
        )
        self.forward_count += 1
        fired_layers = 0
        for layer_index, layer in enumerate(self.gpt_neox.layers):
            if self.forward_count > 1 and layer_index == TARGET_LAYER:
                continue
            layer.mlp(activation)
            fired_layers += 1
        logits = torch.zeros(
            (input_ids.shape[0], input_ids.shape[1], 4),
            device=input_ids.device,
        )
        # Baseline (six hooks) selects id 1; the malformed attempted pass
        # (five hooks) selects id 2. The runner must emit the baseline id.
        logits[:, -1, 1 if fired_layers == TARGET_LAYER + 1 else 2] = 10.0
        return _RunnerOutput(logits)


class _RunnerTokenizer:
    eos_token_id = None

    def __call__(self, prompt, return_tensors="pt"):  # noqa: ARG002
        return SimpleNamespace(input_ids=torch.tensor([[1, 2]], dtype=torch.long))

    def decode(self, ids):
        return f"<{int(ids[0])}>"


def test_hook_failure_result_falls_back_atomically_to_baseline_generation():
    request = CreateSessionRequest(
        prompt="atomic fallback",
        max_new_tokens=1,
        method_config={
            "enabled_methods": ["drive_local_eraser"],
            "knobs": {"drive_local_eraser": {"drive": "F5", "gain": 1.0}},
        },
    )
    model = _HookDropRunnerModel()

    async def _drain():
        return [
            payload
            async for payload in run_pythia(
                request,
                model,
                _RunnerTokenizer(),
                TARGET_LAYER + 1,
            )
        ]

    payloads = asyncio.run(_drain())
    assert len(payloads) == 1
    payload = payloads[0]
    result = payload["eraser_intervention_result"]
    assert result.structural_status == "REJECTED_UNSTABLE_BASELINE"
    assert result.structurally_valid is False
    assert result.stability_control_performed is True
    assert result.baseline_geometry_stable is False
    assert result.applied_coordinates == ()  # unstable control prevents any attempt
    assert payload["token"] == "<1>"  # baseline, never malformed attempted id 2


def test_fake_stream_types_eraser_as_demo_not_executed():
    request = CreateSessionRequest(
        prompt="typed demo",
        max_new_tokens=1,
        method_config={
            "enabled_methods": ["drive_local_eraser"],
            "knobs": {"drive_local_eraser": {"drive": "F5", "gain": 1.0}},
        },
    )

    async def _drain():
        return [event async for event in stream_fake_trace(request)]

    events = asyncio.run(_drain())
    token = next(event for event in events if isinstance(event, TokenEvent))
    result = token.eraser_intervention_result
    assert result is not None
    assert result.execution_kind == "demo_schema_only"
    assert result.source_kind == "demo_schema_only"
    assert result.structural_status == "DEMO_NOT_EXECUTED"
    assert result.structurally_valid is False
    assert result.hook_fired is False
    assert result.activation_changed is None
    assert result.output_changed is None
    assert result.applied_coordinates == ()
