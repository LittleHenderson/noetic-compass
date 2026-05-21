from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "stage27p_qwen_hook_adapter.py"


def _load_module(name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, ADAPTER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_qwen_style_adapter_finds_paths_and_candidates() -> None:
    adapter = _load_module("stage27p_adapter_paths")

    class SelfAttn(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.o_proj = torch.nn.Linear(4, 4)

    class MLP(torch.nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return x

    class Layer(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.self_attn = SelfAttn()
            self.mlp = MLP()

    class Body(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = torch.nn.ModuleList([Layer(), Layer()])

    class Config:
        hidden_size = 4
        num_attention_heads = 2

    class Model(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.model = Body()
            self.config = Config()

    model = Model()
    summary = adapter.adapter_summary(model, (1,))
    components = adapter.candidate_components((1,), num_heads=2, num_layers=2)

    assert summary["rows"][0]["attention_output_projection"] == "self_attn.o_proj"
    assert summary["rows"][0]["mlp_module"] == "mlp"
    assert [component.name for component in components] == ["L1H0", "L1H1", "L1MLP"]


def test_hook_scales_only_requested_positions() -> None:
    adapter = _load_module("stage27p_adapter_hooks")

    class OProj(torch.nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return x

    class SelfAttn(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.o_proj = OProj()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.o_proj(x)

    class MLP(torch.nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return x

    class Layer(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.self_attn = SelfAttn()
            self.mlp = MLP()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.mlp(self.self_attn(x))

    class Body(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = torch.nn.ModuleList([Layer()])

    class Config:
        hidden_size = 4
        num_attention_heads = 2

    class Model(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.model = Body()
            self.config = Config()

    model = Model()
    x = torch.ones((1, 3, 4))
    handles = adapter.install_component_scale_hooks(
        model,
        component_scales=[([adapter.HookComponent("head", 0, 1)], 0.0)],
        positions=[1],
    )
    try:
        y = model.model.layers[0](x)
    finally:
        for handle in handles:
            handle.remove()

    assert torch.equal(y[:, 0, :], torch.ones((1, 4)))
    assert torch.equal(y[:, 2, :], torch.ones((1, 4)))
    assert torch.equal(y[:, 1, :2], torch.ones((1, 2)))
    assert torch.equal(y[:, 1, 2:], torch.zeros((1, 2)))
