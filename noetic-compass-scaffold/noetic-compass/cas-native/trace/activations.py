"""Per-layer activation capture for Mode 7.

This module owns the lifecycle of forward hooks against a CAS-Native structured-
prediction model. The shape it captures is::

    pre_bottleneck     : (B, d_model)              -- pooled hidden state, pre-backbone
    post_bottleneck    : (B, bottleneck_dim)        -- post-backbone z vector
    per_head_logits    : dict[head_name -> Tensor]  -- the 12 head outputs

In v0, the implementation is a stub: the public surface is real, returns
correctly-shaped Python objects, and exercises the same interface a real
implementation will. The stub is gated behind a ``model is None`` (or
``hasattr(model, "_stub_mode")``) check; the diagnostics list flags it.

When the real implementation lands (Follow-on 1 in the spec), the only changes
are inside this module and ``attribution.py``; the public ``MechanisticTrace``
shape and the ``trace_prediction`` signature are stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

# Heads in the order ``StructuredPredictionHead`` exposes them. Importing the
# real labels would create a hard import-time torch dependency for tooling code
# that only consumes traces, so we duplicate the head names here as a stable
# string list. The duplication is intentional: the trace package describes
# predictions, not models.
HEAD_NAMES: tuple[str, ...] = (
    "turn_type",
    "expression_family",
    "transition_kind",
    "noetic",
    "domain",
    "drive",
    "register",
    "register_mode",
    "meta_relation",
    "authority",
    "omega",
    "meta_logic",
)

# Multi-label heads (sigmoid + threshold; not softmax + argmax).
MULTI_LABEL_HEADS: frozenset[str] = frozenset({"register", "meta_relation"})

# Default bottleneck dimension; matches StructuredPredictionHead's default.
DEFAULT_BOTTLENECK_DIM: int = 64
# Default model dimension for the stub path.
DEFAULT_D_MODEL: int = 256


@dataclass
class ActivationCapture:
    """A single forward pass's captured activations.

    Fields are plain Python so the trace surface is decoupled from torch. The
    real implementation populates ``pre_bottleneck`` and ``post_bottleneck`` from
    detached tensor ``.tolist()`` calls; per_head_logits is a flat
    ``dict[str, list[float]]``.

    Stub behaviour: deterministic mock activations that depend on a hash of
    ``input_text`` so traces are reproducible across runs without a model.
    """

    pre_bottleneck: list[float] = field(default_factory=list)
    post_bottleneck: list[float] = field(default_factory=list)
    per_head_logits: dict[str, list[float]] = field(default_factory=dict)
    attention_matrices: list[list[list[float]]] = field(default_factory=list)
    """Per-layer ``(seq_len, seq_len)`` attention matrices, mean-pooled across
    attention heads. Used by attention rollout. Empty in v0 stub."""

    hook_status: dict[str, bool] = field(default_factory=dict)
    """Tells callers whether each hook fired. v0 stub returns all False."""

    diagnostics: list[str] = field(default_factory=list)
    """Human-readable warnings (e.g. ``"stub_capture_no_model"``)."""


def compute_with_hooks(
    model: Any | None,
    input_text: str,
    *,
    bottleneck_dim: int = DEFAULT_BOTTLENECK_DIM,
    d_model: int = DEFAULT_D_MODEL,
) -> ActivationCapture:
    """Run ``model`` on ``input_text``, capture pre/post-bottleneck activations.

    Args:
        model: a structured-prediction-bearing nn.Module, OR None for the stub
            path. The stub generates deterministic activations from the input
            string so smoke tests don't need a checkpoint.
        input_text: the user input string.
        bottleneck_dim: width of the post-backbone bottleneck.
        d_model: width of the pre-backbone hidden state.

    Returns:
        An ``ActivationCapture`` populated with the captured tensors as plain
        lists.

    The real implementation will:
      1. Attach forward hooks on the model's last hidden-state-producing layer
         and on ``head.backbone``.
      2. Run a forward pass with no_grad.
      3. Detach captured tensors, ``.cpu().tolist()`` them, return.
      4. Remove hooks (always, including on exception).
    """
    if model is None:
        return _stub_capture(
            input_text,
            bottleneck_dim=bottleneck_dim,
            d_model=d_model,
        )

    # --- BEGIN: Real implementation lands here in Follow-on 1 ---
    # See spec §4.1. For v0 we fall back to the stub path and flag a diagnostic
    # so callers can fail-fast in production.
    capture = _stub_capture(
        input_text,
        bottleneck_dim=bottleneck_dim,
        d_model=d_model,
    )
    capture.diagnostics.append(
        "stub_capture_real_path_not_implemented"
    )
    return capture
    # --- END ---


def _stub_capture(
    input_text: str,
    *,
    bottleneck_dim: int,
    d_model: int,
) -> ActivationCapture:
    """Deterministic mock activations from a hash of ``input_text``.

    The values are NOT meaningful; their only job is to be correctly shaped,
    reproducible, and varying with the input so that downstream summarizers
    have something non-trivial to chew on in tests.
    """
    seed = _stable_hash(input_text)
    pre = [_pseudo_float(seed, i, scale=1.5) for i in range(d_model)]
    post = [_pseudo_float(seed, i + 10_000, scale=2.0) for i in range(bottleneck_dim)]
    per_head: dict[str, list[float]] = {}
    for head_idx, name in enumerate(HEAD_NAMES):
        # logits widths: turn_type=11, family=6, transition=13, noetic=10,
        # domain=4, drive=7, register=4, register_mode=5, meta_relation=9,
        # authority=3, omega=2, meta_logic=2.
        widths = {
            "turn_type": 11,
            "expression_family": 6,
            "transition_kind": 13,
            "noetic": 10,
            "domain": 4,
            "drive": 7,
            "register": 4,
            "register_mode": 5,
            "meta_relation": 9,
            "authority": 3,
            "omega": 2,
            "meta_logic": 2,
        }
        width = widths[name]
        per_head[name] = [
            _pseudo_float(seed, head_idx * 1000 + 50_000 + i, scale=3.0)
            for i in range(width)
        ]
    return ActivationCapture(
        pre_bottleneck=pre,
        post_bottleneck=post,
        per_head_logits=per_head,
        attention_matrices=[],
        hook_status={
            "pre_bottleneck_captured": False,
            "post_bottleneck_captured": False,
            "attention_captured": False,
        },
        diagnostics=["stub_capture_no_model"] if input_text else [
            "stub_capture_no_model",
            "empty_input",
        ],
    )


def _stable_hash(text: str) -> int:
    """A small stable hash, stdlib only.

    Python's built-in hash() is randomized per-process; for reproducibility
    across runs and across processes we use FNV-1a 32-bit.
    """
    hval = 0x811C9DC5
    for ch in text:
        hval ^= ord(ch) & 0xFF
        hval = (hval * 0x01000193) & 0xFFFFFFFF
    return hval


def _pseudo_float(seed: int, idx: int, *, scale: float) -> float:
    """Deterministic pseudo-random float in roughly [-scale, +scale]."""
    # Linear congruential mix. Cheap, stdlib only, deterministic.
    mixed = (seed * 1103515245 + idx * 12345 + 1) & 0x7FFFFFFF
    norm = (mixed % 1_000_003) / 1_000_003.0  # [0, 1)
    return (norm * 2.0 - 1.0) * scale


def head_logit_widths() -> dict[str, int]:
    """The number of output logits per head. Useful for downstream consumers."""
    return {
        "turn_type": 11,
        "expression_family": 6,
        "transition_kind": 13,
        "noetic": 10,
        "domain": 4,
        "drive": 7,
        "register": 4,
        "register_mode": 5,
        "meta_relation": 9,
        "authority": 3,
        "omega": 2,
        "meta_logic": 2,
    }


def is_multi_label(head_name: str) -> bool:
    return head_name in MULTI_LABEL_HEADS


def iter_head_names() -> Iterable[str]:
    return iter(HEAD_NAMES)
