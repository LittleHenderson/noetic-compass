"""Focused additive coverage for the pinned Qwen Stage B probe adapter.

These are typed local fixtures. They do not load model weights, contact a
provider, execute a scientific experiment, or create an Evidence Packet.
"""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from app.runtime import model_loader
from app.runtime.event_stream import _cover_event
from app.runtime.event_stream import stream_real_trace
from app.runtime.knob_resolution import resolve_knobs
from app.runtime.ablation_probe import (
    run_real_ablation_control,
    run_real_ablation_effect,
)
from app.runtime.pythia_runner import _eraser_intervention
from app.runtime.probe_runner import EraserIntervention, capture_probes
from app.schemas.requests import CreateSessionRequest


class _Projection(nn.Module):
    def __init__(self, input_width: int, output_width: int) -> None:
        super().__init__()
        self.in_features = input_width
        self.out_features = output_width

    def forward(self, activation):
        return activation[..., : self.out_features].clone()


class _QwenMlp(nn.Module):
    def __init__(self, input_width: int = 4864, output_width: int = 896) -> None:
        super().__init__()
        self.down_proj = _Projection(input_width, output_width)


class _QwenLayer(nn.Module):
    def __init__(self, input_width: int = 4864, output_width: int = 896) -> None:
        super().__init__()
        self.mlp = _QwenMlp(input_width, output_width)


class _QwenFixture(nn.Module):
    def __init__(
        self,
        *,
        n_layers: int = 2,
        input_width: int = 4864,
        output_width: int = 896,
    ) -> None:
        super().__init__()
        self.model = SimpleNamespace(
            layers=nn.ModuleList(
                [
                    _QwenLayer(input_width, output_width)
                    for _ in range(n_layers)
                ]
            )
        )

    def forward(self, activation):
        return torch.stack(
            [layer.mlp.down_proj(activation) for layer in self.model.layers]
        ).sum(dim=0)


