"""Masked cross-entropy for reply-only LM training.

The native NL generation head emits logits for every decoder position. For
training, only positions that correspond to real reply tokens should
contribute to the loss; padded positions and the CAS prefix (already stripped
internally by the head) must not. ``masked_cross_entropy`` enforces that.

Usage::

    loss = masked_cross_entropy(out["lm_logits"], batch["lm_targets"], batch["loss_mask"])

If ``mask`` is omitted, positions with ``targets == ignore_index`` are skipped
(the standard ``F.cross_entropy(ignore_index=-100)`` behavior). Both an
explicit mask and ``ignore_index`` may be combined; both must be satisfied
for a position to count.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


def masked_cross_entropy(
    logits: torch.Tensor,
    targets: torch.Tensor,
    mask: torch.Tensor | None = None,
    *,
    ignore_index: int = -100,
    reduction: str = "mean",
    label_smoothing: float = 0.0,
) -> torch.Tensor:
    """Reply-only cross-entropy.

    Args:
        logits: ``(B, L, V)`` — decoder LM logits, vocab on the last dim.
        targets: ``(B, L)`` — long tensor of target token IDs; positions equal
            to ``ignore_index`` are skipped.
        mask: optional ``(B, L)`` bool tensor; True = include, False = skip.
            Combined with ``ignore_index`` via logical AND.
        ignore_index: target value treated as "skip"; default -100.
        reduction: ``"mean"`` (mean over valid positions), ``"sum"``, or
            ``"none"`` (per-position loss tensor with skipped positions = 0).
        label_smoothing: passed to ``F.cross_entropy``.

    Returns:
        A scalar tensor (``mean``/``sum``) or a ``(B, L)`` tensor (``none``).
    """
    if logits.dim() != 3:
        raise ValueError(f"logits must be 3-D (B, L, V); got {tuple(logits.shape)}")
    if targets.dim() != 2:
        raise ValueError(f"targets must be 2-D (B, L); got {tuple(targets.shape)}")
    if logits.shape[:2] != targets.shape:
        raise ValueError(
            f"logits/targets first two dims must match; got "
            f"logits {tuple(logits.shape)} vs targets {tuple(targets.shape)}"
        )
    if mask is not None and mask.shape != targets.shape:
        raise ValueError(
            f"mask must match targets shape; got mask {tuple(mask.shape)} "
            f"vs targets {tuple(targets.shape)}"
        )
    if reduction not in ("mean", "sum", "none"):
        raise ValueError(f"reduction must be mean|sum|none; got {reduction!r}")

    b, l, v = logits.shape

    # Apply mask by overwriting target with ignore_index where mask is False.
    eff_targets = targets
    if mask is not None:
        eff_targets = targets.clone()
        eff_targets[~mask.to(torch.bool)] = ignore_index

    # Per-position cross-entropy with reduction=none, then aggregate ourselves
    # so we control the divisor (number of valid positions).
    flat_logits = logits.reshape(b * l, v)
    flat_targets = eff_targets.reshape(b * l)
    per_pos = F.cross_entropy(
        flat_logits,
        flat_targets,
        ignore_index=ignore_index,
        reduction="none",
        label_smoothing=float(label_smoothing),
    )
    valid = (flat_targets != ignore_index).to(per_pos.dtype)
    n_valid = valid.sum()

    if reduction == "none":
        return (per_pos * valid).reshape(b, l)
    if reduction == "sum":
        return (per_pos * valid).sum()
    # mean — over valid positions only; safe-divide on empty mask.
    if n_valid.item() == 0:
        return torch.zeros((), dtype=per_pos.dtype, device=per_pos.device)
    return (per_pos * valid).sum() / n_valid


__all__ = ["masked_cross_entropy"]
