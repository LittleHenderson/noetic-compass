"""FisherRaoLoss — squared geodesic distance on Δ°₃₉ per build-spec §2.2.

Implements:
    sigma_{b,t} = sum_k sqrt(p[b,t,k] * q[b,t,k])
    sigma_{b,t} = clamp(sigma_{b,t}, 0.0, 1.0 - 1e-7)
    d_{b,t}     = 2 * arccos(sigma_{b,t})
    L_FR        = (sum_{b,t} m[b,t] * d_{b,t}^2) / max(sum_{b,t} m[b,t], 1)

Build-spec rationale (preserved verbatim from §2.2):
- Squared distance, NOT unsquared — squaring suppresses the gradient near
  σ=1 where ``arccos′`` blows up.
- fp64 internal compute path, fp32 cast at output.
- ``q`` is collator-derived per Option γ (hybrid anchor strategy).
- ``m`` is the per-position anchor mask; off-anchor positions contribute
  zero loss and zero gradient.

Stage 1 status: skeleton with full forward + telemetry. Numerical-safety
tests land in Stage 2 (≥8 unit tests in ``test_fisher_rao_loss.py``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from torch import nn


@dataclass
class FisherRaoLossConfig:
    """Hyperparameters per build-spec §2.2."""
    num_states: int = 40
    sigma_clamp_high: float = 1.0 - 1e-7
    sigma_clamp_low: float = 0.0
    eps_for_sqrt: float = 1e-12         # prevent sqrt(negative)
    squared_distance: bool = True       # always True per build-spec
    internal_dtype: torch.dtype = torch.float64


class FisherRaoLoss(nn.Module):
    """Squared geodesic Fisher-Rao distance with anchor masking.

    Forward args:
        p:      (B, L, K) predicted simplex points — strict positive, row-stochastic
        q:      (B, L, K) target  simplex points  — strict positive, row-stochastic
        mask:   (B, L)    bool/float — anchor mask, 1=apply loss, 0=ignore

    Returns:
        scalar L_FR (fp32)

    Telemetry (accessible via ``last_metrics`` dict for `train_progress`):
        loss_fr_mean_d            — mean of unsquared d at anchors (fp32)
        loss_fr_anchor_count      — total anchors in batch (int)
        loss_fr_pct_within_eps    — fraction of anchors with d < 0.1 (fp32)
        loss_fr_sigma_min         — min sigma observed (fp32)
        loss_fr_sigma_max         — max sigma observed (fp32)
    """

    def __init__(self, cfg: Optional[FisherRaoLossConfig] = None):
        super().__init__()
        self.cfg = cfg or FisherRaoLossConfig()
        self.last_metrics: dict[str, torch.Tensor] = {}

    def forward(
        self,
        p: torch.Tensor,
        q: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        if p.shape != q.shape:
            raise ValueError(f"p and q must have same shape; got {p.shape} vs {q.shape}")
        if p.shape[-1] != self.cfg.num_states:
            raise ValueError(
                f"Last dim must be {self.cfg.num_states}; got {p.shape[-1]}"
            )

        original_dtype = p.dtype
        p64 = p.to(dtype=self.cfg.internal_dtype)
        q64 = q.to(dtype=self.cfg.internal_dtype)

        # Bhattacharyya coefficient sigma = sum_k sqrt(p_k * q_k)
        # Use clamp before sqrt to defend against fp roundoff that could
        # produce tiny negatives even for strictly-positive inputs.
        product = (p64 * q64).clamp_min(self.cfg.eps_for_sqrt)
        sigma = product.sqrt().sum(dim=-1)               # (B, L)
        sigma = sigma.clamp(min=self.cfg.sigma_clamp_low, max=self.cfg.sigma_clamp_high)

        d = 2.0 * torch.arccos(sigma)                     # geodesic distance (B, L)
        d_squared = d * d

        if mask is None:
            anchor_mask = torch.ones_like(d, dtype=self.cfg.internal_dtype)
        else:
            anchor_mask = mask.to(dtype=self.cfg.internal_dtype)

        num = (anchor_mask * d_squared).sum()
        denom = anchor_mask.sum().clamp_min(1.0)
        loss_fr = (num / denom).to(dtype=original_dtype)

        # Telemetry (computed in fp64, surfaced as fp32 scalars)
        with torch.no_grad():
            anchor_count = anchor_mask.sum().to(dtype=torch.float32)
            if anchor_count.item() > 0:
                mean_d = ((anchor_mask * d).sum() / denom).to(dtype=torch.float32)
                within_eps = ((d < 0.1).to(self.cfg.internal_dtype) * anchor_mask).sum()
                pct_within = (within_eps / denom).to(dtype=torch.float32)
                sigma_min = sigma[anchor_mask > 0].min().to(dtype=torch.float32) \
                    if (anchor_mask > 0).any() else torch.tensor(0.0)
                sigma_max = sigma[anchor_mask > 0].max().to(dtype=torch.float32) \
                    if (anchor_mask > 0).any() else torch.tensor(0.0)
            else:
                mean_d = torch.tensor(0.0)
                pct_within = torch.tensor(0.0)
                sigma_min = torch.tensor(0.0)
                sigma_max = torch.tensor(0.0)
            self.last_metrics = {
                "loss_fr_mean_d": mean_d,
                "loss_fr_anchor_count": anchor_count,
                "loss_fr_pct_within_eps": pct_within,
                "loss_fr_sigma_min": sigma_min,
                "loss_fr_sigma_max": sigma_max,
            }

        return loss_fr
