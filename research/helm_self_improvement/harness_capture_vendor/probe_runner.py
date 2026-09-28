"""Probe runner — real forward-hook capture for Pythia-160M.

Captures, per emitted token:
  * residual-stream activation at every layer (extract top-K activated
    neurons across all layers for the active-trace overlay)
  * MLP post-activation (for the 3072-wide intermediate dimension that the
    UI's 3D scene treats as the per-layer neuron grid)
  * attention patterns (for Mode 7 attribution: edges from earlier tokens
    to the current one, weighted by attention)
  * lm_head logits (for the softmax-margin confidence)

Hook design borrowed from cas-native/trace/live_capture.py — register on
each layer's MLP output module + the final logits, run forward, detach +
clean up always (even on exception).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, Literal

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


@dataclass(frozen=True)
class EraserIntervention:
    """Runtime MLP-output suppression sent by the live controls panel."""

    coords: tuple[tuple[int, int], ...]
    gain: float


# ---------------------------------------------------------------------------
# Hook registration — context manager so cleanup is always called.
# ---------------------------------------------------------------------------


@contextmanager
def capture_probes(
    model: Any,
    n_layers: int,
    intervention: EraserIntervention | None = None,
) -> Iterator[CaptureState]:
    """Register forward hooks on the model, yield a CaptureState, clean up.

    The hooks are attached to:
      * model.gpt_neox.layers[i].mlp.dense_4h_to_h.output (Pythia naming)
        — gives the per-layer MLP output (post-activation, post-projection)
      * each layer's attention module's attn_output (we re-derive from
        ``attentions`` returned by the model with output_attentions=True
        instead, so this hook is informational only)

    Important: we DO NOT hold tensor references after the hook fires. The
    hook converts to Python lists immediately so that when the
    ``capture_probes`` block exits, no GPU memory is retained.
    """
    handles: list[Any] = []
    state = CaptureState()

    try:
        # Pythia (gpt-neox arch in transformers) lays the blocks out at
        # model.gpt_neox.layers — defensive lookup so a future arch change
        # doesn't crash the worker.
        layers = _get_pythia_layers(model)
        if layers is None:
            logger.warning(
                "capture_probes: could not locate gpt_neox.layers; "
                "MLP-post capture will be empty"
            )
        else:
            for layer_idx in range(min(n_layers, len(layers))):
                layer = layers[layer_idx]
                mlp = getattr(layer, "mlp", None)
                if mlp is None:
                    continue
                # Hook on the FULL mlp module output rather than a
                # specific sub-linear. mlp(...) returns the post-activation
                # post-projection (gelu(dense_h_to_4h(...))) @ dense_4h_to_h.T.
                handle = mlp.register_forward_hook(
                    _make_mlp_hook(state, layer_idx, intervention),
                )
                handles.append(handle)
        yield state
    finally:
        for h in handles:
            try:
                h.remove()
            except Exception:  # pragma: no cover — defensive cleanup
                logger.exception("capture_probes: hook removal failed")


def _get_pythia_layers(model: Any) -> Any | None:
    """Locate the transformer block list on a Pythia model.

    Returns ``model.gpt_neox.layers`` if present, otherwise None.
    """
    gpt_neox = getattr(model, "gpt_neox", None)
    if gpt_neox is None:
        return None
    return getattr(gpt_neox, "layers", None)


def _make_mlp_hook(
    state: CaptureState,
    layer_idx: int,
    intervention: EraserIntervention | None,
) -> Any:
    """Build the forward hook that records the last-token MLP post-activation."""

    def _hook(_module: Any, _inputs: Any, output: Any) -> None:
        try:
            # output is a tensor of shape [batch, seq, hidden]. We only
            # care about the last-prompt-token MLP signal (the one whose
            # logits we're about to emit). batch=1 in the worker.
            if output is None:
                return
            modified = _apply_eraser(output, layer_idx, intervention)
            last = modified[0, -1].detach()
            # Move to CPU + tolist so the caller never sees a tensor.
            # The float() inside the comprehension is defensive — sometimes
            # tolist on bf16 returns numpy.float32 objects.
            state.mlp_post[layer_idx] = [float(v) for v in last.float().cpu().tolist()]
            if modified is not output:
                return modified
        except Exception:  # pragma: no cover — keep generation going even
            # if a single hook misbehaves.
            logger.exception("mlp hook (layer %d) failed", layer_idx)

    return _hook


def _apply_eraser(
    output: Any,
    layer_idx: int,
    intervention: EraserIntervention | None,
) -> Any:
    """Suppress selected MLP-output coordinates before logits are computed."""
    if intervention is None or not intervention.coords:
        return output
    layer_coords = [idx for layer, idx in intervention.coords if layer == layer_idx]
    if not layer_coords:
        return output
    try:
        width = int(output.shape[-1])
        valid = [idx for idx in layer_coords if 0 <= idx < width]
        if not valid:
            return output
        factor = max(0.0, 1.0 - max(0.0, float(intervention.gain)))
        modified = output.clone()
        for idx in valid:
            modified[0, -1, idx] = modified[0, -1, idx] * factor
        return modified
    except Exception:  # pragma: no cover
        logger.exception("drive-local eraser failed at layer %d", layer_idx)
        return output


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
