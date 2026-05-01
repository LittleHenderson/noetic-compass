"""Tests for structured-token vocabulary assignment."""

from __future__ import annotations

from cas_native.tokenizer import (
    BOS_ID,
    EOS_ID,
    PAD_ID,
    RESERVED_TOKENS,
    UNK_ID,
    StructuredTokenVocabulary,
    TokenSource,
    structured_token_key,
    tokenize,
)


def test_reserved_ids_are_stable():
    vocab = StructuredTokenVocabulary.empty()

    assert len(RESERVED_TOKENS) == 8
    assert vocab.token_to_id["<pad>"] == PAD_ID == 0
    assert vocab.token_to_id["<bos>"] == BOS_ID == 1
    assert vocab.token_to_id["<eos>"] == EOS_ID == 2
    assert vocab.token_to_id["<unk>"] == UNK_ID == 3


def test_build_from_token_sequences_is_source_aware_and_deterministic():
    tokens = tokenize("I feel drawn to ^2^P_{F4}|f")
    vocab = StructuredTokenVocabulary.from_token_sequences([tokens])

    keys = [structured_token_key(token) for token in tokens]
    assert "lex:feel" in vocab.token_to_id
    assert "lex:drawn to" in vocab.token_to_id
    assert "cas:^2^P_{F4}|f" in vocab.token_to_id
    assert len(set(vocab.id_for_key(key) for key in keys)) == len(set(keys))


def test_from_records_uses_user_prompt_only():
    records = [
        {
            "user_prompt": "plain words only",
            "assistant_response": "the hidden answer is ^9^O_{F7}|E",
            "cas_expression": "^9^O_{F7}|E",
        }
    ]

    vocab = StructuredTokenVocabulary.from_records(records)

    assert "cas:^9^O_{F7}|E" not in vocab.token_to_id
    assert "surf:plain" in vocab.token_to_id


def test_unknown_cas_and_lexicon_tokens_fall_back_to_source_reserved_ids():
    known = tokenize("I feel this")
    vocab = StructuredTokenVocabulary.from_token_sequences([known])
    unknown_cas = tokenize("^9^O_{F7}|E")[0]
    unknown_lex = [token for token in tokenize("I am exhausted") if token.source == TokenSource.LEXICON][-1]

    assert vocab.id_for_token(unknown_cas) == vocab.token_to_id["<cas_literal>"]
    assert vocab.id_for_token(unknown_lex) == vocab.token_to_id["<lexicon_hit>"]


def test_assign_ids_returns_token_copies_with_vocab_id():
    tokens = tokenize("I feel drawn to this")
    vocab = StructuredTokenVocabulary.from_token_sequences([tokens])

    assigned = vocab.assign_ids(tokens)

    assert all(token.vocab_id is not None for token in assigned)
    assert all(original.vocab_id is None for original in tokens)


def test_vocabulary_json_round_trip(tmp_path):
    vocab = StructuredTokenVocabulary.from_texts(
        ["I feel drawn to this", "we will audit this carefully"],
        min_count=1,
    )
    path = tmp_path / "structured_vocab.json"

    vocab.save(path)
    loaded = StructuredTokenVocabulary.load(path)

    assert loaded.token_to_id == vocab.token_to_id
    assert loaded.id_to_token == vocab.id_to_token
