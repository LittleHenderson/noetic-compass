"""Qwen component hook adapter for Stage 27P.

The Pythia Stage 27J-27O hooks use GPT-NeoX module names. Qwen2.5 uses a
decoder-layer shape with ``self_attn.o_proj`` and ``mlp`` modules. This adapter
provides the small component-scaling surface needed before cross-architecture
eraser-cover steering can be run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HookComponent:
    kind: str
    layer: int
    head: int | None = None

    @property
    def name(self) -> str:
        if self.kind == "head":
            return f"L{self.layer}H{self.head}"
        return f"L{self.layer}MLP"


def component_from_name(name: str) -> HookComponent:
    if "MLP" in name:
        layer = int(name[1 : name.index("MLP")])
        return HookComponent("mlp", layer, None)
    layer_s, head_s = name.split("H", 1)
    return HookComponent("head", int(layer_s[1:]), int(head_s))


def model_layers(model: Any) -> Any:
    if hasattr(model, "model") and hasattr(model.model, "layers"):
        return model.model.layers
    if hasattr(model, "gpt_neox") and hasattr(model.gpt_neox, "layers"):
        return model.gpt_neox.layers
    if hasattr(model, "layers"):
        return model.layers
    raise AttributeError("could not locate transformer layers on model")


def attention_output_projection(layer: Any) -> tuple[Any, str]:
    if hasattr(layer, "self_attn") and hasattr(layer.self_attn, "o_proj"):
        return layer.self_attn.o_proj, "self_attn.o_proj"
    if hasattr(layer, "attention") and hasattr(layer.attention, "dense"):
        return layer.attention.dense, "attention.dense"
    if hasattr(layer, "self_attn") and hasattr(layer.self_attn, "dense"):
        return layer.self_attn.dense, "self_attn.dense"
    raise AttributeError("could not locate attention output projection on layer")


def mlp_module(layer: Any) -> tuple[Any, str]:
    if hasattr(layer, "mlp"):
        return layer.mlp, "mlp"
    if hasattr(layer, "feed_forward"):
        return layer.feed_forward, "feed_forward"
    raise AttributeError("could not locate MLP module on layer")


def prediction_positions(prompt_len: int, continuation_len: int) -> tuple[int, ...]:
    if prompt_len <= 0 or continuation_len <= 0:
        raise ValueError("prompt and continuation lengths must be positive")
    return tuple(prompt_len + offset - 1 for offset in range(continuation_len))


def candidate_components(candidate_layers: tuple[int, ...], num_heads: int, num_layers: int) -> list[HookComponent]:
    if num_heads <= 0:
        raise ValueError("num_heads must be positive")
    bad_layers = [int(layer) for layer in candidate_layers if int(layer) < 0 or int(layer) >= num_layers]
    if bad_layers:
        raise ValueError(f"candidate layers outside 0..{num_layers - 1}: {bad_layers}")
    components: list[HookComponent] = []
    for layer in candidate_layers:
        components.extend(HookComponent("head", int(layer), head) for head in range(num_heads))
        components.append(HookComponent("mlp", int(layer), None))
    return components


def component_scale_targets(
    component_scales: list[tuple[list[HookComponent], float]] | None,
) -> tuple[dict[int, dict[int, float]], dict[int, float]]:
    head_targets: dict[int, dict[int, float]] = {}
    mlp_targets: dict[int, float] = {}
    for components, scale in component_scales or []:
        for component in components:
            if component.kind == "head":
                if component.head is None:
                    raise ValueError(f"head component missing head index: {component}")
                head_targets.setdefault(int(component.layer), {})[int(component.head)] = float(scale)
            elif component.kind == "mlp":
                mlp_targets[int(component.layer)] = float(scale)
            else:
                raise ValueError(f"unknown component kind {component.kind!r}")
    return head_targets, mlp_targets


def install_component_scale_hooks(
    model: Any,
    *,
    component_scales: list[tuple[list[HookComponent], float]] | None,
    positions: list[int],
) -> list[Any]:
    if not component_scales:
        return []
    layers = model_layers(model)
    head_targets, mlp_targets = component_scale_targets(component_scales)
    num_heads = int(model.config.num_attention_heads)
    head_dim = int(model.config.hidden_size // num_heads)
    handles: list[Any] = []

    def make_head_hook(layer_idx: int):
        targets = dict(head_targets.get(layer_idx, {}))

        def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
            x = inputs[0].clone()
            for pos in positions:
                for head, scale in targets.items():
                    start = int(head) * head_dim
                    stop = start + head_dim
                    x[:, pos, start:stop] = x[:, pos, start:stop] * float(scale)
            return (x, *inputs[1:])

        return hook

    def make_mlp_hook(layer_idx: int):
        scale = float(mlp_targets[layer_idx])

        def hook(_module: Any, _inputs: tuple[Any, ...], output: Any) -> Any:
            if isinstance(output, tuple):
                y = output[0].clone()
                rest = output[1:]
                for pos in positions:
                    y[:, pos, :] = y[:, pos, :] * scale
                return (y, *rest)
            y = output.clone()
            for pos in positions:
                y[:, pos, :] = y[:, pos, :] * scale
            return y

        return hook

    for layer_idx in sorted(head_targets):
        module, _path = attention_output_projection(layers[layer_idx])
        handles.append(module.register_forward_pre_hook(make_head_hook(layer_idx)))
    for layer_idx in sorted(mlp_targets):
        module, _path = mlp_module(layers[layer_idx])
        handles.append(module.register_forward_hook(make_mlp_hook(layer_idx)))
    return handles


def adapter_summary(model: Any, candidate_layers: tuple[int, ...]) -> dict[str, Any]:
    layers = model_layers(model)
    rows: list[dict[str, Any]] = []
    for layer_idx in candidate_layers:
        _attn, attn_path = attention_output_projection(layers[int(layer_idx)])
        _mlp, mlp_path = mlp_module(layers[int(layer_idx)])
        rows.append(
            {
                "layer": int(layer_idx),
                "attention_output_projection": attn_path,
                "mlp_module": mlp_path,
            }
        )
    return {
        "num_layers": int(len(layers)),
        "num_attention_heads": int(model.config.num_attention_heads),
        "hidden_size": int(model.config.hidden_size),
        "head_dim": int(model.config.hidden_size // model.config.num_attention_heads),
        "candidate_layers": [int(layer) for layer in candidate_layers],
        "rows": rows,
    }
