"""Cross-attention fusion layer: text encoder hidden states attend over graph nodes.

This is the bridge between the ``GraphEncoder`` and the ``StructuredTokenEmbedding``
path. Text tokens attend over per-node graph embeddings, producing text hidden
states enriched with the structural graph context.

Fusion direction (as specified in proposal §4.1):
    text attends over graph nodes (text queries, graph keys/values)

This is the cheaper default — bidirectional would be a follow-up.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class GraphTextFusion(nn.Module):
    """Cross-attention: text hidden states attend over graph-encoder node embeddings.

    Args:
        d_text:     dimension of text hidden states (from ``StructuredTokenEmbedding``).
        d_graph:    dimension of graph node embeddings (from ``GraphEncoder``).
        n_heads:    number of attention heads.
        dropout:    dropout on attention weights and output projection.

    Input:
        text_hidden:  (B, T, d_text)   text encoder hidden states (queries)
        graph_nodes:  (B, N, d_graph)  per-node graph encoder embeddings (keys/values)
        node_mask:    (B, N)           True for real graph nodes

    Output:
        (B, T, d_text)  text hidden states enriched with graph context

    When ``graph_nodes`` is None or all nodes are masked, the layer returns
    ``text_hidden`` unchanged (identity pass-through for backward compat).
    """

    def __init__(
        self,
        d_text: int,
        d_graph: int,
        n_heads: int = 4,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        if d_text <= 0:
            raise ValueError(f"d_text must be > 0, got {d_text}")
        if d_graph <= 0:
            raise ValueError(f"d_graph must be > 0, got {d_graph}")
        if d_text % n_heads != 0:
            raise ValueError(
                f"d_text ({d_text}) must be divisible by n_heads ({n_heads})"
            )

        self.d_text = d_text
        self.d_graph = d_graph
        self.n_heads = n_heads
        self.head_dim = d_text // n_heads

        # Project text → queries, graph → keys & values
        self.q_proj = nn.Linear(d_text, d_text, bias=False)
        self.k_proj = nn.Linear(d_graph, d_text, bias=False)
        self.v_proj = nn.Linear(d_graph, d_text, bias=False)
        self.out_proj = nn.Linear(d_text, d_text, bias=False)

        self.dropout = nn.Dropout(dropout)
        self.norm = nn.LayerNorm(d_text)

        self._scale = self.head_dim ** -0.5

    def forward(
        self,
        text_hidden: torch.Tensor,
        graph_nodes: torch.Tensor | None,
        node_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Fuse text hidden states with graph node context.

        Args:
            text_hidden: (B, T, d_text)
            graph_nodes: (B, N, d_graph) or None (identity pass-through)
            node_mask:   (B, N) bool, True for real nodes; None = all real

        Returns:
            (B, T, d_text) enriched text hidden states
        """
        if graph_nodes is None:
            return text_hidden

        B, T, _ = text_hidden.shape
        N = graph_nodes.shape[1]
        H, D = self.n_heads, self.head_dim

        # Check if any real graph nodes exist at all
        if node_mask is not None and not node_mask.any():
            return text_hidden

        # Projections
        q = self.q_proj(text_hidden).view(B, T, H, D).transpose(1, 2)  # (B, H, T, D)
        k = self.k_proj(graph_nodes).view(B, N, H, D).transpose(1, 2)  # (B, H, N, D)
        v = self.v_proj(graph_nodes).view(B, N, H, D).transpose(1, 2)  # (B, H, N, D)

        # Scaled dot-product attention
        attn_logits = torch.matmul(q, k.transpose(-2, -1)) * self._scale  # (B, H, T, N)

        # Mask padded graph nodes
        if node_mask is not None:
            # node_mask: (B, N) → (B, 1, 1, N)
            mask = node_mask.unsqueeze(1).unsqueeze(2)
            attn_logits = attn_logits.masked_fill(~mask, -1e9)

        attn_weights = F.softmax(attn_logits, dim=-1)  # (B, H, T, N)
        attn_weights = self.dropout(attn_weights)

        context = torch.matmul(attn_weights, v)           # (B, H, T, D)
        context = context.transpose(1, 2).contiguous()    # (B, T, H, D)
        context = context.view(B, T, H * D)               # (B, T, d_text)
        context = self.out_proj(context)                   # (B, T, d_text)
        context = self.dropout(context)

        # Residual + LayerNorm
        return self.norm(text_hidden + context)


__all__ = ["GraphTextFusion"]
