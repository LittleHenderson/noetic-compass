"""Live PyTorch activation + attribution capture for Mode 7.

This module replaces the v0 stub path inside ``activations.py`` with a real
forward-hook implementation. It is the load-bearing wire-up between the trace
scaffold and the live ``StructuredTokenStructuredPredictor``.

Public surface:

* ``LiveTrace`` — full per-prediction trace dataclass: layer activations,
  bottleneck top-K, per-head argmax+confidence, attention-pattern entropy
  summary, and gradient×input attribution per head on the bottleneck.

* ``capture_live_trace(model, batch, ...)`` — register hooks, run the forward
  pass, compute attribution via a single backward pass, detach and clean up
  hooks (always, including on exception), return a populated ``LiveTrace``.

Hooks are registered on:

* the embedding's ``output_norm`` (deepest pre-pool layer — the closest
  analogue this architecture has to a "transformer block" output),
* the embedding's fused output (the layer immediately before pooling),
* the shared ``head.backbone`` (post-bottleneck z vector),
* each of the 12 head linear layers.

The ``LiveTrace`` data class is JSON-serializable via ``to_dict()``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import torch
import torch.nn as nn

from cas_native.trace.activations import HEAD_NAMES


HEAD_ATTR_NAMES: tuple[str, ...] = (
    "turn_type_head",
    "expression_family_head",
    "transition_kind_head",
    "noetic_head",
    "domain_head",
    "drive_head",
    "register_head",
    "register_mode_head",
    "meta_relation_head",
    "authority_head",
    "omega_head",
    "meta_logic_head",
)
"""Head module attribute names on ``StructuredPredictionHead``, in canonical
order matching ``HEAD_NAMES``."""

MULTI_LABEL_HEADS = frozenset({"register", "meta_relation"})


@dataclass
class LayerActivation:
    """A single hooked layer's captured output.

    Stored as plain Python lists so the LiveTrace surface stays JSON-friendly.
    The original tensor shape is preserved as ``shape``; the flattened values
    are kept as ``flat`` (truncated to ``max_dump`` for the JSON path).
    """

    name: str
    shape: tuple[int, ...]
    l2_norm: float
    mean_abs: float
    max_abs: float
    flat_preview: list[float]
    """First ``max_preview`` values, useful for diffing across runs."""


@dataclass
class HeadInfo:
    """Per-head argmax / confidence / attribution summary."""

    name: str
    argmax_index: int
    argmax_label: str | None
    confidence: float
    """Softmax-max for scalar heads; mean(sigmoid(active_logits)) for
    multi-label heads (registers, meta_relation)."""
    top_k_attribution: list[tuple[int, float]]
    """``[(bottleneck_dim_index, signed_attribution_score), ...]`` sorted by
    ``|score|`` descending. Lengths match ``top_k`` from ``capture_live_trace``."""
    raw_logits: list[float]


@dataclass
class LiveTrace:
    """Full per-prediction live trace.

    Stable, JSON-serializable surface. Consumers should treat all fields as
    read-only (the dataclass is mutable for population convenience but is not
    intended to be mutated post-capture).
    """

    schema_version: str = "live_trace.v1"
    input_text: str = ""
    layer_activations: list[LayerActivation] = field(default_factory=list)
    bottleneck: list[float] = field(default_factory=list)
    bottleneck_top_k: list[tuple[int, float]] = field(default_factory=list)
    heads: list[HeadInfo] = field(default_factory=list)
    attention_entropy_summary: dict[str, float] = field(default_factory=dict)
    """Summary of the attention/gating pattern at the embedding fusion gate.
    Keys: ``mean``, ``min``, ``max``, ``token_count``."""
    hook_status: dict[str, bool] = field(default_factory=dict)
    """Maps hook target name -> whether it fired during the forward pass."""
    diagnostics: list[str] = field(default_factory=list)
    timing: dict[str, float] = field(default_factory=dict)

    def head(self, name: str) -> HeadInfo | None:
        for h in self.heads:
            if h.name == name:
                return h
        return None

    def to_dict(self) -> dict[str, Any]:
        """JSON-friendly nested dict. All numbers are plain ``float``/``int``."""
        return {
            "schema_version": self.schema_version,
            "input_text": self.input_text,
            "layer_activations": [
                {
                    "name": la.name,
                    "shape": list(la.shape),
                    "l2_norm": float(la.l2_norm),
                    "mean_abs": float(la.mean_abs),
                    "max_abs": float(la.max_abs),
                    "flat_preview": [float(v) for v in la.flat_preview],
                }
                for la in self.layer_activations
            ],
            "bottleneck": [float(v) for v in self.bottleneck],
            "bottleneck_top_k": [
                [int(i), float(v)] for i, v in self.bottleneck_top_k
            ],
            "heads": [
                {
                    "name": h.name,
                    "argmax_index": int(h.argmax_index),
                    "argmax_label": h.argmax_label,
                    "confidence": float(h.confidence),
                    "top_k_attribution": [
                        [int(i), float(s)] for i, s in h.top_k_attribution
                    ],
                    "raw_logits": [float(v) for v in h.raw_logits],
                }
                for h in self.heads
            ],
            "attention_entropy_summary": {
                k: float(v) for k, v in self.attention_entropy_summary.items()
            },
            "hook_status": dict(self.hook_status),
            "diagnostics": list(self.diagnostics),
            "timing": {k: float(v) for k, v in self.timing.items()},
        }


def capture_live_trace(
    model: nn.Module,
    batch: Any,
    *,
    input_text: str = "",
    top_k: int = 3,
    head_label_tables: dict[str, tuple[str, ...]] | None = None,
    compute_attribution: bool = True,
) -> tuple[dict[str, torch.Tensor], LiveTrace]:
    """Run ``model`` on ``batch`` with forward hooks, capture activations.

    Hooks are registered before the forward pass and ALWAYS removed afterwards
    — even if the forward (or backward) raises. Activations are detached, moved
    to CPU, and converted to plain Python lists immediately after capture so
    the returned ``LiveTrace`` does not retain any GPU/autograd state.

    Args:
        model: a ``StructuredTokenStructuredPredictor`` (or any module exposing
            ``.embedding`` and ``.head`` with the canonical sub-attributes).
        batch: a ``StructuredTokenBatch`` to feed through the model.
        input_text: the original user input string, recorded on the trace.
        top_k: number of top attribution dims to surface per head.
        head_label_tables: optional ``{head_name: (labels...)}`` for argmax
            label decoding. Heads not in the dict get ``argmax_label=None``.
        compute_attribution: if True, run a single backward pass per head's
            argmax logit to compute ``gradient × input`` attribution on the
            bottleneck. If False, attribution is empty (faster, no_grad path).

    Returns:
        ``(outputs, trace)`` — ``outputs`` is the original head logits dict
        (so callers can decode predictions normally), ``trace`` is the
        populated ``LiveTrace``.

    Raises:
        TypeError: if ``model`` is missing the expected attributes.
    """
    import time

    if not hasattr(model, "embedding") or not hasattr(model, "head"):
        raise TypeError(
            "capture_live_trace requires a StructuredTokenStructuredPredictor-"
            "shaped model (with .embedding and .head attributes); "
            f"got {type(model).__name__}"
        )

    head_module = model.head
    embedding_module = model.embedding

    if not hasattr(head_module, "backbone"):
        raise TypeError(
            "model.head must expose a `backbone` Sequential; "
            f"got {type(head_module).__name__}"
        )

    captured: dict[str, torch.Tensor] = {}
    hook_status: dict[str, bool] = {}
    handles: list[torch.utils.hooks.RemovableHandle] = []

    def _make_hook(key: str, *, retain: bool):
        def _hook(_module: nn.Module, _input: tuple, output: torch.Tensor) -> None:
            hook_status[key] = True
            if isinstance(output, torch.Tensor):
                tensor = output
            elif isinstance(output, tuple) and output and isinstance(output[0], torch.Tensor):
                tensor = output[0]
            else:
                hook_status[key] = False
                return
            if retain:
                # Need to retain grad for backward attribution.
                tensor.retain_grad()
                captured[key] = tensor
            else:
                captured[key] = tensor.detach()
        return _hook

    # Targets to register hooks on.
    targets: list[tuple[str, nn.Module, bool]] = []
    targets.append(("embedding_output", embedding_module, False))
    if hasattr(embedding_module, "output_norm") and isinstance(
        embedding_module.output_norm, nn.Module
    ):
        targets.append(("embedding_output_norm", embedding_module.output_norm, False))
    if hasattr(embedding_module, "fusion_gate") and isinstance(
        embedding_module.fusion_gate, nn.Module
    ):
        targets.append(("embedding_fusion_gate", embedding_module.fusion_gate, False))
    targets.append(("bottleneck", head_module.backbone, True))

    head_keys: list[str] = []
    for short_name, attr_name in zip(HEAD_NAMES, HEAD_ATTR_NAMES):
        sub = getattr(head_module, attr_name, None)
        if sub is None:
            continue
        key = f"head:{short_name}"
        head_keys.append(key)
        targets.append((key, sub, False))

    for key, module, retain in targets:
        hook_status[key] = False
        handles.append(module.register_forward_hook(_make_hook(key, retain=retain)))

    diagnostics: list[str] = []
    timing: dict[str, float] = {}

    try:
        was_training = model.training
        model.eval()
        try:
            grad_ctx = torch.enable_grad() if compute_attribution else torch.no_grad()
            t_fwd_start = time.perf_counter()
            with grad_ctx:
                outputs = model(batch)
                if not isinstance(outputs, dict):
                    raise TypeError(
                        "model forward must return a dict of head logits; "
                        f"got {type(outputs).__name__}"
                    )
            t_fwd_end = time.perf_counter()
            timing["forward_ms"] = (t_fwd_end - t_fwd_start) * 1000.0

            # Build the trace from captured activations.
            trace = _build_trace_from_captures(
                captured=captured,
                hook_status=hook_status,
                head_keys=head_keys,
                outputs=outputs,
                top_k=top_k,
                head_label_tables=head_label_tables or {},
                input_text=input_text,
                diagnostics=diagnostics,
            )

            if compute_attribution and "bottleneck" in captured:
                t_attr_start = time.perf_counter()
                _populate_attribution(
                    trace=trace,
                    bottleneck_tensor=captured["bottleneck"],
                    outputs=outputs,
                    top_k=top_k,
                )
                t_attr_end = time.perf_counter()
                timing["attribution_ms"] = (t_attr_end - t_attr_start) * 1000.0
            else:
                timing["attribution_ms"] = 0.0
                if compute_attribution:
                    diagnostics.append(
                        "attribution_skipped_bottleneck_not_captured"
                    )

            trace.timing = dict(timing)
            trace.diagnostics = list(diagnostics) + list(trace.diagnostics)
        finally:
            if was_training:
                model.train()

        # Detach outputs before returning: the bottleneck retained its graph
        # to support attribution, so other downstream callers should not see
        # that.
        detached_outputs = {
            k: v.detach() if isinstance(v, torch.Tensor) else v
            for k, v in outputs.items()
        }
        return detached_outputs, trace
    finally:
        # Hooks MUST be removed even on exception.
        for h in handles:
            try:
                h.remove()
            except Exception:
                pass


def _build_trace_from_captures(
    *,
    captured: dict[str, torch.Tensor],
    hook_status: dict[str, bool],
    head_keys: list[str],
    outputs: dict[str, torch.Tensor],
    top_k: int,
    head_label_tables: dict[str, tuple[str, ...]],
    input_text: str,
    diagnostics: list[str],
) -> LiveTrace:
    trace = LiveTrace(input_text=input_text, hook_status=dict(hook_status))

    # Layer activations: detached snapshots for the dashboard / log.
    layer_keys = [
        k for k in (
            "embedding_output",
            "embedding_output_norm",
            "embedding_fusion_gate",
            "bottleneck",
        )
        if k in captured
    ]
    for key in layer_keys:
        tensor = captured[key].detach().to("cpu")
        trace.layer_activations.append(_layer_activation(key, tensor))

    # Bottleneck top-K.
    if "bottleneck" in captured:
        z = captured["bottleneck"].detach().to("cpu")
        # Use first row (batch=1).
        if z.dim() == 2 and z.shape[0] >= 1:
            z_vec = z[0].tolist()
        elif z.dim() == 1:
            z_vec = z.tolist()
        else:
            z_vec = z.flatten().tolist()[: int(z.shape[-1])]
        trace.bottleneck = [float(v) for v in z_vec]
        indexed = list(enumerate(z_vec))
        indexed.sort(key=lambda pair: abs(pair[1]), reverse=True)
        trace.bottleneck_top_k = [
            (int(i), float(v)) for i, v in indexed[: max(1, top_k)]
        ]
    else:
        diagnostics.append("bottleneck_not_captured")

    # Attention-pattern entropy summary, derived from the fusion-gate
    # activation. The fusion gate is the "soft attention" of this architecture.
    if "embedding_fusion_gate" in captured:
        gate = captured["embedding_fusion_gate"].detach().to("cpu")
        # gate shape: (B, seq_len, d_model). Mean across d_model -> per-token
        # gating magnitude. Then compute entropy of the normalized magnitudes
        # across tokens.
        if gate.dim() == 3 and gate.shape[1] >= 1:
            per_tok = gate[0].abs().mean(dim=-1)
            tok_count = int(per_tok.shape[0])
            total = float(per_tok.sum().item())
            if total > 0.0:
                p = per_tok / per_tok.sum()
                entropy = float(
                    -(p * (p.clamp_min(1e-12)).log()).sum().item()
                )
            else:
                entropy = 0.0
            trace.attention_entropy_summary = {
                "mean": float(per_tok.mean().item()),
                "min": float(per_tok.min().item()),
                "max": float(per_tok.max().item()),
                "entropy": entropy,
                "token_count": float(tok_count),
            }
    else:
        trace.attention_entropy_summary = {
            "mean": 0.0,
            "min": 0.0,
            "max": 0.0,
            "entropy": 0.0,
            "token_count": 0.0,
        }

    # Per-head info: argmax + confidence + raw logits.
    logit_key_map = {
        "turn_type": "turn_type_logits",
        "expression_family": "expression_family_logits",
        "transition_kind": "transition_kind_logits",
        "noetic": "noetic_logits",
        "domain": "domain_logits",
        "drive": "drive_logits",
        "register": "register_logits",
        "register_mode": "register_mode_logits",
        "meta_relation": "meta_relation_logits",
        "authority": "authority_logits",
        "omega": "omega_logits",
        "meta_logic": "meta_logic_logits",
    }
    for short_name in HEAD_NAMES:
        logit_key = logit_key_map[short_name]
        if logit_key not in outputs:
            continue
        logits = outputs[logit_key].detach().to("cpu")
        if logits.dim() == 2 and logits.shape[0] >= 1:
            row = logits[0].tolist()
        else:
            row = logits.flatten().tolist()
        if not row:
            continue
        argmax_index = int(max(range(len(row)), key=lambda i: row[i]))
        labels = head_label_tables.get(short_name)
        argmax_label = (
            labels[argmax_index]
            if labels is not None and argmax_index < len(labels)
            else None
        )
        confidence = _confidence_for_head(short_name, row)
        trace.heads.append(
            HeadInfo(
                name=short_name,
                argmax_index=argmax_index,
                argmax_label=argmax_label,
                confidence=confidence,
                top_k_attribution=[],
                raw_logits=[float(v) for v in row],
            )
        )

    return trace


def _populate_attribution(
    *,
    trace: LiveTrace,
    bottleneck_tensor: torch.Tensor,
    outputs: dict[str, torch.Tensor],
    top_k: int,
) -> None:
    """Compute gradient × input attribution per head on the bottleneck.

    For each head, we backprop the head's argmax logit (or, for multi-label
    heads, the highest-magnitude logit) into the captured bottleneck tensor
    and record ``grad * z`` as the per-dimension attribution score. Top-K dims
    by ``|score|`` are recorded on the head.

    A separate backward is run per head using ``retain_graph=True`` so the
    graph survives across heads. The bottleneck has ``retain_grad()`` set in
    the forward hook.
    """
    logit_key_map = {
        "turn_type": "turn_type_logits",
        "expression_family": "expression_family_logits",
        "transition_kind": "transition_kind_logits",
        "noetic": "noetic_logits",
        "domain": "domain_logits",
        "drive": "drive_logits",
        "register": "register_logits",
        "register_mode": "register_mode_logits",
        "meta_relation": "meta_relation_logits",
        "authority": "authority_logits",
        "omega": "omega_logits",
        "meta_logic": "meta_logic_logits",
    }

    n_heads = len(HEAD_NAMES)
    for idx, short_name in enumerate(HEAD_NAMES):
        logit_key = logit_key_map[short_name]
        if logit_key not in outputs:
            continue
        logits = outputs[logit_key]
        if logits.dim() != 2 or logits.shape[0] < 1:
            continue
        row = logits[0]
        # Pick the max-magnitude logit for multi-label heads (so the gradient
        # flows on the dim the head is most committed to); pick argmax for
        # scalar heads.
        if short_name in MULTI_LABEL_HEADS:
            tgt_idx = int(row.abs().argmax().item())
        else:
            tgt_idx = int(row.argmax().item())
        target = row[tgt_idx]

        # Zero existing grad on the bottleneck.
        if bottleneck_tensor.grad is not None:
            bottleneck_tensor.grad = None

        retain = idx < n_heads - 1
        try:
            target.backward(retain_graph=retain)
        except RuntimeError:
            # Backward failed (e.g. graph already freed); skip remaining heads.
            trace.diagnostics.append(
                f"attribution_backward_failed:{short_name}"
            )
            break

        if bottleneck_tensor.grad is None:
            trace.diagnostics.append(
                f"attribution_no_grad:{short_name}"
            )
            continue

        grad = bottleneck_tensor.grad.detach()
        z = bottleneck_tensor.detach()
        if grad.dim() == 2:
            grad_row = grad[0]
            z_row = z[0]
        else:
            grad_row = grad.flatten()
            z_row = z.flatten()
        attr = (grad_row * z_row).cpu().tolist()
        indexed = list(enumerate(attr))
        indexed.sort(key=lambda pair: abs(pair[1]), reverse=True)
        top = indexed[: max(1, top_k)]
        head_info = trace.head(short_name)
        if head_info is not None:
            head_info.top_k_attribution = [
                (int(i), float(s)) for i, s in top
            ]


def _confidence_for_head(name: str, logits: list[float]) -> float:
    if not logits:
        return 0.0
    if name in MULTI_LABEL_HEADS:
        sigs = [_sigmoid(v) for v in logits]
        actives = [s for s, v in zip(sigs, logits) if v > 0.0]
        if actives:
            return sum(actives) / len(actives)
        return max(sigs)
    sm = _softmax(logits)
    return max(sm)


def _layer_activation(name: str, tensor: torch.Tensor) -> LayerActivation:
    flat = tensor.flatten()
    n = int(flat.numel())
    if n == 0:
        return LayerActivation(
            name=name,
            shape=tuple(int(x) for x in tensor.shape),
            l2_norm=0.0,
            mean_abs=0.0,
            max_abs=0.0,
            flat_preview=[],
        )
    return LayerActivation(
        name=name,
        shape=tuple(int(x) for x in tensor.shape),
        l2_norm=float(flat.pow(2).sum().sqrt().item()),
        mean_abs=float(flat.abs().mean().item()),
        max_abs=float(flat.abs().max().item()),
        flat_preview=[float(flat[i].item()) for i in range(min(8, n))],
    )


def _softmax(logits: list[float]) -> list[float]:
    if not logits:
        return []
    m = max(logits)
    exps = [math.exp(v - m) for v in logits]
    s = sum(exps) or 1.0
    return [e / s for e in exps]


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


__all__ = [
    "HEAD_ATTR_NAMES",
    "HeadInfo",
    "LayerActivation",
    "LiveTrace",
    "capture_live_trace",
]
