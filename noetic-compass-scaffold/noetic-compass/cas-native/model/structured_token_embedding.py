"""Embedding adapter for CAS structured-token batches.

This module is the first model-side consumer of ``StructuredTokenBatch``. It
does not claim to be the final CAS Transformer encoder. Its job is narrower and
load-bearing: fuse surface vocabulary identity with explicit CAS-axis features
so downstream heads can consume CAS-native streams instead of raw token IDs.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from cas_native.training.structured_token_adapter import (
    NUM_TOKEN_SOURCES,
    SIGNATURE_FEATURE_DIM,
    StructuredTokenBatch,
)
from cas_native.tokenizer.vocabulary import PAD_ID


class StructuredTokenEmbedding(nn.Module):
    """Fuse vocab IDs, CAS signatures, confidence, source, and span features."""

    def __init__(
        self,
        *,
        vocab_size: int,
        d_model: int,
        signature_dim: int = SIGNATURE_FEATURE_DIM,
        num_sources: int = NUM_TOKEN_SOURCES,
        padding_idx: int = PAD_ID,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        if vocab_size <= 0:
            raise ValueError(f"vocab_size must be > 0, got {vocab_size}")
        if d_model <= 0:
            raise ValueError(f"d_model must be > 0, got {d_model}")
        if signature_dim <= 0:
            raise ValueError(f"signature_dim must be > 0, got {signature_dim}")
        if num_sources <= 0:
            raise ValueError(f"num_sources must be > 0, got {num_sources}")

        self.vocab_size = vocab_size
        self.d_model = d_model
        self.signature_dim = signature_dim
        self.num_sources = num_sources
        self.padding_idx = padding_idx

        signature_hidden = max(32, min(256, d_model))
        self.surface_embedding = nn.Embedding(
            vocab_size,
            d_model,
            padding_idx=padding_idx,
        )
        self.signature_projection = nn.Sequential(
            nn.Linear(signature_dim, signature_hidden),
            nn.GELU(),
            nn.LayerNorm(signature_hidden),
            nn.Linear(signature_hidden, d_model),
        )
        self.confidence_projection = nn.Linear(1, d_model)
        self.source_embedding = nn.Embedding(num_sources, d_model, padding_idx=0)
        self.span_projection = nn.Linear(2, d_model)
        self.fusion_gate = nn.Linear(d_model * 2, d_model)
        self.output_norm = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        input_ids: torch.Tensor,
        signature_features: torch.Tensor,
        confidence_features: torch.Tensor,
        source_ids: torch.Tensor,
        span_features: torch.Tensor,
    ) -> torch.Tensor:
        if input_ids.dim() != 2:
            raise ValueError(f"input_ids must be 2-D, got shape {tuple(input_ids.shape)}")
        if signature_features.shape[:2] != input_ids.shape:
            raise ValueError("signature_features must share input_ids batch/sequence shape")
        if confidence_features.shape[:2] != input_ids.shape:
            raise ValueError("confidence_features must share input_ids batch/sequence shape")
        if source_ids.shape != input_ids.shape:
            raise ValueError("source_ids must match input_ids shape")
        if span_features.shape[:2] != input_ids.shape:
            raise ValueError("span_features must share input_ids batch/sequence shape")

        surface = self.surface_embedding(input_ids)
        cas_side = (
            self.signature_projection(signature_features)
            + self.confidence_projection(confidence_features)
            + self.source_embedding(source_ids)
            + self.span_projection(span_features)
        )
        gate = torch.sigmoid(self.fusion_gate(torch.cat([surface, cas_side], dim=-1)))
        fused = gate * surface + (1.0 - gate) * cas_side
        return self.dropout(self.output_norm(fused))

    def forward_batch(self, batch: StructuredTokenBatch) -> torch.Tensor:
        return self(
            batch.input_ids,
            batch.signature_features,
            batch.confidence_features,
            batch.source_ids,
            batch.span_features,
        )


class StructuredTokenStructuredPredictor(nn.Module):
    """Structured-token embedding adapter followed by a prediction head.

    Optionally accepts a ``GraphEncoder`` + ``GraphTextFusion`` pair for the
    diagram-loop lever. When both are provided and a ``graph_batch`` dict is
    passed to ``forward``, the text hidden states are enriched with per-node
    graph context before being passed to the prediction head.

    Backward compat: ``graph_encoder`` and ``graph_text_fusion`` both default to
    ``None``. Callers that don't pass either get the original text-only path.
    """

    def __init__(
        self,
        embedding: StructuredTokenEmbedding,
        head: nn.Module,
        graph_encoder: nn.Module | None = None,
        graph_text_fusion: nn.Module | None = None,
    ) -> None:
        super().__init__()
        self.embedding = embedding
        self.head = head
        self.graph_encoder = graph_encoder
        self.graph_text_fusion = graph_text_fusion

    def forward(
        self,
        batch: StructuredTokenBatch,
        graph_batch: dict[str, torch.Tensor] | None = None,
    ) -> dict[str, torch.Tensor]:
        """Forward pass.

        Args:
            batch:       structured-token batch (text path).
            graph_batch: optional batched graph tensors from
                         ``serialize_diagram_for_batch``. When provided and
                         the model has a graph encoder + fusion layer, the text
                         hidden states attend over the graph node embeddings.

        Returns:
            Dict of head logits + ``hidden_states``.
        """
        hidden_states = self.embedding.forward_batch(batch)

        if (
            graph_batch is not None
            and self.graph_encoder is not None
            and self.graph_text_fusion is not None
        ):
            node_hidden, node_mask = self.graph_encoder.forward_nodes_dict(graph_batch)
            hidden_states = self.graph_text_fusion(hidden_states, node_hidden, node_mask)

        output = self.head(hidden_states, attention_mask=batch.attention_mask)
        return {
            **output,
            "hidden_states": hidden_states,
        }


__all__ = [
    "StructuredTokenEmbedding",
    "StructuredTokenStructuredPredictor",
]
