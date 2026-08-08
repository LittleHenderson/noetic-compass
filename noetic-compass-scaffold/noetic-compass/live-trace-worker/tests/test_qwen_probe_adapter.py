"""Focused additive coverage for the pinned Qwen Stage B probe adapter.

These are typed local fixtures. They do not load model weights, contact a
provider, execute a scientific experiment, or create an Evidence Packet.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch
from torch import nn

from app.runtime import model_loader
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
