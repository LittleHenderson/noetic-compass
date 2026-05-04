"""Mode 7 forward-hook instrumentation for the CAS-Native model.

This module implements the **hook-plumbing layer** for Mode 7 — Network
Attribution / Mechanistic Trace — described in
``docs/working/exposure_button_traceability_spec.md`` (section 2, Mode 7).

What this module does
---------------------
Walk a CAS-Native model (``nn.Module``) and register **named PyTorch forward
hooks** on every CAS-aligned architectural layer that has interpretable
semantic meaning. Hook names are CAS-aligned and stable
(e.g. ``"domain_descent_attention.layers.2"``,
``"prerequisite_gate_layer.layers.0"``,
``"cognitive_state_embedding"``,
``"cognitive_topos_reasoner"``).

What this module deliberately does NOT do
------------------------------------------
* It does not modify any layer class. Hook attachment is **external** —
  the model code is unchanged. This preserves the v7.4 byte-equivalence
  invariants and the existing test suite.
* It does not implement Mode 7 visualization, attribution, or
  forensic-replay infrastructure. Those are downstream consumers.
* It does not persist captured activations to disk. Storage is
  in-memory only.
* It does not introduce any new model dependencies. Vanilla PyTorch
  forward hooks are used.

Lifecycle
---------
1. ``session = register_named_hooks(model)`` registers the hooks and
   returns a ``HookSession`` whose ``.activations`` dict is populated
   on every subsequent forward pass.
2. The default capture ``mode="full"`` stores the full output tensor
   of each hooked layer. ``mode="sparse_topk"`` with parameter ``k``
   stores only the top-K (by absolute value, last-dim) values per hook,
   plus their indices, at substantially reduced memory cost.
3. ``session.unregister_all()`` cleanly detaches every registered hook.
   After that call, the model's forward behavior is byte-equivalent to
   the un-hooked baseline.

Inference-behavior contract
---------------------------
Forward hooks observe outputs but do not modify them. The capture path
detaches tensors, so the captured copy does not participate in autograd
and cannot leak into the model's computation. When no ``HookSession``
is active (the default), this module imports zero CPU/GPU work into the
forward pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Tuple

import torch
import torch.nn as nn


# Capture mode literals.
CAPTURE_MODE_FULL = "full"
CAPTURE_MODE_SPARSE_TOPK = "sparse_topk"
CaptureMode = Literal["full", "sparse_topk"]


# CAS-aligned class names (by ``__name__``) that should always receive a
# named hook when present in the model. This list is the authoritative
# allow-list for "what counts as a CAS-aligned architectural layer."
# Keep this in sync with the architecture overview in CLAUDE.md.
CAS_ALIGNED_CLASS_NAMES: Tuple[str, ...] = (
    # Cognitive-state surfaces
    "CognitiveStateEmbedding",
    "CognitiveStateEmbeddingWithRegister",
    "StructuredTokenEmbedding",
    # Attention surfaces
    "DomainDescentAttention",
    "FractalAttentionHead",
    # Gating surfaces
    "PrerequisiteGateLayer",
    "LacunarityGate",
    # Composite transformer block (carries pooled per-layer output)
    "CASTransformerLayer",
    # Output / reasoning heads
    "CognitiveToposReasoner",
    "InversionDetector",
    "GenerativeHead",
    "LacunarityHead",
    "ExpressionProposerHead",
    "StructuredPredictionHead",
    # Register surfaces (CAS v7.5)
    "RegisterFiLM",
    "RegisterLatent",
)


def _to_camel_snake(name: str) -> str:
    """Convert a class name like ``DomainDescentAttention`` to
    ``domain_descent_attention``.

    Used to derive a stable, CAS-aligned hook name from the layer's
    Python class name when the layer is not addressed by an attribute
    path.
    """
    out: List[str] = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0 and not name[i - 1].isupper():
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def _maybe_capture(
    output: Any,
    name: str,
    storage: Dict[str, Any],
    mode: CaptureMode,
    k: int,
) -> None:
    """Best-effort capture of a layer output into the session storage.

    The capture is robust to layer outputs that are tensors, tuples, or
    dicts (common in this codebase — e.g. ``PrerequisiteGateLayer``
    returns ``(tensor, dict)``, ``CASTransformerLayer`` returns
    ``(tensor, dict)``, ``StructuredPredictionHead`` returns a dict of
    logits). For non-tensor outputs we capture the leading tensor when
    discoverable; otherwise we silently skip — Mode 7 consumers query
    by hook name, so a missing entry is benign.
    """
    tensor = _extract_leading_tensor(output)
    if tensor is None:
        return
    # Detach so the captured copy does not participate in autograd and
    # cannot back-propagate into the model. This is critical to the
    # "no inference-behavior change" contract.
    detached = tensor.detach()
    if mode == CAPTURE_MODE_SPARSE_TOPK:
        storage[name] = _sparse_topk(detached, k)
    else:
        # Full mode: store the detached tensor directly. We do not
        # ``.clone()`` here — Mode 7 callers that need a stable snapshot
        # across multiple forward passes should clone on read.
        storage[name] = detached


def _extract_leading_tensor(output: Any) -> torch.Tensor | None:
    """Walk a layer output and return the first ``Tensor`` encountered.

    Layer outputs in the CAS-Native model are heterogeneous:

    * Most layers return a single ``Tensor``.
    * ``PrerequisiteGateLayer.forward`` returns ``(Tensor, dict)``.
    * ``CASTransformerLayer.forward`` returns ``(Tensor, dict)``.
    * ``StructuredPredictionHead.forward`` returns a ``dict`` of
      logits — for Mode 7 purposes we capture the first logit tensor,
      which is sufficient as a "this layer fired" signal.

    Returns ``None`` if no tensor can be located, in which case the
    capture is a no-op.
    """
    if isinstance(output, torch.Tensor):
        return output
    if isinstance(output, (tuple, list)):
        for item in output:
            t = _extract_leading_tensor(item)
            if t is not None:
                return t
        return None
    if isinstance(output, dict):
        for value in output.values():
            t = _extract_leading_tensor(value)
            if t is not None:
                return t
        return None
    return None


def _sparse_topk(tensor: torch.Tensor, k: int) -> Dict[str, torch.Tensor]:
    """Return the top-K (by absolute value) entries of ``tensor`` along
    its final dimension, plus their indices.

    The returned dict has fields:

    * ``"values"``  — ``(*leading, K_eff)`` signed values
    * ``"indices"`` — ``(*leading, K_eff)`` long indices into the last dim
    * ``"shape"``   — original tensor shape as a CPU long tensor

    K is automatically clamped to ``min(k, last_dim_size)`` so callers
    do not need to know layer-specific shapes ahead of time.
    """
    if tensor.dim() == 0:
        # Scalar — top-K of a scalar is the scalar itself.
        return {
            "values": tensor.unsqueeze(0),
            "indices": torch.zeros(1, dtype=torch.long, device=tensor.device),
            "shape": torch.tensor(list(tensor.shape), dtype=torch.long),
        }
    last_dim = tensor.shape[-1]
    effective_k = max(1, min(int(k), int(last_dim)))
    abs_tensor = tensor.abs()
    topk = torch.topk(abs_tensor, k=effective_k, dim=-1)
    # Gather the original (signed) values at the top-K indices.
    signed_values = torch.gather(tensor, dim=-1, index=topk.indices)
    return {
        "values": signed_values,
        "indices": topk.indices,
        "shape": torch.tensor(list(tensor.shape), dtype=torch.long),
    }


@dataclass
class HookSession:
    """Handle for a set of registered forward hooks and their captures.

    Returned by :func:`register_named_hooks`. Holds the live PyTorch
    ``RemovableHandle`` objects so the caller can cleanly disengage the
    instrumentation, and the in-memory ``activations`` dict that hook
    callbacks write into on every forward pass.

    Attributes:
        activations: Mapping from CAS-aligned hook name to captured
            tensor (or, in sparse mode, a dict with ``values`` /
            ``indices`` / ``shape``). Cleared on demand via
            :meth:`clear`. Mode 7 consumers READ this dict; the hook
            callbacks WRITE it.
        hook_names: Stable list of every name that was registered.
        mode: The capture mode in effect for this session.
        k: The sparse top-K parameter (only meaningful when
            ``mode == "sparse_topk"``).
    """

    activations: Dict[str, Any] = field(default_factory=dict)
    hook_names: List[str] = field(default_factory=list)
    mode: CaptureMode = CAPTURE_MODE_FULL
    k: int = 32
    _handles: List[Any] = field(default_factory=list)

    def clear(self) -> None:
        """Drop all captured activations without unregistering hooks."""
        self.activations.clear()

    def unregister_all(self) -> None:
        """Remove every hook this session registered.

        After this call the model's forward pass is byte-equivalent to
        the un-instrumented baseline (zero hook overhead). The session
        object itself remains usable as a record of what was registered;
        ``activations`` is cleared as a defensive measure.
        """
        for handle in self._handles:
            try:
                handle.remove()
            except Exception:
                # Defensive — even if a handle has already been removed
                # we want to drain the rest. PyTorch's ``RemovableHandle``
                # is idempotent in practice but we don't depend on it.
                pass
        self._handles.clear()
        self.activations.clear()

    def __len__(self) -> int:
        return len(self.hook_names)

    def __contains__(self, name: object) -> bool:
        return name in self.activations


def register_named_hooks(
    model: nn.Module,
    *,
    mode: CaptureMode = CAPTURE_MODE_FULL,
    k: int = 32,
    extra_class_names: Tuple[str, ...] = (),
) -> HookSession:
    """Walk ``model`` and register a named forward hook on every
    CAS-aligned architectural layer.

    Hook names are derived from the model's named-module path when
    available (e.g. ``"layers.2"``), prefixed with the CAS-aligned class
    name in snake_case (e.g.
    ``"cas_transformer_layer.layers.2"``). When a CAS-aligned module is
    a direct attribute of the model with no submodule path (e.g. the
    model's ``cognitive_embedding``), the snake_case class name alone
    is used. Names are guaranteed stable across forward passes for a
    given model instance; downstream Mode 7 callers can rely on string
    equality.

    The function does NOT mutate the model — it only attaches hooks via
    ``Module.register_forward_hook`` and returns the resulting handles
    inside a :class:`HookSession`. Forward inference behavior is
    unchanged: hooks observe the layer output, detach it, and write it
    into the session's ``activations`` dict.

    Args:
        model: The CAS-Native model (or any subtree of it) to
            instrument.
        mode: Capture mode. ``"full"`` stores the detached output
            tensor; ``"sparse_topk"`` stores only the top-K
            highest-magnitude entries along the last dim plus their
            indices and the original shape.
        k: Top-K parameter for ``"sparse_topk"``. Ignored in
            ``"full"`` mode. Defaults to 32, matching the Mode 7
            spec's recommended live-trace budget (~200 KB / turn).
        extra_class_names: Optional additional class names to treat as
            CAS-aligned for this registration. Useful for experimental
            layers not yet promoted to the canonical allow-list.

    Returns:
        A :class:`HookSession` whose ``activations`` will be populated
        on each subsequent forward pass and whose ``unregister_all``
        cleanly detaches every hook.

    Note:
        Calling this function more than once on the same model produces
        multiple independent sessions. Each session captures
        independently into its own ``activations`` dict; they do not
        interfere. Mode 7 callers that need an exclusive view should
        call ``unregister_all()`` between sessions.
    """
    if mode not in (CAPTURE_MODE_FULL, CAPTURE_MODE_SPARSE_TOPK):
        raise ValueError(
            f"mode must be one of 'full' / 'sparse_topk', got {mode!r}"
        )
    if mode == CAPTURE_MODE_SPARSE_TOPK and k <= 0:
        raise ValueError(f"k must be > 0 for sparse_topk mode, got {k}")

    allowed_classes = set(CAS_ALIGNED_CLASS_NAMES) | set(extra_class_names)
    session = HookSession(mode=mode, k=int(k))
    used_names: Dict[str, int] = {}

    for module_path, submodule in model.named_modules():
        cls_name = type(submodule).__name__
        if cls_name not in allowed_classes:
            continue
        hook_name = _build_hook_name(cls_name, module_path, used_names)
        callback = _make_hook_callback(
            hook_name=hook_name,
            storage=session.activations,
            mode=session.mode,
            k=session.k,
        )
        handle = submodule.register_forward_hook(callback)
        session._handles.append(handle)
        session.hook_names.append(hook_name)

    return session


def _build_hook_name(
    cls_name: str,
    module_path: str,
    used_names: Dict[str, int],
) -> str:
    """Construct a stable, unique CAS-aligned hook name.

    The name prefixes the module path with the class name in
    snake_case. When two modules of the same class share the same path
    (which should not happen, but we defend against), we suffix a
    counter to keep names unique inside a session.
    """
    snake_cls = _to_camel_snake(cls_name)
    if module_path:
        candidate = f"{snake_cls}.{module_path}"
    else:
        candidate = snake_cls
    if candidate not in used_names:
        used_names[candidate] = 1
        return candidate
    used_names[candidate] += 1
    return f"{candidate}#{used_names[candidate]}"


def _make_hook_callback(
    *,
    hook_name: str,
    storage: Dict[str, Any],
    mode: CaptureMode,
    k: int,
) -> Callable[[nn.Module, Any, Any], None]:
    """Build a forward-hook callback bound to ``hook_name`` /
    ``storage``.

    PyTorch forward hooks receive ``(module, input, output)``. This
    callback ignores the inputs (Mode 7 reasons about layer outputs),
    captures the output through :func:`_maybe_capture`, and never
    mutates the output. The callback returns ``None`` so PyTorch leaves
    the original output unchanged in the forward pass.
    """

    def _callback(module: nn.Module, args: Any, output: Any) -> None:
        _maybe_capture(output, hook_name, storage, mode, k)

    _callback.__name__ = f"cas_hook[{hook_name}]"
    return _callback


__all__ = [
    "CAS_ALIGNED_CLASS_NAMES",
    "CAPTURE_MODE_FULL",
    "CAPTURE_MODE_SPARSE_TOPK",
    "HookSession",
    "register_named_hooks",
]
