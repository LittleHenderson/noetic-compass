"""Tests for tensorizing structured-token streams."""

from __future__ import annotations

import torch

from cas_native.tokenizer import BOS_ID, EOS_ID, PAD_ID, StructuredTokenVocabulary, tokenize
from cas_native.training.structured_token_adapter import (
    SIGNATURE_FEATURE_DIM,
    SOURCE_CAS_NOTATION_ID,
    SOURCE_LEXICON_ID,
    records_to_structured_token_batch,
    records_to_structured_token_sequences,
    tokens_to_structured_token_batch,
)


def _records():
    return [
        {
            "id": "a",
            "user_prompt": "I feel drawn to this idea",
            "assistant_response": "never use this answer ^9^O_{F7}|E as input",
            "cas_expression": "^9^O_{F7}|E",
        },
        {
            "id": "b",
            "user_prompt": "we will audit ^2^P_{F4}|f carefully",
            "assistant_response": "irrelevant",
            "cas_expression": "^2^P_{F4}|f",
        },
    ]


def test_records_to_sequences_tokenizes_user_prompt_only():
    sequences = records_to_structured_token_sequences(_records())
    surfaces = [token.surface_text for sequence in sequences for token in sequence]

    assert "^9^O_{F7}|E" not in surfaces
    assert "^2^P_{F4}|f" in surfaces


def test_tokens_to_batch_shapes_and_special_tokens():
    sequences = [tokenize("I feel drawn to this"), tokenize("we audit this")]
    vocab = StructuredTokenVocabulary.from_token_sequences(sequences)

    batch = tokens_to_structured_token_batch(sequences, vocab, max_length=10)

    assert batch.input_ids.shape == (2, 10)
    assert batch.attention_mask.shape == (2, 10)
    assert batch.signature_features.shape == (2, 10, SIGNATURE_FEATURE_DIM)
    assert batch.confidence_features.shape == (2, 10, 1)
    assert batch.source_ids.shape == (2, 10)
    assert batch.span_features.shape == (2, 10, 2)
    assert batch.input_ids[0, 0].item() == BOS_ID
    assert EOS_ID in batch.input_ids[0].tolist()
    assert batch.input_ids[0, -1].item() == PAD_ID


def test_records_to_batch_preserves_lexicon_and_cas_notation_sources():
    records = _records()
    vocab = StructuredTokenVocabulary.from_records(records)

    batch = records_to_structured_token_batch(records, vocab, max_length=16)

    assert batch.source_ids.eq(SOURCE_LEXICON_ID).any().item()
    assert batch.source_ids.eq(SOURCE_CAS_NOTATION_ID).any().item()
    assert batch.signature_features.abs().sum().item() > 0.0
    assert torch.all(batch.span_features >= 0.0)
    assert torch.all(batch.span_features <= 1.0)


def test_truncation_respects_max_length_with_special_tokens():
    tokens = tokenize("one two three four five six seven eight nine ten")
    vocab = StructuredTokenVocabulary.from_token_sequences([tokens])

    batch = tokens_to_structured_token_batch([tokens], vocab, max_length=6)

    assert batch.input_ids.shape == (1, 6)
    assert batch.attention_mask.sum().item() == 6
    assert batch.input_ids[0, 0].item() == BOS_ID
    assert batch.input_ids[0, -1].item() == EOS_ID