class _PythiaMlp(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.dense_4h_to_h = _Projection(3072, 768)


class _PythiaLayer(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.mlp = _PythiaMlp()


class _PythiaFixture(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.gpt_neox = SimpleNamespace(
            layers=nn.ModuleList([_PythiaLayer()])
        )

    def forward(self, activation):
        return self.gpt_neox.layers[0].mlp.dense_4h_to_h(activation)


def test_qwen_binding_declares_exact_stack_projection_and_geometry(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    binding = model_loader.active_model_binding()

    assert binding.probe_layer_stack_path == ("model", "layers")
    assert binding.probe_projection_path == ("mlp", "down_proj")
    assert model_loader.probe_hook_module_path(binding, 7) == (
        "model.layers[7].mlp.down_proj"
    )
    assert binding.arch.hidden_size == 896
    assert binding.arch.mlp_intermediate_dim == 4864
    assert binding.stage27f_intervention_supported is False
    assert binding.stage27f_cover_library_supported is False
    assert binding.single_unit_causal_ablation_supported is False


def test_qwen_manifest_declares_observation_only_and_pythia_stays_exact(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    qwen_manifest = model_loader.bootstrap_manifest()

    assert qwen_manifest.intervention_hook_contract.model_dump() == {
        "contract_version": (
            "harness_v2.qwen2_mlp_intermediate_observation_only.v1"
        ),
        "capability_status": (
            "OBSERVATION_ONLY_INTERVENTION_UNAVAILABLE_UNCALIBRATED"
        ),
        "coordinate_space": "mlp_intermediate_post_activation",
        "module_path_template": "model.layers[{layer}].mlp.down_proj",
        "tensor_role": "forward_pre_hook.input[0]",
        "token_selection": "batch_0_last_sequence_position",
        "expected_width_source": "model_arch.mlp_intermediate_dim",
        "failure_policy": "fail_closed",
        "unavailable_reason": "NO_QWEN_CALIBRATED_COORDINATE_ADAPTER",
    }

    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    pythia_manifest = model_loader.bootstrap_manifest()
    assert pythia_manifest is model_loader.PYTHIA_160M_MANIFEST
    pythia_raw = pythia_manifest.model_dump_json().encode("utf-8")
    assert len(pythia_raw) == 1093
    assert hashlib.sha256(pythia_raw).hexdigest() == (
        "3957cd051d1a7de53f49f791b0de5c409506625bf6ed0e94b684ba57c2aa1b37"
    )
    assert pythia_manifest.intervention_hook_contract.model_dump() == {
        "contract_version": "harness_v2.mlp_intermediate_eraser.v2",
        "coordinate_space": "mlp_intermediate_post_activation",
        "module_path_template": (
            "gpt_neox.layers[{layer}].mlp.dense_4h_to_h"
        ),
        "tensor_role": "forward_pre_hook.input[0]",
        "token_selection": "batch_0_last_sequence_position",
        "expected_width_source": "model_arch.mlp_intermediate_dim",
        "failure_policy": "fail_closed",
    }


def test_manifest_schema_cross_binds_qwen_identity_and_observation_contract(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    qwen_manifest = model_loader.bootstrap_manifest()
    qwen_payload = qwen_manifest.model_dump(mode="json")
    qwen_payload.pop("intervention_hook_contract")
    with pytest.raises(ValueError, match="Qwen observation contract requires"):
        type(qwen_manifest).model_validate(qwen_payload)

    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    pythia_manifest = model_loader.bootstrap_manifest()
    pythia_payload = pythia_manifest.model_dump(mode="json")
    pythia_payload["intervention_hook_contract"] = (
        qwen_manifest.intervention_hook_contract.model_dump(mode="json")
    )
    with pytest.raises(ValueError, match="Qwen observation contract requires"):
        type(pythia_manifest).model_validate(pythia_payload)


def _real_manifest_for_binding(binding):
    payload = model_loader.bootstrap_manifest(binding).model_dump(mode="json")
    payload.update(
        {
            "execution_kind": "real_model_weights",
            "resolved_revision": binding.revision,
            "revision_verified": True,
            "weights_filename": binding.weights_filename,
            "weights_sha256": binding.weights_sha256,
            "weights_bytes": binding.weights_bytes,
            "weights_hash_verified": True,
            "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
            "runtime_execution": {
                "profile": "development",
                "device": "cpu",
                "dtype": "torch.float32",
                "torch_version": "2.13.0+cu126",
                "torch_native_jit_disabled": False,
                "cuda_bfloat16_supported": None,
                "cuda_runtime_version": None,
                "cuda_driver_version": None,
                "cuda_device_name": None,
                "cuda_device_capability": None,
            },
            "is_real_model": True,
        }
    )
    return type(model_loader.PYTHIA_160M_MANIFEST).model_validate(payload)


def test_loaded_model_real_state_rejects_cross_family_static_identity(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    qwen_binding = model_loader.active_model_binding()
    pythia_static = model_loader.PYTHIA_160M_MANIFEST.model_dump(mode="json")
    qwen_runtime = _real_manifest_for_binding(qwen_binding).model_dump(mode="json")
    for field in (
        "execution_kind",
        "requested_revision",
        "resolved_revision",
        "revision_verified",
        "weights_filename",
        "weights_sha256",
        "weights_bytes",
        "weights_hash_verified",
        "model_identity_status",
        "runtime_execution",
        "is_real_model",
    ):
        pythia_static[field] = qwen_runtime[field]
    forged = type(model_loader.PYTHIA_160M_MANIFEST).model_validate(pythia_static)
    assert model_loader.LoadedModel(
        manifest=forged,
        model=object(),
        tokenizer=object(),
    ).is_real is False

    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    pythia_binding = model_loader.active_model_binding()
    qwen_static = model_loader.bootstrap_manifest(qwen_binding).model_dump(mode="json")
    pythia_runtime = _real_manifest_for_binding(pythia_binding).model_dump(mode="json")
    for field in (
        "execution_kind",
        "requested_revision",
        "resolved_revision",
        "revision_verified",
        "weights_filename",
        "weights_sha256",
        "weights_bytes",
        "weights_hash_verified",
        "model_identity_status",
        "runtime_execution",
        "is_real_model",
    ):
        qwen_static[field] = pythia_runtime[field]
    forged = type(model_loader.PYTHIA_160M_MANIFEST).model_validate(qwen_static)
    assert model_loader.LoadedModel(
        manifest=forged,
        model=object(),
        tokenizer=object(),
    ).is_real is False


def test_qwen_capture_walks_model_layers_and_hooks_down_proj(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    binding = model_loader.active_model_binding()
    model = _QwenFixture()
    activation = torch.arange(2 * 4864, dtype=torch.float32).reshape(1, 2, 4864)

    with capture_probes(model, 2, probe_binding=binding) as state:
        model(activation)

    assert sorted(state.mlp_post) == [0, 1]
    assert len(state.mlp_post[0]) == 4864
    assert state.mlp_post[0][0] == float(activation[0, -1, 0])
    assert state.tensor_geometry[0].width == 4864
    assert state.tensor_geometry[0].projected_output_width == 896
    assert state.tensor_geometry[0].hook_module_path == (
        "model.layers[0].mlp.down_proj"
    )
    assert not model.model.layers[0].mlp.down_proj._forward_pre_hooks


def test_qwen_probe_resolution_fails_closed_on_wrong_projection_width(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    binding = model_loader.active_model_binding()
    model = _QwenFixture(input_width=4863)

    with pytest.raises(RuntimeError, match="input width mismatch"):
        with capture_probes(model, 2, probe_binding=binding):
            pass


def test_qwen_probe_resolution_does_not_fall_back_to_pythia_path(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    binding = model_loader.active_model_binding()
    model = _PythiaFixture()

    with pytest.raises(RuntimeError, match=r"expected model\.layers"):
        with capture_probes(model, 1, probe_binding=binding):
            pass


def test_qwen_stage27f_intervention_is_refused_before_hooking(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    binding = model_loader.active_model_binding()
    model = _QwenFixture(n_layers=1)
    intervention = EraserIntervention(
        coords=((0, 1),),
        gain=1.0,
        coordinate_space="mlp_intermediate_post_activation",
        execution_kind="typed_test_fixture",
        source_kind="typed_test_fixture",
        expected_coordinate_width=4864,
        expected_projected_output_width=896,
    )

    with pytest.raises(RuntimeError, match="intervention refused"):
        with capture_probes(
            model,
            1,
            intervention=intervention,
            reference_geometry={},
            probe_binding=binding,
        ):
            pass
    assert not model.model.layers[0].mlp.down_proj._forward_pre_hooks


class _MustNotRun:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *_args, **_kwargs):
        self.calls += 1
        raise AssertionError("Qwen ablation refusal must precede model/tokenizer use")

    def parameters(self):
        self.calls += 1
        raise AssertionError("Qwen ablation refusal must precede model inspection")


def test_qwen_causal_ablation_functions_refuse_before_any_forward(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    request = CreateSessionRequest(
        prompt="do not execute",
        max_new_tokens=1,
        probes=["causal_ablation"],
    )
    target = request.ablation_target or SimpleNamespace(layer=0, unit=0, mode="zero")
    model = _MustNotRun()
    tokenizer = _MustNotRun()
    binding = model_loader.active_model_binding()

    for function in (run_real_ablation_effect, run_real_ablation_control):
        with pytest.raises(RuntimeError, match="refusing before any model forward"):
            function(
                request,
                model,
                tokenizer,
                24,
                target,
                model_binding=binding,
            )
    assert model.calls == 0
    assert tokenizer.calls == 0


@pytest.mark.asyncio
async def test_qwen_real_stream_refuses_ablation_before_generation(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    loaded = SimpleNamespace(
        is_real=True,
        manifest=model_loader.bootstrap_manifest(),
        model=_MustNotRun(),
        tokenizer=_MustNotRun(),
    )
    monkeypatch.setattr(
        "app.runtime.event_stream.get_loaded_model",
        lambda: loaded,
    )
    request = CreateSessionRequest(
        prompt="do not execute",
        max_new_tokens=1,
        probes=["causal_ablation"],
    )

    events = [event async for event in stream_real_trace(request)]

    assert len(events) == 1
    assert events[0].type == "error"
    assert "no model forward was executed" in events[0].message
    assert loaded.model.calls == 0
    assert loaded.tokenizer.calls == 0


def test_qwen_real_runner_refuses_pythia_calibrated_cover(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    request = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        probes=["active_trace"],
        method_config={
            "enabled_methods": ["drive_local_eraser"],
            "knobs": {"drive_local_eraser": {"drive": "F5", "gain": 1.0}},
        },
    )

    with pytest.raises(RuntimeError, match="calibrated only for the pinned Pythia"):
        _eraser_intervention(
            request,
            execution_kind="real_model_weights",
            expected_coordinate_width=4864,
            expected_projected_output_width=896,
            model_binding=model_loader.active_model_binding(),
        )


def test_qwen_never_emits_or_advertises_pythia_cover_library(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    request = CreateSessionRequest(
        prompt="inspect only",
        max_new_tokens=1,
        probes=["blindspot_covers"],
        method_config={
            "enabled_methods": ["blindspot_detection"],
            "knobs": {"blindspot_detection": {"scope": "all_7"}},
        },
    )

    resolved = resolve_knobs(request)
    assert resolved["drive_local_eraser"]["cover_available"] is False
    assert resolved["blindspot_detection"] == {
        "scope": "all_7",
        "drive": "all_7",
        "cover_available": False,
    }
    assert _cover_event(request).per_class_neuron_covers == {}


def test_pythia_capture_path_and_geometry_remain_exact(monkeypatch) -> None:
    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    binding = model_loader.active_model_binding()
    model = _PythiaFixture()
    activation = torch.ones((1, 2, 3072), dtype=torch.float32)

    with capture_probes(model, 1, probe_binding=binding) as state:
        model(activation)

    geometry = state.tensor_geometry[0]
    assert binding.probe_layer_stack_path == ("gpt_neox", "layers")
    assert binding.probe_projection_path == ("mlp", "dense_4h_to_h")
    assert binding.stage27f_intervention_supported is True
    assert binding.stage27f_cover_library_supported is True
    assert binding.single_unit_causal_ablation_supported is True
    assert geometry.width == 3072
    assert geometry.projected_output_width == 768
    assert geometry.hook_module_path == (
        "gpt_neox.layers[0].mlp.dense_4h_to_h"
    )


class _RawPythiaTokenizer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, prompt: str, *, return_tensors: str):
        self.calls.append((prompt, return_tensors))
        return SimpleNamespace(input_ids=torch.tensor([[3, 4]], dtype=torch.long))

    def apply_chat_template(self, *_args, **_kwargs):
        raise AssertionError("Pythia must not use a chat template")


class _PinnedQwenTokenizer:
    chat_template = "{{ pinned_qwen_chat_template }}"

    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []

    def __call__(self, *_args, **_kwargs):
        raise AssertionError("Qwen Instruct must not use raw tokenization")

    def apply_chat_template(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return {"input_ids": torch.tensor([[11, 12, 13]], dtype=torch.long)}


def test_pythia_runtime_prompt_keeps_raw_tokenization(monkeypatch) -> None:
    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    tokenizer = _RawPythiaTokenizer()

    encoded = model_loader.encode_runtime_prompt(
        tokenizer,
        "raw prompt",
        binding=model_loader.active_model_binding(),
    )

    assert tokenizer.calls == [("raw prompt", "pt")]
    assert encoded["input_ids"].tolist() == [[3, 4]]


def test_qwen_runtime_prompt_uses_pinned_chat_template(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    tokenizer = _PinnedQwenTokenizer()

    encoded = model_loader.encode_runtime_prompt(
        tokenizer,
        "follow this instruction",
        binding=model_loader.active_model_binding(),
    )

    assert encoded["input_ids"].tolist() == [[11, 12, 13]]
    assert tokenizer.calls == [
        (
            [{"role": "user", "content": "follow this instruction"}],
            {
                "tokenize": True,
                "add_generation_prompt": True,
                "return_tensors": "pt",
                "return_dict": True,
            },
        )
    ]


def test_qwen_runtime_prompt_fails_closed_without_chat_template(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    tokenizer = _PinnedQwenTokenizer()
    tokenizer.chat_template = ""

    with pytest.raises(RuntimeError, match="exposes no chat template"):
        model_loader.encode_runtime_prompt(
            tokenizer,
            "prompt",
            binding=model_loader.active_model_binding(),
        )


class _QwenCanaryFixture:
    def __init__(self) -> None:
        self.model = SimpleNamespace(
            layers=[_QwenLayer() for _ in range(24)]
        )

    def __call__(self, **inputs):
        input_ids = inputs["input_ids"]
        sequence_length = int(input_ids.shape[1])
        activation = torch.ones(
            (1, sequence_length, 4864),
            dtype=torch.float32,
        )
        self.model.layers[0].mlp.down_proj(activation)
        attention = torch.ones(
            (1, 14, sequence_length, sequence_length),
            dtype=torch.float32,
        )
        return SimpleNamespace(
            attentions=[attention] * 24,
            logits=torch.ones((1, sequence_length, 32), dtype=torch.float32),
        )


def test_qwen_runtime_canary_uses_chat_input_and_exact_probe_geometry(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV,
        model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
    )
    tokenizer = _PinnedQwenTokenizer()

    model_loader._validate_runtime_canary(
        torch,
        _QwenCanaryFixture(),
        tokenizer,
        device="cpu",
    )

    assert len(tokenizer.calls) == 1
    assert tokenizer.calls[0][0] == [
        {
            "role": "user",
            "content": "Project Coherence Gate 5 runtime canary.",
        }
    ]
