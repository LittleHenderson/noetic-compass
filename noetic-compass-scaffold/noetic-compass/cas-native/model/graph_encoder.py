"""Graph Attention Network encoder for the diagram-loop lever.

Consumes the batched tensor input produced by ``diagram_serialization.py`` and
emits a per-graph fixed-size representation that can be fused with the text
encoder via ``graph_text_fusion.py``.

No third-party graph library required — this module uses hand-rolled message
passing over a dense adjacency matrix, which is appropriate for the small
graph sizes (max_nodes=32) typical of CAS expressions.

Architecture (2-3 GAT layers, hidden dim 64):

    node_features (B, N, F_node)
        → linear projection to hidden_dim
        → 2 GAT update layers (neighbour attention + residual)
        → mean-pool over masked nodes
        → per-graph vector (B, hidden_dim)

Edge features are incorporated as additive bias on the attention logits,
giving the model a direct signal for *how* two nodes are connected (e.g.
``instantiates`` vs ``rpm_descent`` vs ``emerges_as``).
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class _GATLayer(nn.Module):
    """Single graph attention layer with edge-feature bias.

    Computes for each target node ``i``:
        h_new[i] = LeakyReLU( W_self · h[i]  +  Σ_j α_{ij} · W_neigh · h[j] )

    where α_{ij} = softmax_j( attention_score(h[i], h[j]) + edge_bias[j→i] )
    over the masked neighbourhood of i.

    Args:
        in_dim:  input feature dimension per node.
        out_dim: output feature dimension per node.
        edge_dim: edge feature dimension.
        n_heads: number of attention heads (features are split equally).
    """

    def __init__(
        self,
        in_dim: int,
        out_dim: int,
        edge_dim: int,
        n_heads: int = 4,
    ) -> None:
        super().__init__()
        if out_dim % n_heads != 0:
            raise ValueError(f"out_dim ({out_dim}) must be divisible by n_heads ({n_heads})")
        self.n_heads = n_heads
        self.head_dim = out_dim // n_heads

        self.W_self = nn.Linear(in_dim, out_dim, bias=False)
        self.W_neigh = nn.Linear(in_dim, out_dim, bias=False)
        # Attention scoring: [h_i || h_j] → scalar per head
        self.attn = nn.Linear(2 * self.head_dim, 1, bias=False)
        # Edge bias: edge feature → scalar per head (additive to attn logit)
        self.edge_bias = nn.Linear(edge_dim, n_heads, bias=False)
        self.norm = nn.LayerNorm(out_dim)
        self.skip = nn.Linear(in_dim, out_dim, bias=False) if in_dim != out_dim else nn.Identity()

    def forward(
        self,
        h: torch.Tensor,
        edge_index: torch.Tensor,
        edge_features: torch.Tensor,
        node_mask: torch.Tensor,
        edge_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            h:             (B, N, in_dim)  node hidden states
            edge_index:    (B, 2, E)       source/target node indices
            edge_features: (B, E, edge_dim)
            node_mask:     (B, N)          True for real nodes
            edge_mask:     (B, E)          True for real edges

        Returns:
            (B, N, out_dim) updated node hidden states
        """
        B, N, _ = h.shape
        E_max = edge_index.shape[2]
        H, D = self.n_heads, self.head_dim

        # Project neighbours and self
        h_neigh = self.W_neigh(h).view(B, N, H, D)  # (B, N, H, D)
        h_self = self.W_self(h).view(B, N, H, D)

        # Gather source and target features for each edge
        src_idx = edge_index[:, 0, :]  # (B, E)
        tgt_idx = edge_index[:, 1, :]  # (B, E)

        # Expand indices for gather: (B, E, H, D)
        src_exp = src_idx.unsqueeze(-1).unsqueeze(-1).expand(B, E_max, H, D)
        tgt_exp = tgt_idx.unsqueeze(-1).unsqueeze(-1).expand(B, E_max, H, D)

        h_src = torch.gather(h_neigh, 1, src_exp)  # (B, E, H, D)
        h_tgt = torch.gather(h_neigh, 1, tgt_exp)  # (B, E, H, D)

        # Attention logits per edge
        attn_input = torch.cat([h_src, h_tgt], dim=-1)  # (B, E, H, 2D)
        attn_logits = self.attn(attn_input).squeeze(-1)  # (B, E, H)

        # Add edge feature bias
        edge_b = self.edge_bias(edge_features)  # (B, E, H)
        attn_logits = attn_logits + edge_b

        # Mask padding edges with large negative value
        edge_mask_exp = edge_mask.unsqueeze(-1).expand_as(attn_logits)
        attn_logits = attn_logits.masked_fill(~edge_mask_exp, -1e9)

        # Softmax over edges that point to the same target node.
        # Scatter softmax: for each target node, normalise over its in-edges.
        # We compute a per-node denominator via scatter_add.
        attn_exp = torch.exp(attn_logits - attn_logits.detach().amax(dim=1, keepdim=True))
        attn_exp = attn_exp * edge_mask_exp  # zero out padded

        # tgt_idx_exp: (B, E, H) for scatter
        tgt_idx_h = tgt_idx.unsqueeze(-1).expand(B, E_max, H)
        denom = torch.zeros(B, N, H, device=h.device, dtype=h.dtype)
        denom.scatter_add_(1, tgt_idx_h, attn_exp)
        denom = denom.clamp_min(1e-9)

        # Normalised attention weights per edge
        attn_w = attn_exp / torch.gather(denom, 1, tgt_idx_h)  # (B, E, H)

        # Weighted neighbourhood aggregation
        msg = h_src * attn_w.unsqueeze(-1)  # (B, E, H, D)
        # Scatter sum to target nodes
        agg = torch.zeros(B, N, H, D, device=h.device, dtype=h.dtype)
        tgt_exp2 = tgt_idx.unsqueeze(-1).unsqueeze(-1).expand(B, E_max, H, D)
        agg.scatter_add_(1, tgt_exp2, msg)
        agg = agg.reshape(B, N, H * D)  # (B, N, out_dim)

        # Residual + add self contribution + normalise
        out = F.leaky_relu(h_self.reshape(B, N, H * D) + agg, negative_slope=0.2)
        out = self.norm(out + self.skip(h))
        return out


