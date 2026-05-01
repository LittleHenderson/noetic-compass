"""Tests for the structured-token embedding adapter."""

from __future__ import annotations

import pytest
import torch

from cas_native.model import (
    StructuredPredictionHead,
    StructuredTokenEmbedding,
    StructuredTokenStructuredPredictor,
    TURN_TYPE_LABELS,
)
from cas_native.tokenizer import StructuredTokenVocabulary, tokenize
from cas_native.training.structured_token_adapter import tokens_to_structured_token_batch


def _batch(max_length: int = 12):
    sequences = [
        tokenize("I feel drawn to this idea"),
        tokenize("we will audit ^2^P_{F4}|f carefully"),
    ]
    vocab = StructuredTokenVocabulary.from_token_sequences(sequences)
    return tokens_to_structured_token_batch(sequences, vocab, max_length=max_length), vocab


def test_structured_token_embedding_forward_shape():
    batch, vocab = _batch()
    embedding = StructuredTokenEmbedding(vocab_size=len(vocab), d_model=32, dropout=0.0)

    hidden = embedding.forward_batch(batch)

    assert hidden.shape == (batch.batch_size, batch.sequence_length, 32)
    assert torch.isfinite(hidden).all().item()


def test_structured_token_predictor_feeds_sequence_head():
    batch, vocab = _batch()
    embedding = StructuredTokenEmbedding(vocab_size=len(vocab), d_model=32, dropout=0.0)
    head = StructuredPredictionHead(d_model=32, bottleneck_dim=16)
    model = StructuredTokenStructuredPredictor(embedding, head)

    outputs = model(batch)
    loss = outputs["turn_type_logits"].sum()
    loss.backward()

    assert outputs["turn_type_logits"].shape == (2, len(TURN_TYPE_LABELS))
    assert outputs["hidden_states"].shape == (2, batch.sequence_length, 32)
    assert any(param.grad is not None for param in model.embedding.parameters())


def test_embedding_rejects_mismatched_feature_shapes():
    batch, vocab = _batch()
    embedding = StructuredTokenEmbedding(vocab_size=len(vocab), d_model=16)

    with pytest.raises(ValueError, match="signature_features"):
        embedding(
            batch.input_ids,
            batch.signature_features[:, :-1],
            batch.confidence_features,
            batch.source_ids,
            batch.span_features,
        )
