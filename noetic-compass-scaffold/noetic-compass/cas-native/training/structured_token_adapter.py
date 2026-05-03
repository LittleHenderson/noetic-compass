"""Batch adapter for CAS structured-token streams.

This is the bridge between the Wave-1 tokenizer and model code. It converts
``StructuredToken`` sequences into tensors:

  - vocab IDs for surface identity
  - CAS-axis signature features for symbolic structure
  - confidence/source/span side channels for traceable provenance

It is intentionally parallel to ``structured_backbone_adapter.py`` so the old
raw-token path remains reproducible while the CAS-native input path matures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import torch

from cas_native.tokenizer.assembler import tokenize
from cas_native.tokenizer.lexicon.schema import CASLexicon, load_seed_lexicon
from cas_native.tokenizer.structured_token import (
    DOMAIN_AXIS_LEN,
    DRIVE_AXIS_LEN,
    NOETIC_AXIS_LEN,
    REGISTER_AXIS_LEN,
    StructuredToken,
    TokenSource,
)
from cas_native.tokenizer.vocabulary import (
    BOS_ID,
    EOS_ID,
    PAD_ID,
    StructuredTokenVocabulary,
)
from cas_native.training.structured_prediction_ingest import get_effective_prompt


SIGNATURE_FEATURE_DIM = (
    NOETIC_AXIS_LEN + DOMAIN_AXIS_LEN + DRIVE_AXIS_LEN + REGISTER_AXIS_LEN
)

SOURCE_PAD_ID = 0
SOURCE_FALLBACK_ID = 1
SOURCE_LEXICON_ID = 2
SOURCE_CAS_NOTATION_ID = 3
SOURCE_LEARNED_ID = 4
NUM_TOKEN_SOURCES = 5

SOURCE_ID_BY_TOKEN_SOURCE: dict[TokenSource, int] = {
    TokenSource.FALLBACK: SOURCE_FALLBACK_ID,
    TokenSource.LEXICON: SOURCE_LEXICON_ID,
    TokenSource.CAS_NOTATION: SOURCE_CAS_NOTATION_ID,
    TokenSource.LEARNED: SOURCE_LEARNED_ID,
}


@dataclass(frozen=True)
class StructuredTokenBatch:
    """Tensorized structured-token prompt batch."""

    input_ids: torch.Tensor
    attention_mask: torch.Tensor
    signature_features: torch.Tensor
    confidence_features: torch.Tensor
    source_ids: torch.Tensor
    span_features: torch.Tensor

    @property
    def batch_size(self) -> int:
        return int(self.input_ids.shape[0])

    @property
    def sequence_length(self) -> int:
        return int(self.input_ids.shape[1])


def cas_signature_feature_vector(token: StructuredToken) -> list[float]:
    sig = token.cas_signature
    return [
        *sig.noetic,
        *sig.domain,
        *sig.drive,
        *sig.register,
    ]


def source_id_for_token(token: StructuredToken) -> int:
    return SOURCE_ID_BY_TOKEN_SOURCE[token.source]


def _span_denominator(tokens: Sequence[StructuredToken]) -> float:
    if not tokens:
        return 1.0
    return float(max(1, max(token.surface_span[1] for token in tokens)))


def _content_budget(max_length: int, add_special_tokens: bool) -> int:
    if max_length <= 0:
        raise ValueError(f"max_length must be > 0, got {max_length}")
    if add_special_tokens:
        if max_length < 2:
            raise ValueError("max_length must be at least 2 when add_special_tokens=True")
        return max_length - 2
    return max_length


def tokens_to_structured_token_batch(
    token_sequences: Sequence[Sequence[StructuredToken]],
    vocabulary: StructuredTokenVocabulary,
    *,
    max_length: int = 256,
    device: torch.device | str | None = None,
    add_special_tokens: bool = True,
) -> StructuredTokenBatch:
    """Convert token sequences to padded tensor features."""

    if not token_sequences:
        raise ValueError("token_sequences must be non-empty")

    dev = torch.device(device) if device is not None else None
    content_budget = _content_budget(max_length, add_special_tokens)
    sequence_length = max_length
    batch_size = len(token_sequences)

    input_ids = torch.full(
        (batch_size, sequence_length),
        PAD_ID,
        dtype=torch.long,
        device=dev,
    )
    attention_mask = torch.zeros(
        (batch_size, sequence_length),
        dtype=torch.long,
        device=dev,
    )
    signature_features = torch.zeros(
        (batch_size, sequence_length, SIGNATURE_FEATURE_DIM),
        dtype=torch.float32,
        device=dev,
    )
    confidence_features = torch.zeros(
        (batch_size, sequence_length, 1),
        dtype=torch.float32,
        device=dev,
    )
    source_ids = torch.zeros(
        (batch_size, sequence_length),
        dtype=torch.long,
        device=dev,
    )
    span_features = torch.zeros(
        (batch_size, sequence_length, 2),
        dtype=torch.float32,
        device=dev,
    )

    for row_idx, sequence in enumerate(token_sequences):
        tokens = list(sequence[:content_budget])
        write_pos = 0
        if add_special_tokens:
            input_ids[row_idx, write_pos] = BOS_ID
            attention_mask[row_idx, write_pos] = 1
            write_pos += 1

        denominator = _span_denominator(tokens)
        for token in tokens:
            input_ids[row_idx, write_pos] = vocabulary.id_for_token(token)
            attention_mask[row_idx, write_pos] = 1
            signature_features[row_idx, write_pos] = torch.tensor(
                cas_signature_feature_vector(token),
                dtype=torch.float32,
                device=dev,
            )
            confidence_features[row_idx, write_pos, 0] = float(token.confidence)
            source_ids[row_idx, write_pos] = source_id_for_token(token)
            start, end = token.surface_span
            span_features[row_idx, write_pos, 0] = float(start) / denominator
            span_features[row_idx, write_pos, 1] = float(end) / denominator
            write_pos += 1

        if add_special_tokens and write_pos < sequence_length:
            input_ids[row_idx, write_pos] = EOS_ID
            attention_mask[row_idx, write_pos] = 1

    return StructuredTokenBatch(
        input_ids=input_ids,
        attention_mask=attention_mask,
        signature_features=signature_features,
        confidence_features=confidence_features,
        source_ids=source_ids,
        span_features=span_features,
    )


def records_to_structured_token_sequences(
    records: Iterable[dict[str, Any]],
    *,
    text_field: str = "user_prompt",
    lexicon: CASLexicon | None = None,
    include_whitespace: bool = False,
) -> list[list[StructuredToken]]:
    """Tokenize a record text field into structured-token sequences.

    The default field is ``user_prompt`` by design. Keep labels and rendered
    answers out of the input path unless a caller explicitly opts into another
    field for a non-training diagnostic.
    """

    record_list = list(records)
    if not record_list:
        raise ValueError("records must be non-empty")
    active_lexicon = lexicon or load_seed_lexicon()
    return [
        tokenize(
            _effective_record_text(record, text_field=text_field),
            lexicon=active_lexicon,
            include_whitespace=include_whitespace,
        )
        for record in record_list
    ]


def _effective_record_text(record: dict[str, Any], *, text_field: str) -> str:
    if text_field == "user_prompt":
        return get_effective_prompt(record)
    return str(record.get(text_field) or "")


def records_to_structured_token_batch(
    records: Iterable[dict[str, Any]],
    vocabulary: StructuredTokenVocabulary,
    *,
    text_field: str = "user_prompt",
    lexicon: CASLexicon | None = None,
    include_whitespace: bool = False,
    max_length: int = 256,
    device: torch.device | str | None = None,
    add_special_tokens: bool = True,
) -> StructuredTokenBatch:
    sequences = records_to_structured_token_sequences(
        records,
        text_field=text_field,
        lexicon=lexicon,
        include_whitespace=include_whitespace,
    )
    return tokens_to_structured_token_batch(
        sequences,
        vocabulary,
        max_length=max_length,
        device=device,
        add_special_tokens=add_special_tokens,
    )


__all__ = [
    "SIGNATURE_FEATURE_DIM",
    "SOURCE_PAD_ID",
    "SOURCE_FALLBACK_ID",
    "SOURCE_LEXICON_ID",
    "SOURCE_CAS_NOTATION_ID",
    "SOURCE_LEARNED_ID",
    "NUM_TOKEN_SOURCES",
    "SOURCE_ID_BY_TOKEN_SOURCE",
    "StructuredTokenBatch",
    "cas_signature_feature_vector",
    "source_id_for_token",
    "tokens_to_structured_token_batch",
    "records_to_structured_token_sequences",
    "records_to_structured_token_batch",
]
