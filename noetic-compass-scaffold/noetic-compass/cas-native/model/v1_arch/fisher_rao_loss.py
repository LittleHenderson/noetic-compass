"""Fisher-Rao geodesic distance and loss on the open simplex Δ°₃₉.

Per CAS Correction 4 (CLAUDE.md):

    g^FR_p(u, v) = Σ (u_k * v_k / p_k)
    d(p, q)      = 2 * arccos(Σ √(p_k * q_k))

Distance is bounded in ``[0, π]`` and is the natural Riemannian metric
induced by the Fisher information matrix on the probability simplex.

This module supplies:

- :func:`fisher_rao_distance` — the geodesic distance between two
  simplex distributions (``... × K`` shape, returns ``...``).
- :func:`smooth_one_hot` — convert an integer class index to a smoothed
  one-hot row staying strictly inside the open simplex (``0.999 *
  one_hot + 0.001 / K * uniform``); load-bearing because raw one-hots
  ``log(0)`` the metric.
- :class:`FisherRaoLoss` — distance from the predicted simplex to a
  smoothed-one-hot ground truth, plus an optional drift penalty over
  consecutive frames of the encoder's per-step trace.

C-1 design notes:

- Computation runs in float64 internally and is cast back to the
  caller dtype on return. This keeps ``d(p, p) == 0`` numerically
  pinned and avoids ``arccos`` exploding near 1.0.
- The drift penalty discourages thrashing — adjacent ``p_t``,
  ``p_{t+1}`` rows of the trace shouldn't be wildly different unless
  the model genuinely needs to swing the distribution. It's an
  auxiliary regularizer, weighted by ``drift_weight`` (default
  small).
- Smoothing constant ``epsilon_smooth=0.001`` matches Path C C-1
  spec ("``GT = 0.999 * one_hot + 0.001/40 * uniform``").

Reuse policy: the project already has
``cas_native.model.loss.fisher_rao_distance``. We re-implement here
to keep the v1_arch module self-contained per the C-1 deliverable
("everything in v1_arch/"). The two implementations are tested for
numerical agreement in the C-1 test file so any drift between them
fails fast.
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default smoothing for ground-truth one-hots so they stay strictly
#: inside the open simplex (no entry equals zero). Spec value from the
#: C-1 deliverable: GT = 0.999 * one_hot + 0.001 / K uniform.
DEFAULT_GT_SMOOTH: float = 0.001

#: Floor used when a tensor is occasionally allowed to have zeros from
#: upstream code paths. We do NOT want to mask training-time zeros from
#: the predicted distribution — those should already be strictly
#: positive courtesy of ``SimplexStateEncoder.project_to_open_simplex``.
#: This floor is for ground-truth sanitation only.
SAFETY_FLOOR: float = 1e-12


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------


def fisher_rao_distance(p: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
    """Fisher-Rao geodesic distance on the open probability simplex.

    .. math::

        d(p, q) = 2 \\cdot \\arccos\\!\\Big(\\sum_k \\sqrt{p_k q_k}\\Big)

    Args:
        p: Probability vectors ``(..., K)``.
        q: Probability vectors ``(..., K)``.

    Returns:
        Distance tensor ``(...)`` (one scalar per leading-axis pair).

    Notes:
        - Computes in float64 internally, casts back to the input dtype.
        - Output range is ``[0, π]``.
        - ``d(p, p)`` is numerically pinned to 0 via a near-1.0 clamp on
          the Bhattacharyya coefficient before ``arccos``.
    """
    if p.shape != q.shape:
        raise ValueError(
            f"fisher_rao_distance: p and q must have matching shapes; "
            f"got {tuple(p.shape)} vs {tuple(q.shape)}."
        )

    original_dtype = p.dtype

    # Pointer-equality short-circuit: if the caller passed the same
    # tensor as both arguments the distance is exactly zero by
    # definition. Without this branch, float32-rounded simplex inputs
    # (whose entries don't quite sum to 1.0 even after normalization)
    # accumulate ~1e-3 error in the Bhattacharyya sum and the loose
    # near-1 clamp below cannot recover them.
    if p is q:
        out_shape = p.shape[:-1] if p.dim() > 1 else ()
        return torch.zeros(out_shape, dtype=original_dtype, device=p.device)

    p64 = torch.clamp(p.double(), min=SAFETY_FLOOR)
    q64 = torch.clamp(q.double(), min=SAFETY_FLOOR)

    # Bhattacharyya coefficient.
    bc = torch.sqrt(p64 * q64).sum(dim=-1)
    # Numerical clamp into ``[0, 1]``; arccos(1)=0, arccos(0)=π/2.
    bc = torch.clamp(bc, 0.0, 1.0)
    # Pin near-1 to exactly 1 so d(p,p) is numerically zero. The
    # tolerance is loose enough to absorb float32-rounded inputs
    # (where p.sum() is only ~1.0 to ~1e-6) without erasing real
    # near-overlap distances on distinct distributions.
    bc = torch.where(
        torch.abs(1.0 - bc) < 1e-6,
        torch.ones_like(bc),
        bc,
    )
    return (2.0 * torch.arccos(bc)).to(original_dtype)


# ---------------------------------------------------------------------------
# Smoothed one-hot
# ---------------------------------------------------------------------------


def smooth_one_hot(
    target_index: torch.Tensor,
    *,
    num_classes: int,
    epsilon: float = DEFAULT_GT_SMOOTH,
    dtype: Optional[torch.dtype] = None,
    device: Optional[torch.device] = None,
) -> torch.Tensor:
    """Convert integer class indices to smoothed one-hot rows.

    .. math::

        \\text{GT} = (1 - \\epsilon) \\cdot \\text{one\\_hot}
                   + \\frac{\\epsilon}{K} \\cdot \\text{uniform}

    The result lives on the open simplex (every entry > 0) and is
    therefore admissible as a Fisher-Rao argument.

    Args:
        target_index: ``(...)`` long tensor of class indices in
            ``[0, num_classes)``.
        num_classes: Number of atoms (``K``).
        epsilon: Smoothing coefficient. Default 0.001 per C-1 spec.
        dtype, device: Output dtype/device. Default inherits from
            ``target_index`` (with float promotion to float32).
    """
    if epsilon < 0.0 or epsilon >= 1.0:
        raise ValueError(f"epsilon must be in [0, 1); got {epsilon}.")
    if num_classes <= 1:
        raise ValueError(f"num_classes must be > 1; got {num_classes}.")

    if dtype is None:
        dtype = torch.float32
    if device is None:
        device = target_index.device

    # Build one-hot then mix with uniform.
    one_hot = torch.zeros(
        *target_index.shape, num_classes, dtype=dtype, device=device
    )
    one_hot.scatter_(-1, target_index.unsqueeze(-1).to(device), 1.0)
    uniform = torch.full_like(one_hot, 1.0 / float(num_classes))
    return (1.0 - epsilon) * one_hot + epsilon * uniform


# ---------------------------------------------------------------------------
# Loss module
# ---------------------------------------------------------------------------


class FisherRaoLoss(nn.Module):
    """Fisher-Rao loss on Δ°₃₉ with optional drift-penalty auxiliary.

    Forward signature::

        loss = fr_loss(p_pred, target, p_state_trace=None)

    where:
        - ``p_pred``  is ``(B, K)`` predicted final simplex
          distribution (must already be on the open simplex).
        - ``target``  is either an integer class tensor ``(B,)`` (we
          will smooth-one-hot it internally) OR a precomputed
          smoothed-one-hot ``(B, K)``. Pass ``target_is_index=True``
          for the integer case.
        - ``p_state_trace`` is an optional ``(B, S, K)`` per-step
          trace; if provided AND ``drift_weight > 0``, we add a drift
          penalty equal to ``mean_t( d(p_t, p_{t+1}) )`` averaged over
          the batch.

    The total returned scalar is::

        loss = mean_b( d(p_pred, GT) ) + drift_weight * drift_penalty

    Args:
        num_classes: ``K``. Default 40 for Δ°₃₉.
        epsilon_smooth: GT smoothing coefficient (default 0.001).
        drift_weight: Coefficient on the trace-drift penalty. Default
            ``0.0`` (off). Positive values discourage frame-to-frame
            thrashing in the encoder trajectory.
        reduction: ``"mean"`` or ``"sum"``. Default ``"mean"``.
    """

    def __init__(
        self,
        *,
        num_classes: int = 40,
        epsilon_smooth: float = DEFAULT_GT_SMOOTH,
        drift_weight: float = 0.0,
        reduction: str = "mean",
    ) -> None:
        super().__init__()
        if reduction not in ("mean", "sum"):
            raise ValueError(f"reduction must be 'mean' or 'sum'; got {reduction!r}.")
        self.num_classes = num_classes
        self.epsilon_smooth = epsilon_smooth
        self.drift_weight = drift_weight
        self.reduction = reduction

    # ------------------------------------------------------------------

    def _reduce(self, t: torch.Tensor) -> torch.Tensor:
        return t.mean() if self.reduction == "mean" else t.sum()

    # ------------------------------------------------------------------

    def forward(
        self,
        p_pred: torch.Tensor,
        target: torch.Tensor,
        *,
        target_is_index: bool = True,
        p_state_trace: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        """Compute the Fisher-Rao loss with optional drift penalty.

        Returns:
            Dict with keys ``"loss"`` (scalar), ``"distance"``
            (``(B,)`` per-sample Fisher-Rao distances), and
            ``"drift"`` (scalar drift penalty; zero when no trace
            supplied).
        """
        if p_pred.dim() != 2:
            raise ValueError(
                f"p_pred must be (B, K); got shape {tuple(p_pred.shape)}."
            )
        if p_pred.shape[-1] != self.num_classes:
            raise ValueError(
                f"p_pred last dim must be {self.num_classes}; got {p_pred.shape[-1]}."
            )

        # Build / validate ground truth on the open simplex.
        if target_is_index:
            if target.dtype not in (torch.long, torch.int64, torch.int32):
                target = target.long()
            gt = smooth_one_hot(
                target,
                num_classes=self.num_classes,
                epsilon=self.epsilon_smooth,
                dtype=p_pred.dtype,
                device=p_pred.device,
            )
        else:
            if target.shape != p_pred.shape:
                raise ValueError(
                    f"target (smoothed one-hot path) must match p_pred shape "
                    f"{tuple(p_pred.shape)}; got {tuple(target.shape)}."
                )
            gt = target

        distances = fisher_rao_distance(p_pred, gt)
        primary = self._reduce(distances)

        # Drift penalty.
        if p_state_trace is not None and self.drift_weight > 0.0:
            if p_state_trace.dim() != 3:
                raise ValueError(
                    f"p_state_trace must be (B, S, K); got "
                    f"{tuple(p_state_trace.shape)}."
                )
            if p_state_trace.shape[0] != p_pred.shape[0]:
                raise ValueError(
                    "p_state_trace batch dim must match p_pred batch dim."
                )
            seq_len = p_state_trace.shape[1]
            if seq_len < 2:
                drift = torch.zeros(
                    (), device=p_pred.device, dtype=p_pred.dtype
                )
            else:
                # d(p_t, p_{t+1}) over the seq axis, then mean over (B, T-1).
                p_a = p_state_trace[:, :-1, :]
                p_b = p_state_trace[:, 1:, :]
                step_dists = fisher_rao_distance(p_a, p_b)  # (B, T-1)
                drift = step_dists.mean()
        else:
            drift = torch.zeros((), device=p_pred.device, dtype=p_pred.dtype)

        total = primary + self.drift_weight * drift

        return {
            "loss": total,
            "distance": distances,
            "drift": drift,
        }


__all__ = [
    "fisher_rao_distance",
    "smooth_one_hot",
    "FisherRaoLoss",
    "DEFAULT_GT_SMOOTH",
]
