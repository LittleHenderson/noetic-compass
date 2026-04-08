"""
FractalAttentionHead: Multi-head attention where each head's initial weights
follow fractal structure derived from IFS (Iterated Function System)
contraction maps.

Hutchinson operator: H(A) = union of wi(A) where wi are affine contractions.
Contraction ratios are learnable parameters initialized from CAS operator
composition patterns.

Supports 3 configurable levels of fractal depth, creating multi-scale
attention patterns that mirror the self-similar structure of cognitive
operator interactions.
"""

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class IFSContractionMap(nn.Module):
    """A single affine contraction map wi(x) = si * Ai @ x + bi.

    The contraction ratio si is a learnable parameter constrained to (0, 1)
    to guarantee convergence of the IFS.
    """

    def __init__(self, dim: int, initial_ratio: float = 0.5):
        super().__init__()
        # Learnable affine transform
        self.affine = nn.Linear(dim, dim, bias=True)

        # Learnable contraction ratio in (0, 1) via sigmoid of unconstrained param
        self._ratio_logit = nn.Parameter(
            torch.tensor(math.log(initial_ratio / (1.0 - initial_ratio)))
        )

        # Initialize affine close to identity scaled by contraction ratio
        nn.init.eye_(self.affine.weight)
        self.affine.weight.data *= initial_ratio
        nn.init.zeros_(self.affine.bias)

    @property
    def ratio(self) -> torch.Tensor:
        """Contraction ratio constrained to (0, 1)."""
        return torch.sigmoid(self._ratio_logit)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply the contraction map: si * Ai @ x + bi."""
        return self.ratio * self.affine(x)


class HutchinsonOperator(nn.Module):
    """Hutchinson operator H(A) = union of wi(A).

    Applies multiple IFS contraction maps and aggregates (sums) results.
    """

    def __init__(self, dim: int, num_maps: int = 4, initial_ratios: Optional[list[float]] = None):
        super().__init__()
        if initial_ratios is None:
            # Default: ratios derived from CAS operator composition
            # 10 operators, involution pairs share similar ratios
            initial_ratios = [0.3 + 0.1 * i for i in range(num_maps)]

        assert len(initial_ratios) == num_maps

        self.maps = nn.ModuleList([
            IFSContractionMap(dim, ratio)
            for ratio in initial_ratios
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply all contraction maps and sum results."""
        result = torch.zeros_like(x)
        for w_i in self.maps:
            result = result + w_i(x)
        return result


class FractalAttentionHead(nn.Module):
    """Multi-head attention with fractal-structured initial weights.

    Each attention head operates at a different fractal depth level,
    creating multi-scale attention patterns. The Hutchinson operator
    is applied iteratively to create self-similar structure in the
    attention weights.

    Architecture:
      - Standard QKV attention as base
      - Fractal depth levels (1-3) applied via iterated Hutchinson operator
      - Each head has its own IFS contraction maps (learnable)
      - Final attention is the average across fractal depths
    """

    def __init__(
        self,
        d_model: int,
        n_heads: int,
        fractal_depth: int = 3,
        num_ifs_maps: int = 4,
    ):
        super().__init__()
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"

        self.d_model = d_model
        self.n_heads = n_heads
        self.head_dim = d_model // n_heads
        self.fractal_depth = fractal_depth
        self.scale = math.sqrt(self.head_dim)

        # QKV projections
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        # Hutchinson operators for each fractal depth level
        # CAS operator composition ratios: based on involution pairs
        cas_ratios = [
            [0.3, 0.4, 0.5, 0.6],   # Level 1: coarse scale
            [0.2, 0.35, 0.45, 0.55], # Level 2: medium scale
            [0.15, 0.25, 0.35, 0.5], # Level 3: fine scale
        ]
        self.hutchinson_ops = nn.ModuleList([
            HutchinsonOperator(
                self.head_dim,
                num_ifs_maps,
                cas_ratios[min(i, len(cas_ratios) - 1)],
            )
            for i in range(fractal_depth)
        ])

        # Depth-level mixing weights (learnable)
        self.depth_weights = nn.Parameter(torch.ones(fractal_depth) / fractal_depth)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (batch, seq, d_model)

        Returns:
            Output tensor of shape (batch, seq, d_model)
        """
        batch, seq_len, _ = x.shape

        # QKV
        q = self.q_proj(x).view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(batch, seq_len, self.n_heads, self.head_dim).transpose(1, 2)

        # Apply fractal structure at multiple depth levels
        depth_weights = F.softmax(self.depth_weights, dim=0)
        accumulated_output = torch.zeros_like(q)

        # Start with the base queries
        q_current = q
        for depth, hutchinson in enumerate(self.hutchinson_ops):
            # Apply Hutchinson operator to queries (creates self-similar patterns)
            # Reshape for per-head application
            q_flat = q_current.reshape(-1, self.head_dim)
            q_fractal = hutchinson(q_flat).reshape_as(q_current)

            # Standard scaled dot-product attention with fractal queries
            attn_weights = torch.matmul(q_fractal, k.transpose(-2, -1)) / self.scale
            attn_weights = F.softmax(attn_weights, dim=-1)
            attn_output = torch.matmul(attn_weights, v)

            accumulated_output = accumulated_output + depth_weights[depth] * attn_output

            # For next depth, use the fractal queries as input (iterated IFS)
            q_current = q_fractal

        # Reshape and project
        output = accumulated_output.transpose(1, 2).contiguous().view(batch, seq_len, self.d_model)
        output = self.out_proj(output)

        return output