class GraphEncoder(nn.Module):
    """Small graph attention encoder for CAS expression diagrams.

    Args:
        node_feature_dim: input node feature dimension from ``diagram_serialization``.
        edge_feature_dim: input edge feature dimension from ``diagram_serialization``.
        hidden_dim:       hidden/output dimension (default 64, per proposal spec).
        n_layers:         number of GAT layers (2 or 3, default 2).
        n_heads:          attention heads per layer (default 4).
        dropout:          dropout rate on the final pooled representation.

    Input (from ``serialize_diagram_for_batch``):
        node_features: (B, N, node_feature_dim)
        edge_index:    (B, 2, E)
        edge_features: (B, E, edge_feature_dim)
        node_mask:     (B, N) bool
        edge_mask:     (B, E) bool

    Output:
        (B, hidden_dim) per-graph representation (mean-pool over masked nodes).
    """

    def __init__(
        self,
        node_feature_dim: int,
        edge_feature_dim: int,
        hidden_dim: int = 64,
        n_layers: int = 2,
        n_heads: int = 4,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        if n_layers < 1:
            raise ValueError(f"n_layers must be >= 1, got {n_layers}")
        if hidden_dim <= 0:
            raise ValueError(f"hidden_dim must be > 0, got {hidden_dim}")

        self.hidden_dim = hidden_dim

        # Input projection
        self.input_proj = nn.Sequential(
            nn.Linear(node_feature_dim, hidden_dim),
            nn.GELU(),
            nn.LayerNorm(hidden_dim),
        )

        # GAT layers
        self.layers = nn.ModuleList(
            _GATLayer(hidden_dim, hidden_dim, edge_feature_dim, n_heads=n_heads)
            for _ in range(n_layers)
        )

        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        node_features: torch.Tensor,
        edge_index: torch.Tensor,
        edge_features: torch.Tensor,
        node_mask: torch.Tensor,
        edge_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Encode a batch of graphs to per-graph fixed-size vectors.

        Args:
            node_features: (B, N, node_feature_dim)
            edge_index:    (B, 2, E)
            edge_features: (B, E, edge_feature_dim)
            node_mask:     (B, N) bool — True for real nodes
            edge_mask:     (B, E) bool — True for real edges

        Returns:
            (B, hidden_dim) per-graph mean-pooled representation.
        """
        h = self.input_proj(node_features)  # (B, N, hidden_dim)

        for layer in self.layers:
            h = layer(h, edge_index, edge_features, node_mask, edge_mask)

        # Mean-pool over real (unmasked) nodes
        mask_f = node_mask.unsqueeze(-1).to(h.dtype)  # (B, N, 1)
        h_masked = h * mask_f
        n_real = mask_f.sum(dim=1).clamp_min(1.0)     # (B, 1)
        pooled = h_masked.sum(dim=1) / n_real          # (B, hidden_dim)

        return self.dropout(pooled)

    def forward_nodes(
        self,
        node_features: torch.Tensor,
        edge_index: torch.Tensor,
        edge_features: torch.Tensor,
        node_mask: torch.Tensor,
        edge_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return per-node hidden states for cross-attention in GraphTextFusion.

        Unlike ``forward``, which mean-pools to a single graph vector, this
        method returns the full ``(B, N, hidden_dim)`` node representation after
        all GAT layers, plus the ``node_mask`` needed to mask padded nodes in
        cross-attention.

        Returns:
            Tuple of:
              - node_hidden: (B, N, hidden_dim)
              - node_mask:   (B, N) bool
        """
        h = self.input_proj(node_features)
        for layer in self.layers:
            h = layer(h, edge_index, edge_features, node_mask, edge_mask)
        return h, node_mask

    def forward_nodes_dict(
        self, batch: dict[str, torch.Tensor]
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Convenience wrapper for ``forward_nodes`` from a serialized batch dict."""
        return self.forward_nodes(
            batch["node_features"],
            batch["edge_index"],
            batch["edge_features"],
            batch["node_mask"],
            batch["edge_mask"],
        )

    def forward_dict(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Convenience wrapper accepting a ``serialize_diagram_for_batch`` dict."""
        return self(
            batch["node_features"],
            batch["edge_index"],
            batch["edge_features"],
            batch["node_mask"],
            batch["edge_mask"],
        )


__all__ = ["GraphEncoder"]
